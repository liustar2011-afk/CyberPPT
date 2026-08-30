from __future__ import annotations

import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from jsonschema import Draft202012Validator
from PIL import Image

from cyberppt.script_quality.models import ScriptPage
from cyberppt.script_quality.parsing import parse_script_markdown
from cyberppt.stage02_handoff import _page_record
from cyberppt.stage02_production.image_stage import bind_reconstruction_visual_sources


ROOT = Path(__file__).resolve().parents[1]


def _script_page(*, content_load: str = "", relation: dict | None = None) -> ScriptPage:
    receipt = {"content_relations": [relation]} if relation is not None else None
    return ScriptPage(
        page_id="p01", sequence=1, heading="", page_type="content", title="推进安排",
        main_message="建设任务需要协同推进。", full_prose="协同机制明确各方责任。",
        selection_notes="", evidence_map="", evidence_map_refs=(), source_refs=(),
        boundary_source_refs=(), boundary="", visual_structure="A → B",
        onscreen_text="协同推进：明确责任分工", module_titles=("协同推进",),
        content_load=content_load, contract_receipt=receipt,
    )


def test_final_script_schema_places_content_load_on_slide_items() -> None:
    schema = json.loads((ROOT / "contracts" / "final-script.schema.json").read_text(encoding="utf-8"))
    assert "content_load" not in schema["properties"]["slides"]
    assert schema["properties"]["slides"]["items"]["properties"]["content_load"]["default"] == "standard"
    payload = {
        "contract": "cyberppt.final-script", "version": "1.0",
        "deck": {"title": "测试", "communication_goal": "测试跨阶段契约"},
        "slides": [{"id": "P1", "page_type": "content", "title": "推进安排",
                    "mission": "说明推进安排", "core_message": "形成协同机制",
                    "argument": {"pattern": "progression", "chain": ["责任分工", "协同推进"]},
                    "full_copy": "明确责任分工，形成协同推进机制。",
                    "onscreen": [{"heading": "协同推进", "text": "明确责任分工"}],
                    "visual_thesis": "责任分工推动协同机制形成。",
                    "speaker_notes": "重点说明各方责任如何在推进过程中衔接。",
                    "content_load": "dense"}],
    }
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(payload)) == []
    invalid = copy.deepcopy(payload)
    invalid["slides"][0]["content_load"] = "oversized"
    errors = list(validator.iter_errors(invalid))
    assert any(list(error.path) == ["slides", 0, "content_load"] for error in errors)


def test_markdown_parser_preserves_content_load() -> None:
    document = parse_script_markdown(
        "## P01 推进安排\n- 页面类型：内容页\n- 页面标题：推进安排\n"
        "- 内容负载：dense\n- 核心结论：建设任务需要协同推进。\n"
        "\n### 完整文字稿\n\n协同机制明确各方责任。\n"
        "\n### 上屏文字\n\n- 协同推进：明确责任分工\n"
    )
    assert document.pages[0].content_load == "dense"


def test_stage02_handoff_propagates_content_load_and_standard_default() -> None:
    dense = _page_record(_script_page(content_load="dense"), None)
    assert dense["content_load"] == "dense"
    assert dense["stage02_visual_input"]["content_load"] == "dense"
    standard = _page_record(_script_page(), None)
    assert standard["content_load"] == "standard"


def test_stage02_verifier_does_not_replace_stage01_business_relationships() -> None:
    relation = {"subject": "A", "relation": "semantic_association", "objects": ["B"],
                "direction": "subject_to_objects", "basis": "inferred"}
    visual = _page_record(_script_page(relation=relation), None)["stage02_visual_input"]
    assert visual["business_relationships"][0]["relation"] == "semantic_association"
    assert visual["verified_business_relationships"][0]["relation"] == "directed_relation"
    assert visual["relationship_authority"] == "stage01_authoritative"
    assert visual["render_topology"] == visual["semantic_topology"]


def test_stage02_blocks_rejected_authoritative_stage01_relationship() -> None:
    relation = {"subject": "A", "relation": "peer_classification", "objects": ["B", "C"],
                "direction": "subject_to_objects", "basis": "source_explicit",
                "authority": "source_explicit", "confidence": 0.98, "source_refs": ["S001"]}
    try:
        _page_record(_script_page(relation=relation), None)
    except ValueError as exc:
        assert "return to Stage 01" in str(exc)
    else:
        raise AssertionError("authoritative semantic rejection must block Stage 02 handoff")


def test_audited_full_image_is_bound_as_reconstruction_visual_source() -> None:
    with TemporaryDirectory() as directory:
        full_path = Path(directory) / "page-001-full.png"
        Image.new("RGB", (8, 8), "white").save(full_path)
        manifest = {"pairs": [{"page_number": 1, "full": {
            "path": str(full_path), "text_audit": {"valid": True}}}]}
        bound = bind_reconstruction_visual_sources(manifest)
        source = manifest["pairs"][0]["full"]["reconstruction_visual_source"]
        assert bound[0]["page_number"] == 1
        assert source["authority"] == "audited_full_image"
        assert source["immutable_visual_composition"] is True
        assert len(source["sha256"]) == 64
        assert manifest["visual_truth_policy"]["bound_pages"] == [1]
