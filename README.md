![Version](https://img.shields.io/badge/version-5.4.0-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Commands](https://img.shields.io/badge/commands-33-orange)
![Agents](https://img.shields.io/badge/agents-4-purple)
![Tests](https://img.shields.io/badge/tests-533-brightgreen)
![Claude Code](https://img.shields.io/badge/Claude_Code-plugin-blueviolet)
![FDA 510(k)](https://img.shields.io/badge/FDA-510(k)-red)

# FDA Tools — Claude Code Plugin Marketplace

AI-powered tools for FDA medical device regulatory work. Built for regulatory affairs professionals working on 510(k) submissions.

## Install

From your terminal:

```bash
claude plugin marketplace add andrewlasiter/fda-predicate-assistant-plugin
claude plugin install fda-predicate-assistant@fda-tools
```

Or from inside a Claude Code or Claude Desktop session:

```
/plugin marketplace add andrewlasiter/fda-predicate-assistant-plugin
/plugin install fda-predicate-assistant@fda-tools
```

Start a new session after installing to load the plugin.

## What You Can Do

- **Find predicates** — Search FDA databases, trace predicate lineage, manually propose predicates, and validate device numbers
- **Analyze safety** — Pull MAUDE adverse events, recall history, and UDI/GUDID records for any product code or device
- **Look up standards** — Search FDA Recognized Consensus Standards by product code, standard number, or keyword
- **Plan your submission** — Get pathway recommendations, generate testing plans, and prepare Pre-Sub packages
- **Generate documents** — Substantial equivalence tables, submission outlines, regulatory prose drafts for 18 eSTAR sections
- **Run calculators** — Shelf life (ASTM F1980 accelerated aging), sample size, and sterilization dose calculations
- **Assemble for filing** — eSTAR-structured packages, import/export eSTAR XML, traceability matrices, consistency checks
- **Simulate FDA review** — Pre-check your submission against RTA checklists and identify likely deficiencies before filing
- **Run it all at once** — Full autonomous pipeline from extraction through SE comparison
- **Monitor changes** — Watch for new clearances, recalls, MAUDE events, and guidance updates

## Plugins

### [FDA Predicate Assistant](./plugins/fda-predicate-assistant/)

33 commands, 4 autonomous agents, and 533 tests covering every stage of the 510(k) workflow — from predicate research through CDRH Portal submission. Integrates with all 7 openFDA Device API endpoints and bundles Python scripts for batch PDF processing.

See the [full documentation](./plugins/fda-predicate-assistant/README.md) for commands, agents, installation details, and quick start examples.

## License

MIT
