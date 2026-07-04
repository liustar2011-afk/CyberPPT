from __future__ import annotations

import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
}


def _normalize(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()


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


def build_text_content_qa(pptx_path: Path, expected_texts: list[str]) -> dict:
    expected = [_normalize(text) for text in expected_texts if _normalize(text)]
    actual = pptx_texts(pptx_path)
    mismatches = []
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
    return {
        "schema": "cyberppt.dual_image.text_content_qa.v1",
        "valid": not mismatches,
        "checks": {
            "text_count_matches": len(expected) == len(actual),
            "pptx_text_matches_expected": not mismatches,
        },
        "expected_texts": expected,
        "actual_texts": actual,
        "mismatches": mismatches,
        "error_count": len(mismatches),
    }
