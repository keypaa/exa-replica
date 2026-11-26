from exa_replica.application.plans import STAGE_ORDER, TierPlan, plan_for


def test_tierplan_consistency():
    for tier in ("lite", "auto"):
        plan = plan_for(tier)
        assert isinstance(plan, TierPlan)
        # every stage is known
        assert set(plan.stages) <= set(STAGE_ORDER)
        # stages appear in canonical D66 order
        indices = [STAGE_ORDER.index(s) for s in plan.stages]
        assert indices == sorted(indices)
        # no duplicate stages
        assert len(plan.stages) == len(set(plan.stages))


def test_unknown_tier_rejected():
    try:
        plan_for("deep")
    except ValueError:
        return
    raise AssertionError("deep is out of v1 and must be rejected (D15/D18)")