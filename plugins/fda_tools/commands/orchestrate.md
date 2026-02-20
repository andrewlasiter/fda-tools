---
description: Universal Multi-Agent Orchestrator - JIT agent assignment and comprehensive code review
allowed-tools: Bash, Read, Glob, Grep, Write, AskUserQuestion
argument-hint: "[review|assign|batch|execute] [options]"
---

# Universal Multi-Agent Orchestrator

> **AI-powered JIT agent assignment and multi-dimensional code review**

Automatically selects optimal agent teams from 167 specialized agents across 12 categories for comprehensive, multi-dimensional review covering security, testing, performance, documentation, compliance, architecture, and operations.

## Overview

The Universal Multi-Agent Orchestrator provides 4 main workflows:

1. **`review`** - Comprehensive code review with multi-agent team
2. **`assign`** - Assign agents to existing Linear issue
3. **`batch`** - Process multiple Linear issues in batch
4. **`execute`** - Full workflow: review + create Linear issues

### Key Capabilities

- **167 Agents** across 12 categories (FDA, QA/Security, Languages, Infrastructure, Data/AI, Core Dev, Domains, Meta, Business, Dev Experience, Research, Plugins)
- **8 Review Dimensions**: code_quality, security, testing, documentation, performance, compliance, architecture, operations
- **Multi-dimensional Selection**: Language matching (30%), dimension matching (40%), domain matching (20%), model tier (10%)
- **3 Coordination Patterns**: peer-to-peer (≤3 agents), master-worker (4-6 agents), hierarchical (≥7 agents)
- **Dual-Assignment Model**: FDA expert (delegate) + Technical expert (assignee) + Reviewers

---

## Resolve Plugin Root

**Before running any commands**, resolve the plugin install path:

```bash
FDA_PLUGIN_ROOT=$(python3 -c "
import json, os
f = os.path.expanduser('~/.claude/plugins/installed_plugins.json')
if os.path.exists(f):
    d = json.load(open(f))
    for k, v in d.get('plugins', {}).items():
        if k.startswith('fda-tools@'):
            for e in v:
                p = e.get('installPath', '')
                if os.path.isdir(p):
                    print(p); exit()
print('')
")
echo "FDA_PLUGIN_ROOT=$FDA_PLUGIN_ROOT"
```

---

## Command 1: `review` - Comprehensive Code Review

Analyze task, select optimal agent team, execute multi-agent review, aggregate findings.

### Usage

```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py review \
    --task "Fix authentication vulnerability in FastAPI endpoint" \
    --files "api/auth.py,api/db.py" \
    --max-agents 10
```

### Options

- `--task` (required): Task description
- `--files` (required): Comma-separated file paths
- `--max-agents`: Maximum team size (default: 10)
- `--json`: Output results as JSON

### Output

- Task profile (type, languages, frameworks, domains, complexity)
- Selected agent team (core, language, domain agents, coordinator)
- Execution plan (4 phases with dependencies)
- Aggregated findings (by severity, type, file)

### Example

```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py review \
    --task "Security audit of authentication system" \
    --files "api/auth.py,api/oauth.py,api/tokens.py" \
    --max-agents 12
```

**Output:**
```
======================================================================
COMPREHENSIVE CODE REVIEW
======================================================================

1. Analyzing task...
   Task type: security_audit
   Languages: python
   Complexity: high

2. Selecting agent team...
   Team size: 8 agents
   Core agents: 4
   Language agents: 2
   Domain agents: 1
   Coordinator: voltagent-meta:multi-agent-coordinator

3. Creating execution plan...
   Phases: 4
   Estimated hours: 18
   Coordination: hierarchical

4. Executing multi-agent review...
   Total findings: 12
   CRITICAL: 2
   HIGH: 5
   MEDIUM: 3
   LOW: 2
```

---

## Command 2: `assign` - Assign Agents to Linear Issue

Analyze existing Linear issue and automatically assign optimal agents using dual-assignment model.

### Usage

```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py assign \
    --issue-id "FDA-92" \
    --auto
```

### Options

- `--issue-id` (required): Linear issue ID (e.g., "FDA-92")
- `--auto`: Auto-select agents based on issue content (default: true)
- `--task`: Manual task description (if not --auto)
- `--json`: Output results as JSON

### Dual-Assignment Model

1. **👔 FDA Expert (Delegate)**: Reviews from FDA compliance perspective, validates regulatory requirements
2. **💻 Technical Expert (Assignee)**: Implements fixes, tests, documentation
3. **👥 Reviewers**: Additional code quality, security, testing validation

### Output

- Assignee (implementation agent)
- Delegate (FDA expert, if applicable)
- Reviewers (review agents)

### Example

```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py assign \
    --issue-id "FDA-33" \
    --auto
```

**Output:**
```
======================================================================
ASSIGN AGENTS TO LINEAR ISSUE
======================================================================

Issue: FDA-33
Mode: Auto-assignment

Assigned agents:
  Assignee: voltagent-infra:devops-engineer
  Delegate: fda-software-ai-expert
  Reviewers: 3
    - voltagent-qa-sec:code-reviewer
    - voltagent-lang:python-pro
    - fda-quality-expert
```

---

## Command 3: `batch` - Batch Process Linear Issues

Process multiple Linear issues in batch, assigning agents to each.

### Usage

```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py batch \
    --issue-ids "FDA-92,FDA-93,FDA-94,FDA-95"
```

### Options

- `--issue-ids` (required): Comma-separated Linear issue IDs
- `--json`: Output results as JSON

### Output

- Success/error status for each issue
- Assigned agents for each successful issue

### Example

```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py batch \
    --issue-ids "FDA-30,FDA-31,FDA-32,FDA-33,FDA-34"
```

