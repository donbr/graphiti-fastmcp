# Graphiti Data Export/Import Best Practices: Research Findings

**Research Date:** 2025-12-09  
**Research Status:** Complete  
**Verification Sources:** Zep Documentation (qdrant-docs MCP), FalkorDB Docs, GitHub getzep/graphiti, Web Search

---

## Executive Summary

After comprehensive research, the key findings are:

1. **Graphiti is Episode-First by Design** - There are no official bulk import/export APIs for moving structured graph data
2. **Database-Level Backup is the Recommended Approach** - FalkorDB's RDB backup/restore preserves vector types correctly
3. **The vecf32() Corruption Problem Has a Fix** - Raw Cypher migrations must use `vecf32()` function in queries
4. **Zep Cloud Has Clone Graph API** - For hosted instances, use the `/graph/clone` endpoint
5. **CRUD Operations Exist But Are Low-Level** - Node/Edge `.save()` methods can be used for programmatic migration

---

## Research Question 1: Official APIs

### Findings

**No Official Bulk Import/Export APIs Exist**

According to Zep documentation (Doc ID: Zep_0114 - CRUD Operations), Graphiti provides:

- `EpisodicNode.save(driver)` - Saves episodic nodes
- `EntityNode.save(driver)` - Saves entity nodes
- `EpisodicEdge.save(driver)` - Saves episodic edges
- `EntityEdge.save(driver)` - Saves entity edges

The save method performs a **find-or-create** based on UUID:

```python
async def save(self, driver: AsyncDriver):
    result = await driver.execute_query(
        """
        MERGE (n:Entity {uuid: $uuid})
        SET n = {uuid: $uuid, name: $name, name_embedding: $name_embedding, 
                 summary: $summary, created_at: $created_at}
        RETURN n.uuid AS uuid
        """,
        uuid=self.uuid,
        name=self.name,
        name_embedding=self.name_embedding,
        ...
    )
```

**Zep Cloud Clone Graph API**

For Zep Cloud users, there's a Clone Graph API (Doc ID: Zep_0077):

```
POST https://api.getzep.com/api/v2/graph/clone
```

This clones a user or group graph and returns a new graph_id.

### Recommendation

For self-hosted Graphiti, there is **no application-level backup/restore API**. Use database-level backup instead (see Research Question 3).

---

## Research Question 2: Embedding Handling

### Findings

**FalkorDB Vector Storage**

According to FalkorDB documentation, vectors must be created using the `vecf32()` function:

```cypher
-- Creating a node with vector embedding
CREATE (p:Product {name: 'Laptop', embedding: vecf32([1.0, 2.0, 3.0])})

-- Querying vector index
CALL db.idx.vector.queryNodes('Product', 'embedding', 5, vecf32($query_vector))
YIELD node, score
```

**The Core Problem with Raw Cypher Migration**

When using raw Cypher `CREATE` statements with Python lists as parameters:

```python
# BROKEN - This corrupts embeddings
graph.query(
    "CREATE (n:Entity {name: $name, name_embedding: $embedding})",
    {"name": "test", "embedding": [1.0, 2.0, 3.0]}  # Python list
)
```

The Python FalkorDB driver passes the list directly, which gets stored as a generic array type instead of `Vectorf32`. This breaks vector similarity searches.

**The Fix**

Embeddings must be wrapped with `vecf32()` in the Cypher query:

```python
# CORRECT - Preserves vector type
embedding_list = [1.0, 2.0, 3.0]
query = f"""
CREATE (n:Entity {{
    name: $name, 
    name_embedding: vecf32({embedding_list})
}})
"""
graph.query(query, {"name": "test"})
```

Or use string interpolation for the vector values directly in the query string.

**LangChain FalkorDB Integration Pattern**

The LangChain FalkorDBVector implementation shows the correct pattern:

```python
# From langchain_community.vectorstores.falkordb_vector
"CALL db.idx.vector.queryNodes($entity_label, "
"$entity_property, $k, vecf32($embedding)) "
```

### Recommendation

If fixing `migrate_simple.py`:

1. Do NOT pass embeddings as query parameters
2. Use f-string interpolation with `vecf32()`:
   ```python
   f"vecf32({embedding.tolist()})"
   ```
3. Alternatively, regenerate embeddings post-migration using the same embedder

---

## Research Question 3: Disaster Recovery Patterns

### Findings

**FalkorDB Uses Redis RDB Backup**

FalkorDB (built on Redis protocol) supports standard Redis backup/restore:

```bash
# Create backup (run in redis-cli)
BGSAVE  # Background save (recommended for production)
# or
SAVE    # Synchronous save (blocks other operations)

# Backup file location
redis-cli CONFIG GET dir
# Returns: /var/lib/redis or similar

# The backup file is: dump.rdb
```

**Restore Process**

```bash
# 1. Stop FalkorDB
docker stop falkordb

# 2. Copy backup file to data directory
cp dump.rdb /path/to/falkordb/data/

# 3. Start FalkorDB
docker run -p 6379:6379 -v $(pwd):/data \
    -e REDIS_ARGS="--dir /data --dbfilename dump.rdb" \
    falkordb/falkordb
```

