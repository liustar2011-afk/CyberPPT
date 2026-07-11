"""Advisory second-pass model critique for Stage 1 candidates."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.dual_image_overlay.rebuild_engine.codex_oauth_image import run_codex_text

from cyberppt.commands.analysis_expression_gate import GATE_ORDER
from cyberppt.phase1.artifacts import append_phase1_ledger_records, phase1_paths, sha256_file
from cyberppt.phase1.schemas import _json_payload
from cyberppt.phase1.workflow import (
    MODEL_INSTRUCTIONS,
    _approved_artifact,
    _assert_dependencies_current,
    _run_payload,
    _update_run,
)


CRITIC_CATEGORIES = {
    "unsupported_claim",
    "weak_evidence",
    "duplicate_page",
    "narrative_gap",
    "vague_title",
    "style_violation",
    "density_mismatch",
    "boundary_overstatement",
}


def build_critic_prompt(
    gate: str,
    candidate: str,
    grounding_report: dict[str, object],
    approved: dict[str, str],
) -> str:
    upstream = "\n\n".join(f"【已批准：{name}】\n{text}" for name, text in approved.items())
    return f"""# CyberPPT Stage 1 critic prompt

【任务】独立检查 {gate} 候选稿，不要重写候选稿。
【输出】只返回 JSON 对象：{{"findings": [{{"category": "...", "page": 1, "evidence_ids": ["E01"], "issue": "...", "remediation": "...", "severity": "low|medium|high"}}]}}。
【允许分类】unsupported_claim、weak_evidence、duplicate_page、narrative_gap、vague_title、style_violation、density_mismatch、boundary_overstatement。
【检查重点】证据充分性、数字和边界、跨页重复、逻辑承接、内部汇报文风、标题具体性和信息密度。
【事实边界】不得使用候选稿、证据表和已批准工件以外的事实。

【确定性 grounding 报告】
{json.dumps(grounding_report, ensure_ascii=False, indent=2)}

【已批准上游工件】
{upstream}

【候选稿】
{candidate}
"""


def parse_critic_output(text: str) -> dict[str, object]:
    payload = _json_payload(text)
    if set(payload) - {"findings", "schema"}:
        raise ValueError("critic output contains unknown fields")
    findings = payload.get("findings")
    if not isinstance(findings, list):
        raise ValueError("critic findings must be an array")
    normalized: list[dict[str, object]] = []
    required = {"category", "page", "evidence_ids", "issue", "remediation"}
    for finding in findings:
        if not isinstance(finding, dict):
            raise ValueError("each critic finding must be an object")
        missing = sorted(required - set(finding))
        if missing:
            raise ValueError("critic finding is missing: " + ", ".join(missing))
        category = str(finding["category"])
        if category not in CRITIC_CATEGORIES:
            raise ValueError(f"unknown critic category: {category}")
        if not isinstance(finding["evidence_ids"], list):
            raise ValueError("critic finding evidence_ids must be an array")
        normalized.append(
            {
                "category": category,
                "page": finding["page"],
                "evidence_ids": [str(item) for item in finding["evidence_ids"]],
                "issue": str(finding["issue"]),
                "remediation": str(finding["remediation"]),
                "severity": str(finding.get("severity", "medium")),
            }
        )
    return {"schema": "cyberppt.phase1_critic.v1", "findings": normalized}


def critique_phase1_candidate(project: Path, gate: str, model: str | None = None) -> dict[str, object]:
    root = project.expanduser().resolve()
    paths = phase1_paths(root, gate)
    if not paths.run_manifest.is_file() or not paths.candidate.is_file():
        raise ValueError(f"{gate} candidate is not available")
    run = _run_payload(paths)
    _assert_dependencies_current(run)
    grounding_report = json.loads(paths.grounding_report.read_text(encoding="utf-8"))
    candidate = paths.candidate.read_text(encoding="utf-8")
    approved: dict[str, str] = {}
    for predecessor in GATE_ORDER[: GATE_ORDER.index(gate)]:
        _, text = _approved_artifact(root, predecessor)
        approved[predecessor] = text
    prompt = build_critic_prompt(gate, candidate, grounding_report, approved)
    paths.critic_prompt.write_text(prompt, encoding="utf-8")
    try:
        raw = run_codex_text(
            prompt=prompt,
            instructions=MODEL_INSTRUCTIONS + " Return only critic JSON and never rewrite the candidate.",
            model=model,
        )
        paths.critic_raw.write_text(raw.strip() + "\n", encoding="utf-8")
        report = parse_critic_output(raw)
        report.update(
            {
                "status": "critic_ready",
                "gate": gate,
                "candidate": str(paths.candidate),
                "candidate_sha256": sha256_file(paths.candidate),
                "model": model,
            }
        )
        paths.critic_report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        _update_run(
            run,
            critic_status="critic_ready",
            critic_model=model,
            critic_prompt_path=str(paths.critic_prompt),
            critic_raw_path=str(paths.critic_raw),
            critic_report_path=str(paths.critic_report),
        )
        append_phase1_ledger_records(
            root,
            [
                {
                    "stage": "01-analysis",
                    "page": None,
                    "path": str(paths.critic_report),
                    "status": "critic_ready",
                    "depends_on": [str(paths.candidate), str(paths.critic_prompt)],
                    "supersedes": [],
                    "resume_command": f"python3 -m cyberppt phase1 stage {root} --gate {gate}",
                    "sha256": sha256_file(paths.critic_report),
                    "generator": {"model": model, "prompt": str(paths.critic_prompt)},
                }
            ],
        )
        return report
    except Exception as exc:
        _update_run(run, critic_status="critic_model_failed", critic_error=str(exc), critic_prompt_path=str(paths.critic_prompt))
        raise
