#!/usr/bin/env python3
"""
Validation script for disney_knowledge migration group.

This script validates the migration quality by checking:
1. Episode count (expected ~80, pass if >= 64)
2. Key entity discovery (Disney Studios, OTE, DEEPT, Data Platform Team, Content Genome)
3. Fact validation queries
4. Semantic search quality
"""

import asyncio
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
from graphiti_core import Graphiti
from graphiti_core.search.search_config_recipes import NODE_HYBRID_SEARCH_RRF

from src.config.schema import GraphitiConfig
from src.services.factories import DatabaseDriverFactory, EmbedderFactory, LLMClientFactory
from src.server import Neo4jDriverWithPoolConfig

# Load environment
env_file = PROJECT_ROOT / '.env'
if env_file.exists():
    load_dotenv(env_file)
else:
    load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Validation configuration
GROUP_ID = "disney_knowledge"
EXPECTED_EPISODES = 80
PASS_THRESHOLD = 0.8  # 80%

KEY_ENTITIES = [
    "Disney Studios",
    "OTE",
    "DEEPT",
    "Data Platform Team",
    "Content Genome",
]

VALIDATION_QUERIES = [
    "Disney Content Genome technology",
    "Disney organizational structure teams",
]

MIN_FACTS_PER_QUERY = 3


async def initialize_graphiti_client() -> Graphiti:
    """Initialize Graphiti client for validation."""
    config = GraphitiConfig()

    try:
        llm_client = None
        embedder_client = None

        try:
            llm_client = LLMClientFactory.create(config.llm)
        except Exception as e:
            logger.warning(f'LLM client creation failed (not required for validation): {e}')

        try:
            embedder_client = EmbedderFactory.create(config.embedder)
        except Exception as e:
            logger.warning(f'Embedder client creation failed: {e}')
            raise

        db_config = DatabaseDriverFactory.create_config(config.database)

        # Use custom Neo4j driver with connection pool configuration
        neo4j_driver = Neo4jDriverWithPoolConfig(
            uri=db_config['uri'],
            user=db_config['user'],
            password=db_config['password'],
            database=db_config.get('database', 'neo4j'),
            max_connection_lifetime=db_config.get('max_connection_lifetime', 300),
            max_connection_pool_size=db_config.get('max_connection_pool_size', 50),
            connection_acquisition_timeout=db_config.get('connection_acquisition_timeout', 60.0),
        )

        client = Graphiti(
            graph_driver=neo4j_driver,
            llm_client=llm_client,
            embedder=embedder_client,
        )

        logger.info('Graphiti client initialized successfully')
        return client

    except Exception as e:
        logger.error(f'Failed to initialize Graphiti client: {e}')
        raise


async def validate_episode_count(client: Graphiti) -> dict:
    """Validate episode count for the group."""
    logger.info(f"Checking episode count for group: {GROUP_ID}")

    from graphiti_core.nodes import EpisodicNode

    try:
        episodes = await EpisodicNode.get_by_group_ids(
            client.driver,
            [GROUP_ID],
            limit=200  # Get more than expected to ensure we capture all
        )

        actual_count = len(episodes)
        pass_threshold = int(EXPECTED_EPISODES * PASS_THRESHOLD)
        passed = actual_count >= pass_threshold

        logger.info(f"Episode count: {actual_count} (expected: {EXPECTED_EPISODES}, threshold: {pass_threshold})")

        return {
            "expected": EXPECTED_EPISODES,
            "actual": actual_count,
            "threshold": pass_threshold,
            "pass": passed,
        }
    except Exception as e:
        logger.error(f"Error validating episode count: {e}")
        return {
            "expected": EXPECTED_EPISODES,
            "actual": 0,
            "threshold": int(EXPECTED_EPISODES * PASS_THRESHOLD),
            "pass": False,
            "error": str(e),
        }


