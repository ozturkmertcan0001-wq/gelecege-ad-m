import json
import os
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urljoin

import schedule
from bs4 import BeautifulSoup

from helper_bot import GuvenliIstemci

JSON_DOSYASI = "ilanlar.json"

PORTALLAR = [
    ("kamuilan.sbb.gov.tr", "https://kamuilan.sbb.gov.tr"),
    ("kariyerkapisi.gov.tr", "https://kariyerkapisi.gov.tr"),
    ("isealimkariyerkapisi.cbiko.gov.tr", "https://isealimkariyerkapisi.cbiko.gov.tr"),
    ("osym.gov.tr", "https://www.osym.gov.tr"),
    ("iskur.gov.tr", "https://www.iskur.gov.tr"),
    ("resmigazete.gov.tr", "https://www.resmigazete.gov.tr"),
    ("ilan.gov.tr", "https://www.ilan.gov.tr"),
    ("yerelyonetimler.csb.gov.tr", "https://yerelyonetimler.csb.gov.tr"),
    ("kariyer.ibb.istanbul", "https://kariyer.ibb.istanbul/ilanlar"),
    ("kariyer.ankara.bel.tr", "https://kariyer.ankara.bel.tr"),
    ("izmir.bel.tr", "https://www.izmir.bel.tr/tr/Duyurular"),
    ("dsi.gov.tr", "https://www.dsi.gov.tr/Duyurular"),
    ("kgm.gov.tr", "https://www.kgm.gov.tr/Sayfalar/KGM/SiteTr/Kurumsal/Duyurular.aspx"),
    ("botas.gov.tr", "https://www.botas.gov.tr/Duyurular"),
    ("tpao.gov.tr", "https://www.tpao.gov.tr/duyurular"),
    ("dhmi.gov.tr", "https://www.dhmi.gov.tr/Sayfalar/Duyurular.aspx"),
    ("kariyer.thy.com", "https://kariyer.thy.com"),
    ("tcdd.gov.tr", "https://www.tcdd.gov.tr/duyurular"),
    ("teias.gov.tr", "https://www.teias.gov.tr/duyurular"),
    ("ptt.gov.tr", "https://www.ptt.gov.tr/duyurular"),
    ("gib.gov.tr", "https://www.gib.gov.tr/duyurular"),
    ("sgk.gov.tr", "https://www.sgk.gov.tr/Duyuru"),
    ("aile.gov.tr", "https://www.aile.gov.tr/duyurular"),
    ("tarimorman.gov.tr", "https://www.tarimorman.gov.tr/Duyurular"),
    ("yhgm.saglik.gov.tr", "https://yhgm.saglik.gov.tr"),
    ("personel.meb.gov.tr", "https://personel.meb.gov.tr"),
    ("pgm.adalet.gov.tr", "https://pgm.adalet.gov.tr"),
    ("personeltemin.msb.gov.tr", "https://personeltemin.msb.gov.tr"),
    ("personeltemin.jandarma.gov.tr", "https://personeltemin.jandarma.gov.tr"),
    ("pa.edu.tr", "https://www.pa.edu.tr"),
    ("yok.gov.tr", "https://www.yok.gov.tr"),
    ("kariyer.tubitak.gov.tr", "https://kariyer.tubitak.gov.tr"),
    ("vizyonergenc.com", "https://vizyonergenc.com"),
    ("aselsan.com", "https://www.aselsan.com/tr/kariyer"),
    ("tusas.com", "https://www.tusas.com/kariyer"),
    ("roketsan.com.tr", "https://www.roketsan.com.tr/tr/kariyer"),
    ("kizilaykariyer.com", "https://www.kizilaykariyer.com"),
    ("ziraatbank.com.tr", "https://www.ziraatbank.com.tr/tr/bankamiz/insan-kaynaklari/acik-pozisyonlar"),
    ("halkbank.com.tr", "https://www.halkbank.com.tr/tr/bankamiz/insan-kaynaklari.html"),
    ("vakifbank.com.tr", "https://www.vakifbank.com.tr/insan-kaynaklari.aspx?pageID=203"),
    ("tcmb.gov.tr", "https://insankaynaklari.tcmb.gov.tr"),
    ("bddk.org.tr", "https://www.bddk.org.tr/Duyurular"),
]

