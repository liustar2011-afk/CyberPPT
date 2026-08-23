# Style09 配图能力检查

## 结论

**技术判断：SUPPORT WITH CONDITIONS。**

当前 `Style09` 的源头契约会实质性降低配图出现的概率。图像生成通道仍在，配图没有被关闭；变化发生在风格规则的选择条件、空间优先级和终端执行锁。该风格现在更适合“文字与结构优先、在具名实体场景中补充照片”的领导汇报版式，已偏离此前“语义场景优先”的表现取向。

## 已验证证据

| 位置 | 当前规则 | 对配图的影响 |
| --- | --- | --- |
| `references/visual-system.md`，Style09 开头与第 1 节 | 页面由 shapes、containers、color fields、text hierarchy 与 photography 共同构成 | 摄影从主语义载体变为与结构元素并列的候选。 |
| 第 2 节第 2—3 步 | 照片只在“具名的物理环境或物件”可增加识别价值时使用；文字先占空间，空间紧张时缩小、裁切、简化或移除 anchor | 抽象业务页和文字较密页面会自然走向无配图的结构场。 |
| 第 5 节 | 仅在页面使用照片时采用“一张主元素 + 若干辅助碎片” | 该节保留了配图表现力，但其触发依赖前述严格选择条件。 |
| Style09 最终执行锁 | 要求生成结果以 shapes and containers 为主，并将 photography 放在次级位置 | 该段位于实际提示词的绝对末尾，拥有最高指令权重，会压过前文对照片的许可。 |
| `scripts/imagegen_pipeline/artifact_prompt.py` 的 `_style09_visual_responsibility` | 明确不再传递 `use_scene` 和辅助配图预算，最终是否使用图片完全交由 Style09 源头规则裁决 | 页面级设计无法补偿源头契约的保守取向。 |

## 反例检查

该结论不意味着所有 Style09 页面都会失去配图。源头规则仍允许设施、设备、真实场地、业务场景、内容资产、文档转化与行业现场等具名且可识别的素材；第 5 节也允许主图加辅助碎片。具备明确实体锚点且文字量可控的页面仍可生成配图。

## 同步发现：终端锁兼容回归

使用仓库 `.venv/bin/python3` 运行 Style09 相关测试，36 项中 34 项通过、2 项失败：

- `tests/test_final_prompt_renderer.py::RenderFinalPromptTests::test_style09_terminal_lock_ends_up_at_absolute_end`
- `tests/test_final_prompt_renderer.py::RenderFinalPromptTests::test_style09_terminal_lock_preserves_hard_constraints`

失败原因是旧测试构造的英文标记 `### Final ImageGen execution lock — hard` 已不再对应当前源头文件中的中文终端锁 `【风格09最终执行锁｜最高优先级】`。这不会直接关闭图片生成，却说明 Style09 终端锁的兼容验证已失效，后续修改应一并修复测试和兼容路径。

## 建议的修复方向

若产品目标是恢复“根据页面语义主动配图”的能力，源头风格应重新明确以下优先级：

1. 具备可识别业务对象、动作、状态或结果的页面，优先采用一个语义场景或具体物件作为锚点。
2. 抽象枚举、比较、层级与高密度文字页使用结构场；保留无图作为合理分支。
3. 终端执行锁须与该规则一致，改为“文字安全区优先，选中的语义锚点保持可识别”，避免以 shapes/containers 的固定偏好覆盖已经选定的照片或场景。
4. 保留禁用通用办公图、图标墙、装饰性 3D 与伪文字的约束，确保恢复配图不会退化成 stock 图或装饰图。

这是一项源头风格契约调整；改动后应为“具名实体页有场景、抽象高密度页有结构场”的两类页面各补一条提示词级回归测试。

## 修复状态（2026-08-23）

已完成以下修复：

1. Style09 开头、第 1 节、第 2 节、第 5 节和最终执行锁统一为“语义锚点优先”规则。具名或可直接推断的业务实体、环境、行动、状态和结果会主动使用可识别的场景、物件或证据片段；抽象枚举、比较、层级和高密度文字页可使用结构场。
2. 文字阅读尺度继续优先。空间紧张时先裁切或简化已选锚点，只有保留锚点会损害锁定文字可读性时才移除。
3. `deliverable_prompt.py` 同时识别旧英文终端锁和当前中文终端锁，保证实际送图提示词末尾保留完整、当前生效的终端规则。
4. 回归测试覆盖当前中文终端锁的重申，以及源头 Style09 的场景锚点契约。

验证命令：

```sh
.venv/bin/python3 -m pytest tests/test_extended_style_9.py tests/test_extended_style_9_assets.py tests/test_final_prompt_renderer.py tests/test_artifact_prompt.py tests/test_final_prompt_contract.py tests/test_imagegen_page_manifest.py -q
```

结果：`57 passed`。
