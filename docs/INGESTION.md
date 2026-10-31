# Kaynak bilgilerini koruyan parçalama (T03)

UTF-8 JSON belge girişi, sayfa/bölüm sınırlarını aşmayan deterministik karakter pencerelerine ayrılır. PDF/OCR veya dış kaynak indirme bu aşamada yoktur; ilerideki çıkarıcılar bu giriş sözleşmesine dönüşüm yapacak.

## Çalıştırma

Depo kökünde:

```powershell
.\.venv\Scripts\python.exe -m holoassist.rag datasets/fixtures/synthetic-guide.json --max-chars 180 --overlap 30
```

Çıktı JSON listesidir. Türkçe karakterler Windows konsol kodlamalarından bağımsız taşınabilmesi için JSON Unicode escape biçiminde yazılır; JSON çözümlendiğinde özgün karakterler geri gelir. Hatalı belge/yapılandırma/dosya durumunda stderr ve çıkış kodu 2 döner. Varsayılan boyut 1000 karakter, örtüşme 100 karakterdir; örtüşme boyuttan küçük olmalı.

## Belge ve parça sözleşmesi

`SourceDocument`: document_id, document_version, equipment_id, title, source_uri, source_kind, license, permission_reference ve en az bir block. Her block boş olmayan metin ve en az bir page/section içerir. Aynı sayfa/bölüm konumunun tekrarına izin verilmez; metni birleştirin veya ayrı bölüm kimliği kullanın. Metin aynen saklanır.

`DocumentChunk`, Evidence şemasını genişletir; lisans/izin kaydı, synthetic/manufacturer ayrımı, kaynak adresi, başlık, block_index, start_char ve end_char korunur. Konumlar kaynak block metni içindeki sıfırdan başlayan Unicode karakter indisleridir; byte veya token indisi değildir. Parça kenarındaki boşluklar kırpılır, indisler buna göre düzeltilir. Sadece boşluk içeren pencereler atlanır; aynı kaynak aralığını veren örtüşen parçalar tekilleştirilir. Karakter penceresi cümle veya sözcük ortasında kesebilir.

SHA-256, alınan JSON dosyasının özgün baytlarından hesaplanır (BOM dahil). Bu bir PDF'nin checksum'ı değildir. İleride PDF adapter'ı özgün PDF kimliğini ayrıca korumalıdır. Chunk kimliği doküman/ekipman kimliği, sürüm, checksum, block indisi ve aralıkla deterministik üretilir. Belge içeriği veya metadata değişirse kimlik de değişir.

İzin/lisans alanlarının varlığı doğrulanır; gerçek izin veya üretici kimliği otomatik doğrulanmaz. İndeksleme öncesi insan incelemesi gereklidir. source_kind alanı parçaya taşınır; sentetik belge gerçek teknik kaynak sayılmaz.

Giriş boyutu 5 MiB ile sınırlıdır. CLI sınırın bir byte fazlasını okuyarak büyük dosyaları reddeder. JSON dışında ikili belge/OCR desteklenmez. Chunk üretimi ağ/LLM çağrısı ve yeni bağımlılık gerektirmez.

## Test kaynağı

`datasets/fixtures/synthetic-guide.json` bu proje için yazılmış ve CC0-1.0 ile sunulmuş sentetik test metnidir. Üretici dokümanı, gerçek motor sınırı veya bakım talimatı içermez.

Doğrulama: 86 test, Ruff ve pip check geçti. Testler kapsamı: kaynak metadata/konum/checksum, Unicode aralıkları, içerik kapsamı, sayfa sınırları, örtüşme, kimlik kararlılığı, güncellenen belge, boş/hatalı/büyük giriş ve CLI hata davranışı.