HARIC_TUTULACAKLAR = [
    "ihale", "zeyilname", "sonuç ilanı", "sonuç duyurusu", "sonuçları",
    "sonuçlarının açıklanması", "yerleştirme sonuç", "mülakat sonuç",
    "nihai başarı", "kazanan aday", "yedek aday", "evrak teslim",
    "branş bazında", "sıralama", "cevap kağıt", "cevap kâğıt",
    "soru kitapçık", "cevap anahtar", "aday cevap",
    "sınav başvurusu", "sınav başvurularının", "geç başvuru",
    "sınav merkezi", "sınav yeri", "sınav yerleri",
    "giriş belgesi", "sınav takvimi", "etik ilkeleri", "daire başkanlığı",
    "rehberleri", "taslakları", "yer değiştirme", "mazerete bağlı",
    "görevde yükselme", "unvan değişikliği", "cübbe", "2021", "2022", "2023",
]

SEHIRLER = [
    "Ankara", "İstanbul", "İzmir", "Antalya", "Bursa", "Adana", "Konya",
    "Gaziantep", "Samsun", "Trabzon", "Şanlıurfa", "Batman", "Diyarbakır",
    "Mersin", "Kayseri", "Eskişehir", "Kocaeli", "Sakarya", "Manisa", "Van",
    "Tekirdağ", "Balıkesir", "Muğla", "Aydın", "Denizli", "Malatya", "Erzurum",
    "Elazığ", "Sivas", "Hatay", "Kahramanmaraş", "Ordu", "Çanakkale", "Edirne",
]

