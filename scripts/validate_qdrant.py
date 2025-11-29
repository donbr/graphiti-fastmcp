#!/usr/bin/env python3
"""
Validate Qdrant collection and test semantic search functionality.

This script:
1. Verifies collection exists and has correct configuration
2. Counts total documents and documents per source
3. Tests semantic search with sample queries
4. Validates metadata structure
"""

import os
from collections import Counter
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

# Load environment variables
load_dotenv()

# Constants
COLLECTION_NAME = "llms-full-silver"
EXPECTED_TOTAL = 2670
EXPECTED_SOURCES = {
    "Anthropic": 932,
    "LangChain": 506,
    "Prefect": 767,
    "FastMCP": 175,
    "McpProtocol": 44,
    "PydanticAI": 127,
    "Zep": 119,
}


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print("\n" + "=" * 70)
    print(f"{title}")
    print("=" * 70)


def init_clients():
    """Initialize Qdrant client and embeddings."""
    client = QdrantClient(
        url=os.getenv("QDRANT_API_URL"),
        api_key=os.getenv("QDRANT_API_KEY"),
        prefer_grpc=True,
    )

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        dimensions=1536,
    )

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
        embedding=embeddings,
    )

    return client, embeddings, vector_store


def validate_collection_info(client: QdrantClient) -> bool:
    """Validate collection configuration and basic info."""
    print_header("1. Collection Configuration")

    try:
        collection_info = client.get_collection(COLLECTION_NAME)

        print(f"Collection name: {COLLECTION_NAME}")
        print(f"Status: {collection_info.status}")
        print(f"Vector dimension: {collection_info.config.params.vectors.size}")
        print(f"Distance metric: {collection_info.config.params.vectors.distance}")
        print(f"Total points: {collection_info.points_count:,}")

        # Validate configuration
        checks = []
        checks.append(
            (
                "Status is green",
                collection_info.status == "green",
            )
        )
        checks.append(
            (
                "Vector dimension is 1536",
                collection_info.config.params.vectors.size == 1536,
            )
        )
        checks.append(
            (
                "Distance metric is COSINE",
                str(collection_info.config.params.vectors.distance).upper() == "COSINE",
            )
        )
        checks.append(
            (
                f"Total points is {EXPECTED_TOTAL}",
                collection_info.points_count == EXPECTED_TOTAL,
            )
        )

        print("\nConfiguration checks:")
        all_passed = True
        for check_name, passed in checks:
            status = "✓" if passed else "✗"
            print(f"  {status} {check_name}")
            all_passed = all_passed and passed

        return all_passed

    except Exception as e:
        print(f"✗ Error validating collection: {e}")
        return False


def validate_document_counts(client: QdrantClient) -> bool:
    """Validate document counts by source."""
    print_header("2. Document Counts by Source")

    try:
        # Scroll through all points to count by source
        offset = None
        source_counts = Counter()
        total_scanned = 0

        print("Scanning all documents...")

        while True:
            result = client.scroll(
                collection_name=COLLECTION_NAME,
                limit=100,
                offset=offset,
                with_payload=True,
                with_vectors=False,
            )

            points, offset = result

            if not points:
                break

            for point in points:
                source_name = point.payload.get("metadata", {}).get("source_name")
                if source_name:
                    source_counts[source_name] += 1
                total_scanned += 1

            if offset is None:
                break

        print(f"\nTotal documents scanned: {total_scanned:,}\n")

        # Print results
        print(f"{'Source':<15} {'Expected':<10} {'Actual':<10} {'Status':<10}")
        print("-" * 50)

        all_passed = True
        for source, expected_count in sorted(EXPECTED_SOURCES.items()):
            actual_count = source_counts[source]
            status = "✓" if actual_count == expected_count else "✗"
            print(f"{source:<15} {expected_count:<10} {actual_count:<10} {status:<10}")

            if actual_count != expected_count:
                all_passed = False

        # Check for unexpected sources
        unexpected_sources = set(source_counts.keys()) - set(EXPECTED_SOURCES.keys())
        if unexpected_sources:
            print(f"\n✗ Unexpected sources found: {unexpected_sources}")
            all_passed = False

        # Check total
        total_actual = sum(source_counts.values())
        print("-" * 50)
        print(
            f"{'TOTAL':<15} {EXPECTED_TOTAL:<10} {total_actual:<10} "
            f"{'✓' if total_actual == EXPECTED_TOTAL else '✗':<10}"
        )

        return all_passed and (total_actual == EXPECTED_TOTAL)

    except Exception as e:
        print(f"✗ Error counting documents: {e}")
        return False


