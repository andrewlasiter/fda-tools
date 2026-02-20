# Installation Guide - FDA Tools Plugin

Complete installation and configuration guide for the FDA Tools plugin.

## System Requirements

### Required
- **Claude Code** CLI installed
- **Operating System:** Linux, macOS, or Windows WSL
- **Disk Space:** 500 MB minimum (2-5 GB recommended for full data corpus)
- **Internet:** Stable connection for API access

### Optional
- **Python 3.8+** for batch scripts and data pipeline
- **pip** for Python package installation
- **openFDA API Key** for higher rate limits (free, optional)

## Installation Methods

### Method 1: From Marketplace (Recommended)

1. **Install from Claude Code marketplace:**
   ```bash
   claude plugin install fda-tools
   ```

2. **Verify installation:**
   ```bash
   claude plugin list | grep fda-tools
   ```

3. **Check plugin version:**
   ```bash
   /fda-tools:status
   ```

### Method 2: Manual Installation (Development)

1. **Clone repository:**
   ```bash
   cd ~/.claude/plugins/marketplaces
   git clone https://github.com/andrewlasiter/fda-tools fda-tools
   ```

2. **Install plugin:**
   ```bash
   cd fda-tools
   claude plugin install .
   ```

3. **Verify installation:**
   ```bash
   /fda-tools:status
   ```

## Configuration

### 1. Run Setup Wizard

The easiest way to configure:

```bash
/fda-tools:start
```

The wizard will guide you through:
- Data directory setup
- Existing data detection
- Device type configuration
- Recommended workflow

### 2. Manual Configuration

#### Set Data Directory

```bash
/fda-tools:configure
```

Default location: `~/fda-510k-data/`

Custom location:
```bash
/fda-tools:configure --data-dir /path/to/your/data
```

#### Configure API Keys (Optional)

For openFDA enrichment with higher rate limits:

```bash
# Set API key
export FDA_API_KEY="your-api-key-here"

# Or add to settings file: ~/.claude/fda-tools.local.md
```

To get an API key:
1. Visit: https://open.fda.gov/apis/authentication/
2. Sign up for free
3. Copy your API key

#### Settings File Schema

The settings file at `~/.claude/fda-tools.local.md` uses YAML frontmatter format. An example
file with all supported fields and documentation is available at:

```
plugins/fda-tools/docs/fda-tools.local.example.md
```

Copy it to get started:

```bash
cp ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/docs/fda-tools.local.example.md \
   ~/.claude/fda-tools.local.md
```

