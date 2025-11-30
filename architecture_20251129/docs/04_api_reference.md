# API Reference

## Overview

Graphiti-FastMCP exposes a knowledge graph memory service for AI agents through the Model Context Protocol (MCP). The API provides tools for adding episodes (memories), searching for entities and relationships, managing the graph, and querying server status.

**API Surface:**
- 10 MCP Tools (primary API)
- 1 HTTP endpoint (/health)
- 3 Service classes (GraphitiService, QueueService, factories)
- Configuration system with YAML/environment support
- 9 predefined entity types
- Support for 5 LLM providers, 4 embedder providers, 2 database backends

**Key Features:**
- Asynchronous queue-based processing for memory addition
- Hybrid search combining semantic similarity and keyword matching
- Multi-provider support with factory pattern
- Lazy initialization for optimal startup
- Type-safe responses using TypedDict

---

## MCP Tools API

### add_memory

Add an episode to memory. This is the primary way to add information to the knowledge graph.

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

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| name | str | Yes | - | Name of the episode |
| episode_body | str | Yes | - | The content to persist to memory. For source='json', must be a properly escaped JSON string |
| group_id | str | No | config default | Unique ID for this graph namespace. Allows separate knowledge domains |
| source | str | No | 'text' | Source type: 'text', 'json', or 'message' |
| source_description | str | No | '' | Description of the source (e.g., "news article", "CRM data") |
| uuid | str | No | None | Optional UUID for the episode |

**Returns:**
- `SuccessResponse`: `{"message": "Episode 'X' queued for processing in group 'Y'"}`
- `ErrorResponse`: `{"error": "error description"}`

**Behavior:**
- Returns immediately after queuing (asynchronous processing)
- Episodes for the same group_id are processed sequentially
- Processing involves LLM-based entity extraction and embedding generation
- Episodes are stored as nodes in the graph with relationships to extracted entities

**Examples:**

```python
# Adding plain text content
result = await add_memory(
    name="Company News",
    episode_body="Acme Corp announced a new product line today.",
    source="text",
    source_description="news article",
    group_id="company_updates"
)
# Returns: {"message": "Episode 'Company News' queued for processing in group 'company_updates'"}

# Adding structured JSON data
result = await add_memory(
    name="Customer Profile",
    episode_body='{"company": {"name": "Acme Technologies"}, "products": [{"id": "P001", "name": "CloudSync"}]}',
    source="json",
    source_description="CRM data",
    group_id="customers"
)

# Adding conversation messages
result = await add_memory(
    name="User Interaction",
    episode_body="User: I prefer dark mode\nAssistant: I'll remember that preference.",
    source="message",
    group_id="user_123"
)
```

**Source:** `src/graphiti_mcp_server.py:324-407`

**Notes:**
- Processing happens asynchronously in the background
- LLM calls are made during processing for entity extraction
- Embeddings are generated for entities and relationships
- Use descriptive names and detailed content for better search quality

---

### search_nodes

Search for nodes (entities) in the graph memory using hybrid search.

**Signature:**
```python
async def search_nodes(
    query: str,
    group_ids: list[str] | None = None,
    max_nodes: int = 10,
    entity_types: list[str] | None = None,
) -> NodeSearchResponse | ErrorResponse
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | str | Yes | - | Natural language search query |
| group_ids | list[str] | No | [config default] | List of group IDs to search within |
| max_nodes | int | No | 10 | Maximum number of nodes to return |
| entity_types | list[str] | No | None | Filter by entity type names (e.g., ['Preference', 'Organization']) |

**Returns:**
- `NodeSearchResponse`: `{"message": str, "nodes": [NodeResult, ...]}`
- `ErrorResponse`: `{"error": "error description"}`

**NodeResult Structure:**
```python
{
    "uuid": str,
    "name": str,
    "labels": list[str],  # Entity types
    "created_at": str | None,  # ISO 8601 format
    "summary": str | None,
    "group_id": str,
    "attributes": dict[str, Any]  # Excludes embeddings
}
```

**Examples:**

```python
# Basic search
result = await search_nodes(
    query="user preferences about UI",
    max_nodes=5
)

# Filtered search by entity type
result = await search_nodes(
    query="software companies",
    entity_types=["Organization"],
    max_nodes=10
)

# Multi-group search
result = await search_nodes(
    query="recent events",
    group_ids=["project_a", "project_b"],
    entity_types=["Event"],
    max_nodes=20
)
```

**Source:** `src/graphiti_mcp_server.py:410-487`

**Implementation Details:**
- Uses Reciprocal Rank Fusion (RRF) for hybrid search
- Combines semantic similarity (embeddings) with keyword matching
- Embeddings are stripped from results to reduce payload size
- Search is performed using `NODE_HYBRID_SEARCH_RRF` configuration

---

### search_memory_facts

Search for relevant facts (relationships between entities) in the graph.

**Signature:**
```python
async def search_memory_facts(
    query: str,
    group_ids: list[str] | None = None,
    max_facts: int = 10,
    center_node_uuid: str | None = None,
) -> FactSearchResponse | ErrorResponse
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| query | str | Yes | - | Natural language search query |
| group_ids | list[str] | No | [config default] | List of group IDs to search within |
| max_facts | int | No | 10 | Maximum number of facts to return (must be > 0) |
| center_node_uuid | str | No | None | UUID of a node to center the search around |

**Returns:**
- `FactSearchResponse`: `{"message": str, "facts": [dict, ...]}`
- `ErrorResponse`: `{"error": "error description"}`

**Fact Structure:**
```python
{
    "uuid": str,
    "source_node_uuid": str,
    "target_node_uuid": str,
    "name": str,  # Relationship type/description
    "fact": str,  # Full fact description
    "created_at": str,  # ISO 8601 format
    "expired_at": str | None,  # ISO 8601 format if fact is superseded
    "valid_at": str,  # ISO 8601 format
    "invalid_at": str | None,  # ISO 8601 format if fact became invalid
    "group_id": str,
    "attributes": dict[str, Any]  # Excludes embeddings
}
```

**Examples:**

```python
# Search for facts about preferences
result = await search_memory_facts(
    query="what does the user prefer for UI settings",
    max_facts=5
)

# Search facts around a specific node
result = await search_memory_facts(
    query="relationships",
    center_node_uuid="abc-123-def-456",
    max_facts=10
)

# Multi-group fact search
result = await search_memory_facts(
    query="organizational relationships",
    group_ids=["company_data", "partners"],
    max_facts=15
)
```

**Source:** `src/graphiti_mcp_server.py:490-541`

**Implementation Details:**
- Returns EntityEdge objects formatted as dictionaries
- Temporal metadata tracks when facts were created and if they're still valid
- center_node_uuid filters facts connected to a specific entity
- Embeddings are excluded from response

---

### get_entity_edge

Retrieve a specific entity edge (fact) by its UUID.

