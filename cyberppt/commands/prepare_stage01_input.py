"""Compile deterministic Stage 01 authoring inputs."""

from __future__ import annotations

import json
from pathlib import Path


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


def prepare_outline_input(project: Path) -> Path:
    project = project.expanduser().resolve()
    truth = _load(project / "workbench/stages/01-analysis/source-truth.json")
    records = {
        str(item.get("id")): item
        for item in truth.get("records", [])
        if isinstance(item, dict) and item.get("id")
    }
    lines = [
        "# Outline authoring input",
        "",
        "Set root `visible_judgment_mode` to `required` for formal projects.",
        "Create the Outline from Source Truth. Use canonical field names:",
        "`page_job`, `business_question`, `main_message`, "
        "`onscreen_judgment`, "
        "`judgment_role`, "
        "`onscreen_judgment_mode`, "
        "`new_value_vs_previous`, `reserved_for_later`, `proof_points`, "
        "`visual_intent_type`.",
        "",
        "## coverage_targets",
        "",
    ]
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
            f"- {source_id} [{record.get('claim_role') or record.get('type', '')}; "
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
        "Each content page must define:",
        "- `page_job`",
        "- `business_question`",
        "- `main_message`",
        "- `subtitle`: a concise audience-facing compression of `main_message`, "
        "normally no more than 30 Chinese characters; preserve decisive numbers, "
        "business objects, and the judgment without repeating the page title",
        "- `onscreen_judgment`: retain the approved full judgment as semantic "
        "composition metadata; when `subtitle` carries it, use `semantic_only` "
        "so the body image does not repeat it",
        "- `judgment_role`: use `relationship`, `positioning`, `boundary`, or "
        "`mechanism` when the judgment should normally be proven visually; use "
        "`fact`, `metric`, `milestone`, `acceptance`, or `prohibition` when it "
        "should normally remain verbatim-visible",
        "- `上屏文字` must remain independently readable after compression: preserve "
        "the page's essential evidence, explanatory relation, causal chain, and "
        "implication or handoff instead of reducing the prose to labels and keywords",
        "- `new_value_vs_previous`",
        "- `reserved_for_later`",
        "- `proof_points`: claim, source_refs, consumption",
        "- `visual_intent_type`: optional explicit ImageGen relationship type. Use one of "
        "`judgment_evidence`, `boundary_guardrail`, `hierarchy_support`, "
        "`decision_admission`, `comparison`, "
        "`scenario_application`, `multi_semantic_foundation`, `causal`, "
        "`closed_loop`, `phase`, `capability_relationship`; omit it when the "
        "relationship is not yet clear.",
        "- `visual_proof`: optional one-sentence statement of how the visual relationship "
        "proves `main_message`; omit it when the relationship template is sufficient.",
        "",
        "Before creating `proof_points`, screen each candidate against `page_job`, `business_question`, and `main_message`.",
        "- Keep a candidate only when it directly establishes the page judgment or a necessary step in answering the page question.",
        "- Boundary or unresolved records default to `boundary_refs`; use them as primary proof only when the page itself defines positioning, scope, assurance conditions, or a decision.",
        "- When several records establish one implication, consolidate them into one proof point instead of listing each record as an independent direction.",
        "- Keep at most three primary proof directions on one page; move unrelated material to its actual topic page or reserve it for later.",
    ]
    output = project / "workbench/stages/01-analysis/outline-authoring-input.md"
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output


