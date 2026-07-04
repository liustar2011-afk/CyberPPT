# ppt-master Dual Image Vendor Snapshot

This directory vendors the dual-image rebuild assets copied from `/Volumes/DOC/ppt-master` for CyberPPT's `dual_image_editable_overlay` mode.

Copied source roots:

- `/Volumes/DOC/ppt-master/slide-image-rebuild/`
- `/Volumes/DOC/ppt-master/skills/ppt-master/scripts/`
- `/Volumes/DOC/ppt-master/skills/ppt-master/templates/`
- `/Volumes/DOC/ppt-master/skills/ppt-master/workflows/script-imagegen-to-ppt.md`
- selected tests from `/Volumes/DOC/ppt-master/tests/`

Source snapshot notes:

- `/Volumes/DOC/ppt-master`: branch `main`, commit `c26ca68dcc1149570a92ec55b30b5a3fdb9c06c3`, dirty with 6 status entries at copy time.
- `/Volumes/DOC/ppt-master/slide-image-rebuild`: branch `master`, commit `02a28ba3883943c3e907ac9db1f646017bdf65c9`, clean at copy time.

Excluded transient files:

- `.git/`
- `.DS_Store`
- `__pycache__/`
- `.pytest_cache/`
- `.venv/`
- generated project/export/QA output directories
- `.uuid.LCK`
- `.uuid.TMP-*`

This snapshot is not the formal CyberPPT runtime. Formal output must be generated through `scripts/dual_image_overlay/` and PptxGenJS.
