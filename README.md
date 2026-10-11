# ad-setup
광고 세팅 → 자동 체크 → 자동 수정 프로그램 (G마켓/옥션 광고센터용, Playwright 브라우저 자동화)

## 이 프로그램이 하는 일

```
 [ads.yaml]  원하는 세팅값 (입찰가·일예산·ON/OFF)
     │ setup      → 광고센터 화면을 열어 값이 다르면 고침
     ▼
 [광고센터]
     │ check      → 세팅이 제대로 들어갔는지 확인 + 성과표(클릭·광고비·매출) 수집
     ▼
 [rules.yaml] 규칙 (목표 ROAS 등)
     │ adjust     → 규칙에 따라 입찰가 올림/내림/OFF 결정 → 반영 → ads.yaml 갱신
     └──────────── 반복
```

- 사람 대신 **브라우저를 클릭/입력**하는 방식입니다. (광고센터는 공개 API가 없어서)
- 모든 명령은 기본이 **미리보기**입니다. `--apply` 를 붙여야 실제로 바뀝니다.
- 바꾼 내역은 전부 `data/changes.csv` 에 남습니다.

## 폴더 구조

| 파일 | 역할 | 누가 고치나 |
|---|---|---|
| `config/ads.yaml` | 원하는 광고 세팅값 (정답 파일) | 나 |
| `config/rules.yaml` | 자동 수정 규칙 (목표 ROAS, 올림/내림 폭, 안전장치) | 나 |
| `config/selectors.yaml` | 광고센터 화면의 버튼/입력칸 위치 | 나 (1회, 3단계) |
| `mock/` | 연습용 가짜 광고센터 + 완성된 selectors 예시 | - |
| `adbot/rules.py` | 판단 로직 (브라우저와 분리 → 테스트 가능) | - |
| `adbot/site.py` | 브라우저 조작 | - |
| `main.py` | 실행 명령 | - |

---

## 따라하기

### 1단계: 설치 (내 PC, 10분)
Python 3.10 이상 필요.
```bash
git clone https://github.com/wood999-hub/ad-setup.git
cd ad-setup
pip install -r requirements.txt
playwright install chromium
```

### 2단계: 연습 모드로 전체 흐름 익히기 (실제 광고 영향 없음)
```bash
python main.py setup  --site mock            # 미리보기: A1001 입찰가 200→300 바꿀 예정이라고 나옴
python main.py setup  --site mock --apply    # 실제 반영 (브라우저가 뜨고 자동으로 클릭함)
python main.py check  --site mock            # 세팅 검증 ✓ + 성과표 수집
python main.py adjust --site mock            # 규칙 판단: A1001 올림, A1002 내림, A1003 보류
python main.py adjust --site mock --apply    # 반영 → ads.yaml 도 자동 갱신
```
`config/rules.yaml` 의 `target_roas` 를 바꿔서 다시 `adjust` 해보면 판단이 어떻게 달라지는지 볼 수 있습니다.
연습 데이터 초기화: `data/` 폴더 삭제.

### 3단계: 실제 광고센터 화면 요소 찾기 (핵심, 1회)
프로그램이 "어느 버튼을 누를지" 알려면 화면 요소의 이름(selector)이 필요합니다.

1. 녹화 도구 실행:
   ```bash
   playwright codegen https://www.esmplus.com
   ```
2. 뜬 브라우저에서 로그인 → 광고 목록 화면 → 광고 1개의 **수정** 클릭 → 입찰가 입력 → **저장**까지 **직접** 해봅니다.
3. 옆 창에 코드가 자동으로 생깁니다. 예:
   ```python
   page.locator("#adList tbody tr").nth(0).get_by_role("button", name="수정").click()
   page.fill("#bidInput", "300")
   ```
   여기서 `"#adList tbody tr"`, `"#bidInput"` 같은 따옴표 안 부분을 `config/selectors.yaml` 의 `TODO` 자리에 옮겨 적습니다.
   (`mock/selectors.yaml` 이 완성 예시)
