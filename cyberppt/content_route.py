"""Internal-report content routing for source-grounded page authoring.

``page_type`` classifies structural pages and ``argument_role`` controls claim
authority.  This module deliberately adds neither a new page taxonomy nor a
second evidence model.  It gives authors an optional, reviewable indication of
how a content page's already-approved facts and relations should be arranged.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


CONTENT_ROUTES = frozenset({"state", "diagnosis", "system", "action", "source_native"})
CONTENT_ROUTE_FACETS = frozenset(
    {
        "background",
        "current",
        "progress",
        "comparison",
        "risk",
        "boundary",
        "coordination",
        "next_step",
    }
)
CONTENT_ROUTE_CONFIDENCE = frozenset({"high", "medium", "low"})
STRUCTURAL_PAGE_ROLES = frozenset({"cover", "contents", "chapter", "closing"})
PAGE_ROLE_ALIASES = {
    "agenda": "contents",
    "ending": "closing",
}
MEANING_FACETS = frozenset({"risk", "coordination", "next_step"})

_ARGUMENT_ROLE_ROUTE = {
    "foundation": "state",
    "change": "state",
    "gap": "diagnosis",
    "necessity": "diagnosis",
    "positioning": "system",
    "solution": "system",
    "scope": "system",
    "assurance": "system",
    "implementation": "action",
    "decision": "action",
}
_LOGIC_ROLE_ROUTE = {
    "context": "state",
    "support": "state",
    "need": "diagnosis",
    "constraint": "diagnosis",
    "consequence": "diagnosis",
    "boundary": "system",
    "requirement": "action",
}


@dataclass(frozen=True)
class ContentRouteDecision:
    """A non-authoritative authoring hint resolved from an approved page."""

    primary: str
    facets: tuple[str, ...] = ()
    confidence: str = "low"
    basis: tuple[str, ...] = ()
    rationale: str = ""
    source: str = "fallback"


def normalize_page_role(value: object) -> str:
    """Return the repository's canonical page-role vocabulary."""

    role = str(value or "").strip()
    return PAGE_ROLE_ALIASES.get(role, role)


def is_structural_page(page: Mapping[str, object]) -> bool:
    """Return whether a page is a structural page that must not use a route."""

    kind = normalize_page_role(page.get("page_type") or page.get("page_role"))
    return kind in STRUCTURAL_PAGE_ROLES


def _strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(dict.fromkeys(str(item).strip() for item in value if str(item).strip()))


def _declared_route(page: Mapping[str, object]) -> ContentRouteDecision | None:
    route = page.get("content_route")
    if not isinstance(route, Mapping):
        return None
    primary = str(route.get("primary") or "").strip()
    if primary not in CONTENT_ROUTES:
        return None
    facets = tuple(facet for facet in _strings(route.get("facets")) if facet in CONTENT_ROUTE_FACETS)
    confidence = str(route.get("confidence") or "high").strip()
    if confidence not in CONTENT_ROUTE_CONFIDENCE:
        confidence = "high"
    return ContentRouteDecision(
        primary=primary,
        facets=facets,
        confidence=confidence,
        basis=_strings(route.get("basis")),
        rationale=str(route.get("rationale") or "").strip(),
        source="author",
    )


def infer_content_route(page: Mapping[str, object]) -> ContentRouteDecision:
    """Infer only from declared semantic fields; never from presentation wording.

    A missing or mixed signal intentionally resolves to ``source_native``.  The
    fallback protects special source structures from being forced into a generic
    consulting-report pattern.
    """

    if is_structural_page(page):
        return ContentRouteDecision(
            primary="source_native",
            rationale="结构页不适用内容路由。",
            source="structural",
        )

    argument_role = str(page.get("argument_role") or "").strip()
    route = _ARGUMENT_ROLE_ROUTE.get(argument_role)
    if route:
        return ContentRouteDecision(
            primary=route,
            confidence="high",
            basis=("argument_role",),
            rationale=f"argument_role={argument_role}",
            source="argument_role",
        )

    contract = page.get("page_logic_contract")
    nodes = contract.get("nodes") if isinstance(contract, Mapping) else None
    roles = {
        str(node.get("role") or "").strip()
        for node in nodes or []
        if isinstance(node, Mapping) and str(node.get("role") or "").strip()
    }
    candidates = {_LOGIC_ROLE_ROUTE[role] for role in roles if role in _LOGIC_ROLE_ROUTE}
    if len(candidates) == 1:
        only = next(iter(candidates))
        return ContentRouteDecision(
            primary=only,
            confidence="medium",
            basis=("page_logic_contract.nodes",),
            rationale=f"页面逻辑节点角色均指向 {only}。",
            source="page_logic_contract",
        )

    return ContentRouteDecision(
        primary="source_native",
        confidence="low",
        rationale="页面证据未形成唯一内容路由；保留源材料原有组织方式。",
        source="fallback",
    )


