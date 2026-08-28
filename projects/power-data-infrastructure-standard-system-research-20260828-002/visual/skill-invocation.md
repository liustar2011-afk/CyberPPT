# PPT Visual Structure Designer Invocation

- skill: ppt-visual-structure-designer
- skill_path: /Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/SKILL.md
- skill_sha256: e1458a735c0cae13c1750f3dd146254fcd132d2358e1fecb37415c30dc968d4f
- skill_bundle_sha256: e053be94ae9d2a2cbc4e8463f7314cbd5f296128494e785c713176d087fbb8f8
- approved_script: /Volumes/DOC/CyberPPT/projects/power-data-infrastructure-standard-system-research-20260828-002/script/dist/final-script.md
- approved_script_sha256: 62ea0987054b1632bd23357cd4a0dc03df03401fad71b4a225c9b020021fac24
- approved_script_semantic_sha256: 3e7e52bc19e8c16b4180624b55706182417d377c5b92276db12478637bf40b0a
- stage02_handoff: /Volumes/DOC/CyberPPT/projects/power-data-infrastructure-standard-system-research-20260828-002/workbench/stages/02-handoff/stage02-handoff.json
- visual_design_input: /Volumes/DOC/CyberPPT/projects/power-data-infrastructure-standard-system-research-20260828-002/visual/visual-design-input.json
- skill_request: /Volumes/DOC/CyberPPT/projects/power-data-infrastructure-standard-system-research-20260828-002/visual/skill-request.json
- mode: workbench-handoff
- content_lock: strict

## Required action

Invoke the registered skill in the current execution surface. Use visual-design-input.json, derived only from stage02_handoff.json, as the visual-design interface. Write cyberppt.visual_design_decisions.v3. Treat business_relationships as authoritative, use stage01_relationship_features to preserve actors, actions, directions, conditions, branches and feedback, and treat author_visual_notes as advisory only. trace_refs are audit-only provenance: use them to justify decisions but never copy them into visual copy or ImageGen prompt material. Treat expression_constraints as the required reading-relation and balance profile: it governs peer hierarchy, progression, correspondence, feedback or causal direction; it must never be converted directly into a fixed card, column, arrow, loop, pyramid or matrix template. Every candidate must provide its own visual_thesis and expression_fit with the received form, satisfied constraints, reading relation, balance strategy, and either an empty default-profile deviation or an adapted-profile changed-constraint list plus business reason that preserves the expression core. Respect each page's prompt_mode. For semantic_brief, decide only the semantic focus, source-supported relationship boundary, evidence grouping and exact-text binding; omit execution_design or treat it as non-authoritative advice, leaving scene, carrier, spatial organization and supporting detail to ImageGen. For directed_composition, provide the full authoritative execution_design with business_object, visual_focus, semantic_role, use_scene, scene_type, text_integration_method, spatial_organization and relationship_encoding. For every page, record stage01_visual_note_disposition with the received form, chosen reading relation and balance strategy, plus inherited, adjusted and rejected upstream visual features and reasons. Do not read or reuse any existing Stage 02 visual/ or workbench/prompts/imagegen outputs as authority. Write one candidate when the page's business relationship type is unambiguous from expression_constraints.reading_requirement and content alone; when it is genuinely contested (for example parallel vs. hierarchical), generate and compare 2-3 materially different candidates and justify the selection. Deterministic keyword matching must not choose the final visual intent or carrier. Preserve the approved page set, locked text ids and locked text, and write only:

- `visual/visual-design-decisions.json`

After the Skill has actually produced that decision receipt, run `python -m cyberppt execute-visual-structure <project> --script <script>` to compile `deck-visual-spec.json` and `script-visual-structure.md`; then record the execution with `python -m cyberppt record-visual-structure-execution <project> --script <script> --executor <surface> --model <model>`, and run `visual-structure-audit`. The audit, not the Skill, rebuilds generation-prompts.md as a legacy structural preview. Formal ImageGen handoff uses the repository artifact-spec-v2 compiler over the audited Stage 02 handoff, deck visual spec and style lock.

Do not select a visual style, generate images, SVG, HTML, or PPTX in this stage.
