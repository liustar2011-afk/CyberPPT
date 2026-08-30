# Stage 01 规则硬编码审计

日期：2026-08-30

## 审计结论

技术判断：`SUPPORT`

当前 Stage 01 规则体系存在较大范围的语义关键词硬编码。部分规则承担格式、
安全、交付洁净度检查，使用确定性正则合理；另一部分规则通过少量中文动词、
名词或项目短语推断论证角色、业务关系、成熟度、主体类型和语义完整性，并将
推断结果作为阻断错误。这类规则已经越过确定性校验的可靠边界。

本轮定位到两个并行实现面：

1. `script_engine` 的新 Final Script / Deck Plan 审计；
2. `cyberppt.script_quality` 的旧脚本质量审计。

两套实现均保留语义词表，部分能力重复，判定口径存在漂移。图谱检索统计显示：
`script_engine` 范围内有 61 处 `re.compile` 命中，`cyberppt/script_quality`
范围内有 85 处命中。正则数量只用于定位，不能直接等同于问题数量。

## 判定标准

### A 类：适合确定性阻断

- JSON Schema、必填字段、枚举、ID、引用存在性和引用范围；
- 页码连续性、章节顺序、哈希和输入输出绑定；
- Markdown 标记泄漏、内部元语言、明确禁用句式；
- 明确字符、标点、编号和格式协议；
- 来源状态、责任、条件等结构化字段之间的确定性兼容关系。

### B 类：只能作为候选告警

- 依靠动词判断一句话是否具有完整主谓关系；
- 依靠名词或动词判断 argument role、页面关系或主体类型；
- 依靠字符数判断语义完整、重要性或证据充分性；
- 依靠通用词判断来源力度是否升级；
- 依靠文本相似度判断事实是否相同、重复或得到证明。

### C 类：必须移出通用规则

- 特定项目、行业、客户、方案或历史页面的专用短语；
- 从单个项目事故提炼、没有通用结构依据的禁止表达；
- 需要业务判断却被写成全局正则的规则。

## 高优先级发现

### P0-1：全局 AUTHOR 合同包含具体项目知识

位置：`.agents/skills/cyberppt-script-workflow/references/authoring-contract.md`

证据：合同直接使用“国家数据基础设施建设部署”“中电联先行先试项目”
“电力领域数据基础设施标准体系”等项目对象作为优选措辞或完整示例。

影响：该文件是所有 AUTHOR、CRITIQUE、REWRITE 的唯一操作性作者规则。
具体项目对象进入全局合同后，会对其他项目的用词、对象选择和写作判断形成
提示污染。示例还可能被模型误当作当前材料事实。

处理建议：把项目实例迁移到独立、非默认加载的测试夹具；全局合同只保留抽象
正例结构，并明确示例中的对象均为占位符。

### P0-2：通用规则表包含供需预测项目专用指纹

位置：`cyberppt/script_quality/rules.yaml:89-95`

证据：跨页指纹固定匹配“数据接入—质量治理—模型预测”和“哪版数据—哪版
口径—哪版模型”。

影响：这些词只覆盖一类项目内容，却在全局规则表中启用。其他项目中的真实
重复无法覆盖，相关项目中的合法复用可能产生告警。

处理建议：删除全局业务指纹；跨页重复应基于来源事实 ID、模块 provenance、
论证角色和规范化语义单元计算。

### P0-3：全局禁用表硬编码电力行业业务对象

位置：`contracts/banned-phrasing.json:45-54`

证据：`underspecified-business-object` 直接拦截“电力行业能力建设”以及
“相关任务”等短语。

实测：一个来源可能正式使用的“电力行业能力建设纳入年度安排”在
`core_message` 和 `onscreen.heading` 中均被阻断。

影响：禁用表从交付洁净度规则扩张为业务语义判断，同时携带特定行业词。
它无法区分来源原词、作者概括和确实缺失业务对象的句子。

处理建议：移除行业词；“对象是否缺失”改由来源绑定、实体槽位和 claim
结构校验。缺少结构化绑定的旧项目最多给出告警。

### P0-4：关键词分类结果被用于阻断“错误并列”

位置：

- `cyberppt/script_quality/onscreen.py:134-140`
- `cyberppt/script_quality/onscreen.py:545-735`
- `cyberppt/script_quality/presentation.py:300-311`

证据：系统依据“是/包括/形成/需要/不足/建设”等词，把子项分类为
attribute、change、demand、gap、response；同组出现两个分类便可能触发
`ONSCREEN_FALSE_PARALLEL_SEMANTICS` 阻断。

实测：“建立在既有基础上的现状判断”被分类为 `response`。该分类来自“建立”
的字面命中，没有使用 Foundation 的 `argument_duty`、`status` 或关系字段。

影响：合法分类可能被拆散，真实混维度结构也可能通过换词规避。

处理建议：删除关键词角色分类的阻断权。优先读取 Foundation 和 AUTHOR 模块
绑定中的结构化角色；没有结构化角色时转人工告警。

## 中优先级发现

### P1-1：新 Script Engine 仍用文本正则推断来源状态和关系

位置：

- `script_engine/analysis_audits/common.py:33-49`
- `script_engine/analysis_audits/final_script.py:929-960`

