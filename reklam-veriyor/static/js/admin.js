/* Reklam Veriyor — Yönetim paneli */
'use strict';

(() => {
  const { $, h, api, toast, field, fmtTL, fmtNum, fmtDate, fmtDateTime, openAdCard, miniBoard, placeRect } = RV;
  let D = null;
  let tab = 'overview';

  const STATUS_TR = { pending: 'Ödeme bekleniyor', paid: 'Ödendi', expired: 'Süresi doldu', cancelled: 'İptal', failed: 'Başarısız',
                      refund_needed: 'İade gerekli', refunded: 'İade edildi' };
  const STATUS_TONE = { paid: 'ok', pending: 'warn', refund_needed: 'bad', refunded: 'info', failed: 'bad' };

  async function init() {
    const u = await RV.loadMe();
    if (!u || !u.is_admin) {
      $('#denied').hidden = false;
      if (u) $('#denied-msg').textContent = u.email + ' bir yönetici hesabı değil. Yönetici e-postası ayarlar.php dosyasında tanımlanır.';
      $('#login-btn').onclick = async () => { if (await RV.authFlow('Yönetici hesabınızla giriş yapın.')) location.reload(); };
      return;
    }
    $('#logout').hidden = false;
    $('#logout').onclick = async () => { await RV.logout(); location.href = '/'; };
    await load();
  }

  async function load() {
    D = await api('/api/admin/overview');
    $('#app').hidden = false;
    renderHead();
    renderTabs();
    renderView();
  }

  function renderHead() {
    const p = D.payment;
    const chip = $('#pay-chip');
    chip.className = 'chip ' + (p.provider === 'test' ? 'warn' : p.live ? 'ok' : 'info');
    chip.textContent = 'Ödeme: ' + p.label;
    const alerts = [];
    if (p.provider === 'test') {
      alerts.push(h('p', { class: 'alert' }, h('strong', null, 'Test ödemesi açık: '),
        'şu an herkes gerçek ödeme yapmadan alan alabilir. Satışa başlamadan önce ayarlar.php içinde ',
        h('code', null, "'odeme_saglayici' => 'iyzico'"), ' yapın ve iyzico anahtarlarınızı girin.'));
    }
    if (D.totals.refund_needed) {
      alerts.push(h('p', { class: 'alert bad' }, D.totals.refund_needed + ' siparişte iade gerekiyor (ödeme geldiğinde alan dolmuştu veya tutar eşleşmedi). Siparişler sekmesine bakın.'));
    }
    if (D.totals.pending_review) {
      alerts.push(h('p', { class: 'alert info' }, D.totals.pending_review + ' reklam yayın onayı bekliyor.'));
    }
    $('#alerts').replaceChildren(...alerts.map(a => { a.style.marginBottom = '12px'; return a; }));
    const t = D.totals;
    const occ = t.sold_blocks / t.total_blocks * 100;
    const kpi = (label, value, sub) => h('div', { class: 'stat' }, h('dt', null, label), h('dd', null, value), sub ? h('div', { class: 'small muted' }, sub) : null);
    $('#kpis').replaceChildren(
      kpi('Toplam gelir', fmtTL(t.revenue), t.paid_orders + ' ödenmiş sipariş'),
      kpi('Son 30 gün', fmtTL(t.revenue_30d)),
      kpi('Doluluk', occ.toLocaleString('tr-TR', { maximumFractionDigits: 1 }) + '%', fmtNum(t.sold_blocks) + ' / ' + fmtNum(t.total_blocks) + ' blok satıldı'),
      kpi('Yayındaki reklam', fmtNum(t.active_slots), fmtNum(t.impressions) + ' gösterim · ' + fmtNum(t.clicks) + ' tıklama'));
  }

  function renderTabs() {
    const items = [['overview', 'Pano'], ['settings', 'Fiyat ve süre'], ['orders', 'Siparişler'], ['slots', 'Reklam alanları', D.totals.pending_review],
                   ['legal', 'Yasal metin'], ['demo', 'Demo']];
    $('#tabs').replaceChildren(...items.map(([k, l, n]) => h('button', {
      class: tab === k ? 'on' : '', role: 'tab', onclick: () => { tab = k; renderTabs(); renderView(); },
    }, l, n ? h('span', { class: 'count' }, n) : null)));
  }

  function renderView() {
    const v = { overview, settings, orders, slots, legal, demo }[tab]();
    $('#view').replaceChildren(v);
  }

  // ---------------------------------------------------------------- pano doluluğu
  function overview() {
    const B = D.board;
    const mb = h('div', { class: 'mini-board' });
    for (const t of D.taken) {
      const c = h('div', { class: 'mb-cell ' + t.state });
      placeRect(c, t, B);
      mb.append(c);
    }
    return h('div', { class: 'card' },
      h('h2', null, 'Panonun doluluğu'),
      h('div', { class: 'legend' }, h('span', null, h('i', { class: 'swatch sold' }), 'Satıldı'), h('span', null, h('i', { class: 'swatch reserved' }), 'Rezerve (ödeme sürüyor)'),
        h('span', null, h('i', { class: 'swatch free' }), 'Boş')),
      h('div', { class: 'occupancy' }, mb),
      h('p', { class: 'small muted', style: { marginBottom: 0 } }, 'Pano ' + B.width + '×' + B.height + ' sanal piksel, ' + B.block + '×' + B.block +
        ' px bloklara bölünmüş (' + B.cols + '×' + B.rows + ' = ' + fmtNum(B.cols * B.rows) + ' blok). Fiyat ekran boyutundan bağımsız olarak bu sanal piksellerle hesaplanır.'));
  }

  // ---------------------------------------------------------------- ayarlar
  function settings() {
    const s = D.settings;
    const price = h('input', { value: (s.price_per_pixel / 100).toLocaleString('tr-TR', { minimumFractionDigits: 2 }), inputmode: 'decimal' });
    const days = h('input', { type: 'number', min: '1', max: '3650', value: s.duration_days });
    const reserve = h('input', { type: 'number', min: '5', max: '120', value: s.reserve_minutes });
    const minB = h('input', { type: 'number', min: '1', value: s.min_blocks });
    const maxB = h('input', { type: 'number', min: '0', value: s.max_blocks });
    const mod = h('input', { type: 'checkbox', checked: s.moderation });
    const ex = h('div', { class: 'price-ex' });
    const err = h('p', { class: 'form-error', role: 'alert' });
    const B = D.board;
    const kurus = () => {
      const v = String(price.value).trim().replace(/\./g, '').replace(',', '.');
      const n = Math.round(parseFloat(v) * 100);
      return Number.isFinite(n) ? n : NaN;
    };
    function updEx() {
      const k = kurus();
      if (!(k > 0)) { ex.textContent = 'Geçerli bir fiyat yazın (ör. 0,50).'; return; }
      const blk = B.block * B.block;
      ex.replaceChildren(
        h('span', null, '1 blok (' + B.block + '×' + B.block + ' = ' + blk + ' px): ', h('b', null, fmtTL(blk * k))),
        h('span', null, '120×60 px (' + fmtNum(7200) + ' px): ', h('b', null, fmtTL(7200 * k))),
        h('span', null, 'Panonun tamamı (' + fmtNum(B.width * B.height) + ' px): ', h('b', null, fmtTL(B.width * B.height * k))));
    }
    price.oninput = updEx;
    updEx();
    const save = h('button', { class: 'btn primary', type: 'submit' }, 'Kaydet');
    const form = h('form', { class: 'form' },
      h('div', { class: 'row2' },
        h('div', null, field('Piksel fiyatı (TL)', price), ex),
        field('Yayın süresi (gün)', days, 'Satın alınan alan bu kadar gün yayında kalır.')),
      h('div', { class: 'row2' },
        field('Ödeme sırasında rezervasyon (dakika)', reserve, 'Ödeme tamamlanmazsa alan bu sürenin sonunda serbest kalır.'),
        h('label', { class: 'check', style: { alignSelf: 'center' } }, mod, h('span', null, 'Yayın öncesi onay: reklamlar ben onaylayınca panoda görünsün'))),
      h('div', { class: 'row2' }, field('Bir siparişte en az blok', minB), field('Bir siparişte en fazla blok (0 = sınırsız)', maxB)),
      h('p', { class: 'small muted', style: { margin: 0 } }, 'Yeni fiyat ve süre yalnızca bundan sonraki siparişlere uygulanır. Ödenmiş siparişler değişmez.'),
      err, h('div', null, save));
    form.addEventListener('submit', async e => {
      e.preventDefault();
      err.textContent = '';
      const k = kurus();
      if (!(k >= 1)) { err.textContent = 'Piksel fiyatı en az 0,01 TL olmalı.'; return; }
      save.disabled = true;
      try {
        await api('/api/admin/settings', { method: 'POST', body: {
          price_per_pixel: k, duration_days: +days.value, reserve_minutes: +reserve.value,
          min_blocks: +minB.value, max_blocks: +maxB.value, moderation: mod.checked } });
        toast('Ayarlar kaydedildi.', { type: 'ok' });
        await load();
      } catch (ex2) { err.textContent = ex2.message; } finally { save.disabled = false; }
    });
    const p = D.payment;
    const copyRow = (label, text) => h('div', { class: 'field' }, h('span', null, label), h('div', { class: 'copy' }, h('code', null, text),
      h('button', { class: 'btn small', type: 'button', onclick: () => navigator.clipboard.writeText(text).then(() => toast('Kopyalandı.')) }, 'Kopyala')));
    return h('div', null,
      h('div', { class: 'card' }, h('h2', null, 'Fiyat ve yayın süresi'), form),
      h('div', { class: 'card' }, h('h2', null, 'Ödeme sağlayıcısı'),
        h('p', { class: 'muted' }, 'Şu an: ', h('b', null, p.label), '. Sağlayıcı ve iyzico anahtarları güvenlik için yalnızca ayarlar.php dosyasından değiştirilir.'),
        copyRow('iyzico geri dönüş adresi (otomatik gönderilir)', p.callback_url),
        copyRow('iyzico panelinde bildirim (webhook) adresi olarak girin', p.webhook_url)));
  }

  // ---------------------------------------------------------------- siparişler
  function orders() {
    if (!D.orders.length) return h('div', { class: 'card empty' }, h('h2', null, 'Henüz sipariş yok'));
    const act = async (o, a, msg) => {
      try { const r = await api('/api/admin/orders/' + o.ref + '/' + a, { method: 'POST' }); toast(msg || (r.result ? 'Sağlayıcı yanıtı: ' + r.result.state : 'Tamam.')); await load(); }
      catch (e) { toast(e.message, { type: 'bad' }); }
    };
    return h('div', { class: 'table-wrap' }, h('table', null,
      h('thead', null, h('tr', null, ...['Tarih', 'Sipariş', 'E-posta', 'Tür', 'Alan', 'Tutar', 'Durum', 'Not', ''].map(t => h('th', null, t)))),
      h('tbody', null, ...D.orders.map(o => h('tr', null,
        h('td', null, fmtDateTime(o.created_at)), h('td', null, o.ref), h('td', null, o.email),
        h('td', null, o.kind === 'renew' ? 'Uzatma' : 'Yeni'), h('td', null, o.width_px + '×' + o.height_px + ' px'),
        h('td', { class: 'num' }, fmtTL(o.amount)),
        h('td', null, h('span', { class: 'chip ' + (STATUS_TONE[o.status] || '') }, STATUS_TR[o.status] || o.status)),
        h('td', { style: { whiteSpace: 'normal', minWidth: '180px' }, class: 'small muted' }, o.note || (o.billing ? o.billing.name + ' · ' + o.billing.phone : '')),
        h('td', null,
          ['pending', 'expired'].includes(o.status) && o.provider === D.payment.provider && o.provider !== 'test'
            ? h('button', { class: 'btn small', onclick: () => act(o, 'check') }, 'Ödemeyi sorgula') : null,
          o.status === 'refund_needed' ? h('button', { class: 'btn small', onclick: () => { if (confirm('İadeyi ödeme sağlayıcısının panelinden yaptınız mı?')) act(o, 'refunded', 'İade edildi olarak işaretlendi.'); } }, 'İade yapıldı') : null,
          o.status === 'pending' ? h('button', { class: 'btn small danger', onclick: () => { if (confirm('Rezervasyon iptal edilsin mi?')) act(o, 'cancel', 'İptal edildi.'); } }, 'İptal') : null))))));
  }

  // ---------------------------------------------------------------- alanlar
  function slots() {
    if (!D.slots.length) return h('div', { class: 'card empty' }, h('h2', null, 'Henüz satılmış alan yok'));
    const act = async (s, a, msg, note) => {
      try { await api('/api/admin/slots/' + s.id + '/' + a, { method: 'POST', body: { note } }); toast(msg); await load(); }
      catch (e) { toast(e.message, { type: 'bad' }); }
    };
    const preview = c => openAdCard(Object.assign({ w: 1, h: 1, href: '#' }, c, { display_url: c.url }), { preview: true });
    return h('div', { class: 'table-wrap' }, h('table', null,
      h('thead', null, h('tr', null, ...['', 'Alan', 'Sahibi', 'Boyut', 'Bitiş', 'Durum', 'Gösterim', 'Tıklama', 'Bağlantı', ''].map(t => h('th', null, t)))),
      h('tbody', null, ...D.slots.map(s => {
        const c = s.content || {};
        const d = s.draft;
        const live = s.status === 'active' || s.status === 'suspended';
        let state = s.status === 'expired' ? ['bad', 'Süresi doldu'] : s.status === 'suspended' ? ['bad', 'Askıda'] : !c.image ? ['warn', 'Görsel yok'] : ['ok', 'Yayında'];
        if (s.review === 'pending') state = ['warn', 'Onay bekliyor'];
        return h('tr', null,
          h('td', null, c.image_url ? h('span', { class: 'thumb-sm' }, h('img', { src: c.image_url, alt: '' })) : null),
          h('td', null, '#' + s.id + (s.is_demo ? ' (demo)' : ''), c.title ? h('div', { class: 'small muted' }, c.title) : null),
          h('td', null, s.email), h('td', null, s.width_px + '×' + s.height_px), h('td', null, fmtDate(s.ends_at)),
          h('td', null, h('span', { class: 'chip ' + state[0] }, state[1])),
          h('td', { class: 'num' }, fmtNum(s.impressions)), h('td', { class: 'num' }, fmtNum(s.clicks)),
          h('td', { class: 'small' }, c.url ? h('a', { href: c.url, target: '_blank', rel: 'noopener noreferrer' }, c.url.replace(/^https?:\/\//, '').slice(0, 32)) : '—'),
          h('td', null,
            d && s.review === 'pending' ? [
              h('button', { class: 'btn small', onclick: () => preview(Object.assign({}, d, { w: s.w, h: s.h })) }, 'Yeni içeriği gör'),
              h('button', { class: 'btn small primary', onclick: () => act(s, 'approve', 'Onaylandı, panoda yayında.') }, 'Onayla'),
              h('button', { class: 'btn small danger', onclick: () => { const n = prompt('Ret nedeni (reklamverene gösterilir):', 'İçerik kurallara uygun bulunmadı.'); if (n !== null) act(s, 'reject', 'Reddedildi.', n); } }, 'Reddet'),
            ] : null,
            c.image && live ? h('button', { class: 'btn small', onclick: () => preview(Object.assign({}, c, { w: s.w, h: s.h })) }, 'Önizle') : null,
            s.status === 'active' ? h('button', { class: 'btn small', onclick: () => { const n = prompt('Askıya alma nedeni (reklamverene gösterilir):', ''); if (n !== null) act(s, 'suspend', 'Askıya alındı.', n); } }, 'Askıya al') : null,
            s.status === 'suspended' ? h('button', { class: 'btn small', onclick: () => act(s, 'unsuspend', 'Yeniden yayında.') }, 'Yayına al') : null,
            live ? h('button', { class: 'btn small danger', onclick: () => { if (confirm('Alan #' + s.id + ' kaldırılsın ve satışa açılsın mı? Bu işlem geri alınamaz; gerekiyorsa iadeyi ayrıca yapın.')) act(s, 'remove', 'Alan kaldırıldı.'); } }, 'Kaldır') : null));
      }))));
  }

  // ---------------------------------------------------------------- yasal metin
  function legal() {
    const ta = h('textarea', { style: { minHeight: '420px', fontFamily: 'inherit' } });
    ta.value = D.settings.legal_text;
    const save = h('button', { class: 'btn primary', type: 'button' }, 'Kaydet');
    save.onclick = async () => {
      save.disabled = true;
      try { await api('/api/admin/settings', { method: 'POST', body: { legal_text: ta.value } }); toast('Kaydedildi.', { type: 'ok' }); D.settings.legal_text = ta.value; }
      catch (e) { toast(e.message, { type: 'bad' }); } finally { save.disabled = false; }
    };
    return h('div', { class: 'card form' },
      h('h2', null, 'Ön bilgilendirme ve mesafeli satış sözleşmesi'),
      h('p', { class: 'muted', style: { margin: 0 } }, 'Ödeme öncesi alıcıya onaylatılan metin. [doldurun] yazan yerleri kendi bilgilerinizle değiştirin. iyzico başvurusunda bu sayfanın adresi istenir: ',
        h('a', { href: '/yasal', target: '_blank' }, '/yasal')),
      field('Metin', ta), h('div', null, save));
  }

  // ---------------------------------------------------------------- demo
  function demo() {
    const n = D.totals.demo_slots;
    const run = async (a) => {
      try {
        const r = await api('/api/admin/demo/' + a, { method: 'POST' });
        toast(a === 'load' ? r.added + ' demo reklam eklendi.' : r.removed + ' demo reklam kaldırıldı.', { type: 'ok' });
        await load();
      } catch (e) { toast(e.message, { type: 'bad' }); }
    };
    return h('div', { class: 'card' },
      h('h2', null, 'Demo reklamlar'),
      h('p', { class: 'muted' }, 'Panoyu ilk açtığınızda boş görünmesin diye kurgusal markalarla ' +
        '34 örnek reklam yüklenebilir. Gerçek satışa başlamadan önce kaldırın; kaldırınca alanları satışa açılır.'),
      h('p', null, 'Şu an panoda ', h('b', null, n), ' demo reklam var.'),
      h('div', { class: 'editor-actions' },
        h('button', { class: 'btn', onclick: () => run('load') }, 'Demo reklamları yükle'),
        n ? h('button', { class: 'btn danger', onclick: () => { if (confirm('Tüm demo reklamlar kaldırılsın mı?')) run('remove'); } }, 'Demo reklamları kaldır') : null));
  }

  init().catch(e => toast(e.message, { type: 'bad', ms: 10000 }));
})();
