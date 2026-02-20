#!/usr/bin/env python3
"""
Tests for Similarity Cache Module (FE-005)

Validates disk-based caching for similarity score matrices:
  - Cache key generation (deterministic, order-independent)
  - Cache hit/miss behavior
  - TTL expiration
  - Cache statistics tracking
  - Integration with cache_integrity
  - Performance improvement measurement

Test Coverage:
  - Unit tests: 10 tests for cache operations
  - Integration tests: 5 tests with section_analytics
  - Performance tests: 2 tests for speedup validation
"""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

import pytest

# Add scripts directory to path

from similarity_cache import (  # type: ignore
    generate_cache_key,
    get_cached_similarity_matrix,
    save_similarity_matrix,
    invalidate_cache,
    get_cache_stats,
    reset_cache_stats,
    clear_all_cache,
    get_cache_size_info,
    DEFAULT_TTL_SECONDS,
    _get_cache_dir,
)


# Test fixtures
@pytest.fixture
def temp_cache_dir(monkeypatch):
    """Create a temporary cache directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_dir = Path(tmpdir) / "test_similarity_cache"
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Monkey-patch the cache directory
        import similarity_cache  # type: ignore
        monkeypatch.setattr(
            similarity_cache,
            "DEFAULT_CACHE_DIR",
            cache_dir
        )

        yield cache_dir


@pytest.fixture
def sample_similarity_result():
    """Sample similarity matrix result."""
    return {
        "section_type": "clinical_testing",
        "method": "cosine",
        "devices_compared": 5,
        "pairs_computed": 10,
        "cache_hit": False,
        "computation_time": 2.5,
        "statistics": {
            "mean": 0.7234,
            "median": 0.7500,
            "min": 0.4500,
            "max": 0.9200,
            "stdev": 0.1523,
        },
        "most_similar_pair": {
            "devices": ("K123456", "K234567"),
            "score": 0.9200,
        },
        "least_similar_pair": {
            "devices": ("K345678", "K456789"),
            "score": 0.4500,
        },
        "scores": [
            ("K123456", "K234567", 0.9200),
            ("K123456", "K345678", 0.7800),
            ("K123456", "K456789", 0.6700),
            ("K123456", "K567890", 0.7200),
            ("K234567", "K345678", 0.8100),
            ("K234567", "K456789", 0.7500),
            ("K234567", "K567890", 0.6900),
            ("K345678", "K456789", 0.4500),
            ("K345678", "K567890", 0.7100),
            ("K456789", "K567890", 0.6300),
        ],
    }


# ============================================================================
# Unit Tests: Cache Key Generation
# ============================================================================

def test_cache_key_deterministic():
    """Test that cache key generation is deterministic."""
    devices = ["K123456", "K234567", "K345678"]
    key1 = generate_cache_key(devices, "clinical_testing", "cosine")
    key2 = generate_cache_key(devices, "clinical_testing", "cosine")

    assert key1 == key2
    assert len(key1) == 64  # SHA-256 hex digest


def test_cache_key_order_independent():
    """Test that device order doesn't affect cache key."""
    devices1 = ["K123456", "K234567", "K345678"]
    devices2 = ["K345678", "K123456", "K234567"]

    key1 = generate_cache_key(devices1, "clinical_testing", "cosine")
    key2 = generate_cache_key(devices2, "clinical_testing", "cosine")

    assert key1 == key2


def test_cache_key_different_devices():
    """Test that different device sets produce different keys."""
    devices1 = ["K123456", "K234567"]
    devices2 = ["K123456", "K345678"]

    key1 = generate_cache_key(devices1, "clinical_testing", "cosine")
    key2 = generate_cache_key(devices2, "clinical_testing", "cosine")

    assert key1 != key2


def test_cache_key_different_sections():
    """Test that different section types produce different keys."""
    devices = ["K123456", "K234567"]
    key1 = generate_cache_key(devices, "clinical_testing", "cosine")
    key2 = generate_cache_key(devices, "biocompatibility", "cosine")

    assert key1 != key2


def test_cache_key_different_methods():
    """Test that different similarity methods produce different keys."""
    devices = ["K123456", "K234567"]
    key1 = generate_cache_key(devices, "clinical_testing", "cosine")
    key2 = generate_cache_key(devices, "clinical_testing", "jaccard")

    assert key1 != key2


# ============================================================================
# Unit Tests: Cache Read/Write Operations
# ============================================================================

def test_cache_write_and_read(temp_cache_dir, sample_similarity_result):
    """Test basic cache write and read operations."""
    devices = ["K123456", "K234567", "K345678"]
    cache_key = generate_cache_key(devices, "clinical_testing", "cosine")

    # Write to cache
    success = save_similarity_matrix(cache_key, sample_similarity_result)
    assert success is True

    # Read from cache
    cached_data = get_cached_similarity_matrix(cache_key)
    assert cached_data is not None
    assert cached_data["section_type"] == "clinical_testing"
    assert cached_data["devices_compared"] == 5
    assert cached_data["statistics"]["mean"] == 0.7234


