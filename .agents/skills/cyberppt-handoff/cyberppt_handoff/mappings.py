from __future__ import annotations

FACT_TYPE_TO_EVIDENCE_TYPE = {
    "event": "F", "metric": "F", "definition": "F", "actor": "F", "object": "F",
    "process": "F", "deliverable": "F", "fact": "F",
    "problem": "J", "judgment": "J",
    "goal": "R", "recommendation": "R", "requirement": "R", "approach": "R",
    "constraint": "B", "risk": "B", "condition": "B", "boundary": "B",
}
FACT_TYPE_TO_CLAIM_ROLE = {
    "event": "fact", "metric": "fact", "definition": "fact", "actor": "fact", "object": "fact",
    "process": "fact", "deliverable": "fact", "fact": "fact",
    "problem": "judgment", "judgment": "judgment",
    "goal": "recommendation", "recommendation": "recommendation", "requirement": "recommendation", "approach": "recommendation",
    "constraint": "boundary", "risk": "boundary", "condition": "boundary", "boundary": "boundary",
}
ARGUMENT_DUTY = {
    "background": "premise", "context": "premise", "policy_basis": "premise",
    "problem": "gap", "cause": "driver", "constraint": "boundary", "risk": "boundary", "condition": "boundary",
    "goal": "response", "principle": "support", "approach": "response", "capability": "support", "mechanism": "support",
    "process": "support", "responsibility": "support", "input": "support", "output": "consequence", "deliverable": "consequence",
    "benefit": "consequence", "evidence": "support", "implementation": "response", "conclusion": "consequence",
    "recommendation": "response", "requirement": "constraint", "other": "detail",
}
PAGE_ROLE = {
    "context": "foundation", "background": "foundation", "policy_basis": "foundation", "evidence": "foundation",
    "problem": "gap", "cause": "gap", "risk": "gap",
    "goal": "solution", "principle": "solution", "approach": "solution", "capability": "solution", "mechanism": "solution",
    "process": "solution", "output": "solution", "deliverable": "solution", "benefit": "solution", "conclusion": "solution",
    "responsibility": "scope", "input": "scope", "condition": "assurance", "constraint": "assurance",
    "implementation": "implementation", "recommendation": "implementation", "requirement": "assurance", "other": "solution",
}
VISUAL_INTENT = {
    "architecture": "architecture", "process": "closed_loop_operation", "timeline": "phase",
    "relationship": "actor_relation", "comparison": "judgment_evidence", "matrix": "judgment_evidence",
    "case_evidence": "evidence_support", "metric": "evidence_support", "scenario": "actor_relation",
    "judgment": "judgment_evidence", "summary": "judgment_evidence", "other": "judgment_evidence",
}
IMPORTANCE_TO_PRIORITY = {"high": "P0", "medium": "P1", "low": "P2"}
IMPORTANCE_TO_WEIGHT = {"high": "core", "medium": "supporting", "low": "detail"}
CHAIN_ROLE_TO_DUTY = {
    "premise": "premise", "background": "premise",
    "driver": "driver", "cause": "driver",
    "problem": "gap", "gap": "gap",
    "response": "response", "recommendation": "response", "implementation": "response",
    "condition": "boundary", "constraint": "boundary", "boundary": "boundary",
    "consequence": "consequence", "judgment": "consequence", "conclusion": "consequence",
    "claim": "support", "reason": "support", "instance": "support", "mechanism": "support",
    "support": "support", "evidence": "support",
    "detail": "detail", "other": "detail",
}
