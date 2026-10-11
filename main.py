"""광고 자동 세팅 → 체크 → 수정 프로그램 (새 G마켓 광고센터, 파워클릭 → 직접 운영형).

  python main.py inspect            # 화면 구조 조사 + 로그인 세션 저장 (처음 1회)
  python main.py pull               # 지금 광고센터의 키워드 입찰가를 config/keywords.csv 로 가져옴
  python main.py setup              # keywords.csv 대로 입찰가 세팅 (기본: 미리보기만)
  python main.py setup --apply      #   → 실제 반영 + 반영됐는지 다시 읽어서 확인
  python main.py check              # keywords.csv 와 실제가 같은지 확인 + 캠페인 성과 읽기
  python main.py adjust             # 성과 규칙(rules.yaml)대로 입찰가 조정안 (기본: 미리보기만)
  python main.py off / on           # 모든 캠페인 광고 끄기 / 켜기 (주말 OFF 용)
  python main.py plan --report 리포트.xlsx [--level keyword|product|group]
                                    # 리포트 성과 → 최대입찰가·일예산 조정안 (검토용 엑셀)
  python main.py backup --folder 폴더  # 옛 광고센터에서 받은 키워드 엑셀들을 하나로 합쳐 백업

--site mock 을 붙이면 실제 광고센터 대신 mock/ 연습 페이지에서 돌아간다.
"""
import argparse
import csv
import shutil
from datetime import datetime
from pathlib import Path

from adbot import gmarket, rules, site
from adbot.config import ROOT, load

FIELDS = ["group", "product_no", "product_name", "keyword", "recommended_bid", "bid"]


def log_change(kind: str, ad_id: str, before, after, reason: str) -> None:
    path = ROOT / "data" / "changes.csv"
    path.parent.mkdir(exist_ok=True)
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "kind", "ad_id", "before", "after", "reason"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), kind, ad_id, before, after, reason])


def kw_path(args) -> Path:
    if args.keywords:
        return ROOT / args.keywords
    return ROOT / ("data/mock_keywords.csv" if args.site == "mock" else "config/keywords.csv")


def read_csv(path: Path) -> list[dict]:
    for enc in ("utf-8-sig", "cp949"):  # 엑셀에서 저장하면 cp949 로 바뀔 수 있음
        try:
            with open(path, newline="", encoding=enc) as f:
                rows = list(csv.DictReader(f))
            break
        except UnicodeDecodeError:
            continue
    for r in rows:
        r["bid"] = int(str(r["bid"]).replace(",", "").strip() or 0)
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as f:  # utf-8-sig: 엑셀에서 한글 안 깨짐
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def key(r: dict) -> tuple:
    return (r["product_no"], r["keyword"])


def bid_problem(bid: int, r: dict) -> str | None:
    if not r["bid_min"] <= bid <= r["bid_max"]:
        return f"입찰가 {bid}원이 허용 범위({r['bid_min']}~{r['bid_max']}원) 밖"
    if bid % r["bid_unit"]:
        return f"입찰가 {bid}원이 {r['bid_unit']}원 단위가 아님"
    return None


def apply_and_verify(page, sel, group: dict, changes: dict, before: dict, kind: str, reasons: dict | None = None) -> bool:
    """입찰가 반영 → 화면을 다시 읽어 정말 바뀌었는지 확인."""
    done = gmarket.set_bids(page, sel, group, changes)
    after = {key(x): x["bid"] for x in gmarket.read_group(page, sel, group)}
    ok = True
    for (p, kw), bid in changes.items():
        if after.get((p, kw)) == bid:
            print(f"  ✓ {kw}: {before.get((p, kw))}→{bid}원 반영 확인")
            log_change(kind, f"{group['name']}/{p}/{kw}", before.get((p, kw)), bid, (reasons or {}).get((p, kw), "keywords.csv 반영"))
        else:
            ok = False
            print(f"  ✗ {kw}: {bid}원으로 바꾸려 했지만 지금 {after.get((p, kw))}원 (입력 {len(done)}건)")
    return ok


def cmd_pull(sel, args):
    path = kw_path(args)
    groups = load(args.groups)["groups"]
    with site.open_page(headless=args.headless, mock=args.site == "mock") as page:
        rows = [r for g in groups for r in gmarket.read_group(page, sel, g)]
    if path.exists():
        bak = ROOT / "data" / f"keywords_before_pull_{datetime.now():%Y%m%d_%H%M%S}.csv"
        bak.parent.mkdir(exist_ok=True)
        shutil.copy(path, bak)
        print(f"(기존 파일은 {bak} 로 백업)")
    write_csv(path, rows)
    for g in groups:
        mine = [r for r in rows if r["group"] == g["name"]]
        print(f"[{g['name']}] 키워드 {len(mine)}개")
        for r in mine:
            print(f"  {r['product_no']} {r['keyword']}: {r['bid']:,}원 (추천 {r['recommended_bid']:,}원)")
    print(f"\n저장: {path}\n→ 엑셀로 열어 bid 칸을 고친 뒤 'setup' 으로 미리보기, 'setup --apply' 로 반영")


