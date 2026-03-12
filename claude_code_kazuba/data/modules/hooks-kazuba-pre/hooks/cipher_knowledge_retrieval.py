#!/usr/bin/env python3
"""
Cipher Knowledge Retrieval Hook (PreToolUse) - HYBRID ARCHITECTURE

Arquitetura de 3 Camadas (ADR-001):
- TIER 1: Local Cache (95% dos casos) - Jaccard similarity, 0 tokens, <0.5s
- TIER 2: MCP Enhancement (5% dos casos) - Vector embeddings, ~800 tokens, ~2s
- TIER 3: Graceful Degradation - Fallback local, never block

Execucao: ANTES de Write/Edit/MultiEdit
Integracao: PreToolUse hook

Triggers para MCP (TIER 2):
- Local confidence < 50%
- Local confidence < 30% (weak match)
- Zero local results
- User explicit: "cross-project", "all projects"

Never MCP:
- Local confidence >= 50% (strong match)
- Offline mode
- MCP timeout/error

Referencia: .claude/ADR_001_HYBRID_PERMANENT_ARCHITECTURE.md
"""

from __future__ import annotations

import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

# PERFORMANCE: Heavy imports (torch, transformers, sentence_transformers)
# are deferred to function scope. These add ~2.5s if loaded at module level.
VECTOR_SEARCH_AVAILABLE: bool | None = None  # Lazy-checked
GPU_BRIDGE_AVAILABLE: bool | None = None  # Lazy-checked

# GPU Singleton for reuse across calls (avoids re-loading model)
_vector_search_instance: Any = None

# TTL thresholds for pattern file staleness (seconds)
# Aligned with scripts/cache/cache_manager.py categories
_PATTERN_TTL_WARN = 90 * 24 * 3600  # 90 days — warn but still use
_PATTERN_TTL_EXPIRE = 180 * 24 * 3600  # 180 days — skip entirely

# Skip binary and temporary files from cipher checks
_SKIP_SUFFIXES = frozenset(
    [
        ".pyc",
        ".pyo",
        ".so",
        ".o",
        ".a",
        ".exe",
        ".dll",
        ".dylib",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".svg",
        ".ico",
        ".webp",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
        ".wav",
        ".zip",
        ".tar",
        ".gz",
        ".bz2",
        ".rar",
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".tmp",
        ".swp",
        ".bak",
        ".cache",
        ".log",
    ]
)

# Default hybrid config (H0 improvements: lower thresholds, multi-signal)
_DEFAULT_CONFIG: dict[str, Any] = {
    "tier_1_local": {
        "confidence_threshold": 0.05,
        "enabled": True,
        "hybrid_scoring": True,
        "signal_weights": {
            "error_code": 0.40,
            "tags": 0.20,
            "file_path": 0.30,
            "jaccard": 0.10,
        },
    },
    "tier_2_mcp": {
        "enabled": True,
        "confidence_threshold_trigger": 0.05,
        "min_confidence_to_skip": 0.03,
        "timeout_ms": 3000,
        "triggers": ["cross-project", "all projects", "similar patterns in"],
    },
    "tier_3_fallback": {"enabled": True, "always_allow": True},
    "metrics": {
        "logging_enabled": True,
        "log_path": ".claude/logs/hybrid_metrics.log",
    },
}

# Extension to language tag mapping
_EXT_TAG_MAP: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript-react",
    ".js": "javascript",
    ".jsx": "javascript-react",
    ".go": "golang",
    ".rs": "rust",
    ".java": "java",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
}

# Stopwords for keyword extraction
_STOPWORDS = frozenset(
    {
        "the",
        "a",
        "an",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "and",
        "or",
        "is",
        "are",
    }
)

# Common keywords for tag extraction from content
_COMMON_KEYWORDS = frozenset(
    {
        "async",
        "await",
        "promise",
        "callback",
        "type",
        "interface",
        "class",
        "function",
        "import",
        "export",
        "const",
        "let",
        "react",
        "vue",
        "angular",
        "next",
    }
)

# Regex patterns for error code extraction (compiled once)
_TS_ERROR_RE = re.compile(r"\bTS\d{4}\b")
_PY_ERROR_RE = re.compile(r"\b[EFWCNBIA]\d{3,4}\b")
_COMMON_ERROR_RE = re.compile(
    r"\b(exactOptionalPropertyTypes|strictNullChecks|noImplicitAny)\b",
    re.IGNORECASE,
)


