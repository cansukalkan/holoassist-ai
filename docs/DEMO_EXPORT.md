# İndirilebilir sentetik demo raporu

Demo ekranının altındaki JSON raporu indir düğmesi, seçili üç senaryoyu sunucuda yeniden değerlendirir. Daha önce ekranda görünen eski yanıtların birebir kopyası değildir; seçili senaryoların yeni değerlendirmesidir. Rapor ortak bir teşhis veya ajan çalıştırması değildir. independent_sections=true alanı güvenlik/gösterim, sensör ve Diagnostic bölümlerinin birbirinden bağımsız kaldığını belirtir.

Endpoint:

```text
GET /v1/demo/report?safety=critical&sensor=current&diagnostic=missing_counter_evidence
```

| Seçim | İzinli değerler |
|---|---|
| safety | information, critical, tracking, unknown |
| sensor | current, temperature, vibration |
| diagnostic | complete, missing_counter_evidence |

Sürüm 1.0 DemoExport, export_id, generated_utc, scope=synthetic_demo, independent_sections=true, guidance_allowed=false ve seçimleri içerir. SafetyReport, SensorDemoResult ve DiagnosticReport mevcut doğrulanan sözleşmeleriyle korunur. Raporun oluşturulma zamanı sensör ölçüm zamanı değildir. Her indirme yeni kimlik/zaman alır; dosya sunucuda veya veritabanında saklanmaz. İnceleme/audit/onay kaydı oluşturulmaz. Aynı seçenekler aynı bölüm sonuçlarını verir; export_id/zaman değişebilir.

Kritik veya engellenmiş güvenlik planının adım metni ve alıntıları raporda da gizli kalır. Bu gizleme bağımsız Diagnostic kaynak bölümünü güvenlik planına dönüştürmez; Diagnostic hiçbir bakım adımı sunmaz. Sensör kökeni simulated, diğer demo kaynakları synthetic kalır. Kanıt kimliği, sayfa/bölüm, doküman sürümü, checksum ve karşıt beyan ilişkisi korunur. Bir bölümün fixture'ı okunamıyorsa tüm indirme 503 ile durur; eksik bölümden başarılı rapor üretilemez. Geçerli needs_information/blocked sonuçları ise eksik bilgi durumlarıyla raporda bulunabilir.

Sunucu yalnızca sabit yerel demo kaynaklarını kullanır. Dosya yolu, kullanıcı kimliği veya API anahtarı alınmaz; tarayıcıya credential gönderilmez. Geçersiz seçim 422 ile reddedilir. JSON attachment, no-store ve nosniff başlıklarıyla döner. Veri internete yayınlanmaz. İndirilen dosya kullanıcının kendi dosyasıdır; kaynak metni HTML veya kod olarak çalıştırılmaz.

Örnek gerçek HTTP dosyası: docs/examples/demo-export.json. Bu dosyada critical/needs_approval, simulated akım ve eksik karşıt kanıt nedeniyle boş Diagnostic olasılıkları birlikte bulunur. Fiziksel işlem izni yine false'dur.

13 yeni test kaynak/provenance koruma, dört güvenlik senaryosu, kritik metin gizleme, karşıt kanıt, geçersiz seçim, bölüm hatasında kısmi indirme reddi, onay depolamasına erişmeme, rapor-seçim eşleşmesi ve sırların raporda bulunmamasını kapsar. Yeni bağımlılık yok.

Doğrulama: 406 test Docker PostgreSQL dahil geçti; Ruff/pip check temiz. Docker API'den gerçek HTTP ile örnek dosya kaydedilip DemoExport sözleşmesiyle doğrulandı. Tarayıcı düğmesi raporu hazırlayıp indirme isteğini gönderdi; ekran sonucu docs/examples/export-panel.png içinde. Host ve konteyner paketleri ayrı kayıtlıdır; bu rebuild'de konteyner FastAPI 0.156.5, host test ortamı 0.156.4 kullandı. Konteynerde gerçek HTTP ve tarayıcı akışı ayrıca kontrol edildi.
