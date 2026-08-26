"""Lightweight whole-document semantic understanding preparation and audit."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from cyberppt.source_argument_model import (
    MODEL_JSON as SEMANTIC_ARGUMENT_MODEL_NAME,
    SCHEMA as SEMANTIC_ARGUMENT_MODEL_SCHEMA,
    empty_model,
    extract_model,
    load_model,
    render_review_markdown,
    validate_model,
)
from cyberppt.source_document_map import (
    SOURCE_HEADING_TREE,
    SOURCE_MAP_AUDIT,
    SOURCE_REGISTRY,
    SOURCE_UNITS,
    render_units_for_model,
)


SEMANTIC_STAGE = Path("workbench/stages/00-semantic-understanding")
SEMANTIC_ARTIFACT = SEMANTIC_STAGE / "semantic-understanding.md"
SEMANTIC_ARGUMENT_MODEL = SEMANTIC_STAGE / SEMANTIC_ARGUMENT_MODEL_NAME
SEMANTIC_CONTRACT_VERSION = "cyberppt.semantic_authoring.v1"
SEMANTIC_ARGUMENT_MODEL_CONTRACT_VERSION = SEMANTIC_ARGUMENT_MODEL_SCHEMA

REQUIRED_SECTIONS: dict[str, tuple[str, ...]] = {
    "business_subject": ("全文业务主语",),
    "business_objects": ("核心业务对象",),
    "scope": ("空间、时间与服务范围", "空间时间与服务范围"),
    "decision": ("材料意图与决策动作",),
    "source_structure": ("原文结构与论证顺序", "原文结构评估"),
    "foundation_gap": ("现有基础与能力缺口",),
    "goal_support": ("业务目标与支撑手段",),
    "term_table": ("核心概念语义表",),
    "evidence": ("跨章节证据链",),
    "state_boundary": ("状态、主体与边界",),
    "unresolved": ("待核事项与禁止推断",),
}

PLACEHOLDERS = ("待生成", "待分析", "待补充", "TODO", "TBD", "待填写")
ABSTRACT_SUBJECTS = {
    "平台", "能力", "体系", "工程", "机制", "场景", "模型", "数据", "服务", "建设"
}
DECISION_ACTIONS = ("理解", "审议", "决策", "协调", "部署", "评估", "验收", "确认", "启动")


def _source_headings(source_map: dict[str, Any]) -> list[str]:
    """Return source-native top-level headings from the canonical tree."""

    headings = source_map.get("headings")
    if not isinstance(headings, list):
        return []
    result = [
        str(item.get("title") or "").strip()
        for item in headings
        if isinstance(item, dict)
        and item.get("level") == 1
        and str(item.get("title") or "").strip()
    ]
    return list(dict.fromkeys(result))


def semantic_template() -> str:
    return """# 全文语义理解

> 本文件是 Source Truth 的强制上游约束。必须完整读取全部源材料后填写；不得从目录、摘要、关键词或既有项目材料直接推断。

## 全文业务主语

> 待生成。写出材料究竟要研究、建设、评估或推动的完整业务事项，不能只写“平台、能力、体系、工程、数据服务”。

## 核心业务对象

> 待生成。说明材料具体组织、运营、分析、预测、评估或服务什么对象。

## 空间、时间与服务范围

> 待生成。说明组织层级、时间阶段、业务场景、服务对象和成果使用范围。

## 材料意图与决策动作

### 作者写作目的

> 待生成。不能只写“受众需要理解什么”；要回答作者希望通过这份材料推动什么业务关系、形成什么共同判断或启动什么后续动作，并区分“方案讨论/建议”与“已经决定”。

### 论证方式

> 待生成。按原文顺序说明作者用哪些论证步骤逐步收敛到写作目的；每一步写清它回答的问题、承接的上一步和对下一步的作用，不预设固定故事模板。

### 论证支撑

> 待生成。逐项列出作者实际采用的事实、数据、能力、机制、案例、组织安排或阶段动作，并标注其来源与状态；没有出现在原文中的支撑类型不得补写。

### 受众决策动作

> 待生成。说明受众需要理解、审议、确认、协调、启动、部署或验收什么；它是作者目的的接受端，不等同于作者目的本身。

