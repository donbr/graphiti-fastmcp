"""
Tests for the Neo4j Memory to Graphiti migration system.

Tests cover:
- Entity classification logic
- Entity-to-episode conversion
- Migration state serialization
- Rate limiter behavior
"""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Import migration module components
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from migration.orchestrate_migration import (
    MIGRATION_GROUPS,
    GroupConfig,
    MigrationState,
    Priority,
    ProcessingMode,
    RateLimiter,
    classify_entity,
    convert_entity_to_episode,
    load_agent_definition,
    load_state,
    save_state,
)


# ============================================================================
# classify_entity Tests
# ============================================================================

class TestClassifyEntity:
    """Tests for the entity classification function."""

    def test_don_branson_person(self):
        """Don Branson should go to don_branson_career."""
        entity = {"name": "Don Branson", "type": "person", "observations": []}
        assert classify_entity(entity) == "don_branson_career"

    def test_experience_entity(self):
        """Experience entities should go to don_branson_career."""
        entity = {"name": "IBM Application Architect", "type": "Experience", "observations": []}
        assert classify_entity(entity) == "don_branson_career"

    def test_skills_entity(self):
        """Skills entities should go to don_branson_career."""
        entity = {"name": "Technical Skills", "type": "Skills", "observations": []}
        assert classify_entity(entity) == "don_branson_career"

    def test_credentials_entity(self):
        """Credentials entities should go to don_branson_career."""
        entity = {"name": "Certifications", "type": "Credentials", "observations": []}
        assert classify_entity(entity) == "don_branson_career"

    def test_don_branson_project(self):
        """Don's specific projects should go to don_branson_career."""
        entity = {"name": "kg_rememberall", "type": "Project", "observations": []}
        assert classify_entity(entity) == "don_branson_career"

        entity = {"name": "nsclc-pathways", "type": "Project", "observations": []}
        assert classify_entity(entity) == "don_branson_career"

        entity = {"name": "GDELT Explorer", "type": "Project", "observations": []}
        assert classify_entity(entity) == "don_branson_career"

    def test_disney_organization(self):
        """Disney organizations should go to disney_knowledge."""
        entity = {"name": "Disney Studios", "type": "Organization", "observations": []}
        assert classify_entity(entity) == "disney_knowledge"

    def test_disney_team(self):
        """Disney teams should go to disney_knowledge."""
        entity = {"name": "Disney Data Platform Team", "type": "Team", "observations": []}
        assert classify_entity(entity) == "disney_knowledge"

    def test_buying_center(self):
        """BuyingCenter entities should go to disney_knowledge."""
        entity = {"name": "OTE", "type": "BuyingCenter", "observations": []}
        assert classify_entity(entity) == "disney_knowledge"

    def test_content_genome(self):
        """Content Genome should go to disney_knowledge."""
        entity = {"name": "Content Genome", "type": "Technology", "observations": []}
        assert classify_entity(entity) == "disney_knowledge"

    def test_job_posting(self):
        """JobPosting entities should go to career_opportunities."""
        entity = {"name": "ML Engineer Role", "type": "JobPosting", "observations": []}
        assert classify_entity(entity) == "career_opportunities"

    def test_recruiter_in_observations(self):
        """Entities with recruiter mention should go to career_opportunities."""
        entity = {
            "name": "Some Person",
            "type": "person",
            "observations": ["Works as a recruiter at Apollo"]
        }
        assert classify_entity(entity) == "career_opportunities"

    def test_pattern_entity(self):
        """Pattern entities should go to technical_patterns."""
        entity = {"name": "ReAct Pattern", "type": "Pattern", "observations": []}
        assert classify_entity(entity) == "technical_patterns"

    def test_architecture_entity(self):
        """Architecture entities should go to technical_patterns."""
        entity = {"name": "Medallion Architecture", "type": "Architecture", "observations": []}
        assert classify_entity(entity) == "technical_patterns"

    def test_research_entity(self):
        """Research entities should go to ai_engineering_research."""
        entity = {"name": "GraphRAG Study", "type": "research", "observations": []}
        assert classify_entity(entity) == "ai_engineering_research"

    def test_generic_project(self):
        """Generic projects (not Don's) should go to ai_engineering_research."""
        entity = {"name": "Some Other Project", "type": "Project", "observations": []}
        assert classify_entity(entity) == "ai_engineering_research"

    def test_unknown_entity_type(self):
        """Unknown entity types should default to ai_engineering_research."""
        entity = {"name": "Unknown Thing", "type": "UnknownType", "observations": []}
        assert classify_entity(entity) == "ai_engineering_research"

    def test_empty_entity(self):
        """Empty entity should default to ai_engineering_research."""
        entity = {}
        assert classify_entity(entity) == "ai_engineering_research"


