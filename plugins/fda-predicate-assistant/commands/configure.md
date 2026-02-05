---
description: View or modify FDA predicate assistant settings and data directory paths
allowed-tools: Read, Write
argument-hint: "[--show | --set KEY VALUE | --migrate-cache]"
---

# FDA Predicate Assistant Configuration

You are managing configuration settings for the FDA predicate extraction pipeline.

## Settings File Location

Settings are stored in: `~/.claude/fda-predicate-assistant.local.md`

## Available Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `projects_dir` | `/mnt/c/510k/Python/510k_projects` | Root directory for all project folders (each extraction query gets its own folder) |
| `batchfetch_dir` | `/mnt/c/510k/Python/510kBF` | Legacy directory containing 510kBF output (510k_download.csv, merged_data.csv) |
| `extraction_dir` | `/mnt/c/510k/Python/PredicateExtraction` | Directory containing extraction output (output.csv, pdf_data.json) |
| `pdf_storage_dir` | `/mnt/c/510k/Python/510kBF/510ks` | Where downloaded PDFs are stored |
| `data_dir` | `/mnt/c/510k/Python/PredicateExtraction` | Where FDA database files (pmn*.txt, pma.txt, foiaclass.txt) are stored |
| `extraction_script` | `predicate_extractor.py` | Which extraction script to use (bundled in plugin) |
| `batchfetch_script` | `batchfetch.py` | Which batch fetch script to use (bundled in plugin) |
| `ocr_mode` | `smart` | OCR processing mode: smart, always, never |
| `batch_size` | `100` | Number of PDFs to process per batch |
| `workers` | `4` | Number of parallel processing workers |
| `cache_days` | `5` | Days to cache FDA database files |
| `default_year` | `null` | Default year filter (null = all years) |
| `default_product_code` | `null` | Default product code filter |

## Commands

### Show Current Settings

If `$ARGUMENTS` is `--show` or empty, read and display the current settings:

Read the settings file at `~/.claude/fda-predicate-assistant.local.md`. If it doesn't exist, report defaults and offer to create one.

Also report on bundled scripts:
```
Plugin Scripts (at $CLAUDE_PLUGIN_ROOT/scripts/):
  predicate_extractor.py  — Stage 2: Extract predicates from PDFs
  batchfetch.py           — Stage 1: Filter catalog & download PDFs
  requirements.txt        — Python dependencies for both scripts
```

### Set a Value

If `$ARGUMENTS` starts with `--set`, parse KEY and VALUE, then update the settings file.

Validate the key is one of the known settings before writing. For directory paths, verify the directory exists.

## Settings File Format

The settings file uses YAML frontmatter:

```markdown
---
projects_dir: /mnt/c/510k/Python/510k_projects
batchfetch_dir: /mnt/c/510k/Python/510kBF
extraction_dir: /mnt/c/510k/Python/PredicateExtraction
pdf_storage_dir: /mnt/c/510k/Python/510kBF/510ks
data_dir: /mnt/c/510k/Python/PredicateExtraction
extraction_script: predicate_extractor.py
batchfetch_script: batchfetch.py
ocr_mode: smart
batch_size: 100
workers: 4
cache_days: 5
default_year: null
default_product_code: null
---

# FDA Predicate Assistant Settings

This file stores your preferences for the FDA 510(k) pipeline.

## Directory Paths

- **projects_dir**: Root for all project folders — each `/fda:extract` query gets its own subfolder
- **batchfetch_dir**: Legacy location for 510kBF output (510k_download.csv, merged_data.csv)
- **extraction_dir**: Legacy location for PredicateExtraction output (output.csv, pdf_data.json)
- **pdf_storage_dir**: Where downloaded PDFs are organized by year/applicant/productcode
- **data_dir**: Where FDA database files are stored (pmn*.txt, pma.txt, foiaclass.txt)

## Script Configuration

- **extraction_script**: predicate_extractor.py (bundled in plugin at $CLAUDE_PLUGIN_ROOT/scripts/)
- **batchfetch_script**: batchfetch.py (bundled in plugin at $CLAUDE_PLUGIN_ROOT/scripts/)

## Processing Options

- **ocr_mode**: smart (use OCR only when needed), always, never
- **batch_size**: Number of PDFs per processing batch
- **workers**: Parallel processing workers (adjust based on CPU)
- **cache_days**: How long to cache FDA database files

## Filters

- **default_year**: Set to filter by year automatically
- **default_product_code**: Set to filter by product code automatically
```

### Migrate Cache Format

If `$ARGUMENTS` is `--migrate-cache`, migrate from monolithic `pdf_data.json` to per-device cache:

```bash
python3 << 'PYEOF'
import json, os

extraction_dir = '/mnt/c/510k/Python/PredicateExtraction'
pdf_json = os.path.join(extraction_dir, 'pdf_data.json')
cache_dir = os.path.join(extraction_dir, 'cache')
devices_dir = os.path.join(cache_dir, 'devices')
index_file = os.path.join(cache_dir, 'index.json')

if not os.path.exists(pdf_json):
    print('ERROR: pdf_data.json not found — nothing to migrate')
    exit(1)

if os.path.exists(index_file):
    print('WARNING: Per-device cache already exists. Merging new entries only.')
    with open(index_file) as f:
        index = json.load(f)
else:
    index = {}

os.makedirs(devices_dir, exist_ok=True)

print(f'Loading pdf_data.json...')
with open(pdf_json) as f:
    data = json.load(f)

migrated = 0
skipped = 0
for filename, content in data.items():
    knumber = filename.replace('.pdf', '')
    if knumber in index:
        skipped += 1
        continue

    # Normalize content format
    if isinstance(content, dict):
        device_data = content
    else:
        device_data = {'text': str(content)}

    # Write individual device file
    device_file = os.path.join(devices_dir, f'{knumber}.json')
    with open(device_file, 'w') as f:
        json.dump(device_data, f)

    # Add to index
    rel_path = os.path.relpath(device_file, extraction_dir)
    index[knumber] = {
        'file_path': rel_path,
        'text_length': len(device_data.get('text', '')),
        'extraction_method': device_data.get('extraction_method', 'unknown'),
        'page_count': device_data.get('page_count', 0)
    }
    migrated += 1

# Write index
with open(index_file, 'w') as f:
    json.dump(index, f, indent=2)

print(f'Migration complete: {migrated} devices migrated, {skipped} already existed')
print(f'Index: {index_file} ({len(index)} total devices)')
print(f'Per-device files: {devices_dir}/')
print(f'Original pdf_data.json preserved (can delete manually when ready)')
PYEOF
```

Report the migration results and note that the original `pdf_data.json` is preserved as a backup.

## Creating Default Settings

If no settings file exists and user wants to configure, create one with the template above using the default values.
