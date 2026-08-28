"""Final Script audit rules."""
from __future__ import annotations

from .common import *

def _onscreen_module_lines(module: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    text = module.get("text")
    if isinstance(text, str) and text.strip():
        lines.append(text.strip())
    for item in module.get("items") or []:
        if isinstance(item, str) and item.strip():
            lines.append(item.strip())
    return lines

def _is_lead_like_evidence_item(value: str) -> bool:
    """Identify a proposition-shaped item that can shadow a forbidden lead.

    Evidence-first pages may still contain complete factual statements. The
    relevant failure mode is narrower: a broad proposition appears only as the
    first item while lighter sibling facts follow at the same rendered level.
    """
    return (
        len(_VISIBLE_CHAR_RE.findall(value)) >= _COMPLETE_PROPOSITION_MIN_CHARS
        and bool(_LEAD_LIKE_EVIDENCE_ITEM_RE.search(value))
    )

def _evidence_first_item_hierarchy_issues(
    slide_id: str, module: dict[str, Any]
) -> list[str]:
    """Reject a hidden module lead placed in the first flat evidence item."""
    items = [
        item.strip()
        for item in module.get("items") or []
        if isinstance(item, str) and item.strip()
    ]
    if len(items) < 2 or not _is_lead_like_evidence_item(items[0]):
        return []
    if all(_is_lead_like_evidence_item(item) for item in items[1:]):
        return []
    heading = str(module.get("heading") or "?").strip()
    return [
        f"{slide_id}: onscreen_composition='evidence_first' module '{heading}' "
        "uses a lead-like first item above lighter peer evidence; rewrite every item "
        "as same-granularity source facts, or use selective_lead when the judgment "
        "must remain inside the module"
    ]

def _is_readable_proposition(line: str) -> bool:
    """Return whether a visible line carries a compact, sentence-like proposition."""
    value = str(line or "").strip()
    if not value or re.search(r"[：:]", value) or not _PROPOSITION_END_RE.search(value):
        return False
    chars = len(_VISIBLE_CHAR_RE.findall(value))
    return _COMPLETE_PROPOSITION_MIN_CHARS <= chars <= _COMPLETE_PROPOSITION_MAX_CHARS

def _onscreen_expression_warnings(
    page: dict[str, Any], slide: dict[str, Any],
) -> list[str]:
    """Advisory checks for a declared sentence-led or mixed visible expression mode."""
    contract = page.get("onscreen_contract")
    if not isinstance(contract, dict) or "expression_mode" not in contract:
        return []
    mode = str(contract.get("expression_mode") or "").strip()
    if mode not in {"sentence_led", "mixed"}:
        return []

    modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    if mode == "sentence_led":
        warnings = []
        for module in modules:
            heading = str(module.get("heading") or "?").strip()
            lines = _onscreen_module_lines(module)
            if not any(_is_readable_proposition(line) for line in lines):
                warnings.append(
                    f"module '{heading}': expression_mode='sentence_led' has no readable proposition; "
                    "add one source-grounded sentence with a subject, predicate and terminal punctuation"
                )
        return warnings

    lines = [line for module in modules for line in _onscreen_module_lines(module)]
    if lines and not any(_is_readable_proposition(line) for line in lines):
        return [
            "expression_mode='mixed' contains no readable proposition; "
            "combine compact evidence phrases with at least one source-grounded sentence"
        ]
    return []

def _authored_bare_label_detail_issues(
    page: dict[str, Any],
    slide: dict[str, Any],
    items: dict[str, dict[str, Any]],
) -> list[str]:
    """Keep source detail and role-bearing payload attached to visible labels."""

    contract = page.get("onscreen_contract")
    contract = contract if isinstance(contract, dict) else {}
    detail_policy = contract.get("detail_policy")
    detail_policy = detail_policy if isinstance(detail_policy, dict) else {}
    label_only_allowed = detail_policy.get("label_only_allowed") is True
    contract_modules = {
        str(module.get("heading") or "").strip(): module
        for module in contract.get("modules") or []
        if isinstance(module, dict) and str(module.get("heading") or "").strip()
    }
    page_evidence_ids = _page_evidence_ids(page)
    issues: list[str] = []
    for module_index, module in enumerate(slide.get("onscreen") or []):
        if not isinstance(module, dict):
            continue
        heading = str(module.get("heading") or "").strip()
        visible_items = [
            str(value).strip()
            for value in module.get("items") or []
            if isinstance(value, str) and value.strip()
        ]
        if not visible_items:
            continue
        module_contract = contract_modules.get(heading, {})
        evidence_ids = {
            str(value)
            for value in module_contract.get("evidence_refs") or []
            if str(value)
        } or page_evidence_ids
        source_statements = [
            _item_text(items[item_id])
            for item_id in evidence_ids
            if item_id in items
        ]
        collapsed = [
            value
            for value in visible_items
            if is_bare_business_label(value)
            and source_has_richer_item_detail(value, source_statements)
        ]
        role_only = functional_group_needs_item_explanations(
            heading,
            visible_items,
            content_load=page.get("content_load"),
            label_only_allowed=label_only_allowed,
        )
        if collapsed or role_only:
            labels = collapsed or [
                value for value in visible_items if is_bare_business_label(value)
            ]
            issues.append(
                "onscreen module {index} '{heading}' collapses source-backed or role-bearing "
                "details into bare labels {labels}; write '标签：来源支持的对象、作用、任务或边界' "
                "without terminal punctuation. Use detail_policy.label_only_allowed=true only "
                "when the approved source intentionally provides a label-only taxonomy".format(
                    index=module_index,
                    heading=heading or "?",
                    labels=labels,
                )
            )
    return issues

def _audit_authored_content_coverage(page: dict[str, Any], slide: dict[str, Any]) -> list[str]:
    route = page.get("content_route")
    if not isinstance(route, dict):
        return []
    visible = re.sub(r"\s+", "", _slide_text(slide))
    slide_id = str(slide.get("id") or page.get("id") or "?")
    issues: list[str] = []
    for signal in route.get("meaning_signals") or []:
        if isinstance(signal, str) and signal.strip() and re.sub(r"\s+", "", signal) not in visible:
            issues.append(
                f"{slide_id}: content_route meaning signal '{signal}' is absent from final copy"
            )
    return issues

def _authored_relationships_issues(page: dict[str, Any], slide: dict[str, Any]) -> list[str]:
    """Every `relationships[]` edge AUTHOR writes must trace to PLAN's approved topology."""
    primary = page.get("primary_relation")
    if not isinstance(primary, dict):
        return []
    scope = {s for s in primary.get("scope") or [] if isinstance(s, str)}
    rel_type = primary.get("type")
    secondary_pairs = {
        (relation.get("from"), relation.get("to"))
        for relation in (page.get("secondary_relations") or [])
        if isinstance(relation, dict)
    }
    hard_topology_allows_scoped_pairs = rel_type in ("sequence", "hierarchy", "matrix", "mixed")

    issues: list[str] = []
    for r_index, relation in enumerate(slide.get("relationships") or []):
        if not isinstance(relation, dict):
            continue
        from_label, to_label = relation.get("from"), relation.get("to")
        pair = (from_label, to_label)
        if pair in secondary_pairs:
            continue
        if hard_topology_allows_scoped_pairs and from_label in scope and to_label in scope:
            continue
        if not scope and not secondary_pairs:
            continue
        issues.append(
            f"relationships[{r_index}] ({from_label} → {to_label}): not declared in plan's "
            "primary_relation topology or secondary_relations; AUTHOR cannot invent a relation "
            "edge PLAN did not sanction"
        )
    return issues

def _audit_authored_source_consumption(
    page: dict[str, Any],
    slide: dict[str, Any],
    items: dict[str, dict[str, Any]],
    foundation: dict[str, Any],
) -> list[str]:
    """Require assigned source facts in full_copy and selected facts onscreen."""
    required_policy = requires_source_consumption(page, foundation)
    contract = page.get("source_consumption")
    definition_issues = _audit_source_consumption_definition(page, items, foundation)
    if not isinstance(contract, dict):
        return definition_issues
    if contract.get("mode") != "strict":
        return definition_issues if required_policy else []
    if not required_policy and foundation.get("source_consumption_policy") == "required":
        return []

    issues = definition_issues
    detail_refs, omitted_refs, _ = _source_consumption_sets(contract)
    required_refs = [
        ref
        for ref in page.get("source_refs") or []
        if isinstance(ref, str) and ref and ref not in detail_refs and ref not in omitted_refs
    ]
    anchors_by_ref = {
        str(anchor.get("source_ref")): anchor
        for anchor in contract.get("full_prose_anchors") or []
        if isinstance(anchor, dict) and isinstance(anchor.get("source_ref"), str)
    }
    full_copy = str(slide.get("full_copy") or "")
    compact_full_copy = re.sub(r"\s+", "", full_copy)

    for ref in required_refs:
        item = items.get(ref)
        if not isinstance(item, dict):
            continue
        anchor_contract = anchors_by_ref.get(ref)
        if anchor_contract:
            anchors = [
                str(value).strip()
                for value in anchor_contract.get("anchors") or []
                if str(value).strip()
            ]
            hits = [
                anchor for anchor in anchors
                if re.sub(r"\s+", "", anchor) in compact_full_copy
            ]
            minimum_hits = anchor_contract.get("minimum_hits", len(anchors))
            if isinstance(minimum_hits, int) and len(hits) < minimum_hits:
                missing = [anchor for anchor in anchors if anchor not in hits]
                if not hits:
                    issues.append(
                        f"FULL_COPY_SOURCE_REF_MISSING: {ref} has no declared source anchor in full_copy"
                    )
                issues.append(
                    f"FULL_COPY_SOURCE_ANCHOR_MISSING: source_consumption full_copy gap for {ref}: anchor hits "
                    f"{len(hits)}/{minimum_hits}; missing anchors {missing}; "
                    f"source statement: {_item_text(item)}"
                )
            if required_policy:
                source_surface = " ".join(_source_surface_values(item))
                protected_numbers = set(
                    re.findall(
                        r"\d+(?:\.\d+)?(?:年\d{1,2}月\d{1,2}日|年|月|日|%|％|万|亿|项|级)?",
                        source_surface,
                    )
                )
                for number_ref in item.get("number_refs") or []:
                    number = items.get(number_ref)
                    if not isinstance(number, dict):
                        continue
                    raw_value = number.get("value")
                    value = "" if raw_value is None else str(raw_value).strip()
                    unit = str(number.get("unit") or "").strip()
                    if value:
                        protected_numbers.add(f"{value}{unit}")
                        protected_numbers.add(value)
                missing_numbers = sorted(
                    value for value in protected_numbers
                    if value and re.sub(r"\s+", "", value) not in compact_full_copy
                )
                if missing_numbers:
                    issues.append(
                        f"FULL_COPY_NUMBER_OR_DATE_LOST: {ref} lost protected values {missing_numbers}"
                    )

                missing_conditions = [
                    str(value).strip()
                    for value in item.get("conditions") or []
                    if str(value).strip()
                    and re.sub(r"\s+", "", str(value)) not in compact_full_copy
                ]
                if missing_conditions:
                    issues.append(
                        f"FULL_COPY_CONDITION_LOST: {ref} lost source conditions {missing_conditions}"
                    )

                missing_entities = []
                for entity_ref in item.get("entity_refs") or []:
                    entity = items.get(entity_ref)
                    name = str((entity or {}).get("name") or "").strip()
                    if name and re.sub(r"\s+", "", name) not in compact_full_copy:
                        missing_entities.append(name)
                if missing_entities:
                    issues.append(
                        f"FULL_COPY_RESPONSIBILITY_LOST: {ref} lost source actors {missing_entities}"
                    )

                status = str(item.get("status") or "").strip()
                if status and re.sub(r"\s+", "", status) not in compact_full_copy:
                    issues.append(
                        f"FULL_COPY_STATUS_STRENGTH_LOST: {ref} lost source status '{status}'"
                    )
            continue

        if required_policy:
            issues.append(
                f"FULL_COPY_SOURCE_ANCHOR_MISSING: {ref} has no strict full_prose_anchors contract"
            )
            continue

        statements = [_item_text(item)]
        statements.extend(
            str(unit.get("text") or "")
            for unit in item.get("semantic_units") or []
            if isinstance(unit, dict) and str(unit.get("text") or "").strip()
        )
        overlap = max(
            (_source_statement_overlap(statement, full_copy) for statement in statements if statement.strip()),
            default=0.0,
        )
        if overlap < 0.08:
            issues.append(
                f"source_consumption full_copy gap for {ref}: source-specific content is absent "
                f"(overlap={overlap:.3f}); source statement: {_item_text(item)}"
            )

    if required_policy:
        _, _, onscreen_refs = _source_consumption_sets(contract)
        expected_modules = [
            module
            for module in (page.get("onscreen_contract") or {}).get("modules") or []
            if isinstance(module, dict)
            and onscreen_refs.intersection(
                ref for ref in module.get("evidence_refs") or [] if isinstance(ref, str)
            )
        ]
        actual_by_heading = {
            str(module.get("heading") or "").strip(): module
            for module in slide.get("onscreen") or []
            if isinstance(module, dict)
        }
        for module in expected_modules:
            heading = str(module.get("heading") or "").strip()
            actual = actual_by_heading.get(heading)
            if not isinstance(actual, dict) or not _onscreen_module_lines(actual):
                issues.append(
                    "ONSCREEN_SOURCE_REF_MISSING: representative source module "
                    f"'{heading}' is absent or empty"
                )
    return issues

def _audit_authored_onscreen_composition(
    page: dict[str, Any], slide: dict[str, Any]
) -> list[str]:
    """Check that module lead text follows the approved page composition policy."""
    composition = page.get("onscreen_composition")
    if not isinstance(composition, dict):
        return []

    issues = _audit_onscreen_composition_definition(page)
    mode = composition.get("mode")
    if mode not in _ONSCREEN_COMPOSITION_MODES:
        return issues

    slide_id = str(slide.get("id") or page.get("id") or "?")
    modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    lead_modules = [
        module for module in modules
        if isinstance(module.get("text"), str) and module["text"].strip()
    ]
    if mode == "evidence_first":
        for module in lead_modules:
            heading = str(module.get("heading") or "?").strip()
            issues.append(
                f"{slide_id}: onscreen_composition='evidence_first' forbids module lead text in "
                f"'{heading}'; move the judgment to core_message and retain source facts as evidence items"
            )
        for module in modules:
            issues.extend(_evidence_first_item_hierarchy_issues(slide_id, module))
    else:
        lead_budget = composition.get("lead_budget")
        if isinstance(lead_budget, int) and not isinstance(lead_budget, bool) and len(lead_modules) > lead_budget:
            issues.append(
                f"{slide_id}: onscreen_composition='selective_lead' permits at most {lead_budget} "
                f"module lead(s), got {len(lead_modules)}"
            )
    return issues

def _audit_authored_onscreen_contract(
    page: dict[str, Any], slide: dict[str, Any], items: dict[str, dict[str, Any]]
) -> list[str]:
    """Check that AUTHOR consumed the declared module-level semantic contract.

    This intentionally does not infer a module's meaning from keywords on pages that
    have no contract.  The plan author declares the page's axis, source scope and role
    vocabulary; the final audit then checks the visible module payload against it.
    """
    contract = page.get("onscreen_contract")
    if not isinstance(contract, dict):
        return []

    issues = _onscreen_contract_definition_issues(page, contract, items)
    expected_modules = [module for module in contract.get("modules") or [] if isinstance(module, dict)]
    actual_modules = [module for module in slide.get("onscreen") or [] if isinstance(module, dict)]
    expected_headings = [str(module.get("heading") or "").strip() for module in expected_modules]
    actual_headings = [str(module.get("heading") or "").strip() for module in actual_modules]
    slide_id = str(slide.get("id") or page.get("id") or "?")

    if actual_headings != expected_headings:
        issues.append(
            f"{slide_id}: onscreen module headings do not match the approved contract; "
            f"expected {expected_headings}, got {actual_headings}"
        )

    modules_by_heading = {
        str(module.get("heading") or "").strip(): module
        for module in actual_modules
        if str(module.get("heading") or "").strip()
    }
    contract_headings = set(expected_headings)
    policy = contract.get("detail_policy") or {}
    if not isinstance(policy, dict):
        policy = {}
    role_markers = policy.get("role_markers") or {}
    if not isinstance(role_markers, dict):
        role_markers = {}
    allowed_roles = {str(role) for role in policy.get("allowed_roles") or []}
    forbidden_roles = {str(role) for role in policy.get("forbidden_roles") or []}
    forbidden_patterns = [pattern for pattern in policy.get("forbidden_patterns") or [] if isinstance(pattern, str)]

    for expected in expected_modules:
        heading = str(expected.get("heading") or "").strip()
        module = modules_by_heading.get(heading)
        if module is None:
            continue
        lines = _onscreen_module_lines(module)
        body = " ".join(lines)
        for signal in expected.get("required_signals") or []:
            if isinstance(signal, str) and signal and signal not in body:
                issues.append(
                    f"ONSCREEN_REQUIRED_SIGNAL_MISSING: {slide_id} module '{heading}': "
                    f"required signal '{signal}' is missing"
                )
        for signal in expected.get("forbidden_signals") or []:
            if isinstance(signal, str) and signal and signal in body:
                issues.append(f"{slide_id} module '{heading}': forbidden cross-scope signal '{signal}' is present")

        if contract.get("scope_mode") == "exclusive":
            for other_heading in contract_headings - {heading}:
                if other_heading and other_heading in body:
                    issues.append(
                        f"{slide_id} module '{heading}': exclusive scope contains peer module heading '{other_heading}'"
                    )

        for line in lines:
            matched_roles: set[str] = set()
            for role, patterns in role_markers.items():
                if not isinstance(role, str) or not isinstance(patterns, list):
                    continue
                for pattern in patterns:
                    if not isinstance(pattern, str) or not pattern:
                        continue
                    try:
                        if re.search(pattern, line):
                            matched_roles.add(role)
                            break
                    except re.error:
                        # The definition audit reports the malformed pattern.  Avoid
                        # duplicating that same error for every authored line.
                        continue
            disallowed = matched_roles.intersection(forbidden_roles)
            if allowed_roles:
                disallowed.update(matched_roles - allowed_roles)
            if disallowed:
                issues.append(
                    f"{slide_id} module '{heading}': detail line '{line}' uses disallowed role(s) "
                    f"{sorted(disallowed)}"
                )
            for pattern in forbidden_patterns:
                try:
                    matched = re.search(pattern, line)
                except re.error:
                    matched = None
                if matched:
                    issues.append(
                        f"{slide_id} module '{heading}': detail line '{line}' matches forbidden pattern '{pattern}'"
                    )
    return issues

def _audit_authored_unit_consumption(
    page: dict[str, Any], slide: dict[str, Any], items: dict[str, dict[str, Any]], foundation: dict[str, Any]
) -> list[str]:
    """Check that AUTHOR actually expressed every semantic unit PLAN assigned a disposition to.

    Record-level source_consumption only proves one anchor from a record survived into
    full_copy; a record with several semantic units can still lose most of them. This is
    the per-unit follow-through, and only fires when PLAN declared ``unit_dispositions``
    for the page (see ``_audit_unit_consumption_definition`` for the PLAN-side shape
    validation). Pages without a declaration are unaffected.
    """
    if not requires_source_consumption(page, foundation):
        return []
    contract = page.get("source_consumption")
    if not isinstance(contract, dict):
        return []
    dispositions = contract.get("unit_dispositions")
    if not isinstance(dispositions, list) or not dispositions:
        return []

    full_copy = str(slide.get("full_copy") or "")
    onscreen_contract = page.get("onscreen_contract") or {}
    modules_by_ref: dict[str, list[str]] = {}
    if isinstance(onscreen_contract, dict):
        for module in onscreen_contract.get("modules") or []:
            if not isinstance(module, dict):
                continue
            heading = str(module.get("heading") or "").strip()
            for ref in module.get("evidence_refs") or []:
                if isinstance(ref, str) and ref:
                    modules_by_ref.setdefault(ref, []).append(heading)
    actual_by_heading = {
        str(module.get("heading") or "").strip(): module
        for module in slide.get("onscreen") or []
        if isinstance(module, dict)
    }

    issues: list[str] = []
    for entry in dispositions:
        if not isinstance(entry, dict):
            continue
        ref = str(entry.get("source_ref") or "").strip()
        unit_id = str(entry.get("unit_id") or "").strip()
        disposition = entry.get("disposition")
        item = items.get(ref)
        if not ref or not unit_id or not isinstance(item, dict):
            continue
        unit = next(
            (
                candidate
                for candidate_index, candidate in enumerate(item.get("semantic_units") or [])
                if isinstance(candidate, dict)
                and (str(candidate.get("id") or "").strip() or f"{ref}#{candidate_index}") == unit_id
            ),
            None,
        )
        if not isinstance(unit, dict):
            continue
        unit_text = str(unit.get("text") or "").strip()
        if not unit_text:
            continue

        if disposition == "full_copy":
            overlap = _source_statement_overlap(unit_text, full_copy)
            if overlap < 0.08:
                issues.append(
                    f"FULL_COPY_SEMANTIC_UNIT_GAP: {ref}#{unit_id} is assigned full_copy disposition "
                    f"but is absent from full_copy (overlap={overlap:.3f}); unit text: {unit_text}"
                )
        elif disposition == "onscreen":
            headings = modules_by_ref.get(ref) or []
            module_text = " ".join(
                " ".join(_onscreen_module_lines(actual_by_heading[heading]))
                for heading in headings
                if heading in actual_by_heading
            )
            overlap = _source_statement_overlap(unit_text, module_text) if module_text else 0.0
            if overlap < 0.08:
                issues.append(
                    f"ONSCREEN_SOURCE_DETAIL_INSUFFICIENT: {ref}#{unit_id} is assigned onscreen disposition "
                    f"but is absent from the mapped onscreen module(s); unit text: {unit_text}"
                )
    return issues

def _slide_text(slide: dict[str, Any]) -> str:
    parts: list[str] = []
    for key in ("title", "subtitle", "mission", "core_message", "full_copy", "visual_thesis", "speaker_notes"):
        value = slide.get(key)
        if isinstance(value, str):
            parts.append(value)
    argument = slide.get("argument") or {}
    if isinstance(argument, dict):
        if isinstance(argument.get("pattern"), str):
            parts.append(argument["pattern"])
        parts.extend(x for x in (argument.get("chain") or []) if isinstance(x, str))
    for module in slide.get("onscreen") or []:
        if not isinstance(module, dict):
            continue
        for key in ("heading", "text"):
            value = module.get(key)
            if isinstance(value, str):
                parts.append(value)
        parts.extend(x for x in (module.get("items") or []) if isinstance(x, str))
    for relation in slide.get("relationships") or []:
        if not isinstance(relation, dict):
            continue
        for key in ("from", "to", "relation"):
            value = relation.get(key)
            if isinstance(value, str):
                parts.append(value)
    return " ".join(parts)

def _source_text_for_refs(source_refs: list[Any], foundation: dict[str, Any]) -> str:
    refs = {x for x in source_refs if isinstance(x, str)}
    parts: list[str] = []
    for key in CITABLE_KEYS:
        for item in foundation.get(key) or []:
            if not isinstance(item, dict):
                continue
            if refs.intersection(x for x in (item.get("source_refs") or []) if isinstance(x, str)):
                parts.append(_item_text(item))
    return " ".join(parts)

def _normalize_source_chapter_title(title: str) -> str:
    return CHAPTER_PREFIX_RE.sub("", title).strip(" 　")

def audit_final_script(final_script: dict[str, Any], plan: dict[str, Any], foundation: dict[str, Any]) -> tuple[list[str], list[str]]:
    issues: list[str] = audit_final_internal_expert_voice(final_script, plan)
    warnings: list[str] = []
    items = foundation_items_by_id(foundation)
    pages = {p.get("id"): p for p in (plan.get("pages") or []) if isinstance(p, dict) and isinstance(p.get("id"), str)}
    chapters = {c.get("id"): c for c in (plan.get("chapters") or []) if isinstance(c, dict) and isinstance(c.get("id"), str)}
    structure = {x.get("id"): x for x in (foundation.get("source_structure") or []) if isinstance(x, dict) and isinstance(x.get("id"), str)}
    audience_scope = plan.get("audience_scope", "unspecified")
    preserve_structure = plan.get("source_structure_mode") == "preserve"
    strict_evidence_fit = plan.get("evidence_fit_review_mode") == "strict"
    if not strict_evidence_fit:
        issues.append(
            "PLAN evidence-fit gate: evidence_fit_review_mode: strict is required before AUTHOR"
        )

    for index, slide in enumerate(final_script.get("slides") or []):
        if not isinstance(slide, dict):
            continue
        slide_id = slide.get("id") or f"#{index}"
        page = pages.get(slide_id)
        if page is None:
            warnings.append(f"slides.{index} ({slide_id}): no matching deck-plan page; semantic inheritance cannot be audited")
            continue
        final_text = _slide_text(slide)
        plan_text = _page_text(page)
        evidence_ids = _page_evidence_ids(page)
        evidence = _support_items(sorted(evidence_ids), items)

        for review_issue in _audit_evidence_fit_reviews(page, items, strict=strict_evidence_fit):
            issues.append(f"slides.{index} ({slide_id}): PLAN evidence-fit gate: {review_issue}")

        plan_model = str((page.get("analysis_basis") or {}).get("model") or "").lower()
        plan_logic = str(page.get("logic") or "")
        plan_is_classification = any(token in plan_model for token in ("classification", "taxonomy", "typology")) or "分类" in plan_logic
        plan_allows_progression = bool(PROGRESSION_RE.search(plan_text) or any(token in plan_model for token in ("progression", "maturity")))
        if plan_is_classification and not plan_allows_progression and PROGRESSION_RE.search(final_text):
            issues.append(f"slides.{index} ({slide_id}): AUTHOR upgraded a classification/taxonomy plan into a progression chain")

        if _has_optionality(evidence) and not _preserves_optionality(final_text):
            issues.append(f"slides.{index} ({slide_id}): final script lost source optionality; it must preserve independent choice and progressive deepening")

        group_issue = _group_strength_issue(str(slide.get("core_message") or ""), evidence)
        if group_issue:
            issues.append(f"slides.{index} ({slide_id}): {group_issue}")

        internal = [item for item in evidence if effective_visibility(item) == "internal_only"]
        if audience_scope == "external" and internal:
            exposed: list[str] = []
            for item in internal:
                item_text = _item_text(item)
                values = [str(item.get("value") or "")]
                for match in re.findall(r"\d+(?:\.\d+)?%?(?:至|-|—)\d+(?:\.\d+)?%?|\d+(?:\.\d+)?%", item_text):
                    values.append(match)
                normalized_final = final_text.replace("至", "-").replace("—", "-")
                if any(value and value.replace("至", "-").replace("—", "-") in normalized_final for value in values):
                    exposed.append(str(item.get("id") or "?"))
            if exposed:
                issues.append(f"slides.{index} ({slide_id}): external final script exposes internal-only evidence {sorted(set(exposed))}")

        if GAP_RE.search(final_text):
            source_text = _source_text_for_refs(page.get("source_refs") or [], foundation)
            if not GAP_RE.search(plan_text) and not GAP_RE.search(source_text):
                issues.append(f"slides.{index} ({slide_id}): final script introduces a current-vs-target gap judgment without a source or plan baseline")

        for composition_issue in _audit_authored_onscreen_composition(page, slide):
            issues.append(f"slides.{index} ({slide_id}): {composition_issue}")
        for contract_issue in _audit_authored_onscreen_contract(page, slide, items):
            issues.append(f"slides.{index} ({slide_id}): {contract_issue}")
        for relation_issue in _authored_relationships_issues(page, slide):
            issues.append(f"slides.{index} ({slide_id}): {relation_issue}")
        for consumption_issue in _audit_authored_source_consumption(
            page, slide, items, foundation
        ):
            issues.append(f"slides.{index} ({slide_id}): {consumption_issue}")
        for unit_issue in _audit_authored_unit_consumption(page, slide, items, foundation):
            issues.append(f"slides.{index} ({slide_id}): {unit_issue}")
        for coverage_issue in _audit_authored_content_coverage(page, slide):
            issues.append(f"slides.{index} ({slide_id}): {coverage_issue}")
        for readiness_issue in audit_authored_stage02_readiness(page, slide):
            issues.append(f"slides.{index} ({slide_id}): {readiness_issue}")
        for detail_issue in _authored_bare_label_detail_issues(page, slide, items):
            issues.append(
                f"slides.{index} ({slide_id}): ONSCREEN_SOURCE_DETAIL_COLLAPSED_TO_LABEL: "
                f"{detail_issue}"
            )
        warnings.extend(
            f"slides.{index} ({slide_id}): {warning}"
            for warning in _onscreen_expression_warnings(page, slide)
        )

        if preserve_structure and slide.get("page_type") == "chapter":
            chapter_id = slide.get("chapter_id")
            chapter = chapters.get(chapter_id) if isinstance(chapter_id, str) else None
            source_ids = chapter.get("source_chapter_ids") if isinstance(chapter, dict) else None
            if source_ids and len(source_ids) == 1:
                node = structure.get(source_ids[0])
                if isinstance(node, dict) and isinstance(node.get("title"), str):
                    expected = _normalize_source_chapter_title(node["title"])
                    actual = str(slide.get("title") or "").strip()
                    if actual and expected and actual != expected:
                        issues.append(f"slides.{index} ({slide_id}): source_structure_mode='preserve' requires chapter title '{expected}', got '{actual}'")

    return issues, warnings

__all__ = ['_onscreen_module_lines', '_is_lead_like_evidence_item', '_evidence_first_item_hierarchy_issues', '_is_readable_proposition', '_onscreen_expression_warnings', '_authored_bare_label_detail_issues', '_audit_authored_content_coverage', '_authored_relationships_issues', '_audit_authored_source_consumption', '_audit_authored_unit_consumption', '_audit_authored_onscreen_composition', '_audit_authored_onscreen_contract', '_slide_text', '_source_text_for_refs', '_normalize_source_chapter_title', 'audit_final_script']
