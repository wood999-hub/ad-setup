"""가짜 리포트(일자별)로 plan 전체 흐름: 최근 7일 제외 + 조정안 엑셀 생성."""
from datetime import date

import pandas as pd

from adbot.config import load
from adbot.report import read, to_perfs
from adbot.strategy import plan

COLS = load("config/report_columns.yaml")
S = load("config/strategy.yaml")


def test_recent_days_excluded_and_plan(tmp_path):
    rows = [["리포트 (테스트)"] + [""] * 8,
            ["날짜", "광고 그룹명", "상품 번호", "키워드", "키워드 입찰가", "노출 수", "클릭 수", "광고 비용", "광고 상품 전환 금액"]]
    for day in range(1, 11):  # 10/1~10/10, 매일 클릭 10, 광고비 5,000
        rows.append([f"2026-10-{day:02d}", "G", "111", "키트", "500", "100", "10", "5,000",
                     "50,000" if day >= 5 else "0"])  # 최근 날짜에만 전환
    p = tmp_path / "report.xlsx"
    pd.DataFrame(rows).to_excel(p, header=False, index=False)

    df = read(p, COLS)
    perfs, note = to_perfs(df, "keyword", S["exclude_recent_days"], today=date(2026, 10, 11))
    assert "최근 7일 제외" in note
    assert perfs[0].clicks == 30 and perfs[0].conv_product == 0   # 10/1~10/3 만 사용
    assert plan(perfs, S)[0].action == "lower"   # 앞 3일만 보면 ROAS 0% → 내림 (기간 선택이 결론을 바꾼다)

    perfs, _ = to_perfs(df, "keyword", 0, today=date(2026, 10, 11))
    assert perfs[0].clicks == 100 and plan(perfs, S)[0].action == "raise"   # 전체 기간: ROAS 600%, 노출 1,000 미만
