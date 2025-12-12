# Neo4j Memory → Graphiti Migration Plan V2
## Documentation-Grounded Approach

**Last Verified:** 2025-12-12 10:46 PST  
**Documentation Sources:**
- Context7: `/getzep/graphiti` (188+ code snippets, Trust Score 8.4)
- qdrant-docs: Zep source (119 documents)
- Key Zep docs: Zep_0109 (Episodes), Zep_0112 (Namespacing), Zep_0035 (JSON Best Practices), Zep_0019 (Batch Processing), Zep_0113 (Searching)

---

## Executive Summary

This migration plan transfers ~300 entities and ~500 relationships from the MCP_DOCKER Neo4j Memory graph to the graphiti-local Temporal Knowledge Graph. The approach is grounded in official Graphiti/Zep documentation to ensure semantic consistency, proper embedding generation, and temporal tracking.

### Key Architectural Decision: Episode-First Migration

**From Zep_0109:**
> "Episodes represent a single data ingestion event. An episode is itself a node, and any nodes identified while ingesting the episode are related to the episode via MENTIONS edges. Episodes enable querying for information at a point in time and understanding the provenance of nodes and their edge relationships."

This means we **must not** directly copy entities/relationships. Instead, we convert source entities to episodes and let Graphiti's LLM extraction pipeline:
1. Extract entities automatically
2. Generate proper embeddings
3. Create temporal tracking (valid_at, invalid_at, expired_at)
4. Build community structures
5. Maintain provenance via episode links

---

## Source System Analysis

### MCP_DOCKER Neo4j Memory Graph (Verified 2025-12-12)

```
Entities: 300+ across 15+ types
- person: ~20 (Don Branson, recruiters, interviewers)
- Organization: ~25 (Disney, IBM, Apollo.io, etc.)
- Team: ~10 (DEEPT, OTE, Data Platform Team)
- Project: ~20 (kg_rememberall, GDELT, nsclc-pathways)
- Experience: ~10 (career history entries)
- Technology: ~15 (Neo4j, LangGraph, Prefect)
- Pattern: ~15 (architectural patterns)
- JobPosting: ~7 (Disney, Kizen, Whatnot, etc.)
- Architecture: ~5 (Medallion, Kappa, Data Mesh)
- research: ~5 (analysis documents)

Relationships: 500+ across 30+ types
- Professional: WORKS_FOR, LEADS, MEMBER_OF
- Content: AUTHORED, USES, IMPLEMENTS  
- Knowledge: DOCUMENTED_IN, APPLIES_TO
- Temporal: FOLLOWS, TRANSITIONED_TO
- Organizational: PART_OF, LOCATED_AT
```

### Limitations of Source System
- No embeddings (no vector search capability)
- No temporal tracking (no valid_at/invalid_at on relationships)
- Single namespace (no group_id isolation)
- Entity-first architecture (observations as array properties)

---

## Target System: graphiti-local

### Verified Status
```python
graphiti-local:get_status()
# Response: {"status":"ok","message":"Graphiti MCP server is running and connected to neo4j database"}
```

### Target Architecture Benefits
- **Episode-first**: LLM extraction ensures semantic consistency
- **Embeddings**: Auto-generated for semantic search
- **Temporal**: valid_at, invalid_at, expired_at on edges
- **Communities**: Auto-clustering via Leiden algorithm
- **Namespacing**: group_id isolation for multi-tenancy
- **Provenance**: Episodes track data source

---

## Episode Design Patterns (Documentation-Grounded)

### JSON Best Practices (From Zep_0035)

> "At a high level, ingestion of JSON into Zep works best when these criteria are met:
> 1. **JSON is not too large**: Large JSON should be divided into pieces
> 2. **JSON is not deeply nested**: Deeply nested JSON (more than 3 to 4 levels) should be flattened
> 3. **JSON is understandable in isolation**: Include all information needed to understand the data
> 4. **JSON represents a unified entity**: Ideally represent one concept per episode"

### Episode Types (From Zep_0109)

| Type | Use Case | Example |
|------|----------|---------|
| `text` | Unstructured narrative | Person bios, project descriptions |
| `message` | Conversational format | Interview transcripts, chat logs |
| `json` | Structured data | Credentials, job postings, skills |

### Recommended: Narrative Text Episodes