async def validate_entity_discovery(client: Graphiti) -> dict:
    """Validate that key entities can be discovered."""
    logger.info(f"Searching for {len(KEY_ENTITIES)} key entities")

    found_entities = []
    missing_entities = []

    for entity_name in KEY_ENTITIES:
        try:
            # Search for the entity
            results = await client.search_(
                query=entity_name,
                config=NODE_HYBRID_SEARCH_RRF,
                group_ids=[GROUP_ID],
            )

            # Check if any nodes match
            if results.nodes:
                # Look for exact or close match in top results
                found = False
                for node in results.nodes[:5]:  # Check top 5 results
                    if entity_name.lower() in node.name.lower():
                        found = True
                        found_entities.append(entity_name)
                        logger.info(f"  Found: {entity_name} (as '{node.name}')")
                        break

                if not found:
                    logger.warning(f"  Not found: {entity_name} (searched but no match)")
                    missing_entities.append(entity_name)
            else:
                logger.warning(f"  Not found: {entity_name} (no results)")
                missing_entities.append(entity_name)

        except Exception as e:
            logger.error(f"  Error searching for {entity_name}: {e}")
            missing_entities.append(entity_name)

    found_count = len(found_entities)
    required_count = int(len(KEY_ENTITIES) * PASS_THRESHOLD)
    passed = found_count >= required_count

    logger.info(f"Entity discovery: {found_count}/{len(KEY_ENTITIES)} found (required: {required_count})")

    return {
        "expected": KEY_ENTITIES,
        "found": found_entities,
        "missing": missing_entities,
        "found_count": found_count,
        "required_count": required_count,
        "pass": passed,
    }


async def validate_fact_queries(client: Graphiti) -> dict:
    """Validate that fact queries return relevant results."""
    logger.info(f"Testing {len(VALIDATION_QUERIES)} fact queries")

    queries_tested = 0
    queries_passed = 0
    query_results = []

    for query in VALIDATION_QUERIES:
        queries_tested += 1
        try:
            # Search for facts
            facts = await client.search(
                group_ids=[GROUP_ID],
                query=query,
                num_results=10,
            )

            fact_count = len(facts) if facts else 0
            passed = fact_count >= MIN_FACTS_PER_QUERY

            if passed:
                queries_passed += 1
                logger.info(f"  PASS: '{query}' returned {fact_count} facts")
            else:
                logger.warning(f"  FAIL: '{query}' returned {fact_count} facts (required: {MIN_FACTS_PER_QUERY})")

            query_results.append({
                "query": query,
                "fact_count": fact_count,
                "required": MIN_FACTS_PER_QUERY,
                "pass": passed,
            })

        except Exception as e:
            logger.error(f"  ERROR: '{query}' - {e}")
            query_results.append({
                "query": query,
                "fact_count": 0,
                "required": MIN_FACTS_PER_QUERY,
                "pass": False,
                "error": str(e),
            })

    passed = queries_passed == queries_tested

    logger.info(f"Fact validation: {queries_passed}/{queries_tested} queries passed")

    return {
        "queries_tested": queries_tested,
        "queries_passed": queries_passed,
        "query_results": query_results,
        "pass": passed,
    }


async def validate_semantic_search(client: Graphiti) -> dict:
    """Test semantic search quality."""
    logger.info("Testing semantic search quality")

    test_query = "Disney data platform and content analysis"

    try:
        results = await client.search_(
            query=test_query,
            config=NODE_HYBRID_SEARCH_RRF,
            group_ids=[GROUP_ID],
        )

        if results.nodes:
            top_results = results.nodes[:5]
            result_names = [node.name for node in top_results]

            # Check if results are related to Disney/data/content
            relevant_count = sum(
                1 for name in result_names
                if any(keyword in name.lower() for keyword in ['disney', 'data', 'content', 'platform', 'genome'])
            )

            passed = relevant_count >= 2  # At least 2 of top 5 should be relevant

            logger.info(f"  Semantic search: {relevant_count}/5 top results are relevant")
            logger.info(f"  Top results: {result_names}")

            return {
                "queries_tested": 1,
                "top_results": result_names[:5],
                "relevant_count": relevant_count,
                "pass": passed,
            }
        else:
            logger.warning("  No results from semantic search")
            return {
                "queries_tested": 1,
                "top_results": [],
                "relevant_count": 0,
                "pass": False,
            }

    except Exception as e:
        logger.error(f"  Error in semantic search: {e}")
        return {
            "queries_tested": 1,
            "top_results": [],
            "relevant_count": 0,
            "pass": False,
            "error": str(e),
        }


