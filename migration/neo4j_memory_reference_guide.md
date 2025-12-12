# Neo4j Memory Reference Guide: MCP_DOCKER Knowledge Graph
## Comprehensive Documentation for Graphiti Migration

**Last Verified:** 2025-12-12 10:05 PST  
**Source:** MCP_DOCKER Neo4j Memory Graph via read_graph  
**Purpose:** Reference guide for migrating data from MCP_DOCKER Neo4j Memory to Graphiti temporal knowledge graphs

---

## Executive Summary

The MCP_DOCKER Neo4j Memory server provides a persistent knowledge graph for storing entities, observations, and relationships. Unlike Graphiti's episode-first architecture, Neo4j Memory uses a direct entity-relationship model with observations stored as array properties on entity nodes.

**Key Characteristics:**
- Entity-first architecture (direct node creation)
- Observations as array properties on entities
- Simple typed relationships between entities
- No native temporal tracking on edges
- No embedded vectors in schema (semantic search not native)
- Graph namespacing not enforced (single graph space)

---

# Part 1: Core Concepts

## 1.1 Entity Structure

Entities are the fundamental unit of data in Neo4j Memory. Each entity represents a distinct concept, person, organization, or object.

### Entity Node Pattern

```
┌──────────────────────────────────────────────────────────────┐
│                      ENTITY NODE                              │
│  name: "Don Branson"                                         │
│  type: "person"                                              │
│  observations: [                                             │
│    "AI Engineer with 20+ years experience",                  │
│    "Neo4j Certified Professional",                           │
│    "Specializes in GraphRAG and agentic AI systems"          │
│  ]                                                           │
└──────────────────────────────────────────────────────────────┘
```

### Entity Properties

| Property | Type | Description |
|----------|------|-------------|
| `name` | String | Unique identifier for the entity |
| `type` | String | Category classification (person, organization, project, etc.) |
| `observations` | Array[String] | Facts, notes, and observations about the entity |

### Entity Types in Current Graph

| Type | Count | Examples |
|------|-------|----------|
| `person` | 20+ | Don Branson, Eddie Drake, Jamie Voris, JT Torrance |
| `Organization` | 25+ | Disney Studios, IBM, Apollo.io, Kizen, Fox Corporation |
| `Team` | 10+ | Data Platform Team, OTE, DEEPT, Disney Decision Science Team |
| `Project` | 20+ | kg_rememberall, nsclc-pathways, GDELT Insight Explorer |
| `Experience` | 10+ | IBM Application Architect Career, Quest Software Team Lead |
| `Technology` | 15+ | Neo4j, LangGraph, Content Genome, OneID Identity Graph |
| `Pattern` | 15+ | ReAct Loop Pattern, Medallion Architecture Pattern |
| `JobPosting` | 7 | Disney Ad Platforms ML Engineer Role, Kizen Principal AI Engineer |
| `Architecture` | 5+ | Disney Fog Network Architecture, Foundational Medallion Architecture |
| `research` | 3+ | Graphiti Migration Research Dec 2025, Disney 2025-2026 Data & AI Architecture Analysis |

---

## 1.2 Creating Entities

### Basic Entity Creation

```python
# MCP Tool: create_entities
await create_entities({
    "entities": [
        {
            "name": "Don Branson",
            "entityType": "person",
            "observations": [
                "AI Engineer with 20+ years experience",
                "Neo4j Certified Professional",
                "Specializes in GraphRAG and agentic AI systems"
            ]
        }
    ]
})
```

### Batch Entity Creation

```python
# Create multiple entities at once
await create_entities({
    "entities": [
        {
            "name": "Disney Studios",
            "entityType": "Organization",
            "observations": [
                "Parent organization for studio-related teams",
                "Located in Glendale, California"
            ]
        },
        {
            "name": "Data Platform Team Disney Studios",
            "entityType": "Team",
            "observations": [
                "Manages data platform pipelines",
                "Uses Neo4j for graph database solutions"
            ]
        }
    ]
})
```

### Adding Observations to Existing Entities

