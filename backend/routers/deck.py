from __future__ import annotations

import asyncio
import io
import json
import uuid
import zipfile
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Response, UploadFile

from pydantic import BaseModel, Field

from ..agents.deck.caption import generate_caption
from ..agents.deck.deck_renderer import render_deck
from ..agents.deck.nl_patch import apply_nl_patch
from ..agents.deck.pipeline import compute_verify, persist_edited_deck, run_authoring_pipeline
from ..core import db, plans, ratelimit, signing
from ..core import images as images_util
from ..core.auth import get_current_user, require_owned_job
from ..core.config import settings

router = APIRouter(prefix="/api", tags=["deck"])

# 카드 PNG는 24h TTL 캐시(만료성) — 저작 HTML만 영구. 만료/미존재 카드를 요청하면
# 저장된 HTML에서 재렌더해 자가치유한다. job별 락으로 병렬 카드 요청 스탬피드 방지.
_heal_locks: dict[str, asyncio.Lock] = {}


async def _heal_card_images(job_id: str, card_num: int) -> bytes | None:
    """만료/미존재 카드를 저장된 저작 HTML에서 재렌더(전 카드) → 요청 카드 반환. 복구 불가 시 None."""
    lock = _heal_locks.setdefault(job_id, asyncio.Lock())
    async with lock:
        # 락 대기 중 다른 요청이 이미 재렌더했을 수 있으니 재확인.
        images = await db.get_card_images(job_id)
        if card_num in images:
            return images[card_num]
        deck = await db.get_authored_deck(job_id)
        html = deck.get("html") if deck else None
        if not html:
            return None
        await render_deck(html, job_id=job_id)   # 전 카드 재렌더 + DB 저장(fresh 24h TTL)
        images = await db.get_card_images(job_id)
        return images.get(card_num)

_MAX_PDF_BYTES = 50 * 1024 * 1024  # 50 MB
_MAX_ASSET_BYTES = 8 * 1024 * 1024  # 8 MB — 덱 이미지 자산
# SVG 제외(XSS/SSRF 축소, 스펙 §7). 저작 덱의 raster 삽입만 허용.
_ASSET_MIME_WHITELIST = {"image/png", "image/jpeg", "image/webp", "image/gif"}
_ASSET_SOURCE_TYPES = {"upload-owned", "upload-data", "paper-figure"}


@router.post("/deck/upload", status_code=202)
async def deck_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile,
    card_count: Annotated[int, Form(ge=3, le=12)] = 7,
    persona: Annotated[str | None, Form()] = None,
    style_direction: Annotated[str | None, Form()] = None,
    user: dict = Depends(get_current_user),
):
    """PDF 업로드 → 단일 저작 파이프라인 백그라운드 시작 (헌법 v3.0).

    style_direction: 아트 디렉션(미감 방향, 선택). 비우면 모델 자유 선택.
    """
    plans.require_can_author(user)         # 플랜 게이트 — 무료 1덱 상한(원가 방어)
    ratelimit.enforce_upload_quota(user)   # 유저별 일일 쿼터(재정 DoS) — 플랜과 별개 축
    if file.content_type not in ("application/pdf", "application/octet-stream"):
        if not (file.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, detail={"code": "ERR-INP-001", "message": "PDF 파일만 업로드 가능합니다."})

    pdf_bytes = await file.read()
    if len(pdf_bytes) > _MAX_PDF_BYTES:
        raise HTTPException(400, detail={"code": "ERR-INP-002", "message": "파일 크기가 50MB를 초과합니다."})

    # 티어 상한으로 클램프(base=Sonnet/AUTHOR_MAX_CARDS, 추후 premium 확장)
    card_count = max(3, min(card_count, settings.AUTHOR_MAX_CARDS))

    # 무료 체험 선차감 — **원자적**으로 소비한다. job 생성보다 먼저 해야 한다:
    # require_can_author는 읽은 스냅샷 기반이라 동시 요청 2건이 둘 다 통과할 수 있고
    # (check-then-act), 실제 상한 강제는 이 UPDATE 한 문장이 담당한다. create_job **뒤에**
    # 두면 레이스에서 진 요청이 이미 만든 job 행을 고아로 남긴다 — list_jobs/list_projects는
    # status 필터 없이 그대로 노출하므로 대시보드에 "PENDING"이 서버 재시작 전까지 영원히
    # 뜬다(recover_stale_jobs는 startup 1회뿐). 그래서 job_id를 만들기 전에 소비부터 한다.
    # 파이프라인이 ERROR로 끝나면 pipeline._log_done에서 환불한다(Task 4, 아하 보장).
    if plans.should_consume_free_deck(user):
        if not await db.consume_free_deck(user["id"], plans.FREE_DECK_LIMIT):
            raise plans.author_gate_error(user)   # 레이스에서 진 요청

    job_id = str(uuid.uuid4())
    await db.create_job(job_id, title=file.filename, user_id=user["id"])
    await db.log_event("deck_upload", user_id=user["id"], job_id=job_id,
                       payload={"filename": file.filename, "card_count": card_count})
    background_tasks.add_task(
        run_authoring_pipeline, job_id, pdf_bytes, card_count, persona, user["id"], style_direction
    )
    return {"jobId": job_id, "status": "PENDING"}


