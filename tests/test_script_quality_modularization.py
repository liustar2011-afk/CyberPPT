from __future__ import annotations

import ast
from dataclasses import asdict
import importlib
import json
from pathlib import Path
import unittest


COMPAT_SYMBOLS = (
    "ScriptPage", "ScriptDocument", "ScriptQualityIssue",
    "PAGE_HEADING_RE",
    "parse_script_markdown", "parse_script_path",
    "audit_script_quality", "audit_final_manuscript_form",
    "assert_imagegen_onscreen_readiness", "build_communication_review",
    "ONSCREEN_SEMANTIC_COVERAGE_TARGET",
    "extract_speaker_notes", "meaningful_char_count",
    "onscreen_effective_char_target", "onscreen_semantic_coverage",
    "onscreen_story_roles", "parse_selection_notes",
    "selection_notes_are_structured", "script_retry_directive",
    "text_similarity", "audience_facing_group_label",
    "strip_authoring_group_marker", "resolve_judgment_mode",
    "is_final_script_path", "_prohibited_contrast_hits",
    "_prohibited_colloquial_hits", "_unlabeled_onscreen_bullets",
    "_mechanical_evidence_bullets", "_compound_module_heading_hits",
    "_module_heading_colon_hits", "_negative_foreground_issues",
    "_generic_onscreen_relation_hits",
    "_mechanical_onscreen_label_pattern_hits",
    "_onscreen_detail_phrase_overages", "_onscreen_layout_meta_hits",
    "_onscreen_parent_child_role_mismatches",
    "_onscreen_subordinate_fragments", "_onscreen_false_parallel_semantics",
    "_onscreen_parallel_structure_issues", "_necessity_page_closure_issues",
    "_onscreen_flow_language_issues", "_formulaic_transition_issues",
    "_speaker_placeholder_hits", "_issue", "_presentation_issues",
    "_prohibited_contrast_issues", "_prose_issues",
    "_source_consumption_issues", "_full_prose_source_coverage_issues",
    "_full_prose_paragraph_boundary_issues", "_polarity_dropped_terms",
    "_page_content_unit_coverage_issues", "_model_slot_coverage_issues",
    "_onscreen_module_provenance_issues",
    "_visual_structure_judgment_issues",
    "_page_relationship_continuity_issues",
    "_MODULE_CEILING_FALLBACK", "_RULES_YAML_PATH",
    "_load_module_ceiling",
)

