<?php
/* Reklam Veriyor — sayfalar ve API uçları */
declare(strict_types=1);

// ---------------------------------------------------------------- içerik yardımcıları

const BUTON_KONUM = ['tl', 'tc', 'tr', 'ml', 'mc', 'mr', 'bl', 'bc', 'br', 'none'];

function renk_mi($c): bool
{
    return is_string($c) && (bool) preg_match('/^#(?:[0-9a-fA-F]{3}){1,2}$/', $c);
}

function url_temizle($ham): string
{
    $u = trim((string) ($ham ?? ''));
    if ($u === '') return '';
    if (!preg_match('#^[a-zA-Z][a-zA-Z0-9+.-]*://#', $u)) $u = 'https://' . $u;
    if (strlen($u) > 500 || preg_match('/[\s<>"\']/', $u)) throw new ApiHata('Bağlantı adresi geçersiz.');
    $p = parse_url($u);
    $sema = strtolower($p['scheme'] ?? '');
    $host = $p['host'] ?? '';
    if (!in_array($sema, ['http', 'https'], true) || $host === '' || !str_contains($host, '.')) {
        throw new ApiHata('Bağlantı http:// veya https:// ile başlayan geçerli bir adres olmalı.');
    }
    return $u;
}

function gorsel_url(?string $ad): string
{
    if (!$ad) return '';
    return str_starts_with($ad, 'demo/') ? '/static/' . $ad : '/u/' . $ad;
}

function gorunen_url(?string $u): string
{
    if (!$u) return '';
    $p = parse_url($u);
    $host = preg_replace('/^www\./', '', $p['host'] ?? '');
    $yol = $p['path'] ?? '';
    $s = $host . (in_array($yol, ['', '/'], true) ? '' : $yol);
    return mb_strlen($s) <= 48 ? $s : mb_substr($s, 0, 46) . '…';
}

function icerik_temizle(array $d, int $uid, array $slot): array
{
    $gorsel = (string) ($d['image'] ?? '');
    if ($gorsel !== '') {
        if (str_starts_with($gorsel, 'demo/') && (int) $slot['is_demo']) {
            $ok = (bool) preg_match('#^demo/[a-z0-9-]+\.svg$#', $gorsel);
        } else {
            $ok = (bool) satir('SELECT 1 FROM uploads WHERE filename = ? AND user_id = ?', [$gorsel, $uid]);
        }
        if (!$ok) throw new ApiHata('Görsel bulunamadı, lütfen yeniden yükleyin.');
    }
    $bg = $d['bg'] ?? '#111318';
    $bbg = $d['button_bg'] ?? '#ffc83d';
    $bfg = $d['button_fg'] ?? '#14161b';
    foreach ([$bg, $bbg, $bfg] as $c) if (!renk_mi($c)) throw new ApiHata('Renk değeri geçersiz.');
    $konum = $d['button_pos'] ?? 'br';
    if (!in_array($konum, BUTON_KONUM, true)) throw new ApiHata('Buton konumu geçersiz.');
    $yazi = metin_temizle($d['button_text'] ?? '', 24);
    if ($konum !== 'none' && $yazi === '') $yazi = 'Siteye Git';
    return [
        'image' => $gorsel,
        'fit' => ($d['fit'] ?? '') === 'contain' ? 'contain' : 'cover',
        'bg' => $bg,
        'title' => metin_temizle($d['title'] ?? '', 60),
        'description' => metin_temizle($d['description'] ?? '', 160),
        'button_text' => $yazi,
        'button_pos' => $konum,
        'button_bg' => $bbg,
        'button_fg' => $bfg,
        'url' => url_temizle($d['url'] ?? ''),
    ];
}

function reklam_json(array $s, array $c): array
{
    return [
        'id' => (int) $s['id'], 'x' => (int) $s['x'], 'y' => (int) $s['y'], 'w' => (int) $s['w'], 'h' => (int) $s['h'],
        'image_url' => gorsel_url($c['image'] ?? ''), 'fit' => $c['fit'] ?? 'cover', 'bg' => $c['bg'] ?? '#111318',
        'title' => $c['title'] ?? '', 'description' => $c['description'] ?? '',
        'button_text' => $c['button_text'] ?? '', 'button_pos' => $c['button_pos'] ?? 'br',
        'button_bg' => $c['button_bg'] ?? '#ffc83d', 'button_fg' => $c['button_fg'] ?? '#14161b',
        'display_url' => gorunen_url($c['url'] ?? ''), 'href' => '/r/' . (int) $s['id'],
    ];
}

function pano_durumu(?int $ben = null): array
{
    $t = time();
    $reklamlar = [];
    $dolu = [];
    foreach (q("SELECT * FROM slots WHERE status IN ('active','suspended') AND ends_at > ? ORDER BY id", [$t])->fetchAll() as $s) {
        $c = $s['content'] ? json_decode($s['content'], true) : null;
        $dolu[] = ['x' => (int) $s['x'], 'y' => (int) $s['y'], 'w' => (int) $s['w'], 'h' => (int) $s['h'], 'state' => 'sold',
                   'mine' => $ben !== null && (int) $s['user_id'] === $ben, 'slot_id' => (int) $s['id']];
        if ($s['status'] === 'active' && $c && !empty($c['image'])) $reklamlar[] = reklam_json($s, $c);
    }
    foreach (q("SELECT x, y, w, h, user_id FROM orders WHERE status = 'pending' AND kind = 'new' AND expires_at > ?", [$t])->fetchAll() as $o) {
        $dolu[] = ['x' => (int) $o['x'], 'y' => (int) $o['y'], 'w' => (int) $o['w'], 'h' => (int) $o['h'], 'state' => 'reserved',
                   'mine' => $ben !== null && (int) $o['user_id'] === $ben];
    }
    return [$reklamlar, $dolu];
}

function pano_ayari(array $a): array
{
    $p = saglayici();
    return [
        'board' => ['width' => BOARD_W, 'height' => BOARD_H, 'block' => BLOCK, 'cols' => COLS, 'rows' => ROWS],
        'pricing' => [
            'price_per_pixel' => $a['price_per_pixel'], 'duration_days' => $a['duration_days'],
            'reserve_minutes' => $a['reserve_minutes'], 'min_blocks' => $a['min_blocks'],
            'max_blocks' => $a['max_blocks'], 'currency' => 'TRY',
        ],
        'payment' => ['provider' => $p->ad, 'live' => $p->canli, 'label' => $p->etiket],
    ];
}

function dortgen_oku(array $d, array $a): array
{
    foreach (['x', 'y', 'w', 'h'] as $k) {
        if (!isset($d[$k]) || !is_numeric($d[$k])) throw new ApiHata('Geçersiz seçim.');
    }
    [$x, $y, $w, $h] = [(int) $d['x'], (int) $d['y'], (int) $d['w'], (int) $d['h']];
    if ($w < 1 || $h < 1 || $x < 0 || $y < 0 || $x + $w > COLS || $y + $h > ROWS) throw new ApiHata('Seçim panonun dışına taşıyor.');
    $blok = $w * $h;
    if ($blok < $a['min_blocks']) throw new ApiHata('En az ' . $a['min_blocks'] . ' blok seçmelisiniz.');
    if ($a['max_blocks'] && $blok > $a['max_blocks']) throw new ApiHata('Tek seferde en fazla ' . $a['max_blocks'] . ' blok alınabilir.');
    return [$x, $y, $w, $h];
}

