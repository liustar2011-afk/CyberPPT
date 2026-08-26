# Release Check

- Skill: `word-to-ppt-script`
- Version: **2.2.0**
- Result: **PASS after repository validation**

## v2.2.0 checks

- `10-script-final.md` remains the formal complete artifact;
- template pages map to `cover / contents / chapter / closing`;
- content pages export locked text, page mission and a cleaned page-level visual-structure block;
- raw evidence, notes, logic skeleton and internal `visual_intent_type` labels do not leak into ImageGen;
- reusable palette, material and scene-style prose are not stored per page;
- the integrated repository loads `visual/ACTIVE-STYLE.md` as the only runtime style source;
- page titles remain in the PPT text layer;
- body images use the configured 2048×1024, 2:1 contract by default;
- generated ImageGen review contracts pass strict validation.
