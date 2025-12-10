---
title: "Graphiti Graph Migration: FalkorDB ↔ Neo4j"
created: 2025-12-09
updated: 2025-12-09
tags:
  - graph
  - graphiti
  - falkordb
  - neo4j
  - migration
---

# Graphiti Graph Migration: FalkorDB ↔ Neo4j

**Research Date:** 2025-12-09  
**Research Status:** Complete  
**Verification Sources:** Zep/Graphiti docs (Context7 MCP), FalkorDB GitHub, Neo4j docs, getzep/graphiti source code

---

## Executive Summary

After comprehensive research across multiple sources, the key findings for migrating Graphiti graphs between FalkorDB and Neo4j are:

1. **No Official Graphiti Migration Tooling** - Graphiti provides separate drivers but no built-in migration utilities
2. **Vector Index Formats Are Incompatible** - Neo4j uses HNSW with `db.index.vector.queryNodes()`, FalkorDB uses `vecf32()` with `db.idx.vector.queryNodes()`
3. **Cypher Syntax Differences Exist** - Fulltext search, vector queries, and index creation use different syntax
4. **FalkorDB Has Official Neo4j→FalkorDB Migration Tool** - `FalkorDB/migrate-neo4j-falkordb` repository
5. **No Official FalkorDB→Neo4j Migration Tool** - Reverse migration requires custom scripting
6. **Re-ingestion Via Episodes is the Recommended Approach** - Preserves semantic consistency at cost of exact structure

---

## Graphiti Driver Architecture

### Driver Abstraction Layer

Graphiti uses a pluggable driver architecture defined in `graphiti_core/driver/`:

| Driver | File | Backend | Vector Search |
|--------|------|---------|---------------|
| `Neo4jDriver` | `neo4j_driver.py` | Neo4j 5.26+ | `db.index.vector.queryNodes()` |
| `FalkorDriver` | `falkordb_driver.py` | FalkorDB 1.1.2+ | `db.idx.vector.queryNodes()` with `vecf32()` |
| `KuzuDriver` | `kuzu_driver.py` | Kuzu (embedded) | `array_cosine_similarity()` |
| `NeptuneDriver` | `neptune_driver.py` | Amazon Neptune | OpenSearch Serverless |

### Driver Initialization Patterns

**Neo4j:**
```python
from graphiti_core import Graphiti
from graphiti_core.driver.neo4j_driver import Neo4jDriver

driver = Neo4jDriver(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password",
    database="my_database"  # Optional, defaults to "neo4j"
)
graphiti = Graphiti(graph_driver=driver)
```

**FalkorDB:**
```python
from graphiti_core import Graphiti
from graphiti_core.driver.falkordb_driver import FalkorDriver

driver = FalkorDriver(
    host="localhost",
    port=6379,
    username=None,
    password=None,
    database="my_graph"  # Optional, defaults to "default_db"
)
graphiti = Graphiti(graph_driver=driver)
```

### Key Driver Differences

| Feature | Neo4j | FalkorDB |
|---------|-------|----------|
| **Default Database** | `neo4j` | `default_db` |
| **Default group_id** | `''` (empty string) | `'\_'` (escaped underscore) |
| **Protocol** | Bolt (port 7687) | Redis (port 6379) |
| **Datetime Handling** | Native datetime types | ISO strings (converted) |
| **Fulltext Syntax** | `$query` parameter | `@field:value` RedisSearch syntax |
| **Vector Creation** | Native array property | `vecf32()` wrapper required |

---

## Vector Index Incompatibilities

### The Core Problem

Neo4j and FalkorDB store and query vectors differently, making direct data migration problematic.

### Neo4j Vector Handling

```cypher
-- Index creation (from graph_queries.py)
CREATE VECTOR INDEX name_embedding IF NOT EXISTS
FOR (n:Entity) ON (n.name_embedding)
OPTIONS {indexConfig: {
    `vector.dimensions`: 1024,
    `vector.similarity_function`: 'cosine'
}}

-- Query pattern
CALL db.index.vector.queryNodes('name_embedding', 10, $query_vector)
YIELD node, score

-- Similarity calculation
vector.similarity.cosine(n.name_embedding, $query_vector)
```

