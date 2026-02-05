# Path Resolution for FDA Plugin Commands

All commands that access data files MUST resolve paths from user settings before using defaults. This ensures the plugin works on any system, not just the original development machine.

## Standard Path Resolution

Before accessing any data file, read the user's settings and resolve paths:

```bash
python3 << 'PYEOF'
import os, re

settings_path = os.path.expanduser('~/.claude/fda-predicate-assistant.local.md')
defaults = {
    'projects_dir': os.path.expanduser('~/fda-510k-data/projects'),
    'batchfetch_dir': os.path.expanduser('~/fda-510k-data/batchfetch'),
    'extraction_dir': os.path.expanduser('~/fda-510k-data/extraction'),
    'pdf_storage_dir': os.path.expanduser('~/fda-510k-data/batchfetch/510ks'),
    'data_dir': os.path.expanduser('~/fda-510k-data/extraction'),
}

if os.path.exists(settings_path):
    with open(settings_path) as f:
        content = f.read()
    for key in defaults:
        m = re.search(rf'{key}:\s*(\S+)', content)
        if m and m.group(1) != 'null':
            defaults[key] = m.group(1)

for key, val in defaults.items():
    print(f'{key.upper()}={val}')
PYEOF
```

## Variable Names After Resolution

| Settings Key | Variable Name | Default |
|-------------|--------------|---------|
| `projects_dir` | `$PROJECTS_DIR` | `~/fda-510k-data/projects` |
| `batchfetch_dir` | `$BATCHFETCH_DIR` | `~/fda-510k-data/batchfetch` |
| `extraction_dir` | `$EXTRACTION_DIR` | `~/fda-510k-data/extraction` |
| `pdf_storage_dir` | `$PDF_STORAGE_DIR` | `~/fda-510k-data/batchfetch/510ks` |
| `data_dir` | `$DATA_DIR` | `~/fda-510k-data/extraction` |

## Where Data Files Live

After path resolution, data files are at:

| File | Location |
|------|----------|
| `510k_download.csv` | `$BATCHFETCH_DIR/` or `$PROJECTS_DIR/$PROJECT_NAME/` |
| `output.csv` | `$EXTRACTION_DIR/` or `$PROJECTS_DIR/$PROJECT_NAME/` |
| `pdf_data.json` | `$EXTRACTION_DIR/` or `$PROJECTS_DIR/$PROJECT_NAME/` |
| `cache/index.json` | `$EXTRACTION_DIR/cache/` |
| `pmn96cur.txt` | `$DATA_DIR/` |
| `foiaclass.txt` | `$DATA_DIR/` or `$BATCHFETCH_DIR/fda_data/` |
| Downloaded PDFs | `$PDF_STORAGE_DIR/` or `$PROJECTS_DIR/$PROJECT_NAME/510ks/` |
| Plugin scripts | `$FDA_PLUGIN_ROOT/scripts/` |

## Important Notes

- **Never assume a hardcoded path** — always read settings first
- **Check multiple locations** — data may be in project folder, extraction dir, or batchfetch dir
- **Create directories** as needed — use `mkdir -p` before writing output files
- **Report configured paths** in status/error messages so users know where data is expected
