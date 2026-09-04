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
VISUAL_SYSTEM_PATHS = {
    9: Path(__file__).resolve().parents[2] / "references" / "visual-system.md",
    10: Path(__file__).resolve().parents[2] / "references" / "visual-system-10.md",
}
# Styles 09 and 10 are intentionally read live from their respective
# human-editable visual-system files so a manual style update is immediately
# usable by prompt assembly.
LIVE_CONTRACT_STYLE_IDS = frozenset(VISUAL_SYSTEM_PATHS)
REFERENCE_IMAGE_STYLE_IDS = frozenset({9, 10})
LEGACY_STYLE_ID_ALIASES: dict[int, int] = {}
LEGACY_STYLE_NAME_ALIASES = {
    "light_tech_business_dense": 9,
    "ivory_deep_blue_semantic_scene": 9,
}


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


def _resolved_style(
    style: dict[str, Any],
    source_path: Path = STYLE_LIBRARY_PATH,
) -> dict[str, Any]:
    """Return one style, using its editable visual-system source when available."""

    resolved = dict(style)
    prompt_contract = str(resolved.get("prompt_contract") or "")
    style_id = int(resolved.get("id") or 0)
    visual_system_path = VISUAL_SYSTEM_PATHS.get(style_id)
    if visual_system_path and visual_system_path.is_file():
        live_contract = visual_system_path.read_text(encoding="utf-8-sig").strip()
        if live_contract:
            prompt_contract = live_contract
            resolved["prompt_contract"] = live_contract
            resolved["prompt_contract_source"] = str(visual_system_path)
    if prompt_contract:
        resolved.setdefault("prompt_contract_source", str(source_path))
        resolved["prompt_contract_sha256"] = sha256(
            prompt_contract.encode("utf-8")
        ).hexdigest().upper()
    return resolved


def resolve_default_style(
    *,
    style_id: int | None = None,
    style_name: str | None = None,
    path: Path = STYLE_LIBRARY_PATH,
) -> dict[str, Any]:
    library = load_style_library(path)
    requested_style_id = style_id
    requested_style_name = (style_name or "").strip()

    if style_id in LEGACY_STYLE_ID_ALIASES:
        style_id = LEGACY_STYLE_ID_ALIASES[int(style_id)]
    elif requested_style_name in LEGACY_STYLE_NAME_ALIASES:
        style_id = LEGACY_STYLE_NAME_ALIASES[requested_style_name]
        style_name = None

    if style_id is None and not style_name:
        default_style_id = library.get("default_style_id")
        if not isinstance(default_style_id, int):
            raise ValueError(
                f"style library has no valid default_style_id: {path}"
            )
        style_id = default_style_id

    normalized_name = (style_name or "").strip()
    for style in library["styles"]:
        matched = False
        if style_id is not None and int(style["id"]) == int(style_id):
            matched = True
        else:
            aliases = {
                str(alias).strip()
                for alias in style.get("aliases", [])
                if str(alias).strip()
            }
            if normalized_name and normalized_name in {
                str(style["name"]),
                str(style["slug"]),
                *aliases,
            }:
                matched = True
        if not matched:
            continue
        resolved = _resolved_style(style, path)
        if requested_style_id in LEGACY_STYLE_ID_ALIASES:
            resolved["legacy_alias_from_style_id"] = int(requested_style_id)
        elif requested_style_name in LEGACY_STYLE_NAME_ALIASES:
            resolved["legacy_alias_from_style_name"] = requested_style_name
        return resolved

    raise ValueError(
        f"unknown CyberPPT style selection: id={requested_style_id!r}, name={requested_style_name!r}. "
        "Available styles:\n" + default_style_choices(path)
    )


def _snapshot_metadata(style: dict[str, Any]) -> dict[str, Any]:
    prompt_contract = str(style.get("prompt_contract") or "")
    return {
        "mode": "snapshot",
        "source": str(style.get("prompt_contract_source") or STYLE_LIBRARY_PATH),
        "sha256": (
            sha256(prompt_contract.encode("utf-8")).hexdigest().upper()
            if prompt_contract
            else None
        ),
    }


def write_project_style_lock(
    *,
    project: Path,
    style_id: int | None = None,
    style_name: str | None = None,
    source_script: Path | None = None,
    path: Path = STYLE_LIBRARY_PATH,
) -> Path:
    # Resolve the executable registry exactly once when the lock is created.
    # Production consumers then use the stored snapshot verbatim.
    style = resolve_default_style(style_id=style_id, style_name=style_name, path=path)
    legacy_alias = bool(
        style.get("legacy_alias_from_style_id") is not None
        or style.get("legacy_alias_from_style_name")
    )
    lock_path = project / VISUAL_LOCK_RELATIVE
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "cyberppt.visual_style_lock.v1",
        "created_at": _utc_now(),
        "style_source": str(style.get("prompt_contract_source") or path),
        "source_reference": load_style_library(path).get("source_reference"),
        "source_script": str(source_script) if source_script else None,
        "selection": {
            "requested_style_id": style_id,
            "requested_style_name": style_name,
            "canonical_style_id": int(style.get("id") or -1),
            "legacy_alias": legacy_alias,
        },
        "style": style,
        "resolved_contract": _snapshot_metadata(style),
        "policy": {
            "selected_from_default_8": not bool(style.get("extension_only")),
            "selected_from_extension": bool(style.get("extension_only")),
            "prompt_must_use_style_lock": False,
            "do_not_substitute_external_preset": True,
            "samples_are_required_for_user_confirmation": False,
            "resolved_contract_is_immutable": False,
            "executable_style_authority": str(
                style.get("prompt_contract_source") or STYLE_LIBRARY_PATH
            ),
            "legacy_alias_resolves_to_canonical_snapshot": legacy_alias,
        },
    }
    if int(style.get("id", -1)) in REFERENCE_IMAGE_STYLE_IDS and style.get("sample"):
        repository_root = path.resolve().parents[3]
        reference_path = (repository_root / str(style["sample"])).resolve()
        if reference_path.is_file():
            payload["reference_image"] = {
                "path": str(reference_path),
                "sha256": sha256(reference_path.read_bytes()).hexdigest().upper(),
                "required_for_every_page": True,
                "role": "style_reference_only",
            }
    lock_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return lock_path


