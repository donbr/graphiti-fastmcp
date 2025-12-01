# Component Inventory

## Overview

This codebase is a **Graphiti MCP Server** implementation that exposes the Graphiti knowledge graph library through the Model Context Protocol (MCP). The architecture follows a factory pattern for dependency injection and uses FastMCP for server implementation.

**Key Architecture Patterns:**
- Factory pattern for creating LLM, embedder, and database clients
- Service-oriented architecture with dependency injection
- Asynchronous processing with queue-based episode handling
- Configuration-driven setup with YAML + environment variables
- MCP protocol implementation for tool exposure

**Technology Stack:**
- FastMCP (MCP server framework)
- Graphiti Core (knowledge graph library)
- Pydantic (data validation and settings)
- AsyncIO (asynchronous operations)
- Redis/FalkorDB or Neo4j (graph database backends)

---

## Public API

### Modules

#### `src/server.py` (Lines 1-504)
**Purpose:** FastMCP-based server implementation using factory pattern for deployment
- Primary entry point for FastMCP Cloud deployments
- Implements `create_server()` async factory function
- Provides backward compatibility through `graphiti_mcp_server.py`

#### `src/graphiti_mcp_server.py` (Lines 1-968)
**Purpose:** Original MCP server implementation with global state management
- Legacy entry point with CLI argument parsing
- Global service instances for backward compatibility
- Main function for local development

#### `main.py` (Lines 1-27)
**Purpose:** Backward-compatible entry point wrapper
- Maintains compatibility with existing deployment scripts
- Delegates to `graphiti_mcp_server.py`

### Classes

#### **GraphitiService** (`src/server.py:88-168`, `src/graphiti_mcp_server.py:162-321`)
**Purpose:** Service class managing Graphiti client lifecycle and initialization
**Type:** Public API (Service Layer)

**Key Methods:**
- `__init__(config: GraphitiConfig, semaphore_limit: int)` - Initialize service with configuration
- `async initialize()` - Create and configure Graphiti client with LLM, embedder, and database
- `async get_client() -> Graphiti` - Retrieve initialized client instance

**Responsibilities:**
- Factory pattern for creating LLM/embedder/database clients
- Building custom entity types from configuration
- Managing connection to graph database (FalkorDB/Neo4j)
- Error handling with helpful connection messages

#### **QueueService** (`src/services/queue_service.py:12-153`)
**Purpose:** Manages sequential episode processing by group_id to prevent race conditions
**Type:** Public API (Service Layer)

**Key Methods:**
- `async initialize(graphiti_client: Any)` - Initialize with Graphiti client
- `async add_episode(...)` - Queue episode for async processing
- `async add_episode_task(group_id: str, process_func: Callable)` - Add processing task to queue
- `get_queue_size(group_id: str) -> int` - Get current queue size
- `is_worker_running(group_id: str) -> bool` - Check worker status

**Responsibilities:**
- Sequential processing of episodes per group_id
- Background task workers for each group
- Async episode addition to knowledge graph

### Functions

#### **MCP Tool: add_memory** (`src/server.py:231-266`, `src/graphiti_mcp_server.py:324-407`)
**Purpose:** Add episodes (text, JSON, or messages) to the knowledge graph
**Type:** Public API (MCP Tool)

**Signature:**
```python
async def add_memory(
    name: str,
    episode_body: str,
    group_id: str | None = None,
    source: str = 'text',
    source_description: str = '',
    uuid: str | None = None,
) -> SuccessResponse | ErrorResponse
```

**Parameters:**
- `name` - Episode name/title
- `episode_body` - Content (text, JSON string, or message)
- `group_id` - Knowledge graph namespace (optional)
- `source` - Episode type: 'text', 'json', or 'message'
- `source_description` - Metadata about the source
- `uuid` - Optional UUID for idempotency

#### **MCP Tool: search_nodes** (`src/server.py:268-312`, `src/graphiti_mcp_server.py:410-487`)
**Purpose:** Search for entities in the knowledge graph using natural language queries
**Type:** Public API (MCP Tool)

**Signature:**
```python
async def search_nodes(
    query: str,
    group_ids: list[str] | None = None,
    max_nodes: int = 10,
    entity_types: list[str] | None = None,
) -> NodeSearchResponse | ErrorResponse
```

**Returns:** List of entity nodes with UUID, name, labels, summary, and attributes

#### **MCP Tool: search_memory_facts** (`src/server.py:314-343`, `src/graphiti_mcp_server.py:490-541`)
**Purpose:** Search for relationship facts between entities
**Type:** Public API (MCP Tool)