function fiyat(int $w, int $h, array $a): array
{
    $px = $w * $h * BLOCK_PX;
    return [$px, $px * $a['price_per_pixel']];
}

function fatura_temizle(array $d): array
{
    $b = is_array($d['billing'] ?? null) ? $d['billing'] : [];
    $f = [
        'name' => metin_temizle($b['name'] ?? '', 80),
        'phone' => metin_temizle($b['phone'] ?? '', 20),
        'city' => metin_temizle($b['city'] ?? '', 40),
        'address' => metin_temizle($b['address'] ?? '', 200),
        'tax_id' => substr((string) preg_replace('/\D/', '', (string) ($b['tax_id'] ?? '')), 0, 11),
        'company' => metin_temizle($b['company'] ?? '', 100),
    ];
    if (mb_strlen($f['name']) < 3 || !str_contains($f['name'], ' ')) throw new ApiHata('Fatura için ad ve soyadınızı yazın.');
    if (strlen((string) preg_replace('/\D/', '', $f['phone'])) < 10) throw new ApiHata('Geçerli bir telefon numarası yazın.');
    if (mb_strlen($f['city']) < 2 || mb_strlen($f['address']) < 5) throw new ApiHata('Fatura adresinizi (şehir ve adres) yazın.');
    if (empty($d['accept_terms'])) throw new ApiHata('Devam etmek için sözleşmeyi onaylamalısınız.');
    return $f;
}

function siparis_json(array $o): array
{
    return [
        'ref' => $o['ref'], 'kind' => $o['kind'], 'slot_id' => $o['slot_id'] !== null ? (int) $o['slot_id'] : null,
        'x' => (int) $o['x'], 'y' => (int) $o['y'], 'w' => (int) $o['w'], 'h' => (int) $o['h'],
        'width_px' => (int) $o['w'] * BLOCK, 'height_px' => (int) $o['h'] * BLOCK, 'pixels' => (int) $o['pixels'],
        'amount' => (int) $o['amount'], 'duration_days' => (int) $o['duration_days'], 'status' => $o['status'],
        'provider' => $o['provider'], 'created_at' => (int) $o['created_at'], 'expires_at' => (int) $o['expires_at'],
        'paid_at' => $o['paid_at'] !== null ? (int) $o['paid_at'] : null, 'note' => $o['note'],
    ];
}

function bekleyen_sinir(int $uid): void
{
    $t = time();
    if ((int) deger("SELECT COUNT(*) FROM orders WHERE user_id = ? AND status = 'pending' AND expires_at > ?", [$uid, $t]) >= MAX_PENDING_PER_USER) {
        throw new ApiHata('Ödemesi tamamlanmamış ' . MAX_PENDING_PER_USER . ' siparişiniz var. Önce onları tamamlayın veya iptal edin.', 429);
    }
    if ((int) deger("SELECT COUNT(*) FROM orders WHERE ip = ? AND status = 'pending' AND expires_at > ?", [istemci_ip(), $t]) >= MAX_PENDING_PER_IP) {
        throw new ApiHata('Bu bağlantıdan çok fazla bekleyen rezervasyon var. Biraz sonra tekrar deneyin.', 429);
    }
}

function odeme_baslat(int $oid, array $u, array $fatura): string
{
    $o = satir('SELECT * FROM orders WHERE id = ?', [$oid]);
    $tur = $o['kind'] === 'renew' ? 'Süre uzatma' : 'Reklam alanı';
    $ad = $tur . ' ' . alan_etiketi($o) . ', ' . $o['duration_days'] . ' gün';
    try {
        $r = saglayici()->baslat($o, ['user' => $u, 'billing' => $fatura, 'ip' => istemci_ip(),
                                     'callback_url' => site_adresi() . '/odeme/iyzico/geri-donus', 'item_name' => $ad]);
    } catch (OdemeHatasi $e) {
        tx(function () use ($oid, $e) {
            q("UPDATE orders SET status = 'failed', note = ? WHERE id = ?", [mb_substr($e->getMessage(), 0, 300), $oid]);
            q('DELETE FROM cell_locks WHERE order_id = ?', [$oid]);
        });
        throw new ApiHata('Ödeme başlatılamadı: ' . $e->getMessage(), 502);
    }
    tx(fn() => q('UPDATE orders SET provider_token = ?, provider_url = ? WHERE id = ?', [$r['token'], $r['url'], $oid]));
    return $r['url'];
}

// ---------------------------------------------------------------- ödeme onayı

/** Sağlayıcının doğruladığı ödemeyi işler. Birden çok kez çağrılsa da güvenlidir. */
function odeme_onayla(int $oid, ?string $odeme_id, ?int $odenen): ?array
{
    $iade = tx(function () use ($oid, $odeme_id, $odenen) {
        $o = satir('SELECT * FROM orders WHERE id = ?', [$oid]);
        if (!$o || in_array($o['status'], ['paid', 'refund_needed', 'refunded'], true)) return false;
        $t = time();
        if ($odenen !== (int) $o['amount']) {
            q("UPDATE orders SET status = 'refund_needed', provider_payment_id = ?, paid_at = ?, note = ? WHERE id = ?",
              [$odeme_id, $t, 'Ödenen tutar (' . var_export($odenen, true) . ') sipariş tutarıyla eşleşmedi', $oid]);
            q('DELETE FROM cell_locks WHERE order_id = ? AND slot_id IS NULL', [$oid]);
            return false;
        }
        q('DELETE FROM cell_locks WHERE expires_at <= ?', [$t]);
        $sure = (int) $o['duration_days'] * 86400;
        [$x, $y, $w, $h] = [(int) $o['x'], (int) $o['y'], (int) $o['w'], (int) $o['h']];
        $iade = false;
        if ($o['kind'] === 'renew') {
            $s = satir('SELECT * FROM slots WHERE id = ?', [$o['slot_id']]);
            $diger = (int) deger('SELECT COUNT(*) FROM cell_locks WHERE (slot_id IS NULL OR slot_id != ?) AND ' . dortgen_sql(),
                                 array_merge([(int) $o['slot_id']], dortgen_arg($x, $y, $w, $h)));
            if (!$s || !in_array($s['status'], ['active', 'suspended', 'expired'], true) || $diger) {
                $iade = true;
            } else {
                $bitis = max((int) $s['ends_at'], $t) + $sure;
                $durum = $s['status'] === 'expired' ? 'active' : $s['status'];
                q('UPDATE slots SET ends_at = ?, status = ? WHERE id = ?', [$bitis, $durum, $s['id']]);
                q('DELETE FROM cell_locks WHERE slot_id = ?', [$s['id']]);
                hucre_kilitle(hucreler($x, $y, $w, $h), null, (int) $s['id'], $bitis);
                q("UPDATE orders SET status = 'paid', paid_at = ?, provider_payment_id = ? WHERE id = ?", [$t, $odeme_id, $oid]);
            }
        } else {
            // Rezervasyon süresi dolduysa ve alan hâlâ boşsa satış yine tamamlanır.
            $diger = (int) deger('SELECT COUNT(*) FROM cell_locks WHERE (order_id IS NULL OR order_id != ?) AND ' . dortgen_sql(),
                                 array_merge([$oid], dortgen_arg($x, $y, $w, $h)));
            if ($diger) {
                $iade = true;
            } else {
                $bitis = $t + $sure;
                q("INSERT INTO slots(user_id, order_id, x, y, w, h, starts_at, ends_at, status, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?)",
                  [$o['user_id'], $oid, $x, $y, $w, $h, $t, $bitis, $t]);
                $sid = (int) db()->lastInsertId();
                q('DELETE FROM cell_locks WHERE order_id = ?', [$oid]);
                hucre_kilitle(hucreler($x, $y, $w, $h), null, $sid, $bitis);
                q("UPDATE orders SET status = 'paid', paid_at = ?, provider_payment_id = ?, slot_id = ? WHERE id = ?", [$t, $odeme_id, $sid, $oid]);
            }
        }
        if ($iade) {
            q("UPDATE orders SET status = 'refund_needed', paid_at = ?, provider_payment_id = ?, note = ? WHERE id = ?",
              [$t, $odeme_id, 'Ödeme geldiğinde alan artık boş değildi; iade gerekiyor.', $oid]);
            q('DELETE FROM cell_locks WHERE order_id = ? AND slot_id IS NULL', [$oid]);
        }
        return $iade;
    });
    if ($iade) {
        $o = satir('SELECT * FROM orders WHERE id = ?', [$oid]);
        $p = saglayici();
        if ($o['provider'] === $p->ad && $p->iade($o)) {
            tx(fn() => q("UPDATE orders SET status = 'refunded', note = ? WHERE id = ?",
                         ['Alan başkasına geçtiği için ödeme otomatik iade edildi.', $oid]));
        }
    }
    return satir('SELECT * FROM orders WHERE id = ?', [$oid]);
}

