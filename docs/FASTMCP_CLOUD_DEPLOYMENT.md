# FastMCP Cloud Deployment Guide

This guide covers deploying the Graphiti MCP server to FastMCP Cloud, a managed hosting platform for MCP servers.

## Overview

FastMCP Cloud is a managed platform that:
- Automatically builds and deploys your MCP server from GitHub
- Provides a unique HTTPS URL for your server
- Handles SSL certificates and authentication
- Auto-redeploys on pushes to `main` branch
- Creates preview deployments for pull requests

**Important:** FastMCP Cloud is currently **free while in beta**.

## Prerequisites

Before deploying to FastMCP Cloud, you need:

1. **GitHub Account** - FastMCP Cloud integrates with GitHub repos
2. **FalkorDB Cloud Instance** - Production graph database
3. **API Keys** - OpenAI (required), Anthropic (optional)
4. **Verified Repo** - Run the verification script first

### Pre-Deployment Verification

Run the verification script to check your server is ready:

```bash
uv run python scripts/verify_fastmcp_cloud_readiness.py
```

This checks:
- ✓ Server is discoverable via `fastmcp inspect`
- ✓ Dependencies are properly declared in `pyproject.toml`
- ✓ Environment variables are documented
- ✓ No secrets are committed to git
- ✓ Server can be imported successfully
- ✓ Entrypoint format is correct

All checks should pass before deploying.

## Deployment Steps

### Step 0: Validate Your Server Locally with FastMCP Tools

**Before deploying to FastMCP Cloud, validate your server with BOTH static and runtime checks.**

#### Static Validation: `fastmcp inspect`

Checks that your server module can be imported and tools are registered:

```bash
uv run fastmcp inspect src/graphiti_mcp_server.py:mcp
```

**Expected successful output:**

```
Name: Graphiti Agent Memory
Version: <version>
Tools: 9 found
  - add_memory: Add an episode to memory
  - search_nodes: Search for nodes in the graph memory
  - search_memory_facts: Search the graph memory for relevant facts
  - get_episodes: Get episodes from the graph memory
  - get_entity_edge: Get an entity edge from the graph memory by its UUID
  - delete_episode: Delete an episode from the graph memory
  - delete_entity_edge: Delete an entity edge from the graph memory
  - clear_graph: Clear all data from the graph for specified group IDs
  - get_status: Get the status of the Graphiti MCP server
```

**Generate JSON report:**

```bash
# FastMCP-specific format
uv run fastmcp inspect src/graphiti_mcp_server.py:mcp --format fastmcp -o inspect.json

# MCP protocol format
uv run fastmcp inspect src/graphiti_mcp_server.py:mcp --format mcp -o inspect-mcp.json
```

#### Runtime Validation: `fastmcp dev` (ESSENTIAL!)

**The `inspect` command only checks imports - it does NOT catch runtime initialization issues.**

Run the interactive inspector to test actual server initialization:

```bash
uv run fastmcp dev src/graphiti_mcp_server.py:mcp
```

This starts your server and opens an interactive web UI at `http://localhost:6274`.

**Critical test in the web UI:**

1. Open `http://localhost:6274` in your browser
2. Click the "get_status" tool
3. Click "Execute"
4. **Expected:** `{"status": "ok", "message": "Graphiti MCP server is running and connected to FalkorDB database"}`
5. **If you see:** `{"status": "error", "message": "Graphiti service not initialized"}` → **DO NOT DEPLOY**

This error means your server initialization is broken and deployment will fail silently.

**Common issues caught by each tool:**

| Tool | Catches | Example |
|------|---------|---------|
| `fastmcp inspect` | Import errors, missing dependencies, invalid entrypoint | `ModuleNotFoundError`, `mcp` object not found |
| `fastmcp dev` | Runtime initialization issues, database connection failures, missing env vars | "Graphiti service not initialized", connection refused |

**Troubleshooting runtime failures:**

