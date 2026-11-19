/* Reklam Veriyor — Reklamlarım: alanlar, düzenleyici, önizleme, istatistik */
'use strict';

(() => {
  const { $, h, api, toast, modal, field, fmtTL, fmtNum, fmtDate, fmtDateTime, fmtLeft, buildAd, openAdCard, placeRect, miniBoard } = RV;

  let B = null;            // pano ölçüleri
  let boardAds = [];       // panodaki diğer reklamlar (önizleme için)
  let my = null;           // /api/my yanıtı
  let current = null;      // düzenlenen alan
  let draft = null;        // düzenleyicideki içerik
  let skew = 0;            // sunucu saati farkı

  const PRESETS = ['Siteye Git', 'Ürünü İncele', 'Hemen Al', 'Kayıt Ol', 'Randevu Al', 'Menüyü Gör'];
  const POS = ['tl', 'tc', 'tr', 'ml', 'mc', 'mr', 'bl', 'bc', 'br'];
  const POS_LABEL = { tl: 'sol üst', tc: 'üst orta', tr: 'sağ üst', ml: 'sol orta', mc: 'orta', mr: 'sağ orta', bl: 'sol alt', bc: 'alt orta', br: 'sağ alt' };
  const now = () => Math.floor(Date.now() / 1000) + skew;

  // ---------------------------------------------------------------- yükleme
  async function init() {
    const user = await RV.loadMe();
    if (!user) {
      $('#guest').hidden = false;
      $('#login-btn').onclick = async () => { if (await RV.authFlow()) location.reload(); };
      return;
    }
    $('#whoami').textContent = user.email + ' hesabına bağlı alanlar, görsellerin ve istatistiklerin.';
    $('#logout').hidden = false;
    $('#logout').onclick = async () => { await RV.logout(); location.href = '/'; };
    if (user.is_admin) $('#nav-admin').hidden = false;
    await refresh();
    handleReturn();
    setInterval(tickCountdowns, 1000);
  }

  async function refresh(keepEditor) {
    const [b, m] = await Promise.all([api('/api/board'), api('/api/my')]);
    B = b.board;
    boardAds = b.ads;
    my = m;
    skew = m.server_time - Math.floor(Date.now() / 1000);
    renderPending();
    renderSlots();
    renderHistory();
    if (keepEditor && current) {
      const s = my.slots.find(x => x.id === current.id);
      if (s) { current = s; renderEditor(); }
    }
  }

  // ---------------------------------------------------------------- ödeme dönüşü
  async function handleReturn() {
    const p = RV.params();
    const ref = p.get('siparis');
    if (!ref && p.get('odeme') !== 'bulunamadi') return;
    history.replaceState(null, '', '/reklamlarim');
    const banner = $('#banner');
    if (!ref) {
      banner.replaceChildren(h('p', { class: 'alert bad' }, 'Ödeme dönüşünde sipariş bulunamadı. Ödeme alındıysa birkaç dakika içinde burada görünür.'));
      return;
    }
    let o = my.orders.find(x => x.ref === ref);
    if (o && o.status === 'pending') {
      try { o = (await api('/api/orders/' + ref + '/check', { method: 'POST' })).order; await refresh(); } catch (e) { /* yok say */ }
    }
    if (!o) return;
    if (o.status === 'paid') {
      const slotId = o.slot_id;
      banner.replaceChildren(h('p', { class: 'alert ok' },
        o.kind === 'renew' ? 'Ödeme onaylandı, yayın süren ' + o.duration_days + ' gün uzatıldı.' :
          'Ödeme onaylandı! ' + o.width_px + '×' + o.height_px + ' px alan hesabına bağlandı. Şimdi görselini yükleyip butonunu ekle.'));
      const s = my.slots.find(x => x.id === slotId);
      if (s && o.kind !== 'renew') openEditor(s);
    } else if (o.status === 'pending') {
      banner.replaceChildren(h('p', { class: 'alert info' }, 'Ödemen henüz onaylanmadı. Ödeme sağlayıcısı onay verdiğinde alan otomatik olarak hesabına bağlanır.'));
    } else if (o.status === 'refunded' || o.status === 'refund_needed') {
      banner.replaceChildren(h('p', { class: 'alert bad' }, 'Ödeme geldiğinde seçtiğin alan artık boş değildi. ' +
        (o.status === 'refunded' ? 'Ödemen iade edildi.' : 'İade işlemi site yöneticisi tarafından yapılacak.')));
    } else {
      banner.replaceChildren(h('p', { class: 'alert bad' }, 'Ödeme tamamlanmadı, alan serbest bırakıldı. Dilersen panodan yeniden seçebilirsin.'));
    }
  }

  // ---------------------------------------------------------------- bekleyen siparişler
  function renderPending() {
    const list = my.orders.filter(o => o.status === 'pending' && o.expires_at > now());
    $('#pending').hidden = !list.length;
    $('#pending-list').replaceChildren(...list.map(o => {
      const thumb = h('div', { class: 'slot-thumb' }, miniBoard(B, [], o));
      return h('div', { class: 'slot-item' },
        thumb,
        h('div', null,
          h('h3', null, (o.kind === 'renew' ? 'Süre uzatma · ' : 'Rezerve alan · ') + o.width_px + '×' + o.height_px + ' px'),
          h('div', { class: 'slot-meta' },
            h('span', null, 'Tutar ', h('b', null, fmtTL(o.amount))),
            h('span', null, 'Kalan süre ', h('b', { 'data-expires': o.expires_at }, fmtLeft(o.expires_at - now()))),
            h('span', { class: 'chip warn' }, 'Ödeme bekleniyor'))),
        h('div', { class: 'slot-actions' },
          h('button', { class: 'btn small primary', onclick: () => resume(o) }, 'Ödemeye devam et'),
          o.provider !== 'test' ? h('button', { class: 'btn small', onclick: () => check(o) }, 'Ödemeyi kontrol et') : null,
          h('button', { class: 'btn small danger', onclick: () => cancel(o) }, 'İptal et')));
    }));
  }

  function tickCountdowns() {
    let expired = false;
    for (const el of document.querySelectorAll('[data-expires]')) {
      const left = +el.dataset.expires - now();
      el.textContent = fmtLeft(left);
      if (left <= 0) expired = true;
    }
    if (expired) refresh(true).catch(() => {});
  }

  async function resume(o) {
    try { location.href = (await api('/api/orders/' + o.ref + '/resume', { method: 'POST' })).redirect_url; }
    catch (e) { toast(e.message, { type: 'bad' }); refresh(true); }
  }
  async function check(o) {
    try {
      const r = await api('/api/orders/' + o.ref + '/check', { method: 'POST' });
      toast(r.order.status === 'paid' ? 'Ödeme onaylandı.' : 'Ödeme henüz onaylanmadı.', { type: r.order.status === 'paid' ? 'ok' : '' });
      refresh(true);
    } catch (e) { toast(e.message, { type: 'bad' }); }
  }
  async function cancel(o) {
    if (!confirm('Bu rezervasyonu iptal edip alanı serbest bırakmak istiyor musun?')) return;
    try { await api('/api/orders/' + o.ref + '/cancel', { method: 'POST' }); toast('Rezervasyon iptal edildi.'); refresh(true); }
    catch (e) { toast(e.message, { type: 'bad' }); }
  }

  // ---------------------------------------------------------------- alanlar
  function slotState(s) {
    if (s.status === 'expired') return ['bad', 'Süresi doldu'];
    if (s.status === 'suspended') return ['bad', 'Yönetici askıya aldı'];
    if (s.review === 'pending') return ['warn', 'Onay bekliyor'];
    if (s.review === 'rejected') return ['bad', 'Reddedildi'];
    if (!s.content || !s.content.image) return ['warn', 'Görsel bekleniyor'];
    return ['ok', 'Yayında'];
  }

  function renderSlots() {
    $('#slots-wrap').hidden = !my.slots.length;
    $('#none').hidden = !!my.slots.length || my.orders.some(o => o.status === 'pending' && o.expires_at > now());
    const others = boardAds.map(a => ({ x: a.x, y: a.y, w: a.w, h: a.h }));
    $('#slot-list').replaceChildren(...my.slots.map(s => {
      const [tone, label] = slotState(s);
      const c = s.content || {};
      const ctr = s.impressions ? (s.clicks / s.impressions * 100).toLocaleString('tr-TR', { maximumFractionDigits: 1 }) + '%' : '—';
      return h('div', { class: 'slot-item' + (current && current.id === s.id ? ' on' : '') },
        h('div', { class: 'slot-thumb', title: 'Panodaki konumu' }, miniBoard(B, others, s)),
        h('div', null,
          h('h3', null, c.title || ('Alan #' + s.id), ' ', h('span', { class: 'chip ' + tone }, label)),
          h('div', { class: 'slot-meta' },
            h('span', null, h('b', null, s.width_px + '×' + s.height_px + ' px'), ' · ' + fmtNum(s.pixels) + ' piksel'),
            h('span', null, s.status === 'expired' ? 'Bitti: ' : 'Bitiş: ', h('b', null, fmtDate(s.ends_at)),
              s.status !== 'expired' ? ' (' + fmtLeft(s.ends_at - now()) + ')' : ''),
            h('span', null, 'Gösterim ', h('b', null, fmtNum(s.impressions))),
            h('span', null, 'Tıklama ', h('b', null, fmtNum(s.clicks))),
            h('span', null, 'Oran ', h('b', null, ctr))),
          s.review === 'rejected' && s.review_note ? h('p', { class: 'small', style: { color: '#ffb3bb', margin: '6px 0 0' } }, 'Ret nedeni: ' + s.review_note) : null,
          s.status === 'suspended' && s.admin_note ? h('p', { class: 'small', style: { color: '#ffb3bb', margin: '6px 0 0' } }, 'Not: ' + s.admin_note) : null),
        h('div', { class: 'slot-actions' },
          s.status !== 'expired' ? h('button', { class: 'btn small primary', onclick: () => openEditor(s) }, c.image ? 'Düzenle' : 'Reklamı hazırla') : null,
          h('button', { class: 'btn small', onclick: () => openEditor(s, 'stats') }, 'İstatistik'),
          s.can_renew ? h('button', { class: 'btn small ghost', onclick: () => renew(s) }, 'Süreyi uzat') : null));
    }));
  }

  // ---------------------------------------------------------------- düzenleyici
  function defaults() {
    return { image: '', image_url: '', fit: 'cover', bg: '#111318', title: '', description: '', button_text: 'Siteye Git',
             button_pos: 'br', button_bg: '#ffc83d', button_fg: '#14161b', url: '' };
  }

  let tab = 'edit';
  function openEditor(s, which) {
    current = s;
    tab = which || 'edit';
    draft = Object.assign(defaults(), s.draft || s.content || {});
    renderSlots();
    renderEditor();
    $('#editor-wrap').scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  function renderEditor() {
    const wrap = $('#editor-wrap');
    wrap.hidden = false;
    const s = current;
    const tabs = h('div', { class: 'admin-tabs', role: 'tablist' },
      h('button', { class: tab === 'edit' ? 'on' : '', onclick: () => { tab = 'edit'; renderEditor(); } }, 'Reklamı düzenle'),
      h('button', { class: tab === 'stats' ? 'on' : '', onclick: () => { tab = 'stats'; renderEditor(); } }, 'İstatistikler'));
    const head = h('div', { class: 'page-head', style: { marginTop: '28px' } },
      h('div', null, h('h1', { style: { fontSize: '21px' } }, 'Alan #' + s.id + ' · ' + s.width_px + '×' + s.height_px + ' px'),
        h('p', null, 'Panoda soldan ' + s.x * B.block + ' px, üstten ' + s.y * B.block + ' px. Yayın bitişi ' + fmtDate(s.ends_at) + '.')),
      h('button', { class: 'btn ghost small', onclick: () => { wrap.hidden = true; current = null; renderSlots(); } }, 'Kapat'));
    wrap.replaceChildren(head, tabs, tab === 'stats' ? statsView(s) : editView(s));
  }

  function editView(s) {
    const expired = s.status === 'expired';
    // --- görsel
    const fileInput = h('input', { type: 'file', accept: 'image/png,image/jpeg,image/webp,image/gif', hidden: true });
    const dropInner = h('div');
    const drop = h('div', { class: 'drop', tabindex: '0', role: 'button', 'aria-label': 'Görsel yükle' }, dropInner, fileInput);
    function paintDrop(busy) {
      dropInner.replaceChildren(
        draft.image_url ? h('img', { src: draft.image_url, alt: '' }) : null,
        h('strong', null, busy ? 'Yükleniyor…' : (draft.image_url ? 'Görseli değiştir' : 'Görsel yükle')),
        h('div', { class: 'small muted' }, 'PNG, JPG, WEBP veya GIF · en fazla 5 MB'),
        h('div', { class: 'small muted' }, 'Önerilen ölçü: ' + s.width_px * 2 + '×' + s.height_px * 2 + ' px (alanın 2 katı, keskin görünür)'));
    }
    paintDrop();
    drop.onclick = () => fileInput.click();
    drop.onkeydown = e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); } };
    drop.ondragover = e => { e.preventDefault(); drop.classList.add('over'); };
    drop.ondragleave = () => drop.classList.remove('over');
    drop.ondrop = e => { e.preventDefault(); drop.classList.remove('over'); if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]); };
    fileInput.onchange = () => { if (fileInput.files[0]) upload(fileInput.files[0]); fileInput.value = ''; };
    const ratioNote = h('p', { class: 'small muted', style: { margin: '6px 0 0' } });
    async function upload(file) {
      if (file.size > 5 * 1024 * 1024) { toast('Dosya çok büyük (en fazla 5 MB).', { type: 'bad' }); return; }
      paintDrop(true);
      const fd = new FormData();
      fd.append('file', file);
      try {
        const r = await api('/api/upload', { method: 'POST', form: fd });
        draft.image = r.image;
        draft.image_url = r.image_url;
        const want = s.width_px / s.height_px, got = r.width / r.height;
        ratioNote.textContent = Math.abs(got / want - 1) > 0.08
          ? 'Görselin oranı (' + r.width + '×' + r.height + ') alanınkinden farklı. "Doldur" kenarları kırpar, "Sığdır" boşlukları arka plan rengiyle doldurur.'
          : 'Görsel ' + r.width + '×' + r.height + ' px, alanın oranına uygun.';
        update();
      } catch (e) { toast(e.message, { type: 'bad' }); }
      paintDrop();
    }

    // --- yerleşim
    const fitSeg = h('div', { class: 'seg', role: 'group', 'aria-label': 'Görsel yerleşimi' },
      ...[['cover', 'Doldur (kırp)'], ['contain', 'Sığdır']].map(([v, l]) =>
        h('button', { type: 'button', class: draft.fit === v ? 'on' : '', onclick: e => { draft.fit = v; for (const b of fitSeg.children) b.classList.toggle('on', b === e.currentTarget); update(); } }, l)));
    const bgInput = h('input', { type: 'color', value: hex6(draft.bg), oninput: e => { draft.bg = e.target.value; update(); } });

    // --- metinler
    const title = h('input', { maxlength: '60', value: draft.title, placeholder: 'Ör. Bahçeden Reçel', oninput: e => { draft.title = e.target.value; update(); } });
    const desc = h('input', { maxlength: '160', value: draft.description, placeholder: 'Ör. Katkısız, şekeri az', oninput: e => { draft.description = e.target.value; update(); } });

    // --- buton
    const btnText = h('input', { maxlength: '24', value: draft.button_text, placeholder: 'Siteye Git', oninput: e => { draft.button_text = e.target.value; update(); } });
    const presets = h('div', { class: 'presets' }, ...PRESETS.map(p => h('button', { type: 'button', onclick: () => { btnText.value = p; draft.button_text = p; update(); } }, p)));
    const noBtn = h('input', { type: 'checkbox', checked: draft.button_pos === 'none' });
    let lastPos = draft.button_pos === 'none' ? 'br' : draft.button_pos;
    const posGrid = h('div', { class: 'posgrid', role: 'group', 'aria-label': 'Buton konumu' },
      ...POS.map(p => h('button', { type: 'button', title: POS_LABEL[p], 'aria-label': POS_LABEL[p], class: draft.button_pos === p ? 'on' : '',
        onclick: e => { lastPos = p; draft.button_pos = p; noBtn.checked = false; for (const b of posGrid.children) b.classList.toggle('on', b === e.currentTarget); update(); } })));
    noBtn.onchange = () => {
      draft.button_pos = noBtn.checked ? 'none' : lastPos;
      for (const b of posGrid.children) b.classList.toggle('on', !noBtn.checked && b.title === POS_LABEL[lastPos]);
      update();
    };
    const bbg = h('input', { type: 'color', value: hex6(draft.button_bg), oninput: e => { draft.button_bg = e.target.value; update(); } });
    const bfg = h('input', { type: 'color', value: hex6(draft.button_fg), oninput: e => { draft.button_fg = e.target.value; update(); } });

    // --- bağlantı
    const url = h('input', { type: 'url', inputmode: 'url', value: draft.url, placeholder: 'https://siteniz.com/urun', oninput: e => { draft.url = e.target.value; update(); } });

    const err = h('p', { class: 'form-error', role: 'alert' });
    const publishBtn = h('button', { class: 'btn primary', type: 'button', disabled: expired }, my.pricing.moderation ? 'Onaya gönder' : 'Yayınla');
    const resetBtn = h('button', { class: 'btn ghost', type: 'button', onclick: () => { draft = Object.assign(defaults(), s.content || {}); renderEditor(); } }, 'Değişiklikleri geri al');
    publishBtn.onclick = () => publish(publishBtn, err);
    const status = h('p', { class: 'small muted', style: { margin: 0 } },
      s.review === 'pending' ? 'Son gönderdiğin içerik yönetici onayı bekliyor.' :
        s.published_at ? 'Son yayın: ' + fmtDateTime(s.published_at) : 'Bu alan henüz yayında değil; panoda “Satıldı” olarak görünüyor.');

    const form = h('div', { class: 'card form' },
      h('h2', null, '1. Görsel'), drop, ratioNote,
      h('div', { class: 'pos-row' }, h('div', { class: 'field' }, h('span', null, 'Yerleşim'), fitSeg),
        h('div', { class: 'colors' }, h('label', null, bgInput, 'Arka plan'))),
      h('h2', { style: { marginTop: '8px' } }, '2. Metin'),
      field('Başlık', title, 'Reklam kartında başlık ve görselin alternatif metni olur.'),
      field('Kısa açıklama', desc, 'Reklam kartında görünür (isteğe bağlı).'),
      h('h2', { style: { marginTop: '8px' } }, '3. Buton'),
      field('Buton yazısı', btnText), presets,
      h('div', { class: 'pos-row' },
        h('div', { class: 'field' }, h('span', null, 'Konum'), posGrid),
        h('div', { class: 'colors' }, h('label', null, bbg, 'Buton'), h('label', null, bfg, 'Yazı')),
        h('label', { class: 'check' }, noBtn, h('span', null, 'Görselde buton gösterme'))),
      h('h2', { style: { marginTop: '8px' } }, '4. Hedef bağlantı'),
      field('Buton bu adrese gidecek', url),
      err,
      h('div', { class: 'editor-actions' }, publishBtn, resetBtn), status);

    // --- önizleme
    const boardPrev = h('div', { class: 'preview-board' });
    const closeWrap = h('div', { class: 'preview-close' });
    const closeNote = h('p', { class: 'small muted', style: { margin: '8px 0 0' } });
    let scaleMode = 'desk';
    const SCALES = { desk: ['Masaüstü', 1.2], phone: ['Telefon', 390 / 1200], zoom: ['Yakın', 0] };
    const scaleSeg = h('div', { class: 'seg' }, ...Object.entries(SCALES).map(([k, [l]]) =>
      h('button', { type: 'button', class: k === scaleMode ? 'on' : '', onclick: e => { scaleMode = k; for (const b of scaleSeg.children) b.classList.toggle('on', b === e.currentTarget); update(); } }, l)));
    const linkBox = h('div', { class: 'linkcheck' });
    const cardBtn = h('button', { class: 'btn small', type: 'button', onclick: () => openAdCard(previewAd(), { preview: true }) }, 'Reklam kartını önizle');

    const preview = h('div', { class: 'preview-wrap' },
      h('div', { class: 'card' },
        h('div', { class: 'preview-label' }, h('span', null, 'Panoda nasıl duracak'), h('span', null, 'sarı çerçeve: senin alanın')),
        boardPrev),
      h('div', { class: 'card' },
        h('div', { class: 'preview-label' }, h('span', null, 'Yakın görünüm'), scaleSeg),
        closeWrap, closeNote, h('div', { style: { marginTop: '10px' } }, cardBtn)),
      h('div', { class: 'card' }, h('div', { class: 'preview-label' }, h('span', null, 'Buton nereye gidecek')), linkBox));

    function previewAd() {
      return Object.assign({ id: 'onizleme', x: s.x, y: s.y, w: s.w, h: s.h, href: '#', display_url: displayUrl(draft.url) }, draft);
    }

    function update() {
      const ad = previewAd();
      // panoda
      const board = h('div', { class: 'board' });
      board.style.setProperty('--cols', B.cols);
      board.style.setProperty('--rows', B.rows);
      for (const o of boardAds) if (o.id !== s.id) board.append(buildAd(o, { board: B, preview: true }));
      const mine = draft.image_url ? buildAd(ad, { board: B, preview: true }) : h('div', { class: 'ad placeholder' }, 'Satıldı');
      if (!draft.image_url) placeRect(mine, s, B);
      mine.classList.add('me');
      board.append(mine);
      boardPrev.replaceChildren(board);
      // yakın görünüm
      const maxW = Math.max(160, closeWrap.clientWidth - 32 || 420), maxH = 300;
      let k = SCALES[scaleMode][1];
      if (scaleMode === 'zoom') k = Math.min(4, maxW / s.width_px, maxH / s.height_px);
      const fitK = Math.min(k, maxW / s.width_px);
      const w = s.width_px * fitK, hh = s.height_px * fitK;
      const el = draft.image_url ? buildAd(ad, { preview: true }) : h('div', { class: 'ad placeholder' }, 'Görsel yükle');
      el.style.width = w + 'px';
      el.style.height = hh + 'px';
      closeWrap.replaceChildren(el);
      const btnHidden = draft.button_pos === 'none' || w < 105 || hh < 51;
      closeNote.textContent = (fitK < k ? 'Sığması için küçültüldü. ' : '') +
        (draft.button_pos === 'none' ? 'Görselde buton yok; ziyaretçi görsele dokununca reklam kartı açılır.'
          : btnHidden ? 'Bu boyutta buton okunamayacağı için gizlenir; ziyaretçi görsele dokununca butonlu reklam kartı açılır.'
            : 'Buton görselin üzerinde görünür. Görselin kendisine dokununca da reklam kartı açılır.');
      // bağlantı
      let parsed = null;
      try { parsed = draft.url ? new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(draft.url) ? draft.url : 'https://' + draft.url) : null; } catch (e) { parsed = null; }
      if (!draft.url) linkBox.replaceChildren(h('span', { class: 'muted' }, 'Henüz bağlantı yazmadın.'));
      else if (!parsed || !/^https?:$/.test(parsed.protocol) || !parsed.hostname.includes('.')) linkBox.replaceChildren(h('span', { style: { color: '#ffb3bb' } }, 'Bu adres geçerli görünmüyor. Örnek: https://siteniz.com'));
      else {
        linkBox.replaceChildren(
          h('div', null, '“' + (draft.button_text || 'Siteye Git') + '” → ', h('span', null, parsed.protocol + '//'), h('span', { class: 'host' }, parsed.hostname), h('span', null, parsed.pathname + parsed.search)),
          h('div', { style: { marginTop: '8px' } }, h('a', { href: parsed.href, target: '_blank', rel: 'noopener noreferrer', class: 'btn small' }, 'Bağlantıyı yeni sekmede dene ↗')));
      }
      err.textContent = '';
    }

    requestAnimationFrame(update);
    window.addEventListener('resize', update, { once: true });
    return h('div', { class: 'editor' }, form, preview);
  }

  function displayUrl(u) {
    if (!u) return '';
    try {
      const p = new URL(/^[a-z][a-z0-9+.-]*:\/\//i.test(u) ? u : 'https://' + u);
      return p.hostname.replace(/^www\./, '') + (p.pathname === '/' ? '' : p.pathname);
    } catch (e) { return u; }
  }

  function hex6(c) {
    if (/^#[0-9a-f]{3}$/i.test(c)) return '#' + c.slice(1).split('').map(x => x + x).join('');
    return /^#[0-9a-f]{6}$/i.test(c) ? c : '#111318';
  }

  async function publish(btn, err) {
    err.textContent = '';
    if (!draft.image) { err.textContent = 'Yayınlamak için önce bir görsel yükle.'; return; }
    if (!draft.url) { err.textContent = 'Butonun gideceği bağlantıyı yaz.'; return; }
    btn.disabled = true;
    try {
      const body = Object.assign({}, draft);
      delete body.image_url;
      const r = await api('/api/slots/' + current.id + '/publish', { method: 'POST', body });
      toast(r.moderation ? 'Gönderildi. Yönetici onayından sonra panoda görünecek.' : 'Yayınlandı! Reklamın panoda.', { type: 'ok',
        action: r.moderation ? null : { label: 'Panoda gör', run: () => { location.href = '/'; } } });
      current = r.slot;
      await refresh(true);
    } catch (e) {
      err.textContent = e.message;
    } finally {
      btn.disabled = false;
    }
  }

  // ---------------------------------------------------------------- istatistik
  function statsView(s) {
    const box = h('div', { class: 'card' }, h('p', { class: 'muted' }, 'Yükleniyor…'));
    api('/api/slots/' + s.id + '/stats').then(st => {
      const ctr = st.impressions ? (st.clicks / st.impressions * 100).toLocaleString('tr-TR', { maximumFractionDigits: 2 }) + '%' : '—';
      const table = statsTable(st.series);
      table.hidden = true;
      const toggle = h('button', { class: 'btn small ghost', type: 'button', onclick: () => { table.hidden = !table.hidden; toggle.textContent = table.hidden ? 'Tablo olarak göster' : 'Tabloyu gizle'; } }, 'Tablo olarak göster');
      box.replaceChildren(
        h('dl', { class: 'stats-row' },
          h('div', { class: 'stat' }, h('dt', null, 'Toplam gösterim'), h('dd', null, fmtNum(st.impressions))),
          h('div', { class: 'stat' }, h('dt', null, 'Toplam tıklama'), h('dd', null, fmtNum(st.clicks))),
          h('div', { class: 'stat' }, h('dt', null, 'Tıklama oranı'), h('dd', null, ctr))),
        h('p', { class: 'note' }, h('strong', null, 'Bilgi: '),
          'Gösterim, reklamın en az yarısı bir ziyaretçinin ekranında göründüğünde sayılır (aynı kişi 30 dakikada bir kez). ',
          'Tıklama, butona veya reklam kartındaki butona basıldığında sayılır. Sabit ücret ödediğin için gösterim ya da tıklama başına ücret yoktur.'),
        h('h3', null, 'Günlük gösterim'),
        barChart(st.series, 'impressions', 'bar-i', 'gösterim'),
        h('h3', { style: { marginTop: '16px' } }, 'Günlük tıklama'),
        barChart(st.series, 'clicks', 'bar-c', 'tıklama'),
        h('div', { style: { marginTop: '10px' } }, toggle), table);
    }).catch(e => box.replaceChildren(h('p', { class: 'alert bad' }, e.message)));
    return box;
  }

  function niceMax(v) {
    if (v <= 4) return 4;
    const p = Math.pow(10, Math.floor(Math.log10(v)));
    for (const m of [1, 2, 2.5, 5, 10]) if (m * p >= v) return m * p;
    return 10 * p;
  }

  /** Tek ölçekli sütun grafiği: her ölçüt kendi grafiğinde (iki eksenli grafik yok). */
  function barChart(series, key, cls, unit) {
    const wrap = document.querySelector('#editor-wrap');
    const W = Math.round(Math.max(300, Math.min(1100, (wrap && wrap.clientWidth ? wrap.clientWidth : 680) - 40)));
    const H = 170, L = 34, R = 6, T = 8, Bm = 22;
    const max = niceMax(Math.max(0, ...series.map(d => d[key])));
    const n = series.length;
    const slot = (W - L - R) / n;
    const bw = Math.max(2, Math.min(22, slot - 2));
    const y = v => T + (H - T - Bm) * (1 - v / max);
    const NS = 'http://www.w3.org/2000/svg';
    const el = (tag, attrs, text) => { const e = document.createElementNS(NS, tag); for (const k in attrs) e.setAttribute(k, attrs[k]); if (text != null) e.textContent = text; return e; };
    const svg = el('svg', { class: 'chart', viewBox: '0 0 ' + W + ' ' + H, role: 'img', 'aria-label': 'Günlük ' + unit + ' grafiği' });
    for (const v of [0, max / 2, max]) {
      svg.append(el('line', { class: 'grid', x1: L, x2: W - R, y1: y(v), y2: y(v) }));
      svg.append(el('text', { class: 'axis', x: L - 6, y: y(v) + 3, 'text-anchor': 'end' }, fmtNum(v)));
    }
    const tip = document.querySelector('.chart-tip') || document.body.appendChild(h('div', { class: 'chart-tip', hidden: true }));
    series.forEach((d, i) => {
      const x = L + i * slot + (slot - bw) / 2;
      const v = d[key];
      if (v > 0) {
        const top = y(v), base = y(0), r = Math.min(4, bw / 2, base - top);
        svg.append(el('path', { class: cls, d: 'M' + x + ' ' + base + 'V' + (top + r) + 'Q' + x + ' ' + top + ' ' + (x + r) + ' ' + top +
          'H' + (x + bw - r) + 'Q' + (x + bw) + ' ' + top + ' ' + (x + bw) + ' ' + (top + r) + 'V' + base + 'Z' }));
      }
      if (i === 0 || i === n - 1 || (n > 10 && i % Math.ceil(n / 6) === 0)) {
        svg.append(el('text', { class: 'axis', x: x + bw / 2, y: H - 6, 'text-anchor': 'middle' }, shortDay(d.day)));
      }
      const hit = el('rect', { class: 'hit', x: L + i * slot, y: T, width: slot, height: H - T - Bm });
      hit.addEventListener('pointerenter', e => { tip.hidden = false; tip.textContent = longDay(d.day) + ': ' + fmtNum(v) + ' ' + unit; moveTip(e); });
      hit.addEventListener('pointermove', moveTip);
      hit.addEventListener('pointerleave', () => { tip.hidden = true; });
      svg.append(hit);
    });
    function moveTip(e) { tip.style.left = (e.clientX + 12) + 'px'; tip.style.top = (e.clientY - 34) + 'px'; }
    svg.append(el('line', { class: 'grid', x1: L, x2: W - R, y1: y(0), y2: y(0), style: 'stroke: var(--line-2)' }));
    return svg;
  }

  const shortDay = d => { const [, m, g] = d.split('-'); return +g + '.' + +m; };
  const longDay = d => new Date(d + 'T12:00:00').toLocaleDateString('tr-TR', { day: 'numeric', month: 'long' });

  function statsTable(series) {
    return h('div', { class: 'table-wrap', style: { marginTop: '10px' } }, h('table', null,
      h('thead', null, h('tr', null, h('th', null, 'Gün'), h('th', null, 'Gösterim'), h('th', null, 'Tıklama'))),
      h('tbody', null, ...series.slice().reverse().map(d => h('tr', null,
        h('td', null, longDay(d.day)), h('td', { class: 'num' }, fmtNum(d.impressions)), h('td', { class: 'num' }, fmtNum(d.clicks)))))));
  }

  // ---------------------------------------------------------------- süre uzatma
  async function renew(s) {
    const user = RV.me();
    const amount = s.pixels * my.pricing.price_per_pixel;
    const b = (user && user.billing) || {};
    const inp = (name, attrs) => h('input', Object.assign({ name, value: b[name] || '' }, attrs || {}));
    const f = { name: inp('name', { autocomplete: 'name' }), phone: inp('phone', { autocomplete: 'tel' }), city: inp('city'),
                address: inp('address'), company: inp('company'), tax_id: inp('tax_id', { inputmode: 'numeric', maxlength: '11' }) };
    const terms = h('input', { type: 'checkbox' });
    const err = h('p', { class: 'form-error', role: 'alert' });
    const go = h('button', { class: 'btn primary', type: 'submit' }, fmtTL(amount) + ' öde');
    const form = h('form', { class: 'form', novalidate: true },
      h('dl', { class: 'summary' },
        h('div', null, h('dt', null, 'Alan'), h('dd', null, s.width_px + '×' + s.height_px + ' px')),
        h('div', null, h('dt', null, 'Ek süre'), h('dd', null, my.pricing.duration_days + ' gün')),
        h('div', null, h('dt', null, 'Yeni bitiş'), h('dd', null, '≈ ' + fmtDate(s.ends_at + my.pricing.duration_days * 86400))),
        h('div', { class: 'total' }, h('dt', null, 'Tutar'), h('dd', null, fmtTL(amount)))),
      h('div', { class: 'row2' }, field('Ad Soyad', f.name), field('Telefon', f.phone)),
      h('div', { class: 'row2' }, field('Şehir', f.city), field('Firma adı', f.company)),
      field('Fatura adresi', f.address), field('TC kimlik / vergi no', f.tax_id),
      h('label', { class: 'check' }, terms, h('span', null, h('a', { href: '/yasal', target: '_blank' }, 'Sözleşmeyi'), ' okudum, onaylıyorum.')),
      err, go);
    modal({ title: 'Yayın süresini uzat', wide: true, body: form });
    form.addEventListener('submit', async e => {
      e.preventDefault();
      if (!terms.checked) { err.textContent = 'Devam etmek için sözleşmeyi onaylamalısın.'; return; }
      go.disabled = true;
      try {
        const billing = {};
        for (const k in f) billing[k] = f[k].value;
        const r = await api('/api/slots/' + s.id + '/renew', { method: 'POST', body: { billing, accept_terms: true } });
        location.href = r.redirect_url;
      } catch (ex) { err.textContent = ex.message; go.disabled = false; }
    });
  }

  // ---------------------------------------------------------------- geçmiş
  const STATUS_TR = { pending: 'Ödeme bekleniyor', paid: 'Ödendi', expired: 'Süresi doldu', cancelled: 'İptal edildi',
                      failed: 'Başarısız', refund_needed: 'İade bekliyor', refunded: 'İade edildi' };
  function renderHistory() {
    const rows = my.orders.filter(o => o.status !== 'pending' || o.expires_at <= now());
    $('#history').hidden = !rows.length;
    $('#history-table').replaceChildren(
      h('thead', null, h('tr', null, h('th', null, 'Tarih'), h('th', null, 'Sipariş'), h('th', null, 'Tür'), h('th', null, 'Alan'), h('th', null, 'Tutar'), h('th', null, 'Durum'))),
      h('tbody', null, ...rows.map(o => h('tr', null,
        h('td', null, fmtDateTime(o.created_at)), h('td', null, o.ref), h('td', null, o.kind === 'renew' ? 'Süre uzatma' : 'Yeni alan'),
        h('td', null, o.width_px + '×' + o.height_px + ' px'), h('td', { class: 'num' }, fmtTL(o.amount)),
        h('td', null, STATUS_TR[o.status] || o.status)))));
  }

  init().catch(e => toast(e.message, { type: 'bad', ms: 10000 }));
})();
