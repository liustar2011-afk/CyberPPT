#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path

EXCLUDE_NAMES = {"__pycache__", ".pytest_cache", ".DS_Store"}
EXCLUDE_SUFFIXES = {".pyc", ".pyo"}


def include(path: Path) -> bool:
    if any(part in EXCLUDE_NAMES for part in path.parts):
        return False
    if path.suffix in EXCLUDE_SUFFIXES:
        return False
    return True


def sha256(path: Path) -> str:
    h = hashlib.sha256(path.read_bytes())
    return h.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description="Create clean ZIP release")
    parser.add_argument("root", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path("."))
    args = parser.parse_args()
    root = args.root.resolve()
    version = (root / "VERSION").read_text(encoding="utf-8").strip()
    name = f"word-to-ppt-script-v{version}"
    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    zip_path = out_dir / f"{name}.zip"
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(root.rglob("*")):
            rel = path.relative_to(root)
            if path.is_file() and include(rel):
                zf.write(path, Path(name) / rel)
    digest = sha256(zip_path)
    sha_path = out_dir / f"{name}.sha256"
    sha_path.write_text(f"{digest}  {zip_path.name}\n", encoding="utf-8")
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(td)
        extracted = Path(td) / name
        if not (extracted / "SKILL.md").exists():
            raise RuntimeError("ZIP integrity check failed")
    print(zip_path)
    print(sha_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