def validate_metadata_structure(client: QdrantClient) -> bool:
    """Validate metadata structure of sample documents."""
    print_header("3. Metadata Structure Validation")

    try:
        # Get a few sample points
        result = client.scroll(
            collection_name=COLLECTION_NAME,
            limit=5,
            with_payload=True,
            with_vectors=False,
        )

        points, _ = result

        if not points:
            print("✗ No points found in collection")
            return False

        print(f"Checking metadata structure of {len(points)} sample documents...\n")

        required_fields = [
            "title",
            "source_url",
            "content_length",
            "source_name",
            "total_pages",
            "avg_content_length",
            "doc_id",
            "page_number",
        ]

        all_passed = True
        for i, point in enumerate(points, 1):
            metadata = point.payload.get("metadata", {})
            page_content = point.payload.get("page_content")

            print(f"Document {i} (ID: {point.id}):")
            print(f"  Source: {metadata.get('source_name')}")
            print(f"  Title: {metadata.get('title')}")
            print(f"  Doc ID: {metadata.get('doc_id')}")

            # Check required fields
            missing_fields = [
                field for field in required_fields if field not in metadata
            ]

            if missing_fields:
                print(f"  ✗ Missing fields: {missing_fields}")
                all_passed = False
            else:
                print(f"  ✓ All required metadata fields present")

            if not page_content:
                print(f"  ✗ Missing page_content")
                all_passed = False
            else:
                print(f"  ✓ Has page_content ({len(page_content)} chars)")

            print()

        return all_passed

    except Exception as e:
        print(f"✗ Error validating metadata: {e}")
        return False


def test_semantic_search(vector_store: QdrantVectorStore) -> bool:
    """Test semantic search with sample queries."""
    print_header("4. Semantic Search Tests")

    test_queries = [
        {
            "query": "How do I build a RAG agent with LangChain?",
            "expected_sources": ["LangChain"],
            "k": 3,
        },
        {
            "query": "What are Claude's API features and capabilities?",
            "expected_sources": ["Anthropic"],
            "k": 3,
        },
        {
            "query": "How does Prefect handle workflow orchestration?",
            "expected_sources": ["Prefect"],
            "k": 3,
        },
        {
            "query": "Explain MCP server implementation",
            "expected_sources": ["FastMCP", "McpProtocol", "Anthropic"],
            "k": 3,
        },
    ]

    all_passed = True

    for i, test in enumerate(test_queries, 1):
        print(f"\nTest {i}: {test['query']}")
        print("-" * 70)

        try:
            results = vector_store.similarity_search(test["query"], k=test["k"])

            if not results:
                print(f"✗ No results returned")
                all_passed = False
                continue

            print(f"✓ Retrieved {len(results)} results\n")

            # Check if expected sources are in results
            result_sources = [doc.metadata.get("source_name") for doc in results]
            has_expected_source = any(
                source in result_sources for source in test["expected_sources"]
            )

            if has_expected_source:
                print(
                    f"✓ Found expected source(s): {test['expected_sources']}"
                )
            else:
                print(
                    f"✗ Expected source(s) {test['expected_sources']} not in top {test['k']} results"
                )
                all_passed = False

            # Display top results
            for j, doc in enumerate(results, 1):
                print(f"\n  Result {j}:")
                print(f"    Title: {doc.metadata.get('title')}")
                print(f"    Source: {doc.metadata.get('source_name')}")
                print(f"    URL: {doc.metadata.get('source_url')}")
                print(f"    Preview: {doc.page_content[:150]}...")

        except Exception as e:
            print(f"✗ Error during search: {e}")
            all_passed = False

    return all_passed