def _check_vector_search() -> bool:
    """Lazy check for vector search availability."""
    global VECTOR_SEARCH_AVAILABLE
    if VECTOR_SEARCH_AVAILABLE is None:
        try:
            from cipher_vector_search import CipherVectorSearch  # noqa: F401

            VECTOR_SEARCH_AVAILABLE = True
        except ImportError:
            VECTOR_SEARCH_AVAILABLE = False
    return VECTOR_SEARCH_AVAILABLE


def _check_gpu_bridge() -> bool:
    """Lazy check for GPU bridge availability."""
    global GPU_BRIDGE_AVAILABLE
    if GPU_BRIDGE_AVAILABLE is None:
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent))
            from gpu import get_gpu_accelerator  # noqa: F401

            GPU_BRIDGE_AVAILABLE = True
        except ImportError:
            GPU_BRIDGE_AVAILABLE = False
    return GPU_BRIDGE_AVAILABLE


def get_vector_search() -> Any:
    """Get or create GPU-optimized CipherVectorSearch singleton.

    Uses singleton pattern to avoid reloading model on each hook call.
    Applies GPU optimizations from FASE H0:
    - FP16 mixed precision (2x speedup)
    - Dynamic batch sizing (GPU: 128, CPU: 32)
    - GPU warmup on first call
    """
    global _vector_search_instance

    if not _check_vector_search():
        return None

    if _vector_search_instance is None:
        try:
            from cipher_vector_search import CipherVectorSearch

            _vector_search_instance = CipherVectorSearch(
                model_name="all-MiniLM-L6-v2",
                cache_embeddings=True,
                use_fp16=True,
                warmup_on_init=True,
            )
            inst = _vector_search_instance
            print(
                f"[GPU] CipherVectorSearch initialized: device={inst.device}, "
                f"fp16={inst.use_fp16}, batch_size={inst.batch_size}",
                file=sys.stderr,
            )
        except Exception as e:
            print(f"[GPU] Warning: Could not initialize CipherVectorSearch: {e}", file=sys.stderr)
            return None

    return _vector_search_instance


def format_pretool_output(
    decision: str = "allow",
    reason: str = "",
    metadata: dict[str, Any] | None = None,
    suppress: bool = True,
) -> str:
    """Format output for PreToolUse hooks according to Anthropic schema."""
    output: dict[str, Any] = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        },
        "suppressOutput": suppress,
    }

    if metadata:
        output["systemMessage"] = json.dumps(metadata)

    return json.dumps(output)


def parse_tool_params(tool_name: str, params: dict[str, Any]) -> dict[str, Any]:
    """Extrai informacoes relevantes dos parametros da ferramenta."""
    info: dict[str, Any] = {
        "tool": tool_name,
        "file_path": None,
        "content_preview": None,
        "operation_type": None,
    }

    if tool_name == "Write":
        info["file_path"] = params.get("file_path")
        info["operation_type"] = "create"
        content = params.get("content", "")
        info["content_preview"] = content[:200] if content else None
    elif tool_name in ("Edit", "MultiEdit"):
        info["file_path"] = params.get("file_path")
        info["operation_type"] = "modify"
        info["content_preview"] = params.get("new_string", "")[:200]
    elif tool_name == "Read":
        # hook matcher is "Read|Grep|Glob" — retrieve knowledge before reads too
        info["file_path"] = params.get("file_path")
        info["operation_type"] = "read"
        info["content_preview"] = ""  # no content preview for reads
    elif tool_name == "Grep":
        # Use path as context anchor; pattern as content preview
        info["file_path"] = params.get("path") or params.get("include")
        info["operation_type"] = "search"
        info["content_preview"] = params.get("pattern", "")[:200]
    elif tool_name == "Glob":
        info["file_path"] = params.get("path")
        info["operation_type"] = "glob"
        info["content_preview"] = params.get("pattern", "")[:200]

    return info


def should_check_cipher(info: dict[str, Any]) -> bool:
    """Determina se deve consultar o Cipher para esta operacao."""
    if not info.get("file_path"):
        return False

    return Path(info["file_path"]).suffix not in _SKIP_SUFFIXES


