import type { Card } from '@/types/editor'

const BRAND      = 'oklch(38% 0.14 152)'
const BRAND_DARK = 'oklch(28% 0.14 152)'
const TEXT1      = 'oklch(16% 0.008 152)'
const TEXT2      = 'oklch(44% 0.012 152)'
const TEXT3      = 'oklch(63% 0.008 152)'
const BORDER     = 'oklch(89% 0.012 152)'
const BG_SUBTLE  = 'oklch(97% 0.018 152)'

function get(card: Card, key: string) {
  return card.fields?.[key]?.value ?? ''
}

function header(card: Card, total: number) {
  return `
    <div style="background:${BRAND_DARK};padding:32px 56px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0;">
      <span style="color:rgba(255,255,255,0.75);font-size:24px;font-weight:800;letter-spacing:0.12em;">KITECH</span>
      <span style="color:rgba(255,255,255,0.45);font-size:22px;font-variant-numeric:tabular-nums;">${card.card_num} / ${total}</span>
    </div>`
}

function eyebrow(label: string) {
  return `<p style="font-size:22px;font-weight:700;color:${BRAND};text-transform:uppercase;letter-spacing:0.08em;margin-bottom:24px;">${label}</p>`
}

function buildBody(card: Card): string {
  const t = card.template_type

  if (t === 'cover') {
    return `
      <div style="flex:1;padding:80px 56px;display:flex;flex-direction:column;justify-content:space-between;background:#fff;">
        <div>
          <div style="width:72px;height:6px;background:${BRAND};border-radius:3px;margin-bottom:48px;"></div>
          <h1 style="font-size:68px;font-weight:900;color:${TEXT1};line-height:1.1;letter-spacing:-0.03em;margin-bottom:36px;">${get(card,'title')}</h1>
          <p style="font-size:34px;color:${TEXT2};line-height:1.55;font-weight:400;">${get(card,'subtitle')}</p>
        </div>
        <div style="padding-top:48px;border-top:1.5px solid ${BORDER};">
          <p style="font-size:26px;color:${TEXT3};font-weight:500;">${get(card,'institution')}</p>
        </div>
      </div>`
  }

  if (t === 'problem') {
    return `
      <div style="flex:1;padding:80px 56px;background:#fff;">
        ${eyebrow('연구 배경')}
        <h2 style="font-size:58px;font-weight:800;color:${TEXT1};line-height:1.15;letter-spacing:-0.025em;margin-bottom:52px;">${get(card,'section_title')}</h2>
        <p style="font-size:31px;color:${TEXT2};line-height:1.8;font-weight:400;">${get(card,'body')}</p>
      </div>`
  }

  if (t === 'data') {
    return `
      <div style="flex:1;padding:80px 56px;background:#fff;display:flex;flex-direction:column;justify-content:space-between;">
        <div>
          ${eyebrow('핵심 데이터')}
          <h2 style="font-size:50px;font-weight:800;color:${TEXT1};line-height:1.2;margin-bottom:0;">${get(card,'section_title')}</h2>
        </div>
        <div style="background:${BG_SUBTLE};border-radius:24px;padding:56px;text-align:center;">
          <p style="font-size:136px;font-weight:900;color:${BRAND};line-height:1;letter-spacing:-0.04em;">${get(card,'stat_main')}</p>
          <p style="font-size:30px;color:${TEXT2};margin-top:24px;font-weight:500;">${get(card,'stat_desc')}</p>
          ${get(card,'stat_sub') ? `<p style="font-size:25px;color:${TEXT3};margin-top:14px;">${get(card,'stat_sub')}</p>` : ''}
        </div>
      </div>`
  }

  if (t === 'flow') {
    const steps = ['step1','step2','step3','step4']
      .map(k => get(card, k))
      .filter(Boolean)
    return `
      <div style="flex:1;padding:72px 56px;background:#fff;">
        ${eyebrow('연구 방법')}
        <h2 style="font-size:50px;font-weight:800;color:${TEXT1};line-height:1.2;margin-bottom:52px;">${get(card,'section_title')}</h2>
        <div style="display:flex;flex-direction:column;">
          ${steps.map((s, i) => `
            <div style="display:flex;align-items:flex-start;gap:32px;padding:28px 0;border-bottom:1px solid ${BORDER};">
              <div style="width:48px;height:48px;min-width:48px;background:${BRAND};border-radius:50%;display:flex;align-items:center;justify-content:center;">
                <span style="color:white;font-size:22px;font-weight:800;">${i+1}</span>
              </div>
              <p style="font-size:28px;color:${TEXT2};line-height:1.55;padding-top:6px;">${s}</p>
            </div>`).join('')}
        </div>
      </div>`
  }

  if (t === 'closing') {
    return `
      <div style="flex:1;padding:80px 56px;background:#fff;display:flex;flex-direction:column;justify-content:space-between;">
        <div>
          ${eyebrow('결론')}
          <h2 style="font-size:58px;font-weight:800;color:${TEXT1};line-height:1.15;margin-bottom:52px;">${get(card,'section_title')}</h2>
          <p style="font-size:31px;color:${TEXT2};line-height:1.8;font-weight:400;">${get(card,'body')}</p>
        </div>
        <div style="display:flex;align-items:center;gap:18px;">
          <div style="width:36px;height:5px;background:${BRAND};border-radius:3px;"></div>
          <span style="font-size:22px;color:${TEXT3};font-weight:600;">PolyInsight</span>
        </div>
      </div>`
  }

  // generic fallback
  const entries = Object.entries(card.fields ?? {})
  const title = get(card, 'section_title') || get(card, 'title') || t
  const rest = entries.filter(([k]) => !['section_title','title'].includes(k)).slice(0, 3)
  return `
    <div style="flex:1;padding:80px 56px;background:#fff;">
      <h2 style="font-size:58px;font-weight:800;color:${TEXT1};line-height:1.15;margin-bottom:48px;">${title}</h2>
      ${rest.map(([k, fv]) => `
        <div style="margin-bottom:32px;">
          <p style="font-size:18px;font-weight:700;color:${BRAND};text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">${k}</p>
          <p style="font-size:29px;color:${TEXT2};line-height:1.6;">${fv?.value ?? ''}</p>
        </div>`).join('')}
    </div>`
}

export function getMockCardHtml(card: Card, total: number): string {
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{
    width:1080px;height:1080px;overflow:hidden;
    font-family:-apple-system,"Pretendard Variable",Pretendard,BlinkMacSystemFont,"Apple SD Gothic Neo","Segoe UI",system-ui,sans-serif;
    -webkit-font-smoothing:antialiased;
    word-break:keep-all;overflow-wrap:break-word;
  }
  .card{width:1080px;height:1080px;display:flex;flex-direction:column;overflow:hidden;}
</style>
</head>
<body>
<div class="card">
  ${header(card, total)}
  ${buildBody(card)}
</div>
</body>
</html>`
}
