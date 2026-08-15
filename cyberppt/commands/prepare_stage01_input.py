"""Compile deterministic Stage 01 authoring inputs (lightweight path only)."""

from __future__ import annotations

import json
from pathlib import Path

from cyberppt.semantic_understanding import (
    SEMANTIC_ARGUMENT_MODEL,
)
from cyberppt.source_argument_model import load_model
from cyberppt.outline_authoring_projection import build_outline_authoring_projection


PAGE_SCRIPT_AUTHORING_RULES_PATH = (
    Path(__file__).resolve().parents[2]
    / "vendor/skills/ppt-script/system-prompt/stage1/61-page-script-authoring.md"
)


def storyline_director_authoring_contract() -> str:
    return "\n".join(
        [
            "You are the Outline Director. Do not create pages. First define the directed story that the Outline author must follow.",
            "The source is evidence, not a page inventory. Select and organize evidence around the approved theme and decision destination; preserve all traceability but never give every source item equal narrative or visual weight.",
            "The approved communication goal is an audience, use, and delivery constraint, not a new source fact or source thesis. Never promote a user-requested outcome, inferred rationale, or generic partnership language into a source-explicit page judgment.",
            "Treat `source_logic_focused` as a named storyline-route candidate whenever the source has an explicit argument sequence. This route preserves the source-native thesis and major section progression, then selectively compresses repetition, subordinate evidence, inventories, and execution detail inside that progression; it is focused compression, not one page per source section.",
            "Recommend `source_logic_focused` for first introductions, overview briefings, explanatory peer exchanges, or other goals whose intended outcome is understanding rather than a required approval, cooperation commitment, or immediate action. Audience questions may clarify relevance, but they must not replace the source progression with an action, conversion, or decision funnel.",
            "Prefer `source_logic_focused` when the source has an explicit argument sequence and the approved communication goal is introduction- or understanding-led. Do not create a second route merely to manufacture a choice; change the route only when the approved goal explicitly requires decision/action reordering.",
            "Separate frontstage communication from backstage strategy. Visible story beats, chapter questions, and the communication destination must follow the approved frontstage purpose and audience action. The backstage intent may guide selection but must not become a visible approval request or decision-seeking headline.",
            "Every chapter must answer one question and hand a necessary unresolved question to the next chapter. Every future page must have one storyline role, one self-contained core meaning, and explicit transitions from the preceding page and to the following page.",
            "Do not promote generic value, constraints, boundaries, background, or technical inventories into the main line unless they are the actual subject of the approved communication strategy.",
            "Use the source argument model's explicit `argument_weight` as the authority for narrative importance. `core` means an independent source proposition and must remain a visible story beat; `supporting`, `detail`, and `constraint` describe subordinate material. A semantic relation explains how propositions connect and has `weight_effect=none`; it never changes either endpoint's argument weight or role. Determine the story beat from the approved proposition, not from a project-specific keyword or a generic layer label.",
            "Treat `editorial_hypothesis` entries only as candidates. A candidate framing may be selected, rejected, or tested here, but it may not be relabeled as source-explicit, overwrite the source thesis, or retroactively change Stage 00.",
        ]
    )


def _load(path: Path) -> dict[str, object]:
    if not path.exists():
        raise FileNotFoundError(f"required artifact does not exist: {path}")
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise ValueError(f"artifact root must be an object: {path}")
    return payload


def _records(project: Path) -> dict[str, dict[str, object]]:
    truth = _load(project / "workbench/stages/01-analysis/source-truth.json")
    return {
        str(item.get("id")): item
        for item in truth.get("records", [])
        if isinstance(item, dict) and item.get("id")
    }


