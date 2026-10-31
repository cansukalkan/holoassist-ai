# T10 — Kalıcı sentetik insan onayı prototipi

SQLite üzerinde bekleyen onay, karar, süre dolumu, bağlam geçersizleşmesi ve tek kullanımlık demo devam kaydı uygulanmıştır. Bu, gerçek ekipmana bakım yetkisi veren veya LangGraph grafını otomatik sürdüren bir mekanizma değildir. `guidance_allowed=false` tüm kayıtlarda korunur.

## Yaşam döngüsü

pending → approved veya rejected. Approved kayıt bir kez tüketilip consumed olur. Pending/approved kayıt süresi dolunca expired; bağlam/kapı/izin uyumsuzluğunda invalidated olur. Son durumlar tekrar onaylanamaz veya kullanılamaz. Yeni inceleme için yeni review_id gerekir.

Her kayıt analiz/plan/katalog snapshot'ı ve context_digest taşır. Katalog sürümü, kaynak checksum, ekipman, adım, takip veya analiz bilgisi değişirse eski onayla devam reddedilir. Onay kararında incelenen digest ayrıca açıkça verilmelidir; rastgele approval_id ile kör onay kabul edilmez.

## CLI örneği

Önce T09 Safety demo analizi oluşturulmuş olmalı (`docs/examples/safety-analysis.json`). Depo kökünden PowerShell 7:

```powershell
$pending = .\.venv\Scripts\python.exe -m holoassist.safety.review --db data/reviews.sqlite3 open --analysis docs/examples/safety-analysis.json --request datasets/fixtures/safety-critical-request.json --catalog datasets/fixtures/instruction-catalog.json | ConvertFrom-Json
# Bu ayar yalnızca yerel geliştirme kimliği/izin listesi gösterimidir.
$env:HOLOASSIST_REVIEWERS = (.\.venv\Scripts\python.exe -c 'import getpass; print(getpass.getuser())').Trim()
.\.venv\Scripts\python.exe -m holoassist.safety.review --db data/reviews.sqlite3 inspect $pending.approval_id
# Snapshot ve kapsam incelendikten sonra:
.\.venv\Scripts\python.exe -m holoassist.safety.review --db data/reviews.sqlite3 decide $pending.approval_id --decision approve --expected-digest $pending.context_digest
.\.venv\Scripts\python.exe -m holoassist.safety.review --db data/reviews.sqlite3 resume-demo $pending.approval_id --analysis docs/examples/safety-analysis.json --request datasets/fixtures/safety-critical-request.json --catalog datasets/fixtures/instruction-catalog.json
.\.venv\Scripts\python.exe -m holoassist.safety.review --db data/reviews.sqlite3 audit $pending.approval_id
```

`--decision reject` de desteklenir. İkinci resume-demo reddedilir. `show approval_id` güncel durumu gösterir; `inspect` snapshot incelemesini yalnızca izin listesindeki geliştirme kimliğine açar. Onay için varsayılan izin listesi boştur. İzin listesi kaldırılmış bir kişinin eski onayı kullanılamaz.

Varsayılan süre 900 saniye, izin verilen TTL 1–3600 saniye. Aynı review_id ve aynı bağlamla open çağrısı idempotenttir; ömrü uzatmaz. Aynı review_id başka bağlama bağlanamaz. Süresi dolan/tüketilen review_id yeniden açılarak yenilenmez; yeni review_id kullanılmalıdır.

## Gerçek demo çıktısı

`docs/examples/approval-demo-result.json` ayrı CLI süreçlerinde çalıştırılmış örneği içerir:

| Aşama | Çıktı |
|---|---|
| İnceleme oluşturuldu | pending |
| İzinli geliştirme kimliğiyle karar | approved |
| Güncel bağlam doğrulanıp bir kez tüketildi | demo_continuation_recorded |
| Aynı kayıtla ikinci devam | Reddedildi |
| Fiziksel bakım izni | false |

Demo senaryosunda yalnızca sentetik kritik işlem etiketi vardır. Kaynak/güvenlik kapısı ayrı kalır ve kritik metni hâlâ gizler. Onay tüketimi yeni bir SafetyReport üretip critical adımı display_allowed yapmaz. Receipt gelecekteki entegrasyon için tek kullanımın kaydıdır, operasyon yürütme yetkisi değildir.

## Kalıcılık ve işlem güvenliği

