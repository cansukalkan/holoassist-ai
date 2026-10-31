# T09 — Kaynak ve talimat gösterim kapısı (sentetik prototip)

İzinli katalog, kaynak metadata'sı, ekipman ve takip durumu eşleşmesine göre sentetik bilgilendirme kartlarının gösterimi kontrol edilir. Bu modül fiziksel ekipman güvenliğini doğrulamaz, bakım izni vermez ve tam Safety Agent entegrasyonu değildir.

## Çalıştırma

Yeni bağımlılık eklenmedi. Chroma/Supervisor demo hazırlığı için mevcut rag ve orchestration extras gerekir; gate fonksiyonu Pydantic temel ortamında çalışır.

```powershell
.\.venv\Scripts\python.exe -m holoassist.rag.search --db data/safety-demo-chroma --source-kind synthetic index datasets/fixtures/synthetic-safety.json
.\.venv\Scripts\python.exe -m holoassist.agents --request datasets/fixtures/analysis-request.json --db data/safety-demo-chroma > data/safety-analysis.json
.\.venv\Scripts\python.exe -m holoassist.safety --analysis data/safety-analysis.json --request datasets/fixtures/safety-information-request.json --catalog datasets/fixtures/instruction-catalog.json
```

JSON dosyalarını UTF-8 olarak kaydedin; PowerShell 7 redirection uygundur. Kritik senaryo için safety-critical-request.json, karma plan için safety-mixed-request.json kullanın. `docs/examples/safety-*-result.json` gerçek CLI demo çıktılarını içerir.

## Demo sonucu

| Senaryo | Karar | Talimat metni |
|---|---|---|
| Kaynaklı sentetik bilgi kartı | display_allowed | “SENTETİK KART: Bu ekranda yalnızca test verisi gösteriliyor.” |
| Kritik işlem test etiketi | needs_approval | Gizlenir |
| Bilgi kartı + kritik adım | needs_approval | Planın tüm metinleri gizlenir |
| Kayıtsız parça kimliği | blocked / part_mismatch | Gizlenir |

Her raporda `guidance_allowed=false`. display_allowed yalnızca kaynaklı sentetik bilgi kartının ekranda gösterilebilmesini belirtir; fiziksel bakım izni değildir. needs_approval bir karar kodudur; henüz kalıcı bekleyen onay, onay endpoint'i veya resume yoktur.

## Veri sözleşmeleri

- `InstructionCatalog`: sentetik kapsam, katalog kimliği/sürümü, ekipman kimliği ve en fazla 20 kayıt. Her talimat sabit part_id, risk, metin ve kaynak beyanları taşır. Risk informal anahtar sözcük analiziyle tahmin edilmez; backend'in güvendiği katalog tarafından belirlenir.
- `CatalogInstruction`: informational / critical / prohibited / unknown risklerinden biri. Gösterilecek metin en az bir destekleyen tam alıntıyla birebir aynı olmak zorundadır. Talimatlar kaynak dokümandan serbest LLM metni olarak üretilmez.
- `SafetyRequest`: review_id, bağlı analysis_request_id, tracked/lost/unknown takip durumu ve 1–5 benzersiz adım. Adım yalnızca step_id, instruction_id ve part_id seçer. approval, approval_reference, risk veya text gibi ek alanlar reddedilir.
- `SafetyReport`: plan/adım kararları, gerekçe kodları, katalog sürümü, kaynak konumları ve context_digest. Bütün plan için en kısıtlayıcı karar korunur.

## Kontrol sırası ve ret davranışı

Real modu, farklı ekipman/katalog, başka analize bağlı istek veya hazır olmayan AnalysisState bloke edilir. Kayıtsız talimat/parça, yasak veya bilinmeyen risk bloke edilir. Destek/karşıt kaynak beyanlarının belge kimliği, sürüm, SHA-256, sayfa/bölüm ve tam alıntısı mevcut DocumentChunk ile eşleşmelidir. Eksik bilinen karşıt kaynak da bloke edilir; bulunan karşıt kaynak contradictory_source döndürür.

Takip lost/unknown ise bilgi istenir ve metin gösterilmez. Kaynağı/takibi uygun kritik adım needs_approval / persistent_approval_not_implemented döndürür. İstemci bir onay bayrağı ekleyerek bunu aşamaz. Kritik işlemler için kalıcı backend insan onayı T10'da tasarlanacaktır.

Plan atomiktir: herhangi bir adım uygun değilse tüm display_text alanları ve kaynak alıntıları gizlenir. Kaynak kimliği/sürüm/checksum/konum metadata'sı denetlenebilirlik için kalır. Bu, kritik talimatın kaynak alıntısından sızmasını da önler. Bilgi kartının plan içindeki adım kararı display_allowed kalabilse bile metni yoktur; renderer üst düzey plan status alanını kontrol etmelidir.

## Güven sınırı ve kapsam

Katalog, risk sınıfları, tanıma ve takip çıktıları güvendiğimiz backend adapterlarından gelmelidir. Yerel fonksiyon/CLI kimlik doğrulama uygulamaz; istemcinin tracked/matched beyanı fiziksel takip kanıtı değildir. Bu prototip yalnızca sentetik scope kabul eder, gerçek üretici kaynağıyla fiziksel adım gösterimine kapalıdır. Katalog metninin güvenliğini veya risk etiketinin doğruluğunu otomatik anlamsal analizle kanıtlamaz; gerçek kullanım öncesi uzman incelemesi gerekir.

Kaynak alıntısının checksum'a bağlı kayıtla eşleşmesi, belgenin kriptografik imzayla doğrulandığı anlamına gelmez. context_digest; analysis/request/catalog modellerinin anahtarları sıralanmış JSON gösteriminin SHA-256 özetidir. Bir girdi değişince değişir; gelecekte onayı belirli bağlama bağlamak için kullanılabilir. İmza, kimlik doğrulama, kalıcı onay veya replay koruması değildir.

Gate Diagnostic hipotezleri, sensör analiz raporları, fiziksel enerjilendirme veya gerçek AR takip oturumu doğrulaması yapmaz. Bilinen karşıt kayıtlar katalogda belirtilen beyanlarla sınırlıdır; belgelerdeki tüm anlamsal çelişkileri keşfetmez. Tek başına bir motoru güvenli ilan edemez.

## Mimari ve testler

`contracts/safety.py`: veri sözleşmeleri. `safety/gate.py`: bağımsız evaluate_plan fonksiyonu. CLI: `python -m holoassist.safety`. T06 grafı değiştirilmedi; Data/Diagnostic/Safety henüz ortak tam ajan akışına bağlanmadı. Demo kaynağı/katalog/istekleri bu depoda oluşturulmuş CC0-1.0 sentetik test verisidir; gerçek bakım prosedürü içermez.

35 yeni test: izinli bilgi kartı, kritik/yasak/bilinmeyen risk, yanlış parça, kaynak pinleme, çelişkiler, takip kaybı, sahte onay/risk düşürme, yanlış bağlam, plan atomikliği, gizli alıntı sızıntısı, digest değişimi, hata çıktısı ve gerçek Chroma/Supervisor entegrasyonu. Tam sonuç: 268 test, Ruff ve pip check başarılı. Fiziksel motor veya iPhone testi yapılmadı.

T10 güncellemesi: Ayrı SQLite onay/checkpoint modülü eklendi (docs/APPROVALS.md). Bu gate hâlâ kritik adımlarda persistent_approval_required döndürür; onayla fiziksel talimat gösterimini açmaz. Eski not_implemented kodu önceki aşamanın kaydıdır.
