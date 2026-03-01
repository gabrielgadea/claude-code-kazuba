#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# claude-code-kazuba installer
# ============================================================================
# Usage:
#   ./install.sh --preset minimal --target /path/to/project
#   ./install.sh --modules core,hooks-essential --target .
#   ./install.sh --preset standard --dry-run
#   ./install.sh --help
#
# Remote install:
#   curl -sL https://raw.githubusercontent.com/gabrielgadea/claude-code-kazuba/main/install.sh | bash -s -- --preset standard
# ============================================================================

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PRESETS_DIR="${SCRIPT_DIR}/presets"
MODULES_DIR="${SCRIPT_DIR}/modules"
CORE_DIR="${SCRIPT_DIR}/core"
SCRIPTS_DIR="${SCRIPT_DIR}/scripts"

PRESET=""
MODULES=""
TARGET_DIR=""
DRY_RUN=false
VERBOSE=false

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------
_RED='\033[0;31m'
_GREEN='\033[0;32m'
_YELLOW='\033[0;33m'
_BLUE='\033[0;34m'
_BOLD='\033[1m'
_NC='\033[0m'

info()    { echo -e "${_BLUE}[INFO]${_NC} $*"; }
success() { echo -e "${_GREEN}[OK]${_NC} $*"; }
warn()    { echo -e "${_YELLOW}[WARN]${_NC} $*"; }
error()   { echo -e "${_RED}[ERROR]${_NC} $*" >&2; }

# ---------------------------------------------------------------------------
# Usage
# ---------------------------------------------------------------------------
usage() {
    cat <<EOF
${_BOLD}claude-code-kazuba installer${_NC}

${_BOLD}USAGE${_NC}
    $(basename "$0") [OPTIONS]

${_BOLD}OPTIONS${_NC}
    --preset NAME       Use a preset (minimal, standard, professional, enterprise, research)
    --modules M,M,...   Install specific modules (comma-separated)
    --target DIR        Target project directory (default: current directory)
    --dry-run           Show plan without writing files
    --verbose           Show detailed output
    --help              Show this help message

${_BOLD}PRESETS${_NC}
    minimal         Core configuration only
    standard        Core + essential hooks + meta skills + planning + contexts
    professional    Standard + quality/routing hooks + dev skills/agents/commands
    enterprise      Professional + research + PRP + hypervisor + team orchestrator
    research        Core + essential hooks + planning + research skills + contexts

${_BOLD}EXAMPLES${_NC}
    $(basename "$0") --preset standard --target /path/to/project
    $(basename "$0") --modules core,hooks-essential --target .
    $(basename "$0") --preset minimal --dry-run
EOF
    exit 0
}

# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------
parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --preset)
                PRESET="${2:-}"
                [[ -z "$PRESET" ]] && { error "--preset requires a value"; exit 1; }
                shift 2
                ;;
            --modules)
                MODULES="${2:-}"
                [[ -z "$MODULES" ]] && { error "--modules requires a value"; exit 1; }
                shift 2
                ;;
            --target)
                TARGET_DIR="${2:-}"
                [[ -z "$TARGET_DIR" ]] && { error "--target requires a value"; exit 1; }
                shift 2
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --help|-h)
                usage
                ;;
            *)
                error "Unknown option: $1"
                echo "Run with --help for usage."
                exit 1
                ;;
        esac
    done

    # Default target to current directory
    [[ -z "$TARGET_DIR" ]] && TARGET_DIR="$(pwd)"
    TARGET_DIR="$(cd "$TARGET_DIR" 2>/dev/null && pwd)" || {
        error "Target directory does not exist: $TARGET_DIR"
        exit 1
    }

    # Validate: must have --preset or --modules
    if [[ -z "$PRESET" && -z "$MODULES" ]]; then
        error "Must specify --preset or --modules"
        echo "Run with --help for usage."
        exit 1
    fi

    # Validate: can't have both
    if [[ -n "$PRESET" && -n "$MODULES" ]]; then
        error "Cannot specify both --preset and --modules"
        exit 1
    fi
}

