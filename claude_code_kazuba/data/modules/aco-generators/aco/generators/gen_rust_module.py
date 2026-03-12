"""N1 Generator: Rust/PyO3 module skeleton.

Produces: src/lib.rs + Cargo.toml + Python test file
Triad: execute_script + validate_script + rollback_script
"""

from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GENERATOR_ID = "gen_rust_module"
GENERATOR_VERSION = "1.0.0"


def execute_script(config: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    """Generate Rust module skeleton with PyO3 bindings."""
    module_name = config.get("module_name", "my_module")
    target = target_dir / module_name
    target.mkdir(parents=True, exist_ok=True)
    (target / "src").mkdir(exist_ok=True)

    mod_ident = module_name.replace("-", "_")
    cargo_toml = (
        f'[package]\nname = "{module_name}"\nversion = "0.1.0"\nedition = "2021"\n\n'
        f'[lib]\nname = "{mod_ident}"\ncrate-type = ["cdylib"]\n\n'
        f'[dependencies]\npyo3 = {{ version = "0.21", features = ["extension-module"] }}\n'
    )
    (target / "Cargo.toml").write_text(cargo_toml)

    lib_rs = (
        f"use pyo3::prelude::*;\n\n"
        f"#[pyfunction]\n"
        f"fn hello() -> String {{\n"
        f'    "{module_name} v0.1.0".to_string()\n'
        f"}}\n\n"
        f"#[pymodule]\n"
        f"fn {mod_ident}(m: &Bound<'_, PyModule>) -> PyResult<()> {{\n"
        f"    m.add_function(wrap_pyfunction!(hello, m)?)?;\n"
        f"    Ok(())\n"
        f"}}\n"
    )
    (target / "src" / "lib.rs").write_text(lib_rs)

    files_created = [str(target / "Cargo.toml"), str(target / "src" / "lib.rs")]
    logger.info("gen_rust_module: created %d files in %s", len(files_created), target)
    return {"status": "ok", "files_created": files_created, "module_name": module_name}


def validate_script(config: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    """Validate generated Rust module has required files."""
    module_name = config.get("module_name", "my_module")
    target = target_dir / module_name
    errors = [f"Missing: {req}" for req in ("Cargo.toml", "src/lib.rs") if not (target / req).exists()]
    return {"status": "ok" if not errors else "fail", "errors": errors}


def rollback_script(config: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    """Remove generated Rust module directory."""
    module_name = config.get("module_name", "my_module")
    target = target_dir / module_name
    if target.exists():
        shutil.rmtree(target)
        logger.info("gen_rust_module: rolled back %s", target)
    return {"status": "rolled_back"}


if __name__ == "__main__":
    import sys

    cfg = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"module_name": "example_module"}
    print(json.dumps(execute_script(cfg, Path(".")), indent=2))
