# -*- coding: utf-8 -*-
"""참고문헌 제거 — 결론을 버리지 않기 위해.

실측(2026-07-13, chitosan 논문 81,518자):
  Results     58,027자 (71%)   겨우 들어감
  ──── 60,000자에서 절단 ────
  Conclusion  60,175자 (74%)   ✂ 잘림!!  ← 논문의 핵심 메시지
  References  63,697자 (78%)   ✂ 잘림    ← 이건 버려도 됨

**175자 차이로 결론을 버리고 있었다.** 그리고 참고문헌이 원문의 22%를 차지한다 —
쓸모없는 그것 때문에 결론을 못 봤다. 참고문헌을 먼저 잘라내면 비용 증가 없이 결론이 산다.
"""
from backend.agents.deck.source_trim import trim_source


def test_cuts_references_section():
    text = ("## 1. Introduction\n본문...\n"
            "## 4. Conclusion\n이 연구는 중요하다.\n"
            "## References\n[1] Kim et al. 2024...\n[2] Lee et al. 2023...")
    out, dropped = trim_source(text, limit=100_000)
    assert "Conclusion" in out and "이 연구는 중요하다" in out
    assert "Kim et al" not in out
    assert dropped > 0


def test_cuts_acknowledgements_too():
    text = ("본문\n## Conclusion\n결론이다\n"
            "## Acknowledgements\n연구비 지원...\n## References\n[1] ...")
    out, _ = trim_source(text, limit=100_000)
    assert "결론이다" in out
    assert "연구비 지원" not in out


def test_ignores_inline_mention_of_references():
    """본문 중 'references' 언급을 헤딩으로 오인해 논문을 통째로 날리면 안 된다."""
    text = ("## Results\n"
            "Previous references suggest that... 이 문장은 본문이다.\n" * 20 +
            "## Conclusion\n결론\n## References\n[1] Kim")
    out, _ = trim_source(text, limit=100_000)
    assert "결론" in out
    assert "[1] Kim" not in out
    assert len(out) > 500          # 본문이 살아있다


def test_no_references_section_is_noop():
    text = "## Introduction\n본문만 있는 문서"
    out, dropped = trim_source(text, limit=100_000)
    assert out == text
    assert dropped == 0


def test_long_paper_keeps_conclusion_not_intro():
    """★10만 자 논문(리뷰·학위논문): 참고문헌을 빼도 상한을 넘으면 **중간을 생략**한다.

    앞에서부터 자르면 가장 중요한 결론부터 버린다(실측: chitosan에서 175자 차이로 결론 유실).
    논문의 중요도는 균등하지 않다 — 앞(Abstract·Intro)과 뒤(Results·Conclusion)를 지키고
    중간(Methods 상세)을 버린다.
    """
    body = (
        "ABSTRACT 이 연구는 셀룰로오스 구슬을 만든다.\n" + "서론 내용. " * 500 +
        "METHODS 상세한 실험 조건. " * 8000 +                       # 아주 긴 중간부
        "RESULTS 강도가 238 MPa로 올랐다.\n" + "결과 논의. " * 500 +
        "CONCLUSION 플라스틱을 대체할 수 있다.\n"
    )
    text = body + "\n## References\n" + "[1] Kim, S. et al. Nature, 2024. doi:10.1/x\n" * 50

    out, dropped = trim_source(text, limit=30_000)
    assert len(out) <= 30_000
    assert "ABSTRACT" in out, "앞머리(무엇을 왜 했는가)가 살아야 한다"
    assert "CONCLUSION 플라스틱을 대체할 수 있다" in out, "★결론이 살아야 한다"
    assert "238 MPa" in out, "★핵심 수치가 살아야 한다"
    assert "중략" in out, "생략 사실을 표시해야 한다"
    assert "Kim, S." not in out, "참고문헌은 버린다"


def test_short_paper_untouched_by_middle_ellipsis():
    """상한 안에 들어오면 중간 생략을 하지 않는다."""
    text = "짧은 논문 본문. " * 100
    out, _ = trim_source(text, limit=100_000)
    assert "중략" not in out
    assert out == text


def test_korean_references_heading():
    text = "본문\n## 결론\n중요\n## 참고문헌\n[1] 김철수 2024"
    out, _ = trim_source(text, limit=100_000)
    assert "중요" in out
    assert "김철수" not in out


# ── 폴백: 헤딩 단어에 의존하지 않는다 (언어·형식 무관) ──────────────────

def _bib_lines(n: int) -> str:
    """헤딩 없는 참고문헌 목록 — arXiv preprint 등에서 흔하다."""
    return "\n".join(
        f"[{i}] Vaswani, A., Shazeer, N. Attention is all you need. NeurIPS, vol. 30, pp. 5998-6008, 2017. doi:10.5555/{i}"
        for i in range(1, n + 1)
    )


def test_fallback_finds_references_without_heading():
    """★헤딩이 없어도 잡는다 — 참고문헌의 본질은 단어가 아니라 서지 마커의 밀도다.

    (독일어 논문·중국어 논문·헤딩 없는 preprint에서 정규식은 무력하다.)
    """
    body = "이것은 본문이다. 실험 결과 강도가 크게 올랐다. " * 200      # ~8,000자
    text = body + "\n" + _bib_lines(60)                                # 헤딩 없는 참고문헌
    out, dropped = trim_source(text, limit=200_000)
    assert dropped > 2000, "헤딩 없는 참고문헌을 못 잘랐다"
    assert "Vaswani" not in out
    assert "실험 결과" in out


def test_fallback_does_not_eat_body():
    """★안전장치: 오탐으로 본문을 날리면 안 된다. 본문 30% 아래로는 절대 안 자른다."""
    text = "본문에도 2024년 연구(Kim, S. et al.)가 인용된다. " * 300    # 서지 마커가 본문에 산재
    out, dropped = trim_source(text, limit=200_000)
    assert len(out) >= len(text) * 0.3


def test_no_references_at_all_is_safe():
    """참고문헌이 아예 없는 문서(강의자료·보고서)는 건드리지 않는다."""
    text = "슬라이드 1\n백업과 복구\n슬라이드 2\n트랜잭션 로그\n" * 100
    out, dropped = trim_source(text, limit=200_000)
    assert out == text
    assert dropped == 0
