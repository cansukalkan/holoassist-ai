# Yerel sentetik API — T11 ilk parça

Depo kökünden başlatma:

```powershell
.\.venv\Scripts\python.exe -m uvicorn holoassist.api.app:local_app --factory --host 127.0.0.1 --port 8000
```

Etkileşimli şema: http://127.0.0.1:8000/docs. `GET /health` yalnızca süreç canlılığını bildirir; veritabanı hazır olma testi değildir.

`POST /v1/demo/safety/evaluate` sürüm 1.0 SafetyRequest alır ve SafetyReport döndürür. Örnek girdi `docs/examples/api-request.json`, çıktı `docs/examples/api-response.json`, OpenAPI `docs/examples/api-openapi.json`. Bunlar ileride Unity istemcisi için JSON sözleşme örnekleridir; Unity uygulaması oluşturulmadı.

```powershell
Invoke-RestMethod http://127.0.0.1:8000/v1/demo/safety/evaluate -Method Post -ContentType application/json -InFile docs/examples/api-request.json
```

Sunucu analizi ve kataloğu yerel, sabit sentetik fixture dosyalarından yükler. İstemci kaynak, katalog, onay veya kullanıcı kimliği gönderemez; fazladan alanlar 422 ile reddedilir. Hatalar gönderilen değerleri yansıtmaz. Bilgilendirme kartları kaynak/sayfa/sürüm/kanıt kimliğiyle döner. Kritik adımlar needs_approval, bilinmeyen adımlar blocked olur; reddedilen planın metni ve alıntıları gizlenir. guidance_allowed her zaman false kalır.

Bu API salt değerlendirme yapar ve veritabanını değiştirmez. Aynı girdi aynı sonucu verir. PostgreSQL onay kaydı açma/karar/tüketim bu HTTP sürümüne bağlanmadı; mevcut yerel CLI ile çalışır. Kimlik doğrulaması ve yetkilendirme tasarlanmadan onay güncelleme endpoint'i açılmaz. İstek kaydı/idempotency anahtarı, API kimlik doğrulaması, hız sınırları ve dağıtım T11'in sonraki parçalarıdır. Yalnızca localhost geliştirme kullanımı içindir; ağda yayınlama komutu verilmez.

11 HTTP testi TestClient ile süreç içinde çalışır; ağ, LLM, anahtar ve veritabanı gerekmez. Sağlık, deterministik tekrar, kaynak koruma, kritik/bilinmeyen/takip kaybı engelleri, fazladan alanlar, bozuk JSON ve onay endpoint'inin bulunmaması doğrulanır.

## Kalıcı onay API — T11 ikinci parça

```powershell
# Mevcut .env sırlarını korur; ayrı iki rastgele geliştirme anahtarı ekler, yazdırmaz.
.\scripts\init-api.ps1
.\.venv\Scripts\python.exe -m uvicorn holoassist.api.app:local_review_app --factory --host 127.0.0.1 --port 8001
# Sunucu açıkken: anahtarları yerel .env dosyasından okur; ekrana veya çıktıya yazmaz.
.\.venv\Scripts\python.exe scripts/demo-api-review.py
```

Etkileşimli API: http://127.0.0.1:8001/docs. Önceki salt değerlendirme sunucusu 8000 üzerinde ayrı çalışabilir. local_review_app açıkça seçilmedikçe onay endpoint'leri eklenmez. Kimlik bilgileri eksik, kısa veya aynıysa sunucu başlamaz. `.env` ve süreç ortamı backend seçer; süreç ortamı önceliklidir. Mevcut yerel kurulum PostgreSQL kullanır. Bağlantı arızasında SQLite'a geçilmez.

