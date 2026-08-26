# High-quality source foundation workflow

Default project layout:

```text
projects/<project>/
  source/
  workbench/source-foundation/
    markdown/
    foundation/
    semantic/
    outline/
  workbench/stages/00-source-map/                 # compatibility projection
  workbench/stages/00-semantic-understanding/    # compatibility projection
  workbench/stages/01-analysis/                  # compatibility projection
  integration/
    authority-map.json
    cyberppt-handoff-report.json
```

The first `workbench/source-foundation` subtree is authoritative for source understanding and deck planning. The Stage 00/01 files are generated compatibility views for the existing CyberPPT page authoring and audit code.
