# Architecture Diagrams

## System Architecture

### Overview
The Graphiti MCP Server is built on a layered architecture that separates concerns between presentation (MCP server interface), business logic (services and factories), data access (Graphiti Core integration), and configuration management. The system uses the Model Context Protocol (MCP) to expose knowledge graph functionality through a FastMCP server, which can operate via HTTP, SSE, or STDIO transports.

The architecture follows these key principles:
- **Separation of Concerns**: Clear boundaries between configuration, services, models, and utilities
- **Factory Pattern**: Abstraction of LLM, Embedder, and Database client creation
- **Queue-based Processing**: Asynchronous episode processing with per-group_id sequential guarantees
- **Configuration-driven**: YAML-based configuration with environment variable support and CLI overrides

### Layered Architecture Diagram
```mermaid
flowchart TB
    subgraph "Presentation Layer"
        MCP[FastMCP Server]
        TOOLS[MCP Tools API]
        HTTP[HTTP/SSE/STDIO Transports]
    end

    subgraph "Service Layer"
        GS[GraphitiService]
        QS[QueueService]
        FACT[LLMClientFactory]
        FEMBEDDER[EmbedderFactory]
        FDB[DatabaseDriverFactory]
    end

    subgraph "Core Integration Layer"
        GRAPHITI[Graphiti Core Client]
        DRIVER[Database Driver<br/>Neo4j/FalkorDB]
        LLM[LLM Client<br/>OpenAI/Anthropic/etc]
        EMBEDDER[Embedder Client<br/>OpenAI/Gemini/etc]
    end

    subgraph "Configuration Layer"
        CONFIG[GraphitiConfig]
        YAML[YAML Settings Source]
        ENV[Environment Variables]
        CLI[CLI Arguments]
    end

    subgraph "Model Layer"
        ENTITY[Entity Types]
        RESPONSE[Response Types]
    end

    subgraph "Data Layer"
        NEO4J[(Neo4j Database)]
        FALKOR[(FalkorDB Database)]
    end

    HTTP --> MCP
    MCP --> TOOLS
    TOOLS --> GS
    TOOLS --> QS

    GS --> FACT
    GS --> FEMBEDDER
    GS --> FDB

    FACT --> LLM
    FEMBEDDER --> EMBEDDER
    FDB --> DRIVER

    GS --> GRAPHITI
    GRAPHITI --> DRIVER
    GRAPHITI --> LLM
    GRAPHITI --> EMBEDDER

    DRIVER --> NEO4J
    DRIVER --> FALKOR

    CONFIG --> GS
    YAML --> CONFIG
    ENV --> CONFIG
    CLI --> CONFIG

    ENTITY --> GS
    RESPONSE --> TOOLS

    QS --> GRAPHITI

    style MCP fill:#e1f5ff
    style GS fill:#fff4e1
    style GRAPHITI fill:#e8f5e9
    style CONFIG fill:#fce4ec
```

**Layer Responsibilities:**

1. **Presentation Layer**: Handles all MCP protocol communication and exposes tools as API endpoints
   - FastMCP Server: Main entry point for MCP communication
   - MCP Tools API: Tool definitions (add_memory, search_nodes, search_memory_facts, etc.)
   - Transport Handlers: HTTP, SSE (deprecated), and STDIO transport implementations

2. **Service Layer**: Business logic and orchestration
   - GraphitiService: Main service coordinating Graphiti Core operations
   - QueueService: Manages sequential episode processing per group_id
   - Factories: Create and configure LLM, Embedder, and Database clients

3. **Core Integration Layer**: Integration with Graphiti Core library
   - Graphiti Core Client: Primary interface to the Graphiti knowledge graph library
   - Database Drivers: Neo4j or FalkorDB graph database drivers
   - AI Clients: LLM and Embedder clients for entity extraction and search

4. **Configuration Layer**: Centralized configuration management
   - Multi-source configuration: YAML files, environment variables, CLI arguments
   - Validation and type safety via Pydantic
   - Provider-specific configurations

5. **Model Layer**: Data models and type definitions
   - Entity Types: Custom entity type definitions (Requirement, Preference, Procedure, etc.)
   - Response Types: Structured response formats for MCP tools