See the [main INSTALLATION.md](../../../docs/INSTALLATION.md#settings-schema-reference) for
the complete settings schema reference with types, defaults, and validation rules.

### 3. Install Python Dependencies (Optional)

For batch scripts and data pipeline:

```bash
cd ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts
pip3 install -r requirements.txt
```

**Required packages:**
- `requests` - HTTP client for API calls
- `beautifulsoup4` - HTML/XML parsing
- `lxml` - XML processing
- `pandas` - Data manipulation
- `numpy` - Numerical operations

### 4. Configure MCP Servers (Optional)

For enhanced functionality with PubMed and ClinicalTrials.gov:

The plugin includes `.mcp.json` with pre-configured servers:
- PubMed (via Europe PMC)
- ClinicalTrials.gov v2

No additional configuration needed - servers auto-load with plugin.

## First-Time Setup

### 1. Verify Installation

```bash
/fda-tools:status
```

Expected output:
- ✓ Plugin installed and enabled
- ✓ Data directory configured
- ✓ Scripts accessible
- ⚠ FDA data not yet downloaded (normal on first run)

### 2. Test Basic Commands

```bash
# Test regulatory Q&A
/fda-tools:ask --question "What is a 510(k)?"

# Test K-number validation
/fda-tools:validate --k-number K240001
```

### 3. Download Initial Data (Optional)

Build a local corpus for faster searches:

```bash
# Download recent clearances for a product code
/fda-tools:extract --product-code DQY --years 2024

# Or run full data pipeline for comprehensive corpus
/fda-tools:data-pipeline --product-codes DQY,KGN,OAP --years 2023-2024
```

## Directory Structure

After setup, your data directory will have:

```
~/fda-510k-data/
├── downloads/              # Downloaded PDFs
│   ├── DQY/
│   └── KGN/
├── extracted/              # Extraction results
│   ├── predicates/
│   └── metadata/
├── projects/               # Project-specific data
│   └── my_device/
│       ├── device_profile.json
│       ├── review.json
│       ├── drafts/
│       └── output/
└── cache/                  # Cached API responses
    ├── maude/
    ├── recalls/
    └── guidance/
```

## Permissions Setup

### Bash Execution Permissions

The plugin requires bash permissions for script execution. These are pre-configured in the plugin.

To verify:
```bash
grep "fda-tools" ~/.claude/settings.local.json
```

### File Permissions

Ensure data directory has write permissions:
```bash
chmod -R u+w ~/fda-510k-data/
```

## Verification Checklist

After installation, verify:

- [ ] Plugin appears in `claude plugin list`
- [ ] `/fda-tools:status` runs without errors
- [ ] Data directory created and writable
- [ ] `/fda-tools:ask` responds to test question
- [ ] `/fda-tools:validate --k-number K240001` succeeds
- [ ] (Optional) Python scripts can be executed
- [ ] (Optional) API key configured for enrichment

## Upgrading

### Update Plugin

```bash
# From marketplace
claude plugin update fda-tools

# Or from git (manual installation)
cd ~/.claude/plugins/marketplaces/fda-tools
git pull origin master
```

### Migrate Settings (After v5.22.0 Rename)

If upgrading from `fda-tools`:

```bash
# Migrate settings file
mv ~/.claude/fda-tools.local.md ~/.claude/fda-tools.local.md
```

See [MIGRATION_NOTICE.md](../MIGRATION_NOTICE.md) for complete migration guide.

### Update Python Dependencies

```bash
cd ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts
pip3 install -r requirements.txt --upgrade
```

## Uninstallation

### Remove Plugin

```bash
claude plugin uninstall fda-tools
```

### Remove Data (Optional)

```bash
rm -rf ~/fda-510k-data/
rm ~/.claude/fda-tools.local.md
```

## Platform-Specific Notes

### Linux

No special configuration required. Use default paths.

### macOS

- Use `python3` instead of `python`
- Data directory: `~/fda-510k-data/`
- Ensure Xcode Command Line Tools installed

### Windows WSL

- Access data from Windows: `/mnt/c/Users/YourName/fda-510k-data/`
- Use WSL 2 for better performance
- Ensure line endings set to LF not CRLF

## Troubleshooting Installation

### Plugin Not Found

```bash
# Verify plugin directory exists
ls -la ~/.claude/plugins/marketplaces/fda-tools/

# Reinstall if missing
claude plugin install fda-tools
```

### Permission Denied Errors

```bash
# Fix script permissions
chmod +x ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/*.py

# Fix data directory permissions
chmod -R u+w ~/fda-510k-data/
```

### Python Dependencies Missing

```bash
# Install dependencies
cd ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts
pip3 install -r requirements.txt

# Or use virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### API Connection Failures

```bash
# Test openFDA API connectivity
curl "https://api.fda.gov/device/510k.json?limit=1"

# Check for firewall/proxy issues
# Configure proxy if needed:
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
```

## Next Steps

1. **Quick Start:** See [QUICK_START.md](QUICK_START.md) for common workflows
2. **Documentation:** Explore plugin documentation in `docs/`
3. **First Project:** Run `/fda-tools:start` to begin
4. **Get Help:** Use `/fda-tools:ask` for regulatory questions

## Support

- **Documentation:** `~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/docs/`
- **Command Help:** `/fda-tools:ask --question "How do I..."`
- **Issues:** https://github.com/andrewlasiter/fda-tools/issues
- **Status Check:** `/fda-tools:status`
