# Değişiklikler

Kısa notlar, en yenisi üstte.

## sıradaki sürüm
- arayüz elden geçti (oyun mantığına dokunulmadı):
  - yeni yazı tipleri: başlık ve düğmelerde Russo One, geri kalan her yerde
    Onest (Balsamiq Sans kalktı); başlıklardaki zorla açılmış harf aralığı da
    kalktı
  - düğme ve başlıklarda degrade yok: dünya / yerel / 2 kişilik sıralama
    başlıkları, sıralama satırları, istatistik paneli, kış penceresi düz renk;
    düğmelerin üstündeki parlak çizgi ve dolum çubuklarındaki parlama kalktı
  - yazıyla aynı renkte kenarlık yok: zorluk seçici, seviye eli çipleri, harita
    rozetleri, ayarlar satırları, sonuç ekranı kutuları, mağaza / skin /
    başarım kartları, market kartları, sekmeler. Rozetler artık hafif boyalı
    koyu zemin + mürekkep kenar (tag_chip); renk yazıda ve simgede kalıyor
  - ortalanan yazılar büyük harf yüksekliğine göre dikey ortalanır; kalın
    yazılarda kalın kontur yalnız büyük başlıklarda, düğmelerde sert gölge
  - kayık başlık / alt başlıklar düzeldi: duraklatma başlığı panelden
    taşıyordu, seviye elindeki ipucu satırı çiplerin altında oyun dünyasının
    üstünde okunmuyordu (artık koyu levhada), sıralama başlığındaki yıldızlar
    ve ayarlar / hesap başlığındaki ayraçlar başlık hizasında, KİŞİSEL REKOR
    şeridinin alt satırı ve tüccar balonundaki şans satırı kenara biniyordu
- v3.49: 2 kişilikte iki oyuncu da aynı sürümü kullanmalı (eski dosyayla oda
  kurulunca konuğun kartları ev sahibinin kaydından çıkıyordu)
- ana menü sadeleşti: AYARLAR ve ARKADAŞLAR sol üstte küçük kare düğmeler
  (arkadaşlarda okunmamış rozeti ve çevrimiçi noktası); KIYAFET MARKET kalktı,
  şapka / gözlük / pelerin / pet SKİN MARKET'in sekmeleri; 2 kişilik yalnızca
  OYNA > harita seçiminde (sağ altta); menüdeki arkadaş şeridi kaldırıldı
- açılmamış silah hiçbir yerden gelmez (raf, elinde verecek silah yoksa artık
  bütün silahları değil altın verir)
- 2 kişilik:
  - aynı silah iki oyuncuda olmaz: biri kırbaç aldıysa öbürüne kırbaç seviye
    elinde, sandıkta, efsanevi elde, rafta çıkmaz; açık elinde varsa el
    kendiliğinden yenilenir
  - ikiniz de ESC'ye basarsanız oyun durur (arkadaş düşmüşse ya da koptuysa
    tek başına ESC yeter); biri moladaysa öbürüne üstte yazar
- ARKADAŞLAR (ana menüde yeni düğme): kullanıcı adıyla ekle, isteği kabul et /
  reddet, sil; kim çevrimiçi, menüde mi oyunda mı 2 kişilikte mi görünür;
  arkadaşınla yazışma; profil (en iyi skor, dalga, öldürme, koşu, patron,
  en iyi 2 kişilik skoru ve kiminle); tek tıkla 2 kişiliğe çağır (oda yoksa
  kendiliğinden kurulur). Davet her ekranın üstünde KATIL / SONRA ile belirir;
  yeni mesaj ve arkadaşlık isteği bildirimi, menüde okunmamış rozeti.
  Sunucuda VERITABANI_SOSYAL.sql bir kez çalıştırılmalı
- 2 KİŞİLİK DÜNYA SIRALAMASI: 2 KİŞİLİK ekranı merkez oldu (oda kur, katıl,
  arkadaşlar, sıralama). İkili olarak girersiniz; satırda iki oyuncunun
  silahları yan yana, evrilenler altın halkalı; tıklayınca ikisinin tam kartı
  (silah, kitap, evrim, hasar dökümü, kişisel skor). Skoru ev sahibi gönderir,
  sunucu iki hesabı odadan bilir; sonuç ekranında "#3!" gibi sıra çıkar
