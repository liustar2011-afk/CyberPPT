from __future__ import annotations

import unittest

from cyberppt.page_consumption_contract import argument_chain_visibility_gaps


def _record(
    ref: str,
    *,
    visibility: str,
    topology_role: str,
) -> dict[str, object]:
    return {
        "source_refs": [ref],
        "visibility": visibility,
        "topology_role": topology_role,
    }


class PageConsumptionContractTests(unittest.TestCase):
    def test_offscreen_only_fact_chain_step_is_rejected(self) -> None:
        records = [
            _record(
                "NF-0001",
                visibility="prose_only",
                topology_role="satellite",
            )
        ]
        chain = [{
            "role": "claim",
            "evidence": {"normalized_fact_ids": ["NF-0001"]},
        }]

        gaps = argument_chain_visibility_gaps(records, chain)

        self.assertEqual([(1, ("NF-0001",))], [
            (gap.step_index, gap.source_refs) for gap in gaps
        ])

    def test_one_visible_main_fact_allows_other_step_facts_to_stay_offscreen(self) -> None:
        records = [
            _record(
                "NF-0001",
                visibility="supporting_onscreen",
                topology_role="main_chain",
            ),
            _record(
                "NF-0002",
                visibility="prose_only",
                topology_role="satellite",
            ),
        ]
        chain = [{
            "evidence": {"normalized_fact_ids": ["NF-0001", "NF-0002"]},
        }]

        self.assertEqual((), argument_chain_visibility_gaps(records, chain))

    def test_relationship_or_argument_node_only_step_is_unchanged(self) -> None:
        records = [
            _record(
                "NF-0001",
                visibility="prose_only",
                topology_role="satellite",
            )
        ]
        chain = [
            {"evidence": {"relation_ids": ["REL-0001"]}},
            {"evidence": {"argument_node_ids": ["ARG-0001"]}},
        ]

        self.assertEqual((), argument_chain_visibility_gaps(records, chain))

    def test_projected_source_refs_use_the_same_predicate(self) -> None:
        records = [
            _record(
                "ST0001",
                visibility="prose_only",
                topology_role="satellite",
            )
        ]
        chain = [{"source_refs": ["ST0001"]}]

        self.assertEqual(
            [(1, ("ST0001",))],
            [
                (gap.step_index, gap.source_refs)
                for gap in argument_chain_visibility_gaps(records, chain)
            ],
        )


if __name__ == "__main__":
    unittest.main()
