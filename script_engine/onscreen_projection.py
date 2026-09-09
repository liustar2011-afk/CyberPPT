"""Local projection diagnostics and transient evidence for the author Critic.

Text similarity locates candidate passages only. These checks recognize a small
set of explicit constructions; they do not certify semantic equivalence or decide
which general propositions may be omitted. That decision belongs to the Critic.
"""
from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Any


_NUMBER = re.compile(r"\d+(?:\.\d+)?(?:%|％|亿元|万元|年|月|日|项|类|个|家|万|亿)?")
_ACHIEVED = re.compile(r"已(?:全面|正式|基本|初步)?(?:完成|形成|实现|建立|建成|上线|开放|投入|发布|通过|交付|投产)")
_PENDING = re.compile(r"计划|拟|探索|尚未|将(?:持续)?|待确认")
_PROHIBITION = re.compile(r"不得|严禁|禁止|不允许")
_RESPONSIBILITY = re.compile(r"([^，,。；;\n]+?)负责([^，,。；;\n]+)")
_TRANSFORM = re.compile(r"把([^，,。；;\n]+?)(?:加工成|转化为|转换为|转化成)([^，,。；;\n]+)")
_CONDITION = re.compile(r"^在(.+?(?:后|前|时|条件下|前提下))[，,](.+)$")
_EXAMPLE = re.compile(r"^(?:例如|比如|举例)")


def _compact(value: str) -> str:
    return "".join(re.findall(r"[一-鿿A-Za-z0-9]", value)).lower()


def _anchor(value: str) -> str:
    return _compact(_PENDING.sub("", _ACHIEVED.sub("", _NUMBER.sub("", value))))


def _contains_object(surface: str, value: str) -> bool:
    # Removing the attributive particle is ordinary phrase compression.
    return _compact(value.replace("的", "")) in _compact(surface.replace("的", ""))


def _passages(full_copy: str) -> list[dict[str, str]]:
    # Preserve comma-level conditions and their predicates in the same passage.
    return [
        {"id": f"passage-{index + 1}", "text": text.strip()}
        for index, text in enumerate(re.split(r"[。；;\n]+", full_copy))
        if text.strip()
    ]


def _modules(slide: dict[str, Any]) -> list[dict[str, Any]]:
    modules = []
    for index, module in enumerate(slide.get("onscreen") or []):
        if not isinstance(module, dict):
            continue
        heading = str(module.get("heading") or "")
        body = str(module.get("text") or "")
        entries = [("heading", heading), ("text", body)]
        entries.extend((f"items[{i}]", item) for i, item in enumerate(module.get("items") or []) if isinstance(item, str))
        modules.append({
            "field": f"onscreen[{index}]",
            "text": "\n".join(value for _, value in entries if value.strip()),
            "entries": [
                {"field": f"onscreen[{index}].{key}", "text": value,
                 "context": value if key == "heading" else heading + "\n" + value}
                for key, value in entries if value.strip()
            ],
        })
    return modules


def _parent(context: str, passages: list[dict[str, str]]) -> dict[str, str] | None:
    anchor = _anchor(context)
    if not anchor:
        return None
    ranked = sorted(
        ((SequenceMatcher(None, anchor, _anchor(p["text"])).ratio(), i, p)
         for i, p in enumerate(passages)), reverse=True,
    )
    best = ranked[0] if ranked else None
    if not best or best[0] < 0.55:
        return None
    # Equal duplicate source wording is harmless; distinct ambiguous matches
    # stay with the qualitative reviewer instead of inventing a parent.
    rivals = [row for row in ranked[1:] if _anchor(row[2]["text"]) != _anchor(best[2]["text"])]
    if rivals and best[0] - rivals[0][0] < 0.08:
        return None
    return best[2]


