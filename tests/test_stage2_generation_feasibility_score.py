from cyberppt.visual_structure_contract import _audit_generation_feasibility


def _candidate(*, score: int, dimensions: dict[str, int]):
    return {
        "id": "C1",
        "selection_rationale": {
            "generation_feasibility": {
                "score": score,
                "dimensions": dimensions,
                "risks": [],
            }
        },
    }


def _collector():
    issues = []

    def issue(code, message, page_id=None):
        issues.append({"code": code, "message": message, "page_id": page_id})

    return issues, issue


def test_generation_feasibility_accepts_real_nonperfect_score():
    dimensions = {
        "single_focus": 20,
        "text_capacity": 17,
        "relation_clarity": 19,
        "composition_stability": 18,
        "anti_pattern_risk": 18,
    }
    issues, issue = _collector()

    score = _audit_generation_feasibility(
        _candidate(score=92, dimensions=dimensions), issue, "p01"
    )

    assert score == 92
    assert issues == []


def test_generation_feasibility_rejects_score_sum_mismatch():
    dimensions = {
        "single_focus": 20,
        "text_capacity": 17,
        "relation_clarity": 19,
        "composition_stability": 18,
        "anti_pattern_risk": 18,
    }
    issues, issue = _collector()

    score = _audit_generation_feasibility(
        _candidate(score=100, dimensions=dimensions), issue, "p01"
    )

    assert score is None
    assert [item["code"] for item in issues] == ["CANDIDATE_GENERATION_SCORE_INVALID"]
