# CyberPPT 47 项历史基线失败治理台账

开发分支：`fix/baseline-47-regressions`

基线：`main@366dc81f65f039efdcf48c87e4d132ab5375f6ba`

任务目标：在不回退 Stage2 Artifact Contract v3 已合并能力的前提下，逐组修复仓库现存 47 项历史 Python 测试失败，并将 Python 3.10 / 3.12 全量测试收敛至 0 failed。

实施机制：每个可验证小步骤独立提交；每步同步记录“已完成工作 / 验证结果 / 下一阶段工作”；生产合同与测试期望冲突时，先判定当前正式合同，再决定修代码、迁移测试或补兼容层；禁止为单纯追绿而恢复已废弃行为。

## Step 0｜任务建立与失败基线冻结

状态：已完成

已完成工作：
- 从 Stage2 v3 合并后的 `main@366dc81f65f039efdcf48c87e4d132ab5375f6ba` 创建独立分支 `fix/baseline-47-regressions`。
- 使用 Stage2 v3 最终 CI 的 Python 3.12 pytest artifact 冻结 47 个失败测试 ID。
- 确认 Python 3.10 / 3.12 的 47 个失败集合一致，可采用一套失败清单治理。
- 将 47 项失败按根因域划分为 3 条治理主线，避免跨域混改。

验证结果：
- 冻结基线：47 failed / 2000 passed / 8 skipped / 49 subtests passed。
- 失败分布涉及 20 个测试文件。
- Stage2 v3 合并前已证明这 47 项均属于历史基线集合，本任务以其为唯一治理对象。

下一阶段工作：
- Track A：先处理 Style09/10、Runtime Lock、Style Snapshot 相关 18 项失败；该组最集中，且会影响 Final Prompt 与 ImageGen 上层兼容。

## 治理主线

### Track A｜Style Contract / Runtime Lock / Snapshot（18 项）

涉及：
- `tests/test_artifact_prompt.py`：1
- `tests/test_extended_style_9.py`：4
- `tests/test_extended_style_10.py`：2
- `tests/test_final_prompt_contract.py`：3
- `tests/test_final_prompt_ir.py`：1
- `tests/test_final_prompt_renderer.py`：3
- `tests/test_style_lock_snapshot.py`：4

治理原则：恢复并固化 Style09 terminal runtime lock 的唯一性、末尾位置和 style contract 绑定；核对 Style09/10 registry contract 与 snapshot/migration 语义；不得破坏 Stage2 v3 Copy Contract、Acceptance Contract 与 FinalPromptIR v6。

### Track B｜ImageGen Prompt / Handoff / Creative Brief（22 项）

涉及：
- `tests/test_imagegen_creative_brief.py`：6
- `tests/test_imagegen_deliverable_prompt.py`：4
- `tests/test_imagegen_handoff_modularization.py`：3
- `tests/test_imagegen_micro_freedom.py`：1
- `tests/test_imagegen_no_visual_structure.py`：4
- `tests/test_imagegen_page_manifest.py`：2
- `tests/test_imagegen_prompt_diagnostics.py`：1
- `tests/test_visual_grammar.py`：1

治理原则：以当前 content-first / Stage2 v3 Prompt 合同为权威，逐项区分“生产行为回归”和“旧 wording/snapshot 断言漂移”；优先修真实 prompt 权威冲突，纯旧文案快照按现行合同迁移。

### Track C｜其余仓库合同与模块化（7 项）

涉及：
- `tests/test_content_route.py`：1
- `tests/test_final_script_pages.py`：2
- `tests/test_script_quality_modularization.py`：2
- `tests/test_skill_contract.py`：1
- `tests/test_text_output_contract.py`：1

治理原则：分别处理 route contract、final script fixture、script-quality baseline、skill contract 路径和 newline translation；每类保持独立提交，不用宽松断言掩盖真实问题。

## 精确失败清单