**Signature:**
```python
async def get_entity_edge(uuid: str) -> dict[str, Any] | ErrorResponse
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| uuid | str | Yes | - | UUID of the entity edge to retrieve |

**Returns:**
- `dict[str, Any]`: Formatted fact data (same structure as facts in search_memory_facts)
- `ErrorResponse`: `{"error": "Entity edge not found"}` or other error

**Example:**

```python
# Retrieve specific edge
result = await get_entity_edge(uuid="edge-uuid-123")

# Result structure:
# {
#     "uuid": "edge-uuid-123",
#     "source_node_uuid": "node-abc",
#     "target_node_uuid": "node-def",
#     "name": "prefers",
#     "fact": "User prefers dark mode over light mode",
#     "created_at": "2025-11-29T10:30:00Z",
#     ...
# }
```

**Source:** `src/graphiti_mcp_server.py:596-620`

---

### get_episodes

Retrieve episodes from the graph memory.

**Signature:**
```python
async def get_episodes(
    group_ids: list[str] | None = None,
    max_episodes: int = 10,
) -> EpisodeSearchResponse | ErrorResponse
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| group_ids | list[str] | No | [config default] | List of group IDs to retrieve episodes from |
| max_episodes | int | No | 10 | Maximum number of episodes to return |

**Returns:**
- `EpisodeSearchResponse`: `{"message": str, "episodes": [dict, ...]}`
- `ErrorResponse`: `{"error": "error description"}`

**Episode Structure:**
```python
{
    "uuid": str,
    "name": str,
    "content": str,
    "created_at": str,  # ISO 8601 format
    "source": str,  # 'text', 'json', or 'message'
    "source_description": str,
    "group_id": str
}
```

**Examples:**

```python
# Get recent episodes
result = await get_episodes(max_episodes=20)

# Get episodes from specific groups
result = await get_episodes(
    group_ids=["user_interactions", "system_events"],
    max_episodes=50
)
```

**Source:** `src/graphiti_mcp_server.py:623-688`

---

### delete_entity_edge

Delete an entity edge (relationship) from the graph memory.

**Signature:**
```python
async def delete_entity_edge(uuid: str) -> SuccessResponse | ErrorResponse
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| uuid | str | Yes | - | UUID of the entity edge to delete |

**Returns:**
- `SuccessResponse`: `{"message": "Entity edge with UUID {uuid} deleted successfully"}`
- `ErrorResponse`: `{"error": "Entity edge not found"}` or other error

**Example:**

```python
result = await delete_entity_edge(uuid="edge-uuid-123")
```

**Source:** `src/graphiti_mcp_server.py:544-567`

**Warning:** Deletion is permanent and cannot be undone.

---

### delete_episode

Delete an episode from the graph memory.

**Signature:**
```python
async def delete_episode(uuid: str) -> SuccessResponse | ErrorResponse
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| uuid | str | Yes | - | UUID of the episode to delete |

**Returns:**
- `SuccessResponse`: `{"message": "Episode with UUID {uuid} deleted successfully"}`
- `ErrorResponse`: `{"error": "Episode not found"}` or other error

**Example:**

```python
result = await delete_episode(uuid="episode-uuid-456")
```

**Source:** `src/graphiti_mcp_server.py:570-593`

**Warning:** Deletion is permanent and cannot be undone.

---

### clear_graph

Clear all data from the graph for specified group IDs.

**Signature:**
```python
async def clear_graph(group_ids: list[str] | None = None) -> SuccessResponse | ErrorResponse
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| group_ids | list[str] | No | [config default] | List of group IDs to clear. If not provided, clears the default group |

**Returns:**
- `SuccessResponse`: `{"message": "Graph data cleared successfully for group IDs: X, Y, Z"}`
- `ErrorResponse`: `{"error": "No group IDs specified for clearing"}` or other error

**Examples:**

```python
# Clear default group
result = await clear_graph()

# Clear specific groups
result = await clear_graph(group_ids=["test_data", "temporary"])

# Clear all user groups
result = await clear_graph(group_ids=["user_123", "user_456"])
```

**Source:** `src/graphiti_mcp_server.py:691-723`

**Warning:** This operation is destructive and cannot be undone. All episodes, entities, and relationships in the specified groups will be permanently deleted.

---

### get_status

Get the status of the Graphiti MCP server and database connection.

**Signature:**
```python
async def get_status() -> StatusResponse
```

**Parameters:** None

**Returns:**
- `StatusResponse`: `{"status": "ok" | "error", "message": str}`

**Examples:**

```python
result = await get_status()

# Success response:
# {
#     "status": "ok",
#     "message": "Graphiti MCP server is running and connected to falkordb database"
# }

# Error response:
# {
#     "status": "error",
#     "message": "Graphiti MCP server is running but database connection failed: connection refused"
# }
```

**Source:** `src/graphiti_mcp_server.py:726-756`

**Use Cases:**
- Health monitoring
- Pre-flight checks before operations
- Debugging connection issues

---

## HTTP Endpoints

### GET /health

Health check endpoint for Docker, Kubernetes, and load balancers.

**Signature:**
```python
async def health_check(request) -> JSONResponse
```

**Response:**
```json
{
    "status": "healthy",
    "service": "graphiti-mcp"
}
```

**HTTP Status:** 200 OK (always, even if database is unavailable)

**Example:**

```bash
curl http://localhost:8000/health
```

**Source:** `src/graphiti_mcp_server.py:759-762`

**Use Cases:**
- Container orchestration health probes
- Load balancer health checks
- Simple service availability verification

**Note:** This endpoint only checks if the HTTP server is running, not the database connection. Use `get_status()` MCP tool for comprehensive status.

---

## Service Classes

### GraphitiService

Main service class managing Graphiti client lifecycle and initialization.

**Source:** `src/graphiti_mcp_server.py:162-321`

#### Constructor

```python
def __init__(self, config: GraphitiConfig, semaphore_limit: int = 10)
```

**Parameters:**
- `config`: GraphitiConfig instance with all settings
- `semaphore_limit`: Maximum concurrent operations (default: 10)

**Attributes:**
- `config`: GraphitiConfig instance
- `client`: Graphiti client instance (None until initialized)
- `entity_types`: Custom entity types dictionary
- `semaphore`: Asyncio semaphore for rate limiting

**Example:**

```python
from config.schema import GraphitiConfig

config = GraphitiConfig()
service = GraphitiService(config, semaphore_limit=10)
await service.initialize()
```

#### initialize()

Initialize the Graphiti client with factory-created components.

**Signature:**
```python
async def initialize(self) -> None
```

**Raises:**
- `RuntimeError`: If database is not accessible (with helpful error message)
- `ValueError`: If provider configuration is invalid
- `Exception`: For other initialization errors

**Process:**
1. Creates LLM client using LLMClientFactory
2. Creates embedder client using EmbedderFactory
3. Creates database configuration using DatabaseDriverFactory
4. Builds custom entity types from configuration
5. Initializes Graphiti client with appropriate driver
6. Builds database indices and constraints

**Example:**

```python
try:
    await service.initialize()
