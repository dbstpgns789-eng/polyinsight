'use client'

// 덱 생성 진입 (헌법 v3.0). 논문 PDF + 아트 디렉션(미감 방향)을 받아 단일 저작 시작.
// 디자인: design_reference/claude-design/새 카드뉴스 브리핑.dc.html (2026-07-03 이식)
// 아트 디렉션 = 동질화 방지의 핵심: 같은 논문도 방향을 바꿔 다르게 뽑는다.

import { useCallback, useRef, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import AuthGuard from '@/components/auth/AuthGuard'
import { uploadDeck, friendlyError } from '@/lib/api'
import { planGateKind } from '@/lib/plan'

// 칩 = 영감 팔레트(선택 강제 아님). 이름은 한국어 감각어만 — 비전공자가 읽고 느낌이 와야 함.
// 클릭 시 풀 서술이 입력창에 들어가 "말로 지시" 문법을 가르친다.
const STYLE_CHIPS = [
  '미드나잇 네온: 어두운 배경 + 형광 강조선',
  '따뜻한 종이 잡지: 종이빛 바탕 + 형광펜 강조',
  '학교 칠판: 분필 손글씨 느낌',
  '지브리풍: 부드러운 수채 파스텔',
  '깔끔한 공공기관: 절제된 네이비·그레이',
]

// 예시 발화 = 소프트 스키마: 축(색감/독자/강조점)을 하나씩 가르친다. 코드 파싱 없음(헌법 §1).
const EXAMPLE_UTTERANCES = [
  '어두운 배경에 형광 강조로, 표지는 임팩트 있게',
  '고등학생도 이해할 수 있는 난이도로',
  'Table 3 결과를 표지 메인으로 강조해줘',
]

// 상한 10 = 인스타그램 캐러셀 최대 장수(발행 관점의 실질 천장). 백엔드는 12까지 받는다.
// 7이던 옛 상한은 Haiku 시절 출력 토큰 8,192 천장 탓이었다 — 지금은 Opus에 32,000이라 근거가 사라졌다.
const CARD_TICKS = [3, 4, 5, 6, 7, 8, 9, 10]
const CARD_MIN = 3
const CARD_MAX = 10

function formatSize(bytes: number): string {
  return bytes >= 1_048_576 ? `${(bytes / 1_048_576).toFixed(1)}MB` : `${Math.max(1, Math.round(bytes / 1024))}KB`
}

const cardShadow = { boxShadow: '0 1px 2px rgba(20,50,40,.04), 0 14px 34px rgba(20,50,40,.05)' }

function FileIcon({ size, up }: { size: number; up?: boolean }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M14 3v4a1 1 0 0 0 1 1h4" />
      <path d="M17 21H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h7l5 5v11a2 2 0 0 1-2 2Z" />
      {up ? (<><path d="M12 18v-6" /><path d="m9.5 14 2.5-2.5 2.5 2.5" /></>) : (<><path d="M9 13h6" /><path d="M9 17h4" /></>)}
    </svg>
  )
}

function CheckIcon({ size, stroke = 2.6 }: { size: number; stroke?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d="M20 6 9 17l-5-5" />
    </svg>
  )
}

