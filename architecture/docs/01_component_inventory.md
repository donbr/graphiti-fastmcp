# Component Inventory

## Overview

The Graphiti FastMCP codebase is a Python-based MCP (Model Context Protocol) server that exposes Graphiti knowledge graph functionality as MCP tools. The codebase is organized into a modular structure with clear separation between:

- **Core Server** (`src/graphiti_mcp_server.py`): MCP server implementation with tool endpoints
- **Configuration** (`src/config/`): YAML-based configuration with environment variable support
- **Models** (`src/models/`): Data models for entity types and response structures
- **Services** (`src/services/`): Business logic for client factories and queue management
- **Utils** (`src/utils/`): Formatting and utility functions
- **Examples** (`examples/`): Client usage examples and utility scripts
- **Tests** (`tests/`): Comprehensive test suite with integration and stress tests

The project uses FastMCP for the MCP server framework, Graphiti Core for knowledge graph operations, and supports multiple LLM providers (OpenAI, Azure OpenAI, Anthropic, Gemini, Groq) and database backends (FalkorDB, Neo4j).

## Public API

### Entry Points

#### Main Server Entry Point
- **File**: `main.py:22-26`
- **Function**: `main()`
- **Description**: Backwards-compatible wrapper that imports and runs the graphiti_mcp_server. Maintains compatibility with existing deployment scripts.
- **Usage**: `python main.py [args...]`

#### Core Server Entry Point
- **File**: `src/graphiti_mcp_server.py:954-967`
- **Function**: `main()`
- **Description**: Primary entry point that initializes and runs the MCP server with asyncio.
- **Usage**: Direct import or via main.py wrapper

### MCP Tools (Public API Surface)

All tools are exposed via the FastMCP framework and are the primary public API for clients.

#### Memory Management Tools

1. **add_memory**
   - **File**: `src/graphiti_mcp_server.py:323-407`
   - **Description**: Add an episode to memory (text, JSON, or message). Episodes are processed asynchronously via queue service.
   - **Parameters**:
     - `name` (str): Episode name
     - `episode_body` (str): Content (JSON string for structured data)
     - `group_id` (str, optional): Graph namespace
     - `source` (str): Type - 'text', 'json', or 'message'
     - `source_description` (str): Source description
     - `uuid` (str, optional): Episode UUID
   - **Returns**: `SuccessResponse | ErrorResponse`

2. **search_nodes**
   - **File**: `src/graphiti_mcp_server.py:409-487`
   - **Description**: Search for entity nodes in the knowledge graph using hybrid search.
   - **Parameters**:
     - `query` (str): Search query
     - `group_ids` (list[str], optional): Filter by group IDs
     - `max_nodes` (int): Maximum results (default: 10)
     - `entity_types` (list[str], optional): Filter by entity type labels
   - **Returns**: `NodeSearchResponse | ErrorResponse`

3. **search_memory_facts**
   - **File**: `src/graphiti_mcp_server.py:489-541`
   - **Description**: Search for facts (relationships between entities) in the knowledge graph.
   - **Parameters**:
     - `query` (str): Search query
     - `group_ids` (list[str], optional): Filter by group IDs
     - `max_facts` (int): Maximum results (default: 10)
     - `center_node_uuid` (str, optional): Center search around specific node
   - **Returns**: `FactSearchResponse | ErrorResponse`

4. **get_episodes**
   - **File**: `src/graphiti_mcp_server.py:622-688`
   - **Description**: Retrieve episodes from the knowledge graph by group ID.
   - **Parameters**:
     - `group_ids` (list[str], optional): Filter by group IDs
     - `max_episodes` (int): Maximum results (default: 10)
   - **Returns**: `EpisodeSearchResponse | ErrorResponse`

#### Entity and Edge Management Tools

5. **get_entity_edge**
   - **File**: `src/graphiti_mcp_server.py:595-620`
   - **Description**: Retrieve a specific entity edge (fact) by UUID.
   - **Parameters**:
     - `uuid` (str): Entity edge UUID
   - **Returns**: `dict[str, Any] | ErrorResponse`

6. **delete_entity_edge**
   - **File**: `src/graphiti_mcp_server.py:543-567`
   - **Description**: Delete an entity edge from the knowledge graph.
   - **Parameters**:
     - `uuid` (str): Entity edge UUID
   - **Returns**: `SuccessResponse | ErrorResponse`

