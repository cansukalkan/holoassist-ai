# Küçük geliştirme görevleri

Durum: aşama 1 altyapısı, T02 sözleşmeleri, T03 doküman parçalama, T04 Chroma arama + Hafta 11 içerik adresli LRU önbellek, T05 sentetik referans tanıma, T06 sınırlı LangGraph Supervisor, T07 tanı/çelişki matrisi, T08 sensör serisi analizi, T09 güvenlik kapısı, T10 kalıcı SQLite/PostgreSQL onay döngüsü, T11 FastAPI + kurumsal Web platformu, T12 Unity 6 UI Toolkit 3D denetim istasyonu + EditMode testleri, T14 3D uzamsal anchor projeksiyonu ve T15 tekrarlanabilir sentetik benchmark + jüri sunum rehberi hazır. T01 ve T13 fiziksel donanım/kaynak doğrulaması bekliyor.

| ID | Görev | Bağımlılık | Kabul testi |
|---|---|---|---|
| T01 hazırlık | Motor henüz seçilmedi; sürümlü metadata şablonu ve eksik bilgi kontrolü hazır, gerçek kaynak/donanım doğrulaması bekliyor | Kullanıcı/donanım bilgisi | Model ve kaynak sürümü/lisansı eksiksiz |
| T02 ✓ | Evidence, Observation ve ObservationSeries şemaları | T01: donanıma özgü doğrulama bekliyor | Eksik sayfa/bölüm, birim, provenance ve geçersiz zaman reddi |
| T03 ✓ | Küçük izinli doküman fixture'ı ve chunker | T02 | Sayfa/bölüm ve checksum korunur |
| T04 ✓ | Chroma adapter, kaynaklı retrieval ve içerik adresli LRU önbellek (`holoassist.rag.cache`) | T03 ✓ | Bilinen soru kaynağa gider; ekipmanlar arası sızıntı olmaz |
| T05 prototip ✓ | Referans görüntü tanıma adapter'ı | T01: gerçek ekipman doğrulaması bekliyor | Bilinmeyen ve düşük güven örnekleri reddedilir |
| T06 ✓ | AnalysisState ve sınırlı Supervisor yönlendirmesi | T02 | Hatalı state reddi, sonlu akış ve trace |
| T07 prototip ✓ | Knowledge/Diagnostic: sentetik katalogla kaynaklı hipotezler ve karşıt kanıt matrisi hazır; LLM ve Diagnostic graf entegrasyonu bekliyor | T04,T06 | Desteklenen ve çelişkili kanıtlar ayrılır |
| T08 prototip ✓ | Sentetik sensör fixture ve bağımsız veri analizi; Data/graf entegrasyonu bekliyor | T02 | Boş/NaN/sırasız veri ve birim hatası |
| T09 prototip ✓ | Bağımsız sentetik kaynak/gösterim kapısı; fiziksel Safety/graf entegrasyonu bekliyor | T07,T08 | Kaynaksız/bilinmeyen riskli adım engeli |
| T10 prototip ✓ | SQLite/PostgreSQL snapshot/onay ve tek kullanımlık demo devam kaydı; LangGraph resume ve üretim kimliği bekliyor | T09 | Replay, yetkisiz onay, değişmiş kanıt ve süreç yeniden başlatma |
| T11 ✓ | Sağlık, kaynaklı değerlendirme, 3D uzamsal projeksiyon, sentetik benchmark API ve yerel Bearer rol ayrımıyla kalıcı onay uçları | T10 | İstek doğrulama, idempotency, hata sözleşmesi |
| T12 prototip ✓ | Unity 6.3 LTS (`6000.3.9f1`) UI Toolkit 3D sentetik denetim istasyonu + Unity Test Framework EditMode testleri | T11 | C# sözleşme doğrulama, 3D parça vurgusu ve EditMode birim testleri |
| T13 donanım bekliyor | Fiziksel kamera/referans anchor ve gerçek cihaz takip kaybı ölçümü | T01, T12 + fiziksel cihaz | Gerçek iPhone/ARKit saha ölçümleri (cihaz olmadan başarı iddia edilmez) |
| T14 sentetik ✓ | Sürümlü 3D uzamsal anchor kataloğu (`holoassist.spatial`) ve Web/Unity kart bağlayıcı | T09, T12 | Bilinmeyen `part_id`, kritik gizleme ve `tracking: lost` bastırma testleri |
| T15 sentetik ✓ | Dondurulmuş sentetik benchmark (`holoassist.evaluation`) ve jüri sunum rehberi (`docs/PRESENTATION.md`) | T14 | Dondurulmuş sentetik veriyle tekrar üretilebilir JSON benchmark raporu |

**Şimdiki durum:** Yazılım, sözleşme, güvenlik kapısı, içerik adresli RAG önbelleği, 3D sentetik anchor projeksiyonu (`T14`), tekrarlanabilir sentetik benchmark (`T15`), kurumsal Web platformu (`/`, `/demo`) ve Unity 6 UI Toolkit 3D denetim istasyonu (`T12`) uçtan uca tamamlandı ve doğrulandı. `AGENTS.md` kuralları gereği fiziksel donanım ve lisanslı kılavuz gerektiren `T01` ve gerçek iPhone/ARKit kamera ölçümü gerektiren `T13` açık donanım kapıları olarak korunmaktadır; gerçek cihaz doğrulaması yapılmadığı açıkça etiketlenmiştir.