function odeme_basarisiz(int $oid, ?string $mesaj): void
{
    tx(function () use ($oid, $mesaj) {
        q("UPDATE orders SET status = 'failed', note = ? WHERE id = ? AND status IN ('pending','expired')",
          [mb_substr($mesaj ?: 'Ödeme başarısız', 0, 300), $oid]);
        q('DELETE FROM cell_locks WHERE order_id = ? AND slot_id IS NULL', [$oid]);
    });
}

function saglayicidan_sonuc(int $oid): array
{
    $o = satir('SELECT * FROM orders WHERE id = ?', [$oid]);
    try {
        $r = saglayici()->sorgula($o);
    } catch (OdemeHatasi $e) {
        return ['state' => 'error', 'message' => $e->getMessage()];
    }
    if ($r['state'] === 'success') odeme_onayla($oid, $r['payment_id'] ?? null, $r['amount'] ?? null);
    elseif ($r['state'] === 'failure') odeme_basarisiz($oid, $r['message'] ?? null);
    elseif (!empty($r['message'])) tx(fn() => q('UPDATE orders SET note = ? WHERE id = ?', [mb_substr($r['message'], 0, 300), $oid]));
    return $r;
}

// ---------------------------------------------------------------- reklamlarım yardımcıları

function alan_toplamlari(array $ids): array
{
    if (!$ids) return [];
    $yer = implode(',', array_fill(0, count($ids), '?'));
    $out = [];
    foreach (q("SELECT slot_id, SUM(impressions) i, SUM(clicks) k FROM stats_daily WHERE slot_id IN ($yer) GROUP BY slot_id", $ids)->fetchAll() as $r) {
        $out[(int) $r['slot_id']] = [(int) $r['i'], (int) $r['k']];
    }
    return $out;
}

function alan_json(array $s, array $top): array
{
    $t = time();
    $canli = in_array($s['status'], ['active', 'suspended'], true) && (int) $s['ends_at'] > $t;
    $ekle = function ($ham) {
        if (!$ham) return null;
        $c = json_decode($ham, true);
        $c['image_url'] = gorsel_url($c['image'] ?? '');
        return $c;
    };
    [$i, $k] = $top[(int) $s['id']] ?? [0, 0];
    return [
        'id' => (int) $s['id'], 'x' => (int) $s['x'], 'y' => (int) $s['y'], 'w' => (int) $s['w'], 'h' => (int) $s['h'],
        'width_px' => (int) $s['w'] * BLOCK, 'height_px' => (int) $s['h'] * BLOCK, 'pixels' => (int) $s['w'] * (int) $s['h'] * BLOCK_PX,
        'starts_at' => (int) $s['starts_at'], 'ends_at' => (int) $s['ends_at'],
        'status' => ($canli || $s['status'] === 'removed') ? $s['status'] : 'expired',
        'content' => $ekle($s['content']), 'draft' => $ekle($s['draft']),
        'review' => $s['review'], 'review_note' => $s['review_note'], 'admin_note' => $s['admin_note'],
        'published_at' => $s['published_at'] !== null ? (int) $s['published_at'] : null, 'is_demo' => (bool) $s['is_demo'],
        'impressions' => $i, 'clicks' => $k,
        'can_renew' => $s['status'] === 'active' && (int) $s['ends_at'] > $t,
    ];
}

function kendi_alanim(int $sid): array
{
    $s = satir('SELECT * FROM slots WHERE id = ? AND user_id = ?', [$sid, (int) giris_gerekli()['id']]);
    if (!$s) throw new ApiHata('Reklam alanı bulunamadı.', 404);
    return $s;
}

function kendi_siparisim(string $ref): array
{
    $o = satir('SELECT * FROM orders WHERE ref = ? AND user_id = ?', [$ref, (int) giris_gerekli()['id']]);
    if (!$o) throw new ApiHata('Sipariş bulunamadı.', 404);
    return $o;
}

function alan_istatistik(array $s): array
{
    $t = time();
    $gunler = [];
    for ($d = max((int) $s['starts_at'], $t - 29 * 86400); $d <= $t; $d += 86400) $gunler[] = gun_anahtari($d);
    if (end($gunler) !== gun_anahtari($t)) $gunler[] = gun_anahtari($t);
    $satirlar = [];
    foreach (q('SELECT day, impressions, clicks FROM stats_daily WHERE slot_id = ? AND day >= ?', [$s['id'], $gunler[0]])->fetchAll() as $r) {
        $satirlar[$r['day']] = $r;
    }
    $seri = [];
    foreach ($gunler as $g) {
        $seri[] = ['day' => $g, 'impressions' => (int) ($satirlar[$g]['impressions'] ?? 0), 'clicks' => (int) ($satirlar[$g]['clicks'] ?? 0)];
    }
    $top = satir('SELECT COALESCE(SUM(impressions),0) i, COALESCE(SUM(clicks),0) k FROM stats_daily WHERE slot_id = ?', [$s['id']]);
    return ['series' => $seri, 'impressions' => (int) $top['i'], 'clicks' => (int) $top['k']];
}

// ---------------------------------------------------------------- sayfalar