MESLEK_SOZLUGU = [
    # Sağlık & Sosyal Hizmetler
    ("psikolog", "Psikolog"),
    ("sosyal çalışmacı", "Sosyal Çalışmacı"),
    ("sosyolog", "Sosyolog"),
    ("çocuk gelişimcisi", "Çocuk Gelişimcisi"),
    ("çocuk gelişimi", "Çocuk Gelişimcisi"),
    ("hemşire", "Hemşire"),
    ("ebe", "Ebe"),
    ("paramedik", "Paramedik (İlk ve Acil Yardım)"),
    ("ilk ve acil yardım", "Paramedik (İlk ve Acil Yardım)"),
    ("acil tıp teknisyeni", "Acil Tıp Teknisyeni (ATT)"),
    ("tıbbi sekreter", "Tıbbi Sekreter"),
    ("fizyoterapist", "Fizyoterapist"),
    ("diyetisyen", "Diyetisyen"),
    ("odyolog", "Odyolog"),
    ("ergoterapist", "Ergoterapist"),
    ("dil ve konuşma terapisti", "Dil ve Konuşma Terapisti"),
    ("perfüzyonist", "Perfüzyonist"),
    ("eczacı", "Eczacı"),
    ("diş tabibi", "Diş Tabibi"),
    ("diş hekimi", "Diş Tabibi"),
    ("tabip", "Tabip / Doktor"),
    ("doktor", "Tabip / Doktor"),
    ("veteriner", "Veteriner Hekim"),
    ("biyolog", "Biyolog"),
    ("kimyager", "Kimyager"),
    ("laborant", "Laborant"),
    ("tıbbi görüntüleme", "Tıbbi Görüntüleme (Röntgen)"),
    ("röntgen", "Tıbbi Görüntüleme (Röntgen)"),
    ("anestezi", "Anestezi Teknikeri"),
    ("diyaliz", "Diyaliz Teknikeri"),
    ("ameliyathane", "Ameliyathane Teknikeri"),
    ("ağız ve diş sağlığı", "Ağız ve Diş Sağlığı Teknikeri"),
    ("optisyen", "Optisyen"),
    ("sağlık teknikeri", "Sağlık Teknikeri"),
    ("sağlık personeli", "Sağlık Personeli"),

    # Mühendislik, Mimarlık & Fen Bilimleri
    ("makine mühendisi", "Makine Mühendisi"),
    ("makina mühendisi", "Makine Mühendisi"),
    ("inşaat mühendisi", "İnşaat Mühendisi"),
    ("elektrik-elektronik mühendisi", "Elektrik-Elektronik Mühendisi"),
    ("elektrik elektronik mühendisi", "Elektrik-Elektronik Mühendisi"),
    ("elektrik mühendisi", "Elektrik Mühendisi"),
    ("elektronik mühendisi", "Elektronik Mühendisi"),
    ("bilgisayar mühendisi", "Bilgisayar Mühendisi"),
    ("yazılım mühendisi", "Yazılım Mühendisi"),
    ("endüstri mühendisi", "Endüstri Mühendisi"),
    ("çevre mühendisi", "Çevre Mühendisi"),
    ("gıda mühendisi", "Gıda Mühendisi"),
    ("ziraat mühendisi", "Ziraat Mühendisi"),
    ("orman mühendisi", "Orman Mühendisi"),
    ("harita mühendisi", "Harita Mühendisi"),
    ("jeoloji mühendisi", "Jeoloji Mühendisi"),
    ("jeofizik mühendisi", "Jeofizik Mühendisi"),
    ("maden mühendisi", "Maden Mühendisi"),
    ("metalurji ve malzeme mühendisi", "Metalurji ve Malzeme Mühendisi"),
    ("kimya mühendisi", "Kimya Mühendisi"),
    ("mekatronik mühendisi", "Mekatronik Mühendisi"),
    ("uçak mühendisi", "Uçak / Havacılık Mühendisi"),
    ("havacılık mühendisi", "Uçak / Havacılık Mühendisi"),
    ("otomotiv mühendisi", "Otomotiv Mühendisi"),
    ("biyomedikal mühendisi", "Biyomedikal Mühendisi"),
    ("enerji sistemleri mühendisi", "Enerji Sistemleri Mühendisi"),
    ("mühendis", "Mühendis"),
    ("iç mimar", "İç Mimar"),
    ("peyzaj mimarı", "Peyzaj Mimarı"),
    ("mimar", "Mimar"),
    ("şehir plancısı", "Şehir Plancısı"),
    ("istatistikçi", "İstatistikçi"),
    ("matematikçi", "Matematikçi"),
    ("fizikçi", "Fizikçi"),

    # Büro, Adalet, Finans & Kültür
    ("büro personeli", "Büro Personeli"),
    ("düz memur", "Düz Memur"),
    ("veri hazırlama", "VHKİ (Veri Hazırlama)"),
    ("zabıt katibi", "Zabıt Katibi"),
    ("zabıt kâtibi", "Zabıt Katibi"),
    ("mübaşir", "Mübaşir"),
    ("icra katibi", "İcra Katibi"),
    ("icra kâtibi", "İcra Katibi"),
    ("infaz ve koruma memuru", "İnfaz ve Koruma Memuru"),
    ("avukat", "Avukat"),
    ("mütercim", "Mütercim-Tercüman"),
    ("tercüman", "Mütercim-Tercüman"),
    ("kütüphaneci", "Kütüphaneci"),
    ("arkeolog", "Arkeolog"),
    ("sanat tarihçisi", "Sanat Tarihçisi"),
    ("müze araştırmacısı", "Müze Araştırmacısı"),
    ("restoratör", "Restoratör"),
    ("gişe", "Gişe / Servis Görevlisi"),
    ("servis görevlisi", "Servis Görevlisi"),
    ("veznedar", "Veznedar"),
    ("çağrı merkezi", "Çağrı Merkezi Personeli"),
    ("sekreter", "Sekreter"),
    ("muhasebeci", "Muhasebeci"),

    # Bilişim & Tekniker / Teknisyen
    ("bilişim personeli", "Sözleşmeli Bilişim Personeli"),
    ("yazılım uzmanı", "Yazılım Uzmanı"),
    ("siber güvenlik", "Siber Güvenlik Uzmanı"),
    ("sistem uzmanı", "Sistem / Ağ Uzmanı"),
    ("ağ uzmanı", "Sistem / Ağ Uzmanı"),
    ("veritabanı uzmanı", "Veritabanı Uzmanı"),
    ("programcı", "Programcı"),
    ("bilgisayar teknikeri", "Bilgisayar Teknikeri"),
    ("elektrik teknikeri", "Elektrik Teknikeri"),
    ("elektronik teknikeri", "Elektronik Teknikeri"),
    ("makine teknikeri", "Makine Teknikeri"),
    ("inşaat teknikeri", "İnşaat Teknikeri"),
    ("harita teknikeri", "Harita Teknikeri"),
    ("otomotiv teknikeri", "Otomotiv Teknikeri"),
    ("iklimlendirme", "İklimlendirme Teknikeri"),
    ("tekniker", "Tekniker"),
    ("teknisyen", "Teknisyen"),

    # İşçi, Güvenlik & Destek Hizmetleri
    ("koruma ve güvenlik", "Koruma ve Güvenlik Görevlisi"),
    ("güvenlik görevlisi", "Koruma ve Güvenlik Görevlisi"),
    ("destek personeli", "Destek Personeli"),
    ("temizlik", "Temizlik Görevlisi"),
    ("şoför", "Şoför"),
    ("aşçı", "Aşçı"),
    ("bahçıvan", "Bahçıvan"),
    ("kaloriferci", "Kaloriferci"),
    ("elektrikçi", "Elektrikçi"),
    ("sıhhi tesisat", "Sıhhi Tesisatçı"),
    ("marangoz", "Marangoz"),
    ("kaynakçı", "Kaynakçı"),
    ("boyacı", "Boyacı"),
    ("operatör", "İş Makinesi Operatörü"),
    ("bakım", "Bakım-Onarım Personeli"),
    ("sürekli işçi", "Sürekli İşçi"),
    ("işçi alım", "Kamu İşçisi"),

    # Uzman, Denetim & Akademik
    ("gelir uzman yardımcısı", "Gelir Uzman Yardımcısı"),
    ("vergi müfettiş yardımcısı", "Vergi Müfettiş Yardımcısı"),
    ("uzman yardımcısı", "Uzman Yardımcısı"),
    ("müfettiş yardımcısı", "Müfettiş Yardımcısı"),
    ("denetmen yardımcısı", "Denetmen Yardımcısı"),
    ("kontrolör yardımcısı", "Kontrolör Yardımcısı"),
    ("öğretim görevlisi", "Öğretim Görevlisi"),
    ("araştırma görevlisi", "Araştırma Görevlisi"),
    ("öğretim üyesi", "Öğretim Üyesi"),
    ("öğretmen", "Öğretmen"),
]