- 2 kişilik:
  - evrim artık 2 kişilikte de var: kişi başı 2 silah yuvası olduğu için orada
    2 silah yeter; arkadaş evrilince ikinizin ekranında duyuru
  - mıknatıs: kim alırsa alsın haritadaki altın ve tecrübe ikiye eşit bölünür
  - seviye eli ve mağara kapanınca 3 sn dokunulmazlık (altın kalkan balonu);
    mağaradan +6 seviye gibi üst üste kartlarda her kart için ek koruma
  - konuğun seviye kartları kendi açtığı silah ve kitaplardan çıkar (önceden
    ev sahibinin kaydından çıkıyordu: yeni oyuncunun odasında eski oyuncu
    neredeyse hiç silah göremiyordu)
  - L ile oyunda / lobide arkadaşına yazma
  - takım halkaları, isim etiketi, ekran dışı arkadaş rozeti (yön + mesafe),
    toplu takım paneli; eğitim 2 kişilikte araya girmez
- seviye / mağara ekranındaki takılma: pencere arkasındaki dünya önbellekte
  (seviye ekranı ~2 kat hızlı); yazı tipleri menüde önceden yüklenir
- EĞİTİM: oyuna ilk kez girene kısa bir tur: silahlık (silahlar nasıl açılır,
  aç / kapat), skin market'ten bedava Yeşil Öncü'yü aldırır, oyunu başlatır,
  bir düşman öldürtür, B ile marketi açtırır. Her adımda "EĞİTİMİ GEÇ" var.
  Hem oyunu ilk kez açana hem de yeni hesap açana (kullanıcı adıyla ya da
  Google ile ilk kez) gösterilir
- 2 KİŞİLİK:
  - elmas artık 2 kişilikte de kazanılıyor (herkes kendi topladığı kadar,
    tek kişilikle aynı oranda); sonuç ekranında yazar
  - PATRON RUHU: patron ölünce bir ruh çıkar. Biri ölmüşse ruh ona uçar,
    yaşayan arkadaş mezarın başında 3 sn durunca yarı canla dirilir. Kimse
    ölmediyse ruh bekler; birikmez, en çok 1 tane olur
  - sunak birine gelince ikisine de işler
- evrimler belirgin: Kıyamet Baltası patlaması gerçek bir patlama (ateş topu,
  iki halka, ses); evrilmiş silahlar kendi renginde parlıyor; diğer evrim
  etkilerinin de görünür işaretleri var
- sandık açılınca dünyada üst üste binen yazılar yerine ekranın üstünde tek,
  düzenli bir ödül kartı; "PATRON DEVRİLDİ" karakterin üstüne binmiyor
- altın: kesirli altın artık birikir (art arda hiç düşmeyen öldürmeler yok);
  paralar daha büyük, konturlu ve parlıyor, büyük yığın üç para görünüyor
- hasar dökümünde "parry" yerine "Savuşturma" (+ "Kitap etkileri")
- FPS: kalabalık sahnede kare süresi ~%25 kısaldı (sol üst şeritler, üst
  bilgi, küçük harita ve yetenek çubuğu hazır görüntüden; yerdeki eşyalar
  tek seferde; ışık zerreleri yalnız kamerada olanlar; silah efekti kısma
  varsayılanı kapalı - her karede tam ekran kopyası yapıyordu)
- KARTOPU: zemin bembeyaz kar, buz temalı pencereler; her yaratık 2 elmas,
  tank 3, altın goblin 6 (iyi bir oyun ~100, tavan 130)
- ÖLÜM TEKRARI: ölünce sonuç ekranında "SON ANLARI İZLE" düğmesi çıkar
  - son 8 saniye oynar, son 1,6 saniye ağır çekim; son karede renk çekilir
    ve seni kimin öldürdüğü yazar. ESC ya da tıklama ile geçilir
  - hiçbir yere kaydedilmez (yalnızca bellekte); sonuç ekranından çıkınca
    silinir, sonra bir daha izlenemez
  - 2 kişilikte de var: düştüğün an + 1,4 sn kaydedilir, oyun sonu ekranından
    izlenir
- 2 KİŞİLİK, KONUK TARAFI GECİKME HİSSİ:
  - konuğun ana silahı artık ev sahibini beklemeden anında ateşlenir: mermi
    o an senin namlundan çıkar, sesi o an çalar (hasarı yine ev sahibi verir,
    onun gönderdiği geç kopya gizlenir)
  - kırbaç, kılıç, ışın, hayalet kılıçlar, yarasalar ve deprem artık
    karakterinin geride kalmış hâlinde değil, şimdiki yerinde çizilir
    (doğrudan bağlantıda ~25 px, sunucu üstünde ~95 px kayma gitti)
  - doğrudan bağlantıda görüntü sıklığı 30 -> 45/sn: öbür oyuncu ve
    yaratıklar daha az geriden gelir
