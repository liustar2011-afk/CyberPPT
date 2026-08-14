# SOFFICE Preview Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make page preview rendering recover from Homebrew LibreOffice headless aborts by using the bundled SOFFICE fallback.

**Architecture:** Keep Office executable discovery and conversion retry local to `build_page.py`, matching the proven QA behaviour. Each conversion runs with a temporary LibreOffice profile; successful output is copied into the existing export paths.

**Tech Stack:** Python 3.12, `subprocess`, `tempfile`, `pytest`, LibreOffice SOFFICE, Poppler `pdftoppm`.

## Global Constraints

- Preserve the `--render-preview` CLI and `exports/page-render.pdf` / `page-render.png` output contract.
- Try PATH Office executables before the Codex bundled executable.
- Preserve all relevant error evidence if conversion cannot succeed.
- Do not modify unrelated dirty worktree files.

---

### Task 1: Add resilient Office conversion to page preview rendering

**Files:**

- Modify: `scripts/dual_image_overlay/build_page.py:49-100`
- Test: `tests/test_dual_image_overlay_build_page.py`

**Interfaces:**

- Consumes: `pptx_path: Path`, `exports: Path`, `shutil.which`, and the bundled SOFFICE path.
- Produces: `_render_pptx_preview(pptx_path: Path, exports: Path) -> Path`, preserving the returned PNG path.

- [ ] **Step 1: Write failing fallback tests**

```python
def test_render_preview_retries_bundled_soffice_after_path_failure(tmp_path, monkeypatch):
    # Make PATH soffice raise CalledProcessError, bundled soffice create page.pdf,
    # and assert the bundled command receives -env:UserInstallation=....
    assert rendered == exports / "page-render.png"

def test_render_preview_reports_all_office_failures(tmp_path, monkeypatch):
    # Make both candidates raise and assert their paths appear in RuntimeError.
    assert "/fake/soffice" in str(error.value)
    assert str(bundled) in str(error.value)
```

- [ ] **Step 2: Run the focused tests and verify they fail**

Run: `PYTHONPATH=. .venv/bin/pytest -q tests/test_dual_image_overlay_build_page.py -k render_preview`

Expected: FAIL because preview rendering has no fallback loop.

- [ ] **Step 3: Implement candidate selection and one-at-a-time conversion**

```python
for soffice in _office_candidates():
    try:
        with tempfile.TemporaryDirectory(prefix="cyberppt-soffice-profile-") as profile_dir:
            subprocess.run([
                str(soffice),
                f"-env:UserInstallation={Path(profile_dir).resolve().as_uri()}",
                "--headless", "--convert-to", "pdf", "--outdir", str(temp_path), str(pptx_path),
            ], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if pdf_path.exists():
            break
    except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
        failures.append(_render_failure_evidence(soffice, error))
else:
    raise RuntimeError("All LibreOffice preview attempts failed:\\n  " + "\\n  ".join(failures))
```

- [ ] **Step 4: Run focused tests and verify they pass**

Run: `PYTHONPATH=. .venv/bin/pytest -q tests/test_dual_image_overlay_build_page.py -k render_preview`

Expected: PASS.

- [ ] **Step 5: Run a real preview conversion**

Run: `PYTHONPATH=. .venv/bin/python scripts/dual_image_overlay/build_page.py --help`

Then run the existing page build command with `--render-preview`, and assert `exports/page-render.pdf` and `exports/page-render.png` exist.
