# Tasks: MCP Server Security (v2 - Corrected Test Requirements)

**Input**: Design documents from `/specs/001-mcp-security/`
**Prerequisites**: plan.md (required), spec.md (required for user stories)

**CORRECTION**: The original tasks.md incorrectly stated "Tests are OPTIONAL". This was wrong and directly contradicted the spec requirements. This v2 corrects that error.

**Tests**: Tests are MANDATORY for this security feature. All [Manual] and [Automated] test tasks MUST be executed with evidence before marking user stories complete. Security implementations require verification of all acceptance scenarios per the spec.

**Definition of Done**: A task is ONLY complete when:
- [ ] Code is written or modified
- [ ] Tests are EXECUTED (not just described)
- [ ] Test commands + actual outputs are documented
- [ ] Limitations are explicitly called out

**Reality Check**: As of the last implementation session, 69 tasks were marked complete but ZERO tests were executed. All [Manual] and [Automated] test tasks (T031-T034, T034j-T034n, T046-T050, T060-T063, T085-T090) remain unverified.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths shown below assume single project structure

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [X] T001 Create src/middleware/ directory for authentication middleware
- [X] T002 Create src/services/auth_service.py file (empty module with docstring)
- [X] T003 [P] Create config/mcp_policies.json file (empty JSON structure with version field)
- [X] T004 [P] Add eunomia-mcp dependency to pyproject.toml dependencies section

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 Create AuthService class in src/services/auth_service.py with __init__ method accepting api_keys dict
- [X] T006 Implement validate_token method in AuthService returning dict or None for principal
- [X] T007 Add typing imports and type hints to AuthService (dict[str, dict] for api_keys)
- [X] T008 Create BearerTokenAuthMiddleware class in src/middleware/auth.py extending BaseHTTPMiddleware
- [X] T009 Implement __init__ method in BearerTokenAuthMiddleware accepting app and auth_service parameters
- [X] T010 Implement async dispatch method in Bearer TokenAuthMiddleware with request and call_next parameters
- [X] T011 Add health/status endpoint exemption logic in dispatch method checking request.url.path
- [X] T012 Add Authorization header extraction logic in dispatch method with Bearer prefix check
- [X] T013 Add token validation logic in dispatch method calling auth_service.validate_token
- [X] T014 Add 401 error response for missing/invalid tokens returning JSONResponse with error message
- [X] T015 Add principal attachment to request.state.api_principal after successful validation
- [X] T016 Add necessary imports to src/middleware/auth.py (BaseHTTPMiddleware, Request, JSONResponse)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Secure Server Access with API Key (Priority: P1) 🎯 MVP

**Goal**: Secure server with bearer token authentication, protect all endpoints except health/status

**Independent Test**: Configure client with valid API key, make tool calls, verify invalid keys rejected, verify health endpoint bypasses auth

### Implementation for User Story 1

- [X] T017 [US1] Import AuthService in src/server.py from src.services.auth_service
- [X] T018 [US1] Import BearerTokenAuthMiddleware in src/server.py from src.middleware.auth
- [X] T019 [US1] Add os import to src/server.py for environment variable access
- [X] T020 [US1] Create api_keys dictionary in create_server() loading GRAPHITI_API_KEY_ADMIN from environment
- [X] T021 [US1] Add GRAPHITI_API_KEY_READONLY to api_keys dictionary in create_server()
- [X] T022 [US1] Add GRAPHITI_API_KEY_ANALYST to api_keys dictionary in create_server()
- [X] T023 [US1] Filter None values from api_keys dictionary using dict comprehension
- [X] T024 [US1] Instantiate AuthService with filtered api_keys dictionary
- [X] T025 [US1] Add GRAPHITI_AUTH_ENABLED environment variable check with default value "true"
- [X] T026 [US1] Register BearerTokenAuthMiddleware with server.add_middleware() inside auth enabled check
- [X] T027 [US1] Pass auth_service to middleware registration as keyword argument
- [X] T028 [US1] Verify middleware registration occurs BEFORE _register_tools() call in create_server()
- [X] T029 [US1] Generate test API key using secrets.token_urlsafe(32) for local development testing
- [X] T030 [US1] Document API key format sk_<env>_<random> in inline code comment
- [ ] T031 [US1] [Manual] Test /health endpoint responds 200 with or without auth header (health always unprotected)
- [ ] T032 [US1] [Manual] Test authentication with curl command using valid API key against MCP endpoint
- [ ] T033 [US1] [Manual] Test authentication with curl command using invalid API key verifying 401 response
- [ ] T034 [US1] [Manual] Test authentication with curl command without auth header verifying 401 response

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently. Server requires bearer tokens for all endpoints except /health and /status.

