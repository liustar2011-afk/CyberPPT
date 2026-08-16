#!/usr/bin/env python3
"""Author the confirmed V16 layer-four outline from current foundation inputs.

This is a bounded project-level authoring generator. It does not reinterpret the
DOCX or run any legacy Stage 01 compiler. It groups source level-three detail
under its owning level-two page, preserves source headings and order, and keeps
all normalized facts traceable through page evidence or explicit dispositions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


GOAL = (
    "向电力行业潜在合作方和需求方说明，依托电力领域数据基础设施，以国家数据基础设施电力行业节点、"
    "行业数据与专业能力运营平台、多主体协同和价值共创载体为支撑，组织数据资源、模型能力、专业能力和技术能力，"
    "围绕需求形成可订购、可交付、可评价的数据产品、数据服务和场景服务，并贯通产品形成、订单履行、运营反馈、"
    "计量结算与持续改进，建立合作运营闭环。保持源材料章节标题、内容标题和顺序，采用政府公文式、央企正式交流语体；"
    "不要把交流目标中的受众或行动要求升级为源材料事实。"
)


PAGE_META: dict[str, dict[str, Any]] = {
    "sec-0002": {
        "question": "方案为什么提出建设行业数据服务与场景服务运营合作？",
        "mission": "承接源材料对建设背景、业务需求和合作必要性的说明。",
        "judgment": "电力业务数字化、市场化和智能化程度持续提升，跨主体数据协同需求不断增长；分散资源尚未形成稳定的行业服务供给，行业发展需要建立统一的连接、可信使用和服务运营基础。",
        "value": "明确方案所要回应的背景与必要性，为总体定位和架构说明提供前提。",
        "role": "background",
        "visual": "judgment_evidence",
        "logic": "以背景事实为入口，沿需求与建设必要性汇聚到本页判断。",
    },
    "sec-0003": {
        "question": "电力领域数据基础设施在方案中承担什么总体定位？",
        "mission": "说明行业节点、运营平台和多主体协同载体共同构成的总体定位。",
        "judgment": "电力领域数据基础设施承担行业中枢和价值释放引擎定位，并组织行业资源与应用需求衔接。",
        "value": "建立全篇共同的业务对象和定位边界，区分后续服务体系与运营机制。",
        "role": "approach",
        "visual": "architecture",
        "logic": "以总体定位为中心，向行业节点、运营平台和协同载体展开分层关系。",
    },
    "sec-0007": {
        "question": "总体架构由哪些业务层次和连接关系构成？",
        "mission": "按源材料说明总体架构的构成、接口和业务承接关系。",
        "judgment": "总体架构围绕资源、能力、服务和协同关系组织业务运行，并保留主体与系统衔接边界。",
        "value": "把总体定位转化为可阅读的业务构成，为行业服务体系和平台运营机制承接结构基础。",
        "role": "approach",
        "visual": "architecture",
        "logic": "从架构入口进入，沿层级与接口关系阅读至业务承接出口。",
    },
    "sec-0008": {
        "question": "方案推进已有怎样的建设基础？",
        "mission": "汇总组织制度、行业资源、既有平台、场景储备、实施推进和运营主体基础。",
        "judgment": "方案具备源材料列明的组织、资源、平台、场景、实施和运营基础。",
        "value": "说明后续服务与运营安排所依托的基础条件，不把基础条件升级为已实现成果。",
        "role": "background",
        "visual": "layered_architecture",
        "logic": "以建设基础为中心，按源材料六类基础形成同层并列的证据结构。",
    },
    "sec-0015": {
        "question": "建设目标和评价原则如何约束运营合作？",
        "mission": "说明真实使用、服务质量、经营效果和安全合规四类评价原则。",
        "judgment": "建设目标以真实使用、服务质量、经营效果和安全合规作为评价关注点。",
        "value": "为后续产品、服务、结算和持续运营页面提供评价边界。",
        "role": "goal",
        "visual": "governance",
        "logic": "由建设目标进入，按四类评价原则展开，并将评价边界交给后续运营机制。",
    },
    "sec-0021": {
        "question": "行业数据服务具体覆盖哪些服务能力？",
        "mission": "按源材料集中呈现数据获取、知识内容、模型智能、分析监测和治理核验服务。",
        "judgment": "数据服务围绕数据、知识、模型、分析和治理核验形成分层服务能力。",
        "value": "建立行业服务体系中的数据服务边界，为场景服务和重点方向作区分。",
        "role": "capability",
        "visual": "capability_service_value",
        "logic": "以数据服务为中心，沿五类服务能力展开，出口连接场景服务。",
    },
    "sec-0027": {
        "question": "场景服务在行业服务体系中承担什么作用？",
        "mission": "说明场景服务面向业务问题的服务对象、服务方式和结果边界。",
        "judgment": "场景服务以业务问题和实际使用为牵引，将数据与专业能力组织到具体服务场景。",
        "value": "承接数据服务能力与真实业务问题之间的转化关系。",
        "role": "capability",
        "visual": "scenario_network",
        "logic": "从业务问题进入，连接平台能力、场景动作和服务结果。",
    },
    "sec-0028": {
        "question": "重点服务方向具体落在哪些电力业务领域？",
        "mission": "保留源材料列明的六类重点服务方向及其业务对象。",
        "judgment": "重点服务方向覆盖生产运行、绿色低碳、市场经营、供应链、科研教育和成果转化等领域。",
        "value": "把场景服务的抽象能力落到源材料明确的行业业务方向。",
        "role": "capability",
        "visual": "scenario_network",
        "logic": "以重点服务方向为中心，按同一业务分类维度展开六类方向。",
    },
    "sec-0035": {
        "question": "服务如何交付并以什么等级运行？",
        "mission": "说明访问与成果交付、部署环境、数据处理、服务周期和服务等级。",
        "judgment": "服务交付需要同时明确访问方式、运行环境、数据处理方式、周期和等级。",
        "value": "把服务能力转化为可执行的交付边界，为订单履行和计量结算提供接口。",
        "role": "capability",
        "visual": "condition_choice_result",
        "logic": "从服务请求进入，沿交付条件与等级规则到达可执行服务输出。",
    },
    "sec-0042": {
        "question": "平台运营的总体业务主线如何贯通？",
        "mission": "说明需求、资源能力、产品服务、订单履行和运营反馈之间的主线。",
        "judgment": "平台以客户需求和资源能力为两端输入，贯通产品形成、订单履行和运营反馈。",
        "value": "建立第三章的主线，作为产品形成、生命周期和计量结算的共同前提。",
        "role": "process",
        "visual": "flow",
        "logic": "从需求与资源两端进入，沿产品形成、订单履行和反馈回流形成业务闭环。",
    },
    "sec-0043": {
        "question": "数据资源、模型、专业能力和技术能力如何形成产品？",
        "mission": "说明核心对象及其从资源能力到数据产品、服务和场景的形成关系。",
        "judgment": "产品形成依托数据资源、模型能力、专业能力和技术能力的组合与运营组织。",
        "value": "解释服务产品从能力供给走向可交付对象的形成机制。",
        "role": "capability",
        "visual": "transform",
        "logic": "以多类能力为输入，沿产品化处理与规则约束到达可交付服务对象。",
    },
    "sec-0048": {
        "question": "产品和场景如何经过阶段门控进入持续运营？",
        "mission": "说明产品与场景的阶段、进入条件、阶段成果、审核责任和继续投入决策。",
        "judgment": "产品和场景按源材料规定的阶段门控推进，并依据评价结果继续开发、运营、整改或退出。",
        "value": "把产品形成机制延展为可管理的生命周期与决策边界。",
        "role": "process",
        "visual": "stage_gate",
        "logic": "沿产品与场景阶段顺序阅读，在每个门控点连接条件、成果和决策。",
    },
    "sec-0049": {
        "question": "订单、授权、交付、计量和结算如何保持一致？",
        "mission": "说明服务运营与计量结算贯通的业务对象、记录和校验关系。",
        "judgment": "平台以订单履行为主线，使客户购买内容、系统执行内容和结算依据保持一致并可追溯。",
        "value": "补足运营闭环中的商务、技术和财务接口，为合作机制提供可执行基础。",
        "role": "capability",
        "visual": "flow",
        "logic": "从客户订单进入，连接授权、服务权益、技术交付、计量、验收和结算。",
    },
    "sec-0051": {
        "question": "合作对象有哪些，合作方式如何区分？",
        "mission": "说明标准接入、联合产品、场景联合运营和战略生态四类合作方式。",
        "judgment": "合作方式按参与深度和共同运营关系形成分层安排。",
        "value": "建立合作机制的对象边界和方式分类，避免与后续商务结算混写。",
        "role": "process",
        "visual": "ecosystem",
        "logic": "以合作对象进入，沿四类合作方式展开，出口连接伙伴协同服务。",
    },
    "sec-0056": {
        "question": "合作伙伴在全周期中如何获得协同服务？",
        "mission": "说明合作伙伴从接入、产品共建到运营协同的全周期服务安排。",
        "judgment": "合作伙伴协同服务贯穿合作前、建设期和运营期，并对应不同责任与支持事项。",
        "value": "把合作方式进一步落到伙伴运营界面，为商务与风险保障承接责任基础。",
        "role": "capability",
        "visual": "lifecycle",
        "logic": "沿合作伙伴生命周期阅读，连接接入、共建、交付、运营和复盘。",
    },
    "sec-0057": {
        "question": "商务报价与收益分配依据哪些口径组织？",
        "mission": "说明服务属性分类、客户报价、费用测算、价格关系、结算基础和动态复盘。",
        "judgment": "商务报价与收益分配需要统一报价构成、成本扣除、结算基础和建设运营期安排。",
        "value": "明确合作运营的商务接口和收益分配边界，不替代后续具体报价测算。",
        "role": "process",
        "visual": "governance",
        "logic": "从服务属性与报价构成进入，沿费用、价格、结算和复盘规则到达分配安排。",
    },
    "sec-0068": {
        "question": "数据、权利和衍生成果如何划分与保护？",
        "mission": "说明合作伙伴资源、客户专属资源、单方加工成果、多方联合成果和平台运行信息边界。",
        "judgment": "数据安全、权利与衍生成果按资源来源、加工关系和平台运行属性分别界定。",
        "value": "为合作接入、交付和持续运营提供权利边界，防止把协同关系写成权利转移。",
        "role": "boundary",
        "visual": "layered_architecture",
        "logic": "按资源与成果类型分层，明确归属、使用边界和平台运行信息接口。",
    },
    "sec-0074": {
        "question": "服务质量问题和运营风险如何协同处置？",
        "mission": "说明服务质量保障、风险识别、责任协同和处置闭环。",
        "judgment": "服务质量保障与风险处置需要以责任协同、过程记录和反馈改进保持运营稳定。",
        "value": "补足合作机制中的风险与质量边界，为试点和持续运营提供约束。",
        "role": "problem",
        "visual": "feedback_loop",
        "logic": "从质量与风险事件进入，连接责任处置、验证和运营反馈。",
    },
    "sec-0076": {
        "question": "合作如何建立正式对接机制？",
        "mission": "说明合作双方从需求沟通、资源对接到事项确认的基础机制。",
        "judgment": "合作推进首先通过正式对接机制明确主体、需求、资源和沟通界面。",
        "value": "把合作机制转化为第五章的第一步执行入口。",
        "role": "process",
        "visual": "flow",
        "logic": "从合作需求进入，沿主体、资源和事项对接到形成初步合作界面。",
    },
    "sec-0077": {
        "question": "合作事项如何梳理并形成可推进对象？",
        "mission": "说明合作事项识别、筛选、成熟度判断和优先安排。",
        "judgment": "合作事项需要在需求、资源、技术、安全、商务和责任条件基础上进行梳理确认。",
        "value": "承接对接机制，形成实施方案和试点运行的事项边界。",
        "role": "process",
        "visual": "condition_choice_result",
        "logic": "由事项清单进入，沿成熟度与条件筛选到形成可实施合作事项。",
    },
    "sec-0078": {
        "question": "确定合作事项后如何完善实施方案？",
        "mission": "说明合作实施方案需要明确的范围、责任、交付、合规和运营安排。",
        "judgment": "实施方案将合作事项转化为可执行的任务、责任、资源和验收安排。",
        "value": "连接事项确认与试点运行，明确正式实施前的准备边界。",
        "role": "process",
        "visual": "stage_gate",
        "logic": "从已确认事项进入，沿方案设计、条件确认和责任分解到试点准入。",
    },
    "sec-0079": {
        "question": "试点运行如何组织并完成验收？",
        "mission": "说明试点准备、真实运行、业务技术验收和问题整改。",
        "judgment": "试点运行通过真实客户和业务条件验证交付、价值、质量、成本和持续服务能力。",
        "value": "把方案安排落实到真实运行和验收门控，为持续运营提供依据。",
        "role": "process",
        "visual": "stage_gate",
        "logic": "沿试点准备、运行、验收和整改顺序阅读，出口连接持续运营。",
    },
    "sec-0080": {
        "question": "试点通过后如何持续运营并复制推广？",
        "mission": "说明持续运营、产品优化、标准化和复制推广的推进关系。",
        "judgment": "持续运营以实际应用、服务质量和经营结果为依据，推动优化、标准化和复制推广。",
        "value": "完成第五章推进建议的结果闭环，承接前述试点和运营评价。",
        "role": "process",
        "visual": "feedback_loop",
        "logic": "从试点结果进入，沿运营评价、优化、标准化和复制推广形成回流。",
    },
    "sec-0081": {
        "question": "结束语对合作推进提出什么收束性说明？",
        "mission": "保留源材料结束语对合作方向、共同建设和推进愿景的收束。",
        "judgment": "结束语将前述服务体系、运营机制和合作推进安排收束到源材料的合作表达。",
        "value": "提供全篇正式收束，不提前新增源材料未写明的行动承诺。",
        "role": "conclusion",
        "visual": "judgment_evidence",
        "logic": "回收前文主线，沿方案对象、合作机制和推进安排落到源材料收束。",
    },
}

ATTACHMENT_META = {
    "sec-0082": ("附件一承接哪些合作伙伴资源与能力登记信息？", "把合作伙伴资源与能力登记作为主文合作机制的追溯和实施支撑。"),
    "sec-0083": ("附件二如何补充产品及场景服务说明？", "把产品与场景服务说明作为服务体系和产品形成机制的明细支撑。"),
    "sec-0084": ("附件三如何评估合作事项成熟度？", "把合作事项成熟度评估作为事项筛选、试点准入和持续推进的依据支撑。"),
    "sec-0085": ("附件四如何补充试点实施与验收要点？", "把试点实施与验收要点作为试点运行页的执行和验收支撑。"),
    "sec-0086": ("附件五如何补充服务计量、账单与结算？", "把计量、账单与结算要点作为运营闭环和商务机制的细化支撑。"),
    "sec-0087": ("附件六如何适配数据分类分级与交付方式？", "把数据分类分级与交付方式适配作为可信交付和权利边界的细化支撑。"),
    "sec-0088": ("附件七如何补充商务报价与收益分配参考模型？", "把商务报价与收益分配参考模型作为商务机制的测算和追溯支撑。"),
}


def load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def source_parent_map(headings: list[dict[str, Any]]) -> dict[str, str | None]:
    return {
        str(item["section_id"]): item.get("parent_section_id") or item.get("parent_id")
        for item in headings
    }


def descendants(section_id: str, parents: dict[str, str | None]) -> set[str]:
    result = {section_id}
    changed = True
    while changed:
        changed = False
        for child, parent in parents.items():
            if child not in result and parent in result:
                result.add(child)
                changed = True
    return result


def role_for_fact(fact: dict[str, Any], index: int, total: int) -> str:
    if index == 0:
        return "claim"
    fact_type = str(fact.get("fact_type") or "").lower()
    if fact_type in {"condition", "constraint", "responsibility", "policy_basis"}:
        return "boundary"
    if fact_type in {"service", "dataset", "scenario", "technology", "platform", "deliverable", "metric", "project"}:
        return "instance"
    if fact_type in {"requirement", "process", "goal", "capability", "relationship", "problem"}:
        return "reason"
    if index == 1 and total > 1:
        return "reason"
    return "trace_only"


def chain_role(value: Any) -> str:
    """Map layer-three source roles into the layer-four chain vocabulary."""
    return {
        "approach": "mechanism",
        "capability": "support",
        "other": "detail",
        "goal": "judgment",
        "context": "premise",
        "process": "implementation",
    }.get(str(value or ""), str(value or "support"))


def nearest_source_heading_ids(fact: dict[str, Any], headings: list[dict[str, Any]]) -> list[str]:
    ordered = sorted(
        (item for item in headings if item.get("section_id") and item.get("line") is not None),
        key=lambda item: int(item.get("line") or 0),
    )
    result: list[str] = []
    for evidence in fact.get("evidence") or []:
        if not isinstance(evidence, dict) or evidence.get("line_start") is None:
            continue
        line = int(evidence.get("line_start") or 0)
        candidates = [item for item in ordered if int(item.get("line") or 0) <= line]
        if candidates:
            section_id = str(candidates[-1]["section_id"])
            if section_id not in result:
                result.append(section_id)
    return result


def _heading_only_chain(chain: list[dict[str, Any]], headings: list[dict[str, Any]]) -> bool:
    heading_titles = {
        str(item.get("title") or "").strip()
        for item in headings
        if str(item.get("title") or "").strip()
    }
    statements = [str(item.get("statement") or "").strip() for item in chain if isinstance(item, dict)]
    return bool(statements) and all(statement in heading_titles for statement in statements)


def _fact_ids_for_role(page_facts: list[dict[str, Any]], *fact_types: str) -> list[str]:
    wanted = {value.lower() for value in fact_types}
    return [
        str(fact["normalized_fact_id"])
        for fact in page_facts
        if str(fact.get("fact_type") or "").lower() in wanted
    ]


def _author_argument_chain(page_facts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build a source-fact chain when the semantic input is heading-only.

    Source headings identify topic ownership; they are not themselves an
    argument.  This fallback keeps the page bounded while making the reading
    order explicit as premise/driver-gap/response, using only page facts.
    """
    if not page_facts:
        return []
    selected: list[tuple[str, str, dict[str, Any]]] = []

    def add(role: str, fact: dict[str, Any]) -> None:
        fact_id = str(fact.get("normalized_fact_id") or "")
        if fact_id and fact_id not in {item[0] for item in selected}:
            selected.append((fact_id, role, fact))

    add("premise", page_facts[0])
    for fact in page_facts[1:]:
        if str(fact.get("fact_type") or "").lower() in {"condition", "policy_basis", "capability", "requirement"}:
            add("driver", fact)
            break
    for fact in page_facts[1:]:
        if str(fact.get("fact_type") or "").lower() in {"problem", "constraint"}:
            add("gap", fact)
            break
    for fact in reversed(page_facts[1:]):
        if str(fact.get("fact_type") or "").lower() in {"goal", "process", "capability", "requirement"}:
            add("response", fact)
            break
    return [
        {
            "role": role,
            "statement": str(fact.get("statement") or ""),
            "evidence": {"normalized_fact_ids": [fact_id]},
        }
        for fact_id, role, fact in selected
        if str(fact.get("statement") or "").strip()
    ]


