from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.init_project import init_project
from cyberppt.semantic_understanding import (
    SEMANTIC_ARTIFACT,
    SEMANTIC_MODEL_INPUT,
    approve_semantic_understanding,
    assert_semantic_understanding_ready,
    prepare_semantic_understanding,
    record_semantic_generation,
    run_semantic_understanding_audit,
    semantic_binding_issues,
)


VALID_SEMANTIC = """# 全文语义理解

## 全文业务主语
本材料围绕电力行业数据服务与场景服务运营合作方案，说明基础设施、行业组织和合作企业如何形成运营安排。

## 核心业务对象
业务对象包括电力数据资源、行业数据产品、场景服务以及参与合作的电力骨干企业。

## 空间、时间与服务范围
范围覆盖全国电力行业功能节点及合作企业自身授权范围，区分当前基础、规划建设、合作设想和下一步工作。

## 材料意图与决策动作
受众需要理解现有基础，审议合作方案，并确认调研、场景筛选和后续协同动作。

## 原文结构与论证顺序
原文先介绍基础设施，再规划运营体系，随后提出与骨干企业的合作设想，最后给出下一步建议；四章顺序构成权威一级骨架。

## 现有基础与能力缺口
已经形成的连接和规则能力应与仍在建设的服务运营能力区分；合作范围、资源投入和责任分工仍需调研确认。

## 业务目标与支撑手段
目标是开展行业数据服务与场景服务合作运营；数据、模型、平台工具及组织机制分别承担资源、加工、交付与治理支撑。

## 核心概念语义表
| 原文简称 | 完整含义 | 适用上下文 | 禁止误读 |
|---|---|---|---|
| 行业节点 | 电力领域数据基础设施在国家体系中的行业功能节点 | 行业角色 | 不等同于全部基础设施或运营主体 |

## 跨章节证据链
基础设施介绍提供合作底座证据，运营体系规划说明服务组织方式，合作方案章节将能力映射到企业参与和场景交付。

## 状态、主体与边界
区分已有、在建、规划、合作设想和下一步建议；中电联、数智公司与合作企业分别承担行业治理、运营支撑和自身资源控制责任。

## 待核事项与禁止推断
企业数据授权、投入规模、收益分配和实施时间表需后续确认；不得把规划内容写成既成事实，也不得替合作企业承诺资源。
"""


class SemanticUnderstandingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name) / "project"
        init_project(self.project)
        (self.project / "source" / "material.txt").write_text(
            "structured source material", encoding="utf-8"
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _record_and_audit(self) -> tuple[int, dict[str, object]]:
        record_semantic_generation(
            self.project,
            executor="test-runner",
            model="test-model",
        )
        return run_semantic_understanding_audit(self.project)

    def test_init_creates_required_semantic_gate_and_template(self) -> None:
        manifest = (self.project / "manifest.yml").read_text(encoding="utf-8")
        self.assertIn("semantic_understanding: required", manifest)
        self.assertTrue((self.project / SEMANTIC_ARTIFACT).is_file())

    def test_placeholder_artifact_requires_rewrite(self) -> None:
        code, report = run_semantic_understanding_audit(self.project)
        self.assertEqual(4, code)
        self.assertEqual("rewrite_required", report["status"])
        self.assertTrue(report["issues"])

    def test_prepare_compiles_source_content_into_fixed_model_task(self) -> None:
        payload = prepare_semantic_understanding(self.project)
        model_input = (self.project / SEMANTIC_MODEL_INPUT).read_text(encoding="utf-8")
        self.assertIn("structured source material", model_input)
        self.assertIn("whole-document semantic editor", model_input)
        self.assertEqual(payload["model_input_sha256"], payload["model_input_sha256"].lower())

    def test_passed_gate_becomes_stale_when_source_changes(self) -> None:
        (self.project / SEMANTIC_ARTIFACT).write_text(VALID_SEMANTIC, encoding="utf-8")
        code, report = self._record_and_audit()
        self.assertEqual(0, code)
        self.assertEqual("passed", report["status"])
        with self.assertRaisesRegex(FileNotFoundError, "human approval"):
            assert_semantic_understanding_ready(self.project)
        approve_semantic_understanding(self.project, note="test approval")
        self.assertIsNotNone(assert_semantic_understanding_ready(self.project))

        (self.project / "source" / "material.txt").write_text(
            "changed source material", encoding="utf-8"
        )
        with self.assertRaisesRegex(ValueError, "source materials changed"):
            assert_semantic_understanding_ready(self.project)

    def test_downstream_artifact_must_bind_both_semantic_hashes(self) -> None:
        (self.project / SEMANTIC_ARTIFACT).write_text(VALID_SEMANTIC, encoding="utf-8")
        code, gate = self._record_and_audit()
        self.assertEqual(0, code)

        issues = semantic_binding_issues({}, gate)
        self.assertEqual(
            {
                "SEMANTIC_UNDERSTANDING_NOT_BOUND",
                "SEMANTIC_SOURCE_BUNDLE_NOT_BOUND",
            },
            {item["code"] for item in issues},
        )
        self.assertEqual(
            [],
            semantic_binding_issues(
                {
                    "semantic_understanding_sha256": gate["semantic_understanding_sha256"],
                    "semantic_source_bundle_sha256": gate["source_bundle_sha256"],
                },
                gate,
            ),
        )


if __name__ == "__main__":
    unittest.main()