LEGACY_FACT_SYMBOLS = frozenset(
    """
    ANTI_PATTERN_TERMS BUSINESS_LANE_LABEL_RE COMPLETED_TERMS COMPOSITION_PRIMITIVES
    CONDITIONAL_STATUSES CONSTRAINT_ARGUMENT_ROLES CONSTRAINT_THEME_TERMS COUNT_WORDS
    DEFENSIVE_BOUNDARY_COACHING_RE FINAL_BATCH_HEADING_RE FINAL_BATCH_META_RE
    FINAL_DRAFT_HEADING_RE FINAL_DRAFT_STATUS_RE FINAL_PENDING_AUDIT_RE
    FORMULAIC_TRANSITION_TERMS GENERIC_ONSCREEN_DETAIL_LABELS
    GENERIC_ONSCREEN_GROUP_LABELS GENERIC_ONSCREEN_RELATION_RE IMPLEMENTATION_TERMS
    LAYER_LIKE_INTENT_TYPES LAYER_SIGNALS LOCKED_JUDGMENT_ROLES LOOP_SIGNALS
    MATRIX_SIGNALS MECHANISM_LANE_LABEL_RE MODULE_CEILING MODULE_RE
    NUMBERED_EVIDENCE_BULLET_RE NUMBERED_ORDER_SIGNAL_RE ONSCREEN_BACKEND_META_PHRASES
    ONSCREEN_CONSTRAINT_DETAIL_TERMS ONSCREEN_CONSTRAINT_MODULE_TERMS
    ONSCREEN_DETAIL_PHRASE_ERROR_CHARS ONSCREEN_DETAIL_PHRASE_WARNING_CHARS
    ONSCREEN_EFFECTIVE_CHARS_MAX ONSCREEN_EFFECTIVE_CHARS_MIN ONSCREEN_FLOW_ACTION_TERMS
    ONSCREEN_FLOW_HEADING_MAX_CHARS ONSCREEN_JUDGMENT_MODES ONSCREEN_LAYOUT_META_PATTERNS
    ONSCREEN_PROSE_DENSITY_RATIO ONSCREEN_RELATION_META_LABELS
    ONSCREEN_SEMANTIC_COVERAGE_ERROR_FLOOR ONSCREEN_SEMANTIC_COVERAGE_TARGET
    ONSCREEN_SOURCE_ERASURE_PHRASES ONSCREEN_SOURCE_SPECIFICITY_ERROR_FLOOR
    ONSCREEN_STORY_EXPLANATION_SIGNALS ONSCREEN_STORY_IMPLICATION_SIGNALS
    ONSCREEN_STORY_RELATION_SIGNALS ORDER_SIGNALS PAGE_HEADING_RE PATH_LIKE_INTENT_TYPES
    PageRelationshipSummary Path SCOPE_TERMS SELECTION_NOTE_REQUIRED_MARKERS
    SEMANTIC_ONLY_JUDGMENT_ROLES SEMANTIC_STRUCTURE_SIGNALS SPATIAL_SIGNALS
    SPEAKER_HOST_META_RE SPEAKER_NOTES_MIN_CHARS SPEAKER_PLACEHOLDER_RE SPEAKER_SLIDE_META_RE
    STRATEGY_ORDER STYLE_ONLY_TERMS ScriptDocument ScriptPage ScriptQualityIssue
    VISIBLE_CERTAINTY_TERMS VISIBLE_JUDGMENT_MIN_SIMILARITY
    VISIBLE_JUDGMENT_TERMINAL_PUNCTUATION VISUAL_STRUCTURE_LAYOUT_RECIPE_RES
    VISUAL_STRUCTURE_MULTIPLE_PRIMARY_RE _ACTOR_DUTY_LABEL_RE _ACTOR_LABEL_RE
    _ACTOR_PARENT_RE _ANALYTICAL_VOICE_PATTERNS _BOUNDARY_ASIDE_PATTERNS
    _COMPOUND_HEADING_HEADS _COMPOUND_HEADING_INCOMPATIBLE_HEADS
    _COMPOUND_PARENT_DOMAINS _CONDITIONAL_RISK_PHRASES _DIRECT_BOUNDARY_ARGUMENT_ROLES
    _DIRECT_BOUNDARY_TOPIC_TERMS _MODULE_CEILING_FALLBACK _NEGATIVE_FOREGROUND_TERMS
    _NON_ACTOR_PARENT_RE _OBJECT_TAXONOMY_PARENT_RE _ONSCREEN_MARKDOWN_PATTERNS
    _ONSCREEN_RELATION_META_RE _PROHIBITED_COLLOQUIAL_PATTERNS
    _PROHIBITED_CONTRAST_PATTERNS _RELATION_ACTION_SIGNALS _RELATION_VISIBILITY_SIGNALS
    _RULES_YAML_PATH _SEMANTIC_LINE_PATTERNS _SUBORDINATE_DETAIL_RE
    _TAXONOMY_CROSSCUT_LABEL_RE _TERM_HEDGE_LEAD_RE _TERM_HEDGE_TRAIL_CONDITION_RE
    _TERM_HEDGE_TRAIL_NEGATION_RE _analytical_voice_hits _boundary_aside_hits
    _claim_text _compound_module_heading_hits _constraint_is_declared_subject
    _contract_relations _declared_count _dict_items _formulaic_transition_issues
    _full_prose_paragraph_boundary_issues _full_prose_source_coverage_issues
    _generic_onscreen_relation_hits _has_any _has_visible_declared_relation
    _is_direct_boundary_clarification _issue _leading_negative_foreground_terms
    _line_indent _load_module_ceiling _mechanical_evidence_bullets
    _mechanical_onscreen_label_pattern_hits _model_slot_coverage_issues
    _module_heading_colon_hits _narration_boundary_issues _necessity_page_closure_issues
    _negative_foreground_issues _negative_foreground_terms _nontable_compact_len
    _onscreen_backend_meta_hits _onscreen_constraint_module_hits
    _onscreen_detail_phrase_overages _onscreen_false_parallel_semantics
    _onscreen_flat_long_labelled_detail_hits _onscreen_flow_language_issues
    _onscreen_heading_candidates _onscreen_layout_meta_hits _onscreen_markdown_hits
    _onscreen_module_provenance_issues _onscreen_parallel_structure_issues
    _onscreen_parent_child_role_mismatches _onscreen_relation_meta_hits
    _onscreen_subordinate_fragments _opening_negative_foreground_terms _outline_pages
    _page_content_unit_coverage_issues _page_relation_corpus
    _page_relationship_continuity_issues _page_relationship_summary _page_text
    _polarity_dropped_terms _preempted_scope_terms _preflight_semantic_issues
    _presentation_issues _prohibited_colloquial_hits _prohibited_contrast_hits
    _prohibited_contrast_issues _prose_issues _relation_corpus _relation_parallel_labels
    _relation_values _relation_visibility_signal _relationship_prerequisite_issue
    _relationship_strings _same_page_responsibility _selected_problem_slots
    _semantic_line_role _source_consumption_issues _source_refs
    _source_statement_overlap _speaker_placeholder_hits _subtitle_policy_issues
    _truth_records _unhedged_scope_terms _unhedged_terms _unlabeled_onscreen_bullets
    _visible_module_groups _visual_module_label _visual_structure_chain_nodes
    _visual_structure_judgment_issues _visual_structure_layout_recipe_hits annotations
    assert_imagegen_onscreen_readiness audience_facing_group_label
    audit_final_manuscript_form audit_script_quality build_communication_review
    extract_page_contract_receipt extract_speaker_notes is_final_script_path
    load_page_contract_sidecar meaningful_char_count normalized_tokens
    onscreen_effective_char_target onscreen_semantic_coverage onscreen_story_roles
    parse_script_markdown parse_script_path parse_selection_notes re resolve_judgment_mode
    script_retry_directive selection_notes_are_structured strip_authoring_group_marker
    text_similarity
    """.split()
)

