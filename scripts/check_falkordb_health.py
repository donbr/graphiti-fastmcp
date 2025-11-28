#!/usr/bin/env python3
"""
FalkorDB Cloud Health Check Script

Validates database size and health for FalkorDB Cloud instances,
particularly useful for monitoring free tier usage (100 MB limit).

Usage:
    uv run scripts/check_falkordb_health.py
    python scripts/check_falkordb_health.py --limit 100
"""

import argparse
import asyncio
import os
import sys
from pathlib import Path
from urllib.parse import urlparse

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

# Load environment variables from project root
load_dotenv(project_root / '.env')


async def get_connection():
    """Create FalkorDB connection from environment variables."""
    from falkordb.asyncio import FalkorDB

    uri = os.environ.get('FALKORDB_URI', 'redis://localhost:6379')
    parsed = urlparse(uri)
    host = parsed.hostname or 'localhost'
    port = parsed.port or 6379
    username = os.environ.get('FALKORDB_USER') or None
    password = os.environ.get('FALKORDB_PASSWORD') or None

    # Handle empty string credentials
    if username == '':
        username = None
    if password == '':
        password = None

    db = FalkorDB(host=host, port=port, username=username, password=password)
    return db, host, port


async def get_server_info(db) -> dict:
    """Get Redis server memory information."""
    try:
        info = await db.connection.info('memory')
        return {
            'used_memory': info.get('used_memory', 0),
            'used_memory_human': info.get('used_memory_human', 'N/A'),
            'used_memory_peak': info.get('used_memory_peak', 0),
            'used_memory_peak_human': info.get('used_memory_peak_human', 'N/A'),
            'used_memory_rss': info.get('used_memory_rss', 0),
            'used_memory_rss_human': info.get('used_memory_rss_human', 'N/A'),
            'maxmemory': info.get('maxmemory', 0),
            'maxmemory_human': info.get('maxmemory_human', 'N/A'),
        }
    except Exception as e:
        return {'error': str(e)}


async def get_graph_memory(db, graph_name: str) -> dict:
    """Get memory usage for a specific graph using GRAPH.MEMORY USAGE command."""
    try:
        result = await db.execute_command('GRAPH.MEMORY', 'USAGE', graph_name)
        # Parse the result - it returns alternating key-value pairs
        stats = {}
        if isinstance(result, list):
            for i in range(0, len(result), 2):
                if i + 1 < len(result):
                    key = result[i]
                    value = result[i + 1]
                    stats[key] = value
        return stats
    except Exception as e:
        return {'error': str(e)}


async def get_graph_node_edge_counts(db, graph_name: str) -> dict:
    """Get node and edge counts for a graph."""
    try:
        graph = db.select_graph(graph_name)
        # Count nodes
        node_result = await graph.ro_query('MATCH (n) RETURN count(n) as count')
        node_count = node_result.result_set[0][0] if node_result.result_set else 0

        # Count edges
        edge_result = await graph.ro_query('MATCH ()-[r]->() RETURN count(r) as count')
        edge_count = edge_result.result_set[0][0] if edge_result.result_set else 0

        return {'nodes': node_count, 'edges': edge_count}
    except Exception as e:
        return {'error': str(e), 'nodes': 0, 'edges': 0}


async def get_all_graphs_stats(db) -> list[dict]:
    """Get statistics for all graphs in the database."""
    graphs = []
    try:
        graph_names = await db.list_graphs()
        for name in graph_names:
            memory = await get_graph_memory(db, name)
            counts = await get_graph_node_edge_counts(db, name)
            graphs.append({
                'name': name,
                'memory': memory,
                'counts': counts,
            })
    except Exception as e:
        graphs.append({'error': str(e)})
    return graphs