AYLAR_TR = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4, "mayıs": 5, "haziran": 6,
    "temmuz": 7, "ağustos": 8, "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}


def tr_kucuk(metin: str) -> str:
    return (metin or "").replace("İ", "i").replace("I", "ı").lower()


def gercek_ilan_mi(baslik: str, url: str) -> bool:
    b = tr_kucuk(baslik)
    u = (url or "").lower()
    if len(baslik) < 24 or len(baslik) > 260:
        return False
    if any(h in b for h in HARIC_TUTULACAKLAR):
        return False
    if not u.startswith(("http://", "https://")):
        return False
    if u.endswith("#") or "javascript:" in u or "mailto:" in u:
        return False

    # ÖSYM duyurularında yalnızca personel yerleştirme / tercih kılavuzlarını kabul et
    if "osym.gov.tr" in u:
        return any(
            k in b
            for k in [
                "tercih kılavuzu",
                "tercihlerinin alınması",
                "yerleştirme kılavuzu",
                "personel alım",
                "memur alım",
            ]
        )

    return any(
        k in b
        for k in [
            "personel alım", "memur alım", "işçi alım", "sözleşmeli personel",
            "uzman yardımcısı", "müfettiş yardımcısı", "zabıt katibi", "zabıt kâtibi",
            "mübaşir", "bilişim personeli", "sağlık personeli", "hemşire",
            "paramedik", "psikolog", "mühendis", "açık pozisyon", "işe alım ilanı",
            "kpss tercih", "kpss ile", "kpss puanı", "merkezi yerleştirme",
            "tercih kılavuzu", "tercihlerinin alınması", "kadrolarına", "personel istihdam",
            "sürekli işçi", "koruma ve güvenlik", "destek personeli",
        ]
    )


def meslekleri_cikar(metin: str, kategori: str = "") -> tuple:
    b = tr_kucuk(metin)
    bulunanlar = []
    detayli = []

    for anahtar, unvan in MESLEK_SOZLUGU:
        if len(anahtar) <= 5:
            desen = r"\b" + re.escape(anahtar) + r"(?:i|ı|u|ü|ler|lar|leri|ları)?\b"
            eslesme_var = re.search(desen, b) is not None
        else:
            eslesme_var = anahtar in b

        if eslesme_var and unvan not in bulunanlar:
            if unvan == "Mühendis" and any("Mühendisi" in u for u in bulunanlar):
                continue
            if unvan == "Mimar" and any(u in ("İç Mimar", "Peyzaj Mimarı") for u in bulunanlar):
                continue
            if unvan == "Tekniker" and any("Teknikeri" in u for u in bulunanlar):
                continue

            bulunanlar.append(unvan)

            k_on = re.search(r"\b(\d{1,4})\s*(?:adet|kişi)?\s*" + re.escape(anahtar), b)
            k_arka = re.search(
                re.escape(anahtar) + r"(?:i|ı|u|ü|ler|lar|leri|ları)?\s*[\(\[\:\-\|]?\s*(\d{1,4})\s*(?:adet|kişi|kadro)?[\)\]]?",
                b,
            )
            adet = None
            for m in (k_on, k_arka):
                if m:
                    sayi = int(m.group(1))
                    if 1 <= sayi <= 25000 and sayi not in (2001, 3001, 4001, 2024, 2025, 2026, 2027):
                        adet = sayi
                        break

            detayli.append(f"{unvan} ({adet})" if adet else unvan)

        if len(bulunanlar) >= 25:
            break

    if not bulunanlar:
        if "sözleşmeli personel" in b:
            fallback = "Sözleşmeli Personel (Çeşitli Unvanlar)"
        elif "memur alım" in b:
            fallback = "Memur (Genel İdare / Meslek)"
        elif kategori == "Sağlık Personeli":
            fallback = "Sağlık Personeli"
        elif kategori == "Bilişim & Teknik":
            fallback = "Teknik / Bilişim Personeli"
        elif kategori == "İşçi & Hizmetli":
            fallback = "Sürekli İşçi / Destek Personeli"
        elif kategori == "Uzman & Akademik":
            fallback = "Uzman / Akademik Personel"
        else:
            fallback = "Büro / İdari Personel"
        bulunanlar.append(fallback)
        detayli.append(fallback)

    return bulunanlar, detayli


