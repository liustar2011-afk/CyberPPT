"""CyberPPT default visual style library and project visual locks."""

from __future__ import annotations

import json
import re
from hashlib import sha256
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
    library = load_style_library(path)
    if style_id is None and not style_name:
        default_style_id = library.get("default_style_id")
        if not isinstance(default_style_id, int):
            raise ValueError(
                f"style library has no valid default_style_id: {path}"
            )
        style_id = default_style_id
    normalized_name = (style_name or "").strip()
    for style in library["styles"]:
        if style_id is not None and int(style["id"]) == int(style_id):
            return dict(style)
        aliases = {
            str(alias).strip()
            for alias in style.get("aliases", [])
            if str(alias).strip()
        }
        if normalized_name and normalized_name in {str(style["name"]), str(style["slug"]), *aliases}:
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
    if int(style.get("id", -1)) == 9 and style.get("sample"):
        repository_root = path.resolve().parents[3]
        reference_path = (repository_root / str(style["sample"])).resolve()
        if reference_path.is_file():
            payload["reference_image"] = {
                "path": str(reference_path),
                "sha256": sha256(reference_path.read_bytes()).hexdigest().upper(),
                "required_for_every_page": True,
                "role": "style_reference_only",
            }
    lock_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if int(style.get("id", -1)) == 9:
        # Style 09 is authored in references/visual-system.md. Persist the
        # refreshed source section into the lock itself so every downstream
        # consumer and hash sees the current source-of-truth immediately.
        payload = load_style_lock(lock_path)
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
            # style_source points at .../scripts/imagegen_pipeline/style_presets/*.json;
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
        # Markdown permits up to three leading spaces before an ATX heading.
        # Treat an indented following H2 as a real section boundary so Style 09
        # can never absorb Style 10 or any later style section.
        tail_start = start + len(marker)
        next_heading = re.search(r"(?m)^[ \t]{0,3}##[ \t]+", text[tail_start:])
        end = tail_start + next_heading.start() if next_heading else -1
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
