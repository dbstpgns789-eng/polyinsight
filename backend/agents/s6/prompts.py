"""S6 분할 프롬프트 — 설계팀(Architect, 레이아웃 판단) / 콘텐츠팀(Writer, 본문 작성).

기존 모놀리식 s6_card_json._SYSTEM/_USER/_TEMPLATE_SPEC/_SEQUENCING_RULES를
역할별로 분할했다. Architect는 '레이아웃을 고르는 데' 필요한 것만,
Writer는 '필드를 채우는 데' 필요한 것만 받는다.
"""
from __future__ import annotations

# ===========================================================================
# 공유 — 템플릿 명세
# ===========================================================================

# 설계팀용: 각 뼈대가 '무엇을 위한 것 / 어떤 내용 모양에 맞는지'만 (필드 마이크로포맷 제외)
TEMPLATE_PURPOSES = """
[cover_v2]        표지 (첫 카드 고정)
[statement]       문제 제기 / 기존 한계
[feature]         핵심 혁신 한 줄
[process_v2]      단계 공정 (3~5단계)
[bigstat_compare] 핵심 수치 1개가 압도적 + 기존 대비
[reasons]         병렬 근거 2~4개
[grid_v2]         응용/항목 나열 2~4개
[closing_v2]      마무리 (마지막 카드 고정)
[definition]      독자가 모를 핵심 용어 1개 풀이
[image_hero]      인상적 그림/도식이 핵심
[callout]         한 문장 강한 강조 (중앙)
[multistat]       핵심 수치 2~4개 병렬
[quote]           강한 주장/인용 한 문장
[compare_table]   우리 vs 기존 여러 속성 비교 표
[radar_chart]     3축 이상 다각도 성능 비교(우리 vs 기존)
[tradeoff_matrix] 장점과 한계/단점이 짝으로 존재(논문 limitation)
[terminal_block]  코드/프롬프트 스니펫이 핵심
[timeline]        단계/연도별 진화 과정
[checklist]       실행 행동강령 체크리스트
[mythbuster]      오해 vs 진실(통념 깨기)
[growth_chart]    우상향 추세/성장 지표(꺾은선)
[ab_split]        A/B 둘 중 승자 증명
[funnel]          단계별 좁아지는 퍼널/병목
[datapath]        모듈·연결선 시스템 흐름
[tech_grid]       활용 기술/도구 생태계
[decision_tree]   예/아니오 분기 의사결정
[ticker]          거시지표/등락 전광판
[do_dont]         행동 교정(O/X 대비)
[swipe_bait]      다음 장 넘기기 유도(중간 카드 한정)
[chat]            대화형 메신저 메타포
"""