## 原文结构与论证顺序

> 待生成。逐章说明原文回答的问题、章节之间的承接关系，以及哪些标题层级和表达顺序必须保留。

## 现有基础与能力缺口

> 待生成。区分已经具备、正在建设、尚未形成和条件成熟后实施的内容。

## 业务目标与支撑手段

> 待生成。先写业务目标，再说明数据、模型、平台、工具和组织机制分别如何支撑。

## 核心概念语义表

| 原文简称 | 完整含义 | 适用上下文 | 禁止误读 |
|---|---|---|---|
| 待生成 | 待生成 | 待生成 | 待生成 |

## 跨章节证据链

> 待生成。每项核心语义结论至少连接两处可回查的章节、表格或段落；单一证据时说明限制。

## 状态、主体与边界

> 待生成。区分已有、在建、拟建、建议、待确认、探索和条件成熟后；区分牵头、建设、运营、供给、审核、发布和使用主体。

## 待核事项与禁止推断

> 待生成。列出缺少来源、授权、范围、预算、目标值或责任确认的事项，以及后续不得自行补出的结论。

## 源材料论点模型（机器可读）

> 这一段必须在语义理解阶段完成。它不是提纲，也不是页面清单；它把源材料的主论点、章节论点、论证关系、证据、主体、状态、缺口和 MECE 分区固化为后续阶段唯一可消费的语义合同。

<!-- semantic-argument-model -->
```json
{
  "schema": "cyberppt.semantic_argument_model.v1",
  "version": 1,
  "interpretation_contract_mode": "strict",
  "document_semantics": {
    "document_role": "",
    "subject_of_report": "",
    "primary_thesis": "",
    "decision_boundary": "",
    "author_purpose": "",
    "argument_method": [],
    "supporting_basis": [],
    "business_objects": [],
    "scope": "",
    "decision_intent": ""
  },
  "document_thesis": {
    "statement": "",
    "argument_role": "thesis",
    "argument_weight": "core",
    "status": "mixed",
    "evidence_refs": [],
    "actor_refs": [],
    "claim_origin": "source_explicit"
  },
  "section_nodes": [],
  "subsection_nodes": [],
  "argument_relations": [],
  "mece_rules": {
    "partition_basis": "",
    "exhaustive_scope": "",
    "overlap_policy": "",
    "groups": [],
    "review_notes": []
  },
  "inference_register": [],
  "concept_occurrence_graph": {
    "concepts": [],
    "relations": [],
    "review_notes": []
  },
  "source_coverage": {
    "assignments": [],
    "intentional_omissions": [],
    "review_notes": []
  },
  "semantic_content_unit_coverage_mode": "required",
  "source_gaps": []
}
```
"""


def semantic_authoring_contract() -> str:
    return """You are the whole-document semantic editor for CyberPPT Stage 00.

Read every source extract in this package before writing. Do not use prior projects, archived Stage 01 artifacts, existing outlines, page scripts, keyword summaries, or generic consulting storylines as semantic authority.

Write the canonical output only to the declared `semantic-argument-model.json` artifact. `semantic-check` deterministically renders `semantic-understanding.md` from that model for human review; do not author a second prose interpretation. Determine the full business subject, concrete objects, actors, source-native chapter order, temporal/status distinctions, decision intent, concept boundaries, and cross-section evidence chains before considering slide structure.

