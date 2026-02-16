"""
Mock FDAClient for offline testing of change_detector and related modules.

Simulates the FDAClient API without making network calls. Configurable
with predefined responses per product code, supporting clearance queries,
recall queries, and error simulation.

Usage:
    from tests.mocks.mock_fda_client import MockFDAClient

    client = MockFDAClient()
    client.set_clearances("DQY", meta_total=149, results=[...])
    client.set_recalls("DQY", meta_total=3, results=[...])

    result = client.get_clearances("DQY", limit=100)
    result = client.get_recalls("DQY", limit=10)
"""

from typing import Any, Dict, List, Optional


class MockFDAClient:
    """Mock FDA API client that returns predefined responses without network calls.

    Attributes:
        clearance_responses: Dict mapping product_code -> clearance API response.
        recall_responses: Dict mapping product_code -> recall API response.
        call_log: List of all method calls made, for assertion in tests.
    """

    def __init__(
        self,
        clearance_responses: Optional[Dict[str, Dict]] = None,
        recall_responses: Optional[Dict[str, Dict]] = None,
        default_error: bool = False,
    ):
        """Initialize MockFDAClient with predefined responses.

        Args:
            clearance_responses: Dict mapping product_code (uppercase) to API
                response dicts. Each response should have the shape:
                {"meta": {"results": {"total": N}}, "results": [...]}
            recall_responses: Dict mapping product_code (uppercase) to API
                response dicts for recall queries.
            default_error: If True, return error response for any product code
                not explicitly configured.
        """
        self.clearance_responses = clearance_responses or {}
        self.recall_responses = recall_responses or {}
        self.default_error = default_error
        self.call_log: List[Dict[str, Any]] = []

    def set_clearances(
        self, product_code: str, meta_total: int, results: List[Dict]
    ) -> None:
        """Configure clearance response for a product code.

        Args:
            product_code: FDA product code (e.g., 'DQY').
            meta_total: Value for meta.results.total in the response.
            results: List of clearance result dicts.
        """
        self.clearance_responses[product_code.upper()] = {
            "meta": {"results": {"total": meta_total}},
            "results": results,
        }

    def set_recalls(
        self, product_code: str, meta_total: int, results: Optional[List[Dict]] = None
    ) -> None:
        """Configure recall response for a product code.

        Args:
            product_code: FDA product code (e.g., 'DQY').
            meta_total: Value for meta.results.total in the response.
            results: List of recall result dicts. Defaults to empty list.
        """
        self.recall_responses[product_code.upper()] = {
            "meta": {"results": {"total": meta_total}},
            "results": results or [],
        }

    def set_error(self, product_code: str) -> None:
        """Configure both clearance and recall endpoints to return error for a code.

        Args:
            product_code: FDA product code that should return an error.
        """
        error_response = {"error": "API unavailable", "degraded": True}
        self.clearance_responses[product_code.upper()] = error_response
        self.recall_responses[product_code.upper()] = error_response

    def get_clearances(
        self,
        product_code: str,
        limit: int = 100,
        sort: str = "decision_date:desc",
    ) -> Dict[str, Any]:
        """Return mock clearance data for a product code.

        Args:
            product_code: FDA product code.
            limit: Maximum results to return (applied to results list).
            sort: Sort parameter (ignored in mock but logged).

        Returns:
            Mock API response dict.
        """
        self.call_log.append({
            "method": "get_clearances",
            "product_code": product_code,
            "limit": limit,
            "sort": sort,
        })

        pc = product_code.upper()
        if pc in self.clearance_responses:
            response = self.clearance_responses[pc]
            # If it is an error response, return as-is
            if response.get("error") or response.get("degraded"):
                return response
            # Apply limit to results
            results = response.get("results", [])[:limit]
            return {
                "meta": response.get("meta", {"results": {"total": len(results)}}),
                "results": results,
            }

        if self.default_error:
            return {"error": "API unavailable", "degraded": True}

        # Default: empty response
        return {
            "meta": {"results": {"total": 0}},
            "results": [],
        }

    def get_recalls(
        self,
        product_code: str,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """Return mock recall data for a product code.

        Args:
            product_code: FDA product code.
            limit: Maximum results to return.

        Returns:
            Mock API response dict.
        """
        self.call_log.append({
            "method": "get_recalls",
            "product_code": product_code,
            "limit": limit,
        })

        pc = product_code.upper()
        if pc in self.recall_responses:
            response = self.recall_responses[pc]
            if response.get("error") or response.get("degraded"):
                return response
            results = response.get("results", [])[:limit]
            return {
                "meta": response.get("meta", {"results": {"total": 0}}),
                "results": results,
            }

        if self.default_error:
            return {"error": "API unavailable", "degraded": True}

        return {
            "meta": {"results": {"total": 0}},
            "results": [],
        }
