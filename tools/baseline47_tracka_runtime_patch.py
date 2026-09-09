from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if old not in text:
        raise SystemExit(f"needle not found in {path}: {old[:120]!r}")
    if text.count(old) != 1:
        raise SystemExit(f"needle is not unique in {path}: {text.count(old)}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8", newline="\n")


replace_once(
    "scripts/imagegen_pipeline/runtime_style_contract.py",
    '    "# 12｜最终视觉执行约束｜最高优先级",\n    TERMINAL_EXECUTION_HEADING,',
    '    "# 12｜最终视觉执行约束｜最高优先级",\n    "## 12｜最终风格收口｜最高视觉优先级",\n    TERMINAL_EXECUTION_HEADING,',
)

replace_once(
    "scripts/imagegen_pipeline/final_prompt_ir.py",
    '@dataclass(frozen=True)\nclass RuntimeLockIR:\n    style_contract: str\n    terminal_lock: str = ""\n\n\n\n@dataclass(frozen=True)\nclass FinalPromptIR:',
    '@dataclass(frozen=True)\nclass RuntimeLockIR:\n    style_contract: str\n    terminal_lock: str = ""\n\n    def __post_init__(self) -> None:\n        if not self.style_contract.strip():\n            raise PromptContractError("runtime lock requires a non-empty style contract")\n\n\n@dataclass(frozen=True)\nclass FinalPromptIR:',
)

replace_once(
    "scripts/imagegen_pipeline/final_prompt_contract.py",
    'from scripts.imagegen_pipeline.final_prompt_ir import FinalPromptIR, PromptContractError\n',
    'from scripts.imagegen_pipeline.final_prompt_ir import FinalPromptIR, PromptContractError\nfrom scripts.imagegen_pipeline.runtime_style_contract import TERMINAL_EXECUTION_HEADING\n',
)

replace_once(
    "scripts/imagegen_pipeline/final_prompt_contract.py",
    '    _validate_text_bindings(prompt, ir)\n\n    if ir.full_slide_design_context is not None:\n',
    '''    _validate_text_bindings(prompt, ir)\n\n    runtime_style_contract = ir.runtime_lock.style_contract.strip()\n    if style_id == 9:\n        if prompt.count(TERMINAL_EXECUTION_HEADING) != 1:\n            raise PromptContractError(\n                "live runtime style prompt requires one terminal execution lock"\n            )\n        terminal = prompt.split(TERMINAL_EXECUTION_HEADING, 1)[1].strip()\n        if not terminal or not prompt.rstrip().endswith(terminal):\n            raise PromptContractError(\n                "live runtime style prompt requires one terminal execution lock at the absolute end"\n            )\n    else:\n        if TERMINAL_EXECUTION_HEADING in prompt:\n            raise PromptContractError(\n                "non-live style prompt contains a live terminal execution lock"\n            )\n        if prompt.count(runtime_style_contract) != 1:\n            raise PromptContractError(\n                "final prompt must contain the runtime style contract exactly once"\n            )\n\n    if ir.full_slide_design_context is not None:\n''',
)

replace_once(
    "scripts/imagegen_pipeline/final_prompt_renderer.py",
    'raise ValueError("style_lock is required for style 09 final prompt rendering")',
    'raise ValueError("style lock is required for style 09 final prompt rendering")',
)

print("Track A1 runtime-lock patch applied")
