# Component Inventory

## Overview

Graphiti-FastMCP is an MCP (Model Context Protocol) server that exposes Graphiti knowledge graph functionality through the MCP protocol. The codebase is structured as a Python application with a clean separation between configuration, models, services, and utilities. It provides a memory service for AI agents built on a knowledge graph, supporting multiple LLM providers (OpenAI, Azure OpenAI, Anthropic, Gemini, Groq), embedding providers (OpenAI, Azure OpenAI, Gemini, Voyage), and graph databases (Neo4j, FalkorDB).

**Core Architecture:**
- Entry point: `main.py` (wrapper) -> `src/graphiti_mcp_server.py` (main server)
- Configuration system: YAML-based with environment variable overrides
- Services layer: Factory pattern for LLM, embedder, and database clients
- Queue-based processing: Sequential episode processing per group_id
- MCP integration: FastMCP framework for tool exposure

## Public API

### Modules

| Module Path | Purpose | Lines |
|------------|---------|-------|
| `main.py` | Main entry point wrapper for backward compatibility | 27 |
| `src/graphiti_mcp_server.py` | Primary MCP server implementation with all tool handlers | 968 |
| `src/config/schema.py` | Configuration schema with Pydantic settings and YAML support | 293 |
| `src/models/entity_types.py` | Entity type definitions for knowledge graph extraction | 226 |
| `src/models/response_types.py` | TypedDict response types for MCP tools | 44 |
| `src/services/factories.py` | Factory classes for LLM, Embedder, and Database clients | 440 |
| `src/services/queue_service.py` | Queue service for sequential episode processing | 153 |
| `src/utils/formatting.py` | Formatting utilities for nodes and edges | 51 |
| `src/utils/utils.py` | Azure credential token provider utility | 28 |

### Classes

#### Core Service Classes

**GraphitiService** (`src/graphiti_mcp_server.py:162-321`)
- Purpose: Main service class managing Graphiti client lifecycle and initialization
- Key Methods:
  - `__init__(config, semaphore_limit)` (line 165): Initialize with configuration
  - `async initialize()` (line 172): Initialize Graphiti client with factory-created components
  - `async get_client()` (line 314): Get or initialize the Graphiti client
- Attributes:
  - `config`: GraphitiConfig instance
  - `client`: Graphiti client instance
  - `entity_types`: Custom entity types dictionary
  - `semaphore`: Asyncio semaphore for rate limiting

**QueueService** (`src/services/queue_service.py:12-153`)
- Purpose: Manages sequential episode processing queues by group_id
- Key Methods:
  - `async add_episode_task(group_id, process_func)` (line 24): Add episode processing task to queue
  - `async _process_episode_queue(group_id)` (line 49): Process episodes sequentially for a group
  - `async initialize(graphiti_client)` (line 92): Initialize with graphiti client
  - `async add_episode(...)` (line 101): Add episode for processing with full parameters
  - `get_queue_size(group_id)` (line 82): Get current queue size
  - `is_worker_running(group_id)` (line 88): Check worker status

#### Configuration Classes

**GraphitiConfig** (`src/config/schema.py:230-293`)
- Purpose: Main configuration class with YAML and environment support
- Key Methods:
  - `settings_customise_sources(...)` (line 249): Customize settings sources to include YAML
  - `apply_cli_overrides(args)` (line 264): Apply CLI argument overrides
- Attributes:
  - `server`: ServerConfig instance
  - `llm`: LLMConfig instance
  - `embedder`: EmbedderConfig instance
  - `database`: DatabaseConfig instance
  - `graphiti`: GraphitiAppConfig instance
  - `destroy_graph`: Boolean flag for clearing graph on startup

**ServerConfig** (`src/config/schema.py:76-85`)
- Purpose: Server configuration for transport and networking
- Attributes: `transport`, `host`, `port`

**LLMConfig** (`src/config/schema.py:146-156`)
- Purpose: LLM provider and model configuration
- Attributes: `provider`, `model`, `temperature`, `max_tokens`, `providers`

**EmbedderConfig** (`src/config/schema.py:167-174`)
- Purpose: Embedder provider and model configuration
- Attributes: `provider`, `model`, `dimensions`, `providers`

