#!/usr/bin/env python3
"""
Re-import all FalkorDB Cloud graphs after fixing embedding dimension mismatch.

This script automates the full resolution process for Issue #14:
1. Export fresh backups (optional, uses existing if available)
2. Clear affected graphs
3. Re-import episodes with 1024-dim embeddings
4. Verify search functionality

Prerequisites:
- graphiti-core Bug #2 (vector parameter type mismatch) must be fixed
- MCP server must be running at http://localhost:8000/mcp/
- API keys configured for LLM provider (episode extraction)

Usage:
    # Dry run (shows what would be done)
    uv run scripts/re_import_all_graphs.py --dry-run

    # Execute with existing backups
    uv run scripts/re_import_all_graphs.py --backup-dir backups/

    # Export fresh backups first
    uv run scripts/re_import_all_graphs.py --backup-dir backups/ --fresh-export

    # Skip verification (faster, but not recommended)
    uv run scripts/re_import_all_graphs.py --backup-dir backups/ --no-verify

Related:
- Issue: https://github.com/donbr/graphiti-fastmcp/issues/14
- Analysis: docs/ISSUE_14_RESOLUTION_ANALYSIS.md
"""

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

from mcp import ClientSession, types
from mcp.client.streamable_http import streamablehttp_client

SERVER_URL = 'http://localhost:8000/mcp/'

# Graphs to re-import (from Issue #14)
GRAPHS_TO_REIMPORT = [
    {'group_id': 'graphiti_meta_knowledge', 'episodes': 65, 'entities': 328, 'facts': 809},
    {'group_id': 'default_db', 'episodes': 89, 'entities': 448, 'facts': 1000},
    {'group_id': 'main', 'episodes': 23, 'entities': 31, 'facts': 50},
]


def parse_response(result) -> dict | str:
    """Extract and parse JSON from tool result."""
    for content in result.content:
        if isinstance(content, types.TextContent):
            try:
                return json.loads(content.text)
            except json.JSONDecodeError:
                return content.text
    return str(result)


async def check_server_status(session: ClientSession) -> bool:
    """Check if MCP server is healthy and responding."""
    try:
        result = await session.call_tool('get_status', arguments={})
        data = parse_response(result)
        if isinstance(data, dict) and data.get('status') == 'healthy':
            print('✅ MCP server is healthy')
            return True
        print(f'⚠️  MCP server status: {data}')
        return False
    except Exception as e:
        print(f'❌ Failed to connect to MCP server: {e}')
        return False


async def export_graph(
    session: ClientSession, group_id: str, output_dir: Path, max_episodes: int = 200
) -> Path | None:
    """Export a single graph to JSON."""
    print(f'  Exporting {group_id}...')

    try:
        result = await session.call_tool(
            'get_episodes', arguments={'group_ids': [group_id], 'max_episodes': max_episodes}
        )
        data = parse_response(result)
        episodes = data.get('episodes', [])

        if not episodes:
            print(f'    ⚠️  No episodes found in {group_id}')
            return None

        export_data = {
            'group_id': group_id,
            'exported_at': datetime.utcnow().isoformat() + 'Z',
            'episode_count': len(episodes),
            'episodes': episodes,
        }

        filepath = output_dir / f'{group_id}.json'
        with open(filepath, 'w') as f:
            json.dump(export_data, f, indent=2)

        print(f'    ✅ Exported {len(episodes)} episodes to {filepath}')
        return filepath

    except Exception as e:
        print(f'    ❌ Export failed: {e}')
        return None


async def clear_graph(session: ClientSession, group_id: str, dry_run: bool = False) -> bool:
    """Clear all data in a graph."""
    print(f'  Clearing {group_id}...')

    if dry_run:
        print(f'    [DRY RUN] Would clear {group_id}')
        return True

    try:
        result = await session.call_tool('clear_graph', arguments={'group_ids': [group_id]})
        data = parse_response(result)
        print(f'    ✅ Cleared {group_id}')
        return True
    except Exception as e:
        print(f'    ❌ Clear failed: {e}')
        return False


async def import_episode(session: ClientSession, episode: dict, group_id: str) -> bool:
    """Import a single episode."""
    try:
        source = episode.get('source', 'text')
        episode_body = episode.get('content', '')
        if isinstance(episode_body, dict):
            episode_body = json.dumps(episode_body)

        result = await session.call_tool(
            'add_memory',
            arguments={
                'name': episode.get('name', 'Unnamed Episode'),
                'episode_body': episode_body,
                'source': source,
                'source_description': episode.get('source_description', 'Restored from backup'),
                'group_id': group_id,
            },
        )

        data = parse_response(result)
        return True
    except Exception as e:
        print(f'      ❌ Failed: {e}')
        return False


async def import_graph(
    session: ClientSession, backup_file: Path, dry_run: bool = False
) -> tuple[int, int]:
    """Import all episodes from a backup file."""
    print(f'  Importing from {backup_file.name}...')

    with open(backup_file) as f:
        data = json.load(f)

    group_id = data.get('group_id', 'imported')
    episodes = data.get('episodes', [])

    print(f'    Episodes: {len(episodes)}')
    print(f'    Exported at: {data.get("exported_at", "unknown")}')

    if dry_run:
        print(f'    [DRY RUN] Would import {len(episodes)} episodes')
        return len(episodes), 0

    success = 0
    failed = 0

    for i, episode in enumerate(episodes, 1):
        if i % 10 == 0 or i == len(episodes):
            print(f'    Progress: {i}/{len(episodes)}', end='\r')

        if await import_episode(session, episode, group_id):
            success += 1
        else:
            failed += 1
            print(f'    [{i}/{len(episodes)}] FAILED: {episode.get("name", "Unnamed")[:40]}')

    print(f'    ✅ Imported {success}/{len(episodes)} episodes successfully')
    if failed > 0:
        print(f'    ⚠️  {failed} episodes failed')

    return success, failed


