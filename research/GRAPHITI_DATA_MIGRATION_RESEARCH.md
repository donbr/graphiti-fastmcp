# Research: Graphiti Data Export/Import Best Practices

| Field | Value |
|-------|-------|
| **Date** | 2025-12-09 |
| **Status** | Research prompt - awaiting investigation |
| **Related Issues** | #1098, #1100, MIGRATION_NOTES.md |

---

## Background

Graphiti is a temporal knowledge graph framework designed for AI agent memory. Its primary ingestion pattern is **episodic**: you provide text or JSON content, and Graphiti's LLM pipeline extracts entities, relationships, and generates embeddings.

However, real-world scenarios often require moving **existing structured graph data** (nodes, edges, embeddings) between systems, which doesn't fit the episodic model.

### What Triggered This Research

We attempted to consolidate multiple FalkorDB graphs into a single `default_db` graph using a custom migration script (`migrate_simple.py`). The script used raw Cypher `CREATE` statements to copy nodes and edges, which corrupted `Vectorf32` embeddings into Python `List` types, breaking all vector similarity searches.

---

## The Core Problem

| Approach | Preserves Structure | Correct Embeddings | Preserves Temporal Data |
|----------|--------------------|--------------------|------------------------|
| Re-import via `add_memory` | ❌ Re-extracts differently | ✅ Regenerated correctly | ❌ Loses original timestamps |
| Raw Cypher copy | ✅ Exact structure | ❌ Corrupts Vectorf32→List | ✅ Preserves all fields |
| Unknown best practice? | ? | ? | ? |

### The Tension

- **Episode-based import**: Clean, correct embeddings, but loses exact entity/relationship structure and may extract differently
- **Raw Cypher copy**: Preserves structure exactly, but corrupts embeddings (as we discovered)
- **Hybrid approach needed?**: Unknown if one exists

---

## Research Questions

### 1. Official APIs

- Does `graphiti_core` have any bulk import, restore, or migration APIs beyond `add_episode()`?
- Are there internal methods for directly creating nodes/edges with pre-computed embeddings?
- What methods does the `Graphiti` class expose for low-level graph manipulation?
- Is there a `restore_from_backup()` or similar method?

### 2. Embedding Handling

- How does graphiti-core store embeddings in FalkorDB? (The `vecf32()` wrapper)
- Can embeddings be imported without regeneration if they're in the correct format?
- What happens if embedding dimensions change between export and import?
- How does the Python FalkorDB driver serialize `Vectorf32` types?

### 3. Disaster Recovery Patterns

- How does Zep Cloud handle backup/restore for hosted Graphiti instances?
- Is there an official recommendation for graph snapshots?
- What's the expected workflow for migrating between FalkorDB and Neo4j backends?
- Does Graphiti support database-level backup/restore?

### 4. Temporal Data Preservation

- How should `valid_at`, `invalid_at`, `created_at`, `expired_at` be handled during migration?
- Does re-ingestion via episodes respect original temporal markers?
- Is there a way to import facts with specific validity periods?
- Can `reference_time` in `add_episode()` control temporal placement?

### 5. Community Solutions

- Are there any community-contributed migration tools or scripts?
- Has anyone documented a successful graph-to-graph migration pattern?
- What approaches have been used for FalkorDB Cloud migrations?
- Are there any GitHub discussions or issues about this topic?

---

## Use Cases to Address

### 1. Disaster Recovery
Restore a graph from backup after data loss.
- **Current approach**: Export episodes to JSON, re-import via `add_memory`
- **Limitation**: Entity extraction may produce different results

### 2. Environment Migration
Move from local FalkorDB to FalkorDB Cloud.
- **Current approach**: Unknown
- **Challenge**: Need to preserve embeddings in correct format

### 3. Graph Consolidation
Merge multiple graphs with different group_ids into one.
- **Current approach**: `migrate_simple.py` (broken)
- **Challenge**: Embedding type corruption

### 4. Backend Switch
Migrate from Neo4j to FalkorDB (or vice versa).
- **Current approach**: Unknown
- **Challenge**: Different vector storage formats

### 5. Version Upgrade
Migrate data when Graphiti's schema changes.
- **Current approach**: Unknown
- **Challenge**: Schema compatibility

