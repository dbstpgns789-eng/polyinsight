// MOCK_EDITOR_DATA — /editor/demo · /render/demo 라우트용 mock.
// 신 8뼈대(skin/skeleton 디자인 시스템) 단일 세트 데모. 셀룰로스–COF 미세구슬 논문 스토리.
// 서사 순서: 표지 → 진술 → 혁신 → 과정 → 성능 → 근거 → 응용 → 마무리.

import type { ApiResponse } from '@/types/editor'

export const MOCK_EDITOR_DATA: ApiResponse = {
  filename: 'cellulose_cof_microbead_2024.pdf',
  cardData: {
    theme: { primary: '#16A34A', dark: '#166534' },
    recommended_theme_key: 'forest_green',
    cards: [
      // 1 — 표지 cover_v2
      { card_num: 1, template_type: 'cover_v2', fields: {
        eyebrow: { value: 'KITECH Research Note · 2026' },
        headline: { value: '플라스틱을 *대체*하는 셀룰로스 미세구슬', confidence: 'high' },
        subtitle: { value: 'COF 복합화로 강도와 생분해성을 동시에', confidence: 'high' },
        org: { value: 'KITECH 친환경소재연구부문' },
      } },
      // 2 — 진술 statement
      { card_num: 2, template_type: 'statement', fields: {
        eyebrow: { value: '문제 제기' },
        headline: { value: '왜 친환경 플라스틱은 *약할*까?', confidence: 'high' },
        body: { value: '생분해성 소재는 대개 강도가 낮아 구조재로 쓰기 어렵다. 이 한계가 상용화를 막아 왔다.', confidence: 'medium', source: { section: 'Introduction', page: 2 } },
      } },
      // 3 — 혁신 feature
      { card_num: 3, template_type: 'feature', fields: {
        eyebrow: { value: '핵심 혁신' },
        headline: { value: '셀룰로스에 *COF*를 짜 넣다', confidence: 'high' },
        body: { value: '공유결합 유기골격체(COF)를 셀룰로스 매트릭스에 복합해, 미세구슬 형태로 강도와 다공성을 함께 얻었다.', confidence: 'high', source: { section: 'Methods', page: 4 } },
      } },
      // 4 — 과정 process_v2
      { card_num: 4, template_type: 'process_v2', fields: {
        eyebrow: { value: '제작 방법' },
        headline: { value: '세 단계로 만든다', confidence: 'high' },
        steps: { value: '셀룰로스 용액에 COF 전구체 분산|에멀전법으로 미세구슬 성형|동결건조로 다공 구조 고정', confidence: 'high', source: { section: 'Methods', page: 5 } },
        caption: { value: '전 과정 무용매·저온 — 친환경 공정', confidence: 'medium' },
      } },
      // 5 — 성능 bigstat_compare
      { card_num: 5, template_type: 'bigstat_compare', fields: {
        eyebrow: { value: '성능 검증' },
        headline: { value: '기존 플라스틱보다 *더 단단*하다', confidence: 'high' },
        stat_value: { value: '238', confidence: 'high', source: { section: 'Results', page: 7 } },
        stat_unit: { value: 'MPa' },
        stat_caption: { value: '셀룰로스–COF 복합 미세구슬의 압축 강도', confidence: 'high' },
        bars: { value: '우리 복합 구슬:238:1|폴리프로필렌(PP):199:0|무보강 셀룰로스:142:0', confidence: 'high', source: { section: 'Results · Table 1', page: 7 } },
        source_ref: { value: '출처: Cellulose (2024) · Results', source: { section: 'Results', page: 7 } },
      } },
      // 6 — 근거 reasons
      { card_num: 6, template_type: 'reasons', fields: {
        eyebrow: { value: '왜 이 소재인가' },
        headline: { value: '셀룰로스를 고른 *세 가지* 이유', confidence: 'high' },
        reasons: { value: '풍부함:지구상 가장 많은 천연 고분자, 원료 걱정이 없다|생분해성:토양·해양에서 완전 분해된다|기능화 용이:표면 -OH로 COF 결합이 쉽다', confidence: 'high', source: { section: 'Introduction', page: 3 } },
      } },
      // 7 — 응용 grid_v2
      { card_num: 7, template_type: 'grid_v2', fields: {
        eyebrow: { value: '응용 분야' },
        headline: { value: '어디에 *쓰일까*?', confidence: 'high' },
        items: { value: '포장재:일회용 플라스틱 대체|흡착소재:중금속·염료 제거|약물전달:다공성 캡슐|단열재:경량 구조재', confidence: 'high', source: { section: 'Discussion', page: 10 } },
        body: { value: '강도·다공성·생분해성의 조합이 응용 폭을 넓힌다.', confidence: 'medium' },
      } },
      // 8 — 마무리 closing_v2
      { card_num: 8, template_type: 'closing_v2', fields: {
        eyebrow: { value: '맺음말' },
        headline: { value: '다음은 *대량 생산* 검증', confidence: 'high' },
        body: { value: '실험실 성과를 파일럿 규모로 확장해 경제성과 균일도를 확인하는 후속 연구를 진행한다.', confidence: 'high', source: { section: 'Conclusion', page: 12 } },
        source_ref: { value: '출처: Cellulose (2024) · Conclusion' },
      } },
      // ── 확장 레이아웃 데모 (9~14) ──
      // 9 — 개념 풀이 definition
      { card_num: 9, template_type: 'definition', fields: {
        eyebrow: { value: '개념' },
        headline: { value: '*COF*가 뭐길래?' },
        body: { value: '분자를 그물처럼 단단히 엮은 다공성 물질이에요. 구멍이 아주 많아 가볍고, 표면적이 넓어 무언가를 잘 담습니다.' },
        caption: { value: '스펀지처럼 구멍 많은, 그런데 단단한 그물' },
      } },
      // 10 — 이미지 히어로 image_hero
      { card_num: 10, template_type: 'image_hero', fields: {
        eyebrow: { value: '구조 관찰' },
        headline: { value: '전자현미경으로 본 *미세구슬*' },
        caption: { value: '균일한 구형 + 다공성 표면 (SEM 이미지)' },
      } },
      // 11 — 콜아웃 callout
      { card_num: 11, template_type: 'callout', fields: {
        eyebrow: { value: '한 줄 요약' },
        headline: { value: '플라스틱은 안 썩고, 셀룰로스는 약했다 — 그 둘을 *합쳤다*' },
        body: { value: '강도와 생분해성, 드디어 동시에.' },
      } },
      // 12 — 멀티 수치 multistat
      { card_num: 12, template_type: 'multistat', fields: {
        eyebrow: { value: '핵심 지표' },
        headline: { value: '숫자로 보는 *성능*' },
        stats: { value: '압축강도:238:MPa|기존 대비:+19.6:%|기공률:62:%|분해 기간:90:일' },
        source_ref: { value: '출처: Cellulose (2024) · Results' },
      } },
      // 13 — 인용 quote
      { card_num: 13, template_type: 'quote', fields: {
        eyebrow: { value: '연구자의 말' },
        quote: { value: '약한 게 친환경의 숙명은 *아니다*.' },
        attribution: { value: '— 연구책임자, KITECH' },
      } },
      // 14 — 비교 표 compare_table
      { card_num: 14, template_type: 'compare_table', fields: {
        eyebrow: { value: '비교' },
        headline: { value: '기존 플라스틱 vs *우리 소재*' },
        col_a: { value: '우리 소재' },
        col_b: { value: '폴리프로필렌' },
        rows: { value: '압축강도:238 MPa:199 MPa|생분해성:완전 분해:불가|원료:식물:석유' },
        source_ref: { value: '출처: Cellulose (2024)' },
      } },
    ],
  },
}
