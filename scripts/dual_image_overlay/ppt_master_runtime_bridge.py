"""Resolve the self-contained CyberPPT runtime for dual-image rebuilds.

The dual-image route used to import a vendored module directly from business code.
The vendor snapshot is the production runtime. PPT Master is an upstream source
of ideas/code, not a runtime dependency of CyberPPT.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from types import ModuleType
from typing import Any


@dataclass(frozen=True)
class RuntimeDescriptor:
    source: str
    module_path: str | None
    host_root: str | None
    vendor_root: str
    resource_bindings_path: str
    shared_resources_resolved: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def cyberppt_root() -> Path:
    return Path(__file__).resolve().parents[2]


def vendor_root() -> Path:
    return cyberppt_root() / "vendor" / "ppt_master_slide_image_rebuild"


def resolve_host_root() -> Path | None:
    """Return no host runtime: production resolution is intentionally local-only."""
    return None


def _resource_bindings() -> tuple[dict[str, Any], Path]:
    path = vendor_root() / "resource_bindings.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")), path
    except (OSError, json.JSONDecodeError):
        return {}, path


def resolve_shared_resource(relative_path: str) -> Path | None:
    """Resolve a resource from CyberPPT's local snapshot only."""
    bindings, _ = _resource_bindings()
    fallback = bindings.get("local_fallback", {})
    configured = fallback.get(relative_path) if isinstance(fallback, dict) else None
    if configured:
        candidate = cyberppt_root() / str(configured)
        if candidate.exists():
            return candidate
    shared = bindings.get("shared", {})
    shared_configured = shared.get(relative_path) if isinstance(shared, dict) else None
    if shared_configured:
        candidate = vendor_root() / str(shared_configured)
        if candidate.exists():
            return candidate
        candidate = vendor_root() / "scripts" / Path(str(shared_configured)).name
        if candidate.exists():
            return candidate
    candidate = vendor_root() / relative_path
    return candidate if candidate.exists() else None


def _core_candidates() -> list[tuple[str, Path, Path | None]]:
    return [(
        "cyberppt_vendor",
        vendor_root() / "scripts" / "dual_image_rebuild_pptx.py",
        None,
    )]


def runtime_descriptor() -> RuntimeDescriptor:
    bindings, bindings_path = _resource_bindings()
    for source, path, host in _core_candidates():
        if path.is_file():
            shared_ok = bool(resolve_shared_resource("svg_quality_checker"))
            return RuntimeDescriptor(source, str(path), None, str(vendor_root()), str(bindings_path), shared_ok)
    return RuntimeDescriptor("unavailable", None, None, str(vendor_root()), str(bindings_path), False)


def load_layout_core() -> ModuleType | None:
    """Load the preferred layout core, falling back to the vendored snapshot."""
    descriptor = runtime_descriptor()
    if not descriptor.module_path:
        return None
    module_name = (
        "_cyberppt_vendored_ppt_master_dual_image_rebuild"
        if descriptor.source == "cyberppt_vendor"
        else "_cyberppt_ppt_master_dual_image_layout_core"
    )
    cached = sys.modules.get(module_name)
    if cached is not None:
        return cached
    module_path = Path(descriptor.module_path)
    scripts_dir = module_path.parent
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        return None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        return None
    return module
