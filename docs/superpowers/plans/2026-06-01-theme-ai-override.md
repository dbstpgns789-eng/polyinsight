# Theme AI Recommendation + User Override — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** S6 LLM이 논문 분야를 분석해 `recommended_theme`을 JSON에 포함하고, 사용자가 에디터 RightPanel에서 6개 프리셋 중 오버라이드할 수 있게 한다. 선택된 테마는 DB에 저장되며 프리뷰·내보내기에 즉시 반영된다.

**Architecture:** `CardEditorData`에 `theme: CardTheme`과 `recommended_theme_key: str | None`을 추가해 DB에 퍼시스트한다. S6가 기존 LLM 1회 호출에서 `recommended_theme` 필드를 추가로 출력한다 (추가 API 호출 없음). 프리뷰/내보내기 엔드포인트는 `card_data.theme`을 직접 참조한다.

**Tech Stack:** FastAPI, Pydantic v2, SQLite, Next.js 15 App Router, TypeScript, TanStack Query

---

### Task 1: 백엔드 모델 — `THEME_PRESETS` 추가 + `CardEditorData`에 theme 필드

**Files:**
- Modify: `backend/core/models.py` (CardTheme 정의 아래, CardEditorData 클래스)
- Test: `tests/unit/test_theme_model.py` (새 파일)

- [ ] **Step 1: 테스트 작성**

`tests/unit/test_theme_model.py` 파일 생성:

```python
import pytest
from backend.core.models import CardEditorData, CardMeta, CardTheme, FieldValue, THEME_PRESETS


def _make_fv(v=""):
    return FieldValue(value=v)


def _minimal_meta():
    return CardMeta(
        org=_make_fv("KITECH"),
        dept=_make_fv("연구부"),
        researcher=_make_fv("홍길동"),
        month=_make_fv("2024-01"),
        edition_number=_make_fv("2024-01호"),
    )


def test_theme_presets_has_six_keys():
    assert set(THEME_PRESETS.keys()) == {
        "tech_blue", "forest_green", "sunset_orange",
        "royal_violet", "golden_yellow", "slate"
    }


def test_card_editor_data_default_theme():
    data = CardEditorData(meta=_minimal_meta(), cards=[])
    assert data.theme.primary == "#2563EB"
    assert data.theme.dark == "#1A4C96"


def test_card_editor_data_custom_theme():
    theme = THEME_PRESETS["forest_green"]
    data = CardEditorData(meta=_minimal_meta(), cards=[], theme=theme)
    assert data.theme.primary == "#16A34A"


def test_card_editor_data_recommended_key_default_none():
    data = CardEditorData(meta=_minimal_meta(), cards=[])
    assert data.recommended_theme_key is None


def test_card_editor_data_recommended_key_set():
    data = CardEditorData(
        meta=_minimal_meta(), cards=[],
        recommended_theme_key="forest_green"
    )
    assert data.recommended_theme_key == "forest_green"


def test_backward_compat_no_theme_in_dict():
    """기존 DB 레코드(theme 없음) → default_factory로 복원."""
    raw = {
        "meta": {
            "org": {"value": "KITECH"},
            "dept": {"value": "연구부"},
            "researcher": {"value": "홍길동"},
            "month": {"value": "2024-01"},
            "edition_number": {"value": "2024-01호"},
        },
        "cards": [],
    }
    data = CardEditorData.model_validate(raw)
    assert data.theme.primary == "#2563EB"  # default
    assert data.recommended_theme_key is None
```

- [ ] **Step 2: 테스트 실패 확인**

```
cd C:\Users\User\Desktop\한국생산기술연구원_근로장학\polyinsight
python -m pytest tests/unit/test_theme_model.py -v
```

Expected: `FAILED` — `THEME_PRESETS` not defined, `recommended_theme_key` attribute error

- [ ] **Step 3: 모델 구현**

`backend/core/models.py`에서 `CardTheme` 클래스 바로 아래에 추가:

```python
class CardTheme(BaseModel):
    primary: str = "#2563EB"
    dark: str = "#1A4C96"


THEME_PRESETS: dict[str, "CardTheme"] = {
    "tech_blue":     CardTheme(primary="#2563EB", dark="#1A4C96"),
    "forest_green":  CardTheme(primary="#16A34A", dark="#166534"),
    "sunset_orange": CardTheme(primary="#EA580C", dark="#9A3412"),
    "royal_violet":  CardTheme(primary="#7C3AED", dark="#4C1D95"),
    "golden_yellow": CardTheme(primary="#D97706", dark="#92400E"),
    "slate":         CardTheme(primary="#475569", dark="#1E293B"),
}
```

