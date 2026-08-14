#!/usr/bin/env python3
from __future__ import annotations

from copy import deepcopy
import json
import tempfile
from pathlib import Path
from typing import Any

from build_generation_prompt import page_prompt
from validate_visual_spec import validate_json


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "assets" / "domain-neutral-structure-fixtures.json"
BASE_PAGE = ROOT / "assets" / "example-page-spec.json"
EXPECTED_CATEGORIES = {
    "single_judgment_and_evidence",
    "input_transform_output",
    "multi_party_responsibility",
    "layered_dependency",
    "comparison_decision",
    "boundary_and_feedback",
}


def _binding_for(kind: str) -> str:
    if kind in {"judgment", "result"}:
        return "result"
    if kind == "process":
        return "embedded"
    return "label"


def _execution_design(case: dict[str, Any], focus_text: str) -> dict[str, str]:
    """Provide domain-neutral but drawable relation fields for regression cases."""
    relation = str(case["primary_relation"])
    if relation == "transform":
        return {"carrier": "受理—分流—责任办理的服务流转场", "role": "服务诉求经过分流接口和责任动作转化为可追踪结果", "organization": "服务诉求进入受理接口，经分类分流落到责任办理，再把反馈结果接回同一服务流", "integration": "诉求文字贴在入口对象，分流和办理文字贴在对应动作接口，结果文字贴在交付端", "encoding": "入口、分流接口、责任动作和反馈出口按真实承接关系连续出现", "placement": "以连续服务流转场作为内容区主结构，入口和结果附着于其两端"}
    if relation == "evidence":
        return {"carrier": "证据汇聚到研究判断的论证关系场", "role": "量化和质性证据通过各自依据关系共同支撑研究判断", "organization": "样本趋势和访谈发现从不同证据入口汇入方案判断，判断承担唯一焦点", "integration": "证据文字贴在各自证据对象旁，结论文字贴在被证据支撑的判断对象上", "encoding": "两类证据以有标签的支撑关系汇入同一判断，不形成并列卡片", "placement": "以判断对象和两路证据关系构成内容区主结构"}
    if relation == "responsibility":
        return {"carrier": "职责接口汇入共同成果的协同关系场", "role": "决策、执行和监督分别通过职责接口共同交付成果", "organization": "三类责任主体各自连接到所承担的动作接口，并在共同成果处收敛", "integration": "主体文字贴在对应职责接口，成果文字贴在共同交付结果上", "encoding": "用决策、执行、监督三种具名职责关系指向共同成果", "placement": "以职责接口与共同成果构成主关系场，成果为唯一焦点"}
    if relation == "layer":
        return {"carrier": "基础能力向采用结果逐层传递的能力依赖场", "role": "基础能力通过核心服务和用户功能逐层支撑采用结果", "organization": "基础能力嵌入核心服务的支撑面，核心服务承接到用户功能并形成采用结果", "integration": "每层文字贴在其承载能力上，采用结果文字贴在最终形成的结果对象上", "encoding": "用基础支撑、服务支撑和形成采用三类依赖关系连续连接", "placement": "以能力依赖场作为内容区主结构，采用结果承担最高权重"}
    if relation == "compare":
        return {"carrier": "共同评价标准驱动方案取舍的比较关系场", "role": "同一评价标准作用于两个方案并导向当前选择", "organization": "共同评价标准分别进入方案A和方案B的比较接口，取舍结果从比较中形成", "integration": "标准文字贴在比较依据上，方案文字贴在各自被评价对象上，结论文字贴在选择结果上", "encoding": "同一标准以两条评价关系连接两个方案，比较关系再导向选择结果", "placement": "以共同标准、方案比较和选择结果组成一个连续比较关系场"}
    return {"carrier": "授权输入经审查门控形成允许输出并回流校正的控制关系场", "role": "授权边界、审查动作、允许输出和反馈记录共同构成受控闭环", "organization": "授权输入穿过审查门控形成允许输出，反馈记录从输出回接审查动作", "integration": "输入文字贴在授权入口，门控文字贴在审查动作，输出和反馈文字贴在对应结果与回流记录上", "encoding": "授权进入、受控输出、结果记录和反馈校正按方向形成一条控制关系", "placement": "以门控动作和受控输入输出关系构成内容区主结构"}


