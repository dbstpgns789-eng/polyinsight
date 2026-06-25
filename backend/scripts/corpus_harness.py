"""코퍼스 견고성 하니스 — Mode A(무료 S1 측정).
폴더의 모든 PDF를 S1만 돌려 degrade 텔레메트리를 input_profile로 교차집계한다.
프로세스 격리 Pool(maxtasksperchild)로 fitz C-메모리 OOM 회피(spec §3).
오프라인 개발 도구 — 웹/프로덕션과 무관."""
from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter, defaultdict
from multiprocessing import Pool
from pathlib import Path

from backend.agents.s1_extractor import s1_agent
from backend.core.models import S1Input
from backend.scripts.input_profile import build_input_profile

_PDF_GLOB = "*.pdf"


def profile_one(pdf_path: str) -> dict:
    """논문 1편 → 직렬화 가능 row(Pool 전송 위해 enum 아닌 str). 워커 진입점."""
    pdf_bytes = Path(pdf_path).read_bytes()
    s1 = asyncio.run(s1_agent.execute(S1Input(job_id=pdf_path, pdf_bytes=pdf_bytes)))
    profile = build_input_profile(pdf_bytes, s1.metadata.doi)
    return {
        "file": Path(pdf_path).name,
        "codes": [e.code.value for e in s1.degrade_events],
        "columns": profile["columns"],
        "journal_family": profile["journal_family"],
    }


def aggregate(rows: list[dict]) -> dict:
    """rows → code별 카운트 + (degrade code × input_profile) 교차표."""
    by_code: Counter = Counter()
    crosstab: dict[str, Counter] = defaultdict(Counter)
    files_by_code: dict[str, list[str]] = defaultdict(list)
    clean = 0
    for r in rows:
        if not r["codes"]:
            clean += 1
        for code in r["codes"]:
            by_code[code] += 1
            crosstab[code][(str(r["columns"]), r["journal_family"])] += 1
            files_by_code[code].append(r["file"])
    return {
        "total": len(rows),
        "clean": clean,
        "by_code": dict(by_code),
        "crosstab": {k: dict(v) for k, v in crosstab.items()},
        "files_by_code": dict(files_by_code),
    }


def format_report(agg: dict) -> str:
    lines = [f"=== S1 견고성 리포트 ({agg['total']}편) ==="]
    parts = [f"{c} {n}" for c, n in sorted(agg["by_code"].items())]
    lines.append("code별: " + " / ".join(parts) + f" / 정상 {agg['clean']}")
    for code, cells in agg["crosstab"].items():
        lines.append(f"\n{code} × input_profile (← 핀셋 대상):")
        for (cols, journal), n in sorted(cells.items(), key=lambda kv: -kv[1]):
            lines.append(f"  columns={cols} · journal={journal} : {n}편")
        sample = agg["files_by_code"][code][:5]
        lines.append("  예: " + ", ".join(sample))
    return "\n".join(lines)


def _profile_safe(pdf_path: str) -> dict:
    """profile_one을 에러 격리로 감쌈 — 한 편이 깨져도 배치 전체를 죽이지 않는다."""
    try:
        return profile_one(pdf_path)
    except Exception as exc:
        return {"file": Path(pdf_path).name, "codes": ["harness_error"],
                "columns": 0, "journal_family": f"ERROR:{type(exc).__name__}"}


def run_mode_a(corpus_dir: str, workers: int = 4, maxtasks: int = 10,
               progress: bool = False) -> list[dict]:
    """폴더의 모든 PDF를 S1 측정. workers<=1=순차(Windows multiprocessing 우회),
    그 외=프로세스 격리 Pool(maxtasksperchild로 fitz OOM 회피). 진행상황 stderr."""
    paths = [str(p) for p in sorted(Path(corpus_dir).glob(_PDF_GLOB))]
    if not paths:
        return []
    rows: list[dict] = []
    total = len(paths)
    if workers <= 1:
        for i, p in enumerate(paths, 1):
            rows.append(_profile_safe(p))
            if progress:
                print(f"  [{i}/{total}] {Path(p).name}", file=sys.stderr, flush=True)
    else:
        with Pool(processes=workers, maxtasksperchild=maxtasks) as pool:
            for i, row in enumerate(pool.imap_unordered(_profile_safe, paths), 1):
                rows.append(row)
                if progress:
                    print(f"  [{i}/{total}] {row['file']}", file=sys.stderr, flush=True)
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="코퍼스 견고성 하니스")
    ap.add_argument("--stage", choices=["s1"], default="s1",
                    help="s1=무료 whack-a-mole(Mode A). full(Mode B)은 Plan 2.")
    ap.add_argument("--corpus", required=True, help="PDF 폴더 경로")
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    for stream in (sys.stdout, sys.stderr):   # Windows cp949 콘솔 유니코드 방지
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:
            pass

    if args.stage != "s1":
        print("Mode B(full)는 유료 — Plan 2에서 구현. 지금은 --stage s1만.", file=sys.stderr)
        sys.exit(2)

    rows = run_mode_a(args.corpus, workers=args.workers, progress=True)
    print(format_report(aggregate(rows)))


if __name__ == "__main__":
    main()
