# Değerlendirme planı ve sentetik benchmark doğrulaması

Gerçek fiziksel DC motor (`T01`) ve mobil AR kamera (`T13`) saha ölçümü henüz yapılmamıştır; fiziksel başarı yüzdesi iddia edilmez. Buna karşılık yazılım alt sistemlerinin deterministik sözleşme, kaynak bağlama, önbellek ve güvenlik kapısı davranışı `synthetic_fixture_benchmark` kapsamında otomatik ve tekrarlanabilir olarak doğrulanmaktadır:

```powershell
.\.venv\Scripts\python.exe -m holoassist.evaluation --output docs/examples/synthetic-benchmark-report.json
```

Kaydedilen örnek çıktı `docs/examples/synthetic-benchmark-report.json` dosyasındadır (`physical_device_validated: false`, `calibrated_probabilities: false`, `guidance_allowed: false`) ve canlı olarak `GET /v1/demo/evaluation` ucundan da sunulur. Fiziksel düzenek ve lisanslı üretici kılavuzu eklendiğinde nihai saha eşikleri ayrılmış test seti açılmadan kaydedilecektir.

| Ölçüm | Yöntem |
|---|---|
| Vision precision/recall/F1 | Ayrılmış bilinen/bilinmeyen set; ışık/açı koşulları, confusion matrix |
| RAG kaynak doğruluğu | Önceden uzman etiketli soru-kaynak-sayfa eşleştirmeleri |
| Desteklenmeyen iddia oranı | Kanıtı iddiayı desteklemeyen iddialar / değerlendirilen iddialar |
| Top-3 teşhis | Doğru neden ilk üç hipotezde mi; cevapsız ve belirsiz örnekleri ayrıca raporla |
| Güvenlik | Tehlikeli, kaynaksız, çelişkili, yetkisiz onay ve replay senaryoları; tek ihlal sürüm engelidir |
| AR hatası | Fiziksel referansa uzaklık/açı; takip kaybı ve geri dönüş süresi |
| Gecikme | Uçtan uca p50/p95; soğuk/sıcak önbellek ve çağrı başına süre |
| Ajan katkısı | Aynı model, korpus, veri ve bütçeyle tek ajan / çok ajan karşılaştırması |

Eğitim, geliştirme ve test bölmeleri kaynak/düzenek bazında sızıntıyı önleyecek şekilde tutulur. Test örnekleri prompt/threshold ayarında kullanılmaz. Raporlar örnek sayısı, ham sonuç, hata kategorisi, model/prompt/paket/doküman sürümü, maliyet ve tekrar sayısını içerir. Sentetik sonuçlar fiziksel doğrulama gibi sunulmaz. İnsan etiketlemede çelişkiler ve uzlaşma kaydı tutulur. Kullanıcı testleri onaylı ve gözetimli yürütülür.