except RuntimeError as e:
    print(f"Database not running: {e}")
except Exception as e:
    print(f"Initialization failed: {e}")
```

**Source:** Lines 172-312

**Error Messages:**
- FalkorDB not running: Provides docker-compose startup instructions
- Neo4j not running: Provides Neo4j Desktop and Docker instructions
- Missing API keys: Clear message about which environment variable to set

#### get_client()

Get the Graphiti client, initializing if necessary (lazy initialization).

**Signature:**
```python
async def get_client(self) -> Graphiti
```

**Returns:**
- `Graphiti`: Initialized Graphiti client instance

**Raises:**
- `RuntimeError`: If initialization fails

**Example:**

```python
client = await service.get_client()
# Use client for operations
results = await client.search(query="preferences", group_ids=["user_123"])
```

**Source:** Lines 314-320

**Note:** This method implements lazy initialization - the client is only created on first use, reducing startup time.

---

### QueueService

Service for managing sequential episode processing queues by group_id.

**Source:** `src/services/queue_service.py:12-153`

#### Constructor

```python
def __init__(self)
```

**Attributes:**
- `_episode_queues`: Dictionary of asyncio.Queue per group_id
- `_queue_workers`: Dictionary tracking worker status per group_id
- `_graphiti_client`: Graphiti client for processing

**Example:**

```python
queue_service = QueueService()
await queue_service.initialize(graphiti_client)
```

#### initialize()

Initialize the queue service with a Graphiti client.

**Signature:**
```python
async def initialize(self, graphiti_client: Any) -> None
```

**Parameters:**
- `graphiti_client`: The Graphiti client instance to use for processing episodes

**Example:**

```python
graphiti_client = await graphiti_service.get_client()
await queue_service.initialize(graphiti_client)
```

**Source:** Lines 92-99

#### add_episode()

Add an episode for processing.

**Signature:**
```python
async def add_episode(
    self,
    group_id: str,
    name: str,
    content: str,
    source_description: str,
    episode_type: Any,
    entity_types: Any,
    uuid: str | None,
) -> int
```

**Parameters:**
- `group_id`: The group ID for the episode
- `name`: Name of the episode
- `content`: Episode content (text, JSON, or message)
- `source_description`: Description of the episode source
- `episode_type`: EpisodeType enum value
- `entity_types`: Entity types for extraction (dict of Pydantic models)
- `uuid`: Episode UUID (optional)

**Returns:**
- `int`: Position in the queue

**Raises:**
- `RuntimeError`: If queue service not initialized

**Example:**

```python
from graphiti_core.nodes import EpisodeType

position = await queue_service.add_episode(
    group_id="user_123",
    name="User Preference",
    content="I prefer dark mode",
    source_description="chat message",
    episode_type=EpisodeType.text,
    entity_types=None,
    uuid=None
)
print(f"Episode queued at position {position}")
```

**Source:** Lines 101-152

**Behavior:**
- Creates async processing function
- Queues function for execution
- Returns immediately (does not wait for processing)
- Starts queue worker if not already running

#### get_queue_size()

Get the current queue size for a group_id.

**Signature:**
```python
def get_queue_size(self, group_id: str) -> int
```

**Returns:**
- `int`: Number of episodes waiting in queue (0 if queue doesn't exist)

**Example:**

```python
size = queue_service.get_queue_size("user_123")
print(f"{size} episodes waiting")
```

**Source:** Lines 82-86

#### is_worker_running()

Check if a worker is running for a group_id.

**Signature:**
```python
def is_worker_running(self, group_id: str) -> bool
```

**Returns:**
- `bool`: True if worker is active, False otherwise

**Example:**

```python
if queue_service.is_worker_running("user_123"):
    print("Worker is processing episodes")
```

**Source:** Lines 88-90

---

## Factory Classes

### LLMClientFactory

Factory for creating LLM clients based on configuration.

**Source:** `src/services/factories.py:100-251`

#### create()

Create an LLM client based on the configured provider.

**Signature:**
```python
@staticmethod
def create(config: LLMConfig) -> LLMClient
```

**Parameters:**
- `config`: LLMConfig instance with provider settings

**Returns:**
- `LLMClient`: Provider-specific LLM client instance

**Raises:**
- `ValueError`: If provider not configured or API key missing
- `ImportError`: If provider library not available in graphiti-core

**Supported Providers:**

| Provider | Model Examples | Special Features |
|----------|---------------|------------------|
| openai | gpt-4.1, gpt-4.1-mini, gpt-5, o1, o3 | Reasoning models support with verbosity controls |
| azure_openai | gpt-4, gpt-35-turbo | Azure AD authentication support |
| anthropic | claude-sonnet-4-5 | Max retries configuration |
| gemini | gemini-2.0-flash-exp | Project ID and location support |
| groq | llama-3.3-70b-versatile | Custom API URL |

**Examples:**

```python
from config.schema import LLMConfig, OpenAIProviderConfig, LLMProvidersConfig

# OpenAI
llm_config = LLMConfig(
    provider='openai',
    model='gpt-4.1',
    temperature=0.7,
    providers=LLMProvidersConfig(
        openai=OpenAIProviderConfig(api_key='sk-...')
    )
)
llm_client = LLMClientFactory.create(llm_config)

# Azure OpenAI with Managed Identity
azure_config = LLMConfig(
    provider='azure_openai',
    model='gpt-4',
    providers=LLMProvidersConfig(
        azure_openai=AzureOpenAIProviderConfig(
            api_url='https://myresource.openai.azure.com',
            deployment_name='gpt-4',
            use_azure_ad=True
        )
    )
)
llm_client = LLMClientFactory.create(azure_config)

# Anthropic
anthropic_config = LLMConfig(
    provider='anthropic',
    model='claude-sonnet-4-5',
    providers=LLMProvidersConfig(
        anthropic=AnthropicProviderConfig(api_key='sk-ant-...')
    )
)
llm_client = LLMClientFactory.create(anthropic_config)
```

**Source:** Lines 104-250

**Reasoning Models:**
- GPT-5, O1, O3 models automatically use reasoning mode
- Small model automatically selected: gpt-5-nano for reasoning, gpt-4.1-mini for standard
- Temperature may be ignored by reasoning models

---

### EmbedderFactory

Factory for creating Embedder clients based on configuration.

**Source:** `src/services/factories.py:253-361`

#### create()

Create an Embedder client based on the configured provider.

**Signature:**
```python
@staticmethod
def create(config: EmbedderConfig) -> EmbedderClient
```

**Parameters:**
- `config`: EmbedderConfig instance with provider settings

**Returns:**
- `EmbedderClient`: Provider-specific embedder client instance

**Raises:**
- `ValueError`: If provider not configured or API key missing
- `ImportError`: If provider library not available in graphiti-core

**Supported Providers:**

| Provider | Default Model | Dimensions | Notes |
|----------|--------------|------------|-------|
| openai | text-embedding-3-small | 1536 | Widely supported, good performance |
| azure_openai | text-embedding-3-small | 1536 | Azure AD authentication support |
| gemini | text-embedding-004 | 768 | Lower dimensions, good quality |
| voyage | voyage-3 | 1024 | Optimized for retrieval |

**Examples:**

```python
from config.schema import EmbedderConfig, EmbedderProvidersConfig, OpenAIProviderConfig