BASE_PUBLIC_CONSTANT_OWNERS = {
    "parsing": (
        "FIELD_RE",
        "HEADING_FIELD_ALIASES",
        "HEADING_FIELD_RE",
        "INLINE_MODULE_RE",
        "NON_ONSCREEN_VISUAL_HEADING_RE",
        "PAGE_CONTRACT_FIELDS",
        "PAGE_CONTRACT_RECEIPT_RE",
        "SOURCE_RANGE_RE",
        "SOURCE_RE",
        "SPEAKER_SECTION_RE",
    ),
    "text_rules": (
        "NEGATION_TERMS",
        "PROSE_MIN_CHARS",
    ),
    "onscreen": (
        "ONSCREEN_SEMANTIC_COVERAGE_MIN",
    ),
}

BASE_PUBLIC_CONSTANT_SYMBOLS = frozenset(
    name
    for names in BASE_PUBLIC_CONSTANT_OWNERS.values()
    for name in names
)

FROZEN_FACADE_SYMBOLS = LEGACY_FACT_SYMBOLS | BASE_PUBLIC_CONSTANT_SYMBOLS

BASELINE_SCRIPT = """## 第1页：统一服务运营
- 页面类型：内容页
- 页面标题：统一服务运营
- 主判断：统一服务运营基础将分散资源组织为可交付的行业服务。
- 证据：ST001
- 证据映射：ST001

### 完整文字稿

统一服务运营基础将分散资源组织为可交付的行业服务，并通过统一接入、能力编排和过程治理形成稳定供给。该机制使需求、资源和交付要求在同一运营链路内衔接，确保服务可以持续复用和审阅。

### 文字稿取舍说明

必留上屏：统一运营链路与服务供给结果。
仅讲解：能力编排的执行细节。
仅追溯：来源材料中的背景说明。

### 上屏结论

统一运营基础形成可交付服务供给。

### 上屏文字

**统一运营链路**
    需求接入 → 能力编排 → 服务交付

### 视觉结构

需求从左侧进入统一运营链路，经中央能力编排后在右侧形成服务交付结果。

### 演讲者备注

本页说明统一服务运营如何将分散资源转化为稳定供给。先从需求接入开始，再说明能力编排如何连接资源与交付要求，最后落到可复用、可审阅的服务结果，帮助听众理解运营基础的实际作用。
"""

