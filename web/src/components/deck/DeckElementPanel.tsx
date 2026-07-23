'use client'

// 선택 요소 인스펙터 — 연구자(디자인 미숙)용. 흔한 것(글자·색)은 앞에, 기술 컨트롤(위치수치·
// 순서·자동배치 되돌리기)은 '고급'으로 접어 둠. 개발자 전문용어 금지 — 평범한 말로.
// 다중 선택: 정렬·분배. 자유 드래그/리사이즈는 캔버스에서 직접.

import { useState } from 'react'
import type { SelectedInfo, AlignAxis } from './DeckEditor'
import { parseLetterSpacingPx, parseLineHeightRatio, nearestWeightStep, hasTextShadow } from '@/lib/textStyle'

interface Props {
  selected: SelectedInfo | null
  onStyle: (prop: string, value: string) => void
  onDelete: () => void
  onMove: (dir: 'up' | 'down') => void
  onRevertFlow: () => void
  onSetBackground: () => void
  onAlign: (axis: AlignAxis) => void
  onDistribute: (axis: 'h' | 'v') => void
  onSetRect: (r: { left?: number; top?: number; width?: number; height?: number }) => void
}

function rgbToHex(c: string): string {
  const m = /rgba?\(([^)]+)\)/.exec(c)
  if (!m) return /^#/.test(c) ? c : '#000000'
  const [r, g, b] = m[1].split(',').map((x) => parseInt(x.trim(), 10))
  const h = (n: number) => n.toString(16).padStart(2, '0')
  return `#${h(r)}${h(g)}${h(b)}`
}

// 섹션 라벨(mono 아이브로) — 위계 부여
function Section({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3">{label}</div>
      {children}
    </div>
  )
}

// 색 스와치 행 — raw color input 대신 라벨된 스와치 + 숨긴 피커
function ColorRow({ label, color, onChange }: { label: string; color: string; onChange: (hex: string) => void }) {
  const hex = color ? rgbToHex(color) : '#ffffff'
  return (
    <div className="flex items-center justify-between">
      <span className="text-[12.5px] text-ink-2">{label}</span>
      <label className="relative flex items-center gap-2 cursor-pointer group">
        <span className="font-mono text-[10.5px] text-ink-3 uppercase group-hover:text-ink-2 transition-colors">{hex}</span>
        <span className="w-7 h-7 rounded-lg ring-1 ring-inset ring-deck-line shadow-card" style={{ background: hex }} aria-hidden="true" />
        <input type="color" defaultValue={hex} onChange={(e) => onChange(e.target.value)}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer" aria-label={label} />
      </label>
    </div>
  )
}

