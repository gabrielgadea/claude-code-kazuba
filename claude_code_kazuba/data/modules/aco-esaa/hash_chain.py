"""SHA-256 Merkle hash chain for ESAA event integrity verification.

Implements an append-only hash chain where each event links to the previous
via SHA-256 digest, enabling tamper detection on persisted event logs.

Example:
    >>> from scripts.aco.esaa.hash_chain import GENESIS_HASH, compute_event_hash
    >>> from scripts.aco.esaa.hash_chain import canonical_payload, verify_chain
"""

from __future__ import annotations

import hashlib
import json

GENESIS_HASH: str = "0" * 64


def canonical_payload(payload: dict) -> str:
    """Deterministic JSON representation of payload for hashing.

    Args:
        payload: Event payload dictionary.

    Returns:
        JSON string with sorted keys and compact separators.
    """
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def compute_event_hash(
    prev_hash: str, event_id: str, payload_canonical: str
) -> str:
    """Compute SHA-256 hash linking this event to its predecessor.

    Args:
        prev_hash: Hash of the previous event (GENESIS_HASH for first event).
        event_id: Unique identifier of this event.
        payload_canonical: Canonical JSON representation of payload.

    Returns:
        64-character lowercase hex SHA-256 digest.
    """
    content = f"{prev_hash}:{event_id}:{payload_canonical}"
    return hashlib.sha256(content.encode()).hexdigest()


def verify_chain(events: list) -> bool:
    """Verify SHA-256 hash chain integrity for ordered DomainEvent list.

    Uses duck typing — each event must expose ``event_id``, ``payload``,
    ``prev_hash``, and ``event_hash`` attributes.

    Args:
        events: Ordered list of events (chronological, oldest first).

    Returns:
        True if the entire chain is intact.

    Raises:
        ValueError: If any event has an incorrect hash or broken prev_hash link.
    """
    if not events:
        return True

    prev = GENESIS_HASH
    for i, event in enumerate(events):
        canon = canonical_payload(dict(event.payload))
        expected = compute_event_hash(event.prev_hash, event.event_id, canon)
        if event.event_hash != expected:
            raise ValueError(
                f"Event {i} ({event.event_id[:8]}...) hash mismatch: "
                f"expected={expected[:16]}..., got={event.event_hash[:16]}..."
            )
        if event.prev_hash != prev:
            raise ValueError(
                f"Event {i} ({event.event_id[:8]}...) prev_hash broken: "
                f"expected={prev[:16]}..., got={event.prev_hash[:16]}..."
            )
        prev = event.event_hash
    return True
