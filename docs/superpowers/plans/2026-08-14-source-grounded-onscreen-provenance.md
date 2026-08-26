# Source-Grounded Onscreen Provenance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure every visible Stage 01 module is traceable to its Source Truth facts and expression-model slots, rejecting undeclared cross-fact or cross-slot mixing.

**Architecture:** Add a derived `onscreen_modules` provenance contract to each content page. The Stage 01 compiler produces source-record-bounded `direct` modules and author-confirmable cross-record candidates; the Outline audit validates the contract, the Markdown compiler exposes it outside the audience layer, and script audit verifies each visible module against its declared source boundary rather than granting a page-wide coverage exemption.

**Tech Stack:** Python 3.12, standard-library JSON, CyberPPT Stage 01 CLI, `pytest`.

## Global Constraints

- Do not rerun source registration, semantic understanding, or Source Truth compilation for the current project.
- Preserve Source Truth as the sole fact authority; no page assignment or authored conclusions are written back to it.
- `direct` consumes exactly one Source Truth record and one expression-model slot.
- Cross-record writing requires explicit `synthesis` or `relation` provenance with an allowed claim and rationale.
- Existing Outlines without `source_grounding_mode=required` retain their current audit path.
- Do not create approval, receipt, attempt, manifest, or parallel workflow artifacts.

---

### Task 1: Add source-grounded module generation

**Files:**
- Modify: `cyberppt/stage01_compiler.py:417-632`
- Test: `tests/test_stage01_compiler.py:43-145`

**Interfaces:**
- Consumes: `_page_content_units(page_id, records, topic, expression_model_selection=...)` and the page's `expression_model_selection.source_mapping`.
- Produces: `_onscreen_modules(page_id, records, expression_model_selection) -> list[dict[str, Any]]`; `refresh_outline_content_units()` writes `page["onscreen_modules"]` and `page["source_grounding_mode"] = "required"` only for the refreshed target page.

- [ ] **Step 1: Write failing generation tests**

```python
def test_refresh_generates_one_direct_module_per_source_record_and_slot(self) -> None:
    records = [
        {"id": "ST001", "statement": "协同需求持续增长。", "argument_duty": "driver", "priority": "P0", "semantic_units": [{"text": "协同需求持续增长"}]},
        {"id": "ST002", "statement": "分散资源尚未形成稳定的行业服务供给。", "argument_duty": "gap", "priority": "P0", "semantic_units": [{"text": "分散资源尚未形成稳定的行业服务供给"}]},
    ]
    modules = _onscreen_modules("p04", records, {
        "fit": "selected", "source_mapping": [
            {"slot": "complication", "source_refs": ["ST001", "ST002"]},
        ],
    })
    self.assertEqual(["ST001"], modules[0]["source_refs"])
    self.assertEqual(["ST002"], modules[1]["source_refs"])
    self.assertEqual("direct", modules[1]["derivation_mode"])
    self.assertEqual(["complication"], modules[1]["model_slots"])

def test_refresh_does_not_generate_cross_record_direct_claim(self) -> None:
    modules = _onscreen_modules("p04", records, selected_scqa)
    self.assertNotIn(
        "稳定的数据服务和场景服务供给",
        "\n".join(str(item.get("allowed_visible_claim")) for item in modules),
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_stage01_compiler.py -k 'onscreen_modules or refresh_generates'`

Expected: import failure for `_onscreen_modules`.

- [ ] **Step 3: Implement source-record-bounded generation**

```python
def _onscreen_modules(
    page_id: str,
    records: list[dict[str, Any]],
    expression_model_selection: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    slot_by_ref: dict[str, list[str]] = {}
    for mapping in (expression_model_selection or {}).get("source_mapping") or []:
        if not isinstance(mapping, dict) or mapping.get("implicit") is True:
            continue
        slot = str(mapping.get("slot") or "").strip()
        for ref in _strings(mapping.get("source_refs")):
            slot_by_ref.setdefault(ref, []).append(slot)
    modules = []
    for index, record in enumerate(records, start=1):
        ref = str(record.get("id") or "")
        if not ref:
            continue
        claim = str(record.get("statement") or "").strip()
        modules.append({
            "module_id": f"{page_id}-M{index:02d}",
            "display_title": _clean_title(claim),
            "source_refs": [ref],
            "model_slots": list(dict.fromkeys(slot_by_ref.get(ref, []))),
            "derivation_mode": "direct",
            "allowed_visible_claim": claim,
            "required_characteristics": _content_unit_anchors(record, ""),
        })
    return modules
```

