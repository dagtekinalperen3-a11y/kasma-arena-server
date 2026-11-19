/* Reklam Veriyor — pano: yerleşim, yakınlaştırma, alan seçimi, ödeme öncesi özet */
'use strict';

(() => {
  const { $, h, api, toast, modal, field, fmtTL, fmtNum, fmtDate, buildAd, openAdCard, placeRect, requireLogin } = RV;

  const stage = $('#stage');
  const boardEl = $('#board');
  const adsEl = $('#ads');
  const overlay = $('#overlay');
  const selbox = $('#selbox');
  const seltag = $('#seltag');
  const hoverEl = $('#hovercell');
  const dock = $('#dock');
  const selpanel = $('#selpanel');
  const advBtn = $('#btn-advertise');

  let B = null;          // pano ölçüleri (sanal piksel / blok)
  let pricing = null;
  let payment = null;
  let ads = [];
  let taken = [];
  const adById = new Map();
  let mode = 'view';
  let sel = null;        // {x, y, w, h} blok cinsinden
  const view = { fit: 1, scale: 1, tx: 0, ty: 0 };
  const MAX_SCALE = 8;   // 1 sanal piksel = en fazla 8 ekran pikseli
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));

  // ---------------------------------------------------------------- görünüm
  const vw = () => stage.clientWidth;
  const vh = () => stage.clientHeight;

  function computeFit() {
    view.fit = Math.min(vw() / B.width, vh() / B.height);
  }

  // Telefonda alt menü ve seçim paneli ekranın altını kaplar; pano sığıyorsa
  // onların üstündeki boş alana ortalanır, böylece hiçbir reklamı örtmezler.
  function freeHeight() {
    let top = vh();
    const d = dock.getBoundingClientRect();
    if (d.height) top = Math.min(top, d.top);
    if (!selpanel.hidden && narrow.matches) top = Math.min(top, selpanel.getBoundingClientRect().top);
    return top - 8;
  }
  const narrow = matchMedia('(max-width: 760px)');

  function apply() {
    const bw = B.width * view.scale, bh = B.height * view.scale;
    view.tx = bw <= vw() ? (vw() - bw) / 2 : clamp(view.tx, vw() - bw, 0);
    const free = freeHeight();
    if (bh <= free - 8) view.ty = Math.max(8, (free - bh) / 2);
    else view.ty = bh <= vh() ? (vh() - bh) / 2 : clamp(view.ty, vh() - bh, 0);
    boardEl.style.width = bw + 'px';
    boardEl.style.height = bh + 'px';
    boardEl.style.transform = 'translate3d(' + view.tx + 'px,' + view.ty + 'px,0)';
    boardEl.classList.toggle('dense', B.block * view.scale < 6);
    const freeBelow = vh() - (view.ty + bh);
    dock.classList.toggle('over', freeBelow < dock.offsetHeight + 20);
    positionPanel();
  }

  function zoomTo(scale, cx = vw() / 2, cy = vh() / 2) {
    scale = clamp(scale, view.fit, Math.max(MAX_SCALE, view.fit));
    const k = scale / view.scale;
    view.tx = cx - (cx - view.tx) * k;
    view.ty = cy - (cy - view.ty) * k;
    view.scale = scale;
    apply();
  }

  function fitView() {
    computeFit();
    view.scale = view.fit;
    apply();
  }

  window.addEventListener('resize', () => {
    if (!B) return;
    const wasFit = Math.abs(view.scale - view.fit) < 1e-6;
    computeFit();
    if (wasFit || view.scale < view.fit) view.scale = view.fit;
    apply();
  });

  function cellAt(clientX, clientY) {
    const r = boardEl.getBoundingClientRect();
    const vx = (clientX - r.left) / view.scale, vy = (clientY - r.top) / view.scale;
    return {
      cx: clamp(Math.floor(vx / B.block), 0, B.cols - 1),
      cy: clamp(Math.floor(vy / B.block), 0, B.rows - 1),
      inside: vx >= 0 && vy >= 0 && vx < B.width && vy < B.height,
    };
  }

  // ---------------------------------------------------------------- veri
  async function load() {
    const d = await api('/api/board');
    B = d.board;
    pricing = d.pricing;
    payment = d.payment;
    ads = d.ads;
    taken = d.taken;
    boardEl.style.setProperty('--cols', B.cols);
    boardEl.style.setProperty('--rows', B.rows);
    renderAds();
    renderTaken();
    if (sel) renderSel();
    $('#test-chip').hidden = payment.live;
    $('#empty-hint').hidden = !(ads.length === 0 && taken.length === 0 && mode === 'view');
  }

  function renderAds() {
    adById.clear();
    io.disconnect();
    const frag = document.createDocumentFragment();
    const shown = new Set();
    for (const ad of ads) {
      adById.set(ad.id, ad);
      shown.add(ad.id);
      const el = buildAd(ad, { board: B });
      frag.append(el);
      io.observe(el);
    }
    // satılmış ama içeriği henüz yüklenmemiş alanlar
    for (const t of taken) {
      if (t.state !== 'sold' || shown.has(t.slot_id)) continue;
      const el = h('div', { class: 'ad placeholder', title: 'Bu alan satıldı' }, 'Satıldı');
      placeRect(el, t, B);
      frag.append(el);
    }
    adsEl.replaceChildren(frag);
  }

  function renderTaken() {
    const frag = document.createDocumentFragment();
    for (const t of taken) {
      const label = t.mine ? (t.state === 'reserved' ? 'Rezerve (senin)' : 'Senin') : (t.state === 'reserved' ? 'Rezerve' : 'Satıldı');
      const el = h('div', { class: 'taken ' + t.state + (t.mine ? ' mine' : '') }, h('span', null, label));
      placeRect(el, t, B);
      frag.append(el);
    }
    overlay.replaceChildren(frag);
  }

  // ---------------------------------------------------------------- gösterim sayımı
  const visitorId = (() => {
    try {
      let v = localStorage.getItem('rv_v');
      if (!v) {
        v = (crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2) + Date.now().toString(36));
        localStorage.setItem('rv_v', v);
      }
      return v;
    } catch (e) { return ''; }
  })();
  const counted = new Set();
  const queue = new Set();
  const io = new IntersectionObserver(entries => {
    if (document.hidden) return;
    for (const en of entries) {
      if (!en.isIntersecting || en.intersectionRatio < 0.5) continue;
      const id = +en.target.dataset.id;
      if (id && !counted.has(id)) { counted.add(id); queue.add(id); }
    }
  }, { threshold: [0.5] });

  function flush() {
    if (!queue.size) return;
    const ids = Array.from(queue);
    queue.clear();
    fetch('/api/track', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, keepalive: true,
      body: JSON.stringify({ ids, v: visitorId }),
    }).catch(() => {});
  }
  setInterval(flush, 2500);
  document.addEventListener('visibilitychange', () => {
    if (document.hidden) { flush(); return; }
    for (const el of adsEl.children) { io.unobserve(el); if (el.dataset.id) io.observe(el); }
  });

  // ---------------------------------------------------------------- dokunma / fare
  const pointers = new Map();
  let gesture = null;
  let suppressClick = false;
  let spaceDown = false;
  let lastPointer = null;

  stage.addEventListener('contextmenu', e => { if (mode === 'select') e.preventDefault(); });

  stage.addEventListener('pointerdown', e => {
    pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    suppressClick = false;
    if (pointers.size === 2) { startPinch(); return; }
    if (pointers.size > 2) return;
    const panKey = e.button === 1 || e.button === 2 || spaceDown;
    if (mode === 'select' && !panKey && e.button === 0) {
      e.preventDefault();
      startSelect(e);
    } else {
      gesture = { type: 'maybe', id: e.pointerId, x0: e.clientX, y0: e.clientY, tx0: view.tx, ty0: view.ty };
      if (panKey) { e.preventDefault(); beginPan(e); }
    }
  });

  stage.addEventListener('pointermove', e => {
    if (pointers.has(e.pointerId)) pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
    if (mode === 'select' && e.pointerType === 'mouse' && !gesture) showHover(e);
    if (!gesture) return;
    if (gesture.type === 'pinch') { movePinch(); return; }
    if (gesture.id !== e.pointerId) return;
    if (gesture.type === 'maybe') {
      if (Math.hypot(e.clientX - gesture.x0, e.clientY - gesture.y0) < 6) return;
      beginPan(e);
    }
    if (gesture.type === 'pan') {
      view.tx = gesture.tx0 + (e.clientX - gesture.x0);
      view.ty = gesture.ty0 + (e.clientY - gesture.y0);
      apply();
    } else if (gesture.type === 'select') {
      lastPointer = { x: e.clientX, y: e.clientY };
      updateSelect(e.clientX, e.clientY);
    }
  });

  function endPointer(e) {
    pointers.delete(e.pointerId);
    if (!gesture) return;
    if (gesture.type === 'pinch') {
      if (pointers.size === 1) {
        const [id, p] = Array.from(pointers.entries())[0];
        gesture = { type: 'pan', id, x0: p.x, y0: p.y, tx0: view.tx, ty0: view.ty };
      } else if (pointers.size === 0) gesture = null;
      return;
    }
    if (gesture.id !== e.pointerId) return;
    if (gesture.type === 'select') finishSelect();
    stage.classList.remove('panning');
    gesture = null;
  }
  stage.addEventListener('pointerup', endPointer);
  stage.addEventListener('pointercancel', endPointer);
  stage.addEventListener('pointerleave', () => { hoverEl.hidden = true; });

  function beginPan(e) {
    gesture = { type: 'pan', id: e.pointerId, x0: e.clientX, y0: e.clientY, tx0: view.tx, ty0: view.ty };
    try { stage.setPointerCapture(e.pointerId); } catch (_) { /* yok say */ }
    stage.classList.add('panning');
    suppressClick = true;
  }

  function startPinch() {
    if (gesture && gesture.type === 'select') { sel = gesture.prev; renderSel(); }
    const [a, b] = Array.from(pointers.values());
    gesture = {
      type: 'pinch', d0: Math.hypot(a.x - b.x, a.y - b.y) || 1,
      c0: { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 }, s0: view.scale, tx0: view.tx, ty0: view.ty,
    };
    suppressClick = true;
    hoverEl.hidden = true;
  }

  function movePinch() {
    const [a, b] = Array.from(pointers.values());
    if (!b) return;
    const g = gesture;
    const d = Math.hypot(a.x - b.x, a.y - b.y);
    const c = { x: (a.x + b.x) / 2, y: (a.y + b.y) / 2 };
    const s = clamp(g.s0 * d / g.d0, view.fit, Math.max(MAX_SCALE, view.fit));
    const k = s / g.s0;
    view.scale = s;
    view.tx = c.x - (g.c0.x - g.tx0) * k;
    view.ty = c.y - (g.c0.y - g.ty0) * k;
    apply();
  }

  stage.addEventListener('wheel', e => {
    e.preventDefault();
    const unit = e.deltaMode === 1 ? 16 : 1;
    const factor = Math.exp(-e.deltaY * unit * (e.ctrlKey ? 0.01 : 0.0018));
    zoomTo(view.scale * factor, e.clientX, e.clientY);
  }, { passive: false });

  $('#zoom-in').addEventListener('click', () => zoomTo(view.scale * 1.6));
  $('#zoom-out').addEventListener('click', () => zoomTo(view.scale / 1.6));
  $('#zoom-fit').addEventListener('click', fitView);

  document.addEventListener('keydown', e => {
    if (document.querySelector('.modal-back')) return;
    if (e.target.matches && e.target.matches('input, textarea, select')) return;
    if (e.key === '+' || e.key === '=') zoomTo(view.scale * 1.4);
    else if (e.key === '-' || e.key === '_') zoomTo(view.scale / 1.4);
    else if (e.key === '0') fitView();
    else if (e.key === 'Escape' && mode === 'select') exitSelect();
    else if (e.key === ' ' && mode === 'select') { spaceDown = true; stage.style.cursor = 'grab'; e.preventDefault(); }
    else if (e.key.startsWith('Arrow') && e.target === stage) {
      const step = 80;
      if (e.key === 'ArrowLeft') view.tx += step;
      if (e.key === 'ArrowRight') view.tx -= step;
      if (e.key === 'ArrowUp') view.ty += step;
      if (e.key === 'ArrowDown') view.ty -= step;
      apply();
      e.preventDefault();
    }
  });
  document.addEventListener('keyup', e => { if (e.key === ' ') { spaceDown = false; stage.style.cursor = ''; } });

  // reklama tıklama: buton doğrudan siteye gider, görsel reklam kartını açar
  adsEl.addEventListener('click', e => {
    if (suppressClick) { e.preventDefault(); e.stopPropagation(); suppressClick = false; return; }
    if (e.target.closest('.ad-btn')) return;
    const el = e.target.closest('.ad');
    if (el && el.dataset.id) { e.stopPropagation(); openAdCard(adById.get(+el.dataset.id)); }
  });
  adsEl.addEventListener('keydown', e => {
    const el = e.target.closest && e.target.closest('.ad');
    if (el && el.dataset.id && (e.key === 'Enter' || e.key === ' ') && !e.target.closest('.ad-btn')) {
      e.preventDefault();
      openAdCard(adById.get(+el.dataset.id));
    }
  });
  stage.addEventListener('click', e => {
    if (suppressClick) { suppressClick = false; return; }
    if (mode !== 'view' || e.target.closest('.ad')) return;
    const c = cellAt(e.clientX, e.clientY);
    if (!c.inside) return;
    const one = { x: c.cx, y: c.cy, w: 1, h: 1 };
    if (taken.some(t => overlaps(one, t))) return;
    toast('Burası boş bir alan. Satın almak için seçebilirsin.', {
      action: { label: 'Reklam Ver', run: () => { enterSelect(); setSel(one); } },
    });
  });

  // ---------------------------------------------------------------- seçim
  const overlaps = (a, b) => a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  const norm = (ax, ay, bx, by) => ({
    x: Math.min(ax, bx), y: Math.min(ay, by), w: Math.abs(ax - bx) + 1, h: Math.abs(ay - by) + 1,
  });

  function startSelect(e) {
    try { stage.setPointerCapture(e.pointerId); } catch (_) { /* yok say */ }
    hoverEl.hidden = true;
    const c = cellAt(e.clientX, e.clientY);
    const prev = sel ? Object.assign({}, sel) : null;
    const handle = e.target.closest('.hdl');
    lastPointer = { x: e.clientX, y: e.clientY };
    if (handle && sel) {
      const d = handle.dataset.h;
      gesture = {
        type: 'select', id: e.pointerId, mode: 'resize', prev,
        ax: d.includes('w') ? sel.x + sel.w - 1 : sel.x,
        ay: d.includes('n') ? sel.y + sel.h - 1 : sel.y,
      };
    } else if (sel && e.target.closest('.selbox')) {
      gesture = { type: 'select', id: e.pointerId, mode: 'move', prev, ox: c.cx - sel.x, oy: c.cy - sel.y };
    } else {
      gesture = { type: 'select', id: e.pointerId, mode: 'new', prev, ax: c.cx, ay: c.cy };
      setSel({ x: c.cx, y: c.cy, w: 1, h: 1 });
    }
    edgeLoop();
  }

  function updateSelect(clientX, clientY) {
    const g = gesture;
    const c = cellAt(clientX, clientY);
    if (g.mode === 'move') {
      setSel({ x: clamp(c.cx - g.ox, 0, B.cols - sel.w), y: clamp(c.cy - g.oy, 0, B.rows - sel.h), w: sel.w, h: sel.h });
    } else {
      setSel(norm(g.ax, g.ay, c.cx, c.cy));
    }
  }

  // Yakınlaştırılmışken seçim ekran kenarına sürüklenirse pano kendiliğinden kayar.
  function edgeLoop() {
    if (!gesture || gesture.type !== 'select') return;
    const m = 36, sp = 14;
    let dx = 0, dy = 0;
    if (lastPointer) {
      if (lastPointer.x < m) dx = sp; else if (lastPointer.x > vw() - m) dx = -sp;
      if (lastPointer.y < m) dy = sp; else if (lastPointer.y > vh() - m) dy = -sp;
    }
    if (dx || dy) {
      const ox = view.tx, oy = view.ty;
      view.tx += dx; view.ty += dy;
      apply();
      if (view.tx !== ox || view.ty !== oy) updateSelect(lastPointer.x, lastPointer.y);
    }
    requestAnimationFrame(edgeLoop);
  }

  function finishSelect() {
    if (sel && gesture.mode === 'new' && sel.w * sel.h === 1 && gesture.prev && !validate(sel).ok) {
      // yanlışlıkla dolu bir bloğa dokunulduysa önceki seçimi koru
      sel = gesture.prev;
      renderSel();
    }
  }

  function showHover(e) {
    const c = cellAt(e.clientX, e.clientY);
    hoverEl.hidden = !c.inside;
    if (c.inside) placeRect(hoverEl, { x: c.cx, y: c.cy, w: 1, h: 1 }, B);
  }

  function validate(r) {
    for (const t of taken) {
      if (!overlaps(r, t)) continue;
      if (t.state === 'reserved') {
        return { ok: false, msg: t.mine ? 'Bu alan, ödemesi bekleyen kendi siparişinde rezerve. Reklamlarım\'dan ödemeye devam edebilirsin.' : 'Seçim, şu anda ödemesi yapılan (rezerve) bir alana taşıyor.' };
      }
      return { ok: false, msg: 'Seçim, satılmış bir alana taşıyor. Boş (yeşil) bloklardan seç.' };
    }
    const blocks = r.w * r.h;
    if (blocks < pricing.min_blocks) return { ok: false, msg: 'En az ' + pricing.min_blocks + ' blok seçmelisin.' };
    if (pricing.max_blocks && blocks > pricing.max_blocks) {
      return { ok: false, msg: 'Tek seferde en fazla ' + fmtNum(pricing.max_blocks) + ' blok alınabilir.' };
    }
    return { ok: true };
  }

  function setSel(r) { sel = r; renderSel(); }

  function quoteLocal(r) {
    const pixels = r.w * r.h * B.block * B.block;
    return { pixels, amount: pixels * pricing.price_per_pixel };
  }

  function renderSel() {
    const msg = $('#sel-msg'), buy = $('#sel-buy');
    if (!sel) {
      selbox.hidden = true;
      for (const id of ['#s-w', '#s-h', '#s-px']) $(id).textContent = '—';
      $('#s-days').textContent = pricing.duration_days + ' gün';
      $('#s-price').textContent = '—';
      msg.className = 'sel-msg muted';
      msg.textContent = matchMedia('(pointer: coarse)').matches
        ? 'Bir parmakla boş (yeşil) alanı sürükleyerek seç. İki parmakla yakınlaştır ve kaydır.'
        : 'Fareyle boş (yeşil) alanı sürükleyerek seç. Tekerlekle yakınlaştır; Boşluk tuşu veya sağ tıkla sürükleyerek kaydır.';
      buy.disabled = true;
      return;
    }
    const v = validate(sel);
    selbox.hidden = false;
    placeRect(selbox, sel, B);
    selbox.classList.toggle('bad', !v.ok);
    selbox.classList.toggle('tag-below', sel.y < 2);
    seltag.textContent = (sel.w * B.block) + ' × ' + (sel.h * B.block) + ' px';
    const q = quoteLocal(sel);
    $('#s-w').replaceChildren((sel.w * B.block) + ' px', h('small', null, sel.w + ' blok'));
    $('#s-h').replaceChildren((sel.h * B.block) + ' px', h('small', null, sel.h + ' blok'));
    $('#s-px').textContent = fmtNum(q.pixels);
    $('#s-days').textContent = pricing.duration_days + ' gün';
    $('#s-price').textContent = fmtTL(q.amount);
    msg.textContent = v.ok ? 'Köşelerden boyutlandır, ortadan tutup taşı.' : v.msg;
    msg.className = 'sel-msg' + (v.ok ? ' muted' : ' bad');
    buy.disabled = !v.ok;
    positionPanel();
  }

  function positionPanel() {
    if (selpanel.hidden || !sel || !B) return;
    // panel, seçimin karşı tarafında dursun ki seçilen alanı örtmesin
    const centerX = view.tx + (sel.x + sel.w / 2) * B.block * view.scale;
    selpanel.classList.toggle('left', centerX > vw() / 2);
  }

  function enterSelect() {
    if (mode === 'select') return;
    mode = 'select';
    boardEl.classList.add('select-mode');
    overlay.hidden = false;
    selpanel.hidden = false;
    stage.classList.add('selecting');
    advBtn.textContent = 'Vazgeç';
    $('#empty-hint').hidden = true;
    renderSel();
    apply();
    load().catch(() => {});
  }

  function exitSelect() {
    mode = 'view';
    boardEl.classList.remove('select-mode');
    overlay.hidden = true;
    selpanel.hidden = true;
    selbox.hidden = true;
    hoverEl.hidden = true;
    stage.classList.remove('selecting');
    advBtn.textContent = 'Reklam Ver';
    sel = null;
    $('#empty-hint').hidden = !(ads.length === 0 && taken.length === 0);
    apply();
  }

  document.addEventListener('click', e => {
    const b = e.target.closest('[data-action="advertise"]');
    if (!b) return;
    if (mode === 'select' && b === advBtn) exitSelect(); else enterSelect();
  });
  $('#sel-clear').addEventListener('click', () => setSel(null));
  $('#sel-buy').addEventListener('click', () => buy());

  // ---------------------------------------------------------------- satın alma
  async function buy() {
    if (!sel || !validate(sel).ok) return;
    const user = await requireLogin('Alanı satın almak için hesap oluşturun veya giriş yapın. Ödeme onaylanınca alan bu hesaba bağlanır.');
    if (!user) return;
    let q;
    try {
      q = await api('/api/quote', { method: 'POST', body: sel });
    } catch (e) { toast(e.message, { type: 'bad' }); return; }
    if (!q.available) {
      toast('Bu alanın bir kısmı az önce rezerve edildi veya satıldı. Pano güncellendi.', { type: 'bad' });
      await load();
      return;
    }
    checkout(q, user);
  }

  function checkout(q, user) {
    const b = user.billing || {};
    const inp = (name, attrs = {}) => h('input', Object.assign({ name, value: b[name] || '' }, attrs));
    const fName = inp('name', { autocomplete: 'name', required: true, placeholder: 'Ad Soyad', value: b.name || user.name || '' });
    const fPhone = inp('phone', { autocomplete: 'tel', inputmode: 'tel', required: true, placeholder: '05xx xxx xx xx' });
    const fCity = inp('city', { autocomplete: 'address-level1', required: true, placeholder: 'İstanbul' });
    const fAddr = inp('address', { autocomplete: 'street-address', required: true, placeholder: 'Mahalle, sokak, no' });
    const fCompany = inp('company', { autocomplete: 'organization', placeholder: 'İsteğe bağlı' });
    const fTax = inp('tax_id', { inputmode: 'numeric', placeholder: 'İsteğe bağlı', maxlength: '11' });
    const terms = h('input', { type: 'checkbox', required: true });
    const err = h('p', { class: 'form-error', role: 'alert' });
    const payBtn = h('button', { class: 'btn primary', type: 'submit' }, fmtTL(q.amount) + ' öde');
    const endEstimate = Math.floor(Date.now() / 1000) + q.duration_days * 86400;

    const summary = h('dl', { class: 'summary' },
      h('div', null, h('dt', null, 'Boyut'), h('dd', null, q.width_px + ' × ' + q.height_px + ' px (' + q.w + ' × ' + q.h + ' blok)')),
      h('div', null, h('dt', null, 'Konum'), h('dd', null, 'soldan ' + q.x * B.block + ' px, üstten ' + q.y * B.block + ' px')),
      h('div', null, h('dt', null, 'Toplam piksel'), h('dd', null, fmtNum(q.pixels))),
      h('div', null, h('dt', null, 'Piksel fiyatı'), h('dd', null, fmtTL(q.price_per_pixel))),
      h('div', null, h('dt', null, 'Yayın süresi'), h('dd', null, q.duration_days + ' gün (≈ ' + fmtDate(endEstimate) + ')')),
      h('div', { class: 'total' }, h('dt', null, 'Toplam'), h('dd', null, fmtTL(q.amount))));

    const form = h('form', { class: 'form', novalidate: true },
      h('div', { class: 'row2' }, RV.field('Ad Soyad', fName), RV.field('Telefon', fPhone)),
      h('div', { class: 'row2' }, RV.field('Şehir', fCity), RV.field('Firma adı', fCompany)),
      RV.field('Fatura adresi', fAddr),
      RV.field('TC kimlik / vergi no', fTax),
      h('label', { class: 'check' }, terms, h('span', null,
        h('a', { href: '/yasal', target: '_blank' }, 'Ön bilgilendirme formunu ve mesafeli satış sözleşmesini'),
        ' okudum, onaylıyorum.')),
      err, payBtn);

    const m = modal({
      title: 'Ödeme öncesi özet', wide: true,
      body: h('div', null,
        summary,
        h('p', { class: 'note' },
          h('strong', null, 'Sabit ücret: '),
          'gösterim veya tıklama başına ücret yoktur, reklamverene de gösterim/tıklama başına ödeme yapılmaz. ',
          'Ödeme sayfasındayken alan ' + q.reserve_minutes + ' dakika boyunca senin için ayrılır. ',
          payment.live ? 'Ödeme ' + payment.label + ' güvencesiyle alınır.' : 'Şu an test ödemesi açık: gerçek para çekilmez.'),
        form),
    });

    form.addEventListener('submit', async e => {
      e.preventDefault();
      err.textContent = '';
      if (!terms.checked) { err.textContent = 'Devam etmek için sözleşmeyi onaylamalısın.'; return; }
      payBtn.disabled = true;
      payBtn.textContent = 'Alan ayrılıyor…';
      try {
        const res = await api('/api/orders', {
          method: 'POST',
          body: {
            x: q.x, y: q.y, w: q.w, h: q.h, amount: q.amount, accept_terms: true,
            billing: { name: fName.value, phone: fPhone.value, city: fCity.value, address: fAddr.value, company: fCompany.value, tax_id: fTax.value },
          },
        });
        payBtn.textContent = 'Ödeme sayfasına gidiliyor…';
        location.href = res.redirect_url;
      } catch (ex) {
        err.textContent = ex.message;
        payBtn.disabled = false;
        payBtn.textContent = fmtTL(q.amount) + ' öde';
        if (ex.status === 409) { load().catch(() => {}); }
      }
    });
  }

  // ---------------------------------------------------------------- dok
  let idleTimer = null;
  function wake() {
    dock.classList.remove('idle');
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => { if (dock.classList.contains('over') && mode === 'view') dock.classList.add('idle'); }, 3500);
  }
  window.addEventListener('pointermove', e => { if (e.pointerType === 'mouse') wake(); }, { passive: true });

  // ---------------------------------------------------------------- başlat
  (async () => {
    try {
      await load();
    } catch (e) {
      toast('Pano yüklenemedi: ' + e.message, { type: 'bad', ms: 10000 });
      return;
    }
    fitView();
    wake();
    stage.focus({ preventScroll: true });
    RV.loadMe();
    if (RV.params().get('sec') === '1') enterSelect();
    // Seçim modunda rezervasyonlar 20 sn'de bir, normal görünümde dakikada bir yenilenir.
    let tick = 0;
    setInterval(() => {
      tick++;
      if (!document.hidden && (mode === 'select' || tick % 3 === 0)) load().catch(() => {});
    }, 20000);
  })();
})();
