from __future__ import annotations

import argparse
import html
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any


TEXT_RE = re.compile(r"<text(?P<attrs>[^>]*)>(?P<body>.*?)</text>", re.S)
ATTR_RE = re.compile(r"(?P<name>[\w:-]+)=(?P<quote>[\"'])(?P<value>.*?)(?P=quote)")


def compact_text(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _attrs_to_dict(raw: str) -> dict[str, str]:
    return {match.group("name"): match.group("value") for match in ATTR_RE.finditer(raw)}


def _number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load_ocr_boxes(project_dir: Path) -> list[dict[str, Any]]:
    boxes: list[dict[str, Any]] = []
    for mapping_path in sorted((project_dir / "analysis" / "ocr").glob("page_*_text_mapping.json")):
        data = json.loads(mapping_path.read_text(encoding="utf-8"))
        page_number = data.get("page_number") or _page_number_from_name(mapping_path.name)
        for box in data.get("boxes", []):
            item = dict(box)
            item["page_number"] = page_number
            item["source_file"] = str(mapping_path)
            boxes.append(item)
    return boxes


def load_svg_texts(project_dir: Path) -> list[dict[str, Any]]:
    texts: list[dict[str, Any]] = []
    svg_dir = project_dir / "svg_output"
    for svg_path in sorted(svg_dir.glob("*.svg")):
        page_number = _page_number_from_name(svg_path.name)
        svg = svg_path.read_text(encoding="utf-8")
        for match in TEXT_RE.finditer(svg):
            attrs = _attrs_to_dict(match.group("attrs"))
            body = html.unescape(re.sub(r"<.*?>", "", match.group("body")).strip())
            if not body:
                continue
            texts.append(
                {
                    "page_number": page_number,
                    "source_file": str(svg_path),
                    "text": body,
                    "compact_text": compact_text(body),
                    "x": _number(attrs.get("x")),
                    "y": _number(attrs.get("y")),
                    "text_anchor": attrs.get("text-anchor", "start"),
                    "font_size": _number(attrs.get("font-size")),
                }
            )
    return texts


def _page_number_from_name(name: str) -> int | None:
    match = re.search(r"page_(\d+)", name)
    return int(match.group(1)) if match else None


def mine_phrase_breaks(boxes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    observed: dict[str, Counter[str]] = defaultdict(Counter)
    for box in boxes:
        text = str(box.get("text", ""))
        if "\n" not in text:
            continue
        compact = compact_text(text)
        if compact:
            observed[compact][text] += 1
    candidates: list[dict[str, Any]] = []
    for compact, variants in sorted(observed.items()):
        value, count = variants.most_common(1)[0]
        candidates.append({"compact_text": compact, "break_text": value, "support": count})
    return candidates


def _cluster_by_y(boxes: list[dict[str, Any]], tolerance: float = 12.0) -> list[list[dict[str, Any]]]:
    clusters: list[list[dict[str, Any]]] = []
    for box in sorted(boxes, key=lambda item: _number(item.get("y")) + _number(item.get("h")) / 2):
        center_y = _number(box.get("y")) + _number(box.get("h")) / 2
        if not clusters:
            clusters.append([box])
            continue
        last = clusters[-1]
        last_center = median(_number(item.get("y")) + _number(item.get("h")) / 2 for item in last)
        if abs(center_y - last_center) <= tolerance:
            last.append(box)
        else:
            clusters.append([box])
    return clusters


def _cluster_by_x(boxes: list[dict[str, Any]], tolerance: float = 48.0) -> list[list[dict[str, Any]]]:
    clusters: list[list[dict[str, Any]]] = []
    for box in sorted(boxes, key=lambda item: _number(item.get("x"))):
        center_x = _number(box.get("x"))
        for cluster in clusters:
            cluster_x = median(_number(item.get("x")) for item in cluster)
            if abs(center_x - cluster_x) <= tolerance:
                cluster.append(box)
                break
        else:
            clusters.append([box])
    return [sorted(cluster, key=lambda item: _number(item.get("y")) + _number(item.get("h")) / 2) for cluster in clusters]


def _mine_repeated_column_body_groups(page_number: int | None, page_boxes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    body_boxes = [
        box
        for box in page_boxes
        if str(box.get("align", "")).lower() == "left"
        and _number(box.get("w")) >= 40
        and _number(box.get("h")) >= 10
        and len(compact_text(str(box.get("text", "")))) >= 8
    ]
    candidates: list[dict[str, Any]] = []
    for row in _cluster_by_y(body_boxes, tolerance=48.0):
        column_count = len(_cluster_by_x(row))
        if len(row) < 3 or column_count < 3:
            continue
        centers = [_number(item.get("y")) + _number(item.get("h")) / 2 for item in row]
        labels = [str(item.get("text", "")) for item in sorted(row, key=lambda item: _number(item.get("x")))]
        candidates.append(
            {
                "page_number": page_number,
                "candidate_y": round(float(median(centers)), 2),
                "y_min": round(min(centers), 2),
                "y_max": round(max(centers), 2),
                "labels": labels,
                "support": len(row),
                "source": "repeated_column_body_rows",
            }
        )
    return candidates


def mine_baseline_groups(boxes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    boxes_by_page: dict[int | None, list[dict[str, Any]]] = defaultdict(list)
    for box in boxes:
        boxes_by_page[box.get("page_number")].append(box)

    for page_number, page_boxes in sorted(boxes_by_page.items(), key=lambda item: item[0] or 0):
        row_like_boxes = [
            box
            for box in page_boxes
            if str(box.get("align", "")).lower() == "center"
            and _number(box.get("w")) >= 25
            and _number(box.get("h")) >= 10
        ]
        for cluster in _cluster_by_y(row_like_boxes):
            if len(cluster) < 3:
                continue
            centers = [_number(item.get("y")) + _number(item.get("h")) / 2 for item in cluster]
            labels = [compact_text(str(item.get("text", ""))) for item in sorted(cluster, key=lambda item: _number(item.get("x")))]
            candidates.append(
                {
                    "page_number": page_number,
                    "candidate_y": round(float(median(centers)), 2),
                    "y_min": round(min(centers), 2),
                    "y_max": round(max(centers), 2),
                    "labels": labels,
                    "support": len(cluster),
                }
            )
        candidates.extend(_mine_repeated_column_body_groups(page_number, page_boxes))
    return candidates


def mine_alignment_issues(boxes: list[dict[str, Any]], svg_texts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    svg_by_page_text = {(item["page_number"], item["compact_text"]): item for item in svg_texts}
    issues: list[dict[str, Any]] = []
    for box in boxes:
        text = str(box.get("text", ""))
        compact = compact_text(text)
        align = str(box.get("align", "")).lower()
        if align != "left" or "\n" not in text:
            continue
        suggested_x = _number(box.get("x")) + _number(box.get("w")) / 2
        issue: dict[str, Any] = {
            "page_number": box.get("page_number"),
            "text": text,
            "observed_align": align,
            "suggested_text_anchor": "middle",
            "suggested_x": round(suggested_x, 2),
            "reason": "multiline label appears left-aligned inside a visual container",
        }
        svg_match = svg_by_page_text.get((box.get("page_number"), compact))
        if svg_match:
            issue["current_svg_x"] = round(float(svg_match["x"]), 2)
            issue["current_svg_anchor"] = svg_match["text_anchor"]
        issues.append(issue)
    return issues


def mine_layout_rules(project_dir: Path) -> dict[str, Any]:
    boxes = load_ocr_boxes(project_dir)
    svg_texts = load_svg_texts(project_dir)
    return {
        "schema": "cyberppt.dual_image.candidate_layout_rules.v1",
        "project": str(project_dir),
        "inputs": {
            "ocr_boxes": len(boxes),
            "svg_texts": len(svg_texts),
        },
        "line_break": {
            "phrase_breaks": mine_phrase_breaks(boxes),
        },
        "baseline_groups": mine_baseline_groups(boxes),
        "alignment_issues": mine_alignment_issues(boxes, svg_texts),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Mine reusable dual-image overlay layout-rule candidates.")
    parser.add_argument("project_dir", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    report = mine_layout_rules(args.project_dir)
    output = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
