"""ESAA CLI Commands - Event Sourcing for Autonomous Agents.

Commands:
    init: Initialize ESAA structure in directory
    submit: Submit an agent result as ESAA event
    verify: Verify integrity of ESAA projection
    replay: Replay events up to specific point
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from claude_code_kazuba.models.esaa_types import (
    CilaLevel,
    CognitiveTrace,
    CommandPayload,
    OperationType,
    ProjectedState,
    RawEventEntry,
    RiskLevel,
)
from claude_code_kazuba.rust_bridge import RustBridge

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SCHEMA_VERSION = "0.4.0"
ESAA_DIR_NAME = ".esaa"
ACTIVITY_FILE = "activity.jsonl"
ROADMAP_FILE = "roadmap.json"


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------
def _get_esaa_dir(root: Path) -> Path:
    """Get ESAA directory for a project root."""
    return root / ESAA_DIR_NAME


def _ensure_esaa_dir(root: Path) -> Path:
    """Ensure ESAA directory exists, create if needed."""
    esaa_dir = _get_esaa_dir(root)
    esaa_dir.mkdir(parents=True, exist_ok=True)
    return esaa_dir


def _load_activity_file(esaa_dir: Path) -> list[RawEventEntry]:
    """Load all events from activity.jsonl."""
    activity_file = esaa_dir / ACTIVITY_FILE
    if not activity_file.exists():
        return []

    events: list[RawEventEntry] = []
    with open(activity_file, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                events.append(RawEventEntry.model_validate(data))
            except (json.JSONDecodeError, ValidationError) as e:
                print(f"Warning: Skipping invalid line {line_num}: {e}", file=sys.stderr)

    return events


def _save_activity_entry(esaa_dir: Path, entry: dict[str, Any]) -> None:
    """Append entry to activity.jsonl."""
    activity_file = esaa_dir / ACTIVITY_FILE
    with open(activity_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, default=str) + "\n")


def _get_next_event_id(esaa_dir: Path) -> str:
    """Generate next event ID based on existing events."""
    events = _load_activity_file(esaa_dir)
    if not events:
        return "EV-00000001"

    # Find max sequence number
    max_seq = 0
    for event in events:
        if event.event_id and event.event_id.startswith("EV-"):
            try:
                seq = int(event.event_id.split("-")[1])
                max_seq = max(max_seq, seq)
            except (IndexError, ValueError):
                pass

    return f"EV-{max_seq + 1:08d}"


def _compute_event_hash(event_data: dict[str, Any]) -> str:
    """Compute SHA-256 hash of event data."""
    canonical = json.dumps(event_data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _project_events_python(events: list[RawEventEntry]) -> ProjectedState:
    """Pure Python event projection (fallback when Rust unavailable)."""
    from claude_code_kazuba.models.esaa_types import (
        Indexes,
        MetaState,
        ProjectInfo,
        RunInfo,
        Task,
        TaskStatus,
    )

    meta = MetaState(
        schema_version=SCHEMA_VERSION,
        esaa_version="0.4.x",
        immutable_done=True,
        master_correlation_id=None,
        run=RunInfo(
            run_id=None,
            status="initialized",
            last_event_seq=0,
            projection_hash_sha256="",
            verify_status="unknown",
        ),
    )

    project = ProjectInfo(name="kazuba-esaa", audit_scope=".esaa/")
    tasks: list[Task] = []

    for entry in events:
        if not entry.activity_event:
            continue

        event = entry.activity_event
        action = event.action
        task_id = event.task_id
        payload = event.payload

        if action == "task.create":
            tasks.append(
                Task(
                    task_id=task_id,
                    task_kind="checkpoint",
                    title=payload.get("name", "Unknown"),
                    status=TaskStatus.TODO,
                    assigned_to="kazuba-orchestrator",
                )
            )
        elif action == "verify.ok":
            for task in tasks:
                if task.task_id == task_id:
                    tasks[tasks.index(task)] = Task(
                        **task.model_dump(exclude={"status", "completed_at"}),
                        status=TaskStatus.DONE,
                        completed_at=datetime.utcnow(),
                    )
                    break
        elif action in ("verify.fail", "output.rejected"):
            for task in tasks:
                if task.task_id == task_id:
                    tasks[tasks.index(task)] = Task(
                        **task.model_dump(exclude={"status", "fail_reason"}),
                        status=TaskStatus.FAILED,
                        fail_reason=payload.get("reason", "Unknown"),
                    )
                    break

    # Build indexes
    by_status: dict[str, int] = {}
    by_kind: dict[str, int] = {}
    for task in tasks:
        by_status[task.status.value] = by_status.get(task.status.value, 0) + 1
        by_kind[task.task_kind] = by_kind.get(task.task_kind, 0) + 1

    return ProjectedState(
        meta=meta,
        project=project,
        tasks=tasks,
        indexes=Indexes(by_status=by_status, by_kind=by_kind),
    )


def _compute_projection_hash(state: ProjectedState) -> str:
    """Compute SHA-256 hash of projected state."""
    payload = {
        "schema_version": state.meta.schema_version,
        "project": state.project.model_dump(),
        "tasks": [t.model_dump() for t in state.tasks],
        "indexes": state.indexes.model_dump(),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Command Implementations
# ---------------------------------------------------------------------------
def cmd_init(args: argparse.Namespace) -> int:
    """Initialize ESAA structure in directory."""
    root = Path(args.root).resolve()
    esaa_dir = _ensure_esaa_dir(root)

    # Create activity.jsonl if not exists
    activity_file = esaa_dir / ACTIVITY_FILE
    if not activity_file.exists():
        activity_file.write_text("", encoding="utf-8")
        print(f"Created: {activity_file}")

    # Create schemas directory
    schemas_dir = esaa_dir / "schemas"
    schemas_dir.mkdir(exist_ok=True)
    print(f"Created: {schemas_dir}")

    # Create initial roadmap.json
    roadmap_file = esaa_dir / ROADMAP_FILE
    if not roadmap_file.exists():
        initial_roadmap = {
            "meta": {
                "schema_version": SCHEMA_VERSION,
                "esaa_version": "0.4.x",
                "immutable_done": True,
                "master_correlation_id": None,
                "run": {
                    "run_id": None,
                    "status": "initialized",
                    "last_event_seq": 0,
                    "projection_hash_sha256": "",
                    "verify_status": "unknown",
                },
            },
            "project": {"name": root.name, "audit_scope": ".esaa/"},
            "tasks": [],
            "indexes": {"by_status": {}, "by_kind": {}},
        }
        roadmap_file.write_text(json.dumps(initial_roadmap, indent=2), encoding="utf-8")
        print(f"Created: {roadmap_file}")

    print(f"\nESAA initialized in: {esaa_dir}")
    return 0


def cmd_submit(args: argparse.Namespace) -> int:
    """Submit an agent result as ESAA event."""
    root = Path(args.root).resolve()
    esaa_dir = _get_esaa_dir(root)

    if not esaa_dir.exists():
        print("Error: ESAA not initialized. Run 'esaa init' first.", file=sys.stderr)
        return 1

    # Load agent result
    result_path = Path(args.result_file)
    if not result_path.exists():
        print(f"Error: Result file not found: {result_path}", file=sys.stderr)
        return 1

    try:
        result_data = json.loads(result_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in result file: {e}", file=sys.stderr)
        return 1

    # Generate event ID
    event_id = _get_next_event_id(esaa_dir)

    # Build ESAA event
    activity_event = result_data.get("activity_event", {})
    file_updates = result_data.get("file_updates", [])

    # Create cognitive trace
    cognitive = CognitiveTrace(
        q_value=0.0,
        intention=f"{activity_event.get('action', 'unknown')}: {activity_event.get('task_id', 'unknown')}",
        risk_assessment=RiskLevel.LOW,
        cila_context=CilaLevel.L3,
        agent_id=args.actor,
        timestamp=datetime.utcnow(),
    )

    # Create command payload
    command = CommandPayload(
        operation_type=OperationType.HOOK_EVENT,
        target_node=None,
        delta_payload=json.dumps(file_updates),
        cognitive_state=cognitive,
        parent_hash=None,
    )

    # Build full event
    event_data = {
        "event_id": event_id,
        "timestamp": datetime.utcnow().isoformat(),
        "activity_event": activity_event,
        "file_updates": file_updates,
        "actor": args.actor,
    }

    # Compute hash
    hash_value = _compute_event_hash(event_data)

    envelope = {
        "event_id": event_id,
        "timestamp": datetime.utcnow().isoformat(),
        "command": command.model_dump(),
        "cryptographic_hash": hash_value,
        "schema_version": SCHEMA_VERSION,
    }

    # Save to activity.jsonl
    _save_activity_entry(esaa_dir, envelope)

    print(f"Submitted: {event_id}")
    print(f"Hash: {hash_value[:32]}...")
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Verify integrity of ESAA projection."""
    root = Path(args.root).resolve()
    esaa_dir = _get_esaa_dir(root)

    if not esaa_dir.exists():
        print("Error: ESAA not initialized.", file=sys.stderr)
        return 1

    # Load events
    events = _load_activity_file(esaa_dir)
    if not events:
        print("No events found.")
        return 0

    # Load roadmap
    roadmap_file = esaa_dir / ROADMAP_FILE
    if not roadmap_file.exists():
        print("Error: roadmap.json not found.", file=sys.stderr)
        return 1

    try:
        roadmap = json.loads(roadmap_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"Error: Invalid roadmap.json: {e}", file=sys.stderr)
        return 1

    # Try Rust first, fallback to Python
    bridge = RustBridge.instance()
    if bridge.available:
        try:
            import esaa_ffi

            result_json = esaa_ffi.esaa_verify(
                json.dumps([e.model_dump() for e in events], default=str),
                json.dumps(roadmap),
            )
            result = json.loads(result_json)
        except ImportError:
            # Fallback to Python
            state = _project_events_python(events)
            computed_hash = _compute_projection_hash(state)
            stored_hash = roadmap.get("meta", {}).get("run", {}).get("projection_hash_sha256", "")

            result = {
                "verify_status": "ok" if computed_hash == stored_hash else "mismatch",
                "hash": computed_hash if computed_hash == stored_hash else None,
                "expected": stored_hash if computed_hash != stored_hash else None,
                "computed": computed_hash if computed_hash != stored_hash else None,
            }
    else:
        # Pure Python projection
        state = _project_events_python(events)
        computed_hash = _compute_projection_hash(state)
        stored_hash = roadmap.get("meta", {}).get("run", {}).get("projection_hash_sha256", "")

        result = {
            "verify_status": "ok" if computed_hash == stored_hash else "mismatch",
            "hash": computed_hash if computed_hash == stored_hash else None,
            "expected": stored_hash if computed_hash != stored_hash else None,
            "computed": computed_hash if computed_hash != stored_hash else None,
        }

    # Output result
    if result["verify_status"] == "ok":
        print("✅ Verification OK")
        print(f"   Hash: {result['hash']}")
        print(f"   Events: {len(events)}")
    else:
        print("❌ Verification FAILED")
        print(f"   Expected: {result.get('expected', 'N/A')}")
        print(f"   Computed: {result.get('computed', 'N/A')}")
        return 1

    return 0


