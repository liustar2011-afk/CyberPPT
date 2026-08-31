"""Runtime facade that routes legacy Final Script orchestration through focused helpers.

The large legacy module remains as the orchestration host while responsibilities are
extracted incrementally. Rebinding its helper globals keeps call order and the public
API stable while making focused modules the runtime authority.
"""
from __future__ import annotations

from . import final_authoring as _authoring
from . import final_lean as _lean
from . import final_script as _legacy


for _focused in (_authoring, _lean):
    for _name in _focused.__all__:
        setattr(_legacy, _name, getattr(_focused, _name))

for _name in _legacy.__all__:
    globals()[_name] = getattr(_legacy, _name)

__all__ = list(_legacy.__all__)