```python
# MCP Tool: add_observations
await add_observations({
    "observations": [
        {
            "entityName": "Don Branson",
            "contents": [
                "Interviewed at Disney December 10, 2025",
                "Two active Disney opportunities in pipeline"
            ]
        }
    ]
})
```

---

## 1.3 Relationship Structure

Relationships connect entities and are defined by source, target, and relationship type.

### Relationship Pattern

```
┌───────────────┐         ┌──────────────────┐         ┌───────────────┐
│   SOURCE      │         │    RELATION      │         │   TARGET      │
│   (Entity)    │─────────▶│  relationType   │─────────▶│   (Entity)    │
└───────────────┘         └──────────────────┘         └───────────────┘
  "Don Branson"              "HAS_EXPERIENCE"           "IBM Application
                                                         Architect Career"
```

### Relationship Properties

| Property | Type | Description |
|----------|------|-------------|
| `from` (source) | String | Name of the source entity |
| `to` (target) | String | Name of the target entity |
| `relationType` | String | Type of relationship (SCREAMING_SNAKE_CASE) |

### Common Relationship Types in Current Graph

| Category | Relationship Types | Usage |
|----------|-------------------|-------|
| **Professional** | WORKS_FOR, EMPLOYED_BY, REPORTS_TO, MEMBER_OF | Employment and team membership |
| **Authorship** | AUTHORED, CONTRIBUTED_TO, PRODUCED | Content creation and contributions |
| **Skills** | HAS_EXPERIENCE, HAS_SKILLS, HAS_EXPERTISE, HAS_CREDENTIALS | Competency associations |
| **Projects** | INCLUDES, USES, IMPLEMENTS, DEMONSTRATES | Project relationships |
| **Organizational** | PART_OF, LEADS, MANAGES, OVERSEES | Hierarchical structures |
| **Knowledge** | DOCUMENTED_IN, APPLIES_TO, RELATED_TO, SIMILAR_CONCEPT_TO | Semantic connections |
| **Temporal** | FOLLOWS, TRANSITIONED_TO, FOLLOWS_FROM | Sequence and progression |
| **Career** | CANDIDATE_FOR, RECRUITING_FOR, INTERVIEWER_FOR | Job search relationships |

---

## 1.4 Creating Relationships

### Basic Relationship Creation

```python
# MCP Tool: create_relations
await create_relations({
    "relations": [
        {
            "from": "Don Branson",
            "to": "IBM Application Architect Career",
            "relationType": "HAS_EXPERIENCE"
        },
        {
            "from": "Don Branson",
            "to": "kg_rememberall",
            "relationType": "AUTHORED"
        }
    ]
})
```

### Relationship Best Practices

| Criteria | Recommendation |
|----------|----------------|
| **Naming** | Use SCREAMING_SNAKE_CASE for relation types |
| **Direction** | Model active voice (AUTHORED, LEADS, USES) |
| **Specificity** | Use specific types over generic RELATES_TO |
| **Consistency** | Reuse existing relation types when possible |

---

# Part 2: Data Operations

## 2.1 Query Operations

### Read Entire Graph

```python
# MCP Tool: read_graph
result = await read_graph()
# Returns: {"entities": [...], "relations": [...]}
```

### Search Entities by Query

```python
# MCP Tool: search_nodes
result = await search_nodes({
    "query": "Don Branson Neo4j GraphRAG"
})
# Returns entities matching fulltext search across name, type, observations
```

### Open Specific Entities

```python
# MCP Tool: open_nodes
result = await open_nodes({
    "names": ["Don Branson", "Disney Studios", "Content Genome"]
})
# Returns specific entities with their relationships
```

---

## 2.2 Delete Operations

### Delete Entities

```python
# MCP Tool: delete_entities
# WARNING: Also deletes all relationships involving these entities
await delete_entities({
    "entityNames": ["Outdated Entity", "Old Project"]
})
```

### Delete Observations

```python
# MCP Tool: delete_observations
await delete_observations({
    "deletions": [
        {
            "entityName": "Don Branson",
            "observations": ["Outdated certification info"]
        }
    ]
})
```

