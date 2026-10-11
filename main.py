"""광고 자동 세팅 → 체크 → 수정 프로그램.

  python main.py login              # 1회: 직접 로그인해서 세션 저장
  python main.py setup              # ads.yaml 대로 세팅 (기본: 미리보기만)
  python main.py check              # 성과 수집 + 세팅값이 ads.yaml 과 같은지 확인
  python main.py adjust             # 규칙대로 입찰가 조정안 출력 (기본: 미리보기만)
  python main.py adjust --apply     # 조정안을 실제로 반영

--site mock 을 붙이면 실제 광고센터 대신 mock/ 연습 페이지에서 돌아간다.
"""
import argparse
import csv
from datetime import datetime

from adbot import rules, site
from adbot.config import ROOT, load


def log_change(kind: str, ad_id: str, before, after, reason: str) -> None:
    path = ROOT / "data" / "changes.csv"
    path.parent.mkdir(exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "kind", "ad_id", "before", "after", "reason"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), kind, ad_id, before, after, reason])


def sync_ads_yaml(path: str, ad_id: str, key: str, value) -> None:
    """자동 조정 결과를 ads.yaml 에도 반영해서 '정답 파일'과 실제 세팅을 일치시킨다. (주석 유지)"""
    p = ROOT / path
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    in_block = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("- id:"):
            in_block = f'"{ad_id}"' in line or line.split(":", 1)[1].strip() == ad_id
        elif in_block and line.strip().startswith(f"{key}:"):
            indent = line[: len(line) - len(line.lstrip())]
            comment = line[line.index("#"):].rstrip("\n") if "#" in line else ""
            val = f'"{value}"' if isinstance(value, str) else value
            lines[i] = f"{indent}{key}: {val}" + (f" {comment}" if comment else "") + "\n"
            break
    p.write_text("".join(lines), encoding="utf-8")


def cmd_setup(sel, args):
    wanted = load(args.ads)["ads"]
    with site.open_page(headless=args.headless, mock=args.site == "mock") as page:
        current = site.read_ads(page, sel)
        for ad in wanted:
            cur = current.get(ad["id"])
            if cur is None:
                print(f"[없음] {ad['id']} {ad.get('name', '')} - 광고센터에서 먼저 상품을 등록하세요")
                continue
            diff = {k: ad[k] for k in ("bid", "daily_budget", "status") if k in ad and k in cur and ad[k] != cur[k]}
            if not diff:
                print(f"[같음] {ad['id']} 변경 없음")
                continue
            print(f"[변경] {ad['id']} {cur} → {diff}")
            if args.apply:
                site.edit_ad(page, sel, ad["id"], **diff)
                log_change("setup", ad["id"], cur, diff, "ads.yaml 반영")
        if not args.apply:
            print("\n(미리보기) 실제 반영하려면 --apply 를 붙이세요.")


def cmd_check(sel, args):
    wanted = {a["id"]: a for a in load(args.ads)["ads"]}
    with site.open_page(headless=args.headless, mock=args.site == "mock") as page:
        current = site.read_ads(page, sel)
        metrics = site.read_report(page, sel)
        shot = site.screenshot(page, f"report_{datetime.now():%Y%m%d_%H%M}")

    print("== 세팅값 검증 ==")
    ok = True
    for ad_id, want in wanted.items():
        cur = current.get(ad_id)
        bad = {k: (cur or {}).get(k) for k in ("bid", "daily_budget", "status")
               if k in want and (cur is None or (k in cur and cur[k] != want[k]))}
        if bad:
            ok = False
            print(f"  ✗ {ad_id}: 기대 {({k: want[k] for k in bad})} / 실제 {bad}")
        else:
            print(f"  ✓ {ad_id}")
    print("  → 모두 일치" if ok else "  → 불일치 있음 (setup --apply 로 맞추거나 원인 확인)")

    print("\n== 성과 ==")
    out = ROOT / "data" / f"metrics_{datetime.now():%Y%m%d_%H%M}.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["ad_id", "bid", "impressions", "clicks", "cost", "conversions", "revenue", "roas"])
        for m in metrics:
            w.writerow([m.ad_id, m.bid, m.impressions, m.clicks, m.cost, m.conversions, m.revenue, f"{m.roas:.0f}"])
            print(f"  {m.ad_id}: 클릭 {m.clicks} 광고비 {m.cost:,}원 매출 {m.revenue:,}원 ROAS {m.roas:.0f}%")
    print(f"\n저장: {out}\n화면: {shot}")


def cmd_adjust(sel, args):
    r = load(args.rules)
    with site.open_page(headless=args.headless, mock=args.site == "mock") as page:
        decisions = rules.plan(site.read_report(page, sel), r)
        changes = [d for d in decisions if d.action != "hold"]
        for d in decisions:
            arrow = f"{d.old_bid}→{d.new_bid}원" if d.action in ("raise", "lower") else ""
            print(f"  [{d.action:5}] {d.ad_id} {arrow} {d.reason}")

        if len(changes) > r["max_changes_per_run"]:
            print(f"\n중단: 변경 {len(changes)}건 > 1회 한도 {r['max_changes_per_run']}건. 규칙/데이터를 확인하세요.")
            return
        if not args.apply:
            print("\n(미리보기) 실제 반영하려면 --apply 를 붙이세요.")
            return
        for d in changes:
            if d.action == "pause":
                site.edit_ad(page, sel, d.ad_id, status="OFF")
                sync_ads_yaml(args.ads, d.ad_id, "status", "OFF")
                log_change("adjust", d.ad_id, "ON", "OFF", d.reason)
            else:
                site.edit_ad(page, sel, d.ad_id, bid=d.new_bid)
                sync_ads_yaml(args.ads, d.ad_id, "bid", d.new_bid)
                log_change("adjust", d.ad_id, d.old_bid, d.new_bid, d.reason)
        print(f"\n{len(changes)}건 반영 완료 → data/changes.csv 기록, {args.ads} 갱신")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["login", "setup", "check", "adjust"])
    ap.add_argument("--site", choices=["real", "mock"], default="real")
    ap.add_argument("--apply", action="store_true", help="실제로 반영 (없으면 미리보기)")
    ap.add_argument("--headless", action="store_true", help="브라우저 창 없이 실행")
    ap.add_argument("--ads", default="config/ads.yaml")
    ap.add_argument("--rules", default="config/rules.yaml")
    args = ap.parse_args()

    sel = load("config/selectors.yaml" if args.site == "real" else "mock/selectors.yaml")
    {"login": lambda s, a: site.save_login(s), "setup": cmd_setup,
     "check": cmd_check, "adjust": cmd_adjust}[args.command](sel, args)


if __name__ == "__main__":
    main()