function statik_sayfa(string $dosya): void
{
    guvenlik_basliklari(true);
    header('Content-Type: text/html; charset=utf-8');
    header('Cache-Control: no-cache');
    readfile(dirname(__DIR__) . '/static/' . $dosya);
    exit;
}

function yuklenen_dosya(string $ad): void
{
    if (!preg_match('/^[a-f0-9]{24}\.(webp|png|jpg|gif)$/', $ad, $m)) sayfa_yok();
    $yol = YUKLEME_DIZINI . '/' . $ad;
    if (!is_file($yol)) sayfa_yok();
    $tur = ['webp' => 'image/webp', 'png' => 'image/png', 'jpg' => 'image/jpeg', 'gif' => 'image/gif'][$m[1]];
    header('Content-Type: ' . $tur);
    header('Content-Length: ' . filesize($yol));
    header('Cache-Control: public, max-age=31536000, immutable');
    header('X-Content-Type-Options: nosniff');
    header("Content-Security-Policy: default-src 'none'");
    readfile($yol);
    exit;
}

function sablon(string $ad, array $degisken): void
{
    guvenlik_basliklari(true);
    header('Content-Type: text/html; charset=utf-8');
    extract($degisken);
    require __DIR__ . '/sablon-' . $ad . '.php';
    exit;
}

// ---------------------------------------------------------------- API: hesap

function api_ben(): void
{
    json_yanit(['user' => kullanici_json(kullanici()), 'csrf' => csrf()]);
}

function api_kayit(): void
{
    hiz_siniri('auth', 20, 600);
    $d = json_govde();
    $eposta = strtolower(trim((string) ($d['email'] ?? '')));
    $sifre = (string) ($d['password'] ?? '');
    if (!preg_match('/^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$/', $eposta) || strlen($eposta) > 160) throw new ApiHata('Geçerli bir e-posta adresi yazın.');
    if (strlen($sifre) < 8) throw new ApiHata('Şifre en az 8 karakter olmalı.');
    if (strlen($sifre) > 200) throw new ApiHata('Şifre çok uzun.');
    if (satir('SELECT 1 FROM users WHERE email = ?', [$eposta])) throw new ApiHata('Bu e-posta ile zaten bir hesap var. Giriş yapmayı deneyin.', 409);
    tx(fn() => q('INSERT INTO users(email, pw_hash, name, created_at) VALUES (?, ?, ?, ?)',
                 [$eposta, password_hash($sifre, PASSWORD_DEFAULT), metin_temizle($d['name'] ?? '', 80), time()]));
    giris_yap((int) deger('SELECT id FROM users WHERE email = ?', [$eposta]));
    json_yanit(['user' => kullanici_json(satir('SELECT * FROM users WHERE id = ?', [$_SESSION['uid']])), 'csrf' => $_SESSION['csrf']]);
}

function api_giris(): void
{
    hiz_siniri('auth', 20, 600);
    $d = json_govde();
    $u = satir('SELECT * FROM users WHERE email = ?', [strtolower(trim((string) ($d['email'] ?? '')))]);
    if (!$u || !password_verify((string) ($d['password'] ?? ''), $u['pw_hash'])) throw new ApiHata('E-posta veya şifre hatalı.', 401);
    giris_yap((int) $u['id']);
    json_yanit(['user' => kullanici_json($u), 'csrf' => $_SESSION['csrf']]);
}

function api_cikis(): void
{
    oturum_baslat();
    $_SESSION = [];
    session_regenerate_id(true);
    json_yanit(['ok' => true, 'csrf' => csrf()]);
}

// ---------------------------------------------------------------- API: pano ve sipariş

function api_pano(): void
{
    temizlik();
    $u = kullanici();
    session_write_close();
    [$reklamlar, $dolu] = pano_durumu($u ? (int) $u['id'] : null);
    json_yanit(pano_ayari(ayarlar()) + ['ads' => $reklamlar, 'taken' => $dolu, 'server_time' => time()]);
}

function api_teklif(): void
{
    $a = ayarlar();
    [$x, $y, $w, $h] = dortgen_oku(json_govde(), $a);
    temizlik();
    $mesgul = (int) deger('SELECT COUNT(*) FROM cell_locks WHERE expires_at > ? AND ' . dortgen_sql(), array_merge([time()], dortgen_arg($x, $y, $w, $h)));
    [$px, $tutar] = fiyat($w, $h, $a);
    json_yanit(['x' => $x, 'y' => $y, 'w' => $w, 'h' => $h, 'width_px' => $w * BLOCK, 'height_px' => $h * BLOCK,
                'blocks' => $w * $h, 'pixels' => $px, 'amount' => $tutar, 'price_per_pixel' => $a['price_per_pixel'],
                'duration_days' => $a['duration_days'], 'reserve_minutes' => $a['reserve_minutes'], 'available' => $mesgul === 0]);
}

function api_siparis_olustur(): void
{
    $u = giris_gerekli();
    $a = ayarlar();
    $d = json_govde();
    [$x, $y, $w, $h] = dortgen_oku($d, $a);
    $fatura = fatura_temizle($d);
    [$px, $tutar] = fiyat($w, $h, $a);
    if (isset($d['amount']) && (int) $d['amount'] !== $tutar) {
        throw new ApiHata('Fiyat değişti. Lütfen yeni fiyatı kontrol edip tekrar deneyin.', 409, ['amount' => $tutar]);
    }
    temizlik(true);
    $t = time();
    $bitis = $t + $a['reserve_minutes'] * 60;
    $ref = strtoupper(bin2hex(random_bytes(8)));
    try {
        $oid = tx(function () use ($u, $x, $y, $w, $h, $px, $tutar, $a, $fatura, $t, $bitis, $ref) {
            bekleyen_sinir((int) $u['id']);
            q('DELETE FROM cell_locks WHERE expires_at <= ?', [$t]);
            if ((int) deger('SELECT COUNT(*) FROM cell_locks WHERE ' . dortgen_sql(), dortgen_arg($x, $y, $w, $h))) {
                throw new ApiHata('Seçtiğiniz alanın bir kısmı az önce başka biri tarafından alındı veya rezerve edildi. Lütfen başka bir alan seçin.', 409);
            }
            $fj = json_encode($fatura, JSON_UNESCAPED_UNICODE);
            q("INSERT INTO orders(ref, user_id, kind, x, y, w, h, pixels, price_per_pixel, amount, duration_days, status, provider, billing, ip, created_at, expires_at)
               VALUES (?, ?, 'new', ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)",
              [$ref, $u['id'], $x, $y, $w, $h, $px, $a['price_per_pixel'], $tutar, $a['duration_days'], saglayici()->ad, $fj, istemci_ip(), $t, $bitis]);
            $oid = (int) db()->lastInsertId();
            // Birincil anahtar ihlali olursa (yarış durumu) işlem tamamen geri alınır.
            hucre_kilitle(hucreler($x, $y, $w, $h), $oid, null, $bitis);
            q('UPDATE users SET billing = ? WHERE id = ?', [$fj, $u['id']]);
            return $oid;
        });
    } catch (PDOException $e) {
        if (str_contains($e->getMessage(), 'UNIQUE') || str_contains($e->getMessage(), 'constraint')) {
            throw new ApiHata('Seçtiğiniz alan az önce başka birine ayrıldı. Lütfen başka bir alan seçin.', 409);
        }
        throw $e;
    }
    $url = odeme_baslat($oid, $u, $fatura);
    json_yanit(['ref' => $ref, 'redirect_url' => $url, 'expires_at' => $bitis, 'amount' => $tutar]);
}

