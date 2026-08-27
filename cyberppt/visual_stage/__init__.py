"""Visual-structure Stage 02 internals.

The public compatibility surface remains ``cyberppt.commands.visual_structure_stage``.
"""

from .audit import run_visual_structure_audit
from .execution import (
    execute_visual_structure_stage,
    prepare_visual_structure_stage,
    record_visual_structure_execution,
    visual_structure_required,
)
from .prompt_gate import assert_visual_structure_ready

__all__ = [
    "assert_visual_structure_ready",
    "execute_visual_structure_stage",
    "prepare_visual_structure_stage",
    "record_visual_structure_execution",
    "run_visual_structure_audit",
    "visual_structure_required",
]
