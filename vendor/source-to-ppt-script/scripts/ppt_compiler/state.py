from __future__ import annotations

from pathlib import Path
from typing import Any

from .utils import file_content_hash, now_iso, read_json, sha256_file, stable_hash, write_json

STAGE_ORDER = ["assets", "plan", "copy", "visual", "audit"]
STAGE_FILES = {
    "assets": "stages/01_information_assets.json",
    "plan": "stages/02_page_plan.json",
    "copy": "stages/03_screen_copy.json",
    "visual": "stages/04_visual_plan.json",
    "audit": "stages/05_semantic_audit.json",
}
UPSTREAM = {
    "assets": [],
    "plan": ["assets"],
    "copy": ["assets", "plan"],
    "visual": ["plan", "copy"],
    "audit": ["assets", "plan", "copy", "visual"],
}
STATE_FILE = ".ppt-script-skill-state.json"


def stage_path(project: Path, stage: str) -> Path:
    return project / STAGE_FILES[stage]


def _profile_hash(project: Path) -> str:
    return file_content_hash(project / "config/project.yaml")


def _source_hash(project: Path) -> str:
    return file_content_hash(project / "source/source_blocks.json")


def stage_input_hash(project: Path, stage: str) -> str:
    inputs: dict[str, Any] = {"profile": _profile_hash(project)}
    if stage in {"assets", "audit"}:
        inputs["source"] = _source_hash(project)
    for upstream in UPSTREAM[stage]:
        inputs[upstream] = file_content_hash(stage_path(project, upstream))
    return stable_hash(inputs)


def load_state(project: Path) -> dict[str, Any]:
    return read_json(project / STATE_FILE, {"version": 1, "locks": {}}) or {"version": 1, "locks": {}}


def save_state(project: Path, state: dict[str, Any]) -> None:
    write_json(project / STATE_FILE, state)


def stage_status(project: Path, stage: str) -> dict[str, Any]:
    state = load_state(project)
    path = stage_path(project, stage)
    if not path.exists():
        return {"stage": stage, "status": "missing", "path": str(path)}
    lock = state.get("locks", {}).get(stage)
    if not lock:
        return {"stage": stage, "status": "unlocked", "path": str(path)}
    current_input = stage_input_hash(project, stage)
    current_output = sha256_file(path)
    if lock.get("output_hash") != current_output:
        return {"stage": stage, "status": "dirty", "path": str(path)}
    if lock.get("input_hash") != current_input:
        return {"stage": stage, "status": "stale", "path": str(path)}
    return {"stage": stage, "status": "current", "path": str(path), "locked_at": lock.get("locked_at", "")}


def all_status(project: Path) -> list[dict[str, Any]]:
    return [stage_status(project, stage) for stage in STAGE_ORDER]


def upstream_current(project: Path, stage: str) -> tuple[bool, list[str]]:
    bad = [s for s in UPSTREAM[stage] if stage_status(project, s)["status"] != "current"]
    return not bad, bad


def lock_stage(project: Path, stage: str) -> dict[str, Any]:
    ok, bad = upstream_current(project, stage)
    if not ok:
        raise RuntimeError(f"上游阶段未锁定或已失效：{', '.join(bad)}")
    path = stage_path(project, stage)
    if not path.exists():
        raise FileNotFoundError(path)
    state = load_state(project)
    locks = state.setdefault("locks", {})
    locks[stage] = {
        "input_hash": stage_input_hash(project, stage),
        "output_hash": sha256_file(path),
        "locked_at": now_iso(),
    }
    index = STAGE_ORDER.index(stage)
    for downstream in STAGE_ORDER[index + 1 :]:
        locks.pop(downstream, None)
    save_state(project, state)
    return locks[stage]


def unlock_from(project: Path, stage: str) -> None:
    state = load_state(project)
    locks = state.setdefault("locks", {})
    index = STAGE_ORDER.index(stage)
    for item in STAGE_ORDER[index:]:
        locks.pop(item, None)
    save_state(project, state)
