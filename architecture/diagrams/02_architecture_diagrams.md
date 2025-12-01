# Architecture Diagrams

## Overview

The Graphiti MCP Server is a FastMCP-based implementation that exposes the Graphiti knowledge graph library through the Model Context Protocol. The architecture follows a layered design with clear separation between API, service, configuration, and data model layers. It employs the Factory Pattern for dependency injection and supports multiple LLM/embedder/database providers.

**Key Architectural Characteristics:**
- **Layered Architecture**: API Layer (MCP Tools) -> Service Layer -> Integration Layer -> External Services
- **Factory Pattern**: Configurable client creation for LLM, Embedder, and Database providers
- **Queue-Based Processing**: Sequential episode processing per group_id to prevent race conditions
- **Configuration-Driven**: YAML + Environment Variables with hierarchical overrides
- **Dual Entry Points**: Factory-based (cloud) and legacy (local development)

---

## System Architecture (Layered View)

### Diagram

```mermaid
graph TB
    subgraph "API Layer"
        A1[FastMCP Server]
        A2[MCP Tools]
        A3[Custom Routes]
        A1 --> A2
        A1 --> A3
    end

    subgraph "Service Layer"
        S1[GraphitiService]
        S2[QueueService]
        S1 -.manages.-> S2
    end

    subgraph "Factory Layer"
        F1[LLMClientFactory]
        F2[EmbedderFactory]
        F3[DatabaseDriverFactory]
    end

    subgraph "Configuration Layer"
        C1[GraphitiConfig]
        C2[YamlSettingsSource]
        C3[Environment Variables]
        C4[YAML Config Files]
        C1 --> C2
        C2 --> C3
        C2 --> C4
    end

    subgraph "Data Models Layer"
        M1[Response Types]
        M2[Entity Types]
        M3[Config Schemas]
    end

    subgraph "Utilities Layer"
        U1[Formatting Utils]
        U2[Azure Utils]
    end

    subgraph "External Services"
        E1[Graphiti Core Client]
        E2[LLM Providers]
        E3[Embedder Providers]
        E4[Graph Database]
        E1 --> E2
        E1 --> E3
        E1 --> E4
    end

    A2 --> S1
    A2 --> S2
    S1 --> F1
    S1 --> F2
    S1 --> F3
    F1 --> C1
    F2 --> C1
    F3 --> C1
    S1 --> E1
    A2 --> M1
    S1 --> M2
    F1 --> U2
    A2 --> U1

    style A1 fill:#e1f5ff
    style S1 fill:#fff4e6
    style F1 fill:#f3e5f5
    style F2 fill:#f3e5f5
    style F3 fill:#f3e5f5
    style C1 fill:#e8f5e9
    style E1 fill:#fce4ec
```

### Explanation

**API Layer** (`src/server.py`, `src/graphiti_mcp_server.py`)
- Exposes MCP tools for knowledge graph operations
- Handles HTTP/stdio transport and custom routes
- Implements tool registration via closure pattern
- File: `src/server.py` (Lines 230-455)

**Service Layer** (`src/server.py:88-168`, `src/services/queue_service.py`)
- **GraphitiService**: Manages Graphiti client lifecycle, initialization, and provider setup
- **QueueService**: Handles sequential episode processing with per-group_id queues
- Provides business logic abstraction from API layer
- Files:
  - `src/server.py` (Lines 88-168)
  - `src/services/queue_service.py`

**Factory Layer** (`src/services/factories.py`)
- **LLMClientFactory**: Creates LLM clients (OpenAI, Azure, Anthropic, Gemini, Groq)
- **EmbedderFactory**: Creates embedder clients (OpenAI, Azure, Gemini, Voyage)
- **DatabaseDriverFactory**: Creates database configs (Neo4j, FalkorDB)
- Enables provider abstraction and dependency injection
- File: `src/services/factories.py` (Lines 100-440)

