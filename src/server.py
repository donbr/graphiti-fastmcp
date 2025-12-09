#!/usr/bin/env python3
"""
Graphiti MCP Server - Exposes Graphiti functionality through the Model Context Protocol (MCP)
"""

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Any

import fastmcp
from dotenv import load_dotenv
from fastmcp import FastMCP
from graphiti_core import Graphiti
from graphiti_core.edges import EntityEdge
from graphiti_core.nodes import EpisodeType, EpisodicNode
from graphiti_core.search.search_filters import SearchFilters
from graphiti_core.utils.maintenance.graph_data_operations import clear_data
from pydantic import BaseModel
from starlette.responses import JSONResponse

from config.schema import GraphitiConfig
from models.response_types import (
    EpisodeSearchResponse,
    ErrorResponse,
    FactSearchResponse,
    NodeResult,
    NodeSearchResponse,
    StatusResponse,
    SuccessResponse,
)
from services.factories import DatabaseDriverFactory, EmbedderFactory, LLMClientFactory
from services.queue_service import QueueService
from utils.formatting import format_fact_result

# Load .env file
mcp_server_dir = Path(__file__).parent.parent
env_file = mcp_server_dir / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

# Semaphore limit configuration
SEMAPHORE_LIMIT = int(os.getenv('SEMAPHORE_LIMIT', 10))

# Configure logging
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=DATE_FORMAT,
    stream=sys.stderr,
)

# Configure specific loggers
logging.getLogger('uvicorn').setLevel(logging.INFO)
logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
logging.getLogger('mcp.server.streamable_http_manager').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

# MCP server instructions
GRAPHITI_MCP_INSTRUCTIONS = """
Graphiti is a memory service for AI agents built on a knowledge graph. Graphiti performs well
with dynamic data such as user interactions, changing enterprise data, and external information.

Graphiti transforms information into a richly connected knowledge network. The system organizes data as episodes 
(content snippets), nodes (entities), and facts (relationships between entities).

Key capabilities:
1. Add episodes (text, messages, or JSON) to the knowledge graph with the add_memory tool
2. Search for nodes (entities) in the graph using natural language queries with search_nodes
3. Find relevant facts (relationships between entities) with search_facts
4. Retrieve specific entity edges or episodes by UUID
5. Manage the knowledge graph with tools like delete_episode, delete_entity_edge, and clear_graph
"""

# ------------------------------------------------------------------------------
# Service Definition
# ------------------------------------------------------------------------------


class GraphitiService:
    """Graphiti service using the unified configuration system."""

    def __init__(self, config: GraphitiConfig, semaphore_limit: int = 10):
        self.config = config
        self.semaphore_limit = semaphore_limit
        self.semaphore = asyncio.Semaphore(semaphore_limit)
        self.client: Graphiti | None = None
        self.entity_types = None

    async def initialize(self) -> None:
        """Initialize the Graphiti client with factory-created components."""
        try:
            llm_client = None
            embedder_client = None

            try:
                llm_client = LLMClientFactory.create(self.config.llm)
            except Exception as e:
                logger.warning(f'Failed to create LLM client: {e}')

            try:
                embedder_client = EmbedderFactory.create(self.config.embedder)
            except Exception as e:
                logger.warning(f'Failed to create embedder client: {e}')

            db_config = DatabaseDriverFactory.create_config(self.config.database)

            # Build custom entity types
            custom_types = None
            if self.config.graphiti.entity_types:
                custom_types = {}
                for entity_type in self.config.graphiti.entity_types:
                    entity_model = type(
                        entity_type.name,
                        (BaseModel,),
                        {'__doc__': entity_type.description},
                    )
                    custom_types[entity_type.name] = entity_model
            self.entity_types = custom_types

            # Initialize Graphiti client
            if self.config.database.provider.lower() == 'falkordb':
                from graphiti_core.driver.falkordb_driver import FalkorDriver

                falkor_driver = FalkorDriver(
                    host=db_config['host'],
                    port=db_config['port'],
                    username=db_config['username'],
                    password=db_config['password'],
                    database=db_config['database'],
                )
                self.client = Graphiti(
                    graph_driver=falkor_driver,
                    llm_client=llm_client,
                    embedder=embedder_client,
                    max_coroutines=self.semaphore_limit,
                )
            else:
                self.client = Graphiti(
                    uri=db_config['uri'],
                    user=db_config['user'],
                    password=db_config['password'],
                    llm_client=llm_client,
                    embedder=embedder_client,
                    max_coroutines=self.semaphore_limit,
                )

            await self.client.build_indices_and_constraints()
            logger.info('Successfully initialized Graphiti client')

        except Exception as e:
            logger.error(f'Failed to initialize Graphiti client: {e}')
            raise

    async def get_client(self) -> Graphiti:
        if self.client is None:
            await self.initialize()
        if self.client is None:
            raise RuntimeError('Failed to initialize Graphiti client')
        return self.client


