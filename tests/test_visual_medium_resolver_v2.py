from cyberppt.visual_medium_policy import resolve_visual_medium_policy


def test_same_scene_policy_different_semantics_choose_different_media():
    operation = resolve_visual_medium_policy(
        None,
        scene_policy="auto",
        page_mission="展示现场调度、设备巡检和处置流程",
        business_relationships=(
            {"subject": "调度中心", "relation": "dispatches", "objects": ["现场班组"]},
        ),
        business_object="输电设备",
        actor_type="企业部门与现场人员",
    )
    data = resolve_visual_medium_policy(
        None,
        scene_policy="auto",
        page_mission="展示年度可靠性指标趋势、同比变化和预测结果",
        data_available=True,
        text_count=6,
    )
    assert operation.preferred in {"business_scene", "object_illustration"}
    assert data.preferred == "data_visualization"
    assert operation.preferred != data.preferred


def test_relationship_semantics_prefer_relationship_diagram():
    policy = resolve_visual_medium_policy(
        None,
        scene_policy="forbidden",
        page_mission="表达多主体可信流通、授权、接口和治理关系",
        business_relationships=(
            {"subject": "数据提供方", "relation": "supports", "objects": ["数据使用方"]},
            {"subject": "平台", "relation": "interface", "objects": ["双方"]},
        ),
    )
    assert policy.preferred == "relationship_diagram"
    assert policy.secondary
    assert "business_scene" in policy.forbidden


def test_concrete_object_semantics_prefer_object_illustration_when_scene_forbidden():
    policy = resolve_visual_medium_policy(
        None,
        scene_policy="forbidden",
        page_mission="解释可信连接器设备及其功能组成",
        business_object="可信连接器设备",
    )
    assert policy.preferred == "object_illustration"


def test_mixed_is_selected_only_when_two_specialized_media_are_both_strong_and_close():
    neutral = resolve_visual_medium_policy(None, scene_policy="auto")
    assert neutral.preferred != "mixed"

    hybrid = resolve_visual_medium_policy(
        None,
        scene_policy="auto",
        page_mission="展示业务流程中的指标监测与趋势分析",
        business_relationships=(
            {"subject": "业务流程", "relation": "supports", "objects": ["监测指标"]},
        ),
        data_available=True,
    )
    # Resolver may still choose one specialized medium when the score gap is
    # meaningful; if mixed wins, its rationale must explicitly name the two
    # strong specialized media rather than using mixed as a fallback.
    if hybrid.preferred == "mixed":
        assert "two specialized media are simultaneously strong and close" in hybrid.rationale


def test_rationale_and_scores_are_traceable_to_actual_semantic_signals():
    policy = resolve_visual_medium_policy(
        None,
        scene_policy="auto",
        page_mission="分析电力供需预测趋势和指标变化",
        data_available=True,
    )
    scores = dict(policy.scores)
    assert scores[policy.preferred] >= scores[policy.secondary]
    assert f"preferred={policy.preferred}" in policy.rationale
    assert "page semantics" in policy.rationale
    assert 0.0 <= policy.confidence <= 1.0
