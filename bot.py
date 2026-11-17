import json
import re
import time
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
import schedule

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
    "giriş belgesi", "sınav takvimi", "etik ilkeleri", "daire başkanlığı",
    "rehberleri", "taslakları", "yer değiştirme", "mazerete bağlı",
    "görevde yükselme", "unvan değişikliği", "cübbe", "2024", "2025"
]

SEHIRLER = [
    "Ankara", "İstanbul", "İzmir", "Antalya", "Bursa", "Adana", "Konya",
    "Gaziantep", "Samsun", "Trabzon", "Şanlıurfa", "Batman", "Diyarbakır",
    "Mersin", "Kayseri", "Eskişehir", "Kocaeli", "Sakarya", "Manisa", "Van"
]

# Alım yapılacak kadro/unvan eşleştirme sözlüğü (anahtar -> görünen unvan)
KADRO_SOZLUGU = [
    # Büro, İdari, Adalet & Finans
    ("büro personeli", "Büro Personeli"),
    ("düz memur", "Düz Memur"),
    ("zabıt katibi", "Zabıt Katibi"),
    ("zabıt kâtibi", "Zabıt Katibi"),
    ("mübaşir", "Mübaşir"),
    ("icra katibi", "İcra Katibi"),
    ("infaz ve koruma memuru", "İnfaz ve Koruma Memuru"),
    ("gişe", "Gişe / Servis Görevlisi"),
    ("servis görevlisi", "Servis Görevlisi"),
    ("veznedar", "Veznedar"),
    ("veri hazırlama", "VHKİ (Veri Hazırlama)"),
    ("çağrı merkezi", "Çağrı Merkezi Personeli"),
    ("sekreter", "Sekreter"),
    ("avukat", "Avukat"),
    # Sağlık
    ("hemşire", "Hemşire"),
    ("ebe", "Ebe"),
    ("paramedik", "Paramedik (İlk ve Acil Yardım)"),
    ("ilk ve acil yardım", "Paramedik (İlk ve Acil Yardım)"),
    ("acil tıp teknisyeni", "Acil Tıp Teknisyeni (ATT)"),
    ("tıbbi sekreter", "Tıbbi Sekreter"),
    ("sağlık teknikeri", "Sağlık Teknikeri"),
    ("fizyoterapist", "Fizyoterapist"),
    ("diyetisyen", "Diyetisyen"),
    ("psikolog", "Psikolog"),
    ("sosyal çalışmacı", "Sosyal Çalışmacı"),
    ("eczacı", "Eczacı"),
    ("tabip", "Tabip / Doktor"),
    ("doktor", "Tabip / Doktor"),
    ("veteriner", "Veteriner Hekim"),
    ("laborant", "Laborant"),
    ("röntgen", "Röntgen Teknisyeni"),
    ("sağlık personeli", "Sağlık Personeli"),
    # Bilişim & Mühendislik & Teknik
    ("bilişim personeli", "Sözleşmeli Bilişim Personeli"),
    ("yazılım", "Yazılım Uzmanı / Mühendisi"),
    ("siber güvenlik", "Siber Güvenlik Uzmanı"),
    ("sistem uzmanı", "Sistem / Ağ Uzmanı"),
    ("ağ uzmanı", "Sistem / Ağ Uzmanı"),
    ("bilgisayar mühendisi", "Bilgisayar Mühendisi"),
    ("elektrik-elektronik", "Elektrik-Elektronik Mühendisi"),
    ("inşaat mühendisi", "İnşaat Mühendisi"),
    ("makine mühendisi", "Makine Mühendisi"),
    ("ziraat mühendisi", "Ziraat Mühendisi"),
    ("gıda mühendisi", "Gıda Mühendisi"),
    ("harita mühendisi", "Harita Mühendisi"),
    ("mühendis", "Mühendis"),
    ("mimar", "Mimar"),
    ("tekniker", "Tekniker"),
    ("teknisyen", "Teknisyen"),
    ("programcı", "Programcı"),
    # İşçi, Güvenlik & Destek Hizmetleri
    ("koruma ve güvenlik", "Koruma ve Güvenlik Görevlisi"),
    ("güvenlik görevlisi", "Koruma ve Güvenlik Görevlisi"),
    ("destek personeli", "Destek Personeli"),
    ("temizlik", "Temizlik Görevlisi"),
    ("şoför", "Şoför"),
    ("aşçı", "Aşçı"),
    ("bahçıvan", "Bahçıvan"),
    ("operatör", "İş Makinesi Operatörü"),
    ("bakım", "Bakım-Onarım Personeli"),
    ("sürekli işçi", "Sürekli İşçi"),
    ("işçi alım", "Kamu İşçisi"),
    # Uzman, Denetim & Akademik
    ("uzman yardımcısı", "Uzman Yardımcısı"),
    ("müfettiş yardımcısı", "Müfettiş Yardımcısı"),
    ("denetmen yardımcısı", "Denetmen Yardımcısı"),
    ("kontrolör yardımcısı", "Kontrolör Yardımcısı"),
    ("öğretim görevlisi", "Öğretim Görevlisi"),
    ("araştırma görevlisi", "Araştırma Görevlisi"),
    ("öğretim üyesi", "Öğretim Üyesi"),
    ("öğretmen", "Öğretmen"),
]


