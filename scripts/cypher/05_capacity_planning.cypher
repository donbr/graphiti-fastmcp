// =============================================================================
// GRAPHITI CAPACITY PLANNING
// Purpose: Size estimates, growth tracking, and resource planning
// Frequency: Monthly or before major data imports
// =============================================================================

// -----------------------------------------------------------------------------
// 1. Detailed Size by Group ID
// Returns: Node and relationship counts per namespace
// Use: Understand relative sizes of knowledge graphs
// -----------------------------------------------------------------------------
MATCH (n)
WHERE n.group_id IS NOT NULL
WITH n.group_id AS group_id, labels(n) AS lbls
RETURN group_id,
       count(*) AS total_nodes,
       sum(CASE WHEN 'Episodic' IN lbls THEN 1 ELSE 0 END) AS episodes,
       sum(CASE WHEN 'Entity' IN lbls THEN 1 ELSE 0 END) AS entities
ORDER BY total_nodes DESC;

// -----------------------------------------------------------------------------
// 2. Relationship Counts by Group
// Returns: Number of relationships per namespace
// Use: Estimate graph density
// -----------------------------------------------------------------------------
MATCH (n1)-[r]->(n2)
WHERE n1.group_id IS NOT NULL
RETURN n1.group_id AS group_id,
       type(r) AS relationship_type,
       count(r) AS relationship_count
ORDER BY group_id, relationship_count DESC;

// -----------------------------------------------------------------------------
// 3. Highly Connected Entities (Hubs)
// Returns: Entities with most relationships
// Use: Identify central concepts that may need special handling
// -----------------------------------------------------------------------------
MATCH (n:Entity)-[r]-()
WITH n, count(r) AS connection_count
ORDER BY connection_count DESC
LIMIT 30
RETURN n.name AS entity_name,
       n.group_id AS group_id,
       [l IN labels(n) WHERE l <> 'Entity'] AS entity_types,
       connection_count;

// -----------------------------------------------------------------------------
// 4. Average Connections per Entity Type
// Returns: Connectivity statistics by entity label
// Use: Understand which entity types are most connected
// -----------------------------------------------------------------------------
MATCH (n:Entity)-[r]-()
WITH n, [l IN labels(n) WHERE l <> 'Entity'][0] AS entity_type, count(r) AS connections
RETURN entity_type,
       count(n) AS entity_count,
       round(avg(connections), 2) AS avg_connections,
       min(connections) AS min_connections,
       max(connections) AS max_connections
ORDER BY avg_connections DESC;

// -----------------------------------------------------------------------------
// 5. Growth Over Time (Episodes per Month)
// Returns: Episode creation trend
// Use: Forecast storage needs
// -----------------------------------------------------------------------------
MATCH (e:Episodic)
WHERE e.created_at IS NOT NULL
WITH e, date(e.created_at) AS created_date
RETURN created_date.year AS year,
       created_date.month AS month,
       count(e) AS episodes_created
ORDER BY year DESC, month DESC
LIMIT 12;

// -----------------------------------------------------------------------------
// 6. Growth Over Time (Episodes per Week)
// Returns: Recent weekly growth trend
// Use: Monitor ingestion rate
// -----------------------------------------------------------------------------
MATCH (e:Episodic)
WHERE e.created_at > datetime() - duration('P90D')
WITH e, date(e.created_at) AS created_date
WITH e, created_date.year AS year, created_date.week AS week
RETURN year, week, count(e) AS episodes_created
ORDER BY year DESC, week DESC;

// -----------------------------------------------------------------------------
// 7. Embedding Storage Estimate
// Returns: Count of nodes with embeddings
// Use: Estimate vector storage requirements
// Note: Each embedding is ~4KB (1024 dimensions * 4 bytes)
// -----------------------------------------------------------------------------
MATCH (n:Entity)
RETURN count(n) AS total_entities,
       sum(CASE WHEN n.name_embedding IS NOT NULL THEN 1 ELSE 0 END) AS with_embeddings,
       sum(CASE WHEN n.name_embedding IS NOT NULL THEN 1 ELSE 0 END) * 4 AS estimated_embedding_kb;

// -----------------------------------------------------------------------------
// 8. Property Usage Analysis
// Returns: Which properties are populated across entities
// Use: Understand data completeness
// -----------------------------------------------------------------------------
MATCH (n:Entity)
RETURN count(n) AS total_entities,
       sum(CASE WHEN n.name IS NOT NULL THEN 1 ELSE 0 END) AS has_name,
       sum(CASE WHEN n.summary IS NOT NULL THEN 1 ELSE 0 END) AS has_summary,
       sum(CASE WHEN n.name_embedding IS NOT NULL THEN 1 ELSE 0 END) AS has_embedding,
       sum(CASE WHEN n.attributes IS NOT NULL THEN 1 ELSE 0 END) AS has_attributes;

// -----------------------------------------------------------------------------
// 9. Index Status Check
// Returns: All indexes in the database
// Use: Verify search indexes are created
// -----------------------------------------------------------------------------
SHOW INDEXES
YIELD name, type, labelsOrTypes, properties, state
RETURN name, type, labelsOrTypes, properties, state
ORDER BY labelsOrTypes, name;

// -----------------------------------------------------------------------------
// 10. Constraint Status Check
// Returns: All constraints in the database
// Use: Verify data integrity constraints
// -----------------------------------------------------------------------------
SHOW CONSTRAINTS
YIELD name, type, labelsOrTypes, properties
RETURN name, type, labelsOrTypes, properties
ORDER BY labelsOrTypes, name;

// -----------------------------------------------------------------------------
// 11. Database Size Projection
// Returns: Current size and simple growth projection
// Use: Plan for future capacity
// -----------------------------------------------------------------------------
MATCH (n)
WITH count(n) AS current_nodes
MATCH ()-[r]->()
WITH current_nodes, count(r) AS current_rels
RETURN current_nodes,
       current_rels,
       current_nodes + current_rels AS total_elements,
       // Assuming 10% monthly growth
       round((current_nodes + current_rels) * 1.1) AS projected_1_month,
       round((current_nodes + current_rels) * 1.33) AS projected_3_months,
       round((current_nodes + current_rels) * 1.77) AS projected_6_months;
