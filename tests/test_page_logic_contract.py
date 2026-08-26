from __future__ import annotations

import unittest

from cyberppt.page_logic_contract import (
    build_page_logic_preflight,
    validate_authored_page_logic,
    validate_page_logic_contract,
)


def _p04_page() -> dict[str, object]:
    refs = ["ST0046", "ST0047", "ST0048", "ST0049", "ST0052", "ST0053", "ST0054", "ST0055", "ST0057"]
    return {
        "page_id": "p04",
        "page_type": "content",
        "title": "一、建设背景",
        "core_message": "协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求。",
        "source_refs": refs,
        "page_consumption_contract_mode": "required",
        "onscreen_structure_contract_mode": "required",
        "page_logic_contract_mode": "required",
        "argument_chain": [
            {"role": "context", "source_refs": ["ST0046"]},
            {"role": "driver", "source_refs": ["ST0047"]},
            {"role": "need", "source_refs": ["ST0049"]},
            {"role": "requirement", "source_refs": ["ST0057"]},
        ],
        "content_units": [
            {
                "unit_id": f"p04-U{index:02d}",
                "statement": statement,
                "source_refs": [ref],
                "argument_function": "mechanism",
                "relation_to_proposition": "supports",
                "decision_scope": "current",
                "visibility": "supporting_onscreen",
                "topology_role": "main_chain",
                "group_id": f"g{index}",
                "onscreen_group_id": f"g{index}",
                "onscreen_group_kind": "proposition",
                "peer_dimension": "argument_stage",
                "sequence_index": index,
            }
            for index, (ref, statement) in enumerate(
                [
                    ("ST0046", "电力行业具有基础性、战略性属性。"),
                    ("ST0047", "数字化、市场化、智能化发展提升跨主体协同需求。"),
                    ("ST0049", "业务需求持续增长。"),
                    ("ST0053", "资源分散且口径和接口尚未完全统一。"),
                    ("ST0057", "需要完善资源供给到业务应用的持续运营机制。"),
                ],
                start=1,
            )
        ],
        "page_logic_contract": {
            "nodes": [
                {"id": "context", "role": "context", "statement": "电力行业完整产业链覆盖生产、传输、消费及相关服务。", "source_refs": ["ST0046"], "prose_signals": ["完整产业链", "生产、传输、消费"], "onscreen_signals": ["完整产业链"]},
                {"id": "driver", "role": "driver", "statement": "数字化、市场化、智能化持续提升跨主体、跨系统、跨领域协同需求。", "source_refs": ["ST0047"], "prose_signals": ["数字化、市场化、智能化", "跨主体、跨系统、跨领域"], "onscreen_signals": ["协同需求"]},
                {"id": "need", "role": "need", "statement": "多源数据、专业知识、预测模型、持续监测和智能服务需求持续增长。", "source_refs": ["ST0049"], "prose_signals": ["多源数据、专业知识、预测模型", "持续监测和智能服务"], "onscreen_signals": ["多源数据、专业知识、预测模型", "持续监测和智能服务"]},
                {"id": "constraint", "role": "constraint", "statement": "数据、知识、模型和专业能力分散于不同主体、系统与安全域，目录、口径、接口、标准、授权和版本尚未完全统一，协同成本较高。", "source_refs": ["ST0052", "ST0053", "ST0054"], "prose_signals": ["数据、知识、模型和专业能力", "不同主体、系统与安全域", "尚未完全统一", "协同成本较高"], "onscreen_signals": ["数据、知识、模型和专业能力", "不同主体、系统与安全域", "尚未完全统一", "协同成本较高"]},
                {"id": "requirement", "role": "requirement", "statement": "建设需要形成资源连接、可信使用、产品组织和持续服务基础。", "source_refs": ["ST0048", "ST0055", "ST0057"], "prose_signals": ["资源连接、可信使用、产品组织和持续服务"], "onscreen_signals": ["资源连接、可信使用、产品组织和持续服务"]},
            ],
            "page_proposition": {"statement": "协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求。", "node_ids": ["need", "constraint", "requirement"], "source_refs": ["ST0048", "ST0049", "ST0052", "ST0053", "ST0054", "ST0055", "ST0057"], "prose_signals": ["协同需求增长与资源协同现状", "资源连接、可信使用、产品组织和持续服务的基础要求"], "onscreen_signals": ["协同需求增长与资源协同现状", "资源连接、可信使用、产品组织和持续服务的基础要求"]},
            "edges": [
                {"id": "e0", "from": "context", "to": "driver", "relation": "contextualizes", "basis": "inferred", "confidence": "low", "inference_rationale": "完整产业链的行业属性构成协同需求升级的业务背景。"},
                {"id": "e1", "from": "driver", "to": "need", "relation": "creates_need", "basis": "explicit", "confidence": "high"},
                {"id": "e2", "from": "need", "to": "requirement", "relation": "requires", "basis": "inferred", "confidence": "medium", "inference_rationale": "增长需求与资源协同、持续服务要求共同构成建设背景。"},
                {"id": "e3", "from": "constraint", "to": "requirement", "relation": "requires", "basis": "inferred", "confidence": "medium", "inference_rationale": "资源分散和协同成本构成资源连接与持续服务基础的建设依据。"},
            ],
            "paragraph_plan": [
                {"node_ids": ["context"]},
                {"node_ids": ["driver"]},
                {"node_ids": ["need", "constraint"]},
                {"node_ids": ["requirement"]},
            ],
            "onscreen_projection": [
                {"node_ids": ["context", "driver", "need"], "edge_ids": ["e0", "e1"], "carrier": "协同需求升级", "carrier_mode": "ordered_chain", "relation_signal": "→", "onscreen_signals": ["数字化、市场化、智能化", "协同需求"]},
                {"node_ids": ["constraint"], "carrier": "资源协同现状", "carrier_mode": "integrated_proposition", "relation_signal": "分散", "onscreen_signals": ["资源协同现状", "协同成本较高"]},
                {"node_ids": ["requirement"], "edge_ids": ["e2", "e3"], "carrier": "建设基础", "carrier_mode": "integrated_proposition", "relation_signal": "共同提出", "onscreen_signals": ["协同需求增长与资源协同现状共同提出", "资源连接、可信使用、产品组织和持续服务的基础要求"]},
            ],
        },
    }