### FalkorDB Vector Handling

```cypher
-- Index creation
CREATE VECTOR INDEX FOR (n:Entity) ON (n.name_embedding) 
OPTIONS {dimension: 1024, similarityFunction: 'cosine'}

-- Query pattern (CRITICAL: uses vecf32() wrapper)
CALL db.idx.vector.queryNodes(
    'Entity',            -- Label (not index name!)
    'name_embedding',    -- Property name
    10,                  -- K results
    vecf32($query_vector)  -- MUST use vecf32()
) YIELD node, score

-- Similarity calculation (different formula)
(2 - vec.cosineDistance(n.name_embedding, vecf32($query_vector))) / 2
```

### Migration Implications

| Scenario | Challenge | Impact |
|----------|-----------|--------|
| **Neo4j → FalkorDB** | Vectors stored as native arrays must be readable by FalkorDB | Medium - FalkorDB can read arrays |
| **FalkorDB → Neo4j** | `Vectorf32` type must be converted to standard arrays | High - Type conversion required |
| **Query Migration** | Different procedure names and parameters | High - All queries must be rewritten |
| **Index Migration** | Different index creation syntax | Medium - Schema recreation needed |

---

## Fulltext Search Differences

### Neo4j Fulltext Syntax

```cypher
-- Index creation
CREATE FULLTEXT INDEX node_name_and_summary IF NOT EXISTS
FOR (n:Entity) ON EACH [n.name, n.summary, n.group_id]

-- Query
CALL db.index.fulltext.queryNodes("node_name_and_summary", $query, {limit: $limit})
YIELD node, score
```

### FalkorDB Fulltext Syntax (RedisSearch-based)

```cypher
-- Index creation
CALL db.idx.fulltext.createNodeIndex(
    {
        label: 'Entity',
        stopwords: ['a', 'is', 'the', ...]
    },
    'name', 'summary', 'group_id'
)

-- Query (uses @ prefix for field queries)
CALL db.idx.fulltext.queryNodes('Entity', '@group_id:main (search terms)')
YIELD node, score
```

### Key Syntax Differences

| Feature | Neo4j | FalkorDB |
|---------|-------|----------|
| **Index Reference** | Index name | Node label |
| **Query Syntax** | Plain text | RedisSearch syntax (`@field:value`) |
| **Stopwords** | Server configuration | Query-time configuration |
| **Field Queries** | Via Lucene syntax | `@field:value` syntax |

---

## Official Migration Tools

### Neo4j → FalkorDB: FalkorDB/migrate-neo4j-falkordb

**Repository:** https://github.com/FalkorDB/migrate-neo4j-falkordb

**Migration Flow:**
```
1. Export from Neo4j (CSV via APOC)
     ↓
2. Transform data (datetime → UNIX epoch, label mapping)
     ↓
3. Import to FalkorDB (LOAD CSV)
     ↓
4. Verify data integrity
```

**Key Features:**
- Preserves node labels, relationships, properties, constraints
- Handles temporal data conversion (Neo4j datetime → UNIX epoch)
- Provides comparison scripts for verification

**Limitations for Graphiti:**
- Does NOT handle vector embeddings specifically
- Designed for general graphs, not Graphiti's specific schema
- Requires manual adaptation for Graphiti's node types (Entity, Episodic, Community)

### FalkorDB → Neo4j: No Official Tool

**Current Status:** No official reverse migration tool exists.

**Required Approach:**
1. Export via Cypher queries (MATCH, RETURN)
2. Transform `Vectorf32` → standard arrays
3. Import via Cypher/APOC
4. Recreate Neo4j-specific indexes

---

## Recommended Migration Strategies

### Strategy 1: Episode Re-Ingestion (Recommended)

