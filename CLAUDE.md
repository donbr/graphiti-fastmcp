# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Graphiti MCP (Model Context Protocol) Server implementation that exposes knowledge graph functionality through the MCP protocol. The project demonstrates integration of **Graphiti** (knowledge graph framework) with **FalkorDB** (in-memory graph database) and **Neo4j**.

> **Quick start**: See `QUICKSTART.md` for a 5-minute introduction.

## Architecture

### Four-Layer Architecture

1. **Presentation Layer** (`src/graphiti_mcp_server.py`)
   - FastMCP-based server exposing Graphiti tools via MCP protocol
   - Supports HTTP (default) and stdio transports
   - Tool decorators with type-safe validation

2. **Services Layer** (`src/services/`)
   - GraphitiService: Client lifecycle management
   - QueueService: Async episode processing with per-group_id queues
   - Factories: Runtime provider selection (LLM, Embedder, Database)

3. **Core Integration Layer** (Graphiti Framework)
   - Automatic entity/relationship extraction from episodes
   - Hybrid search (vector similarity + BM25 keyword retrieval)
   - Temporal knowledge tracking with reference times
   - Center node reranking for graph-aware search

4. **Data Persistence Layer** (Database Drivers)
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
- LLM: OpenAI, Anthropic, Gemini, Groq, Azure OpenAI (with Azure AD support)
- Embedder: OpenAI, Azure OpenAI, Voyage, Sentence Transformers, Gemini
- Database: FalkorDB (local and cloud), Neo4j

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
docker compose -f docker/docker-compose.yml up
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

**FalkorDB Cloud (managed service):**
For production deployments, FalkorDB Cloud provides managed instances. Configure via environment variables:
```bash
# In .env file
FALKORDB_URI=redis://your-cloud-instance-endpoint:port
FALKORDB_DATABASE=default_db
FALKORDB_USER=your_cloud_username_here
FALKORDB_PASSWORD=your_cloud_password_here
```

Note: FalkorDB Cloud requires authentication (username/password), while local instances typically don't.

**FalkorDB Cloud Health Check:**
Monitor your FalkorDB Cloud instance size and health (free tier limit: 100 MB):
```bash
uv run scripts/check_falkordb_health.py
```

This script reports:
- Redis memory usage (used, peak, RSS, max)
- Per-graph storage size, node counts, and edge counts
- Free tier usage percentage with status (OK/WARNING/CRITICAL)

Exit codes: 0=OK, 1=WARNING (>70%), 2=CRITICAL (>90%)

### Running the Server

**With Docker (recommended):**
```bash
docker compose -f docker/docker-compose.yml up
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

### Environment Variables

Create a `.env` file in the project root:

```bash
# Required - at least one LLM provider
OPENAI_API_KEY=sk-...

# Optional - other LLM providers
ANTHROPIC_API_KEY=...
GOOGLE_API_KEY=...
GROQ_API_KEY=...

# Optional - Azure OpenAI (alternative to OpenAI)
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
AZURE_OPENAI_API_VERSION=2024-10-21
USE_AZURE_AD=false  # Set to true for Azure Managed Identity auth

# Database configuration - Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=demodemo

# Database configuration - FalkorDB Local
FALKORDB_URI=redis://localhost:6379
FALKORDB_DATABASE=default_db
FALKORDB_USER=
FALKORDB_PASSWORD=

# Database configuration - FalkorDB Cloud
# FALKORDB_URI=redis://your-cloud-instance-endpoint:port
# FALKORDB_DATABASE=default_db
# FALKORDB_USER=your_cloud_username_here
# FALKORDB_PASSWORD=your_cloud_password_here

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

### OpenAI Reasoning Models (gpt-5, o1, o3)

The server automatically detects and configures reasoning models correctly:
- **Detection**: Models starting with `gpt-5`, `o1`, or `o3` are treated as reasoning models
- **Configuration**: Reasoning models use `reasoning='minimal'` and `verbosity='low'` parameters
- **Small model selection**: When using a reasoning model, the small model defaults to `gpt-5-nano` instead of `gpt-4.1-mini`

No manual configuration needed - just set the model name in config or via `--model` flag.

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

## Code Style

This project follows these code style conventions (enforced by ruff):

- Line length: 100 characters
- Quote style: Single quotes for strings
- Import ordering: Enforced by isort (imports sorted alphabetically)
- Formatting: 4-space indentation
- Type checking: Basic level with pyright (Python 3.10+)

Run linting and formatting:
```bash
# Format code
uv run ruff format .

# Check for issues
uv run ruff check .

# Type checking
uv run pyright
```

