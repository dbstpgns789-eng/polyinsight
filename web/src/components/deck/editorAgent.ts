// iframe 내부에 주입되어 실행되는 편집 에이전트 (헌법 v3.0 Phase 3).
// 부모(React)와 postMessage로 통신. 클린 직렬화는 여기(=iframe)에서 수행한다 —
// 부모는 contentDocument를 직접 읽지 않고, 편집 아티팩트가 제거된 HTML 문자열만 받는다.
//
// 이 모듈은 함수 본문을 '문자열'로 내보낸다. DeckEditor가 iframe 문서에 <script>로 주입한다.

const AGENT_BODY = `
(function () {
  if (window.__piAgent) return;
  window.__piAgent = true;

  var mode = 'view';
  var sel = null;          // 선택된 요소
  var overlay = null;      // 선택 하이라이트 오버레이

  function post(type, payload) {
    parent.postMessage(Object.assign({ source: 'pi-deck', type: type }, payload || {}), '*');
  }

  function postHeight() {
    post('HEIGHT', { height: document.documentElement.scrollHeight });
  }

  function ensureOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.setAttribute('data-pi-overlay', '1');
    overlay.style.cssText =
      'position:absolute;pointer-events:none;z-index:2147483647;' +
      'border:2px solid #2F6F4E;border-radius:4px;box-shadow:0 0 0 2px rgba(47,111,78,.25);' +
      'transition:all .05s;display:none';
    document.body.appendChild(overlay);
    return overlay;
  }

  function positionOverlay() {
    if (!sel) { if (overlay) overlay.style.display = 'none'; return; }
    var r = sel.getBoundingClientRect();
    var ov = ensureOverlay();
    ov.style.display = 'block';
    ov.style.left = (r.left + window.scrollX - 2) + 'px';
    ov.style.top = (r.top + window.scrollY - 2) + 'px';
    ov.style.width = r.width + 'px';
    ov.style.height = r.height + 'px';
  }

  // 텍스트 리프(블록 자식 없는 인라인 콘텐츠 요소)인가 → 인라인 편집 가능
  function isTextLeaf(el) {
    if (!el) return false;
    if (el.querySelector('div,section,svg,img,ul,ol,table,figure,canvas,header,footer,article')) return false;
    return (el.textContent || '').trim().length > 0;
  }

  // 클릭 대상에서 편집 단위 요소 선택 (카드 프레임/바디/오버레이는 제외)
  function pick(target) {
    var el = target;
    if (!el || el === overlay) return null;
    if (el.nodeType === 3) el = el.parentElement;
    if (!el || el === document.body || el === document.documentElement) return null;
    if (el.hasAttribute && el.hasAttribute('data-screen-label')) return null; // 카드 프레임 자체는 선택 안 함
    return el;
  }

  function styleSnapshot(el) {
    var cs = getComputedStyle(el);
    return {
      color: cs.color, fontSize: cs.fontSize, textAlign: cs.textAlign,
      fontWeight: cs.fontWeight, background: el.style.background || el.style.backgroundColor || ''
    };
  }

  function select(el) {
    deselect();
    sel = el;
    positionOverlay();
    if (isTextLeaf(el)) {
      el.setAttribute('contenteditable', 'true');
      el.style.outline = 'none';
      el.focus();
    }
    post('SELECTED', {
      tag: el.tagName.toLowerCase(),
      editable: isTextLeaf(el),
      styles: styleSnapshot(el),
      text: (el.textContent || '').slice(0, 80)
    });
  }

  function deselect() {
    if (sel && sel.getAttribute('contenteditable')) sel.removeAttribute('contenteditable');
    sel = null;
    if (overlay) overlay.style.display = 'none';
    post('DESELECTED', {});
  }

  function onClick(e) {
    if (mode !== 'edit') return;
    var el = pick(e.target);
    if (!el) { deselect(); return; }
    e.preventDefault();
    select(el);
  }

  function onInput() {
    post('DIRTY', {});
    positionOverlay();
    postHeight();
  }

  function setMode(m) {
    mode = m;
    document.body.style.cursor = (m === 'edit') ? 'pointer' : '';
    if (m !== 'edit') deselect();
  }

  // 편집 아티팩트를 제거한 클린 HTML 직렬화
  function serialize() {
    var clone = document.documentElement.cloneNode(true);
    var rm = clone.querySelectorAll('[data-pi-overlay],[data-pi-agent]');
    for (var i = 0; i < rm.length; i++) rm[i].parentNode.removeChild(rm[i]);
    var ce = clone.querySelectorAll('[contenteditable]');
    for (var j = 0; j < ce.length; j++) ce[j].removeAttribute('contenteditable');
    return '<!DOCTYPE html>\\n' + clone.outerHTML;
  }

  window.addEventListener('message', function (e) {
    var d = e.data || {};
    if (d.source !== 'pi-host') return;
    switch (d.type) {
      case 'SET_MODE': setMode(d.mode); break;
      case 'GET_HTML': post('HTML', { html: serialize() }); break;
      case 'CLEAR_SELECTION': deselect(); break;
      case 'APPLY_STYLE':
        if (sel) {
          sel.style[d.prop] = d.value;
          positionOverlay(); post('DIRTY', {}); postHeight();
          post('SELECTED', { tag: sel.tagName.toLowerCase(), editable: isTextLeaf(sel), styles: styleSnapshot(sel), text: (sel.textContent || '').slice(0, 80) });
        }
        break;
      case 'DELETE_ELEMENT':
        if (sel) { var p = sel.parentNode; p.removeChild(sel); sel = null; if (overlay) overlay.style.display = 'none'; post('DESELECTED', {}); post('DIRTY', {}); postHeight(); }
        break;
      case 'MOVE_ELEMENT':
        if (sel) {
          if (d.dir === 'up' && sel.previousElementSibling) sel.parentNode.insertBefore(sel, sel.previousElementSibling);
          else if (d.dir === 'down' && sel.nextElementSibling) sel.parentNode.insertBefore(sel.nextElementSibling, sel);
          positionOverlay(); post('DIRTY', {}); postHeight();
        }
        break;
    }
  });

  document.addEventListener('click', onClick, true);
  document.addEventListener('input', onInput, true);
  window.addEventListener('resize', function () { positionOverlay(); postHeight(); });
  window.addEventListener('scroll', positionOverlay, true);

  post('EDITOR_READY', {});
  postHeight();
})();
`;

export default AGENT_BODY;