async def verify_graph(session: ClientSession, group_id: str, expected_episodes: int) -> bool:
    """Verify that episodes were imported and entities extracted."""
    print(f'  Verifying {group_id}...')

    # Wait for async processing
    print('    Waiting 20 seconds for entity extraction...')
    await asyncio.sleep(20)

    try:
        # Check episodes
        result = await session.call_tool(
            'get_episodes', arguments={'group_ids': [group_id], 'max_episodes': 10}
        )
        data = parse_response(result)
        episodes = data.get('episodes', [])

        if not episodes:
            print(f'    ❌ No episodes found after import')
            return False

        print(f'    ✅ Episodes imported: {len(episodes)}+ (showing first 10)')

        # Check entities (search_nodes)
        result = await session.call_tool(
            'search_nodes', arguments={'query': 'test query', 'group_ids': [group_id], 'max_nodes': 5}
        )
        data = parse_response(result)
        nodes = data.get('nodes', [])

        if not nodes:
            print(f'    ⚠️  No entities found (may still be extracting)')
        else:
            print(f'    ✅ Entities extracted: {len(nodes)}+ nodes found')

        # Check facts (search_memory_facts)
        result = await session.call_tool(
            'search_memory_facts',
            arguments={'query': 'test query', 'group_ids': [group_id], 'max_facts': 5},
        )
        data = parse_response(result)
        facts = data.get('facts', [])

        if not facts:
            print(f'    ⚠️  No facts found (may still be extracting)')
        else:
            print(f'    ✅ Facts extracted: {len(facts)}+ facts found')

        return True

    except Exception as e:
        print(f'    ❌ Verification failed: {e}')
        return False


async def main():
    parser = argparse.ArgumentParser(
        description='Re-import all FalkorDB Cloud graphs (Issue #14)'
    )
    parser.add_argument(
        '--backup-dir', '-b', default='backups', help='Backup directory (default: backups/)'
    )
    parser.add_argument(
        '--fresh-export', '-f', action='store_true', help='Export fresh backups before re-import'
    )
    parser.add_argument('--dry-run', '-n', action='store_true', help='Dry run (no changes)')
    parser.add_argument('--no-verify', action='store_true', help='Skip verification step')
    parser.add_argument(
        '--max-episodes', '-m', type=int, default=200, help='Max episodes to export per graph'
    )
    args = parser.parse_args()

    backup_dir = Path(args.backup_dir)
    backup_dir.mkdir(parents=True, exist_ok=True)

    print('=' * 70)
    print('FalkorDB Cloud Graph Re-import (Issue #14)')
    print('=' * 70)
    print(f'Backup directory: {backup_dir}')
    print(f'Graphs to process: {len(GRAPHS_TO_REIMPORT)}')
    if args.dry_run:
        print('MODE: Dry run (no changes will be made)')
    print()

    async with streamablehttp_client(SERVER_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            print('Connected to MCP server!')
            print()

            # Check server health
            if not await check_server_status(session):
                print('❌ MCP server is not healthy. Aborting.')
                return 1

            print()

            # Phase 1: Export (if requested)
            if args.fresh_export:
                print('-' * 70)
                print('Phase 1: Exporting fresh backups')
                print('-' * 70)
                for graph_info in GRAPHS_TO_REIMPORT:
                    group_id = graph_info['group_id']
                    await export_graph(session, group_id, backup_dir, args.max_episodes)
                print()
            else:
                print('Skipping fresh export (using existing backups)')
                print()

            # Phase 2: Clear graphs
            print('-' * 70)
            print('Phase 2: Clearing affected graphs')
            print('-' * 70)
            for graph_info in GRAPHS_TO_REIMPORT:
                group_id = graph_info['group_id']
                await clear_graph(session, group_id, args.dry_run)
            print()

            if args.dry_run:
                print('[DRY RUN] Stopping before import phase')
                return 0

            # Phase 3: Re-import
            print('-' * 70)
            print('Phase 3: Re-importing episodes')
            print('-' * 70)
            total_success = 0
            total_failed = 0

            for graph_info in GRAPHS_TO_REIMPORT:
                group_id = graph_info['group_id']
                backup_file = backup_dir / f'{group_id}.json'

                if not backup_file.exists():
                    print(f'  ⚠️  Backup file not found: {backup_file}')
                    continue

                success, failed = await import_graph(session, backup_file)
                total_success += success
                total_failed += failed

            print()

            # Phase 4: Verify (if not skipped)
            if not args.no_verify:
                print('-' * 70)
                print('Phase 4: Verification')
                print('-' * 70)
                for graph_info in GRAPHS_TO_REIMPORT:
                    group_id = graph_info['group_id']
                    expected = graph_info['episodes']
                    await verify_graph(session, group_id, expected)
                print()

    print('=' * 70)
    print('Summary')
    print('=' * 70)
    print(f'Total episodes imported: {total_success}')
    print(f'Failed: {total_failed}')
    print()
    print('✅ Re-import complete!')
    print()
    print('Next steps:')
    print('  1. Run full verification: uv run scripts/verify_meta_knowledge.py')
    print('  2. Test search functionality in production')
    print('  3. Close Issue #14 if all acceptance criteria met')

    return 0 if total_failed == 0 else 1


if __name__ == '__main__':
    sys.exit(asyncio.run(main()))
