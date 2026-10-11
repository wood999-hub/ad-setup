"""G마켓 검색 결과에서 내 상품이 몇 번째인지 센다 (참고용).

검색 결과의 상품 링크(goodscode=숫자)를 화면 순서대로 모으고,
상품 칸 안에 'AD'/'광고' 표시가 있으면 광고 상품으로 본다.
"""
from urllib.parse import quote

from playwright.sync_api import Page

from .site import resolve

JS = r"""
() => {
  const seen = new Set(), items = [];
  const nodes = document.querySelectorAll('a[href*="goodscode="], a[href*="goodsCode="], [data-montelena-goodscode]');
  for (const a of nodes) {
    const m = (a.getAttribute('href') || '').match(/goods[cC]ode=(\d+)/) ;
    const code = m ? m[1] : a.getAttribute('data-montelena-goodscode');
    if (!code || seen.has(code)) continue;
    const r = a.getBoundingClientRect();
    if (r.width === 0 && r.height === 0) continue;          // 숨은 링크 제외
    seen.add(code);
    const card = a.closest('li, [class*="box__item-container"], [class*="box__component"], [class*="item"]') || a.parentElement;
    const isAd = [...card.querySelectorAll('*')].some(e =>
      e.children.length === 0 && /^(AD|광고)$/i.test((e.innerText || e.getAttribute('aria-label') || '').trim()))
      || /(^|[_-])ad([_-]|$)/i.test(card.className || '');
    const title = (card.innerText || '').trim().split('\n').find(t => t.length > 6) || '';
    items.push({code, ad: isAd, title: title.slice(0, 30)});
  }
  return items;
}
"""


def search(page: Page, url_tpl: str, keyword: str) -> list[dict]:
    page.goto(resolve(url_tpl.format(keyword=quote(keyword))), wait_until="domcontentloaded")
    page.wait_for_timeout(2500)          # 상품 목록이 늦게 뜨는 경우
    page.mouse.wheel(0, 3000)            # 아래쪽 상품도 불러오기
    page.wait_for_timeout(1000)
    return page.evaluate(JS)


def position(items: list[dict], product_nos: set[str]) -> dict:
    """전체 순서 / 광고 상품 중 순서 (1부터, 없으면 None)."""
    ads = [i for i in items if i["ad"]]
    overall = next((n for n, i in enumerate(items, 1) if i["code"] in product_nos), None)
    ad_rank = next((n for n, i in enumerate(ads, 1) if i["code"] in product_nos), None)
    return {"overall": overall, "ad": ad_rank, "ad_count": len(ads), "total": len(items)}
