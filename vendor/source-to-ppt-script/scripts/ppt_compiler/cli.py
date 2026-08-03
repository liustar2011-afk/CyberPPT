from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

from .exporters import export_project
from .extractors import initialise_project
from .state import STAGE_ORDER, all_status, lock_stage, stage_status, unlock_from
from .utils import read_json, write_json
from .validators import Finding, schema_for, validate_all, validate_assets, validate_schema, validate_stage


def skill_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_profile(value: str) -> Path:
    root = skill_root()
    aliases = {
        "cec": root / "assets/profiles/cec_leadership.yaml",
        "generic": root / "assets/profiles/generic_executive.yaml",
    }
    path = aliases.get(value, Path(value))
    if not path.is_absolute():
        path = Path.cwd() / path
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在：{path}")
    return path


def print_findings(findings: list[Finding]) -> None:
    counts = {s: sum(f.severity == s for f in findings) for s in ["error", "warning", "info"]}
    print(json.dumps({"pass": counts["error"] == 0, "counts": counts, "findings": [f.to_dict() for f in findings]}, ensure_ascii=False, indent=2))


def command_doctor(_: argparse.Namespace) -> int:
    modules = {"yaml": "PyYAML", "jsonschema": "jsonschema", "docx": "python-docx", "fitz": "PyMuPDF", "pptx": "python-pptx"}
    missing = [package for module, package in modules.items() if importlib.util.find_spec(module) is None]
    result = {"python": sys.version.split()[0], "ok": not missing and sys.version_info >= (3, 10), "missing_packages": missing}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def command_init(args: argparse.Namespace) -> int:
    metadata = initialise_project([Path(x) for x in args.source], Path(args.project), resolve_profile(args.profile), force=args.force)
    print(json.dumps(metadata, ensure_ascii=False, indent=2))
    return 0


def command_status(args: argparse.Namespace) -> int:
    statuses = all_status(Path(args.project))
    print(json.dumps(statuses, ensure_ascii=False, indent=2))
    return 0


def command_validate(args: argparse.Namespace) -> int:
    findings = validate_stage(skill_root(), Path(args.project), args.stage, strict_audit=not args.allow_failed_audit)
    print_findings(findings)
    return 2 if any(f.severity == "error" for f in findings) else 0



def command_validate_all(args: argparse.Namespace) -> int:
    findings = validate_all(skill_root(), Path(args.project), strict_audit=not args.allow_failed_audit)
    print_findings(findings)
    return 2 if any(f.severity == "error" for f in findings) else 0

def command_lock(args: argparse.Namespace) -> int:
    project = Path(args.project)
    findings = validate_stage(skill_root(), project, args.stage, strict_audit=not args.allow_failed_audit)
    if any(f.severity == "error" for f in findings):
        print_findings(findings)
        return 2
    lock = lock_stage(project, args.stage)
    print(json.dumps({"stage": args.stage, "status": "current", "lock": lock}, ensure_ascii=False, indent=2))
    return 0


def command_unlock(args: argparse.Namespace) -> int:
    unlock_from(Path(args.project), args.from_stage)
    print(json.dumps({"unlocked_from": args.from_stage}, ensure_ascii=False))
    return 0


def command_prepare_merge(args: argparse.Namespace) -> int:
    project = Path(args.project)
    chunk_schema = skill_root() / "references/schemas/information_assets_chunk.schema.json"
    source = read_json(project / "source/source_blocks.json", {})
    files = sorted((project / "stages/chunks").glob("assets_chunk_*.json"))
    expected = int(source.get("metadata", {}).get("chunk_count", 0))
    if len(files) != expected:
        print(json.dumps({"pass": False, "error": f"应有{expected}个分块资产文件，当前{len(files)}个。"}, ensure_ascii=False, indent=2))
        return 2
    combined: list[dict] = []
    summaries: list[str] = []
    findings: list[Finding] = []
    for index, path in enumerate(files, start=1):
        payload = read_json(path, {})
        findings += validate_schema(payload, chunk_schema)
        pseudo = {"document": {"title": "", "purpose": "", "audience": "", "central_judgment": "", "narrative_threads": [], "constraints": [], "source_characteristics": []}, "assets": payload.get("assets", [])}
        findings += validate_assets(pseudo, source)
        id_map = {a.get("asset_id"): f"C{index:03d}-{a.get('asset_id')}" for a in payload.get("assets", [])}
        for asset in payload.get("assets", []):
            cloned = dict(asset)
            cloned["asset_id"] = id_map.get(asset.get("asset_id"), asset.get("asset_id"))
            cloned["related_asset_ids"] = [id_map.get(x, x) for x in asset.get("related_asset_ids", [])]
            combined.append(cloned)
        summaries.append(payload.get("chunk_summary", ""))
    if any(f.severity == "error" for f in findings):
        print_findings(findings)
        return 2
    output = project / "stages/chunks/combined_assets.json"
    write_json(output, {"chunk_summaries": summaries, "assets": combined})
    print(json.dumps({"pass": True, "output": str(output), "asset_count": len(combined)}, ensure_ascii=False, indent=2))
    return 0


def command_export(args: argparse.Namespace) -> int:
    project = Path(args.project)
    statuses = all_status(project)
    bad = [x for x in statuses if x["status"] != "current"]
    if bad and not args.force:
        print(json.dumps({"pass": False, "error": "存在未锁定或失效阶段", "stages": bad}, ensure_ascii=False, indent=2))
        return 2
    outputs = export_project(project)
    print(json.dumps({k: str(v) for k, v in outputs.items()}, ensure_ascii=False, indent=2))
    return 0


def command_schema(args: argparse.Namespace) -> int:
    print(schema_for(skill_root(), args.stage).read_text(encoding="utf-8"))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Source-to-PPT Script Skill deterministic helper")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    init = sub.add_parser("init")
    init.add_argument("--project", required=True)
    init.add_argument("--source", action="append", required=True, help="可重复提供多个源文件")
    init.add_argument("--profile", default="cec", help="cec、generic或自定义YAML路径")
    init.add_argument("--force", action="store_true")
    status = sub.add_parser("status")
    status.add_argument("--project", required=True)
    validate = sub.add_parser("validate")
    validate.add_argument("--project", required=True)
    validate.add_argument("--stage", choices=STAGE_ORDER, required=True)
    validate.add_argument("--allow-failed-audit", action="store_true")
    validate_all_parser = sub.add_parser("validate-all")
    validate_all_parser.add_argument("--project", required=True)
    validate_all_parser.add_argument("--allow-failed-audit", action="store_true")
    lock = sub.add_parser("lock")
    lock.add_argument("--project", required=True)
    lock.add_argument("--stage", choices=STAGE_ORDER, required=True)
    lock.add_argument("--allow-failed-audit", action="store_true")
    unlock = sub.add_parser("unlock")
    unlock.add_argument("--project", required=True)
    unlock.add_argument("--from-stage", choices=STAGE_ORDER, required=True)
    merge = sub.add_parser("prepare-assets-merge")
    merge.add_argument("--project", required=True)
    export = sub.add_parser("export")
    export.add_argument("--project", required=True)
    export.add_argument("--force", action="store_true")
    schema = sub.add_parser("schema")
    schema.add_argument("--stage", choices=STAGE_ORDER, required=True)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    commands = {
        "doctor": command_doctor, "init": command_init, "status": command_status,
        "validate": command_validate, "validate-all": command_validate_all, "lock": command_lock, "unlock": command_unlock,
        "prepare-assets-merge": command_prepare_merge, "export": command_export, "schema": command_schema,
    }
    return commands[args.command](args)