# ------------------------------------------------------------------------------
# Factory Entrypoint
# ------------------------------------------------------------------------------


async def create_server() -> FastMCP:
    """Factory function that creates and initializes the MCP server.

    This is the entrypoint for FastMCP Cloud and `fastmcp dev`.
    Configuration comes from environment variables and config files only.
    """
    logger.info('Initializing Graphiti MCP server via factory pattern...')

    # 1. Load configuration
    # Note: Environment variables are already loaded at module level
    factory_config = GraphitiConfig()

    # 2. Initialize Services
    factory_graphiti_service = GraphitiService(factory_config, SEMAPHORE_LIMIT)
    factory_queue_service = QueueService()

    # Await initialization of the Graphiti service
    await factory_graphiti_service.initialize()

    # Initialize queue with the Graphiti client
    client = await factory_graphiti_service.get_client()
    await factory_queue_service.initialize(client)

    logger.info('Graphiti services initialized successfully via factory')

    # 3. Create Server Instance
    server = FastMCP(
        'Graphiti Agent Memory',
        instructions=GRAPHITI_MCP_INSTRUCTIONS,
    )

    # 4. Register Tools
    # We pass the initialized services into the registration function
    _register_tools(server, factory_config, factory_graphiti_service, factory_queue_service)

    # 5. Register Custom Routes
    @server.custom_route('/health', methods=['GET'])
    async def health_check(request):
        return JSONResponse({'status': 'healthy', 'service': 'graphiti-mcp'})

    @server.custom_route('/status', methods=['GET'])
    async def status_check(request):
        return JSONResponse({'status': 'ok', 'service': 'graphiti-mcp'})

    logger.info('FastMCP server created with factory pattern')
    return server


