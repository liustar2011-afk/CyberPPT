# Externalize Stage 01 quality thresholds

## Goal

Make the active numerical quality-policy values configurable from the existing
`vendor/skills/ppt-script/config/rules.yaml`, following the verified
`MODULE_CEILING` loading pattern. Default runtime behaviour must be unchanged.

## Scope

Move these active policy values out of Python literals:

- script-quality visible-judgment similarity (`0.04`);
- script-quality onscreen semantic-coverage advisory minimum (`0.22`);
- outline core-message trigram redundancy similarity (`0.72`);
- outline consecutive thin-page density factor (`median * 0.45`).

The existing page-composition module ceiling remains unchanged and is the
implementation precedent.

## Design

Add a narrowly named Stage 01 quality-threshold mapping to `rules.yaml`.
Each consuming module will load only its relevant leaf values at import time,
using explicit defaults when PyYAML is unavailable, the file is absent or
malformed, or a configured value cannot be converted to a finite float.

`script_quality_contract.py` will share one private rules-file reader for its
three values (including the existing module ceiling), avoiding repeated YAML
parsing and preserving its standalone fallback behaviour. Its public constant
names stay intact so existing callers and tests need no interface migration.

`outline_audit_density.py` and `outline_audit_structure.py` will each use a
small local loader with the same failure semantics and constants for their
respective values. The values remain policy, rather than becoming outline
input fields or project artifacts.

## Validation

Add focused tests that patch the YAML-path/module reload boundary to prove:

1. configured values affect the corresponding audit decision;
2. missing, malformed, non-numeric, or non-finite values retain the current
   defaults; and
3. the existing default-rule test suite continues to produce the same results.

No project-level manifests, approvals, attempts, or parallel artifacts are
introduced.
