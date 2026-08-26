from pathlib import Path

from ppt_script_compiler.extractors import extract_markdown, chunk_blocks


def test_markdown_extraction(tmp_path: Path):
    path = tmp_path / "sample.md"
    path.write_text("# 标题\n\n## 背景\n\n第一段。\n\n第二段。", encoding="utf-8")
    result = extract_markdown(path)
    assert result.metadata["block_count"] == 4
    assert result.blocks[0]["source_id"] == "S00001"
    assert result.blocks[2]["section_path"] == ["标题", "背景"]


def test_chunk_blocks_preserves_all_blocks():
    blocks = [{"source_id": f"S{i:05d}", "text": "内容" * 100} for i in range(1, 11)]
    chunks = chunk_blocks(blocks, max_chars=1000)
    flattened = [b for chunk in chunks for b in chunk]
    assert flattened == blocks
    assert len(chunks) > 1
