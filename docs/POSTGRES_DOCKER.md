# PostgreSQL ve Docker altyapısı

PostgreSQL, kalıcı onay/snapshot/audit kayıtları için alternatif backend olarak eklendi. Chroma teknik belge parçalarının vektör aramasını sürdürür. Docker Compose PostgreSQL ve Python/API servislerini birlikte çalıştırır; tam demo kurulumu docs/DOCKER_APP.md içinde. SQLite hızlı yerel test ve mevcut demo kayıtları için kullanılabilir. SQLite verileri otomatik taşınmaz veya silinmez.

## İlk kurulum

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev,rag,vision,orchestration,postgres]'
# Yalnızca .env yoksa: örnek dosyadan rastgele parola üretir, parolayı yazdırmaz.
.\scripts\init-postgres.ps1
# Yapılandırmayı sırları yazdırmadan kontrol eder:
docker compose config --quiet
docker compose up -d --wait postgres
```

`.env` zaten varsa init script üzerine yazmaz. `.env.example` içindeki HOLOASSIST_POSTGRES_* ayarlarını mevcut dosyaya bilinçli biçimde ekleyin. Lokal .env ve data/ Git tarafından ignore edilir. Compose .env dosyasını otomatik okur; Python CLI ise açıkça `--env-file .env` ile okur. Mevcut süreç ortamı dosya değerlerinden önceliklidir.

Örnek kullanım:

```powershell
.\.venv\Scripts\python.exe -m holoassist.safety.review --env-file .env open --analysis docs/examples/safety-analysis.json --request datasets/fixtures/safety-critical-request.json --catalog datasets/fixtures/instruction-catalog.json
# PostgreSQL kayıtları için aynı --env-file seçimiyle show/inspect/decide/resume-demo/audit kullanılır.
```

HOLOASSIST_APPROVAL_BACKEND=postgres sürücüyü seçer. SQLite için backend=sqlite; --db eski yerel SQLite yolunu belirler, PostgreSQL'de dikkate alınmaz. Yanlış backend veya başarısız PostgreSQL bağlantısında sessiz SQLite fallback yapılmaz. Eksik parola reddedilir, driver hata ayrıntıları CLI'ye ve loglara kopyalanmaz.

## Compose servisinin kapsamı

- Resmî postgres:17-bookworm imajı; kararlı 17 sürüm ailesi. Tag patch güncellemeleri alabilir; bu aşamada image digest kilitlenmedi ve imaj indirildi.
- Host bağlantısı yalnızca 127.0.0.1:5433, konteyner içinde 5432. Port HOLOASSIST_POSTGRES_PORT ile değiştirilebilir.
- Veriler named volume içinde kalır; healthcheck pg_isready kullanır.
- Parola compose.yaml içine yazılmadı; yerel .env üzerinden alınır. Bu geliştirme kurulumu environment tabanlı parola kullanır; üretim secret yönetimi değildir.
- POSTGRES_USER=holoassist, POSTGRES_DB=holoassist. Resmî imajın başlangıç kullanıcısı geliştirme yönetici kullanıcısıdır; dağıtım öncesi ayrı, sınırlı yetkili uygulama rolü gerekir.

Güvenli durdurma: `docker compose stop postgres`. Bu komut named volume verisini silmez. Mevcut volume'da .env parolasını değiştirmek PostgreSQL rol parolasını otomatik değiştirmez. Veri taşıma/rol rotasyonu bu adımda uygulanmadı.

## Onay backend tasarımı

`safety/postgres.py` içindeki PostgresApprovalStore mevcut ApprovalStore yaşam döngüsünü paylaşır. Psycopg 3 ile yalnızca storage/transaction ayrılır; onay iş kuralları kopyalanmadı. Şu an snapshot ve record modelleri TEXT JSON olarak saklanır, audit kimlikleri PostgreSQL identity sütunudur. ORM veya normalize edilmiş genel uygulama şeması eklenmedi.

Her işlem transaction içinde yapılır. Küçük prototipte transaction-scoped advisory lock kullanılır; farklı süreçlerin aynı onayı iki kez tüketmesi ve aynı review_id için yarışması önlenir. Tüm onay işlemleri tek advisory anahtarında serileştirilir; bu yüksek trafikli tasarım değildir. Connect/lock timeout 5 saniye, SQL statement timeout 10 saniyedir. Connection pool, Alembic migration ve uygulama rolü ayrımı gelecekteki API/dağıtım aşamasıdır.

Sürücü parametre bağlama kullanır; ortak sınıftan gelen sabit SQL'in qmark yer tutucuları Psycopg biçimine çevrilir. Kullanıcı verisi SQL metnine eklenmez. Bu dönüştürücü genel SQL ayrıştırıcısı veya dışarı açılan sorgu API'si değildir.

T10 güven sınırları değişmedi: onay kimliği üretim düzeyinde doğrulanmış değildir; scope yalnızca sentetik demo, fiziksel guidance_allowed=false, LangGraph checkpointer/resume entegrasyonu yoktur.

## Testler

```powershell
# Çalışan yerel Compose PostgreSQL sunucusuna karşı (yalnızca test şemaları oluşturur):
$env:HOLOASSIST_TEST_POSTGRES = '1'
.\scripts\check.ps1
Remove-Item Env:\HOLOASSIST_TEST_POSTGRES
```

PostgreSQL entegrasyon testleri açıkça seçilmelidir. Her test rastgele adlı kendi şemasını oluşturup yalnızca o şemayı temizler; public uygulama tablolarını silmez. Test hesabının şema oluşturma yetkisi olmalıdır. Sunucuya erişilemiyorsa seçilmiş entegrasyon testleri başarısız olur, başarı gibi skip edilmez. Flag verilmezse altı PostgreSQL testi skip olur.

Bu oturumda: **312 test geçti**, Ruff ve pip check temiz. Bunlara gerçek PostgreSQL 17.10 üzerinde altı entegrasyon testi dahil: bağlantı yenileme, tek kullanımlık onay, paralel tüketim, paralel idempotent open, süre dolumu ve değişen bağlam. Testler Docker'da değil, bu proje için oluşturulmuş izole yerel PostgreSQL kümesinde 127.0.0.1:55433 üzerinde çalıştırıldı. Test sunucusu işlem sonunda kapatıldı. Mevcut PostgreSQL sunucularına/veritabanlarına dokunulmadı.

Yedi yeni yapılandırma/hata gizleme testi de eklendi. Psycopg 3.3.6 ve python-dotenv postgres extra içindedir. Tüm extras resolver raporu docs/dependency-resolution.json içinde güncellendi; kurulu ortam requirements-postgres.lock.txt dosyasında kayıtlıdır.

## Docker üzerinde doğrulama — 21 Ekim 2026

Kullanıcı Docker Desktop açtıktan sonra motor erişimi sağlandı. `docker compose up -d --wait postgres` başarılı: `holoassist-postgres-1` healthy, PostgreSQL 17.11, bağlantı `127.0.0.1:5433`, veritabanı `holoassist`. Veriler `holoassist_postgres_data` volume içinde saklanır. Konteyner çalışır durumda bırakıldı.

Python backend üzerinden `approvals` ve `approval_events` tabloları oluşturuldu. Bir sentetik inceleme kaydı ve bir audit olayı eklendi; inceleme insan onayı bekler ve 15 dakika geçerlidir. Fiziksel işlem izni verilmedi. Altı PostgreSQL entegrasyon testi bu kez Docker sunucusuna karşı çalıştırıldı: **6 geçti**. Önceki 312 testlik tam doğrulama yerel PostgreSQL 17.10 üzerindeydi; bu adımda yalnızca ilgili altı test yeniden çalıştırıldı.

Önceki `sailor-ingest.sock` açılış hatası bu çalıştırmada tekrarlanmadı; kesin kök nedeni belirlenmedi. Docker runtime dosyaları silinmedi ve fabrika ayarlarına dönülmedi. Kaydedilmiş çıktı: [docker-postgres-result.json](examples/docker-postgres-result.json).

Kaynaklar: [Resmî PostgreSQL Docker imajı](https://hub.docker.com/_/postgres), [Psycopg kullanım ve parametre bağlama](https://www.psycopg.org/psycopg3/docs/basic/usage.html).

API konteyneri de eklendi ve mevcut PostgreSQL volume ile doğrulandı. Başlatma: docker compose up -d --build --wait. Demo http://127.0.0.1:8002/demo. Ayrıntılar docs/DOCKER_APP.md.