def review_onscreen_projection(slide: dict[str, Any]) -> dict[str, Any]:
    passages = _passages(str(slide.get("full_copy") or ""))
    modules = _modules(slide)
    findings: list[dict[str, str]] = []
    mappings: list[dict[str, Any]] = []

    def add(code: str, field: str, source: str, detail: str) -> None:
        finding = {"code": code, "field": field, "source": source, "detail": detail}
        if finding not in findings:
            findings.append(finding)

    for module in modules:
        for entry in module["entries"]:
            parent = _parent(entry["context"], passages)
            mappings.append({**entry, "candidate_parent": parent, "verified": False})
            if parent is None:
                continue
            source, target = parent["text"], entry["text"]
            if _PENDING.search(source) and not _ACHIEVED.search(source) and _ACHIEVED.search(target):
                add("ONSCREEN_LOCAL_STATUS_PROMOTED", entry["field"], source,
                    "Visible completed state replaces the matched planned/exploratory state.")
            if (_PROHIBITION.search(source) and not _PROHIBITION.search(module["text"])
                    and _compact(_PROHIBITION.sub("", source)) == _compact(entry["context"])):
                add("ONSCREEN_LOCAL_PROHIBITION_LOST", entry["field"], source,
                    "The same predicate lost its explicit prohibition.")
            # Only flag newly assigned numeric values when the local parent is
            # confident and contains quantities; missing values have a separate
            # existing retention check. Never borrow numbers from another module.
            source_numbers = set(_NUMBER.findall(source))
            added = set(_NUMBER.findall(target)) - source_numbers
            if source_numbers and added and _anchor(entry["context"]) == _anchor(source):
                add("ONSCREEN_LOCAL_NUMBER_MISMATCH", entry["field"], source,
                    f"Values {sorted(added)} do not belong to the matched proposition.")

    for passage in passages:
        source = passage["text"]
        if _EXAMPLE.match(source):
            continue
        for match in _RESPONSIBILITY.finditer(source):
            actor = match[1].rsplit("由", 1)[-1].strip()
            action = match[2].strip()
            relevant = [m for m in modules if _compact(action) in _compact(m["text"])]
            if relevant and not any(_compact(actor) in _compact(m["text"]) for m in relevant):
                add("ONSCREEN_RESPONSIBILITY_MISMATCH", relevant[0]["field"], source,
                    f"Keep actor '{actor}' attached to responsibility '{action}' in the same visible module.")
        for match in _TRANSFORM.finditer(source):
            input_object, output_object = match[1].strip(), match[2].strip()
            if not any(_contains_object(m["text"], input_object)
                       and _contains_object(m["text"], output_object) for m in modules):
                add("ONSCREEN_TRANSFORMATION_LOST", "onscreen", source,
                    f"Explicit transformation needs both '{input_object}' and '{output_object}'; review any equivalent rewrite against this passage.")
            for module in modules:
                for entry in module["entries"]:
                    text = entry["text"]
                    directions = [(m[1], m[2]) for m in _TRANSFORM.finditer(text)]
                    directions.extend(re.findall(r"([^，。；;\n：:]+?)\s*(?:→|->)\s*([^，。；;\n]+)", text))
                    for left, right in directions:
                        if (_contains_object(left, output_object)
                                and _contains_object(right, input_object)):
                            add("ONSCREEN_TRANSFORMATION_REVERSED", entry["field"], source,
                                "The explicit transformation endpoints are reversed.")
        condition = _CONDITION.match(source)
        if condition:
            qualifier, body = condition.groups()
            condition_payload = re.sub(r"(?:后|前|时|条件下|前提下)$", "", qualifier)
            # An unchanged predicate with its qualifier deleted is a concrete
            # omission. More distant rewrites remain in the Critic packet.
            relevant = [m for m in modules if _compact(body) in _compact(m["text"])]
            if relevant and not any(_compact(condition_payload) in _compact(m["text"]) for m in relevant):
                add("ONSCREEN_LOCAL_CONDITION_LOST", relevant[0]["field"], source,
                    f"Keep condition '{qualifier}' with its visible predicate.")
            opposite = qualifier[:-1] + ({"后": "前", "前": "后"}.get(qualifier[-1], ""))
            if qualifier.endswith(("前", "后")):
                for module in relevant:
                    if _compact(opposite) in _compact(module["text"]):
                        add("ONSCREEN_LOCAL_CONDITION_REVERSED", module["field"], source,
                            f"Condition '{qualifier}' is reversed in the visible module.")

    return {
        "source_passages": passages,
        "visible_modules": modules,
        "candidate_mappings": mappings,
        "findings": findings,
        "semantic_review_required": True,
        "review_directions": ["onscreen_to_full_copy", "full_copy_to_onscreen"],
        "review_instruction": (
            "Verify each visible proposition against its local full-copy parent, then account for all substantive full-copy information. "
            "Check actor, action, object, status, responsibility, quantity with unit/scope, condition and relation direction. "
            "Candidate mappings and findings are unverified hints only. Preserve substantive examples and background; "
            "repair meaning changes using the complete full_copy and onscreen texts, regardless of these hints."
        ),
    }


def onscreen_projection_issues(slide: dict[str, Any]) -> list[str]:
    if slide.get("page_type") != "content" or not slide.get("full_copy"):
        return []
    return [
        f"{item['code']}: {item['field']}: {item['detail']} Source: {item['source']}"
        for item in review_onscreen_projection(slide)["findings"]
    ]