def _page_from_case(
    base: dict[str, Any],
    case: dict[str, Any],
    *,
    page_number: int,
    style_source_ref: str,
) -> dict[str, Any]:
    page = deepcopy(base)
    evidence = [
        {
            **item,
            "source_ref": f"domain-neutral fixture {case['id']}",
        }
        for item in case["evidence_units"]
    ]
    evidence_by_id = {item["id"]: item for item in evidence}
    evidence_ids = list(evidence_by_id)
    focus_ref = case["focus_ref"]
    focus_text = evidence_by_id[focus_ref]["text"]
    execution = _execution_design(case, focus_text)
    page.update(
        {
            "schema_version": "1.1",
            "page_id": f"P{page_number:02d}",
            "page_number": page_number,
            "page_title": case["page_title"],
            "page_role": case["page_role"],
            "page_mission": case["page_mission"],
            "core_judgment": case["core_judgment"],
            "evidence_units": evidence,
        }
    )
    page["content_lock"] = {
        "mode": "strict",
        "locked_items": [
            {
                "id": "T1",
                "type": "title",
                "text": case["page_title"],
                "source_ref": f"domain-neutral fixture {case['id']}",
            },
            *[
                {
                    "id": f"B{index}",
                    "type": "body",
                    "text": item["text"],
                    "source_ref": f"domain-neutral fixture {case['id']}",
                }
                for index, item in enumerate(evidence, start=1)
            ],
        ],
        "allowed_transformations": ["line_break", "grouping", "position_change"],
        "forbidden_transformations": [
            "change facts",
            "change actors",
            "change relationships",
        ],
    }
    page["semantic_graph"] = {
        "primary_relation": case["primary_relation"],
        "direction": case["direction"],
        "nodes": evidence_ids,
        "edges": deepcopy(case["edges"]),
        "decision_relationship": case["core_judgment"],
    }
    page["structural_decision"] = {
        "semantic_focus": {
            "kind": case["semantic_focus_kind"],
            "ref": focus_ref,
        },
        "spatial_grammar": list(case["spatial_grammar"]),
        "semantic_tags": list(case["semantic_tags"]),
        "primary_refs": list(case["primary_refs"]),
        "secondary_refs": list(case["secondary_refs"]),
        "reading_sequence": list(case["reading_sequence"]),
        "text_bindings": [
            {
                "evidence_id": item["id"],
                "target_ref": item["id"],
                "binding": _binding_for(item["kind"]),
            }
            for item in evidence
        ],
        "representation_freedom": {
            "carrier": "free",
            "medium": "free",
            "reason": "The source fixes semantic relationships but leaves carrier and medium open.",
        },
    }
    page["visual_decision"] = {
        "visual_intent_type": case["visual_intent_type"],
        "visual_thesis": case["core_judgment"],
        "spatial_organization": execution["organization"],
        "reading_path": [evidence_by_id[item]["text"] for item in case["reading_sequence"]],
        "text_integration_method": execution["integration"],
        "relationship_encoding": execution["encoding"],
        "visual_center_count": 1,
        "visual_hierarchy": {
            "primary": focus_text,
            "secondary": [
                evidence_by_id[item]["text"]
                for item in case["primary_refs"]
                if item != focus_ref
            ],
            "tertiary": [evidence_by_id[item]["text"] for item in case["secondary_refs"]],
        },
    }
    page["text_integration"] = {
        "title_render_mode": "external_text_layer",
        "subtitle_render_mode": "external_text_layer",
        "body_render_mode": "in_image",
        "placement_strategy": execution["integration"],
    }
    page["geometry"]["regions"] = [
        {
            "id": "R1",
            "role": "primary_structure",
            "x": 80,
            "y": 130,
            "w": 820,
            "h": 500,
            "priority": "primary",
        },
        {
            "id": "R2",
            "role": "subordinate_evidence",
            "x": 920,
            "y": 180,
            "w": 280,
            "h": 390,
            "priority": "secondary",
        },
    ]
    page["image_plan"] = {
        "use_scene": False,
        "scene_type": "No independent scene; the business relationship field carries the page",
        "business_object": execution["carrier"],
        "semantic_role": execution["role"],
        "placement": execution["placement"],
        "front_facing_people": False,
        "identifiable_location": False,
        "factual_event_implication": False,
    }
    page["connectors"] = [
        {
            "from": edge["from"],
            "to": edge["to"],
            "type": edge["relation"],
            "direction": case["direction"],
            "label": edge["label"],
            "main_chain": edge["from"] == focus_ref or edge["to"] == focus_ref,
        }
        for edge in case["edges"]
    ]
    page["final_text"] = [
        {
            "id": f"F{index}",
            "role": "result" if item["id"] == focus_ref else "module",
            "text": item["text"],
            "region_id": "R1" if item["id"] in case["primary_refs"] else "R2",
        }
        for index, item in enumerate(evidence, start=1)
    ]
    page["generation_handoff"] = {
        "structural_guidance": {
            "source": "structural_decision",
            "additional_constraints": [
                "keep one primary structure",
                "bind every P0 evidence unit",
                "do not duplicate one judgment as another primary region",
            ],
        },
        "required_text": [item["text"] for item in evidence],
        "style_source_ref": style_source_ref,
        "title_exclusion_instruction": (
            "Reserve the top title area for an external PowerPoint text layer. "
            "Do not draw title, subtitle, logo or page number."
        ),
    }
    page["avoid"] = [
        "equal treatment of unequal semantic roles",
        "one visual object per bullet",
        "a second primary structure",
    ]
    page["qa"] = {
        "status": "passed",
        "score": 96,
        "blocking_issues": [],
        "warnings": [],
    }
    return page


