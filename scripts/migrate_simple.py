#!/usr/bin/env python3
"""
Simple migration: Copy ALL nodes/edges from source graphs, filtering by group_id.

Uses DUMP/RESTORE approach for efficiency.

Usage:
    uv run python scripts/migrate_simple.py
"""

import os
from falkordb import FalkorDB

# Connection details
FALKORDB_HOST = os.getenv('FALKORDB_HOST', 'r-6jissuruar.instance-ebqwfrd4o.hc-2uaqqpjgg.us-east-2.aws.f2e0a955bb84.cloud')
FALKORDB_PORT = int(os.getenv('FALKORDB_PORT', '57857'))
FALKORDB_USER = os.getenv('FALKORDB_USER', 'falkordb')
FALKORDB_PASSWORD = os.getenv('FALKORDB_PASSWORD', 'graphitiKG1!')

# Which graph/group_id combinations to migrate
MIGRATIONS = [
    ('graphiti_meta_knowledge', 'graphiti_meta_knowledge'),
    ('agent_memory_decision_tree_2025', 'agent_memory_decision_tree_2025'),
    ('main', 'main'),
    ('main', 'tutorials'),
]

TARGET_GRAPH = 'default_db'


def connect():
    print(f'Connecting to FalkorDB Cloud...')
    return FalkorDB(host=FALKORDB_HOST, port=FALKORDB_PORT, username=FALKORDB_USER, password=FALKORDB_PASSWORD)


def copy_by_group_id(client, source_graph_name: str, group_id: str, target_graph_name: str):
    """Copy nodes/edges for a specific group_id from source to target."""
    print(f'\nMigrating: {source_graph_name}[group_id={group_id}] → {target_graph_name}')

    source = client.select_graph(source_graph_name)
    target = client.select_graph(target_graph_name)

    # Get all node UUIDs for this group_id
    result = source.query(f'MATCH (n) WHERE n.group_id = "{group_id}" RETURN n.uuid as uuid')
    node_uuids = [r[0] for r in result.result_set if r[0]]
    print(f'  Found {len(node_uuids)} nodes with group_id="{group_id}"')

    # Copy each node
    nodes_created = 0
    for uuid in node_uuids:
        # Get full node data
        result = source.query(f'MATCH (n {{uuid: "{uuid}"}}) RETURN n')
        if not result.result_set:
            continue

        node = result.result_set[0][0]
        labels = ':'.join(node.labels)
        props = dict(node.properties)

        # Build property string
        parts = []
        for k, v in props.items():
            if isinstance(v, str):
                escaped = v.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
                parts.append(f'{k}: "{escaped}"')
            elif v is None:
                parts.append(f'{k}: null')
            elif isinstance(v, bool):
                parts.append(f'{k}: {str(v).lower()}')
            else:
                parts.append(f'{k}: {v}')

        props_str = '{' + ', '.join(parts) + '}'

        # Create in target
        try:
            target.query(f'CREATE (:{labels} {props_str})')
            nodes_created += 1
        except Exception as e:
            if 'Duplicated element' not in str(e):
                print(f'    Error: {e}')

    print(f'  ✓ Created {nodes_created} nodes')

    # Copy edges between these nodes
    result = source.query(f'''
        MATCH (s {{group_id: "{group_id}"}})-[r]->(t {{group_id: "{group_id}"}})
        RETURN s.uuid, type(r), r, t.uuid
    ''')

    edges_created = 0
    for record in result.result_set:
        s_uuid, rel_type, edge, t_uuid = record[0], record[1], record[2], record[3]

        props = dict(edge.properties) if hasattr(edge, 'properties') else {}
        parts = []
        for k, v in props.items():
            if isinstance(v, str):
                escaped = v.replace('"', '\\"').replace('\n', '\\n').replace('\r', '')
                parts.append(f'{k}: "{escaped}"')
            elif v is None:
                parts.append(f'{k}: null')
            elif isinstance(v, bool):
                parts.append(f'{k}: {str(v).lower()}')
            else:
                parts.append(f'{k}: {v}')

        props_str = '{' + ', '.join(parts) + '}' if parts else ''

        try:
            target.query(f'''
                MATCH (s {{uuid: "{s_uuid}"}}), (t {{uuid: "{t_uuid}"}})
                CREATE (s)-[:{rel_type} {props_str}]->(t)
            ''')
            edges_created += 1
        except Exception:
            pass  # Skip duplicates

    print(f'  ✓ Created {edges_created} edges')


def main():
    client = connect()

    print('\n' + '=' * 80)
    print('Starting Migration')
    print('=' * 80)

    total_nodes = 0
    total_edges = 0

    for source_graph, group_id in MIGRATIONS:
        try:
            result = copy_by_group_id(client, source_graph, group_id, TARGET_GRAPH)
        except Exception as e:
            print(f'  ❌ Error: {e}')

    # Verify final state
    print('\n' + '=' * 80)
    print('Final State')
    print('=' * 80)

    target = client.select_graph(TARGET_GRAPH)

    result = target.query('MATCH (n) RETURN count(n)')
    total_nodes = result.result_set[0][0]

    result = target.query('MATCH ()-[r]->() RETURN count(r)')
    total_edges = result.result_set[0][0]

    result = target.query('MATCH (e:Episodic) RETURN DISTINCT e.group_id')
    group_ids = [r[0] for r in result.result_set]

    print(f'Total Nodes: {total_nodes}')
    print(f'Total Edges: {total_edges}')
    print(f'Group IDs: {", ".join(group_ids)}')

    print('\n✅ Migration complete!')
    print('\n💡 Next: Restart Graphiti MCP server and test queries')


if __name__ == '__main__':
    main()
