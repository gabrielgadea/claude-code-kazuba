#!/usr/bin/env python3
"""SessionStart Hook: Learning System Session Startup.

Loads workflow recommendations at session start based on ANTT execution history
from the skill-orchestrator's learning_system.py.

Hook Type: SessionStart
Execution: Once per session (deduplication via marker file)
Timeout: 10000ms

Architecture:
- Session deduplication (marker file pattern)
- Learning system integration (ANTT patterns)
- Graceful degradation (never blocks session)
- Performance: <50ms when already loaded (marker check only)

PERFORMANCE: All heavy imports (rlm_memory_bridge, gpu, scipy, numpy)
are deferred to function scope. Top-level imports are stdlib only.
"""

from __future__ import annotations

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

# Configure logging (stdlib only - fast)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# Common ANTT patterns to precompute (from gpu_config.yaml)
PRECOMPUTE_PATTERNS = [
    "reequilíbrio econômico-financeiro concessão",
    "termo aditivo contrato concessão rodovia",
    "parecer PF-ANTT conformidade legal",
    "análise técnica SUROD infraestrutura",
    "Fator D desconto acréscimo tarifa",
    "VPL valor presente líquido fluxo caixa",
    "cronologia eventos processo administrativo",
    "voto deliberativo diretoria ANTT",
    "TCU Tribunal Contas União acórdão",
    "resolução ANTT normativa regulação",
    "Lei 10.233/2001 transporte terrestre",
    "Lei 8.987/1995 concessão serviço público",
    "AIR análise impacto regulatório",
    "nota técnica parecer fundamentação",
    "processo administrativo 50500 50505",
    "concessionária rodovia federal BR",
    "equilíbrio econômico financeiro contrato",
    "fiscalização obra infraestrutura",
    "metodologia cálculo reajuste tarifa",
    "prazo concessão prorrogação aditivo",
]


# ============================================================================
# Data Models
# ============================================================================


@dataclass
class WorkflowRecommendation:
    """Workflow recommendation based on execution history."""

    task_description: str
    task_type: str
    workflow_name: str
    confidence: float
    past_executions: int
    avg_execution_time: float = 0.0
    success_rate: float = 0.0


@dataclass
class LearningStatistics:
    """Learning system statistics."""

    total_executions: int
    successful_executions: int
    failed_executions: int
    success_rate: float
    avg_execution_time: float
    total_time_saved: float = 0.0


@dataclass
class RLMSyncResult:
    """RLM Memory sync result."""

    available: bool
    cli_available: bool = False
    rust_kernel: bool = False
    entries_synced: int = 0
    total_entries: int = 0


@dataclass
class GPUPreloadResult:
    """GPU preload result."""

    service_available: bool
    device: str = "cpu"
    warmup_done: bool = False
    warmup_latency_ms: float = 0.0
    models_loaded: list[str] = field(default_factory=list)
    cache_loaded: bool = False
    cache_size: int = 0
    patterns_precomputed: int = 0


# ============================================================================
# Session Marker Management
# ============================================================================


class SessionMarker:
    """Manages session deduplication markers."""

    def __init__(self, marker_name: str = "learning_loaded") -> None:
        self.marker_name = marker_name
        self.marker_dir = Path.cwd() / ".cipher" / "session"
        self.marker_dir.mkdir(parents=True, exist_ok=True)

    def is_loaded(self) -> bool:
        """Check if already loaded today."""
        try:
            session_date = datetime.now().strftime("%Y%m%d")
            marker_file = self.marker_dir / f"{self.marker_name}_{session_date}.marker"
            return marker_file.exists()
        except Exception as e:
            logger.warning(f"Error checking session marker: {e}")
            return False

    def mark_loaded(self) -> bool:
        """Mark as loaded."""
        try:
            session_date = datetime.now().strftime("%Y%m%d")
            marker_file = self.marker_dir / f"{self.marker_name}_{session_date}.marker"
            marker_file.write_text(datetime.now().isoformat(), encoding="utf-8")
            self._cleanup_old_markers(days_to_keep=7)
            return True
        except Exception as e:
            logger.warning(f"Error marking session loaded: {e}")
            return False

    def _cleanup_old_markers(self, days_to_keep: int = 7) -> None:
        """Clean up old session markers."""
        try:
            cutoff_str = (datetime.now() - timedelta(days=days_to_keep)).strftime("%Y%m%d")
            for marker_file in self.marker_dir.glob(f"{self.marker_name}_*.marker"):
                try:
                    marker_date_str = marker_file.stem.split("_")[-1]
                    if marker_date_str < cutoff_str:
                        marker_file.unlink()
                except (ValueError, IndexError):
                    continue
        except Exception as e:
            logger.warning(f"Error during marker cleanup: {e}")


# ============================================================================
# Lazy-loaded components (heavy imports deferred)
# ============================================================================