def calculate_similarity(query_tokens: set[str], memory_tokens: set[str]) -> float:
    """Calcula similaridade Jaccard entre dois conjuntos de tokens."""
    if not query_tokens or not memory_tokens:
        return 0.0

    intersection = len(query_tokens & memory_tokens)
    union = len(query_tokens | memory_tokens)

    return intersection / union if union > 0 else 0.0


def extract_keywords(text: str) -> set[str]:
    """Extrai keywords relevantes do texto."""
    if not text:
        return set()

    words = text.lower().split()
    keywords = {w.strip(".,;:(){}[]\"'") for w in words if len(w) > 2}

    return keywords - _STOPWORDS


_HYBRID_CONFIG_CACHE: dict[str, Any] | None = None


def load_hybrid_config() -> dict[str, Any]:
    """Load hybrid configuration from hybrid_config.json (cached after first read)."""
    global _HYBRID_CONFIG_CACHE
    if _HYBRID_CONFIG_CACHE is not None:
        return _HYBRID_CONFIG_CACHE

    try:
        config_path = Path(__file__).parent / "hybrid_config.json"
        if config_path.exists():
            with open(config_path, encoding="utf-8") as f:
                raw = json.load(f).get("hybrid_knowledge_system", {})
                _HYBRID_CONFIG_CACHE = dict(raw) if isinstance(raw, dict) else {}
                return _HYBRID_CONFIG_CACHE
    except Exception as e:
        print(f"[Hybrid] Warning: Could not load config: {e}", file=sys.stderr)

    _HYBRID_CONFIG_CACHE = _DEFAULT_CONFIG.copy()
    return _HYBRID_CONFIG_CACHE


def should_use_mcp(info: dict[str, Any], local_confidence: float, config: dict[str, Any]) -> bool:
    """Decide if MCP enhancement is worth the cost.

    Returns True only in ~5% of cases:
    - User explicit request (cross-project, all projects)
    - Local confidence < min_confidence_to_skip threshold
    """
    tier_2_config = config.get("tier_2_mcp", {})

    if not tier_2_config.get("enabled", True):
        return False

    # Check for explicit user triggers in context/query
    triggers = tier_2_config.get("triggers", [])
    user_context = info.get("context", "").lower()
    content_preview = info.get("content_preview", "").lower()

    for trigger in triggers:
        trigger_lower = trigger.lower()
        if trigger_lower in user_context or trigger_lower in content_preview:
            return True

    # Low local confidence triggers MCP (covers zero results case too)
    min_confidence = tier_2_config.get("min_confidence_to_skip", 0.30)
    return local_confidence < min_confidence


def is_mcp_available() -> bool:
    """Check if vector search with sentence-transformers is available."""
    return _check_vector_search()


def log_metrics(
    tier: str,
    tokens: int,
    latency_ms: int,
    confidence: float,
    info: dict[str, Any],
) -> None:
    """Log metrics for hybrid architecture monitoring."""
    try:
        config = load_hybrid_config()
        metrics_config = config.get("metrics", {})

        if not metrics_config.get("logging_enabled", True):
            return

        log_path = Path.cwd() / metrics_config.get("log_path", ".claude/logs/hybrid_metrics.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "timestamp": datetime.now().isoformat(),
            "tier": tier,
            "tokens_used": tokens,
            "latency_ms": latency_ms,
            "confidence": round(confidence, 3),
            "file": str(info.get("file_path", "unknown")),
            "operation": info.get("operation_type", "unknown"),
        }

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")

    except Exception as e:
        print(f"[Hybrid] Warning: Could not log metrics: {e}", file=sys.stderr)


def search_local_cipher(info: dict[str, Any]) -> tuple[dict[str, Any] | None, float]:
    """TIER 1: Local cache search with Jaccard similarity."""
    memory = search_cipher_memory(info)
    confidence = memory.get("confidence", 0.0) if memory else 0.0
    return memory, confidence