**Why narrative over structured JSON?**
1. LLM extracts relationships naturally from prose
2. Better entity resolution and deduplication
3. More natural embedding representations
4. Follows how Graphiti was designed to work

---

## Episode Conversion Templates

### Template 1: Person Entity (source="text")

**Source (Neo4j Memory):**
```json
{
  "name": "Don Branson",
  "type": "person",
  "observations": [
    "Author of kg_rememberall and nsclc-pathways repositories",
    "Email: dwbranson@gmail.com",
    "AI Engineer and Solutions Architect with 20+ years experience",
    "Specializes in knowledge graphs, GraphRAG, and agentic AI systems",
    "Neo4j Certified Professional",
    "Location: Fullerton CA, USA"
  ]
}
```

**Target (Graphiti Episode):**
```python
add_memory(
    name="Don Branson Profile",
    episode_body="""Don Branson is an AI Engineer and Solutions Architect with over 20 years 
of experience. He is the author of kg_rememberall and nsclc-pathways repositories on GitHub. 
His email is dwbranson@gmail.com and he is located in Fullerton, California, USA.

Don specializes in knowledge graphs, GraphRAG, and agentic AI systems. He holds the Neo4j 
Certified Professional certification and maintains an active LinkedIn profile. His work 
spans enterprise modernization, cloud architecture, and cutting-edge AI systems development.""",
    source="text",
    source_description="Migrated from Neo4j Memory - person entity",
    group_id="don_branson_career"
)
```

### Template 2: Organization Entity (source="text")

**Source:**
```json
{
  "name": "Disney Studios",
  "type": "Organization",
  "observations": [
    "Parent organization for studio-related teams",
    "Located in Glendale, California",
    "Multiple AI/ML hiring tracks active December 2025",
    "Data Platform Team interviewed Don Branson December 10, 2025"
  ]
}
```

**Target:**
```python
add_memory(
    name="Disney Studios Overview",
    episode_body="""Disney Studios is the parent organization for studio-related teams and 
is located in Glendale, California. The organization encompasses production, distribution, 
and data platform functions.

In December 2025, Disney Studios has multiple AI/ML hiring tracks active. The Ad Platforms 
team (Decisioning Fleet) is hiring ML Engineers. The Decision Science Team is recruiting via 
Korn Ferry. The Data Platform Team interviewed Don Branson on December 10, 2025.""",
    source="text",
    source_description="Migrated from Neo4j Memory - Organization entity",
    group_id="disney_knowledge"
)
```

### Template 3: Experience Entity (source="json")

**Structured data benefits from JSON format:**
```python
add_memory(
    name="Don Branson IBM Career",
    episode_body=json.dumps({
        "role": "Application Architect",
        "company": "IBM",
        "employment_type": "Direct and subcontractor",
        "tenure": {
            "total_years": 14,
            "subcontractor_period": "2010-2017 via CDI Corporation",
            "direct_period": "2017-2024"
        },
        "clients": [
            "Delta Airlines",
            "American Airlines",
            "Gilead Sciences",
            "General Motors",
            "New York State",
            "Ulta Beauty",
            "United Airlines"
        ],
        "key_projects": [
            "American Airlines Payload Modernization",
            "Delta Airlines Garage Coach",
            "IBM Clinical Trials Platform",
            "General Motors watsonx.ai Pilot"
        ]
    }),
    source="json",
    source_description="Migrated from Neo4j Memory - Experience entity",
    group_id="don_branson_career"
)
```

### Template 4: JobPosting Entity (source="json")

```python
add_memory(
    name="Disney Ad Platforms ML Engineer Role",
    episode_body=json.dumps({
        "title": "Senior Machine Learning Engineer, Ad Platforms",
        "company": "Disney",
        "team": "Ad Platforms -> Decisioning Fleet -> Selection Squad",
        "locations": ["Glendale", "San Francisco", "Santa Monica"],
        "work_arrangement": "4 days in office",
        "salary_range": {
            "min": 141900,
            "max": 208400,
            "currency": "USD",
            "includes": ["bonus", "LTIP"]
        },
        "requirements": [
            "LangGraph, Crew AI, strands sdk for developing agents",
            "Vector databases and retrieval-augmented generation (RAG)",
            "LLM-as-a-service (AWS Bedrock, Azure Cognitive Services, Vertex AI)",
            "Java proficiency plus Python",
            "Kafka and/or Kinesis streaming experience"
        ],
        "posted_date": "2025-12-02",
        "indeed_url": "https://to.indeed.com/nzzwl6gybt0p9"
    }),
    source="json",
    source_description="Migrated from Neo4j Memory - JobPosting entity",
    group_id="career_opportunities"
)
```

