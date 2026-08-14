"""Deterministic Markdown structure and source-assertion fact-base extraction."""
from .factbase import build_fact_base
from .parser import parse_document
__all__=["build_fact_base","parse_document"]
__version__="0.2.0"
