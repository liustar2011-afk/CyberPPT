# CLI compatibility deprecations

The following flags are retained only so older automation does not break:

- `--lightweight-stage01-confirmed`
- `--allow-script-edit`

Passing either flag emits a deprecation warning to stderr. Neither flag changes
Stage 01/Stage 02 authorization, script audit, prompt approval, image-text QA,
reconstruction QA, or delivery gates. New examples and automation must not use
them.

Planned removal: the next major CyberPPT CLI revision. Removal will be announced
in that major revision's migration notes before the parser aliases are deleted.

`--no-style-reference` refers generically to the selected style reference image;
it is not tied to a numbered internal style.