# ============================================================================
# convert_entity_to_episode Tests
# ============================================================================

class TestConvertEntityToEpisode:
    """Tests for the entity-to-episode conversion function."""

    def test_experience_entity_json_format(self):
        """Experience entities should produce JSON episodes."""
        entity = {
            "name": "IBM Application Architect",
            "type": "Experience",
            "observations": ["14 years", "Enterprise integration"]
        }
        episode = convert_entity_to_episode(entity, "don_branson_career")

        assert episode["name"] == "IBM Application Architect - Experience"
        assert episode["source"] == "json"
        assert episode["group_id"] == "don_branson_career"
        assert "Migrated from Neo4j Memory" in episode["source_description"]

        # Verify JSON body
        body = json.loads(episode["episode_body"])
        assert body["name"] == "IBM Application Architect"
        assert body["type"] == "Experience"
        assert body["details"] == ["14 years", "Enterprise integration"]
        assert body["migrated_from"] == "neo4j_memory"

    def test_job_posting_json_format(self):
        """JobPosting entities should produce JSON episodes."""
        entity = {
            "name": "Disney ML Engineer",
            "type": "JobPosting",
            "observations": ["$150K-$200K", "LangGraph required"]
        }
        episode = convert_entity_to_episode(entity, "career_opportunities")

        assert episode["source"] == "json"
        body = json.loads(episode["episode_body"])
        assert body["type"] == "JobPosting"

    def test_credentials_json_format(self):
        """Credentials entities should produce JSON episodes."""
        entity = {
            "name": "AWS Certifications",
            "type": "Credentials",
            "observations": ["AWS Developer", "AWS Solutions Architect"]
        }
        episode = convert_entity_to_episode(entity, "don_branson_career")

        assert episode["source"] == "json"

    def test_skills_json_format(self):
        """Skills entities should produce JSON episodes."""
        entity = {
            "name": "Technical Skills",
            "type": "Skills",
            "observations": ["Python", "Neo4j", "GraphRAG"]
        }
        episode = convert_entity_to_episode(entity, "don_branson_career")

        assert episode["source"] == "json"

    def test_person_entity_text_format(self):
        """Person entities should produce text episodes."""
        entity = {
            "name": "Don Branson",
            "type": "person",
            "observations": ["AI Engineer", "Neo4j Certified"]
        }
        episode = convert_entity_to_episode(entity, "don_branson_career")

        assert episode["name"] == "Don Branson - person"
        assert episode["source"] == "text"
        assert episode["group_id"] == "don_branson_career"

        # Verify text body format
        assert "Don Branson (person):" in episode["episode_body"]
        assert "- AI Engineer" in episode["episode_body"]
        assert "- Neo4j Certified" in episode["episode_body"]

    def test_organization_text_format(self):
        """Organization entities should produce text episodes."""
        entity = {
            "name": "Disney Studios",
            "type": "Organization",
            "observations": ["Entertainment company", "Glendale, CA"]
        }
        episode = convert_entity_to_episode(entity, "disney_knowledge")

        assert episode["source"] == "text"
        assert "Disney Studios (Organization):" in episode["episode_body"]

    def test_pattern_text_format(self):
        """Pattern entities should produce text episodes."""
        entity = {
            "name": "ReAct Pattern",
            "type": "Pattern",
            "observations": ["Reasoning + Acting", "Used in agents"]
        }
        episode = convert_entity_to_episode(entity, "technical_patterns")

        assert episode["source"] == "text"

    def test_empty_observations(self):
        """Entities with no observations should still convert."""
        entity = {"name": "Empty Entity", "type": "unknown", "observations": []}
        episode = convert_entity_to_episode(entity, "ai_engineering_research")

        assert episode["name"] == "Empty Entity - unknown"
        # Text format with empty observations
        assert "Empty Entity (unknown):" in episode["episode_body"]

    def test_migration_timestamp_in_json(self):
        """JSON episodes should include migration timestamp."""
        entity = {
            "name": "Test Experience",
            "type": "Experience",
            "observations": []
        }
        episode = convert_entity_to_episode(entity, "don_branson_career")

        body = json.loads(episode["episode_body"])
        assert "migration_date" in body
        # Verify it's a valid ISO timestamp
        datetime.fromisoformat(body["migration_date"].replace("Z", "+00:00"))


