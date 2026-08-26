from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import streamlit as st
import yaml

from ppt_script_compiler.codex_runner import CodexError, CodexRunner, MockCodexRunner
from ppt_script_compiler.pipeline import Pipeline
from ppt_script_compiler.store import ProjectStore, STAGE_ORDER, list_projects
from ppt_script_compiler.utils import read_json, stable_hash
from ppt_script_compiler.validators import stage_findings, validate_schema


APP_ROOT = Path(__file__).resolve().parent
WORKSPACES_ROOT = APP_ROOT / "workspaces"
DEFAULT_PROFILE = APP_ROOT / "templates/default_profile.yaml"
SCHEMA_BY_STAGE = {
    "assets": APP_ROOT / "schemas/assets.schema.json",
    "plan": APP_ROOT / "schemas/page_plan.schema.json",
    "copy": APP_ROOT / "schemas/screen_copy.schema.json",
    "visual": APP_ROOT / "schemas/visual_plan.schema.json",
    "audit": APP_ROOT / "schemas/audit.schema.json",
}
STAGE_LABELS = {
    "source": "源材料",
    "assets": "信息资产",
    "plan": "页面规划",
    "copy": "上屏文字",
    "visual": "视觉构图",
    "audit": "质量审查",
    "export": "导出",
}


st.set_page_config(page_title="PPT脚本编译器", page_icon="📑", layout="wide")
st.markdown(
    """
<style>
.block-container {padding-top: 1.4rem; padding-bottom: 3rem;}
.small-note {color:#5f6b7a;font-size:0.9rem;}
.status-ok {background:#eaf7ef;padding:0.45rem 0.65rem;border-radius:0.45rem;}
.status-warn {background:#fff4df;padding:0.45rem 0.65rem;border-radius:0.45rem;}
.status-pending {background:#f1f3f5;padding:0.45rem 0.65rem;border-radius:0.45rem;}
</style>
""",
    unsafe_allow_html=True,
)


def show_findings(findings: list[Any]) -> None:
    if not findings:
        st.success("本地校验未发现问题。")
        return
    errors = sum(1 for f in findings if f.severity == "error")
    warnings = sum(1 for f in findings if f.severity == "warning")
    st.warning(f"本地校验：{errors}项错误，{warnings}项警告，共{len(findings)}项。")
    rows = [
        {
            "级别": f.severity,
            "代码": f.code,
            "页面": f.page_id,
            "资产": f.asset_id,
            "问题": f.description,
            "建议": f.recommendation,
        }
        for f in findings
    ]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def make_runner(store: ProjectStore, demo_mode: bool):
    if demo_mode:
        return MockCodexRunner()
    settings = store.settings()
    return CodexRunner(
        codex_bin=settings.get("codex_bin") or None,
        model=settings.get("model") or None,
        reasoning_effort=settings.get("reasoning_effort") or "high",
        timeout_seconds=int(settings.get("timeout_seconds", 1800)),
    )


def stage_editor(stage: str, store: ProjectStore) -> None:
    path = store.stage_path(stage)
    if not path.exists():
        st.info("本阶段尚未生成。")
        return
    payload = read_json(path, {})
    editor_key = f"editor_{store.root.name}_{stage}_{path.stat().st_mtime_ns}"
    raw = st.text_area(
        "结构化结果（可人工修订）",
        value=json.dumps(payload, ensure_ascii=False, indent=2),
        height=520,
        key=editor_key,
    )
    locked = bool(store.stage_status(stage).get("locked"))
    col1, col2, col3 = st.columns([1, 1, 4])
    with col1:
        if st.button("保存修订", key=f"save_{store.root.name}_{stage}", disabled=locked):
            try:
                revised = json.loads(raw)
                schema_errors = validate_schema(revised, SCHEMA_BY_STAGE[stage])
                if schema_errors:
                    show_findings(schema_errors)
                else:
                    store.save_stage_json(stage, revised, input_hash=stable_hash({"manual": revised}), manual=True)
                    st.success("已保存，并将后续阶段标记为需要重新生成。")
                    st.rerun()
            except json.JSONDecodeError as exc:
                st.error(f"JSON格式错误：{exc}")
    with col2:
        label = "解除锁定" if locked else "锁定阶段"
        if st.button(label, key=f"lock_{store.root.name}_{stage}"):
            store.set_locked(stage, not locked)
            st.rerun()
    findings = stage_findings(stage, store.root, APP_ROOT / "schemas", store.profile())
    show_findings(findings)


st.title("PPT脚本编译器")
st.caption("源材料 → 信息资产 → 页面规划 → 上屏文字 → 视觉构图 → 质量审查 → PPT脚本")

WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)
projects = list_projects(WORKSPACES_ROOT)

