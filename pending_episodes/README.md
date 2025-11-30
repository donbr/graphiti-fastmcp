# Pending Episodes Queue

This directory contains episodes that are ready to be imported into the Graphiti knowledge graph but were created when the MCP server was unavailable.

## Purpose

Acts as a temporary queue for episodes that need to be added to the knowledge graph. This allows episode creation to continue even when the Graphiti MCP server is not accessible.

## Workflow

### 1. Creating Pending Episodes

When Claude Code (or another agent) prepares episodes but cannot connect to the Graphiti MCP server, episodes are saved here as JSON files.

**Filename convention**: `YYYY-MM-DD_topic_N.json`
- `YYYY-MM-DD`: Session date
- `topic`: Short identifier (e.g., `qdrant_docs`, `graphiti_cleanup`, `scaling_research`)
- `N`: Sequential number if multiple episodes same day/topic

### 2. Importing Pending Episodes

When MCP server is available, import episodes:

```python
import json

# Read episode file
with open('pending_episodes/2025-11-29_qdrant_docs_best_practice.json') as f:
    episode_data = json.load(f)

# Add to knowledge graph
add_memory(
    name=episode_data['name'],
    content=episode_data['content'],
    group_id=episode_data['group_id'],
    source_description=episode_data.get('source_description', 'Pending episode import')
)
```

**Important**: Wait 30-60 seconds after import for async entity extraction to complete.

### 3. Validating Import

After import, verify episodes were added:

```python
# Search for content from newly imported episodes
search_memory_facts(
    query="[topic from episode]",
    group_ids=["graphiti_meta_knowledge"],
    max_facts=10
)

# Check episode count increased
get_episodes(
    group_ids=["graphiti_meta_knowledge"],
    max_episodes=100
)
```

### 4. Cleanup

After successful import and validation:
- Move imported files to `pending_episodes/imported/` subdirectory
- Or delete if no archive needed

## File Format

Each JSON file contains:

```json
{
  "name": "Episode Title",
  "content": "Episode content (text or JSON string)",
  "group_id": "graphiti_meta_knowledge",
  "source_description": "Description of episode source/context"
}
```

## Security Notes

⚠️ **This directory is gitignored** to prevent committing episodes that may contain:
- Sensitive learnings or intellectual property
- Session-specific context
- Potentially sensitive patterns or insights

Only commit `README.md` and `.gitkeep` to maintain directory structure.

## Current Status

Check directory contents:
```bash
ls -la pending_episodes/
```

Count pending imports:
```bash
ls pending_episodes/*.json 2>/dev/null | wc -l
```
