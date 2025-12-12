// =============================================================================
// GRAPHITI DATA QUALITY AUDIT
// Purpose: Find data issues that may affect search and retrieval
// Frequency: Weekly or after bulk imports
// =============================================================================

// -----------------------------------------------------------------------------
// 1. Entities Missing Embeddings (CRITICAL)
// Returns: Entities without name_embedding property
// Impact: These entities will NOT appear in search results!
// Action: Re-ingest the source episode or investigate extraction failure
// -----------------------------------------------------------------------------
MATCH (n:Entity)
WHERE n.name_embedding IS NULL
RETURN n.name AS entity_name,
       n.group_id AS group_id,
       [l IN labels(n) WHERE l <> 'Entity'] AS entity_types,
       n.created_at AS created_at
ORDER BY n.created_at DESC
LIMIT 50;

// -----------------------------------------------------------------------------
// 2. Orphan Entities (No Relationships)
// Returns: Entities with no RELATES_TO or MENTIONS connections
// Impact: Isolated nodes may indicate extraction issues
// Note: Some orphans are acceptable (standalone concepts)
// -----------------------------------------------------------------------------
MATCH (n:Entity)
WHERE NOT (n)-[:RELATES_TO]-() AND NOT ()-[:MENTIONS]->(n)
RETURN n.name AS entity_name,
       n.group_id AS group_id,
       [l IN labels(n) WHERE l <> 'Entity'] AS entity_types,
       n.summary AS summary
ORDER BY n.group_id, n.name
LIMIT 50;

// -----------------------------------------------------------------------------
// 3. Episodes Without Extracted Entities
// Returns: Episodes that have no MENTIONS relationships
// Impact: May indicate extraction failure or very short content
// -----------------------------------------------------------------------------
MATCH (e:Episodic)
WHERE NOT ()-[:MENTIONS]->(e) AND NOT (e)-[:MENTIONS]->()
RETURN e.name AS episode_name,
       e.group_id AS group_id,
       e.source AS source_type,
       e.created_at AS created_at,
       left(e.content, 100) AS content_preview
ORDER BY e.created_at DESC
LIMIT 30;

// -----------------------------------------------------------------------------
// 4. Potential Duplicate Entities (Same Name, Different UUIDs)
// Returns: Entity names that appear multiple times
// Impact: May fragment knowledge across multiple nodes
// Note: Some duplicates are valid (same name, different contexts)
// -----------------------------------------------------------------------------
MATCH (n:Entity)
WITH n.name AS name, n.group_id AS group_id, collect(n.uuid) AS uuids
WHERE size(uuids) > 1
RETURN name,
       group_id,
       size(uuids) AS duplicate_count,
       uuids
ORDER BY duplicate_count DESC
LIMIT 20;

// -----------------------------------------------------------------------------
// 5. Entities with Very Short Summaries
// Returns: Entities where summary may be incomplete
// Impact: May indicate poor extraction quality
// -----------------------------------------------------------------------------
MATCH (n:Entity)
WHERE n.summary IS NOT NULL AND size(n.summary) < 50
RETURN n.name AS entity_name,
       n.group_id AS group_id,
       n.summary AS short_summary,
       size(n.summary) AS summary_length
ORDER BY summary_length ASC
LIMIT 30;

// -----------------------------------------------------------------------------
// 6. Data Quality Summary
// Returns: Counts of potential issues
// Use: Quick overview of data health
// -----------------------------------------------------------------------------
MATCH (n:Entity)
OPTIONAL MATCH (n)-[r:RELATES_TO]-()
WITH n,
     CASE WHEN n.name_embedding IS NULL THEN 1 ELSE 0 END AS missing_embedding,
     CASE WHEN r IS NULL THEN 1 ELSE 0 END AS is_orphan
RETURN count(n) AS total_entities,
       sum(missing_embedding) AS entities_missing_embeddings,
       sum(is_orphan) AS orphan_entities,
       round(100.0 * sum(missing_embedding) / count(n), 2) AS pct_missing_embeddings,
       round(100.0 * sum(is_orphan) / count(n), 2) AS pct_orphans;
