# -*- coding: utf-8 -*-
"""eval 결과 갤러리 — 여러 조건의 덱을 한 페이지에 나란히 (무료, LLM 호출 없음).

이미지는 전부 data URI로 인라인한다. 로컬 file:// + 한글 경로에서 상대·절대 경로가
깨지는 걸 원천 차단 — 파일 하나만 열면 끝.

사용:
  python -m backend.scripts.eval_gallery --out eval/runs/gallery.html \
      "구 프롬프트=baseline-oldprompt/microbead-cof" \
      "D안=exp-D-paper-as-ref/microbead-cof"
"""
from __future__ import annotations

import argparse
import base64
import io
import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_RUNS = _ROOT / "eval" / "runs"
_THUMB_W = 460          # 카드 원본 2160px → 썸네일(파일 크기·로딩 방어)


def _data_uri(png: Path) -> str:
    raw = png.read_bytes()
    try:
        from PIL import Image
        im = Image.open(io.BytesIO(raw))
        if im.width > _THUMB_W:
            h = round(im.height * _THUMB_W / im.width)
            im = im.convert("RGB").resize((_THUMB_W, h), Image.LANCZOS)
            buf = io.BytesIO()
            im.save(buf, format="JPEG", quality=88)
            return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        pass
    return "data:image/png;base64," + base64.b64encode(raw).decode()


def _judge_of(run: str, paper: str) -> dict | None:
    """해당 런의 저지 결과(있으면). baseline은 별도 파일."""
    rp = _RUNS / run / "results.json"
    if rp.exists():
        for e in json.loads(rp.read_text(encoding="utf-8")):
            if e["id"] == paper:
                return e.get("judge")
    single = _RUNS / run / f"{paper}-judge.json"
    if single.exists():
        return json.loads(single.read_text(encoding="utf-8"))
    return None


def main() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8")
        except Exception:
            pass

    ap = argparse.ArgumentParser(description="eval 결과 갤러리")
    ap.add_argument("--out", default="eval/runs/gallery.html")
    ap.add_argument("--title", default="같은 논문, 조건별 결과")
    ap.add_argument("rows", nargs="+", help='"라벨=런디렉터리/논문id" 형식')
    args = ap.parse_args()

    h = [
        "<!DOCTYPE html><meta charset='utf-8'>",
        f"<title>{args.title}</title>",
        "<style>",
        "body{background:#0d0e10;color:#e9e7e4;font-family:Pretendard,-apple-system,system-ui,sans-serif;",
        "margin:0;padding:28px 24px 60px}",
        "h1{font-size:23px;margin:0 0 6px}.sub{color:#8b9096;font-size:13px;margin-bottom:30px}",
        "section{margin-bottom:38px}",
        "h2{font-size:16px;margin:0 0 4px;font-weight:700}",
        ".meta{color:#8b9096;font-size:12.5px;margin-bottom:10px;line-height:1.65}",
        ".bad{color:#f0a35e}.good{color:#68c99a}",
        ".row{display:flex;gap:9px;flex-wrap:wrap}",
        "img{width:230px;border-radius:7px;box-shadow:0 5px 18px rgba(0,0,0,.55);display:block}",
        "figure{margin:0}figcaption{color:#6f747a;font-size:10.5px;text-align:center;margin-top:4px}",
        "</style>",
        f"<h1>{args.title}</h1>",
        "<div class=sub>이미지는 전부 인라인 — 이 파일 하나만 열면 됩니다.</div>",
    ]

    for spec in args.rows:
        label, _, path = spec.partition("=")
        run, _, paper = path.partition("/")
        d = _RUNS / run / paper
        pngs = sorted(d.glob("*.png"))
        j = _judge_of(run, paper)

        h.append("<section>")
        h.append(f"<h2>{label}</h2>")
        if j:
            defects = [k for k, v in (j.get("defects") or {}).items() if v]
            sc = j.get("scores", {})
            score_txt = " · ".join(f"{k} {v}" for k, v in sc.items())
            h.append(f"<div class=meta>저지 <b>{j.get('verdict')}</b> — {score_txt}<br>")
            if defects:
                h.append(f"<span class=bad>결함: {', '.join(defects)}</span>")
            else:
                h.append("<span class=good>결함 없음</span>")
            h.append(f"<br>{j.get('one_line','')}</div>")
        else:
            h.append(f"<div class=meta>{len(pngs)}장 · (저지 결과 없음)</div>")

        h.append("<div class=row>")
        for i, p in enumerate(pngs, 1):
            h.append(f"<figure><img src='{_data_uri(p)}'><figcaption>{i:02}</figcaption></figure>")
        h.append("</div></section>")

    out = _ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(h), encoding="utf-8")
    mb = out.stat().st_size / 1024 / 1024
    print(f"생성: {out}  ({mb:.1f}MB)")


if __name__ == "__main__":
    main()