| Endpoint | Rol | Sonuç |
|---|---|---|
| POST /v1/demo/reviews | operator | Sunucudaki analiz/katalogla kritik sentetik inceleme açar |
| GET /v1/demo/reviews/{approval_id} | operator veya reviewer | Kalıcı durum ve bağlam özeti |
| GET /v1/demo/reviews/{approval_id}/context | reviewer | İncelenecek snapshot ve kaynaklar |
| POST /v1/demo/reviews/{approval_id}/decision | reviewer | Digest eşleşiyorsa pending kaydı approve/reject yapar |

İnceleme açma gövdesi: `{"schema_version":"1.0","selection":SafetyRequest,"ttl_seconds":900}`. Karar gövdesi: `{"schema_version":"1.0","decision":"approve","expected_context_digest":"<snapshot digest>"}`. Kullanıcı kimliği gövdeden alınmaz; Bearer anahtarı sunucudaki `local-api-operator` veya `local-api-reviewer` kimliğine bağlıdır. Karar ve kimlik audit kaydına kalıcı yazılır. Operatör karar veremez, reviewer inceleme açamaz. İnceleyici snapshot'ı görüp digest ile karar verir.

Aynı review_id ve bağlam aynı kaydı döndürür. Aynı kimlikte değişmiş bağlam 409 olur. Tekrar open TTL'yi yenilemez. Karar yalnızca pending ve süresi geçmemiş kayda uygulanır; tekrar karar veya yanlış digest 409 olur. Kayıt yoksa 404, kimlik doğrulanmıyorsa 401, rol yetmiyorsa 403, storage arızasında 503 döner. Hata gövdeleri schema_version/code içerir; istek değerleri ve sürücü hataları yansıtılmaz.

Bu, iki paylaşılan geliştirme anahtarıyla yerel rol ayrımıdır; bir kişinin gerçek kimliğini veya insan varlığını doğrulayan üretim giriş sistemi değildir. Roller bu tek yerel demo alanındaki kayıtları paylaşır; kullanıcı/kurum bazlı sahiplik yoktur. Anahtarlar `.env` içindedir, Unity'ye gömülmez. Rotasyon için anahtarı değiştirip API'yi yeniden başlatın. Üretim OIDC/OAuth, token süresi/iptali, TLS, hız sınırları ve kullanıcı bazlı erişim sonraki dağıtım çalışmalarıdır.

Demo script yalnızca sentetik pending kayıt açar, reviewer bağlam erişimini ve operatörün karar verememesini kontrol eder; onay vermez. HTTP üzerinden resume veya fiziksel eylem endpoint'i yoktur. Approved kayıtta bile guidance_allowed=false kalır. Yerel CLI'nin izin listesi HTTP kimliğinden bağımsız yapılandırılır.

Doğrulama: **339 test geçti**, bunların 7'si gerçek Docker PostgreSQL entegrasyon testi. Yeni HTTP yetki/lifecycle testleri SQLite geçici dosyalarıyla süreç içinde çalışır. Ek PostgreSQL HTTP testi kendi rastgele test şemasında karar/audit/kalıcılık doğrular. Ayrıca çalışan localhost sunucusuna gerçek HTTP isteğiyle pending kayıt oluşturuldu: [çıktı](examples/api-postgres-review.json). Bu kayıt 15 dakika sonra süresi dolmuş olarak değerlendirilir. Ruff ve pip check temiz. Yeni bağımlılık eklenmedi.


## Hazır olma ve istek sınırı — T11 üçüncü parça

`GET /ready` onay sunucusunda iki kalıcı tabloya sorgu gönderir, inceleme/audit durumunu değiştirmez. Erişim varsa storage=reachable, arıza varsa 503 ve schema_version/code içeren storage_unavailable döner. Salt değerlendirme factory'si storage=not_configured bildirir. `/health` yalnızca sürecin canlılığını bildirir. Bu kontrol şema migration uyumluluğunu veya üretim yetki tasarımını doğrulamaz.

