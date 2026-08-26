#!/usr/bin/env python3
"""Draft 完整文字稿 (and optionally 上屏文字) for one page via the Anthropic API.

This is the automated counterpart to "write it yourself" in
references/18-full-prose-assembly.md: for contexts where no LLM agent is
present in the compilation loop (a scheduled unattended regeneration, a
pure-script CI run), this script makes the same call an agent would make —
read the page's source-truth records, write connected argument prose — by
calling the Anthropic API directly instead.

It is NOT a replacement for the quality gate. Whatever this script produces
still has to pass `scripts/validate_script.py --strict` before it is treated
as done, exactly like agent-written or `assemble_full_prose()`-assembled
prose. This script only does a cheap local pre-check (banned contrast /
defensive-coaching phrasing) before printing output, to fail fast on the
most common defect class without waiting for the full validator.

Requires:
    pip install anthropic
    export ANTHROPIC_API_KEY=...

Usage:
    python3 llm_draft_page.py --outline outline.json --source-truth source-truth.json \\
        --page-id p04
    python3 llm_draft_page.py --outline outline.json --source-truth source-truth.json \\
        --page-id p04 --onscreen --json > p04-draft.json

Input file shape (as produced by this skill's Gate 1 / Gate 3, or by a
project's own workbench/stages/01-analysis/{outline,source-truth}.json):
    outline.json:      {"pages": [{"page_id", "title", "core_message",
                         "chapter_id", "content_units": [{"source_refs": [...]}]}]}
    source-truth.json: {"records": [{"id", "statement", "claim_role",
                         "semantic_argument_role", "semantic_argument_weight"}]}

This script does not know about a project's PAGES-dict conventions or
templates/10-script-final.md's full field set — it only drafts the two
fields that benefit most from real argument-writing (完整文字稿, and
optionally a first-pass 上屏文字 bullet list). Splicing the result into a
project's own generation script or template is a separate, deliberate step.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    yaml = None

CONFIG_DIR = Path(__file__).resolve().parents[1] / "config"

DEFAULT_BANNED_CONTRAST = [
    r"不是.*而是",
    r"不能只.*还要",
    r"不只是.*更是",
]
DEFAULT_BANNED_DEFENSIVE = [
    r"反复区分",
    r"避免.{0,12}(?:误解|听成|当成)",
    r"不要.{0,12}讲成",
    r"不是.{0,8}承诺",
    r"不构成.{0,8}承诺",
    r"防止.{0,12}误解",
    r"以免.{0,12}误解",
]

SYSTEM_PROMPT = """\
你是在为一份中国中央企业/行业协会的正式PPT脚本撰写"完整文字稿"（一页的完整论证文字）。

写作规则（硬性）：
1. 只使用下面给出的source-truth记录中的事实、数字、主体和判断，不得引入记录未覆盖的新事实、新数字或新承诺。
2. 不要机械复述记录自带的"一是/二是/三是"编号，要写成有真实起承转合的连贯段落：背景与事实在前，判断居中，机制与做法其后，建议和边界收尾；用"与此同时""在此基础上""由此""需要说明的是"等真实过渡语衔接，而不是简单罗列。
3. 不使用"不是……而是……""不能只……还要……""不只是……更是……"这类对立转折句式。
4. 不使用防御性边界提示语，例如"反复区分""避免……误解""不要……讲成""不构成……承诺""以免……误解"——这类自我提醒式表达不属于正式陈述句。
5. 语言正式、克制，符合中央企业/行业协会公文语域，避免口语化、避免咨询式口号。
6. 只输出完整文字稿正文本身，不输出任何解释、标题、前后缀或markdown标记。
"""

ONSCREEN_SYSTEM_PROMPT = """\
你是在为同一页PPT撰写"上屏文字"——完整文字稿的可视化简版。

规则：
1. 必须是完整文字稿的缩写，不能是同等长度的改写：每条明细优先控制在20-36个有效汉字左右的短语或短句；37-60个字必须继续压缩或拆分，超过60个字不得通过。
2. 每一分项用"小标题+文字明细"表达：小标题不超过10个汉字，是功能性短语而不是句子。
3. 上屏文字整体要覆盖完整文字稿中的主要判断和关键细节（数字、具体做法、责任主体），不能因为追求简短而丢信息。
4. 如果一个分项内部本身包含两条以上并列信息，要拆成嵌套的"小标题+文字明细"子项，而不是塞进一句话。
5. 主判断、法律边界和必要的完整结论放入对应的独立字段，不要塞进明细；四行选择矩阵、阅读顺序、视觉中心、构图说明、泳道/色块/主链呈现和第X行坐标等后台元数据不得出现在上屏文字。
6. 只输出JSON，不输出任何解释或markdown代码块标记。JSON schema：
   [{"label": "小标题", "detail": "文字明细"}, ...]
   或者当某一项需要嵌套时：
   [{"label": "小标题", "sub_items": [{"label": "子标题", "detail": "子文字明细"}, ...]}, ...]
