# Feature Specification: MCP Server Security

**Feature Branch**: `001-mcp-security`
**Created**: 2025-12-01
**Status**: Draft
**Input**: User description: "Implement non-interactive bearer token authentication + Eunomia authorization for Graphiti MCP server deployed on FastMCP Cloud, enabling secure access from Claude Code without fragile OAuth browser flows."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Secure Server Access with API Key (Priority: P1)

A developer or system needs to securely access the Graphiti MCP server from Claude Code or other MCP clients without browser-based authentication flows. They configure their client with an API key and can immediately start using all authorized tools without any interactive prompts or popups.

**Why this priority**: This is the foundational security layer. Without it, the server remains completely open to unauthorized access. This story delivers immediate value by protecting all server endpoints.

**Independent Test**: Can be fully tested by configuring a client with a valid API key, making tool calls, and verifying that requests with invalid keys are rejected. Delivers complete authentication protection for the server.

**Acceptance Scenarios**:

1. **Given** a deployed MCP server with authentication enabled, **When** a client connects with a valid API key in the Authorization header, **Then** the connection succeeds and tools are accessible
2. **Given** authentication is enabled, **When** a client attempts to connect without an API key, **Then** the connection is rejected with 401 Unauthorized
3. **Given** authentication is enabled, **When** a client connects with an invalid API key, **Then** the connection is rejected with 401 Unauthorized
4. **Given** a valid API key, **When** the client makes multiple requests, **Then** all requests are authenticated without re-prompting
5. **Given** the server is running, **When** health check endpoints are accessed without authentication, **Then** they respond successfully (health endpoints bypass auth)
6. **Given** a `.claude.json` MCP config referencing the FastMCP Cloud URL and providing a valid bearer token via its `auth` field, **When** Claude Code executes `tools/list`, **Then** unauthorized tools are filtered according to Eunomia policy and authorized tool calls succeed without interactive authentication

---

### User Story 2 - Role-Based Tool Access Control (Priority: P2)

An administrator needs to control which tools different users can access based on their roles (admin, readonly, analyst). They define policies that specify which tools each role can list and execute. Users with readonly role can only search and view data, while admins can perform write operations.

**Why this priority**: After securing the server (P1), fine-grained authorization prevents privilege escalation and ensures users only access appropriate tools for their role. This is essential for production deployment with multiple user types.

**Independent Test**: Can be tested by configuring policies for different roles, connecting with API keys for each role, and verifying that tool listing filters properly and unauthorized tool calls are blocked. Delivers role-based access control independently of authentication.

**Acceptance Scenarios**:

1. **Given** a readonly user, **When** they request the tools list, **Then** only search and read tools are shown (search_nodes, search_memory_facts, get_episodes, get_entity_edge, get_status)
2. **Given** a readonly user, **When** they attempt to call add_memory, **Then** the request is blocked with 403 Forbidden
3. **Given** an admin user, **When** they request the tools list, **Then** all tools are shown including write operations
4. **Given** an admin user, **When** they call any tool including destructive operations (clear_graph), **Then** the request succeeds
5. **Given** policies are updated, **When** a user reconnects, **Then** their tool access reflects the new policies without code changes

---

### User Story 3 - Audit and Monitoring (Priority: P3)

Operations team needs visibility into who is accessing the server and what operations they perform. All authentication attempts (successful and failed) and tool executions are logged with user identity, timestamp, and outcome. Logs include API key identifiers (not full keys) for security analysis.

**Why this priority**: After authentication and authorization are working (P1, P2), audit logging enables security monitoring, compliance, and debugging. While important, the system is functional without detailed logging.

**Independent Test**: Can be tested by performing various operations with different API keys and verifying that all actions are logged with appropriate detail. Delivers complete audit trail independently of auth/authz functionality.

**Acceptance Scenarios**:

1. **Given** a client successfully authenticates, **When** the request is processed, **Then** a log entry records the API key identifier, timestamp, and success
2. **Given** a failed authentication attempt, **When** the request is rejected, **Then** a log entry records the attempted key identifier (truncated) and failure reason
3. **Given** a tool is executed, **When** the operation completes, **Then** a log entry records the user, tool name, parameters (sanitized), and outcome
4. **Given** multiple requests from the same user, **When** reviewing logs, **Then** all operations from that user can be correlated by their API key identifier
5. **Given** a security incident, **When** investigating logs, **Then** the timeline of all authentication and authorization events is reconstructible

---

### Edge Cases

