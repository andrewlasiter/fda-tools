# FDA Tools OpenClaw Skill

> **Version:** 1.0.0 | **Phase:** 3 of TICKET-017 | **Status:** Complete

OpenClaw skill that provides FDA 510(k)/PMA regulatory intelligence via messaging
platforms (WhatsApp, Telegram, Slack, Discord). Wraps the Phase 2 HTTP Bridge Server
to deliver 68 FDA commands through a secure, audited pipeline.

## Overview

This skill enables FDA regulatory professionals to access the full FDA Tools plugin
through conversational messaging interfaces. All requests are routed through a
SecurityGateway that enforces data classification, LLM provider routing, and
channel access controls.

### Architecture

```
Messaging Platform (WhatsApp, Telegram, Slack, Discord)
        |
        v
OpenClaw Gateway (ws://127.0.0.1:18789)
        |  trigger phrase match
        v
FDA Tools Skill (this package)
        |  HTTP POST/GET
        v
FDA Bridge Server (http://localhost:18790)
        |  SecurityGateway + AuditLogger
        v
FDA Tools Plugin (68 commands)
        |
        v
openFDA API, ClinicalTrials.gov, PubMed, GUDID
```

### Security Model

All data is classified into 3 tiers with strict enforcement:

| Tier | Data Types | LLM Provider | Channels |
|------|-----------|--------------|----------|
| PUBLIC | FDA databases, published 510(k)s, MAUDE, recalls | Any (cloud OK) | All |
| RESTRICTED | Derived analysis, intelligence reports | Cloud with warnings | Most (with disclaimers) |
| CONFIDENTIAL | Device specs, drafts, submissions, project data | Local (Ollama) ONLY | File output ONLY |

The SecurityGateway enforces these rules immutably. Confidential data will be
**blocked** on messaging channels with a clear error message.

## Prerequisites

- **Node.js** >= 18.0.0
- **Python** >= 3.9 (for the bridge server)
- **OpenClaw** installed and configured
- **FDA Tools Plugin** installed in Claude Code
- Network access to localhost ports 18789 (OpenClaw) and 18790 (bridge)

## Installation

### Step 1: Copy Skill to OpenClaw

```bash
# From the FDA tools repository
cp -r openclaw-skill ~/.openclaw/workspace/skills/fda-tools
```

### Step 2: Install Dependencies

```bash
cd ~/.openclaw/workspace/skills/fda-tools
npm install
npm run build
```

### Step 3: Start the FDA Bridge Server

```bash
cd /path/to/fda-predicate-assistant
python3 bridge/server.py
```

The bridge server starts on `http://localhost:18790`. Verify with:

```bash
curl http://localhost:18790/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "commands_available": 68,
  "sessions_active": 0
}
```

### Step 4: Restart OpenClaw

Restart the OpenClaw application to load the new skill. The skill will
be activated when trigger phrases are detected in user messages.

### Step 5: Verify

Send a message through your messaging platform:

> "fda research for product code DQY"

You should receive a response with predicate candidates, testing strategy,
and regulatory intelligence for cardiovascular catheters.

## Configuration

### Bridge Server URL

The skill connects to `http://localhost:18790` by default. To change this,
modify the `bridge_url` in SKILL.md frontmatter or set the environment
variable before starting OpenClaw:

```bash
export FDA_BRIDGE_URL=http://localhost:18790
```

### Security Configuration

Security is configured via `~/.claude/fda-tools.security.toml` (read by the
bridge server). This file should be read-only (mode 444) and defines:

- Data classification patterns
- LLM provider routing
- Channel access lists
- Audit log location and retention

See the Phase 1 security documentation for configuration details.

### LLM Provider Setup

For CONFIDENTIAL data processing, you need a local LLM:

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama2

# Verify it runs
ollama list
```

The bridge server auto-detects Ollama at `http://localhost:11434`.

## Usage Examples

### Research (PUBLIC -- safe on any channel)

> User: "Find predicates for a cardiovascular catheter, product code DQY"
>
> Skill: Executes `research --product-code DQY` via bridge
> Returns: Predicate list, testing strategy, regulatory intelligence

### Validation (PUBLIC)

> User: "Validate K240001"
>
> Skill: Executes `validate K240001` via bridge
> Returns: Device details, applicant, clearance date, predicate chain

### Safety Analysis (PUBLIC)

> User: "Show adverse events for electrosurgical devices GEI"
>
> Skill: Executes `safety --product-code GEI` via bridge
> Returns: MAUDE event analysis, recall history, safety signals

### Draft Section (CONFIDENTIAL -- blocked on messaging)

