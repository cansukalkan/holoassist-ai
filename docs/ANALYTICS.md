# T08 — Sensör serisi analizi prototipi

Sıcaklık, akım ve titreşim serileri için deterministik betimsel analiz eklendi. Bu adım motor arızası veya güvenli çalışma kararı vermez. Modül mevcut Supervisor/Diagnostic akışına henüz bağlanmadı; bağımsız olarak çalışır.

## Çalıştırma

Temel Python/Pydantic ortamı yeterlidir; yeni bağımlılık gerekmez.

```powershell
.\.venv\Scripts\python.exe -m holoassist.analytics --series datasets/fixtures/sensor-temperature.json
.\.venv\Scripts\python.exe -m holoassist.analytics --series datasets/fixtures/sensor-current.json
.\.venv\Scripts\python.exe -m holoassist.analytics --series datasets/fixtures/sensor-vibration.json
.\scripts\check.ps1
```

Giriş daha önce uygulanan ObservationSeries JSON sözleşmesidir. Her dosya yalnızca tek ekipman, sensör, ölçüm türü, birim ve provenance içerir; zaman kesin artar. Eksik değerler doldurulmaz, birimler dönüştürülmez ve örnekler sessizce sıralanmaz. CLI en fazla 5 MiB girdi, Python adapterı en fazla 100000 örnek kabul eder.

## Gerçek demo çıktısı (tamamı sentetik)

| Seri | Değer aralığı | Ortalama | Sonuç |
|---|---|---|---|
| Sıcaklık | 25–35 degC | 30 degC | 50 saniyede +10 degC; eğim +0.2 degC/s |
| Akım | 0.40–1.80 A | 0.65 A | 4. örnek istatistiksel aykırı aday |
| Titreşim | 0.11–0.13 m/s2 | 0.12 m/s2 | MAD yöntemiyle aykırı aday işaretlenmedi |

Bunlar gerçek ölçüm, motor çalışma sınırı veya fiziksel arıza kanıtı değildir. Akımın 4. örneği JSON'da sıfırdan başlayan `sample_indices=[3]` olarak belirtilir. İşaretlenmeyen seri güvenli veya hatasız ilan edilmez. Üretilen raporlar `docs/examples/sensor-*-result.json` dosyalarında bulunur.

## Hesaplananlar

Minimum, maksimum, örneklerin aritmetik ortalaması, medyan, ilk/son değer, son-ilk farkı, süre ve gerçek saniye koordinatlarıyla en küçük kareler doğrusal eğimi hesaplanır. Ortalama örnek ağırlıklıdır; düzensiz örneklemede zamana göre ağırlıklı ortalama değildir. Eğim birimi degC/s, A/s veya (m/s2)/s olarak döner. Positive/negative/zero eğimin işaretidir; serinin her adımda tek yönde ilerlediğini veya değişimin teknik açıdan önemli olduğunu göstermez.

En az 5 örnekte medyan mutlak sapma (MAD) tabanlı modified z-score hesaplanır: abs(0.6744897501960817 * (değer - medyan) / MAD) > 3.5. Bu istatistiksel aday işaretidir; motor eşiği, alarm veya sensör arızası değildir. İşaretlenen örnekler analizden çıkarılmaz; ortalama ve eğimi etkiler. Yöntem gerçek motor veri setiyle kalibre edilmedi.

5'ten az örnekte outlier status=insufficient_samples; MAD sıfırsa status=zero_mad döner. Bu durumlarda boş indis listesi “anomali yok” anlamına gelmez; yöntem çalıştırılamamıştır.

## Veri ve hata davranışı

- Tek örnekte needs_information; ortalama/eğim gibi kısmi istatistikler sunulmaz.
- Herhangi bir örnek suspect/invalid kalite taşıyorsa tüm seri için yeni veri istenir. Hangi örneklerin sorunlu olduğu indislerle korunur; örnekler sessizce atılmaz.
- Boş seri, NaN/sonsuzluk, eksik alan, sırasız/aynı zaman, farklı sensör/ekipman/provenance ve yanlış birimler sözleşmede reddedilir.
- Girdi sayıları sonlu olsa bile hesaplama float aralığını aşarsa blocked / numeric_range_unavailable döner. Kısmi veya sonsuz sayılı rapor üretilmez; bu durum ekipman arızası anlamına gelmez.
- Simulated/measured etiketi her raporda korunur. Measured beyanının gerçek fiziksel ölçüm olduğu ayrıca doğrulanmaz.
- `guidance_allowed=false` sabittir. Güvenli/tehlikeli veya kesin arıza sınıflandırması yapılmaz.
- CLI geçersiz girdide hata kodu 2 döndürür; güvenilmeyen payload veya özel değerler hata mesajına kopyalanmaz. Başarılı JSON, blocked/needs_information değerlendirmelerini de taşıyabilir; uygulama status alanını kontrol etmelidir.

## Mimari ve doğrulama

`analytics/series.py`: analyze_series; `contracts/analytics.py`: DataReport, SeriesStatistics, OutlierSummary; CLI: analytics/__main__.py. İlk analiz için standart kütüphanenin statistics/math araçları kullanıldı. Pandas gelecekteki büyük veri/CSV analizleri için planlanan opsiyonel bağımlılık olarak kalır; bu modül için kurulması gerekmez.

33 yeni test; düzensiz zaman aralıkları, eğim işareti, istatistiksel aday, sıfır MAD, kalite kapısı, tek/boş/NaN seri, zaman sırası, karışık bağlam, sayısal taşma, korunmuş provenance, birimler, JSON gidiş-dönüşü ve CLI hata gizleme dahil. Tam test sonucu docs/STATUS.md içinde tutulur. Gerçek motor, sensör veya iPhone ölçümü yapılmadı.

T08 yalnızca istatistiksel özet ve göreli aykırı örnek prototipi olarak hazırdır. Data Agent'ın grafa bağlanması ve Diagnostic hipotezlerinin bu kanıtlarla beslenmesi sonraki iştir.

T08 web gösterimi: üç sabit simulated fixture salt okunur /v1/demo/sensors/{sensor} endpoint'iyle demo ekranına bağlandı. Sürüm 1.0 SensorDemoResult seri/rapor kimliğini doğrular ve fixture checksum korur. Bu yalnızca HTTP/görselleştirme adapterıdır; Diagnostic/Supervisor/graf entegrasyonu değildir. docs/DEMO_UI.md sensör panelini açıklar.