| Issue | Symptom in `fastmcp dev` | Fix |
|-------|---------|-----|
| Missing dependencies | Import errors in terminal | Run `uv sync` |
| Database not running | Connection refused errors | Start FalkorDB/Neo4j (see [CLAUDE.md:86](../CLAUDE.md#L86)) |
| Missing environment variables | API key errors, config errors | Check `.env` file exists and has required keys |
| Service initialization failure | `get_status` returns "not initialized" | Check logs in terminal for root cause |

**If EITHER validation fails, do NOT proceed with deployment until errors are fixed.**

### Step 1: Prepare Your Repository

1. **Ensure `pyproject.toml` is complete**

   FastMCP Cloud automatically detects dependencies from `pyproject.toml`:
   ```toml
   [project]
   dependencies = [
       "fastmcp>=2.13.0",
       "graphiti-core==0.24.1",
       "falkordb>=4.2.6",
       "pydantic>=2.0.0",
       "pydantic-settings>=2.0.0",
       "pyyaml>=6.0.0",
       # ... other dependencies
   ]
   ```

2. **Verify `.env` is in `.gitignore`**

   ```bash
   # Check that .env is ignored
   git check-ignore -v .env

   # Should output something like:
   # .gitignore:42:.env    .env
   ```

3. **Commit and push your code**

   ```bash
   git add .
   git commit -m "Prepare for FastMCP Cloud deployment"
   git push origin main
   ```

### Step 2: Create FastMCP Cloud Project

1. **Visit [fastmcp.cloud](https://fastmcp.cloud)**

2. **Sign in with your GitHub account**

3. **Create a new project:**
   - Click "Create Project"
   - Select your `graphiti-fastmcp` repository
   - Repository can be public or private

4. **Configure project settings:**

   | Setting | Value | Notes |
   |---------|-------|-------|
   | **Name** | `graphiti-mcp` | Used in your deployment URL |
   | **Entrypoint** | `src/graphiti_mcp_server.py:mcp` | Points to module-level server instance |
   | **Authentication** | ✓ Enabled | Recommended for production |

   **Important:** The entrypoint must point to a **module-level** `FastMCP` instance, not one created inside `if __name__ == "__main__"`.

### Step 3: Configure Environment Variables

Set these environment variables in the FastMCP Cloud UI (**NOT** in `.env` files):

#### Required Variables

```bash
# LLM Provider (required)
OPENAI_API_KEY=sk-...

# FalkorDB Cloud Connection (required)
FALKORDB_URI=redis://your-instance.falkordb.cloud:port
FALKORDB_DATABASE=default_db
FALKORDB_USER=your_cloud_username
FALKORDB_PASSWORD=your_cloud_password
```

#### Optional Variables

```bash
# Additional LLM providers
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...
GROQ_API_KEY=...

# Performance tuning
SEMAPHORE_LIMIT=10  # Concurrent episode processing (adjust based on API tier)

# Azure OpenAI (alternative to OpenAI)
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-10-21
```

**Security Note:** Environment variables set in FastMCP Cloud UI are encrypted at rest and never logged.

### Step 4: Deploy

1. **Click "Deploy"**

   FastMCP Cloud will:
   1. Clone your repository
   2. Detect dependencies from `pyproject.toml`
   3. Install dependencies using `uv`
   4. Build your FastMCP server
   5. Deploy to a unique URL
   6. Make it immediately available

2. **Monitor the build**

   Watch the build logs in the FastMCP Cloud UI. The build typically takes 2-5 minutes.

3. **Note your deployment URL**

   Your server will be accessible at:
   ```
   https://your-project-name.fastmcp.app/mcp
   ```

### Step 5: Verify Deployment

1. **Test with `fastmcp inspect`**

   ```bash
   fastmcp inspect https://your-project-name.fastmcp.app/mcp
   ```

   You should see your server info and 9 tools.

2. **Connect from Claude Desktop**

   FastMCP Cloud provides auto-generated configuration. Click "Connect to Claude Desktop" in the UI and copy the configuration.

3. **Test add_memory tool**

   Use Claude Desktop or the MCP client to test:
   ```
   Add a memory: "John prefers dark mode UI"
   ```

## Post-Deployment

### Automatic Redeployment

FastMCP Cloud automatically redeploys when you:

- **Push to `main` branch** - Production deployment updates
- **Open a pull request** - Preview deployment with unique URL

### Pull Request Previews

Each PR gets a unique preview URL:
```
https://your-project-name-pr-42.fastmcp.app/mcp
```

Test changes before merging to production.

### Monitoring

Monitor your deployment:

1. **Build Logs** - View in FastMCP Cloud UI
2. **FalkorDB Health** - Monitor memory usage with:
   ```bash
   uv run scripts/check_falkordb_health.py
   ```
3. **API Usage** - Check OpenAI/Anthropic dashboard for rate limits

## Troubleshooting

### Build Failures

**Issue:** Dependencies fail to install

```
Solution:
1. Verify pyproject.toml syntax
2. Check dependency versions are available on PyPI
3. Remove any local-only dependencies
```

**Issue:** Module import errors

```
Solution:
1. Ensure all imports use absolute paths
2. Check that config/ is a proper Python package
3. Verify __init__.py files exist
```

### Runtime Errors

**Issue:** "API key is not configured"

```
Solution:
1. Verify environment variables are set in FastMCP Cloud UI
2. Check variable names match exactly (case-sensitive)
3. Redeploy after adding environment variables
```

**Issue:** FalkorDB connection failures

```
Solution:
1. Verify FalkorDB Cloud credentials are correct
2. Check firewall rules allow FastMCP Cloud IPs
3. Test connection string format:
   redis://username:password@host:port
```

**Issue:** 429 Rate Limit Errors

```
Solution:
1. Lower SEMAPHORE_LIMIT based on your API tier
2. OpenAI Tier 1: SEMAPHORE_LIMIT=1-2
3. OpenAI Tier 2: SEMAPHORE_LIMIT=5-8
```

### Authentication Issues

**Issue:** "Unauthorized" when connecting

```
Solution:
1. If authentication is enabled, get token from FastMCP Cloud UI
2. Add token to your MCP client configuration
3. Or disable authentication in project settings (not recommended for production)
```

## Configuration Differences

### FastMCP Cloud vs Local Development

| Aspect | FastMCP Cloud | Local Development |
|--------|---------------|-------------------|
| **Entry point** | Module-level instance | `if __name__ == "__main__"` block can run |
| **Dependencies** | Auto-detected from `pyproject.toml` | Installed via `uv sync` |
| **Environment** | Set in Cloud UI | Loaded from `.env` file |
| **Transport** | Managed by platform | Configured via `mcp.run()` |
| **HTTPS** | Automatic | Manual setup |
| **Authentication** | Built-in OAuth | Configure manually |

### What Gets Ignored

FastMCP Cloud **ignores**:

- `if __name__ == "__main__"` blocks
- `.env` files (use Cloud UI instead)
- `fastmcp.json` config files (use Cloud UI)
- YAML config files (use environment variables)
- Docker configurations

FastMCP Cloud **uses**:

- Module-level `FastMCP` instance
- `pyproject.toml` or `requirements.txt`
- Environment variables from Cloud UI
- Code from your `main` branch

## Best Practices

### 1. Use Environment Variables

All configuration should use environment variables:

```python
# Good - FastMCP Cloud compatible
import os
api_key = os.environ.get('OPENAI_API_KEY')

# Bad - Won't work on FastMCP Cloud
api_key = 'sk-hardcoded-key'
```

### 2. Module-Level Server Instance

```python
# Good - FastMCP Cloud can discover this
from fastmcp import FastMCP
mcp = FastMCP("Graphiti Agent Memory")

if __name__ == "__main__":
    # This block is IGNORED by FastMCP Cloud
    mcp.run()
```

### 3. Document Required Variables

Keep `.env.example` updated:

```bash
# .env.example
# Set these in FastMCP Cloud UI, NOT in .env files

OPENAI_API_KEY=sk-...
FALKORDB_URI=redis://...
```

### 4. Test Locally First

Always test locally before deploying:

```bash
# Run verification script
uv run python scripts/verify_fastmcp_cloud_readiness.py

# Test local server
uv run src/graphiti_mcp_server.py
```

### 5. Monitor Resource Usage

- **FalkorDB free tier:** 100 MB limit
- **OpenAI rate limits:** Tier-dependent
- **SEMAPHORE_LIMIT:** Tune based on API tier

## Security Considerations

### Secrets Management

- ✅ **DO:** Set secrets in FastMCP Cloud UI
- ✅ **DO:** Add `.env` to `.gitignore`
- ✅ **DO:** Use `.env.example` for documentation
- ❌ **DON'T:** Commit `.env` files
- ❌ **DON'T:** Hardcode API keys
- ❌ **DON'T:** Store secrets in YAML configs

### Authentication

FastMCP Cloud provides built-in authentication:

- **Enabled:** Only org members can connect (recommended)
- **Disabled:** Public access (use for demos only)

Enable authentication for production deployments.

### Knowledge Graph Data

Remember:
- Episodes are stored in **plaintext** in FalkorDB
- Don't store PII, passwords, or sensitive data
- Treat graph data as public
- Use separate group_ids for isolation

## Alternative: Self-Hosted Deployment

If you prefer self-hosted deployment instead of FastMCP Cloud:

1. **Use Docker Compose:**
   ```bash
   docker compose -f docker/docker-compose.yml up
   ```

2. **Use `fastmcp.json` configuration:**
   ```json
   {
     "source": {
       "path": "src/graphiti_mcp_server.py",
       "entrypoint": "mcp"
     },
     "deployment": {
       "transport": "http",
       "host": "0.0.0.0",
       "port": 8000
     }
   }
   ```

3. **Deploy to:**
   - Cloud VMs (AWS EC2, Google Compute Engine, Azure VMs)
   - Container platforms (Cloud Run, ECS, ACI)
   - PaaS (Railway, Render, Fly.io)
   - Kubernetes clusters

See [HTTP Deployment](https://gofastmcp.com/deployment/http) in FastMCP docs for details.

## Resources

- **FastMCP Cloud:** [fastmcp.cloud](https://fastmcp.cloud)
- **FastMCP Docs:** [gofastmcp.com](https://gofastmcp.com)
- **FastMCP Discord:** [discord.com/invite/aGsSC3yDF4](https://discord.com/invite/aGsSC3yDF4)
- **Verification Script:** [`scripts/verify_fastmcp_cloud_readiness.py`](../scripts/verify_fastmcp_cloud_readiness.py)
- **FalkorDB Cloud:** [cloud.falkordb.com](https://cloud.falkordb.com)

## Summary Checklist

Before deploying to FastMCP Cloud:

- [ ] Run `uv run python scripts/verify_fastmcp_cloud_readiness.py`
- [ ] All checks pass
- [ ] FalkorDB Cloud instance is running
- [ ] API keys are ready (OpenAI required)
- [ ] Code is pushed to GitHub `main` branch
- [ ] `.env` is in `.gitignore`
- [ ] No secrets committed to repo

During deployment:

- [ ] Create project on fastmcp.cloud
- [ ] Configure entrypoint: `src/graphiti_mcp_server.py:mcp`
- [ ] Enable authentication
- [ ] Set all required environment variables in UI
- [ ] Deploy and monitor build logs

After deployment:

- [ ] Test with `fastmcp inspect <URL>`
- [ ] Connect from Claude Desktop
- [ ] Test add_memory and search tools
- [ ] Monitor FalkorDB memory usage
- [ ] Monitor API rate limits

You're now ready to deploy! 🚀
