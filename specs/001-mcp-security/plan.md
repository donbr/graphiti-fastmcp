# Implementation Plan: MCP Server Security

**Branch**: `001-mcp-security` | **Date**: 2025-12-01 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-mcp-security/spec.md`

## Summary

Implement non-interactive bearer token authentication and Eunomia-based authorization for the Graphiti MCP server. Enable secure access from Claude Code and other MCP clients without browser-based OAuth flows. Use API keys validated via Starlette middleware, with role-based tool access control enforced by Eunomia policies. Deploy to FastMCP Cloud using environment variables exclusively.

**Technical Approach**: Add authentication middleware to `src/server.py:create_server()` factory function, register Eunomia middleware for authorization, configure via environment variables, maintain backward compatibility with existing tools and closure-based architecture.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**: FastMCP 2.13.1+, Starlette (ASGI middleware), Eunomia MCP middleware, graphiti-core 0.24.1
**Storage**: FalkorDB/Neo4j (existing, unchanged), environment variables for API keys, JSON file for policies
**Testing**: pytest, existing test infrastructure in `tests/`
**Target Platform**: FastMCP Cloud (HTTP transport), local dev (HTTP/STDIO)
**Project Type**: single (server-side only, no frontend)
**Performance Goals**: <5ms auth overhead per request, 100+ concurrent connections
**Constraints**: <200ms tool execution (including auth), stateless authentication, zero regression on existing tools
**Scale/Scope**: 9 MCP tools, 3 roles (admin/readonly/analyst), env-based config for Cloud deployment

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: Non-Interactive Authentication

✅ **PASS** - Authentication via `Authorization: Bearer <token>` header, no browser interaction
- Middleware validates token from header on every request
- No OAuth redirects, no login pages
- Works from Claude Code, curl, any HTTP client

### Principle II: Bearer Token Simplicity

✅ **PASS** - Standard HTTP bearer authentication
- Format: `Authorization: Bearer sk_<env>_<random>`
- No custom schemes, works with FastMCP client `auth=` parameter
- Starlette middleware extracts and validates

### Principle III: Tool-Level Authorization

✅ **PASS** - Eunomia middleware enforces tool access
- Policies in `mcp_policies.json` define role → tool mappings
- `tools/list` filtered by role (hide unauthorized tools)
- `tools/call` blocked for unauthorized tools (403 Forbidden)

### Principle IV: Environment-Based Configuration

✅ **PASS** - Pure environment variable configuration
- API keys: `GRAPHITI_API_KEY_ADMIN`, `GRAPHITI_API_KEY_READONLY`, etc.
- Policy file path: `EUNOMIA_POLICY_FILE` (defaults to `config/mcp_policies.json`)
- No code changes between dev/prod deployments

### Principle V: Future-Proof Design

✅ **PASS** - Extensible to JWT/RemoteOAuth
- Middleware architecture supports swapping auth validators
- Can replace API key dict with JWT verifier function (fastmcp.server.auth.providers.jwt.JWTVerifier)
- Can add RemoteAuthProvider later without changing tool code

### Principle VI: Development Mode Toggle

✅ **PASS** - Configurable auth via `GRAPHITI_AUTH_ENABLED` environment variable
- Default: auth enabled (`GRAPHITI_AUTH_ENABLED=true`)
- Dev opt-out: `GRAPHITI_AUTH_ENABLED=false` disables auth for local iteration
- Logs warning on startup when auth disabled
- Production deployment enforces auth via Cloud environment variables

### Principle VII: Observability & Structured Logging

✅ **PASS** - Comprehensive logging with secret protection
- Auth middleware logs all authentication attempts (success/failure)
- Logs include: principal identity, tool name, outcome, truncated token (first 8 chars)
- No full API keys or sensitive payloads in logs
- Structured format enables correlation by user_id

**Gate Result**: ✅ ALL PRINCIPLES SATISFIED (7/7) - Proceed to Phase 0

## Project Structure

### Documentation (this feature)

```text
specs/001-mcp-security/
├── plan.md              # This file (/speckit.plan command output)
├── spec.md              # Feature specification (complete)
├── research.md          # Phase 0 output (API key generation, Eunomia setup, middleware patterns)
├── data-model.md        # Phase 1 output (API Key, UserPrincipal, Policy entities)
├── quickstart.md        # Phase 1 output (dev setup, testing guide)
├── contracts/           # Phase 1 output (middleware interface, Eunomia policy schema)
└── checklists/
    └── requirements.md  # Spec validation (complete)
