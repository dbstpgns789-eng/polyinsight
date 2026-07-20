'use client'

// 요금 안내 (/upgrade) — 무료체험 배관 마지막 태스크(Task 11).
// 진입: 대시보드 미터 CTA·덱 카드 잠금 / deck/new 402(?from=author) / 내보내기 페이월(?from=export).
// ★가격 미확정 — 덱 원가(현재 ~$1)를 먼저 낮춘 뒤 결정한다(루트 CLAUDE.md 무료체험 배관 결정).
// 그래서 Pro/Lab 금액은 $— + "가안" 칩이고, Pro 버튼은 결제 연동(Creem) 전까지 비활성이다.
// 거짓 숫자를 쓰지 않는다 — 없는 값은 "가안"으로 표시하지 지어내지 않는다.
//
// AuthGuard로 감싸지 않는다: 이 페이지의 모든 CTA가 비인증 상태에서도 안전하다
// (무료="현재 플랜" 정적 라벨, Pro="준비 중" 비활성, Lab=mailto). 결제·플랜 전환 같은
// 인증이 필요한 동작이 아직 없어 로그인을 요구할 이유가 없고, 향후 랜딩에서 바로
// 링크할 수 있도록 공개 라우트로 둔다.

import { useSearchParams } from 'next/navigation'
import { Suspense } from 'react'

const LAB_EMAIL = 'dbstpgns789@hanyang.ac.kr'

function UpgradeInner() {
  const from = useSearchParams().get('from')
  const headline =
    from === 'export'
      ? '내보내려면 업그레이드가 필요해요'
      : from === 'author'
        ? '무료 체험 1덱을 모두 사용했어요'
        : '계속 만들고, 파일로 내보내세요'

  return (
    <main className="upgrade">
      <div className="upgrade__wrap">
        <header className="upgrade__head">
          <p className="eyebrow">업그레이드</p>
          <h1>{headline}</h1>
          <p className="upgrade__lede">만든 카드뉴스는 그대로 보관돼요. 업그레이드하면 바로 이어서 쓸 수 있어요.</p>
        </header>

        <div className="upgrade__banner">
          <span className="upgrade__banner-ic">i</span>
          <span>
            가격은 <strong>확정 전</strong>이에요. 덱 생성 원가를 먼저 낮춘 뒤 공정하게 정할게요.
          </span>
        </div>

        <div className="upgrade__tiers">
          {/* 무료 */}
          <section className="upgrade__tier">
            <div className="upgrade__tier-name">무료</div>
            <p className="upgrade__tier-desc">우리 실력을 직접 확인하는 체험판</p>

            <div className="upgrade__price">
              <span className="upgrade__price-num">$0</span>
            </div>
            <div className="upgrade__quota">
              <span className="upgrade__quota-big">1덱</span>
              <span className="upgrade__quota-lab">평생 · 보기·편집 전용</span>
            </div>

            <button className="btn btn-outline upgrade__cta" disabled>
              현재 플랜
            </button>

            <ul className="upgrade__feats">
              <li>완성된 카드뉴스</li>
              <li>원문 수치 검증</li>
              <li>화면에서 보기·편집</li>
              <li className="upgrade__feat--off">파일 내보내기</li>
              <li className="upgrade__feat--off">2번째 덱부터</li>
            </ul>
          </section>

          {/* Pro */}
          <section className="upgrade__tier upgrade__tier--featured">
            <span className="upgrade__ribbon">가장 인기</span>
            <div className="upgrade__tier-name">Pro</div>
            <p className="upgrade__tier-desc">자기 연구를 꾸준히 알리는 연구자</p>

            <div className="upgrade__price">
              <span className="upgrade__price-num">$—</span>
              <span className="upgrade__price-per">/월</span>
              <span className="upgrade__price-guess">가안</span>
            </div>
            <div className="upgrade__quota">
              <span className="upgrade__quota-big">매달 여러 덱</span>
              <span className="upgrade__quota-lab">가안 · 원가 확정 후 공개</span>
            </div>

            <button className="btn btn-primary upgrade__cta" disabled>
              준비 중
            </button>

            <ul className="upgrade__feats">
              <li>무료의 모든 것 +</li>
              <li>1080×1350 PNG·ZIP 내보내기</li>
              <li>원문 수치 검증</li>
              <li>화면에서 편집 + 이미지 삽입</li>
            </ul>
          </section>

          {/* Lab */}
          <section className="upgrade__tier">
            <div className="upgrade__tier-name">Lab</div>
            <p className="upgrade__tier-desc">연구실·팀이 함께 쓰는 플랜</p>

            <div className="upgrade__price">
              <span className="upgrade__price-num">$—</span>
              <span className="upgrade__price-per">/월</span>
              <span className="upgrade__price-guess">가안</span>
            </div>
            <div className="upgrade__quota">
              <span className="upgrade__quota-big">사용량 협의</span>
              <span className="upgrade__quota-lab">연구실·팀 단위</span>
            </div>

            <a className="btn btn-outline upgrade__cta" href={`mailto:${LAB_EMAIL}`}>
              문의하기
            </a>

            <ul className="upgrade__feats">
              <li>Pro의 모든 것 +</li>
              <li>팀 단위 사용량 협의</li>
              <li>온보딩 지원</li>
            </ul>
          </section>
        </div>

        <p className="upgrade__foot">
          결제는 <span className="upgrade__mono">Creem</span>(Merchant of Record)을 통해 처리될 예정이에요 — 세금·인보이스 대행, USD 청구.
        </p>
      </div>
    </main>
  )
}

export default function UpgradePage() {
  return (
    <Suspense fallback={null}>
      <UpgradeInner />
    </Suspense>
  )
}
