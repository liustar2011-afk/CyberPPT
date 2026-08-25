#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 tools/bootstrap.py --backend auto
python3 tools/doctor.py
echo 'Ready. Example: python3 enhance.py page.png'
