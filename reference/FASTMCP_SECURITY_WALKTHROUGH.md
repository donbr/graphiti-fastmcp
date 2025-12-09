# FastMCP Cloud Authentication Walkthrough

This walkthrough demonstrates the complete process of deploying a FastMCP server with authentication and connecting it to Claude Code.

## Prerequisites

- GitHub account
- FastMCP Cloud account (sign up at https://fastmcp.cloud)
- Claude Code installed

## Step 1: Create Repository from Template

1. Navigate to the FastMCP Quickstart Template:
   ```
   https://github.com/PrefectHQ/fastmcp-quickstart-template
   ```

2. Click **"Use this template"** → **"Create a new repository"**

3. Configure the new repository:
   - Owner: Your GitHub account
   - Repository name: `claude-fastmcp-quickstart` (or similar)
   - Visibility: Public (for simplicity)

4. Click **"Create repository"**

**Result**: You now have a repository with a simple echo server (`echo.py`)

## Step 2: Deploy to FastMCP Cloud (No Auth Initially)

1. Go to [FastMCP Cloud](https://fastmcp.cloud) and sign in with GitHub

2. Click **"New Server"** → **"Hosted"**

3. Select your repository from the list (e.g., `donbr/claude-fastmcp-quickstart`)

4. Configure deployment:
   - **Server name**: `claude-fastmcp-quickstart` (must be unique)
   - **Entrypoint**: `echo.py`
   - **Authentication**: Toggle **OFF** (Open mode for initial testing)

5. Click **"Deploy Server"**

6. Wait for deployment to complete (usually 1-2 minutes)

**Result**: Server deployed at `https://claude-fastmcp-quickstart.fastmcp.app/mcp`

## Step 3: Test Without Authentication

Verify the server works using curl:

```bash
curl -X POST https://claude-fastmcp-quickstart.fastmcp.app/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

**Expected Response**:
```json
{"jsonrpc":"2.0","id":1,"result":{"tools":[{"name":"echo_tool","description":"Echo the input text",...}]}}
```

Test calling the tool:
```bash
curl -X POST https://claude-fastmcp-quickstart.fastmcp.app/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"echo_tool","arguments":{"text":"Hello from curl"}},"id":2}'
```

**Expected Response**:
```json
{"jsonrpc":"2.0","id":2,"result":{"content":[{"type":"text","text":"Hello from curl"}],...}}
```

## Step 4: Enable Authentication

1. In FastMCP Cloud, go to your server's **Configuration** → **Security** tab

2. Change **Authentication Mode** from "Open" to **"Private"**
   - Private: Requires OAuth or API key, org membership required

3. Click **"Save Changes"**

4. Click **"Redeploy"** (or wait for the notification with Redeploy button)

5. Wait for redeployment to complete

## Step 5: Verify Authentication is Required

Test without authentication (should fail):
```bash
curl -s -X POST https://claude-fastmcp-quickstart.fastmcp.app/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

**Expected Response**:
```json
{"error":"invalid_request","error_description":"Bearer token required"}
```

## Step 6: Create API Key

1. In FastMCP Cloud, click your **profile icon** (bottom left)

2. Select **"API Keys"**

3. Click **"Create API Key"**

4. Enter a descriptor: `Claude Code Access` (or similar)

5. Click **"Create"**

6. **IMPORTANT**: Copy the API key immediately!
   - Format: `fmcp_XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`
   - It won't be shown again!

## Step 7: Test With Authentication

```bash
curl -s -X POST https://claude-fastmcp-quickstart.fastmcp.app/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer fmcp_YOUR_API_KEY_HERE" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

**Expected Response**: Success with tools list

## Step 8: Configure Claude Code

Add the MCP server to Claude Code with authentication:

```bash
claude mcp add claude-fastmcp-quickstart https://claude-fastmcp-quickstart.fastmcp.app/mcp \
  --scope user \
  --transport http \
  -H "Authorization: Bearer fmcp_YOUR_API_KEY_HERE"
```

Verify the connection:
```bash
claude mcp list
```

**Expected Output**:
```
claude-fastmcp-quickstart: https://claude-fastmcp-quickstart.fastmcp.app/mcp (HTTP) - ✓ Connected
```

## Summary

| Step | Action | Result |
|------|--------|--------|
| 1 | Create repo from template | GitHub repository with echo.py |
| 2 | Deploy to FastMCP Cloud (Open) | Server accessible without auth |
| 3 | Test with curl (no auth) | Verify server works |
| 4 | Enable Private mode | Authentication required |
| 5 | Test without auth | Get "Bearer token required" error |
| 6 | Create API key | Get `fmcp_...` key |
| 7 | Test with auth | Verify auth works |
| 8 | Configure Claude Code | MCP server connected |

## Authentication Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Open** | No authentication | Testing, public demos |
| **Public** | OAuth required, any FastMCP user | Community servers |
| **Private** | OAuth or API key, org membership | Team/enterprise |

## Key Commands Reference

```bash
# Add MCP server with authentication
claude mcp add <name> <url> --transport http -H "Authorization: Bearer <key>"

# List configured servers
claude mcp list

# Remove a server
claude mcp remove <name>

# Test endpoint with curl
curl -X POST <url> \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -H "Authorization: Bearer <key>" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

## Troubleshooting

### "Bearer token required" error
- Ensure you're including the Authorization header
- Verify the API key is correct (starts with `fmcp_`)
- Check header format: `Authorization: Bearer <key>` (note the space)

### Connection timeout
- Verify server URL is correct
- Check deployment status in FastMCP Cloud
- Try redeploying the server

### "⚠ Needs authentication" in Claude Code
- Re-add the server with the correct API key
- Verify org membership if using Private mode

---

*This walkthrough was created using Claude Code with Playwright MCP for browser automation.*