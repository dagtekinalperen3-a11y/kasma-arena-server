<?php
/* Panoyu tanıtmak için kurgusal demo reklamlar (Yönetim > Demo reklamları yükle).
 * Görseller static/demo/ klasöründedir. Yönetim panelinden tek tıkla kaldırılır. */
declare(strict_types=1);

const DEMO_REKLAMLAR = [
    // x, y, w, h (blok), anahtar, başlık, açıklama, buton, konum, buton zemini, buton yazısı, arka plan
    [0, 0, 12, 8, 'kahve', 'Kahve Köşesi', 'Taze çekilmiş, her sabah', 'Menüyü Gör', 'br', '#ffc83d', '#1b1206', '#3b1d0f'],
    [68, 0, 12, 8, 'kitap', 'Mavi Kitap Evi', 'İkinci el kitaplarda %30', 'Ürünü İncele', 'br', '#ffffff', '#0f2a5c', '#0f2a5c'],
    [0, 42, 12, 8, 'pedal', 'Pedal Atölyesi', 'Bisiklet bakımı tek günde', 'Randevu Al', 'br', '#ffe066', '#10261d', '#0e3b2e'],
    [68, 42, 12, 8, 'kodla', 'Kodla Başla', 'Hafta sonu yazılım kursu', 'Kayıt Ol', 'br', '#ffffff', '#2a0f4a', '#2a0f4a'],
    [12, 0, 6, 4, 'saksi', 'Yeşil Saksı', 'Ofis bitkileri', 'Siteye Git', 'bc', '#ffffff', '#4a1020', '#4a1020'],
    [18, 0, 10, 6, 'firin', 'Tatlı Fırın', 'Ev yapımı baklava', 'Hemen Al', 'br', '#ffd166', '#0b2427', '#123a40'],
    [30, 0, 20, 5, 'indirim', 'Kış Fırsatları', 'Montlarda sezon sonu indirimi', 'Ürünü İncele', 'mr', '#ffc83d', '#1b1206', '#3b1d0f'],
    [52, 0, 4, 4, 'pati', 'Pati Bakım', '', 'Siteye Git', 'bc', '#ffffff', '#0f2a5c', '#0f2a5c'],
    [56, 0, 8, 8, 'seramik', 'Seramik Atölyesi', 'Çamurla tanış', 'Kayıt Ol', 'bc', '#ffe066', '#10261d', '#0e3b2e'],
    [64, 0, 4, 4, 'yoga', 'Yoga Evi', '', 'Siteye Git', 'bc', '#ffffff', '#2a0f4a', '#2a0f4a'],
    [14, 46, 8, 4, 'tekne', 'Tekne Turu', 'Gün batımında', 'Hemen Al', 'br', '#ffffff', '#4a1020', '#4a1020'],
    [24, 44, 16, 6, 'pazar', 'Organik Pazar', 'Kapına kadar taze sebze', 'Siteye Git', 'br', '#ffd166', '#0b2427', '#123a40'],
    [42, 47, 3, 3, 'a1', 'Balıkçı', 'Günlük taze balık', 'Siteye Git', 'bc', '#ffc83d', '#1b1206', '#3b1d0f'],
    [45, 47, 3, 3, 'a2', 'Çınar Kafe', '', 'Siteye Git', 'bc', '#ffffff', '#2a0f4a', '#2a0f4a'],
    [48, 46, 10, 4, 'muzik', 'Gitar Dersi', 'Birebir, online', 'Kayıt Ol', 'mr', '#ffffff', '#0f2a5c', '#0f2a5c'],
    [60, 45, 6, 5, 'cicek', 'Mor Çiçekçi', 'Aynı gün teslim', 'Hemen Al', 'bc', '#ffe066', '#10261d', '#0e3b2e'],
    [0, 8, 6, 6, 'kirtasiye', 'Kampüs Kırtasiye', '', 'Siteye Git', 'bc', '#ffffff', '#4a1020', '#4a1020'],
    [0, 16, 8, 10, 'yemek', 'Ev Yemekleri', 'Günlük menü', 'Menüyü Gör', 'bc', '#ffd166', '#0b2427', '#123a40'],
    [0, 28, 5, 5, 'oyun', 'Oyun Kulübü', '', 'Siteye Git', 'bc', '#ffc83d', '#1b1206', '#3b1d0f'],
    [0, 34, 10, 8, 'foto', 'Deniz Fotoğraf', 'Düğün ve etkinlik', 'Siteye Git', 'br', '#ffffff', '#0f2a5c', '#0f2a5c'],
    [74, 8, 6, 6, 'tamir', 'Usta Tamir', '', 'Randevu Al', 'bc', '#ffe066', '#10261d', '#0e3b2e'],
    [72, 16, 8, 12, 'kamp', 'Kamp Malzemesi', 'Çadır, uyku tulumu', 'Ürünü İncele', 'bc', '#ffffff', '#2a0f4a', '#2a0f4a'],
    [75, 30, 5, 5, 'dil', 'Dil Kursu', '', 'Kayıt Ol', 'bc', '#ffffff', '#4a1020', '#4a1020'],
    [70, 35, 10, 7, 'spor', 'Sabah Koşusu', 'Ücretsiz grup antrenmanı', 'Kayıt Ol', 'br', '#ffd166', '#0b2427', '#123a40'],
    [30, 18, 20, 12, 'recel', 'Bahçeden Reçel', 'Katkısız, şekeri az, kavanozda', 'Ürünü İncele', 'br', '#ffc83d', '#1b1206', '#3b1d0f'],
    [20, 10, 6, 6, 'kedi', 'Kedi Maması', '', 'Hemen Al', 'bc', '#ffffff', '#0f2a5c', '#0f2a5c'],
    [52, 12, 8, 5, 'harita', 'Gezi Rehberi', 'Ege rotaları', 'Siteye Git', 'br', '#ffe066', '#10261d', '#0e3b2e'],
    [24, 30, 4, 4, 'kalem', 'Hat Sanatı', '', 'Siteye Git', 'bc', '#ffffff', '#2a0f4a', '#2a0f4a'],
    [54, 24, 10, 6, 'ajans', 'Dijital Ajans', 'Web sitesi + reklam', 'Siteye Git', 'br', '#ffffff', '#4a1020', '#4a1020'],
    [14, 14, 1, 1, 'm1', 'Simitçi', 'Sıcak simit, çay', 'Siteye Git', 'bc', '#ffd166', '#0b2427', '#123a40'],
    [15, 14, 1, 1, 'm2', 'Anahtarcı', '7/24 çilingir', 'Siteye Git', 'bc', '#ffc83d', '#1b1206', '#3b1d0f'],
    [16, 14, 1, 1, 'm3', 'Terzi', 'Paça ve tadilat', 'Siteye Git', 'bc', '#ffe066', '#10261d', '#0e3b2e'],
    [62, 30, 2, 2, 'm4', 'Lostra', 'Ayakkabı boyama', 'Siteye Git', 'bc', '#ffffff', '#2a0f4a', '#2a0f4a'],
    [40, 36, 2, 1, 'm5', 'Kuaför', 'Randevusuz', 'Randevu Al', 'bc', '#ffffff', '#4a1020', '#4a1020'],
];

