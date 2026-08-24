# Split `script-engine/` into a standalone Git repository

The subtree is intentionally self-contained. When a separate GitHub repository is desired, split its history without changing internal paths.

## Recommended repository name

`CyberPPT-Script`

## One-time split from the CyberPPT host repository

From a local clone of CyberPPT:

```bash
git fetch origin
git switch main
git pull --ff-only

git subtree split \
  --prefix=script-engine \
  --branch=script-engine-main
```

Create the empty remote repository, then push the split branch:

```bash
git remote add script-engine git@github.com:liustar2011-afk/CyberPPT-Script.git
git push -u script-engine script-engine-main:main
```

The resulting repository root will already contain:

```text
.agents/
.github/
adapters/
contracts/
docs/
examples/
references/
script_engine/
tests/
AGENTS.md
LICENSE
README.md
pyproject.toml
```

No path rewrite is required after the split.

## Keep the host and Script Engine loosely coupled

Prefer a versioned release, Git submodule, Git subtree import, or ordinary external checkout. Do not reintroduce imports from Script Engine internals into CyberPPT Stage 02.

The runtime boundary remains:

```text
CyberPPT-Script/dist/final-script.md
        ↓ file path
CyberPPT prepare-stage02-handoff --script ...
```

## Optional host linkage

A host repository may keep only documentation pointing to the external Script Engine repository. A Git submodule is optional and should be used only if local co-checkout convenience is worth the repository-management overhead.

Stage 02 itself requires neither a submodule nor a Python dependency on Script Engine.
