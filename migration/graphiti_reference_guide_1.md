# Graphiti Reference Guide: Core Concepts & Data Operations
## Comprehensive Documentation for Graph Migration

**Last Verified:** 2025-12-12 09:33 PST  
**Source:** Zep Documentation via qdrant-docs MCP  
**Purpose:** Reference guide for migrating data into Graphiti temporal knowledge graphs

---

## Executive Summary

Graphiti is a Python framework for building **temporally-aware knowledge graphs** designed for AI agents. It enables real-time incremental updates to knowledge graphs without batch recomputation, making it suitable for dynamic environments where relationships and information evolve over time.

**Key Characteristics:**
- Episode-first architecture (primary ingestion via episodes)
- Automatic entity and relationship extraction via LLM
- Hybrid search combining semantic, BM25, and graph traversal
- Graph namespacing via `group_id` for multi-tenant isolation
- Community detection for high-level graph synthesis

---

# Part 1: Core Concepts

## 1.1 Adding Episodes

Episodes are the **fundamental unit of data ingestion** in Graphiti. An episode represents a single data ingestion event and is itself a node in the graph.

### Episode Architecture

```
┌──────────────────────────────────────────────────────┐
│                    EPISODE NODE                       │
│  (Represents a single data ingestion event)          │
└────────────────────────┬─────────────────────────────┘
                         │ MENTIONS
         ┌───────────────┼───────────────┐
         │               │               │
         ▼               ▼               ▼
    ┌─────────┐    ┌─────────┐    ┌─────────┐
    │ Entity  │    │ Entity  │    │ Entity  │
    │  Node   │    │  Node   │    │  Node   │
    └─────────┘    └─────────┘    └─────────┘
```

### Supported Episode Types

| Type | Description | Use Case |
|------|-------------|----------|
| `text` | Unstructured text data | Documents, articles, wiki pages |
| `message` | Conversational format `speaker: message...` | Chat logs, emails, transcripts |
| `json` | Structured data | CRM records, API responses, metadata |

### Basic Episode Addition

```python
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType

# Initialize Graphiti
graphiti = Graphiti(uri, user, password)

# Add a text episode
await graphiti.add_episode(
    name="Disney Research Notes",
    episode_body="Eddie Drake is the CTO of Walt Disney Studios. He previously led technology at Marvel Studios.",
    source=EpisodeType.text,
    source_description="Research notes on Disney leadership",
    reference_time=datetime.now(),  # Optional temporal anchor
    group_id="disney_knowledge_2025"  # Namespace isolation
)
```

### JSON Episode Ingestion

JSON episodes are processed distinctly, extracting entities and relationships from structured data:

```python
import json

# JSON data
data = {
    "entity_type": "Person",
    "name": "Eddie Drake",
    "role": "CTO of Walt Disney Studios",
    "previous_role": "Head of Technology at Marvel Studios",
    "focus_areas": ["innovative solutions", "scalable tech", "secure systems"]
}

await graphiti.add_episode(
    name="Person: Eddie Drake",
    episode_body=json.dumps(data),
    source=EpisodeType.json,
    source_description="Disney leadership profile",
    group_id="disney_knowledge_2025"
)
```

### JSON Best Practices

From Zep documentation, JSON ingestion works best when:

| Criteria | Description |
|----------|-------------|
| **Not too large** | Large JSON should be divided into pieces, adding each piece separately |
| **Not deeply nested** | More than 3-4 levels of nesting should be flattened |
| **Understandable in isolation** | Include descriptions or clear attribute names |
| **Represents a unified entity** | Each JSON should ideally represent a single conceptual entity |

### Batch Episode Ingestion

For efficient bulk loading of large datasets:

```python
episodes = [
    RawEpisode(
        name="Episode 1",
        content="Content here...",
        source=EpisodeType.text,
        source_description="Batch import",
        reference_time=datetime.now()
    ),
    # ... more episodes
]

await graphiti.add_episode_bulk(episodes, group_id="disney_knowledge_2025")
```

