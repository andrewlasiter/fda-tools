# Linear Agent Assignment Guide for FDA Tools

## Available Regulatory Agents

### FDA-Specific Agents (from fda-tools skills)

1. **fda-predicate-assessment**
   - **Purpose:** Assess 510(k) predicate strategy, substantial equivalence, predicate validity
   - **Best for:** GAP-009, GAP-019, GAP-025 (predicate-related issues)
   - **Delegate as:** `fda-predicate-assessment`

2. **fda-510k-knowledge**
   - **Purpose:** Local FDA 510(k) data pipeline, plugin scripts, configured data paths
   - **Best for:** GAP-003, GAP-004, GAP-005 (codebase structure issues)
   - **Delegate as:** `fda-510k-knowledge`

3. **fda-safety-signal-triage**
   - **Purpose:** Triage FDA safety signals - recalls, MAUDE adverse events, complaints
   - **Best for:** GAP-011, GAP-036 (safety/MAUDE-related issues)
   - **Delegate as:** `fda-safety-signal-triage`

4. **fda-510k-submission-outline**
   - **Purpose:** Build 510(k) submission outlines, RTA readiness, evidence plans
   - **Best for:** GAP-019, GAP-033, GAP-034 (compliance/submission issues)
   - **Delegate as:** `fda-510k-submission-outline`

### Business/Compliance Agents (from voltagent-biz)

5. **compliance-auditor** (voltagent-qa-sec)
   - **Purpose:** Regulatory compliance, audit frameworks, risk assessments
   - **Best for:** GAP-034 (compliance disclaimer), GAP-006 (CI/CD compliance)
   - **Delegate as:** `voltagent-qa-sec:compliance-auditor`

6. **legal-advisor** (voltagent-biz)
   - **Purpose:** Draft contracts, review compliance, assess legal risks
   - **Best for:** GAP-027 (user-agent spoofing), GAP-010 (input validation security)
   - **Delegate as:** `voltagent-biz:legal-advisor`

7. **technical-writer** (voltagent-biz)
   - **Purpose:** Create/improve documentation, API references, user guides
   - **Best for:** GAP-013, GAP-022, GAP-040 (documentation issues)
   - **Delegate as:** `voltagent-biz:technical-writer`

8. **business-analyst** (voltagent-biz)
   - **Purpose:** Analyze business processes, gather requirements, identify improvements
   - **Best for:** TICKET-005 through TICKET-013 (feature requirements)
   - **Delegate as:** `voltagent-biz:business-analyst`

### QA/Testing Agents (from voltagent-qa-sec)

9. **qa-expert**
   - **Purpose:** Quality assurance strategy, test planning, quality metrics
   - **Best for:** GAP-004, GAP-005, GAP-025 (testing issues)
   - **Delegate as:** `voltagent-qa-sec:qa-expert`

10. **test-automator**
    - **Purpose:** Build automated test frameworks, create test scripts
    - **Best for:** GAP-016, GAP-024, GAP-035 (test automation)
    - **Delegate as:** `voltagent-qa-sec:test-automator`

11. **code-reviewer**
    - **Purpose:** Code reviews for quality, security, best practices
    - **Best for:** GAP-001, GAP-002, GAP-023 (code quality issues)
    - **Delegate as:** `voltagent-qa-sec:code-reviewer`

12. **security-auditor**
    - **Purpose:** Security audits, compliance assessments, vulnerability analysis
    - **Best for:** GAP-010, GAP-011, GAP-027 (security issues)
    - **Delegate as:** `voltagent-qa-sec:security-auditor`

### Development Agents (from voltagent-lang and voltagent-dev-exp)

13. **python-pro** (voltagent-lang)
    - **Purpose:** Type-safe, production-ready Python code
    - **Best for:** GAP-001, GAP-002, GAP-037 (Python code issues)
    - **Delegate as:** `voltagent-lang:python-pro`

14. **refactoring-specialist** (voltagent-dev-exp)
    - **Purpose:** Transform complex code into clean, maintainable systems
    - **Best for:** GAP-015, GAP-017, GAP-038 (code refactoring)
    - **Delegate as:** `voltagent-dev-exp:refactoring-specialist`

---

## Assignment Strategy by Issue Type

### URGENT Priority Issues

| Issue | Agent | Rationale |
|-------|-------|-----------|
| FDA-34 (GAP-034) | `voltagent-qa-sec:compliance-auditor` | Compliance disclaimer requirements |
| FDA-33 (GAP-006) | `voltagent-infra:devops-engineer` | CI/CD pipeline expertise |
| FDA-32 (GAP-012) | `voltagent-lang:python-pro` | Atomic file operations |

### HIGH Priority Issues - Testing

| Issue | Agent | Rationale |
|-------|-------|-----------|
| FDA-29 (GAP-004) | `voltagent-qa-sec:test-automator` | Create test suites for lib/ modules |
| FDA-28 (GAP-005) | `voltagent-qa-sec:test-automator` | Create test suites for scripts |
| FDA-22 (GAP-025) | `voltagent-qa-sec:qa-expert` | TESTING_SPEC implementation |

### HIGH Priority Issues - Code Quality

| Issue | Agent | Rationale |
|-------|-------|-----------|
| FDA-31 (GAP-001) | `voltagent-qa-sec:code-reviewer` | Bare except clause patterns |
| FDA-30 (GAP-002) | `voltagent-qa-sec:code-reviewer` | Silent exception handling |
| FDA-25 (GAP-010) | `voltagent-qa-sec:security-auditor` | Input validation security |