def cmd_setup(sel, args):
    path, r = kw_path(args), load(args.rules)
    if not path.exists():
        print(f"{path} 가 없습니다. 먼저 'pull' 을 실행하세요.")
        return
    desired = read_csv(path)
    groups = load(args.groups)["groups"]
    total = 0
    with site.open_page(headless=args.headless, mock=args.site == "mock") as page:
        for g in groups:
            want = {key(x): x["bid"] for x in desired if x["group"] == g["name"]}
            live = {key(x): x["bid"] for x in gmarket.read_group(page, sel, g)}
            changes = {}
            print(f"[{g['name']}]")
            for k, bid in want.items():
                if k not in live:
                    print(f"  [없음] {k[1]} - 광고센터에 이 키워드가 없음 (추가는 아직 미지원)")
                elif (problem := bid_problem(bid, r)):
                    print(f"  [오류] {k[1]}: {problem} → 건너뜀")
                elif bid != live[k]:
                    changes[k] = bid
                    print(f"  [변경] {k[1]}: {live[k]:,} → {bid:,}원")
            print(f"  변경 {len(changes)}건, 같음 {len(want) - len(changes)}건")
            total += len(changes)
            if not (args.apply and changes):
                continue
            if len(changes) > r["max_changes_per_run"]:
                print(f"  중단: 변경 {len(changes)}건 > 1회 한도 {r['max_changes_per_run']}건 (rules.yaml)")
                continue
            apply_and_verify(page, sel, g, changes, live, "setup")
    if total and not args.apply:
        print("\n(미리보기) 실제 반영하려면 --apply 를 붙이세요.")


def cmd_check(sel, args):
    path = kw_path(args)
    desired = read_csv(path) if path.exists() else []
    groups = load(args.groups)["groups"]
    stamp = f"{datetime.now():%Y%m%d_%H%M}"
    with site.open_page(headless=args.headless, mock=args.site == "mock") as page:
        live = [x for g in groups for x in gmarket.read_group(page, sel, g)]
        campaigns = gmarket.read_campaigns(page, sel)
        shot = site.screenshot(page, f"campaigns_{stamp}")

    print("== 입찰가 검증 (keywords.csv vs 실제) ==")
    if not desired:
        print("  keywords.csv 가 없어 건너뜀 (pull 먼저)")
    live_map = {key(x): x["bid"] for x in live}
    bad = 0
    for d in desired:
        cur = live_map.get(key(d))
        if cur != d["bid"]:
            bad += 1
            print(f"  ✗ {d['group']} / {d['keyword']}: 기대 {d['bid']:,}원, 실제 {cur if cur is None else f'{cur:,}원'}")
    if desired:
        print(f"  {len(desired) - bad}/{len(desired)} 일치" + ("" if bad else " ✓"))

    print("\n== 캠페인 성과 (오늘) ==")
    for c in campaigns:
        print(f"  {c.get('캠페인명')} [{c.get('상태')}] 노출 {c.get('노출수')} 클릭 {c.get('클릭수')} "
              f"광고비 {c.get('광고비용')} 전환매출 {c.get('판매자 전환금액')} 수익률 {c.get('광고 수익율')}")
    write_csv(ROOT / "data" / f"live_keywords_{stamp}.csv", live)
    print(f"\n저장: data/live_keywords_{stamp}.csv, 화면: {shot}")