4. 표 안의 값(광고번호 속성 등)은 Chrome에서 해당 칸 **우클릭 → 검사**로 HTML을 보고 확인합니다.
   광고번호가 `<tr data-ad-id="A1001">` 처럼 들어있으면 `id_attr: data-ad-id`.

> ⚠️ 화면에서 **실제 저장 버튼을 누르면 실제 광고가 바뀝니다.** 녹화할 때는 같은 값으로 저장하거나, 꺼둔 테스트 광고로 하세요.

### 4단계: 로그인 세션 저장
```bash
python main.py login
```
브라우저에서 직접 로그인(캡차·2차인증 포함) 후 터미널에서 Enter. 쿠키가 `auth/state.json` 에 저장되고 이후 명령은 로그인 없이 동작합니다.
`auth/` 는 `.gitignore` 되어 있어 커밋되지 않습니다. **절대 남에게 공유하지 마세요** (계정 접근 권한과 같습니다).
세션이 만료되면 다시 `login`.

### 5단계: 실제 광고에 적용 (작게 시작)
1. `config/ads.yaml` 에 **광고 1개만** 넣고 현재 값 그대로 적습니다.
2. `python main.py check` → ✓ 가 나오면 읽기는 성공.
3. 입찰가를 10원만 바꾸고 `python main.py setup` (미리보기) → `--apply` → 광고센터에서 눈으로 확인.
4. `python main.py adjust` 미리보기를 며칠 지켜보고, 판단이 맞다고 느껴지면 `--apply`.

### 6단계: 매일 자동 실행
Windows 작업 스케줄러 / macOS·Linux cron 으로 하루 1~2회:
```
python main.py check  --headless
python main.py adjust --headless --apply
```
안전장치: `rules.yaml` 의 `max_changes_per_run` 보다 많이 바꾸려 하면 아무것도 안 바꾸고 중단합니다.

---

## 키워드 백업 (광고센터 이전 전에 필수)
파워클릭 일반그룹의 **OFF 키워드는 새 광고센터로 이전되지 않고 삭제**됩니다. 이전 전에 백업하세요.

1. 옛 광고센터에서 그룹마다 **엑셀 다운로드**
2. 받은 파일만 새 폴더에 모으고, **파일 이름을 그룹명으로** 바꿈 (예: `칼라콘.xls`)
3. 실행:
   ```bash
   python main.py backup --folder "C:\Users\PC\Downloads\키워드백업"
   ```
4. 그룹별 키워드 수가 광고센터 화면과 같은지 확인 → `data/keywords_backup.csv` 에 전체가 합쳐짐

똑같은 내용의 파일이 있으면(같은 그룹을 두 번 받은 경우) 경고가 나옵니다.

## 자동 수정 규칙 (기본값)
| 상황 | 행동 |
|---|---|
| 클릭 < 20 | 보류 (데이터 부족) |
| 전환 0 + 광고비 ≥ 30,000원 | 광고 OFF |
| ROAS < 목표×0.8 | 입찰가 15% 내림 |
| ROAS > 목표×1.2 | 입찰가 10% 올림 |
| 그 외 | 유지 |

입찰가는 10원 단위, 70~3,000원 범위로 제한됩니다. 모두 `config/rules.yaml` 에서 변경.

## 주의
- 지금 화면은 기존 옥션 광고센터 → **신규 G마켓 광고센터(AI Product Ads)** 이전 안내입니다. 이전할 거라면 3단계 selector는 **새 광고센터 화면 기준**으로 잡으세요. 옛 화면 기준으로 만들면 이전 후 다시 해야 합니다.
- AI매출업/AI Product Ads 처럼 **입찰을 AI가 자동으로 하는 유형**은 입찰가를 직접 조정할 수 없습니다. 이 프로그램의 입찰가 조정은 직접 운영형(파워클릭 일반그룹 같은)에 맞습니다. AI형은 `check`(성과 수집·검증) 위주로 쓰고, 예산·ON/OFF만 조정하세요.
- 광고센터 화면이 개편되면 `selectors.yaml` 만 다시 잡으면 됩니다.
- 자동화 사용이 광고센터 이용약관에 맞는지 확인하고, 하루 몇 번 수준으로만 돌리세요.

## 테스트
```bash
python -m pytest -q
```
