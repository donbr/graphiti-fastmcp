# API Reference

## Overview

The Graphiti MCP Server exposes a knowledge graph memory system through the Model Context Protocol (MCP). This API allows AI agents and applications to store, retrieve, and manage episodic memories in a graph structure with entities (nodes) and relationships (edges).

**Architecture**: The API uses FastMCP for protocol implementation, follows a factory pattern for service initialization, and employs asynchronous queue-based processing for write operations.

**Protocol**: All API interactions use JSON-RPC 2.0 over HTTP or stdio transport. The MCP protocol handles tool discovery, invocation, and response serialization.

**Knowledge Graph Model**:
- **Episodes**: Units of content (text, messages, or JSON) added to memory
- **Entities (Nodes)**: Extracted concepts, people, places, organizations, etc.
- **Facts (Edges)**: Relationships between entities with temporal validity
- **Groups**: Namespaces for organizing knowledge by context or user

---

## MCP Tools

The server exposes 9 public tools through the MCP protocol. All tools are registered via the `@server.tool()` decorator and accessible to connected MCP clients.

### add_memory

```python
@server.tool()
async def add_memory(
    name: str,
    episode_body: str,
    group_id: str | None = None,
    source: str = 'text',
    source_description: str = '',
    uuid: str | None = None,
) -> SuccessResponse | ErrorResponse
```

**Description**: Add an episode to the knowledge graph memory. Episodes are processed asynchronously - this tool queues the episode for background processing and returns immediately. The LLM extracts entities and relationships from the episode content.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | str | Yes | Episode name/title for identification |
| episode_body | str | Yes | Content to add (text, JSON string, or message) |
| group_id | str | No | Knowledge graph namespace (defaults to config value) |
| source | str | No | Episode type: 'text', 'json', or 'message' (default: 'text') |
| source_description | str | No | Metadata about the episode source |
| uuid | str | No | Optional UUID for idempotent episode creation |

**Returns**:
- `SuccessResponse`: `{"message": "Episode '{name}' queued for processing in group '{group_id}'"}`
- `ErrorResponse`: `{"error": "Error queuing episode: {details}"}`

**Example**:
```python
# Add a text episode
result = await session.call_tool("add_memory", {
    "name": "Meeting Notes",
    "episode_body": "Discussed Q4 roadmap with Alice and Bob. Decided to prioritize feature X.",
    "group_id": "project-alpha",
    "source": "text",
    "source_description": "Team meeting 2024-11-30"
})

# Add a message episode
result = await session.call_tool("add_memory", {
    "name": "User Conversation",
    "episode_body": "User: What's the weather? Assistant: It's sunny today.",
    "source": "message"
})
```

**Behavior**:
- Episodes are processed asynchronously via QueueService to prevent race conditions
- Multiple episodes for the same group_id are processed sequentially
- Different groups can process episodes in parallel
- LLM extracts entities and relationships from episode_body
- Returns success immediately; processing happens in background

**Source**: `src/server.py:230-266`

---

### search_nodes

```python
@server.tool()
async def search_nodes(
    query: str,
    group_ids: list[str] | None = None,
    max_nodes: int = 10,
    entity_types: list[str] | None = None,
) -> NodeSearchResponse | ErrorResponse
```

**Description**: Search for entity nodes in the knowledge graph using natural language queries. Uses hybrid search combining vector similarity and keyword matching with Reciprocal Rank Fusion (RRF) scoring.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | str | Yes | Natural language search query |
| group_ids | list[str] | No | List of group IDs to search (defaults to config group_id) |
| max_nodes | int | No | Maximum number of nodes to return (default: 10) |
| entity_types | list[str] | No | Filter by entity labels (e.g., ['Organization', 'Location']) |

**Returns**:
- `NodeSearchResponse`: Contains message and list of `NodeResult` objects
- `ErrorResponse`: `{"error": "Error searching nodes: {details}"}`

**NodeResult Structure**:
```typescript
{
  uuid: string,           // Unique identifier
  name: string,           // Entity name
  labels: string[],       // Entity types/labels
  created_at: string,     // ISO 8601 timestamp
  summary: string | null, // LLM-generated entity summary
  group_id: string,       // Namespace
  attributes: object      // Additional metadata (embeddings excluded)
}
```

**Example**:
```python
# Basic search
result = await session.call_tool("search_nodes", {
    "query": "people working on AI projects",
    "max_nodes": 5
})

# Filtered search
result = await session.call_tool("search_nodes", {
    "query": "technology companies",
    "entity_types": ["Organization"],
    "group_ids": ["project-alpha"],
    "max_nodes": 10
})
```

**Search Configuration**: Uses `NODE_HYBRID_SEARCH_RRF` from graphiti_core which combines:
- Vector similarity search on entity embeddings
- Keyword matching on entity names and summaries
- RRF scoring to merge results

**Source**: `src/server.py:268-312`

---

### search_memory_facts

```python
@server.tool()
async def search_memory_facts(
    query: str,
    group_ids: list[str] | None = None,
    max_facts: int = 10,
    center_node_uuid: str | None = None,
) -> FactSearchResponse | ErrorResponse
```

**Description**: Search for relationship facts (edges) between entities in the knowledge graph. Facts represent connections like "Alice WORKS_AT Acme Corp" with temporal validity.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | str | Yes | Natural language query for facts |
| group_ids | list[str] | No | List of group IDs to search (defaults to config group_id) |
| max_facts | int | No | Maximum number of facts to return (default: 10) |
| center_node_uuid | str | No | UUID of entity to search around |

**Returns**:
- `FactSearchResponse`: Contains message and list of fact dictionaries
- `ErrorResponse`: `{"error": "Error searching facts: {details}"}`

**Fact Structure**:
```typescript
{
  uuid: string,               // Unique identifier
  source_node_uuid: string,   // Source entity UUID
  target_node_uuid: string,   // Target entity UUID
  name: string,               // Relationship type (e.g., "WORKS_AT")
  fact: string,               // Human-readable fact description
  valid_at: string,           // ISO 8601 timestamp when fact was valid
  invalid_at: string | null,  // ISO 8601 timestamp when fact became invalid
  created_at: string,         // ISO 8601 timestamp
  group_id: string,           // Namespace
  attributes: object          // Additional metadata (embeddings excluded)
}
```

**Example**:
```python
# Basic fact search
result = await session.call_tool("search_memory_facts", {
    "query": "employment relationships",
    "max_facts": 10
})

# Search around specific entity
result = await session.call_tool("search_memory_facts", {
    "query": "collaborations",
    "center_node_uuid": "alice-uuid-123",
    "max_facts": 5
})
```

**Source**: `src/server.py:314-343`

---

### get_episodes

