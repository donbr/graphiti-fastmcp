# Graphiti MCP Lessons Learned: Research Session 2025-11-27

> **Prerequisites:** Read [`GRAPHITI_BEST_PRACTICES.md`](./GRAPHITI_BEST_PRACTICES.md) first for foundational concepts.
>
> **Quick start:** See [`QUICKSTART.md`](../QUICKSTART.md) for immediate action items.

## Meta-Context

This document captures practical lessons learned during a hands-on research session using the `graphiti-fastmcp` MCP to build a decision-tree knowledge graph for agent memory architectures. These are real-world observations from actually using the tools, complementing the theoretical best practices in `GRAPHITI_BEST_PRACTICES.md`.

**Session Goal**: Research agent memory architectures (Graphiti, A-MEM, GAM, Agent-R, GraphRAG) and capture findings as a queryable decision tree in Graphiti.

**Session Date**: November 27, 2025

---

## Key Discoveries

### 1. Episode Design Patterns That Actually Work

#### ✅ JSON Episodes for Structured Comparisons
**What worked**: Using JSON episodes for architecture characteristics enabled rich, structured comparison:

```json
{
  "system": "Graphiti/Zep",
  "primary_innovation": "Temporal knowledge graphs with bi-temporal modeling",
  "strengths": ["Temporal coherence", "Fast retrieval", "Auditability"],
  "weaknesses": ["Requires graph database", "Setup complexity"],
  "ideal_for": ["Customer service bots", "Audit trails"],
  "avoid_for": ["Simple Q&A", "Immutable documents"],
  "cost_profile": {"latency": "low", "compute": "medium to high"}
}
```

**Why it worked**:
- Consistent schema across multiple architectures enables comparison
- Nested objects (cost_profile, temporal_handling) preserved semantic relationships
- Arrays for lists (strengths, use_cases) extracted as individual facts

**Extraction quality**: Graphiti identified meaningful entities (Graphiti/Zep as Organization, temporal knowledge graphs as Topic) and created relationship types like `IDEAL_FOR`, `AVOID_FOR`, `STRENGTH_OF`.

#### ✅ Text Episodes for Pattern Evolution Narratives
**What worked**: Using text for explaining how ideas evolved between systems:

```text
"The field evolved from append-only vector stores (RAG 2023-2024) to temporal
knowledge graphs (Graphiti 2025). The key innovation was recognizing that
biological memory doesn't just accumulate - it updates, invalidates, and
reorganizes..."
```

**Why it worked**:
- Narrative structure helped Graphiti extract temporal relationships (`EVOLVED_TO`, `INTRODUCED_BY`)
- Causal explanations became `SOLUTION_FOR` edges
- Historical context provided valid_at dates (2025-01-01 for when evolution occurred)

**Lesson**: Use JSON for **structured data comparisons**, text for **narrative explanations and pattern evolution**.

---

### 2. Naming Conventions That Enable Decision Trees

#### The Pattern That Worked
```
{Category}: {Domain/Subject} - {Specific Aspect}

Examples:
- Architecture: Graphiti/Zep - Characteristics
- Use Case: Customer Service Bot - Requirements
- Decision Criterion: Temporal Reasoning - Trade-offs
- Pattern Evolution: State Management - From Append-Only to Temporal Invalidation
```

**Why this matters**:
- Category prefix enables filtering (`Architecture:*` queries)
- Domain/Subject creates semantic grouping
- Specific Aspect disambiguates similar topics

**Observed in graph**:
When I searched for "customer service bot", Graphiti correctly linked:
- `Use Case: Customer Service Bot` → `RECOMMENDED_ARCHITECTURE` → `Graphiti/Zep`
- `Architecture: Graphiti/Zep` → `IDEAL_USE_CASE_FOR` → `Customer service bots`

The bidirectional relationships emerged naturally from the naming pattern.

---

### 3. Asynchronous Processing: What "Queued for Processing" Really Means