**Configuration Layer** (`src/config/schema.py`)
- Hierarchical configuration: CLI > ENV > YAML > Defaults
- Environment variable expansion in YAML files
- Provider-specific configuration classes
- File: `src/config/schema.py` (Lines 1-293)

**Data Models Layer** (`src/models/`)
- Response types for MCP tool outputs (TypedDict)
- Entity types for knowledge extraction (Pydantic)
- Configuration schemas (Pydantic BaseSettings)
- Files:
  - `src/models/response_types.py`
  - `src/models/entity_types.py`

**Utilities Layer** (`src/utils/`)
- Formatting utilities for nodes and edges
- Azure AD credential providers
- Files:
  - `src/utils/formatting.py`
  - `src/utils/utils.py`

**External Services**
- **Graphiti Core**: Knowledge graph library
- **LLM Providers**: OpenAI, Azure OpenAI, Anthropic, Gemini, Groq
- **Embedder Providers**: OpenAI, Azure OpenAI, Gemini, Voyage
- **Graph Databases**: FalkorDB (Redis-based), Neo4j

---

## Component Relationships

### Diagram

```mermaid
graph LR
    subgraph "Entry Points"
        E1[main.py]
        E2[server.py::create_server]
        E3[graphiti_mcp_server.py::main]
    end

    subgraph "Core Components"
        C1[GraphitiConfig]
        C2[GraphitiService]
        C3[QueueService]
        C4[FastMCP Server]
    end

    subgraph "Factory Components"
        F1[LLMClientFactory]
        F2[EmbedderFactory]
        F3[DatabaseDriverFactory]
    end

    subgraph "External Integration"
        I1[Graphiti Client]
        I2[LLM Client]
        I3[Embedder Client]
        I4[Database Driver]
    end

    E1 -.legacy wrapper.-> E3
    E2 -.factory pattern.-> C1
    E3 -.legacy pattern.-> C1

    E2 --> C2
    E2 --> C3
    E2 --> C4

    C1 --> F1
    C1 --> F2
    C1 --> F3

    C2 --> F1
    C2 --> F2
    C2 --> F3

    F1 --> I2
    F2 --> I3
    F3 --> I4

    C2 --> I1
    I1 --> I2
    I1 --> I3
    I1 --> I4

    C3 --> I1
    C4 --> C2
    C4 --> C3

    style E2 fill:#e1f5ff
    style C2 fill:#fff4e6
    style F1 fill:#f3e5f5
    style F2 fill:#f3e5f5
    style F3 fill:#f3e5f5
    style I1 fill:#fce4ec
```

### Explanation

**Entry Point Relationships:**
- `main.py` is a backward-compatible wrapper delegating to `graphiti_mcp_server.py`
- `server.py::create_server()` is the modern factory-based entry point for FastMCP Cloud
- `graphiti_mcp_server.py::main()` is the legacy entry point with global state

**Configuration Flow:**
- GraphitiConfig loads from YAML files and environment variables
- Configuration is passed to factory classes for client creation
- Factory classes create concrete provider implementations

**Service Dependencies:**
- GraphitiService uses factories to create LLM, embedder, and database clients
- GraphitiService initializes the Graphiti Core client
- QueueService depends on initialized Graphiti client for episode processing
- FastMCP Server uses closures to capture service instances in tool functions

**Client Creation Flow:**
```
GraphitiConfig -> Factory Classes -> Provider Clients -> Graphiti Client
```

**Request Processing Flow:**
```
MCP Client -> FastMCP Server -> MCP Tool -> GraphitiService/QueueService -> Graphiti Client -> Database
```

---

## Class Hierarchies

### Diagram

