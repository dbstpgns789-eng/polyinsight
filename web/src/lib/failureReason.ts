// 실패 원인 분류 — 엉뚱한 탓을 하지 않기 위해.
//
// 실전 버그(2026-07-14): 실패 화면이 **어떤 실패든** "스캔본(이미지) PDF는 텍스트를 못 읽어요"를
// 무조건 붙이고 있었다. 크레딧이 소진돼 실패했는데도 유저는 자기 PDF를 의심하게 됐다.
// 지금까지 실패한 적이 없어서 아무도 이 화면을 안 봤고, 크레딧이 떨어지자 드러났다.
//
// **운영자가 고칠 문제를 유저 탓처럼 보이게 하는 건 최악의 에러 화면이다.**

export type FailureKind = 'credit' | 'scan' | 'unknown'

export interface Failure {
  kind: FailureKind
  title: string     // 무슨 일이 일어났나
  hint: string      // 무엇을 하면 되나
}

const CREDIT_MARKERS = [
  'credit balance',
  'insufficient credit',
  'ai 사용량',
  '사용량이 한도',
]

export function failureReason(warnings?: string[]): Failure {
  const list = warnings ?? []
  const joined = list.join(' ').toLowerCase()

  if (CREDIT_MARKERS.some((m) => joined.includes(m))) {
    return {
      kind: 'credit',
      title: '지금은 카드뉴스를 만들 수 없습니다',
      hint: 'AI 사용량이 한도에 도달했습니다. 운영자가 곧 복구합니다 — 잠시 후 다시 시도해 주세요. (업로드하신 논문에는 문제가 없습니다.)',
    }
  }

  const abort = list.find((x) => x.startsWith('ABORT-S1'))
  if (abort) {
    return {
      kind: 'scan',
      title: '논문에서 글자를 읽지 못했습니다',
      hint: '스캔본(이미지) PDF는 텍스트를 못 읽어요 — 텍스트가 살아있는 PDF로 다시 시도해 주세요.',
    }
  }

  const err = list.find((x) => x.startsWith('ERR-') || x.startsWith('ABORT-'))
  return {
    kind: 'unknown',
    title: err ? err.replace(/^(ABORT|ERR)-[A-Z0-9]*:\s*/, '') : '카드뉴스를 만들지 못했습니다',
    hint: '잠시 후 다시 시도해 주세요. 계속 실패하면 다른 논문으로 시도해 보세요.',
  }
}
