# AI 디자이너 "편집 스펙" 포맷 + 적용 (스펙)

> 2026-07-24 · 정본 정의 `docs/contracts/25_ai_designer.md` 구현 · 상태: **적대적 검증 대기**
> 목표: LLM이 덱 전체 HTML을 재출력하던 구조(느림 3~5분·비쌈·타임아웃·측정불가)를,
> LLM이 **최소 편집 스펙(ops)만** 뱉고 코드가 결정적으로 적용하는 구조로 바꾼다.

## 1. 결정 (확정)
- 적용 위치 = **A. 서버 적용** (propose가 eid 붙은 html 받아 서버가 ops 적용 → {html, verify} 반환). 기존 propose 계약 유지, 라운드트립 1번.
- op 종류 v1 = **style · text** 둘. 이동·리사이즈·삭제·순서 = 직접조작 편집기(§25.6, AI 아님).
- 스타일 표현 = **구체 CSS 속성:값** (LLM이 디자이너라 CSS를 안다. 코드는 그대로 적용).

## 2. 편집 스펙 포맷 (LLM 출력)

```json
{
  "summary": "제목에 은은한 그림자를 넣어 가독성을 높였어요",
  "ops": [
    { "eid": "e3abc", "op": "style", "style": { "text-shadow": "0 1px 3px rgba(0,0,0,.35)" } },
    { "eid": "e5def", "op": "text",  "text": "더 짧은 제목" }
  ]
}
```
- `eid`: 대상 요소(레이어 패널이 스탬프한 `data-eid`).
- `op`: `"style"`(CSS 속성 맵) | `"text"`(내부 텍스트 교체, 자식 요소 없는 텍스트 리프만).
- `summary`: 사용자에게 보여줄 한 줄(propose 카드 제목). 필수.
- ops 빈 배열 = "바꿀 것 없음"(지시가 모호/불가) → summary로 설명, 무변경.

## 3. 데이터 흐름 (propose)

```
프론트 → POST /deck/{id}/nlpatch/propose
  body: { instruction, html(eid 유지), target?, inventory }
  ↓
백엔드: LLM( inventory + instruction + target )  ← ★LLM은 html을 안 본다. 인벤토리(작음)만.
  → { summary, ops }
  ↓
백엔드: apply_ops(html, ops)  ← 결정적. [data-eid]로 찾아 인라인 style 병합 / text 교체.
  → modified_html
  ↓
백엔드: compute_verify(modified_html)   ← 해자. text op가 원문 밖 수치 넣으면 "확인 필요".
  ↓
프론트 ← { html: modified_html, verify, summary }   ← 기존 계약 + summary. 제안 표시 → 사용자 확인 → save.
```

★핵심: **LLM 입력=인벤토리(수백~수천 토큰), 출력=ops(수백 토큰).** html 재출력 0 → 수초·저렴·측정가능(deck_edit 이벤트에 실토큰 기록, 계측은 이미 있음).

## 4. 요소 인벤토리 (프론트 생성 → LLM 입력)

프론트(editorAgent)가 현재 카드(또는 전체)의 편집가능 요소를 수집해 전달. `collectLayers`에 핵심 스타일만 얹은 것:
```json
[ { "eid": "e3abc", "kind": "text", "label": "제목: 코팅 하나로 32.7배...",
    "styles": { "color": "#1a1a1a", "fontSize": "80px", "fontWeight": "700",
                "background": "", "textShadow": "none", "textAlign": "left" } }, ... ]
```
- `kind`: text|image|graphic|shape (collectLayers 그대로).
- `styles`: getComputedStyle에서 뽑은 편집 관련 핵심만(색·크기·굵기·배경·그림자·정렬·자간·행간). LLM이 상대 변경("더 어둡게","더 크게") 판단에 씀.
- 전체 vs 현재카드: v1 = **현재 보이는 카드**(편집 모드는 한 장씩 페이징). 전체 대상 지시는 v1.1.

## 5. 서버 적용 `apply_ops(html, ops)`

- 파서: lxml/BeautifulSoup로 html 파싱.
- `style` op: `[data-eid=X]` 찾아 기존 인라인 style에 **병합**(같은 속성이면 덮어씀). CSS 속성명은 kebab-case 그대로.
- `text` op: `[data-eid=X]`가 **텍스트 리프(자식 요소 없음)**면 내부 텍스트 교체. 자식 있으면 무시(안전) + 경고.
- eid 없거나 카드 밖 요소 = 무시 + 경고(계약 위반 방지).
- 반환: 수정된 html 문자열.

