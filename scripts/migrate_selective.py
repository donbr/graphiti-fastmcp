#!/usr/bin/env python3
"""
Selective migration: Import only canonical episodes where graph name matches group_id.

This avoids duplicates by only importing episodes from their "home" graph:
- graphiti_meta_knowledge graph → episodes with group_id="graphiti_meta_knowledge"
- agent_memory_decision_tree_2025 graph → episodes with group_id="agent_memory_decision_tree_2025"
- main graph → episodes with group_id="main" or "tutorials"

Usage:
    uv run python scripts/migrate_selective.py --dry-run  # Preview
    uv run python scripts/migrate_selective.py            # Execute
"""

import argparse
import os
from datetime import datetime

from falkordb import FalkorDB

# FalkorDB Cloud connection
FALKORDB_HOST = os.getenv('FALKORDB_HOST', 'r-6jissuruar.instance-ebqwfrd4o.hc-2uaqqpjgg.us-east-2.aws.f2e0a955bb84.cloud')
FALKORDB_PORT = int(os.getenv('FALKORDB_PORT', '57857'))
FALKORDB_USER = os.getenv('FALKORDB_USER', 'falkordb')
FALKORDB_PASSWORD = os.getenv('FALKORDB_PASSWORD', 'graphitiKG1!')

# Migration map: source_graph → list of group_ids to import
MIGRATION_MAP = {
    'graphiti_meta_knowledge': ['graphiti_meta_knowledge'],
    'agent_memory_decision_tree_2025': ['agent_memory_decision_tree_2025'],
    'main': ['main', 'tutorials']
}

TARGET_GRAPH = 'default_db'


def connect_falkordb():
    """Connect to FalkorDB Cloud."""
    print(f'Connecting to FalkorDB at {FALKORDB_HOST}:{FALKORDB_PORT}...')
    client = FalkorDB(
        host=FALKORDB_HOST,
        port=FALKORDB_PORT,
        username=FALKORDB_USER,
        password=FALKORDB_PASSWORD
    )
    print('✅ Connected to FalkorDB\n')
    return client


def copy_graph_data(client, source_graph: str, target_graph: str, group_ids: list[str], dry_run: bool = False):
    """Copy nodes and edges for specific group_ids from source to target graph."""
    print(f'{"[DRY RUN] " if dry_run else ""}Copying from "{source_graph}" → "{target_graph}"')
    print(f'  Group IDs: {", ".join(group_ids)}')

    source = client.select_graph(source_graph)
    target = client.select_graph(target_graph)

    group_filter = '", "'.join(group_ids)

    # Count episodes to migrate
    result = source.query(f'''
        MATCH (e:Episodic)
        WHERE e.group_id IN ["{group_filter}"]
        RETURN count(e) as count
    ''')
    episode_count = result.result_set[0][0] if result.result_set else 0

    # Count total nodes for these episodes
    result = source.query(f'''
        MATCH (e:Episodic)-[*0..1]-(n)
        WHERE e.group_id IN ["{group_filter}"]
        RETURN count(DISTINCT n) as count
    ''')
    node_count = result.result_set[0][0] if result.result_set else 0

    print(f'  Episodes: {episode_count}')
    print(f'  Connected nodes: ~{node_count}')

    if dry_run:
        return {
            'episodes': episode_count,
            'nodes': node_count
        }

    # Copy all nodes (we'll filter by group_id on query)
    print(f'  Copying nodes...')
    result = source.query(f'''
        MATCH (n)
        WHERE EXISTS((n:Episodic)) AND n.group_id IN ["{group_filter}"]
           OR EXISTS((n)-[]-(e:Episodic)) AND e.group_id IN ["{group_filter}"]
        RETURN n
    ''')

    nodes_created = 0
    node_uuid_map = {}  # Track UUIDs for edge creation

    for record in result.result_set:
        node = record[0]
        uuid = dict(node.properties).get('uuid') if hasattr(node, 'properties') else None

        if uuid:
            node_uuid_map[uuid] = True

        # Build CREATE statement
        labels = ':'.join(node.labels)
        props = dict(node.properties) if hasattr(node, 'properties') else {}

        props_parts = []
        for k, v in props.items():
            if isinstance(v, str):
                v_escaped = v.replace('"', '\\"').replace('\n', '\\n')
                props_parts.append(f'{k}: "{v_escaped}"')
            elif isinstance(v, (int, float, bool)):
                props_parts.append(f'{k}: {str(v).lower() if isinstance(v, bool) else v}')

        props_str = '{' + ', '.join(props_parts) + '}' if props_parts else ''

        try:
            target.query(f'CREATE (:{labels} {props_str})')
            nodes_created += 1
        except Exception as e:
            if 'already exists' not in str(e).lower():
                print(f'    ⚠️  Error creating node: {e}')

    print(f'  ✓ Created {nodes_created} nodes')

    # Copy edges between migrated nodes
    print(f'  Copying edges...')
    result = source.query(f'''
        MATCH (e:Episodic)-[*0..2]-(s)-[r]->(t)
        WHERE e.group_id IN ["{group_filter}"]
        RETURN s.uuid as source_uuid, type(r) as rel_type, r, t.uuid as target_uuid
    ''')

    edges_created = 0
    for record in result.result_set:
        source_uuid = record[0]
        rel_type = record[1]
        edge = record[2]
        target_uuid = record[3]

        if not source_uuid or not target_uuid:
            continue

        props = dict(edge.properties) if hasattr(edge, 'properties') else {}
        props_parts = []
        for k, v in props.items():
            if isinstance(v, str):
                v_escaped = v.replace('"', '\\"').replace('\n', '\\n')
                props_parts.append(f'{k}: "{v_escaped}"')
            elif isinstance(v, (int, float, bool)):
                props_parts.append(f'{k}: {str(v).lower() if isinstance(v, bool) else v}')

        props_str = '{' + ', '.join(props_parts) + '}' if props_parts else ''

        try:
            target.query(f'''
                MATCH (s {{uuid: "{source_uuid}"}}), (t {{uuid: "{target_uuid}"}})
                CREATE (s)-[:{rel_type} {props_str}]->(t)
            ''')
            edges_created += 1
        except Exception as e:
            if 'already exists' not in str(e).lower():
                pass  # Silently skip duplicate edges

    print(f'  ✓ Created {edges_created} edges\n')

    return {
        'episodes': episode_count,
        'nodes': nodes_created,
        'edges': edges_created
    }