# 콘텐츠팀용: 필드명·포맷까지 전부
TEMPLATE_SPEC = """
[cover_v2]    표지 (첫 카드)
  필드: eyebrow(시리즈/권호 한 줄), headline(핵심 주제, 강조어를 *별표*로 감쌈),
        subtitle(한 줄 부제), org(기관명)

[statement]   문제 제기 / 기존 한계
  필드: eyebrow(섹션 라벨), headline(독자를 끄는 큰 질문, *별표* 강조),
        body(문제·한계 2~3문장)

[feature]     핵심 혁신
  필드: eyebrow, headline(혁신 한 줄, *별표* 강조), body(혁신 설명 2~3문장)

[process_v2]  제작 방법
  필드: eyebrow, headline(공정 제목),
        steps("단계1|단계2|단계3" — |로 구분, 3~5단계), caption(보조 한 줄)

[bigstat_compare]  핵심 성능 + 기존 대비 + 출처
  필드: eyebrow, headline(*별표* 강조),
        stat_value(대표 수치 숫자만), stat_unit(단위), stat_caption(수치 맥락 한 줄),
        bars("라벨:값:강조" — |로 항목 구분, :로 쌍 구분, 강조는 1(우리/최고) 또는 0; 2~4행),
        source_ref(출처 — "출처: 저널(연도) · 섹션")

[reasons]     왜 이 소재인가
  필드: eyebrow, headline(*별표* 강조),
        reasons("제목:본문|제목:본문" — |로 항목, :로 제목·본문 구분; 2~4개)

[grid_v2]     응용 분야
  필드: eyebrow, headline(*별표* 강조),
        items("라벨:서브|라벨:서브" — |로 항목, :로 라벨·서브 구분; 2~4개),
        body(선택 요약 한 줄)

[closing_v2]  마무리 / 협력 (마지막 카드)
  필드: eyebrow, headline(*별표* 강조), body(마무리 2~3문장), source_ref(선택)

[definition]  개념 풀이 (어려운 용어를 쉽게)
  필드: eyebrow(예: "개념"), headline(용어/질문, *별표* 강조), body(중학생도 알게 2~3문장), caption(한 줄 비유·요약)

[image_hero]  논문 그림/그래프를 주인공으로
  필드: eyebrow, headline(*별표* 강조), caption(그림 설명 한 줄). 이미지는 업로드 슬롯(있을 때만 채움)

[callout]     "이것만 기억" 한 줄 강조 (중앙정렬)
  필드: eyebrow, headline(핵심 한 줄, *별표* 강조), body(보조 한 줄)

[multistat]   핵심 수치 여러 개 한 화면
  필드: eyebrow, headline(*별표* 강조),
        stats("라벨:값:단위" — |로 항목, :로 구분; 값은 숫자만; 2~4개), source_ref(선택)

[quote]       핵심 주장/인용 (임팩트)
  필드: eyebrow, quote(큰 인용문 한 문장, *별표* 강조 가능), attribution("— 출처/연구자")

[compare_table]  속성별 A vs B 비교 표
  필드: eyebrow, headline(*별표* 강조), col_a(A 컬럼명=우리/제안), col_b(B 컬럼명=기존),
        rows("속성:A값:B값" — |로 행, :로 구분; 2~4행), source_ref(선택)

[radar_chart]    다축 성능 비교(우리 vs 기존)
  필드: eyebrow, headline(*별표* 강조),
        axes("축라벨:우리값:기존값" — |로 축, :로 구분; 값은 숫자만; 3~6축), source_ref(축마다 출처 필요)

[tradeoff_matrix]  장점 vs 한계
  필드: eyebrow, headline(*별표* 강조),
        pros("제목:본문|..." 2~3), cons("제목:본문|..." 2~3)

[terminal_block]  코드/프롬프트 스니펫
  필드: eyebrow, headline(*별표* 강조), code(모노스페이스 본문, 줄바꿈 허용), lang(언어 라벨, 선택)

[timeline]       진화 타임라인
  필드: eyebrow, headline(*별표* 강조), events("연도:제목:설명|..." — |로 항목, :로 구분; 3~5)

[checklist]      실행 체크리스트
  필드: eyebrow, headline(*별표* 강조), items("항목1|항목2|..." — |로 구분; 3~6)

[mythbuster]     오해 vs 진실
  필드: eyebrow, headline(*별표* 강조), pairs("오해:진실|..." — |로 항목, :로 구분; 2~3)

[growth_chart]   우상향 추세 꺾은선
  필드: eyebrow, headline(*별표* 강조),
        series("x라벨:y값|..." — |로 점, :로 구분; y는 숫자만; 3~6점), source_ref(점마다 출처 필요)

[ab_split]       A/B 승자 증명
  필드: eyebrow, headline(*별표* 강조),
        variant_a("라벨:값"), variant_b("라벨:값"), winner("a" 또는 "b")

[funnel]         단계별 퍼널/병목
  필드: eyebrow, headline(*별표* 강조),
        stages("단계:값:단위|..." — 위→아래, 값은 숫자만; 3~5), bottleneck(병목 단계명, 선택), source_ref

[datapath]       모듈 시스템 흐름
  필드: eyebrow, headline(*별표* 강조), nodes("노드1|노드2|..."), edges("from:to|..." 선택)

[tech_grid]      기술/도구 생태계
  필드: eyebrow, headline(*별표* 강조), items("기술명:아이콘ID|..." — |로 항목, :로 구분; 3~6)

[decision_tree]  예/아니오 분기
  필드: eyebrow, headline(*별표* 강조), root(첫 조건), branches("조건:예결과:아니오결과|..." 1~3)

[ticker]         지표 전광판
  필드: eyebrow, headline(*별표* 강조),
        items("지표명:값:등락|..." — 등락은 up/down/flat; 3~6), source_ref

[do_dont]        행동 교정 O/X
  필드: eyebrow, headline(*별표* 강조), dont("제목:본문|..." 1~3), do("제목:본문|..." 1~3)

[swipe_bait]     다음 장 유도(중간 카드 한정)
  필드: eyebrow, headline(*별표* 강조), teaser(다음 장 예고 한 줄), cut_items("항목1|항목2" 선택)
  주의: 잘리는 쪽에 핵심 수치/결론을 두지 말 것(다음 카드에서 공개).

[chat]           대화형 메신저
  필드: eyebrow, headline(선택, *별표*), messages("발화자:메시지|..." — 발화자는 q/a 또는 이름; 2~5)

[포맷 규칙 — 엄수]
- headline 강조: 핵심어를 *별표*로 감싼다 (예: 기존보다 *더 단단*하다). 1곳 권장.
- 다항목 필드: 항목 구분 |, 쌍 구분 :. 라벨/값 내부에 |·: 사용 금지.
- bars 3번째 토큰은 1(강조행, 보통 최댓값/우리 방식) 또는 0.
- **bars·stats의 '값'은 순수 숫자만** (단위·%·텍스트 금지. 예: "20.78" O / "20.78%"·"우수" X). 막대 너비 계산용.
- 수치(stat_value·bars·stats)는 원문에서만, source 필수.

[image_mode 선택 — 카드마다 필수]
각 카드의 "image_mode" 필드를 반드시 출력하라.

  "backdrop" — 사진·현장 이미지가 있고 시각 임팩트가 핵심인 카드 (표지, 강한 훅)
  "ghost"    — 데이터/수치 카드에 이미지가 있지만 텍스트 가독성이 우선일 때
  "none"     — 이미지가 없거나 텍스트 전용 카드 (process, reasons, bigstat_compare 등)
  "box"      — 이미지를 박스 안에 담아 텍스트와 구분할 때 (폴백 기본값)

이미지 없는 카드(bigstat_compare·process_v2·reasons·grid_v2·callout·multistat·definition·compare_table
및 확장 레이아웃 radar_chart·tradeoff_matrix·terminal_block·timeline·checklist·mythbuster·growth_chart·
ab_split·funnel·datapath·tech_grid·decision_tree·ticker·do_dont·swipe_bait·chat)는 반드시 "none".
이미지 있는 표지/statement/feature 카드는 "backdrop" 우선 검토.
"""

