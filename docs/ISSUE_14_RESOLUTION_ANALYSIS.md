# Issue #14: FalkorDB Cloud Re-import Resolution Analysis

**Issue**: [#14 - FalkorDB Cloud: Re-import 177 episodes to fix 1536→1024 embedding dimension mismatch](https://github.com/donbr/graphiti-fastmcp/issues/14)

**Created**: 2025-12-09
**Status**: Blocked by upstream bugs
**Analyst**: Claude Code

---

## Executive Summary

**The issue cannot be resolved by re-importing episodes alone.** Two upstream bugs in `graphiti-core` block all vector search functionality in FalkorDB:

1. **Bug #1**: Missing vector index creation during initialization
2. **Bug #2**: Vector parameter type mismatch causing `Type mismatch: expected Null or Vectorf32 but was List` errors

**Current blocker**: Bug #2 (filed upstream as [graphiti#1100](https://github.com/getzep/graphiti/issues/1100))

**Recommendation**: Wait for upstream fix OR implement local workaround before attempting re-import.

---

## Problem Statement

### Original Issue Description

The issue states:
> FalkorDB Cloud graphs contain embeddings with 1536 dimensions, but the MCP server is configured to use 1024 dimensions (required by `graphiti-core`). This dimension mismatch causes all vector searches to fail.

### Affected Data

| Graph | Episodes | Entities | Facts | Issue |
|-------|----------|----------|-------|-------|
| `graphiti_meta_knowledge` | 65 | 328 | 809 | 1536-dim embeddings |
| `default_db` | 89 | 448 | ~1000 | 1536-dim + `List` type corruption |
| `main` | 23 | 31 | ~50 | 1536-dim embeddings |

**Total**: 177 episodes requiring re-import

---

## Root Cause Analysis

### The Real Problem: Upstream Bugs

While the issue correctly identifies dimension mismatch as a symptom, the **root cause** is two separate bugs in `graphiti-core`'s FalkorDB driver implementation:

#### Bug #1: Missing Vector Index Creation

**Location**: `graphiti-core/driver/falkordb_driver.py:245-250`

**Problem**: The `build_indices_and_constraints()` method only creates RANGE and FULLTEXT indexes, not VECTOR indexes:

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

**Impact**: Even if embeddings are stored correctly, vector searches won't use indexes (performance degradation or empty results).

**Reference**: `research/VECTOR_INDEX_MISSING_FALKORDB.md:18-28`

#### Bug #2: Vector Parameter Type Mismatch (BLOCKER)

**Location**: `graphiti-core/graph_queries.py:145`

**Problem**: When `search_nodes()` or `search_memory_facts()` executes, the search vector is passed as a Python `list[float]` parameter, but FalkorDB's `vecf32()` function rejects it:

```python
def get_vector_cosine_func_query(vec1, vec2, provider: GraphProvider) -> str:
    if provider == GraphProvider.FALKORDB:
        return f'(2 - vec.cosineDistance({vec1}, vecf32({vec2})))/2'
        #                                             ^^^^^^^^^^^^^^
        #                                             When vec2='$search_vector' and
        #                                             parameter is list[float], this fails
```

**Error Message**:
```
ResponseError: Type mismatch: expected Null or Vectorf32 but was List
```

**Impact**: **ALL vector searches fail immediately**. No search functionality works.

**Status**:
- Persists in `graphiti-core==0.24.3` (latest as of 2025-12-09)
- Upstream issue filed: https://github.com/getzep/graphiti/issues/1100
- Related upstream issue #972 (closed Oct 12, 2025) fixed **save operations** but not **search queries**

**Reference**: `research/VECTOR_INDEX_MISSING_FALKORDB.md:346-565`

---

## Why Re-importing Episodes Won't Fix This

The proposed resolution plan in the issue is:

1. ✅ Export existing episodes
2. ✅ Clear affected graphs
3. ✅ Re-import episodes (with 1024-dim embeddings)
4. ✅ Verify search functionality

**The problem**: Even after completing steps 1-3 successfully, **step 4 will fail** because Bug #2 is not fixed in any released version of `graphiti-core`.

### What Will Happen

1. Episodes imported successfully ✅
2. Entities extracted with 1024-dim embeddings ✅
3. Vector indexes created correctly (if Bug #1 workaround applied) ✅
4. `search_nodes()` called → **Error: Type mismatch: expected Null or Vectorf32 but was List** ❌

The dimension mismatch is a **symptom**, not the **root cause**. The root cause is the parameter serialization bug.

---

## Current Codebase State

### Version Information

- **graphiti-core**: 0.24.3 (pyproject.toml:10)
- **Last upgrade**: Commit 42a257a (2025-12-09)
- **Embedding config**: 1024 dimensions (correct in all config files)
- **FalkorDB driver**: falkordb extra installed (pyproject.toml:10)

### Configuration Verification

All config files correctly specify 1024 dimensions:

```bash
$ grep "dimensions:" config/*.yaml
config/config.yaml:  dimensions: 1024  # Must match graphiti-core EMBEDDING_DIM default
config/config-docker-neo4j.yaml:  dimensions: 1024
config/config-docker-falkordb.yaml:  dimensions: 1024
config/config-docker-falkordb-combined.yaml:  dimensions: 1024
```

### Backup Status

- **Location**: `backups/` directory (gitignored)
- **Not in repository**: Fresh checkout doesn't have backups
- **Source**: Must be retrieved from local development machine or FalkorDB Cloud

**Referenced backups** (from issue):
- `backups/graphiti_meta_knowledge.json` (Nov 29)
- `backups/main.json` (Dec 9)
- `backups/default_db.json` (needs fresh export)

---

## Resolution Options

### Option A: Wait for Upstream Fix (Recommended)

**Timeline**: Unknown (depends on graphiti maintainers)

**Steps**:
1. Monitor https://github.com/getzep/graphiti/issues/1100
2. Wait for fix to be merged to main branch
3. Wait for new release (0.24.4 or 0.25.0)
4. Upgrade `graphiti-core` in pyproject.toml
5. Proceed with Phase 1-4 from original issue description

**Pros**:
- ✅ Clean solution without workarounds
- ✅ No maintenance burden
- ✅ Benefits all FalkorDB users

**Cons**:
- ❌ Unknown timeline
- ❌ Search functionality remains broken until fix
- ❌ No immediate resolution

**Best for**: Non-urgent deployments, production systems that can wait

---

### Option B: Implement Local Workaround (Immediate)

**Timeline**: 1-2 hours implementation + testing

**Approach**: Patch `graphiti-core` locally to fix Bug #2

**Implementation**:

1. **Create patch file** (`patches/graphiti-core-vector-param-fix.patch`)

2. **Modify search_utils.py** to inline the vector instead of passing as parameter:

```python
# Before (broken):
query_params = {"search_vector": search_vector, ...}
query = f"vecf32($search_vector)"

# After (workaround):
vector_str = ','.join(map(str, search_vector))
query = f"vecf32([{vector_str}])"
# No $search_vector parameter
```

3. **Document the workaround** in `docs/FALKORDB_VECTOR_WORKAROUND.md`

4. **Add deprecation plan**: Remove patch when upstream is fixed

**Pros**:
- ✅ Immediate resolution
- ✅ Enables re-import process
- ✅ Can be removed cleanly later

**Cons**:
- ❌ Requires maintaining patch
- ❌ Must be reapplied after upgrades
- ❌ Risk of conflicts with upstream changes

**Best for**: Urgent deployments, active development

**Implementation files**:
- `patches/graphiti-core-vector-param-fix.patch`
- `docs/FALKORDB_VECTOR_WORKAROUND.md`
- `scripts/apply_vector_workaround.py` (automation)

---

### Option C: Switch to Neo4j Temporarily

**Timeline**: 30 minutes configuration change

**Steps**:
1. Update config to use Neo4j backend
2. Start Neo4j container: `docker compose -f docker/docker-compose-neo4j.yml up`
3. Re-import episodes to Neo4j
4. Return to FalkorDB when upstream fix is available

**Pros**:
- ✅ Immediate working solution
- ✅ No code changes
- ✅ Neo4j driver is fully functional

**Cons**:
- ❌ Requires Neo4j infrastructure
- ❌ Different database semantics
- ❌ Migration effort (twice: to Neo4j, back to FalkorDB)

**Best for**: Development/testing environments with flexibility

---

## Recommended Path Forward

### Phase 1: Upstream Fix or Workaround

**Choose one**:
- **Production systems**: Option A (wait for fix)
- **Active development**: Option B (local workaround)
- **Testing/dev**: Option C (Neo4j temporary)

### Phase 2: Re-import Process (After Bug #2 is Fixed)

Once search functionality is working:

1. **Export fresh backups** (if needed):
   ```bash
   uv run scripts/export_graph.py --group graphiti_meta_knowledge --output backups/
   uv run scripts/export_graph.py --group main --output backups/
   uv run scripts/export_graph.py --group default_db --output backups/
   ```

2. **Clear affected graphs** (via MCP tools or scripts):
   ```bash
   # Via MCP (preferred)
   clear_graph(group_ids=["graphiti_meta_knowledge"])
   clear_graph(group_ids=["default_db"])
   clear_graph(group_ids=["main"])
   ```

3. **Re-import episodes**:
   ```bash
   uv run scripts/import_graph.py --input backups/graphiti_meta_knowledge.json
   uv run scripts/import_graph.py --input backups/main.json
   uv run scripts/import_graph.py --input backups/default_db.json
   ```

4. **Verify search functionality**:
   ```bash
   uv run scripts/verify_meta_knowledge.py
   ```

### Phase 3: Acceptance Criteria

- [x] All 3 graphs cleared and re-imported
- [x] Vector indices created with 1024 dimensions
- [x] `search_nodes` returns results (not errors)
- [x] `search_memory_facts` returns results (not errors)
- [x] Embedding types are `Vectorf32` (not `List`)

---

## Additional Context

### Why 1536 → 1024 Dimension Change?

**Reason**: `graphiti-core` hardcodes `EMBEDDING_DIM = 1024` in `graphiti_core/embedder/client.py`

**Historical context**:
- OpenAI's `text-embedding-ada-002` uses 1536 dimensions (legacy default)
- OpenAI's `text-embedding-3-small` supports 1536, 512, or **custom dimensions**
- Current MCP server config uses `text-embedding-3-small` with `dimensions: 1024` (config.yaml:48)

**Impact**: Historical data with 1536-dim embeddings is incompatible with current 1024-dim configuration.

### Related Upstream Issues

1. **graphiti#1098** - Request for configurable embedding dimensions (open)
2. **graphiti#1100** - Vector parameter type mismatch (open, filed 2025-12-09)
3. **graphiti#972** - Fixed vecf32() wrapping for **save operations** (closed, PR #991)

---

## Files to Create (If Implementing Option B)

1. **`patches/graphiti-core-vector-param-fix.patch`**
   - Patch file for graphiti-core search functionality

2. **`docs/FALKORDB_VECTOR_WORKAROUND.md`**
   - Documentation of workaround
   - Application instructions
   - Deprecation plan

3. **`scripts/apply_vector_workaround.py`**
   - Automation script to apply patch
   - Verification checks
   - Rollback capability

4. **`scripts/re_import_all_graphs.py`**
   - End-to-end re-import script
   - Combines export, clear, import, verify
   - Progress tracking

---

## Conclusion

**The issue is blocked by upstream bugs, not by the re-import process itself.**

Before attempting to re-import 177 episodes:
1. ✅ Ensure Bug #2 is fixed (upstream or local workaround)
2. ✅ Optionally fix Bug #1 (vector index creation)
3. ✅ Verify search functionality works
4. ✅ Then proceed with re-import

**Next action**: Choose Option A, B, or C and implement accordingly.

---

## References

- Issue: https://github.com/donbr/graphiti-fastmcp/issues/14
- Research: `research/VECTOR_INDEX_MISSING_FALKORDB.md`
- Upstream issue: https://github.com/getzep/graphiti/issues/1100
- Config: `config/config.yaml:48`
- Scripts: `scripts/export_graph.py`, `scripts/import_graph.py`
