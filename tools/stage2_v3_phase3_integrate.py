from __future__ import annotations

from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    (ROOT / path).write_text(content, encoding="utf-8", newline="\n")


def replace_once(path: str, old: str, new: str) -> None:
    content = read(path)
    count = content.count(old)
    if count != 1:
        raise RuntimeError(f"{path}: expected one patch target, found {count}: {old[:120]!r}")
    write(path, content.replace(old, new, 1))


def run(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, check=check, text=True)


# 1. Visual Stage supplies semantic evidence to the v2 resolver.
compiler = "cyberppt/visual_stage/compiler.py"
if "def _medium_semantic_kwargs(" not in read(compiler):
    marker = "\ndef _decision_execution_design(\n"
    helper = '''\ndef _medium_semantic_kwargs(\n    source: dict[str, Any],\n    *,\n    business_object: str = "",\n) -> dict[str, object]:\n    locked = source.get("locked_text_items")\n    locked = locked if isinstance(locked, list) else []\n    texts = [\n        str(item.get("text") or "")\n        for item in locked\n        if isinstance(item, dict) and str(item.get("text") or "")\n    ]\n    relationships = source.get("business_relationships")\n    relationships = relationships if isinstance(relationships, list) else []\n    actors: list[str] = []\n    for item in relationships:\n        if not isinstance(item, dict):\n            continue\n        subject = str(item.get("subject") or "").strip()\n        if subject:\n            actors.append(subject)\n        actors.extend(str(value).strip() for value in item.get("objects") or [] if str(value).strip())\n    explicit_actor = str(source.get("actor_type") or source.get("business_actor_type") or "").strip()\n    data_available = bool(\n        source.get("data_available")\n        or source.get("metrics")\n        or source.get("data_points")\n        or source.get("chart_data")\n    )\n    return {\n        "page_mission": str(source.get("page_mission") or ""),\n        "business_relationships": relationships,\n        "text_count": len(texts),\n        "text_characters": sum(len(text) for text in texts),\n        "business_object": business_object,\n        "actor_type": explicit_actor or " ".join(dict.fromkeys(actors)),\n        "data_available": data_available,\n    }\n\n'''
    replace_once(compiler, marker, helper + marker)

# semantic_brief call
old = '''        medium_policy = resolve_visual_medium_policy(\n            selected.get("visual_medium_policy"),\n            scene_policy=scene_policy,\n        )\n'''
new = '''        medium_policy = resolve_visual_medium_policy(\n            selected.get("visual_medium_policy"),\n            scene_policy=scene_policy,\n            **_medium_semantic_kwargs(source),\n        )\n'''
if old in read(compiler):
    replace_once(compiler, old, new)

# directed explicit design call
old = '''        medium_policy = resolve_visual_medium_policy(\n            design.get("visual_medium_policy") or selected.get("visual_medium_policy"),\n            scene_policy=scene_policy,\n        )\n'''
new = '''        medium_policy = resolve_visual_medium_policy(\n            design.get("visual_medium_policy") or selected.get("visual_medium_policy"),\n            scene_policy=scene_policy,\n            **_medium_semantic_kwargs(source, business_object=normalized["business_object"]),\n        )\n'''
if old in read(compiler):
    replace_once(compiler, old, new)

# directed fallback call
old = '''    medium_policy = resolve_visual_medium_policy(\n        selected.get("visual_medium_policy"),\n        scene_policy=scene_policy,\n    )\n'''
new = '''    medium_policy = resolve_visual_medium_policy(\n        selected.get("visual_medium_policy"),\n        scene_policy=scene_policy,\n        **_medium_semantic_kwargs(source, business_object=f"{subject}中围绕‘{focus_label}’形成的业务关系场"),\n    )\n'''
if old in read(compiler):
    replace_once(compiler, old, new)

