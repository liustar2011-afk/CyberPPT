# Stage 5 Page-Script Prompt Resource Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move Stage 5's static page-script writing guidance from Python into a reviewable Markdown resource without changing generated authoring input.

**Architecture:** A repository-root-relative `Path` constant identifies a single Stage 1 Markdown resource. `prepare_page_script_input()` reads its UTF-8 lines as the static prefix, then preserves the existing per-page dynamic append loop unchanged. Tests pin the existing fixture output hash and prove the function consumes the resource instead of a duplicate literal.

**Tech Stack:** Python 3, `pathlib.Path`, `unittest`, `unittest.mock`, pytest.

## Global Constraints

- Preserve all Stage 5 writing-rule wording, ordering, blank lines, CLI parameters, and generated output exactly.
- Create no project control artifacts, manifests, receipts, or alternate workflow paths.
- Keep dynamic Outline and Source Truth page data in `prepare_page_script_input()`.
- Store the resource at `vendor/skills/ppt-script/system-prompt/stage1/61-page-script-authoring.md` as UTF-8 Markdown.
- Load a missing resource through a path-bearing `FileNotFoundError`; do not silently omit the static contract.
- Preserve unrelated dirty-worktree changes; stage only files named by each task.

---

### Task 1: Establish resource loading behavior and its regression tests

**Files:**
- Modify: `tests/test_prepare_stage01_input.py:1-175`
- Modify: `cyberppt/commands/prepare_stage01_input.py:1-10,265-432`
- Create: `vendor/skills/ppt-script/system-prompt/stage1/61-page-script-authoring.md`

**Interfaces:**
- Consumes: existing `prepare_page_script_input(project: Path, page_id: str = "") -> str`.
- Produces: `PAGE_SCRIPT_AUTHORING_RULES_PATH: Path`, pointing to the sole static Stage 5 rule resource; `prepare_page_script_input()` returns the resource prefix followed by its unchanged page-specific context.

- [ ] **Step 1: Write the failing resource-consumption and missing-resource tests**

  Add `from unittest.mock import patch` and import `PAGE_SCRIPT_AUTHORING_RULES_PATH`. Add these test methods to `PrepareStage01InputTests`:

  ```python
  def test_prepare_page_script_input_reads_static_rules_from_resource(self) -> None:
      resource = self.project / "page-script-rules.md"
      resource.write_text("# Resource marker\n\nunique resource guidance\n", encoding="utf-8")

      with patch(
          "cyberppt.commands.prepare_stage01_input.PAGE_SCRIPT_AUTHORING_RULES_PATH",
          resource,
      ):
          text = prepare_page_script_input(self.project, "p04")

      self.assertTrue(text.startswith("# Resource marker\n\nunique resource guidance\n"))
      self.assertIn("## p04 建设基础", text)

  def test_prepare_page_script_input_reports_missing_rules_resource(self) -> None:
      missing = self.project / "missing-page-script-rules.md"

      with patch(
          "cyberppt.commands.prepare_stage01_input.PAGE_SCRIPT_AUTHORING_RULES_PATH",
          missing,
      ):
          with self.assertRaisesRegex(FileNotFoundError, str(missing)):
              prepare_page_script_input(self.project, "p04")
  ```

- [ ] **Step 2: Run the two tests to verify they fail before the migration**

  Run:

  ```bash
  PYTHONPATH=. pytest -q tests/test_prepare_stage01_input.py -k "reads_static_rules_from_resource or reports_missing_rules_resource"
  ```

  Expected: collection/import failure because `PAGE_SCRIPT_AUTHORING_RULES_PATH` does not yet exist.

- [ ] **Step 3: Create the Markdown resource by moving the static prompt verbatim**

  Create `vendor/skills/ppt-script/system-prompt/stage1/61-page-script-authoring.md`. Copy, byte-for-byte at the text level, every string emitted by the `lines = [` block in `prepare_page_script_input()` before `for page in pages:`. Preserve its initial heading `# Page script authoring input`, all blank lines, all embedded newlines (including the canonical hierarchy example), and end the file with exactly one newline.

- [ ] **Step 4: Implement minimal resource loading and retain the dynamic loop**

  After imports, define the repository-root-relative path:

  ```python
  PAGE_SCRIPT_AUTHORING_RULES_PATH = (
      Path(__file__).resolve().parents[2]
      / "vendor/skills/ppt-script/system-prompt/stage1/61-page-script-authoring.md"
  )
  ```

  At the start of `prepare_page_script_input()`, replace the large static literal list with:

  ```python
  if not PAGE_SCRIPT_AUTHORING_RULES_PATH.is_file():
      raise FileNotFoundError(
          f"required page-script authoring rules do not exist: "
          f"{PAGE_SCRIPT_AUTHORING_RULES_PATH}"
      )
  lines = PAGE_SCRIPT_AUTHORING_RULES_PATH.read_text(encoding="utf-8").splitlines()
  ```

  Leave the existing `for page in pages:` loop and terminal `"\n".join(lines).rstrip() + "\n"` unchanged. This preserves the resource's trailing-newline normalization and ensures the patched-resource test has the same consumer path.