`CardEditorData` 클래스 수정 (기존 `theme: CardTheme = Field(default_factory=CardTheme)` 라인이 없으면 추가):

```python
class CardEditorData(BaseModel):
    storyboard: Storyboard | None = None       # S6 기획 결과, 디버깅·UI 표시용
    meta: CardMeta
    cards: List[CardSlot]                      # 가변 길이 (S6가 결정)
    theme: CardTheme = Field(default_factory=CardTheme)
    recommended_theme_key: str | None = None
```

- [ ] **Step 4: 테스트 통과 확인**

```
python -m pytest tests/unit/test_theme_model.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 5: 커밋**

```
git add backend/core/models.py tests/unit/test_theme_model.py
git commit -m "[BE] CardEditorData에 theme/recommended_theme_key 필드 추가, THEME_PRESETS 정의"
```

---

### Task 2: S6 — LLM 프롬프트에 `recommended_theme` 추가 + 파싱

**Files:**
- Modify: `backend/agents/s6_card_json.py`
- Test: `tests/unit/test_s6_theme.py` (새 파일)

- [ ] **Step 1: 테스트 작성**

`tests/unit/test_s6_theme.py` 파일 생성:

```python
import pytest
from backend.agents.s6_card_json import S6CardJsonAgent
from backend.core.models import THEME_PRESETS, CardEditorData, CardMeta, FieldValue


def _minimal_parsed(theme_key: str) -> dict:
    fv = {"value": "test", "confidence": "high", "match_quality": "exact",
          "claim_type": "qualitative", "source": {"section": "abstract", "page": 1},
          "risk_level": "LOW", "verified": False}
    return {
        "recommended_theme": theme_key,
        "storyboard": {
            "story_arc": "테스트 스토리",
            "beats": [{"card_num": 1, "template_type": "cover",
                       "narrative_role": "소개", "key_message": "핵심"}],
        },
        "meta": {
            "org": fv, "dept": fv, "researcher": fv,
            "month": fv, "edition_number": fv,
        },
        "cards": [{"card_num": 1, "template_type": "cover",
                   "fields": {"title": fv}}],
    }


agent = S6CardJsonAgent()


def test_forest_green_theme_applied():
    parsed = _minimal_parsed("forest_green")
    result = agent._build_card_editor_data(parsed)
    assert result.theme.primary == "#16A34A"
    assert result.recommended_theme_key == "forest_green"


def test_tech_blue_theme_applied():
    parsed = _minimal_parsed("tech_blue")
    result = agent._build_card_editor_data(parsed)
    assert result.theme.primary == "#2563EB"
    assert result.recommended_theme_key == "tech_blue"


def test_invalid_theme_key_falls_back_to_tech_blue():
    parsed = _minimal_parsed("nonexistent_key")
    result = agent._build_card_editor_data(parsed)
    assert result.theme.primary == "#2563EB"
    assert result.recommended_theme_key == "tech_blue"


def test_missing_theme_key_falls_back_to_tech_blue():
    parsed = _minimal_parsed("tech_blue")
    del parsed["recommended_theme"]
    result = agent._build_card_editor_data(parsed)
    assert result.theme.primary == "#2563EB"
    assert result.recommended_theme_key == "tech_blue"


def test_all_valid_preset_keys_resolve():
    for key in THEME_PRESETS:
        parsed = _minimal_parsed(key)
        result = agent._build_card_editor_data(parsed)
        assert result.theme == THEME_PRESETS[key]
        assert result.recommended_theme_key == key
```

- [ ] **Step 2: 테스트 실패 확인**

```
python -m pytest tests/unit/test_s6_theme.py -v
```

Expected: `FAILED` — `_build_card_editor_data` does not handle `recommended_theme`

- [ ] **Step 3: S6 `_SYSTEM` 프롬프트 수정**

`backend/agents/s6_card_json.py`의 `_SYSTEM` 문자열에서 아래 블록을 찾아 제거:

```python
테마 컬러 제안 (강제 아님):
농업/식품: #3BAF6B | 환경/에너지: #0EA5BE | 로봇/제조: #F59E20
의료/바이오: #6C5CE7 | 소재/화학: #7B5FFF | 센서/전자: #F5C430
기본(미분류): #2563EB
```

그 위치에 아래를 추가:

```python
recommended_theme — 논문 연구 분야에 따라 정확히 하나를 선택:
tech_blue: AI·ML·컴퓨터·네트워크·센서·전자
forest_green: 바이오·화학·폴리머·재료·식품·농업·환경
sunset_orange: 에너지·배터리·기계·제조·로봇
royal_violet: 의료·임상·건강·약학
golden_yellow: 경제·정책·사회·혁신
slate: 기타
```

- [ ] **Step 4: S6 `_USER` JSON 스키마에 `recommended_theme` 필드 추가**

`_USER` 문자열에서 아래 부분을 찾아:

```python
아래 JSON 스키마를 완성하라:

{{
  "storyboard": {{
```

아래로 교체:

```python
아래 JSON 스키마를 완성하라:

{{
  "recommended_theme": "tech_blue",
  "storyboard": {{
```

- [ ] **Step 5: `_build_card_editor_data` 수정**

`backend/agents/s6_card_json.py` 상단 import에 `THEME_PRESETS` 추가:

```python
from ..core.models import (
    CardEditorData, CardMeta, CardSlot, FieldValue,
    MatchQuality, RiskLevel, ClaimType, FieldSource,
    CardStorybeat, Storyboard,
    S6Input, S6Output,
    THEME_PRESETS,
)
```

`_build_card_editor_data` 메서드 끝부분 수정 (기존 `return CardEditorData(...)` 라인 교체):

```python
def _build_card_editor_data(self, parsed: dict) -> CardEditorData:
    # storyboard 파싱 (없으면 None)
    storyboard: Storyboard | None = None
    if raw_sb := parsed.get("storyboard"):
        beats = [CardStorybeat.model_validate(b) for b in raw_sb.get("beats", [])]
        storyboard = Storyboard(story_arc=raw_sb.get("story_arc", ""), beats=beats)

    meta = CardMeta.model_validate(parsed["meta"])
    cards: list[CardSlot] = []
    for raw_card in parsed["cards"]:
        fields = {
            k: FieldValue.model_validate(v)
            for k, v in raw_card["fields"].items()
        }
        cards.append(CardSlot(
            card_num=raw_card["card_num"],
            template_type=raw_card["template_type"],
            fields=fields,
        ))

    raw_key = parsed.get("recommended_theme", "tech_blue")
    theme_key = raw_key if raw_key in THEME_PRESETS else "tech_blue"
    theme = THEME_PRESETS[theme_key]

    return CardEditorData(
        storyboard=storyboard, meta=meta, cards=cards,
        theme=theme, recommended_theme_key=theme_key,
    )
```

- [ ] **Step 6: mock 모드도 theme 설정**

`_build_mock_card_data` 함수 끝의 `return CardEditorData(...)` 라인을 교체:

```python
    return CardEditorData(
        storyboard=storyboard, meta=meta, cards=cards,
        theme=THEME_PRESETS["tech_blue"],
        recommended_theme_key="tech_blue",
    )
```

- [ ] **Step 7: 테스트 통과 확인**

```
python -m pytest tests/unit/test_s6_theme.py tests/unit/test_theme_model.py -v
```

Expected: 모든 테스트 PASS

- [ ] **Step 8: 커밋**

```
git add backend/agents/s6_card_json.py tests/unit/test_s6_theme.py
git commit -m "[BE] S6 LLM 프롬프트에 recommended_theme 필드 추가, 파싱 및 fallback 구현"
```

---

### Task 3: 백엔드 라우터 — 프리뷰·내보내기에 `card_data.theme` 연결

**Files:**
- Modify: `backend/routers/jobs.py`

- [ ] **Step 1: 프리뷰 엔드포인트 수정**

`backend/routers/jobs.py`의 `get_card_preview` 함수에서:

```python
    renderer = S7Renderer()
    html = renderer.render_slot_html(slot, card_data)
```

를 아래로 교체:

```python
    renderer = S7Renderer()
    html = renderer.render_slot_html(slot, card_data, theme=card_data.theme)
```

- [ ] **Step 2: 내보내기 엔드포인트 수정**

`trigger_export` 함수에서:

```python
    s7_out = await renderer.execute(S7Input(job_id=job_id, card_data=card_data, theme=CardTheme()))
```

를 아래로 교체:

```python
    s7_out = await renderer.execute(S7Input(job_id=job_id, card_data=card_data, theme=card_data.theme))
```

- [ ] **Step 3: 불필요해진 `CardTheme` import 정리 확인**

`jobs.py` import 라인 확인:
```python
from ..core.models import CardEditorData, CardTheme
```
`CardTheme`이 더 이상 직접 사용되지 않으면 제거:
```python
from ..core.models import CardEditorData
```

- [ ] **Step 4: 백엔드 서버 기동 확인**

```
cd C:\Users\User\Desktop\한국생산기술연구원_근로장학\polyinsight\backend
python -m uvicorn main:app --port 8000 --reload
```

Expected: 서버 정상 기동, 오류 없음 (Ctrl+C로 종료)

- [ ] **Step 5: 커밋**

```
git add backend/routers/jobs.py
git commit -m "[BE] 프리뷰·내보내기 엔드포인트에 card_data.theme 연결 (CardTheme() 하드코딩 제거)"
```

---

### Task 4: 프론트엔드 타입 — `CardTheme`, `CardDataPayload` 업데이트

**Files:**
- Modify: `web/src/types/editor.ts`

- [ ] **Step 1: 타입 파일 수정**

`web/src/types/editor.ts` 전체를 아래로 교체:

```typescript
export type RiskLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM'

export interface FieldValue {
  value?: string
  confidence?: string
  risk_level?: RiskLevel
  source?: { section: string; page: number }
}

export interface Card {
  card_num: number
  template_type: string
  image_url?: string
  fields?: Record<string, FieldValue>
}

export interface CardTheme {
  primary: string
  dark: string
}

export interface CardDataPayload {
  cards: Card[]
  theme?: CardTheme
  recommended_theme_key?: string
}

export interface ApiResponse {
  filename?: string
  cardData?: CardDataPayload
}
```

- [ ] **Step 2: TypeScript 빌드 확인**

```
cd C:\Users\User\Desktop\한국생산기술연구원_근로장학\polyinsight\web
npx tsc --noEmit
```

Expected: 오류 없음

- [ ] **Step 3: 커밋**

```
git add web/src/types/editor.ts
git commit -m "[WEB] CardTheme 타입 추가, CardDataPayload에 theme/recommended_theme_key 필드 추가"
```

---

### Task 5: RightPanel — 가짜 액센트 컬러를 실제 6개 프리셋으로 교체

**Files:**
- Modify: `web/src/components/editor/RightPanel.tsx`

- [ ] **Step 1: Props 인터페이스에 theme 관련 props 추가**

`RightPanel.tsx`의 `interface Props` 블록을 찾아 교체:

```typescript
interface Props {
  jobId: string
  activeCard?: Card
  onImageUpdate: (imageUrl: string | null) => void
  imageUploadRequested?: boolean
  onImageUploadHandled?: () => void
  currentThemePrimary?: string
  recommendedThemeKey?: string
  onThemeChange: (theme: { primary: string; dark: string }) => void
}
```

- [ ] **Step 2: 가짜 `ACCENT_COLORS` 상수를 실제 `THEME_PRESETS` 상수로 교체**

파일 상단에서 `ACCENT_COLORS` 상수 정의 블록을 찾아 제거하고, 그 자리에 아래 추가:

```typescript
const THEME_PRESETS = [
  { key: 'tech_blue',     label: '테크 블루',    primary: '#2563EB', dark: '#1A4C96' },
  { key: 'forest_green',  label: '포레스트 그린', primary: '#16A34A', dark: '#166534' },
  { key: 'sunset_orange', label: '썬셋 오렌지',  primary: '#EA580C', dark: '#9A3412' },
  { key: 'royal_violet',  label: '로열 바이올렛',primary: '#7C3AED', dark: '#4C1D95' },
  { key: 'golden_yellow', label: '골든 옐로',    primary: '#D97706', dark: '#92400E' },
  { key: 'slate',         label: '슬레이트',     primary: '#475569', dark: '#1E293B' },
] as const
```

- [ ] **Step 3: 컴포넌트 함수 시그니처에 새 props 추가**

```typescript
export default function RightPanel({
  jobId, activeCard, onImageUpdate, imageUploadRequested, onImageUploadHandled,
  currentThemePrimary, recommendedThemeKey, onThemeChange,
}: Props) {
```

- [ ] **Step 4: 기존 `§4 — 브랜드 액센트` 섹션을 실제 테마 선택 UI로 교체**

파일에서 `{/* §4 — 브랜드 액센트 */}` 섹션 블록 전체를 찾아 아래로 교체:

```tsx
{/* §4 — 테마 색상 */}
<section>
  <SectionHead>테마 색상</SectionHead>
  <div className="grid grid-cols-3" style={{ gap: 8 }}>
    {THEME_PRESETS.map(t => {
      const isActive = currentThemePrimary === t.primary
      const isRecommended = recommendedThemeKey === t.key
      return (
        <button
          key={t.key}
          aria-label={t.label}
          onClick={() => onThemeChange({ primary: t.primary, dark: t.dark })}
          className={`relative flex flex-col items-center gap-1 transition-all ${
            isActive
              ? 'border-2 border-forest-green bg-forest-green-wash'
              : 'border border-surface-border bg-surface-bright hover:bg-forest-green-ghost'
          }`}
          style={{ padding: '8px 4px', borderRadius: 10 }}
        >
          <div className="w-8 h-8 rounded-full" style={{ background: t.primary }} />
          <span style={{
            fontSize: 10, fontWeight: 600, color: 'var(--ink)',
            lineHeight: 1.2, textAlign: 'center',
          }}>
            {t.label}
          </span>
          {isRecommended && (
            <span
              className="absolute -top-1.5 -right-1.5 text-[8px] font-bold px-1 rounded-full"
              style={{ background: '#16A34A', color: '#fff', lineHeight: 1.6 }}
            >
              AI
            </span>
          )}
        </button>
      )
    })}
  </div>
</section>
```

- [ ] **Step 5: TypeScript 빌드 확인**

```
cd C:\Users\User\Desktop\한국생산기술연구원_근로장학\polyinsight\web
npx tsc --noEmit
```

Expected: 오류 없음 (단, editor page에서 onThemeChange를 아직 전달 안 했으므로 타입 오류 가능 — Task 6에서 수정)

- [ ] **Step 6: 커밋**

```
git add web/src/components/editor/RightPanel.tsx
git commit -m "[WEB] RightPanel 테마 색상 섹션을 실제 6개 프리셋 + AI 추천 배지로 구현"
```

---

### Task 6: 에디터 페이지 — `handleThemeChange` 연결 + RightPanel props 전달

**Files:**
- Modify: `web/src/app/editor/[jobId]/page.tsx`

- [ ] **Step 1: `handleThemeChange` 핸들러 추가**

`editor/[jobId]/page.tsx`에서 `handleImageUpdate` 함수 아래에 추가:

```typescript
const handleThemeChange = useCallback((theme: { primary: string; dark: string }) => {
  setLocalData((prev) => {
    const base = prev ?? apiData?.cardData
    if (!base) return prev
    const updated = { ...base, theme }
    saveNow(updated)
    return updated
  })
}, [apiData, saveNow])
```

`useCallback` import가 이미 있는지 확인 (있으면 추가 불필요).

- [ ] **Step 2: `RightPanel`에 theme props 전달**

`<RightPanel ... />` 부분을 찾아 새 props 추가:

```tsx
<RightPanel
  jobId={jobId}
  activeCard={cards[activeCardIdx]}
  onImageUpdate={handleImageUpdate}
  imageUploadRequested={imageUploadRequested}
  onImageUploadHandled={() => setImageUploadRequested(false)}
  currentThemePrimary={cardData?.theme?.primary}
  recommendedThemeKey={cardData?.recommended_theme_key}
  onThemeChange={handleThemeChange}
/>
```

- [ ] **Step 3: TypeScript 빌드 오류 없음 확인**

```
cd C:\Users\User\Desktop\한국생산기술연구원_근로장학\polyinsight\web
npx tsc --noEmit
```

Expected: 오류 없음

- [ ] **Step 4: 커밋**

```
git add web/src/app/editor/[jobId]/page.tsx
git commit -m "[WEB] 에디터 페이지에 handleThemeChange 연결, RightPanel에 theme props 전달"
```

---

### Task 7: 수동 검증 (성공 기준)

현재 에디터에 카드뉴스가 열려 있는 상태에서:

- [ ] **Step 1: 백엔드 서버 기동**

```
cd C:\Users\User\Desktop\한국생산기술연구원_근로장학\polyinsight\backend
python -m uvicorn main:app --port 8000 --reload
```

- [ ] **Step 2: 프론트엔드 서버 기동**

```
cd C:\Users\User\Desktop\한국생산기술연구원_근로장학\polyinsight\web
npm run dev
```

- [ ] **Step 3: 에디터 열기**

브라우저에서 현재 열린 jobId 기준 에디터 접속.

- [ ] **Step 4: 초기 상태 확인**

우측 패널 "테마 색상" 섹션에 6개 원형 스와치가 보임.
현재 활성 테마(파란색)에 초록 테두리 표시 확인.
"AI" 배지가 어떤 프리셋 위에 있는지 확인.

- [ ] **Step 5: 오버라이드 테스트**

"포레스트 그린" 클릭 → 자동저장 진행 → 약 2~3초 후 중앙 카드 프리뷰의 강조색이 초록으로 변경됨.

- [ ] **Step 6: 다른 색상으로 재오버라이드**

"슬레이트" 클릭 → 프리뷰 강조색이 회색 계열로 변경됨.

- [ ] **Step 7: 최종 커밋**

```
git add .
git commit -m "[BE/WEB] Theme AI 추천 + 사용자 오버라이드 기능 완성"
```
