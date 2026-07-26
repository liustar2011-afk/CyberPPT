from __future__ import annotations

import unittest

from cyberppt.argument_flow_contract import (
    audit_argument_flow,
    validate_page_role_fields,
)


def record(
    source_id: str,
    claim_role: str,
    *,
    pages: list[str] | None = None,
    depends_on: list[str] | None = None,
    status: str = "现状",
) -> dict[str, object]:
    return {
        "id": source_id,
        "claim_role": claim_role,
        "page_refs": pages or [],
        "depends_on": depends_on or [],
        "status": status,
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
        "proof_points": [
            {"claim": f"{page_id}支撑点", "source_refs": refs or []}
        ],
        "new_value_vs_previous": f"{page_id}新增判断",
        "reserved_for_later": "后续内容由后页展开。",
    }


def strict_outline(*pages: dict[str, object]) -> dict[str, object]:
    return {"argument_contract_mode": "strict", "pages": list(pages)}


def strict_truth(*records: dict[str, object]) -> dict[str, object]:
    return {"argument_contract_mode": "strict", "records": list(records)}


class ArgumentFlowContractTests(unittest.TestCase):
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
        page["proof_points"] = [{"claim": "越界证据", "source_refs": ["S999"]}]

        self.assertIn(
            "PROOF_POINT_INVALID",
            {issue.code for issue in validate_page_role_fields(strict_outline(page))},
        )

    def test_adjacent_same_job_and_sources_are_rejected(self) -> None:
        first = content_page("p04", 4, "solution", refs=["S001"])
        second = content_page("p05", 5, "solution", refs=["S001"])
        first["page_job"] = second["page_job"] = "说明总体能力建设框架"

        issues = audit_argument_flow(
            strict_outline(first, second),
            strict_truth(record("S001", "recommendation", pages=["p04", "p05"])),
        )

        self.assertIn("PAGE_CONTRIBUTION_OVERLAP", {issue.code for issue in issues})

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
