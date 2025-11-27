# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Graphiti MCP (Model Context Protocol) Server implementation that exposes knowledge graph functionality through the MCP protocol. The project demonstrates integration of **Graphiti** (knowledge graph framework) with **FalkorDB** (in-memory graph database) and **Neo4j**.

## Architecture

### Three-Layer Architecture

1. **MCP Server Layer** (`src/graphiti_mcp_server.py`)
   - FastMCP-based server exposing Graphiti tools via MCP protocol
   - Supports HTTP (default) and stdio transports
   - Queue-based episode processing with configurable concurrency

2. **Intelligence Layer** (Graphiti Framework)
   - Automatic entity/relationship extraction from episodes
   - Hybrid search (vector similarity + BM25 keyword retrieval)
   - Temporal knowledge tracking with reference times
   - Center node reranking for graph-aware search

3. **Infrastructure Layer** (Database Drivers)
   - FalkorDB: Redis-based in-memory graph database (default)
   - Neo4j: Production-grade graph database option

### Core Components

**Episode System**: Primary data ingestion mechanism. Episodes are units of knowledge (text or JSON) that Graphiti processes to extract entities and relationships. Parameters:
- `episode_body`: Content (text string or JSON string)
- `source`: `EpisodeType.text` or `EpisodeType.json`
- `source_description`: Context metadata
- `reference_time`: Temporal tracking
- `group_id`: Logical namespace for graph data

**Queue Service** (`src/services/queue_service.py`): Manages sequential episode processing per group_id. Episodes within the same group are processed sequentially to maintain consistency; different groups can process in parallel.

**Factory Pattern** (`src/services/factories.py`): Creates LLM clients, embedders, and database drivers based on configuration. Supports multiple providers:
- LLM: OpenAI, Anthropic, Gemini, Groq, Azure OpenAI
- Embedder: OpenAI, Voyage, Sentence Transformers, Gemini
- Database: FalkorDB, Neo4j

**Configuration** (`src/config/schema.py`): Pydantic-based settings with YAML file support and environment variable expansion using `${VAR:default}` syntax.

## Development Environment

### Prerequisites

- Python 3.10+ (see pyproject.toml:6)
- Docker and Docker Compose
- API key for at least one LLM provider (OpenAI recommended)

### Dependency Management

This project uses `uv` for package management:

```bash
# Install dependencies
uv sync

# Install with additional LLM providers
uv sync --extra providers

# Install with dev dependencies
uv sync --extra dev

# Add a package
uv add package-name
```

### Database Setup

**FalkorDB (Default - Combined Container):**
```bash
docker compose up
```
This starts both FalkorDB and MCP server in a single container.
- FalkorDB Web UI: http://localhost:3000
- MCP endpoint: http://localhost:8000/mcp/

**FalkorDB (Separate Containers):**
```bash
docker compose -f docker/docker-compose-falkordb.yml up
```

**Neo4j:**
```bash
docker compose -f docker/docker-compose-neo4j.yml up
```
- Neo4j Browser: http://localhost:7474
- Default credentials: neo4j/demodemo

**Standalone FalkorDB (for notebook/script development):**
```bash
docker run -p 6379:6379 -p 3000:3000 -it --rm falkordb/falkordb:latest
```

### Running the Server

**With Docker (recommended):**
```bash
docker compose up
```

**Direct execution:**
```bash
# Using main.py (wrapper)
python main.py

# Using the actual server module
uv run src/graphiti_mcp_server.py

# With specific configuration
uv run src/graphiti_mcp_server.py --config config/config-docker-neo4j.yaml

# With command-line overrides
uv run src/graphiti_mcp_server.py --database-provider neo4j --llm-provider anthropic
```

**Running the Jupyter notebook:**
```bash
jupyter notebook graphiti-falkordb-gs.ipynb
```
Or use VS Code with the Jupyter extension.

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required - at least one LLM provider
OPENAI_API_KEY=sk-...

# Optional - other providers
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
GROQ_API_KEY=...

# Database configuration
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=demodemo
FALKORDB_URI=redis://localhost:6379

# Performance tuning
SEMAPHORE_LIMIT=10  # Concurrent episode processing limit
```

**Important**: Never commit `.env` files with real API keys. Only commit `.env.example` with placeholders.

## Testing

### Test Structure

Tests are organized in `tests/` with pytest markers:
- `unit` - Fast unit tests
- `integration` - Tests requiring database
- `slow` - Long-running tests (stress/load)
- `requires_neo4j` / `requires_falkordb` / `requires_openai` - Dependency markers

### Running Tests

**Using the test runner (recommended):**
```bash
# Quick smoke tests
python tests/run_tests.py smoke

