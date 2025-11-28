# Graphiti Operational Scripts

Utility scripts for managing and maintaining Graphiti knowledge graphs.

## Setup

Ensure the Graphiti MCP server is running:

```bash
docker compose up
```

## Available Scripts

| Script | Purpose |
|--------|---------|
| `export_graph.py` | Export graph episodes to JSON for backup |
| `import_graph.py` | Restore graph from JSON backup |
| `populate_meta_knowledge.py` | Bootstrap knowledge with foundational episodes |
| `verify_meta_knowledge.py` | Verify entity/relationship extraction |

## Backup & Restore

### Export a group

```bash
uv run python scripts/export_graph.py --group graphiti_meta_knowledge --output backups/
```

### Export all groups

```bash
uv run python scripts/export_graph.py --all --output backups/
```

### Restore from backup

```bash
uv run python scripts/import_graph.py --input backups/graphiti_meta_knowledge.json
```

## Verification

After adding episodes, verify extraction completed:

```bash
uv run python scripts/verify_meta_knowledge.py
```

> **Note**: Entity extraction is asynchronous. Wait 15-30 seconds after adding episodes before verification.

## See Also

- [`examples/`](../examples/) - MCP SDK learning tutorials
- [`reference/`](../reference/) - Best practices documentation (if available)
