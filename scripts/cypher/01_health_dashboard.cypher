// =============================================================================
// GRAPHITI HEALTH DASHBOARD
// Purpose: Daily monitoring of system health and statistics
// Frequency: Daily or after bulk operations
// =============================================================================

// -----------------------------------------------------------------------------
// 1. Complete Database Statistics
// Returns: Total nodes, relationships, label counts, relationship type counts
// -----------------------------------------------------------------------------
CALL apoc.meta.stats() YIELD nodeCount, relCount, labels, relTypesCount
RETURN nodeCount AS total_nodes,
       relCount AS total_relationships,
       labels AS node_labels,
       relTypesCount AS relationship_types;

// -----------------------------------------------------------------------------
// 2. Episode Distribution by Group ID
// Returns: Count of episodes per namespace
// Use: Verify data is in expected namespaces
// -----------------------------------------------------------------------------
MATCH (e:Episodic)
RETURN e.group_id AS group_id, count(*) AS episode_count
ORDER BY episode_count DESC;

// -----------------------------------------------------------------------------
// 3. Entity Type Distribution
// Returns: Count of entities by label type
// Use: Understand what kinds of entities have been extracted
// -----------------------------------------------------------------------------
MATCH (n:Entity)
WITH n, [l IN labels(n) WHERE l <> 'Entity'] AS entity_labels
UNWIND entity_labels AS label
RETURN label AS entity_type, count(*) AS count
ORDER BY count DESC;

// -----------------------------------------------------------------------------
// 4. Relationship Type Distribution
// Returns: Count by relationship type
// Use: Verify RELATES_TO and MENTIONS are being created
// -----------------------------------------------------------------------------
MATCH ()-[r]->()
RETURN type(r) AS relationship_type, count(*) AS count
ORDER BY count DESC;

// -----------------------------------------------------------------------------
// 5. Recent Episodes (Last 7 Days)
// Returns: Recently added episodes
// Use: Track ingestion activity
// -----------------------------------------------------------------------------
MATCH (e:Episodic)
WHERE e.created_at > datetime() - duration('P7D')
RETURN e.name AS episode_name,
       e.group_id AS group_id,
       e.created_at AS created_at
ORDER BY e.created_at DESC
LIMIT 20;

// -----------------------------------------------------------------------------
// 6. Quick Health Summary
// Returns: Single-row summary of key metrics
// Use: At-a-glance health check
// -----------------------------------------------------------------------------
MATCH (e:Episodic)
WITH count(e) AS total_episodes
MATCH (n:Entity)
WITH total_episodes, count(n) AS total_entities
MATCH ()-[r:RELATES_TO]->()
WITH total_episodes, total_entities, count(r) AS relates_to_count
MATCH ()-[m:MENTIONS]->()
RETURN total_episodes,
       total_entities,
       relates_to_count,
       count(m) AS mentions_count;