@router.get("/deck/{job_id}")
async def get_deck(job_id: str, user: dict = Depends(get_current_user)):
    """덱 뷰용 — 저작 HTML + 충실성 검증 + 상태."""
    job = await require_owned_job(job_id, user)
    deck = await db.get_authored_deck(job_id)
    verify = None
    if deck and deck.get("verify_json"):
        try:
            verify = json.loads(deck["verify_json"])
        except Exception:
            verify = None
    return {
        "jobId": job_id,
        "filename": job["title"],
        "status": job["status"],
        "warnings": job.get("warnings", []),
        "html": deck["html"] if deck else None,
        "verify": verify,
        "cardCount": deck["card_count"] if deck else 0,
        "canReverify": bool(deck and deck.get("paper_text")),
    }


class DeckPatch(BaseModel):
    html: str = Field(min_length=1, max_length=2_000_000)


@router.patch("/deck/{job_id}")
async def patch_deck(job_id: str, body: DeckPatch, user: dict = Depends(get_current_user)):
    """편집된 덱 HTML 저장(직접조작) → 재검증 + PNG 재렌더. 최종 판단은 사용자(헌법 3조)."""
    await require_owned_job(job_id, user)
    deck = await db.get_authored_deck(job_id)
    if deck is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "덱이 없습니다."})
    if "data-screen-label" not in body.html:
        raise HTTPException(
            400, detail={"code": "ERR-INP-003", "message": "유효한 덱 HTML이 아닙니다(카드 라벨 없음)."}
        )
    result = await persist_edited_deck(job_id, body.html)
    await db.log_event("deck_edit", user_id=user["id"], job_id=job_id,
                       payload={"kind": "direct", "card_count": result["cardCount"]})
    return result


class DeckNLPatch(BaseModel):
    instruction: str = Field(min_length=1, max_length=2000)


@router.post("/deck/{job_id}/nlpatch")
async def nlpatch_deck(job_id: str, body: DeckNLPatch, user: dict = Depends(get_current_user)):
    """자연어 편집 — 지시로 덱 HTML 최소 변경(1회 LLM) → 재검증 + PNG 재렌더.

    모델이 출력 계약을 깨면(카드 라벨 소실) 원본을 보존하고 거부한다(422).
    응답에 수정된 html 동봉 → 프론트가 에디터를 갱신본으로 재마운트.
    """
    await require_owned_job(job_id, user)
    plans.require_can_ai_designer(user)   # AI 디자이너 = 유료 (호출마다 LLM 원가 방어)
    deck = await db.get_authored_deck(job_id)
    if deck is None or not deck.get("html"):
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "덱이 없습니다."})

    new_html = await apply_nl_patch(deck["html"], body.instruction, deck.get("paper_text"))
    if "data-screen-label" not in new_html:
        raise HTTPException(
            422,
            detail={"code": "ERR-EDIT-001",
                    "message": "수정 결과가 덱 구조를 벗어나 적용하지 않았습니다. 원본은 그대로입니다."},
        )

    result = await persist_edited_deck(job_id, new_html)
    result["html"] = new_html
    await db.log_event("deck_edit", user_id=user["id"], job_id=job_id,
                       payload={"kind": "nl", "card_count": result["cardCount"]})
    return result