---

## Phase 3.5: Claude Code Integration

**Goal**: Document and test Claude Code MCP client configuration with bearer token authentication

**Independent Test**: Configure Claude Code with `.claude.json` MCP entry, verify tools work with auth

### Implementation for Claude Code Integration

- [X] T034a [P] Create docs/CLAUDE_MCP_CONFIG.md with Claude Code configuration guide
- [X] T034b [P] Document .claude.json structure for local development (localhost:8000)
- [X] T034c [P] Document .claude.json structure for FastMCP Cloud deployment
- [X] T034d [P] Document bearer token configuration syntax with ${GRAPHITI_API_KEY_ADMIN} env var
- [X] T034e [P] Add troubleshooting section to CLAUDE_MCP_CONFIG.md for auth errors (401/403)
- [X] T034f [P] Document testing tool access from Claude Code (tools/list and tools/call examples)
- [X] T034g [P] Document role switching procedure (changing token env var)
- [ ] T034h [P] Add Claude Code configuration section to docs/SECURITY.md
- [ ] T034i [P] Add Claude Code client setup section to docs/FASTMCP_CLOUD_DEPLOYMENT.md
- [ ] T034j [Manual] Test Claude Code connection with valid admin token, verify tools/list shows all tools
- [ ] T034k [Manual] Test calling add_memory from Claude Code with admin token, verify success
- [ ] T034l [Manual] Test Claude Code with readonly token, verify add_memory blocked with 403
- [ ] T034m [Manual] Test Claude Code with invalid token, verify 401 error with clear message
- [ ] T034n [Manual] Verify no interactive auth prompts appear (no browser popups during connection)

**Checkpoint**: Claude Code integration complete and documented. All user-facing auth flows tested.

---

## Phase 4: User Story 2 - Role-Based Tool Access Control (Priority: P2)

**Goal**: Implement role-based tool access control using Eunomia policies

**Independent Test**: Configure policies for different roles, connect with API keys for each role, verify tool listing filters and unauthorized calls blocked

### Implementation for User Story 2

- [X] T035 [US2] Define admin policy in config/mcp_policies.json with role "admin" and resources ["*"]
- [X] T036 [US2] Define readonly policy in config/mcp_policies.json with role "readonly" and specific tool list
- [X] T037 [US2] Add readonly tools to policy: search_nodes, search_memory_facts, get_episodes, get_entity_edge, get_status
- [X] T038 [US2] Define analyst policy in config/mcp_policies.json with role "analyst" including readonly tools plus add_memory
- [X] T039 [US2] Set version field to "1.0" in config/mcp_policies.json root object
- [X] T040 [US2] Validate JSON syntax in config/mcp_policies.json using json.tool or IDE validator
- [X] T041 [US2] Import RoleBasedAuthorizationMiddleware in src/server.py (custom implementation)
- [X] T042 [US2] Add EUNOMIA_POLICY_FILE environment variable check with default "config/mcp_policies.json"
- [X] T043 [US2] Create RoleBasedAuthorizationMiddleware with policy_file parameter in create_server()
- [X] T044 [US2] Register authorization middleware with server.add_middleware() AFTER auth middleware
- [X] T045 [US2] Verify authorization middleware registration occurs BEFORE _register_tools() call
- [ ] T046 [US2] [Manual] Test admin role by setting GRAPHITI_API_KEY_ADMIN and calling all tools
- [ ] T047 [US2] [Manual] Test readonly role by calling tools/list and verifying only 5 tools returned
- [ ] T048 [US2] [Manual] Test readonly role by calling add_memory and verifying 403 Forbidden response
- [ ] T049 [US2] [Manual] Test analyst role by calling add_memory and verifying 200 success response
- [ ] T050 [US2] [Manual] Test analyst role by calling delete_entity_edge and verifying 403 Forbidden response

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently. Role-based access control fully functional.

