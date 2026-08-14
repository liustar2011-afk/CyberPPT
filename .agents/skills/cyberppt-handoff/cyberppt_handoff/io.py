from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return value


def json_sha256(value: object) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def load_inputs(foundation_dir: Path, semantic_dir: Path, outline_dir: Path) -> dict[str, dict[str, Any]]:
    required = {
        "structure": foundation_dir / "structure.json",
        "fact_base": foundation_dir / "fact-base.json",
        "normalized": semantic_dir / "normalized-facts.json",
        "concepts": semantic_dir / "concept-base.json",
        "relations": semantic_dir / "relation-graph.json",
        "argument": semantic_dir / "argument-chain.json",
        "semantic_report": semantic_dir / "semantic-report.json",
        "deck": outline_dir / "deck-brief.json",
        "page_plan": outline_dir / "page-plan.json",
        "outline_report": outline_dir / "outline-report.json",
    }
    payloads: dict[str, dict[str, Any]] = {}
    for name, path in required.items():
        if not path.is_file():
            raise FileNotFoundError(f"Required handoff input is missing: {path}")
        payloads[name] = read_json(path)
    if payloads["semantic_report"].get("status") != "ok":
        raise ValueError("semantic-report.json must report status: ok")
    if payloads["outline_report"].get("status") != "ok":
        raise ValueError("outline-report.json must report status: ok")
    return payloads
