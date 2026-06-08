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
    ],
  },
}
