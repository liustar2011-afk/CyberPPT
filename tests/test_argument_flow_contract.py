from __future__ import annotations

import unittest

from cyberppt.argument_flow_contract import (
    audit_argument_flow,
    validate_page_role_fields,
    validate_source_relation_fields,
)


def record(
    source_id: str,
    claim_role: str,
    *,
    pages: list[str] | None = None,
    depends_on: list[str] | None = None,
    status: str = "现状",
    statement: str = "",
) -> dict[str, object]:
    return {
        "id": source_id,
        "claim_role": claim_role,
        "page_refs": pages or [],
        "depends_on": depends_on or [],
        "status": status,
        "statement": statement,
    }


def content_page(
    page_id: str,
    sequence: int,
    argument_role: str,
    *,
    refs: list[str] | None = None,
    prerequisites: list[str] | None = None,
    allowed: list[str] | None = None,
    forbidden: list[str] | None = None,
    status: str = "confirmed",
) -> dict[str, object]:
    return {
        "page_id": page_id,
        "sequence": sequence,
        "page_type": "content",
        "argument_role": argument_role,
        "source_refs": refs or [],
        "allowed_claim_roles": allowed or [],
        "forbidden_claim_roles": forbidden or [],
        "prerequisite_pages": prerequisites or [],
        "main_claim_status": status,
        "page_job": f"{page_id}唯一页面任务",
        "business_question": f"{page_id}需要回答什么",
        "main_message": f"{page_id}支撑点",
        "proof_points": [
            {"claim": f"{page_id}支撑点", "source_refs": refs or [], "consumption": "primary"}
        ],
        "new_value_vs_previous": f"{page_id}新增判断",
        "reserved_for_later": "后续内容由后页展开。",
    }


def strict_outline(*pages: dict[str, object]) -> dict[str, object]:
    return {"argument_contract_mode": "strict", "pages": list(pages)}


def strict_truth(*records: dict[str, object]) -> dict[str, object]:
    return {"argument_contract_mode": "strict", "records": list(records)}


