# Docker ile tüm yerel demoyu çalıştırma

Docker Desktop motoru açık olmalı. Depo kökünden:

```powershell
# İlk kurulumda .env yoksa PostgreSQL anahtarını oluşturur:
.\scripts\init-postgres.ps1
# .env içinde API kimlikleri yoksa iki ayrı yerel anahtar ekler:
.\scripts\init-api.ps1
# İlk imajı oluşturur; sonraki kaynak değişikliklerinde de yeniden build eder:
docker compose up -d --build --wait
```

Mevcut .env varsa init-postgres.ps1 tekrar çalıştırılmamalı; mevcut sırları korur ve üzerine yazmayı reddeder. init-api.ps1 mevcut iki anahtarı korur. Sırlar görüntülenmez, Git'e veya imaja eklenmez. İmaj build context'i explicit allowlist ile sınırlıdır. Gereken API anahtarları eksikse API başlamaz.

- Demo: http://127.0.0.1:8002/demo
- API: http://127.0.0.1:8002/docs
- Hazır olma: http://127.0.0.1:8002/ready
- PostgreSQL host erişimi: 127.0.0.1:5433

8002 portu HOLOASSIST_API_PORT ile değiştirilebilir. Önceki host Python demosu 8001 üzerinde ayrı çalışabilir; Docker kurulumu onun çalışmasını gerektirmez. Konteyner içindeki API portu 8000, PostgreSQL adresi postgres:5432'dir. API dışarıya yalnızca host loopback üzerinden açılır. .env dosyası mount edilmez; yalnızca gerekli değişkenler Compose tarafından çalışma anında sağlanır.

Durum ve durdurma:

```powershell
docker compose ps
docker compose stop
# Var olan imajlarla yeniden aç:
docker compose up -d --wait
```

stop volume verisini silmez. PostgreSQL verileri mevcut holoassist_postgres_data volume'undadır. Uygulama yeniden başlatıldığında onay kayıtları bu veritabanından okunur. Volume silme/temizleme bu kurulumun parçası değildir.

API imajı Python 3.12-slim-bookworm kullanır. Yalnızca api/postgres extras kurulur; Chroma, OpenCV, LangGraph, LLM/model veya Unity eklenmez. Demo, sabit kaynak/analiz fixture'larıyla çalışır. Non-root UID 10001, salt okunur root filesystem, /tmp tmpfs, cap_drop=ALL ve no-new-privileges kullanılır. Bu bir yerel geliştirme dağıtımıdır; üretim kişi kimliği, TLS ve servis ölçekleme değildir. Taban imajı major/minor tag'i kullanır; yeniden build patch/dependency güncellemesi alabilir.

Docker readiness doğrudan /ready üzerinden PostgreSQL tablo erişimini kontrol eder; ilk başlatma postgres healthcheck'ini bekler. Çalışan PostgreSQL sonradan koparsa API 503/healthy olmayan duruma geçebilir; depends_on runtime yeniden bağlanma/orchestrator garantisi değildir.

## Doğrulanan sonuç

21 Ekim 2026: api ve postgres konteynerleri healthy. Tarayıcıda 8002/demo tüm panelleriyle doğrulandı. Gerçek HTTP ile statik ekran, sensör ve iki Diagnostic endpoint'i 200 döndü. İnceleme açma 401/403 rol engelleri, idempotent open ve reviewer snapshot erişimi kontrol edildi. API restart sonrası aynı pending inceleme, aynı digest ile korundu; gerçek işlem onayı verilmedi. Kayıt TTL dolunca expired olarak değerlendirilir. Çıktı docs/examples/api-container-review.json içinde.

380 test Docker PostgreSQL dahil geçti. Host ve imaj içinde pip check temiz. Container ortamındaki resolver raporu docs/dependency-resolution-container.json, kurulu Linux sürümleri requirements-container.lock.txt. Host ortam kilidi bundan ayrıdır. İmaj içinde .env, .git ve host data/ olmadığı ayrıca kontrol edildi. PostgreSQL volume'u yeniden oluşturulmadı veya taşınmadı.

Tekrarlanabilir HTTP smoke:

```powershell
.\.venv\Scripts\python.exe scripts/demo-api-review.py --port 8002
```

Bu yardımcı host geliştirme ortamı ve python-dotenv gerektirir; normal Docker demo kullanımı host Python gerektirmez. Smoke yalnızca sentetik pending kayıt açar, karar vermez. Yerel geliştirme anahtarları Unity'ye veya tarayıcı koduna gömülmez.
