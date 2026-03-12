"""N1 Generator: FastAPI endpoint skeleton.

Produces: routers/<name>.py with CRUD endpoints + Pydantic models
Triad: execute_script + validate_script + rollback_script
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

GENERATOR_ID = "gen_api_endpoint"
GENERATOR_VERSION = "1.0.0"


def execute_script(config: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    """Generate FastAPI router with CRUD endpoints."""
    resource = config.get("resource_name", "item")
    router_dir = target_dir / "routers"
    router_dir.mkdir(parents=True, exist_ok=True)
    router_file = router_dir / f"{resource}.py"
    class_name = resource.replace("_", " ").title().replace(" ", "")
    content = (
        f'"""Router for {resource} CRUD operations."""\n'
        f"from __future__ import annotations\n\n"
        f"from fastapi import APIRouter, HTTPException\n"
        f"from pydantic import BaseModel\n\n"
        f'router = APIRouter(prefix="/{resource}s", tags=["{resource}s"])\n\n\n'
        f"class {class_name}Create(BaseModel):\n"
        f"    name: str\n\n\n"
        f"class {class_name}Response(BaseModel):\n"
        f"    id: int\n"
        f"    name: str\n\n\n"
        f"@router.get(\"/\", response_model=list[{class_name}Response])\n"
        f"async def list_{resource}s():\n"
        f"    return []\n\n\n"
        f"@router.post(\"/\", response_model={class_name}Response, status_code=201)\n"
        f"async def create_{resource}(payload: {class_name}Create):\n"
        f"    return {class_name}Response(id=1, name=payload.name)\n\n\n"
        f'@router.get("/{{item_id}}", response_model={class_name}Response)\n'
        f"async def get_{resource}(item_id: int):\n"
        f'    raise HTTPException(status_code=404, detail="{class_name} not found")\n\n\n'
        f'@router.delete("/{{item_id}}", status_code=204)\n'
        f"async def delete_{resource}(item_id: int) -> None:\n"
        f"    return None\n"
    )
    router_file.write_text(content)
    logger.info("gen_api_endpoint: created %s", router_file)
    return {"status": "ok", "files_created": [str(router_file)]}


def validate_script(config: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    """Validate generated router file."""
    resource = config.get("resource_name", "item")
    router_file = target_dir / "routers" / f"{resource}.py"
    errors: list[str] = []
    if not router_file.exists():
        errors.append(f"Missing: {router_file}")
    else:
        try:
            compile(router_file.read_text(), str(router_file), "exec")
        except SyntaxError as e:
            errors.append(f"Syntax error: {e}")
    return {"status": "ok" if not errors else "fail", "errors": errors}


def rollback_script(config: dict[str, Any], target_dir: Path) -> dict[str, Any]:
    """Remove generated router file."""
    resource = config.get("resource_name", "item")
    router_file = target_dir / "routers" / f"{resource}.py"
    if router_file.exists():
        router_file.unlink()
        logger.info("gen_api_endpoint: rolled back %s", router_file)
    return {"status": "rolled_back"}


if __name__ == "__main__":
    import sys

    cfg = json.loads(sys.argv[1]) if len(sys.argv) > 1 else {"resource_name": "document"}
    print(json.dumps(execute_script(cfg, Path(".")), indent=2))
