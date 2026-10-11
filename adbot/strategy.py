"""리포트 성과 → 최대입찰가·일예산 조정안 (순위 로직 없음).

브라우저·엑셀과 분리된 순수 계산이라 단위 테스트로 검증한다.
"""
from dataclasses import dataclass, field


@dataclass
class Perf:
    """키워드·상품·그룹 1개의 판단 기간 합계 성과."""
    level: str                 # keyword | product | group
    key: dict                  # 식별값 (그룹명, 상품번호, 키워드 …)
    bid: int = 0               # 현재 최대입찰가 (keyword/product)
    budget: int = 0            # 현재 일예산 (group)
    impressions: int = 0
    clicks: int = 0
    cost: int = 0              # 광고비용 (VAT 포함)
    conv_product: int = 0      # 광고 상품 기준 전환금액
    conv_seller: int = 0       # 판매자 기준 전환금액
    burn_ratio: float = 0.0    # 일예산 소진율 (group)


@dataclass
class Change:
    level: str
    key: dict
    action: str                # raise | lower | candidate_off | budget_up | hold
    before: int
    after: int
    reason: str
    metrics: dict = field(default_factory=dict)


def roas(p: Perf, s: dict) -> float:
    conv = p.conv_product if s["basis"] == "product" else p.conv_seller
    cost = p.cost / 1.1 if s["cost_vat"] == "excluded" else p.cost
    return conv / cost * 100 if cost else 0.0


def clamp_bid(v: float, s: dict) -> int:
    v = int(round(v / s["bid_unit"]) * s["bid_unit"])
    return max(s["bid_min"], min(s["bid_max"], v))


def clamp_budget(v: float, s: dict) -> int:
    v = int(round(v / 1000) * 1000)
    return max(s["budget_min"], min(s["budget_max"], v))


def _limited(before: int, pct: float, s: dict) -> float:
    pct = max(-s["max_step_pct"], min(s["max_step_pct"], pct))  # 1회 조정 폭 상한
    return before * (1 + pct / 100)


def decide(p: Perf, s: dict) -> Change:
    r = roas(p, s)
    m = {"ROAS": round(r), "클릭": p.clicks, "노출": p.impressions, "광고비": p.cost}
    target = s["target_roas"]

    if p.level == "group":
        if r >= target and p.burn_ratio >= s["budget_burn_ratio"]:
            after = clamp_budget(_limited(p.budget, s["budget_step_pct"], s), s)
            if after > p.budget:
                return Change("group", p.key, "budget_up", p.budget, after,
                              f"ROAS {r:.0f}% ≥ 목표, 예산 소진율 {p.burn_ratio:.0%}", m)
        return Change("group", p.key, "hold", p.budget, p.budget, f"ROAS {r:.0f}%, 소진율 {p.burn_ratio:.0%}", m)

    conv = p.conv_product if s["basis"] == "product" else p.conv_seller
    if conv == 0 and p.cost >= s["zero_conv_cost"]:
        return Change(p.level, p.key, "candidate_off", p.bid, p.bid,
                      f"전환 0인데 광고비 {p.cost:,}원 → 삭제/OFF 검토 (자동 변경 안 함)", m)
    if p.clicks < s["min_clicks"]:
        return Change(p.level, p.key, "hold", p.bid, p.bid, f"표본 부족 (클릭 {p.clicks} < {s['min_clicks']})", m)
    if r < target * s["lower_below_ratio"]:
        after = clamp_bid(_limited(p.bid, -s["step_down_pct"], s), s)
        if after < p.bid:
            return Change(p.level, p.key, "lower", p.bid, after, f"ROAS {r:.0f}% < 목표 {target}%×{s['lower_below_ratio']}", m)
    if r > target * s["raise_above_ratio"] and p.impressions < s["low_impressions"]:
        after = clamp_bid(_limited(p.bid, s["step_up_pct"], s), s)
        if after > p.bid:
            return Change(p.level, p.key, "raise", p.bid, after,
                          f"ROAS {r:.0f}% > 목표×{s['raise_above_ratio']} 이고 노출 {p.impressions:,} 적음", m)
    return Change(p.level, p.key, "hold", p.bid, p.bid, f"ROAS {r:.0f}% 유지", m)


def plan(perfs: list[Perf], s: dict) -> list[Change]:
    return [decide(p, s) for p in perfs]