### Track A
- `tests/test_artifact_prompt.py::ArtifactPromptTests::test_style09_terminal_lock_is_unique_and_at_absolute_end`
- `tests/test_extended_style_10.py::test_style_ten_resolves_to_its_copied_live_contract`
- `tests/test_extended_style_10.py::test_style_ten_is_not_advertised_and_reuses_style_nine_palette`
- `tests/test_extended_style_9.py::test_style_nine_registry_contract_carries_current_visual_invariants`
- `tests/test_extended_style_9.py::test_legacy_style_nine_lock_refreshes_to_current_contract`
- `tests/test_extended_style_9.py::test_style_nine_contract_reaches_content_first_compiler_without_routing_metadata`
- `tests/test_extended_style_9.py::test_style_nine_terminal_lock_reasserts_the_visual_focus_requirement`
- `tests/test_final_prompt_contract.py::ValidateFinalPromptTests::test_non_style09_rejects_style09_terminal_marker`
- `tests/test_final_prompt_contract.py::ValidateFinalPromptTests::test_rejects_duplicate_runtime_lock`
- `tests/test_final_prompt_contract.py::ValidateFinalPromptTests::test_style09_requires_exactly_one_terminal_lock`
- `tests/test_final_prompt_ir.py::FinalPromptIRTests::test_runtime_lock_requires_style_contract`
- `tests/test_final_prompt_renderer.py::RenderFinalPromptTests::test_style09_current_chinese_terminal_lock_is_reasserted`
- `tests/test_final_prompt_renderer.py::RenderFinalPromptTests::test_style09_requires_style_lock`
- `tests/test_final_prompt_renderer.py::RenderFinalPromptTests::test_style09_terminal_lock_ends_up_at_absolute_end`
- `tests/test_style_lock_snapshot.py::test_style09_lock_is_an_immutable_registry_snapshot`
- `tests/test_style_lock_snapshot.py::test_new_style09_lock_picks_up_new_registry_revision`
- `tests/test_style_lock_snapshot.py::test_documentation_revision_does_not_change_registry_lock`
- `tests/test_style_lock_snapshot.py::test_legacy_style09_lock_migrates_once_then_freezes`

### Track B
- `tests/test_imagegen_creative_brief.py::test_visual_structure_review_mode_is_explicit_and_auditable`
- `tests/test_imagegen_creative_brief.py::test_creative_brief_visual_grammar_defaults_to_empty_auxiliary_allowlist`
- `tests/test_imagegen_creative_brief.py::test_content_first_treats_visible_judgment_as_body_conclusion_with_style_typography_lock`
- `tests/test_imagegen_creative_brief.py::test_content_first_omits_tracking_metadata_and_avoids_repeated_rules`
- `tests/test_imagegen_creative_brief.py::test_semantic_only_handoff_preserves_thesis_logic_and_relations`
- `tests/test_imagegen_creative_brief.py::test_creative_brief_is_included_for_compact_style_contract`
- `tests/test_imagegen_deliverable_prompt.py::DualImageOverlayDeliverablePromptTests::test_compile_removes_evidence_caveats_and_placeholder_language`
- `tests/test_imagegen_deliverable_prompt.py::DualImageOverlayDeliverablePromptTests::test_compile_requires_style_lock`
- `tests/test_imagegen_deliverable_prompt.py::DualImageOverlayDeliverablePromptTests::test_render_prompt_omits_core_judgment_and_boundary`
- `tests/test_imagegen_deliverable_prompt.py::DualImageOverlayDeliverablePromptTests::test_style_nine_safety_rules_are_injected_into_imagegen_prompt`
- `tests/test_imagegen_handoff_modularization.py::test_facade_and_modular_prompt_builder_are_behaviorally_identical_for_style09`
- `tests/test_imagegen_handoff_modularization.py::test_content_first_prompt_keeps_current_canvas_text_and_template_contracts`
- `tests/test_imagegen_handoff_modularization.py::test_compiled_prompt_metadata_uses_current_compiler_and_style09`
- `tests/test_imagegen_micro_freedom.py::test_prompt_locks_macro_mutation_and_allows_region_internal_design`
- `tests/test_imagegen_no_visual_structure.py::ImageGenNoVisualStructureTests::test_build_page_prompt_omits_visual_structure`
- `tests/test_imagegen_no_visual_structure.py::ImageGenNoVisualStructureTests::test_page_prompt_places_visual_intent_after_global_style_as_final_priority`
- `tests/test_imagegen_no_visual_structure.py::ImageGenNoVisualStructureTests::test_render_prompt_template_omits_visual_structure`
- `tests/test_imagegen_no_visual_structure.py::StructureStyleDecouplingTests::test_style09_and_style10_project_identical_structure`
- `tests/test_imagegen_page_manifest.py::CyberpptPairManifestTests::test_strict_manifest_uses_content_first_canonical_prompt`
- `tests/test_imagegen_page_manifest.py::CyberpptPairManifestTests::test_style09_contract_is_single_complete_source_lock_after_stage02_summary`
- `tests/test_imagegen_prompt_diagnostics.py::test_analyze_prompt_reports_metrics_duplicates_and_known_conflicts`
- `tests/test_visual_grammar.py::test_open_visual_grammar_allows_expression_with_business_boundaries`