**Signature:**
```python
async def search_memory_facts(
    query: str,
    group_ids: list[str] | None = None,
    max_facts: int = 10,
    center_node_uuid: str | None = None,
) -> FactSearchResponse | ErrorResponse
```

**Returns:** List of relationship edges with source, target, and relationship metadata

#### **MCP Tool: get_episodes** (`src/server.py:381-416`, `src/graphiti_mcp_server.py:623-688`)
**Purpose:** Retrieve episodes from the knowledge graph
**Type:** Public API (MCP Tool)

**Signature:**
```python
async def get_episodes(
    group_ids: list[str] | None = None,
    max_episodes: int = 10,
) -> EpisodeSearchResponse | ErrorResponse
```

#### **MCP Tool: delete_episode** (`src/server.py:357-367`, `src/graphiti_mcp_server.py:570-593`)
**Purpose:** Delete an episode by UUID
**Type:** Public API (MCP Tool)

#### **MCP Tool: delete_entity_edge** (`src/server.py:345-355`, `src/graphiti_mcp_server.py:544-567`)
**Purpose:** Delete a relationship edge by UUID
**Type:** Public API (MCP Tool)

#### **MCP Tool: get_entity_edge** (`src/server.py:369-378`, `src/graphiti_mcp_server.py:596-620`)
**Purpose:** Retrieve a specific relationship edge by UUID
**Type:** Public API (MCP Tool)

#### **MCP Tool: clear_graph** (`src/server.py:418-432`, `src/graphiti_mcp_server.py:691-723`)
**Purpose:** Clear all data for specified group IDs
**Type:** Public API (MCP Tool)

#### **MCP Tool: get_status** (`src/server.py:434-455`, `src/graphiti_mcp_server.py:726-756`)
**Purpose:** Health check for server and database connectivity
**Type:** Public API (MCP Tool)

#### **create_server** (`src/server.py:173-219`)
**Purpose:** Factory function creating and initializing FastMCP server instance
**Type:** Public API (Entry Point)

**Signature:**
```python
async def create_server() -> FastMCP
```

**Responsibilities:**
- Load configuration from environment/YAML
- Initialize GraphitiService and QueueService
- Create FastMCP server instance
- Register all MCP tools via closure pattern
- Register custom health check route

---

## Internal Implementation

### Modules

#### `src/config/schema.py` (Lines 1-293)
**Purpose:** Configuration schema with Pydantic settings and YAML support
**Type:** Internal (Configuration)

**Key Components:**
- `YamlSettingsSource` - Custom settings source for YAML config files
- `GraphitiConfig` - Main configuration class with nested settings
- Provider-specific configs for OpenAI, Azure, Anthropic, Gemini, Groq, Voyage, Neo4j, FalkorDB

#### `src/services/factories.py` (Lines 1-440)
**Purpose:** Factory classes for creating client instances based on configuration
**Type:** Internal (Factory Pattern)

**Key Classes:**
- `LLMClientFactory` - Creates LLM clients (OpenAI, Azure, Anthropic, Gemini, Groq)
- `EmbedderFactory` - Creates embedder clients (OpenAI, Azure, Gemini, Voyage)
- `DatabaseDriverFactory` - Creates database connection configs (Neo4j, FalkorDB)

#### `src/models/response_types.py` (Lines 1-44)
**Purpose:** TypedDict definitions for MCP tool responses
**Type:** Internal (Data Models)

**Defined Types:**
- `ErrorResponse`, `SuccessResponse`, `StatusResponse`
- `NodeResult`, `NodeSearchResponse`
- `FactSearchResponse`, `EpisodeSearchResponse`

#### `src/models/entity_types.py` (Lines 1-226)
**Purpose:** Custom Pydantic entity type definitions for knowledge extraction
**Type:** Internal (Domain Models)

**Defined Entities:**
- `Requirement`, `Preference`, `Procedure`
- `Location`, `Event`, `Object`, `Topic`
- `Organization`, `Document`

#### `src/utils/formatting.py` (Lines 1-51)
**Purpose:** Utility functions for formatting Graphiti entities
**Type:** Internal (Utilities)

**Functions:**
- `format_node_result(node: EntityNode) -> dict` - Format entity nodes
- `format_fact_result(edge: EntityEdge) -> dict` - Format relationship edges

#### `src/utils/utils.py` (Lines 1-28)
**Purpose:** General utility functions
**Type:** Internal (Utilities)

**Functions:**
- `create_azure_credential_token_provider()` - Azure AD authentication helper

### Classes