- What happens when an API key is revoked mid-session? (Subsequent requests fail with 401, existing validated requests complete)
- How does the system handle malformed Authorization headers? (Return 401 with clear error message)
- What happens when policy files are updated while the server is running? (Eunomia policy updates require server restart for v1; hot reload is explicitly out of scope)
- How does the system handle concurrent requests from the same API key? (All requests are independently validated, no session state maintained)
- What happens if Eunomia middleware fails to load? (Server startup fails with clear error, not partially secured state)
- How are rate limits enforced per API key? (Outside initial scope, but architecture should support future rate limiting)

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST authenticate all requests using bearer tokens in the Authorization header (format: `Authorization: Bearer <token>`)
- **FR-002**: System MUST validate API keys against a configured set of valid keys stored in environment variables
- **FR-003**: System MUST reject unauthenticated requests with HTTP 401 Unauthorized (except health/status endpoints)
- **FR-004**: System MUST attach user principal (user_id, role) to request context after successful authentication for use by tools
- **FR-005**: System MUST exempt /health and /status endpoints from authentication requirements
- **FR-006**: System MUST support declarative policy files defining which tools each role can access
- **FR-007**: System MUST filter tools/list responses based on user role permissions (hide unauthorized tools)
- **FR-008**: System MUST block tools/call requests for unauthorized tools with HTTP 403 Forbidden
- **FR-009**: System MUST log all authentication attempts (success and failure) with API key identifier and timestamp
- **FR-010**: System MUST log all tool executions with user identity, tool name, and outcome
- **FR-011**: System MUST support multiple roles (minimum: admin, readonly, analyst) with different tool access levels
- **FR-012**: System MUST allow configuration entirely through environment variables (no code changes per deployment)
- **FR-013**: System MUST initialize authentication and authorization middleware before any tool registration
- **FR-014**: System MUST maintain the factory pattern entrypoint (`create_server()`) for FastMCP Cloud compatibility
- **FR-015**: System MUST preserve existing tool functionality (all 9 Graphiti MCP tools: add_memory, search_nodes, search_memory_facts, delete_entity_edge, delete_episode, get_entity_edge, get_episodes, clear_graph, get_status)

### Key Entities

- **API Key**: Secure token identifying a user/system, format `sk_<env>_<random>`, stored as environment variable, associated with a role
- **User Principal**: Runtime identity attached to authenticated request, contains user_id (derived from API key) and role (admin/readonly/analyst)
- **Policy**: Declarative rule set specifying which tools a role can access, stored in JSON format, loaded at server startup
- **Role**: Security classification (admin, readonly, analyst) determining tool access permissions
- **Audit Log Entry**: Record of authentication or authorization event, contains timestamp, user identifier (truncated API key), action, and outcome

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Claude Code client connects to secured MCP server and executes authorized tools without any browser-based authentication (zero interactive prompts)
- **SC-002**: Unauthorized access attempts are blocked within 10ms with appropriate error codes (401 for auth, 403 for authz)
- **SC-003**: Server supports at least 100 concurrent authenticated connections without performance degradation
- **SC-004**: All authentication and authorization events are logged with sufficient detail for security audit (user identity, timestamp, action, outcome)
- **SC-005**: Role-based access control reduces unauthorized tool access attempts to zero (policy enforcement is complete)
- **SC-006**: Server configuration changes (new API keys, policy updates) deploy to FastMCP Cloud without code modifications (pure environment variable updates)
- **SC-007**: Existing Graphiti MCP functionality remains intact - all tools work identically for authorized users (zero regression)
- **SC-008**: Security implementation adds less than 5ms latency to tool execution for authenticated requests (minimal performance impact)

### Non-Functional Requirements

- **NFR-001**: Authentication must be stateless (no session storage required)
- **NFR-002**: API keys must be stored securely (environment variables, never in code or logs)
- **NFR-003**: Failed authentication attempts must not leak information about valid key formats or patterns
- **NFR-004**: Audit logs must not contain full API keys (use truncated identifiers)
- **NFR-005**: Authorization policies must be human-readable and version-controllable (JSON format)

## Out of Scope

- Browser-based OAuth flows or user login pages
- API key generation or rotation tooling (manual generation acceptable for MVP)
- Advanced rate limiting per API key (defer to future iteration)
- JWT token validation (start with simple API keys, architecture allows future JWT support)
- Integration with external identity providers (RemoteOAuth deferred to future)
- Web UI for policy management (JSON file editing acceptable for MVP)
- Automated API key lifecycle management (manual revocation acceptable)
- Multi-factor authentication
- IP allowlisting or geo-restrictions

## Assumptions

- API keys are generated manually using secure random generators (e.g., `secrets.token_urlsafe(32)`)
- Keys are distributed securely to users out-of-band (not through the system itself)
- FastMCP Cloud environment variables support is sufficient for all configuration needs
- Policy files are deployed alongside code or referenced via environment variable path
- Three roles (admin, readonly, analyst) cover initial use cases
- Eunomia MCP middleware is compatible with FastMCP server architecture
- Health and status endpoints do not require authentication (needed for monitoring)
- Audit logs are written to stdout/stderr for collection by infrastructure logging
- Users accept stateless authentication (no session management, bearer token on every request)
- Failed authentication attempts are acceptable to log at info/warn level (not critical alerts)

## Dependencies

- FastMCP server framework (2.13.1+)
- Eunomia MCP middleware for authorization (requires installation)
- Starlette ASGI framework for middleware support
- Environment variable support in FastMCP Cloud deployment
- Existing Graphiti MCP server codebase and tools
