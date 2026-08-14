#!/usr/bin/env python3
from __future__ import annotations
import argparse,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ppt_outline_planning.render import render_outline_directory
def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description="Render ppt-outline.md from validated outline artifacts."); p.add_argument("outline"); p.add_argument("-o","--output"); p.add_argument("--force",action="store_true"); ns=p.parse_args(argv)
    try: path=render_outline_directory(Path(ns.outline),output_path=Path(ns.output).expanduser() if ns.output else None,force=ns.force)
    except (OSError,ValueError) as exc: print(f"[error] {exc}",file=sys.stderr); return 1
    print(path); return 0
if __name__=="__main__": raise SystemExit(main())
