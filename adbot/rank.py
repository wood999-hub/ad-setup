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
    for _ in range(6):                   # 상품 목록이 늦게 뜨면 최대 약 12초까지 기다림
        page.wait_for_timeout(2000)
        page.mouse.wheel(0, 2500)        # 아래쪽 상품도 불러오기
        items = page.evaluate(JS)
        if len(items) >= 10:
            break
    return items


DIAG = r"""
() => {
  const links = [...document.querySelectorAll('a[href]')].map(a => a.href);
  const itemish = links.filter(h => /item|goods|product|\d{9,}/i.test(h));
  return {title: document.title, url: location.href, links: links.length,
          sample: [...new Set(itemish)].slice(0, 8),
          text: (document.body.innerText || '').trim().replace(/\s+/g, ' ').slice(0, 200)};
}
"""


def diagnose(page: Page) -> dict:
    """상품을 못 찾았을 때 화면이 어떤 상태인지 (차단 화면인지, 링크 모양이 다른지)."""
    return page.evaluate(DIAG)


def position(items: list[dict], product_nos: set[str]) -> dict:
    """전체 순서 / 광고 상품 중 순서 (1부터, 없으면 None)."""
    ads = [i for i in items if i["ad"]]
    overall = next((n for n, i in enumerate(items, 1) if i["code"] in product_nos), None)
    ad_rank = next((n for n, i in enumerate(ads, 1) if i["code"] in product_nos), None)
    return {"overall": overall, "ad": ad_rank, "ad_count": len(ads), "total": len(items)}