class DeckNLTarget(BaseModel):
    eid: str | None = None
    cardIndex: int | None = None
    quotedText: str | None = Field(default=None, max_length=4000)


class DeckNLPropose(BaseModel):
    instruction: str = Field(min_length=1, max_length=2000)
    html: str = Field(min_length=1, max_length=2_000_000)
    target: DeckNLTarget | None = None


@router.post("/deck/{job_id}/nlpatch/propose")
async def nlpatch_propose(job_id: str, body: DeckNLPropose, user: dict = Depends(get_current_user)):
    """AI 편집 제안 — 미저장·미렌더. 라이브 캔버스 html + target으로 최소 변경 수정본을
    만들어 verify와 함께 반환한다. 실제 반영은 PATCH /deck/{id}(commit)에서만."""
    await require_owned_job(job_id, user)
    plans.require_can_ai_designer(user)   # AI 디자이너 = 유료 (호출마다 LLM 원가 방어)
    deck = await db.get_authored_deck(job_id)
    if deck is None or not deck.get("html"):
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "덱이 없습니다."})

    new_html = await apply_nl_patch(
        body.html, body.instruction, deck.get("paper_text"),
        target=body.target.model_dump() if body.target else None,
    )
    if "data-screen-label" not in new_html:
        raise HTTPException(
            422,
            detail={"code": "ERR-EDIT-001",
                    "message": "수정 결과가 덱 구조를 벗어나 제안하지 않았습니다. 원본은 그대로입니다."},
        )

    verify = compute_verify(new_html, deck.get("paper_text"))
    await db.log_event("deck_edit", user_id=user["id"], job_id=job_id, payload={"kind": "nl-propose"})
    return {"html": new_html, "verify": verify}


@router.post("/deck/{job_id}/assets", status_code=201)
async def upload_deck_asset(
    job_id: str,
    file: UploadFile,
    source_type: Annotated[str, Form()] = "upload-owned",
    user: dict = Depends(get_current_user),
):
    """사용자 이미지 업로드 → deck_assets 바이트 저장 → {assetId, url} (스펙 §3.1 업로드).

    저장 HTML엔 반환 url만 실리고, 렌더 직전 deck_renderer가 data URI로 인라인한다.
    """
    await require_owned_job(job_id, user)

    mime = (file.content_type or "").lower()
    if mime not in _ASSET_MIME_WHITELIST:
        raise HTTPException(
            400,
            detail={"code": "ERR-IMG-001",
                    "message": "지원하지 않는 이미지 형식입니다(PNG·JPEG·WebP·GIF)."},
        )
    data = await file.read()
    if not data:
        raise HTTPException(400, detail={"code": "ERR-IMG-003", "message": "빈 파일입니다."})
    if len(data) > _MAX_ASSET_BYTES:
        raise HTTPException(400, detail={"code": "ERR-IMG-002", "message": "이미지 크기가 8MB를 초과합니다."})

    st = source_type if source_type in _ASSET_SOURCE_TYPES else "upload-owned"
    asset_id = uuid.uuid4().hex[:16]
    await db.save_deck_asset(job_id, asset_id, data, mime, source_type=st)
    await db.log_event("deck_asset_upload", user_id=user["id"], job_id=job_id,
                       payload={"asset_id": asset_id, "mime": mime,
                                "source_type": st, "bytes": len(data)})
    return {"assetId": asset_id, "url": f"/api/deck/{job_id}/assets/{asset_id}"}


@router.get("/deck/{job_id}/assets/{asset_id}")
async def get_deck_asset(job_id: str, asset_id: str):
    """자산 바이트를 원본 mime으로 서빙 — **무인증 capability URL**(스펙 §9).

    편집 미리보기는 sandboxed iframe(null-origin)이라 인증 서빙 URL에 세션 쿠키를
    실을 수 없어 401→빈칸 렌더가 된다(2026-07-01 실측). 추측 불가능한 job_id+asset_id
    조합이 접근 권한. export/렌더 PNG는 이 라우트 대신 렌더시 인라인이 대체한다.
    """
    asset = await db.get_deck_asset(job_id, asset_id)
    if asset is None or asset.get("bytes") is None:
        raise HTTPException(
            404,
            detail={"code": "ERR-IMG-004",
                    "message": "이미지를 찾을 수 없습니다(만료되었을 수 있습니다)."},
        )
    return Response(content=asset["bytes"], media_type=asset["mime"] or "image/png")


