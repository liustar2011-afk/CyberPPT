from __future__ import annotations

import zipfile
import re
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def _normalize(value: str) -> str:
    # DrawingML normalizes ideographic spaces inside SVG text runs to regular
    # spaces.  Treat that conversion as formatting, not a content mutation.
    return value.replace("\r\n", "\n").replace("\r", "\n").replace("\u3000", " ").strip()


def pptx_texts(path: Path) -> list[str]:
    texts: list[str] = []
    with zipfile.ZipFile(path) as package:
        slide_names = sorted(
            name
            for name in package.namelist()
            if name.startswith("ppt/slides/slide") and name.endswith(".xml")
        )
        for name in slide_names:
            root = ET.fromstring(package.read(name))
            for shape in root.findall(".//p:sp", NS):
                current: list[str] = []
                for node in shape.findall(".//a:t", NS):
                    if node.text:
                        current.append(node.text)
                if current:
                    texts.append(_normalize("".join(current)))
    return texts


def _match_fragmented_texts(expected: list[str], actual: list[str]) -> list[dict]:
    """Match logical script strings against adjacent native visual-line objects."""
    def key(value: str) -> str:
        return re.sub(r"\s+", "", value)

    mismatches: list[dict] = []
    used: set[int] = set()
    for expected_text in expected:
        expected_key = key(expected_text)
        found: tuple[int, ...] | None = None
        for start in range(len(actual)):
            if start in used:
                continue
            joined = ""
            indices: list[int] = []
            for index in range(start, len(actual)):
                if index in used:
                    break
                joined += key(actual[index])
                indices.append(index)
                if joined == expected_key:
                    found = tuple(indices)
                    break
                if len(joined) >= len(expected_key):
                    break
        if found is None:
            mismatches.append(
                {
                    "expected": expected_text,
                    "code": "expected_text_missing_from_fragmented_pptx",
                }
            )
        else:
            used.update(found)
    for index, text in enumerate(actual):
        if index not in used:
            mismatches.append(
                {
                    "actual": text,
                    "code": "unexpected_fragmented_text_in_pptx",
                }
            )
    return mismatches


def build_text_content_qa(
    pptx_path: Path,
    expected_texts: list[str],
    *,
    order_sensitive: bool = True,
    allow_fragmented_actual: bool = False,
) -> dict:
    """Compare the exported PPTX's actual editable text against expected content.

    `order_sensitive=True` (default) preserves the original strict positional
    comparison used by `build_page.py`, where text boxes are created in a
    known, controlled order. `order_sensitive=False` compares as a multiset
    instead: it still catches missing, extra, or wrong text, but does not
    false-flag a page whose text boxes were simply created in a different
    (but individually correct) order -- the case for image-based reconstruction's
    pipeline, which doesn't guarantee shape-creation order matches any single
    canonical text sequence.
    """
    expected = [_normalize(text) for text in expected_texts if _normalize(text)]
    actual = pptx_texts(pptx_path)
    mismatches = []
    if order_sensitive:
        for index in range(max(len(expected), len(actual))):
            expected_text = expected[index] if index < len(expected) else None
            actual_text = actual[index] if index < len(actual) else None
            if expected_text != actual_text:
                mismatches.append(
                    {
                        "index": index,
                        "expected": expected_text,
                        "actual": actual_text,
                        "code": "pptx_text_differs_from_expected",
                    }
                )
    elif allow_fragmented_actual:
        mismatches.extend(_match_fragmented_texts(expected, actual))
    else:
        expected_counts: dict[str, int] = {}
        for text in expected:
            expected_counts[text] = expected_counts.get(text, 0) + 1
        actual_counts: dict[str, int] = {}
        for text in actual:
            actual_counts[text] = actual_counts.get(text, 0) + 1
        for text, count in expected_counts.items():
            if actual_counts.get(text, 0) < count:
                mismatches.append(
                    {
                        "expected": text,
                        "expected_count": count,
                        "actual_count": actual_counts.get(text, 0),
                        "code": "expected_text_missing_from_pptx",
                    }
                )
        for text, count in actual_counts.items():
            if expected_counts.get(text, 0) < count:
                mismatches.append(
                    {
                        "expected": text,
                        "expected_count": expected_counts.get(text, 0),
                        "actual_count": count,
                        "code": "unexpected_text_in_pptx",
                    }
                )
    return {
        "schema": "cyberppt.dual_image.text_content_qa.v1",
        "valid": not mismatches,
        "order_sensitive": order_sensitive,
        "allow_fragmented_actual": allow_fragmented_actual,
        "checks": {
            "text_count_matches": len(expected) == len(actual) or allow_fragmented_actual,
            "pptx_text_matches_expected": not mismatches,
        },
        "expected_texts": expected,
        "actual_texts": actual,
        "mismatches": mismatches,
        "error_count": len(mismatches),
    }