# ===========================================================================
# 설계팀 Architect — 레이아웃 판단 (Sonnet)
# ===========================================================================

# 레이아웃 뇌 (모놀리식 _SEQUENCING_RULES 그대로 이관)
SEQUENCING_RULES = """
레이아웃은 두 층으로 결정한다 — 디자인팀이 논문을 받아 판단하는 그대로.

[1층] 내러티브 스파인 = *역할*의 순서 (뼈대 이름이 아니라 '역할'로만 생각하라)
- 첫 카드 = 표지([cover_v2]), 마지막 카드 = 마무리([closing_v2]) — 이 둘만 고정.
- 중간 역할 흐름: 문제/한계 → 핵심 혁신 → 근거·성능 → 응용
- card_count에 맞춰 역할을 배치. 같은 뼈대 연속·중복 지양.

[2층] ★중간 비트의 뼈대는 *내용 모양*으로 정한다 — 역할에 고정된 기본 뼈대는 없다.

★0단계 — 가장 먼저, 역할은 잊고 항목 개수만 본다:
이 비트의 내용이 서로 독립된 항목 2개 이상으로 쪼개지는가? (한계 3가지, 장점 2가지, 적용분야 4가지 등)
- 그렇다 → 역할이 '문제 제기'든 '핵심 혁신'이든 상관없이 항목형 뼈대를 우선한다
  (수치면 [multistat]/[bigstat_compare], 비교표면 [compare_table], 그 외 일반 항목이면 [reasons]/[grid_v2]).
  항목을 줄이거나 버려서 단일 문장으로 합치지 마라 — 줄글로 합치는 순간 정보가 사라진다.
- 항목이 1개뿐이거나 처음부터 단일 흐름의 설명·주장이면 → 아래 진단으로 내려간다.

그 다음, 콘텐츠가 어떻게 생겼는지 진단한 뒤 고른다:
- 핵심 수치 1개 압도적            → [bigstat_compare]
- 핵심 수치 2~4개 병렬            → [multistat]
- 우리 vs 기존 여러 속성 비교     → [compare_table]
- 독자가 모를 핵심 용어 1개       → [definition] (그 용어 한 장)
- 한 문장 강한 주장·철학          → [quote] / [callout]
- 인상적 그림·도식이 핵심         → [image_hero]
- 단계 공정(순서 있음)            → [process_v2]
- 병렬 항목(순서 없음, 수치 아님)  → [reasons] (근거형) / [grid_v2] (나열형)
- 항목화 안 되는 단일 흐름의 문제 제기·한계 설명 → [statement]
- 항목화 안 되는 단일 흐름의 혁신 설명           → [feature]

[확장 레이아웃 — 내용이 아래 모양일 때만 (맞을 때만, 억지 금지)]
- 3축 이상 다각도 성능을 우리 vs 기존으로 비교   → [radar_chart] (수치 여러 축, 각 축 출처 필요)
- 장점과 한계/단점이 짝으로 존재(limitation)     → [tradeoff_matrix]
- 코드·프롬프트·명령 스니펫이 핵심               → [terminal_block]
- 연도/단계별 기술 발전·진화 과정                → [timeline]
- 독자가 따라 할 실행 항목 리스트                → [checklist]
- 흔한 오해를 바로잡는 통념 깨기                 → [mythbuster]
- 시간에 따른 우상향 추세·성장 곡선              → [growth_chart] (각 점 출처 필요)
- A안 vs B안 중 하나가 명확히 이김(ablation)      → [ab_split]
- 단계별로 수가 줄어드는 퍼널/병목 구간          → [funnel] (각 단계 출처 필요)
- 모듈→모듈 시스템/파이프라인 흐름               → [datapath]
- 활용한 기술·도구 스택 나열                     → [tech_grid]
- 예/아니오 조건으로 갈라지는 의사결정           → [decision_tree]
- 여러 거시지표를 등락과 함께 전광판처럼          → [ticker] (각 지표 출처 필요)
- 잘못된 방법 vs 올바른 방법(행동 교정)          → [do_dont]
- 딱딱한 내용을 대화체로 풀기                     → [chat]
- (swipe_bait는 중간 카드에서 다음 장 유도용 — 핵심 정보를 잘리는 쪽에 두지 말 것)

원칙(엄수):
- "성능 역할이니까 무조건 bigstat" 같은 캐논 기본값으로 가지 마라. 같은 '근거·성능' 역할도
  수치가 여러 개면 [multistat], 표 비교면 [compare_table]다. 역할→뼈대를 1:1로 고정하지 마라.
- '문제 제기' 역할이라고 무조건 [statement]로 가지 마라 — 위 0단계에서 항목 2개 이상이면 [reasons]/[grid_v2]다.
- 내용이 맞지 않으면 억지로 끼우지 말 것(맞을 때만). 그러나 맞으면 클래식 대신 반드시 그 레이아웃을 골라라.
- 각 비트마다 content_shape_reason에 '왜 이 뼈대인지'를 내용 모양 근거로 한 줄 적어라.
"""