```

### Source Code (repository root)

```text
src/
├── server.py                  # MODIFY: Add auth middleware to create_server()
│                              # PRIMARY ENTRYPOINT: src/server.py:create_server
│                              # (Factory pattern, FastMCP Cloud compatible)
├── graphiti_mcp_server.py     # LEGACY: Global state pattern (backward compatibility only)
├── config/
│   └── schema.py              # OPTIONAL: Add AuthConfig Pydantic model
│                              # (Can defer to v2, use os.getenv directly in v1)
├── services/
│   └── auth_service.py        # NEW: API key validation, principal creation
└── middleware/
    └── auth.py                # NEW: Starlette BaseHTTPMiddleware for bearer token validation

config/
└── mcp_policies.json    # NEW: Eunomia policy definitions (admin/readonly/analyst roles)

tests/
├── unit/
│   ├── test_auth_service.py      # NEW: API key validation tests
│   └── test_auth_middleware.py   # NEW: Middleware behavior tests
└── integration/
    └── test_secured_server.py     # NEW: End-to-end auth/authz tests

docs/
├── FASTMCP_CLOUD_DEPLOYMENT.md   # MODIFY: Add security env vars section
└── SECURITY.md                    # NEW: API key management, policy updates
```

**Structure Decision**: Single project structure (existing pattern). All changes in `src/`, new auth components in `src/middleware/` and `src/services/`. Eunomia policies in `config/`. No frontend/mobile components needed.

## Complexity Tracking

> **No violations - all constitution principles satisfied**

N/A - Implementation aligns with all five constitution principles without exceptions.

## Phase 0: Research & Technology Selection

### Research Tasks

1. **API Key Format and Generation**
   - Decision: Use `sk_<env>_<random>` format (e.g., `sk_prod_xQ7vK8pL2mN9rT4w`)
   - Generation: Python `secrets.token_urlsafe(32)` for cryptographically secure random
   - Storage: Environment variables (`GRAPHITI_API_KEY_<ROLE>=sk_...`)
   - Rationale: Industry standard (OpenAI, Stripe pattern), URL-safe, 256-bit entropy

2. **Eunomia MCP Middleware Integration**
   - Installation: `pip install eunomia-mcp`
   - Usage: `from eunomia_mcp import create_eunomia_middleware`
   - Registration: `mcp.add_middleware(create_eunomia_middleware(policy_file="..."))`
   - Policy format: JSON with `{"version": "1.0", "policies": [...]}`
   - Tool mapping: Eunomia auto-maps MCP methods (tools/list, tools/call) to authz checks

3. **Starlette Middleware Best Practices**
   - Pattern: `BaseHTTPMiddleware` subclass with `async def dispatch(request, call_next)`
   - Request context: Attach principal to `request.state.api_principal`
   - Error responses: Return `JSONResponse({"error": "..."}, status_code=401/403)`
   - Health endpoint exemption: Check `request.url.path in ["/health", "/status"]` before auth

4. **FastMCP Factory Pattern with Middleware**
   - Middleware registration: Call `mcp.add_middleware(...)` before `_register_tools(...)`
   - Order matters: Auth middleware → Eunomia middleware → tool registration
   - Closure preservation: Tools access services via closure, auth via `request_ctx.get()`
   - Example: `from fastmcp.server.context import request_ctx` then `ctx.request.state.api_principal`

5. **Environment Variable Configuration Strategy**
   - API keys: `GRAPHITI_API_KEY_<ROLE>` (e.g., `_ADMIN`, `_READONLY`, `_ANALYST`)
   - Policy file: `EUNOMIA_POLICY_FILE` (default: `config/mcp_policies.json`)
   - Enable/disable auth: `GRAPHITI_AUTH_ENABLED` (default: `true`)
   - Load in `create_server()`: Use `os.getenv()` or add to `GraphitiConfig` Pydantic model

**Output**: `research.md` documenting all decisions with code snippets

## Phase 1: Design & Implementation Plan

### Data Model

**Entity**: API Key
- Format: `sk_<env>_<random>` (string, 48 chars)
- Associated role: admin | readonly | analyst
- Storage: Environment variable
- Validation: Check existence in configured key-to-role mapping

**Entity**: User Principal
- Fields: `user_id` (string, derived from key), `role` (enum)
- Lifecycle: Created per-request after auth, attached to `request.state`
- Usage: Tools read via `request_ctx.get().request.state.api_principal`

**Entity**: Policy
- Schema: JSON with `policies` array, each entry specifies `role` → allowed `resources` (tools)
- Example:
  ```json
  {
    "version": "1.0",
    "policies": [
      {
        "role": "admin",
        "resources": ["*"]
      },
      {
        "role": "readonly",
        "resources": ["search_nodes", "search_memory_facts", "get_episodes", "get_entity_edge", "get_status"]
      }
    ]
  }
  ```
- Loading: Eunomia loads at server startup
- Updates: Require server restart (acceptable for MVP)

**Output**: `data-model.md` with entity definitions

### API Contracts

**Contract**: Authentication Middleware Interface
- Input: HTTP request with `Authorization: Bearer <token>` header
- Output:
  - Success: Request continues with `request.state.api_principal = {"user_id": "...", "role": "..."}`
  - Failure: 401 JSON response `{"error": "Unauthorized", "detail": "..."}`
- Exempt paths: `/health`, `/status`

**Contract**: Eunomia Policy Schema
- File: `config/mcp_policies.json`
- Schema: `{"version": "1.0", "policies": [{"role": str, "resources": [str]}]}`
- Validation: Eunomia validates on load, server fails to start if invalid

**Contract**: Tool Access via Principal
- Tools read principal: `from fastmcp.server.context import request_ctx; principal = request_ctx.get().request.state.api_principal`
- Principal guaranteed present (middleware ensures it)
- Optional logging: Tools can log `principal["user_id"]` for audit

**Output**: `contracts/` directory with schema files

### Quickstart Guide

**Local Development**:
1. Generate API keys:
   ```bash
   python -c "import secrets; print(f'sk_dev_{secrets.token_urlsafe(32)}')"
   ```
2. Set environment variables:
   ```bash
   export GRAPHITI_API_KEY_ADMIN=sk_dev_...
   export GRAPHITI_API_KEY_READONLY=sk_dev_...
   ```
3. Create `config/mcp_policies.json`
4. Run server: `uv run src/server.py`
5. Test with curl:
   ```bash
   curl -H "Authorization: Bearer sk_dev_..." http://localhost:8000/mcp
   ```

**FastMCP Cloud Deployment**:
1. Set env vars in Cloud UI: `GRAPHITI_API_KEY_ADMIN`, `GRAPHITI_API_KEY_READONLY`, `EUNOMIA_POLICY_FILE`
2. Commit `config/mcp_policies.json` to repo
3. Deploy (entrypoint: `src/server.py:create_server`)

**Testing Authentication**:
```bash
# Should succeed
curl -H "Authorization: Bearer $GRAPHITI_API_KEY_ADMIN" http://localhost:8000/mcp