def cmd_replay(args: argparse.Namespace) -> int:
    """Replay events up to specific point."""
    root = Path(args.root).resolve()
    esaa_dir = _get_esaa_dir(root)

    if not esaa_dir.exists():
        print("Error: ESAA not initialized.", file=sys.stderr)
        return 1

    # Load all events
    events = _load_activity_file(esaa_dir)
    if not events:
        print("No events found.")
        return 0

    # Filter events
    until = args.until
    filtered_events = []

    if until.isdigit():
        # Replay up to sequence number
        seq_limit = int(until)
        filtered_events = events[:seq_limit]
    else:
        # Replay up to event_id
        for event in events:
            filtered_events.append(event)
            if event.event_id == until:
                break

    # Project filtered events
    state = _project_events_python(filtered_events)

    # Compute hash
    computed_hash = _compute_projection_hash(state)

    # Output
    print(f"Replayed {len(filtered_events)} events")
    print(f"Tasks: {len(state.tasks)}")
    for task in state.tasks:
        status_icon = "✅" if task.status.value == "done" else "⬜" if task.status.value == "todo" else "❌"
        print(f"   {status_icon} {task.task_id}: {task.title[:40]} ({task.status.value})")

    print(f"\nProjection Hash: {computed_hash[:32]}...")

    # Save if not dry-run
    if not args.dry_run:
        replay_file = esaa_dir / f"replay_{until}.json"
        replay_data = {
            "meta": state.meta.model_dump(),
            "project": state.project.model_dump(),
            "tasks": [t.model_dump() for t in state.tasks],
            "indexes": state.indexes.model_dump(),
            "_replay_info": {
                "events_replayed": len(filtered_events),
                "until": until,
                "projection_hash": computed_hash,
            },
        }
        replay_file.write_text(json.dumps(replay_data, indent=2, default=str), encoding="utf-8")
        print(f"Saved: {replay_file}")

    return 0


