import type { ApiResponse } from '@/types/editor'

export const MOCK_EDITOR_DATA: ApiResponse = {
  filename: 'kim2024_smartfarm_review.pdf',
  cardData: {
    cards: [
      {
        card_num: 1,
        template_type: 'cover',
        fields: {
          title: {
            value: '스마트팜 기반 식물 생장 최적화 연구',
            confidence: 'high',
          },
          subtitle: {
            value: '온도·습도 통합 제어 시스템의 성능 검증',
            confidence: 'high',
            source: { section: 'Abstract', page: 1 },
          },
          institution: {
            value: 'KITECH 스마트제조연구부문',
            confidence: 'high',
          },
        },
      },
      {
        card_num: 2,
        template_type: 'problem',
        fields: {
          section_title: {
            value: '왜 이 연구가 필요한가?',
            confidence: 'high',
          },
          body: {
            value: '기존 수경재배 시스템의 온도·습도 제어 실패율이 23%에 달하며, 이로 인한 작물 손실이 연간 약 340억 원에 이른다. 현행 단일 센서 기반 제어 방식은 환경 변화에 즉각 대응하지 못하는 구조적 한계를 가진다.',
            confidence: 'medium',
            risk_level: 'HIGH',
            source: { section: 'Introduction', page: 2 },
          },
        },
      },
      {
        card_num: 3,
        template_type: 'data',
        fields: {
          section_title: {
            value: '핵심 성과 수치',
            confidence: 'high',
          },
          stat_main: {
            value: '73.2%',
            confidence: 'high',
            source: { section: 'Results · Table 2', page: 8 },
          },
          stat_desc: {
            value: '다중 센서 융합 제어 적용 후 제어 정확도 향상률',
            confidence: 'high',
          },
          stat_sub: {
            value: '실패율 23% → 6.2%로 감소 (기존 대비 73% 개선)',
            confidence: 'high',
            risk_level: 'CRITICAL',
            source: { section: 'Results · Table 3', page: 9 },
          },
        },
      },
      {
        card_num: 4,
        template_type: 'flow',
        fields: {
          section_title: {
            value: '연구 방법 — 4단계 파이프라인',
            confidence: 'high',
          },
          step1: { value: '① 다중 센서 데이터 수집 (온도/습도/CO₂/조도)', confidence: 'high' },
          step2: { value: '② 칼만 필터 기반 노이즈 제거', confidence: 'high' },
          step3: { value: '③ 퍼지 제어 알고리즘 적용', confidence: 'medium', source: { section: 'Methods', page: 4 } },
          step4: { value: '④ 피드백 루프로 실시간 보정', confidence: 'high' },
        },
      },
      {
        card_num: 5,
        template_type: 'closing',
        fields: {
          section_title: {
            value: '결론 및 향후 과제',
            confidence: 'high',
          },
          body: {
            value: '제안한 다중 센서 융합 시스템은 기존 단일 센서 방식 대비 제어 정확도를 73.2% 향상시켰다. 향후 딥러닝 기반 예측 제어를 통합하여 실시간 적응형 스마트팜 시스템으로 확장할 계획이다.',
            confidence: 'high',
            source: { section: 'Conclusion', page: 12 },
          },
        },
      },
    ],
  },
}
