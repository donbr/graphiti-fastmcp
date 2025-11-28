# Repository Architecture Documentation

## Overview

The **Graphiti FastMCP Server** is a production-ready MCP (Model Context Protocol) server that exposes knowledge graph functionality for building AI agent memory systems. Built on top of Graphiti Core, it provides a robust API for adding information (episodes), searching entities and relationships, and managing graph data through the standardized MCP protocol.

**Key Capabilities:**
- **Knowledge Graph Memory**: Transform unstructured text, JSON, and messages into a queryable knowledge graph
- **Multi-Provider Support**: Compatible with OpenAI, Azure OpenAI, Anthropic, Gemini, and Groq for LLMs; OpenAI, Azure, Gemini, and Voyage for embeddings
- **Flexible Database Backends**: Supports both Neo4j and FalkorDB graph databases
- **Async Processing**: Queue-based episode processing ensures data consistency while maintaining high throughput
- **Production-Ready**: HTTP transport, health checks, comprehensive logging, and Docker support
- **Type-Safe**: Full TypeScript-style type hints and Pydantic validation throughout

**Architecture Highlights:**
- Layered architecture with clear separation of concerns
- Factory pattern for provider abstraction
- Queue-based processing with sequential guarantees per namespace
- Configuration-driven design supporting YAML, environment variables, and CLI overrides
- FastMCP framework for MCP protocol handling

## Quick Start

### Using This Documentation

This architecture documentation is organized to support different exploration needs:

1. **Understanding the System**: Start with this README for the big picture
2. **Exploring Components**: Use the Component Inventory to find specific files and functions
3. **Understanding Structure**: Review Architecture Diagrams for visual system layout
4. **Following Requests**: Check Data Flows to see how operations execute
5. **API Integration**: Reference the API Reference for detailed tool and configuration documentation

### Document Index

| Document | Description | Use When... |
|----------|-------------|-------------|
| [Component Inventory](docs/01_component_inventory.md) | Complete catalog of all modules, classes, and functions with file locations | You need to find where specific functionality is implemented or understand what each file does |
| [Architecture Diagrams](diagrams/02_architecture_diagrams.md) | Visual representations of system structure, class hierarchies, and component relationships | You want to understand how components interact or visualize the overall system design |
| [Data Flows](docs/03_data_flows.md) | Detailed sequence diagrams showing request/response lifecycles and message routing | You need to trace how specific operations execute through the system |
| [API Reference](docs/04_api_reference.md) | Comprehensive API documentation with examples and configuration guides | You're integrating with the server or need detailed parameter information |

## Architecture Summary

### System Overview

The Graphiti MCP Server implements a **four-layer architecture** that cleanly separates protocol handling, business logic, core integration, and data persistence:

```
┌─────────────────────────────────────────────────┐
│         Presentation Layer (FastMCP)            │  ← MCP protocol, HTTP/SSE/STDIO
├─────────────────────────────────────────────────┤
│     Service Layer (Business Logic)              │  ← GraphitiService, QueueService, Factories
├─────────────────────────────────────────────────┤
│   Core Integration (Graphiti + AI Providers)    │  ← Graphiti Core, LLM/Embedder clients
├─────────────────────────────────────────────────┤
│        Data Layer (Graph Database)              │  ← Neo4j / FalkorDB
└─────────────────────────────────────────────────┘
```

**Key Architectural Decisions:**

1. **MCP Protocol**: Uses FastMCP framework for standardized agent communication, enabling integration with any MCP-compatible client
2. **Queue-Based Processing**: Episodes are processed asynchronously via per-namespace queues, ensuring sequential consistency while allowing cross-namespace parallelism
3. **Provider Abstraction**: Factory pattern allows runtime selection of LLM, embedder, and database providers without code changes
4. **Configuration Composition**: Multi-source configuration (YAML → ENV → CLI) with type-safe validation via Pydantic

### Layered Architecture

#### Layer 1: Presentation (MCP Interface)
- **Location**: `src/graphiti_mcp_server.py` (lines 148-756)
- **Components**: FastMCP server instance, tool decorators, HTTP/SSE/STDIO transports
- **Responsibility**: Handle MCP protocol messages, route to appropriate handlers, serialize responses
- **Key Pattern**: Decorator-based tool registration with `@mcp.tool()`

