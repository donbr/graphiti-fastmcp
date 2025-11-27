#!/usr/bin/env python3
"""
Example 3: Graphiti Knowledge Graph - All 9 Tools

Complete demonstration of all Graphiti MCP tools for knowledge graph operations.

GRAPHITI CONCEPTS:
- Episodes: Raw data stored in the graph (text, JSON, messages)
- Nodes: Entities extracted from episodes (people, places, concepts)
- Edges/Facts: Relationships between nodes with temporal metadata
- Groups: Namespaces for organizing data (group_id)

THE 9 TOOLS:
1. get_status         - Check server health
2. add_memory         - Store an episode
3. search_nodes       - Find entities
4. search_memory_facts - Find relationships
5. get_episodes       - List stored episodes
6. get_entity_edge    - Get edge by UUID
7. delete_episode     - Remove an episode
8. delete_entity_edge - Remove an edge
9. clear_graph        - Reset the graph

Run:
    uv run python examples/03_graphiti_memory.py
"""

import asyncio
import json
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client

SERVER_URL = "http://localhost:8000/mcp/"


def parse_response(result) -> dict | str:
    """Extract and parse JSON from tool result."""
    for content in result.content:
        if isinstance(content, types.TextContent):
            try:
                return json.loads(content.text)
            except json.JSONDecodeError:
                return content.text
    return str(result)


def print_section(number: int, title: str):
    """Print a formatted section header."""
    print(f"\n{'─' * 50}")
    print(f"{number}. {title}")
    print('─' * 50)


