#!/usr/bin/env python3
"""
Migrate Graphiti data from multiple FalkorDB graphs into a single default_db graph.

This script consolidates data from separate graph names (main, graphiti_meta_knowledge,
agent_memory_decision_tree_2025) into the default_db graph with proper group_id namespacing.

Usage:
    uv run python scripts/migrate_to_default_db.py --dry-run  # Preview what will be migrated
    uv run python scripts/migrate_to_default_db.py            # Execute migration
"""

import argparse
import asyncio
import os
from datetime import datetime
from pathlib import Path

from falkordb import FalkorDB

# FalkorDB Cloud connection
FALKORDB_URI = os.getenv('FALKORDB_URI', 'redis://localhost:6379')
FALKORDB_HOST = os.getenv('FALKORDB_HOST', 'r-6jissuruar.instance-ebqwfrd4o.hc-2uaqqpjgg.us-east-2.aws.f2e0a955bb84.cloud')
FALKORDB_PORT = int(os.getenv('FALKORDB_PORT', '57857'))
FALKORDB_USER = os.getenv('FALKORDB_USER', 'falkordb')
FALKORDB_PASSWORD = os.getenv('FALKORDB_PASSWORD', 'graphitiKG1!')

# Source graphs to migrate
SOURCE_GRAPHS = ['main', 'graphiti_meta_knowledge', 'agent_memory_decision_tree_2025']
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
    print('✅ Connected to FalkorDB')
    return client


def get_graph_stats(client, graph_name: str) -> dict:
    """Get statistics about a graph."""
    graph = client.select_graph(graph_name)

    # Count nodes by type
    result = graph.query('MATCH (n) RETURN labels(n) as labels, count(n) as count')
    node_stats = {}
    total_nodes = 0
    for record in result.result_set:
        labels = tuple(record[0])
        count = record[1]
        node_stats[labels] = count
        total_nodes += count

    # Count episodes
    result = graph.query('MATCH (e:Episodic) RETURN count(e) as count')
    episode_count = result.result_set[0][0] if result.result_set else 0

    # Count edges
    result = graph.query('MATCH ()-[r]->() RETURN count(r) as count')
    edge_count = result.result_set[0][0] if result.result_set else 0

    # Get group_ids
    result = graph.query('MATCH (e:Episodic) RETURN DISTINCT e.group_id as group_id')
    group_ids = [record[0] for record in result.result_set]

    return {
        'total_nodes': total_nodes,
        'episode_count': episode_count,
        'edge_count': edge_count,
        'node_stats': node_stats,
        'group_ids': group_ids
    }


def export_graph_data(client, graph_name: str) -> dict:
    """Export all nodes and edges from a graph."""
    print(f'\n📤 Exporting data from "{graph_name}" graph...')
    graph = client.select_graph(graph_name)

    # Export all nodes with all properties
    result = graph.query('''
        MATCH (n)
        RETURN n
    ''')

    nodes = []
    for record in result.result_set:
        node = record[0]
        # Extract node properties
        node_data = {
            'labels': node.labels,
            'properties': dict(node.properties) if hasattr(node, 'properties') else {}
        }
        nodes.append(node_data)

    print(f'  ✓ Exported {len(nodes)} nodes')

    # Export all edges with all properties
    result = graph.query('''
        MATCH (s)-[r]->(t)
        RETURN s, r, t
    ''')

    edges = []
    for record in result.result_set:
        source_node = record[0]
        edge = record[1]
        target_node = record[2]

        edge_data = {
            'source_labels': source_node.labels,
            'source_properties': dict(source_node.properties) if hasattr(source_node, 'properties') else {},
            'relationship_type': edge.relation,
            'relationship_properties': dict(edge.properties) if hasattr(edge, 'properties') else {},
            'target_labels': target_node.labels,
            'target_properties': dict(target_node.properties) if hasattr(target_node, 'properties') else {}
        }
        edges.append(edge_data)

    print(f'  ✓ Exported {len(edges)} edges')

    return {
        'graph_name': graph_name,
        'nodes': nodes,
        'edges': edges,
        'exported_at': datetime.utcnow().isoformat()
    }


