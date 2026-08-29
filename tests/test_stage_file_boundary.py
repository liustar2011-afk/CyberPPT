from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
from cyberppt.stage02_input import INPUT_JSON, build_stage02_input, prepare_stage02_input

SCRIPT="""## P01 文件边界
- 页面类型：内容页
- 页面标题：文件边界
- 内容负载：standard
- 页面使命：说明两个阶段通过文件对接
- 核心结论：Stage2 只消费脚本文件

### 完整文字稿
Stage2 只读取当前输入文件，并从该文件建立自己的视觉生产状态。

### 上屏文字
输入文件：Final Script 是唯一跨阶段输入
  Stage2 自行派生视觉结构和生产产物

### 视觉结构
输入文件进入视觉生产链，形成完整页面视觉稿。
"""

def test_stage2_input_is_portable_and_ignores_adjacent_producer_state():
    with TemporaryDirectory() as directory:
        root=Path(directory); producer=root/"producer"; producer.mkdir(); script=producer/"final-script.md"; script.write_text(SCRIPT,encoding="utf-8")
        (producer/"deck-plan.json").write_text('{"pages":[]}',encoding="utf-8"); (producer/"foundation.json").write_text('{"facts":[]}',encoding="utf-8")
        stage2=root/"stage2"; payload=build_stage02_input(stage2,script=script)
        assert payload["schema"]=="cyberppt.stage02_script_input.v1"; assert payload["pages"][0]["title"]=="文件边界"; assert payload["pages"][0]["content_load"]=="standard"; assert payload["source_bindings"]["script"]["source_path"]==str(script.resolve())
        assert (stage2/"workbench/inputs/final-script.md").is_file(); assert prepare_stage02_input(stage2,script=script,reuse_current=True)["status"]=="passed"; assert (stage2/INPUT_JSON).is_file()

def test_formal_stage2_runtime_has_no_stage1_artifact_dependency():
    repo=Path(__file__).resolve().parents[1]
    files=[repo/"cyberppt/stage02_input.py",repo/"cyberppt/page_artifact_spec.py",repo/"scripts/imagegen_pipeline/page_manifest.py"]
    files.extend(sorted((repo/"cyberppt/visual_stage").glob("*.py")))
    files.extend(sorted((repo/"cyberppt/stage02_production").glob("*.py")))
    text="\n".join(path.read_text(encoding="utf-8") for path in files)
    assert "from cyberppt.stage02_handoff" not in text; assert "parse_script_path" not in (repo/"cyberppt/stage02_input.py").read_text(encoding="utf-8"); assert "script_semantic_digest" not in text
    for token in ("deck-plan.json","foundation.json","source-truth.json","outline.json"): assert token not in text
