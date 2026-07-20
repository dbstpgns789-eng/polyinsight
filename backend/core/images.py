"""서빙 레이어 이미지 변환.

무료 유저에게 인라인 카드를 축소해서 준다 — "다 보이되 못 가져간다"(순수잠금)의
'못 가져간다'를 실제로 성립시키는 조각. 게이트(402)가 아니라 해상도 차등이다.
"""
from __future__ import annotations

import io

from PIL import Image

PREVIEW_MAX_WIDTH = 540  # 인스타 게시 규격(1080)의 절반 — 화면에선 읽히고 게시엔 부족


def downscale_png(raw: bytes, max_width: int = PREVIEW_MAX_WIDTH) -> bytes:
    """긴 변 기준 절대 상한으로 축소. 실패하면 원본을 그대로 돌려준다(뷰어가 깨지면 아하가 죽는다).

    ★상대 배율(scale=0.5)을 쓰면 안 된다 — 원본이 레티나 2배(2160×2700)로 렌더되므로
      절반으로 줄여도 정확히 인스타 게시 규격(1080×1350)이 나와 벽이 무의미해진다.
      렌더 배율이 바뀌어도 결과가 흔들리지 않도록 절대 상한으로 고정한다.
    """
    try:
        img = Image.open(io.BytesIO(raw))
        w, h = img.size
        if w <= max_width:
            return raw   # 이미 미리보기보다 작음 — 확대 금지, 그대로 반환
        new_h = max(1, round(h * max_width / w))
        out = io.BytesIO()
        img.resize((max_width, new_h), Image.LANCZOS).save(out, format="PNG", optimize=True)
        return out.getvalue()
    except Exception:
        return raw
