<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Test Ödemesi · Reklam Veriyor</title>
<link rel="stylesheet" href="/static/css/style.css?v=2">
</head>
<body class="page">
<main class="narrow">
  <div class="paycard">
    <div class="test-ribbon">TEST ÖDEME SAYFASI · Gerçek para çekilmez</div>
    <h1>Ödeme</h1>
    <p class="muted">Bu sayfa, gerçek ödeme sağlayıcısının (iyzico) yerine geçen bir denemedir.
      <code>ayarlar.php</code> içinde <code>'odeme_saglayici' =&gt; 'iyzico'</code> yapılınca kapanır.</p>
    <dl class="summary">
      <div><dt>Sipariş</dt><dd><?= e($o['ref']) ?></dd></div>
      <div><dt><?= $o['kind'] === 'renew' ? 'Süre uzatma' : 'Reklam alanı' ?></dt><dd><?= e($etiket) ?></dd></div>
      <div><dt>Toplam piksel</dt><dd><?= number_format((int) $o['pixels'], 0, ',', '.') ?></dd></div>
      <div><dt>Yayın süresi</dt><dd><?= (int) $o['duration_days'] ?> gün</dd></div>
      <div class="total"><dt>Tutar</dt><dd><?= e(tl((int) $o['amount'])) ?></dd></div>
    </dl>
    <?php if ($bitti): ?>
      <p class="alert">Bu siparişin ödeme süresi doldu veya sipariş kapandı. Panoya dönüp alanı yeniden seçebilirsiniz.</p>
      <a class="btn" href="/reklamlarim">Reklamlarım</a>
    <?php else: ?>
      <p class="muted">Alan sizin için <strong><?= intdiv($kalan, 60) ?> dk <?= $kalan % 60 ?> sn</strong> daha ayrılmış durumda.</p>
      <form method="post" class="paybtns">
        <input type="hidden" name="token" value="<?= e($o['provider_token']) ?>">
        <button class="btn primary" name="result" value="success">Ödemeyi onayla (test)</button>
        <button class="btn ghost" name="result" value="failure">Ödeme başarısız olsun</button>
      </form>
    <?php endif; ?>
  </div>
</main>
</body>
</html>
