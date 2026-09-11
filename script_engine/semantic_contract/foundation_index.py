"""Addressable Foundation index used by structured semantic audits."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from script_engine.source_trace_contracts import FOUNDATION_CITABLE_KEYS

from .models import FoundationRecord


def _iter_records(value: object) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            if isinstance(item, dict):
                yield item


class FoundationIndex:
    """Index current Foundation records without reparsing source documents."""

    def __init__(self, foundation: dict[str, Any] | None) -> None:
        self._records: dict[str, FoundationRecord] = {}
        self._aliases: dict[str, str] = {}
        self._relations: list[dict[str, Any]] = []
        payload = foundation if isinstance(foundation, dict) else {}
        for kind in (*FOUNDATION_CITABLE_KEYS, "argument_nodes"):
            self._index_collection(kind, payload.get(kind))
        semantic_units = payload.get("semantic_units")
        if isinstance(semantic_units, dict):
            for kind, values in semantic_units.items():
                self._index_collection(f"semantic_units.{kind}", values)
        elif isinstance(semantic_units, list):
            self._index_collection("semantic_units", semantic_units)
        self._relations.extend(_iter_records(payload.get("relations")))
        self._relations.extend(_iter_records(payload.get("argument_relations")))

    def _index_collection(self, kind: str, values: object) -> None:
        for item in _iter_records(values):
            ref = str(item.get("id") or "").strip()
            if not ref:
                continue
            self._records.setdefault(ref, FoundationRecord(ref, kind, item))
            for key in ("source_refs", "source_unit_refs", "coverage_anchors"):
                aliases = item.get(key)
                if isinstance(aliases, list):
                    for alias in aliases:
                        alias_text = str(alias or "").strip()
                        if alias_text:
                            self._aliases.setdefault(alias_text, ref)
            alias = str(item.get("source_unit_ref") or "").strip()
            if alias:
                self._aliases.setdefault(alias, ref)

    def record(self, ref: str) -> FoundationRecord | None:
        key = str(ref or "").strip()
        return self._records.get(key) or self._records.get(self._aliases.get(key, ""))

    def records(self) -> tuple[FoundationRecord, ...]:
        return tuple(self._records.values())

    def contains(self, ref: str) -> bool:
        return self.record(ref) is not None

    def status(self, ref: str) -> str:
        record = self.record(ref)
        if record is None:
            return ""
        return str(
            record.payload.get("status")
            or record.payload.get("semantic_status")
            or record.payload.get("strength")
            or ""
        ).strip()

    def argument_duty(self, ref: str) -> str:
        record = self.record(ref)
        if record is None:
            return ""
        return str(
            record.payload.get("argument_duty")
            or record.payload.get("argument_role")
            or record.payload.get("claim_role")
            or record.payload.get("role")
            or record.payload.get("duty")
            or record.payload.get("argument_weight")
            or ""
        ).strip()

    def actors(self, ref: str) -> tuple[str, ...]:
        """Return explicitly typed actors, including referenced entity names.

        This is a read-only projection of Foundation structure. It does not infer
        actors from prose or business keywords.
        """

        record = self.record(ref)
        if record is None:
            return ()

        actors: list[str] = []
        value = record.payload.get("actors") or record.payload.get("actor")
        if isinstance(value, list):
            actors.extend(str(item).strip() for item in value if str(item).strip())
        else:
            text = str(value or "").strip()
            if text:
                actors.append(text)

        for entity_ref in record.payload.get("entity_refs") or []:
            if not isinstance(entity_ref, str) or not entity_ref.strip():
                continue
            entity = self.record(entity_ref)
            if entity is None:
                continue
            name = str(entity.payload.get("name") or "").strip()
            if name:
                actors.append(name)

        return tuple(dict.fromkeys(actors))

    def conditions(self, ref: str) -> tuple[str, ...]:
        record = self.record(ref)
        if record is None:
            return ()
        value = record.payload.get("conditions") or record.payload.get("condition")
        if isinstance(value, list):
            return tuple(str(item).strip() for item in value if str(item).strip())
        text = str(value or "").strip()
        return (text,) if text else ()

    def claim_origin(self, ref: str) -> str:
        record = self.record(ref)
        if record is None:
            return ""
        return str(
            record.payload.get("claim_origin")
            or record.payload.get("origin")
            or record.payload.get("basis")
            or record.payload.get("strength")
            or ""
        ).strip()

    def relations_between(self, refs: Iterable[str]) -> tuple[dict[str, Any], ...]:
        wanted = {str(ref).strip() for ref in refs if str(ref).strip()}
        matches: list[dict[str, Any]] = []
        for relation in self._relations:
            endpoints: set[str] = set()
            for key in ("from", "to", "source", "target"):
                value = relation.get(key)
                if isinstance(value, str) and value.strip():
                    endpoints.add(value.strip())
            support = relation.get("support")
            if isinstance(support, list):
                endpoints.update(str(item).strip() for item in support if str(item).strip())
            if endpoints & wanted:
                matches.append(relation)
        return tuple(matches)