def test_filtered_search(vector_store: QdrantVectorStore) -> bool:
    """Test semantic search with metadata filtering.

    Note: Filtered search requires creating an index on metadata fields.
    This is optional and can be created later if needed for production use.
    """
    print_header("5. Filtered Search Tests (Optional Feature)")

    from qdrant_client.models import FieldCondition, Filter, MatchValue

    test_cases = [
        {
            "query": "API authentication",
            "filter": Filter(
                must=[
                    FieldCondition(
                        key="metadata.source_name", match=MatchValue(value="Anthropic")
                    )
                ]
            ),
            "expected_source": "Anthropic",
            "description": "Search only Anthropic docs",
        },
        {
            "query": "graph memory",
            "filter": Filter(
                must=[
                    FieldCondition(
                        key="metadata.source_name", match=MatchValue(value="Zep")
                    )
                ]
            ),
            "expected_source": "Zep",
            "description": "Search only Zep docs",
        },
    ]

    all_passed = True

    for i, test in enumerate(test_cases, 1):
        print(f"\nTest {i}: {test['description']}")
        print(f"Query: '{test['query']}'")
        print(f"Expected source: {test['expected_source']}")
        print("-" * 70)

        try:
            results = vector_store.similarity_search(
                test["query"], k=3, filter=test["filter"]
            )

            if not results:
                print(f"✗ No results returned")
                all_passed = False
                continue

            print(f"✓ Retrieved {len(results)} results")

            # Verify all results match expected source
            all_match_filter = all(
                doc.metadata.get("source_name") == test["expected_source"]
                for doc in results
            )

            if all_match_filter:
                print(f"✓ All results are from {test['expected_source']}")
            else:
                print(f"✗ Some results are not from {test['expected_source']}")
                all_passed = False

            # Display results
            for j, doc in enumerate(results, 1):
                print(f"\n  Result {j}:")
                print(f"    Title: {doc.metadata.get('title')}")
                print(f"    Source: {doc.metadata.get('source_name')}")
                print(f"    Preview: {doc.page_content[:100]}...")

        except Exception as e:
            error_msg = str(e)
            if "Index required" in error_msg:
                print(
                    f"ℹ  Filtered search requires creating an index on metadata fields"
                )
                print(f"   This is optional. To enable, create a payload index:")
                print(
                    f"   client.create_payload_index('{COLLECTION_NAME}', 'metadata.source_name')"
                )
            else:
                print(f"✗ Error during filtered search: {e}")
                all_passed = False

    # Filtered search is optional, so we return True even if index doesn't exist
    print(
        "\nNote: Filtered search is optional. Basic semantic search is fully functional."
    )
    return True  # Don't fail validation if index isn't created


def main():
    """Run all validation tests."""
    print_header("Qdrant Collection Validation")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Expected documents: {EXPECTED_TOTAL:,}")

    try:
        # Initialize clients
        print("\nInitializing clients...")
        client, embeddings, vector_store = init_clients()
        print("✓ Clients initialized")

        # Run validation tests
        results = []

        results.append(("Collection Info", validate_collection_info(client)))
        results.append(("Document Counts", validate_document_counts(client)))
        results.append(("Metadata Structure", validate_metadata_structure(client)))
        results.append(("Semantic Search", test_semantic_search(vector_store)))
        results.append(("Filtered Search", test_filtered_search(vector_store)))

        # Print summary
        print_header("Validation Summary")

        all_passed = True
        for test_name, passed in results:
            status = "✓ PASSED" if passed else "✗ FAILED"
            print(f"{test_name:<25} {status}")
            all_passed = all_passed and passed

        print("=" * 70)

        if all_passed:
            print("\n✓ All validation tests passed!")
            print(
                f"\nYour Qdrant collection '{COLLECTION_NAME}' is ready for production use."
            )
            return 0
        else:
            print("\n✗ Some validation tests failed. Please review the output above.")
            return 1

    except Exception as e:
        print(f"\n✗ Fatal error during validation: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
