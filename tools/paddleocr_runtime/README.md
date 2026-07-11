# Repository PaddleOCR runtime

This directory defines the isolated OCR runtime used by CyberPPT's local
`paddleocr-local` backend. It is intentionally separate from the main project
interpreter. The lock is based on the `/Volumes/DOC/PaddleOCR` checkout at
release `v3.7.0` and uses PaddlePaddle `3.1.1` on CPU.

## Bootstrap

Use Python 3.12 and run the script without positional arguments:

```bash
PYTHON_BIN=/opt/homebrew/bin/python3.12 ./tools/paddleocr_runtime/bootstrap.sh
```

The script creates `tools/paddleocr_runtime/.venv`, installs the pinned
requirements, and invokes pip only as `"$VIRTUAL_ENV/bin/python" -m pip`.

Model archives are downloaded by the OCR adapter on first use. Their exact
URLs and SHA-256 digests are recorded in `runtime_manifest.json`; model
binaries are deliberately not committed to this repository.
