# `script_quality/onscreen.py` 二级拆分评估

本评估按任务书要求基于实际函数与调用关系进行，不以文件行数作为拆分依据。

- 函数总数：54
- 识别的规则/辅助簇：7
- 跨簇直接调用边：8
- 各簇函数数：{"detail_completeness": 6, "hierarchy": 10, "label_policy": 2, "page_expression": 2, "parse_normalize": 2, "shared_other": 30, "source_visibility": 2}

结论：本轮保持 `onscreen.py` 的现有实现边界，不再做二级物理拆分。当前规则簇仍通过共享 normalize、模块层级、正文角色与页面表达状态发生直接交叉调用；在 P0/P1 主链与 `analysis_audit` 同轮迁移时继续移动这些规则会扩大行为回归面。该结论符合任务书“只有规则簇具备独立输入、独立测试和较少共享状态时才迁移”的约束。

后续触发拆分的条件：某一规则簇可在不读取其他簇内部状态的前提下独立单测，并且 `test_script_quality_contract.py` 与 `test_script_quality_modularization.py` 的 frozen behavior 能保持逐项一致。