# ---------------------------------------------------------------------------
# Find Python 3
# ---------------------------------------------------------------------------
find_python() {
    local py=""
    for candidate in python3 python; do
        if command -v "$candidate" &>/dev/null; then
            local ver
            ver="$("$candidate" --version 2>&1 | grep -oP '\d+\.\d+')"
            if [[ "$(echo "$ver >= 3.10" | bc -l 2>/dev/null || echo 0)" == "1" ]]; then
                py="$candidate"
                break
            fi
        fi
    done

    if [[ -z "$py" ]]; then
        # Check for venv in project
        if [[ -f "${SCRIPT_DIR}/.venv/bin/python" ]]; then
            py="${SCRIPT_DIR}/.venv/bin/python"
        else
            error "Python 3.10+ not found. Install Python or create a venv."
            exit 1
        fi
    fi
    echo "$py"
}

# ---------------------------------------------------------------------------
# Load preset
# ---------------------------------------------------------------------------
load_preset() {
    local preset_file="${PRESETS_DIR}/${PRESET}.txt"
    if [[ ! -f "$preset_file" ]]; then
        error "Unknown preset: ${PRESET}"
        info "Available presets:"
        for f in "${PRESETS_DIR}"/*.txt; do
            echo "  - $(basename "$f" .txt)"
        done
        exit 1
    fi

    # Read modules from preset file (skip empty lines and comments)
    local modules_list=""
    while IFS= read -r line; do
        line="$(echo "$line" | sed 's/#.*//' | xargs)"
        [[ -z "$line" ]] && continue
        [[ -n "$modules_list" ]] && modules_list="${modules_list},"
        modules_list="${modules_list}${line}"
    done < "$preset_file"

    MODULES="$modules_list"
    info "Loaded preset '${PRESET}': ${MODULES}"
}

# ---------------------------------------------------------------------------
# Stack detection
# ---------------------------------------------------------------------------
detect_stack() {
    local py="$1"
    info "Detecting project stack..." >&2
    local stack_output
    stack_output="$(cd "$TARGET_DIR" && PYTHONPATH="${SCRIPT_DIR}" "$py" -c "
from claude_code_kazuba.installer.detect_stack import detect_stack
from pathlib import Path
info = detect_stack(Path('.'))
for k, v in sorted(info.items()):
    print(f'{k}={v}')
" 2>/dev/null)" || stack_output="language=unknown"

    echo "$stack_output"
}

# ---------------------------------------------------------------------------
# Resolve dependencies
# ---------------------------------------------------------------------------
resolve_deps() {
    local py="$1"
    local module_list="$2"

    # Convert comma-separated to space-separated args
    local args
    args="$(echo "$module_list" | tr ',' ' ')"

    info "Resolving dependencies..." >&2
    local resolved
    resolved="$(PYTHONPATH="${SCRIPT_DIR}" "$py" -c "
import sys
from claude_code_kazuba.installer.resolve_deps import resolve_dependencies
from pathlib import Path
modules_dir = Path('${MODULES_DIR}')
core_dir = Path('${CORE_DIR}')
names = '${args}'.split()
try:
    order = resolve_dependencies(names, modules_dir, core_dir=core_dir)
    for m in order:
        print(m)
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    sys.exit(1)
")" || {
        error "Dependency resolution failed"
        exit 1
    }

    echo "$resolved"
}