function DeckNewInner() {
  const router = useRouter()
  const [file, setFile] = useState<File | null>(null)
  const [cardCount, setCardCount] = useState(7)
  const [style, setStyle] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const acceptFile = useCallback((f: File | null | undefined) => {
    if (!f) return
    if (f.type !== 'application/pdf' && !f.name.toLowerCase().endsWith('.pdf')) {
      setError('PDF 파일만 올릴 수 있습니다.')
      return
    }
    setError(null)
    setFile(f)
  }, [])

  const submit = useCallback(async () => {
    if (!file) { setError('논문 PDF를 선택해 주세요.'); return }
    setSubmitting(true); setError(null)
    try {
      const r = await uploadDeck(file, cardCount, undefined, style.trim() || undefined)
      router.push(`/deck/${r.data.jobId}`)
    } catch (e) {
      // 무료체험 소진(402 ERR-PLAN-AUTHOR) → 업그레이드로. 그 외 에러는 화면에 그대로 표시.
      const kind = planGateKind(e)
      if (kind === 'author') {
        router.push('/upgrade?from=author')
        return
      }
      setError(friendlyError(e, '업로드에 실패했어요. 파일을 확인하고 다시 시도해 주세요.'))
      setSubmitting(false)
    }
  }, [file, cardCount, style, router])

  const fillPct = `${((cardCount - CARD_MIN) / (CARD_MAX - CARD_MIN)) * 100}%`

  return (
    <div className="min-h-screen bg-canvas-subtle flex justify-center px-6 pt-13 pb-19" style={{ wordBreak: 'keep-all' }}>
      <div className="w-full max-w-[560px] deck-fade-up">

        {/* 슬림 헤더 — 작업 화면은 길잡이만, 연설 금지. 세리프 대제목·배지는 랜딩 문법이라 은퇴 */}
        <nav className="flex items-center gap-2.5 mb-6" aria-label="페이지 내비게이션">
          <Link href="/dashboard" className="inline-flex items-center gap-1.5 text-[13.5px] font-semibold text-ink-3 hover:text-forest-green-deep transition-colors">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="m15 18-6-6 6-6" /></svg>
            대시보드
          </Link>
          <span className="w-[3px] h-[3px] rounded-full bg-border" aria-hidden="true" />
          <h1 className="text-[15px] font-bold text-ink">새 카드뉴스</h1>
        </nav>

        {/* 드롭존 / 논문 카드 */}
        <input
          ref={inputRef} type="file" accept="application/pdf" className="hidden"
          onChange={(e) => { acceptFile(e.target.files?.[0]); e.target.value = '' }}
        />
        {file ? (
          <div className="bg-canvas border border-border rounded-[20px] px-5 py-4.5 flex items-center gap-4" style={cardShadow}>
            <div className="w-12 h-14 rounded-[11px] bg-forest-green-wash border border-forest-green/25 flex items-center justify-center text-forest-green-deep shrink-0">
              <FileIcon size={24} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-[15.5px] font-bold text-ink truncate">{file.name}</p>
              <p className="text-[13px] text-ink-3 mt-0.5">PDF · {formatSize(file.size)}</p>
              <p className="inline-flex items-center gap-1.5 mt-2 text-forest-green-deep text-[12.5px] font-bold">
                <CheckIcon size={13} stroke={2.8} />
                논문 업로드 완료
              </p>
            </div>
            <button type="button" onClick={() => inputRef.current?.click()}
              className="shrink-0 bg-canvas border border-border text-ink-2 font-bold text-[13.5px] px-4 py-2 rounded-[10px] transition-colors hover:border-forest-green hover:text-forest-green-deep">
              교체
            </button>
          </div>
        ) : (
          <>
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={(e) => { e.preventDefault(); setDragOver(false); acceptFile(e.dataTransfer.files?.[0]) }}
              className={`w-full rounded-[20px] border-2 border-dashed px-7 py-8 text-center transition-colors ${
                dragOver ? 'border-forest-green bg-forest-green-wash' : 'border-forest-green/35 bg-forest-green-ghost hover:border-forest-green hover:bg-forest-green-wash'
              }`}
            >
              <div className="w-15 h-15 rounded-[17px] bg-canvas border border-forest-green/20 flex items-center justify-center mx-auto mb-4 text-forest-green" style={{ boxShadow: '0 6px 16px rgba(16,80,55,.10)' }}>
                <FileIcon size={28} up />
              </div>
              <p className="text-[18px] font-extrabold text-ink mb-1">{dragOver ? '여기에 놓으세요' : '논문 PDF를 끌어다 놓으세요'}</p>
              <p className="text-[14px] font-medium text-ink-3">또는 클릭해서 파일 선택</p>
            </button>
            <p className="text-[12.5px] text-ink-3 mt-3 text-center">PDF 파일만 올릴 수 있습니다.</p>
          </>
        )}

        {/* 미발표 원고를 올릴지 망설이는 순간이 여기다 — 처리방침을 읽지 않는 사람에게도 보여야 한다 */}
        <p className="text-[12.5px] text-ink-3 mt-2 text-center leading-relaxed">
          올린 논문은 카드뉴스를 만드는 데만 쓰이고 <strong className="font-semibold text-ink-2">AI 학습에는 사용되지 않습니다.</strong>{' '}
          언제든 직접 삭제할 수 있으며, 자세한 내용은{' '}
          <a href="/privacy" className="underline underline-offset-2 hover:text-ink-2">개인정보 처리방침</a>에서 확인할 수 있습니다.
        </p>

        {/* 아트디렉터에게 한마디 */}
        <div className="bg-canvas border border-border rounded-[20px] p-6 mt-4" style={cardShadow}>
          <div className="flex items-baseline gap-2 mb-1.5">
            <h2 className="text-[18px] font-extrabold text-ink tracking-[-0.01em]">아트디렉터에게 한마디</h2>
            <span className="text-[13px] text-ink-3 font-semibold">선택</span>
          </div>
          <p className="text-[13.5px] leading-relaxed text-ink-3 mb-5">비워도 괜찮아요. AI가 논문에 맞춰 알아서 정합니다.</p>

          <p className="text-[13px] font-bold text-ink-2 mb-2.5">💡 이렇게 말해보세요</p>
          <div className="flex flex-col gap-2 mb-5">
            {EXAMPLE_UTTERANCES.map((u) => (
              <button key={u} type="button" onClick={() => setStyle(u)}
                className="text-left bg-canvas border border-border rounded-xl px-4 py-3 text-[14px] font-medium text-ink-2 flex items-center gap-3 transition-all hover:border-forest-green hover:bg-forest-green-ghost hover:translate-x-[3px]">
                <span className="text-forest-green text-[20px] font-bold leading-none relative top-[3px] shrink-0" style={{ fontFamily: 'var(--font-serif)' }}>&ldquo;</span>
                <span>{u}</span>
              </button>
            ))}
          </div>

          <div className="flex flex-wrap gap-2 mb-4">
            {STYLE_CHIPS.map((c) => (
              <button key={c} type="button" onClick={() => setStyle(c)}
                className={`text-[13.5px] px-4 py-2 rounded-full border whitespace-nowrap transition-colors ${style === c ? 'bg-forest-green text-canvas border-forest-green font-bold' : 'bg-canvas border-border text-ink-2 font-semibold hover:border-forest-green/50'}`}>
                {c.split(':')[0]}
              </button>
            ))}
          </div>

          <textarea
            value={style} onChange={(e) => setStyle(e.target.value)}
            placeholder="색감·난이도·강조점, 뭐든 말로 지시하세요… (비워도 됩니다)"
            rows={2}
            className="block w-full min-h-[72px] text-[14.5px] leading-relaxed rounded-[14px] border border-border p-4 resize-y text-ink outline-none transition-shadow focus:border-forest-green focus:ring-4 focus:ring-forest-green-wash"
            style={{ background: 'var(--surface)' }}
          />
        </div>

        {/* 카드 수 */}
        <div className="bg-canvas border border-border rounded-[20px] px-6 pt-5 pb-5.5 mt-3.5" style={cardShadow}>
          <div className="flex items-baseline justify-between mb-4">
            <span className="text-[15px] font-bold text-ink">카드 수</span>
            <span className="text-[15px] font-extrabold text-forest-green-deep">{cardCount}장</span>
          </div>
          <input
            type="range" min={CARD_MIN} max={CARD_MAX} step={1} value={cardCount}
            onChange={(e) => setCardCount(Number(e.target.value))}
            className="deck-range w-full"
            style={{ background: `linear-gradient(to right, var(--accent) ${fillPct}, var(--border) ${fillPct})` }}
            aria-label="카드 수"
          />
          <div className="flex justify-between mt-2.5 px-0.5">
            {CARD_TICKS.map((n) => (
              <span key={n} className={`text-[12.5px] ${n === cardCount ? 'text-forest-green-deep font-extrabold' : 'text-ink-3 font-semibold'}`}>{n}</span>
            ))}
          </div>
        </div>

        {error && <p className="text-[13px] text-red-600 mt-4" role="alert">{error}</p>}

        {/* 생성 CTA */}
        <button
          onClick={submit} disabled={submitting}
          className="w-full mt-5 rounded-[15px] py-4 bg-forest-green hover:bg-forest-green-deep text-canvas font-extrabold text-[16.5px] tracking-[-0.01em] flex items-center justify-center gap-2.5 transition-colors disabled:opacity-80"
          style={{ boxShadow: '0 12px 26px rgba(16,90,60,.24)' }}
        >
          {submitting ? (
            <>
              <span className="deck-spinner" aria-hidden="true" />
              카드뉴스 만드는 중…
            </>
          ) : '카드뉴스 생성'}
        </button>
        {/* 신뢰 문구의 제자리 = 결심하는 순간 옆 */}
        <p className="text-center text-[12.5px] text-ink-3 mt-3 inline-flex items-center gap-1.5 w-full justify-center">
          <span className="text-forest-green-deep inline-flex"><CheckIcon size={12} stroke={3} /></span>
          모든 수치는 원문과 자동 대조됩니다 · 논문에 따라 2~5분
        </p>

      </div>
    </div>
  )
}

export default function DeckNewPage() {
  return (
    <AuthGuard>
      <DeckNewInner />
    </AuthGuard>
  )
}
