# Troubleshooting Guide

**Purpose:** Calm, diagnostic guidance for common issues. Empty results ≠ broken system.

---

## Before You Panic

Most "problems" are actually just missing parameters or wrong namespaces. Follow this decision tree before assuming anything is broken.

---

## Decision Tree: Empty Results

```
Got empty results from Graphiti query?
│
├─ Did you specify group_ids parameter?
│  ├─ NO → Add group_ids=["graphiti_meta_knowledge"] and retry
│  └─ YES → Continue below
│
├─ Is the group_id correct?
│  ├─ Query available groups:
│  │  mcp__docker__read_neo4j_cypher(
│  │      query="MATCH (e:Episodic) RETURN DISTINCT e.group_id, count(*)"
│  │  )
│  └─ Use one of the returned group_ids
│
├─ Did you just add an episode?
│  ├─ YES → Wait 15-20 seconds, then query again
│  │        (Async processing: entities 5-10s, relationships 15-20s)
│  └─ NO → Continue below
│
├─ Is the server running?
│  └─ mcp__graphiti-local__get_status()
│     ├─ Returns OK → Server is fine, check query parameters
│     └─ Returns error → Check server logs, restart if needed
│
└─ Still empty after all checks?
   └─ ASK THE USER before taking any action
      "I'm seeing empty results for group_id X after checking parameters.
       Should I investigate further or is this expected?"
```

---

## Decision Tree: MCP Tool Errors

```
Got an error from MCP tool?
│
├─ "Unauthorized" or "401" error?
│  ├─ neo4j-cypher → Database credentials not configured
│  ├─ neo4j-cloud-aura-api → Aura API credentials not configured
│  └─ Action: Inform user, don't try to fix credentials yourself
│
├─ "Connection refused" or timeout?
│  ├─ Check if server is running: mcp__graphiti-local__get_status()
│  ├─ Check Neo4j instance status: mcp__docker__list_instances()
│  └─ If instance is paused: Ask user if they want to resume it
│
└─ Other error?
   └─ Report the exact error message to user
      Do NOT attempt to "fix" by deleting or clearing data
```

---

## ⛔ NEVER Do These (Without Explicit User Request)

| Action | Why It's Dangerous | What To Do Instead |
|--------|-------------------|-------------------|
| `clear_graph` | Permanently deletes ALL data | Ask user first |
| `delete_episode` | Irreversible data loss | Ask user first |
| `delete_entity_edge` | Removes relationships | Ask user first |
| Assume empty = broken | Usually wrong group_id | Check parameters |
| "Fix" without asking | Might delete valid data | Report findings, ask |

---

## Common Scenarios

### Scenario 1: "No episodes found"

**Don't panic.** This usually means:
1. Wrong `group_id` parameter
2. Querying default `main` namespace (which is empty)
3. No data has been added yet (valid state)

**Solution:**
```python
# Check what groups exist
mcp__docker__read_neo4j_cypher(
    query="MATCH (e:Episodic) RETURN DISTINCT e.group_id AS group, count(*) AS count"
)
```

### Scenario 2: "Search returns nothing"

**Don't panic.** This usually means:
1. Query terms don't match any entities
2. Wrong `group_ids` parameter
3. Data was just added and still processing

**Solution:**
```python
# Broaden the search
mcp__graphiti-local__search_nodes(
    query="*",  # or very broad term
    group_ids=["graphiti_meta_knowledge"],
    max_nodes=20
)
```

### Scenario 3: "Neo4j connection error"

**Don't panic.** Check instance status:
```python
# Check if instance is running
mcp__docker__list_instances()
# Look for status: "running" vs "paused"
```

If paused, ask user: "Your Neo4j instance appears to be paused. Would you like me to resume it?"

### Scenario 4: "Missing embeddings" in data quality check

**Don't panic.** This means entities won't appear in search results.

**Solution:**
1. Report the affected entities to user
2. Ask if they want to re-ingest the source episodes
3. Do NOT delete the entities

---

## The Golden Rule

> **When in doubt, ASK THE USER.**
>
> It's always better to report what you found and ask for guidance
> than to attempt a "fix" that might delete valid data.

---

## Quick Diagnostic Commands

```python
# 1. Check server health
mcp__graphiti-local__get_status()

# 2. Check Neo4j instance
mcp__docker__list_instances()

# 3. Check available groups
mcp__docker__read_neo4j_cypher(
    query="MATCH (e:Episodic) RETURN DISTINCT e.group_id, count(*) ORDER BY count(*) DESC"
)

# 4. Check data quality
mcp__docker__read_neo4j_cypher(
    query="MATCH (n:Entity) RETURN count(n) AS entities, sum(CASE WHEN n.name_embedding IS NULL THEN 1 ELSE 0 END) AS missing_embeddings"
)
```