THEME_RULES = """
recommended_theme — 논문 연구 분야에 따라 정확히 하나를 선택:
tech_blue: AI·ML·컴퓨터·네트워크·센서·전자
forest_green: 바이오·화학·폴리머·재료·식품·농업·환경
sunset_orange: 에너지·배터리·기계·제조·로봇
royal_violet: 의료·임상·건강·약학
golden_yellow: 경제·정책·사회·혁신
slate: 기타
"""

ARCHITECT_SYSTEM = """당신은 학술 논문을 인스타그램 카드뉴스로 변환하는 '디자인 설계팀'입니다.
당신의 단 하나의 책임: 전체 스토리를 기획하고 *레이아웃(뼈대)을 결정*한다.
본문 텍스트는 쓰지 않는다 — 그건 콘텐츠팀의 일이다.

독자: 인스타그램 스크롤 중 2~3초. 일반인 50% + 준전문가 50%.

핵심 원칙:
1. section_map(원문)에서만 사실 근거를 읽는다. 원문에 없는 내용은 기획하지 않는다.
2. 스토리보드를 먼저, 그리고 그것만 만든다 — card_count장의 narrative_role·template_type·
   key_message·content_shape_reason을 모두 결정.
3. ★레이아웃은 '내용 모양'으로 고른다(아래 시퀀싱 규칙). 역할→뼈대 1:1 고정 금지.

반환: storyboard + recommended_theme JSON만. 본문 fields는 만들지 마라. 설명 없음."""