# OpenAI
embedder_config = EmbedderConfig(
    provider='openai',
    model='text-embedding-3-small',
    dimensions=1536,
    providers=EmbedderProvidersConfig(
        openai=OpenAIProviderConfig(api_key='sk-...')
    )
)
embedder = EmbedderFactory.create(embedder_config)

# Voyage AI
voyage_config = EmbedderConfig(
    provider='voyage',
    model='voyage-3',
    dimensions=1024,
    providers=EmbedderProvidersConfig(
        voyage=VoyageProviderConfig(api_key='pa-...')
    )
)
embedder = EmbedderFactory.create(voyage_config)

# Gemini
gemini_config = EmbedderConfig(
    provider='gemini',
    model='text-embedding-004',
    dimensions=768,
    providers=EmbedderProvidersConfig(
        gemini=GeminiProviderConfig(
            api_key='AI...',
            project_id='my-project',
            location='us-central1'
        )
    )
)
embedder = EmbedderFactory.create(gemini_config)
```

**Source:** Lines 257-360

---

### DatabaseDriverFactory

Factory for creating Database driver configurations.

**Source:** `src/services/factories.py:363-440`

#### create_config()

Create database configuration dictionary based on the configured provider.

**Signature:**
```python
@staticmethod
def create_config(config: DatabaseConfig) -> dict
```

**Parameters:**
- `config`: DatabaseConfig instance with provider settings

**Returns:**
- `dict`: Configuration dictionary for the database driver

**Raises:**
- `ValueError`: If provider not supported or configuration invalid
- `ImportError`: If driver library not available

**Supported Providers:**

| Provider | Default URI | Default Database | Notes |
|----------|------------|------------------|-------|
| neo4j | bolt://localhost:7687 | neo4j | Production-grade graph database |
| falkordb | redis://localhost:6379 | default_db | Redis-based graph database |

**Neo4j Configuration:**
```python
{
    'uri': str,           # bolt://host:port
    'user': str,          # Username
    'password': str       # Password
}
```

**FalkorDB Configuration:**
```python
{
    'driver': 'falkordb',
    'host': str,          # Hostname
    'port': int,          # Port (6379)
    'username': str,      # Username (optional)
    'password': str,      # Password (optional)
    'database': str       # Database name
}
```

**Examples:**

```python
from config.schema import DatabaseConfig, DatabaseProvidersConfig, Neo4jProviderConfig

# Neo4j
db_config = DatabaseConfig(
    provider='neo4j',
    providers=DatabaseProvidersConfig(
        neo4j=Neo4jProviderConfig(
            uri='bolt://localhost:7687',
            username='neo4j',
            password='password123'
        )
    )
)
config_dict = DatabaseDriverFactory.create_config(db_config)

# FalkorDB
falkor_config = DatabaseConfig(
    provider='falkordb',
    providers=DatabaseProvidersConfig(
        falkordb=FalkorDBProviderConfig(
            uri='redis://localhost:6379',
            database='my_graph'
        )
    )
)
config_dict = DatabaseDriverFactory.create_config(falkor_config)
```

**Source:** Lines 371-439

**Environment Variables:**
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` override Neo4j config
- `FALKORDB_URI`, `FALKORDB_USER`, `FALKORDB_PASSWORD` override FalkorDB config

---

## Configuration

### GraphitiConfig Class

Main configuration class with YAML and environment variable support.

**Source:** `src/config/schema.py:230-293`

**Structure:**

```python
class GraphitiConfig(BaseSettings):
    server: ServerConfig
    llm: LLMConfig
    embedder: EmbedderConfig
    database: DatabaseConfig
    graphiti: GraphitiAppConfig
    destroy_graph: bool
```

**Configuration Sources (Priority Order):**
1. CLI arguments (highest priority)
2. Environment variables
3. YAML configuration file
4. .env file
5. Default values (lowest priority)

**Example YAML Configuration:**

```yaml
# config/config.yaml
server:
  transport: http
  host: 0.0.0.0
  port: 8000

llm:
  provider: openai
  model: gpt-4.1
  temperature: 0.7
  max_tokens: 4096
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}

embedder:
  provider: openai
  model: text-embedding-3-small
  dimensions: 1536
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}

database:
  provider: falkordb
  providers:
    falkordb:
      uri: redis://localhost:6379
      database: graphiti_db

graphiti:
  group_id: main
  user_id: mcp_user
  entity_types:
    - name: Preference
      description: User preferences and choices
    - name: Requirement
      description: Project requirements and features
```

**Example Environment Variables:**

```bash
# Server
SERVER__TRANSPORT=http
SERVER__HOST=0.0.0.0
SERVER__PORT=8000

# LLM
LLM__PROVIDER=openai
LLM__MODEL=gpt-4.1
LLM__PROVIDERS__OPENAI__API_KEY=sk-...

# Embedder
EMBEDDER__PROVIDER=openai
EMBEDDER__MODEL=text-embedding-3-small
EMBEDDER__PROVIDERS__OPENAI__API_KEY=sk-...

# Database
DATABASE__PROVIDER=falkordb
DATABASE__PROVIDERS__FALKORDB__URI=redis://localhost:6379

# Graphiti
GRAPHITI__GROUP_ID=main
GRAPHITI__USER_ID=mcp_user

# Advanced
SEMAPHORE_LIMIT=10
```

**Environment Variable Expansion in YAML:**

```yaml
# Use ${VAR} or ${VAR:default} syntax
llm:
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}  # Required
      api_url: ${OPENAI_API_URL:https://api.openai.com/v1}  # With default
    azure_openai:
      use_azure_ad: ${USE_AZURE_AD:false}  # Boolean conversion
```

**Loading Configuration:**

```python
import os
from pathlib import Path
from config.schema import GraphitiConfig

# Set config path
os.environ['CONFIG_PATH'] = '/path/to/config.yaml'

# Load configuration
config = GraphitiConfig()

# Access settings
print(config.llm.provider)
print(config.llm.model)
print(config.server.port)
```

**Applying CLI Overrides:**

```python
import argparse

parser = argparse.ArgumentParser()
parser.add_argument('--llm-provider', choices=['openai', 'anthropic'])
parser.add_argument('--model')
args = parser.parse_args()

config = GraphitiConfig()
config.apply_cli_overrides(args)
```

**Source:** Lines 230-293

---

### Environment Variables Reference

Complete list of environment variables supported:

