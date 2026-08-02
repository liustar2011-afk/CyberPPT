"""Source-bound whole-document semantic understanding gate for Stage 01."""

from __future__ import annotations

import hashlib
import json
import re
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree


SEMANTIC_STAGE = Path("workbench/stages/00-semantic-understanding")
SEMANTIC_ARTIFACT = SEMANTIC_STAGE / "semantic-understanding.md"
SEMANTIC_AUDIT_JSON = SEMANTIC_STAGE / "semantic-understanding-audit.json"
SEMANTIC_AUDIT_MD = SEMANTIC_STAGE / "semantic-understanding-audit.md"
SEMANTIC_MODEL_INPUT = SEMANTIC_STAGE / "semantic-model-input.md"
SEMANTIC_MODEL_INPUT_JSON = SEMANTIC_STAGE / "semantic-model-input.json"
SEMANTIC_GENERATION_RECEIPT = SEMANTIC_STAGE / "semantic-generation-receipt.json"
SEMANTIC_APPROVAL = Path("workbench/approvals/semantic-understanding-approved.json")
SEMANTIC_CONTRACT_VERSION = "cyberppt.semantic_authoring.v1"

_WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

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


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().lower()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def semantic_gate_required(project: Path) -> bool:
    manifest = project.expanduser().resolve() / "manifest.yml"
    if not manifest.is_file():
        return False
    text = manifest.read_text(encoding="utf-8-sig")
    match = re.search(r"(?ms)^gates:\s*\n(?P<body>(?:^[ \t]+.*\n?)*)", text)
    if not match:
        return False
    return bool(
        re.search(
            r"(?m)^\s+semantic_understanding:\s*required\s*$",
            match.group("body"),
        )
    )


def collect_source_receipts(project: Path) -> list[dict[str, Any]]:
    source_dir = project.expanduser().resolve() / "source"
    if not source_dir.is_dir():
        raise FileNotFoundError(f"source directory does not exist: {source_dir}")
    files = sorted(
        path for path in source_dir.rglob("*")
        if path.is_file() and path.name != ".gitkeep"
    )
    if not files:
        raise FileNotFoundError(f"no source files found: {source_dir}")
    return [
        {
            "path": path.relative_to(project).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256_path(path),
        }
        for path in files
    ]


def source_bundle_sha256(receipts: list[dict[str, Any]]) -> str:
    payload = "\n".join(
        f"{item['path']}\t{item['bytes']}\t{item['sha256']}" for item in receipts
    )
    return _sha256_bytes(payload.encode("utf-8"))


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

> 待生成。说明受众需要理解、审议、确认、协调、启动、部署或验收什么。

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
"""


def semantic_authoring_contract() -> str:
    return """You are the whole-document semantic editor for CyberPPT Stage 00.

Read every source extract in this package before writing. Do not use prior projects, archived Stage 01 artifacts, existing outlines, page scripts, keyword summaries, or generic consulting storylines as semantic authority.

Write the output to the declared `semantic-understanding.md` artifact and preserve all eleven required section headings. Determine the full business subject, concrete objects, actors, source-native chapter order, temporal/status distinctions, decision intent, concept boundaries, and cross-section evidence chains before considering slide structure.

Hard requirements:
- Preserve the source document's authoritative first-level structure and argument order unless the source itself supports a different relation.
- Distinguish systems/infrastructure, their role in a wider system, organizations, operating entities, partners, customers, and service objects. Never merge adjacent concepts merely because they co-occur.
- Distinguish existing facts, work in progress, plans, cooperation concepts, items pending investigation, and next-step recommendations.
- Treat scope, authorization, security, uncertainty, and contract terms as constraints. Do not promote them into the semantic center unless they are the source's actual business subject.
- Do not invent causality, necessity, exclusivity, commitments, outcomes, prices, responsibilities, or maturity.
- Cite paragraph/table identifiers from the source extract for the most important semantic conclusions.
- Record unresolved items and forbidden inferences explicitly.

