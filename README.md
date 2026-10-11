# ad-setup
새 G마켓 광고센터(AI Product Ads, 직접 운영형) 키워드 입찰가 **세팅 → 자동 체크 → 자동 수정** 프로그램.
브라우저를 사람 대신 클릭하는 방식(Playwright)이라 광고센터 API가 없어도 동작합니다.

```
 config/keywords.csv  (그룹·상품·키워드별 입찰가, 엑셀로 편집)
      ▲ pull            │ setup --apply → 광고센터 입력 → 다시 읽어서 반영 확인 ✓
      │                 ▼
 [새 G마켓 광고센터]  광고 관리 → 캠페인 → 그룹 수정 → 상품 → 키워드 팝업
      │ check  : keywords.csv 와 실제가 같은지 + 캠페인 성과(노출·클릭·광고비·수익률)
      │ adjust : rules.yaml 규칙대로 입찰가 올림/내림 (키워드별 리포트 조사 후 사용 가능)
```

- 모든 변경 명령은 기본이 **미리보기**. `--apply` 를 붙여야 실제로 바뀝니다.
- 바꾼 뒤에는 화면을 **다시 읽어서 정말 바뀌었는지 확인**하고, `data/changes.csv` 에 이유와 함께 기록합니다.
- 잘못된 입찰가(범위 밖, 10원 단위 아님)와 한 번에 너무 많은 변경은 자동으로 막습니다 (`config/rules.yaml`).

## 파일

| 파일 | 역할 |
|---|---|
| `config/groups.yaml` | 관리할 광고 그룹 (그룹 화면 주소의 번호) |
| `config/keywords.csv` | 원하는 입찰가 — `pull` 로 만들고 엑셀에서 `bid` 칸 수정 |
| `config/rules.yaml` | 자동 수정 규칙 (목표 ROAS, 올림/내림 폭, 입찰가 범위, 안전장치) |
| `config/selectors.yaml` | 광고센터 화면 요소 위치 (`inspect` 로 조사한 값) |
| `mock/` | 실제 광고센터와 같은 구조의 연습용 페이지 |

## 사용법 (Windows PowerShell)

처음 한 번:
```powershell
[Console]::OutputEncoding = [Text.Encoding]::UTF8; $env:PYTHONIOENCODING = "utf-8"
cd $env:USERPROFILE\Documents\ad-setup; git pull
py -3 -m pip install -r requirements.txt; py -3 -m playwright install chromium
py -3 main.py inspect      # 뜨는 브라우저에서 로그인 → PowerShell 에서 q + Enter (로그인 세션 저장)
```

평소:
```powershell
py -3 main.py pull             # 현재 입찰가 → config\keywords.csv
# keywords.csv 를 엑셀로 열어 bid 칸 수정 후 저장
py -3 main.py setup            # 무엇이 바뀔지 미리보기
py -3 main.py setup --apply    # 반영 + 반영 확인
py -3 main.py check            # 검증 + 오늘 성과
```

연습: 모든 명령 뒤에 `--site mock` 을 붙이면 실제 광고에 영향 없이 연습 페이지에서 돌아갑니다.

## 그룹 추가
광고 관리 → 캠페인 → 그룹을 열고 주소창의 `campaignGroupId`, `campaignId`, `campaignGroupType` 값을 `config/groups.yaml` 에 추가합니다.

## 자동 수정 규칙 (기본값, `config/rules.yaml`)
| 상황 | 행동 |
|---|---|
| 클릭 < 20 | 보류 (데이터 부족) |
| 전환 0 + 광고비 ≥ 30,000원 | 최저 입찰가(70원)로 (새 센터는 키워드 OFF가 없음) |
| ROAS < 목표×0.8 | 입찰가 15% 내림 |
| ROAS > 목표×1.2 | 입찰가 10% 올림 |
| 그 외 | 유지 |

`adjust` 는 키워드별 성과가 필요합니다. 새 센터의 **리포트** 화면을 `inspect` 로 조사해 `selectors.yaml` 의 `report` 를 채우면 실제 광고에서도 동작합니다.

## 화면이 바뀌었을 때
`py -3 main.py inspect` 로 해당 화면을 다시 조사해서 `config/selectors.yaml` 만 고치면 됩니다.

## 옛 옥션 광고센터 키워드 백업
옛 센터에서 그룹별로 받은 엑셀(.xls)을 한 폴더에 모은 뒤:
```powershell
py -3 main.py backup --folder "$env:USERPROFILE\Downloads\키워드백업"
```
→ `data/keywords_backup.csv` 로 합쳐집니다. 같은 내용 파일은 자동으로 제외됩니다.

## 주의
- 판매예치금이 마이너스면 광고 노출이 중단됩니다. 세팅은 되지만 성과(노출·클릭)는 0으로 나옵니다.
- `auth/` 폴더(로그인 세션)는 계정 접근 권한과 같습니다. 공유하거나 커밋하지 마세요.
- 하루 몇 번 수준으로만 실행하세요.

## 테스트
```bash
python -m pytest -q
```
