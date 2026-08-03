from pathlib import Path

from ppt_script_compiler.codex_runner import MockCodexRunner
from ppt_script_compiler.pipeline import Pipeline
from ppt_script_compiler.store import ProjectStore


APP_ROOT = Path(__file__).resolve().parents[1]


def test_mock_pipeline_end_to_end(tmp_path: Path):
    workspaces = tmp_path / "workspaces"
    store = ProjectStore.create(workspaces, "测试项目", APP_ROOT / "templates/default_profile.yaml")
    source = tmp_path / "source.md"
    source.write_text(
        "# 汇报材料\n\n## 背景\n\n存在数据分散问题。\n\n## 方案\n\n通过可信连接器提供受控API服务。",
        encoding="utf-8",
    )
    pipeline = Pipeline(APP_ROOT, store, MockCodexRunner())
    pipeline.parse_source(source)
    pipeline.run_all(semantic_audit=True)
    assert (store.root / "exports/ppt_script.md").exists()
    assert (store.root / "stages/05_audit.json").exists()
