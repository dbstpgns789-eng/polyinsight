"""서빙 레이어 이미지 변환.

무료 유저에게 인라인 카드를 축소해서 준다 — "다 보이되 못 가져간다"(순수잠금)의
'못 가져간다'를 실제로 성립시키는 조각. 게이트(402)가 아니라 해상도 차등이다.
"""
from __future__ import annotations

import io

from PIL import Image

PREVIEW_SCALE = 0.5  # 1080×1350 → 540×675. 화면에선 충분, 인스타 게시(1080)엔 부족


def downscale_png(raw: bytes, scale: float = PREVIEW_SCALE) -> bytes:
    """PNG를 비율 축소. 실패하면 원본을 그대로 돌려준다(뷰어가 깨지면 아하가 죽는다)."""
    try:
        img = Image.open(io.BytesIO(raw))
        w, h = img.size
        out = io.BytesIO()
        img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS).save(
            out, format="PNG", optimize=True
        )
        return out.getvalue()
    except Exception:
        return raw