def search_mcp_cipher(
    info: dict[str, Any],
    config: dict[str, Any],
) -> tuple[dict[str, Any] | None, float]:
    """TIER 2: MCP enhancement with GPU-accelerated vector embeddings.

    Uses GPU-optimized local vector search with sentence-transformers for semantic matching.
    GPU Optimizations (FASE H0/2.1):
    - FP16 mixed precision (2x speedup)
    - Dynamic batch sizing (GPU: 128, CPU: 32)
    - Singleton pattern (avoids reloading model)
    - GPU warmup (eliminates cold start)
    """
    if not _check_vector_search():
        return None, 0.0

    try:
        cipher_dir = Path.cwd() / ".cipher" / "patterns"
        if not cipher_dir.exists():
            return None, 0.0

        all_patterns: list[Any] = []
        for pattern_file in cipher_dir.glob("*.json"):
            try:
                with open(pattern_file, encoding="utf-8") as f:
                    data = json.load(f)
                all_patterns.extend(data.get("patterns", []))
            except Exception as e:
                print(f"[VectorSearch] Skipping pattern file: {e}", file=sys.stderr)
                continue

        if not all_patterns:
            return None, 0.0

        query_parts = [
            Path(info.get("file_path", "")).stem,
            info.get("content_preview", "")[:200],
        ]
        query = " ".join(filter(None, query_parts))

        searcher = get_vector_search()
        if searcher is None:
            return None, 0.0

        results = searcher.search_patterns(query, all_patterns, top_k=5, min_similarity=0.3)

        if not results:
            return None, 0.0

        gpu_metrics = searcher.get_metrics()

        suggestions: list[str] = []
        warnings: list[str] = []
        top_confidence = 0.0

        for result in results[:5]:
            top_confidence = max(top_confidence, result.similarity)

            if result.tags:
                tags_str = ", ".join(result.tags[:3])
                suggestions.append(f"Similar pattern ({result.similarity:.0%}): {tags_str}")

            if result.confidence < 0.7:
                warnings.append("Previous implementation had quality issues")

        device = gpu_metrics.get("device", "unknown")
        memory: dict[str, Any] = {
            "decision": "allow",
            "found_memories": len(results),
            "suggestions": suggestions[:3],
            "warnings": warnings[:2],
            "confidence": top_confidence,
            "storage": "vector_search_gpu" if device == "cuda" else "vector_search_cpu",
            "top_matches": [
                {
                    "file": r.pattern_data.get("file_path", "unknown"),
                    "similarity": r.similarity,
                    "tags": r.tags,
                }
                for r in results[:3]
            ],
            "search_method": "semantic_embeddings",
            "gpu_metrics": {
                "device": device,
                "fp16_enabled": gpu_metrics.get("fp16_enabled", False),
                "avg_embedding_ms": gpu_metrics.get("avg_embedding_ms", 0),
                "cache_hit_rate": gpu_metrics.get("cache_hit_rate", 0),
            },
        }

        return memory, top_confidence

    except Exception as e:
        print(f"[VectorSearch] Error in MCP search: {e}", file=sys.stderr)
        return None, 0.0


def retrieve_hybrid_knowledge(info: dict[str, Any]) -> dict[str, Any]:
    """Hybrid knowledge retrieval with 3-tier architecture.

    TIER 1: Local (0 tokens, <0.5s) - 95% of cases
    TIER 2: MCP (~800 tokens, ~2s) - 5% of cases
    TIER 3: Graceful fallback - always allows
    """
    config = load_hybrid_config()
    start_time = time.time()

    # TIER 1: Always try local first
    local_memory, local_confidence = search_local_cipher(info)
    local_latency = int((time.time() - start_time) * 1000)

    tier_1_threshold = config.get("tier_1_local", {}).get("confidence_threshold", 0.50)
    if local_confidence >= tier_1_threshold:
        log_metrics("tier_1_local", 0, local_latency, local_confidence, info)
        return {
            "memory": local_memory,
            "tier": "tier_1_local",
            "confidence": local_confidence,
            "tokens_used": 0,
            "latency_ms": local_latency,
            "fallback_used": False,
        }

    # TIER 2: Low confidence or no results -> Try MCP
    if is_mcp_available() and should_use_mcp(info, local_confidence, config):
        try:
            mcp_start = time.time()
            mcp_memory, mcp_confidence = search_mcp_cipher(info, config)
            mcp_latency = int((time.time() - mcp_start) * 1000)

            if mcp_memory and mcp_confidence > 0:
                log_metrics("tier_2_mcp", 800, mcp_latency, mcp_confidence, info)
                return {
                    "memory": mcp_memory,
                    "tier": "tier_2_mcp",
                    "confidence": mcp_confidence,
                    "tokens_used": 800,
                    "latency_ms": mcp_latency,
                    "fallback_used": False,
                }
        except Exception as e:
            print(f"[Hybrid] MCP error, falling back to local: {e}", file=sys.stderr)

    # TIER 3: Graceful degradation
    total_latency = int((time.time() - start_time) * 1000)
    log_metrics("tier_3_fallback", 0, total_latency, local_confidence, info)

    return {
        "memory": local_memory,
        "tier": "tier_3_fallback",
        "confidence": local_confidence,
        "tokens_used": 0,
        "latency_ms": total_latency,
        "fallback_used": True,
    }