# ============================================================================
# MigrationState Tests
# ============================================================================

class TestMigrationState:
    """Tests for migration state management."""

    def test_default_state(self):
        """Default state should have empty values."""
        state = MigrationState()

        assert state.started_at == ""
        assert state.current_phase == 0
        assert state.completed_groups == []
        assert state.in_progress_group is None
        assert state.completed_episodes == {}
        assert state.failed_episodes == {}
        assert state.validation_results == {}
        assert state.errors == []

    def test_to_json(self):
        """State should serialize to JSON correctly."""
        state = MigrationState(
            started_at="2025-12-12T10:00:00Z",
            current_phase=2,
            completed_groups=["don_branson_career"],
            in_progress_group="disney_knowledge",
            completed_episodes={"don_branson_career": ["entity1", "entity2"]},
        )

        json_data = state.to_json()

        assert json_data["started_at"] == "2025-12-12T10:00:00Z"
        assert json_data["current_phase"] == 2
        assert json_data["completed_groups"] == ["don_branson_career"]
        assert json_data["in_progress_group"] == "disney_knowledge"
        assert "don_branson_career" in json_data["completed_episodes"]

    def test_from_json(self):
        """State should deserialize from JSON correctly."""
        json_data = {
            "started_at": "2025-12-12T10:00:00Z",
            "current_phase": 3,
            "completed_groups": ["g1", "g2"],
            "in_progress_group": "g3",
            "completed_episodes": {"g1": ["e1"], "g2": ["e2", "e3"]},
            "failed_episodes": {"g1": [{"name": "bad", "error": "failed"}]},
            "validation_results": {"g1": {"pass": True}},
            "errors": [{"msg": "error1"}],
            "last_checkpoint": "2025-12-12T11:00:00Z",
        }

        state = MigrationState.from_json(json_data)

        assert state.started_at == "2025-12-12T10:00:00Z"
        assert state.current_phase == 3
        assert state.completed_groups == ["g1", "g2"]
        assert state.in_progress_group == "g3"
        assert len(state.completed_episodes["g1"]) == 1
        assert len(state.completed_episodes["g2"]) == 2

    def test_from_json_partial(self):
        """State should handle partial JSON data gracefully."""
        json_data = {"started_at": "2025-12-12T10:00:00Z"}

        state = MigrationState.from_json(json_data)

        assert state.started_at == "2025-12-12T10:00:00Z"
        assert state.current_phase == 0  # Default
        assert state.completed_groups == []  # Default

    def test_roundtrip(self):
        """State should survive JSON roundtrip."""
        original = MigrationState(
            started_at="2025-12-12T10:00:00Z",
            current_phase=2,
            completed_groups=["g1"],
            in_progress_group="g2",
            completed_episodes={"g1": ["e1", "e2"]},
            errors=[{"error": "test"}],
        )

        json_data = original.to_json()
        restored = MigrationState.from_json(json_data)

        assert restored.started_at == original.started_at
        assert restored.current_phase == original.current_phase
        assert restored.completed_groups == original.completed_groups
        assert restored.in_progress_group == original.in_progress_group
        assert restored.completed_episodes == original.completed_episodes

    def test_progress_summary(self):
        """Progress summary should calculate correct totals."""
        state = MigrationState(
            completed_groups=["g1", "g2"],
            completed_episodes={"g1": ["e1", "e2"], "g2": ["e3"]},
            failed_episodes={"g1": [{"name": "bad"}]},
            in_progress_group="g3",
            last_checkpoint="2025-12-12T12:00:00Z",
        )

        summary = state.get_progress_summary()

        assert summary["phases_completed"] == 2
        assert summary["episodes_completed"] == 3
        assert summary["episodes_failed"] == 1
        assert summary["current_group"] == "g3"


