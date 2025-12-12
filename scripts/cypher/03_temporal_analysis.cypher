// =============================================================================
// GRAPHITI TEMPORAL ANALYSIS
// Purpose: Track knowledge evolution and fact lifecycle
// Frequency: As needed for understanding how knowledge changes
// =============================================================================

// -----------------------------------------------------------------------------
// 1. Recently Invalidated Facts
// Returns: Facts that have been superseded by newer information
// Use: Understand how knowledge is evolving
// Note: invalid_at being set means a newer fact replaced this one
// -----------------------------------------------------------------------------
MATCH (n1:Entity)-[r:RELATES_TO]->(n2:Entity)
WHERE r.invalid_at IS NOT NULL
RETURN n1.name AS source_entity,
       r.fact AS fact_description,
       n2.name AS target_entity,
       r.valid_at AS became_valid,
       r.invalid_at AS became_invalid,
       duration.between(r.valid_at, r.invalid_at) AS fact_lifespan
ORDER BY r.invalid_at DESC
LIMIT 30;

// -----------------------------------------------------------------------------
// 2. Currently Valid Facts
// Returns: Facts that are still considered true
// Use: See the current state of knowledge
// -----------------------------------------------------------------------------
MATCH (n1:Entity)-[r:RELATES_TO]->(n2:Entity)
WHERE r.invalid_at IS NULL
RETURN n1.name AS source_entity,
       r.fact AS fact_description,
       n2.name AS target_entity,
       r.valid_at AS valid_since,
       n1.group_id AS group_id
ORDER BY r.valid_at DESC
LIMIT 50;

// -----------------------------------------------------------------------------
// 3. Fact Validity Statistics
// Returns: Summary of valid vs invalidated facts
// Use: Measure knowledge churn rate
// -----------------------------------------------------------------------------
MATCH ()-[r:RELATES_TO]->()
RETURN count(r) AS total_facts,
       sum(CASE WHEN r.invalid_at IS NULL THEN 1 ELSE 0 END) AS valid_facts,
       sum(CASE WHEN r.invalid_at IS NOT NULL THEN 1 ELSE 0 END) AS invalidated_facts,
       round(100.0 * sum(CASE WHEN r.invalid_at IS NOT NULL THEN 1 ELSE 0 END) / count(r), 2) AS churn_rate_pct;

// -----------------------------------------------------------------------------
// 4. Temporal Coverage by Group
// Returns: Date range of facts per namespace
// Use: Understand temporal span of each knowledge graph
// -----------------------------------------------------------------------------
MATCH (n:Entity)-[r:RELATES_TO]->()
WHERE r.valid_at IS NOT NULL
WITH n.group_id AS group_id, r.valid_at AS valid_at
RETURN group_id,
       min(valid_at) AS earliest_fact,
       max(valid_at) AS latest_fact,
       duration.between(min(valid_at), max(valid_at)) AS temporal_span,
       count(*) AS fact_count
ORDER BY latest_fact DESC;

// -----------------------------------------------------------------------------
// 5. Entities with Most Fact Changes
// Returns: Entities whose facts have changed most frequently
// Use: Identify volatile or frequently updated concepts
// -----------------------------------------------------------------------------
MATCH (n:Entity)-[r:RELATES_TO]->()
WHERE r.invalid_at IS NOT NULL
WITH n, count(r) AS invalidation_count
ORDER BY invalidation_count DESC
LIMIT 20
RETURN n.name AS entity_name,
       n.group_id AS group_id,
       invalidation_count AS facts_superseded,
       [l IN labels(n) WHERE l <> 'Entity'] AS entity_types;

// -----------------------------------------------------------------------------
// 6. Knowledge Timeline (Recent Activity)
// Returns: Timeline of fact creation and invalidation
// Use: Visualize knowledge evolution over time
// -----------------------------------------------------------------------------
MATCH (n1:Entity)-[r:RELATES_TO]->(n2:Entity)
WITH r, n1, n2, 'CREATED' AS event_type, r.valid_at AS event_time
WHERE r.valid_at IS NOT NULL
RETURN event_type,
       event_time,
       n1.name AS source,
       n2.name AS target,
       left(r.fact, 80) AS fact_preview
ORDER BY event_time DESC
LIMIT 30;

// -----------------------------------------------------------------------------
// 7. Facts Created in Time Window
// Returns: Facts created within a specific date range
// Use: Audit what was added during a specific period
// Modify the duration as needed (P7D = 7 days, P30D = 30 days)
// -----------------------------------------------------------------------------
MATCH (n1:Entity)-[r:RELATES_TO]->(n2:Entity)
WHERE r.valid_at > datetime() - duration('P7D')
RETURN n1.name AS source_entity,
       r.fact AS fact_description,
       n2.name AS target_entity,
       r.valid_at AS created_at,
       n1.group_id AS group_id
ORDER BY r.valid_at DESC;