## Configuration Files

- `config/config.yaml` - Default configuration
- `config/config-docker-falkordb-combined.yaml` - FalkorDB combined container
- `config/config-docker-falkordb.yaml` - FalkorDB separate containers
- `config/config-docker-neo4j.yaml` - Neo4j configuration

Configuration uses YAML with environment variable expansion: `${VAR_NAME:default_value}`

## MCP Tools Exposed

The server exposes these tools via MCP:
- `add_memory` - Add text/JSON/message episodes (queued for async processing)
- `search_nodes` - Search for entity node summaries
- `search_memory_facts` - Search for relationships/edges between entities
- `get_episodes` - Retrieve recent episodes
- `delete_episode` - Remove an episode
- `get_entity_edge` - Get edge by UUID
- `delete_entity_edge` - Delete an edge
- `clear_graph` - Clear all data and rebuild indices
- `get_status` - Check server and database status

## Common Tasks

**Start development environment:**
```bash
docker compose -f docker/docker-compose.yml up  # Start FalkorDB + MCP server
```

**Switch database backends:**
```bash
docker compose down
docker compose -f docker/docker-compose-neo4j.yml up
```

**Clear graph data:**
```bash
docker compose down
docker volume rm docker_falkordb_data  # or docker_neo4j_data
docker compose -f docker/docker-compose.yml up
```

**View logs:**
```bash
docker compose logs -f graphiti-mcp
docker compose logs -f neo4j
```

**Access database UI:**
- FalkorDB: http://localhost:3000
- Neo4j: http://localhost:7474

## Troubleshooting

### Common Issues

**"API key is not configured" error:**
- Ensure the appropriate environment variable is set (OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.)
- For Azure OpenAI, verify AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_DEPLOYMENT are set
- Check that the .env file is in the project root and loaded correctly

**429 Rate Limit Errors:**
- Lower SEMAPHORE_LIMIT in .env based on your LLM provider tier (see Concurrency Control section)
- OpenAI Tier 1 users should use SEMAPHORE_LIMIT=1-2
- Monitor your API usage dashboard

**FalkorDB connection failures:**
```bash
# Check if FalkorDB is running
docker ps | grep falkordb

# Test connection
redis-cli -h localhost -p 6379 ping

# For FalkorDB Cloud, verify credentials and endpoint
```

**Neo4j connection failures:**
```bash
# Check if Neo4j is running
docker ps | grep neo4j

# Test browser access
curl http://localhost:7474

# Verify credentials match NEO4J_PASSWORD in .env
```

**Import errors for optional providers:**
- Install providers extra: `uv sync --extra providers`
- This includes: Anthropic, Gemini, Groq, Voyage, Sentence Transformers

**Azure AD authentication issues:**
- Ensure Azure CLI is installed and authenticated: `az login`
- Verify managed identity has appropriate permissions
- Set USE_AZURE_AD=true in .env

## Reference Documentation

### Additional Documentation

- **`architecture/`** - Detailed architecture documentation including component inventory, data flows, and API reference
- **`examples/`** - MCP SDK learning tutorials (`01_connect_and_discover.py`, `02_call_tools.py`, `03_graphiti_memory.py`, `04_mcp_concepts.py`)
- **`scripts/`** - Operational utilities for backup/restore (`export_graph.py`, `import_graph.py`, `populate_meta_knowledge.py`, `verify_meta_knowledge.py`, `check_falkordb_health.py`)

### When Working with Graphiti Knowledge Graphs

**`reference/GRAPHITI_BEST_PRACTICES.md`** - Consult this file when:
- Designing episode structures (JSON vs text, naming conventions)
- Planning knowledge graph organization (group_id strategy)
- Implementing MCP tool workflows (add_memory, search_nodes, search_memory_facts)
- Verifying asynchronous episode processing
- Building meta-knowledge systems that accumulate learnings across sessions

Key topics: Episode categories (Lesson/Procedure/Best Practice/Anti-Pattern), JSON structure guidelines, verification patterns, relationship types.

**`reference/CLAUDE_META_KNOWLEDGE_REVIEW.md`** - Reference when:
- Evaluating knowledge graph quality and effectiveness
- Understanding what makes good vs poor episode design
- Learning from documented mistakes and corrections (meta-lessons on research-before-critique)
- Deciding between knowledge graph storage vs other documentation methods
- Planning knowledge consolidation strategies and lifecycle management

Key topics: Structural critiques, query effectiveness analysis, domain separation, premature consolidation pitfalls, honest assessment of graph value vs alternatives.