# Lessons Learned — 001-mcp-security (v2 - Verification Update)

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| v1 | 2025-12-01 | Implementation Agent | Initial lessons documenting critical middleware bug |
| v2 | 2025-12-01 | Verification Agent | Updated with fix verification and implementation confirmation |

---

## 1. Context & Intent

**Goal**: Implement non-interactive bearer token authentication and role-based authorization for Graphiti MCP server on FastMCP, with Claude Code and FastMCP clients as first-class consumers.

**Inputs**: constitution.md, spec.md, plan.md, tasks.md for 001-mcp-security.

---

## 2. Implementation Summary

### What Was Built

| Component | File | Description |
|-----------|------|-------------|
| Authentication Middleware | `src/middleware/auth.py` | Bearer token validation using FastMCP `Middleware` class |
| Authorization Middleware | `src/middleware/authorization.py` | Role-based tool access control |
| Auth Service | `src/services/auth_service.py` | API key validation and principal mapping |
| Policy Configuration | `config/mcp_policies.json` | Role-to-tool permission mappings |
| Server Integration | `src/server.py:208-244` | Middleware registration and configuration |

### Key Technical Decisions

1. **FastMCP Middleware Pattern**: Used `fastmcp.server.middleware.Middleware` base class with hooks (`on_call_tool`, `on_initialize`, `on_list_tools`) instead of Starlette's `BaseHTTPMiddleware`

2. **HTTP Header Access**: Used `get_http_headers()` from `fastmcp.server.dependencies` for HTTP transport header access

3. **State Management**: Principal stored via `context.fastmcp_context.set_state('api_principal', principal)` for cross-middleware access

4. **Health Endpoint Exemption**: Used `@server.custom_route` which is exempt from MCP middleware by design

---

## 3. What Went Well

### Planning Phase

- ✅ **Strong specification**: 3 user stories with clear FRs, NFRs, and measurable success criteria
- ✅ **Correct architecture targeting**: Plan identified `src/server.py:create_server()` as primary entrypoint
- ✅ **Task granularity**: 104 tasks with clear file paths enabled incremental work
- ✅ **Independent testability**: Each user story designed to be testable in isolation

### Implementation Phase

- ✅ **Correct FastMCP Middleware API**: Implementation uses proper `Middleware` base class with hook methods
- ✅ **Proper HTTP Header Access**: Uses `get_http_headers()` from FastMCP dependencies
- ✅ **Context State Management**: Principal correctly stored/retrieved via `fastmcp_context`
- ✅ **Security Logging**: Token truncation (8 chars) prevents key leakage in logs
- ✅ **Policy Loading**: JSON-based role-to-tool mapping works correctly

### Verification Phase

- ✅ **All US1 Authentication Tests Pass**: T031-T034 verified via curl + server logs
- ✅ **All US3 Audit Logging Tests Pass**: T060-T063 verified via server log analysis
- ✅ **Authorization Middleware Wired Correctly**: Code review confirms proper implementation
- ✅ **Health Endpoints Exempt**: T090 verified - endpoints accessible without auth

---

## 4. What Didn't Go Well (Original Issues)

### Root Cause: Contradictory Test Guidance

The original tasks.md contained line 6:
> "Tests are OPTIONAL - only included if explicitly requested"

This was corrected in v2, but the lesson remains: **Template defaults matter**.

### Documentation Gap: MCP Protocol Testing

**Issue**: Simple curl tests cannot verify tool-level authorization because `tools/call` requires an established SSE session with session ID.

**Impact**: T046, T048, T050 cannot be fully verified without MCP SDK client.

**Resolution**: Code review confirms correct implementation; SDK client tests recommended for full verification.

---

## 5. Technical Learnings

### FastMCP Middleware Architecture

**Key Insight**: FastMCP middleware is NOT the same as Starlette/ASGI middleware.

| Aspect | Starlette | FastMCP |
|--------|-----------|---------|
| Base Class | `BaseHTTPMiddleware` | `Middleware` |
| Method | `dispatch(request, call_next)` | `on_call_tool(context, call_next)` |
| HTTP Access | `request.headers` | `get_http_headers()` |
| State | `request.state` | `context.fastmcp_context.set_state()` |

