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
  var markPool = [];       // 팩트 점프 하이라이트(수치 위 마커) — 선택 오버레이와 별도 풀
  var markRects = [];      // 현재 마킹된 사각형(스크롤·리사이즈 시 재배치용)
  var hlGen = 0;           // 하이라이트 세대 — 새 요청/clear 때 증가, 늦은 재시도가 새 카드를 덮지 않게
  var groupBox = null;     // 2개+ 선택 시 집합 바운딩박스(점선)
  var handles = [];        // 8방향 리사이즈 핸들(단일 선택 시만)
  var guides = [];         // 스냅 정렬 가이드선
  var spacingEls = [];     // 드래그 중 이웃 간격 측정(선+숫자 배지) — 가이드와 함께 정리
  var dimBadge = null;     // 선택 요소 치수(W×H) 배지
  var paged = false;       // 편집 모드 한 장씩 페이징(3f)
  var activeCard = 0;      // 현재 페이지(0-based)
  var pageStyle = null;    // .pi-hidden 숨김 스타일시트(아티팩트)
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
    // SVG 안쪽 도형(path/circle 등)은 x/y 속성이라 CSS left/top 무효 → 루트 <svg>로 승격(원자 선택).
    // ownerSVGElement는 가장 가까운 조상 svg(루트면 null) → 최외곽 svg까지 오른다.
    if (el.ownerSVGElement) { var s = el; while (s.ownerSVGElement) s = s.ownerSVGElement; el = s; }
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
      fontWeight: cs.fontWeight, background: el.style.background || el.style.backgroundColor || '',
      letterSpacing: cs.letterSpacing, lineHeight: cs.lineHeight,  // 텍스트 세밀(자간·행간=computed)
      textShadow: el.style.textShadow || '',  // 그림자=인라인(프리셋 정확매칭용, background와 동일 패턴)
      borderRadius: cs.borderTopLeftRadius, objectFit: cs.objectFit, opacity: cs.opacity  // 이미지 트리트먼트
    };
  }
  // 선택 요소에 불투명 난수 data-eid 스탬프(1회, 위치·서수 무관). data-pi-*가 아니라 serialize 생존.
  // setAttribute는 'input' 이벤트를 안 내므로 dirty·undo에 영향 없음(메타 부여이지 콘텐츠 편집 아님).
  function ensureEid(el) {
    if (!el.getAttribute('data-eid')) {
      el.setAttribute('data-eid', 'e' + Math.random().toString(36).slice(2, 10));
    }
    return el.getAttribute('data-eid');
  }
  function clamp(v, min, max) { return Math.max(min, Math.min(max, v)); }
  // ★ SVG 루트는 offsetWidth/Height가 undefined(HTML 레이아웃 박스가 아님) → getBoundingClientRect 폴백.
  // 없으면 CARD_W - offsetWidth = NaN → clamp NaN → style.left='NaNpx'(무효) → SVG 이동·드래그·수치이동 불가
  // (레이어 패널이 SVG를 선택 가능하게 만들며 드러난 이동 블로커). HTML은 offsetWidth 그대로(무회귀).
  function offW(el) { var v = el.offsetWidth; return (v == null) ? Math.round(el.getBoundingClientRect().width) : v; }
  function offH(el) { var v = el.offsetHeight; return (v == null) ? Math.round(el.getBoundingClientRect().height) : v; }

  function primary() { return selection.length ? selection[selection.length - 1] : null; }
  function inSelection(el) { return selection.indexOf(el) >= 0; }
  // 이 지점이 편집 중인 텍스트 안인가 — 텍스트 긁기와 요소 드래그를 가르는 판정.
  function editableHostOf(t) {
    if (t && t.nodeType === 3) t = t.parentElement;
    if (!t || !t.closest) return null;
    return t.closest('[contenteditable="true"]');
  }
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

  // ── 치수 배지(선택/드래그/리사이즈 중 W×H 표시, Figma식) ─────────────────────────
  // body 좌표(오버레이와 동일계). 카드 자연px = 표시 수치(1080폭 캔버스 기준). data-pi-artifact → serialize 제거.
  function showDimBadge(b) {
    if (!dimBadge) {
      dimBadge = document.createElement('div');
      dimBadge.setAttribute('data-pi-artifact', '1');
      dimBadge.style.cssText = 'position:absolute;pointer-events:none;z-index:2147483646;'
        + 'background:#2F6F4E;color:#fff;font:600 12px/1.35 ui-sans-serif,system-ui,-apple-system,sans-serif;'
        + 'padding:2px 7px;border-radius:5px;white-space:nowrap;box-shadow:0 1px 3px rgba(0,0,0,.28);'
        + 'transform:translateX(-50%);display:none;';
      document.body.appendChild(dimBadge);
    }
    dimBadge.textContent = Math.round(b.w) + ' × ' + Math.round(b.h);
    dimBadge.style.display = 'block';
    dimBadge.style.left = (b.x + b.w / 2) + 'px';
    dimBadge.style.top = (b.y + b.h + 7) + 'px';
  }
  function hideDimBadge() { if (dimBadge) dimBadge.style.display = 'none'; }

  // ── 팩트 점프 하이라이트 ────────────────────────────────────────────────────
  // DOM에 <mark>를 넣지 않는다 — 삽입하면 문서가 dirty가 되어 자동저장이 원본을 오염시킨다.
  // Range 좌표만 읽어 오버레이 박스를 띄운다(data-pi-artifact → serialize에서 제거됨).
  function makeMarkEl() {
    var d = document.createElement('div');
    d.setAttribute('data-pi-mark', '1'); d.setAttribute('data-pi-artifact', '1');
    d.style.cssText = 'position:absolute;pointer-events:none;z-index:2147483644;border-radius:3px;'
      + 'background:rgba(250,204,21,.38);box-shadow:0 0 0 2px rgba(202,138,4,.55);display:none;';
    document.body.appendChild(d);
    return d;
  }

  function clearHighlight() {
    hlGen++;   // 진행 중인 재시도 체인 무효화 (아래 highlight 세대 가드)
    markRects = [];
    for (var i = 0; i < markPool.length; i++) markPool[i].style.display = 'none';
  }

  // 현재 카드 안에서 needle이 나오는 모든 위치의 사각형을 모은다.
  function findRects(needle) {
    var cs = cardEls();
    var card = cs[activeCard];
    if (!card || !needle) return [];
    var rects = [];
    var walker = document.createTreeWalker(card, NodeFilter.SHOW_TEXT, null);
    var node;
    while ((node = walker.nextNode())) {
      var text = node.nodeValue || '';
      var from = 0;
      while (true) {
        var at = text.indexOf(needle, from);
        if (at < 0) break;
        var r = document.createRange();
        r.setStart(node, at); r.setEnd(node, at + needle.length);
        var list = r.getClientRects();
        for (var i = 0; i < list.length; i++) {
          var b = list[i];
          if (b.width > 0 && b.height > 0) {
            rects.push({ x: b.left + window.scrollX, y: b.top + window.scrollY, w: b.width, h: b.height });
          }
        }
        from = at + needle.length;
      }
    }
    return rects;
  }

  function positionMarks() {
    for (var i = 0; i < markPool.length; i++) markPool[i].style.display = 'none';
    while (markPool.length < markRects.length) markPool.push(makeMarkEl());
    for (var j = 0; j < markRects.length; j++) placeBox(markPool[j], markRects[j]);
  }

  function locate(value) {
    // 텍스트가 공백으로 갈라져 있을 수 있다("170% 증가" vs "170 % 증가") — 원문 → 공백제거 순으로 시도
    var r = findRects(value);
    if (!r.length) r = findRects(value.replace(/\\s+/g, ''));
    return r;
  }
  function highlight(value, tries, gen) {
    if (gen === undefined) { clearHighlight(); gen = hlGen; }   // 최초 호출: 이전 것 지우고 새 세대 취득
    else if (gen !== hlGen) return;                             // 재시도 도중 새 요청이 왔다 — 이 체인 폐기
    markRects = locate(value);
    positionMarks();
    if (markRects.length) {
      var first = markRects[0];
      window.scrollTo({ top: Math.max(0, first.y - 120), behavior: 'smooth' });
      post('HIGHLIGHTED', { value: value, found: markRects.length });
      return;
    }
    // 못 찾음 — 페이지 전환 직후엔 폰트 로드·레이아웃이 아직이라 좌표가 안 나온다.
    // 폰트 ready와 짧은 rAF 재시도로 정착을 기다린다(최대 6회 ≈ 800ms). 그래도 없으면 '없음' 보고.
    var n = (tries || 0) + 1;
    if (n <= 6) {
      var retry = function () { highlight(value, n, gen); };
      if (document.fonts && document.fonts.status !== 'loaded') document.fonts.ready.then(retry);
      else setTimeout(retry, 130);
      return;
    }
    post('HIGHLIGHTED', { value: value, found: 0 });
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
    if (!selection.length) { showHandles(false); hideDimBadge(); return; }
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
    // 치수 배지: 단일=요소 박스, 다중=집합 박스. 드래그·리사이즈 중 positionOverlay가 매 프레임 갱신 → 라이브.
    showDimBadge(selection.length > 1 ? unionBox(selection) : boxOf(selection[0]));
    positionMarks();   // 마커도 스크롤·리사이즈·줌에 맞춰 재추적
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
    var single = (n === 1);
    post('SELECTED', {
      tag: n > 1 ? ('(다중 ' + n + ')') : p.tagName.toLowerCase(),
      count: n,
      editable: single && isTextLeaf(p),
      absolute: isAbsolute(p),
      isImage: single && p.tagName === 'IMG',
      isBackground: single && p.getAttribute('data-bg') === '1',
      styles: styleSnapshot(p),
      text: single ? (p.textContent || '').slice(0, 80) : '',
      eid: single ? ensureEid(p) : '',
      cardIndex: single ? cardIndexOf(p) : -1,
      quotedText: single ? (p.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 2000) : '',
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
  function afterMutate() { positionOverlay(); post('DIRTY', {}); postHeight(); emitLayers(); }
  function afterHistoryStep() {
    refreshEditable(); pruneSelection();
    if (selection.length) emitSelected(); else post('DESELECTED', {});
    afterMutate(); emitHistory();
  }
  function undo() { commitTextEdit(); var c = undoStack.pop(); if (!c) return; c.undo(); redoStack.push(c); afterHistoryStep(); }
  function redo() { commitTextEdit(); var c = redoStack.pop(); if (!c) return; c.run(); undoStack.push(c); afterHistoryStep(); }

  var LAYOUT_PROPS = ['position', 'left', 'top', 'width', 'height', 'transform', 'margin', 'boxSizing'];
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
  function clearSpacing() { for (var i = 0; i < spacingEls.length; i++) { if (spacingEls[i].parentNode) spacingEls[i].parentNode.removeChild(spacingEls[i]); } spacingEls = []; }
  // 가이드·간격 측정은 둘 다 드래그 순간 힌트 → 함께 정리(매 mousemove·drag end).
  function clearGuides() { clearSpacing(); for (var i = 0; i < guides.length; i++) { if (guides[i].parentNode) guides[i].parentNode.removeChild(guides[i]); } guides = []; }
  function addGuide(card, vertical, pos) {
    var g = document.createElement('div'); g.setAttribute('data-pi-guide', '1'); g.setAttribute('data-pi-artifact', '1');
    g.style.cssText = vertical
      ? 'position:absolute;top:0;bottom:0;left:' + pos + 'px;width:2px;background:#ff3d8b;z-index:2147483646;pointer-events:none;'
      : 'position:absolute;left:0;right:0;top:' + pos + 'px;height:2px;background:#ff3d8b;z-index:2147483646;pointer-events:none;';
    card.appendChild(g); guides.push(g);
  }

  // ── 간격 측정(드래그 중 이웃까지의 픽셀 간격, Figma식 주황 치수선) ───────────────────
  // 카드 상대좌표로 card 자식에 그린다(가이드와 동일계). 선(점선) + 숫자 배지 쌍.
  var SPACE_MAX = 320;  // 이보다 먼 이웃은 그리지 않는다(측정이 의미 있으려면 근접).
  function spacingSeg(card, horizontal, a, b, cross, gap) {
    var col = '#ff3d8b';
    var ln = document.createElement('div'); ln.setAttribute('data-pi-artifact', '1');
    ln.style.cssText = horizontal
      ? 'position:absolute;height:0;left:' + Math.min(a, b) + 'px;top:' + cross + 'px;width:' + Math.abs(b - a) + 'px;border-top:1.5px dashed ' + col + ';z-index:2147483645;pointer-events:none;'
      : 'position:absolute;width:0;top:' + Math.min(a, b) + 'px;left:' + cross + 'px;height:' + Math.abs(b - a) + 'px;border-left:1.5px dashed ' + col + ';z-index:2147483645;pointer-events:none;';
    card.appendChild(ln); spacingEls.push(ln);
    var bd = document.createElement('div'); bd.setAttribute('data-pi-artifact', '1');
    bd.textContent = String(Math.round(gap));
    bd.style.cssText = 'position:absolute;left:' + (horizontal ? (a + b) / 2 : cross) + 'px;top:' + (horizontal ? cross : (a + b) / 2) + 'px;'
      + 'transform:translate(-50%,-50%);background:' + col + ';color:#fff;font:600 11px/1.3 ui-sans-serif,system-ui,-apple-system,sans-serif;'
      + 'padding:1px 5px;border-radius:4px;white-space:nowrap;z-index:2147483646;pointer-events:none;';
    card.appendChild(bd); spacingEls.push(bd);
  }
  // box = 이동 후 카드 상대 박스{x,y,w,h}. 4방향 각각 가장 가까운(겹치는) 이웃까지의 간격을 그린다.
  function showSpacing(card, box, group) {
    var cr = card.getBoundingClientRect();
    var sibs = siblingsOf(card, group);
    var mL = box.x, mR = box.x + box.w, mT = box.y, mB = box.y + box.h;
    var L = null, R = null, T = null, B = null;
    for (var i = 0; i < sibs.length; i++) {
      var r = sibs[i].getBoundingClientRect();
      var sl = r.left - cr.left, st = r.top - cr.top, sR = sl + r.width, sB = st + r.height;
      if (st < mB && sB > mT) {   // 세로 겹침 → 좌/우 이웃
        var cy = Math.max(mT, st) + (Math.min(mB, sB) - Math.max(mT, st)) / 2;
        if (sR <= mL) { var gl = mL - sR; if (gl <= SPACE_MAX && (!L || gl < L.gap)) L = { edge: sR, near: mL, cross: cy, gap: gl }; }
        else if (sl >= mR) { var gr = sl - mR; if (gr <= SPACE_MAX && (!R || gr < R.gap)) R = { edge: sl, near: mR, cross: cy, gap: gr }; }
      }
      if (sl < mR && sR > mL) {   // 가로 겹침 → 상/하 이웃
        var cx = Math.max(mL, sl) + (Math.min(mR, sR) - Math.max(mL, sl)) / 2;
        if (sB <= mT) { var gt = mT - sB; if (gt <= SPACE_MAX && (!T || gt < T.gap)) T = { edge: sB, near: mT, cross: cx, gap: gt }; }
        else if (st >= mB) { var gb = st - mB; if (gb <= SPACE_MAX && (!B || gb < B.gap)) B = { edge: st, near: mB, cross: cx, gap: gb }; }
      }
    }
    if (L) spacingSeg(card, true, L.edge, L.near, L.cross, L.gap);
    if (R) spacingSeg(card, true, R.near, R.edge, R.cross, R.gap);
    if (T) spacingSeg(card, false, T.edge, T.near, T.cross, T.gap);
    if (B) spacingSeg(card, false, B.near, B.edge, B.cross, B.gap);
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
  // ★ 절대배치의 실제 기준(containing block) = 부모 체인에서 가장 가까운 positioned 조상.
  // el.offsetParent를 쓰면 안 되는 이유: SVG 등은 offsetParent가 null이라 '|| card' 폴백이
  // 걸리는데, SVG의 실제 containing block이 중첩된 absolute 래퍼면 card 기준으로 계산한 top/left이
  // 래퍼 오프셋만큼(예:150px) 어긋난다(구슬이 제목을 덮는 편집진입 변형의 근본원인). 부모 체인을
  // 직접 걸어 올라가면 SVG·HTML 모두 정확 — HTML은 offsetParent와 동일 결과라 무회귀.
  function posAncestor(el, card) {
    var p = el.parentElement;
    while (p && p !== card) {
      if (getComputedStyle(p).position !== 'static') return p;
      p = p.parentElement;
    }
    return card;
  }
  // R2 방지: 여러 요소 승격 시 '전원 rect를 먼저 캡처 → 그 다음 전원 promote → 캡처값으로 배치'.
  function promoteAll(els, card) {
    if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
    var cr = card.getBoundingClientRect();
    var snaps = [], rects = [];
    for (var i = 0; i < els.length; i++) { snaps.push(snapInline(els[i])); rects.push(els[i].getBoundingClientRect()); }
    for (var i = 0; i < els.length; i++) {
      var el = els[i], r = rects[i];
      if (getComputedStyle(el).position !== 'absolute') {
        // measured 값은 border-box(getBoundingClientRect) → box-sizing 고정해야 w/h가 정확(content-box면 padding만큼 팽창 방지)
        // ★ Math.ceil: 서브픽셀(89.6px 등)을 올림 → 고정폭이 텍스트보다 미세하게 좁아 wrap/clip되는 것 방지.
        el.style.boxSizing = 'border-box';
        el.style.width = Math.ceil(r.width) + 'px'; el.style.height = Math.ceil(r.height) + 'px';
        // ★ 절대배치에선 margin이 border-box를 밀어 left/top과 어긋남 → 0으로. left/top이 곧 border-box 위치.
        // (margin은 LAYOUT_PROPS라 undo/revertFlow가 원복. margin 있는 요소 grab 점프·가장자리 못 닿음 수정)
        el.style.margin = '0';
        el.style.position = 'absolute';
        // ★ left/top은 카드가 아니라 '실제 containing block'(가장 가까운 positioned 조상) 기준이어야
        // 제자리 유지. offsetParent 대신 posAncestor를 쓴다 — SVG는 offsetParent가 null이라 card로
        // 폴백되며 래퍼 오프셋만큼 어긋난다(구슬 겹침 버그).
        var op = posAncestor(el, card), opr = op.getBoundingClientRect();
        el.style.left = (r.left - opr.left) + 'px'; el.style.top = (r.top - opr.top) + 'px';
      }
    }
    return snaps; // promote 이전 인라인 스냅(undo용 before)
  }

  // ── 프리즈: 편집모드에서 카드 처음 보일 때 1회, 전 flow 요소를 현재 위치로 절대배치 고정 ──────
  // 목적: 하나를 옮겨도 나머지가 reflow로 안 흔들리게(Figma 모델 — 처음부터 전부 절대배치).
  // measure-all→promote-all을 '문서순(부모 먼저)'으로 → 각 자식의 offsetParent가 이미 제자리라 좌표 정확.
  // inline은 제외(부모 블록이 고정되면 그 안에서 정상 wrap). BR·이미 배치(absolute/fixed)·아티팩트 제외.
  // 픽셀 무이동: promoteAll이 margin:0 + box-sizing:border-box + measured w/h/left/top으로 제자리 착지.
  // 요소가 '맨 텍스트노드'(공백 제외)를 직접 자식으로 가지면 mixed content — 그 안의 요소를 절대배치로
  // 빼내면 남은 맨 텍스트가 밀려 겹침(예: kicker <div flex><span dot></span> 핵심원리…</div>).
  function hasBareText(el) {
    if (!el) return false;
    var ch = el.childNodes;
    for (var i = 0; i < ch.length; i++) {
      if (ch[i].nodeType === 3 && ch[i].nodeValue && ch[i].nodeValue.trim().length) return true;
    }
    return false;
  }
  // ★ 자식을 잃고 붕괴할 컨테이너(승격 대상이 아닌 = 이미 absolute/제외된 것)의 박스를 측정값으로 고정.
  // bottom-앵커 + height:auto 컨테이너는 자식이 흐름에서 빠지면 붕괴→윗변이 하강하고, promoteAll이 붕괴
  // 중인 offsetParent 좌표를 읽어 자식들이 압축·겹친다(크레딧 카드 마감 버그). 승격 前에 부모 박스를
  // 못박아 붕괴를 차단 → offsetParent 안정 → 자식 픽셀 무이동. (top-앵커는 안 밀리지만 고정해도 무해.)
  function pinCollapsingContainers(els, card) {
    var targets = [];
    for (var i = 0; i < els.length; i++) {
      var a = els[i].parentElement;
      while (a && a !== card) {
        if (els.indexOf(a) < 0 && targets.indexOf(a) < 0) targets.push(a);
        a = a.parentElement;
      }
    }
    var rects = [];  // 먼저 전원 측정(고정이 다음 측정을 흔들지 않게)
    for (var i = 0; i < targets.length; i++) rects.push(targets[i].getBoundingClientRect());
    for (var i = 0; i < targets.length; i++) {
      var t = targets[i], r = rects[i];
      t.style.boxSizing = 'border-box';
      t.style.width = Math.ceil(r.width) + 'px';
      t.style.height = Math.ceil(r.height) + 'px';
    }
  }
  // ★ 부모가 inline 흐름 자식을 가지면(마커펜 하이라이트용 display:inline 제목 등) 그 형제도 승격 금지.
  // inline은 승격에서 제외(display:inline continue)되므로, 형제 block만 흐름에서 빠지면 inline이 빈자리로
  // 밀려 겹친다(치약 표지 카드: eyebrow block 승격 → inline 제목이 27px 상승 겹침). hasBareText(맨 텍스트
  // mixed)와 같은 원리 — 대상만 '맨 텍스트'에서 'inline 요소'로 확장. mixed 컨테이너는 통째 프리즈한다.
  function hasInlineFlowChild(parent) {
    if (!parent) return false;
    var ch = parent.children;
    for (var i = 0; i < ch.length; i++) {
      var c = ch[i];
      if (isPiArtifact(c)) continue;
      var cs = getComputedStyle(c);
      if (cs.position === 'absolute' || cs.position === 'fixed') continue;
      if (cs.display === 'inline') return true;
    }
    return false;
  }
  function freezeCard(card) {
    if (!card || card.getAttribute('data-pi-frozen') === '1') return;
    // ★ 렌더되지 않은 카드는 측정할 수 없다. display:none이면 getBoundingClientRect가 전부 0이라
    // width:0/height:0을 박고 data-pi-frozen까지 붙어 되돌릴 기회도 사라진다 — 그 카드로 돌아오면
    // 폭 0에서 한글이 한 글자씩 흘러 텍스트가 세로로 보인다(2026-07-26 제보).
    // 이 경로는 사용자 조작 없이 열린다: applyPaging이 폰트 로딩 중이면 card를 클로저로 잡아
    // fonts.ready 후에 freeze하는데, 그 사이 SET_PAGE(진입 카드 복원)가 그 카드를 숨긴다.
    // 스킵해도 손실이 없다 — 그 카드가 다시 활성화되면 applyPaging이 freeze를 재시도한다.
    if (!card.getClientRects().length) return;
    if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
    var nodes = card.querySelectorAll('*'), els = [];
    for (var i = 0; i < nodes.length; i++) {
      var el = nodes[i];
      if (isPiArtifact(el) || el.tagName === 'BR') continue;
      var cs = getComputedStyle(el);
      if (cs.position === 'absolute' || cs.position === 'fixed') continue;
      if (cs.display === 'inline') continue;
      // ★ 부모가 mixed content(맨 텍스트 or inline 요소 포함)면 승격 금지 — 부모를 통째 프리즈해 내부
      // 레이아웃(dot+텍스트, eyebrow+마커제목) 보존. 일부만 흐름에서 빼면 남은 것이 밀려 겹친다.
      if (hasBareText(el.parentElement) || hasInlineFlowChild(el.parentElement)) continue;
      els.push(el);
    }
    pinCollapsingContainers(els, card);  // ★ 붕괴할 컨테이너 박스 고정 → 자식 겹침 방지(마감 크레딧 카드)
    promoteAll(els, card);  // 문서순 → 부모 먼저 → 자식 offsetParent 정확
    card.setAttribute('data-pi-frozen', '1');
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
    if (spaceHeld) { e.preventDefault(); startPan(e); return; }   // 스페이스+드래그 = 팬(편집 대신)
    if (e.target && e.target.hasAttribute && e.target.hasAttribute('data-pi-handle')) return; // 핸들은 자체 처리
    // ★ 이미 편집 중인(포커스된) 텍스트를 다시 끌면 = 범위 선택(긁기). 요소를 옮기지 않는다.
    // 텍스트를 긁으려면 이동 임계(3px)를 넘겨야 하는데 그 순간 드래그로 전환하며 clearEditable()과
    // removeAllRanges()가 선택을 지워, 텍스트 범위 선택이 구조적으로 불가능했다(2026-07-26 제보).
    // 여기서 빠지면 브라우저 기본 동작이 캐럿·범위 선택을 처리한다. 옮기려면 편집을 벗어난 뒤 끈다
    // (딴 곳을 클릭하면 포커스가 옮겨가 이 조건이 풀린다) — Figma·Canva와 같은 관례.
    var ceHost = editableHostOf(e.target);
    if (ceHost && document.activeElement === ceHost) return;
    commitTextEdit();  // 선택/드래그 전환 전에 진행 중 텍스트 편집 확정
    var picked = pick(e.target);
    if (!picked) {                              // 빈영역 → 마퀴 시작(additive면 선택 유지)
      if (additive(e)) return;
      startMarquee(e); return;
    }
    // ★ 기하 대상 = 클릭한 리프(Figma식). cardChild 폐기 — offsetParent-aware promote가 좌표 붕괴 처리.
    var el = picked;
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
        // 요소별 offsetParent 오프셋(카드좌표) 캡처 — 중첩 요소의 클램프를 카드공간에서 하기 위함
        for (var i = 0; i < group.length; i++) {
          var op0 = posAncestor(group[i], card), opr0 = op0.getBoundingClientRect();  // SVG offsetParent=null → posAncestor
          bases.push({ l: parseFloat(group[i].style.left) || 0, t: parseFloat(group[i].style.top) || 0, offX: opr0.left - cr.left, offY: opr0.top - cr.top });
        }
        gx0 = minx; gy0 = miny; gw = maxx - minx; gh = maxy - miny;
      }
      var dx = ev.clientX - downX, dy = ev.clientY - downY;
      // 집합 좌상단을 경계 클램프 후 스냅 → 전 요소에 동일 델타
      var nbx = clamp(gx0 + dx, 0, CARD_W - gw), nby = clamp(gy0 + dy, 0, CARD_H - gh);
      var sn = snapMove(card, group, nbx, nby, gw, gh);
      showSpacing(card, { x: sn.left, y: sn.top, w: gw, h: gh }, group);   // 이웃 간격 치수(스냅 가이드와 별개)
      var ddx = sn.left - gx0, ddy = sn.top - gy0;
      for (var i = 0; i < group.length; i++) {
        var w = offW(group[i]), h = offH(group[i]);
        // 카드공간에서 클램프 후 offsetParent 좌표로 환원 — 중첩 요소가 컨테이너 top에 걸려 카드끝까지 못 올라가던 버그 수정(direct child는 off=0 → 무변화)
        var cardL = clamp(bases[i].l + bases[i].offX + ddx, 0, CARD_W - w);
        var cardT = clamp(bases[i].t + bases[i].offY + ddy, 0, CARD_H - h);
        group[i].style.left = (cardL - bases[i].offX) + 'px';
        group[i].style.top = (cardT - bases[i].offY) + 'px';
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
    var baseW = offW(el), baseH = offH(el);   // SVG offsetWidth=undefined 대비(핸들 리사이즈)
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
      var w = offW(el), h = offH(el);
      // ★ 입력값은 카드 좌표 → 실제 containing block 좌표로 변환(중첩·SVG 어긋남 수정). 클램프는 카드 공간에서.
      // posAncestor 사용 — SVG는 offsetParent=null이라 card로 폴백되며 래퍼 오프셋만큼 어긋난다(promoteAll과 동일 규칙).
      var op = posAncestor(el, card), opr = op.getBoundingClientRect(), cardr = card.getBoundingClientRect();
      var offX = opr.left - cardr.left, offY = opr.top - cardr.top;
      if (d.left != null) after.left = (clamp(parseFloat(d.left) || 0, 0, CARD_W - w) - offX) + 'px';
      if (d.top != null) after.top = (clamp(parseFloat(d.top) || 0, 0, CARD_H - h) - offY) + 'px';
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
        after.left = clamp((parseFloat(el.style.left) || 0) + dx, 0, CARD_W - offW(el)) + 'px';
        after.top = clamp((parseFloat(el.style.top) || 0) + dy, 0, CARD_H - offH(el)) + 'px';
        cmds.push(layoutCmd(el, befores[i], after)); applyInline(el, after);
      }
      pushCmd(compositeCmd(cmds)); emitSelected(); afterMutate();
    }
  }

  // ── 이미지 '배경으로 깔기' 토글 (풀블리드 + 콘텐츠 뒤 z-index:-1 ↔ 박스). data-bg/data-box는 serialize 생존.
  function setImageBg() {
    var el = primary();
    if (!el || el.tagName !== 'IMG') return;
    var card = cardOf(el);
    var beforeCss = el.style.cssText, beforeBg = el.getAttribute('data-bg'), beforeBox = el.getAttribute('data-box');
    function setState(css, bg, box) {
      el.style.cssText = css;
      if (bg) el.setAttribute('data-bg', bg); else el.removeAttribute('data-bg');
      if (box) el.setAttribute('data-box', box); else el.removeAttribute('data-box');
    }
    if (beforeBg === '1') {
      // 박스로 되돌리기 — 저장 박스 복원(없으면 기본)
      var box = el.getAttribute('data-box');
      if (box) setState(box, null, null);
      else setState('position:absolute;left:' + ((CARD_W - 400) / 2) + 'px;top:' + ((CARD_H - 300) / 2) + 'px;width:400px;height:300px;object-fit:cover;', null, null);
    } else {
      // 배경으로 — 현재 박스 저장 후 풀블리드(콘텐츠 뒤)
      if (card) { if (getComputedStyle(card).position === 'static') card.style.position = 'relative'; card.style.zIndex = '0'; }
      setState('position:absolute;left:0;top:0;width:100%;height:100%;object-fit:cover;z-index:-1;border-radius:0;', '1', beforeCss);
    }
    var afterCss = el.style.cssText, afterBg = el.getAttribute('data-bg'), afterBox = el.getAttribute('data-box');
    pushCmd({ run: function () { setState(afterCss, afterBg, afterBox); }, undo: function () { setState(beforeCss, beforeBg, beforeBox); } });
    positionOverlay(); emitSelected(); afterMutate();
  }

  // ── serialize (편집 아티팩트 제거한 클린 HTML) ────────────────────────────────
  function serialize() {
    var clone = document.documentElement.cloneNode(true);
    var rm = clone.querySelectorAll('[data-pi-artifact],[data-pi-agent]');
    for (var i = 0; i < rm.length; i++) rm[i].parentNode.removeChild(rm[i]);
    var ce = clone.querySelectorAll('[contenteditable]');
    for (var j = 0; j < ce.length; j++) { ce[j].removeAttribute('contenteditable'); ce[j].style.outline = ''; }
    var ph = clone.querySelectorAll('.pi-hidden');   // 페이징 숨김 흔적 제거 → 7장 온전
    for (var k = 0; k < ph.length; k++) ph[k].classList.remove('pi-hidden');
    var eids = clone.querySelectorAll('[data-eid]');  // 레이어/선택 스탬프 제거 → 발행 HTML 오염 방지
    for (var m = 0; m < eids.length; m++) eids[m].removeAttribute('data-eid');
    return '<!DOCTYPE html>\\n' + clone.outerHTML;
  }

  // ── 페이징 (편집 모드 한 장씩, 3f) ────────────────────────────────────────────
  function cardEls() { return document.querySelectorAll('[data-screen-label]'); }
  function cardIndexOf(el) {
    var card = cardOf(el); if (!card) return -1;
    var cs = cardEls();
    for (var i = 0; i < cs.length; i++) if (cs[i] === card) return i;
    return -1;
  }

  // ── 레이어 패널: 카드의 '원자 요소'(텍스트리프·이미지·SVG루트·가시 도형) 수집 ──────────────
  // freeze 승격 집합과 독립 — 가려진(배경 SVG·풀블리드 div)·inline 요소도 목록에 떠야 클릭 가림을
  // 우회한다(가림이 "안 움직인다"의 정체였다). 컨테이너(자식 있는 래퍼)는 하강만, 목록엔 원자 요소만
  // → 노이즈 없이(래퍼 div 미포함) 누락 없이(SVG·도형·이미지 포착). 실측 3덱 20카드 검증 규칙.
  function paintsSomething(el) {
    var cs = getComputedStyle(el);
    if (parseFloat(cs.opacity) === 0 || cs.visibility === 'hidden') return false;
    var col = cs.backgroundColor;
    if (col && col !== 'rgba(0, 0, 0, 0)' && col !== 'transparent') return true;
    if (cs.backgroundImage && cs.backgroundImage !== 'none') return true;
    if (cs.borderTopWidth !== '0px' || cs.borderRightWidth !== '0px' || cs.borderBottomWidth !== '0px' || cs.borderLeftWidth !== '0px') return true;
    if (cs.boxShadow && cs.boxShadow !== 'none') return true;
    return false;
  }
  function layerLabel(el, kind) {
    if (kind === 'text') return (el.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 40);
    if (kind === 'image') return el.getAttribute('alt') || '이미지';
    if (kind === 'graphic') return '그래픽';
    var r = el.getBoundingClientRect();
    return '도형 ' + Math.round(r.width) + '×' + Math.round(r.height);
  }
  function collectLayers(card) {
    var items = [];
    function visit(el) {
      var kids = el.children;
      for (var i = 0; i < kids.length; i++) {
        var c = kids[i];
        if (isPiArtifact(c) || c.tagName === 'BR') continue;
        var tag = c.tagName.toLowerCase(), kind = null;
        if (tag === 'svg') kind = 'graphic';                 // 루트 svg — 안 파고듦(도형은 원자 아님)
        else if (tag === 'img') kind = 'image';
        else if (isTextLeaf(c)) kind = 'text';               // 텍스트 덩어리 — 안 파고듦(inline span 병합)
        else if (c.childElementCount === 0) {
          var r = c.getBoundingClientRect();
          if (r.width > 4 && r.height > 4 && paintsSomething(c)) kind = 'shape';
          else continue;                                     // 안 보이는 빈 요소 스킵
        } else { visit(c); continue; }                       // 컨테이너 → 하강만
        items.push({ eid: ensureEid(c), kind: kind, label: layerLabel(c, kind) });
      }
    }
    visit(card);
    return items;
  }
  function emitLayers() {
    if (!paged) return;
    var cs = cardEls(), card = cs[activeCard];
    post('LAYERS', { items: card ? collectLayers(card) : [], cardIndex: activeCard });
  }
  // 레이어 목록 행 hover → 캔버스에서 그 요소를 아웃라인(로케이트). 선택 오버레이보다 아래 z(가려짐 표시용
  // 점선). data-pi-artifact라 serialize 제거. 선택과 별개 풀 — hover는 순간 표시, 클릭이 진짜 선택.
  var hoverOv = null;
  function hoverEid(eid) {
    if (!hoverOv) {
      hoverOv = document.createElement('div');
      hoverOv.setAttribute('data-pi-artifact', '1');
      hoverOv.style.cssText = 'position:absolute;pointer-events:none;z-index:2147483643;border:2px dashed #2F6F4E;border-radius:4px;background:rgba(47,111,78,.06);display:none;';
      document.body.appendChild(hoverOv);
    }
    if (!eid) { hoverOv.style.display = 'none'; return; }
    var cs = cardEls(), card = cs[activeCard];
    var el = card && card.querySelector('[data-eid="' + String(eid).replace(/"/g, '') + '"]');
    if (!el) { hoverOv.style.display = 'none'; return; }
    var bx = boxOf(el);
    hoverOv.style.display = 'block';
    hoverOv.style.left = (bx.x - 2) + 'px'; hoverOv.style.top = (bx.y - 2) + 'px';
    hoverOv.style.width = bx.w + 'px'; hoverOv.style.height = bx.h + 'px';
  }

  function ensurePageStyle() {
    if (pageStyle) return;
    pageStyle = document.createElement('style');
    pageStyle.setAttribute('data-pi-artifact', '1');
    // 편집 모드: body 캔버스(프리뷰 배경·패딩·gap)를 정규화 — 현재 카드가 iframe에 꽉 차게.
    // pageStyle은 data-pi-artifact라 serialize에서 제거됨 → 저장/발행 HTML의 body 원본은 보존.
    pageStyle.textContent = '.pi-hidden{display:none !important;}' +
      'html,body{margin:0 !important;padding:0 !important;background:transparent !important;}' +
      'body{display:block !important;}';
    (document.head || document.documentElement).appendChild(pageStyle);
  }
  function applyPaging() {
    var cs = cardEls();
    if (activeCard < 0) activeCard = 0;
    if (activeCard > cs.length - 1) activeCard = cs.length - 1;
    for (var i = 0; i < cs.length; i++) {
      if (i === activeCard) cs[i].classList.remove('pi-hidden');
      else cs[i].classList.add('pi-hidden');
    }
    // ★ 프리즈는 폰트 로드 完了 후 측정해야 함 — 웹폰트(JetBrains Mono 등) 로드 前 fallback 메트릭으로
    // 고정폭/높이를 박으면 진짜 폰트 로드 시 텍스트가 넓/커져 wrap·overflow(뷰어PNG는 폰트후 렌더라 정상).
    var card = cs[activeCard];
    if (card && document.fonts && document.fonts.status !== 'loaded') {
      document.fonts.ready.then(function () { freezeCard(card); positionOverlay(); postHeight(); emitLayers(); });
    } else {
      freezeCard(card);
      emitLayers();
    }
    positionOverlay(); postHeight();
  }
  function clearPaging() {
    var ph = document.querySelectorAll('.pi-hidden');
    for (var i = 0; i < ph.length; i++) ph[i].classList.remove('pi-hidden');
    postHeight();
  }
  function emitPage() { post('PAGE', { index: activeCard, count: cardEls().length }); }
  function setPage(index) {
    if (!paged) return;
    var n = cardEls().length;
    activeCard = Math.max(0, Math.min(index, n - 1));
    deselect();          // 이전 페이지 선택의 유령 오버레이 방지
    clearHighlight();    // 다른 카드로 넘어가면 이전 카드의 마커는 무효
    applyPaging(); emitPage();
  }

  function setMode(m) {
    commitTextEdit();
    mode = m;
    document.body.style.cursor = (m === 'edit') ? 'default' : '';
    if (m !== 'edit') {
      deselect();
      paged = false; clearPaging();
    } else {
      paged = true; ensurePageStyle(); applyPaging(); emitPage();
      positionOverlay();
    }
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
      case 'SELECT_EID': {
        var cs2 = cardEls(), card2 = cs2[activeCard];
        var t = card2 && card2.querySelector('[data-eid="' + String(d.eid || '').replace(/"/g, '') + '"]');
        if (t) select(t);
        break;
      }
      case 'HOVER_EID': hoverEid(d.eid); break;
      case 'UNDO': undo(); break;
      case 'REDO': redo(); break;
      case 'REVERT_FLOW': revertFlow(); break;
      case 'ALIGN': alignSelection(d.axis); break;
      case 'DISTRIBUTE': distributeSelection(d.axis); break;
      case 'SET_RECT': setRect(d); break;
      case 'SET_IMAGE_BG': setImageBg(); break;
      case 'SET_PAGE': setPage(d.index); break;
      case 'HIGHLIGHT': highlight(String(d.value || '')); break;
      case 'CLEAR_HIGHLIGHT': clearHighlight(); break;
      case 'APPLY_STYLE': {
        var el = primary();
        if (el) {
          pushCmd(propCmd(el, d.prop, el.style[d.prop] || '', d.value));
          el.style[d.prop] = d.value;
          positionOverlay(); post('DIRTY', {}); postHeight(); emitSelected();
        }
        break;
      }
      case 'INSERT_IMAGE': {
        var cards = cardEls();
        var card = cards[activeCard];   // 삽입 대상 = 현재 보이는 카드만(숨은 카드 금지)
        if (!card) break;
        if (getComputedStyle(card).position === 'static') card.style.position = 'relative';
        var img = document.createElement('img');
        img.src = d.url;
        // 메타는 data-* 로(serialize가 data-pi-* 만 제거 → 이건 생존). data-pi-artifact 절대 금지.
        img.setAttribute('data-asset-id', d.assetId || '');
        img.setAttribute('data-source-type', d.sourceType || 'upload-owned');
        if (d.provider) img.setAttribute('data-provider', d.provider);
        if (d.credit) img.setAttribute('data-credit', d.credit);
        if (d.creditUrl) img.setAttribute('data-credit-url', d.creditUrl);
        // element 프리셋: absolute + 명시 px(height:auto 금지 — setRect/resize의 offsetWidth 로직이 px 요구).
        var IW = 400, IH = 300;
        img.style.position = 'absolute';
        img.style.width = IW + 'px';
        img.style.height = IH + 'px';
        img.style.left = ((CARD_W - IW) / 2) + 'px';
        img.style.top = ((CARD_H - IH) / 2) + 'px';
        img.style.objectFit = 'cover';
        // undo 보편성(3e 불변식): 삽입도 되돌리기 가능. run=append, undo=remove.
        pushCmd({
          run: function () { card.appendChild(img); },
          undo: function () { if (img.parentNode) img.parentNode.removeChild(img); }
        });
        card.appendChild(img);
        select(img);
        afterMutate();
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

  // ── 캔버스 팬/줌 제스처 → 부모 포워딩(iframe이 이벤트를 삼켜 카드 위에서 직접 팬/줌 불가) ──
  // 휠: 일반=팬, Ctrl/⌘(핀치)=커서 기준 줌. 스페이스+드래그=팬. 좌표(cx,cy)는 iframe 자연px(부모가 환산).
  var spaceHeld = false;
  function startPan(e) {
    var lx = e.clientX, ly = e.clientY;
    function mv(ev) {
      post('VIEWPORT', { kind: 'pan', dx: -(ev.clientX - lx), dy: -(ev.clientY - ly), drag: true });
      lx = ev.clientX; ly = ev.clientY;
    }
    function up() { document.removeEventListener('mousemove', mv, true); document.removeEventListener('mouseup', up, true); }
    document.addEventListener('mousemove', mv, true);
    document.addEventListener('mouseup', up, true);
  }
  window.addEventListener('wheel', function (e) {
    if (mode !== 'edit') return;
    e.preventDefault();
    if (e.ctrlKey || e.metaKey) post('VIEWPORT', { kind: 'zoom', delta: e.deltaY, cx: e.clientX, cy: e.clientY });
    else post('VIEWPORT', { kind: 'pan', dx: e.deltaX, dy: e.deltaY });
  }, { passive: false });
  window.addEventListener('keydown', function (e) {
    if (mode === 'edit' && (e.code === 'Space' || e.key === ' ') &&
        !(document.activeElement && document.activeElement.isContentEditable)) {
      if (!spaceHeld) { spaceHeld = true; document.body.style.cursor = 'grab'; }
      e.preventDefault();
    }
  }, true);
  window.addEventListener('keyup', function (e) {
    if (e.code === 'Space' || e.key === ' ') { spaceHeld = false; if (mode === 'edit') document.body.style.cursor = 'default'; }
  }, true);

  post('EDITOR_READY', {});
  emitHistory();
  postHeight();
})();
`;

export default AGENT_BODY;