def import_graph_data(client, target_graph_name: str, source_data: dict, dry_run: bool = False):
    """Import nodes and edges into the target graph."""
    graph_name = source_data['graph_name']
    nodes = source_data['nodes']
    edges = source_data['edges']

    print(f'\n📥 {"[DRY RUN] " if dry_run else ""}Importing data from "{graph_name}" into "{target_graph_name}"...')

    if dry_run:
        print(f'  Would import {len(nodes)} nodes and {len(edges)} edges')
        return

    graph = client.select_graph(target_graph_name)

    # Import nodes
    nodes_created = 0
    for node_data in nodes:
        labels_str = ':'.join(node_data['labels'])
        properties = node_data['properties']

        # Build property string
        props_list = []
        for key, value in properties.items():
            if isinstance(value, str):
                props_list.append(f'{key}: "{value}"')
            else:
                props_list.append(f'{key}: {value}')
        props_str = '{' + ', '.join(props_list) + '}' if props_list else ''

        # Create node
        query = f'CREATE (n:{labels_str} {props_str})'
        try:
            graph.query(query)
            nodes_created += 1
        except Exception as e:
            print(f'  ⚠️  Error creating node: {e}')
            print(f'     Query: {query}')

    print(f'  ✓ Created {nodes_created} nodes')

    # Import edges (requires matching nodes by UUID)
    edges_created = 0
    for edge_data in edges:
        # Match source and target nodes by UUID (assuming UUID exists)
        source_uuid = edge_data['source_properties'].get('uuid')
        target_uuid = edge_data['target_properties'].get('uuid')
        rel_type = edge_data['relationship_type']
        rel_props = edge_data['relationship_properties']

        if not source_uuid or not target_uuid:
            continue

        # Build relationship property string
        props_list = []
        for key, value in rel_props.items():
            if isinstance(value, str):
                props_list.append(f'{key}: "{value}"')
            else:
                props_list.append(f'{key}: {value}')
        props_str = '{' + ', '.join(props_list) + '}' if props_list else ''

        # Create edge
        query = f'''
            MATCH (s {{uuid: "{source_uuid}"}}), (t {{uuid: "{target_uuid}"}})
            CREATE (s)-[r:{rel_type} {props_str}]->(t)
        '''
        try:
            graph.query(query)
            edges_created += 1
        except Exception as e:
            print(f'  ⚠️  Error creating edge: {e}')

    print(f'  ✓ Created {edges_created} edges')


def main():
    parser = argparse.ArgumentParser(description='Migrate Graphiti data to default_db graph')
    parser.add_argument('--dry-run', action='store_true', help='Preview migration without making changes')
    args = parser.parse_args()

    print('=' * 80)
    print('Graphiti FalkorDB Migration Tool')
    print('=' * 80)

    if args.dry_run:
        print('\n🔍 DRY RUN MODE - No changes will be made\n')

    # Connect to FalkorDB
    client = connect_falkordb()

    # Check target graph status
    print(f'\n📊 Checking target graph "{TARGET_GRAPH}"...')
    target_stats = get_graph_stats(client, TARGET_GRAPH)
    print(f'  Current state: {target_stats["total_nodes"]} nodes, {target_stats["edge_count"]} edges')

    if target_stats['total_nodes'] > 0 and not args.dry_run:
        print(f'\n⚠️  WARNING: Target graph "{TARGET_GRAPH}" is not empty!')
        response = input(f'  Continue and merge data? (yes/no): ')
        if response.lower() != 'yes':
            print('  ❌ Migration cancelled')
            return

    # Analyze source graphs
    print(f'\n📊 Analyzing source graphs...')
    total_episodes = 0
    total_nodes = 0
    total_edges = 0

    for graph_name in SOURCE_GRAPHS:
        try:
            stats = get_graph_stats(client, graph_name)
            print(f'\n  {graph_name}:')
            print(f'    Episodes: {stats["episode_count"]}')
            print(f'    Nodes: {stats["total_nodes"]}')
            print(f'    Edges: {stats["edge_count"]}')
            print(f'    Group IDs: {", ".join(stats["group_ids"])}')

            total_episodes += stats['episode_count']
            total_nodes += stats['total_nodes']
            total_edges += stats['edge_count']
        except Exception as e:
            print(f'  ⚠️  Error reading {graph_name}: {e}')

    print(f'\n📊 Migration Summary:')
    print(f'  Total Episodes: {total_episodes}')
    print(f'  Total Nodes: {total_nodes}')
    print(f'  Total Edges: {total_edges}')

    if args.dry_run:
        print('\n✅ Dry run complete. Run without --dry-run to execute migration.')
        return

    # Execute migration
    print(f'\n🚀 Starting migration...')

    for graph_name in SOURCE_GRAPHS:
        try:
            # Export
            data = export_graph_data(client, graph_name)

            # Import
            import_graph_data(client, TARGET_GRAPH, data, dry_run=False)

        except Exception as e:
            print(f'  ❌ Error migrating {graph_name}: {e}')

    # Verify final state
    print(f'\n📊 Final state of "{TARGET_GRAPH}"...')
    final_stats = get_graph_stats(client, TARGET_GRAPH)
    print(f'  Episodes: {final_stats["episode_count"]}')
    print(f'  Nodes: {final_stats["total_nodes"]}')
    print(f'  Edges: {final_stats["edge_count"]}')
    print(f'  Group IDs: {", ".join(final_stats["group_ids"])}')

    print(f'\n✅ Migration complete!')
    print(f'\n💡 Next steps:')
    print(f'  1. Restart Graphiti MCP server to pick up changes')
    print(f'  2. Test with: mcp__graphiti-fastmcp__get_episodes(group_ids=["main"], max_episodes=5)')
    print(f'  3. Verify all group_ids work correctly')


if __name__ == '__main__':
    main()