### Delete Relationships

```python
# MCP Tool: delete_relations
await delete_relations({
    "relations": [
        {
            "from": "Don Branson",
            "to": "Old Company",
            "relationType": "WORKS_FOR"
        }
    ]
})
```

---

## 2.3 Graph Schema Analysis

### Current Graph Statistics

| Metric | Value |
|--------|-------|
| Total Entities | 300+ |
| Total Relationships | 500+ |
| Entity Types | 20+ distinct types |
| Relationship Types | 50+ distinct types |

### Domain Coverage

| Domain | Description | Key Entities |
|--------|-------------|--------------|
| **Professional Profile** | Don Branson's career data | Don Branson, certifications, skills |
| **Career History** | Work experience timeline | IBM, CDI Corporation, Quest Software experiences |
| **Projects** | Technical project portfolio | kg_rememberall, nsclc-pathways, GDELT |
| **Disney Organization** | Disney company structure | Disney Studios, DEEPT, OTE, teams |
| **Job Market** | Active job opportunities | 7 job postings with salary data |
| **Architecture Patterns** | Technical patterns | Medallion, Kappa, ReAct, RAG patterns |
| **Research** | Technical research findings | Migration research, architecture analysis |

---

# Part 3: Migration Reference

## 3.1 Key Differences: Neo4j Memory vs Graphiti

| Aspect | Neo4j Memory | Graphiti |
|--------|-------------|----------|
| **Ingestion Model** | Entity-first (direct creation) | Episode-first (LLM extraction) |
| **Observations** | Array property on entity | Extracted into EntityEdge facts |
| **Temporal Tracking** | None | valid_at, invalid_at, expired_at on edges |
| **Embeddings** | Not stored | Generated for semantic search |
| **Namespacing** | Single graph | group_id isolation |
| **Entity Resolution** | Manual (by name) | Automatic (LLM deduplication) |

## 3.2 Recommended Migration Strategy: Episode-First Conversion

### Why Episode-First?

| Aspect | Episode Ingestion | Direct Node Import |
|--------|-------------------|-------------------|
| **Semantic Consistency** | ✅ Preserved via LLM extraction | ⚠️ May differ |
| **Embeddings** | ✅ Generated properly | ⚠️ Manual process |
| **Temporal Tracking** | ✅ Via reference_time | ⚠️ Manual |
| **Community Detection** | ✅ Works correctly | ⚠️ May not work |
| **Provenance** | ✅ Episode links preserved | ❌ No episode links |

### Entity-to-Episode Conversion Template

```python
import json
from datetime import datetime
from graphiti_core.nodes import EpisodeType

def entity_to_episode(entity: dict) -> dict:
    """Convert a Neo4j Memory entity to a Graphiti episode."""
    return {
        "name": f"{entity['type']}_{entity['name'][:50]}",
        "episode_body": json.dumps({
            "entity_type": entity["type"],
            "entity_name": entity["name"],
            "observations": entity.get("observations", []),
            "source": "neo4j_memory_migration",
            "migrated_at": datetime.now().isoformat()
        }),
        "source": EpisodeType.json,
        "source_description": "Migrated from MCP_DOCKER Neo4j Memory graph",
        "group_id": determine_group_id(entity["type"])
    }

def determine_group_id(entity_type: str) -> str:
    """Map entity types to Graphiti group_ids."""
    type_mapping = {
        "person": "don_branson_resume_v3",
        "Experience": "don_branson_resume_v3",
        "Skills": "don_branson_resume_v3",
        "Credentials": "don_branson_resume_v3",
        "Project": "don_branson_resume_v3",
        "Organization": "disney_knowledge_2025",
        "Team": "disney_knowledge_2025",
        "Architecture": "disney_knowledge_2025",
        "Technology": "disney_knowledge_2025",
        "JobPosting": "career_opportunities_2025",
        "Pattern": "technical_patterns",
        "research": "technical_research"
    }
    return type_mapping.get(entity_type, "general_knowledge")
```

