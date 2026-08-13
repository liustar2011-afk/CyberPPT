from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from cyberppt.commands.init_project import init_project
from cyberppt.semantic_understanding import (
    SEMANTIC_ARGUMENT_MODEL,
    SEMANTIC_ARTIFACT,
    SEMANTIC_STAGE,
    prepare_semantic_understanding,
    run_semantic_understanding_audit,
)
from cyberppt.source_document_map import prepare_source_map


SEMANTIC_AUDIT_JSON = SEMANTIC_STAGE / "semantic-understanding-audit.json"
SEMANTIC_AUDIT_MD = SEMANTIC_STAGE / "semantic-understanding-audit.md"


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

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_lightweight_prepare_reads_existing_source_map_without_control_writes(self) -> None:
        lightweight = Path(self.temp.name) / "lightweight"
        init_project(lightweight)
        (lightweight / "source" / "material.txt").write_text(
            "source-native business relation and operating arrangement",
            encoding="utf-8",
        )
        prepare_source_map(lightweight)
        before = sorted(
            path.relative_to(lightweight).as_posix()
            for path in lightweight.rglob("*")
            if path.is_file()
        )

        payload = prepare_semantic_understanding(lightweight)
        after = sorted(
            path.relative_to(lightweight).as_posix()
            for path in lightweight.rglob("*")
            if path.is_file()
        )

        self.assertEqual(before, after)
        self.assertEqual("lightweight", payload["mode"])
        self.assertIn("source-native business relation", payload["authoring_task"])
        self.assertIn("author_purpose", payload["authoring_task"])
        self.assertIn("argument_method", payload["authoring_task"])
        self.assertIn("heading_semantic_cards", payload["authoring_task"])
        self.assertIn("concept_occurrence_graph", payload["authoring_task"])
        self.assertIn("source_gaps", payload["authoring_task"])
        self.assertNotIn("source_bundle_sha256", payload["authoring_task"])
        self.assertFalse((lightweight / SEMANTIC_ARTIFACT).exists())

    def test_lightweight_semantic_check_keeps_substantive_rules_without_receipt_files(self) -> None:
        lightweight = Path(self.temp.name) / "lightweight-audit"
        init_project(lightweight)
        (lightweight / "source" / "material.txt").write_text(
            "structured source material", encoding="utf-8"
        )
        prepare_source_map(lightweight)
        artifact = lightweight / SEMANTIC_ARTIFACT
        artifact.write_text(VALID_SEMANTIC, encoding="utf-8")

        code, report = run_semantic_understanding_audit(lightweight)
        codes = {item["code"] for item in report["issues"]}

        self.assertEqual(4, code)
        self.assertIn("SEMANTIC_ARGUMENT_MODEL_MISSING", codes)
        self.assertIn("SEMANTIC_INTERPRETATION_MODE_REQUIRED", codes)
        self.assertNotIn("SEMANTIC_GENERATION_RECEIPT_MISSING", codes)
        self.assertEqual("lightweight", report["mode"])
        self.assertFalse(any(key.endswith("sha256") for key in report))
        self.assertFalse((lightweight / SEMANTIC_AUDIT_JSON).exists())
        self.assertFalse((lightweight / SEMANTIC_AUDIT_MD).exists())
        self.assertFalse((lightweight / SEMANTIC_ARGUMENT_MODEL).exists())


if __name__ == "__main__":
    unittest.main()
