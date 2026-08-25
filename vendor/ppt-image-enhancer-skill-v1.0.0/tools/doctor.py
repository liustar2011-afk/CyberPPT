#!/usr/bin/env python3
from pathlib import Path
import json, sys
ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/'src'
sys.path.insert(0,str(SRC))
from ppt_image_enhancer.auto import backend_status
print(json.dumps(backend_status(), ensure_ascii=False, indent=2))
