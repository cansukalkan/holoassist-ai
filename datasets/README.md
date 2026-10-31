# Veri politikası

Bu klasörde henüz veri yok. Yalnızca izinli kaynaklar eklenir. Her veri kaydı: dataset_id, equipment_id, lisans/izin, kaynak, sürüm/checksum, toplama tarihi, simulated/measured ve train/dev/test bölümü içerir. Özel/ham veriler Git'e eklenmez; `data/` altında yerel tutulur. Büyük dosya veya model ağırlığı depoya eklemeden ayrı saklama kararı verilir.

Sentetik fixture: fixtures/synthetic-guide.json. Bu depo için oluşturulmuş CC0-1.0 test metnidir; üretici kaynağı veya fiziksel ölçüm değildir.

Diagnostic testi: fixtures/synthetic-diagnostic.json ve fixtures/diagnostic-catalog.json. İkisi de bu depo için oluşturulmuş CC0-1.0 sentetik test verisidir; gerçek motor nedenlerini veya ölçümlerini temsil etmez.

Sensör fixture'ları: fixtures/sensor-temperature.json, sensor-current.json ve sensor-vibration.json. Bu depo için oluşturulmuş CC0-1.0 sentetik değerlerdir; tüm örnekler provenance=simulated taşır. Fiziksel ölçüm veya motor eşikleri değildir.

Safety testi: synthetic-safety.json, instruction-catalog.json ve safety-*-request.json fixture'ları. Bu depo için oluşturulmuş CC0-1.0 sentetik gösterim/ret testi verileridir; gerçek bakım prosedürü veya risk sınıflandırması değildir.
