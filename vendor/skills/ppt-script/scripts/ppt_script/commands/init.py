from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from ..cognition import initialize_cognition
from ..editorial import initialize_editorial
from ..experience import initialize_experience
from ..contracts import create_contract_scaffolds
from ..version import find_repo_root, get_version
from ..workflow import load_workflow_registry, route_workflow


DIRECTORIES = (
    "source",
    "analysis",
    "analysis/readings",
    "analysis/editorial",
    "decision",
    "outline",
    "pages",
    "review",
    "output",
    "approvals",
    "comparison",
    "contracts",
    "experience",
    "knowledge/editorial-frameworks",
)

PLACEHOLDERS = {
    "analysis/00-analysis.md": "# 材料分析\n\n> 待生成（Step 0）\n",
    "analysis/01-source-truth-map.md": "# Source Truth Map\n\n> 待生成。正式材料必须建立统一S###来源条目。\n",
    "decision/01-decision.md": "# 决策稿\n\n> 待生成（Step 1）\n",
    "outline/02-outline.md": "# 正式PPT提纲\n\n> 待生成（Step 2）\n",
    "outline/02-plan-audit.md": "# 故事线、章节与页面规划机器检查\n\n> 待运行 plan-check。\n",
    "review/04-review.md": "# 关键自检\n\n> 待生成（Step 4）\n",
    "review/05-evaluation.md": "# 100分质量评价与四道闸门\n\n> 待生成。\n",
    "review/06-speaker-notes-audit.md": "# 演讲者备注质量检查\n\n> 待运行 notes-check 或 audit。\n",
    "output/script-final.md": "# 完整PPT内容脚本\n\n> 待组装（运行 assemble 命令）\n",
    "output/script-imagegen.md": "# PPT构图输入脚本\n\n> 待组装（运行 assemble 命令）\n",
    "output/outline-index.json": '{\n  "schema": "ppt-script.outline_index.v1",\n  "pages": []\n}\n',
    "output/script-speaker-notes.md": "# 演讲者备注讲稿\n\n> 待组装（运行 assemble 命令）\n",
    "output/speaker-notes.json": '{\n  "schema": "ppt-script.speaker_notes.v1",\n  "pages": []\n}\n',
}


def initialize_project(projects_dir: Path, project_name: str) -> Path:
    project = projects_dir / project_name
    if project.exists():
        raise FileExistsError(f"项目已存在：{project}")
    for name in DIRECTORIES:
        (project / name).mkdir(parents=True, exist_ok=True)
    for relative, content in PLACEHOLDERS.items():
        (project / relative).write_text(content, encoding="utf-8")
    analysis_template = find_repo_root() / "templates/source-analysis.md"
    if analysis_template.is_file():
        (project / "analysis/00-analysis.md").write_text(
            analysis_template.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    semantic_template = find_repo_root() / "templates/semantic-understanding.md"
    if semantic_template.is_file():
        (project / "analysis/00-semantic-understanding.md").write_text(
            semantic_template.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
    (project / "pages/README.md").write_text(
        "# 页面文件目录\n\n每页一个 MD 文件，命名格式：`p01-封面.md`。\n",
        encoding="utf-8",
    )
    now = datetime.now()
    version = get_version()
    registry = load_workflow_registry(find_repo_root() / "config/workflow-routes.yaml")
    route = route_workflow(registry, task_type="full-presentation")
    meta = {
        "name": project_name,
        "created": now.isoformat(),
        "stage": "initialized",
        "source_files": [],
        "interaction_mode": "gated",
        "batch_pages": 3,
        "source_truth_mode": "full",
        "context_mode": "deep",
        "context_source_char_limit": 120000,
        "context_artifact_char_limit": 120000,
        "semantic_gate_required": True,
        "understanding_gate_required": True,
        "experience_mode": "enabled",
        "experience_case_limit": 5,
        "editorial_mode": "chief-editor",
        "editorial_gate_required": True,
        "editorial_contract_version": 2,
        "editorial_migration_status": "current",
        "editorial_auto_rework_limit": 2,
        "editorial_case_status_allowed": ["approved"],
        "skill_version": version,
        "task_type": route.task_type,
        "source_state": route.source_state,
        "primary_goal": route.primary_goal,
        "workflow_state": "INITIALIZED",
        "workflow": list(route.stages),
        "writing_profile": "government-soe-formal",
        "report_subtype": "work-report",
        "decision_intent": "inform",
        "audience_level": "executive-leadership",
        "project_phase": "planning",
        "speaker_notes_enabled": True,
        "speaker_notes_required_for_substantive": True,
        "speaker_notes_default_seconds": 60,
        "target_duration_minutes": None,
    }
    (project / "project.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    create_contract_scaffolds(project, version)
    initialize_cognition(project, find_repo_root())
    initialize_experience(project, find_repo_root())
    initialize_editorial(project, find_repo_root())
    (project / "README.md").write_text(
        f"""# {project_name}

创建时间：{now.strftime('%Y-%m-%d %H:%M')}  
技能版本：{version}

## 目录与流程

前置材料链：`源材料 → 全文语义理解 → Source Truth Map`。
规划产物继续包含章节合同和页面合同。

全文语义理解 → Source Truth → 独立认知 → 语义规划合同
→ 总编独立判断 → 多结构竞争 → 总编结构裁决
→ 章节页面规划 → 总编提纲审稿 → 反方审稿 → 页面脚本

总编闸门失败时，其结论覆盖 `plan-check` 的通过状态并阻断页面生成；完成定向返工并重新通过相应 `editorial-check` 后方可继续。  
比较结果保存在 `comparison/`。

## 常用命令

```bash
python3 scripts/project_manager.py run {project_name}
python3 scripts/project_manager.py source-inventory {project_name}
python3 scripts/project_manager.py context-pack {project_name} deep
python3 scripts/project_manager.py semantic-check {project_name}
python3 scripts/project_manager.py understanding-check {project_name}
python3 scripts/project_manager.py cognitive-check {project_name}
python3 scripts/project_manager.py experience-pack {project_name}
python3 scripts/project_manager.py editorial-init {project_name}
python3 scripts/project_manager.py editorial-pack {project_name} semantic-planning
python3 scripts/project_manager.py editorial-check {project_name} semantic-planning
python3 scripts/project_manager.py editorial-pack {project_name} independent
python3 scripts/project_manager.py editorial-check {project_name} independent
python3 scripts/project_manager.py editorial-pack {project_name} storyline-candidates
python3 scripts/project_manager.py editorial-check {project_name} storyline-candidates
python3 scripts/project_manager.py editorial-pack {project_name} storyline
python3 scripts/project_manager.py editorial-check {project_name} storyline
python3 scripts/project_manager.py plan-check {project_name}
python3 scripts/project_manager.py editorial-pack {project_name} outline
python3 scripts/project_manager.py editorial-check {project_name} outline
python3 scripts/project_manager.py editorial-pack {project_name} red-team
python3 scripts/project_manager.py editorial-check {project_name} red-team-review
python3 scripts/project_manager.py editorial-pack {project_name} red-team-response
python3 scripts/project_manager.py editorial-check {project_name} red-team
python3 scripts/project_manager.py audit {project_name}
python3 scripts/project_manager.py notes-check {project_name}
python3 scripts/project_manager.py compare {project_name} <原稿.md> <优化稿.md>
```
""",
        encoding="utf-8",
    )
    return project