## 3.3 Group ID Strategy for Migration

| group_id | Content Type | Migration Priority | Entity Count |
|----------|--------------|-------------------|--------------|
| `don_branson_resume_v3` | Resume, skills, work history, projects | CRITICAL | ~100 |
| `disney_knowledge_2025` | Disney org, tech, architecture, teams | HIGH | ~80 |
| `career_opportunities_2025` | Job postings, job search, recruiters | MEDIUM | ~20 |
| `technical_patterns` | Architecture patterns, best practices | MEDIUM | ~30 |
| `technical_research` | Research findings, analysis documents | LOW | ~15 |

## 3.4 Relationship Migration Strategy

Neo4j Memory relationships don't map directly to Graphiti's fact-based edges. Options:

### Option A: Include in Episode Body (Recommended)

```python
def entity_with_relations_to_episode(entity: dict, relations: list) -> dict:
    """Convert entity with its relationships to episode."""
    outgoing = [r for r in relations if r['from'] == entity['name']]
    incoming = [r for r in relations if r['to'] == entity['name']]
    
    return {
        "name": f"{entity['type']}_{entity['name'][:50]}",
        "episode_body": json.dumps({
            "entity_type": entity["type"],
            "entity_name": entity["name"],
            "observations": entity.get("observations", []),
            "relationships": {
                "outgoing": [
                    {"to": r['to'], "type": r['relationType']} 
                    for r in outgoing
                ],
                "incoming": [
                    {"from": r['from'], "type": r['relationType']} 
                    for r in incoming
                ]
            },
            "source": "neo4j_memory_migration"
        }),
        "source": EpisodeType.json,
        "source_description": "Migrated from MCP_DOCKER Neo4j Memory",
        "group_id": determine_group_id(entity["type"])
    }
```

### Option B: Separate Relationship Episodes

```python
def relation_to_episode(relation: dict) -> dict:
    """Convert a relationship to a text episode."""
    fact_text = f"{relation['from']} {relation['relationType'].replace('_', ' ').lower()} {relation['to']}"
    
    return {
        "name": f"Relation_{relation['relationType'][:30]}",
        "episode_body": fact_text,
        "source": EpisodeType.text,
        "source_description": "Relationship from Neo4j Memory",
        "group_id": "migrated_relations"
    }
```

## 3.5 Full Migration Script Template

```python
import asyncio
import json
from datetime import datetime

async def migrate_neo4j_to_graphiti(neo4j_graph: dict, graphiti_client):
    """
    Complete migration from Neo4j Memory to Graphiti.
    
    Args:
        neo4j_graph: Result from MCP_DOCKER read_graph()
        graphiti_client: Initialized Graphiti client
    """
    entities = neo4j_graph['entities']
    relations = neo4j_graph['relations']
    
    # Group entities by target group_id
    grouped_entities = {}
    for entity in entities:
        group_id = determine_group_id(entity.get('type', 'unknown'))
        if group_id not in grouped_entities:
            grouped_entities[group_id] = []
        grouped_entities[group_id].append(entity)
    
    # Migrate by priority group
    priority_order = [
        'don_branson_resume_v3',
        'disney_knowledge_2025',
        'career_opportunities_2025',
        'technical_patterns',
        'technical_research'
    ]
    
    migrated_count = 0
    
    for group_id in priority_order:
        if group_id not in grouped_entities:
            continue
            
        print(f"Migrating group: {group_id}")
        
        for entity in grouped_entities[group_id]:
            episode = entity_with_relations_to_episode(entity, relations)
            
            await graphiti_client.add_episode(
                name=episode['name'],
                episode_body=episode['episode_body'],
                source=episode['source'],
                source_description=episode['source_description'],
                group_id=group_id,
                reference_time=datetime.now()
            )
            
            migrated_count += 1
            
            # Rate limiting
            if migrated_count % 10 == 0:
                print(f"Migrated {migrated_count} entities...")
                await asyncio.sleep(1)
    
    print(f"Migration complete: {migrated_count} entities migrated")
    return migrated_count
```

