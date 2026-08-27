"""Storyline and chapter ordering vocabulary."""

STORYLINE_PAGE_FIELDS = (
    "storyline_role",
    "transition_from_previous",
    "transition_to_next",
)
GENERIC_TRANSITIONS = frozenset(
    {"承上启下", "承接上页", "引出下页", "进入下一页", "继续说明", "进一步说明"}
)
PAGE_ORDER_PRINCIPLES = frozenset(
    {
        "definition_before_detail",
        "whole_before_parts",
        "dependency_before_dependent",
        "mechanism_before_execution",
        "process_direction",
        "status_or_maturity_progression",
        "source_argument_sequence",
        "audience_question_progression",
    }
)

__all__ = ["GENERIC_TRANSITIONS", "PAGE_ORDER_PRINCIPLES", "STORYLINE_PAGE_FIELDS"]