In `refresh_outline_content_units()`, add:

```python
page["onscreen_modules"] = _onscreen_modules(
    str(page.get("page_id") or ""), page_records,
    page.get("expression_model_selection") if isinstance(page.get("expression_model_selection"), dict) else None,
)
page["source_grounding_mode"] = "required"
```

- [ ] **Step 4: Run focused compiler tests**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_stage01_compiler.py`

Expected: all pass.

- [ ] **Step 5: Commit the generation contract**

```bash
git add cyberppt/stage01_compiler.py tests/test_stage01_compiler.py
git commit -m "feat(stage01): generate source-grounded onscreen modules"
```

### Task 2: Validate provenance in the Outline audit

**Files:**
- Modify: `cyberppt/outline_audit_semantics.py:199-399`
- Test: `tests/test_outline_contract.py:205-260`

**Interfaces:**
- Consumes: content-page `source_grounding_mode`, `onscreen_modules`, `source_refs`, and `expression_model_selection.source_mapping`.
- Produces: `_onscreen_module_provenance_issues(pages) -> list[AuditIssue]` with `SOURCE_GROUNDING_MODULE_INVALID`.

- [ ] **Step 1: Write failing validation tests**

```python
def test_required_source_grounding_rejects_direct_module_with_two_sources(self) -> None:
    page = formal_content_page()
    page["source_grounding_mode"] = "required"
    page["onscreen_modules"] = [{
        "module_id": "p04-M01", "display_title": "缺口",
        "source_refs": ["ST001", "ST002"], "model_slots": ["complication"],
        "derivation_mode": "direct", "allowed_visible_claim": "混合事实",
        "required_characteristics": ["来源特征"],
    }]
    codes = {issue.code for issue in audit_outline({"pages": [page]})}
    self.assertIn("SOURCE_GROUNDING_MODULE_INVALID", codes)

def test_required_source_grounding_accepts_declared_synthesis(self) -> None:
    page = formal_content_page()
    page["source_grounding_mode"] = "required"
    page["onscreen_modules"] = [{
        "module_id": "p04-M03", "display_title": "供需关系",
        "source_refs": ["ST001", "ST002"], "model_slots": ["complication", "answer"],
        "derivation_mode": "synthesis", "relation": "responds_to",
        "allowed_visible_claim": "协同需求需要统一服务运营基础回应",
        "synthesis_rationale": "来源分别陈述需求和回应，页面明示其回应关系。",
        "required_characteristics": ["协同需求", "服务运营基础"],
    }]
    self.assertNotIn("SOURCE_GROUNDING_MODULE_INVALID", {issue.code for issue in audit_outline({"pages": [page]})})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_outline_contract.py -k 'source_grounding'`

Expected: the invalid direct module is not yet rejected.

- [ ] **Step 3: Add provenance contract validation**

```python
def _onscreen_module_provenance_issues(pages: list[dict[str, object]]) -> list[AuditIssue]:
    issues: list[AuditIssue] = []
    for page in pages:
        if page.get("source_grounding_mode") != "required":
            continue
        page_id = _page_id(page)
        page_refs = set(_strings(page.get("source_refs")))
        mapped_slots = {
            str(mapping.get("slot") or "")
            for mapping in ((page.get("expression_model_selection") or {}).get("source_mapping") or [])
            if isinstance(mapping, dict) and mapping.get("implicit") is not True
        }
        for module in _items(page.get("onscreen_modules")):
            mode = str(module.get("derivation_mode") or "")
            refs = set(_strings(module.get("source_refs")))
            slots = set(_strings(module.get("model_slots")))
            claim = str(module.get("allowed_visible_claim") or "").strip()
            invalid = not module.get("module_id") or not claim or not refs <= page_refs
            invalid |= mode == "direct" and (len(refs) != 1 or len(slots) > 1)
            invalid |= mode in {"synthesis", "relation"} and not all(
                str(module.get(key) or "").strip()
                for key in ("relation", "synthesis_rationale")
            )
            invalid |= mode not in {"direct", "synthesis", "relation"}
            invalid |= bool(slots - mapped_slots)
            if invalid:
                issues.append(AuditIssue(
                    "SOURCE_GROUNDING_MODULE_INVALID",
                    "上屏来源归属模块不满足 direct、synthesis 或 relation 的事实边界契约。",
                    (page_id,), "repair_onscreen_module_provenance",
                ))
    return issues
