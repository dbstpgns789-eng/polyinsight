#!/bin/bash
# PolyInsight SessionStart Hook
# 웹세션 시작 시 실행 — 로컬 CLI 작업 내용을 이 세션에 동기화 + 의존성 설치
set -uo pipefail

# 웹 환경에서만 실행
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

cd "$CLAUDE_PROJECT_DIR"

# 1. origin/main 최신 상태 가져오기 (merge 없음 — 브랜치 충돌 방지)
echo "[session-start] origin/main 동기화 중..."
git fetch origin main 2>/dev/null && echo "[session-start] fetch 완료" || echo "[session-start] fetch 실패 (네트워크 문제), 스킵"

echo "[session-start] origin/main 최신 5개 커밋:"
git log origin/main --oneline -5 2>/dev/null || git log --oneline -5

echo "[session-start] origin/main 구현 파일 현황:"
git ls-tree -r origin/main --name-only 2>/dev/null \
  | grep -E "\.(py|jsx|html|css)$" | grep -v __pycache__ | sort \
  || echo "  (파일 목록 조회 실패)"

# 2. Python 의존성 설치 (origin/main의 requirements.txt 기준)
echo "[session-start] Python 의존성 설치 중..."
if git show origin/main:backend/requirements.txt > /tmp/pi_requirements.txt 2>/dev/null; then
  pip install -q -r /tmp/pi_requirements.txt && echo "[session-start] pip 설치 완료"
elif [ -f backend/requirements.txt ]; then
  pip install -q -r backend/requirements.txt && echo "[session-start] pip 설치 완료 (로컬 파일)"
else
  echo "[session-start] requirements.txt 없음, 스킵"
fi

# 3. Playwright 브라우저 설치
echo "[session-start] Playwright chromium 확인..."
playwright install chromium --quiet 2>/dev/null && echo "[session-start] Playwright 준비 완료" \
  || echo "[session-start] Playwright 스킵 (이미 설치됨)"

# 4. PYTHONPATH 설정
echo "export PYTHONPATH=\"$CLAUDE_PROJECT_DIR\"" >> "$CLAUDE_ENV_FILE"

echo "[session-start] 완료"