### Template 5: Pattern Entity (source="text")

```python
add_memory(
    name="SHACL Competency Questions Pattern",
    episode_body="""The SHACL Competency Questions Pattern provides precision in prompt 
engineering and data validation. Creating effective prompts is similar to ontology-based 
competency questions.

SHACL (Shapes Constraint Language) can identify when upstream datasets change significantly 
by detecting when data doesn't have the expected shape. This enables proactive detection of 
data quality issues before they impact downstream systems.

Don Branson has prior SHACL experience from a Healthcare/Life Sciences standards proposal. 
This pattern was identified during the Disney Interview Post-Mortem in December 2025, where 
it emerged as a key insight for solving upstream data source detection problems.""",
    source="text",
    source_description="Migrated from Neo4j Memory - Pattern entity",
    group_id="technical_patterns"
)
```

---

## group_id Namespace Strategy

### Mapping Based on Zep_0112 Namespacing Guidance

| group_id | Domain | Source Entity Types | Priority | Processing |
|----------|--------|---------------------|----------|------------|
| `don_branson_career` | Professional identity | person, Experience, Skills, Credentials, personal Projects | CRITICAL | Sequential |
| `disney_knowledge` | Disney context | Organization, Team, Person, Architecture, Strategy | HIGH | Batch-capable |
| `career_opportunities` | Job search | JobPosting, recruiter contacts, market analysis | MEDIUM | Sequential |
| `technical_patterns` | Reusable patterns | Pattern, Architecture, anti-patterns | MEDIUM | Batch-capable |
| `ai_engineering_research` | Technical research | Project, Technology, research | LOW | Batch-capable |

### Entity Classification Function

```python
def classify_entity_group(entity: dict) -> str:
    """Classify entity into appropriate group_id namespace."""
    name = entity.get("name", "")
    entity_type = entity.get("type", "")
    
    # CRITICAL: Career/Resume entities
    if name == "Don Branson":
        return "don_branson_career"
    if entity_type in ["Experience", "Skills", "Credentials"]:
        return "don_branson_career"
    if "Don Branson" in name:
        return "don_branson_career"
    
    # HIGH: Disney context
    if "Disney" in name or entity_type in ["BuyingCenter"]:
        return "disney_knowledge"
    if name in ["OTE", "DEEPT", "Content Genome", "OneID Identity Graph"]:
        return "disney_knowledge"
    
    # MEDIUM: Job search
    if entity_type == "JobPosting":
        return "career_opportunities"
    if "Role" in name or "Position" in name:
        return "career_opportunities"
    if entity_type == "Person" and any(x in str(entity.get("observations", [])) 
                                        for x in ["recruiter", "Recruiter"]):
        return "career_opportunities"
    
    # MEDIUM: Technical patterns
    if entity_type in ["Pattern", "Architecture"]:
        return "technical_patterns"
    if "Pattern" in name or "Anti-Pattern" in name:
        return "technical_patterns"
    
    # LOW: Everything else
    return "ai_engineering_research"
```

---

## Migration Execution Plan

### Phase 1: Preparation (1-2 hours)

**Step 1.1: Export Source Graph**
```python
# Via MCP
result = MCP_DOCKER:read_graph()
backup = {
    "exported_at": datetime.now().isoformat(),
    "entities": result["entities"],
    "relations": result["relations"]
}
# Save to /mnt/user-data/outputs/neo4j_memory_backup_2025-12-12.json
```

**Step 1.2: Verify Target System**
```python
status = graphiti-local:get_status()
# Expected: {"status":"ok","message":"Graphiti MCP server is running..."}

episodes = graphiti-local:get_episodes(max_episodes=5)
# Expected: Empty or minimal existing content
```

**Step 1.3: Prepare Classification**
- Implement entity classification function
- Create episode conversion functions for each template
- Set up logging and progress tracking

### Phase 2: Episode Generation (2-3 hours)

**Step 2.1: Convert Entities by Priority**