def resolve_content_route(page: Mapping[str, object]) -> ContentRouteDecision:
    """Resolve an explicit author choice before any deterministic inference."""

    return _declared_route(page) or infer_content_route(page)


def audit_content_route(page: Mapping[str, object]) -> list[str]:
    """Validate a declared route and reject only clear evidence conflicts."""

    raw = page.get("content_route")
    if raw is None:
        return []
    if is_structural_page(page):
        return ["content_route applies only to content pages, not structural pages"]
    if not isinstance(raw, Mapping):
        return ["content_route must be an object"]

    issues: list[str] = []
    primary = str(raw.get("primary") or "").strip()
    if primary not in CONTENT_ROUTES:
        issues.append("content_route.primary must be one of: state, diagnosis, system, action, source_native")
    raw_facets = raw.get("facets")
    facets = _strings(raw_facets)
    invalid_facets = sorted(set(facets) - CONTENT_ROUTE_FACETS)
    if invalid_facets:
        issues.append(f"content_route.facets contains unsupported value(s) {invalid_facets}")
    raw_facet_values = (
        [str(item).strip() for item in raw_facets if str(item).strip()]
        if isinstance(raw_facets, (list, tuple))
        else []
    )
    if len(raw_facet_values) != len(set(raw_facet_values)):
        issues.append("content_route.facets must not repeat a value")
    confidence = raw.get("confidence")
    if confidence is not None and str(confidence).strip() not in CONTENT_ROUTE_CONFIDENCE:
        issues.append("content_route.confidence must be one of: high, medium, low")
    basis = _strings(raw.get("basis"))
    if not basis:
        issues.append("content_route.basis must contain at least one declared evidence field")
    if not str(raw.get("rationale") or "").strip():
        issues.append("content_route.rationale is required for an explicit route")
    meaning_signals = _strings(raw.get("meaning_signals"))
    raw_meaning_signals = raw.get("meaning_signals")
    raw_meaning_values = (
        [str(item).strip() for item in raw_meaning_signals if str(item).strip()]
        if isinstance(raw_meaning_signals, (list, tuple))
        else []
    )
    if len(raw_meaning_values) != len(set(raw_meaning_values)):
        issues.append("content_route.meaning_signals must not repeat a value")
    if set(facets).intersection(MEANING_FACETS) and not meaning_signals:
        issues.append(
            "content_route.meaning_signals is required when facets include risk, coordination, or next_step"
        )

    inferred = infer_content_route(page)
    if (
        primary in CONTENT_ROUTES - {"source_native"}
        and inferred.primary in CONTENT_ROUTES - {"source_native"}
        and inferred.confidence in {"high", "medium"}
        and (
            inferred.confidence == "high"
            or str(page.get("page_logic_contract_mode") or "") == "required"
        )
        and primary != inferred.primary
    ):
        issues.append(
            "content_route.primary conflicts with the page's declared semantic route "
            f"({inferred.primary} expected)"
        )
    return issues


def render_content_route(page: Mapping[str, object]) -> str:
    """Render the resolved route for author/reviewer-facing diagnostics."""

    decision = resolve_content_route(page)
    facets = f"｜侧面 {'、'.join(decision.facets)}" if decision.facets else ""
    basis = f"｜依据 {'、'.join(decision.basis)}" if decision.basis else ""
    rationale = f"｜{decision.rationale}" if decision.rationale else ""
    return (
        f"- 内容路由：{decision.primary}｜{decision.source}/{decision.confidence}"
        f"{facets}{basis}{rationale}"
    )


__all__ = [
    "CONTENT_ROUTE_CONFIDENCE",
    "CONTENT_ROUTE_FACETS",
    "CONTENT_ROUTES",
    "ContentRouteDecision",
    "audit_content_route",
    "infer_content_route",
    "is_structural_page",
    "render_content_route",
    "resolve_content_route",
]
