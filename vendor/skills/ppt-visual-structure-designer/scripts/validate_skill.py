#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import py_compile
import re
import sys
from pathlib import Path

import yaml

ALLOWED_FRONTMATTER = {"name", "description"}
REQUIRED_REFS = {
    "semantic-model.md",
    "visual-intent-router.md",
    "composition-grammar.md",
    "scene-and-image-integration.md",
    "cec-government-enterprise-profile.md",
    "output-contract.md",
    "quality-gates.md",
    "prompt-assembly.md",
    "examples.md",
    "ppt-script-integration.md",
}
REQUIRED_ASSETS = {
    "default-profile-cec.yaml",
    "visual-intent-registry.yaml",
    "page-visual-spec.schema.json",
    "deck-visual-spec.schema.json",
    "page-visual-spec-template.md",
    "example-page-spec.json",
    "example-deck-spec.json",
    "example-page-script.md",
}


def issue(level: str, code: str, message: str) -> dict[str, str]:
    return {"level": level, "code": code, "message": message}


def validate(skill_dir: Path) -> dict:
    issues: list[dict[str, str]] = []
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        issues.append(issue("error", "missing_skill_md", "SKILL.md not found"))
        return summary(issues)

    content = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not match:
        issues.append(issue("error", "frontmatter", "Invalid YAML frontmatter"))
    else:
        try:
            fm = yaml.safe_load(match.group(1))
        except yaml.YAMLError as exc:
            issues.append(issue("error", "frontmatter_yaml", str(exc)))
            fm = {}
        if not isinstance(fm, dict):
            issues.append(issue("error", "frontmatter_type", "Frontmatter must be a mapping"))
            fm = {}
        unexpected = set(fm) - ALLOWED_FRONTMATTER
        if unexpected:
            issues.append(issue("error", "frontmatter_keys", f"Unexpected frontmatter keys: {sorted(unexpected)}"))
        name = fm.get("name", "")
        desc = fm.get("description", "")
        if not isinstance(name, str) or not re.fullmatch(r"[a-z0-9-]{1,64}", name):
            issues.append(issue("error", "name", "Skill name must be lowercase hyphen-case and <=64 characters"))
        elif name != skill_dir.name:
            issues.append(issue("error", "folder_name", f"Folder name must match skill name: {name}"))
        if not isinstance(desc, str) or not desc.strip():
            issues.append(issue("error", "description", "Description is required"))
        elif len(desc) > 1024 or "<" in desc or ">" in desc:
            issues.append(issue("error", "description_format", "Description must be <=1024 chars and contain no angle brackets"))

    if len(content.splitlines()) > 500:
        issues.append(issue("warning", "skill_length", "SKILL.md exceeds 500 lines; move detail to references"))

    refs = skill_dir / "references"
    missing_refs = sorted(REQUIRED_REFS - {p.name for p in refs.glob("*.md")}) if refs.exists() else sorted(REQUIRED_REFS)
    for name in missing_refs:
        issues.append(issue("error", "missing_reference", name))

    assets = skill_dir / "assets"
    missing_assets = sorted(REQUIRED_ASSETS - {p.name for p in assets.iterdir()}) if assets.exists() else sorted(REQUIRED_ASSETS)
    for name in missing_assets:
        issues.append(issue("error", "missing_asset", name))

    for path in assets.glob("*.json") if assets.exists() else []:
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(issue("error", "json_parse", f"{path.name}: {exc}"))
    for path in assets.glob("*.yaml") if assets.exists() else []:
        try:
            yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            issues.append(issue("error", "yaml_parse", f"{path.name}: {exc}"))

    openai_yaml = skill_dir / "agents" / "openai.yaml"
    if not openai_yaml.exists():
        issues.append(issue("error", "openai_yaml", "agents/openai.yaml not found"))
    else:
        try:
            data = yaml.safe_load(openai_yaml.read_text(encoding="utf-8"))
            interface = data.get("interface", {})
            for key in ("display_name", "short_description", "default_prompt"):
                if not interface.get(key):
                    issues.append(issue("error", "openai_interface", f"Missing interface.{key}"))
            sd = interface.get("short_description", "")
            if not 25 <= len(sd) <= 64:
                issues.append(issue("error", "short_description_length", f"short_description length is {len(sd)}, expected 25-64"))
        except Exception as exc:
            issues.append(issue("error", "openai_yaml_parse", str(exc)))

    scripts = skill_dir / "scripts"
    for path in scripts.glob("*.py") if scripts.exists() else []:
        try:
            py_compile.compile(str(path), doraise=True)
        except Exception as exc:
            issues.append(issue("error", "python_compile", f"{path.name}: {exc}"))

    return summary(issues)


def summary(issues: list[dict[str, str]]) -> dict:
    errors = [x for x in issues if x["level"] == "error"]
    warnings = [x for x in issues if x["level"] == "warning"]
    return {"valid": not errors, "errors": errors, "warnings": warnings, "issue_count": len(issues)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("skill_dir", nargs="?", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--json-report", action="store_true")
    args = ap.parse_args()
    result = validate(Path(args.skill_dir).resolve())
    if args.json_report:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("PASS" if result["valid"] else "FAIL")
        for group in ("errors", "warnings"):
            for item in result[group]:
                print(f"[{item['level'].upper()}] {item['code']}: {item['message']}")
    return 0 if result["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
