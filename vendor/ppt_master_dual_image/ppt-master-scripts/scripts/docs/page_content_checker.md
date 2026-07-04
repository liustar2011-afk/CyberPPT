# Page Content Checker

Validate SVG semantic coverage against `analysis/page_contract.json`.

```bash
python3 scripts/page_content_checker.py <project_path> --require-contract
```

The checker reads `data-ref` and `data-role` from visible SVG groups. Missing required references or relationship references exit with code one. The coverage measure is an approximate SVG element-area signal; it identifies sparse pages but does not replace visual review.

For existing projects that predate page contracts, omit `--require-contract`; the command emits a warning and exits successfully.

See [`content-quality-gate.md`](../../references/content-quality-gate.md) for the contract schema and SVG annotation rules.
