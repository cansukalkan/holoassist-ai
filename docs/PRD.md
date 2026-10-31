# Ürün gereksinimleri

## Amaç ve kullanıcı

Öğrenci veya gözetimli laboratuvar kullanıcısı, tanımlı DC motor düzeneğini referans görüntüyle tanır, belirti seçer, kaynaklı olası nedenleri ve güvenli inceleme noktalarını görür. Sistem kesin teşhis veya otonom bakım yapmaz.

## Varsayımlar ve açık kararlar

- Tek geliştirici, 12 haftalık çalışma; süreler plan tahminidir.
- İlk düzenek akım sınırlı, düşük voltajlı eğitim donanımıdır. Motor modeli, besleme değerleri, parça listesi ve güvenli eşikler henüz bilinmiyor; üretici dokümanı olmadan sayısal eşik atanmayacak.
- İlk hedef iPhone; model, iOS sürümü ve Mac/Xcode erişimi henüz doğrulanmadı.
- İlk belirtiler: aşırı ısınma, dönmeme, olağandışı titreşim. Bunlar başlangıç senaryolarıdır; fiziksel doğrulama bekler.
- Türkçe arayüz; kaynaklar Türkçe/İngilizce olabilir. Çeviri orijinal kanıtı koruyacak.
- İlk kamera tanıma yöntemi referans görüntü/etiket. YOLO ancak lisanslı ve etiketli veri yeterliyse değerlendirilir.
- LLM modeli, bütçe, veri saklama süresi ve üretici kaynak lisansı açık kararlardır.

## MVP kabul kriterleri

| Kimlik | Davranış | Doğrulama |
|---|---|---|
| M1 | Referans ekipmanı tanır; bilinmeyen veya düşük güvende analiz durur | Ayrılmış bilinen/bilinmeyen görüntüler |
| M2 | En az dört uzman düğüm koordineli çalışır: Knowledge, Diagnostic, Data, Safety | Yapılandırılmış durum ve düğüm izleri |
| M3 | Teknik iddialar doküman/sürüm/sayfa veya bölüm/kanıt kimliği taşır | İnsan tarafından kaynak eşleştirmesi |
| M4 | Belirtiye göre en çok üç olası neden ve eksik kanıt gösterilir | Etiketli senaryo değerlendirmesi |
| M5 | İzin verilen adımlar önceden tanımlı parça anchor'larında görünür | Gerçek cihaz kontrolü |
| M6 | Kaynaksız adımlar engellenir; kritik işlem kalıcı insan onayı bekler | Negatif ve resume/replay testleri |
| M7 | Takip kaybında işaretçiler gizlenir ve yürütme durur | Kamera kapatma/nesne kaybetme deneyi |
| M8 | Simülasyon ve ölçüm açıkça ayrılır | JSON ve UI kontrolü |

## Kapsam dışı

Genel endüstriyel ekipman tanıma, şebeke gerilimiyle bakım, canlı elektrik müdahalesi, otonom kontrol, serbest LLM koordinatlarıyla AR yerleştirme ve üretim ortamı sertifikasyonu.

## Veri ve gizlilik

Kamera görüntüsü varsayılan olarak kalıcı saklanmaz. Harici modele gönderim öncesi veri akışı görünür olmalı; görüntü boyutu/türü sınırlandırılmalı. Dokümanlar izin/lisans kaydıyla alınır. Loglar anahtar ve kişisel bilgi içermez. Saklama süresi kararı veri toplama öncesi kapatılır.

## İlk aşama çıkış kapısı

Belgeler, klasörler, kurulabilen Python paketi ve anahtarsız test altyapısı hazır; bağımlılık kontrolünün kapsamı kayıtlı. Bu kapı MVP özelliklerinin tamamlandığı anlamına gelmez.