def _strip_live_contract_registry_meta(section: str) -> str:
    """Legacy helper: strip registry metadata from a documentation section."""

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
    """Legacy diagnostic helper for reading the documentation section.

    This function is intentionally not used by resolve_default_style(), lock
    creation or lock migration. It remains only for compatibility/debugging.
    """

    if style_id not in LIVE_CONTRACT_STYLE_IDS:
        raise ValueError(
            f"live extension contract is not defined for style {style_id}: {style_id}"
        )
    visual_system_path = VISUAL_SYSTEM_PATHS[style_id]
    if not visual_system_path.is_file():
        raise FileNotFoundError(
            f"Style {style_id:02d} source file is missing: {visual_system_path}"
        )
    text = visual_system_path.read_text(encoding="utf-8-sig")
    marker = f"## 扩展风格{style_id}："
    start = text.find(marker)
    if start < 0:
        if style_id == 10:
            return text.strip()
        raise ValueError(
            f"Style {style_id:02d} section is missing from documentation: {visual_system_path}"
        )
    tail_start = start + len(marker)
    next_heading = re.search(r"(?m)^[ \t]{0,3}##[ \t]+", text[tail_start:])
    end = tail_start + next_heading.start() if next_heading else len(text)
    contract = _strip_live_contract_registry_meta(text[start:end].strip())
    if not contract:
        raise ValueError(
            f"Style {style_id:02d} section is empty in documentation: {VISUAL_SYSTEM_PATH}"
        )
    return contract


def _apply_live_extension_contract(style: dict[str, Any]) -> None:
    """Legacy compatibility helper; never called by production resolution."""

    contract = _load_live_extension_contract(int(style["id"]))
    style["prompt_contract"] = contract
    style["prompt_contract_source"] = str(VISUAL_SYSTEM_PATHS[int(style["id"])])
    style["prompt_contract_sha256"] = sha256(
        contract.encode("utf-8")
    ).hexdigest().upper()


def _is_immutable_snapshot(payload: dict[str, Any]) -> bool:
    resolved = payload.get("resolved_contract")
    policy = payload.get("policy")
    return (
        isinstance(resolved, dict)
        and resolved.get("mode") == "snapshot"
        and isinstance(policy, dict)
        and policy.get("resolved_contract_is_immutable") is True
    )


def _migrate_legacy_live_lock(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Upgrade a pre-snapshot Style 09 lock once, then freeze it.

    Existing immutable snapshots remain untouched for reproducibility. Only
    historical pre-snapshot locks are migrated, and their one-time target is
    now the executable style registry rather than the documentation projection.
    """

    style = payload.get("style")
    if not isinstance(style, dict):
        return payload
    try:
        style_id = int(style.get("id") or -1)
    except (TypeError, ValueError):
        return payload
    if style_id not in LIVE_CONTRACT_STYLE_IDS or _is_immutable_snapshot(payload):
        return payload

    migrated = dict(payload)
    migrated_style = resolve_default_style(style_id=style_id)
    migrated["style"] = migrated_style
    migrated["style_source"] = str(STYLE_LIBRARY_PATH)
    migrated["resolved_contract"] = _snapshot_metadata(migrated_style)
    policy = dict(migrated.get("policy") or {})
    policy["resolved_contract_is_immutable"] = True
    policy["executable_style_authority"] = "style_registry_snapshot"
    migrated["policy"] = policy
    migrated["migration"] = {
        "from": "legacy_live_refresh",
        "to": "style_registry_snapshot",
        "migrated_at": _utc_now(),
    }
    path.write_text(
        json.dumps(migrated, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return migrated


def load_style_lock(path: Path) -> dict[str, Any]:
    """Load a style lock and refresh its editable extension contract."""

    payload = _read_json(path)
    style = payload.get("style")
    if not isinstance(style, dict) or int(style.get("id") or 0) not in LIVE_CONTRACT_STYLE_IDS:
        return payload
    current = resolve_default_style(style_id=int(style["id"]))
    if style == current:
        return payload
    refreshed = dict(payload)
    refreshed["style"] = current
    refreshed["style_source"] = str(current.get("prompt_contract_source") or STYLE_LIBRARY_PATH)
    refreshed["resolved_contract"] = _snapshot_metadata(current)
    path.write_text(
        json.dumps(refreshed, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return refreshed