def _expression_ir() -> dict[str, object]:
    return {
        "schema": "cyberppt.onscreen_expression_ir.v1",
        "pattern": "parallel_states_to_foundation",
        "reading_order": ["context", "demand", "need", "resource", "foundation"],
        "nodes": [
            {"id": "context", "role": "context", "render": "focus_label", "logic_node_ids": ["context"], "source_refs": ["ST0046"], "surface_label": "行业基础", "text": "完整产业链"},
            {"id": "demand", "role": "current_state", "render": "statement_stack", "logic_node_ids": ["driver"], "source_refs": ["ST0047"], "surface_label": "协同需求升级", "items": ["数字化、市场化、智能化", "跨主体、跨系统、跨领域协同需求"]},
            {"id": "need", "role": "requirement_target", "render": "chip_set", "logic_node_ids": ["need"], "source_refs": ["ST0049"], "surface_label": "业务服务需求", "items": ["多源数据、专业知识、预测模型", "持续监测和智能服务"]},
            {"id": "resource", "role": "current_state", "render": "statement_stack", "logic_node_ids": ["constraint"], "source_refs": ["ST0052", "ST0053", "ST0054"], "surface_label": "资源协同现状", "items": ["数据、知识、模型和专业能力分散于不同主体、系统与安全域", "目录、口径、接口、标准、授权和版本尚未完全统一", "协同成本较高"]},
            {"id": "foundation", "role": "conclusion", "render": "landing", "logic_node_ids": ["requirement"], "source_refs": ["ST0048", "ST0055", "ST0057"], "surface_label": "建设基础", "text": "协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求"},
        ],
        "edges": [
            {"id": "demand_to_need", "from": "demand", "to": "need", "relation": "raises_requirement", "visible_label": "提出更高要求", "source_basis": "explicit", "source_refs": ["ST0047", "ST0049"]},
            {"id": "need_to_foundation", "from": "need", "to": "foundation", "relation": "requires", "visible_label": "共同提出", "source_basis": "inferred", "source_refs": ["ST0048", "ST0049", "ST0055", "ST0057"]},
            {"id": "resource_to_foundation", "from": "resource", "to": "foundation", "relation": "requires", "visible_label": "共同提出", "source_basis": "inferred", "source_refs": ["ST0048", "ST0052", "ST0053", "ST0054"]},
        ],
    }