def tr_kucuk(metin: str) -> str:
    return metin.replace("İ", "i").replace("I", "ı").lower()


def kadrolari_cikar(metin: str, kategori: str = "") -> list:
    """Başlık ve duyuru içeriğinden alım yapılacak unvan/kadroları çıkarır."""
    b = tr_kucuk(metin)
    bulunanlar = []
    for anahtar, unvan in KADRO_SOZLUGU:
        if anahtar in b and unvan not in bulunanlar:
            # Genel 'Mühendis' etiketini daha spesifik mühendislik varsa ekleme
            if unvan == "Mühendis" and any("Mühendisi" in u for u in bulunanlar):
                continue
            bulunanlar.append(unvan)
        if len(bulunanlar) >= 6:
            break

    if not bulunanlar:
        if "sözleşmeli personel" in b:
            bulunanlar.append("Sözleşmeli Personel (Çeşitli Unvanlar)")
        elif "memur alım" in b:
            bulunanlar.append("Memur (Genel İdare / Meslek)")
        elif kategori == "Sağlık Personeli":
            bulunanlar.append("Sağlık Personeli")
        elif kategori == "Bilişim & Teknik":
            bulunanlar.append("Teknik / Bilişim Personeli")
        elif kategori == "İşçi & Hizmetli":
            bulunanlar.append("Sürekli İşçi / Destek Personeli")
        elif kategori == "Uzman & Akademik":
            bulunanlar.append("Uzman / Akademik Personel")
        else:
            bulunanlar.append("Büro / İdari Personel")

    return bulunanlar


def gercek_ilan_mi(baslik: str, url: str) -> bool:
    b = tr_kucuk(baslik)
    u = url.lower()
    if len(baslik) < 28 or any(h in b for h in HARIC_TUTULACAKLAR):
        return False
    if u.endswith("#") or "javascript:" in u:
        return False
    return any(k in b for k in [
        "personel alım", "memur alım", "işçi alım", "sözleşmeli personel",
        "uzman yardımcısı", "müfettiş yardımcısı", "zabıt katibi", "mübaşir",
        "bilişim personeli", "sağlık personeli", "hemşire", "paramedik",
        "açık pozisyon", "işe alım ilanı", "kpss", "tercih kılavuzu", "kadrolarına"
    ])


def detay_cikar(baslik: str, domain: str):
    b = tr_kucuk(baslik)

    if any(k in b for k in ["hemşire", "sağlık", "paramedik", "ebe", "doktor", "tıbbi", "eczacı"]):
        kategori = "Sağlık Personeli"
    elif any(k in b for k in ["bilişim", "mühendis", "tekniker", "programcı", "yazılım", "siber"]):
        kategori = "Bilişim & Teknik"
    elif any(k in b for k in ["işçi", "temizlik", "şoför", "güvenlik", "hizmetli", "operatör", "koruma"]):
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

    if any(k in domain for k in ["ibb.istanbul", "ankara.bel.tr", "thy.com", "aselsan", "tusas", "roketsan", "bank"]):
        kpss = "KPSS Şartsız"

    duz_mu = any(k in b for k in [
        "4001", "3001", "2001", "bölüm şartsız", "herhangi bir lisans",
        "herhangi bir önlisans", "düz memur", "büro personeli",
        "zabıt katibi", "mübaşir", "gişe", "servis görevlisi", "destek personeli"
    ])

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

    eslesme = re.search(r"(\d{1,5})\s*(?:sözleşmeli|sürekli|memur|personel|işçi|uzman|kadro|kişilik)", b)
    kontenjan = int(eslesme.group(1)) if eslesme else 1

    if "2001" in b:
        nitelik = "2001 (Lise - Bölüm Şartsız)"
    elif "3001" in b:
        nitelik = "3001 (Önlisans - Bölüm Şartsız)"
    elif "4001" in b or duz_mu:
        nitelik = "4001 (Bölüm Şartsız)"
    else:
        nitelik = "Özel Nitelik"

    kadrolar = kadrolari_cikar(baslik, kategori)
    return kategori, egitim, kpss, duz_mu, sehir, kontenjan, nitelik, kadrolar