Hard requirements:
- Preserve the source document's authoritative first-level structure and argument order unless the source itself supports a different relation.
- Distinguish systems/infrastructure, their role in a wider system, organizations, operating entities, partners, customers, and service objects. Never merge adjacent concepts merely because they co-occur.
- Distinguish existing facts, work in progress, plans, cooperation concepts, items pending investigation, and next-step recommendations.
- Treat scope, authorization, security, uncertainty, and contract terms as constraints. Do not promote them into the semantic center unless they are the source's actual business subject.
- Do not invent causality, necessity, exclusivity, commitments, outcomes, prices, responsibilities, or maturity.
- Cite paragraph/table identifiers from the source extract for the most important semantic conclusions.
- Record unresolved items and forbidden inferences explicitly.
- In the marked JSON block, declare one `document_thesis`, every source-native first-level chapter as a `section_node`, every child heading that carries an independent proposition as a `subsection_node`, and the evidence-backed `argument_relations` between them. Do not collapse distinct semantic dimensions merely because they reuse the same object or vocabulary.
- Separate `argument_weight` from `argument_role` and from `argument_relations`. Use `core` for an independent source proposition that must remain visible in the directed story, `supporting` for proof or expansion modules, `detail` for retained granularity, and `constraint` for conditions/boundaries. A node can support or map to another node and still be `core`; `supports` or `maps_to` never means "支撑层" and must not downgrade the `argument_weight` of either endpoint. Declare `argument_weight` once, directly on the node — do not also maintain a separate weighting summary.
- Also complete `document_semantics` with the document role, subject of report, exact primary thesis, decision/maturity boundary, **author_purpose**, an ordered **argument_method**, explicit **supporting_basis**, concrete business objects, scope, and audience decision intent. `author_purpose` must state what the author is trying to advance; `argument_method` must reconstruct the source's actual sequence of claims and questions; `supporting_basis` must identify only the evidence types the author actually uses. These fields are produced here and must be copied downstream; Source Truth and Outline must not re-infer them from evidence records.
- Every node must declare its source heading, thesis, argument role, actor references, status, evidence references, and `primary_consumer`. `primary_consumer` identifies the later chapter/page mission that should carry the node; it is not permission to create a page automatically.
- Every section/subsection node must also declare `level` consistent with its source heading hierarchy and an explicit `argument_weight`; a lower-level item must not be flattened into a higher-level peer merely because its wording sounds important. Every heading in the supplied original heading tree must be interpreted by exactly one section/subsection node with a matching `source_heading` and `level` — a heading is structural evidence, not automatically a fact or a slide title, but it may not go uninterpreted either.
- Set `interpretation_contract_mode` to `strict`. Use stable `SU-*` source-unit identifiers in all evidence fields; legacy `Sxxxx` identifiers are not valid source evidence in this mode.
- Classify every thesis, semantic node, and argument relation with `claim_origin`: `source_explicit`, `source_implied`, or `editorial_hypothesis`. Register every implied claim in `inference_register` with its basis, affected nodes, and handling. Editorial hypotheses may be recorded only as Director candidates in the inference register; they may not be promoted into the source-native thesis, nodes, or argument relations.
- Optionally build `concept_occurrence_graph` for terms or objects repeated in multiple source locations when a repetition is genuinely ambiguous (same meaning vs. different dimension vs. homonym). This is an advisory aid, not a required inventory — only fill it in where a real reader would otherwise be confused; repetition alone is not proof that two passages are duplicates or should become one page.
- Set `semantic_content_unit_coverage_mode` to `required`; this is the default strict contract, not an opt-in audit. Treat source completeness as a disposition problem, not a keyword-sampling problem. In `source_coverage.assignments`, place every substantive paragraph, list item, table or other non-heading `SU-*` unit under one or more section/subsection nodes whose thesis actually carries that information. The assigned unit must also appear in the target node's `evidence_refs`.
- A source-unit assignment may not rely on `summary` alone. Add `atomic_items`; each item must contain `item_id`, a source-faithful `statement`, `source_unit_refs`, `status`, `argument_duty`, and at least two source-specific `coverage_anchors`. `argument_duty` must state the item's actual role in the local source argument: `premise`, `driver`, `consequence`, `gap`, `response`, `support`, `detail`, `boundary`, or `metadata`. It is not inferred from heading position, visual type, or keywords downstream. Preserve named business objects, actors, actions, processing targets, conditions, states and numeric facts in the item; use optional machine-readable `actors`, `conditions`, and `numeric_facts` arrays when present. If one source unit contains independently removable premises, drivers, consequences, gaps, responses, different statuses, or metadata (cover titles, subtitles, author/organization lines, dates, catalog labels), split it into multiple atomic items so each keeps one coherent claim and duty. Every assigned source unit must occur in at least one atomic item.
- Do not map an atomic item to a node merely because the heading is nearby; its `status` must be compatible with the target semantic node's status, otherwise correct the classification or split the item.
- If a source unit is deliberately excluded from the semantic model, list it in `source_coverage.intentional_omissions` with `source_unit_refs` and a specific editorial reason. Units supporting `core` or `constraint` nodes, and units supporting an independently headed `supporting` node with at least six evidence units, are protected: omission additionally requires `user_authorized_omission: true` and a concrete `user_decision_ref`. An unassigned source unit, a generic reason such as “not important”, or a coverage list that is not bound to a semantic node is invalid.
- Preserve argument prerequisites as first-class semantic content: overall policy/industry background, causal premises, business changes, named objects, duties, processing targets, operating actions, participants, quantitative facts and explicit conditions must not disappear merely because a later paragraph states a more compact conclusion.
- Every argument relation must declare `weight_effect: "none"`; relation type describes how propositions connect, not their narrative importance.
- Write the marked JSON block as real UTF-8 text. Never replace source language with `?`, the Unicode replacement character, mojibake, or an empty evidence/actor field; the Stage 00 audit will reject lossy text before any downstream artifact can consume it.
- Declare `mece_rules` with the partition basis, exhaustive scope, overlap policy, and one or more `groups` that enumerate each checked sibling partition (`parent_id`, `node_ids`, `partition_basis`, `exhaustive_scope`, `overlap_policy`). If two source sections use similar words for different dimensions, keep both nodes and state the dimension relation instead of deleting one.
- Declare `source_gaps` for missing completion facts, implementation conditions, responsible parties, acceptance metrics, demand validation, rights/authorization, or commercial terms. State how the gap must be expressed later; never turn a gap into a fact or a commitment.

