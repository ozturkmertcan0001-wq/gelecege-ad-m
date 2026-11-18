import json
import os
import random
import re
from datetime import datetime, timedelta
from urllib.parse import urljoin

from playwright.sync_api import sync_playwright

try:
    from dotenv import load_dotenv
    from google import genai
    from google.genai import types
    from pydantic import BaseModel, Field

    load_dotenv()
    GEMINI_AKTIF = bool(os.getenv("GEMINI_API_KEY"))
except ImportError:
    GEMINI_AKTIF = False

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
    "görevde yükselme", "unvan değişikliği", "cübbe", "2023", "2024", "2025",
    "kazanan", "yedek liste", "atama sonuç", "mülakat sonuç"
]

SEHIRLER = [
    "Ankara", "İstanbul", "İzmir", "Antalya", "Bursa", "Adana", "Konya",
    "Gaziantep", "Samsun", "Trabzon", "Şanlıurfa", "Batman", "Diyarbakır",
    "Mersin", "Kayseri", "Eskişehir", "Kocaeli", "Sakarya", "Manisa", "Van",
    "Erzurum", "Malatya", "Hatay", "Balıkesir", "Tekirdağ", "Muğla", "Aydın"
]

KADRO_SOZLUGU = [
    ("büro yöneticisi", "Büro Yöneticisi"),
    ("büro yönetimi", "Büro Yöneticisi / Büro Personeli"),
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
    ("psikolog", "Psikolog"),
    ("sosyal çalışmacı", "Sosyal Çalışmacı"),
    ("çocuk gelişimci", "Çocuk Gelişimcisi"),
    ("sosyolog", "Sosyolog"),
    ("hemşire", "Hemşire"),
    ("ebe", "Ebe"),
    ("paramedik", "Paramedik (İlk ve Acil Yardım)"),
    ("ilk ve acil yardım", "Paramedik (İlk ve Acil Yardım)"),
    ("acil tıp teknisyeni", "Acil Tıp Teknisyeni (ATT)"),
    ("tıbbi sekreter", "Tıbbi Sekreter"),
    ("sağlık teknikeri", "Sağlık Teknikeri"),
    ("fizyoterapist", "Fizyoterapist"),
    ("diyetisyen", "Diyetisyen"),
    ("eczacı", "Eczacı"),
    ("tabip", "Tabip / Doktor"),
    ("doktor", "Tabip / Doktor"),
    ("veteriner", "Veteriner Hekim"),
    ("laborant", "Laborant"),
    ("röntgen", "Röntgen Teknisyeni"),
    ("sağlık personeli", "Sağlık Personeli"),
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
    ("şoför", "Şoför"),
    ("sürücü", "Şoför"),
    ("koruma ve güvenlik", "Koruma ve Güvenlik Görevlisi"),
    ("güvenlik görevlisi", "Koruma ve Güvenlik Görevlisi"),
    ("destek personeli", "Destek Personeli"),
    ("temizlik", "Temizlik Görevlisi"),
    ("hizmetli", "Hizmetli / Destek Personeli"),
    ("aşçı", "Aşçı"),
    ("bahçıvan", "Bahçıvan"),
    ("operatör", "İş Makinesi Operatörü"),
    ("bakım", "Bakım-Onarım Personeli"),
    ("sürekli işçi", "Sürekli İşçi"),
    ("işçi alım", "Kamu İşçisi"),
    ("uzman yardımcısı", "Uzman Yardımcısı"),
    ("müfettiş yardımcısı", "Müfettiş Yardımcısı"),
    ("denetmen yardımcısı", "Denetmen Yardımcısı"),
    ("kontrolör yardımcısı", "Kontrolör Yardımcısı"),
    ("öğretim görevlisi", "Öğretim Görevlisi"),
    ("araştırma görevlisi", "Araştırma Görevlisi"),
    ("öğretim üyesi", "Öğretim Üyesi"),
    ("öğretmen", "Öğretmen"),
]

