# Veri sözleşmeleri v1.0

T02 kapsamında `holoassist.contracts` modülü uygulanmıştır. Pydantic artık temel bağımlılıktır. Bu modül anahtar, ağ veya fiziksel ekipman gerektirmez.

## Kullanım

```python
from holoassist.contracts import Observation, ObservationSeries

reading = Observation(
    equipment_id="synthetic-rig",
    sensor_id="synthetic-temperature",
    timestamp_utc="2026-10-19T12:00:00+03:00",
    quantity="temperature",
    value=25.0,
    unit="degC",
    provenance="simulated",
    quality="valid",
)
print(reading.model_dump_json(indent=2))
series = ObservationSeries(observations=[reading])
# Sözleşmeyi araçlar/istemciler için üretmek mümkündür:
print(Observation.model_json_schema())
```

Bu örnekteki kimlik ve değerler sentetiktir; gerçek motor sınırı veya arıza göstergesi değildir.

## Kurallar

- Her sözleşme `schema_version="1.0"` taşır. Bilinmeyen sürüm ve alanlar reddedilir.
- `Evidence` doküman kimliği, sürüm, ekipman, orijinal belge baytlarının SHA-256 özeti, alıntı ve en az bir kaynak konumu gerektirir. `page` birden başlayan pozitif tam sayıdır; `section` boş olamaz. İkisi birlikte verilebilir.
- Checksum yalnızca biçim olarak doğrulanır. Dosya ile eşleşme, lisans, kaynak gerçekliği ve alıntının iddiayı desteklemesi ileride ingestion/kanıt katmanında kontrol edilecek.
- `retrieval_score` isteğe bağlı sonlu sayıdır; mesafe veya benzerlik sağlayıcıya bağlıdır. Olasılık değildir ve 0–1 aralığı dayatılmaz.
- `Observation` yalnızca temperature/degC, current/A ve vibration/m/s2 eşleşmelerini kabul eder. Birimler otomatik dönüştürülmez. Motor sınırları veya teşhis eşikleri uygulanmaz.
- Zaman ISO-8601 saat dilimiyle veya aware datetime olarak verilir, UTC'ye çevrilir. Naive zaman, epoch sayısı, NaN, sonsuzluk, boolean ve sayısal metin ölçümü reddedilir.
- `provenance` ve `quality` zorunludur; ölçüm kaynağı otomatik tahmin edilmez. Geçersiz kalite verisi kayıtta korunabilir; sonraki analiz katmanı bunu kullanma kararını verecek.
- `ObservationSeries` boş olamaz; tek ekipman/sensör/ölçüm türü/birim/provenance içerir. Zamanlar kesin artar. Kopya veya sırasız örnekler sessizce sıralanmaz. Farklı sensörler ayrı serilerle aktarılır.
- Modeller normal alan atamasına kapalıdır ve seriler tuple olarak tutulur. Güvenilmeyen veri `model_validate` veya `model_validate_json` ile alınır. Pydantic'in doğrulamayı atlayan `model_construct` / `model_copy(update=...)` yöntemleri güven sınırlarında kullanılmaz.

## Doğrulama

`./scripts/check.ps1`: 53 test, Ruff ve pip check geçti. Testler kaynak konumu eksikliği, şema sürümü, ek alanlar, ölçüm birimleri, zorunlu provenance, sonlu değerler, UTC dönüşümü, seri sırası ve JSON gidiş-dönüşünü kapsar. Gerçek motor ölçümü veya teşhis testi yapılmadı.

Uygulama referansı: [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/).
