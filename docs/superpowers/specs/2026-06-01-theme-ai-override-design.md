# Theme AI Recommendation + User Override

**Date:** 2026-06-01  
**Status:** Approved

---

## Problem

`CardTheme(primary, dark)`는 모델에 이미 정의되어 있으나:
- `CardEditorData`에 저장되지 않아 DB에 퍼시스트되지 않음
- 프리뷰 엔드포인트가 theme 없이 렌더링 → 항상 기본 파란색
- 업로드/내보내기 모두 `CardTheme()` 하드코딩
- 사용자가 테마를 바꿀 UI 없음

## Decision

S6 LLM 호출(기존 1회) 응답 JSON에 `recommended_theme` 필드를 추가해 AI 추천을 얻는다.  
사용자는 DesignPanel(우측 패널)에서 6개 프리셋 중 오버라이드 가능하다.  
선택된 테마는 `CardEditorData.theme`으로 저장되며 프리뷰·내보내기에 즉시 반영된다.

## 6개 프리셋 테마

| key | primary | dark | 대표 분야 |
|---|---|---|---|
| `tech_blue` | `#2563EB` | `#1A4C96` | AI, ML, computer, network |
| `forest_green` | `#16A34A` | `#166534` | bio, chemistry, polymer, cellulose |
| `sunset_orange` | `#EA580C` | `#9A3412` | energy, battery, material, mechanical |
| `royal_violet` | `#7C3AED` | `#4C1D95` | medical, clinical, health, drug |
| `golden_yellow` | `#D97706` | `#92400E` | economy, policy, social, market |
| `slate` | `#475569` | `#1E293B` | 기본/기타 |

## AI 추천 방식

S6 LLM 프롬프트 끝에 다음 지시 추가 (추가 API 호출 0):

```
마지막으로, 이 논문의 연구 분야와 분위기에 가장 잘 맞는 테마를 선택하세요.
선택지: tech_blue / forest_green / sunset_orange / royal_violet / golden_yellow / slate
응답 JSON에 "recommended_theme": "<선택값>" 필드를 포함하세요.
```

S6 파싱 후 `CardEditorData.theme`을 해당 프리셋으로 설정.  
파싱 실패 시 `tech_blue` fallback.

## 데이터 흐름

```
Upload
  → S6 LLM (1회, Haiku 4.5)
  → recommended_theme 파싱
  → CardEditorData.theme = PRESETS[recommended_theme]
  → DB 저장

에디터 열기
  → GET /api/cards/{job_id} → cardData.theme 포함
  → DesignPanel: 현재 테마 하이라이트 + "AI 추천" 배지

사용자 테마 변경
  → localData.theme 업데이트
  → debouncedSave → PATCH /api/cards/{job_id}/data
  → previewKey++ → iframe 재요청
  → GET /api/cards/{job_id}/preview/{card_num}
      → card_data.theme → render_slot_html(slot, card_data, theme)
      → --theme-primary / --theme-dark CSS 변수 주입

내보내기
  → card_data.theme 사용 (하드코딩 CardTheme() 제거)
```

## 변경 범위

| 파일 | 변경 |
|---|---|
| `backend/core/models.py` | `CardEditorData`에 `theme: CardTheme` 필드 추가 |
| `backend/agents/s6_agent.py` (또는 orchestrator) | S6 프롬프트에 recommended_theme 지시 추가, 파싱 후 theme 설정 |
| `backend/routers/jobs.py` | 프리뷰 엔드포인트에 theme 전달, 내보내기 CardTheme() 하드코딩 제거 |
| `web/src/types/editor.ts` | `CardDataPayload`에 `theme` 타입 추가 |
| `web/src/components/editor/DesignPanel.tsx` | 6개 프리셋 스와치 UI + AI 추천 배지 + `onThemeChange` |
| `web/src/app/editor/[jobId]/page.tsx` | `handleThemeChange` 핸들러, `localData.theme` 관리 |

## Rationale

- S6 기존 LLM 호출에 피기백 → 추가 비용 없음 (모델: Haiku 4.5 유지)
- `CardEditorData.theme` 저장 → DB backward compatible (default_factory로 기존 데이터 호환)
- 프리셋 고정 → 사용자가 유효하지 않은 색상 입력하는 경우 없음

## Risks

- S6 JSON 파싱 실패 시 fallback(`tech_blue`)으로 처리 — 무음 처리, 경고 로그만
- 기존 DB에 theme 없는 레코드 → `CardEditorData` default_factory가 자동으로 `tech_blue` 주입
