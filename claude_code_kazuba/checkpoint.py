"""Checkpoint management in TOON format (msgpack with header)."""

from __future__ import annotations

import struct
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import msgpack  # pyright: ignore[reportMissingTypeStubs]

if TYPE_CHECKING:
    from pathlib import Path

# TOON format constants
TOON_MAGIC: bytes = b"TOON"
TOON_VERSION: int = 1


def _pack(data: dict[str, Any]) -> bytes:
    """Serialize data to bytes using msgpack."""
    result: bytes = cast("bytes", msgpack.packb(data, use_bin_type=True))  # pyright: ignore[reportUnknownMemberType]
    return result


def _unpack(payload: bytes) -> dict[str, Any]:
    """Deserialize bytes using msgpack."""
    result: dict[str, Any] = cast("dict[str, Any]", msgpack.unpackb(payload, raw=False))  # pyright: ignore[reportUnknownMemberType]
    return result


def save_toon(path: Path, data: dict[str, Any]) -> Path:
    """Save a checkpoint in TOON format.

    Format: 4 bytes magic ("TOON") + 1 byte version + msgpack payload.

    Args:
        path: Destination file path.
        data: Dictionary to serialize.

    Returns:
        The path where the checkpoint was written.
    """
    header = TOON_MAGIC + struct.pack("B", TOON_VERSION)
    payload = _pack(data)
    path.write_bytes(header + payload)
    return path


def load_toon(path: Path) -> dict[str, Any]:
    """Load and validate a TOON checkpoint.

    Args:
        path: Path to the checkpoint file.

    Returns:
        The deserialized dictionary.

    Raises:
        ValueError: If the magic header or version is invalid.
    """
    raw = path.read_bytes()

    # Validate magic header
    if raw[:4] != TOON_MAGIC:
        msg = f"Invalid TOON magic header: expected {TOON_MAGIC!r}, got {raw[:4]!r}"
        raise ValueError(msg)

    # Validate version
    version = struct.unpack("B", raw[4:5])[0]
    if version != TOON_VERSION:
        msg = f"Unsupported TOON version: {version} (expected {TOON_VERSION})"
        raise ValueError(msg)

    payload = raw[5:]
    return _unpack(payload)


def create_phase_checkpoint(
    phase_id: int,
    title: str,
    results: dict[str, Any],
    checkpoint_dir: Path,
) -> Path:
    """Create a high-level phase checkpoint with metadata.

    Args:
        phase_id: Phase number (e.g. 1, 2, 3).
        title: Human-readable phase title.
        results: Phase results data.
        checkpoint_dir: Directory to write the checkpoint to.

    Returns:
        Path to the created checkpoint file.
    """
    timestamp = datetime.now(tz=UTC).isoformat()
    data: dict[str, Any] = {
        "phase_id": phase_id,
        "title": title,
        "timestamp": timestamp,
        "results": results,
    }
    filename = f"phase_{phase_id:02d}_{int(time.time())}.toon"
    path = checkpoint_dir / filename
    return save_toon(path, data)
