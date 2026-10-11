from adbot.config import load
from adbot.rules import Metrics, decide

R = load("config/rules.yaml")


def m(**kw):
    base = dict(ad_id="X", bid=300, impressions=1000, clicks=100, cost=30000, conversions=5, revenue=90000)
    base.update(kw)
    return Metrics(**base)


def test_few_clicks_hold():
    assert decide(m(clicks=5), R).action == "hold"


def test_no_conversion_big_spend_pause():
    assert decide(m(conversions=0, revenue=0, cost=40000), R).action == "pause"


def test_low_roas_lowers_bid():
    d = decide(m(revenue=30000), R)  # ROAS 100%
    assert d.action == "lower" and d.new_bid == 260  # 300 * 0.85 = 255 → 10원 단위 반올림


def test_high_roas_raises_bid():
    d = decide(m(revenue=300000), R)  # ROAS 1000%
    assert d.action == "raise" and d.new_bid == 330


def test_on_target_hold():
    assert decide(m(revenue=90000), R).action == "hold"  # ROAS 300%


def test_bid_never_exceeds_max():
    d = decide(m(bid=3000, cost=300000, revenue=3000000), R)
    assert d.new_bid == R["bid_max"] and d.action == "hold"
