# MCP Python SDK Examples

Learn to build MCP clients with Python using the Graphiti knowledge graph server.

## Setup

```bash
# Install uv (if needed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dependencies
uv sync

# Start the Graphiti MCP server
docker compose up
```

## Examples

Run examples in order - each builds on the previous:

| # | File | What You Learn |
|---|------|----------------|
| 1 | `01_connect_and_discover.py` | Connect to server, list available tools |
| 2 | `02_call_tools.py` | Call tools with/without arguments |
| 3 | `03_graphiti_memory.py` | All 9 Graphiti knowledge graph operations |
| 4 | `04_mcp_concepts.py` | MCP primitives: Tools vs Resources vs Prompts |

### Run an example

```bash
uv run python examples/01_connect_and_discover.py
```

---

## MCP Core Concepts

MCP (Model Context Protocol) defines **three primitives** for AI applications:

### 1. Tools (Actions)

**What**: Functions that perform actions, potentially with side effects.

**When to use**: API calls, computations, data modifications, triggering workflows.

**Discovery**: `session.list_tools()`
**Invocation**: `session.call_tool("name", {"arg": "value"})`

```python
# Server-side (FastMCP)
@mcp.tool()
def calculate(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

# Client-side
result = await session.call_tool("calculate", {"a": 5, "b": 3})
```

### 2. Resources (Data)

**What**: Read-only data sources (files, configs, database content).

**When to use**: Exposing static or dynamic data for LLMs to read.

**Discovery**: `session.list_resources()`
**Invocation**: `session.read_resource("uri://path")`

```python
# Server-side (FastMCP)
@mcp.resource("config://{name}")
def get_config(name: str) -> str:
    """Get configuration by name"""
    return configs[name]

# Client-side
content = await session.read_resource("config://settings")
```

### 3. Prompts (Templates)

**What**: Pre-defined message templates for LLM interactions.

**When to use**: Standardizing how LLMs are prompted for specific tasks.

**Discovery**: `session.list_prompts()`
**Invocation**: `session.get_prompt("name", {"arg": "value"})`

```python
# Server-side (FastMCP)
@mcp.prompt()
def review_code(code: str) -> str:
    """Generate a code review prompt"""
    return f"Please review this code:\n{code}"

# Client-side
prompt = await session.get_prompt("review_code", {"code": "def foo(): pass"})
```

### Quick Comparison

| Aspect | Tools | Resources | Prompts |
|--------|-------|-----------|---------|
| Purpose | Actions | Data access | LLM instructions |
| Side effects | Yes | No (read-only) | No |
| Discovery | `list_tools()` | `list_resources()` | `list_prompts()` |
| Invocation | `call_tool()` | `read_resource()` | `get_prompt()` |

> **Note**: Graphiti exposes only **Tools** because it's an action-based API
> (add data, search, delete). It doesn't expose Resources or Prompts.

---

## The Client Pattern

Every MCP client follows this structure:

```python
import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def main():
    # 1. Connect to server
    async with streamablehttp_client("http://localhost:8000/mcp/") as (read, write, _):
        # 2. Create session
        async with ClientSession(read, write) as session:
            # 3. Initialize (required - performs MCP handshake)
            await session.initialize()

            # 4. Discover capabilities
            tools = await session.list_tools()
            resources = await session.list_resources()
            prompts = await session.list_prompts()

            # 5. Use the capabilities
            result = await session.call_tool("tool_name", {"arg": "value"})

asyncio.run(main())
```

---

## Graphiti Tools (9 total)

Graphiti is a **temporally-aware knowledge graph** for AI agents. It stores information as:
- **Episodes**: Raw data (text, JSON, messages)
- **Nodes**: Entities extracted from episodes
- **Edges/Facts**: Relationships between entities

### Tool Reference

| Tool | Purpose | Arguments |
|------|---------|-----------|
| `get_status` | Check server health | (none) |
| `add_memory` | Store episode in graph | `name`*, `episode_body`*, `source`, `source_description`, `group_id` |
| `search_nodes` | Find entities | `query`*, `max_nodes`, `group_ids`, `entity_types` |
| `search_memory_facts` | Find relationships | `query`*, `max_facts`, `group_ids`, `center_node_uuid` |
| `get_episodes` | List stored episodes | `max_episodes`, `group_ids` |
| `get_entity_edge` | Get edge by UUID | `uuid`* |
| `delete_episode` | Remove an episode | `uuid`* |
| `delete_entity_edge` | Remove an edge | `uuid`* |
| `clear_graph` | Clear all data | `group_ids` |

*Required arguments marked with asterisk

### add_memory Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `name` | string | Name/title for the episode |
| `episode_body` | string | Content to store (text or JSON string) |
| `source` | string | `"text"`, `"json"`, or `"message"` |
| `source_description` | string | Description of data source |
| `group_id` | string | Namespace for organizing data (default: "main") |

> **Important: Async Processing**
>
> `add_memory` returns immediately with "queued for processing" - the actual entity extraction happens asynchronously and takes ~15-20 seconds per episode. If you query immediately after adding, you may get empty results. Wait for processing to complete or run queries in a separate script.

### Search Arguments

| Argument | Type | Description |
|----------|------|-------------|
| `query` | string | Natural language search query |
| `max_nodes` / `max_facts` | int | Maximum results to return |
| `group_ids` | list | Filter by namespace(s) |
| `center_node_uuid` | string | Rerank results by graph proximity |

---

## Handling Responses

Tool results contain a list of content items:

```python
from mcp import types
import json

result = await session.call_tool("search_nodes", {"query": "AI", "max_nodes": 5})

for content in result.content:
    if isinstance(content, types.TextContent):
        # Most Graphiti responses are JSON strings
        data = json.loads(content.text)
        print(data)

# Structured content (newer MCP spec)
if result.structuredContent:
    print(result.structuredContent)
```

---

## Further Reading

- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [MCP Specification](https://modelcontextprotocol.io)
- [Graphiti](https://github.com/getzep/graphiti)
- [Graphiti MCP Server](https://github.com/getzep/graphiti/tree/main/mcp_server)
