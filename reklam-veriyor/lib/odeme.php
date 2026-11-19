<?php
/*
 * Ödeme sağlayıcıları.
 *   baslat($siparis, $ctx) -> ['token' => ..., 'url' => ...]   ödeme sayfasını açar
 *   sorgula($siparis)      -> ['state' => success|failure|pending|error, ...]
 *   iade($siparis)         -> bool  (alan başkasına geçmişse para iadesi)
 *
 * Ödeme sonucuna tarayıcıdan gelen veriye bakarak karar verilmez: iyzico dönüşünde
 * yalnızca token alınır, sonuç iyzico API'sinden sunucu-sunucu sorgulanır ve
 * tutar, para birimi ve sipariş numarası kontrol edilir.
 */
declare(strict_types=1);

final class OdemeHatasi extends Exception {}

function kurus_metin(int $kurus): string
{
    return sprintf('%d.%02d', intdiv($kurus, 100), $kurus % 100);
}

final class TestOdeme
{
    public string $ad = 'test';
    public bool $canli = false;
    public string $etiket = 'Test ödemesi (gerçek para çekilmez)';

    public function baslat(array $o, array $ctx): array
    {
        return ['token' => bin2hex(random_bytes(24)), 'url' => '/odeme/test/' . $o['ref']];
    }

    public function sorgula(array $o): array
    {
        return ['state' => 'pending'];   // sonucu /odeme/test sayfası bildirir
    }

    public function iade(array $o): bool
    {
        return true;
    }
}

final class IyzicoOdeme
{
    public string $ad = 'iyzico';
    public bool $canli;
    public string $etiket;
    private string $anahtar;
    private string $gizli;
    private string $adres;

    const BASLAT = '/payment/iyzipos/checkoutform/initialize/auth/ecom';
    const SORGU = '/payment/iyzipos/checkoutform/auth/ecom/detail';
    const IPTAL = '/payment/cancel';

    public function __construct(string $anahtar, string $gizli, string $adres)
    {
        $this->anahtar = $anahtar;
        $this->gizli = $gizli;
        $this->adres = rtrim($adres, '/');
        $this->canli = !str_contains($this->adres, 'sandbox');
        $this->etiket = 'iyzico' . ($this->canli ? '' : ' (sandbox)');
    }

