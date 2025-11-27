#!/usr/bin/env python3
"""
Example 1: Connect to MCP Server and Discover Capabilities

The first step in any MCP client: connect, initialize, and see what's available.

KEY CONCEPTS:
- streamablehttp_client: Creates HTTP connection to MCP server
- ClientSession: Manages the MCP protocol conversation
- session.initialize(): REQUIRED - performs MCP handshake
- session.list_tools(): Discovers available tools

THE PATTERN:
    async with streamablehttp_client(url) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()  # Always first!
            # Now you can use the session...

Run:
    uv run python examples/01_connect_and_discover.py
"""

import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Server URL - Graphiti MCP server default endpoint
SERVER_URL = "http://localhost:8000/mcp/"


async def main():
    print("=" * 60)
    print("MCP Client: Connect and Discover")
    print("=" * 60)
    print(f"\nConnecting to: {SERVER_URL}")

    # STEP 1: Connect using HTTP transport
    # The streamablehttp_client returns (read_stream, write_stream, session_id)
    # We use async context manager for automatic cleanup
    async with streamablehttp_client(SERVER_URL) as (read, write, _):

        # STEP 2: Create a ClientSession to manage the MCP protocol
        async with ClientSession(read, write) as session:

            # STEP 3: Initialize - REQUIRED before any other operations
            # This performs the MCP handshake and capability negotiation
            await session.initialize()
            print("Connected successfully!\n")

            # STEP 4: Discover what the server offers
            # list_tools() returns a ListToolsResult with a .tools attribute
            tools = await session.list_tools()

            print(f"Found {len(tools.tools)} tools:\n")
            for tool in tools.tools:
                print(f"  {tool.name}")
                if tool.description:
                    # Show first line of description
                    desc = tool.description.split('\n')[0][:55]
                    print(f"    {desc}...")
                print()


if __name__ == "__main__":
    asyncio.run(main())
