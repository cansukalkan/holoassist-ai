# Gerçek motor hazırlık kaydı — T01

21 Ekim 2026: Kullanıcı henüz motor seçmediğini belirtti. Motor modeli, üretici veya çalışma değerleri tahmin edilmedi. T01 gerçek donanım/kaynak doğrulaması tamamlanmış değildir.

Boş şablon: docs/equipment-intake.template.json. Bilgiler geldiğinde ayrı bir yerel dosyaya kopyalanarak doldurulabilir. Bilinmeyen alanları null bırakın; tahminî veriyle eksikleri kapatmayın.

Kontrol:

```powershell
# Host Python ortamı:
.\.venv\Scripts\python.exe -m holoassist.equipment --profile docs/equipment-intake.template.json
# Çalışan güncel Docker API imajında:
docker compose exec -T api python -m holoassist.equipment --profile docs/equipment-intake.template.json
```

Komut yalnızca verilen JSON dosyasını okur; ağ çağrısı, yükleme, donanım erişimi veya veritabanı yazımı yapmaz. Geçerli ama eksik kayıt için exit 0 ve status=needs_information döner. Çağıran uygulama status alanını kontrol etmelidir. Bozuk/sürümü uyumsuz/boyut sınırını aşan girdi exit 2 ile reddedilir; içerik hata mesajına eklenmez. Girdi sınırı 64 KiB.

| Alan | Kaydedilecek bilgi |
|---|---|
| equipment_id | Seçilen düzeneğin sabit kimliği |
| manufacturer, model | Etiket/dokümanla eşleştirilecek gerçek marka ve model |
| manufacturer_document | Doküman kimliği, sürümü, kaynak adresi, SHA-256, lisans ve izin referansı |
| power_supply_notes | Kullanılacak beslemenin kimliği ve incelenecek özellikleri |
| reference_image_notes | Motor referans görüntülerinin kaynağı ve doğrulama notu |
| sensor_notes | Sensör kimliği, veri kaynağı ve doğrulama gereksinimleri |

Doküman referansı yalnızca metadata olarak doğrulanır. Kaynak adresi açılmaz; belge baytlarıyla SHA-256 eşleşmesi, lisansın geçerliliği veya model uyumu bu komutla kanıtlanmaz. Bunlar ayrı kaynak incelemesinde doğrulanmalıdır. Besleme notu veya fotoğraf açıklaması da gerçek dosya/cihaz incelemesi yerine geçmez.

Eksikler kapansa bile status=metadata_recorded yalnızca alanların dolduğunu belirtir. Manufacturer source review, donanıma özgü sınır incelemesi, referans görüntü doğrulaması ve fiziksel düzenek doğrulaması pending_checks içinde kalır. real_device_ready=false ve guidance_allowed=false sabittir. Bu komut çalışma sınırı hesaplamaz, motor seçmez, bakım prosedürü veya kullanıma hazır kararı vermez. Bir istemcinin approval alanı kabul edilmez.

Sonraki kullanıcı girdisi gerçek marka/model olmalı; ardından ilgili üretici kılavuzu/sürümü ve kullanım izni kaydedilir. Model seçilene kadar web demosu sentetik verilerle çalışmaya devam eder. Unity AR veya tam ajan akışı bu adımda üretilmedi.

13 yeni test: boş ve dolu metadata, eksik alan, boş metin, kapsam dışı ekipman, istemci onayı, eksik kaynak bilgisi, tutarsız rapor, sürümlü JSON ve CLI hata/boyut davranışları. Gerçek düzenek testi yapılmadı. Örnek çıktı docs/examples/equipment-intake-result.json içinde.

Tam doğrulama: 393 test Docker PostgreSQL dahil geçti; Ruff/pip check temiz. Komut güncel Docker API imajı içinde çalıştırıldı ve boş profil için needs_information çıktısı kaydedildi. Docker demo /ready kontrolü ready/reachable.