---

## Technical Constraints

### FalkorDB Embedding Storage
- Requires `Vectorf32` type, not Python lists
- Must use `vecf32()` function in Cypher to create/query vectors
- Parameter passing has type mismatch issues (see #1100)

### Graphiti Data Model
- **Episodic nodes**: Contain `content`, `source`, `source_description`, `reference_time`
- **Entity nodes**: Have `name`, `name_embedding`, `summary`, `summary_embedding`
- **Relationships**: Have temporal validity (`valid_at`, `invalid_at`, `expired_at`)
- **All nodes**: Have `group_id` for namespacing, `uuid` for identity

### LLM Dependency
- Entity names extracted by LLM may differ between runs
- Relationship types depend on LLM interpretation
- Embeddings depend on embedder model and dimensions

---

## Current Tools Inventory

### Our Scripts

| Script | Purpose | Approach | Status |
|--------|---------|----------|--------|
| `scripts/export_graph.py` | Export episodes to JSON | Queries Episodic nodes | ✅ Working |
| `scripts/import_graph.py` | Import episodes from JSON | Uses `add_memory` MCP tool | ✅ Working |
| `scripts/migrate_simple.py` | Copy nodes/edges via Cypher | Raw Cypher CREATE | ❌ Corrupts embeddings |

### Graphiti APIs

| API | Purpose | Preserves Structure? |
|-----|---------|---------------------|
| `graphiti.add_episode()` | Add new episode | No - extracts fresh |
| `graphiti.search()` | Query graph | N/A |
| `graphiti.build_indices_and_constraints()` | Setup schema | N/A |
| `graphiti._driver.execute_query()` | Raw Cypher | Yes - but risky |

---

## Resources to Check

### Documentation
- Zep Graphiti docs: https://docs.getzep.com/graphiti
- FalkorDB vector docs: https://docs.falkordb.com/cypher/functions
- graphiti-core source: https://github.com/getzep/graphiti

### Source Code Locations
- `graphiti_core/graphiti.py` - Main class, check for bulk import methods
- `graphiti_core/driver/` - Database drivers, check for backup/restore
- `graphiti_core/nodes.py` - Node definitions, check for serialization
- `graphiti_core/edges.py` - Edge definitions

### MCP Tools Available
- `mcp__qdrant-docs__search_docs` - Search Zep documentation
- `mcp__Context7__get-library-docs` - Get graphiti source code
- `mcp__ai-docs-server__fetch_docs` - Fetch documentation pages

---

## Desired Research Outputs

1. **Recommended approach for each use case** listed above
2. **Code examples or API references** if official solutions exist
3. **Workarounds** if no official solution exists
4. **Warnings** about data loss or semantic drift risks
5. **Upstream recommendations** - should we file a feature request?

---

## Hypotheses to Test

### Hypothesis 1: Graphiti is Episode-First by Design
Graphiti may intentionally not support bulk node/edge import because the episodic model ensures semantic consistency. The "correct" approach may always be to re-ingest original content.

### Hypothesis 2: FalkorDB Driver Needs vecf32() Fix in Migration
If we fix `migrate_simple.py` to use `vecf32()` for embedding properties, raw Cypher migration might work. But this bypasses Graphiti's entity extraction.

### Hypothesis 3: Database-Level Backup is the Answer
For disaster recovery, using FalkorDB's native backup/restore (if it exists) or Neo4j's backup tools may be more appropriate than application-level migration.

### Hypothesis 4: Hybrid Approach Needed
The best approach may be:
1. Export episodes (for semantic content)
2. Export entity/relationship metadata separately (for structure)
3. Re-import episodes, then patch metadata

---

## Next Steps

1. [ ] Search Zep documentation for "backup", "restore", "migrate", "export", "import"
2. [ ] Examine graphiti-core source for bulk import APIs
3. [ ] Check FalkorDB documentation for database backup/restore
4. [ ] Search GitHub issues for migration discussions
5. [ ] Test if `reference_time` in `add_episode()` preserves temporal data
6. [ ] Document findings and recommendations

---

*Research prompt created: 2025-12-09*
*To be investigated using: qdrant-docs MCP, Context7 MCP, web search, source code analysis*
