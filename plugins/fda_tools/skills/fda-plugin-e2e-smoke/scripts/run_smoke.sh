#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: run_smoke.sh [--tmp-dir DIR] [--workers N] [--cleanup]

Deterministic live smoke check for FDA plugin scripts:
  - scripts/gap_analysis.py
  - scripts/predicate_extractor.py

Options:
  --tmp-dir DIR   Reuse/create a specific workspace directory.
  --workers N     Worker count passed to predicate_extractor.py (default: 1).
  --cleanup       Delete workspace when finished.
EOF
}

TMP_DIR=""
WORKERS="1"
CLEANUP="0"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --tmp-dir)
      TMP_DIR="${2:-}"
      shift 2
      ;;
    --workers)
      WORKERS="${2:-}"
      shift 2
      ;;
    --cleanup)
      CLEANUP="1"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 1
      ;;
  esac
done

if [[ -z "$TMP_DIR" ]]; then
  TMP_DIR="$(mktemp -d /tmp/fda_plugin_smoke_XXXXXX)"
else
  mkdir -p "$TMP_DIR"
fi

DATA_DIR="$TMP_DIR/data"
PDF_DIR="$TMP_DIR/pdfs"
WORK_DIR="$TMP_DIR/work"
EXTRACT_DIR="$WORK_DIR/extract"
mkdir -p "$DATA_DIR" "$PDF_DIR" "$EXTRACT_DIR"

cleanup_tmp() {
  if [[ "$CLEANUP" == "1" ]]; then
    rm -rf "$TMP_DIR"
  fi
}
trap cleanup_tmp EXIT

echo "[1/5] Preparing synthetic PMN/baseline data"
cat > "$DATA_DIR/pmn96cur.txt" <<'EOF'
KNUMBER|APPLICANT|STREET1|STREET2|CITY|STATE|COUNTRY_CODE|ZIP|DATEPANEL|DESSION_DATE|DATERECEIVED|DECISION|REVIEWCODE|ESSION_CODE|PRODUCTCODE|STATEORSUMM|CLASSADVISE|ESSION_CODE2|TYPE|THIRDPARTY|EXPEDITEDREVIEW|DEVICENAME
K250001|ALPHA MEDICAL|1 Main||Boston|MA|US|02108|01/15/2025|02/15/2025|01/01/2025|SESE|RC001|SE|AAA|Cleared|N|SE|Traditional|N|N|Alpha Predicate
K250002|BETA DEVICES|2 Oak||Austin|TX|US|73301|02/01/2025|03/01/2025|02/01/2025|SESE|RC002|SE|BBB|Cleared|N|SE|Special|N|N|Beta Reference
K250003|GAMMA HEALTH|3 Pine||Denver|CO|US|80014|03/01/2025|04/01/2025|03/01/2025|SESE|RC003|SE|AAA|Cleared|N|SE|Traditional|N|N|Gamma Subject
EOF

for f in pmn9195 pmn8690 pmn8185 pmn7680 pmnlstmn; do
  cp "$DATA_DIR/pmn96cur.txt" "$DATA_DIR/$f.txt"
done

cat > "$DATA_DIR/pma.txt" <<'EOF'
PNUMBER|OTHER
P123456|x
EOF

cat > "$WORK_DIR/baseline.csv" <<'EOF'
KNUMBER,TYPE
K250001,Predicate
EOF

echo "[2/5] Running gap analysis"
python3 scripts/gap_analysis.py \
  --years 2025 \
  --pmn-files "$DATA_DIR/pmn96cur.txt" \
  --baseline "$WORK_DIR/baseline.csv" \
  --pdf-dir "$PDF_DIR" \
  --output "$WORK_DIR/gap_manifest.csv"

echo "[3/5] Creating sample PDF"
export TMP_DIR
python3 - <<'PY'
import os
from pathlib import Path

import fitz

tmp = Path(os.environ["TMP_DIR"])
pdf_path = tmp / "pdfs" / "K250003.pdf"
pdf_path.parent.mkdir(parents=True, exist_ok=True)

doc = fitz.open()
page = doc.new_page()
page.insert_text(
    (72, 72),
    "Subject device K250003 cites predicate K250001 and reference K250002. Also mentions DEN200045.",
)
doc.save(str(pdf_path))
doc.close()
print(f"PDF_CREATED:{pdf_path}")
PY

echo "[4/5] Running predicate extractor"
EXTRACT_LOG="$EXTRACT_DIR/extract.log"
if ! python3 scripts/predicate_extractor.py \
  --directory "$PDF_DIR" \
  --output-dir "$EXTRACT_DIR" \
  --data-dir "$DATA_DIR" \
  --no-cache \
  --workers "$WORKERS" \
  --batch-size 10 >"$EXTRACT_LOG" 2>&1; then
  cat "$EXTRACT_LOG" >&2
  if grep -q "SemLock" "$EXTRACT_LOG"; then
    echo "ERROR: Multiprocessing semaphore restriction detected (SemLock)." >&2
    echo "Rerun with elevated permissions or outside restricted sandbox." >&2
    exit 2
  fi
  exit 1
fi

echo "[5/5] Validating smoke outputs"
python3 - "$WORK_DIR/gap_manifest.csv" "$EXTRACT_DIR/output.csv" <<'PY'
import csv
import sys

manifest_path, output_path = sys.argv[1], sys.argv[2]

with open(manifest_path, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
    got = {(r["KNUMBER"], r["STATUS"]) for r in rows}
    required = {("K250002", "need_download"), ("K250003", "need_download")}
    missing = required - got
    if missing:
        raise SystemExit(f"Manifest missing expected rows: {sorted(missing)}")

with open(output_path, newline="", encoding="utf-8") as f:
    out_rows = list(csv.DictReader(f))
    if len(out_rows) != 1:
        raise SystemExit(f"Expected 1 extraction row, got {len(out_rows)}")
    row = out_rows[0]
    values = set(row.values())
    for token in ["K250001", "K250002", "DEN200045"]:
        if token not in values:
            raise SystemExit(f"Missing extracted token: {token}")

print("SMOKE_VALIDATION:PASS")
PY

echo "SMOKE_STATUS:PASS"
echo "SMOKE_TMP_DIR:$TMP_DIR"
echo "SMOKE_MANIFEST:$WORK_DIR/gap_manifest.csv"
echo "SMOKE_OUTPUT:$EXTRACT_DIR/output.csv"
echo "SMOKE_SUPPLEMENT:$EXTRACT_DIR/supplement.csv"