- YETENEK: oyun artık "4 silah al, düz koş" ile kazanılmıyor
  - ODAK (oyuncunun altındaki çubuk): elle nişan alıp vurdukça, kusursuz
    kaçış ve savuşturmayla dolar; ateşi bırakınca ve vurulunca düşer.
    Bütün hasar x0.8 - x1.2, skor x0.6 - x2.0
  - vurulunca kombo kırılır (kombo skoru çarpıyor)
  - KUSURSUZ KAÇIŞ: atılırken darbeyi boşa çıkar: kısa ağır çekim, odak,
    2.5 sn +%25 hasar
  - SAVUŞTURMA: bonk yakındaki düşman mermilerini geri yollar
  - elitler (5. dalgadan) yere vurur, nişancılar (8. dalgadan) havan atar:
    düşecekleri yer işaretli ve gittiğin yöne nişan alıyorlar
  - taban skor kısıldı: dikkatsiz oyun eskisinin ~üçte biri, iyi oyun daha
    fazlası
- 2 KİŞİLİK: evrim, güç sunakları, 5 harita bulgusu ve kayıp kervan artık 2
  kişilikte de var; başında duran oyuncu alır, eller ve evrimler kişiye özel
- Noel menüsü kalıcı
- karakter: gölgeli gövde, yürürken basan ayaklar, göz kırpma; Taş Meydan
  zemininde "kareli defter" ızgarası kalktı, taşlara doku
- silahı henüz açılmamış oyuncuya da Silah Rafı kart verir (verecek kart
  yoksa altın)
- tüccar ipucu da üstteki not satırında (sol paneli örtüyordu); pencere
  açıkken arkadaki notlar gizlenir
- 2 KİŞİLİK GECİKME: iki oyun artık birbirine DOĞRUDAN bağlanmayı dener (UDP,
  NAT delik açma, IPv6). Kurulursa mesajlar sunucuya uğramaz: aynı şehirde
  ~130 ms yerine ~20-40 ms. Kurulamazsa sunucu yolundan devam eder; doğrudan
  yol koparsa sunucuya geçer, düzelince kendiliğinden geri döner. Lobide ve
  oyunda bağlantı türü yazıyor
- 2 kişilik: görüntü 15 -> 30 Hz, konuk girdisi 30 -> 60 Hz, çizim gecikme
  tamponu yarıya indi (yaratıklar daha güncel görünür)
- açılıştaki takılma: sesler ilk açılışta bir kez üretilip diske yazılıyor,
  sonraki açılışlar anında; üretim sırasında menü artık donmuyor
- OYUN 2 KAT UZUN: 25 dalga normal 70 dk, zor 60, kabus 40. Yaratık başına
  tecrübe/altın ve skor yarıya indi: dalga başına güçlenme ve sıralama aynı
- DENGE: oyuncu bir dalga için olağandan güçlüyse yeni yaratıklar daha canlı
  gelir (güçlü takımla 25. dalgada yaratıklar kâğıt gibiydi). 2. patrondan
  itibaren her patron dövüşü daha uzun, darbesi daha sert; 1. patron aynı
- SİLAH EVRİMİ yenilendi: her silahın kendine has evrimi (20 ayrı etki: kalkan
  dalgası, işaretleme, sersemletme, buz kesme, infaz, savurma, ruh yığını,
  kanama, artçı sarsıntı...). Şart Lv.10 + eş kitap Lv.3 (nadir kitap: elde
  olsun) + en az 3 silah; koşuda en çok 2 evrim; hasar payı x1.25