    private function istek(string $yol, array $govde): array
    {
        $yuk = json_encode($govde, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        $rnd = (string) floor(microtime(true) * 1000) . bin2hex(random_bytes(4));
        $imza = hash_hmac('sha256', $rnd . $yol . $yuk, $this->gizli);
        $auth = base64_encode('apiKey:' . $this->anahtar . '&randomKey:' . $rnd . '&signature:' . $imza);
        $ch = curl_init($this->adres . $yol);
        curl_setopt_array($ch, [
            CURLOPT_POST => true,
            CURLOPT_POSTFIELDS => $yuk,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT => 25,
            CURLOPT_HTTPHEADER => [
                'Authorization: IYZWSv2 ' . $auth,
                'x-iyzi-rnd: ' . $rnd,
                'Content-Type: application/json',
                'Accept: application/json',
            ],
        ]);
        $yanit = curl_exec($ch);
        $hata = curl_error($ch);
        curl_close($ch);
        if ($yanit === false) throw new OdemeHatasi("iyzico'ya ulaşılamadı: " . $hata);
        $veri = json_decode((string) $yanit, true);
        if (!is_array($veri)) throw new OdemeHatasi('iyzico yanıtı okunamadı');
        return $veri;
    }

    public function baslat(array $o, array $ctx): array
    {
        $f = $ctx['billing'];
        $u = $ctx['user'];
        $tam = trim($f['name'] ?? '') ?: (trim($u['name']) ?: 'Reklam Veren');
        $parca = preg_split('/\s+/u', $tam);
        $ad = count($parca) > 1 ? implode(' ', array_slice($parca, 0, -1)) : $tam;
        $soyad = count($parca) > 1 ? end($parca) : $tam;
        $fiyat = kurus_metin((int) $o['amount']);
        $adres = [
            'contactName' => $tam,
            'city' => ($f['city'] ?? '') ?: 'Istanbul',
            'country' => 'Turkey',
            'address' => ($f['address'] ?? '') ?: '-',
        ];
        $tc = preg_replace('/\D/', '', (string) ($f['tax_id'] ?? ''));
        $veri = $this->istek(self::BASLAT, [
            'locale' => 'tr',
            'conversationId' => $o['ref'],
            'price' => $fiyat,
            'paidPrice' => $fiyat,
            'currency' => 'TRY',
            'basketId' => $o['ref'],
            'paymentGroup' => 'PRODUCT',
            'callbackUrl' => $ctx['callback_url'],
            'enabledInstallments' => [1],
            'buyer' => [
                'id' => 'U' . $u['id'],
                'name' => $ad,
                'surname' => $soyad,
                'gsmNumber' => $f['phone'] ?? '',
                'email' => $u['email'],
                // TC kimlik no zorunlu alan; girilmediyse iyzico'nun kabul ettiği varsayılan
                'identityNumber' => strlen($tc) === 11 ? $tc : '11111111111',
                'registrationAddress' => $adres['address'],
                'ip' => $ctx['ip'] ?: '127.0.0.1',
                'city' => $adres['city'],
                'country' => 'Turkey',
            ],
            'billingAddress' => $adres,
            'shippingAddress' => $adres,
            'basketItems' => [[
                'id' => 'ALAN-' . $o['ref'],
                'name' => mb_substr($ctx['item_name'], 0, 250),
                'category1' => 'Reklam',
                'itemType' => 'VIRTUAL',
                'price' => $fiyat,
            ]],
        ]);
        if (($veri['status'] ?? '') !== 'success' || empty($veri['token']) || empty($veri['paymentPageUrl'])) {
            throw new OdemeHatasi($veri['errorMessage'] ?? 'iyzico ödeme sayfasını başlatamadı');
        }
        return ['token' => $veri['token'], 'url' => $veri['paymentPageUrl']];
    }

    public function sorgula(array $o): array
    {
        if (empty($o['provider_token'])) return ['state' => 'error', 'message' => 'token yok'];
        $v = $this->istek(self::SORGU, ['locale' => 'tr', 'conversationId' => $o['ref'], 'token' => $o['provider_token']]);
        if (($v['status'] ?? '') !== 'success') return ['state' => 'error', 'message' => $v['errorMessage'] ?? 'sorgu başarısız'];
        foreach (['basketId', 'conversationId'] as $alan) {
            if (isset($v[$alan]) && $v[$alan] !== $o['ref']) return ['state' => 'error', 'message' => $alan . ' eşleşmedi'];
        }
        $durum = strtoupper((string) ($v['paymentStatus'] ?? ''));
        if ($durum === 'SUCCESS') {
            $fraud = $v['fraudStatus'] ?? null;
            if ($fraud === -1) return ['state' => 'failure', 'message' => 'iyzico dolandırıcılık kontrolü reddetti'];
            if ($fraud === 0) return ['state' => 'pending', 'message' => 'iyzico incelemesi sürüyor'];
            if (($v['currency'] ?? 'TRY') !== 'TRY') return ['state' => 'error', 'message' => 'para birimi eşleşmedi'];
            return ['state' => 'success', 'payment_id' => (string) ($v['paymentId'] ?? ''),
                    'amount' => (int) round(((float) ($v['price'] ?? 0)) * 100)];
        }
        if ($durum === 'FAILURE' || $durum === 'FAILED') return ['state' => 'failure', 'message' => $v['errorMessage'] ?? 'ödeme başarısız'];
        return ['state' => 'pending'];
    }

    public function iade(array $o): bool
    {
        if (empty($o['provider_payment_id'])) return false;
        try {
            $v = $this->istek(self::IPTAL, ['locale' => 'tr', 'conversationId' => $o['ref'],
                                             'paymentId' => $o['provider_payment_id'], 'ip' => $o['ip'] ?: '127.0.0.1']);
        } catch (OdemeHatasi $e) {
            return false;
        }
        return ($v['status'] ?? '') === 'success';
    }
}

function saglayici()
{
    static $p = null;
    if ($p) return $p;
    $secim = strtolower((string) cfg('odeme_saglayici', 'test'));
    if ($secim === 'iyzico') {
        $k = (string) cfg('iyzico_api_key', '');
        $g = (string) cfg('iyzico_secret_key', '');
        if ($k === '' || $g === '') throw new RuntimeException('iyzico seçili ama ayarlar.php içinde API anahtarları boş.');
        return $p = new IyzicoOdeme($k, $g, (string) cfg('iyzico_adres', 'https://sandbox-api.iyzipay.com'));
    }
    return $p = new TestOdeme();
}