**Warning:** Batch ingestion is designed for scenarios where:
- Graph is empty (initial load)
- Edge invalidation is not required
- Order of processing is not critical

---

## 1.2 Custom Entity and Edge Types

Graphiti allows defining custom entity types and edge types using **Pydantic models** to create domain-specific ontologies.

### Defining Custom Entity Types

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class Person(BaseModel):
    """A person entity with biographical information."""
    age: Optional[int] = Field(None, description="Age of the person")
    occupation: Optional[str] = Field(None, description="Current occupation")
    location: Optional[str] = Field(None, description="Current location")
    birth_date: Optional[datetime] = Field(None, description="Date of birth")

class Company(BaseModel):
    """A business organization entity."""
    industry: Optional[str] = Field(None, description="Primary industry")
    founded: Optional[int] = Field(None, description="Year founded")
    headquarters: Optional[str] = Field(None, description="HQ location")
    employee_count: Optional[int] = Field(None, description="Number of employees")

class Technology(BaseModel):
    """A technology, tool, or framework."""
    category: Optional[str] = Field(None, description="Tech category")
    version: Optional[str] = Field(None, description="Current version")
    open_source: Optional[bool] = Field(None, description="Is open source")
```

### Defining Custom Edge Types

```python
class WorksAt(BaseModel):
    """Employment relationship between person and company."""
    start_date: Optional[datetime] = Field(None, description="Employment start date")
    end_date: Optional[datetime] = Field(None, description="Employment end date")
    title: Optional[str] = Field(None, description="Job title")
    department: Optional[str] = Field(None, description="Department")

class UsesSkill(BaseModel):
    """Relationship between person and skill/technology."""
    proficiency: Optional[str] = Field(None, description="Skill level: beginner/intermediate/expert")
    years_experience: Optional[int] = Field(None, description="Years of experience")
```

### Using Custom Types with Episodes

```python
# Define entity types dictionary
entity_types = {
    "Person": Person,
    "Company": Company,
    "Technology": Technology
}

# Define edge types dictionary
edge_types = {
    "WORKS_AT": WorksAt,
    "USES": UsesSkill
}

