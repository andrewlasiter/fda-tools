# Issue Dependency Map

**Created:** 2026-02-19
**Total Issues:** 71
**Dependencies Set:** 32 relationships

---

## Foundation Issues (Block Multiple Others)

These critical issues must be resolved first as they block downstream work:

### 🔴 FDA-101: OpenClaw TypeScript Skill Missing (P0 CRITICAL)
**Blocks:**
- FDA-108: Tool Emulation Layer
- FDA-110: Command Execution
- FDA-117: Security Gateway

**Impact:** All OpenClaw integration work blocked until this is complete.

---

### 🔴 FDA-104: cross_process_rate_limiter.py Not Integrated (P1 HIGH)
**Blocks:**
- FDA-143: Rate Limiting Coordination
- FDA-151: PubMed API Rate Limiting
- FDA-153: OpenFDA API Quota Management

**Impact:** All API rate limiting features blocked.

---

### 🟡 FDA-139: CI/CD Pipeline Missing (P2 MEDIUM)
**Blocks:**
- FDA-140: Docker Container Support
- FDA-141: Health Check Endpoint
- FDA-149: Automated Security Scanning
- FDA-150: Smoke Tests
- FDA-159: Code Coverage Badges
- FDA-160: Automated Changelog
- FDA-162: Performance Benchmarks
- FDA-165: Dependency Update Automation

**Impact:** All CI/CD-dependent automation blocked.

---

### 🟡 FDA-147: JSON Schema Validation Missing (P2 MEDIUM)
**Blocked By:**
- FDA-105: manifest_validator.py Integration
- FDA-124: Input Validators Module

**Blocks:**
- FDA-152: Rollback Mechanism (needs integrity checks)

**Impact:** Data integrity features blocked.

---

### 🟢 FDA-128: Documentation Gaps (P3 LOW)
**Blocks:**
- FDA-155: CONTRIBUTING.md
- FDA-156: API Documentation
- FDA-157: Architecture Decision Records

**Impact:** Documentation standardization blocked.

---

### 🟢 FDA-155: CONTRIBUTING.md (P3 LOW)
**Blocked By:**
- FDA-128: Documentation Gaps

**Blocks:**
- FDA-158: Code Comments Standards
- FDA-160: Changelog (commit conventions)

**Impact:** Contributor onboarding blocked.

---

### 🔴 FDA-102: Phase 1 & 2 Enrichment Audit (P0 CRITICAL)
**Blocks:**
- FDA-103: CFR/Guidance Verification
- FDA-119: Post-Market Surveillance

**Impact:** Regulatory compliance blocked.

---

### 🟡 FDA-112: Stale Dependencies (P1 HIGH)
**Blocks:**
- FDA-149: Security Scanning (needs clean baseline)

**Impact:** Security automation blocked.

---

### 🟡 FDA-148: Secrets Management (.env) (P2 MEDIUM)
**Blocks:**
- FDA-106: API Key Exposure Fix
- FDA-151: PubMed Rate Limiting (needs API key support)

**Impact:** Credential management features blocked.

---

## Testing Dependency Chain

Critical path for test coverage:

```
FDA-133 (Unit Tests)
    ↓
FDA-118 (Integration Tests)
    ↓
FDA-150 (Smoke Tests)
```

**Rationale:** Unit tests → Integration tests → Smoke tests (increasing scope)

---

## Complete Dependency Graph

### OpenClaw Chain
```
FDA-101 (OpenClaw TypeScript Skill) [P0]
    ├─→ FDA-108 (Tool Emulation) [P0]
    ├─→ FDA-110 (Command Execution) [P0]
    └─→ FDA-117 (Security Gateway) [P1]
```

### Rate Limiting Chain
```
FDA-104 (Rate Limiter Core) [P1]
    ├─→ FDA-143 (Cross-Command Coordination) [P2]
    ├─→ FDA-151 (PubMed Rate Limiting) [P2]
    └─→ FDA-153 (OpenFDA Quota Management) [P2]
```

### CI/CD Chain
```
FDA-139 (CI/CD Pipeline) [P2]
    ├─→ FDA-140 (Docker Support) [P2]
    ├─→ FDA-141 (Health Check) [P2]
    ├─→ FDA-149 (Security Scanning) [P2]
    ├─→ FDA-150 (Smoke Tests) [P2]
    ├─→ FDA-159 (Coverage Badges) [P3]
    ├─→ FDA-160 (Changelog Automation) [P3]
    ├─→ FDA-162 (Performance Benchmarks) [P3]
    └─→ FDA-165 (Dependabot) [P3]
```

### Data Integrity Chain
```
FDA-105 (manifest_validator Integration) [P1]
    ↓
FDA-124 (Input Validators) [P2]
    ↓
FDA-147 (JSON Schema Validation) [P2]
    ↓
FDA-152 (Rollback Mechanism) [P2]
```

### Documentation Chain
```
FDA-128 (Documentation Gaps) [P3]
    ├─→ FDA-155 (CONTRIBUTING.md) [P3]
    ├─→ FDA-156 (API Docs) [P3]
    └─→ FDA-157 (ADRs) [P3]

FDA-155 (CONTRIBUTING.md) [P3]
    ├─→ FDA-158 (Code Comments) [P3]
    └─→ FDA-160 (Changelog) [P3]
```