6. **Data Layer**: Persistent storage
   - Graph databases for knowledge graph storage (Neo4j or FalkorDB)

## Component Relationships

### Overview
The system uses a service-oriented architecture where the GraphitiService acts as the central coordinator. It uses factory classes to create provider-specific clients (LLM, Embedder, Database), and delegates episode processing to the QueueService for concurrent handling with sequential guarantees per group_id.

### Component Diagram
```mermaid
flowchart LR
    subgraph "Entry Point"
        MAIN[main.py]
        SERVER[graphiti_mcp_server.py]
    end

    subgraph "Configuration System"
        CONFIG[GraphitiConfig]
        SCONFIG[ServerConfig]
        LCONFIG[LLMConfig]
        ECONFIG[EmbedderConfig]
        DBCONFIG[DatabaseConfig]
    end

    subgraph "Service Components"
        GRAPHITI_SVC[GraphitiService]
        QUEUE_SVC[QueueService]
    end

    subgraph "Factory Components"
        LLM_FACTORY[LLMClientFactory]
        EMB_FACTORY[EmbedderFactory]
        DB_FACTORY[DatabaseDriverFactory]
    end

    subgraph "MCP Tools"
        ADD_MEM[add_memory]
        SEARCH_NODES[search_nodes]
        SEARCH_FACTS[search_memory_facts]
        GET_EPISODES[get_episodes]
        DELETE[delete_episode/edge]
        CLEAR[clear_graph]
        STATUS[get_status]
    end

    subgraph "Utilities"
        FORMAT[formatting.py]
        UTILS[utils.py]
    end

    MAIN --> SERVER
    SERVER --> CONFIG
    CONFIG --> SCONFIG
    CONFIG --> LCONFIG
    CONFIG --> ECONFIG
    CONFIG --> DBCONFIG

    SERVER --> GRAPHITI_SVC
    SERVER --> QUEUE_SVC

    GRAPHITI_SVC --> LLM_FACTORY
    GRAPHITI_SVC --> EMB_FACTORY
    GRAPHITI_SVC --> DB_FACTORY

    ADD_MEM --> QUEUE_SVC
    SEARCH_NODES --> GRAPHITI_SVC
    SEARCH_FACTS --> GRAPHITI_SVC
    GET_EPISODES --> GRAPHITI_SVC
    DELETE --> GRAPHITI_SVC
    CLEAR --> GRAPHITI_SVC
    STATUS --> GRAPHITI_SVC

    SEARCH_FACTS --> FORMAT
    GRAPHITI_SVC --> UTILS

    style MAIN fill:#e1f5ff
    style CONFIG fill:#fce4ec
    style GRAPHITI_SVC fill:#fff4e1
    style QUEUE_SVC fill:#fff4e1
```

**Key Relationships:**

1. **Initialization Flow**: main.py → graphiti_mcp_server.py → initialize_server() → GraphitiService + QueueService
2. **Configuration Cascade**: GraphitiConfig contains nested configs (ServerConfig, LLMConfig, EmbedderConfig, DatabaseConfig)
3. **Factory Pattern**: GraphitiService uses factories to create provider-specific clients
4. **Tool Routing**: MCP tools route to either GraphitiService (for queries) or QueueService (for writes)
5. **Utility Support**: Formatting utilities for response serialization, utils for Azure AD authentication

## Class Hierarchies

### Overview
The codebase uses Pydantic models extensively for configuration and data validation. Entity types are dynamically created Pydantic models, while response types use TypedDict for MCP tool returns. The service classes follow a simple initialization pattern without deep inheritance.