# Add episode with custom ontology
await graphiti.add_episode(
    name="Don Branson Profile",
    episode_body="Don Branson is an AI Engineer who works with Neo4j and LangGraph.",
    source=EpisodeType.text,
    source_description="Professional profile",
    entity_types=entity_types,
    edge_types=edge_types,
    group_id="don_branson_resume_v3"
)
```

### Edge Type Mapping Behavior

- If no mapping exists for a node pair, Graphiti uses generic `RELATES_TO`
- Custom edge types enable richer semantic relationships
- Types are optional but improve graph structure quality

---

## 1.3 Communities

Communities represent **groups of related entity nodes** determined by the Leiden algorithm, which clusters strongly connected nodes together.

### Building Communities

```python
# Build communities for the entire graph
await graphiti.build_communities()
```

### Community Features

| Feature | Description |
|---------|-------------|
| **Clustering** | Uses Leiden algorithm for modularity optimization |
| **Summaries** | Contains synthesized summary of member entity summaries |
| **High-level View** | Provides overview of what the graph contains |
| **Incremental Updates** | Can be updated as new episodes are added |

### Updating Communities with New Episodes

```python
# Add episode and update communities
await graphiti.add_episode(
    name="New Research",
    episode_body="...",
    source=EpisodeType.text,
    update_communities=True  # Incrementally update communities
)
```

### Community Update Methodology

When a new node is added:
1. Graphiti determines which community it should join
2. Selection based on most represented community among surrounding nodes
3. Community summary is updated to include new node information

---

## 1.4 Graph Namespacing (group_id)

Graph namespacing via `group_id` creates **isolated graph environments** within the same Graphiti instance.

### Namespace Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GRAPHITI INSTANCE                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │  group_id:          │  │  group_id:          │          │
│  │  disney_knowledge   │  │  don_branson_resume │          │
│  │  ─────────────────  │  │  ─────────────────  │          │
│  │  • Disney orgs      │  │  • Work history     │          │
│  │  • Tech stack       │  │  • Skills           │          │
│  │  • Personnel        │  │  • Projects         │          │
│  │  • Strategies       │  │  • Certifications   │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                             │
│  ┌─────────────────────┐  ┌─────────────────────┐          │
│  │  group_id:          │  │  group_id:          │          │
│  │  disney_interview   │  │  career_patterns    │          │
│  │  ─────────────────  │  │  ─────────────────  │          │
│  │  • Debrief notes    │  │  • Industry domain  │          │
│  │  • Lessons learned  │  │  • Tech evolution   │          │
│  │  • Next steps       │  │  • Strategy         │          │
│  └─────────────────────┘  └─────────────────────┘          │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Use Cases for Namespacing

| Use Case | Description |
|----------|-------------|
| **Multi-tenant applications** | Isolate data between customers/organizations |
| **Testing environments** | Separate dev, test, and production graphs |
| **Domain-specific knowledge** | Create specialized graphs for different domains |
| **Team collaboration** | Different teams work with their own graph spaces |

### Namespace Behavior

- Nodes and edges with the same `group_id` form a **cohesive, isolated graph**
- Queries are automatically scoped to the specified `group_id`
- **Critical:** Mismatched `group_id` causes data to be "invisible" to queries

### Example: Multi-Namespace Workflow

```python
# Add to Disney knowledge namespace
await graphiti.add_episode(
    name="Disney Tech Stack",
    episode_body="Disney uses Neo4j, Snowflake, and LangGraph...",
    source=EpisodeType.text,
    group_id="disney_knowledge_2025"
)

# Add to resume namespace
await graphiti.add_episode(
    name="Don Branson Skills",
    episode_body="Don Branson is proficient in Neo4j, Python, and GraphRAG...",
    source=EpisodeType.text,
    group_id="don_branson_resume_v3"
)

# Query scoped to specific namespace
results = await graphiti.search(
    query="Neo4j experience",
    group_ids=["don_branson_resume_v3"]  # Only searches resume namespace
)
```

---

# Part 2: Working with Data

## 2.1 Searching the Graph

Graphiti provides **hybrid search** combining multiple retrieval methods for optimal results.

### Search Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                      HYBRID SEARCH                            │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌────────────┐  ┌────────────┐  ┌─────────────────────┐    │
│  │  Semantic  │  │   BM25     │  │  Graph Traversal    │    │
│  │  (Vector)  │  │ (Keyword)  │  │  (Relationship)     │    │
│  └─────┬──────┘  └─────┬──────┘  └──────────┬──────────┘    │
│        │               │                     │               │
│        └───────────────┼─────────────────────┘               │
│                        │                                     │
│                        ▼                                     │
│           ┌────────────────────────┐                        │
│           │  Reciprocal Rank      │                        │
│           │  Fusion (RRF)         │                        │
│           └───────────┬───────────┘                        │
│                       │                                     │
│                       ▼                                     │
│              ┌─────────────────┐                           │
│              │ Ranked Results  │                           │
│              └─────────────────┘                           │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Basic Search

```python
# Simple hybrid search
results = await graphiti.search(
    query="Neo4j graph database experience"
)

# Search with namespace filtering
results = await graphiti.search(
    query="LangGraph multi-agent workflows",
    group_ids=["don_branson_resume_v3", "disney_knowledge_2025"]
)
```

### Node Distance Reranking

Extends hybrid search by prioritizing results based on proximity to a specified "focal" node:

```python
# First, find the focal node
focal_node = await graphiti.get_node_by_name("Don Branson")