def check_free_tier_status(graphs: list[dict], limit_mb: float = 100.0) -> dict:
    """Check if usage is within free tier limits."""
    total_mb = 0.0
    for graph in graphs:
        if 'memory' in graph and 'total_graph_sz_mb' in graph['memory']:
            total_mb += float(graph['memory']['total_graph_sz_mb'])

    percentage = (total_mb / limit_mb) * 100 if limit_mb > 0 else 0

    if percentage >= 90:
        status = 'CRITICAL'
        message = f'Usage at {percentage:.1f}% - approaching free tier limit!'
    elif percentage >= 70:
        status = 'WARNING'
        message = f'Usage at {percentage:.1f}% - consider cleanup'
    else:
        status = 'OK'
        message = f'Usage at {percentage:.1f}% - within healthy limits'

    return {
        'total_mb': total_mb,
        'limit_mb': limit_mb,
        'percentage': percentage,
        'status': status,
        'message': message,
    }


def format_bytes(bytes_val: int) -> str:
    """Format bytes to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_val < 1024:
            return f'{bytes_val:.2f} {unit}'
        bytes_val /= 1024
    return f'{bytes_val:.2f} TB'


def print_report(host: str, port: int, server_info: dict, graphs: list[dict], tier_status: dict):
    """Print formatted health report."""
    print()
    print('=' * 60)
    print('FalkorDB Cloud Health Report')
    print('=' * 60)
    print(f'Server: {host}:{port}')

    # Server info
    if 'error' in server_info:
        print(f'Server Info Error: {server_info["error"]}')
    else:
        print()
        print('Redis Memory Usage:')
        print(f"  Used:     {server_info.get('used_memory_human', 'N/A')}")
        print(f"  Peak:     {server_info.get('used_memory_peak_human', 'N/A')}")
        print(f"  RSS:      {server_info.get('used_memory_rss_human', 'N/A')}")
        if server_info.get('maxmemory', 0) > 0:
            print(f"  Max:      {server_info.get('maxmemory_human', 'N/A')}")

    # Graphs
    print()
    print(f'Graphs ({len(graphs)} found):')
    if not graphs:
        print('  No graphs found')
    else:
        for graph in graphs:
            if 'error' in graph:
                print(f"  Error: {graph['error']}")
                continue

            name = graph['name']
            memory = graph.get('memory', {})
            counts = graph.get('counts', {})

            if 'error' in memory:
                size_str = f"Error: {memory['error']}"
            elif 'total_graph_sz_mb' in memory:
                size_str = f"{float(memory['total_graph_sz_mb']):.3f} MB"
            else:
                size_str = 'N/A'

            nodes = counts.get('nodes', 0)
            edges = counts.get('edges', 0)

            print(f'  - {name}:')
            print(f'      Size:  {size_str}')
            print(f'      Nodes: {nodes:,}')
            print(f'      Edges: {edges:,}')

            # Show memory breakdown if available
            if 'indices_sz_mb' in memory:
                print(f"      Indices: {float(memory['indices_sz_mb']):.3f} MB")

    # Free tier status
    print()
    print('-' * 60)
    print('Free Tier Status:')
    print(f"  Total Graph Storage: {tier_status['total_mb']:.2f} MB / {tier_status['limit_mb']:.0f} MB")
    print(f"  Usage: {tier_status['percentage']:.1f}%")
    print(f"  Status: {tier_status['status']} - {tier_status['message']}")
    print('=' * 60)
    print()


async def main(limit_mb: float = 100.0):
    """Main entry point."""
    try:
        db, host, port = await get_connection()
        print(f'Connecting to {host}:{port}...')

        # Test connection
        try:
            await db.connection.ping()
            print('Connection successful!')
        except Exception as e:
            print(f'Connection failed: {e}')
            return 1

        # Gather data
        server_info = await get_server_info(db)
        graphs = await get_all_graphs_stats(db)
        tier_status = check_free_tier_status(graphs, limit_mb)

        # Print report
        print_report(host, port, server_info, graphs, tier_status)

        # Close connection
        await db.connection.aclose()

        # Return exit code based on status
        if tier_status['status'] == 'CRITICAL':
            return 2
        elif tier_status['status'] == 'WARNING':
            return 1
        return 0

    except Exception as e:
        print(f'Error: {e}')
        return 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Check FalkorDB Cloud database health and size'
    )
    parser.add_argument(
        '--limit',
        type=float,
        default=100.0,
        help='Free tier limit in MB (default: 100)',
    )
    args = parser.parse_args()

    exit_code = asyncio.run(main(args.limit))
    sys.exit(exit_code)