# Should fail (401)
curl http://localhost:8000/mcp

# Health should succeed without auth
curl http://localhost:8000/health
```

**Output**: `quickstart.md` with setup instructions

## Implementation Phases

### Phase 2: Authentication Implementation (User Story 1 - P1)

**Goal**: Secure server with bearer token authentication

**Files to Create**:
1. `src/services/auth_service.py` - API key validation logic
2. `src/middleware/auth.py` - Starlette middleware
3. `tests/unit/test_auth_service.py` - Unit tests
4. `tests/unit/test_auth_middleware.py` - Middleware tests

**Files to Modify**:
1. `src/server.py` - Add middleware registration in `create_server()` (PRIMARY ENTRYPOINT)
2. `pyproject.toml` - No changes needed (Starlette already dependency of FastMCP)

**Note**: `AuthConfig` Pydantic model in `src/config/schema.py` is OPTIONAL and deferred to v2. Use `os.getenv()` directly in `create_server()` for v1 MVP to minimize complexity.

**Key Functions**:
```python
# src/services/auth_service.py
class AuthService:
    def __init__(self, api_keys: dict[str, dict]):
        self.api_keys = api_keys  # {"sk_dev_...": {"user_id": "admin", "role": "admin"}}

    def validate_token(self, token: str) -> dict | None:
        return self.api_keys.get(token)

