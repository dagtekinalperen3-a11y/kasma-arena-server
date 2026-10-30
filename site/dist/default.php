<?php
// İndirme sayacı. ?action=hit sayacı 1 artırır (aynı IP'den dakikada en çok
// 1 kez), parametresiz istek sayıyı döndürür. Dosyalar kilitlenerek yazılır.
header('Content-Type: text/plain; charset=utf-8');
header('Cache-Control: no-store');
header('X-Content-Type-Options: nosniff');

$file = __DIR__ . '/counter.txt';
$ipsFile = __DIR__ . '/counter_ips.json';

function read_count($file) {
    return file_exists($file) ? max(0, (int)file_get_contents($file)) : 0;
}

if (isset($_GET['action']) && $_GET['action'] === 'hit') {
    $ip = hash('sha256', 'ea-dl|' . ($_SERVER['REMOTE_ADDR'] ?? ''));
    $now = time();
    $fp = fopen($ipsFile, 'c+');
    $allowed = true;
    if ($fp && flock($fp, LOCK_EX)) {
        $raw = stream_get_contents($fp);
        $ips = json_decode($raw ?: '{}', true);
        if (!is_array($ips)) { $ips = []; }
        foreach ($ips as $k => $t) { if ($now - (int)$t > 60) { unset($ips[$k]); } }
        if (isset($ips[$ip])) { $allowed = false; } else { $ips[$ip] = $now; }
        if (count($ips) > 5000) { $ips = array_slice($ips, -2000, null, true); }
        ftruncate($fp, 0); rewind($fp); fwrite($fp, json_encode($ips));
        flock($fp, LOCK_UN);
    }
    if ($fp) { fclose($fp); }

    $cf = fopen($file, 'c+');
    $count = 0;
    if ($cf && flock($cf, LOCK_EX)) {
        $count = max(0, (int)stream_get_contents($cf));
        if ($allowed) {
            $count++;
            ftruncate($cf, 0); rewind($cf); fwrite($cf, (string)$count);
        }
        flock($cf, LOCK_UN);
    }
    if ($cf) { fclose($cf); }
    echo $count;
    exit;
}

echo read_count($file);
