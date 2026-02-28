#!/usr/bin/env python3
"""Run all phase validation scripts sequentially."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PHASE_IDS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]


def main() -> int:
    validation_dir = Path(__file__).parent
    failed: list[int] = []

    for phase_id in PHASE_IDS:
        script = validation_dir / f"validate_phase_{phase_id:02d}.py"
        if not script.exists():
            print(f"[SKIP] Phase {phase_id}: validation script not found")
            continue

        spec = importlib.util.spec_from_file_location(f"validate_{phase_id}", script)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        result = mod.main()
        if result != 0:
            failed.append(phase_id)

    print(f"\n============================================================")
    if failed:
        print(f"  FAILED phases: {failed}")
        return 1
    print(f"  ALL PHASES PASSED")
    print(f"============================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
