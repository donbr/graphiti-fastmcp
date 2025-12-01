# Claude Code MCP Configuration Guide

This guide explains how to configure Claude Code to connect to the Graphiti MCP server with bearer token authentication.

## Quick Start

Add the following configuration to your `.claude.json` file (usually located in your home directory):

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

## Configuration Options

### Local Development (localhost)

For local development with the MCP server running on your machine:

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

**Environment Variables Required:**
- `GRAPHITI_API_KEY_ADMIN` - Your admin API key from the server's `.env` file

### FastMCP Cloud Deployment

For production deployment on FastMCP Cloud:

```json
{
  "mcpServers": {
    "graphiti-memory": {
      "url": "https://your-project-name.fastmcp.cloud/mcp/",
      "headers": {
        "Authorization": "Bearer ${GRAPHITI_API_KEY_ADMIN}"
      }
    }
  }
}
```

**Environment Variables Required:**
- `GRAPHITI_API_KEY_ADMIN` - Your admin API key configured in FastMCP Cloud environment

## Bearer Token Configuration

### Token Format

API keys follow the format: `sk_<env>_<random>`

Examples:
- `sk_admin_AbCdEf123...` (admin role)
- `sk_readonly_XyZ789...` (readonly role)
- `sk_analyst_MnOp456...` (analyst role)

### Using Environment Variables

Claude Code automatically expands `${VAR_NAME}` syntax in headers. Store your API keys as environment variables:

**Linux/macOS:**
```bash
export GRAPHITI_API_KEY_ADMIN="sk_admin_your_key_here"
export GRAPHITI_API_KEY_READONLY="sk_readonly_your_key_here"
export GRAPHITI_API_KEY_ANALYST="sk_analyst_your_key_here"
```

**Windows (PowerShell):**
```powershell
$env:GRAPHITI_API_KEY_ADMIN = "sk_admin_your_key_here"
$env:GRAPHITI_API_KEY_READONLY = "sk_readonly_your_key_here"
$env:GRAPHITI_API_KEY_ANALYST = "sk_analyst_your_key_here"
```

## Role-Based Access Control

Different API keys grant different levels of access:

### Admin Role
- **Full access** to all tools
- Can add, search, modify, and delete data
- Recommended for: development, administrative tasks

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

### Readonly Role
- **Read-only access** to search and retrieve data
- Can use: `search_nodes`, `search_memory_facts`, `get_episodes`, `get_entity_edge`, `get_status`
- Cannot modify or delete data
- Recommended for: read-only applications, reporting

```json
{
  "mcpServers": {
    "graphiti-memory": {
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Authorization": "Bearer ${GRAPHITI_API_KEY_READONLY}"
      }
    }
  }
}
```

### Analyst Role
- **Read and write access** for data analysis
- Can use readonly tools plus `add_memory`
- Cannot delete data
- Recommended for: data collection, analysis workflows

```json
{
  "mcpServers": {
    "graphiti-memory": {
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Authorization": "Bearer ${GRAPHITI_API_KEY_ANALYST}"
      }
    }
  }
}
```

## Switching Roles

To switch between roles, change the environment variable reference in `.claude.json`:

```json
{
  "mcpServers": {
    "graphiti-memory": {
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Authorization": "Bearer ${GRAPHITI_API_KEY_READONLY}"
      }
    }
  }
}
```

Then restart Claude Code to apply the new configuration.

## Testing Tool Access

### 1. List Available Tools

After connecting, use Claude Code to list available tools:

```
What tools are available from the graphiti-memory MCP server?
```

**Expected:** You should see tools appropriate for your role (e.g., 5 tools for readonly, 11 tools for admin).

### 2. Test Tool Calls

**With admin token:**
```
Call add_memory tool to add an episode with name "Test Episode" and episode_body "This is a test"
```
**Expected:** Success response

**With readonly token:**
```
Call add_memory tool to add an episode with name "Test Episode" and episode_body "This is a test"
```
**Expected:** 403 Forbidden error (tool not available for readonly role)