**Best for:** Production migrations where semantic consistency matters

**Approach:**
1. Export Episodic nodes from source graph
2. Create new Graphiti instance with target driver
3. Re-ingest episodes via `add_episode()`
4. Accept that entity extraction may differ

**Pros:**
- Embeddings generated correctly for target backend
- Semantic consistency guaranteed
- Clean schema and indexes

**Cons:**
- Entity/relationship UUIDs will change
- LLM may extract different entities
- Temporal data needs careful handling via `reference_time`

**Code Example:**
```python
# Export episodes from FalkorDB
source_driver = FalkorDriver(host="localhost", port=6379, database="source_db")
result = await source_driver.execute_query("""
    MATCH (e:Episodic)
    WHERE e.group_id = $group_id
    RETURN e.content, e.source, e.source_description, 
           e.reference_time, e.group_id
""", params={"group_id": "my_group"})

# Re-ingest to Neo4j
target_graphiti = Graphiti(
    uri="bolt://localhost:7687",
    user="neo4j",
    password="password"
)
await target_graphiti.build_indices_and_constraints()

for episode in episodes:
    await target_graphiti.add_episode(
        name=episode['source'],
        episode_body=episode['content'],
        source=EpisodeType.text,
        source_description=episode['source_description'],
        reference_time=parse_datetime(episode['reference_time']),
        group_id=episode['group_id']
    )
```

### Strategy 2: Direct Data Copy with Vector Handling

**Best for:** Development/testing where exact structure matters

**Approach:**
1. Export all nodes and edges via Cypher
2. Transform vector formats appropriately
3. Import with proper vector wrappers
4. Rebuild indexes

**For Neo4j → FalkorDB:**
```python
# Export from Neo4j
neo4j_result = neo4j_session.run("""
    MATCH (n:Entity)
    RETURN n.uuid, n.name, n.summary, n.name_embedding, 
           n.group_id, n.created_at
""")

# Import to FalkorDB with vecf32()
for node in neo4j_result:
    embedding = node['name_embedding']
    # CRITICAL: Use vecf32() in query string, NOT parameter
    query = f"""
    CREATE (n:Entity {{
        uuid: $uuid,
        name: $name,
        summary: $summary,
        name_embedding: vecf32({list(embedding)}),
        group_id: $group_id,
        created_at: $created_at
    }})
    """
    falkordb_graph.query(query, params={...})
```

**For FalkorDB → Neo4j:**
```python
# Export from FalkorDB
falkor_result = await falkor_driver.execute_query("""
    MATCH (n:Entity)
    RETURN n.uuid, n.name, n.summary, n.name_embedding,
           n.group_id, n.created_at
""")

# Import to Neo4j (vectors are standard arrays)
for node in falkor_result:
    embedding = node['name_embedding']
    # Neo4j accepts standard arrays directly
    neo4j_session.run("""
        CREATE (n:Entity {
            uuid: $uuid,
            name: $name,
            summary: $summary,
            name_embedding: $embedding,
            group_id: $group_id,
            created_at: $created_at
        })
    """, uuid=node['uuid'], name=node['name'], 
       embedding=list(embedding), ...)
```

**⚠️ Warning:** This bypasses Graphiti's semantic extraction layer. Use only when exact structure preservation is required.

### Strategy 3: Hybrid Approach

**Best for:** Complex migrations with specific requirements

**Steps:**
1. Export episodes AND entity metadata separately
2. Re-ingest episodes to new backend
3. Compare extracted entities with original
4. Patch any critical metadata discrepancies via CRUD operations

```python
# Use Graphiti's CRUD operations for metadata patches
from graphiti_core.nodes import EntityNode

# After re-ingestion, fix specific entities if needed
entity = EntityNode(
    uuid=original_uuid,  # Preserve original UUID
    name="Original Name",
    summary="Original summary preserved",
    name_embedding=regenerated_embedding,  # From new backend's embedder
    group_id="my_group"
)
await entity.save(target_driver)
```