7. **delete_episode**
   - **File**: `src/graphiti_mcp_server.py:569-593`
   - **Description**: Delete an episode (episodic node) from the knowledge graph.
   - **Parameters**:
     - `uuid` (str): Episode UUID
   - **Returns**: `SuccessResponse | ErrorResponse`

#### Graph Management Tools

8. **clear_graph**
   - **File**: `src/graphiti_mcp_server.py:690-723`
   - **Description**: Clear all data from the knowledge graph for specified group IDs.
   - **Parameters**:
     - `group_ids` (list[str], optional): Group IDs to clear
   - **Returns**: `SuccessResponse | ErrorResponse`

9. **get_status**
   - **File**: `src/graphiti_mcp_server.py:725-756`
   - **Description**: Check MCP server and database connection status.
   - **Returns**: `StatusResponse`

#### HTTP Endpoints

10. **health_check**
    - **File**: `src/graphiti_mcp_server.py:758-762`
    - **Route**: `/health` (GET)
    - **Description**: Health check endpoint for Docker and load balancers.
    - **Returns**: JSON response with status

### Configuration Classes (Public API)

All configuration classes are in `src/config/schema.py`.

1. **GraphitiConfig** (lines 230-293)
   - Main configuration class using Pydantic Settings
   - Supports YAML files, environment variables, and CLI overrides
   - Nested configuration for server, LLM, embedder, database, and graphiti-specific settings

2. **ServerConfig** (lines 76-85)
   - Transport type (http, stdio, sse)
   - Host and port settings

3. **LLMConfig** (lines 146-156)
   - Provider selection (openai, azure_openai, anthropic, gemini, groq)
   - Model name, temperature, max_tokens

4. **EmbedderConfig** (lines 167-174)
   - Provider selection (openai, azure_openai, gemini, voyage)
   - Model name, dimensions

5. **DatabaseConfig** (lines 202-207)
   - Provider selection (neo4j, falkordb)
   - Provider-specific configurations

6. **GraphitiAppConfig** (lines 216-228)
   - group_id: Graph namespace
   - user_id: User tracking
   - entity_types: Custom entity type definitions

### Response Type Models (Public API)

All response types are in `src/models/response_types.py`.

1. **ErrorResponse** (lines 8-9)
   - `error` (str): Error message

2. **SuccessResponse** (lines 12-13)
   - `message` (str): Success message

3. **NodeResult** (lines 16-24)
   - `uuid`, `name`, `labels`, `created_at`, `summary`, `group_id`, `attributes`

4. **NodeSearchResponse** (lines 26-28)
   - `message` (str)
   - `nodes` (list[NodeResult])

5. **FactSearchResponse** (lines 31-33)
   - `message` (str)
   - `facts` (list[dict[str, Any]])

6. **EpisodeSearchResponse** (lines 36-38)
   - `message` (str)
   - `episodes` (list[dict[str, Any]])

7. **StatusResponse** (lines 41-43)
   - `status` (str)
   - `message` (str)

## Internal Implementation

### Core Service Classes

#### GraphitiService
- **File**: `src/graphiti_mcp_server.py:162-321`
- **Description**: Manages Graphiti client lifecycle and initialization
- **Key Methods**:
  - `__init__(config, semaphore_limit)` (line 165): Initialize with configuration
  - `initialize()` (line 172): Create LLM, embedder, and database clients using factories
  - `get_client()` (line 314): Lazy initialization of Graphiti client
- **Responsibilities**: Client creation, entity type configuration, database driver initialization

### Service Factories

All factory classes are in `src/services/factories.py`.

1. **LLMClientFactory** (lines 100-251)
   - **Method**: `create(config: LLMConfig) -> LLMClient` (line 104)
   - **Description**: Creates LLM clients based on provider configuration
   - **Supported Providers**: OpenAI, Azure OpenAI, Anthropic, Gemini, Groq
   - **Special Handling**: Reasoning model detection for OpenAI (gpt-5, o1, o3 families)

2. **EmbedderFactory** (lines 253-361)
   - **Method**: `create(config: EmbedderConfig) -> EmbedderClient` (line 257)
   - **Description**: Creates embedder clients based on provider configuration
   - **Supported Providers**: OpenAI, Azure OpenAI, Gemini, Voyage

