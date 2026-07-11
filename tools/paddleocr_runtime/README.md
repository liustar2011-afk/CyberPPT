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

The OCR adapter never downloads models. Provision the two manifest-listed
archives out of band, verify their SHA-256 values, and unpack them under
`tools/paddleocr_runtime/models/PP-OCRv5_mobile_det` and
`PP-OCRv5_mobile_rec` (or provide equivalent verified det/rec directories).
Missing or unverified models fail closed before PaddleOCR starts; model
binaries are deliberately not committed to this repository.