**Output:**
```
======================================================================
BATCH PROCESS LINEAR ISSUES
======================================================================

Processing 5 issues...

Results:
  Success: 5
  Errors: 0

  FDA-30: ✓ Assigned to voltagent-qa-sec:code-reviewer
  FDA-31: ✓ Assigned to voltagent-qa-sec:code-reviewer
  FDA-32: ✓ Assigned to voltagent-lang:python-pro
  FDA-33: ✓ Assigned to voltagent-infra:devops-engineer
  FDA-34: ✓ Assigned to voltagent-lang:python-pro
```

---

## Command 4: `execute` - Full Workflow

Complete workflow: comprehensive review + create Linear issues from findings.

### Usage

```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py execute \
    --task "Security audit of bridge server" \
    --files "bridge/server.py,bridge/auth.py" \
    --create-linear \
    --max-agents 12
```

### Options

- `--task` (required): Task description
- `--files` (required): Comma-separated file paths
- `--create-linear`: Create Linear issues from findings
- `--max-agents`: Maximum team size (default: 10)
- `--json`: Output results as JSON

### Workflow

1. Analyze task → generate profile
2. Select optimal agent team
3. Create execution plan
4. Execute multi-agent review
5. Create Linear issues (if --create-linear)

### Output

- Full review results
- List of created Linear issues

### Example

```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py execute \
    --task "Major refactoring of authentication system" \
    --files "api/auth.py,api/oauth.py,api/tokens.py,api/sessions.py" \
    --create-linear \
    --max-agents 15
```

**Output:**
```
======================================================================
FULL ORCHESTRATION WORKFLOW
======================================================================

[... review output ...]

5. Creating Linear issues from findings...
   Created 8 Linear issues
```

---

## Agent Categories (167 Total)

### 1. FDA Regulatory (23 agents)
- fda-quality-expert, fda-software-ai-expert, fda-clinical-expert, fda-biocompatibility-expert, fda-sterilization-expert, etc.

### 2. QA/Security (15 agents)
- voltagent-qa-sec:code-reviewer, security-auditor, test-automator, qa-expert, penetration-tester, etc.

### 3. Languages (24 agents)
- voltagent-lang:python-pro, typescript-pro, javascript-pro, rust-engineer, golang-pro, java-architect, etc.

### 4. Infrastructure (16 agents)
- voltagent-infra:devops-engineer, kubernetes-specialist, cloud-architect, terraform-engineer, sre-engineer, etc.

### 5. Data & AI (12 agents)
- voltagent-data-ai:ml-engineer, data-scientist, data-engineer, ai-engineer, llm-architect, etc.

### 6. Core Development (10 agents)
- voltagent-core-dev:fullstack-developer, frontend-developer, backend-developer, api-designer, etc.

### 7. Domains (12 agents)
- voltagent-domains:fintech-engineer, blockchain-developer, iot-engineer, game-developer, etc.

### 8. Meta-Coordination (9 agents)
- voltagent-meta:multi-agent-coordinator, task-distributor, workflow-orchestrator, etc.

### 9. Business (11 agents)
- voltagent-biz:product-manager, technical-writer, business-analyst, scrum-master, etc.

### 10. Dev Experience (13 agents)
- voltagent-dev-exp:refactoring-specialist, mcp-developer, cli-developer, tooling-engineer, etc.

### 11. Research (6 agents)
- voltagent-research:market-researcher, competitive-analyst, trend-analyst, etc.

### 12. Plugins (16 agents)
- agent-sdk-dev, code-simplifier, feature-dev, pr-review-toolkit, etc.

---

## Tips

1. **Start small**: Use `--max-agents 5` for quick reviews, `--max-agents 15` for comprehensive audits
2. **Language detection**: System auto-detects languages from file extensions and task description
3. **Domain matching**: Healthcare/FDA tasks automatically get FDA expert delegates
4. **Batch processing**: Use `batch` command for assigning agents to multiple existing issues
5. **JSON output**: Add `--json` flag for programmatic consumption

---

## Examples

### Example 1: Quick Security Review
```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py review \
    --task "Quick security check for auth endpoint" \
    --files "api/auth.py" \
    --max-agents 5
```

### Example 2: Comprehensive FDA Review
```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py execute \
    --task "FDA 510(k) software validation review" \
    --files "device/algorithm.py,device/validation.py" \
    --create-linear \
    --max-agents 12
```

### Example 3: Assign Agents to All Open Issues
```bash
# Get open issue IDs from Linear
ISSUE_IDS="FDA-90,FDA-91,FDA-92,FDA-93"

python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py batch \
    --issue-ids "$ISSUE_IDS"
```

### Example 4: Full Stack Feature Review
```bash
python3 $FDA_PLUGIN_ROOT/scripts/universal_orchestrator.py review \
    --task "Review new payment processing feature" \
    --files "api/payment.py,frontend/PaymentForm.tsx,tests/test_payment.py" \
    --max-agents 8
```

---

## Notes

- **Simulation Mode**: Current implementation simulates agent invocation. Production would use Task tool for actual agent execution.
- **Linear Integration**: Framework for Linear MCP tools is in place. Production would call actual Linear APIs.
- **Extensible**: Easy to add new agents by updating the UNIVERSAL_AGENT_CATALOG in agent_registry.py
- **Performance**: Parallel agent execution where possible, sequential for dependencies

---

## Architecture

```
Universal Orchestrator
├── UniversalAgentRegistry (167 agents)
├── TaskAnalyzer (AI classification)
├── AgentSelector (multi-dimensional selection)
├── ExecutionCoordinator (4-phase workflow)
└── LinearIntegrator (dual-assignment model)
```

🚀 **Universal Multi-Agent Orchestrator** - Comprehensive, AI-powered code review at scale
