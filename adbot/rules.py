"""성과 데이터를 보고 '무엇을 바꿀지' 결정하는 규칙 엔진.

브라우저와 완전히 분리되어 있어서, 실제 광고센터 없이도 테스트할 수 있다.
"""
from dataclasses import dataclass


@dataclass
class Metrics:
    ad_id: str
    bid: int
    impressions: int
    clicks: int
    cost: int
    conversions: int
    revenue: int

    @property
    def roas(self) -> float:
        """광고비 대비 매출(%) = 매출 / 광고비 * 100"""
        return self.revenue / self.cost * 100 if self.cost else 0.0


@dataclass
class Decision:
    ad_id: str
    action: str  # hold | raise | lower | pause
    old_bid: int
    new_bid: int
    reason: str


def _round_bid(value: float, unit: int) -> int:
    return int(round(value / unit) * unit)


def decide(m: Metrics, r: dict) -> Decision:
    target = r["target_roas"]
    clamp = lambda b: max(r["bid_min"], min(r["bid_max"], b))

    if m.clicks < r["min_clicks"]:
        return Decision(m.ad_id, "hold", m.bid, m.bid, f"데이터 부족 (클릭 {m.clicks} < {r['min_clicks']})")

    if m.conversions == 0 and m.cost >= r["pause_cost_without_conversion"]:
        return Decision(m.ad_id, "pause", m.bid, m.bid, f"전환 0인데 광고비 {m.cost:,}원 소진")

    if m.roas < target * r["lower_below_ratio"]:
        new = clamp(_round_bid(m.bid * (1 - r["step_down_pct"] / 100), r["bid_unit"]))
        return Decision(m.ad_id, "lower" if new < m.bid else "hold", m.bid, new,
                        f"ROAS {m.roas:.0f}% < 목표 {target}%")

    if m.roas > target * r["raise_above_ratio"]:
        new = clamp(_round_bid(m.bid * (1 + r["step_up_pct"] / 100), r["bid_unit"]))
        return Decision(m.ad_id, "raise" if new > m.bid else "hold", m.bid, new,
                        f"ROAS {m.roas:.0f}% > 목표 {target}%")

    return Decision(m.ad_id, "hold", m.bid, m.bid, f"ROAS {m.roas:.0f}% 목표 범위 내")


def plan(metrics: list[Metrics], r: dict) -> list[Decision]:
    return [decide(m, r) for m in metrics]
