# Graphiti MCP Quick Start

**For New Claude Code Sessions**: Follow these three steps to connect to the knowledge graph:

```python
# Step 1: Verify connection
mcp__graphiti-local__get_status()
# ✅ Expected: {"status":"ok","message":"Graphiti MCP server is running..."}

# Step 2: List available knowledge (MUST specify group_ids)
mcp__graphiti-local__get_episodes(
    group_ids=["graphiti_meta_knowledge", "graphiti_reference_docs"],
    max_episodes=10
)

# Step 3: Search for specific topics
mcp__graphiti-local__search_nodes(
    query="episode design best practices",
    group_ids=["graphiti_meta_knowledge"],
    max_nodes=5
)
```

## ⚠️ Critical: Always Specify group_ids

**The most common mistake**: Querying without `group_ids` returns empty results.

```python
# ❌ WRONG - Returns nothing (queries default "main" namespace which is empty)
mcp__graphiti-local__get_episodes(max_episodes=10)
mcp__graphiti-local__search_nodes(query="graphiti")

# ✅ CORRECT - Always specify group_ids explicitly
mcp__graphiti-local__get_episodes(
    group_ids=["graphiti_meta_knowledge"],
    max_episodes=10
)
mcp__graphiti-local__search_nodes(
    query="graphiti",
    group_ids=["graphiti_meta_knowledge"]
)
```

## Available Knowledge Graphs

| Group ID | Purpose |
|----------|---------|
| `graphiti_meta_knowledge` | How to use Graphiti effectively |
| `graphiti_reference_docs` | Reference documentation summaries |

**Query current counts:**
```python
# Get live episode counts (don't rely on hardcoded numbers)
mcp__docker__read_neo4j_cypher(
    query="MATCH (e:Episodic) RETURN e.group_id AS group_id, count(*) AS episodes ORDER BY episodes DESC"
)
```

**Query all groups at once:**
```python
mcp__graphiti-local__get_episodes(
    group_ids=["graphiti_meta_knowledge", "graphiti_reference_docs"],
    max_episodes=20
)
```

---

> **🔒 SECURITY WARNING**: Never commit sensitive information to knowledge graphs:
> - API keys, passwords, tokens, credentials, PII, PHI, proprietary business data
>
> **All episodes are stored in plaintext**. See [CLAUDE.md](../CLAUDE.md) for best practices.

---

## ⛔ Guardrails - DO NOT (Without Explicit User Request)

| Action | Why It's Dangerous | What To Do Instead |
|--------|-------------------|-------------------|
| `clear_graph` | Permanently deletes ALL data | Ask user first |
| `delete_episode` | Irreversible data loss | Ask user first |
| `delete_entity_edge` | Removes relationships | Ask user first |
| Assume empty = broken | Usually wrong group_id | Check parameters first |
| "Fix" without asking | Might delete valid data | Report findings, ask user |

**If results are empty:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - it's almost always a `group_ids` parameter issue, NOT a broken system.

---

## Quick Exploration Examples

```python
# Browse meta-knowledge (how to use Graphiti)
mcp__graphiti-local__get_episodes(
    group_ids=["graphiti_meta_knowledge"],
    max_episodes=10
)

# Search for entities about a topic
mcp__graphiti-local__search_nodes(
    query="temporal tracking valid_at invalid_at",
    group_ids=["graphiti_meta_knowledge"],
    max_nodes=10
)

# Find relationships/facts
mcp__graphiti-local__search_memory_facts(
    query="Graphiti strengths and ideal use cases",
    group_ids=["graphiti_meta_knowledge"],
    max_facts=10
)
```

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
mcp__graphiti-local__add_memory(
    name="Architecture: MySystem - Characteristics",
    episode_body='{"system": "MySystem", "strengths": ["low latency", "horizontal scaling", "real-time processing"], "weaknesses": ["complex setup", "requires monitoring"], "ideal_for": ["high-throughput APIs", "real-time analytics"], "cost_profile": {"latency": "low", "operational_overhead": "medium"}}',
    source="json",
    source_description="System architecture comparison",
    group_id="architecture_decision_tree_2025"
)

