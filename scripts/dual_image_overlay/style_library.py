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
        if style.get("extension_only"):
            continue
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
            "selected_from_default_8": not bool(style.get("extension_only")),
            "selected_from_extension": bool(style.get("extension_only")),
            "prompt_must_use_style_lock": True,
            "do_not_substitute_external_preset": True,
            "samples_are_required_for_user_confirmation": True,
        },
    }
    lock_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return lock_path


def _strip_style09_registry_meta(section: str) -> str:
    """Keep Style 09 visual rules; drop heading and registry/routing meta."""

    kept: list[str] = []
    for raw in section.splitlines():
        line = raw.strip()
        if not line:
            if kept and kept[-1] != "":
                kept.append("")
            continue
        if line.startswith("## 扩展风格9"):
            continue
        if (
            "不进入默认候选" in line
            or "可通过 ID" in line
            or "默认8种风格仍保持" in line
            or "slug `" in line
            or "slug " in line and "ivory_deep_blue" in line
        ):
            continue
        kept.append(line)
    while kept and kept[0] == "":
        kept.pop(0)
    while kept and kept[-1] == "":
        kept.pop()
    # Collapse runs of blank lines to a single blank.
    compact: list[str] = []
    for line in kept:
        if line == "" and compact and compact[-1] == "":
            continue
        compact.append(line)
    return "\n".join(compact).strip()


def load_style_lock(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    style = payload.get("style")
    if not isinstance(style, dict) or int(style.get("id", -1)) != 9:
        return payload

    # STYLE09 is maintained by the human-readable visual-system reference.
    # Refresh the lock snapshot at read time so edits to that document are not
    # silently ignored by ImageGen handoff compilation.
    style_source = payload.get("style_source")
    source_reference = payload.get("source_reference")
    candidates: list[Path] = []
    if isinstance(source_reference, str) and source_reference.strip():
        reference = Path(source_reference)
        if reference.is_absolute():
            candidates.append(reference)
        elif isinstance(style_source, str) and style_source.strip():
            source_path = Path(style_source)
            # style_source points at .../scripts/dual_image_overlay/style_presets/*.json;
            # the repository root is three parents above that file.
            if len(source_path.parents) > 3:
                candidates.append(source_path.parents[3] / reference)
        candidates.append(Path.cwd() / reference)
    for reference in candidates:
        if not reference.is_file():
            continue
        text = reference.read_text(encoding="utf-8")
        marker = "## 扩展风格9："
        start = text.find(marker)
        if start < 0:
            break
        # Style 09 now contains internal English `##` subsections. End only at
        # the next numbered extension-style heading (e.g. 扩展风格10), not at
        # the first `##` anywhere in the section body.
        end = -1
        search_from = start + len(marker)
        while True:
            next_heading = text.find("\n## ", search_from)
            if next_heading < 0:
                break
            heading_line = text[next_heading + 1 : text.find("\n", next_heading + 1)]
            if heading_line.startswith("## 扩展风格") and not heading_line.startswith(
                "## 扩展风格9"
            ):
                end = next_heading
                break
            search_from = next_heading + 4
        section = text[start:end if end >= 0 else len(text)].strip()
        cleaned = _strip_style09_registry_meta(section)
        if cleaned:
            refreshed = dict(payload)
            refreshed_style = dict(style)
            refreshed_style["prompt_contract"] = cleaned
            refreshed["style"] = refreshed_style
            return refreshed
        break
    return payload
