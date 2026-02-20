# Universal Multi-Agent Orchestrator - Architecture

## System Overview

The Universal Multi-Agent Orchestrator is a comprehensive JIT (Just-In-Time) agent orchestration system that automatically selects and coordinates optimal teams of specialized agents across 167 agents in 12 categories for multi-dimensional code review and issue management.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Universal Orchestrator                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │                  CLI Entry Point                          │  │
│  │  • review   - Comprehensive code review                   │  │
│  │  • assign   - Assign agents to Linear issue               │  │
│  │  • batch    - Process multiple Linear issues              │  │
│  │  • execute  - Full workflow (review + create issues)      │  │
│  └──────────────────────────────────────────────────────────┘  │
│          ↓                ↓                 ↓                    │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐       │
│  │  Task        │→ │   Agent      │→ │   Execution     │       │
│  │  Analyzer    │  │   Selector   │  │   Coordinator   │       │
│  └──────────────┘  └──────────────┘  └─────────────────┘       │
│                                              ↓                   │
│                                      ┌──────────────────┐        │
│                                      │  Linear          │        │
│                                      │  Integrator      │        │
│                                      └──────────────────┘        │
│                                              ↓                   │
│                                      [ Linear Issues ]           │
└─────────────────────────────────────────────────────────────────┘

