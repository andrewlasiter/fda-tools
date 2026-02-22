"""
FDA-239  [SIG-004] MAUDE Adverse Event Narrative Classifier
============================================================
Uses Claude Haiku (``claude-haiku-4-5-20251001``) to zero-shot classify
MAUDE adverse event narratives into four structured categories:

    harm_type      : DEATH | SERIOUS_INJURY | INJURY | MALFUNCTION |
                     NO_INJURY | UNKNOWN
    failure_mode   : SOFTWARE | MECHANICAL | ELECTRICAL | USER_ERROR |
                     LABELING | STERILITY | BATTERY | CONNECTIVITY |
                     MATERIAL_DEGRADATION | OTHER | UNKNOWN
    severity       : CRITICAL | HIGH | MEDIUM | LOW | UNKNOWN
    patient_outcome: DEATH | PERMANENT_IMPAIRMENT | TEMPORARY_IMPAIRMENT |
                     HOSPITALIZATION | NO_OUTCOME | UNKNOWN

All classifications include a confidence score (0.0–1.0).

Performance
-----------
- Target: 100 narratives/minute on Haiku
- Batches of 10 narratives per API call (reduces token overhead)
- Results cached in ``maude_classifications`` Postgres table
- Regex keyword fallback when API is unavailable

Schema dependency
-----------------
    CREATE TABLE IF NOT EXISTS maude_classifications (
        event_id     text PRIMARY KEY,
        product_code text,
        narrative    text NOT NULL,
        harm_type    text,
        failure_mode text,
        severity     text,
        patient_outcome text,
        confidence   float,
        method       text NOT NULL,   -- 'haiku' | 'regex' | 'cached'
        classified_at timestamptz NOT NULL DEFAULT now()
    );

Usage
-----
    from fda_tools.scripts.maude_classifier import classify_batch

    results = classify_batch(
        narratives=[{"event_id": "123", "text": "The pump stopped..."}],
        product_code="DQY",
    )
"""

from __future__ import annotations

import json
import logging
import os
import re
import time
from dataclasses import dataclass
from typing import List, Optional, Dict

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

MODEL_ID        = "claude-haiku-4-5-20251001"
BATCH_SIZE      = 10           # narratives per Haiku call
MAX_TOKENS      = 1024         # output tokens per batch call
RATE_LIMIT_RPM  = 60           # Haiku rate limit guard
MIN_CALL_GAP_S  = 60 / RATE_LIMIT_RPM

# ── Data structures ───────────────────────────────────────────────────────────

@dataclass
class ClassificationResult:
    event_id:       str
    harm_type:      str
    failure_mode:   str
    severity:       str
    patient_outcome: str
    confidence:     float
    method:         str         # 'haiku' | 'regex' | 'error'
    raw_narrative:  Optional[str] = None


# ── Regex keyword fallback ────────────────────────────────────────────────────

# Map category → (pattern, value) pairs ordered by priority
_HARM_PATTERNS = [
    (r"\b(death|died|fatal|fatality|deceased)\b", "DEATH"),
    (r"\b(permanent|paralysis|amputat|blind|deaf|serious injur)\b", "SERIOUS_INJURY"),
    (r"\b(injur|burn|lacerat|fracture|hemorrhage|bleeding|pain)\b", "INJURY"),
    (r"\b(malfunction|fail|defect|broke|stopped working|error)\b", "MALFUNCTION"),
    (r"\b(no injur|no harm|no adverse|without incident)\b", "NO_INJURY"),
]

_FAILURE_PATTERNS = [
    (r"\b(software|firmware|program|algorithm|crash|freeze|reboot)\b", "SOFTWARE"),
    (r"\b(crack|fracture|break|bent|deform|structural)\b", "MECHANICAL"),
    (r"\b(short circuit|electrical|power supply|voltage|current|spark)\b", "ELECTRICAL"),
    (r"\b(user error|misuse|operator|training|human error)\b", "USER_ERROR"),
    (r"\b(label|instruction|IFU|directions|package insert)\b", "LABELING"),
    (r"\b(sterile|contamina|infection|bioburden)\b", "STERILITY"),
    (r"\b(battery|charge|power|discharg)\b", "BATTERY"),
    (r"\b(connect|network|wireless|bluetooth|wifi|signal)\b", "CONNECTIVITY"),
    (r"\b(degrad|corrode|wear|deteriorat|rust|leak)\b", "MATERIAL_DEGRADATION"),
]

_SEVERITY_PATTERNS = [
    (r"\b(death|died|fatal|critical condition|life.threatening)\b", "CRITICAL"),
    (r"\b(hospital|ICU|emergenc|serious|severe|permanent)\b", "HIGH"),
    (r"\b(injur|medical attention|treatment|temporary)\b", "MEDIUM"),
    (r"\b(minor|mild|no harm|no injur|inconvenience)\b", "LOW"),
]

