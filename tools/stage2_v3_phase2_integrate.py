from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    content = read(path)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one target, found {count}: {old[:100]!r}")
    write(path, content.replace(old, new, 1))


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, text=True)


# 1. Extend CompositionStrategy with explicit materialization and a clearly
# marked legacy projection.  New Stage02 compilation never uses the legacy map.
strategy_path = "cyberppt/composition_strategy.py"
if "def materialize_composition_strategy(" not in read(strategy_path):
    marker = "\ndef resolve_composition_strategy(\n"
    insertion = '''\ndef materialize_composition_strategy(\n    *,\n    topology: str,\n    strategy_id: str,\n    score: float = 1.0,\n    rationale: tuple[str, ...] = ("explicit composition strategy",),\n) -> CompositionStrategySpec:\n    if strategy_id not in legal_strategy_ids(topology):\n        raise ValueError(f"composition strategy {strategy_id!r} is not legal for topology {topology!r}")\n    blueprint = _STRATEGY_BLUEPRINTS[strategy_id]\n    return CompositionStrategySpec(\n        strategy_id=strategy_id,\n        topology=topology,\n        primary_axis=blueprint["primary_axis"],\n        geometry=blueprint["geometry"],\n        anchor_policy=blueprint["anchor_policy"],\n        weight_policy=blueprint["weight_policy"],\n        span_policy=blueprint["span_policy"],\n        score=score,\n        rationale=rationale,\n    )\n\n\n# Compatibility only: old callers that do not provide CompositionStrategy keep\n# their historical macro axis.  This is not the v3 production resolver.\n_LEGACY_DEFAULT_STRATEGY_BY_TOPOLOGY = {\n    "parallel_set": "open_spatial_field",\n    "causal_convergence": "radial_focus_field",\n    "layered_architecture": "layered_editorial_stack",\n    "directed_flow": "editorial_horizontal",\n    "lifecycle_loop": "radial_focus_field",\n    "governance_boundary": "editorial_horizontal",\n    "ecosystem_map": "open_spatial_field",\n    "allocation_flow": "editorial_horizontal",\n    "conclusion_anchor": "editorial_horizontal",\n}\n\n\ndef legacy_composition_strategy(topology: str) -> CompositionStrategySpec:\n    try:\n        strategy_id = _LEGACY_DEFAULT_STRATEGY_BY_TOPOLOGY[topology]\n    except KeyError as exc:\n        raise ValueError(f"unsupported composition topology: {topology!r}") from exc\n    return materialize_composition_strategy(\n        topology=topology,\n        strategy_id=strategy_id,\n        score=0.5,\n        rationale=("legacy Stage02 compatibility projection",),\n    )\n\n'''
    replace_once(strategy_path, marker, insertion + marker)
    replace_once(
        strategy_path,
        '    "legal_strategy_ids",\n    "resolve_composition_strategy",\n',
        '    "legal_strategy_ids",\n    "legacy_composition_strategy",\n    "materialize_composition_strategy",\n    "resolve_composition_strategy",\n',
    )

# 2. RegionGraph consumes CompositionStrategy rather than deriving axis from topology.
region_path = "cyberppt/region_graph.py"
if "from cyberppt.composition_strategy import" not in read(region_path):
    replace_once(
        region_path,
        "from typing import Any, Mapping\n\n",
        "from typing import Any, Mapping\n\n"
        "from cyberppt.composition_strategy import (\n"
        "    CompositionStrategySpec, legacy_composition_strategy, legal_strategy_ids,\n"
        ")\n\n",
    )

if "composition_strategy_id: str = \"\"" not in read(region_path):
    replace_once(
        region_path,
        "    relations: tuple[RegionRelationSpec, ...]\n\n    def to_dict(self) -> dict[str, Any]:\n",
        "    relations: tuple[RegionRelationSpec, ...]\n"
        "    composition_strategy_id: str = \"\"\n\n"
        "    def to_dict(self) -> dict[str, Any]:\n",
    )
    replace_once(
        region_path,
        '            "relations": [\n                {"from": item.source, "to": item.target, "type": item.type}\n                for item in self.relations\n            ],\n',
        '            "relations": [\n                {"from": item.source, "to": item.target, "type": item.type}\n                for item in self.relations\n            ],\n            **({"composition_strategy_id": self.composition_strategy_id} if self.composition_strategy_id else {}),\n',
    )
    replace_once(
        region_path,
        "        relations=tuple(relations),\n    )\n\n\n_AXIS_BY_TOPOLOGY = {\n    \"parallel_set\": \"free_spatial\",\n    \"causal_convergence\": \"radial\",\n    \"layered_architecture\": \"layered\",\n    \"directed_flow\": \"horizontal\",\n    \"lifecycle_loop\": \"radial\",\n    \"governance_boundary\": \"horizontal\",\n    \"ecosystem_map\": \"free_spatial\",\n    \"allocation_flow\": \"horizontal\",\n    \"conclusion_anchor\": \"horizontal\",\n}\n\n",
        "        relations=tuple(relations),\n"
        "        composition_strategy_id=str(value.get(\"composition_strategy_id\") or \"\").strip(),\n"
        "    )\n\n\n",
    )

