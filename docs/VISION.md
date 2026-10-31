# Referans görüntü tanıma (T05 prototipi)

OpenCV ORB + Hamming eşleştirme + RANSAC homography ile tek bir kayıtlı düzlemsel referansın görüntüde bulunması uygulanmıştır. Bu bir YOLO modeli, genel motor sınıflandırıcısı, 3D poz tahmini veya AR anchor sistemi değildir. Etiket/referans kartı yaklaşımıdır.

## Çalıştırma

```powershell
.\.venv\Scripts\python.exe -m pip install -e '.[dev,rag,vision]'
.\.venv\Scripts\python.exe -m holoassist.vision.demo
.\.venv\Scripts\python.exe -m holoassist.vision --reference data/vision-demo/reference.png --image data/vision-demo/scene.png --equipment-id synthetic-rig --reference-kind synthetic
```

Demo tekrar üretilebilir sentetik test kartı, perspektifli sahne, farklı desenli kart ve boş görüntü oluşturur. `data/vision-demo/recognition.json` sonucunu ve `recognized.png` işaretli görüntüsünü kaydeder. Dosyalar test verisidir; motor fotoğrafı veya fiziksel ölçüm değildir. Aynı klasördeki demo dosyaları yeniden üretimde güncellenir.

Farklı görüntüde reddi görmek için `--image data/vision-demo/unknown.png` veya `blank.png` kullanın. Kamera açılmaz. Canlı kamera/Unity entegrasyonu gelecekte kareleri `ReferenceMatcher.recognize(frame)` metoduna iletebilir.

## Sonuç ve kabul kapıları

- status: matched / unknown / low_confidence. Yalnızca matched ekipman kimliği ve dört piksel köşesi taşır. Sonuç, referansın synthetic/real niteliğini korur; matched tek başına teknik analiz izni değildir.
- Varsayılanlar: en az 16 benzersiz eşleşme, 12 RANSAC inlier ve 0.6 inlier oranı. Lowe ratio test 0.75. Referans üzerindeki inlier convex hull alanı en az %10 olmalıdır.
- Köşeler sonlu ve dörtgen dışbükey olmalı; izdüşüm alanı sahnenin %1–101 aralığında ve köşeler görüntü sınırının %5 toleransında olmalıdır. Toleranslar pilot ayarlardır; gerçek veride kalibrasyon gerekir.
- İnlier oranı yalnızca geometrik tutarlılık metriğidir; ekipman doğruluğu olasılığı değildir.
- Özelliksiz referans kaydedilemez. Boş, az eşleşen veya geometrik olarak zayıf sahnelerde kimlik verilmez. Benzer etiket düzenleri kısmi eşleşip low_confidence dönebilir.
- Giriş uint8 grayscale veya BGR NumPy dizisidir. En az 32x32 ve en fazla 4 milyon piksel; dosyadan giriş en fazla 10 MiB. Decode sonrasında boyut denetlenir; güvenilmeyen uzaktan görüntüler için izolasyonlu decoder henüz tasarlanmadı.

## Sınırlar ve doğrulama

18 vision testi: perspektifli referansın köşe hatası, aynı görüntü/BGR, farklı desen, boş/rastgele görüntü, düşük güven, geçersiz homography/izdüşüm, hatalı giriş ve ayar doğrulaması. Diğer modüllerle toplam 125 test hedeflenir; güncel test sonucu STATUS.md içinde tutulur.

Motor modeli/referans fotoğrafları henüz yok; gerçek ekipman doğruluğu ve bilinmeyen sınıf performansı ölçülmedi. Çoklu referanslar arasında belirsizlik, canlı kamera yakalama, takip kararlılığı ve mobil gecikme henüz uygulanmadı. Düşük dokulu/parlak/tekrarlı yüzeyler ve 3D bakış değişimleri bu yöntem için sınırlamadır. Sentetik test başarısı fiziksel cihaz başarısı değildir.

Kurulu OpenCV: opencv-python-headless 4.14.0.94. Doğrulanan dev+rag+vision ortamı requirements-vision.lock.txt içinde. Yeni bağımlılık aralığı eklenmedi; vision extra önceki tüm-extras raporunda çözümlenmişti. Bu adımda gerçek import/çalışma testleri yapıldı.

Yöntem referansı: [OpenCV feature matching ve homography](https://docs.opencv.org/4.x/d1/de0/tutorial_py_feature_homography.html).
