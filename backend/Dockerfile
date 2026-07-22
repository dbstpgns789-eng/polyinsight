# PolyInsight 백엔드 (FastAPI + Playwright/Chromium)
# Playwright 공식 python 이미지 = Chromium + 시스템 의존성 포함, arm64(Oracle Ampere) 지원.
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# 스캔본 OCR (2026-07-21) — OCR 엔진은 PyMuPDF에 번들, 언어데이터만 필요하다.
# tesseract-ocr-kor/eng가 traineddata를 /usr/share/tesseract-ocr/4.00/tessdata 에 깐다.
# TESSDATA_PREFIX로 PyMuPDF의 get_textpage_ocr가 그 경로를 찾게 한다.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        tesseract-ocr tesseract-ocr-kor tesseract-ocr-eng \
    && rm -rf /var/lib/apt/lists/*
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/4.00/tessdata

COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --no-cache-dir -r backend/requirements.txt \
    && python -m playwright install chromium

COPY backend ./backend

# SQLite는 마운트 볼륨(/data)에 저장 → 재배포·재시작에도 영속
ENV DATABASE_URL=sqlite:////data/polyinsight.db
VOLUME ["/data"]

EXPOSE 8000
# --proxy-headers: CF터널→web→backend 체인의 X-Forwarded-* 신뢰(실 IP·scheme). backend는 compose 내부에서만 접근.
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips", "*"]