// Enter/blur 커밋 수치 필드
function NumberField({
  label, value, disabled, onCommit,
}: { label: string; value: number | null; disabled?: boolean; onCommit: (v: number) => void }) {
  const [focused, setFocused] = useState(false)
  const [local, setLocal] = useState(value == null ? '' : String(Math.round(value)))
  const [prev, setPrev] = useState(value)
  if (!focused && value !== prev) {
    setPrev(value)
    setLocal(value == null ? '' : String(Math.round(value)))
  }
  const commit = () => { const n = parseFloat(local); if (!Number.isNaN(n)) onCommit(n) }
  return (
    <label className="flex items-center gap-2">
      <span className="w-4 font-mono text-[11px] text-ink-3">{label}</span>
      <input type="number" value={local} disabled={disabled}
        onChange={(e) => setLocal(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => { setFocused(false); commit() }}
        onKeyDown={(e) => { if (e.key === 'Enter') { commit(); (e.target as HTMLInputElement).blur() } }}
        className="w-full h-8 px-2.5 rounded-lg border border-deck-line bg-surface text-[12.5px] text-ink tabular-nums focus:border-forest-green/50 focus:outline-none disabled:opacity-40 disabled:bg-bg-subtle" />
    </label>
  )
}

const ALIGNS: { axis: AlignAxis; glyph: string; title: string }[] = [
  { axis: 'left', glyph: '⇤', title: '왼쪽' },
  { axis: 'hcenter', glyph: '⇔', title: '가로 가운데' },
  { axis: 'right', glyph: '⇥', title: '오른쪽' },
  { axis: 'top', glyph: '⤒', title: '위' },
  { axis: 'vcenter', glyph: '⇳', title: '세로 가운데' },
  { axis: 'bottom', glyph: '⤓', title: '아래' },
]
const TEXT_ALIGNS = [
  { key: 'left', glyph: '⇤' }, { key: 'center', glyph: '↔' }, { key: 'right', glyph: '⇥' },
] as const

// 이미지 채움 방식 — cover(꽉 채워 잘림)·contain(전체 보이게 여백)
const FITS = [
  { key: 'cover', label: '채우기' }, { key: 'contain', label: '맞추기' },
] as const
// 모서리 둥글기 프리셋 — 미니 스와치로 미리보기(preview=스와치 border-radius)
const RADII = [
  { key: '0px', preview: '0', title: '각짐' },
  { key: '16px', preview: '3px', title: '둥글게' },
  { key: '28px', preview: '5px', title: '더 둥글게' },
  { key: '9999px', preview: '50%', title: '원형' },
] as const
function activeRadiusKey(px: number): string {
  return px >= 1000 ? '9999px' : px >= 22 ? '28px' : px >= 8 ? '16px' : '0px'
}

// 굵기 스케일 — 볼드 토글 대신 4단(평범한 말). 폰트(Pretendard)가 전 웨이트 지원.
const WEIGHTS = [
  { w: 400, label: '보통' }, { w: 600, label: '약간' }, { w: 700, label: '굵게' }, { w: 800, label: '매우' },
] as const
const WEIGHT_VALUES = WEIGHTS.map((x) => x.w)
// 그림자 프리셋 — 사진 위 글자 가독성용. '번짐'=사방 헤일로(테두리 대체). 값은 인라인으로 정확매칭.
const SHADOWS = [
  { key: 'none', label: '없음' },
  { key: '0px 1px 3px rgba(0,0,0,0.28)', label: '옅게' },
  { key: '0px 2px 8px rgba(0,0,0,0.5)', label: '진하게' },
  { key: '0px 0px 4px rgba(0,0,0,0.9)', label: '번짐' },
] as const

export default function DeckElementPanel({
  selected, onStyle, onDelete, onMove, onRevertFlow, onSetBackground, onAlign, onDistribute, onSetRect,
}: Props) {
  if (!selected) {
    return (
      <div className="flex flex-col items-center text-center gap-2 pt-6">
        <span className="w-11 h-11 rounded-full bg-bg-subtle grid place-items-center text-ink-3 text-[18px]" aria-hidden="true">☝</span>
        <p className="text-[13.5px] font-bold text-ink">요소를 선택하세요</p>
        <p className="text-[11.5px] text-ink-3 leading-relaxed max-w-[240px]">카드 위 글자·이미지를 클릭하면 여기서 크기·색·정렬을 바꿀 수 있어요. Shift+클릭으로 여러 개도 함께.</p>
      </div>
    )
  }

  const count = selected.count ?? 1
  const multi = count > 1
  const rect = selected.rect ?? null
  const fontPx = parseFloat(selected.styles.fontSize) || 16
  const weightStep = nearestWeightStep(selected.styles.fontWeight, WEIGHT_VALUES)
  const trackingPx = parseLetterSpacingPx(selected.styles.letterSpacing)
  const leadRatio = parseLineHeightRatio(selected.styles.lineHeight, selected.styles.fontSize)
  const shadowKey = hasTextShadow(selected.styles.textShadow) ? selected.styles.textShadow : 'none'
  const align = selected.styles.textAlign
  const isImage = !multi && !!selected.isImage
  const isBg = !!selected.isBackground
  const objectFit = selected.styles.objectFit || 'cover'
  const radiusKey = activeRadiusKey(parseFloat(selected.styles.borderRadius) || 0)
  const opacityPct = Math.round((parseFloat(selected.styles.opacity) || 1) * 100)
  const typeLabel = multi ? `요소 ${count}개` : isImage ? '이미지' : selected.editable ? '텍스트' : selected.tag

  return (
    <div className="flex flex-col gap-6">
      {/* 헤더 */}
      <div>
        <div className="font-mono text-[10px] uppercase tracking-[0.16em] text-ink-3">선택 요소</div>
        <div className="mt-1.5 flex items-center gap-2">
          <span className="text-[15px] font-bold text-ink">{typeLabel}</span>
          {!multi && <span className="font-mono text-[10.5px] text-ink-3 bg-bg-subtle rounded px-1.5 py-0.5">{selected.tag}</span>}
        </div>
        {!multi && selected.editable && <p className="mt-1 text-[11px] text-ink-3">카드에서 바로 글자를 고칠 수도 있어요.</p>}
      </div>

      {/* 다중: 정렬·분배 */}
      {multi && (
        <Section label="정렬">
          <div className="grid grid-cols-6 gap-1 p-1 rounded-lg bg-bg-subtle border border-deck-line">
            {ALIGNS.map((a) => (
              <button key={a.axis} title={a.title} onClick={() => onAlign(a.axis)}
                className="h-8 rounded-md text-ink-2 text-[13px] hover:bg-surface hover:text-forest-green-deep transition-colors">{a.glyph}</button>
            ))}
          </div>
          <div className="flex gap-1.5">
            <button onClick={() => onDistribute('h')} disabled={!selected.canDistribute}
              className="flex-1 h-8 rounded-lg border border-deck-line text-[11.5px] text-ink-2 disabled:opacity-30 hover:border-forest-green/50 hover:text-forest-green-deep transition-colors">가로 균등</button>
            <button onClick={() => onDistribute('v')} disabled={!selected.canDistribute}
              className="flex-1 h-8 rounded-lg border border-deck-line text-[11.5px] text-ink-2 disabled:opacity-30 hover:border-forest-green/50 hover:text-forest-green-deep transition-colors">세로 균등</button>
          </div>
        </Section>
      )}

      {/* 단일 이미지: 트리트먼트 (배경으로·채움·모서리·투명도) */}
      {isImage && (
        <Section label="이미지">
          <button onClick={onSetBackground}
            className={`h-9 rounded-lg border text-[12.5px] font-semibold transition-colors ${isBg ? 'border-forest-green text-forest-green-deep bg-forest-green-wash' : 'border-deck-line text-ink-2 hover:border-forest-green/50 hover:text-forest-green-deep'}`}>
            {isBg ? '✓ 카드 배경으로 깔림' : '카드 배경으로 깔기'}
          </button>
          <p className="-mt-1.5 text-[10.5px] text-ink-3 leading-relaxed">사진을 카드 전체에 풀블리드로 깔고 글자를 그 위에 얹습니다. 다시 누르면 박스로 되돌립니다.</p>

          <div className="flex items-center justify-between">
            <span className="text-[12.5px] text-ink-2">채움</span>
            <div className="flex items-center gap-0.5 p-0.5 rounded-lg bg-bg-subtle border border-deck-line">
              {FITS.map((f) => (
                <button key={f.key} onClick={() => onStyle('objectFit', f.key)}
                  className={`px-3 h-7 rounded-md text-[11.5px] font-medium transition-colors ${objectFit === f.key ? 'bg-surface shadow-card text-forest-green-deep' : 'text-ink-3 hover:text-ink-2'}`}>{f.label}</button>
              ))}
            </div>
          </div>

          {!isBg && (
            <div className="flex items-center justify-between">
              <span className="text-[12.5px] text-ink-2">모서리</span>
              <div className="flex items-center gap-0.5 p-0.5 rounded-lg bg-bg-subtle border border-deck-line">
                {RADII.map((r) => {
                  const on = radiusKey === r.key
                  return (
                    <button key={r.key} title={r.title} onClick={() => onStyle('borderRadius', r.key)}
                      className={`w-8 h-7 grid place-items-center rounded-md transition-colors ${on ? 'bg-surface shadow-card text-forest-green-deep' : 'text-ink-3 hover:text-ink-2'}`}>
                      <span className="block w-3.5 h-3.5 border-[1.5px] border-current" style={{ borderRadius: r.preview }} aria-hidden="true" />
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[12.5px] text-ink-2">투명도</span>
              <span className="font-mono text-[11px] tabular-nums text-ink-3">{opacityPct}%</span>
            </div>
            <input type="range" min={10} max={100} value={opacityPct}
              onChange={(e) => onStyle('opacity', String(Number(e.target.value) / 100))}
              className="w-full accent-forest-green cursor-pointer" aria-label="투명도" />
          </div>
        </Section>
      )}

      {/* 단일: 글자 */}
      {!multi && !isImage && (
        <Section label="글자">
          <div className="flex items-center justify-between">
            <span className="text-[12.5px] text-ink-2">크기</span>
            <div className="flex items-center p-0.5 rounded-lg bg-bg-subtle border border-deck-line">
              <button onClick={() => onStyle('fontSize', `${Math.max(8, fontPx - 2)}px`)} aria-label="글자 작게"
                className="w-7 h-7 rounded-md grid place-items-center text-ink-2 hover:bg-surface transition-colors">−</button>
              <span className="w-11 text-center text-[12.5px] font-semibold tabular-nums text-ink">{Math.round(fontPx)}</span>
              <button onClick={() => onStyle('fontSize', `${fontPx + 2}px`)} aria-label="글자 크게"
                className="w-7 h-7 rounded-md grid place-items-center text-ink-2 hover:bg-surface transition-colors">+</button>
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[12.5px] text-ink-2">정렬</span>
            <div className="flex items-center gap-0.5 p-0.5 rounded-lg bg-bg-subtle border border-deck-line">
              {TEXT_ALIGNS.map((a) => (
                <button key={a.key} onClick={() => onStyle('textAlign', a.key)} title={a.key}
                  className={`w-8 h-7 rounded-md text-[12px] transition-colors ${align === a.key ? 'bg-surface shadow-card text-forest-green-deep' : 'text-ink-3 hover:text-ink-2'}`}>{a.glyph}</button>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[12.5px] text-ink-2">굵기</span>
            <div className="flex items-center gap-0.5 p-0.5 rounded-lg bg-bg-subtle border border-deck-line">
              {WEIGHTS.map((x) => (
                <button key={x.w} onClick={() => onStyle('fontWeight', String(x.w))}
                  style={{ fontWeight: x.w }}
                  className={`px-2.5 h-7 rounded-md text-[11.5px] transition-colors ${weightStep === x.w ? 'bg-surface shadow-card text-forest-green-deep' : 'text-ink-3 hover:text-ink-2'}`}>{x.label}</button>
              ))}
            </div>
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[12.5px] text-ink-2">자간</span>
              <span className="font-mono text-[11px] tabular-nums text-ink-3">{trackingPx.toFixed(1)}px</span>
            </div>
            <input type="range" min={-2} max={8} step={0.5} value={trackingPx}
              onChange={(e) => onStyle('letterSpacing', `${e.target.value}px`)}
              className="w-full accent-forest-green cursor-pointer" aria-label="자간" />
          </div>
          <div className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="text-[12.5px] text-ink-2">행간</span>
              <span className="font-mono text-[11px] tabular-nums text-ink-3">{leadRatio.toFixed(1)}</span>
            </div>
            <input type="range" min={1} max={2.2} step={0.1} value={leadRatio}
              onChange={(e) => onStyle('lineHeight', e.target.value)}
              className="w-full accent-forest-green cursor-pointer" aria-label="행간" />
          </div>
          <div className="flex items-center justify-between">
            <span className="text-[12.5px] text-ink-2">그림자</span>
            <div className="flex items-center gap-0.5 p-0.5 rounded-lg bg-bg-subtle border border-deck-line">
              {SHADOWS.map((s) => (
                <button key={s.key} onClick={() => onStyle('textShadow', s.key)}
                  className={`px-2.5 h-7 rounded-md text-[11.5px] transition-colors ${shadowKey === s.key ? 'bg-surface shadow-card text-forest-green-deep' : 'text-ink-3 hover:text-ink-2'}`}>{s.label}</button>
              ))}
            </div>
          </div>
          <ColorRow label="글자색" color={selected.styles.color} onChange={(hex) => onStyle('color', hex)} />
        </Section>
      )}

      {/* 단일: 배경 */}
      {!multi && !isImage && (
        <Section label="배경">
          <ColorRow label="배경색" color={selected.styles.background || ''} onChange={(hex) => onStyle('background', hex)} />
        </Section>
      )}

      {/* 위치·크기 — first-class(Figma식 transform). pro 툴이라 숨기지 않음. 배경 풀블리드면 무의미해 숨김 */}
      {!isBg && (rect || (!multi && selected.absolute)) && (
        <Section label="위치·크기 (px)">
          {rect && (
            <div className="grid grid-cols-2 gap-x-3 gap-y-2">
              <NumberField label="X" value={rect.x} onCommit={(v) => onSetRect({ left: v })} />
              <NumberField label="Y" value={rect.y} onCommit={(v) => onSetRect({ top: v })} />
              <NumberField label="W" value={multi ? null : rect.w} disabled={multi} onCommit={(v) => onSetRect({ width: v })} />
              <NumberField label="H" value={multi ? null : rect.h} disabled={multi} onCommit={(v) => onSetRect({ height: v })} />
            </div>
          )}
          {multi && <p className="text-[10.5px] text-ink-3">W·H는 여러 요소라 읽기 전용입니다.</p>}
          {!multi && selected.absolute && (
            <button onClick={onRevertFlow} title="드래그로 옮긴 위치를 자동 배치로 되돌립니다"
              className="h-8 rounded-lg border border-deck-line text-[12px] text-ink-2 hover:border-forest-green/50 hover:text-forest-green-deep transition-colors">↺ 자동 배치로 되돌리기</button>
          )}
        </Section>
      )}

      {/* 삭제 */}
      {!multi && (
        <button onClick={onDelete}
          className="h-9 rounded-lg text-[12.5px] font-semibold text-risk-critical border border-deck-line hover:bg-risk-critical-bg hover:border-risk-critical/40 transition-colors">
          이 요소 삭제
        </button>
      )}
    </div>
  )
}