class TestStatePersistence:
    """Tests for state file persistence."""

    def test_save_and_load_state(self, tmp_path):
        """State should save and load from file correctly."""
        state_file = tmp_path / "migration_state.json"

        # Temporarily override STATE_FILE
        import migration.orchestrate_migration as module
        original_state_file = module.STATE_FILE
        module.STATE_FILE = state_file

        try:
            # Create and save state
            state = MigrationState(
                started_at="2025-12-12T10:00:00Z",
                current_phase=1,
                completed_groups=["g1"],
            )
            save_state(state)

            # Verify file exists
            assert state_file.exists()

            # Load and verify
            loaded = load_state()
            assert loaded.started_at == "2025-12-12T10:00:00Z"
            assert loaded.current_phase == 1
            assert loaded.completed_groups == ["g1"]
            assert loaded.last_checkpoint != ""  # Should be set by save

        finally:
            module.STATE_FILE = original_state_file

    def test_load_nonexistent_state(self, tmp_path):
        """Loading nonexistent state should return default."""
        state_file = tmp_path / "nonexistent.json"

        import migration.orchestrate_migration as module
        original_state_file = module.STATE_FILE
        module.STATE_FILE = state_file

        try:
            state = load_state()
            assert state.started_at == ""
            assert state.completed_groups == []
        finally:
            module.STATE_FILE = original_state_file


# ============================================================================
# RateLimiter Tests
# ============================================================================

class TestRateLimiter:
    """Tests for the rate limiter."""

    def test_initial_state(self):
        """Rate limiter should start with no backoff."""
        limiter = RateLimiter()

        assert limiter.last_call_time == {}
        assert limiter.backoff_multiplier == {}

    def test_record_error_increases_backoff(self):
        """Recording an error should increase backoff."""
        limiter = RateLimiter()

        limiter.record_error("test_key")
        assert limiter.backoff_multiplier["test_key"] == 2.0

        limiter.record_error("test_key")
        assert limiter.backoff_multiplier["test_key"] == 4.0

        limiter.record_error("test_key")
        assert limiter.backoff_multiplier["test_key"] == 8.0

    def test_backoff_caps_at_maximum(self):
        """Backoff should cap at 16x."""
        limiter = RateLimiter()

        for _ in range(10):
            limiter.record_error("test_key")

        assert limiter.backoff_multiplier["test_key"] == 16.0

    def test_record_success_decreases_backoff(self):
        """Recording success should decrease backoff."""
        limiter = RateLimiter()

        # Build up backoff
        limiter.backoff_multiplier["test_key"] = 8.0

        limiter.record_success("test_key")
        assert limiter.backoff_multiplier["test_key"] == 4.0

        limiter.record_success("test_key")
        assert limiter.backoff_multiplier["test_key"] == 2.0

        limiter.record_success("test_key")
        assert limiter.backoff_multiplier["test_key"] == 1.0

    def test_backoff_floors_at_one(self):
        """Backoff should not go below 1.0."""
        limiter = RateLimiter()

        limiter.backoff_multiplier["test_key"] = 1.0
        limiter.record_success("test_key")

        assert limiter.backoff_multiplier["test_key"] == 1.0

    def test_success_on_unknown_key(self):
        """Success on unknown key should not error."""
        limiter = RateLimiter()

        # Should not raise
        limiter.record_success("unknown_key")

        # Key should not be added
        assert "unknown_key" not in limiter.backoff_multiplier


