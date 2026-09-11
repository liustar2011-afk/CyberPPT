"""Compatibility facade for stage-specific deterministic analysis audits."""
from __future__ import annotations

from .analysis_audits.common import *
from .analysis_audits.foundation import *
from .analysis_audits.deck_plan import *
from .analysis_audits.final_script_runtime import *
from .analysis_audits.source_index import *

# Phase 4 convergence: keep all historical helper re-exports above, but make the
# public Final Script audit name resolve to the single semantic-contract entry
# exposed by ``script_engine.analysis_audits``. Callers that explicitly need the
# frozen raw implementation can import ``analysis_audits.final_script_runtime``.
from .analysis_audits import audit_final_script as audit_final_script
