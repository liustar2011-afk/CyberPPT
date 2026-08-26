from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .utils import read_json, total_text_chars


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
    schema = read_json(schema_path)
    findings: list[Finding] = []
    for error in sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path)):
        loc = "/".join(map(str, error.path)) or "<root>"
        findings.append(
            Finding(
                severity="error",
                code="SCHEMA_INVALID",
                description=f"{loc}: {error.message}",
                recommendation="按结构化字段要求修正JSON。",
            )
        )
    return findings


def validate_assets(payload: dict[str, Any], source_payload: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    source_ids = {b.get("source_id") for b in source_payload.get("blocks", [])}
    assets = payload.get("assets", [])
    asset_ids = [a.get("asset_id") for a in assets]
    duplicates = {x for x in asset_ids if asset_ids.count(x) > 1}
    for dup in sorted(duplicates):
        findings.append(Finding("error", "DUPLICATE_ASSET_ID", f"信息资产编号重复：{dup}", "重新连续编号并同步关联编号。", asset_id=dup or ""))
    known_assets = set(asset_ids)
    for asset in assets:
        aid = asset.get("asset_id", "")
        refs = asset.get("source_refs", [])
        invalid_refs = [ref for ref in refs if ref not in source_ids]
        if invalid_refs:
            findings.append(Finding("error", "INVALID_SOURCE_REF", f"{aid}引用了不存在的来源编号：{', '.join(invalid_refs)}", "改为source_blocks.json中实际存在的编号。", asset_id=aid))
        if not refs:
            findings.append(Finding("error", "MISSING_SOURCE_REF", f"{aid}没有来源编号。", "至少关联一个明确来源块。", asset_id=aid))
        if asset.get("must_retain") and asset.get("priority") == "supporting":
            findings.append(Finding("warning", "PRIORITY_CONFLICT", f"{aid}标记为必须保留，但优先级为supporting。", "核对其是否应提升为core或important。", asset_id=aid))
        for related in asset.get("related_asset_ids", []):
            if related not in known_assets:
                findings.append(Finding("warning", "INVALID_RELATED_ASSET", f"{aid}关联了不存在的信息资产{related}。", "删除或改为有效资产编号。", asset_id=aid))
        if len(asset.get("content", "")) > 220:
            findings.append(Finding("warning", "ASSET_TOO_LONG", f"{aid}内容较长，可能包含多个独立语义。", "检查是否需要拆分为多个最小完整语义资产。", asset_id=aid))
    if not any(a.get("priority") == "core" for a in assets):
        findings.append(Finding("warning", "NO_CORE_ASSET", "没有标记任何core信息资产。", "识别决定汇报主线不可缺失的信息。"))
    return findings


def validate_plan(payload: dict[str, Any], assets_payload: dict[str, Any], profile: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    pages = payload.get("pages", [])
    page_ids = [p.get("page_id") for p in pages]
    asset_map = {a.get("asset_id"): a for a in assets_payload.get("assets", [])}
    valid_asset_ids = set(asset_map)
    for dup in sorted({x for x in page_ids if page_ids.count(x) > 1}):
        findings.append(Finding("error", "DUPLICATE_PAGE_ID", f"页面编号重复：{dup}", "页面编号必须唯一。", page_id=dup or ""))
    orders = [p.get("order") for p in pages]
    if orders != list(range(1, len(pages) + 1)):
        findings.append(Finding("warning", "NONCONTIGUOUS_ORDER", "页面order不是从1开始的连续顺序。", "按实际页面顺序连续编号。"))
    assigned: set[str] = set()
    for page in pages:
        pid = page.get("page_id", "")
        ids = page.get("source_asset_ids", [])
        assigned.update(ids)
        invalid = [aid for aid in ids if aid not in valid_asset_ids]
        if invalid:
            findings.append(Finding("error", "INVALID_ASSET_REF", f"{pid}引用不存在的信息资产：{', '.join(invalid)}", "改为有效asset_id。", page_id=pid))
        if page.get("page_type") == "content" and not ids:
            findings.append(Finding("error", "CONTENT_PAGE_WITHOUT_ASSET", f"{pid}是内容页但没有来源资产。", "为本页分配明确来源资产。", page_id=pid))
        mission = page.get("page_mission", "")
        judgment = page.get("core_judgment", "")
        if not mission or not judgment:
            findings.append(Finding("error", "PAGE_CONTROL_EMPTY", f"{pid}缺少页面使命或核心判断。", "补齐唯一页面使命和核心判断。", page_id=pid))
        if page.get("split_risk") == "high":
            findings.append(Finding("warning", "HIGH_SPLIT_RISK", f"{pid}被标记为高拆页风险。", "人工检查是否混入两个不同的领导问题或逻辑关系。", page_id=pid))
        if len(page.get("must_include", [])) > 7:
            findings.append(Finding("warning", "TOO_MANY_MUST_INCLUDE", f"{pid}必须包含的信息超过7项，页面可能过载。", "合并同类项或拆页。", page_id=pid))
    required = {a["asset_id"] for a in assets_payload.get("assets", []) if a.get("priority") == "core" or a.get("must_retain")}
    unassigned = required - assigned
    declared_unassigned = set(payload.get("unassigned_core_asset_ids", []))
    silently_missing = unassigned - declared_unassigned
    if silently_missing:
        findings.append(Finding("error", "CORE_ASSET_UNASSIGNED", f"核心信息未进入任何页面且未声明：{', '.join(sorted(silently_missing))}", "将其分配到页面，或在unassigned_core_asset_ids中明确说明。"))
    presentation = profile.get("presentation", {})
    if presentation.get("page_count_mode") != "auto":
        target = int(presentation.get("target_page_count", 0) or 0)
        if target and len(pages) != target:
            findings.append(Finding("warning", "PAGE_COUNT_MISMATCH", f"配置目标页数为{target}，当前为{len(pages)}。", "核对是否需要调整页面规划。"))
    min_pages = int(presentation.get("min_page_count", 0) or 0)
    max_pages = int(presentation.get("max_page_count", 9999) or 9999)
    if len(pages) < min_pages or len(pages) > max_pages:
        findings.append(Finding("warning", "PAGE_COUNT_OUT_OF_RANGE", f"当前页数{len(pages)}超出配置范围{min_pages}—{max_pages}。", "检查叙事完整性和页面纯度。"))
    return findings


def validate_copy(payload: dict[str, Any], plan_payload: dict[str, Any], profile: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    plan_map = {p["page_id"]: p for p in plan_payload.get("pages", [])}
    copy_pages = payload.get("pages", [])
    copy_ids = [p.get("page_id") for p in copy_pages]
    if set(copy_ids) != set(plan_map):
        missing = set(plan_map) - set(copy_ids)
        extra = set(copy_ids) - set(plan_map)
        if missing:
            findings.append(Finding("error", "COPY_PAGE_MISSING", f"缺少页面文案：{', '.join(sorted(missing))}", "补齐与页面规划一一对应的文案。"))
        if extra:
            findings.append(Finding("error", "COPY_PAGE_EXTRA", f"出现页面规划之外的文案：{', '.join(sorted(extra))}", "删除额外页面或先修改页面规划。"))
    rules = profile.get("screen_copy", {})
    max_title = int(rules.get("max_title_chars", 22))
    max_subtitle = int(rules.get("max_subtitle_chars", 45))
    max_modules = int(rules.get("max_module_count", 5))
    max_lines = int(rules.get("max_body_lines_per_module", 4))
    max_total = int(rules.get("max_total_chars_per_content_page", 220))
    forbidden_phrases = ["不是", "而是"]
    for page in copy_pages:
        pid = page.get("page_id", "")
        plan = plan_map.get(pid, {})
        allowed = set(plan.get("source_asset_ids", []))
        used = set(page.get("source_asset_ids", []))
        if not used.issubset(allowed):
            findings.append(Finding("error", "COPY_CROSS_PAGE_ASSET", f"{pid}使用了本页规划之外的资产：{', '.join(sorted(used - allowed))}", "删除跨页借用的信息，或先调整页面规划。", page_id=pid))
        if len(page.get("title", "")) > max_title:
            findings.append(Finding("warning", "TITLE_TOO_LONG", f"{pid}标题超过{max_title}字。", "压缩为表达判断或职能的短句。", page_id=pid))
        if len(page.get("subtitle", "")) > max_subtitle:
            findings.append(Finding("warning", "SUBTITLE_TOO_LONG", f"{pid}副标题超过{max_subtitle}字。", "压缩或留空。", page_id=pid))
        modules = page.get("modules", [])
        if len(modules) > max_modules:
            findings.append(Finding("warning", "TOO_MANY_MODULES", f"{pid}模块数超过{max_modules}。", "合并同类信息或检查是否需要拆页。", page_id=pid))
        for module in modules:
            module_assets = set(module.get("asset_ids", []))
            if not module_assets.issubset(allowed):
                findings.append(Finding("error", "MODULE_ASSET_INVALID", f"{pid}/{module.get('module_id')}引用本页之外的资产。", "仅引用页面规划锁定的资产。", page_id=pid))
            if len(module.get("body_lines", [])) > max_lines:
                findings.append(Finding("warning", "TOO_MANY_BODY_LINES", f"{pid}/{module.get('module_id')}正文行数超过{max_lines}。", "压缩或拆分模块。", page_id=pid))
        total_chars = total_text_chars({k: v for k, v in page.items() if k not in {"content_lock", "source_asset_ids", "page_id"}})
        if plan.get("page_type") == "content" and total_chars > max_total:
            findings.append(Finding("warning", "PAGE_TEXT_OVERLOAD", f"{pid}上屏文字约{total_chars}字，超过配置上限{max_total}。", "压缩重复信息，保留判断、依据和必要限定。", page_id=pid))
        all_text = " ".join([page.get("title", ""), page.get("subtitle", ""), page.get("conclusion", "")] + [line for m in modules for line in m.get("body_lines", [])])
        if "不是" in all_text and "而是" in all_text:
            findings.append(Finding("warning", "FORBIDDEN_PATTERN", f"{pid}出现禁用的“不是……而是……”句式。", "改为直接陈述判断。", page_id=pid))
        if "*" in all_text:
            findings.append(Finding("warning", "ASTERISK_IN_COPY", f"{pid}出现星号。", "删除星号，使用正式标点或结构化短句。", page_id=pid))
    return findings


def validate_visual(payload: dict[str, Any], copy_payload: dict[str, Any], profile: dict[str, Any]) -> list[Finding]:
    findings: list[Finding] = []
    copy_ids = {p["page_id"] for p in copy_payload.get("pages", [])}
    visual_ids = {p.get("page_id") for p in payload.get("pages", [])}
    if copy_ids != visual_ids:
        missing = copy_ids - visual_ids
        extra = visual_ids - copy_ids
        if missing:
            findings.append(Finding("error", "VISUAL_PAGE_MISSING", f"缺少视觉规划：{', '.join(sorted(missing))}", "补齐所有页面视觉规划。"))
        if extra:
            findings.append(Finding("error", "VISUAL_PAGE_EXTRA", f"出现额外视觉页面：{', '.join(sorted(extra))}", "删除页面规划之外的视觉页面。"))
    expected_title_rendering = profile.get("visual_rules", {}).get("title_rendering", "ppt_text_layer")
    for page in payload.get("pages", []):
        pid = page.get("page_id", "")
        if page.get("title_rendering") != expected_title_rendering:
            findings.append(Finding("warning", "TITLE_RENDERING_MISMATCH", f"{pid}标题渲染方式与配置不一致。", f"设置为{expected_title_rendering}。", page_id=pid))
        prompt = page.get("generation_prompt", "")
        risky = [term for term in ["绘制标题", "正面人像", "卡片墙", "图标密集"] if term in prompt and "不" not in prompt[max(0, prompt.find(term)-3):prompt.find(term)]]
        if risky:
            findings.append(Finding("warning", "VISUAL_PROMPT_RISK", f"{pid}生图提示可能包含风险项：{', '.join(risky)}", "明确改为禁用约束。", page_id=pid))
        if len(page.get("layout_regions", [])) >= 5 and all(r.get("relative_size") == "medium" for r in page.get("layout_regions", [])):
            findings.append(Finding("warning", "EQUAL_REGION_WALL", f"{pid}布局区域过多且权重相同，容易退化为卡片墙。", "设置一个dominant主区域，并降低辅助区域权重。", page_id=pid))
    return findings


def run_local_audit(workspace: Path, schemas_dir: Path, profile: dict[str, Any]) -> list[Finding]:
    source = read_json(workspace / "source/source_blocks.json", {})
    assets = read_json(workspace / "stages/01_information_assets.json", {})
    plan = read_json(workspace / "stages/02_page_plan.json", {})
    copy = read_json(workspace / "stages/03_screen_copy.json", {})
    visual = read_json(workspace / "stages/04_visual_plan.json", {})
    findings: list[Finding] = []
    findings.extend(validate_schema(assets, schemas_dir / "assets.schema.json"))
    findings.extend(validate_assets(assets, source))
    findings.extend(validate_schema(plan, schemas_dir / "page_plan.schema.json"))
    findings.extend(validate_plan(plan, assets, profile))
    findings.extend(validate_schema(copy, schemas_dir / "screen_copy.schema.json"))
    findings.extend(validate_copy(copy, plan, profile))
    findings.extend(validate_schema(visual, schemas_dir / "visual_plan.schema.json"))
    findings.extend(validate_visual(visual, copy, profile))
    return findings


def stage_findings(stage: str, workspace: Path, schemas_dir: Path, profile: dict[str, Any]) -> list[Finding]:
    source = read_json(workspace / "source/source_blocks.json", {})
    if stage == "assets":
        payload = read_json(workspace / "stages/01_information_assets.json", {})
        return validate_schema(payload, schemas_dir / "assets.schema.json") + validate_assets(payload, source)
    if stage == "plan":
        assets = read_json(workspace / "stages/01_information_assets.json", {})
        payload = read_json(workspace / "stages/02_page_plan.json", {})
        return validate_schema(payload, schemas_dir / "page_plan.schema.json") + validate_plan(payload, assets, profile)
    if stage == "copy":
        plan = read_json(workspace / "stages/02_page_plan.json", {})
        payload = read_json(workspace / "stages/03_screen_copy.json", {})
        return validate_schema(payload, schemas_dir / "screen_copy.schema.json") + validate_copy(payload, plan, profile)
    if stage == "visual":
        copy = read_json(workspace / "stages/03_screen_copy.json", {})
        payload = read_json(workspace / "stages/04_visual_plan.json", {})
        return validate_schema(payload, schemas_dir / "visual_plan.schema.json") + validate_visual(payload, copy, profile)
    return []
