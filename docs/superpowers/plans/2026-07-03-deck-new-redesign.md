# /deck/new 리디자인 ("아트디렉터에게 한마디") Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** /deck/new 업로드 화면의 방향 위임 존을 Mirra식 "예시 발화 + 감각어 칩 + 자유입력"으로 재구성한다 (스펙: `docs/superpowers/specs/2026-07-03-deck-new-redesign-design.md`).

**Architecture:** 프론트 단일 파일 변경. 입력값은 기존 `style` 파라미터로 파싱 없이 S6에 전달(변경 없음). 드롭존·카드수·CTA·submit 로직 그대로 — 카피와 "한마디" 존 마크업만 교체.

**Tech Stack:** Next.js 15 App Router, Tailwind(기존 토큰 클래스: `text-ink*`, `border-border`, `bg-forest-green`, `bg-canvas-subtle`).

**검증 방식:** web에 테스트 하네스 없음 → `npx tsc --noEmit` + 브라우저 시각 검증(web/CLAUDE.md: 완료 기준 = 시각 일치, 빌드 성공 아님). 대조 목업: `.superpowers/brainstorm/16654-1783078077/content/final-composition.html`.

---

### Task 1: 상수·카피·"한마디" 존 구현

**Files:**
- Modify: `web/src/app/deck/new/page.tsx`

- [ ] **Step 1: 상수 교체 — STYLE_CHIPS 서술형 + EXAMPLE_UTTERANCES 추가**

`STYLE_CHIPS` 배열(11-17행 부근)을 아래로 교체. 형식 = `이름 — 서술` (em-dash). "웜 페이퍼 에디토리얼" → "따뜻한 종이 잡지" (감각어 네이밍 원칙: 디자이너 용어 금지).

```tsx
// 칩 = 영감 팔레트(선택 강제 아님). 이름은 한국어 감각어만 — 비전공자가 읽고 느낌이 와야 함.
// 클릭 시 풀 서술이 입력창에 들어가 "말로 지시" 문법을 가르친다.
const STYLE_CHIPS = [
  '미드나잇 네온 — 어두운 배경 + 형광 강조선',
  '따뜻한 종이 잡지 — 종이빛 바탕 + 형광펜 강조',
  '학교 칠판 — 분필 손글씨 느낌',
  '지브리풍 — 부드러운 수채 파스텔',
  '깔끔한 공공기관 — 절제된 네이비·그레이',
]

// 예시 발화 = 소프트 스키마: 축(색감/독자/강조점)을 하나씩 가르친다. 코드 파싱 없음(헌법 §1).
const EXAMPLE_UTTERANCES = [
  '어두운 배경에 형광 강조로, 표지는 임팩트 있게',
  '고등학생도 이해할 수 있는 난이도로',
  'Table 3 결과를 표지 메인으로 강조해줘',
]
```

- [ ] **Step 2: 타이틀 캡션 — 해자 강조**

기존:
```tsx
<p className="text-[13px] text-ink-3 mb-6">PDF 한 편 → 발행 가능한 7장. 원문 수치는 코드가 대조합니다.</p>
```
교체:
```tsx
<p className="text-[13px] text-ink-3 mb-6">
  PDF 한 편 → 발행 가능한 카드뉴스. <strong className="text-forest-green font-semibold">원문 수치는 코드가 대조합니다.</strong>
</p>
```

- [ ] **Step 3: "아트 디렉션" 존 → "아트디렉터에게 한마디" 존으로 교체**

기존 블록(라벨 2줄 + 칩 div + textarea, `{/* 아트 디렉션 */}` 주석부터 textarea까지)을 아래로 통째 교체:

