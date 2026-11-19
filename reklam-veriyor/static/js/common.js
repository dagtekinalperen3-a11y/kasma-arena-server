/* Reklam Veriyor — ortak yardımcılar (pano, Reklamlarım, Yönetim) */
'use strict';

const RV = (() => {
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  /** Güvenli eleman oluşturucu: metinler her zaman textContent ile eklenir. */
  function h(tag, attrs, ...children) {
    const el = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v == null || v === false) continue;
        if (k === 'class') el.className = v;
        else if (k === 'style' && typeof v === 'object') Object.assign(el.style, v);
        else if (k === 'dataset') Object.assign(el.dataset, v);
        else if (k.startsWith('on') && typeof v === 'function') el.addEventListener(k.slice(2), v);
        else if (v === true) el.setAttribute(k, '');
        else el.setAttribute(k, v);
      }
    }
    for (const c of children.flat()) {
      if (c == null || c === false) continue;
      el.append(c instanceof Node ? c : document.createTextNode(String(c)));
    }
    return el;
  }

  // ---------- biçimlendirme ----------
  const nf = new Intl.NumberFormat('tr-TR');
  const cf = new Intl.NumberFormat('tr-TR', { style: 'currency', currency: 'TRY', minimumFractionDigits: 2 });
  const fmtNum = n => nf.format(n);
  const fmtTL = kurus => cf.format(kurus / 100);
  const fmtDate = ts => new Date(ts * 1000).toLocaleDateString('tr-TR', { day: 'numeric', month: 'long', year: 'numeric' });
  const fmtDateTime = ts => new Date(ts * 1000).toLocaleString('tr-TR', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' });
  function fmtLeft(sec) {
    if (sec <= 0) return 'süresi doldu';
    const d = Math.floor(sec / 86400);
    if (d >= 1) return d + ' gün';
    const hh = Math.floor(sec / 3600), mm = Math.floor((sec % 3600) / 60), ss = sec % 60;
    if (hh) return hh + ' sa ' + mm + ' dk';
    return mm + ':' + String(ss).padStart(2, '0');
  }

  // ---------- API ----------
  let csrf = null;
  let me = null;
  let meLoaded = null;

  async function api(path, opts = {}) {
    const init = { method: opts.method || 'GET', headers: {}, credentials: 'same-origin' };
    if (init.method !== 'GET') {
      if (!csrf) await loadMe();
      init.headers['X-CSRF-Token'] = csrf;
    }
    if (opts.form) init.body = opts.form;
    else if (opts.body !== undefined) {
      init.headers['Content-Type'] = 'application/json';
      init.body = JSON.stringify(opts.body);
    }
    let res;
    try {
      res = await fetch(path, init);
    } catch (e) {
      throw Object.assign(new Error('Sunucuya ulaşılamadı. İnternet bağlantınızı kontrol edin.'), { status: 0 });
    }
    let data = {};
    try { data = await res.json(); } catch (e) { /* boş gövde */ }
    if (data.csrf) csrf = data.csrf;
    if (!res.ok) {
      const err = new Error(data.error || ('İşlem başarısız (' + res.status + ')'));
      err.status = res.status; err.data = data;
      throw err;
    }
    return data;
  }

  function loadMe(force) {
    if (!meLoaded || force) {
      meLoaded = fetch('/api/me', { credentials: 'same-origin' })
        .then(r => r.json())
        .then(d => { csrf = d.csrf; me = d.user; return me; });
    }
    return meLoaded;
  }

  async function logout() {
    await api('/api/auth/logout', { method: 'POST' });
    me = null;
    meLoaded = Promise.resolve(null);
  }

  // ---------- bildirim ----------
  function toast(msg, opts = {}) {
    let box = $('#toasts');
    if (!box) { box = h('div', { id: 'toasts', class: 'toasts', 'aria-live': 'polite' }); document.body.append(box); }
    const el = h('div', { class: 'toast ' + (opts.type || ''), role: 'status' }, h('span', null, msg));
    if (opts.action) {
      el.append(h('button', { class: 'btn small primary', onclick: () => { el.remove(); opts.action.run(); } }, opts.action.label));
    }
    box.append(el);
    setTimeout(() => el.remove(), opts.ms || (opts.action ? 6500 : 4200));
    return el;
  }

  // ---------- modal ----------
  function modal({ title, body, wide, className, onClose }) {
    const prevFocus = document.activeElement;
    const box = h('div', { class: 'modal ' + (wide ? 'wide ' : '') + (className || ''), role: 'dialog', 'aria-modal': 'true' });
    const closeBtn = h('button', { class: 'iconbtn close', 'aria-label': 'Kapat', type: 'button' }, '×');
    if (title) box.append(h('h2', null, title));
    box.append(closeBtn);
    if (body) box.append(body);
    const back = h('div', { class: 'modal-back' }, box);
    function close() {
      back.remove();
      document.removeEventListener('keydown', onKey);
      if (prevFocus && prevFocus.focus) prevFocus.focus();
      if (onClose) onClose();
    }
    function onKey(e) { if (e.key === 'Escape') close(); }
    closeBtn.addEventListener('click', close);
    back.addEventListener('pointerdown', e => { if (e.target === back) back.dataset.down = '1'; });
    back.addEventListener('click', e => { if (e.target === back && back.dataset.down) close(); delete back.dataset.down; });
    document.addEventListener('keydown', onKey);
    document.body.append(back);
    const first = box.querySelector('input, button:not(.close), a[href]');
    (first || closeBtn).focus();
    return { close, el: box };
  }

  function field(label, input, hint) {
    return h('label', { class: 'field' }, h('span', null, label), input, hint ? h('small', null, hint) : null);
  }

  // ---------- giriş / kayıt ----------
  function authFlow(reason) {
    return new Promise(resolve => {
      let mode = 'register';
      const err = h('p', { class: 'form-error', role: 'alert' });
      const name = h('input', { name: 'name', autocomplete: 'name', placeholder: 'Ad Soyad' });
      const email = h('input', { name: 'email', type: 'email', autocomplete: 'email', required: true, placeholder: 'ornek@eposta.com' });
      const pass = h('input', { name: 'password', type: 'password', autocomplete: 'new-password', required: true, minlength: '8', placeholder: 'En az 8 karakter' });
      const nameField = field('Ad Soyad', name);
      const submit = h('button', { class: 'btn primary', type: 'submit' }, 'Hesap oluştur');
      const tReg = h('button', { type: 'button', class: 'on' }, 'Yeni hesap');
      const tLog = h('button', { type: 'button' }, 'Giriş yap');
      function setMode(m) {
        mode = m;
        tReg.classList.toggle('on', m === 'register');
        tLog.classList.toggle('on', m === 'login');
        nameField.hidden = m === 'login';
        pass.autocomplete = m === 'login' ? 'current-password' : 'new-password';
        submit.textContent = m === 'login' ? 'Giriş yap' : 'Hesap oluştur';
        err.textContent = '';
      }
      tReg.onclick = () => setMode('register');
      tLog.onclick = () => setMode('login');
      const form = h('form', { class: 'form', novalidate: true },
        nameField, field('E-posta', email), field('Şifre', pass), err, submit);
      let done = false;
      const m = modal({
        title: 'Reklamlarım hesabı',
        body: h('div', null,
          h('p', { class: 'muted small' }, reason || 'Satın aldığınız alan bu hesaba bağlanır. Görselinizi ve bağlantınızı buradan yönetirsiniz.'),
          h('div', { class: 'tabs' }, tReg, tLog), form),
        onClose: () => { if (!done) resolve(null); },
      });
      form.addEventListener('submit', async e => {
        e.preventDefault();
        err.textContent = '';
        submit.disabled = true;
        try {
          const d = await api(mode === 'login' ? '/api/auth/login' : '/api/auth/register', {
            method: 'POST', body: { email: email.value, password: pass.value, name: name.value },
          });
          me = d.user;
          meLoaded = Promise.resolve(me);
          done = true;
          m.close();
          resolve(me);
        } catch (ex) {
          err.textContent = ex.message;
          if (ex.status === 409) setTimeout(() => setMode('login'), 600);
        } finally {
          submit.disabled = false;
        }
      });
      setTimeout(() => email.focus(), 30);
    });
  }

  async function requireLogin(reason) {
    const u = await loadMe();
    return u || authFlow(reason);
  }

  // ---------- reklam çizimi ----------
  function placeRect(el, r, board) {
    el.style.left = (r.x / board.cols * 100) + '%';
    el.style.top = (r.y / board.rows * 100) + '%';
    el.style.width = (r.w / board.cols * 100) + '%';
    el.style.height = (r.h / board.rows * 100) + '%';
  }

  /** Panoda ve önizlemede aynı görünüm için tek reklam çizici. */
  function buildAd(ad, opts = {}) {
    const el = h('div', {
      class: 'ad', dataset: { id: ad.id }, tabindex: opts.preview ? null : '0', role: opts.preview ? null : 'button',
      'aria-label': opts.preview ? null : ((ad.title || 'Reklam') + ' — reklam kartını aç'),
    });
    if (opts.board) placeRect(el, ad, opts.board);
    el.style.background = ad.bg || '#111318';
    if (ad.image_url) {
      const img = h('img', { class: 'ad-img', src: ad.image_url, alt: ad.title || 'Reklam', draggable: 'false', decoding: 'async' });
      img.style.objectFit = ad.fit === 'contain' ? 'contain' : 'cover';
      el.append(img);
    }
    if (ad.button_text && ad.button_pos !== 'none') {
      const b = h(opts.preview ? 'span' : 'a', { class: 'ad-btn pos-' + (ad.button_pos || 'br') }, ad.button_text);
      if (!opts.preview) { b.href = ad.href; b.target = '_blank'; b.rel = 'sponsored noopener'; }
      b.style.background = ad.button_bg || '#ffc83d';
      b.style.color = ad.button_fg || '#14161b';
      el.append(b);
    }
    return el;
  }

  /** Küçük bloklarda butonun okunabildiği reklam kartı. */
  function openAdCard(ad, opts = {}) {
    const media = h('div', { class: 'adcard-media' });
    media.style.background = ad.bg || '#111318';
    media.style.aspectRatio = ad.w + ' / ' + ad.h;
    if (ad.image_url) {
      const img = h('img', { src: ad.image_url, alt: ad.title || 'Reklam' });
      img.style.objectFit = ad.fit === 'contain' ? 'contain' : 'cover';
      media.append(img);
    }
    const ctaText = (ad.button_text || 'Siteye Git') + ' ↗';
    const cta = opts.preview
      ? h('span', { class: 'btn cta' }, ctaText)
      : h('a', { class: 'btn cta', href: ad.href, target: '_blank', rel: 'sponsored noopener' }, ctaText);
    cta.style.background = ad.button_bg || '#ffc83d';
    cta.style.color = ad.button_fg || '#14161b';
    const body = h('div', { class: 'adcard' },
      h('span', { class: 'chip' }, 'Reklam'),
      media,
      ad.title ? h('h3', null, ad.title) : null,
      ad.description ? h('p', null, ad.description) : null,
      ad.display_url ? h('div', { class: 'dest' }, 'Gideceğiniz adres: ', h('b', null, ad.display_url)) : null,
      cta);
    const m = modal({ body, className: '' });
    if (!opts.preview) cta.addEventListener('click', () => setTimeout(m.close, 100));
    return m;
  }

  function miniBoard(board, rects, highlight) {
    const mb = h('div', { class: 'mini-board' });
    for (const r of rects) {
      const c = h('div', { class: 'mb-cell' });
      placeRect(c, r, board);
      mb.append(c);
    }
    if (highlight) {
      const c = h('div', { class: 'mb-cell me' });
      placeRect(c, highlight, board);
      mb.append(c);
    }
    return mb;
  }

  function params() { return new URLSearchParams(location.search); }

  return {
    $, $$, h, api, loadMe, logout, me: () => me, toast, modal, field, authFlow, requireLogin,
    fmtNum, fmtTL, fmtDate, fmtDateTime, fmtLeft, buildAd, openAdCard, placeRect, miniBoard, params,
  };
})();