class ArgumentFlowContractTests(unittest.TestCase):
    def test_v2_requires_source_relation_fields_not_argument_taxonomy(self) -> None:
        page = {
            "page_id": "p10",
            "page_type": "content",
            "page_mission": "说明总体能力框架的构成",
            "core_message": "总体能力框架由五个层次构成",
            "source_refs": ["S021"],
            "content_units": [
                {"statement": "总体能力框架由五个层次构成", "source_refs": ["S021"], "role": "primary"}
            ],
            "content_relations": [
                {"relation": "composed_of", "subject": "总体能力框架", "objects": ["五个层次"], "source_refs": ["S021"]}
            ],
            "new_value_vs_previous": "给出后续建设内容的总体结构",
            "reserved_for_later": "各层内容由后页展开",
        }
        payload = {"schema": "cyberppt.outline.v2", "argument_contract_mode": "strict", "pages": [page]}

        self.assertEqual([], validate_source_relation_fields(payload))
        codes = {issue.code for issue in validate_page_role_fields(payload)}
        self.assertNotIn("ARGUMENT_FIELDS_MISSING", codes)
        self.assertNotIn("PAGE_CONTRIBUTION_FIELDS_MISSING", codes)

    def test_v2_content_unit_must_use_page_sources(self) -> None:
        payload = {
            "schema": "cyberppt.outline.v2",
            "argument_contract_mode": "strict",
            "pages": [{
                "page_id": "p10", "page_type": "content",
                "page_mission": "说明框架", "core_message": "框架由五层构成",
                "source_refs": ["S021"],
                "content_units": [{"statement": "框架由五层构成", "source_refs": ["S999"], "role": "primary"}],
                "content_relations": [{"relation": "composed_of", "source_refs": ["S021"]}],
                "new_value_vs_previous": "给出结构", "reserved_for_later": "各层后述",
            }],
        }
        self.assertIn("CONTENT_UNIT_INVALID", {issue.code for issue in validate_source_relation_fields(payload)})

    def test_v2_content_relation_must_use_page_sources(self) -> None:
        payload = {
            "schema": "cyberppt.outline.v2", "argument_contract_mode": "strict",
            "pages": [{
                "page_id": "p10", "page_type": "content",
                "page_mission": "说明框架", "core_message": "框架由五层构成",
                "source_refs": ["S021"],
                "content_units": [{"statement": "框架由五层构成", "source_refs": ["S021"], "role": "primary"}],
                "content_relations": [{"relation": "composed_of", "source_refs": ["S999"]}],
                "new_value_vs_previous": "给出结构", "reserved_for_later": "各层后述",
            }],
        }
        self.assertIn("CONTENT_RELATION_REFS_INVALID", {issue.code for issue in validate_source_relation_fields(payload)})

    def test_v2_boundary_record_cannot_be_primary_content_unit(self) -> None:
        page = {
            "page_id": "p10", "sequence": 10, "page_type": "content",
            "page_mission": "说明建设内容", "core_message": "建设统一运营能力",
            "source_refs": ["S027"],
            "content_units": [{"statement": "投资规模待确定", "source_refs": ["S027"], "role": "primary"}],
            "content_relations": [{"relation": "contains", "source_refs": ["S027"]}],
            "core_message_derivation": {"source_refs": [], "supporting_statements": [], "derivation": "", "introduced_relations": [], "introduced_modalities": []},
            "new_value_vs_previous": "给出建设内容", "reserved_for_later": "投资后续确定",
        }
        payload = {"schema": "cyberppt.outline.v2", "argument_contract_mode": "strict", "pages": [page]}
        truth = strict_truth(record("S027", "boundary", pages=["p10"]))

        codes = {issue.code for issue in audit_argument_flow(payload, truth)}
        self.assertIn("BOUNDARY_USED_AS_PRIMARY_PROOF", codes)

    def test_v2_boundary_record_cannot_derive_ordinary_core_message(self) -> None:
        page = {
            "page_id": "p10", "sequence": 10, "page_type": "content",
            "page_mission": "说明建设内容", "core_message": "投资规模仍待确定",
            "source_refs": ["S027"],
            "content_units": [{"statement": "投资规模待确定", "source_refs": ["S027"], "role": "boundary"}],
            "content_relations": [{"relation": "bounded_by", "source_refs": ["S027"]}],
            "core_message_derivation": {"source_refs": ["S027"], "supporting_statements": ["投资规模待确定"], "derivation": "保留原文边界", "introduced_relations": [], "introduced_modalities": []},
            "new_value_vs_previous": "给出投资边界", "reserved_for_later": "投资后续确定",
        }
        payload = {"schema": "cyberppt.outline.v2", "argument_contract_mode": "strict", "pages": [page]}
        truth = strict_truth(record("S027", "boundary", pages=["p10"]))

        codes = {issue.code for issue in audit_argument_flow(payload, truth)}
        self.assertIn("BOUNDARY_USED_AS_CORE_MESSAGE", codes)

    def test_v2_justified_boundary_focus_page_may_use_boundary_core(self) -> None:
        page = {
            "page_id": "p10", "sequence": 10, "page_type": "content",
            "page_mission": "明确试运行准入边界", "core_message": "三项测试通过后才能进入真实客户试运行",
            "boundary_focus": True,
            "boundary_focus_reason": "本页唯一业务职责是明确真实客户试运行的准入条件。",
            "source_refs": ["S027"],
            "content_units": [{"statement": "三项测试通过后才能试运行", "source_refs": ["S027"], "role": "boundary"}],
            "content_relations": [{"relation": "bounded_by", "source_refs": ["S027"]}],
            "core_message_derivation": {"source_refs": ["S027"], "supporting_statements": ["三项测试通过后才能试运行"], "derivation": "保留原文准入条件", "introduced_relations": [], "introduced_modalities": []},
            "new_value_vs_previous": "给出准入条件", "reserved_for_later": "验收指标后述",
        }
        payload = {"schema": "cyberppt.outline.v2", "argument_contract_mode": "strict", "pages": [page]}
        truth = strict_truth(record("S027", "boundary", pages=["p10"]))

        codes = {issue.code for issue in audit_argument_flow(payload, truth)}
        self.assertNotIn("BOUNDARY_USED_AS_PRIMARY_PROOF", codes)
        self.assertNotIn("BOUNDARY_USED_AS_CORE_MESSAGE", codes)
        self.assertNotIn("BOUNDARY_FOCUS_JUSTIFICATION_MISSING", codes)

    def test_strict_content_page_requires_argument_role_fields(self) -> None:
        payload = {
            "argument_contract_mode": "strict",
            "pages": [
                {
                    "page_id": "p04",
                    "page_type": "content",
                    "argument_role": "foundation",
                }
            ],
        }

        codes = {issue.code for issue in validate_page_role_fields(payload)}

        self.assertIn("ARGUMENT_FIELDS_MISSING", codes)

    def test_legacy_outline_does_not_require_argument_fields(self) -> None:
        payload = {
            "argument_contract_mode": "legacy",
            "pages": [{"page_id": "p04", "page_type": "content"}],
        }

        self.assertEqual([], validate_page_role_fields(payload))

    def test_strict_content_page_requires_contribution_fields(self) -> None:
        payload = {
            "argument_contract_mode": "strict",
            "pages": [
                {
                    "page_id": "p04",
                    "page_type": "content",
                    "argument_role": "foundation",
                    "allowed_claim_roles": ["fact"],
                    "forbidden_claim_roles": ["recommendation"],
                    "prerequisite_pages": [],
                }
            ],
        }

        self.assertIn(
            "PAGE_CONTRIBUTION_FIELDS_MISSING",
            {issue.code for issue in validate_page_role_fields(payload)},
        )

    def test_proof_points_must_use_page_sources(self) -> None:
        page = content_page("p04", 4, "foundation", refs=["S001"])
        page["proof_points"] = [{"claim": "越界证据", "source_refs": ["S999"], "consumption": "primary"}]

        self.assertIn(
            "PROOF_POINT_INVALID",
            {issue.code for issue in validate_page_role_fields(strict_outline(page))},
        )

    def test_boundary_refs_must_not_overlap_proof_points(self) -> None:
        page = content_page("p04", 4, "positioning", refs=["S001"])
        page["boundary_refs"] = ["S001"]

        self.assertIn(
            "BOUNDARY_REFS_INVALID",
            {issue.code for issue in validate_page_role_fields(strict_outline(page))},
        )

    def test_off_topic_primary_proof_is_rejected(self) -> None:
        page = content_page("p09", 9, "positioning", refs=["S059"])
        page["page_job"] = "明确平台的总体定位"
        page["business_question"] = "拟建设什么性质的平台"
        page["main_message"] = "平台定位为行业公共预测能力"
        page["proof_points"] = [
            {
                "claim": "采购方式和投资规模需要后续确定",
                "source_refs": ["S059"],
                "consumption": "primary",
            }
        ]

        issues = audit_argument_flow(
            strict_outline(page),
            strict_truth(
                record(
                    "S059",
                    "boundary",
                    pages=["p09"],
                    statement="采购方式和投资规模需要后续确定",
                )
            ),
        )

        self.assertIn("PROOF_POINT_OFF_TOPIC", {issue.code for issue in issues})

    def test_boundary_record_cannot_be_primary_proof_on_solution_page(self) -> None:
        page = content_page("p12", 12, "solution", refs=["S027"])
        page["proof_points"] = [
            {
                "claim": "正式投资规模需要后续确定",
                "source_refs": ["S027"],
                "consumption": "primary",
            }
        ]

        issues = audit_argument_flow(
            strict_outline(page),
            strict_truth(record("S027", "boundary", pages=["p12"])),
        )

        self.assertIn("BOUNDARY_USED_AS_PRIMARY_PROOF", {issue.code for issue in issues})

    def test_too_many_primary_proof_directions_are_rejected(self) -> None:
        page = content_page("p20", 20, "solution", refs=["S001", "S002", "S003", "S004"])
        page["proof_points"] = [
            {
                "claim": f"能力主题支撑方向{index}",
                "source_refs": [source_id],
                "consumption": "primary",
            }
            for index, source_id in enumerate(page["source_refs"], start=1)
        ]

        issues = audit_argument_flow(
            strict_outline(page),
            strict_truth(
                *[
                    record(source_id, "recommendation", pages=["p20"])
                    for source_id in page["source_refs"]
                ]
            ),
        )

        self.assertIn("PRIMARY_PROOF_DIRECTIONS_EXCESSIVE", {issue.code for issue in issues})

    def test_consolidated_primary_proof_passes_focus_audit(self) -> None:
        page = content_page("p20", 20, "solution", refs=["S001", "S002", "S003", "S004"])
        page["page_job"] = "说明核心能力如何形成统一研判"
        page["business_question"] = "哪些能力共同支撑统一研判"
        page["main_message"] = "四类能力共同形成统一研判"
        page["proof_points"] = [
            {
                "claim": "四类能力共同支撑统一研判",
                "source_refs": ["S001", "S002", "S003", "S004"],
                "consumption": "primary",
            }
        ]

        issues = audit_argument_flow(
            strict_outline(page),
            strict_truth(
                *[
                    record(source_id, "recommendation", pages=["p20"])
                    for source_id in page["source_refs"]
                ]
            ),
        )

        focus_codes = {
            "PROOF_POINT_OFF_TOPIC",
            "BOUNDARY_USED_AS_PRIMARY_PROOF",
            "PRIMARY_PROOF_DIRECTIONS_EXCESSIVE",
        }
        self.assertFalse(focus_codes & {issue.code for issue in issues})

    def test_adjacent_same_job_and_sources_are_rejected(self) -> None:
        first = content_page("p04", 4, "solution", refs=["S001"])
        second = content_page("p05", 5, "solution", refs=["S001"])
        first["page_job"] = second["page_job"] = "说明总体能力建设框架"

        issues = audit_argument_flow(
            strict_outline(first, second),
            strict_truth(record("S001", "recommendation", pages=["p04", "p05"])),
        )

        self.assertIn("PAGE_CONTRIBUTION_OVERLAP", {issue.code for issue in issues})

    def test_nonadjacent_partial_evidence_overlap_is_rejected(self) -> None:
        first = content_page("p04", 4, "solution", refs=["S001", "S002"])
        middle = content_page("p05", 5, "solution", refs=["S003"])
        last = content_page("p06", 6, "solution", refs=["S001", "S002", "S004"])
        first["page_job"] = last["page_job"] = "说明总体能力建设框架"
        for page in (first, middle, last):
            page["proof_points"][0]["consumption"] = "supporting"

        issues = audit_argument_flow(
            strict_outline(first, middle, last),
            strict_truth(
                record("S001", "recommendation", pages=["p04", "p06"]),
                record("S002", "recommendation", pages=["p04", "p06"]),
                record("S003", "recommendation", pages=["p05"]),
                record("S004", "recommendation", pages=["p06"]),
            ),
        )

        overlaps = [issue for issue in issues if issue.code == "PAGE_CONTRIBUTION_OVERLAP"]
        self.assertEqual([("p04", "p06")], [issue.pages for issue in overlaps])

    def test_foundation_page_rejects_recommendation_claim(self) -> None:
        issues = audit_argument_flow(
            strict_outline(
                content_page(
                    "p04",
                    4,
                    "foundation",
                    refs=["S006R"],
                    allowed=["fact"],
                    forbidden=["recommendation"],
                )
            ),
            strict_truth(record("S006R", "recommendation", pages=["p04"])),
        )

        self.assertIn(
            "CLAIM_ROLE_EXCEEDS_PAGE_ROLE",
            {issue.code for issue in issues},
        )

    def test_prerequisite_must_appear_earlier(self) -> None:
        issues = audit_argument_flow(
            strict_outline(
                content_page("p04", 4, "necessity", prerequisites=["p06"]),
                content_page("p06", 6, "gap"),
            ),
            strict_truth(),
        )

        self.assertIn(
            "PREREQUISITE_PAGE_NOT_EARLIER",
            {issue.code for issue in issues},
        )

    def test_dependency_cycle_is_rejected(self) -> None:
        issues = audit_argument_flow(
            strict_outline(
                content_page("p04", 4, "gap", prerequisites=["p05"]),
                content_page("p05", 5, "necessity", prerequisites=["p04"]),
            ),
            strict_truth(),
        )

        self.assertIn(
            "ARGUMENT_DEPENDENCY_CYCLE",
            {issue.code for issue in issues},
        )

    def test_foundation_change_gap_necessity_sequence_passes(self) -> None:
        pages = (
            content_page("p04", 4, "foundation", refs=["S004"], allowed=["fact"]),
            content_page(
                "p05",
                5,
                "change",
                refs=["S005"],
                prerequisites=["p04"],
                allowed=["change"],
            ),
            content_page(
                "p06",
                6,
                "gap",
                refs=["S006"],
                prerequisites=["p04", "p05"],
                allowed=["problem"],
            ),
            content_page(
                "p07",
                7,
                "necessity",
                refs=["S007"],
                prerequisites=["p06"],
                allowed=["judgment"],
            ),
        )
        truth = strict_truth(
            record("S004", "fact", pages=["p04"]),
            record("S005", "change", pages=["p05"]),
            record("S006", "problem", pages=["p06"]),
            record("S007", "judgment", pages=["p07"]),
        )

        self.assertEqual([], audit_argument_flow(strict_outline(*pages), truth))

    def test_scope_page_may_use_first_phase_recommendation(self) -> None:
        issues = audit_argument_flow(
            strict_outline(
                content_page(
                    "p19",
                    19,
                    "scope",
                    refs=["S022"],
                    allowed=["recommendation", "boundary"],
                    status="proposed",
                )
            ),
            strict_truth(
                record("S022", "recommendation", pages=["p19"], status="首期建议")
            ),
        )

        self.assertNotIn(
            "CLAIM_ROLE_EXCEEDS_PAGE_ROLE",
            {issue.code for issue in issues},
        )

    def test_strict_outline_can_read_legacy_typed_source_record(self) -> None:
        legacy_truth = {
            "argument_contract_mode": "legacy",
            "records": [
                {
                    "id": "S004",
                    "type": "F",
                    "page_refs": ["p04"],
                    "depends_on": [],
                    "status": "现状",
                }
            ],
        }
        issues = audit_argument_flow(
            strict_outline(
                content_page(
                    "p04",
                    4,
                    "foundation",
                    refs=["S004"],
                    allowed=["fact"],
                )
            ),
            legacy_truth,
        )

        self.assertEqual([], issues)

    def test_page_evidence_mapping_must_match_in_both_directions(self) -> None:
        issues = audit_argument_flow(
            strict_outline(
                content_page(
                    "p04",
                    4,
                    "foundation",
                    refs=["S002"],
                    allowed=["fact"],
                )
            ),
            strict_truth(record("S004", "fact", pages=["p04"])),
        )

        self.assertIn(
            "PAGE_EVIDENCE_MAPPING_MISMATCH",
            {issue.code for issue in issues},
        )

    def test_missing_outline_source_is_rejected(self) -> None:
        issues = audit_argument_flow(
            strict_outline(
                content_page(
                    "p04",
                    4,
                    "foundation",
                    refs=["S404"],
                    allowed=["fact"],
                )
            ),
            strict_truth(),
        )

        self.assertIn("PAGE_SOURCE_MISSING", {issue.code for issue in issues})

    def test_strict_content_page_requires_evidence(self) -> None:
        issues = audit_argument_flow(
            strict_outline(content_page("p14", 14, "solution")),
            strict_truth(),
        )

        self.assertIn("PAGE_EVIDENCE_MISSING", {issue.code for issue in issues})

    def test_boundary_cannot_be_upgraded_to_confirmed(self) -> None:
        issues = audit_argument_flow(
            strict_outline(
                content_page(
                    "p19",
                    19,
                    "scope",
                    refs=["S023"],
                    allowed=["boundary"],
                    status="confirmed",
                )
            ),
            strict_truth(
                record("S023", "boundary", pages=["p19"], status="条件成熟后")
            ),
        )

        self.assertIn("SOURCE_STATUS_UPGRADED", {issue.code for issue in issues})

    def test_claim_dependency_must_be_covered_by_prerequisite_pages(self) -> None:
        issues = audit_argument_flow(
            strict_outline(
                content_page(
                    "p04",
                    4,
                    "foundation",
                    refs=["S004"],
                    allowed=["fact"],
                ),
                content_page(
                    "p19",
                    19,
                    "scope",
                    refs=["S022"],
                    allowed=["recommendation"],
                    status="proposed",
                ),
            ),
            strict_truth(
                record("S004", "fact", pages=["p04"]),
                record(
                    "S022",
                    "recommendation",
                    pages=["p19"],
                    depends_on=["S004"],
                    status="首期建议",
                ),
            ),
        )

        self.assertIn(
            "EVIDENCE_PREREQUISITE_UNCOVERED",
            {issue.code for issue in issues},
        )


if __name__ == "__main__":
    unittest.main()
