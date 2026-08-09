"""Compile deterministic Stage 01 authoring inputs."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

from cyberppt.communication_strategy import (
    assert_communication_strategy_ready,
    communication_strategy_binding_issues,
)
from cyberppt.semantic_understanding import (
    SEMANTIC_ARTIFACT,
    SEMANTIC_ARGUMENT_MODEL,
    assert_semantic_understanding_ready,
)
from cyberppt.source_argument_model import load_model
from cyberppt.storyline_director import assert_storyline_director_ready


def _load(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"required artifact does not exist: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"artifact root must be an object: {path}")
    return payload


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().lower()


def _ensure_page_script_authoring(
    project: Path,
    outline_path: Path,
    pages: list[dict[str, object]],
) -> Path:
    """Create an explicit page-authoring contract when a project lacks one.

    The compiler consumes this JSON artifact.  Markdown remains a reviewable
    authoring input, while the JSON carries the exact content-unit consumption
    declaration and the outline binding used for stale-artifact detection.
    """

    path = project / "workbench/scripts/page-script-authoring.json"
    if path.exists():
        return path
    payload = {
        "schema": "cyberppt.page_script_authoring.v1",
        "project": project.name,
        "outline_sha256": _sha256(outline_path),
        "pages": {
            str(page["page_id"]): {
                "prose": "",
                "selection": ["", "", ""],
                "onscreen": "",
                "visual": "",
                "notes": "",
                "consumes": [
                    str(unit["unit_id"])
                    for unit in page.get("content_units", [])
                    if isinstance(unit, dict)
                    and unit.get("role") != "boundary"
                    and unit.get("unit_id")
                ],
            }
            for page in pages
            if page.get("page_id")
        },
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def _records(project: Path) -> dict[str, dict[str, object]]:
    truth = _load(project / "workbench/stages/01-analysis/source-truth.json")
    return {
        str(item.get("id")): item
        for item in truth.get("records", [])
        if isinstance(item, dict) and item.get("id")
    }


def prepare_outline_input(project: Path) -> Path:
    project = project.expanduser().resolve()
    semantic_gate = assert_semantic_understanding_ready(project)
    communication_gate = assert_communication_strategy_ready(project)
    director_gate = assert_storyline_director_ready(project)
    argument_model = None
    if semantic_gate is not None and semantic_gate.get("semantic_argument_model_sha256"):
        argument_model = load_model(project / SEMANTIC_ARGUMENT_MODEL)
    truth = _load(project / "workbench/stages/01-analysis/source-truth.json")
    records = {
        str(item.get("id")): item
        for item in truth.get("records", [])
        if isinstance(item, dict) and item.get("id")
    }
    lines = [
        "# Outline authoring input",
        "",
        "The whole-document semantic understanding below is the authoritative upstream constraint. Do not replace its business subject, source structure, actors, status distinctions, or decision intent with a generic PPT storyline.",
        "The Outline root must copy `semantic_understanding_sha256`, `semantic_source_bundle_sha256`, and, when present, `semantic_source_map_bundle_sha256` from the current semantic gate.",
        "The Outline must also copy `semantic_argument_model_sha256` and consume the source argument model below. Do not rebuild the source thesis from evidence records.",
        "Source Truth is frozen after the Source Truth stage. Set `source_truth_mapping_mode` to `consumption_manifest`; record `source_truth_semantic_sha256` and `source_consumption_semantic_sha256` as the authority bindings, while retaining the corresponding raw SHA-256 fields only as byte receipts. Write page-to-evidence mappings only to the independent `source_consumption_manifest`; never write page assignments back into Source Truth records.",
        "",
        "Before planning pages, preserve the Stage 00 source argument model `document_semantics` and the Source Truth copy: `document_role` says what artifact is being presented; `subject_of_report` says what the presentation is about; `primary_thesis` is the deck-level conclusion; `decision_boundary` limits its maturity; `author_purpose` states what the author is trying to advance; `argument_method` and `supporting_basis` explain how the source argues for that purpose.",
        "Never replace the subject of report with the activity used to produce or present the document. Document role and business subject are separate fields.",
        "Copy `document_semantics` into the outline and set root `narrative_thesis` exactly to its `primary_thesis`.",
        "",
        "Every content page must state one source-supported `core_message`: the smallest complete meaning the page communicates.",
        "A core message may express a fact, composition, relationship, process, scope, boundary, or a source-supported judgment. Boundary is opt-in: B/U records constrain an ordinary page and must not become its semantic center by default.",
        "Set schema to `cyberppt.outline.v2` and root `core_message_derivation_mode` to `required`.",
        "Create the Outline from Source Truth. Use canonical field names when the material calls for them:",
        "required `page_mission`, required `core_message`, optional `onscreen_conclusion`, "
        "required `audience_question`, `must_not_include`, `split_risk`, "
        "`new_value_vs_previous`, `reserved_for_later`, `content_units`, "
        "`visual_intent_type`.",
        "Set root `editorial_control_mode` to `required`.",
        "Set root `storyline_contract_mode` to `required`. Copy `storyline_director_sha256` and the complete `storyline` contract from the current Storyline Director gate exactly.",
        "Set root `semantic_argument_model_mode` to `required`; copy `semantic_argument_model_sha256` exactly from Stage 00.",
        "",
    ]
    if communication_gate is not None:
        selected = communication_gate["selected_option"]
        posture_fields = [
            "frontstage_purpose",
            "backstage_intent",
            "interaction_posture",
            "explicit_audience_action",
            "forbidden_frontstage_frames",
        ]
        lines += [
            "## approved_communication_strategy",
            "",
            "The following human-approved communication strategy determines the Outline structure. Copy every named root field exactly; do not silently choose another audience or reporting direction.",
            f"- communication_strategy_sha256: {communication_gate['communication_strategy_sha256']}",
            f"- communication_strategy_approval_sha256: {communication_gate['communication_strategy_approval_sha256']}",
            f"- audience: {communication_gate['audience']}",
            f"- communication_purpose: {communication_gate['communication_purpose']}",
            f"- decision_task: {communication_gate['decision_task']}",
            f"- reporting_direction: {communication_gate['option_id']}",
            f"- user_decision_id: {communication_gate.get('user_decision_id', '')}",
            f"- architecture_mode: {selected['architecture_mode']}",
            f"- structure_principle: {selected['structure_principle']}",
            *[
                f"- {field}: " + (
                    json.dumps(communication_gate.get(field), ensure_ascii=False)
                    if isinstance(communication_gate.get(field), (list, dict))
                    else str(communication_gate.get(field) or "")
                )
                for field in posture_fields
                if communication_gate.get(field) not in (None, "", [])
            ],
            "- audience_concerns: " + json.dumps(
                communication_gate.get("audience_concerns", []),
                ensure_ascii=False,
            ),
            "",
            "Use `structure_principle` to determine chapter order. Source truth still controls meaning and evidence; the approved strategy controls how that meaning is organized for this audience.",
            "Visible agenda, chapter titles, page titles, audience questions, and closing language must follow `frontstage_purpose` and `explicit_audience_action`. `backstage_intent` is not a visible story beat and must never be turned into an approval request, decision headline, or closing call to action.",
            "Copy all supplied posture fields to the Outline root exactly. None of the literal `forbidden_frontstage_frames` may appear in visible or editorial page fields.",
            "",
        ]
    if director_gate is not None:
        lines += [
            "## authoritative_storyline_director",
            "",
            "The Outline Director has already organized the approved semantic understanding for this audience. It is authoritative only for evidence selection and ordering; it may not replace source subject, source chapter missions, actor roles, status distinctions, or forbidden inferences.",
            f"- storyline_director_sha256: {director_gate['storyline_director_sha256']}",
            "- storyline: " + json.dumps(director_gate["outline_contract"], ensure_ascii=False),
            "",
            "Each content page must add `storyline_role`, `transition_from_previous`, and `transition_to_next`. These fields must explain a source-supported relation; generic wording such as 承上启下 is invalid.",
            "Each content page must add `audience_concern_ids` and `audience_relevance`. Copy only IDs from the approved concern contract and explain why the selected audience needs this page.",
            "Use Source Truth as evidence selected for the page mission, not as a list of page candidates. Full traceability may live in detail_refs without earning on-screen or page-level weight.",
            "",
        ]
    if semantic_gate is not None:
        semantic_text = (project / SEMANTIC_ARTIFACT).read_text(encoding="utf-8-sig")
        lines += [
            "## semantic_gate_binding",
            "",
            f"- semantic_understanding_sha256: {semantic_gate['semantic_understanding_sha256']}",
            f"- semantic_source_bundle_sha256: {semantic_gate['source_bundle_sha256']}",
            f"- semantic_source_map_bundle_sha256: {semantic_gate.get('source_map_bundle_sha256', '')}",
            f"- semantic_argument_model_sha256: {semantic_gate.get('semantic_argument_model_sha256', '')}",
            "",
            "## authoritative_semantic_understanding",
            "",
            semantic_text.rstrip(),
            "",
        ]
        if argument_model is not None:
            lines += [
                "## authoritative_source_argument_model",
                "",
                "This model was completed in Stage 00. Use it to select and organize pages; do not change its document_semantics, thesis, node roles, argument_weight, statuses, relations, MECE basis, or source gaps.",
                json.dumps(argument_model, ensure_ascii=False, indent=2),
                "",
                "Every content page must declare `primary_argument_node_id`, `source_argument_node_ids`, and include the same node IDs in `core_message_derivation.argument_node_ids`.",
                "Every content page must copy `source_argument_node_roles` and `source_argument_node_weights` for its selected nodes. `argument_weight=core` is an authoritative source proposition and must not be replaced by a generic layer label merely because another proposition supports it; relation, role, and weight are separate dimensions.",
                "Each source node needs one primary page consumer or an explicit allowed merge; a source evidence record alone is not a substitute for node consumption.",
                "Do not default to one page per source subsection regardless of how much material that subsection has. Before finalizing the page plan, estimate each candidate page's available source material (roughly, the combined length of the Source Truth statements it would cite). If two or more consecutive subsections in the same chapter are each much thinner than the deck's typical page, merge them into one denser page instead of writing several thin standalone pages — a page that can't be filled from real source material should not exist just because the source document gave that content its own subsection heading. The audit enforces this: `outline-audit` flags `CONTENT_PAGE_DENSITY_LOW` for runs of 2+ consecutive same-chapter pages that fall far below the deck's median page volume, with `retry_strategy: merge_thin_adjacent_pages`.",
                "",
            ]
    semantics = truth.get("document_semantics")
    lines += ["", "## document_semantics", ""]
    lines.append(json.dumps(semantics, ensure_ascii=False) if isinstance(semantics, dict) else "- missing")
    lines += ["", "## coverage_targets", ""]
    for target in truth.get("coverage_targets", []):
        if not isinstance(target, dict):
            continue
        refs = ", ".join(str(item) for item in target.get("record_refs", []))
        lines.append(
            f"- {target.get('id')} [{target.get('priority', '')}] "
            f"{target.get('label', '')}: {refs}"
        )
    lines += ["", "## evidence_records", ""]
    for source_id, record in records.items():
        lines.append(
            f"- {source_id} [{record.get('priority', '')}; "
            f"{record.get('claim_role') or record.get('type', '')}; "
            f"{record.get('status', '')}]: {record.get('statement', '')}"
        )
    lines += ["", "## conclusions", ""]
    for conclusion in truth.get("conclusions", []):
        if isinstance(conclusion, dict):
            lines.append(f"- {json.dumps(conclusion, ensure_ascii=False)}")
    if not truth.get("conclusions"):
        lines.append("- none")
    lines += [
        "",
        "## required_content_page_contract",
        "",
        "Each content page must define its semantic center, evidence, and content structure:",
        "- `page_mission`: required internal editorial responsibility; describe what the page does in the deck, not a claim it must prove",
        "- `audience_question`: required concrete question the audience needs this page to answer; it must not repeat page_mission or use a placeholder such as 本页说明什么",
        "- `business_question`: optional legacy alias; audience_question is the authoritative editorial control",
        "- `must_not_include`: required non-empty list of adjacent topics, claims, or details that must stay outside this page",
        "- `split_risk`: required `low`, `medium`, or `high`; medium/high also requires `split_risk_reason`, and high must be resolved by splitting or restructuring before approval",
        "- `storyline_role`: required concrete role in the director's story arc; state what changes in the audience's understanding or decision after this page",
        "- `transition_from_previous`: required concrete logical dependency on the previous content page or chapter question",
        "- `transition_to_next`: required concrete unresolved question handed to the next content page or decision destination",
        "- `core_message`: required; state the smallest complete meaning supported by the cited material, without requiring argument, causality, necessity, value judgment, or action",
        "- `core_message_derivation`: required; include `source_refs`, `supporting_statements`, `derivation`, `introduced_relations`, and `introduced_modalities`",
        "- `primary_argument_node_id`: required; the one source argument node whose thesis the page carries",
        "- `source_argument_node_ids`: required; semantic nodes selected for the page; do not use Source Truth records as a replacement",
        "- `source_argument_node_statuses`: required object; copy each selected node's status exactly and preserve conditional/planned wording",
        "- `source_argument_node_weights`: required object; copy each selected node's `argument_weight` exactly (`core`, `supporting`, `detail`, or `constraint`); do not derive it from the page role or relation type",
        "- `source_argument_node_roles`: required object; copy each selected node's `argument_role` exactly; no source role may be replaced by a generic layer label",
        "- `source_gap_ids` / `gap_handling`: required when a selected semantic node carries source gaps; state what remains待确认/条件性 and never replace the gap with a fact",
        "- `core_message_derivation.argument_node_ids`: required and must include `primary_argument_node_id`",
        "- `content_relations`: required; each relation must include a non-empty `subject`, one or more non-empty `objects`, the actual source-supported `relation` (such as composed_of, contains, layered_as, corresponds_to, sequence_before, applies_to, covers, bounded_by, provides_to, or supports), and supporting `source_refs`",
        "- `subtitle`: optional; it may summarize page content and must not manufacture a conclusion",
        "- `onscreen_conclusion`: optional; write it only when it is an equal-strength visible compression of `core_message`",
        "- Definitions, composition, design, lists, process, duties, and arrangements still require a complete core_message, even when no visible conclusion is appropriate",
        "- Never add causality, necessity, exclusivity, certainty, or outcome claims merely to complete a field",
        "- The semantic argument model is authoritative for thesis, chapter role, argument role, argument_weight, argument relation, status, actor, and source gaps. Outline authoring may select/compress/reorder for the approved audience, but may not create a new thesis, merge nodes without a declared source relation, downgrade a `core` node to a supporting/foundation layer, or turn a source gap into a fact.",
        "- `上屏文字` must remain independently readable and preserve only relations actually stated or directly supported by the source",
        "- `new_value_vs_previous`",
        "- `reserved_for_later`",
        "- `content_units`: statement, source_refs, role (`primary`, `supporting`, or `boundary`); these are source-grounded content units, not proof claims",
        "- `detail_refs`: source_refs retained for full prose, notes, parameters, examples, or traceability but intentionally not promoted into peer on-screen modules",
        "- Treat Source Truth priority as semantic weight: P0 is page-forming, P1 supports one of the page's main modules, and P2 is retained detail. Complete coverage never means equal page or visual weight.",
        "- An ordinary page must contain exactly one `primary` content unit, at most three grouped `supporting` units, and at most one grouped `boundary` unit. A justified boundary-focus page may omit the primary unit.",
        "- Never create one `content_unit` per Source Truth record. Group related P0/P1 records into 2-4 semantic modules and place P2 records in `detail_refs`.",
        "- P0 records may not be placed only in `detail_refs`; P2 records may not derive `core_message` or create peer content modules.",
        "- Every page `source_ref` must be classified through a content unit or `detail_refs`; this preserves traceability without flattening hierarchy.",
        "- Source Truth records with claim_role `boundary` or `unresolved` must use content-unit role `boundary`; they must never be labeled `primary` or `supporting`",
        "- Exclude boundary/unresolved records from `core_message_derivation.source_refs` on ordinary pages; place them in `boundary_refs` instead",
        "- Only when scope, admission, assurance conditions, or a pending decision is the page's actual business subject may the page set `boundary_focus: true`; it must also provide a non-empty `boundary_focus_reason`",
        "- `decision_boundary` is a deck-level maturity constraint. Copying it into document_semantics does not require a boundary-led page and does not authorize promoting it into a core_message",
        "- `visual_intent_type`: optional explicit ImageGen relationship type. Use one of "
        "`judgment_evidence`, `boundary_guardrail`, `hierarchy_support`, "
        "`decision_admission`, `comparison`, "
        "`scenario_application`, `multi_semantic_foundation`, `causal`, "
        "`closed_loop`, `phase`, `capability_relationship`; omit it when the "
        "relationship is not yet clear.",
        "- `semantic_intent_type`: optional canonical visual-structure relationship for the "
        "new review router. Use only after semantic-intent review; it does not bypass script "
        "or ImageGen approval. Legacy `visual_intent_type` remains the production fallback.",
        "- `visual_proof`: optional one-sentence statement of how the visual relationship "
        "expresses `core_message`; omit it when the relationship template is sufficient.",
        "",
        "Before creating `content_units`, screen each candidate against the source-supported page content.",
        "- Keep a unit only when it directly presents cited material or supplies part of the page core_message.",
        "- Use `boundary` role when a condition or unresolved item is genuinely part of this page's subject; page or claim taxonomies must not decide this.",
        "- Consolidate records only when they express one complete content unit; preserve distinct objects and relations when aggregation would change meaning.",
        "- Do not manufacture implications merely to turn descriptive material into proof.",
    ]
    output = project / "workbench/stages/01-analysis/outline-authoring-input.md"
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output


def prepare_page_script_input(project: Path, page_id: str = "") -> Path:
    project = project.expanduser().resolve()
    assert_semantic_understanding_ready(project)
    communication_gate = assert_communication_strategy_ready(project)
    outline = _load(project / "workbench/stages/01-analysis/outline.json")
    communication_issues = communication_strategy_binding_issues(outline, communication_gate)
    if communication_issues:
        raise ValueError(
            "outline is not bound to the approved communication strategy; rebuild and audit the outline"
        )
    records = _records(project)
    pages = [
        item for item in outline.get("pages", [])
        if isinstance(item, dict)
        and item.get("page_type") == "content"
        and (not page_id or item.get("page_id") == page_id)
    ]
    if page_id and not pages:
        raise ValueError(f"content page not found: {page_id}")
    authoring_artifact = _ensure_page_script_authoring(
        project,
        project / "workbench/stages/01-analysis/outline.json",
        pages,
    )
    lines = [
        "# Page script authoring input",
        "",
        f"Authoritative JSON authoring artifact: `{authoring_artifact}`",
        "The compiler consumes this JSON artifact. Keep its `outline_sha256` bound to the current Outline and declare every non-boundary `content_unit.unit_id` in each page's `consumes` list.",
        "Write backend composition guidance as a separate two-line block: `【视觉结构，不上屏】` followed by the guidance text. Never place that guidance inside `上屏文字`.",
        "Write full prose from the approved core_message and source-supported content relations; derive on-screen text from it.",
        "Do not add `副标题` or `上屏结论` merely because the page is a content page. "
        "When the approved Outline has them, preserve them; when it does not, begin with the source-supported on-screen modules.",
        "When migrating an already approved script to this subtitle rule, preserve "
        "its existing `上屏文字` unchanged. Only add or update `副标题`, retain the "
        "full judgment as semantic metadata, and set the appropriate display mode.",
        "The approved core_message is mandatory semantic metadata; its onscreen_conclusion remains optional.",
        "Answer the approved `audience_question`, respect every `must_not_include` exclusion, and do not revive an unresolved split risk while drafting prose or on-screen modules.",
        "Use `detail_refs` when drafting 完整文字稿 and speaker notes, but do not turn each detail record into an on-screen module.",
        "Never strengthen the core_message from page labels, modules, visual structure, or speaker notes.",
        "The visible layer must be independently readable without speaker narration.",
        "First fix the page relation skeleton (path / layers / loop / judgment-evidence), "
        "then write matching on-screen modules. Do not chase token coverage by stuffing "
        "full-prose sentences onto the slide.",
        "Write `上屏文字` as a focused body expression: source-supported content → "
        "the same-strength relation stated by the material → implication or handoff only when supported. "
        "Do not repeat the page title or subtitle inside the body.",
        "Write each labelled on-screen detail as a short phrase or short sentence: count meaningful Chinese/Latin/numeric characters after the first label separator; <=36 is the preferred band, 37–60 requires shortening or splitting, and >60 is a script-audit error. Keep long judgments, legal boundaries, and necessary complete conclusions in their dedicated fields instead of hiding them inside a detail line.",
        "Indentation declares a real parent-child taxonomy, not visual grouping. Before nesting, verify that every child answers the same classification question implied by its parent. Never nest actors or participating parties under a construction item, mechanism, platform, carrier, path, process, task, or goal. Fold those actors into the item's short description, or create a separate actor group only when actor roles are independently required on screen.",
        "Never put compositor instructions such as 四行选择矩阵、阅读顺序、视觉中心、构图说明、泳道/色块/主链呈现 or 第X行｜ coordinates into `上屏文字`; write them under `【视觉结构，不上屏】` or another backend field.",
        "Boundary is opt-in, never a mandatory fourth beat. A boundary, evidence-status, "
        "pending-proof, or research-status module may appear only when it is the primary "
        "meaning of the approved core_message, not merely mentioned by the title, page mission, "
        "or a trailing caveat. Otherwise keep it in full prose, narration, or traceability and "
        "never promote it to a peer on-screen module.",
        "Do not compress the full prose into module labels plus keywords. Preserve every fact, number, and relation needed to understand why the conclusion follows; preserve a limitation only when the limitation is itself part of the declared page subject.",
        "Count only Chinese, Latin, and numeric characters: target roughly 50% of the full prose, with a hard minimum of 220 and a cap target of 320 visible characters.",
        "Use at least two evidence-bearing on-screen lines. The visible conclusion may also carry the implication or handoff; do not add formulaic 因此/由此 wording only to satisfy the contract.",
        "`文字稿取舍说明` must use three buckets:",
        "  - 必留上屏：module titles / key phrases that remain on the slide",
        "  - 仅讲解：mechanism detail kept for speaker notes, not on-screen",
        "  - 仅追溯：S### retained in 证据映射 but not rendered on-screen",
        "ImageGen must not re-promote 完整文字稿 or 证据映射 into must-onscreen text; "
        "fix thin slides by rewriting Stage 01 上屏文字.",
        "`must_not_include`, `reserved_for_later`, `boundary_refs`, and `boundary_constraints` are internal controls only.",
        "They must not be copied into coaching tips or speaker notes. State a constraint only when it is the page's declared business subject.",
        "",
    ]
    for page in pages:
        lines += [
            f"## {page.get('page_id')} {page.get('title')}",
            f"- page_mission: {page.get('page_mission') or page.get('page_job', '')}",
            f"- audience_question: {page.get('audience_question', '')}",
            f"- business_question: {page.get('business_question', '')}",
            f"- must_not_include: {json.dumps(page.get('must_not_include') or [], ensure_ascii=False)}",
            f"- split_risk: {page.get('split_risk', '')}",
            f"- split_risk_reason: {page.get('split_risk_reason', '')}",
            f"- core_message: {page.get('core_message') or page.get('main_message', '')}",
            f"- onscreen_conclusion: {page.get('onscreen_conclusion') or page.get('onscreen_judgment', '')}",
            f"- core_message_derivation: {json.dumps(page.get('core_message_derivation') or page.get('judgment_derivation') or {}, ensure_ascii=False)}",
            f"- primary_argument_node_id: {page.get('primary_argument_node_id', '')}",
            f"- source_argument_node_ids: {json.dumps(page.get('source_argument_node_ids') or [], ensure_ascii=False)}",
            f"- source_argument_node_roles: {json.dumps(page.get('source_argument_node_roles') or {}, ensure_ascii=False)}",
            f"- source_argument_node_statuses: {json.dumps(page.get('source_argument_node_statuses') or {}, ensure_ascii=False)}",
            f"- source_argument_node_weights: {json.dumps(page.get('source_argument_node_weights') or {}, ensure_ascii=False)}",
            f"- content_relations: {json.dumps(page.get('content_relations') or [], ensure_ascii=False)}",
            f"- source_evidence_contract: {json.dumps(page.get('source_evidence_contract') or {}, ensure_ascii=False)}",
            f"- source_claims: {json.dumps(page.get('source_claims') or [], ensure_ascii=False)}",
            f"- onscreen_conclusion_mode: {page.get('onscreen_conclusion_mode') or page.get('onscreen_judgment_mode', 'auto')}",
            f"- new_value_vs_previous: {page.get('new_value_vs_previous', '')}",
            f"- reserved_for_later: {page.get('reserved_for_later', '')}",
            f"- detail_refs: {', '.join(str(item) for item in page.get('detail_refs', [])) or '[]'}",
            f"- visual_intent_type: {page.get('visual_intent_type') or 'auto'}",
            f"- visual_proof: {page.get('visual_proof') or 'auto'}",
            "- content_units:",
        ]
        content_units = page.get("content_units") or [
            {
                "statement": point.get("claim"),
                "source_refs": point.get("source_refs", []),
                "role": "primary" if point.get("consumption") == "primary" else "supporting",
            }
            for point in page.get("proof_points", [])
            if isinstance(point, dict)
        ]
        for point in content_units:
            if isinstance(point, dict):
                refs = ", ".join(str(item) for item in point.get("source_refs", []))
                lines.append(f"  - {point.get('unit_id', '')} [{point.get('role', 'supporting')}] {point.get('statement', '')} ({refs})")
        proof_source_ids = list(
            dict.fromkeys(
                str(source_id)
                for point in content_units
                if isinstance(point, dict)
                for source_id in point.get("source_refs", [])
            )
        )
        boundary_source_ids = [
            str(source_id) for source_id in page.get("boundary_refs", [])
        ]
        detail_source_ids = [
            str(source_id) for source_id in page.get("detail_refs", [])
        ]
        lines.append("- evidence_text:")
        for source_id in proof_source_ids:
            lines.append(f"  - {source_id}: {records.get(str(source_id), {}).get('statement', '')}")
        lines.append("- retained_detail_text:")
        if detail_source_ids:
            for source_id in detail_source_ids:
                lines.append(
                    f"  - {source_id}: {records.get(source_id, {}).get('statement', '')}"
                )
        else:
            lines.append("  - none")
        lines.append("- boundary_refs: " + (
            ", ".join(boundary_source_ids) if boundary_source_ids else "[]"
        ))
        lines.append("- boundary_constraints:")
        if boundary_source_ids:
            for source_id in boundary_source_ids:
                lines.append(
                    f"  - {source_id}: {records.get(source_id, {}).get('statement', '')}"
                )
        else:
            lines.append("  - none")
        receipt = {
            "schema": "cyberppt.page_contract_receipt.v2",
            "page_id": page.get("page_id"),
            "page_mission": page.get("page_mission") or page.get("page_job"),
            "audience_question": page.get("audience_question"),
            "business_question": page.get("business_question"),
            "must_not_include": page.get("must_not_include", []),
            "split_risk": page.get("split_risk"),
            "split_risk_reason": page.get("split_risk_reason"),
            "core_message": page.get("core_message") or page.get("main_message"),
            "onscreen_conclusion": page.get("onscreen_conclusion") or page.get("onscreen_judgment"),
            "core_message_derivation": page.get("core_message_derivation") or page.get("judgment_derivation"),
            "content_relations": page.get("content_relations", []),
            "onscreen_conclusion_mode": page.get("onscreen_conclusion_mode") or page.get("onscreen_judgment_mode"),
            "new_value_vs_previous": page.get("new_value_vs_previous"),
            "reserved_for_later": page.get("reserved_for_later"),
            "visual_intent_type": page.get("visual_intent_type"),
            "visual_proof": page.get("visual_proof"),
            "content_units": content_units,
            "detail_refs": page.get("detail_refs", []),
            "boundary_refs": page.get("boundary_refs", []),
            "new_value_realized": True,
            "reserved_for_later_respected": True,
            "audience_question_answered": True,
            "must_not_include_respected": True,
            "split_risk_resolved": True,
        }
        lines += [
            "- page_contract_receipt (draft transport only; copy unchanged so the final assembler can move it into page-contracts.json):",
            f"  <!-- cyberppt-page-contract {json.dumps(receipt, ensure_ascii=False, separators=(',', ':'))} -->",
        ]
        lines.append("")
    suffix = f"-{page_id}" if page_id else ""
    output = project / "workbench/scripts" / f"page-script-authoring-input{suffix}.md"
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output