```

Call it from `audit_outline()` after `_expression_model_issues()`.

- [ ] **Step 4: Run focused audit tests**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_outline_contract.py tests/test_outline_audit_command.py`

Expected: all pass.

- [ ] **Step 5: Commit Outline validation**

```bash
git add cyberppt/outline_audit_semantics.py tests/test_outline_contract.py
git commit -m "feat(stage01): validate onscreen fact provenance"
```

### Task 3: Expose provenance in authoring Markdown

**Files:**
- Modify: `cyberppt/commands/compile_page_script_authoring.py:155-339`
- Test: `tests/test_compile_page_script_authoring.py:176-220`

**Interfaces:**
- Consumes: page `onscreen_modules` validated in Task 2.
- Produces: `_onscreen_provenance_block(page) -> list[str]`; a `### 上屏来源归属（不上屏）` block immediately after `### 表达模型（不上屏）`.

- [ ] **Step 1: Write the failing Markdown output test**

```python
def test_emits_onscreen_provenance_as_non_onscreen_context(self) -> None:
    page = self.outline["pages"][2]
    page["onscreen_modules"] = [{
        "module_id": "p03-M01", "display_title": "服务供给断点",
        "source_refs": ["ST001"], "model_slots": ["complication"],
        "derivation_mode": "direct", "allowed_visible_claim": "分散资源尚未形成稳定供给",
        "required_characteristics": ["资源发现", "服务运营机制"],
    }]
    # Rewrite outline and authoring SHA as in existing expression-model test.
    compile_page_script_authoring(self.project, output_dir=output)
    chapter = (output / "ch01.md").read_text(encoding="utf-8")
    self.assertIn("### 上屏来源归属（不上屏）", chapter)
    self.assertIn("p03-M01｜服务供给断点｜direct｜complication｜ST001", chapter)
    self.assertNotIn("上屏来源归属", chapter.split("### 上屏文字（严格锁定）", 1)[1].split("### 逻辑骨架", 1)[0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_compile_page_script_authoring.py -k 'onscreen_provenance'`

Expected: missing Markdown section.

- [ ] **Step 3: Implement Markdown rendering**

```python
def _onscreen_provenance_block(page: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    for module in page.get("onscreen_modules") or []:
        if not isinstance(module, dict):
            continue
        module_id = str(module.get("module_id") or "").strip()
        title = str(module.get("display_title") or "").strip()
        mode = str(module.get("derivation_mode") or "").strip()
        slots = "、".join(_strings(module.get("model_slots"))) or "未映射槽位"
        refs = "、".join(_strings(module.get("source_refs"))) or "未引用"
        lines.append(f"- {module_id}｜{title}｜{mode}｜{slots}｜{refs}")
        lines.append(f"  - 允许命题：{str(module.get('allowed_visible_claim') or '').strip()}")
        characteristics = "、".join(_strings(module.get("required_characteristics")))
        if characteristics:
            lines.append(f"  - 必留特征：{characteristics}")
        if mode in {"synthesis", "relation"}:
            lines.append(f"  - 关系：{str(module.get('relation') or '').strip()}")
            lines.append(f"  - 综合理由：{str(module.get('synthesis_rationale') or '').strip()}")
    return lines or ["- 未启用来源归属契约。"]
```

Insert the section after `*_expression_model_block(page)` in `_content_page()`.

