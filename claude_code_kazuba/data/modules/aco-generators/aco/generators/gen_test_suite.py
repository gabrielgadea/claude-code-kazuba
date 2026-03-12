"""N1 Generator: pytest test suite skeleton.

Produces: tests/test_<module>.py with fixtures and parametrize examples
Triad: execute_script + validate_script + rollback_script
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GENERATOR_ID = "gen_test_suite"
GENERATOR_VERSION = "1.0.0"


def execute_script(config: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    """Generate pytest test suite skeleton."""
    module_name = config.get("module_name", "my_module")
    test_dir = target_dir / "tests"
    test_dir.mkdir(parents=True, exist_ok=True)
    test_file = test_dir / f"test_{module_name}.py"
    class_name = module_name.replace("_", " ").title().replace(" ", "")
    content = (
        f'"""Tests for {module_name}."""\n'
        f"from __future__ import annotations\n\n"
        f"import pytest\n\n\n"
        f"@pytest.fixture\n"
        f"def sample_data():\n"
        f'    """Provide sample test data."""\n'
        f'    return {{"key": "value", "count": 42}}\n\n\n'
        f"class Test{class_name}:\n"
        f'    """Test suite for {module_name}."""\n\n'
        f"    def test_placeholder(self, sample_data):\n"
        f'        """Placeholder test."""\n'
        f'        assert sample_data["count"] == 42\n\n'
        f'    @pytest.mark.parametrize("input_val,expected", [("a", True), ("", False)])\n'
        f"    def test_parametrized(self, input_val, expected):\n"
        f'        """Parametrized placeholder."""\n'
        f"        assert bool(input_val) == expected\n"
    )
    test_file.write_text(content)
    logger.info("gen_test_suite: created %s", test_file)
    return {"status": "ok", "files_created": [str(test_file)]}


def validate_script(config: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    """Validate generated test file exists and has valid syntax."""
    module_name = config.get("module_name", "my_module")
    test_file = target_dir / "tests" / f"test_{module_name}.py"
    errors: list[str] = []
    if not test_file.exists():
        errors.append(f"Missing: {test_file}")
    else:
        try:
            compile(test_file.read_text(), str(test_file), "exec")
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
    return {"status": "ok" if not errors else "fail", "errors": errors}


def rollback_script(config: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    """Remove generated test file."""
    module_name = config.get("module_name", "my_module")
    test_file = target_dir / "tests" / f"test_{module_name}.py"
    if test_file.exists():
        test_file.unlink()
        logger.info("gen_test_suite: rolled back %s", test_file)
    return {"status": "rolled_back"}


if __name__ == "__main__":
    import sys

    cfg = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"module_name": "example"}
    print(json.dumps(execute_script(cfg, Path(".")), indent=2))
