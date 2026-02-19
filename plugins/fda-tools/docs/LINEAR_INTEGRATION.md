# Linear MCP Integration Setup Guide

Complete guide for integrating the Universal Multi-Agent Orchestrator with Linear for automated issue creation and agent assignment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Installation](#installation)
3. [Configuration](#configuration)
4. [Custom Fields Setup](#custom-fields-setup)
5. [Authentication](#authentication)
6. [Usage Examples](#usage-examples)
7. [Troubleshooting](#troubleshooting)
8. [API Reference](#api-reference)

---

## Prerequisites

### Required
- **Linear Account**: Team workspace with admin access
- **Linear API Key**: Personal API key with write permissions
- **Claude Code**: Version 1.0.0 or higher
- **Python**: 3.8 or higher

### Optional
- **Linear MCP Plugin**: For enhanced integration features
- **Git Integration**: For automatic branch name generation

---

## Installation

### Step 1: Install Linear MCP Plugin (Recommended)

```bash
claude plugin install linear
```

### Step 2: Verify Plugin Installation

```bash
claude plugin list | grep linear
```

Expected output:
```
linear@linear  Installed  Linear MCP integration for Claude Code
```

### Step 3: Install Python Dependencies

```bash
cd $FDA_PLUGIN_ROOT
pip3 install requests python-dateutil
```

---

## Configuration

### Step 1: Get Linear API Key

1. Go to https://linear.app/settings/api
2. Click "Create new personal API key"
3. Name it "FDA Tools Orchestrator"
4. Copy the API key (starts with `lin_api_`)

### Step 2: Store API Key Securely

**Option A: Environment Variable (Recommended)**

Add to `~/.bashrc` or `~/.zshrc`:
```bash
export LINEAR_API_KEY="lin_api_your_key_here"
```

Reload shell:
```bash
source ~/.bashrc  # or ~/.zshrc
```

**Option B: .env File**

Create `.env` in plugin root:
```bash
cd $FDA_PLUGIN_ROOT
echo "LINEAR_API_KEY=lin_api_your_key_here" > .env
```

Add to `.gitignore`:
```bash
echo ".env" >> .gitignore
```

### Step 3: Configure Linear Team

The orchestrator needs your Linear team ID. Get it from:
```bash
# Using Linear MCP plugin
/linear:list_teams

# Or using Linear API directly
curl https://api.linear.app/graphql \
  -H "Authorization: YOUR_LINEAR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "{ teams { nodes { id name } } }"}'
```

Store your team ID:
```bash
export LINEAR_TEAM_ID="5e4df6d3-2006-4e51-b862-b65ba71bff04"  # Replace with your team ID
```

---

## Custom Fields Setup

The orchestrator uses two custom fields for agent assignment:

### 1. Delegate Field (FDA Expert)

**Setup:**
1. Go to Linear → Settings → Custom Fields
2. Click "Create custom field"
3. Configure:
   - **Name**: `delegate`
   - **Type**: `User`
   - **Teams**: Select your FDA Tools team
   - **Description**: "FDA regulatory expert assigned to this issue"

### 2. Reviewers Field (Technical Experts)

**Setup:**
1. Go to Linear → Settings → Custom Fields
2. Click "Create custom field"
3. Configure:
   - **Name**: `reviewers`
   - **Type**: `User` (multi-select)
   - **Teams**: Select your FDA Tools team
   - **Description**: "Technical experts reviewing this issue"

### Field Usage

The orchestrator automatically populates these fields:

- **Assignee**: Primary technical expert (e.g., `voltagent-qa-sec:code-reviewer`)
- **Delegate**: FDA regulatory expert (e.g., `fda-quality-expert`)
- **Reviewers**: Additional technical reviewers (e.g., `documentation-engineer`)

---

## Authentication

### Verify Authentication

Test your Linear API key:

```bash
python3 $FDA_PLUGIN_ROOT/scripts/test_linear_auth.py
```

Expected output:
```
✅ Linear API authentication successful
   Team: FDA tools
   Workspace: Quaella
   Projects: 3
```

### Authentication Troubleshooting

**Error: "Invalid API key"**
- Check API key format (should start with `lin_api_`)
- Regenerate API key in Linear settings
- Verify environment variable is set: `echo $LINEAR_API_KEY`

**Error: "Unauthorized"**
- Verify API key has write permissions
- Check team membership
- Confirm workspace access

---

## Usage Examples

### Example 1: Create Issues from Code Review

**Single file review:**
```bash
cd $FDA_PLUGIN_ROOT
python3 scripts/universal_orchestrator.py execute \
  --task "Security audit of authentication system" \
  --files "scripts/linear_integrator.py" \
  --create-linear \
  --max-agents 8
```

**Expected output:**
```
✅ Created 3 Linear issues:
   FDA-99 [SECURITY] API key exposure in authentication (CRITICAL)
   FDA-100 [TESTING] Missing test coverage for error paths (HIGH)
   FDA-101 [DOCUMENTATION] API documentation incomplete (MEDIUM)
```

### Example 2: Assign Agents to Existing Issue

```bash
python3 scripts/universal_orchestrator.py assign \
  --issue "FDA-98" \
  --task "Add comprehensive architecture documentation"
```

**Expected output:**
```
✅ Assigned agents to FDA-98:
   Assignee: voltagent-biz:technical-writer
   Delegate: fda-documentation-expert
   Reviewers:
     - voltagent-dev-exp:documentation-engineer
     - voltagent-biz:ux-researcher
```

### Example 3: Batch Process Multiple Issues

```bash
python3 scripts/universal_orchestrator.py batch \
  --issues "FDA-92,FDA-93,FDA-94,FDA-95,FDA-96" \
  --json
```

**Expected output (JSON):**
```json
{
  "processed": 5,
  "success": 5,
  "failed": 0,
  "issues": [
    {
      "issue_id": "FDA-92",
      "assignee": "voltagent-qa-sec:security-auditor",
      "delegate": "fda-cybersecurity-expert",
      "reviewers": ["code-reviewer"]
    }
    // ... 4 more issues
  ]
}
```

---

## Troubleshooting

### Issue Creation Failures

**Problem:** "Failed to create Linear issue"

**Solutions:**
1. Verify API key: `echo $LINEAR_API_KEY`
2. Check team permissions
3. Verify project exists: `/linear:list_projects`
4. Check rate limits: Max 100 requests/minute

**Problem:** "Delegate field not found"

**Solutions:**
1. Create custom field "delegate" (User type)
2. Enable field for your team
3. Restart orchestrator

### Agent Assignment Issues

**Problem:** "Agent not found in registry"

**Solutions:**
1. Update agent registry: `cd $FDA_PLUGIN_ROOT && git pull`
2. Verify agent name: Check `agent_registry.py`
3. Use closest alternative agent

**Problem:** "No agents selected for task"

**Solutions:**
1. Check task description clarity
2. Add language/framework hints
3. Use `--max-agents` to increase team size

### Performance Issues

**Problem:** "Orchestrator slow for large codebases"

**Solutions:**
1. Limit file count: `--files` with specific paths
2. Use `--max-agents` to reduce team size
3. Process in batches: `batch` command with `--batch-size 10`

---

## API Reference

### LinearIntegrator Class

```python
from linear_integrator import LinearIntegrator

integrator = LinearIntegrator(
    api_key="lin_api_...",
    team_id="5e4df6d3-...",
    project_id="abc123..."  # Optional
)
```

#### Methods

**create_issue()**
```python
issue_id = integrator.create_issue(
    title="[SECURITY] API key exposure",
    description="Detailed issue description...",
    assignee="voltagent-qa-sec:security-auditor",
    delegate="fda-cybersecurity-expert",
    reviewers=["code-reviewer"],
    priority=1,  # 0=None, 1=Urgent, 2=High, 3=Normal, 4=Low
    labels=["security", "critical"]
)
```

**assign_agents_to_issue()**
```python
integrator.assign_agents_to_issue(
    issue_id="FDA-98",
    assignee="technical-writer",
    delegate="fda-documentation-expert",
    reviewers=["documentation-engineer"]
)
```

**create_issues_from_findings()**
```python
from execution_coordinator import AggregatedFindings

issue_ids = integrator.create_issues_from_findings(
    findings=aggregated_findings,
    review_team=review_team,
    project_name="FDA Plugin"
)
# Returns: List[str] (issue IDs)
```

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `LINEAR_API_KEY` | Linear personal API key | Yes | `lin_api_xyz...` |
| `LINEAR_TEAM_ID` | Team UUID | Yes | `5e4df6d3-2006-...` |
| `LINEAR_PROJECT_ID` | Default project UUID | No | `abc123...` |
| `LINEAR_RATE_LIMIT` | Calls per minute | No | `100` (default) |

### GraphQL Queries

**Create Issue:**
```graphql
mutation CreateIssue($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    issue {
      id
      identifier
      title
      url
    }
  }
}
```

**Update Issue (Assign Agents):**
```graphql
mutation UpdateIssue($id: String!, $input: IssueUpdateInput!) {
  issueUpdate(id: $id, input: $input) {
    issue {
      id
      assignee { name }
      # delegate and reviewers custom fields
    }
  }
}
```

---

## Best Practices

### 1. Issue Creation
- Use descriptive titles with severity prefix: `[CRITICAL]`, `[HIGH]`, `[MEDIUM]`, `[LOW]`
- Include code snippets in issue descriptions
- Link to relevant files using GitHub URLs
- Tag with appropriate labels for filtering

### 2. Agent Assignment
- Assign FDA expert as delegate for regulatory oversight
- Use technical expert as primary assignee
- Add 1-3 reviewers for multi-perspective review
- Match agent expertise to issue type (security → security-auditor)

### 3. Workflow
- Run `review` command before `execute` to preview findings
- Use `assign` to add agents to manually created issues
- Process large batches using `batch` command with `--batch-size`
- Monitor rate limits (100 calls/min)

### 4. Performance
- Cache agent registry data (reloaded every 24 hours)
- Batch GraphQL queries when creating multiple issues
- Use circuit breaker pattern for API failures (built-in)
- Implement exponential backoff for retries (built-in)

---

## Advanced Configuration

### Custom Linear Workflows

Create workflow states in Linear:
1. **Backlog** (default)
2. **In Progress** (when agent starts work)
3. **In Review** (when reviewers evaluate)
4. **Done** (when issue resolved)

The orchestrator automatically sets state to "Backlog" on creation.

### Integration with GitHub

Link Linear issues to GitHub PRs:

```bash
# Create issue with GitHub link
python3 scripts/universal_orchestrator.py execute \
  --task "Fix authentication bug" \
  --files "api/auth.py" \
  --create-linear \
  --github-pr "https://github.com/user/repo/pull/123"
```

### Slack Notifications

Configure Linear → Settings → Integrations → Slack to receive notifications:
- When issues are created by orchestrator
- When agents are assigned
- When issues transition to "Done"

---

## Security Considerations

### API Key Security
- ✅ **DO**: Store API key in environment variables or `.env` file
- ✅ **DO**: Add `.env` to `.gitignore`
- ✅ **DO**: Rotate API keys quarterly
- ❌ **DON'T**: Commit API keys to Git
- ❌ **DON'T**: Share API keys in Slack/email
- ❌ **DON'T**: Use API keys in client-side code

### Rate Limiting
- Built-in rate limiter: 100 calls/minute
- Circuit breaker: 5 failures = 60 second cooldown
- Exponential backoff: 2s, 4s, 8s delays

### Error Handling
- All API calls wrapped in try/except
- Graceful degradation on API failures
- Detailed error logging for debugging
- Partial results on partial failures

---

## Support

### Documentation
- [ORCHESTRATOR_ARCHITECTURE.md](../ORCHESTRATOR_ARCHITECTURE.md) - System architecture
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues and solutions
- [FDA_EXAMPLES.md](FDA_EXAMPLES.md) - FDA-specific workflows

### Get Help
- **GitHub Issues**: [Report a bug](https://github.com/andrewlasiter/fda-tools/issues)
- **Linear Docs**: https://developers.linear.app/docs
- **Claude Code**: https://claude.ai/code

---

**Last Updated:** 2026-02-19
**Version:** 1.0.0
