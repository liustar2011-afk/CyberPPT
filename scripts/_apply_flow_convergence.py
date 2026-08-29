from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def path(rel: str) -> Path:
    return ROOT / rel


def read(rel: str) -> str:
    return path(rel).read_text(encoding="utf-8")


def write(rel: str, text: str) -> None:
    path(rel).write_text(text, encoding="utf-8", newline="\n")


def replace_once(rel: str, old: str, new: str) -> None:
    text = read(rel)
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{rel}: expected one exact match, got {count}\n--- old ---\n{old}")
    write(rel, text.replace(old, new, 1))


def sub_once(rel: str, pattern: str, replacement: str) -> None:
    text = read(rel)
    updated, count = re.subn(pattern, replacement, text, count=1, flags=re.S)
    if count != 1:
        raise RuntimeError(f"{rel}: expected one regex match, got {count}: {pattern}")
    write(rel, updated)


# 1) Restore the current CI break to the intent of the test.  This test checks
# Stage02-readiness preservation; it should not implicitly exercise the new
# self-read density gate.
replace_once(
    "tests/test_content_route.py",
    '''    final = {\n        "slides": [{\n            "id": "P06",\n            "page_type": "content",\n            "title": "推进安排",\n            "core_message": "建设任务需要协同推进。",\n            "full_copy": "协同机制明确各方责任。",\n            "onscreen": [{"heading": "协同推进", "items": ["明确责任分工"]}],\n        }]\n    }\n    assert validate_deck_plan(_plan(page)) == []\n''',
    '''    final = {\n        "deck": {"delivery_mode": "presented"},\n        "slides": [{\n            "id": "P06",\n            "page_type": "content",\n            "title": "推进安排",\n            "core_message": "建设任务需要协同推进。",\n            "full_copy": "协同机制明确各方责任。",\n            "onscreen": [{"heading": "协同推进", "items": ["明确责任分工"]}],\n        }]\n    }\n    assert validate_deck_plan(_plan(page)) == []\n''',
)

