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

## Backup Storage Strategy

### Tier 1: Bootstrap from Code (Public)

**Use when**: Fresh environment, no backups available

```bash
uv run python scripts/populate_meta_knowledge.py
```

**Recovery Time**: < 2 minutes
**Result**: 10 foundational episodes covering core Graphiti concepts

### Tier 2: Local Backups (Private)

**Location**: `backups/` directory (.gitignored)

**Use when**: Restoring from operational backups

```bash
# Export current state (manual backup)
uv run python scripts/export_graph.py --all --output backups/

# Restore from backup
uv run python scripts/import_graph.py --input backups/graphiti_meta_knowledge.json
```

**Recovery Time**: < 5 minutes
**Result**: Full graph state including organic growth

**Backup Schedule**:
- After significant research sessions
- Before major changes (schema updates, migration)
- Weekly for active development

### Tier 3: Private Repository (Optional)

**Use when**: Preserving temporal evolution for research

**Setup**:
```bash
# Create private backup repo
gh repo create graphiti-fastmcp-backups --private

# Initialize in backups/ directory
cd backups/
git init
git remote add origin git@github.com:donbr/graphiti-fastmcp-backups.git

# Commit with timestamps
git add .
git commit -m "backup: $(date +%Y-%m-%d)"
git push -u origin main
```

**Value**: Git history shows knowledge graph evolution over time

**Recommended for**: Long-term research projects tracking learning progression

---

## Storage Location Decision Matrix

| Scenario | Recommended Tier | Rationale |
|----------|------------------|-----------|
| New environment setup | Tier 1 (Bootstrap) | Fast, deterministic, no dependencies |
| Daily development | Tier 2 (Local) | Quick access, full state |
| Pre-production migration | Tier 2 (Local) | Complete episode history |
| Research artifact preservation | Tier 3 (Private repo) | Temporal versioning |
| Disaster recovery (laptop failure) | Tier 1 + Tier 3 | Bootstrap if no backups, full restore if versioned |

---

## See Also

- [`examples/`](../examples/) - MCP SDK learning tutorials
- [`reference/`](../reference/) - Best practices documentation
