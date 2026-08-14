#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ppt_outline_planning.prepare import prepare_outline_workpack
def main(argv:list[str]|None=None)->int:
    parser=argparse.ArgumentParser(description="Prepare a PPT outline planning workpack from validated layer-three semantic artifacts."); parser.add_argument("semantic"); parser.add_argument("-o","--output"); group=parser.add_mutually_exclusive_group(); group.add_argument("--request"); group.add_argument("--request-text"); parser.add_argument("--force",action="store_true"); ns=parser.parse_args(argv)
    semantic=Path(ns.semantic).expanduser(); output=Path(ns.output).expanduser() if ns.output else semantic.parent/f"{semantic.name}.outline"; request=None
    if ns.request:
        try: request=json.loads(Path(ns.request).expanduser().read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as exc: print(f"[error] {exc}",file=sys.stderr); return 2
        if not isinstance(request,dict): print("[error] --request JSON must contain an object",file=sys.stderr); return 2
    try: result=prepare_outline_workpack(semantic,output,request=request,request_text=ns.request_text,force=ns.force)
    except (OSError,ValueError,json.JSONDecodeError) as exc: print(f"[error] {exc}",file=sys.stderr); return 1
    print(result["workpack"]); return 0
if __name__=="__main__": raise SystemExit(main())