# Pre-computed paths — avoid per-call Path resolution
_HOOKS_UTILS_DIR = str(Path(__file__).parent.parent / "utils")
_HOOKS_DIR = str(Path(__file__).parent.parent)


def _load_rlm_memory() -> tuple[bool, Any]:
    """Load RLM memory bridge on demand."""
    try:
        if _HOOKS_UTILS_DIR not in sys.path:
            sys.path.insert(0, _HOOKS_UTILS_DIR)
        from rlm_memory_bridge import rlm_memory

        return True, rlm_memory
    except ImportError:
        return False, None


def _load_gpu_bridge() -> tuple[bool, Any, Any]:
    """Load GPU bridge on demand."""
    try:
        if _HOOKS_DIR not in sys.path:
            sys.path.insert(0, _HOOKS_DIR)
        from gpu import GPUHookAccelerator, get_gpu_accelerator

        return True, get_gpu_accelerator, GPUHookAccelerator
    except ImportError:
        return False, None, None


def sync_rlm_memory() -> RLMSyncResult:
    """Sync Python learning JSON to RLM Memory on session start."""
    available, rlm_memory = _load_rlm_memory()
    if not available or rlm_memory is None:
        return RLMSyncResult(available=False)

    try:
        entries_synced = rlm_memory.sync_from_learning_json()
        stats_after = rlm_memory.get_stats()
        result = RLMSyncResult(
            available=True,
            cli_available=rlm_memory._cli_available,
            rust_kernel=stats_after.rust_available,
            entries_synced=entries_synced,
            total_entries=stats_after.total_entries,
        )
        if entries_synced > 0:
            logger.info(
                f"[RLM] Synced {entries_synced} entries, "
                f"total={stats_after.total_entries}, "
                f"rust={stats_after.rust_available}"
            )
        return result
    except Exception as e:
        logger.warning(f"[RLM] Sync failed: {e}")
        return RLMSyncResult(available=True, cli_available=False)


def _load_learning_patterns(max_patterns: int = 50) -> list[str]:
    """Load patterns from learning system cache."""
    try:
        learning_cache = Path.cwd() / ".local-cache" / "learning_cache.json"
        if not learning_cache.exists():
            return []
        with open(learning_cache) as f:
            data = json.load(f)
        return [desc for entry in data.get("patterns", [])[:max_patterns] if (desc := entry.get("description"))]
    except Exception as e:
        logger.debug(f"[GPU] Failed to load learning patterns: {e}")
        return []


async def preload_gpu_service() -> GPUPreloadResult:
    """Preload GPU service on session start."""
    gpu_available, get_gpu_accelerator, _ = _load_gpu_bridge()
    if not gpu_available:
        return GPUPreloadResult(service_available=False)

    try:
        import time

        start = time.time()

        cache_loaded = False
        cache_size = 0
        try:
            from gpu.gpu_embedding_cache import get_embedding_cache

            cache = get_embedding_cache()
            cache_size = len(cache)
            cache_loaded = cache_size > 0
            if cache_loaded:
                logger.info(f"[GPU] Disk cache loaded: {cache_size} embeddings")
        except ImportError:
            pass

        accelerator = get_gpu_accelerator()
        status = accelerator.get_status()
        device = status.device if hasattr(status, "device") else "cpu"
        service_healthy = status.mode != "error" if hasattr(status, "mode") else True

        warmup_success = True
        try:
            await accelerator.warmup()
        except Exception as e:
            logger.warning(f"[GPU] Warmup failed: {e}")
            warmup_success = False

        warmup_latency = (time.time() - start) * 1000

        patterns_precomputed = 0
        try:
            all_patterns = list(PRECOMPUTE_PATTERNS)
            all_patterns.extend(_load_learning_patterns(max_patterns=30))
            seen: set[str] = set()
            unique_patterns = []
            for p in all_patterns:
                if p.lower() not in seen:
                    seen.add(p.lower())
                    unique_patterns.append(p)
            if unique_patterns:
                await accelerator.embed(unique_patterns[:50])
                patterns_precomputed = min(len(unique_patterns), 50)
        except Exception as e:
            logger.warning(f"[GPU] Pattern precompute failed: {e}")

        return GPUPreloadResult(
            service_available=service_healthy,
            device=device,
            warmup_done=warmup_success,
            warmup_latency_ms=warmup_latency,
            models_loaded=getattr(status, "models_loaded", []),
            cache_loaded=cache_loaded,
            cache_size=cache_size,
            patterns_precomputed=patterns_precomputed,
        )
    except Exception as e:
        logger.warning(f"[GPU] Preload failed: {e}")
        return GPUPreloadResult(service_available=False)


