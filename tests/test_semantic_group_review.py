from cyberppt.semantic_group_review import source_colocation_grouping_mismatch


def test_narrow_institution_parent_rejects_action_plan_application_evidence() -> None:
    mismatch = source_colocation_grouping_mismatch(
        "能源制度",
        [
            (
                "ST0053",
                "《数据要素×》行动计划将绿色低碳列为重点行动领域，"
                "对电力数据采集、流通、应用提出要求",
                ["SU-001"],
            ),
            (
                "ST0054",
                "能源行业数据分类分级指南实行一般、重要、核心三级管理",
                ["SU-001"],
            ),
        ],
    )

    assert mismatch is not None
    assert mismatch.action_refs == ("ST0053",)
    assert mismatch.institution_refs == ("ST0054",)


def test_policy_requirement_umbrella_accepts_mixed_policy_instruments() -> None:
    mismatch = source_colocation_grouping_mismatch(
        "能源政策要求",
        [
            (
                "ST0053",
                "《数据要素×》行动计划将绿色低碳列为重点行动领域，"
                "对电力数据采集、流通、应用提出要求",
                ["SU-001"],
            ),
            (
                "ST0054",
                "能源行业数据分类分级指南实行一般、重要、核心三级管理",
                ["SU-001"],
            ),
        ],
    )

    assert mismatch is None


def test_single_institution_source_does_not_create_false_positive() -> None:
    mismatch = source_colocation_grouping_mismatch(
        "安全制度",
        [("S1", "数据安全管理办法明确重要数据保护和安全责任", ["SU-001"])],
    )

    assert mismatch is None


def test_different_source_locations_do_not_trigger_colocation_rule() -> None:
    mismatch = source_colocation_grouping_mismatch(
        "能源制度",
        [
            ("A", "行动计划面向绿色低碳应用场景提出数据流通要求", ["SU-A"]),
            ("B", "分类分级指南形成能源数据制度安排", ["SU-B"]),
        ],
    )

    assert mismatch is None
