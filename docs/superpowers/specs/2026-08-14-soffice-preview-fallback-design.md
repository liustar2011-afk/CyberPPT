# SOFFICE Preview Fallback Design

## Goal

Make `build_page.py --render-preview` tolerate the macOS Homebrew LibreOffice headless abort (exit 134) without changing its command line or output contract.

## Scope

Only `scripts/dual_image_overlay/build_page.py` and its focused tests change. The preview renderer will try the PATH-resolved Office executable first, then the Codex bundled SOFFICE executable when the first conversion fails. Every attempt uses a temporary LibreOffice user profile.

## Behaviour

- A successful first conversion continues to produce `exports/page-render.pdf` and `exports/page-render.png` as before.
- A failed first conversion proceeds to the bundled executable at `~/.cache/codex-runtimes/codex-primary-runtime/dependencies/bin/override/soffice` when that file exists.
- If no Office executable exists, or every attempt fails, the raised error identifies each attempted executable and includes its failure evidence.
- `pdftoppm` remains a required dependency and retains its existing behaviour.

## Verification

Unit tests will simulate a failed PATH executable and a successful bundled fallback, verify that a disposable profile flag is supplied, and verify that all-failure errors retain both executable paths. A final real conversion uses the existing editable SVG PPTX fixture and asserts PDF and PNG preview files.