# Search with node distance reranking
results = await graphiti.search(
    query="graph database projects",
    focal_node_uuid=focal_node.uuid
)
```

**Use Case:** Entity-specific queries where context around a particular node is most relevant.

### Search Comparison

| Search Type | Method | Best For |
|-------------|--------|----------|
| **Hybrid Search** | `search(query)` | Broad exploration, general queries |
| **Node Distance Reranking** | `search(query, focal_node_uuid)` | Entity-specific queries, contextual relevance |

### MCP Server Search Tools

When using Graphiti via MCP:

```python
# Search for nodes (entities)
search_nodes(
    query="Neo4j LangGraph Python",
    group_ids=["don_branson_resume_v3"],
    max_nodes=10,
    entity_types=["Technology"]  # Optional type filter
)

# Search for facts (edges/relationships)
search_memory_facts(
    query="data engineering pipeline experience",
    group_ids=["don_branson_resume_v3"],
    max_facts=15,
    center_node_uuid="uuid-123"  # Optional proximity reranking
)
```

---

## 2.2 CRUD Operations

Graphiti uses **8 core classes** for graph data management.

### Core Classes

| Class | Description | Parent |
|-------|-------------|--------|
| `Node` | Abstract base class for nodes | - |
| `EpisodicNode` | Raw episode storage | `Node` |
| `EntityNode` | Extracted entities | `Node` |
| `CommunityNode` | Community clusters | `Node` |
| `Edge` | Abstract base class for edges | - |
| `EpisodicEdge` | Episode-to-entity links | `Edge` |
| `EntityEdge` | Entity-to-entity relationships (facts) | `Edge` |
| `CommunityEdge` | Community connections | `Edge` |

### Save Operation (MERGE Pattern)

The `save()` method performs a **find-or-create** based on UUID:

```python
from graphiti_core.nodes import EntityNode

# Create or update a node
node = EntityNode(
    uuid="unique-uuid-here",
    name="Don Branson",
    summary="AI Engineer specializing in GraphRAG and knowledge graphs",
    group_id="don_branson_resume_v3"
)

await node.save(driver)  # MERGE based on uuid
```

### Underlying Cypher Pattern

```cypher
MERGE (n:Entity {uuid: $uuid})
SET n = {
    uuid: $uuid,
    name: $name,
    name_embedding: $name_embedding,
    summary: $summary,
    created_at: $created_at
}
RETURN n.uuid AS uuid
```

### Delete Operations

```python
# Delete a node
await entity_node.delete(driver)

# Delete an edge
await entity_edge.delete(driver)

# Delete an episode (does not regenerate facts/edges)
await episodic_node.delete(driver)
```

**Warning:** Deleting an edge never deletes associated nodes, even if it leaves orphan nodes with no edges.

### Retrieve Operations

```python
# Get episodes for a group
episodes = await graphiti.get_episodes(
    group_ids=["disney_knowledge_2025"],
    max_episodes=10
)

# Get a specific node by UUID
node = await graphiti.get_node(uuid="node-uuid")
```

---

## 2.3 Adding Fact Triples

Fact triples allow **direct knowledge injection** without LLM extraction.

### Fact Triple Structure

```
┌────────────┐         ┌──────────────┐         ┌────────────┐
│   SOURCE   │         │     EDGE     │         │   TARGET   │
│   (Node)   │────────▶│   (Fact)     │────────▶│   (Node)   │
└────────────┘         └──────────────┘         └────────────┘
    "Bob"              "LIKES"                  "bananas"
                   fact: "Bob likes bananas"
```

### Creating Fact Triples

```python
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge
import uuid
from datetime import datetime

# Define source node (existing)
source_node = EntityNode(
    uuid="existing-uuid-from-neo4j",  # Use existing UUID if node exists
    name="Don Branson",
    group_id="don_branson_resume_v3"
)

# Define target node (new)
target_node = EntityNode(
    uuid=str(uuid.uuid4()),  # Generate new UUID for new node
    name="Neo4j",
    group_id="don_branson_resume_v3"
)

