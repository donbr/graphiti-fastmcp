#!/usr/bin/env python3
"""
Export Graphiti graph episodes to JSON for backup and disaster recovery.

Usage:
    uv run python examples/export_graph.py --group agent_memory_decision_tree_2025 --output backups/
    uv run python examples/export_graph.py --group graphiti_meta_knowledge --output backups/
    uv run python examples/export_graph.py --all --output backups/ # not creating any output yet

The exported JSON can be used with import_graph.py to recreate the graph.
"""

import argparse
import asyncio
import json
from datetime import datetime
from pathlib import Path

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


async def get_all_group_ids(session: ClientSession) -> list[str]:
    """Get all available group IDs from server status."""
    result = await session.call_tool("get_status", arguments={})
    data = parse_response(result)
    return data.get("group_ids", [])


async def export_group(session: ClientSession, group_id: str, max_episodes: int = 100) -> dict:
    """Export all episodes from a group."""
    result = await session.call_tool(
        "get_episodes",
        arguments={"group_ids": [group_id], "max_episodes": max_episodes}
    )
    data = parse_response(result)

    episodes = data.get("episodes", [])

    return {
        "group_id": group_id,
        "exported_at": datetime.utcnow().isoformat() + "Z",
        "episode_count": len(episodes),
        "episodes": episodes
    }


async def main():
    parser = argparse.ArgumentParser(description="Export Graphiti graph episodes")
    parser.add_argument("--group", "-g", help="Group ID to export")
    parser.add_argument("--all", "-a", action="store_true", help="Export all groups")
    parser.add_argument("--output", "-o", default=".", help="Output directory")
    parser.add_argument("--max-episodes", "-m", type=int, default=100, help="Max episodes per group")
    args = parser.parse_args()

    if not args.group and not args.all:
        parser.error("Either --group or --all is required")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 60)
    print("Graphiti Graph Export")
    print("=" * 60)

    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected to MCP server!")
            print()

            if args.all:
                group_ids = await get_all_group_ids(session)
                print(f"Found {len(group_ids)} groups: {group_ids}")
            else:
                group_ids = [args.group]

            for group_id in group_ids:
                print(f"\nExporting: {group_id}")

                export_data = await export_group(session, group_id, args.max_episodes)

                filename = f"{group_id}.json"
                filepath = output_dir / filename

                with open(filepath, "w") as f:
                    json.dump(export_data, f, indent=2)

                print(f"  Episodes: {export_data['episode_count']}")
                print(f"  Output: {filepath}")

    print()
    print("=" * 60)
    print("Export complete!")
    print("=" * 60)
    print()
    print("To restore, run:")
    print(f"  uv run python examples/import_graph.py --input {output_dir}/<group>.json")


if __name__ == "__main__":
    asyncio.run(main())