### Class Diagram
```mermaid
classDiagram
    class BaseSettings {
        +model_config: SettingsConfigDict
        +settings_customise_sources()
    }

    class GraphitiConfig {
        +server: ServerConfig
        +llm: LLMConfig
        +embedder: EmbedderConfig
        +database: DatabaseConfig
        +graphiti: GraphitiAppConfig
        +destroy_graph: bool
        +apply_cli_overrides(args)
    }

    class ServerConfig {
        +transport: str
        +host: str
        +port: int
    }

    class LLMConfig {
        +provider: str
        +model: str
        +temperature: float
        +max_tokens: int
        +providers: LLMProvidersConfig
    }

    class EmbedderConfig {
        +provider: str
        +model: str
        +dimensions: int
        +providers: EmbedderProvidersConfig
    }

    class DatabaseConfig {
        +provider: str
        +providers: DatabaseProvidersConfig
    }

    class GraphitiAppConfig {
        +group_id: str
        +episode_id_prefix: str
        +user_id: str
        +entity_types: list[EntityTypeConfig]
    }

    class GraphitiService {
        -config: GraphitiConfig
        -semaphore_limit: int
        -semaphore: asyncio.Semaphore
        -client: Graphiti
        -entity_types: dict
        +initialize()
        +get_client()
    }

    class QueueService {
        -_episode_queues: dict[str, asyncio.Queue]
        -_queue_workers: dict[str, bool]
        -_graphiti_client: Graphiti
        +initialize(graphiti_client)
        +add_episode_task(group_id, process_func)
        +add_episode(...)
        -_process_episode_queue(group_id)
    }

    class LLMClientFactory {
        +create(config: LLMConfig)$ LLMClient
    }

    class EmbedderFactory {
        +create(config: EmbedderConfig)$ EmbedderClient
    }

    class DatabaseDriverFactory {
        +create_config(config: DatabaseConfig)$ dict
    }

    class BaseModel {
        +model_dump()
    }

    class Requirement {
        +project_name: str
        +description: str
    }

    class Preference {
        ...
    }

    class Procedure {
        +description: str
    }

    class Location {
        +name: str
        +description: str
    }

    class Event {
        +name: str
        +description: str
    }

    class Organization {
        +name: str
        +description: str
    }

    class Document {
        +title: str
        +description: str
    }

    BaseSettings <|-- GraphitiConfig
    GraphitiConfig *-- ServerConfig
    GraphitiConfig *-- LLMConfig
    GraphitiConfig *-- EmbedderConfig
    GraphitiConfig *-- DatabaseConfig
    GraphitiConfig *-- GraphitiAppConfig

    BaseModel <|-- Requirement
    BaseModel <|-- Preference
    BaseModel <|-- Procedure
    BaseModel <|-- Location
    BaseModel <|-- Event
    BaseModel <|-- Organization
    BaseModel <|-- Document

    GraphitiService ..> GraphitiConfig : uses
    GraphitiService ..> LLMClientFactory : uses
    GraphitiService ..> EmbedderFactory : uses
    GraphitiService ..> DatabaseDriverFactory : uses

    QueueService ..> GraphitiService : uses client from
```

**Class Design Patterns:**

1. **Configuration Composition**: GraphitiConfig aggregates multiple configuration classes
2. **Static Factories**: Factory classes use static methods to create instances
3. **Service Pattern**: GraphitiService and QueueService are stateful services initialized at startup
4. **Pydantic Models**: Entity types and configurations use Pydantic for validation
5. **TypedDict Responses**: Response types use TypedDict for lightweight structured returns

## Module Dependencies

### Overview
The module structure is organized into clear packages: config (configuration management), services (business logic), models (data definitions), and utils (helper functions). The main server module orchestrates all components and exposes MCP tools.