def preload_gpu_sync() -> GPUPreloadResult:
    """Synchronous wrapper for GPU preload."""
    import asyncio

    try:
        # get_running_loop() raises RuntimeError when no loop is active (Python 3.10+)
        try:
            asyncio.get_running_loop()
            loop_is_running = True
        except RuntimeError:
            loop_is_running = False

        if loop_is_running:
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, preload_gpu_service())
                return future.result(timeout=10.0)
        else:
            return asyncio.run(preload_gpu_service())
    except Exception as e:
        logger.warning(f"[GPU] Sync preload error: {e}")
        return GPUPreloadResult(service_available=False)


# ============================================================================
# Learning System Loader
# ============================================================================


class LearningSystemLoader:
    """Load workflow recommendations from ANTT learning system."""

    def __init__(self) -> None:
        self.logger = logging.getLogger(__name__)
        self._learning_system: Any = None

    def load_recommendations(
        self,
        max_recommendations: int = 5,
    ) -> tuple[list[WorkflowRecommendation], LearningStatistics | None]:
        try:
            learning = self._get_learning_system()
            if not learning:
                return [], None
            stats = self._get_statistics(learning)
            recommendations = self._get_task_recommendations(learning, max_recommendations)
            return recommendations, stats
        except Exception as e:
            self.logger.error(f"Error loading recommendations: {e}", exc_info=True)
            return [], None

    def _get_learning_system(self) -> Any:
        if self._learning_system:
            return self._learning_system
        # LearningSystem module was removed (antt-skill-orchestrator deprecated).
        # Returns None — recommendations and statistics will be empty.
        return None

    def _get_statistics(self, learning: Any) -> LearningStatistics | None:
        try:
            total = len(learning.executions)
            successful = sum(1 for e in learning.executions if e.get("success", False))
            times = [e.get("execution_time_seconds", 0.0) for e in learning.executions]
            return LearningStatistics(
                total_executions=total,
                successful_executions=successful,
                failed_executions=total - successful,
                success_rate=successful / total if total > 0 else 0.0,
                avg_execution_time=sum(times) / len(times) if times else 0.0,
            )
        except Exception as e:
            self.logger.warning(f"Error calculating statistics: {e}")
            return None

    def _get_task_recommendations(
        self,
        _learning: Any,
        _max_recommendations: int,
    ) -> list[WorkflowRecommendation]:
        # ANTTTaskType and LearningSystem were removed (deprecated).
        # Recommendations require a live learning backend to function.
        return []


# ============================================================================
# Anthropic Schema Output
# ============================================================================


def format_session_output(context: str = "", suppress: bool = True) -> str:
    """Format output for SessionStart hooks."""
    return json.dumps(
        {
            "hookSpecificOutput": {
                "hookEventName": "SessionStart",
                "additionalContext": context,
            },
            "suppressOutput": suppress,
        },
        ensure_ascii=False,
    )


# ============================================================================
# Hook Entry Point
# ============================================================================


def main() -> None:
    """SessionStart hook entry point."""
    try:
        # FAST PATH: Check session marker first (< 1ms)
        marker = SessionMarker()
        if marker.is_loaded():
            print(format_session_output("Learning recommendations already loaded today (skipped)"))
            return

        # SLOW PATH: Full initialization (only once per day)
        loader = LearningSystemLoader()
        recommendations, statistics = loader.load_recommendations(max_recommendations=5)

        # RLM Memory Sync
        rlm_result = None
        rlm_available, _ = _load_rlm_memory()
        if rlm_available:
            try:
                rlm_result = sync_rlm_memory()
            except Exception as e:
                logger.warning(f"[RLM] Auto-sync error: {e}")

        # GPU Preload
        gpu_result = None
        gpu_available, _, _ = _load_gpu_bridge()
        if gpu_available:
            try:
                gpu_result = preload_gpu_sync()
            except Exception as e:
                logger.warning(f"[GPU] Preload error: {e}")

        marker.mark_loaded()

        # Build output
        message_parts = ["Learning recommendations loaded"]
        if recommendations:
            message_parts.append(f"({len(recommendations)} patterns)")
        if statistics:
            message_parts.append(f"Success rate: {statistics.success_rate:.1%}")
        if gpu_result and gpu_result.warmup_done:
            gpu_info = f"GPU: {gpu_result.device}"
            if gpu_result.cache_size > 0:
                gpu_info += f", cache: {gpu_result.cache_size}"
            if gpu_result.patterns_precomputed > 0:
                gpu_info += f", precomputed: {gpu_result.patterns_precomputed}"
            message_parts.append(gpu_info)
        if rlm_result and rlm_result.available:
            rlm_info = f"RLM: {rlm_result.total_entries} entries"
            if rlm_result.rust_kernel:
                rlm_info += " (Rust accelerated)"
            message_parts.append(rlm_info)

        print(format_session_output(" - ".join(message_parts)))

    except Exception as e:
        logger.error(f"Learning startup hook failed: {e}", exc_info=True)
        print(format_session_output(f"Learning startup hook failed (continuing): {e}"))


if __name__ == "__main__":
    main()
