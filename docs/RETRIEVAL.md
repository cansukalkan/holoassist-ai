# Chroma kaynaklı arama (T04)

Bu sürüm yerel Chroma veritabanında kaynaklı parçaları kalıcı saklar ve sıralı kaynak sonuçları döndürür. LLM ile cevap üretimi veya anlamsal embedding modeli henüz eklenmedi. Geliştirme ve test için deterministik, 512 boyutlu SHA-256 sözcük hashing baseline'ı kullanılır. Varsayılan Chroma embedding modeli kullanılmaz, model indirilmez ve API anahtarı gerekmez.

## Kurulum ve demo

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev,rag]'
.\.venv\Scripts\python.exe -m holoassist.rag.search --db data/demo-chroma --source-kind synthetic index datasets/fixtures/synthetic-guide.json
.\.venv\Scripts\python.exe -m holoassist.rag.search --db data/demo-chroma --source-kind synthetic query temperature --equipment-id synthetic-rig
.\scripts\check.ps1
```

Beklenen sonuç: sentetik test belgesinin 2. sayfasındaki “Sentetik sensör kayıtları” bölümü. Gerçek çalıştırma çıktısı `examples/retrieval-result.json` içinde kaydedilir. `source_kind=synthetic` korunur; sonuç teknik bakım kaynağı sayılmaz. Çıktı sayfa/bölüm, alıntı, belge sürümü, SHA-256, izin/lisans ve karakter aralığı taşır.

Doğrulanan dev+rag ortamının kesin paket sürümleri `requirements-rag.lock.txt` içindedir. Yeni ortamda bu dosyayı kurup ardından `pip install -e .` çalıştırın. Yalnızca dev ortamını kurarsanız Chroma entegrasyon testleri skip olur; tam kontrol için rag grubu gereklidir.

## Kaynak ve sürüm davranışı

- synthetic/manufacturer kaynakları ayrı koleksiyonlara gider; kaynak türü açıkça seçilmelidir. Koleksiyon metadata'sında embedding yöntemi ve şema sürümü doğrulanır.
- Arama ekipman kimliğiyle filtrelenir. Farklı ekipmanın parçaları sonuçlara karışmaz.
- Aynı dokümanın aynı parçalarını yeniden indekslemek kayıt sayısını artırmaz.
- Mevcut dokümanın sürümü, içeriği veya parçalama ayarları değişirse indeksleme reddedilir. Yeni koleksiyon kullanın; eski parçalar sessizce tutulmaz veya silinmez.
- Bu tek yazarlı bir prototiptir. Büyük dokümanlar 128 kayıtlık batch'lerle yazılır; tüm doküman yazımı atomik değildir. Yazım ortasında hata durumunda yeni koleksiyonda yeniden oluşturun. Eşzamanlı yazar ve sürüm migrasyonu henüz desteklenmez.
- İzin/lisans alanları beyan niteliğindedir. Gerçek üretici dokümanları insan incelemesi sonrası eklenmelidir.

## Arama sınırları

Sözcükler Unicode ile ayrılır; temel Türkçe/İngilizce durak sözcükleri elenir. Kök bulma, eş anlamlılık veya semantik anlama yoktur. Cosine uzaklığı 0.9'dan yüksek adaylar ve sorguyla ortak sözcüğü olmayan adaylar elenir. Boş koleksiyon, yanlış ekipman ve ilgisiz sorgu boş sonuç döndürür. Bu eşik pilot ayardır; gerçek veriyle kalibre edilmemiştir.

`retrieval_score = 1 - cosine_distance` benzerlik skorudur, güven olasılığı değildir. Varsayılan en fazla 3 sonuç; top_k 1–20 arasında. Boş veya hatalı parametreler reddedilir. Metadata ile alıntı/kimlik/checksum arasında tutarsızlık varsa sonuç sunulmaz.

Adaylar küçük bir vektör komşuluğundan alınır; lexical filtre sonrasında top_k'dan az sonuç kalabilir. Filtrelenen ekipmanın ID'lerini saymak küçük korpus için uygundur; büyük korpus ölçeklemesi henüz yapılmadı. Türkçe semantik kalite, gerçek üretici verisi ve uzman kaynak doğruluğu değerlendirmesi bekliyor. Chroma veritabanı dosyalarına doğrudan müdahaleye karşı kriptografik imzalama uygulanmadı.

## Doğrulama

107 test geçti; bunlara gerçek Chroma ile indeks/arama, tekrar indeksleme, sürüm değişimi reddi, yanlış ekipman, kaynak ayrımı, bozuk alıntı metadata'sı ve ayrı süreçlerde kalıcılık testleri dahil. Ruff ve pip check temiz. Ağ ve LLM çağrısı test gereksinimi değildir.

API uygulama referansları: [Chroma veri ekleme](https://docs.trychroma.com/docs/collections/add-data), [query/get ve filtreleme](https://docs.trychroma.com/docs/querying-collections/query-and-get).