**This Preserves Vector Types**

The RDB file format preserves the internal representation of `Vectorf32` types, unlike Cypher parameter passing which converts to Python lists.

**FalkorDB Cloud Migration**

From RedisGraph to FalkorDB docs:
> "FalkorDB is fully compatible with RedisGraph RDB files, making migration straightforward."

### Recommendation

**For Disaster Recovery:**
1. Use `BGSAVE` to create RDB snapshots
2. Store `dump.rdb` files in external backup storage
3. Restore by mounting the RDB file to a new FalkorDB container

**For Graph Consolidation (your use case):**
- Database-level backup doesn't help merge multiple graphs
- See Hybrid Approach recommendation in Conclusions

---

## Research Question 4: Temporal Data Preservation

### Findings

**Graphiti Temporal Model**

From Zep documentation (Doc ID: Zep_0101 - Overview):

- Episodes have `reference_time` - when the event occurred
- Entity edges have `valid_at`, `invalid_at`, `expired_at`
- All nodes have `created_at`

**Episode add_episode() Reference Time**

```python
await graphiti.add_episode(
    name="Meeting Notes",
    episode_body="...",
    reference_time=datetime(2024, 1, 15),  # When event occurred
    source=EpisodeType.text,
    source_description="Meeting transcript"
)
```

The `reference_time` parameter controls temporal placement of extracted facts.

**Re-ingestion Limitations**

When re-importing episodes:
1. LLM may extract different entities/relationships
2. Timestamps can be preserved via `reference_time`
3. Entity UUIDs will be regenerated (unless using CRUD save methods)

### Recommendation

For temporal data preservation:
1. Export original `reference_time` values from episodes
2. Re-import with same `reference_time` to maintain temporal context
3. Accept that entity/edge UUIDs will change

---

## Research Question 5: Community Solutions

### Findings

**No Official Migration Tools Exist**

GitHub issues search revealed:
- Issue #366: User lost access to 60M token/$180 graph data due to group_id mismatch
- Issue #1063: Database connection issues after version upgrades
- No dedicated migration tools or scripts in the repository