**DatabaseConfig** (`src/config/schema.py:202-207`)
- Purpose: Database provider configuration
- Attributes: `provider`, `providers`

**GraphitiAppConfig** (`src/config/schema.py:216-228`)
- Purpose: Graphiti-specific configuration
- Attributes: `group_id`, `episode_id_prefix`, `user_id`, `entity_types`

**EntityTypeConfig** (`src/config/schema.py:209-214`)
- Purpose: Configuration for custom entity types
- Attributes: `name`, `description`

#### Provider Configuration Classes

**OpenAIProviderConfig** (`src/config/schema.py:87-93`)
- Attributes: `api_key`, `api_url`, `organization_id`

**AzureOpenAIProviderConfig** (`src/config/schema.py:95-103`)
- Attributes: `api_key`, `api_url`, `api_version`, `deployment_name`, `use_azure_ad`

**AnthropicProviderConfig** (`src/config/schema.py:105-111`)
- Attributes: `api_key`, `api_url`, `max_retries`

**GeminiProviderConfig** (`src/config/schema.py:113-119`)
- Attributes: `api_key`, `project_id`, `location`

**GroqProviderConfig** (`src/config/schema.py:121-126`)
- Attributes: `api_key`, `api_url`

**VoyageProviderConfig** (`src/config/schema.py:128-134`)
- Attributes: `api_key`, `api_url`, `model`

**Neo4jProviderConfig** (`src/config/schema.py:176-184`)
- Attributes: `uri`, `username`, `password`, `database`, `use_parallel_runtime`

**FalkorDBProviderConfig** (`src/config/schema.py:186-193`)
- Attributes: `uri`, `username`, `password`, `database`

#### Factory Classes

**LLMClientFactory** (`src/services/factories.py:100-251`)
- Purpose: Factory for creating LLM clients based on configuration
- Key Methods:
  - `create(config)` (line 104): Create LLM client for configured provider (OpenAI, Azure OpenAI, Anthropic, Gemini, Groq)

**EmbedderFactory** (`src/services/factories.py:253-361`)
- Purpose: Factory for creating Embedder clients based on configuration
- Key Methods:
  - `create(config)` (line 257): Create Embedder client for configured provider (OpenAI, Azure OpenAI, Gemini, Voyage)

**DatabaseDriverFactory** (`src/services/factories.py:363-440`)
- Purpose: Factory for creating Database driver configurations
- Key Methods:
  - `create_config(config)` (line 371): Create database configuration dictionary (Neo4j, FalkorDB)

#### Entity Type Classes

**Requirement** (`src/models/entity_types.py:6-32`)
- Purpose: Represents project requirements or features
- Attributes: `project_name`, `description`

**Preference** (`src/models/entity_types.py:34-44`)
- Purpose: Represents user preferences, choices, or opinions (prioritized classification)
- Attributes: Inherits from BaseModel

**Procedure** (`src/models/entity_types.py:46-65`)
- Purpose: Represents action procedures or instructions
- Attributes: `description`

**Location** (`src/models/entity_types.py:67-91`)
- Purpose: Represents physical or virtual places
- Attributes: `name`, `description`

**Event** (`src/models/entity_types.py:93-115`)
- Purpose: Represents time-bound activities or occurrences
- Attributes: `name`, `description`

**Object** (`src/models/entity_types.py:117-141`)
- Purpose: Represents physical items, tools, or devices (last resort classification)
- Attributes: `name`, `description`

**Topic** (`src/models/entity_types.py:143-167`)
- Purpose: Represents subjects of conversation or knowledge domains (last resort classification)
- Attributes: `name`, `description`

**Organization** (`src/models/entity_types.py:169-190`)
- Purpose: Represents companies, institutions, or formal entities
- Attributes: `name`, `description`

**Document** (`src/models/entity_types.py:192-213`)
- Purpose: Represents information content in various forms
- Attributes: `title`, `description`

### Functions

#### MCP Tool Functions (Public API)