class PageLogicContractTests(unittest.TestCase):
    def test_p04_logic_contract_produces_ready_preflight(self) -> None:
        page = _p04_page()

        report = build_page_logic_preflight(page)

        self.assertEqual("ready", report["contract_status"])
        self.assertEqual([], report["issues"])

    def test_isolated_business_demand_fails_when_author_does_not_supply_chain(self) -> None:
        page = _p04_page()
        page["argument_chain"] = [{"role": "claim", "source_refs": ["ST0046", "ST0047"]}]
        page["page_logic_contract"] = {}

        codes = {issue["code"] for issue in validate_page_logic_contract(page)}

        self.assertIn("PAGE_LOGIC_CONTRACT_MISSING", codes)

    def test_inferred_strong_causality_is_rejected(self) -> None:
        page = _p04_page()
        next(edge for edge in page["page_logic_contract"]["edges"] if edge["id"] == "e2")["relation"] = "causes"

        codes = {issue["code"] for issue in validate_page_logic_contract(page)}

        self.assertIn("UNSUPPORTED_CAUSAL_LANGUAGE", codes)

    def test_expression_ir_keeps_reading_order_objects_and_visible_relations(self) -> None:
        page = _p04_page()
        page["page_logic_contract"]["onscreen_expression"] = _expression_ir()

        self.assertEqual([], validate_page_logic_contract(page))
        issues = validate_authored_page_logic(
            page,
            prose="完整产业链覆盖生产、传输、消费及相关服务。\n\n数字化、市场化、智能化持续提升跨主体、跨系统、跨领域协同需求。\n\n多源数据、专业知识、预测模型与持续监测和智能服务需求增长；数据、知识、模型和专业能力分散于不同主体、系统与安全域，目录、口径、接口、标准、授权和版本尚未完全统一，协同成本较高。\n\n协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求。",
            onscreen="行业基础：完整产业链\n协同需求升级：数字化、市场化、智能化→跨主体、跨系统、跨领域协同需求\n业务服务需求：多源数据、专业知识、预测模型；持续监测和智能服务；提出更高要求\n资源协同现状：数据、知识、模型和专业能力分散于不同主体、系统与安全域；目录、口径、接口、标准、授权和版本尚未完全统一，协同成本较高\n建设基础：协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求",
            module_titles=("行业基础", "协同需求升级", "业务服务需求", "资源协同现状", "建设基础"),
        )

        self.assertEqual([], issues)

    def test_expression_ir_rejects_dropped_object_or_relation_label(self) -> None:
        page = _p04_page()
        page["page_logic_contract"]["onscreen_expression"] = _expression_ir()
        expression = page["page_logic_contract"]["onscreen_expression"]
        expression["nodes"][2].pop("source_refs")
        expression["edges"][0].pop("visible_label")

        codes = {issue["code"] for issue in validate_page_logic_contract(page)}

        self.assertIn("ONSCREEN_EXPRESSION_NODE_INVALID", codes)
        self.assertIn("ONSCREEN_EXPRESSION_EDGE_INVALID", codes)

    def test_expression_ir_rejects_copy_without_a_declared_argument_role(self) -> None:
        page = _p04_page()
        page["page_logic_contract"]["onscreen_expression"] = _expression_ir()
        issues = validate_authored_page_logic(
            page,
            prose="完整产业链覆盖生产、传输、消费及相关服务。\n\n数字化、市场化、智能化持续提升跨主体、跨系统、跨领域协同需求。\n\n多源数据、专业知识、预测模型与持续监测和智能服务需求增长；数据、知识、模型和专业能力分散于不同主体、系统与安全域，目录、口径、接口、标准、授权和版本尚未完全统一，协同成本较高。\n\n协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求。",
            onscreen="行业基础：完整产业链\n协同需求升级：数字化、市场化、智能化→跨主体、跨系统、跨领域协同需求\n业务服务需求：多源数据、专业知识、预测模型；持续监测和智能服务；提出更高要求\n资源协同现状：数据、知识、模型和专业能力分散于不同主体、系统与安全域；目录、口径、接口、标准、授权和版本尚未完全统一，协同成本较高\n建设基础：协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求\n行业影响广泛",
            module_titles=("行业基础", "协同需求升级", "业务服务需求", "资源协同现状", "建设基础"),
        )

        unmapped = [item for item in issues if item["code"] == "ONSCREEN_EXPRESSION_COPY_UNMAPPED"]
        self.assertEqual(("行业影响广泛",), unmapped[0]["evidence"])

    def test_expression_ir_rejects_visible_node_disconnected_from_page_proposition(self) -> None:
        page = _p04_page()
        page["page_logic_contract"]["edges"] = [
            edge for edge in page["page_logic_contract"]["edges"] if edge["id"] != "e0"
        ]
        page["page_logic_contract"]["onscreen_expression"] = _expression_ir()

        codes = {issue["code"] for issue in validate_page_logic_contract(page)}

        self.assertIn("ONSCREEN_EXPRESSION_TOPIC_DISCONNECTED", codes)

    def test_short_phrases_must_keep_the_declared_relation_carrier(self) -> None:
        page = _p04_page()
        issues = validate_authored_page_logic(
            page,
            prose="完整产业链覆盖生产、传输、消费及相关服务。\n\n数字化、市场化、智能化持续提升跨主体、跨系统、跨领域协同需求。\n\n多源数据、专业知识、预测模型与持续监测和智能服务需求增长；数据、知识、模型和专业能力分散于不同主体、系统与安全域，目录、口径、接口、标准、授权和版本尚未完全统一，协同成本较高。\n\n协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求。",
            onscreen="行业基础\n需求升级\n建设要求",
            module_titles=("行业基础", "需求升级", "建设要求"),
        )

        self.assertIn("ONSCREEN_RELATION_CARRIER_MISSING", {item["code"] for item in issues})

    def test_current_state_node_cannot_disappear_from_onscreen_projection(self) -> None:
        page = _p04_page()
        page["page_logic_contract"]["onscreen_projection"] = [
            item
            for item in page["page_logic_contract"]["onscreen_projection"]
            if "constraint" not in item.get("node_ids", [])
        ]

        codes = {issue["code"] for issue in validate_page_logic_contract(page)}

        self.assertIn("ONSCREEN_ARGUMENT_NODE_MISSING", codes)

    def test_ordered_phrase_chain_passes_when_signal_remains_visible(self) -> None:
        page = _p04_page()
        issues = validate_authored_page_logic(
            page,
            prose="完整产业链覆盖生产、传输、消费及相关服务。\n\n数字化、市场化、智能化持续提升跨主体、跨系统、跨领域协同需求。\n\n多源数据、专业知识、预测模型与持续监测和智能服务需求增长；数据、知识、模型和专业能力分散于不同主体、系统与安全域，目录、口径、接口、标准、授权和版本尚未完全统一，协同成本较高。\n\n协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求。",
            onscreen="行业基础：完整产业链\n协同需求升级：数字化、市场化、智能化→跨主体、跨系统、跨领域协同需求\n业务服务需求：多源数据、专业知识、预测模型；持续监测和智能服务\n资源协同现状：数据、知识、模型和专业能力分散于不同主体、系统与安全域；目录、口径、接口、标准、授权和版本尚未完全统一，协同成本较高\n建设基础：协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求",
            module_titles=("行业基础", "协同需求升级", "资源协同现状", "建设基础"),
        )

        self.assertEqual([], issues)

    def test_integrated_landing_can_carry_a_relation_without_a_fake_module(self) -> None:
        page = _p04_page()
        page["page_logic_contract"]["onscreen_projection"][-1] = {
            "node_ids": ["requirement"],
            "edge_ids": ["e2", "e3"],
            "carrier": "协同需求增长与资源协同现状",
            "carrier_mode": "integrated_landing",
            "relation_signal": "共同提出",
            "onscreen_signals": [
                "协同需求增长与资源协同现状共同提出",
                "资源连接、可信使用、产品组织和持续服务的基础要求",
                "规模化服务机制",
            ],
        }

        issues = validate_authored_page_logic(
            page,
            prose="完整产业链覆盖生产、传输、消费及相关服务。\n\n数字化、市场化、智能化持续提升跨主体、跨系统、跨领域协同需求。\n\n多源数据、专业知识、预测模型与持续监测和智能服务需求增长；数据、知识、模型和专业能力分散于不同主体、系统与安全域，目录、口径、接口、标准、授权和版本尚未完全统一，协同成本较高。\n\n规模化服务机制仍需完善；协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求。",
            onscreen="行业基础：完整产业链\n协同需求升级：数字化、市场化、智能化→跨主体、跨系统、跨领域协同需求\n业务服务需求：多源数据、专业知识、预测模型；持续监测和智能服务\n资源协同现状：数据、知识、模型和专业能力分散于不同主体、系统与安全域；目录、口径、接口、标准、授权和版本尚未完全统一，协同成本较高\n规模化服务机制仍需完善。\n协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求。",
            module_titles=("行业基础", "协同需求升级", "业务服务需求", "资源协同现状"),
        )

        self.assertEqual([], issues)

    def test_current_state_fails_when_onscreen_copy_drops_its_decisive_constraints(self) -> None:
        page = _p04_page()
        issues = validate_authored_page_logic(
            page,
            prose="完整产业链覆盖生产、传输、消费及相关服务。\n\n数字化、市场化、智能化持续提升跨主体、跨系统、跨领域协同需求。\n\n多源数据、专业知识、预测模型与持续监测和智能服务需求增长；数据、知识、模型和专业能力分散于不同主体、系统与安全域，目录、口径、接口、标准、授权和版本尚未完全统一，协同成本较高。\n\n协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求。",
            onscreen="行业基础：完整产业链\n协同需求升级：数字化、市场化、智能化→跨主体、跨系统、跨领域协同需求\n业务服务需求：多源数据、专业知识、预测模型；持续监测和智能服务\n资源协同现状：资源分散\n建设基础：协同需求增长与资源协同现状共同提出资源连接、可信使用、产品组织和持续服务的基础要求",
            module_titles=("行业基础", "协同需求升级", "业务服务需求", "资源协同现状", "建设基础"),
        )

        missing = [item for item in issues if item["code"] == "ONSCREEN_ARGUMENT_NODE_MISSING"]
        self.assertTrue(missing)
        self.assertIn("协同成本较高", missing[0]["evidence"])


if __name__ == "__main__":
    unittest.main()