### Dependency Diagram
```mermaid
flowchart TD
    subgraph "Root Modules"
        MAIN[main.py]
        SERVER[src/graphiti_mcp_server.py]
    end

    subgraph "Config Package"
        CFG_INIT[src/config/__init__.py]
        CFG_SCHEMA[src/config/schema.py]
    end

    subgraph "Models Package"
        MOD_INIT[src/models/__init__.py]
        MOD_ENTITY[src/models/entity_types.py]
        MOD_RESPONSE[src/models/response_types.py]
    end

    subgraph "Services Package"
        SVC_INIT[src/services/__init__.py]
        SVC_FACTORY[src/services/factories.py]
        SVC_QUEUE[src/services/queue_service.py]
    end

    subgraph "Utils Package"
        UTL_INIT[src/utils/__init__.py]
        UTL_FORMAT[src/utils/formatting.py]
        UTL_UTILS[src/utils/utils.py]
    end

    subgraph "External Dependencies"
        GRAPHITI[graphiti_core]
        FASTMCP[fastmcp]
        PYDANTIC[pydantic]
        DOTENV[python-dotenv]
        OPENAI[openai]
        YAML[pyyaml]
    end

    MAIN --> SERVER

    SERVER --> CFG_SCHEMA
    SERVER --> MOD_RESPONSE
    SERVER --> SVC_FACTORY
    SERVER --> SVC_QUEUE
    SERVER --> UTL_FORMAT
    SERVER --> FASTMCP
    SERVER --> GRAPHITI
    SERVER --> DOTENV

    CFG_SCHEMA --> PYDANTIC
    CFG_SCHEMA --> YAML

    MOD_ENTITY --> PYDANTIC
    MOD_RESPONSE --> PYDANTIC

    SVC_FACTORY --> CFG_SCHEMA
    SVC_FACTORY --> UTL_UTILS
    SVC_FACTORY --> GRAPHITI
    SVC_FACTORY --> OPENAI

    UTL_FORMAT --> GRAPHITI

    style MAIN fill:#e1f5ff
    style SERVER fill:#e1f5ff
    style CFG_SCHEMA fill:#fce4ec
    style SVC_FACTORY fill:#fff4e1
    style SVC_QUEUE fill:#fff4e1
    style GRAPHITI fill:#e8f5e9
    style FASTMCP fill:#e8f5e9
```

**Dependency Layers:**

1. **Entry Layer** (main.py, graphiti_mcp_server.py)
   - Imports from all internal packages
   - Directly depends on external frameworks (fastmcp, graphiti_core)

2. **Configuration Layer** (config/)
   - schema.py: Depends on pydantic, pyyaml
   - No dependencies on other internal packages

3. **Models Layer** (models/)
   - entity_types.py: Depends only on pydantic
   - response_types.py: Depends only on typing_extensions
   - No dependencies on other internal packages

4. **Services Layer** (services/)
   - factories.py: Depends on config, utils, graphiti_core, openai
   - queue_service.py: Minimal dependencies (asyncio, logging)

5. **Utils Layer** (utils/)
   - formatting.py: Depends on graphiti_core
   - utils.py: Depends on azure.identity (optional)

**Import Guidelines:**

- **Top-down dependencies**: Server → Services → Config/Models/Utils
- **No circular dependencies**: Clean separation between layers
- **Optional imports**: Provider-specific clients are imported conditionally
- **External isolation**: External dependencies concentrated in factories and server

## Data Flow

### Overview
The system processes data through several key flows: episode addition (async write path), search operations (sync read path), and initialization (setup). The episode addition flow uses a queue-based system to ensure sequential processing per group_id while allowing concurrent processing across different groups.

### Episode Addition Flow
```mermaid
sequenceDiagram
    participant Client
    participant MCP as FastMCP Server
    participant Tool as add_memory Tool
    participant QS as QueueService
    participant Worker as Queue Worker
    participant GC as Graphiti Client
    participant DB as Database
    participant LLM as LLM Client
    participant EMB as Embedder Client

    Client->>MCP: Add episode request
    MCP->>Tool: add_memory(name, content, group_id, ...)

    Note over Tool: Validate parameters
    Tool->>Tool: Parse episode_type enum
    Tool->>Tool: Determine effective_group_id

    Tool->>QS: add_episode(group_id, name, content, ...)

    Note over QS: Create async task
    QS->>QS: Create queue for group_id (if new)
    QS->>QS: Add process_func to queue
    QS->>Worker: Start worker (if not running)
    QS-->>Tool: Return queue position

    Tool-->>MCP: SuccessResponse(queued)
    MCP-->>Client: Episode queued message

    Note over Worker,GC: Async processing
    Worker->>Worker: Dequeue process_func
    Worker->>GC: add_episode(name, content, ...)

    activate GC
    GC->>LLM: Extract entities from content
    LLM-->>GC: Entity list

    GC->>LLM: Deduplicate entities
    LLM-->>GC: Deduplicated entities

    GC->>EMB: Generate embeddings
    EMB-->>GC: Embeddings

    GC->>DB: Create nodes and edges
    DB-->>GC: Confirmation
    deactivate GC

    Worker->>QS: Mark task_done()

    Note over Worker: Process next episode in queue
```