**add_memory** (`src/graphiti_mcp_server.py:324-407`)
- Purpose: Add an episode to memory (primary way to add information to graph)
- Parameters: `name`, `episode_body`, `group_id`, `source`, `source_description`, `uuid`
- Returns: `SuccessResponse | ErrorResponse`
- MCP Tool: @mcp.tool() decorator

**search_nodes** (`src/graphiti_mcp_server.py:410-487`)
- Purpose: Search for nodes (entities) in the graph memory
- Parameters: `query`, `group_ids`, `max_nodes`, `entity_types`
- Returns: `NodeSearchResponse | ErrorResponse`
- MCP Tool: @mcp.tool() decorator

**search_memory_facts** (`src/graphiti_mcp_server.py:490-541`)
- Purpose: Search for relevant facts (relationships) in the graph
- Parameters: `query`, `group_ids`, `max_facts`, `center_node_uuid`
- Returns: `FactSearchResponse | ErrorResponse`
- MCP Tool: @mcp.tool() decorator

**delete_entity_edge** (`src/graphiti_mcp_server.py:544-567`)
- Purpose: Delete an entity edge from the graph memory
- Parameters: `uuid`
- Returns: `SuccessResponse | ErrorResponse`
- MCP Tool: @mcp.tool() decorator

**delete_episode** (`src/graphiti_mcp_server.py:570-593`)
- Purpose: Delete an episode from the graph memory
- Parameters: `uuid`
- Returns: `SuccessResponse | ErrorResponse`
- MCP Tool: @mcp.tool() decorator

**get_entity_edge** (`src/graphiti_mcp_server.py:596-620`)
- Purpose: Get an entity edge by UUID
- Parameters: `uuid`
- Returns: `dict[str, Any] | ErrorResponse`
- MCP Tool: @mcp.tool() decorator

**get_episodes** (`src/graphiti_mcp_server.py:623-688`)
- Purpose: Get episodes from the graph memory
- Parameters: `group_ids`, `max_episodes`
- Returns: `EpisodeSearchResponse | ErrorResponse`
- MCP Tool: @mcp.tool() decorator

**clear_graph** (`src/graphiti_mcp_server.py:691-723`)
- Purpose: Clear all data from the graph for specified group IDs
- Parameters: `group_ids`
- Returns: `SuccessResponse | ErrorResponse`
- MCP Tool: @mcp.tool() decorator

**get_status** (`src/graphiti_mcp_server.py:726-756`)
- Purpose: Get status of Graphiti MCP server and database connection
- Parameters: None
- Returns: `StatusResponse`
- MCP Tool: @mcp.tool() decorator

**health_check** (`src/graphiti_mcp_server.py:759-762`)
- Purpose: Health check endpoint for Docker and load balancers
- Parameters: `request`
- Returns: `JSONResponse`
- Route: @mcp.custom_route('/health', methods=['GET'])

#### Server Lifecycle Functions

**initialize_server** (`src/graphiti_mcp_server.py:764-908`)
- Purpose: Parse CLI arguments and initialize Graphiti server configuration
- Parameters: None (reads from sys.argv)
- Returns: `ServerConfig`
- Key Operations:
  - Parse command-line arguments
  - Load YAML configuration
  - Apply CLI overrides
  - Initialize GraphitiService and QueueService
  - Handle graph destruction if requested

**run_mcp_server** (`src/graphiti_mcp_server.py:910-952`)
- Purpose: Run the MCP server in the current event loop
- Parameters: None
- Returns: None
- Key Operations:
  - Initialize server
  - Start appropriate transport (stdio, sse, or http)

**main** (`src/graphiti_mcp_server.py:954-964`)
- Purpose: Main function to run the Graphiti MCP server
- Parameters: None
- Returns: None
- Entry Point: Yes (if __name__ == '__main__')

**main** (`main.py:23-26`)
- Purpose: Wrapper entry point for backward compatibility
- Parameters: None
- Returns: None
- Entry Point: Yes (if __name__ == '__main__')

#### Utility Functions

**format_node_result** (`src/utils/formatting.py:9-30`)
- Purpose: Format an entity node into a readable result dictionary
- Parameters: `node` (EntityNode)
- Returns: `dict[str, Any]`
- Note: Excludes embeddings to reduce payload size