BOLUM_SOZLUGU = [
    ("büro yönetimi ve yönetici asistanlığı", "Büro Yönetimi ve Yönetici Asistanlığı"),
    ("büro yönetimi", "Büro Yönetimi / Büro Yöneticiliği"),
    ("psikoloji", "Psikoloji"),
    ("ilk ve acil yardım", "İlk ve Acil Yardım (Paramedik)"),
    ("bilgisayar programcılığı", "Bilgisayar Programcılığı"),
    ("bilgisayar teknolojisi", "Bilgisayar Teknolojisi"),
    ("bilişim güvenliği", "Bilişim Güvenliği Teknolojisi"),
    ("hemşirelik", "Hemşirelik"),
    ("ebelik", "Ebelik"),
    ("tıbbi dokümantasyon", "Tıbbi Dokümantasyon ve Sekreterlik"),
    ("anestezi", "Anestezi"),
    ("tıbbi görüntüleme", "Tıbbi Görüntüleme Teknikleri"),
    ("tıbbi laboratuvar", "Tıbbi Laboratuvar Teknikleri"),
    ("fizyoterapi", "Fizyoterapi ve Rehabilitasyon"),
    ("beslenme ve diyetetik", "Beslenme ve Diyetetik"),
    ("eczacılık", "Eczacılık"),
    ("adalet", "Adalet"),
    ("hukuk", "Hukuk"),
    ("işletme", "İşletme"),
    ("iktisat", "İktisat"),
    ("kamu yönetimi", "Kamu Yönetimi / Siyaset Bilimi"),
    ("maliye", "Maliye"),
    ("uluslararası ilişkiler", "Uluslararası İlişkiler"),
    ("çalışma ekonomisi", "Çalışma Ekonomisi ve Endüstri İlişkileri"),
    ("muhasebe", "Muhasebe ve Vergi Uygulamaları"),
    ("bankacılık ve sigortacılık", "Bankacılık ve Sigortacılık"),
    ("sosyal hizmet", "Sosyal Hizmet"),
    ("çocuk gelişimi", "Çocuk Gelişimi"),
    ("bilgisayar mühendisliği", "Bilgisayar Mühendisliği"),
    ("yazılım mühendisliği", "Yazılım Mühendisliği"),
    ("elektrik-elektronik mühendisliği", "Elektrik-Elektronik Mühendisliği"),
    ("endüstri mühendisliği", "Endüstri Mühendisliği"),
    ("inşaat mühendisliği", "İnşaat Mühendisliği"),
    ("makine mühendisliği", "Makine Mühendisliği"),
    ("harita mühendisliği", "Harita Mühendisliği"),
    ("ziraat mühendisliği", "Ziraat Mühendisliği"),
    ("gıda mühendisliği", "Gıda Mühendisliği"),
    ("mimarlık", "Mimarlık"),
    ("özel güvenlik ve koruma", "Özel Güvenlik ve Koruma"),
    ("4001", "Herhangi Bir Lisans Programı (4001)"),
    ("3001", "Herhangi Bir Önlisans Programı (3001)"),
    ("2001", "Herhangi Bir Ortaöğretim / Lise Alanı (2001)"),
]

OZEL_SART_KELIMELERI = [
    "mezun", "ehliyet", "sürücü belgesi", "src", "psikoteknik",
    "sertifika", "güvenlik kimlik", "kpss", "puan", "yaşını doldurmamış",
    "deneyim", "tecrübe", "lisans", "önlisans", "ortaöğretim", "lise"
]


def tr_kucuk(metin: str) -> str:
    return metin.replace("İ", "i").replace("I", "ı").lower()


def kadrolari_cikar(metin: str, kategori: str = "") -> list[str]:
    b = tr_kucuk(metin)
    bulunanlar = []
    for anahtar, unvan in KADRO_SOZLUGU:
        if anahtar in b and unvan not in bulunanlar:
            if unvan == "Mühendis" and any("Mühendisi" in u for u in bulunanlar):
                continue
            bulunanlar.append(unvan)
        if len(bulunanlar) >= 12:
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


def bolumleri_cikar(metin: str) -> list[str]:
    b = tr_kucuk(metin)
    bolumler = []
    for anahtar, bolum_adi in BOLUM_SOZLUGU:
        if anahtar in b and bolum_adi not in bolumler:
            bolumler.append(bolum_adi)
        if len(bolumler) >= 12:
            break

    if not bolumler:
        if "herhangi bir lisans" in b:
            bolumler.append("Herhangi Bir Lisans Programı (4001)")
        elif "herhangi bir önlisans" in b or "herhangi bir ön lisans" in b:
            bolumler.append("Herhangi Bir Önlisans Programı (3001)")
        elif "ortaöğretim" in b or "lise" in b:
            bolumler.append("Ortaöğretim / Lise Mezunu")
    return bolumler


