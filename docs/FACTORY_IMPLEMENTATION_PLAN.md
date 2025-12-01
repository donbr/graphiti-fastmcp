# Factory Pattern Implementation Plan

## Overview

This document outlines the concrete code changes needed to implement Option 2 (Factory Pattern) from the Revised Deployment Strategy.

## Implementation Strategy

Given the complexity of refactoring 9 tool functions, I recommend a **hybrid approach**:

1. Keep the current module-level `mcp` instance (for backward compat with local development)
2. Add `create_server()` factory that creates a NEW instance with all tools
3. Test factory with inspector
4. Once validated, optionally deprecate the module-level instance

This approach:
- ✅ Minimizes risk (both paths work during transition)
- ✅ Allows incremental testing
- ✅ Preserves existing local dev workflow
- ✅ Provides clean Cloud entrypoint

## Code Changes

### Change 1: Add Factory Function

**Location**: After `GraphitiService` class (around line 320)

**Code to add**:

```python
async def create_server() -> FastMCP:
    """Factory function that creates and initializes the MCP server.

    This is the recommended entrypoint for FastMCP Cloud and `fastmcp dev`.
    Configuration comes from environment variables and config files only (no CLI args).

    Returns:
        Fully-initialized FastMCP server instance

    Usage:
        # FastMCP Cloud entrypoint: src/graphiti_mcp_server.py:create_server
        # Local testing: uv run fastmcp dev src/graphiti_mcp_server.py:create_server
    """
    logger.info('Initializing Graphiti MCP server via factory pattern...')

    # Load config from environment (no CLI args in Cloud)
    factory_config = GraphitiConfig()

    # Initialize services
    factory_graphiti_service = GraphitiService(factory_config, SEMAPHORE_LIMIT)
    factory_queue_service = QueueService()
    await factory_graphiti_service.initialize()

    factory_graphiti_client = await factory_graphiti_service.get_client()
    await factory_queue_service.initialize(factory_graphiti_client)

    logger.info('Graphiti services initialized successfully via factory')

    # Create server instance
    server = FastMCP(
        'Graphiti Agent Memory',
        instructions=GRAPHITI_MCP_INSTRUCTIONS,
    )

    # Register all tools with closure over factory services
    _register_tools(
        server,
        factory_config,
        factory_graphiti_service,
        factory_queue_service,
    )

    # Register custom routes
    @server.custom_route('/health', methods=['GET'])
    async def health_check(request):
        return JSONResponse({'status': 'healthy', 'service': 'graphiti-mcp'})

    logger.info('FastMCP server created with factory pattern')
    return server


def _register_tools(
    server: FastMCP,
    cfg: GraphitiConfig,
    graphiti_svc: GraphitiService,
    queue_svc: QueueService,
) -> None:
    """Register all MCP tools on the server instance.

    Uses closure pattern to capture service instances without global state.

    Args:
        server: FastMCP server instance to register tools on
        cfg: Configuration instance
        graphiti_svc: Initialized GraphitiService instance
        queue_svc: Initialized QueueService instance
    """

    @server.tool()
    async def add_memory(
        name: str,
        episode_body: str,
        group_id: str | None = None,
        source: str = 'text',
        source_description: str = '',
        uuid: str | None = None,
    ) -> SuccessResponse | ErrorResponse:
        """Add an episode to memory. This is the primary way to add information to the graph.

        This function returns immediately and processes the episode addition in the background.
        Episodes for the same group_id are processed sequentially to avoid race conditions.

        Args:
            name (str): Name of the episode
            episode_body (str): The content of the episode to persist to memory. When source='json', this must be a
                               properly escaped JSON string, not a raw Python dictionary. The JSON data will be
                               automatically processed to extract entities and relationships.
            group_id (str, optional): A unique ID for this graph. If not provided, uses the default group_id from CLI
                                     or a generated one.
            source (str, optional): Source type, must be one of:
                                   - 'text': For plain text content (default)
                                   - 'json': For structured data
                                   - 'message': For conversation-style content
            source_description (str, optional): Description of the source
            uuid (str, optional): Optional UUID for the episode

        Examples:
            # Adding plain text content
            add_memory(
                name="Company News",
                episode_body="Acme Corp announced a new product line today.",
                source="text",
                source_description="news article",
                group_id="some_arbitrary_string"
            )

            # Adding structured JSON data
            # NOTE: episode_body should be a JSON string (standard JSON escaping)
            add_memory(
                name="Customer Profile",
                episode_body='{"company": {"name": "Acme Technologies"}, "products": [{"id": "P001", "name": "CloudSync"}, {"id": "P002", "name": "DataMiner"}]}',
                source="json",
                source_description="CRM data"
            )
        """
        try:
            # Use the provided group_id or fall back to the default from config
            effective_group_id = group_id or cfg.graphiti.group_id

            # Try to parse the source as an EpisodeType enum, with fallback to text
            episode_type = EpisodeType.text  # Default
            if source:
                try:
                    episode_type = EpisodeType[source.lower()]
                except (KeyError, AttributeError):
                    # If the source doesn't match any enum value, use text as default
                    logger.warning(f"Unknown source type '{source}', using 'text' as default")
                    episode_type = EpisodeType.text

            # Submit to queue service for async processing
            await queue_svc.add_episode(
                group_id=effective_group_id,
                name=name,
                content=episode_body,
                source_description=source_description,
                episode_type=episode_type,
                entity_types=graphiti_svc.entity_types,
                uuid=uuid or None,  # Ensure None is passed if uuid is None
            )

            return SuccessResponse(
                message=f"Episode '{name}' queued for processing in group '{effective_group_id}'"
            )
        except Exception as e:
            error_msg = str(e)
            logger.error(f'Error queuing episode: {error_msg}')
            return ErrorResponse(error=f'Error queuing episode: {error_msg}')

    @server.tool()
    async def search_nodes(
        query: str,
        group_ids: list[str] | None = None,
        max_nodes: int = 10,
        entity_types: list[str] | None = None,
    ) -> NodeSearchResponse | ErrorResponse:
        """Search for nodes in the graph memory.

        Args:
            query: The search query
            group_ids: Optional list of group IDs to filter results
            max_nodes: Maximum number of nodes to return (default: 10)
            entity_types: Optional list of entity type names to filter by
        """
        try:
            client = await graphiti_svc.get_client()

            # Use the provided group_ids or fall back to the default from config if none provided
            effective_group_ids = (
                group_ids
                if group_ids is not None
                else [cfg.graphiti.group_id]
                if cfg.graphiti.group_id
                else []
            )

            # Create search filters
            search_filters = SearchFilters(
                node_labels=entity_types,
            )

            # Use the search_ method with node search config
            from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

            results = await client.search_(
                query=query,
                config=NODE_HYBRID_SEARCH_RRF,
                group_ids=effective_group_ids,
                search_filter=search_filters,
            )

            # Extract nodes from results
            nodes = results.nodes[:max_nodes] if results.nodes else []

            if not nodes:
                return NodeSearchResponse(message='No relevant nodes found', nodes=[])

            # Format the results
            node_results = []
            for node in nodes:
                # Get attributes and ensure no embeddings are included
                attrs = node.attributes if hasattr(node, 'attributes') else {}
                # Remove any embedding keys that might be in attributes
                attrs = {k: v for k, v in attrs.items() if 'embedding' not in k.lower()}

                node_results.append(
                    NodeResult(
                        uuid=node.uuid,
                        name=node.name,
                        labels=node.labels if node.labels else [],
                        created_at=node.created_at.isoformat() if node.created_at else None,
                        summary=node.summary,
                        group_id=node.group_id,
                        attributes=attrs,
                    )
                )

            return NodeSearchResponse(message='Nodes retrieved successfully', nodes=node_results)
        except Exception as e:
            error_msg = str(e)
            logger.error(f'Error searching nodes: {error_msg}')
            return ErrorResponse(error=f'Error searching nodes: {error_msg}')

    # ... continue with remaining 7 tools (search_memory_facts, delete_entity_edge, etc.)
    # Each tool follows same pattern: reference cfg, graphiti_svc, queue_svc from closure
```