**format_fact_result** (`src/utils/formatting.py:32-51`)
- Purpose: Format an entity edge into a readable result dictionary
- Parameters: `edge` (EntityEdge)
- Returns: `dict[str, Any]`
- Note: Excludes embeddings to reduce payload size

**create_azure_credential_token_provider** (`src/utils/utils.py:6-28`)
- Purpose: Create Azure credential token provider for managed identity authentication
- Parameters: None
- Returns: `Callable[[], str]`
- Note: Requires azure-identity package

## Internal Implementation

### Internal Modules

| Module Path | Purpose |
|------------|---------|
| `src/config/__init__.py` | Config package initialization (empty) |
| `src/models/__init__.py` | Models package initialization (empty) |
| `src/services/__init__.py` | Services package initialization (empty) |
| `src/utils/__init__.py` | Utils package initialization (empty) |
| `src/__init__.py` | Main package initialization (empty) |

### Helper Classes

**YamlSettingsSource** (`src/config/schema.py:16-74`)
- Purpose: Custom settings source for loading from YAML files with environment variable expansion
- Key Methods:
  - `_expand_env_vars(value)` (line 23): Recursively expand environment variables in configuration values
  - `get_field_value(field_name, field_info)` (line 60): Get field value from YAML config
  - `__call__()` (line 64): Load and parse YAML configuration
- Note: Supports ${VAR} and ${VAR:default} syntax for environment variables

**LLMProvidersConfig** (`src/config/schema.py:136-144`)
- Purpose: Container for all LLM provider configurations
- Attributes: `openai`, `azure_openai`, `anthropic`, `gemini`, `groq`

**EmbedderProvidersConfig** (`src/config/schema.py:158-165`)
- Purpose: Container for all embedder provider configurations
- Attributes: `openai`, `azure_openai`, `gemini`, `voyage`

**DatabaseProvidersConfig** (`src/config/schema.py:195-200`)
- Purpose: Container for all database provider configurations
- Attributes: `neo4j`, `falkordb`

### Utility Functions

**configure_uvicorn_logging** (`src/graphiti_mcp_server.py:99-109`)
- Purpose: Configure uvicorn loggers to match application's log format
- Parameters: None
- Returns: None
- Note: Internal helper for consistent logging

**_validate_api_key** (`src/services/factories.py:76-98`)
- Purpose: Validate API key is present for provider
- Parameters: `provider_name`, `api_key`, `logger`
- Returns: `str` (validated API key)
- Raises: ValueError if API key is None or empty

## Entry Points

### Main Entry Points

1. **Primary Entry Point**: `main.py`
   - Line 23-26: `main()` function
   - Imports and delegates to `src.graphiti_mcp_server.main()`
   - Purpose: Backward compatibility wrapper for existing deployment scripts

2. **Server Entry Point**: `src/graphiti_mcp_server.py`
   - Line 954-964: `main()` function
   - Line 966-967: `if __name__ == '__main__'` guard
   - Executes: `asyncio.run(run_mcp_server())`
   - Purpose: Main server initialization and execution

3. **Script Entry Points**:
   - `scripts/check_falkordb_health.py`: FalkorDB health check utility
   - `scripts/export_graph.py`: Graph export utility
   - `scripts/import_graph.py`: Graph import utility
   - `scripts/populate_meta_knowledge.py`: Meta knowledge population utility
   - `scripts/validate_qdrant.py`: Qdrant validation utility
   - `scripts/verify_meta_knowledge.py`: Meta knowledge verification utility

4. **Example Entry Points**:
   - `examples/01_connect_and_discover.py`: MCP connection example
   - `examples/02_call_tools.py`: Tool calling example
   - `examples/03_graphiti_memory.py`: Memory operations example
   - `examples/04_mcp_concepts.py`: MCP concepts example

### Package Interfaces

**Package: src**
- Location: `src/__init__.py`
- Exports: None (empty __init__.py)
- Note: Modules must be imported directly (e.g., `from src.graphiti_mcp_server import main`)

**Package: src.config**
- Location: `src/config/__init__.py`
- Exports: None (empty __init__.py)
- Direct imports required: `from config.schema import GraphitiConfig`

