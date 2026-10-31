# Bağımlılık ve platform uyumluluğu

Kontrol tarihi: 19 Ekim 2026. Ortam: Windows x64, Python 3.12.7.

## Kurulup çalıştırılan altyapı

İzole `.venv` içinde editable paket, pytest 8.4.2 ve Ruff 0.17.1 kuruldu. İki temel test, Ruff ve `pip check` geçti. Bunlar yalnızca paketleme ve geliştirme altyapısını doğrular. Geliştirme paketlerinin kesin sürümleri `requirements-dev.lock.txt` içinde; hash kilidi değildir.

Tekrarlama:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.lock.txt
.\.venv\Scripts\python.exe -m pip install -e .
.\scripts\check.ps1
```

## Gelecek modüller

`pyproject.toml` bağımlılıkları ayrı extras gruplarına ayırır. Tüm gruplar için resolver raporu `dependency-resolution.json` dosyasına yazılır. Resolver başarısı paketlerin sürüm gereksinimlerinin birlikte karşılanabildiğini gösterir; import, Chroma persistence, OpenCV kamera, LangGraph checkpoint ve OpenAI API çalışma testlerinin yerine geçmez. Bu testler ilgili modül aşamasında eklenecek. API anahtarıyla çağrı yapılmadı. Geliştirme kilidi gelecekteki AI paketlerini içermez.

YOLO/Ultralytics henüz eklenmedi: veri ihtiyacı, lisans, PyTorch ve donanım kararı ayrı görevdir. Headless OpenCV kamera/görüntü işlemlerini hedefler; masaüstü `imshow` arayüzü sağlamaz. İleride GUI gerekirse iki OpenCV dağıtımını aynı ortama kurmadan paket tercihi değiştirilir.

## Unity / iOS

Unity 6 (6000.0) ile AR Foundation 6.0 ve ARKit XR Plug-in 6.0 resmi belgede eşleştirilmiştir. Bu bir hedef sürüm ailesidir; Editor ve kesin paket patch sürümleri Unity projesi oluşturulurken kilitlenecek. Yerelde Unity Editor, XR paketleri, Xcode ve iPhone çalışması doğrulanmadı. Yerel iOS derlemesi için Xcode/macOS erişimi gerekir.

Kaynaklar:

- [Unity AR Foundation kurulum ve sağlayıcı uyumluluğu](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation@6.0/manual/project-setup/install-arfoundation.html)
- [Unity iOS build süreci](https://docs.unity3d.com/6000.0/Documentation/Manual/iphone-BuildProcess.html)
- [LangGraph paket metadata](https://pypi.org/project/langgraph/)
- [Chroma paket metadata](https://pypi.org/project/chromadb/)

Paket sürümleri için yerel pip raporu esas alınır; web arama indeksleri daha eski sürüm gösterebilir.

## Resolver sonucu

Tüm extras grupları için pip dry-run başarıyla tamamlandı (exit 0). Paketler bu kontrolde kurulmadı.

| Paket | Çözümlenen sürüm |
|---|---|
| chromadb | 1.5.9 |
| fastapi | 0.146.0 |
| langgraph | 1.2.16 |
| openai | 2.54.0 |
| opencv-python-headless | 4.14.0.94 |
| pandas | 2.3.3 |
| pydantic | 2.14.1 |
| uvicorn | 0.54.0 |
| numpy | 2.5.4 |

T02 güncellemesi: Pydantic 2.14.1 temel bağımlılık olarak kuruldu. 53 test, Ruff ve pip check geçti; geliştirme kilidi güncellendi. Yukarıdaki iki test ifadesi ilk aşamanın tarihsel kaydıdır. Resolver raporu güncel pyproject ile yeniden oluşturulur.

T04 güncellemesi: Chroma 1.5.9 ayrı rag extra grubuyla kuruldu; LangGraph ve OpenAI kurulmadan indeks/arama kullanılabilir. Gerçek Chroma ile 107 test, Ruff ve pip check geçti. Ayrı süreçlerde kalıcılık ve kaynak türü ayrımı doğrulandı. Dev+rag ortamı requirements-rag.lock.txt içinde kayıtlı. Yeni test/CLI'ler ağ veya varsayılan embedding modeli gerektirmez. Tüm gelecek extras için resolver komutuna rag grubu dahil edilmelidir.

Güncel tüm-extras dry-run başarıyla tamamlandı (exit 0). Resolver kurulum yapmadan uyumlu sürümleri seçti; bu raporda FastAPI 0.147.0 seçilmiştir. Önceki sürüm tablosu ilk çözümlemenin tarihsel kaydıdır. Kesin güncel çözüm docs/dependency-resolution.json içinde, kurulu ortam requirements-rag.lock.txt içinde bulunur.

T05: opencv-python-headless 4.14.0.94 kuruldu ve 18 vision testi geçti. dev+rag+vision ortamı requirements-vision.lock.txt içinde kayıtlı. Vision dependency aralıkları değişmedi; önceki resolver raporuyla aynı paket ailesi kullanıldı.

21 Ekim 2026 — T06: LangGraph 1.2.16 orchestration grubuyla kuruldu; ai grubu gelecekteki OpenAI istemcisi için ayrıldı. Dev+rag+vision+orchestration ortamı requirements-orchestration.lock.txt içinde kayıtlı. Tüm extras dry-run (dev,rag,vision,orchestration,ai,analytics,api) exit 0 ile tamamlandı ve dependency-resolution.json güncellendi. 170 test, Ruff ve pip check geçti. Mevcut modüller gerçek LangGraph ile çalıştırıldı; LLM çağrısı ve gerçek cihaz testi yapılmadı. Önceki resolver tabloları tarihsel kayıttır; bu çözümlemede gelecekteki FastAPI için 0.156.4 seçilmiştir (kurulmadı).

PostgreSQL eklemesi: postgres extra grubuna psycopg[binary]>=3.2,<4 ve python-dotenv>=1,<2 eklendi. Psycopg 3.3.6 kuruldu; tüm extras dry-run exit 0 ile tamamlandı. Gerçek PostgreSQL 17.10 dahil 312 test, Ruff ve pip check geçti. Docker/Compose doğrulandı; PostgreSQL 17.11 konteyneri healthy ve altı entegrasyon testi konteyner üzerinde geçti. requirements-postgres.lock.txt kurulu sürümleri kaydeder.

API: FastAPI 0.156.4, Starlette 1.9.0, Uvicorn 0.54.0. HTTP test istemcisi için httpx>=0.28,<1 dev grubuna açıkça eklendi. Resolver docs/dependency-resolution-api.json, kurulu ortam requirements-api.lock.txt. 317 test geçti, 6 PostgreSQL testi seçilmedi; Ruff/pip check temiz.

Docker API: Python 3.12 Linux taban imajı, api/postgres extras ile build edildi. Linux resolver docs/dependency-resolution-container.json ve requirements-container.lock.txt içinde; host kilitlerinden ayrıdır. İmaj pip check temiz; 380 host testi gerçek Docker PostgreSQL dahil geçti. Container HTTP/readiness ve restart kalıcılığı ayrıca doğrulandı.