_OUTCOME_PATTERNS = [
    (r"\b(death|died|fatal|deceased)\b", "DEATH"),
    (r"\b(permanent|paralysis|amputation|blind|deaf)\b", "PERMANENT_IMPAIRMENT"),
    (r"\b(temporary|recovered|resolved|healing)\b", "TEMPORARY_IMPAIRMENT"),
    (r"\b(hospital|admitted|ICU|emergency room|ER)\b", "HOSPITALIZATION"),
    (r"\b(no outcome|no injur|no harm|no adverse)\b", "NO_OUTCOME"),
]


def _classify_regex(event_id: str, text: str) -> ClassificationResult:
    """Fast keyword-based fallback classifier (no API call)."""
    text_lower = text.lower()

    def match_first(patterns: list, default: str) -> str:
        for pattern, value in patterns:
            if re.search(pattern, text_lower, re.IGNORECASE):
                return value
        return default

    return ClassificationResult(
        event_id        = event_id,
        harm_type       = match_first(_HARM_PATTERNS,    "UNKNOWN"),
        failure_mode    = match_first(_FAILURE_PATTERNS, "UNKNOWN"),
        severity        = match_first(_SEVERITY_PATTERNS,"UNKNOWN"),
        patient_outcome = match_first(_OUTCOME_PATTERNS, "UNKNOWN"),
        confidence      = 0.55,   # regex is medium-confidence
        method          = "regex",
        raw_narrative   = text[:200],
    )


# ── Haiku batch classifier ────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are a medical device adverse event classifier.
For each narrative, output a JSON object with exactly these keys:
  harm_type      : one of DEATH|SERIOUS_INJURY|INJURY|MALFUNCTION|NO_INJURY|UNKNOWN
  failure_mode   : one of SOFTWARE|MECHANICAL|ELECTRICAL|USER_ERROR|LABELING|
                   STERILITY|BATTERY|CONNECTIVITY|MATERIAL_DEGRADATION|OTHER|UNKNOWN
  severity       : one of CRITICAL|HIGH|MEDIUM|LOW|UNKNOWN
  patient_outcome: one of DEATH|PERMANENT_IMPAIRMENT|TEMPORARY_IMPAIRMENT|
                   HOSPITALIZATION|NO_OUTCOME|UNKNOWN
  confidence     : float 0.0–1.0 representing your certainty

Rules:
- Use only the listed values; never invent new categories
- If the narrative is too vague, use UNKNOWN with low confidence
- Output ONLY a JSON array, one object per narrative, no extra text
"""

def _build_user_message(batch: List[dict]) -> str:
    lines = []
    for i, item in enumerate(batch):
        text = item["text"][:800]   # truncate very long narratives
        lines.append(f'[{i}] """{text}"""')
    return "Classify these MAUDE narratives:\n\n" + "\n\n".join(lines)


def _parse_haiku_response(response_text: str, batch: List[dict]) -> List[ClassificationResult]:
    """Parse the JSON array returned by Haiku."""
    try:
        # Strip markdown code fences if present
        text = response_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```[a-z]*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        parsed = json.loads(text)
        if not isinstance(parsed, list):
            parsed = [parsed]
    except (json.JSONDecodeError, ValueError) as exc:
        logger.warning("Haiku JSON parse failed: %s\nResponse: %s", exc, response_text[:300])
        return []

    results = []
    for i, item in enumerate(batch[:len(parsed)]):
        c = parsed[i] if i < len(parsed) else {}
        results.append(ClassificationResult(
            event_id        = item["event_id"],
            harm_type       = c.get("harm_type", "UNKNOWN"),
            failure_mode    = c.get("failure_mode", "UNKNOWN"),
            severity        = c.get("severity", "UNKNOWN"),
            patient_outcome = c.get("patient_outcome", "UNKNOWN"),
            confidence      = float(c.get("confidence", 0.7)),
            method          = "haiku",
            raw_narrative   = item["text"][:200],
        ))
    return results


_last_call_time: float = 0.0


def _call_haiku(batch: List[dict]) -> List[ClassificationResult]:
    """Call Claude Haiku for a batch; rate-limit to MIN_CALL_GAP_S."""
    global _last_call_time
    gap = time.monotonic() - _last_call_time
    if gap < MIN_CALL_GAP_S:
        time.sleep(MIN_CALL_GAP_S - gap)

    try:
        import anthropic as _anthropic_module  # type: ignore[import]
    except ImportError:
        raise ImportError("anthropic SDK required: pip install anthropic")

    api_key = os.getenv("ANTHROPIC_API_KEY")
    client = _anthropic_module.Anthropic(api_key=api_key) if api_key else _anthropic_module.Anthropic()

    _last_call_time = time.monotonic()
    msg = client.messages.create(
        model      = MODEL_ID,
        max_tokens = MAX_TOKENS,
        system     = _SYSTEM_PROMPT,
        messages   = [{"role": "user", "content": _build_user_message(batch)}],
    )

    _TextBlock = _anthropic_module.types.TextBlock
    response_text = next(
        (b.text for b in msg.content if isinstance(b, _TextBlock)),
        "",
    )
    return _parse_haiku_response(response_text, batch)


# ── Database caching ──────────────────────────────────────────────────────────

def _load_cached(event_ids: List[str], db_url: Optional[str]) -> Dict[str, ClassificationResult]:
    """Return already-classified event IDs from DB."""
    if not db_url:
        return {}
    try:
        import psycopg2 as _pg  # type: ignore[import]
        conn = _pg.connect(db_url)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT event_id, harm_type, failure_mode, severity,
                           patient_outcome, confidence, method
                    FROM maude_classifications
                    WHERE event_id = ANY(%s)
                """, (event_ids,))
                return {
                    row[0]: ClassificationResult(
                        event_id=row[0], harm_type=row[1], failure_mode=row[2],
                        severity=row[3], patient_outcome=row[4],
                        confidence=float(row[5] or 0), method=str(row[6] or "cached"),
                    )
                    for row in cur.fetchall()
                }
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Cache load failed: %s", exc)
        return {}