def extract_error_codes(text: str) -> set[str]:
    """Extract TypeScript/Python error codes from text.

    Examples: TS2375, TS2379, TS2322, TS2339, E501, E302, etc.
    """
    if not text:
        return set()

    error_codes: set[str] = set()
    error_codes.update(_TS_ERROR_RE.findall(text.upper()))
    error_codes.update(_PY_ERROR_RE.findall(text.upper()))
    error_codes.update(_COMMON_ERROR_RE.findall(text))

    return error_codes


def calculate_path_similarity(query_path: Path, pattern_path: Path) -> float:
    """Calculate path similarity between query and pattern.

    Scoring:
    - Same file extension: +0.3
    - Same directory: +0.3 (or same parent name: +0.2)
    - Contains similar keywords: +0.2
    """
    if not query_path or not pattern_path:
        return 0.0

    score = 0.0

    if query_path.suffix == pattern_path.suffix:
        score += 0.3

    if query_path.parent == pattern_path.parent:
        score += 0.3
    elif query_path.parent.name == pattern_path.parent.name:
        score += 0.2

    query_parts = set(str(query_path).lower().split("/"))
    pattern_parts = set(str(pattern_path).lower().split("/"))
    common_parts = query_parts & pattern_parts
    if common_parts:
        score += 0.2 * (len(common_parts) / max(len(query_parts), 1))

    return min(score, 1.0)


def calculate_tag_similarity(query_tags: set[str], pattern_tags: list[str]) -> float:
    """Calculate tag overlap similarity using Jaccard index."""
    if not query_tags or not pattern_tags:
        return 0.0

    pattern_tags_set = {tag.lower() for tag in pattern_tags}
    query_tags_lower = {tag.lower() for tag in query_tags}

    return calculate_similarity(query_tags_lower, pattern_tags_set)


def extract_tags_from_info(info: dict[str, Any]) -> set[str]:
    """Extract relevant tags from file info (extension, directory, error codes, language)."""
    tags: set[str] = set()

    file_path = Path(info.get("file_path", ""))
    content = info.get("content_preview", "")

    # File extension as tag
    if file_path.suffix in _EXT_TAG_MAP:
        tags.add(_EXT_TAG_MAP[file_path.suffix])

    # Directory context as tags
    parts = file_path.parts
    dir_tag_map = {
        "components": "component",
        "hooks": "hook",
        "services": "service",
        "api": "api",
    }
    for dir_name, tag in dir_tag_map.items():
        if dir_name in parts:
            tags.add(tag)
    if "utils" in parts or "helpers" in parts:
        tags.add("utility")
    if "tests" in parts or "test" in file_path.stem:
        tags.add("test")

    # Error codes as tags
    tags.update(extract_error_codes(content))

    # Common keywords as tags
    content_lower = content.lower()
    for keyword in _COMMON_KEYWORDS:
        if keyword in content_lower:
            tags.add(keyword)

    return tags