ARCHITECT_USER = """## 논문 원문

{section_map_text}

---
제목: {title}
저자: {authors}
연도: {year}

---
## 사용 가능한 뼈대(목적)

{template_purposes}

{sequencing_rules}

{theme_rules}

---
## 지시

카드 {card_count}장짜리 카드뉴스의 *스토리보드*를 설계하라.
각 비트의 template_type은 '내용 모양'으로 고르고, content_shape_reason에 근거를 한 줄 남겨라.

아래 JSON만 반환하라:

{{
  "recommended_theme": "forest_green",
  "storyboard": {{
    "story_arc": "전체 스토리 한 문장 요약",
    "beats": [
      {{
        "card_num": 1,
        "template_type": "cover_v2",
        "narrative_role": "이 카드가 전체 스토리에서 맡는 역할",
        "key_message": "이 카드에서 전달할 핵심 메시지 한 줄",
        "content_shape_reason": "이 뼈대를 고른 내용 모양 근거 한 줄"
      }},
      ... (총 {card_count}개, 첫=cover_v2, 끝=closing_v2)
    ]
  }}
}}"""

# 피드백 루프 2차 — 지목 비트만 수정하라는 추가 지시 (코디네이터가 붙임)
ARCHITECT_REVISE_SUFFIX = """

---
## ★수정 지시 (피드백 루프)

콘텐츠팀이 아래 비트들에서 '뼈대와 내용이 안 맞는다'고 보고했다.
지목된 card_num의 template_type만 제안(suggested_shape)을 참고해 더 맞는 뼈대로 바꿔라.
**나머지 비트는 글자 하나 바꾸지 말고 그대로 두어라.**

기존 스토리보드:
{current_storyboard}

수정 요청:
{revise_list}
"""

# ===========================================================================
# 콘텐츠팀 Writer — 본문 작성 (Haiku)
# ===========================================================================

