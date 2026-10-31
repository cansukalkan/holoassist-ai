# Proje durumu

21 Ekim 2026: Bu rapor T11 yerel API ve görsel demo prototipinden sonra güncellenmiştir. Tamamlanan işler çalıştırılabilir kodla doğrulandı; haftalar takvimsel ilerleme yüzdesi değildir.

| Aşama | Durum | Oluşturulanlar |
|---|---|---|
| Kapsam ve mimari | Hazır | DC motor MVP sınırı; PRD, ARCHITECTURE, ROADMAP, EVALUATION, AGENTS ve TASKS |
| Geliştirme altyapısı | Çalışıyor | Git deposu, Python 3.12 venv, paketleme, Pytest, Ruff, kontrol script'i, bağımlılık raporları/kilit kayıtları |
| T02 veri sözleşmeleri | Tamamlandı | Evidence, Observation, ObservationSeries; kaynak, birim, UTC, provenance ve sıra doğrulamaları |
| T03 doküman parçalama | Tamamlandı | JSON kaynak girişi, sayfa/bölüm koruma, SHA-256, kararlı parça kimlikleri, sentetik fixture ve CLI |
| T04 indeksleme ve arama | Baseline tamamlandı | Kalıcı gerçek Chroma, çevrimdışı sözcük vektörleri, kaynaklı sonuç, ekipman filtresi, kaynak ayrımı ve CLI |
| T01 gerçek düzenek ve doküman | Bilgi bekliyor | Motor modeli, üretici kılavuzu, izin/lisans ve donanım sınırları henüz kesinleşmedi |
| T05 referans görüntü tanıma | Sentetik prototip çalışıyor | OpenCV ORB/RANSAC, eşleşme/izdüşüm kapıları, kimlik vermeden ret, CLI ve demo; gerçek kamera/motor doğrulaması bekliyor |
| T06 state/Supervisor | Sınırlı prototip tamamlandı | LangGraph ile üç düğümlü sonlu akış, kaynak adapterı, hata ve eksik bilgi duruşu, trace |
| T07 Knowledge/Diagnostic | Sentetik Diagnostic prototipi hazır | Kaynak adapterının çıktısına katalogla bağlı destek/karşıt kanıt değerlendirmesi; LLM ve gerçek motor teşhisi yok |
| T08 sensör analizi | Bağımsız prototip çalışıyor | Ortalama/min/max/medyan, gerçek zamanlı eğim ve MAD aykırı adaylar; provenance/kalite kapıları; graf/Diagnostic entegrasyonu henüz yok |
| T09 kaynak/gösterim kapısı | Bağımsız sentetik prototip hazır | Katalog/ekipman/parça/kaynak/takip kontrolü, kritik/yasak risk reddi, atomik metin gizleme; fiziksel bakım izni yok |
| T10 kalıcı onay | Bağımsız sentetik prototip hazır | SQLite snapshot/audit, yerel izin listesi, digest/süre/tek kullanım kontrolü; LangGraph resume ve üretim kimlik doğrulaması yok |
| T11 API ve Web Platformu | Tamamlandı (Sentetik kapsam) | FastAPI değerlendirme, sensör, tanı, 3D anchor (`/v1/demo/spatial/*`), benchmark (`/v1/demo/evaluation`) ve `/` + `/demo` web arayüzleri |
| T12–T14 Unity 3D & Anchor | Sentetik prototip tamamlandı | Unity 6 UI Toolkit 3D denetim istasyonu + 9 EditMode testi (`T12`) ve `SpatialAnchorCatalog` bağlayıcısı (`T14`); fiziksel AR (`T13`) donanım bekliyor |
| T15 Sentetik Benchmark & Sunum | Sentetik doğrulama tamamlandı | İçerik adresli RAG önbelleği, `python -m holoassist.evaluation` tekrarlanabilir benchmark raporu ve `docs/PRESENTATION.md` jüri rehberi |

## Şu an uçtan uca çalışan bölüm

Sentetik JSON belge → kaynaklı parçalar → yerel Chroma indeksi → ekipmana göre sorgu → sayfa/bölüm ve alıntı içeren JSON sonuç.

Bu bölüm ağ, OpenAI API anahtarı, kamera veya Unity gerektirmez. Gerçek motor tanıma, arıza teşhisi ve AR bakım rehberliği henüz doğrulanmadı. Ayrı Vision akışı: sentetik referans + perspektifli görüntü → matched/unknown/low_confidence JSON ve piksel köşeleri. Vision sonucu ve Chroma araması sınırlı LangGraph yönlendirmesine bağlandı; entegrasyon sentetik veride test edildi. Çıktı yalnızca ready_for_diagnostic / needs_information / blocked; bakım rehberliği izni her zaman false.

