"""G마켓 검색 결과에서 내 상품이 몇 번째인지 센다 (참고용).

검색 결과의 상품 링크(goodscode=숫자)를 화면 순서대로 모으고,
상품 칸 안에 'AD'/'광고' 표시가 있으면 광고 상품으로 본다.
"""
from urllib.parse import quote

from playwright.sync_api import Page

from .site import resolve

CORE = r"""
  const ownText = e => [...e.childNodes].filter(n => n.nodeType === 3).map(n => n.textContent).join('').trim();
  const isAdLabel = e => /^(AD|광고)$/i.test(ownText(e)) || /^(AD|광고)$/i.test((e.getAttribute && e.getAttribute('aria-label')) || '');
  const LINK = 'a[href*="goodscode="], a[href*="goodsCode="], [data-montelena-goodscode]';
  const adSection = card => {           // 위로 올라가며 '광고' 표시가 있는 가장 가까운 구역을 찾는다
    let el = card;
    for (let d = 0; el && d < 12; d++, el = el.parentElement) {
      if (el.querySelectorAll(LINK).length > 60) return null;   // 페이지 전체만큼 넓어지면 중단
      const label = [...el.querySelectorAll('*')].find(isAdLabel);
      if (label) {
        // '광고' 표시가 들어있는 부분(제목 줄)에는 상품이 없어야 진짜 그 구역의 표시.
        // (상품이 있으면 옆 광고 구역의 표시를 잘못 잡은 것 → 일반 상품)
        let part = label; while (part.parentElement !== el) part = part.parentElement;
        return part.querySelector(LINK) && !part.contains(card) ? null : el;
      }
    }
    return null;
  };
  const sectionName = sec => {
    const t = [...sec.querySelectorAll('h1,h2,h3,h4,strong,span,div,p')].map(ownText).find(x => x && x.length >= 3 && x.length <= 20 && !/^(AD|광고|상품등록)$/.test(x));
    return t || '광고 구역';
  };
  const seen = new Set(), items = [];
  for (const a of document.querySelectorAll(LINK)) {
    const m = (a.getAttribute('href') || '').match(/goods[cC]ode=(\d+)/);
    const code = m ? m[1] : a.getAttribute('data-montelena-goodscode');
    if (!code || seen.has(code)) continue;
    const r = a.getBoundingClientRect(); if (r.width === 0 && r.height === 0) continue;
    seen.add(code);
    const card = a.closest('li, [class*="box__item-container"], [class*="box__component"], [class*="item"]') || a.parentElement;
    const sec = adSection(card);
    items.push({code, ad: !!sec, sec, card});
  }
  // 광고 구역별 순서 (구역마다 1위부터)
  const secs = [...new Set(items.filter(i => i.sec).map(i => i.sec))];
  for (const i of items) if (i.sec) {
    const same = items.filter(j => j.sec === i.sec);
    i.adRank = same.indexOf(i) + 1; i.secName = sectionName(i.sec); i.secSize = same.length;
  }
"""

JS = "() => {" + CORE + """
  return items.map(i => ({code: i.code, ad: i.ad, adRank: i.adRank || null, section: i.secName || '',
                          title: ((i.card.innerText || '').trim().split('\\n').find(t => t.length > 6) || '').slice(0, 30)}));
}"""


def search(page: Page, url_tpl: str, keyword: str) -> list[dict]:
    page.goto(resolve(url_tpl.format(keyword=quote(keyword))), wait_until="domcontentloaded")
    for _ in range(6):                   # 상품 목록이 늦게 뜨면 최대 약 12초까지 기다림
        page.wait_for_timeout(2000)
        page.mouse.wheel(0, 2500)        # 아래쪽 상품도 불러오기
        items = page.evaluate(JS)
        if len(items) >= 10:
            break
    return items


def read_current(page: Page) -> list[dict]:
    """지금 브라우저에 떠 있는 화면을 그대로 읽는다 (사람이 봇 확인을 푼 뒤)."""
    page.wait_for_timeout(1500)
    page.mouse.wheel(0, 2500)
    page.wait_for_timeout(1000)
    return page.evaluate(JS)


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
    mine = [i for i in ads if i["code"] in product_nos]
    best = min(mine, key=lambda i: i.get("adRank") or 999) if mine else None
    ad_rank = (best.get("adRank") or ads.index(best) + 1) if best else None
    return {"overall": overall, "ad": ad_rank, "section": best.get("section", "") if best else "",
            "ad_count": len(ads), "total": len(items)}


BOOKMARKLET = "(() => { const MINE = new Set(__MINE__), TARGET = __TARGET__;" + CORE + r"""
  const all = items.findIndex(i => MINE.has(i.code)) + 1;
  const mineAds = items.filter(i => i.ad && MINE.has(i.code)).sort((x, y) => x.adRank - y.adRank);
  const best = mineAds[0];
  items.filter(i => MINE.has(i.code)).forEach(i => { i.card.style.outline = '4px solid #E5484D'; });
  if (best) best.card.scrollIntoView({block: 'center'});
  secs.forEach(sec => { sec.style.outline = '2px dashed #2F6BFF'; });
  const kw = decodeURIComponent((location.search.match(/keyword=([^&]*)/) || [])[1] || '').replace(/\+/g, ' ');
  const ok = best && best.adRank <= TARGET;
  const box = document.getElementById('my-rank-box') || document.body.appendChild(Object.assign(document.createElement('div'), {id: 'my-rank-box'}));
  box.style.cssText = 'position:fixed;top:16px;right:16px;z-index:2147483647;padding:14px 18px;border-radius:10px;font:bold 16px sans-serif;color:#fff;box-shadow:0 4px 16px #0004;white-space:pre;background:' + (ok ? '#13A35B' : '#E5484D');
  box.innerText = (kw ? '[' + kw + '] ' : '') + (best ? best.secName + ' 광고 ' + best.adRank + '위 (구역 ' + best.secSize + '개 중)' : '광고 구역에 없음') +
                  (all ? ' · 전체 ' + all + '번째' : '') + '\n목표 ' + TARGET + '위 안: ' + (ok ? '✓ 통과' : '✗ 순위권 밖') +
                  '  (광고 구역 ' + secs.length + '개 · 광고 ' + items.filter(i => i.ad).length + '개 / 상품 ' + items.length + '개)';
})();
"""


def bookmarklet(product_nos: set[str], target: int) -> str:
    import json
    import re
    code = BOOKMARKLET.replace("__MINE__", json.dumps(sorted(product_nos))).replace("__TARGET__", str(target))
    code = re.sub(r"\s//[^\n]*", "", code)            # 한 줄로 합치기 전에 // 주석 제거
    code = re.sub(r"\s*\n\s*", " ", code).strip()
    return "javascript:" + quote(code, safe="(){}[]=;:,.'!*/<>&|?+-_ ")
