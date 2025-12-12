#!/usr/bin/env python3
"""
Populate the graphiti_meta_knowledge group with foundational Graphiti best practices.

This script creates 10 episodes covering:
1. Episode types (text/json/message) selection guide
2. JSON structure requirements and anti-patterns
3. Group ID namespacing strategy
4. Search operations (hybrid, reranking)
5. Async processing verification pattern
6. MCP tools context requirement
7. Episode naming conventions
8. Custom entity types
9. Knowledge lifecycle management
10. Anti-pattern: domain mixing

Run:
    uv run python examples/populate_meta_knowledge.py
"""

import asyncio
import json
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client

SERVER_URL = "http://localhost:8000/mcp/"
GROUP_ID = "graphiti_meta_knowledge"


def parse_response(result) -> dict | str:
    """Extract and parse JSON from tool result."""
    for content in result.content:
        if isinstance(content, types.TextContent):
            try:
                return json.loads(content.text)
            except json.JSONDecodeError:
                return content.text
    return str(result)


# Episode definitions
EPISODES = [
    # Episode 1: Episode Types Selection Guide
    {
        "name": "Lesson: Episode Types - Selecting Source Format",
        "episode_body": json.dumps({
            "id": "episode_types_001",
            "name": "Episode Type Selection Guide",
            "description": "When to use each episode type in Graphiti",
            "types": [
                {
                    "type": "text",
                    "use_for": "Unstructured narratives, articles, reports, freeform content",
                    "example": "Customer interaction transcripts, lessons learned"
                },
                {
                    "type": "message",
                    "use_for": "Conversational data with speaker attribution",
                    "example": "Support logs, dialogue transcripts (speaker: message pairs)"
                },
                {
                    "type": "json",
                    "use_for": "Structured data with clear schemas",
                    "example": "Identity records, certifications, project metadata"
                }
            ]
        }),
        "source": "json",
        "source_description": "Graphiti documentation - Episode types guide"
    },

    # Episode 2: JSON Structure Requirements
    {
        "name": "Lesson: JSON Ingestion - Structure Requirements",
        "episode_body": json.dumps({
            "id": "json_structure_001",
            "name": "JSON Structure Requirements",
            "description": "Guidelines for effective JSON episode ingestion",
            "practices": [
                {
                    "practice": "Keep JSON flat (3-4 levels max)",
                    "rationale": "Deeply nested JSON produces sparse graphs"
                },
                {
                    "practice": "Include identifying fields: id, name, description",
                    "rationale": "Enables proper entity extraction and linking"
                },
                {
                    "practice": "Use atomic attributes",
                    "rationale": "Separate fields vs compound strings enable better relationships"
                },
                {
                    "practice": "Split large objects into smaller episodes",
                    "rationale": "Unified entities per episode improve extraction quality"
                }
            ],
            "anti_patterns": [
                "5+ levels of nesting",
                "JSON without id/name/description fields",
                "Compound attributes like {contact_info: 'John - john@example.com'}",
                "Single massive JSON with all data"
            ]
        }),
        "source": "json",
        "source_description": "Graphiti documentation - JSON structure best practices"
    },

    # Episode 3: Group ID Strategy
    {
        "name": "Lesson: Graph Namespacing - Group ID Strategy",
        "episode_body": json.dumps({
            "id": "group_id_001",
            "name": "Group ID Organization Strategy",
            "description": "How to segment knowledge domains using group_id",
            "use_cases": [
                {
                    "type": "Multi-tenant systems",
                    "description": "Segregate data across customers/organizations"
                },
                {
                    "type": "Environment management",
                    "description": "Separate dev, test, production graphs"
                },
                {
                    "type": "Domain specialization",
                    "description": "Focused graphs for specific subject areas"
                },
                {
                    "type": "Meta-knowledge",
                    "description": "Reusable learnings across projects (e.g., graphiti_meta_knowledge)"
                }
            ],
            "best_practices": [
                "Use standardized naming conventions",
                "Document namespace structures",
                "Balance granularity appropriately",
                "Cross-namespace queries via application-level aggregation"
            ]
        }),
        "source": "json",
        "source_description": "Graphiti documentation - Graph namespacing guide"
    },

    # Episode 4: Search Operations
    {
        "name": "Lesson: Search Operations - Hybrid and Reranking",
        "episode_body": json.dumps({
            "id": "search_strategy_001",
            "name": "Search Strategy Guide",
            "description": "Effective search patterns in Graphiti",
            "methods": [
                {
                    "name": "Hybrid Search",
                    "description": "Combines semantic similarity with BM25 retrieval",
                    "use_case": "Broad retrieval of facts across knowledge graph"
                },
                {
                    "name": "Node Distance Reranking",
                    "description": "Prioritizes results by proximity to specified node",
                    "use_case": "Entity-focused queries, organizational hierarchies, cause-effect chains"
                }
            ],
            "reranking_options": [
                "RRF (Reciprocal Rank Fusion) - aggregates multiple algorithm results",
                "MMR (Maximal Marginal Relevance) - balances relevance with diversity",
                "Cross-Encoders - jointly encode query with results (OpenAI, Gemini, BGE)"
            ]
        }),
        "source": "json",
        "source_description": "Graphiti documentation - Search functionality guide"
    },

    # Episode 5: Async Processing Verification
    {
        "name": "Lesson: Async Processing - Verification Pattern",
        "episode_body": """Episodes in Graphiti are processed asynchronously. When add_memory returns "queued for processing", entity and fact extraction happens in background.

Three-Tool Verification Pattern:
1. get_episodes(group_ids=["your_group"]) - Confirm episode exists
2. search_nodes(query="key terms", group_ids=["your_group"]) - Verify entities extracted
3. search_memory_facts(query="key terms", group_ids=["your_group"]) - Verify relationships created

Allow brief delay (15-20 seconds) for background processing to complete before verification. This is especially important when immediately querying after adding episodes.""",
        "source": "text",
        "source_description": "Graphiti operational pattern - async verification"
    },

    # Episode 6: MCP Context Requirement
    {
        "name": "Lesson: MCP Tools - Context Requirement",
        "episode_body": """MCP tools like mcp__graphiti-local__add_memory are only accessible within Claude's context (Claude Code, Cursor with MCP configured).

Standalone Python scripts cannot directly call MCP tools through the mcp__ prefix. Options for programmatic access:
1. Use the MCP Python SDK with streamablehttp_client to connect to http://localhost:8000/mcp/
2. Implement MCP client connection using the mcp package
3. Use the REST API endpoints if available

This is a common source of confusion when testing Graphiti integrations. The MCP tools shown in Claude Code's tool list require the MCP server connection to be properly initialized.""",
        "source": "text",
        "source_description": "Graphiti integration pattern - MCP access methods"
    },

    # Episode 7: Episode Naming Convention
    {
        "name": "Preference: Episode Naming - Hierarchical Pattern",
        "episode_body": json.dumps({
            "id": "naming_convention_001",
            "name": "Episode Naming Convention",
            "description": "Standardized naming pattern for episodes",
            "pattern": "{Category}: {Topic} - {Specific Aspect}",
            "categories": [
                {"name": "Lesson:", "use": "Single insight from a session"},
                {"name": "Procedure:", "use": "Multi-step workflow that works"},
                {"name": "Anti-Pattern:", "use": "What NOT to do (with rationale)"},
                {"name": "Preference:", "use": "User-specific conventions"},
                {"name": "Best Practice:", "use": "Consolidated, stable guidance (validated across 3+ sessions)"},
                {"name": "Tool Usage:", "use": "How to effectively use specific tools"}
            ],
            "examples": [
                "Lesson: JSON Ingestion - Flattening Nested Data",
                "Procedure: Graph Verification - Three-Tool Pattern",
                "Anti-Pattern: Episode Design - Compound Attributes"
            ]
        }),
        "source": "json",
        "source_description": "Knowledge management convention - episode naming"
    },

    # Episode 8: Custom Entity Types
    {
        "name": "Lesson: Entity Extraction - Custom Types",
        "episode_body": json.dumps({
            "id": "custom_entities_001",
            "name": "Custom Entity Type Guide",
            "description": "Constraining entity extraction with Pydantic models",
            "when_to_use": [
                "Default extraction is too broad for your domain",
                "Need specific attributes on entities",
                "Want to filter results by entity type"
            ],
            "implementation": {
                "define_types": "entity_types = {'Product': ProductModel, 'Customer': CustomerModel}",
                "exclude_types": "await graphiti.add_episode(..., excluded_entity_types=['Topic'])",
                "filter_queries": "SearchFilters(node_labels=['Product', 'Customer'])"
            },
            "best_practices": [
                "Use PascalCase for type names, snake_case for attributes",
                "Include Field descriptions for LLM guidance",
                "Make attributes optional to handle missing info",
                "Define edge_type_map for valid relationships"
            ],
            "protected_names": ["uuid", "name", "group_id", "labels", "created_at", "summary", "attributes", "name_embedding"]
        }),
        "source": "json",
        "source_description": "Graphiti documentation - Custom entity types"
    },

    # Episode 9: Knowledge Lifecycle
    {
        "name": "Lesson: Meta-Knowledge - Lifecycle Management",
        "episode_body": """Knowledge Lifecycle in Graphiti:

Fine-grained episodes (Lesson:) -> patterns emerge -> Consolidated episodes (Best Practice:) -> temporal facts track evolution -> Updated episodes when knowledge changes

Key Principles:
- Label new knowledge as Lesson: initially
- Only promote to Best Practice: after patterns validated across 3+ sessions
- Add confidence attribute to source_description (e.g., "confidence: medium")
- Graphiti's temporal facts (valid_at, invalid_at) automatically handle evolution

Common Mistake: Consolidating immediately. "Best practices" created in same session as lessons are really "first impressions" - label them as Lesson: until validated.

The graphiti_meta_knowledge group should grow organically through actual usage, not be pre-populated with aspirational guidance.""",
        "source": "text",
        "source_description": "Meta-knowledge management - lifecycle pattern"
    },

    # Episode 10: Anti-Pattern - Domain Mixing
    {
        "name": "Anti-Pattern: Group Organization - Domain Mixing",
        "episode_body": """Anti-Pattern: Mixing unrelated knowledge domains in the same group_id.

Example Problem: Putting both "Graphiti usage best practices" and "Claude Agent SDK patterns" in the same group called "claude_meta_knowledge".

Consequences:
- Search pollution: Query for "best practices" returns both domains
- Maintenance burden: SDK updates require graph updates
- False confidence: Graph makes unvalidated patterns look authoritative

Solution: Use separate groups:
- graphiti_meta_knowledge: How to use Graphiti (self-referential, stable)
- claude_agent_sdk_patterns: SDK architecture guidance (external domain, version-dependent)

Rule: One group = one coherent knowledge domain. If knowledge requires different update frequencies or comes from different authority sources, use separate groups.""",
        "source": "text",
        "source_description": "Knowledge organization anti-pattern - domain mixing"
    }
]


