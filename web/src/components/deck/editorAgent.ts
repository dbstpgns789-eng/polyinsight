// iframe 내부에 주입되어 실행되는 편집 에이전트 (헌법 v3.0 Phase 3 + 3d 직접조작).
// 부모(React)와 postMessage로 통신. 클린 직렬화는 여기(=iframe)에서 수행한다 —
// 부모는 contentDocument를 직접 읽지 않고, 편집 아티팩트가 제거된 HTML 문자열만 받는다.
//
// 설계 원칙: DOM이 유일한 사실 소스. 편집(이동/리사이즈/스타일/삭제)은 인라인 스타일·DOM 변경으로
// 적용되고, undo/redo는 커맨드 패턴(do/undo 역연산)으로 관리한다(C-좋음 편집 모델의 씨앗).
//
// 모듈: selection · transform(드래그/리사이즈) · snap · history · serialize · bridge.
// 이 모듈은 함수 본문을 '문자열'로 내보낸다. DeckEditor가 iframe 문서에 <script>로 주입한다.

const AGENT_BODY = `
(function () {
  if (window.__piAgent) return;
  window.__piAgent = true;

  var mode = 'view';
  var sel = null;          // 선택된 요소
  var overlay = null;      // 선택 하이라이트 오버레이
  var handles = [];        // 8방향 리사이즈 핸들
  var guides = [];         // 스냅 정렬 가이드선
  var CARD_W = 1080, CARD_H = 1350;
  var DRAG_THRESHOLD = 3, SNAP = 6;
  var HANDLE_DIRS = ['nw','n','ne','e','se','s','sw','w'];

  // ── bridge ───────────────────────────────────────────────────────────────
  function post(type, payload) {
    parent.postMessage(Object.assign({ source: 'pi-deck', type: type }, payload || {}), '*');
  }
  function postHeight() { post('HEIGHT', { height: document.documentElement.scrollHeight }); }

  // ── selection ──────────────────────────────────────────────────────────────
  function isTextLeaf(el) {
    if (!el) return false;
    if (el.querySelector('div,section,svg,img,ul,ol,table,figure,canvas,header,footer,article')) return false;
    return (el.textContent || '').trim().length > 0;
  }
  function isPiArtifact(el) {
    return el.hasAttribute && (el.hasAttribute('data-pi-overlay') || el.hasAttribute('data-pi-handle') || el.hasAttribute('data-pi-guide'));
  }
  function pick(target) {
    var el = target;
    if (!el) return null;
    if (el.nodeType === 3) el = el.parentElement;
    if (!el || el === document.body || el === document.documentElement) return null;
    if (isPiArtifact(el)) return null;
    if (el.hasAttribute && el.hasAttribute('data-screen-label')) return null; // 카드 프레임 자체는 선택 안 함
    return el;
  }
  function cardOf(el) {
    var c = el;
    while (c && !(c.hasAttribute && c.hasAttribute('data-screen-label'))) c = c.parentElement;
    return c;
  }
  function isAbsolute(el) { return getComputedStyle(el).position === 'absolute'; }
  function styleSnapshot(el) {
    var cs = getComputedStyle(el);
    return {
      color: cs.color, fontSize: cs.fontSize, textAlign: cs.textAlign,
      fontWeight: cs.fontWeight, background: el.style.background || el.style.backgroundColor || ''
    };
  }
  function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }

  function ensureOverlay() {
    if (overlay) return overlay;
    overlay = document.createElement('div');
    overlay.setAttribute('data-pi-overlay', '1');
    overlay.style.cssText =
      'position:absolute;pointer-events:none;z-index:2147483645;' +
      'border:2px solid #2F6F4E;border-radius:4px;box-shadow:0 0 0 2px rgba(47,111,78,.25);display:none';
    document.body.appendChild(overlay);
    return overlay;
  }
  function resizeCursor(dir) {
    var m = { n: 'ns', s: 'ns', e: 'ew', w: 'ew', ne: 'nesw', sw: 'nesw', nw: 'nwse', se: 'nwse' };
    return (m[dir] || 'default') + '-resize';
  }
  function ensureHandles() {
    if (handles.length) return;
    for (var i = 0; i < HANDLE_DIRS.length; i++) {
      (function (dir) {
        var hd = document.createElement('div');
        hd.setAttribute('data-pi-handle', dir);
        hd.style.cssText =
          'position:absolute;width:11px;height:11px;margin:-6px 0 0 -6px;background:#fff;' +
          'border:1.5px solid #2F6F4E;border-radius:2px;z-index:2147483647;display:none;cursor:' + resizeCursor(dir) + ';';
        hd.addEventListener('mousedown', function (e) { startResize(dir, e); });
        document.body.appendChild(hd);
        handles.push(hd);
      })(HANDLE_DIRS[i]);
    }
  }
  function showHandles(show) { for (var i = 0; i < handles.length; i++) handles[i].style.display = show ? 'block' : 'none'; }

  function positionOverlay() {
    if (!sel) { if (overlay) overlay.style.display = 'none'; showHandles(false); return; }
    var r = sel.getBoundingClientRect();
    var ov = ensureOverlay();
    ov.style.display = 'block';
    var x = r.left + window.scrollX, y = r.top + window.scrollY, w = r.width, h = r.height;
    ov.style.left = (x - 2) + 'px'; ov.style.top = (y - 2) + 'px';
    ov.style.width = w + 'px'; ov.style.height = h + 'px';
    if (mode === 'edit') {
      ensureHandles(); showHandles(true);
      var pos = { nw: [x, y], n: [x + w / 2, y], ne: [x + w, y], e: [x + w, y + h / 2], se: [x + w, y + h], s: [x + w / 2, y + h], sw: [x, y + h], w: [x, y + h / 2] };
      for (var i = 0; i < handles.length; i++) {
        var d = handles[i].getAttribute('data-pi-handle');
        handles[i].style.left = pos[d][0] + 'px'; handles[i].style.top = pos[d][1] + 'px';
      }
    } else { showHandles(false); }
  }

  function emitSelected() {
    if (!sel) return;
    post('SELECTED', {
      tag: sel.tagName.toLowerCase(),
      editable: isTextLeaf(sel),
      absolute: isAbsolute(sel),
      styles: styleSnapshot(sel),
      text: (sel.textContent || '').slice(0, 80)
    });
  }
  function select(el) {
    if (sel && sel !== el && sel.getAttribute('contenteditable')) sel.removeAttribute('contenteditable');
    sel = el;
    positionOverlay();
    if (isTextLeaf(el)) { el.setAttribute('contenteditable', 'true'); el.style.outline = 'none'; }
    emitSelected();
  }
  function deselect() {
    if (sel && sel.getAttribute('contenteditable')) sel.removeAttribute('contenteditable');
    sel = null;
    if (overlay) overlay.style.display = 'none';
    showHandles(false);
    post('DESELECTED', {});
  }

  // ── history (command pattern) ───────────────────────────────────────────────
  var undoStack = [], redoStack = [];
  function emitHistory() { post('HISTORY_STATE', { canUndo: undoStack.length > 0, canRedo: redoStack.length > 0 }); }
  function pushCmd(cmd) { undoStack.push(cmd); redoStack = []; emitHistory(); }
  function afterMutate() { positionOverlay(); post('DIRTY', {}); postHeight(); }
  function undo() {
    var c = undoStack.pop(); if (!c) return;
    c.undo(); redoStack.push(c);
    if (sel && !document.body.contains(sel)) deselect();
    else if (sel) emitSelected();
    afterMutate(); emitHistory();
  }
  function redo() {
    var c = redoStack.pop(); if (!c) return;
    c.run(); undoStack.push(c);
    if (sel && !document.body.contains(sel)) deselect();
    else if (sel) emitSelected();
    afterMutate(); emitHistory();
  }
  var LAYOUT_PROPS = ['position', 'left', 'top', 'width', 'height', 'transform'];
  function snapInline(el) { var o = {}; for (var i = 0; i < LAYOUT_PROPS.length; i++) o[LAYOUT_PROPS[i]] = el.style[LAYOUT_PROPS[i]] || ''; return o; }
  function applyInline(el, snap) { for (var i = 0; i < LAYOUT_PROPS.length; i++) el.style[LAYOUT_PROPS[i]] = snap[LAYOUT_PROPS[i]]; }
  function layoutCmd(el, before, after) { return { run: function () { applyInline(el, after); }, undo: function () { applyInline(el, before); } }; }
  function propCmd(el, prop, before, after) { return { run: function () { el.style[prop] = after; }, undo: function () { el.style[prop] = before; } }; }

  // ── snap (정렬 가이드) ───────────────────────────────────────────────────────
  function clearGuides() { for (var i = 0; i < guides.length; i++) { if (guides[i].parentNode) guides[i].parentNode.removeChild(guides[i]); } guides = []; }
  function addGuide(card, vertical, pos) {
    var g = document.createElement('div'); g.setAttribute('data-pi-guide', '1');
    g.style.cssText = vertical
      ? 'position:absolute;top:0;bottom:0;left:' + pos + 'px;width:1.5px;background:#ff3d8b;z-index:2147483646;pointer-events:none;'
      : 'position:absolute;left:0;right:0;top:' + pos + 'px;height:1.5px;background:#ff3d8b;z-index:2147483646;pointer-events:none;';
    card.appendChild(g); guides.push(g);
  }
  function siblingsOf(card, el) { var out = [], ch = card.children; for (var i = 0; i < ch.length; i++) { var s = ch[i]; if (s === el || isPiArtifact(s)) continue; out.push(s); } return out; }
  // 이동 좌표(nl,nt)에 정렬 스냅 적용 + 분홍 가이드. 카드 가장자리/중심/안전영역 + 형제 가장자리/중심.
  function snapMove(card, el, nl, nt, w, h) {
    clearGuides();
    var cr = card.getBoundingClientRect();
    var padL = parseFloat(getComputedStyle(card).paddingLeft) || 0;
    var padT = parseFloat(getComputedStyle(card).paddingTop) || 0;
    var xs = [[0, false], [CARD_W - w, false], [(CARD_W - w) / 2, true], [padL, false], [CARD_W - padL - w, false]];
    var ys = [[0, false], [CARD_H - h, false], [(CARD_H - h) / 2, true], [padT, false], [CARD_H - padT - h, false]];
    var sibs = siblingsOf(card, el);
    for (var i = 0; i < sibs.length; i++) {
      var sr = sibs[i].getBoundingClientRect();
      var sl = sr.left - cr.left, st = sr.top - cr.top, sw = sr.width, sh = sr.height;
      xs.push([sl, false]); xs.push([sl + sw - w, false]); xs.push([sl + (sw - w) / 2, true]);
      ys.push([st, false]); ys.push([st + sh - h, false]); ys.push([st + (sh - h) / 2, true]);
    }
    var bx = nl, gx = null, by = nt, gy = null;
    for (var i = 0; i < xs.length; i++) { if (Math.abs(nl - xs[i][0]) <= SNAP) { bx = xs[i][0]; gx = xs[i][1] ? (bx + w / 2) : bx; break; } }
    for (var i = 0; i < ys.length; i++) { if (Math.abs(nt - ys[i][0]) <= SNAP) { by = ys[i][0]; gy = ys[i][1] ? (by + h / 2) : by; break; } }
    if (gx != null) addGuide(card, true, gx);
    if (gy != null) addGuide(card, false, gy);
    return { left: bx, top: by };
  }

  // ── transform: 하이브리드 드래그 이동 + 리사이즈 ──────────────────────────────
  function promote(el, card) {
    if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
    if (getComputedStyle(el).position !== 'absolute') {
      var r = el.getBoundingClientRect(), cr = card.getBoundingClientRect();
      el.style.width = r.width + 'px'; el.style.height = r.height + 'px';
      el.style.left = (r.left - cr.left) + 'px'; el.style.top = (r.top - cr.top) + 'px';
      el.style.position = 'absolute';
    }
  }

  // 통일 하이브리드: 모든 요소가 드래그 가능. 클릭(이동 임계 미만)=텍스트면 편집/선택,
  // 임계를 넘기면 드래그 이동(텍스트면 편집 모드 해제). 비텍스트는 네이티브 드래그/선택 방지.
  function onMouseDown(e) {
    if (mode !== 'edit') return;
    if (e.target && e.target.hasAttribute && e.target.hasAttribute('data-pi-handle')) return; // 핸들은 자체 처리
    var el = pick(e.target);
    if (!el) { deselect(); return; }
    var card = cardOf(el);
    if (!card) { select(el); return; }
    if (!isTextLeaf(el)) e.preventDefault();   // 텍스트는 캐럿 위해 기본동작 허용
    select(el);
    var downX = e.clientX, downY = e.clientY, dragging = false;
    var before = null, baseL = 0, baseT = 0, w = 0, h = 0;
    function move(ev) {
      if (!dragging) {
        if (Math.abs(ev.clientX - downX) < DRAG_THRESHOLD && Math.abs(ev.clientY - downY) < DRAG_THRESHOLD) return;
        dragging = true;
        if (el.getAttribute('contenteditable')) el.removeAttribute('contenteditable');
        if (window.getSelection) { var s = window.getSelection(); if (s && s.removeAllRanges) s.removeAllRanges(); }
        before = snapInline(el);
        promote(el, card);
        baseL = parseFloat(el.style.left) || 0; baseT = parseFloat(el.style.top) || 0;
        w = el.offsetWidth; h = el.offsetHeight;
      }
      var dx = ev.clientX - downX, dy = ev.clientY - downY;
      var nl = clamp(baseL + dx, 0, CARD_W - w), nt = clamp(baseT + dy, 0, CARD_H - h);
      var sn = snapMove(card, el, nl, nt, w, h);
      el.style.left = sn.left + 'px'; el.style.top = sn.top + 'px';
      positionOverlay();
    }
    function up() {
      document.removeEventListener('mousemove', move, true);
      document.removeEventListener('mouseup', up, true);
      clearGuides();
      if (dragging) { pushCmd(layoutCmd(el, before, snapInline(el))); emitSelected(); afterMutate(); }
    }
    document.addEventListener('mousemove', move, true);
    document.addEventListener('mouseup', up, true);
  }

  function startResize(dir, e) {
    if (!sel) return;
    e.preventDefault(); e.stopPropagation();
    var el = sel, card = cardOf(el); if (!card) return;
    var before = snapInline(el);
    promote(el, card);
    var sx = e.clientX, sy = e.clientY;
    var baseL = parseFloat(el.style.left) || 0, baseT = parseFloat(el.style.top) || 0;
    var baseW = el.offsetWidth, baseH = el.offsetHeight;
    function move(ev) {
      var dx = ev.clientX - sx, dy = ev.clientY - sy;
      var l = baseL, t = baseT, w = baseW, h = baseH;
      if (dir.indexOf('e') >= 0) w = baseW + dx;
      if (dir.indexOf('s') >= 0) h = baseH + dy;
      if (dir.indexOf('w') >= 0) { w = baseW - dx; l = baseL + dx; }
      if (dir.indexOf('n') >= 0) { h = baseH - dy; t = baseT + dy; }
      w = Math.max(12, w); h = Math.max(12, h);
      l = clamp(l, 0, CARD_W - w); t = clamp(t, 0, CARD_H - h);
      el.style.left = l + 'px'; el.style.top = t + 'px'; el.style.width = w + 'px'; el.style.height = h + 'px';
      positionOverlay();
    }
    function up() {
      document.removeEventListener('mousemove', move, true);
      document.removeEventListener('mouseup', up, true);
      pushCmd(layoutCmd(el, before, snapInline(el)));
      emitSelected(); afterMutate();
    }
    document.addEventListener('mousemove', move, true);
    document.addEventListener('mouseup', up, true);
  }

  function revertFlow() {
    if (!sel || !isAbsolute(sel)) return;
    var before = snapInline(sel);
    var after = {}; for (var i = 0; i < LAYOUT_PROPS.length; i++) after[LAYOUT_PROPS[i]] = '';
    applyInline(sel, after);
    pushCmd(layoutCmd(sel, before, after));
    emitSelected(); afterMutate();
  }

  // ── serialize (편집 아티팩트 제거한 클린 HTML) ────────────────────────────────
  function serialize() {
    var clone = document.documentElement.cloneNode(true);
    var rm = clone.querySelectorAll('[data-pi-overlay],[data-pi-agent],[data-pi-handle],[data-pi-guide]');
    for (var i = 0; i < rm.length; i++) rm[i].parentNode.removeChild(rm[i]);
    var ce = clone.querySelectorAll('[contenteditable]');
    for (var j = 0; j < ce.length; j++) { ce[j].removeAttribute('contenteditable'); ce[j].style.outline = ''; }
    return '<!DOCTYPE html>\\n' + clone.outerHTML;
  }

  function setMode(m) {
    mode = m;
    document.body.style.cursor = (m === 'edit') ? 'default' : '';
    if (m !== 'edit') deselect(); else positionOverlay();
  }
  function onInput() { post('DIRTY', {}); positionOverlay(); postHeight(); }

  // ── 부모 → iframe 명령 ───────────────────────────────────────────────────────
  window.addEventListener('message', function (e) {
    var d = e.data || {};
    if (d.source !== 'pi-host') return;
    switch (d.type) {
      case 'SET_MODE': setMode(d.mode); break;
      case 'GET_HTML': post('HTML', { html: serialize() }); break;
      case 'CLEAR_SELECTION': deselect(); break;
      case 'UNDO': undo(); break;
      case 'REDO': redo(); break;
      case 'REVERT_FLOW': revertFlow(); break;
      case 'APPLY_STYLE':
        if (sel) {
          pushCmd(propCmd(sel, d.prop, sel.style[d.prop] || '', d.value));
          sel.style[d.prop] = d.value;
          positionOverlay(); post('DIRTY', {}); postHeight(); emitSelected();
        }
        break;
      case 'DELETE_ELEMENT':
        if (sel) {
          var el = sel, parent = el.parentNode, next = el.nextSibling;
          pushCmd({ run: function () { parent.removeChild(el); }, undo: function () { parent.insertBefore(el, next); } });
          parent.removeChild(el);
          sel = null; if (overlay) overlay.style.display = 'none'; showHandles(false);
          post('DESELECTED', {}); afterMutate();
        }
        break;
      case 'MOVE_ELEMENT':
        if (sel) {
          var s = sel, p = s.parentNode;
          var doUp = function () { if (s.previousElementSibling) p.insertBefore(s, s.previousElementSibling); };
          var doDown = function () { if (s.nextElementSibling) p.insertBefore(s.nextElementSibling, s); };
          if (d.dir === 'up' && s.previousElementSibling) { pushCmd({ run: doUp, undo: doDown }); doUp(); }
          else if (d.dir === 'down' && s.nextElementSibling) { pushCmd({ run: doDown, undo: doUp }); doDown(); }
          afterMutate();
        }
        break;
    }
  });

  document.addEventListener('mousedown', onMouseDown, true);
  document.addEventListener('input', onInput, true);
  window.addEventListener('resize', function () { positionOverlay(); postHeight(); });
  window.addEventListener('scroll', positionOverlay, true);
  document.addEventListener('keydown', function (e) {
    if (mode !== 'edit') return;
    if ((e.ctrlKey || e.metaKey) && (e.key === 'z' || e.key === 'Z')) { e.preventDefault(); if (e.shiftKey) redo(); else undo(); }
    else if ((e.ctrlKey || e.metaKey) && (e.key === 'y' || e.key === 'Y')) { e.preventDefault(); redo(); }
  }, true);

  post('EDITOR_READY', {});
  emitHistory();
  postHeight();
})();
`;

export default AGENT_BODY;