**Server Configuration:**
- `SERVER__TRANSPORT`: Transport type (http, stdio, sse)
- `SERVER__HOST`: Server host (default: 0.0.0.0)
- `SERVER__PORT`: Server port (default: 8000)

**LLM Configuration:**
- `LLM__PROVIDER`: LLM provider (openai, azure_openai, anthropic, gemini, groq)
- `LLM__MODEL`: Model name
- `LLM__TEMPERATURE`: Temperature (0.0-2.0)
- `LLM__MAX_TOKENS`: Max tokens (default: 4096)
- `LLM__PROVIDERS__OPENAI__API_KEY`: OpenAI API key
- `LLM__PROVIDERS__OPENAI__API_URL`: OpenAI API URL
- `LLM__PROVIDERS__AZURE_OPENAI__API_KEY`: Azure OpenAI API key
- `LLM__PROVIDERS__AZURE_OPENAI__API_URL`: Azure OpenAI endpoint
- `LLM__PROVIDERS__AZURE_OPENAI__DEPLOYMENT_NAME`: Azure deployment name
- `LLM__PROVIDERS__AZURE_OPENAI__USE_AZURE_AD`: Use Azure AD auth (true/false)
- `LLM__PROVIDERS__ANTHROPIC__API_KEY`: Anthropic API key
- `LLM__PROVIDERS__GEMINI__API_KEY`: Gemini API key
- `LLM__PROVIDERS__GEMINI__PROJECT_ID`: GCP project ID
- `LLM__PROVIDERS__GROQ__API_KEY`: Groq API key

**Embedder Configuration:**
- `EMBEDDER__PROVIDER`: Embedder provider (openai, azure_openai, gemini, voyage)
- `EMBEDDER__MODEL`: Embedder model name
- `EMBEDDER__DIMENSIONS`: Embedding dimensions
- `EMBEDDER__PROVIDERS__OPENAI__API_KEY`: OpenAI API key
- `EMBEDDER__PROVIDERS__AZURE_OPENAI__API_KEY`: Azure OpenAI API key
- `EMBEDDER__PROVIDERS__GEMINI__API_KEY`: Gemini API key
- `EMBEDDER__PROVIDERS__VOYAGE__API_KEY`: Voyage API key

**Database Configuration:**
- `DATABASE__PROVIDER`: Database provider (neo4j, falkordb)
- `DATABASE__PROVIDERS__NEO4J__URI`: Neo4j URI
- `DATABASE__PROVIDERS__NEO4J__USERNAME`: Neo4j username
- `DATABASE__PROVIDERS__NEO4J__PASSWORD`: Neo4j password
- `DATABASE__PROVIDERS__FALKORDB__URI`: FalkorDB URI
- `DATABASE__PROVIDERS__FALKORDB__USERNAME`: FalkorDB username
- `DATABASE__PROVIDERS__FALKORDB__PASSWORD`: FalkorDB password

**Graphiti Configuration:**
- `GRAPHITI__GROUP_ID`: Default group ID
- `GRAPHITI__USER_ID`: User ID for operations
- `GRAPHITI__EPISODE_ID_PREFIX`: Prefix for episode IDs

**Advanced:**
- `SEMAPHORE_LIMIT`: Concurrent operation limit (default: 10)
- `CONFIG_PATH`: Path to YAML config file

---

### ServerConfig

Server configuration for transport and networking.

**Source:** `src/config/schema.py:76-85`

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| transport | str | 'http' | Transport type: http, stdio, or sse |
| host | str | '0.0.0.0' | Server host address |
| port | int | 8000 | Server port |

**Transport Options:**
- `http`: Recommended for production, supports health checks and load balancers
- `stdio`: Used by Claude Desktop and local MCP clients
- `sse`: Deprecated, server-sent events transport

---

### LLMConfig

LLM provider and model configuration.

**Source:** `src/config/schema.py:146-156`

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| provider | str | 'openai' | LLM provider name |
| model | str | 'gpt-4.1' | Model name |
| temperature | float | None | Temperature (0.0-2.0), None for reasoning models |
| max_tokens | int | 4096 | Maximum tokens |
| providers | LLMProvidersConfig | {} | Provider-specific configurations |

---

### EmbedderConfig

Embedder provider and model configuration.

**Source:** `src/config/schema.py:167-174`

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| provider | str | 'openai' | Embedder provider name |
| model | str | 'text-embedding-3-small' | Embedder model name |
| dimensions | int | 1536 | Embedding dimensions |
| providers | EmbedderProvidersConfig | {} | Provider-specific configurations |

---

### DatabaseConfig

Database provider configuration.

**Source:** `src/config/schema.py:202-207`

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| provider | str | 'falkordb' | Database provider name |
| providers | DatabaseProvidersConfig | {} | Provider-specific configurations |

---

### GraphitiAppConfig

Graphiti-specific application configuration.

**Source:** `src/config/schema.py:216-228`

**Fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| group_id | str | 'main' | Default group ID for graph namespace |
| episode_id_prefix | str | '' | Prefix for episode IDs |
| user_id | str | 'mcp_user' | User ID for operations |
| entity_types | list[EntityTypeConfig] | [] | Custom entity types |

---

## Models

### Entity Types

Predefined entity types for knowledge graph extraction.

**Source:** `src/models/entity_types.py`

#### Preference

Represents user preferences, choices, or opinions. **Highest priority classification.**

**Fields:** (Inherits from BaseModel, no custom fields)

**Usage:** Low threshold for detection. Any mention of likes, dislikes, wants, or choices.

**Examples:**
- "I prefer dark mode"
- "I don't like emails in the morning"
- "Use Python rather than JavaScript"

**Source:** Lines 34-43

---

#### Requirement

Represents project requirements or features.

**Fields:**
- `project_name` (str): Name of the project
- `description` (str): Description of the requirement

**Usage:** Explicit statements of needs or system specifications.

**Examples:**
- "The app must support offline mode"
- "Users need to export data to CSV"
- "System should handle 1000 requests per second"

**Source:** Lines 6-32

---

#### Procedure

Represents action procedures or instructions.

**Fields:**
- `description` (str): Description of the procedure

**Usage:** Sequential instructions or directives.

**Examples:**
- "First authenticate, then fetch user data"
- "When error occurs, retry three times"
- "Always validate input before processing"

**Source:** Lines 46-65

---

#### Location

Represents physical or virtual places.

**Fields:**
- `name` (str): Name of the location
- `description` (str): Description of the location

**Usage:** Places where activities occur or entities exist.

**Examples:**
- "Meeting in Conference Room A"
- "Seattle office"
- "https://app.example.com/dashboard"

**Source:** Lines 67-91

**Priority:** Check Preference, Organization, Document, Event first.

---

#### Event

Represents time-bound activities or occurrences.

**Fields:**
- `name` (str): Name of the event
- `description` (str): Description of the event

**Usage:** Scheduled or unscheduled time-bound activities.

**Examples:**
- "Q4 Planning Meeting scheduled for next week"
- "System outage on 2025-11-28"
- "Annual conference in March"