async def main():
    print("=" * 60)
    print("Populating graphiti_meta_knowledge Group")
    print("=" * 60)
    print(f"Target group_id: {GROUP_ID}")
    print(f"Episodes to add: {len(EPISODES)}")
    print()

    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected to MCP server!\n")

            # Check server status
            result = await session.call_tool("get_status", arguments={})
            data = parse_response(result)
            print(f"Server status: {data.get('status', 'unknown')}")
            print()

            # Add each episode
            for i, episode in enumerate(EPISODES, 1):
                print(f"[{i}/{len(EPISODES)}] Adding: {episode['name']}")

                result = await session.call_tool(
                    "add_memory",
                    arguments={
                        "name": episode["name"],
                        "episode_body": episode["episode_body"],
                        "source": episode["source"],
                        "source_description": episode["source_description"],
                        "group_id": GROUP_ID
                    }
                )

                data = parse_response(result)
                message = data.get("message", str(data))
                print(f"    Result: {message[:60]}...")
                print()

            print("=" * 60)
            print("All episodes queued for processing!")
            print("=" * 60)
            print()
            print("NOTE: Entity extraction happens asynchronously.")
            print("Wait 30-60 seconds, then verify with:")
            print()
            print(f"  search_nodes(query='episode types', group_ids=['{GROUP_ID}'])")
            print(f"  search_memory_facts(query='JSON best practices', group_ids=['{GROUP_ID}'])")
            print(f"  get_episodes(group_ids=['{GROUP_ID}'])")


if __name__ == "__main__":
    asyncio.run(main())