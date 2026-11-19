<?php
/*
 * Reklam Veriyor — site ayarları
 * Bu dosyayı hosting dosya yöneticisinden düzenleyin. Fiyat ve yayın süresi
 * buradan DEĞİL, sitedeki Yönetim panelinden (/yonetim) ayarlanır.
 */
return [
    // Sitenin tam adresi (sonunda / olmadan). Ödeme dönüş adresi için gerekli.
    'site_adresi' => '',              // örnek: 'https://reklamveriyor.com'

    // Site yöneticisi hesabı. İlk girişten sonra şifreyi burada tutmaya devam edin;
    // değiştirirseniz bir sonraki açılışta güncellenir.
    'yonetici_eposta' => '',          // örnek: 'siz@ornek.com'
    'yonetici_sifre'  => '',          // en az 8 karakter

    // Ödeme sağlayıcısı: 'test' (gerçek para çekilmez) veya 'iyzico'
    'odeme_saglayici' => 'test',
    'iyzico_api_key'    => '',
    'iyzico_secret_key' => '',
    // Deneme: https://sandbox-api.iyzipay.com   Canlı: https://api.iyzipay.com
    'iyzico_adres' => 'https://sandbox-api.iyzipay.com',

    // Veritabanı ve yüklenen görsellerin klasörü. Mümkünse public_html DIŞINDA
    // bir klasör verin (örn. '/home/KULLANICI/reklam-veri'). Boş bırakılırsa
    // korumalı 'veri' klasörü kullanılır.
    'veri_dizini' => '',

    // Pano ölçüsü (sanal piksel). Satış başladıktan sonra değiştirmeyin.
    'pano_genislik'  => 1200,
    'pano_yukseklik' => 750,
    'blok'           => 15,
];
