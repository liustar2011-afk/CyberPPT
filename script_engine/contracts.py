"""Compatibility facade for Script Engine delivery contracts.

The implementation lives in :mod:`script_engine.contract_rules`.  Keeping this
module as the stable import boundary lets the rule implementation be split by
sub-domain without forcing all existing callers to migrate in one change.
"""
from __future__ import annotations

from . import contract_rules as _impl

# Re-export the historical module surface, including private helper names that
# existing repository tests or downstream callers may still import. New code
# should import focused modules as they are introduced rather than growing this
# facade again.
for _name, _value in vars(_impl).items():
    if not _name.startswith("__"):
        globals()[_name] = _value

__all__ = [name for name in vars(_impl) if not name.startswith("__")]