## 6. eid 유지 (serialize 충돌 해소)

지금 `serialize`(editorAgent)는 `data-eid`를 제거(발행 위생, 2026-07-23). 그런데 propose는 eid가 있어야 서버가 타겟함.
- **해법**: propose 전용 html은 eid 유지. `GET_HTML`에 `keepEids` 옵션 추가(또는 `GET_HTML_RAW`). propose만 keepEids, **최종 save(patchDeck)는 기존 strip serialize 그대로** → 발행 html은 여전히 clean.
- 반환된 modified_html도 eid 유지 → 프론트 재마운트(편집기 내부라 eid 무해) → 사용자 확인 후 save에서 strip.

## 7. 충실성·안전 (해자 유지)

- `style` op: 내용 불변 → 안전. 단 파괴적 속성(position/display/width/height 등 레이아웃 붕괴)은 **화이트리스트 밖이면 거부**(색·서체·그림자·배경·간격·정렬·투명도·모서리만 허용). 레이아웃은 직접조작 편집기 담당.
- `text` op: `compute_verify`가 결과 대조 → 원문 밖 수치는 "확인 필요"(기존 해자 그대로). 사용자가 제안 확인 단계에서 봄.
- 실패(LLM 에러·빈 ops·422)면 **무과금**(§25.7-4). consume_credits는 성공·적용 후에만.

## 8. 변경 파일

- `backend/agents/deck/nl_patch.py` — 재작성. 프롬프트가 html 재출력이 아니라 **ops JSON** 요구. 입력=인벤토리+지시. `apply_ops` 신규(또는 별 모듈).
- `backend/routers/deck.py` — nlpatch/propose·nlpatch: body에 `inventory` 수신, apply_ops → verify. (usage 계측·consume_credits 순서 유지, 성공 후 과금.)
- 프롬프트 파일 — EDIT_SYSTEM을 ops 계약으로. few-shot(그림자·색·텍스트 교체 예).
- `web/src/components/deck/editorAgent.ts` — 인벤토리 생성(collectLayers+styles) 방출 or GET, `GET_HTML` keepEids 옵션.
- `web/src/components/deck/DeckEditor.tsx` · `web/src/lib/api.ts` — propose 요청에 inventory·keepEids html 배선. 응답 summary 표시.
- axios `nlProposeDeck` timeout: 이제 수초라 180s 과함 → 30~60s로 되돌려도 됨(빠름 검증 후).

## 9. 스코프

- **In(v1)**: 현재 카드의 style·text 자연어 편집, 서버 적용, verify, propose→확인, 실패 무과금, 실토큰 측정.
- **Out(다음)**: 전체 덱 대상 지시(v1.1), 구조 변경(이동·삭제=편집기), 전체 재작업 async 잡(무거운 미감 오버홀), 프리셋 버튼의 LLM화(프리셋은 결정적 유지).

## 10. 리스크 / 적대적 검증 대상

1. **인벤토리가 충분한가** — LLM이 "이 제목" 같은 지시를 eid로 정확히 매핑하려면 label·styles가 충분해야. 부족하면 오타겟.
2. **text op 텍스트 리프 경계** — 자식 있는 요소(h1 안 span)의 text 교체는 위험. 리프만 허용 규칙이 실덱에서 맞나.
3. **style 화이트리스트** — 너무 좁으면 "고급스럽게"가 못 표현, 너무 넓으면 레이아웃 붕괴. 경계.
4. **전체 톤 지시** — "전체 차분히"가 현재카드만 도는 v1 한계. 사용자 기대와 갭.
5. **eid 유지 html 왕복** — modified_html에 eid 남아 프론트 재마운트·save strip이 정말 깨끗한가.
6. **LLM ops JSON 신뢰성** — 잘못된 eid·깨진 JSON·환각 속성. 파싱 실패 시 graceful(무변경+무과금).
7. **정의 부합** — 이 설계가 §25(온디맨드 디자이너·최소 출력·자연어 지능) 의도와 맞나.

