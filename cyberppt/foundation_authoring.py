"""Prepare and validate direct Foundation authoring for the script profile."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from script_engine.source_index import render_source_context, validate_reading_strategy

from .source_document_map import prepare_source_context

FOUNDATION_PATH = Path("script/foundation.json")


def _render_authoring_task(project: Path, source_index: dict[str, Any]) -> str:
    output = project / FOUNDATION_PATH
    strategy = source_index.get("reading_strategy") or {}
    context = render_source_context(source_index, reading_strategy=strategy)
    return f"""# CyberPPT script-profile Foundation authoring task

Write one source-faithful Foundation JSON to:

`{output}`

Use `contracts/foundation.schema.json` as the contract. Preserve every source
heading in `source_structure`, retain source identity and SHA-256 in `sources`,
and bind authored facts, constraints, numbers, argument nodes, and inferred
relations to stable `SU-*` source-unit references.

Foundation is a lightweight source-preservation index for page planning and
writing. Preserve and separate source propositions; do not strengthen, complete,
interpret or strategize them. Apply these rules before writing any
downstream-facing field:

- `document_semantics.primary_thesis` must be a near-extractive statement of the
  source's own main proposition. When the source provides several parallel
  propositions but no single governing claim, retain them as ordered parallel
  clauses instead of inventing causality, necessity, priority or a value thesis.
- `author_purpose` states only the action the source author explicitly undertakes
  or requests. `argument_method` describes the source's actual order of topics
  and claims; it must not manufacture a problem, tension, rationale or necessity.
- A fact preserves the source predicate and its direction. Do not convert
  “为确保达到某节点而组织开展工作” into “该工作服务于该节点”, “为该节点
  提供实际应用支撑” or another reversed/expanded relationship.
- Keep only source-explicit relations in authoritative theses, facts, argument
  nodes and `relations`. Do not search for, reconstruct or record latent
  relations in the default script profile; an empty `relations` collection is
  valid. Analytical inference belongs only to an explicitly requested
  analytical workflow.
- Do not add connective language such as “因此、从而、意味着、只有…才、
  必须…才能、需要在…条件下形成…” unless that same relationship is explicit in
  the cited source unit. Adjacency and shared vocabulary are not evidence of a
  relationship.

Set `source_consumption_policy: required` and
`source_consumption_contract_version: 2`. When one fact or constraint cites a
compound paragraph, several table rows, or several list items, populate
`semantic_units` before summarizing it: preserve each independently meaningful
sentence or row as its own unit, give it a stable ID and `text`, and bind it with
`source_unit_ref` or `source_unit_refs`. A short source unit carrying one atomic
fact may remain a single fact without `semantic_units`. Do not replace row-level
objects, actions, responsibilities, conditions, outputs, or boundaries with a
category label.

Review `Source asset candidates` as derived routing hints. Promote only useful
caption, table, formula, image or chart candidates into `source_assets`; retain
the candidate ID, kind, locator and complete source-unit refs unchanged. Author
its `meaning`, bind at least one value in `argument_node_ids` whose source refs intersect
the asset, and state `wrong_reading`. Mark `presentation_role: money_slide` only
when the asset is expected to carry the deck's peak argument.

Author `document_thesis` and an ordered `document_semantics.argument_method`
whose referenced `argument_nodes` collectively cover every source-structure
node. Each `source_structure` node must retain its heading unit in
`source_refs`; selection depth cannot change the source argument order.

Use the following deterministic recommendation as the initial
`reading_strategy`. For long mode, show the communication goal, mapped/deep-read
selection and exclusion reasons at the first human stop; incorporate the user's
changes before authoring Foundation:

```json
{json.dumps(strategy, ensure_ascii=False, indent=2)}
```

For long mode, mapped previews establish structure and routing only. Deep-read
the exact source units before authoring precise numbers, dates, responsibilities,
status, conditions, exclusions, or strong conclusions. Preserve all source
sections in the argument skeleton; every excluded section requires a reason.

Do not create slides, a Content Plan, Source Truth, semantic sidecars, approval
files, checkpoints, or receipts. Output the Foundation JSON only, then run:

`.venv/bin/python3 -m script_engine.cli validate foundation {output}`
`.venv/bin/python3 -m script_engine.cli audit-foundation {output}`

{context}"""


def prepare_script_foundation(project: Path, *, profile: str = "script") -> dict[str, Any]:
    """Prepare the model authoring task; semantic Foundation remains model-authored."""

    project = project.expanduser().resolve()
    if profile not in {"script", "strict", "legacy"}:
        raise ValueError("profile must be script, strict, or legacy")
    if profile != "script":
        raise ValueError(
            "strict/legacy projects use prepare-source-map, semantic understanding, "
            "and project-foundation; prepare-script-foundation is script-profile only"
        )
    source_index = prepare_source_context(project)
    if source_index.get("status") != "passed":
        codes = [str(item.get("code")) for item in source_index.get("issues") or []]
        raise ValueError(f"source context requires repair before Foundation authoring: {codes}")
    return {
        "schema": "cyberppt.foundation_authoring_task.v1",
        "profile": "script",
        "project": str(project),
        "source_index": str(source_index["source_index"]),
        "output": str(project / FOUNDATION_PATH),
        "reading_load": source_index.get("reading_load"),
        "reading_strategy": source_index.get("reading_strategy"),
        "authoring_task": _render_authoring_task(project, source_index),
    }


__all__ = ["prepare_script_foundation", "validate_reading_strategy"]
