#!/usr/bin/env python3
"""
Multi-Agent Migration Orchestrator using Claude Agent SDK.

This script coordinates the Neo4j Memory -> Graphiti migration using:
- Orchestrator agent (Opus) for overall coordination
- Extractor-Sequential worker (Sonnet) for critical data (don_branson_career)
- Extractor-Batch worker (Sonnet) for batch-capable domains
- Validation agent (Sonnet) for quality assurance

Usage:
    # Dry run - show what would be migrated
    uv run python migration/orchestrate_migration.py --dry-run

    # Run specific phase only
    uv run python migration/orchestrate_migration.py --phase 1

    # Resume from checkpoint
    uv run python migration/orchestrate_migration.py --resume

    # Full migration
    uv run python migration/orchestrate_migration.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# Check for SDK availability
try:
    from claude_agent_sdk import (
        ClaudeAgentOptions,
        ClaudeSDKClient,
        HookMatcher,
        create_sdk_mcp_server,
        tool,
    )
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    print("Warning: claude-agent-sdk not installed. Install with: pip install claude-agent-sdk")

# ============================================================================
# Configuration
# ============================================================================

PROJECT_ROOT = Path(__file__).parent.parent
AGENTS_DIR = PROJECT_ROOT / "migration" / "agents"
STATE_FILE = PROJECT_ROOT / "migration" / "progress" / "migration_state.json"
VALIDATION_DIR = PROJECT_ROOT / "migration" / "progress"
LOG_DIR = PROJECT_ROOT / "migration" / "logs"

# Ensure directories exist
STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# Constants (documented magic numbers)
# ============================================================================

# Maximum exponential backoff factor (2^4 = 16x base delay)
MAX_BACKOFF_MULTIPLIER = 16.0

# Maximum seconds to wait between API calls during rate limiting
MAX_RATE_LIMIT_DELAY = 60.0

# Maximum migration runtime in seconds (16 hours)
MAX_MIGRATION_TIMEOUT = 16 * 3600

# Warning threshold for entity observation count
LARGE_ENTITY_OBSERVATION_THRESHOLD = 100


class ProcessingMode(Enum):
    SEQUENTIAL = "sequential"
    BATCH = "batch"


class Priority(Enum):
    CRITICAL = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


@dataclass
class GroupConfig:
    """Configuration for a migration group."""
    group_id: str
    priority: Priority
    mode: ProcessingMode
    expected_episodes: int
    key_entities: list[str] = field(default_factory=list)
    validation_queries: list[str] = field(default_factory=list)
    entity_type_filter: list[str] = field(default_factory=list)


# Migration group configurations from plan v2
MIGRATION_GROUPS = [
    GroupConfig(
        group_id="don_branson_career",
        priority=Priority.CRITICAL,
        mode=ProcessingMode.SEQUENTIAL,
        expected_episodes=50,
        key_entities=[
            "Don Branson",
            "IBM Application Architect",
            "Neo4j Certified Professional",
            "kg_rememberall",
        ],
        validation_queries=[
            "Don Branson IBM experience",
            "Don Branson certifications skills",
        ],
        entity_type_filter=["person", "Experience", "Skills", "Credentials", "Project"],
    ),
    GroupConfig(
        group_id="disney_knowledge",
        priority=Priority.HIGH,
        mode=ProcessingMode.BATCH,
        expected_episodes=80,
        key_entities=[
            "Disney Studios",
            "OTE",
            "DEEPT",
            "Data Platform Team",
            "Content Genome",
        ],
        validation_queries=[
            "Disney Content Genome technology",
            "Disney organizational structure teams",
        ],
        entity_type_filter=["Organization", "Team", "Technology", "BuyingCenter", "Architecture"],
    ),
    GroupConfig(
        group_id="career_opportunities",
        priority=Priority.MEDIUM,
        mode=ProcessingMode.BATCH,
        expected_episodes=20,
        key_entities=[],  # Dynamic based on job postings
        validation_queries=["ML Engineer job requirements salary"],
        entity_type_filter=["JobPosting", "Recruiter"],
    ),
    GroupConfig(
        group_id="technical_patterns",
        priority=Priority.MEDIUM,
        mode=ProcessingMode.BATCH,
        expected_episodes=40,
        key_entities=[
            "SHACL",
            "Medallion Architecture",
            "Kappa Architecture",
            "ReAct Pattern",
        ],
        validation_queries=[
            "SHACL data validation",
            "streaming architecture patterns",
        ],
        entity_type_filter=["Pattern", "Architecture"],
    ),
    GroupConfig(
        group_id="ai_engineering_research",
        priority=Priority.LOW,
        mode=ProcessingMode.BATCH,
        expected_episodes=110,
        key_entities=["LangGraph", "Graphiti", "GraphRAG"],
        validation_queries=["agentic AI multi-agent systems"],
        entity_type_filter=["research", "Project"],
    ),
]

# Rate limiting configuration
RATE_LIMITS = {
    "sequential": {"delay_seconds": 2.0, "batch_size": 1},
    "batch": {"delay_seconds": 0.3, "batch_pause_seconds": 3.0, "batch_size": 10},
}


# ============================================================================
# State Management
# ============================================================================

@dataclass
class MigrationState:
    """Tracks overall migration progress."""
    started_at: str = ""
    current_phase: int = 0
    completed_groups: list[str] = field(default_factory=list)
    in_progress_group: str | None = None
    completed_episodes: dict[str, list[str]] = field(default_factory=dict)
    failed_episodes: dict[str, list[dict]] = field(default_factory=dict)
    validation_results: dict[str, dict] = field(default_factory=dict)
    errors: list[dict] = field(default_factory=list)
    last_checkpoint: str = ""

    def to_json(self) -> dict:
        return {
            "started_at": self.started_at,
            "current_phase": self.current_phase,
            "completed_groups": self.completed_groups,
            "in_progress_group": self.in_progress_group,
            "completed_episodes": self.completed_episodes,
            "failed_episodes": self.failed_episodes,
            "validation_results": self.validation_results,
            "errors": self.errors,
            "last_checkpoint": self.last_checkpoint,
        }

    @classmethod
    def from_json(cls, data: dict) -> MigrationState:
        return cls(
            started_at=data.get("started_at", ""),
            current_phase=data.get("current_phase", 0),
            completed_groups=data.get("completed_groups", []),
            in_progress_group=data.get("in_progress_group"),
            completed_episodes=data.get("completed_episodes", {}),
            failed_episodes=data.get("failed_episodes", {}),
            validation_results=data.get("validation_results", {}),
            errors=data.get("errors", []),
            last_checkpoint=data.get("last_checkpoint", ""),
        )

    def get_progress_summary(self) -> dict:
        """Get a summary of migration progress."""
        total_completed = sum(len(eps) for eps in self.completed_episodes.values())
        total_failed = sum(len(eps) for eps in self.failed_episodes.values())
        return {
            "phases_completed": len(self.completed_groups),
            "phases_total": len(MIGRATION_GROUPS),
            "episodes_completed": total_completed,
            "episodes_failed": total_failed,
            "current_group": self.in_progress_group,
            "last_checkpoint": self.last_checkpoint,
        }


def load_state() -> MigrationState:
    """Load migration state from checkpoint file."""
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return MigrationState.from_json(json.load(f))
    return MigrationState()


def save_state(state: MigrationState) -> None:
    """Save migration state to checkpoint file."""
    state.last_checkpoint = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state.to_json(), f, indent=2)
    logging.debug(f"State saved to {STATE_FILE}")


# ============================================================================
# Agent Definitions Loader
# ============================================================================

def load_agent_definition(agent_name: str) -> dict:
    """Load agent definition from JSON file.

    Args:
        agent_name: Name of the agent (without .json extension)

    Returns:
        Agent definition dictionary

    Raises:
        FileNotFoundError: If agent definition file doesn't exist
        ValueError: If agent definition contains invalid JSON
    """
    agent_file = AGENTS_DIR / f"{agent_name}.json"
    if not agent_file.exists():
        raise FileNotFoundError(f"Agent definition not found: {agent_file}")
    try:
        with open(agent_file) as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in agent definition {agent_file}: {e}") from e


# ============================================================================
# Entity Classification
# ============================================================================

def classify_entity(entity: dict) -> str:
    """Classify entity into appropriate group_id based on type and name."""
    name = entity.get("name", "")
    entity_type = entity.get("type", "")
    observations = entity.get("observations", [])
    obs_text = " ".join(str(o) for o in observations)

    # Don Branson career data
    if name == "Don Branson":
        return "don_branson_career"
    if entity_type in ["Experience", "Skills", "Credentials"]:
        return "don_branson_career"
    if entity_type == "Project" and any(
        x in name for x in ["kg_rememberall", "nsclc-pathways", "GDELT"]
    ):
        return "don_branson_career"

    # Disney knowledge
    if "Disney" in name or entity_type == "BuyingCenter":
        return "disney_knowledge"
    if entity_type in ["Organization", "Team", "Technology"] and any(
        x in name for x in ["Disney", "OTE", "DEEPT", "Content Genome"]
    ):
        return "disney_knowledge"

    # Career opportunities
    if entity_type == "JobPosting":
        return "career_opportunities"
    if "recruiter" in obs_text.lower() or "Recruiter" in entity_type:
        return "career_opportunities"

    # Technical patterns
    if entity_type in ["Pattern", "Architecture"]:
        return "technical_patterns"

    # Default to research
    return "ai_engineering_research"


def convert_entity_to_episode(entity: dict, group_id: str) -> dict:
    """Convert a Neo4j Memory entity to Graphiti episode format.

    Args:
        entity: Neo4j Memory entity with name, type, and observations
        group_id: Target Graphiti group_id namespace

    Returns:
        Episode dictionary ready for add_memory call
    """
    name = entity.get("name", "Unknown")
    entity_type = entity.get("type", "unknown")
    observations = entity.get("observations", [])

    # Warn about large entities that may cause memory issues
    if len(observations) > LARGE_ENTITY_OBSERVATION_THRESHOLD:
        logging.warning(
            f"Entity '{name}' has {len(observations)} observations "
            f"(threshold: {LARGE_ENTITY_OBSERVATION_THRESHOLD}). Consider chunking."
        )

    # Determine source type based on entity type
    if entity_type in ["Experience", "JobPosting", "Credentials", "Skills"]:
        # JSON format for structured data
        source = "json"
        episode_body = json.dumps({
            "name": name,
            "type": entity_type,
            "details": observations,
            "migrated_from": "neo4j_memory",
            "migration_date": datetime.now(timezone.utc).isoformat(),
        })
    else:
        # Narrative text format
        source = "text"
        obs_text = "\n".join(f"- {obs}" for obs in observations)
        episode_body = f"{name} ({entity_type}):\n\n{obs_text}"

    return {
        "name": f"{name} - {entity_type}",
        "episode_body": episode_body,
        "source": source,
        "source_description": f"Migrated from Neo4j Memory - {entity_type} entity",
        "group_id": group_id,
    }


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """Rate limiter with exponential backoff for API calls."""

    def __init__(self):
        self.last_call_time: dict[str, float] = {}
        self.backoff_multiplier: dict[str, float] = {}

    async def wait_if_needed(self, key: str, base_delay: float) -> None:
        """Wait if needed based on rate limiting.

        Args:
            key: Identifier for the rate-limited resource
            base_delay: Base delay in seconds before backoff multiplier
        """
        import time

        multiplier = self.backoff_multiplier.get(key, 1.0)
        delay = min(base_delay * multiplier, MAX_RATE_LIMIT_DELAY)

        last_time = self.last_call_time.get(key, 0)
        elapsed = time.time() - last_time

        if elapsed < delay:
            wait_time = delay - elapsed
            logging.debug(f"Rate limiting: waiting {wait_time:.1f}s (multiplier: {multiplier}x)")
            await asyncio.sleep(wait_time)

        self.last_call_time[key] = time.time()

    def record_error(self, key: str) -> None:
        """Record error to increase backoff exponentially."""
        current = self.backoff_multiplier.get(key, 1.0)
        new_multiplier = min(current * 2, MAX_BACKOFF_MULTIPLIER)
        self.backoff_multiplier[key] = new_multiplier

        if new_multiplier >= MAX_BACKOFF_MULTIPLIER:
            logging.error(
                f"Rate limiter for {key} at maximum backoff ({MAX_BACKOFF_MULTIPLIER}x). "
                "Consider pausing migration or checking API status."
            )
        else:
            logging.warning(f"Backoff increased for {key}: {new_multiplier}x")

    def record_success(self, key: str) -> None:
        """Record success to decrease backoff gradually."""
        if key in self.backoff_multiplier:
            current = self.backoff_multiplier[key]
            self.backoff_multiplier[key] = max(current / 2, 1.0)
            if current > 1.0:
                logging.debug(f"Backoff decreased for {key}: {self.backoff_multiplier[key]}x")


# ============================================================================
# Migration Functions (SDK Mode)
# ============================================================================

if SDK_AVAILABLE:

    @tool("get_migration_config", "Get migration configuration for a group_id", {"group_id": str})
    async def get_migration_config_tool(args: dict) -> dict:
        """Get configuration for a migration group."""
        group_id = args.get("group_id", "")
        for group in MIGRATION_GROUPS:
            if group.group_id == group_id:
                return {
                    "content": [{
                        "type": "text",
                        "text": json.dumps({
                            "group_id": group.group_id,
                            "priority": group.priority.name,
                            "mode": group.mode.value,
                            "expected_episodes": group.expected_episodes,
                            "key_entities": group.key_entities,
                            "entity_type_filter": group.entity_type_filter,
                        })
                    }]
                }
        return {"content": [{"type": "text", "text": f"Group not found: {group_id}"}]}

    @tool("classify_entity", "Classify entity into group_id", {
        "entity_name": str,
        "entity_type": str,
    })
    async def classify_entity_tool(args: dict) -> dict:
        """Classify entity into appropriate group_id."""
        entity = {"name": args.get("entity_name", ""), "type": args.get("entity_type", "")}
        group_id = classify_entity(entity)
        return {"content": [{"type": "text", "text": json.dumps({"group_id": group_id})}]}

    def create_migration_mcp_server():
        """Create in-process MCP server with migration tools."""
        return create_sdk_mcp_server(
            name="migration-tools",
            version="1.0.0",
            tools=[get_migration_config_tool, classify_entity_tool],
        )


# ============================================================================
# Dry Run Mode
# ============================================================================

async def dry_run_migration() -> None:
    """Show what would be migrated without making changes."""
    print("\n" + "=" * 60)
    print("DRY RUN - No changes will be made")
    print("=" * 60)

    print("\n📋 Migration Groups (in priority order):\n")

    for i, group in enumerate(sorted(MIGRATION_GROUPS, key=lambda g: g.priority.value), 1):
        mode_emoji = "🔄" if group.mode == ProcessingMode.SEQUENTIAL else "📦"
        print(f"  Phase {i}: {group.group_id}")
        print(f"    Priority: {group.priority.name}")
        print(f"    Mode: {mode_emoji} {group.mode.value}")
        print(f"    Expected episodes: ~{group.expected_episodes}")
        print(f"    Entity types: {', '.join(group.entity_type_filter)}")
        if group.key_entities:
            print(f"    Key entities: {', '.join(group.key_entities[:3])}...")
        print()

    total_episodes = sum(g.expected_episodes for g in MIGRATION_GROUPS)
    print(f"📊 Total estimated episodes: {total_episodes}")
    print(f"⏱️  Estimated runtime: 10-16 hours (LLM dependent)")

    print("\n🔧 Agent Configuration:")
    for agent_name in ["orchestrator", "extractor_sequential", "extractor_batch", "validation_agent"]:
        try:
            agent = load_agent_definition(agent_name)
            print(f"  ✅ {agent_name}: {agent.get('model', 'unknown')} model")
        except FileNotFoundError:
            print(f"  ❌ {agent_name}: NOT FOUND")

    print("\n" + "=" * 60)


# ============================================================================
# Simple Mode (No SDK)
# ============================================================================

async def run_simple_migration(
    start_phase: int = 1,
    resume: bool = False,
) -> None:
    """Run migration using direct MCP calls (no SDK required)."""
    logging.info("Running in simple mode (no Claude Agent SDK)")

    state = load_state() if resume else MigrationState()
    if not state.started_at:
        state.started_at = datetime.now(timezone.utc).isoformat()

    sorted_groups = sorted(MIGRATION_GROUPS, key=lambda g: g.priority.value)

    # Filter based on start phase or resume
    if resume and state.in_progress_group:
        idx = next(
            (i for i, g in enumerate(sorted_groups) if g.group_id == state.in_progress_group),
            0
        )
        sorted_groups = sorted_groups[idx:]
    elif not resume:
        sorted_groups = sorted_groups[start_phase - 1:]

    print("\n⚠️  Simple mode requires manual MCP tool calls.")
    print("For full automation, install claude-agent-sdk:")
    print("  pip install claude-agent-sdk\n")

    for group in sorted_groups:
        print(f"\n📦 Ready to migrate: {group.group_id}")
        print(f"   Mode: {group.mode.value}")
        print(f"   Expected: ~{group.expected_episodes} episodes")
        print(f"\n   Manual steps:")
        print(f"   1. Export entities from MCP_DOCKER: mcp__docker__read_graph()")
        print(f"   2. Filter for types: {group.entity_type_filter}")
        print(f"   3. Convert to episodes using templates in agent definitions")
        print(f"   4. Call mcp__graphiti-local__add_memory() for each")
        print(f"   5. Validate with mcp__graphiti-local__search_nodes()")

    save_state(state)


# ============================================================================
# SDK Mode
# ============================================================================

async def run_sdk_migration(
    start_phase: int = 1,
    resume: bool = False,
) -> None:
    """Run migration using Claude Agent SDK."""
    if not SDK_AVAILABLE:
        logging.error("Claude Agent SDK not available. Install with: pip install claude-agent-sdk")
        await run_simple_migration(start_phase, resume)
        return

    logging.info("Running in SDK mode with multi-agent orchestration")

    state = load_state() if resume else MigrationState()
    if not state.started_at:
        state.started_at = datetime.now(timezone.utc).isoformat()

    rate_limiter = RateLimiter()
    sorted_groups = sorted(MIGRATION_GROUPS, key=lambda g: g.priority.value)

    # Filter based on start phase or resume
    if resume and state.in_progress_group:
        idx = next(
            (i for i, g in enumerate(sorted_groups) if g.group_id == state.in_progress_group),
            0
        )
        sorted_groups = sorted_groups[idx:]
    elif not resume:
        sorted_groups = sorted_groups[start_phase - 1:]

    # Load orchestrator definition
    orchestrator_def = load_agent_definition("orchestrator")

    # Create rate limiting hook
    async def rate_limit_hook(input_data: dict, tool_use_id: str, context: dict) -> dict:
        tool_name = input_data.get("tool_name", "")
        if "add_memory" in tool_name:
            mode = ProcessingMode.BATCH  # Default to batch
            if state.in_progress_group == "don_branson_career":
                mode = ProcessingMode.SEQUENTIAL
            base_delay = RATE_LIMITS[mode.value]["delay_seconds"]
            await rate_limiter.wait_if_needed(tool_name, base_delay)
        return {}

    # Configure SDK options
    migration_server = create_migration_mcp_server()

    options = ClaudeAgentOptions(
        system_prompt=orchestrator_def["prompt"],
        allowed_tools=orchestrator_def["tools"],
        model=orchestrator_def.get("model", "opus"),
        mcp_servers={"migration-tools": migration_server},
        hooks={
            "PreToolUse": [
                HookMatcher(
                    matcher="mcp__graphiti-local__add_memory",
                    hooks=[rate_limit_hook],
                ),
            ],
        },
        max_turns=orchestrator_def.get("metadata", {}).get("max_turns", 100),
        cwd=str(PROJECT_ROOT),
        # Define subagents
        agents={
            "extractor_sequential": {
                "description": load_agent_definition("extractor_sequential")["description"],
                "prompt": load_agent_definition("extractor_sequential")["prompt"],
                "tools": load_agent_definition("extractor_sequential")["tools"],
                "model": "sonnet",
            },
            "extractor_batch": {
                "description": load_agent_definition("extractor_batch")["description"],
                "prompt": load_agent_definition("extractor_batch")["prompt"],
                "tools": load_agent_definition("extractor_batch")["tools"],
                "model": "sonnet",
            },
            "validation_agent": {
                "description": load_agent_definition("validation_agent")["description"],
                "prompt": load_agent_definition("validation_agent")["prompt"],
                "tools": load_agent_definition("validation_agent")["tools"],
                "model": "sonnet",
            },
        },
    )

    # Track migration start time for timeout checking
    migration_start = datetime.now(timezone.utc)

    async with ClaudeSDKClient(options=options) as client:
        # Build migration prompt
        groups_info = "\n".join([
            f"- {g.group_id} (Priority: {g.priority.name}, Mode: {g.mode.value}, Expected: {g.expected_episodes})"
            for g in sorted_groups
        ])

        prompt = f"""