def _judgment_derivation(page_facts: list[dict[str, Any]], judgment: str) -> dict[str, Any]:
    """Record the source statements used for the page's authored judgment."""
    preferred = [
        fact for fact in page_facts
        if str(fact.get("fact_type") or "").lower()
        in {"problem", "requirement", "goal", "capability", "condition", "policy_basis", "process"}
    ]
    supporting = preferred[:6] or page_facts[:3]
    return {
        "source_refs": [str(fact["normalized_fact_id"]) for fact in supporting],
        "supporting_statements": [str(fact.get("statement") or "") for fact in supporting],
        "derivation": judgment,
        "introduced_relations": [],
        "introduced_modalities": [],
    }


def _evidence_roles(
    page_facts: list[dict[str, Any]], derivation: dict[str, Any]
) -> dict[str, list[str]]:
    """Assign derivation facts to claim before applying type-based defaults."""
    roles: dict[str, list[str]] = {
        "claim": [],
        "reason": [],
        "instance": [],
        "boundary": [],
        "trace_only": [],
    }
    claim_ids = {str(value) for value in derivation.get("source_refs") or []}
    for index, fact in enumerate(page_facts):
        fact_id = str(fact.get("normalized_fact_id") or "")
        role = "claim" if fact_id in claim_ids else role_for_fact(fact, index, len(page_facts))
        if fact_id and fact_id not in roles[role]:
            roles[role].append(fact_id)
    return roles