### Search Flow
```mermaid
sequenceDiagram
    participant Client
    participant MCP as FastMCP Server
    participant Tool as search_nodes Tool
    participant GS as GraphitiService
    participant GC as Graphiti Client
    participant EMB as Embedder Client
    participant DB as Database
    participant FMT as Formatting Utils

    Client->>MCP: Search request
    MCP->>Tool: search_nodes(query, group_ids, ...)

    Tool->>Tool: Determine effective_group_ids
    Tool->>Tool: Create SearchFilters

    Tool->>GS: get_client()
    GS-->>Tool: Graphiti Client

    Tool->>GC: search_(query, config, group_ids, filters)

    activate GC
    GC->>EMB: Generate query embedding
    EMB-->>GC: Query embedding

    GC->>DB: Hybrid search (vector + text)
    DB-->>GC: Matching nodes
    deactivate GC

    GC-->>Tool: Search results

    loop For each node
        Tool->>Tool: Remove embeddings from attributes
        Tool->>Tool: Create NodeResult
    end

    Tool-->>MCP: NodeSearchResponse
    MCP-->>Client: Search results
```

### Initialization Flow
```mermaid
sequenceDiagram
    participant Main as main.py
    participant Server as graphiti_mcp_server
    participant Config as GraphitiConfig
    participant YAML as YAML File
    participant ENV as Environment
    participant GS as GraphitiService
    participant Factories as Factory Classes
    participant QS as QueueService
    participant GC as Graphiti Client
    participant DB as Database Driver

    Main->>Server: main()
    Server->>Server: initialize_server()

    Note over Server,ENV: Configuration Loading
    Server->>Config: GraphitiConfig()
    Config->>YAML: Load config.yaml
    YAML-->>Config: YAML settings
    Config->>ENV: Read environment variables
    ENV-->>Config: Environment settings
    Config->>Config: Merge with defaults
    Config-->>Server: Unified configuration

    Server->>Server: Apply CLI overrides

    Note over Server,GS: Service Initialization
    Server->>GS: GraphitiService(config)
    Server->>GS: initialize()

    activate GS
    GS->>Factories: LLMClientFactory.create(config.llm)
    Factories-->>GS: LLM Client

    GS->>Factories: EmbedderFactory.create(config.embedder)
    Factories-->>GS: Embedder Client

    GS->>Factories: DatabaseDriverFactory.create_config(config.db)
    Factories-->>GS: Database config

    GS->>GC: Graphiti(driver, llm, embedder)
    GC->>DB: Connect to database
    DB-->>GC: Connection established
    GC->>DB: build_indices_and_constraints()
    DB-->>GC: Indices ready
    GC-->>GS: Client ready
    deactivate GS

    Server->>QS: QueueService()
    Server->>QS: initialize(graphiti_client)

    Server->>Server: Set fastmcp settings (host, port)
    Server-->>Main: ServerConfig

    Main->>Server: run_mcp_server()
    Server->>Server: Run with configured transport

    Note over Server: Server running, ready for requests
```

### Configuration Resolution Flow
```mermaid
flowchart LR
    subgraph "Priority Order (Highest to Lowest)"
        CLI[1. CLI Arguments]
        ENV[2. Environment Variables]
        YAML[3. YAML Config File]
        DEFAULT[4. Pydantic Defaults]
    end

    subgraph "Configuration Sources"
        CLI_ARGS[--llm-provider openai<br/>--model gpt-4<br/>--transport http]
        ENV_VARS[OPENAI_API_KEY=xxx<br/>DATABASE__PROVIDER=falkordb]
        YAML_FILE[llm:<br/>  provider: openai<br/>  model: gpt-4.1]
        DEFAULTS[provider: 'openai'<br/>model: 'gpt-4.1'<br/>transport: 'http']
    end

    CLI --> CLI_ARGS
    ENV --> ENV_VARS
    YAML --> YAML_FILE
    DEFAULT --> DEFAULTS

    CLI_ARGS --> MERGE[Configuration Merger]
    ENV_VARS --> MERGE
    YAML_FILE --> MERGE
    DEFAULTS --> MERGE

    MERGE --> FINAL[Final GraphitiConfig]

    style CLI fill:#ff9999
    style ENV fill:#ffcc99
    style YAML fill:#ffff99
    style DEFAULT fill:#ccffcc
    style FINAL fill:#99ccff
```