## Doğrulama

312 test geçti: önceki 299 teste ek 7 storage yapılandırma testi ve 6 gerçek PostgreSQL entegrasyon testi. Docker PostgreSQL 17.11 konteyneri healthy; ilgili altı entegrasyon testi ayrıca konteyner üzerinde geçti. Ruff ve pip check başarılı. Kalıcılık ayrı Python süreçleri arasında test edildi. Fiziksel motor/iPhone testi veya gerçek üretici korpusuyla arama kalitesi ölçümü yapılmadı.

## Yol haritasındaki konum

1. haftanın Python altyapısı ve mimari çıktıları hazır; Unity Editor projesi oluşturulmadı. 2. haftanın sentetik doküman alma/parçalama/indeksleme/arama prototipi hazır. Gerçek üretici verisi ve kaynak doğruluğu değerlendirmesi olmadan 2. hafta tamamen tamamlandı sayılmaz.

T05 için sentetik referans tanıma prototipi hazır; gerçek ekipman doğrulaması için motor modeli ve referans görüntüleri gerekir. T06 AnalysisState ve sınırlı Supervisor tamamlandı. T07 sentetik prototipinde kaynaklı hipotez ve çelişki raporu hazır; gerçek motor/LLM tabanlı teşhis ve grafa Diagnostic entegrasyonu bekliyor. T08 sensör serisi analiz prototipi hazır. T09 kaynak/gösterim kapısı sentetik veride hazır. T10 kalıcı demo inceleme/onay ve bağlam/replay kontrolü hazır. Sonraki bağımsız adım T11 minimal API ve Unity veri aktarım sözleşmeleri; onay güncellemelerini ağdan açmadan önce backend kimlik doğrulaması tasarlanmalıdır. Gerçek bakım talimatları motor dokümanı gelmeden hazırlanmayacak. Tam çok ajanlı teşhis, Safety ve AR uygulaması henüz yoktur.



T07 demo: kaynaklı AnalysisState → sentetik katalog değerlendirmesi → iki doğrulanmamış olasılık ve ayrı destek/karşıt kaynaklar. Bu modül grafın içine bağlanmadı; bağımsız değerlendirme adımıdır. Detaylar docs/DIAGNOSTIC.md içinde.


T08 demo: simulated ObservationSeries → betimsel istatistikler + süre/eğim + göreli aykırı adaylar. Modül güvenli/arıza kararı vermez ve henüz Diagnostic/graf akışına bağlanmadı. Kullanım docs/ANALYTICS.md içinde.


T09 demo: hazır AnalysisState + seçilen adımlar + sentetik katalog → display_allowed / needs_information / needs_approval / blocked. Sadece bilgilendirme kartı gösterimi açıktır; guidance_allowed her zaman false. Kritik veya uygunsuz bir adım tüm plan metinlerini ve alıntılarını gizler. Ayrıntılar docs/SAFETY.md içinde.


T10 demo: kalıcı pending inceleme → izinli geliştirme kimliğiyle approved → bağlamı yeniden doğrulama → bir kez tüketilen demo devam kaydı. İkinci kullanım reddedilir, fiziksel guidance_allowed=false kalır. Bu uygulama checkpoint'idir; LangGraph checkpointer/resume henüz bağlanmadı. docs/APPROVALS.md ayrıntıları açıklar.


PostgreSQL/Docker eklemesi: Compose PostgreSQL servisi, Psycopg backend ve açık sqlite/postgres seçimi hazır. Gerçek PostgreSQL 17.10 testleri izole yerel kümede geçti; Docker PostgreSQL 17.11 konteyneri çalışıyor; approvals/approval_events tabloları ve sentetik bekleyen inceleme kaydı oluşturuldu, altı entegrasyon testi geçti. Ayrıntılar docs/POSTGRES_DOCKER.md içinde.


T11 ilk API parçası: 11 yeni HTTP testi, toplam 317 geçti / 6 seçilmeyen PostgreSQL testi; Ruff ve pip check temiz. API veritabanı değişikliği yapmaz. Kullanım docs/API.md içinde.