## 11. 적대적 검증 반영 (착수 전 확정) — 2026-07-24 리뷰 + 실지출 확증

적대적 검증기가 코드 대조로 10개 구멍을 찾았고, 그중 핵심을 실지출(콘솔: 실패 편집 3회 각
출력 15.5k토큰=덱 전체 재출력, $0.98 손실)이 확증했다. 착수 전 다음을 확정한다.

1. **과금 = 적용 카운트.** `apply_ops` → `(html, applied_n)`. `applied_n == 0`이면 consume_credits
   스킵 + "적용할 게 없었어요"로 표면화. (검증기 #1: 현 게이트 `data-screen-label not in html`은
   ops 경로에서 절대 안 걸려 §25.7-4 자동 위반. 실패도 과금되던 게 이거.)
2. **인벤토리 확장.** 원자 요소(collectLayers) + **카드 프레임·배경/컨테이너 div** 포함, styles는
   `getComputedStyle`(인라인만 아님). 그래야 "표지 배경색" 같은 §25.4 대표 시나리오가 타겟됨.
   (검증기 #2)
3. **text op 경계 통일.** v1은 인라인 자식(span/b/i/em/br)만 있는 텍스트까지 허용, innerText 교체
   (인라인 강조 소실은 감수, 프리뷰서 확인). 블록 자식 있으면 거부+무시(무과금). 인벤토리
   `kind:text` 정의와 apply 규칙을 하나로. (검증기 #3: 수치 강조 span 박은 제목이 흔함.)
4. **발행 위생 + 프리즈 회피 (제일 까다로운 매듭).**
   (a) `patch_deck` 서버 경계에서 `data-eid` strip(2026-07-23 fence-strip처럼) → commit이 serialize를
       우회해도 발행 html clean. (검증기 #5)
   (b) ★편집을 **비프리즈 authored html에 적용.** 편집모드 라이브 캔버스는 freezeCard가 절대배치+
       고정 박스로 못박아, font-size op이 박스에서 클립된다(검증기 #4). editorAgent가 propose용으로
       **eid 스탬프된 비프리즈 html**을 제공(freeze 안 한 구조). 크기·여백 변경이 박스에 안 갇힘 →
       §25.4(크기·여백 동시) 표현 가능.
5. **style 화이트리스트 = §25.4와 화해.** 색·서체·그림자·배경·정렬·자간·행간·투명도·모서리 +
   **크기(font-size)·여백(margin/padding)** 허용(비프리즈 적용 전제). position/display/transform/float
   등 레이아웃 구조는 거부(직접조작 편집기 담당, §25.6). (검증기 #4)
6. **★async + 결과 영속 (오늘 실지출 교훈, 핵심).** 편집을 생성처럼 **백그라운드 잡**으로. 클라
   타임아웃에 완성된 유료 결과가 버려지던 것(오늘 $0.98 완주 후 폐기)을 근본 차단 = **완성된 LLM
   작업은 절대 버리지 않는다.** §1 결정에 async 추가. 스펙(작은 출력)으로 대부분은 수초라 동기여도
   되지만, 안전판으로 완주 결과는 DB에 영속.
7. **파서 충실성 + graceful.** apply_ops는 대상 요소만 외과적 수정(전체 재직렬화 최소화, 인라인
   SVG·DOCTYPE 보존). LLM JSON 파싱 실패 → `{summary:"이해하지 못했어요", ops:[]}`로 강등(#1의
   무변경·무과금과 합류). DEV_MOCK_LLM도 ops 계약으로. (검증기 #6·#9)
8. **/nlpatch(비-propose) 은퇴.** DB html엔 eid가 없어(저장 시 strip) ops 타겟 불가 → propose를 주
   경로로 확정, 직접 nlpatch 은퇴. (검증기 #8: 폐기도 docs 먼저.)
9. **스타일 프리뷰.** propose 후 pending.html(전체 덱)을 읽기전용 iframe으로 렌더해 style 변화를
   눈으로 보게(현재는 text diff만 → style op은 무프리뷰 승인). (검증기 #10)

**미해결(구현 중 판단):** 4-(b) 비프리즈 html 조달 메커니즘의 정확한 형태(freeze 되돌리기 vs raw
직렬화 vs 저장본+eid 재매핑) — 구현 착수 시 실덱으로 결정.