function api_siparis(string $ref): void
{
    json_yanit(['order' => siparis_json(kendi_siparisim($ref))]);
}

function api_siparis_devam(string $ref): void
{
    $o = kendi_siparisim($ref);
    if ($o['status'] !== 'pending' || (int) $o['expires_at'] <= time() || !$o['provider_url']) {
        throw new ApiHata('Bu siparişin ödeme süresi doldu. Alanı yeniden seçebilirsiniz.', 410);
    }
    json_yanit(['redirect_url' => $o['provider_url']]);
}

function api_siparis_iptal(string $ref): void
{
    $o = kendi_siparisim($ref);
    tx(function () use ($o) {
        q("UPDATE orders SET status = 'cancelled' WHERE id = ? AND status = 'pending'", [$o['id']]);
        q('DELETE FROM cell_locks WHERE order_id = ? AND slot_id IS NULL', [$o['id']]);
    });
    json_yanit(['ok' => true]);
}

function api_siparis_kontrol(string $ref): void
{
    $o = kendi_siparisim($ref);
    if (in_array($o['status'], ['pending', 'expired'], true) && $o['provider'] === saglayici()->ad) saglayicidan_sonuc((int) $o['id']);
    json_yanit(['order' => siparis_json(kendi_siparisim($ref))]);
}

// ---------------------------------------------------------------- ödeme sayfaları

function iyzico_geri_donus(): void
{
    if (saglayici()->ad !== 'iyzico') sayfa_yok();
    $token = substr((string) ($_POST['token'] ?? ''), 0, 200);
    $o = $token !== '' ? satir('SELECT * FROM orders WHERE provider_token = ?', [$token]) : null;
    if (!$o) yonlendir('/reklamlarim?odeme=bulunamadi', 303);
    $r = saglayicidan_sonuc((int) $o['id']);
    yonlendir('/reklamlarim?siparis=' . rawurlencode($o['ref']) . '&sonuc=' . rawurlencode($r['state']), 303);
}

/** iyzico bildirim (webhook) adresi: tarayıcı kapansa bile sipariş tamamlanır.
 *  Gelen içerik yalnızca hangi siparişin sorgulanacağını söyler. */
function iyzico_bildirim(): void
{
    if (saglayici()->ad !== 'iyzico') sayfa_yok();
    $d = json_govde();
    $token = substr((string) ($d['token'] ?? ''), 0, 200);
    $ref = substr((string) ($d['paymentConversationId'] ?? $d['conversationId'] ?? ''), 0, 40);
    $o = $token !== '' ? satir('SELECT * FROM orders WHERE provider_token = ?', [$token]) : null;
    if (!$o && $ref !== '') $o = satir('SELECT * FROM orders WHERE ref = ?', [$ref]);
    if ($o && in_array($o['status'], ['pending', 'expired', 'failed'], true)) saglayicidan_sonuc((int) $o['id']);
    json_yanit(['ok' => true]);
}

function test_odeme(string $ref): void
{
    if (saglayici()->ad !== 'test') sayfa_yok();
    $o = satir("SELECT * FROM orders WHERE ref = ? AND provider = 'test'", [$ref]);
    if (!$o) sayfa_yok();
    if ($_SERVER['REQUEST_METHOD'] === 'POST') {
        $token = (string) ($_POST['token'] ?? '');
        if (!$o['provider_token'] || !hash_equals($o['provider_token'], $token)) {
            http_response_code(403);
            exit('Geçersiz istek');
        }
        if (($_POST['result'] ?? '') === 'success') {
            odeme_onayla((int) $o['id'], 'TEST-' . bin2hex(random_bytes(6)), (int) $o['amount']);
            yonlendir('/reklamlarim?siparis=' . rawurlencode($ref) . '&sonuc=success', 303);
        }
        odeme_basarisiz((int) $o['id'], 'Test ödemesi reddedildi');
        yonlendir('/reklamlarim?siparis=' . rawurlencode($ref) . '&sonuc=failure', 303);
    }
    $kalan = max(0, (int) $o['expires_at'] - time());
    sablon('odeme-test', ['o' => $o, 'etiket' => alan_etiketi($o), 'kalan' => $kalan,
                          'bitti' => $o['status'] !== 'pending' || $kalan <= 0]);
}

// ---------------------------------------------------------------- API: reklamlarım

function api_reklamlarim(): void
{
    $u = giris_gerekli();
    temizlik();
    $alanlar = q("SELECT * FROM slots WHERE user_id = ? AND status != 'removed' ORDER BY ends_at > ? DESC, id DESC", [$u['id'], time()])->fetchAll();
    $top = alan_toplamlari(array_map(fn($s) => (int) $s['id'], $alanlar));
    $siparisler = q('SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT 50', [$u['id']])->fetchAll();
    $a = ayarlar();
    json_yanit([
        'slots' => array_map(fn($s) => alan_json($s, $top), $alanlar),
        'orders' => array_map('siparis_json', $siparisler),
        'pricing' => ['price_per_pixel' => $a['price_per_pixel'], 'duration_days' => $a['duration_days'], 'moderation' => $a['moderation']],
        'server_time' => time(),
    ]);
}