## 3.6 Validation Queries Post-Migration

### Graphiti Validation

```python
# Verify entity extraction
nodes = await search_nodes(
    query="Don Branson Neo4j GraphRAG",
    group_ids=["don_branson_resume_v3"]
)
print(f"Found {len(nodes)} matching nodes")

# Verify fact extraction
facts = await search_memory_facts(
    query="experience certifications projects",
    group_ids=["don_branson_resume_v3"]
)
print(f"Found {len(facts)} facts")

# Verify episode count
episodes = await get_episodes(
    group_ids=["don_branson_resume_v3"],
    max_episodes=100
)
print(f"Migrated episodes: {len(episodes)}")
```

### Comparison Validation

```python
async def validate_migration(neo4j_graph: dict, graphiti_client) -> dict:
    """Compare Neo4j Memory entities with Graphiti nodes."""
    
    # Get all Neo4j entities
    neo4j_entities = {e['name'] for e in neo4j_graph['entities']}
    
    # Search for each in Graphiti
    found_in_graphiti = set()
    missing_in_graphiti = set()
    
    for name in neo4j_entities:
        nodes = await graphiti_client.search_nodes(query=name)
        if any(name.lower() in n.name.lower() for n in nodes):
            found_in_graphiti.add(name)
        else:
            missing_in_graphiti.add(name)
    
    return {
        "total_neo4j": len(neo4j_entities),
        "found_in_graphiti": len(found_in_graphiti),
        "missing_in_graphiti": len(missing_in_graphiti),
        "missing_entities": list(missing_in_graphiti)[:20]  # Sample
    }
```

## 3.7 Rollback Strategy

```python
# Clear specific namespace in Graphiti
await graphiti.clear_graph(group_ids=["don_branson_resume_v3"])

# Neo4j Memory graph remains unchanged as read-only reference
# Can re-run migration after adjustments
```

---

# Part 4: Entity Catalog

## 4.1 Professional Profile Entities

### Don Branson (Primary Entity)

```json
{
  "name": "Don Branson",
  "type": "person",
  "observations": [
    "AI Engineer and Solutions Architect with 20+ years experience",
    "Neo4j Certified Professional",
    "Specializes in knowledge graphs, GraphRAG, and agentic AI systems",
    "Email: dwbranson@gmail.com",
    "Location: Fullerton CA, USA",
    "Education: BA in Psychology, University of Alberta",
    "Languages: English, French",
    "Two active Disney opportunities: Data Platform Team and Decision Science Team"
  ],
  "key_relationships": [
    "HAS_EXPERIENCE → IBM Application Architect Career",
    "AUTHORED → kg_rememberall, nsclc-pathways, GDELT Insight Explorer",
    "HAS_CREDENTIALS → Don Branson Certifications",
    "HAS_SKILLS → Don Branson Technical Skills",
    "CANDIDATE_FOR → Disney Ad Platforms ML Engineer Role, Kizen Principal AI Engineer Role"
  ]
}
```

### Key Experience Entities

| Entity Name | Type | Years | Key Observations |
|-------------|------|-------|------------------|
| IBM Application Architect Career | Experience | 2010-2024 | 14 years total, subcontractor then direct |
| CDI Corporation Development Team Lead | Experience | 2010-2017 | American Airlines Cargo, B2B integration |
| Quest Software Team Lead | Experience | 2004-2009 | SOA, Siebel CRM, EDI/BPEL |
| AI Engineer Independent Consultant | Experience | 2024-Present | GraphRAG, agentic systems, Neo4j |

### Certification Entities

```json
{
  "name": "Don Branson Certifications",
  "type": "Credentials",
  "observations": [
    "Microsoft Certified: Azure AI Engineer Associate (active)",
    "Microsoft Certified: Azure Solutions Architect Expert (active)",
    "Neo4j Certified Professional - Graph Data Science",
    "AWS Certified Developer - Associate",
    "TOGAF 9 Foundations",
    "AI Makerspace Certified AI Engineer (2024)"
  ]
}
```