```mermaid
classDiagram
    class BaseSettings {
        <<Pydantic>>
        +model_config
        +settings_customise_sources()
    }

    class GraphitiConfig {
        +ServerConfig server
        +LLMConfig llm
        +EmbedderConfig embedder
        +DatabaseConfig database
        +GraphitiAppConfig graphiti
        +bool destroy_graph
        +apply_cli_overrides(args)
    }

    class BaseModel {
        <<Pydantic>>
        +model_dump()
        +model_validate()
    }

    class ServerConfig {
        +str transport
        +str host
        +int port
    }

    class LLMConfig {
        +str provider
        +str model
        +float temperature
        +int max_tokens
        +LLMProvidersConfig providers
    }

    class EmbedderConfig {
        +str provider
        +str model
        +int dimensions
        +EmbedderProvidersConfig providers
    }

    class DatabaseConfig {
        +str provider
        +DatabaseProvidersConfig providers
    }

    class GraphitiAppConfig {
        +str group_id
        +str episode_id_prefix
        +str user_id
        +list~EntityTypeConfig~ entity_types
    }

    class GraphitiService {
        -GraphitiConfig config
        -int semaphore_limit
        -Semaphore semaphore
        -Graphiti client
        -dict entity_types
        +initialize()
        +get_client()
    }

    class QueueService {
        -dict~str,Queue~ _episode_queues
        -dict~str,bool~ _queue_workers
        -Any _graphiti_client
        +initialize(client)
        +add_episode(...)
        +add_episode_task(group_id, func)
        +get_queue_size(group_id)
        +is_worker_running(group_id)
        -_process_episode_queue(group_id)
    }

    class LLMClientFactory {
        <<Factory>>
        +create(config)$ LLMClient
    }

    class EmbedderFactory {
        <<Factory>>
        +create(config)$ EmbedderClient
    }

    class DatabaseDriverFactory {
        <<Factory>>
        +create_config(config)$ dict
    }

    class EntityTypeConfig {
        +str name
        +str description
    }

    class Requirement {
        +str project_name
        +str description
    }

    class Preference {
        ...
    }

    class Procedure {
        +str description
    }

    class Location {
        +str name
        +str description
    }

    class Event {
        +str name
        +str description
    }

    class Organization {
        +str name
        +str description
    }

    class Document {
        +str title
        +str description
    }

    BaseSettings <|-- GraphitiConfig
    BaseModel <|-- ServerConfig
    BaseModel <|-- LLMConfig
    BaseModel <|-- EmbedderConfig
    BaseModel <|-- DatabaseConfig
    BaseModel <|-- GraphitiAppConfig
    BaseModel <|-- EntityTypeConfig
    BaseModel <|-- Requirement
    BaseModel <|-- Preference
    BaseModel <|-- Procedure
    BaseModel <|-- Location
    BaseModel <|-- Event
    BaseModel <|-- Organization
    BaseModel <|-- Document

    GraphitiConfig *-- ServerConfig
    GraphitiConfig *-- LLMConfig
    GraphitiConfig *-- EmbedderConfig
    GraphitiConfig *-- DatabaseConfig
    GraphitiConfig *-- GraphitiAppConfig
    GraphitiAppConfig *-- EntityTypeConfig

    GraphitiService --> GraphitiConfig
    GraphitiService --> LLMClientFactory
    GraphitiService --> EmbedderFactory
    GraphitiService --> DatabaseDriverFactory

    QueueService --> GraphitiService
```

### Explanation

**Configuration Hierarchy:**
- `GraphitiConfig` extends Pydantic `BaseSettings` for environment variable support
- Nested configuration classes extend `BaseModel` for validation
- Composition pattern: GraphitiConfig contains ServerConfig, LLMConfig, EmbedderConfig, etc.
- File: `src/config/schema.py` (Lines 230-293)

**Service Classes:**
- `GraphitiService`: Manages Graphiti client lifecycle, uses factories for initialization
- `QueueService`: Independent service for queue management, depends on Graphiti client
- Both services use dependency injection pattern
- Files:
  - `src/server.py` (Lines 88-168)
  - `src/services/queue_service.py` (Lines 12-153)