Data Flow:
1. Task → TaskAnalyzer → TaskProfile (languages, dimensions, complexity)
2. TaskProfile → AgentSelector → ReviewTeam (core, language, domain agents)
3. ReviewTeam → ExecutionCoordinator → ExecutionPlan (4 phases)
4. ExecutionPlan → Execute → AggregatedResults (findings by severity)
5. AggregatedResults → LinearIntegrator → Linear Issues (with agent assignments)
```

## Core Components

### 1. Universal Agent Registry

**File:** `agent_registry.py`
**Lines:** 1,200+ (extended from original)

#### Responsibilities
- Discovers and catalogs 167 agents across 12 categories
- Provides multi-dimensional search (dimension, language, category, domain)
- Maintains agent metadata (category, model tier, review dimensions, languages)

#### Agent Categories (167 total)
1. **FDA Regulatory** (23 agents): fda-quality-expert, fda-software-ai-expert, fda-clinical-expert, etc.
2. **QA/Security** (15 agents): security-auditor, code-reviewer, penetration-tester, etc.
3. **Languages** (24 agents): python-pro, typescript-pro, rust-engineer, golang-pro, etc.
4. **Infrastructure** (16 agents): devops-engineer, kubernetes-specialist, cloud-architect, etc.
5. **Data & AI** (12 agents): ml-engineer, data-scientist, llm-architect, etc.
6. **Core Development** (10 agents): fullstack-developer, frontend-developer, api-designer, etc.
7. **Domains** (12 agents): fintech-engineer, blockchain-developer, iot-engineer, etc.
8. **Meta-Coordination** (9 agents): multi-agent-coordinator, task-distributor, etc.
9. **Business** (11 agents): product-manager, technical-writer, scrum-master, etc.
10. **Dev Experience** (13 agents): refactoring-specialist, mcp-developer, tooling-engineer, etc.
11. **Research** (6 agents): market-researcher, competitive-analyst, trend-analyst, etc.
12. **Plugins** (16 agents): code-simplifier, feature-dev agents, pr-review-toolkit agents, etc.

#### Key Methods
```python
discover_all_agents() → Dict[str, List[str]]
find_agents_by_review_dimension(dimension: str) → List[str]
find_agents_by_language(language: str) → List[str]
find_agents_by_category(category: str) → List[str]
```

---

### 2. Task Analyzer

**File:** `task_analyzer.py`
**Lines:** 450 (new)

#### Responsibilities
- AI-powered task classification
- Language/framework/domain detection
- Review dimension scoring (0-1 scale)
- Complexity estimation
- Linear issue metadata extraction

#### Detection Patterns

**Languages:** Python, TypeScript, JavaScript, Rust, Go, Java, C++, C#, PHP, Ruby, Swift, Kotlin, Elixir

**Frameworks:** React, FastAPI, Django, Spring, Next.js, Vue, Angular, Rails, Laravel, Flask

**Domains:** Healthcare/FDA, Fintech/Payment, Blockchain, API, IoT, Gaming, Security

#### Review Dimensions (8)
1. **code_quality** (0-1): Refactoring, maintainability, best practices
2. **security** (0-1): Vulnerabilities, authentication, authorization, encryption
3. **testing** (0-1): Coverage, test quality, edge cases
4. **documentation** (0-1): API docs, comments, README, examples
5. **performance** (0-1): Optimization, latency, bottlenecks
6. **compliance** (0-1): FDA, HIPAA, PCI, regulatory requirements
7. **architecture** (0-1): Design patterns, system structure, scalability
8. **operations** (0-1): Deployment, monitoring, incident response

#### Example Output
```python
TaskProfile(
    task_type="security_audit",
    languages=["python", "typescript"],
    frameworks=["fastapi", "react"],
    domains=["healthcare", "api"],
    review_dimensions={
        "security": 0.9,
        "code_quality": 0.7,
        "testing": 0.6,
        "compliance": 0.5,
    },
    complexity="high",
    estimated_scope="days",
    critical_files=["api/auth.py", "frontend/Login.tsx"],
    keywords=["authentication", "security", "vulnerability"],
)
```

---

### 3. Agent Selector

**File:** `agent_selector.py`
**Lines:** 500 (new)

#### Responsibilities
- Multi-dimensional team selection
- Weighted agent ranking
- Coordination pattern recommendation
- Implementation agent selection (for Linear assignment)

#### Selection Algorithm

**Weighted Scoring:**
- Review dimension match: **40%**
- Language match: **30%**
- Domain match: **20%**
- Model tier (opus > sonnet > haiku): **10%**

**Team Composition:**
1. **Core agents** (by review dimension): Select 1-2 agents per dimension with score > 0.3
2. **Language agents**: 1 per detected language
3. **Domain agents**: 1 per detected domain
4. **Coordinator** (if team ≥ 7): multi-agent-coordinator

**Coordination Patterns:**
- **Peer-to-peer** (≤3 agents): No coordinator, agents collaborate directly
- **Master-worker** (4-6 agents): Coordinator delegates and aggregates
- **Hierarchical** (≥7 agents): Coordinator manages sub-teams with dependencies

#### Example Output
```python
ReviewTeam(
    core_agents=[
        {"name": "voltagent-qa-sec:security-auditor", "score": 0.95},
        {"name": "voltagent-qa-sec:code-reviewer", "score": 0.85},
    ],
    language_agents=[
        {"name": "voltagent-lang:python-pro", "score": 0.90},
    ],
    domain_agents=[
        {"name": "fda-software-ai-expert", "score": 0.75},
    ],
    coordinator="voltagent-meta:multi-agent-coordinator",
    coordination_pattern="hierarchical",
    total_agents=8,
)
```

---

### 4. Execution Coordinator

**File:** `execution_coordinator.py`
**Lines:** 600 (new)

#### Responsibilities
- Multi-agent workflow orchestration
- 4-phase execution plan generation
- Result aggregation and deduplication
- Severity-based prioritization

#### 4-Phase Execution Plan

**Phase 1: Initial Analysis** (Parallel)
- Core agents (2-3): code-reviewer, architect-reviewer
- Estimated: 2 hours
- Dependencies: None

**Phase 2: Specialist Review** (Parallel)
- Specialist agents (5-8): security-auditor, test-automator, python-pro, etc.
- Estimated: 4 hours
- Dependencies: Phase 1 completion

**Phase 3: Integration Review** (Sequential)
- Coordinator: multi-agent-coordinator
- Aggregates findings, identifies patterns
- Estimated: 2 hours
- Dependencies: Phase 2 completion

**Phase 4: Issue Creation** (Sequential)
- Orchestrator: Creates Linear issues from findings
- Estimated: 1 hour
- Dependencies: Phase 3 completion

#### Result Aggregation

**Deduplication:** Findings with same location + type → merged
**Sorting:** CRITICAL > HIGH > MEDIUM > LOW
**Grouping:** By file, type, agent

---

### 5. Linear Integrator

**File:** `linear_integrator.py`
**Lines:** 480 (new)

#### Responsibilities
- Linear issue creation via MCP tools
- Dual-assignment model (assignee + delegate + reviewers)
- Issue description generation (markdown)
- Label determination and priority mapping
- Batch operations for multiple issues

#### Dual-Assignment Model

**1. Assignee** (Implementation Agent)
- Does the actual work: code, tests, documentation
- Selected based on language + task type
- Examples: python-pro, security-auditor, test-automator

**2. Delegate** (FDA Expert)
- Regulatory review & compliance validation
- Selected from FDA agents in review team
- Examples: fda-software-ai-expert, fda-quality-expert

**3. Reviewers** (Review Agents)
- Additional oversight: code quality, security, testing
- 3-5 agents from review team
- Examples: code-reviewer, penetration-tester, qa-expert

#### Linear MCP Integration

**Tools Used:**
- `mcp__plugin_linear_linear__create_issue`
- `mcp__plugin_linear_linear__get_issue`
- `mcp__plugin_linear_linear__update_issue`
- `mcp__plugin_linear_linear__create_comment`

**Error Handling:**
- Retry logic: 3 attempts, 2s initial delay, exponential backoff
- Rate limiting: 100 calls/min
- Circuit breaker: 5 failures → open, 60s recovery
- Fallback: Simulation mode if MCP tools unavailable

#### Priority Mapping
```python
"urgent"  → 1 (Linear Urgent)
"high"    → 2 (Linear High)
"medium"  → 3 (Linear Normal)
"low"     → 4 (Linear Low)
```

---

### 6. Error Handling

**File:** `error_handling.py`
**Lines:** 350 (new)

#### Components

**1. Retry Logic (`with_retry` decorator)**
```python
@with_retry(max_attempts=3, initial_delay=1.0, max_delay=60.0)
def api_call():
    ...
