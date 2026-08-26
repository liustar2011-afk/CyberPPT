"""Generate human- and machine-readable semantic-intent shadow audits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cyberppt.script_quality_contract import parse_script_path
from scripts.imagegen_pipeline.imagegen_handoff import audit_page_semantic_intent


def build_audit(script: Path) -> dict[str, object]:
    document = parse_script_path(script)
    pages: list[dict[str, object]] = []
    prior_carriers: list[str] = []
    for page in document.pages:
        if page.page_type != "content":
            continue
        record = audit_page_semantic_intent(page, prior_carriers=tuple(prior_carriers))
        pages.append(record)
        prior_carriers.append(str(record["visual_carrier"]["selected"]))
    deck_warnings: list[dict[str, object]] = []
    for index in range(2, len(pages)):
        window = pages[index - 2:index + 1]
        intents = {str(item["primary_intent"]) for item in window}
        carriers = {
            str(item["visual_carrier"]["selected"])
            for item in window
        }
        if len(intents) == 1 and len(carriers) == 1:
            deck_warnings.append(
                {
                    "code": "DECK_THREE_PAGE_STRUCTURE_REPEAT",
                    "pages": [str(item["page_id"]) for item in window],
                    "intent": str(window[0]["primary_intent"]),
                    "carrier": str(window[0]["visual_carrier"]["selected"]),
                }
            )
    return {
        "schema": "cyberppt.semantic-intent-audit.v1",
        "script": str(script.resolve()),
        "content_page_count": len(pages),
        "difference_count": sum(not bool(page["legacy_matches"]) for page in pages),
        "semantic_refinement_count": sum(bool(page["semantic_refinement"]) for page in pages),
        "blocking_issue_count": sum(len(page["blocking_issues"]) for page in pages),
        "deck_warnings": deck_warnings,
        "pages": pages,
    }


def render_markdown(audit: dict[str, object]) -> str:
    lines = [
        "# 页面语义意图影子审计",
        "",
        f"- 内容页：{audit['content_page_count']}",
        f"- 新旧分类差异：{audit['difference_count']}",
        f"- 细分类待确认：{audit['semantic_refinement_count']}",
        f"- 阻断问题：{audit['blocking_issue_count']}",
        f"- 整套节奏警告：{len(audit['deck_warnings'])}",
        "",
        "| 页面 | 旧分类 | 新主分类 | 选定载体 | 来源 | 置信度 | 阻断问题 |",
        "|---|---|---|---|---|---:|---|",
    ]
    for page in audit["pages"]:
        issues = "、".join(page["blocking_issues"]) or "—"
        lines.append(
            f"| {page['page_id']} {page['page_title']} | {page['legacy_intent']} | "
            f"{page['primary_intent']} | {page['visual_carrier']['selected']} | {page['source']} | "
            f"{page['confidence']:.2f} | {issues} |"
        )
    lines.extend(["", "## 逐页证据", ""])
    for page in audit["pages"]:
        evidence = "；".join(page["evidence"]) or "无显式证据，采用安全回退"
        relations = "、".join(page["supporting_relations"]) or "—"
        lines.extend(
            [
                f"### {page['page_id']}｜{page['page_title']}",
                "",
                f"- 来源关系：{relations}",
                f"- 识别证据：{evidence}",
                f"- 空间组织：{page['composition']['spatial_organization']}",
                f"- 阅读路径：{' → '.join(page['composition']['reading_path'])}",
                f"- 选定载体：{page['visual_carrier']['selected']}",
                f"- 构图交接：{page['composition_guidance']}",
                f"- 新旧兼容：{'一致' if page['legacy_matches'] else '需人工复核'}",
                "",
            ]
        )
    return "\n".join(lines)


def build_override_proposal(audit: dict[str, object]) -> dict[str, object]:
    proposals = []
    for page in audit["pages"]:
        if not page["semantic_refinement"]:
            continue
        proposals.append(
            {
                "page_id": page["page_id"],
                "page_title": page["page_title"],
                "current_visual_intent_type": page["legacy_intent"],
                "current_canonical_intent": page["legacy_canonical_intent"],
                "proposed_semantic_intent_type": page["primary_intent"],
                "secondary_intents": page["secondary_intents"],
                "confidence": page["confidence"],
                "evidence": page["evidence"],
                "recommended_carrier": page["visual_carrier"]["selected"],
                "status": "pending_user_approval",
            }
        )
    return {
        "schema": "cyberppt.semantic-intent-override-proposal.v1",
        "source_script": audit["script"],
        "approval_effect": "none",
        "instructions": (
            "Review each proposal against Source Truth and the approved page contract. "
            "Copy semantic_intent_type into the active override only after user approval."
        ),
        "proposals": proposals,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("script", type=Path)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    parser.add_argument("--proposal-output", type=Path)
    args = parser.parse_args(argv)
    audit = build_audit(args.script)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(
        json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    args.markdown_output.write_text(render_markdown(audit) + "\n", encoding="utf-8", newline="\n")
    if args.proposal_output is not None:
        args.proposal_output.parent.mkdir(parents=True, exist_ok=True)
        args.proposal_output.write_text(
            json.dumps(build_override_proposal(audit), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return 1 if audit["blocking_issue_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