> User: "Draft the device description for my project stent-001"
>
> Skill: Attempts `draft device-description --project stent-001`
> Returns: SECURITY BLOCK -- confidential data not permitted on messaging.
> Suggests using file output or local terminal instead.

### Any Command (Generic)

> User: "Calculate shelf life with Q10=2, Taa=55, Trt=25, time=2 years"
>
> Skill: Executes `calc shelf-life --q10 2 --taa 55 --trt 25 --time 2`
> Returns: Accelerated aging calculations per ASTM F1980

## Available Tools

The skill exposes 5 tools to the OpenClaw agent:

| Tool | Description | Primary Use |
|------|-------------|------------|
| `fda_research` | Structured predicate research | Most common research queries |
| `fda_validate` | Device number validation | K/P/DEN number lookup |
| `fda_analyze` | Multi-source data analysis | Project and pipeline analysis |
| `fda_draft` | Submission section drafting | Regulatory prose generation |
| `fda_command` | Generic command wrapper | All 68 commands |

The agent selects the appropriate tool based on the user's intent. The generic
`fda_command` tool serves as a fallback for commands not covered by the
specialized tools.

## Development

### Project Structure

```
openclaw-skill/
  SKILL.md              # Skill manifest (triggers, security, command list)
  README.md             # This file
  index.ts              # Skill entry point and registration
  package.json          # NPM package configuration
  tsconfig.json         # TypeScript compiler configuration
  jest.config.json      # Jest test configuration
  bridge/
    client.ts           # HTTP client with retry logic
    types.ts            # TypeScript type definitions
  tools/
    fda_research.ts     # Research tool (structured)
    fda_validate.ts     # Validate tool (structured)
    fda_analyze.ts      # Analyze tool (structured)
    fda_draft.ts        # Draft tool (structured)
    fda_generic.ts      # Generic wrapper (all commands)
  tests/
    integration.test.ts # Structural validation tests
```

### Building

```bash
npm run build         # Compile TypeScript
npm run typecheck     # Type-check without emitting
npm run lint          # Run ESLint
```

### Testing

```bash
npm test              # Run all tests
npm run test:watch    # Watch mode
```

The test suite includes 60+ structural validation tests that verify:
- SKILL.md manifest correctness
- Tool export integrity
- Bridge client structure
- Type definition completeness
- Package configuration validity
- Error handling coverage
- Security model enforcement
- File structure completeness

### Adding a New Tool

1. Create `tools/fda_<name>.ts` following the pattern in existing tools
2. Import and register in `index.ts`
3. Add tests in `tests/integration.test.ts`
4. Update SKILL.md if adding new trigger phrases

## Troubleshooting

### "Bridge server not running"

The FDA Bridge Server must be running on `http://localhost:18790`.

```bash
# Check if running
curl http://localhost:18790/health

# Start if not running
cd /path/to/fda-predicate-assistant
python3 bridge/server.py
```

### "Security violation" errors

The SecurityGateway blocks certain operations based on channel and
data classification. Common issues:

- **Drafting on WhatsApp:** Draft commands access CONFIDENTIAL data.
  Use file output or local terminal instead.
- **Missing security config:** Create `~/.claude/fda-tools.security.toml`
  or run in permissive mode (not recommended for production).

### "Command not found"

Verify the command name against the list in SKILL.md or query:

```bash
curl http://localhost:18790/commands
```

### Timeout errors

Long-running commands (research with deep analysis, batch operations)
may time out. The client retries 3 times with exponential backoff.
If timeouts persist, try narrowing query parameters.

### OpenClaw does not detect the skill

1. Verify the skill is in `~/.openclaw/workspace/skills/fda-tools/`
2. Check that SKILL.md has valid frontmatter
3. Restart OpenClaw
4. Check OpenClaw logs for skill loading errors

## API Reference

The skill communicates with the FDA Bridge Server via REST API:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server health and LLM provider status |
| `/commands` | GET | List all 68 FDA commands |
| `/execute` | POST | Execute an FDA command |
| `/session` | POST | Create or retrieve a session |
| `/session/{id}` | GET | Get session details |
| `/session/{id}/questions` | GET | Get pending questions |
| `/session/{id}/answer` | POST | Submit answer to pending question |
| `/sessions` | GET | List active sessions |
| `/tools` | GET | List available tool emulators |
| `/audit/integrity` | GET | Verify audit log integrity |

## License

MIT

## Related Documentation

- Phase 1: Security Foundation (`lib/security_gateway.py`, `lib/audit_logger.py`)
- Phase 2: HTTP Bridge Server (`bridge/server.py`, `bridge/session_manager.py`)
- Phase 3: OpenClaw Skill (this package)
- FDA Tools Plugin: 68 commands in `commands/*.md`