`ApprovalStore` analiz/request/katalog modellerini doğrulayıp snapshot'ı SQLite'a kaydeder. Her method ayrı bağlantı açar ve kapatır; başka süreç aynı dosyadan devam edebilir. Yaşam döngüsü değişikliği ve audit olayı aynı transaction'da yazılır. BEGIN IMMEDIATE ile durum kontrolü ve tüketim aynı yazma işlemi içinde gerçekleşir; iki eşzamanlı isteğin ikisi birden aynı kaydı tüketemez.

Resume sırasında hem kayıtlı snapshot hem backend'in verdiği güncel bağlam kaynak/güvenlik kapısından tekrar geçirilir. Her iki digest kayıtla aynı olmalıdır. Eski snapshot değişikliği, takip kaybı, yasak riske geçiş, kaynak/ekipman değişikliği veya reviewer izninin kaldırılması tüketimi engeller. Geçersizleşme/süre dolumu, operasyon reddedilse de kalıcı kaydedilir.

Saat kontrolü sunucu UTC saatidir; sona erme anında (now >= expires) kayıt kullanılamaz. Saat kaydın son güncellemesinin gerisine düşerse işlem reddedilir. Veritabanı kilidinde 5 saniye timeout vardır; bağlantı/hata durumunda transaction rollback yapılır. Harici dosya veya ekipman işlemi atomik transaction'ın parçası değildir.

Audit olayları kabul edilen durum geçişlerini kaydeder: oluşturma, onay, ret, süre dolumu, geçersizleştirme, tüketim. Yetkisiz başarısız girişimler ayrı audit olayına dönüştürülmez. SQLite dosyaları `data/` altında yerel tutulur ve Git'e alınmaz. Testler kendi rastgele adlı veritabanlarını data/approval-tests altında bırakır.

## Kimlik ve güven sınırı

Python API'sindeki `authenticated_reviewer`, ileride backend'in doğruladığı kullanıcı kimliğinden gelmelidir. Constructor'daki authorized_reviewers izin listesi kimlik doğrulaması değildir. İstemcinin gönderdiği reviewer/approved alanları güvenilir kimlik veya onay kanıtı sayılamaz.

Yerel CLI getpass.getuser() geliştirme etiketini ve HOLOASSIST_REVIEWERS ortam ayarını kullanır. Bu değerler yerel ortamı kontrol eden biri tarafından değiştirilebilir; üretim düzeyinde kullanıcı doğrulaması sağlamaz. Şu an ağ endpoint'i, kullanıcı oturumu, dijital imza veya yetkili personel doğrulaması yoktur. Gerçek mod zaten kapalıdır. Inspect/show/audit komutları yerel araçlardır; ağ API'sine taşınırken endpoint bazında erişim kontrolü gerekir.

SQLite yerel dosyası imzalanmış veya şifrelenmiş değildir; snapshot özel doküman/analiz içerebilir. Snapshot/digest uyumsuzluğu yakalanır fakat dosyaya yazma erişimi olan bir saldırgana karşı bütünlük garantisi verilmez. Ham dosyaların güncelliğini kendisi okuyup doğrulamaz; resume'a verilen güncel bağlam backend'in güvenilir kaynak kayıtlarından gelmelidir. Eski snapshot güncelmiş gibi verilirse dış dünyadaki değişikliği keşfedemez.

Bu T10 prototipi kalıcı uygulama checkpoint'i ve demo devam kaydı sağlar. LangGraph checkpointer/interrupt-resume entegrasyonu, çok ajanlı akışın sürdürülmesi ve fiziksel/AR operasyon izni henüz uygulanmadı. T09 kapı kodu artık persistent_approval_required döndürür; eski not_implemented çıktıları tarihsel demo kayıtlarıdır.

## Kod ve doğrulama

- contracts/approval.py: ApprovalRecord ve DemoResumeReceipt.
- safety/approvals.py: ApprovalStore ve audit/state işlemleri.
- safety/review.py: open/show/inspect/decide/resume-demo/audit CLI.

31 yeni test: süreçler arasında kalıcılık, izin listesi, digest bağlama, süre dolumu, reddedilmiş/bekleyen kayıt, tekrar kullanım, izni kaldırılan reviewer, kaynak/katalog/parça bağlamı değişikliği, saat gerilemesi, snapshot değişikliği ve iki eşzamanlı tüketici. Tam test sonucu: 299 test, Ruff ve pip check geçti. Yeni bağımlılık eklenmedi; Python sqlite3 kullanıldı. Gerçek motor/iPhone testi veya gerçek müdahale yapılmadı.

Uygulama referansları: [Python sqlite3](https://docs.python.org/3.12/library/sqlite3.html), [SQLite transaction kontrolü](https://www.sqlite.org/lang_transaction.html).
