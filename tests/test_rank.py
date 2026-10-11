from adbot.rank import position


def test_position_counts_ads_separately():
    items = [{"code": "1", "ad": True}, {"code": "2", "ad": False}, {"code": "9", "ad": True}, {"code": "3", "ad": True}]
    p = position(items, {"9"})
    assert (p["overall"], p["ad"], p["ad_count"], p["total"]) == (3, 2, 3, 4)
    assert position(items, {"777"})["ad"] is None


def test_position_uses_rank_inside_ad_section():
    items = [{"code": "1", "ad": True, "adRank": 1, "section": "먼저 둘러보세요"},
             {"code": "9", "ad": True, "adRank": 2, "section": "먼저 둘러보세요"},
             {"code": "5", "ad": False}]
    p = position(items, {"9"})
    assert (p["ad"], p["section"]) == (2, "먼저 둘러보세요")
