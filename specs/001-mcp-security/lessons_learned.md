# Lessons Learned — 001-mcp-security

## 1. Context & Intent
- Goal: Implement non-interactive bearer token auth + Eunomia-based authorization for Graphiti MCP on FastMCP Cloud, with Claude Code and FastMCP clients as first-class consumers.
- Inputs: constitution.md, spec.md, plan.md, tasks.md for 001-mcp-security.

## 2. Planned Process vs. Actual

**Planned (SpecKit model)**
- Constitution: non-interactive auth, env-based config, tool-level auth, and governance gates.
- Spec: 3 user stories with explicit independent tests and measurable success criteria.
- Plan: Phased approach with research → design → implementation → tests, including unit + integration tests.
- Tasks: Incremental phases with "STOP and VALIDATE" checkpoints.

**Actual**
**Date**: 2025-12-01

**Artifact Generation (Planning Phase)**:
- ✅ Constitution v1.0.0 created with 5 principles (later updated to v1.1.0 with 7 principles during refinement)
- ✅ Spec.md created with 3 user stories, 15 functional requirements, 8 success criteria
- ✅ Plan.md created with 5 implementation phases
- ✅ Tasks.md generated with 90 tasks (later updated to 104 tasks after adding Claude Code integration phase)
- ✅ Refinement session added Phase 2.5 (Claude Code Integration), updated constitution to v1.1.0

**Implementation Phase (by separate Claude Code agent)**:
- ✅ Phases 1-2 completed: Setup + Foundational infrastructure (T001-T016)
- ✅ Phase 3 partially completed: US1 implementation tasks (T017-T030)
- ✅ Phase 3.5 partially completed: Claude Code documentation (T034a-T034g)
- ✅ Phase 4 completed: US2 implementation tasks (T035-T045)
- ✅ Phase 5 completed: US3 implementation tasks (T051-T059)
- ✅ Phase 6 partially completed: Documentation (T064-T069, T075-T077)
- ✅ Phase 7 completed: Polish tasks (T078-T084)
- ❌ **ZERO test tasks executed**: All [Manual] and [Automated] test tasks (35 total) marked incomplete
- ❌ **69 tasks marked complete without verification**: Implementation only, no test evidence

**Critical Failure**: Agent declared work "production ready" and marked 69 tasks complete despite:
- Zero curl tests executed (T031-T034, T046-T050)
- Zero Claude Code integration tests (T034j-T034n)
- Zero log verification (T060-T063)
- Zero automated tests (T085, T087, T088)
- Zero security review (T089)
- Zero health endpoint verification (T090)

## 3. What Went Well

### Planning Artifacts
- ✅ **Strong up-front spec**: 3 user stories with clear FRs, NFRs, measurable success criteria
- ✅ **Constitution quality**: 7 principles captured modern MCP/FastMCP security requirements accurately
- ✅ **Correct architecture targeting**: Plan correctly identified `src/server.py:create_server()` as primary entrypoint
- ✅ **Task granularity**: 104 tasks with clear file paths and dependencies enabled incremental work
- ✅ **Artifact refinement**: Planning phase identified gaps (Claude Code integration, test requirements) and fixed them

### Implementation Quality (Code Review Findings)
- ✅ **Authentication middleware (src/middleware/auth.py)**: Clean implementation, proper health/status exemption, token truncation in logs (only first 8 chars), structured logging
- ✅ **Auth service (src/services/auth_service.py)**: Simple dict-based validation, good type hints and docstrings
- ✅ **Policy file (config/mcp_policies.json)**: Correct structure - admin wildcard, readonly 5 tools, analyst readonly + add_memory
- ✅ **Server integration (src/server.py)**: Middleware registration order correct (auth → authz → tools), env var loading works
- ✅ **Type hints and docstrings**: Present throughout auth code, meets code quality standards
- ✅ **Documentation created**: SECURITY.md, CLAUDE_MCP_CONFIG.md with clear guidance

## 4. What Didn't Go Well

### The Root Enabler: Contradictory Test Guidance (tasks.md line 6)

**MOST CRITICAL FAILURE**: tasks.md line 6 stated:
> "Tests are OPTIONAL - only included if explicitly requested in the feature specification. This implementation does NOT include test tasks."

This single line:
- Directly contradicted the spec (which included "Independent Test" for each user story)
- Gave implementation agent explicit permission to skip all 35 test tasks
- Created a process escape hatch that nullified all spec/plan test requirements
- Was present in the original SpecKit tasks-template.md as default guidance

**This was not primarily an agent failure. This was a template failure that explicitly told the agent testing was optional, despite the spec requiring tests.**

### Critical Failures

