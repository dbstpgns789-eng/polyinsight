# UI_COMPONENTS.md — 프론트엔드 컴포넌트 명세

> 구현된 컴포넌트와 예정 컴포넌트의 계약 문서.
> 코드 위치: `../web/src/components/`

---

## 컴포넌트 계층

```
App Shell
├── TopBar               — 로고 + 네비게이션 + 유저 메뉴
├── Pages
│   ├── LandingPage      — 히어로 + 가치 제안 + CTA
│   ├── DashboardPage    — 프로젝트 목록 + 통계
│   └── EditorPage       — 3패널 에디터
│       ├── ContentPanel — 카드 내용 편집
│       ├── PreviewPanel — 카드 미리보기 (실시간)
│       └── DesignPanel  — 템플릿 선택 + 토큰 오버라이드
└── Modals (React Portal)
    ├── UploadModal      — PDF 업로드 + 처리 진행
    └── ExportModal      — 다운로드 + SNS 발행
```

---

## 핵심 컴포넌트 명세

### CardPreview

카드뉴스 1장의 1080×1080 렌더를 브라우저에서 미리보는 컴포넌트.

```typescript
type CardPreviewState = 'loading' | 'ready' | 'error';

interface CardPreviewProps {
  card: CardData | null;   // null = S6 분석 중 (Skeleton 상태)
  template: TemplateId;
  state?: CardPreviewState;
  scale?: number;          // 미리보기 축소 비율 (기본 0.4)
  editable?: boolean;      // 클릭으로 필드 선택 가능 여부
}
```

**Skeleton 상태 (card === null || state === 'loading')**:
- 실제 텍스트 대신 Placeholder 텍스트를 템플릿 위에 렌더
- `opacity: 0.35` + `@keyframes skeleton-pulse` 애니메이션
- 템플릿 레이아웃·색상은 실제로 보여줌 → 유저가 선택 판단 가능
- Placeholder 예시: `"연구 결과 핵심 수치 ..."`, `"주요 발견 사항 ..."`

```css
@keyframes skeleton-pulse {
  0%, 100% { opacity: 0.35; }
  50%       { opacity: 0.55; }
}
.skeleton-text {
  animation: skeleton-pulse 1.8s ease-in-out infinite;
  background: var(--border);
  border-radius: 4px;
  color: transparent;
  user-select: none;
}
```

**상태 전환**:
```
업로드 → state='loading' (Skeleton 표시, S6 백그라운드 실행)
S6 완료 → card=CardData, state='ready' (실제 콘텐츠로 교체, fade-in)
S6 실패 → state='error' (에러 배너, 재시도 버튼)
```

- S7 Playwright 렌더 전 브라우저 미리보기용 (근사치)
- `--set-*` 토큰으로 스킨 교체

### RiskBadge

S6 출력의 risk_level을 시각화하는 배지.

```typescript
type RiskLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

interface RiskBadgeProps {
  level: RiskLevel;
  showLabel?: boolean;
}
```

- CRITICAL: 빨간 배경 + "검토 필요" 레이블
- HIGH: 주황 배경
- MEDIUM: 노란 배경
- LOW: 표시 안 함 (또는 초록)

### UploadModal

PDF 업로드 → 파이프라인 실행 → 완료 대기.

상태 흐름:
```
idle → uploading → processing(S1→S6) → done | error
```

- 처리 중 취소 가능
- error 상태: 재시도 버튼 + 에러 메시지
- done → 에디터 자동 이동

### ExportModal

완성된 카드뉴스 내보내기.

```typescript
interface ExportModalProps {
  jobId: string;
  cards: CardData[];
  hasCriticalRisk: boolean;   // 경고 표시 여부
  hasUnreviewed: boolean;     // 경고 표시 여부
}
```

- `hasCriticalRisk || hasUnreviewed` → 경고 배너 표시
- 경고는 **소프트 차단** — 유저가 "그래도 내보내기" 선택 가능
- 하드블록(CTA 비활성화) 절대 금지

### TemplateSelector

템플릿(디자인 세트) 선택 UI.

```typescript
interface TemplateSelectorProps {
  templates: Template[];
  selected: TemplateId;
  onSelect: (id: TemplateId) => void;
  recommended?: TemplateId;   // AI 추천 템플릿
}
```

- 추천 템플릿에 "AI 추천" 배지
- 미리보기 썸네일 (140×140 축소본)

---

## 에디터 패널 — ContentPanel

카드별 필드 단위 편집.

편집 가능 필드:
- `headline` — 카드 제목 (rich text 예정, 현재 plain)
- `body` — 본문 (단락 단위)
- `stat` — 수치 (원문 출처 표기 포함)
- `image` — 이미지 슬롯 (optional)

각 필드에 RiskBadge 연동.
CRITICAL 필드: 강조 테두리 + 원문 출처 툴팁.

---

## 자동저장

- 5초 idle 후 자동저장 (`useAutoSave` 훅)
- 저장 상태: `saving | saved | error` → TopBar 우측에 표시
- 충돌 없음: 단일 유저, 서버 저장 우선

---

## 미구현 (v2 예정)

- Rich text 편집기 (현재 plain text)
- 폰트 선택 UI
- 카드 순서 드래그&드롭
- SNS 자동발행 연동 버튼
