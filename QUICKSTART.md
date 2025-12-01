# Graphiti MCP Quick Start

A 5-minute guide to get a new Claude instance connected and productive with Graphiti knowledge graphs.

> **🔒 SECURITY WARNING**: Never commit sensitive information to version control or knowledge graphs:
> - API keys, passwords, tokens, credentials
> - Credit card numbers, financial data
> - Personal Identifiable Information (PII): names, addresses, SSNs, emails
> - Protected Health Information (PHI): medical records, diagnoses, prescriptions
> - Proprietary business data
>
> **All episodes added to knowledge graphs are stored in plaintext**. Use `.gitignore` for sensitive backups.
> See [CLAUDE.md:194](CLAUDE.md#L194) for environment variable best practices.

---

## First 3 Commands

Run these immediately to verify connection and recover context:

```python
# 1. Check connection
mcp__graphiti-fastmcp__get_status()
# Expected: {"status": "ok", "group_ids": [...]}

# 2. Recover recent session context (if continuing after compression)
mcp__graphiti-fastmcp__search_memory_facts(
    query="session priorities pending tasks",
    group_ids=["graphiti_meta_knowledge"],
    max_facts=10
)
# Look for: "Next session priorities", "PRIORITY_INCLUDES" facts

# 3. Query meta-knowledge about using Graphiti (if first time)
mcp__graphiti-fastmcp__search_memory_facts(
    query="best practices episode design",
    group_ids=["graphiti_meta_knowledge"],
    max_facts=5
)
```

**Note**: Command #2 recovers context from previous sessions. Command #3 teaches Graphiti basics.

---

## Validating Your Local Server

Before deploying to FastMCP Cloud, validate your server with TWO commands:

### 1. Static Validation (Quick Check)

```bash
# Verify server structure and tool registration
uv run fastmcp inspect src/server.py:create_server
```

**Expected output:**
```
Name: Graphiti Agent Memory
Tools: 9 found
  - add_memory
  - search_nodes
  - search_memory_facts
  ... (etc)
```

This checks that the module can be imported and tools are registered.

### 2. Runtime Validation (Essential!)

```bash
# Run interactive inspector - tests actual initialization
uv run fastmcp dev src/server.py:create_server
```

This starts your server and opens an interactive web UI at `http://localhost:6274` where you can:
- Test `get_status` tool to verify initialization
- Call tools and see actual responses
- Catch runtime errors before deployment

**In the web UI, run:**
1. Click "get_status" tool
2. Expected: `{"status": "ok", "message": "Graphiti MCP server is running and connected to falkordb database"}`
3. If you see `"Graphiti service not initialized"`, fix initialization issues before deploying

**If validation fails:**
- Check dependencies: `uv sync`
- Verify database is running (see [CLAUDE.md:86](CLAUDE.md#L86))
- Check environment variables in `.env`
- Fix any import or connection errors

---

## Key Concepts (30 seconds)

Graphiti is a **temporal knowledge graph**. It has three core components:

| Component | What It Is | Example |
|-----------|------------|---------|
| **Episodes** | Input data you add | JSON about an architecture, text lesson |
| **Nodes** | Entities extracted from episodes | "Graphiti/Zep" (Organization), "temporal reasoning" (Topic) |
| **Facts** | Relationships with timestamps | "Graphiti IDEAL_FOR customer service bots" |

**Key insight**: You add episodes. Graphiti extracts entities and relationships automatically using an LLM.

---

## Before Adding Data

Read **one** document first: [`reference/GRAPHITI_BEST_PRACTICES.md`](reference/GRAPHITI_BEST_PRACTICES.md)

Critical concepts:
- **Episode naming**: `{Category}: {Subject} - {Specific Aspect}`
- **JSON structure**: Keep flat (3-4 levels max), include `id`, `name`, `description`
- **Async processing**: Episodes are "queued" - wait 15-20 seconds before verification

---

## Adding Your First Episode

### JSON Episodes (Structured Comparisons)

**Use JSON for**: Architecture characteristics, decision criteria, structured comparisons

```python
# Architecture characteristics with consistent schema
mcp__graphiti-fastmcp__add_memory(
    name="Architecture: MySystem - Characteristics",
    episode_body='{"system": "MySystem", "strengths": ["low latency", "horizontal scaling", "real-time processing"], "weaknesses": ["complex setup", "requires monitoring"], "ideal_for": ["high-throughput APIs", "real-time analytics"], "cost_profile": {"latency": "low", "operational_overhead": "medium"}}',
    source="json",
    source_description="System architecture comparison",
    group_id="architecture_decision_tree_2025"
)

# Decision criteria with multiple options
mcp__graphiti-fastmcp__add_memory(
    name="Decision: Database Selection - Criteria",
    episode_body='{"decision": "database_selection", "options": [{"name": "PostgreSQL", "strengths": ["ACID compliance", "mature ecosystem"]}, {"name": "FalkorDB", "strengths": ["graph queries", "Redis-based"]}], "requirements": ["sub-100ms queries", "graph traversal"], "constraints": ["max 2GB dataset", "cloud deployment"]}',
    source="json",
    source_description="Database selection decision tree",
    group_id="architecture_decision_tree_2025"
)
```

**Why JSON works well**:
- Consistent schema enables cross-entity comparison
- Nested objects preserve semantic relationships
- Arrays extract as individual facts
- Produces high-quality entity extraction (labels: Organization, Topic, Requirement)

### Text Episodes (Narrative Explanations)

**Use text for**: Pattern evolution, causal explanations, historical context

```python
# Pattern evolution with temporal relationships
mcp__graphiti-fastmcp__add_memory(
    name="Lesson: FastMCP Deployment - Evolution from Global State to Factory Pattern",
    episode_body="The deployment pattern evolved from using global state (2024) to factory pattern (2025). The key innovation was recognizing that FastMCP Cloud ignores if __name__ == '__main__' blocks. This represents a shift from imperative initialization to declarative factory functions. The factory pattern produces cleaner testability and eliminates global state complexity.",
    source="text",
    source_description="Deployment pattern evolution lesson",
    group_id="agent_memory_decision_tree_2025"
)

# Causal explanation with solution
mcp__graphiti-fastmcp__add_memory(
    name="Lesson: Graphiti Service Initialization - Root Cause Discovery",
    episode_body="We discovered that 'Graphiti service not initialized' errors occurred because FastMCP Cloud uses fastmcp run internally, which completely disregards the if __name__ == '__main__' block. The solution was implementing a create_server() factory function that initializes services before returning the FastMCP instance. This fixed deployment failures by ensuring initialization happens on module import, not script execution.",
    source="text",
    source_description="Debugging session discovery",
    group_id="graphiti_meta_knowledge"
)
```

**Why text works well**:
- Enables temporal relationships (EVOLVED_TO, INTRODUCED_BY)
- Causal explanations become SOLUTION_FOR edges
- Narrative structure helps extraction understand progression
- Provides valid_at dates from historical context

---

## Verification Pattern (Essential!)

After adding episodes, verify extraction worked using the **Three-Tool Verification Pattern**:

```python
# Step 1: Confirm episode stored (immediate - no wait needed)
mcp__graphiti-fastmcp__get_episodes(
    group_ids=["architecture_decision_tree_2025"],
    max_episodes=5
)
# ✅ Confirms: Episode ingested successfully

# Step 2: Verify entities extracted (wait 5-10 seconds)
mcp__graphiti-fastmcp__search_nodes(
    query="MySystem latency",
    group_ids=["architecture_decision_tree_2025"],
    max_nodes=5
)
# ✅ Confirms: Entities created (e.g., "MySystem", "low latency", "horizontal scaling")

# Step 3: Verify relationships created (wait 15-20 seconds total from add_memory)
mcp__graphiti-fastmcp__search_memory_facts(
    query="MySystem strengths and ideal use cases",
    group_ids=["architecture_decision_tree_2025"],
    max_facts=5
)
# ✅ Confirms: Relationships extracted (e.g., "MySystem HAS_STRENGTH low latency", "MySystem IDEAL_FOR real-time analytics")
```

**Key insight from `graphiti_meta_knowledge`**:
> "add_memory queues processing; episodes stored immediately while entity/relationship extraction completes in 5–15 seconds. Wait 15–20 seconds after add_memory before final verification."

**What each tool validates**:
1. **get_episodes** - Episode ingestion (immediate)
2. **search_nodes** - Entity extraction (5-10s delay)
3. **search_memory_facts** - Relationship formation (15-20s total delay)

---

## If the Graph is Empty (Disaster Recovery)

If `graphiti_meta_knowledge` is empty, bootstrap it:

```bash
# From project root
uv run python scripts/populate_meta_knowledge.py
```

This creates 10 foundational episodes covering:
- Episode type selection guide
- JSON structure requirements
- Naming conventions
- Verification patterns
- Common anti-patterns

---

## Available Tools

| Tool | Purpose |
|------|---------|
| `get_status` | Check server connection |
| `add_memory` | Add episode to graph |
| `search_nodes` | Find entities |
| `search_memory_facts` | Find relationships |
| `get_episodes` | List stored episodes |
| `get_entity_edge` | Get edge/relationship by UUID |
| `delete_episode` | Remove episode |
| `delete_entity_edge` | Remove relationship |
| `clear_graph` | Clear all data for group(s) |

---

## Available Documentation Tools

Beyond Graphiti memory, you have access to comprehensive documentation search:

| Tool | Coverage | Use For |
|------|----------|---------|
| `mcp__qdrant-docs__search_docs` | 2,670 pages (Anthropic, Zep, LangChain, Prefect, FastMCP, PydanticAI, McpProtocol) | Semantic search of official docs |
| `mcp__ai-docs-server__fetch_docs` | 13 frameworks (llms.txt format) | Fetch specific documentation pages |
| `mcp__ai-docs-server-full__fetch_docs` | 11 frameworks (llms-full.txt format) | Full documentation versions |
| `mcp__Context7__get-library-docs` | Library documentation | Up-to-date library references |

**Quick example:**
```python
# Search Anthropic documentation for prompt caching
mcp__qdrant-docs__search_docs(
    query="prompt caching implementation",
    source="Anthropic",
    k=3
)
```

See [`reference/QUICK_START_QDRANT_MCP_CLIENT.md`](reference/QUICK_START_QDRANT_MCP_CLIENT.md) for detailed usage guide.

---

## Group Strategy

| Group | Purpose |
|-------|---------|
| `graphiti_meta_knowledge` | How to use Graphiti (always query first) |
| `{domain}_decision_tree_{year}` | Domain-specific knowledge graphs |
| `{project}_learnings` | Session-specific discoveries |

---

## Next Steps

1. **5 min**: Read [`reference/GRAPHITI_BEST_PRACTICES.md`](reference/GRAPHITI_BEST_PRACTICES.md)
2. **15 min**: Read [`reference/GRAPHITI_MCP_LESSONS_LEARNED.md`](reference/GRAPHITI_MCP_LESSONS_LEARNED.md)
3. **Optional**: Deep dive into [`reference/CLAUDE_META_KNOWLEDGE_REVIEW.md`](reference/CLAUDE_META_KNOWLEDGE_REVIEW.md)
4. **Hands-on**: Run examples in [`examples/`](examples/)

---

## Quick Reference Card

```
Episode Naming:     {Category}: {Subject} - {Aspect}
Categories:         Lesson, Best Practice, Anti-Pattern, Procedure, Architecture, Use Case
JSON Rule:          Flat structure, include id/name/description
Verification:       get_episodes → search_nodes (5-10s) → search_memory_facts (10-15s)
Meta-knowledge:     Always query graphiti_meta_knowledge first
Recovery:           uv run python examples/populate_meta_knowledge.py
```
