from adbot.config import load
from adbot.strategy import Perf, clamp_bid, clamp_budget, decide

S = load("config/strategy.yaml")


def kw(**kw):
    base = dict(level="keyword", key={"keyword": "키트"}, bid=500, impressions=500, clicks=100,
                cost=50000, conv_product=150000, conv_seller=200000)
    base.update(kw)
    return Perf(**base)


def test_bid_clamped_to_ad_center_range():
    assert clamp_bid(10, S) == 90 and clamp_bid(999999, S) == 200000
    assert clamp_budget(1, S) == 10000 and clamp_budget(10 ** 9, S) == 10000000


def test_small_sample_not_adjusted():
    assert decide(kw(clicks=5, conv_product=0, cost=1000), S).action == "hold"


def test_low_roas_lowers_within_step_limit():
    c = decide(kw(conv_product=50000), S)          # ROAS 100%
    assert c.action == "lower" and c.after == 450   # -10%
    assert abs(c.after - c.before) / c.before <= S["max_step_pct"] / 100


def test_high_roas_raises_only_when_few_impressions():
    assert decide(kw(conv_product=500000, impressions=500), S).action == "raise"
    assert decide(kw(conv_product=500000, impressions=50000), S).action == "hold"


def test_zero_conversion_is_only_a_candidate():
    c = decide(kw(conv_product=0, cost=40000), S)
    assert c.action == "candidate_off" and c.after == c.before   # 자동으로 바꾸지 않음


def test_basis_switch_uses_seller_conversion():
    s = {**S, "basis": "seller"}
    assert decide(kw(conv_product=50000, conv_seller=200000), s).action != "lower"   # 판매자 기준 ROAS 400%


def test_vat_excluded_raises_roas():
    s = {**S, "cost_vat": "excluded"}
    # VAT 포함 ROAS 230% → 제외 시 253% : 목표×0.8(240) 기준을 넘어 내림 대상에서 빠짐
    assert decide(kw(conv_product=115000), S).action == "lower"
    assert decide(kw(conv_product=115000), s).action == "hold"


def test_group_budget_up_when_burning_and_profitable():
    g = Perf(level="group", key={"group": "A"}, budget=20000, cost=20000, conv_product=80000, burn_ratio=0.95)
    c = decide(g, S)
    assert c.action == "budget_up" and c.after == 22000
    assert decide(Perf(level="group", key={}, budget=20000, cost=20000, conv_product=10000, burn_ratio=0.95), S).action == "hold"
