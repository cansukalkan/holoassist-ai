# Yerel demo ekranı

Ürün ve mimari sayfası: http://127.0.0.1:8001/ · İnceleme konsolu: http://127.0.0.1:8001/demo

Aynı FastAPI sunucusu HTML/CSS/JS dosyalarını paket içinden sunar. Ayrı Node/frontend kurulumu veya harici servis yoktur. Ekran dört sentetik seçimi mevcut değerlendirme endpoint'ine gönderir: bilgi kartı, kritik adım, takip kaybı, katalogla uyuşmayan parça. Backend kaynak ve karar kontrolünün sahibidir.

Ekran gösterim durumunu, Türkçe gerekçeyi, doküman sürümünü, sayfa/bölümü ve kanıt kimliğini gösterir. Her sonuçta sentetik etiketi ve fiziksel işlem izninin kapalı olduğu korunur. Senaryo değişince eski içerik hemen kaldırılır; geç dönen yanıt yeni seçimi ezemez. Bağlantı hatasında önceki kart gizlenir. Dinamik içerik textContent ile eklenir; belge metni HTML olarak yürütülmez. CSP yalnızca aynı sunucunun script/style bağlantılarına izin verir. API erişim anahtarları tarayıcıya gönderilmez.

Bu ekranda kayıt açma, onay verme, gerçek görüntü tanıma veya AR yoktur. Motor çizimi temsili SVG'dir. /ready yalnızca tablo erişimini gösterir; ölçüm veya gerçek cihaz doğrulaması anlamına gelmez.

Tarayıcıda dört senaryo elle doğrulandı: bilgi kartı kaynakla göründü; kritik/takip/parça uyuşmazlığında metin gizlendi. Tablet genişliğindeki gerçek önizleme incelendi; ayrı telefon/cihaz testi yapılmadı. Ekran görüntüsü examples/demo-screen.png içinde. 6 yeni HTTP/statik erişim testiyle toplam **357 test geçti**, Docker PostgreSQL entegrasyonları dahil. Ruff/pip check temiz. Wheel paketi üretildi ve üç statik dosyanın içinde olduğu kontrol edildi. Yeni çalışma zamanı bağımlılığı yok.

## Sensör paneli

Demo ekranının üçüncü bölümü Akım/Sıcaklık/Titreşim sekmeleriyle sunucudaki sabit sentetik serileri gösterir. İstatistikler mevcut analyze_series modülünde hesaplanır; tarayıcı ortalama veya aday kararını yeniden hesaplamaz. Grafik x ekseninde örnek sırası yerine başlangıçtan geçen saniyeyi kullanır. Y ekseni veriye göre ölçeklenir ve çalışma sınırı olarak sunulmaz. Turuncu nokta MAD tabanlı istatistiksel adaydır. Seriler canlı ölçüm değildir; simulated etiketi her zaman görünür.

Min/max/ortalama, örnek sayısı ve açılabilir ham veri tablosu vardır. Her serinin sensör kimliği, UTC başlangıcı ve fixture SHA-256 özeti korunur. Kalite sorunu olduğunda API kısmi istatistik üretmez, ekran grafik/özeti gizler. Sekme değişiminde önceki grafik kaldırılır, eski/geç yanıt yeni sekmeyi ezmez.

Tarayıcı kontrolünde üç sekme ve ham tablo doğrulandı. Akım: 0.65 A ortalama, 4. örnek aday; sıcaklık: 30 °C ortalama; titreşim: 0.12 m/s² ortalama. Aday işaretlenmemesi güvenlik sonucu değildir. Görüntü examples/sensor-panel.png, gerçek HTTP çıktısı examples/api-sensor-current.json. 13 yeni sensör API/sözleşme testiyle toplam 370 test Docker PostgreSQL dahil geçti; Ruff/pip check temiz. Yeni bağımlılık yok. Tam ajan, fiziksel cihaz, teşhis veya AR bağlantısı eklenmedi.

## Kaynaklı test olasılıkları paneli

Ekranın dördüncü bölümü iki senaryo sunar. Tüm test kayıtları seçiliyken iki doğrulanmamış katalog etiketi ve bunların kaynakları gösterilir. Destek ve karşıt alıntılar ayrı etiketlidir; sayfa/bölüm, doküman sürümü, checksum ve kanıt kimliği korunur. Çelişki yüzde güvene veya sıralamaya dönüştürülmez.

Karşıt kayıt eksik seçimi sunucuda yalnızca bu test için karşıt beyanla eşleşen parçayı değerlendirme girdisinden çıkarır; dosya veya veritabanını değiştirmez. Mevcut evaluate_hypotheses tüm test olasılıklarını gizler. Bu iki durum tarayıcıda doğrulandı. Görüntü examples/diagnostic-panel.png içinde.

GET /v1/demo/diagnostic/complete ve /missing_counter_evidence sabit, kayıtlı sentetik AnalysisState ve katalogla çalışır. Canlı Chroma araması, LLM çağrısı veya Supervisor çalıştırmaz; sensör panelinden veri almaz. Kaynak açıklamaları gerçek motor arıza nedenleri değildir; gerçek motor modeli, incelenmiş üretici dokümanı ve doğrulanmış sensör serisi hâlâ gerekir. Bakım adımı üretilmez. Ekranda kayıt/onay işlemi yoktur.

7 yeni HTTP testi; toplam 377 test Docker PostgreSQL dahil geçti. Ruff ve pip check temiz; yeni bağımlılık yok. Gerçek HTTP çıktıları examples/api-diagnostic-complete.json ve api-diagnostic-missing.json içinde.

Demo çıktısı JSON raporu indir düğmesiyle dışa aktarılabilir. Seçimler sunucuda yeniden değerlendirilir; mevcut ekrandaki eski yanıtların ekran görüntüsü değildir. Bölümler bağımsız ve sentetik kalır, bir bölüm hatasında dosya üretilmez. docs/DEMO_EXPORT.md.