```tsx
        {/* 아트디렉터에게 한마디 — 방향 위임(선택). 비우면 AI 자유 = 1급 경로 */}
        <label className="block text-[13px] font-semibold text-ink-2 mb-1">아트디렉터에게 한마디 <span className="text-ink-3 font-normal">(선택)</span></label>
        <p className="text-[12px] text-ink-3 mb-3">비우면 AI가 논문에 맞게 정합니다 · 내용은 논문이 정합니다 — 수치는 검증돼요</p>

        <p className="text-[12px] text-ink-3 mb-1.5">💡 이렇게 말해보세요</p>
        <div className="mb-2.5">
          {EXAMPLE_UTTERANCES.map((u) => (
            <button key={u} type="button" onClick={() => setStyle(u)}
              className="block w-full text-left text-[12.5px] text-ink-2 border border-border rounded-lg px-3 py-2 mb-1.5 bg-canvas-subtle/60 hover:border-forest-green/50 hover:bg-canvas-subtle transition-colors">
              &ldquo;{u}&rdquo;
            </button>
          ))}
        </div>

        <div className="flex flex-wrap gap-2 mb-2.5">
          {STYLE_CHIPS.map((c) => (
            <button key={c} type="button" onClick={() => setStyle(c)}
              className={`text-[12px] px-3 py-1.5 rounded-full border transition-colors ${style === c ? 'bg-forest-green text-canvas border-forest-green' : 'border-border text-ink-2 hover:bg-canvas-subtle'}`}>
              {c.split(' — ')[0]}
            </button>
          ))}
        </div>

        <textarea
          value={style} onChange={(e) => setStyle(e.target.value)}
          placeholder="색감, 난이도, 강조점 — 뭐든 말로 지시하세요… (비워도 됩니다)"
          rows={2}
          className="block w-full text-[13px] rounded-lg border border-border p-3 mb-5 resize-none"
        />
```

주의: 칩 활성 판정 `style === c`는 서술형 문자열 기준이라 그대로 동작(setStyle(c)가 풀 문자열 삽입). 예문 클릭 후엔 어떤 칩도 활성 아님 — 의도된 동작.

- [ ] **Step 4: 타입체크**

Run: `cd web && npx tsc --noEmit`
Expected: 출력 없음(클린)

- [ ] **Step 5: 커밋**

```bash
git add web/src/app/deck/new/page.tsx
git commit -m "[WEB] /deck/new 아트디렉터에게 한마디 — 예시발화+감각어칩 (스펙 2026-07-03)"
```

---

### Task 2: 시각 검증 (완료 기준)

**Files:** 없음 (검증만)

- [ ] **Step 1: dev 서버 확인**

web dev 서버(3000)가 떠 있는지 확인, 없으면 `cd web && npm run dev`. Next는 핫리로드라 재시작 불필요.

- [ ] **Step 2: 브라우저 대조**

http://localhost:3000/deck/new 열고 목업(`.superpowers/brainstorm/16654-1783078077/content/final-composition.html`)과 대조:
1. 캡션에 "원문 수치는 코드가 대조합니다"가 초록 강조로 보임
2. 💡 예시 발화 3개 렌더 — 클릭하면 입력창에 그 문장 삽입(편집 가능)
3. 칩 5개 — "따뜻한 종이 잡지" 라벨 확인, 클릭하면 "따뜻한 종이 잡지 — 종이빛 바탕 + 형광펜 강조" 풀 서술 삽입 + 칩 활성색
4. 입력창 placeholder = "색감, 난이도, 강조점 — 뭐든 말로 지시하세요… (비워도 됩니다)"
5. 드래그앤드롭 존 기존 동작 유지(파일 끌어오면 논문 카드 변신)
6. 빈 입력 + PDF만으로 생성 버튼 활성(비우면 AI 자유 = 1급 경로) — 실제 생성은 누르지 않음(유료 호출)

Expected: 6항목 전부 육안 확인. 불일치 시 Task 1로 돌아가 수정 후 재검증.

- [ ] **Step 3: 스크린샷 기록(선택) + 완료 보고**

사용자에게 화면 확인 요청 — 최종 판단은 사용자.