---

## Schema Recreation

### Entity Node Schema

Both backends use the same Graphiti schema, but index syntax differs:

**Neo4j:**
```cypher
CREATE INDEX entity_uuid IF NOT EXISTS FOR (n:Entity) ON (n.uuid)
CREATE INDEX entity_group_id IF NOT EXISTS FOR (n:Entity) ON (n.group_id)
CREATE INDEX name_entity_index IF NOT EXISTS FOR (n:Entity) ON (n.name)
CREATE FULLTEXT INDEX node_name_and_summary IF NOT EXISTS
    FOR (n:Entity) ON EACH [n.name, n.summary, n.group_id]
CREATE VECTOR INDEX name_embedding IF NOT EXISTS
    FOR (n:Entity) ON (n.name_embedding)
    OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}}
```

**FalkorDB:**
```cypher
CREATE INDEX FOR (n:Entity) ON (n.uuid, n.group_id, n.name, n.created_at)
CALL db.idx.fulltext.createNodeIndex({label: 'Entity', stopwords: [...]}, 'name', 'summary', 'group_id')
CREATE VECTOR INDEX FOR (n:Entity) ON (n.name_embedding) 
    OPTIONS {dimension: 1024, similarityFunction: 'cosine'}
```

### Relationship Schema (RELATES_TO)

**Neo4j:**
```cypher
CREATE INDEX relation_uuid IF NOT EXISTS FOR ()-[e:RELATES_TO]-() ON (e.uuid)
CREATE INDEX valid_at_edge_index IF NOT EXISTS FOR ()-[e:RELATES_TO]-() ON (e.valid_at)
CREATE FULLTEXT INDEX edge_name_and_fact IF NOT EXISTS
    FOR ()-[e:RELATES_TO]-() ON EACH [e.name, e.fact, e.group_id]
CREATE VECTOR INDEX fact_embedding IF NOT EXISTS
    FOR ()-[r:RELATES_TO]-() ON (r.fact_embedding)
    OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}}
```

**FalkorDB:**
```cypher
CREATE INDEX FOR ()-[e:RELATES_TO]-() ON (e.uuid, e.group_id, e.name, e.created_at, e.expired_at, e.valid_at, e.invalid_at)
CREATE FULLTEXT INDEX FOR ()-[e:RELATES_TO]-() ON (e.name, e.fact, e.group_id)
CREATE VECTOR INDEX FOR ()-[e:RELATES_TO]-() ON (e.fact_embedding)
    OPTIONS {dimension: 1024, similarityFunction: 'cosine'}
```

---

## Temporal Data Handling

### FalkorDB Limitation

FalkorDB does NOT support Neo4j's native temporal types (`date`, `datetime`, `localdatetime`).

**FalkorDB expects:** UNIX epoch time in microseconds

**Migration Transform:**
```python
def convert_neo4j_datetime_to_falkordb(dt):
    """Convert Neo4j datetime to FalkorDB UNIX epoch microseconds."""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt)
    return int(dt.timestamp() * 1_000_000)

def convert_falkordb_epoch_to_neo4j(epoch_us):
    """Convert FalkorDB UNIX epoch to ISO datetime string."""
    return datetime.fromtimestamp(epoch_us / 1_000_000, tz=timezone.utc).isoformat()
```

### Graphiti Temporal Fields

| Field | Node/Edge | Purpose |
|-------|-----------|---------|
| `created_at` | All | When the record was created |
| `reference_time` | Episodic | When the event occurred |
| `valid_at` | RELATES_TO | When the fact became true |
| `invalid_at` | RELATES_TO | When the fact became false |
| `expired_at` | RELATES_TO | When the record was superseded |

---

## Migration Verification Checklist

### Pre-Migration
- [ ] Backup source database (RDB for FalkorDB, neo4j-admin dump for Neo4j)
- [ ] Document source graph statistics (node count, edge count, index list)
- [ ] Verify embedding dimensions match between source and target
- [ ] Test migration script on sample data first

