#!/usr/bin/env python3
"""
Verify the graphiti_meta_knowledge group was populated correctly.

Run:
    uv run python examples/verify_meta_knowledge.py
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


async def main():
    print("=" * 60)
    print("Verifying graphiti_meta_knowledge Group")
    print("=" * 60)
    print()

    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected!\n")

            # 1. Get Episodes
            print("-" * 50)
            print("1. get_episodes() - Verify episodes exist")
            print("-" * 50)

            result = await session.call_tool(
                "get_episodes",
                arguments={
                    "group_ids": [GROUP_ID],
                    "max_episodes": 15
                }
            )
            data = parse_response(result)
            episodes = data.get("result", data).get("episodes", [])
            print(f"Found {len(episodes)} episodes:\n")
            for ep in episodes:
                print(f"  - {ep.get('name', 'Untitled')}")
            print()

            # 2. Search Nodes
            print("-" * 50)
            print("2. search_nodes() - Verify entities extracted")
            print("-" * 50)

            result = await session.call_tool(
                "search_nodes",
                arguments={
                    "query": "episode types JSON structure",
                    "group_ids": [GROUP_ID],
                    "max_nodes": 10
                }
            )
            data = parse_response(result)
            nodes = data.get("result", data).get("nodes", [])
            print(f"Found {len(nodes)} nodes:\n")
            for node in nodes:
                print(f"  - {node.get('name', 'Unknown')}")
                if node.get('summary'):
                    summary = node['summary'][:80] + "..." if len(node.get('summary', '')) > 80 else node.get('summary', '')
                    print(f"    {summary}")
            print()

            # 3. Search Facts
            print("-" * 50)
            print("3. search_memory_facts() - Verify relationships")
            print("-" * 50)

            result = await session.call_tool(
                "search_memory_facts",
                arguments={
                    "query": "best practices JSON verification",
                    "group_ids": [GROUP_ID],
                    "max_facts": 10
                }
            )
            data = parse_response(result)
            facts = data.get("result", data).get("facts", [])
            print(f"Found {len(facts)} facts:\n")
            for fact in facts:
                fact_text = fact.get('fact', fact.get('name', 'Unknown'))
                if len(fact_text) > 100:
                    fact_text = fact_text[:100] + "..."
                print(f"  - {fact_text}")
            print()

            # 4. Test specific queries
            print("-" * 50)
            print("4. Test specific queries")
            print("-" * 50)

            queries = [
                "How should I name episodes?",
                "What are anti-patterns to avoid?",
                "How do I verify async processing?"
            ]

            for query in queries:
                print(f"\nQuery: '{query}'")
                result = await session.call_tool(
                    "search_memory_facts",
                    arguments={
                        "query": query,
                        "group_ids": [GROUP_ID],
                        "max_facts": 3
                    }
                )
                data = parse_response(result)
                facts = data.get("result", data).get("facts", [])
                if facts:
                    for fact in facts[:2]:
                        fact_text = fact.get('fact', fact.get('name', 'No fact'))
                        if len(fact_text) > 80:
                            fact_text = fact_text[:80] + "..."
                        print(f"  -> {fact_text}")
                else:
                    print("  -> No facts found")

            print("\n" + "=" * 60)
            print("Verification complete!")
            print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())