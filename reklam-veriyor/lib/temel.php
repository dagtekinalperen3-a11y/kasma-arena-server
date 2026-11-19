<?php
/* Reklam Veriyor — çekirdek: ayarlar, veritabanı, oturum, yardımcılar */
declare(strict_types=1);

const RV_SURUM = '1.0';

final class ApiHata extends Exception
{
    public int $durum;
    public array $ek;

    public function __construct(string $mesaj, int $durum = 400, array $ek = [])
    {
        parent::__construct($mesaj);
        $this->durum = $durum;
        $this->ek = $ek;
    }
}

// ---------------------------------------------------------------- ayarlar

$GLOBALS['RV_CFG'] = require dirname(__DIR__) . '/ayarlar.php';
foreach (['RV_VERI_DIZINI' => 'veri_dizini', 'RV_ODEME' => 'odeme_saglayici', 'RV_YONETICI_EPOSTA' => 'yonetici_eposta',
          'RV_YONETICI_SIFRE' => 'yonetici_sifre', 'RV_SITE_ADRESI' => 'site_adresi'] as $env => $key) {
    $v = getenv($env);
    if ($v !== false && $v !== '') $GLOBALS['RV_CFG'][$key] = $v;   // testler ve gelişmiş kurulum için
}

function cfg(string $k, $varsayilan = null)
{
    $v = $GLOBALS['RV_CFG'][$k] ?? null;
    return ($v === null || $v === '') ? $varsayilan : $v;
}

define('VERI', rtrim((string) cfg('veri_dizini', dirname(__DIR__) . '/veri'), '/'));
define('YUKLEME_DIZINI', VERI . '/yuklemeler');
define('BOARD_W', (int) cfg('pano_genislik', 1200));
define('BOARD_H', (int) cfg('pano_yukseklik', 750));
define('BLOCK', (int) cfg('blok', 15));
define('COLS', intdiv(BOARD_W, BLOCK));
define('ROWS', intdiv(BOARD_H, BLOCK));
define('BLOCK_PX', BLOCK * BLOCK);
const MAX_PENDING_PER_USER = 3;
const MAX_PENDING_PER_IP = 6;
const IMPRESSION_WINDOW = 1800;   // aynı ziyaretçi aynı reklamı 30 dk'da bir kez sayılır
const CLICK_WINDOW = 30;          // art arda tıklamalar 30 sn'de bir kez sayılır
const TZ_OFFSET = 10800;          // Türkiye saati (UTC+3)

function kurulum_kontrol(): array
{
    $sorunlar = [];
    if (PHP_VERSION_ID < 80000) $sorunlar[] = 'PHP 8.0 veya üstü gerekli (şu an ' . PHP_VERSION . '). Hosting panelinden PHP sürümünü yükseltin.';
    if (!extension_loaded('pdo_sqlite')) $sorunlar[] = 'PHP "pdo_sqlite" eklentisi kapalı. Hosting panelinde PHP eklentilerinden açın.';
    if (!extension_loaded('gd')) $sorunlar[] = 'PHP "gd" eklentisi kapalı (görsel yükleme için gerekli).';
    if (cfg('odeme_saglayici') === 'iyzico' && !extension_loaded('curl')) $sorunlar[] = 'PHP "curl" eklentisi kapalı (iyzico için gerekli).';
    if (BOARD_W % BLOCK || BOARD_H % BLOCK) $sorunlar[] = 'Pano genişliği ve yüksekliği blok ölçüsünün katı olmalı (ayarlar.php).';
    foreach ([VERI, YUKLEME_DIZINI, VERI . '/oturumlar'] as $d) {
        if (!is_dir($d) && !@mkdir($d, 0750, true)) {
            $sorunlar[] = 'Klasör oluşturulamadı: ' . $d;
        } elseif (!is_writable($d)) {
            $sorunlar[] = 'Klasöre yazılamıyor: ' . $d . ' (izinleri 755 yapın).';
        }
    }
    return $sorunlar;
}

function koru_dizin(string $d): void
{
    if (!is_file($d . '/.htaccess')) {
        @file_put_contents($d . '/.htaccess', "<IfModule mod_authz_core.c>\n  Require all denied\n</IfModule>\n"
            . "<IfModule !mod_authz_core.c>\n  Order allow,deny\n  Deny from all\n</IfModule>\n");
    }
    if (!is_file($d . '/index.html')) @file_put_contents($d . '/index.html', '');
}