This task ends after producing the canonical semantic-argument-model.json. Do not create Source Truth, an Outline, page scripts, images, or PPTX.
"""


def _render_model_input(
    project: Path,
    receipts: list[dict[str, Any]],
    source_map: dict[str, Any],
    rendered_sources: list[tuple[dict[str, Any], str]],
    *,
    include_hashes: bool = True,
) -> str:
    lines = [
        "# CyberPPT whole-document semantic model task",
        "",
        f"- contract: `{SEMANTIC_CONTRACT_VERSION}`",
        f"- project: `{project}`",
        f"- canonical_output: `{project / SEMANTIC_ARGUMENT_MODEL}`",
        f"- generated_review: `{project / SEMANTIC_ARTIFACT}`",
        "## Model contract",
        "",
        semantic_authoring_contract().rstrip(),
        "",
        "## Required output skeleton",
        "",
        (
            semantic_template().rstrip()
            if include_hashes
            else json.dumps(empty_model(), ensure_ascii=False, indent=2)
        ),
    ]
    lines += [
        "",
        "## Canonical source-map contract",
        "",
        "The following extracts are compiled from the original heading tree and stable source units. "
        "Use the exact `SU-*` identifiers for semantic evidence. A heading is structural evidence, "
        "not automatically a factual claim; interpret its semantic function before assigning weight or origin.",
        "",
        "### Original heading tree",
        "",
        json.dumps(source_map.get("headings", []), ensure_ascii=False, indent=2),
    ]
    receipt_by_path = {str(item["path"]): item for item in receipts}
    for source, extract in rendered_sources:
        receipt = receipt_by_path.get(str(source["path"]), source)
        lines += [
            "",
            f"## Source units: {source['path']}",
            "",
            f"- source_id: `{source['source_id']}`",
            f"- bytes: {receipt['bytes']}",
            "",
            "```text",
            extract.rstrip(),
            "```",
        ]
    return "\n".join(lines).rstrip() + "\n"


def _load_existing_source_map(project: Path) -> dict[str, Any]:
    """Load the already-checked source map without regenerating control files."""

    paths = {
        "audit": project / SOURCE_MAP_AUDIT,
        "registry": project / SOURCE_REGISTRY,
        "units": project / SOURCE_UNITS,
        "headings": project / SOURCE_HEADING_TREE,
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise FileNotFoundError(
            "lightweight semantic preparation requires an existing source map; "
            f"run prepare-source-map and source-map-check first. Missing: {missing}"
        )
    audit = json.loads(paths["audit"].read_text(encoding="utf-8-sig"))
    registry = json.loads(paths["registry"].read_text(encoding="utf-8-sig"))
    heading_tree = json.loads(paths["headings"].read_text(encoding="utf-8-sig"))
    if not isinstance(audit, dict) or audit.get("status") != "passed":
        raise ValueError("source map has not passed source-map-check")
    if not isinstance(registry, dict) or not isinstance(registry.get("sources"), list):
        raise ValueError(f"invalid source registry: {paths['registry']}")
    if not isinstance(heading_tree, dict) or not isinstance(heading_tree.get("headings"), list):
        raise ValueError(f"invalid source heading tree: {paths['headings']}")
    units: list[dict[str, Any]] = []
    for line_number, raw in enumerate(
        paths["units"].read_text(encoding="utf-8-sig").splitlines(), start=1
    ):
        if not raw.strip():
            continue
        item = json.loads(raw)
        if not isinstance(item, dict) or not str(item.get("unit_id") or "").strip():
            raise ValueError(f"invalid source unit at {paths['units']}:{line_number}")
        units.append(item)
    if not units:
        raise ValueError(f"source unit registry is empty: {paths['units']}")
    return {
        **audit,
        "sources": registry["sources"],
        "headings": heading_tree["headings"],
        "unit_ids": [str(item["unit_id"]) for item in units],
        "content_unit_ids": [
            str(item["unit_id"])
            for item in units
            if str(item.get("kind") or "").lower() != "heading"
            and str(item.get("text") or "").strip()
        ],
    }


def _source_content_unit_ids(project: Path) -> list[str]:
    """Return substantive non-heading units that require an explicit disposition."""

    path = project / SOURCE_UNITS
    result: list[str] = []
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        if not raw.strip():
            continue
        item = json.loads(raw)
        unit_id = str(item.get("unit_id") or "").strip()
        if (
            unit_id
            and str(item.get("kind") or "").lower() != "heading"
            and str(item.get("text") or "").strip()
        ):
            result.append(unit_id)
    return result


def prepare_semantic_understanding(project: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise FileNotFoundError(f"project does not exist: {project}")
    source_map = _load_existing_source_map(project)
    receipts = [
        {
            "path": str(item.get("path") or ""),
            "bytes": int(item.get("bytes") or 0),
        }
        for item in source_map.get("sources", [])
        if isinstance(item, dict) and item.get("path")
    ]
    if source_map.get("status") != "passed":
        raise ValueError(
            "source map is incomplete; run source-map-check and resolve extraction issues before semantic understanding"
        )
    source_map["content_unit_ids"] = _source_content_unit_ids(project)
    rendered_sources = render_units_for_model(project, prepared=source_map)
    return {
        "schema": "cyberppt.semantic_understanding_input.v1",
        "mode": "lightweight",
        "project": str(project),
        "outputs": [
            str(project / SEMANTIC_ARTIFACT),
            str(project / SEMANTIC_ARGUMENT_MODEL),
        ],
        "semantic_argument_model_required": True,
        "interpretation_contract_mode_required": "strict",
        "source_headings": _source_headings(source_map),
        "source_heading_tree": source_map["headings"],
        "source_unit_ids": source_map["unit_ids"],
        "source_content_unit_ids": source_map.get("content_unit_ids", []),
        "required_sections": [aliases[0] for aliases in REQUIRED_SECTIONS.values()],
        "authoring_task": _render_model_input(
            project,
            receipts,
            source_map,
            rendered_sources,
            include_hashes=False,
        ),
    }


def _heading_sections(text: str) -> dict[str, str]:
    matches = list(re.finditer(r"(?m)^(#{2,4})\s+(.+?)\s*$", text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        level = len(match.group(1))
        end = len(text)
        for following in matches[index + 1:]:
            if len(following.group(1)) <= level:
                end = following.start()
                break
        sections[match.group(2).strip()] = text[match.end():end].strip()
    return sections


def _section(sections: dict[str, str], aliases: tuple[str, ...]) -> str:
    for title, body in sections.items():
        if any(alias in title for alias in aliases):
            return body
    return ""


def _substantive(body: str, minimum: int = 24) -> bool:
    compact = re.sub(r"\s+", "", body)
    return len(compact) >= minimum and not any(
        token.casefold() in body.casefold() for token in PLACEHOLDERS
    )


def _table_data_rows(body: str) -> int:
    count = 0
    for line in body.splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if not cells or cells[0] in {"原文简称", "---"} or set(cells[0]) == {"-"}:
            continue
        count += 1
    return count


def run_semantic_understanding_audit(project: Path) -> tuple[int, dict[str, Any]]:
    project = project.expanduser().resolve()
    prepared = prepare_semantic_understanding(project)
    artifact = project / SEMANTIC_ARTIFACT
    argument_model_path = project / SEMANTIC_ARGUMENT_MODEL
    argument_model: dict[str, Any] | None = None
    if argument_model_path.is_file():
        argument_model = load_model(argument_model_path)
        artifact.parent.mkdir(parents=True, exist_ok=True)
        artifact.write_text(
            render_review_markdown(argument_model),
            encoding="utf-8",
            newline="\n",
        )
    if not artifact.is_file():
        raise FileNotFoundError(
            "semantic argument model is missing; author the canonical JSON at "
            f"{argument_model_path} and rerun semantic-check"
        )
    text = artifact.read_text(encoding="utf-8-sig")
    sections = _heading_sections(text)
    issues: list[dict[str, Any]] = []
    resolved: dict[str, str] = {}
    for key, aliases in REQUIRED_SECTIONS.items():
        body = _section(sections, aliases)
        resolved[key] = body
        if not body:
            issues.append({
                "code": "SEMANTIC_SECTION_MISSING",
                "message": f"缺少全文语义理解章节：{aliases[0]}",
                "section": aliases[0],
            })
        elif not _substantive(body):
            issues.append({
                "code": "SEMANTIC_SECTION_SHALLOW",
                "message": f"全文语义理解章节内容过浅或仍为占位：{aliases[0]}",
                "section": aliases[0],
            })

    if argument_model is None:
        argument_model = extract_model(text)
    required_model = bool(prepared.get("semantic_argument_model_required"))
    strict_interpretation = bool(
        isinstance(argument_model, dict)
        and argument_model.get("interpretation_contract_mode") == "strict"
    )
    argument_model_issues = validate_model(
        argument_model,
        required_headings=prepared.get("source_headings") or [],
        required_heading_records=prepared.get("source_heading_tree") or [],
        source_unit_ids=set(prepared.get("source_unit_ids") or []),
        required_content_unit_ids=set(
            prepared.get("source_content_unit_ids") or []
        ),
        require_document_context=required_model,
    )
    if argument_model is None and not required_model:
        # Legacy text-only callers may still use the prose-only semantic
        # contract.  Do not pretend that it supplies a consumable argument
        # model; downstream strict workflows will require the structured form.
        argument_model_issues = []
    if (
        not isinstance(argument_model, dict)
        or argument_model.get("interpretation_contract_mode") != "strict"
    ):
        argument_model_issues.append(
            {
                "code": "SEMANTIC_INTERPRETATION_MODE_REQUIRED",
                "message": "该项目启用了严格解读合同，语义模型必须声明 interpretation_contract_mode=strict。",
            }
        )
    for item in argument_model_issues:
        issues.append({
            "code": item["code"],
            "message": item["message"],
            "section": "源材料论点模型（机器可读）",
            **({"node_id": item["node_id"]} if item.get("node_id") else {}),
        })
    if required_model and isinstance(argument_model, dict):
        context = argument_model.get("document_semantics")
        if isinstance(context, dict):
            if not str(context.get("author_purpose") or "").strip():
                issues.append({
                    "code": "SEMANTIC_AUTHOR_PURPOSE_MISSING",
                    "message": "正式语义模型必须区分作者写作目的与受众决策动作，并声明 author_purpose。",
                    "section": "材料意图与决策动作",
                })
            for field, label in (
                ("argument_method", "论证方式"),
                ("supporting_basis", "论证支撑"),
            ):
                value = context.get(field)
                if not isinstance(value, list) or not value:
                    issues.append({
                        "code": "SEMANTIC_ARGUMENT_SUPPORT_MISSING",
                        "message": f"正式语义模型必须声明非空的 {field}（{label}）数组。",
                        "section": "材料意图与决策动作",
                    })
                    continue
                for index, item in enumerate(value):
                    refs = item.get("source_refs") if isinstance(item, dict) else None
                    if not isinstance(item, dict) or not isinstance(refs, list) or not refs:
                        issues.append({
                            "code": "SEMANTIC_ARGUMENT_SUPPORT_UNANCHORED",
                            "message": f"{field}[{index}] 必须是带 source_refs 的源材料论证记录。",
                            "section": "材料意图与决策动作",
                        })
    if argument_model is not None:
        argument_model_path.write_text(
            json.dumps(argument_model, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    elif argument_model_path.exists() and required_model:
        # A stale compiled model must not survive a missing source block.
        argument_model_path.write_text("{}\n", encoding="utf-8", newline="\n")

    subject = re.sub(r"\s+", "", resolved.get("business_subject", ""))
    if subject and subject.strip("，。；：、,.!?！？") in ABSTRACT_SUBJECTS:
        issues.append({
            "code": "BUSINESS_SUBJECT_ABSTRACT",
            "message": "全文业务主语只有抽象词，没有具体业务方向、对象和范围。",
            "section": "全文业务主语",
        })
    decision = resolved.get("decision", "")
    if decision and not any(action in decision for action in DECISION_ACTIONS):
        issues.append({
            "code": "DECISION_ACTION_MISSING",
            "message": "材料意图没有明确受众需要理解、审议、确认、协调、启动、部署、评估或验收什么。",
            "section": "材料意图与决策动作",
        })
    if resolved.get("term_table") and _table_data_rows(resolved["term_table"]) < 1:
        issues.append({
            "code": "SEMANTIC_TERM_TABLE_EMPTY",
            "message": "核心概念语义表至少需要一条有效记录。",
            "section": "核心概念语义表",
        })

    report = {
        "schema": "cyberppt.semantic_understanding_audit.v1",
        "status": "passed" if not issues else "rewrite_required",
        "artifact": str(artifact),
        "semantic_argument_model_schema": SEMANTIC_ARGUMENT_MODEL_CONTRACT_VERSION,
        "semantic_argument_model_required": required_model,
        "interpretation_contract_mode": (
            argument_model.get("interpretation_contract_mode", "legacy")
            if isinstance(argument_model, dict)
            else "legacy"
        ),
        "semantic_argument_model": str(argument_model_path) if argument_model is not None else None,
        "argument_model_summary": {
            "section_nodes": len(argument_model.get("section_nodes", [])) if isinstance(argument_model, dict) and isinstance(argument_model.get("section_nodes"), list) else 0,
            "subsection_nodes": len(argument_model.get("subsection_nodes", [])) if isinstance(argument_model, dict) and isinstance(argument_model.get("subsection_nodes"), list) else 0,
            "argument_relations": len(argument_model.get("argument_relations", [])) if isinstance(argument_model, dict) and isinstance(argument_model.get("argument_relations"), list) else 0,
            "heading_semantic_cards": len(argument_model.get("heading_semantic_cards", [])) if isinstance(argument_model, dict) and isinstance(argument_model.get("heading_semantic_cards"), list) else 0,
            "inference_records": len(argument_model.get("inference_register", [])) if isinstance(argument_model, dict) and isinstance(argument_model.get("inference_register"), list) else 0,
            "repeated_concepts": len(argument_model.get("concept_occurrence_graph", {}).get("concepts", [])) if isinstance(argument_model, dict) and isinstance(argument_model.get("concept_occurrence_graph"), dict) and isinstance(argument_model.get("concept_occurrence_graph", {}).get("concepts"), list) else 0,
            "source_gaps": len(argument_model.get("source_gaps", [])) if isinstance(argument_model, dict) and isinstance(argument_model.get("source_gaps"), list) else 0,
        },
        "sections_present": sum(bool(value) for value in resolved.values()),
        "sections_required": len(REQUIRED_SECTIONS),
        "issues": issues,
        "mode": "lightweight",
    }
    return (0 if not issues else 4), report