def _register_tools(
    server: FastMCP,
    cfg: GraphitiConfig,
    graphiti_svc: GraphitiService,
    queue_svc: QueueService,
) -> None:
    """Register all MCP tools using closure to capture service instances."""

    @server.tool()
    async def add_memory(
        name: str,
        episode_body: str,
        group_id: str | None = None,
        source: str = 'text',
        source_description: str = '',
        uuid: str | None = None,
    ) -> SuccessResponse | ErrorResponse:
        """Add an episode to memory."""
        try:
            effective_group_id = group_id or cfg.graphiti.group_id

            episode_type = EpisodeType.text
            if source:
                try:
                    episode_type = EpisodeType[source.lower()]
                except (KeyError, AttributeError):
                    logger.warning(f"Unknown source type '{source}', using 'text'")
                    episode_type = EpisodeType.text

            await queue_svc.add_episode(
                group_id=effective_group_id,
                name=name,
                content=episode_body,
                source_description=source_description,
                episode_type=episode_type,
                entity_types=graphiti_svc.entity_types,
                uuid=uuid or None,
            )

            return SuccessResponse(
                message=f"Episode '{name}' queued for processing in group '{effective_group_id}'"
            )
        except Exception as e:
            logger.error(f'Error queuing episode: {e}')
            return ErrorResponse(error=f'Error queuing episode: {str(e)}')

    @server.tool()
    async def search_nodes(
        query: str,
        group_ids: list[str] | None = None,
        max_nodes: int = 10,
        entity_types: list[str] | None = None,
    ) -> NodeSearchResponse | ErrorResponse:
        """Search for nodes in the graph memory."""
        try:
            client = await graphiti_svc.get_client()
            effective_group_ids = (
                group_ids
                if group_ids is not None
                else [cfg.graphiti.group_id]
                if cfg.graphiti.group_id
                else []
            )

            search_filters = SearchFilters(node_labels=entity_types)
            from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

            results = await client.search_(
                query=query,
                config=NODE_HYBRID_SEARCH_RRF,
                group_ids=effective_group_ids,
                search_filter=search_filters,
            )

            nodes = results.nodes[:max_nodes] if results.nodes else []
            if not nodes:
                return NodeSearchResponse(message='No relevant nodes found', nodes=[])

            node_results = []
            for node in nodes:
                attrs = node.attributes if hasattr(node, 'attributes') else {}
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
            logger.error(f'Error searching nodes: {e}')
            return ErrorResponse(error=f'Error searching nodes: {str(e)}')

    @server.tool()
    async def search_memory_facts(
        query: str,
        group_ids: list[str] | None = None,
        max_facts: int = 10,
        center_node_uuid: str | None = None,
    ) -> FactSearchResponse | ErrorResponse:
        """Search the graph memory for relevant facts."""
        try:
            if max_facts <= 0:
                return ErrorResponse(error='max_facts must be a positive integer')

            client = await graphiti_svc.get_client()
            effective_group_ids = (
                group_ids
                if group_ids is not None
                else [cfg.graphiti.group_id]
                if cfg.graphiti.group_id
                else []
            )

            relevant_edges = await client.search(
                group_ids=effective_group_ids,
                query=query,
                num_results=max_facts,
                center_node_uuid=center_node_uuid,
            )

            if not relevant_edges:
                return FactSearchResponse(message='No relevant facts found', facts=[])

            facts = [format_fact_result(edge) for edge in relevant_edges]
            return FactSearchResponse(message='Facts retrieved successfully', facts=facts)
        except Exception as e:
            logger.error(f'Error searching facts: {e}')
            return ErrorResponse(error=f'Error searching facts: {str(e)}')

    @server.tool()
    async def delete_entity_edge(uuid: str) -> SuccessResponse | ErrorResponse:
        """Delete an entity edge from the graph memory."""
        try:
            client = await graphiti_svc.get_client()
            entity_edge = await EntityEdge.get_by_uuid(client.driver, uuid)
            await entity_edge.delete(client.driver)
            return SuccessResponse(message=f'Entity edge with UUID {uuid} deleted successfully')
        except Exception as e:
            logger.error(f'Error deleting entity edge: {e}')
            return ErrorResponse(error=f'Error deleting entity edge: {str(e)}')

    @server.tool()
    async def delete_episode(uuid: str) -> SuccessResponse | ErrorResponse:
        """Delete an episode from the graph memory."""
        try:
            client = await graphiti_svc.get_client()
            episodic_node = await EpisodicNode.get_by_uuid(client.driver, uuid)
            await episodic_node.delete(client.driver)
            return SuccessResponse(message=f'Episode with UUID {uuid} deleted successfully')
        except Exception as e:
            logger.error(f'Error deleting episode: {e}')
            return ErrorResponse(error=f'Error deleting episode: {str(e)}')

    @server.tool()
    async def get_entity_edge(uuid: str) -> dict[str, Any] | ErrorResponse:
        """Get an entity edge from the graph memory by its UUID."""
        try:
            client = await graphiti_svc.get_client()
            entity_edge = await EntityEdge.get_by_uuid(client.driver, uuid)
            return format_fact_result(entity_edge)
        except Exception as e:
            logger.error(f'Error getting entity edge: {e}')
            return ErrorResponse(error=f'Error getting entity edge: {str(e)}')

    @server.tool()
    async def get_episodes(
        group_ids: list[str] | None = None,
        max_episodes: int = 10,
    ) -> EpisodeSearchResponse | ErrorResponse:
        """Get episodes from the graph memory."""
        try:
            client = await graphiti_svc.get_client()
            effective_group_ids = (
                group_ids
                if group_ids is not None
                else [cfg.graphiti.group_id]
                if cfg.graphiti.group_id
                else []
            )

            if effective_group_ids:
                episodes = await EpisodicNode.get_by_group_ids(
                    client.driver, effective_group_ids, limit=max_episodes
                )
            else:
                episodes = []

            if not episodes:
                return EpisodeSearchResponse(message='No episodes found', episodes=[])

            episode_results = []
            for episode in episodes:
                episode_dict = {
                    'uuid': episode.uuid,
                    'name': episode.name,
                    'content': episode.content,
                    'created_at': episode.created_at.isoformat() if episode.created_at else None,
                    'source': episode.source.value
                    if hasattr(episode.source, 'value')
                    else str(episode.source),
                    'source_description': episode.source_description,
                    'group_id': episode.group_id,
                }
                episode_results.append(episode_dict)

            return EpisodeSearchResponse(
                message='Episodes retrieved successfully', episodes=episode_results
            )
        except Exception as e:
            logger.error(f'Error getting episodes: {e}')
            return ErrorResponse(error=f'Error getting episodes: {str(e)}')

    @server.tool()
    async def clear_graph(group_ids: list[str] | None = None) -> SuccessResponse | ErrorResponse:
        """Clear all data from the graph for specified group IDs."""
        try:
            client = await graphiti_svc.get_client()
            effective_group_ids = (
                group_ids or [cfg.graphiti.group_id] if cfg.graphiti.group_id else []
            )

            if not effective_group_ids:
                return ErrorResponse(error='No group IDs specified for clearing')

            await clear_data(client.driver, group_ids=effective_group_ids)
            return SuccessResponse(
                message=f'Graph data cleared for group IDs: {", ".join(effective_group_ids)}'
            )
        except Exception as e:
            logger.error(f'Error clearing graph: {e}')
            return ErrorResponse(error=f'Error clearing graph: {str(e)}')

    @server.tool()
    async def get_status() -> StatusResponse:
        """Get the status of the Graphiti MCP server and database connection."""
        try:
            client = await graphiti_svc.get_client()
            # Test database connection
            async with client.driver.session() as session:
                result = await session.run('MATCH (n) RETURN count(n) as count')
                if result:
                    _ = [record async for record in result]

            provider_name = cfg.database.provider
            return StatusResponse(
                status='ok',
                message=f'Graphiti MCP server is running and connected to {provider_name} database',
            )
        except Exception as e:
            logger.error(f'Error checking database connection: {e}')
            return StatusResponse(
                status='error',
                message=f'Graphiti MCP server is running but database connection failed: {str(e)}',
            )