Execute the Neo4j Memory to Graphiti migration.

Groups to migrate (in order):
{groups_info}

Current state:
- Completed groups: {state.completed_groups}
- In progress: {state.in_progress_group}

Instructions:
1. For each group, first verify graphiti-local status with get_status()
2. Export source data from MCP_DOCKER using read_graph()
3. For don_branson_career: Use extractor_sequential subagent (one at a time)
4. For other groups: Use extractor_batch subagent (batches of 10)
5. After each group: Run validation_agent subagent
6. After completing a group, report: COMPLETED_GROUP:<group_id>
7. After each entity, report: MIGRATED_ENTITY:<group_id>:<entity_name>
8. On validation pass, report: VALIDATION_PASS:<group_id>

Begin migration.
"""

        await client.query(prompt)

        # Process responses and update state
        async for msg in client.receive_response():
            # Check for timeout (Python 3.10 compatible approach)
            elapsed = (datetime.now(timezone.utc) - migration_start).total_seconds()
            if elapsed > MAX_MIGRATION_TIMEOUT:
                logging.error(
                    f"Migration timed out after {MAX_MIGRATION_TIMEOUT // 3600} hours. "
                    "Use --resume to continue from checkpoint."
                )
                state.errors.append({
                    "type": "timeout",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "message": f"Migration exceeded {MAX_MIGRATION_TIMEOUT // 3600} hour limit",
                })
                break

            msg_str = str(msg)
            logging.info(f"Orchestrator: {msg_str[:200]}...")

            # Parse structured responses for state updates
            if "COMPLETED_GROUP:" in msg_str:
                group_id = msg_str.split("COMPLETED_GROUP:")[1].split()[0].strip()
                if group_id not in state.completed_groups:
                    state.completed_groups.append(group_id)
                    logging.info(f"Group completed: {group_id}")
                state.in_progress_group = None
                save_state(state)

            elif "MIGRATED_ENTITY:" in msg_str:
                parts = msg_str.split("MIGRATED_ENTITY:")[1].split(":")
                if len(parts) >= 2:
                    group_id = parts[0].strip()
                    entity_name = parts[1].split()[0].strip()
                    state.in_progress_group = group_id
                    if group_id not in state.completed_episodes:
                        state.completed_episodes[group_id] = []
                    if entity_name not in state.completed_episodes[group_id]:
                        state.completed_episodes[group_id].append(entity_name)
                    # Save state periodically (every 10 entities)
                    if len(state.completed_episodes[group_id]) % 10 == 0:
                        save_state(state)

            elif "VALIDATION_PASS:" in msg_str:
                group_id = msg_str.split("VALIDATION_PASS:")[1].split()[0].strip()
                state.validation_results[group_id] = {
                    "pass": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                save_state(state)

    save_state(state)
    logging.info("Migration complete!")


# ============================================================================
# Main Entry Point
# ============================================================================

async def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Neo4j Memory to Graphiti Migration Orchestrator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --dry-run          # Show what would be migrated
  %(prog)s --phase 1          # Start from phase 1
  %(prog)s --resume           # Resume from checkpoint
  %(prog)s --simple           # Run without SDK (manual mode)
        """,
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show what would be migrated without making changes",
    )
    parser.add_argument(
        "--phase", "-p",
        type=int,
        default=1,
        choices=[1, 2, 3, 4, 5],
        help="Start from specific phase (1-5)",
    )
    parser.add_argument(
        "--resume", "-r",
        action="store_true",
        help="Resume from last checkpoint",
    )
    parser.add_argument(
        "--simple", "-s",
        action="store_true",
        help="Run in simple mode without Claude Agent SDK",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging",
    )

    args = parser.parse_args()

    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(LOG_DIR / f"migration_{datetime.now():%Y%m%d_%H%M%S}.log"),
        ],
    )

    if args.dry_run:
        await dry_run_migration()
    elif args.simple or not SDK_AVAILABLE:
        await run_simple_migration(args.phase, args.resume)
    else:
        await run_sdk_migration(args.phase, args.resume)


if __name__ == "__main__":
    asyncio.run(main())
