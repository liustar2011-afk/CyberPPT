"""Runtime facade that preserves legacy Final Script audit imports.

Focused helper modules and the focused orchestrator are the runtime authorities.
The legacy module remains as a compatibility namespace during convergence.
"""
from __future__ import annotations

from . import final_authoring as _authoring
from . import final_deck as _deck
from . import final_lean as _lean
from . import final_onscreen as _onscreen
from . import final_orchestrator as _orchestrator
from . import final_script as _legacy


for _focused in (_authoring, _lean, _onscreen, _deck):
    for _name in _focused.__all__:
        setattr(_legacy, _name, getattr(_focused, _name))

_legacy.audit_final_script = _orchestrator.audit_final_script

for _name in _legacy.__all__:
    globals()[_name] = getattr(_legacy, _name)

__all__ = list(_legacy.__all__)