def _mutate(page: dict[str, Any], mutation: str) -> dict[str, Any]:
    invalid = deepcopy(page)
    if mutation == "missing_primary_relation":
        invalid["semantic_graph"]["primary_relation"] = "none"
    elif mutation == "unbound_p0_evidence":
        first_p0 = next(
            item["id"] for item in invalid["evidence_units"] if item["priority"] == "P0"
        )
        invalid["structural_decision"]["text_bindings"] = [
            item
            for item in invalid["structural_decision"]["text_bindings"]
            if item["evidence_id"] != first_p0
        ]
    elif mutation == "dual_visual_center":
        invalid["visual_decision"]["visual_center_count"] = 2
    elif mutation == "replicated_roles":
        actor_ids = [item["id"] for item in invalid["evidence_units"][:2]]
        for item in invalid["evidence_units"]:
            if item["id"] in actor_ids:
                item["kind"] = "actor"
        focus_ref = invalid["structural_decision"]["semantic_focus"]["ref"]
        for item in invalid["structural_decision"]["text_bindings"]:
            if item["evidence_id"] in actor_ids:
                item["target_ref"] = focus_ref
    elif mutation == "duplicated_primary_expression":
        binding = invalid["structural_decision"]["text_bindings"][0]
        evidence_id = binding["evidence_id"]
        original_target = binding["target_ref"]
        focus_ref = invalid["structural_decision"]["semantic_focus"]["ref"]
        if original_target == focus_ref:
            focus_ref = next(
                item
                for item in invalid["semantic_graph"]["nodes"]
                if item != original_target
            )
        primary_refs = invalid["structural_decision"]["primary_refs"]
        for target in (original_target, focus_ref):
            if target not in primary_refs:
                primary_refs.append(target)
        invalid["structural_decision"]["secondary_refs"] = [
            item
            for item in invalid["structural_decision"]["secondary_refs"]
            if item not in {original_target, focus_ref}
        ]
        invalid["structural_decision"]["text_bindings"].append(
            {
                "evidence_id": evidence_id,
                "target_ref": focus_ref,
                "binding": binding["binding"],
            }
        )
    elif mutation == "layout_recipe_in_relationship":
        invalid["semantic_graph"]["decision_relationship"] = (
            "主视觉以四条纵向泳道排列，底部设置统一收束条。"
        )
    elif mutation == "disconnected_media_and_text":
        invalid["visual_decision"]["text_integration_method"] = (
            "左图右表，两侧各自完整呈现内容，彼此没有文字归属或业务连接。"
        )
    elif mutation == "dual_primary_narrative":
        invalid["visual_decision"]["spatial_organization"] += (
            " 另一套总结链独立于主关系形成结果说明。"
        )
    elif mutation == "abstract_center":
        invalid["visual_decision"]["spatial_organization"] = (
            "页面中央设置抽象中心框，周边放射连接全部内容。"
        )
    elif mutation == "style_leak":
        invalid["generation_handoff"]["structural_guidance"]["additional_constraints"].append(
            "use #123456 borders"
        )
    elif mutation == "generic_execution_carrier":
        invalid["image_plan"]["business_object"] = "Semantic nodes, actions, relationships and outcomes"
        invalid["visual_decision"]["visual_hierarchy"]["primary"] = "Semantic nodes, actions, relationships and outcomes"
    elif mutation == "generic_text_integration":
        invalid["visual_decision"]["text_integration_method"] = "Bind each text unit to its semantic node inside the primary structure."
    elif mutation == "generic_relationship_field":
        invalid["visual_decision"]["spatial_organization"] = "Use one path as the primary structure and keep secondary evidence subordinate."
        invalid["visual_decision"]["relationship_encoding"] = "Preserve the declared direction and edge labels."
        invalid["image_plan"]["semantic_role"] = "Optional medium selected by the final renderer"
        invalid["image_plan"]["placement"] = "One integrated relationship field"
    else:
        raise ValueError(f"Unknown mutation: {mutation}")
    return invalid


