# Graphiti MCP Quick Start

## Validating Your Local Server

Before deploying to FastMCP Cloud, validate your server with TWO commands:

### 1. Static Validation (Quick Check)

```bash
# Verify server structure and tool registration
uv run fastmcp inspect src/server.py:create_server
```

**Expected output:**
```
Name: Graphiti Agent Memory
Tools: 9 found
  - add_memory
  - search_nodes
  - search_memory_facts
  ... (etc)
```

This checks that the module can be imported and tools are registered.

### 2. Runtime Validation (Essential!)

```bash
# Run interactive inspector - tests actual initialization
uv run fastmcp dev src/server.py:create_server
```

This starts your server and opens an interactive web UI at `http://localhost:6274` where you can:
- Test `get_status` tool to verify initialization
- Call tools and see actual responses
- Catch runtime errors before deployment

**In the web UI, run:**
1. Click "get_status" tool
2. Expected: `{"status": "ok", "message": "Graphiti MCP server is running and connected to falkordb database"}`
3. If you see `"Graphiti service not initialized"`, fix initialization issues before deploying

**If validation fails:**
- Check dependencies: `uv sync`
- Verify database is running (see [CLAUDE.md:86](CLAUDE.md#L86))
- Check environment variables in `.env`
- Fix any import or connection errors
