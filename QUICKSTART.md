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
get_status()
# Expected: {"status": "ok", "group_ids": [...]}

# 2. Recover recent session context (if continuing after compression)
search_memory_facts(
    query="session priorities pending tasks",
    group_ids=["graphiti_meta_knowledge"],
    max_facts=10
)
# Look for: "Next session priorities", "PRIORITY_INCLUDES" facts

# 3. Query meta-knowledge about using Graphiti (if first time)
search_memory_facts(
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
uv run fastmcp inspect src/graphiti_mcp_server.py:mcp
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
uv run fastmcp dev src/graphiti_mcp_server.py:mcp
```

This starts your server and opens an interactive web UI at `http://localhost:6274` where you can:
- Test `get_status` tool to verify initialization
- Call tools and see actual responses
- Catch runtime errors before deployment

**In the web UI, run:**
1. Click "get_status" tool
2. Expected: `{"status": "ok", "message": "...connected to FalkorDB..."}`
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

```python
# JSON episode (for structured data)
mcp__graphiti-fastmcp__add_memory(
    name="Architecture: MySystem - Characteristics",
    episode_body='{"system": "MySystem", "strengths": ["fast", "reliable"], "ideal_for": ["production"]}',
    source="json",
    source_description="Initial system documentation",
    group_id="my_project_knowledge"
)

# Text episode (for narratives)
mcp__graphiti-fastmcp__add_memory(
    name="Lesson: MySystem - Performance Discovery",
    episode_body="We discovered that MySystem performs best when...",
    source="text",
    source_description="Session learning from testing",
    group_id="my_project_knowledge"
)
```

---

## Verification Pattern (Essential!)

After adding episodes, verify extraction worked:

```python
# Step 1: Confirm episode stored (immediate)
get_episodes(group_ids=["my_project_knowledge"], max_episodes=5)

# Step 2: Verify entities extracted (wait 5-10 sec)
search_nodes(query="MySystem", group_ids=["my_project_knowledge"], max_nodes=5)

# Step 3: Verify relationships created (wait 10-15 sec)
search_memory_facts(query="MySystem strengths", group_ids=["my_project_knowledge"], max_facts=5)
```

---

## If the Graph is Empty (Disaster Recovery)

If `graphiti_meta_knowledge` is empty, bootstrap it:

```bash
# From project root
uv run python examples/populate_meta_knowledge.py
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
