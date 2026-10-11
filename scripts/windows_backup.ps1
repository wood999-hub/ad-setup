# 키워드 백업 한 번에 실행 (Windows PowerShell)
# 1) 다운로드 폴더의 키워드 엑셀을 '키워드백업' 폴더로 복사  2) Python/Git 없으면 설치
# 3) 프로그램 받기/업데이트  4) backup 실행
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$env:PYTHONIOENCODING = "utf-8"

$dl   = Join-Path $env:USERPROFILE "Downloads"
$bk   = Join-Path $dl "키워드백업"
$repo = Join-Path $env:USERPROFILE "Documents\ad-setup"

function Refresh-Path {
  $env:Path = [Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [Environment]::GetEnvironmentVariable("Path","User")
}

# 1) 엑셀 복사 (원본은 그대로 둠)
New-Item -ItemType Directory -Force -Path $bk | Out-Null
$files = Get-ChildItem $dl -File | Where-Object { $_.Name -like "20261011_admanagement*.xls*" -or $_.BaseName -eq "팻말" }
if (-not $files) { Write-Host "다운로드 폴더에서 키워드 엑셀을 못 찾았습니다." -ForegroundColor Red; return }
$files | Copy-Item -Destination $bk -Force
Write-Host "엑셀 $($files.Count)개 → $bk 복사 완료" -ForegroundColor Green

# 2) Python / Git 설치 (없을 때만)
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
  Write-Host "Python 설치 중..."; winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements; Refresh-Path
}
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Host "Git 설치 중..."; winget install -e --id Git.Git --accept-source-agreements --accept-package-agreements; Refresh-Path
}

# 3) 프로그램 받기 (이미 있으면 최신으로)
if (Test-Path $repo) {
  git -C $repo pull
} else {
  git clone -b claude/cool-euler-nrua88 https://github.com/wood999-hub/ad-setup.git $repo
}
Set-Location $repo
py -3 -m pip install -q -r requirements.txt

# 4) 백업 실행
py -3 main.py backup --folder $bk
Write-Host "`n결과 파일: $repo\data\keywords_backup.csv" -ForegroundColor Green