BASELINE_OUTLINE = {
    "pages": [{
        "page_id": "p01",
        "page_type": "content",
        "title": "统一服务运营",
        "core_message": "统一服务运营基础将分散资源组织为可交付的行业服务。",
        "source_refs": ["ST001"],
        "onscreen_judgment_mode": "locked",
        "onscreen_conclusion": "统一运营基础形成可交付服务供给。",
        "onscreen_modules": [{
            "title": "统一运营链路", "source_refs": ["ST001"],
        }],
    }],
}

BASELINE_SOURCE_TRUTH = {
    "records": [{
        "id": "ST001",
        "statement": "统一服务运营基础将分散资源组织为可交付的行业服务，并通过统一接入、能力编排和过程治理形成稳定供给。",
    }],
}

BASELINE_PATH = Path(__file__).parent / "fixtures" / "script_quality_contract_baseline.json"
SCRIPT_QUALITY_PACKAGE = "cyberppt.script_quality"


def internal_import_targets(
    node: ast.Import | ast.ImportFrom,
    module_names: frozenset[str],
) -> tuple[str, ...]:
    targets: list[str] = []
    if isinstance(node, ast.Import):
        for alias in node.names:
            prefix = f"{SCRIPT_QUALITY_PACKAGE}."
            if alias.name.startswith(prefix):
                target = alias.name[len(prefix):].split(".", 1)[0]
                if target in module_names:
                    targets.append(target)
        return tuple(targets)

    if node.level == 1:
        if node.module:
            target = node.module.split(".", 1)[0]
            if target in module_names:
                targets.append(target)
        else:
            targets.extend(
                alias.name.split(".", 1)[0]
                for alias in node.names
                if alias.name.split(".", 1)[0] in module_names
            )
        return tuple(targets)

    prefix = f"{SCRIPT_QUALITY_PACKAGE}."
    if node.level == 0 and node.module and node.module.startswith(prefix):
        target = node.module[len(prefix):].split(".", 1)[0]
        if target in module_names:
            targets.append(target)
    return tuple(targets)


def internal_dependency_graph(package_dir: Path) -> dict[str, set[str]]:
    paths = sorted(package_dir.glob("*.py"))
    module_names = frozenset(path.stem for path in paths)
    graph = {name: set() for name in module_names}
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                graph[path.stem].update(internal_import_targets(node, module_names))
    return graph