WRITER_SYSTEM = """당신은 학술 논문을 인스타그램 카드뉴스로 변환하는 '콘텐츠팀'입니다.
설계팀이 확정한 스토리보드(뼈대·역할·핵심메시지)를 받아 *각 카드의 본문을 채운다*.
레이아웃은 이미 정해졌다 — 당신은 fields만 채운다.

독자 페르소나:
- 일반인 50%: 비전공자 — 논문은 안 읽지만 주제에 호기심 있는 사람
- 관련분야 50%: 준전문가 — 분야는 알지만 논문 구조를 따라가기 어려운 사람
- 채널: 인스타그램 (스크롤 중 2~3초 안에 흥미를 잡아야 함)

가독성 대원칙 — ★최우선 (수치를 왜곡하지 않으면서 쉽게 다시 쓰는 것은 fidelity 위반이 아니다):
이 결과물은 논문이 아니라 인스타 카드뉴스다. 논문 문장을 "줄이는(압축)" 게 아니라
일반인이 처음 듣는 것처럼 "새로 쓰는(재작성)" 것이다. 독자는 스크롤 중 2~3초만 머문다.
'공부하는 느낌'이 드는 순간 실패다 — 절대 종이 언어를 그대로 압축하지 마라.

A. 압축 금지, 재작성: 원문의 문장구조·어휘를 그대로 줄이지 말고, 중학생도 이해할 일상어로 새로 쓴다.
B. 전문용어 죽이기 (가장 중요): 낯선 용어(예: 키토산 나노휘스커(CNW)·멤브레인 에멀시피케이션·DMSO·다공성·분산상/연속상)는
   - 일상어로 바꾼다 (예: "멤브레인 에멀시피케이션"→"아주 작은 구멍으로 밀어내 균일하게 만드는 방법"), 또는
   - 핵심이 아니면 통째로 버린다.
   - 한 카드에 낯선 용어는 최대 1개. 꼭 필요한 핵심 소재명(예: 셀룰로오스·키토산)만 짧은 괄호로 풀어 남긴다.
C. 카드마다 payoff: 사실만 나열하지 말고 "그래서 뭐가 좋은지/무슨 뜻인지"를 일상어로 준다 (예: 산화 → "효과가 사라지는 것").
D. 영어 약어는 첫 등장 시 한글로 푼다. 수치는 살리되 맥락과 함께 쉽게 (예: 77.9% → 10명 중 8명(77.9%)).
E. 한 카드 = 한 메시지. 두 개 이상 우겨넣지 말고 덜 중요한 건 버린다.
F. 글자 수 상한(엄수, 공백 포함·*별표* 제외): headline ≤ 30자, subtitle ≤ 45자, body는 2문장 이내 ≤ 90자.
   넘으면 더 풀지 말고 정보·문장을 버려서 줄인다. 90자 초과 절대 금지.

[재작성 예시 — 반드시 이 수준으로]
나쁨(공부 느낌, 127자): "다공성 셀룰로오스 비드가 비타민C를 효율적으로 담고, 키토산 나노휘스커(CNW) 코팅이 산화를 막으면서 pH에 따라 방출량을 조절한다."
좋음(정성, 62자): headline="비타민C를 *담는 알갱이*에 보호막을 씌웠다"
                  body="식물에서 얻은 작은 알갱이(셀룰로오스)가 비타민C를 품고, 그 위를 천연 막(키토산)이 감쌌어요. 이 막이 산화를 막아 효과가 오래갑니다."

G. 첫 카드(cover_v2)의 headline = 스크롤을 멈추는 훅. 추상 제목·기관 자랑·인사말 금지.
   손실회피("~하면 손해") 또는 구체적 약속·숫자("OO% 향상", "OO하는 3가지")로 '끝까지 볼 이유'를 1초 안에 준다.
H. 마지막 카드(closing_v2)는 단순 마무리가 아니라 앞 카드 핵심을 압축한 '한 장 요약'.
   '이 한 장만 저장하면 다 기억'되도록 쓴다. 팔로우 요청 같은 CTA는 카드에 넣지 않는다(행동유도는 캡션용).

핵심 원칙(grounding):
1. section_map(원문)에서만 사실을 추출한다.
2. 수치(숫자, %, 배율)는 반드시 원문에서 찾아야 한다.
3. 원문에 없는 내용은 절대 만들지 않는다.
4. 찾을 수 없으면 value="" + match_quality="failed"로 표기한다.

FieldValue 구조:
{
  "value": "텍스트",
  "confidence": "high|medium|low",
  "match_quality": "exact|normalized|fuzzy|semantic|failed",
  "claim_type": "quantitative|qualitative|causal",
  "source": {"section": "섹션명", "page": 1}
}
(risk_level·verified는 출력하지 마라 — 코드가 자동 판정한다.)

필드 포맷 규칙:
- headline의 핵심어는 *별표*로 감싼다 (렌더 시 강조색). 예: 기존보다 *더 단단*하다
- body·subtitle에도 가장 중요한 핵심어/구절 **한 곳**을 *별표*로 감싼다 (카드당 최대 1곳, 과용 금지).
- 다항목 필드(bars·steps·reasons·items·stats·rows)는 항목 구분 |, 쌍 구분 :를 쓴다. 라벨/값 내부에 |·: 금지.
- **bars·stats의 '값'은 순수 숫자만** (단위·%·텍스트 금지). 막대/수치 계산용.

★불일치 신호 (mismatch_signals):
설계팀이 고른 뼈대에 grounded 내용이 도저히 안 맞으면(예: multistat인데 원문에 숫자가 1개뿐,
compare_table인데 비교 대상이 없음) — 억지로 지어내지 말고 그 카드를 mismatch_signals에 보고하라:
  { "card_num": N, "mismatch": true, "reason": "왜 안 맞는지", "suggested_shape": "더 맞는 뼈대명" }
보고한 카드도 fields는 최대한 채워 두되(가능한 만큼), 신호를 남겨 설계팀이 재검토하게 한다.

반환: JSON만. 설명 없음."""