Processing order (sequential for critical, batch-capable for reference):
1. `don_branson_career` - ~50 episodes (SEQUENTIAL)
2. `disney_knowledge` - ~80 episodes (BATCH-CAPABLE)
3. `career_opportunities` - ~20 episodes (BATCH-CAPABLE)
4. `technical_patterns` - ~40 episodes (BATCH-CAPABLE)
5. `ai_engineering_research` - ~110 episodes (BATCH-CAPABLE)

**Step 2.2: Episode Size Validation**

Per Zep_0035, ensure each episode:
- Is less than 4KB
- Has ≤3-4 nesting levels for JSON
- Is understandable in isolation
- Represents a unified concept

```python
def validate_episode_size(episode_body: str) -> bool:
    """Validate episode meets size guidelines."""
    if len(episode_body.encode('utf-8')) > 4096:
        return False
    if episode_body.startswith('{'):
        try:
            data = json.loads(episode_body)
            depth = get_json_depth(data)
            if depth > 4:
                return False
        except:
            pass
    return True
```

### Phase 3: Migration Execution (4-8 hours)

**Step 3.1: Execute Critical Domain First**

```python
# don_branson_career - SEQUENTIAL processing
for entity in career_entities:
    episode = convert_to_episode(entity, "don_branson_career")
    
    result = graphiti-local:add_memory(
        name=episode["name"],
        episode_body=episode["body"],
        source=episode["source"],
        source_description=episode["description"],
        group_id="don_branson_career"
    )
    
    # Sequential: wait between each
    time.sleep(2)  # Allow LLM processing
    log_progress(entity["name"], result)
```

**Step 3.2: Execute Reference Domains**

From Zep_0019 on batch processing:
> "The batch method works with data with a temporal dimension... can process up to 20 episodes simultaneously"

```python
# disney_knowledge - BATCH-CAPABLE
batch_size = 10  # Conservative batch size
for batch in chunks(disney_entities, batch_size):
    for entity in batch:
        episode = convert_to_episode(entity, "disney_knowledge")
        graphiti-local:add_memory(...)
    
    # Pause between batches
    time.sleep(3)  # Allow LLM processing to complete
```

**Rate Limiting Guidelines:**
- Sequential domains: 1 episode, 2-second pause
- Batch domains: 10 episodes, 3-second pause between batches
- If errors occur: Implement exponential backoff (2s → 4s → 8s)

### Phase 4: Validation (2-3 hours)

**Step 4.1: Entity Count Validation**

```python
# Verify entity extraction per group_id
for group_id in ["don_branson_career", "disney_knowledge", "career_opportunities", 
                  "technical_patterns", "ai_engineering_research"]:
    
    # Get episodes
    episodes = graphiti-local:get_episodes(group_ids=[group_id], max_episodes=100)
    print(f"{group_id}: {len(episodes)} episodes")
    
    # Search for expected entities
    key_entities = get_expected_key_entities(group_id)
    for entity_name in key_entities:
        result = graphiti-local:search_nodes(
            query=entity_name,
            group_ids=[group_id],
            max_nodes=5
        )
        assert len(result) > 0, f"Missing: {entity_name} in {group_id}"
```

**Step 4.2: Relationship Extraction Validation**

```python
# Validate key facts were extracted
validation_queries = [
    ("Don Branson IBM experience", "don_branson_career"),
    ("Disney Content Genome technology", "disney_knowledge"),
    ("LangGraph agent development", "career_opportunities"),
    ("SHACL data validation", "technical_patterns"),
]

for query, group_id in validation_queries:
    facts = graphiti-local:search_memory_facts(
        query=query,
        group_ids=[group_id],
        max_facts=10
    )
    print(f"Query: {query}")
    print(f"Facts found: {len(facts)}")
    for fact in facts[:3]:
        print(f"  - {fact}")
```

**Step 4.3: Semantic Search Quality**

```python
# Test semantic similarity (should find related concepts)
semantic_tests = [
    ("graph database Neo4j experience", "don_branson_career"),  # Should find Don's Neo4j work
    ("streaming architecture real-time", "disney_knowledge"),    # Should find Kappa/Medallion
    ("agentic AI multi-agent systems", "technical_patterns"),   # Should find patterns
]

for query, group_id in semantic_tests:
    nodes = graphiti-local:search_nodes(
        query=query,
        group_ids=[group_id],
        max_nodes=5
    )
    print(f"Semantic: '{query}' → {[n['name'] for n in nodes]}")
```