# src/middleware/auth.py
class BearerTokenAuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, auth_service: AuthService):
        super().__init__(app)
        self.auth_service = auth_service

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ["/health", "/status"]:
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        token = auth_header[7:]
        principal = self.auth_service.validate_token(token)
        if principal is None:
            return JSONResponse({"error": "Invalid token"}, status_code=401)

        request.state.api_principal = principal
        return await call_next(request)
```

**Integration in create_server()**:
```python
# src/server.py (modify create_server function)
async def create_server() -> FastMCP:
    # ... existing config and service initialization ...

    # NEW: Initialize auth service
    api_keys = {
        os.getenv("GRAPHITI_API_KEY_ADMIN"): {"user_id": "admin", "role": "admin"},
        os.getenv("GRAPHITI_API_KEY_READONLY"): {"user_id": "readonly", "role": "readonly"},
    }
    auth_service = AuthService({k: v for k, v in api_keys.items() if k})  # Filter None keys

    # ... existing server creation ...

    # NEW: Register auth middleware (BEFORE tool registration)
    if os.getenv("GRAPHITI_AUTH_ENABLED", "true").lower() == "true":
        server.add_middleware(BearerTokenAuthMiddleware, auth_service=auth_service)

    # ... existing tool registration ...

    return server
```

**Testing Strategy**:
- Unit tests: Mock Request, test middleware logic
- Integration tests: Start server, make HTTP requests with/without auth headers
- Verify 401 for missing/invalid tokens, 200 for valid tokens
- Verify health endpoint bypasses auth

### Phase 2.5: Claude Code Integration

**Goal**: Enable and document Claude Code MCP client configuration with bearer token authentication

**Why this phase**: Claude Code is the primary client for this MCP server. Explicit integration documentation and testing ensures the authentication flow works seamlessly in the intended production environment.

**Files to Create**:
1. `docs/CLAUDE_MCP_CONFIG.md` - Claude Code configuration guide
2. `.claude.json.example` - Example MCP configuration (optional, for reference)

**Files to Modify**:
1. `docs/SECURITY.md` - Add Claude Code configuration section
2. `docs/FASTMCP_CLOUD_DEPLOYMENT.md` - Add Claude Code client setup section

**Claude Code MCP Configuration Structure**:

Example `.claude.json` entry for local development:
```json
{
  "mcpServers": {
    "graphiti-mcp": {
      "url": "http://localhost:8000/mcp/",
      "transport": "http",
      "auth": {
        "type": "bearer",
        "token": "${GRAPHITI_API_KEY_ADMIN}"
      }
    }
  }
}
```

Example for FastMCP Cloud deployment:
```json
{
  "mcpServers": {
    "graphiti-mcp-cloud": {
      "url": "https://your-project.fastmcp.cloud/mcp/",
      "transport": "http",
      "auth": {
        "type": "bearer",
        "token": "${GRAPHITI_API_KEY_ADMIN}"
      }
    }
  }
}
```

**Documentation Content** (`docs/CLAUDE_MCP_CONFIG.md`):
- Overview of Claude Code MCP configuration
- Step-by-step setup for local development
- Step-by-step setup for FastMCP Cloud
- Environment variable management (`.env` file for local, not committed)
- Bearer token configuration syntax
- Troubleshooting auth errors (401/403)
- Testing tool access: `tools/list` and `tools/call` examples
- Switching between roles (admin/readonly/analyst) by changing token

**Testing Strategy**:
- Manual test: Configure Claude Code with valid admin token, verify tools/list shows all tools
- Manual test: Call `add_memory` from Claude Code, verify success
- Manual test: Configure with readonly token, verify `add_memory` blocked with 403
- Manual test: Configure with invalid token, verify 401 error with clear message
- Manual test: Verify health endpoint accessible without token

**Integration Verification Checklist**:
- [ ] Claude Code connects successfully with bearer token
- [ ] tools/list filtered by role (admin sees all, readonly sees subset)
- [ ] tools/call succeeds for authorized tools
- [ ] tools/call blocked for unauthorized tools (403 Forbidden)
- [ ] Clear error messages for missing/invalid tokens
- [ ] No interactive auth prompts (no browser popups)

### Phase 3: Authorization Implementation (User Story 2 - P2)

**Goal**: Implement role-based tool access control with Eunomia

**Files to Create**:
1. `config/mcp_policies.json` - Policy definitions
2. `tests/integration/test_authorization.py` - Policy enforcement tests

**Files to Modify**:
1. `src/server.py` - Add Eunomia middleware registration
2. `pyproject.toml` - Add `eunomia-mcp` dependency

**Eunomia Policy File** (`config/mcp_policies.json`):
```json
{
  "version": "1.0",
  "policies": [
    {
      "role": "admin",
      "resources": ["*"]
    },
    {
      "role": "readonly",
      "resources": [
        "search_nodes",
        "search_memory_facts",
        "get_episodes",
        "get_entity_edge",
        "get_status"
      ]
    },
    {
      "role": "analyst",
      "resources": [
        "search_nodes",
        "search_memory_facts",
        "get_episodes",
        "get_entity_edge",
        "get_status",
        "add_memory"
      ]
    }
  ]
}
```

**Integration in create_server()**:
```python
# src/server.py (after auth middleware)
from eunomia_mcp import create_eunomia_middleware

