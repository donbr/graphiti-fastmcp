Run the Day 1 verification sequence to confirm the environment is working.

## Instructions

Execute these three checks in order. Report results but do NOT attempt fixes without user approval.

### Check 1: Server Health
```python
mcp__graphiti-local__get_status()
```
**Expected:** Status OK with database connection confirmed.

### Check 2: Query Available Groups
```python
mcp__docker__read_neo4j_cypher(
    query="MATCH (e:Episodic) RETURN DISTINCT e.group_id AS group_id, count(*) AS episodes ORDER BY episodes DESC"
)
```
**Expected:** List of group_ids with episode counts. Primary groups are `graphiti_meta_knowledge` and `graphiti_reference_docs`.

### Check 3: Test Semantic Search
```python
mcp__graphiti-local__search_nodes(
    query="graphiti best practices",
    group_ids=["graphiti_meta_knowledge"],
    max_nodes=5
)
```
**Expected:** Returns relevant entity nodes.

## After Running

Report your findings to the user:
- ✅ All checks passed - environment is healthy
- ⚠️ Some checks failed - describe what you found, ASK before fixing
- ❌ Connection errors - report error, do NOT attempt destructive fixes

## Remember

- Empty results usually mean wrong `group_ids` parameter, NOT a broken system
- NEVER run `clear_graph` or delete commands without explicit user request
- When in doubt, ASK THE USER
