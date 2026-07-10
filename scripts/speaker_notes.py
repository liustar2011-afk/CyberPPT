#!/usr/bin/env python3
"""Build speaker-note drafts from the business script before PPT assembly."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Sequence

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.dual_image_overlay.deliverable_prompt import parse_pages
from scripts.dual_image_overlay.rebuild_engine.codex_oauth_image import run_codex_vision_text


PAGE_HEADING_RE = re.compile(r"^##\s*第\s*(?P<num>\d+)\s*页(?:[:：]|\s+)(?P<title>.+?)\s*$", re.M)
SECTION_HEADING_RE = re.compile(r"^#{1,6}\s*(?P<title>.+?)\s*$")
BULLET_RE = re.compile(r"^\s*[-*]\s+")
NOTE_PROVENANCE_RE = re.compile(
    r"(证据链|来源位置|源材料|完整性校核|业务稿证据|重点对应|对应E\d+|\bE\d+\b|P\d+|T\d+)"
)
NOTE_FILLER_RE = re.compile(r"(围绕本章内容|本章内容开展汇报|作简要汇报|先对本章涉及)")


@dataclass(frozen=True)
class NotePage:
    page_number: int
    title: str
    text: str


def parse_note_pages(path: Path) -> dict[int, NotePage]:
    text = path.read_text(encoding="utf-8")
    matches = list(PAGE_HEADING_RE.finditer(text))
    pages: dict[int, NotePage] = {}
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        block = text[start:end].strip()
        page_number = int(match.group("num"))
        title = match.group("title").strip()
        pages[page_number] = NotePage(page_number=page_number, title=title, text=block)
    return pages


def clean_line(line: str) -> str:
    line = BULLET_RE.sub("", line.strip())
    line = re.sub(r"^\d+[.、]\s*", "", line)
    line = line.replace("**", "")
    return line.strip()


def section_lines(page: NotePage, *section_names: str) -> list[str]:
    wanted = tuple(name.strip() for name in section_names)
    lines = page.text.splitlines()
    current = ""
    found: list[str] = []
    for raw in lines:
        stripped = raw.strip()
        heading = SECTION_HEADING_RE.match(stripped)
        if heading:
            current = heading.group("title").strip(" ：:")
            continue
        if not stripped or not current:
            continue
        if any(name in current for name in wanted):
            if stripped.startswith("**") and stripped.endswith("**"):
                continue
            value = clean_line(stripped)
            if value and not value.startswith("【") and not value.startswith("|"):
                found.append(value)
    return found


def visible_business_lines(page: NotePage) -> list[str]:
    excluded_markers = ("证据链", "来源位置", "完整性校核", "绘制", "草图", "页面表达框架", "组件")
    values: list[str] = []
    for raw in page.text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("##"):
            continue
        if stripped.startswith("**") and stripped.endswith("**"):
            continue
        if stripped.startswith("#"):
            continue
        if any(marker in stripped for marker in excluded_markers):
            continue
        if stripped.startswith("|") or stripped.startswith("```"):
            continue
        value = clean_line(stripped)
        if value and not value.startswith("【") and value not in values:
            values.append(value)
    return values


def evidence_labels(page: NotePage, limit: int = 4) -> list[str]:
    labels: list[str] = []
    for line in section_lines(page, "证据链", "来源位置"):
        for label in re.findall(r"\bE\d+\b", line):
            if label not in labels:
                labels.append(label)
        if len(labels) >= limit:
            break
    return labels[:limit]


def integrity_notes(page: NotePage, limit: int = 2) -> list[str]:
    notes: list[str] = []
    for line in section_lines(page, "完整性校核"):
        clean = clean_line(line)
        if re.match(r"^E\d+\b", clean):
            continue
        clean = re.sub(r"^校核[:：]\s*", "", clean)
        clean = clean.replace("均不得删除", "").strip("。；; ")
        if clean and clean not in notes:
            notes.append(clean)
        if len(notes) >= limit:
            break
    return notes


def speech_points(items: list[str], limit: int = 4) -> str:
    selected = compress_items(items, limit)
    if not selected:
        return ""
    labels = ("一是", "二是", "三是", "四是")
    parts = [f"{labels[index]}{item.rstrip('。；;')}" for index, item in enumerate(selected)]
    return "；".join(parts) + "。"


def first_nonempty(*groups: Iterable[str]) -> list[str]:
    for group in groups:
        values = [item for item in group if item]
        if values:
            return values
    return []


def compress_items(items: list[str], limit: int = 7) -> list[str]:
    result: list[str] = []
    for item in items:
        if item not in result:
            result.append(item)
        if len(result) >= limit:
            break
    return result


def join_items(items: list[str]) -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return "、".join(items[:-1]) + "和" + items[-1]


def sanitize_speech_note(text: str) -> str:
    sentences = re.split(r"(?<=[。！？])", text)
    kept: list[str] = []
    for sentence in sentences:
        stripped = sentence.strip()
        if not stripped:
            continue
        if NOTE_PROVENANCE_RE.search(stripped) or NOTE_FILLER_RE.search(stripped):
            continue
        kept.append(stripped)
    return "".join(kept).strip()


def page_role(page: NotePage) -> str:
    title = page.title
    if page.page_number == 1 or "封面" in title:
        return "cover"
    if "目录" in title:
        return "agenda"
    if re.search(r"第[一二三四五六七八九十]+章", title):
        return "section"
    if any(keyword in title for keyword in ("封底", "结束", "感谢")):
        return "ending"
    return "body"


def note_heading(page: NotePage) -> str:
    lines = visible_business_lines(page)
    if page_role(page) == "cover" and lines:
        return lines[0]
    if page_role(page) == "section":
        return re.sub(r"^第[一二三四五六七八九十]+章\s*", "", page.title).strip() or page.title
    if page_role(page) == "ending" and lines:
        return lines[0]
    return page.title


def build_rule_note(page: NotePage, *, seconds: int) -> str:
    role = page_role(page)
    heading = note_heading(page)
    if role == "cover":
        lines = visible_business_lines(page)
        unit = lines[1] if len(lines) >= 2 else ""
        date = lines[2] if len(lines) >= 3 else ""
        tail = f"汇报单位为{unit}，时间为{date}。" if unit or date else ""
        return f"各位领导，下面汇报《{heading}》。{tail}".strip()
    if role == "agenda":
        items = compress_items(visible_business_lines(page), 6)
        return f"本次汇报主要包括{join_items(items)}几个方面，重点说明工作基础、建设考虑、实施安排以及需请领导审定事项。"
    if role == "section":
        return ""
    if role == "ending":
        return "以上汇报，请各位领导审阅。"

    explicit = first_nonempty(
        section_lines(page, "页面内容脚本", "讲稿", "表达脚本"),
        section_lines(page, "上屏文字", "内容锁定"),
        visible_business_lines(page),
    )
    points = compress_items(explicit, 8)
    paragraphs: list[str] = [f"这一页汇报{heading}。"]
    if points:
        paragraphs.append(f"主要说明{speech_points(points)}")
    note = "".join(paragraphs)
    if seconds > 90:
        note += "如需展开，可结合页面中的数据、机制和成果产品逐项说明。"
    return sanitize_speech_note(note)


def build_llm_prompt(pages: list[NotePage], draft_notes: dict[int, str], *, seconds: int) -> str:
    payload = []
    for page in pages:
        payload.append(
            {
                "page_number": page.page_number,
                "title": page.title,
                "role": page_role(page),
                "business_source": page.text,
                "rule_draft": draft_notes.get(page.page_number, ""),
            }
        )
    return (
        "你是央企/行业协会内部汇报材料的讲稿编辑。请把逐页备注优化成自然、克制、下级向领导汇报的口吻。\n"
        "必须遵守：不新增事实；不改数字；不把边界事项写成既定事实；不使用咨询腔金句；"
        "不得把证据链、来源位置、完整性校核、E编号、P页码、T表号或“业务稿证据支撑”等审稿说明写进演讲备注；"
        "封面、目录、章节过渡、封底只写简短串场；"
        f"内容页按约 {seconds} 秒可讲完控制篇幅。\n"
        "请只返回 JSON，结构为：{\"notes\":[{\"page_number\":1,\"title\":\"...\",\"notes_text\":\"...\"}]}。\n\n"
        "输入如下：\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n"
    )


def parse_llm_notes(text: str) -> dict[int, str]:
    stripped = text.strip()
    fenced = re.search(r"```(?:json)?\s*(?P<body>.*?)```", stripped, re.S)
    if fenced:
        stripped = fenced.group("body").strip()
    data = json.loads(stripped)
    notes = data.get("notes") if isinstance(data, dict) else None
    if not isinstance(notes, list):
        raise ValueError("LLM output must contain notes[]")
    result: dict[int, str] = {}
    for item in notes:
        if not isinstance(item, dict):
            continue
        page_number = int(item["page_number"])
        notes_text = str(item.get("notes_text") or "").strip()
        if notes_text:
            result[page_number] = notes_text
    return result


def build_manifest(
    *,
    business_script: Path,
    pages_raw: str,
    output_dir: Path,
    seconds: int = 75,
    llm_output: Path | None = None,
    use_llm: bool = False,
    model: str | None = None,
    timeout: int = 300,
    dry_run_llm: bool = False,
) -> dict[str, Any]:
    pages_by_number = parse_note_pages(business_script)
    if not pages_by_number:
        raise ValueError(f"no page blocks found in business script: {business_script}")
    page_numbers = parse_pages(pages_raw, set(pages_by_number))
    pages = [pages_by_number[number] for number in page_numbers]
    rule_notes = {page.page_number: build_rule_note(page, seconds=seconds) for page in pages}
    llm_notes = parse_llm_notes(llm_output.read_text(encoding="utf-8")) if llm_output else {}
    prompt = build_llm_prompt(pages, rule_notes, seconds=seconds)
    output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = output_dir / "speaker_notes_llm_prompt.md"
    prompt_path.write_text(prompt, encoding="utf-8")
    generated_llm_output = llm_output
    if use_llm:
        llm_text = run_codex_vision_text(
            prompt=prompt,
            image_paths=[],
            model=model,
            timeout=timeout,
            dry_run=dry_run_llm,
        )
        generated_llm_output = output_dir / "speaker_notes_llm_output.json"
        generated_llm_output.write_text(llm_text.strip() + "\n", encoding="utf-8")
        if dry_run_llm:
            generated_llm_output = None
    if generated_llm_output and generated_llm_output.is_file():
        llm_notes = parse_llm_notes(generated_llm_output.read_text(encoding="utf-8"))
    note_records = []
    for page in pages:
        source = "llm_optimized" if page.page_number in llm_notes else "business_rule_draft"
        note_records.append(
            {
                "page_number": page.page_number,
                "title": note_heading(page),
                "page_role": page_role(page),
                "notes_text": sanitize_speech_note(llm_notes.get(page.page_number, rule_notes[page.page_number])),
                "source": source,
                "business_source_excerpt": page.text[:2000],
            }
        )
    return {
        "schema": "cyberppt.speaker_notes_manifest.v1",
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "business_script": str(business_script),
        "pages": page_numbers,
        "seconds_per_content_page": seconds,
        "llm_prompt": str(prompt_path),
        "llm_output": str(generated_llm_output) if generated_llm_output else None,
        "policy": {
            "notes_source": "business_script_first",
            "drawing_script_is_not_primary_notes_source": True,
            "llm_optimization_allowed": True,
            "llm_must_not_add_facts": True,
        },
        "notes": note_records,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build business-script speaker notes for CyberPPT PPTX notes.")
    parser.add_argument("--business-script", required=True, type=Path)
    parser.add_argument("--pages", default="all")
    parser.add_argument("-o", "--output-dir", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--seconds", type=int, default=75)
    parser.add_argument("--llm-output", type=Path, help="Optional reviewed JSON output from the LLM optimization prompt.")
    parser.add_argument("--use-llm", action="store_true", help="Call Codex Responses to optimize notes into speech-like prose.")
    parser.add_argument("--model", help="Optional text model for --use-llm.")
    parser.add_argument("--timeout", type=int, default=300)
    parser.add_argument("--dry-run-llm", action="store_true", help="Write the LLM request preview instead of calling the model.")
    args = parser.parse_args(argv)

    manifest = build_manifest(
        business_script=args.business_script.resolve(),
        pages_raw=args.pages,
        output_dir=args.output_dir.resolve(),
        seconds=args.seconds,
        llm_output=args.llm_output.resolve() if args.llm_output else None,
        use_llm=args.use_llm,
        model=args.model,
        timeout=args.timeout,
        dry_run_llm=args.dry_run_llm,
    )
    manifest_path = args.manifest.resolve() if args.manifest else args.output_dir.resolve() / "speaker_notes_manifest.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(manifest_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
