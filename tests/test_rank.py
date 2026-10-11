from adbot.rank import position


def test_position_counts_ads_separately():
    items = [{"code": "1", "ad": True}, {"code": "2", "ad": False}, {"code": "9", "ad": True}, {"code": "3", "ad": True}]
    p = position(items, {"9"})
    assert (p["overall"], p["ad"], p["ad_count"], p["total"]) == (3, 2, 3, 4)
    assert position(items, {"777"})["ad"] is None