### Post-Migration
- [ ] Verify node counts match for each label (Entity, Episodic, Community)
- [ ] Verify edge counts for each type (RELATES_TO, MENTIONS, HAS_MEMBER)
- [ ] Test vector similarity search returns results
- [ ] Test fulltext search returns results
- [ ] Verify temporal queries work correctly
- [ ] Check group_id isolation is preserved

### Sample Verification Queries

```python
# Count verification
source_counts = await source_driver.execute_query("""
    MATCH (n) RETURN labels(n)[0] as label, count(n) as count
""")
target_counts = await target_driver.execute_query("""
    MATCH (n) RETURN labels(n)[0] as label, count(n) as count
""")

# Vector search test
test_results = await target_graphiti.search(
    query="test search query",
    group_ids=["migrated_group"],
    num_results=5
)
assert len(test_results) > 0, "Vector search failed"

# Fulltext search test
fulltext_results = await target_driver.execute_query("""
    CALL db.index.fulltext.queryNodes("node_name_and_summary", "test", {limit: 5})
    YIELD node RETURN node.name
""")
assert len(fulltext_results) > 0, "Fulltext search failed"
```

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Vector dimension mismatch | Medium | High | Verify embedder config before migration |
| Entity extraction drift | High | Medium | Accept or use CRUD to patch critical entities |
| Temporal data loss | Low | Medium | Carefully transform datetime formats |
| group_id mismatch | Medium | High | Explicitly set group_id during import |
| Index creation failure | Low | Medium | Run schema setup before data import |
| Query compatibility | High | High | Review all application queries post-migration |

---

## Recommendations

### For Neo4j → FalkorDB

1. **Use FalkorDB's official migration tool** as a starting point
2. **Add vector handling** - ensure embeddings are imported with `vecf32()`
3. **Convert temporal types** to UNIX epoch microseconds
4. **Test thoroughly** before production migration

### For FalkorDB → Neo4j

1. **Re-ingest episodes** (recommended) for clean migration
2. **If direct copy needed:**
   - Export vectors as standard arrays
   - Rebuild Neo4j-specific vector indexes
   - Convert temporal data to ISO strings or native datetime
3. **Review and update all queries** that use FalkorDB-specific syntax

### For Both Directions

1. **Always backup first** using database-native tools
2. **Test on staging** before production
3. **Accept semantic drift** if using episode re-ingestion
4. **Document the migration** for audit and rollback purposes

---

## Upstream Feature Requests

Consider filing these with Zep/Graphiti:

1. **Official Migration CLI Tool**
   - `graphiti migrate --source neo4j --target falkordb`
   - Handle vector format conversion automatically

2. **Export/Import API**
   - `graphiti.export_graph(format='portable')`
   - `graphiti.import_graph(data, preserve_uuids=True)`

3. **Driver-Agnostic Vector Handling**
   - Abstract vector storage format at the driver level
   - Automatic conversion during cross-backend operations

---

## Verification Summary

| Source | Tool Used | Key Finding |
|--------|-----------|-------------|
| getzep/graphiti driver code | Context7 MCP | Driver architecture, vector query differences |
| Zep documentation | qdrant-docs MCP | CRUD operations, driver initialization |
| FalkorDB migration repo | GitHub MCP | Official Neo4j→FalkorDB tool exists |
| FalkorDB docs | Brave search | vecf32() requirement, temporal limitations |
| Neo4j docs | Brave search | Vector index syntax, APOC export |
| graph_queries.py source | GitHub MCP | Index creation differences per backend |

**Last Verified:** 2025-12-09 via Context7 MCP, GitHub MCP, Brave Search

---

*Research completed: 2025-12-09*
*Tools used: Context7 MCP (graphiti source), qdrant-docs MCP (Zep docs), MCP_DOCKER:search_code, MCP_DOCKER:get_file_contents, brave_web_search*