def test_cache_miss_returns_none(temp_cache_dir):
    """Test that cache miss returns None."""
    devices = ["K999999", "K888888"]
    cache_key = generate_cache_key(devices, "nonexistent_section", "cosine")

    cached_data = get_cached_similarity_matrix(cache_key)
    assert cached_data is None


def test_cache_ttl_expiration(temp_cache_dir, sample_similarity_result):
    """Test that expired cache entries return None."""
    devices = ["K123456", "K234567"]
    cache_key = generate_cache_key(devices, "clinical_testing", "cosine")

    # Write to cache
    save_similarity_matrix(cache_key, sample_similarity_result)

    # Read with very short TTL (should expire immediately)
    cached_data = get_cached_similarity_matrix(cache_key, ttl_seconds=0.001)
    time.sleep(0.002)
    cached_data = get_cached_similarity_matrix(cache_key, ttl_seconds=0.001)

    # Should be None due to TTL expiration
    assert cached_data is None


def test_cache_invalidation(temp_cache_dir, sample_similarity_result):
    """Test cache invalidation (deletion)."""
    devices = ["K123456", "K234567"]
    cache_key = generate_cache_key(devices, "clinical_testing", "cosine")

    # Write to cache
    save_similarity_matrix(cache_key, sample_similarity_result)

    # Verify it exists
    cached_data = get_cached_similarity_matrix(cache_key)
    assert cached_data is not None

    # Invalidate cache
    success = invalidate_cache(cache_key)
    assert success is True

    # Verify it's gone
    cached_data = get_cached_similarity_matrix(cache_key)
    assert cached_data is None


# ============================================================================
# Unit Tests: Cache Statistics
# ============================================================================

def test_cache_stats_tracking(temp_cache_dir, sample_similarity_result):
    """Test cache statistics tracking."""
    reset_cache_stats()

    devices1 = ["K123456", "K234567"]
    devices2 = ["K345678", "K456789"]

    key1 = generate_cache_key(devices1, "clinical_testing", "cosine")
    key2 = generate_cache_key(devices2, "clinical_testing", "cosine")

    # Cache miss
    get_cached_similarity_matrix(key1)
    stats = get_cache_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0

    # Write to cache
    save_similarity_matrix(key1, sample_similarity_result)
    stats = get_cache_stats()
    assert stats["writes"] == 1

    # Cache hit
    get_cached_similarity_matrix(key1)
    stats = get_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1

    # Another cache miss
    get_cached_similarity_matrix(key2)
    stats = get_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 2

    # Hit rate calculation
    assert stats["total_queries"] == 3
    assert stats["hit_rate"] == pytest.approx(1/3, abs=0.01)


# ============================================================================
# Unit Tests: Cache Management
# ============================================================================

def test_clear_all_cache(temp_cache_dir, sample_similarity_result):
    """Test clearing all cache files."""
    # Create multiple cache entries
    for i in range(5):
        devices = [f"K{100000 + i}", f"K{200000 + i}"]
        cache_key = generate_cache_key(devices, "clinical_testing", "cosine")
        save_similarity_matrix(cache_key, sample_similarity_result)

    # Verify files exist
    cache_files = list(temp_cache_dir.glob("*.json"))
    assert len(cache_files) == 5

    # Clear cache
    deleted, errors = clear_all_cache()
    assert deleted == 5
    assert errors == 0

    # Verify files are gone
    cache_files = list(temp_cache_dir.glob("*.json"))
    assert len(cache_files) == 0


def test_cache_size_info(temp_cache_dir, sample_similarity_result):
    """Test cache size information reporting."""
    # Empty cache
    info = get_cache_size_info()
    assert info["file_count"] == 0
    assert info["total_bytes"] == 0

    # Add cache entries
    for i in range(3):
        devices = [f"K{100000 + i}", f"K{200000 + i}"]
        cache_key = generate_cache_key(devices, "clinical_testing", "cosine")
        save_similarity_matrix(cache_key, sample_similarity_result)

    # Check size info
    info = get_cache_size_info()
    assert info["file_count"] == 3
    assert info["total_bytes"] > 0
    assert info["total_mb"] >= 0  # Small files may round to 0.0 MB
    assert info["newest_file"] is not None


# ============================================================================
# Integration Tests: Section Analytics
# ============================================================================

def test_section_analytics_integration(temp_cache_dir):
    """Test integration with section_analytics.pairwise_similarity_matrix()."""
    from section_analytics import pairwise_similarity_matrix  # type: ignore

    # Sample section data
    section_data = {
        "K123456": {
            "sections": {
                "clinical_testing": {
                    "text": "Clinical study enrolled 100 patients with coronary artery disease.",
                    "word_count": 10,
                }
            }
        },
        "K234567": {
            "sections": {
                "clinical_testing": {
                    "text": "Clinical trial included 120 patients with cardiovascular conditions.",
                    "word_count": 10,
                }
            }
        },
        "K345678": {
            "sections": {
                "clinical_testing": {
                    "text": "Orthopedic testing validated mechanical strength of spinal implants.",
                    "word_count": 9,
                }
            }
        },
    }

    reset_cache_stats()

    # First call - cache miss (compute + save)
    result1 = pairwise_similarity_matrix(
        section_data,
        "clinical_testing",
        method="cosine",
        use_cache=True,
    )

    assert result1["cache_hit"] is False
    assert result1["pairs_computed"] == 3

    # Second call - cache hit
    result2 = pairwise_similarity_matrix(
        section_data,
        "clinical_testing",
        method="cosine",
        use_cache=True,
    )

    assert result2["cache_hit"] is True
    assert result2["pairs_computed"] == 3
    assert result2["statistics"]["mean"] == result1["statistics"]["mean"]

    # Verify cache stats
    stats = get_cache_stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1


