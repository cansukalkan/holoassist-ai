# Unity 6 UI Toolkit 3D sentetik denetim istasyonu ve AR geçiş sınırı

Unity 6.3 LTS (`6000.3.9f1`) üzerinde AR olmadan çalışan **sentetik 3D teknik denetim istasyonu**, 12 haftalık yol haritasına uygun olarak **Unity UI Toolkit (`UnityEngine.UIElements` + `USS` + `TSS`)** ve **Unity Test Framework (`EditMode` C# birim testleri)** ile yapılandırıldı. `AGENTS.md` kapsamı gereği gerçek AR oturumu, kamera takibi veya mobil cihaz derlemesi henüz üretilmedi.

## Mevcut Unity Mimarisi (Yalnızca Sentetik Masaüstü/Editor Demosu)

- `unity-app/Assets/Scripts/Runtime/HoloAssist.Client.asmdef`: İstemci çekirdeğini bağımsız ve test edilebilir derleme olarak tanımlar.
- `unity-app/Assets/Scripts/Runtime/HoloAssistContracts.cs`: FastAPI ile birebir eşleşen sürümlü C# veri sözleşmeleri ve istemci tarafı sözleşme doğrulayıcısı (`HoloAssistContractValidator`).
- `unity-app/Assets/Scripts/Runtime/HoloAssistMotorRig3D.cs`: Temsili düşük voltajlı DC motor eğitim düzeneği 3D sahnesi, yörünge kamerası ve yalnızca doğrulanmış `part_id` (`demo-label`, `demo-critical-part`) için çalışan 3D uzamsal parça vurgusu.
- `unity-app/Assets/Scripts/Runtime/HoloAssistChartRenderer.cs`: Sunucudan alınan `simulated` zaman serilerini ve MAD tabanlı istatistiksel aykırı adayları çizen grafik bileşeni.
- `unity-app/Assets/Scripts/Runtime/HoloAssistUiToolkitView.cs`, `Assets/Resources/HoloAssistWorkstation.uss`, `Assets/Resources/HoloAssistTheme.tss`: `UIDocument` ve `PanelSettings` tabanlı, Inspector'da elle atama gerektirmeyen 3 sütunlu **Unity UI Toolkit** arayüzü.
- `unity-app/Assets/Scripts/HoloAssistApiClient.cs`: Web platformuyla aynı güvenlik, sensör, çelişki ve bağımsız JSON rapor uçlarını tüketen ana istemci denetleyicisi.
- `unity-app/Assets/Tests/EditMode/HoloAssistClientEditModeTests.cs`: Sözleşme doğrulama, `simulated` köken zorunluluğu, takip kaybında (`lost`) ve bilinmeyen parçada 3D vurgunun temizlenmesini sınayan **Unity Test Framework EditMode** birim testleri.

## Unity Test Runner ile Birim Testlerini Çalıştırma

1. Unity Editor içinde üst menüden **Window > General > Test Runner** panelini açın.
2. **EditMode** sekmesini seçip **Run All** düğmesine basın (`HoloAssistClientEditModeTests` altındaki 9 birim testi dış ağ veya sunucu gerektirmeden çalışır).

## Sözleşme ve Güvenlik Eşlemeleri

| Mevcut sözleşme alanı | Unity istemcisindeki karşılığı |
|---|---|
| schema_version | Desteklenmeyen sürümde (`!= "1.0"`) gösterimi reddet |
| source_kind | Sentetik etiketi üst çubukta ve kartta görünür tut |
| status | Yalnızca `display_allowed` durumunda metni aç; diğer durumlarda atomik gizle |
| guidance_allowed | Her zaman `false`; fiziksel eylem izni açılmaz |
| part_id | Yalnızca doğrulanmış 3D parça eşlemesi (`demo-label`, `demo-critical-part`); takip kaybı ve bilinmeyende gizle |
| document_id, document_version, page, section | Kaynak kartında koru |
| evidence_id, context_digest | İzlenebilirlik ve inceleme bağını koru |

Kabul ölçütleri: kaynak yoksa adım metni gösterilmez, `tracking_status: "lost"` veya hata durumunda eski kart ve 3D parça vurgusu kaldırılır, kritik adım istemci `approval` alanıyla açılamaz (`HTTP 422`), sentetik veri `measured` olamaz. API/LLM sırları ve yerel reviewer anahtarı Unity içine gömülmez (`ai-engine/tests/test_unity_contracts.py` ile otomatik denetlenir).

Sonraki aşamalar için önce gerçek motor modeli, üretici dokümanı/sürümü ve izinli referanslar (T01) doğrulanmalı; gerçek cihazda ARKit/ARCore anchor ve takip testleri bundan sonra ele alınmalıdır.