def calculate_hybrid_score(
    query_info: dict[str, Any],
    pattern_data: dict[str, Any],
    config: dict[str, Any],
) -> tuple[float, dict[str, float]]:
    """Calculate hybrid relevance score using multiple signals.

    Signals (default weights):
    1. Error code matching (40%): Exact match of error codes
    2. Tag matching (20%): Overlap in tags
    3. File path similarity (30%): Path/directory similarity
    4. Jaccard similarity (10%): Keyword overlap (baseline)
    """
    signal_weights = config.get("tier_1_local", {}).get(
        "signal_weights",
        {
            "error_code": 0.40,
            "tags": 0.20,
            "file_path": 0.30,
            "jaccard": 0.10,
        },
    )

    scores: dict[str, float] = {}

    # Signal 1: Error code matching
    query_errors = extract_error_codes(query_info.get("content_preview", ""))
    pattern_errors = extract_error_codes(
        pattern_data.get("problem", "")
        + " "
        + str(pattern_data.get("solution", ""))
        + " "
        + " ".join(pattern_data.get("tags", []))
    )

    if query_errors and pattern_errors:
        scores["error_code"] = len(query_errors & pattern_errors) / len(query_errors)
    else:
        scores["error_code"] = 0.0

    # Signal 2: Tag matching
    query_tags = extract_tags_from_info(query_info)
    scores["tags"] = calculate_tag_similarity(query_tags, pattern_data.get("tags", []))

    # Signal 3: File path similarity
    query_path = Path(query_info.get("file_path", ""))
    pattern_path_str = pattern_data.get("file_path", "")
    if not pattern_path_str:
        context = pattern_data.get("context", {})
        if isinstance(context, dict):
            files_affected = context.get("files_affected", [])
            if isinstance(files_affected, list) and files_affected:
                pattern_path_str = files_affected[0]

    pattern_path = Path(pattern_path_str) if pattern_path_str else Path("")
    scores["file_path"] = calculate_path_similarity(query_path, pattern_path)

    # Signal 4: Jaccard similarity (baseline)
    query_keywords = extract_keywords(query_info.get("content_preview", ""))
    pattern_keywords = extract_keywords(json.dumps(pattern_data))
    scores["jaccard"] = calculate_similarity(query_keywords, pattern_keywords)

    # Calculate weighted final score
    final_score = sum(scores.get(signal, 0.0) * weight for signal, weight in signal_weights.items())

    return min(final_score, 1.0), scores


def load_recent_error_patterns(file_path: Path, days: int = 7) -> list[dict[str, Any]]:
    """Load recent error patterns from `.cipher/error_patterns/` (H1).

    Proactive error prevention by loading recent failures.
    """
    try:
        error_patterns_dir = Path.cwd() / ".cipher" / "error_patterns"
        if not error_patterns_dir.exists():
            return []

        patterns: list[dict[str, Any]] = []
        cutoff = datetime.now().timestamp() - (days * 86400)

        for pattern_file in error_patterns_dir.glob("errors_*.json"):
            if pattern_file.stat().st_mtime < cutoff:
                continue

            try:
                with open(pattern_file, encoding="utf-8") as f:
                    data = json.load(f)

                for pattern in data.get("patterns", []):
                    pattern_file_path = Path(pattern.get("file_path", ""))
                    if file_path.suffix == pattern_file_path.suffix or file_path.parent == pattern_file_path.parent:
                        patterns.append(pattern)

            except (json.JSONDecodeError, OSError):
                continue

        patterns.sort(key=lambda p: p.get("timestamp", ""), reverse=True)
        return patterns[:10]

    except Exception as e:
        print(f"[ErrorPatterns] Load failed: {e}", file=sys.stderr)
        return []


def _empty_memory_result(storage: str = "no_patterns_yet") -> dict[str, Any]:
    """Return an empty memory result dict."""
    return {
        "decision": "allow",
        "found_memories": 0,
        "suggestions": [],
        "warnings": [],
        "confidence": 0.0,
        "storage": storage,
    }


def _check_pattern_file_ttl(pattern_file: Path) -> str:
    """Check pattern file age against TTL thresholds.

    Returns:
        "ok" — file is fresh, use normally.
        "stale" — file is old (>90d), use with warning.
        "expired" — file is very old (>180d), skip entirely.
    """
    try:
        age_seconds = time.time() - pattern_file.stat().st_mtime
    except OSError:
        return "ok"  # If stat fails, assume ok (fail-open)

    if age_seconds > _PATTERN_TTL_EXPIRE:
        return "expired"
    if age_seconds > _PATTERN_TTL_WARN:
        return "stale"
    return "ok"


