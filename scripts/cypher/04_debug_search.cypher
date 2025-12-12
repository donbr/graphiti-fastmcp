// =============================================================================
// GRAPHITI DEBUG & SEARCH QUERIES
// Purpose: Ad-hoc entity and episode lookup for troubleshooting
// Frequency: As needed during development and debugging
// =============================================================================

// -----------------------------------------------------------------------------
// 1. Find Entity by Name (Case-Insensitive)
// Usage: Replace 'search_term' with your search string
// Returns: Matching entities with details
// -----------------------------------------------------------------------------
MATCH (n:Entity)
WHERE toLower(n.name) CONTAINS toLower('search_term')
RETURN n.name AS entity_name,
       n.uuid AS uuid,
       n.group_id AS group_id,
       [l IN labels(n) WHERE l <> 'Entity'] AS entity_types,
       n.summary AS summary,
       n.created_at AS created_at
ORDER BY n.name
LIMIT 20;

// -----------------------------------------------------------------------------
// 2. Find Episode by Name
// Usage: Replace 'search_term' with your search string
// Returns: Matching episodes with content preview
// -----------------------------------------------------------------------------
MATCH (e:Episodic)
WHERE toLower(e.name) CONTAINS toLower('search_term')
RETURN e.name AS episode_name,
       e.uuid AS uuid,
       e.group_id AS group_id,
       e.source AS source_type,
       e.created_at AS created_at,
       left(e.content, 200) AS content_preview
ORDER BY e.created_at DESC
LIMIT 20;

// -----------------------------------------------------------------------------
// 3. Get Entity by UUID
// Usage: Replace 'your-uuid-here' with actual UUID
// Returns: Complete entity details
// -----------------------------------------------------------------------------
MATCH (n:Entity {uuid: 'your-uuid-here'})
RETURN n.name AS entity_name,
       n.uuid AS uuid,
       n.group_id AS group_id,
       labels(n) AS all_labels,
       n.summary AS summary,
       n.created_at AS created_at,
       n.name_embedding IS NOT NULL AS has_embedding;

// -----------------------------------------------------------------------------
// 4. Get Episode by UUID
// Usage: Replace 'your-uuid-here' with actual UUID
// Returns: Complete episode details
// -----------------------------------------------------------------------------
MATCH (e:Episodic {uuid: 'your-uuid-here'})
RETURN e.name AS episode_name,
       e.uuid AS uuid,
       e.group_id AS group_id,
       e.source AS source_type,
       e.source_description AS source_description,
       e.created_at AS created_at,
       e.content AS full_content;

// -----------------------------------------------------------------------------
// 5. Trace Episode to Extracted Entities
// Usage: Replace 'episode-uuid' with the episode's UUID
// Returns: All entities mentioned by this episode
// -----------------------------------------------------------------------------
MATCH (e:Episodic {uuid: 'episode-uuid'})-[:MENTIONS]->(n:Entity)
RETURN e.name AS episode_name,
       n.name AS extracted_entity,
       [l IN labels(n) WHERE l <> 'Entity'] AS entity_types,
       n.summary AS entity_summary
ORDER BY n.name;

// -----------------------------------------------------------------------------
// 6. Find All Facts About an Entity
// Usage: Replace 'Entity Name' with the entity's name
// Returns: All relationships involving this entity
// -----------------------------------------------------------------------------
MATCH (n:Entity)
WHERE n.name = 'Entity Name'
OPTIONAL MATCH (n)-[r1:RELATES_TO]->(target:Entity)
OPTIONAL MATCH (source:Entity)-[r2:RELATES_TO]->(n)
WITH n,
     collect(DISTINCT {direction: 'outgoing', fact: r1.fact, target: target.name, valid: r1.invalid_at IS NULL}) AS outgoing,
     collect(DISTINCT {direction: 'incoming', fact: r2.fact, source: source.name, valid: r2.invalid_at IS NULL}) AS incoming
RETURN n.name AS entity_name,
       n.summary AS entity_summary,
       outgoing,
       incoming;

// -----------------------------------------------------------------------------
// 7. Find Entities in Specific Group
// Usage: Replace 'graphiti_meta_knowledge' with your group_id
// Returns: All entities in that namespace
// -----------------------------------------------------------------------------
MATCH (n:Entity {group_id: 'graphiti_meta_knowledge'})
RETURN n.name AS entity_name,
       [l IN labels(n) WHERE l <> 'Entity'] AS entity_types,
       n.summary AS summary
ORDER BY n.name
LIMIT 50;

// -----------------------------------------------------------------------------
// 8. Find Episodes in Specific Group
// Usage: Replace 'graphiti_meta_knowledge' with your group_id
// Returns: All episodes in that namespace
// -----------------------------------------------------------------------------
MATCH (e:Episodic {group_id: 'graphiti_meta_knowledge'})
RETURN e.name AS episode_name,
       e.source AS source_type,
       e.created_at AS created_at,
       left(e.content, 100) AS content_preview
ORDER BY e.created_at DESC
LIMIT 50;

// -----------------------------------------------------------------------------
// 9. Entity Neighborhood (2-hop)
// Usage: Replace 'Entity Name' with target entity
// Returns: Entity and all connected entities within 2 hops
// -----------------------------------------------------------------------------
MATCH path = (n:Entity {name: 'Entity Name'})-[:RELATES_TO*1..2]-(connected:Entity)
RETURN n.name AS center_entity,
       [node IN nodes(path) | node.name] AS path_nodes,
       length(path) AS hops
LIMIT 30;

// -----------------------------------------------------------------------------
// 10. Full-Text Search Across Summaries
// Usage: Replace 'keyword' with your search term
// Returns: Entities whose summaries contain the keyword
// -----------------------------------------------------------------------------
MATCH (n:Entity)
WHERE n.summary IS NOT NULL AND toLower(n.summary) CONTAINS toLower('keyword')
RETURN n.name AS entity_name,
       n.group_id AS group_id,
       [l IN labels(n) WHERE l <> 'Entity'] AS entity_types,
       n.summary AS matching_summary
ORDER BY n.name
LIMIT 20;
