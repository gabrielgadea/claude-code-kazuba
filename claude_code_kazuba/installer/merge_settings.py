"""Deep merge algorithm for settings.json files.

Merge rules:
- permissions.allow / permissions.deny: extend arrays (no duplicates)
- hooks: merge hook arrays per event (append, don't overwrite)
- env: merge dicts (new keys added, existing preserved)
- Never overwrite user's existing values
"""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


def _extend_unique(base: list[Any], overlay: list[Any]) -> list[Any]:
    """Extend a list with items from overlay, avoiding duplicates.

    Preserves order: base items first, then new overlay items.
    """
    result = list(base)
    seen = set()
    for item in base:
        if isinstance(item, (str, int, float, bool)):
            seen.add(item)
        else:
            seen.add(json.dumps(item, sort_keys=True))

    for item in overlay:
        key = (
            item if isinstance(item, (str, int, float, bool)) else json.dumps(item, sort_keys=True)
        )
        if key not in seen:
            seen.add(key)
            result.append(item)

    return result


def _merge_hooks(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Merge hook configurations per event.

    For each event (PreToolUse, PostToolUse, etc.), append new hooks
    from overlay without removing existing ones from base.
    """
    result = deepcopy(base)

    for event, hooks in overlay.items():
        if event not in result:
            result[event] = deepcopy(hooks)
        elif isinstance(result[event], list) and isinstance(hooks, list):
            result[event] = _extend_unique(result[event], hooks)
        else:
            # Non-list hook config: overlay wins for new keys
            if isinstance(result[event], dict) and isinstance(hooks, dict):
                result[event] = {**result[event], **deepcopy(hooks)}
            else:
                result[event] = deepcopy(hooks)

    return result


def _merge_permissions(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Merge permissions: extend allow and deny arrays."""
    result = deepcopy(base)

    for key in ("allow", "deny"):
        if key in overlay:
            base_list = result.get(key, [])
            if isinstance(base_list, list) and isinstance(overlay[key], list):
                result[key] = _extend_unique(base_list, overlay[key])
            else:
                result[key] = deepcopy(overlay[key])

    return result


def _merge_env(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Merge env vars: add new keys, preserve existing values."""
    result = deepcopy(base)
    for key, value in overlay.items():
        if key not in result:
            result[key] = value
    return result


def merge_settings(base: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two settings.json structures.

    Merge strategy:
    - $schema: preserve base, use overlay if base is missing
    - permissions.allow/deny: extend arrays (no duplicates)
    - hooks: merge hook arrays per event (append)
    - env: merge dicts (new keys only, existing preserved)
    - Other keys: overlay wins if base doesn't have it

    Args:
        base: The existing settings dict (user's config).
        overlay: The new settings to merge in (from module).

    Returns:
        Merged settings dict. Original dicts are not modified.
    """
    result = deepcopy(base)

    # $schema
    if "$schema" not in result and "$schema" in overlay:
        result["$schema"] = overlay["$schema"]

    # permissions
    if "permissions" in overlay:
        result["permissions"] = _merge_permissions(
            result.get("permissions", {}),
            overlay["permissions"],
        )

    # hooks
    if "hooks" in overlay:
        result["hooks"] = _merge_hooks(
            result.get("hooks", {}),
            overlay["hooks"],
        )

    # env
    if "env" in overlay:
        result["env"] = _merge_env(
            result.get("env", {}),
            overlay["env"],
        )

    # Any other top-level keys from overlay not already in result
    for key in overlay:
        if key not in result:
            result[key] = deepcopy(overlay[key])

    return result


def merge_settings_file(base_path: Path, overlay_path: Path) -> dict[str, Any]:
    """Merge two settings JSON files.

    Args:
        base_path: Path to base settings.json.
        overlay_path: Path to overlay settings fragment.

    Returns:
        Merged settings dict.

    Raises:
        FileNotFoundError: If overlay_path doesn't exist.
        json.JSONDecodeError: If either file is not valid JSON.
    """
    base = json.loads(base_path.read_text(encoding="utf-8")) if base_path.exists() else {}

    overlay = json.loads(overlay_path.read_text(encoding="utf-8"))
    return merge_settings(base, overlay)


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 3:
        print("Usage: merge_settings.py BASE_FILE OVERLAY_FILE", file=sys.stderr)
        sys.exit(1)

    merged = merge_settings_file(Path(sys.argv[1]), Path(sys.argv[2]))
    print(json.dumps(merged, indent=2))
