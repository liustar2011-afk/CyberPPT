"""Legacy compatibility facade for Script Engine delivery contracts.

Historical callers may still import :mod:`script_engine.contract_rules`. The
canonical public API now lives in :mod:`script_engine.contracts`, which routes
each responsibility to a focused module. Keep this file implementation-free so
legacy imports cannot create a second rule authority.
"""
from __future__ import annotations

from .contracts import *  # noqa: F401,F403
from .contracts import __all__
