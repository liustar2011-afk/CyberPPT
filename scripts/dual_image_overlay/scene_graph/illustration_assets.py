from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any

from PIL import Image

from .schema import PageSceneGraph, VisualNode


ILLUSTRATION_ASSET_SCHEMA = "cyberppt.recognized_illustration_assets.v1"
IMAGE_ROLES = {
    "semantic_image",
    "illustration",
    "photo",
    "screenshot",
    "chart",
    "document",
    "equipment",
    "visual",
}


def _is_recognized_image(node: VisualNode) -> bool:
    attrs = node.attributes
    return bool(
        attrs.get("recognized_layout")
        and (
            node.node_type in {"image", "illustration", "photo"}
            or node.semantic_role.lower() in IMAGE_ROLES
            or attrs.get("preserve_internal_text") is True
        )
    )


def _crop_box(node: VisualNode, graph: PageSceneGraph, image: Image.Image) -> tuple[int, int, int, int]:
    context = graph.coordinate_context.to_dict()
    canvas = context.get("coordinate_space") or context.get("normalized_canvas") or {}
    canvas_width = float(canvas.get("width") or image.width)
    canvas_height = float(canvas.get("height") or image.height)
    sx = image.width / canvas_width
    sy = image.height / canvas_height
    left = max(0, min(image.width, round(node.bbox.x1 * sx)))
    top = max(0, min(image.height, round(node.bbox.y1 * sy)))
    right = max(left + 1, min(image.width, round(node.bbox.x2 * sx)))
    bottom = max(top + 1, min(image.height, round(node.bbox.y2 * sy)))
    return left, top, right, bottom


def materialize_recognized_illustration_assets(
    graph: PageSceneGraph,
    *,
    background_image: str | Path,
    output_dir: str | Path,
) -> tuple[PageSceneGraph, dict[str, Any]]:
    """Crop recognized illustration containers into independent image assets."""

    source_path = Path(background_image).resolve()
    target_dir = Path(output_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    records: list[dict[str, Any]] = []
    updated_nodes: list[VisualNode] = []

    with Image.open(source_path) as image:
        rgba = image.convert("RGBA")
        for node in graph.visual_nodes:
            if not _is_recognized_image(node):
                updated_nodes.append(node)
                continue
            crop_box = _crop_box(node, graph, rgba)
            output_path = target_dir / f"page_{graph.page:03d}_{node.node_id}.png"
            rgba.crop(crop_box).save(output_path)
            attrs = dict(node.attributes)
            attrs.update(
                {
                    "source_ref": str(output_path),
                    "crop": {
                        "x": crop_box[0],
                        "y": crop_box[1],
                        "width": crop_box[2] - crop_box[0],
                        "height": crop_box[3] - crop_box[1],
                    },
                    "text_bearing": bool(attrs.get("text_bearing", True)),
                    "preserve_internal_text": True,
                    "editable": False,
                    "fit_mode": str(attrs.get("fit_mode") or "contain"),
                    "movable": True,
                }
            )
            updated_nodes.append(
                replace(
                    node,
                    node_type="image",
                    source={"kind": "recognized_illustration_crop", "path": str(output_path)},
                    attributes=attrs,
                )
            )
            records.append(
                {
                    "node_id": node.node_id,
                    "role": node.semantic_role,
                    "source": str(source_path),
                    "crop_path": str(output_path),
                    "crop_bbox": list(crop_box),
                    "preserve_internal_text": True,
                }
            )

    updated_graph = replace(
        graph,
        visual_nodes=updated_nodes,
        metadata={
            **graph.metadata,
            "recognized_illustration_assets": {
                "schema": ILLUSTRATION_ASSET_SCHEMA,
                "count": len(records),
                "assets": records,
            },
        },
    )
    return updated_graph, {
        "schema": ILLUSTRATION_ASSET_SCHEMA,
        "page": graph.page,
        "count": len(records),
        "assets": records,
    }