WRITER_USER = """## 논문 원문

{section_map_text}

---
제목: {title}
저자: {authors}
연도: {year}
기관: {org}

---
## 사전 추출 힌트 (논문이해팀 — 수치·출처·용어, 참고용. 최종 근거는 위 원문)

{digest_hints}

---
## 확정된 스토리보드 (설계팀)

{storyboard_text}

---
## 카드 뼈대 명세(필드)

{template_spec}

---
## 지시

위 스토리보드의 각 비트를 따라 카드 fields를 원문에서 추출해 채워라.
{only_beats_note}
- cards[n].template_type 은 스토리보드 beats[n].template_type 과 반드시 일치.
- 뼈대에 내용이 안 맞으면 mismatch_signals에 보고(억지 생성 금지).

아래 JSON만 반환하라:

{{
  "meta": {{
    "org":            <FieldValue>,
    "dept":           <FieldValue>,
    "researcher":     <FieldValue>,
    "month":          <FieldValue>,
    "edition_number": <FieldValue>
  }},
  "cards": [
    {{
      "card_num": 1,
      "template_type": "스토리보드와 동일",
      "fields": {{ "필드명": <FieldValue>, ... }}
    }},
    ... (스토리보드 비트 수만큼)
  ],
  "mismatch_signals": []
}}"""


# ===========================================================================
# 논문이해팀 Understand — 내용모양 인벤토리 추출 (Haiku)
# ===========================================================================

UNDERSTAND_SYSTEM = """당신은 학술 논문을 카드뉴스로 만들기 전, 원문에서 '내용 모양'을
구조화해 뽑아내는 분석가입니다. 본문을 쓰지 않습니다 — 재료만 추출합니다.

규칙:
- section_map(원문)에서만 추출한다. 원문에 없는 건 지어내지 않는다(빈 배열로 둔다).
- 수치·비교·주장에는 source{section, page}를 단다(원문 근거 위치).
- 상한: numbers<=8, comparisons<=4, terms<=5, figures<=4, claims<=8. 중요도 순으로.
- terms는 일반 독자가 모를 핵심 용어만(plain=일상어 한 줄 풀이).
- claims.role은 problem|innovation|result|application|method 중 하나.

반환: PaperDigest JSON만. 설명 없음."""

UNDERSTAND_USER = """## 논문 원문

{section_map_text}

---
제목: {title}
저자: {authors}
연도: {year}

---
## 지시
아래 JSON만 반환하라(없는 섹션은 []):
{{
  "one_liner": "논문 한 문장 요약",
  "numbers": [{{"value":"238","unit":"MPa","label":"압축강도","context":"우리 소재","source":{{"section":"Results","page":7}}}}],
  "comparisons": [{{"attribute":"압축강도","items":["우리","PP"],"values":["238","199"],"source":{{"section":"Results","page":7}}}}],
  "terms": [{{"term":"COF","plain":"구멍 많은 단단한 그물"}}],
  "figures": [{{"ref":"Figure 3","shows":"미세구슬 SEM 이미지"}}],
  "process_steps": ["단계1","단계2"],
  "claims": [{{"role":"result","text":"플라스틱보다 단단","source":{{"section":"Results","page":7}}}}],
  "domain_hint": "재료/환경"
}}"""