**Data Flow Characteristics:**

1. **Async Write Path**: Episode additions are queued and processed asynchronously, returning immediately to the client
2. **Sequential Guarantees**: Episodes for the same group_id are processed sequentially to maintain consistency
3. **Concurrent Processing**: Different group_ids can be processed in parallel (limited by semaphore)
4. **Sync Read Path**: Search operations are synchronous and return results immediately
5. **Configuration Cascade**: Configuration is resolved through multiple layers with clear priority order
6. **Error Handling**: Each layer handles errors appropriately and returns structured error responses

## Key Architectural Patterns

### 1. Factory Pattern
Used extensively for creating provider-specific clients (LLM, Embedder, Database) with configuration-driven selection.

**Location**: `src/services/factories.py`

**Benefits**:
- Encapsulates complex client creation logic
- Supports multiple providers without changing client code
- Centralizes provider-specific configuration

### 2. Service Pattern
GraphitiService and QueueService act as stateful facades to Graphiti Core functionality.

**Locations**:
- `src/graphiti_mcp_server.py` (lines 162-321)
- `src/services/queue_service.py`

**Benefits**:
- Encapsulates initialization complexity
- Manages lifecycle of Graphiti client
- Provides clean interface for MCP tools

### 3. Queue-based Async Processing
Episodes are processed asynchronously through per-group queues to ensure sequential consistency while allowing concurrency.

**Location**: `src/services/queue_service.py` (lines 49-80)

**Benefits**:
- Non-blocking API for episode addition
- Sequential processing per group_id prevents race conditions
- Concurrent processing across different groups

### 4. Configuration Composition
Multi-layered configuration system with YAML, environment variables, and CLI overrides.

**Location**: `src/config/schema.py`

**Benefits**:
- Flexible deployment options (dev, staging, prod)
- Type-safe configuration with Pydantic validation
- Clear priority order for configuration sources

### 5. Decorator-based Tool Registration
MCP tools are registered using FastMCP decorators for clean, declarative API definition.

**Location**: `src/graphiti_mcp_server.py` (lines 323-755)

**Benefits**:
- Clear tool definitions with type hints
- Automatic request/response handling
- Self-documenting API

### 6. Response Type Standardization
Consistent response types (SuccessResponse, ErrorResponse, etc.) across all tools.

**Location**: `src/models/response_types.py`

**Benefits**:
- Predictable error handling
- Consistent client experience
- Easy to test and validate

## Technology Stack

### Core Technologies
- **Python 3.10+**: Primary programming language
- **FastMCP**: MCP protocol server implementation
- **Graphiti Core**: Knowledge graph library
- **Pydantic**: Data validation and configuration management
- **asyncio**: Asynchronous programming support

### AI/ML Integrations
- **LLM Providers**: OpenAI, Azure OpenAI, Anthropic, Gemini, Groq
- **Embedder Providers**: OpenAI, Azure OpenAI, Gemini, Voyage AI

### Database Support
- **Neo4j**: Graph database (bolt protocol)
- **FalkorDB**: Redis-based graph database

### Configuration & Deployment
- **PyYAML**: Configuration file parsing
- **python-dotenv**: Environment variable management
- **Docker**: Containerization support
- **uvicorn**: ASGI server for HTTP transport

## File Reference

### Main Server Files
- `main.py` - Entry point wrapper
- `src/graphiti_mcp_server.py` - Main server implementation with MCP tools

### Configuration
- `src/config/schema.py` - Pydantic configuration schemas

### Services
- `src/services/factories.py` - Client factories for LLM, Embedder, Database
- `src/services/queue_service.py` - Queue-based episode processing

### Models
- `src/models/entity_types.py` - Custom entity type definitions
- `src/models/response_types.py` - MCP tool response types

### Utilities
- `src/utils/formatting.py` - Response formatting utilities
- `src/utils/utils.py` - Azure AD authentication utilities

### Tests
- `tests/` - Comprehensive test suite including integration, stress, and transport tests
