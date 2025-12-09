# Bug Research: FalkorDB Driver Issues in graphiti-core

| Field | Value |
|-------|-------|
| **Library** | `graphiti-core` |
| **Repository** | https://github.com/getzep/graphiti |
| **Affected Version** | 0.24.1 (and likely all versions with FalkorDB support) |
| **Maintainer** | Zep Software, Inc. |
| **Date** | 2025-12-09 |
| **Status** | Two bugs identified - see details below |

---

## Bug Summary

| # | Bug | Location | Status |
|---|-----|----------|--------|
| 1 | Missing vector index creation | `falkordb_driver.py:245-250` | Root cause identified |
| 2 | Vector parameter type mismatch | `graph_queries.py:145` | Root cause identified |

---

# Bug 1: Missing Vector Index Creation

## Problem Summary

The `graphiti-core` Python library's FalkorDB driver does **not** create vector indexes during `build_indices_and_constraints()`, causing all hybrid/similarity searches to return empty results. The Neo4j driver correctly creates these indexes, indicating this is a FalkorDB-specific gap in implementation.

**Affected files in `graphiti-core`:**
- [`graphiti_core/driver/falkordb_driver.py`](https://github.com/getzep/graphiti/blob/main/graphiti_core/driver/falkordb_driver.py) - Lines 245-250
- [`graphiti_core/graph_queries.py`](https://github.com/getzep/graphiti/blob/main/graphiti_core/graph_queries.py) - Missing `get_vector_indices()` for FalkorDB

**Affected functions:**
- `FalkorDriver.build_indices_and_constraints()` - Only calls `get_range_indices()` + `get_fulltext_indices()`
- Missing: `get_vector_indices()` function for `GraphProvider.FALKORDB`

---

## GitHub Issue Search

### Ready-to-Use Search URLs

Click these links to search the `getzep/graphiti` repository:

1. **[Vector index + FalkorDB issues](https://github.com/getzep/graphiti/issues?q=is%3Aissue+falkordb+vector+index)**
   ```
   is:issue falkordb vector index
   ```

2. **[Search returns empty issues](https://github.com/getzep/graphiti/issues?q=is%3Aissue+search+empty+OR+%22no+results%22)**
   ```
   is:issue search empty OR "no results"
   ```

3. **[FalkorDB-related issues (all)](https://github.com/getzep/graphiti/issues?q=is%3Aissue+falkordb)**
   ```
   is:issue falkordb
   ```

4. **[name_embedding or fact_embedding mentions](https://github.com/getzep/graphiti/search?q=name_embedding+OR+fact_embedding&type=issues)**
   ```
   name_embedding OR fact_embedding
   ```

5. **[build_indices issues](https://github.com/getzep/graphiti/issues?q=is%3Aissue+build_indices)**
   ```
   is:issue build_indices
   ```

### Code Search Queries

Search the codebase to understand the implementation:

1. **[Vector index creation in codebase](https://github.com/getzep/graphiti/search?q=CREATE+VECTOR+INDEX&type=code)**
   ```
   CREATE VECTOR INDEX
   ```

2. **[FalkorDB driver file](https://github.com/getzep/graphiti/search?q=path%3Afalkordb_driver.py&type=code)**
   ```
   path:falkordb_driver.py
   ```

3. **[graph_queries.py vector references](https://github.com/getzep/graphiti/search?q=path%3Agraph_queries.py+vector&type=code)**
   ```
   path:graph_queries.py vector
   ```

4. **[Neo4j vector index (for comparison)](https://github.com/getzep/graphiti/search?q=vector.dimensions+OR+similarity_function&type=code)**
   ```
   vector.dimensions OR similarity_function
   ```

### Pull Request Search

Check for recent FalkorDB-related changes:

1. **[FalkorDB PRs](https://github.com/getzep/graphiti/pulls?q=is%3Apr+falkordb)**
   ```
   is:pr falkordb
   ```

2. **[Index-related PRs](https://github.com/getzep/graphiti/pulls?q=is%3Apr+index)**
   ```
   is:pr index
   ```

### Labels to Check

If the repository uses issue labels, look for:
- `bug`
- `falkordb`
- `search`
- `indexing`
- `enhancement`
- `good first issue`

---

## Evidence: Local Verification

### Database State (FalkorDB `default_db` graph)

```
Embeddings Status:
├── Entity nodes total:        448
├── Nodes WITH embeddings:     448 (100%)
├── Nodes WITHOUT embeddings:  0
└── Embedding dimensions:      1024 ✓

Index Status:
├── RANGE indexes:             ✓ Present (uuid, group_id, name, created_at)
├── FULLTEXT indexes:          ✓ Present (name, summary, group_id)
└── VECTOR indexes:            ✗ MISSING (name_embedding not indexed)
```

### Code Analysis

**FalkorDB driver (`falkordb_driver.py:245-250`):**
```python
async def build_indices_and_constraints(self, delete_existing=False):
    if delete_existing:
        await self.delete_all_indexes()
    index_queries = get_range_indices(self.provider) + get_fulltext_indices(self.provider)
    #              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^   ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    #              ✓ Creates RANGE indexes            ✓ Creates FULLTEXT indexes
    #
    #              MISSING: get_vector_indices(self.provider)
    for query in index_queries:
        await self.execute_query(query)
```

**graph_queries.py - Functions present:**
- `get_range_indices(provider)` - Line 28 ✓
- `get_fulltext_indices(provider)` - Line 72 ✓
- `get_vector_indices(provider)` - **DOES NOT EXIST** ✗

**Neo4j vector index creation (exists in examples):**
```sql
CREATE VECTOR INDEX name_embedding IF NOT EXISTS
FOR (n:Entity) ON (n.name_embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 1024, `vector.similarity_function`: 'cosine'}}
```

**Required FalkorDB equivalent (not implemented):**
```sql
CREATE VECTOR INDEX FOR (n:Entity) ON (n.name_embedding)
OPTIONS {dimension:1024, similarityFunction:'cosine'}
```

---

## Bug Report Template

If no existing issue is found, use this template to file a new issue:

### Title
```
[FalkorDB] Missing vector index creation in build_indices_and_constraints()
```

### Body

```markdown
## Description

The FalkorDB driver does not create vector indexes for `name_embedding` (Entity nodes) or `fact_embedding` (RELATES_TO edges) during `build_indices_and_constraints()`. This causes hybrid search methods (`search_nodes`, `search_memory_facts`, `search_`) to return empty results even when embeddings exist on all nodes.

## Environment

- **graphiti-core version**: 0.24.1
- **FalkorDB version**: latest (falkordb/falkordb:latest Docker image)
- **Python version**: 3.10+
- **OS**: Linux (WSL2)

## Steps to Reproduce

1. Initialize Graphiti with FalkorDB driver
2. Call `build_indices_and_constraints()`
3. Add episodes (embeddings are created correctly)
4. Call `search_nodes("any query")` or `search_memory_facts("any query")`

**Expected**: Returns relevant nodes/facts based on similarity
**Actual**: Returns `{"message":"No relevant nodes found","nodes":[]}`

## Root Cause Analysis

### Affected Files
- `graphiti_core/driver/falkordb_driver.py` (lines 245-250)
- `graphiti_core/graph_queries.py` (missing function)

### The Problem

`FalkorDriver.build_indices_and_constraints()` only calls:
```python
index_queries = get_range_indices(self.provider) + get_fulltext_indices(self.provider)
```

There is no `get_vector_indices()` function, and no vector index creation for FalkorDB.

### Evidence

Direct FalkorDB query confirms embeddings exist but no vector index:
```cypher
-- Embeddings exist
MATCH (n:Entity) WHERE n.name_embedding IS NOT NULL RETURN count(n)
-- Returns: 448

-- Check indexes
CALL db.indexes() YIELD label, properties, types WHERE label = 'Entity' RETURN *
-- Returns: uuid, group_id, name, created_at, summary (NO name_embedding)
```

## Proposed Solution

Add `get_vector_indices()` to `graph_queries.py`:

```python
def get_vector_indices(provider: GraphProvider, embedding_dim: int = 1024) -> list[LiteralString]:
    if provider == GraphProvider.FALKORDB:
        return [
            f"CREATE VECTOR INDEX FOR (n:Entity) ON (n.name_embedding) OPTIONS {{dimension:{embedding_dim}, similarityFunction:'cosine'}}",
            f"CREATE VECTOR INDEX FOR ()-[e:RELATES_TO]->() ON (e.fact_embedding) OPTIONS {{dimension:{embedding_dim}, similarityFunction:'cosine'}}",
        ]
    # ... Neo4j and Kuzu implementations
```

Update `FalkorDriver.build_indices_and_constraints()`:
```python
index_queries = (
    get_range_indices(self.provider)
    + get_fulltext_indices(self.provider)
    + get_vector_indices(self.provider)  # ADD THIS
)
```

## Workaround

Manually create vector indexes after initialization:

```python
await driver.execute_query("""
CREATE VECTOR INDEX FOR (n:Entity) ON (n.name_embedding)
OPTIONS {dimension:1024, similarityFunction:'cosine'}
""")
await driver.execute_query("""
CREATE VECTOR INDEX FOR ()-[e:RELATES_TO]->() ON (e.fact_embedding)
OPTIONS {dimension:1024, similarityFunction:'cosine'}
""")
```

## Additional Context

- Neo4j driver correctly creates vector indexes (see examples/ecommerce/runner.ipynb logs)
- FalkorDB vector index syntax documented at: https://docs.falkordb.com/cypher/indexing
- This may have been overlooked when FalkorDB support was added
```

---

## Workaround: Manual Index Creation

Until the upstream fix is merged, create the vector indexes manually:

### Using Cypher (via FalkorDB Browser or redis-cli)

```cypher
-- Entity node vector index
CREATE VECTOR INDEX FOR (n:Entity) ON (n.name_embedding)
OPTIONS {dimension:1024, similarityFunction:'cosine'}

-- RELATES_TO edge vector index
CREATE VECTOR INDEX FOR ()-[e:RELATES_TO]->() ON (e.fact_embedding)
OPTIONS {dimension:1024, similarityFunction:'cosine'}
```

### Using Python

```python
from graphiti_core.driver.falkordb_driver import FalkorDriver

driver = FalkorDriver(host='localhost', port=6379, database='default_db')

# Create missing vector indexes
await driver.execute_query("""
CREATE VECTOR INDEX FOR (n:Entity) ON (n.name_embedding)
OPTIONS {dimension:1024, similarityFunction:'cosine'}
""")

await driver.execute_query("""
CREATE VECTOR INDEX FOR ()-[e:RELATES_TO]->() ON (e.fact_embedding)
OPTIONS {dimension:1024, similarityFunction:'cosine'}
""")
```

### Verify Index Creation

```cypher
CALL db.indexes() YIELD label, properties, types
RETURN label, properties, types
```

Look for `VECTOR` type on `name_embedding` and `fact_embedding`.

---

## References

### graphiti-core Source Code
- [FalkorDB Driver](https://github.com/getzep/graphiti/blob/main/graphiti_core/driver/falkordb_driver.py)
- [Graph Queries](https://github.com/getzep/graphiti/blob/main/graphiti_core/graph_queries.py)
- [Neo4j Driver (for comparison)](https://github.com/getzep/graphiti/blob/main/graphiti_core/driver/neo4j_driver.py)

### FalkorDB Documentation
- [Vector Indexing](https://docs.falkordb.com/cypher/indexing) - CREATE VECTOR INDEX syntax
- [Vector Functions](https://docs.falkordb.com/cypher/functions) - vecf32(), vec.cosineDistance()

### Graphiti Documentation
- [FalkorDB Configuration](https://docs.getzep.com/graphiti/configuration/graph-db-configuration#falkordb)
- [Searching the Graph](https://docs.getzep.com/graphiti/operations/searching)

---

---

# Bug 2: Vector Parameter Type Mismatch

## Problem Summary

When executing vector similarity searches, the FalkorDB driver throws:
```
Type mismatch: expected Null or Vectorf32 but was List
```

This occurs even when vector indexes exist. The root cause is in how the `vecf32()` function handles Python list parameters passed via Cypher query parameters.

**Affected files in `graphiti-core`:**
- [`graphiti_core/graph_queries.py`](https://github.com/getzep/graphiti/blob/main/graphiti_core/graph_queries.py) - Line 145
- [`graphiti_core/search/search_utils.py`](https://github.com/getzep/graphiti/blob/main/graphiti_core/search/search_utils.py) - Lines 335, 407, 421

---

## Evidence: Error Reproduction

### Error Message
```
ResponseError: Type mismatch: expected Null or Vectorf32 but was List
```

### Failing Query Pattern
```cypher
MATCH (n:Entity)
WHERE n.group_id IN $group_ids
WITH n, (2 - vec.cosineDistance(n.name_embedding, vecf32($search_vector)))/2 AS score
WHERE score > 0.5
RETURN n
```

### Root Cause

In `graph_queries.py:145`:
```python
def get_vector_cosine_func_query(vec1, vec2, provider: GraphProvider) -> str:
    if provider == GraphProvider.FALKORDB:
        return f'(2 - vec.cosineDistance({vec1}, vecf32({vec2})))/2'
```

The `$search_vector` parameter is passed as a Python `list[float]` from `search_utils.py:421`:
```python
search_vector=search_vector  # This is a list[float]
```

FalkorDB's `vecf32()` function expects the vector to be serialized differently when passed as a query parameter.

---

## Diagnosis Steps

### 1. Confirmed Error Occurs Locally
Ran local MCP server against FalkorDB Cloud:
```bash
uv run fastmcp dev src/server.py:create_server
```

Error reproduced identically to FastMCP Cloud deployment.

### 2. Verified Code is Identical to Upstream
Compared local `src/server.py` with upstream `getzep/graphiti/mcp_server/server.py`:
- `search_nodes()` - identical
- `search_memory_facts()` - identical

**Conclusion**: Bug is in `graphiti-core`, not our MCP server code.

### 3. Confirmed Embeddings and Data are Valid
```cypher
-- Check entity embeddings exist
MATCH (n:Entity)
RETURN count(n) as total,
       count(n.name_embedding) as with_embedding,
       size(n.name_embedding) as dimensions
-- Returns: 448 total, 448 with embeddings, 1024 dimensions
```

### 4. Identified Root Cause Location
The issue is the interaction between:
1. Python FalkorDB driver parameter serialization
2. FalkorDB's `vecf32()` Cypher function
3. How the query is constructed in `graph_queries.py`

---

## Potential Solutions

### Option A: Inline Vector Serialization
Instead of passing vector as parameter, serialize it inline:
```python
vector_str = ','.join(map(str, search_vector))
query = f"vecf32([{vector_str}])"
```

### Option B: Use array() Constructor
```python
return f'(2 - vec.cosineDistance({vec1}, array({vec2})))/2'
```

### Option C: Pre-convert to Vectorf32
Convert the Python list to a FalkorDB-compatible format before passing:
```python
from falkordb import Vectorf32
search_vector_param = Vectorf32(search_vector)
```

---

## Bug Report Template (Bug 2)

### Title
```
[FalkorDB] vecf32() type mismatch when passing vector as query parameter
```

### Body

```markdown
## Description

When using the FalkorDB driver with vector similarity search, queries fail with:
```
Type mismatch: expected Null or Vectorf32 but was List
```

The issue occurs because `vecf32($search_vector)` in the Cypher query doesn't properly handle Python list parameters.

## Environment

- **graphiti-core version**: 0.24.1
- **FalkorDB version**: latest
- **Python version**: 3.10+

## Steps to Reproduce

1. Initialize Graphiti with FalkorDB driver
2. Add episodes (entities with embeddings are created)
3. Call `search_nodes("any query")`

**Expected**: Returns matching nodes
**Actual**: `ResponseError: Type mismatch: expected Null or Vectorf32 but was List`

## Root Cause

In `graph_queries.py:145`:
```python
return f'(2 - vec.cosineDistance({vec1}, vecf32({vec2})))/2'
```

When `vec2 = '$search_vector'` and the parameter is a Python list, FalkorDB's `vecf32()` function rejects it.

## Proposed Solution

Option 1 - Inline the vector:
```python
def get_vector_cosine_func_query(vec1, vec2_value, provider: GraphProvider) -> str:
    if provider == GraphProvider.FALKORDB:
        if isinstance(vec2_value, list):
            vec2_str = ','.join(map(str, vec2_value))
            return f'(2 - vec.cosineDistance({vec1}, vecf32([{vec2_str}])))/2'
        return f'(2 - vec.cosineDistance({vec1}, vecf32({vec2_value})))/2'
```

Option 2 - Use Vectorf32 type from falkordb package in search_utils.py before passing parameter.
```

---

## Relationship Between Bug 1 and Bug 2

These are **separate issues**:

| Aspect | Bug 1 (Missing Index) | Bug 2 (Type Mismatch) |
|--------|----------------------|----------------------|
| **Symptom** | Empty results | Exception thrown |
| **When occurs** | After index rebuild | During any search |
| **Location** | `falkordb_driver.py` | `graph_queries.py` |
| **Fix complexity** | Add missing function | Change parameter handling |

Bug 2 is currently blocking search functionality. Even if Bug 1 is fixed, Bug 2 will still prevent searches from working.

---

## Investigation Progress (2025-12-09)

### Upstream Issue Search
- **Issue #972** was closed (Oct 12, 2025) - fixed **save operations** wrapping embeddings with `vecf32()`
- **PR #991** fixed entity/edge save queries, NOT search queries
- The search query parameter issue is **not fixed** in the main branch

### Version Testing
- Tested `graphiti-core==0.24.3` (latest as of Dec 8, 2025)
- Error persists: `Type mismatch: expected Null or Vectorf32 but was List`
- Code in `graph_queries.py:145` is unchanged

### Root Cause Confirmed
The fix in PR #991 addressed **inline vector data** in save operations:
```cypher
-- SAVE (fixed): vecf32(node.name_embedding) - works because node.name_embedding is inline data
SET n.name_embedding = vecf32(node.name_embedding)
```

The **search query** passes vectors as **Cypher parameters**, which is not handled:
```cypher
-- SEARCH (broken): vecf32($search_vector) - fails because $search_vector is a Python list parameter
vec.cosineDistance(n.name_embedding, vecf32($search_vector))
```

### Next Steps

1. [x] Search upstream issues for existing reports of Bug 2 - **Not found**
2. [x] Test if `graphiti-core` 0.24.3 has a fix - **Still broken**
3. [x] File upstream issue - **Created: https://github.com/getzep/graphiti/issues/1100**
4. [ ] Implement local workaround while waiting for fix

---

*Research conducted: 2025-12-09 using qdrant-docs MCP (Zep documentation), Context7 MCP (FalkorDB docs, graphiti source), and direct FalkorDB database queries.*
