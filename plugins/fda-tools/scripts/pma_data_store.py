#!/usr/bin/env python3
"""
PMA Data Store -- Structured Cache and Manifest System for PMA Intelligence.

Provides project-level manifest, TTL-based caching, and file organization
for PMA approval data, SSED documents, supplement tracking, and extracted
sections. Follows the same patterns as fda_data_store.py for 510(k) data.

Directory layout:
    ~/fda-510k-data/pma_cache/
        data_manifest.json
        P170019/
            pma_data.json          # API data from openFDA
            ssed.pdf               # Downloaded SSED PDF
            extracted_sections.json # 15-section extraction results
        P200024/
            ...

Usage:
    from pma_data_store import PMADataStore

    store = PMADataStore()
    data = store.get_pma_data("P170019")
    store.save_pma_data("P170019", data)
    manifest = store.get_manifest()
    store.update_manifest("P170019", {"status": "downloaded"})

    # CLI usage:
    python3 pma_data_store.py --pma P170019
    python3 pma_data_store.py --pma P170019 --refresh
    python3 pma_data_store.py --show-manifest
    python3 pma_data_store.py --product-code NMH --year 2024
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

# Import FDAClient from sibling module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fda_api_client import FDAClient


# TTL tiers for PMA data (hours)
PMA_TTL_TIERS = {
    "pma_approval": 168,       # 7 days -- approval data is stable once approved
    "pma_ssed": 0,             # Never expires -- SSED documents are static PDFs
    "pma_supplements": 24,     # 24 hours -- new supplements may appear
    "pma_search": 24,          # 24 hours -- search results may include new approvals
    "pma_sections": 0,         # Never expires -- extraction of static PDFs
}


def _get_pma_cache_dir() -> str:
    """Determine the PMA cache directory from settings or default."""
    settings_path = os.path.expanduser("~/.claude/fda-tools.local.md")
    if os.path.exists(settings_path):
        with open(settings_path) as f:
            m = re.search(r"pma_cache_dir:\s*(.+)", f.read())
            if m:
                return os.path.expanduser(m.group(1).strip())
    return os.path.expanduser("~/fda-510k-data/pma_cache")


class PMADataStore:
    """Structured cache and manifest system for PMA Intelligence data.

    Manages API responses, SSED PDFs, extracted sections, and supplement
    data with TTL-based expiration and manifest tracking.
    """

    def __init__(self, cache_dir: Optional[str] = None, client: Optional[FDAClient] = None):
        """Initialize PMA data store.

        Args:
            cache_dir: Override default cache directory.
            client: Optional pre-configured FDAClient instance.
        """
        self.cache_dir = Path(cache_dir or _get_pma_cache_dir())
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = client or FDAClient()
        self._manifest: Optional[Dict] = None

    # ------------------------------------------------------------------
    # Manifest management
    # ------------------------------------------------------------------

    def get_manifest(self) -> Dict:
        """Load or create the PMA data manifest.

        Returns:
            Manifest dictionary with pma_entries, search_cache, and metadata.
        """
        if self._manifest is not None:
            return self._manifest

        manifest_path = self.cache_dir / "data_manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    self._manifest = json.load(f)
                assert self._manifest is not None  # Type narrowing for Pyright
                return self._manifest
            except (json.JSONDecodeError, OSError):
                pass  # Fall through to create new manifest

        self._manifest = {
            "schema_version": "1.0.0",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "total_pmas": 0,
            "total_sseds_downloaded": 0,
            "total_sections_extracted": 0,
            "pma_entries": {},
            "search_cache": {},
        }
        return self._manifest

    def save_manifest(self) -> None:
        """Save the manifest to disk with atomic write."""
        manifest = self.get_manifest()
        manifest["last_updated"] = datetime.now(timezone.utc).isoformat()

        # Count totals
        entries = manifest.get("pma_entries", {})
        manifest["total_pmas"] = len(entries)
        manifest["total_sseds_downloaded"] = sum(
            1 for e in entries.values() if e.get("ssed_downloaded")
        )
        manifest["total_sections_extracted"] = sum(
            1 for e in entries.values() if e.get("sections_extracted")
        )

        manifest_path = self.cache_dir / "data_manifest.json"
        tmp_path = manifest_path.with_suffix(".json.tmp")
        try:
            with open(tmp_path, "w") as f:
                json.dump(manifest, f, indent=2)
            tmp_path.replace(manifest_path)
        except OSError:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    def update_manifest_entry(self, pma_number: str, updates: Dict) -> None:
        """Update a specific PMA entry in the manifest.

        Args:
            pma_number: PMA number (e.g., 'P170019')
            updates: Dictionary of fields to update/merge.
        """
        manifest = self.get_manifest()
        pma_key = pma_number.upper()

        if pma_key not in manifest["pma_entries"]:
            manifest["pma_entries"][pma_key] = {
                "pma_number": pma_key,
                "first_cached_at": datetime.now(timezone.utc).isoformat(),
            }

        manifest["pma_entries"][pma_key].update(updates)
        manifest["pma_entries"][pma_key]["last_updated"] = datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # TTL expiration
    # ------------------------------------------------------------------

    def is_expired(self, pma_number: str, data_type: str = "pma_approval") -> bool:
        """Check if cached data for a PMA has expired.

        Args:
            pma_number: PMA number
            data_type: One of PMA_TTL_TIERS keys

        Returns:
            True if data is expired or not cached, False otherwise.
        """
        ttl_hours = PMA_TTL_TIERS.get(data_type, 24)

        # TTL of 0 means never expires (SSED docs, extracted sections)
        if ttl_hours == 0:
            manifest = self.get_manifest()
            entry = manifest.get("pma_entries", {}).get(pma_number.upper(), {})
            # Check if data exists at all
            if data_type == "pma_ssed":
                return not entry.get("ssed_downloaded", False)
            elif data_type == "pma_sections":
                return not entry.get("sections_extracted", False)
            return False

        manifest = self.get_manifest()
        entry = manifest.get("pma_entries", {}).get(pma_number.upper(), {})
        fetched_at = entry.get(f"{data_type}_fetched_at", "")

        if not fetched_at:
            return True

        try:
            fetched_time = datetime.fromisoformat(fetched_at)
            if fetched_time.tzinfo is None:
                fetched_time = fetched_time.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - fetched_time).total_seconds() / 3600
            return elapsed > ttl_hours
        except (ValueError, TypeError):
            return True

    # ------------------------------------------------------------------
    # PMA directory management
    # ------------------------------------------------------------------

    def get_pma_dir(self, pma_number: str) -> Path:
        """Get the cache directory for a specific PMA, creating if needed.

        Args:
            pma_number: PMA number (e.g., 'P170019')

        Returns:
            Path to PMA-specific cache directory.
        """
        pma_dir = self.cache_dir / pma_number.upper()
        pma_dir.mkdir(parents=True, exist_ok=True)
        return pma_dir

    # ------------------------------------------------------------------
    # API data (from openFDA)
    # ------------------------------------------------------------------

    def get_pma_data(self, pma_number: str, refresh: bool = False) -> Dict:
        """Get PMA approval data, using cache when available.

        Args:
            pma_number: PMA number (e.g., 'P170019')
            refresh: Force refresh from API, ignoring cache.

        Returns:
            Dictionary with PMA approval data.
        """
        pma_key = pma_number.upper()
        pma_dir = self.get_pma_dir(pma_key)
        data_path = pma_dir / "pma_data.json"

        # Check cache unless refresh is forced
        if not refresh and data_path.exists() and not self.is_expired(pma_key, "pma_approval"):
            try:
                with open(data_path) as f:
                    data = json.load(f)
                return data
            except (json.JSONDecodeError, OSError):
                pass  # Fall through to API fetch

        # Fetch from API
        result = self.client.get_pma(pma_key)

        if result.get("degraded") or result.get("error"):
            # API error -- try stale cache
            if data_path.exists():
                try:
                    with open(data_path) as f:
                        data = json.load(f)
                    data["_cache_status"] = "stale"
                    return data
                except (json.JSONDecodeError, OSError):
                    pass
            return {"error": result.get("error", "API unavailable"), "pma_number": pma_key}

        # Extract and structure data
        pma_data = self._extract_pma_fields(result, pma_key)
        pma_data["_cache_status"] = "fresh"
        pma_data["_fetched_at"] = datetime.now(timezone.utc).isoformat()

        # Save to cache
        self.save_pma_data(pma_key, pma_data)

        # Update manifest
        self.update_manifest_entry(pma_key, {
            "pma_approval_fetched_at": datetime.now(timezone.utc).isoformat(),
            "device_name": pma_data.get("device_name", ""),
            "applicant": pma_data.get("applicant", ""),
            "product_code": pma_data.get("product_code", ""),
            "decision_date": pma_data.get("decision_date", ""),
            "advisory_committee": pma_data.get("advisory_committee", ""),
        })
        self.save_manifest()

        return pma_data

    def save_pma_data(self, pma_number: str, data: Dict) -> None:
        """Save PMA data to the cache.

        Args:
            pma_number: PMA number
            data: PMA data dictionary to save.
        """
        pma_dir = self.get_pma_dir(pma_number.upper())
        data_path = pma_dir / "pma_data.json"
        tmp_path = data_path.with_suffix(".json.tmp")
        try:
            with open(tmp_path, "w") as f:
                json.dump(data, f, indent=2)
            tmp_path.replace(data_path)
        except OSError:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    def _extract_pma_fields(self, api_result: Dict, pma_number: str) -> Dict:
        """Extract structured fields from an openFDA PMA API response.

        Args:
            api_result: Raw API response dict
            pma_number: PMA number for fallback

        Returns:
            Structured PMA data dictionary.
        """
        results = api_result.get("results", [])
        if not results:
            return {"pma_number": pma_number, "error": "No results found"}

        # Find the base PMA record (not a supplement)
        base_record = None
        supplements = []
        for r in results:
            pn = r.get("pma_number", "")
            if "S" in pn[1:]:  # Contains supplement indicator
                supplements.append(r)
            elif base_record is None:
                base_record = r
            else:
                supplements.append(r)

        if base_record is None and results:
            base_record = results[0]

        r = base_record or {}
        return {
            "pma_number": r.get("pma_number", pma_number),
            "applicant": r.get("applicant", "N/A"),
            "device_name": r.get("trade_name", r.get("generic_name", "N/A")),
            "generic_name": r.get("generic_name", "N/A"),
            "product_code": r.get("product_code", "N/A"),
            "decision_date": r.get("decision_date", "N/A"),
            "decision_code": r.get("decision_code", "N/A"),
            "advisory_committee": r.get("advisory_committee", "N/A"),
            "advisory_committee_description": r.get("advisory_committee_description", "N/A"),
            "supplement_number": r.get("supplement_number", ""),
            "supplement_type": r.get("supplement_type", ""),
            "supplement_reason": r.get("supplement_reason", ""),
            "expedited_review_flag": r.get("expedited_review_flag", "N"),
            "ao_statement": r.get("ao_statement", ""),
            "docket_number": r.get("docket_number", ""),
            "fed_reg_notice_date": r.get("fed_reg_notice_date", ""),
            "total_results": api_result.get("meta", {}).get("results", {}).get("total", 0),
            "supplement_count": len(supplements),
            "_raw_results_count": len(results),
        }

    # ------------------------------------------------------------------
    # Supplement data
    # ------------------------------------------------------------------

    def get_supplements(self, pma_number: str, refresh: bool = False) -> List[Dict]:
        """Get all supplements for a PMA.

        Args:
            pma_number: Base PMA number (e.g., 'P170019')
            refresh: Force refresh from API.

        Returns:
            List of supplement dictionaries.
        """
        pma_key = pma_number.upper()
        pma_dir = self.get_pma_dir(pma_key)
        supp_path = pma_dir / "supplements.json"

        # Check cache
        if not refresh and supp_path.exists() and not self.is_expired(pma_key, "pma_supplements"):
            try:
                with open(supp_path) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass

        # Fetch from API
        result = self.client.get_pma_supplements(pma_key, limit=100)

        if result.get("degraded") or result.get("error"):
            if supp_path.exists():
                try:
                    with open(supp_path) as f:
                        return json.load(f)
                except (json.JSONDecodeError, OSError):
                    pass
            return []

        # Extract supplements
        supplements = []
        for r in result.get("results", []):
            pn = r.get("pma_number", "")
            supp_num = r.get("supplement_number", "")
            if supp_num or ("S" in pn[1:]):
                supplements.append({
                    "pma_number": pn,
                    "supplement_number": supp_num,
                    "supplement_type": r.get("supplement_type", ""),
                    "supplement_reason": r.get("supplement_reason", ""),
                    "decision_date": r.get("decision_date", ""),
                    "decision_code": r.get("decision_code", ""),
                    "applicant": r.get("applicant", ""),
                    "trade_name": r.get("trade_name", ""),
                })

        # Save to cache
        try:
            with open(supp_path, "w") as f:
                json.dump(supplements, f, indent=2)
        except OSError:
            pass

        # Update manifest
        self.update_manifest_entry(pma_key, {
            "pma_supplements_fetched_at": datetime.now(timezone.utc).isoformat(),
            "supplement_count": len(supplements),
        })
        self.save_manifest()

        return supplements

    # ------------------------------------------------------------------
    # SSED metadata (download state tracked here, actual download in pma_ssed_cache.py)
    # ------------------------------------------------------------------

    def mark_ssed_downloaded(self, pma_number: str, filepath: str,
                             file_size_kb: int, url: str) -> None:
        """Record that an SSED PDF was downloaded for a PMA.

        Args:
            pma_number: PMA number
            filepath: Path to downloaded PDF
            file_size_kb: File size in KB
            url: URL the SSED was downloaded from
        """
        self.update_manifest_entry(pma_number.upper(), {
            "ssed_downloaded": True,
            "ssed_filepath": filepath,
            "ssed_file_size_kb": file_size_kb,
            "ssed_url": url,
            "ssed_downloaded_at": datetime.now(timezone.utc).isoformat(),
        })
        self.save_manifest()

    def mark_sections_extracted(self, pma_number: str, section_count: int,
                                word_count: int) -> None:
        """Record that sections were extracted from an SSED PDF.

        Args:
            pma_number: PMA number
            section_count: Number of sections extracted
            word_count: Total word count across all sections
        """
        self.update_manifest_entry(pma_number.upper(), {
            "sections_extracted": True,
            "section_count": section_count,
            "total_word_count": word_count,
            "sections_extracted_at": datetime.now(timezone.utc).isoformat(),
        })
        self.save_manifest()

    # ------------------------------------------------------------------
    # Extracted sections
    # ------------------------------------------------------------------

    def get_extracted_sections(self, pma_number: str) -> Optional[Dict]:
        """Load extracted sections for a PMA.

        Args:
            pma_number: PMA number

        Returns:
            Dictionary of extracted sections, or None if not available.
        """
        pma_dir = self.get_pma_dir(pma_number.upper())
        sections_path = pma_dir / "extracted_sections.json"

        if not sections_path.exists():
            return None

        try:
            with open(sections_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def save_extracted_sections(self, pma_number: str, sections: Dict) -> None:
        """Save extracted sections for a PMA.

        Args:
            pma_number: PMA number
            sections: Dictionary of extracted sections.
        """
        pma_dir = self.get_pma_dir(pma_number.upper())
        sections_path = pma_dir / "extracted_sections.json"
        tmp_path = sections_path.with_suffix(".json.tmp")
        try:
            with open(tmp_path, "w") as f:
                json.dump(sections, f, indent=2)
            tmp_path.replace(sections_path)
        except OSError:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
            raise

    # ------------------------------------------------------------------
    # Search cache
    # ------------------------------------------------------------------

    def cache_search_results(self, search_key: str, results: List[Dict]) -> None:
        """Cache PMA search results.

        Args:
            search_key: Canonical search key (e.g., 'product_code:NMH:year:2024')
            results: List of PMA result dicts.
        """
        manifest = self.get_manifest()
        manifest["search_cache"][search_key] = {
            "results": results,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "result_count": len(results),
        }
        self.save_manifest()

    def get_cached_search(self, search_key: str) -> Optional[List[Dict]]:
        """Get cached search results if not expired.

        Args:
            search_key: Canonical search key.

        Returns:
            List of results or None if expired/missing.
        """
        manifest = self.get_manifest()
        entry = manifest.get("search_cache", {}).get(search_key)
        if not entry:
            return None

        fetched_at = entry.get("fetched_at", "")
        ttl_hours = PMA_TTL_TIERS.get("pma_search", 24)

        try:
            fetched_time = datetime.fromisoformat(fetched_at)
            if fetched_time.tzinfo is None:
                fetched_time = fetched_time.replace(tzinfo=timezone.utc)
            elapsed = (datetime.now(timezone.utc) - fetched_time).total_seconds() / 3600
            if elapsed > ttl_hours:
                return None
        except (ValueError, TypeError):
            return None

        return entry.get("results")

    # ------------------------------------------------------------------
    # Listing and stats
    # ------------------------------------------------------------------

    def list_cached_pmas(self) -> List[Dict]:
        """List all cached PMAs with their status.

        Returns:
            List of dicts with pma_number, status fields.
        """
        manifest = self.get_manifest()
        result = []
        for pma_key, entry in manifest.get("pma_entries", {}).items():
            result.append({
                "pma_number": pma_key,
                "device_name": entry.get("device_name", "N/A"),
                "applicant": entry.get("applicant", "N/A"),
                "product_code": entry.get("product_code", "N/A"),
                "decision_date": entry.get("decision_date", "N/A"),
                "ssed_downloaded": entry.get("ssed_downloaded", False),
                "sections_extracted": entry.get("sections_extracted", False),
                "section_count": entry.get("section_count", 0),
                "supplement_count": entry.get("supplement_count", 0),
                "last_updated": entry.get("last_updated", "N/A"),
            })
        return sorted(result, key=lambda x: x.get("decision_date", ""), reverse=True)

    def get_stats(self) -> Dict:
        """Get aggregate statistics for the PMA cache.

        Returns:
            Dictionary with total counts, coverage metrics, etc.
        """
        manifest = self.get_manifest()
        entries = manifest.get("pma_entries", {})

        # Collect product codes
        product_codes = set()
        for entry in entries.values():
            pc = entry.get("product_code", "")
            if pc and pc != "N/A":
                product_codes.add(pc)

        # Calculate total SSED size
        total_ssed_kb = sum(
            entry.get("ssed_file_size_kb", 0) for entry in entries.values()
        )

        return {
            "total_pmas": len(entries),
            "total_sseds_downloaded": sum(
                1 for e in entries.values() if e.get("ssed_downloaded")
            ),
            "total_sections_extracted": sum(
                1 for e in entries.values() if e.get("sections_extracted")
            ),
            "total_ssed_size_mb": round(total_ssed_kb / 1024, 2),
            "unique_product_codes": len(product_codes),
            "product_codes": sorted(product_codes),
            "search_cache_entries": len(manifest.get("search_cache", {})),
            "last_updated": manifest.get("last_updated", "N/A"),
        }

    # ------------------------------------------------------------------
    # Cache maintenance
    # ------------------------------------------------------------------

    def clear_pma(self, pma_number: str) -> bool:
        """Remove all cached data for a specific PMA.

        Args:
            pma_number: PMA number to clear.

        Returns:
            True if data was cleared, False if PMA was not cached.
        """
        import shutil

        pma_key = pma_number.upper()
        pma_dir = self.cache_dir / pma_key

        # Remove directory
        if pma_dir.exists():
            shutil.rmtree(pma_dir)

        # Remove from manifest
        manifest = self.get_manifest()
        removed = manifest.get("pma_entries", {}).pop(pma_key, None)
        if removed:
            self.save_manifest()
            return True
        return False

    def clear_all(self) -> int:
        """Remove all cached PMA data and reset manifest.

        Returns:
            Number of PMAs cleared.
        """
        import shutil

        manifest = self.get_manifest()
        count = len(manifest.get("pma_entries", {}))

        # Remove all PMA directories
        for pma_key in list(manifest.get("pma_entries", {}).keys()):
            pma_dir = self.cache_dir / pma_key
            if pma_dir.exists():
                shutil.rmtree(pma_dir)

        # Reset manifest
        self._manifest = None
        manifest_path = self.cache_dir / "data_manifest.json"
        if manifest_path.exists():
            manifest_path.unlink()

        return count

    def clear_expired_searches(self) -> int:
        """Remove expired search cache entries.

        Returns:
            Number of search entries cleared.
        """
        manifest = self.get_manifest()
        ttl_hours = PMA_TTL_TIERS.get("pma_search", 24)
        now = datetime.now(timezone.utc)
        to_remove = []

        for key, entry in manifest.get("search_cache", {}).items():
            fetched_at = entry.get("fetched_at", "")
            try:
                fetched_time = datetime.fromisoformat(fetched_at)
                if fetched_time.tzinfo is None:
                    fetched_time = fetched_time.replace(tzinfo=timezone.utc)
                elapsed = (now - fetched_time).total_seconds() / 3600
                if elapsed > ttl_hours:
                    to_remove.append(key)
            except (ValueError, TypeError):
                to_remove.append(key)

        for key in to_remove:
            del manifest["search_cache"][key]

        if to_remove:
            self.save_manifest()

        return len(to_remove)


# ------------------------------------------------------------------
# CLI interface
# ------------------------------------------------------------------

def _print_pma_data(data: Dict, cache_status: str = "FRESH") -> None:
    """Print PMA data in structured KEY:VALUE format."""
    print(f"CACHE_STATUS:{cache_status}")
    if data.get("error"):
        print(f"ERROR:{data['error']}")
        return
    print(f"PMA_NUMBER:{data.get('pma_number', 'N/A')}")
    print(f"APPLICANT:{data.get('applicant', 'N/A')}")
    print(f"DEVICE_NAME:{data.get('device_name', 'N/A')}")
    print(f"GENERIC_NAME:{data.get('generic_name', 'N/A')}")
    print(f"PRODUCT_CODE:{data.get('product_code', 'N/A')}")
    print(f"DECISION_DATE:{data.get('decision_date', 'N/A')}")
    print(f"DECISION_CODE:{data.get('decision_code', 'N/A')}")
    print(f"ADVISORY_COMMITTEE:{data.get('advisory_committee', 'N/A')}")
    print(f"ADVISORY_COMMITTEE_DESC:{data.get('advisory_committee_description', 'N/A')}")
    print(f"SUPPLEMENT_COUNT:{data.get('supplement_count', 0)}")
    print(f"EXPEDITED_REVIEW:{data.get('expedited_review_flag', 'N')}")
    print(f"SOURCE:openFDA PMA API")


def _print_manifest(store: PMADataStore) -> None:
    """Print manifest summary."""
    stats = store.get_stats()
    print(f"PMA_CACHE_DIR:{store.cache_dir}")
    print(f"TOTAL_PMAS:{stats['total_pmas']}")
    print(f"SSEDS_DOWNLOADED:{stats['total_sseds_downloaded']}")
    print(f"SECTIONS_EXTRACTED:{stats['total_sections_extracted']}")
    print(f"TOTAL_SSED_SIZE_MB:{stats['total_ssed_size_mb']}")
    print(f"PRODUCT_CODES:{','.join(stats['product_codes']) or 'none'}")
    print(f"SEARCH_CACHE:{stats['search_cache_entries']} entries")
    print(f"LAST_UPDATED:{stats['last_updated']}")
    print("---")

    pmas = store.list_cached_pmas()
    for p in pmas:
        ssed = "SSED" if p["ssed_downloaded"] else "no-SSED"
        sections = f"{p['section_count']}sec" if p["sections_extracted"] else "no-sections"
        print(f"PMA:{p['pma_number']}|{p['device_name'][:40]}|{p['product_code']}|{p['decision_date']}|{ssed}|{sections}")


def main():
    parser = argparse.ArgumentParser(
        description="PMA Data Store -- Structured cache for PMA Intelligence"
    )
    parser.add_argument("--pma", help="PMA number to look up (e.g., P170019)")
    parser.add_argument("--product-code", dest="product_code", help="Search by product code")
    parser.add_argument("--year", type=int, help="Filter by approval year")
    parser.add_argument("--refresh", action="store_true", help="Force refresh from API")
    parser.add_argument("--show-manifest", action="store_true", dest="show_manifest",
                        help="Show cache manifest summary")
    parser.add_argument("--stats", action="store_true", help="Show cache statistics")
    parser.add_argument("--clear", help="Clear cached data for a specific PMA")
    parser.add_argument("--clear-all", action="store_true", dest="clear_all",
                        help="Clear ALL cached PMA data")

    args = parser.parse_args()
    store = PMADataStore()

    if args.show_manifest:
        _print_manifest(store)
    elif args.stats:
        stats = store.get_stats()
        print(json.dumps(stats, indent=2))
    elif args.clear_all:
        count = store.clear_all()
        print(f"CLEARED:{count} PMAs removed from cache")
    elif args.clear:
        removed = store.clear_pma(args.clear)
        if removed:
            print(f"CLEARED:{args.clear} removed from cache")
        else:
            print(f"NOT_FOUND:{args.clear} was not in cache")
    elif args.pma:
        data = store.get_pma_data(args.pma, refresh=args.refresh)
        status = data.get("_cache_status", "fresh")
        _print_pma_data(data, status.upper())
    elif args.product_code:
        result = store.client.search_pma(
            product_code=args.product_code,
            year_start=args.year,
            year_end=args.year,
            limit=50,
        )
        if result.get("degraded"):
            print(f"ERROR:{result.get('error')}")
            return
        total = result.get("meta", {}).get("results", {}).get("total", 0)
        print(f"TOTAL_PMAS:{total}")
        for r in result.get("results", []):
            pn = r.get("pma_number", "N/A")
            name = r.get("trade_name", r.get("generic_name", "N/A"))[:50]
            date = r.get("decision_date", "N/A")
            code = r.get("decision_code", "N/A")
            print(f"PMA:{pn}|{name}|{date}|{code}")
    else:
        parser.error("Specify --pma, --product-code, --show-manifest, --stats, --clear, or --clear-all")


if __name__ == "__main__":
    main()
