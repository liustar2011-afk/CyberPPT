from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.imagegen_pipeline.build_transaction import (
    BuildLock,
    BuildLockError,
    atomic_write_text,
)
from scripts.imagegen_pipeline.prompt_approval import (
    assert_prompt_fresh,
    build_prompt_approval,
)
from scripts.imagegen_pipeline.script_parser import (
    load_page_context_bundle,
    load_page_missions,
)


class P2StructureTest(unittest.TestCase):
    def test_stage01_context_is_loaded_once_and_filtered(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            outline = project / "workbench" / "stages" / "01-analysis" / "outline.json"
            outline.parent.mkdir(parents=True)
            outline.write_text(
                json.dumps(
                    {
                        "pages": [
                            {
                                "page_id": "p04",
                                "business_question": "回答服务边界",
                                "visual_center": "行业节点",
                                "visual_intent": {
                                    "visual_intent_type": "boundary_guardrail",
                                    "not_allowed": "ignored",
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            missions, contexts, overrides = load_page_context_bundle(
                project,
                allowed_override_fields={"visual_intent_type"},
            )
            self.assertEqual("回答服务边界", missions["p04"])
            self.assertEqual("行业节点", contexts["p04"]["visual_center"])
            self.assertEqual({"visual_intent_type": "boundary_guardrail"}, overrides["p04"])
            self.assertEqual(missions, load_page_missions(project))

    def test_build_lock_is_exclusive_and_atomic_write_replaces_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "analysis" / "state.json"
            atomic_write_text(target, "first")
            atomic_write_text(target, "second")
            self.assertEqual("second", target.read_text(encoding="utf-8"))
            first = BuildLock(root / ".lock", "build-a").acquire()
            try:
                with self.assertRaises(BuildLockError):
                    BuildLock(root / ".lock", "build-b").acquire()
            finally:
                first.release()
            self.assertFalse((root / ".lock").exists())

    def test_atomic_write_handles_long_target_names(self) -> None:
        """Temporary names must not push Windows delivery paths past MAX_PATH."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            deep = root / ("x" * 100)
            deep.mkdir()
            target = deep / (("page_001_" + "长文件名" * 20 + ".svg"))
            atomic_write_text(target, "<svg/>")
            self.assertEqual("<svg/>", target.read_text(encoding="utf-8"))

    def test_prompt_approval_records_hashes_and_stale_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "approved.md"
            approval = build_prompt_approval(
                approved_path=path,
                approved_prompt="approved",
                canonical_prompt="approved",
                consumed_prompt="approved",
            )
            self.assertFalse(approval.stale)
            self.assertEqual(approval.approved_hash, approval.consumed_hash)
            assert_prompt_fresh(approval, page_number=4)
            stale = build_prompt_approval(
                approved_path=path,
                approved_prompt="approved",
                canonical_prompt="changed",
                consumed_prompt="approved",
            )
            self.assertTrue(stale.stale)
            with self.assertRaises(ValueError):
                assert_prompt_fresh(stale, page_number=4)


if __name__ == "__main__":
    unittest.main()