**Source**: [gofastmcp.com/servers/middleware](https://gofastmcp.com/servers/middleware)

### Available Middleware Hooks

```python
on_message(context, call_next)     # All messages
on_request(context, call_next)      # All requests
on_notification(context, call_next) # Notifications
on_initialize(context, call_next)   # Session init
on_call_tool(context, call_next)    # Tool calls
on_read_resource(context, call_next)
on_get_prompt(context, call_next)
on_list_tools(context, call_next)
on_list_resources(context, call_next)
on_list_prompts(context, call_next)
```

### MCP Protocol Session Model

**Key Insight**: MCP over HTTP uses SSE (Server-Sent Events) with session management.

1. Client sends `initialize` request
2. Server returns session ID and capabilities
3. Subsequent requests must include session ID
4. Tool calls (`tools/call`) only work within established session

**Implication**: Simple HTTP POST tests can verify `initialize` but not `tools/call`.

---

## 6. Recommendations

### Immediate Actions

1. **Create MCP SDK Client Tests**: Use Python `mcp.ClientSession` for full authorization verification
2. **Fix test_fixtures Import**: Resolve import error in existing test suite
3. **Complete Deployment Docs**: Finish T070-T074 for FastMCP Cloud

### Process Improvements

1. **Template Update**: Ensure tasks-template.md has correct test requirements by default
2. **MCP Testing Guidance**: Add guidance for testing MCP servers (SDK client vs curl)
3. **Verification Checklist**: Add mandatory verification step before marking user stories complete

### Technical Debt

1. **Performance Testing**: Execute T087-T088 for latency and concurrency benchmarks
2. **Claude Code Integration**: Manual verification with Claude Code IDE (T034j-T034n)
3. **Security Review**: Complete T089 security checklist

---

## 7. Reference Materials

### Official Documentation

| Resource | URL | Description |
|----------|-----|-------------|
| FastMCP Middleware | [gofastmcp.com/servers/middleware](https://gofastmcp.com/servers/middleware) | Middleware API reference |
| FastMCP Dependencies | [gofastmcp.com/python-sdk/fastmcp-server-dependencies](https://gofastmcp.com/python-sdk/fastmcp-server-dependencies) | HTTP header access |
| FastMCP Bearer Auth | [gofastmcp.com/clients/auth/bearer](https://gofastmcp.com/clients/auth/bearer) | Client authentication |
| MCP Specification | [spec.modelcontextprotocol.io](https://spec.modelcontextprotocol.io) | Protocol specification |

### Key Code Patterns

**Authentication Middleware Pattern**:
```python
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.server.dependencies import get_http_headers
from mcp.shared.exceptions import McpError
from mcp.types import ErrorData

class BearerTokenAuthMiddleware(Middleware):
    def __init__(self, auth_service):
        self.auth_service = auth_service

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        headers = get_http_headers()
        # ... validate token ...
        context.fastmcp_context.set_state('api_principal', principal)
        return await call_next(context)
```

**Authorization Middleware Pattern**:
```python
class RoleBasedAuthorizationMiddleware(Middleware):
    async def on_call_tool(self, context: MiddlewareContext, call_next):
        principal = context.fastmcp_context.get_state('api_principal')
        tool_name = context.message.params.name
        if not self._is_tool_allowed(principal['role'], tool_name):
            raise McpError(ErrorData(code=-32000, message='Access denied'))
        return await call_next(context)
```

---

## 8. Verification Confirmation

### Tests Verified (2025-12-01)

| Test | Description | Status | Evidence |
|------|-------------|--------|----------|
| T031 | Health without auth | ✅ PASS | `{"status":"healthy"}` |
| T032 | Valid admin key | ✅ PASS | `serverInfo` in response |
| T033 | Invalid key rejected | ✅ PASS | Error response + log |
| T034 | Missing auth rejected | ✅ PASS | Error response + log |
| T047 | Readonly init | ✅ PASS | `user_id=readonly` in log |
| T049 | Analyst init | ✅ PASS | `user_id=analyst` in log |
| T060 | Success logging | ✅ PASS | `Authentication successful` |
| T061 | Failure logging | ✅ PASS | `Authentication failed` |
| T062 | No full keys in logs | ✅ PASS | grep verification |
| T063 | Log correlation | ✅ PASS | Consistent user_id |
| T090 | Health accessible | ✅ PASS | HTTP 200 |

### Implementation Verified

| Component | Verification Method | Status |
|-----------|---------------------|--------|
| `BearerTokenAuthMiddleware` | Code review | ✅ Correct FastMCP pattern |
| `RoleBasedAuthorizationMiddleware` | Code review | ✅ Correct hook implementation |
| Server integration | Log inspection | ✅ Middleware executing |
| Policy loading | Server startup log | ✅ 3 policies loaded |

---

## 9. Conclusion

The MCP Server Security implementation is **functional and correctly implemented**. All authentication tests pass, audit logging works correctly, and the authorization middleware is properly wired using FastMCP's middleware API.

**Outstanding Work**:
- Tool-level authorization tests require MCP SDK client (code review confirms correct implementation)
- Documentation completion (deployment guides)
- Performance benchmarking

**Key Success Factors**:
1. Correct use of FastMCP `Middleware` base class (not Starlette)
2. Proper HTTP header access via `get_http_headers()`
3. Context state management for cross-middleware principal sharing
4. Health endpoints exempt via `@server.custom_route`

---

**Verification Date**: 2025-12-01 21:52:00 UTC
**Verified By**: Claude Code (Verification Session)
