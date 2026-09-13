# Stage 01 / Stage 02 字段调整开发与验证

日期：2026-09-13。

## 已实现行为

1. Stage 01 的 deck.delivery_mode 经最终 Markdown 页前的“交流方式”传到 ScriptPage、Stage 02 intake 和当前正式 content-first 提示词。self_read 与 presented 分别表达独立阅读和演讲辅助；缺省使用 self_read，未知值或冲突声明阻断解析。正文中的同名引用不会改变整套稿的模式。
2. 当前正式编译统一通过 content_text 读取普通内容。新 1.2 稿取完整稿，外部稿取适配后的正文，旧 1.0/1.1 稿保留原先编写的上屏文字。旧稿不同于上屏稿的 full_prose 继续作为完整背景传入，避免关键条件丢失。
3. 新建 intake 页声明 content_contract_version: 2，并携带 source_mode 和 delivery_mode。旧正文别名与嵌套字段仍序列化供兼容消费者读取；本次隔离它们的正式消费与身份职责，未全仓删除字段。
4. 完整 intake 的 semantic_sha256 继续检查所有持久化字段。生产输入指纹、关系判断和逐页复用改用版本化 production_page_input，排除重复别名与旧拓扑诊断，保留实际内容、额外背景、交流方式、标题、使命、保真项和来源语义。
5. 历史未声明版本的 intake 继续使用整页身份，不自动批量迁移缓存。新合同与旧合同的摘要不同；回执只有在其对应身份及实际提示词等检查仍一致时才可复用。新的正式提示词增加交流方式，因此已有图片不能凭旧提示词直接认定可复用。
6. v4 关系合同保持现有字段。Skill 明确以 relations / constraints / uncertainties 承接对象、责任、状态、数字所指、条件附着和来源等权性。新证据优先引用 content_text；新合同中的 onscreen_text 证据别名对当前 content_text 校验，防止引用过期副本。

Stage 01 继续保存完整语义，fidelity_text 继续仅约束少量精确字符串；本次未新增强制平台型、机制型、架构型、视觉焦点、节点图或布局字段。

## 验证结果

仓库解释器：/Volumes/DOC/CyberPPT/.venv/bin/python3。

组合回归结果：848 passed、2 skipped、5 subtests passed。两个跳过项均因 power-supply-demand 历史项目产物缺失。

执行范围：

```sh
.venv/bin/python3 -m pytest \
  tests/test_stage02_field_contract.py \
  tests/test_stage02_fidelity_intake.py \
  tests/test_relationship_judgment_v4.py \
  tests/test_stage02_cyberppt_script_adapter.py \
  tests/test_stage02_handoff.py \
  tests/test_script_quality_contract.py \
  tests/test_stage02_page_local_reuse.py \
  tests/test_stage02_manifest_reuse_identity.py \
  tests/test_stage02_input_identity.py \
  tests/script_engine -q -rs
```

新增字段合同测试覆盖：

- self_read / presented 经渲染、解析、intake 和实际编译提示词往返；
- 1.0/1.1 上屏稿与完整背景区分；
- 外部结构化稿与自由正文适配；
- 错误或冲突模式拒绝、正文引用范围保护；
- 诊断变化不改变新生产身份，语义变化导致失效；
- 原有历史摘要与旧稿读取兼容；
- 过期正文别名不能作为新关系证据；
- 即使刷新完整性校验和，非法内容合同仍被 audit 拒绝；
- 正式 prepare_preflight 与 attach_page_input_sha256 使用同一语义投影，改变交流方式会要求重新判断。

现有关系回归包含正式 final-script-pages 子进程调用，验证只编译审阅、同批次 dry-run 续跑、实际提示词/manifest 写入及旧关系阻断。三个修改后的 Skill 通过 quick_validate，git diff --check 通过。

[完整测试输出](/tmp/cyberppt-stage1-skill-review-20260913/field-contract-tests.txt)

## 修改文件

### 字段传递与正文消费

- [Stage 01 Markdown 渲染](/Volumes/DOC/CyberPPT/script_engine/render.py)
- [ScriptPage 模型](/Volumes/DOC/CyberPPT/cyberppt/script_quality/models.py)
- [脚本解析](/Volumes/DOC/CyberPPT/cyberppt/script_quality/parsing.py)
- [Stage 02 输入及生产字段投影](/Volumes/DOC/CyberPPT/cyberppt/stage02_input.py)
- [正式提示词输入适配](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/page_manifest.py)
- [正式提示词编译](/Volumes/DOC/CyberPPT/scripts/imagegen_pipeline/handoff/prompt.py)

### 身份与复用

- [生产预检](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/preflight.py)
- [逐页复用](/Volumes/DOC/CyberPPT/cyberppt/stage02_production/page_reuse.py)
- [关系判断校验](/Volumes/DOC/CyberPPT/cyberppt/visual_stage/relationship_judgment.py)
- [新增行为测试](/Volumes/DOC/CyberPPT/tests/test_stage02_field_contract.py)

### 流程与 Skill

- [主流程](/Volumes/DOC/CyberPPT/docs/CYBERPPT_WORKFLOW.md)
- [Stage 01 Skill](/Volumes/DOC/CyberPPT/.agents/skills/cyberppt-script-workflow/SKILL.md)
- [Stage 02 Skill](/Volumes/DOC/CyberPPT/.agents/skills/cyberppt-stage02-editable-pptx/SKILL.md)
- [关系判断 Skill](/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/SKILL.md)
- [v4 关系合同](/Volumes/DOC/CyberPPT/vendor/skills/ppt-visual-structure-designer/references/relationship-contract.md)

## 验证边界

本次验证字段、正式编译消费、输入校验和续跑身份，未调用真实生图服务、OCR 或 PowerPoint 渲染，不能据此宣称视觉质量已提高。constraints 的语义依据仍由主 Agent 审核；字符串结构校验与引用定位不能证明业务判断正确。

工作区预先存在的风格文件、stage02_adapter.py 和其他未跟踪内容未纳入本次修改。未提交 Git。
