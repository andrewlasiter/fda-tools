# Configuration Examples

This directory contains environment-specific configuration examples for the FDA Tools plugin.

## Files

### `development.toml`
Configuration optimized for local development:
- Debug logging enabled
- Shorter cache TTLs (1 day)
- Experimental features enabled
- More verbose output
- Faster PDF downloads
- Development data directories

### `production.toml`
Configuration optimized for production deployment:
- Warning-level logging only
- Long cache TTLs (7-30 days)
- No experimental features
- Minimal console output
- Conservative rate limits
- Audit logging (21 CFR Part 11)

### `staging.toml` (coming soon)
Configuration for staging/QA environments.

## Usage

### Development Environment

Copy the development config to your user config location:

```bash
cp examples/config/development.toml ~/.claude/fda-tools.config.toml
```

Or set environment variable:

```bash
export FDA_GENERAL_ENVIRONMENT=development
```

### Production Deployment

Replace the system config with production settings:

```bash
cp examples/config/production.toml plugins/fda-tools/config.toml
```

### Environment-Specific Overrides

You can override specific settings using environment variables:

```bash
# Override cache TTL
export FDA_CACHE_DEFAULT_TTL=86400

# Enable debug logging
export FDA_LOGGING_LEVEL=DEBUG

# Use custom data directory
export FDA_PATHS_BASE_DIR=/data/fda-510k-data
```

## Key Differences

| Setting | Development | Production |
|---------|-------------|------------|
| Log Level | DEBUG | WARNING |
| Cache TTL | 1 day | 7-30 days |
| PDF Download Delay | 10s | 30s |
| Experimental Features | Enabled | Disabled |
| Console Output | Enabled | Disabled |
| Auto Backup | 12 hours | 24 hours |
| Strict Validation | Disabled | Enabled |
| Progress Bars | Enabled | Disabled |

## Testing Your Configuration

Validate your configuration:

```bash
python3 lib/config.py --validate
```

Show current configuration:

```bash
python3 lib/config.py --show
```

Export to JSON for review:

```bash
python3 lib/config.py --export /tmp/config.json
cat /tmp/config.json | jq
```

## Security Notes

**NEVER commit API keys to configuration files!**

Use one of these secure methods:
1. Environment variables: `export OPENFDA_API_KEY="..."`
2. System keyring: `python3 lib/secure_config.py --set openfda`
3. User config file (encrypted)

## Support

For questions about configuration:
- See `docs/CONFIGURATION_ARCHITECTURE.md` for architecture details
- See `docs/CONFIGURATION_REFERENCE.md` for all options
- See `CONFIGURATION_MIGRATION_GUIDE.md` for migration help