def prepare_outline_input(project: Path, *, communication_goal: str = "") -> str:
    project = project.expanduser().resolve()
    if not communication_goal.strip():
        raise ValueError("--communication-goal is required")
    model_path = project / SEMANTIC_ARGUMENT_MODEL
    if not model_path.is_file():
        raise FileNotFoundError(
            "lightweight Outline preparation requires semantic-argument-model.json"
        )
    argument_model = load_model(model_path)
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
        "The Outline must consume the semantic argument model below. Do not rebuild the source thesis from evidence records.",
        "Source Truth is the factual authority. Keep page-to-evidence mappings in the Outline consumption fields; never write page assignments back into Source Truth records.",
        "Do not add approval, hash, receipt, retry, attempt, escalation, ledger, or freshness-control fields.",
        "",
        "Before planning pages, preserve the Stage 00 source argument model `document_semantics` and the Source Truth copy: `document_role` says what artifact is being presented; `subject_of_report` says what the presentation is about; `primary_thesis` is the deck-level conclusion; `decision_boundary` limits its maturity; `author_purpose` states what the author is trying to advance; `argument_method` and `supporting_basis` explain how the source argues for that purpose.",
        "Source Truth must be built by reverse coverage from the Stage 00 semantic model. For every protected semantic node (`core`, `constraint`, or a `supporting` subsection with its own heading and at least six evidence refs), create enough atomic Source Truth records to cover every stable `SU-*` evidence ref used by that node; one representative summary record is not complete coverage.",
        "When one Source Truth record spans several source units or independent claims, split `semantic_units` so each fact, relationship, condition, status, number, responsibility, or recommendation remains independently auditable. Preserve exact source_unit_refs on the record.",
        "If the user explicitly removes a protected source matter, add root `intentional_source_unit_omissions` with `source_unit_refs`, a specific `reason`, `user_authorized_omission=true`, and `user_decision_ref`. The generator may not omit protected evidence on its own, and generic compression or low-priority reasons are insufficient.",
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
        "Every content unit must declare `unit_id`, `statement`, `source_refs`, `importance` (`primary`/`supporting`/`detail`/`boundary`), `argument_duties`, `full_prose_required`, `coverage_anchors`, `onscreen_required`, and `onscreen_anchors`. `coverage_anchors` must preserve at least two source-specific business objects, actions, conditions, statuses, or numbers; generic terms such as platform, mechanism, support, capability, collaboration, or service are not sufficient alone.",
        "All primary and source-essential supporting units are `full_prose_required=true`. Mark `onscreen_required=true` for the page judgment, main business relation, indispensable business objects/actions, critical status, and decision-driving numbers. Detail may remain prose-only, but the page must retain at least one onscreen-required unit.",
        "Preserve the complete argument chain, not only its conclusion. A retained premise/driver/consequence/gap/response may be compressed but cannot be placed only in `detail_refs` or narration when removing it would make the page start from an unexplained middle claim. Carry Source Truth `argument_duty` values into `content_units.argument_duties`.",
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
        "Treat `compile-outline-draft` only as a deterministic candidate inventory, never as the authored Outline. Set root `editorial_authoring_mode` to `author_driven` and change `editorial_authoring_status` from `mechanical_draft` to `author_edited` only after completing the editorial decisions below.",
        "For every content page author `non_substitutable_value`, one governing `argument_chain`, grouped `evidence_roles` (`claim`, `reason`, `instance`, `boundary`, `trace_only`), and `excluded_from_onscreen`. Evidence coverage is not page necessity; broad relevance is not direct support.",
        "Run a deletion test for every onscreen-required unit: if removing it still leaves the audience question fully answered, demote it to full prose, notes, or trace-only. Appendix registration fields, material checklists, operating forms, and procedural inventories default to `excluded_from_onscreen` unless they directly determine the page judgment.",
        "Do not use audit errors to invent modules or duplicate anchors. First make the professional editorial decision, then use audit only to catch source drift, missing duties, false relations, hierarchy errors, and contract defects.",
        "Set root `storyline_contract_mode` to `required` and embed the selected storyline contract directly in `storyline`; do not create a separate Storyline Director artifact.",
        "Set root `semantic_argument_model_mode` to `required`; consume Stage 00 node IDs, roles, weights, relations and gaps without hash binding.",
        "",
        "## selected_communication_goal",
        "",
        communication_goal.strip(),
        "",
        "Copy the selected goal exactly into the Outline root field `communication_goal`. Derive the concrete `audience`, `communication_purpose`, `decision_task`, `architecture_mode`, `architecture_reason`, and `structure_principle` from that selected goal and the source as editorial constraints. Do not turn any user-goal wording into a source fact, source judgment, or page core message unless the source explicitly supports it. `architecture_reason` is required and must explain why the selected architecture fits the material and communication goal; solution is the default architecture for formal proposal material unless the selected goal explicitly requires consulting argumentation, in which case the reason must identify that explicit request.",
        "Every chapter question, page audience_question, evidence choice and closing action must visibly serve this goal. Do not silently switch audience or turn a peer-exchange goal into an approval request.",
        "",
        "## embedded_storyline_director_reasoning",
        "",
        storyline_director_authoring_contract(),
        "",
        "Before authoring the Outline, use one source-faithful storyline route for this communication goal. Prefer `source_logic_focused` when the source has an explicit argument sequence; state the route's audience logic, evidence selection, chapter progression, and risks, then encode only that route in the Outline `storyline` contract. Do not generate or ask the user to choose among multiple routes.",
        "Apply the named route guidance above: preserve the source-native thesis and major progression, and make any audience or action framing visibly an editorial constraint rather than a source-authored conclusion.",
        "The final Outline is a selective argument, not a directory of source sections. Preserve every source fact in traceability where needed, but give page-forming weight only to the chosen route and the semantic model's P0/core propositions.",
        "Present the completed chapter/page Outline to the user for review before page-detail authoring.",
        "After page-detail authoring, present the detailed page content to the user: readable full prose, on-screen text, and the speaker explanation logic. Do this before submitting a final script to any automated gate.",
        "",
    ]
    lines += [
        "## outline_authoring_projection",
        "",
        "This is a structured, de-duplicated editing workset. It is not a new authority artifact. Use its ST/SU IDs to look up the existing semantic-understanding.md, semantic-argument-model.json, and source-truth.json whenever full context is needed.",
        json.dumps(build_outline_authoring_projection(argument_model, truth), ensure_ascii=False, indent=2),
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
    return "\n".join(lines).rstrip() + "\n"


def prepare_page_script_input(project: Path, page_id: str = "") -> str:
    project = project.expanduser().resolve()
    outline = _load(project / "workbench/stages/01-analysis/outline.json")
    records = _records(project)
    pages = [
        item for item in outline.get("pages", [])
        if isinstance(item, dict)
        and item.get("page_type") == "content"
        and (not page_id or item.get("page_id") == page_id)
    ]
    if page_id and not pages:
        raise ValueError(f"content page not found: {page_id}")
    if not PAGE_SCRIPT_AUTHORING_RULES_PATH.is_file():
        raise FileNotFoundError(
            f"required page-script authoring rules do not exist: "
            f"{PAGE_SCRIPT_AUTHORING_RULES_PATH}"
        )
    lines = PAGE_SCRIPT_AUTHORING_RULES_PATH.read_text(encoding="utf-8").split("\n")
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
        lines += [
            "- required Markdown sections: 完整文字稿、文字稿取舍说明（必留上屏/仅讲解/仅追溯）、上屏文字、证据映射、【视觉结构，不上屏】、【演讲者备注】",
            "- write the finished page directly into its chapter draft; do not emit page-contract receipts or control metadata",
        ]
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"