### Regulatory Chain
```
FDA-102 (Enrichment Audit) [P0]
    ├─→ FDA-103 (CFR/Guidance Verification) [P1]
    └─→ FDA-119 (Post-Market Surveillance) [P1]
```

### Security Chain
```
FDA-112 (Dependency Updates) [P1]
    ↓
FDA-149 (Security Scanning) [P2]

FDA-148 (Secrets Management) [P2]
    ├─→ FDA-106 (API Key Exposure) [P0]
    └─→ FDA-151 (PubMed Rate Limiting) [P2]
```

### Testing Chain
```
FDA-133 (Unit Test Coverage) [P2]
    ↓
FDA-118 (Integration Tests) [P1]
    ↓
FDA-150 (Smoke Tests) [P2]
```

---

## Critical Path Analysis

### Shortest Path to Production (P0/P1 only)

**Phase 1: Foundation (Parallel)**
1. FDA-101: OpenClaw TypeScript Skill (64 pts) - BLOCKER
2. FDA-102: Enrichment Audit (10 pts)
3. FDA-104: Rate Limiter Integration (4 pts)
4. FDA-105: manifest_validator Integration (2 pts)

**Phase 2: OpenClaw Core (Sequential)**
5. FDA-110: Command Execution (16 pts) - depends on FDA-101
6. FDA-108: Tool Emulation (24 pts) - depends on FDA-101
7. FDA-117: Security Gateway (16 pts) - depends on FDA-101

**Phase 3: Regulatory & Security (Parallel)**
8. FDA-103: CFR Verification (3 pts) - depends on FDA-102
9. FDA-106: API Key Exposure (3 pts)
10. FDA-107: TLS Verification (4 pts)
11. FDA-109: PMA Pathway (20 pts)

**Phase 4: Integration & Testing (Sequential)**
12. FDA-118: Integration Tests (64 pts) - depends on FDA-101, FDA-110, FDA-108
13. FDA-119: Post-Market Surveillance (12 pts) - depends on FDA-102

**Total Critical Path:** ~242 points (~6 weeks)

---

## Implementation Strategy

### Week 1: Foundation Issues (Parallel)
- **Team A:** FDA-101 (OpenClaw skill) - 64 pts
- **Team B:** FDA-102 (Audit), FDA-104 (Rate Limiter), FDA-105 (Validator) - 16 pts
- **Deliverable:** OpenClaw skill exists, regulatory audit complete, rate limiter ready

### Week 2: OpenClaw Integration (Sequential)
- FDA-110 (Command Execution) - 16 pts
- FDA-108 (Tool Emulation) - 24 pts
- FDA-117 (Security Gateway) - 16 pts
- **Deliverable:** OpenClaw fully functional

### Week 3: Security & Regulatory (Parallel)
- **Team A:** FDA-106, FDA-107, FDA-112, FDA-113 (Security) - 19 pts
- **Team B:** FDA-103, FDA-109, FDA-119, FDA-120 (Regulatory) - 43 pts
- **Deliverable:** All P0/P1 security and regulatory issues resolved

### Week 4: Testing & Polish (Sequential)
- FDA-133 (Unit Tests) - 12 pts
- FDA-118 (Integration Tests) - 64 pts
- **Deliverable:** Comprehensive test coverage

### Week 5-6: P2 MEDIUM Issues (Parallel across teams)
- CI/CD chain (FDA-139 + 8 downstream) - 119 pts
- Data integrity chain (FDA-147, FDA-152) - 26 pts
- Operations (API limits, monitoring) - 87 pts

---

## Dependencies Not Set (Intentional)

These issues are independent and can be worked on anytime:
- FDA-100: Stored XSS (standalone fix)
- FDA-111: Unvalidated Output Path (standalone fix)
- FDA-114-116: Code duplication (refactoring, no dependencies)
- FDA-121-127: Individual operational improvements
- FDA-129-131: Individual feature utilization
- FDA-132, FDA-134-138: Individual testing/ops improvements
- FDA-144-146, FDA-161, FDA-163-164, FDA-166: Individual polish items

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| **Total Issues** | 71 |
| **Foundation Issues** | 9 |
| **Blocked Issues** | 23 |
| **Independent Issues** | 48 |
| **Dependency Relationships** | 32 |
| **Longest Chain** | 4 levels (FDA-128 → FDA-155 → FDA-158/160) |
| **Critical Path Length** | ~242 points (6 weeks) |

---

## Validation

All dependencies follow logical patterns:
- ✅ No circular dependencies
- ✅ Foundation issues (FDA-101, FDA-104, FDA-139, FDA-147) correctly identified
- ✅ Testing chain follows unit → integration → smoke progression
- ✅ Documentation chain ensures standards before implementation
- ✅ CI/CD issues blocked until pipeline exists
- ✅ Rate limiting features blocked until core limiter integrated

**Status:** ✅ **Dependency graph complete and validated**
