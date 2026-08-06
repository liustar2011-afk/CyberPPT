from __future__ import annotations

from dataclasses import dataclass

# 电力/数据基础设施类材料中常见的易混淆概念组：同一份材料里出现同组多个术语，
# 且 Source Truth Map 未对其做区分或标记待核时，语义理解很容易把它们当成同一件事。
_CONFUSION_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("数据资源/数据产品/数据服务", ("数据资源", "数据产品", "数据服务")),
    ("建设主体/运营主体/投资主体", ("建设主体", "运营主体", "投资主体")),
    ("可信互联节点/平台能力", ("可信互联节点", "平台能力", "全域能力")),
    ("原始数据/脱敏数据/加工数据", ("原始数据", "脱敏数据", "加工数据", "衍生数据")),
    ("数据要素/数据资产", ("数据要素", "数据资产")),
    ("现状/规划/目标", ("现状", "规划目标", "远期目标")),
)


@dataclass(frozen=True)
class DomainConfusionHit:
    group: str
    terms: tuple[str, ...]


def detect_domain_confusions(source_text: str) -> list[DomainConfusionHit]:
    hits: list[DomainConfusionHit] = []
    for group, terms in _CONFUSION_GROUPS:
        present = tuple(term for term in terms if term in source_text)
        if len(present) >= 2:
            hits.append(DomainConfusionHit(group=group, terms=present))
    return hits