def son_basvuru_tarihi_bul(metin: str) -> str:
    b = tr_kucuk(metin)
    bugun = datetime.now()
    aday_tarihler = []

    for m in re.finditer(r"(\d{1,2})[./](\d{1,2})[./](202[6-8])", b):
        gun, ay, yil = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            dt = datetime(yil, ay, gun)
            if bugun - timedelta(days=1) <= dt <= bugun + timedelta(days=120):
                aday_tarihler.append(dt)
        except ValueError:
            continue

    for m in re.finditer(
        r"(\d{1,2})\s+(ocak|şubat|mart|nisan|mayıs|haziran|temmuz|ağustos|eylül|ekim|kasım|aralık)\s+(202[6-8])",
        b,
    ):
        gun = int(m.group(1))
        ay = AYLAR_TR.get(m.group(2), 0)
        yil = int(m.group(3))
        try:
            dt = datetime(yil, ay, gun)
            if bugun - timedelta(days=1) <= dt <= bugun + timedelta(days=120):
                aday_tarihler.append(dt)
        except ValueError:
            continue

    if aday_tarihler:
        return max(aday_tarihler).strftime("%Y-%m-%d")
    return (bugun + timedelta(days=10)).strftime("%Y-%m-%d")


def sartlari_cikar(govde: str) -> list:
    ham_parcalar = re.split(r"(?<=[.!?])\s+|\n+|\s*•\s*|\s*-\s+(?=[A-ZÇĞİÖŞÜ])", govde[:18000])
    sart_anahtarlari = [
        "kpss", "puan", "p3", "p93", "p94", "mezun", "lisans", "önlisans", "ortaöğretim",
        "lise", "2001", "3001", "4001", "yaşını doldurmamış", "yaş şartı", "657 sayılı",
        "4/b", "askerlik", "sertifika", "sürücü belgesi", "ehliyet", "ikamet",
        "başvuru tarih", "nitelik", "şart", "belge", "sözlü sınav", "uygulamalı sınav",
    ]
    secilenler = []
    gorulen_oz = set()

    for parca in ham_parcalar:
        temiz = " ".join(parca.split()).strip(" -•:;·")
        if not (32 <= len(temiz) <= 260):
            continue
        kucuk = tr_kucuk(temiz)
        if any(g in kucuk for g in ["çerez", "cookie", "tüm hakları saklıdır", "ana sayfa", "iletişim", "menü"]):
            continue
        if any(k in kucuk for k in sart_anahtarlari):
            oz = kucuk[:45]
            if oz not in gorulen_oz:
                gorulen_oz.add(oz)
                secilenler.append(temiz)
        if len(secilenler) >= 6:
            break

    if not secilenler:
        secilenler.append("İlgili kurumun resmi duyuru sayfasındaki genel ve özel başvuru şartlarını inceleyiniz.")
    return secilenler


def belgeleri_cikar(govde: str) -> list:
    b = tr_kucuk(govde[:12000])
    belgeler = ["e-Devlet Mezuniyet Belgesi", "KPSS Sonuç Belgesi"]
    aday_belgeler = [
        ("adli sicil", "Adli Sicil Kaydı (e-Devlet)"),
        ("askerlik", "Askerlik Durum Belgesi"),
        ("sağlık kurulu", "Tam Teşekküllü Sağlık Kurulu Raporu"),
        ("sürücü belgesi", "Sürücü Belgesi (Ehliyet) Fotokopisi"),
        ("ehliyet", "Sürücü Belgesi (Ehliyet) Fotokopisi"),
        ("sertifika", "Mesleki Yeterlilik / Kurs Sertifikası"),
        ("özgeçmiş", "Detaylı Özgeçmiş (CV)"),
        ("ikamet", "Yerleşim Yeri (İkametgah) Belgesi"),
        ("fotoğraf", "Biyometrik / Vesikalık Fotoğraf"),
    ]
    for anahtar, etiket in aday_belgeler:
        if anahtar in b and etiket not in belgeler:
            belgeler.append(etiket)
        if len(belgeler) >= 6:
            break
    return belgeler


