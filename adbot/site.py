"""광고센터 화면을 실제로 조작하는 부분 (Playwright).

어떤 버튼/입력칸을 누를지는 코드에 박지 않고 selectors.yaml 에서 읽는다.
화면이 바뀌면 코드 말고 selectors.yaml 만 고치면 된다.
"""
from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import Page, sync_playwright

from .config import ROOT
from .rules import Metrics

AUTH_FILE = ROOT / "auth" / "state.json"
MOCK_STATE = ROOT / "data" / "mock_state.json"
MOCK_HOST = "http://mock.adcenter"  # 연습용 가짜 주소 (인터넷에 나가지 않고 mock/ 폴더를 보여줌)


def url(sel: dict, key: str) -> str:
    u = sel["urls"][key]
    if u.startswith(("http://", "https://")):
        return u
    return f"{MOCK_HOST}/{u}"


def _serve_mock(route):
    path = ROOT / route.request.url.removeprefix(MOCK_HOST + "/").split("?")[0]
    route.fulfill(path=str(path)) if path.is_file() else route.fulfill(status=404)


@contextmanager
def open_page(headless: bool = False, mock: bool = False):
    """브라우저를 열고, 저장된 세션(쿠키)을 불러온다. 끝나면 세션을 다시 저장한다."""
    state_file = MOCK_STATE if mock else AUTH_FILE
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(
            storage_state=str(state_file) if state_file.exists() else None, locale="ko-KR")
        if mock:
            context.route(f"{MOCK_HOST}/**", _serve_mock)
        page = context.new_page()
        try:
            yield page
            state_file.parent.mkdir(exist_ok=True)
            context.storage_state(path=str(state_file))
        finally:
            context.close()
            browser.close()


def save_login(sel: dict) -> None:
    """브라우저를 띄우고 사람이 직접 로그인 → 쿠키를 auth/state.json 에 저장.
    (캡차/2차인증 때문에 로그인 자체는 자동화하지 않는다.)"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(locale="ko-KR")
        page = context.new_page()
        page.goto(url(sel, "login"))
        input("브라우저에서 로그인을 끝내고, 광고센터 메인이 보이면 여기서 Enter ▶ ")
        AUTH_FILE.parent.mkdir(exist_ok=True)
        context.storage_state(path=str(AUTH_FILE))
        browser.close()
    print(f"로그인 세션 저장 완료: {AUTH_FILE}")


def _num(text: str) -> int:
    digits = "".join(ch for ch in text if ch.isdigit())
    return int(digits) if digits else 0


def read_ads(page: Page, sel: dict) -> dict[str, dict]:
    """광고 목록 화면에서 현재 세팅값(입찰가, 일예산, ON/OFF)을 읽는다."""
    s = sel["ad_list"]
    page.goto(url(sel, "ad_list"))
    page.wait_for_selector(s["row"])
    result = {}
    for row in page.locator(s["row"]).all():
        ad_id = row.get_attribute(s["id_attr"])
        cur = {"bid": _num(row.locator(s["bid"]).inner_text())}
        # 일예산/상태 칸은 화면에 없을 수 있다 (selectors.yaml 에서 비워두면 건너뜀)
        if s.get("budget"):
            cur["daily_budget"] = _num(row.locator(s["budget"]).inner_text())
        if s.get("status"):
            cur["status"] = row.locator(s["status"]).inner_text().strip()
        result[ad_id] = cur
    return result


def edit_ad(page: Page, sel: dict, ad_id: str, *, bid=None, daily_budget=None, status=None) -> None:
    """광고 1개의 입찰가/예산/상태를 수정하고 저장한다."""
    s = sel["edit"]
    page.goto(url(sel, "ad_list"))
    row = page.locator(f'{sel["ad_list"]["row"]}[{sel["ad_list"]["id_attr"]}="{ad_id}"]')
    row.locator(s["open"]).click()
    if bid is not None:
        page.fill(s["bid_input"], str(bid))
    if daily_budget is not None:
        page.fill(s["budget_input"], str(daily_budget))
    if status is not None:
        page.select_option(s["status_select"], status)
    page.click(s["save"])
    page.wait_for_selector(s["saved_signal"])


def read_report(page: Page, sel: dict) -> list[Metrics]:
    """성과 리포트 표를 읽어서 Metrics 목록으로 만든다."""
    s = sel["report"]
    page.goto(url(sel, "report"))
    page.wait_for_selector(s["row"])
    c = s["columns"]  # 몇 번째 칸(0부터)에 어떤 값이 있는지
    out = []
    for row in page.locator(s["row"]).all():
        cells = [t.strip() for t in row.locator("td").all_inner_texts()]
        out.append(Metrics(
            ad_id=cells[c["ad_id"]],
            bid=_num(cells[c["bid"]]),
            impressions=_num(cells[c["impressions"]]),
            clicks=_num(cells[c["clicks"]]),
            cost=_num(cells[c["cost"]]),
            conversions=_num(cells[c["conversions"]]),
            revenue=_num(cells[c["revenue"]]),
        ))
    return out


def screenshot(page: Page, name: str) -> Path:
    p = ROOT / "data" / f"{name}.png"
    p.parent.mkdir(exist_ok=True)
    page.screenshot(path=str(p), full_page=True)
    return p