#### Layer 2: Service (Business Logic)
- **Location**:
  - GraphitiService: `src/graphiti_mcp_server.py` (lines 162-321)
  - QueueService: `src/services/queue_service.py`
  - Factories: `src/services/factories.py`
- **Components**: Service classes, factory classes, queue management
- **Responsibility**: Orchestrate Graphiti operations, manage client lifecycle, handle async processing
- **Key Patterns**: Service pattern, factory pattern, queue-based async processing

#### Layer 3: Core Integration (AI & Graph Engine)
- **Location**: Graphiti Core library (external), provider SDKs (OpenAI, Anthropic, etc.)
- **Components**: Graphiti client, LLM clients, embedder clients, database drivers
- **Responsibility**: Execute knowledge graph operations, perform entity extraction, generate embeddings
- **Key Pattern**: Client wrapper pattern with factory creation

#### Layer 4: Data (Persistence)
- **Location**: External databases (Neo4j or FalkorDB)
- **Components**: Graph database instances
- **Responsibility**: Store and query nodes, edges, and embeddings
- **Key Pattern**: Driver abstraction via configuration

### Key Design Patterns

1. **Factory Pattern** (`src/services/factories.py`)
   - Creates provider-specific LLM, embedder, and database clients
   - Enables runtime provider selection
   - Centralizes provider-specific configuration logic

2. **Service Pattern** (GraphitiService, QueueService)
   - Encapsulates complex initialization and lifecycle management
   - Provides clean interface for MCP tools
   - Manages stateful resources (Graphiti client, queues)

3. **Queue-Based Async Processing** (`src/services/queue_service.py`)
   - Per-namespace queues ensure sequential processing within a namespace
   - Allows concurrent processing across different namespaces
   - Non-blocking API returns immediately while processing in background

4. **Configuration Composition** (`src/config/schema.py`)
   - Hierarchical configuration with clear precedence: CLI → ENV → YAML → Defaults
   - Environment variable expansion in YAML: `${VAR:default}`
   - Type-safe validation with Pydantic

5. **Decorator-Based Tool Registration**
   - Tools exposed via `@mcp.tool()` decorators
   - FastMCP handles argument validation and response serialization
   - Self-documenting API with type hints and docstrings

6. **Response Type Standardization** (`src/models/response_types.py`)
   - Consistent response structures across all tools
   - TypedDict for type safety without runtime overhead
   - Clear success/error response patterns

## Component Overview

### Core Components

**Main Server** (`src/graphiti_mcp_server.py`)
- FastMCP server with 9 MCP tools for graph operations
- GraphitiService for client lifecycle management
- Global configuration and service initialization
- Entry point and server startup logic

**Configuration System** (`src/config/`)
- `schema.py`: Pydantic configuration models with YAML support
- YamlSettingsSource: Custom settings source with environment variable expansion
- Multi-layered config hierarchy with provider-specific settings

**Services** (`src/services/`)
- `factories.py`: LLMClientFactory, EmbedderFactory, DatabaseDriverFactory
- `queue_service.py`: QueueService for async episode processing

**Models** (`src/models/`)
- `entity_types.py`: Custom entity type definitions (Requirement, Preference, etc.)
- `response_types.py`: TypedDict response structures

**Utilities** (`src/utils/`)
- `formatting.py`: Response formatting with embedding exclusion
- `utils.py`: Azure AD authentication helpers

### Public API Surface

**9 MCP Tools** (exposed via FastMCP):
1. `add_memory` - Add episodes to the knowledge graph (async queue-based)
2. `search_nodes` - Search for entities using hybrid search
3. `search_memory_facts` - Search for relationships/edges
4. `get_entity_edge` - Retrieve specific edge by UUID
5. `get_episodes` - Retrieve episodes by group ID
6. `delete_entity_edge` - Delete specific edge
7. `delete_episode` - Delete specific episode
8. `clear_graph` - Clear all data for specified namespaces
9. `get_status` - Health check and database connectivity status

**HTTP Endpoint**:
- `/health` - Non-MCP health check for load balancers

**Configuration Classes**:
- GraphitiConfig, ServerConfig, LLMConfig, EmbedderConfig, DatabaseConfig
- Provider-specific configs for each supported service

### Internal Services

**GraphitiService**
- Initializes and manages Graphiti Core client
- Coordinates LLM, embedder, and database client creation via factories
- Provides `get_client()` for lazy initialization
- Handles connection errors with helpful provider-specific messages