### Track C
- `tests/test_content_route.py::test_content_route_is_not_part_of_the_v2_lean_plan_contract`
- `tests/test_final_script_pages.py::FinalScriptPagesTests::test_compiles_pages_7_8_from_final_script_with_traceable_artifacts`
- `tests/test_final_script_pages.py::FinalScriptPagesTests::test_subtitle_migration_preserves_existing_body_copy`
- `tests/test_script_quality_modularization.py::ScriptQualityCompatibilityTests::test_baseline_fixture_matches_current_contract`
- `tests/test_script_quality_modularization.py::ScriptQualityCompatibilityTests::test_second_baseline_fixture_matches_current_contract`
- `tests/test_skill_contract.py::SkillContractTests::test_default_project_route_uses_current_strict_pipeline`
- `tests/test_text_output_contract.py::TextOutputContractTests::test_production_text_artifact_writers_disable_newline_translation`

## 完成标准

- Python 3.10：0 failed。
- Python 3.12：0 failed。
- Windows / macOS wheel smoke 保持通过。
- OfficeCLI smoke 保持通过。
- 不回退 Stage2 v3 已合并合同：Copy Contract、Composition Strategy、Visual Medium v2、Text Capacity、Visual Thesis、Full-slide Context、Acceptance Contract。
- 全部临时 patch helper / 专用 CI workflow 在 Ready 前清理。

## Track A / Step A1｜Runtime Lock 契约修复

状态：已完成

已完成工作：
- Runtime Style splitter 增加当前 Style 09 终端章节 `## 12｜最终风格收口｜最高视觉优先级` 的识别。
- `RuntimeLockIR` 强制 style contract 非空。
- Final Prompt validator 恢复 runtime style contract 唯一性校验、Style 09 terminal 唯一且位于绝对末尾校验、非 live style 禁止 terminal marker 校验。
- Style 09 缺少 style lock 的错误信息统一为可读口径。

验证结果：
- 8 项 Runtime Lock 定向回归全部通过。
- 未修改 `references/visual-system.md` 的现行 Style 09 文案，仅修复 runtime 对现行终端章节的识别与合同校验。

下一阶段工作：
- Track A / Step A2：迁移 Style 09/10 registry 合同断言到当前中文 Artifact Spec 执行版，并校正 live-contract / palette / terminal-focus 相关旧测试。

## Track A / Step A2｜Style 09/10 Live Contract 对齐

状态：已完成

已完成工作：
- Style 09 测试断言从已废弃英文 prompt contract 迁移到当前 `references/visual-system.md` 中文 GPT Image 2.5 Artifact Spec 执行合同。
- Style 09 的 palette、主焦点、构图机制、场景/图标职责与终端收口均按当前 live contract 验证。
- Style 10 测试改为验证当前独立 `visual-system-10.md` 的 scene-led / locked-copy 合同。
- 修正 Style 10 registry 的 reference sample：从 `palette-09.png` 改为仓库已存在的专属 `palette-10.png`。

