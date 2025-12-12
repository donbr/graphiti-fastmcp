# Neo4j Memory to Graphiti Migration

Multi-agent migration system for transferring data from MCP_DOCKER Neo4j Memory to Graphiti temporal knowledge graphs.

## Overview

This migration uses the Claude Agent SDK to orchestrate 4 specialized agents:

| Agent | Model | Purpose |
|-------|-------|---------|
| Orchestrator | Opus | Coordinates phases, manages state, handles rollback |
| Extractor-Sequential | Sonnet | Critical data (don_branson_career) - 1 at a time |
| Extractor-Batch | Sonnet | Batch processing (10 per batch) for other domains |
| Validation | Sonnet | Quality assurance after each group completes |

## Quick Start

```bash
# 1. Verify environment
uv run python migration/orchestrate_migration.py --dry-run

# 2. Run migration (full)
uv run python migration/orchestrate_migration.py

# 3. Or run specific phase
uv run python migration/orchestrate_migration.py --phase 1
```

## Directory Structure

```
migration/
├── README.md                    # This file
├── orchestrate_migration.py     # Main orchestration script
├── neo4j_to_graphiti_migration_plan_v2.md  # Detailed migration plan
├── neo4j_memory_reference_guide.md         # Source system reference
├── graphiti_reference_guide_1.md           # Target system reference
├── progress/                    # State files (gitignored)
│   ├── .gitkeep
│   ├── migration_state.json     # Checkpoint file
│   └── validation_*.json        # Validation reports
├── logs/                        # Log files (gitignored)
│   └── .gitkeep
└── skills/
    └── SKILL.md                 # Migration skill for Claude
```

## Migration Groups (Priority Order)

| Phase | group_id | Priority | Mode | Expected |
|-------|----------|----------|------|----------|
| 1 | don_branson_career | CRITICAL | Sequential | ~50 |
| 2 | disney_knowledge | HIGH | Batch | ~80 |
| 3 | career_opportunities | MEDIUM | Batch | ~20 |
| 4 | technical_patterns | MEDIUM | Batch | ~40 |
| 5 | ai_engineering_research | LOW | Batch | ~110 |

## Rate Limiting

- **Sequential mode**: 1 episode, 2s pause (don_branson_career)
- **Batch mode**: 10 per batch, 3s pause between batches
- **Backoff**: Exponential on 429 errors (2s → 4s → 8s → 16s)

## Resume from Checkpoint

If migration fails, resume from where it stopped:

```bash
uv run python migration/orchestrate_migration.py --resume
```

State is saved to `progress/migration_state.json` after each batch.

## Validation

After each group completes, the validation agent checks:
- Episode count (≥80% of expected)
- Key entity discovery (≥80% found)
- Relationship extraction (≥3 facts per query)
- Semantic search quality

Reports saved to `progress/validation_{group_id}.json`.

## Rollback

To rollback a specific group:

```python
# DANGEROUS - requires confirmation
mcp__graphiti-local__clear_graph(group_ids=["group_id_here"])
```

Source Neo4j Memory remains unchanged as read-only reference.

## Agent Definitions

Located in `migration/agents/`:
- `orchestrator.json`
- `extractor_sequential.json`
- `extractor_batch.json`
- `validation_agent.json`

## Requirements

- Python 3.10+
- Claude Agent SDK: `pip install claude-agent-sdk`
- Running graphiti-local server
- Access to MCP_DOCKER (Neo4j Memory source)

## Estimated Runtime

10-16 hours depending on LLM response times and rate limits.