### Phase 5: Documentation & Cleanup (30 min)

**Step 5.1: Document Semantic Drift**

LLM extraction may produce different entity names or merge/split entities.
Document any significant changes:

```markdown
## Semantic Drift Report

### Merged Entities
- "Don Branson Technical Skills" + "Don Branson Certifications" → "Don Branson Qualifications"

### Split Entities  
- "IBM Application Architect Career" → "IBM Subcontractor Period" + "IBM Direct Employment Period"

### Name Changes
- "Disney Studio Technology" → "Walt Disney Studios Technology"
```

**Step 5.2: Preserve Source Reference**

Keep original Neo4j Memory graph as read-only reference:
- Backup file: `/mnt/user-data/outputs/neo4j_memory_backup_2025-12-12.json`
- Do not delete source until validation complete
- May be useful for debugging semantic drift

---

## Rollback Procedure

From graphiti-local MCP tools:

```python
# Clear specific namespace if migration failed
graphiti-local:clear_graph(group_ids=["don_branson_career"])

# Clear all migrated namespaces
graphiti-local:clear_graph(group_ids=[
    "don_branson_career",
    "disney_knowledge", 
    "career_opportunities",
    "technical_patterns",
    "ai_engineering_research"
])
```

**Note:** This only affects Graphiti. Source Neo4j Memory graph remains intact.

---

## Skills & Capabilities Required

### Technical Skills

| Skill | Purpose | Proficiency |
|-------|---------|-------------|
| Python async/await | MCP tool invocation | Expert |
| JSON manipulation | Episode body construction | Intermediate |
| Neo4j Cypher | Source data extraction | Intermediate |
| Graphiti API | Target system operations | Intermediate |
| MCP Protocol | Tool communication | Intermediate |
| LLM behavior understanding | Anticipate extraction variance | Intermediate |

### Domain Knowledge

| Area | Purpose |
|------|---------|
| Knowledge graph architecture | Understand source/target differences |
| Vector databases | Comprehend embedding implications |
| Temporal knowledge graphs | Design episode temporal placement |
| Data migration patterns | Apply best practices |

### Operational Skills

| Skill | Purpose |
|-------|---------|
| Rate limiting management | Prevent LLM overload |
| Error handling | Graceful failure recovery |
| Logging/monitoring | Track migration progress |
| QA validation | Verify migration success |

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| LLM rate limiting | HIGH | MEDIUM | Batch processing with pauses |
| Semantic drift | MEDIUM | MEDIUM | Validation queries, drift documentation |
| Missing relationships | MEDIUM | LOW | Include relationship context in narratives |
| Entity deduplication issues | LOW | MEDIUM | Review merged entities post-migration |
| Graphiti connection failure | LOW | HIGH | Pre-validation, retry logic |

---

## Timeline Estimate

| Phase | Duration | Notes |
|-------|----------|-------|
| Preparation | 1-2 hours | Export, verify, setup |
| Episode Generation | 2-3 hours | Convert 300 entities |
| Migration Execution | 4-8 hours | LLM processing time dependent |
| Validation | 2-3 hours | Query verification |
| Documentation | 30 min | Drift report, cleanup |
| **Total** | **10-16 hours** | Elapsed time |

---

## Appendix: MCP Tool Reference

### Source System (MCP_DOCKER)
- `read_graph()` - Export all entities and relations
- `search_nodes(query)` - Find specific entities
- `open_nodes(names)` - Get entities by exact name

### Target System (graphiti-local)
- `add_memory(name, episode_body, source, source_description, group_id)` - Ingest episode
- `search_nodes(query, group_ids, max_nodes)` - Search entities
- `search_memory_facts(query, group_ids, max_facts)` - Search facts/edges
- `get_episodes(group_ids, max_episodes)` - Retrieve episodes
- `delete_episode(uuid)` - Remove single episode
- `clear_graph(group_ids)` - Clear namespace(s)
- `get_status()` - Verify connection

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-12-12 | Claude | Initial plan |
| 2.0 | 2025-12-12 | Claude | Documentation-grounded revision using Context7 + qdrant-docs |
