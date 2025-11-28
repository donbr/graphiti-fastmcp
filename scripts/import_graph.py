#!/usr/bin/env python3
"""
Import Graphiti graph episodes from JSON backup.

Usage:
    uv run python examples/import_graph.py --input backups/agent_memory_decision_tree_2025.json
    uv run python examples/import_graph.py --input backups/ --all

This restores episodes exported by export_graph.py. Entity and relationship
extraction happens asynchronously after import.

Note: This does NOT clear existing data. If you need a clean restore, first run:
    clear_graph(group_ids=["group_to_clear"])
"""

import argparse
import asyncio
import json
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


async def import_episode(session: ClientSession, episode: dict, group_id: str) -> str:
    """Import a single episode."""
    # Determine source type from episode metadata
    source = episode.get("source", "text")

    # Episode body might be stored as string or dict
    episode_body = episode.get("content", "")
    if isinstance(episode_body, dict):
        episode_body = json.dumps(episode_body)

    result = await session.call_tool(
        "add_memory",
        arguments={
            "name": episode.get("name", "Unnamed Episode"),
            "episode_body": episode_body,
            "source": source,
            "source_description": episode.get("source_description", "Restored from backup"),
            "group_id": group_id
        }
    )

    data = parse_response(result)
    return data.get("message", str(data))


async def import_file(session: ClientSession, filepath: Path, dry_run: bool = False) -> tuple[int, int]:
    """Import all episodes from a JSON file."""
    with open(filepath) as f:
        data = json.load(f)

    group_id = data.get("group_id", "imported")
    episodes = data.get("episodes", [])

    print(f"\nImporting: {filepath.name}")
    print(f"  Group: {group_id}")
    print(f"  Episodes: {len(episodes)}")
    print(f"  Exported at: {data.get('exported_at', 'unknown')}")

    if dry_run:
        print("  [DRY RUN - no changes made]")
        return len(episodes), 0

    success = 0
    failed = 0

    for i, episode in enumerate(episodes, 1):
        try:
            result = await import_episode(session, episode, group_id)
            print(f"  [{i}/{len(episodes)}] {episode.get('name', 'Unnamed')[:50]}...")
            success += 1
        except Exception as e:
            print(f"  [{i}/{len(episodes)}] FAILED: {episode.get('name', 'Unnamed')[:30]} - {e}")
            failed += 1

    return success, failed


async def main():
    parser = argparse.ArgumentParser(description="Import Graphiti graph episodes from backup")
    parser.add_argument("--input", "-i", required=True, help="Input file or directory")
    parser.add_argument("--all", "-a", action="store_true", help="Import all .json files in directory")
    parser.add_argument("--dry-run", "-n", action="store_true", help="Show what would be imported without making changes")
    args = parser.parse_args()

    input_path = Path(args.input)

    if args.all and input_path.is_dir():
        files = list(input_path.glob("*.json"))
    elif input_path.is_file():
        files = [input_path]
    else:
        print(f"Error: {input_path} not found or not a valid file/directory")
        return

    if not files:
        print(f"No JSON files found in {input_path}")
        return

    print("=" * 60)
    print("Graphiti Graph Import")
    print("=" * 60)
    print(f"Files to import: {len(files)}")
    if args.dry_run:
        print("MODE: Dry run (no changes will be made)")

    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print("Connected to MCP server!")

            total_success = 0
            total_failed = 0

            for filepath in files:
                success, failed = await import_file(session, filepath, args.dry_run)
                total_success += success
                total_failed += failed

    print()
    print("=" * 60)
    print("Import Summary")
    print("=" * 60)
    print(f"Total episodes processed: {total_success + total_failed}")
    print(f"Successful: {total_success}")
    print(f"Failed: {total_failed}")
    print()
    print("NOTE: Entity extraction happens asynchronously.")
    print("Wait 30-60 seconds, then verify with:")
    print("  search_nodes(query='<topic>', group_ids=['<group>'])")
    print("  search_memory_facts(query='<topic>', group_ids=['<group>'])")


if __name__ == "__main__":
    asyncio.run(main())