def kadro_ve_sart_eslestir(satirlar: list[str]) -> list[str]:
    """İlan metnindeki her bir kadronun (Şoför, Psikolog, Büro Yöneticisi vb.)
    yanında veya hemen alt satırında yazan mezuniyet/ehliyet/sertifika şartını eşleştirir."""
    eslesen_sartlar = []
    kullanilan_unvanlar = set()

    for idx, satir in enumerate(satirlar):
        s_kucuk = tr_kucuk(satir)
        if len(satir) > 320:
            continue

        for anahtar, unvan in KADRO_SOZLUGU:
            if anahtar in s_kucuk and unvan not in kullanilan_unvanlar:
                # Kadro satırı çok kısaysa (tablo başlığı gibiyse) hemen altındaki 1-2 satırı da şart olarak ekle
                baglam = satir
                if len(satir) < 55 and idx + 1 < len(satirlar):
                    sonraki = satirlar[idx + 1]
                    if len(sonraki) < 260 and any(k in tr_kucuk(sonraki) for k in OZEL_SART_KELIMELERI):
                        baglam = f"{satir} — {sonraki}"
                        if len(sonraki) < 60 and idx + 2 < len(satirlar):
                            ucuncu = satirlar[idx + 2]
                            if len(ucuncu) < 220 and any(k in tr_kucuk(ucuncu) for k in OZEL_SART_KELIMELERI):
                                baglam = f"{baglam} ({ucuncu})"

                # Eğer satırda veya devamında gerçek bir şart/açıklama varsa listeye ekle
                if any(k in tr_kucuk(baglam) for k in OZEL_SART_KELIMELERI) or len(baglam) > len(anahtar) + 12:
                    temiz_baglam = re.sub(r"\s+", " ", baglam).strip()
                    eslesen_sartlar.append(f"{unvan}: {temiz_baglam}")
                    kullanilan_unvanlar.add(unvan)
                break

        if len(eslesen_sartlar) >= 10:
            break

    return eslesen_sartlar


def gercek_ilan_mi(baslik: str, url: str) -> bool:
    b = tr_kucuk(baslik)
    u = url.lower()
    if len(baslik) < 22 or len(baslik) > 260:
        return False
    if any(h in b for h in HARIC_TUTULACAKLAR):
        return False
    if u.endswith("#") or "javascript:" in u or "mailto:" in u:
        return False
    return any(k in b for k in [
        "personel alım", "memur alım", "işçi alım", "sözleşmeli personel",
        "uzman yardımcısı", "müfettiş yardımcısı", "zabıt katibi", "mübaşir",
        "bilişim personeli", "sağlık personeli", "hemşire", "paramedik",
        "açık pozisyon", "işe alım", "kpss", "tercih kılavuzu", "kadrolarına",
        "alımı yapılacaktır", "personel istihdam"
    ])


def detay_cikar(baslik: str, domain: str):
    b = tr_kucuk(baslik)

    if any(k in b for k in ["hemşire", "sağlık", "paramedik", "ebe", "doktor", "tıbbi", "eczacı", "psikolog"]):
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

    if any(k in domain for k in ["ibb.istanbul", "ankara.bel.tr", "thy.com", "aselsan", "tusas", "roketsan", "bank", "vizyonergenc"]):
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

    eslesme = re.search(r"\b(\d{1,5})\s*(?:sözleşmeli|sürekli|memur|personel|işçi|uzman|kadro|kişilik|adet)", b)
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


def ai_ile_zenginlestir(ham_metin: str) -> dict | None:
    if not GEMINI_AKTIF:
        return None

    class AiIlanAnaliz(BaseModel):
        positions: list[str] = Field(description="İlanda geçen tüm unvanlar (Örn: Şoför, Psikolog, Büro Yöneticisi)")
        departments: list[str] = Field(description="Aranan mezuniyet bölümleri veya nitelik kodları")
        quota: int = Field(description="Toplam kontenjan sayısı")
        kpss: str = Field(description="KPSS puan türü ve taban puan şartı")
        endDate: str = Field(description="YYYY-MM-DD formatında son başvuru tarihi")
        requirements: list[str] = Field(description="Her kadro için aranan bölümü, ehliyeti, sertifikayı ve özel şartı 'Kadro Adı: Şartlar' şeklinde yaz")

    try:
        client = genai.Client()
        prompt = f"""
        Aşağıdaki resmi ilan metnini analiz et.
        Özellikle ilanın içinde geçen her pozisyon (örneğin Şoför, Psikolog, Büro Yöneticisi vb.) için hangi mezuniyet bölümünün, ehliyetin, sertifikanın veya KPSS puanının arandığını tek tek çıkar.

        İlan Metni:
        {ham_metin[:14000]}
        """
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=AiIlanAnaliz,
                temperature=0.1,
            ),
        )
        return json.loads(resp.text)
    except Exception:
        return None