def temel_analiz(baslik: str, domain: str):
    b = tr_kucuk(baslik)

    if any(k in b for k in ["hemşire", "sağlık", "paramedik", "ebe", "doktor", "tıbbi", "eczacı", "psikolog", "fizyoterapist", "diyetisyen"]):
        kategori = "Sağlık Personeli"
    elif any(k in b for k in ["bilişim", "mühendis", "mimar", "tekniker", "teknisyen", "programcı", "yazılım", "siber"]):
        kategori = "Bilişim & Teknik"
    elif any(k in b for k in ["işçi", "temizlik", "şoför", "güvenlik", "hizmetli", "operatör", "koruma", "aşçı", "kaloriferci"]):
        kategori = "İşçi & Hizmetli"
    elif any(k in b for k in ["uzman", "müfettiş", "öğretim", "araştırma", "akademik", "denetmen"]):
        kategori = "Uzman & Akademik"
    else:
        kategori = "Büro & İdari"

    if any(k in b for k in ["2001", "ortaöğretim", "lise"]):
        egitim, kpss = "Ortaöğretim", "KPSS P94 (Ortaöğretim)"
    elif any(k in b for k in ["3001", "önlisans", "ön lisans", "tekniker", "paramedik"]):
        egitim, kpss = "Önlisans", "KPSS P93 (Önlisans)"
    elif any(k in b for k in ["ilköğretim", "sürekli işçi", "işçi alım"]):
        egitim, kpss = "İlköğretim", "KPSS Şartsız"
    else:
        egitim, kpss = "Lisans", "KPSS P3 (Lisans)"

    if any(k in domain for k in ["ibb.istanbul", "ankara.bel.tr", "thy.com", "aselsan", "tusas", "roketsan", "bank", "vizyonergenc"]):
        kpss = "KPSS Şartsız"

    duz_mu = any(
        k in b
        for k in [
            "4001", "3001", "2001", "bölüm şartsız", "herhangi bir lisans",
            "herhangi bir önlisans", "düz memur", "büro personeli",
            "zabıt katibi", "zabıt kâtibi", "mübaşir", "gişe", "servis görevlisi", "destek personeli",
        ]
    )

    sehir = "Türkiye Geneli"
    if "ibb.istanbul" in domain:
        sehir = "İstanbul"
    elif "ankara.bel.tr" in domain:
        sehir = "Ankara"
    elif "izmir.bel.tr" in domain:
        sehir = "İzmir"
    else:
        for s in SEHIRLER:
            if tr_kucuk(s) in b:
                sehir = s
                break

    eslesme = re.search(r"\b(\d{1,5})\s*(?:sözleşmeli|sürekli|memur|personel|işçi|uzman|kadro|kişilik)", b)
    kontenjan = int(eslesme.group(1)) if eslesme else 1

    if "2001" in b:
        nitelik = "2001 (Lise - Bölüm Şartsız)"
    elif "3001" in b:
        nitelik = "3001 (Önlisans - Bölüm Şartsız)"
    elif "4001" in b or duz_mu:
        nitelik = "4001 (Bölüm Şartsız)"
    else:
        nitelik = "Özel Nitelik"

    meslekler, detayli_meslekler = meslekleri_cikar(baslik, kategori)
    return kategori, egitim, kpss, duz_mu, sehir, kontenjan, nitelik, meslekler, detayli_meslekler


