# Graphiti Memory Best Practices for Claude Code

A guide for effectively using the `graphiti-fastmcp` MCP with Claude Code to build temporal knowledge graphs that accumulate learnings across sessions.

> **New here?** Start with [`QUICKSTART.md`](../QUICKSTART.md) for a 5-minute introduction.
>
> **Want real-world examples?** See [`GRAPHITI_MCP_LESSONS_LEARNED.md`](./GRAPHITI_MCP_LESSONS_LEARNED.md) for hands-on discoveries.

## Overview

Graphiti is a temporal knowledge graph that transforms information into a richly connected network of:
- **Episodes**: Content snippets (the source data)
- **Nodes**: Extracted entities
- **Facts**: Relationships between entities with temporal metadata

The `graphiti-fastmcp` MCP provides tools to interact with Graphiti directly from Claude Code.

## Group Organization Strategy

Use `group_id` to segment knowledge domains:

| Group Type | Example | Purpose |
|------------|---------|---------|
| Meta-knowledge | `claude_meta_knowledge` | Best practices, learnings, procedures |

**Rationale**: Separate groups enable targeted searches without noise and allow meta-knowledge to be reusable across projects.

## Episode Design

### Source Types

| Type | Use For | Example |
|------|---------|---------|
| `json` | Structured data with clear schemas | Identity, certifications, project metadata |
| `text` | Narratives, descriptions, freeform content | Experience descriptions, lessons learned |
| `message` | Conversational format | `speaker: message` pairs |

### Naming Convention

Pattern: `{Category}: {Topic} - {Specific Aspect}`

```
Best Practice: JSON Ingestion - Flattening Nested Data
Lesson: MCP Tools - Standalone Python Limitation
Experience: IBM - Application Architect
Project: GDELT KB - Metadata
Preference: Episode Naming - Hierarchical Pattern
```

For person-centric data: `{Person Name} - {Category}`
```
Don Branson - Professional Identity
Don Branson - Technology Expertise
```

### Episode Categories

| Category | When to Use |
|----------|-------------|
| `Lesson:` | Single insight from a session |
| `Procedure:` | Multi-step workflow that works |
| `Anti-Pattern:` | What NOT to do (with rationale) |
| `Preference:` | User-specific conventions |
| `Best Practice:` | Consolidated, stable guidance |
| `Tool Usage:` | How to effectively use specific tools |

## JSON Structure Guidelines

When using `source="json"`:

### Do

1. **Keep JSON flat** (3-4 levels max)
   - Deeply nested JSON produces sparse graphs

2. **Include identifying fields**
   ```json
   {
     "id": "proj_001",
     "name": "GDELT Knowledge Base",
     "description": "Knowledge graph project for global events"
   }
   ```

3. **Use atomic attributes**
   ```json
   {"name": "John", "email": "john@example.com"}
   ```

4. **Split large objects** into smaller unified entities
   - Separate episodes for identity, skills, experience

### Avoid

- 5+ levels of nesting
- JSON without `id`/`name`/`description` fields
- Compound attributes: `{"contact_info": "John - john@example.com"}`
- Single massive JSON with all data

## MCP Tool Usage

### Available Tools

| Tool | Purpose |
|------|---------|
| `add_memory` | Add episodes to the graph |
| `search_nodes` | Find entities by query |
| `search_memory_facts` | Find relationships between entities |
| `get_episodes` | Retrieve episodes by group |
| `get_status` | Check server/database connection |
| `delete_episode` | Remove an episode |
| `delete_entity_edge` | Remove a relationship |
| `clear_graph` | Clear all data for group(s) |

### Key Insight: MCP Context Requirement

MCP tools like `mcp__graphiti-fastmcp__add_memory` are **only accessible within Claude's context** (Claude Code, Cursor with MCP).

Standalone Python scripts cannot directly call MCP tools. Options:
1. Use Claude's direct MCP tool access for ingestion
2. Implement MCP client connection using MCP Python SDK

## Verification Pattern

Episodes are processed **asynchronously**. When `add_memory` returns "queued for processing", entity/fact extraction happens in background.

### Three-Tool Verification

```python
# 1. Confirm episode exists
get_episodes(group_ids=["your_group_id"], max_episodes=10)

# 2. Verify entities were extracted
search_nodes(query="key terms", group_ids=["your_group_id"])

# 3. Verify relationships were created
search_memory_facts(query="key terms", group_ids=["your_group_id"])
```

Allow brief delay for background processing to complete.

## Meta-Knowledge Workflow

### Before Any Graphiti Task

```python
# Query existing knowledge first
search_memory_facts(
    query="<task domain> best practices",
    group_ids=["claude_meta_knowledge"]
)
```

### Knowledge Lifecycle

```
Fine-grained episodes (Lesson:)
        ↓ patterns emerge
Consolidated episodes (Best Practice:)
        ↓ temporal facts track evolution
Updated episodes (when knowledge changes)
```

### Granularity Strategy

| Knowledge State | Granularity | Example |
|-----------------|-------------|---------|
| New insight | Fine-grained | `Lesson: Async Processing - Queue Delay` |
| Stable pattern | Consolidated | `Best Practice: Episode Design` |
| Evolving | Fine-grained until stable | New lessons accumulate |

Graphiti's temporal facts (`valid_at`, `invalid_at`) automatically handle knowledge evolution - old facts get invalidated, new ones created, history preserved.

## Relationship Types

Common edge types extracted by Graphiti:

| Relationship | Meaning |
|--------------|---------|
| `INCLUDES_PRACTICE` | Best practice doc → specific guidance |
| `PRACTICE_RATIONALE` | Explains why a practice is recommended |
| `CITES_SOURCE` | Provenance to source documentation |
| `GIVES_EXAMPLE` | Connects practice → concrete example |
| `HAS_TYPE` | Classification of entity |
| `HAS_CATEGORY` | Domain categorization |
| `DEMONSTRATES_EXPERTISE_IN` | Person → skill/domain |
| `WORKED_AT` | Person → organization |

## Quick Reference

### Add a Best Practice

```python
mcp__graphiti-fastmcp__add_memory(
    name="Best Practice: JSON Ingestion - Flattening",
    episode_body='{"id": "bp_001", "name": "...", "description": "...", "practices": [...]}',
    source="json",
    source_description="Consolidated best practices for JSON structure",
    group_id="claude_meta_knowledge"
)
```

### Add a Session Learning

```python
mcp__graphiti-fastmcp__add_memory(
    name="Lesson: MCP Tools - Context Requirement",
    episode_body="Key learning: MCP tools only accessible within Claude context...",
    source="text",
    source_description="Session learning about MCP accessibility",
    group_id="claude_meta_knowledge"
)
```

### Search Before Starting

```python
# Check for relevant guidance
search_memory_facts(
    query="ingestion best practices JSON",
    group_ids=["claude_meta_knowledge"],
    max_facts=10
)

# Find related entities
search_nodes(
    query="episode design naming",
    group_ids=["claude_meta_knowledge"],
    max_nodes=10
)
```

## References

- [Zep Graphiti Documentation](https://help.getzep.com/graphiti/getting-started/welcome.mdx)
- [Adding JSON Best Practices](https://help.getzep.com/adding-json-best-practices.mdx)
- [Custom Entity and Edge Types](https://help.getzep.com/graphiti/core-concepts/custom-entity-and-edge-types.mdx)
- [Adding Episodes](https://help.getzep.com/graphiti/core-concepts/adding-episodes.mdx)
