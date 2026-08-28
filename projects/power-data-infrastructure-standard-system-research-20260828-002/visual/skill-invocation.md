# PPT Visual Structure Designer Invocation

- skill: ppt-visual-structure-designer
- skill_path: D:\CyberPPT\vendor\skills\ppt-visual-structure-designer\SKILL.md
- skill_sha256: 9c89f589aad3be09baadc3f2733ea711a4a9c48bd4fd15fb71ec879e88c0c323
- skill_bundle_sha256: 5e7378cbba7c6b70cf4c7ad938c69823da3f48ffeb87b4cce3b9939500c5f0d7
- approved_script: D:\CyberPPT\projects\power-data-infrastructure-standard-system-research-20260828-002\workbench\scripts\final\script-final.md
- approved_script_sha256: 0df8d20b0523770c0ff9fbed0e964a26ae0a49b8bb71622fca4b58fe78d1a669
- approved_script_semantic_sha256: 50c30fb14f32ffc9e16c16a07ca7e66b3feaecff16b330619593985bba015324
- stage02_handoff: D:\CyberPPT\projects\power-data-infrastructure-standard-system-research-20260828-002\workbench\stages\02-handoff\stage02-handoff.json
- visual_design_input: D:\CyberPPT\projects\power-data-infrastructure-standard-system-research-20260828-002\visual\visual-design-input.json
- skill_request: D:\CyberPPT\projects\power-data-infrastructure-standard-system-research-20260828-002\visual\skill-request.json
- mode: workbench-handoff
- content_lock: strict

## Required action

Invoke the registered skill in the current execution surface. Use visual-design-input.json, derived only from stage02_handoff.json, as the visual-design interface. Write cyberppt.visual_design_decisions.v3. Treat business_relationships as authoritative, use stage01_relationship_features to preserve actors, actions, directions, conditions, branches and feedback, and treat author_visual_notes as advisory only. trace_refs are audit-only provenance: use them to justify decisions but never copy them into visual copy or ImageGen prompt material. Treat expression_constraints as the required reading-relation and balance profile: it governs peer hierarchy, progression, correspondence, feedback or causal direction; it must never be converted directly into a fixed card, column, arrow, loop, pyramid or matrix template. Every candidate must provide its own visual_thesis and expression_fit with the received form, satisfied constraints, reading relation, balance strategy, and either an empty default-profile deviation or an adapted-profile changed-constraint list plus business reason that preserves the expression core. Respect each page's prompt_mode. For semantic_brief, decide only the semantic focus, source-supported relationship boundary, evidence grouping and exact-text binding; omit execution_design or treat it as non-authoritative advice, leaving scene, carrier, spatial organization and supporting detail to ImageGen. For directed_composition, provide the full authoritative execution_design with business_object, visual_focus, semantic_role, use_scene, scene_type, text_integration_method, spatial_organization and relationship_encoding. For every page, record stage01_visual_note_disposition with the received form, chosen reading relation and balance strategy, plus inherited, adjusted and rejected upstream visual features and reasons. Do not read or reuse any existing Stage 02 visual/ or workbench/prompts/imagegen outputs as authority. Write one candidate when the page's business relationship type is unambiguous from expression_constraints.reading_requirement and content alone; when it is genuinely contested (for example parallel vs. hierarchical), generate and compare 2-3 materially different candidates and justify the selection. Deterministic keyword matching must not choose the final visual intent or carrier. Preserve the approved page set, locked text ids and locked text, and write only:

- `visual/visual-design-decisions.json`

After the Skill has actually produced that decision receipt, run `python -m cyberppt execute-visual-structure <project> --script <script>` to compile `deck-visual-spec.json` and `script-visual-structure.md`; then record the execution with `python -m cyberppt record-visual-structure-execution <project> --script <script> --executor <surface> --model <model>`, and run `visual-structure-audit`. The audit, not the Skill, rebuilds generation-prompts.md as a legacy structural preview. Formal ImageGen handoff uses the repository artifact-spec-v2 compiler over the audited Stage 02 handoff, deck visual spec and style lock.

Do not select a visual style, generate images, SVG, HTML, or PPTX in this stage.