def search_cipher_memory(info: dict[str, Any]) -> dict[str, Any] | None:
    """Busca conhecimento relevante no Cipher com HYBRID MULTI-SIGNAL SCORING (H0+H1).

    H0: Multi-signal scoring (error codes 40% + tags 20% + paths 30% + jaccard 10%)
    H1: Loads recent error patterns from `.cipher/error_patterns/`
    """
    try:
        file_path = Path(info.get("file_path", ""))
        content_preview = info.get("content_preview", "")

        cipher_dir = Path.cwd() / ".cipher" / "patterns"
        if not cipher_dir.exists():
            return _empty_memory_result("no_patterns_yet")

        config = load_hybrid_config()
        hybrid_enabled = config.get("tier_1_local", {}).get("hybrid_scoring", True)
        min_threshold = config.get("tier_1_local", {}).get("confidence_threshold", 0.05)

        matches: list[dict[str, Any]] = []
        stale_count = 0
        for pattern_file in cipher_dir.glob("*.json"):
            # TTL check: skip expired, warn on stale
            ttl_status = _check_pattern_file_ttl(pattern_file)
            if ttl_status == "expired":
                continue
            if ttl_status == "stale":
                stale_count += 1

            try:
                with open(pattern_file, encoding="utf-8") as f:
                    pattern_data_file = json.load(f)

                patterns_list = pattern_data_file.get("patterns", [])
                if not patterns_list and pattern_data_file.get("pattern_id"):
                    patterns_list = [pattern_data_file]

                for pattern in patterns_list:
                    if hybrid_enabled:
                        similarity, signal_breakdown = calculate_hybrid_score(
                            info,
                            pattern,
                            config,
                        )
                    else:
                        # Fallback: Original Jaccard-only scoring
                        file_keywords = extract_keywords(file_path.stem)
                        content_keywords = extract_keywords(content_preview[:200])
                        query_keywords = file_keywords | content_keywords

                        pattern_file_path = Path(pattern.get("file_path", ""))
                        pattern_keywords = extract_keywords(pattern_file_path.stem) | extract_keywords(
                            pattern.get("content_preview", "")
                        )
                        similarity = calculate_similarity(query_keywords, pattern_keywords)
                        signal_breakdown = {}

                        if file_path.suffix == pattern_file_path.suffix:
                            similarity *= 1.2

                    if similarity > min_threshold:
                        match_data: dict[str, Any] = {
                            "similarity": min(similarity, 1.0),
                            "pattern": pattern,
                            "pattern_file": pattern_file.name,
                        }
                        if signal_breakdown:
                            match_data["signal_breakdown"] = signal_breakdown
                        matches.append(match_data)

            except (json.JSONDecodeError, OSError) as e:
                print(
                    f"[Cipher] Warning: Could not load pattern file {pattern_file}: {e}",
                    file=sys.stderr,
                )
                continue

        matches.sort(key=lambda m: m["similarity"], reverse=True)

        # H1: Proactive warnings from recent error patterns
        error_patterns = load_recent_error_patterns(file_path, days=30)

        suggestions: list[str] = []
        warnings: list[str] = []
        top_confidence = 0.0

        # TTL staleness warning
        if stale_count > 0:
            warnings.append(f"{stale_count} pattern file(s) older than 90 days — consider refreshing")

        if error_patterns:
            error_codes_seen: set[str] = set()
            for err_pattern in error_patterns[:3]:
                for code in err_pattern.get("error_codes", []):
                    if code not in error_codes_seen:
                        warnings.append(f"Recent error in similar files: {code}")
                        error_codes_seen.add(code)
                        if len(warnings) >= 2:
                            break
                if len(warnings) >= 2:
                    break

        for match in matches[:5]:
            pattern = match["pattern"]
            top_confidence = max(top_confidence, match["similarity"])

            if pattern.get("tags"):
                tags_str = ", ".join(pattern["tags"][:3])
                suggestions.append(f"Similar pattern used: {tags_str}")

            if pattern.get("quality_score", 1.0) < 0.7:
                warnings.append("Previous implementation had quality issues")

        return {
            "decision": "allow",
            "found_memories": len(matches),
            "suggestions": suggestions[:3],
            "warnings": warnings[:2],
            "confidence": top_confidence,
            "storage": "local_cipher_compatible",
            "top_matches": [
                {
                    "file": m["pattern"].get("file_path"),
                    "similarity": m["similarity"],
                    "tags": m["pattern"].get("tags", []),
                }
                for m in matches[:3]
            ],
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "storage": "failed",
        }


