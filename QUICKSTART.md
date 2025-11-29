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

Run these immediately to verify your connection and understand what knowledge exists:

```python
# 1. Check connection
get_status()
# Expected: {"status": "ok", "group_ids": [...]}

# 2. Query existing meta-knowledge (how to use Graphiti)
search_memory_facts(
    query="best practices episode design",
    group_ids=["graphiti_meta_knowledge"],
    max_facts=5
)

# 3. See what domain graphs exist
get_episodes(group_ids=["agent_memory_decision_tree_2025"], max_episodes=5)
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

```python
# JSON episode (for structured data)
mcp__graphiti-memory__add_memory(
    name="Architecture: MySystem - Characteristics",
    episode_body='{"system": "MySystem", "strengths": ["fast", "reliable"], "ideal_for": ["production"]}',
    source="json",
    source_description="Initial system documentation",
    group_id="my_project_knowledge"
)

# Text episode (for narratives)
mcp__graphiti-memory__add_memory(
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
