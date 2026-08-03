from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .state import STAGE_FILES, upstream_current
from .utils import read_json, read_yaml, total_text_chars, write_json


@dataclass
class Finding:
    severity: str
    code: str
    description: str
    recommendation: str
    page_id: str = ""
    asset_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_schema(payload: Any, schema_path: Path) -> list[Finding]:
    schema = read_json(schema_path, {})
    findings: list[Finding] = []
    for error in sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path)):
        loc = "/".join(map(str, error.path)) or "<root>"
        findings.append(Finding("error", "SCHEMA_INVALID", f"{loc}: {error.message}", "按JSON Schema修正结构和字段。"))
    return findings


def validate_assets(payload: dict[str, Any], source_payload: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    source_ids = {b.get("source_id") for b in source_payload.get("blocks", [])}
    assets = payload.get("assets", [])
    asset_ids = [a.get("asset_id") for a in assets]
    for duplicate in sorted({x for x in asset_ids if x and asset_ids.count(x) > 1}):
        findings.append(Finding("error", "DUPLICATE_ASSET_ID", f"信息资产编号重复：{duplicate}", "重新连续编号并同步关联编号。", asset_id=duplicate))
    known_assets = set(asset_ids)
    for asset in assets:
        aid = asset.get("asset_id", "")
        refs = asset.get("source_refs", [])
        invalid_refs = [ref for ref in refs if ref not in source_ids]
        if invalid_refs:
            findings.append(Finding("error", "INVALID_SOURCE_REF", f"{aid}引用不存在的来源编号：{', '.join(invalid_refs)}", "改为source_blocks.json中的有效编号。", asset_id=aid))
        if not refs:
            findings.append(Finding("error", "MISSING_SOURCE_REF", f"{aid}没有来源编号。", "至少关联一个明确来源块。", asset_id=aid))
        if asset.get("must_retain") and asset.get("priority") == "supporting":
            findings.append(Finding("warning", "PRIORITY_CONFLICT", f"{aid}标记为必须保留，但优先级为supporting。", "核对并调整优先级。", asset_id=aid))
        for related in asset.get("related_asset_ids", []):
            if related not in known_assets:
                findings.append(Finding("error", "INVALID_RELATED_ASSET", f"{aid}关联不存在的信息资产：{related}", "删除或改为有效资产编号。", asset_id=aid))
        if len(asset.get("content", "")) > 220:
            findings.append(Finding("warning", "ASSET_TOO_LONG", f"{aid}内容超过220字，可能混入多个语义。", "检查是否需要拆分。", asset_id=aid))
        if asset.get("priority") == "core" and not asset.get("must_retain"):
            findings.append(Finding("info", "CORE_NOT_MUST_RETAIN", f"{aid}为core但must_retain=false。", "核对该核心信息是否允许遗漏。", asset_id=aid))
    if not any(a.get("priority") == "core" for a in assets):
        findings.append(Finding("warning", "NO_CORE_ASSET", "没有core信息资产。", "识别决定汇报主线不可缺失的信息。"))
    return findings


def validate_plan(payload: dict[str, Any], assets_payload: dict[str, Any], profile: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    pages = payload.get("pages", [])
    page_ids = [p.get("page_id") for p in pages]
    valid_asset_ids = {a.get("asset_id") for a in assets_payload.get("assets", [])}
    for duplicate in sorted({x for x in page_ids if x and page_ids.count(x) > 1}):
        findings.append(Finding("error", "DUPLICATE_PAGE_ID", f"页面编号重复：{duplicate}", "页面编号必须唯一。", page_id=duplicate))
    orders = [p.get("order") for p in pages]
    if orders != list(range(1, len(pages) + 1)):
        findings.append(Finding("error", "NONCONTIGUOUS_ORDER", "页面order不是从1开始的连续顺序。", "按实际页面顺序连续编号。"))
    assigned: set[str] = set()
    for page in pages:
        pid = page.get("page_id", "")
        ids = page.get("source_asset_ids", [])
        assigned.update(ids)
        invalid = [aid for aid in ids if aid not in valid_asset_ids]
        if invalid:
            findings.append(Finding("error", "INVALID_ASSET_REF", f"{pid}引用不存在的信息资产：{', '.join(invalid)}", "改为有效asset_id。", page_id=pid))
        if page.get("page_type") == "content" and not ids:
            findings.append(Finding("error", "CONTENT_PAGE_WITHOUT_ASSET", f"{pid}是内容页但没有来源资产。", "分配明确来源资产。", page_id=pid))
        if not page.get("page_mission") or not page.get("core_judgment"):
            findings.append(Finding("error", "PAGE_CONTROL_EMPTY", f"{pid}缺少页面使命或核心判断。", "补齐唯一页面使命和核心判断。", page_id=pid))
        if page.get("split_risk") == "high":
            findings.append(Finding("warning", "HIGH_SPLIT_RISK", f"{pid}被标记为高拆页风险。", "检查是否混入两个领导问题或两种逻辑关系。", page_id=pid))
        if len(page.get("must_include", [])) > 7:
            findings.append(Finding("warning", "TOO_MANY_MUST_INCLUDE", f"{pid}必须包含信息超过7项。", "合并同类项或拆页。", page_id=pid))
        mission = page.get("page_mission", "")
        if re.search(r"为什么|必要性", mission) and re.search(r"如何|路径|方案|实施", mission):
            findings.append(Finding("warning", "MIXED_WHY_HOW", f"{pid}页面使命可能同时包含为什么做与怎么做。", "拆分页面使命。", page_id=pid))
    required = {a["asset_id"] for a in assets_payload.get("assets", []) if a.get("priority") == "core" or a.get("must_retain")}
    missing = required - assigned
    declared = set(payload.get("unassigned_core_asset_ids", []))
    silent = missing - declared
    if silent:
        findings.append(Finding("error", "CORE_ASSET_UNASSIGNED", f"核心信息未进入页面且未声明：{', '.join(sorted(silent))}", "分配到页面或明确列入unassigned_core_asset_ids。"))
    presentation = profile.get("presentation", {})
    mode = presentation.get("page_count_mode", "auto")
    if mode != "auto":
        target = int(presentation.get("target_page_count", 0) or 0)
        if target and len(pages) != target:
            findings.append(Finding("warning", "PAGE_COUNT_MISMATCH", f"配置目标页数为{target}，当前为{len(pages)}。", "核对页面规划。"))
    min_pages = int(presentation.get("min_page_count", 1) or 1)
    max_pages = int(presentation.get("max_page_count", 80) or 80)
    if not min_pages <= len(pages) <= max_pages:
        findings.append(Finding("warning", "PAGE_COUNT_OUT_OF_RANGE", f"当前{len(pages)}页，不在配置范围{min_pages}-{max_pages}。", "核对拆页与合页。"))
    return findings


def validate_copy(payload: dict[str, Any], plan_payload: dict[str, Any], profile: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    plan_map = {p["page_id"]: p for p in plan_payload.get("pages", [])}
    copy_pages = payload.get("pages", [])
    copy_map = {p.get("page_id"): p for p in copy_pages}
    if set(copy_map) != set(plan_map):
        findings.append(Finding("error", "PAGE_SET_MISMATCH", "上屏文字页集合与页面规划不一致。", "保持page_id一一对应，不增删页面。"))
    rules = profile.get("content", {})
    max_title = int(rules.get("max_title_chars", 26))
    max_line = int(rules.get("max_body_line_chars", 36))
    max_lines = int(rules.get("max_body_lines_per_page", 12))
    max_modules = int(rules.get("max_modules_per_page", 6))
    max_total = int(rules.get("max_total_chars_per_page", 260))
    prohibited = rules.get("prohibited_phrases", ["不是……而是……"])
    titles: list[str] = []
    for pid, page in copy_map.items():
        plan = plan_map.get(pid, {})
        allowed = set(plan.get("source_asset_ids", []))
        titles.append(page.get("title", ""))
        if len(page.get("title", "")) > max_title:
            findings.append(Finding("warning", "TITLE_TOO_LONG", f"{pid}标题超过{max_title}字。", "压缩为判断式短句。", page_id=pid))
        if set(page.get("source_asset_ids", [])) != allowed:
            findings.append(Finding("error", "COPY_SOURCE_SCOPE_CHANGED", f"{pid}上屏文字source_asset_ids与页面规划不一致。", "恢复为本页规划资产集合。", page_id=pid))
        modules = page.get("modules", [])
        if len(modules) > max_modules:
            findings.append(Finding("warning", "TOO_MANY_MODULES", f"{pid}模块数超过{max_modules}。", "合并同类模块或拆页。", page_id=pid))
        body_lines = [line for m in modules for line in m.get("body_lines", [])]
        if len(body_lines) > max_lines:
            findings.append(Finding("warning", "TOO_MANY_BODY_LINES", f"{pid}正文行数超过{max_lines}。", "压缩或拆页。", page_id=pid))
        for module in modules:
            invalid = [aid for aid in module.get("asset_ids", []) if aid not in allowed]
            if invalid:
                findings.append(Finding("error", "MODULE_ASSET_OUT_OF_SCOPE", f"{pid}模块引用其他页面资产：{', '.join(invalid)}", "只引用本页规划资产。", page_id=pid))
            for line in module.get("body_lines", []):
                if len(line) > max_line:
                    findings.append(Finding("warning", "BODY_LINE_TOO_LONG", f"{pid}正文单行超过{max_line}字：{line[:28]}…", "短句化。", page_id=pid))
        if total_text_chars({"title": page.get("title"), "subtitle": page.get("subtitle"), "modules": modules, "conclusion": page.get("conclusion")}) > max_total:
            findings.append(Finding("warning", "PAGE_COPY_TOO_DENSE", f"{pid}上屏文字总量超过{max_total}字。", "保留主张、证据和结论，压缩解释性文字。", page_id=pid))
        full_text = "\n".join([page.get("title", ""), page.get("subtitle", ""), page.get("conclusion", "")] + body_lines)
        for phrase in prohibited:
            normalized = phrase.replace("……", ".*").replace("…", ".*")
            try:
                hit = re.search(normalized, full_text)
            except re.error:
                hit = phrase in full_text
            if hit:
                findings.append(Finding("error", "PROHIBITED_PHRASE", f"{pid}出现禁用句式：{phrase}", "改为直接判断或正向陈述。", page_id=pid))
    duplicates = {t for t in titles if t and titles.count(t) > 1}
    for title in duplicates:
        findings.append(Finding("warning", "DUPLICATE_TITLE", f"标题重复：{title}", "核对页面使命是否重复。"))
    return findings


def validate_visual(payload: dict[str, Any], copy_payload: dict[str, Any], profile: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    copy_ids = {p.get("page_id") for p in copy_payload.get("pages", [])}
    visual_pages = payload.get("pages", [])
    visual_ids = {p.get("page_id") for p in visual_pages}
    if copy_ids != visual_ids:
        findings.append(Finding("error", "PAGE_SET_MISMATCH", "视觉规划页集合与上屏文字不一致。", "保持page_id一一对应。"))
    expected_ratio = profile.get("visual", {}).get("aspect_ratio", "16:9")
    for page in visual_pages:
        pid = page.get("page_id", "")
        prompt = page.get("generation_prompt", "")
        if page.get("title_rendering") != "ppt_text_layer":
            findings.append(Finding("error", "TITLE_RENDERING_WRONG", f"{pid}标题渲染方式不是ppt_text_layer。", "标题和副标题由PPT文字层处理。", page_id=pid))
        if page.get("aspect_ratio") != expected_ratio:
            findings.append(Finding("warning", "ASPECT_RATIO_MISMATCH", f"{pid}画面比例与配置不一致。", f"使用{expected_ratio}。", page_id=pid))
        if len(page.get("layout_regions", [])) > 7:
            findings.append(Finding("warning", "TOO_MANY_REGIONS", f"{pid}布局区域超过7个。", "减少碎片化区域，强化单一视觉中心。", page_id=pid))
        if not page.get("dominant_carrier") or not page.get("visual_thesis"):
            findings.append(Finding("error", "MISSING_VISUAL_CORE", f"{pid}缺少视觉主张或主视觉载体。", "明确单一主视觉结构。", page_id=pid))
        prompt_for_positive_check = re.sub(r"(?:不|禁止|不要)(?:在图中)?绘制(?:标题|副标题|标题、副标题|标题和副标题)", "", prompt)
        if re.search(r"(?:要求|需要|请|在图中).{0,8}绘制.{0,6}(标题|副标题)|render.{0,8}(title|subtitle)", prompt_for_positive_check, flags=re.I):
            findings.append(Finding("error", "PROMPT_DRAWS_TITLE", f"{pid}生图提示词要求在图中绘制标题。", "删除该要求，并明确不绘制标题、副标题。", page_id=pid))
        required_avoid = ["正面人像", "图标密集", "卡片"]
        combined_avoid = "；".join(page.get("avoid", [])) + prompt
        for term in required_avoid:
            if term not in combined_avoid:
                findings.append(Finding("info", "MISSING_VISUAL_AVOID", f"{pid}未显式约束“{term}”。", "按项目视觉规则补充。", page_id=pid))
    return findings


def validate_audit(payload: dict[str, Any], strict: bool = True) -> list[Finding]:
    findings: list[Finding] = []
    if strict and not payload.get("summary", {}).get("pass", False):
        findings.append(Finding("error", "SEMANTIC_AUDIT_FAILED", "语义审查summary.pass=false。", "修正前序阶段并重新审查。"))
    for item in payload.get("findings", []):
        if strict and item.get("severity") == "error":
            findings.append(Finding("error", "SEMANTIC_ERROR_REMAINS", item.get("description", "仍有语义错误"), item.get("recommendation", "修正后重审"), page_id=item.get("page_id", ""), asset_id=item.get("asset_id", "")))
    return findings


def schema_for(skill_root: Path, stage: str) -> Path:
    names = {
        "assets": "information_assets.schema.json",
        "plan": "page_plan.schema.json",
        "copy": "screen_copy.schema.json",
        "visual": "visual_plan.schema.json",
        "audit": "semantic_audit.schema.json",
    }
    return skill_root / "references/schemas" / names[stage]


def validate_stage(skill_root: Path, project: Path, stage: str, strict_audit: bool = True, check_upstream: bool = True) -> list[Finding]:
    if check_upstream and stage != "assets":
        ok, bad = upstream_current(project, stage)
        if not ok:
            return [Finding("error", "UPSTREAM_NOT_CURRENT", f"上游阶段未锁定或已失效：{', '.join(bad)}", "先修正并锁定上游阶段。")]
    path = project / STAGE_FILES[stage]
    if not path.exists():
        return [Finding("error", "STAGE_FILE_MISSING", f"阶段文件不存在：{path}", "按SKILL.md指定路径创建阶段JSON。")]
    payload = read_json(path, {})
    findings = validate_schema(payload, schema_for(skill_root, stage))
    profile = read_yaml(project / "config/project.yaml", {}) or {}
    if stage == "assets":
        findings += validate_assets(payload, read_json(project / "source/source_blocks.json", {}))
    elif stage == "plan":
        findings += validate_plan(payload, read_json(project / STAGE_FILES["assets"], {}), profile)
    elif stage == "copy":
        findings += validate_copy(payload, read_json(project / STAGE_FILES["plan"], {}), profile)
    elif stage == "visual":
        findings += validate_visual(payload, read_json(project / STAGE_FILES["copy"], {}), profile)
    elif stage == "audit":
        findings += validate_audit(payload, strict=strict_audit)
    report = {
        "stage": stage,
        "pass": not any(f.severity == "error" for f in findings),
        "counts": {severity: sum(f.severity == severity for f in findings) for severity in ["error", "warning", "info"]},
        "findings": [f.to_dict() for f in findings],
    }
    write_json(project / f"reports/local_validation_{stage}.json", report)
    return findings


def validate_all(skill_root: Path, project: Path, strict_audit: bool = True) -> list[Finding]:
    findings: list[Finding] = []
    for stage in ["assets", "plan", "copy", "visual", "audit"]:
        findings.extend(validate_stage(skill_root, project, stage, strict_audit=strict_audit, check_upstream=False))
    write_json(project / "reports/local_validation_all.json", {
        "pass": not any(f.severity == "error" for f in findings),
        "counts": {severity: sum(f.severity == severity for f in findings) for severity in ["error", "warning", "info"]},
        "findings": [f.to_dict() for f in findings],
    })
    return findings