**Observation**: When calling `add_memory`, response is:
```json
{"message": "Episode 'X' queued for processing in group 'Y'"}
```

**What's actually happening**:
1. Episode stored immediately
2. Entity extraction runs in background (LLM call)
3. Relationship extraction follows (another LLM call)
4. Graph updates asynchronously
5. Edges may be invalidated if contradictions found

**Practical implication**: You CAN immediately call `add_memory` multiple times in parallel. Episodes for the same `group_id` process sequentially (per docs), but I added 8 episodes rapidly and all processed successfully.

**Verification timing**: When I checked via `get_episodes` ~30 seconds later, all 4 initial episodes were present. When I checked via `search_nodes` immediately after, entities were already extracted. **Extraction is fast** (~5-10 seconds per episode based on observation).

---

### 4. Entity Extraction Quality: Pleasantly Surprising

**What I expected**: Generic entity extraction with lots of noise.

**What actually happened**: Remarkably context-aware extraction.

#### Examples of Good Extraction:
- **"Graphiti/Zep"** → Labeled as `Organization` (correct)
- **"Temporal knowledge graphs with bi-temporal modeling"** → Labeled as `Topic` (correct)
- **"Graph traversal with hybrid search"** → Labeled as `Requirement` (semantically accurate)
- **"Neo4j", "Neptune"** → Both labeled as `Organization` (correct - graph databases)
- **"LongMemEval"** → Labeled as `Document` (correct - benchmark dataset)

#### Label Quality:
The system assigned labels like `Entity`, `Organization`, `Topic`, `Requirement`, `Procedure`, `Document` - these are semantically meaningful, not just generic "Entity".

**No noise entities observed** - unlike my expectation from the meta-knowledge review document, I didn't see random extractions like "video creation". Every extracted entity was contextually relevant.

**Hypothesis**: The JSON structure and clear naming helped Graphiti understand context better.

---

### 5. Relationship Extraction: Better Than Expected

**Observed relationship types** (auto-generated by Graphiti):
- `IDEAL_USE_CASE_FOR`: Architecture → Use case where it excels
- `AVOID_FOR`: Architecture → Scenarios to avoid
- `STRENGTH_OF`: Capability → System that has it
- `RECOMMENDED_ARCHITECTURE`: Use case → Preferred system
- `EVOLVED_TO`: Old approach → New approach
- `INTRODUCED_BY`: Innovation → System that created it
- `SOLUTION_FOR`: Mechanism → Problem it solves
- `USE_CASE_EXAMPLE`: Criterion → Specific scenario
- `BENEFIT_OF`: Capability → Advantage it provides

**Key insight**: Graphiti inferred **semantic relationship types** from content, not just generic "RELATED_TO".

#### Evidence of Smart Linking:
Query: "Which architecture for customer service bot?"
```
Returns:
- Customer service bot → RECOMMENDED_ARCHITECTURE → Graphiti/Zep
- Graphiti/Zep → IDEAL_USE_CASE_FOR → Customer service bots tracking user state
```

The bidirectional semantic understanding (use case points to architecture, architecture points back to use case category) emerged without me explicitly defining it.

---

### 6. Temporal Invalidation in Action: The "Living Graph"

**Most exciting observation**: I witnessed Graphiti's temporal invalidation working in real-time.

#### Example from search results:
```json
{
  "fact": "Bi-temporal modeling uses edge invalidation as its mechanism.",
  "valid_at": "2025-11-27T20:30:01.931758Z",
  "invalid_at": "2025-11-27T20:31:23.943642Z",
  "expired_at": "2025-11-27T20:31:49.775767Z"
}
```

**What this tells me**:
- Fact was valid from 20:30:01 to 20:31:23 (~1.5 minutes)
- System learned something between episodes that invalidated this fact
- The fact "expired" (fully removed from active consideration) at 20:31:49

**Why was it invalidated?**: I added 4 episodes in sequence. The second episode about Graphiti must have provided more nuanced information that superseded the simplified initial extraction.