with st.sidebar:
    st.header("项目")
    with st.expander("新建项目", expanded=not projects):
        new_name = st.text_input("项目名称", placeholder="例如：电力行业数据服务汇报")
        if st.button("创建项目", use_container_width=True, disabled=not new_name.strip()):
            store = ProjectStore.create(WORKSPACES_ROOT, new_name, DEFAULT_PROFILE)
            st.session_state["selected_project"] = store.root.name
            st.rerun()

    project_names = [p.name for p in projects]
    selected_default = st.session_state.get("selected_project")
    default_index = project_names.index(selected_default) if selected_default in project_names else 0
    selected = st.selectbox("打开项目", project_names, index=default_index if project_names else None, placeholder="请先创建项目")
    if selected:
        st.session_state["selected_project"] = selected

if not selected:
    st.info("请在左侧新建项目。")
    st.stop()

store = ProjectStore.open(WORKSPACES_ROOT / selected)

with st.sidebar:
    st.divider()
    st.header("Codex设置")
    settings = store.settings()
    codex_bin = st.text_input("Codex命令路径", value=settings.get("codex_bin", ""), placeholder="留空则自动查找 codex")
    model = st.text_input("模型覆盖", value=settings.get("model", ""), placeholder="留空使用Codex默认模型")
    reasoning = st.selectbox("推理强度", ["medium", "high", "xhigh"], index=["medium", "high", "xhigh"].index(settings.get("reasoning_effort", "high") if settings.get("reasoning_effort", "high") in ["medium", "high", "xhigh"] else "high"))
    timeout = st.number_input("单阶段超时（秒）", min_value=120, max_value=7200, value=int(settings.get("timeout_seconds", 1800)), step=60)
    demo_mode = st.checkbox("演示模式（不调用Codex）", value=False, help="仅用于验证安装和流程，不适合真实材料。")
    if st.button("保存设置", use_container_width=True):
        store.save_settings({"codex_bin": codex_bin.strip(), "model": model.strip(), "reasoning_effort": reasoning, "timeout_seconds": int(timeout)})
        st.success("设置已保存。")
    if st.button("检查Codex", use_container_width=True):
        runner = make_runner(store, demo_mode=False)
        probe = runner.probe(force=True)
        if probe.installed and probe.logged_in:
            st.success(f"可用：{probe.version}\n\n{probe.login_status}")
        elif probe.installed:
            st.warning(f"已安装但未登录：{probe.version}\n\n请在终端运行 `codex login`。")
        else:
            st.error("未找到Codex CLI。请运行 setup_windows.bat，或先安装Codex。")

    st.divider()
    st.header("阶段状态")
    for stage in STAGE_ORDER:
        info = store.stage_status(stage)
        status = info.get("status", "pending")
        locked = " 🔒" if info.get("locked") else ""
        icon = "✅" if status == "completed" else "⚠️" if status == "stale" else "○"
        st.write(f"{icon} {STAGE_LABELS[stage]}{locked}")

runner = make_runner(store, demo_mode)
pipeline = Pipeline(APP_ROOT, store, runner)

meta = store.metadata()
st.subheader(meta.get("name", store.root.name))
status_cols = st.columns(7)
for col, stage in zip(status_cols, STAGE_ORDER):
    info = store.stage_status(stage)
    status = info.get("status", "pending")
    css = "status-ok" if status == "completed" else "status-warn" if status == "stale" else "status-pending"
    col.markdown(f'<div class="{css}"><b>{STAGE_LABELS[stage]}</b><br>{status}</div>', unsafe_allow_html=True)

run_col, audit_col, export_col = st.columns([2, 1, 1])
with run_col:
    if st.button("一键运行至最终脚本", type="primary", use_container_width=True, disabled=store.stage_status("source").get("status") != "completed"):
        try:
            with st.status("正在执行分阶段编译…", expanded=True) as status:
                def progress(message: str) -> None:
                    status.write(message)
                pipeline.run_all(progress=progress, semantic_audit=store.profile().get("quality", {}).get("run_semantic_audit", True))
                status.update(label="编译完成", state="complete")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
with audit_col:
    if st.button("重跑审查", use_container_width=True, disabled=store.stage_status("visual").get("status") != "completed"):
        try:
            with st.status("正在审查…") as status:
                pipeline.run_audit(progress=status.write, semantic=True)
                status.update(label="审查完成", state="complete")
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
with export_col:
    if st.button("重新导出", use_container_width=True, disabled=store.stage_status("visual").get("status") != "completed"):
        try:
            pipeline.export()
            st.rerun()
        except Exception as exc:
            st.error(str(exc))

source_tab, profile_tab, assets_tab, plan_tab, copy_tab, visual_tab, audit_tab, export_tab = st.tabs(
    ["1 源材料", "配置", "2 信息资产", "3 页面规划", "4 上屏文字", "5 视觉构图", "6 质量审查", "7 导出"]
)