Tüm HTTP gövdeleri JSON ayrıştırılmadan ve endpoint çalışmadan önce en fazla 64 KiB ile sınırlandırılır. Gerçekte alınan baytlar sayılır; Content-Length olmadan parçalı aktarım veya yanlış uzunluk alanı sınırı aşamaz. Büyük istek 413/request_too_large, geçersiz/tekrarlanan Content-Length ASGI sınırında 400 olur. Uvicorn protokol katmanı geçersiz HTTP çerçevelerini daha erken reddedebilir. Sınır, sunucunun aldığı tek ağ parçasının boyutunu değiştirmez; uygulamanın biriktirdiği gövdeyi sınırlar. Rate limit ve yavaş aktarım zaman aşımı bu parçaya dahil değildir.

OpenAPI hata şemaları gerçek versioned hata yanıtlarıyla eşleştirildi. Güncel yetkili OpenAPI: examples/api-review-openapi.json. Gerçek localhost HTTP çıktısı: examples/api-readiness-result.json. 351 testlik tam koşu Docker PostgreSQL dahil geçti; gerçek HTTP'de saptanan erken bağlantı kapanması düzeltildikten sonra ilgili 38 API testi tekrar geçti. Gerçek HTTP ile reachable ve 413 JSON gövdesi ayrıca doğrulandı. Yeni bağımlılık yok.

## Salt okunur sensör demo endpoint'i

`GET /v1/demo/sensors/{sensor}` yalnızca current, temperature, vibration seçimlerini kabul eder. Sunucu datasets/fixtures/sensor-*.json dosyalarını izinli seçimle yükler, ObservationSeries doğrulamasından sonra mevcut analyze_series modülünü çağırır. Kullanıcı dosya yolu veya seri gövdesi alınmaz. Eksik/bozuk/1 MiB üstü fixture ve measured kökeni bu demo endpoint'inde 503/sensor_demo_unavailable ile reddedilir. Kalitesi suspect/invalid olan geçerli seri needs_information ve boş istatistikle döner.

Sürüm 1.0 SensorDemoResult: fixture_id, fixture_checksum, scope=synthetic_demo, series ve report içerir. Sözleşme, serinin ve raporun ekipman/sensör/tür/birim/köken/örnek sayısı/zaman aralığını eşleştirir. Her ikisi simulated olmalıdır; report.guidance_allowed=false sabittir. Bu JSON uç noktası veri yazmaz, teşhis veya gösterim kapısı kararını değiştirmez.

13 yeni test: üç fixture sonucu ve checksum, deterministik tekrar, bilinmeyen dosya seçimi, measured reddi, kalite kapısı, eksik/bozuk fixture hata gizleme, rapor-seri bağı ve POST reddi. Toplam 370 test Docker PostgreSQL dahil geçti.

## Kaynaklı olasılık demo endpoint'i

GET /v1/demo/diagnostic/complete ve /v1/demo/diagnostic/missing_counter_evidence, kayıtlı sentetik analize mevcut Diagnostic katalog değerlendiricisini uygular. Sürüm 1.0 DiagnosticReport döner. Destek/karşıt kanıt bağı korunur; karşıt kayıt eksikse tüm olasılıklar gizlenir. Kaynaklar sunucuya aittir; client analiz/snapshot veya dosya yolu veremez, POST yoktur. Bozuk/eksik fixture 503/diagnostic_demo_unavailable, bilinmeyen senaryo 422 olur. Bu bir canlı teşhis veya çok ajanlı akış endpoint'i değildir. Ayrıntı docs/DIAGNOSTIC.md içinde.

GET /v1/demo/report seçili bağımsız sentetik bölümleri JSON attachment olarak dışa aktarır. safety/sensor/diagnostic parametreleri izinli enum değerleridir; no-store uygulanır, kaynak kimlikleri ve gizleme kararları korunur. Yeni onay veya kalıcı kayıt oluşturulmaz. Sözleşme ve sınırlar docs/DEMO_EXPORT.md içinde.
