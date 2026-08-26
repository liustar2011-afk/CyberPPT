"""Content-structure fidelity regression against a real, historical project.

This module runs the current Content Integrity Contract (P0), cross-root /
detail-promotion guards (P1), and root-module-preserving semantic grouping
(P2) against a real production deck --
``projects/power-data-infrastructure-cooperation-v16-20260815-foundation`` --
using its actual ``script-final.md`` and Stage 01 outputs (rebuilt fresh with
current code) paired with its actual, historical, *unmodified*
``visual/visual-design-decisions.json``.

The project directory is only ever read; a temporary copy of the script and
Stage 01 outputs is used to rebuild a current-code Stage 02 handoff, exactly
as ``cyberppt.commands.visual_structure_stage`` would for a live run.

Two things are being verified here that no synthetic fixture can prove as
convincingly:

1. Pages whose historical Visual Designer decision happens to respect root
   module boundaries compile cleanly, and their root-module count survives
   unchanged all the way into ``FinalPromptIR.semantic_groups`` (P2's core
   promise).
2. Pages whose historical decision does NOT respect root module boundaries
   are now caught by ``CONTENT_CROSS_ROOT_GROUPING`` -- turning a real,
   previously undetected structural defect (confirmed by reading the
   author's own "锚点覆盖说明" annotations, which explicitly call out these
   trailing boundary sentences as deliberately independent of the modules
   above them) into a permanent regression test.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from cyberppt.artifact_ledger import write_json_atomic
from cyberppt.commands.visual_structure_stage import (
    _build_executable_page,
    _write_visual_design_input,
)
from cyberppt.page_artifact_spec import build_page_artifact_spec
from cyberppt.stage02_handoff import HANDOFF_JSON, audit_stage02_handoff, build_stage02_handoff
from scripts.imagegen_pipeline.artifact_prompt import build_final_prompt_ir

PROJECT = Path(__file__).resolve().parents[1] / "projects" / (
    "power-data-infrastructure-cooperation-v16-20260815-foundation"
)
STYLE_LOCK = PROJECT / "workbench" / "locks" / "visual_style_lock.json"

# Pages whose historical (pre-P1) Visual Designer decision merges locked
# text from more than one root content module into a single evidence unit.
# Confirmed by reading the source script: every one of these pages ends with
# a zero-indent boundary/cross-cutting sentence that the script author's own
# "锚点覆盖说明" annotation explicitly separates from the numbered modules
# above it (e.g. P06's "已从④模块下移出避免暗示虚假从属关系"). The historical
# decision re-merged what the author deliberately kept apart.
#
# This is a real, measured baseline, not an aspiration -- if it shrinks,
# someone re-ran Visual Structure Designer for that page (good; update the
# baseline). If it grows, a change introduced a new structural regression.
KNOWN_CROSS_ROOT_VIOLATIONS = frozenset(
    {
        "p06", "p07", "p10", "p11", "p12", "p15", "p16",
        "p17", "p20", "p23", "p24", "p26", "p27", "p29",
    }
)


def _rebuild_design_input_and_decisions() -> tuple[dict, dict, dict]:
    """Rebuild a fresh design-input (with current-code content_integrity)
    from the real project's script + Stage 01 outputs, paired with the real
    project's unmodified historical Visual Designer decisions.

    Returns (handoff_by_id, design_input_by_id, decisions_by_id).
    """

    with tempfile.TemporaryDirectory() as directory:
        tmp = Path(directory) / "project"
        (tmp / "workbench" / "stages" / "01-analysis").mkdir(parents=True)
        shutil.copy(
            PROJECT / "workbench/stages/01-analysis/outline.json",
            tmp / "workbench/stages/01-analysis/outline.json",
        )
        shutil.copy(
            PROJECT / "workbench/stages/01-analysis/source-truth.json",
            tmp / "workbench/stages/01-analysis/source-truth.json",
        )
        (tmp / "workbench" / "scripts" / "final").mkdir(parents=True)
        script_path = tmp / "workbench/scripts/final/script-final.md"
        shutil.copy(PROJECT / "workbench/scripts/final/script-final.md", script_path)

        payload = build_stage02_handoff(tmp, script=script_path)
        audit = audit_stage02_handoff(tmp, payload)
        assert audit["status"] == "passed", audit["blocking_issues"]

        handoff_path = tmp / HANDOFF_JSON
        handoff_path.parent.mkdir(parents=True, exist_ok=True)
        write_json_atomic(handoff_path, payload)

        design_input_path = _write_visual_design_input(tmp, handoff_path)
        design_input = json.loads(design_input_path.read_text(encoding="utf-8"))

    handoff_by_id = {str(page["page_id"]).lower(): page for page in payload["pages"]}
    design_input_by_id = {page["page_id"]: page for page in design_input["pages"]}
    decisions = json.loads(
        (PROJECT / "visual/visual-design-decisions.json").read_text(encoding="utf-8")
    )
    decisions_by_id = {page["page_id"]: page for page in decisions["pages"]}
    return handoff_by_id, design_input_by_id, decisions_by_id


@unittest.skipUnless(PROJECT.is_dir(), "reference project not present in this checkout")
class RealProjectContentStructureRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.handoff_by_id, cls.design_input_by_id, cls.decisions_by_id = (
            _rebuild_design_input_and_decisions()
        )

    def test_compliant_pages_preserve_root_module_count_into_final_prompt(self) -> None:
        # p04/p05/p31 correspond to the architecture plan's regression
        # scenarios (multi-factor convergence, root+detail non-promotion,
        # six-step flow); their historical decisions respect root module
        # boundaries and must keep compiling, with the final prompt's
        # semantic group count matching the page's root module count exactly
        # -- proof, on real data, that P2 no longer collapses root modules.
        for page_id in ("p04", "p05", "p31"):
            with self.subTest(page_id=page_id):
                source = self.design_input_by_id[page_id]
                decision = self.decisions_by_id[page_id]
                page_spec = _build_executable_page(source, decision)

                root_nodes = (source.get("content_integrity") or {}).get("root_nodes") or []
                self.assertGreater(len(root_nodes), 0)

                spec = build_page_artifact_spec(
                    handoff_page=self.handoff_by_id[page_id],
                    visual_page=page_spec,
                    style_lock=STYLE_LOCK,
                    handoff_sha256="a" * 64,
                    visual_source_sha256="b" * 64,
                )
                self.assertEqual(len(root_nodes), spec.content_root_count)
                ir = build_final_prompt_ir(spec)
                self.assertEqual(len(root_nodes), len(ir.semantic_groups))

    def test_historically_violating_pages_are_now_blocked(self) -> None:
        # P06 and P12 merge a trailing, author-designated-independent
        # boundary sentence into an adjacent numbered module -- exactly the
        # "false subordination" the script's own 锚点覆盖说明 warns against.
        for page_id in ("p06", "p12", "p17"):
            with self.subTest(page_id=page_id):
                source = self.design_input_by_id[page_id]
                decision = self.decisions_by_id[page_id]
                with self.assertRaisesRegex(ValueError, "cross-root grouping is forbidden"):
                    _build_executable_page(source, decision)

    def test_full_deck_cross_root_violation_baseline(self) -> None:
        # Deck-wide sweep (all 23 content pages with a recorded decision),
        # not just the six sampled above. This is the honest, measured
        # picture: cross-root merging turns out to be a deck-wide historical
        # pattern (the author consistently wrote trailing boundary sentences
        # at zero indent, deliberately separate from the modules above), not
        # an isolated defect in one or two pages.
        violations: set[str] = set()
        clean: set[str] = set()
        for page_id in sorted(self.design_input_by_id):
            decision = self.decisions_by_id.get(page_id)
            if decision is None:
                continue
            source = self.design_input_by_id[page_id]
            try:
                _build_executable_page(source, decision)
            except ValueError as exc:
                if "cross-root grouping is forbidden" in str(exc):
                    violations.add(page_id)
                else:
                    raise
            else:
                clean.add(page_id)

        self.assertEqual(KNOWN_CROSS_ROOT_VIOLATIONS, violations)
        self.assertEqual(set(self.decisions_by_id) - KNOWN_CROSS_ROOT_VIOLATIONS, clean)

    def test_full_deck_handoff_passes_content_integrity_audit(self) -> None:
        # Root/parent-child/source-order fidelity = 100% (P0's hash-verified
        # guarantee), anchored against the full real deck rather than only
        # synthetic pages.
        with tempfile.TemporaryDirectory() as directory:
            tmp = Path(directory) / "project"
            (tmp / "workbench" / "stages" / "01-analysis").mkdir(parents=True)
            shutil.copy(
                PROJECT / "workbench/stages/01-analysis/outline.json",
                tmp / "workbench/stages/01-analysis/outline.json",
            )
            shutil.copy(
                PROJECT / "workbench/stages/01-analysis/source-truth.json",
                tmp / "workbench/stages/01-analysis/source-truth.json",
            )
            (tmp / "workbench" / "scripts" / "final").mkdir(parents=True)
            script_path = tmp / "workbench/scripts/final/script-final.md"
            shutil.copy(PROJECT / "workbench/scripts/final/script-final.md", script_path)

            payload = build_stage02_handoff(tmp, script=script_path)
            report = audit_stage02_handoff(tmp, payload)

        self.assertEqual("passed", report["status"])
        self.assertEqual([], report["blocking_issues"])


if __name__ == "__main__":
    unittest.main()