- [ ] **Step 5: Run the focused tests to verify they pass**

  Run:

  ```bash
  PYTHONPATH=. pytest -q tests/test_prepare_stage01_input.py -k "reads_static_rules_from_resource or reports_missing_rules_resource"
  ```

  Expected: `2 passed`.

- [ ] **Step 6: Commit the independently testable resource-loader change**

  ```bash
  git add cyberppt/commands/prepare_stage01_input.py tests/test_prepare_stage01_input.py vendor/skills/ppt-script/system-prompt/stage1/61-page-script-authoring.md
  git commit -m "refactor(stage01): externalize page script rules"
  ```

### Task 2: Lock byte-for-byte compatibility and verify the production-facing command

**Files:**
- Modify: `tests/test_prepare_stage01_input.py:72-175`
- Verify: `cyberppt/commands/prepare_stage01_input.py:265-432`
- Verify: `cyberppt/cli.py:338-349`

**Interfaces:**
- Consumes: `prepare_page_script_input()` and its unchanged CLI wrapper `_prepare_page_script_input_command(args: argparse.Namespace) -> int`.
- Produces: a fixture-backed compatibility guarantee for the command's full text output.

- [ ] **Step 1: Write the failing anti-duplication and output-baseline tests**

  Add `import hashlib`, `import inspect`, `import subprocess`, and `import sys`. In `PrepareStage01InputTests`, add:

  ```python
  def test_prepare_page_script_input_has_no_embedded_static_rule_copy(self) -> None:
      from cyberppt.commands import prepare_stage01_input

      source = inspect.getsource(prepare_stage01_input.prepare_page_script_input)
      self.assertNotIn("Never strengthen the core_message", source)
      self.assertNotIn("Write the completed pages directly", source)

  def test_prepare_page_script_input_matches_pre_resource_output_baseline(self) -> None:
      text = prepare_page_script_input(self.project, "p04")

      self.assertEqual(len(text), 13826)
      self.assertEqual(
          hashlib.sha256(text.encode("utf-8")).hexdigest(),
          "9fcd8334762bc4b9788199384902fc428590b56a743805a349818d721deef5fd",
      )

  def test_prepare_page_script_input_cli_emits_resource_backed_output(self) -> None:
      result = subprocess.run(
          [
              sys.executable,
              "-m",
              "cyberppt",
              "prepare-page-script-input",
              str(self.project),
              "--page",
              "p04",
          ],
          cwd=Path(__file__).resolve().parents[1],
          text=True,
          capture_output=True,
          check=False,
      )

      self.assertEqual(result.returncode, 0, result.stderr)
      self.assertTrue(result.stdout.startswith("# Page script authoring input\n"))
      self.assertIn("## p04 建设基础", result.stdout)
  ```

- [ ] **Step 2: Run these tests to verify the anti-duplication assertion fails before deleting the literal**

  Run:

  ```bash
  PYTHONPATH=. pytest -q tests/test_prepare_stage01_input.py -k "no_embedded_static_rule_copy or pre_resource_output_baseline"
  ```

  Expected: the anti-duplication test fails while the old literal remains; the baseline test passes and records the pre-migration contract.

- [ ] **Step 3: Remove the migrated literal only after confirming the resource contains it**

  Delete the static rule strings from `prepare_page_script_input()` so that the resource loader from Task 1 is its only static-rule source. Do not change any fields appended in the page loop or the CLI wrapper.

- [ ] **Step 4: Run the full targeted test module**

  Run:

  ```bash
  PYTHONPATH=. pytest -q tests/test_prepare_stage01_input.py
  ```

  Expected: all tests pass, including the two existing page-input tests, missing-resource handling, resource consumption, anti-duplication, and the 13,826-character SHA-256 compatibility baseline.

- [ ] **Step 5: Verify the CLI consumer through the fixture-backed test**

  The new `test_prepare_page_script_input_cli_emits_resource_backed_output` invokes `python -m cyberppt prepare-page-script-input` with the test's real temporary project path. Its assertions require exit code `0`, the canonical heading, and the expected page section; no hand-created project or placeholder path is permitted.

- [ ] **Step 6: Commit the compatibility contract**

  ```bash
  git add tests/test_prepare_stage01_input.py
  git commit -m "test(stage01): lock page script prompt output"
  ```

## Final Verification

- [ ] Run `git diff --check` for the three implementation files.
- [ ] Run `PYTHONPATH=. pytest -q tests/test_prepare_stage01_input.py` and record the exact pass count.
- [ ] Inspect `git status --short` and confirm only task-scoped files were staged in each commit; leave unrelated pre-existing changes untouched.
- [ ] Confirm the resource file is the only location containing both `Never strengthen the core_message` and `Write the completed pages directly` within production source and resource paths.
