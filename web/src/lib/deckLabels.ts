// 저작 덱 HTML에서 카드별 스토리보드 라벨을 뽑는다(좌측 네비 = 서사 아크 표면화).
//
// 1순위 — `data-role`: 저작 모델이 카드 div에 명시한 역할(신규 계약). §1 안전한 **메타데이터**라
//   형태를 가두지 않으면서 라벨의 정본을 복원한다. 강건(정규식 추측 불필요).
// 2순위(구덱 폴백) — kicker "ROLE · 부제"의 한글 부제.
//   ★실측 교훈: 역할은 **영문**(WHY·HOW·THE NUMBER·FEEL IT…)이고 한글은 **부제**다.
//   구 코드는 '한글 · X'로 가정 → 영문 역할을 놓치고, 본문 middot(치약·세안제)·소속 표기(한글·한글)를
//   오매치하거나 12자로 잘라 라벨이 깨졌다("세안제"·"술연구원 융합기술연구소"). 이제 영문역할 뒤
//   한글 부제를 취하고 **단어 경계로 다듬어**(중간 잘림·본문 번짐 최소화) 쓴다.
//   매치 없으면 첫 장 '표지', 나머지는 null(레일이 'CARD 0N'로 폴백 — 깨진 라벨보다 정직).

const MIDDOT = '[\\u00B7\\u2027\\u30FB]'
const ROLE_ATTR = /data-role\s*=\s*["']([^"']{1,20})["']/i
// 영문 역할 kicker(ROLE · ) 뒤의 한글 부제. 소속(한글·한글)은 영문 선행이 없어 안 걸린다.
const KICKER = new RegExp(`[A-Za-z][A-Za-z\\s]{0,18}${MIDDOT}\\s*([가-힣][가-힣0-9\\s]{1,16})`)

// 라벨을 단어 경계로 다듬음(≤max, 중간 글자 잘림 방지). 실 부제는 대개 4~9자.
function tidy(s: string, max = 11): string {
  const t = s.trim()
  if (t.length <= max) return t
  const cut = t.slice(0, max)
  const sp = cut.lastIndexOf(' ')
  return (sp >= 4 ? cut.slice(0, sp) : cut).trim()
}

export function extractCardLabels(html: string | null | undefined): (string | null)[] {
  if (!html) return []
  const blocks = html.split(/(?=data-screen-label)/).slice(1)
  return blocks.map((block, i) => {
    const gt = block.indexOf('>')
    const head = gt >= 0 ? block.slice(0, gt + 1) : block.slice(0, 300) // 여는 div 태그
    const role = head.match(ROLE_ATTR)?.[1]?.trim()
    if (role) return role                        // 1순위: 명시 역할
    if (i === 0) return '표지'                    // 첫 장 = 표지 관례(마스트헤드 middot 오매치 전에)
    const body = gt >= 0 ? block.slice(gt + 1) : block
    const text = body.replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 200)
    const sub = text.match(KICKER)?.[1]
    if (sub) {
      const label = tidy(sub)
      if (label.length >= 2) return label
    }
    return null                                  // 레일이 'CARD 0N' 폴백
  })
}
