// MOCK_EDITOR_DATA — /editor/demo 라우트용 mock.
// 새 React 카드 컴포넌트(2026-06-01 Phase 2 migration)의 필드명과 정확히 일치.
// 12개 템플릿 모두 포함. 실제 논문(smartfarm 가상 데이터) 기반.

import type { ApiResponse } from '@/types/editor'

export const MOCK_EDITOR_DATA: ApiResponse = {
  filename: 'kim2024_smartfarm_review.pdf',
  cardData: {
    theme: { primary: '#16A34A', dark: '#166534' },
    recommended_theme_key: 'forest_green',
    cards: [
      // 01 — cover
      {
        card_num: 1,
        template_type: 'cover',
        fields: {
          edition: { value: 'KITECH Research Note · 2026' },
          title: { value: '스마트팜 기반 식물 생장 최적화 연구', confidence: 'high' },
          subtitle: { value: '온도·습도 통합 제어 시스템의 성능 검증', confidence: 'high', source: { section: 'Abstract', page: 1 } },
          org: { value: 'KITECH 스마트제조연구부문' },
        },
      },

      // 02 — hook
      {
        card_num: 2,
        template_type: 'hook',
        fields: {
          title: { value: '수경재배 시스템의 23%가 실패한다면, 무엇이 잘못된 걸까?', confidence: 'high' },
          highlight: { value: '핵심은 단일 센서로는 환경 변화에 즉응할 수 없다는 것.', confidence: 'high' },
          body: { value: '본 연구는 다중 센서 융합으로 이 한계를 넘어선 첫 검증 사례를 제시한다.', confidence: 'medium', source: { section: 'Introduction', page: 2 } },
          source_credit: { value: 'KITECH Lab, 2026' },
        },
      },

      // 03 — problem
      {
        card_num: 3,
        template_type: 'problem',
        fields: {
          title: { value: '왜 이 연구가 필요한가?', confidence: 'high' },
          body: {
            value: '기존 단일 센서 기반 스마트팜은 평균 23%의 제어 실패율을 보이며, 이로 인한 작물 손실은 연간 약 340억 원에 이른다.',
            confidence: 'medium',
            risk_level: 'HIGH',
            source: { section: 'Introduction', page: 2 },
          },
          emphasis: { value: '핵심 격차: 환경 변화에 대한 실시간 대응력', confidence: 'high' },
        },
      },

      // 04 — definition
      {
        card_num: 4,
        template_type: 'definition',
        fields: {
          term: { value: '다중 센서 융합 제어', confidence: 'high' },
          term_detail: { value: 'Multi-Sensor Fusion Control' },
          definition_text: { value: '온도·습도·CO₂·조도를 동시에 측정하고 칼만 필터·퍼지 제어를 결합해 단일 센서의 노이즈를 보정하는 제어 방식.', confidence: 'high', source: { section: 'Methods', page: 3 } },
          body: { value: '이 방식은 센서 하나가 일시적 오작동을 일으켜도 다른 센서가 보완해 시스템 전체의 안정성을 유지한다.', confidence: 'medium' },
        },
      },

      // 05 — circle3
      {
        card_num: 5,
        template_type: 'circle3',
        fields: {
          title: { value: '세 가지 핵심 구성 요소', confidence: 'high' },
          c1: { value: '센서 노드:4종 동시 측정' },
          c2: { value: '필터 계층:칼만+퍼지' },
          c3: { value: '제어 루프:200ms 주기' },
          body: { value: '세 단계가 직렬로 연결되어 데이터 수집 → 노이즈 제거 → 환경 보정의 폐쇄 루프를 구성한다.', confidence: 'high' },
        },
      },

      // 06 — flow
      {
        card_num: 6,
        template_type: 'flow',
        fields: {
          title: { value: '연구 방법 — 4단계 파이프라인', confidence: 'high' },
          steps_text: { value: '다중 센서 데이터 수집 (온도·습도·CO₂·조도) · 칼만 필터 기반 노이즈 제거 · 퍼지 제어 알고리즘 적용 · 피드백 루프로 실시간 보정', confidence: 'high', source: { section: 'Methods', page: 4 } },
        },
      },

      // 07 — compare2
      {
        card_num: 7,
        template_type: 'compare2',
        fields: {
          title: { value: '단일 센서 vs 다중 센서 융합', confidence: 'high' },
          subtitle: { value: '제어 정확도·안정성 비교', confidence: 'high' },
          label_a: { value: '기존 (단일 센서)' },
          label_b: { value: '제안 (다중 센서 융합)' },
          points_a: { value: '제어 실패율 23% · 평균 응답 시간 1.4초 · 센서 고장 시 시스템 정지' },
          points_b: { value: '제어 실패율 6.2% · 평균 응답 시간 0.3초 · 단일 센서 고장에도 동작 유지' },
        },
      },

      // 08 — grid4
      {
        card_num: 8,
        template_type: 'grid4',
        fields: {
          title: { value: '네 가지 검증 지표', confidence: 'high' },
          subtitle: { value: '실험실 대비 실증 농가 결과', confidence: 'high' },
          item1_label: { value: '온도 안정도' },
          item1_sub: { value: '±0.4°C 이내' },
          item2_label: { value: '습도 추종' },
          item2_sub: { value: '오차 2% 미만' },
          item3_label: { value: '에너지 효율' },
          item3_sub: { value: '18% 절감' },
          item4_label: { value: '작물 수율' },
          item4_sub: { value: '12% 향상' },
        },
      },

      // 09 — data (bar chart)
      {
        card_num: 9,
        template_type: 'data',
        fields: {
          title: { value: '제어 실패율 비교 (5개 실증 농가)', confidence: 'high' },
          data_unit: { value: '단위: %' },
          bars: { value: '농가 A:24|농가 B:21|농가 C:6.2|농가 D:5.8|농가 E:7.1', confidence: 'high' },
          bar_max: { value: '30' },
          source: { value: 'Results · Table 2, p.8', risk_level: 'CRITICAL', source: { section: 'Results · Table 2', page: 8 } },
        },
      },

      // 10 — showcase
      {
        card_num: 10,
        template_type: 'showcase',
        fields: {
          title: { value: '실증 농가 적용 사례', confidence: 'high' },
          body: { value: '경기 안성·충북 음성·전북 익산 3개 실증 농가에서 6개월간 운영한 결과, 단일 센서 대비 평균 73.2%의 제어 정확도 향상을 확인했다.', confidence: 'high', source: { section: 'Results', page: 9 } },
          icon1: { value: '안성:6개월' },
          icon2: { value: '음성:6개월' },
          icon3: { value: '익산:6개월' },
        },
      },

      // 11 — closing
      {
        card_num: 11,
        template_type: 'closing',
        fields: {
          title_white: { value: '향후 과제는' },
          title_accent: { value: '딥러닝 예측 제어' },
          body: { value: '실시간 적응형 스마트팜 시스템으로 확장하기 위해, 환경 변화 예측 모델과 다중 센서 융합을 통합하는 후속 연구를 진행한다.', confidence: 'high', source: { section: 'Conclusion', page: 12 } },
        },
      },

      // 12 — brand
      {
        card_num: 12,
        template_type: 'brand',
        fields: {
          tagline: { value: 'PolyInsight' },
          body: { value: '논문 한 편이 카드뉴스 한 세트가 되는, 가장 빠른 길.' },
          cta: { value: 'polyinsight.kr · 무료로 시작하기' },
          footer_text: { value: 'PolyInsight · KITECH Research Note' },
        },
      },
    ],
  },
}
