# 科标研训两页PPT

CyberPPT Stage 01 workspace (`script` profile).

## Flow

1. Put the only authoritative source materials in `source/`.
2. Run `.venv/bin/python3 -m cyberppt prepare-source-context <project>` once.
3. Run `.venv/bin/python3 -m cyberppt prepare-script-foundation <project> --profile script` and complete UNDERSTAND once in `script/foundation.json`.
4. Follow `cyberppt-script-workflow` to create the lean `script/deck-plan.json`, stop at **脚本规划待确认**, then author `script/dist/final-script.md` and stop at **最终脚本已生成**.
5. After the final script is locked, run `prepare-stage02-handoff` and continue to Stage 02.

For this profile, do not run `prepare-source-map`, `prepare-semantic-understanding`,
`semantic-check`, Source Truth compilation, or `project-foundation`. Those commands
belong to explicit `strict/legacy` work.

AUTHOR loads the document thesis and structure once per deck, then reads only the
source evidence bound to the current page and its adjacent-page scope. Critic and
Rewrite operate on that authored page and its bound evidence; they do not rerun
whole-document semantic understanding.

The three authoritative Stage 01 content artifacts are `script/foundation.json`,
`script/deck-plan.json`, and `script/dist/final-script.md`.
