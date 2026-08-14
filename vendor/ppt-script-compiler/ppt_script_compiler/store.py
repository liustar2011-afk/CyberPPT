from __future__ import annotations

import shutil
from datetime import datetime
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .utils import read_json, read_yaml, slugify, stable_hash, utc_now_iso, write_json, write_yaml


STAGE_ORDER = ["source", "assets", "plan", "copy", "visual", "audit", "export"]
STAGE_FILES = {
    "source": "source/source_blocks.json",
    "assets": "stages/01_information_assets.json",
    "plan": "stages/02_page_plan.json",
    "copy": "stages/03_screen_copy.json",
    "visual": "stages/04_visual_plan.json",
    "audit": "stages/05_audit.json",
    "export": "exports/ppt_script.md",
}


@dataclass
class ProjectStore:
    root: Path

    @property
    def metadata_path(self) -> Path:
        return self.root / "project.json"

    @property
    def profile_path(self) -> Path:
        return self.root / "profile.yaml"

    @classmethod
    def create(cls, workspaces_root: Path, name: str, default_profile: Path) -> "ProjectStore":
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        project_id = f"{slugify(name)}-{stamp}"
        root = workspaces_root / project_id
        root.mkdir(parents=True, exist_ok=False)
        for folder in ["source/original", "source/chunks", "stages/chunks", "logs", "exports", "tmp"]:
            (root / folder).mkdir(parents=True, exist_ok=True)
        shutil.copy2(default_profile, root / "profile.yaml")
        data = {
            "project_id": project_id,
            "name": name.strip() or project_id,
            "created_at": utc_now_iso(),
            "updated_at": utc_now_iso(),
            "source": {},
            "settings": {
                "codex_bin": "",
                "model": "",
                "reasoning_effort": "high",
                "timeout_seconds": 1800,
            },
            "stages": {stage: {"status": "pending", "locked": False} for stage in STAGE_ORDER},
        }
        write_json(root / "project.json", data)
        return cls(root)

    @classmethod
    def open(cls, root: Path) -> "ProjectStore":
        store = cls(root)
        if not store.metadata_path.exists():
            raise FileNotFoundError(f"不是有效项目目录：{root}")
        return store

    def metadata(self) -> dict[str, Any]:
        return read_json(self.metadata_path, {})

    def save_metadata(self, data: dict[str, Any]) -> None:
        data["updated_at"] = utc_now_iso()
        write_json(self.metadata_path, data)

    def profile(self) -> dict[str, Any]:
        return read_yaml(self.profile_path, {}) or {}

    def save_profile(self, data: dict[str, Any]) -> None:
        write_yaml(self.profile_path, data)
        self.invalidate_after("source", include_current=False, reason="profile_changed")

    def stage_path(self, stage: str) -> Path:
        return self.root / STAGE_FILES[stage]

    def stage_data(self, stage: str) -> Any:
        path = self.stage_path(stage)
        if path.suffix.lower() == ".json":
            return read_json(path)
        return path.read_text(encoding="utf-8") if path.exists() else None

    def stage_status(self, stage: str) -> dict[str, Any]:
        return self.metadata().get("stages", {}).get(stage, {"status": "pending", "locked": False})

    def mark_stage(
        self,
        stage: str,
        *,
        status: str,
        input_hash: str | None = None,
        output_hash: str | None = None,
        message: str | None = None,
        manual: bool = False,
    ) -> None:
        data = self.metadata()
        info = data.setdefault("stages", {}).setdefault(stage, {})
        info.update({"status": status, "updated_at": utc_now_iso(), "manual": manual})
        if input_hash is not None:
            info["input_hash"] = input_hash
        if output_hash is not None:
            info["output_hash"] = output_hash
        if message is not None:
            info["message"] = message
        data["stages"][stage] = info
        self.save_metadata(data)

    def set_locked(self, stage: str, locked: bool) -> None:
        data = self.metadata()
        data.setdefault("stages", {}).setdefault(stage, {})["locked"] = bool(locked)
        self.save_metadata(data)

    def invalidate_after(self, stage: str, include_current: bool = False, reason: str = "upstream_changed") -> None:
        if stage not in STAGE_ORDER:
            return
        data = self.metadata()
        start = STAGE_ORDER.index(stage) + (0 if include_current else 1)
        for downstream in STAGE_ORDER[start:]:
            info = data.setdefault("stages", {}).setdefault(downstream, {})
            if info.get("status") != "pending":
                info["status"] = "stale"
                info["locked"] = False
                info["message"] = reason
                info["updated_at"] = utc_now_iso()
        self.save_metadata(data)

    def save_stage_json(self, stage: str, payload: Any, input_hash: str, manual: bool = False) -> Path:
        path = self.stage_path(stage)
        write_json(path, payload)
        output_hash = stable_hash(payload)
        self.mark_stage(stage, status="completed", input_hash=input_hash, output_hash=output_hash, manual=manual)
        self.invalidate_after(stage, include_current=False, reason=f"{stage}_changed")
        return path

    def settings(self) -> dict[str, Any]:
        return self.metadata().get("settings", {})

    def save_settings(self, settings: dict[str, Any]) -> None:
        data = self.metadata()
        data["settings"] = settings
        self.save_metadata(data)

    def set_source(self, source_info: dict[str, Any]) -> None:
        data = self.metadata()
        data["source"] = source_info
        self.save_metadata(data)
        self.mark_stage("source", status="completed", input_hash=source_info.get("sha256"), output_hash=source_info.get("blocks_hash"))
        self.invalidate_after("source", include_current=False, reason="source_changed")

    def ready_for(self, stage: str) -> tuple[bool, str]:
        prerequisites = {
            "assets": ["source"],
            "plan": ["assets"],
            "copy": ["plan"],
            "visual": ["copy"],
            "audit": ["visual"],
            "export": ["plan", "copy", "visual"],
        }
        for prereq in prerequisites.get(stage, []):
            status = self.stage_status(prereq).get("status")
            if status != "completed":
                return False, f"前置阶段“{prereq}”尚未完成"
        return True, ""


def list_projects(workspaces_root: Path) -> list[Path]:
    if not workspaces_root.exists():
        return []
    projects = [p for p in workspaces_root.iterdir() if p.is_dir() and (p / "project.json").exists()]
    return sorted(projects, key=lambda p: p.stat().st_mtime, reverse=True)
