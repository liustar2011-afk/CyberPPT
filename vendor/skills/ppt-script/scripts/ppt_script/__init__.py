"""PPT script V3 deterministic support package."""

from .audit import audit_script_text, compare_script_texts
from .config import AuditConfig
from .extractors import extract_project_sources, extract_text
from .planning import audit_plan_text, parse_plan
from .source_truth import build_source_inventory, parse_source_truth_map

__all__ = [
    "AuditConfig",
    "audit_plan_text",
    "audit_script_text",
    "build_source_inventory",
    "compare_script_texts",
    "extract_project_sources",
    "extract_text",
    "parse_plan",
    "parse_source_truth_map",
]
