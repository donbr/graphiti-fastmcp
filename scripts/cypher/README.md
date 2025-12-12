# Graphiti Cypher Query Toolkit

Cypher queries for monitoring and managing Graphiti knowledge graphs on Neo4j.

## Quick Start

Open Neo4j Browser and run queries from the appropriate file based on your need.

## Query Files

| File | Purpose | Frequency |
|------|---------|-----------|
| [01_health_dashboard.cypher](01_health_dashboard.cypher) | Overall system health and statistics | Daily |
| [02_data_quality.cypher](02_data_quality.cypher) | Find data issues (orphans, missing embeddings) | Weekly |
| [03_temporal_analysis.cypher](03_temporal_analysis.cypher) | Track knowledge evolution and fact invalidation | As needed |
| [04_debug_search.cypher](04_debug_search.cypher) | Ad-hoc entity and episode lookup | As needed |
| [05_capacity_planning.cypher](05_capacity_planning.cypher) | Size estimates and growth tracking | Monthly |

## Graphiti Schema Reference

### Node Labels

| Label | Description |
|-------|-------------|
| `Episodic` | Episodes (input data units) |
| `Entity` | Base label for all extracted entities |
| `Organization` | Companies, institutions, groups |
| `Topic` | Subject areas, knowledge domains |
| `Requirement` | Needs, features, functionality |
| `Procedure` | Instructions, processes |
| `Document` | Information content (articles, reports) |
| `Location` | Physical or virtual places |
| `Event` | Time-bound activities |
| `Preference` | User choices, opinions |
| `Object` | Physical items, tools |

### Relationship Types

| Type | Description |
|------|-------------|
| `RELATES_TO` | Semantic relationship between entities |
| `MENTIONS` | Episode mentions an entity |

### Key Properties

| Property | Found On | Description |
|----------|----------|-------------|
| `group_id` | All nodes | Logical namespace for filtering |
| `name` | Entities, Episodes | Human-readable identifier |
| `uuid` | All nodes | Unique identifier |
| `created_at` | All nodes | Creation timestamp |
| `summary` | Entities | LLM-generated summary |
| `name_embedding` | Entities | Vector embedding for search |
| `valid_at` | Relationships | When fact became true |
| `invalid_at` | Relationships | When fact was superseded |

## Usage Tips

1. **Always filter by group_id** when querying specific namespaces
2. **Check embeddings** after data issues - missing embeddings break search
3. **Monitor invalidations** to understand knowledge evolution
4. **Run health dashboard** after bulk imports to verify success

## Current Knowledge Graphs

| Group ID | Purpose |
|----------|---------|
| `graphiti_meta_knowledge` | How to use Graphiti effectively |
| `graphiti_reference_docs` | Reference documentation summaries |

## See Also

- [QUICKSTART.md](../../QUICKSTART.md) - Getting started with Graphiti MCP
- [CLAUDE.md](../../CLAUDE.md) - Project documentation
- [reference/GRAPHITI_BEST_PRACTICES.md](../../reference/GRAPHITI_BEST_PRACTICES.md) - Episode design guidelines