### HIGH Priority Issues - Architecture

| Issue | Agent | Rationale |
|-------|-------|-----------|
| FDA-27 (GAP-007) | `voltagent-infra:devops-engineer` | Dependency management |
| FDA-26 (GAP-008) | `voltagent-lang:typescript-pro` | OpenClaw TypeScript build |
| FDA-23 (GAP-019) | `fda-510k-submission-outline` | eSTAR XML validation for FDA |

### MEDIUM Priority Issues - Documentation

| Issue | Agent | Rationale |
|-------|-------|-----------|
| FDA-22 (GAP-022) | `voltagent-biz:technical-writer` | Error recovery documentation |
| FDA-13 (GAP-040) | `voltagent-biz:technical-writer` | Settings schema documentation |

### MEDIUM Priority Issues - Security

| Issue | Agent | Rationale |
|-------|-------|-----------|
| FDA-71 (GAP-011) | `voltagent-qa-sec:security-auditor` | Cache integrity verification |
| FDA-59 (GAP-027) | `voltagent-biz:legal-advisor` | User-agent compliance review |

### Feature Tickets

| Ticket Range | Agent | Rationale |
|--------------|-------|-----------|
| TICKET-001 to TICKET-004 | `fda-predicate-assessment` | PMA-related features |
| TICKET-005 | `voltagent-biz:business-analyst` | IDE pathway requirements |
| FE-001, FE-002 | `voltagent-qa-sec:test-automator` | Test suite creation |

---

## How to Assign Agents in Linear

### Via Linear UI
1. Open the issue in Linear
2. Find the "Delegate" field in the issue details
3. Enter the agent name (e.g., `voltagent-qa-sec:test-automator`)

### Via API (for bulk assignment)
```typescript
await linear.updateIssue("FDA-34", {
  delegate: "voltagent-qa-sec:compliance-auditor"
});
```

### Via MCP Tool
```json
{
  "issueId": "FDA-34",
  "delegate": "voltagent-qa-sec:compliance-auditor"
}
```

---

## Agent Assignment Matrix

### By Skill Area

| Skill Area | Primary Agent | Backup Agent |
|------------|---------------|--------------|
| **510(k) Submissions** | `fda-510k-submission-outline` | `fda-predicate-assessment` |
| **Safety Signals** | `fda-safety-signal-triage` | `voltagent-qa-sec:security-auditor` |
| **Code Quality** | `voltagent-qa-sec:code-reviewer` | `voltagent-lang:python-pro` |
| **Testing** | `voltagent-qa-sec:test-automator` | `voltagent-qa-sec:qa-expert` |
| **Security** | `voltagent-qa-sec:security-auditor` | `voltagent-biz:legal-advisor` |
| **Documentation** | `voltagent-biz:technical-writer` | `fda-510k-knowledge` |
| **Compliance** | `voltagent-qa-sec:compliance-auditor` | `fda-510k-submission-outline` |
| **CI/CD** | `voltagent-infra:devops-engineer` | `voltagent-dev-exp:dx-optimizer` |

### By Task Type

| Task Type | Recommended Agent |
|-----------|-------------------|
| Write tests | `voltagent-qa-sec:test-automator` |
| Review code | `voltagent-qa-sec:code-reviewer` |
| Security audit | `voltagent-qa-sec:security-auditor` |
| Write docs | `voltagent-biz:technical-writer` |
| Refactor code | `voltagent-dev-exp:refactoring-specialist` |
| Fix bugs | `voltagent-lang:python-pro` |
| Design features | `voltagent-biz:business-analyst` |
| Compliance check | `voltagent-qa-sec:compliance-auditor` |
| FDA-specific work | `fda-510k-submission-outline` or `fda-predicate-assessment` |

---

## Recommended Bulk Assignments

Run these to assign agents to high-priority issues:

```bash
# URGENT issues
linear issue update FDA-34 --delegate "voltagent-qa-sec:compliance-auditor"
linear issue update FDA-33 --delegate "voltagent-infra:devops-engineer"
linear issue update FDA-32 --delegate "voltagent-lang:python-pro"

# HIGH priority - Testing
linear issue update FDA-29 --delegate "voltagent-qa-sec:test-automator"
linear issue update FDA-28 --delegate "voltagent-qa-sec:test-automator"
linear issue update FDA-22 --delegate "voltagent-qa-sec:qa-expert"

# HIGH priority - Code Quality
linear issue update FDA-31 --delegate "voltagent-qa-sec:code-reviewer"
linear issue update FDA-30 --delegate "voltagent-qa-sec:code-reviewer"
linear issue update FDA-25 --delegate "voltagent-qa-sec:security-auditor"

# HIGH priority - Architecture
linear issue update FDA-27 --delegate "voltagent-infra:devops-engineer"
linear issue update FDA-26 --delegate "voltagent-lang:typescript-pro"
linear issue update FDA-23 --delegate "fda-510k-submission-outline"
```

---

## Notes

- **Agent availability**: All listed agents are available in the current Claude Code environment
- **Multiple agents**: Some complex issues may benefit from sequential agent assignment (e.g., code-reviewer → refactoring-specialist → test-automator)
- **FDA-specific agents**: Use FDA agents for regulatory/compliance work, voltagent agents for general software engineering
- **Specialization**: FDA agents understand 21 CFR regulations, FDA guidance documents, and regulatory submission requirements
