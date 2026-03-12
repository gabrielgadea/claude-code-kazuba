"""Rust acceleration bridge for ACO -- try Rust, fallback to Python.

Provides dual-mode access to ACO components (graph, tracker, models).
When the ``claude_learning_kernel`` Rust extension is installed the faster
native implementation is used; otherwise the pure-Python equivalents from
``scripts.aco`` are returned transparently.

Usage::

    from scripts.aco.rust_bridge import (
        is_rust_available,
        get_graph_class,
        get_compute_composite,
        get_determine_status,
        get_build_report,
        get_dim_result_class,
        get_tracker_constants,
    )

    GraphClass = get_graph_class()
    compute = get_compute_composite()
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Probe Rust availability at import time
# ---------------------------------------------------------------------------

# Sentinel values — overwritten inside the try block when Rust is available.
# Initialized here so pyright does not report "possibly unbound" on usages
# that are always guarded by ``if RUST_AVAILABLE:``.
_RUST_CRITICAL_WEIGHT: Any = None
_RUST_HALT_ITERATIONS: Any = None
_RUST_HALT_THRESHOLD: Any = None
_RUST_NORMAL_WEIGHT: Any = None
_RUST_VETO_THRESHOLD: Any = None
_RustAcoGraph: Any = None
_RustDimResult: Any = None
_RustTrackerReport: Any = None
_rust_build_report: Any = None
_rust_compute_composite: Any = None
_rust_determine_status: Any = None
# D3/D4 ESAA sentinels
_RustEventProjector: Any = None
_rust_verify_chain_parallel: Any = None

try:
    from claude_learning_kernel.claude_learning_kernel import (  # type: ignore[import-untyped]
        CRITICAL_WEIGHT as _RUST_CRITICAL_WEIGHT,
    )
    from claude_learning_kernel.claude_learning_kernel import (
        HALT_ITERATIONS as _RUST_HALT_ITERATIONS,
    )
    from claude_learning_kernel.claude_learning_kernel import (
        HALT_THRESHOLD as _RUST_HALT_THRESHOLD,
    )
    from claude_learning_kernel.claude_learning_kernel import (
        NORMAL_WEIGHT as _RUST_NORMAL_WEIGHT,
    )
    from claude_learning_kernel.claude_learning_kernel import (
        VETO_THRESHOLD as _RUST_VETO_THRESHOLD,
    )
    from claude_learning_kernel.claude_learning_kernel import (
        AcoGraph as _RustAcoGraph,
    )
    from claude_learning_kernel.claude_learning_kernel import (
        DimResult as _RustDimResult,
    )
    from claude_learning_kernel.claude_learning_kernel import (
        TrackerReport as _RustTrackerReport,
    )
    from claude_learning_kernel.claude_learning_kernel import (
        py_build_report as _rust_build_report,
    )
    from claude_learning_kernel.claude_learning_kernel import (
        py_compute_composite as _rust_compute_composite,
    )
    from claude_learning_kernel.claude_learning_kernel import (
        py_determine_status as _rust_determine_status,
    )

    RUST_AVAILABLE = True
    logger.debug("ACO Rust acceleration available")
except ImportError:
    RUST_AVAILABLE = False
    logger.debug("ACO Rust acceleration not available, using Python fallback")

# D3/D4 ESAA: probe independently so main RUST_AVAILABLE is not affected
_ESAA_RUST_AVAILABLE: bool = False
try:
    from claude_learning_kernel.claude_learning_kernel import (  # type: ignore[import-untyped]
        EventProjector as _RustEventProjector,
    )
    from claude_learning_kernel.claude_learning_kernel import (
        verify_chain_parallel as _rust_verify_chain_parallel,
    )

    _ESAA_RUST_AVAILABLE = True
    logger.debug("ESAA Rust acceleration (D3/D4) available")
except ImportError:
    logger.debug("ESAA Rust acceleration not available, using Python fallback")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def is_rust_available() -> bool:
    """Check if the Rust ACO acceleration module is installed and importable."""
    return RUST_AVAILABLE


def get_graph_class() -> type:
    """Return the graph implementation class.

    Returns:
        ``AcoGraph`` (Rust) when available, otherwise
        ``MutableGeneratorGraph`` (Python).
    """
    if RUST_AVAILABLE:
        return _RustAcoGraph  # type: ignore[return-value]
    from scripts.aco.generator_graph import MutableGeneratorGraph

    return MutableGeneratorGraph


def get_compute_composite() -> Any:
    """Return the ``compute_composite`` callable.

    Returns:
        Rust ``py_compute_composite`` when available, otherwise the Python
        ``_compute_composite`` from ``goal_tracker_v2``.
    """
    if RUST_AVAILABLE:
        return _rust_compute_composite
    from scripts.aco.goal_tracker_v2 import _compute_composite

    return _compute_composite


def get_determine_status() -> Any:
    """Return the ``determine_status`` callable.

    The Rust version is ``py_determine_status(dims, composite) -> TrackerStatus``
    while the Python equivalent is inlined in ``run_all``. This function
    returns a unified callable with the same ``(dims, composite) -> str``
    signature (Rust returns a ``TrackerStatus`` whose ``__str__`` matches).

    Returns:
        Rust ``py_determine_status`` when available, otherwise a Python
        function implementing the same logic.
    """
    if RUST_AVAILABLE:
        return _rust_determine_status
    from scripts.aco.goal_tracker_v2 import (
        HALT_THRESHOLD,
        VETO_THRESHOLD,
    )

    def _py_determine_status(
        dims: list[Any],
        composite: float,
    ) -> str:
        all_pass = all(d.score >= VETO_THRESHOLD for d in dims)
        if all_pass:
            return "PASS"
        if composite < HALT_THRESHOLD:
            return "HALT"
        return "VETO"

    return _py_determine_status


def get_build_report() -> Any:
    """Return the ``build_report`` callable.

    Returns:
        Rust ``py_build_report`` when available, otherwise a Python
        function that builds a ``TrackerReport`` dataclass.
    """
    if RUST_AVAILABLE:
        return _rust_build_report
    from scripts.aco.goal_tracker_v2 import TrackerReport, _compute_composite

    def _py_build_report(
        dims: list[Any],
        iteration: int,
    ) -> TrackerReport:
        from scripts.aco.goal_tracker_v2 import (
            HALT_THRESHOLD,
            VETO_THRESHOLD,
        )

        composite = _compute_composite(dims)
        all_pass = all(d.score >= VETO_THRESHOLD for d in dims)
        if all_pass:
            status = "PASS"
        elif composite < HALT_THRESHOLD:
            status = "HALT"
        else:
            status = "VETO"
        return TrackerReport(
            dims=list(dims),
            composite=composite,
            status=status,
            iteration=iteration,
        )

    return _py_build_report


def get_dim_result_class() -> type:
    """Return the DimResult class.

    Returns:
        Rust ``DimResult`` when available, otherwise the Python
        ``DimResult`` dataclass from ``goal_tracker_v2``.
    """
    if RUST_AVAILABLE:
        return _RustDimResult  # type: ignore[return-value]
    from scripts.aco.goal_tracker_v2 import DimResult

    return DimResult


def get_tracker_report_class() -> type:
    """Return the TrackerReport class.

    Returns:
        Rust ``TrackerReport`` when available, otherwise the Python
        ``TrackerReport`` dataclass from ``goal_tracker_v2``.
    """
    if RUST_AVAILABLE:
        return _RustTrackerReport  # type: ignore[return-value]
    from scripts.aco.goal_tracker_v2 import TrackerReport

    return TrackerReport


def get_tracker_constants() -> dict[str, float | int]:
    """Return the canonical ACO tracker constants.

    Returns a dict with keys ``VETO_THRESHOLD``, ``HALT_THRESHOLD``,
    ``HALT_ITERATIONS``, ``CRITICAL_WEIGHT``, ``NORMAL_WEIGHT``.

    The Rust and Python constants are identical by design (verified in
    parity tests), but this accessor ensures a single source of truth
    at runtime.

    Returns:
        Dict mapping constant names to their values.
    """
    if RUST_AVAILABLE:
        return {
            "VETO_THRESHOLD": float(_RUST_VETO_THRESHOLD),
            "HALT_THRESHOLD": float(_RUST_HALT_THRESHOLD),
            "HALT_ITERATIONS": int(_RUST_HALT_ITERATIONS),
            "CRITICAL_WEIGHT": float(_RUST_CRITICAL_WEIGHT),
            "NORMAL_WEIGHT": float(_RUST_NORMAL_WEIGHT),
        }
    from scripts.aco.goal_tracker_v2 import (
        CRITICAL_WEIGHT,
        HALT_ITERATIONS,
        HALT_THRESHOLD,
        NORMAL_WEIGHT,
        VETO_THRESHOLD,
    )

    return {
        "VETO_THRESHOLD": float(VETO_THRESHOLD),
        "HALT_THRESHOLD": float(HALT_THRESHOLD),
        "HALT_ITERATIONS": int(HALT_ITERATIONS),
        "CRITICAL_WEIGHT": float(CRITICAL_WEIGHT),
        "NORMAL_WEIGHT": float(NORMAL_WEIGHT),
    }


# ---------------------------------------------------------------------------
# D3/D4 — ESAA Event Projector & Parallel Hash Chain Verifier
# ---------------------------------------------------------------------------


def is_esaa_rust_available() -> bool:
    """Return True if D3/D4 Rust ESAA acceleration is available."""
    return _ESAA_RUST_AVAILABLE


def get_event_projector_class() -> type | None:
    """Return the Rust ``EventProjector`` class (D3) or ``None``.

    When available, callers can use it as::

        proj = get_event_projector_class()()
        proj.load_events(events_as_json_strings)
        state_json = proj.project_agent_state("agent-1")
        valid     = proj.verify_hash_chain("agent-1")

    Returns:
        Rust ``EventProjector`` class or ``None`` when Rust is unavailable.
    """
    return _RustEventProjector if _ESAA_RUST_AVAILABLE else None


def rust_verify_chain_parallel(events_json: list[str]) -> bool:
    """Verify a SHA-256 hash chain via Rust/Rayon (D4) or Python fallback.

    Accepts JSON-serialised events (fields: ``event_id``, ``prev_hash``,
    ``event_hash``, ``payload``). Verifies linkage and per-event SHA-256 in
    parallel (Rust) or sequentially (Python).

    Args:
        events_json: List of JSON strings, one per event.

    Returns:
        ``True`` if the chain is intact, ``False`` on any hash mismatch.
    """
    if _ESAA_RUST_AVAILABLE and _rust_verify_chain_parallel is not None:
        return bool(_rust_verify_chain_parallel(events_json))
    return _python_verify_chain_parallel(events_json)


def _python_verify_chain_parallel(events_json: list[str]) -> bool:
    """Pure-Python fallback for SHA-256 chain verification.

    Mirrors ``scripts.aco.esaa.hash_chain.verify_chain`` but accepts
    JSON strings — same interface as the Rust D4 function.
    """
    import json

    from scripts.aco.esaa.hash_chain import (
        GENESIS_HASH,
        canonical_payload,
        compute_event_hash,
    )

    if not events_json:
        return True
    prev_hash = GENESIS_HASH
    for ev_json in events_json:
        ev = json.loads(ev_json)
        raw_payload = ev.get("payload", {})
        if isinstance(raw_payload, str):
            raw_payload = json.loads(raw_payload)
        canon = canonical_payload(raw_payload)
        expected = compute_event_hash(ev["prev_hash"], ev["event_id"], canon)
        if ev["event_hash"] != expected or ev["prev_hash"] != prev_hash:
            return False
        prev_hash = ev["event_hash"]
    return True
