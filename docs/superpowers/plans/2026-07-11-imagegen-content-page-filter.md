# ImageGen Content-Page Filter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent CyberPPT from scheduling image generation for cover, agenda, chapter-transition, and ending pages.

**Architecture:** Add a shared page-role classifier beside the image-manifest builder and use it to split a requested page range into content-image pairs and template-only skipped pages. Keep the `pairs[]` item schema unchanged; record `skipped_pages[]` alongside it. Existing template export remains responsible for non-content rendering.

**Tech Stack:** Python 3, JSON manifests, `unittest`, existing CyberPPT CLI.

## Global Constraints

- `pairs[]` contains only business-content image-generation tasks.
- Each `skipped_pages[]` entry contains `page_number`, `title`, `page_role`, and `reason: template_only_page`.
- Cover, agenda, section, and ending pages remain in the requested project page set for template assembly.
- A request with no content pages raises an actionable `ValueError`.
- Template export behavior is unchanged.

---

### Task 1: Classify template-only pages in the manifest builder

**Files:**

- Modify: `scripts/dual_image_overlay/cyberppt_pair_manifest.py:34-201`
- Test: `tests/test_dual_image_overlay_pair_manifest.py`

**Interfaces:**

- Consumes parsed page objects with `page_number`, `title`, and `text` from `parse_page_blocks()`.
- Produces `classify_page_role(page_number: int, title: str, text: str) -> str` and manifest field `skipped_pages: list[dict[str, object]]`.

- [ ] **Step 1: Write failing manifest tests**

```python
def test_build_manifest_skips_template_only_pages_and_keeps_content_pages(self):
    manifest, *_ = module.build_manifest(
        script=script, pages_raw="1-5", output_dir=output_dir,
        project_path=None, style_lock=None,
    )
    self.assertEqual([4], [pair["page_number"] for pair in manifest["pairs"]])
    self.assertEqual(
        [(1, "cover"), (2, "agenda"), (3, "section"), (5, "ending")],
        [(item["page_number"], item["page_role"]) for item in manifest["skipped_pages"]],
    )

def test_build_manifest_rejects_navigation_only_range(self):
    with self.assertRaisesRegex(ValueError, "no content pages selected for image generation"):
        module.build_manifest(
            script=script, pages_raw="1-3,5", output_dir=output_dir,
            project_path=None, style_lock=None,
        )
```

- [ ] **Step 2: Verify the new tests fail**

Run: `python3 -m unittest tests.test_dual_image_overlay_pair_manifest -v`

Expected: FAIL because every requested page is currently added to `pairs[]`.

- [ ] **Step 3: Implement role classification and filtering**

```python
def classify_page_role(page_number: int, title: str, text: str) -> str:
    normalized = f"{title}\n{text}"
    if page_number == 1 or "封面" in title:
        return "cover"
    if "目录" in title:
        return "agenda"
    if any(marker in title for marker in ("封底", "结束", "感谢")):
        return "ending"
    if "章节过渡" in normalized or re.match(r"第[一二三四五六七八九十]+章", title):
        return "section"
    return "content"
```

In `build_manifest()`, build `pairs[]` only for `content` pages. For every other role append `{page_number, title, page_role, reason: "template_only_page"}` to `skipped_pages[]`. Add `requested_pages: page_numbers` and `skipped_pages: skipped_pages` to the manifest. If `pairs` is empty, raise `ValueError("no content pages selected for image generation; select at least one content page")`.

- [ ] **Step 4: Verify focused tests pass**

Run: `python3 -m unittest tests.test_dual_image_overlay_pair_manifest -v`

Expected: PASS.

- [ ] **Step 5: Commit task one**

```bash
git add scripts/dual_image_overlay/cyberppt_pair_manifest.py tests/test_dual_image_overlay_pair_manifest.py
git commit -m "feat: skip template-only pages during image generation"
```

### Task 2: Preserve project-stage traceability

**Files:**

- Modify: `cyberppt/commands/final_script_pages.py:437-530`
- Test: `tests/test_final_script_pages.py`

**Interfaces:**

- Consumes a filtered manifest with `requested_pages`, `pairs[]`, and `skipped_pages[]`.
- Produces a final-script-page summary that distinguishes requested project pages from image-generation pages.

- [ ] **Step 1: Write failing project-level regression test**

```python
def test_final_script_pages_records_template_only_pages_without_image_tasks(self):
    summary = run_final_script_pages(project=project, script=script, pages_raw="1-5")
    manifest = json.loads(Path(summary["artifacts"]["page_image_pairs"]).read_text(encoding="utf-8"))
    self.assertEqual([1, 2, 3, 4, 5], summary["pages"])
    self.assertEqual([4], [pair["page_number"] for pair in manifest["pairs"]])
    self.assertEqual([1, 2, 3, 5], [item["page_number"] for item in manifest["skipped_pages"]])
```

- [ ] **Step 2: Verify the regression test fails**

Run: `python3 -m unittest tests.test_final_script_pages.FinalScriptPagesTests.test_final_script_pages_records_template_only_pages_without_image_tasks -v`

Expected: FAIL because the current manifest schedules every page as a full-image task.

- [ ] **Step 3: Add traceability fields to the stage summary**

```python
generated_pages = [int(pair["page_number"]) for pair in manifest["pairs"]]
skipped_pages = [int(item["page_number"]) for item in manifest.get("skipped_pages", [])]
summary["image_generation_pages"] = generated_pages
summary["template_only_pages"] = skipped_pages
```

Keep `summary["pages"]`, template-text locks, approvals, notes, and assembly scope equal to the requested page list.

- [ ] **Step 4: Run focused regressions**

Run: `python3 -m unittest tests.test_dual_image_overlay_pair_manifest tests.test_final_script_pages -v`

Expected: PASS.

- [ ] **Step 5: Run broader verification and commit**

Run: `python3 -m unittest discover -s tests -p 'test*.py'`

Expected: PASS with no production-preparation or template-export regression.

```bash
git add cyberppt/commands/final_script_pages.py tests/test_final_script_pages.py
git commit -m "feat: report template-only image generation skips"
```