"""


def load_yaml(path: Path) -> dict:
    if yaml is None or not path.exists():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def banned_patterns() -> tuple[list[str], list[str]]:
    """Load banned-phrase regexes from this skill's own config, falling back
    to the built-in defaults if the config or yaml module is unavailable —
    keeps this script usable standalone without silently drifting from
    config/cec-formal.yaml when it *is* available."""
    profile = load_yaml(CONFIG_DIR / "cec-formal.yaml")
    writing = profile.get("writing", {})
    contrast = writing.get("banned_contrast_frames") or DEFAULT_BANNED_CONTRAST
    defensive = writing.get("banned_defensive_coaching_frames") or DEFAULT_BANNED_DEFENSIVE
    return contrast, defensive


def self_check(text: str) -> list[str]:
    contrast, defensive = banned_patterns()
    hits = []
    for pattern in contrast + defensive:
        if re.search(pattern, text):
            hits.append(pattern)
    return hits


def load_page(outline_path: Path, source_truth_path: Path, page_id: str) -> tuple[dict, list[dict]]:
    outline = json.loads(outline_path.read_text(encoding="utf-8"))
    source_truth = json.loads(source_truth_path.read_text(encoding="utf-8"))
    records = {r["id"]: r for r in source_truth["records"]}

    page = next((p for p in outline["pages"] if p["page_id"] == page_id), None)
    if page is None:
        raise SystemExit(f"page_id not found in outline: {page_id}")

    refs: list[str] = []
    for cu in page.get("content_units", []):
        refs.extend(cu.get("source_refs", []))
    if not refs:
        raise SystemExit(f"page {page_id} has no content_units/source_refs to draft from")

    missing = [r for r in refs if r not in records]
    if missing:
        raise SystemExit(f"source-truth records not found: {missing}")

    return page, [records[r] for r in refs]


def build_full_prose_prompt(page: dict, records: list[dict]) -> str:
    lines = [
        f"页面标题：{page.get('title', '')}",
        f"本页核心判断（主判断）：{page.get('core_message', '')}",
        "",
        "本页可用的source-truth记录（按顺序，只能使用这些记录中的信息）：",
    ]
    for r in records:
        lines.append(
            f"- [{r['id']}] claim_role={r.get('claim_role', '')} "
            f"semantic_argument_role={r.get('semantic_argument_role', '')} "
            f"semantic_argument_weight={r.get('semantic_argument_weight', '')}\n"
            f"  {r.get('statement', '')}"
        )
    lines.append("")
    lines.append("请撰写本页的完整文字稿。")
    return "\n".join(lines)


def build_onscreen_prompt(page: dict, full_prose: str) -> str:
    return (
        f"页面标题：{page.get('title', '')}\n"
        f"本页核心判断：{page.get('core_message', '')}\n\n"
        f"完整文字稿：\n{full_prose}\n\n"
        "请基于上面的完整文字稿撰写上屏文字。"
    )


def call_claude(system: str, user: str, model: str, max_tokens: int) -> str:
    try:
        import anthropic
    except ImportError as exc:
        raise SystemExit(
            "the 'anthropic' package is not installed — run: pip install anthropic"
        ) from exc

    import os
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit(
            "ANTHROPIC_API_KEY is not set. Export it before running this script — "
            "this call will incur API cost on your own account, so it is deliberately "
            "not silently skipped or defaulted."
        )

    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    try:
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.APIError as exc:
        raise SystemExit(f"Anthropic API call failed: {exc}") from exc
    return "".join(
        block.text for block in response.content if getattr(block, "type", "") == "text"
    ).strip()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--outline", type=Path, required=True)
    parser.add_argument("--source-truth", type=Path, required=True)
    parser.add_argument("--page-id", required=True)
    parser.add_argument("--model", default="claude-sonnet-4-5")
    parser.add_argument("--max-tokens", type=int, default=1500)
    parser.add_argument("--onscreen", action="store_true", help="also draft a first-pass 上屏文字 bullet list")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON instead of plain text")
    args = parser.parse_args()

    page, records = load_page(args.outline, args.source_truth, args.page_id)

    full_prose_prompt = build_full_prose_prompt(page, records)
    full_prose = call_claude(SYSTEM_PROMPT, full_prose_prompt, args.model, args.max_tokens)

    issues = self_check(full_prose)
    if issues:
        print(f"WARNING: drafted 完整文字稿 matched banned pattern(s): {issues}", file=sys.stderr)
        print("Rewrite the affected sentence(s) before using this draft; do not silently ship it.", file=sys.stderr)

    result = {"page_id": args.page_id, "full_prose": full_prose}

    if args.onscreen:
        onscreen_prompt = build_onscreen_prompt(page, full_prose)
        onscreen_raw = call_claude(ONSCREEN_SYSTEM_PROMPT, onscreen_prompt, args.model, args.max_tokens)
        try:
            onscreen = json.loads(onscreen_raw)
        except json.JSONDecodeError:
            print("WARNING: 上屏文字 draft was not valid JSON, returning raw text under 'onscreen_raw'", file=sys.stderr)
            onscreen = None
            result["onscreen_raw"] = onscreen_raw
        if onscreen is not None:
            result["onscreen"] = onscreen

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(result["full_prose"])
        if args.onscreen and "onscreen" in result:
            print("\n--- 上屏文字draft ---")
            print(json.dumps(result["onscreen"], ensure_ascii=False, indent=2))

    print(
        "\nReminder: run scripts/validate_script.py --strict on the assembled script "
        "before treating this draft as final.",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