def _authoring_decisions(
    fact_ids: list[str],
    roles: dict[str, list[str]],
    *,
    attachment: bool,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    excluded_ids = list(fact_ids) if attachment else list(roles["trace_only"])
    excluded = [
        {
            "source_refs": [fact_id],
            "reason": (
                "附件明细保留在附录、完整稿和追溯层，不自动形成主文上屏模块。"
                if attachment
                else "该证据保留在完整稿和追溯层，不直接形成受众模块。"
            ),
        }
        for fact_id in excluded_ids
    ]
    decisions = {
        "deletion_test": (
            "删除本页将丢失该源节对方案主线的独立说明；附件明细本身不改变主文判断。"
            if attachment
            else "删除本页将丢失该源节在全篇业务链条中的独立判断。"
        ),
        "evidence_selection": (
            "上屏只保留附件与主文机制直接相关的摘要，其余登记、清单和操作字段留在追溯层。"
            if attachment
            else "上屏围绕页面核心判断选择直接证据，细项和登记信息留在完整稿或追溯层。"
        ),
        "attachment_disposition": "appendix" if attachment else "not_applicable",
    }
    return excluded, decisions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--outline-dir", type=Path, required=True)
    parser.add_argument("--semantic-dir", type=Path, required=True)
    args = parser.parse_args()

    outline_dir = args.outline_dir.resolve()
    semantic_dir = args.semantic_dir.resolve()
    workpack = load(outline_dir / "outline-workpack.json")
    normalized = load(semantic_dir / "normalized-facts.json")
    argument = load(semantic_dir / "argument-chain.json")
    facts = {
        str(item["normalized_fact_id"]): item
        for item in normalized.get("facts", [])
        if item.get("normalized_fact_id")
    }
    headings = [item for item in workpack.get("source_heading_outline", []) if isinstance(item, dict)]
    heading_by_id = {str(item["section_id"]): item for item in headings}
    parents = source_parent_map(headings)
    nodes = [item for item in argument.get("source_chain", []) if isinstance(item, dict)]
    nodes_by_section: dict[str, list[dict[str, Any]]] = {}
    for node in nodes:
        for section_id in node.get("section_ids") or []:
            nodes_by_section.setdefault(str(section_id), []).append(node)

    root_ids = [str(item["section_id"]) for item in headings if int(item.get("level") or 0) == 1]
    main_root_ids = [item for item in root_ids if item in {"sec-0001", "sec-0020", "sec-0041", "sec-0050", "sec-0075"}]
    level2_ids = [str(item["section_id"]) for item in headings if int(item.get("level") or 0) == 2]
    attachment_ids = [str(item["section_id"]) for item in headings if str(item["section_id"]) in ATTACHMENT_META]
    content_ids = level2_ids + ["sec-0081"] + attachment_ids

    page_counter = 1
    pages: list[dict[str, Any]] = []
    sections: list[dict[str, Any]] = []
    page_for_section: dict[str, str] = {}
    section_for_root = {root: f"S{index:02d}" for index, root in enumerate(main_root_ids, 1)}
    section_for_root.update({"sec-0081": "S06"})
    section_for_root.update({section_id: f"S{index:02d}" for index, section_id in enumerate(attachment_ids, 7)})
    section_page_ids: dict[str, list[str]] = {value: [] for value in sorted(set(section_for_root.values()))}

    def add_page(payload: dict[str, Any]) -> None:
        nonlocal page_counter
        payload["page_id"] = f"P{page_counter:02d}"
        payload["order"] = page_counter
        pages.append(payload)
        page_counter += 1

    add_page({
        "page_type": "template",
        "template_role": "cover",
        "title_intent": "依托电力领域数据基础设施开展行业数据服务与场景服务运营合作方案",
    })
    add_page({"page_type": "template", "template_role": "agenda", "title_intent": "目录"})

    fact_dispositions: list[dict[str, Any]] = []
    for fact_id in [f"NF-{index:04d}" for index in range(1, 42)]:
        fact_dispositions.append({
            "normalized_fact_id": fact_id,
            "disposition": "intentional_omission",
            "rationale": "题名、落款、日期和目录条目属于文档元数据，保留在源材料追溯层，不进入业务内容页。",
        })

    for root_id in main_root_ids:
        section_id = section_for_root[root_id]
        root_title = str(heading_by_id[root_id]["title"])
        divider_id = f"P{page_counter:02d}"
        add_page({
            "page_type": "template",
            "template_role": "section_divider",
            "section_id": section_id,
            "title_intent": root_title,
            "source_heading_ids": [root_id],
            "primary_source_heading_id": root_id,
        })
        section_page_ids[section_id].append(divider_id)
        owned = [item for item in level2_ids if item in descendants(root_id, parents)]
        for primary_id in owned:
            page_id = f"P{page_counter:02d}"
            page_for_section[primary_id] = page_id
            section_page_ids[section_id].append(page_id)
            meta = dict(PAGE_META[primary_id])
            owned_sections = descendants(primary_id, parents)
            page_nodes = [node for node in nodes if any(str(sid) in owned_sections for sid in node.get("section_ids") or [])]
            if primary_id == owned[0]:
                page_nodes.extend(
                    node for node in nodes
                    if root_id in {str(sid) for sid in node.get("section_ids") or []}
                    and node not in page_nodes
                )
            page_nodes.sort(key=lambda item: int(item.get("order") or 0))
            fact_ids: list[str] = []
            for node in page_nodes:
                for fact_id in node.get("normalized_fact_ids") or []:
                    fact_id = str(fact_id)
                    if fact_id not in fact_ids:
                        fact_ids.append(fact_id)
            page_facts = [facts[fact_id] for fact_id in fact_ids if fact_id in facts]
            derivation = _judgment_derivation(page_facts, str(meta["judgment"]))
            roles = _evidence_roles(page_facts, derivation)
            excluded, authoring_decisions = _authoring_decisions(
                fact_ids,
                roles,
                attachment=False,
            )
            for fact_id in fact_ids:
                source_heading_ids = nearest_source_heading_ids(facts[fact_id], headings)
                if source_heading_ids and primary_id not in source_heading_ids:
                    disposition = "trace" if fact_id in roles["trace_only"] else "detail"
                    fact_dispositions.append({
                        "normalized_fact_id": fact_id,
                        "disposition": disposition,
                        "page_ids": [page_id],
                        "rationale": "三级源标题内容作为本节页面的证据细项承接，不另设页面；保留事实与源位置。",
                    })
            chain = [
                {
                    "role": chain_role(node.get("role")),
                    "statement": str(node.get("statement") or ""),
                    "evidence": {"normalized_fact_ids": [str(value) for value in node.get("normalized_fact_ids") or []]},
                }
                for node in page_nodes
                if node.get("normalized_fact_ids")
            ]
            if _heading_only_chain(chain, headings):
                chain = _author_argument_chain(page_facts)
            add_page({
                "page_type": "content",
                "section_id": section_id,
                "title_intent": str(heading_by_id[primary_id]["title"]),
                "source_heading_ids": [primary_id],
                "primary_source_heading_id": primary_id,
                "source_heading_preserved": True,
                "source_heading_preservation_rationale": "按源材料章节、节标题与顺序保留；三级条目作为本节证据细项承接。",
                "audience_question": meta["question"],
                "page_mission": meta["mission"],
                "key_judgment": meta["judgment"],
                "judgment_derivation": derivation,
                "non_substitutable_value": meta["value"],
                "judgment_basis": "source_synthesis",
                "argument_role": meta["role"],
                "must_not_include": ["不改写源材料标题、事实强度、责任、条件和状态。", "不提前吸收后续章节的独立页面使命。"],
                "reserved_for_later": [],
                "excluded_from_onscreen": excluded,
                "authoring_decisions": authoring_decisions,
                "split_risk": "medium" if len(fact_ids) > 12 else "low",
                "split_risk_reason": "本节包含多个三级条目，先以源节为页面主单位并在后续脚本阶段检查单页容量。" if len(fact_ids) > 12 else "源节事实规模可在单页边界内继续作者化。",
                "transition_from_previous": "承接上一页的源材料顺序与前置判断。",
                "transition_to_next": "将本节判断与证据交给下一源节继续展开。",
                "evidence": {"normalized_fact_ids": fact_ids, "relation_ids": [], "argument_node_ids": []},
                "argument_chain": chain,
                "evidence_roles": roles,
                "content_strategy": "以源节核心判断为中心，三级条目按源顺序承担原因、实例、边界和追溯职责。",
                "suggested_visual_logic": meta["logic"],
                "visual_intent_type": meta["visual"],
                "importance": "core" if primary_id in {"sec-0003", "sec-0021", "sec-0042", "sec-0048", "sec-0051", "sec-0079"} else "supporting",
            })

    # Closing and appendix pages follow the source order after the five chapters.
    for primary_id in ["sec-0081"] + attachment_ids:
        section_id = section_for_root[primary_id] if primary_id in section_for_root else "S07"
        page_id = f"P{page_counter:02d}"
        page_for_section[primary_id] = page_id
        section_page_ids.setdefault(section_id, []).append(page_id)
        meta = PAGE_META.get(primary_id)
        if meta is None:
            question, judgment = ATTACHMENT_META[primary_id]
            meta = {
                "question": question,
                "mission": "保留附件内容，作为主文判断的实施、交付或追溯支撑。",
                "judgment": judgment,
                "value": "保留附件对主文方案落地和复核不可替代的支撑信息。",
                "role": "support",
                "visual": "governance",
                "logic": "以附件主题进入，按源材料条目组织支撑信息并回接主文对应机制。",
            }
        page_nodes = [node for node in nodes if primary_id in {str(sid) for sid in node.get("section_ids") or []}]
        fact_ids = []
        for node in page_nodes:
            for fact_id in node.get("normalized_fact_ids") or []:
                if str(fact_id) not in fact_ids:
                    fact_ids.append(str(fact_id))
        page_facts = [facts[fact_id] for fact_id in fact_ids if fact_id in facts]
        derivation = _judgment_derivation(page_facts, str(meta["judgment"]))
        roles = _evidence_roles(page_facts, derivation)
        excluded, authoring_decisions = _authoring_decisions(
            fact_ids,
            roles,
            attachment=primary_id in attachment_ids,
        )
        chain = [
            {"role": chain_role(node.get("role")), "statement": str(node.get("statement") or ""), "evidence": {"normalized_fact_ids": [str(value) for value in node.get("normalized_fact_ids") or []]}}
            for node in page_nodes
            if node.get("normalized_fact_ids")
        ]
        if _heading_only_chain(chain, headings):
            chain = _author_argument_chain(page_facts)
        add_page({
            "page_type": "content",
            "section_id": section_id,
            "title_intent": str(heading_by_id[primary_id]["title"]),
            "source_heading_ids": [primary_id],
            "primary_source_heading_id": primary_id,
            "source_heading_preserved": True,
            "source_heading_preservation_rationale": "附件标题与顺序按源材料保留，作为主文内容的实施和追溯支撑。",
            "audience_question": meta["question"],
            "page_mission": meta["mission"],
            "key_judgment": meta["judgment"],
            "judgment_derivation": derivation,
            "non_substitutable_value": meta["value"],
            "judgment_basis": "source_synthesis",
            "argument_role": meta["role"],
            "must_not_include": ["不把附件明细升级为主文未声明的承诺或事实。", "不替代主文对应章节的总体判断。"],
            "reserved_for_later": [],
            "excluded_from_onscreen": excluded,
            "authoring_decisions": authoring_decisions,
            "split_risk": "medium" if len(fact_ids) > 16 else "low",
            "split_risk_reason": "附件事实较多，后续脚本阶段需按信息密度检查是否拆分。" if len(fact_ids) > 16 else "附件事实规模可在单页边界内继续作者化。",
            "transition_from_previous": "承接源材料前一节并进入本附件支撑内容。",
            "transition_to_next": "将附件支撑信息交给下一源材料条目或全篇收束。",
            "evidence": {"normalized_fact_ids": fact_ids, "relation_ids": [], "argument_node_ids": []},
            "argument_chain": chain,
            "evidence_roles": roles,
            "content_strategy": "以附件主题为页面核心，保留主文所需的实施、交付、计量、权利或商务支撑信息。",
            "suggested_visual_logic": meta["logic"],
            "visual_intent_type": meta["visual"],
            "importance": "supporting",
        })

    closing_id = f"P{page_counter:02d}"
    add_page({"page_type": "template", "template_role": "closing", "title_intent": "谢谢"})

    section_root_by_id = {section_id: root_id for root_id, section_id in section_for_root.items()}
    for order, (section_id, page_ids) in enumerate(section_page_ids.items(), 1):
        root_id = section_root_by_id.get(section_id, "")
        root_title = next((str(item["title"]) for item in headings if str(item["section_id"]) == root_id), "附件")
        if section_id == "S06":
            mission = "收束源材料主文并保留结束语。"
            thesis = "以源材料结束语完成方案表达的正式收束。"
            roles = ["conclusion"]
        elif section_id == "S07":
            mission = "提供主文方案所需的实施、交付、计量、权利和商务追溯支撑。"
            thesis = "附件以明细和参考模型支撑主文判断，不替代主文结构。"
            roles = ["support", "boundary"]
        else:
            mission = f"按源材料顺序说明{root_title}的业务内容与页面边界。"
            thesis = f"{root_title}构成全篇合作方案的一个连续业务段落。"
            roles = sorted({str(page.get("argument_role")) for page in pages if page.get("section_id") == section_id and page.get("page_type") == "content"})
        sections.append({
            "section_id": section_id,
            "order": order,
            "title_intent": root_title,
            "section_mission": mission,
            "section_thesis": thesis,
            "argument_roles": roles,
            "page_ids": page_ids,
        })

    deck_id = "deck-power-data-infrastructure-v16-20260815"
    binding = workpack["binding"]
    deck = {
        "schema_version": "1.1",
        "artifact_type": "ppt_deck_brief",
        "deck_id": deck_id,
        "communication_goal": GOAL,
        "narrative_thesis": "按源材料总体概述、行业服务体系、平台运营机制、合作机制与保障体系、合作推进建议及附件顺序，说明行业数据服务与场景服务运营合作方案。",
        "architecture_mode": "solution",
        "architecture_reason": "源材料是正式合作方案，包含定位、体系、运营、合作保障和推进安排，采用源结构锁定的方案型架构。",
        "structure_principle": "保留源材料章节、节标题和顺序，以二级业务节为页面主单位，三级条目作为证据细项，附件作为实施与追溯支撑。",
        "workpack_binding": {"request_sha256": binding["request_sha256"], "planning_policy_sha256": binding["planning_policy_sha256"]},
        "task_understanding": {
            "audience": "电力行业潜在合作方和需求方",
            "purpose": "说明行业数据服务与场景服务运营合作方案的业务体系、平台机制、合作保障和推进安排",
            "writing_style_mode": "government_official",
            "source_structure_mode": "locked",
            "constraints": ["保持源材料章节标题、内容标题和顺序。", "交流目标中的受众和行动要求不升级为源材料事实。"],
        },
        "deck_strategy": {
            "working_title": "依托电力领域数据基础设施开展行业数据服务与场景服务运营合作方案",
            "core_question": "电力领域数据基础设施如何支撑行业数据服务与场景服务运营合作？",
            "deck_thesis": "源材料通过总体定位、行业服务体系、平台运营机制、合作保障和推进建议，说明数据资源与专业能力如何进入可运营的产品、服务和场景合作链条。",
            "page_budget": {"target": len(pages), "min": len(pages), "max": len(pages)},
            "page_budget_rationale": "以源材料二级业务节和附件为内容主单位，保留五个主章节分隔页及必要模板页。",
            "decision_path": ["总体定位", "服务体系", "运营机制", "合作保障", "推进建议", "附件支撑"],
            "deck_type": "正式方案交流",
            "narrative_mode": "source_logic_focused",
        },
        "planning_policy": workpack["planning_policy"],
        "title_style_mode": "formal_plain",
        "editorial_control_mode": "required",
        "editorial_authoring_mode": "author_driven",
        "editorial_authoring_status": "author_edited",
        "core_message_derivation_mode": "required",
        "storyline_contract_mode": "required",
        "storyline": {
            "route": "source_logic_focused",
            "audience_logic": "先说明方案对象与总体定位，再依源顺序说明服务、运营、合作保障和推进安排。",
            "evidence_selection": "页面直接消费所属源节及其三级条目的归一化事实；元数据留在追溯层，附件保留为实施与复核支撑。",
            "chapter_progression": ["第一章　总体概述", "第二章　行业服务体系", "第三章　平台运营机制", "第四章　合作机制与保障体系", "第五章　合作推进建议"],
            "risks": ["不将交流目标中的受众和行动要求升级为源材料事实。", "不以审计覆盖替代页面使命判断。", "不把附件登记和商务明细提前改写成主文结论。"],
        },
        "argument_contract_mode": "strict",
        "semantic_argument_model_mode": "required",
        "sections": sections,
    }
    plan = {
        "schema_version": "1.1",
        "artifact_type": "ppt_page_plan",
        "deck_id": deck_id,
        "communication_goal": GOAL,
        "narrative_thesis": deck["narrative_thesis"],
        "planning_policy": workpack["planning_policy"],
        "editorial_control_mode": "required",
        "editorial_authoring_mode": "author_driven",
        "editorial_authoring_status": "author_edited",
        "core_message_derivation_mode": "required",
        "storyline_contract_mode": "required",
        "semantic_argument_model_mode": "required",
        "storyline": deck["storyline"],
        "argument_contract_mode": "strict",
        "fact_dispositions": fact_dispositions,
        "pages": pages,
    }
    write(outline_dir / "deck-brief.json", deck)
    write(outline_dir / "page-plan.json", plan)
    print(json.dumps({"deck": str(outline_dir / "deck-brief.json"), "plan": str(outline_dir / "page-plan.json"), "page_count": len(pages), "content_pages": sum(page.get("page_type") == "content" for page in pages), "fact_dispositions": len(fact_dispositions)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