**Factory Pattern:**
- Static factory methods for creating provider-specific clients
- Each factory handles multiple provider types via match/case
- File: `src/services/factories.py` (Lines 100-440)

**Entity Type Models:**
- All entity types inherit from Pydantic `BaseModel`
- Used for custom knowledge extraction in Graphiti
- Defines schema for structured entity extraction
- File: `src/models/entity_types.py` (Lines 6-225)

**Inheritance Patterns:**
- Configuration classes use composition over inheritance
- Entity types use inheritance for base Pydantic functionality
- Factory classes use static methods (no inheritance)

---

## Module Dependencies

### Diagram

```mermaid
graph TD
    subgraph "Entry Points"
        M1[main.py]
        M2[src/server.py]
        M3[src/graphiti_mcp_server.py]
    end

    subgraph "Configuration"
        C1[src/config/schema.py]
    end

    subgraph "Services"
        S1[src/services/factories.py]
        S2[src/services/queue_service.py]
    end

    subgraph "Models"
        D1[src/models/response_types.py]
        D2[src/models/entity_types.py]
    end

    subgraph "Utilities"
        U1[src/utils/formatting.py]
        U2[src/utils/utils.py]
    end

    subgraph "External Libraries"
        E1[fastmcp]
        E2[graphiti_core]
        E3[pydantic]
        E4[dotenv]
        E5[asyncio]
    end

    M1 --> M3
    M2 --> C1
    M2 --> D1
    M2 --> S1
    M2 --> S2
    M2 --> U1
    M2 --> E1
    M2 --> E2

    M3 --> C1
    M3 --> D1
    M3 --> S1
    M3 --> S2
    M3 --> U1
    M3 --> E1
    M3 --> E2

    S1 --> C1
    S1 --> U2

    S2 --> E5

    C1 --> E3
    C1 --> E4

    D1 --> E3
    D2 --> E3

    U1 --> E2

    style M2 fill:#e1f5ff
    style C1 fill:#e8f5e9
    style S1 fill:#f3e5f5
    style S2 fill:#f3e5f5
    style E1 fill:#ffebee
    style E2 fill:#ffebee
```

### Explanation

**Entry Point Dependencies:**
- `main.py` only imports `graphiti_mcp_server` for backward compatibility
- `src/server.py` imports config, models, services, and utilities (modern approach)
- `src/graphiti_mcp_server.py` has similar imports (legacy approach)

**Core Module Import Structure:**

**Configuration Module** (`src/config/schema.py`):
- Depends on: `pydantic`, `pydantic_settings`, `yaml`, `pathlib`, `os`
- Provides: Configuration schemas used throughout the application
- No internal dependencies (leaf module in dependency tree)

**Factory Module** (`src/services/factories.py`):
- Imports: `config.schema` (GraphitiConfig and provider configs)
- Imports: `utils.utils` (Azure credential helpers)
- Conditional imports: Graphiti Core provider clients
- Provides: Factory classes for LLM, Embedder, Database client creation

**Queue Service Module** (`src/services/queue_service.py`):
- Imports: `asyncio`, `logging`, `datetime`
- No internal module dependencies
- Provides: Queue management for episode processing

**Models Modules** (`src/models/`):
- `response_types.py`: Depends on `typing_extensions` for TypedDict
- `entity_types.py`: Depends on `pydantic` for BaseModel
- Both are leaf modules with no internal dependencies

**Utilities Modules** (`src/utils/`):
- `formatting.py`: Imports `graphiti_core.edges`, `graphiti_core.nodes`
- `utils.py`: Imports `azure.identity` conditionally
- Minimal internal dependencies

**External Library Dependencies:**
- **FastMCP**: Server framework for MCP protocol
- **Graphiti Core**: Knowledge graph library (main integration)
- **Pydantic**: Data validation and settings management
- **AsyncIO**: Asynchronous operation support
- **dotenv**: Environment variable loading