3. **DatabaseDriverFactory** (lines 363-440)
   - **Method**: `create_config(config: DatabaseConfig) -> dict` (line 371)
   - **Description**: Creates database configuration dictionaries
   - **Supported Providers**: Neo4j, FalkorDB
   - **Note**: Returns config dicts, not driver instances directly

### Queue Service

#### QueueService
- **File**: `src/services/queue_service.py:12-153`
- **Description**: Manages sequential episode processing queues by group_id to avoid race conditions
- **Key Methods**:
  - `initialize(graphiti_client)` (line 92): Initialize with Graphiti client
  - `add_episode(...)` (line 101): Queue episode for processing
  - `add_episode_task(group_id, process_func)` (line 24): Add processing task to queue
  - `_process_episode_queue(group_id)` (line 49): Long-lived worker that processes queue
  - `get_queue_size(group_id)` (line 82): Get current queue size
  - `is_worker_running(group_id)` (line 88): Check worker status
- **Internal State**:
  - `_episode_queues`: Dict of asyncio.Queue per group_id
  - `_queue_workers`: Dict tracking worker status per group_id
  - `_graphiti_client`: Shared Graphiti client instance

### Configuration Support Classes

#### YamlSettingsSource
- **File**: `src/config/schema.py:16-74`
- **Description**: Custom Pydantic settings source for YAML configuration
- **Key Methods**:
  - `__call__()` (line 64): Load and parse YAML configuration
  - `_expand_env_vars(value)` (line 23): Recursively expand environment variables with `${VAR}` or `${VAR:default}` syntax
- **Features**: Boolean conversion, None handling for empty env vars

### Utility Functions

#### Formatting Utilities
- **File**: `src/utils/formatting.py`

1. **format_node_result** (lines 9-29)
   - **Parameters**: `node: EntityNode`
   - **Returns**: `dict[str, Any]`
   - **Description**: Serialize EntityNode to dict, excluding embeddings

2. **format_fact_result** (lines 32-51)
   - **Parameters**: `edge: EntityEdge`
   - **Returns**: `dict[str, Any]`
   - **Description**: Serialize EntityEdge to dict, excluding embeddings

#### General Utilities
- **File**: `src/utils/utils.py`

1. **create_azure_credential_token_provider** (lines 6-28)
   - **Returns**: `Callable[[], str]`
   - **Description**: Create Azure AD token provider for managed identity authentication
   - **Requires**: azure-identity package

### Internal Helper Functions

#### Logging Configuration
- **Function**: `configure_uvicorn_logging()`
- **File**: `src/graphiti_mcp_server.py:99-109`
- **Description**: Configure uvicorn loggers to match application format

#### Server Initialization
- **Function**: `initialize_server()`
- **File**: `src/graphiti_mcp_server.py:764-908`
- **Description**: Parse CLI args, load config, initialize services, set up MCP server
- **Returns**: `ServerConfig`

#### MCP Server Runner
- **Function**: `run_mcp_server()`
- **File**: `src/graphiti_mcp_server.py:910-952`
- **Description**: Run MCP server with configured transport (stdio, sse, or http)

#### Validation Helper
- **Function**: `_validate_api_key(provider_name, api_key, logger)`
- **File**: `src/services/factories.py:76-98`
- **Description**: Validate API key presence and log provider initialization

### Provider Configuration Models

All provider configs are in `src/config/schema.py`.

- **OpenAIProviderConfig** (lines 87-93): api_key, api_url, organization_id
- **AzureOpenAIProviderConfig** (lines 95-103): api_key, api_url, api_version, deployment_name, use_azure_ad
- **AnthropicProviderConfig** (lines 105-111): api_key, api_url, max_retries
- **GeminiProviderConfig** (lines 113-119): api_key, project_id, location
- **GroqProviderConfig** (lines 121-126): api_key, api_url
- **VoyageProviderConfig** (lines 128-134): api_key, api_url, model
- **Neo4jProviderConfig** (lines 176-184): uri, username, password, database, use_parallel_runtime
- **FalkorDBProviderConfig** (lines 186-193): uri, username, password, database

### Entity Type Definitions

**File**: `src/models/entity_types.py`

These are example entity types with detailed extraction instructions:

1. **Requirement** (lines 6-32): Project requirements with project name and description
2. **Preference** (lines 34-43): User preferences (highest priority classification)
3. **Procedure** (lines 46-65): Step-by-step procedures and instructions
4. **Location** (lines 67-91): Physical or virtual places
5. **Event** (lines 93-115): Time-bound activities and occurrences
6. **Object** (lines 117-141): Physical items, tools, devices (last resort classification)
7. **Topic** (lines 143-167): Subjects and knowledge domains (last resort classification)
8. **Organization** (lines 169-190): Companies, institutions, formal groups
9. **Document** (lines 192-213): Information content in various forms

**ENTITY_TYPES Dictionary** (lines 215-225): Maps entity type names to Pydantic models

## Entry Points

### Primary Entry Point
- **File**: `main.py`
- **Function**: `main()` (line 23)
- **Usage**: `python main.py [--config CONFIG] [--transport {sse,stdio,http}] [--host HOST] [--port PORT] [OPTIONS]`
- **Description**: Wrapper around graphiti_mcp_server.main() for backwards compatibility

### Direct Server Entry Point
- **File**: `src/graphiti_mcp_server.py`
- **Function**: `main()` (line 954)
- **Usage**: Can be imported directly or run via main.py
- **Description**: Runs asyncio.run(run_mcp_server())

### Example Scripts

All example scripts are standalone CLI tools demonstrating MCP client usage:

1. **01_connect_and_discover.py** - Connect to MCP server and list available tools
2. **02_call_tools.py** - Call MCP tools (add_memory, search_nodes, search_facts)
3. **03_graphiti_memory.py** - Demonstrate memory/knowledge graph operations
4. **04_mcp_concepts.py** - Explain MCP concepts with examples
5. **export_graph.py** - Export graph episodes to JSON for backup
6. **import_graph.py** - Import graph episodes from JSON backup
7. **populate_meta_knowledge.py** - Populate meta-knowledge about Graphiti
8. **verify_meta_knowledge.py** - Verify meta-knowledge was correctly stored

### Test Entry Points

1. **run_tests.py** (line 342)
   - **File**: `tests/run_tests.py`
   - **Class**: `TestRunner`
   - **Usage**: `python run_tests.py {unit,integration,comprehensive,async,stress,smoke,all} [OPTIONS]`
   - **Description**: Orchestrates test execution with various configurations

## Module Dependency Summary

### Dependency Layers

```
Layer 1: External Dependencies
├── fastmcp (MCP server framework)
├── graphiti-core (Knowledge graph engine)
├── pydantic/pydantic-settings (Configuration and validation)
├── openai, anthropic, google-genai, groq (LLM providers)
└── neo4j, redis/falkordb (Database backends)

Layer 2: Configuration and Models
├── src/config/schema.py (Configuration classes)
└── src/models/ (Entity types, response types)

Layer 3: Services and Utilities
├── src/services/factories.py (Client factories)
├── src/services/queue_service.py (Episode queue management)
└── src/utils/ (Formatting, utilities)

Layer 4: Core Application
├── src/graphiti_mcp_server.py (MCP server with GraphitiService)
└── main.py (Entry point wrapper)

Layer 5: Client Examples
└── examples/ (MCP client usage examples)

Layer 6: Testing
└── tests/ (Test suite with conftest, test runner, integration tests)
```

### Key Dependencies

1. **Configuration System**:
   - `config/schema.py` defines all configuration classes
   - Uses Pydantic Settings with custom YAML source
   - Supports environment variables with `${VAR:default}` syntax
   - CLI overrides via `apply_cli_overrides()`

2. **Service Layer**:
   - `services/factories.py` creates LLM, embedder, and database clients
   - Depends on `config/schema.py` for configuration models
   - Conditional imports based on available providers

3. **Queue Service**:
   - `services/queue_service.py` manages async episode processing
   - Depends on Graphiti client from GraphitiService
   - Uses asyncio.Queue for sequential processing per group_id

4. **MCP Server**:
   - `graphiti_mcp_server.py` orchestrates all components
   - Depends on: config, models, services, utils
   - Creates FastMCP instance with tools
   - Initializes GraphitiService and QueueService

5. **Examples**:
   - All examples depend on `mcp` package (ClientSession, streamablehttp_client)
   - Independent of server code (client-only)
   - Use standard MCP protocol for communication