async def create_server() -> FastMCP:
    # ... auth middleware registration ...

    # NEW: Register Eunomia middleware (AFTER auth, BEFORE tools)
    policy_file = os.getenv("EUNOMIA_POLICY_FILE", "config/mcp_policies.json")
    eunomia_middleware = create_eunomia_middleware(policy_file=policy_file)
    server.add_middleware(eunomia_middleware)

    # ... existing tool registration ...
```

**Testing Strategy**:
- Test admin role: Can access all tools
- Test readonly role: `tools/list` only shows readonly tools, `tools/call add_memory` returns 403
- Test analyst role: Can add_memory but not delete_entity_edge
- Test policy updates: Modify JSON, restart server, verify changes

### Phase 4: Audit Logging (User Story 3 - P3)

**Goal**: Log all authentication and tool execution events

**Files to Modify**:
1. `src/middleware/auth.py` - Add logging to middleware
2. `src/server.py` - Add logging to tool wrappers (optional, can use FastMCP built-in logging)

**Logging Pattern**:
```python
import logging

logger = logging.getLogger(__name__)

# In auth middleware
async def dispatch(self, request: Request, call_next):
    # ... auth logic ...

    if principal is None:
        logger.warning(f"Auth failed: token={token[:8]}... path={request.url.path}")
        return JSONResponse({"error": "Invalid token"}, status_code=401)

    logger.info(f"Auth success: user={principal['user_id']} role={principal['role']} path={request.url.path}")
    # ...