## 4.2 Disney Organization Entities

### Organization Hierarchy

```
Disney Studios (Organization)
├── Studio Technology (Team) - CTO: Eddie Drake
│   ├── Studio Data Platform (Team)
│   │   └── Data Platform Team Disney Studios (Team)
│   │       ├── JT Torrance (Person) - Staff Data Engineer
│   │       └── Rory McNaughton (Person) - Senior Manager
│   └── Content Genome (Technology)
├── DEEPT (BuyingCenter) - CPTO: Adam Smith
│   ├── Disney+ Product
│   ├── Hulu Product
│   └── ESPN+ Product
└── OTE (BuyingCenter) - Head: Jamie Voris
    ├── Disney Agentic AI Initiative
    ├── Disney Spatial Computing Strategy
    └── Automatronics Project
```

### Key Technology Entities

| Entity | Type | Key Observations |
|--------|------|------------------|
| Content Genome | Technology | ML system for digital archival, graph database, RAG source |
| OneID Identity Graph | Technology | Universal identifier, graph database methodologies |
| Disney Compass | Platform | Unified advertising data platform, Snowflake Clean Rooms |
| Foundational Medallion Architecture | Architecture | Databricks/AWS, Bronze/Silver/Gold tiers |

## 4.3 Project Entities

### Don Branson Projects

| Project | Type | Technologies | Status |
|---------|------|--------------|--------|
| kg_rememberall | project | GLiNER, GLiREL, Neo4j, LanceDB, Prefect | Active |
| nsclc-pathways | project | WikiPathways, STITCH, BioGrid, Neo4j | Complete |
| GDELT Insight Explorer | Project | Qdrant, Neo4j, LangGraph, Prefect | Active |
| ra-commons Orchestrator Framework | Project | Multi-agent workflows, evaluation loops | Active |
| OpenTelemetry GenAI Validation Framework | Project | LangSmith, Arize Phoenix, RAGAS | Active |

## 4.4 Job Market Entities

### Active Job Postings (December 2025)

| Entity | Company | Salary Range | Key Requirements |
|--------|---------|--------------|------------------|
| Disney Ad Platforms ML Engineer Role | Disney | $141K-$208K | LangGraph, RAG, Java |
| Kizen Principal AI Engineer Role | Kizen | $250K-$350K | Graph-based RAG, Django |
| Whatnot LLM Platform Engineer Role | Whatnot | $225K-$320K | MCP servers, RAG |
| Sony Pictures Director Data Science Role | Sony | $190K-$228K | RAG pipelines, MLOps |
| Fox Corporation Senior ML Engineer Role | Fox | $160K-$180K | LangChain, agentic workflows |
| Apollo.io Senior AI Engineer Role | Apollo.io | $190K-$300K | Multi-agent systems |
| Deluxe Media Senior Director Architecture Role | Deluxe | $208K-$260K | Cloud-native, AI/ML |

---

# Appendix A: MCP Server Tools Reference

| Tool | Description | Parameters |
|------|-------------|------------|
| `create_entities` | Create multiple new entities | entities: [{name, entityType, observations}] |
| `create_relations` | Create relationships between entities | relations: [{from, to, relationType}] |
| `add_observations` | Add observations to existing entities | observations: [{entityName, contents}] |
| `delete_entities` | Delete entities and their relationships | entityNames: [string] |
| `delete_observations` | Remove specific observations | deletions: [{entityName, observations}] |
| `delete_relations` | Remove specific relationships | relations: [{from, to, relationType}] |
| `read_graph` | Read entire knowledge graph | (none) |
| `search_nodes` | Search entities by query | query: string |
| `open_nodes` | Retrieve specific entities | names: [string] |

# Appendix B: Relationship Type Inventory

