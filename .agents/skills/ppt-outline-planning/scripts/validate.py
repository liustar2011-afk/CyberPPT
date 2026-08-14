#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from ppt_outline_planning.validate import validate_outline_outputs
def main(argv:list[str]|None=None)->int:
    p=argparse.ArgumentParser(description="Validate PPT deck brief and page plan against layer-three semantic evidence."); p.add_argument("semantic"); p.add_argument("outline"); p.add_argument("--report",action="store_true"); ns=p.parse_args(argv)
    try: result=validate_outline_outputs(Path(ns.semantic),Path(ns.outline),write_report=ns.report)
    except (OSError,ValueError,json.JSONDecodeError) as exc: print(f"[error] {exc}",file=sys.stderr); return 2
    print(str(Path(ns.outline)/"outline-report.json") if ns.report else json.dumps(result,ensure_ascii=False,indent=2)); return 0 if result["status"]=="ok" else 1
if __name__=="__main__": raise SystemExit(main())
