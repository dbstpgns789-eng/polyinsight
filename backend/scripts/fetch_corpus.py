"""분야별 고인용 오픈액세스(OA) 논문 PDF 합법 다운로드.

OpenAlex(인용수 정렬) → best_oa_location의 **합법 OA PDF만** 받는다.
Sci-Hub/페이월 우회 안 함. 잠긴 논문(OA 없음)은 건너뛴다 — OA가 희박한 도메인
(인문·한국 정책)은 4편을 다 못 채울 수 있고, 그 갭은 정직하게 리포트한다.

사용:
  python -m backend.scripts.fetch_corpus --out <dir> --per-field 4
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

import httpx

OPENALEX = "https://api.openalex.org/works"
MAILTO = "polyinsight-dev@example.com"   # OpenAlex polite pool

# 분야 키 → (OpenAlex concept id, 라벨, 언어필터 or None)
# 1 AI/CS · 2 보안/핀테크 · 3 생명·화학·의학(2단 지뢰밭) · 4 인문·사회 · 5 공공정책(국문)
FIELDS: dict[str, tuple[str, str, str | None]] = {
    "ai_cs":         ("C154945302", "Artificial intelligence", None),
    "security_fin":  ("C38652104",  "Computer security",       None),
    "life_chem_med": ("C86803240",  "Biology",                 None),
    "humanities":    ("C144024400", "Sociology",               None),
    "policy_kr":     ("C3116431",   "Public administration",   "ko"),
}

_HEADERS = {"User-Agent": f"polyinsight-corpus-fetcher (mailto:{MAILTO})"}


def _sanitize(title: str, limit: int = 60) -> str:
    t = re.sub(r"[^0-9A-Za-z가-힣 ]", "", title or "untitled").strip()
    t = re.sub(r"\s+", "_", t)
    return (t[:limit] or "untitled")


def _candidates(client: httpx.Client, concept_id: str, language: str | None, n: int) -> list[dict]:
    """인용수 내림차순 OA 후보. pdf_url 있는 것만."""
    filt = f"concepts.id:{concept_id},is_oa:true,has_fulltext:true"
    if language:
        filt += f",language:{language}"
    r = client.get(OPENALEX, params={
        "filter": filt,
        "sort": "cited_by_count:desc",
        "per_page": str(n),
        "mailto": MAILTO,
        "select": "title,cited_by_count,doi,best_oa_location,primary_location,open_access",
    }, timeout=30)
    r.raise_for_status()
    out = []
    for w in r.json().get("results", []):
        url = None
        for loc_key in ("best_oa_location", "primary_location"):
            loc = w.get(loc_key) or {}
            if loc.get("pdf_url"):
                url = loc["pdf_url"]
                break
        if not url:
            oa = w.get("open_access") or {}
            url = oa.get("oa_url")   # 랜딩일 수 있음 — 다운로드 시 PDF 검증
        if url:
            out.append({"title": w.get("title") or "untitled",
                        "cites": w.get("cited_by_count", 0), "url": url})
    return out


def _download_pdf(client: httpx.Client, url: str, dest: Path) -> bool:
    """PDF면 저장하고 True. HTML/404/비PDF면 False(매직바이트 검증)."""
    try:
        r = client.get(url, timeout=60, follow_redirects=True, headers=_HEADERS)
        if r.status_code != 200:
            return False
        body = r.content
        if not body[:5].startswith(b"%PDF"):   # 랜딩페이지/HTML 거름
            return False
        if len(body) < 10_000:                  # 1KB대 = 가짜/에러본
            return False
        dest.write_bytes(body)
        return True
    except Exception:
        return False


def fetch_field(client: httpx.Client, key: str, want: int, out_dir: Path) -> list[str]:
    concept_id, label, lang = FIELDS[key]
    saved: list[str] = []
    # 후보를 넉넉히(want*8) 받아서 성공할 때까지 — OA여도 pdf_url이 404/HTML인 경우 많음.
    cands = _candidates(client, concept_id, lang, max(want * 8, 24))
    print(f"\n[{key}] {label}{' (ko)' if lang else ''} — 후보 {len(cands)}편, {want}편 목표")
    for c in cands:
        if len(saved) >= want:
            break
        fname = f"{key}_{c['cites']}_{_sanitize(c['title'])}.pdf"
        dest = out_dir / fname
        if dest.exists():
            continue
        ok = _download_pdf(client, c["url"], dest)
        mark = "✓" if ok else "✗"
        print(f"  {mark} {c['cites']:>6} cites | {c['title'][:55]}")
        if ok:
            saved.append(fname)
        time.sleep(0.3)
    return saved


def main() -> None:
    ap = argparse.ArgumentParser(description="고인용 OA 논문 합법 페처(OpenAlex)")
    ap.add_argument("--out", required=True, help="저장 폴더(없으면 생성)")
    ap.add_argument("--per-field", type=int, default=4)
    ap.add_argument("--fields", nargs="*", default=list(FIELDS.keys()),
                    help=f"기본 전체: {list(FIELDS.keys())}")
    args = ap.parse_args()

    # Windows 콘솔(cp949)이 em-dash·✓ 등 유니코드를 못 찍어 죽는 것 방지.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    summary: dict[str, int] = {}
    with httpx.Client(headers=_HEADERS) as client:
        for key in args.fields:
            if key not in FIELDS:
                print(f"알 수 없는 분야: {key}", file=sys.stderr)
                continue
            saved = fetch_field(client, key, args.per_field, out_dir)
            summary[key] = len(saved)

    print("\n=== 결과 ===")
    total = 0
    for key in args.fields:
        got = summary.get(key, 0)
        total += got
        gap = "" if got >= args.per_field else f"  ← OA 희박, {args.per_field - got}편 부족(정직 보고)"
        print(f"  {key:<14}: {got}/{args.per_field}{gap}")
    print(f"  합계: {total}편 → {out_dir}")


if __name__ == "__main__":
    main()