### Change 2: Update `__main__` Block (Optional for Local Dev)

**Location**: Around line 954

**Current**:
```python
def main():
    """Main function to run the Graphiti MCP server."""
    try:
        # Run everything in a single event loop
        asyncio.run(run_mcp_server())
    except KeyboardInterrupt:
        logger.info('Server shutting down...')
    except Exception as e:
        logger.error(f'Error initializing Graphiti MCP server: {str(e)}')
        raise


if __name__ == '__main__':
    main()
```

**Option A - Use Factory** (recommended):
```python
async def run_mcp_server_factory():
    """Run the MCP server using factory pattern."""
    # Get server from factory
    server = await create_server()

    # Parse CLI args for local dev overrides (host, port, transport)
    parser = argparse.ArgumentParser(description='Run Graphiti MCP server')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--transport', choices=['http', 'stdio'], default='http')
    args = parser.parse_args()

    # Apply CLI overrides
    if args.host:
        fastmcp.settings.host = args.host
    if args.port:
        fastmcp.settings.port = args.port

    # Run the server
    logger.info(f'Starting MCP server with {args.transport} transport on {args.host}:{args.port}')
    if args.transport == 'stdio':
        await server.run_stdio_async()
    else:
        await server.run_http_async(transport="http")


def main():
    """Main function to run the Graphiti MCP server."""
    try:
        asyncio.run(run_mcp_server_factory())
    except KeyboardInterrupt:
        logger.info('Server shutting down...')
    except Exception as e:
        logger.error(f'Error initializing Graphiti MCP server: {str(e)}')
        raise


if __name__ == '__main__':
    main()
```

**Option B - Keep Existing** (preserve current behavior):
```python
# No changes - keep using initialize_server() path for local dev
# Factory is only for Cloud/fastmcp dev
```

## Testing Plan

### Step 1: Test Factory Locally

```bash
# Test with fastmcp dev (simulates Cloud behavior)
uv run fastmcp dev src/graphiti_mcp_server.py:create_server

# In browser at http://localhost:6274:
# 1. Call get_status tool
# 2. Expected: {"status": "ok", "message": "...connected to FalkorDB..."}
# 3. Test add_memory, search_nodes to verify functionality
```

### Step 2: Test Module Import

```bash
# Verify factory can be imported without side effects
python -c "from src.graphiti_mcp_server import create_server; print('✓ Import successful')"
```

### Step 3: Deploy to FastMCP Cloud

1. Update entrypoint in Cloud UI: `src/graphiti_mcp_server.py:create_server`
2. Deploy
3. Verify with: `fastmcp inspect https://your-project.fastmcp.app/mcp`
4. Test `get_status` via Cloud endpoint

## Remaining Work

Due to the size of this refactor (9 tools), I recommend:

**Do you want me to:**

A. **Complete full implementation** (all 9 tools in `_register_tools()`)
   - Most thorough
   - Takes more time
   - Single PR with all changes

B. **Implement 2-3 tools as proof-of-concept**
   - Faster to test
   - You can verify pattern works
   - Then bulk-complete remaining tools

C. **Provide script to auto-generate tool registration code**
   - Fastest
   - Mechanical transformation
   - Review generated code before applying

Which approach do you prefer?