- HARİTA BULGULARI (iyi koşu / kötü koşu): her koşuda bazıları çıkar, bazıları
  hiç gelmez. SİLAH RAFI (erken, uzakta: epik silah kartları), TAŞTAKİ KILIÇ
  (4 sn başında dur: koşu boyunca +%15 hasar), DEMİRCİ ÖRSÜ (bir silahına +2
  seviye), MEYDAN OKUMA TAŞI (25 sn elit dalgasına dayan: sandık), HAZİNE
  HARİTASI (uzaktaki X'i kaz: altın + sandık). Küçük haritada ve kenar
  oklarında görünürler; kaçırılan bulgu bir süre sonra kaybolur
- Gök İşareti kaldırıldı
- KAYIP KERVAN: bazı koşularda 2-4. dalga arası haritadan bir kervan geçer;
  yakalarsan altın + bir el efsanevi kart, kaçarsa gider
- güç sunakları kaldı; altın yağmuru / kan ayı / göktaşı yağmuru kaldırıldı
- daha sakin ekran: flaş ve sarsıntı yarıya yakın, kalabalıkta küçük hasar
  sayıları ve parçacıklar kısıldı (düşman sayısı/hızı aynı)
- arayüz: kutuların kenarları düz, büyük başlıklarda harf aralığı, yazı
  konturu inceldi; düğmeler yine koyu, basılabilir eski hâlinde
- silahlık ayrıntısında uzun yazılar taşıyordu (Kasırga vb.), pencere artık
  yazıya göre büyüyor ve satır kırıyor
- kalabalıkta yaratıkların bir kısmı eski yöne bakıyordu (çizim sırası
  sondakilere hiç gelmiyordu); artık hepsi yürürken oyuncuya döner
- üstteki duyuru satırları koyu zemin üstünde: süzülen yazılar altına girse de
  okunuyor
- art arda gelen "COMBO x50! / x60!" yazıları üst üste binmiyor (eskisi silinir)
- gözlük gözü kapatır, göz ve gözlük aynı yöne bakar; şapka/gözlüklere
  kontur ve ışıltı; markette eşya kendi karakterinde denenir
- Taş Meydan yaratıklarına arena donanımı (miğfer, sorguç, kalkan, tasma)
- arayüz baştan çizildi: yeni yazı tipi, kalın konturlu kartlar, sıcak renkler
- ₺ işareti kare kutu çıkıyordu, artık "TL" yazıyor

## 3.48
- 2 kişilikte katılan oyuncunun donma/gecikme sorunu düzeldi (akış denetimi, kopunca yeniden bağlanma, ping göstergesi)
- patronlar artık can kitabıyla geçiştirilemiyor: asgari darbe + sahada patron varken şifa azalıyor ("yara")
- önceki patron yaşarken yenisi gelmiyordu, düzeldi
- cehenneme 25'ten sonra giren oyuncu yanlışlıkla hileci sayılıyordu, düzeldi
- Kabus Avcısı başarımı 5. dalgadan 10. dalgaya çıktı

## 3.47
- dalgalar artık süreyle ilerliyor (25 dalga: normal 35 dk, zor 30, kabus 20; sonra 2 katına çıktı)
- patron dalgayı durdurmuyor
- 2 kişilik mod (beta, sadece PC ve Taş Meydan): oda kur, 6 harfli kodla katıl

## 3.46
- telefon: tam ekran, hızlı açılış, ağır sahnede 30 FPS'e düşüp geri çıkma, menüler önbellekli

## 3.45
- telefon sürümü (pygbag): dokunmatik joystick, otomatik nişan, ayrı mobil sıralama

## 3.44
- skinler seviyeyle güçleniyor, yeni skin: Kozmik Gezgin
- köşede kamp yapana da yaratık doğuyor
- hesap ekranına iletişim formu, yeni yerel skor tablosu, tanıtım filmi

## 3.43
- anahtarlı sandık (3 anahtar), yeni dünya sıralaması + koşu kartı
- ölüm ekranı yenilendi, kartopu etkinliği

## 3.42
- oyunun adı EvolveArena oldu (kayıtlar aynı yerde)
- kayıtta kurtarma e-postası zorunlu
- her haritanın kendi patronları, her patronun en az 5 yeteneği
- dünya 5x5, 30. dalgadan sonra mutantlar, haritalar güzelleşti

## 3.41 - 3.35
- patron uyarıları zemine çiziliyor
- yeni mağaza, 8 elmas paketi, 10 yeni pet
- sınırsız cehennem, harita kilitleri, şifremi unuttum
- geç oyun zorlaştı, tüccar ve lanetli sandık değişti
- .exe sunucuya bağlanamıyordu (sertifika), düzeldi
- her haritaya kendi yaratıkları, yeni OYNA ekranı
- hile açığı kapandı (hile anında sunucuya bildiriliyor)

## 3.34 - 3.29
- 4 harita, 12 yemin
- kitaplara nadirlik, 2 yeni kitap, deprem
- 10 yeni silah (şahin, yarasa sürüsü, kurtlar, hayalet kılıçlar...)
- lanetli sandık / gizli mağara, şans sistemi

## 3.28 - 3.26
- mağazada TL ile ödeme, kendi petini yap
- dalga temposu ve seviye/altın dengesi
- pelerinler yenilendi, yılbaşı menüsü, tanıtım filmi

## 3.21 - 3.17
- hesap sistemi (kullanıcı adı + Google), ilerleme hesaba bağlı
- 5 dil
- hile koruması, şifreli kayıt dosyası
- büyük harita (M)

## 3.16 ve öncesi
- kitap takımı, yeni HUD, istatistik paneli
- FPS sınırı ayarı (240'a kadar), petler
- büyük denge turu, yeni silahlar (emanet, pelerin, buz izi)
- seviye atlayınca silah seçme, silahlık ekranı
- patron yetenekleri, patron sandığı, cehennem
- harita 3x3, başarımlar, skin yetenekleri

## Kontroller
WASD / ok tuşları: yürü, fare: nişan, sol tık: ateş, Space: bonk,
Shift / sağ tık: dash, B: market, Tab: istatistik, E: portal, Esc: mola,
F11: tam ekran, F3: FPS
