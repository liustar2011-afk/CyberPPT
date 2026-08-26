from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .utils import read_json, read_yaml, write_json, write_yaml


def _bullet_lines(items: list[str], indent: str = "- ") -> list[str]:
    return [f"{indent}{item}" for item in items if str(item).strip()]


def render_markdown(workspace: Path) -> str:
    profile = read_yaml(workspace / "profile.yaml", {}) or {}
    assets_doc = read_json(workspace / "stages/01_information_assets.json", {})
    plan = read_json(workspace / "stages/02_page_plan.json", {})
    copy = read_json(workspace / "stages/03_screen_copy.json", {})
    visual = read_json(workspace / "stages/04_visual_plan.json", {})
    audit = read_json(workspace / "stages/05_audit.json", {})

    asset_map = {a["asset_id"]: a for a in assets_doc.get("assets", [])}
    copy_map = {p["page_id"]: p for p in copy.get("pages", [])}
    visual_map = {p["page_id"]: p for p in visual.get("pages", [])}

    lines: list[str] = []
    lines.append(f"# {plan.get('presentation_title') or assets_doc.get('document', {}).get('title', 'PPT脚本')}")
    lines.append("")
    lines.append("## 脚本总控")
    lines.append("")
    lines.append(f"- 汇报主张：{plan.get('overall_thesis', '')}")
    lines.append(f"- 汇报对象：{profile.get('presentation', {}).get('audience', '')}")
    lines.append(f"- 汇报用途：{profile.get('presentation', {}).get('purpose', '')}")
    lines.append(f"- 页面数量：{len(plan.get('pages', []))}")
    lines.append(f"- 画面比例：{profile.get('visual_rules', {}).get('aspect_ratio', '16:9')}")
    lines.append(f"- 字体：{profile.get('visual_rules', {}).get('font', 'Microsoft YaHei')}")
    lines.append("- 标题与副标题由PPT文字层处理，不在图片中绘制。")
    lines.append("")
    lines.append("### 全局内容约束")
    lines.extend(_bullet_lines(profile.get("content_rules", [])))
    lines.append("")
    lines.append("### 全局视觉约束")
    lines.extend(_bullet_lines(profile.get("visual_rules", {}).get("requirements", [])))
    lines.extend(_bullet_lines([f"避免：{x}" for x in profile.get("visual_rules", {}).get("avoid", [])]))
    lines.append("")

    for page in sorted(plan.get("pages", []), key=lambda p: p.get("order", 0)):
        pid = page["page_id"]
        page_copy = copy_map.get(pid, {})
        page_visual = visual_map.get(pid, {})
        title = page_copy.get("title") or page.get("page_role") or pid
        lines.append(f"---\n\n## 第{page.get('order')}页｜{title}")
        lines.append("")
        lines.append("### 页面控制")
        lines.append(f"- 页面编号：{pid}")
        lines.append(f"- 页面类型：{page.get('page_type', '')}")
        lines.append(f"- 页面职能：{page.get('page_role', '')}")
        lines.append(f"- 页面使命：{page.get('page_mission', '')}")
        lines.append(f"- 核心判断：{page.get('core_judgment', '')}")
        lines.append(f"- 观众问题：{page.get('audience_question', '')}")
        lines.append(f"- 逻辑关系：{page.get('relationship_type', '')}")
        lines.append(f"- 与前页关系：{page.get('previous_page_relation', '')}")
        lines.append(f"- 与后页关系：{page.get('next_page_relation', '')}")
        if page.get("must_not_include"):
            lines.append("- 本页不得混入：" + "；".join(page.get("must_not_include", [])))
        lines.append("")

        lock = page_copy.get("content_lock", {})
        lines.append("### 内容锁定")
        lines.append(f"- 标题语义：{lock.get('title_meaning', '')}")
        lines.append(f"- 锁定判断：{lock.get('core_judgment', '')}")
        if lock.get("required_facts"):
            lines.append("- 必须保留事实：" + "；".join(lock.get("required_facts", [])))
        if lock.get("required_terms"):
            lines.append("- 必须使用术语：" + "；".join(lock.get("required_terms", [])))
        if lock.get("prohibited_rewrites"):
            lines.append("- 禁止改写：" + "；".join(lock.get("prohibited_rewrites", [])))
        if lock.get("prohibited_additions"):
            lines.append("- 禁止补充：" + "；".join(lock.get("prohibited_additions", [])))
        lines.append("")

        lines.append("### 上屏文字")
        lines.append(f"- 标题：{page_copy.get('title', '')}")
        if page_copy.get("subtitle"):
            lines.append(f"- 副标题：{page_copy.get('subtitle')}")
        for module in page_copy.get("modules", []):
            lines.append(f"- 模块｜{module.get('heading', '')}")
            for body in module.get("body_lines", []):
                lines.append(f"  - {body}")
        if page_copy.get("annotations"):
            lines.append("- 注释：")
            lines.extend([f"  - {x}" for x in page_copy.get("annotations", [])])
        if page_copy.get("conclusion"):
            lines.append(f"- 结论落点：{page_copy.get('conclusion')}")
        lines.append("")

        lines.append("### 视觉意图与构图")
        lines.append(f"- 视觉意图类型：{page_visual.get('visual_intent_type', '')}")
        lines.append(f"- 视觉主张：{page_visual.get('visual_thesis', '')}")
        lines.append(f"- 主视觉载体：{page_visual.get('dominant_carrier', '')}")
        lines.append(f"- 行业场景锚点：{page_visual.get('scene_anchor', '')}")
        lines.append(f"- 构图说明：{page_visual.get('composition', '')}")
        if page_visual.get("reading_path"):
            lines.append("- 阅读路径：" + " → ".join(page_visual.get("reading_path", [])))
        lines.append(f"- 第一视觉重点：{page_visual.get('emphasis_primary', '')}")
        if page_visual.get("emphasis_secondary"):
            lines.append("- 次级重点：" + "；".join(page_visual.get("emphasis_secondary", [])))
        if page_visual.get("text_embedding"):
            lines.append("- 文字嵌入：" + "；".join(page_visual.get("text_embedding", [])))
        if page_visual.get("imagery"):
            lines.append("- 图像要求：" + "；".join(page_visual.get("imagery", [])))
        if page_visual.get("layout_regions"):
            lines.append("- 布局区域：")
            for region in sorted(page_visual.get("layout_regions", []), key=lambda r: r.get("z_order", 0)):
                lines.append(
                    f"  - {region.get('region_id')}｜{region.get('purpose')}｜{region.get('position')}｜{region.get('relative_size')}｜内容引用：{region.get('content_ref')}"
                )
        if page_visual.get("avoid"):
            lines.append("- 本页避免：" + "；".join(page_visual.get("avoid", [])))
        lines.append("")
        lines.append("### 生图提示词")
        lines.append("")
        lines.append(page_visual.get("generation_prompt", ""))
        lines.append("")

        ids = page.get("source_asset_ids", [])
        lines.append("### 来源追溯")
        for aid in ids:
            asset = asset_map.get(aid, {})
            refs = "、".join(asset.get("source_refs", []))
            lines.append(f"- {aid}｜{asset.get('content', '')}｜来源：{refs}")
        lines.append("")

    if audit:
        summary = audit.get("summary", {})
        lines.append("---\n\n## 质量审查摘要")
        lines.append("")
        lines.append(f"- 是否通过：{'是' if summary.get('pass') else '否'}")
        lines.append(f"- 原文忠实度：{summary.get('source_fidelity_score', '')}")
        lines.append(f"- 核心覆盖度：{summary.get('coverage_score', '')}")
        lines.append(f"- 页面纯度：{summary.get('page_purity_score', '')}")
        lines.append(f"- 视觉一致性：{summary.get('visual_alignment_score', '')}")
        lines.append(f"- 审查意见：{summary.get('overall_comment', '')}")
        findings = audit.get("findings", [])
        if findings:
            lines.append("")
            lines.append("### 审查问题")
            for finding in findings:
                loc = finding.get("page_id") or finding.get("asset_id") or "全局"
                lines.append(f"- [{finding.get('severity')}] {finding.get('code')}｜{loc}｜{finding.get('description')}｜建议：{finding.get('recommendation')}")
    return "\n".join(lines).strip() + "\n"