#### **YamlSettingsSource** (`src/config/schema.py:16-74`)
**Purpose:** Custom Pydantic settings source for loading YAML configuration files
**Type:** Internal (Configuration)

**Key Methods:**
- `_expand_env_vars(value: Any) -> Any` - Recursively expand ${VAR} syntax in YAML
- `__call__() -> dict[str, Any]` - Load and parse YAML with env var expansion

#### **GraphitiConfig** (`src/config/schema.py:230-293`)
**Purpose:** Main configuration class with environment and YAML support
**Type:** Internal (Configuration)

**Key Methods:**
- `apply_cli_overrides(args)` - Apply command-line argument overrides
- `settings_customise_sources()` - Configure settings priority (CLI > env > YAML > defaults)

**Nested Configuration:**
- `server: ServerConfig` - Host, port, transport settings
- `llm: LLMConfig` - LLM provider and model configuration
- `embedder: EmbedderConfig` - Embedding provider configuration
- `database: DatabaseConfig` - Database provider configuration
- `graphiti: GraphitiAppConfig` - Graphiti-specific settings (group_id, entity types)

### Functions

#### **_register_tools** (`src/server.py:222-455`)
**Purpose:** Internal function to register all MCP tools using closure pattern
**Type:** Internal (Tool Registration)

**Signature:**
```python
def _register_tools(
    server: FastMCP,
    cfg: GraphitiConfig,
    graphiti_svc: GraphitiService,
    queue_svc: QueueService,
) -> None
```

**Pattern:** Closure-based dependency injection - tools capture service instances

#### **run_local** (`src/server.py:461-495`)
**Purpose:** Run the server locally with CLI argument support
**Type:** Internal (Entry Point)

**Responsibilities:**
- Create server via factory pattern
- Parse CLI arguments for local overrides
- Configure FastMCP settings
- Run with stdio or HTTP transport

#### **initialize_server** (`src/graphiti_mcp_server.py:764-908`)
**Purpose:** Parse CLI arguments and initialize server configuration (legacy)
**Type:** Internal (Initialization)

**Responsibilities:**
- Parse comprehensive CLI arguments
- Load YAML configuration
- Apply CLI overrides to config
- Initialize GraphitiService and QueueService
- Handle graph destruction if requested

#### **run_mcp_server** (`src/graphiti_mcp_server.py:910-952`)
**Purpose:** Run the MCP server in the current event loop (legacy)
**Type:** Internal (Entry Point)

#### **_validate_api_key** (`src/services/factories.py:76-98`)
**Purpose:** Validate that required API keys are present
**Type:** Internal (Validation)

#### **_process_episode_queue** (`src/services/queue_service.py:49-80`)
**Purpose:** Background worker processing episodes sequentially per group_id
**Type:** Internal (Queue Processing)

**Pattern:** Long-lived async task with queue-based task processing

---

## Entry Points

### Primary Entry Points

1. **FastMCP Cloud Deployment**: `src/server.py::create_server()`
   - Factory function for async server creation
   - Used by FastMCP Cloud platform
   - Configuration from environment variables only

2. **Local Development**: `main.py` → `src/graphiti_mcp_server.py::main()`
   - CLI-based entry point with argument parsing
   - Supports YAML config files
   - Backward compatible with existing scripts

3. **Direct Server Module**: `python src/graphiti_mcp_server.py`
   - Legacy entry point
   - Full CLI argument support
   - Used for local testing and development

### Example/Script Entry Points

4. **MCP Client Examples**: `examples/01_connect_and_discover.py`, `examples/02_call_tools.py`
   - Demonstrate MCP client usage patterns
   - Connect via HTTP transport
   - Show tool invocation patterns

5. **Utility Scripts**:
   - `scripts/check_falkordb_health.py` - Database health monitoring
   - `scripts/populate_meta_knowledge.py` - Seed knowledge graph with best practices
   - `scripts/export_graph.py`, `scripts/import_graph.py` - Data migration
   - `scripts/validate_qdrant.py` - Vector database validation
   - `scripts/verify_fastmcp_cloud_readiness.py` - Deployment verification

### Test Entry Points

6. **Test Runner**: `tests/run_tests.py`
   - Custom pytest runner
   - Configures test environment

---

## Dependencies Between Components

### Dependency Graph

