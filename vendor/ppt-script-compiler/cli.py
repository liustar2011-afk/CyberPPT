from __future__ import annotations

import argparse
from pathlib import Path

from ppt_script_compiler.codex_runner import CodexRunner, MockCodexRunner
from ppt_script_compiler.pipeline import Pipeline
from ppt_script_compiler.store import ProjectStore


APP_ROOT = Path(__file__).resolve().parent
WORKSPACES_ROOT = APP_ROOT / "workspaces"
DEFAULT_PROFILE = APP_ROOT / "templates/default_profile.yaml"


def main() -> int:
    parser = argparse.ArgumentParser(description="将源材料分阶段编译为PPT脚本")
    sub = parser.add_subparsers(dest="command", required=True)

    check = sub.add_parser("check", help="检查Codex安装与登录状态")
    check.add_argument("--codex-bin", default="")

    run = sub.add_parser("run", help="解析材料并一键生成完整脚本")
    run.add_argument("source", type=Path)
    run.add_argument("--name", default="PPT脚本项目")
    run.add_argument("--codex-bin", default="")
    run.add_argument("--model", default="")
    run.add_argument("--reasoning", choices=["medium", "high", "xhigh"], default="high")
    run.add_argument("--timeout", type=int, default=1800)
    run.add_argument("--mock", action="store_true")
    run.add_argument("--no-semantic-audit", action="store_true")

    args = parser.parse_args()
    if args.command == "check":
        runner = CodexRunner(codex_bin=args.codex_bin or None)
        probe = runner.probe(force=True)
        print(f"installed={probe.installed}")
        print(f"version={probe.version}")
        print(f"logged_in={probe.logged_in}")
        print(probe.login_status)
        return 0 if probe.installed and probe.logged_in else 1

    WORKSPACES_ROOT.mkdir(parents=True, exist_ok=True)
    store = ProjectStore.create(WORKSPACES_ROOT, args.name, DEFAULT_PROFILE)
    runner = MockCodexRunner() if args.mock else CodexRunner(
        codex_bin=args.codex_bin or None,
        model=args.model or None,
        reasoning_effort=args.reasoning,
        timeout_seconds=args.timeout,
    )
    pipeline = Pipeline(APP_ROOT, store, runner)
    metadata = pipeline.parse_source(args.source)
    print(f"源材料：{metadata['block_count']}个来源块，{metadata['character_count']}字")
    pipeline.run_all(progress=print, semantic_audit=not args.no_semantic_audit)
    print(f"项目目录：{store.root}")
    print(f"最终脚本：{store.root / 'exports/ppt_script.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
