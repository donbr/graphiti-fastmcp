"""Tests for Neo4j 5.x race condition handling during index creation."""

import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.integration
@pytest.mark.requires_neo4j
async def test_neo4j_index_race_condition_handled():
    """Test that EquivalentSchemaRuleAlreadyExists is gracefully handled."""
    from config.schema import ServerConfig
    from src.server import GraphitiService

    # Create a properly configured mock config
    config = MagicMock(spec=ServerConfig)
    config.database = MagicMock()
    config.database.provider = 'neo4j'
    config.llm = MagicMock()
    config.llm.provider = 'openai'
    config.embedder = MagicMock()
    config.embedder.provider = 'openai'
    config.graphiti = MagicMock()
    config.graphiti.group_id = 'test_group'

    service = GraphitiService(config)

    # Mock the Graphiti client to raise the race condition error
    mock_client = AsyncMock()
    mock_error = Exception('Neo.ClientError.Schema.EquivalentSchemaRuleAlreadyExists')
    mock_client.build_indices_and_constraints.side_effect = mock_error

    with (
        patch('src.server.Graphiti', return_value=mock_client),
        patch('services.factories.LLMClientFactory.create', return_value=AsyncMock()),
        patch('services.factories.EmbedderFactory.create', return_value=AsyncMock()),
    ):
        # Should complete without raising
        await service.initialize()

        # Verify client was created
        assert service.client is not None


@pytest.mark.integration
@pytest.mark.requires_neo4j
async def test_neo4j_other_index_errors_are_raised():
    """Test that non-race-condition errors are properly raised."""
    from config.schema import ServerConfig
    from src.server import GraphitiService

    # Create a properly configured mock config
    config = MagicMock(spec=ServerConfig)
    config.database = MagicMock()
    config.database.provider = 'neo4j'
    config.llm = MagicMock()
    config.llm.provider = 'openai'
    config.embedder = MagicMock()
    config.embedder.provider = 'openai'
    config.graphiti = MagicMock()
    config.graphiti.group_id = 'test_group'

    service = GraphitiService(config)

    # Mock the Graphiti client to raise a different error
    mock_client = AsyncMock()
    mock_error = Exception('Some other database error')
    mock_client.build_indices_and_constraints.side_effect = mock_error

    # Should raise the original error
    with (
        patch('src.server.Graphiti', return_value=mock_client),
        patch('services.factories.LLMClientFactory.create', return_value=AsyncMock()),
        patch('services.factories.EmbedderFactory.create', return_value=AsyncMock()),
        pytest.raises(Exception, match='Some other database error'),
    ):
        await service.initialize()


@pytest.mark.integration
@pytest.mark.requires_neo4j
async def test_neo4j_race_condition_logs_warning(caplog):
    """Test that race condition triggers a warning log."""
    from config.schema import ServerConfig
    from src.server import GraphitiService

    # Create a properly configured mock config
    config = MagicMock(spec=ServerConfig)
    config.database = MagicMock()
    config.database.provider = 'neo4j'
    config.llm = MagicMock()
    config.llm.provider = 'openai'
    config.embedder = MagicMock()
    config.embedder.provider = 'openai'
    config.graphiti = MagicMock()
    config.graphiti.group_id = 'test_group'

    service = GraphitiService(config)

    # Mock the Graphiti client to raise the race condition error
    mock_client = AsyncMock()
    mock_error = Exception('Neo.ClientError.Schema.EquivalentSchemaRuleAlreadyExists')
    mock_client.build_indices_and_constraints.side_effect = mock_error

    with (
        caplog.at_level(logging.WARNING),
        patch('src.server.Graphiti', return_value=mock_client),
        patch('services.factories.LLMClientFactory.create', return_value=AsyncMock()),
        patch('services.factories.EmbedderFactory.create', return_value=AsyncMock()),
    ):
        await service.initialize()

        # Verify warning was logged
        assert any(
            'Index creation race condition detected' in record.message
            for record in caplog.records
        )
