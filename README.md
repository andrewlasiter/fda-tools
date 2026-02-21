![Version](https://img.shields.io/badge/version-5.36.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Commands](https://img.shields.io/badge/commands-42-orange)
![Agents](https://img.shields.io/badge/agents-4-purple)
![Tests](https://img.shields.io/badge/tests-722-brightgreen)
[![codecov](https://codecov.io/gh/andrewlasiter/fda-tools/branch/master/graph/badge.svg)](https://codecov.io/gh/andrewlasiter/fda-tools)
![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-blueviolet)
![FDA 510(k)](https://img.shields.io/badge/FDA-510(k)-red)

# FDA Tools — Claude Code Plugin Marketplace

AI-powered tools for FDA medical device regulatory work. Built for regulatory affairs professionals working on 510(k) submissions.

## Install

From your terminal:

```bash
claude plugin marketplace add andrewlasiter/fda-tools
claude plugin install fda-tools@fda-tools
```

Or from inside a Claude Code or Claude Desktop session:

```
/plugin marketplace add andrewlasiter/fda-tools
/plugin install fda-tools@fda-tools
```

Start a new session after installing to load the plugin.

## What You Can Do

- **Find predicates** — Search FDA databases, trace predicate lineage, manually propose predicates, and validate device numbers
- **Analyze safety** — Pull MAUDE adverse events, recall history, and UDI/GUDID records for any product code or device
- **Compare adverse events** — Statistical peer comparison with percentile-based classification (EXCELLENT → EXTREME_OUTLIER)
- **Competitive intelligence** — Market concentration (HHI), top manufacturers, technology trends, and gold standard predicates
- **Look up standards** — Search FDA Recognized Consensus Standards by product code, standard number, or keyword
- **Plan your submission** — Get pathway recommendations, generate testing plans, and prepare Pre-Sub packages
- **Generate documents** — Substantial equivalence tables, submission outlines, regulatory prose drafts for 18 eSTAR sections
- **Run calculators** — Shelf life (ASTM F1980 accelerated aging), sample size, and sterilization dose calculations
- **Assemble for filing** — eSTAR-structured packages, import/export eSTAR XML, traceability matrices, consistency checks
- **Simulate FDA review** — Pre-check your submission against RTA checklists and identify likely deficiencies before filing
- **Maintain your data** — Gap analysis, automated PDF downloads, predicate extraction, and merge pipeline
- **Run it all at once** — Full autonomous pipeline from extraction through SE comparison
- **Monitor changes** — Watch for new clearances, recalls, MAUDE events, and guidance updates

## Plugins

### [FDA Predicate Assistant](./plugins/fda-tools/)

42 commands, 7 autonomous agents, and 712 tests covering every stage of the 510(k) workflow — from predicate research through CDRH Portal submission. Integrates with all 7 openFDA Device API endpoints and bundles Python scripts for batch PDF processing and data pipeline maintenance.

See the [full documentation](./plugins/fda-tools/README.md) for commands, agents, installation details, and quick start examples.

## Documentation

- **[Quick Start Guide](docs/QUICK_START.md)** - Get started in 5 minutes with essential commands and workflows
- **[Installation Guide](docs/INSTALLATION.md)** - Complete setup instructions, dependencies, and configuration
- **[Troubleshooting Guide](docs/TROUBLESHOOTING.md)** - Common issues and solutions
- **[Linear Integration](plugins/fda-tools/docs/LINEAR_INTEGRATION.md)** - Setup guide for Linear MCP integration and automated issue creation
- **[FDA Examples](plugins/fda-tools/docs/FDA_EXAMPLES.md)** - FDA-specific workflow examples (510(k), PMA, MAUDE analysis)
- **[Orchestrator Architecture](plugins/fda-tools/ORCHESTRATOR_ARCHITECTURE.md)** - Multi-agent orchestration system architecture
- **[Changelog](CHANGELOG.md)** - Release history and version updates
- **[Full Plugin Documentation](./plugins/fda-tools/README.md)** - Detailed command reference and advanced features

## Try It Now — Example Projects

Three worked examples cover the most common 510(k) scenarios:

| Example | Device type | Key topics |
|---------|-------------|-----------|
| [Example 1 — Catheter](examples/01-basic-510k-catheter/) | Hardware (DQY) | Predicate matching, EO sterilization |
| [Example 2 — AI Software](examples/02-samd-digital-pathology/) | SaMD (QKQ) | IEC 62304, cybersecurity, clinical validation |
| [Example 3 — Combination Product](examples/03-combination-product-wound-dressing/) | Combo (FRO) | OTC monograph, Class U, device-led |

```bash
# Load Example 1 and run a readiness check (~5 minutes):
cp examples/01-basic-510k-catheter/device_profile.json \
   ~/.fda-510k-data/projects/example-catheter/
/fda-tools:pre-check --project example-catheter
```

See [`examples/README.md`](examples/README.md) for the full guide.

## Shell Completion

Tab-completion is available for all `fda-*` CLI commands in bash and zsh.

**Bash** (one-time, current shell):
```bash
source tools/completions/fda-tools.bash
```

**Bash** (permanent):
```bash
echo 'source /path/to/fda-tools/tools/completions/fda-tools.bash' >> ~/.bashrc
```

**Zsh** (permanent — add before `compinit` in `~/.zshrc`):
```zsh
fpath=(/path/to/fda-tools/tools/completions $fpath)
autoload -Uz compinit && compinit
```

**System-wide install** (requires sudo):
```bash
make completion-install
```

Completion scripts live in [`tools/completions/`](tools/completions/).

## Quick Links

- **Installation**: `claude plugin install fda-tools@fda-tools`
- **Version**: 5.36.0
- **Repository**: [GitHub](https://github.com/andrewlasiter/fda-tools)
- **Issues**: [Report a bug](https://github.com/andrewlasiter/fda-tools/issues)
- **Contributing**: [CONTRIBUTING.md](CONTRIBUTING.md)
- **License**: MIT

## License

MIT
