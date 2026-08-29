from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

for name in (
    "script_quality_contract_baseline.json",
    "script_quality_contract_baseline_2.json",
):
    target = ROOT / "tests" / "fixtures" / name
    payload = json.loads(target.read_text(encoding="utf-8"))
    for page in (payload.get("document") or {}).get("pages") or []:
        if isinstance(page, dict):
            page.setdefault("content_load", "")
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )

Path(__file__).unlink()