**Dependency Injection Pattern:**
```
server.py → services (factories, queue) → config → external providers
```

**Import Hierarchy (least to most dependent):**
1. Models (no internal imports)
2. Config (imports only external libraries)
3. Utilities (minimal imports)
4. Services (import config, utils)
5. Server modules (import everything)

---

## Data Flow

### Diagram

```mermaid
sequenceDiagram
    participant Client as MCP Client
    participant Server as FastMCP Server
    participant Tool as MCP Tool (add_memory)
    participant Queue as QueueService
    participant Graphiti as GraphitiService
    participant Factory as ClientFactory
    participant Core as Graphiti Core
    participant DB as Graph Database

    Note over Client,DB: Initialization Flow
    Server->>Graphiti: initialize()
    Graphiti->>Factory: create LLM client
    Factory-->>Graphiti: LLM client
    Graphiti->>Factory: create Embedder client
    Factory-->>Graphiti: Embedder client
    Graphiti->>Factory: create DB config
    Factory-->>Graphiti: DB config
    Graphiti->>Core: Graphiti(llm, embedder, db)
    Core-->>Graphiti: client instance
    Graphiti->>Queue: initialize(client)

    Note over Client,DB: Episode Addition Flow
    Client->>Server: add_memory(name, content, group_id)
    Server->>Tool: route request
    Tool->>Queue: add_episode(params)
    Queue->>Queue: queue episode task
    Queue-->>Tool: queue position
    Tool-->>Server: SuccessResponse
    Server-->>Client: response

    Note over Queue,DB: Background Processing
    Queue->>Queue: _process_episode_queue()
    Queue->>Core: add_episode(content)
    Core->>Core: extract entities
    Core->>Core: create embeddings
    Core->>Core: deduplicate entities
    Core->>Core: extract relationships
    Core->>DB: write nodes & edges
    DB-->>Core: success
    Core-->>Queue: episode processed

    Note over Client,DB: Search Flow
    Client->>Server: search_nodes(query)
    Server->>Tool: route request
    Tool->>Graphiti: get_client()
    Graphiti-->>Tool: client
    Tool->>Core: search_(query, config)
    Core->>DB: hybrid search query
    DB-->>Core: matching nodes
    Core-->>Tool: search results
    Tool->>Tool: format results
    Tool-->>Server: NodeSearchResponse
    Server-->>Client: response
```

### Explanation

**Initialization Flow** (`src/server.py:173-219`):
1. `create_server()` factory loads GraphitiConfig from environment/YAML
2. GraphitiService uses factories to create LLM, Embedder, and Database clients
3. Factories handle provider-specific initialization (OpenAI, Azure, Anthropic, etc.)
4. GraphitiService creates Graphiti Core client with all providers
5. QueueService is initialized with Graphiti client
6. FastMCP server is created and tools are registered
7. File: `src/server.py` (Lines 173-219)

**Episode Addition Flow** (`src/server.py:231-266`):
1. MCP client calls `add_memory` tool with episode data
2. Tool validates source type and sets effective group_id
3. Episode is queued via QueueService.add_episode()
4. QueueService creates background task if needed
5. Immediate response returned to client (async processing)
6. Background worker processes episode sequentially per group_id
7. File: `src/server.py` (Lines 231-266)

**Background Episode Processing** (`src/services/queue_service.py:128-152`):
1. Background worker retrieves queued task
2. Calls Graphiti Core add_episode() method
3. Graphiti extracts entities using LLM
4. Entities are embedded using embedder client
5. Deduplication and relationship extraction occur
6. Nodes and edges written to graph database
7. Worker marks task complete and processes next
8. File: `src/services/queue_service.py` (Lines 128-152)