```python
@server.tool()
async def get_episodes(
    group_ids: list[str] | None = None,
    max_episodes: int = 10,
) -> EpisodeSearchResponse | ErrorResponse
```

**Description**: Retrieve episodes from the knowledge graph. Episodes are the original content units added via `add_memory`.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| group_ids | list[str] | No | List of group IDs to retrieve from (defaults to config group_id) |
| max_episodes | int | No | Maximum number of episodes to return (default: 10) |

**Returns**:
- `EpisodeSearchResponse`: Contains message and list of episode dictionaries
- `ErrorResponse`: `{"error": "Error getting episodes: {details}"}`

**Episode Structure**:
```typescript
{
  uuid: string,                // Unique identifier
  name: string,                // Episode name/title
  content: string,             // Original episode content
  created_at: string,          // ISO 8601 timestamp
  source: string,              // Episode type: 'text', 'json', or 'message'
  source_description: string,  // Source metadata
  group_id: string             // Namespace
}
```

**Example**:
```python
# Get recent episodes
result = await session.call_tool("get_episodes", {
    "max_episodes": 5
})

# Get episodes from specific groups
result = await session.call_tool("get_episodes", {
    "group_ids": ["project-alpha", "project-beta"],
    "max_episodes": 20
})
```

**Source**: `src/server.py:381-416`

---

### get_entity_edge

```python
@server.tool()
async def get_entity_edge(uuid: str) -> dict[str, Any] | ErrorResponse
```

**Description**: Retrieve a specific relationship edge by its UUID.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| uuid | str | Yes | UUID of the entity edge to retrieve |

**Returns**:
- Fact dictionary (same structure as `search_memory_facts` results)
- `ErrorResponse`: `{"error": "Error getting entity edge: {details}"}`

**Example**:
```python
result = await session.call_tool("get_entity_edge", {
    "uuid": "edge-uuid-123"
})
```

**Source**: `src/server.py:369-378`

---

### delete_entity_edge

```python
@server.tool()
async def delete_entity_edge(uuid: str) -> SuccessResponse | ErrorResponse
```

**Description**: Delete a relationship edge from the knowledge graph.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| uuid | str | Yes | UUID of the entity edge to delete |

**Returns**:
- `SuccessResponse`: `{"message": "Entity edge with UUID {uuid} deleted successfully"}`
- `ErrorResponse`: `{"error": "Error deleting entity edge: {details}"}`

**Example**:
```python
result = await session.call_tool("delete_entity_edge", {
    "uuid": "edge-uuid-123"
})
```

**Source**: `src/server.py:345-355`

---

### delete_episode

```python
@server.tool()
async def delete_episode(uuid: str) -> SuccessResponse | ErrorResponse
```

**Description**: Delete an episode from the knowledge graph. This removes the episode node but may not remove entities or facts extracted from it.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| uuid | str | Yes | UUID of the episode to delete |

**Returns**:
- `SuccessResponse`: `{"message": "Episode with UUID {uuid} deleted successfully"}`
- `ErrorResponse`: `{"error": "Error deleting episode: {details}"}`

**Example**:
```python
result = await session.call_tool("delete_episode", {
    "uuid": "episode-uuid-123"
})
```

**Source**: `src/server.py:357-367`

---

### clear_graph

```python
@server.tool()
async def clear_graph(group_ids: list[str] | None = None) -> SuccessResponse | ErrorResponse
```

**Description**: Clear all data from the knowledge graph for specified group IDs. This is a destructive operation that removes all episodes, entities, and facts for the specified groups.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| group_ids | list[str] | No | List of group IDs to clear (defaults to config group_id) |

**Returns**:
- `SuccessResponse`: `{"message": "Graph data cleared for group IDs: {group_ids}"}`
- `ErrorResponse`: `{"error": "Error clearing graph: {details}"}`

**Example**:
```python
# Clear specific groups
result = await session.call_tool("clear_graph", {
    "group_ids": ["test-group", "temp-data"]
})

# Clear default group
result = await session.call_tool("clear_graph", {})
```

**Warning**: This operation is irreversible. All data for the specified groups will be permanently deleted.

**Source**: `src/server.py:418-432`

---

### get_status

```python
@server.tool()
async def get_status() -> StatusResponse
```

**Description**: Health check for the Graphiti MCP server and database connection. Tests database connectivity by executing a simple query.

**Parameters**: None

**Returns**:
- `StatusResponse`: `{"status": "ok"|"error", "message": "..."}`

**Example**:
```python
result = await session.call_tool("get_status", {})
# Response: {"status": "ok", "message": "Graphiti MCP server is running and connected to falkordb database"}
```

**Use Cases**:
- Pre-flight checks before executing operations
- Monitoring and health checks
- Debugging connection issues

**Source**: `src/server.py:434-455`

---

## Services

### GraphitiService

```python
class GraphitiService:
    """Service class managing Graphiti client lifecycle and initialization."""
```

**Description**: Manages the Graphiti Core client instance, handling initialization with LLM, embedder, and database components created via factory pattern. Provides access to the initialized client for tool handlers.

**Constructor**:
```python
def __init__(self, config: GraphitiConfig, semaphore_limit: int = 10)
```

**Parameters**:
- `config`: GraphitiConfig instance with all provider settings
- `semaphore_limit`: Maximum concurrent operations (default: 10)

**Attributes**:
- `client`: Initialized Graphiti instance (None until initialize() called)
- `entity_types`: Dictionary of custom Pydantic entity models
- `semaphore`: Asyncio semaphore for concurrency control

**Methods**:

#### initialize()

```python
async def initialize() -> None
```

**Description**: Initialize the Graphiti client with factory-created LLM, embedder, and database drivers. Builds custom entity types from configuration and establishes database connection.

**Process**:
1. Create LLM client via `LLMClientFactory.create(config.llm)`
2. Create embedder client via `EmbedderFactory.create(config.embedder)`
3. Create database config via `DatabaseDriverFactory.create_config(config.database)`
4. Build custom entity type models from configuration
5. Initialize Graphiti client with all components
6. Build database indices and constraints

**Raises**:
- `RuntimeError`: If initialization fails
- `ValueError`: If API keys missing or invalid configuration

**Example**:
```python
config = GraphitiConfig()
service = GraphitiService(config, semaphore_limit=10)
await service.initialize()
```

**Source**: `src/server.py:98-160`

---

#### get_client()

```python
async def get_client() -> Graphiti
```

**Description**: Retrieve the initialized Graphiti client instance. Calls `initialize()` if not already initialized.

**Returns**: Initialized Graphiti Core client

**Raises**:
- `RuntimeError`: If client initialization failed

**Example**:
```python
client = await service.get_client()
results = await client.search_("AI companies")
```

