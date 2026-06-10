"""실제 논문 PDF → S1→S6→S7→S8 전체 파이프라인 테스트."""
import asyncio
import sys
import logging
from pathlib import Path

# ── 로깅 설정: 모든 단계 상세 출력 ──────────────────────────────────────────
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("pipeline_debug.log", encoding="utf-8"),
    ],
)
# 너무 verbose한 라이브러리 로그 억제
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("asyncio").setLevel(logging.WARNING)

sys.path.insert(0, str(Path(__file__).parent))

from backend.agents.orchestrator import run_pipeline
from backend.core import db
from backend.core.models import CardTheme
from backend.core.llm_client import llm_client

PDF_PATH = Path(r"C:\Users\User\Desktop\한국생산기술연구원_근로장학\poly_claude_code\논문\VAE_Auto_Encoding_Variational_Bayes.pdf")
OUTPUT_DIR = Path(__file__).parent / "render_output_pipeline"
JOB_ID = "test-vae-004"

logger = logging.getLogger("pipeline_test")


async def main():
    if not PDF_PATH.exists():
        logger.error("PDF 없음: %s", PDF_PATH)
        sys.exit(1)

    pdf_bytes = PDF_PATH.read_bytes()
    logger.info("━━━ PDF 로드: %s (%s bytes) ━━━", PDF_PATH.name, f"{len(pdf_bytes):,}")

    # DB 초기화 및 job 생성
    await db.migrate()
    # 기존 job 있으면 삭제 후 재생성
    existing = await db.get_job(JOB_ID)
    if existing:
        logger.info("기존 job 발견 → 재사용: %s", JOB_ID)
    else:
        await db.create_job(JOB_ID, title=PDF_PATH.stem)
        logger.info("Job 생성: %s", JOB_ID)

    # LLM 사용량 사전 확인
    stats = llm_client.usage_stats()
    logger.info("LLM 사용량 현황: %d/%d (잔여 %d회)", stats['daily_calls'], stats['daily_limit'], stats['remaining'])

    # 파이프라인 실행
    logger.info("━━━ 파이프라인 시작 (S1 → S6 → S7 → S8) ━━━")
    await run_pipeline(
        job_id=JOB_ID,
        pdf_bytes=pdf_bytes,
        theme=CardTheme(),
        card_count=5,
    )

    # 최종 결과 확인
    job = await db.get_job(JOB_ID)
    logger.info("━━━ 파이프라인 완료 ━━━")
    logger.info("상태:    %s", job['status'])
    logger.info("스테이지: %s", job.get('stage', '-'))
    logger.info("진행률:  %s%%", job.get('progress', 0))
    if job.get('warnings'):
        logger.warning("경고 목록:\n%s", '\n'.join(job['warnings']) if isinstance(job['warnings'], list) else job['warnings'])

    # S6 카드 데이터 확인
    card_data_json = await db.get_card_data(JOB_ID)
    if card_data_json:
        import json
        card_data = json.loads(card_data_json)
        logger.info("━━━ S6 출력 카드 데이터 ━━━")
        logger.info("%s", json.dumps(card_data, ensure_ascii=False, indent=2))
    else:
        logger.warning("카드 데이터 없음")

    # PNG 저장
    images = await db.get_card_images(JOB_ID)
    if images:
        OUTPUT_DIR.mkdir(exist_ok=True)
        for card_num, img_bytes in sorted(images.items()):
            out_path = OUTPUT_DIR / f"card{card_num}.png"
            out_path.write_bytes(img_bytes)
            logger.info("PNG 저장: %s (%s bytes)", out_path.name, f"{len(img_bytes):,}")
        logger.info("출력 폴더: %s", OUTPUT_DIR.resolve())
    else:
        logger.warning("PNG 없음")

    # 최종 LLM 사용량
    stats = llm_client.usage_stats()
    logger.info("━━━ LLM 최종 사용량: %d/%d ━━━", stats['daily_calls'], stats['daily_limit'])


if __name__ == "__main__":
    asyncio.run(main())
