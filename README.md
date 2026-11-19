# Geleceğe Adım — Kamu İlan
**Merkezi Kamu, Belediye & Kurum Personel Alım Takip Sistemi (42 Resmi Portal)**

Geleceğe Adım Kamu İlan; Türkiye'deki 42 resmi kamu kurumu, bakanlık, büyükşehir belediyesi ve kamu iktisadi teşebbüsünün kariyer portallarını saatlik olarak tarayan, her ilanın içine girerek **aranan meslek gruplarını** ve **başvuru şartlarını** çıkaran açık kaynaklı bir web uygulamasıdır.

## Öne Çıkan Özellikler
- **42 Resmi Portal Entegrasyonu:** Cumhurbaşkanlığı Kamu İlan (SBB), Kariyer Kapısı, İŞKUR, Resmî Gazete, ÖSYM, MSB, Jandarma, İBB, Ankara BB, İzmir BB, DSİ, KGM, BOTAŞ, Kamu Bankaları ve Savunma Sanayii.
- **İlan İçi Meslek & Şart Ayrıştırma (`bot.py`):** Her ilanın kendi duyuru sayfasını okuyarak aranan meslekleri, kadro tablolarını ve başvuru şartlarını detay penceresinde listeler.
- **4 Katmanlı Engel Aşma Modülü (`helper_bot.py`):** SSL sertifika hataları, WAF/403 korumaları, JavaScript tabanlı portallar ve PDF duyuru dosyalarını otomatik çözer.
- **Bölüm Şartsız (2001 / 3001 / 4001) Vitrini:** Herhangi bir lise, önlisans veya lisans bölümünden mezun adayların başvurabileceği düz memurluk kadrolarını tek tıkla filtreler.
- **Kesintisiz Saatlik Otomasyon:** Yeni ilan bulunmadığında çökmeden mevcut aktif ilanları koruyarak sessizce güncellenir.