def ilan_sayfasi_zenginlestir(page, url: str, mevcut_baslik: str, kategori: str, mevcut_kontenjan: int, mevcut_kpss: str):
    if url.lower().endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".rar")):
        return None

    try:
        page.goto(url, timeout=18000, wait_until="domcontentloaded")
        page.wait_for_timeout(1600)

        ham_govde = page.inner_text("body")
        satirlar = [s.strip() for s in ham_govde.splitlines() if len(s.strip()) > 2]
        govde = " ".join(satirlar)
        if len(govde) < 100:
            return None

        ai_sonuc = ai_ile_zenginlestir(f"Başlık: {mevcut_baslik}\n\n{ham_govde}")
        if ai_sonuc and ai_sonuc.get("requirements"):
            return ai_sonuc

        birlesik_metin = f"{mevcut_baslik} {govde[:10000]}"
        b_kucuk = tr_kucuk(birlesik_metin)

        zengin_kadrolar = kadrolari_cikar(birlesik_metin, kategori)
        aranan_bolumler = bolumleri_cikar(birlesik_metin)
        kadro_sart_listesi = kadro_ve_sart_eslestir(satirlar)

        yeni_kontenjan = mevcut_kontenjan
        if mevcut_kontenjan <= 1:
            m = re.search(r"\b(\d{1,5})\s*(?:adet|kişi|kadro|pozisyon|sözleşmeli\s+personel|sürekli\s+işçi|memur)\b", b_kucuk)
            if m:
                sayi = int(m.group(1))
                if 1 <= sayi <= 50000:
                    yeni_kontenjan = sayi

        guncel_kpss = mevcut_kpss
        kpss_puan = re.search(r"kpss[^\d]{0,30}(\d{2})\s*(?:ve\s+üzeri|puan)", b_kucuk)
        if kpss_puan:
            guncel_kpss = f"{mevcut_kpss} - En Az {kpss_puan.group(1)} Puan"

        son_tarih = ""
        tarih_eslesme = re.search(r"son\s+başvuru\s*(?:tarihi)?[:\s-]*(\d{1,2})[./-](\d{1,2})[./-](202\d)", b_kucuk)
        if tarih_eslesme:
            gun, ay, yil = tarih_eslesme.groups()
            son_tarih = f"{yil}-{int(ay):02d}-{int(gun):02d}"

        detay_maddeleri = []
        if kadro_sart_listesi:
            detay_maddeleri.extend(kadro_sart_listesi)
        if aranan_bolumler:
            detay_maddeleri.append(f"Aranan Bölümler / Alanlar: {', '.join(aranan_bolumler)}")
        if zengin_kadrolar and not kadro_sart_listesi:
            detay_maddeleri.append(f"Alım Yapılacak Kadrolar: {', '.join(zengin_kadrolar)}")
        detay_maddeleri.append(f"Sınav / Puan Şartı: {guncel_kpss}")

        # Özel şart içeren (ehliyet, sertifika, yaş, mezuniyet) ek satırları da yakala
        for satir in satirlar:
            if 35 <= len(satir) <= 240 and any(k in tr_kucuk(satir) for k in ["ehliyet", "sürücü belgesi", "src", "sertifika", "yaşını doldurmamış", "mezun olmak"]):
                if satir not in detay_maddeleri and not any(satir in d for d in detay_maddeleri):
                    detay_maddeleri.append(satir)
                if len(detay_maddeleri) >= 12:
                    break

        return {
            "positions": zengin_kadrolar,
            "departments": aranan_bolumler,
            "quota": yeni_kontenjan,
            "kpss": guncel_kpss,
            "endDate": son_tarih,
            "requirements": detay_maddeleri,
        }
    except Exception:
        return None