@router.get("/deck/{job_id}/cards/{card_num}/public")
async def get_card_public(job_id: str, card_num: int, exp: int = 0, sig: str = ""):
    """서명·만료 검증된 무인증 카드 이미지 (Meta Graph API image_url용, 스펙 §5).
    ★B1: Meta는 JPEG·폭≤1440만 허용 → 저장 PNG(2160)를 1080폭 JPEG로 변환해 서빙.
    ★M3: signing.verify_card가 시크릿 없으면 무조건 False(빈키 위조 차단). self-heal 재사용."""
    if not signing.verify_card(job_id, card_num, exp, sig):
        raise HTTPException(404, detail={"code": "ERR-IMG-004", "message": "not found"})
    png = await _heal_card_images(job_id, card_num)
    if png is None:
        raise HTTPException(404, detail={"code": "ERR-IMG-004", "message": "not found"})
    jpeg = images_util.to_jpeg(png, max_width=1080)
    return Response(content=jpeg, media_type="image/jpeg")


@router.get("/deck/{job_id}/cards/{card_num}")
async def get_deck_card(job_id: str, card_num: int, user: dict = Depends(get_current_user)):
    """덱 카드 1장 PNG."""
    await require_owned_job(job_id, user)
    images = await db.get_card_images(job_id)
    png = images.get(card_num)
    if png is None:
        # 렌더 캐시 만료(24h) 또는 미존재 → 저장된 HTML에서 자가치유 재렌더(원본을 DB에 저장).
        png = await _heal_card_images(job_id, card_num)
    if png is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "카드 이미지가 없습니다."})

    # 저장은 항상 원본(위 자가치유 포함) — 응답만 무료 유저에게 축소. 순서를 바꾸면
    # 축소본이 DB에 영구 저장돼 유료 전환 후에도 저해상도가 남는다.
    if not plans.can_export(user):
        png = images_util.downscale_png(png)
    return Response(content=png, media_type="image/png")


@router.get("/deck/{job_id}/caption")
async def get_deck_caption(job_id: str, user: dict = Depends(get_current_user)):
    """인스타 게시용 캡션 → {caption, hashtags}. lazy 생성 + 캐시.

    ★게이트 없음(export 게이트 안 걸림): 캡션 미리보기는 무료 아하다(순수잠금은 파일만).
    비용 방어는 게이트가 아니라 캐시로 — 첫 요청만 LLM(덱당 1회로 바운드), 이후는 캐시 read.
    편집 시 save_authored_deck이 캡션을 무효화(NULL)해 다음 요청에 재생성(staleness 처리).
    """
    await require_owned_job(job_id, user)
    deck = await db.get_authored_deck(job_id)
    if deck is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "덱이 없습니다."})

    cached = deck.get("caption_json")
    if cached:
        return json.loads(cached)

    result = await generate_caption(deck["html"] or "", deck.get("paper_text") or "")
    await db.set_deck_caption(job_id, json.dumps(result, ensure_ascii=False))
    return result


@router.post("/deck/{job_id}/export")
async def export_deck(job_id: str, user: dict = Depends(get_current_user)):
    """저장된 카드 PNG + HTML + 검증 결과를 ZIP으로. 다운로드는 /api/export/{id}/download 재사용."""
    plans.require_can_export(user)
    await require_owned_job(job_id, user)
    deck = await db.get_authored_deck(job_id)
    if deck is None:
        raise HTTPException(404, detail={"code": "ERR-JOB-001", "message": "덱이 없습니다."})
    images = await db.get_card_images(job_id)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for n in sorted(images):
            zf.writestr(f"card_{n:02d}.png", images[n])
        zf.writestr("deck.html", deck["html"] or "")
        if deck.get("verify_json"):
            zf.writestr("verify.json", deck["verify_json"])

    export_id = str(uuid.uuid4())
    await db.save_export(export_id, job_id, buf.getvalue(), f"polyinsight_deck_{job_id[:8]}.zip")
    await db.log_event("deck_export", user_id=user["id"], job_id=job_id,
                       payload={"export_id": export_id, "image_count": len(images)})
    return {"exportId": export_id, "status": "DONE"}
