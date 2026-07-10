"""CyberPPT default visual style library and project visual locks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STYLE_LIBRARY_PATH = Path(__file__).parent / "style_presets" / "cyberppt_default_styles.json"
VISUAL_LOCK_RELATIVE = Path("workbench/locks/visual_style_lock.json")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return data


def load_style_library(path: Path = STYLE_LIBRARY_PATH) -> dict[str, Any]:
    payload = _read_json(path)
    styles = payload.get("styles")
    if not isinstance(styles, list) or not styles:
        raise ValueError(f"style library must contain non-empty styles: {path}")
    return payload


def default_style_choices(path: Path = STYLE_LIBRARY_PATH) -> str:
    library = load_style_library(path)
    choices: list[str] = []
    for style in library["styles"]:
        choices.append(f"{style['id']}. {style['name']} - {style['scenario']}")
    return "\n".join(choices)


def resolve_default_style(
    *,
    style_id: int | None = None,
    style_name: str | None = None,
    path: Path = STYLE_LIBRARY_PATH,
) -> dict[str, Any]:
    if style_id is None and not style_name:
        raise ValueError(
            "请选择一个 CyberPPT 默认视觉风格后再转换脚本。可用选项：\n"
            + default_style_choices(path)
        )
    library = load_style_library(path)
    normalized_name = (style_name or "").strip()
    for style in library["styles"]:
        if style_id is not None and int(style["id"]) == int(style_id):
            return dict(style)
        if normalized_name and normalized_name in {str(style["name"]), str(style["slug"])}:
            return dict(style)
    raise ValueError(
        f"unknown CyberPPT style selection: id={style_id!r}, name={style_name!r}. "
        "Available styles:\n" + default_style_choices(path)
    )


def write_project_style_lock(
    *,
    project: Path,
    style_id: int | None = None,
    style_name: str | None = None,
    source_script: Path | None = None,
    path: Path = STYLE_LIBRARY_PATH,
) -> Path:
    style = resolve_default_style(style_id=style_id, style_name=style_name, path=path)
    lock_path = project / VISUAL_LOCK_RELATIVE
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "cyberppt.visual_style_lock.v1",
        "created_at": _utc_now(),
        "style_source": str(path),
        "source_reference": load_style_library(path).get("source_reference"),
        "source_script": str(source_script) if source_script else None,
        "style": style,
        "policy": {
            "selected_from_default_8": True,
            "prompt_must_use_style_lock": True,
            "do_not_substitute_external_preset": True,
            "samples_are_required_for_user_confirmation": True,
        },
    }
    lock_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return lock_path


def load_style_lock(path: Path) -> dict[str, Any]:
    return _read_json(path)
