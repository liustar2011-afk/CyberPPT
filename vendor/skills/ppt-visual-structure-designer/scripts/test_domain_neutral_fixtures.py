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
        "spatial_organization": (
            f"Use {', '.join(case['spatial_grammar'])} as one integrated semantic structure; "
            "keep secondary evidence subordinate to the semantic focus."
        ),
        "reading_path": [evidence_by_id[item]["text"] for item in case["reading_sequence"]],
        "text_integration_method": (
            "Bind each text unit to its semantic node, action, relationship or outcome inside the primary structure."
        ),
        "relationship_encoding": (
            "Preserve the declared direction and edge labels; use adjacency for subordinate relationships."
        ),
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
        "placement_strategy": "Place each locked text unit with the semantic node or relationship it explains.",
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
        "scene_type": "No medium selected at the structural stage",
        "business_object": "Semantic nodes, actions, relationships and outcomes",
        "semantic_role": "Optional medium selected by the final renderer",
        "placement": "One integrated relationship field with subordinate evidence attached",
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
    elif mutation == "style_leak":
        invalid["generation_handoff"]["structural_guidance"]["additional_constraints"].append(
            "use #123456 borders"
        )
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