T11 ikinci parça: yerel operator/reviewer Bearer kimlikleri, kalıcı open/get/context/decision API; 339 test Docker PostgreSQL dahil geçti. HTTP demo pending kayıt oluşturdu, onay vermedi. Üretim kimliği ve fiziksel izin yok. Yetkili demo 127.0.0.1:8001/docs, ayrıntı docs/API.md.

T11 üçüncü parça: /ready kalıcı tablo erişimini doğrular; 64 KiB gerçek bayt sınırı endpoint öncesinde uygulanır. Tam koşu 351 geçti (Docker PostgreSQL dahil), son middleware düzeltmesinden sonra ilgili 38 API testi tekrar geçti. Çalışan 8001 sunucusunda gerçek HTTP reachable/413 JSON doğrulandı. Sıradaki görsel adım yerel demo sonuç ekranı; gerçek motor ve üretici dokümanı hâlâ bekleniyor.

Yerel görsel demo hazır: http://127.0.0.1:8001/demo. Kaynaklı bilgi kartı ve üç engelleme senaryosu gerçek tarayıcıda doğrulandı. 357 test Docker PostgreSQL dahil geçti; statik dosyalar wheel paketinde doğrulandı. Unity/AR uygulaması oluşturulmadı; geçiş planı docs/UNITY_HANDOFF.md, ekran açıklaması docs/DEMO_UI.md.

Sensör demo paneli: Akım/Sıcaklık/Titreşim grafiği, backend istatistikleri ve ham örnek tablosu hazır. Üç sekme tarayıcıda doğrulandı; veri simulated kaldı. 370 test Docker PostgreSQL dahil geçti, Ruff/pip check temiz. /v1/demo/sensors/{sensor} salt okunur adapter; Diagnostic/graf ve gerçek cihaz entegrasyonu hâlâ yok.

Kaynaklı test olasılıkları paneli hazır. Kayıtlı sentetik Diagnostic sonucu HTTP/görsel adapterına bağlandı; destek/karşıt kayıtlar ve eksik karşıt kanıtta tüm olasılıkların gizlenmesi tarayıcıda doğrulandı. 377 test Docker PostgreSQL dahil geçti; Ruff/pip check temiz. Canlı retrieval, sensör-Diagnostic veya tam ajan akışı eklenmedi. Gerçek motor/üretici kaynağı bekleniyor.

Docker uygulama kurulumu hazır: API + PostgreSQL healthy, demo 127.0.0.1:8002/demo. Mevcut PostgreSQL volume korundu; API restart sonrası sentetik pending onay kaydı tekrar okundu. 380 test Docker PostgreSQL dahil geçti; imajda resolver/pip check ve sırların build context dışında kaldığı doğrulandı. docs/DOCKER_APP.md.

T01 metadata hazırlığı: kullanıcı motor seçmediğini doğruladı. Boş sürümlü ekipman şablonu ve host/Docker CLI eksik bilgi raporu hazır; gerçek model veya limit atanmadı. 13 yeni testle toplam 393 test Docker PostgreSQL dahil geçti; Ruff/pip check temiz. Güncel API konteyneri healthy/ready. T01 fiziksel kaynak/donanım doğrulaması hâlâ açık. docs/EQUIPMENT_INTAKE.md ve docs/examples/equipment-intake-result.json.

Demo raporu dışa aktarma hazır: seçilen bağımsız güvenlik/sensör/Diagnostic bölümleri sürüm 1.0 JSON dosyasında korunur. Fiziksel izin yok, sunucuda kayıt açılmaz. 406 test Docker PostgreSQL dahil geçti; gerçek HTTP örneği ve tarayıcı indirme isteği doğrulandı. docs/DEMO_EXPORT.md.

31 Ekim 2026 güncellemesi: Kurumsal Web platformu (`/` ve `/demo`), Unity 6.3 LTS UI Toolkit 3D denetim istasyonu + EditMode testleri (`T12`), sürümlü 3D uzamsal anchor projeksiyonu (`T14`, `/v1/demo/spatial/{scenario}`), içerik adresli RAG LRU önbelleği (`holoassist.rag.cache`), tekrarlanabilir dondurulmuş sentetik benchmark paketi (`T15`, `python -m holoassist.evaluation`, `/v1/demo/evaluation`, `docs/examples/synthetic-benchmark-report.json`) ve jüri/staj teknik sunum rehberi (`docs/PRESENTATION.md`) tamamlandı. Fiziksel motor (`T01`) ve mobil kamera AR takibi (`T13`) açık donanım kapıları olarak korunmaktadır.
