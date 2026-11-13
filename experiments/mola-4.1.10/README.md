# Mola 4.1.10 — hedefli APK özelleştirme denemesi

**Durum: analiz yapıldı; değiştirilmiş ve imzalanmış APK henüz üretilmedi.**

Bu çalışma dalı, çalışan `main` dalına ve orijinal APK'ya dokunmadan iki değişikliği araştırmak için oluşturuldu.

## Esas alınan sürüm

- Kullanıcı tarafından sağlanan orijinal APK: `Mola-4.1.10-dagitim(1).apk`
- SHA-256: `b047fb12b9ff96f39fa4dda398ecf3ba0a9886089782c702406d434399ed92ba`
- Boyut: 124527834 bayt; 12 DEX dosyası
- **Önemli:** Bu APK, mevcut GitHub Actions ile eski kaynaklardan derlenen ~160 MB APK ile aynı değildir. Eski kaynakları derlemek, orijinal 4.1.10'un birebir korunması değildir.

## İstenen iki değişiklik

1. Ana ekranda Web kısayolunu gizle; Web/YouTube altyapısını silme.
2. Elle eklenen 19 radyoda oynatma ekranının ortasında o istasyonun gerçek PNG logosunu göster. TV ve radyo yayın URL'lerini değiştirme.

## APK içinden tespit edilen modüller

- `classes5.dex`: `DashboardItems`, `AddonUiMetadata`. Menü Web görünürlüğü bu katmanda incelenmeli.
- `classes8.dex`: `RadioStageView`, `RadioSourceItem`, `RadioStationItem`, `RadioBrowserStation`.
- Rehberden gelen `RadioStationItem` favicon bilgisiyle logo gösterebiliyor; elle eklenen `RadioSourceItem` için aynı yol mevcut değil.
- `RadioStageView.setLogo` ve `RadioStageView.show`, oynatıcıda logo bağlanması için hedef yöntemler.
- 19 mevcut logo `main/Radyo Logoları/*.png` altında, kullanıcı listesi `main/iptv/radio.m3u` içinde.

## Uygulama güvenlik sınırları

- Orijinal uygulamanın kodunu ve tüm native kütüphanelerini mümkün olduğunca koru.
- Sadece hedef DEX yöntemlerini değiştir; gerekli değilse `AndroidManifest.xml`, servisleri, Android Auto izinlerini veya Web modülünün altyapısını değiştirme.
- Yeniden imzalama farklı uygulama imzası anlamına gelir. APK'nın yüklenmesi ve Android Auto'da tanınması ayrı test gerektirir.
- Derlemeden önce sabit orijinal SHA-256 kontrolü yap; çıktı ayrı isimde olsun.
- Test: ana ekran Web görünürlüğü; YouTube; 19 radyonun sesi ve ortadaki logosu; TV; ekran kilidinde ses; Android Auto.
- Kullanıcının APK'sını veya abonelik içeren yayın listelerini halka açık GitHub'a **yeniden yükleme**.

## Mevcut engel

Bu oturumdaki yerel çalışma ortamında apktool, baksmali/smali, apksigner, zipalign mevcut değil. GitHub'daki mevcut Actions projesi orijinal 4.1.10 APK ikilisini içermiyor. Bu nedenle **bu daldan henüz çalışır 4.1.10 tabanlı APK çıkarılmış değil**; değiştirilmiş sürüm varmış gibi APK indirme bağlantısı verilmemeli.