def strongly_connected_components(
    graph: dict[str, set[str]],
) -> list[tuple[str, ...]]:
    index = 0
    indices: dict[str, int] = {}
    lowlinks: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    components: list[tuple[str, ...]] = []

    def visit(node: str) -> None:
        nonlocal index
        indices[node] = index
        lowlinks[node] = index
        index += 1
        stack.append(node)
        on_stack.add(node)

        for target in sorted(graph[node]):
            if target not in indices:
                visit(target)
                lowlinks[node] = min(lowlinks[node], lowlinks[target])
            elif target in on_stack:
                lowlinks[node] = min(lowlinks[node], indices[target])

        if lowlinks[node] == indices[node]:
            component: list[str] = []
            while True:
                target = stack.pop()
                on_stack.remove(target)
                component.append(target)
                if target == node:
                    break
            components.append(tuple(sorted(component)))

    for node in sorted(graph):
        if node not in indices:
            visit(node)
    return sorted(components)


def json_value(value: object) -> object:
    return json.loads(json.dumps(value, ensure_ascii=False, sort_keys=True))


def serialize_document(document: object) -> dict[str, object]:
    return json_value(asdict(document))  # type: ignore[arg-type, return-value]


def serialize_issues(issues: list[object]) -> list[dict[str, object]]:
    return json_value([asdict(issue) for issue in issues])  # type: ignore[arg-type, return-value]