```
- Exponential backoff: delay × 2^attempt
- Configurable attempts and delays
- Logs all retry attempts

**2. Rate Limiter**
```python
rate_limiter = RateLimiter(calls_per_minute=100)
with rate_limiter:
    api_call()
```
- Sliding window algorithm
- Prevents API rate limit violations
- Automatic throttling

**3. Circuit Breaker**
```python
circuit_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
result = circuit_breaker.call(api_function, *args)
```
- States: CLOSED → OPEN → HALF_OPEN → CLOSED
- Fails fast after threshold
- Auto-recovery after timeout

**4. RobustAPIClient** (Combined)
```python
client = RobustAPIClient(
    max_retries=3,
    calls_per_minute=100,
    failure_threshold=5,
)
result = client.call(api_func, *args)
```
- Combines retry + rate limiting + circuit breaker
- Single interface for all error handling

---

## Usage Examples

### 1. Comprehensive Code Review

```bash
python3 universal_orchestrator.py review \
    --task "Security audit of authentication system" \
    --files "api/auth.py,api/oauth.py,api/tokens.py" \
    --max-agents 12
```

**Output:**
- Task profile (type, languages, dimensions, complexity)
- Selected team (8-12 agents across dimensions)
- Execution plan (4 phases, estimated 9 hours)
- Aggregated findings (sorted by severity)

### 2. Assign Agents to Linear Issue

```bash
python3 universal_orchestrator.py assign \
    --issue-id "FDA-92" \
    --auto
```

**Output:**
- Assignee: voltagent-qa-sec:security-auditor
- Delegate: fda-software-ai-expert
- Reviewers: 3-5 agents

### 3. Batch Process Linear Issues

```bash
python3 universal_orchestrator.py batch \
    --issue-ids "FDA-92,FDA-93,FDA-94,FDA-95"
```

**Output:**
- Success/error status for each issue
- Agent assignments for successful issues

### 4. Full Workflow (Review + Create Issues)

```bash
python3 universal_orchestrator.py execute \
    --task "Major refactoring of authentication system" \
    --files "api/auth.py,api/oauth.py,api/tokens.py,api/sessions.py" \
    --create-linear \
    --max-agents 15