function api_yukle(): void
{
    $u = giris_gerekli();
    hiz_siniri('upload', 40, 3600);
    $f = $_FILES['file'] ?? null;
    if (!$f || ($f['error'] ?? UPLOAD_ERR_NO_FILE) === UPLOAD_ERR_NO_FILE) throw new ApiHata('Dosya seçilmedi.');
    if (in_array($f['error'], [UPLOAD_ERR_INI_SIZE, UPLOAD_ERR_FORM_SIZE], true) || $f['size'] > 5 * 1024 * 1024) {
        throw new ApiHata('Dosya çok büyük (en fazla 5 MB).', 413);
    }
    if ($f['error'] !== UPLOAD_ERR_OK || !is_uploaded_file($f['tmp_name'])) throw new ApiHata('Dosya yüklenemedi, tekrar deneyin.');
    $veri = (string) file_get_contents($f['tmp_name']);
    $bilgi = @getimagesizefromstring($veri);
    $turler = ['image/png' => 'png', 'image/jpeg' => 'jpg', 'image/webp' => 'webp', 'image/gif' => 'gif'];
    if (!$bilgi || !isset($turler[$bilgi['mime']])) throw new ApiHata('Bu dosya geçerli bir görsel değil. PNG, JPG, WEBP veya GIF yükleyin.');
    [$gen, $yuk] = [(int) $bilgi[0], (int) $bilgi[1]];
    if ($gen < 1 || $yuk < 1 || $gen * $yuk > 40000000) throw new ApiHata('Görsel çok büyük (en fazla 40 megapiksel).');
    $ad = bin2hex(random_bytes(12));
    $hareketli = $bilgi['mime'] === 'image/gif' && preg_match_all('#\x00\x21\xF9\x04.{4}\x00[\x2C\x21]#s', $veri) > 1;
    if ($hareketli) {
        if ($gen * $yuk > 2400 * 1500) throw new ApiHata('Hareketli GIF en fazla 2400×1500 piksel olabilir.');
        $dosya = $ad . '.gif';
        file_put_contents(YUKLEME_DIZINI . '/' . $dosya, $veri);
    } else {
        // Görsel her zaman yeniden kodlanır: içine gizlenmiş kod veya meta veri taşınmaz.
        @ini_set('memory_limit', '256M');
        $img = @imagecreatefromstring($veri);
        if (!$img) throw new ApiHata('Görsel açılamadı. PNG veya JPG olarak kaydedip tekrar deneyin.');
        if (!imageistruecolor($img)) imagepalettetotruecolor($img);
        if ($bilgi['mime'] === 'image/jpeg' && function_exists('exif_read_data')) {
            $exif = @exif_read_data('data://image/jpeg;base64,' . base64_encode($veri));
            $acilar = [3 => 180, 6 => -90, 8 => 90];
            if (!empty($exif['Orientation']) && isset($acilar[$exif['Orientation']])) {
                $img = imagerotate($img, $acilar[$exif['Orientation']], 0);
            }
        }
        $gen = imagesx($img);
        $yuk = imagesy($img);
        $oran = min(1, 2400 / max($gen, $yuk));
        if ($oran < 1) {
            $yg = max(1, (int) round($gen * $oran));
            $yy = max(1, (int) round($yuk * $oran));
            $yeni = imagecreatetruecolor($yg, $yy);
            imagealphablending($yeni, false);
            imagesavealpha($yeni, true);
            imagecopyresampled($yeni, $img, 0, 0, 0, 0, $yg, $yy, $gen, $yuk);
            imagedestroy($img);
            $img = $yeni;
            [$gen, $yuk] = [$yg, $yy];
        }
        imagealphablending($img, false);
        imagesavealpha($img, true);
        if (function_exists('imagewebp')) {
            $dosya = $ad . '.webp';
            $ok = imagewebp($img, YUKLEME_DIZINI . '/' . $dosya, 88);
        } else {
            $dosya = $ad . '.png';
            $ok = imagepng($img, YUKLEME_DIZINI . '/' . $dosya, 6);
        }
        imagedestroy($img);
        if (!$ok) throw new ApiHata('Görsel kaydedilemedi (sunucu klasör izni).', 500);
    }
    tx(fn() => q('INSERT INTO uploads(user_id, filename, width, height, created_at) VALUES (?, ?, ?, ?, ?)',
                 [$u['id'], $dosya, $gen, $yuk, time()]));
    json_yanit(['image' => $dosya, 'image_url' => gorsel_url($dosya), 'width' => $gen, 'height' => $yuk]);
}