def format_retrieval_message(info: dict[str, Any], result: dict[str, Any]) -> str:
    """Formata mensagem de contexto recuperado com informacoes de tier."""
    memory = result.get("memory")
    if not memory or memory.get("status") == "error":
        return ""

    found = memory.get("found_memories", 0)
    if found == 0:
        return ""

    tier = result.get("tier", "unknown")
    tokens = result.get("tokens_used", 0)
    latency = result.get("latency_ms", 0)
    confidence = result.get("confidence", 0)
    fallback = result.get("fallback_used", False)

    tier_labels = {
        "tier_1_local": "Local Cache",
        "tier_2_mcp": "MCP Enhancement",
        "tier_3_fallback": "Local Fallback",
    }
    tier_label = tier_labels.get(tier, "Cipher Knowledge")

    lines = [
        "",
        f"{tier_label} Retrieved",
        "-" * 40,
        f"File: {Path(info['file_path']).name}",
        f"Found: {found} relevant memory(ies)",
        f"Latency: {latency}ms | Tokens: {tokens}",
        "",
    ]

    if fallback:
        lines.append("Using local results (MCP unavailable)")
        lines.append("")

    suggestions = memory.get("suggestions", [])
    if suggestions:
        lines.append("Suggestions from past experience:")
        for i, suggestion in enumerate(suggestions[:3], 1):
            lines.append(f"  {i}. {suggestion}")
        lines.append("")

    warnings = memory.get("warnings", [])
    if warnings:
        lines.append("Known pitfalls:")
        lines.extend(f"  - {warning}" for warning in warnings[:2])
        lines.append("")

    if confidence > 0.7:
        lines.append(f"High confidence match ({confidence:.0%})")
    elif confidence > 0.5:
        lines.append(f"Medium confidence match ({confidence:.0%})")
    elif confidence > 0:
        lines.append(f"Low confidence match ({confidence:.0%})")

    lines.append("-" * 40)
    return "\n".join(lines)


def main() -> int:
    """Hook principal executado no PreToolUse.

    Implementa arquitetura hibrida de 3 tiers:
    - TIER 1: Local cache (95% - high confidence)
    - TIER 2: MCP enhancement (5% - low confidence, explicit triggers)
    - TIER 3: Graceful fallback (always allows)
    """
    try:
        # Claude Code sends hook payload via stdin JSON, not sys.argv.
        # sys.argv is always empty for hooks; reading it caused this hook
        # to return "No arguments provided" on every single invocation.
        data = json.load(sys.stdin)
        tool_name = data.get("tool_name", "")
        params = data.get("tool_input", {})

        if not tool_name:
            print(format_pretool_output("allow", "No tool_name in payload"))
            return 0

        info = parse_tool_params(tool_name, params)

        if not should_check_cipher(info):
            print(format_pretool_output("allow", "No cipher check needed"))
            return 0

        hybrid_result = retrieve_hybrid_knowledge(info)
        message = format_retrieval_message(info, hybrid_result)

        memory = hybrid_result.get("memory")

        metadata = {
            "hybrid_architecture": True,
            "tier_used": hybrid_result.get("tier"),
            "tokens_used": hybrid_result.get("tokens_used", 0),
            "latency_ms": hybrid_result.get("latency_ms", 0),
            "confidence": hybrid_result.get("confidence", 0),
            "fallback_used": hybrid_result.get("fallback_used", False),
            "found_memories": memory.get("found_memories", 0) if memory else 0,
        }

        print(format_pretool_output("allow", message, metadata=metadata))

        if message:
            tier = hybrid_result.get("tier", "unknown")
            tokens = hybrid_result.get("tokens_used", 0)
            print(
                f"[Hybrid] {tier} - Retrieved context for {info['file_path']} ({tokens} tokens)",
                file=sys.stderr,
            )

        return 0

    except Exception as e:
        print(format_pretool_output("allow", f"Cipher retrieval error: {e}"))
        print(f"[Hybrid] ERROR: {e}", file=sys.stderr)
        return 0


if __name__ == "__main__":
    sys.exit(main())
