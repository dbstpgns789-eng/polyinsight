# 스펙 — 옵트인 폴리시 루프 (S6.5 아트디렉션 리뷰)

> 2026-07-04. 목표: 클로드 디자인급 마감을 **사용자가 원할 때만·비용 상한 안에서** 근접.
> 원칙: **손은 싸게(생성=Sonnet), 눈은 비싸게(비평=Opus 1회), 항상-켜짐이 아니라 옵트인.**
> 근거: 블라인드 로그가 증명한 격차 = 단발 저작 vs 렌더→보고→비평→수정 루프. 상세는
> `design_reference/claude-design/blind_refs/README.md` + 세션 진단.

## 1. 무엇이 새로 필요한가 (딱 하나)

**비전 입력.** 현재 `llm_client.call`은 텍스트 전용
(`messages=[{"role":"user","content":user_prompt}]`). 비평자가 카드를 **보려면**
이미지 블록을 넣어야 한다. → `call(..., images: list[bytes] | None = None)` 추가:
```
content = [{"type":"image","source":{"type":"base64","media_type":"image/png","data":b64}} for png in images]
content.append({"type":"text","text": user_prompt})
```
이것이 유일한 신규 원시연산. 나머지는 전부 재사용.

## 2. 재사용하는 기존 부품

| 부품 | 위치 | 폴리시에서의 역할 |
|---|---|---|
| `render_deck(html) -> (images, warns)` | `agents/deck/deck_renderer.py` | 카드별 PNG 생성(비평자 입력) + 렌더 경고(코드 게이트) |
| `persist_edited_deck(job_id, html)` | `agents/deck/pipeline.py:45` | **수정 HTML 적용 = 재검증→재렌더→저장** 통째로 재사용 |
| `verify_deck(html, paper_text)` | `core/fidelity.py` | 수정 후 수치 환각 재검증(해자) |
| `authored_deck.paper_text` | DB | 재검증용 원문 이미 보관됨 |
| `call(model=...)` 오버라이드 | `core/llm_client.py:87` | 비평=Opus / 수정=Sonnet 라우팅 |
| usage 집계 | `llm_client._record_usage` | 모델별 토큰·비용 로깅 |

## 3. 루프 (유계, 기본 1라운드)

이미 저작·렌더된 덱 위에서 동작. **기본 파이프라인 밖, 사용자 트리거.**

```
POST /deck/{job_id}/polish
  │
  ▼
[0] 코드 게이트 (무료)
     render 경고(넘침/빈약/0카드) 수집 → 비평자에 힌트로 전달
  │
  ▼
[1] 눈 — 비평자 1회 (Opus, 비전)                     ★유일한 프리미엄 지출
     입력: 카드 PNG N장 + fidelity 리포트 + 루브릭(+선택: 레퍼런스 덱을 기준선)
     출력(구조화 JSON): 카드별 {card, severity, flaw, fix} + 전역판정 + 수정대상 목록
     루브릭: 위계·균형·여백·넘침·팔레트 일관·초점 명료·차트 정확·타이포 위계
  │
  ▼
[2] 판정 (무료)
     "material 이슈 없음" → 정지 (여기서 끝, 수정 지출 0)
     아니면 severity ≥ 임계 카드만 선택
  │
  ▼
[3] 손 — 수정자 1회 (Sonnet)                          싼 지출
     입력: 현재 HTML 전체 + [지목된 카드]의 구체 지시
     제약: "이 수정만 적용, 나머지 불변, 모든 수치 원문 그대로"
     출력: 수정된 HTML 전문 (카드별 N회 아님 — 1회로 전체 재기술)
  │
  ▼
[4] 재검증 + 재렌더 = persist_edited_deck 재사용
     verify_deck로 수치 환각 검사 → unverified 늘면 경고/롤백 제안
     render_deck → 카드 PNG 저장
  │
  ▼
[5] 루프 제어
     MAX_POLISH_ROUNDS=1 기본(첫 수정에 이득 70~85% 집중, 이후 체감 급감)
     before/after 보존 → 사용자 승인 or 되돌리기 (헌법: 최종 판단은 사용자)
```

## 4. 비용 (상한, 예측 가능)

**폴리시 1회 = Opus 비전 1콜 + Sonnet 1콜.** 끝.

- 비평(Opus): 입력 = 카드 PNG N장(장당 ~1~1.5k토큰) + 루브릭, 출력 = 작은 구조화 JSON.
- 수정(Sonnet): 입력 = HTML(~15k) + 비평, 출력 = 수정 HTML(~15k).
- 렌더 = 로컬 Playwright(무료).

핵심 절약: **카드별 콜 금지.** 비평자가 7장을 *한 번에* 보고, 수정자가 *한 번에* 재기술.
카드별로 돌리면 7배 → 안 함. "material 이슈 없음"이면 수정 콜 자체를 스킵.

## 5. 가드레일 (정직성)

- 수정 후 **fidelity 재검증 필수** — 수정 콜이 수치를 환각할 수 있다. unverified 증가 시 크게 표면화 + 되돌리기 제공.
- 라운드 상한. 사용자가 최종 승인. before/after 보존(되돌리기 불변식, Phase 3e 계보).
- 비평 콜 실패(auth/rate/timeout) → 원본 무손상 반환, 덱 상태·과금 없음.
- 폴리시는 **기본 파이프라인에 안 들어감** — 배치 생성 비용 0 유지.

## 6. UI (옵트인 트리거)

`/deck/{id}` 에디터에 버튼: **"이 덱 다듬기 · 아트디렉션 리뷰"**
- 비용 고지: "강한 모델이 1회 검토 → 1회 수정".
- 진행: 검토 중 → 수정 중 → 렌더 중.
- 결과: before/after 비교 → 사용자 **적용 / 되돌리기**.

## 7. 설정 노브

```
POLISH_CRITIC_MODEL   = <opus-class>      # 눈
POLISH_REVISER_MODEL  = claude-sonnet-4-6 # 손 (저작과 동일)
MAX_POLISH_ROUNDS     = 1
POLISH_SEVERITY_MIN   = "medium"          # 이 미만은 수정 안 함
POLISH_USE_REFERENCE  = true              # 저장된 비타민 덱을 품질 기준선으로
```

## 8. 단계 (구현 시)

- **S0** — `llm_client` 비전 입력 + 던지기 하네스: Opus가 카드 PNG 1장 비평 가능 증명 (싼 테스트 1회).
- **S1** — 비평자(프롬프트+구조화 스키마)만. 기존 덱에 돌려 **비평 품질만 검사**, 수정 없음 (Opus 1회 평가).
- **S2** — 수정자 + 재검증 + 재렌더 (persist_edited_deck 재사용).
- **S3** — 엔드포인트 + 루프 제어 + before/after 영속화.
- **S4** — 웹 버튼 + before/after UI.

각 S 사이 실호출은 **사전 허락**(헌법: 비용 규칙). S0/S1은 mock/단발로 최소화.
