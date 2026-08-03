#!/usr/bin/env python3
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


def _doctor_without_dependencies() -> int:
    modules = {"yaml": "PyYAML", "jsonschema": "jsonschema", "docx": "python-docx", "fitz": "PyMuPDF", "pptx": "python-pptx"}
    missing = [package for module, package in modules.items() if importlib.util.find_spec(module) is None]
    result = {"python": sys.version.split()[0], "ok": not missing and sys.version_info >= (3, 10), "missing_packages": missing}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "doctor":
    raise SystemExit(_doctor_without_dependencies())

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ppt_compiler.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