async def main():
    print("=" * 60)
    print("Graphiti Knowledge Graph: All 9 Tools")
    print("=" * 60)

    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected!")

            # ═══════════════════════════════════════════════════════════
            # TOOL 1: get_status - Check server health
            # ═══════════════════════════════════════════════════════════
            print_section(1, "get_status() - Check server health")

            result = await session.call_tool("get_status", arguments={})
            data = parse_response(result)
            print(f"Status: {data.get('status', 'unknown')}")
            print(f"Message: {data.get('message', 'N/A')}")

            # ═══════════════════════════════════════════════════════════
            # TOOL 2: add_memory - Store an episode
            # ═══════════════════════════════════════════════════════════
            print_section(2, "add_memory() - Store an episode")

            # Example: Add text content
            result = await session.call_tool(
                "add_memory",
                arguments={
                    "name": "Python MCP Tutorial",
                    "episode_body": "The Model Context Protocol (MCP) has three primitives: "
                                   "Tools for actions, Resources for data, and Prompts for "
                                   "LLM instructions. Graphiti uses Tools exclusively.",
                    "source": "text",
                    "source_description": "Tutorial notes",
                    "group_id": "tutorials"  # Optional: namespace
                }
            )
            data = parse_response(result)
            print(f"Result: {data.get('message', data)}")

            # Example: Add JSON content
            result = await session.call_tool(
                "add_memory",
                arguments={
                    "name": "MCP Tools Reference",
                    "episode_body": json.dumps({
                        "tools": ["get_status", "add_memory", "search_nodes"],
                        "purpose": "knowledge graph operations"
                    }),
                    "source": "json",
                    "source_description": "Structured reference data"
                }
            )
            data = parse_response(result)
            print(f"JSON Result: {data.get('message', data)}")

            # ═══════════════════════════════════════════════════════════
            # TOOL 3: search_nodes - Find entities
            # ═══════════════════════════════════════════════════════════
            print_section(3, "search_nodes() - Find entities")

            result = await session.call_tool(
                "search_nodes",
                arguments={
                    "query": "MCP protocol tools",
                    "max_nodes": 5
                    # Optional: "group_ids": ["tutorials"]
                    # Optional: "entity_types": ["Topic", "Document"]
                }
            )
            data = parse_response(result)
            nodes = data.get("result", data).get("nodes", [])
            print(f"Found {len(nodes)} nodes:")
            for node in nodes[:5]:
                print(f"  • {node.get('name', 'Unknown')}")
                if node.get('summary'):
                    print(f"    {node['summary'][:60]}...")

            # ═══════════════════════════════════════════════════════════
            # TOOL 4: search_memory_facts - Find relationships
            # ═══════════════════════════════════════════════════════════
            print_section(4, "search_memory_facts() - Find relationships")

            result = await session.call_tool(
                "search_memory_facts",
                arguments={
                    "query": "what covers or includes",
                    "max_facts": 5
                    # Optional: "center_node_uuid": "..." for graph proximity reranking
                }
            )
            data = parse_response(result)
            facts = data.get("result", data).get("facts", [])
            print(f"Found {len(facts)} facts:")
            for fact in facts[:5]:
                print(f"  • {fact.get('fact', fact.get('name', 'Unknown'))}")

            # ═══════════════════════════════════════════════════════════
            # TOOL 5: get_episodes - List stored episodes
            # ═══════════════════════════════════════════════════════════
            print_section(5, "get_episodes() - List stored episodes")

            result = await session.call_tool(
                "get_episodes",
                arguments={
                    "max_episodes": 5
                    # Optional: "group_ids": ["tutorials"]
                }
            )
            data = parse_response(result)
            episodes = data.get("result", data).get("episodes", [])
            print(f"Found {len(episodes)} episodes:")

            episode_uuid = None  # Store for later deletion demo
            for ep in episodes[:5]:
                print(f"  • {ep.get('name', 'Untitled')}")
                print(f"    UUID: {ep.get('uuid', 'N/A')[:20]}...")
                if not episode_uuid and ep.get('uuid'):
                    episode_uuid = ep['uuid']

            # ═══════════════════════════════════════════════════════════
            # TOOL 6: get_entity_edge - Get edge by UUID
            # ═══════════════════════════════════════════════════════════
            print_section(6, "get_entity_edge() - Get edge by UUID")

            # First, get a fact to find an edge UUID
            result = await session.call_tool(
                "search_memory_facts",
                arguments={"query": "any relationship", "max_facts": 1}
            )
            data = parse_response(result)
            facts = data.get("result", data).get("facts", [])

            if facts and facts[0].get('uuid'):
                edge_uuid = facts[0]['uuid']
                result = await session.call_tool(
                    "get_entity_edge",
                    arguments={"uuid": edge_uuid}
                )
                data = parse_response(result)
                print(f"Edge details: {json.dumps(data, indent=2)[:200]}...")
            else:
                print("No edges found to demonstrate get_entity_edge")

            # ═══════════════════════════════════════════════════════════
            # TOOL 7: delete_episode - Remove an episode (DEMO ONLY)
            # ═══════════════════════════════════════════════════════════
            print_section(7, "delete_episode() - Remove an episode")

            print("DEMO: delete_episode requires a valid UUID")
            print("Usage: await session.call_tool('delete_episode', {'uuid': '...'})")
            print("⚠️  This permanently removes the episode and orphaned nodes")

            # Uncomment to actually delete:
            # if episode_uuid:
            #     result = await session.call_tool(
            #         "delete_episode",
            #         arguments={"uuid": episode_uuid}
            #     )
            #     print(f"Deleted: {parse_response(result)}")

            # ═══════════════════════════════════════════════════════════
            # TOOL 8: delete_entity_edge - Remove an edge (DEMO ONLY)
            # ═══════════════════════════════════════════════════════════
            print_section(8, "delete_entity_edge() - Remove an edge")

            print("DEMO: delete_entity_edge requires a valid UUID")
            print("Usage: await session.call_tool('delete_entity_edge', {'uuid': '...'})")
            print("⚠️  This permanently removes the relationship")

            # ═══════════════════════════════════════════════════════════
            # TOOL 9: clear_graph - Reset the graph (DANGEROUS!)
            # ═══════════════════════════════════════════════════════════
            print_section(9, "clear_graph() - Reset the graph")

            print("⚠️  WARNING: clear_graph deletes ALL data!")
            print("Usage: await session.call_tool('clear_graph', {'group_ids': ['...']})")
            print("If group_ids not specified, clears the default group")

            # Uncomment to actually clear (DANGEROUS!):
            # result = await session.call_tool(
            #     "clear_graph",
            #     arguments={"group_ids": ["tutorials"]}  # Only clear specific group
            # )
            # print(f"Cleared: {parse_response(result)}")

            print("\n" + "=" * 60)
            print("All 9 Graphiti tools demonstrated!")
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
