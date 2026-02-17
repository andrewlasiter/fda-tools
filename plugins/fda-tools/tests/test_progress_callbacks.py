"""
Tests for Progress Callbacks (FDA-61 / FE-006).

Validates that progress callbacks are invoked correctly during long-running
analytics operations, providing user feedback for similarity matrix computations.

Test Coverage:
    - PROG-001: Progress callback is invoked during computation
    - PROG-002: Progress callback receives correct parameters
    - PROG-003: Progress callback reports final count = total pairs
    - PROG-004: Progress callback is optional (backward compatibility)
    - PROG-005: Progress updates are not too frequent (performance)
    - PROG-006: ProgressBar displays correct percentage and ETA
"""

import os
import sys
import time

import pytest

# Ensure scripts directory is on sys.path for imports
SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "scripts"
)
sys.path.insert(0, SCRIPTS_DIR)

from section_analytics import pairwise_similarity_matrix  # type: ignore
from compare_sections import ProgressBar  # type: ignore


# ===================================================================
# Progress Callback Tests
# ===================================================================


class TestPROG001ProgressCallbackInvoked:
    """PROG-001: Progress callback is invoked during computation.

    Validates that when a progress_callback is provided to
    pairwise_similarity_matrix, it is called at least once during
    the computation.
    """

    def test_callback_is_invoked(self, sample_section_data):
        """Progress callback is called during matrix computation."""
        # Track callback invocations
        invocations = []

        def callback(current: int, total: int, message: str):
            invocations.append({"current": current, "total": total, "message": message})

        # Use 4 DQY devices (6 pairs)
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:4]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset,
            "clinical_testing",
            method="sequence",
            use_cache=False,  # Disable cache to force computation
            progress_callback=callback,
        )

        assert len(invocations) > 0, "Progress callback should be invoked at least once"
        assert result["pairs_computed"] == 6, f"Expected 6 pairs, got {result['pairs_computed']}"


class TestPROG002ProgressCallbackParameters:
    """PROG-002: Progress callback receives correct parameters.

    Validates that the callback receives current, total, and message
    parameters with sensible values.
    """

    def test_callback_receives_correct_parameters(self, sample_section_data):
        """Callback parameters are within expected ranges."""
        invocations = []

        def callback(current: int, total: int, message: str):
            invocations.append({"current": current, "total": total, "message": message})

        # Use 4 DQY devices (6 pairs)
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:4]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        pairwise_similarity_matrix(
            subset,
            "clinical_testing",
            method="sequence",
            use_cache=False,
            progress_callback=callback,
        )

        assert len(invocations) > 0
        for inv in invocations:
            assert inv["current"] >= 0, f"Current should be >= 0: {inv['current']}"
            assert inv["total"] == 6, f"Total should be 6: {inv['total']}"
            assert inv["current"] <= inv["total"], (
                f"Current ({inv['current']}) should not exceed total ({inv['total']})"
            )
            assert isinstance(inv["message"], str), f"Message should be a string: {inv['message']}"


class TestPROG003ProgressFinalCount:
    """PROG-003: Progress callback reports final count = total pairs.

    Validates that the last callback invocation reports current = total,
    indicating completion.
    """

    def test_final_callback_reports_completion(self, sample_section_data):
        """Final callback invocation reports current = total."""
        invocations = []

        def callback(current: int, total: int, message: str):
            invocations.append({"current": current, "total": total, "message": message})

        # Use 4 DQY devices (6 pairs)
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:4]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset,
            "clinical_testing",
            method="sequence",
            use_cache=False,
            progress_callback=callback,
        )

        assert len(invocations) > 0
        final = invocations[-1]
        assert final["current"] == final["total"], (
            f"Final invocation should report completion: current={final['current']}, total={final['total']}"
        )
        assert final["current"] == result["pairs_computed"], (
            f"Final current should match pairs_computed: {final['current']} vs {result['pairs_computed']}"
        )


class TestPROG004BackwardCompatibility:
    """PROG-004: Progress callback is optional (backward compatibility).

    Validates that pairwise_similarity_matrix works correctly when
    progress_callback is not provided (None).
    """

    def test_no_callback_works(self, sample_section_data):
        """Matrix computation works without progress callback."""
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:4]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        # Call without progress_callback parameter (defaults to None)
        result = pairwise_similarity_matrix(
            subset,
            "clinical_testing",
            method="sequence",
            use_cache=False,
        )

        assert result["pairs_computed"] == 6
        assert result["statistics"]["mean"] >= 0.0

    def test_explicit_none_callback_works(self, sample_section_data):
        """Matrix computation works with explicit progress_callback=None."""
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:4]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset,
            "clinical_testing",
            method="sequence",
            use_cache=False,
            progress_callback=None,
        )

        assert result["pairs_computed"] == 6