def cmd_adjust(sel, args):
    r = load(args.rules)
    if sel.get("report", {}).get("row", "TODO") == "TODO":
        print("키워드별 성과 화면(리포트)이 아직 조사되지 않아 adjust 는 연습 모드(--site mock)에서만 동작합니다.")
        return
    path = kw_path(args)
    desired = read_csv(path)
    by_key = {f"{x['product_no']}/{x['keyword']}": x for x in desired}
    groups = {g["name"]: g for g in load(args.groups)["groups"]}
    with site.open_page(headless=args.headless, mock=args.site == "mock") as page:
        decisions = rules.plan(site.read_report(page, sel), r)
        plan = {}
        for d in decisions:
            if d.action == "pause":  # 새 센터는 키워드 ON/OFF 가 없어 최저 입찰가로 낮춤
                d.new_bid, d.reason = r["bid_min"], d.reason + " → 최저 입찰가로"
            arrow = f"{d.old_bid}→{d.new_bid}원" if d.new_bid != d.old_bid else ""
            print(f"  [{d.action:5}] {d.ad_id} {arrow} {d.reason}")
            if d.new_bid != d.old_bid and d.ad_id in by_key:
                plan[d.ad_id] = d
        if len(plan) > r["max_changes_per_run"]:
            print(f"\n중단: 변경 {len(plan)}건 > 1회 한도 {r['max_changes_per_run']}건.")
            return
        if not args.apply:
            print("\n(미리보기) 실제 반영하려면 --apply 를 붙이세요.")
            return
        for name, g in groups.items():
            mine = {key(by_key[a]): d.new_bid for a, d in plan.items() if by_key[a]["group"] == name}
            if not mine:
                continue
            before = {key(by_key[a]): d.old_bid for a, d in plan.items() if by_key[a]["group"] == name}
            reasons = {key(by_key[a]): d.reason for a, d in plan.items() if by_key[a]["group"] == name}
            if apply_and_verify(page, sel, g, mine, before, "adjust", reasons):
                for a, d in plan.items():
                    by_key[a]["bid"] = d.new_bid
        write_csv(path, desired)
        print(f"\n{path.name} 도 새 입찰가로 갱신했습니다.")


def cmd_on(sel, args):
    _switch(sel, args, True)


def cmd_off(sel, args):
    _switch(sel, args, False)


def _switch(sel, args, on: bool):
    word = "켜기(ON)" if on else "끄기(OFF)"
    with site.open_page(headless=args.headless, mock=args.site == "mock") as page:
        result = gmarket.set_campaigns(page, sel, on)
    for name, ok in result:
        print(f"  {'✓' if ok else '✗'} {name}: 광고 {word} {'완료' if ok else '실패 - 광고센터에서 직접 확인하세요'}")
    log_change("on" if on else "off", "전체 캠페인", "", word, "수동/예약 실행")


def cmd_plan(sel, args):
    """리포트 엑셀 → 조정안(검토용 엑셀). 광고센터는 건드리지 않는다."""
    import pandas as pd

    from adbot import report, strategy

    s = load("config/strategy.yaml")
    df = report.read(Path(args.report), load("config/report_columns.yaml"))
    missing = [m for m in df.attrs.get("missing", []) if m not in ("date", "budget", "keyword", "product_no", "bid")]
    if missing:
        print(f"⚠ 리포트에서 못 찾은 칸: {missing} → config/report_columns.yaml 확인 필요")
    level = args.level
    perfs, note = report.to_perfs(df, level, s["exclude_recent_days"])
    # 리포트에는 현재 입찰가가 없으므로 keywords.csv(가져오기 결과)에서 채운다
    path = kw_path(args)
    if level == "keyword" and path.exists():
        bids = {(r["product_no"], r["keyword"]): r["bid"] for r in read_csv(path)}
        missing_bid = 0
        for p in perfs:
            if not p.bid:
                p.bid = bids.get((p.key.get("product_no", ""), p.key.get("keyword", "")), 0)
                missing_bid += not p.bid
        if missing_bid:
            print(f"⚠ 현재 입찰가를 모르는 키워드 {missing_bid}개 → 먼저 [1. 가져오기] 를 누르세요 (조정 대상에서 빠짐)")
        perfs = [p for p in perfs if p.bid]
    changes = strategy.plan(perfs, s)
    print(f"[{level}] {len(perfs)}개 · {note} · 기준 {'광고 상품' if s['basis'] == 'product' else '판매자'} ROAS, 목표 {s['target_roas']}%")
    names = {"raise": "올림", "lower": "내림", "candidate_off": "삭제/OFF 후보", "budget_up": "예산 올림", "hold": "유지"}
    rows = []
    for c in changes:
        label = " / ".join(str(v) for v in c.key.values())
        if c.action != "hold":
            print(f"  [{names[c.action]}] {label}: {c.before:,} → {c.after:,}  ({c.reason})")
        rows.append({**c.key, "조치": names[c.action], "변경 전": c.before, "변경 후": c.after, "근거": c.reason, **c.metrics})
    out = ROOT / "data" / f"조정안_{level}_{datetime.now():%Y%m%d_%H%M}.xlsx"
    out.parent.mkdir(exist_ok=True)
    pd.DataFrame(rows).to_excel(out, index=False)
    n = sum(c.action != "hold" for c in changes)
    print(f"\n변경 {n}건 / 유지 {len(changes) - n}건 → 검토용: {out}")
    print("※ 업로드용 엑셀은 광고센터 엑셀등록 템플릿을 받은 뒤 만들 수 있습니다.")
    if args.open and hasattr(__import__("os"), "startfile"):
        __import__("os").startfile(out)  # 프로그램 창에서 실행하면 조정안을 바로 연다


