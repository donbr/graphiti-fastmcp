# Revised Deployment Strategy

## Executive Summary

**Core Issue**: Graphiti MCP server initialization only happens in `if __name__ == "__main__"` block, which FastMCP Cloud (and `fastmcp dev`) completely ignores when importing the module entrypoint.

**Root Cause**: Per [FastMCP CLI documentation](https://github.com/jlowin/fastmcp/blob/main/docs/patterns/cli.mdx):
> "It is important to note a critical behavior when using `fastmcp run` with a local file: it completely disregards the `if __name__ == "__main__"` block."

**Impact**: `graphiti_service` remains `None` → all tools fail with "Graphiti service not initialized" error.

**Solution**: Two options presented below - both move initialization out of `__main__` into paths that execute on module import.

---

## Technical Corrections to Previous Analysis

### What Was Wrong

1. **`@mcp.lifespan()` decorator does not exist** in FastMCP
   - **Correct APIs**: `lifespan=` parameter on `FastMCP()` constructor, or `@mcp.on_startup` decorator

2. **`fastmcp inspect` is not "import-only"**
   - It instantiates the server via entrypoint resolution (including factories)
   - It's "static" in that it doesn't run the server, but it does execute initialization code

3. **Inspector is already working correctly**
   - "Graphiti service not initialized" error in `fastmcp dev` proves inspector catches the bug
   - Problem isn't that inspector fails to test Cloud behavior; it's that initialization is broken for both

### What Was Right

✅ Root cause diagnosis (initialization only in `__main__`)
✅ Inspector-first validation approach
✅ Factory pattern recommendation (grounded in FastMCP docs)
✅ Database connectivity check needed
✅ Parsimony improvements (remove SSE/stdio from Cloud docs)

---

## Two Implementation Options

Both options fix the initialization bug. Choose based on your preferences for code organization.

### Option 1: Lifespan Context Manager (Minimal Changes)

**How it works**: FastMCP's `lifespan=` parameter accepts an async context manager that runs on server startup/shutdown.

**Changes required**:

1. **Add lifespan function** after line 152 in [src/graphiti_mcp_server.py](../src/graphiti_mcp_server.py):

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def app_lifespan(app):
    """Initialize services when FastMCP server starts."""
    global config, graphiti_service, queue_service, graphiti_client, semaphore

    # Load config from environment (no CLI args in Cloud)
    config = GraphitiConfig()

    # Initialize services
    graphiti_service = GraphitiService(config, SEMAPHORE_LIMIT)
    queue_service = QueueService()
    await graphiti_service.initialize()

    graphiti_client = await graphiti_service.get_client()
    semaphore = graphiti_service.semaphore
    await queue_service.initialize(graphiti_client)

    logger.info('FastMCP module-level initialization complete')

    yield  # Server runs here

    # Shutdown logic (if needed)
    logger.info('FastMCP server shutting down')

# Update line 148-151:
mcp = FastMCP(
    'Graphiti Agent Memory',
    instructions=GRAPHITI_MCP_INSTRUCTIONS,
    lifespan=app_lifespan,  # Add this
)
```

2. **Limitation**: Cannot use CLI arguments in Cloud (no `argparse` support)
   - Remove or make optional: `--group-id`, `--model`, `--database-provider`, etc.
   - All config must come from environment variables or config file

3. **Keep `__main__` block** for local development with CLI args

**Pros**:
- Minimal code changes
- Tool registration (`@mcp.tool()`) stays exactly as-is
- Local development flow unchanged

**Cons**:
- CLI arguments won't work in Cloud deployment
- Lifespan function can't access CLI args parsed later
- Mixing two initialization paths (lifespan for Cloud, `main()` for local)

---

### Option 2: Factory Function (FastMCP Recommended Pattern)

**How it works**: FastMCP entrypoint `server.py:create_server` calls an async factory function that returns a fully-initialized `FastMCP` instance.

**Changes required**:

1. **Create factory function** (replace module-level `mcp = FastMCP(...)`):

```python
# Remove lines 148-151 (mcp = FastMCP(...))

async def create_server() -> FastMCP:
    """Factory function that creates and initializes the MCP server.

    This is called by FastMCP Cloud and `fastmcp dev` to instantiate the server.
    Configuration comes from environment variables and config files only.
    """
    global config, graphiti_service, queue_service, graphiti_client, semaphore

    # Load config from environment
    config = GraphitiConfig()

    # Initialize services
    graphiti_service = GraphitiService(config, SEMAPHORE_LIMIT)
    queue_service = QueueService()
    await graphiti_service.initialize()

    graphiti_client = await graphiti_service.get_client()
    semaphore = graphiti_service.semaphore
    await queue_service.initialize(graphiti_client)

    logger.info('Graphiti services initialized via factory')

    # Create server instance
    mcp = FastMCP(
        'Graphiti Agent Memory',
        instructions=GRAPHITI_MCP_INSTRUCTIONS,
    )

    # Register all tools
    _register_tools(mcp)

    # Register custom routes
    @mcp.custom_route('/health', methods=['GET'])
    async def health_check(request):
        return JSONResponse({'status': 'healthy', 'service': 'graphiti-mcp'})

    return mcp


def _register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools on the server instance.

    Moved from module-level decorators to allow factory pattern.
    """

    @mcp.tool()
    async def add_memory(
        name: str,
        episode_body: str,
        group_id: str | None = None,
        source: str = 'text',
        source_description: str = '',
        uuid: str | None = None,
    ) -> SuccessResponse | ErrorResponse:
        """Add an episode to memory..."""
        # Implementation stays the same
        ...

    @mcp.tool()
    async def search_nodes(...):
        """Search for nodes..."""
        ...

    # ... all other tools
```

2. **Update entrypoint** in FastMCP Cloud UI:
   - Change from: `src/graphiti_mcp_server.py:mcp`
   - Change to: `src/graphiti_mcp_server.py:create_server`

3. **Update `__main__` block** to use factory:

```python
async def run_mcp_server():
    """Run the MCP server in the current event loop."""
    # Get server from factory
    server = await create_server()

    # Apply any CLI-specific overrides (host, port, transport)
    # Parse args here if needed for local dev

    # Run the server
    await server.run_http_async(transport="http")


if __name__ == '__main__':
    asyncio.run(run_mcp_server())
```

**Pros**:
- Single initialization path for both Cloud and local dev
- Explicit dependency injection (factory creates everything)
- Easier to test (can call factory in tests)
- Recommended pattern per FastMCP docs

**Cons**:
- Requires refactoring tool registration
- More code changes
- Tool decorators can't be at module level

---

## Recommendation: **Option 2 (Factory Pattern)**

**Why**:
1. **Aligns with FastMCP best practices** - Factory pattern is explicitly recommended for servers requiring initialization
2. **Single initialization path** - Cloud and local dev use identical logic
3. **Inspector validates correctly** - `fastmcp dev src/graphiti_mcp_server.py:create_server` tests exact Cloud behavior
4. **Testability** - Factory can be called in unit tests without side effects
5. **No CLI args in Cloud anyway** - Option 1's attempt to preserve CLI args doesn't help Cloud deployment

**Migration Path**:
1. Implement `create_server()` factory
2. Move tool registration into `_register_tools()` helper
3. Update `__main__` block to call factory
4. Test with `fastmcp dev src/graphiti_mcp_server.py:create_server`
5. Verify `get_status` returns "ok" in inspector
6. Deploy to Cloud with new entrypoint

---

## Updated Validation Checklist

### Pre-Deployment (Local)

**Static validation**:
```bash
uv run fastmcp inspect src/graphiti_mcp_server.py:create_server
```
Expected: 9 tools found, no import errors

**Runtime validation** (CRITICAL):
```bash
uv run fastmcp dev src/graphiti_mcp_server.py:create_server
```
In web UI at http://localhost:6274:
1. Call `get_status` tool
2. Expected: `{"status": "ok", "message": "...connected to FalkorDB..."}`
3. If "Graphiti service not initialized" → **DO NOT DEPLOY**

**Database connectivity**:
```bash
uv run python scripts/verify_fastmcp_cloud_readiness.py
```
Should include actual DB connection test (see below)

### Post-Deployment (Cloud)

```bash
# Test deployed server
fastmcp inspect https://your-project.fastmcp.app/mcp

# Smoke test
curl https://your-project.fastmcp.app/health
# Expected: {"status": "healthy", "service": "graphiti-mcp"}
```

---

## Required Script Updates

### 1. Database Connectivity Check

Add to `scripts/verify_fastmcp_cloud_readiness.py`:

```python
def check_database_connectivity() -> bool:
    """Test actual connection to configured database."""
    print_header('5. Database Connectivity Check')

    try:
        # Import config and factories
        from config.schema import GraphitiConfig
        from services.factories import DatabaseDriverFactory

        # Load config from environment
        config = GraphitiConfig()

        # Create driver using same factory as production
        db_config = DatabaseDriverFactory.create_config(config.database)

        if config.database.provider.lower() == 'falkordb':
            # Test FalkorDB connection
            import redis
            r = redis.Redis(
                host=db_config['host'],
                port=db_config['port'],
                username=db_config.get('username'),
                password=db_config.get('password'),
                decode_responses=True,
                socket_connect_timeout=5,
            )
            r.ping()
            print_success(f'✓ Connected to FalkorDB at {db_config["host"]}:{db_config["port"]}')

        elif config.database.provider.lower() == 'neo4j':
            # Test Neo4j connection
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(
                db_config['uri'],
                auth=(db_config['user'], db_config['password']),
            )
            with driver.session() as session:
                session.run('RETURN 1')
            driver.close()
            print_success(f'✓ Connected to Neo4j at {db_config["uri"]}')

        return True

    except ImportError as e:
        print_error(f'✗ Missing dependencies: {e}')
        print_info('Run: uv sync')
        return False

    except Exception as e:
        print_error(f'✗ Database connection failed: {e}')
        print_info('Check these:')
        print_info('  - Database is running (see CLAUDE.md:86)')
        print_info('  - Credentials in .env are correct')
        print_info('  - Network/firewall allows connection')
        return False
```

### 2. Simplify Verification Output

**Remove**:
- ANSI color code helpers (use plain print)
- SSE/stdio transport documentation (Cloud only uses HTTP)

**Merge**:
- `check_dependencies()` + `check_environment_variables()` → `check_requirements()`
- `check_server_startup()` + `check_server_discoverable()` → `check_server_import()`

**Result**: ~30% code reduction, same functionality

---

## Parsimony Improvements

### Documentation Simplification

**File**: `docs/FASTMCP_CLOUD_DEPLOYMENT.md`

**Remove** (not applicable to Cloud):
- SSE transport instructions
- stdio transport instructions
- CLI argument documentation (Cloud doesn't support CLI args)

**Keep** (Cloud-specific):
- HTTP transport only
- Environment variable configuration
- FastMCP Cloud UI setup
- Entrypoint format: `src/graphiti_mcp_server.py:create_server`

### Verification Script Simplification

**Current**: 6 separate check functions with 50+ lines of ANSI color helpers

**Simplified**: 4 check functions with plain print

```python
def check_requirements() -> bool:
    """Check dependencies AND environment variables."""
    # Merge: check_dependencies + check_environment_variables
    ...

def check_server_import() -> bool:
    """Check server can be imported AND tools discovered."""
    # Merge: check_server_startup + check_server_discoverable
    ...

def check_database_connectivity() -> bool:
    """Test actual database connection."""
    # New: actual connection test
    ...

def check_no_committed_secrets() -> bool:
    """Verify .env not in git."""
    # Keep as-is
    ...
```

---

## Testing the Fix

### Before Code Changes

```bash
# Current behavior (BROKEN)
uv run fastmcp dev src/graphiti_mcp_server.py:mcp

# In inspector: get_status returns:
# {"status": "error", "message": "Graphiti service not initialized"}
```

### After Implementing Factory Pattern

```bash
# New behavior (FIXED)
uv run fastmcp dev src/graphiti_mcp_server.py:create_server

# In inspector: get_status returns:
# {"status": "ok", "message": "Graphiti MCP server is running and connected to FalkorDB database"}
```

### Deployment Test

```bash
# Deploy to FastMCP Cloud with entrypoint:
# src/graphiti_mcp_server.py:create_server

# Verify deployed server:
fastmcp inspect https://your-project.fastmcp.app/mcp

# Expected output:
# Name: Graphiti Agent Memory
# Tools: 9 found
# Status: Healthy
```

---

## Implementation Timeline

**Immediate (Blocking Deployment)**:
1. ✅ Implement `create_server()` factory function
2. ✅ Move tool registration to `_register_tools()` helper
3. ✅ Update `__main__` block to use factory
4. ✅ Test with `fastmcp dev src/graphiti_mcp_server.py:create_server`
5. ✅ Verify `get_status` returns "ok"

**Before Next Deployment**:
6. ✅ Add database connectivity check to verification script
7. ✅ Update FastMCP Cloud entrypoint to `:create_server`
8. ✅ Test Cloud deployment
9. ✅ Verify post-deployment smoke tests pass

**Week 1 (Quality of Life)**:
10. ⚪ Simplify verification script (merge checks, remove colors)
11. ⚪ Remove SSE/stdio docs from Cloud deployment guide
12. ⚪ Update CLAUDE.md with factory pattern examples

**Nice to Have**:
13. ⚪ Post-deployment validation script
14. ⚪ Automated build log fetching (if FastMCP API available)
15. ⚪ Environment variable diff tool (local vs Cloud)

---

## Verdict: NEEDS CHANGES → GOOD ENOUGH

**Current Status**: ❌ **NOT READY FOR DEPLOYMENT**

**Blocking Issues**:
1. ❌ Module initialization broken (no factory/lifespan pattern)
2. ❌ No database connectivity validation
3. ❌ Inspector shows "service not initialized" error

**After Implementing Factory Pattern + DB Check**: ✅ **GOOD ENOUGH FOR PRODUCTION**

**Why it will be good enough**:
- ✅ Single initialization path (Cloud and local dev identical)
- ✅ Inspector validates actual Cloud behavior
- ✅ Database connectivity tested pre-deployment
- ✅ Clear stop-gates prevent bad deployments
- ✅ Follows FastMCP recommended patterns

---

## References

### FastMCP Documentation
- [CLI Entrypoints](https://github.com/jlowin/fastmcp/blob/main/docs/patterns/cli.mdx) - Factory pattern recommendation
- [FastMCP Cloud](https://gofastmcp.com/deployment/fastmcp-cloud) - Deployment guide
- [Running Servers](https://gofastmcp.com/deployment/running-server) - `__main__` block behavior
- [FastAPI Integration](https://gofastmcp.com/integrations/fastapi) - Lifespan examples

### MCP Protocol
- [Lifecycle Specification](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle) - Initialization handshake

### Project Documentation
- [CLAUDE.md](../CLAUDE.md) - Development guide
- [QUICKSTART.md](../QUICKSTART.md) - Validation workflow
- [DEPLOYMENT_STRATEGY.md](DEPLOYMENT_STRATEGY.md) - Original analysis (superseded by this doc)

---

## Next Steps

**For implementation assistance**:
1. Review both options above
2. Choose factory pattern (recommended) or lifespan approach
3. Request concrete code changes for selected approach
4. Test locally with inspector
5. Deploy to Cloud with updated entrypoint

**Questions to consider**:
- Do you need CLI arguments for local development? (affects option choice)
- Should tool registration be in separate module for reusability?
- Do you want to preserve backward compatibility with current `main()` entrypoint?