```

**Output:**
- Full review results
- 8 Linear issues created with agent assignments

---

## Performance & Scalability

### Metrics
- **Agent Selection Time:** < 1 second
- **Execution Plan Generation:** < 0.5 seconds
- **Review Workflow (5 agents):** ~2-4 hours estimated
- **Review Workflow (10 agents):** ~6-9 hours estimated
- **Linear Issue Creation:** < 2 seconds per issue (with rate limiting)

### Optimization Strategies
1. **Parallel Execution:** Phases 1 & 2 run agents in parallel
2. **Rate Limiting:** Respects Linear API limits (100 calls/min)
3. **Circuit Breaker:** Fails fast to prevent cascading failures
4. **Caching:** Agent registry cached in memory
5. **Lazy Loading:** MCP tools loaded only when needed

---

## Testing

### Test Coverage: 85%+

**test_task_analyzer.py** (400 lines)
- Language/framework/domain detection: 18 tests
- Review dimension scoring: 8 tests
- Complexity estimation: 6 tests
- Linear metadata extraction: 4 tests

**test_agent_selector.py** (350 lines)
- Agent ranking algorithm: 12 tests
- Coordination pattern selection: 8 tests
- Team composition: 10 tests
- Edge cases: 6 tests

**test_execution_coordinator.py** (300 lines)
- Execution plan generation: 8 tests
- Result aggregation: 10 tests
- Severity sorting: 4 tests
- Error handling: 6 tests

**test_linear_integrator.py** (250 lines)
- Issue description generation: 6 tests
- Dual-assignment model: 8 tests
- Label determination: 6 tests
- Batch operations: 4 tests

**test_universal_orchestrator.py** (200 lines)
- End-to-end workflows: 8 tests
- CLI integration: 4 tests
- Component integration: 6 tests
- Error handling: 4 tests

### Running Tests
```bash
cd plugins/fda-tools
python3 -m pytest tests/test_task_analyzer.py -v
python3 -m pytest tests/test_agent_selector.py -v
python3 -m pytest tests/test_execution_coordinator.py -v
python3 -m pytest tests/test_linear_integrator.py -v
python3 -m pytest tests/test_universal_orchestrator.py -v
```

---

## Future Enhancements

### Phase 8: Machine Learning Integration (8 hours)
- Train ML model on historical task→agent assignments
- Predict optimal agent teams based on past successes
- Confidence scoring for agent selections

### Phase 9: Continuous Monitoring (6 hours)
- Monitor Linear issues for new comments/updates
- Re-trigger review if substantial changes detected
- Auto-assign new agents based on evolving requirements

### Phase 10: Agent Performance Tracking (8 hours)
- Track agent effectiveness (finding quality, resolution time)
- Rank agents by historical performance
- Auto-remove low-performing agents from rotation

### Phase 11: Multi-Repo Support (10 hours)
- Extend beyond FDA tools plugin
- Support orchestration across multiple repositories
- Cross-repo dependency analysis

---

## Troubleshooting

### Issue: "Linear MCP tools not loaded"

**Solution:**
```python
# Tools must be loaded via ToolSearch first
from ToolSearch import ToolSearch
ToolSearch(query="+linear create issue", max_results=5)
```

### Issue: "Circuit breaker OPEN"

**Cause:** Too many Linear API failures (≥5)

**Solution:**
1. Wait 60 seconds for auto-recovery
2. Check Linear API status
3. Verify API credentials
4. Check rate limits

### Issue: "Rate limit exceeded"

**Cause:** More than 100 calls/minute to Linear API

**Solution:**
- Rate limiter automatically throttles
- Wait for sliding window to clear
- Consider batching operations

### Issue: "No agents selected"

**Cause:** Task profile too minimal or no matching agents

**Solution:**
1. Add more context to task description
2. Specify files with language extensions
3. Include keywords (security, testing, etc.)
4. Lower max_agents limit may help

---

## Architecture Decisions

### Why Multi-Dimensional Selection?

**Problem:** Single-dimension agent selection misses issues
**Solution:** 8 review dimensions ensure comprehensive coverage

**Rationale:** Security expert may miss testing gaps; tester may miss security issues. Multi-dimensional ensures all angles covered.

### Why 3 Coordination Patterns?

**Problem:** One-size-fits-all coordination doesn't scale
**Solution:** Pattern adapts to team size

**Rationale:**
- Small teams (≤3): Overhead of coordinator unnecessary
- Medium teams (4-6): Coordinator helps but not critical
- Large teams (≥7): Coordinator essential to prevent chaos

### Why Dual-Assignment Model?

**Problem:** Implementation ≠ Review expertise
**Solution:** Separate implementer and reviewers

**Rationale:**
- Assignee focuses on execution
- Delegate ensures regulatory compliance
- Reviewers validate quality/security/testing

### Why 4-Phase Execution?

**Problem:** Parallel chaos vs sequential slowness
**Solution:** Balanced approach with dependencies

**Rationale:**
- Phases 1-2: Parallel for speed
- Phases 3-4: Sequential for quality
- Dependencies ensure proper ordering

---

## Security Considerations

1. **API Keys:** Never hardcode; use environment variables
2. **Rate Limiting:** Prevents abuse and DOS
3. **Circuit Breaker:** Prevents cascading failures
4. **Input Validation:** All user inputs sanitized
5. **Error Logging:** Sensitive data redacted from logs

---

## Contributing

### Adding New Agents

Edit `agent_registry.py`:
```python
UNIVERSAL_AGENT_CATALOG = {
    "your-new-agent": {
        "category": "category-name",
        "model": "opus",  # or "sonnet", "haiku"
        "review_dimensions": ["code_quality", "security"],
        "languages": ["python", "typescript"],
        "description": "Agent description",
    },
}
```

### Adding New Review Dimensions

Edit `task_analyzer.py`:
```python
DIMENSION_KEYWORDS = {
    "your_dimension": ["keyword1", "keyword2", ...],
}
```

---

## References

- [Universal Orchestrator Plan](plan.md)
- [Linear MCP Documentation](https://linear.app/docs)
- [FDA Tools Plugin](../README.md)
- [Agent Catalog](agent_registry.py)

---

**Last Updated:** 2026-02-18
**Version:** 1.0.0
**Authors:** Claude Sonnet 4.5 + Andrew Lasiter