---

## Phase 5: User Story 3 - Audit and Monitoring (Priority: P3)

**Goal**: Log all authentication attempts and tool executions with user identity

**Independent Test**: Perform operations with different API keys, verify all actions logged with appropriate detail

### Implementation for User Story 3

- [X] T051 [US3] Import logging module in src/middleware/auth.py
- [X] T052 [US3] Create logger instance in src/middleware/auth.py using logging.getLogger(__name__)
- [X] T053 [US3] Add info log statement in dispatch method after successful authentication
- [X] T054 [US3] Include user_id and role in success log message from principal dictionary
- [X] T055 [US3] Include request.url.path in success log message for audit trail
- [X] T056 [US3] Add warning log statement in dispatch method for failed authentication
- [X] T057 [US3] Include truncated token (first 8 chars) in failure log message
- [X] T058 [US3] Include request.url.path in failure log message for audit trail
- [X] T059 [US3] Timestamp already configured in server.py logging.basicConfig (DATE_FORMAT)
- [ ] T060 [US3] [Manual] Test logging by making authenticated request and checking log output contains user info
- [ ] T061 [US3] [Manual] Test logging by making failed auth request and verifying warning logged with truncated key
- [ ] T062 [US3] [Manual] Verify no full API keys appear in log output (security check)
- [ ] T063 [US3] [Manual] Test log correlation by making multiple requests with same API key and verifying user_id consistent

**Checkpoint**: All user stories should now be independently functional. Complete audit logging in place.

---

## Phase 6: Documentation & Deployment

**Purpose**: Documentation and deployment preparation

- [X] T064 [P] Create docs/SECURITY.md file with API key management guide
- [X] T065 [P] Document API key generation instructions in SECURITY.md using secrets.token_urlsafe
- [X] T066 [P] Document role descriptions (admin/readonly/analyst) in SECURITY.md
- [X] T067 [P] Document policy file format in SECURITY.md with example JSON
- [X] T068 [P] Document key rotation procedure in SECURITY.md (manual for MVP)
- [X] T069 [P] Document security best practices in SECURITY.md (never commit keys, use env vars)
- [ ] T070 [P] Add security configuration section to docs/FASTMCP_CLOUD_DEPLOYMENT.md
- [ ] T071 [P] Document GRAPHITI_API_KEY_* environment variables in FASTMCP_CLOUD_DEPLOYMENT.md
- [ ] T072 [P] Document EUNOMIA_POLICY_FILE environment variable in FASTMCP_CLOUD_DEPLOYMENT.md
- [ ] T073 [P] Document GRAPHITI_AUTH_ENABLED environment variable in FASTMCP_CLOUD_DEPLOYMENT.md
- [ ] T074 [P] Add security note to README.md referencing SECURITY.md
- [X] T075 Create .env.example file with placeholder API key values (NOT real keys)
- [X] T076 Add config/mcp_policies.json to git (no secrets in this file, safe to commit)
- [X] T077 Verify .gitignore excludes .env file (do not commit real API keys)