# 2. FinalPromptIR carries v2 medium fields with backwards-compatible defaults.
ir = "scripts/imagegen_pipeline/final_prompt_ir.py"
old = '''class VisualMediumPolicyIR:\n    preferred: str\n    allowed: tuple[str, ...]\n    scene_policy: str\n    rationale: str\n\n    def __post_init__(self) -> None:\n        if not self.preferred.strip() or not self.allowed or not self.scene_policy.strip():\n            raise PromptContractError("visual medium policy IR is incomplete")\n        if self.preferred not in self.allowed:\n            raise PromptContractError("preferred visual medium must be allowed")\n'''
new = '''class VisualMediumPolicyIR:\n    preferred: str\n    allowed: tuple[str, ...]\n    scene_policy: str\n    rationale: str\n    secondary: str = ""\n    forbidden: tuple[str, ...] = ()\n    confidence: float = 0.5\n\n    def __post_init__(self) -> None:\n        if not self.preferred.strip() or not self.allowed or not self.scene_policy.strip():\n            raise PromptContractError("visual medium policy IR is incomplete")\n        if self.preferred not in self.allowed:\n            raise PromptContractError("preferred visual medium must be allowed")\n        if self.secondary and (self.secondary not in self.allowed or self.secondary == self.preferred):\n            raise PromptContractError("secondary visual medium must be a distinct allowed medium")\n        if set(self.allowed) & set(self.forbidden):\n            raise PromptContractError("allowed and forbidden visual media must be disjoint")\n        if not 0.0 <= self.confidence <= 1.0:\n            raise PromptContractError("visual medium confidence must be between 0 and 1")\n'''
if old in read(ir):
    replace_once(ir, old, new)

# 3. Artifact projection carries v2 fields.
artifact = "scripts/imagegen_pipeline/artifact_prompt.py"
old = '''    return VisualMediumPolicyIR(\n        preferred=policy.preferred,\n        allowed=policy.allowed,\n        scene_policy=policy.scene_policy,\n        rationale=policy.rationale,\n    )\n'''
new = '''    return VisualMediumPolicyIR(\n        preferred=policy.preferred,\n        allowed=policy.allowed,\n        scene_policy=policy.scene_policy,\n        rationale=policy.rationale,\n        secondary=policy.secondary,\n        forbidden=policy.forbidden,\n        confidence=policy.confidence,\n    )\n'''
if old in read(artifact):
    replace_once(artifact, old, new)

# 4. Production prompt exposes public medium choices/confidence, while receipt
# retains the raw v2 audit contract.
renderer = "scripts/imagegen_pipeline/final_prompt_renderer.py"
old = '''    if policy is not None:\n        allowed = "; ".join(item.replace("_", " ") for item in policy.allowed)\n        lines.extend((\n            f"Preferred visual medium: {policy.preferred.replace('_', ' ')}.",\n            f"Allowed visual media: {allowed}.",\n            f"Scene policy: {policy.scene_policy.replace('_', ' ')}.",\n            f"Medium rationale: {policy.rationale}",\n        ))\n'''
new = '''    if policy is not None:\n        allowed = "; ".join(item.replace("_", " ") for item in policy.allowed)\n        forbidden = "; ".join(item.replace("_", " ") for item in policy.forbidden) or "none"\n        rationale = policy.rationale.replace("_", " ")\n        medium_lines = [\n            f"Preferred visual medium: {policy.preferred.replace('_', ' ')}.",\n        ]\n        if policy.secondary:\n            medium_lines.append(f"Secondary visual medium: {policy.secondary.replace('_', ' ')}.")\n        medium_lines.extend((\n            f"Allowed visual media: {allowed}.",\n            f"Forbidden visual media: {forbidden}.",\n            f"Medium confidence: {policy.confidence:.2f}.",\n            f"Scene policy: {policy.scene_policy.replace('_', ' ')}.",\n            f"Medium rationale: {rationale}",\n        ))\n        lines.extend(medium_lines)\n'''
if old in read(renderer):
    replace_once(renderer, old, new)

