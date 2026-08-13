"""Strict, machine-readable contract for a fail-closed autonomous run."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ContractError(ValueError):
    """Raised when an autonomous contract cannot safely be honored."""


@dataclass(frozen=True)
class AutonomousContract:
    path: Path
    project: Path
    allowed_sources: tuple[Path, ...]
    denied_prefixes: tuple[Path, ...]
    style_id: int
    production_mode: str
    require_images: bool
    require_prompt_files: bool
    require_image_qa: bool


def _path(value: object, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ContractError(f"{field} must be a non-empty absolute path")
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ContractError(f"{field} must be an absolute path: {value}")
    return path.resolve()


def _bool(payload: dict[str, Any], field: str) -> bool:
    value = payload.get(field)
    if not isinstance(value, bool):
        raise ContractError(f"required.{field} must be boolean")
    return value


def load_contract(path: Path) -> AutonomousContract:
    """Load the intentionally small JSON schema used by ``run-autonomous``."""

    path = path.expanduser().resolve()
    if not path.is_file():
        raise ContractError(f"autonomous contract is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ContractError(f"autonomous contract must be valid JSON: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ContractError("autonomous contract root must be an object")
    if payload.get("schema_version") != 1:
        raise ContractError("schema_version must be 1")
    if payload.get("mode") != "autonomous_lightweight":
        raise ContractError("mode must be autonomous_lightweight")

    project = _path(payload.get("project"), "project")
    source = payload.get("source")
    if not isinstance(source, dict):
        raise ContractError("source must be an object")
    raw_allowed = source.get("allow")
    raw_denied = source.get("deny_prefixes")
    if not isinstance(raw_allowed, list) or not raw_allowed:
        raise ContractError("source.allow must contain at least one source file")
    if not isinstance(raw_denied, list):
        raise ContractError("source.deny_prefixes must be an array")
    allowed = tuple(_path(item, "source.allow") for item in raw_allowed)
    denied = tuple(_path(item, "source.deny_prefixes") for item in raw_denied)
    if len(set(allowed)) != len(allowed):
        raise ContractError("source.allow contains duplicate paths")

    required = payload.get("required")
    if not isinstance(required, dict):
        raise ContractError("required must be an object")
    if _bool(required, "stage01") is not True or _bool(required, "stage02") is not True:
        raise ContractError("autonomous_lightweight requires required.stage01 and required.stage02")
    style_id = required.get("style_id")
    if not isinstance(style_id, int) or not 1 <= style_id <= 10:
        raise ContractError("required.style_id must be an integer from 1 through 10")
    production_mode = required.get("production_mode")
    if production_mode not in {
        "full-image",
        "editable-overlay",
        "editable-overlay-text-reference",
    }:
        raise ContractError("required.production_mode is unsupported")

    return AutonomousContract(
        path=path,
        project=project,
        allowed_sources=allowed,
        denied_prefixes=denied,
        style_id=style_id,
        production_mode=str(production_mode),
        require_images=_bool(required, "images"),
        require_prompt_files=_bool(required, "prompt_files"),
        require_image_qa=_bool(required, "image_qa"),
    )


def validate_source_boundary(contract: AutonomousContract) -> None:
    """Ensure the project uses exactly the registered local source files.

    This prevents accidental extra material from entering a run and rejects any
    authoritative workbench artifact that names a prohibited legacy location.
    It intentionally cannot prove what an external agent saw; it proves the
    project inputs and saved authority chain do not contain that material.
    """

    project = contract.project
    source_root = (project / "source").resolve()
    if not project.is_dir() or not source_root.is_dir():
        raise ContractError(f"project source directory is missing: {source_root}")
    for denied in contract.denied_prefixes:
        if project.is_relative_to(denied):
            raise ContractError(f"denied prefix contains the project: {denied}")
    for source in contract.allowed_sources:
        if not source.is_file() or not source.is_relative_to(source_root):
            raise ContractError(f"allowed source must be a file beneath project/source: {source}")
        if any(source.is_relative_to(denied) for denied in contract.denied_prefixes):
            raise ContractError(f"allowed source is beneath denied prefix: {source}")

    # ``init --lightweight`` retains a placeholder so the otherwise empty
    # source directory is represented in git.  It is not a source document
    # and ``prepare_source_map`` deliberately ignores it as well.
    actual = tuple(
        sorted(
            path.resolve()
            for path in source_root.rglob("*")
            if path.is_file() and path.name != ".gitkeep"
        )
    )
    if set(actual) != set(contract.allowed_sources):
        raise ContractError(
            "project source files do not match the autonomous contract allowlist"
        )

    workbench = project / "workbench"
    if not workbench.is_dir():
        return
    denied_strings = tuple(str(path) for path in contract.denied_prefixes)
    for path in workbench.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl", ".md", ".txt", ".yml", ".yaml"}:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if any(prefix in text for prefix in denied_strings):
            raise ContractError(f"denied source provenance appears in authoritative artifact: {path}")
