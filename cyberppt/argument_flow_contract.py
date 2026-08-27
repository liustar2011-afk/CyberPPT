"""Compatibility facade for the modular argument-flow contract package.

Implementation lives under :mod:`cyberppt.argument_flow`. Existing imports are
kept stable while new business rules must be added to the focused modules.
"""

from cyberppt.argument_flow import (
    ArgumentFlowIssue,
    BOUNDARY_PRIMARY_ARGUMENT_ROLES,
    CLAIM_ROLES,
    DEFAULT_ALLOWED_CLAIMS,
    EVIDENCE_TYPE_TO_CLAIM_ROLE,
    GENERIC_TRANSITIONS,
    PAGE_ARGUMENT_ROLES,
    PAGE_CONTRIBUTION_FIELDS,
    PAGE_ORDER_PRINCIPLES,
    PRIMARY_PROOF_DIRECTION_LIMIT,
    SEMANTIC_CONTRIBUTION_FIELDS,
    STORYLINE_PAGE_FIELDS,
    argument_graph_summary,
    audit_argument_flow,
    validate_page_role_fields,
    validate_page_sequence_fields,
    validate_source_relation_fields,
    validate_topic_partition_fields,
)

__all__ = [
    "ArgumentFlowIssue",
    "BOUNDARY_PRIMARY_ARGUMENT_ROLES",
    "CLAIM_ROLES",
    "DEFAULT_ALLOWED_CLAIMS",
    "EVIDENCE_TYPE_TO_CLAIM_ROLE",
    "GENERIC_TRANSITIONS",
    "PAGE_ARGUMENT_ROLES",
    "PAGE_CONTRIBUTION_FIELDS",
    "PAGE_ORDER_PRINCIPLES",
    "PRIMARY_PROOF_DIRECTION_LIMIT",
    "SEMANTIC_CONTRIBUTION_FIELDS",
    "STORYLINE_PAGE_FIELDS",
    "argument_graph_summary",
    "audit_argument_flow",
    "validate_page_role_fields",
    "validate_page_sequence_fields",
    "validate_source_relation_fields",
    "validate_topic_partition_fields",
]