- [ ] **Step 4: Run authoring compiler tests**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_compile_page_script_authoring.py`

Expected: all pass.

- [ ] **Step 5: Commit Markdown visibility**

```bash
git add cyberppt/commands/compile_page_script_authoring.py tests/test_compile_page_script_authoring.py
git commit -m "feat(stage01): render onscreen fact provenance"
```

### Task 4: Enforce visible module-to-fact provenance in script audit

**Files:**
- Modify: `cyberppt/script_quality_contract.py:554-624, 3010-3150, 4764-5289`
- Test: `tests/test_script_quality_contract.py:129-192`

**Interfaces:**
- Consumes: parsed visible module groups from `page.onscreen_text` and page `onscreen_modules`.
- Produces: `_onscreen_module_provenance_issues(page, contract) -> list[ScriptQualityIssue]` with `ONSCREEN_FACT_PROVENANCE_MISSING` and `ONSCREEN_CROSS_SLOT_FACT_MIXING`.

- [ ] **Step 1: Write failing script-audit tests**

```python
def test_direct_module_rejects_answer_result_mixed_into_complication(self) -> None:
    page = self._page(
        "服务供给断点\n"
        "    分散的数据、知识、模型和专业能力尚未形成稳定的数据服务和场景服务供给"
    )
    contract = {
        "source_grounding_mode": "required",
        "onscreen_modules": [{
            "module_id": "p04-M01", "display_title": "服务供给断点",
            "source_refs": ["ST008"], "model_slots": ["complication"],
            "derivation_mode": "direct",
            "allowed_visible_claim": "分散资源尚未形成稳定的行业服务供给",
            "required_characteristics": ["资源发现", "服务运营机制"],
        }],
    }
    codes = {issue.code for issue in _onscreen_module_provenance_issues(page, contract)}
    self.assertIn("ONSCREEN_CROSS_SLOT_FACT_MIXING", codes)

