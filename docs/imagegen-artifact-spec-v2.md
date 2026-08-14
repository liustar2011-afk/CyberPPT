# ImageGen artifact-spec-v2 正式提示词链路

CyberPPT正式链路把GPT Image输出定义为可交付的PPT正文视觉资产，而不是普通插画。默认编译器`artifact-spec-v2`只读取三项已审计权威来源：

- Stage 02 handoff：页面使命、核心判断、精确正文与2048×1024正文画布。
- `visual/deck-visual-spec.json`：选中候选的视觉论点、证据关系、载体/场景策略、空间组织与文字归属。
- 项目style lock：完整视觉语言合同。

编译器在内存中生成不可变的`PageArtifactSpec`，不新增持久化业务真值文件，然后按固定顺序输出九段：

1. Deliverable / 成品规格
2. Communication goal / 页面使命
3. Visual thesis / 核心视觉论点
4. Evidence & relationships / 证据与关系
5. Visual carrier / 视觉载体
6. Composition / 空间组织
7. Art direction / 视觉语言
8. Typography & exact text / 文字资产合同
9. Hard constraints / 硬约束

`visual-design-decisions.json`使用`cyberppt.visual_design_decisions.v3`。每个候选必须提供自己的`visual_thesis`；选中页必须提供完整`execution_design`，包括业务对象、视觉焦点、语义角色、场景布尔策略、场景类型、文字融合、空间组织和关系编码。审计器会阻断这些字段在`deck-visual-spec.json`中的任何漂移。

正式入口：

```bash
python -m scripts.dual_image_overlay.imagegen_handoff \
  <project> --script <approved-script.md> --style-lock <style-lock.json> \
  --pages 1-10 --batch-name chapter01
```

审批、canonical prompt、manifest和实际发送复用同一编译结果。批准稿允许人工修改，但进入manifest前必须再次通过九段顺序、段落非空、精确可见文字、后台ID禁入和Style09唯一终端锁校验。批准后不得追加prompt enrichment。

`visual/generation-prompts.md`和compact blueprint仅保留为旧结构预览/兼容诊断，不能进入已审批生产链路。旧编译器仍可显式指定：

```text
--prompt-compiler content-first-v1
--prompt-compiler creative-brief-v1
--prompt-compiler legacy
```