with source_tab:
    st.markdown("### 上传并解析源材料")
    uploaded = st.file_uploader("支持 DOCX、PDF、Markdown、TXT、PPTX", type=["docx", "pdf", "md", "markdown", "txt", "pptx"])
    if uploaded is not None:
        if st.button("解析源材料", type="primary"):
            upload_path = store.root / "source/original" / Path(uploaded.name).name
            upload_path.parent.mkdir(parents=True, exist_ok=True)
            upload_path.write_bytes(uploaded.getbuffer())
            metadata = pipeline.parse_source(upload_path)
            st.success(f"解析完成：{metadata['block_count']}个来源块，约{metadata['character_count']}字。")
            st.rerun()
    source_data = read_json(store.root / "source/source_blocks.json", {})
    if source_data:
        metadata = source_data.get("metadata", {})
        st.json(metadata, expanded=False)
        blocks = source_data.get("blocks", [])
        preview = [{"编号": b["source_id"], "类型": b["kind"], "章节": " > ".join(b.get("section_path", [])), "内容": b["text"][:180]} for b in blocks[:200]]
        st.dataframe(preview, use_container_width=True, hide_index=True)
        if len(blocks) > 200:
            st.caption(f"界面仅预览前200个来源块，完整内容保存在 source/source_blocks.json。")

with profile_tab:
    st.markdown("### 项目配置")
    profile_text = st.text_area("YAML配置", value=store.profile_path.read_text(encoding="utf-8"), height=650)
    if st.button("保存配置"):
        try:
            parsed = yaml.safe_load(profile_text)
            if not isinstance(parsed, dict):
                raise ValueError("配置根节点必须是对象。")
            store.save_profile(parsed)
            st.success("配置已保存，后续阶段已标记为需要重新生成。")
            st.rerun()
        except Exception as exc:
            st.error(f"配置格式错误：{exc}")


def stage_tab(stage: str, tab, run_method):
    with tab:
        st.markdown(f"### {STAGE_LABELS[stage]}")
        ready, reason = store.ready_for(stage)
        locked = bool(store.stage_status(stage).get("locked"))
        if locked:
            st.info("本阶段已锁定。解除锁定后才能重新生成。")
        if st.button(f"生成{STAGE_LABELS[stage]}", type="primary", disabled=not ready or locked, key=f"run_{stage}"):
            try:
                with st.status(f"正在生成{STAGE_LABELS[stage]}…", expanded=True) as status:
                    result = run_method(progress=status.write)
                    status.update(label=f"{STAGE_LABELS[stage]}生成完成", state="complete")
                show_findings(result.findings)
                st.rerun()
            except (CodexError, RuntimeError, ValueError) as exc:
                st.error(str(exc))
        if not ready:
            st.caption(reason)
        stage_editor(stage, store)


stage_tab("assets", assets_tab, pipeline.run_assets)
stage_tab("plan", plan_tab, pipeline.run_plan)
stage_tab("copy", copy_tab, pipeline.run_copy)
stage_tab("visual", visual_tab, pipeline.run_visual)

with audit_tab:
    st.markdown("### 质量审查")
    ready, reason = store.ready_for("audit")
    if st.button("执行语义审查", type="primary", disabled=not ready):
        try:
            with st.status("正在执行独立审查…", expanded=True) as status:
                result = pipeline.run_audit(progress=status.write, semantic=True)
                status.update(label="质量审查完成", state="complete")
            show_findings(result.findings)
            st.rerun()
        except Exception as exc:
            st.error(str(exc))
    if not ready:
        st.caption(reason)
    if store.stage_path("audit").exists():
        audit = read_json(store.stage_path("audit"), {})
        st.json(audit.get("summary", {}), expanded=True)
        findings = audit.get("findings", [])
        if findings:
            st.dataframe(findings, use_container_width=True, hide_index=True)
        stage_editor("audit", store)

with export_tab:
    st.markdown("### 导出结果")
    if store.stage_status("visual").get("status") == "completed":
        if st.button("生成导出文件", type="primary"):
            try:
                pipeline.export()
                st.rerun()
            except Exception as exc:
                st.error(str(exc))
    exports_dir = store.root / "exports"
    files = [p for p in exports_dir.glob("*") if p.is_file()]
    for path in sorted(files, key=lambda p: p.stat().st_mtime, reverse=True):
        mime = "application/zip" if path.suffix == ".zip" else "application/json" if path.suffix == ".json" else "text/markdown" if path.suffix == ".md" else "text/yaml"
        st.download_button(f"下载 {path.name}", data=path.read_bytes(), file_name=path.name, mime=mime, key=f"download_{path.name}_{path.stat().st_mtime_ns}")
    script_path = exports_dir / "ppt_script.md"
    if script_path.exists():
        st.markdown("### 最终脚本预览")
        st.markdown(script_path.read_text(encoding="utf-8"))