# 2) Fix Final Script schema: content_load belongs to each slide, not to the
# slides array schema itself.
schema_path = path("contracts/final-script.schema.json")
schema = json.loads(schema_path.read_text(encoding="utf-8"))
slides_schema = schema["properties"]["slides"]
slides_schema.pop("content_load", None)
slides_schema["items"]["properties"]["content_load"] = {
    "type": "string",
    "enum": ["light", "standard", "dense"],
    "default": "standard",
}
schema_path.write_text(json.dumps(schema, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n")

# 3) Carry content_load through the Markdown authority parser into Stage02.
replace_once(
    "cyberppt/script_quality/models.py",
    '''    top_level_module_titles: tuple[str, ...] = ()\n    subtitle: str = ""\n    visual_proof: str = ""\n''',
    '''    top_level_module_titles: tuple[str, ...] = ()\n    subtitle: str = ""\n    content_load: str = "standard"\n    visual_proof: str = ""\n''',
)
replace_once(
    "cyberppt/script_quality/parsing.py",
    '''    "页面使命",\n    "副标题",\n    "核心结论",\n''',
    '''    "页面使命",\n    "副标题",\n    "内容负载",\n    "核心结论",\n''',
)
replace_once(
    "cyberppt/script_quality/parsing.py",
    '''                title=fields.get("页面标题", heading).strip(),\n                subtitle=fields.get("副标题", "").strip(),\n                page_mission=fields.get("页面使命", "").strip(),\n''',
    '''                title=fields.get("页面标题", heading).strip(),\n                subtitle=fields.get("副标题", "").strip(),\n                content_load=fields.get("内容负载", "standard").strip() or "standard",\n                page_mission=fields.get("页面使命", "").strip(),\n''',
)

# 4) Stage02 semantic verifier is a validator + render-topology derivation.  It
# must not overwrite Stage01 business_relationships.
sub_once(
    "cyberppt/stage02_handoff.py",
    r'''def _visual_relationship_contract\(\n.*?\n\ndef _page_record''',
    '''def _visual_relationship_contract(\n    raw_relationships: list[dict[str, Any]],\n    proposals: list[dict[str, Any]],\n    verification: dict[str, Any],\n    verified_relationships: list[dict[str, Any]],\n) -> tuple[list[dict[str, Any]], str]:\n    """Keep Stage 01 semantics authoritative at the Stage 02 boundary.\n\n    The verifier may validate proposals and derive a render topology, but it\n    cannot replace the business relationship collection consumed by visual\n    design.  This prevents Stage 02 from becoming a second semantic-authoring\n    pass.  Verified relationships remain available in separate diagnostic /\n    render-guidance fields.\n    """\n\n    _ = proposals, verification, verified_relationships\n    return [dict(item) for item in raw_relationships], "stage01_authoritative"\n\n\ndef _assert_no_authoritative_semantic_rejection(\n    page_id: str, verification: dict[str, Any]\n) -> None:\n    blockers = [\n        item\n        for item in verification.get("verdicts") or []\n        if isinstance(item, dict)\n        and str(item.get("verdict") or "") in {"rejected", "unresolved"}\n        and str(item.get("constraint_authority") or "soft") in {"hard", "strong"}\n    ]\n    if not blockers:\n        return\n    detail = "; ".join(\n        f"{item.get('proposal_id') or '?'}:{item.get('verdict')}:{','.join(item.get('conflict_codes') or [])}"\n        for item in blockers\n    )\n    raise ValueError(\n        f"Stage 02 semantic verification rejected or could not resolve authoritative Stage 01 "\n        f"relationships for {page_id}; return to Stage 01 and repair the relationship contract: {detail}"\n    )\n\n\ndef _page_record''',
)
replace_once(
    "cyberppt/stage02_handoff.py",
    '''    verified_relationships = [\n        dict(item)\n        for item in verification.get("verified_relationships") or []\n        if isinstance(item, dict)\n    ]\n    verified_features = _verified_relationship_features(verified_relationships, page.visual_structure)\n    semantic_topology = resolve_semantic_topology(\n''',
    '''    verified_relationships = [\n        dict(item)\n        for item in verification.get("verified_relationships") or []\n        if isinstance(item, dict)\n    ]\n    _assert_no_authoritative_semantic_rejection(page.page_id, verification)\n    verified_features = _verified_relationship_features(verified_relationships, page.visual_structure)\n    render_topology = resolve_semantic_topology(\n''',
)
replace_once(
    "cyberppt/stage02_handoff.py",
    '''    )\n    explicit_prompt_mode = str(\n        receipt.get("stage02_prompt_mode")\n''',
    '''    )\n    # Compatibility alias: semantic_topology historically named the Stage 02\n    # layout projection.  Keep it while exposing the clearer render_topology.\n    semantic_topology = render_topology\n    explicit_prompt_mode = str(\n        receipt.get("stage02_prompt_mode")\n''',
)
replace_once(
    "cyberppt/stage02_handoff.py",
    '''    action_text = tuple(\n        " ".join(str(item.get(field) or "") for field in ("subject", "relation", "object")).strip()\n        for item in verified_features["actions"]\n        if isinstance(item, dict)\n    )\n    expression = resolve_onscreen_expression(\n        page,\n        page_mission=page_mission,\n        business_relationships=verified_relationships,\n''',
    '''    action_text = tuple(\n        " ".join(str(item.get(field) or "") for field in ("subject", "relation", "object")).strip()\n        for item in upstream_features["actions"]\n        if isinstance(item, dict)\n    )\n    expression = resolve_onscreen_expression(\n        page,\n        page_mission=page_mission,\n        business_relationships=business_relationships,\n''',
)
replace_once(
    "cyberppt/stage02_handoff.py",
    '''        "title": page.title,\n        "subtitle": page.subtitle,\n        "page_mission": page_mission,\n''',
    '''        "title": page.title,\n        "subtitle": page.subtitle,\n        "content_load": page.content_load,\n        "page_mission": page_mission,\n''',
)
replace_once(
    "cyberppt/stage02_handoff.py",
    '''        "verified_business_relationships": verified_relationships,\n        "semantic_topology": semantic_topology,\n        "onscreen_expression": expression,\n''',
    '''        "verified_business_relationships": verified_relationships,\n        "semantic_topology": semantic_topology,\n        "render_topology": render_topology,\n        "onscreen_expression": expression,\n''',
)
replace_once(
    "cyberppt/stage02_handoff.py",
    '''            "verified_business_relationships": "stage02-semantic-verifier",\n            "semantic_topology": "stage02-topology-resolver",\n            "onscreen_expression_ir": "stage01-author-declared",\n''',
    '''            "verified_business_relationships": "stage02-semantic-verifier",\n            "semantic_topology": "stage02-topology-resolver-compatibility-alias",\n            "render_topology": "stage02-topology-resolver",\n            "content_load": "script-final.md",\n            "onscreen_expression_ir": "stage01-author-declared",\n''',
)
replace_once(
    "cyberppt/stage02_handoff.py",
    '''        "page_mission": page_mission,\n        "core_message": page.main_message,\n        "full_prose": page.full_prose,\n        "argument_chain": page.argument_chain or str(outline.get("argument_chain") or ""),\n''',
    '''        "page_mission": page_mission,\n        "core_message": page.main_message,\n        "full_prose": page.full_prose,\n        "content_load": page.content_load,\n        "argument_chain": page.argument_chain or str(outline.get("argument_chain") or ""),\n''',
)
replace_once(
    "cyberppt/stage02_handoff.py",
    '''        # Compatibility-facing fields contain verified semantics whenever the\n        # upstream relation was inferred or the verifier changed it.\n        "business_relationships": visual_relationships,\n        "stage01_relationship_features": visual_features,\n        # Raw upstream material remains separately auditable.\n        "upstream_business_relationships": business_relationships,\n''',
    '''        # Stage 01 relationships remain semantic authority.  Stage 02 verifier\n        # output is available separately as render guidance and diagnostics.\n        "business_relationships": visual_relationships,\n        "stage01_relationship_features": visual_features,\n        "upstream_business_relationships": business_relationships,\n''',
)
replace_once(
    "cyberppt/stage02_handoff.py",
    '''        "verified_relationship_features": verified_features,\n        "semantic_topology": semantic_topology,\n        "relationship_authority": visual_relationship_source,\n''',
    '''        "verified_relationship_features": verified_features,\n        "semantic_topology": semantic_topology,\n        "render_topology": render_topology,\n        "relationship_authority": visual_relationship_source,\n''',
)

# 5) Visual-structure design explicitly consumes page load and the derived
# render topology, while keeping business relationships as the semantic truth.
replace_once(
    "cyberppt/visual_stage/execution.py",
    '''                "semantic_context": page.get("full_prose"),\n                "argument_chain": page.get("argument_chain"),\n                "prompt_mode": page.get("prompt_mode") or "semantic_brief",\n''',
    '''                "semantic_context": page.get("full_prose"),\n                "content_load": visual.get("content_load") or page.get("content_load") or "standard",\n                "argument_chain": page.get("argument_chain"),\n                "prompt_mode": page.get("prompt_mode") or "semantic_brief",\n''',
)
replace_once(
    "cyberppt/visual_stage/execution.py",
    '''                "business_relationships": business_relationships,\n                "stage01_relationship_features": visual.get("stage01_relationship_features") or {},\n                "relationship_authority": "business_relationships",\n''',
    '''                "business_relationships": business_relationships,\n                "stage01_relationship_features": visual.get("stage01_relationship_features") or {},\n                "render_topology": visual.get("render_topology") or visual.get("semantic_topology") or {},\n                "semantic_verification": visual.get("semantic_verification") or {},\n                "relationship_authority": "business_relationships",\n''',
)
replace_once(
    "cyberppt/visual_stage/execution.py",
    '''            "relationship_policy": (\n                "business_relationships is authoritative; author_visual_notes is advisory only "\n                "and must never be copied into decision_relationship"\n            ),\n''',
    '''            "relationship_policy": (\n                "business_relationships is Stage 01 semantic authority; render_topology is Stage 02-derived "\n                "layout guidance only and must not rewrite business nodes or edges; author_visual_notes is "\n                "advisory only and must never be copied into decision_relationship"\n            ),\n''',
)
replace_once(
    "cyberppt/visual_stage/execution.py",
    '''    if reuse_current_handoff:\n        if not handoff.is_file():\n            raise FileNotFoundError("reuse_current_handoff requires an existing Stage 02 handoff")\n        from cyberppt.stage02_handoff import audit_stage02_handoff\n\n        report = audit_stage02_handoff(project)\n        if report.get("status") != "passed":\n            codes = ", ".join(\n                item.get("code", "HANDOFF_INVALID")\n                for item in report.get("blocking_issues", [])\n            )\n            raise ValueError(f"reuse_current_handoff requires a current Stage 02 handoff: {codes}")\n    else:\n        report = prepare_stage02_handoff(project, script=script)\n        if report.get("status") != "passed":\n            raise ValueError("Stage 01 to Stage 02 handoff is not passed")\n''',
    '''    from cyberppt.stage02_handoff import audit_stage02_handoff\n\n    if reuse_current_handoff:\n        if not handoff.is_file():\n            raise FileNotFoundError("reuse_current_handoff requires an existing Stage 02 handoff")\n        report = audit_stage02_handoff(project)\n        if report.get("status") != "passed":\n            codes = ", ".join(\n                item.get("code", "HANDOFF_INVALID")\n                for item in report.get("blocking_issues", [])\n            )\n            raise ValueError(f"reuse_current_handoff requires a current Stage 02 handoff: {codes}")\n    else:\n        # Avoid rebuilding an already-current handoff.  If the script copy or\n        # any binding changed, audit_stage02_handoff fails and we regenerate.\n        report = audit_stage02_handoff(project) if handoff.is_file() else {"status": "missing"}\n        if report.get("status") != "passed":\n            report = prepare_stage02_handoff(project, script=script)\n            if report.get("status") != "passed":\n                raise ValueError("Stage 01 to Stage 02 handoff is not passed")\n''',
)

# 6) Bind the audited full image as the immutable visual source for editable
# reconstruction.  This is a source binding, not an assertion that later PPTX
# rendering QA has already passed.
insert_after = '''def normalize_audited_manifest_images(manifest: dict[str, Any]) -> None:\n'''
image_stage_text = read("cyberppt/stage02_production/image_stage.py")
if insert_after not in image_stage_text:
    raise RuntimeError("image_stage.py: normalize function marker missing")
# Insert the helper immediately before _failed_text_audit_image_path to keep
# normalization and binding utilities together.
replace_once(
    "cyberppt/stage02_production/image_stage.py",
    '''\n\ndef _failed_text_audit_image_path(output_path: Path, attempt: int) -> Path:\n''',
    '''\n\ndef bind_reconstruction_visual_sources(manifest: dict[str, Any]) -> list[dict[str, Any]]:\n    """Bind text-audited full images as immutable visual truth for reconstruction.\n\n    The editable branch may decompose, clean text regions and rebuild native\n    text, but it must not silently switch to a different visual composition.\n    The SHA binding makes that source explicit and invalidates downstream reuse\n    when the audited full image changes.\n    """\n\n    bound: list[dict[str, Any]] = []\n    for pair in manifest.get("pairs", []):\n        if not isinstance(pair, dict):\n            continue\n        full = pair.get("full") if isinstance(pair.get("full"), dict) else None\n        if full is None:\n            continue\n        audit = full.get("text_audit") if isinstance(full.get("text_audit"), dict) else None\n        full_path = Path(str(full.get("path") or ""))\n        if audit is None or audit.get("valid") is not True or not full_path.is_file():\n            continue\n        binding = {\n            "authority": "audited_full_image",\n            "path": str(full_path),\n            "sha256": sha256(full_path.read_bytes()).hexdigest(),\n            "immutable_visual_composition": True,\n        }\n        full["reconstruction_visual_source"] = binding\n        bound.append({"page_number": pair.get("page_number"), **binding})\n    manifest["visual_truth_policy"] = {\n        "authority": "audited_full_image",\n        "scope": "editable_reconstruction",\n        "rule": "downstream reconstruction may decompose or rebuild text but must not redesign the accepted visual composition",\n        "bound_pages": [item.get("page_number") for item in bound],\n    }\n    return bound\n\n\ndef _failed_text_audit_image_path(output_path: Path, attempt: int) -> Path:\n''',
)
replace_once(
    "cyberppt/stage02_production/orchestrator.py",
    '''from .image_stage import normalize_audited_manifest_images, run_image_stage\n''',
    '''from .image_stage import bind_reconstruction_visual_sources, normalize_audited_manifest_images, run_image_stage\n''',
)
replace_once(
    "cyberppt/stage02_production/orchestrator.py",
    '''        normalize_audited_manifest_images(images.manifest)\n        write_json(manifest.manifest_path, images.manifest)\n        require_generated(images.manifest)\n''',
    '''        normalize_audited_manifest_images(images.manifest)\n        require_generated(images.manifest)\n        bind_reconstruction_visual_sources(images.manifest)\n        write_json(manifest.manifest_path, images.manifest)\n''',
)

# 7) Focused regression tests for the new cross-stage contracts.
new_test = r'''from __future__ import annotations

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


def _script_page(*, content_load: str = "standard", relation: dict | None = None) -> ScriptPage:
    receipt = {"content_relations": [relation]} if relation is not None else None
    return ScriptPage(
        page_id="p01",
        sequence=1,
        heading="",
        page_type="content",
        title="推进安排",
        main_message="建设任务需要协同推进。",
        full_prose="协同机制明确各方责任。",
        selection_notes="",
        evidence_map="",
        evidence_map_refs=(),
        source_refs=(),
        boundary_source_refs=(),
        boundary="",
        visual_structure="A → B",
        onscreen_text="协同推进：明确责任分工",
        module_titles=("协同推进",),
        content_load=content_load,
        contract_receipt=receipt,
    )


def test_final_script_schema_places_content_load_on_slide_items() -> None:
    schema = json.loads((ROOT / "contracts" / "final-script.schema.json").read_text(encoding="utf-8"))
    assert "content_load" not in schema["properties"]["slides"]
    assert schema["properties"]["slides"]["items"]["properties"]["content_load"]["default"] == "standard"

    payload = {
        "contract": "cyberppt.final-script",
        "version": "1.0",
        "deck": {"title": "测试", "communication_goal": "测试跨阶段契约"},
        "slides": [{
            "id": "P1",
            "page_type": "content",
            "title": "推进安排",
            "mission": "说明推进安排",
            "core_message": "形成协同机制",
            "onscreen": [{"heading": "协同推进", "text": "明确责任分工"}],
            "content_load": "dense",
        }],
    }
    validator = Draft202012Validator(schema)
    assert list(validator.iter_errors(payload)) == []
    invalid = copy.deepcopy(payload)
    invalid["slides"][0]["content_load"] = "oversized"
    errors = list(validator.iter_errors(invalid))
    assert any(list(error.path) == ["slides", 0, "content_load"] for error in errors)


def test_markdown_parser_preserves_content_load() -> None:
    document = parse_script_markdown(
        "## P01 推进安排\n"
        "- 页面类型：内容页\n"
        "- 页面标题：推进安排\n"
        "- 内容负载：dense\n"
        "- 核心结论：建设任务需要协同推进。\n"
        "\n### 完整文字稿\n\n协同机制明确各方责任。\n"
        "\n### 上屏文字\n\n- 协同推进：明确责任分工\n"
    )
    assert document.pages[0].content_load == "dense"


def test_stage02_handoff_propagates_content_load() -> None:
    record = _page_record(_script_page(content_load="dense"), None)
    assert record["content_load"] == "dense"
    assert record["stage02_visual_input"]["content_load"] == "dense"


def test_stage02_verifier_does_not_replace_stage01_business_relationships() -> None:
    relation = {
        "subject": "A",
        "relation": "semantic_association",
        "objects": ["B"],
        "direction": "subject_to_objects",
        "basis": "inferred",
    }
    record = _page_record(_script_page(relation=relation), None)
    visual = record["stage02_visual_input"]
    assert visual["business_relationships"][0]["relation"] == "semantic_association"
    assert visual["verified_business_relationships"][0]["relation"] == "directed_relation"
    assert visual["relationship_authority"] == "stage01_authoritative"
    assert visual["render_topology"] == visual["semantic_topology"]


def test_stage02_blocks_rejected_authoritative_stage01_relationship() -> None:
    relation = {
        "subject": "A",
        "relation": "peer_classification",
        "objects": ["B", "C"],
        "direction": "subject_to_objects",
        "basis": "source_explicit",
        "authority": "source_explicit",
        "confidence": 0.98,
        "source_refs": ["S001"],
    }
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
        manifest = {
            "pairs": [{
                "page_number": 1,
                "full": {
                    "path": str(full_path),
                    "text_audit": {"valid": True},
                },
            }]
        }
        bound = bind_reconstruction_visual_sources(manifest)
        source = manifest["pairs"][0]["full"]["reconstruction_visual_source"]
        assert bound[0]["page_number"] == 1
        assert source["authority"] == "audited_full_image"
        assert source["immutable_visual_composition"] is True
        assert len(source["sha256"]) == 64
        assert manifest["visual_truth_policy"]["bound_pages"] == [1]
'''
write("tests/test_flow_convergence_contracts.py", new_test)

# 8) Documentation / skill language follows the same authority boundaries.
replace_once(
    "docs/CYBERPPT_WORKFLOW.md",
    '''运行 `prepare-stage02-handoff`，核对当前最终脚本、项目绑定、脚本版本和页面范围。脚本发生变化后，必须重新生成 handoff，不得沿用旧绑定。\n''',
    '''运行 `prepare-stage02-handoff`，核对当前最终脚本、项目绑定、脚本版本和页面范围。脚本发生变化后，必须重新生成 handoff，不得沿用旧绑定。`business_relationships` 由 Stage 01 锁定并保持语义权威；Stage 02 semantic verifier 只负责校验，并可生成独立的 `render_topology` 作为视觉布局推导。对于 hard/strong 权威关系，出现 rejected 或 unresolved 时 handoff 直接阻断并返回 Stage 01 修复，Stage 02 不得改写关系后继续。`content_load` 从 Final Script 原样进入 handoff 和视觉设计输入，用于控制阅读型页面的信息承载。\n''',
)
replace_once(
    "docs/CYBERPPT_WORKFLOW.md",
    '''1. 生成并审计 full 图，作为可见表面与文字对照证据；\n2. 从 full 图准备无文字底图，清除计划以 SVG 原生文字重建的区域；\n3. 当前 Codex 主 Agent 直接查看归一化 full 图、无字底图、锁定上屏文字和已注册局部图层，在同一画布坐标系中编写完整 authored SVG；缺少 authored SVG 时生产编排停在该页，完成编写后用同一 build 续跑；\n''',
    '''1. 生成并审计 full 图；通过文字审计的 full 图在 manifest 中写入 `reconstruction_visual_source` 的 SHA-256 绑定，作为后续可编辑重建的视觉真相源。后续阶段可以拆层、清字和重建原生文字，不得重新设计已接受的视觉构图；\n2. 从 full 图准备无文字底图，清除计划以 SVG 原生文字重建的区域；\n3. 当前 Codex 主 Agent 直接查看已绑定的归一化 full 图、无字底图、锁定上屏文字和已注册局部图层，在同一画布坐标系中编写完整 authored SVG；该步骤属于高保真重建，不承担第二轮视觉设计。缺少 authored SVG 时生产编排停在该页，完成编写后用同一 build 续跑；\n''',
)
replace_once(
    ".agents/skills/cyberppt-stage02-editable-pptx/SKILL.md",
    '''Default chain: audited full image → text-free base → high-fidelity authored SVG →\nvendored Quick assembly → render and final-visible-text QA.\n''',
    '''Default chain: audited full image → immutable reconstruction visual-source binding →\ntext-free base → high-fidelity authored SVG reconstruction → vendored Quick assembly →\nrender and final-visible-text QA. The audited full image is the visual truth for the\neditable reconstruction; authored SVG may reconstruct and decompose it but must not\nintroduce a second visual design.\n''',
)
replace_once(
    ".agents/skills/cyberppt-stage02-editable-pptx/SKILL.md",
    '''The current Codex main agent owns this authoring step, matching the source Quick\nworkflow: inspect the normalized full image, clean base, locked onscreen text and\nregistered local assets, then write the complete page SVG directly on that same\ncanvas. `final-script-pages` prepares and validates the workspace; if an\n''',
    '''The current Codex main agent owns this reconstruction step, matching the source Quick\nworkflow: inspect the normalized audited full image, clean base, locked onscreen text\nand registered local assets, then reproduce that accepted visual composition as the\ncomplete page SVG on the same canvas. The authored SVG must preserve the bound full\nimage's spatial composition and visual hierarchy; it does not reopen visual design.\n`final-script-pages` prepares and validates the workspace; if an\n''',
)
replace_once(
    "README.md",
    '''- 生成逐页正文内容区 ImageGen 蓝图，用于锁定正文区构图、层级、密度、色板和图表语言；标题、副标题和公共模板元素由模板/可编辑文字层生成。\n- 使用“复杂视觉保真 + 主要文字可编辑”的混合还原策略生成 PPTX。\n- 第三阶段只使用已审计 full 图 → 可编辑 SVG → 原生 PPTX 的重建链。每页先盘点可还原区域和注册图层；未验证的数据图、标识或文字必须标记 `manual_required` 并阻断交付，禁止以整页截图蒙版回退。\n''',
    '''- 根据逐页脚本生成完整正文视觉稿，锁定页面主体的构图、层级、密度、色板和图表语言。\n- 使用“完整图视觉保真 + 原生文字/形状可编辑”的重建策略生成 PPTX。\n- 第三阶段只使用已审计 full 图 → 可编辑 SVG → 原生 PPTX 的重建链。通过审计的 full 图写入 SHA-256 视觉来源绑定，作为后续可编辑重建的视觉真相；SVG 阶段负责高保真复刻和拆层，不重新设计页面。每页先盘点可还原区域和注册图层；未验证的数据图、标识或文字必须标记 `manual_required` 并阻断交付，禁止以整页截图蒙版回退。\n''',
)
replace_once(
    "README.md",
    '''关键原则：`结构可编辑` 和 `视觉还原` 是同等硬门槛；`strict QA` 通过不等于视觉合格；ImageGen 蓝图是参考，不是最终 PPT 背景。\n''',
    '''关键原则：`结构可编辑` 和 `视觉还原` 是同等硬门槛；`strict QA` 通过不等于视觉合格；通过审计并完成来源绑定的 full 图是可编辑重建的视觉真相，后续拆层不得改变其已接受的视觉构图。\n''',
)
replace_once(
    "README.md",
    '''git clone https://github.com/crazyykhllc-bit/CyberPPT.git CyberPPT\n''',
    '''git clone https://github.com/liustar2011-afk/CyberPPT.git CyberPPT\n''',
)

# 9) Restore the normal workflow and remove this bootstrap helper from the final diff.
write(
    ".github/workflows/tests.yml",
    '''name: CyberPPT tests\n\non:\n  pull_request:\n  push:\n    branches:\n      - main\n\njobs:\n  test:\n    runs-on: ubuntu-latest\n    strategy:\n      fail-fast: false\n      matrix:\n        python-version: ["3.10", "3.12"]\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with:\n          python-version: ${{ matrix.python-version }}\n          cache: pip\n      - name: Install package and test dependencies\n        run: |\n          python -m pip install --upgrade pip\n          python -m pip install -e ".[test]"\n      - name: Environment check\n        run: |\n          python -m pip check\n          python -m pytest --version\n      - name: Run test suite\n        run: python -m pytest -q\n''',
)
Path(__file__).unlink()
