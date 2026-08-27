"""Modular argument-flow contracts.

The legacy :mod:`cyberppt.argument_flow_contract` module re-exports this API
for compatibility. New implementation belongs in the focused modules here.
"""

from .audit import argument_graph_summary, audit_argument_flow
from .chapter_scope import validate_page_sequence_fields, validate_topic_partition_fields
from .evidence import (
    BOUNDARY_PRIMARY_ARGUMENT_ROLES,
    EVIDENCE_TYPE_TO_CLAIM_ROLE,
    PRIMARY_PROOF_DIRECTION_LIMIT,
)
from .page_contract import validate_source_relation_fields
from .roles import (
    ArgumentFlowIssue,
    CLAIM_ROLES,
    DEFAULT_ALLOWED_CLAIMS,
    PAGE_ARGUMENT_ROLES,
    PAGE_CONTRIBUTION_FIELDS,
    SEMANTIC_CONTRIBUTION_FIELDS,
    validate_page_role_fields,
)
from .storyline import GENERIC_TRANSITIONS, PAGE_ORDER_PRINCIPLES, STORYLINE_PAGE_FIELDS

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
