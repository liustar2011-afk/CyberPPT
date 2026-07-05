#!/usr/bin/env python3
"""Shared JSON read helper for ppt-master scripts.

Single source of truth for the ``load_json`` helper that was previously copied
verbatim across many ``*_lib.py`` modules. Behaviour is intentionally identical
to the historical copies: best-effort read that returns ``{}`` on any missing
file or parse error so callers can treat a project as partially-scaffolded
without wrapping every read in try/except.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
