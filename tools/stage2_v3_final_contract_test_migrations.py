from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"{label} not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def main() -> None:
    page_spec = Path("tests/test_page_artifact_spec.py")
    replace_once(
        page_spec,
        '''    def test_dense_non_scene_page_defaults_to_relationship_field_only(self) -> None:
        budget = _visual_budget(
            {},
            topology="layered_architecture",
            use_scene=False,
            visible_text=tuple("dense evidence" for _ in range(14)),
        )
        self.assertEqual("relationship_field_only", budget.mode)
        self.assertEqual(0, budget.max_auxiliary_fragments)
        self.assertEqual("page", budget.scope)
        self.assertFalse(budget.region_local_visuals)
''',
        '''    def test_dense_text_no_longer_overrides_non_scene_visual_budget(self) -> None:
        budget = _visual_budget(
            {},
            topology="layered_architecture",
            use_scene=False,
            visible_text=tuple("dense evidence" for _ in range(14)),
        )
        self.assertEqual("shared_field", budget.mode)
        self.assertEqual(1, budget.max_auxiliary_fragments)
        self.assertEqual("page", budget.scope)
        self.assertFalse(budget.region_local_visuals)
''',
        "page artifact dense budget expectation",
    )

    scene_policy = Path("tests/test_stage2_scene_policy.py")
    replace_once(
        scene_policy,
        '''def test_dense_page_still_limits_visual_fragments() -> None:
    assert _visual_budget(True, "required") == {
        "mode": "relationship_field_only",
        "max_auxiliary_fragments": 0,
        "scope": "page",
        "region_local_visuals": False,
    }
''',
        '''def test_dense_page_does_not_override_visual_budget() -> None:
    assert _visual_budget(True, "required") == {
        "mode": "integrated_scene",
        "max_auxiliary_fragments": 4,
        "scope": "region",
        "region_local_visuals": True,
    }
''',
        "visual stage dense budget expectation",
    )

    artifact_prompt = Path("tests/test_artifact_prompt.py")
    replace_once(
        artifact_prompt,
        '        self.assertEqual("v4", compiled.prompt_ir_version)\n',
        '        self.assertEqual("v6", compiled.prompt_ir_version)\n',
        "final prompt IR version expectation",
    )

    region_graph = Path("tests/test_region_graph_compiler.py")
    replace_once(
        region_graph,
        '''    assert graph["primary_axis"] == "radial"
    assert {item["role"] for item in graph["regions"]} == {"lifecycle_stage"}
    assert {item["anchor"] for item in graph["regions"]} == {"free"}
    assert "feedback" in {item["type"] for item in graph["relations"]}
''',
        '''    assert graph["primary_axis"] == "radial"
    assert {item["role"] for item in graph["regions"]} == {"lifecycle_stage"}
    assert _region(graph, "E3")["anchor"] == "center"
    assert {_region(graph, "E1")["anchor"], _region(graph, "E2")["anchor"]} == {"free"}
    assert "feedback" in {item["type"] for item in graph["relations"]}
''',
        "lifecycle composition anchor expectation",
    )


if __name__ == "__main__":
    main()
