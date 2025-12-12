# Active Tasks

**Last Updated:** 2025-12-11
**Current Phase:** Implementation

---

## Key Insight (Preserve This)

> Tonight's entire debugging session happened because of ONE missing instruction:
> **always specify group_ids**. The system was never broken. The docs were incomplete.
>
> **Parsimony means:** Say only what's necessary, but say it clearly and completely.

---

## Completed This Session (2025-12-11)

- [x] Diagnosed group_id namespace issue (empty results ≠ broken)
- [x] Configured all three Neo4j MCP tiers
  - Tier 1: Graphiti MCP (semantic) - was already working
  - Tier 2: neo4j-cypher (queries) - configured with database credentials
  - Tier 3: neo4j-cloud-aura-api (management) - configured with Aura API credentials
- [x] Created Cypher query toolkit (`scripts/cypher/`)
- [x] Added session learnings to knowledge graph
- [x] Created docs/ directory structure

---

## Current Tasks

### Phase 1: Safe Documentation Structure
- [x] Create docs/ directory and move QUICKSTART.md
- [x] Create docs/TASKS.md (this file)
- [ ] Create docs/TROUBLESHOOTING.md with calm decision tree
- [ ] Create .claude/commands/verify.md slash command
- [ ] Update CLAUDE.md to be a router (minimal, stable references only)

### Phase 2: Remove Landmines from QUICKSTART.md
- [ ] Remove hardcoded episode counts (65, 10) - replace with "query live"
- [ ] Add Day 1 verification section at very top
- [ ] Add explicit guardrails section with DO NOT list
- [ ] Ensure all code examples include group_ids parameter

### Phase 3: Knowledge Graph Hygiene
- [ ] Update entry point episode to be minimal and stable
- [ ] Review episodes for panic-inducing language
- [ ] Ensure no episode contains stale counts

### Phase 4: Test with Fresh Eyes
- [ ] Read QUICKSTART.md as new Claude - any panic triggers?
- [ ] Run /verify command
- [ ] Confirm: "Would a new Claude try to fix something that isn't broken?"

---

## Environment Status (Query Live, Don't Hardcode)

To get current stats, run:
```python
mcp__graphiti-local__get_status()
mcp__docker__get_instance_details(instance_ids=["cd339b4f"])
mcp__docker__read_neo4j_cypher(query="MATCH (e:Episodic) RETURN e.group_id, count(*) ORDER BY count(*) DESC")
```

---

## Three-Tier MCP Architecture (Stable Reference)

| Tier | MCP Server | Use For |
|------|------------|---------|
| 1. Semantic | `graphiti-local` | Memory operations, search, add episodes |
| 2. Query | `neo4j-cypher` | Direct Cypher queries, data quality audits |
| 3. Management | `neo4j-cloud-aura-api` | Pause/resume instance, scaling |

---

## Files Modified This Session

- `docs/QUICKSTART.md` (moved from root)
- `docs/TASKS.md` (new)
- `scripts/cypher/*.cypher` (new - 5 query files + README)
- Knowledge graph: 3 new episodes added to `graphiti_meta_knowledge`