old_anchor = '''def _region_anchor(\n    topology: str,\n    evidence_id: str,\n    focus_id: str,\n    position: int,\n    total: int,\n    axis: str,\n) -> str:\n    if topology == "causal_convergence":\n        return "center" if evidence_id == focus_id else "free"\n    if topology in {"parallel_set", "ecosystem_map", "lifecycle_loop"}:\n        return "free"\n    if topology == "governance_boundary":\n        if evidence_id == focus_id:\n            return "center"\n        focus_position = max(0, min(total - 1, position))\n        return "left" if position < focus_position else "right"\n    return _axis_anchor(axis, position, total)\n'''
new_anchor = '''def _region_anchor(\n    strategy: CompositionStrategySpec,\n    evidence_id: str,\n    focus_id: str,\n    position: int,\n    total: int,\n) -> str:\n    policy = strategy.anchor_policy\n    if policy == "focus_centered":\n        return "center" if evidence_id == focus_id else "free"\n    if policy == "free":\n        return "free"\n    if policy == "split":\n        if evidence_id == focus_id:\n            return "center"\n        focus_position = max(0, min(total - 1, position))\n        return "left" if position < focus_position else "right"\n    if policy == "stepped":\n        if total <= 1:\n            return "center"\n        if position == 0:\n            return "top_left"\n        if position == total - 1:\n            return "bottom_right"\n        return "center"\n    return _axis_anchor(strategy.primary_axis, position, total)\n'''
if old_anchor in read(region_path):
    replace_once(region_path, old_anchor, new_anchor)

old_span = '''def _region_span(topology: str, evidence_id: str, focus_id: str) -> str:\n    if topology == "layered_architecture":\n        return "band"\n    if topology in {"parallel_set", "ecosystem_map", "lifecycle_loop"}:\n        return "free"\n    if evidence_id == focus_id and topology in {"causal_convergence", "conclusion_anchor"}:\n        return "half"\n    if topology == "governance_boundary":\n        return "half"\n    return "compact"\n'''
new_span = '''def _region_span(strategy: CompositionStrategySpec, evidence_id: str, focus_id: str) -> str:\n    if strategy.span_policy == "band":\n        return "band"\n    if strategy.span_policy == "free":\n        return "free"\n    if strategy.span_policy == "half":\n        return "half"\n    if strategy.span_policy == "focus_half" and evidence_id == focus_id:\n        return "half"\n    return "compact"\n'''
if old_span in read(region_path):
    replace_once(region_path, old_span, new_span)

if "composition_strategy: CompositionStrategySpec | None = None," not in read(region_path):
    replace_once(
        region_path,
        "    semantic_edges: list[Mapping[str, object]] | tuple[Mapping[str, object], ...],\n"
        "    focus_policy: str,\n"
        ") -> dict[str, Any]:\n",
        "    semantic_edges: list[Mapping[str, object]] | tuple[Mapping[str, object], ...],\n"
        "    focus_policy: str,\n"
        "    composition_strategy: CompositionStrategySpec | None = None,\n"
        ") -> dict[str, Any]:\n",
    )
    replace_once(
        region_path,
        "    axis = _AXIS_BY_TOPOLOGY[topology]\n"
        "    region_by_evidence = {evidence_id: f\"RG{index:02d}\" for index, evidence_id in enumerate(reading, 1)}\n",
        "    strategy = composition_strategy or legacy_composition_strategy(topology)\n"
        "    if strategy.topology != topology or strategy.strategy_id not in legal_strategy_ids(topology):\n"
        "        raise ValueError(\"Region Graph composition strategy is incompatible with semantic topology\")\n"
        "    region_by_evidence = {evidence_id: f\"RG{index:02d}\" for index, evidence_id in enumerate(reading, 1)}\n",
    )
    replace_once(
        region_path,
        "        anchor = _region_anchor(topology, evidence_id, focus_id, position, len(reading), axis)\n"
        "        if topology == \"governance_boundary\" and evidence_id != focus_id:\n"
        "            anchor = \"left\" if position < focus_position else \"right\"\n",
        "        anchor = _region_anchor(strategy, evidence_id, focus_id, position, len(reading))\n",
    )
    replace_once(
        region_path,
        '            "span": _region_span(topology, evidence_id, focus_id),\n',
        '            "span": _region_span(strategy, evidence_id, focus_id),\n',
    )
    replace_once(
        region_path,
        '        "primary_axis": axis,\n        "regions": regions,\n',
        '        "primary_axis": strategy.primary_axis,\n        "composition_strategy_id": strategy.strategy_id,\n        "regions": regions,\n',
    )

# 3. Production Visual Stage resolves strategy independently and passes it to RegionGraph.
compiler_path = "cyberppt/visual_stage/compiler.py"
if "from cyberppt.composition_strategy import resolve_composition_strategy" not in read(compiler_path):
    replace_once(
        compiler_path,
        "from cyberppt.page_artifact_spec import is_text_dense\n",
        "from cyberppt.composition_strategy import resolve_composition_strategy\n"
        "from cyberppt.page_artifact_spec import is_text_dense\n",
    )