# ------------------------------------------------------------------------------
# Main Execution Block (Local Dev)
# ------------------------------------------------------------------------------


async def run_local():
    """Run the server locally using the factory pattern."""
    # 1. Create server via factory (same as Cloud)
    server = await create_server()

    # 2. Parse basic args for local overrides
    parser = argparse.ArgumentParser(description='Run Graphiti MCP server')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--transport', choices=['http', 'stdio'], default='http')

    # Allow unknown args (ignore Cloud/Legacy specific args)
    args, _ = parser.parse_known_args()

    # 3. Apply overrides
    if args.host:
        fastmcp.settings.host = args.host
    if args.port:
        fastmcp.settings.port = args.port

    logger.info(f'Starting MCP server with {args.transport} transport')

    if args.transport == 'stdio':
        await server.run_stdio_async()
    else:
        # Patch uvicorn logging just for local run
        for logger_name in ['uvicorn', 'uvicorn.error', 'uvicorn.access']:
            uvicorn_logger = logging.getLogger(logger_name)
            uvicorn_logger.handlers.clear()
            handler = logging.StreamHandler(sys.stderr)
            handler.setFormatter(logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT))
            uvicorn_logger.addHandler(handler)
            uvicorn_logger.propagate = False

        await server.run_http_async()


if __name__ == '__main__':
    try:
        asyncio.run(run_local())
    except KeyboardInterrupt:
        logger.info('Server shutting down...')
    except Exception as e:
        logger.error(f'Fatal error: {str(e)}')
        sys.exit(1)