**Source:** Lines 93-115

---

#### Object

Represents physical items, tools, or devices. **Last resort classification.**

**Fields:**
- `name` (str): Name of the object
- `description` (str): Description of the object

**Usage:** Only if doesn't fit other types.

**Examples:**
- "MacBook Pro laptop"
- "iPhone 15"
- "Office chair"

**Source:** Lines 117-141

**Priority:** Check all other types first, especially Preference and Document.

---

#### Topic

Represents subjects of conversation or knowledge domains. **Last resort classification.**

**Fields:**
- `name` (str): Name of the topic
- `description` (str): Description of the topic

**Usage:** Only if doesn't fit other types.

**Examples:**
- "Machine learning algorithms"
- "Climate change"
- "Marketing strategy"

**Source:** Lines 143-167

**Priority:** Check all other types first.

---

#### Organization

Represents companies, institutions, or formal entities.

**Fields:**
- `name` (str): Name of the organization
- `description` (str): Description of the organization

**Usage:** Company names, institutions, formal groups.

**Examples:**
- "Acme Corporation"
- "Stanford University"
- "Red Cross"

**Source:** Lines 169-190

---

#### Document

Represents information content in various forms.

**Fields:**
- `title` (str): Title of the document
- `description` (str): Description of the document

**Usage:** Written or recorded content.

**Examples:**
- "Q4 Financial Report"
- "Product Requirements Document"
- "Tutorial video on Python"

**Source:** Lines 192-213

---

#### ENTITY_TYPES Dictionary

Dictionary mapping entity type names to Pydantic models.

**Source:** Lines 215-225

**Structure:**
```python
ENTITY_TYPES: dict[str, BaseModel] = {
    'Requirement': Requirement,
    'Preference': Preference,
    'Procedure': Procedure,
    'Location': Location,
    'Event': Event,
    'Object': Object,
    'Topic': Topic,
    'Organization': Organization,
    'Document': Document,
}
```

**Usage:**
```python
from models.entity_types import ENTITY_TYPES

# Get entity type
preference_model = ENTITY_TYPES['Preference']

# Iterate types
for name, model in ENTITY_TYPES.items():
    print(f"{name}: {model.__doc__}")
```

---

### Response Types

TypedDict response types for MCP tools.

**Source:** `src/models/response_types.py`

#### ErrorResponse

```python
class ErrorResponse(TypedDict):
    error: str
```

**Usage:** Returned when operations fail.

---

#### SuccessResponse

```python
class SuccessResponse(TypedDict):
    message: str
```

**Usage:** Returned for successful operations without data.

---

#### NodeResult

```python
class NodeResult(TypedDict):
    uuid: str
    name: str
    labels: list[str]
    created_at: str | None
    summary: str | None
    group_id: str
    attributes: dict[str, Any]
```

**Usage:** Single node in search results.

---

#### NodeSearchResponse

```python
class NodeSearchResponse(TypedDict):
    message: str
    nodes: list[NodeResult]
```

**Usage:** Response from search_nodes.

---

#### FactSearchResponse

```python
class FactSearchResponse(TypedDict):
    message: str
    facts: list[dict[str, Any]]
```

**Usage:** Response from search_memory_facts.

---

#### EpisodeSearchResponse

```python
class EpisodeSearchResponse(TypedDict):
    message: str
    episodes: list[dict[str, Any]]
```

**Usage:** Response from get_episodes.

---

#### StatusResponse

```python
class StatusResponse(TypedDict):
    status: str
    message: str
```

**Usage:** Response from get_status.

---

## Utility Functions

### format_node_result()

Format an entity node into a readable result dictionary.

**Signature:**
```python
def format_node_result(node: EntityNode) -> dict[str, Any]
```

**Parameters:**
- `node`: EntityNode to format

**Returns:**
- `dict[str, Any]`: Serialized node with embeddings excluded

**Source:** `src/utils/formatting.py:9-30`

**Implementation:**
```python
result = node.model_dump(
    mode='json',
    exclude={'name_embedding'}
)
result.get('attributes', {}).pop('name_embedding', None)
return result
```

---

### format_fact_result()

Format an entity edge into a readable result dictionary.

**Signature:**
```python
def format_fact_result(edge: EntityEdge) -> dict[str, Any]
```

**Parameters:**
- `edge`: EntityEdge to format

**Returns:**
- `dict[str, Any]`: Serialized edge with embeddings excluded

**Source:** `src/utils/formatting.py:32-51`

**Implementation:**
```python
result = edge.model_dump(
    mode='json',
    exclude={'fact_embedding'}
)
result.get('attributes', {}).pop('fact_embedding', None)
return result
```

---

### create_azure_credential_token_provider()

Create Azure credential token provider for managed identity authentication.

**Signature:**
```python
def create_azure_credential_token_provider() -> Callable[[], str]
```

**Returns:**
- `Callable[[], str]`: Token provider function

**Raises:**
- `ImportError`: If azure-identity package not installed

**Source:** `src/utils/utils.py:6-28`

**Usage:**
```python
from utils.utils import create_azure_credential_token_provider

# Create token provider for Azure AD authentication
token_provider = create_azure_credential_token_provider()

# Use with Azure OpenAI client
azure_client = AsyncAzureOpenAI(
    azure_endpoint="https://myresource.openai.azure.com",
    azure_ad_token_provider=token_provider
)
```

**Requirements:**
```bash
pip install azure-identity
# or
pip install mcp-server[azure]
```

---

## Usage Patterns

### Basic Usage

```python
import asyncio
from config.schema import GraphitiConfig

# Initialize service
config = GraphitiConfig()
from src.graphiti_mcp_server import GraphitiService, QueueService

graphiti_service = GraphitiService(config)
queue_service = QueueService()

await graphiti_service.initialize()
client = await graphiti_service.get_client()
await queue_service.initialize(client)

# Add memory
from src.graphiti_mcp_server import add_memory

result = await add_memory(
    name="User Preference",
    episode_body="User prefers dark mode and large fonts",
    group_id="user_123",
    source="text"
)
print(result)

# Search nodes
from src.graphiti_mcp_server import search_nodes

nodes = await search_nodes(
    query="user interface preferences",
    group_ids=["user_123"],
    max_nodes=5
)
print(nodes)

# Search facts
from src.graphiti_mcp_server import search_memory_facts

facts = await search_memory_facts(
    query="what are the user's preferences",
    group_ids=["user_123"],
    max_facts=10
)
print(facts)
```

---

### Multi-Provider Setup

```yaml
# config/config.yaml - Multiple providers configured

llm:
  provider: anthropic  # Switch providers easily
  model: claude-sonnet-4-5
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
    anthropic:
      api_key: ${ANTHROPIC_API_KEY}
    azure_openai:
      api_url: ${AZURE_OPENAI_ENDPOINT}
      deployment_name: gpt-4
      use_azure_ad: true

embedder:
  provider: voyage  # Different provider for embeddings
  model: voyage-3
  dimensions: 1024
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
    voyage:
      api_key: ${VOYAGE_API_KEY}
```