# ---------------------------------------------------------------------------
# Install a single module
# ---------------------------------------------------------------------------
install_one_module() {
    local py="$1"
    local module_name="$2"
    local stack_vars="$3"

    info "Installing module: ${_BOLD}${module_name}${_NC}"

    local var_args=""
    while IFS= read -r line; do
        [[ -z "$line" ]] && continue
        var_args="${var_args}, '${line%%=*}': '${line#*=}'"
    done <<< "$stack_vars"

    local output
    output="$(PYTHONPATH="${SCRIPT_DIR}" "$py" -c "
import json
from pathlib import Path
from claude_code_kazuba.installer.install_module import install_module
variables = {${var_args:2}}
result = install_module(
    '${module_name}',
    Path('${SCRIPT_DIR}'),
    Path('${TARGET_DIR}'),
    variables,
)
print(json.dumps(result))
")" || {
        error "Failed to install module: ${module_name}"
        return 1
    }

    if $VERBOSE; then
        echo "$output" | python3 -m json.tool 2>/dev/null || echo "$output"
    fi

    local copied merged rendered
    copied="$(echo "$output" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('copied',[])))" 2>/dev/null || echo 0)"
    merged="$(echo "$output" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('merged',[])))" 2>/dev/null || echo 0)"
    rendered="$(echo "$output" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('rendered',[])))" 2>/dev/null || echo 0)"

    success "${module_name}: ${copied} copied, ${merged} merged, ${rendered} rendered"
}

# ---------------------------------------------------------------------------
# Post-install validation
# ---------------------------------------------------------------------------
validate() {
    local py="$1"
    info "Running post-install validation..."

    local output
    output="$(PYTHONPATH="${SCRIPT_DIR}" "$py" -c "
import json
from pathlib import Path
from claude_code_kazuba.installer.validate_installation import validate_installation
results = validate_installation(Path('${TARGET_DIR}'))
messages = results.pop('_messages', [])
for msg in messages:
    print(msg)
all_ok = results.pop('all_passed', False)
print('ALL_PASSED=' + str(all_ok))
")" || {
        warn "Validation script encountered an error"
        return 0
    }

    echo "$output" | while IFS= read -r line; do
        if [[ "$line" == *"[PASS]"* ]]; then
            success "${line#*] }"
        elif [[ "$line" == *"[FAIL]"* ]]; then
            error "${line#*] }"
        elif [[ "$line" == "ALL_PASSED=True" ]]; then
            echo ""
            success "All validation checks passed!"
        elif [[ "$line" == "ALL_PASSED=False" ]]; then
            echo ""
            warn "Some validation checks failed. Review the output above."
        fi
    done
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
main() {
    echo ""
    echo -e "${_BOLD}claude-code-kazuba installer${_NC}"
    echo "========================================"
    echo ""

    parse_args "$@"

    # Load preset if specified
    [[ -n "$PRESET" ]] && load_preset

    # Find Python
    local py
    py="$(find_python)"
    info "Using Python: $py"

    # Detect stack
    local stack_vars
    stack_vars="$(detect_stack "$py")"
    while IFS= read -r line; do
        [[ -n "$line" ]] && info "Stack: $line"
    done <<< "$stack_vars"

    # Resolve dependencies
    local resolved
    resolved="$(resolve_deps "$py" "$MODULES")"

    # Count modules
    local count
    count="$(echo "$resolved" | grep -c . || true)"
    echo ""
    info "Installation plan: ${count} module(s) to install"
    info "Target: ${TARGET_DIR}"
    echo ""

    # Show plan
    local i=1
    while IFS= read -r mod; do
        [[ -z "$mod" ]] && continue
        echo -e "  ${_BOLD}${i}.${_NC} ${mod}"
        ((i++))
    done <<< "$resolved"
    echo ""

    # Dry run?
    if $DRY_RUN; then
        warn "Dry run mode — no files were written."
        exit 0
    fi

    # Create .claude/ directory
    mkdir -p "${TARGET_DIR}/.claude"

    # Install each module
    local failed=0
    while IFS= read -r mod; do
        [[ -z "$mod" ]] && continue
        install_one_module "$py" "$mod" "$stack_vars" || ((failed++))
    done <<< "$resolved"

    echo ""

    if [[ $failed -gt 0 ]]; then
        error "${failed} module(s) failed to install."
        exit 1
    fi

    success "All ${count} module(s) installed successfully!"
    echo ""

    # Validate
    validate "$py"

    echo ""
    echo -e "${_BOLD}Installation complete!${_NC}"
    echo ""
    info "Next steps:"
    echo "  1. Review .claude/CLAUDE.md"
    echo "  2. Review .claude/settings.json"
    echo "  3. Start Claude Code in your project"
    echo ""
}

main "$@"
