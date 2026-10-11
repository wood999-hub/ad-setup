import pandas as pd

from adbot.backup import collect

HDR = ["파워클릭 광고 ID", "상품번호", "키워드", "운영상태", "희망클릭비용 (VAT미포함)", "클릭수", "총비용 (VAT포함)"]


def test_reads_xlsx_with_title_row_and_html_xls(tmp_path):
    # 제목 줄이 위에 있는 .xlsx
    rows = [["광고관리 다운로드"] + [""] * 6, HDR, ["111", "222", "겨울만들기", "OFF", "1,150", "0", "0원"]]
    pd.DataFrame(rows).to_excel(tmp_path / "팻말.xlsx", header=False, index=False)
    # 확장자는 .xls 지만 내용은 HTML
    html = "<table><tr><th>광고그룹명</th>" + "".join(f"<th>{h}</th>" for h in HDR) + "</tr>" \
           "<tr><td>칼라콘</td><td>1</td><td>2</td><td>색칠공부</td><td>ON</td><td>800</td><td>3</td><td>2,400원</td></tr></table>"
    (tmp_path / "20261011_admanagement.xls").write_text(html, encoding="utf-8")

    merged, report = collect(tmp_path)

    assert all("error" not in r for r in report)
    by_kw = merged.set_index("keyword")
    assert by_kw.loc["겨울만들기", "group"] == "팻말"      # 그룹명 없으면 파일 이름
    assert by_kw.loc["겨울만들기", "bid"] == 1150
    assert by_kw.loc["색칠공부", "group"] == "칼라콘"
    assert by_kw.loc["색칠공부", "cost"] == 2400