**QueueService**
- Manages per-namespace asyncio queues
- Spawns worker tasks for each active namespace
- Ensures sequential episode processing per group_id
- Provides queue monitoring (size, worker status)

**Factory Classes**
- Runtime provider selection based on configuration
- Conditional imports for optional dependencies
- API key validation and logging
- Special handling for reasoning models (GPT-5, o1, o3)

## Data Flows

### Primary Flows

#### 1. Episode Addition Flow (Async Write)
```
Client → MCP Tool → Validate → Queue → Return Success
                                  ↓
                            Background Worker → Graphiti → LLM → Embedder → Database
```

**Characteristics**:
- Non-blocking: Client receives success response immediately
- Sequential per namespace: Episodes for same group_id processed in order
- Concurrent across namespaces: Different group_ids processed in parallel
- Semaphore-limited: Controlled concurrency to avoid rate limits

**File References**:
- Tool handler: `src/graphiti_mcp_server.py:323-407`
- Queue service: `src/services/queue_service.py:101-153`

#### 2. Search Flow (Sync Read)
```
Client → MCP Tool → GraphitiService → Graphiti Client → Embedder → Database
                                                                      ↓
Client ← Formatted Response ← Remove Embeddings ← Search Results ← Hybrid Search
```

**Characteristics**:
- Synchronous: Blocks until results are returned
- Hybrid search: Combines vector similarity and keyword matching
- Filtered results: Embeddings removed to reduce payload size
- Namespace-aware: Respects group_id boundaries

**File References**:
- search_nodes: `src/graphiti_mcp_server.py:410-486`
- search_memory_facts: `src/graphiti_mcp_server.py:490-540`

#### 3. Initialization Flow
```
main.py → initialize_server() → Load Config (YAML + ENV + CLI)
                                      ↓
                              Create GraphitiService
                                      ↓
                              Factories → Create LLM, Embedder, DB Clients
                                      ↓
                              Initialize Graphiti Client
                                      ↓
                              Build Database Indices
                                      ↓
                              Initialize QueueService
                                      ↓
                              Start MCP Server
```

**File Reference**: `src/graphiti_mcp_server.py:764-907`

### Request/Response Lifecycle

**MCP Request Processing**:
1. HTTP POST to `/mcp/` with JSON-RPC payload
2. FastMCP parses request and extracts tool name + arguments
3. Argument validation against function signature (Pydantic)
4. Route to appropriate tool handler
5. Execute business logic (GraphitiService or QueueService)
6. Format response (exclude embeddings, serialize dates)
7. Wrap in CallToolResult and serialize to JSON-RPC
8. Return HTTP response

**Error Handling Path**:
- Try/catch blocks in all tools
- Errors logged with context
- ErrorResponse returned to client
- Service continues processing (fails gracefully)

## Key Configuration

### Quick Configuration Guide

**Most Important Settings**:

```yaml
# config/config.yaml
server:
  transport: "http"        # Use 'http' for production, 'stdio' for local testing
  host: "0.0.0.0"
  port: 8000

llm:
  provider: "openai"       # openai | azure_openai | anthropic | gemini | groq
  model: "gpt-5-mini"
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}

embedder:
  provider: "openai"       # openai | azure_openai | gemini | voyage
  model: "text-embedding-3-small"
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}

database:
  provider: "falkordb"     # falkordb | neo4j
  providers:
    falkordb:
      uri: ${FALKORDB_URI:redis://localhost:6379}
      database: ${FALKORDB_DATABASE:default_db}

graphiti:
  group_id: "main"         # Default namespace for graph data
```

### Environment Variables (Essential)

**Required for Operation**:
```bash
# LLM Provider
export OPENAI_API_KEY="sk-..."                    # For OpenAI
# OR
export ANTHROPIC_API_KEY="sk-ant-..."            # For Anthropic
# OR
export GOOGLE_API_KEY="..."                       # For Gemini

# Database (if not using defaults)
export FALKORDB_URI="redis://localhost:6379"      # For FalkorDB
# OR
export NEO4J_URI="bolt://localhost:7687"          # For Neo4j
export NEO4J_PASSWORD="password"
```

**Performance Tuning**:
```bash
# Concurrency control (tune based on LLM rate limits)
export SEMAPHORE_LIMIT=10  # Default: 10, adjust based on provider tier

# OpenAI Tier 1 (free): Use 1
# OpenAI Tier 3: Use 10
# Anthropic high tier: Use 20
```