def export_project(workspace: Path) -> dict[str, Path]:
    exports = workspace / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    script_path = exports / "ppt_script.md"
    script_path.write_text(render_markdown(workspace), encoding="utf-8")

    bundle = {
        "profile": read_yaml(workspace / "profile.yaml", {}),
        "source": read_json(workspace / "source/source_blocks.json", {}),
        "information_assets": read_json(workspace / "stages/01_information_assets.json", {}),
        "page_plan": read_json(workspace / "stages/02_page_plan.json", {}),
        "screen_copy": read_json(workspace / "stages/03_screen_copy.json", {}),
        "visual_plan": read_json(workspace / "stages/04_visual_plan.json", {}),
        "audit": read_json(workspace / "stages/05_audit.json", {})
    }
    json_path = exports / "ppt_script_bundle.json"
    yaml_path = exports / "ppt_script_bundle.yaml"
    write_json(json_path, bundle)
    write_yaml(yaml_path, bundle)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    zip_path = exports / f"ppt-script-project-{timestamp}.zip"
    include_paths = [
        workspace / "project.json",
        workspace / "profile.yaml",
        workspace / "source/source_blocks.json",
        workspace / "source/source_readable.md",
        workspace / "stages/01_information_assets.json",
        workspace / "stages/02_page_plan.json",
        workspace / "stages/03_screen_copy.json",
        workspace / "stages/04_visual_plan.json",
        workspace / "stages/05_audit.json",
        script_path,
        json_path,
        yaml_path,
    ]
    original_dir = workspace / "source/original"
    include_paths.extend([p for p in original_dir.glob("*") if p.is_file()])
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in include_paths:
            if path.exists():
                zf.write(path, path.relative_to(workspace).as_posix())
    return {"markdown": script_path, "json": json_path, "yaml": yaml_path, "zip": zip_path}