```
Professional Relationships:
├── WORKS_FOR, EMPLOYED_BY, REPORTS_TO
├── MEMBER_OF, LEADS, MANAGES, OVERSEES
└── RECRUITING_FOR, CANDIDATE_FOR, INTERVIEWER_FOR

Content Relationships:
├── AUTHORED, CONTRIBUTED_TO, PRODUCED
├── INCLUDES, CONTAINS, USES, IMPLEMENTS
└── DEMONSTRATES, ENABLES, SUPPORTS

Knowledge Relationships:
├── DOCUMENTED_IN, APPLIES_TO, RELATED_TO
├── SIMILAR_CONCEPT_TO, COMPLEMENTS, EXTENDS
└── FOUNDATION_FOR, SKILLS_TRANSFER_TO

Temporal Relationships:
├── FOLLOWS, FOLLOWS_FROM, TRANSITIONED_TO
├── PREDECESSOR_OF, EXTENDS, LEARNS_FROM
└── CONTEXT_FOR, INFORMS

Organizational Relationships:
├── PART_OF, LOCATED_AT, PARTNERS_WITH
├── POSTED_BY, POSITION_IN, DISCOVERED
└── AFFECTS, CONSTRAINS, GOVERNS
```

# Appendix C: Migration Checklist

## Pre-Migration
- [ ] Export complete Neo4j Memory graph via `read_graph()`
- [ ] Analyze entity types and relationship patterns
- [ ] Define group_id mapping strategy
- [ ] Initialize Graphiti with target group_ids
- [ ] Verify Graphiti connection and permissions

## Migration Execution
- [ ] Migrate CRITICAL group (don_branson_resume_v3) first
- [ ] Validate core entities present in Graphiti
- [ ] Migrate HIGH priority groups
- [ ] Implement rate limiting to avoid LLM throttling
- [ ] Log migration progress and any errors

## Post-Migration Validation
- [ ] Verify entity counts per group_id
- [ ] Spot-check key relationships extracted as facts
- [ ] Test semantic search queries
- [ ] Compare search results Neo4j vs Graphiti
- [ ] Document any semantic drift or missing entities

## Rollback Preparation
- [ ] Keep Neo4j Memory graph unchanged (read-only reference)
- [ ] Document clear_graph commands for rollback
- [ ] Maintain entity mapping for debugging

---

# References

## Source Documentation

| Document | Location | Purpose |
|----------|----------|---------|
| Graphiti Reference Guide | `/mnt/project/graphiti_reference_guide.md` | Target system reference |
| Neo4j Memory Notes | `/mnt/project/2025-12-12-17-53-17-mcp-neo4j-memory-reference-guide.txt` | Session context |
| Resume Retrieval Instructions | `/mnt/project/RESUME_RETRIEVAL_INSTRUCTIONS.md` | Query patterns |

## MCP Servers Used

| Server | Purpose | Key Tools |
|--------|---------|-----------|
| MCP_DOCKER | Source Neo4j Memory graph | read_graph, search_nodes, create_entities |
| graphiti-local | Target Graphiti system | add_memory, search_nodes, search_memory_facts |
| qdrant-docs | Documentation search | search_docs (Zep: 119 docs) |
| mcp-server-time | Timestamp verification | get_current_time |

## Related Research

| Research | Date | Key Findings |
|----------|------|--------------|
| Graphiti Migration Research | Dec 2025 | Episode-first recommended, no bulk import APIs |
| Graphiti FalkorDB Neo4j Migration | Dec 2025 | Vector format incompatibilities, vecf32 issues |
| Graphiti Schema Evolution Gap | Dec 2025 | Custom entity types via Pydantic models |

## Graphiti Core Concepts (from Reference Guide)

- **Episodes**: Fundamental unit of data ingestion (text, message, json)
- **Entities**: Extracted from episodes via LLM
- **EntityEdges**: Facts as relationships with temporal validity
- **group_id**: Multi-tenant namespace isolation
- **Communities**: Leiden algorithm clustering for synthesis

---

**Document Version:** 1.0  
**Last Verified:** 2025-12-12 10:05 PST  
**Tools Used:** MCP_DOCKER:read_graph, mcp-server-time:get_current_time, view (project files)  
**Migration Target:** Graphiti temporal knowledge graph via graphiti-local MCP