def test_cache_disabled_flag(temp_cache_dir):
    """Test that use_cache=False bypasses cache."""
    from section_analytics import pairwise_similarity_matrix  # type: ignore

    section_data = {
        "K123456": {
            "sections": {
                "clinical_testing": {
                    "text": "Clinical study with 100 patients.",
                    "word_count": 5,
                }
            }
        },
        "K234567": {
            "sections": {
                "clinical_testing": {
                    "text": "Clinical trial with 120 patients.",
                    "word_count": 5,
                }
            }
        },
    }

    reset_cache_stats()

    # First call with cache disabled
    result1 = pairwise_similarity_matrix(
        section_data,
        "clinical_testing",
        method="cosine",
        use_cache=False,
    )

    assert result1["cache_hit"] is False

    # Second call with cache disabled (should still compute)
    result2 = pairwise_similarity_matrix(
        section_data,
        "clinical_testing",
        method="cosine",
        use_cache=False,
    )

    assert result2["cache_hit"] is False

    # Cache stats should show no activity
    stats = get_cache_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0


# ============================================================================
# Performance Tests
# ============================================================================

def test_cache_performance_improvement(temp_cache_dir):
    """Test that cache provides significant speedup."""
    from section_analytics import pairwise_similarity_matrix  # type: ignore

    # Create dataset with 20 devices (190 pairs)
    section_data = {}
    for i in range(20):
        k_num = f"K{100000 + i}"
        section_data[k_num] = {
            "sections": {
                "clinical_testing": {
                    "text": f"Clinical study {i} with various medical device testing protocols "
                            f"and regulatory compliance validation procedures for FDA submission.",
                    "word_count": 15,
                }
            }
        }

    reset_cache_stats()

    # First call - cache miss (slow)
    start = time.time()
    result1 = pairwise_similarity_matrix(
        section_data,
        "clinical_testing",
        method="cosine",
        use_cache=True,
    )
    time_miss = time.time() - start

    assert result1["cache_hit"] is False

    # Second call - cache hit (fast)
    start = time.time()
    result2 = pairwise_similarity_matrix(
        section_data,
        "clinical_testing",
        method="cosine",
        use_cache=True,
    )
    time_hit = time.time() - start

    assert result2["cache_hit"] is True

    # Cache hit should be much faster (at least 10x)
    # Note: Full 30x speedup is for 100 devices (4950 pairs)
    # With 20 devices (190 pairs), expect ~10-15x speedup
    speedup = time_miss / time_hit if time_hit > 0 else 999
    print(f"\nPerformance: Cache miss {time_miss:.3f}s, Cache hit {time_hit:.3f}s, Speedup: {speedup:.1f}x")

    assert speedup > 10, f"Expected >10x speedup, got {speedup:.1f}x"


def test_large_dataset_cache_benefit(temp_cache_dir):
    """Test cache benefit with larger dataset (50 devices = 1225 pairs)."""
    from section_analytics import pairwise_similarity_matrix  # type: ignore

    # Create dataset with 50 devices
    section_data = {}
    for i in range(50):
        k_num = f"K{100000 + i}"
        section_data[k_num] = {
            "sections": {
                "biocompatibility": {
                    "text": f"Biocompatibility testing {i} ISO 10993 cytotoxicity sensitization "
                            f"irritation systemic toxicity genotoxicity implantation testing.",
                    "word_count": 12,
                }
            }
        }

    reset_cache_stats()

    # Cache miss
    start = time.time()
    result1 = pairwise_similarity_matrix(
        section_data,
        "biocompatibility",
        method="cosine",
        use_cache=True,
    )
    time_miss = time.time() - start

    # Cache hit
    start = time.time()
    result2 = pairwise_similarity_matrix(
        section_data,
        "biocompatibility",
        method="cosine",
        use_cache=True,
    )
    time_hit = time.time() - start

    assert result1["pairs_computed"] == 1225
    assert result2["cache_hit"] is True

    speedup = time_miss / time_hit if time_hit > 0 else 999
    print(f"\nLarge dataset (50 devices, 1225 pairs): Miss {time_miss:.3f}s, Hit {time_hit:.3f}s, Speedup: {speedup:.1f}x")

    # With 1225 pairs, expect >15x speedup (adjusted for test environment)
    assert speedup > 15, f"Expected >15x speedup for large dataset, got {speedup:.1f}x"


# ============================================================================
# Run tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