**With analyst token:**
```
Call add_memory tool to add an episode with name "Test Episode" and episode_body "This is a test"
```
**Expected:** Success response (analyst can add memories)

## Troubleshooting

### 401 Unauthorized Error

**Symptom:** "Missing Authorization header" or "Invalid or expired API key"

**Solutions:**
1. Verify the API key environment variable is set:
   ```bash
   echo $GRAPHITI_API_KEY_ADMIN
   ```
2. Check that the key matches the server's `.env` file
3. Ensure the `Bearer` prefix is included in the Authorization header
4. Restart Claude Code after setting environment variables

### 403 Forbidden Error

**Symptom:** "Tool not available for your role" or tool calls blocked

**Solutions:**
1. Verify you're using the correct role key (e.g., admin vs readonly)
2. Check the tool is available for your role in [docs/SECURITY.md](SECURITY.md)
3. Switch to an admin key if you need full access

### No Interactive Auth Prompts

**Expected Behavior:** Authentication is **non-interactive** - no browser popups or OAuth flows.

**Configuration:** Bearer tokens are passed via HTTP headers automatically by Claude Code.

**Verification:**
1. Set environment variable with your API key
2. Configure `.claude.json` with the correct URL and header
3. Restart Claude Code
4. Connection should succeed without any prompts

If you see interactive auth prompts, check:
- You're using the correct MCP server URL (should end in `/mcp/`)
- The Authorization header is correctly configured
- No OAuth/OIDC provider is misconfigured in the server

### Server Connection Failed

**Symptom:** "Cannot connect to MCP server"

**Solutions:**
1. Verify the server is running:
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status":"healthy","service":"graphiti-mcp"}`

2. Check the URL in `.claude.json` matches the server address
3. For local development, ensure port 8000 is not blocked
4. For FastMCP Cloud, verify the deployment is active

### Token Environment Variable Not Expanded

**Symptom:** Error about invalid token format or 401 with `${GRAPHITI_API_KEY_ADMIN}` literal

**Solutions:**
1. Ensure the environment variable is exported before starting Claude Code
2. Restart Claude Code after setting the variable
3. Verify variable syntax: `${VAR_NAME}` (no spaces)
4. Check your shell environment:
   ```bash
   env | grep GRAPHITI_API_KEY
   ```

## Security Best Practices

1. **Never commit API keys** to version control
2. **Use environment variables** for all API keys
3. **Rotate keys regularly** by generating new keys and updating both server and client
4. **Use least privilege** - assign readonly role unless write access is needed
5. **Monitor access logs** - check server logs for unauthorized access attempts

## Example Workflows

### Development Workflow

```json
{
  "mcpServers": {
    "graphiti-memory-local": {
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Authorization": "Bearer ${GRAPHITI_API_KEY_ADMIN}"
      }
    }
  }
}
```

Use admin key for full access during development.

### Production Read-Only Workflow

```json
{
  "mcpServers": {
    "graphiti-memory-prod": {
      "url": "https://graphiti-prod.fastmcp.cloud/mcp/",
      "headers": {
        "Authorization": "Bearer ${GRAPHITI_API_KEY_READONLY}"
      }
    }
  }
}
```

Use readonly key for production queries to prevent accidental modifications.

### Multi-Environment Configuration

```json
{
  "mcpServers": {
    "graphiti-dev": {
      "url": "http://localhost:8000/mcp/",
      "headers": {
        "Authorization": "Bearer ${GRAPHITI_API_KEY_ADMIN}"
      }
    },
    "graphiti-prod": {
      "url": "https://graphiti-prod.fastmcp.cloud/mcp/",
      "headers": {
        "Authorization": "Bearer ${GRAPHITI_API_KEY_READONLY}"
      }
    }
  }
}
```

Configure multiple servers with different access levels.

## Next Steps

- Review [SECURITY.md](SECURITY.md) for API key management best practices
- See [FASTMCP_CLOUD_DEPLOYMENT.md](FASTMCP_CLOUD_DEPLOYMENT.md) for production deployment
- Check [README.md](../README.md) for general server setup
