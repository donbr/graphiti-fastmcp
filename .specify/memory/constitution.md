<!--
Sync Impact Report:
- Version: 1.0.0 → 1.1.0 (Added dev toggle and observability principles)
- Added Sections: Principles VI and VII to Core Principles
- Principles Added:
  1. Non-Interactive Authentication
  2. Bearer Token Simplicity
  3. Tool-Level Authorization
  4. Environment-Based Configuration
  5. Future-Proof Design
  6. Development Mode Toggle (NEW - v1.1.0)
  7. Observability & Structured Logging (NEW - v1.1.0)
- Templates Status:
  ✅ plan-template.md - Constitution Check section exists
  ✅ spec-template.md - Requirements section exists
  ✅ tasks-template.md - Task categorization exists
- Follow-up TODOs: None
-->

# Graphiti FastMCP Server Constitution

## Core Principles

### I. Non-Interactive Authentication

Authentication MUST be non-interactive. No browser popups, no OAuth redirects, no human intervention
required during authentication flows. All authentication must work programmatically to support
automated systems, CI/CD pipelines, and non-interactive clients like Claude Code's MCP client.

**Rationale**: Browser-based OAuth flows are fragile, break automation, and create poor developer
experience. Service-to-service authentication must be reliable and deterministic.

### II. Bearer Token Simplicity

Authentication MUST use Bearer-style API keys (`Authorization: Bearer <token>`) or JWTs. These tokens
must work reliably from Claude Code's MCP client, FastMCP clients, and any HTTP client. No custom
authentication schemes that require special client implementation.

**Rationale**: Standard HTTP bearer authentication is universally supported, well-understood, and
works across all HTTP clients without special SDKs or libraries.

### III. Tool-Level Authorization

Authorization MUST be enforceable at the tool level using Eunomia MCP middleware or equivalent
policy-based systems. All MCP tools (add_memory, search_nodes, etc.) must be filterable via
`tools/list` and blockable via `tools/call` based on user roles and permissions defined in
declarative policies.

**Rationale**: Fine-grained authorization enables role-based access control (admin, readonly,
analyst) and prevents unauthorized access to sensitive operations like graph deletion or unrestricted
memory writes.

### IV. Environment-Based Configuration

The solution MUST be deployable to FastMCP Cloud using environment variables exclusively. No code
changes per environment, no hardcoded secrets, no configuration files that differ between dev/staging/
prod. All API keys, tokens, policy references, and configuration must be externalized.

**Rationale**: 12-factor app principles ensure security (secrets not in code), portability (same
codebase across environments), and FastMCP Cloud compatibility (env vars set in Cloud UI).

### V. Future-Proof Design

The architecture MUST support future migration to RemoteOAuth providers (Scalekit, WorkOS AuthKit)
without breaking existing clients. Current bearer token implementation must be extensible to JWT
validation, and eventually to full OAuth 2.1 with Dynamic Client Registration if business requirements
evolve.

**Rationale**: Starting simple (API keys) while designing for extensibility prevents architecture
lock-in and enables graduated security maturity as requirements grow.

### VI. Development Mode Toggle

Authentication MAY be disabled in isolated development environments via a single environment variable
(`GRAPHITI_AUTH_ENABLED=false`) but MUST remain enabled in all shared, deployed, or CI/CD environments.
Disabling authentication MUST require explicit opt-in and MUST log a warning on server startup.

**Rationale**: Development friction is real, but security-by-default prevents accidental exposure.
A single toggle provides escape hatch for local iteration while ensuring production safety through
conscious choice.

### VII. Observability & Structured Logging

Authentication and authorization MUST emit structured logs including principal identity, tool name,
request outcome, and correlation ID. Logs MUST NOT leak secrets (full API keys, tokens) or sensitive
request payloads. Failed authentication attempts MUST log truncated key identifiers for forensic
analysis.

**Rationale**: Security without observability is security theater. Structured logs enable incident
response, compliance audits, and performance debugging while protecting credential confidentiality.

## Technical Constraints

### Technologies in Scope

- **Server**: FastMCP 2.13.1+ with HTTP/SSE transport on FastMCP Cloud
- **Authentication**: Bearer tokens, JWTVerifier, Starlette BaseHTTPMiddleware, future RemoteOAuth
- **Authorization**: Eunomia MCP middleware for policy-based access control
- **Client**: Claude Code MCP client connecting over HTTP with bearer token
- **Tools**: 9 Graphiti MCP tools (add_memory, search_nodes, search_memory_facts, delete_entity_edge,
  delete_episode, get_entity_edge, get_episodes, clear_graph, get_status)

### Non-Goals

- No UI-based login flows or web authentication pages
- No full OAuth 2.1 authorization server implementation (use external providers if needed)
- No complex IAM hierarchies or nested role structures (keep flat: admin/readonly/analyst roles)

### Architecture Requirements

- **Factory Pattern**: Use `src/server.py:create_server()` factory function for FastMCP Cloud
  entrypoint (NOT global state pattern in `src/graphiti_mcp_server.py`)
- **Middleware Registration**: Authentication and authorization via `mcp.add_middleware()` in factory
- **Service Closures**: Tools access services (GraphitiService, QueueService) via closure, not globals
- **Health Exemptions**: `/health` and `/status` endpoints MUST bypass authentication
- **Request Context**: User principal/role attached to `request.state.api_principal` for tool access

## Governance

### Amendment Procedure

1. Propose constitution change with rationale and impact analysis
2. Update all dependent templates (plan-template.md, spec-template.md, tasks-template.md)
3. Increment version per semantic versioning (MAJOR/MINOR/PATCH rules)
4. Update Sync Impact Report in HTML comment at file top
5. Verify no placeholders remain (except explicitly TODOed items)

### Versioning Policy

- **MAJOR** (X.0.0): Backward-incompatible principle removals or redefinitions
- **MINOR** (x.Y.0): New principle added or materially expanded guidance
- **PATCH** (x.y.Z): Clarifications, wording, typo fixes, non-semantic refinements

### Compliance Review

- All PRs/reviews MUST verify compliance with Core Principles
- Complexity violations MUST be justified in plan.md Complexity Tracking table
- Architecture decisions MUST reference constitution principles (e.g., "Per Principle II...")
- Any auth/config pattern deviating from principles requires amendment proposal

**Version**: 1.1.0 | **Ratified**: 2025-12-01 | **Last Amended**: 2025-12-01