# Define the edge (fact)
edge = EntityEdge(
    group_id="don_branson_resume_v3",
    source_node_uuid=source_node.uuid,
    target_node_uuid=target_node.uuid,
    created_at=datetime.now(),
    name="EXPERTISE_IN",
    fact="Don Branson has expertise in Neo4j graph databases"
)

# Save nodes and edge
await source_node.save(driver)
await target_node.save(driver)
await edge.save(driver)
```

### Fact Triple Behavior

- Graphiti attempts **deduplication** against existing nodes/edges
- Both nodes and edge must share the same `group_id`
- Useful for **structured data** where relationships are already known
- Bypasses LLM extraction pipeline

### MCP Server Fact Operations

When using graphiti-local MCP:

```python
# Delete a specific entity edge (fact)
delete_entity_edge(uuid="edge-uuid")

# Get a specific entity edge
get_entity_edge(uuid="edge-uuid")
```

---

# Part 3: Migration Reference

## 3.1 Episode-First Migration Strategy

**Recommended Approach:** Convert existing graph data into structured episodes for Graphiti ingestion.

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
def entity_to_episode(entity: dict) -> dict:
    """Convert a graph entity to a Graphiti episode."""
    return {
        "name": f"{entity['type']}_{entity['name'][:50]}",
        "episode_body": json.dumps({
            "entity_type": entity["type"],
            "entity_name": entity["name"],
            "observations": entity.get("observations", []),
            "relationships": entity.get("relationships", {}),
            "source": "migration",
            "migrated_at": datetime.now().isoformat()
        }),
        "source": EpisodeType.json,
        "source_description": "Migrated from source graph",
        "group_id": determine_group_id(entity["type"])
    }
```

## 3.2 Group ID Strategy for Migration

| group_id | Content Type | Migration Priority |
|----------|--------------|-------------------|
| `don_branson_resume_v3` | Resume, skills, work history | CRITICAL |
| `disney_knowledge_2025` | Disney org, tech, strategies | HIGH |
| `disney_interview_2025` | Interview insights, lessons | MEDIUM |
| `career_patterns` | Synthesized career patterns | LOW |

## 3.3 Validation Queries Post-Migration

```python
# Verify entity extraction
nodes = await search_nodes(
    query="Don Branson",
    group_ids=["don_branson_resume_v3"]
)

# Verify fact extraction
facts = await search_memory_facts(
    query="Neo4j experience",
    group_ids=["don_branson_resume_v3"]
)

# Verify episode count
episodes = await get_episodes(
    group_ids=["don_branson_resume_v3"]
)
print(f"Migrated episodes: {len(episodes)}")
```

## 3.4 Rollback Strategy

```python
# Clear a specific namespace
await graphiti.clear_graph(group_ids=["disney_knowledge_2025"])
```

**Note:** Source graph remains unchanged as read-only reference.

---

# Appendix A: MCP Server Tools Reference

| Tool | Description |
|------|-------------|
| `add_memory` | Add an episode to the graph |
| `search_nodes` | Search for entity nodes |
| `search_memory_facts` | Search for relationship facts |
| `get_episodes` | Retrieve episodes for a group |
| `delete_entity_edge` | Delete a specific fact/edge |
| `delete_episode` | Delete a specific episode |
| `get_entity_edge` | Retrieve a specific edge by UUID |
| `clear_graph` | Clear all data for specified group_ids |
| `get_status` | Check server and database status |

# Appendix B: Episode Type Summary

| Type | Format | Extraction Method |
|------|--------|-------------------|
| `text` | Plain string | LLM extracts entities and relationships |
| `message` | `speaker: message` | LLM processes conversational context |
| `json` | JSON object | LLM extracts from structured fields |

---

**Document Source:** Zep Documentation (qdrant-docs MCP)  
**Last Verified:** 2025-12-12 09:33 PST  
**Tools Used:** qdrant-docs (FastMCP):search_docs, mcp-server-time:get_current_time