```
main.py
  └─> src/graphiti_mcp_server.py (imports and calls main())
      ├─> config/schema.py (GraphitiConfig)
      ├─> models/response_types.py (Response TypedDicts)
      ├─> services/factories.py (Client factories)
      ├─> services/queue_service.py (QueueService)
      └─> utils/formatting.py (format_fact_result, format_node_result)

src/server.py (factory pattern)
  ├─> config/schema.py (GraphitiConfig)
  ├─> models/response_types.py (Response TypedDicts)
  ├─> services/factories.py (Client factories)
  ├─> services/queue_service.py (QueueService)
  └─> utils/formatting.py (format_fact_result)

services/factories.py
  ├─> config/schema.py (Provider configs)
  └─> utils/utils.py (Azure credential provider)

config/schema.py
  └─> YAML file loading (config/config.yaml)
  └─> Environment variables (.env)
```

### Component Relationships

**Configuration Flow:**
```
Environment Variables → .env file → config/config.yaml → GraphitiConfig → Service Initialization
```

**Request Flow:**
```
MCP Client → FastMCP Server → MCP Tool Function → GraphitiService → Graphiti Client → Database
                                                  └─> QueueService (for add_memory)
```

**Factory Pattern Flow:**
```
GraphitiConfig → LLMClientFactory.create() → LLM Client Instance
              → EmbedderFactory.create() → Embedder Client Instance
              → DatabaseDriverFactory.create_config() → Database Config Dict
```

**Service Initialization:**
```
create_server() (factory)                    initialize_server() (legacy)
  └─> Load GraphitiConfig                      └─> Parse CLI args
  └─> Create GraphitiService                   └─> Apply overrides to config
      └─> Initialize LLM client                └─> Create GraphitiService
      └─> Initialize Embedder client               └─> (same initialization)
      └─> Initialize Database driver           └─> Create QueueService
  └─> Create QueueService                      └─> Set global instances
  └─> Initialize QueueService with client      └─> Configure FastMCP settings
  └─> Create FastMCP instance
  └─> Register tools via _register_tools()
```

### Key Architectural Decisions

1. **Factory Pattern for Deployment Flexibility**
   - `create_server()` factory enables FastMCP Cloud deployment
   - Separation of server creation from execution
   - Clean dependency injection

2. **Dual Entry Point Strategy**
   - Factory-based (`server.py`) for cloud deployment
   - Global-based (`graphiti_mcp_server.py`) for local development
   - Maintains backward compatibility

3. **Queue-Based Episode Processing**
   - Prevents race conditions with sequential processing per group_id
   - Separate queues for different knowledge namespaces
   - Background workers with proper error handling

4. **Configuration Hierarchy**
   - CLI args override environment vars
   - Environment vars override YAML config
   - YAML config overrides defaults
   - Supports ${VAR} expansion in YAML

5. **Provider Abstraction**
   - Factory pattern for LLM/embedder/database clients
   - Supports multiple providers (OpenAI, Azure, Anthropic, Gemini, Groq, Voyage)
   - Conditional imports for optional dependencies

---

## File Locations Summary

### Source Code (src/)
- **Main Servers**: `server.py`, `graphiti_mcp_server.py`
- **Configuration**: `config/schema.py`
- **Models**: `models/response_types.py`, `models/entity_types.py`
- **Services**: `services/factories.py`, `services/queue_service.py`
- **Utilities**: `utils/formatting.py`, `utils/utils.py`

### Entry Points
- **Production**: `main.py`
- **Factory**: `src/server.py::create_server()`

### Examples
- `examples/01_connect_and_discover.py`
- `examples/02_call_tools.py`
- `examples/03_graphiti_memory.py`
- `examples/04_mcp_concepts.py`

### Scripts
- `scripts/check_falkordb_health.py`
- `scripts/populate_meta_knowledge.py`
- `scripts/export_graph.py`
- `scripts/import_graph.py`
- `scripts/validate_qdrant.py`

### Tests
- `tests/` (13 test files)
- `tests/conftest.py` (pytest configuration)

---

## Notes

- **Async-First Architecture**: All core operations use asyncio for concurrent processing
- **MCP Protocol**: Uses FastMCP framework for Model Context Protocol implementation
- **Knowledge Graph**: Built on Graphiti Core library with FalkorDB or Neo4j backend
- **Configuration-Driven**: Extensive YAML + environment variable configuration support
- **Multi-Provider Support**: Flexible provider abstraction for LLMs, embedders, and databases
- **Queue-Based Processing**: Episode processing is asynchronous and sequential per group_id
- **Temporal Facts**: Graph maintains temporal metadata for knowledge evolution
- **Custom Entity Types**: Supports Pydantic models for domain-specific entity extraction

**Version Information:**
- Python 3.10+
- FastMCP (MCP server framework)
- Graphiti Core (knowledge graph library)
- Pydantic v2 (data validation)
- Multiple LLM provider support (OpenAI, Azure, Anthropic, Gemini, Groq)