def main():
    parser = argparse.ArgumentParser(description='Selective Graphiti migration to default_db')
    parser.add_argument('--dry-run', action='store_true', help='Preview without making changes')
    args = parser.parse_args()

    print('=' * 80)
    print('Graphiti Selective Migration Tool')
    print('=' * 80)
    print()

    if args.dry_run:
        print('🔍 DRY RUN MODE - No changes will be made\n')

    client = connect_falkordb()

    # Check target graph
    target = client.select_graph(TARGET_GRAPH)
    result = target.query('MATCH (n) RETURN count(n) as count')
    existing_nodes = result.result_set[0][0] if result.result_set else 0

    if existing_nodes > 0:
        print(f'⚠️  Target graph "{TARGET_GRAPH}" has {existing_nodes} nodes')
        if not args.dry_run:
            response = input('  Continue and merge? (yes/no): ')
            if response.lower() != 'yes':
                print('  ❌ Migration cancelled\n')
                return
        print()

    # Execute migrations
    total_stats = {'episodes': 0, 'nodes': 0, 'edges': 0}

    for source_graph, group_ids in MIGRATION_MAP.items():
        try:
            stats = copy_graph_data(client, source_graph, TARGET_GRAPH, group_ids, dry_run=args.dry_run)
            if stats:
                total_stats['episodes'] += stats.get('episodes', 0)
                total_stats['nodes'] += stats.get('nodes', 0)
                total_stats['edges'] += stats.get('edges', 0)
        except Exception as e:
            print(f'  ❌ Error migrating {source_graph}: {e}\n')

    # Summary
    print('=' * 80)
    print('Migration Summary')
    print('=' * 80)
    print(f'Total Episodes: {total_stats["episodes"]}')
    print(f'Total Nodes: {total_stats["nodes"]}')
    print(f'Total Edges: {total_stats["edges"]}')
    print()

    if args.dry_run:
        print('✅ Dry run complete. Run without --dry-run to execute migration.')
    else:
        print('✅ Migration complete!')
        print()
        print('💡 Next steps:')
        print('  1. Restart Graphiti MCP server')
        print('  2. Test with: mcp__graphiti-fastmcp__get_episodes(group_ids=["graphiti_meta_knowledge"])')
        print('  3. Verify search: mcp__graphiti-fastmcp__search_nodes(query="...", group_ids=[...])')


if __name__ == '__main__':
    main()