**Related Issue: Unable to Retrieve Memories (#366)**

A user reported that after setup changes, the Cursor agent couldn't see existing nodes:
> "The agent connects to the database and can add memories and also retrieve them - but is absolutely blind to all my nodes and connections existing in the database."

This was due to `group_id` mismatch - Graphiti uses `group_id` for multi-tenancy isolation.

### Recommendation

1. Always verify `group_id` consistency between source and target
2. Consider filing a feature request for official migration tooling
3. Document any custom migration scripts for community benefit

---

## Recommended Approaches by Use Case

### Use Case 1: Disaster Recovery

| Approach | Recommendation | Confidence |
|----------|---------------|------------|
| **FalkorDB RDB Backup** | ✅ Recommended | High |
| Re-import via episodes | ❌ Not recommended | - |
| Raw Cypher copy | ❌ Not recommended | - |

**Implementation:**
```bash
# Backup
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb /backup/dump_$(date +%Y%m%d).rdb

# Restore
docker stop falkordb
cp /backup/dump_20241209.rdb /data/dump.rdb
docker start falkordb
```

### Use Case 2: Environment Migration (Local to FalkorDB Cloud)

| Approach | Recommendation | Confidence |
|----------|---------------|------------|
| **Upload RDB to Cloud** | ✅ Recommended | High |
| Re-import episodes | ⚠️ Works but may differ | Medium |

Contact FalkorDB Cloud support for RDB upload instructions.

### Use Case 3: Graph Consolidation (Multiple group_ids → One)

| Approach | Recommendation | Confidence |
|----------|---------------|------------|
| **Hybrid Approach** | ✅ Recommended | Medium |
| Fixed Cypher with vecf32() | ⚠️ Possible but fragile | Medium |
| Re-import all episodes | ⚠️ Semantic drift risk | Low |

**Hybrid Approach:**

1. **Export episodes from each source graph:**
   ```python
   # Query Episodic nodes
   MATCH (e:Episodic) WHERE e.group_id = $source_group_id
   RETURN e.content, e.source, e.source_description, e.reference_time
   ```

2. **Re-import episodes with new group_id:**
   ```python
   await graphiti.add_episode(
       name=episode.name,
       episode_body=episode.content,
       reference_time=episode.reference_time,
       source=episode.source,
       group_id=target_group_id  # New unified group
   )
   ```

3. **Accept semantic drift** - entities may be extracted differently

### Use Case 4: Backend Switch (Neo4j ↔ FalkorDB)

| Approach | Recommendation | Confidence |
|----------|---------------|------------|
| **Re-import episodes** | ✅ Recommended | High |
| Direct data copy | ❌ Not recommended | - |

Different backends have incompatible vector storage formats. Re-ingestion is required.

### Use Case 5: Version Upgrade

| Approach | Recommendation | Confidence |
|----------|---------------|------------|
| **Database backup + upgrade** | ✅ Recommended | High |
| Re-import if schema changed | ⚠️ Only if required | Medium |

```bash
# Before upgrade
redis-cli BGSAVE
cp dump.rdb dump_pre_upgrade.rdb

# Upgrade FalkorDB version
docker pull falkordb/falkordb:latest

# Restore if needed
cp dump_pre_upgrade.rdb dump.rdb
```

---

## Fixed Migration Script Pattern

If you need to fix `migrate_simple.py` for the vecf32 issue:

```python
import json
from falkordb import FalkorDB

async def migrate_node_with_embedding(source_graph, target_graph, node_data):
    """Migrate a node with proper vector handling."""
    
    # Extract embedding as Python list
    embedding = node_data['name_embedding']
    
    # Build query with vecf32() wrapper
    # NOTE: Using f-string for embedding to use vecf32()
    query = f"""
    CREATE (n:{node_data['label']} {{
        uuid: $uuid,
        name: $name,
        name_embedding: vecf32({json.dumps(embedding)}),
        summary: $summary,
        created_at: $created_at,
        group_id: $group_id
    }})
    """
    
    params = {
        'uuid': node_data['uuid'],
        'name': node_data['name'],
        'summary': node_data['summary'],
        'created_at': node_data['created_at'],
        'group_id': node_data['group_id']
    }
    
    await target_graph.query(query, params)

async def migrate_edge_with_embedding(source_graph, target_graph, edge_data):
    """Migrate an edge with proper vector handling."""
    
    fact_embedding = edge_data['fact_embedding']
    
    query = f"""
    MATCH (source:Entity {{uuid: $source_uuid}})
    MATCH (target:Entity {{uuid: $target_uuid}})
    CREATE (source)-[r:RELATES_TO {{
        uuid: $uuid,
        name: $name,
        fact: $fact,
        fact_embedding: vecf32({json.dumps(fact_embedding)}),
        valid_at: $valid_at,
        invalid_at: $invalid_at,
        expired_at: $expired_at,
        group_id: $group_id
    }}]->(target)
    """
    
    params = {
        'uuid': edge_data['uuid'],
        'source_uuid': edge_data['source_uuid'],
        'target_uuid': edge_data['target_uuid'],
        'name': edge_data['name'],
        'fact': edge_data['fact'],
        'valid_at': edge_data['valid_at'],
        'invalid_at': edge_data['invalid_at'],
        'expired_at': edge_data['expired_at'],
        'group_id': edge_data['group_id']
    }
    
    await target_graph.query(query, params)
```

**⚠️ Warning:** This bypasses Graphiti's entity extraction pipeline. Use only when:
- You need exact structure preservation
- You accept responsibility for data consistency
- You've tested thoroughly in a non-production environment

---

## Upstream Recommendations

Consider filing these feature requests with Zep/Graphiti:

1. **Official Export/Import CLI Tool**
   - Export graph to portable format (JSON/Parquet)
   - Import with options to preserve UUIDs, regenerate embeddings
   
2. **Bulk Node/Edge Import API**
   - `graphiti.import_nodes(nodes_list, preserve_embeddings=True)`
   - `graphiti.import_edges(edges_list, preserve_embeddings=True)`

3. **Documentation on Migration Patterns**
   - Official guidance for disaster recovery
   - Multi-tenancy consolidation patterns
   - Backend switching procedures

---

## Verification Summary

| Source | Tool Used | Key Finding |
|--------|-----------|-------------|
| Zep Docs (Zep_0114) | qdrant-docs MCP | CRUD save() methods exist |
| Zep Docs (Zep_0077) | qdrant-docs MCP | Clone Graph API for cloud |
| FalkorDB Indexing Docs | Web Search | vecf32() required for vectors |
| Redis Persistence Docs | Web Search | RDB backup preserves types |
| GitHub #366 | Web Search | group_id isolation critical |

**Last Verified:** 2025-12-09 via web_search and qdrant-docs MCP tools

---

## Conclusions

### Hypothesis 1: Episode-First by Design ✅ CONFIRMED

Graphiti intentionally does not support bulk node/edge import. The episodic model ensures semantic consistency through LLM extraction.

### Hypothesis 2: vecf32() Fix Works ⚠️ PARTIALLY CONFIRMED

Using `vecf32()` in Cypher queries should preserve embedding types, but this bypasses Graphiti's semantic layer. Not officially supported.

### Hypothesis 3: Database-Level Backup is the Answer ✅ CONFIRMED

For disaster recovery, FalkorDB's RDB backup/restore is the correct approach. It preserves vector types and all data.

### Hypothesis 4: Hybrid Approach Needed ✅ CONFIRMED

For graph consolidation:
1. Export episodes (for semantic content)
2. Re-import with unified group_id
3. Accept that entity extraction may differ

---

*Research completed: 2025-12-09*
*Tools used: qdrant-docs MCP (Zep source), web_search, web_fetch*