6. **Tests**:
   - `conftest.py` provides shared fixtures (config)
   - `run_tests.py` provides test orchestration
   - Individual test files depend on pytest, pytest-asyncio
   - Tests interact with server via MCP protocol or direct imports

### Cross-Module Relationships

- **Config → All**: Every module imports configuration classes
- **Models → Server/Utils**: Response types used by MCP tools, formatting uses entity types
- **Services → Server**: Factories and queue service used by GraphitiService
- **Utils → Server/Services**: Formatting for responses, Azure auth for factories
- **Examples → None**: Examples are independent clients
- **Tests → Server/Config**: Tests import server modules and config for fixtures

### Global State

The server maintains minimal global state:
- `config`: GraphitiConfig instance (line 114)
- `mcp`: FastMCP instance (line 148)
- `graphiti_service`: GraphitiService instance (line 154)
- `queue_service`: QueueService instance (line 155)
- `graphiti_client`: Graphiti client for backward compatibility (line 158)
- `semaphore`: asyncio.Semaphore for concurrency control (line 159)

All global state is initialized in `initialize_server()` before the server starts.

## Package Structure

```
graphiti-fastmcp/
├── main.py                          # Entry point wrapper
├── src/                             # Main source code
│   ├── __init__.py
│   ├── graphiti_mcp_server.py       # Core MCP server
│   ├── config/                      # Configuration system
│   │   ├── __init__.py
│   │   └── schema.py
│   ├── models/                      # Data models
│   │   ├── __init__.py
│   │   ├── entity_types.py
│   │   └── response_types.py
│   ├── services/                    # Business logic
│   │   ├── __init__.py
│   │   ├── factories.py
│   │   └── queue_service.py
│   └── utils/                       # Utilities
│       ├── __init__.py
│       ├── formatting.py
│       └── utils.py
├── examples/                        # Client examples
│   ├── 01_connect_and_discover.py
│   ├── 02_call_tools.py
│   ├── 03_graphiti_memory.py
│   ├── 04_mcp_concepts.py
│   ├── export_graph.py
│   ├── import_graph.py
│   ├── populate_meta_knowledge.py
│   └── verify_meta_knowledge.py
└── tests/                           # Test suite
    ├── __init__.py
    ├── conftest.py
    ├── run_tests.py
    ├── test_async_operations.py
    ├── test_comprehensive_integration.py
    ├── test_configuration.py
    ├── test_falkordb_integration.py
    ├── test_fixtures.py
    ├── test_http_integration.py
    ├── test_integration.py
    ├── test_mcp_integration.py
    ├── test_mcp_transports.py
    ├── test_stdio_simple.py
    └── test_stress_load.py
```

## Key Architectural Patterns

1. **Factory Pattern**: LLMClientFactory, EmbedderFactory, DatabaseDriverFactory create provider-specific clients
2. **Service Pattern**: GraphitiService encapsulates Graphiti client lifecycle
3. **Queue Pattern**: QueueService manages sequential async processing per group_id
4. **Settings Pattern**: GraphitiConfig uses Pydantic Settings with custom YAML source
5. **Decorator Pattern**: FastMCP @tool() decorators expose functions as MCP tools
6. **Context Manager Pattern**: Examples use async with for MCP client sessions
7. **Singleton Pattern**: Global service instances initialized once at startup

## Configuration Flow

1. CLI args parsed in `initialize_server()` (line 768)
2. YAML config loaded via `YamlSettingsSource` with env var expansion
3. Environment variables override YAML values
4. CLI args override environment variables via `apply_cli_overrides()`
5. Final config passed to GraphitiService and factories
6. Providers created dynamically based on config.provider field

## Data Flow

### Episode Addition
1. Client calls `add_memory` tool
2. MCP tool validates and converts parameters
3. Episode queued via `queue_service.add_episode()`
4. Queue worker calls `graphiti_client.add_episode()`
5. Graphiti Core extracts entities and relationships
6. Data persisted to database (FalkorDB or Neo4j)
7. Success response returned immediately (async processing)

### Search Operations
1. Client calls `search_nodes` or `search_memory_facts`
2. MCP tool creates SearchFilters and search config
3. Graphiti client performs hybrid search (vector + keyword)
4. Results formatted via `format_node_result()` or `format_fact_result()`
5. Embeddings excluded from response
6. Response returned as NodeSearchResponse or FactSearchResponse
