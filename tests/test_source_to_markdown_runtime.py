from __future__ import annotations

import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / ".agents/skills/source-to-markdown/scripts/convert.py"


def _load_convert_module():
    spec = importlib.util.spec_from_file_location("source_to_markdown_convert", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_delegates_to_repository_venv_when_skill_venv_is_missing(tmp_path, monkeypatch):
    module = _load_convert_module()
    repo_root = tmp_path / "repo"
    skill_root = repo_root / ".agents/skills/source-to-markdown"
    skill_root.mkdir(parents=True)
    (repo_root / ".git").mkdir()

    repository_python = repo_root / ".venv/bin/python"
    repository_python.parent.mkdir(parents=True)
    repository_python.write_text("#!/bin/sh\nexit 17\n", encoding="utf-8")
    repository_python.chmod(0o755)

    monkeypatch.setattr(module, "ROOT", skill_root)
    monkeypatch.setattr(module, "_markitdown_available", lambda: False)
    monkeypatch.setattr(module.sys, "executable", str(tmp_path / "system-python"))
    monkeypatch.setattr(module.sys, "argv", [str(SCRIPT), "input.docx"])

    assert module._maybe_delegate_to_local_venv() == 17