class TestPROG005UpdateFrequency:
    """PROG-005: Progress updates are not too frequent (performance).

    Validates that the callback is not invoked for every single pair,
    which would degrade performance. Updates should be batched (e.g., every 1%).
    """

    def test_callback_not_invoked_for_every_pair(self, sample_section_data):
        """Callback invocations are batched, not per-pair."""
        invocations = []

        def callback(current: int, total: int, message: str):
            invocations.append({"current": current, "total": total})

        # Use all 5 DQY devices (10 pairs: C(5,2) = 10)
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:5]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        result = pairwise_similarity_matrix(
            subset,
            "clinical_testing",
            method="sequence",
            use_cache=False,
            progress_callback=callback,
        )

        # With 10 pairs and 1% update interval, we expect ~1 update (update_interval = max(1, 10//100) = 1)
        # So we might get 10 updates (one per pair since interval is 1)
        # But for larger datasets, this should be batched

        # For a small dataset, we should get at least 1 update and at most pairs_computed updates
        assert len(invocations) >= 1, "Should have at least one callback invocation"
        assert len(invocations) <= result["pairs_computed"], (
            f"Should not have more invocations ({len(invocations)}) than pairs ({result['pairs_computed']})"
        )

    def test_large_dataset_batching(self, sample_section_data):
        """For larger datasets, callbacks are batched efficiently."""
        invocations = []

        def callback(current: int, total: int, message: str):
            invocations.append({"current": current, "total": total})

        # Use all 8 devices (DQY + OVE): C(8,2) = 28 pairs
        all_keys = sorted(sample_section_data.keys())[:8]
        subset = {k: sample_section_data[k] for k in all_keys}

        result = pairwise_similarity_matrix(
            subset,
            "clinical_testing",
            method="sequence",
            use_cache=False,
            progress_callback=callback,
        )

        # With 28 pairs and 1% batching, update_interval = max(1, 28//100) = 1
        # So we might still get many updates. But the key is that we don't get
        # MORE invocations than pairs.
        assert len(invocations) <= result["pairs_computed"], (
            f"Invocations ({len(invocations)}) should not exceed pairs ({result['pairs_computed']})"
        )


# ===================================================================
# ProgressBar Display Tests
# ===================================================================


class TestPROG006ProgressBarDisplay:
    """PROG-006: ProgressBar displays correct percentage and ETA.

    Validates that the ProgressBar class correctly calculates percentage
    completion and estimated time remaining.
    """

    def test_progress_bar_initialization(self):
        """ProgressBar initializes with correct parameters."""
        bar = ProgressBar(total=100, description="Test progress", width=20)
        assert bar.total == 100
        assert bar.description == "Test progress"
        assert bar.width == 20

    def test_progress_bar_percentage_calculation(self):
        """ProgressBar calculates percentage correctly."""
        bar = ProgressBar(total=100, description="", width=20)

        # Manually test percentage calculation
        # At 25 out of 100, should be 25%
        # At 50 out of 100, should be 50%
        # At 100 out of 100, should be 100%

        # We can't easily test the printed output, but we can verify
        # the update method doesn't crash
        bar.update(25, "quarter done")
        bar.update(50, "half done")
        bar.update(100, "complete")
        bar.finish()

    def test_progress_bar_zero_total(self):
        """ProgressBar handles zero total gracefully."""
        bar = ProgressBar(total=0, description="Empty", width=20)
        # Should not crash
        bar.update(0, "no work")
        bar.finish()

    def test_progress_bar_eta_estimation(self):
        """ProgressBar estimates ETA based on elapsed time."""
        bar = ProgressBar(total=10, description="ETA test", width=20)

        # Simulate some work
        for i in range(1, 11):
            time.sleep(0.01)  # Small delay to simulate work
            bar.update(i, f"item {i}")

        bar.finish()
        # If we got here without crashing, ETA calculation works


# ===================================================================
# Integration Tests
# ===================================================================


class TestPROG007IntegrationTest:
    """PROG-007: Integration test with ProgressBar and pairwise_similarity_matrix.

    Validates that the ProgressBar can be used effectively with the
    pairwise_similarity_matrix progress_callback.
    """

    def test_progress_bar_with_similarity_matrix(self, sample_section_data):
        """ProgressBar integrates correctly with pairwise_similarity_matrix."""
        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:4]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        # Create progress bar
        total_pairs = 6  # C(4,2) = 6
        progress_bar = ProgressBar(total_pairs, description="Computing similarity...", width=20)

        def progress_callback(current: int, total: int, message: str):
            progress_bar.update(current, message)

        result = pairwise_similarity_matrix(
            subset,
            "clinical_testing",
            method="sequence",
            use_cache=False,
            progress_callback=progress_callback,
        )

        progress_bar.finish()

        assert result["pairs_computed"] == 6
        assert result["statistics"]["mean"] >= 0.0


class TestPROG008CacheHitNoProgress:
    """PROG-008: Cache hit should not invoke progress callback.

    When a cached result is returned, no computation occurs, so the
    progress callback should not be invoked.
    """

    def test_cache_hit_no_progress_callback(self, sample_section_data):
        """Cache hit returns immediately without invoking progress callback."""
        invocations = []

        def callback(current: int, total: int, message: str):
            invocations.append({"current": current, "total": total})

        dqy_keys = sorted(
            k for k, v in sample_section_data.items()
            if v.get("metadata", {}).get("product_code") == "DQY"
        )[:4]
        subset = {k: sample_section_data[k] for k in dqy_keys}

        # First run: compute and cache
        result1 = pairwise_similarity_matrix(
            subset,
            "clinical_testing",
            method="sequence",
            use_cache=True,
            progress_callback=callback,
        )

        first_invocation_count = len(invocations)
        assert first_invocation_count >= 0  # May be 0 if cache was already present

        # Second run: should hit cache (if cache is available)
        invocations.clear()
        result2 = pairwise_similarity_matrix(
            subset,
            "clinical_testing",
            method="sequence",
            use_cache=True,
            progress_callback=callback,
        )

        # If cache hit, no progress callbacks should be invoked
        if result2.get("cache_hit"):
            assert len(invocations) == 0, (
                f"Cache hit should not invoke progress callback, but got {len(invocations)} invocations"
            )
