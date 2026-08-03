from __future__ import annotations

import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from .state import STAGE_FILES
from .utils import read_json, read_yaml, write_json, write_yaml


def _bullets(items: list[str], indent: str = "- ") -> list[str]:
    return [f"{indent}{item}" for item in items if str(item).strip()]


def render_markdown(project: Path) -> str:
    profile = read_yaml(project / "config/project.yaml", {}) or {}
    assets_doc = read_json(project / STAGE_FILES["assets"], {})
    plan = read_json(project / STAGE_FILES["plan"], {})
    copy = read_json(project / STAGE_FILES["copy"], {})
    visual = read_json(project / STAGE_FILES["visual"], {})
    audit = read_json(project / STAGE_FILES["audit"], {})
    asset_map = {a["asset_id"]: a for a in assets_doc.get("assets", [])}
    copy_map = {p["page_id"]: p for p in copy.get("pages", [])}
    visual_map = {p["page_id"]: p for p in visual.get("pages", [])}
    lines: list[str] = [f"# {plan.get('presentation_title') or assets_doc.get('document', {}).get('title', 'PPT脚本')}", "", "## 脚本总控", ""]
    lines += [
        f"- 汇报主张：{plan.get('overall_thesis', '')}",
        f"- 汇报对象：{profile.get('presentation', {}).get('audience', '')}",
        f"- 汇报用途：{profile.get('presentation', {}).get('purpose', '')}",
        f"- 页面数量：{len(plan.get('pages', []))}",
        f"- 画面比例：{profile.get('visual', {}).get('aspect_ratio', '16:9')}",
        f"- 字体：{profile.get('visual', {}).get('font', 'Microsoft YaHei')}",
        "- 标题与副标题由PPT文字层处理，不在图片中绘制。", "",
        "### 全局内容约束", "",
    ]
    lines.extend(_bullets(profile.get("content", {}).get("rules", [])))
    lines += ["", "### 全局视觉约束", ""]
    lines.extend(_bullets(profile.get("visual", {}).get("requirements", [])))
    lines.extend(_bullets([f"避免：{x}" for x in profile.get("visual", {}).get("avoid", [])]))
    lines.append("")
    for page in sorted(plan.get("pages", []), key=lambda p: p.get("order", 0)):
        pid = page["page_id"]
        page_copy = copy_map.get(pid, {})
        page_visual = visual_map.get(pid, {})
        title = page_copy.get("title") or page.get("page_role") or pid
        lines += ["---", "", f"## 第{page.get('order')}页｜{title}", "", "### 页面控制", ""]
        lines += [
            f"- 页面编号：{pid}", f"- 页面类型：{page.get('page_type', '')}", f"- 页面职能：{page.get('page_role', '')}",
            f"- 页面使命：{page.get('page_mission', '')}", f"- 核心判断：{page.get('core_judgment', '')}",
            f"- 观众问题：{page.get('audience_question', '')}", f"- 逻辑关系：{page.get('relationship_type', '')}",
            f"- 与前页关系：{page.get('previous_page_relation', '')}", f"- 与后页关系：{page.get('next_page_relation', '')}",
        ]
        if page.get("must_not_include"):
            lines.append("- 本页不得混入：" + "；".join(page.get("must_not_include", [])))
        lock = page_copy.get("content_lock", {})
        lines += ["", "### 内容锁定", "", f"- 标题语义：{lock.get('title_meaning', '')}", f"- 锁定判断：{lock.get('core_judgment', '')}"]
        for key, label in [("required_facts", "必须保留事实"), ("required_terms", "必须使用术语"), ("prohibited_rewrites", "禁止改写"), ("prohibited_additions", "禁止补充")]:
            if lock.get(key):
                lines.append(f"- {label}：" + "；".join(lock[key]))
        lines += ["", "### 上屏文字", "", f"- 标题：{page_copy.get('title', '')}"]
        if page_copy.get("subtitle"):
            lines.append(f"- 副标题：{page_copy.get('subtitle')}")
        for module in page_copy.get("modules", []):
            lines.append(f"- 模块｜{module.get('heading', '')}")
            lines.extend([f"  - {body}" for body in module.get("body_lines", [])])
        if page_copy.get("annotations"):
            lines.append("- 注释：")
            lines.extend([f"  - {x}" for x in page_copy.get("annotations", [])])
        if page_copy.get("conclusion"):
            lines.append(f"- 结论落点：{page_copy.get('conclusion')}")
        lines += ["", "### 视觉意图与构图", ""]
        lines += [
            f"- 视觉意图类型：{page_visual.get('visual_intent_type', '')}", f"- 视觉主张：{page_visual.get('visual_thesis', '')}",
            f"- 主视觉载体：{page_visual.get('dominant_carrier', '')}", f"- 行业场景锚点：{page_visual.get('scene_anchor', '')}",
            f"- 构图说明：{page_visual.get('composition', '')}",
        ]
        if page_visual.get("reading_path"):
            lines.append("- 阅读路径：" + " → ".join(page_visual["reading_path"]))
        lines.append(f"- 第一视觉重点：{page_visual.get('emphasis_primary', '')}")
        if page_visual.get("emphasis_secondary"):
            lines.append("- 次级重点：" + "；".join(page_visual["emphasis_secondary"]))
        if page_visual.get("text_embedding"):
            lines.append("- 文字嵌入：" + "；".join(page_visual["text_embedding"]))
        if page_visual.get("imagery"):
            lines.append("- 图像要求：" + "；".join(page_visual["imagery"]))
        if page_visual.get("layout_regions"):
            lines.append("- 布局区域：")
            for region in sorted(page_visual["layout_regions"], key=lambda r: r.get("z_order", 0)):
                lines.append(f"  - {region.get('region_id')}｜{region.get('purpose')}｜{region.get('position')}｜{region.get('relative_size')}｜内容引用：{region.get('content_ref')}")
        if page_visual.get("avoid"):
            lines.append("- 本页避免：" + "；".join(page_visual["avoid"]))
        lines += ["", "### 生图提示词", "", page_visual.get("generation_prompt", ""), "", "### 来源追溯", ""]
        for aid in page.get("source_asset_ids", []):
            asset = asset_map.get(aid, {})
            lines.append(f"- {aid}｜{asset.get('content', '')}｜来源：{'、'.join(asset.get('source_refs', []))}")
        lines.append("")
    if audit:
        summary = audit.get("summary", {})
        lines += ["---", "", "## 质量审查摘要", "", f"- 是否通过：{'是' if summary.get('pass') else '否'}",
                  f"- 原文忠实度：{summary.get('source_fidelity_score', '')}", f"- 核心覆盖度：{summary.get('coverage_score', '')}",
                  f"- 页面纯度：{summary.get('page_purity_score', '')}", f"- 视觉一致性：{summary.get('visual_alignment_score', '')}",
                  f"- 审查意见：{summary.get('overall_comment', '')}"]
        if audit.get("findings"):
            lines += ["", "### 审查问题", ""]
            for finding in audit["findings"]:
                loc = finding.get("page_id") or finding.get("asset_id") or "全局"
                lines.append(f"- [{finding.get('severity')}] {finding.get('code')}｜{loc}｜{finding.get('description')}｜建议：{finding.get('recommendation')}")
    return "\n".join(lines).strip() + "\n"


def export_project(project: Path) -> dict[str, Path]:
    exports = project / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    md_path = exports / "ppt_script.md"
    md_path.write_text(render_markdown(project), encoding="utf-8")
    bundle: dict[str, Any] = {
        "profile": read_yaml(project / "config/project.yaml", {}),
        "source": read_json(project / "source/source_blocks.json", {}),
        "information_assets": read_json(project / STAGE_FILES["assets"], {}),
        "page_plan": read_json(project / STAGE_FILES["plan"], {}),
        "screen_copy": read_json(project / STAGE_FILES["copy"], {}),
        "visual_plan": read_json(project / STAGE_FILES["visual"], {}),
        "semantic_audit": read_json(project / STAGE_FILES["audit"], {}),
    }
    json_path = exports / "ppt_script_bundle.json"
    yaml_path = exports / "ppt_script_bundle.yaml"
    write_json(json_path, bundle)
    write_yaml(yaml_path, bundle)
    zip_path = exports / f"ppt-script-project-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(p for p in project.rglob("*") if p.is_file() and p != zip_path):
            zf.write(path, path.relative_to(project).as_posix())
    return {"markdown": md_path, "json": json_path, "yaml": yaml_path, "zip": zip_path}
