# Graphiti Operational Scripts

Utility scripts for managing Graphiti knowledge graphs.

## Prerequisites

- Graphiti MCP server running at `http://localhost:8000/mcp/`
- Docker: `docker compose up`

## Script Categories

### Core Operations (Tier 1)

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `export_graph.py` | Export episodes to JSON | Before major changes, regular backups |
| `import_graph.py` | Restore from JSON backup | Disaster recovery, environment setup |

### Bootstrap & Verification (Tier 2)

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `populate_meta_knowledge.py` | Create foundational episodes | Fresh environment, no backups available |
| `verify_meta_knowledge.py` | Verify entity extraction | After adding episodes, debugging |

### Monitoring & Deployment (Tier 3)

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `check_falkordb_health.py` | Monitor FalkorDB Cloud storage | Regular health checks, free tier monitoring |
| `verify_fastmcp_cloud_readiness.py` | Pre-deployment validation | Before deploying to FastMCP Cloud |

### Research Tools (Tier 4)

| Script | Purpose | When to Use |
|--------|---------|-------------|
| `validate_qdrant.py` | Validate Qdrant docs collection | Verify documentation search MCP server |

> Contains 2,670 pages: Zep Graphiti, Anthropic Claude, LangChain, Prefect, FastMCP, PydanticAI, MCP Protocol

## Quick Reference

### Backup & Restore

```bash
# Export a group
uv run scripts/export_graph.py --group graphiti_meta_knowledge --output backups/

# Export all groups
uv run scripts/export_graph.py --all --output backups/

# Restore from backup
uv run scripts/import_graph.py --input backups/graphiti_meta_knowledge.json
```

### Health Monitoring

```bash
# Check FalkorDB Cloud usage (free tier: 100 MB)
uv run scripts/check_falkordb_health.py
```

### Deployment

```bash
# Verify ready for FastMCP Cloud
uv run scripts/verify_fastmcp_cloud_readiness.py
```

## Data Migration

**IMPORTANT**: Do NOT use raw Cypher scripts to copy graph data. This corrupts embeddings.

**Correct approach**:
1. Export episodes: `uv run scripts/export_graph.py --group <id> --output backups/`
2. Clear target if needed: Use `clear_graph` MCP tool
3. Import via API: `uv run scripts/import_graph.py --input backups/<file>.json`

The import script uses Graphiti's MCP API which regenerates embeddings correctly.

> **⚠️ Known Limitation**: FalkorDB vector searches may fail due to upstream bugs in `graphiti-core`. See [`research/VECTOR_INDEX_MISSING_FALKORDB.md`](../research/VECTOR_INDEX_MISSING_FALKORDB.md) for details and workarounds.

## Backup Storage Strategy

### Tier 1: Bootstrap from Code (Public)

**Use when**: Fresh environment, no backups available

```bash
uv run scripts/populate_meta_knowledge.py
```

**Recovery Time**: < 2 minutes
**Result**: 10 foundational episodes covering core Graphiti concepts

### Tier 2: Local Backups (Private)

**Location**: `backups/` directory (.gitignored)

**Use when**: Restoring from operational backups

```bash
# Export current state (manual backup)
uv run scripts/export_graph.py --all --output backups/

# Restore from backup
uv run scripts/import_graph.py --input backups/graphiti_meta_knowledge.json
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

### Research Documentation

- [`research/VECTOR_INDEX_MISSING_FALKORDB.md`](../research/VECTOR_INDEX_MISSING_FALKORDB.md) - **Critical**: Upstream bugs affecting FalkorDB searches
- [`research/graphiti_migration_research_findings.md`](../research/graphiti_migration_research_findings.md) - Best practices for data migration
- [`research/Graphiti Graph Migration FalkorDB ↔ Neo4j.md`](../research/Graphiti%20Graph%20Migration%20FalkorDB%20↔%20Neo4j.md) - Cross-backend migration
