// iframe 내부에 주입되어 실행되는 편집 에이전트 (헌법 v3.0 Phase 3 + 3d 직접조작 + 3e 다중선택).
// 부모(React)와 postMessage로 통신. 클린 직렬화는 여기(=iframe)에서 수행한다 —
// 부모는 contentDocument를 직접 읽지 않고, 편집 아티팩트가 제거된 HTML 문자열만 받는다.
//
// 설계 원칙: DOM이 유일한 사실 소스. 편집(이동/리사이즈/스타일/삭제)은 인라인 스타일·DOM 변경으로
// 적용되고, undo/redo는 커맨드 패턴(do/undo 역연산)으로 관리한다(C-좋음 편집 모델의 씨앗).
//
// 모듈: selection(다중) · transform(드래그/리사이즈) · snap · history · serialize · bridge.
// 이 모듈은 함수 본문을 '문자열'로 내보낸다. DeckEditor가 iframe 문서에 <script>로 주입한다.
// ⚠️ 이 문자열 안에서는 백틱·${ 사용 금지(외부 템플릿 리터럴과 충돌), ES5(var/function) 유지.

const AGENT_BODY = `
(function () {
  if (window.__piAgent) return;
  window.__piAgent = true;

  var mode = 'view';
  var selection = [];      // 선택된 요소들(배열). primary()=마지막.
  var overlayPool = [];    // 요소별 하이라이트 오버레이 풀(재사용)
  var groupBox = null;     // 2개+ 선택 시 집합 바운딩박스(점선)
  var handles = [];        // 8방향 리사이즈 핸들(단일 선택 시만)
  var guides = [];         // 스냅 정렬 가이드선
  var CARD_W = 1080, CARD_H = 1350;
  var DRAG_THRESHOLD = 3, SNAP = 6;
  var HANDLE_DIRS = ['nw','n','ne','e','se','s','sw','w'];

  // ── bridge ───────────────────────────────────────────────────────────────
  function post(type, payload) {
    parent.postMessage(Object.assign({ source: 'pi-deck', type: type }, payload || {}), '*');
  }
  function postHeight() { post('HEIGHT', { height: document.documentElement.scrollHeight }); }

  // ── selection helpers ────────────────────────────────────────────────────
  function isTextLeaf(el) {
    if (!el) return false;
    if (el.querySelector('div,section,svg,img,ul,ol,table,figure,canvas,header,footer,article')) return false;
    return (el.textContent || '').trim().length > 0;
  }
  function isPiArtifact(el) {
    return el.hasAttribute && (el.hasAttribute('data-pi-artifact') || el.hasAttribute('data-pi-overlay') || el.hasAttribute('data-pi-handle') || el.hasAttribute('data-pi-guide'));
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
  // 기하 연산(이동/정렬/분배/수치)의 대상 = 카드의 직계 자식 조상. (D3: 중첩 요소 absolute 승격 시
  // offsetParent가 카드가 아닌 래퍼가 되어 좌표가 붕괴하는 것을 방지)
  function cardChild(el) {
    var card = cardOf(el); if (!card) return null;
    var c = el;
    while (c && c.parentElement !== card) c = c.parentElement;
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

  function primary() { return selection.length ? selection[selection.length - 1] : null; }
  function inSelection(el) { return selection.indexOf(el) >= 0; }
  function clearEditable() {
    var es = document.querySelectorAll('[contenteditable]');
    for (var i = 0; i < es.length; i++) { es[i].removeAttribute('contenteditable'); es[i].style.outline = ''; }
  }
  // 정확히 1개 텍스트 리프 선택일 때만 인라인 편집 허용(1→다중 전환 시 편집 해제)
  function refreshEditable() {
    clearEditable();
    var p = primary();
    if (selection.length === 1 && isTextLeaf(p)) { p.setAttribute('contenteditable', 'true'); p.style.outline = 'none'; }
  }
  function pruneSelection() {
    var kept = [];
    for (var i = 0; i < selection.length; i++) if (document.body.contains(selection[i])) kept.push(selection[i]);
    selection = kept;
  }

  // ── overlay 풀 + 핸들 ────────────────────────────────────────────────────
  function makeOverlayEl(dashed) {
    var d = document.createElement('div');
    d.setAttribute('data-pi-overlay', '1'); d.setAttribute('data-pi-artifact', '1');
    d.style.cssText = 'position:absolute;pointer-events:none;z-index:2147483645;border-radius:4px;display:none;'
      + (dashed
          ? 'border:1.5px dashed #2F6F4E;'
          : 'border:2px solid #2F6F4E;box-shadow:0 0 0 2px rgba(47,111,78,.25);');
    document.body.appendChild(d);
    return d;
  }
  function ensureOverlays(n) { while (overlayPool.length < n) overlayPool.push(makeOverlayEl(false)); }
  function boxOf(el) { var r = el.getBoundingClientRect(); return { x: r.left + window.scrollX, y: r.top + window.scrollY, w: r.width, h: r.height }; }
  function unionBox(els) {
    var minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9;
    for (var i = 0; i < els.length; i++) { var b = boxOf(els[i]); minx = Math.min(minx, b.x); miny = Math.min(miny, b.y); maxx = Math.max(maxx, b.x + b.w); maxy = Math.max(maxy, b.y + b.h); }
    return { x: minx, y: miny, w: maxx - minx, h: maxy - miny };
  }
  function placeBox(ov, b) { ov.style.display = 'block'; ov.style.left = (b.x - 2) + 'px'; ov.style.top = (b.y - 2) + 'px'; ov.style.width = b.w + 'px'; ov.style.height = b.h + 'px'; }

  function resizeCursor(dir) {
    var m = { n: 'ns', s: 'ns', e: 'ew', w: 'ew', ne: 'nesw', sw: 'nesw', nw: 'nwse', se: 'nwse' };
    return (m[dir] || 'default') + '-resize';
  }
  function ensureHandles() {
    if (handles.length) return;
    for (var i = 0; i < HANDLE_DIRS.length; i++) {
      (function (dir) {
        var hd = document.createElement('div');
        hd.setAttribute('data-pi-handle', dir); hd.setAttribute('data-pi-artifact', '1');
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
    for (var i = 0; i < overlayPool.length; i++) overlayPool[i].style.display = 'none';
    if (groupBox) groupBox.style.display = 'none';
    if (!selection.length) { showHandles(false); return; }
    ensureOverlays(selection.length);
    for (var i = 0; i < selection.length; i++) placeBox(overlayPool[i], boxOf(selection[i]));
    if (selection.length > 1) {
      if (!groupBox) groupBox = makeOverlayEl(true);
      placeBox(groupBox, unionBox(selection));
    }
    // 8방향 리사이즈 핸들은 정확히 1개 선택 + 편집모드일 때만(다중 스케일은 범위 밖)
    if (mode === 'edit' && selection.length === 1) {
      ensureHandles(); showHandles(true);
      var b = boxOf(selection[0]); var x = b.x, y = b.y, w = b.w, h = b.h;
      var pos = { nw: [x, y], n: [x + w / 2, y], ne: [x + w, y], e: [x + w, y + h / 2], se: [x + w, y + h], s: [x + w / 2, y + h], sw: [x, y + h], w: [x, y + h / 2] };
      for (var i = 0; i < handles.length; i++) {
        var d = handles[i].getAttribute('data-pi-handle');
        handles[i].style.left = pos[d][0] + 'px'; handles[i].style.top = pos[d][1] + 'px';
      }
    } else { showHandles(false); }
  }

  // 자연 카드좌표(카드 좌상단 기준)에서의 요소 rect
  function natRectOf(el) {
    var card = cardOf(el); if (!card) return null;
    var r = el.getBoundingClientRect(), cr = card.getBoundingClientRect();
    return { x: r.left - cr.left, y: r.top - cr.top, w: r.width, h: r.height };
  }
  function groupNatRect() {
    var p = primary(), card = cardOf(p); if (!card) return null;
    var cr = card.getBoundingClientRect();
    var minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9;
    for (var i = 0; i < selection.length; i++) {
      var r = selection[i].getBoundingClientRect();
      minx = Math.min(minx, r.left - cr.left); miny = Math.min(miny, r.top - cr.top);
      maxx = Math.max(maxx, r.right - cr.left); maxy = Math.max(maxy, r.bottom - cr.top);
    }
    return { x: minx, y: miny, w: maxx - minx, h: maxy - miny };
  }
  function sameSize() {
    if (selection.length < 2) return true;
    var r0 = selection[0].getBoundingClientRect();
    for (var i = 1; i < selection.length; i++) {
      var r = selection[i].getBoundingClientRect();
      if (Math.abs(r.width - r0.width) > 1 || Math.abs(r.height - r0.height) > 1) return false;
    }
    return true;
  }

  function emitSelected() {
    var p = primary(); if (!p) return;
    var n = selection.length;
    var rect = (n > 1) ? groupNatRect() : natRectOf(p);
    post('SELECTED', {
      tag: n > 1 ? ('(다중 ' + n + ')') : p.tagName.toLowerCase(),
      count: n,
      editable: n === 1 && isTextLeaf(p),
      absolute: isAbsolute(p),
      styles: styleSnapshot(p),
      text: n === 1 ? (p.textContent || '').slice(0, 80) : '',
      rect: rect,
      mixed: n > 1 && !sameSize(),
      canDistribute: n >= 3
    });
  }

  // 단일 선택(클릭). 다중선택 토글/마퀴는 아래 인터랙션에서.
  function select(el) {
    selection = [el];
    refreshEditable(); positionOverlay(); emitSelected();
  }
  function deselect() {
    selection = [];
    clearEditable(); positionOverlay();
    post('DESELECTED', {});
  }
  function afterSelChange() {
    refreshEditable(); positionOverlay();
    if (selection.length) emitSelected(); else post('DESELECTED', {});
  }
  function setSelection(els) { selection = els.slice(); afterSelChange(); }
  // Shift/Ctrl+클릭 토글. D2: 다른 카드 요소면 그 카드로 리셋.
  function toggleSel(el) {
    if (selection.length && cardOf(primary()) !== cardOf(el)) { select(el); return; }
    var idx = selection.indexOf(el);
    if (idx >= 0) selection.splice(idx, 1); else selection.push(el);
    afterSelChange();
  }

  // ── history (command pattern) ───────────────────────────────────────────────
  var undoStack = [], redoStack = [];
  function emitHistory() { post('HISTORY_STATE', { canUndo: undoStack.length > 0, canRedo: redoStack.length > 0 }); }
  function pushCmd(cmd) { undoStack.push(cmd); redoStack = []; emitHistory(); }
  function afterMutate() { positionOverlay(); post('DIRTY', {}); postHeight(); }
  function afterHistoryStep() {
    refreshEditable(); pruneSelection();
    if (selection.length) emitSelected(); else post('DESELECTED', {});
    afterMutate(); emitHistory();
  }
  function undo() { commitTextEdit(); var c = undoStack.pop(); if (!c) return; c.undo(); redoStack.push(c); afterHistoryStep(); }
  function redo() { commitTextEdit(); var c = redoStack.pop(); if (!c) return; c.run(); undoStack.push(c); afterHistoryStep(); }

  var LAYOUT_PROPS = ['position', 'left', 'top', 'width', 'height', 'transform'];
  function snapInline(el) { var o = {}; for (var i = 0; i < LAYOUT_PROPS.length; i++) o[LAYOUT_PROPS[i]] = el.style[LAYOUT_PROPS[i]] || ''; return o; }
  function applyInline(el, snap) { for (var i = 0; i < LAYOUT_PROPS.length; i++) el.style[LAYOUT_PROPS[i]] = snap[LAYOUT_PROPS[i]]; }
  function layoutCmd(el, before, after) { return { run: function () { applyInline(el, after); }, undo: function () { applyInline(el, before); } }; }
  function propCmd(el, prop, before, after) { return { run: function () { el.style[prop] = after; }, undo: function () { el.style[prop] = before; } }; }
  // 다중 조작(다중이동/정렬/분배)을 하나의 undo 단위로. undo는 역순.
  function compositeCmd(cmds) {
    return {
      run: function () { for (var i = 0; i < cmds.length; i++) cmds[i].run(); },
      undo: function () { for (var i = cmds.length - 1; i >= 0; i--) cmds[i].undo(); }
    };
  }

  // ── 텍스트 편집 커맨드 (undo 보편성 §5 — 유일한 미포착 조작이던 타이핑을 스택에 편입) ─────
  // beforeinput에서 편집 시작 시점 innerHTML 캡처, 커밋(포커스아웃/undo·redo·선택변경·모드변경)에
  // before≠after면 textCmd push. → Ctrl+Z/버튼이 타이핑도 순차 복원.
  var editingEl = null, editingBefore = '';
  function textCmd(el, before, after) { return { run: function () { el.innerHTML = after; }, undo: function () { el.innerHTML = before; } }; }
  function beginTextEdit(el) { editingEl = el; editingBefore = el.innerHTML; }
  function commitTextEdit() {
    if (!editingEl) return;
    var el = editingEl, before = editingBefore; editingEl = null;
    if (!document.body.contains(el)) return;
    var after = el.innerHTML;
    if (after !== before) { undoStack.push(textCmd(el, before, after)); redoStack = []; emitHistory(); post('DIRTY', {}); }
  }

  // ── snap (정렬 가이드) ───────────────────────────────────────────────────────
  function clearGuides() { for (var i = 0; i < guides.length; i++) { if (guides[i].parentNode) guides[i].parentNode.removeChild(guides[i]); } guides = []; }
  function addGuide(card, vertical, pos) {
    var g = document.createElement('div'); g.setAttribute('data-pi-guide', '1'); g.setAttribute('data-pi-artifact', '1');
    g.style.cssText = vertical
      ? 'position:absolute;top:0;bottom:0;left:' + pos + 'px;width:1.5px;background:#ff3d8b;z-index:2147483646;pointer-events:none;'
      : 'position:absolute;left:0;right:0;top:' + pos + 'px;height:1.5px;background:#ff3d8b;z-index:2147483646;pointer-events:none;';
    card.appendChild(g); guides.push(g);
  }
  function siblingsOf(card, els) {
    var out = [], ch = card.children;
    for (var i = 0; i < ch.length; i++) { var s = ch[i]; if (isPiArtifact(s)) continue; if (els.indexOf(s) >= 0) continue; out.push(s); }
    return out;
  }
  // 이동 좌표(nl,nt)에 정렬 스냅 적용 + 분홍 가이드. 카드 가장자리/중심/안전영역 + 형제 가장자리/중심.
  // els = 함께 이동 중인 요소들(형제 후보에서 제외). w,h = 스냅 기준 박스 크기.
  function snapMove(card, els, nl, nt, w, h) {
    clearGuides();
    var padL = parseFloat(getComputedStyle(card).paddingLeft) || 0;
    var padT = parseFloat(getComputedStyle(card).paddingTop) || 0;
    var xs = [[0, false], [CARD_W - w, false], [(CARD_W - w) / 2, true], [padL, false], [CARD_W - padL - w, false]];
    var ys = [[0, false], [CARD_H - h, false], [(CARD_H - h) / 2, true], [padT, false], [CARD_H - padT - h, false]];
    var cr = card.getBoundingClientRect();
    var sibs = siblingsOf(card, els);
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
  // R2 방지: 여러 요소 승격 시 '전원 rect를 먼저 캡처 → 그 다음 전원 promote → 캡처값으로 배치'.
  function promoteAll(els, card) {
    if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
    var cr = card.getBoundingClientRect();
    var snaps = [], rects = [];
    for (var i = 0; i < els.length; i++) { snaps.push(snapInline(els[i])); rects.push(els[i].getBoundingClientRect()); }
    for (var i = 0; i < els.length; i++) {
      var el = els[i], r = rects[i];
      if (getComputedStyle(el).position !== 'absolute') {
        el.style.width = r.width + 'px'; el.style.height = r.height + 'px';
        el.style.left = (r.left - cr.left) + 'px'; el.style.top = (r.top - cr.top) + 'px';
        el.style.position = 'absolute';
      }
    }
    return snaps; // promote 이전 인라인 스냅(undo용 before)
  }

  // ── 마퀴(rubber-band) 선택 ────────────────────────────────────────────────
  function cardAtPoint(x, y) { var el = document.elementFromPoint(x, y); return el ? cardOf(el) : null; }
  function makeMarquee() {
    var d = document.createElement('div');
    d.setAttribute('data-pi-marquee', '1'); d.setAttribute('data-pi-artifact', '1');
    d.style.cssText = 'position:absolute;z-index:2147483646;pointer-events:none;border:1px dashed #ff3d8b;background:rgba(255,61,139,.08);';
    document.body.appendChild(d); return d;
  }
  function placeMarquee(box, x1, y1, x2, y2) {
    box.style.left = (Math.min(x1, x2) + window.scrollX) + 'px'; box.style.top = (Math.min(y1, y2) + window.scrollY) + 'px';
    box.style.width = Math.abs(x2 - x1) + 'px'; box.style.height = Math.abs(y2 - y1) + 'px';
  }
  // 시작 카드의 직계 자식 중 마퀴 사각형과 교차하는 것 일괄 선택(D2: 카드 한정, D3: 직계자식).
  function selectInMarquee(card, x1, y1, x2, y2) {
    if (!card) { deselect(); return; }
    var ml = Math.min(x1, x2), mt = Math.min(y1, y2), mr = Math.max(x1, x2), mb = Math.max(y1, y2);
    var hits = [], ch = card.children;
    for (var i = 0; i < ch.length; i++) {
      var s = ch[i]; if (isPiArtifact(s)) continue;
      var r = s.getBoundingClientRect();
      if (ml < r.right && mr > r.left && mt < r.bottom && mb > r.top) hits.push(s);
    }
    if (hits.length) setSelection(hits); else deselect();
  }
  function startMarquee(e) {
    var startCard = cardAtPoint(e.clientX, e.clientY);
    var downX = e.clientX, downY = e.clientY, box = null, dragging = false;
    function move(ev) {
      if (!dragging) {
        if (Math.abs(ev.clientX - downX) < DRAG_THRESHOLD && Math.abs(ev.clientY - downY) < DRAG_THRESHOLD) return;
        dragging = true; box = makeMarquee();
      }
      placeMarquee(box, downX, downY, ev.clientX, ev.clientY);
    }
    function up(ev) {
      document.removeEventListener('mousemove', move, true);
      document.removeEventListener('mouseup', up, true);
      if (box && box.parentNode) box.parentNode.removeChild(box);
      if (!dragging) { deselect(); return; }        // 임계 미만 = 빈영역 클릭 → 해제
      selectInMarquee(startCard, downX, downY, ev.clientX, ev.clientY);
    }
    document.addEventListener('mousemove', move, true);
    document.addEventListener('mouseup', up, true);
  }

  function additive(e) { return e.shiftKey || e.ctrlKey || e.metaKey; }

  // 통일 하이브리드: 모든 요소가 드래그 가능. 클릭(이동 임계 미만)=텍스트면 편집/선택,
  // 임계를 넘기면 드래그 이동(텍스트면 편집 모드 해제). 다중선택 상태면 전원 함께 이동.
  function onMouseDown(e) {
    if (mode !== 'edit') return;
    if (e.target && e.target.hasAttribute && e.target.hasAttribute('data-pi-handle')) return; // 핸들은 자체 처리
    commitTextEdit();  // 선택/드래그 전환 전에 진행 중 텍스트 편집 확정
    var picked = pick(e.target);
    if (!picked) {                              // 빈영역 → 마퀴 시작(additive면 선택 유지)
      if (additive(e)) return;
      startMarquee(e); return;
    }
    var el = cardChild(picked) || picked;   // 기하 대상 = 카드 직계 자식(D3)
    var card = cardOf(el);
    if (additive(e)) { e.preventDefault(); toggleSel(el); return; } // Shift/Ctrl+클릭 토글
    if (!card) { select(picked); return; }

    // 다중선택 유지 조건: 이미 선택집합에 든 요소를 드래그하면 집합 전체 이동. 아니면 단일 선택.
    // collapse: 다중 중 하나를 plain클릭(드래그 없음)하면 mouseup에 단일로 축소(Figma식).
    var group, collapse = false;
    if (inSelection(el) && selection.length > 1) { group = selection.slice(); collapse = true; }
    else { select(isTextLeaf(picked) ? picked : el); group = [el]; }

    if (!isTextLeaf(primary())) e.preventDefault(); // 텍스트는 캐럿 위해 기본동작 허용
    var downX = e.clientX, downY = e.clientY, dragging = false;
    var befores = null, bases = [], gx0 = 0, gy0 = 0, gw = 0, gh = 0;

    function move(ev) {
      if (!dragging) {
        if (Math.abs(ev.clientX - downX) < DRAG_THRESHOLD && Math.abs(ev.clientY - downY) < DRAG_THRESHOLD) return;
        dragging = true;
        clearEditable();
        if (window.getSelection) { var s = window.getSelection(); if (s && s.removeAllRanges) s.removeAllRanges(); }
        var cr = card.getBoundingClientRect();
        // 집합 바운딩박스(카드 자연좌표) — 스냅 기준
        var minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9;
        for (var i = 0; i < group.length; i++) { var r = group[i].getBoundingClientRect(); minx = Math.min(minx, r.left - cr.left); miny = Math.min(miny, r.top - cr.top); maxx = Math.max(maxx, r.right - cr.left); maxy = Math.max(maxy, r.bottom - cr.top); }
        befores = promoteAll(group, card);
        for (var i = 0; i < group.length; i++) bases.push({ l: parseFloat(group[i].style.left) || 0, t: parseFloat(group[i].style.top) || 0 });
        gx0 = minx; gy0 = miny; gw = maxx - minx; gh = maxy - miny;
      }
      var dx = ev.clientX - downX, dy = ev.clientY - downY;
      // 집합 좌상단을 경계 클램프 후 스냅 → 전 요소에 동일 델타
      var nbx = clamp(gx0 + dx, 0, CARD_W - gw), nby = clamp(gy0 + dy, 0, CARD_H - gh);
      var sn = snapMove(card, group, nbx, nby, gw, gh);
      var ddx = sn.left - gx0, ddy = sn.top - gy0;
      for (var i = 0; i < group.length; i++) {
        group[i].style.left = clamp(bases[i].l + ddx, 0, CARD_W - group[i].offsetWidth) + 'px';
        group[i].style.top = clamp(bases[i].t + ddy, 0, CARD_H - group[i].offsetHeight) + 'px';
      }
      positionOverlay();
    }
    function up() {
      document.removeEventListener('mousemove', move, true);
      document.removeEventListener('mouseup', up, true);
      clearGuides();
      if (dragging) {
        var cmds = [];
        for (var i = 0; i < group.length; i++) cmds.push(layoutCmd(group[i], befores[i], snapInline(group[i])));
        pushCmd(cmds.length === 1 ? cmds[0] : compositeCmd(cmds));
        emitSelected(); afterMutate();
      } else if (collapse) { select(el); } // 다중 중 하나 plain클릭 → 단일 축소
    }
    document.addEventListener('mousemove', move, true);
    document.addEventListener('mouseup', up, true);
  }

  function startResize(dir, e) {
    var el = primary(); if (!el || selection.length !== 1) return;
    e.preventDefault(); e.stopPropagation();
    var card = cardOf(el); if (!card) return;
    var before = snapInline(el);
    promoteAll([el], card);
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
    var el = primary(); if (!el || !isAbsolute(el)) return;
    var before = snapInline(el);
    var after = {}; for (var i = 0; i < LAYOUT_PROPS.length; i++) after[LAYOUT_PROPS[i]] = '';
    applyInline(el, after);
    pushCmd(layoutCmd(el, before, after));
    emitSelected(); afterMutate();
  }

  // ── 정렬·분배 (집합 바운딩박스 기준) ──────────────────────────────────────────
  // R2 준수: rect(자연좌표)를 promote 전에 전원 캡처 → promote → 좌표 적용.
  function alignSelection(axis) {
    var els = selection.slice(); if (els.length < 2) return;
    var card = cardOf(els[0]); if (!card) return;
    var cr = card.getBoundingClientRect();
    var boxes = [], minx = 1e9, miny = 1e9, maxx = -1e9, maxy = -1e9;
    for (var i = 0; i < els.length; i++) {
      var r = els[i].getBoundingClientRect();
      var o = { l: r.left - cr.left, t: r.top - cr.top, w: r.width, h: r.height };
      boxes.push(o); minx = Math.min(minx, o.l); miny = Math.min(miny, o.t); maxx = Math.max(maxx, o.l + o.w); maxy = Math.max(maxy, o.t + o.h);
    }
    var befores = promoteAll(els, card);
    var cmds = [];
    for (var i = 0; i < els.length; i++) {
      var el = els[i], o = boxes[i], after = snapInline(el);
      var nl = parseFloat(el.style.left) || 0, nt = parseFloat(el.style.top) || 0;
      if (axis === 'left') nl = minx;
      else if (axis === 'right') nl = maxx - o.w;
      else if (axis === 'hcenter') nl = (minx + maxx) / 2 - o.w / 2;
      else if (axis === 'top') nt = miny;
      else if (axis === 'bottom') nt = maxy - o.h;
      else if (axis === 'vcenter') nt = (miny + maxy) / 2 - o.h / 2;
      after.left = nl + 'px'; after.top = nt + 'px';
      cmds.push(layoutCmd(el, befores[i], after)); applyInline(el, after);
    }
    pushCmd(compositeCmd(cmds)); emitSelected(); afterMutate();
  }
  // 인접 요소 간 간격(edge-to-edge) 균등화, 양 끝 고정.
  function distributeSelection(axis) {
    var els = selection.slice(); if (els.length < 3) return;
    var card = cardOf(els[0]); if (!card) return;
    var cr = card.getBoundingClientRect();
    var items = [];
    for (var i = 0; i < els.length; i++) {
      var el = els[i], r = el.getBoundingClientRect();
      items.push({ el: el, before: snapInline(el), l: r.left - cr.left, t: r.top - cr.top, w: r.width, h: r.height });
    }
    items.sort(function (a, b) { return axis === 'h' ? (a.l - b.l) : (a.t - b.t); });
    promoteAll(els, card);
    var n = items.length, cmds = [];
    if (axis === 'h') {
      var span = (items[n - 1].l + items[n - 1].w) - items[0].l, total = 0;
      for (var i = 0; i < n; i++) total += items[i].w;
      var gap = (span - total) / (n - 1), cur = items[0].l;
      for (var i = 0; i < n; i++) { var it = items[i], after = snapInline(it.el); after.left = cur + 'px'; cmds.push(layoutCmd(it.el, it.before, after)); applyInline(it.el, after); cur += it.w + gap; }
    } else {
      var span = (items[n - 1].t + items[n - 1].h) - items[0].t, total = 0;
      for (var i = 0; i < n; i++) total += items[i].h;
      var gap = (span - total) / (n - 1), cur = items[0].t;
      for (var i = 0; i < n; i++) { var it = items[i], after = snapInline(it.el); after.top = cur + 'px'; cmds.push(layoutCmd(it.el, it.before, after)); applyInline(it.el, after); cur += it.h + gap; }
    }
    pushCmd(compositeCmd(cmds)); emitSelected(); afterMutate();
  }

  // ── 수치 입력(SET_RECT) ──────────────────────────────────────────────────────
  // 단일: left/top/width/height 직접. 다중: X/Y=집합 좌상단 → 전체 이동(델타). W/H 무시(범위 밖).
  function setRect(d) {
    var els = selection.slice(); if (!els.length) return;
    var card = cardOf(primary()); if (!card) return;
    if (els.length === 1) {
      var el = els[0], before = snapInline(el);
      promoteAll([el], card);
      var after = snapInline(el);
      if (d.width != null) after.width = Math.max(12, parseFloat(d.width) || 0) + 'px';
      if (d.height != null) after.height = Math.max(12, parseFloat(d.height) || 0) + 'px';
      applyInline(el, after);
      var w = el.offsetWidth, h = el.offsetHeight;
      if (d.left != null) after.left = clamp(parseFloat(d.left) || 0, 0, CARD_W - w) + 'px';
      if (d.top != null) after.top = clamp(parseFloat(d.top) || 0, 0, CARD_H - h) + 'px';
      applyInline(el, after);
      pushCmd(layoutCmd(el, before, after)); emitSelected(); afterMutate();
    } else {
      var cr = card.getBoundingClientRect(), minx = 1e9, miny = 1e9;
      for (var i = 0; i < els.length; i++) { var r = els[i].getBoundingClientRect(); minx = Math.min(minx, r.left - cr.left); miny = Math.min(miny, r.top - cr.top); }
      var dx = (d.left != null) ? ((parseFloat(d.left) || 0) - minx) : 0;
      var dy = (d.top != null) ? ((parseFloat(d.top) || 0) - miny) : 0;
      if (!dx && !dy) return;
      var befores = promoteAll(els, card), cmds = [];
      for (var i = 0; i < els.length; i++) {
        var el = els[i], after = snapInline(el);
        after.left = clamp((parseFloat(el.style.left) || 0) + dx, 0, CARD_W - el.offsetWidth) + 'px';
        after.top = clamp((parseFloat(el.style.top) || 0) + dy, 0, CARD_H - el.offsetHeight) + 'px';
        cmds.push(layoutCmd(el, befores[i], after)); applyInline(el, after);
      }
      pushCmd(compositeCmd(cmds)); emitSelected(); afterMutate();
    }
  }

  // ── serialize (편집 아티팩트 제거한 클린 HTML) ────────────────────────────────
  function serialize() {
    var clone = document.documentElement.cloneNode(true);
    var rm = clone.querySelectorAll('[data-pi-artifact],[data-pi-agent]');
    for (var i = 0; i < rm.length; i++) rm[i].parentNode.removeChild(rm[i]);
    var ce = clone.querySelectorAll('[contenteditable]');
    for (var j = 0; j < ce.length; j++) { ce[j].removeAttribute('contenteditable'); ce[j].style.outline = ''; }
    return '<!DOCTYPE html>\\n' + clone.outerHTML;
  }

  function setMode(m) {
    commitTextEdit();
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
      case 'ALIGN': alignSelection(d.axis); break;
      case 'DISTRIBUTE': distributeSelection(d.axis); break;
      case 'SET_RECT': setRect(d); break;
      case 'APPLY_STYLE': {
        var el = primary();
        if (el) {
          pushCmd(propCmd(el, d.prop, el.style[d.prop] || '', d.value));
          el.style[d.prop] = d.value;
          positionOverlay(); post('DIRTY', {}); postHeight(); emitSelected();
        }
        break;
      }
      case 'DELETE_ELEMENT': {
        var el = primary();
        if (el) {
          var parent = el.parentNode, next = el.nextSibling;
          pushCmd({ run: function () { parent.removeChild(el); }, undo: function () { parent.insertBefore(el, next); } });
          parent.removeChild(el);
          selection = []; positionOverlay();
          post('DESELECTED', {}); afterMutate();
        }
        break;
      }
      case 'MOVE_ELEMENT': {
        var s = primary();
        if (s) {
          var p = s.parentNode;
          var doUp = function () { if (s.previousElementSibling) p.insertBefore(s, s.previousElementSibling); };
          var doDown = function () { if (s.nextElementSibling) p.insertBefore(s.nextElementSibling, s); };
          if (d.dir === 'up' && s.previousElementSibling) { pushCmd({ run: doUp, undo: doDown }); doUp(); }
          else if (d.dir === 'down' && s.nextElementSibling) { pushCmd({ run: doDown, undo: doUp }); doDown(); }
          afterMutate();
        }
        break;
      }
    }
  });

  document.addEventListener('mousedown', onMouseDown, true);
  document.addEventListener('input', onInput, true);
  // 텍스트 편집 포착: beforeinput에서 변경 전 innerHTML 캡처(재편집도 자동 재무장), 포커스아웃에 커밋.
  document.addEventListener('beforeinput', function (e) {
    var t = e.target;
    if (!editingEl && t && t.getAttribute && t.getAttribute('contenteditable')) beginTextEdit(t);
  }, true);
  document.addEventListener('focusout', function () { commitTextEdit(); }, true);
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