**Configuration Priority** (highest to lowest):
1. CLI arguments (`--llm-provider openai`)
2. Environment variables (`LLM__PROVIDER=openai`)
3. YAML configuration file
4. Pydantic defaults

## Getting Started with the Codebase

### Entry Points

**Primary Entry Point**:
- `main.py:23` - Wrapper that calls graphiti_mcp_server.main()

**Core Server Entry Point**:
- `src/graphiti_mcp_server.py:954` - Main server entry point with asyncio.run()

**Example Scripts** (Client-side usage):
- `examples/01_connect_and_discover.py` - MCP connection and service discovery
- `examples/02_call_tools.py` - Calling MCP tools
- `examples/03_graphiti_memory.py` - Memory operations demo
- `examples/export_graph.py` - Export graph data to JSON
- `examples/import_graph.py` - Import graph data from JSON

### Key Files to Understand

**Tier 1: Core Server Logic**
1. `src/graphiti_mcp_server.py` (967 lines)
   - MCP tool definitions (lines 323-756)
   - GraphitiService class (lines 162-321)
   - Server initialization (lines 764-907)
   - Transport handling (lines 910-951)

**Tier 2: Configuration & Models**
2. `src/config/schema.py` (293 lines)
   - Configuration class hierarchy
   - YAML settings source with env var expansion (lines 16-74)
   - Provider configurations

3. `src/models/response_types.py` (44 lines)
   - Response type definitions for all MCP tools

**Tier 3: Business Logic**
4. `src/services/factories.py` (440 lines)
   - LLMClientFactory (lines 100-251)
   - EmbedderFactory (lines 253-361)
   - DatabaseDriverFactory (lines 363-440)

5. `src/services/queue_service.py` (153 lines)
   - QueueService for async episode processing
   - Per-namespace queue management

**Tier 4: Utilities**
6. `src/utils/formatting.py` (51 lines)
   - Response formatting helpers
   - Embedding exclusion logic

### Recommended Reading Order

1. **Start with Configuration** (`src/config/schema.py`)
   - Understand how the system is configured
   - See what providers are supported
   - Learn the configuration hierarchy

2. **Read Response Types** (`src/models/response_types.py`)
   - Quick overview of API response structures
   - Understand success/error patterns

3. **Explore MCP Tools** (`src/graphiti_mcp_server.py:323-756`)
   - See the public API surface
   - Understand tool signatures and behavior
   - Follow the code flow for one tool (e.g., `search_nodes`)

4. **Study GraphitiService** (`src/graphiti_mcp_server.py:162-321`)
   - Understand client initialization
   - See how factories are used
   - Learn error handling patterns

5. **Examine Factories** (`src/services/factories.py`)
   - Understand provider abstraction
   - See conditional imports
   - Learn special handling for different providers

6. **Review QueueService** (`src/services/queue_service.py`)
   - Understand async processing model
   - See queue management logic
   - Learn worker task lifecycle

7. **Check Examples** (`examples/`)
   - See client-side usage patterns
   - Understand MCP protocol interaction
   - Learn best practices

## Architecture Decisions

### Why MCP?

**Model Context Protocol (MCP)** provides a standardized way for AI agents to access external context and tools:

- **Standardization**: Works with any MCP-compatible client (Claude Desktop, custom agents, etc.)
- **Tool Discovery**: Clients can discover available tools programmatically
- **Type Safety**: Structured arguments and responses with validation
- **Transport Flexibility**: HTTP for production, STDIO for local development
- **Future-Proof**: Industry standard backed by Anthropic and growing ecosystem

**Alternative Considered**: Custom REST API
- **Rejected Because**: Non-standard, requires custom client code, no built-in tool discovery

### Why Queue-Based Processing?

**Problem**: Race conditions when multiple episodes modify the same graph entities concurrently

**Solution**: Sequential processing per namespace via asyncio queues

**Benefits**:
- **Consistency**: Episodes for same group_id processed in order
- **Performance**: Different group_ids processed in parallel
- **Non-Blocking**: API returns immediately, processing happens in background
- **Scalability**: Worker tasks spawned on-demand per namespace

**Trade-offs**:
- Episodes not immediately visible in graph (eventual consistency)
- No direct feedback on processing errors (already returned success)
- Queue buildup if processing slower than ingestion

**Tuning**: SEMAPHORE_LIMIT controls max concurrent Graphiti operations (see `src/graphiti_mcp_server.py:49-76`)

