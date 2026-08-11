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
from cyberppt.storyline_director import (
    assert_storyline_director_ready,
    storyline_director_authoring_contract,
)


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


def prepare_outline_input(
    project: Path,
    *,
    lightweight: bool = False,
    communication_goal: str = "",
) -> Path | str:
    project = project.expanduser().resolve()
    if lightweight and not communication_goal.strip():
        raise ValueError("--communication-goal is required with --lightweight")
    semantic_gate = None if lightweight else assert_semantic_understanding_ready(project)
    communication_gate = None if lightweight else assert_communication_strategy_ready(project)
    director_gate = None if lightweight else assert_storyline_director_ready(project)
    argument_model = None
    if lightweight:
        model_path = project / SEMANTIC_ARGUMENT_MODEL
        if not model_path.is_file():
            raise FileNotFoundError(
                "lightweight Outline preparation requires semantic-argument-model.json"
            )
        argument_model = load_model(model_path)
    elif semantic_gate is not None and semantic_gate.get("semantic_argument_model_sha256"):
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
        *(
            [
                "The Outline must consume the semantic argument model below. Do not rebuild the source thesis from evidence records.",
                "Source Truth is the factual authority. Keep page-to-evidence mappings in the Outline consumption fields; never write page assignments back into Source Truth records.",
                "Do not add approval, hash, receipt, retry, attempt, escalation, ledger, or freshness-control fields in lightweight mode.",
            ]
            if lightweight
            else [
                "The Outline root must copy `semantic_understanding_sha256`, `semantic_source_bundle_sha256`, and, when present, `semantic_source_map_bundle_sha256` from the current semantic gate.",
                "The Outline must also copy `semantic_argument_model_sha256` and consume the source argument model below. Do not rebuild the source thesis from evidence records.",
                "Source Truth is frozen after the Source Truth stage. Set `source_truth_mapping_mode` to `consumption_manifest`; record `source_truth_semantic_sha256` and `source_consumption_semantic_sha256` as the authority bindings, while retaining the corresponding raw SHA-256 fields only as byte receipts. Write page-to-evidence mappings only to the independent `source_consumption_manifest`; never write page assignments back into Source Truth records.",
            ]
        ),
        "",
        "Before planning pages, preserve the Stage 00 source argument model `document_semantics` and the Source Truth copy: `document_role` says what artifact is being presented; `subject_of_report` says what the presentation is about; `primary_thesis` is the deck-level conclusion; `decision_boundary` limits its maturity; `author_purpose` states what the author is trying to advance; `argument_method` and `supporting_basis` explain how the source argues for that purpose.",
        "Never replace the subject of report with the activity used to produce or present the document. Document role and business subject are separate fields.",
        "Copy `document_semantics` into the outline and set root `narrative_thesis` exactly to its `primary_thesis`.",
        "",
        "Every content page must state one source-supported `core_message`: the smallest complete meaning the page communicates.",
        "A core message may express a fact, composition, relationship, process, scope, boundary, or a source-supported judgment. Boundary is opt-in: B/U records constrain an ordinary page and must not become its semantic center by default.",
        "Set schema to `cyberppt.outline.v2`, root `argument_contract_mode` to `strict`, and root `core_message_derivation_mode` to `required`.",
        "Add required root `source_section_weights` as an object. Populate it only when authoritative normalized chapter weights are available from the source analysis; otherwise use `{}` rather than inventing weights. When populated, content pages must declare matching `source_weight` values for distortion auditing.",
        "Set root `topic_partition_mode` to `required`. This enables the chapter/page topic partition contract described below.",
        "Topic partitioning is on by default for formal v2 storyline outlines; declaring the mode keeps that default visible and auditable.",
        "Set root `page_sequence_mode` to `required` and add root `chapter_page_orders`. Intra-chapter page ordering is also on by default for formal v2 storyline outlines.",
        "Set root `argument_node_disposition_mode` to `required` and add root `argument_node_dispositions`. Before creating pages, inventory every Stage 00 `subsection_node` as a page-forming candidate and assign exactly one disposition: `standalone_page`, `merged_page`, or `intentional_omission`.",
        "Set root `page_content_unit_coverage_mode` to `required`. For every retained page, decompose its assigned Source Truth and semantic-node content into atomic `content_units`; do not use one summary sentence as a substitute for several source facts or relations.",
        "Every content unit must declare `unit_id`, `statement`, `source_refs`, `importance` (`primary`/`supporting`/`detail`/`boundary`), `full_prose_required`, `coverage_anchors`, `onscreen_required`, and `onscreen_anchors`. `coverage_anchors` must preserve at least two source-specific business objects, actions, conditions, statuses, or numbers; generic terms such as platform, mechanism, support, capability, collaboration, or service are not sufficient alone.",
        "All primary and source-essential supporting units are `full_prose_required=true`. Mark `onscreen_required=true` for the page judgment, main business relation, indispensable business objects/actions, critical status, and decision-driving numbers. Detail may remain prose-only, but the page must retain at least one onscreen-required unit.",
        "Compression is performed only after the atomic unit inventory is complete: first ensure the full prose covers every required unit, then phrase the onscreen-required units as short clauses. Never derive the inventory backward from already compressed prose or onscreen copy.",
        "A `standalone_page` disposition must name the page where that node is `primary_argument_node_id`. A `merged_page` disposition must name a page that formally includes the node in `source_argument_node_ids`, and must provide both `rationale` and `merge_reason` explaining why the two source topics share one page theme and one main business relation. Putting a node only in `detail_refs`, `source_evidence_node_ids`, prose, or speaker notes does not count as consuming a page-forming topic.",
        "An `intentional_omission` disposition must provide `rationale` and `omission_reason` tied to the selected communication goal or storyline. Page limits, compression, low priority, or 'supporting' weight alone are not sufficient reasons when the node has a distinct source heading, thesis, business role, or substantial evidence. This makes selective argument explicit without silently losing source-authored topics.",
        "Protected argument nodes cannot be omitted by the authoring model: every `core` node, every `constraint` node, and every `supporting` subsection with its own source heading and at least six evidence refs must be retained as `standalone_page` or `merged_page`. Omit one only when the user explicitly requested that removal; then set `user_authorized_omission=true` and record the concrete `user_decision_ref`.",
        "Every `merged_page` disposition must also declare `shared_page_topic`, exactly matching the target page's `topic_category`. If the target page is outside the source node's original chapter, add `cross_chapter_reason`. A generic compression or page-count reason is insufficient.",
        "Review the disposition table chapter by chapter before finalizing page count. Each retained chapter topic must either own a page or be demonstrably inseparable from the page that carries it; do not merge current foundation, target plan, architecture, product/service, mechanism, cooperation, or implementation topics merely because they occur in the same source chapter.",
        "Set root `title_style_mode` to `formal_plain` for formal government, state-owned-enterprise, association, proposal, planning, and implementation materials. This is the default for formal v2 solution outlines: write plain declarative titles in the form business object + matter/mechanism/requirement; avoid question titles, slogans, `从……到……` journey rhetoric, promotional verbs, and titles that state `完整构成`. Use `expressive` only when the user explicitly requests a speech- or marketing-led title style, and then set `user_requested_title_style` to true.",
        "Create the Outline from Source Truth. Use canonical field names when the material calls for them:",
        "required `page_mission`, required `core_message`, optional `onscreen_conclusion`, "
        "required `audience_question`, `must_not_include`, `split_risk`, "
        "`new_value_vs_previous`, `reserved_for_later`, `content_units`, "
        "`visual_intent_type`.",
        "Set root `editorial_control_mode` to `required`.",
        *(
            [
                "Set root `storyline_contract_mode` to `required` and embed the selected storyline contract directly in `storyline`; do not create a separate Storyline Director artifact.",
                "Set root `semantic_argument_model_mode` to `required`; consume Stage 00 node IDs, roles, weights, relations and gaps without hash binding.",
            ]
            if lightweight
            else [
                "Set root `storyline_contract_mode` to `required`. Copy `storyline_director_sha256` and the complete `storyline` contract from the current Storyline Director gate exactly.",
                "Set root `semantic_argument_model_mode` to `required`; copy `semantic_argument_model_sha256` exactly from Stage 00.",
            ]
        ),
        "",
    ]
    if lightweight:
        lines += [
            "## selected_communication_goal",
            "",
            communication_goal.strip(),
            "",
            "Copy the selected goal exactly into the Outline root field `communication_goal`. Derive the concrete `audience`, `communication_purpose`, `decision_task`, `architecture_mode`, `architecture_reason`, and `structure_principle` from that selected goal and the source. `architecture_reason` is required and must explain why the selected architecture fits the material and communication goal; solution is the default architecture for formal proposal material unless the selected goal explicitly requires consulting argumentation, in which case the reason must identify that explicit request.",
            "Every chapter question, page audience_question, evidence choice and closing action must visibly serve this goal. Do not silently switch audience or turn a peer-exchange goal into an approval request.",
            "",
            "## embedded_storyline_director_reasoning",
            "",
            storyline_director_authoring_contract(),
            "",
            "Before authoring the Outline, compare 2-3 genuinely different source-supported storyline routes for this communication goal. For each route state its audience logic, evidence selection, chapter progression, strengths, and risks. Select and explain one recommended route, then encode only that route in the Outline `storyline` contract.",
            "Apply the named route guidance above: when the source has an explicit argument sequence, include `source_logic_focused` among the candidates and recommend it for introduction- or understanding-led communication unless the selected goal explicitly requires decision/action reordering.",
            "The final Outline is a selective argument, not a directory of source sections. Preserve every source fact in traceability where needed, but give page-forming weight only to the chosen route and the semantic model's P0/core propositions.",
            "Present the completed chapter/page Outline to the user for review before page-detail authoring.",
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
    elif lightweight:
        semantic_path = project / SEMANTIC_ARTIFACT
        if not semantic_path.is_file():
            raise FileNotFoundError(
                "lightweight Outline preparation requires semantic-understanding.md"
            )
        lines += [
            "## authoritative_semantic_understanding",
            "",
            semantic_path.read_text(encoding="utf-8-sig").rstrip(),
            "",
            "## authoritative_source_argument_model",
            "",
            "Use this model to select and organize pages; do not change its document semantics, thesis, node roles, weights, statuses, relations, MECE basis, inferences, concept distinctions, or source gaps.",
            json.dumps(argument_model, ensure_ascii=False, indent=2),
            "",
            "Every content page must declare `primary_argument_node_id`, `source_argument_node_ids`, and matching roles, weights, statuses and gap handling. Do not default to one page per source subsection; merge adjacent thin material when one source-supported page can carry the relationship more clearly.",
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
        "Plan chapter and page boundaries before assigning evidence:",
        "- Build chapters by business subject and argument function, not by mechanically copying source section headings. A chapter must answer one coherent chapter question and own a non-empty `topic_categories` list in its storyline chapter mission.",
        "- Source headings remain traceability cues, not mandatory chapter boundaries. Merge adjacent source sections when they serve the same chapter question; split one source section when it contains different business subjects or argument functions.",
        "- Deck-level positioning, foundations, and overall architecture may share an overall-cognition chapter when they jointly establish the project model, but keep them on separate pages when they answer different audience questions or express different core relations.",
        "- Products and services may share one chapter when they form one coherent offering or operating system. Distinct product, service, operating, commercial, or implementation themes must still remain separate page topics.",
        "- Every content page must declare exactly one authoritative `topic_category`, and that category must belong to its chapter mission's `topic_categories`.",
        "- Every `content_unit` must repeat the page's `topic_category`. Never combine different topic categories on one page merely to reduce page count.",
        "- Aggregate same-topic components on one page only when they answer the same `audience_question`, support one `core_message`, and preserve one primary business relation. Category equality is necessary but not sufficient for aggregation.",
        "- Split pages when the business object, primary relation, factual/status boundary, decision task, or audience question changes. When one `topic_category` intentionally spans multiple pages in a chapter, every such page must state a concrete, page-specific `topic_split_reason` describing that semantic distinction.",
        "- A complete process may remain on one page when it has one process subject, one directional relationship, and one audience question. Do not create redundant overview and step pages unless the source or audience task requires separate judgments.",
        "- Chapter membership does not authorize page aggregation: related topics may belong to one chapter while remaining separate pages so that each page retains a clear semantic center.",
        "",
        "After defining chapter membership and page topics, order pages by source-supported understanding dependencies:",
        "- Add one root `chapter_page_orders` entry per content chapter. Each entry requires `chapter_id`, non-empty `ordering_principles`, `ordered_topic_categories`, `ordered_page_ids`, and `rationale`. Keep this Outline-owned page-consumption relationship outside the authoritative Storyline Director contract. The declared page IDs must exactly match the chapter's actual content-page order.",
        "- Use one or more supported principles: `definition_before_detail`, `whole_before_parts`, `dependency_before_dependent`, `mechanism_before_execution`, `process_direction`, `status_or_maturity_progression`, `source_argument_sequence`, or `audience_question_progression`.",
        "- Select principles per chapter; do not impose one universal ladder. Definitions or positioning normally precede their details, a whole normally precedes its parts, prerequisites precede dependent mechanisms, and mechanisms normally precede execution details when the source supports those relations.",
        "- Preserve source-native direction for composition, causality, process, admission, status, and maturity relations. Editorial reordering may improve audience understanding but may not reverse an authoritative relation or turn a later condition into an earlier fact.",
        "- Keep pages with the same `topic_category` contiguous. Do not leave a topic, enter another topic, and then return to the first topic unless the content is reclassified into genuinely different page topics.",
        "- Put whole-model cognition before local detail when the detail depends on that model; put operating or delivery mechanics before checklists that execute them; put constraints at the point where they govern the subject rather than collecting unrelated caveats into a closing page.",
        "- A page may move away from its source heading only when its evidence, status, and relation remain unchanged and the new position answers a necessary audience question or dependency more clearly.",
        "- Every content page must add a non-empty `page_order_reason` explaining why it belongs at that exact position. This is an editorial rationale, not visible slide copy.",
        "- After any reorder, rebuild `ordered_page_ids`, `ordered_topic_categories`, `prerequisite_pages`, `transition_from_previous`, and `transition_to_next`; stale transitions or silent dependency jumps are invalid.",
        "",
        "Each content page must define its semantic center, evidence, and content structure:",
        "- `page_mission`: required internal editorial responsibility; describe what the page does in the deck, not a claim it must prove",
        "- `audience_question`: required concrete question the audience needs this page to answer; it must not repeat page_mission or use a placeholder such as 本页说明什么",
        "- `business_question`: optional legacy alias; audience_question is the authoritative editorial control",
        "- `must_not_include`: required non-empty list of adjacent topics, claims, or details that must stay outside this page",
        "- Allocate the semantic model's source information across pages before drafting copy. Every Source Truth record selected for the deck must have one owning page for full-prose consumption; related pages may cite it again only when they answer a different declared question.",
        "- `intentional_omissions`: optional list of objects with `source_refs` and a specific `reason`. Use it only when assigned source information is deliberately excluded from this page's full prose. It is never a substitute for forgetting, compression, page limits, or generic claims that the detail is unimportant.",
        "- Completeness does not authorize topic leakage. A page must consume all of its assigned information while excluding mechanisms, examples, actors, conditions, or actions whose owning business question is reserved for another page.",
        "- `split_risk`: required `low`, `medium`, or `high`; medium/high also requires `split_risk_reason`, and high must be resolved by splitting or restructuring before approval",
        "- `storyline_role`: required concrete role in the director's story arc; state what changes in the audience's understanding or decision after this page",
        "- `transition_from_previous`: required concrete logical dependency on the previous content page or chapter question",
        "- `transition_to_next`: required concrete unresolved question handed to the next content page or decision destination",
        "- `page_order_reason`: required internal explanation of why this page follows its predecessor and prepares its successor under the matching root chapter_page_orders entry",
        "- `core_message`: required; state the smallest complete meaning supported by the cited material, without requiring argument, causality, necessity, value judgment, or action",
        "- `core_message_derivation`: required; include `source_refs`, `supporting_statements`, `derivation`, `introduced_relations`, and `introduced_modalities`",
        "- `primary_argument_node_id`: required; the one source argument node whose thesis the page carries",
        "- `source_argument_node_ids`: required; semantic nodes selected for the page; do not use Source Truth records as a replacement",
        "- `source_evidence_node_ids`: optional; semantic nodes used only to bind supporting/detail Source Truth records to their source argument. They do not become additional page theses or peer modules.",
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
        "- `content_units`: statement, source_refs, role (`primary`, `supporting`, or `boundary`), and the page-matching `topic_category`; these are source-grounded content units, not proof claims",
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
    content = "\n".join(lines).rstrip() + "\n"
    if lightweight:
        return content
    output = project / "workbench/stages/01-analysis/outline-authoring-input.md"
    output.write_text(content, encoding="utf-8")
    return output


def prepare_page_script_input(
    project: Path,
    page_id: str = "",
    *,
    lightweight: bool = False,
) -> Path | str:
    project = project.expanduser().resolve()
    if not lightweight:
        assert_semantic_understanding_ready(project)
    communication_gate = None if lightweight else assert_communication_strategy_ready(project)
    outline = _load(project / "workbench/stages/01-analysis/outline.json")
    communication_issues = (
        []
        if lightweight
        else communication_strategy_binding_issues(outline, communication_gate)
    )
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
    authoring_artifact = None
    if not lightweight:
        authoring_artifact = _ensure_page_script_authoring(
            project,
            project / "workbench/stages/01-analysis/outline.json",
            pages,
        )
    lines = [
        "# Page script authoring input",
        "",
        *(
            [
                "Write the completed pages directly as chapter Markdown files under `workbench/scripts/drafts/`; do not create page-script-authoring.json or another control artifact.",
                "After completing the requested chapter or pages, present the detailed page content to the user for live review and modification before assembling the final script.",
            ]
            if lightweight
            else [
                f"Authoritative JSON authoring artifact: `{authoring_artifact}`",
                "The compiler consumes this JSON artifact. Keep its `outline_sha256` bound to the current Outline and declare every non-boundary `content_unit.unit_id` in each page's `consumes` list.",
            ]
        ),
        "Write the Stage 02 semantic-structure handoff as a separate two-line block: `【视觉结构，不上屏】` followed by the guidance text. Never place that guidance inside `上屏文字`.",
        "This handoff records one core judgment, one primary business relation and direction, the participating roles or objects, and which locked text belongs to which role, action, boundary or result. It is not a page-layout recipe.",
        "Do not prescribe rows, columns, swim lanes, matrices, card counts, top/bottom/left/right/center placement, percentage geometry, summary strips, or a named visual carrier. Leave candidate composition and medium selection to the Stage 02 visual-structure designer.",
        "The logic skeleton and the visual-structure handoff must describe the same business relation. Do not add a second process, result chain, abstract hub or conclusion that is absent from the approved content relation.",
        "Write full prose from the approved core_message and source-supported content relations; derive on-screen text from it.",
        "Write 完整文字稿 as semantic paragraphs, not one dense block. Split at real argument boundaries (for example background → concrete demand → present gap → page conclusion); never split mechanically by equal length or sentence count.",
        "Treat completeness and page ownership as simultaneous constraints. Every source record assigned to this page must be represented in 完整文字稿 unless the approved Outline records a specific intentional omission; information assigned to a later page must stay out of this page even when it is broadly related.",
        "A page may answer only its approved audience_question and topic_category. Background/necessity pages state the external change, concrete demand and present gap; they must not preview product formation, resource registration, authorization delivery, metering, settlement, cooperation steps or other solution mechanisms reserved for later pages.",
        "Do not add `副标题` or `上屏结论` merely because the page is a content page. "
        "When the approved Outline has them, preserve them; when it does not, begin with the source-supported on-screen modules.",
        "When migrating an already approved script to this subtitle rule, preserve "
        "its existing `上屏文字` unchanged. Only add or update `副标题`, retain the "
        "full judgment as semantic metadata, and set the appropriate display mode.",
        "The approved core_message is mandatory semantic metadata; its onscreen_conclusion remains optional.",
        "Preserve the approved Outline title exactly. For formal materials, keep the default `formal_plain` title style and do not re-dramatize titles as questions, slogans, journey rhetoric, or promotional claims during page drafting.",
        "The approved title must name the page's actual argumentative function rather than a narrower content fragment. A 建设必要性 page should normally say 建设必要性 explicitly; 需求、背景 or 现状 alone is insufficient when the page also proves why construction is required.",
        "Answer the approved `audience_question`, respect every `must_not_include` exclusion, and do not revive an unresolved split risk while drafting prose or on-screen modules.",
        "Before finalizing each module, trace it to this page's source_refs/content_units and ask whether it directly advances the page_mission. Broad relevance is insufficient. Delete or move any module whose real business question belongs to another page.",
        "Use `detail_refs` when drafting 完整文字稿 and speaker notes, but do not turn each detail record into an on-screen module.",
        "Never strengthen the core_message from page labels, modules, visual structure, or speaker notes.",
        "The visible layer must be independently readable without speaker narration.",
        "Within one visible module, use one peer syntax skeleton (prefer 标签：短语 or 主体：动作): keep labels parallel and do not mix label-value items with free paragraph fragments.",
        "Parallel syntax is a form constraint, not a reason to flatten business distinctions. Preserve each source-specific object, responsibility, processed object, participant, and action even when the sentence pattern is repeated.",
        "For causal, process, progression, or closed-loop pages, top-level on-screen modules must read continuously as one business chain. Each step needs a concrete action or relation predicate; isolated noun phrases may not rely on arrows or layout to create meaning. Do not over-explain every edge with explicit 推动/带动 wording when sequence and predicates already make the relation clear.",
        "Keep each top-level flow heading within 24 meaningful characters. Do not repeat the previous step's ending verbatim as the next step's opening; let each step advance with a new business subject or predicate. A necessity chain needs a real constraint (难以/尚未/不足) and a construction response that states what it connects or changes, but does not need overt causal conjunctions.",
        "Do not use formulaic discourse words such as 因此、由此、进而、综上、基于此、鉴于此 or 所以 in 完整文字稿、上屏文字 or 演讲者备注; let the subject, action, constraint, or result carry the transition. Keep evidence and enumerations in the child lines rather than turning peer headings back into category labels.",
        "Across adjacent pages, prefer a steady formal progression in page judgments: background/need → present gap → positioning → architecture → product/service → mechanism → cooperation → implementation. Do not force a repeated slogan; each page must advance its own approved topic.",
        "First fix the page relation skeleton (path / layers / loop / judgment-evidence), "
        "then write matching on-screen modules. Do not chase token coverage by stuffing "
        "full-prose sentences onto the slide.",
        "Write `上屏文字` as a focused body expression: source-supported content → "
        "the same-strength relation stated by the material → implication or handoff only when supported. "
        "Do not repeat the page title or subtitle inside the body.",
        "Make the on-screen argument complete. A necessity page must visibly progress from driving change to concrete demand, then to the current supply gap, and close with the source-supported construction response. Do not stop at a list of problems, and do not manufacture a generic conclusion.",
        "Write each labelled on-screen detail as a phrase or compact short sentence: count meaningful Chinese/Latin/numeric characters after the first label separator; <=30 is required and >30 is a script-audit error. Increase page coverage with several same-topic short items or true parent-child detail lines, never with paragraph-like copy. Keep long judgments, legal boundaries, and necessary complete conclusions in their dedicated fields instead of hiding them inside a detail line.",
        "Compression must preserve source specificity. Keep the source's named business objects in module titles, and keep its concrete duties, processed objects, operating actions, participants, and collaboration actions in the child items. Satisfy the <=30-character rule by adding or splitting true source-supported short items, never by replacing distinctive content with generic labels such as position, role, object, matter, support, or relationship.",
        "Make the visible information architecture explicit. Normally use 2–5 peer top-level business modules for the page skeleton; one umbrella module is allowed only when it owns several true children. When a module needs support, place only true members of that module as indented short details beneath it and separate peer modules with blank lines. Do not flatten a layered topic into an undifferentiated list, and do not invent hierarchy merely to create visual grouping.",
        "Indentation declares a real parent-child taxonomy, not visual grouping. Before nesting, verify that every child answers the same classification question implied by its parent. Never nest actors or participating parties under a construction item, mechanism, platform, carrier, path, process, task, or goal. Fold those actors into the item's short description, or create a separate actor group only when actor roles are independently required on screen.",
        "Never put compositor instructions such as 四行选择矩阵、阅读顺序、视觉中心、构图说明、泳道/色块/主链呈现 or 第X行｜ coordinates into `上屏文字` or `【视觉结构，不上屏】`. Translate any legitimate business meaning into the semantic relation handoff and leave the concrete layout to Stage 02.",
        "Boundary is opt-in, never a mandatory fourth beat. A boundary, evidence-status, "
        "pending-proof, or research-status module may appear only when it is the primary "
        "meaning of the approved core_message, not merely mentioned by the title, page mission, "
        "or a trailing caveat. Otherwise keep it in full prose, narration, or traceability and "
        "never promote it to a peer on-screen module.",
        "Do not add routine caveats, limitations, pending conditions, status reminders, or defensive closing sentences to 完整文字稿, 上屏文字, or 演讲者备注. When boundary or status is not the approved page subject, state the positive source-supported proposition directly and omit the caveat entirely; traceability fields already preserve the source boundary. Only pages whose approved primary relation is bounded_by, or whose core message explicitly distinguishes plan from result, may foreground that meaning.",
        "Do not compress the full prose into module labels plus keywords. Preserve every fact, number, and relation needed to understand why the conclusion follows; preserve a limitation only when the limitation is itself part of the declared page subject.",
        "Count only Chinese, Latin, and numeric characters. An explicit source-specific module hierarchy may use concise copy below the legacy 220-character target; four thin lines or generic concept labels do not qualify. Never add paragraph-like text merely to reach a character target.",
        "Use at least two evidence-bearing on-screen lines. The visible conclusion may also carry the implication or handoff through a concrete business action or result, never through formulaic transition filler.",
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
            f"- intentional_omissions: {json.dumps(page.get('intentional_omissions') or [], ensure_ascii=False)}",
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
            "intentional_omissions": page.get("intentional_omissions", []),
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
        if lightweight:
            lines += [
                "- required Markdown sections: 完整文字稿、文字稿取舍说明（必留上屏/仅讲解/仅追溯）、上屏文字、证据映射、【视觉结构，不上屏】、【演讲者备注】",
                "- write the finished page directly into its chapter draft; do not emit page-contract receipts or control metadata",
            ]
        else:
            lines += [
                "- page_contract_receipt (draft transport only; copy unchanged so the final assembler can move it into page-contracts.json):",
                f"  <!-- cyberppt-page-contract {json.dumps(receipt, ensure_ascii=False, separators=(',', ':'))} -->",
            ]
        lines.append("")
    content = "\n".join(lines).rstrip() + "\n"
    if lightweight:
        return content
    suffix = f"-{page_id}" if page_id else ""
    output = project / "workbench/scripts" / f"page-script-authoring-input{suffix}.md"
    output.write_text(content, encoding="utf-8")
    return output
