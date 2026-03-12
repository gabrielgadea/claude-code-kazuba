#!/usr/bin/env python3
"""
Cipher Knowledge Capture Hook (PostToolUse)

Captura e armazena conhecimento APÓS operações Write/Edit bem-sucedidas,
especialmente quando passam pelos quality gates.

Execução: DEPOIS de Write/Edit/MultiEdit (sucesso)
Integração: PostToolUse hook

Capacidades:
- Armazena padrões de código bem-sucedidos
- Captura soluções para problemas recorrentes
- Extrai tags automaticamente via IA
- Mantém confidence scoring
- Cria embeddings vetoriais para busca semântica
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

# Try to import vector search for embedding generation
try:
    from cipher_vector_search import CipherVectorSearch

    VECTOR_SEARCH_AVAILABLE = True
except ImportError:
    VECTOR_SEARCH_AVAILABLE = False

# Pre-computed skip suffixes (binary + temporary) — avoid per-call list creation
_SKIP_SUFFIXES = frozenset(
    {
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
    }
)

# Pre-computed language map — avoid per-call dict creation
_LANG_MAP = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript-react",
    ".js": "javascript",
    ".jsx": "javascript-react",
    ".vue": "vue",
    ".go": "golang",
    ".rs": "rust",
    ".md": "markdown",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".xml": "xml",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "bash",
}

# Pre-computed config suffixes for tag detection
_CONFIG_SUFFIXES = frozenset({".json", ".yaml", ".yml", ".toml"})


def parse_tool_result(tool_name: str, params: dict, result: dict) -> dict:
    """Extrai informações do resultado da ferramenta."""
    info = {
        "tool": tool_name,
        "file_path": None,
        "content": None,
        "operation_type": None,
        "success": result.get("success", False),
        "timestamp": datetime.now().isoformat(),
    }

    if tool_name == "Write":
        info["file_path"] = params.get("file_path")
        info["content"] = params.get("content", "")
        info["operation_type"] = "create"

    elif tool_name in ["Edit", "MultiEdit"]:
        info["file_path"] = params.get("file_path")
        info["content"] = f"OLD: {params.get('old_string', '')}\nNEW: {params.get('new_string', '')}"
        info["operation_type"] = "modify"

    return info


def should_capture_knowledge(info: dict) -> bool:
    """Determina se deve capturar conhecimento desta operação."""
    # Só capturar operações bem-sucedidas
    if not info.get("success"):
        return False

    # Só capturar se houver file_path
    if not info.get("file_path"):
        return False

    file_path = Path(info["file_path"])

    # Skip binary and temporary files — frozenset O(1) lookup
    return file_path.suffix not in _SKIP_SUFFIXES


def extract_knowledge_tags(info: dict) -> list[str]:
    """
    Extrai tags automaticamente do conteúdo.

    Em produção: IA extrai tags semanticamente.
    Por ora: extração baseada em padrões.
    """
    tags = []

    file_path = Path(info.get("file_path", ""))
    content = info.get("content", "")

    # Tag by language/file type — uses module-level _LANG_MAP
    lang = _LANG_MAP.get(file_path.suffix)
    if lang:
        tags.append(lang)

    # Tag por tipo de operação
    tags.append(info.get("operation_type", "unknown"))

    # Tags por contexto de diretório
    parts = file_path.parts
    if "components" in parts:
        tags.append("component")
    if "hooks" in parts:
        tags.append("hook")
    if "services" in parts:
        tags.append("service")
    if "utils" in parts:
        tags.append("utility")
    if "tests" in parts or "test" in file_path.stem:
        tags.append("test")
    if ".claude" in parts:
        tags.append("claude-config")
    if "docs" in parts or "documentation" in parts:
        tags.append("documentation")

    # Tags por tipo de documento/configuração
    if file_path.suffix == ".md":
        # Detectar tipo de documento Markdown
        name_lower = file_path.stem.lower()
        if "adr" in name_lower or "architecture" in name_lower:
            tags.append("adr")
        if "guide" in name_lower or "workflow" in name_lower:
            tags.append("guide")
        if "readme" in name_lower:
            tags.append("readme")
        if "plan" in name_lower:
            tags.append("plan")
        if "report" in name_lower:
            tags.append("report")
        tags.append("documentation")

    if file_path.suffix in _CONFIG_SUFFIXES:
        tags.append("configuration")
        if "package" in file_path.stem:
            tags.append("dependencies")
        if "config" in file_path.stem or "settings" in file_path.stem:
            tags.append("settings")

    # Tags por conteúdo (análise simples)
    if "async" in content or "await" in content:
        tags.append("async")
    if "class " in content:
        tags.append("class")
    if "def " in content or "function " in content:
        tags.append("function")
    if "import" in content:
        tags.append("imports")

    return list(set(tags))  # Remove duplicatas


def generate_memory_id(info: dict) -> str:
    """Gera ID único para a memória."""
    content = f"{info['file_path']}:{info['timestamp']}:{info['content'][:100]}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def create_memory_entry(info: dict) -> dict:
    """Cria entrada de memória estruturada para o Cipher."""
    memory = {
        "id": generate_memory_id(info),
        "type": "code_pattern",
        "file_path": info["file_path"],
        "operation": info["operation_type"],
        "content": info["content"][:1000],  # Limitar tamanho
        "tags": extract_knowledge_tags(info),
        "timestamp": info["timestamp"],
        "confidence": 0.95,  # Alta confiança - passou pelos quality gates
        "metadata": {
            "tool": info["tool"],
            "success": info["success"],
            "quality_gate_passed": True,  # Se chegou aqui, passou
        },
    }

    # Generate embedding if vector search available
    if VECTOR_SEARCH_AVAILABLE:
        try:
            searcher = CipherVectorSearch()
            # Combine file path and content for better semantic representation
            text_for_embedding = f"{info['file_path']} {info['content'][:500]}"
            embedding = searcher.encode_text(text_for_embedding)

            if embedding is not None:
                memory["metadata"]["has_embedding"] = True
                memory["metadata"]["embedding_model"] = searcher.model_name
            else:
                memory["metadata"]["has_embedding"] = False
        except Exception as e:
            print(f"[Cipher] Warning: Could not generate embedding: {e}", file=sys.stderr)
            memory["metadata"]["has_embedding"] = False
    else:
        memory["metadata"]["has_embedding"] = False

    return memory


def store_in_cipher(memory: dict) -> dict:
    """
    Armazena memória no Cipher.

    Implementação: Local Cipher-compatible storage em .cipher/patterns/
    Futuramente: Migrar para chamadas diretas ao Cipher MCP server

    Patterns são agrupados por tipo de arquivo para eficiência:
    - python_patterns.json
    - typescript_patterns.json
    - javascript_patterns.json

    Args:
        memory: Entrada de memória estruturada

    Returns:
        dict com status do armazenamento
    """
    try:
        # Setup do diretório Cipher local
        cipher_dir = Path.cwd() / ".cipher" / "patterns"
        cipher_dir.mkdir(parents=True, exist_ok=True)

        # Determinar arquivo baseado na linguagem principal
        primary_tag = memory["tags"][0] if memory["tags"] else "general"
        pattern_file = cipher_dir / f"{primary_tag}_patterns.json"

        # Carregar padrões existentes
        existing_patterns = {"patterns": [], "metadata": {}}
        if pattern_file.exists():
            try:
                with open(pattern_file, encoding="utf-8") as f:
                    existing_patterns = json.load(f)
            except (OSError, json.JSONDecodeError) as e:
                print(f"[Cipher] Warning: Could not load existing patterns: {e}", file=sys.stderr)
                existing_patterns = {"patterns": [], "metadata": {}}

        # Adicionar nova memória
        # Armazenar apenas preview do content para economizar espaço
        stored_memory = {
            "id": memory["id"],
            "file_path": memory["file_path"],
            "operation": memory["operation"],
            "content_preview": memory["content"][:300],  # Preview limitado
            "tags": memory["tags"],
            "timestamp": memory["timestamp"],
            "confidence": memory["confidence"],
            "quality_score": 0.95,  # Alta qualidade (passou quality gates)
        }

        existing_patterns["patterns"].append(stored_memory)

        # Limitar tamanho - manter apenas os 100 padrões mais recentes por arquivo
        if len(existing_patterns["patterns"]) > 100:
            # Ordenar por timestamp (mais recente primeiro)
            existing_patterns["patterns"].sort(key=lambda p: p.get("timestamp", ""), reverse=True)
            existing_patterns["patterns"] = existing_patterns["patterns"][:100]

        # Atualizar metadata
        existing_patterns["metadata"] = {
            "last_updated": datetime.now().isoformat(),
            "total_patterns": len(existing_patterns["patterns"]),
            "storage_type": "local_cipher_compatible",
            "primary_tag": primary_tag,
        }

        # Persistir
        try:
            with open(pattern_file, "w", encoding="utf-8") as f:
                json.dump(existing_patterns, f, indent=2, ensure_ascii=False)
        except OSError as e:
            print(f"[Cipher] Error: Could not save patterns: {e}", file=sys.stderr)
            return {"status": "error", "error": f"Failed to save patterns: {e}"}

        return {
            "decision": "allow",
            "memory_id": memory["id"],
            "tags": memory["tags"],
            "storage_file": str(pattern_file.name),
            "total_stored": existing_patterns["metadata"]["total_patterns"],
            "message": f"Knowledge stored: {Path(memory['file_path']).name}",
        }

    except Exception as e:
        return {"status": "error", "error": str(e), "storage": "failed"}


def format_capture_message(memory: dict, store_result: dict) -> str:
    """Formata mensagem de captura."""
    if store_result.get("decision") != "allow":
        return ""

    lines = [
        "",
        "🧠 Cipher Knowledge Captured",
        "-" * 40,
        f"📁 File: {Path(memory['file_path']).name}",
        f"🏷️  Tags: {', '.join(memory['tags'][:5])}",
        f"📊 Confidence: {memory['confidence']:.0%}",
        f"🆔 Memory ID: {memory['id']}",
        "",
        "✅ Knowledge stored successfully",
        "   Available for future retrieval via cipher-search-memory",
        "-" * 40,
    ]

    return "\n".join(lines)


def format_posttool_output(context: str = "", suppress: bool = True) -> str:
    """Format output for PostToolUse hooks according to Anthropic schema.

    Args:
        context: Additional context for Claude
        suppress: Whether to suppress output in transcript

    Returns:
        JSON string with correct Anthropic schema format
    """
    output = {
        "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": context},
        "suppressOutput": suppress,
    }
    return json.dumps(output)


def main():
    """Hook principal executado no PostToolUse."""
    try:
        # Read JSON event from stdin — Claude Code hook protocol.
        # PostToolUse hooks receive: tool_name, tool_input, tool_response via stdin.
        try:
            event = json.load(sys.stdin)
        except (json.JSONDecodeError, EOFError):
            print(format_posttool_output(""))
            return 0

        tool_name = event.get("tool_name", "")
        params = event.get("tool_input", {})
        # PostToolUse is only invoked after successful tool execution.
        result = {"success": True}

        # Parsear informações
        info = parse_tool_result(tool_name, params, result)

        # Verificar se deve capturar
        if not should_capture_knowledge(info):
            print(format_posttool_output(""))
            return 0

        # Criar entrada de memória
        memory = create_memory_entry(info)

        # Armazenar no Cipher
        store_result = store_in_cipher(memory)

        # Formatar mensagem
        message = format_capture_message(memory, store_result)

        # Output in Anthropic-compliant format
        context = message if message else ""
        print(format_posttool_output(context, suppress=True))

        if message:
            print(f"[Cipher] Captured knowledge for {info['file_path']}", file=sys.stderr)

        return 0

    except Exception as e:
        print(format_posttool_output(f"⚠️ Cipher capture error: {e}"))
        print(f"[Cipher] ERROR: {e}", file=sys.stderr)
        return 0  # Não falha a operação principal


if __name__ == "__main__":
    sys.exit(main())
