"""Independence checks for CyberPPT's production runtime."""

from __future__ import annotations

from typing import Any

from .ppt_master_runtime_bridge import resolve_shared_resource, runtime_descriptor


def check_standalone_runtime() -> dict[str, Any]:
    descriptor = runtime_descriptor()
    resources = {
        "dual_image_core": descriptor.module_path,
        "svg_quality_checker": str(resolve_shared_resource("svg_quality_checker") or ""),
    }
    issues: list[dict[str, Any]] = []
    if descriptor.source != "cyberppt_vendor":
        issues.append({"code": "non_local_runtime_source", "source": descriptor.source, "blocking": True})
    if descriptor.host_root is not None:
        issues.append({"code": "host_runtime_dependency", "host_root": descriptor.host_root, "blocking": True})
    for name, path in resources.items():
        if not path:
            issues.append({"code": "local_resource_missing", "resource": name, "blocking": True})
    return {
        "schema": "cyberppt.standalone_runtime_gate.v1",
        "valid": not issues,
        "blocking_count": len(issues),
        "issues": issues,
        "runtime": descriptor.to_dict(),
        "resources": resources,
        "policy": "production_runtime_must_not_resolve_external_ppt_master_checkout",
    }

