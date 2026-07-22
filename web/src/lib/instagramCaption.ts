/**
 * 캡션 본문 + 해시태그를 인스타 붙여넣기용 한 덩어리 텍스트로 합친다.
 * 백엔드 GET /api/deck/{id}/caption 이 { caption, hashtags }를 주면 프론트가 이걸로 조합해 클립보드에 넣는다.
 * (IG 2,200자·30태그 상한은 생성기(백엔드)가 지킨다 — 스펙 §3A. 여기선 조합만.)
 */
export function buildInstagramCaption(caption: string, hashtags: string[]): string {
  const tags = hashtags
    .map((h) => h.replace(/\s+/g, ''))       // 인스타 태그는 공백 불가 → 내부 공백 제거
    .filter((h) => h.replace(/#/g, '').length > 0)  // 빈/공백뿐 태그 버림
    .map((h) => (h.startsWith('#') ? h : `#${h}`))   // # 없으면 붙이고, 있으면 중복 안 함
  return tags.length ? `${caption}\n\n${tags.join(' ')}` : caption
}
