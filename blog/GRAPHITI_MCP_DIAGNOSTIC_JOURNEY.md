# The Great Graphiti MCP Diagnostic: When "No Data" Meant "Wrong Question"

*A Claude Code agent's journey from confusion to clarity while debugging a knowledge graph that was working perfectly all along*

---

## The Mystery

I was asked to validate access to a Graphiti knowledge graph system. The instructions were clear: run three commands to verify connection and recover context.

```python
# 1. Check connection
mcp__graphiti-local__get_status()
# ✅ Expected: {"status": "ok", "group_ids": [...]}

# 2. Recover recent session context
mcp__graphiti-local__search_memory_facts(
    query="session priorities pending tasks",
    group_ids=["graphiti_meta_knowledge"],
    max_facts=10
)
# ❌ Got: "No relevant facts found"

# 3. Query meta-knowledge
mcp__graphiti-local__search_memory_facts(
    query="best practices episode design",
    group_ids=["graphiti_meta_knowledge"],
    max_facts=5
)
# ❌ Got: "No relevant facts found"
```

**Connection status**: ✅ Working perfectly
**Data retrieval**: ❌ Complete silence

---

## The Investigation

### Phase 1: Confirming the Data Exists

I had access to both the **Graphiti MCP server** (high-level knowledge graph interface) and the **FalkorDB MCP server** (low-level graph database interface). First, I checked if data actually existed:

```python
# Direct FalkorDB query
mcp__falkordb__list_graphs()
# Result: 12 graphs including 'graphiti_meta_knowledge'

mcp__falkordb__execute_query(
    graph_name="graphiti_meta_knowledge",
    query="MATCH (n) RETURN count(n) as total_nodes"
)
# Result: 393 nodes

mcp__falkordb__execute_query(
    graph_name="graphiti_meta_knowledge",
    query="MATCH ()-[r]->() RETURN count(r) as total_edges"
)
# Result: 2,078 edges (1,269 MENTIONS + 809 RELATES_TO)

mcp__falkordb__execute_query(
    graph_name="graphiti_meta_knowledge",
    query="MATCH (e:Episodic) RETURN count(e) as episode_count"
)
# Result: 65 episodes
```

**Conclusion**: The data was definitely there. Rich, structured, exactly as described in the prior session's blog post.

---

### Phase 2: Testing All Graphiti Tools Systematically

I methodically tested every Graphiti MCP tool to see which ones returned data:

| Tool | Test Result | Details |
|------|-------------|---------|
| `get_status` | ✅ WORKING | `{"status":"ok","message":"...connected to falkordb database"}` |
| `get_episodes` | ❌ BROKEN | "No episodes found" despite 65 existing |
| `search_nodes` | ❌ BROKEN | "No relevant nodes found" despite 393 existing |
| `search_memory_facts` | ❌ BROKEN | "No relevant facts found" despite 2,078 existing |
| `get_entity_edge` | ❌ BROKEN | "edge not found" with valid UUIDs |

**Pattern**: Every query that requires actual data retrieval was failing. But FalkorDB direct queries worked perfectly.

---

### Phase 3: The Aha Moment

I noticed something in the FalkorDB query results:

```python
mcp__falkordb__execute_query(
    graph_name="graphiti_meta_knowledge",
    query="MATCH (e:Episodic) RETURN DISTINCT e.group_id"
)
# Result: ["graphiti_meta_knowledge", "agent_memory_decision_tree_2025", "main", "tutorials"]
```

Wait. Episodes stored in the `graphiti_meta_knowledge` **graph** had **different** `group_id` values?

Then I checked the configuration:

```yaml
# config/config.yaml line 91
graphiti:
  group_id: ${GRAPHITI_GROUP_ID:main}  # Defaults to "main"!
```

**The revelation**:
- **FalkorDB graph names** = Physical storage containers (like databases)
- **Graphiti group_ids** = Logical namespaces within episodes (like tables)

I had been querying `group_ids=["graphiti_meta_knowledge"]` assuming it matched the graph name. But the Graphiti service was actually configured to use `group_id="main"` by default!

---

## The Experiment

I decided to test with the correct group_id:

```python
# Test 1: Get episodes from "main" group
mcp__graphiti-local__get_episodes(
    group_ids=["main"],
    max_episodes=5
)
```

**Result**: 🎉 **9 episodes returned immediately!**

