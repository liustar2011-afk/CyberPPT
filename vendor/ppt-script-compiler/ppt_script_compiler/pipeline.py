from __future__ import annotations

import copy
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from .codex_runner import CodexRunner, MockCodexRunner
from .exporters import export_project
from .extractors import chunk_blocks, extract_source, save_extraction
from .prompts import (
    PROMPT_VERSION,
    assets_prompt,
    audit_prompt,
    consolidate_assets_prompt,
    page_plan_prompt,
    screen_copy_prompt,
    visual_plan_prompt,
)
from .store import ProjectStore
from .utils import read_json, stable_hash, write_json
from .validators import Finding, run_local_audit, stage_findings


@dataclass
class StageResult:
    stage: str
    payload: dict[str, Any]
    findings: list[Finding]
    output_path: Path

    @property
    def has_errors(self) -> bool:
        return any(f.severity == "error" for f in self.findings)


class Pipeline:
    def __init__(self, app_root: Path, store: ProjectStore, runner: CodexRunner | MockCodexRunner) -> None:
        self.app_root = app_root
        self.store = store
        self.runner = runner
        self.schemas_dir = app_root / "schemas"

    def parse_source(self, source_file: Path) -> dict[str, Any]:
        original_dir = self.store.root / "source/original"
        original_dir.mkdir(parents=True, exist_ok=True)
        destination = original_dir / source_file.name
        if source_file.resolve() != destination.resolve():
            shutil.copy2(source_file, destination)
        result = extract_source(destination)
        metadata = save_extraction(result, self.store.root)
        metadata["original_path"] = destination.relative_to(self.store.root).as_posix()
        self.store.set_source(metadata)
        return metadata

    def _stage_input_hash(self, stage: str, upstream: Any) -> str:
        return stable_hash({"stage": stage, "prompt_version": PROMPT_VERSION, "profile": self.store.profile(), "upstream": upstream})

    def run_assets(self, progress: Callable[[str], None] | None = None) -> StageResult:
        ready, reason = self.store.ready_for("assets")
        if not ready:
            raise RuntimeError(reason)
        source_path = self.store.root / "source/source_blocks.json"
        source_payload = read_json(source_path, {})
        blocks = source_payload.get("blocks", [])
        profile = self.store.profile()
        limit = int(profile.get("chunking", {}).get("single_call_character_limit", 90000))
        chunk_limit = int(profile.get("chunking", {}).get("chunk_character_limit", 42000))
        char_count = source_payload.get("metadata", {}).get("character_count", sum(len(b.get("text", "")) for b in blocks))
        output_path = self.store.stage_path("assets")
        input_hash = self._stage_input_hash("assets", source_payload.get("metadata", {}))

        if char_count <= limit:
            payload = self.runner.run_structured(
                stage_name="assets",
                prompt=assets_prompt(self.store.root, source_path, self.store.profile_path, chunk=False),
                schema_path=self.schemas_dir / "assets.schema.json",
                workspace=self.store.root,
                output_path=output_path,
                log_path=self.store.root / "logs/01_assets.json",
                progress=progress,
            )
        else:
            chunks = chunk_blocks(blocks, max_chars=chunk_limit)
            combined_assets: list[dict[str, Any]] = []
            chunk_summaries: list[str] = []
            for index, chunk in enumerate(chunks, start=1):
                chunk_path = self.store.root / f"source/chunks/chunk_{index:03d}.json"
                write_json(chunk_path, {"chunk_index": index, "chunk_count": len(chunks), "blocks": chunk})
                chunk_output = self.store.root / f"stages/chunks/assets_chunk_{index:03d}.json"
                chunk_payload = self.runner.run_structured(
                    stage_name=f"assets_chunk_{index:03d}",
                    prompt=assets_prompt(self.store.root, chunk_path, self.store.profile_path, chunk=True),
                    schema_path=self.schemas_dir / "assets_chunk.schema.json",
                    workspace=self.store.root,
                    output_path=chunk_output,
                    log_path=self.store.root / f"logs/01_assets_chunk_{index:03d}.json",
                    progress=progress,
                )
                # Namespace IDs before consolidation so relations remain unambiguous.
                id_map = {a["asset_id"]: f"C{index:03d}-{a['asset_id']}" for a in chunk_payload.get("assets", [])}
                for asset in chunk_payload.get("assets", []):
                    cloned = copy.deepcopy(asset)
                    cloned["asset_id"] = id_map[asset["asset_id"]]
                    cloned["related_asset_ids"] = [id_map[x] for x in asset.get("related_asset_ids", []) if x in id_map]
                    combined_assets.append(cloned)
                chunk_summaries.append(chunk_payload.get("chunk_summary", ""))
            max_merge = int(profile.get("chunking", {}).get("max_assets_per_merge", 260))
            working_assets = combined_assets
            level = 1
            while len(working_assets) > max_merge:
                next_assets: list[dict[str, Any]] = []
                batches = [working_assets[i : i + max_merge] for i in range(0, len(working_assets), max_merge)]
                for batch_index, batch in enumerate(batches, start=1):
                    batch_path = self.store.root / f"stages/chunks/merge_l{level}_{batch_index:03d}_input.json"
                    batch_output = self.store.root / f"stages/chunks/merge_l{level}_{batch_index:03d}_output.json"
                    write_json(batch_path, {"chunk_summaries": chunk_summaries, "assets": batch})
                    batch_payload = self.runner.run_structured(
                        stage_name=f"assets_consolidation_l{level}_{batch_index:03d}",
                        prompt=consolidate_assets_prompt(self.store.root, batch_path, source_path, self.store.profile_path),
                        schema_path=self.schemas_dir / "assets.schema.json",
                        workspace=self.store.root,
                        output_path=batch_output,
                        log_path=self.store.root / f"logs/01_assets_merge_l{level}_{batch_index:03d}.json",
                        progress=progress,
                    )
                    id_map = {a["asset_id"]: f"M{level:02d}{batch_index:03d}-{a['asset_id']}" for a in batch_payload.get("assets", [])}
                    for asset in batch_payload.get("assets", []):
                        cloned = copy.deepcopy(asset)
                        cloned["asset_id"] = id_map[asset["asset_id"]]
                        cloned["related_asset_ids"] = [id_map[x] for x in asset.get("related_asset_ids", []) if x in id_map]
                        next_assets.append(cloned)
                working_assets = next_assets
                level += 1
            combined_path = self.store.root / "stages/chunks/combined_assets.json"
            write_json(combined_path, {"chunk_summaries": chunk_summaries, "assets": working_assets})
            payload = self.runner.run_structured(
                stage_name="assets_consolidation",
                prompt=consolidate_assets_prompt(self.store.root, combined_path, source_path, self.store.profile_path),
                schema_path=self.schemas_dir / "assets.schema.json",
                workspace=self.store.root,
                output_path=output_path,
                log_path=self.store.root / "logs/01_assets_consolidation.json",
                progress=progress,
            )

        self.store.save_stage_json("assets", payload, input_hash=input_hash)
        findings = stage_findings("assets", self.store.root, self.schemas_dir, profile)
        if findings:
            self.store.mark_stage("assets", status="completed", message=f"本地校验发现{len(findings)}项问题")
        return StageResult("assets", payload, findings, output_path)

    def run_plan(self, progress: Callable[[str], None] | None = None) -> StageResult:
        ready, reason = self.store.ready_for("plan")
        if not ready:
            raise RuntimeError(reason)
        assets_path = self.store.stage_path("assets")
        assets = read_json(assets_path, {})
        input_hash = self._stage_input_hash("plan", assets)
        output_path = self.store.stage_path("plan")
        payload = self.runner.run_structured(
            stage_name="page_plan",
            prompt=page_plan_prompt(self.store.root, assets_path, self.store.profile_path),
            schema_path=self.schemas_dir / "page_plan.schema.json",
            workspace=self.store.root,
            output_path=output_path,
            log_path=self.store.root / "logs/02_page_plan.json",
            progress=progress,
        )
        self.store.save_stage_json("plan", payload, input_hash=input_hash)
        findings = stage_findings("plan", self.store.root, self.schemas_dir, self.store.profile())
        if findings:
            self.store.mark_stage("plan", status="completed", message=f"本地校验发现{len(findings)}项问题")
        return StageResult("plan", payload, findings, output_path)

    def run_copy(self, progress: Callable[[str], None] | None = None) -> StageResult:
        ready, reason = self.store.ready_for("copy")
        if not ready:
            raise RuntimeError(reason)
        assets_path = self.store.stage_path("assets")
        plan_path = self.store.stage_path("plan")
        upstream = {"assets": read_json(assets_path, {}), "plan": read_json(plan_path, {})}
        input_hash = self._stage_input_hash("copy", upstream)
        output_path = self.store.stage_path("copy")
        payload = self.runner.run_structured(
            stage_name="screen_copy",
            prompt=screen_copy_prompt(self.store.root, assets_path, plan_path, self.store.profile_path),
            schema_path=self.schemas_dir / "screen_copy.schema.json",
            workspace=self.store.root,
            output_path=output_path,
            log_path=self.store.root / "logs/03_screen_copy.json",
            progress=progress,
        )
        self.store.save_stage_json("copy", payload, input_hash=input_hash)
        findings = stage_findings("copy", self.store.root, self.schemas_dir, self.store.profile())
        if findings:
            self.store.mark_stage("copy", status="completed", message=f"本地校验发现{len(findings)}项问题")
        return StageResult("copy", payload, findings, output_path)

    def run_visual(self, progress: Callable[[str], None] | None = None) -> StageResult:
        ready, reason = self.store.ready_for("visual")
        if not ready:
            raise RuntimeError(reason)
        plan_path = self.store.stage_path("plan")
        copy_path = self.store.stage_path("copy")
        upstream = {"plan": read_json(plan_path, {}), "copy": read_json(copy_path, {})}
        input_hash = self._stage_input_hash("visual", upstream)
        output_path = self.store.stage_path("visual")
        payload = self.runner.run_structured(
            stage_name="visual_plan",
            prompt=visual_plan_prompt(self.store.root, plan_path, copy_path, self.store.profile_path),
            schema_path=self.schemas_dir / "visual_plan.schema.json",
            workspace=self.store.root,
            output_path=output_path,
            log_path=self.store.root / "logs/04_visual_plan.json",
            progress=progress,
        )
        self.store.save_stage_json("visual", payload, input_hash=input_hash)
        findings = stage_findings("visual", self.store.root, self.schemas_dir, self.store.profile())
        if findings:
            self.store.mark_stage("visual", status="completed", message=f"本地校验发现{len(findings)}项问题")
        return StageResult("visual", payload, findings, output_path)

    def run_audit(self, progress: Callable[[str], None] | None = None, semantic: bool = True) -> StageResult:
        ready, reason = self.store.ready_for("audit")
        if not ready:
            raise RuntimeError(reason)
        local_findings = run_local_audit(self.store.root, self.schemas_dir, self.store.profile())
        source_path = self.store.root / "source/source_blocks.json"
        assets_path = self.store.stage_path("assets")
        plan_path = self.store.stage_path("plan")
        copy_path = self.store.stage_path("copy")
        visual_path = self.store.stage_path("visual")
        upstream = {
            "assets": read_json(assets_path, {}), "plan": read_json(plan_path, {}),
            "copy": read_json(copy_path, {}), "visual": read_json(visual_path, {})
        }
        input_hash = self._stage_input_hash("audit", upstream)
        output_path = self.store.stage_path("audit")
        if semantic:
            payload = self.runner.run_structured(
                stage_name="semantic_audit",
                prompt=audit_prompt(self.store.root, source_path, assets_path, plan_path, copy_path, visual_path, self.store.profile_path),
                schema_path=self.schemas_dir / "audit.schema.json",
                workspace=self.store.root,
                output_path=output_path,
                log_path=self.store.root / "logs/05_semantic_audit.json",
                progress=progress,
            )
        else:
            payload = {
                "summary": {
                    "pass": not any(f.severity == "error" for f in local_findings),
                    "source_fidelity_score": 0,
                    "coverage_score": 100 if not any(f.code in {"CORE_ASSET_UNASSIGNED", "COPY_PAGE_MISSING"} for f in local_findings) else 70,
                    "page_purity_score": 100 if not any(f.code in {"HIGH_SPLIT_RISK", "PAGE_TEXT_OVERLOAD"} for f in local_findings) else 70,
                    "visual_alignment_score": 100 if not any(f.code.startswith("VISUAL_") or f.code == "EQUAL_REGION_WALL" for f in local_findings) else 70,
                    "overall_comment": "仅执行本地结构校验，未执行模型语义审查。"
                },
                "findings": []
            }
        existing_keys = {(f.get("code"), f.get("page_id"), f.get("asset_id"), f.get("description")) for f in payload.get("findings", [])}
        for finding in local_findings:
            item = finding.to_dict()
            key = (item["code"], item["page_id"], item["asset_id"], item["description"])
            if key not in existing_keys:
                payload.setdefault("findings", []).append(item)
        errors = [f for f in payload.get("findings", []) if f.get("severity") == "error"]
        if errors:
            payload["summary"]["pass"] = False
            payload["summary"]["overall_comment"] = (payload["summary"].get("overall_comment", "") + f" 本地校验合并后仍有{len(errors)}项错误。 ").strip()
        write_json(output_path, payload)
        self.store.save_stage_json("audit", payload, input_hash=input_hash)
        findings = [Finding(**{k: f.get(k, "") for k in ["severity", "code", "description", "recommendation", "page_id", "asset_id"]}) for f in payload.get("findings", [])]
        return StageResult("audit", payload, findings, output_path)

    def export(self) -> dict[str, Path]:
        ready, reason = self.store.ready_for("export")
        if not ready:
            raise RuntimeError(reason)
        paths = export_project(self.store.root)
        self.store.mark_stage("export", status="completed", input_hash=self._stage_input_hash("export", {k: str(v) for k, v in paths.items()}), output_hash=stable_hash({k: str(v) for k, v in paths.items()}))
        return paths

    def run_all(self, progress: Callable[[str], None] | None = None, semantic_audit: bool = True) -> dict[str, Any]:
        results: dict[str, Any] = {}
        for stage, method in [
            ("assets", self.run_assets),
            ("plan", self.run_plan),
            ("copy", self.run_copy),
            ("visual", self.run_visual),
        ]:
            status = self.store.stage_status(stage).get("status")
            if status != "completed":
                results[stage] = method(progress=progress)
        if self.store.stage_status("audit").get("status") != "completed":
            results["audit"] = self.run_audit(progress=progress, semantic=semantic_audit)
        results["exports"] = self.export()
        return results
