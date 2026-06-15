# PolyInsight 백엔드 (FastAPI + Playwright/Chromium)
# Playwright 공식 python 이미지 = Chromium + 시스템 의존성 포함, arm64(Oracle Ampere) 지원.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && python -m playwright install chromium

COPY backend ./backend

# SQLite는 마운트 볼륨(/data)에 저장 → 재배포·재시작에도 영속
ENV DATABASE_URL=sqlite:////data/polyinsight.db
VOLUME ["/data"]

EXPOSE 8000
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
