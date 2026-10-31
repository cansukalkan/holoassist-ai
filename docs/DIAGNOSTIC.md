# T07 — Kaynaklı Diagnostic prototipi

Bu adım, mevcut Knowledge/Chroma kaynak aramasının ardından ayrı çalışan deterministik bir Diagnostic değerlendirme modülü ekler. Kaynaklı olasılık listesi ve karşıt kanıt üretir. LLM, gerçek motor teşhisi ve tam çok ajanlı iş akışı henüz yoktur.

## Çalıştırma

Mevcut `dev,rag,orchestration` ortamı yeterlidir; yeni bağımlılık eklenmedi.

```powershell
.\.venv\Scripts\python.exe -m holoassist.rag.search --db data/diagnostic-demo-chroma --source-kind synthetic index datasets/fixtures/synthetic-diagnostic.json
.\.venv\Scripts\python.exe -m holoassist.agents --request datasets/fixtures/analysis-request.json --db data/diagnostic-demo-chroma > data/diagnostic-analysis.json
.\.venv\Scripts\python.exe -m holoassist.agents.diagnostic --analysis data/diagnostic-analysis.json --catalog datasets/fixtures/diagnostic-catalog.json
```

Windows PowerShell 5 yerine PowerShell 7 kullanın veya JSON çıktısını UTF-8 olarak kaydedin. CLI input JSON UTF-8/UTF-8-BOM kabul eder. Önceden çalıştırılmış çıktılar `docs/examples/diagnostic-analysis.json` ve `docs/examples/diagnostic-result.json` içinde bulunur.

## Demo çıktısının anlamı

Belirti: overheating. Tamamen uydurulmuş iki test etiketi değerlendirilir:

| Test olasılığı | Belirsizlik | Kaynak |
|---|---|---|
| demo_environment_state | unverified: doğrulanmadı | Sentetik kaydın 3. sayfası |
| demo_load_state | conflicting_evidence: çelişkili kanıt var | Destek: sayfa 3; karşıt kayıt: sayfa 4 |

Bunlar gerçek motorun olası nedenleri değildir. Demo metni sadece kaynak eşleştirmeyi, çelişkiyi korumayı ve ek bilgi istemeyi test etmek için yazılmıştır. Çıktı `source_kind=synthetic` ve `guidance_allowed=false` taşır. Gerçek motor modeli, incelenmiş üretici kaynağı ve doğrulanmış sensör serisi hâlâ eksiktir.

## Sözleşmeler ve davranış

`DiagnosticCatalog`, tek ekipman için en fazla üç kural içerir. Katalog yalnızca synthetic_demo kapsamını kabul eder; real modunda değerlendirme bloke edilir. Kural, desteklediği belirtinin yanı sıra açıklama, eksik bilgi alanları ve en az bir destekleyen kaynak beyanı taşır.

Her `SourceAssertion` belge kimliği, sürüm, checksum, sayfa/bölüm, tam alıntı ve supports/contradicts ilişkisi taşır. Modül yalnızca aynı kaynaktan ve konumdan alınmış parçada alıntının aynen bulunduğunu doğrular. Sözcük arayarak otomatik teknik çıkarım yapmaz. İlişki ve açıklama katalog yazarı tarafından tanımlanır; bunların doğruluğu otomatik olarak kanıtlanmış sayılmaz.

- Yalnızca ready_for_diagnostic AnalysisState değerlendirilir; giriş tekrar doğrulanır.
- Belirti için kural yoksa needs_information döner.
- Seçilen kuralın herhangi bir destekleyen veya karşıt alıntısı eksikse tüm hipotezler gizlenir ve eksik source_for kimlikleri listelenir. Bilinen karşıt kanıtın arama sonucuna girmemesi sessizce yok sayılmaz.
- Her hipotez destekleyen/karşıt evidence_id listelerini ayrı taşır. Her alıntı eşleşmesinde belge/sürüm/checksum/sayfa/bölüm ve tam alıntı korunur.
- Çelişki varsa uncertainty=conflicting_evidence; aksi durumda unverified. Yüzde güven veya kesin teşhis sunulmaz.
- Aynı parça hem destek hem karşıt ifade içerebilir; ilişkiler ayrı alıntılarla korunur.
- Hipotez sırası kod adına göredir, olasılık sırası değildir.
- Katalogda tanımlanmamış çelişkiler keşfedilmez. Katalog kapsamı ve kaynak metninin anlamsal doğruluğu insan incelemesi gerektirir.
- Sonuç bakım talimatı veya insan onayı yetkisi üretmez. Safety ve kalıcı onay ayrı aşamalardır.

Katalogda kod veya doküman talimatı yürütülmez. CLI hataları güvenilmeyen girdiyi/anahtarları stderr'e kopyalamadan genel hata kodu döndürür. İki JSON girişinin her biri 1 MiB ile sınırlıdır.

## Mimari sınır

T06 LangGraph grafı üç düğümlü haliyle korunur. Diagnostic bu grafın çıktısına uygulanan ayrı, küçük bir modüldür; grafın içine bağlanmış dördüncü ajan veya tamamlanmış çok ajanlı teşhis sistemi değildir. Mevcut Knowledge düğümü kaynak adapterını çağırır; LLM tabanlı Knowledge/Diagnostic davranışı gelecekteki iştir.

Katalog ve sentetik kaynak bu depoda CC0-1.0 test verisi olarak oluşturuldu. Kaynak baytları değişirse katalog checksum'ları yeniden incelenerek güncellenmelidir. Rastgele belgeler otomatik teşhis kuralına dönüştürülmez.

## Doğrulama

30 yeni test: kaynak bağlama, eksik karşıt kanıtta durma, kaynak checksum/sürüm/sayfa/bölüm/alıntı uyuşmazlığı, yanlış ekipman/mod, kaynaksız hipotez reddi, state uygunluğu, çelişkili kanıt, dangling citation ve gerçek Chroma/Supervisor entegrasyonu. Tam test sonucu STATUS.md içinde tutulur. Fiziksel motor testi yapılmadı.

## Web/API adapterı

/v1/demo/diagnostic/{scenario} salt okunur endpoint'i, complete ve missing_counter_evidence izinli seçimlerini alır. docs/examples/diagnostic-analysis.json kayıtlı sentetik analizi ve datasets/fixtures/diagnostic-catalog.json kataloğu sunucuda yüklenir; her girdi 1 MiB ile sınırlıdır. Client analizi/dosya yolu alınmaz. Manufacturer parçaları veya demo dışı mod reddedilir. Eksik/bozuk fixture 503/diagnostic_demo_unavailable döner; dosya yolu ve içerik hata yanıtına eklenmez.

Eksik karşıt kanıt senaryosu matches fonksiyonuyla karşıt beyana bağlı parçayı yalnızca bellekte çıkarır. Rapor mevcut evaluate_hypotheses ile oluşturulur, dosyalar değişmez. Dönen nesne sürümlü DiagnosticReport'tur; source_kind=synthetic, guidance_allowed=false. Aynı kayıtlı girdi aynı sonucu verir. POST desteklenmez. Yeni endpoint graf veya canlı retrieval bağlantısı kurmaz.

7 yeni HTTP testi: tam raporun destek/karşıt bağı, eksik karşıt kayıtta tüm olasılıkların gizlenmesi, bilinmeyen senaryo, eksik/bozuk fixture hatası, manufacturer verisinin reddi ve POST reddi. Toplam 377 test Docker PostgreSQL dahil geçti. Panel açıklaması docs/DEMO_UI.md içinde.
