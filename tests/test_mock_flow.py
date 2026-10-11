"""연습용 광고센터(mock)로 pull → setup --apply → check 전체 흐름 확인 (브라우저 사용)."""
import csv
import subprocess
import sys

from adbot.config import ROOT


def run(*args, kw):
    r = subprocess.run([sys.executable, "main.py", *args, "--site", "mock", "--headless", "--keywords", str(kw)],
                       cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return r.stdout


def test_pull_setup_check(tmp_path):
    (ROOT / "data" / "mock_state.json").unlink(missing_ok=True)  # 연습 데이터 초기화
    kw = tmp_path / "kw.csv"

    out = run("pull", kw=kw)
    assert "키워드 9개" in out

    rows = list(csv.DictReader(open(kw, encoding="utf-8-sig")))
    rows[0]["bid"] = "450"  # 키트 400 → 450
    with open(kw, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    assert "(미리보기)" in run("setup", kw=kw)
    assert "✓ 키트: 400→450원 반영 확인" in run("setup", "--apply", kw=kw)
    assert "9/9 일치 ✓" in run("check", kw=kw)
