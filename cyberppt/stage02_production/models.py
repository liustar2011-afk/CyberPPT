from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Stage02RunOptions:
    project: Path
    script: Path
    pages_raw: str
    style_lock: Path | None = None
    style_id: int | None = None
    style_name: str | None = None
    output_dir: Path | None = None
    semantic_plan_dir: Path | None = None
    require_images: bool = False
    production_build: bool = False
    production_mode: str = "image-to-editable-svg"
    assembly_mode: str = "editable"
    generate_images: bool = False
    image_model: str = "gpt-image-2"
    image_quality: str = "high"
    image_timeout: int = 600
    force_images: bool = False
    dry_run_images: bool = False
    prompt_enrich: str = "off"
    require_send_approval: bool = False
    build_id: str | None = None
    external_script: bool = False
    autonomous_contract: Path | None = None
    blueprint_only: bool = False
    no_style_reference: bool = False
    skip_image_text_audit: bool = False
    # Deprecated compatibility telemetry only. No authorization/gate is allowed
    # to branch on this field; it remains so old callers and test patch-points
    # can observe that the legacy CLI flag was supplied during migration.
    allow_script_edit_requested: bool = False
    allow_prompt_edit: bool = False
    prompt_overrides_dir: Path | None = None


@dataclass(frozen=True)
class Stage02BuildContext:
    project: Path
    canonical_script: Path
    selected_pages: tuple[int, ...]
    pages_raw: str
    build_id: str
    build_dir: Path
    style_lock: Path
    source_script_sha256: str
    script_input_sha256: str
    visual_spec_sha256: str
    style_lock_sha256: str
    production_mode: str
    assembly_mode: str
    source_mode: str
    full_reference_images: tuple[Path, ...] = ()
    autonomous_contract: Path | None = None
    project_created: bool = False


@dataclass(frozen=True)
class ManifestStageResult:
    manifest: dict[str, Any]
    manifest_path: Path
    compiled_script: Path
    page_numbers: tuple[int, ...]
    template_lock_path: Path
    build_context_path: Path


@dataclass(frozen=True)
class ImageStageResult:
    manifest: dict[str, Any]
    generation: dict[str, Any] | None = None


@dataclass(frozen=True)
class ReconstructionStageResult:
    clean_base_generation: dict[str, Any] | None = None
    build: dict[str, Any] | None = None
    production_readiness: dict[str, Any] | None = None
    tool_consumption: dict[str, Any] = field(default_factory=dict)
    status: str = "ready_for_image_generation"


@dataclass(frozen=True)
class DeliveryStageResult:
    summary: dict[str, Any]
    summary_path: Path
    build_context_path: Path
    officecli_render_qa: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class Stage02ProductionResult:
    context: Stage02BuildContext
    manifest: ManifestStageResult
    images: ImageStageResult
    reconstruction: ReconstructionStageResult
    delivery: DeliveryStageResult