def ilan_detay_analiz_et(istemci: GuvenliIstemci, ilan: dict) -> dict:
    """Her bir ilanın kendi sayfasına girer; site engelli veya kapalıysa çökmek yerine mevcut veriyi döndürür."""
    try:
        yanit = istemci.sayfa_getir(ilan["url"], timeout=12, js_destegi=True)
        if not yanit.get("ok"):
            return ilan

        kadro_satirlari = []
        govde = ""

        if yanit.get("pdf_text"):
            govde = yanit["pdf_text"]
        elif yanit.get("html"):
            soup = BeautifulSoup(yanit["html"], "html.parser")
            for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                tag.decompose()

            govde = soup.get_text("\n")

            for tr in soup.find_all("tr"):
                hucreler = [" ".join(td.get_text().split()) for td in tr.find_all(["td", "th"]) if td.get_text(strip=True)]
                if 2 <= len(hucreler) <= 8:
                    satir = " — ".join(hucreler[:4])
                    if 8 <= len(satir) <= 150 and any(
                        k in tr_kucuk(satir)
                        for k in [
                            "mühendis", "psikolog", "hemşire", "paramedik", "tekniker", "teknisyen",
                            "büro", "memur", "işçi", "şoför", "güvenlik", "uzman", "avukat", "tabip",
                            "ebe", "diyetisyen", "fizyoterapist", "katibi", "kâtibi", "mübaşir", "unvan", "kadro",
                        ]
                    ):
                        if satir not in kadro_satirlari:
                            kadro_satirlari.append(satir)
                if len(kadro_satirlari) >= 15:
                    break

        temiz_govde = " ".join(govde.split())
        if len(temiz_govde) < 80:
            return ilan

        birlesik_metin = f"{ilan['title']} {temiz_govde[:25000]}"
        meslekler, detayli_meslekler = meslekleri_cikar(birlesik_metin, ilan["category"])
        sartlar = sartlari_cikar(govde)
        belgeler = belgeleri_cikar(temiz_govde)
        son_tarih = son_basvuru_tarihi_bul(temiz_govde[:8000])

        kucuk_icerik = tr_kucuk(temiz_govde[:12000])
        if re.search(r"\b(2001|3001|4001)\b", kucuk_icerik) or "bölüm şartsız" in kucuk_icerik:
            ilan["isDuzMemurluk"] = True
            if "2001" in kucuk_icerik and "3001" in kucuk_icerik and "4001" in kucuk_icerik:
                ilan["qualCode"] = "2001 / 3001 / 4001 (Bölüm Şartsız)"
            elif "3001" in kucuk_icerik:
                ilan["qualCode"] = "3001 (Önlisans - Bölüm Şartsız)"
            elif "2001" in kucuk_icerik:
                ilan["qualCode"] = "2001 (Lise - Bölüm Şartsız)"
            else:
                ilan["qualCode"] = "4001 (Lisans - Bölüm Şartsız)"

        if ilan["quota"] <= 1:
            m = re.search(
                r"\b(\d{1,5})\s*(?:adet|kişi|kadro|sözleşmeli personel|sürekli işçi|memur|personel)\b",
                kucuk_icerik[:6000],
            )
            if m:
                sayi = int(m.group(1))
                if 1 <= sayi <= 50000:
                    ilan["quota"] = sayi

        ilan["positions"] = meslekler
        ilan["positionDetails"] = detayli_meslekler
        ilan["kadroRows"] = kadro_satirlari
        ilan["requirements"] = sartlar
        ilan["documents"] = belgeler
        ilan["endDate"] = son_tarih
        ilan["detailParsed"] = True
        return ilan
    except Exception:
        return ilan


def mevcut_ilanlari_yukle() -> list:
    if not os.path.exists(JSON_DOSYASI):
        return []
    try:
        with open(JSON_DOSYASI, "r", encoding="utf-8") as f:
            veri = json.load(f)
            return veri if isinstance(veri, list) else []
    except Exception:
        return []