old = '''                "preferred": ir.visual_medium_policy.preferred,\n                "allowed": list(ir.visual_medium_policy.allowed),\n                "scene_policy": ir.visual_medium_policy.scene_policy,\n                "rationale": ir.visual_medium_policy.rationale,\n'''
new = '''                "preferred": ir.visual_medium_policy.preferred,\n                "secondary": ir.visual_medium_policy.secondary,\n                "allowed": list(ir.visual_medium_policy.allowed),\n                "forbidden": list(ir.visual_medium_policy.forbidden),\n                "confidence": ir.visual_medium_policy.confidence,\n                "scene_policy": ir.visual_medium_policy.scene_policy,\n                "rationale": ir.visual_medium_policy.rationale,\n'''
if old in read(renderer):
    replace_once(renderer, old, new)

# 5. Focused prompt-surface tests.
test_path = ROOT / "tests/test_visual_medium_prompt_v2.py"
test_path.write_text(
    '''from scripts.imagegen_pipeline.final_prompt_ir import (\n    CompositionIR, FinalPromptIR, RuntimeLockIR, SemanticGroupIR, VisualMediumPolicyIR,\n)\nfrom scripts.imagegen_pipeline.final_prompt_renderer import render_debug_receipt, render_final_prompt\n\n\ndef _ir():\n    return FinalPromptIR(\n        deliverable="Create one finished PowerPoint body visual.",\n        page_judgment="形成可信协同能力。",\n        dominant_relationship="多主体通过受控接口形成可信协同关系。",\n        reading_path=("主体", "接口", "结果"),\n        semantic_groups=(SemanticGroupIR(id="g1", role="content", summary="可信协同", emphasis="primary"),),\n        composition=CompositionIR(\n            spatial_organization="one coherent relationship field",\n            primary_focus="可信协同",\n            visual_responsibility=("Use one relationship-bearing field.",),\n        ),\n        visible_text=("可信协同",),\n        hard_constraints=("Do not render instructions.",),\n        runtime_lock=RuntimeLockIR(style_contract="Pure white editorial art direction."),\n        visual_medium_policy=VisualMediumPolicyIR(\n            preferred="relationship_diagram",\n            secondary="object_illustration",\n            allowed=("relationship_diagram", "object_illustration"),\n            forbidden=("business_scene", "data_visualization", "mixed"),\n            scene_policy="forbidden",\n            confidence=0.86,\n            rationale="preferred=relationship_diagram score=0.82; semantic relationship signal",\n        ),\n    )\n\n\ndef test_prompt_exposes_public_medium_v2_contract_without_backend_tokens():\n    prompt = render_final_prompt(_ir())\n    assert "Preferred visual medium: relationship diagram." in prompt\n    assert "Secondary visual medium: object illustration." in prompt\n    assert "Forbidden visual media: business scene; data visualization; mixed." in prompt\n    assert "Medium confidence: 0.86." in prompt\n    assert "relationship_diagram" not in prompt\n    assert "object_illustration" not in prompt\n\n\ndef test_debug_receipt_keeps_raw_medium_v2_audit_fields():\n    receipt = render_debug_receipt(_ir(), page_id="P03", compiler="artifact-spec-v3", prompt_ir_version="v5")\n    policy = receipt["visual_medium_policy"]\n    assert policy["preferred"] == "relationship_diagram"\n    assert policy["secondary"] == "object_illustration"\n    assert policy["forbidden"] == ["business_scene", "data_visualization", "mixed"]\n    assert policy["confidence"] == 0.86\n''',
    encoding="utf-8",
    newline="\n",
)

run(
    "python", "-m", "pytest", "-q",
    "tests/test_visual_medium_policy.py",
    "tests/test_visual_medium_resolver_v2.py",
    "tests/test_visual_medium_prompt_v2.py",
    "tests/test_region_graph_composition_strategy.py",
)

run("git", "config", "user.name", "github-actions[bot]")
run("git", "config", "user.email", "41898282+github-actions[bot]@users.noreply.github.com")
run("git", "add", compiler, ir, artifact, renderer, "tests/test_visual_medium_prompt_v2.py")
if run("git", "diff", "--cached", "--quiet", check=False).returncode != 0:
    run("git", "commit", "-m", "stage2-v3: integrate semantic visual medium resolver")
    run("git", "push", "origin", "HEAD:feature/stage2-artifact-contract-v3")