def cmd_backup(sel, args):
    from pathlib import Path

    from adbot import backup

    folder = Path(args.folder).expanduser()
    merged, report = backup.collect(folder)
    print(f"== 파일별 결과 ({folder}) ==")
    for r in report:
        if "error" in r:
            print(f"  ✗ {r['file']}: {r['error']}")
        else:
            missing = [k for k, v in r["mapping"].items() if v is None and k != "group"]
            kws = merged[merged["source_file"] == r["file"]]["keyword"].drop_duplicates()
            print(f"  ✓ {r['file']}: {r['rows']}줄, 키워드 {len(kws)}종  예) {', '.join(kws.head(5))}")
            if missing:
                print(f"      못 찾은 칸: {', '.join(missing)} / 파일의 실제 머리글: {r['headers']}")

    if merged.empty:
        print("\n읽은 키워드가 없습니다.")
        return

    # 같은 내용을 두 번 받은 파일 찾기
    sigs = {}
    for name, g in merged.groupby("source_file"):
        sig = tuple(sorted(map(tuple, g[["ad_id", "product_no", "keyword", "bid"]].astype(str).values)))
        sigs.setdefault(sig, []).append(name)
    for names in sigs.values():
        if len(names) > 1:
            print(f"  ⚠ 내용이 똑같은 파일: {', '.join(names)} → {names[0]} 만 사용")
            merged = merged[~merged["source_file"].isin(names[1:])]

    print("\n== 그룹별 요약 ==")
    for group, g in merged.groupby("group", sort=False):
        status = g["status"].fillna("?").value_counts().to_dict()
        print(f"  {group}: {len(g)}줄, 키워드 {g['keyword'].nunique()}종, 상품 {g['product_no'].nunique()}개 {status}")

    out = ROOT / "data" / "keywords_backup.csv"
    out.parent.mkdir(exist_ok=True)
    merged.to_csv(out, index=False, encoding="utf-8-sig")
    print(f"\n총 {len(merged)}개 → {out} (엑셀로 열 수 있음)")
    if merged["group"].astype(str).str.contains("admanagement").any():
        print("※ 파일 안에 그룹명이 없어서 파일 이름을 그룹명으로 썼습니다. 파일 이름을 그룹명으로 바꿔두세요.")


def cmd_inspect(sel, args):
    from adbot import inspect_page

    with site.open_page(headless=args.headless, mock=args.site == "mock") as page:
        print("브라우저를 여는 중... (따로 뜨는 새 창에서 로그인하세요)")
        try:
            page.goto(site.url(sel, "login"), wait_until="domcontentloaded")
        except Exception as e:  # 첫 화면 로딩이 느려도 조사는 계속할 수 있게
            print(f"(첫 화면 로딩 지연: {e.__class__.__name__}) 브라우저에서 직접 주소를 열어도 됩니다.")
        print("브라우저가 열렸습니다. 로그인이 필요하면 브라우저에서 직접 로그인하세요.")
        inspect_page.run(page)
    print("끝. 로그인 세션도 저장했습니다 (다음부터 로그인 생략).")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["login", "pull", "setup", "check", "adjust", "on", "off", "plan", "backup", "inspect"])
    ap.add_argument("--site", choices=["real", "mock"], default="real")
    ap.add_argument("--apply", action="store_true", help="실제로 반영 (없으면 미리보기)")
    ap.add_argument("--headless", action="store_true", help="브라우저 창 없이 실행")
    ap.add_argument("--groups", default="config/groups.yaml")
    ap.add_argument("--keywords", help="입찰가 파일 (기본: config/keywords.csv)")
    ap.add_argument("--rules", default="config/rules.yaml")
    ap.add_argument("--folder", default="backup", help="backup: 키워드 엑셀 파일들이 있는 폴더")
    ap.add_argument("--report", help="plan: 광고센터에서 받은 리포트 엑셀 파일")
    ap.add_argument("--open", action="store_true", help="plan: 만든 조정안 엑셀을 바로 열기")
    ap.add_argument("--level", default="keyword", choices=["keyword", "product", "group"], help="plan: 판단 단위")
    args = ap.parse_args()

    sel = load("config/selectors.yaml" if args.site == "real" else "mock/selectors.yaml")
    {"login": lambda s, a: site.save_login(s), "pull": cmd_pull, "setup": cmd_setup, "check": cmd_check,
     "adjust": cmd_adjust, "on": cmd_on, "off": cmd_off, "plan": cmd_plan, "backup": cmd_backup, "inspect": cmd_inspect}[args.command](sel, args)


if __name__ == "__main__":
    main()