def _normalized_without_style(page: dict[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(page)
    normalized["generation_handoff"]["style_source_ref"] = "<external-style-source>"
    return normalized


def _write_and_validate(
    page: dict[str, Any],
    directory: Path,
    name: str,
) -> dict[str, Any]:
    path = directory / f"{name}.json"
    path.write_text(json.dumps(page, ensure_ascii=False, indent=2), encoding="utf-8")
    return validate_json(path, ROOT)


def main() -> int:
    payload = json.loads(FIXTURES.read_text(encoding="utf-8"))
    base = json.loads(BASE_PAGE.read_text(encoding="utf-8"))
    cases = payload["cases"]
    categories = {case["category"] for case in cases}
    domains = {case["domain"] for case in cases}
    if len(cases) != 6 or categories != EXPECTED_CATEGORIES:
        raise SystemExit(
            f"Expected six canonical categories, got {len(cases)} cases and {sorted(categories)}"
        )
    if len(domains) < 4:
        raise SystemExit(f"Fixture set must cover at least four domains, got {sorted(domains)}")
    if len({case["id"] for case in cases}) != len(cases):
        raise SystemExit("Fixture ids must be unique")

    valid_count = 0
    invalid_count = 0
    style_variant_count = 0
    with tempfile.TemporaryDirectory() as temp:
        directory = Path(temp)
        for index, case in enumerate(cases, start=1):
            variants = [
                _page_from_case(
                    base,
                    case,
                    page_number=index,
                    style_source_ref=style_ref,
                )
                for style_ref in payload["style_refs"]
            ]
            normalized = [_normalized_without_style(page) for page in variants]
            if any(item != normalized[0] for item in normalized[1:]):
                raise SystemExit(f"Style source changed structural JSON for fixture {case['id']}")
            prompts = [
                page_prompt(page).replace(
                    f"[Style source]\n{style_ref}",
                    "[Style source]\n<external-style-source>",
                )
                for page, style_ref in zip(variants, payload["style_refs"], strict=True)
            ]
            if any(item != prompts[0] for item in prompts[1:]):
                raise SystemExit(f"Style source changed structural prompt for fixture {case['id']}")
            style_variant_count += len(variants)

            valid_page = variants[0]
            result = _write_and_validate(valid_page, directory, f"valid-{case['id']}")
            if not result["valid"] or result["warnings"]:
                raise SystemExit(
                    f"Valid fixture failed {case['id']}: "
                    f"errors={result['errors']} warnings={result['warnings']}"
                )
            valid_count += 1

            for mutation, expected_code in payload["failure_mutations"].items():
                invalid = _mutate(valid_page, mutation)
                result = _write_and_validate(
                    invalid,
                    directory,
                    f"invalid-{case['id']}-{mutation}",
                )
                codes = {item["code"] for item in result["errors"]}
                if result["valid"] or expected_code not in codes:
                    raise SystemExit(
                        f"Mutation {mutation} was not precisely blocked for {case['id']}; "
                        f"expected={expected_code} got={sorted(codes)}"
                    )
                invalid_count += 1

    print(
        "DOMAIN-NEUTRAL FIXTURES PASS "
        f"({valid_count} valid, {invalid_count} invalid, {style_variant_count} style variants)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