class ScriptQualityCompatibilityTests(unittest.TestCase):
    def test_internal_dependency_graph_has_no_nontrivial_scc(self) -> None:
        package_dir = Path(__file__).parents[1] / "cyberppt" / "script_quality"
        graph = internal_dependency_graph(package_dir)
        nontrivial = [
            component
            for component in strongly_connected_components(graph)
            if len(component) > 1
        ]
        self.assertEqual([], nontrivial)

    def test_internal_package_imports_are_not_nested_in_functions(self) -> None:
        package_dir = Path(__file__).parents[1] / "cyberppt" / "script_quality"
        paths = sorted(package_dir.glob("*.py"))
        module_names = frozenset(path.stem for path in paths)
        offenders: list[str] = []

        class NestedImportVisitor(ast.NodeVisitor):
            def __init__(self, path: Path) -> None:
                self.path = path
                self.function_depth = 0

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
                self.function_depth += 1
                self.generic_visit(node)
                self.function_depth -= 1

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
                self.function_depth += 1
                self.generic_visit(node)
                self.function_depth -= 1

            def visit_Lambda(self, node: ast.Lambda) -> None:
                self.function_depth += 1
                self.generic_visit(node)
                self.function_depth -= 1

            def record_import(self, node: ast.Import | ast.ImportFrom) -> None:
                if not self.function_depth:
                    return
                offenders.extend(
                    f"{self.path.name}:{node.lineno}:{target}"
                    for target in internal_import_targets(node, module_names)
                )

            def visit_Import(self, node: ast.Import) -> None:
                self.record_import(node)

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                self.record_import(node)

        for path in paths:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            NestedImportVisitor(path).visit(tree)
        self.assertEqual([], offenders)

    def test_internal_modules_do_not_import_legacy_facade(self) -> None:
        package_dir = Path(__file__).parents[1] / "cyberppt" / "script_quality"
        offenders = []
        for path in sorted(package_dir.glob("*.py")):
            text = path.read_text(encoding="utf-8")
            if "script_quality_contract" in text:
                offenders.append(path.name)
        self.assertEqual([], offenders)

    def test_all_internal_modules_import_cleanly(self) -> None:
        names = (
            "common", "models", "parsing", "text_rules", "onscreen",
            "source_coverage", "presentation", "relationships", "final_form",
            "audit",
        )
        for name in names:
            with self.subTest(name=name):
                importlib.import_module(f"cyberppt.script_quality.{name}")

    def test_common_text_helpers_have_one_implementation(self) -> None:
        common = importlib.import_module("cyberppt.script_quality.common")
        text_rules = importlib.import_module("cyberppt.script_quality.text_rules")
        onscreen = importlib.import_module("cyberppt.script_quality.onscreen")
        source_coverage = importlib.import_module(
            "cyberppt.script_quality.source_coverage"
        )
        for name in ("_compact_len", "normalized_tokens", "text_similarity"):
            with self.subTest(module="text_rules", name=name):
                self.assertIs(getattr(common, name), getattr(text_rules, name))
        for name in ("_compact_len", "normalized_tokens"):
            with self.subTest(module="onscreen", name=name):
                self.assertIs(getattr(common, name), getattr(onscreen, name))
        for name in ("normalized_tokens", "text_similarity"):
            with self.subTest(module="source_coverage", name=name):
                self.assertIs(getattr(common, name), getattr(source_coverage, name))

    def test_audit_is_direct_reexport_and_facade_is_small(self) -> None:
        legacy = importlib.import_module("cyberppt.script_quality_contract")
        audit = importlib.import_module("cyberppt.script_quality.audit")
        self.assertIs(legacy.audit_script_quality, audit.audit_script_quality)
        self.assertIs(legacy.script_retry_directive, audit.script_retry_directive)
        facade = Path(legacy.__file__).read_text(encoding="utf-8")
        self.assertLessEqual(len(facade.splitlines()), 200)

    def test_legacy_facade_explicitly_reexports_all_frozen_symbols(self) -> None:
        legacy = importlib.import_module("cyberppt.script_quality_contract")
        facade = Path(legacy.__file__).read_text(encoding="utf-8")
        tree = ast.parse(facade)

        self.assertEqual(205, len(LEGACY_FACT_SYMBOLS))
        self.assertEqual(13, len(BASE_PUBLIC_CONSTANT_SYMBOLS))
        self.assertEqual(218, len(FROZEN_FACADE_SYMBOLS))
        self.assertEqual(FROZEN_FACADE_SYMBOLS, frozenset(getattr(legacy, "__all__", ())))
        self.assertEqual(
            [],
            sorted(name for name in FROZEN_FACADE_SYMBOLS if not hasattr(legacy, name)),
        )

        imported_names: set[str] = set()
        star_imports: list[str] = []
        unexpected_nodes: list[str] = []
        for index, node in enumerate(tree.body):
            if index == 0 and isinstance(node, ast.Expr):
                continue
            if isinstance(node, ast.Import):
                imported_names.update(
                    alias.asname or alias.name.split(".")[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                star_imports.extend(
                    alias.name for alias in node.names if alias.name == "*"
                )
                imported_names.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name != "*"
                )
            elif not (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "__all__"
            ):
                unexpected_nodes.append(type(node).__name__)
        self.assertEqual([], star_imports)
        self.assertEqual([], unexpected_nodes)
        self.assertEqual(FROZEN_FACADE_SYMBOLS, frozenset(imported_names))

    def test_legacy_facade_directly_reexports_base_public_constants(self) -> None:
        legacy = importlib.import_module("cyberppt.script_quality_contract")
        missing = sorted(
            name for name in BASE_PUBLIC_CONSTANT_SYMBOLS if not hasattr(legacy, name)
        )
        self.assertEqual([], missing)
        for owner, names in BASE_PUBLIC_CONSTANT_OWNERS.items():
            module = importlib.import_module(f"cyberppt.script_quality.{owner}")
            for name in names:
                with self.subTest(owner=owner, name=name):
                    self.assertIs(getattr(module, name), getattr(legacy, name))

    def test_models_are_reexported_without_wrapper_types(self) -> None:
        legacy = importlib.import_module("cyberppt.script_quality_contract")
        models = importlib.import_module("cyberppt.script_quality.models")
        self.assertIs(legacy.ScriptPage, models.ScriptPage)
        self.assertIs(legacy.ScriptDocument, models.ScriptDocument)
        self.assertIs(legacy.ScriptQualityIssue, models.ScriptQualityIssue)

    def test_parsing_functions_are_reexported_directly(self) -> None:
        legacy = importlib.import_module("cyberppt.script_quality_contract")
        parsing = importlib.import_module("cyberppt.script_quality.parsing")
        self.assertIs(legacy.parse_script_markdown, parsing.parse_script_markdown)
        self.assertIs(legacy.parse_script_path, parsing.parse_script_path)
        self.assertIs(legacy.extract_speaker_notes, parsing.extract_speaker_notes)

    def test_text_and_onscreen_rules_are_direct_reexports(self) -> None:
        legacy = importlib.import_module("cyberppt.script_quality_contract")
        text_rules = importlib.import_module("cyberppt.script_quality.text_rules")
        onscreen = importlib.import_module("cyberppt.script_quality.onscreen")
        self.assertIs(
            legacy._prohibited_contrast_hits,
            text_rules._prohibited_contrast_hits,
        )
        self.assertIs(
            legacy._prohibited_colloquial_hits,
            text_rules._prohibited_colloquial_hits,
        )
        self.assertIs(
            legacy._unlabeled_onscreen_bullets,
            onscreen._unlabeled_onscreen_bullets,
        )
        self.assertIs(
            legacy.assert_imagegen_onscreen_readiness,
            onscreen.assert_imagegen_onscreen_readiness,
        )
        self.assertIs(
            legacy._MODULE_CEILING_FALLBACK,
            onscreen._MODULE_CEILING_FALLBACK,
        )
        self.assertIs(legacy._RULES_YAML_PATH, onscreen._RULES_YAML_PATH)
        self.assertIs(
            legacy._load_module_ceiling,
            onscreen._load_module_ceiling,
        )

    def test_source_coverage_functions_are_direct_reexports(self) -> None:
        legacy = importlib.import_module("cyberppt.script_quality_contract")
        coverage = importlib.import_module("cyberppt.script_quality.source_coverage")
        self.assertIs(legacy.text_similarity, coverage.text_similarity)
        self.assertIs(
            legacy._source_consumption_issues,
            coverage._source_consumption_issues,
        )
        self.assertIs(
            legacy._full_prose_source_coverage_issues,
            coverage._full_prose_source_coverage_issues,
        )

    def test_communication_review_exports_are_direct_reexports(self) -> None:
        legacy = importlib.import_module("cyberppt.script_quality_contract")
        audit = importlib.import_module("cyberppt.script_quality.audit")
        self.assertIs(
            legacy.build_communication_review,
            audit.build_communication_review,
        )
        self.assertIs(
            legacy.ONSCREEN_SEMANTIC_COVERAGE_TARGET,
            audit.ONSCREEN_SEMANTIC_COVERAGE_TARGET,
        )

    def test_presentation_final_form_and_relationships_are_reexported(self) -> None:
        legacy = importlib.import_module("cyberppt.script_quality_contract")
        presentation = importlib.import_module("cyberppt.script_quality.presentation")
        final_form = importlib.import_module("cyberppt.script_quality.final_form")
        relationships = importlib.import_module("cyberppt.script_quality.relationships")
        self.assertIs(legacy._presentation_issues, presentation._presentation_issues)
        self.assertIs(legacy.audit_final_manuscript_form, final_form.audit_final_manuscript_form)
        self.assertIs(
            legacy._page_relationship_continuity_issues,
            relationships._page_relationship_continuity_issues,
        )

    def test_legacy_module_exports_used_contract(self) -> None:
        module = importlib.import_module("cyberppt.script_quality_contract")
        missing = [name for name in COMPAT_SYMBOLS if not hasattr(module, name)]
        self.assertEqual([], missing)

    def test_baseline_fixture_matches_current_contract(self) -> None:
        module = importlib.import_module("cyberppt.script_quality_contract")
        document = module.parse_script_markdown(BASELINE_SCRIPT)
        actual = {
            "document": serialize_document(document),
            "issues": serialize_issues(
                module.audit_script_quality(
                    document, BASELINE_OUTLINE, BASELINE_SOURCE_TRUTH,
                )
            ),
        }
        expected = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(expected, actual)