**Source**: `src/server.py:162-167`

---

**Service Initialization Pattern**:
```python
# In create_server() factory
config = GraphitiConfig()
graphiti_service = GraphitiService(config, SEMAPHORE_LIMIT)
await graphiti_service.initialize()
client = await graphiti_service.get_client()
```

**Source**: `src/server.py:88-168`

---

### QueueService

```python
class QueueService:
    """Service for managing sequential episode processing queues by group_id."""
```

**Description**: Manages asynchronous, sequential processing of episodes per group_id to prevent race conditions in the knowledge graph. Each group has its own queue and background worker.

**Constructor**:
```python
def __init__(self)
```

**Attributes**:
- `_episode_queues`: Dictionary of asyncio.Queue instances per group_id
- `_queue_workers`: Dictionary tracking worker status per group_id
- `_graphiti_client`: Graphiti client instance (set via initialize())

**Methods**:

#### initialize()

```python
async def initialize(graphiti_client: Any) -> None
```

**Description**: Initialize the queue service with a Graphiti client instance.

**Parameters**:
- `graphiti_client`: Initialized Graphiti client for episode processing

**Example**:
```python
queue_service = QueueService()
await queue_service.initialize(graphiti_client)
```

**Source**: `src/services/queue_service.py:92-99`

---

#### add_episode()

```python
async def add_episode(
    group_id: str,
    name: str,
    content: str,
    source_description: str,
    episode_type: Any,
    entity_types: Any,
    uuid: str | None,
) -> int
```

**Description**: Queue an episode for asynchronous processing. Creates a closure that captures episode parameters and adds it to the group's queue. Starts a background worker if not already running.

**Parameters**:
| Name | Type | Description |
|------|------|-------------|
| group_id | str | Group ID for the episode |
| name | str | Episode name/title |
| content | str | Episode content |
| source_description | str | Source metadata |
| episode_type | EpisodeType | Type enum (text, json, message) |
| entity_types | dict | Custom entity type models |
| uuid | str | Optional episode UUID |

**Returns**: Queue position (int) - number of items in queue after adding

**Raises**:
- `RuntimeError`: If queue service not initialized

**Example**:
```python
position = await queue_service.add_episode(
    group_id="project-alpha",
    name="Meeting Notes",
    content="Discussed roadmap...",
    source_description="Team meeting",
    episode_type=EpisodeType.text,
    entity_types=custom_entity_types,
    uuid=None
)
# Returns: 1 (first in queue)
```

**Processing Flow**:
1. Creates closure function capturing episode parameters
2. Adds closure to group's asyncio.Queue
3. Starts background worker if not running
4. Returns immediately (async processing)
5. Worker processes episodes sequentially

**Source**: `src/services/queue_service.py:101-152`

---

#### add_episode_task()

```python
async def add_episode_task(
    group_id: str,
    process_func: Callable[[], Awaitable[None]]
) -> int
```

**Description**: Low-level method to add a processing function to the queue. Used internally by `add_episode()`.

**Parameters**:
- `group_id`: Group ID for the queue
- `process_func`: Async function to execute

**Returns**: Queue position

**Source**: `src/services/queue_service.py:24-47`

---

#### get_queue_size()

```python
def get_queue_size(group_id: str) -> int
```

**Description**: Get current queue size for a group_id.

**Parameters**:
- `group_id`: Group ID to check

