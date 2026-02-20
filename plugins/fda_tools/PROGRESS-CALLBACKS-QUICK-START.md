# Progress Callbacks - Quick Start Guide

## For End Users

### Using Progress Bars in CLI

Progress bars are **automatically enabled** when running similarity analysis:

```bash
# Progress bar shows automatically (verbose mode is default)
python3 compare_sections.py --product-code DQY --sections clinical --similarity

# Disable progress bar (quiet mode)
python3 compare_sections.py --product-code DQY --sections clinical --similarity --quiet
```

**Example Output:**
```
Computing similarity for clinical_testing...
[████████████░░░░░░░░░░░░░░░░░░] 75% (3712/4950 pairs) ETA: 15s
  clinical_testing: mean=0.742, stdev=0.103, pairs=4950, computed (60.24s)
```

### Demo Script

Try the interactive demo to see progress bars in action:

```bash
# Basic demo (30 devices, 435 pairs)
python3 scripts/demo_progress_bar.py --devices 30

# Large dataset demo (100 devices, 4950 pairs)
python3 scripts/demo_progress_bar.py --devices 100

# Compare with/without progress
python3 scripts/demo_progress_bar.py --devices 50 --no-progress
```

## For Developers

### Using Progress Callbacks in Code

#### Basic Usage

```python
from section_analytics import pairwise_similarity_matrix
from compare_sections import ProgressBar

# Prepare your data
section_data = {...}  # K-number -> device data

# Create progress bar
total_pairs = (n_devices * (n_devices - 1)) // 2
progress_bar = ProgressBar(total_pairs, description="Computing similarity...")

# Define callback
def progress_callback(current: int, total: int, message: str):
    progress_bar.update(current, message)

# Compute with progress
result = pairwise_similarity_matrix(
    section_data,
    "clinical_testing",
    method="cosine",
    progress_callback=progress_callback
)

progress_bar.finish()
```

#### Custom Callback (No Visual Display)

```python
def my_callback(current: int, total: int, message: str):
    # Log progress to file
    with open("progress.log", "a") as f:
        pct = int((current / total) * 100)
        f.write(f"{pct}% complete: {current}/{total} pairs\n")

result = pairwise_similarity_matrix(
    section_data,
    "clinical_testing",
    progress_callback=my_callback
)
```

#### Backward Compatible (No Callback)

```python
# Works exactly as before - no progress reporting
result = pairwise_similarity_matrix(
    section_data,
    "clinical_testing",
    method="cosine"
)
```

### Callback Signature

```python
def callback(current: int, total: int, message: str) -> None:
    """
    Args:
        current: Number of pairs computed so far (1-based)
        total: Total number of pairs to compute
        message: Status message (e.g., "Computing similarity")
    """
    pass
```

### ProgressBar Class API

```python
class ProgressBar:
    def __init__(self, total: int, description: str = "", width: int = 20):
        """
        Args:
            total: Total number of items to process
            description: Description displayed above progress bar
            width: Width of progress bar in characters (default: 20)
        """

    def update(self, current: int, message: str = ""):
        """Update progress bar.

        Args:
            current: Current item count
            message: Optional additional message
        """

    def finish(self):
        """Complete progress bar and move to next line."""
```

### Example: Adding Progress to New Function

```python
def my_long_running_function(data, progress_callback=None):
    """Your function that takes a long time.

    Args:
        data: Input data
        progress_callback: Optional progress callback
    """
    total_items = len(data)

    for i, item in enumerate(data):
        # Do your work
        result = process(item)

        # Report progress periodically (every 1%)
        if progress_callback and (i % max(1, total_items // 100) == 0 or i == total_items - 1):
            progress_callback(i + 1, total_items, "Processing")

    return results
```

## Performance Notes

### Update Frequency
- Callbacks update every **1% of progress** by default
- Minimal overhead: <0.1% performance impact
- For 4,950 pairs: ~50 callback invocations
- For 499,500 pairs: ~5,000 callback invocations

### Cache Behavior
- **Cache hit**: No callbacks (instant return)
- **Cache miss**: Full progress reporting
- Use `--no-cache` to force computation and see progress

### Large Datasets

For very large datasets (>1000 devices, >500K pairs):
- Progress updates remain efficient (1% batching)
- ETA becomes more accurate over time
- Memory usage unchanged (callbacks don't store data)

## Testing

Run the comprehensive test suite:

```bash
# Progress callback tests (13 tests)
pytest tests/test_progress_callbacks.py -v

# All analytics tests (60 tests)
pytest tests/test_progress_callbacks.py tests/test_section_analytics.py -v
```

## Troubleshooting

### Progress bar not showing?

Check verbose mode:
```bash
# Explicitly enable verbose (default)
python3 compare_sections.py ... --similarity

# Check if quiet mode is disabling it
python3 compare_sections.py ... --similarity --quiet  # No progress bar
```

### Progress stuck at 0%?

- Cache hit - result returned immediately
- Use `--no-cache` to force computation

### Want to disable progress?

```bash
# Use quiet mode
python3 compare_sections.py ... --similarity --quiet

# Or in code
result = pairwise_similarity_matrix(data, section_type, progress_callback=None)
```

## Files Modified

- `scripts/section_analytics.py` - Core progress callback support
- `scripts/compare_sections.py` - ProgressBar class and CLI integration
- `tests/test_progress_callbacks.py` - Comprehensive test suite
- `scripts/demo_progress_bar.py` - Interactive demonstration

## Next Steps

1. **Try the demo**: `python3 scripts/demo_progress_bar.py --devices 50`
2. **Run tests**: `pytest tests/test_progress_callbacks.py -v`
3. **Use in production**: Progress bars work automatically in CLI
4. **Extend to other functions**: Use the pattern to add progress to other long-running operations

## Support

For questions or issues:
- See `FE-006-IMPLEMENTATION-SUMMARY.md` for detailed technical documentation
- Check test files for usage examples
- Run demo script for interactive examples