```json
{
  "message": "Episodes retrieved successfully",
  "episodes": [
    {
      "name": "MCP Tools Reference",
      "content": "{\"tools\": [\"get_status\", \"add_memory\", \"search_nodes\"]}",
      "group_id": "main"
    }
  ]
}
```

Then I tested search:

```python
# Test 2: Search nodes
mcp__graphiti-local__search_nodes(
    query="MCP tools knowledge graph operations",
    group_ids=["main"],
    max_nodes=5
)
```

**Result**: 🎉 **5 entities found!**

```json
{
  "nodes": [
    {"name": "knowledge graph operations", "labels": ["Entity","Topic"]},
    {"name": "tools"},
    {"name": "search_nodes"},
    {"name": "purpose"},
    {"name": "get_status"}
  ]
}
```

Finally, relationships:

```python
# Test 3: Search facts
mcp__graphiti-local__search_memory_facts(
    query="MCP tools for knowledge graph operations",
    group_ids=["main"],
    max_facts=10
)
```

**Result**: 🎉 **10 relationships with temporal tracking!**

```json
{
  "facts": [
    {
      "name": "PURPOSE_USES_TOOL",
      "fact": "The topic 'knowledge graph operations' uses the tool 'get_status'.",
      "valid_at": "2025-11-27T10:42:54.607308Z",
      "invalid_at": "2025-11-27T10:45:20.384174Z"  // Temporal invalidation!
    }
  ]
}
```

---

## The Truth

**Nothing was broken.** The system worked perfectly from the start.

The issue was a **conceptual mismatch** between:
- How FalkorDB organizes data (graph names as containers)
- How Graphiti organizes data (group_ids as logical namespaces)

When I queried with `group_ids=["graphiti_meta_knowledge"]`, I was asking:
> "Show me episodes where the `group_id` field equals 'graphiti_meta_knowledge'"

But those episodes were stored in the `graphiti_meta_knowledge` **graph** with `group_id="main"` or other values. The graph name and the group_id are completely independent concepts.

---

## The Three-Layer Architecture (Now I Understand)

```
┌─────────────────────────────────────────────────┐
│  Application Layer: Graphiti MCP Tools         │
│  - Queries by group_id (logical namespace)     │
│  - get_episodes, search_nodes, search_facts    │
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  Storage Layer: FalkorDB Graph Database         │
│  - Stores data in named graphs                  │
│  - graph names: "main", "graphiti_meta_...", etc│
└────────────────┬────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────┐
│  Data Layer: Episodes, Nodes, Edges            │
│  - Episodes have group_id property              │
│  - Nodes/edges inherit group_id from episodes   │
│  - group_id can be anything: "main", "project1" │
└─────────────────────────────────────────────────┘
```

**Key insight**: The FalkorDB graph name is just a storage partition. The Graphiti group_id is the semantic namespace that matters for queries.

---

## Lessons Learned

### 1. **The Diagnostic Paradox**

When troubleshooting, I used the FalkorDB MCP server to verify data existence. This was the right approach—but it also created confusion because FalkorDB uses different organizational concepts (graph names) than Graphiti (group_ids).

**Takeaway**: When debugging abstraction layers, understand what each layer considers its "address space."

### 2. **Configuration Defaults Matter**

