from __future__ import annotations

import re
from collections.abc import Iterable

from .models import SourceInventory, SourceItem, SourceTruthMap

_VALID_CATEGORIES = {"F", "P", "J", "I", "R", "B", "U"}
_VALID_IMPORTANCE = {"P0", "P1", "P2"}
_NUMBER_RE = re.compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*(?![A-Za-z0-9])")
_SOURCE_LABEL_RE = re.compile(r"\[来源文件：([^\]]+)\]")
_STATE_TERMS = (
    "已完成",
    "正在",
    "已启动",
    "拟开展",
    "拟",
    "计划",
    "推动",
    "探索",
    "条件成熟后",
    "待核实",
)
_BOUNDARY_TERMS = (
    "不得",
    "仅限",
    "仅",
    "前提",
    "条件",
    "范围",
    "授权",
    "合规",
    "安全",
    "受控域",
    "不外流",
)


def _unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            result.append(value)
    return result


def build_source_inventory(text: str, file_names: Iterable[str] = ()) -> SourceInventory:
    names = _unique([*file_names, *_SOURCE_LABEL_RE.findall(text)])
    paragraphs = [line.strip() for line in text.replace("\r\n", "\n").splitlines() if line.strip()]
    cleaned = _SOURCE_LABEL_RE.sub("", text)
    candidates: list[str] = []
    for paragraph in [part.strip() for part in re.split(r"\n+", cleaned) if part.strip()]:
        pieces = [part.strip() for part in re.split(r"(?<=[。！？；;])", paragraph) if part.strip()]
        candidates.extend(pieces or [paragraph])
    numbers = _unique(match.group(0).replace(",", "") for match in _NUMBER_RE.finditer(text))
    return SourceInventory(
        file_names=names,
        file_count=len(names),
        char_count=len(re.sub(r"\s+", "", text)),
        paragraph_count=len(paragraphs),
        candidate_item_count=len(candidates),
        numbers=numbers,
        state_terms={term: text.count(term) for term in _STATE_TERMS if text.count(term)},
        boundary_terms={term: text.count(term) for term in _BOUNDARY_TERMS if text.count(term)},
    )


def _split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def parse_source_truth_map(text: str) -> SourceTruthMap:
    rows = [line for line in text.replace("\r\n", "\n").splitlines() if line.strip().startswith("|")]
    header_index = next(
        (index for index, line in enumerate(rows) if "Source ID" in line and "重要性" in line),
        None,
    )
    if header_index is None:
        return SourceTruthMap(issues=["未找到Source Truth Map表格"])
    headers = _split_table_row(rows[header_index])
    items: list[SourceItem] = []
    issues: list[str] = []
    seen: set[str] = set()
    for line in rows[header_index + 1 :]:
        cells = _split_table_row(line)
        if cells and all(re.fullmatch(r":?-+:?", cell) for cell in cells):
            continue
        if len(cells) < len(headers):
            cells.extend([""] * (len(headers) - len(cells)))
        data = dict(zip(headers, cells))
        source_id = (data.get("Source ID") or data.get("ID") or "").upper()
        if not re.fullmatch(r"S\d{3,4}", source_id):
            issues.append(f"无效Source ID：{source_id or '<空>'}")
            continue
        if source_id in seen:
            issues.append(f"Source ID重复：{source_id}")
        seen.add(source_id)
        category = (data.get("类型") or "").upper()
        importance = (data.get("重要性") or "").upper()
        if category not in _VALID_CATEGORIES:
            issues.append(f"{source_id}无效类型：{category or '<空>'}")
        if importance not in _VALID_IMPORTANCE:
            issues.append(f"{source_id}无效重要性：{importance or '<空>'}")
        items.append(
            SourceItem(
                source_id=source_id,
                category=category,
                importance=importance,
                state=data.get("状态", ""),
                subject=data.get("主体", ""),
                content=data.get("内容", ""),
                numbers_time=data.get("数字/时间", ""),
                boundary=data.get("条件/边界", ""),
                source_location=data.get("原文出处", ""),
                conflict=data.get("冲突/待核", ""),
            )
        )
    return SourceTruthMap(items=items, issues=issues)