# Decision criteria with multiple options
mcp__graphiti-local__add_memory(
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
mcp__graphiti-local__add_memory(
    name="Lesson: FastMCP Deployment - Evolution from Global State to Factory Pattern",
    episode_body="The deployment pattern evolved from using global state (2024) to factory pattern (2025). The key innovation was recognizing that FastMCP Cloud ignores if __name__ == '__main__' blocks. This represents a shift from imperative initialization to declarative factory functions. The factory pattern produces cleaner testability and eliminates global state complexity.",
    source="text",
    source_description="Deployment pattern evolution lesson",
    group_id="agent_memory_decision_tree_2025"
)

# Causal explanation with solution
mcp__graphiti-local__add_memory(
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
mcp__graphiti-local__get_episodes(
    group_ids=["architecture_decision_tree_2025"],
    max_episodes=5
)
# ✅ Confirms: Episode ingested successfully

# Step 2: Verify entities extracted (wait 5-10 seconds)
mcp__graphiti-local__search_nodes(
    query="MySystem latency",
    group_ids=["architecture_decision_tree_2025"],
    max_nodes=5
)
# ✅ Confirms: Entities created (e.g., "MySystem", "low latency", "horizontal scaling")

# Step 3: Verify relationships created (wait 15-20 seconds total from add_memory)
mcp__graphiti-local__search_memory_facts(
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
| `clear_graph` | ⚠️ **DESTRUCTIVE** - Permanently deletes all data for specified group(s) |

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

| Group | Purpose | Query First? |
|-------|---------|--------------|
| `graphiti_meta_knowledge` | How to use Graphiti effectively | ✅ Yes |
| `graphiti_reference_docs` | Reference documentation summaries | Optional |
| `{domain}_decision_tree_{year}` | Domain-specific knowledge graphs | As needed |
| `{project}_learnings` | Session-specific discoveries | As needed |

**Important**: The default `group_id` in config is `main`, but this namespace is typically empty. Always explicitly specify `group_ids` in your queries.

---

## Next Steps

1. **5 min**: Read [`reference/GRAPHITI_BEST_PRACTICES.md`](reference/GRAPHITI_BEST_PRACTICES.md)
2. **15 min**: Read [`reference/GRAPHITI_MCP_LESSONS_LEARNED.md`](reference/GRAPHITI_MCP_LESSONS_LEARNED.md)
3. **Optional**: Deep dive into [`reference/CLAUDE_META_KNOWLEDGE_REVIEW.md`](reference/CLAUDE_META_KNOWLEDGE_REVIEW.md)
4. **Hands-on**: Run examples in [`examples/`](examples/)

---

## Monitoring & Debugging (For Claude Code)

Claude Code has access to **three tiers** of Neo4j tools via MCP:

### Neo4j Access Tiers Overview

| Tier | MCP Server | Status | Use For |
|------|------------|--------|---------|
| **1. Semantic** | `graphiti-local` | ✅ Ready | Memory operations, search, add episodes |
| **2. Query** | `neo4j-cypher` | ✅ Ready | Direct Cypher queries, data quality audits |
| **3. Management** | `neo4j-cloud-aura-api` | ✅ Ready | Pause/resume instance, scaling, monitoring |

---

### Tier 1: Graphiti MCP Tools (Always Available)

Use these for day-to-day semantic operations:

```python
# Health check
mcp__graphiti-local__get_status()

# Check what's in each namespace
mcp__graphiti-local__get_episodes(
    group_ids=["graphiti_meta_knowledge", "graphiti_reference_docs"],
    max_episodes=50
)

# Search for specific entities
mcp__graphiti-local__search_nodes(
    query="your search term",
    group_ids=["graphiti_meta_knowledge"],
    max_nodes=20
)

# Find relationships/facts
mcp__graphiti-local__search_memory_facts(
    query="your search term",
    group_ids=["graphiti_meta_knowledge"],
    max_facts=20
)
```

---

### Tier 2: Direct Cypher Queries (Requires Configuration)

For data quality audits and advanced analysis, use the `neo4j-cypher` MCP server:

```python
# Database statistics
mcp__docker__read_neo4j_cypher(
    query="CALL apoc.meta.stats() YIELD nodeCount, relCount RETURN nodeCount, relCount"
)

# Group distribution
mcp__docker__read_neo4j_cypher(
    query="MATCH (e:Episodic) RETURN e.group_id AS group_id, count(*) AS count ORDER BY count DESC"
)

# Data quality: Find entities missing embeddings (CRITICAL - breaks search)
mcp__docker__read_neo4j_cypher(
    query="MATCH (n:Entity) WHERE n.name_embedding IS NULL RETURN n.name, n.group_id LIMIT 20"
)

# Find orphan entities
mcp__docker__read_neo4j_cypher(
    query="MATCH (n:Entity) WHERE NOT (n)-[:RELATES_TO]-() RETURN n.name, n.group_id LIMIT 20"
)
```

**Configuration**: Add `neo4j-cypher` to Docker MCP with database credentials.
**Alternative**: Use Neo4j Browser directly with queries from `scripts/cypher/`.

---

### Tier 3: Neo4j Aura Instance Management (Requires Configuration)

For infrastructure operations, use the `neo4j-cloud-aura-api` MCP server:

```python
# List all Aura instances
mcp__docker__list_instances()

# Get instance details by name
mcp__docker__get_instance_by_name(name="your-instance-name")

# Get instance details by ID
mcp__docker__get_instance_details(instance_ids=["your-instance-id"])

# Pause instance (cost savings when not in use)
mcp__docker__pause_instance(instance_id="your-instance-id")

# Resume paused instance
mcp__docker__resume_instance(instance_id="your-instance-id")

# Scale memory (GB)
mcp__docker__update_instance_memory(instance_id="your-instance-id", memory=2)

# Enable vector optimization (for embedding workloads)
mcp__docker__update_instance_vector_optimization(
    instance_id="your-instance-id",
    vector_optimized=True
)
```

**Configuration**:
1. Go to [Neo4j Aura Console](https://console.neo4j.io) → Account → API Credentials
2. Create credentials and note the `client_id` and `client_secret`
3. Configure Docker MCP with `NEO4J_AURA_CLIENT_ID` and `NEO4J_AURA_CLIENT_SECRET`

---

### Cypher Query Reference Files

Pre-built query files for Neo4j Browser are in `scripts/cypher/`:

| File | Purpose | Frequency |
|------|---------|-----------|
| `01_health_dashboard.cypher` | Database stats, group distribution | Daily |
| `02_data_quality.cypher` | Missing embeddings, orphans, duplicates | Weekly |
| `03_temporal_analysis.cypher` | Fact invalidation, knowledge evolution | As needed |
| `04_debug_search.cypher` | Find entities/episodes by name/UUID | As needed |
| `05_capacity_planning.cypher` | Size estimates, growth trends | Monthly |

---

### Common Issues & Solutions

| Symptom | Cause | Solution |
|---------|-------|----------|
| Empty query results | Missing `group_ids` | Always specify `group_ids` explicitly |
| "No episodes found" | Wrong namespace | List groups: `get_episodes(group_ids=[...])` |
| Search returns nothing | Embeddings missing | Run `02_data_quality.cypher` check |
| Slow queries | Large result sets | Reduce `max_*` params or add LIMIT |
| Cypher auth error | MCP not configured | Use Neo4j Browser or configure `neo4j-cypher` |
| Aura API 401 error | Missing API credentials | Configure `NEO4J_AURA_CLIENT_ID/SECRET` |

---

## Quick Reference Card

```
Episode Naming:     {Category}: {Subject} - {Aspect}
Categories:         Lesson, Best Practice, Anti-Pattern, Procedure, Architecture, Use Case
JSON Rule:          Flat structure, include id/name/description
Verification:       get_episodes → search_nodes (5-10s) → search_memory_facts (10-15s)
Meta-knowledge:     Always query graphiti_meta_knowledge first
Recovery:           uv run python scripts/populate_meta_knowledge.py
Cypher Queries:     scripts/cypher/*.cypher (for Neo4j Browser or MCP)
```
