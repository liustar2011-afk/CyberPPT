from __future__ import annotations

import json
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from jsonschema import Draft202012Validator

from .utils import clean_json_text, read_json, relative_posix, utc_now_iso, write_json


class CodexError(RuntimeError):
    pass


@dataclass
class CodexProbe:
    executable: str | None
    installed: bool
    version: str
    logged_in: bool
    login_status: str
    exec_help: str

    @property
    def supports_output_schema(self) -> bool:
        return "--output-schema" in self.exec_help

    @property
    def supports_ephemeral(self) -> bool:
        return "--ephemeral" in self.exec_help

    @property
    def supports_skip_git(self) -> bool:
        return "--skip-git-repo-check" in self.exec_help

    @property
    def supports_color(self) -> bool:
        return "--color" in self.exec_help

    @property
    def supports_sandbox(self) -> bool:
        return "--sandbox" in self.exec_help

    @property
    def supports_model(self) -> bool:
        return "--model" in self.exec_help


class CodexRunner:
    def __init__(
        self,
        codex_bin: str | None = None,
        model: str | None = None,
        reasoning_effort: str | None = "high",
        timeout_seconds: int = 1800,
    ) -> None:
        self.codex_bin = codex_bin or os.getenv("CODEX_BIN") or shutil.which("codex")
        self.model = (model or "").strip()
        self.reasoning_effort = (reasoning_effort or "").strip()
        self.timeout_seconds = int(timeout_seconds)
        self._probe: CodexProbe | None = None

    def probe(self, force: bool = False) -> CodexProbe:
        if self._probe is not None and not force:
            return self._probe
        if not self.codex_bin:
            self._probe = CodexProbe(None, False, "", False, "未找到 codex 命令", "")
            return self._probe

        def run(args: list[str], timeout: int = 30) -> subprocess.CompletedProcess[str]:
            return subprocess.run(
                [self.codex_bin, *args],
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=timeout,
                shell=False,
            )

        try:
            version_run = run(["--version"])
            version = (version_run.stdout or version_run.stderr).strip()
            help_run = run(["exec", "--help"])
            exec_help = (help_run.stdout or "") + "\n" + (help_run.stderr or "")
            status_run = run(["login", "status"])
            login_status = ((status_run.stdout or "") + "\n" + (status_run.stderr or "")).strip()
            self._probe = CodexProbe(
                executable=self.codex_bin,
                installed=version_run.returncode == 0,
                version=version,
                logged_in=status_run.returncode == 0,
                login_status=login_status,
                exec_help=exec_help,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            self._probe = CodexProbe(self.codex_bin, False, "", False, str(exc), "")
        return self._probe

    def ensure_ready(self) -> CodexProbe:
        probe = self.probe()
        if not probe.installed:
            raise CodexError("未找到可用的 Codex CLI。请先安装 Codex，并确认 codex 命令可在终端运行。")
        if not probe.logged_in:
            raise CodexError("Codex CLI 尚未登录。请在终端运行 `codex login`，选择使用 ChatGPT 账户登录。")
        if not probe.supports_output_schema:
            raise CodexError("当前 Codex CLI 版本不支持 --output-schema。请先更新 Codex CLI。")
        return probe

    def run_structured(
        self,
        *,
        stage_name: str,
        prompt: str,
        schema_path: Path,
        workspace: Path,
        output_path: Path,
        log_path: Path,
        progress: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        probe = self.ensure_ready()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        raw_output = output_path.with_suffix(output_path.suffix + ".raw")
        if raw_output.exists():
            raw_output.unlink()

        cmd = [probe.executable or "codex", "exec"]
        if probe.supports_skip_git:
            cmd.append("--skip-git-repo-check")
        if probe.supports_sandbox:
            cmd.extend(["--sandbox", "read-only"])
        if probe.supports_ephemeral:
            cmd.append("--ephemeral")
        if probe.supports_color:
            cmd.extend(["--color", "never"])
        if self.model and probe.supports_model:
            cmd.extend(["--model", self.model])
        if self.reasoning_effort in {"low", "medium", "high", "xhigh"}:
            cmd.extend(["--config", f'model_reasoning_effort="{self.reasoning_effort}"'])
        cmd.extend(["--output-schema", str(schema_path.resolve())])
        cmd.extend(["--output-last-message", str(raw_output.resolve())])
        cmd.append("-")

        if progress:
            progress(f"正在运行 {stage_name}…")
        started = time.time()
        proc = subprocess.Popen(
            cmd,
            cwd=str(workspace),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
        try:
            stdout, stderr = proc.communicate(input=prompt, timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired:
            proc.kill()
            stdout, stderr = proc.communicate()
            raise CodexError(f"{stage_name} 超时（{self.timeout_seconds} 秒）。可提高超时值后重试当前阶段。")

        duration = round(time.time() - started, 2)
        log_record = {
            "stage": stage_name,
            "started_at": utc_now_iso(),
            "duration_seconds": duration,
            "return_code": proc.returncode,
            "command": [Path(cmd[0]).name, *cmd[1:]],
            "stdout": stdout,
            "stderr": stderr,
        }
        write_json(log_path, log_record)
        if proc.returncode != 0:
            detail = (stderr or stdout or "未知错误")[-5000:]
            raise CodexError(f"Codex 执行失败：\n{detail}")
        if not raw_output.exists():
            detail = (stdout or stderr or "未生成结果")[-3000:]
            raise CodexError(f"Codex 未写入结构化结果文件。\n{detail}")

        raw_text = raw_output.read_text(encoding="utf-8", errors="replace")
        try:
            payload = json.loads(clean_json_text(raw_text))
        except (json.JSONDecodeError, ValueError) as exc:
            raise CodexError(f"{stage_name} 返回内容不是有效 JSON：{exc}") from exc

        schema = read_json(schema_path)
        errors = sorted(Draft202012Validator(schema).iter_errors(payload), key=lambda e: list(e.path))
        if errors:
            details = "\n".join(f"- {'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors[:20])
            raise CodexError(f"{stage_name} 输出未通过 JSON Schema 校验：\n{details}")
        write_json(output_path, payload)
        if progress:
            progress(f"{stage_name} 完成，用时 {duration:.1f} 秒")
        return payload


class MockCodexRunner:
    """Offline smoke-test runner. It never calls a model and is not intended for real documents."""

    model = "mock"
    reasoning_effort = "none"

    def probe(self, force: bool = False) -> CodexProbe:
        return CodexProbe("mock", True, "mock-1.0", True, "mock", "--output-schema --ephemeral --skip-git-repo-check --sandbox --model --color")

    def ensure_ready(self) -> CodexProbe:
        return self.probe()

    def run_structured(
        self,
        *,
        stage_name: str,
        prompt: str,
        schema_path: Path,
        workspace: Path,
        output_path: Path,
        log_path: Path,
        progress: Callable[[str], None] | None = None,
    ) -> dict[str, Any]:
        if progress:
            progress(f"演示模式：生成 {stage_name}")
        payload = self._build(stage_name, workspace)
        schema = read_json(schema_path)
        errors = list(Draft202012Validator(schema).iter_errors(payload))
        if errors:
            raise CodexError(f"Mock 输出不符合 schema：{errors[0].message}")
        write_json(output_path, payload)
        write_json(log_path, {"stage": stage_name, "mock": True, "at": utc_now_iso()})
        return payload

    def _build(self, stage_name: str, workspace: Path) -> dict[str, Any]:
        source = read_json(workspace / "source/source_blocks.json", {"blocks": []})
        blocks = source.get("blocks", [])
        if stage_name.startswith("assets_chunk"):
            chunk_num = stage_name.split("_")[-1]
            return {"chunk_summary": f"演示分块 {chunk_num}", "assets": self._assets(blocks)}
        if stage_name == "assets":
            assets = self._assets(blocks)
            return {
                "document": {
                    "title": source.get("metadata", {}).get("file_name", "演示材料"),
                    "purpose": "演示源材料转PPT脚本流程",
                    "audience": "内部汇报对象",
                    "central_judgment": assets[0]["content"] if assets else "材料需要结构化表达",
                    "narrative_threads": ["背景", "判断", "方案", "行动"],
                    "constraints": ["演示模式未进行真实语义分析"],
                    "source_characteristics": ["按源段落机械生成信息资产"]
                },
                "assets": assets or [self._fallback_asset()]
            }
        if stage_name.startswith("assets_consolidation"):
            combined = read_json(workspace / "stages/chunks/combined_assets.json", {"assets": []})
            assets = combined.get("assets", [])
            # re-id to keep schema and references stable
            for i, asset in enumerate(assets, 1):
                asset["asset_id"] = f"A{i:03d}"
                asset["related_asset_ids"] = []
            return {
                "document": {
                    "title": source.get("metadata", {}).get("file_name", "演示材料"),
                    "purpose": "演示源材料转PPT脚本流程",
                    "audience": "内部汇报对象",
                    "central_judgment": assets[0]["content"] if assets else "材料需要结构化表达",
                    "narrative_threads": ["背景", "方案", "实施"],
                    "constraints": ["演示模式"],
                    "source_characteristics": ["长材料分块"]
                },
                "assets": assets[:80] or [self._fallback_asset()]
            }
        if stage_name == "page_plan":
            assets_doc = read_json(workspace / "stages/01_information_assets.json", {"assets": []})
            assets = assets_doc.get("assets", [])
            pages = []
            groups = [assets[i:i+3] for i in range(0, len(assets), 3)] or [[self._fallback_asset()]]
            for i, group in enumerate(groups[:12], 1):
                ids = [a["asset_id"] for a in group]
                pages.append({
                    "page_id": f"P{i:02d}", "order": i, "page_type": "cover" if i == 1 else "content",
                    "page_role": "封面" if i == 1 else "内容页", "page_mission": group[0]["content"],
                    "core_judgment": group[0]["content"], "audience_question": "本页需要说明什么",
                    "relationship_type": "single_judgment", "source_asset_ids": ids,
                    "must_include": [a["content"] for a in group], "must_not_include": [],
                    "previous_page_relation": "" if i == 1 else "承接前页", "next_page_relation": "引出后页" if i < len(groups) else "形成结论",
                    "split_risk": "low", "notes": "演示模式"
                })
            return {
                "presentation_title": assets_doc.get("document", {}).get("title", "演示汇报"),
                "overall_thesis": assets_doc.get("document", {}).get("central_judgment", ""),
                "narrative_arc": [p["page_mission"] for p in pages], "pages": pages, "unassigned_core_asset_ids": []
            }
        if stage_name == "screen_copy":
            plan = read_json(workspace / "stages/02_page_plan.json", {"pages": []})
            assets_doc = read_json(workspace / "stages/01_information_assets.json", {"assets": []})
            lookup = {a["asset_id"]: a for a in assets_doc.get("assets", [])}
            pages = []
            for page in plan.get("pages", []):
                ids = page["source_asset_ids"]
                lines = [lookup[i]["content"] for i in ids if i in lookup]
                pages.append({
                    "page_id": page["page_id"], "title": page["core_judgment"][:22], "subtitle": "",
                    "conclusion": page["core_judgment"],
                    "modules": [{"module_id": "M01", "heading": "核心内容", "body_lines": lines[:4], "asset_ids": ids}],
                    "annotations": [], "source_asset_ids": ids,
                    "content_lock": {
                        "title_meaning": page["core_judgment"], "core_judgment": page["core_judgment"],
                        "required_facts": lines, "required_terms": [], "prohibited_rewrites": [], "prohibited_additions": ["原文不存在的内容"]
                    }
                })
            return {"pages": pages}
        if stage_name == "visual_plan":
            copy = read_json(workspace / "stages/03_screen_copy.json", {"pages": []})
            pages = []
            for page in copy.get("pages", []):
                pages.append({
                    "page_id": page["page_id"], "visual_intent_type": "single_judgment", "visual_thesis": page["conclusion"],
                    "dominant_carrier": "一个主视觉结构", "scene_anchor": "与内容相关的行业实景背景",
                    "composition": "主视觉居中，文字以嵌入式面板附着", "reading_path": ["主视觉", "核心信息", "结论"],
                    "emphasis_primary": page["conclusion"], "emphasis_secondary": [], "text_embedding": ["文字嵌入主结构"],
                    "imagery": ["实景彩色行业场景"],
                    "layout_regions": [{"region_id": "R01", "purpose": "主视觉", "content_ref": "visual_thesis", "position": "中央偏右", "relative_size": "dominant", "z_order": 1}],
                    "avoid": ["卡片墙", "正面人像", "图标密集"], "aspect_ratio": "16:9", "title_rendering": "ppt_text_layer",
                    "generation_prompt": "生成政企领导汇报页面底图，不绘制标题和副标题。"
                })
            return {"global_visual_rules": ["演示模式"], "pages": pages}
        if stage_name == "semantic_audit":
            return {"summary": {"pass": True, "source_fidelity_score": 80, "coverage_score": 80, "page_purity_score": 80, "visual_alignment_score": 80, "overall_comment": "演示模式仅验证流程。"}, "findings": []}
        raise CodexError(f"未知 mock stage: {stage_name}")

    @staticmethod
    def _assets(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
        assets = []
        for i, block in enumerate([b for b in blocks if b.get("text")][:24], 1):
            assets.append({
                "asset_id": f"A{i:03d}", "content": block["text"][:160],
                "asset_type": "judgment" if block.get("kind") == "heading" else "fact",
                "priority": "core" if i <= 4 else "important", "must_retain": i <= 4,
                "compressibility": "limited", "source_refs": [block["source_id"]],
                "evidence": [block["text"][:80]], "related_asset_ids": [], "notes": "演示模式"
            })
        return assets

    @staticmethod
    def _fallback_asset() -> dict[str, Any]:
        return {"asset_id": "A001", "content": "源材料需要形成稳定的PPT叙事结构", "asset_type": "judgment", "priority": "core", "must_retain": True, "compressibility": "limited", "source_refs": ["S00001"], "evidence": [], "related_asset_ids": [], "notes": "fallback"}
