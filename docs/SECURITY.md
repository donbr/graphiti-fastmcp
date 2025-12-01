# Security Guide

This document describes the security features, API key management, and best practices for the Graphiti MCP server.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Authorization (Role-Based Access Control)](#authorization-role-based-access-control)
- [API Key Management](#api-key-management)
- [Role Descriptions](#role-descriptions)
- [Configuration](#configuration)
- [Security Best Practices](#security-best-practices)
- [Key Rotation](#key-rotation)
- [Audit Logging](#audit-logging)
- [Claude Code Configuration](#claude-code-configuration)

## Overview

The Graphiti MCP server implements a three-layer security model:

1. **Authentication** - Bearer token authentication using API keys
2. **Authorization** - Role-based access control (RBAC) using policy files
3. **Audit Logging** - Comprehensive logging of all authentication attempts and access decisions

All three security layers work together to provide secure, auditable access to the MCP server.

## Authentication

### Bearer Token Authentication

The server uses bearer token authentication with API keys. All requests (except `/health` and `/status`) must include an `Authorization` header:

```
Authorization: Bearer sk_admin_your_key_here
```

### API Key Format

API keys follow the format: `sk_<role>_<random>`

Examples:
- `sk_admin_AbCdEf123456...` (admin role)
- `sk_readonly_XyZ789...` (readonly role)
- `sk_analyst_MnOp456...` (analyst role)

### Generating API Keys

Use Python's `secrets` module to generate cryptographically secure keys:

```python
import secrets

# Generate a secure API key
key = f"sk_admin_{secrets.token_urlsafe(32)}"
print(key)
```

**Output example:**
```
sk_admin_OQlB4hDGrLafM7nI1QZWyFMA-02wh16wg8dYG64gbo0
```

### Configuration

Set API keys via environment variables:

```bash
# Admin key (full access)
export GRAPHITI_API_KEY_ADMIN="sk_admin_your_key_here"

# Readonly key (read-only access)
export GRAPHITI_API_KEY_READONLY="sk_readonly_your_key_here"

# Analyst key (read + write memory)
export GRAPHITI_API_KEY_ANALYST="sk_analyst_your_key_here"
```

### Disabling Authentication

For local development only, you can disable authentication:

```bash
export GRAPHITI_AUTH_ENABLED=false
```

**⚠️ WARNING:** Never disable authentication in production!

## Authorization (Role-Based Access Control)

### Policy File

Authorization policies are defined in `config/mcp_policies.json`:

```json
{
  "version": "1.0",
  "policies": [
    {
      "role": "admin",
      "resources": ["*"],
      "description": "Full access to all MCP tools"
    },
    {
      "role": "readonly",
      "resources": [
        "search_nodes",
        "search_memory_facts",
        "get_episodes",
        "get_entity_edge",
        "get_status"
      ],
      "description": "Read-only access"
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
      ],
      "description": "Read access plus add_memory"
    }
  ]
}
```

### Customizing Policies

1. Edit `config/mcp_policies.json`
2. Add/remove resources for each role
3. Restart the server (policy changes require restart)

**Note:** Policy hot-reload is not supported in v1. Changes require server restart.

## API Key Management

### Storage

**NEVER commit API keys to version control!**

✅ **DO:**
- Store keys in environment variables
- Use `.env` file (excluded from git)
- Store keys in secure key management systems (AWS Secrets Manager, HashiCorp Vault, etc.)
- Use FastMCP Cloud environment variable UI for production keys

❌ **DON'T:**
- Commit keys to git
- Share keys in plain text (Slack, email, etc.)
- Hardcode keys in source code
- Log full API keys

### Environment Setup

**Development (.env file):**
```bash
# .env file (never commit this!)
GRAPHITI_AUTH_ENABLED=true
GRAPHITI_API_KEY_ADMIN=sk_admin_generated_key_here
GRAPHITI_API_KEY_READONLY=sk_readonly_generated_key_here
GRAPHITI_API_KEY_ANALYST=sk_analyst_generated_key_here
```

**Production (FastMCP Cloud):**
1. Go to FastMCP Cloud dashboard
2. Navigate to your project's environment variables
3. Add each API key as a separate environment variable
4. Deploy

## Role Descriptions

### Admin Role
- **Access Level:** Full access to all tools
- **Use Cases:**
  - Development and debugging
  - Administrative tasks
  - System maintenance
  - Emergency operations
- **Tools:** All MCP tools (11 total)
- **Security Note:** Use sparingly, audit carefully

### Readonly Role
- **Access Level:** Read-only queries and retrieval
- **Use Cases:**
  - Reporting and analytics
  - Read-only applications
  - Public-facing queries
  - Audit and compliance tools
- **Tools:** 5 tools
  - `search_nodes` - Search for entity nodes
  - `search_memory_facts` - Search for relationships
  - `get_episodes` - Retrieve episodes
  - `get_entity_edge` - Get specific edge
  - `get_status` - Check server status
- **Security Note:** Cannot modify or delete data

### Analyst Role
- **Access Level:** Read access + ability to add memory
- **Use Cases:**
  - Data collection and ingestion
  - Research and analysis workflows
  - Content annotation
  - Knowledge base curation
- **Tools:** 6 tools (readonly + `add_memory`)
- **Security Note:** Can add data but cannot delete

## Configuration

### Server Configuration

Environment variables:

```bash
# Authentication
GRAPHITI_AUTH_ENABLED=true  # Enable/disable auth (default: true)

# API Keys
GRAPHITI_API_KEY_ADMIN=sk_admin_...
GRAPHITI_API_KEY_READONLY=sk_readonly_...
GRAPHITI_API_KEY_ANALYST=sk_analyst_...

# Authorization
EUNOMIA_POLICY_FILE=config/mcp_policies.json  # Policy file path
```

### Testing Configuration

```bash
# Generate test keys
python3 -c "import secrets; print(f'sk_admin_{secrets.token_urlsafe(32)}')"
python3 -c "import secrets; print(f'sk_readonly_{secrets.token_urlsafe(32)}')"
python3 -c "import secrets; print(f'sk_analyst_{secrets.token_urlsafe(32)}')"

# Test authentication
curl -H "Authorization: Bearer $GRAPHITI_API_KEY_ADMIN" \
  http://localhost:8000/mcp/

# Test health endpoint (no auth required)
curl http://localhost:8000/health
```

## Security Best Practices

### 1. API Key Security

- **Generate strong keys:** Use `secrets.token_urlsafe(32)` or longer
- **One key per role per environment:** Don't reuse keys across dev/staging/prod
- **Rotate keys regularly:** At least every 90 days
- **Monitor key usage:** Review audit logs for unusual access patterns
- **Revoke compromised keys immediately:** Generate new keys and update environment

### 2. Access Control

- **Principle of least privilege:** Use readonly or analyst roles whenever possible
- **Audit admin access:** Log and review all admin key usage
- **Separate keys by purpose:** Different keys for different applications
- **Document key ownership:** Maintain a registry of which keys are used where

### 3. Network Security

- **Use HTTPS in production:** FastMCP Cloud provides HTTPS automatically
- **Restrict network access:** Use firewalls/security groups to limit access
- **Never expose auth keys in URLs:** Always use Authorization headers
- **Monitor failed authentication attempts:** Set up alerts for repeated failures

### 4. Operational Security

- **Secure .env files:** Set file permissions to 600 (`chmod 600 .env`)
- **Use secret management:** AWS Secrets Manager, HashiCorp Vault, etc.
- **Backup policy files:** Version control `mcp_policies.json` (no secrets in this file)
- **Test security changes:** Verify authentication/authorization in staging first

### 5. Audit and Compliance

- **Enable audit logging:** Ensure logs are captured and retained
- **Regular security reviews:** Review access logs monthly
- **Incident response plan:** Document steps for key compromise
- **Compliance documentation:** Maintain records of access control changes

## Key Rotation

### Rotation Procedure

**1. Generate new keys:**
```bash
python3 -c "import secrets; print(f'sk_admin_{secrets.token_urlsafe(32)}')"
```

**2. Update server environment:**
```bash
# Update .env file or FastMCP Cloud environment variables
GRAPHITI_API_KEY_ADMIN=sk_admin_NEW_KEY_HERE
```

**3. Restart server:**
```bash
# Local
uv run src/server.py

# Docker
docker compose restart

# FastMCP Cloud
# (Automatic on environment variable change)
```

**4. Update clients:**
- Update all client configurations with new keys
- Test client connections
- Monitor logs for authentication failures

**5. Revoke old keys:**
- Remove old keys from environment
- Document the rotation in security log

### Rotation Schedule

- **Admin keys:** Every 90 days or after personnel changes
- **Analyst keys:** Every 180 days
- **Readonly keys:** Every 180 days
- **Compromised keys:** Immediately

## Audit Logging

### Log Format

All authentication attempts are logged:

**Successful authentication:**
```
2025-12-01 01:28:45 - middleware.auth - INFO - Authentication successful: user_id=admin, role=admin, path=/mcp/tools/call
```

**Failed authentication:**
```
2025-12-01 01:28:47 - middleware.auth - WARNING - Authentication failed: Invalid token=sk_admin_..., path=/mcp/tools/call
```

**Missing credentials:**
```
2025-12-01 01:28:49 - middleware.auth - WARNING - Authentication failed: Missing Authorization header, path=/mcp/tools/call
```

### Log Security

- **No full API keys in logs:** Only first 8 characters logged on failure
- **User ID tracking:** Every request logged with user_id and role
- **Path tracking:** Every request logged with endpoint path
- **Timestamp:** ISO 8601 format timestamps

### Log Monitoring

Monitor logs for:
- Repeated authentication failures (potential brute force)
- Unexpected role usage (admin access from unusual locations)
- Authorization failures (users attempting unauthorized operations)
- High-volume access patterns (potential abuse)

### Log Retention

- **Development:** 7 days minimum
- **Production:** 90 days minimum (or per compliance requirements)

## Claude Code Configuration

### Quick Setup

Add to `.claude.json` in your home directory:

```json
{
  "mcpServers": {
    "graphiti-memory": {
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Authorization": "Bearer ${GRAPHITI_API_KEY_ADMIN}"
      }
    }
  }
}
```

### Role-Based Client Configuration

**Admin access (development):**
```json
{
  "mcpServers": {
    "graphiti-dev": {
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Authorization": "Bearer ${GRAPHITI_API_KEY_ADMIN}"
      }
    }
  }
}
```

**Readonly access (production queries):**
```json
{
  "mcpServers": {
    "graphiti-prod-readonly": {
      "url": "https://graphiti.fastmcp.cloud/mcp/",
      "headers": {
        "Authorization": "Bearer ${GRAPHITI_API_KEY_READONLY}"
      }
    }
  }
}
```

**Analyst access (data collection):**
```json
{
  "mcpServers": {
    "graphiti-analyst": {
      "url": "https://graphiti.fastmcp.cloud/mcp/",
      "headers": {
        "Authorization": "Bearer ${GRAPHITI_API_KEY_ANALYST}"
      }
    }
  }
}
```

### Troubleshooting

See [CLAUDE_MCP_CONFIG.md](CLAUDE_MCP_CONFIG.md) for detailed Claude Code troubleshooting.

## Threat Model

### Threats Mitigated

✅ **Unauthorized access:** Bearer token authentication prevents unauthenticated access
✅ **Privilege escalation:** RBAC prevents users from accessing tools beyond their role
✅ **Data tampering:** Readonly role prevents accidental or malicious data modification
✅ **Audit trail:** Comprehensive logging enables incident investigation

### Threats NOT Mitigated (Out of Scope for v1)

⚠️ **Rate limiting:** No rate limiting on authentication attempts (add reverse proxy for this)
⚠️ **IP allowlisting:** No IP-based access control (use firewall/security groups)
⚠️ **OAuth/SSO:** No federated authentication (use API keys only)
⚠️ **Policy hot-reload:** Policy changes require server restart

## Compliance

### GDPR Considerations

- **Personal data:** API keys and user_ids may be considered personal data
- **Right to erasure:** Implement key revocation procedures
- **Data retention:** Configure log retention per GDPR requirements
- **Audit logging:** Maintain access logs for compliance

### SOC 2 Controls

- **Access control:** Role-based access control with audit logging
- **Authentication:** Secure API key authentication
- **Monitoring:** Comprehensive audit logs
- **Key management:** Documented key rotation procedures

## Support

For security issues or questions:

- **Security vulnerabilities:** Report via GitHub Security Advisories
- **General questions:** See [README.md](../README.md) or [CLAUDE.md](../CLAUDE.md)
- **Deployment:** See [FASTMCP_CLOUD_DEPLOYMENT.md](FASTMCP_CLOUD_DEPLOYMENT.md)
