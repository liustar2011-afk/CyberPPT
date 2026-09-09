from __future__ import annotations

from pathlib import Path


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"{label} not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


def main() -> None:
    thesis = Path("cyberppt/visual_thesis.py")
    replace_once(
        thesis,
        '    re.compile(r"\\b(?:from|through|into|between|converge|connect|support|flow|feedback|return|map|depend|interface|boundary|exchange|transform|allocate)\\b", re.I),\n',
        '    re.compile(r"\\b(?:from|through|into|between|relationship|relational|peer|converge|connect|supports?|flow|feedback|return|map|depend|interface|boundary|exchange|transform|allocate)\\b", re.I),\n',
        "English relationship vocabulary",
    )

    regression = Path("tests/test_prompt_optimization_regressions.py")
    replace_once(
        regression,
        '''                "id": "c1",
                "semantic_focus": {"kind": "outcome", "evidence_key": "result"},
''',
        '''                "id": "c1",
                "visual_thesis": "Input flows through the approved relationship into the result.",
                "semantic_focus": {"kind": "outcome", "evidence_key": "result"},
''',
        "prompt optimization visual thesis fixture",
    )

    structure = Path("tests/test_visual_structure_stage.py")
    replace_once(
        structure,
        "from __future__ import annotations\n\nimport json\n",
        "from __future__ import annotations\n\nimport copy\nimport json\n",
        "visual structure copy import",
    )
    replace_once(
        structure,
        '''from cyberppt.onscreen_expression import expression_constraints
from cyberppt.onscreen_expression import expression_constraints_sha256


class VisualStructureStageTests(unittest.TestCase):
''',
        '''from cyberppt.onscreen_expression import expression_constraints
from cyberppt.onscreen_expression import expression_constraints_sha256


_RAW_BUILD_EXECUTABLE_PAGE = _build_executable_page


def _build_executable_page(source, decision):
    """Migrate legacy fixtures to the required visual-thesis contract.

    Missing-thesis rejection is covered separately by
    test_visual_thesis_compiler_contract.py. These older structure fixtures
    need an explicit relational thesis so they can reach the contract they
    were originally written to exercise.
    """
    migrated = copy.deepcopy(decision)
    for candidate in migrated.get("candidates", []):
        candidate.setdefault(
            "visual_thesis",
            "Approved evidence flows through the source-supported relationship.",
        )
    return _RAW_BUILD_EXECUTABLE_PAGE(source, migrated)


class VisualStructureStageTests(unittest.TestCase):
''',
        "legacy visual structure fixture migration",
    )

    schema = Path("vendor/skills/ppt-visual-structure-designer/assets/page-visual-spec.schema.json")
    replace_once(
        schema,
        '''    "region_graph": {
      "type": "object",
''',
        '''    "composition_strategy": {
      "type": "object",
      "additionalProperties": false,
      "required": [
        "strategy_id",
        "topology",
        "primary_axis",
        "geometry",
        "anchor_policy",
        "weight_policy",
        "span_policy",
        "score",
        "rationale",
        "version"
      ],
      "properties": {
        "strategy_id": {
          "enum": [
            "editorial_horizontal",
            "editorial_vertical",
            "open_spatial_field",
            "radial_focus_field",
            "layered_editorial_stack",
            "split_boundary_field",
            "stepped_spatial_path"
          ]
        },
        "topology": {
          "enum": [
            "parallel_set",
            "causal_convergence",
            "layered_architecture",
            "directed_flow",
            "lifecycle_loop",
            "governance_boundary",
            "ecosystem_map",
            "allocation_flow",
            "conclusion_anchor"
          ]
        },
        "primary_axis": {
          "enum": [
            "horizontal",
            "vertical",
            "radial",
            "bidirectional",
            "layered",
            "free_spatial"
          ]
        },
        "geometry": {"type": "string", "minLength": 1},
        "anchor_policy": {
          "enum": ["axis", "free", "focus_centered", "split", "stepped"]
        },
        "weight_policy": {
          "enum": ["semantic_focus", "paired"]
        },
        "span_policy": {
          "enum": ["compact", "free", "focus_half", "band", "half"]
        },
        "score": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        },
        "rationale": {
          "type": "array",
          "minItems": 1,
          "items": {"type": "string", "minLength": 1}
        },
        "version": {"const": "composition-strategy-v1"}
      },
      "description": "Independent macro-composition strategy. Semantic topology remains the relationship-truth authority."
    },
    "region_graph": {
      "type": "object",
''',
        "composition strategy schema",
    )
    replace_once(
        schema,
        '''        "primary_axis": {
          "enum": [
            "horizontal",
            "vertical",
            "radial",
            "bidirectional",
            "layered",
            "free_spatial"
          ]
        },
        "regions": {
''',
        '''        "primary_axis": {
          "enum": [
            "horizontal",
            "vertical",
            "radial",
            "bidirectional",
            "layered",
            "free_spatial"
          ]
        },
        "composition_strategy_id": {
          "type": "string",
          "minLength": 1
        },
        "regions": {
''',
        "region graph composition strategy id schema",
    )
    replace_once(
        schema,
        '''        "preferred": {
          "enum": [
            "business_scene",
            "object_illustration",
            "relationship_diagram",
            "data_visualization",
            "mixed"
          ]
        },
        "allowed": {
''',
        '''        "version": {
          "const": "visual-medium-policy-v2"
        },
        "preferred": {
          "enum": [
            "business_scene",
            "object_illustration",
            "relationship_diagram",
            "data_visualization",
            "mixed"
          ]
        },
        "secondary": {
          "enum": [
            "",
            "business_scene",
            "object_illustration",
            "relationship_diagram",
            "data_visualization",
            "mixed"
          ]
        },
        "allowed": {
''',
        "visual medium version and secondary schema",
    )
    replace_once(
        schema,
        '''        "scene_policy": {
          "enum": [
            "required",
            "allowed",
            "forbidden",
            "auto"
          ]
        },
        "rationale": {
''',
        '''        "forbidden": {
          "type": "array",
          "uniqueItems": true,
          "items": {
            "enum": [
              "business_scene",
              "object_illustration",
              "relationship_diagram",
              "data_visualization",
              "mixed"
            ]
          }
        },
        "scene_policy": {
          "enum": [
            "required",
            "allowed",
            "forbidden",
            "auto"
          ]
        },
        "confidence": {
          "type": "number",
          "minimum": 0,
          "maximum": 1
        },
        "scores": {
          "type": "object",
          "additionalProperties": false,
          "properties": {
            "business_scene": {"type": "number", "minimum": 0, "maximum": 1},
            "object_illustration": {"type": "number", "minimum": 0, "maximum": 1},
            "relationship_diagram": {"type": "number", "minimum": 0, "maximum": 1},
            "data_visualization": {"type": "number", "minimum": 0, "maximum": 1},
            "mixed": {"type": "number", "minimum": 0, "maximum": 1}
          }
        },
        "rationale": {
''',
        "visual medium v2 schema fields",
    )


if __name__ == "__main__":
    main()