async def run_validation() -> dict:
    """Run all validation checks and generate report."""
    logger.info(f"Starting validation for group: {GROUP_ID}")
    logger.info("="*60)

    client = await initialize_graphiti_client()

    try:
        # Run all validation checks
        episode_validation = await validate_episode_count(client)
        entity_validation = await validate_entity_discovery(client)
        fact_validation = await validate_fact_queries(client)
        semantic_validation = await validate_semantic_search(client)

        # Determine overall pass/fail
        overall_pass = all([
            episode_validation["pass"],
            entity_validation["pass"],
            fact_validation["pass"],
            semantic_validation["pass"],
        ])

        # Collect warnings
        warnings = []
        if not episode_validation["pass"]:
            warnings.append(f"Episode count below threshold: {episode_validation['actual']}/{episode_validation['expected']}")
        if entity_validation["missing"]:
            warnings.append(f"Missing entities: {', '.join(entity_validation['missing'])}")
        if not fact_validation["pass"]:
            warnings.append(f"Some fact queries failed to return sufficient results")
        if not semantic_validation["pass"]:
            warnings.append("Semantic search quality below threshold")

        # Build validation report
        report = {
            "group_id": GROUP_ID,
            "validation_time": datetime.now(timezone.utc).isoformat(),
            "episode_validation": episode_validation,
            "entity_validation": entity_validation,
            "fact_validation": fact_validation,
            "semantic_search": semantic_validation,
            "semantic_drift": {
                "merged": [],  # Would require source comparison
                "split": [],
                "renamed": [],
            },
            "overall_pass": overall_pass,
            "warnings": warnings,
        }

        return report

    finally:
        # Close client
        await client.close()


async def main():
    """Main entry point."""
    try:
        # Run validation
        report = await run_validation()

        # Save report
        output_dir = PROJECT_ROOT / "migration" / "progress"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"validation_{GROUP_ID}.json"

        with open(output_file, 'w') as f:
            json.dump(report, f, indent=2)

        logger.info("="*60)
        logger.info(f"Validation report saved to: {output_file}")

        # Print summary
        print("\n" + "="*60)
        print(f"VALIDATION SUMMARY: {GROUP_ID}")
        print("="*60)
        print(f"Episode Count:    {'PASS' if report['episode_validation']['pass'] else 'FAIL'}")
        print(f"Entity Discovery: {'PASS' if report['entity_validation']['pass'] else 'FAIL'}")
        print(f"Fact Queries:     {'PASS' if report['fact_validation']['pass'] else 'FAIL'}")
        print(f"Semantic Search:  {'PASS' if report['semantic_search']['pass'] else 'FAIL'}")
        print(f"\nOverall Result:   {'PASS' if report['overall_pass'] else 'FAIL'}")

        if report['warnings']:
            print("\nWarnings:")
            for warning in report['warnings']:
                print(f"  - {warning}")

        print("="*60 + "\n")

        # Output result code for orchestrator
        if report['overall_pass']:
            print(f"VALIDATION_PASS:{GROUP_ID}")
            return 0
        else:
            print(f"VALIDATION_FAIL:{GROUP_ID}")
            return 1

    except Exception as e:
        logger.error(f"Validation failed with error: {e}", exc_info=True)
        print(f"VALIDATION_ERROR:{GROUP_ID}")
        return 2


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
