# Mola Kişisel — Android Auto test sürümü

Bu özel depo, Mola/FermataX açık kaynak projesinin kişisel TV, radyo ve root deneme yapılandırmasını barındırır. Üst proje: https://github.com/moris545454/araba- (GPL-3.0).

Bu depodaki `iptv/` dosyaları **özel IPTV aboneliği kimlik bilgilerini** barındırır. Depoyu herkese açık yapmayın ve oluşturulacak APK'yı paylaşmayın.

İlk sürüm Mola 2.2.2 kaynak koduyla derlenir; Mola 4.1.10 ile birebir aynı değildir. Android Auto'da video çalışması, root davranışı ve direksiyon kumandası araç üzerinde doğrulanmalıdır.

## Sade arayuz denemesi

Ana ekran ve Android Auto yan gezinme cubugunda yalniz **TV, Radyo, YouTube** (ve geri donus icin Ana Sayfa) gorunur.
Diger servisler koddan silinmez; gereksiz kisayollar, favori ve son oynatilan raflari, web kisayollari ve sesli kontrol kisayolu gizlenir. YouTube web modulu korunur.
**Yeni ayri paket**: `me.app.molakisiselsade.auto.debug`. Boylece daha once Android Auto'da calistigi dogrulanan test APKsi, orijinal Mola ve tercihleri bozulmaz. Yeni APK'yi KingInstaller'in once Classic/root'suz yontemiyle kurun; Android Auto'da gercek aracta test edin. APK boyutu ve Android Auto uyumlulugu test edilmelidir.
