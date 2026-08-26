from __future__ import annotations

from pathlib import Path

from cyberppt.semantic_expression_models import DEFAULT_LIBRARY, load_expression_models, model_candidates


def test_loads_scqa_from_single_markdown_library() -> None:
    model = load_expression_models(DEFAULT_LIBRARY)["scqa"]

    assert [slot.name for slot in model.slots] == ["situation", "complication", "question", "answer"]
    assert "S → C → Q → A" in model.expression_structure
    assert next(slot for slot in model.slots if slot.name == "question").implicit_allowed
    assert model.lifecycle == "verified"


def test_candidates_rank_declared_signature_and_keep_source_native() -> None:
    models = load_expression_models(DEFAULT_LIBRARY)
    candidates = model_candidates(models, {"context", "tension", "response"})

    assert candidates[0].model_id == "scqa"
    assert candidates[-1].model_id == "source_native"


def test_rejects_duplicate_model_ids(tmp_path: Path) -> None:
    path = tmp_path / "models.md"
    source = DEFAULT_LIBRARY.read_text(encoding="utf-8")
    path.write_text(source + source[source.index("## scqa"):source.index("## pyramid_principle")], encoding="utf-8")

    try:
        load_expression_models(path)
    except ValueError as exc:
        assert "duplicate" in str(exc)
    else:
        raise AssertionError("duplicate model ids must be rejected")


def test_candidate_model_is_not_automatically_ranked(tmp_path: Path) -> None:
    library = tmp_path / "models.md"
    library.write_text(
        """## Source native\n<!-- model\nid: source_native\nfamily: native\nlifecycle: verified\nsemantic_signature: []\nslots: []\nforbidden_inferences: []\n-->\n### Expression structure\n\nNative\n\n## Candidate\n<!-- model\nid: candidate\nfamily: test\nlifecycle: candidate\nsemantic_signature: [context]\nslots: []\nforbidden_inferences: []\n-->\n### Expression structure\n\nCandidate\n""",
        encoding="utf-8",
    )

    assert [model.model_id for model in model_candidates(load_expression_models(library), {"context"})] == ["source_native"]