This task ends after producing the semantic-understanding artifact. Do not create Source Truth, an Outline, page scripts, images, or PPTX.
"""


def _docx_source_extract(path: Path) -> str:
    with zipfile.ZipFile(path) as package:
        document = ElementTree.fromstring(package.read("word/document.xml"))
    body = document.find(f"{_WORD_NS}body")
    if body is None:
        raise ValueError(f"DOCX has no document body: {path}")
    lines: list[str] = []
    paragraph_number = 0
    table_number = 0
    for child in body:
        if child.tag == f"{_WORD_NS}p":
            paragraph_number += 1
            text = "".join(node.text or "" for node in child.iter(f"{_WORD_NS}t"))
            style = child.find(f"{_WORD_NS}pPr/{_WORD_NS}pStyle")
            style_id = style.get(f"{_WORD_NS}val") if style is not None else ""
            style_suffix = f"[style={style_id}]" if style_id else ""
            prefix = f"[P{paragraph_number:04d}]{style_suffix}"
            lines.append(f"{prefix} {text}" if text else prefix)
        elif child.tag == f"{_WORD_NS}tbl":
            table_number += 1
            lines.append(f"[TABLE{table_number:03d}]")
            for row_number, row in enumerate(child.findall(f"{_WORD_NS}tr"), 1):
                cells = []
                for cell in row.findall(f"{_WORD_NS}tc"):
                    cells.append("".join(node.text or "" for node in cell.iter(f"{_WORD_NS}t")))
                lines.append(
                    f"[TABLE{table_number:03d}-R{row_number:03d}] " + " | ".join(cells)
                )
    return "\n".join(lines).rstrip() + "\n"


def _source_extract(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix == ".docx":
        return _docx_source_extract(path)
    if suffix in {".txt", ".md", ".json", ".csv", ".tsv", ".yaml", ".yml"}:
        return path.read_text(encoding="utf-8-sig")
    return (
        f"[BINARY SOURCE: {path.name}]\n"
        "The model executor must open and inspect this registered source file directly; "
        "the deterministic compiler does not extract this format.\n"
    )


def _render_model_input(
    project: Path,
    receipts: list[dict[str, Any]],
) -> str:
    lines = [
        "# CyberPPT whole-document semantic model task",
        "",
        f"- contract: `{SEMANTIC_CONTRACT_VERSION}`",
        f"- project: `{project}`",
        f"- output: `{project / SEMANTIC_ARTIFACT}`",
        f"- source_bundle_sha256: `{source_bundle_sha256(receipts)}`",
        "",
        "## Model contract",
        "",
        semantic_authoring_contract().rstrip(),
        "",
        "## Required output skeleton",
        "",
        semantic_template().rstrip(),
    ]
    for receipt in receipts:
        source_path = project / str(receipt["path"])
        lines += [
            "",
            f"## Source extract: {receipt['path']}",
            "",
            f"- bytes: {receipt['bytes']}",
            f"- sha256: `{receipt['sha256']}`",
            "",
            "```text",
            _source_extract(source_path).rstrip(),
            "```",
        ]
    return "\n".join(lines).rstrip() + "\n"


def prepare_semantic_understanding(project: Path) -> dict[str, Any]:
    project = project.expanduser().resolve()
    if not project.is_dir():
        raise FileNotFoundError(f"project does not exist: {project}")
    receipts = collect_source_receipts(project)
    stage = project / SEMANTIC_STAGE
    stage.mkdir(parents=True, exist_ok=True)
    artifact = project / SEMANTIC_ARTIFACT
    if not artifact.exists():
        artifact.write_text(semantic_template(), encoding="utf-8")
    model_input = project / SEMANTIC_MODEL_INPUT
    model_input.write_text(_render_model_input(project, receipts), encoding="utf-8")
    model_input_sha256 = _sha256_path(model_input)
    input_path = stage / "semantic-understanding-input.json"
    payload = {
        "schema": "cyberppt.semantic_understanding_input.v1",
        "contract_version": SEMANTIC_CONTRACT_VERSION,
        "project": str(project),
        "artifact": str(artifact),
        "model_input": str(model_input),
        "model_input_sha256": model_input_sha256,
        "source_bundle_sha256": source_bundle_sha256(receipts),
        "source_receipts": receipts,
        "required_sections": [aliases[0] for aliases in REQUIRED_SECTIONS.values()],
        "prepared_at": _utc_now(),
    }
    input_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (project / SEMANTIC_MODEL_INPUT_JSON).write_text(
        json.dumps(
            {
                "schema": "cyberppt.semantic_model_input.v1",
                "contract_version": SEMANTIC_CONTRACT_VERSION,
                "model_input": str(model_input),
                "model_input_sha256": model_input_sha256,
                "output": str(artifact),
                "source_bundle_sha256": payload["source_bundle_sha256"],
                "source_receipts": receipts,
                "required_sections": payload["required_sections"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return payload


def record_semantic_generation(
    project: Path,
    *,
    executor: str,
    model: str,
    note: str = "",
) -> Path:
    project = project.expanduser().resolve()
    if not executor.strip() or not model.strip():
        raise ValueError("executor and model are required for the semantic generation receipt")
    prepared = prepare_semantic_understanding(project)
    artifact = project / SEMANTIC_ARTIFACT
    if not artifact.is_file():
        raise FileNotFoundError(f"semantic artifact does not exist: {artifact}")
    receipt = {
        "schema": "cyberppt.semantic_generation_receipt.v1",
        "contract_version": SEMANTIC_CONTRACT_VERSION,
        "executor": executor.strip(),
        "model": model.strip(),
        "model_input": prepared["model_input"],
        "model_input_sha256": prepared["model_input_sha256"],
        "semantic_understanding": str(artifact),
        "semantic_understanding_sha256": _sha256_path(artifact),
        "source_bundle_sha256": prepared["source_bundle_sha256"],
        "generated_at": _utc_now(),
        "note": note.strip(),
    }
    output = project / SEMANTIC_GENERATION_RECEIPT
    output.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


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

    receipts = prepared["source_receipts"]
    generation_receipt: dict[str, Any] | None = None
    generation_receipt_path = project / SEMANTIC_GENERATION_RECEIPT
    if semantic_gate_required(project):
        if not generation_receipt_path.is_file():
            issues.append({
                "code": "SEMANTIC_GENERATION_RECEIPT_MISSING",
                "message": "缺少模型执行回执；必须登记执行器、模型及输入输出哈希。",
                "section": "模型执行回执",
            })
        else:
            loaded_receipt = json.loads(
                generation_receipt_path.read_text(encoding="utf-8-sig")
            )
            if not isinstance(loaded_receipt, dict):
                raise ValueError("semantic generation receipt root must be an object")
            generation_receipt = loaded_receipt
            receipt_expectations = (
                ("contract_version", SEMANTIC_CONTRACT_VERSION, "SEMANTIC_CONTRACT_VERSION_STALE"),
                ("model_input_sha256", prepared["model_input_sha256"], "SEMANTIC_MODEL_INPUT_STALE"),
                ("semantic_understanding_sha256", _sha256_path(artifact), "SEMANTIC_MODEL_OUTPUT_STALE"),
                ("source_bundle_sha256", prepared["source_bundle_sha256"], "SEMANTIC_MODEL_SOURCE_STALE"),
            )
            for field, expected, code in receipt_expectations:
                if str(generation_receipt.get(field) or "").casefold() != str(expected).casefold():
                    issues.append({
                        "code": code,
                        "message": f"模型执行回执字段 {field} 与当前任务不一致。",
                        "section": "模型执行回执",
                    })
            if not str(generation_receipt.get("executor") or "").strip():
                issues.append({
                    "code": "SEMANTIC_EXECUTOR_MISSING",
                    "message": "模型执行回执缺少 executor。",
                    "section": "模型执行回执",
                })
            if not str(generation_receipt.get("model") or "").strip():
                issues.append({
                    "code": "SEMANTIC_MODEL_ID_MISSING",
                    "message": "模型执行回执缺少 model。",
                    "section": "模型执行回执",
                })
    report = {
        "schema": "cyberppt.semantic_understanding_audit.v1",
        "status": "passed" if not issues else "rewrite_required",
        "artifact": str(artifact),
        "semantic_understanding_sha256": _sha256_path(artifact),
        "source_bundle_sha256": source_bundle_sha256(receipts),
        "source_receipts": receipts,
        "model_input": prepared["model_input"],
        "model_input_sha256": prepared["model_input_sha256"],
        "generation_receipt": generation_receipt,
        "generation_receipt_sha256": (
            _sha256_path(generation_receipt_path)
            if generation_receipt_path.is_file()
            else None
        ),
        "sections_present": sum(bool(value) for value in resolved.values()),
        "sections_required": len(REQUIRED_SECTIONS),
        "issues": issues,
        "audited_at": _utc_now(),
    }
    audit_json = project / SEMANTIC_AUDIT_JSON
    audit_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    lines = [
        "# 全文语义理解门禁",
        "",
        f"- 状态：**{report['status']}**",
        f"- 章节：{report['sections_present']}/{report['sections_required']}",
        f"- 源材料包 SHA-256：`{report['source_bundle_sha256']}`",
        f"- 模型输入 SHA-256：`{report['model_input_sha256']}`",
        f"- 语义理解 SHA-256：`{report['semantic_understanding_sha256']}`",
        f"- 模型执行回执：{'已绑定' if report['generation_receipt'] else '缺失'}",
        "",
        "## 问题",
        "",
    ]
    if issues:
        lines.extend(f"- `{item['code']}`：{item['message']}" for item in issues)
    else:
        lines.append("- 无。可进入 Source Truth，但本门禁不等同于用户批准页面结构。")
    (project / SEMANTIC_AUDIT_MD).write_text("\n".join(lines) + "\n", encoding="utf-8")
    return (0 if not issues else 4), report


def approve_semantic_understanding(project: Path, note: str = "") -> Path:
    project = project.expanduser().resolve()
    audit_path = project / SEMANTIC_AUDIT_JSON
    if not audit_path.is_file():
        raise FileNotFoundError(
            "semantic audit is missing; run semantic-check before approval"
        )
    audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
    if not isinstance(audit, dict) or audit.get("status") != "passed":
        raise ValueError("semantic understanding must pass semantic-check before approval")
    artifact = project / SEMANTIC_ARTIFACT
    if audit.get("semantic_understanding_sha256") != _sha256_path(artifact):
        raise ValueError("semantic audit is stale; rerun semantic-check before approval")
    receipts = collect_source_receipts(project)
    if audit.get("source_bundle_sha256") != source_bundle_sha256(receipts):
        raise ValueError("source materials changed; rerun semantic-check before approval")
    generation_receipt = project / SEMANTIC_GENERATION_RECEIPT
    if not generation_receipt.is_file():
        raise FileNotFoundError("semantic generation receipt is missing")
    approval = {
        "schema": "cyberppt.semantic_understanding_approval.v1",
        "decision": "approved",
        "semantic_understanding_sha256": audit["semantic_understanding_sha256"],
        "source_bundle_sha256": audit["source_bundle_sha256"],
        "model_input_sha256": audit["model_input_sha256"],
        "generation_receipt_sha256": _sha256_path(generation_receipt),
        "semantic_audit_sha256": _sha256_path(audit_path),
        "approved_at": _utc_now(),
        "note": note.strip(),
    }
    output = project / SEMANTIC_APPROVAL
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(approval, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return output


def assert_semantic_understanding_ready(project: Path) -> dict[str, Any] | None:
    project = project.expanduser().resolve()
    if not semantic_gate_required(project):
        return None
    artifact = project / SEMANTIC_ARTIFACT
    audit_path = project / SEMANTIC_AUDIT_JSON
    if not artifact.is_file() or not audit_path.is_file():
        raise FileNotFoundError(
            "required semantic-understanding gate is missing. Run: "
            f"python -m cyberppt prepare-semantic-understanding {project}"
        )
    report = json.loads(audit_path.read_text(encoding="utf-8-sig"))
    if report.get("status") != "passed":
        raise ValueError(
            "semantic-understanding gate is not passed. Complete the semantic artifact and run: "
            f"python -m cyberppt semantic-check {project}"
        )
    if report.get("semantic_understanding_sha256") != _sha256_path(artifact):
        raise ValueError("semantic-understanding gate is stale; rerun semantic-check")
    receipts = collect_source_receipts(project)
    if report.get("source_bundle_sha256") != source_bundle_sha256(receipts):
        raise ValueError("source materials changed after semantic review; rerun semantic-check")
    approval_path = project / SEMANTIC_APPROVAL
    if not approval_path.is_file():
        raise FileNotFoundError(
            "semantic understanding passed automated checks but lacks human approval. Run: "
            f"python -m cyberppt approve-semantic-understanding {project}"
        )
    approval = json.loads(approval_path.read_text(encoding="utf-8-sig"))
    if not isinstance(approval, dict) or approval.get("decision") != "approved":
        raise ValueError("semantic-understanding human approval is invalid")
    approval_expectations = (
        ("semantic_understanding_sha256", report.get("semantic_understanding_sha256")),
        ("source_bundle_sha256", report.get("source_bundle_sha256")),
        ("model_input_sha256", report.get("model_input_sha256")),
        ("generation_receipt_sha256", report.get("generation_receipt_sha256")),
        ("semantic_audit_sha256", _sha256_path(audit_path)),
    )
    if any(
        str(approval.get(field) or "").casefold() != str(expected or "").casefold()
        for field, expected in approval_expectations
    ):
        raise ValueError(
            "semantic-understanding human approval is stale; rerun semantic-check and approval"
        )
    report["human_approval"] = approval
    report["human_approval_path"] = str(approval_path)
    return report


def semantic_binding_issues(
    payload: dict[str, Any], gate: dict[str, Any] | None
) -> list[dict[str, str]]:
    if gate is None:
        return []
    issues: list[dict[str, str]] = []
    expected_semantic = str(gate.get("semantic_understanding_sha256") or "")
    expected_source = str(gate.get("source_bundle_sha256") or "")
    if str(payload.get("semantic_understanding_sha256") or "").lower() != expected_semantic.lower():
        issues.append({
            "code": "SEMANTIC_UNDERSTANDING_NOT_BOUND",
            "message": "Artifact must bind to the current semantic-understanding SHA-256.",
            "retry_strategy": "rebuild_from_semantic_understanding",
        })
    if str(payload.get("semantic_source_bundle_sha256") or "").lower() != expected_source.lower():
        issues.append({
            "code": "SEMANTIC_SOURCE_BUNDLE_NOT_BOUND",
            "message": "Artifact must bind to the source bundle reviewed by the semantic gate.",
            "retry_strategy": "rebuild_from_semantic_understanding",
        })
    return issues