**Returns**: Number of pending episodes (0 if queue doesn't exist)

**Example**:
```python
size = queue_service.get_queue_size("project-alpha")
print(f"Queue size: {size}")
```

**Source**: `src/services/queue_service.py:82-86`

---

#### is_worker_running()

```python
def is_worker_running(group_id: str) -> bool
```

**Description**: Check if a background worker is running for a group_id.

**Parameters**:
- `group_id`: Group ID to check

**Returns**: True if worker is active, False otherwise

**Example**:
```python
if queue_service.is_worker_running("project-alpha"):
    print("Worker is processing episodes")
```

**Source**: `src/services/queue_service.py:88-90`

---

**Queue Architecture**:
- **Sequential Processing**: Episodes for same group_id processed one at a time
- **Parallel Groups**: Different groups can process simultaneously
- **Background Workers**: Long-lived asyncio tasks that wait for queue items
- **Error Isolation**: Worker errors don't crash other workers or affect client responses

**Source**: `src/services/queue_service.py:12-153`

---

## Factories

Factories create provider-specific client instances based on configuration. All factories support multiple providers with conditional imports for optional dependencies.

### LLMClientFactory

```python
class LLMClientFactory:
    """Factory for creating LLM clients based on configuration."""
```

**Description**: Creates LLM client instances for text generation and entity extraction. Supports multiple providers with provider-specific configurations.

#### create()

```python
@staticmethod
def create(config: LLMConfig) -> LLMClient
```

**Description**: Create an LLM client based on the configured provider.

**Parameters**:
- `config`: LLMConfig with provider, model, and provider-specific settings

**Returns**: LLMClient instance (OpenAIClient, AzureOpenAILLMClient, AnthropicClient, GeminiClient, or GroqClient)

**Raises**:
- `ValueError`: If provider not supported or API key missing
- `ImportError`: If provider library not installed

**Supported Providers**:

| Provider | Models | Configuration Required |
|----------|--------|------------------------|
| openai | gpt-4.1, gpt-4.1-mini, gpt-5, gpt-5-nano, o1, o3 | api_key |
| azure_openai | All Azure OpenAI models | api_key or use_azure_ad, api_url, deployment_name |
| anthropic | claude-3-opus, claude-3-sonnet, claude-3-haiku | api_key |
| gemini | gemini-pro, gemini-ultra | api_key, project_id (optional) |
| groq | llama-3.1-70b, mixtral-8x7b | api_key |

**Example Configuration**:
```yaml
llm:
  provider: openai
  model: gpt-4.1
  temperature: 0.7
  max_tokens: 4096
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
```

**Special Handling**:
- **Reasoning Models** (gpt-5, o1, o3): Sets `reasoning='minimal'` and `verbosity='low'`
- **Small Model Selection**: Automatically selects appropriate small model based on main model type
- **Azure AD Authentication**: Supports managed identity via `use_azure_ad: true`

**Example**:
```python
from config.schema import LLMConfig
from services.factories import LLMClientFactory

config = LLMConfig(
    provider="openai",
    model="gpt-4.1",
    temperature=0.7
)
llm_client = LLMClientFactory.create(config)
```

**Source**: `src/services/factories.py:100-251`

---

### EmbedderFactory

```python
class EmbedderFactory:
    """Factory for creating Embedder clients based on configuration."""
```

**Description**: Creates embedder client instances for generating vector embeddings. Embeddings enable semantic similarity search in the knowledge graph.

#### create()

```python
@staticmethod
def create(config: EmbedderConfig) -> EmbedderClient
```

**Description**: Create an embedder client based on the configured provider.

**Parameters**:
- `config`: EmbedderConfig with provider, model, dimensions, and provider-specific settings

**Returns**: EmbedderClient instance (OpenAIEmbedder, AzureOpenAIEmbedderClient, GeminiEmbedder, or VoyageAIEmbedder)

**Raises**:
- `ValueError`: If provider not supported or API key missing
- `ImportError`: If provider library not installed

**Supported Providers**:

| Provider | Models | Dimensions | Configuration Required |
|----------|--------|------------|------------------------|
| openai | text-embedding-3-small, text-embedding-3-large | 1536, 3072 | api_key |
| azure_openai | text-embedding-3-small, text-embedding-3-large | 1536, 3072 | api_key or use_azure_ad, api_url, deployment_name |
| gemini | text-embedding-004 | 768 | api_key |
| voyage | voyage-3, voyage-3-lite | 1024, 512 | api_key |

**Example Configuration**:
```yaml
embedder:
  provider: openai
  model: text-embedding-3-small
  dimensions: 1536
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
```

**Example**:
```python
from config.schema import EmbedderConfig
from services.factories import EmbedderFactory

config = EmbedderConfig(
    provider="openai",
    model="text-embedding-3-small",
    dimensions=1536
)
embedder = EmbedderFactory.create(config)
```

**Source**: `src/services/factories.py:253-361`

---

### DatabaseDriverFactory

```python
class DatabaseDriverFactory:
    """Factory for creating Database drivers based on configuration."""
```

**Description**: Creates database configuration dictionaries for graph database backends. Returns config dicts that can be passed to Graphiti() constructor.

#### create_config()

```python
@staticmethod
def create_config(config: DatabaseConfig) -> dict
```

**Description**: Create database configuration dictionary based on the configured provider.

**Parameters**:
- `config`: DatabaseConfig with provider and provider-specific settings

**Returns**: Dictionary with database connection configuration

**Raises**:
- `ValueError`: If provider not supported or required config missing
- `ImportError`: If database driver not installed

**Supported Providers**:

| Provider | Graph Type | Configuration Required | Default Port |
|----------|------------|------------------------|--------------|
| neo4j | Property Graph | uri, username, password | 7687 (bolt) |
| falkordb | Graph over Redis | uri, username (optional), password (optional) | 6379 (redis) |

**Neo4j Configuration**:
```yaml
database:
  provider: neo4j
  providers:
    neo4j:
      uri: bolt://localhost:7687
      username: neo4j
      password: ${NEO4J_PASSWORD}
      database: neo4j
```

**Returns**:
```python
{
    'uri': 'bolt://localhost:7687',
    'user': 'neo4j',
    'password': 'secret'
}
```

**FalkorDB Configuration**:
```yaml
database:
  provider: falkordb
  providers:
    falkordb:
      uri: redis://localhost:6379
      password: ${FALKORDB_PASSWORD}
      database: default_db
```

**Returns**:
```python
{
    'driver': 'falkordb',
    'host': 'localhost',
    'port': 6379,
    'username': None,
    'password': 'secret',
    'database': 'default_db'
}
```

**Environment Variable Overrides**:
The factory checks for environment variables that override YAML config:
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
- `FALKORDB_URI`, `FALKORDB_USER`, `FALKORDB_PASSWORD`

**Example**:
```python
from config.schema import DatabaseConfig
from services.factories import DatabaseDriverFactory

config = DatabaseConfig(provider="falkordb")
db_config = DatabaseDriverFactory.create_config(config)

# Use with Graphiti
from graphiti_core.driver.falkordb_driver import FalkorDriver
driver = FalkorDriver(**db_config)
```

**Source**: `src/services/factories.py:363-440`

---

## Configuration

Configuration uses Pydantic Settings with multiple sources (YAML files, environment variables, defaults) with a defined priority.

### GraphitiConfig

```python
class GraphitiConfig(BaseSettings):
    """Graphiti configuration with YAML and environment support."""
```

**Description**: Main configuration class that aggregates all provider configurations. Supports loading from YAML files with environment variable expansion and direct environment variable overrides.

**Configuration Priority** (highest to lowest):
1. CLI arguments (via `apply_cli_overrides()`)
2. Environment variables
3. YAML file (`config/config.yaml` or path from `CONFIG_PATH` env var)
4. Default values

**Attributes**:
```python
server: ServerConfig           # Server settings (host, port, transport)
llm: LLMConfig                # LLM provider configuration
embedder: EmbedderConfig      # Embedder provider configuration
database: DatabaseConfig      # Database provider configuration
graphiti: GraphitiAppConfig   # Graphiti-specific settings
destroy_graph: bool           # Clear graph on startup (default: False)
```

**Environment Variables**:

#### Server Configuration
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| SERVER__TRANSPORT | str | "http" | Transport type: http, stdio |
| SERVER__HOST | str | "0.0.0.0" | Server host address |
| SERVER__PORT | int | 8000 | Server port |

#### LLM Configuration
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| LLM__PROVIDER | str | "openai" | LLM provider name |
| LLM__MODEL | str | "gpt-4.1" | Model name |
| LLM__TEMPERATURE | float | None | Temperature (0.0-2.0, None for reasoning models) |
| LLM__MAX_TOKENS | int | 4096 | Max output tokens |
| LLM__PROVIDERS__OPENAI__API_KEY | str | - | OpenAI API key |
| LLM__PROVIDERS__AZURE_OPENAI__API_KEY | str | - | Azure OpenAI API key |
| LLM__PROVIDERS__AZURE_OPENAI__API_URL | str | - | Azure endpoint URL |
| LLM__PROVIDERS__AZURE_OPENAI__DEPLOYMENT_NAME | str | - | Azure deployment name |
| LLM__PROVIDERS__AZURE_OPENAI__USE_AZURE_AD | bool | false | Use Azure AD auth |
| LLM__PROVIDERS__ANTHROPIC__API_KEY | str | - | Anthropic API key |
| LLM__PROVIDERS__GEMINI__API_KEY | str | - | Gemini API key |
| LLM__PROVIDERS__GROQ__API_KEY | str | - | Groq API key |

#### Embedder Configuration
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| EMBEDDER__PROVIDER | str | "openai" | Embedder provider name |
| EMBEDDER__MODEL | str | "text-embedding-3-small" | Model name |
| EMBEDDER__DIMENSIONS | int | 1536 | Embedding dimensions |
| EMBEDDER__PROVIDERS__OPENAI__API_KEY | str | - | OpenAI API key |
| EMBEDDER__PROVIDERS__AZURE_OPENAI__API_KEY | str | - | Azure OpenAI API key |
| EMBEDDER__PROVIDERS__GEMINI__API_KEY | str | - | Gemini API key |
| EMBEDDER__PROVIDERS__VOYAGE__API_KEY | str | - | Voyage API key |

#### Database Configuration
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| DATABASE__PROVIDER | str | "falkordb" | Database provider name |
| DATABASE__PROVIDERS__NEO4J__URI | str | "bolt://localhost:7687" | Neo4j connection URI |
| DATABASE__PROVIDERS__NEO4J__USERNAME | str | "neo4j" | Neo4j username |
| DATABASE__PROVIDERS__NEO4J__PASSWORD | str | - | Neo4j password |
| DATABASE__PROVIDERS__FALKORDB__URI | str | "redis://localhost:6379" | FalkorDB connection URI |
| DATABASE__PROVIDERS__FALKORDB__PASSWORD | str | - | FalkorDB password |

#### Graphiti Configuration
| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| GRAPHITI__GROUP_ID | str | "main" | Default group ID for namespacing |
| GRAPHITI__USER_ID | str | "mcp_user" | Default user ID |
| GRAPHITI__EPISODE_ID_PREFIX | str | "" | Prefix for episode IDs |

**YAML Configuration**:

Example `config/config.yaml`:
```yaml
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
    azure_openai:
      api_key: ${AZURE_OPENAI_API_KEY}
      api_url: https://your-resource.openai.azure.com
      api_version: "2024-10-21"
      deployment_name: gpt-4
      use_azure_ad: false

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
      password: ${FALKORDB_PASSWORD}
      database: default_db
    neo4j:
      uri: bolt://localhost:7687
      username: neo4j
      password: ${NEO4J_PASSWORD}

graphiti:
  group_id: main
  user_id: mcp_user
  entity_types:
    - name: Organization
      description: Companies, institutions, and formal groups
    - name: Location
      description: Physical or virtual places
```

**Environment Variable Expansion**:
YAML supports `${VAR}` and `${VAR:default}` syntax:
```yaml
llm:
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}              # Required, no default
      api_url: ${OPENAI_API_URL:https://api.openai.com/v1}  # Optional with default
```

**Usage**:
```python
# Load from default location (config/config.yaml)
config = GraphitiConfig()

# Load from custom path
os.environ['CONFIG_PATH'] = '/path/to/config.yaml'
config = GraphitiConfig()

# Access configuration
print(config.llm.provider)  # "openai"
print(config.database.provider)  # "falkordb"
```

**Source**: `src/config/schema.py:230-293`

---

### Nested Configuration Classes

#### ServerConfig
```python
class ServerConfig(BaseModel):
    transport: str = 'http'  # http, stdio, or sse (deprecated)
    host: str = '0.0.0.0'
    port: int = 8000
```
**Source**: `src/config/schema.py:76-85`

---

#### LLMConfig
```python
class LLMConfig(BaseModel):
    provider: str = 'openai'
    model: str = 'gpt-4.1'
    temperature: float | None = None
    max_tokens: int = 4096
    providers: LLMProvidersConfig
```
**Source**: `src/config/schema.py:146-156`

---

#### EmbedderConfig
```python
class EmbedderConfig(BaseModel):
    provider: str = 'openai'
    model: str = 'text-embedding-3-small'
    dimensions: int = 1536
    providers: EmbedderProvidersConfig
```
**Source**: `src/config/schema.py:167-174`

---

#### DatabaseConfig
```python
class DatabaseConfig(BaseModel):
    provider: str = 'falkordb'
    providers: DatabaseProvidersConfig
```
**Source**: `src/config/schema.py:202-207`

---

#### GraphitiAppConfig
```python
class GraphitiAppConfig(BaseModel):
    group_id: str = 'main'
    episode_id_prefix: str = ''
    user_id: str = 'mcp_user'
    entity_types: list[EntityTypeConfig] = []
```
**Source**: `src/config/schema.py:216-228`

---

#### EntityTypeConfig
```python
class EntityTypeConfig(BaseModel):
    name: str          # Entity type name (e.g., "Organization")
    description: str   # Description for LLM entity extraction
```

**Example**:
```yaml
graphiti:
  entity_types:
    - name: Organization
      description: Companies, institutions, and formal groups
    - name: Preference
      description: User preferences, choices, and opinions
```

**Source**: `src/config/schema.py:209-214`

---

## Data Models

Data models use TypedDict for JSON-serializable response structures. All timestamps are ISO 8601 formatted strings.

### Response Types

#### ErrorResponse
```python
class ErrorResponse(TypedDict):
    error: str
```
**Usage**: Returned by all tools when errors occur
**Example**: `{"error": "Database connection failed"}`
**Source**: `src/models/response_types.py:8-9`

---

#### SuccessResponse
```python
class SuccessResponse(TypedDict):
    message: str
```
**Usage**: Returned by write operations (add_memory, delete_*, clear_graph)
**Example**: `{"message": "Episode 'Meeting Notes' queued for processing"}`
**Source**: `src/models/response_types.py:12-13`

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
**Usage**: Individual entity node in search results
**Example**:
```json
{
  "uuid": "550e8400-e29b-41d4-a716-446655440000",
  "name": "Acme Corporation",
  "labels": ["Organization"],
  "created_at": "2024-11-30T10:30:00Z",
  "summary": "A technology company specializing in AI products",
  "group_id": "project-alpha",
  "attributes": {
    "industry": "Technology",
    "founded": "2020"
  }
}
```
**Source**: `src/models/response_types.py:16-24`

---

#### NodeSearchResponse
```python
class NodeSearchResponse(TypedDict):
    message: str
    nodes: list[NodeResult]
```
**Usage**: Returned by search_nodes tool
**Example**:
```json
{
  "message": "Nodes retrieved successfully",
  "nodes": [
    { "uuid": "...", "name": "Acme Corp", ... },
    { "uuid": "...", "name": "Alice Smith", ... }
  ]
}
```
**Source**: `src/models/response_types.py:26-28`

---

#### FactSearchResponse
```python
class FactSearchResponse(TypedDict):
    message: str
    facts: list[dict[str, Any]]
```
**Usage**: Returned by search_memory_facts tool
**Fact Structure**:
```json
{
  "uuid": "fact-uuid-123",
  "source_node_uuid": "alice-uuid",
  "target_node_uuid": "acme-uuid",
  "name": "WORKS_AT",
  "fact": "Alice works at Acme Corporation",
  "valid_at": "2024-01-15T00:00:00Z",
  "invalid_at": null,
  "created_at": "2024-11-30T10:30:00Z",
  "group_id": "project-alpha",
  "attributes": {}
}
```
**Source**: `src/models/response_types.py:31-33`

---

#### EpisodeSearchResponse
```python
class EpisodeSearchResponse(TypedDict):
    message: str
    episodes: list[dict[str, Any]]
```
**Usage**: Returned by get_episodes tool
**Episode Structure**:
```json
{
  "uuid": "episode-uuid-123",
  "name": "Meeting Notes",
  "content": "Discussed Q4 roadmap...",
  "created_at": "2024-11-30T10:00:00Z",
  "source": "text",
  "source_description": "Team meeting",
  "group_id": "project-alpha"
}
```
**Source**: `src/models/response_types.py:36-38`

---

#### StatusResponse
```python
class StatusResponse(TypedDict):
    status: str        # "ok" or "error"
    message: str
```
**Usage**: Returned by get_status tool
**Example**:
```json
{
  "status": "ok",
  "message": "Graphiti MCP server is running and connected to falkordb database"
}
```
**Source**: `src/models/response_types.py:41-43`

---

### Entity Types

Custom Pydantic models for domain-specific entity extraction. These guide the LLM when extracting entities from episodes.

#### Requirement
```python
class Requirement(BaseModel):
    """A specific need, feature, or functionality that must be fulfilled."""

    project_name: str  # Project to which requirement belongs
    description: str   # Requirement description
```
**Usage**: Extract project requirements and specifications from episodes
**Source**: `src/models/entity_types.py:6-32`

---

#### Preference
```python
class Preference(BaseModel):
    """User preferences, choices, opinions, or selections."""
```
**Priority**: Highest - prioritize over other classifications
**Trigger Patterns**: "I want/like/prefer", "I don't want/dislike", "X is better/worse"
**Source**: `src/models/entity_types.py:34-43`

---

#### Procedure
```python
class Procedure(BaseModel):
    """Instructions for actions or how to perform in certain scenarios."""

    description: str  # Procedure description
```
**Usage**: Extract step-by-step instructions, workflows, and processes
**Source**: `src/models/entity_types.py:46-65`

---

#### Location
```python
class Location(BaseModel):
    """Physical or virtual place where activities occur."""

    name: str
    description: str
```
**Examples**: Cities, buildings, websites, virtual meeting rooms
**Source**: `src/models/entity_types.py:67-91`

---

#### Event
```python
class Event(BaseModel):
    """Time-bound activity, occurrence, or experience."""

    name: str
    description: str
```
**Examples**: Meetings, appointments, deadlines, celebrations
**Source**: `src/models/entity_types.py:93-115`

---

#### Object
```python
class Object(BaseModel):
    """Physical item, tool, device, or possession."""

    name: str
    description: str
```
**Priority**: Last resort - check other types first
**Examples**: Car, phone, equipment, tools
**Source**: `src/models/entity_types.py:117-141`

---

#### Topic
```python
class Topic(BaseModel):
    """Subject of conversation, interest, or knowledge domain."""

    name: str
    description: str
```
**Priority**: Last resort - check other types first
**Examples**: Technology, health, sports, machine learning
**Source**: `src/models/entity_types.py:143-167`

---

#### Organization
```python
class Organization(BaseModel):
    """Company, institution, group, or formal entity."""

    name: str
    description: str
```
**Examples**: Companies, schools, hospitals, government agencies, clubs
**Source**: `src/models/entity_types.py:169-190`

---

#### Document
```python
class Document(BaseModel):
    """Information content in various forms."""

    title: str
    description: str
```
**Examples**: Books, articles, reports, emails, videos, presentations
**Source**: `src/models/entity_types.py:192-213`

---

**Entity Type Configuration**:
```yaml
graphiti:
  entity_types:
    - name: Organization
      description: Companies, institutions, and formal groups
    - name: Location
      description: Physical or virtual places
```

**ENTITY_TYPES Dictionary**:
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
**Source**: `src/models/entity_types.py:215-225`

---

## Utility Functions

### format_node_result()

```python
def format_node_result(node: EntityNode) -> dict[str, Any]
```

**Description**: Format an EntityNode Pydantic model into a JSON-serializable dictionary. Excludes embedding vectors to reduce payload size.

**Parameters**:
- `node`: EntityNode instance from Graphiti Core

**Returns**: Dictionary with serialized dates and excluded embeddings

**Exclusions**:
- `name_embedding` field
- Any `*_embedding` fields in attributes

**Example**:
```python
from graphiti_core.nodes import EntityNode
from utils.formatting import format_node_result

node = EntityNode(
    uuid="node-123",
    name="Acme Corp",
    labels=["Organization"],
    summary="Tech company",
    group_id="main"
)
formatted = format_node_result(node)
# Result: {"uuid": "node-123", "name": "Acme Corp", ...}
```

**Source**: `src/utils/formatting.py:9-29`

---

### format_fact_result()

```python
def format_fact_result(edge: EntityEdge) -> dict[str, Any]
```

**Description**: Format an EntityEdge Pydantic model into a JSON-serializable dictionary. Excludes embedding vectors.

**Parameters**:
- `edge`: EntityEdge instance from Graphiti Core

**Returns**: Dictionary with serialized dates and excluded embeddings

**Exclusions**:
- `fact_embedding` field
- Any `*_embedding` fields in attributes

**Example**:
```python
from graphiti_core.edges import EntityEdge
from utils.formatting import format_fact_result

edge = EntityEdge(
    uuid="edge-123",
    source_node_uuid="alice-uuid",
    target_node_uuid="acme-uuid",
    name="WORKS_AT",
    fact="Alice works at Acme Corp",
    group_id="main"
)
formatted = format_fact_result(edge)
# Result: {"uuid": "edge-123", "source_node_uuid": "alice-uuid", ...}
```

**Source**: `src/utils/formatting.py:32-50`

---

### create_azure_credential_token_provider()

```python
def create_azure_credential_token_provider() -> Callable[[], str]
```

**Description**: Create Azure credential token provider for managed identity authentication with Azure OpenAI.

**Returns**: Token provider callable for Azure SDK clients

**Raises**:
- `ImportError`: If azure-identity package not installed

**Requirements**:
```bash
pip install azure-identity
# or
pip install mcp-server[azure]
```

**Usage**:
```python
from utils.utils import create_azure_credential_token_provider

# In Azure environment (VM, App Service, etc.)
token_provider = create_azure_credential_token_provider()

# Use with Azure OpenAI client
from openai import AsyncAzureOpenAI
client = AsyncAzureOpenAI(
    azure_endpoint="https://your-resource.openai.azure.com",
    azure_ad_token_provider=token_provider
)
```

**Authentication Flow**:
1. Uses `DefaultAzureCredential` to automatically discover credentials
2. Tries multiple credential sources in order:
   - Environment variables
   - Managed identity
   - Azure CLI
   - Visual Studio Code
   - Azure PowerShell
3. Gets bearer token for Cognitive Services scope
4. Returns token provider function for SDK clients

**Source**: `src/utils/utils.py:6-27`

---

## Usage Patterns

### Basic Client Connection

```python
from mcp import ClientSession, streamablehttp_client

SERVER_URL = "http://localhost:8000/mcp/"

async with streamablehttp_client(SERVER_URL) as (read, write, _):
    async with ClientSession(read, write) as session:
        # Initialize MCP session (required)
        await session.initialize()

        # Discover available tools
        tools = await session.list_tools()
        for tool in tools.tools:
            print(f"Tool: {tool.name}")
            print(f"Description: {tool.description}")

        # Call a tool
        result = await session.call_tool("get_status", {})
        print(result)
```

**Source**: `examples/01_connect_and_discover.py`

---

### Adding Episodes

```python
# Add text episode
result = await session.call_tool("add_memory", {
    "name": "Team Meeting",
    "episode_body": "Discussed Q4 roadmap with Alice and Bob. Decided to prioritize feature X over feature Y.",
    "group_id": "project-alpha",
    "source": "text",
    "source_description": "Team meeting on 2024-11-30"
})

# Add message episode
conversation = """User: What's the weather like today?
Assistant: It's sunny with a high of 75°F.
User: Perfect for a picnic!"""

result = await session.call_tool("add_memory", {
    "name": "User Conversation",
    "episode_body": conversation,
    "source": "message"
})

# Add JSON episode
data = {
    "event": "product_launch",
    "date": "2024-12-15",
    "products": ["Product A", "Product B"],
    "attendees": ["Alice", "Bob", "Carol"]
}

result = await session.call_tool("add_memory", {
    "name": "Product Launch Event",
    "episode_body": json.dumps(data),
    "source": "json",
    "source_description": "Marketing event data"
})
```

---

### Searching the Knowledge Graph

```python
# Search for entities
result = await session.call_tool("search_nodes", {
    "query": "AI companies in San Francisco",
    "max_nodes": 5,
    "entity_types": ["Organization", "Location"]
})

nodes = json.loads(result.content[0].text)["nodes"]
for node in nodes:
    print(f"Entity: {node['name']}")
    print(f"Type: {node['labels']}")
    print(f"Summary: {node['summary']}")

# Search for relationships
result = await session.call_tool("search_memory_facts", {
    "query": "employment relationships",
    "max_facts": 10
})

facts = json.loads(result.content[0].text)["facts"]
for fact in facts:
    print(f"Fact: {fact['fact']}")
    print(f"Valid from: {fact['valid_at']}")
```

---

### Advanced Configuration

#### Multi-Provider Setup

```yaml
# config/config.yaml
llm:
  provider: openai
  model: gpt-4.1
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
    anthropic:
      api_key: ${ANTHROPIC_API_KEY}
    azure_openai:
      api_key: ${AZURE_OPENAI_API_KEY}
      api_url: https://your-resource.openai.azure.com
      deployment_name: gpt-4

embedder:
  provider: voyage
  model: voyage-3
  dimensions: 1024
  providers:
    voyage:
      api_key: ${VOYAGE_API_KEY}
    openai:
      api_key: ${OPENAI_API_KEY}

database:
  provider: neo4j
  providers:
    neo4j:
      uri: bolt://localhost:7687
      username: neo4j
      password: ${NEO4J_PASSWORD}
```

#### Custom Entity Types

```yaml
graphiti:
  group_id: my-app
  entity_types:
    - name: Product
      description: Software products, features, or services offered by the company
    - name: Customer
      description: Customers, clients, or users of the products
    - name: Requirement
      description: Product requirements, feature requests, or specifications
    - name: Issue
      description: Bugs, problems, or technical issues
```

#### Azure AD Authentication

```yaml
llm:
  provider: azure_openai
  model: gpt-4
  providers:
    azure_openai:
      use_azure_ad: true  # No API key needed
      api_url: https://your-resource.openai.azure.com
      deployment_name: gpt-4
      api_version: "2024-10-21"
```

---

### Error Handling

```python
async def call_tool_with_retry(session, tool_name, args, max_retries=3):
    """Call a tool with automatic retry on transient errors."""
    for attempt in range(max_retries):
        try:
            result = await session.call_tool(tool_name, args)

            # Parse result
            if hasattr(result, 'content') and result.content:
                data = json.loads(result.content[0].text)

                # Check for error response
                if 'error' in data:
                    print(f"Tool error: {data['error']}")
                    return None

                return data

        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed: {e}. Retrying...")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"All {max_retries} attempts failed")
                raise

    return None

# Usage
result = await call_tool_with_retry(session, "search_nodes", {
    "query": "AI companies",
    "max_nodes": 10
})
```

---

### Health Checks

```python
async def wait_for_server(session, timeout=30):
    """Wait for server to be healthy."""
    start = time.time()
    while time.time() - start < timeout:
        try:
            result = await session.call_tool("get_status", {})
            data = json.loads(result.content[0].text)

            if data.get('status') == 'ok':
                print("Server is healthy")
                return True

            print(f"Server status: {data.get('message')}")

        except Exception as e:
            print(f"Health check failed: {e}")

        await asyncio.sleep(2)

    print("Server health check timeout")
    return False

# Usage
async with ClientSession(read, write) as session:
    await session.initialize()

    if await wait_for_server(session):
        # Proceed with operations
        pass
```

---

### Batch Episode Processing

```python
async def add_episodes_batch(session, episodes, group_id="main"):
    """Add multiple episodes in batch."""
    results = []

    for episode in episodes:
        result = await session.call_tool("add_memory", {
            "name": episode['name'],
            "episode_body": episode['content'],
            "group_id": group_id,
            "source": episode.get('source', 'text')
        })

        data = json.loads(result.content[0].text)
        results.append({
            'name': episode['name'],
            'success': 'message' in data,
            'response': data
        })

        # Brief delay to avoid overwhelming the queue
        await asyncio.sleep(0.1)

    return results

# Usage
episodes = [
    {"name": "Meeting 1", "content": "Discussed project timeline..."},
    {"name": "Meeting 2", "content": "Reviewed budget allocation..."},
    {"name": "Meeting 3", "content": "Planned Q1 objectives..."}
]

results = await add_episodes_batch(session, episodes, "project-alpha")
print(f"Added {sum(r['success'] for r in results)} episodes")
```

---

## Best Practices

### 1. Group ID Management
- Use meaningful group IDs to namespace knowledge (e.g., `user-123`, `project-alpha`)
- Separate user data, project data, and system data into different groups
- Default group ID is `main` - override for multi-tenant applications

### 2. Episode Design
- **Name episodes descriptively**: Use clear, searchable names
- **Keep episodes focused**: One topic or interaction per episode
- **Include context**: Use `source_description` to add temporal/source metadata
- **Choose appropriate source type**: `text` for general content, `message` for conversations, `json` for structured data

### 3. Search Optimization
- **Use specific queries**: "AI companies in San Francisco" vs "companies"
- **Filter by entity types**: Reduces noise and improves relevance
- **Adjust max_nodes/max_facts**: Balance between comprehensiveness and speed
- **Search both nodes and facts**: Nodes for entities, facts for relationships

### 4. Performance
- **Batch operations**: Add multiple episodes with small delays between calls
- **Monitor queue sizes**: Check `get_queue_size()` if processing seems slow
- **Use appropriate max_tokens**: Higher values for complex entity extraction
- **Consider provider limits**: Rate limits vary by provider

### 5. Configuration
- **Use environment variables for secrets**: Never commit API keys to version control
- **YAML for structure**: Provider configs, entity types, defaults
- **Validate configuration**: Run `get_status` after deployment
- **Document custom entity types**: Clear descriptions improve LLM extraction

### 6. Error Handling
- **Always check for ErrorResponse**: Tools return error objects, not exceptions
- **Implement retries for transient errors**: Network issues, rate limits
- **Log errors with context**: Include tool name, parameters, and error message
- **Monitor background processing**: Episode addition is async - check logs

### 7. Testing
- **Use separate group IDs for testing**: `test-*` prefix recommended
- **Clean up test data**: Use `clear_graph` after tests
- **Verify connectivity**: Run health checks before test suites
- **Test with sample data**: Start small before production workloads

### 8. Security
- **Secure API keys**: Use environment variables, secret managers, or Azure AD
- **Validate input**: Especially for user-provided episode content
- **Use HTTPS in production**: Protect data in transit
- **Implement rate limiting**: Prevent abuse of public endpoints

### 9. Monitoring
- **Track episode processing**: Monitor queue sizes and processing times
- **Watch database connections**: Check pool sizes and connection errors
- **Monitor LLM usage**: Track token consumption and costs
- **Set up health check endpoints**: Use `get_status` for uptime monitoring

### 10. Deployment
- **Use factory pattern**: Required for FastMCP Cloud deployment
- **Configure logging levels**: INFO for production, DEBUG for troubleshooting
- **Set appropriate timeouts**: Balance between reliability and responsiveness
- **Plan for scaling**: Consider database capacity and LLM rate limits

---

## Index

### Tools
- [add_memory](#add_memory) - Add episodes to memory
- [clear_graph](#clear_graph) - Clear graph data
- [delete_entity_edge](#delete_entity_edge) - Delete relationship edges
- [delete_episode](#delete_episode) - Delete episodes
- [get_entity_edge](#get_entity_edge) - Retrieve specific edges
- [get_episodes](#get_episodes) - Retrieve episodes
- [get_status](#get_status) - Health check
- [search_memory_facts](#search_memory_facts) - Search relationships
- [search_nodes](#search_nodes) - Search entities

### Services
- [GraphitiService](#graphitiservice) - Graphiti client manager
  - [initialize()](#initialize) - Initialize client
  - [get_client()](#get_client) - Get Graphiti instance
- [QueueService](#queueservice) - Episode queue manager
  - [initialize()](#initialize-1) - Initialize with client
  - [add_episode()](#add_episode) - Queue episode
  - [get_queue_size()](#get_queue_size) - Check queue
  - [is_worker_running()](#is_worker_running) - Check worker status

### Factories
- [LLMClientFactory](#llmclientfactory) - Create LLM clients
  - [create()](#create) - Factory method
- [EmbedderFactory](#embedderfactory) - Create embedder clients
  - [create()](#create-1) - Factory method
- [DatabaseDriverFactory](#databasedriverfactory) - Create database configs
  - [create_config()](#create_config) - Factory method

### Configuration
- [GraphitiConfig](#graphiticonfig) - Main configuration class
- [ServerConfig](#serverconfig) - Server settings
- [LLMConfig](#llmconfig) - LLM settings
- [EmbedderConfig](#embedderconfig) - Embedder settings
- [DatabaseConfig](#databaseconfig) - Database settings
- [GraphitiAppConfig](#graphitiappconfig) - Graphiti settings
- [EntityTypeConfig](#entitytypeconfig) - Entity type definition

### Data Models
- [ErrorResponse](#errorresponse) - Error result
- [SuccessResponse](#successresponse) - Success result
- [NodeResult](#noderesult) - Entity node structure
- [NodeSearchResponse](#nodesearchresponse) - Node search results
- [FactSearchResponse](#factsearchresponse) - Fact search results
- [EpisodeSearchResponse](#episodesearchresponse) - Episode results
- [StatusResponse](#statusresponse) - Health status

### Entity Types
- [Requirement](#requirement) - Project requirements
- [Preference](#preference) - User preferences
- [Procedure](#procedure) - Instructions and processes
- [Location](#location) - Physical/virtual places
- [Event](#event) - Time-bound activities
- [Object](#object) - Physical items
- [Topic](#topic) - Knowledge domains
- [Organization](#organization) - Companies and institutions
- [Document](#document) - Information content

### Utilities
- [format_node_result()](#format_node_result) - Format entity nodes
- [format_fact_result()](#format_fact_result) - Format relationship edges
- [create_azure_credential_token_provider()](#create_azure_credential_token_provider) - Azure AD authentication

---

## Additional Resources

**Source Code Locations**:
- Main Server: `src/server.py`
- Configuration: `src/config/schema.py`
- Factories: `src/services/factories.py`
- Queue Service: `src/services/queue_service.py`
- Response Types: `src/models/response_types.py`
- Entity Types: `src/models/entity_types.py`
- Utilities: `src/utils/`

**Examples**:
- Connection: `examples/01_connect_and_discover.py`
- Tool Usage: `examples/02_call_tools.py`
- Memory Operations: `examples/03_graphiti_memory.py`

**Documentation**:
- Component Inventory: `ra_output/architecture_20251130_170000/docs/01_component_inventory.md`
- Data Flows: `ra_output/architecture_20251130_170000/docs/03_data_flows.md`

**External Dependencies**:
- Graphiti Core: https://github.com/getzep/graphiti-core
- FastMCP: https://github.com/jlowin/fastmcp
- MCP Specification: https://modelcontextprotocol.io/

---

*This API reference covers the main project codebase (src/) and excludes analysis frameworks (ra_*/) and virtual environments (.venv/).*
