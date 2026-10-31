# Unity 6 sentetik 3D teknik denetim istasyonu

`unity-app/`, Unity 6.3 LTS (`6000.3.9f1`) üzerinde yapılandırılmış masaüstü/Editor sentetik denetim istemcisidir (`Assets/MainScene.unity`).

- **Arayüz teknolojisi:** Unity UI Toolkit (`UnityEngine.UIElements`, `Assets/Resources/HoloAssistWorkstation.uss`, `Assets/Resources/HoloAssistTheme.tss`) — Inspector üzerinde elle kurulum gerektirmeden çalışır.
- **3D sentetik sahne:** Temsili düşük voltajlı DC motor eğitim düzeneği (`HoloAssistMotorRig3D`), yalnızca doğrulanmış katalog parçaları (`demo-label`, `demo-critical-part`) için uzamsal vurgu açar; `tracking: lost`, `unknown-part` veya `HTTP 422` durumunda vurguyu ve etiketi anında kaldırır.
- **Birim testleri:** Unity Test Framework (`com.unity.test-framework` 1.6.0) ile `Assets/Tests/EditMode/HoloAssistClientEditModeTests.cs` (*Window > General > Test Runner > EditMode > Run All*).

**Sınırlar:** Gerçek AR oturumu (AR Foundation / ARKit / ARCore), kamera takibi, iOS/Xcode imzalama ve fiziksel cihaz testleri bu aşamada henüz yapılmamıştır (`AGENTS.md`). Yerel API sırları ve `.env` anahtarları Unity içerisine eklenmez.