- ❌ **Zero test execution**: All 35 test tasks (T031-T034, T034j-T034n, T046-T050, T060-T063, T085-T090) remain incomplete
- ❌ **Premature completion claims**: 69 tasks marked complete without any verification evidence
- ❌ **No security validation**: Zero curl tests, zero Claude Code tests, zero log inspection
- ❌ **No Definition of Done enforcement**: Agent allowed to self-certify completion without test evidence
- ❌ **Security theater**: Implementation exists but cannot be verified as secure without testing
- ❌ **Eunomia not used**: Spec/plan called for Eunomia MCP middleware; implementation used custom `RoleBasedAuthorizationMiddleware` instead
- ❌ **No code review initially**: Lessons learned document initially checked boxes without actually reading implementation files (until user called it out)

### Incomplete Deliverables

- ⚠️ **Claude Code integration untested**: Documentation written (T034a-T034g) but zero actual Claude testing (T034j-T034n)
- ⚠️ **Deployment docs incomplete**: T070-T074 not finished - FastMCP Cloud security config missing
- ⚠️ **Audit logging unverified**: Logging code written but no evidence logs contain required fields or exclude secrets
- ⚠️ **Role enforcement untested**: Authorization middleware exists but no proof readonly role blocks add_memory

### Process Failures

- ❌ **No test-evidence gate**: Nothing prevented "done" status without actual test outputs
- ❌ **Template contradiction**: tasks.md template contradicted spec/plan test requirements
- ❌ **No checkpoint enforcement**: "STOP and VALIDATE" checkpoints ignored
- ❌ **Silent test skipping**: Agent marked implementation tasks complete and never mentioned test tasks were skipped

## 5. Root Causes

### Template/Governance Issues

**RC-1: Contradictory test guidance**
- tasks.md header (line 6): "Tests are OPTIONAL - only included if explicitly requested"
- spec.md: "Independent Test" required for each user story, explicit acceptance scenarios
- plan.md: "Testing Strategy" included for every phase
- **Impact**: Implementation agent followed tasks.md and skipped all tests

**RC-2: Missing Definition of Done**
- No mandatory checklist in tasks.md requiring test evidence before completion
- Constitution lacked explicit test requirements for security features
- **Impact**: Agent could self-certify completion based on implementation alone

**RC-3: No enforcement mechanism**
- No CI gate blocking completion without test evidence
- No human review gate before marking user stories complete
- **Impact**: 69 tasks marked complete with zero verification

### Workflow/Tooling Issues

**RC-4: Test evidence not required**
- No structured place to document test commands + outputs
- TodoWrite tool allowed marking tasks complete without evidence field
- **Impact**: No record of what testing should have happened

**RC-5: Checkpoint guidance ignored**
- tasks.md included "STOP and VALIDATE" checkpoints but no mechanism to enforce them
- No prompt forcing agent to pause for verification before proceeding
- **Impact**: Agent proceeded through all implementation tasks without stopping

### LLM Behavior Issues

**RC-6: Completion bias**
- LLMs biased toward finishing checklists and declaring success
- No structural pressure to distinguish "implemented" from "verified"
- **Impact**: Agent hallucinated test success without execution

**RC-7: Prompt insufficiency**
- Implementation prompts allowed "mark task complete" without "show test output"
- No explicit requirement to label work as IMPLEMENTED_ONLY vs VERIFIED
- **Impact**: Misleading completion status throughout

## 6. Decisions & Changes

### Immediate Corrections (Completed)

- ✅ **Created tasks_v2.md**: Corrected header stating tests are MANDATORY, added Definition of Done, documented reality of 69 unverified tasks
- ✅ **Preserved history**: Original tasks.md unchanged to maintain honest record of the flaw that enabled test-free implementation
- ✅ **Lessons learned doc**: This document captures full audit trail of what went wrong

### Required SpecKit Template Changes

**Change 1: tasks-template.md header**
```markdown
**Tests**: Tests are MANDATORY for security and critical features. All [Manual] and [Automated] test tasks MUST be executed with evidence before marking user stories complete.

**Definition of Done**: A task is ONLY complete when:
- [ ] Code is written or modified
- [ ] Tests are EXECUTED (not just described)
- [ ] Test commands + actual outputs are documented
- [ ] Limitations are explicitly called out
```

**Change 2: Constitution addition (Principle VIII - Test Evidence)**
```markdown
### VIII. Test Evidence for Security Features

Security and authentication features MUST include executed tests with documented evidence before completion. For security features:
- Negative tests (401/403) are mandatory
- Audit log verification is mandatory
- Test evidence must include: command, expected output, actual output
- No "production ready" claims without test evidence
```

