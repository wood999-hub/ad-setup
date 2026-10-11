"""새 G마켓 광고센터 조작: 그룹 → 상품 → 키워드 입찰가 읽기/바꾸기, 캠페인 성과 읽기.

화면 요소 위치는 전부 selectors.yaml 의 group_edit / campaign_list 에서 읽는다.
"""
from playwright.sync_api import Page

from .site import resolve


def _num(text: str) -> int:
    digits = "".join(ch for ch in str(text) if ch.isdigit())
    return int(digits) if digits else 0


def _cells(row) -> list[str]:
    return row.evaluate("r => [...r.children].map(c => c.innerText.trim())")


class LoginExpired(RuntimeError):
    pass


def _open_group(page: Page, sel: dict, group: dict) -> None:
    page.goto(resolve(sel["urls"]["group_edit"].format(**group)))
    try:
        page.wait_for_selector(sel["group_edit"]["product_row"], timeout=20000)
    except Exception:
        if "login" in page.url:
            raise LoginExpired("로그인 세션이 없거나 만료됐습니다. 'python main.py inspect' 로 다시 로그인한 뒤 q 로 끝내세요.")
        raise RuntimeError(f"[{group['name']}] 그룹 화면을 열지 못했습니다. groups.yaml 의 번호를 확인하세요. (주소: {page.url})")


def _open_keywords(page: Page, s: dict, product_row) -> None:
    product_row.locator(s["open_keywords"]).first.click()
    page.wait_for_selector(s["kw_row"])


def _close_layer(page: Page, s: dict, button: str) -> None:
    page.click(s[button])
    # '팝업을 종료하겠습니까?' 같은 확인창이 뜨면 '확인'
    confirm = page.get_by_role("button", name="확인", exact=True)
    try:
        confirm.last.wait_for(state="visible", timeout=2000)
        confirm.last.click()
    except Exception:
        pass
    page.wait_for_selector(s["layer"], state="hidden")


def read_group(page: Page, sel: dict, group: dict) -> list[dict]:
    """그룹 안 모든 상품의 키워드와 입찰가를 읽는다. (아무것도 저장하지 않음)"""
    s = sel["group_edit"]
    _open_group(page, sel, group)
    out = []
    rows = page.locator(s["product_row"])
    for i in range(rows.count()):
        row = rows.nth(i)
        cells = _cells(row)
        product_no, product_name = cells[s["product_no_col"]], cells[s["product_name_col"]]
        _open_keywords(page, s, row)
        kws = page.locator(s["kw_row"])
        for j in range(kws.count()):
            kw = kws.nth(j)
            kc = _cells(kw)
            out.append({
                "group": group["name"],
                "product_no": product_no,
                "product_name": product_name,
                "keyword": kc[s["kw_name_col"]],
                "recommended_bid": _num(kc[s["kw_recommend_col"]]),
                "bid": _num(kw.locator(s["kw_bid_input"]).first.input_value()),
            })
        _close_layer(page, s, "layer_cancel")
    return out


def set_bids(page: Page, sel: dict, group: dict, changes: dict[tuple[str, str], int]) -> list[tuple]:
    """changes = {(상품번호, 키워드): 새 입찰가}. 팝업에서 입력 → 적용하기 → 수정하기.
    실제로 입력한 (상품번호, 키워드, 새 입찰가) 목록을 돌려준다."""
    s = sel["group_edit"]
    _open_group(page, sel, group)
    done = []
    rows = page.locator(s["product_row"])
    for i in range(rows.count()):
        row = rows.nth(i)
        product_no = _cells(row)[s["product_no_col"]]
        wanted = {kw: bid for (p, kw), bid in changes.items() if p == product_no}
        if not wanted:
            continue
        _open_keywords(page, s, row)
        kws = page.locator(s["kw_row"])
        for j in range(kws.count()):
            kw = kws.nth(j)
            name = _cells(kw)[s["kw_name_col"]]
            if name in wanted:
                kw.locator(s["kw_bid_input"]).first.fill(str(wanted[name]))
                done.append((product_no, name, wanted[name]))
        _close_layer(page, s, "layer_apply")
    if done:
        page.click(s["save"])
        confirm = page.locator(s["save_confirm"])
        try:  # 확인 팝업이 뜨는 경우에만 누른다
            confirm.first.wait_for(state="visible", timeout=3000)
            confirm.first.click()
        except Exception:
            pass
        page.wait_for_load_state("networkidle")
    return done


def read_campaigns(page: Page, sel: dict) -> list[dict]:
    """광고 관리 화면의 캠페인 성과(노출수·클릭수·광고비용 등)를 읽는다."""
    s = sel["campaign_list"]
    page.goto(resolve(sel["urls"]["campaigns"]))
    page.wait_for_selector(s["row"])
    out = []
    rows = page.locator(s["row"])
    for i in range(rows.count()):
        row = rows.nth(i)
        cells = dict(zip(s["columns"], _cells(row)))
        cells["id"] = row.get_attribute(s["id_attr"])
        out.append(cells)
    return out


def _confirm_if_asked(page: Page) -> None:
    confirm = page.get_by_role("button", name="확인", exact=True)
    try:
        confirm.last.wait_for(state="visible", timeout=2000)
        confirm.last.click()
    except Exception:
        pass


def set_campaigns(page: Page, sel: dict, on: bool) -> list[tuple[str, bool]]:
    """모든 캠페인을 켜거나(on=True) 끈다. 바꾼 뒤 다시 읽어 (캠페인명, 성공여부) 목록을 돌려준다."""
    s = sel["campaign_list"]
    page.goto(resolve(sel["urls"]["campaigns"]))
    page.wait_for_selector(s["row"])
    rows = page.locator(s["row"])
    names = []
    for i in range(rows.count()):
        row = rows.nth(i)
        name = dict(zip(s["columns"], _cells(row))).get("캠페인명", f"캠페인{i + 1}")
        names.append(name)
        toggle = row.locator(s["toggle"]).first
        if toggle.is_checked() != on:
            toggle.click(force=True)  # 스위치 모양으로 꾸며진 체크박스라 force
            _confirm_if_asked(page)
            page.wait_for_load_state("networkidle")
    # 다시 읽어서 확인
    page.reload()
    page.wait_for_selector(s["row"])
    rows = page.locator(s["row"])
    return [(names[i], rows.nth(i).locator(s["toggle"]).first.is_checked() == on) for i in range(rows.count())]