function api_yayinla(int $sid): void
{
    $u = giris_gerekli();
    $s = kendi_alanim($sid);
    if (!in_array($s['status'], ['active', 'suspended'], true) || (int) $s['ends_at'] <= time()) throw new ApiHata('Bu alanın yayın süresi bitmiş.', 410);
    $c = icerik_temizle(json_govde(), (int) $u['id'], $s);
    if ($c['image'] === '') throw new ApiHata('Yayınlamak için bir görsel yükleyin.');
    if ($c['url'] === '') throw new ApiHata('Butonun gideceği bağlantıyı yazın.');
    $j = json_encode($c, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    $onay = ayarlar()['moderation'];
    tx(function () use ($j, $sid, $onay) {
        if ($onay) q("UPDATE slots SET draft = ?, review = 'pending', review_note = NULL WHERE id = ?", [$j, $sid]);
        else q('UPDATE slots SET content = ?, draft = NULL, review = NULL, review_note = NULL, published_at = ? WHERE id = ?', [$j, time(), $sid]);
    });
    json_yanit(['slot' => alan_json(kendi_alanim($sid), alan_toplamlari([$sid])), 'moderation' => $onay]);
}

function api_alan_istatistik(int $sid): void
{
    json_yanit(alan_istatistik(kendi_alanim($sid)));
}

function api_sure_uzat(int $sid): void
{
    $u = giris_gerekli();
    $s = kendi_alanim($sid);
    if ($s['status'] !== 'active' || (int) $s['ends_at'] <= time()) throw new ApiHata('Yalnızca yayında olan alanların süresi uzatılabilir.', 409);
    $fatura = fatura_temizle(json_govde());
    $a = ayarlar();
    [$px, $tutar] = fiyat((int) $s['w'], (int) $s['h'], $a);
    $t = time();
    $ref = strtoupper(bin2hex(random_bytes(8)));
    $oid = tx(function () use ($u, $s, $px, $tutar, $a, $fatura, $t, $ref) {
        bekleyen_sinir((int) $u['id']);
        $fj = json_encode($fatura, JSON_UNESCAPED_UNICODE);
        q("INSERT INTO orders(ref, user_id, kind, slot_id, x, y, w, h, pixels, price_per_pixel, amount, duration_days, status, provider, billing, ip, created_at, expires_at)
           VALUES (?, ?, 'renew', ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)",
          [$ref, $u['id'], $s['id'], $s['x'], $s['y'], $s['w'], $s['h'], $px, $a['price_per_pixel'], $tutar, $a['duration_days'],
           saglayici()->ad, $fj, istemci_ip(), $t, $t + max($a['reserve_minutes'], 30) * 60]);
        $oid = (int) db()->lastInsertId();
        q('UPDATE users SET billing = ? WHERE id = ?', [$fj, $u['id']]);
        return $oid;
    });
    json_yanit(['ref' => $ref, 'redirect_url' => odeme_baslat($oid, $u, $fatura), 'amount' => $tutar]);
}

// ---------------------------------------------------------------- gösterim / tıklama

function api_takip(): void
{
    if (bot_mu()) json_yanit(['ok' => true]);
    $d = json_govde();
    $ids = [];
    foreach (array_slice((array) ($d['ids'] ?? []), 0, 300) as $i) if (is_numeric($i)) $ids[(int) $i] = true;
    $ids = array_keys($ids);
    if (!$ids) json_yanit(['ok' => true]);
    $kim = ziyaretci_izi(substr((string) preg_replace('/[^a-zA-Z0-9_-]/', '', (string) ($d['v'] ?? '')), 0, 40));
    $t = time();
    $gun = gun_anahtari($t);
    tx(function () use ($ids, $kim, $t, $gun) {
        $yer = implode(',', array_fill(0, count($ids), '?'));
        $canli = q("SELECT id FROM slots WHERE id IN ($yer) AND status = 'active' AND ends_at > ?", array_merge($ids, [$t]))->fetchAll(PDO::FETCH_COLUMN);
        $ekle = db()->prepare('INSERT OR IGNORE INTO seen(k, expires_at) VALUES (?, ?)');
        $say = db()->prepare('INSERT INTO stats_daily(slot_id, day, impressions) VALUES (?, ?, 1) '
                           . 'ON CONFLICT(slot_id, day) DO UPDATE SET impressions = impressions + 1');
        foreach ($canli as $sid) {
            bagla($ekle, ['i:' . $sid . ':' . $kim, $t + IMPRESSION_WINDOW]);
            if ($ekle->rowCount()) bagla($say, [(int) $sid, $gun]);
        }
    });
    json_yanit(['ok' => true]);
}

function tiklama(int $sid): void
{
    $t = time();
    $s = satir("SELECT * FROM slots WHERE id = ? AND status = 'active' AND ends_at > ?", [$sid, $t]);
    $c = ($s && $s['content']) ? json_decode($s['content'], true) : null;
    if (!$c || empty($c['url'])) yonlendir('/');
    if (!bot_mu()) {
        tx(function () use ($sid, $t) {
            $st = q('INSERT OR IGNORE INTO seen(k, expires_at) VALUES (?, ?)', ['c:' . $sid . ':' . ziyaretci_izi(), $t + CLICK_WINDOW]);
            if ($st->rowCount()) {
                q('INSERT INTO stats_daily(slot_id, day, clicks) VALUES (?, ?, 1) ON CONFLICT(slot_id, day) DO UPDATE SET clicks = clicks + 1',
                  [$sid, gun_anahtari($t)]);
            }
        });
    }
    header('Referrer-Policy: origin');
    yonlendir($c['url']);
}

// ---------------------------------------------------------------- API: yönetim

function api_yonetim_ozet(): void
{
    yonetici_gerekli();
    temizlik(true);
    $t = time();
    $a = ayarlar();
    $gelir = satir("SELECT COALESCE(SUM(amount),0) s, COUNT(*) n FROM orders WHERE status = 'paid'");
    $gelir30 = (int) deger("SELECT COALESCE(SUM(amount),0) FROM orders WHERE status = 'paid' AND paid_at >= ?", [$t - 30 * 86400]);
    $satilan = (int) deger('SELECT COUNT(*) FROM cell_locks WHERE slot_id IS NOT NULL AND expires_at > ?', [$t]);
    $rezerve = (int) deger('SELECT COUNT(*) FROM cell_locks WHERE slot_id IS NULL AND expires_at > ?', [$t]);
    $tot = satir('SELECT COALESCE(SUM(impressions),0) i, COALESCE(SUM(clicks),0) k FROM stats_daily');
    $siparisler = q('SELECT o.*, u.email FROM orders o JOIN users u ON u.id = o.user_id ORDER BY o.id DESC LIMIT 300')->fetchAll();
    $alanlar = q("SELECT s.*, u.email FROM slots s JOIN users u ON u.id = s.user_id WHERE s.status != 'removed'
                  ORDER BY (s.review = 'pending') DESC, s.ends_at > ? DESC, s.id DESC", [$t])->fetchAll();
    $top = alan_toplamlari(array_map(fn($s) => (int) $s['id'], $alanlar));
    $p = saglayici();
    [$reklamlar, $dolu] = pano_durumu();
    json_yanit([
        'settings' => $a,
        'payment' => ['provider' => $p->ad, 'live' => $p->canli, 'label' => $p->etiket,
                      'callback_url' => site_adresi() . '/odeme/iyzico/geri-donus', 'webhook_url' => site_adresi() . '/odeme/iyzico/bildirim'],
        'board' => ['width' => BOARD_W, 'height' => BOARD_H, 'block' => BLOCK, 'cols' => COLS, 'rows' => ROWS],
        'totals' => [
            'revenue' => (int) $gelir['s'], 'paid_orders' => (int) $gelir['n'], 'revenue_30d' => $gelir30,
            'sold_blocks' => $satilan, 'reserved_blocks' => $rezerve, 'total_blocks' => COLS * ROWS,
            'impressions' => (int) $tot['i'], 'clicks' => (int) $tot['k'],
            'active_slots' => count(array_filter($alanlar, fn($s) => $s['status'] === 'active' && (int) $s['ends_at'] > $t)),
            'pending_review' => count(array_filter($alanlar, fn($s) => $s['review'] === 'pending')),
            'refund_needed' => count(array_filter($siparisler, fn($o) => $o['status'] === 'refund_needed')),
            'demo_slots' => count(array_filter($alanlar, fn($s) => (int) $s['is_demo'])),
        ],
        'orders' => array_map(function ($o) {
            return siparis_json($o) + ['email' => $o['email'], 'provider_payment_id' => $o['provider_payment_id'],
                                       'billing' => $o['billing'] ? json_decode($o['billing'], true) : null];
        }, $siparisler),
        'slots' => array_map(fn($s) => alan_json($s, $top) + ['email' => $s['email']], $alanlar),
        'ads' => $reklamlar, 'taken' => $dolu, 'server_time' => $t,
    ]);
}

function api_yonetim_ayarlar(): void
{
    yonetici_gerekli();
    $d = json_govde();
    $yeni = [];
    $tam = function (string $k, int $alt, int $ust, string $etiket) use ($d, &$yeni) {
        if (!array_key_exists($k, $d)) return;
        if (!is_numeric($d[$k]) || (int) $d[$k] != $d[$k]) throw new ApiHata($etiket . ' tam sayı olmalı.');
        $v = (int) $d[$k];
        if ($v < $alt || $v > $ust) throw new ApiHata("$etiket $alt ile $ust arasında olmalı.");
        $yeni[$k] = $v;
    };
    $tam('price_per_pixel', 1, 10000000, 'Piksel fiyatı (kuruş)');
    $tam('duration_days', 1, 3650, 'Yayın süresi (gün)');
    $tam('reserve_minutes', 5, 120, 'Rezervasyon süresi (dakika)');
    $tam('min_blocks', 1, COLS * ROWS, 'En az blok');
    $tam('max_blocks', 0, COLS * ROWS, 'En fazla blok');
    if (array_key_exists('moderation', $d)) $yeni['moderation'] = $d['moderation'] ? '1' : '0';
    if (array_key_exists('legal_text', $d)) $yeni['legal_text'] = mb_substr((string) $d['legal_text'], 0, 30000);
    $birlesik = array_merge(ayarlar(), array_intersect_key($yeni, ['min_blocks' => 1, 'max_blocks' => 1]));
    if ($birlesik['max_blocks'] && $birlesik['max_blocks'] < $birlesik['min_blocks']) throw new ApiHata('En fazla blok, en az bloktan küçük olamaz.');
    tx(fn() => ayar_kaydet($yeni));
    json_yanit(['settings' => ayarlar()]);
}

function api_yonetim_alan(int $sid, string $islem): void
{
    yonetici_gerekli();
    $s = satir('SELECT * FROM slots WHERE id = ?', [$sid]);
    if (!$s) throw new ApiHata('Alan bulunamadı.', 404);
    $not = metin_temizle(json_govde()['note'] ?? '', 300) ?: null;
    tx(function () use ($sid, $islem, $s, $not) {
        switch ($islem) {
            case 'suspend':
                q("UPDATE slots SET status = 'suspended', admin_note = ? WHERE id = ? AND status = 'active'", [$not, $sid]);
                break;
            case 'unsuspend':
                q("UPDATE slots SET status = 'active', admin_note = NULL WHERE id = ? AND status = 'suspended'", [$sid]);
                break;
            case 'approve':
                if (!$s['draft']) throw new ApiHata('Onay bekleyen içerik yok.');
                q('UPDATE slots SET content = draft, draft = NULL, review = NULL, review_note = NULL, published_at = ? WHERE id = ?', [time(), $sid]);
                break;
            case 'reject':
                q("UPDATE slots SET review = 'rejected', review_note = ? WHERE id = ?", [$not ?: 'İçerik kurallara uygun bulunmadı.', $sid]);
                break;
            case 'remove':
                q("UPDATE slots SET status = 'removed', admin_note = ? WHERE id = ?", [$not, $sid]);
                q('DELETE FROM cell_locks WHERE slot_id = ?', [$sid]);
                break;
            default:
                throw new ApiHata('Bilinmeyen işlem.', 404);
        }
    });
    json_yanit(['ok' => true]);
}

function api_yonetim_siparis(string $ref, string $islem): void
{
    yonetici_gerekli();
    $o = satir('SELECT * FROM orders WHERE ref = ?', [$ref]);
    if (!$o) throw new ApiHata('Sipariş bulunamadı.', 404);
    if ($islem === 'check') {
        if ($o['provider'] !== saglayici()->ad) throw new ApiHata('Bu sipariş başka bir ödeme sağlayıcısıyla açılmış.');
        json_yanit(['result' => saglayicidan_sonuc((int) $o['id'])]);
    }
    if ($islem === 'refunded') {
        tx(fn() => q("UPDATE orders SET status = 'refunded', note = 'Yönetici iadeyi tamamladı' WHERE id = ? AND status = 'refund_needed'", [$o['id']]));
        json_yanit(['ok' => true]);
    }
    if ($islem === 'cancel') {
        tx(function () use ($o) {
            q("UPDATE orders SET status = 'cancelled', note = 'Yönetici iptal etti' WHERE id = ? AND status = 'pending'", [$o['id']]);
            q('DELETE FROM cell_locks WHERE order_id = ? AND slot_id IS NULL', [$o['id']]);
        });
        json_yanit(['ok' => true]);
    }
    throw new ApiHata('Bilinmeyen işlem.', 404);
}

function api_yonetim_demo(string $islem): void
{
    yonetici_gerekli();
    if ($islem === 'load') {
        require_once __DIR__ . '/demo.php';
        json_yanit(['added' => demo_yukle()]);
    }
    if ($islem === 'remove') {
        $n = tx(function () {
            $ids = q("SELECT id FROM slots WHERE is_demo = 1 AND status != 'removed'")->fetchAll(PDO::FETCH_COLUMN);
            foreach ($ids as $sid) {
                q("UPDATE slots SET status = 'removed', admin_note = 'Demo kaldırıldı' WHERE id = ?", [$sid]);
                q('DELETE FROM cell_locks WHERE slot_id = ?', [$sid]);
            }
            return count($ids);
        });
        json_yanit(['removed' => $n]);
    }
    throw new ApiHata('Bilinmeyen işlem.', 404);
}

// ---------------------------------------------------------------- yönlendirici

function yonlendirici(): void
{
    $yol = rawurldecode((string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH));
    $yontem = $_SERVER['REQUEST_METHOD'] ?? 'GET';

    if (str_starts_with($yol, '/api/') && $yontem === 'POST' && $yol !== '/api/track') csrf_dogrula();

    $rotalar = [
        ['GET', '#^/$#', fn() => statik_sayfa('index.html')],
        ['GET', '#^/reklamlarim/?$#', fn() => statik_sayfa('panel.html')],
        ['GET', '#^/yonetim/?$#', fn() => statik_sayfa('admin.html')],
        ['GET', '#^/yasal/?$#', fn() => sablon('yasal', ['metin' => ayarlar()['legal_text']])],
        ['GET', '#^/u/([^/]+)$#', fn($m) => yuklenen_dosya($m[1])],
        ['GET', '#^/r/(\d+)$#', fn($m) => tiklama((int) $m[1])],
        ['GET', '#^/api/me$#', fn() => api_ben()],
        ['POST', '#^/api/auth/register$#', fn() => api_kayit()],
        ['POST', '#^/api/auth/login$#', fn() => api_giris()],
        ['POST', '#^/api/auth/logout$#', fn() => api_cikis()],
        ['GET', '#^/api/board$#', fn() => api_pano()],
        ['POST', '#^/api/quote$#', fn() => api_teklif()],
        ['POST', '#^/api/orders$#', fn() => api_siparis_olustur()],
        ['GET', '#^/api/orders/([A-Z0-9]{8,40})$#', fn($m) => api_siparis($m[1])],
        ['POST', '#^/api/orders/([A-Z0-9]{8,40})/resume$#', fn($m) => api_siparis_devam($m[1])],
        ['POST', '#^/api/orders/([A-Z0-9]{8,40})/cancel$#', fn($m) => api_siparis_iptal($m[1])],
        ['POST', '#^/api/orders/([A-Z0-9]{8,40})/check$#', fn($m) => api_siparis_kontrol($m[1])],
        ['GET', '#^/api/my$#', fn() => api_reklamlarim()],
        ['POST', '#^/api/upload$#', fn() => api_yukle()],
        ['POST', '#^/api/slots/(\d+)/publish$#', fn($m) => api_yayinla((int) $m[1])],
        ['GET', '#^/api/slots/(\d+)/stats$#', fn($m) => api_alan_istatistik((int) $m[1])],
        ['POST', '#^/api/slots/(\d+)/renew$#', fn($m) => api_sure_uzat((int) $m[1])],
        ['POST', '#^/api/track$#', fn() => api_takip()],
        ['GET', '#^/api/admin/overview$#', fn() => api_yonetim_ozet()],
        ['POST', '#^/api/admin/settings$#', fn() => api_yonetim_ayarlar()],
        ['POST', '#^/api/admin/slots/(\d+)/([a-z]+)$#', fn($m) => api_yonetim_alan((int) $m[1], $m[2])],
        ['POST', '#^/api/admin/orders/([A-Z0-9]{8,40})/([a-z]+)$#', fn($m) => api_yonetim_siparis($m[1], $m[2])],
        ['POST', '#^/api/admin/demo/([a-z]+)$#', fn($m) => api_yonetim_demo($m[1])],
        ['POST', '#^/odeme/iyzico/geri-donus$#', fn() => iyzico_geri_donus()],
        ['POST', '#^/odeme/iyzico/bildirim$#', fn() => iyzico_bildirim()],
        ['GET', '#^/odeme/test/([A-Z0-9]{8,40})$#', fn($m) => test_odeme($m[1])],
        ['POST', '#^/odeme/test/([A-Z0-9]{8,40})$#', fn($m) => test_odeme($m[1])],
    ];
    $yol_var = false;
    foreach ($rotalar as [$y, $desen, $isleyici]) {
        if (!preg_match($desen, $yol, $m)) continue;
        $yol_var = true;
        if ($y === $yontem || ($y === 'GET' && $yontem === 'HEAD')) {
            $isleyici($m);
            return;
        }
    }
    if (str_starts_with($yol, '/api/')) throw new ApiHata($yol_var ? 'Bu yöntem desteklenmiyor.' : 'Bulunamadı.', $yol_var ? 405 : 404);
    sayfa_yok();
}