**Search Flow** (`src/server.py:268-312`):
1. MCP client calls `search_nodes` with natural language query
2. Tool retrieves initialized Graphiti client
3. Search filters created for entity types
4. Hybrid search (vector + keyword) executed
5. Database returns matching nodes with relevance scores
6. Results formatted and returned to client
7. File: `src/server.py` (Lines 268-312)

**Configuration Flow** (`src/config/schema.py:249-262`):
```
YAML File -> YamlSettingsSource -> Environment Variable Expansion
    -> Pydantic Validation -> GraphitiConfig Instance
    -> Provider-Specific Configs -> Factory Classes
```

**Error Handling:**
- Factory methods validate API keys and provider availability
- Service methods catch exceptions and return ErrorResponse
- Queue processing logs errors but continues with next task
- Background workers have CancelledError handling

**Data Transformation:**
- Input: Raw text/JSON/messages from MCP client
- Processing: Entity extraction, embedding generation
- Storage: Graph nodes (entities) and edges (relationships)
- Output: Formatted search results with metadata

---

## Deployment Patterns

### Diagram

```mermaid
graph TB
    subgraph "FastMCP Cloud Deployment"
        FC1[FastMCP Cloud Platform]
        FC2[Environment Variables]
        FC3[create_server Factory]
        FC4[FastMCP Server Instance]

        FC1 --> FC2
        FC2 --> FC3
        FC3 --> FC4
    end

    subgraph "Local Development"
        LD1[main.py / server.py]
        LD2[YAML Config + .env]
        LD3[CLI Arguments]
        LD4[Config Merger]
        LD5[Server Instance]

        LD1 --> LD2
        LD1 --> LD3
        LD2 --> LD4
        LD3 --> LD4
        LD4 --> LD5
    end

    subgraph "Legacy Deployment"
        LG1[graphiti_mcp_server.py]
        LG2[Global State]
        LG3[initialize_server]
        LG4[Server Instance]

        LG1 --> LG2
        LG1 --> LG3
        LG3 --> LG4
    end

    subgraph "Shared Components"
        SC1[GraphitiService]
        SC2[QueueService]
        SC3[Factory Classes]
        SC4[Graphiti Core Client]
    end

    FC4 --> SC1
    FC4 --> SC2
    LD5 --> SC1
    LD5 --> SC2
    LG4 --> SC1
    LG4 --> SC2

    SC1 --> SC3
    SC1 --> SC4
    SC2 --> SC4

    style FC3 fill:#e1f5ff
    style LD4 fill:#fff4e6
    style LG3 fill:#ffebee
    style SC1 fill:#f3e5f5
```

### Explanation

**FastMCP Cloud Deployment** (Recommended):
- Entry: `src/server.py::create_server()` async factory function
- Configuration: Environment variables only (no CLI args)
- Pattern: Factory pattern with dependency injection
- Initialization: All services initialized before server creation
- File: `src/server.py` (Lines 173-219)

**Local Development Deployment**:
- Entry: `main.py` or `python src/server.py`
- Configuration: YAML files + .env + optional CLI overrides
- Pattern: Same factory pattern as cloud
- Flexibility: Supports transport selection (http/stdio)
- File: `src/server.py` (Lines 461-495)

**Legacy Deployment** (Backward Compatibility):
- Entry: `src/graphiti_mcp_server.py::main()`
- Configuration: Full CLI argument parsing + YAML + .env
- Pattern: Global state variables
- Purpose: Maintains compatibility with existing scripts
- File: `src/graphiti_mcp_server.py`

**Configuration Priority** (All Patterns):
```
CLI Arguments > Environment Variables > YAML Config > Defaults
```

**Shared Service Layer**:
- All deployment patterns use the same GraphitiService and QueueService
- Factory classes ensure consistent client creation
- Services are provider-agnostic

**Key Differences**:
- **Cloud**: No file system access, env vars only, factory pattern
- **Local**: File access, multiple config sources, same factory pattern
- **Legacy**: File access, global state, comprehensive CLI args