```

**Tool Execution Logging** (optional enhancement):
- FastMCP likely has built-in request logging
- If needed, wrap tools or use Eunomia's audit logging feature
- Log format: `timestamp | user_id | tool_name | outcome | latency_ms`

**Testing Strategy**:
- Run operations, verify logs contain expected entries
- Check no full API keys in logs (only truncated identifiers)
- Verify correlation by user_id across multiple requests

### Phase 5: Documentation & Deployment

**Files to Create**:
1. `docs/SECURITY.md` - API key management guide

**Files to Modify**:
1. `docs/FASTMCP_CLOUD_DEPLOYMENT.md` - Add security configuration section
2. `README.md` - Add security note referencing SECURITY.md

**SECURITY.md Contents**:
- API key generation instructions
- Role descriptions (admin/readonly/analyst)
- Policy file format
- Key rotation procedure (manual for MVP)
- Security best practices (never commit keys, use env vars)

**Deployment Checklist**:
- [ ] Generate production API keys (unique per environment)
- [ ] Set env vars in FastMCP Cloud UI
- [ ] Commit `config/mcp_policies.json` (no secrets in this file)
- [ ] Deploy to Cloud (entrypoint: `src/server.py:create_server`)
- [ ] Test with curl/Claude Code using production keys
- [ ] Verify health endpoint accessible without auth
- [ ] Verify unauthorized requests blocked
- [ ] Monitor logs for auth failures

## Dependencies & Integration Points

### External Dependencies

1. **Eunomia MCP** - Add to `pyproject.toml`:
   ```toml
   eunomia-mcp = "^0.1.0"  # Check latest version
   ```

2. **Starlette** - Already included via FastMCP dependency

3. **Python secrets module** - Standard library, no install needed

### Internal Integration Points

1. **FastMCP Server** (`src/server.py`):
   - Modify `create_server()` to add middleware registrations
   - Order: auth middleware → Eunomia middleware → tool registration
   - Preserve existing service initialization and closure pattern

2. **Configuration** (`src/config/schema.py`):
   - Optional: Add `AuthConfig` Pydantic model
   - Validate env vars at startup
   - Fail fast if auth enabled but no keys configured

3. **Existing Tools**:
   - No modifications required (zero regression goal)
   - Tools can optionally read `request_ctx.get().request.state.api_principal` for logging
   - Eunomia filters/blocks at protocol level, not tool level

4. **Testing Infrastructure**:
   - Use existing pytest setup
   - Add fixtures for authenticated clients (with different roles)
   - Integration tests start server with test API keys

## Risk Mitigation

**Risk**: Eunomia incompatibility with FastMCP
**Mitigation**: Test Eunomia integration early in Phase 3, have fallback custom authz middleware

**Risk**: API keys leaked in logs
**Mitigation**: Truncate tokens in logs (first 8 chars only), add linter rule to catch accidental logging

**Risk**: Performance degradation from middleware
**Mitigation**: Benchmark auth overhead, optimize if >5ms (e.g., cache principal per request ID)

**Risk**: Policy updates require server restart
**Mitigation**: Document clearly, acceptable for MVP, add hot-reload in future iteration

**Risk**: Local dev workflow complexity
**Mitigation**: Provide clear quickstart.md, support `GRAPHITI_AUTH_ENABLED=false` for development

## Success Metrics

- **SC-001**: Claude Code connects with API key, no browser prompts ✅ (verify with manual test)
- **SC-002**: Unauthorized requests blocked <10ms ✅ (benchmark with pytest)
- **SC-003**: 100+ concurrent connections ✅ (load test with locust/ab)
- **SC-004**: All auth events logged ✅ (verify log output)
- **SC-005**: Policy enforcement complete ✅ (test all role × tool combinations)
- **SC-006**: Pure env var config ✅ (deploy without code changes)
- **SC-007**: Zero tool regression ✅ (run existing test suite)
- **SC-008**: <5ms auth overhead ✅ (benchmark middleware)

## Next Steps

1. **Run `/speckit.tasks`** to generate detailed task list from this plan
2. **Phase 0**: Create `research.md` with technology decisions
3. **Phase 1**: Create `data-model.md`, `contracts/`, `quickstart.md`
4. **Phase 2-5**: Implement per plan, test incrementally
5. **Deploy**: Follow deployment checklist

---

**Plan Status**: ✅ COMPLETE - Ready for task generation

All constitution principles satisfied. No complexity violations. Clear phase breakdown with file-level granularity. Integration points documented. Risk mitigation strategies defined.