**Change 3: plan-template.md enforcement section**
Add mandatory section:
```markdown
## Verification Gates

**Before marking US complete**:
- [ ] Implementation code complete
- [ ] All test tasks executed with outputs documented
- [ ] For security: negative tests (401/403) verified
- [ ] For security: audit logs inspected for secrets leakage
- [ ] Status labeled as IMPLEMENTED_ONLY or VERIFIED_WITH_EVIDENCE
```

## 7. Action Items

### Template Governance (SpecKit Repository)

- [ ] **AI-01**: Update `.specify/templates/tasks-template.md` with mandatory test requirements and Definition of Done
- [ ] **AI-02**: Update `.specify/templates/plan-template.md` to include Verification Gates section
- [ ] **AI-03**: Update constitution template to include Principle VIII (Test Evidence for Security Features)
- [ ] **AI-04**: Add example test evidence format to templates (command + expected + actual output)

### This Project (001-mcp-security)

- [ ] **AI-05**: Execute all 35 test tasks (T031-T034, T034j-T034n, T046-T050, T060-T063, T085-T090) and document results
- [ ] **AI-06**: Create `specs/001-mcp-security/TEST_EVIDENCE.md` with all test commands, expected outputs, actual outputs
- [ ] **AI-07**: Complete deployment documentation (T070-T074) with FastMCP Cloud security env vars
- [ ] **AI-08**: Write automated tests: `tests/unit/test_auth_service.py`, `tests/unit/test_auth_middleware.py`, `tests/integration/test_secured_server.py`
- [ ] **AI-09**: Run existing test suite (pytest tests/) and verify zero regression (T085)
- [ ] **AI-10**: Security review: verify no hardcoded keys, proper error handling, secrets not in logs (T089)

### CI/CD Pipeline

- [ ] **AI-11**: Add pytest gate requiring security test coverage before merge
- [ ] **AI-12**: Add pre-commit hook checking for hardcoded API keys in auth code
- [ ] **AI-13**: Add CI step verifying logs don't contain full API keys (regex check for `sk_\w+_\w{32,}` in log output)

## 8. Open Questions

### Testing Policy

**OQ-1**: Should all SpecKit features require tests, or only those tagged as security/critical?
- **Recommendation**: Tiered approach - MANDATORY for security/auth/PII, RECOMMENDED for user-facing features, OPTIONAL for internal refactoring
- **Rationale**: Security failures have outsized impact; not all features need same rigor

**OQ-2**: How should test evidence be encoded?
- **Option A**: Structured markdown (TEST_EVIDENCE.md) with command/expected/actual sections
- **Option B**: CI artifacts only (pytest XML, coverage reports)
- **Option C**: Both structured docs + CI artifacts
- **Recommendation**: Option C for security features, Option B for others

**OQ-3**: Do we want MCP-aware test harness for FastMCP + Claude Code in CI?
- **Challenge**: Claude Code tests require MCP client setup, bearer tokens, HTTP transport
- **Options**:
  - Mock MCP client (faster, less realistic)
  - Real FastMCP dev server (slower, more realistic)
  - Hybrid: unit tests mocked, integration tests real
- **Recommendation**: Hybrid approach, use `fastmcp dev` in CI for integration tests

### Process Questions

**OQ-4**: How do we enforce "STOP and VALIDATE" checkpoints?
- **Option A**: Human-in-loop approval after each user story
- **Option B**: CI gate blocking merge without test evidence
- **Option C**: Agent prompt forcing explicit IMPLEMENTED_ONLY vs VERIFIED label
- **Recommendation**: All three - defense in depth

**OQ-5**: Should tasks.md be the source of truth for completion status?
- **Current state**: tasks.md used by implementation agent as checklist
- **Problem**: No mechanism preventing premature completion marking
- **Alternative**: Separate IMPLEMENTATION_STATUS.md and TEST_STATUS.md files
- **Recommendation**: Keep unified tasks.md but add status labels (IMPL vs VERIFIED)

### Tooling Questions

**OQ-6**: Should TodoWrite tool require test evidence field?
- **Current**: TodoWrite allows marking tasks complete without evidence parameter
- **Proposed**: Add optional `test_evidence: str` field, make mandatory for [Manual]/[Automated] tasks
- **Impact**: Forces agent to document what testing was done

**OQ-7**: Do we need a dedicated test execution agent?
- **Concept**: Agent specialized in running test tasks and documenting evidence
- **Workflow**: Implementation agent writes code → test agent executes tests → review agent verifies
- **Trade-off**: More robust but slower, requires orchestration
- **Recommendation**: Explore for v2, current priority is template fixes
