#!/usr/bin/env python3
"""
Example 4: Understanding MCP Primitives

Educational example showing the three MCP primitives and how to discover
which ones a server supports.

MCP PRIMITIVES:

┌─────────────┬───────────────────────────────────────────────────────┐
│ TOOLS       │ Actions that perform computations or have side       │
│             │ effects. LLMs call tools to DO things.               │
│             │ Example: calculate(), search(), send_email()         │
├─────────────┼───────────────────────────────────────────────────────┤
│ RESOURCES   │ Read-only data sources. LLMs read resources to GET   │
│             │ information.                                         │
│             │ Example: config://settings, file:///data.json        │
├─────────────┼───────────────────────────────────────────────────────┤
│ PROMPTS     │ Pre-defined message templates for LLM interactions.  │
│             │ Standardize how LLMs are prompted for specific tasks.│
│             │ Example: review_code, summarize_document             │
└─────────────┴───────────────────────────────────────────────────────┘

WHY GRAPHITI ONLY HAS TOOLS:
Graphiti is an action-based API. Every operation modifies state (add, delete)
or performs computation (search). There's no static data to expose as Resources,
and no prompt templates needed.

Run:
    uv run python examples/04_mcp_concepts.py
"""

import asyncio
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

SERVER_URL = "http://localhost:8000/mcp/"


async def main():
    print("=" * 60)
    print("MCP Primitives: Tools, Resources, and Prompts")
    print("=" * 60)

    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected to Graphiti MCP server!\n")

            # ═══════════════════════════════════════════════════════════
            # DISCOVER: What does this server offer?
            # ═══════════════════════════════════════════════════════════
            print("Discovering server capabilities...\n")

            # ─────────────────────────────────────────────────────────
            # 1. TOOLS - Actions the server can perform
            # ─────────────────────────────────────────────────────────
            print("┌" + "─" * 58 + "┐")
            print("│ TOOLS - Actions (session.list_tools)                    │")
            print("└" + "─" * 58 + "┘")

            tools = await session.list_tools()
            print(f"Found {len(tools.tools)} tools:")
            for tool in tools.tools:
                print(f"  • {tool.name}")
            print()

            # ─────────────────────────────────────────────────────────
            # 2. RESOURCES - Data sources the server exposes
            # ─────────────────────────────────────────────────────────
            print("┌" + "─" * 58 + "┐")
            print("│ RESOURCES - Data (session.list_resources)               │")
            print("└" + "─" * 58 + "┘")

            try:
                resources = await session.list_resources()
                if resources.resources:
                    print(f"Found {len(resources.resources)} resources:")
                    for resource in resources.resources:
                        print(f"  • {resource.uri}")
                else:
                    print("No resources available.")
                    print("  → Graphiti doesn't expose static data as resources")
            except Exception as e:
                print(f"Resources not supported: {e}")
            print()

            # ─────────────────────────────────────────────────────────
            # 3. RESOURCE TEMPLATES - Dynamic resource patterns
            # ─────────────────────────────────────────────────────────
            print("┌" + "─" * 58 + "┐")
            print("│ RESOURCE TEMPLATES (session.list_resource_templates)    │")
            print("└" + "─" * 58 + "┘")

            try:
                templates = await session.list_resource_templates()
                if templates.resourceTemplates:
                    print(f"Found {len(templates.resourceTemplates)} templates:")
                    for tmpl in templates.resourceTemplates:
                        print(f"  • {tmpl.uriTemplate}")
                else:
                    print("No resource templates available.")
                    print("  → Graphiti doesn't use dynamic resource patterns")
            except Exception as e:
                print(f"Resource templates not supported: {e}")
            print()

            # ─────────────────────────────────────────────────────────
            # 4. PROMPTS - Pre-defined LLM interaction templates
            # ─────────────────────────────────────────────────────────
            print("┌" + "─" * 58 + "┐")
            print("│ PROMPTS - Templates (session.list_prompts)              │")
            print("└" + "─" * 58 + "┘")

            try:
                prompts = await session.list_prompts()
                if prompts.prompts:
                    print(f"Found {len(prompts.prompts)} prompts:")
                    for prompt in prompts.prompts:
                        print(f"  • {prompt.name}")
                else:
                    print("No prompts available.")
                    print("  → Graphiti doesn't provide prompt templates")
            except Exception as e:
                print(f"Prompts not supported: {e}")

            # ═══════════════════════════════════════════════════════════
            # SUMMARY
            # ═══════════════════════════════════════════════════════════
            print("\n" + "=" * 60)
            print("SUMMARY: Graphiti Server Capabilities")
            print("=" * 60)
            print(f"""
Graphiti exposes {len(tools.tools)} TOOLS because it's an action-based API:

  ✓ add_memory         → Action: Store data in graph
  ✓ search_nodes       → Action: Query the graph
  ✓ search_memory_facts → Action: Query relationships
  ✓ get_episodes       → Action: Retrieve stored data
  ✓ delete_episode     → Action: Remove data
  ✓ clear_graph        → Action: Reset the graph
  ... and more

Graphiti does NOT expose:
  ✗ Resources  → No static data to read
  ✗ Prompts    → No LLM templates needed

This is a design choice. Other MCP servers might expose all three
primitives depending on their purpose.
""")

            # ═══════════════════════════════════════════════════════════
            # WHEN TO USE EACH PRIMITIVE
            # ═══════════════════════════════════════════════════════════
            print("=" * 60)
            print("WHEN TO USE EACH PRIMITIVE (Server Design Guide)")
            print("=" * 60)
            print("""
Use TOOLS when:
  • Performing computations (calculate, search, analyze)
  • Modifying state (add, update, delete)
  • Making API calls (send email, post to API)
  • Running code or commands

Use RESOURCES when:
  • Exposing configuration files
  • Providing database content
  • Sharing static documents
  • Offering file system access

Use PROMPTS when:
  • Standardizing LLM instructions
  • Providing expert system templates
  • Guiding specific workflows
  • Creating reusable conversation starters

Remember: A server can expose any combination of these!
""")


if __name__ == "__main__":
    asyncio.run(main())
