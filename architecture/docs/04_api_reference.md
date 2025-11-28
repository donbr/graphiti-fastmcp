# API Reference

## Overview

The Graphiti MCP Server exposes a comprehensive API for building knowledge graph-based AI agent memory systems. The API provides tools for adding information (episodes), searching entities (nodes) and relationships (facts), retrieving specific graph elements, and managing the knowledge graph lifecycle.

This reference documents all public APIs including:
- **MCP Tools**: FastMCP-decorated functions exposed to MCP clients
- **Configuration Classes**: Pydantic models for server, LLM, embedder, and database configuration
- **Response Types**: Type-safe response structures for all API operations
- **Service Classes**: Core service implementations for Graphiti operations and queue management
- **Factory Classes**: Factory methods for creating LLM, embedder, and database clients
- **Utility Functions**: Helper functions for formatting and authentication

## Table of Contents

1. [MCP Tools](#mcp-tools)
   - [add_memory](#add_memory)
   - [search_nodes](#search_nodes)
   - [search_memory_facts](#search_memory_facts)
   - [get_entity_edge](#get_entity_edge)
   - [get_episodes](#get_episodes)
   - [delete_entity_edge](#delete_entity_edge)
   - [delete_episode](#delete_episode)
   - [clear_graph](#clear_graph)
   - [get_status](#get_status)
2. [Configuration Classes](#configuration-classes)
   - [GraphitiConfig](#graphiticonfig)
   - [ServerConfig](#serverconfig)
   - [LLMConfig](#llmconfig)
   - [EmbedderConfig](#embedderconfig)
   - [DatabaseConfig](#databaseconfig)
   - [Provider Configurations](#provider-configurations)
3. [Response Types](#response-types)
   - [SuccessResponse](#successresponse)
   - [ErrorResponse](#errorresponse)
   - [NodeResult](#noderesult)
   - [NodeSearchResponse](#nodesearchresponse)
   - [FactSearchResponse](#factsearchresponse)
   - [EpisodeSearchResponse](#episodesearchresponse)
   - [StatusResponse](#statusresponse)
4. [Service Classes](#service-classes)
   - [GraphitiService](#graphitiservice)
   - [QueueService](#queueservice)
5. [Factory Classes](#factory-classes)
   - [LLMClientFactory](#llmclientfactory)
   - [EmbedderFactory](#embedderfactory)
   - [DatabaseDriverFactory](#databasedriverfactory)
6. [Utility Functions](#utility-functions)
   - [format_node_result](#format_node_result)
   - [format_fact_result](#format_fact_result)
   - [create_azure_credential_token_provider](#create_azure_credential_token_provider)
7. [Configuration Options](#configuration-options)
8. [Usage Patterns](#usage-patterns)
9. [Best Practices](#best-practices)

---

## MCP Tools

MCP Tools are the primary API endpoints exposed to MCP clients. All tools are async functions decorated with `@mcp.tool()`.

### add_memory

```python
@mcp.tool()
async def add_memory(
    name: str,
    episode_body: str,
    group_id: str | None = None,
    source: str = 'text',
    source_description: str = '',
    uuid: str | None = None,
) -> SuccessResponse | ErrorResponse:
```

**Description**: Add an episode to the knowledge graph. This is the primary way to add information. Episodes are processed asynchronously in the background, with sequential processing per group_id to avoid race conditions.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| name | str | Yes | Name of the episode (used for identification) |
| episode_body | str | Yes | Content of the episode. For JSON source, must be properly escaped JSON string |
| group_id | str \| None | No | Namespace for the graph. If not provided, uses default from config |
| source | str | No | Source type: 'text' (default), 'json', or 'message' |
| source_description | str | No | Description of where the content came from |
| uuid | str \| None | No | Optional UUID for the episode (auto-generated if not provided) |

**Returns**: `SuccessResponse | ErrorResponse`
- Success: Confirms episode was queued for processing
- Error: Contains error message if validation or queuing fails

**Example**:
```python
# Adding plain text content
result = await add_memory(
    name="Company News",
    episode_body="Acme Corp announced a new product line today.",
    source="text",
    source_description="news article",
    group_id="company_news"
)

# Adding structured JSON data
result = await add_memory(
    name="Customer Profile",
    episode_body='{"company": {"name": "Acme Technologies"}, "products": [{"id": "P001", "name": "CloudSync"}]}',
    source="json",
    source_description="CRM data"
)

# Adding conversation messages
result = await add_memory(
    name="Support Chat",
    episode_body="Customer asked about pricing for enterprise plan.",
    source="message",
    source_description="support ticket #1234"
)
```

**Source**: `src/graphiti_mcp_server.py:324-407`

---

### search_nodes

```python
@mcp.tool()
async def search_nodes(
    query: str,
    group_ids: list[str] | None = None,
    max_nodes: int = 10,
    entity_types: list[str] | None = None,
) -> NodeSearchResponse | ErrorResponse:
```

**Description**: Search for entity nodes (people, organizations, locations, etc.) in the knowledge graph using natural language queries. Uses hybrid search (vector + keyword) with reciprocal rank fusion (RRF).

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | str | Yes | Natural language search query |
| group_ids | list[str] \| None | No | Filter results to specific group IDs. Uses default if not provided |
| max_nodes | int | No | Maximum number of nodes to return (default: 10) |
| entity_types | list[str] \| None | No | Filter by entity type labels (e.g., ["Preference", "Organization"]) |

**Returns**: `NodeSearchResponse | ErrorResponse`
- Success: List of matching nodes with details
- Error: Contains error message if search fails

**Example**:
```python
# Basic node search
result = await search_nodes(
    query="Find all people who work at Acme Corp"
)

# Search with filters
result = await search_nodes(
    query="technology companies",
    entity_types=["Organization"],
    max_nodes=5,
    group_ids=["company_data"]
)

# Response structure:
# {
#     "message": "Nodes retrieved successfully",
#     "nodes": [
#         {
#             "uuid": "abc123...",
#             "name": "Acme Corp",
#             "labels": ["Organization"],
#             "created_at": "2024-01-15T10:30:00",
#             "summary": "Technology company specializing in...",
#             "group_id": "company_data",
#             "attributes": {...}
#         }
#     ]
# }
```

**Source**: `src/graphiti_mcp_server.py:410-487`

---

### search_memory_facts

```python
@mcp.tool()
async def search_memory_facts(
    query: str,
    group_ids: list[str] | None = None,
    max_facts: int = 10,
    center_node_uuid: str | None = None,
) -> FactSearchResponse | ErrorResponse:
```

**Description**: Search for facts (relationships/edges) in the knowledge graph. Facts represent connections between entities and contain temporal metadata indicating when they were created and whether they've been invalidated.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| query | str | Yes | Natural language search query describing the relationship |
| group_ids | list[str] \| None | No | Filter results to specific group IDs. Uses default if not provided |
| max_facts | int | No | Maximum number of facts to return (default: 10, must be > 0) |
| center_node_uuid | str \| None | No | UUID of a node to center the search around |

**Returns**: `FactSearchResponse | ErrorResponse`
- Success: List of matching facts with source/target nodes
- Error: Contains error message if search fails

**Example**:
```python
# Basic fact search
result = await search_memory_facts(
    query="Who are the founders of Acme Corp?"
)

# Search facts around a specific node
result = await search_memory_facts(
    query="relationships",
    center_node_uuid="abc123...",
    max_facts=5
)

# Response structure:
# {
#     "message": "Facts retrieved successfully",
#     "facts": [
#         {
#             "uuid": "def456...",
#             "name": "FOUNDED_BY",
#             "fact": "John Smith founded Acme Corp in 2010",
#             "valid_at": "2010-01-01T00:00:00",
#             "invalid_at": null,
#             "source_node_uuid": "abc123...",
#             "target_node_uuid": "xyz789...",
#             "group_id": "company_data"
#         }
#     ]
# }
```

**Source**: `src/graphiti_mcp_server.py:490-541`

---

### get_entity_edge

```python
@mcp.tool()
async def get_entity_edge(uuid: str) -> dict[str, Any] | ErrorResponse:
```

**Description**: Retrieve a specific entity edge (fact/relationship) by its UUID. Useful when you have a fact UUID from previous searches.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| uuid | str | Yes | UUID of the entity edge to retrieve |

**Returns**: `dict[str, Any] | ErrorResponse`
- Success: Dictionary containing complete edge details
- Error: Contains error message if edge not found or retrieval fails

**Example**:
```python
# Get a specific fact by UUID
edge = await get_entity_edge(uuid="def456...")

# Response:
# {
#     "uuid": "def456...",
#     "name": "WORKS_AT",
#     "fact": "John Smith works at Acme Corp as CEO",
#     "valid_at": "2020-01-15T10:30:00",
#     "invalid_at": null,
#     "source_node_uuid": "abc123...",
#     "target_node_uuid": "xyz789...",
#     "group_id": "company_data",
#     "episodes": ["episode1", "episode2"]
# }
```

**Source**: `src/graphiti_mcp_server.py:596-620`

---

### get_episodes

```python
@mcp.tool()
async def get_episodes(
    group_ids: list[str] | None = None,
    max_episodes: int = 10,
) -> EpisodeSearchResponse | ErrorResponse:
```

**Description**: Retrieve episodes from the knowledge graph. Episodes are the original content snippets that were added to the graph.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| group_ids | list[str] \| None | No | Filter to specific group IDs. Uses default if not provided |
| max_episodes | int | No | Maximum number of episodes to return (default: 10) |

**Returns**: `EpisodeSearchResponse | ErrorResponse`
- Success: List of episodes with content and metadata
- Error: Contains error message if retrieval fails

**Example**:
```python
# Get recent episodes
result = await get_episodes(max_episodes=5)

# Get episodes from specific groups
result = await get_episodes(
    group_ids=["company_news", "product_updates"],
    max_episodes=20
)

# Response structure:
# {
#     "message": "Episodes retrieved successfully",
#     "episodes": [
#         {
#             "uuid": "ep123...",
#             "name": "Company News",
#             "content": "Acme Corp announced...",
#             "created_at": "2024-01-15T10:30:00",
#             "source": "text",
#             "source_description": "news article",
#             "group_id": "company_news"
#         }
#     ]
# }
```

**Source**: `src/graphiti_mcp_server.py:623-688`

---

### delete_entity_edge

```python
@mcp.tool()
async def delete_entity_edge(uuid: str) -> SuccessResponse | ErrorResponse:
```

**Description**: Delete a specific entity edge (fact/relationship) from the knowledge graph by its UUID.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| uuid | str | Yes | UUID of the entity edge to delete |

**Returns**: `SuccessResponse | ErrorResponse`
- Success: Confirms successful deletion
- Error: Contains error message if edge not found or deletion fails

**Example**:
```python
# Delete a specific fact
result = await delete_entity_edge(uuid="def456...")
# {"message": "Entity edge with UUID def456... deleted successfully"}
```

**Source**: `src/graphiti_mcp_server.py:544-567`

---

### delete_episode

```python
@mcp.tool()
async def delete_episode(uuid: str) -> SuccessResponse | ErrorResponse:
```

**Description**: Delete a specific episode from the knowledge graph by its UUID.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| uuid | str | Yes | UUID of the episode to delete |

**Returns**: `SuccessResponse | ErrorResponse`
- Success: Confirms successful deletion
- Error: Contains error message if episode not found or deletion fails

**Example**:
```python
# Delete an episode
result = await delete_episode(uuid="ep123...")
# {"message": "Episode with UUID ep123... deleted successfully"}
```

**Source**: `src/graphiti_mcp_server.py:570-593`

---

### clear_graph

```python
@mcp.tool()
async def clear_graph(
    group_ids: list[str] | None = None
) -> SuccessResponse | ErrorResponse:
```

**Description**: Clear all data from the knowledge graph for specified group IDs. This is a destructive operation that removes all nodes, edges, and episodes.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| group_ids | list[str] \| None | No | List of group IDs to clear. If not provided, clears the default group |

**Returns**: `SuccessResponse | ErrorResponse`
- Success: Confirms successful clearing
- Error: Contains error message if no group IDs specified or operation fails

**Example**:
```python
# Clear default group
result = await clear_graph()

# Clear specific groups
result = await clear_graph(group_ids=["test_data", "old_data"])
# {"message": "Graph data cleared successfully for group IDs: test_data, old_data"}
```

**Source**: `src/graphiti_mcp_server.py:691-723`

---

### get_status

```python
@mcp.tool()
async def get_status() -> StatusResponse:
```

**Description**: Get the status of the Graphiti MCP server and verify database connectivity.

**Parameters**: None

**Returns**: `StatusResponse`
- Contains status ("ok" or "error") and descriptive message

**Example**:
```python
status = await get_status()
# {
#     "status": "ok",
#     "message": "Graphiti MCP server is running and connected to falkordb database"
# }
```

**Source**: `src/graphiti_mcp_server.py:726-756`

---

## Configuration Classes

Configuration classes use Pydantic models with support for YAML files, environment variables, and CLI arguments.

### GraphitiConfig

```python
class GraphitiConfig(BaseSettings):
    server: ServerConfig
    llm: LLMConfig
    embedder: EmbedderConfig
    database: DatabaseConfig
    graphiti: GraphitiAppConfig
    destroy_graph: bool = False
```

**Description**: Main configuration class that combines all subsystem configurations. Supports loading from YAML files with environment variable expansion.

**Fields**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| server | ServerConfig | ServerConfig() | Server transport and network settings |
| llm | LLMConfig | LLMConfig() | LLM provider and model configuration |
| embedder | EmbedderConfig | EmbedderConfig() | Embedder provider and model configuration |
| database | DatabaseConfig | DatabaseConfig() | Database provider and connection settings |
| graphiti | GraphitiAppConfig | GraphitiAppConfig() | Graphiti-specific settings (group_id, entity types) |
| destroy_graph | bool | False | Clear all graph data on startup (use with caution) |

**Configuration Priority** (highest to lowest):
1. CLI arguments
2. Environment variables
3. YAML configuration file
4. Default values

**Methods**:

#### apply_cli_overrides
```python
def apply_cli_overrides(self, args) -> None:
```
Apply command-line argument overrides to configuration.

**Example**:
```python
# Load from YAML with environment variable expansion
config = GraphitiConfig()

# Apply CLI overrides
import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--llm-provider', choices=['openai', 'anthropic'])
parser.add_argument('--model', help='Model name')
args = parser.parse_args()
config.apply_cli_overrides(args)

# Configuration is now ready
print(f"Using LLM: {config.llm.provider} / {config.llm.model}")
```

**Source**: `src/config/schema.py:230-293`

---

### ServerConfig

```python
class ServerConfig(BaseModel):
    transport: str = 'http'
    host: str = '0.0.0.0'
    port: int = 8000
```

**Description**: Server transport and network configuration.

**Fields**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| transport | str | 'http' | Transport type: 'http' (recommended), 'stdio', or 'sse' (deprecated) |
| host | str | '0.0.0.0' | Host address to bind to |
| port | int | 8000 | Port number to bind to |

**Example**:
```yaml
# In config.yaml
server:
  transport: "http"
  host: "0.0.0.0"
  port: 8000
```

**Source**: `src/config/schema.py:76-85`

---

### LLMConfig

```python
class LLMConfig(BaseModel):
    provider: str = 'openai'
    model: str = 'gpt-4.1'
    temperature: float | None = None
    max_tokens: int = 4096
    providers: LLMProvidersConfig = LLMProvidersConfig()
```

**Description**: Configuration for Language Model provider and settings.

**Fields**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| provider | str | 'openai' | LLM provider: 'openai', 'azure_openai', 'anthropic', 'gemini', 'groq' |
| model | str | 'gpt-4.1' | Model name to use |
| temperature | float \| None | None | Sampling temperature (0.0-2.0). None for reasoning models |
| max_tokens | int | 4096 | Maximum tokens in response |
| providers | LLMProvidersConfig | {} | Provider-specific configurations |

**Example**:
```yaml
# In config.yaml
llm:
  provider: "openai"
  model: "gpt-5-mini"
  temperature: null  # Auto-selected based on model type
  max_tokens: 4096

  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
      api_url: "https://api.openai.com/v1"
```

**Source**: `src/config/schema.py:146-156`

---

### EmbedderConfig

```python
class EmbedderConfig(BaseModel):
    provider: str = 'openai'
    model: str = 'text-embedding-3-small'
    dimensions: int = 1536
    providers: EmbedderProvidersConfig = EmbedderProvidersConfig()
```

**Description**: Configuration for embedding model provider and settings.

**Fields**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| provider | str | 'openai' | Embedder provider: 'openai', 'azure_openai', 'gemini', 'voyage' |
| model | str | 'text-embedding-3-small' | Embedding model name |
| dimensions | int | 1536 | Embedding vector dimensions |
| providers | EmbedderProvidersConfig | {} | Provider-specific configurations |

**Example**:
```yaml
# In config.yaml
embedder:
  provider: "openai"
  model: "text-embedding-3-small"
  dimensions: 1536

  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
```

**Source**: `src/config/schema.py:167-174`

---

### DatabaseConfig

```python
class DatabaseConfig(BaseModel):
    provider: str = 'falkordb'
    providers: DatabaseProvidersConfig = DatabaseProvidersConfig()
```

**Description**: Configuration for graph database provider and connection settings.

**Fields**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| provider | str | 'falkordb' | Database provider: 'neo4j', 'falkordb' |
| providers | DatabaseProvidersConfig | {} | Provider-specific configurations |

**Example**:
```yaml
# In config.yaml
database:
  provider: "falkordb"

  providers:
    falkordb:
      uri: ${FALKORDB_URI:redis://localhost:6379}
      username: ${FALKORDB_USER:}
      password: ${FALKORDB_PASSWORD:}
      database: ${FALKORDB_DATABASE:default_db}

    neo4j:
      uri: ${NEO4J_URI:bolt://localhost:7687}
      username: ${NEO4J_USER:neo4j}
      password: ${NEO4J_PASSWORD}
      database: ${NEO4J_DATABASE:neo4j}
```

**Source**: `src/config/schema.py:202-207`

---

### Provider Configurations

#### OpenAIProviderConfig
```python
class OpenAIProviderConfig(BaseModel):
    api_key: str | None = None
    api_url: str = 'https://api.openai.com/v1'
    organization_id: str | None = None
```

**Source**: `src/config/schema.py:87-93`

#### AzureOpenAIProviderConfig
```python
class AzureOpenAIProviderConfig(BaseModel):
    api_key: str | None = None
    api_url: str | None = None
    api_version: str = '2024-10-21'
    deployment_name: str | None = None
    use_azure_ad: bool = False
```

**Source**: `src/config/schema.py:95-103`

#### AnthropicProviderConfig
```python
class AnthropicProviderConfig(BaseModel):
    api_key: str | None = None
    api_url: str = 'https://api.anthropic.com'
    max_retries: int = 3
```

**Source**: `src/config/schema.py:105-111`

#### GeminiProviderConfig
```python
class GeminiProviderConfig(BaseModel):
    api_key: str | None = None
    project_id: str | None = None
    location: str = 'us-central1'
```

**Source**: `src/config/schema.py:113-119`

#### GroqProviderConfig
```python
class GroqProviderConfig(BaseModel):
    api_key: str | None = None
    api_url: str = 'https://api.groq.com/openai/v1'
```

**Source**: `src/config/schema.py:121-126`

#### VoyageProviderConfig
```python
class VoyageProviderConfig(BaseModel):
    api_key: str | None = None
    api_url: str = 'https://api.voyageai.com/v1'
    model: str = 'voyage-3'
```

**Source**: `src/config/schema.py:128-134`

#### Neo4jProviderConfig
```python
class Neo4jProviderConfig(BaseModel):
    uri: str = 'bolt://localhost:7687'
    username: str = 'neo4j'
    password: str | None = None
    database: str = 'neo4j'
    use_parallel_runtime: bool = False
```

**Source**: `src/config/schema.py:176-184`

#### FalkorDBProviderConfig
```python
class FalkorDBProviderConfig(BaseModel):
    uri: str = 'redis://localhost:6379'
    username: str | None = None
    password: str | None = None
    database: str = 'default_db'
```

**Source**: `src/config/schema.py:186-193`

#### GraphitiAppConfig
```python
class GraphitiAppConfig(BaseModel):
    group_id: str = 'main'
    episode_id_prefix: str | None = ''
    user_id: str = 'mcp_user'
    entity_types: list[EntityTypeConfig] = []
```

**Fields**:
| Field | Type | Default | Description |
|-------|------|---------|-------------|
| group_id | str | 'main' | Default namespace for graph data |
| episode_id_prefix | str \| None | '' | Optional prefix for episode IDs |
| user_id | str | 'mcp_user' | User ID for tracking operations |
| entity_types | list[EntityTypeConfig] | [] | Custom entity type definitions |

**Source**: `src/config/schema.py:216-228`

#### EntityTypeConfig
```python
class EntityTypeConfig(BaseModel):
    name: str
    description: str
```

**Description**: Defines custom entity types for extraction from episodes.

**Example**:
```yaml
graphiti:
  entity_types:
    - name: "Preference"
      description: "User preferences, choices, or selections"
    - name: "Organization"
      description: "Companies, institutions, or groups"
```

**Source**: `src/config/schema.py:209-214`

---

## Response Types

All response types are TypedDict classes for type-safe API responses.

### SuccessResponse

```python
class SuccessResponse(TypedDict):
    message: str
```

**Description**: Standard success response containing a descriptive message.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| message | str | Success message describing the operation result |

**Source**: `src/models/response_types.py:12-14`

---

### ErrorResponse

```python
class ErrorResponse(TypedDict):
    error: str
```

**Description**: Standard error response containing error details.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| error | str | Error message describing what went wrong |

**Source**: `src/models/response_types.py:8-10`

---

### NodeResult

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

**Description**: Represents a single entity node from the knowledge graph.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| uuid | str | Unique identifier for the node |
| name | str | Human-readable name of the entity |
| labels | list[str] | Entity type labels (e.g., ["Organization"], ["Preference"]) |
| created_at | str \| None | ISO-8601 timestamp of node creation |
| summary | str \| None | AI-generated summary of the entity |
| group_id | str | Group/namespace the node belongs to |
| attributes | dict[str, Any] | Additional properties (excludes embeddings) |

**Source**: `src/models/response_types.py:16-24`

---

### NodeSearchResponse

```python
class NodeSearchResponse(TypedDict):
    message: str
    nodes: list[NodeResult]
```

**Description**: Response from node search operations.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| message | str | Status message |
| nodes | list[NodeResult] | List of matching nodes |

**Source**: `src/models/response_types.py:26-29`

---

### FactSearchResponse

```python
class FactSearchResponse(TypedDict):
    message: str
    facts: list[dict[str, Any]]
```

**Description**: Response from fact (edge) search operations.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| message | str | Status message |
| facts | list[dict[str, Any]] | List of matching facts/edges. Each fact contains: uuid, name, fact, valid_at, invalid_at, source_node_uuid, target_node_uuid, group_id |

**Source**: `src/models/response_types.py:31-34`

---

### EpisodeSearchResponse

```python
class EpisodeSearchResponse(TypedDict):
    message: str
    episodes: list[dict[str, Any]]
```

**Description**: Response from episode retrieval operations.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| message | str | Status message |
| episodes | list[dict[str, Any]] | List of episodes. Each episode contains: uuid, name, content, created_at, source, source_description, group_id |

**Source**: `src/models/response_types.py:36-39`

---

### StatusResponse

```python
class StatusResponse(TypedDict):
    status: str
    message: str
```

**Description**: Response from server status check.

**Fields**:
| Field | Type | Description |
|-------|------|-------------|
| status | str | Status: "ok" or "error" |
| message | str | Detailed status message |

**Source**: `src/models/response_types.py:41-44`

---

## Service Classes

### GraphitiService

```python
class GraphitiService:
    def __init__(self, config: GraphitiConfig, semaphore_limit: int = 10):
        ...
```

**Description**: Core service managing Graphiti client lifecycle and operations. Handles initialization of LLM, embedder, and database clients using factory pattern.

**Attributes**:
| Attribute | Type | Description |
|-----------|------|-------------|
| config | GraphitiConfig | Configuration object |
| semaphore_limit | int | Max concurrent Graphiti operations |
| semaphore | asyncio.Semaphore | Semaphore for concurrency control |
| client | Graphiti \| None | Initialized Graphiti client |
| entity_types | dict \| None | Custom entity type definitions |

**Methods**:

#### initialize
```python
async def initialize(self) -> None:
```

**Description**: Initialize the Graphiti client with factory-created LLM, embedder, and database components. Builds indices and constraints. Provides detailed error messages for connection failures.

**Raises**:
- `RuntimeError`: If database is not accessible (with provider-specific help)
- `Exception`: For other initialization failures

**Example**:
```python
config = GraphitiConfig()
service = GraphitiService(config, semaphore_limit=10)
await service.initialize()
# Logs: Successfully initialized Graphiti client
# Logs: Using LLM provider: openai / gpt-5-mini
# Logs: Using Embedder provider: openai
# Logs: Using database: falkordb
```

**Source**: `src/graphiti_mcp_server.py:172-313`

#### get_client
```python
async def get_client(self) -> Graphiti:
```

**Description**: Get the Graphiti client, initializing if necessary. Safe to call multiple times.

**Returns**: `Graphiti` - Initialized Graphiti client instance

**Raises**:
- `RuntimeError`: If client initialization fails

**Example**:
```python
client = await service.get_client()
# Use client for graph operations
```

**Source**: `src/graphiti_mcp_server.py:314-321`

**Source**: `src/graphiti_mcp_server.py:162-321`

---

### QueueService

```python
class QueueService:
    def __init__(self):
        ...
```

**Description**: Manages sequential episode processing queues by group_id. Ensures episodes for the same group are processed in order to avoid race conditions while allowing parallel processing across different groups.

**Attributes**:
| Attribute | Type | Description |
|-----------|------|-------------|
| _episode_queues | dict[str, asyncio.Queue] | Queues per group_id |
| _queue_workers | dict[str, bool] | Worker status per group_id |
| _graphiti_client | Any | Graphiti client for processing |

**Methods**:

#### initialize
```python
async def initialize(self, graphiti_client: Any) -> None:
```

**Description**: Initialize the queue service with a Graphiti client.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| graphiti_client | Any | Yes | Graphiti client instance for processing episodes |

**Source**: `src/services/queue_service.py:92-100`

#### add_episode
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
) -> int:
```

**Description**: Add an episode for asynchronous processing. Episodes are queued and processed sequentially per group_id.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| group_id | str | Yes | Group ID namespace |
| name | str | Yes | Episode name |
| content | str | Yes | Episode content |
| source_description | str | Yes | Source description |
| episode_type | Any | Yes | EpisodeType enum value |
| entity_types | Any | Yes | Entity types for extraction |
| uuid | str \| None | Yes | Episode UUID (can be None) |

**Returns**: `int` - Position in the queue

**Raises**:
- `RuntimeError`: If service not initialized

**Example**:
```python
queue_service = QueueService()
await queue_service.initialize(graphiti_client)

position = await queue_service.add_episode(
    group_id="main",
    name="Meeting Notes",
    content="Discussed Q4 strategy...",
    source_description="Zoom meeting",
    episode_type=EpisodeType.text,
    entity_types=custom_types,
    uuid="abc123"
)
# Returns: 1 (first in queue for this group_id)
```

**Source**: `src/services/queue_service.py:101-153`

#### add_episode_task
```python
async def add_episode_task(
    self, group_id: str, process_func: Callable[[], Awaitable[None]]
) -> int:
```

**Description**: Add a generic episode processing task to the queue. Lower-level method used internally by add_episode.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| group_id | str | Yes | Group ID for the task |
| process_func | Callable[[], Awaitable[None]] | Yes | Async function to process the episode |

**Returns**: `int` - Position in queue

**Source**: `src/services/queue_service.py:24-48`

#### get_queue_size
```python
def get_queue_size(self, group_id: str) -> int:
```

**Description**: Get the current queue size for a group_id.

**Returns**: `int` - Number of episodes waiting in queue

**Source**: `src/services/queue_service.py:82-87`

#### is_worker_running
```python
def is_worker_running(self, group_id: str) -> bool:
```

**Description**: Check if a worker is running for a group_id.

**Returns**: `bool` - True if worker is active

**Source**: `src/services/queue_service.py:88-91`

**Source**: `src/services/queue_service.py:12-153`

---

## Factory Classes

Factory classes create configured instances of LLM clients, embedders, and database drivers.

### LLMClientFactory

```python
class LLMClientFactory:
    @staticmethod
    def create(config: LLMConfig) -> LLMClient:
        ...
```

**Description**: Factory for creating LLM clients based on configuration. Supports OpenAI, Azure OpenAI, Anthropic, Gemini, and Groq providers.

**Methods**:

#### create
```python
@staticmethod
def create(config: LLMConfig) -> LLMClient:
```

**Description**: Create an LLM client based on configured provider. Automatically selects appropriate small model and handles reasoning model configuration.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| config | LLMConfig | Yes | LLM configuration object |

**Returns**: `LLMClient` - Provider-specific LLM client instance

**Raises**:
- `ValueError`: If provider not supported or configuration missing
- `ValueError`: If API key not configured

**Supported Providers**:
- `openai`: OpenAI API (including GPT-5 reasoning models)
- `azure_openai`: Azure OpenAI Service (with optional Azure AD auth)
- `anthropic`: Anthropic Claude models
- `gemini`: Google Gemini models
- `groq`: Groq API

**Example**:
```python
from config.schema import LLMConfig, OpenAIProviderConfig

# Configure OpenAI
llm_config = LLMConfig(
    provider="openai",
    model="gpt-5-mini",
    temperature=None,  # Auto for reasoning models
    max_tokens=4096
)
llm_config.providers.openai = OpenAIProviderConfig(
    api_key="sk-..."
)

# Create client
llm_client = LLMClientFactory.create(llm_config)

# For reasoning models (gpt-5*, o1*, o3*), the factory automatically:
# - Sets reasoning='minimal' and verbosity='low'
# - Uses gpt-5-nano as small_model
# For non-reasoning models, these parameters are disabled
```

**Source**: `src/services/factories.py:100-251`

---

### EmbedderFactory

```python
class EmbedderFactory:
    @staticmethod
    def create(config: EmbedderConfig) -> EmbedderClient:
        ...
```

**Description**: Factory for creating embedding clients based on configuration. Supports OpenAI, Azure OpenAI, Gemini, and Voyage providers.

**Methods**:

#### create
```python
@staticmethod
def create(config: EmbedderConfig) -> EmbedderClient:
```

**Description**: Create an embedder client based on configured provider.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| config | EmbedderConfig | Yes | Embedder configuration object |

**Returns**: `EmbedderClient` - Provider-specific embedder client instance

**Raises**:
- `ValueError`: If provider not supported or configuration missing
- `ValueError`: If API key not configured

**Supported Providers**:
- `openai`: OpenAI embeddings (text-embedding-3-small, text-embedding-3-large)
- `azure_openai`: Azure OpenAI embeddings (with optional Azure AD auth)
- `gemini`: Google Gemini embeddings (text-embedding-004)
- `voyage`: Voyage AI embeddings (voyage-3)

**Example**:
```python
from config.schema import EmbedderConfig, OpenAIProviderConfig

# Configure OpenAI embedder
embedder_config = EmbedderConfig(
    provider="openai",
    model="text-embedding-3-small",
    dimensions=1536
)
embedder_config.providers.openai = OpenAIProviderConfig(
    api_key="sk-..."
)

# Create client
embedder = EmbedderFactory.create(embedder_config)
```

**Source**: `src/services/factories.py:253-361`

---

### DatabaseDriverFactory

```python
class DatabaseDriverFactory:
    @staticmethod
    def create_config(config: DatabaseConfig) -> dict:
        ...
```

**Description**: Factory for creating database driver configurations. Returns configuration dictionaries that can be passed to Graphiti(), not driver instances directly.

**Methods**:

#### create_config
```python
@staticmethod
def create_config(config: DatabaseConfig) -> dict:
```

**Description**: Create database configuration dictionary based on configured provider. Supports environment variable overrides for CI/CD compatibility.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| config | DatabaseConfig | Yes | Database configuration object |

**Returns**: `dict` - Configuration dictionary with provider-specific keys

**Raises**:
- `ValueError`: If provider not supported or configuration missing

**Supported Providers**:
- `neo4j`: Neo4j graph database
- `falkordb`: FalkorDB (Redis-based graph database)

**Return Structure**:

For Neo4j:
```python
{
    'uri': 'bolt://localhost:7687',
    'user': 'neo4j',
    'password': 'password'
}
```

For FalkorDB:
```python
{
    'driver': 'falkordb',
    'host': 'localhost',
    'port': 6379,
    'username': None,
    'password': None,
    'database': 'default_db'
}
```

**Example**:
```python
from config.schema import DatabaseConfig, FalkorDBProviderConfig

# Configure FalkorDB
db_config = DatabaseConfig(provider="falkordb")
db_config.providers.falkordb = FalkorDBProviderConfig(
    uri="redis://localhost:6379",
    database="my_graph"
)

# Create configuration dictionary
config_dict = DatabaseDriverFactory.create_config(db_config)

# Environment variable overrides are automatically applied:
# FALKORDB_URI, FALKORDB_USER, FALKORDB_PASSWORD
# NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD
```

**Source**: `src/services/factories.py:363-440`

---

## Utility Functions

### format_node_result

```python
def format_node_result(node: EntityNode) -> dict[str, Any]:
```

**Description**: Format an entity node into a serializable dictionary. Excludes embedding vectors to reduce payload size and avoid exposing internal representations.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| node | EntityNode | Yes | The EntityNode to format |

**Returns**: `dict[str, Any]` - Dictionary representation with serialized dates and excluded embeddings

**Example**:
```python
from graphiti_core.nodes import EntityNode

# Get a node from Graphiti
node = await client.get_node(uuid="abc123...")

# Format for API response
formatted = format_node_result(node)
# {
#     'uuid': 'abc123...',
#     'name': 'Acme Corp',
#     'labels': ['Organization'],
#     'created_at': '2024-01-15T10:30:00',
#     'summary': 'Technology company...',
#     'attributes': {...}
#     # 'name_embedding' excluded
# }
```

**Source**: `src/utils/formatting.py:9-30`

---

### format_fact_result

```python
def format_fact_result(edge: EntityEdge) -> dict[str, Any]:
```

**Description**: Format an entity edge (fact/relationship) into a serializable dictionary. Excludes embedding vectors to reduce payload size.

**Parameters**:
| Name | Type | Required | Description |
|------|------|----------|-------------|
| edge | EntityEdge | Yes | The EntityEdge to format |

**Returns**: `dict[str, Any]` - Dictionary representation with serialized dates and excluded embeddings

**Example**:
```python
from graphiti_core.edges import EntityEdge

# Get an edge from Graphiti
edge = await EntityEdge.get_by_uuid(driver, uuid="def456...")

# Format for API response
formatted = format_fact_result(edge)
# {
#     'uuid': 'def456...',
#     'name': 'WORKS_AT',
#     'fact': 'John Smith works at Acme Corp',
#     'valid_at': '2020-01-15T10:30:00',
#     'invalid_at': null,
#     'source_node_uuid': 'abc123...',
#     'target_node_uuid': 'xyz789...',
#     'attributes': {...}
#     # 'fact_embedding' excluded
# }
```

**Source**: `src/utils/formatting.py:32-51`

---

### create_azure_credential_token_provider

```python
def create_azure_credential_token_provider() -> Callable[[], str]:
```

**Description**: Create Azure credential token provider for managed identity authentication. Uses DefaultAzureCredential to support multiple authentication methods (managed identity, Azure CLI, environment variables, etc.).

**Returns**: `Callable[[], str]` - Token provider function for Azure OpenAI client

**Raises**:
- `ImportError`: If azure-identity package not installed

**Requirements**: Install with `pip install mcp-server[azure]` or `pip install azure-identity`

**Example**:
```python
# Configure Azure OpenAI with managed identity
if use_azure_ad:
    token_provider = create_azure_credential_token_provider()

    azure_client = AsyncAzureOpenAI(
        azure_endpoint="https://your-resource.openai.azure.com",
        api_version="2024-10-21",
        azure_ad_token_provider=token_provider  # No API key needed
    )
else:
    # Use API key authentication
    azure_client = AsyncAzureOpenAI(
        api_key="...",
        azure_endpoint="https://your-resource.openai.azure.com"
    )
```

**Source**: `src/utils/utils.py:6-28`

---

## Configuration Options

### Environment Variables

The server supports configuration via environment variables, YAML files, and CLI arguments. Environment variables can be referenced in YAML using `${VAR_NAME}` or `${VAR_NAME:default}` syntax.

#### Core Settings

| Variable | Description | Default |
|----------|-------------|---------|
| CONFIG_PATH | Path to YAML configuration file | config/config.yaml |
| SEMAPHORE_LIMIT | Max concurrent episode processing operations | 10 |

#### Server Settings

| Variable | Description | Default |
|----------|-------------|---------|
| SERVER__TRANSPORT | Transport type: http, stdio, or sse | http |
| SERVER__HOST | Server host address | 0.0.0.0 |
| SERVER__PORT | Server port number | 8000 |

#### LLM Provider Settings

| Variable | Description | Default |
|----------|-------------|---------|
| LLM__PROVIDER | LLM provider name | openai |
| LLM__MODEL | Model name | gpt-4.1 |
| LLM__TEMPERATURE | Sampling temperature | null |
| LLM__MAX_TOKENS | Maximum tokens | 4096 |
| OPENAI_API_KEY | OpenAI API key | - |
| OPENAI_API_URL | OpenAI API base URL | https://api.openai.com/v1 |
| OPENAI_ORGANIZATION_ID | OpenAI organization ID | - |
| AZURE_OPENAI_API_KEY | Azure OpenAI API key | - |
| AZURE_OPENAI_ENDPOINT | Azure OpenAI endpoint URL | - |
| AZURE_OPENAI_API_VERSION | Azure OpenAI API version | 2024-10-21 |
| AZURE_OPENAI_DEPLOYMENT | Azure OpenAI deployment name | - |
| USE_AZURE_AD | Use Azure AD authentication | false |
| ANTHROPIC_API_KEY | Anthropic API key | - |
| ANTHROPIC_API_URL | Anthropic API base URL | https://api.anthropic.com |
| GOOGLE_API_KEY | Google/Gemini API key | - |
| GOOGLE_PROJECT_ID | Google Cloud project ID | - |
| GOOGLE_LOCATION | Google Cloud location | us-central1 |
| GROQ_API_KEY | Groq API key | - |
| GROQ_API_URL | Groq API base URL | https://api.groq.com/openai/v1 |

#### Embedder Provider Settings

| Variable | Description | Default |
|----------|-------------|---------|
| EMBEDDER__PROVIDER | Embedder provider name | openai |
| EMBEDDER__MODEL | Embedding model name | text-embedding-3-small |
| EMBEDDER__DIMENSIONS | Embedding dimensions | 1536 |
| VOYAGE_API_KEY | Voyage AI API key | - |
| VOYAGE_API_URL | Voyage AI API base URL | https://api.voyageai.com/v1 |

#### Database Settings

| Variable | Description | Default |
|----------|-------------|---------|
| DATABASE__PROVIDER | Database provider | falkordb |
| FALKORDB_URI | FalkorDB connection URI | redis://localhost:6379 |
| FALKORDB_USER | FalkorDB username | - |
| FALKORDB_PASSWORD | FalkorDB password | - |
| FALKORDB_DATABASE | FalkorDB database name | default_db |
| NEO4J_URI | Neo4j connection URI | bolt://localhost:7687 |
| NEO4J_USER | Neo4j username | neo4j |
| NEO4J_PASSWORD | Neo4j password | - |
| NEO4J_DATABASE | Neo4j database name | neo4j |
| USE_PARALLEL_RUNTIME | Use Neo4j parallel runtime | false |

#### Graphiti Settings

| Variable | Description | Default |
|----------|-------------|---------|
| GRAPHITI__GROUP_ID | Default namespace for graph data | main |
| GRAPHITI__EPISODE_ID_PREFIX | Prefix for episode IDs | - |
| GRAPHITI__USER_ID | User ID for operations | mcp_user |

### YAML Configuration

The recommended way to configure the server is through a YAML file (default: `config/config.yaml`).

```yaml
# config/config.yaml
server:
  transport: "http"
  host: "0.0.0.0"
  port: 8000

llm:
  provider: "openai"
  model: "gpt-5-mini"
  max_tokens: 4096

  providers:
    openai:
      api_key: ${OPENAI_API_KEY}
      api_url: ${OPENAI_API_URL:https://api.openai.com/v1}

embedder:
  provider: "openai"
  model: "text-embedding-3-small"
  dimensions: 1536

  providers:
    openai:
      api_key: ${OPENAI_API_KEY}

database:
  provider: "falkordb"

  providers:
    falkordb:
      uri: ${FALKORDB_URI:redis://localhost:6379}
      database: ${FALKORDB_DATABASE:default_db}

graphiti:
  group_id: ${GRAPHITI_GROUP_ID:main}
  user_id: ${USER_ID:mcp_user}
  entity_types:
    - name: "Preference"
      description: "User preferences and choices"
    - name: "Organization"
      description: "Companies and institutions"
```

### CLI Arguments

Command-line arguments override both environment variables and YAML configuration.

| Argument | Description | Example |
|----------|-------------|---------|
| --config | Path to YAML config file | --config /path/to/config.yaml |
| --transport | Transport type | --transport http |
| --host | Server host | --host 0.0.0.0 |
| --port | Server port | --port 8000 |
| --llm-provider | LLM provider | --llm-provider openai |
| --model | LLM model name | --model gpt-5-mini |
| --temperature | LLM temperature | --temperature 0.7 |
| --embedder-provider | Embedder provider | --embedder-provider openai |
| --embedder-model | Embedder model | --embedder-model text-embedding-3-small |
| --database-provider | Database provider | --database-provider falkordb |
| --group-id | Graph namespace | --group-id my_group |
| --user-id | User ID | --user-id user123 |
| --destroy-graph | Clear graph on startup | --destroy-graph |

**Example**:
```bash
python src/graphiti_mcp_server.py \
  --config config/production.yaml \
  --llm-provider openai \
  --model gpt-5-mini \
  --transport http \
  --port 8080 \
  --group-id production_data
```

---

## Usage Patterns

### Basic Setup

```python
import asyncio
from config.schema import GraphitiConfig
from services.factories import LLMClientFactory, EmbedderFactory

async def setup_graphiti():
    # Load configuration (from YAML + env vars)
    config = GraphitiConfig()

    # Create service
    from graphiti_mcp_server import GraphitiService
    service = GraphitiService(config, semaphore_limit=10)

    # Initialize
    await service.initialize()

    # Get client
    client = await service.get_client()
    return client

# Run setup
client = asyncio.run(setup_graphiti())
```

### Custom Configuration

```python
from config.schema import (
    GraphitiConfig,
    LLMConfig,
    EmbedderConfig,
    DatabaseConfig,
    OpenAIProviderConfig,
    FalkorDBProviderConfig
)

# Build configuration programmatically
config = GraphitiConfig()

# Configure LLM
config.llm = LLMConfig(
    provider="openai",
    model="gpt-5-mini",
    temperature=None,  # Auto for reasoning models
    max_tokens=4096
)
config.llm.providers.openai = OpenAIProviderConfig(
    api_key="sk-...",
    api_url="https://api.openai.com/v1"
)

# Configure Embedder
config.embedder = EmbedderConfig(
    provider="openai",
    model="text-embedding-3-small",
    dimensions=1536
)
config.embedder.providers.openai = OpenAIProviderConfig(
    api_key="sk-..."
)

# Configure Database
config.database = DatabaseConfig(provider="falkordb")
config.database.providers.falkordb = FalkorDBProviderConfig(
    uri="redis://localhost:6379",
    database="my_graph"
)

# Configure Graphiti app settings
config.graphiti.group_id = "my_namespace"
config.graphiti.user_id = "user123"

# Use the configuration
service = GraphitiService(config)
await service.initialize()
```

### Error Handling

```python
from models.response_types import ErrorResponse, SuccessResponse

async def safe_add_memory(name: str, content: str):
    """Add memory with comprehensive error handling."""
    try:
        result = await add_memory(
            name=name,
            episode_body=content,
            source="text"
        )

        # Check if error response
        if isinstance(result, dict) and 'error' in result:
            print(f"Error: {result['error']}")
            return None

        # Success
        print(f"Success: {result['message']}")
        return result

    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

# Usage
await safe_add_memory("Meeting", "Discussed Q4 strategy")
```

### Working with Search Results

```python
async def search_and_analyze():
    # Search for nodes
    nodes_result = await search_nodes(
        query="technology companies",
        entity_types=["Organization"],
        max_nodes=10
    )

    if 'error' not in nodes_result:
        for node in nodes_result['nodes']:
            print(f"Found: {node['name']}")
            print(f"  UUID: {node['uuid']}")
            print(f"  Summary: {node['summary']}")
            print(f"  Created: {node['created_at']}")

            # Get facts about this node
            facts_result = await search_memory_facts(
                query="relationships",
                center_node_uuid=node['uuid'],
                max_facts=5
            )

            if 'error' not in facts_result:
                print(f"  Related facts:")
                for fact in facts_result['facts']:
                    print(f"    - {fact['fact']}")

await search_and_analyze()
```

### Queue Monitoring

```python
from services.queue_service import QueueService

# Access queue service
queue_service = QueueService()
await queue_service.initialize(graphiti_client)

# Add episodes
await queue_service.add_episode(
    group_id="main",
    name="Episode 1",
    content="Content...",
    source_description="test",
    episode_type=EpisodeType.text,
    entity_types=None,
    uuid=None
)

# Monitor queue
group_id = "main"
queue_size = queue_service.get_queue_size(group_id)
is_processing = queue_service.is_worker_running(group_id)

print(f"Queue size: {queue_size}")
print(f"Worker active: {is_processing}")
```

### Managing Multiple Namespaces

```python
# Add data to different namespaces
await add_memory(
    name="Customer A Info",
    episode_body="Customer A prefers email communication",
    group_id="customer_a"
)

await add_memory(
    name="Customer B Info",
    episode_body="Customer B prefers phone calls",
    group_id="customer_b"
)

# Search within specific namespace
result = await search_nodes(
    query="communication preferences",
    group_ids=["customer_a"]
)

# Search across multiple namespaces
result = await search_nodes(
    query="communication preferences",
    group_ids=["customer_a", "customer_b"]
)

# Clear specific namespace
await clear_graph(group_ids=["test_data"])
```

---

## Best Practices

### 1. Configuration Management

**DO**: Use YAML configuration files with environment variable expansion
```yaml
llm:
  providers:
    openai:
      api_key: ${OPENAI_API_KEY}  # Reference env var
```

**DON'T**: Hard-code API keys in configuration files
```yaml
llm:
  providers:
    openai:
      api_key: "sk-1234..."  # Never do this!
```

### 2. Concurrency Control

**DO**: Tune SEMAPHORE_LIMIT based on your LLM provider's rate limits

```bash
# For OpenAI Tier 1 (free): 3 RPM
export SEMAPHORE_LIMIT=1

# For OpenAI Tier 3: 500 RPM
export SEMAPHORE_LIMIT=10

# For Anthropic high tier: 1,000 RPM
export SEMAPHORE_LIMIT=20
```

**Symptoms of incorrect settings**:
- Too high: 429 rate limit errors, increased costs
- Too low: Slow throughput, underutilized API quota

**Source**: `src/graphiti_mcp_server.py:49-76`

### 3. Namespace (group_id) Organization

**DO**: Use logical namespaces to separate different data domains

```python
# Separate by customer
await add_memory(name="...", episode_body="...", group_id="customer_123")

# Separate by project
await add_memory(name="...", episode_body="...", group_id="project_alpha")

# Separate by environment
await add_memory(name="...", episode_body="...", group_id="production")
```

**DON'T**: Mix unrelated data in the same namespace

```python
# Bad: mixing customer and internal data
await add_memory(name="Customer data", episode_body="...", group_id="main")
await add_memory(name="Internal meeting", episode_body="...", group_id="main")
```

### 4. Episode Content Structure

**DO**: Provide descriptive names and rich content

```python
await add_memory(
    name="Q4 2024 Sales Meeting Notes",
    episode_body="Team discussed Q4 targets. Key points: increase focus on enterprise clients, new product launch in November, hiring 3 sales reps.",
    source="text",
    source_description="Sales team meeting on 2024-10-15"
)
```

**DON'T**: Use vague names or minimal content

```python
await add_memory(
    name="Meeting",
    episode_body="Stuff discussed",
    source="text"
)
```

### 5. JSON Episode Formatting

**DO**: Provide properly escaped JSON strings

```python
import json

data = {
    "customer": {"name": "Acme Corp"},
    "products": [{"id": "P001", "name": "Widget"}]
}

await add_memory(
    name="Customer Data",
    episode_body=json.dumps(data),  # Proper JSON string
    source="json",
    source_description="CRM export"
)
```

**DON'T**: Pass raw dictionaries or unescaped JSON

```python
# Wrong: passing dict instead of JSON string
await add_memory(
    name="Customer Data",
    episode_body={"customer": "Acme"},  # Will fail
    source="json"
)
```

### 6. Search Query Specificity

**DO**: Use specific, descriptive queries

```python
# Good: specific query
await search_nodes(
    query="software companies founded after 2020 in San Francisco",
    entity_types=["Organization"]
)

# Good: targeted fact search
await search_memory_facts(
    query="who are the founders and when did they start the company",
    max_facts=5
)
```

**DON'T**: Use overly generic queries

```python
# Bad: too generic
await search_nodes(query="companies")

# Bad: unclear intent
await search_memory_facts(query="stuff")
```

### 7. Error Handling

**DO**: Always check for error responses

```python
result = await add_memory(name="Test", episode_body="Content")

if 'error' in result:
    logger.error(f"Failed to add memory: {result['error']}")
    # Handle error appropriately
else:
    logger.info(f"Success: {result['message']}")
```

**DON'T**: Assume operations always succeed

```python
# Bad: no error checking
result = await add_memory(name="Test", episode_body="Content")
print(result['message'])  # May crash if error occurred
```

### 8. Resource Cleanup

**DO**: Clear test data after development/testing

```python
# Clear test namespace after testing
await clear_graph(group_ids=["test", "development"])
```

**DON'T**: Let test data accumulate in production namespaces

### 9. Entity Type Configuration

**DO**: Define custom entity types relevant to your domain

```yaml
graphiti:
  entity_types:
    - name: "Customer"
      description: "Business customers and clients"
    - name: "Product"
      description: "Products and services offered"
    - name: "Transaction"
      description: "Purchase and sales transactions"
```

**DON'T**: Use generic entity types for specialized domains

### 10. Database Connection Management

**DO**: Verify database connectivity before operations

```python
status = await get_status()

if status['status'] == 'ok':
    print("Database connected, ready to proceed")
    # Perform operations
else:
    print(f"Database error: {status['message']}")
    # Handle connection issue
```

**DON'T**: Assume database is always available

### 11. Transport Selection

**DO**: Use HTTP transport for production deployments

```yaml
server:
  transport: "http"  # Recommended for production
  host: "0.0.0.0"
  port: 8000
```

**DON'T**: Use stdio transport in production (it's for local development/testing)

```yaml
server:
  transport: "stdio"  # Only for local testing
```

### 12. Logging and Monitoring

**DO**: Monitor logs for processing status and errors

```python
# The server logs include:
# - Episode queuing and processing
# - LLM provider rate limit warnings
# - Database connection status
# - Configuration details at startup

# Watch for:
# - "429 rate limit errors" -> reduce SEMAPHORE_LIMIT
# - "Failed to process episode" -> check content format
# - "Database connection failed" -> verify database is running
```

### 13. Custom Entity Types

**DO**: Use entity type priorities appropriately

```python
# High priority types should be checked first
entity_types = [
    {"name": "Preference", "description": "PRIORITIZE over most other types"},
    {"name": "Organization", "description": "Companies and groups"},
    {"name": "Topic", "description": "Use as last resort"}
]
```

**Reference**: The built-in entity types have priority guidance in their descriptions. See `src/models/entity_types.py:1-226`

### 14. Azure AD Authentication

**DO**: Use managed identity for Azure deployments

```yaml
llm:
  providers:
    azure_openai:
      api_url: ${AZURE_OPENAI_ENDPOINT}
      api_version: "2024-10-21"
      deployment_name: ${AZURE_OPENAI_DEPLOYMENT}
      use_azure_ad: true  # No API key needed
```

**Requirement**: Install azure-identity package

```bash
pip install azure-identity
# or
pip install mcp-server[azure]
```

---

## Appendix

### Type Definitions

#### EpisodeType
```python
from graphiti_core.nodes import EpisodeType

# Available types:
EpisodeType.text      # Plain text content
EpisodeType.json      # Structured JSON data
EpisodeType.message   # Conversation messages
```

#### SearchFilters
```python
from graphiti_core.search.search_filters import SearchFilters

# Filter nodes by labels
filters = SearchFilters(node_labels=["Organization", "Person"])
```

### Error Codes and Messages

#### Database Connection Errors

**FalkorDB not running**:
```
Database Connection Error: FalkorDB is not running
FalkorDB at localhost:6379 is not accessible.

To start FalkorDB:
  - Using Docker Compose: cd mcp_server && docker compose up
  - Or run FalkorDB manually: docker run -p 6379:6379 falkordb/falkordb
```

**Neo4j not running**:
```
Database Connection Error: Neo4j is not running
Neo4j at bolt://localhost:7687 is not accessible.

To start Neo4j:
  - Using Docker Compose: cd mcp_server && docker compose -f docker/docker-compose-neo4j.yml up
  - Or install Neo4j Desktop from: https://neo4j.com/download/
```

#### Configuration Errors

**Missing API key**:
```
ValueError: OpenAI API key is not configured. Please set the appropriate environment variable.
```

**Unsupported provider**:
```
ValueError: Unsupported LLM provider: invalid_provider
```

**Provider not available**:
```
ValueError: Azure OpenAI LLM client not available in current graphiti-core version
```

#### Validation Errors

**Invalid max_facts**:
```
ErrorResponse: max_facts must be a positive integer
```

**No group IDs for clearing**:
```
ErrorResponse: No group IDs specified for clearing
```

#### Service Errors

**Service not initialized**:
```
ErrorResponse: Graphiti service not initialized
```

**Queue service not initialized**:
```
RuntimeError: Queue service not initialized. Call initialize() first.
```

### Related Documentation

- **Architecture Overview**: See architecture documentation for system design
- **Graphiti Core**: https://github.com/getzep/graphiti (underlying graph library)
- **FastMCP**: https://github.com/jlowin/fastmcp (MCP server framework)
- **Model Context Protocol**: https://modelcontextprotocol.io/ (MCP specification)

### Version Information

This API reference is for Graphiti MCP Server based on:
- Graphiti Core: Check server logs or `/app/.graphiti-core-version` in Docker
- FastMCP: Latest compatible version
- Python: 3.10+

---

**Last Updated**: 2024-11-27

**Source Files**:
- Main Server: `src/graphiti_mcp_server.py`
- Configuration: `src/config/schema.py`
- Response Types: `src/models/response_types.py`
- Entity Types: `src/models/entity_types.py`
- Factories: `src/services/factories.py`
- Queue Service: `src/services/queue_service.py`
- Formatting Utils: `src/utils/formatting.py`
- Auth Utils: `src/utils/utils.py`
- Config Example: `config/config.yaml`
