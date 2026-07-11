"""Project-level scaffold and status for analysis-expression gates."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


GATE_ORDER = (
    "source_analysis",
    "reporting_direction",
    "report_structure",
    "page_design",
    "business_script",
)

REQUIRED_HEADINGS = {
    "source_analysis": ("输入盘点", "证据表", "开放数据冲突", "内容脑暴", "页面物料池"),
    "reporting_direction": ("汇报对象", "汇报目的", "内容重点", "证据", "优势", "边界", "推荐方向"),
    "report_structure": (),
    "page_design": (),
    "business_script": ("非上屏：证据链", "来源位置", "非上屏：完整性校核"),
    "drawing_script": (),
}
HEADING_ALIASES = {
    "source_analysis": {
        "证据表": ("MBB 证据表摘要",),
        "开放数据冲突": ("开放数据冲突、缺失证据和 caveat",),
        "内容脑暴": ("内容脑暴：3 条备选故事线",),
    },
    "reporting_direction": {
        "汇报对象": ("适用受众",),
        "证据": ("证据支撑",),
        "边界": ("风险边界",),
        "推荐方向": ("推荐策略",),
    },
    "page_design": {
        "目录": ("目录页",),
        "过渡页": ("章节过渡页",),
        "封底": ("封底页",),
    },
    "business_script": {
        "非上屏：证据链": ("非上屏：证据链与完整性校核",),
        "来源位置": ("非上屏：证据链与完整性校核",),
        "非上屏：完整性校核": ("非上屏：证据链与完整性校核",),
    },
}

_STRUCTURE_PAGE_COUNT_FIELDS = ("页数", "页码", "页面数量")
_STRUCTURE_PAGE_TITLE_FIELDS = ("页面标题", "页标题")
_STRUCTURE_VISUAL_FIELDS = ("视觉形式", "视觉形态", "视觉样式")
_STRUCTURE_MODULE_PATTERN = re.compile(r"^#{3,}\s*[一二三四五六七八九十]+[、.．]\s*.+$", re.MULTILINE)
_NAVIGATION_HEADINGS = ("封面", "目录", "过渡页", "封底")
_NAVIGATION_RESTRICTED_TERMS = ("证据", "决策", "决定", "论证", "论据")
_DRAWING_GEOMETRY_PATTERN = re.compile(
    r"(?:\b[xy]\s*=|\b(?:width|height|left|top)\s*=|\b\d+(?:\.\d+)?px\b|坐标|像素|几何)",
    re.IGNORECASE,
)
_DRAWING_IMPLEMENTATION_PATTERN = re.compile(
    r"(?:#[0-9a-f]{3,8}\b|\brgba?\b|颜色|色值|配色|字体|字号|字重|字族|图标|\bicons?\b|最终构图|最终版|完整页面|页面定稿)",
    re.IGNORECASE,
)
_DRAWING_COMPONENT_PATTERN = re.compile(r"^组件[A-ZＡ-Ｚ一二三四五六七八九十0-9]+(?:[（(].*?[)）])?\s*(?:[—-]+|[:：])", re.MULTILINE)
_CONSULTING_DELIVERY_PATTERN = re.compile(r"\b(?:MBB|SO\s+WHAT|Caveat|Resolution)\b|核心判断", re.IGNORECASE)
_NON_VISIBLE_HEADINGS = ("非上屏", "来源位置")
_DRAWING_PROVENANCE_PATTERN = re.compile(r"(?:\bE\d+\b|证据链|来源位置|源材料\s*P?\d+|完整性校核)")
_EVIDENCE_ID_PATTERN = re.compile(r"(?<![A-Za-z0-9])E[- ]?(\d+)(?![A-Za-z0-9])", re.IGNORECASE)
_COMPLETENESS_CATEGORIES = ("事实", "数字", "分类", "边界", "请求事项")
_NUMBER_PATTERN = re.compile(r"\d+(?:\.\d+)?(?:[%％]|万千瓦|亿千瓦时|万|亿|台|项|个|页|年|月|日)?")
_ALLOWED_CONCISE_FACTS = {"供需总体平衡": "供需平衡"}
_CONTENT_PAGE_PATTERN = re.compile(r"^##\s*第\s*(?P<number>\d+)\s*页(?:[：:]|\s+)(?P<title>.+?)\s*$", re.MULTILINE)
_NON_CONTENT_PAGE_TITLES = ("封面", "目录", "过渡", "封底", "结束", "感谢")
_DIRECTION_HEADING_PATTERN = re.compile(r"^##\s*方向(?P<index>[一二三四1-4])(?:[：:\s]|$).*?$", re.MULTILINE)
_DIRECTION_DETAIL_HEADINGS = ("适用受众", "汇报目的", "内容重点", "优势", "风险边界")


@dataclass(frozen=True)
class AnalysisExpressionStatus:
    adopted: bool
    next_gate: str | None
    gates: dict[str, dict[str, object]]


@dataclass(frozen=True)
class InheritedUnits:
    """Business-script units that a drawing script must carry without mutation."""

    evidence_bindings: tuple[str, ...]
    source_locations: tuple[str, ...]
    completeness_units: tuple[str, ...]
    density_units: tuple[str, ...]

    def to_payload(self) -> dict[str, list[str]]:
        return {
            "evidence_bindings": list(self.evidence_bindings),
            "source_locations": list(self.source_locations),
            "completeness_units": list(self.completeness_units),
            "density_units": list(self.density_units),
        }


def _contract_path(project: Path) -> Path:
    return project.expanduser().resolve() / "workbench" / "analysis_expression" / "contract.json"


def _analysis_root(project: Path) -> Path:
    return _contract_path(project).parent


def _artifact_path(project: Path, gate: str) -> Path:
    return _analysis_root(project) / f"{gate}.md"


def _pending_path(project: Path, gate: str) -> Path:
    return _analysis_root(project) / f"{gate}.pending-confirmation.json"


def _approval_path(project: Path, gate: str) -> Path:
    return _analysis_root(project) / f"{gate}.approved.json"


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def adopt_analysis_expression_contract(project: Path) -> Path:
    contract = _contract_path(project)
    if not contract.exists():
        _write_json(
            contract,
            {
                "schema": "cyberppt.analysis_expression.v1",
                "adopted": True,
                "gates": {},
            },
        )
    return contract


def _validate_gate(gate: str) -> str:
    if gate not in GATE_ORDER:
        allowed = ", ".join(GATE_ORDER)
        raise ValueError(f"unknown analysis-expression gate: {gate}; expected one of {allowed}")
    return gate


def _predecessor(gate: str) -> str | None:
    index = GATE_ORDER.index(gate)
    return GATE_ORDER[index - 1] if index else None


def _approval_exists(project: Path, gate: str) -> bool:
    path = _approval_path(project, gate)
    if not path.exists():
        return False
    try:
        return bool(json.loads(path.read_text(encoding="utf-8")).get("approved"))
    except json.JSONDecodeError:
        return False


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _section_text(text: str, heading: str) -> str:
    match = re.search(rf"^#+\s*{re.escape(heading)}\s*$", text, re.MULTILINE)
    if not match:
        return ""
    following = re.search(r"^#+\s+", text[match.end() :], re.MULTILINE)
    end = match.end() + following.start() if following else len(text)
    return text[match.end() : end]


def _direction_sections(text: str) -> tuple[tuple[str, str], ...]:
    matches = list(_DIRECTION_HEADING_PATTERN.finditer(text))
    sections: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        next_heading = re.search(r"^##\s+", text[match.end() :], re.MULTILINE)
        end = match.end() + next_heading.start() if next_heading else len(text)
        sections.append((match.group("index"), text[match.start() : end]))
    return tuple(sections)


def _has_heading(text: str, heading: str) -> bool:
    return bool(re.search(rf"^#+\s*{re.escape(heading)}\s*$", text, re.MULTILINE))


def _has_required_heading(gate: str, text: str, heading: str) -> bool:
    aliases = HEADING_ALIASES.get(gate, {}).get(heading, ())
    if gate == "report_structure" and heading.startswith("模块"):
        position = "一二三四五六七八九十".index(heading[-1])
        module_headings = _STRUCTURE_MODULE_PATTERN.findall(text)
        return len(module_headings) > position or _has_heading(text, heading)
    if gate == "page_design" and heading == "内容页":
        return bool(re.search(r"^#+\s*内容(?:页|第\s*\d+\s*页)(?:\s*[（(].*[）)])?\s*$", text, re.MULTILINE))
    return any(_has_heading(text, candidate) for candidate in (heading, *aliases))


def _role_section_texts(text: str, role: str) -> list[str]:
    headings = (role, *HEADING_ALIASES.get("page_design", {}).get(role, ()))
    return [section for heading in headings for section in _all_section_texts(text, heading)]


def _all_section_texts(text: str, heading: str) -> list[str]:
    matches = list(re.finditer(rf"^#+\s*{re.escape(heading)}\s*$", text, re.MULTILINE))
    sections: list[str] = []
    for match in matches:
        following = re.search(r"^#+\s+", text[match.end() :], re.MULTILINE)
        end = match.end() + following.start() if following else len(text)
        sections.append(text[match.end() : end])
    return sections


def _section_items(text: str, heading: str) -> tuple[str, ...]:
    items: list[str] = []
    for section in _all_section_texts(text, heading):
        for line in section.splitlines():
            value = re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", line).strip()
            if value:
                items.append(value)
    return tuple(dict.fromkeys(items))


def _visible_text(text: str) -> str:
    visible: list[str] = []
    hidden = False
    for line in text.splitlines():
        heading = re.match(r"^#+\s*(.*?)\s*$", line)
        if heading:
            title = heading.group(1)
            hidden = any(marker in title for marker in _NON_VISIBLE_HEADINGS)
        if not hidden:
            visible.append(line)
    return "\n".join(visible)


def _parse_inherited_units(text: str) -> InheritedUnits:
    combined = _section_items(text, "非上屏：证据链与完整性校核")
    combined_evidence = tuple(item for item in combined if re.match(r"^E\d+", item))
    combined_sources = tuple(item for item in combined if "源材料" in item or re.search(r"\bP\d+", item))
    combined_checks = tuple(
        f"事实：{re.sub(r'^校核[：:]\s*', '', item)}"
        for item in combined
        if item.startswith("校核：") or item.startswith("校核:")
    )
    completeness = _section_items(text, "非上屏：完整性校核") or combined_checks
    return InheritedUnits(
        evidence_bindings=_section_items(text, "非上屏：证据链") or combined_evidence,
        source_locations=_section_items(text, "来源位置") or combined_sources,
        completeness_units=completeness,
        density_units=_section_items(text, "非上屏：信息密度") or _section_items(text, "信息密度"),
    )


def _content_pages(text: str) -> tuple[tuple[int | None, str], ...]:
    matches = list(_CONTENT_PAGE_PATTERN.finditer(text))
    if not matches:
        return ((None, text),)
    pages: list[tuple[int | None, str]] = []
    for index, match in enumerate(matches):
        title = match.group("title")
        if any(marker in title for marker in _NON_CONTENT_PAGE_TITLES) or re.match(r"第[一二三四五六七八九十]+章", title):
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        pages.append((int(match.group("number")), text[match.start() : end]))
    return tuple(pages)


def _page_label(gate: str, page_number: int | None) -> str:
    return gate if page_number in {None, 1} else f"{gate} page {page_number}"


def _required_completeness_categories(units: InheritedUnits) -> set[str]:
    categories: set[str] = set()
    for unit in units.completeness_units:
        match = re.match(r"^([^：:]+)[：:]\s*.+$", unit)
        if match:
            categories.add(match.group(1).strip())
    return categories


def _completeness_values(units: InheritedUnits, category: str) -> tuple[str, ...]:
    prefix = re.compile(rf"^{re.escape(category)}[：:]\s*(.+)$")
    values: list[str] = []
    for unit in units.completeness_units:
        match = prefix.match(unit)
        if match:
            values.append(match.group(1).strip())
    return tuple(dict.fromkeys(values))


def _normalized_visible_value(value: str) -> str:
    return re.sub(r"\s+|[，。、“”‘’：:；;、,.!?！？]", "", value)


def _evidence_ids(text: str) -> set[str]:
    return {f"E{int(value):02d}" for value in _EVIDENCE_ID_PATTERN.findall(text)}


def _visible_text_units(text: str) -> tuple[str, ...]:
    return tuple(
        value
        for line in text.splitlines()
        if (value := re.sub(r"^\s*(?:[-*+]\s+|\d+[.)]\s+)", "", line).strip())
    )


def _fact_is_visible(fact: str, visible_text: str) -> bool:
    normalized_fact = _normalized_visible_value(fact)
    normalized_visible = _normalized_visible_value(visible_text)
    if normalized_fact in normalized_visible:
        return True
    concise_fact = _ALLOWED_CONCISE_FACTS.get(normalized_fact)
    return concise_fact is not None and any(
        concise_fact == _normalized_visible_value(unit) for unit in _visible_text_units(visible_text)
    )


def _drawing_visible_text(text: str) -> str:
    sections = _all_section_texts(text, "上屏文字")
    return "\n".join(sections) if sections else text


def _validate_business_units(
    units: InheritedUnits, *, label: str, require_categories: bool = True, require_density: bool = True
) -> list[str]:
    errors: list[str] = []
    if not units.evidence_bindings:
        errors.append(f"{label} requires at least one evidence binding")
    if not units.source_locations:
        errors.append(f"{label} requires at least one source location")
    if not units.completeness_units:
        errors.append(f"{label} requires at least one completeness unit")
    missing_categories = set(_COMPLETENESS_CATEGORIES) - _required_completeness_categories(units)
    if require_categories and missing_categories:
        errors.append(f"{label} completeness check is missing categories: " + ", ".join(sorted(missing_categories)))
    if require_density and not units.density_units:
        errors.append(f"{label} requires at least one high-density unit")
    return errors


def validate_business_script(text: str) -> list[str]:
    """Validate formal visible language and required non-visible business units."""

    errors: list[str] = []
    if _CONSULTING_DELIVERY_PATTERN.search(_visible_text(text)):
        errors.append("business_script must not contain consulting-delivery language in visible text")

    for page_number, page_text in _content_pages(text):
        errors.extend(
            _validate_business_units(
                _parse_inherited_units(page_text),
                label=_page_label("business_script", page_number),
                require_categories=False,
                require_density=False,
            )
        )
    return errors


def validate_business_evidence_references(text: str, source_analysis: str) -> list[str]:
    """Require business pages to cite the frozen source-analysis evidence registry."""

    registered = _evidence_ids(source_analysis)
    if not registered:
        return ["source_analysis does not contain a usable evidence table"]
    referenced = _evidence_ids(text)
    unknown = sorted(referenced - registered)
    return ["business_script references unknown evidence IDs: " + ", ".join(unknown)] if unknown else []


def validate_drawing_script(text: str, business: str) -> list[str]:
    """Validate that a drawing script is a non-geometric translation of business truth."""

    errors: list[str] = []
    if _DRAWING_GEOMETRY_PATTERN.search(text):
        errors.append("drawing_script must not contain geometry keywords")
    if _DRAWING_IMPLEMENTATION_PATTERN.search(text):
        errors.append("drawing_script must not contain implementation directives")
    if _DRAWING_PROVENANCE_PATTERN.search(text):
        errors.append("drawing_script must not contain evidence or source text")

    drawing_pages = dict(_content_pages(text))
    for page_number, business_page in _content_pages(business):
        label = _page_label("drawing_script", page_number)
        error_prefix = "" if page_number in {None, 1} else f"{label} "
        drawing_page = drawing_pages.get(page_number)
        if drawing_page is None:
            errors.append(f"{error_prefix}is missing for required business content")
            continue
        if not _DRAWING_COMPONENT_PATTERN.search(drawing_page):
            errors.append(f"{error_prefix}requires at least one component directive")
            continue
        business_units = _parse_inherited_units(business_page)
        business_numbers = set(re.findall(r"\d+(?:\.\d+)?", business_page))
        visible_text = _drawing_visible_text(drawing_page)
        for fact in _completeness_values(business_units, "事实"):
            if re.search(r"不得|不可|不能|必须|不设置|不删除|需保留|均需保留", fact):
                continue
            if not _fact_is_visible(fact, visible_text):
                errors.append(f"{error_prefix}missing required business fact in visible text: {fact}")
        for number in _completeness_values(business_units, "数字"):
            if _normalized_visible_value(number) not in _normalized_visible_value(visible_text):
                errors.append(f"{error_prefix}missing required business number in visible text: {number}")

        drawing_numbers = set(re.findall(r"\d+(?:\.\d+)?", visible_text))
        added_numbers = sorted(drawing_numbers - business_numbers)
        if added_numbers:
            errors.append(f"{error_prefix}changes required numbers: " + ", ".join(added_numbers))
    return errors


def validate_analysis_artifact(gate: str, text: str) -> list[str]:
    """Return semantic validation failures for one ordered analysis artifact."""

    _validate_gate(gate)
    errors = [
        f"missing required heading: {heading}"
        for heading in REQUIRED_HEADINGS[gate]
        if not _has_required_heading(gate, text, heading)
    ]

    if gate == "report_structure":
        canonical_modules = re.findall(r"^#+\s*模块[一二三四五六七八九十0-9]+\s*$", text, re.MULTILINE)
        module_count = max(len(canonical_modules), len(_STRUCTURE_MODULE_PATTERN.findall(text)))
        if not 2 <= module_count <= 8:
            errors.append("report_structure module count must be between 2 and 8")
        if any(re.search(rf"^\s*{re.escape(field)}\s*[:：]\s*\S", text, re.MULTILINE) for field in _STRUCTURE_PAGE_COUNT_FIELDS):
            errors.append("report_structure must not contain page count fields")
        if any(re.search(rf"^\s*{re.escape(field)}\s*[:：]\s*\S", text, re.MULTILINE) for field in _STRUCTURE_PAGE_TITLE_FIELDS):
            errors.append("report_structure must not contain page title fields")
        if any(re.search(rf"^\s*{re.escape(field)}\s*[:：]\s*\S", text, re.MULTILINE) for field in _STRUCTURE_VISUAL_FIELDS):
            errors.append("report_structure must not contain visual form fields")

    if gate == "reporting_direction":
        direction_sections = _direction_sections(text)
        if len(direction_sections) < 4:
            errors.append("reporting_direction requires four expanded direction sections")
        for index, section in direction_sections:
            missing = [heading for heading in _DIRECTION_DETAIL_HEADINGS if not _has_heading(section, heading)]
            if missing:
                errors.append(
                    f"reporting_direction direction {index} is missing detail headings: " + ", ".join(missing)
                )

    if gate == "source_analysis" and not _evidence_ids(text):
        errors.append("source_analysis requires at least one evidence ID")

    if gate == "drawing_script" and _DRAWING_GEOMETRY_PATTERN.search(text):
        errors.append("drawing_script must not contain geometry keywords")
    if gate == "drawing_script" and _DRAWING_IMPLEMENTATION_PATTERN.search(text):
        errors.append("drawing_script must not contain implementation directives")

    if gate == "business_script":
        errors.extend(validate_business_script(text))

    return errors


def _normalize_options(options: list[dict[str, Any]], *, require_labels: bool = False) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for option in options:
        if not isinstance(option, dict) or not isinstance(option.get("id"), str) or not option["id"].strip():
            raise ValueError("each confirmation option requires a non-empty id")
        if require_labels and (not isinstance(option.get("label"), str) or not option["label"].strip()):
            raise ValueError("each reporting_direction option requires a non-empty label")
        normalized.append(dict(option))
    return normalized


def _invalidate_successor_records(project: Path, gate: str) -> None:
    for successor in GATE_ORDER[GATE_ORDER.index(gate) + 1 :]:
        for path in (_pending_path(project, successor), _approval_path(project, successor)):
            if path.exists():
                path.unlink()


def stage_analysis_artifact(
    project: Path,
    gate: str,
    source: str,
    recommendation: str,
    options: list[dict[str, Any]],
    question: str | None = None,
    *,
    generation_run: Path | None = None,
) -> Path:
    """Save a validated artifact and its pending, user-selectable confirmation record."""

    gate = _validate_gate(gate)
    root = project.expanduser().resolve()
    predecessor = _predecessor(gate)
    if predecessor and not _approval_exists(root, predecessor):
        raise ValueError(f"{predecessor} approval is required before staging {gate}")

    errors = validate_analysis_artifact(gate, source)
    business_source_sha256: str | None = None
    inherited_units: InheritedUnits | None = None
    source_analysis_sha256: str | None = None
    if gate == "business_script":
        source_analysis_approval = json.loads(_approval_path(root, "source_analysis").read_text(encoding="utf-8"))
        source_analysis_artifact = Path(str(source_analysis_approval["artifact"]))
        source_analysis = source_analysis_artifact.read_text(encoding="utf-8")
        source_analysis_sha256 = hashlib.sha256(source_analysis.encode("utf-8")).hexdigest()
        if source_analysis_sha256 != source_analysis_approval.get("source_sha256"):
            raise ValueError("approved source_analysis has changed; approve source_analysis again")
        errors.extend(validate_business_evidence_references(source, source_analysis))
    if gate == "drawing_script":
        business_approval = json.loads(_approval_path(root, "business_script").read_text(encoding="utf-8"))
        business_artifact = Path(str(business_approval["artifact"]))
        business = business_artifact.read_text(encoding="utf-8")
        business_source_sha256 = hashlib.sha256(business.encode("utf-8")).hexdigest()
        if business_source_sha256 != business_approval.get("source_sha256"):
            raise ValueError("approved business script has changed; approve business_script again")
        errors.extend(validate_drawing_script(source, business))
        inherited_units = _parse_inherited_units(business)
    generation_run_payload: dict[str, Any] | None = None
    if generation_run is not None:
        generation_run = generation_run.expanduser().resolve()
        if not generation_run.is_file():
            raise ValueError(f"generation run is missing: {generation_run}")
        generation_run_payload = json.loads(generation_run.read_text(encoding="utf-8"))
        if generation_run_payload.get("gate") != gate:
            raise ValueError("generation run gate does not match staged gate")
        if generation_run_payload.get("status") != "candidate_ready":
            raise ValueError("generation run is not candidate_ready")
        source_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
        if generation_run_payload.get("candidate_sha256") != source_hash:
            raise ValueError("generation run candidate hash does not match staged source")
        for raw_path, expected in dict(generation_run_payload.get("dependency_hashes", {})).items():
            dependency = Path(raw_path).expanduser().resolve()
            if not dependency.is_file() or hashlib.sha256(dependency.read_bytes()).hexdigest() != expected:
                raise ValueError(f"generation run dependency is stale: {dependency}")
        grounding_path = Path(str(generation_run_payload.get("grounding_report_path", ""))).expanduser().resolve()
        if not grounding_path.is_file():
            raise ValueError("generation run grounding report is missing")
        grounding = json.loads(grounding_path.read_text(encoding="utf-8"))
        if grounding.get("blocking"):
            raise ValueError("generation run deterministic grounding failed")
    if errors:
        raise ValueError("; ".join(dict.fromkeys(errors)))

    normalized_options = _normalize_options(options, require_labels=gate == "reporting_direction")
    if gate == "reporting_direction":
        if len(normalized_options) < 4:
            raise ValueError("reporting_direction requires at least four confirmation options")
        option_values = {option["id"] for option in normalized_options} | {option["label"] for option in normalized_options}
        if recommendation not in option_values:
            raise ValueError("reporting_direction recommendation must match an option id or label")

    artifact = _artifact_path(root, gate)
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text(source, encoding="utf-8")
    pending = _pending_path(root, gate)
    pending_payload: dict[str, object] = {
            "schema": "cyberppt.analysis_expression.pending_confirmation.v1",
            "gate": gate,
            "status": "pending_confirmation",
            "artifact": str(artifact),
            "source_sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
            "recommendation": recommendation,
            "question": question or _default_confirmation_question(gate, recommendation),
            "options": normalized_options,
            "created_at": _utc_now(),
    }
    if business_source_sha256 is not None and inherited_units is not None:
        pending_payload["business_source_sha256"] = business_source_sha256
        pending_payload["inherited_units"] = inherited_units.to_payload()
    if source_analysis_sha256 is not None:
        pending_payload["source_analysis_sha256"] = source_analysis_sha256
    if generation_run is not None:
        pending_payload["generation_run"] = str(generation_run)
        pending_payload["generation_run_sha256"] = hashlib.sha256(generation_run.read_bytes()).hexdigest()
    _write_json(pending, pending_payload)
    approval = _approval_path(root, gate)
    if approval.exists():
        approval.unlink()
    _invalidate_successor_records(root, gate)
    return pending


def _default_confirmation_question(gate: str, recommendation: str) -> str:
    if gate == "reporting_direction":
        return f"是否采用{recommendation}汇报方向？"
    return f"是否确认{gate.replace('_', ' ')}？"


def approve_analysis_artifact(project: Path, gate: str, option_id: str, note: str = "") -> Path:
    """Persist the selected option after a staged confirmation record is reviewed."""

    gate = _validate_gate(gate)
    root = project.expanduser().resolve()
    pending = _pending_path(root, gate)
    if not pending.exists():
        raise FileNotFoundError(f"no pending confirmation for {gate}; stage the artifact before approval")
    data = json.loads(pending.read_text(encoding="utf-8"))
    option_ids = {option.get("id") for option in data.get("options", []) if isinstance(option, dict)}
    if option_id not in option_ids:
        raise ValueError(f"option_id is not available for {gate}: {option_id}")

    approval = _approval_path(root, gate)
    approval_payload: dict[str, object] = {
            "schema": "cyberppt.analysis_expression.approval.v1",
            "gate": gate,
            "approved": True,
            "approved_at": _utc_now(),
            "pending_confirmation": str(pending),
            "artifact": data["artifact"],
            "source_sha256": data["source_sha256"],
            "option_id": option_id,
            "note": note,
    }
    if gate == "drawing_script":
        approval_payload["business_source_sha256"] = data["business_source_sha256"]
        approval_payload["inherited_units"] = data["inherited_units"]
    if gate == "business_script":
        approval_payload["source_analysis_sha256"] = data["source_analysis_sha256"]
    _write_json(approval, approval_payload)
    return approval


def _artifact_status(root: Path, gate: str, record: dict[str, object]) -> dict[str, object]:
    failures: list[str] = []
    source_hash_state = "unavailable"
    artifact_value = record.get("artifact")
    source = ""
    if isinstance(artifact_value, str):
        artifact = Path(artifact_value)
        if artifact.exists():
            source = artifact.read_text(encoding="utf-8")
            current_hash = hashlib.sha256(source.encode("utf-8")).hexdigest()
            source_hash_state = "current" if current_hash == record.get("source_sha256") else "stale"
            failures.extend(validate_analysis_artifact(gate, source))
        else:
            failures.append(f"artifact is missing: {artifact}")
    else:
        failures.append("artifact path is missing")

    status: dict[str, object] = {
        "validation_failures": failures,
        "source_hash_state": source_hash_state,
    }
    if gate == "drawing_script":
        business_approval = _approval_path(root, "business_script")
        if not business_approval.exists():
            status["business_dependency_hash_state"] = "unavailable"
        else:
            business_record = json.loads(business_approval.read_text(encoding="utf-8"))
            business_artifact = Path(str(business_record.get("artifact", "")))
            if not business_artifact.exists():
                status["business_dependency_hash_state"] = "unavailable"
            else:
                business = business_artifact.read_text(encoding="utf-8")
                business_hash = hashlib.sha256(business.encode("utf-8")).hexdigest()
                status["business_dependency_hash_state"] = (
                    "current" if business_hash == record.get("business_source_sha256") else "stale"
                )
                if source:
                    failures.extend(validate_drawing_script(source, business))
    if gate == "business_script":
        source_analysis_approval = _approval_path(root, "source_analysis")
        if not source_analysis_approval.exists():
            status["source_analysis_dependency_hash_state"] = "unavailable"
        else:
            source_analysis_record = json.loads(source_analysis_approval.read_text(encoding="utf-8"))
            source_analysis_artifact = Path(str(source_analysis_record.get("artifact", "")))
            if not source_analysis_artifact.exists():
                status["source_analysis_dependency_hash_state"] = "unavailable"
            else:
                source_analysis = source_analysis_artifact.read_text(encoding="utf-8")
                source_analysis_hash = hashlib.sha256(source_analysis.encode("utf-8")).hexdigest()
                status["source_analysis_dependency_hash_state"] = (
                    "current" if source_analysis_hash == record.get("source_analysis_sha256") else "stale"
                )
                if source:
                    failures.extend(validate_business_evidence_references(source, source_analysis))
    return status


def get_analysis_expression_status(project: Path) -> AnalysisExpressionStatus:
    contract = _contract_path(project)
    if not contract.exists():
        return AnalysisExpressionStatus(adopted=False, next_gate=None, gates={})
    root = project.expanduser().resolve()
    next_gate: str | None = None
    gates: dict[str, dict[str, object]] = {}
    for gate in GATE_ORDER:
        approval = _approval_path(root, gate)
        pending = _pending_path(root, gate)
        if _approval_exists(root, gate):
            data = json.loads(approval.read_text(encoding="utf-8"))
            gates[gate] = {
                "status": "approved",
                "approval": str(approval),
                **_artifact_status(root, gate, data),
            }
        elif pending.exists():
            data = json.loads(pending.read_text(encoding="utf-8"))
            gates[gate] = {
                "status": "pending_confirmation",
                "pending_confirmation": str(pending),
                "question": data.get("question"),
                "recommendation": data.get("recommendation"),
                "options": data.get("options", []),
                **_artifact_status(root, gate, data),
            }
        else:
            gates[gate] = {"status": "not_staged", "validation_failures": [], "source_hash_state": "unavailable"}
    for gate in GATE_ORDER:
        gate_status = gates[gate]
        if (
            gate_status.get("status") != "approved"
            or gate_status.get("source_hash_state") != "current"
            or gate_status.get("validation_failures")
            or gate_status.get("source_analysis_dependency_hash_state") == "stale"
        ):
            next_gate = gate
            break
    return AnalysisExpressionStatus(adopted=True, next_gate=next_gate, gates=gates)


def analysis_expression_status_as_json(status: AnalysisExpressionStatus) -> str:
    return json.dumps(
        {
            "adopted": status.adopted,
            "next_gate": status.next_gate,
            "gates": status.gates,
            "next_command": f"stage-{status.next_gate.replace('_', '-')}" if status.next_gate else None,
        },
        ensure_ascii=False,
        indent=2,
    )


def assert_analysis_expression_ready(project: Path) -> None:
    """Reject generation when an adopted project's analysis contract is incomplete or stale."""

    root = project.expanduser().resolve()
    if not _contract_path(root).exists():
        return

    for gate in GATE_ORDER:
        if not _approval_exists(root, gate):
            raise ValueError(f"{gate} approval is required")

    approvals = {
        gate: json.loads(_approval_path(root, gate).read_text(encoding="utf-8"))
        for gate in GATE_ORDER
    }
    artifacts: dict[str, str] = {}
    for gate, approval in approvals.items():
        artifact = Path(str(approval["artifact"]))
        source = artifact.read_text(encoding="utf-8")
        if hashlib.sha256(source.encode("utf-8")).hexdigest() != approval.get("source_sha256"):
            raise ValueError(f"approved {gate} has changed; approve {gate} again")
        artifacts[gate] = source

    business_approval = approvals["business_script"]
    business = artifacts["business_script"]
    source_analysis = artifacts["source_analysis"]
    source_analysis_sha256 = hashlib.sha256(source_analysis.encode("utf-8")).hexdigest()
    if business_approval.get("source_analysis_sha256") != source_analysis_sha256:
        raise ValueError("business_script dependency hash is stale; stage and approve business_script again")
    business_errors = validate_business_evidence_references(business, source_analysis)
    if business_errors:
        raise ValueError("business_script approval is invalid: " + "; ".join(business_errors))