# ============================================================================
# Agent Definition Loading Tests
# ============================================================================

class TestAgentDefinitionLoading:
    """Tests for agent definition loading."""

    def test_load_valid_agent(self, tmp_path):
        """Valid agent definition should load correctly."""
        agent_file = tmp_path / "test_agent.json"
        agent_data = {
            "name": "test_agent",
            "description": "Test agent",
            "prompt": "You are a test agent",
            "tools": ["Read", "Write"],
            "model": "sonnet"
        }
        agent_file.write_text(json.dumps(agent_data))

        # Temporarily override AGENTS_DIR
        import migration.orchestrate_migration as module
        original_agents_dir = module.AGENTS_DIR
        module.AGENTS_DIR = tmp_path

        try:
            loaded = load_agent_definition("test_agent")
            assert loaded["name"] == "test_agent"
            assert loaded["model"] == "sonnet"
            assert "Read" in loaded["tools"]
        finally:
            module.AGENTS_DIR = original_agents_dir

    def test_load_nonexistent_agent(self):
        """Loading nonexistent agent should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_agent_definition("nonexistent_agent_xyz")

    def test_load_invalid_json_agent(self, tmp_path):
        """Invalid JSON should raise ValueError with helpful message."""
        agent_file = tmp_path / "bad_agent.json"
        agent_file.write_text("{ invalid json }")

        import migration.orchestrate_migration as module
        original_agents_dir = module.AGENTS_DIR
        module.AGENTS_DIR = tmp_path

        try:
            with pytest.raises(ValueError, match="Invalid JSON in agent definition"):
                load_agent_definition("bad_agent")
        finally:
            module.AGENTS_DIR = original_agents_dir


# ============================================================================
# GroupConfig Tests
# ============================================================================

class TestGroupConfig:
    """Tests for migration group configuration."""

    def test_migration_groups_defined(self):
        """All 5 migration groups should be defined."""
        assert len(MIGRATION_GROUPS) == 5

    def test_priority_ordering(self):
        """Groups should have correct priorities."""
        priorities = {g.group_id: g.priority for g in MIGRATION_GROUPS}

        assert priorities["don_branson_career"] == Priority.CRITICAL
        assert priorities["disney_knowledge"] == Priority.HIGH
        assert priorities["career_opportunities"] == Priority.MEDIUM
        assert priorities["technical_patterns"] == Priority.MEDIUM
        assert priorities["ai_engineering_research"] == Priority.LOW

    def test_processing_modes(self):
        """Groups should have correct processing modes."""
        modes = {g.group_id: g.mode for g in MIGRATION_GROUPS}

        assert modes["don_branson_career"] == ProcessingMode.SEQUENTIAL
        assert modes["disney_knowledge"] == ProcessingMode.BATCH
        assert modes["career_opportunities"] == ProcessingMode.BATCH

    def test_all_groups_have_expected_episodes(self):
        """All groups should have expected episode counts > 0."""
        for group in MIGRATION_GROUPS:
            assert group.expected_episodes > 0, f"{group.group_id} has no expected episodes"

    def test_critical_group_has_key_entities(self):
        """Critical group should have key entities defined."""
        critical = next(g for g in MIGRATION_GROUPS if g.priority == Priority.CRITICAL)
        assert len(critical.key_entities) > 0
        assert "Don Branson" in critical.key_entities