if "composition_strategy = resolve_composition_strategy(" not in read(compiler_path):
    replace_once(
        compiler_path,
        "    region_graph = bind_region_graph_text(\n"
        "        build_region_graph(\n",
        "    composition_strategy = resolve_composition_strategy(\n"
        "        topology=topology,\n"
        "        focus_policy=focus_policy,\n"
        "        evidence_count=len(evidence_keys),\n"
        "        medium=str((design.get(\"visual_medium_policy\") or {}).get(\"preferred\") or \"\"),\n"
        "        page_index=int(source.get(\"page_number\") or 0),\n"
        "        adjacent_strategy_ids=tuple(\n"
        "            str(value) for value in source.get(\"adjacent_composition_strategy_ids\") or [] if str(value)\n"
        "        ),\n"
        "    )\n"
        "    region_graph = bind_region_graph_text(\n"
        "        build_region_graph(\n",
    )
    replace_once(
        compiler_path,
        "            semantic_edges=graph_edges,\n"
        "            focus_policy=focus_policy,\n"
        "        ),\n",
        "            semantic_edges=graph_edges,\n"
        "            focus_policy=focus_policy,\n"
        "            composition_strategy=composition_strategy,\n"
        "        ),\n",
    )
    replace_once(
        compiler_path,
        '        "region_graph": region_graph,\n        "visual_medium_policy": medium_policy,\n',
        '        "composition_strategy": composition_strategy.to_dict(),\n        "region_graph": region_graph,\n        "visual_medium_policy": medium_policy,\n',
    )

# 4. Integration tests: same topology, three macro geometries, same relationship truth.
test_path = ROOT / "tests/test_region_graph_composition_strategy.py"
test_path.write_text(
    '''from cyberppt.composition_strategy import (\n    legal_strategy_ids, materialize_composition_strategy, resolve_composition_strategy,\n)\nfrom cyberppt.region_graph import build_region_graph\n\n\ndef _graph(strategy):\n    return build_region_graph(\n        topology="directed_flow",\n        evidence_ids=("E1", "E2", "E3"),\n        focus_id="E3",\n        reading_sequence=("E1", "E2", "E3"),\n        semantic_edges=(\n            {"from": "E1", "to": "E2", "relation": "flow"},\n            {"from": "E2", "to": "E3", "relation": "flow"},\n        ),\n        focus_policy="sequence_focus",\n        composition_strategy=strategy,\n    )\n\n\ndef test_region_graph_consumes_three_legal_macro_strategies_for_same_topology():\n    signatures = set()\n    relation_signatures = set()\n    for strategy_id in legal_strategy_ids("directed_flow"):\n        strategy = materialize_composition_strategy(topology="directed_flow", strategy_id=strategy_id)\n        graph = _graph(strategy)\n        assert graph["composition_strategy_id"] == strategy_id\n        signatures.add((graph["primary_axis"], tuple(item["anchor"] for item in graph["regions"])))\n        relation_signatures.add(tuple((item["from"], item["to"], item["type"]) for item in graph["relations"]))\n    assert len(signatures) >= 3\n    assert len(relation_signatures) == 1\n\n\ndef test_legacy_region_graph_call_preserves_compatibility_projection():\n    graph = build_region_graph(\n        topology="layered_architecture",\n        evidence_ids=("E1", "E2", "E3"),\n        focus_id="E3",\n        reading_sequence=("E1", "E2", "E3"),\n        semantic_edges=(),\n        focus_policy="sequence_focus",\n    )\n    assert graph["primary_axis"] == "layered"\n    assert graph["composition_strategy_id"] == "layered_editorial_stack"\n\n\ndef test_dynamic_resolver_can_change_axis_without_changing_topology():\n    first = resolve_composition_strategy(\n        topology="directed_flow", focus_policy="sequence_focus", evidence_count=3,\n        medium="business_scene", page_index=1,\n    )\n    second = resolve_composition_strategy(\n        topology="directed_flow", focus_policy="sequence_focus", evidence_count=6,\n        medium="relationship_diagram", page_index=2, adjacent_strategy_ids=(first.strategy_id,),\n    )\n    assert first.topology == second.topology\n    assert first.strategy_id != second.strategy_id\n''',
    encoding="utf-8",
    newline="\n",
)

# 5. Targeted tests. Existing region_graph tests are included when present.
tests = ["tests/test_composition_strategy.py", "tests/test_region_graph_composition_strategy.py"]
if (ROOT / "tests/test_region_graph.py").exists():
    tests.append("tests/test_region_graph.py")
run("python", "-m", "pytest", "-q", *tests)

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", strategy_path, region_path, compiler_path, "tests/test_region_graph_composition_strategy.py")
diff = run("git", "diff", "--cached", "--quiet", check=False)
if diff.returncode != 0:
    run("git", "commit", "-m", "stage2-v3: decouple topology from composition strategy")
    run("git", "push", "origin", "HEAD:feature/stage2-artifact-contract-v3")
