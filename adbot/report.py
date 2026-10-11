"""광고센터 리포트 엑셀 → 키워드/상품/그룹별 성과(Perf) 합계.

머리글 이름은 config/report_columns.yaml 에서 찾는다. 날짜 칸이 있으면 최근 N일을 뺀다.
"""
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from .backup import _pick, _raw_tables, _to_int, _with_header
from .strategy import Perf


def read(path: Path, cols: dict) -> pd.DataFrame:
    for raw in _raw_tables(path):
        df = None
        for i in range(min(len(raw), 20)):  # '노출' 이 들어있는 줄을 머리글로
            cells = [str(c).strip() for c in raw.fillna("").iloc[i].tolist()]
            if any("노출" in c for c in cells):
                df = raw.iloc[i + 1:].copy()
                df.columns = cells
                break
        if df is None:
            continue
        headers = list(df.columns)
        out = pd.DataFrame({k: df[h] if (h := _pick(headers, v)) else None for k, v in cols.items()})
        out.attrs["missing"] = [k for k, v in cols.items() if not _pick(headers, v)]
        return out
    raise ValueError(f"리포트 표를 찾지 못함: {path.name}")


def to_perfs(df: pd.DataFrame, level: str, exclude_recent_days: int, today: date | None = None) -> tuple[list[Perf], str]:
    """level 별로 묶어 합계. 반환: (성과 목록, 기간 설명)."""
    note = "날짜 칸 없음 → 리포트 전체 기간 사용 (최근 7일 제외하려면 기간을 그렇게 받아 주세요)"
    if df["date"].notna().any():
        d = pd.to_datetime(df["date"].astype(str).str[:10], errors="coerce")
        cutoff = pd.Timestamp((today or date.today()) - timedelta(days=exclude_recent_days))
        df = df[d < cutoff]
        note = f"{cutoff.date()} 이전 데이터만 사용 (최근 {exclude_recent_days}일 제외)"
    keys = {"keyword": ["group", "product_no", "keyword"], "product": ["group", "product_no"], "group": ["group"]}[level]
    df = df.copy()
    for c in ("impressions", "clicks", "cost", "conv_product", "conv_seller", "bid", "budget"):
        df[c] = df[c].map(lambda v: _to_int(v) or 0)
    perfs = []
    for k, g in df.groupby([df[c].astype(str) for c in keys], sort=False):
        k = k if isinstance(k, tuple) else (k,)
        perfs.append(Perf(level=level, key=dict(zip(keys, k)), bid=int(g["bid"].iloc[-1]), budget=int(g["budget"].iloc[-1]),
                          impressions=int(g["impressions"].sum()), clicks=int(g["clicks"].sum()), cost=int(g["cost"].sum()),
                          conv_product=int(g["conv_product"].sum()), conv_seller=int(g["conv_seller"].sum())))
    return perfs, note