**Switching Providers:**

```bash
# Via CLI
python src/graphiti_mcp_server.py \
  --llm-provider anthropic \
  --model claude-sonnet-4-5 \
  --embedder-provider voyage \
  --embedder-model voyage-3

# Via environment
export LLM__PROVIDER=anthropic
export LLM__MODEL=claude-sonnet-4-5
export EMBEDDER__PROVIDER=voyage

python src/graphiti_mcp_server.py
```

---

### Error Handling

```python
from src.graphiti_mcp_server import add_memory, search_nodes
from models.response_types import ErrorResponse

# Check response type
result = await add_memory(
    name="Test",
    episode_body="Test content"
)

if 'error' in result:
    print(f"Error: {result['error']}")
else:
    print(f"Success: {result['message']}")

# Handle search errors
try:
    nodes = await search_nodes(query="preferences", max_nodes=5)

    if 'error' in nodes:
        print(f"Search failed: {nodes['error']}")
    else:
        for node in nodes['nodes']:
            print(f"Found: {node['name']}")
except Exception as e:
    print(f"Unexpected error: {e}")

# Database connection errors
from src.graphiti_mcp_server import GraphitiService

try:
    service = GraphitiService(config)
    await service.initialize()
except RuntimeError as e:
    if "Connection Error" in str(e):
        print("Database not running")
        print(e)  # Helpful startup instructions
    else:
        raise
```

---

### Custom Entity Types

```yaml
# config/config.yaml
graphiti:
  entity_types:
    - name: Product
      description: Software products or features
    - name: Customer
      description: Customer or client organizations
    - name: Issue
      description: Bug reports or technical issues
```

**Using Custom Types:**

```python
# Custom entity types are automatically used during extraction
result = await add_memory(
    name="Product Feedback",
    episode_body="Customer Acme Corp reported issue with Product CloudSync login feature",
    group_id="support"
)

# Search by custom entity type
nodes = await search_nodes(
    query="login issues",
    entity_types=["Product", "Issue"],
    max_nodes=10
)
```

---

### Batch Operations

```python
import asyncio

# Add multiple episodes
episodes = [
    ("User Session 1", "User prefers dark theme", "user_123"),
    ("User Session 2", "User likes keyboard shortcuts", "user_123"),
    ("User Session 3", "User wants notifications off", "user_123"),
]

# Queue all episodes
for name, content, group_id in episodes:
    await add_memory(
        name=name,
        episode_body=content,
        group_id=group_id
    )

# Search across multiple groups
results = await search_nodes(
    query="user preferences",
    group_ids=["user_123", "user_456", "user_789"],
    max_nodes=50
)
```

---

## Best Practices

### Memory Management

**1. Use Descriptive Names:**
```python
# Good
await add_memory(
    name="Q4 Planning Meeting Notes - Nov 29",
    episode_body="Discussed roadmap priorities..."
)

# Avoid
await add_memory(
    name="Notes",
    episode_body="Some stuff..."
)
```

**2. Provide Detailed Content:**
```python
# Good - specific details
await add_memory(
    name="User Preference Update",
    episode_body="User Jane Doe (jane@example.com) prefers to receive email notifications only for critical alerts, not routine updates. She wants notifications between 9 AM and 5 PM EST only.",
    group_id="user_jane_doe"
)

# Avoid - vague content
await add_memory(
    name="Settings",
    episode_body="Changed notification settings",
    group_id="user_jane_doe"
)
```

**3. Use Appropriate Source Types:**
```python
# Text for narrative content
await add_memory(
    name="Meeting Notes",
    episode_body="Team discussed project timeline...",
    source="text"
)

# JSON for structured data
await add_memory(
    name="API Response",
    episode_body='{"user_id": "123", "preferences": {"theme": "dark"}}',
    source="json"
)

# Message for conversations
await add_memory(
    name="Support Chat",
    episode_body="User: How do I reset password?\nAgent: Click forgot password link...",
    source="message"
)
```

**4. Organize by Group:**
```python
# Per-user groups
await add_memory(..., group_id=f"user_{user_id}")

# Per-project groups
await add_memory(..., group_id=f"project_{project_id}")

# Per-session groups
await add_memory(..., group_id=f"session_{session_id}")
```

---

### Search Optimization

**1. Use Specific Queries:**
```python
# Good - specific
nodes = await search_nodes(
    query="user interface theme preferences for dark mode",
    entity_types=["Preference"]
)

# Avoid - too vague
nodes = await search_nodes(query="preferences")
```

**2. Filter by Entity Types:**
```python
# Find only organizations
orgs = await search_nodes(
    query="software companies in Seattle",
    entity_types=["Organization"]
)

# Find preferences and requirements
results = await search_nodes(
    query="user needs for mobile app",
    entity_types=["Preference", "Requirement"]
)
```

**3. Set Appropriate Limits:**
```python
# For quick overview
nodes = await search_nodes(query="...", max_nodes=5)

# For comprehensive search
nodes = await search_nodes(query="...", max_nodes=50)

# Facts are typically more numerous
facts = await search_memory_facts(query="...", max_facts=20)
```

**4. Use Center Node for Related Facts:**
```python
# First find the entity
nodes = await search_nodes(
    query="CloudSync product",
    entity_types=["Product"],
    max_nodes=1
)

if nodes['nodes']:
    product_uuid = nodes['nodes'][0]['uuid']

    # Then find related facts
    facts = await search_memory_facts(
        query="issues and features",
        center_node_uuid=product_uuid,
        max_facts=20
    )
```

---

### Configuration Best Practices

**1. Use YAML for Base Configuration:**
```yaml
# config/config.yaml - committed to repo
server:
  transport: http
  host: 0.0.0.0
  port: 8000

llm:
  provider: openai
  model: gpt-4.1
  temperature: 0.7
  # API keys from environment, not hardcoded
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
```

**2. Use Environment Variables for Secrets:**
```bash
# .env - NOT committed to repo
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
NEO4J_PASSWORD=secret123
```

**3. Use CLI Arguments for Overrides:**
```bash
# Development
python src/graphiti_mcp_server.py \
  --transport stdio \
  --llm-provider anthropic \
  --model claude-sonnet-4-5

# Production
python src/graphiti_mcp_server.py \
  --transport http \
  --host 0.0.0.0 \
  --port 8000
```

**4. Configure Semaphore for Rate Limits:**
```bash
# OpenAI Tier 1 (free) - 3 RPM
SEMAPHORE_LIMIT=1

# OpenAI Tier 2 - 60 RPM
SEMAPHORE_LIMIT=5

# OpenAI Tier 3 - 500 RPM
SEMAPHORE_LIMIT=10

# OpenAI Tier 4 - 5000 RPM
SEMAPHORE_LIMIT=30
```

---

### Production Deployment