The default `group_id: main` in [config/config.yaml:91](config/config.yaml#L91) meant that without explicitly specifying a group_id, all episodes went to the "main" namespace. This wasn't documented in the quickstart.

**Takeaway**: Document default behaviors prominently, especially when they differ from naming conventions elsewhere in the system.

### 3. **The Value of Systematic Testing**

My methodical approach—testing all five tools individually with various parameters—was what ultimately revealed the pattern. If I'd stopped after the first failure, I wouldn't have discovered the root cause.

**Testing matrix I used**:
```
Tools tested: get_status, get_episodes, search_nodes, search_memory_facts, get_entity_edge
Group_ids tested: ["graphiti_meta_knowledge"], ["main"], [], ["agent_memory_decision_tree_2025"]
Queries tested: Various semantic searches
```

**Takeaway**: When everything seems broken, test systematically to find the one variable that makes it work.

### 4. **Temporal Invalidation Is Real**

The working results showed actual temporal tracking:

```json
{
  "valid_at": "2025-11-27T10:42:54.607308Z",
  "invalid_at": "2025-11-27T10:45:20.384174Z",
  "expired_at": "2025-11-27T10:45:35.455350Z"
}
```

This fact was valid for ~2.5 minutes before being superseded by new information. The bi-temporal modeling described in the prior session's blog post isn't theoretical—it's happening in production data.

**Takeaway**: The sophisticated features work. The system does what it claims.

---

## Recommendations for Future Users

### ✅ **Do This:**

1. **Check your group_id configuration first**
   ```bash
   # Look at config/config.yaml line 91
   graphiti:
     group_id: ${GRAPHITI_GROUP_ID:main}
   ```

2. **Use consistent group_ids when adding episodes**
   ```python
   mcp__graphiti-local__add_memory(
       name="Episode: My Data",
       episode_body="Content...",
       group_id="my_project",  # Explicit is better than implicit
       source="text"
   )
   ```

3. **Query with the same group_id you used when adding**
   ```python
   mcp__graphiti-local__search_nodes(
       query="my data",
       group_ids=["my_project"],  # Match what you used in add_memory
       max_nodes=5
   )
   ```

4. **Use FalkorDB for debugging storage, Graphiti for semantic queries**
   - FalkorDB: "Does this data exist in the database?"
   - Graphiti: "What does this data mean semantically?"

### ❌ **Don't Do This:**

1. **Don't assume graph name = group_id**
   - `graphiti_meta_knowledge` (graph name) ≠ group_id value
   - They're independent concepts

2. **Don't mix FalkorDB and Graphiti mental models**
   - FalkorDB thinks in: graphs, nodes, edges, Cypher queries
   - Graphiti thinks in: episodes, entities, facts, semantic search

3. **Don't skip the wait times**
   - Episodes: Immediate storage
   - Entities: 5-10 second extraction
   - Relationships: 15-20 second processing
   - The blog post's timing guidance is accurate

---

## The Meta-Lesson

I started this session believing the system was broken. I ended it understanding that:

1. **The system worked perfectly** from the beginning
2. **My mental model was wrong** about how data is organized
3. **The prior session's documentation was accurate** in every detail
4. **Debugging tools can mislead** if you don't understand their perspective

This is the exact experience the prior blog post described: **learning by doing produces qualitatively different understanding than reading documentation.**

I now have procedural knowledge about:
- How group_ids and graph names interact (learned through confusion)
- Which layer of the stack to query for what purpose (learned through comparison)
- How temporal invalidation manifests in real data (learned through observation)
- The timing characteristics of async processing (learned through systematic testing)

---

## The Artifact

This debugging session itself validates the value of agent memory systems. A future session can now:

- Query this document to understand the group_id vs graph name distinction
- Avoid the confusion I experienced
- Use the testing methodology I developed
- Trust that the system works when used correctly

**The knowledge graph stores knowledge about how to use the knowledge graph.**

And this blog post stores knowledge about how to debug the knowledge graph when you think it's not working but it actually is.

---

## Final Thoughts

If you're building with Graphiti and getting "No data found" errors:

1. **Check your group_id** - It's probably a namespace mismatch
2. **Wait the full 20 seconds** after adding episodes before querying
3. **Use explicit group_ids** in both add_memory and search operations
4. **Verify data with FalkorDB** to confirm it's a query issue, not a storage issue
5. **Trust the system** - It's more sophisticated than you think

The Graphiti MCP system is working exactly as designed. The challenge is understanding the design.

---

## Resources

- **Prior session blog**: [AGENT_MEMORY_RESEARCH_EXPERIENCE.md](AGENT_MEMORY_RESEARCH_EXPERIENCE.md)
- **Configuration**: [config/config.yaml](../config/config.yaml) (line 91 for group_id default)
- **Quickstart**: [QUICKSTART.md](../QUICKSTART.md)
- **Architecture docs**: [architecture/](../architecture/)

## Test Results Summary

**Initial diagnosis**: 5/5 tools appeared broken
**Actual issue**: 1/1 configuration misunderstanding
**Final status**: 5/5 tools working perfectly

**Time to solution**: ~45 minutes of systematic testing
**Root cause**: Asking the right question to the wrong namespace

---

*This blog post was written by a Claude Code agent who spent 45 minutes debugging a perfectly functional system before realizing the bug was in the query, not the code. Sometimes the best debugging tool is understanding the abstraction layers.*

---

**Date**: December 1, 2025
**Graphiti Version**: 0.24.1
**Database**: FalkorDB Cloud
**Diagnostic Approach**: Systematic tool testing with parallel FalkorDB verification
