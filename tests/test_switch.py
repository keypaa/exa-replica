from exa_replica.bootstrap.switch import apply_switch, plan_switch


def test_switch_peak_or_outage():
    # 2x V_gpu fits -> load new before freeing old (2x peak)
    assert plan_switch("A", "B", v_gpu_peak_gb=10, budget_gb=24).mode == "2x_peak"
    # 2x V_gpu doesn't fit -> short dense outage (BM25 still served)
    assert plan_switch("A", "B", v_gpu_peak_gb=15, budget_gb=24).mode == "short_outage"


def test_atomic():
    # atomic switch: the new build becomes active, no partial state (D68)
    assert apply_switch("A", "B") == "B"
    assert apply_switch("B", "C") == "C"