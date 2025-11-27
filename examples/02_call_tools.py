#!/usr/bin/env python3
"""
Example 2: Call Tools on MCP Server

After discovering tools, call them with arguments and handle responses.

KEY CONCEPTS:
- session.call_tool(name, arguments): Execute a tool
- Tool results contain .content (list of content items)
- types.TextContent: Most common response type
- JSON parsing: Graphiti returns JSON strings in TextContent

RESPONSE STRUCTURE:
    result = await session.call_tool("tool_name", {"arg": "value"})
    result.content         # List of content items
    result.structuredContent  # Direct dict (newer MCP spec)
    result.isError         # True if tool execution failed

Run:
    uv run python examples/02_call_tools.py
"""

import asyncio
import json
from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client

SERVER_URL = "http://localhost:8000/mcp/"


def parse_tool_result(result) -> dict | str:
    """
    Helper to extract data from tool results.

    Most Graphiti tools return JSON inside TextContent.
    This helper extracts and parses it.
    """
    for content in result.content:
        if isinstance(content, types.TextContent):
            try:
                return json.loads(content.text)
            except json.JSONDecodeError:
                return content.text
    return str(result)


async def main():
    print("=" * 60)
    print("MCP Client: Call Tools")
    print("=" * 60)

    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected!\n")

            # ─────────────────────────────────────────────────────────
            # Example 1: Tool with NO arguments
            # ─────────────────────────────────────────────────────────
            print("-" * 40)
            print("1. Calling: get_status()")
            print("-" * 40)

            # call_tool takes tool name and arguments dict
            result = await session.call_tool("get_status", arguments={})

            # Parse and display the response
            data = parse_tool_result(result)
            print(json.dumps(data, indent=2))
            print()

            # ─────────────────────────────────────────────────────────
            # Example 2: Tool WITH arguments
            # ─────────────────────────────────────────────────────────
            print("-" * 40)
            print("2. Calling: search_nodes(query='AI', max_nodes=3)")
            print("-" * 40)

            result = await session.call_tool(
                "search_nodes",
                arguments={
                    "query": "AI",       # Required: search query
                    "max_nodes": 3       # Optional: limit results
                }
            )

            data = parse_tool_result(result)

            # Handle the response structure
            if isinstance(data, dict):
                nodes = data.get("result", data).get("nodes", [])
                print(f"Found {len(nodes)} nodes:")
                for node in nodes:
                    print(f"  - {node.get('name', 'Unknown')}")
            else:
                print(data)
            print()

            # ─────────────────────────────────────────────────────────
            # Example 3: Using structuredContent (newer MCP spec)
            # ─────────────────────────────────────────────────────────
            print("-" * 40)
            print("3. Calling: search_memory_facts(query='learning')")
            print("-" * 40)

            result = await session.call_tool(
                "search_memory_facts",
                arguments={
                    "query": "learning",
                    "max_facts": 3
                }
            )

            # structuredContent provides direct dict access (if supported)
            if result.structuredContent:
                print("Using structuredContent:")
                facts = result.structuredContent.get("result", {}).get("facts", [])
                for fact in facts:
                    print(f"  - {fact.get('fact', 'Unknown')}")
            else:
                # Fall back to parsing TextContent
                data = parse_tool_result(result)
                print(json.dumps(data, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
