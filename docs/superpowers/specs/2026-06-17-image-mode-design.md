# image_mode 독립 차원 설계

> 2026-06-17
> 배경: 박사님 피드백 "템플릿이 색깔 바꿔치기 아니야?" → 이미지 활용 방식을 스켈레톤에서 분리해 시각 풍부함·자율성 확보.

---

## Problem

현재 이미지 배치 방식은 **스켈레톤에 박혀 있다.**

- `Cover` → 이미지 항상 하단 밴드
- `Feature` → 이미지 항상 우측
- `BigStat`, `Reasons` 등 → 이미지 없음

이미지를 풀블리드로 쓰거나 상단 밴드로 바꾸려면 새 스켈레톤을 만들어야 한다.
결과: S6가 레이아웃 조합을 선택할 자율성이 없고, 덱이 "색만 다른 같은 구조"로 느껴진다.

---

## Decision

`image_mode` 필드를 **스켈레톤과 독립적인 차원**으로 추가한다.

```
기존:  template_type  →  콘텐츠 배치 + 이미지 위치 모두 고정
변경:  template_type  →  콘텐츠 배치만
      image_mode      →  이미지 렌더 방식만  ← 신규
```

S6가 두 값을 독립적으로 판단 → 14 스켈레톤 × 6 image_mode = 84가지 조합.
**기존 스켈레톤 코드 무변경.**

---

## image_mode 값 정의

| 값 | 설명 | 이미지 없을 때 |
|---|---|---|
| `box` | 현재 방식. VisualZone 둥근 박스 안에 (기본값, 하위 호환) | 빈 박스 숨김 |
| `backdrop` | 이미지 풀블리드 + 하단 그라디언트 오버레이. SNS 임팩트 최대 | 세트 배경 그대로 |
| `ghost` | 이미지 극저투명도(8~12%) 배경. 수치·텍스트 카드에 시각 풍부함 추가 | 세트 배경 그대로 |
| `band` | 상단 50% 이미지 밴드, 하단 50% 스켈레톤. 잡지 표지형 | 상단 세트 배경 |
| `split` | 좌 48% 이미지, 우 52% 스켈레톤. 논문 figure 나란히 설명 | 좌측 세트 배경 |
| `panel` | 이미지 풀블리드 배경 + 하단 불투명 패널 안에 텍스트. 가독성 보장 | 세트 배경 그대로 |
| `none` | 이미지 완전히 없음. VisualZone 숨김 | (없음) |

### S6 선택 기준

| 상황 | 권장 image_mode |
|---|---|
| 강렬한 사진·현장 이미지 있음 | `backdrop` |
| 논문 figure·SEM·그래프 설명 필요 | `band` or `split` |
| 이미지 있음 + 긴 텍스트 가독성 필수 | `panel` |
| 데이터 heavy 카드 (막대·수치) + 이미지 있음 | `ghost` |
| 이미지 없음 or 데이터 카드 | `none` |
| 업로드 여부 불명, 폴백 안전 | `box` |

---

## 데이터 모델 변경

### backend/core/models.py — CardSlot

```python
IMAGE_MODES = {"box", "backdrop", "ghost", "band", "split", "panel", "none"}

class CardSlot(BaseModel):
    card_num: int
    template_type: str
    fields: Dict[str, FieldValue]
    image_url: str | None = None
    focal: Dict[str, float] | None = None        # 기존
    image_fit: str | None = None                 # 기존 ('cover'|'contain')
    image_mode: str = "box"                      # 신규. 기본 'box' (하위 호환)
    field_styles: Dict[str, FieldStyle] | None = None
```

### S6 출력 스키마 (카드별 추가 필드)

```json
{
  "image_mode": "backdrop",
  "image_mode_rationale": "SEM 사진 임팩트 극대화를 위해"
}
```

---

## 렌더 아키텍처

### 원칙
- `backdrop` / `ghost` / `panel` / `none` → **Phase 1** (CSS 레이어만 추가, 구조 변경 없음)
- `band` / `split` → **Phase 2** (CardFrame이 구조적 레이아웃 주입, 스켈레톤 렌더 영역 제한)
- `box` → 현재 그대로