# ---------------------------------------------------------------------------
# CLI Entry Point
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    """ESAA CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="esaa",
        description="ESAA - Event Sourcing for Autonomous Agents",
    )
    parser.add_argument("--root", default=".", help="Project root directory")
    parser.add_argument("--version", action="version", version="%(prog)s 0.4.0")

    sub = parser.add_subparsers(dest="command", help="ESAA commands")

    # init
    p_init = sub.add_parser("init", help="Initialize ESAA structure")
    p_init.set_defaults(func=cmd_init)

    # submit
    p_submit = sub.add_parser("submit", help="Submit agent result as ESAA event")
    p_submit.add_argument("result_file", help="Path to agent result JSON")
    p_submit.add_argument("--actor", default="claude-code", help="Actor identifier")
    p_submit.set_defaults(func=cmd_submit)

    # verify
    p_verify = sub.add_parser("verify", help="Verify ESAA projection integrity")
    p_verify.set_defaults(func=cmd_verify)

    # replay
    p_replay = sub.add_parser("replay", help="Replay events up to specific point")
    p_replay.add_argument("--until", required=True, help="Event ID or sequence number")
    p_replay.add_argument("--dry-run", action="store_true", help="Don't save replay file")
    p_replay.set_defaults(func=cmd_replay)

    args = parser.parse_args(argv)
    if not args.command:
        parser.print_help()
        return 0

    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