**Checkpoint**: Documentation complete, deployment configuration documented

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [X] T078 [P] Add docstrings to AuthService class and methods
- [X] T079 [P] Add docstrings to BearerTokenAuthMiddleware class and methods
- [X] T080 [P] Add type hints to all function signatures in src/services/auth_service.py
- [X] T081 [P] Add type hints to all function signatures in src/middleware/auth.py
- [X] T082 [P] Run ruff format on src/services/auth_service.py and src/middleware/auth.py
- [X] T083 [P] Run ruff check --fix on modified files
- [X] T084 [P] Run pyright type checker on modified files and fix any type errors
- [ ] T085 [Automated] Verify existing test suite still passes (zero regression requirement)
- [ ] T086 [Manual] Test complete authentication flow from Claude Code MCP client with bearer token
- [ ] T087 [Automated] Benchmark auth overhead and verify <5ms latency requirement
- [ ] T088 [Automated] Test 100 concurrent connections and verify no performance degradation
- [ ] T089 [Manual] Review all code for security issues (no hardcoded keys, proper error handling)
- [ ] T090 [Manual] Verify health and status endpoints still accessible without authentication

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3-5)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel (if staffed)
  - Or sequentially in priority order (P1 → P2 → P3)
- **Documentation (Phase 6)**: Can start after US1 completes, no blocking dependencies
- **Polish (Phase 7)**: Depends on all desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P2)**: Can start after Foundational (Phase 2) - Builds on US1 auth but independently testable
- **User Story 3 (P3)**: Can start after Foundational (Phase 2) - Adds logging to US1 auth but independently testable

### Within Each User Story

- Models before services
- Services before middleware
- Middleware registration before tool registration
- Core implementation before integration testing
- Story complete before moving to next priority

### Parallel Opportunities

- All Setup tasks marked [P] can run in parallel
- All Documentation tasks marked [P] can run in parallel
- All Polish tasks marked [P] can run in parallel
- Once Foundational phase completes, all user stories can start in parallel (if team capacity allows)
- Different user stories can be worked on in parallel by different team members

---

## Parallel Example: User Story 1

```bash
# After Foundational phase completes, start User Story 1:
# Tasks T017-T034 must run sequentially (all modify same file src/server.py or depend on each other)
# But documentation (Phase 6) can start in parallel once US1 core is done
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T004)
2. Complete Phase 2: Foundational (T005-T016) - CRITICAL - blocks all stories
3. Complete Phase 3: User Story 1 (T017-T034)
4. **STOP and VALIDATE**: Test User Story 1 independently
5. Deploy/demo if ready

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently → Deploy/Demo (MVP!)
3. Add User Story 2 → Test independently → Deploy/Demo
4. Add User Story 3 → Test independently → Deploy/Demo
5. Each story adds value without breaking previous stories

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (T017-T034)
   - Developer B: User Story 2 (T035-T050) - can start after US1 core auth
   - Developer C: Documentation (T064-T077) - can start anytime
3. Stories complete and integrate independently

---

## Notes

- [P] tasks = different files, no dependencies
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: vague tasks, same file conflicts, cross-story dependencies that break independence

---

## Task Summary

**Total Tasks**: 104 (updated from 90 - added Claude Code integration phase)
- **Setup**: 4 tasks
- **Foundational**: 12 tasks (BLOCKING)
- **User Story 1 (P1)**: 18 tasks - Authentication
- **Claude Code Integration**: 14 tasks (9 documentation [P], 5 manual tests)
- **User Story 2 (P2)**: 16 tasks - Authorization
- **User Story 3 (P3)**: 13 tasks - Audit Logging
- **Documentation**: 14 tasks
- **Polish**: 13 tasks

**Parallel Opportunities**: 36 tasks marked [P] can run in parallel within their phase (up from 27)

**MVP Scope**: Setup (4) + Foundational (12) + US1 (18) + Claude Integration (14) = 48 tasks for minimum viable security with Claude Code support

**Test Categorization**:
- **[Manual]**: Tasks requiring manual verification (curl tests, Claude Code UI testing)
- **[Automated]**: Tasks that can be implemented as pytest tests (implied when no [Manual] tag)

**Independent Testing**: Each user story (US1, US2, US3) and Claude Code integration can be tested independently and delivers value standalone
