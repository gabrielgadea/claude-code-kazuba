#!/usr/bin/env python3
"""Generate a scripted asciinema v2 cast demonstrating the PyPI installation flow.

Produces `kazuba-demo.cast` in the same directory as this script.
The cast simulates the full pip-install-to-validate journey without
requiring any real packages to be installed.

Usage:
    python docs/demo/generate_cast.py
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

# ---------------------------------------------------------------------------
# ANSI escape helpers
# ---------------------------------------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
WHITE = "\033[97m"
DIM = "\033[2m"
BOLD_GREEN = f"{BOLD}{GREEN}"
BOLD_RED = f"{BOLD}{RED}"
BOLD_WHITE = f"{BOLD}{WHITE}"
BOLD_YELLOW = f"{BOLD}{YELLOW}"
BOLD_CYAN = f"{BOLD}{CYAN}"

PROMPT = f"{BOLD_GREEN}~{RESET} {BOLD_WHITE}${RESET} "

# Typing speed: 40ms per character (natural touch-typing pace)
CHAR_DELAY = 0.040


# ---------------------------------------------------------------------------
# Cast builder
# ---------------------------------------------------------------------------

@dataclass
class CastBuilder:
    """Incrementally builds asciinema v2 cast events."""

    width: int = 120
    height: int = 30
    title: str = "Kazuba — pip install & protect your Claude Code project"
    events: list[list[float | str]] = field(default_factory=list)
    cursor: float = 0.0  # current timestamp in seconds

    # -- timing helpers -----------------------------------------------------

    def advance(self, seconds: float) -> None:
        """Move the clock forward."""
        self.cursor += seconds

    # -- output primitives --------------------------------------------------

    def emit(self, text: str, dt: float = 0.0) -> None:
        """Append a single output event at cursor + dt."""
        self.cursor += dt
        self.events.append([round(self.cursor, 6), "o", text])

    def type_chars(self, text: str, *, delay: float = CHAR_DELAY) -> None:
        """Emit characters one at a time to simulate human typing."""
        for ch in text:
            self.emit(ch, dt=delay)

    def instant(self, text: str) -> None:
        """Emit text with no additional delay."""
        self.emit(text)

    def newline(self) -> None:
        self.emit("\r\n")

    # -- high-level helpers -------------------------------------------------

    def prompt(self) -> None:
        """Show a bash prompt."""
        self.emit(PROMPT)

    def type_command(self, cmd: str) -> None:
        """Type a command character-by-character, then press Enter."""
        self.prompt()
        self.type_chars(cmd)
        self.newline()

    def output_line(self, text: str, *, delay: float = 0.05) -> None:
        """Print a full line of output with a small delay."""
        self.advance(delay)
        self.emit(text + "\r\n")

    def blank_line(self, *, delay: float = 0.03) -> None:
        self.advance(delay)
        self.emit("\r\n")

    def pause(self, seconds: float) -> None:
        """Idle pause (between commands, waiting for output, etc.)."""
        self.advance(seconds)

    def progress_bar(self, label: str, total_kb: int, *, duration: float = 1.5) -> None:
        """Simulate a pip download progress bar that updates in-place."""
        steps = 8
        step_time = duration / steps
        for i in range(1, steps + 1):
            frac = i / steps
            done_kb = int(total_kb * frac)
            bar_len = 20
            filled = int(bar_len * frac)
            bar = "#" * filled + "-" * (bar_len - filled)
            pct = int(frac * 100)
            line = f"\r{DIM}  [{bar}] {done_kb}/{total_kb} kB ({pct}%){RESET}"
            self.advance(step_time)
            self.emit(line)
        self.emit(f"\r{' ' * 60}\r")  # clear the progress line

    # -- serialization ------------------------------------------------------

    def build(self) -> str:
        """Return the full cast file content (header + events)."""
        header = {
            "version": 2,
            "width": self.width,
            "height": self.height,
            "timestamp": int(time.time()),
            "title": self.title,
            "env": {"TERM": "xterm-256color", "SHELL": "/bin/bash"},
        }
        lines = [json.dumps(header, ensure_ascii=False)]
        for ev in self.events:
            lines.append(json.dumps(ev, ensure_ascii=False))
        return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Scene builders
# ---------------------------------------------------------------------------

def scene_pip_install(c: CastBuilder) -> None:
    """Scene 1: pip install claude-code-kazuba (~16s)."""
    c.pause(1.0)
    c.type_command("pip install claude-code-kazuba")

    # Simulated pip output — network fetching feels slow
    c.pause(0.6)
    c.output_line(f"{DIM}Collecting claude-code-kazuba{RESET}")
    c.pause(1.5)
    c.output_line(f"{DIM}  Downloading claude_code_kazuba-0.2.0-py3-none-any.whl (148 kB){RESET}")
    c.progress_bar("claude_code_kazuba", 148, duration=2.2)
    c.pause(0.4)
    c.output_line(f"{DIM}Collecting pydantic>=2.0{RESET}")
    c.pause(0.6)
    c.output_line(f"{DIM}  Using cached pydantic-2.11.1-py3-none-any.whl (443 kB){RESET}")
    c.pause(0.4)
    c.output_line(f"{DIM}Collecting jinja2>=3.1{RESET}")
    c.pause(0.5)
    c.output_line(f"{DIM}  Using cached jinja2-3.1.6-py3-none-any.whl (134 kB){RESET}")
    c.pause(0.4)
    c.output_line(f"{DIM}Collecting msgpack>=1.0{RESET}")
    c.pause(0.3)
    c.output_line(f"{DIM}  Using cached msgpack-1.1.0-cp312-cp312-linux_x86_64.whl (401 kB){RESET}")
    c.pause(1.2)
    c.output_line(f"{DIM}Installing collected packages: msgpack, markupsafe, jinja2, "
                  f"annotated-types, pydantic-core, pydantic, claude-code-kazuba{RESET}")
    c.pause(2.5)
    c.output_line(f"{BOLD_GREEN}Successfully installed claude-code-kazuba-0.2.0{RESET}")
    c.pause(2.5)


def scene_version(c: CastBuilder) -> None:
    """Scene 2: kazuba --version (~3.5s)."""
    c.type_command("kazuba --version")
    c.pause(0.5)
    c.output_line("kazuba 0.2.0")
    c.pause(2.0)


def scene_list_presets(c: CastBuilder) -> None:
    """Scene 3: kazuba list-presets (~7s)."""
    c.type_command("kazuba list-presets")
    c.pause(0.6)
    c.output_line("  enterprise: core, hooks-essential, hooks-quality, hooks-routing, "
                  "skills-meta, skills-planning, skills-dev, skills-research, agents-dev, "
                  "commands-dev, commands-prp, config-hypervisor, contexts, team-orchestrator",
                  delay=0.08)
    c.output_line("  minimal: core", delay=0.08)
    c.output_line("  professional: core, hooks-essential, hooks-quality, hooks-routing, "
                  "skills-meta, skills-planning, skills-dev, agents-dev, commands-dev, contexts",
                  delay=0.08)
    c.output_line("  research: core, hooks-essential, skills-meta, skills-planning, "
                  "skills-research, contexts", delay=0.08)
    c.output_line(f"  {BOLD_CYAN}standard: core, hooks-essential, skills-meta, "
                  f"skills-planning, contexts{RESET}", delay=0.08)
    c.pause(3.0)


def scene_dry_run(c: CastBuilder) -> None:
    """Scene 4: kazuba install --preset standard --dry-run (~6s)."""
    c.type_command("kazuba install --preset standard --target . --dry-run")
    c.pause(0.7)
    c.output_line("Would install 5 module(s): core, hooks-essential, skills-meta, "
                  "skills-planning, contexts")
    c.pause(2.0)


def scene_install(c: CastBuilder) -> None:
    """Scene 5: kazuba install --preset standard (~11s)."""
    c.type_command("kazuba install --preset standard --target .")
    c.pause(1.2)

    modules = [
        ("core", 12, 1, 3),
        ("hooks-essential", 4, 2, 1),
        ("skills-meta", 3, 0, 2),
        ("skills-planning", 2, 0, 1),
        ("contexts", 2, 1, 0),
    ]
    for name, copied, merged, rendered in modules:
        c.pause(1.0)
        c.output_line(f"  {BOLD_GREEN}[OK]{RESET} {name}: {copied} copied, "
                      f"{merged} merged, {rendered} rendered")

    c.pause(0.6)
    c.blank_line()
    c.output_line(f"{BOLD_GREEN}All 5 modules installed successfully!{RESET}")
    c.pause(2.5)


def scene_secrets_blocked(c: CastBuilder) -> None:
    """Scene 6: secrets scanner blocks a credential (~10s)."""
    c.type_command(
        "echo '{\"tool\":\"Write\",\"tool_input\":{\"path\":\"config.py\","
        "\"content\":\"AWS_KEY=AKIA...\"}}' | python .claude/hooks/secrets_scanner.py"
    )
    c.pause(0.8)

    c.output_line(f"{BOLD_RED}BLOCKED{RESET} — secrets_scanner hook detected a potential secret",
                  delay=0.10)
    c.output_line(f"  {RED}Pattern:{RESET}  AWS Access Key (AKIA...)", delay=0.10)
    c.output_line(f"  {RED}File:{RESET}     config.py", delay=0.10)
    c.output_line(f"  {RED}Action:{RESET}  Write operation denied (exit code 2)", delay=0.10)
    c.blank_line()
    c.output_line(f"{BOLD_YELLOW}Tip:{RESET} Store secrets in environment variables or a vault, "
                  "not in source files.", delay=0.10)
    c.pause(3.0)


def scene_validate(c: CastBuilder) -> None:
    """Scene 7: kazuba validate (~8s)."""
    c.type_command("kazuba validate .")
    c.pause(1.0)

    checks = [
        ("CLAUDE.md exists", True),
        ("settings.json valid", True),
        ("hooks registered", True),
        ("hook scripts executable", True),
        ("skills directories present", True),
        ("no conflicting modules", True),
    ]
    for label, passed in checks:
        marker = f"{BOLD_GREEN}\u2713{RESET}" if passed else f"{BOLD_RED}\u2717{RESET}"
        c.output_line(f"  {marker} {label}", delay=0.30)

    c.blank_line()
    c.output_line(f"{BOLD_GREEN}Validation passed — 6/6 checks OK{RESET}")
    c.pause(2.5)


def scene_outro(c: CastBuilder) -> None:
    """Final message (~5s)."""
    c.blank_line()
    c.output_line(f"{BOLD_WHITE}Your project is now protected by Kazuba.{RESET}", delay=0.2)
    c.output_line(f"{DIM}Learn more: https://github.com/gabrielgadea/claude-code-kazuba{RESET}",
                  delay=0.2)
    c.pause(3.5)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    cast = CastBuilder()

    scene_pip_install(cast)
    scene_version(cast)
    scene_list_presets(cast)
    scene_dry_run(cast)
    scene_install(cast)
    scene_secrets_blocked(cast)
    scene_validate(cast)
    scene_outro(cast)

    out_path = Path(__file__).resolve().parent / "kazuba-demo.cast"
    out_path.write_text(cast.build(), encoding="utf-8")

    # Summary
    duration = cast.cursor
    num_events = len(cast.events)
    size_kb = out_path.stat().st_size / 1024

    print(f"Generated: {out_path}")
    print(f"  Events:   {num_events}")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Size:     {size_kb:.1f} KB")
    print()
    print("Scenes:")
    print("  1. pip install claude-code-kazuba  (~16s)")
    print("  2. kazuba --version               (~3.5s)")
    print("  3. kazuba list-presets             (~7s)")
    print("  4. kazuba install --dry-run        (~6s)")
    print("  5. kazuba install --preset standard (~11s)")
    print("  6. Secrets scanner blocks AWS_KEY  (~10s)")
    print("  7. kazuba validate .               (~8s)")
    print()
    print("To preview:  asciinema play kazuba-demo.cast")
    print("To convert:  agg kazuba-demo.cast kazuba-demo.gif --cols 120 --rows 30")


if __name__ == "__main__":
    main()