/** Gizli değerleri .php dosyasında saklar: dosya tarayıcıdan açılsa bile içerik görünmez. */
function kalici_gizli(string $ad, callable $uret): string
{
    $yol = VERI . '/' . $ad . '.php';
    if (is_file($yol)) {
        $v = include $yol;
        if (is_string($v) && $v !== '') return $v;
    }
    $v = $uret();
    file_put_contents($yol, "<?php\nreturn " . var_export($v, true) . ";\n", LOCK_EX);
    return $v;
}

function gizli_anahtar(): string
{
    static $k = null;
    return $k ??= kalici_gizli('gizli-anahtar', fn() => bin2hex(random_bytes(32)));
}

// ---------------------------------------------------------------- veritabanı

const SEMA = <<<'SQL'
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY, email TEXT NOT NULL UNIQUE COLLATE NOCASE, pw_hash TEXT NOT NULL,
    name TEXT NOT NULL DEFAULT '', is_admin INTEGER NOT NULL DEFAULT 0, billing TEXT, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY, ref TEXT NOT NULL UNIQUE, user_id INTEGER NOT NULL REFERENCES users(id),
    kind TEXT NOT NULL DEFAULT 'new', slot_id INTEGER,
    x INTEGER NOT NULL, y INTEGER NOT NULL, w INTEGER NOT NULL, h INTEGER NOT NULL,
    pixels INTEGER NOT NULL, price_per_pixel INTEGER NOT NULL, amount INTEGER NOT NULL, duration_days INTEGER NOT NULL,
    status TEXT NOT NULL, provider TEXT NOT NULL, provider_token TEXT, provider_url TEXT, provider_payment_id TEXT,
    billing TEXT, ip TEXT, note TEXT, created_at INTEGER NOT NULL, expires_at INTEGER NOT NULL, paid_at INTEGER
);
CREATE INDEX IF NOT EXISTS orders_user ON orders(user_id);
CREATE INDEX IF NOT EXISTS orders_status ON orders(status, expires_at);
CREATE INDEX IF NOT EXISTS orders_token ON orders(provider_token);
CREATE TABLE IF NOT EXISTS slots (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), order_id INTEGER,
    x INTEGER NOT NULL, y INTEGER NOT NULL, w INTEGER NOT NULL, h INTEGER NOT NULL,
    starts_at INTEGER NOT NULL, ends_at INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'active',
    content TEXT, draft TEXT, review TEXT, review_note TEXT, admin_note TEXT, published_at INTEGER,
    is_demo INTEGER NOT NULL DEFAULT 0, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS slots_user ON slots(user_id);