def prepare_page_script_input(project: Path, page_id: str = "") -> Path:
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
    lines = [
        "# Page script authoring input",
        "",
        "Write full prose first; derive on-screen text from it.",
        "Every content page must place `副标题` before `上屏结论` and `上屏文字`. "
        "The template subtitle carries the concise judgment; body on-screen text "
        "carries the page's own evidence, relationships, and business implications.",
        "When migrating an already approved script to this subtitle rule, preserve "
        "its existing `上屏文字` unchanged. Only add or update `副标题`, retain the "
        "full judgment as semantic metadata, and set the appropriate display mode.",
        "Derive the default display policy from `judgment_role`: relationship/positioning/boundary/mechanism become `semantic_only`; fact/metric/milestone/acceptance/prohibition become `locked`. Use `onscreen_judgment_mode` only as an explicit override.",
        "Emit `onscreen_judgment` in the completed Chinese script as `- 上屏结论：...` without terminal punctuation.",
        "The visible layer must be independently readable without speaker narration.",
        "Write `上屏文字` as a focused body story: source-supported evidence → "
        "explanation or causal relation → implication or handoff. "
        "Do not repeat the page title or subtitle inside the body.",
        "Boundary is opt-in, never a mandatory fourth beat. Only pages whose declared "
        "business subject is scope, admission, safety, governance, quality, compliance, "
        "risk, assurance, deployment, capacity, degradation, or acceptance may show boundary or "
        "constraint modules. On all other pages, keep boundary material in internal "
        "controls and never create labels such as 质量边界、质量要求、安全边界 or 约束条件.",
        "Do not compress the full prose into module labels plus keywords. Preserve every fact, number, and relation needed to understand why the conclusion follows; preserve a limitation only when the limitation is itself part of the declared page subject.",
        "Count only Chinese, Latin, and numeric characters: target roughly 50% of the full prose, with a hard minimum of 220 and a cap target of 320 visible characters.",
        "Use at least two evidence-bearing on-screen lines. The visible conclusion may also carry the implication or handoff; do not add formulaic 因此/由此 wording only to satisfy the contract.",
        "`reserved_for_later`, `boundary_refs`, and `boundary_constraints` are internal controls only.",
        "They must not be copied into coaching tips or speaker notes. State a constraint only when it is the page's declared business subject.",
        "",
    ]
    for page in pages:
        lines += [
            f"## {page.get('page_id')} {page.get('title')}",
            f"- page_job: {page.get('page_job', '')}",
            f"- business_question: {page.get('business_question', '')}",
            f"- main_message: {page.get('main_message', '')}",
            f"- onscreen_judgment: {page.get('onscreen_judgment', '')}",
            f"- judgment_role: {page.get('judgment_role', '')}",
            f"- onscreen_judgment_mode: {page.get('onscreen_judgment_mode', 'auto')}",
            f"- new_value_vs_previous: {page.get('new_value_vs_previous', '')}",
            f"- reserved_for_later: {page.get('reserved_for_later', '')}",
            f"- visual_intent_type: {page.get('visual_intent_type') or 'auto'}",
            f"- visual_proof: {page.get('visual_proof') or 'auto'}",
            "- proof_points:",
        ]
        for point in page.get("proof_points", []):
            if isinstance(point, dict):
                refs = ", ".join(str(item) for item in point.get("source_refs", []))
                lines.append(f"  - [{point.get('consumption', 'supporting')}] {point.get('claim', '')} ({refs})")
        proof_source_ids = list(
            dict.fromkeys(
                str(source_id)
                for point in page.get("proof_points", [])
                if isinstance(point, dict)
                for source_id in point.get("source_refs", [])
            )
        )
        boundary_source_ids = [
            str(source_id) for source_id in page.get("boundary_refs", [])
        ]
        lines.append("- evidence_text:")
        for source_id in proof_source_ids:
            lines.append(f"  - {source_id}: {records.get(str(source_id), {}).get('statement', '')}")
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
            "page_job": page.get("page_job"),
            "business_question": page.get("business_question"),
            "main_message": page.get("main_message"),
            "onscreen_judgment": page.get("onscreen_judgment"),
            "judgment_role": page.get("judgment_role"),
            "onscreen_judgment_mode": page.get("onscreen_judgment_mode"),
            "new_value_vs_previous": page.get("new_value_vs_previous"),
            "reserved_for_later": page.get("reserved_for_later"),
            "visual_intent_type": page.get("visual_intent_type"),
            "visual_proof": page.get("visual_proof"),
            "proof_points": page.get("proof_points", []),
            "boundary_refs": page.get("boundary_refs", []),
            "new_value_realized": True,
            "reserved_for_later_respected": True,
        }
        lines += [
            "- page_contract_receipt (copy unchanged into the completed page):",
            f"  <!-- cyberppt-page-contract {json.dumps(receipt, ensure_ascii=False, separators=(',', ':'))} -->",
        ]
        lines.append("")
    suffix = f"-{page_id}" if page_id else ""
    output = project / "workbench/scripts" / f"page-script-authoring-input{suffix}.md"
    output.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return output