def tek_portal_tara(istemci: GuvenliIstemci, idx: int, domain: str, base_url: str) -> list:
    bulunan_adaylar = []
    try:
        yanit = istemci.sayfa_getir(base_url, timeout=15, js_destegi=True)
        if not yanit.get("ok") or not yanit.get("html"):
            print(f"Bilgi ({domain}): Portal erişime kapalı veya koruma altında, atlandı.")
            return []

        soup = BeautifulSoup(yanit["html"], "html.parser")
        yerel_url = set()

        for a_idx, link in enumerate(soup.find_all("a", href=True)):
            metin = " ".join(link.get_text().split()).strip()
            tam_url = urljoin(base_url, link["href"].strip())

            if tam_url in yerel_url or not gercek_ilan_mi(metin, tam_url):
                continue

            yerel_url.add(tam_url)
            kategori, egitim, kpss, duz_mu, sehir, kontenjan, nitelik, meslekler, detayli = temel_analiz(metin, domain)

            bulunan_adaylar.append(
                {
                    "id": f"ga-{idx}-{a_idx}",
                    "sourceDomain": domain,
                    "category": kategori,
                    "institution": domain.upper(),
                    "title": metin[:200],
                    "positions": meslekler,
                    "positionDetails": detayli,
                    "kadroRows": [],
                    "city": sehir,
                    "education": egitim,
                    "kpss": kpss,
                    "quota": kontenjan,
                    "publishDate": datetime.now().strftime("%Y-%m-%d"),
                    "endDate": (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
                    "refNo": f"GA-{idx + 1}-{a_idx + 100}",
                    "qualCode": nitelik,
                    "isDuzMemurluk": duz_mu,
                    "url": tam_url,
                    "requirements": ["İlgili kurumun resmi duyuru metnindeki başvuru şartlarını inceleyiniz."],
                    "documents": ["e-Devlet Mezuniyet Belgesi", "KPSS Sonuç Belgesi"],
                    "detailParsed": False,
                }
            )
            if len(bulunan_adaylar) >= 8:
                break
    except Exception as hata:
        print(f"Bilgi ({domain}): Güvenli atlama ({type(hata).__name__}).")
    return bulunan_adaylar


def portallari_tara():
    baslangic = time.time()
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 42 resmi portal taranıyor...")

    istemci = GuvenliIstemci()
    mevcut_liste = [
        item for item in mevcut_ilanlari_yukle()
        if gercek_ilan_mi(item.get("title", ""), item.get("url", ""))
    ]
    mevcut_harita = {item.get("url"): item for item in mevcut_liste if item.get("url")}

    yeni_aday_ilanlar = []
    gorulen_url = set()

    with ThreadPoolExecutor(max_workers=8) as havuz:
        gelecekler = [
            havuz.submit(tek_portal_tara, istemci, idx, domain, url)
            for idx, (domain, url) in enumerate(PORTALLAR)
        ]
        for f in as_completed(gelecekler):
            try:
                sonuc_listesi = f.result()
            except Exception:
                sonuc_listesi = []

            for ilan in sonuc_listesi:
                u = ilan["url"]
                if u in gorulen_url:
                    continue
                gorulen_url.add(u)

                if u in mevcut_harita:
                    eski = mevcut_harita[u]
                    if (
                        eski.get("detailParsed")
                        or len(eski.get("requirements", [])) > 1
                        or len(eski.get("positionDetails", [])) > 1
                        or len(eski.get("kadroRows", [])) > 0
                    ):
                        continue
                    ilan["publishDate"] = eski.get("publishDate", ilan["publishDate"])
                    ilan["id"] = eski.get("id", ilan["id"])

                yeni_aday_ilanlar.append(ilan)

    zengin_ilanlar = []
    if yeni_aday_ilanlar:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] {len(yeni_aday_ilanlar)} yeni/eksik ilanın detay sayfası inceleniyor...")
        with ThreadPoolExecutor(max_workers=6) as detay_havuzu:
            detay_isler = [detay_havuzu.submit(ilan_detay_analiz_et, istemci, ilan) for ilan in yeni_aday_ilanlar]
            for f in as_completed(detay_isler):
                try:
                    zengin_ilanlar.append(f.result())
                except Exception:
                    pass

    bugun_str = datetime.now().strftime("%Y-%m-%d")
    sonuc_haritasi = {}

    for eski in mevcut_liste:
        u = eski.get("url")
        if u and eski.get("endDate", "2099-12-31") >= bugun_str:
            sonuc_haritasi[u] = eski

    yeni_eklenen_sayisi = 0
    for yeni in zengin_ilanlar:
        u = yeni["url"]
        if u not in sonuc_haritasi:
            yeni_eklenen_sayisi += 1
            sonuc_haritasi[u] = yeni
        else:
            if yeni.get("detailParsed") or len(yeni.get("requirements", [])) > 1:
                sonuc_haritasi[u] = yeni

    nihai_liste = list(sonuc_haritasi.values())

    if not nihai_liste and mevcut_liste:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Portallara geçici erişim sağlanamadı; mevcut {len(mevcut_liste)} ilan korundu.")
        return

    nihai_liste.sort(key=lambda x: (x.get("publishDate", ""), x.get("id", "")), reverse=True)
    sure = round(time.time() - baslangic, 1)

    try:
        with open(JSON_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(nihai_liste, f, ensure_ascii=False, indent=2)
        print(
            f"[{datetime.now().strftime('%H:%M:%S')}] Tamamlandı ({sure} sn): "
            f"+{yeni_eklenen_sayisi} yeni ilan, toplam {len(nihai_liste)} aktif ilan kaydedildi."
        )
    except Exception as hata:
        print(f"Uyarı: Dosya yazma hatası ({hata}), sistem çalışmaya devam ediyor.")


class CORSHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        super().end_headers()


if __name__ == "__main__":
    try:
        portallari_tara()
    except Exception as genel_hata:
        print(f"Tarama uyarısı (kurtarıldı): {genel_hata}")

    if "--once" in sys.argv:
        sys.exit(0)

    schedule.every().hour.at(":00").do(portallari_tara)
    threading.Thread(
        target=lambda: HTTPServer(("0.0.0.0", 8000), CORSHandler).serve_forever(),
        daemon=True,
    ).start()
    print("Canlı JSON sunucusu aktif: http://localhost:8000/ilanlar.json")
    while True:
        try:
            schedule.run_pending()
        except Exception as e:
            print(f"Zamanlayıcı uyarısı (kurtarıldı): {e}")
        time.sleep(15)