### Provider Abstraction

**Problem**: Support multiple LLM, embedder, and database providers without code duplication

**Solution**: Factory pattern with runtime provider selection

**Benefits**:
- **Flexibility**: Switch providers via configuration
- **Extensibility**: Add new providers by extending factory
- **Testability**: Easy to mock providers for testing
- **Cost Optimization**: Choose providers based on cost/performance

**Implementation**:
- Factories at `src/services/factories.py`
- Conditional imports for optional dependencies
- Provider-specific configuration nested under main config
- Special handling for provider quirks (e.g., reasoning models)

## References

### Internal Documentation

- **[Component Inventory](docs/01_component_inventory.md)**: Complete catalog of modules, classes, functions, and their locations
- **[Architecture Diagrams](diagrams/02_architecture_diagrams.md)**: Visual representations of system structure, class hierarchies, dependencies, and data flows
- **[Data Flows](docs/03_data_flows.md)**: Detailed sequence diagrams for query operations, session management, tool permissions, server communication, and message routing
- **[API Reference](docs/04_api_reference.md)**: Comprehensive API documentation with examples, configuration guides, and best practices

### External Resources

- **[Graphiti Core](https://github.com/getzep/graphiti)**: Underlying knowledge graph library
- **[FastMCP](https://github.com/jlowin/fastmcp)**: MCP server framework
- **[Model Context Protocol](https://modelcontextprotocol.io/)**: MCP specification and documentation
- **[Neo4j](https://neo4j.com/)**: Neo4j graph database
- **[FalkorDB](https://www.falkordb.com/)**: FalkorDB (Redis-based graph database)

### Configuration Examples

- **[Sample Config](../../../config/config.yaml)**: Production-ready configuration template
- **[Environment Variables](docs/04_api_reference.md#environment-variables-essential)**: Complete list of supported environment variables

## Contributing

### Understanding the Architecture

**For New Contributors**:

1. **Read This README First**: Get the big picture and architectural context
2. **Review Architecture Diagrams**: Understand visual system layout
3. **Study One Data Flow**: Pick a flow (e.g., search) and trace it end-to-end
4. **Read Related Code**: Follow the recommended reading order above
5. **Run Examples**: Execute client examples to see the system in action
6. **Check Tests**: Look at test files to understand expected behavior

**Key Principles**:
- **Separation of Concerns**: Each layer has clear responsibilities
- **Type Safety**: Use type hints and Pydantic validation
- **Error Handling**: Always catch exceptions and return ErrorResponse
- **Logging**: Log important operations and errors
- **Documentation**: Update docstrings and architecture docs

### Where to Add New Features

**Adding a New MCP Tool**:
1. Define in `src/graphiti_mcp_server.py` with `@mcp.tool()` decorator
2. Add response type to `src/models/response_types.py`
3. Update API reference documentation
4. Add example usage to `examples/`

**Adding a New Provider**:
1. Add provider config to `src/config/schema.py`
2. Extend appropriate factory in `src/services/factories.py`
3. Add environment variables to YAML template
4. Document in API reference

**Adding Configuration Options**:
1. Add field to appropriate config class in `src/config/schema.py`
2. Update YAML template in `config/config.yaml`
3. Add CLI argument in `initialize_server()` if needed
4. Document in API reference

**Adding Custom Entity Types**:
1. Define in `src/models/entity_types.py` (or via config)
2. Add to YAML configuration under `graphiti.entity_types`
3. Document usage in API reference

**Modifying Data Flows**:
1. Update sequence diagrams in `ra_output/architecture_20251127_152442/docs/03_data_flows.md`
2. Update architecture diagrams if component relationships change
3. Update this README if architectural decisions change

### Testing Your Changes

**Run Tests**:
```bash
python tests/run_tests.py unit          # Unit tests
python tests/run_tests.py integration   # Integration tests
python tests/run_tests.py all          # All tests
```

**Manual Testing**:
```bash
# Start server
python main.py

# In another terminal, run examples
python examples/01_connect_and_discover.py
python examples/02_call_tools.py
```

---

**Generated**: 2024-11-27

**Documentation Covers**:
- System architecture and design patterns
- Component inventory and relationships
- Data flows and request lifecycles
- Complete API reference with examples
- Configuration options and best practices
- Getting started guide for contributors

**Maintained By**: Architecture documentation is generated from source code analysis and should be updated when significant architectural changes are made.
