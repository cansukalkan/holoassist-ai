# Kalan donanım kapıları ve sonraki saha aşamaları — 31 Ekim 2026

Şu an yazılım ve sözleşme katmanlarının tamamı (`T02–T12`, `T14`, `T15`) sentetik veriyle uçtan uca çalışır ve doğrulanmıştır: kaynak korumalı Chroma RAG + içerik adresli LRU önbellek, ORB/RANSAC referans tanıma, sınırlı LangGraph Supervisor, karşıt kanıt matrisi, kalıcı SQLite/PostgreSQL insan onayı, 3D uzamsal anchor bağlayıcı, tekrarlanabilir sentetik benchmark, kurumsal Web platformu (`/`, `/demo`) ve Unity 6 UI Toolkit 3D denetim istasyonu.

Fiziksel saha ürününe geçiş için yalnızca donanım/kaynak bağımlı kapılar açıktır:

| Sıra | Açık Donanım / Saha Kapısı | Tamamlanma Ölçütü |
|---|---|---|
| 1 (`T01`) | Gerçek düşük voltajlı DC motor ve izinli kılavuz | Fiziksel motor modeli seçilmiş, yeniden dağıtım/kullanım izinli üretici kılavuzu indekslenmiş ve gerçek çalışma sınırları doğrulanmış |
| 2 (`T13`) | Fiziksel kamera ve mobil AR takibi | Gerçek iPhone/ARKit veya ARCore üzerinde referans görsel hizalama hatası, takip kaybı ve geri kazanım süresi ölçülmüş |
| 3 (Canlı LLM Deneyi) | Tek ajan vs. çok ajan LLM karşılaştırması | Lisanslı gerçek kılavuz üzerinde aynı bütçe ile tek ajanlı ve çok ajanlı akışların doğruluk ve p50/p95 gecikme ölçümü tamamlanmış |

Gerçek motor bilgileri gelmeden ekipmana özgü güvenli sınırlar veya bakım prosedürleri hazırlanmaz. Tam ajan akışı, YOLO eğitimi ve fiziksel Unity AR kamera takibi mevcut geliştirme kapsamına dahil değildir. Yerel paylaşılan Bearer anahtarları üretim giriş sistemi sayılmaz; üretim için kişi bazlı kimlik, erişim sınırları ve dağıtım kontrolleri gerekir.