def ilan_sayfasi_zenginlestir(url: str, headers: dict, mevcut_baslik: str, kategori: str, mevcut_kontenjan: int):
    """İlanın detay sayfasına girerek alınacak unvanları, gerçek kontenjanı ve özet şartları zenginleştirir."""
    if url.lower().endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx")):
        return None
    try:
        r = requests.get(url, headers=headers, timeout=6)
        if r.status_code != 200:
            return None
        if not r.encoding or r.encoding.lower() == "iso-8859-1":
            r.encoding = r.apparent_encoding or "utf-8"
        s = BeautifulSoup(r.text, "html.parser")
        for tag in s(["script", "style", "nav", "header", "footer"]):
            tag.decompose()
        govde = " ".join(s.get_text(" ").split())
        if len(govde) < 80:
            return None

        # Detay metninden kadroları çıkar
        zengin_kadrolar = kadrolari_cikar(f"{mevcut_baslik} {govde[:4000]}", kategori)

        # Detay metninden kontenjan yakala (başlıkta 1 kaldıysa)
        yeni_kontenjan = mevcut_kontenjan
        if mevcut_kontenjan <= 1:
            m = re.search(r"(\d{1,5})\s*(?:adet|kişi|kadro|sözleşmeli personel|sürekli işçi|memur)", tr_kucuk(govde[:3500]))
            if m:
                sayi = int(m.group(1))
                if 1 <= sayi <= 50000:
                    yeni_kontenjan = sayi

        # Anlamlı 1-2 cümlelik özet çıkar
        cumleler = [c.strip() for c in re.split(r"[.!?]\s+", govde[:2500]) if 35 <= len(c.strip()) <= 220]
        ilgili_cumleler = [
            c for c in cumleler
            if any(k in tr_kucuk(c) for k in ["alım", "başvuru", "kpss", "personel", "kadro", "unvan", "mezun"])
        ][:2]

        return {
            "positions": zengin_kadrolar,
            "quota": yeni_kontenjan,
            "requirements": ilgili_cumleler
        }
    except Exception:
        return None


def portallari_tara():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 42 resmi portal taranıyor...")
    tum_ilanlar = []
    gorulen_url = set()
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/131.0.0.0 Safari/537.36",
        "Accept-Language": "tr-TR,tr;q=0.9"
    }

    for idx, (domain, base_url) in enumerate(PORTALLAR):
        try:
            resp = requests.get(base_url, headers=headers, timeout=15)
            if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding or "utf-8"

            soup = BeautifulSoup(resp.text, "html.parser")
            portal_sayac = 0

            for a_idx, link in enumerate(soup.find_all("a", href=True)):
                metin = " ".join(link.get_text().split()).strip()
                tam_url = urljoin(base_url, link["href"].strip())

                if tam_url in gorulen_url or not gercek_ilan_mi(metin, tam_url):
                    continue

                gorulen_url.add(tam_url)
                kategori, egitim, kpss, duz_mu, sehir, kontenjan, nitelik, kadrolar = detay_cikar(metin, domain)
                sartlar = ["İlgili kurumun resmi duyuru metnindeki başvuru şartlarını inceleyiniz."]

                # İlk 4 ilanın detay sayfasına girip alınacak unvanları ve şartları zenginleştir
                if portal_sayac < 4:
                    zengin = ilan_sayfasi_zenginlestir(tam_url, headers, metin, kategori, kontenjan)
                    if zengin:
                        if zengin.get("positions"):
                            kadrolar = zengin["positions"]
                        if zengin.get("quota"):
                            kontenjan = zengin["quota"]
                        if zengin.get("requirements"):
                            sartlar = zengin["requirements"]

                tum_ilanlar.append({
                    "id": f"ga-{idx}-{a_idx}",
                    "sourceDomain": domain,
                    "category": kategori,
                    "institution": domain.upper(),
                    "title": metin[:180],
                    "positions": kadrolar,
                    "city": sehir,
                    "education": egitim,
                    "kpss": kpss,
                    "quota": kontenjan,
                    "publishDate": datetime.now().strftime("%Y-%m-%d"),
                    "endDate": (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d"),
                    "refNo": f"GA-{idx+1}-{a_idx+100}",
                    "qualCode": nitelik,
                    "isDuzMemurluk": duz_mu,
                    "url": tam_url,
                    "requirements": sartlar,
                    "documents": ["e-Devlet Mezuniyet Belgesi", "KPSS Sonuç Belgesi"]
                })
                portal_sayac += 1
                if portal_sayac >= 8:
                    break
        except Exception as hata:
            print(f"Uyarı ({domain}): {hata}")

    if tum_ilanlar:
        with open("ilanlar.json", "w", encoding="utf-8") as f:
            json.dump(tum_ilanlar, f, ensure_ascii=False, indent=2)
        print(f"Tamamlandı: {len(tum_ilanlar)} doğrulanmış ilan 'ilanlar.json' dosyasına yazıldı.")
    else:
        print("Uyarı: Yeni ilan çekilemedi, mevcut ilanlar.json korundu.")


class CORSHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()


if __name__ == "__main__":
    portallari_tara()
    schedule.every().hour.at(":00").do(portallari_tara)
    threading.Thread(
        target=lambda: HTTPServer(("0.0.0.0", 8000), CORSHandler).serve_forever(),
        daemon=True
    ).start()
    print("Canlı JSON sunucusu aktif: http://localhost:8000/ilanlar.json")
    while True:
        schedule.run_pending()
        time.sleep(15)