**1. Use HTTP Transport:**
```yaml
server:
  transport: http
  host: 0.0.0.0
  port: 8000
```

**2. Set Up Health Checks:**
```yaml
# docker-compose.yml
services:
  graphiti-mcp:
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**3. Configure Logging:**
```python
import logging

# Set appropriate log level
logging.basicConfig(level=logging.INFO)

# Reduce noise from libraries
logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
```

**4. Use Persistent Database:**
```yaml
# docker-compose.yml
services:
  neo4j:
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs

volumes:
  neo4j_data:
  neo4j_logs:
```

**5. Monitor Queue Sizes:**
```python
# Check queue status
size = queue_service.get_queue_size("user_123")
is_running = queue_service.is_worker_running("user_123")

if size > 100:
    logger.warning(f"Queue backlog: {size} episodes pending")
```

---

## Appendix

### Type Definitions

```python
# Graphiti core types
from graphiti_core import Graphiti
from graphiti_core.nodes import EntityNode, EpisodeType, EpisodicNode
from graphiti_core.edges import EntityEdge
from graphiti_core.search.search_filters import SearchFilters

# MCP server types
from config.schema import (
    GraphitiConfig,
    ServerConfig,
    LLMConfig,
    EmbedderConfig,
    DatabaseConfig,
    GraphitiAppConfig,
)

from models.response_types import (
    ErrorResponse,
    SuccessResponse,
    NodeResult,
    NodeSearchResponse,
    FactSearchResponse,
    EpisodeSearchResponse,
    StatusResponse,
)

from models.entity_types import ENTITY_TYPES

from services.factories import (
    LLMClientFactory,
    EmbedderFactory,
    DatabaseDriverFactory,
)

from services.queue_service import QueueService
```

---

### Constants

**Semaphore Limit:**
```python
SEMAPHORE_LIMIT = int(os.getenv('SEMAPHORE_LIMIT', 10))
```
- Controls concurrent episode processing
- Default: 10
- Adjust based on LLM provider rate limits

**Log Format:**
```python
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
```

**MCP Server Instructions:**
```python
GRAPHITI_MCP_INSTRUCTIONS = """
Graphiti is a memory service for AI agents built on a knowledge graph...
"""
```
- Displayed to MCP clients
- Provides usage guidance
- Source: Lines 117-145 in graphiti_mcp_server.py

---

### CLI Reference

**Full Command Line Options:**

```bash
python src/graphiti_mcp_server.py [OPTIONS]

Configuration:
  --config PATH              Path to YAML config file (default: config/config.yaml)

Transport:
  --transport {stdio,http,sse}  Transport type (default: http)
  --host HOST                Server host (default: 0.0.0.0)
  --port PORT                Server port (default: 8000)

LLM:
  --llm-provider {openai,azure_openai,anthropic,gemini,groq}
  --model MODEL              LLM model name
  --temperature TEMP         Temperature 0.0-2.0
  --small-model MODEL        Small model name

Embedder:
  --embedder-provider {openai,azure_openai,gemini,voyage}
  --embedder-model MODEL     Embedder model name

Database:
  --database-provider {neo4j,falkordb}

Graphiti:
  --group-id ID              Default group ID
  --user-id ID               User ID
  --destroy-graph            Clear all graphs on startup

Examples:
  # Basic startup
  python src/graphiti_mcp_server.py

  # Custom config
  python src/graphiti_mcp_server.py --config /path/to/config.yaml

  # Override provider
  python src/graphiti_mcp_server.py --llm-provider anthropic --model claude-sonnet-4-5

  # STDIO for Claude Desktop
  python src/graphiti_mcp_server.py --transport stdio

  # Production HTTP
  python src/graphiti_mcp_server.py --transport http --host 0.0.0.0 --port 8000
```

---

### Error Codes and Messages

**Common Errors:**

| Error | Cause | Solution |
|-------|-------|----------|
| "Services not initialized" | Tools called before server ready | Wait for initialization |
| "Graphiti service not initialized" | GraphitiService is None | Check server startup logs |
| "API key is not configured" | Missing API key in config | Set environment variable |
| "Database Connection Error" | Database not running | Start Neo4j/FalkorDB |
| "max_facts must be a positive integer" | Invalid parameter | Use max_facts > 0 |
| "No group IDs specified for clearing" | clear_graph called without groups | Provide group_ids parameter |
| "Entity edge not found" | UUID doesn't exist | Verify UUID is correct |
| "Queue service not initialized" | add_episode before initialize | Call queue_service.initialize() |

**Database Connection Errors:**

FalkorDB:
```
Database Connection Error: FalkorDB is not running
To start FalkorDB:
  - Using Docker Compose: cd mcp_server && docker compose up
  - Or run FalkorDB manually: docker run -p 6379:6379 falkordb/falkordb
```

Neo4j:
```
Database Connection Error: Neo4j is not running
To start Neo4j:
  - Using Docker Compose: cd mcp_server && docker compose -f docker/docker-compose-neo4j.yml up
  - Or install Neo4j Desktop from: https://neo4j.com/download/
  - Or run Neo4j manually: docker run -p 7474:7474 -p 7687:7687 neo4j:latest
```

---

### Version Information

**Checking Versions:**

```python
# Graphiti Core version
import graphiti_core
print(graphiti_core.__version__)

# Or from Docker
cat /app/.graphiti-core-version

# FastMCP version
import fastmcp
print(fastmcp.__version__)
```

**Logged at Startup:**
```
2025-11-29 10:30:00 - __main__ - INFO - Using configuration:
2025-11-29 10:30:00 - __main__ - INFO -   - LLM: openai / gpt-4.1
2025-11-29 10:30:00 - __main__ - INFO -   - Embedder: openai / text-embedding-3-small
2025-11-29 10:30:00 - __main__ - INFO -   - Database: falkordb
2025-11-29 10:30:00 - __main__ - INFO -   - Group ID: main
2025-11-29 10:30:00 - __main__ - INFO -   - Transport: http
2025-11-29 10:30:00 - __main__ - INFO -   - Graphiti Core: 0.3.x
```

---

## Summary

This API reference documents the complete public API surface of Graphiti-FastMCP:

- **10 MCP Tools** for memory operations
- **3 Service Classes** for internal architecture
- **3 Factory Classes** for multi-provider support
- **5 Configuration Classes** for flexible setup
- **9 Entity Types** for knowledge extraction
- **7 Response Types** for type-safe returns
- **3 Utility Functions** for formatting and auth

The API is designed for:
- **Ease of use**: Simple async functions with clear parameters
- **Type safety**: TypedDict responses, Pydantic models
- **Flexibility**: Multi-provider, multi-transport support
- **Production readiness**: Health checks, error handling, logging
- **Performance**: Async processing, hybrid search, rate limiting

For more information:
- Component Inventory: `01_component_inventory.md`
- Data Flows: `03_data_flows.md`
- Examples: `examples/`
- Source Code: `src/`
