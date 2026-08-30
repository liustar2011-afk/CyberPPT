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
VISUAL_SYSTEM_PATH = Path(__file__).resolve().parents[2] / "references" / "visual-system.md"
LIVE_CONTRACT_STYLE_IDS = frozenset({9})


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


def _resolved_style(style: dict[str, Any]) -> dict[str, Any]:
    """Resolve a style once when a project lock is created.

    Live extension sources are authoring inputs, not runtime dependencies.  The
    returned payload is therefore a snapshot that must be persisted into the
    visual style lock before production starts.
    """

    resolved = dict(style)
    if int(resolved.get("id") or -1) in LIVE_CONTRACT_STYLE_IDS:
        _apply_live_extension_contract(resolved)
    return resolved


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
            return _resolved_style(style)
        aliases = {
            str(alias).strip()
            for alias in style.get("aliases", [])
            if str(alias).strip()
        }
        if normalized_name and normalized_name in {str(style["name"]), str(style["slug"]), *aliases}:
            return _resolved_style(style)
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
    style_id_value = int(style.get("id", -1))
    resolved_contract_sha256 = str(style.get("prompt_contract_sha256") or "")
    payload = {
        "schema": "cyberppt.visual_style_lock.v1",
        "created_at": _utc_now(),
        "style_source": str(path),
        "source_reference": load_style_library(path).get("source_reference"),
        "source_script": str(source_script) if source_script else None,
        "style": style,
        "resolution": {
            "mode": "frozen_snapshot",
            "style_id": style_id_value,
            "resolved_contract_sha256": resolved_contract_sha256 or None,
            "resolved_contract_source": style.get("prompt_contract_source"),
            "resolved_at": _utc_now(),
        },
        "policy": {
            "selected_from_default_8": not bool(style.get("extension_only")),
            "selected_from_extension": bool(style.get("extension_only")),
            "prompt_must_use_style_lock": True,
            "do_not_substitute_external_preset": True,
            "samples_are_required_for_user_confirmation": True,
            "runtime_contract_refresh_forbidden": True,
        },
    }
    if style_id_value in LIVE_CONTRACT_STYLE_IDS and style.get("sample"):
        repository_root = path.resolve().parents[3]
        reference_path = (repository_root / str(style["sample"])).resolve()
        if reference_path.is_file():
            payload["reference_image"] = {
                "path": str(reference_path),
                "sha256": sha256(reference_path.read_bytes()).hexdigest().upper(),
                "required_for_every_page": True,
                "role": "style_reference_only",
            }
    lock_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")
    return lock_path


def _strip_live_contract_registry_meta(section: str) -> str:
    """Keep model-usable visual rules; drop registry/routing metadata."""

    kept: list[str] = []
    for raw in section.splitlines():
        line = raw.strip()
        if not line:
            if kept and kept[-1] != "":
                kept.append("")
            continue
        if line.startswith("## 扩展风格"):
            continue
        if (
            "不进入默认候选" in line
            or "可通过 ID" in line
            or "默认8种风格仍保持" in line
            or "slug `" in line
            or ("slug " in line and "ivory_deep_blue" in line)
        ):
            continue
        kept.append(line)
    while kept and kept[0] == "":
        kept.pop(0)
    while kept and kept[-1] == "":
        kept.pop()
    compact: list[str] = []
    for line in kept:
        if line == "" and compact and compact[-1] == "":
            continue
        compact.append(line)
    return "\n".join(compact).strip()


def _strip_style09_registry_meta(section: str) -> str:
    """Compatibility wrapper for callers/tests using the previous private name."""

    return _strip_live_contract_registry_meta(section)


def _load_live_extension_contract(style_id: int) -> str:
    """Load a live extension contract only while creating a new lock snapshot."""

    if style_id not in LIVE_CONTRACT_STYLE_IDS:
        raise ValueError(f"live extension contract is not defined for style {style_id}: {style_id}")
    if not VISUAL_SYSTEM_PATH.is_file():
        raise FileNotFoundError(
            f"Style {style_id:02d} source file is missing: {VISUAL_SYSTEM_PATH}"
        )
    text = VISUAL_SYSTEM_PATH.read_text(encoding="utf-8-sig")
    marker = f"## 扩展风格{style_id}："
    start = text.find(marker)
    if start < 0:
        raise ValueError(
            f"Style {style_id:02d} section is missing from canonical source: {VISUAL_SYSTEM_PATH}"
        )
    tail_start = start + len(marker)
    next_heading = re.search(r"(?m)^[ \t]{0,3}##[ \t]+", text[tail_start:])
    end = tail_start + next_heading.start() if next_heading else len(text)
    contract = _strip_live_contract_registry_meta(text[start:end].strip())
    if not contract:
        raise ValueError(
            f"Style {style_id:02d} section is empty in canonical source: {VISUAL_SYSTEM_PATH}"
        )
    return contract


def _apply_live_extension_contract(style: dict[str, Any]) -> None:
    """Resolve the canonical extension source into a lock-ready snapshot."""

    contract = _load_live_extension_contract(int(style["id"]))
    style["prompt_contract"] = contract
    style["prompt_contract_source"] = str(VISUAL_SYSTEM_PATH)
    style["prompt_contract_sha256"] = sha256(contract.encode("utf-8")).hexdigest().upper()


def _validate_frozen_extension_contract(payload: dict[str, Any], path: Path) -> None:
    style = payload.get("style")
    if not isinstance(style, dict):
        return
    style_id = int(style.get("id", -1))
    if style_id not in LIVE_CONTRACT_STYLE_IDS:
        return
    contract = style.get("prompt_contract")
    expected_sha256 = str(style.get("prompt_contract_sha256") or "").upper()
    if not isinstance(contract, str) or not contract.strip() or not expected_sha256:
        raise ValueError(
            f"Style {style_id:02d} lock is a legacy live lock without a frozen resolved contract: {path}. "
            "Regenerate the project visual style lock before production."
        )
    actual_sha256 = sha256(contract.encode("utf-8")).hexdigest().upper()
    if actual_sha256 != expected_sha256:
        raise ValueError(
            f"Style {style_id:02d} frozen contract hash mismatch in {path}: "
            f"expected {expected_sha256}, got {actual_sha256}"
        )
    resolution = payload.get("resolution")
    if isinstance(resolution, dict):
        resolution_sha256 = str(resolution.get("resolved_contract_sha256") or "").upper()
        if resolution_sha256 and resolution_sha256 != actual_sha256:
            raise ValueError(
                f"Style {style_id:02d} resolution hash mismatch in {path}: "
                f"expected {resolution_sha256}, got {actual_sha256}"
            )


def load_style_lock(path: Path) -> dict[str, Any]:
    """Load exactly the style snapshot recorded by the lock.

    Production must never refresh a previously created lock from
    ``references/visual-system.md``.  A Style 09 lock therefore fails closed if
    it predates frozen-contract snapshots or if its embedded contract hash no
    longer matches the stored text.
    """

    payload = _read_json(path)
    _validate_frozen_extension_contract(payload, path)
    return payload
