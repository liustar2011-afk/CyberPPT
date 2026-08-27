"""Stage 01 declarations that make later image QA precise.

These declarations describe what Stage 02 must preserve.  They deliberately do
not attempt to judge a generated image, rendered SVG, or PPTX geometry.
"""

from __future__ import annotations

import re
from typing import Any, Mapping


CONTAINER_ROLES = frozenset({"module", "table", "shared"})
TABLE_TEXT_ROLES = frozenset({"header", "body", "note"})


def _compact(value: object) -> str:
    return re.sub(r"\s+", "", str(value or "")).strip()


def _strings(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def audit_stage02_readiness(page: Mapping[str, object]) -> list[str]:
    """Validate optional Stage 01 preservation expectations.

    A readiness declaration is a page-plan annotation, never an additional
    source of business facts.  It names only continuous copy and semantic
    containers already justified by the page's approved evidence.
    """

    raw = page.get("stage02_readiness")
    if raw is None:
        return []
    if not isinstance(raw, Mapping):
        return ["stage02_readiness must be an object"]

    issues: list[str] = []
    sentences = _strings(raw.get("continuous_sentence_signals"))
    if len(sentences) != len(set(sentences)):
        issues.append("stage02_readiness.continuous_sentence_signals must not repeat a value")

    containers = raw.get("containers")
    if containers is not None and not isinstance(containers, list):
        issues.append("stage02_readiness.containers must be an array")
        containers = []
    container_ids: set[str] = set()
    for index, container in enumerate(containers or []):
        if not isinstance(container, Mapping):
            issues.append(f"stage02_readiness.containers[{index}] must be an object")
            continue
        container_id = str(container.get("id") or "").strip()
        heading = str(container.get("heading") or "").strip()
        role = str(container.get("role") or "module").strip()
        if not container_id or container_id in container_ids:
            issues.append(f"stage02_readiness.containers[{index}].id must be unique and non-empty")
        container_ids.add(container_id)
        if not heading:
            issues.append(f"stage02_readiness.containers[{index}].heading is required")
        if role not in CONTAINER_ROLES:
            issues.append(
                f"stage02_readiness.containers[{index}].role must be one of: module, table, shared"
            )

    tables = raw.get("tables")
    if tables is not None and not isinstance(tables, list):
        issues.append("stage02_readiness.tables must be an array")
        tables = []
    for index, table in enumerate(tables or []):
        if not isinstance(table, Mapping):
            issues.append(f"stage02_readiness.tables[{index}] must be an object")
            continue
        container_id = str(table.get("container_id") or "").strip()
        if not container_id or container_id not in container_ids:
            issues.append(
                f"stage02_readiness.tables[{index}].container_id must reference a declared container"
            )
        header_rows = table.get("header_rows")
        if not isinstance(header_rows, int) or header_rows < 0:
            issues.append(f"stage02_readiness.tables[{index}].header_rows must be a non-negative integer")
        for key, default in (("header_role", "header"), ("body_role", "body"), ("note_role", "note")):
            role = str(table.get(key) or default).strip()
            if role not in TABLE_TEXT_ROLES:
                issues.append(
                    f"stage02_readiness.tables[{index}].{key} must be one of: header, body, note"
                )
    return issues


def audit_authored_stage02_readiness(
    page: Mapping[str, object], slide: Mapping[str, object]
) -> list[str]:
    """Check that declared Stage 01 preservation expectations survive authoring."""

    raw = page.get("stage02_readiness")
    if not isinstance(raw, Mapping):
        return []
    issues = audit_stage02_readiness(page)
    slide_id = str(slide.get("id") or page.get("id") or "?")
    visible_text = _compact(
        " ".join(
            str(slide.get(key) or "")
            for key in ("core_message", "full_copy")
        )
        + " "
        + " ".join(
            str(value or "")
            for module in slide.get("onscreen") or []
            if isinstance(module, Mapping)
            for value in [module.get("heading"), module.get("text"), *(module.get("items") or [])]
        )
    )
    for signal in _strings(raw.get("continuous_sentence_signals")):
        if _compact(signal) not in visible_text:
            issues.append(
                f"{slide_id}: declared continuous sentence signal '{signal}' is absent from final script"
            )

    headings = {
        _compact(module.get("heading"))
        for module in slide.get("onscreen") or []
        if isinstance(module, Mapping) and _compact(module.get("heading"))
    }
    for container in raw.get("containers") or []:
        if not isinstance(container, Mapping):
            continue
        heading = _compact(container.get("heading"))
        if heading and heading not in headings:
            issues.append(
                f"{slide_id}: declared Stage 02 container heading '{container.get('heading')}' is absent from onscreen modules"
            )
    return issues


__all__ = [
    "audit_authored_stage02_readiness",
    "audit_stage02_readiness",
]
