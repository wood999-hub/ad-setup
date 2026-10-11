"""화면 구조 조사 도구.

사람이 브라우저에서 원하는 화면(광고 관리, 키워드 목록 등)을 열고 Enter 를 누르면
그 화면의 표/버튼/입력칸과 각각을 가리키는 selector 를 글자로 뽑아준다.
이 결과를 보고 config/selectors.yaml 을 채운다.
"""
from datetime import datetime

from playwright.sync_api import Page

from .config import ROOT

# 브라우저 안에서 실행되는 조사 스크립트
JS = r"""
() => {
  const vis = el => { const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
  const txt = el => (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.title || '').trim().replace(/\s+/g, ' ').slice(0, 40);
  const sel = el => {
    if (el.id && !/^\d/.test(el.id)) return '#' + CSS.escape(el.id);
    for (const a of ['data-testid', 'data-test', 'name']) {
      const v = el.getAttribute(a); if (v) return `${el.tagName.toLowerCase()}[${a}="${v}"]`;
    }
    const parts = [];
    let cur = el;
    for (let depth = 0; cur && cur.nodeType === 1 && depth < 4; depth++, cur = cur.parentElement) {
      let s = cur.tagName.toLowerCase();
      if (cur.id && !/^\d/.test(cur.id)) { parts.unshift('#' + CSS.escape(cur.id)); break; }
      const cls = [...cur.classList].filter(c => !/^(css-|sc-|jsx-)|\d{3,}/.test(c)).slice(0, 2);
      if (cls.length) s += '.' + cls.map(c => CSS.escape(c)).join('.');
      parts.unshift(s);
    }
    return parts.join(' > ');
  };

  const out = { url: location.href, title: document.title, tables: [], grids: [], buttons: [], inputs: [], frames: document.querySelectorAll('iframe').length };

  for (const t of document.querySelectorAll('table')) {
    if (!vis(t)) continue;
    const headers = [...t.querySelectorAll('thead th, thead td')].map(txt);
    const rows = t.querySelectorAll('tbody tr');
    const first = rows[0];
    out.tables.push({
      selector: sel(t), headers, rows: rows.length,
      first_row: first ? [...first.children].map(txt) : [],
      first_row_attrs: first ? [...first.attributes].map(a => `${a.name}=${a.value}`.slice(0, 60)) : [],
    });
  }
  for (const g of document.querySelectorAll('[role=grid], [role=table], .ag-root, .tui-grid-container')) {
    if (!vis(g)) continue;
    const headers = [...g.querySelectorAll('[role=columnheader], .ag-header-cell-text')].map(txt);
    const rows = g.querySelectorAll('[role=row]');
    out.grids.push({ selector: sel(g), headers, rows: rows.length,
      first_row: rows[1] ? [...rows[1].querySelectorAll('[role=gridcell], [role=cell], .ag-cell')].map(txt) : [] });
  }
  for (const b of document.querySelectorAll('button, a[role=button], [role=button], input[type=button], input[type=submit]')) {
    if (!vis(b)) continue;
    const t = txt(b); if (!t) continue;
    out.buttons.push(`${t}  →  ${sel(b)}`);
  }
  for (const i of document.querySelectorAll('input:not([type=hidden]):not([type=button]):not([type=submit]), select, textarea')) {
    if (!vis(i)) continue;
    out.inputs.push(`${i.tagName.toLowerCase()}[${i.type || ''}] ${txt(i) || i.value || ''}  →  ${sel(i)}`);
  }
  out.buttons = [...new Set(out.buttons)].slice(0, 80);
  out.inputs = out.inputs.slice(0, 60);
  return out;
}
"""


def describe(page: Page) -> str:
    info = page.evaluate(JS)
    lines = [f"### 주소: {info['url']}", f"제목: {info['title']}  (iframe {info['frames']}개)"]
    for kind in ("tables", "grids"):
        for i, t in enumerate(info[kind], 1):
            lines.append(f"\n[{'표' if kind == 'tables' else '그리드'} {i}] {t['selector']}  ({t['rows']}줄)")
            lines.append(f"  머리글: {t['headers']}")
            lines.append(f"  첫 줄: {t['first_row']}")
            if t.get("first_row_attrs"):
                lines.append(f"  첫 줄 속성: {t['first_row_attrs']}")
    lines.append("\n[버튼]")
    lines += [f"  {b}" for b in info["buttons"]]
    lines.append("\n[입력칸]")
    lines += [f"  {i}" for i in info["inputs"]]
    return "\n".join(lines)


def run(page: Page) -> None:
    out_dir = ROOT / "data" / "inspect"
    out_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    while True:
        cmd = input("\n조사할 화면을 브라우저에 띄우고 Enter (끝내려면 q + Enter) ▶ ").strip().lower()
        if cmd == "q":
            break
        n += 1
        page = page.context.pages[-1]  # 새 탭에서 열었으면 가장 최근 탭
        text = describe(page)
        stamp = f"{datetime.now():%H%M%S}_{n}"
        (out_dir / f"page_{stamp}.txt").write_text(text, encoding="utf-8")
        (out_dir / f"page_{stamp}.html").write_text(page.content(), encoding="utf-8")
        print(text)
        print(f"\n(저장: {out_dir / f'page_{stamp}.txt'}) ↑ 위 내용을 복사해서 Claude 에게 보내주세요.")