验证结果：
- `tests/test_extended_style_9.py + tests/test_extended_style_10.py` 全部通过。
- 未回退当前 Style 09/10 live contract；测试与 registry 对当前实际资源完成对齐。

下一阶段工作：
- Track A / Step A3：将 4 项 Style Lock Snapshot 历史测试迁移到当前“live style 默认刷新、显式 immutable 才冻结”的正式策略，并补足行为边界验证。

## Track A / Step A3｜Style Lock Live/Snapshot 策略对齐

状态：已完成

已完成工作：
- 将 4 项 Style Lock Snapshot 历史测试迁移到当前正式策略：Style 09/10 默认读取 live contract，只有显式 `resolved_contract_is_immutable=true` 才冻结。
- 补充默认 live refresh、新 lock 获取当前版本、显式 immutable 冻结、legacy lock 持续跟随 live contract 四类行为边界。
- 修正 `style_library.py` 注释与 docstring，使其与现行 live-refresh 实现一致。

验证结果：
- `tests/test_style_lock_snapshot.py + tests/test_extended_style_9.py + tests/test_extended_style_10.py` 全部通过。
- 未改变 live-refresh 生产行为，仅纠正历史测试和过时注释。

下一阶段工作：
- Track A 聚合验收：运行 Track A 原 18 项失败涉及的完整测试族和标准全量 CI，确认 Track A 历史失败清零并计算剩余基线失败数；随后清理 Track A 临时 workflow/helper，进入 Track B。

## Track A｜聚合验收与收口

状态：已完成

已完成工作：
- 对 Track A 涉及的 Runtime Lock、Style 09/10 live contract、Style Lock refresh/snapshot 全测试族执行聚合回归。
- 使用同一 branch head 的标准 Python 3.10 / 3.12 全量 CI 对原 47 项失败集合重新做精确差分。
- 清理 Track A 开发期专用 workflow 与 patch helper，不将临时门禁带入 Track B。

验证结果：
- Track A 聚合门禁 run `34418949118`：89 passed，5 subtests passed。
- 标准全量 CI run `34418955910`：Python 3.10 与 3.12 均为 29 failed / 2018 passed / 8 skipped / 49 subtests passed。
- 两个 Python 版本剩余 29 项失败集合完全一致；Track A 原 18 项全部消失，新增失败 0。
- 剩余 29 项精确对应 Track B 22 项 + Track C 7 项。
- Windows wheel、macOS wheel、OfficeCLI smoke 全部通过。

下一阶段工作：
- Track B / Step B1：从 ImageGen Creative Brief 6 项失败开始，核对当前 content-first / Stage2 v3 Prompt 合同，区分生产行为回归与旧 wording/snapshot 断言漂移。

## Track B / Step B1｜Creative Brief 合同对齐

状态：已完成

已完成工作：
- 修复 review-mode composition guidance 的生产排序：从固定索引插入改为置于页面语义/逻辑之后、presentation/canvas contract 之前，避免切入标题/使命/核心判断非上屏上下文。
- Creative Brief 辅助标签测试迁移到当前“允许但必须由内容支撑”的 visual grammar，不再要求已废弃的 empty allowlist / one-to-one mapping。
- 标题与核心判断测试迁移到 Stage2 v3 的显式非上屏语义上下文，继续验证其不进入上屏内容素材。
- Style09 正文结论测试迁移到当前中文 live contract 与 `【结论句要求｜不上屏】`，保留 terminal runtime lock 末尾校验。

验证结果：
- `tests/test_imagegen_creative_brief.py` 全文件回归通过。
- 6 项历史 Creative Brief 失败清零；仅 1 项涉及生产排序修复，其余为旧 wording/authority 断言迁移。

下一阶段工作：
- Track B / Step B2：处理 Deliverable Prompt 4 项失败，核对 style lock 必填、核心判断/边界不上屏、Style09 安全规则与 evidence placeholder 清理。