### Phase 1 렌더링 (CardFrame 확장)

CardFrame props에 `imageUrl` / `imageMode` 추가:

```
backdrop:
  ① <img src={imageUrl} style="position:absolute; inset:0; object-fit:cover; z-index:0">
  ② <div style="position:absolute; inset:0; background: linear-gradient(투명→검정); z-index:1">
  ③ children (스켈레톤) → z-index:2 위에 정상 렌더
  ④ CardSurface background → transparent (Context로 전달)

ghost:
  ① CardFrame inner: background: var(--set-bg-gradient) 유지 (세트 색상이 베이스)
  ② <img src={imageUrl} style="position:absolute; inset:0; object-fit:cover; opacity:0.09; z-index:1">
  ③ children (스켈레톤) → z-index:2. CardSurface background → transparent (이미지 투비침)

panel:
  ① <img src={imageUrl} style="position:absolute; inset:0; object-fit:cover; z-index:0">
  ② children → position:absolute; bottom:0; background:rgba(255,255,255,0.95); 패널 안에

none:
  이미지 렌더 없음. VisualZone 자동 숨김.
```

### VisualZone 자동 숨김

```typescript
// skin/VisualZone.tsx
const { imageMode } = useCardContext()
if (imageMode !== 'box') return null
```

**기존 14개 스켈레톤 코드 변경 없음.** VisualZone이 스스로 판단.

### Phase 2 렌더링 (band / split)

CardFrame이 이미지 존과 스켈레톤 존을 구조적으로 분리:

```
band:
  [상단 50% — <img object-fit:cover>]
  [하단 50% — 스켈레톤 렌더 (CardSurface 세트 배경)]

split:
  [좌 48% — <img object-fit:cover>]  [우 52% — 스켈레톤 렌더]
```

스켈레톤은 자신이 전체 카드가 아닌 일부 영역에서 렌더됨을 인식하지 않아도 됨.
CardSurface가 `flex:1 / height:100%` 로 할당 영역을 채움.

---

## 에디터 UI

위치: RightPanel 이미지 업로드 섹션 아래

- `image_mode` 아이콘 토글 6개 (box·backdrop·ghost·band·split·panel·none)
- S6 제안값이 기본 선택, 사용자가 직접 바꿀 수 있음
- 이미지 URL 없을 때 `backdrop/band/split/panel` 선택 시 — 에디터에서 점선 드롭존만 표시 (export 비차단)

---

## Risks

| 리스크 | 대응 |
|---|---|
| backdrop 시 가독성 저하 | 그라디언트 오버레이 강도 토큰화 (`--image-overlay-opacity`) |
| S6가 image_mode를 일관성 없이 선택 | S6 프롬프트에 선택 기준표 명시 |
| band/split에서 CardSurface 레이아웃 깨짐 | Phase 2 슬라이스에서 별도 검증 |
| 이미지 없는데 backdrop 선택 시 빈 카드 | fallback: 이미지 없으면 세트 배경 그대로 |

---

## 구현 순서

**Phase 1** (이번 슬라이스):
1. `CardSlot`에 `image_mode` 필드 추가 (backend)
2. 프론트 타입 동기화
3. `CardContext`에 `imageMode` 추가
4. `VisualZone` 자동 숨김 로직
5. `CardFrame`에 backdrop / ghost / none / panel 렌더 구현
6. S6 프롬프트에 image_mode 선택 지침 추가
7. RightPanel image_mode 토글 UI
8. E2E: 기존 box 카드 회귀 없음 확인

**Phase 2** (후속):
9. band 레이아웃 (CardFrame 구조 주입)
10. split 레이아웃 (CardFrame 구조 주입)

---

## 관련 문서

- 디자인 시스템: `docs/18_card_design_system.md`
- 에디터 UI: `docs/12_card_editor_content.md`
- S6 그라운딩: `docs/05_agent_design.md`