def _save_classifications(results: List[ClassificationResult], db_url: Optional[str]) -> None:
    """Upsert classification results into maude_classifications."""
    if not db_url or not results:
        return
    try:
        import psycopg2 as _pg  # type: ignore[import]
        from psycopg2.extras import execute_batch as _eb  # type: ignore[import]
        conn = _pg.connect(db_url)
        try:
            sql = """
                INSERT INTO maude_classifications
                    (event_id, harm_type, failure_mode, severity,
                     patient_outcome, confidence, method)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (event_id) DO UPDATE SET
                    harm_type       = EXCLUDED.harm_type,
                    failure_mode    = EXCLUDED.failure_mode,
                    severity        = EXCLUDED.severity,
                    patient_outcome = EXCLUDED.patient_outcome,
                    confidence      = EXCLUDED.confidence,
                    method          = EXCLUDED.method,
                    classified_at   = now()
            """
            rows = [
                (r.event_id, r.harm_type, r.failure_mode,
                 r.severity, r.patient_outcome, r.confidence, r.method)
                for r in results
            ]
            with conn.cursor() as cur:
                _eb(cur, sql, rows)
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("Cache write failed: %s", exc)


# ── Public API ────────────────────────────────────────────────────────────────

def classify_batch(
    narratives:   List[dict],
    product_code: str = "",
    db_url:       Optional[str] = None,
    use_cache:    bool = True,
    use_haiku:    bool = True,
) -> List[ClassificationResult]:
    """
    Classify a list of MAUDE narratives.

    Parameters
    ----------
    narratives   : list of ``{"event_id": str, "text": str}``
    product_code : FDA product code (logged only)
    db_url       : PostgreSQL DSN for caching
    use_cache    : skip already-classified events
    use_haiku    : use Claude Haiku; falls back to regex on failure

    Returns
    -------
    List of :class:`ClassificationResult`
    """
    if not narratives:
        return []

    db_url = db_url or os.getenv("DATABASE_URL")
    results: Dict[str, ClassificationResult] = {}

    # Load cached
    if use_cache:
        cached = _load_cached([n["event_id"] for n in narratives], db_url)
        results.update(cached)
        logger.info("Cache hit: %d/%d narratives", len(cached), len(narratives))

    # Determine what still needs classification
    remaining = [n for n in narratives if n["event_id"] not in results]
    if not remaining:
        return list(results.values())

    # Try Haiku in batches
    new_results: List[ClassificationResult] = []
    if use_haiku:
        for i in range(0, len(remaining), BATCH_SIZE):
            batch = remaining[i : i + BATCH_SIZE]
            try:
                batch_results = _call_haiku(batch)
                new_results.extend(batch_results)
                logger.info(
                    "Haiku classified %d narratives (product=%s)",
                    len(batch_results), product_code or "?",
                )
                # Fill any missing items with regex
                classified_ids = {r.event_id for r in batch_results}
                for item in batch:
                    if item["event_id"] not in classified_ids:
                        new_results.append(_classify_regex(item["event_id"], item["text"]))
            except Exception as exc:
                logger.warning(
                    "Haiku batch failed (%s); falling back to regex for %d items",
                    exc, len(batch),
                )
                for item in batch:
                    new_results.append(_classify_regex(item["event_id"], item["text"]))
    else:
        for item in remaining:
            new_results.append(_classify_regex(item["event_id"], item["text"]))

    # Cache new results
    if use_cache and new_results:
        _save_classifications(new_results, db_url)

    results.update({r.event_id: r for r in new_results})
    return list(results.values())


def classify_single(
    event_id: str,
    text:     str,
    db_url:   Optional[str] = None,
) -> ClassificationResult:
    """Convenience wrapper for single-narrative classification."""
    results = classify_batch(
        [{"event_id": event_id, "text": text}],
        db_url=db_url,
    )
    return results[0] if results else _classify_regex(event_id, text)