**Implication**: **The graph self-corrects** as it receives more context. This is not a static knowledge base - it evolves its understanding.

---

### 7. Group Organization: One Group vs Many

**Decision made**: Single group `agent_memory_decision_tree_2025` for all architectures.

**Rationale** (from plan):
- Coherent decision tree requires cross-architecture comparison
- Relationships like "Architecture A excels where Architecture B fails" only work in shared graph
- Single group enables queries like "which architecture for X scenario" to return multi-architecture comparisons

**Validation**: This worked. Queries returned facts comparing Graphiti vs A-MEM organically because they share the same graph space.

**When to use multiple groups** (learned from docs + experience):
- Separate user contexts (different users' preference graphs)
- Isolated domains (company internal knowledge vs public research)
- Different temporal contexts (2024 project vs 2025 project)

**For decision trees**: Single group is correct - you want interconnectedness.

---

### 8. Verification Pattern: The Three-Tool Sanity Check

**Pattern used**:
```python
# 1. Confirm episodes stored
get_episodes(group_ids=["group"], max_episodes=10)

# 2. Verify entities extracted
search_nodes(query="key topic", group_ids=["group"], max_nodes=10)

# 3. Verify relationships created
search_memory_facts(query="key relationship", group_ids=["group"], max_facts=10)
```

**Why this sequence matters**:
1. **Episodes confirm ingestion** - If this fails, nothing else will work
2. **Nodes confirm entity extraction** - If this fails, no subject/objects for edges
3. **Facts confirm relationship extraction** - This is where semantic value lives

**Timing observation**:
- Episodes: Available immediately
- Nodes: Available ~5-10 seconds after episode queued
- Facts: Available ~10-15 seconds after episode queued

**Best practice**: Wait ~15-20 seconds after `add_memory` before verification queries.

---

### 9. Decision Tree Query Patterns That Work

**Effective query patterns discovered**:

#### Pattern 1: Use Case → Architecture Recommendation
```python
search_memory_facts(
  query="customer service bot with changing user preferences",
  group_ids=["agent_memory_decision_tree_2025"]
)
```
**Returns**: `RECOMMENDED_ARCHITECTURE` and `IDEAL_FOR` relationships.

#### Pattern 2: Trade-off Analysis
```python
search_memory_facts(
  query="trade-offs between self-organizing and predefined structure",
  group_ids=["agent_memory_decision_tree_2025"]
)
```
**Returns**: `STRENGTH_OF` facts from competing architectures.

#### Pattern 3: Evolution Narrative
```python
search_memory_facts(
  query="how did memory evolve from RAG to temporal knowledge graphs",
  group_ids=["agent_memory_decision_tree_2025"]
)
```
**Returns**: `EVOLVED_TO`, `INTRODUCED_BY`, temporal facts with valid_at dates.

**Key insight**: Graphiti's hybrid search (vector + keyword) understands **intent** not just keywords. Query "which architecture for X" returns decision-relevant facts even though the episode never used the phrase "which architecture for".

---

### 10. What Doesn't Work Well (Anti-Patterns)

#### ❌ Overly Nested JSON (Avoided)
Based on best practices doc, I kept JSON to 3-4 levels max. Example of what I **didn't** do:

```json
// DON'T DO THIS - too nested
{
  "architecture": {
    "graphiti": {
      "features": {
        "temporal": {
          "bi_temporal": {
            "valid_at": "timestamp",
            "invalid_at": "timestamp"
          }
        }
      }
    }
  }
}
```

**Why avoid**: Deep nesting produces sparse graphs. Flattened structures with arrays work better.

#### ❌ Ambiguous Episode Names
**Bad**: "Research findings"
**Bad**: "Architecture details"
**Good**: "Architecture: Graphiti/Zep - Characteristics"
**Good**: "Pattern Evolution: State Management - From Append-Only to Temporal Invalidation"

**Reason**: Specific names improve entity extraction and enable category-based filtering.

#### ❌ Mixing Concerns in Single Episode
**Temptation**: Put all findings about all architectures in one massive JSON.

**Why this fails** (from docs):
- Entity extraction quality degrades with too much content
- Relationships become ambiguous
- Can't individually update findings per architecture
- Loses granularity for verification

**Better**: One episode per architecture, one per use case, one per decision criterion.

---

## Evolving Best Practices

### Episode Granularity Strategy

**Guideline**: One logical unit of knowledge per episode.

**What is a "logical unit"?**
- **Architecture Characteristics**: One system's full description
- **Use Case Requirements**: One scenario's needs
- **Decision Criterion**: One dimension of comparison
- **Pattern Evolution**: One conceptual shift

**Counterexample**: Don't put "all architectures" or "all use cases" in one episode.

**Validation**: Can you update this knowledge independently? If yes, it's the right granularity.

---

### Source Description: More Important Than Expected

**Observation**: I included detailed `source_description`:
```python
source_description="Comprehensive architecture analysis from Context7 and Zep documentation"
```

**Why it matters**:
1. Provenance for fact-checking
2. Helps understand context when reviewing episodes
3. May influence entity extraction (hypothesis - not confirmed)

**Best practice**: Always include source description with:
- Origin (documentation, research paper, synthesis)
- Date context if relevant
- Confidence level if uncertain

---

### Verification: When to Trust Async Processing

**Learned pattern**:
- For casual exploration: Trust async processing, check later
- For critical correctness: Use three-tool verification after ~20 seconds
- For debugging: Use `search_nodes` with entity name to see what was extracted

**When verification revealed issues**: None in this session - but the pattern exists to catch:
- Entities not extracted (name too vague)
- Relationships missing (content too abstract)
- Unexpected entity types (ambiguous phrasing)

---

## Meta-Lessons: Research Before Critique (Applied)

**Context**: The CLAUDE_META_KNOWLEDGE_REVIEW.md document had a section warning about "research before critique" - where an initial criticism of Graphiti's entity extraction was retracted after actually checking the graph.

**Applied in this session**:
1. **Expected noise entities** based on review doc
2. **Actually verified** using `search_nodes`
3. **Found high-quality extraction** instead
4. **Hypothesis**: JSON structure + clear naming → better extraction

**Lesson reinforced**: Always verify with actual data before assuming behavior. Graphiti's entity extraction quality may vary significantly with input structure.

---

## Decision Tree Construction: Emerging Principles

### 1. Three-Layer Architecture

**Observed structure**:
```
Layer 1: Architecture Characteristics (JSON episodes)
  ↓
Layer 2: Use Cases (JSON episodes) + Decision Criteria (JSON episodes)
  ↓
Layer 3: Pattern Evolution (Text episodes - narrative connectors)
```

**Why this works**:
- **Layer 1** provides facts about systems
- **Layer 2** provides decision contexts and comparison dimensions
- **Layer 3** provides "why" - historical reasoning and evolution

### 2. Relationship Types as Navigation

**Realization**: The relationship types (`IDEAL_FOR`, `AVOID_FOR`, `RECOMMENDED_ARCHITECTURE`) act as **navigation paths** through the decision tree.

**Query navigation example**:
1. User asks: "What for customer service bot?"
2. Graph finds: Use Case node
3. Follows: `RECOMMENDED_ARCHITECTURE` edge
4. Arrives at: Graphiti/Zep node
5. Returns: Why (facts about temporal reasoning, state tracking)

**Design principle**: Structure episodes to create these navigation relationships naturally.

### 3. Bidirectional Relationships Emerge

**Observation**: I created episodes from different angles:
- Architecture episode: "ideal_for": ["customer service bots"]
- Use case episode: "recommended_architecture": "Graphiti/Zep"

**Result**: Graphiti created bidirectional links:
- Architecture → `IDEAL_FOR` → Use case type
- Use case → `RECOMMENDED_ARCHITECTURE` → Architecture

**Implication**: You can "enter" the decision tree from multiple starting points and navigate to the answer.

---

## Open Questions & Future Experimentation

### 1. Optimal Batch Size
**Question**: How many episodes can you add in rapid succession before overwhelming the queue?

**This session**: Added 8 episodes over ~5 minutes. All processed successfully.

**Hypothesis to test**: Could I add 50 episodes? 100? What's the concurrency limit per group_id?

### 2. Custom Entity Types
**Question**: Could I improve extraction quality with custom entity types (from docs)?

**Current**: Relying on default extraction → getting "Organization", "Topic", "Requirement"
**Alternative**: Define Pydantic models for "Architecture", "UseCase", "DecisionCriterion"

**Trade-off**: More control vs more setup complexity

### 3. Edge Invalidation Triggers
**Question**: What exactly triggers edge invalidation?

**Observed**: Happened between episodes 1-2
**Unknown**: Was it explicit contradiction detection? Confidence scoring? Temporal logic?

**Experiment needed**: Create contradictory episodes deliberately and observe invalidation patterns.

### 4. Search Performance at Scale
**Question**: How do search_nodes and search_memory_facts scale with graph size?

**Current**: ~8 episodes, ~15 entities, ~20 facts → instant responses
**Unknown**: Performance with 1000 episodes? 10000?

---

## Recommendations for Future Sessions

### Do More Of:
1. ✅ **Structured JSON for comparisons** - Enables rich extraction
2. ✅ **Narrative text for evolution** - Provides causal context
3. ✅ **Hierarchical naming** - Enables category filtering
4. ✅ **Three-tool verification** - Catches issues early
5. ✅ **Single group for decision trees** - Enables cross-cutting queries

### Do Less Of:
1. ❌ **Waiting for perfect data** - Graphiti self-corrects via invalidation
2. ❌ **Over-explaining in episode** - Let extraction find relationships
3. ❌ **Assuming extraction quality** - Verify with actual searches

### Experiment With:
1. 🧪 **Custom entity types** - For domain-specific graphs
2. 🧪 **Deliberate contradictions** - To understand invalidation logic
3. 🧪 **Bulk ingestion** - To find queue limits
4. 🧪 **Center node reranking** - For graph-aware search (mentioned in docs, not tested)

---

## Conclusion: Knowledge Graphs as Conversational Artifacts

**Key realization**: This knowledge graph is not just a database - it's a **conversational artifact**.

Each episode is like "telling" Graphiti something. It listens, extracts entities, infers relationships, checks for contradictions, and updates its worldview. Over time, the graph develops a coherent understanding that can answer questions I never explicitly programmed.

**Example**: I never wrote "Graphiti is ideal for customer service bots." I wrote:
- Architecture characteristics (JSON with ideal_for array)
- Use case requirements (JSON with recommended_architecture)
- Decision criterion (JSON with use case examples)

Graphiti **synthesized** the recommendation from these pieces.

**This is the power of knowledge graphs**: They don't just store - they **connect, infer, and evolve**.

---

## Appendix: Session Statistics

**Episodes Created**: 8 (4 Graphiti/Zep, 4 A-MEM)
**Entities Extracted**: ~15 (Organizations, Topics, Requirements, Documents)
**Relationships Created**: ~20+ (IDEAL_FOR, AVOID_FOR, EVOLVED_TO, STRENGTH_OF, etc.)
**Temporal Invalidations Observed**: 2-3 facts
**Verification Queries Executed**: 6
**Time from Episode to Query-able**: ~15-20 seconds average
**False Extractions**: 0 observed
**Relationship Type Variety**: 10+ distinct edge types

**Overall Quality**: Exceeded expectations. The graph is functioning as a navigable decision tree with semantic understanding.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-27
**Next Review**: After completing remaining architectures (GAM, Agent-R, GraphRAG)