def portallari_tara():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 42 resmi kurum taranıyor...")
    tum_ilanlar = []
    gorulen_url = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1366, "height": 768},
            locale="tr-TR",
            ignore_https_errors=True,
        )

        context.route(
            "**/*",
            lambda route: route.abort()
            if route.request.resource_type in ["image", "media", "font"]
            else route.continue_(),
        )

        liste_sayfasi = context.new_page()
        detay_sayfasi = context.new_page()

        for idx, (domain, base_url) in enumerate(PORTALLAR):
            try:
                liste_sayfasi.goto(base_url, timeout=22000, wait_until="domcontentloaded")
                liste_sayfasi.wait_for_timeout(1800)

                ham_linkler = liste_sayfasi.eval_on_selector_all(
                    "a[href]",
                    """els => els.map(e => ({
                        text: (e.innerText || e.title || e.getAttribute('aria-label') || '').replace(/\\s+/g, ' ').trim(),
                        href: e.getAttribute('href') || ''
                    }))""",
                )

                portal_sayac = 0
                for a_idx, item in enumerate(ham_linkler):
                    metin = item["text"]
                    tam_url = urljoin(base_url, item["href"].strip())

                    if tam_url in gorulen_url or not gercek_ilan_mi(metin, tam_url):
                        continue

                    gorulen_url.add(tam_url)
                    kategori, egitim, kpss, duz_mu, sehir, kontenjan, nitelik, kadrolar = detay_cikar(metin, domain)
                    bolumler = bolumleri_cikar(metin)
                    bitis_tarihi = (datetime.now() + timedelta(days=10)).strftime("%Y-%m-%d")
                    sartlar = ["İlgili kurumun resmi duyuru metnindeki başvuru şartlarını inceleyiniz."]

                    if portal_sayac < 6:
                        zengin = ilan_sayfasi_zenginlestir(
                            detay_sayfasi, tam_url, metin, kategori, kontenjan, kpss
                        )
                        if zengin:
                            if zengin.get("positions"):
                                kadrolar = zengin["positions"]
                            if zengin.get("departments"):
                                bolumler = zengin["departments"]
                            if zengin.get("quota"):
                                kontenjan = zengin["quota"]
                            if zengin.get("kpss"):
                                kpss = zengin["kpss"]
                            if zengin.get("endDate"):
                                bitis_tarihi = zengin["endDate"]
                            if zengin.get("requirements"):
                                sartlar = zengin["requirements"]

                        time.sleep(random.uniform(0.3, 0.7))

                    tum_ilanlar.append({
                        "id": f"ga-{idx}-{a_idx}",
                        "sourceDomain": domain,
                        "category": kategori,
                        "institution": domain.upper(),
                        "title": metin[:200],
                        "positions": kadrolar,
                        "departments": bolumler,
                        "city": sehir,
                        "education": egitim,
                        "kpss": kpss,
                        "quota": kontenjan,
                        "publishDate": datetime.now().strftime("%Y-%m-%d"),
                        "endDate": bitis_tarihi,
                        "refNo": f"GA-{idx+1}-{a_idx+100}",
                        "qualCode": nitelik,
                        "isDuzMemurluk": duz_mu,
                        "url": tam_url,
                        "requirements": sartlar,
                        "documents": ["e-Devlet Mezuniyet Belgesi", "KPSS Sonuç Belgesi"],
                    })
                    portal_sayac += 1
                    if portal_sayac >= 10:
                        break

                print(f"[TAMAM] {domain}: {portal_sayac} ilan eklendi.")
            except Exception as hata:
                print(f"[UYARI] {domain} atlandı: {str(hata)[:90]}")

        browser.close()

    if tum_ilanlar:
        gecici_dosya = "ilanlar.tmp.json"
        with open(gecici_dosya, "w", encoding="utf-8") as f:
            json.dump(tum_ilanlar, f, ensure_ascii=False, indent=2)
        os.replace(gecici_dosya, "ilanlar.json")
        print(f"[BITTI] Toplam {len(tum_ilanlar)} detaylı ilan 'ilanlar.json' dosyasına yazıldı.")
    else:
        print("[UYARI] Yeni ilan çekilemedi, mevcut 'ilanlar.json' korundu.")


if __name__ == "__main__":
    portallari_tara()