# Integration tests with mock LLM (no API key needed)
python tests/run_tests.py integration --mock-llm

# All tests
python tests/run_tests.py all

# With specific database
python tests/run_tests.py integration --database neo4j

# Parallel execution
python tests/run_tests.py all --parallel 4

# With coverage
python tests/run_tests.py all --coverage
```

**Direct pytest:**
```bash
pytest tests/
pytest tests/test_integration.py
pytest -m integration
pytest -m "not slow"
```

See `tests/README.md` for detailed test documentation.

## Key Development Patterns

### Graphiti Initialization

Always call `build_indices_and_constraints()` after creating a Graphiti instance:

```python
from graphiti_core import Graphiti
from graphiti_core.driver.falkordb_driver import FalkorDriver

falkor_driver = FalkorDriver(host='localhost', port=6379)
graphiti = Graphiti(graph_driver=falkor_driver)
await graphiti.build_indices_and_constraints()
```

This sets up entity types, constraints, and search indices.

### Working with Episodes

All episode operations are async. Convert dicts to JSON strings for JSON episodes:

```python
from graphiti_core.nodes import EpisodeType
import json

# Text episode
await graphiti.add_episode(
    name="User Interaction",
    episode_body="John prefers dark mode in the UI",
    source=EpisodeType.text,
    source_description="user preference",
    reference_time=datetime.now(timezone.utc),
    group_id="user-prefs"
)

# JSON episode
data = {"user": "John", "preference": "dark_mode"}
await graphiti.add_episode(
    name="Settings Export",
    episode_body=json.dumps(data),
    source=EpisodeType.json,
    source_description="settings export",
    reference_time=datetime.now(timezone.utc),
    group_id="user-prefs"
)
```

### Search Strategies

**Basic search** (hybrid vector + keyword):
```python
results = await graphiti.search("What are John's preferences?")
```

**Center node search** (graph-aware reranking):
```python
results = await graphiti.search(
    "What are John's preferences?",
    center_node_uuid=known_node_uuid
)
```

Use center node search for:
- Organizational hierarchies
- Process chains
- Cause-effect relationships

### Concurrency Control

Episode processing concurrency is controlled by `SEMAPHORE_LIMIT`. Tune based on your LLM provider's rate limits:

- OpenAI Tier 1 (free): `SEMAPHORE_LIMIT=1-2`
- OpenAI Tier 2 (60 RPM): `SEMAPHORE_LIMIT=5-8`
- OpenAI Tier 3 (500 RPM): `SEMAPHORE_LIMIT=10-15`
- Anthropic default (50 RPM): `SEMAPHORE_LIMIT=5-8`

Symptoms:
- Too high: 429 rate limit errors
- Too low: Slow throughput

## Configuration Files

- `config/config.yaml` - Default configuration
- `config/config-docker-falkordb-combined.yaml` - FalkorDB combined container
- `config/config-docker-falkordb.yaml` - FalkorDB separate containers
- `config/config-docker-neo4j.yaml` - Neo4j configuration

Configuration uses YAML with environment variable expansion: `${VAR_NAME:default_value}`

## MCP Tools Exposed

The server exposes these tools via MCP:
- `add_episode` - Add text/JSON/message episodes
- `search_nodes` - Search for entity node summaries
- `search_facts` - Search for relationships/edges
- `get_episodes` - Retrieve recent episodes
- `delete_episode` - Remove an episode
- `get_entity_edge` - Get edge by UUID
- `delete_entity_edge` - Delete an edge
- `clear_graph` - Clear all data and rebuild indices
- `get_status` - Check server and database status

## Common Tasks

**Start development environment:**
```bash
docker compose up  # Start FalkorDB + MCP server
# In another terminal:
python graphiti-falkordb-gs.ipynb  # Or open in VS Code
```

**Switch database backends:**
```bash
docker compose down
docker compose -f docker/docker-compose-neo4j.yml up
```

**Clear graph data:**
```bash
docker compose down
docker volume rm mcp_server_falkordb_data  # or docker_neo4j_data
docker compose up
```

**View logs:**
```bash
docker compose logs -f graphiti-mcp
docker compose logs -f neo4j
```

**Access database UI:**
- FalkorDB: http://localhost:3000
- Neo4j: http://localhost:7474
