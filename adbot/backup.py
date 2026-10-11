"""광고센터에서 받은 키워드 엑셀 파일들을 읽어서 하나의 백업 목록으로 합친다.

- .xls(97-2003) / .xlsx / .csv 지원
- 한국 사이트 엑셀은 실제로는 HTML 인 경우가 많아서, 엑셀로 안 열리면 HTML 표로 다시 읽는다.
- 위쪽에 제목 줄이 있어도 '키워드' 가 들어있는 줄을 찾아 머리글로 쓴다.
"""
from pathlib import Path

import pandas as pd

# 표준 이름: 엑셀 머리글에서 찾을 단어들 (앞에 있을수록 우선)
COLUMNS = {
    "group": ["광고그룹명", "그룹명", "광고그룹"],
    "ad_id": ["파워클릭 광고 ID", "파워클릭 광고ID", "광고 ID", "광고ID", "ID"],
    "product_no": ["상품번호"],
    "product_name": ["상품명"],
    "keyword": ["키워드"],
    "status": ["운영상태", "상태"],
    "bid": ["희망클릭비용", "입찰가", "클릭비용"],
    "auto_bid": ["자동입찰 설정여부"],
    "auto_bid_rank": ["자동입찰 희망순위"],
    "auto_bid_max": ["자동입찰 최대비용"],
    "quality": ["품질평가지수"],
    "impressions": ["노출수"],
    "clicks": ["클릭수"],
    "cost": ["총비용"],
}
# '노출수/클릭수/클릭율' 처럼 한 칸에 여러 값이 '/' 로 붙어있는 경우
COMBINED = {"노출수/클릭수": ["impressions", "clicks"]}
OUTPUT_COLUMNS = ["source_file", *COLUMNS]
EXTENSIONS = {".xls", ".xlsx", ".csv", ".html", ".htm"}


def _raw_tables(path: Path) -> list[pd.DataFrame]:
    """머리글 구분 없이 파일 안의 표들을 그대로 읽는다."""
    if path.suffix.lower() == ".csv":
        for enc in ("utf-8-sig", "cp949"):
            try:
                return [pd.read_csv(path, header=None, dtype=str, encoding=enc)]
            except UnicodeDecodeError:
                continue
    try:
        sheets = pd.read_excel(path, header=None, dtype=str, sheet_name=None)
        return list(sheets.values())
    except Exception:
        pass
    for enc in ("utf-8", "cp949", "euc-kr"):  # 확장자는 .xls 인데 내용은 HTML 인 경우
        try:
            text = path.read_text(encoding=enc)
            return pd.read_html(_html_io(text), header=None)
        except (UnicodeDecodeError, ValueError):
            continue
    raise ValueError(f"읽을 수 없는 파일: {path.name}")


def _html_io(text: str):
    from io import StringIO
    return StringIO(text)


def _with_header(df: pd.DataFrame) -> pd.DataFrame | None:
    """'키워드' 칸이 있는 줄을 찾아서 그 줄을 머리글로 만든다. 없으면 None."""
    headers = [str(c).strip() for c in df.columns]
    if any(c.startswith("키워드") for c in headers):  # HTML 표는 머리글이 이미 열 이름에 들어가 있음
        df = df.copy()
        df.columns = headers
        return df.fillna("").astype(str)
    df = df.fillna("").astype(str)
    for i in range(min(len(df), 20)):
        cells = [c.strip() for c in df.iloc[i].tolist()]
        if any(c.startswith("키워드") for c in cells):
            body = df.iloc[i + 1:].copy()
            body.columns = cells
            return body
    return None


def _pick(headers: list[str], candidates: list[str]) -> str | None:
    for cand in candidates:
        for h in headers:  # 정확히 같은 이름 먼저
            if h.replace(" ", "") == cand.replace(" ", ""):
                return h
    for cand in candidates:
        for h in headers:  # 다음으로 앞부분이 같은 이름 (예: '희망클릭비용 (VAT미포함)')
            if h.replace(" ", "").startswith(cand.replace(" ", "")):
                return h
    return None


def _to_int(v) -> int | None:
    digits = "".join(ch for ch in str(v) if ch.isdigit())
    return int(digits) if digits else None


def read_file(path: Path) -> tuple[pd.DataFrame, dict]:
    """파일 1개 → (표준 열 이름의 표, 머리글 연결 결과, 원래 머리글 목록)"""
    frames, mapping, headers = [], {}, []
    for raw in _raw_tables(path):
        df = _with_header(raw)
        if df is None:
            continue
        headers = list(df.columns)
        mapping = {std: _pick(headers, cands) for std, cands in COLUMNS.items()}
        out = pd.DataFrame({std: (df[src] if src else None) for std, src in mapping.items()})
        for prefix, targets in COMBINED.items():
            src = next((h for h in headers if h.replace(" ", "").startswith(prefix)), None)
            if not src:
                continue
            parts = df[src].astype(str).str.split("/")
            for i, std in enumerate(targets):
                if mapping.get(std) in (None, src):
                    out[std] = parts.str[i]
                    mapping[std] = src
        frames.append(out)
    if not frames:
        raise ValueError(f"'키워드' 머리글을 찾지 못함: {path.name}")
    out = pd.concat(frames, ignore_index=True)
    out["keyword"] = out["keyword"].fillna("").astype(str).str.strip()
    out = out[~out["keyword"].isin(["", "nan"])].copy()
    for col in ("bid", "auto_bid_max", "impressions", "clicks", "cost"):
        out[col] = out[col].map(_to_int)
    out.insert(0, "source_file", path.name)
    if out["group"].isna().all() or (out["group"].astype(str).str.strip() == "").all():
        out["group"] = path.stem  # 파일 안에 그룹명이 없으면 파일 이름을 그룹명으로
    return out[OUTPUT_COLUMNS], mapping, headers


def collect(folder: Path) -> tuple[pd.DataFrame, list[dict]]:
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in EXTENSIONS and not p.name.startswith("~$"))
    frames, report = [], []
    for f in files:
        try:
            df, mapping, headers = read_file(f)
            frames.append(df)
            report.append({"file": f.name, "rows": len(df), "mapping": mapping, "headers": headers})
        except Exception as e:  # 한 파일이 실패해도 나머지는 계속
            report.append({"file": f.name, "error": str(e)})
    merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=OUTPUT_COLUMNS)
    return merged, report