function demo_yukle(): int
{
    if (COLS !== 80 || ROWS !== 50) throw new ApiHata('Demo yerleşimi 1200×750 / 15 px panoya göre hazırlandı.');
    $t = time();
    return tx(function () use ($t) {
        q('DELETE FROM cell_locks WHERE expires_at <= ?', [$t]);
        $uid = deger("SELECT id FROM users WHERE email = 'demo@reklamveriyor.local'");
        if (!$uid) {
            q('INSERT INTO users(email, pw_hash, name, created_at) VALUES (?, ?, ?, ?)',
              ['demo@reklamveriyor.local', password_hash(bin2hex(random_bytes(16)), PASSWORD_DEFAULT), 'Demo Reklamveren', $t]);
            $uid = db()->lastInsertId();
        }
        $eklenen = 0;
        foreach (DEMO_REKLAMLAR as [$x, $y, $w, $h, $k, $baslik, $aciklama, $buton, $konum, $bbg, $bfg, $bg]) {
            if ((int) deger('SELECT COUNT(*) FROM cell_locks WHERE ' . dortgen_sql(), dortgen_arg($x, $y, $w, $h))) continue;
            $icerik = json_encode([
                'image' => 'demo/demo-' . $k . '.svg', 'fit' => 'cover', 'bg' => $bg, 'title' => $baslik,
                'description' => $aciklama ?: 'Demo reklam', 'button_text' => $buton, 'button_pos' => $konum,
                'button_bg' => $bbg, 'button_fg' => $bfg, 'url' => 'https://example.com/' . $k,
            ], JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
            $bitis = $t + 365 * 86400;
            q("INSERT INTO slots(user_id, x, y, w, h, starts_at, ends_at, status, content, published_at, is_demo, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, 1, ?)", [$uid, $x, $y, $w, $h, $t, $bitis, $icerik, $t, $t]);
            hucre_kilitle(hucreler($x, $y, $w, $h), null, (int) db()->lastInsertId(), $bitis);
            $eklenen++;
        }
        return $eklenen;
    });
}
