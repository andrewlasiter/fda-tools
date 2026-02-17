# FDA Tools Plugin - Installation Guide

Complete installation and configuration instructions for the FDA Tools Plugin.

## Table of Contents

- [System Requirements](#system-requirements)
- [Installation Steps](#installation-steps)
- [Optional Components](#optional-components)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)
- [Upgrading](#upgrading)

## System Requirements

### Minimum Requirements

- **Python**: 3.9 or higher
- **Disk Space**:
  - 100MB for plugin installation
  - 500MB for basic FDA data
  - 5GB recommended for extensive data analysis
- **RAM**: 4GB minimum, 8GB recommended
- **Internet**: Required for FDA API access
- **OS**: Linux, macOS, or Windows (WSL)

### Recommended Requirements

For optimal performance:

- **Python**: 3.11 or higher
- **Disk Space**: 10GB (allows extensive data caching)
- **RAM**: 8GB or more
- **Storage**: SSD for faster data access
- **Network**: Broadband connection (FDA APIs can be slow)

### Supported Platforms

- **Linux**: Ubuntu 20.04+, Debian 11+, Fedora 35+
- **macOS**: macOS 11 (Big Sur) or later
- **Windows**: Windows 10/11 with WSL2

## Installation Steps

### Step 1: Install Claude Code

If you haven't already, install Claude Code:

```bash
# Follow instructions at https://claude.ai/code
```

Verify installation:

```bash
claude --version
```

### Step 2: Install FDA Tools Plugin

**Option A: From Claude Code Marketplace** (Recommended)

From your terminal:

```bash
claude plugin marketplace add andrewlasiter/fda-tools
claude plugin install fda-tools@fda-tools
```

**Option B: From Claude Code Session**

Inside a Claude Code session:

```
/plugin marketplace add andrewlasiter/fda-tools
/plugin install fda-tools@fda-tools
```

**Option C: Manual Installation** (Advanced)

Clone the repository:

```bash
cd ~/.claude/plugins/marketplaces/
git clone https://github.com/andrewlasiter/fda-predicate-assistant fda-tools
```

### Step 3: Verify Plugin Installation

Check that the plugin is installed:

```bash
ls -la ~/.claude/plugins/marketplaces/fda-tools/
```

You should see:
- `plugins/fda-tools/` - Main plugin directory
- `README.md` - Documentation
- `CHANGELOG.md` - Version history

**Important**: Restart Claude Code after installation to load the plugin.

### Step 4: Verify Plugin Works

Start a new Claude Code session and test:

```
/fda:validate --k-number K240001
```

Expected output:
```
✓ K240001 is a valid FDA 510(k) number
```

If you see this, the plugin is working correctly!

### Step 5: Install Python Dependencies

Navigate to the plugin directory:

```bash
cd ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/
```

Install required packages:

```bash
pip3 install -r requirements.txt
```

Required packages:
- **requests** (2.31.0+) - FDA API access
- **beautifulsoup4** (4.12.0+) - HTML parsing
- **lxml** (4.9.0+) - XML processing
- **pikepdf** (8.0.0+) - PDF processing
- **python-dateutil** (2.8.0+) - Date parsing

**Note**: On some systems, you may need to use `pip` instead of `pip3`.

### Step 6: Configure Data Directory

Set your FDA data directory:

```
/fda-tools:configure
```

Default location: `~/fda-510k-data/`

The plugin will create this structure automatically:

```
~/fda-510k-data/
├── cache/              # API response cache
│   ├── clearances/
│   ├── recalls/
│   └── maude/
├── downloads/          # Downloaded PDFs
│   ├── 510k/
│   └── pma/
├── structured/         # Parsed structured data
│   ├── devices/
│   └── sections/
├── projects/           # Your submission projects
│   ├── PROJECT_NAME_1/
│   └── PROJECT_NAME_2/
├── reports/            # Generated reports
└── logs/               # Debug logs
```

### Step 7: Test Installation

Run a simple test:

```
/fda:research --product-code DQY --device "catheter"
```

This should:
1. Query the FDA database
2. Find clearances for product code DQY
3. Display results

If this works, installation is complete!

## Optional Components

### A. OpenClaw Bridge Server

For OpenClaw integration (TypeScript/JavaScript environments):

```bash
cd ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/bridge/
pip3 install -r requirements.txt
python3 server.py
```

The bridge server runs on port 18790 by default.

Verify it's running:

```bash
curl http://localhost:18790/health
```

Expected output:
```json
{"status": "healthy", "version": "1.0.0"}
```

### B. TypeScript Skill (OpenClaw)

For TypeScript-based workflows:

```bash
cd ~/.claude/plugins/marketplaces/fda-tools/openclaw-skill/
npm install
npm run build
```

This compiles the TypeScript skill for use in OpenClaw environments.

### C. Expert Skills

The plugin includes 7 specialized expert skills located in:

```
~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/skills/
```

These are loaded automatically when you invoke expert agents:

- `fda-clinical-expert/`
- `fda-postmarket-expert/`
- `fda-quality-expert/`
- `fda-regulatory-strategy-expert/`
- `fda-software-ai-expert/`

No additional installation required.

## Configuration

### Environment Variables

Optional environment variables for advanced configuration:

```bash
# FDA data directory (overrides default)
export FDA_DATA_DIR=~/fda-510k-data

# FDA API key (for increased rate limits)
export FDA_API_KEY=your_api_key_here

# Enable debug logging
export FDA_DEBUG=1

# Cache TTL in seconds (default: 86400 = 24 hours)
export FDA_CACHE_TTL=86400

# Maximum PDF download size in MB (default: 50)
export FDA_MAX_PDF_SIZE=50
```

Add these to your shell profile (`~/.bashrc`, `~/.zshrc`, etc.) to persist across sessions.

### Settings File

Create a local settings file for persistent configuration:

```bash
mkdir -p ~/.claude/
nano ~/.claude/fda-tools.local.md
```

Example settings:

```markdown
# FDA Tools Local Settings

data_directory: ~/fda-510k-data
default_product_codes: [DQY, OVE, FRO]
auto_cache: true
cache_ttl: 86400
max_concurrent_downloads: 5
pdf_timeout: 300
api_timeout: 30
```

### Plugin Configuration

Configure plugin behavior using the configure command:

```
/fda-tools:configure
```

This interactive command allows you to set:
- Data directory location
- Cache preferences
- Download settings
- API parameters
- Debug options

## Verification

### Quick Verification

Test each major component:

```bash
# 1. Validate K-number
/fda:validate --k-number K240001

# 2. Search FDA database
/fda:research --product-code DQY

# 3. Extract data
/fda:extract --product-codes DQY --years 2024 --limit 5

# 4. Check plugin version
/fda-tools:status
```

### Comprehensive Verification

Run the full test suite:

```bash
cd ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/
python3 -m pytest tests/
```

Expected result:
```
===================== 722 tests passed in X.XX seconds =====================
```

### Component Verification

Test individual components:

**Python Scripts:**
```bash
cd ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/scripts/
python3 validation.py --k-number K240001
```

**Bridge Server:**
```bash
curl http://localhost:18790/validate/K240001
```

**Expert Skills:**
```
/fda-clinical-expert
```

## Troubleshooting

### "Command not found" Error

**Problem**: `/fda:research` returns "command not found"

**Solutions**:
1. Verify plugin installed: `ls ~/.claude/plugins/marketplaces/fda-tools/`
2. Restart Claude Code completely
3. Check Claude Code version: `claude --version` (requires v1.0.0+)
4. Try re-installing: `/plugin install fda-tools@fda-tools`

### "No module named 'requests'" Error

**Problem**: Python import errors

**Solution**: Install dependencies:
```bash
cd ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/
pip3 install -r requirements.txt
```

If pip3 not found, try:
```bash
python3 -m pip install -r requirements.txt
```

### Permission Denied Errors

**Problem**: Cannot write to data directory

**Solutions**:
1. Check directory permissions: `ls -la ~/fda-510k-data/`
2. Create directory manually: `mkdir -p ~/fda-510k-data`
3. Set proper permissions: `chmod 755 ~/fda-510k-data`
4. Change data directory to writable location: `/fda-tools:configure`

### API Connection Errors

**Problem**: Cannot connect to FDA API

**Solutions**:
1. Check internet connection: `ping api.fda.gov`
2. Test API directly: `curl https://api.fda.gov/device/510k.json?limit=1`
3. Check firewall settings
4. Try with VPN disabled (some VPNs block FDA API)
5. Wait and retry (FDA API sometimes has outages)

### Slow Performance

**Problem**: Commands take >30 seconds

**Solutions**:
1. Enable caching: `/fda:configure` → set auto_cache=true
2. Use SSD for data directory
3. Increase available RAM (close other applications)
4. Use product code filters to reduce data volume
5. Clear old cache: `/fda:cache clear --older-than 30d`

### PDF Download Failures

**Problem**: PDFs fail to download

**Solutions**:
1. Check internet connection
2. Verify K-number is valid: `/fda:validate --k-number KXXXXXX`
3. Check disk space: `df -h ~/fda-510k-data`
4. Increase timeout: `export FDA_PDF_TIMEOUT=600`
5. Use `--skip-downloads` flag to continue without PDFs
6. Note: Some older PDFs may not be available on openFDA

### Bridge Server Won't Start

**Problem**: `python3 bridge/server.py` fails

**Solutions**:
1. Check port 18790 not in use: `lsof -i :18790`
2. Kill existing process: `kill $(lsof -t -i:18790)`
3. Install bridge dependencies: `pip3 install -r bridge/requirements.txt`
4. Check Python version: `python3 --version` (must be 3.9+)
5. Try alternate port: `python3 server.py --port 18791`

### Import Errors

**Problem**: Plugin commands work but scripts fail with import errors

**Solution**: Set PYTHONPATH:
```bash
export PYTHONPATH=$PYTHONPATH:~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/
```

Add to shell profile for persistence.

## Upgrading

### Upgrade to Latest Version

**From Marketplace:**
```bash
claude plugin update fda-tools
```

**From Git:**
```bash
cd ~/.claude/plugins/marketplaces/fda-tools/
git pull origin master
pip3 install -r plugins/fda-tools/requirements.txt --upgrade
```

### Check Current Version

```
/fda-tools:status
```

Or check plugin.json:
```bash
cat ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/.claude-plugin/plugin.json | grep version
```

Current version: **5.36.0**

### Version History

See [CHANGELOG.md](../CHANGELOG.md) for complete version history.

### Migration Guides

When upgrading across major versions:

- **v4.x → v5.x**: See `docs/migrations/v4_to_v5.md`
- **v5.0-5.19 → v5.20+**: No breaking changes
- **v5.25.0 → v5.25.1**: Drop-in replacement (patch release)

### Backup Before Upgrading

Always backup your data directory before major upgrades:

```bash
cp -r ~/fda-510k-data ~/fda-510k-data.backup
```

### Rollback

If upgrade causes issues, rollback:

```bash
cd ~/.claude/plugins/marketplaces/fda-tools/
git checkout v5.35.0  # or desired version
pip3 install -r plugins/fda-tools/requirements.txt
```

## Post-Installation

### Recommended First Steps

1. **Configure data directory**: `/fda-tools:configure`
2. **Test with known K-number**: `/fda:validate --k-number K240001`
3. **Extract sample data**: `/fda:extract --product-codes DQY --years 2024 --limit 10`
4. **Review documentation**: Read `docs/QUICK_START.md`
5. **Try an agent**: `/fda-research-intelligence`

### Enable Advanced Features

**Smart Auto-Update:**
```
/fda-tools:update-data --smart
```

**Competitive Intelligence:**
```
/fda:dashboard --product-code DQY
```

**Section Comparison:**
```
/fda-tools:compare-sections --product-code DQY
```

### Performance Optimization

For best performance:

1. **Use SSD** for data directory
2. **Enable caching** with reasonable TTL
3. **Limit concurrent downloads** to avoid rate limits
4. **Use product code filters** instead of downloading everything
5. **Clear old cache periodically**: `/fda:cache clear --older-than 90d`

## Getting Help

### Documentation

- **Quick Start**: `docs/QUICK_START.md`
- **Troubleshooting**: `docs/TROUBLESHOOTING.md`
- **Command Reference**: `README.md`
- **Changelog**: `CHANGELOG.md`

### Support Channels

- **GitHub Issues**: [Report bugs](https://github.com/andrewlasiter/fda-predicate-assistant/issues)
- **Documentation**: All docs in `docs/` directory
- **Ask Claude**: Use `/fda-510k-knowledge` expert for regulatory questions

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
export FDA_DEBUG=1
/fda:research --product-code DQY
```

Logs are saved to: `~/fda-510k-data/logs/`

View recent logs:
```bash
tail -f ~/fda-510k-data/logs/fda-tools.log
```

## Security Considerations

### API Keys

If using an FDA API key:
- Never commit to version control
- Use environment variables, not hardcoded values
- Rotate periodically
- Request from FDA: https://open.fda.gov/apis/authentication/

### Data Privacy

- FDA Tools stores data locally in `~/fda-510k-data/`
- No data is sent to third parties
- All FDA data is public information
- Your project data stays on your machine

### Network Security

- All FDA API calls use HTTPS
- No external dependencies beyond FDA APIs
- No telemetry or usage tracking
- Fully offline after initial data download (except for updates)

## Advanced Installation

### Docker Installation

Create a Dockerfile:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
RUN git clone https://github.com/andrewlasiter/fda-predicate-assistant
WORKDIR /app/fda-predicate-assistant/plugins/fda-tools
RUN pip install -r requirements.txt

ENV FDA_DATA_DIR=/data
VOLUME /data

CMD ["python3", "bridge/server.py"]
```

Build and run:
```bash
docker build -t fda-tools .
docker run -p 18790:18790 -v ~/fda-510k-data:/data fda-tools
```

### Virtual Environment

For isolated installation:

```bash
python3 -m venv ~/fda-venv
source ~/fda-venv/bin/activate
pip install -r ~/.claude/plugins/marketplaces/fda-tools/plugins/fda-tools/requirements.txt
```

### Multi-User Setup

For shared team environments:

```bash
# Shared data directory
export FDA_DATA_DIR=/shared/fda-data
sudo mkdir -p /shared/fda-data
sudo chown $USER:$GROUP /shared/fda-data
sudo chmod 775 /shared/fda-data
```

## Uninstallation

### Remove Plugin

```bash
claude plugin uninstall fda-tools
```

Or manually:
```bash
rm -rf ~/.claude/plugins/marketplaces/fda-tools/
```

### Remove Data

```bash
rm -rf ~/fda-510k-data/
```

**Warning**: This deletes all cached data and projects. Backup first!

### Clean Up Environment

Remove environment variables from shell profile:
```bash
# Remove these lines from ~/.bashrc or ~/.zshrc
export FDA_DATA_DIR=~/fda-510k-data
export FDA_API_KEY=...
export FDA_DEBUG=1
```

## Next Steps

After installation:

1. Read the [Quick Start Guide](QUICK_START.md)
2. Review [Common Workflows](QUICK_START.md#common-workflows)
3. Try the [Example Submission](QUICK_START.md#example-complete-new-device-submission)
4. Explore [Agent-Powered Workflows](QUICK_START.md#agent-powered-workflows)
5. Check [Troubleshooting Guide](TROUBLESHOOTING.md) if issues arise

Ready to start? Run:
```
/fda:research --product-code DQY
```

Happy submitting! 🎉
