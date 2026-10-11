# ad-setup — 프로젝트 안내 (Claude Code 용)

G마켓 광고(새 G마켓 광고센터 · AI Product Ads · 직접 운영형) 키워드 입찰가를
세팅·확인·조정하는 Windows 데스크톱 프로그램. 사용자는 개발자가 아닌 판매자(가게: 에브리즘).

## 사용자와 대화하는 법
- 한국어로, 짧게. 형식: **결론 → 근거 → 검증 → 행동지침 → 지금 해야 할 것 1가지**
- 사용자는 Windows PC + PowerShell 을 쓴다. 명령은 그대로 붙여넣을 수 있게 PowerShell 로.
- Claude(클라우드)는 사용자 PC 파일·광고센터·G마켓에 직접 접근할 수 없다.
  사용자가 캡처나 출력 내용을 보내주면 그걸로 판단한다. 클라우드에서는 gmarket.co.kr 접속이 막혀 있다.

## 사용자 PC
- 설치 위치: `C:\Users\PC\Documents\ad-setup` (git clone, 프로그램의 [프로그램 업데이트] = `git pull`)
- 실행: 바탕화면 [광고 자동화] 아이콘 → `광고자동화.pyw` (tkinter 창, 검은 창 없음)
- PC 에만 있는 것(깃에 없음): `auth/`(로그인 세션), `data/`(기록·결과), `config/keywords.csv`(입찰가)
- 판매자ID chm87929, 관리 그룹 'MK관리 REV.3 추가' (config/groups.yaml), 상품 2168720238

## 구조
| 파일 | 역할 |
|---|---|
| `광고자동화.pyw` | 버튼 창. main.py 명령을 숨김 실행하고 결과를 색으로 표시 |
| `main.py` | 명령: pull / setup / check / on / off / plan / rank / rank-tabs / backup / inspect / adjust |
| `adbot/gmarket.py` | 새 광고센터 조작 (그룹 수정 화면 → 상품 → 키워드 팝업 입찰가 읽기/쓰기, 캠페인 ON/OFF) |
| `adbot/strategy.py` + `config/strategy.yaml` | 리포트 성과(ROAS) 기반 입찰가·일예산 조정 규칙 (순위 로직 없음) |
| `adbot/report.py` + `config/report_columns.yaml` | 광고센터 리포트 엑셀(키워드별·날짜별) 읽기 |
| `adbot/rank.py` + `config/rank.yaml` | G마켓 검색 결과에서 내 상품 광고 순위 (북마크 반자동 + 자동) |
| `adbot/backup.py` | 옛 옥션 광고센터 키워드 엑셀 백업 합치기 |
| `adbot/inspect_page.py` | 화면 구조 조사 → selectors 작성용 |
| `config/selectors.yaml` | 새 광고센터 화면 요소 위치 (inspect 로 확인한 값) |
| `mock/` | 실제 화면 구조를 흉내 낸 연습용 페이지. `--site mock` 으로 테스트 |
| `사용설명서.txt` | 사용자용 설명서 (UTF-8 BOM, CRLF) |

## 확인된 사실 / 결정 (2026-10-11)
- 파워클릭 → AI Product Ads 로 개편. 새 광고센터(adcenter.esmplus.com)에는 **순위 지정 입찰·순위 지표가 없다**.
  입찰가는 상한선. 그래서 조정은 리포트 성과(ROAS) 기준(`plan`), 순위는 참고용(`rank`).
- 판단 기준 기본값: 광고 상품 기준 ROAS 300%, 최근 7일 제외(전환 15일 지연), 최소 클릭 30, 1회 ±10%(최대 20%),
  입찰가 90~200,000원, 일예산 10,000~10,000,000원.
- 사용자 목표 순위: 모든 키워드 광고 4위 안 (`config/rank.yaml`).
- G마켓 검색 결과의 광고는 상품마다 AD 표시가 아니라 **구역 제목 옆 '광고ⓘ'** 로 표시됨
  ('오늘의 상품이에요', '먼저 둘러보세요'). 그 구역 안 순서로 순위를 센다.
- 자동화 브라우저로 G마켓 검색 시 봇 확인이 뜬다 → 평소 크롬에 탭을 열고 '내 순위' 북마크로 확인하는 반자동 방식이 기본.
  봇 확인을 우회(사람 흉내 마우스/키보드)하는 방식은 만들지 않기로 함.
- 약관(화면 자동조작)은 사용자가 '테스트 단계라 신경 쓰지 말라'고 함. 화면 조작 기능 유지.
- 옥션: 옛 옥션 광고센터 파워클릭 그룹 전부 OFF. G마켓만 운영.
- 남은 일: 엑셀등록 템플릿 받아 업로드용 엑셀 생성 / 입찰 마감(16시) 전 알림 / 주말 OFF(금) · ON(일) 예약 / 리포트 칸 이름 실제 파일로 확정.

## 개발 규칙
- 실제 사이트에서 못 돌려본 건 반드시 '확인 전' 이라고 말한다. mock 으로 먼저 검증.
- 테스트: `python -m pytest -q` (Playwright 필요. 화면 표시가 필요한 명령은 `xvfb-run`).
- 사용자 파일(엑셀·CSV)은 utf-8-sig 로 쓰고, 읽을 때 cp949 도 허용(엑셀 저장 시 바뀜).