**Package: src.models**
- Location: `src/models/__init__.py`
- Exports: None (empty __init__.py)
- Direct imports required:
  - `from models.entity_types import ENTITY_TYPES, Requirement, Preference, etc.`
  - `from models.response_types import ErrorResponse, SuccessResponse, etc.`

**Package: src.services**
- Location: `src/services/__init__.py`
- Exports: None (empty __init__.py)
- Direct imports required:
  - `from services.factories import LLMClientFactory, EmbedderFactory, DatabaseDriverFactory`
  - `from services.queue_service import QueueService`

**Package: src.utils**
- Location: `src/utils/__init__.py`
- Exports: None (empty __init__.py)
- Direct imports required:
  - `from utils.formatting import format_node_result, format_fact_result`
  - `from utils.utils import create_azure_credential_token_provider`

### Global State and Constants

**MCP Server Instance** (`src/graphiti_mcp_server.py:148-151`)
- `mcp`: FastMCP instance with name 'Graphiti Agent Memory'
- Instructions: GRAPHITI_MCP_INSTRUCTIONS (lines 117-145)

**Global Services** (`src/graphiti_mcp_server.py:154-159`)
- `graphiti_service`: GraphitiService instance
- `queue_service`: QueueService instance
- `graphiti_client`: Graphiti client (backward compatibility)
- `semaphore`: Asyncio semaphore for concurrency control

**Constants**:
- `SEMAPHORE_LIMIT`: Concurrent operation limit (line 76, default: 10)
- `LOG_FORMAT`: Log message format (line 80)
- `DATE_FORMAT`: Log date format (line 81)

**Entity Types Dictionary** (`src/models/entity_types.py:215-225`)
- `ENTITY_TYPES`: Dictionary mapping entity type names to Pydantic models

## Summary Statistics

- **Total modules**: 9 main modules + 5 package __init__ files + 6 scripts + 4 examples = 24 total files
- **Total classes**: 30 classes
  - Core service classes: 2 (GraphitiService, QueueService)
  - Configuration classes: 18 (GraphitiConfig, ServerConfig, LLMConfig, etc.)
  - Factory classes: 3 (LLMClientFactory, EmbedderFactory, DatabaseDriverFactory)
  - Entity type classes: 9 (Requirement, Preference, Procedure, etc.)
  - Helper classes: 4 (YamlSettingsSource, LLMProvidersConfig, etc.)

- **Total functions**: 25 functions
  - MCP tool functions: 10 (add_memory, search_nodes, search_memory_facts, etc.)
  - Server lifecycle functions: 3 (initialize_server, run_mcp_server, main)
  - Utility functions: 4 (format_node_result, format_fact_result, etc.)
  - Internal helpers: 2 (configure_uvicorn_logging, _validate_api_key)
  - Factory methods: 3 (LLMClientFactory.create, EmbedderFactory.create, DatabaseDriverFactory.create_config)
  - Service methods: 6 (QueueService methods)

- **Public API items**:
  - 10 MCP tools (exposed via @mcp.tool() decorator)
  - 1 HTTP endpoint (/health)
  - 9 entity type classes (exported via ENTITY_TYPES dictionary)
  - 3 factory classes (public static methods)
  - Main configuration class (GraphitiConfig)

- **Internal items**:
  - 5 package __init__ files
  - 4 helper/container classes
  - 2 internal helper functions
  - 18 provider configuration classes

**Lines of Code by Module**:
- Main server: 968 lines
- Factories: 440 lines
- Configuration schema: 293 lines
- Entity types: 226 lines
- Queue service: 153 lines
- Formatting utilities: 51 lines
- Response types: 44 lines
- Utils: 28 lines
- Main wrapper: 27 lines

**Key Design Patterns**:
1. Factory Pattern: For creating LLM, Embedder, and Database clients
2. Service Pattern: GraphitiService and QueueService encapsulate business logic
3. Configuration as Code: YAML + Environment variables + CLI overrides
4. Async Queue Pattern: Sequential processing with asyncio.Queue
5. Decorator Pattern: MCP tools using @mcp.tool() decorator
6. Singleton Pattern: Global service instances (graphiti_service, queue_service)