def test_direct_module_accepts_source_faithful_shortening(self) -> None:
    page = self._page(
        "服务供给断点\n"
        "    分散资源尚未形成稳定的行业服务供给\n"
        "    服务运营：供需对接、产品封装、授权执行、服务计量和价值结算尚未形成完整机制"
    )
    codes = {issue.code for issue in _onscreen_module_provenance_issues(page, direct_contract)}
    self.assertEqual(set(), codes & {"ONSCREEN_FACT_PROVENANCE_MISSING", "ONSCREEN_CROSS_SLOT_FACT_MIXING"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_script_quality_contract.py -k 'module_provenance or cross_slot'`

Expected: import failure for `_onscreen_module_provenance_issues`.

- [ ] **Step 3: Parse visible module groups and enforce the contract**

```python
def _visible_module_groups(text: str) -> dict[str, str]:
    groups: dict[str, str] = {}
    for group in (item for item in str(text).split("\n\n") if item.strip()):
        lines = [line.strip() for line in group.splitlines() if line.strip()]
        if lines:
            groups[_module_title(lines[0]) or lines[0]] = "\n".join(lines)
    return groups

def _onscreen_module_provenance_issues(
    page: ScriptPage, contract: dict[str, object],
) -> list[ScriptQualityIssue]:
    if contract.get("source_grounding_mode") != "required":
        return []
    groups = _visible_module_groups(page.onscreen_text)
    issues: list[ScriptQualityIssue] = []
    for module in _dict_items(contract, "onscreen_modules"):
        title = str(module.get("display_title") or "").strip()
        visible = groups.get(title, "")
        claim = str(module.get("allowed_visible_claim") or "").strip()
        characteristics = _strings(module.get("required_characteristics"))
        if not visible:
            issues.append(_issue("ONSCREEN_FACT_PROVENANCE_MISSING", page, "登记的上屏来源模块没有对应可见模块。", "恢复对应模块或修改来源归属登记。", evidence=(title,)))
            continue
        claim_overlap = _source_statement_overlap(claim, visible, size=3)
        feature_hit = any(feature in visible for feature in characteristics)
        if claim_overlap < 0.20 or not feature_hit:
            code = "ONSCREEN_CROSS_SLOT_FACT_MIXING" if module.get("derivation_mode") == "direct" else "ONSCREEN_FACT_PROVENANCE_MISSING"
            issues.append(_issue(code, page, "可见模块未保持登记来源事实的对象、状态或槽位边界。", "拆回直接事实，或登记为 synthesis/relation 并明确关系。", source_ids=tuple(_strings(module.get("source_refs"))), evidence=(f"module={title}", f"claim_overlap={claim_overlap:.3f}")))
    return issues
```

Call this function in `audit_script_quality()` before `_page_content_unit_coverage_issues()`. In `_page_content_unit_coverage_issues()`, remove the whole-page `model_covered_refs` exemption only when `source_grounding_mode == "required"`; direct-module coverage becomes the authoritative visible proof.

- [ ] **Step 4: Run script-contract tests**

Run: `PYTHONPATH=. python3 -m pytest -q tests/test_script_quality_contract.py`

Expected: all pass.

- [ ] **Step 5: Commit the enforcement gate**

```bash
git add cyberppt/script_quality_contract.py tests/test_script_quality_contract.py
git commit -m "fix(stage01): enforce onscreen fact provenance"
```

### Task 5: Regenerate only P04 and verify the real project path

**Files:**
- Modify: `projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline.json`
- Modify: `projects/power-data-infrastructure-cooperation-v16-20260813/workbench/scripts/drafts/c1.md`
- Generated audit: `projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline-audit.md`

**Interfaces:**
- Consumes: Tasks 1–4 and current project Source Truth, Outline, P04 script.
- Produces: P04 provenance records, P04 Markdown provenance block, passing `outline-audit` and `script-audit`.

- [ ] **Step 1: Refresh only P04 derived units and provenance**

Run:

```bash
PYTHONPATH=. python3 -m cyberppt refresh-outline-content-units \
  projects/power-data-infrastructure-cooperation-v16-20260813 \
  --page-id p04
```

Expected: only `p04.content_units`, `p04.onscreen_modules`, `p04.detail_refs`, and `p04.source_grounding_mode` are regenerated; author-authored page mission and judgment remain unchanged.

- [ ] **Step 2: Make the P04 author decision explicit**

Set `p04.onscreen_modules` so “服务供给断点” is `direct`, references only `ST0008`, uses only `complication`, and records the exact allowed claim plus its four source-specific characteristics. Keep the current source-faithful visible copy; do not place “数据服务和场景服务” in this direct module.

- [ ] **Step 3: Run Outline audit**

Run:

```bash
PYTHONPATH=. python3 -m cyberppt outline-audit \
  projects/power-data-infrastructure-cooperation-v16-20260813 \
  --input projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline.json
```

Expected: `status=passed`; no `SOURCE_GROUNDING_MODULE_INVALID`.

- [ ] **Step 4: Regenerate P04/P05 chapter draft through the normal authoring compiler**

Run:

```bash
PYTHONPATH=. python3 -m cyberppt compile-page-script-authoring \
  projects/power-data-infrastructure-cooperation-v16-20260813 \
  --output-dir projects/power-data-infrastructure-cooperation-v16-20260813/workbench/scripts/drafts/provenance-refresh
```

Copy only the verified P04 provenance block into the authoritative `c1.md` while preserving the user-reviewed P04/P05 prose and on-screen copy. Do not create a parallel authoritative draft.

- [ ] **Step 5: Run project script audit and full relevant regression suite**

Run:

```bash
PYTHONPATH=. python3 -m cyberppt script-audit \
  projects/power-data-infrastructure-cooperation-v16-20260813 \
  --input projects/power-data-infrastructure-cooperation-v16-20260813/workbench/scripts/drafts/c1.md
PYTHONPATH=. python3 -m pytest -q \
  tests/test_stage01_compiler.py \
  tests/test_outline_contract.py \
  tests/test_outline_audit_command.py \
  tests/test_compile_page_script_authoring.py \
  tests/test_script_quality_contract.py
git diff --check
npx --no-install graft build
npx --no-install graft check
```

Expected: project audit `passed`, test suite green, no whitespace errors, and `graph check: OK`.

- [ ] **Step 6: Commit the verified integration slice**

```bash
git add projects/power-data-infrastructure-cooperation-v16-20260813/workbench/stages/01-analysis/outline.json \
  projects/power-data-infrastructure-cooperation-v16-20260813/workbench/scripts/drafts/c1.md
git commit -m "fix(stage01): ground p04 onscreen facts in source truth"
```

## Self-review

- Spec coverage: Tasks 1–4 cover generation, contract validation, Markdown synchronization, and script enforcement; Task 5 verifies the exact P04 failure without re-running upstream stages.
- Compatibility: Task 2 and Task 4 apply new blocking behavior only under `source_grounding_mode=required`.
- Natural compression: Task 4 uses phrase overlap plus mandatory source characteristics, so a compressed direct claim can pass without a verbatim copy.
- Drift prevention: Task 4 removes the older whole-page model coverage exemption only for provenance-required pages, preventing a cross-slot aggregate unit from silently proving a direct visible module.
- Scope: no Source Truth edits, no Stage 02 work, and no unrelated worktree files are staged.
