# Migration Validation Guide

## Overview

This guide explains how to validate the disney_knowledge migration using the validation agent.

## Validation Agent

The validation agent is responsible for verifying migration quality after each group_id completes. It checks:

1. **Episode Count**: Verifies that at least 80% of expected episodes were migrated
2. **Key Entity Discovery**: Confirms key entities can be found via search
3. **Fact Validation**: Tests that relationship queries return sufficient results
4. **Semantic Search**: Validates search quality for relevant queries
5. **Semantic Drift**: Documents any entity merges, splits, or name changes

## Running Validation

### Automated Validation (Recommended)

```bash
# From project root
uv run python migration/validate_disney_knowledge.py
```

The script will:
- Connect to the Graphiti database
- Run all validation checks
- Generate a detailed JSON report
- Output VALIDATION_PASS or VALIDATION_FAIL

### Manual Validation via MCP Tools

If you prefer to validate manually using MCP tools:

#### 1. Episode Count Check

```python
# Using mcp__graphiti-local__get_episodes
get_episodes(
    group_ids=["disney_knowledge"],
    max_episodes=200
)

# Expected: ~80 episodes
# Pass threshold: >= 64 (80% of 80)
```

#### 2. Entity Discovery Check

Search for each key entity:

```python
# Using mcp__graphiti-local__search_nodes
search_nodes(
    query="Disney Studios",
    group_ids=["disney_knowledge"],
    max_nodes=10
)

search_nodes(
    query="OTE",
    group_ids=["disney_knowledge"],
    max_nodes=10
)

search_nodes(
    query="DEEPT",
    group_ids=["disney_knowledge"],
    max_nodes=10
)

search_nodes(
    query="Data Platform Team",
    group_ids=["disney_knowledge"],
    max_nodes=10
)

search_nodes(
    query="Content Genome",
    group_ids=["disney_knowledge"],
    max_nodes=10
)

# Pass requirement: >= 4 of 5 entities found (80%)
```

#### 3. Fact Validation Check

Test relationship queries:

```python
# Using mcp__graphiti-local__search_memory_facts
search_memory_facts(
    query="Disney Content Genome technology",
    group_ids=["disney_knowledge"],
    max_facts=10
)

search_memory_facts(
    query="Disney organizational structure teams",
    group_ids=["disney_knowledge"],
    max_facts=10
)

# Pass requirement: >= 3 facts returned per query
```

#### 4. Semantic Search Quality

```python
# Using mcp__graphiti-local__search_nodes
search_nodes(
    query="Disney data platform and content analysis",
    group_ids=["disney_knowledge"],
    max_nodes=10
)

# Pass requirement: Top 5 results contain Disney-related concepts
```

## Validation Report Format

The validation script generates a JSON report at:
```
migration/progress/validation_disney_knowledge.json
```

### Report Structure

```json
{
  "group_id": "disney_knowledge",
  "validation_time": "2025-12-12T10:30:00Z",
  "episode_validation": {
    "expected": 80,
    "actual": 78,
    "threshold": 64,
    "pass": true
  },
  "entity_validation": {
    "expected": ["Disney Studios", "OTE", "DEEPT", "Data Platform Team", "Content Genome"],
    "found": ["Disney Studios", "OTE", "DEEPT", "Data Platform Team"],
    "missing": ["Content Genome"],
    "found_count": 4,
    "required_count": 4,
    "pass": true
  },
  "fact_validation": {
    "queries_tested": 2,
    "queries_passed": 2,
    "query_results": [
      {
        "query": "Disney Content Genome technology",
        "fact_count": 5,
        "required": 3,
        "pass": true
      },
      {
        "query": "Disney organizational structure teams",
        "fact_count": 4,
        "required": 3,
        "pass": true
      }
    ],
    "pass": true
  },
  "semantic_search": {
    "queries_tested": 1,
    "top_results": ["Disney Studios", "Content Genome", "Data Platform Team"],
    "relevant_count": 3,
    "pass": true
  },
  "semantic_drift": {
    "merged": [],
    "split": [],
    "renamed": []
  },
  "overall_pass": true,
  "warnings": []
}
```

## Pass Criteria

### Episode Count
- Expected: ~80 episodes
- Pass threshold: >= 64 episodes (80%)

### Entity Discovery
- Expected: 5 key entities
- Pass threshold: >= 4 entities found (80%)

### Fact Validation
- Expected: 2 test queries
- Pass threshold: Both queries return >= 3 facts

### Semantic Search
- Expected: Relevant results in top 5
- Pass threshold: >= 2 relevant results

### Overall Result
- ALL validation checks must pass for overall PASS
- Any single failure results in overall FAIL

## Expected Entities

The disney_knowledge group should contain:

1. **Disney Studios** - The main organization
2. **OTE** - Organizational unit
3. **DEEPT** - Team name
4. **Data Platform Team** - Technical team
5. **Content Genome** - Technology/platform

## Expected Relationships

The validation queries test for:

1. **Technology relationships**: Disney Content Genome and associated technologies
2. **Organizational structure**: Teams and their relationships

## Troubleshooting

### Low Episode Count

If episode count is below threshold:
- Check migration logs for errors
- Verify source data was correctly classified as disney_knowledge
- Review entity classification logic in orchestrate_migration.py

### Missing Entities

If key entities are not found:
- Check if entity names were modified during extraction
- Verify embeddings are working correctly
- Test with broader search queries

### Low Fact Count

If fact queries return too few results:
- Verify relationships were extracted from episodes
- Check if LLM client is configured correctly
- Review episode content quality

### Semantic Search Issues

If semantic search quality is poor:
- Verify embedder configuration
- Check if vector search is enabled
- Test with different query formulations

## Files

- **validate_disney_knowledge.py**: Automated validation script
- **run_validation.sh**: Shell wrapper for validation
- **validation_disney_knowledge.json**: Generated validation report
- **migration_state.json**: Overall migration state tracking

## Next Steps

After validation:

1. If PASS: Proceed to next migration group
2. If FAIL: Review warnings and errors, fix issues, re-run migration
3. Update migration_state.json with validation results

## Environment Requirements

- Python 3.10+
- uv package manager
- Access to Graphiti Neo4j database
- OpenAI API key (for embeddings)
- Qdrant credentials (if using vector search)

## References

- [Migration Plan v2](../docs/migration_plan_v2.md)
- [Agent Definitions](../migration/agents/)
- [Orchestration Script](../migration/orchestrate_migration.py)