CREATE INDEX IF NOT EXISTS slots_status ON slots(status, ends_at);
-- Aynı bloğun iki kez satılamaması burada garanti edilir: cell birincil anahtardır.
CREATE TABLE IF NOT EXISTS cell_locks (
    cell INTEGER PRIMARY KEY, order_id INTEGER, slot_id INTEGER, expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS cell_locks_order ON cell_locks(order_id);
CREATE INDEX IF NOT EXISTS cell_locks_slot ON cell_locks(slot_id);
CREATE INDEX IF NOT EXISTS cell_locks_exp ON cell_locks(expires_at);
CREATE TABLE IF NOT EXISTS uploads (
    id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, filename TEXT NOT NULL UNIQUE,
    width INTEGER, height INTEGER, created_at INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS stats_daily (
    slot_id INTEGER NOT NULL, day TEXT NOT NULL, impressions INTEGER NOT NULL DEFAULT 0,
    clicks INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (slot_id, day)
);
CREATE TABLE IF NOT EXISTS seen (k TEXT PRIMARY KEY, expires_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS seen_exp ON seen(expires_at);
CREATE TABLE IF NOT EXISTS rate_log (bucket TEXT NOT NULL, ip TEXT NOT NULL, t INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS rate_log_idx ON rate_log(bucket, ip, t);
SQL;

function varsayilan_ayarlar(): array
{
    return [
        'price_per_pixel' => '50',     // kuruş / piksel (0,50 TL)
        'duration_days' => '30',
        'reserve_minutes' => '15',
        'min_blocks' => '1',
        'max_blocks' => '800',
        'moderation' => '0',
        'legal_text' => (string) file_get_contents(__DIR__ . '/yasal-sablon.txt'),
    ];
}

function db(): PDO
{
    static $pdo = null;
    if ($pdo) return $pdo;
    $ad = kalici_gizli('veritabani-adi', fn() => 'rv-' . bin2hex(random_bytes(8)) . '.sqlite');
    $pdo = new PDO('sqlite:' . VERI . '/' . $ad, null, null, [
        PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
        PDO::ATTR_TIMEOUT => 20,
        PDO::ATTR_STRINGIFY_FETCHES => false,
    ]);
    $pdo->exec('PRAGMA busy_timeout = 20000');
    $pdo->exec('PRAGMA foreign_keys = ON');
    if ((int) $pdo->query('PRAGMA user_version')->fetchColumn() < 1) {
        $pdo->exec('BEGIN IMMEDIATE');
        $pdo->exec(SEMA);
        $st = $pdo->prepare('INSERT OR IGNORE INTO settings(key, value) VALUES (?, ?)');
        foreach (varsayilan_ayarlar() as $k => $v) $st->execute([$k, $v]);
        $pdo->exec('PRAGMA user_version = 1');
        $pdo->exec('COMMIT');
    }
    return $pdo;
}

/** Parametreler türüyle bağlanır: SQLite, metin olarak gelen sayıyı bir hesaplamayla
 *  (ör. cell / 80) karşılaştırırken dönüştürmez; tam sayılar mutlaka PARAM_INT olmalı. */
function bagla(PDOStatement $st, array $p): PDOStatement
{
    $i = 1;
    foreach ($p as $v) {
        $tur = is_int($v) ? PDO::PARAM_INT : (is_bool($v) ? PDO::PARAM_BOOL : ($v === null ? PDO::PARAM_NULL : PDO::PARAM_STR));
        $st->bindValue($i++, $v, $tur);
    }
    $st->execute();
    return $st;
}

function q(string $sql, array $p = []): PDOStatement
{
    return bagla(db()->prepare($sql), $p);
}

function satir(string $sql, array $p = []): ?array
{
    $r = q($sql, $p)->fetch();
    return $r === false ? null : $r;
}

function deger(string $sql, array $p = [])
{
    return q($sql, $p)->fetchColumn();
}

/** Yazma kilidini hemen alan işlem: aynı anda gelen rezervasyonlar sıraya girer. */
function tx(callable $fn)
{
    db()->exec('BEGIN IMMEDIATE');
    try {
        $r = $fn();
        db()->exec('COMMIT');
        return $r;
    } catch (Throwable $e) {
        db()->exec('ROLLBACK');
        throw $e;
    }
}

function ayarlar(): array
{
    $ham = varsayilan_ayarlar();
    foreach (q('SELECT key, value FROM settings')->fetchAll() as $r) $ham[$r['key']] = $r['value'];
    return [
        'price_per_pixel' => (int) $ham['price_per_pixel'],
        'duration_days' => (int) $ham['duration_days'],
        'reserve_minutes' => (int) $ham['reserve_minutes'],
        'min_blocks' => (int) $ham['min_blocks'],
        'max_blocks' => (int) $ham['max_blocks'],
        'moderation' => $ham['moderation'] === '1',
        'legal_text' => $ham['legal_text'],
    ];
}

function ayar_kaydet(array $degerler): void
{
    foreach ($degerler as $k => $v) {
        q('INSERT INTO settings(key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value', [$k, (string) $v]);
    }
}

/** ayarlar.php'deki yönetici hesabını veritabanına işler (yalnızca değiştiğinde). */
function yonetici_hazirla(): void
{
    $e = strtolower(trim((string) cfg('yonetici_eposta', '')));
    $s = (string) cfg('yonetici_sifre', '');
    if ($e === '' || strlen($s) < 8) return;
    $iz = hash('sha256', $e . '|' . $s . '|' . gizli_anahtar());
    if (deger("SELECT value FROM settings WHERE key = 'admin_cfg'") === $iz) return;
    tx(function () use ($e, $s, $iz) {
        $u = satir('SELECT * FROM users WHERE email = ?', [$e]);
        if (!$u) {
            q('INSERT INTO users(email, pw_hash, name, is_admin, created_at) VALUES (?, ?, ?, 1, ?)',
              [$e, password_hash($s, PASSWORD_DEFAULT), 'Site Yöneticisi', time()]);
        } else {
            q('UPDATE users SET pw_hash = ?, is_admin = 1 WHERE id = ?', [password_hash($s, PASSWORD_DEFAULT), $u['id']]);
        }
        ayar_kaydet(['admin_cfg' => $iz]);
    });
}

// ---------------------------------------------------------------- istek / yanıt

function https_mi(): bool
{
    if (!empty($_SERVER['HTTPS']) && $_SERVER['HTTPS'] !== 'off') return true;
    if (($_SERVER['HTTP_X_FORWARDED_PROTO'] ?? '') === 'https') return true;
    return str_starts_with((string) cfg('site_adresi', ''), 'https://');
}

function site_adresi(): string
{
    $a = rtrim((string) cfg('site_adresi', ''), '/');
    if ($a !== '') return $a;
    return (https_mi() ? 'https' : 'http') . '://' . ($_SERVER['HTTP_HOST'] ?? 'localhost');
}

function istemci_ip(): string
{
    return substr((string) ($_SERVER['REMOTE_ADDR'] ?? ''), 0, 64);
}

function json_govde(): array
{
    static $g = null;
    if ($g === null) {
        $g = json_decode((string) file_get_contents('php://input'), true);
        if (!is_array($g)) $g = [];
    }
    return $g;
}

function json_yanit($veri, int $durum = 200): void
{
    http_response_code($durum);
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store');
    echo json_encode($veri, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function guvenlik_basliklari(bool $html): void
{
    header('X-Content-Type-Options: nosniff');
    header('Referrer-Policy: strict-origin-when-cross-origin');
    if ($html) {
        header("Content-Security-Policy: default-src 'self'; img-src 'self' data: blob:; style-src 'self' 'unsafe-inline'; "
            . "script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'");
        header('X-Frame-Options: DENY');
    }
}

function yonlendir(string $adres, int $kod = 302): void
{
    header('Location: ' . $adres, true, $kod);
    header('Cache-Control: no-store');
    exit;
}

function sayfa_yok(): void
{
    http_response_code(404);
    header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><meta charset="utf-8"><title>Bulunamadı</title><p style="font-family:sans-serif">Sayfa bulunamadı. <a href="/">Panoya dön</a></p>';
    exit;
}

function hiz_siniri(string $kova, int $limit, int $saniye): void
{
    $ip = istemci_ip();
    $t = time();
    $n = (int) deger('SELECT COUNT(*) FROM rate_log WHERE bucket = ? AND ip = ? AND t > ?', [$kova, $ip, $t - $saniye]);
    if ($n >= $limit) throw new ApiHata('Çok fazla deneme yaptınız, biraz sonra tekrar deneyin.', 429);
    q('INSERT INTO rate_log(bucket, ip, t) VALUES (?, ?, ?)', [$kova, $ip, $t]);
}

function bot_mu(): bool
{
    return (bool) preg_match('/bot|crawl|spider|slurp|preview|facebookexternalhit|headless/i', $_SERVER['HTTP_USER_AGENT'] ?? '');
}

function ziyaretci_izi(string $ek = ''): string
{
    $taban = istemci_ip() . '|' . substr((string) ($_SERVER['HTTP_USER_AGENT'] ?? ''), 0, 200) . '|' . $ek;
    return substr(hash('sha256', gizli_anahtar() . $taban), 0, 20);
}

function gun_anahtari(?int $t = null): string
{
    return gmdate('Y-m-d', ($t ?? time()) + TZ_OFFSET);
}

// ---------------------------------------------------------------- oturum

function oturum_baslat(): void
{
    if (session_status() === PHP_SESSION_ACTIVE) return;
    session_save_path(VERI . '/oturumlar');
    ini_set('session.gc_maxlifetime', (string) (30 * 86400));
    ini_set('session.use_strict_mode', '1');
    session_name('rv_oturum');
    session_set_cookie_params([
        'lifetime' => 30 * 86400, 'path' => '/', 'secure' => https_mi(), 'httponly' => true, 'samesite' => 'Lax',
    ]);
    session_start();
}

function csrf(): string
{
    oturum_baslat();
    if (empty($_SESSION['csrf'])) $_SESSION['csrf'] = bin2hex(random_bytes(18));
    return $_SESSION['csrf'];
}

function csrf_dogrula(): void
{
    oturum_baslat();
    $gelen = (string) ($_SERVER['HTTP_X_CSRF_TOKEN'] ?? '');
    if ($gelen === '' || empty($_SESSION['csrf']) || !hash_equals($_SESSION['csrf'], $gelen)) {
        throw new ApiHata('Oturum doğrulaması başarısız. Sayfayı yenileyin.', 403);
    }
}

function kullanici(): ?array
{
    static $u = false;
    if ($u !== false) return $u;
    oturum_baslat();
    $u = null;
    if (!empty($_SESSION['uid'])) {
        $u = satir('SELECT * FROM users WHERE id = ?', [(int) $_SESSION['uid']]);
        if (!$u) unset($_SESSION['uid']);
    }
    return $u;
}

function giris_yap(int $uid): void
{
    oturum_baslat();
    session_regenerate_id(true);
    $_SESSION = ['uid' => $uid, 'csrf' => bin2hex(random_bytes(18))];
}

function giris_gerekli(): array
{
    $u = kullanici();
    if (!$u) throw new ApiHata('Bu işlem için giriş yapmalısınız.', 401);
    return $u;
}

function yonetici_gerekli(): array
{
    $u = giris_gerekli();
    if (!(int) $u['is_admin']) throw new ApiHata('Bu sayfa yalnızca site yöneticisi içindir.', 403);
    return $u;
}

function kullanici_json(?array $u): ?array
{
    if (!$u) return null;
    return [
        'id' => (int) $u['id'], 'email' => $u['email'], 'name' => $u['name'], 'is_admin' => (bool) $u['is_admin'],
        'billing' => $u['billing'] ? json_decode($u['billing'], true) : null,
    ];
}

// ---------------------------------------------------------------- pano yardımcıları

function hucreler(int $x, int $y, int $w, int $h): array
{
    $c = [];
    for ($yy = $y; $yy < $y + $h; $yy++) for ($xx = $x; $xx < $x + $w; $xx++) $c[] = $yy * COLS + $xx;
    return $c;
}

function dortgen_sql(): string
{
    return '(cell / ' . COLS . ') BETWEEN ? AND ? AND (cell % ' . COLS . ') BETWEEN ? AND ?';
}

function dortgen_arg(int $x, int $y, int $w, int $h): array
{
    return [$y, $y + $h - 1, $x, $x + $w - 1];
}

function hucre_kilitle(array $hucreler, ?int $order_id, ?int $slot_id, int $bitis): void
{
    $st = db()->prepare('INSERT INTO cell_locks(cell, order_id, slot_id, expires_at) VALUES (?, ?, ?, ?)');
    foreach ($hucreler as $c) bagla($st, [$c, $order_id, $slot_id, $bitis]);
}

function alan_etiketi(array $r): string
{
    return sprintf('%d×%d px (%d×%d blok)', $r['w'] * BLOCK, $r['h'] * BLOCK, $r['w'], $r['h']);
}

function metin_temizle($v, int $sinir): string
{
    $s = trim((string) preg_replace('/\s+/u', ' ', (string) ($v ?? '')));
    return mb_substr($s, 0, $sinir);
}

function tl(int $kurus): string
{
    return '₺' . number_format(intdiv($kurus, 100), 0, ',', '.') . ',' . sprintf('%02d', $kurus % 100);
}

function e($s): string
{
    return htmlspecialchars((string) $s, ENT_QUOTES, 'UTF-8');
}

/** Süresi dolan rezervasyonları ve yayın süresi biten alanları serbest bırakır.
 *  Sorgular zaten expires_at'e baktığı için doğruluk buna bağlı değildir. */
function temizlik(bool $zorla = false): void
{
    $isaret = VERI . '/.temizlik';
    if (!$zorla && is_file($isaret) && time() - (int) @filemtime($isaret) < 15) return;
    @touch($isaret);
    $n = time();
    tx(function () use ($n) {
        q("UPDATE orders SET status = 'expired' WHERE status = 'pending' AND expires_at <= ?", [$n]);
        q("UPDATE slots SET status = 'expired' WHERE status IN ('active','suspended') AND ends_at <= ?", [$n]);
        q('DELETE FROM cell_locks WHERE expires_at <= ?', [$n]);
        q('DELETE FROM seen WHERE expires_at <= ?', [$n]);
        q('DELETE FROM rate_log WHERE t < ?', [$n - 86400]);
    });
}
