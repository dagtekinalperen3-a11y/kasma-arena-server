<?php
/*
 * Reklam Veriyor — piksel reklam panosu
 * Bütün istekler .htaccess ile bu dosyaya yönlendirilir.
 */
declare(strict_types=1);

// PHP'nin yerleşik sunucusunda (yerel deneme) statik dosyaları doğrudan ver.
if (PHP_SAPI === 'cli-server') {
    $p = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);
    if (str_starts_with($p, '/static/') && is_file(__DIR__ . $p)) return false;
}

require __DIR__ . '/lib/temel.php';
require __DIR__ . '/lib/odeme.php';
require __DIR__ . '/lib/rotalar.php';

$sorunlar = kurulum_kontrol();
if ($sorunlar) {
    http_response_code(500);
    header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><meta charset="utf-8"><title>Kurulum</title><body style="font-family:sans-serif;max-width:640px;margin:40px auto;padding:0 16px">';
    echo '<h1>Reklam Veriyor kurulumu tamamlanmadı</h1><ul>';
    foreach ($sorunlar as $s) echo '<li>' . e($s) . '</li>';
    echo '</ul></body>';
    exit;
}
koru_dizin(VERI);
koru_dizin(YUKLEME_DIZINI);
koru_dizin(VERI . '/oturumlar');

try {
    yonetici_hazirla();
    yonlendirici();
} catch (ApiHata $e) {
    json_yanit(['error' => $e->getMessage()] + $e->ek, $e->durum);
} catch (Throwable $e) {
    @file_put_contents(VERI . '/hata.log', date('c') . ' ' . $e->getMessage() . ' @ ' . $e->getFile() . ':' . $e->getLine() . "\n", FILE_APPEND);
    $yol = (string) parse_url($_SERVER['REQUEST_URI'] ?? '/', PHP_URL_PATH);
    if (str_starts_with($yol, '/api/')) json_yanit(['error' => 'Sunucu hatası. Lütfen biraz sonra tekrar deneyin.'], 500);
    http_response_code(500);
    header('Content-Type: text/html; charset=utf-8');
    echo '<!doctype html><meta charset="utf-8"><p style="font-family:sans-serif">Sunucu hatası. <a href="/">Panoya dön</a></p>';
}
