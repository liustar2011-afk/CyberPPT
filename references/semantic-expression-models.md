# 语义表达模型库

本文件是 CyberPPT 的单一、版本化表达模型库。模型只组织已确认的来源语义；不得补造事实、因果、对象或结论。`source_native` 永远可选。

`lifecycle` 支持 `candidate`、`verified`、`deprecated`：仅已验证模型参与自动候选排序；候选模型经实际页面复核后由维护者提升，废弃模型保留历史但不再推荐。现有未标注条目视为已验证，以兼容首版模型库。

## source_native
<!-- model
id: source_native
family: native
semantic_signature: []
slots: []
forbidden_inferences: []
-->
### Expression structure

沿用来源的已证实论证顺序；只进行不改变关系的编辑压缩。

## scqa
<!-- model
id: scqa
family: narrative
semantic_signature: [context, tension, response]
slots: [situation|required, complication|required, question|implicit_allowed, answer|required]
forbidden_inferences: [不得把隐含问题伪装为原文直接提问]
-->
### Expression structure

S → C → Q → A。情境交代共同前提；矛盾呈现张力；问题可由矛盾等强度归纳；回应只使用来源已有方案。

## pyramid_principle
<!-- model
id: pyramid_principle
family: narrative
semantic_signature: [judgment, support]
slots: [governing_thought|required, supporting_reasons|required]
forbidden_inferences: [不得把并列事实提升为结论]
-->
### Expression structure

结论先行 → 2–4 条相互独立的支撑理由 → 必要证据。

## mece_issue_tree
<!-- model
id: mece_issue_tree
family: problem_analysis
semantic_signature: [problem, decomposition]
slots: [problem|required, branches|required]
forbidden_inferences: [不得把未穷尽的来源事项标为MECE]
-->
### Expression structure

问题 → 互斥分支 → 证据/待验证项。

## three_c
<!-- model
id: three_c
family: management_consulting
semantic_signature: [customer, competitor, company]
slots: [customer|required, competitor|required, company|required]
forbidden_inferences: [缺少竞争或客户证据时不得使用]
-->
### Expression structure

客户/需求 → 外部竞争或替代 → 自身能力与定位。

## porters_five_forces
<!-- model
id: porters_five_forces
family: management_consulting
semantic_signature: [industry, rivalry, suppliers, buyers, substitutes, entrants]
slots: [industry|required, rivalry|required, suppliers|required, buyers|required, substitutes|required, entrants|required]
forbidden_inferences: [缺少完整行业竞争证据时不得使用]
-->
### Expression structure

行业中心 → 五类竞争力量 → 竞争含义。

## value_chain
<!-- model
id: value_chain
family: management_consulting
semantic_signature: [value_activities, value_creation]
slots: [activities|required, value_linkage|required]
forbidden_inferences: [不得把组织清单写成价值链]
-->
### Expression structure

价值活动链 → 关键能力/接口 → 价值形成位置。

## mckinsey_7s
<!-- model
id: mckinsey_7s
family: management_consulting
semantic_signature: [strategy, structure, systems, skills, staff, style, shared_values]
slots: [strategy|required, structure|required, systems|required, skills|required, staff|required, style|required, shared_values|required]
forbidden_inferences: [缺少组织诊断证据时不得使用]
-->
### Expression structure

七要素一致性 → 失配/协同 → 调整重点。

## business_model_canvas
<!-- model
id: business_model_canvas
family: business_design
semantic_signature: [customers, value_proposition, channels, relationships, revenue, resources, activities, partners, costs]
slots: [customer_segments|required, value_proposition|required, channels_or_relationships|required, resources_activities_partners|required, costs_or_revenue|required]
forbidden_inferences: [缺少客户或价值交换证据时不得使用]
-->
### Expression structure

客户与价值主张 → 交付和关系 → 关键资源/活动/伙伴 → 成本与收益逻辑。

## togaf_adm
<!-- model
id: togaf_adm
family: enterprise_architecture
semantic_signature: [business_architecture, data_application_architecture, technology_architecture, migration, governance]
slots: [architecture_vision|required, business_architecture|required, information_systems_architecture|required, technology_architecture|required, migration|required, implementation_governance|required]
forbidden_inferences: [不得把单一技术方案称为企业架构全生命周期]
-->
### Expression structure

架构愿景 → 业务/数据应用/技术架构 → 差距与机会 → 迁移路线 → 实施治理。

## dama_dmbok
<!-- model
id: dama_dmbok
family: data_governance
semantic_signature: [data_domain, ownership, standards, quality, lifecycle, sharing]
slots: [data_objects|required, governance_roles|required, standards_quality|required, lifecycle_or_service|required]
forbidden_inferences: [不得把数据资源目录等同于数据治理体系]
-->
### Expression structure

数据对象/域 → 权责与规则 → 标准质量/生命周期 → 共享使用或服务运营。

## itil4_svs
<!-- model
id: itil4_svs
family: service_management
semantic_signature: [demand, service, value, operations, improvement]
slots: [demand_or_opportunity|required, service_value_chain|required, governance_or_practices|required, continual_improvement|required]
forbidden_inferences: [不得把一次性交付称为持续服务运营]
-->
### Expression structure

需求/机会 → 服务价值链 → 治理与实践 → 持续改进 → 价值共创。

## cobit_2019
<!-- model
id: cobit_2019
family: it_governance
semantic_signature: [governance_objectives, processes, organizational_structures, information, people, policies, infrastructure]
slots: [governance_objectives|required, components|required, metrics_or_controls|required]
forbidden_inferences: [不得仅以流程图宣称完成治理体系]
-->
### Expression structure

治理目标 → 治理组件 → 责任/控制/度量 → 监督改进。

## iso_iec_27001
<!-- model
id: iso_iec_27001
family: security_governance
semantic_signature: [assets, risks, controls, audit, improvement]
slots: [risk_scope|required, controls|required, assurance_or_audit|required]
forbidden_inferences: [不得把技术措施等同于完整ISMS]
-->
### Expression structure

资产与风险 → 控制措施 → 审计证据 → 管理评审与持续改进。

## pmbok
<!-- model
id: pmbok
family: project_delivery
semantic_signature: [outcomes, deliverables, stakeholders, risks, schedule]
slots: [outcomes|required, delivery_scope|required, stakeholders|required, risks_or_constraints|required]
forbidden_inferences: [不得从空泛目标生成进度或资源承诺]
-->
### Expression structure

目标价值 → 交付范围 → 干系人/责任 → 节奏与风险。

## adkar
<!-- model
id: adkar
family: change_management
semantic_signature: [change_need, adoption, knowledge, ability, reinforcement]
slots: [awareness|required, desire|required, knowledge|required, ability|required, reinforcement|required]
forbidden_inferences: [缺少受影响角色和采用信息时不得使用]
-->
### Expression structure

认知 → 意愿 → 知识 → 能力 → 强化。

## stage_gate
<!-- model
id: stage_gate
family: implementation_governance
semantic_signature: [stages, validation, decision_gates, feedback]
slots: [stages|required, gate_criteria|required, decision_owner|required]
forbidden_inferences: [不得把时间顺序清单写成阶段门]
-->
### Expression structure

阶段目标 → 交付/验证 → 决策门 → 反馈与下一阶段条件。

## zachman
<!-- model
id: zachman
family: information_architecture
semantic_signature: [scope, business, system, technology, operations]
slots: [perspectives|required, architecture_objects|required]
forbidden_inferences: [不得将单一架构视图替代多视角描述]
-->
### Expression structure

范围、业务、系统、技术、运行等视角下的对象—关系矩阵。