规则通过固定词组识别 optionality、universality、progression 和 gap，并直接
产生最终脚本问题。Foundation 已有 `status`、`semantic_status`、
`argument_duty`、`claim_role` 和 argument relations，这些结构化字段尚未成为
主要判据。

处理建议：状态和关系判定迁移到结构化字段；文本规则只检查结构化状态是否在
可见文案中得到表达，且必须绑定到具体来源事实或模块。

### P1-2：语义完整性由固定谓词和字符阈值决定

位置：`script_engine/contracts.py:264-380`

`_SEMANTIC_PREDICATES` 词表与最短字符数共同决定段首或模块标题是否为完整
命题。实测“项目已经成为重点”会被判定为具有完整语义谓词，该句仍缺少重点
事项和判断边界。

影响：规则同时存在误放和误杀；作者可以通过补一个高频动词通过检查。

处理建议：保留长度检查作为提示；完整性阻断依赖结构化 actor、action、object、
status、condition 槽位及来源绑定。

### P1-3：关系是否可见由关系—词语对照表决定

位置：`cyberppt/script_quality/relationships.py:25-95,139-166`

`causes`、`supports`、`responsible_for` 等关系分别映射到若干中文词。实测
“市场变化形成新的问题”仅因包含“形成”便被认定为呈现 `causes` 关系。

代码已对 `page_logic_contract=required` 绕过该词表，说明结构化关系链已经存在
更可靠路径；legacy 分支仍会使用弱词表。

处理建议：完成结构化关系链迁移；legacy 词表降级为诊断提示并标注低置信度。

### P1-4：旧审计含跨项目残留对象

位置：`cyberppt/script_quality/relationships.py:81-95`

组合范围固定包含“课程包、场景包、课程、岗位”等对象，明显来自另一类业务
项目。类似残留还存在于 actor、constraint、anti-pattern、scope 和 implementation
词表中。

处理建议：业务对象必须来自项目 Foundation 的 entities/concepts；通用引擎只
保留关系类型和结构协议。

### P1-5：规则系统重复导致判定漂移

新引擎的 `script_engine/contracts.py`、`analysis_audits/*` 与旧引擎的
`cyberppt/script_quality/*` 同时检查标题、上屏、状态、关系、密度和来源覆盖。
同一意图存在不同词表、不同阈值和不同豁免条件。

影响：一个入口通过、另一个入口失败；修复一个规则后，另一套旧规则仍可能
继续产生相同问题。

处理建议：建立单一规则注册表和单一执行入口；legacy 兼容层只做格式转换，
不保留第二套语义判定。

## 可保留的确定性规则

以下规则没有发现同类架构问题，可继续保持阻断：

- Source ID、Source Unit ID、页码和章节编号格式；
- JSON Schema、枚举、必填字段和未知引用；
- Markdown/后台元数据泄漏；
- 明确禁用的否定转折句式；
- 表格行、目录、版本号和日期等结构元数据误入正文；
- 哈希、审批、输入输出和 Stage 02 锁定文本绑定；
- 明确的页面数量、顺序和文件存在性检查。

字符数、密度、重复度和相似度适合作为候选告警，不能单独证明语义错误。

## 根因判断

1. 早期项目事故通过新增词表快速修复，专用规则逐渐进入全局路径；
2. 新旧两套审计并存，结构化 contract 与文本启发式没有完成迁移；
3. Final Script 仅有页面级 `source_refs`，缺少模块级 claim/evidence 绑定；
4. 规则定义缺少 scope、confidence、severity rationale、owner、expiry 和反例测试；
5. 测试大量验证“某个关键词能触发”，较少验证同义改写、合法反例和跨领域输入。

## 建议整改顺序

### 第一阶段：止损

1. 将所有项目专用规则移出全局 Skill、JSON 和 YAML；
2. 将语义词表产生的阻断统一降为告警；
3. 标注每条规则的 `kind=format|safety|semantic_heuristic|project_specific`；
4. CI 禁止 `project_specific` 规则进入默认 profile。

### 第二阶段：结构化替代

1. 为 Final Script 上屏模块增加 claim、evidence、relation、derivation provenance；
2. 从 Foundation 派生 status、argument duty、actor、condition 和责任强度；
3. 用 ID 与结构兼容矩阵校验来源边界、状态、责任和论证关系；
4. 无法由结构确定的质量判断交给 AUTHOR/Critic 和人工复核。

### 第三阶段：收敛执行面

1. 合并新旧语义审计，只保留一个权威执行入口；
2. legacy 层只做输入投影和兼容，不继续发展独立语义规则；
3. 为每条保留规则增加正例、反例、同义改写和跨领域测试；
4. 删除没有调用、与结构化 contract 重复或长期只能产生噪声的规则。

## 建议验收标准

- 默认规则中没有客户、行业或具体项目专名；
- 语义阻断能够指出具体 claim ID、evidence ID、关系和不兼容字段；
- 改写同义词不会改变结构化审计结论；
- 合法反例不会因命中单个动词或名词而失败；
- 同一产物只有一个权威语义审计结果；
- 新增规则必须说明适用范围、置信度、阻断理由和反例覆盖。

## 本轮边界

本轮完成静态代码、规则表、调用链和四个最小反例检查。尚未对全部历史项目
逐一运行差分审计，因此未量化每条规则在真实项目上的误报率。下一轮应建立
跨项目语料集，分别记录每条规则的 true positive、false positive 和 bypass。
