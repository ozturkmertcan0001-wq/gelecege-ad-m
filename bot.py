import json
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

def kategori_tahmin_et(baslik: str) -> str:
    b = baslik.lower()
    if any(k in b for k in ["hemşire", "sağlık", "paramedik", "ebe", "doktor", "tıbbi"]):
        return "Sağlık Personeli"
    if any(k in b for k in ["bilişim", "mühendis", "tekniker", "programcı", "yazılım"]):
        return "Bilişim & Teknik"
    if any(k in b for k in ["işçi", "temizlik", "şoför", "güvenlik", "hizmetli"]):
        return "İşçi & Hizmetli"
    if any(k in b for k in ["uzman", "müfettiş", "öğretim", "araştırma", "akademik"]):
        return "Uzman & Akademik"
    return "Büro & İdari"

def bolum_sartsiz_mi(baslik: str) -> bool:
    b = baslik.lower()
    return any(k in b for k in ["4001", "3001", "2001", "bölüm şartsız", "herhangi bir lisans", "herhangi bir önlisans", "düz memur", "büro personeli", "zabıt katibi", "mübaşir", "gişe", "servis görevlisi"])

def portallari_tara():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 42 resmi portal taranıyor...")
    tum_ilanlar = []
    headers = {"User-Agent": "Mozilla/5.0 (GelecegeAdim Bot/3.0)"}

    for idx, (domain, base_url) in enumerate(PORTALLAR):
        try:
            resp = requests.get(base_url, headers=headers, timeout=12)
            soup = BeautifulSoup(resp.text, "html.parser")
            for a_idx, link in enumerate(soup.find_all("a", href=True)):
                metin = " ".join(link.get_text().split())
                tam_url = urljoin(base_url, link["href"])
                if len(metin) > 25 and any(k in metin.lower() for k in ["alım", "ilan", "personel", "memur", "işçi", "sınav", "tercih", "pozisyon"]):
                    duz_mu = bolum_sartsiz_mi(metin)
                    tum_ilanlar.append({
                        "id": f"ga-{idx}-{a_idx}-{int(time.time())}",
                        "sourceDomain": domain,
                        "category": kategori_tahmin_et(metin),
                        "institution": domain.upper(),
                        "title": metin[:160],
                        "city": "Türkiye Geneli",
                        "education": "Lisans",
                        "kpss": "KPSS P3 (Lisans)",
                        "quota": 10,
                        "publishDate": datetime.now().strftime("%Y-%m-%d"),
                        "endDate": (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d"),
                        "refNo": f"GA-{idx+1}-{a_idx+100}",
                        "qualCode": "4001 (Bölüm Şartsız)" if duz_mu else "Özel Nitelik",
                        "isDuzMemurluk": duz_mu,
                        "url": tam_url,
                        "requirements": ["İlgili kurumun resmi duyurusundaki başvuru şartlarını inceleyiniz."],
                        "documents": ["e-Devlet Mezuniyet Belgesi", "KPSS Sonuç Belgesi"]
                    })
                    if len([x for x in tum_ilanlar if x["sourceDomain"] == domain]) >= 5:
                        break
        except Exception as hata:
            print(f"Uyarı ({domain}): {hata}")

    with open("ilanlar.json", "w", encoding="utf-8") as f:
        json.dump(tum_ilanlar, f, ensure_ascii=False, indent=2)
    print(f"Tamamlandı: {len(tum_ilanlar)} gerçek ilan 'ilanlar.json' dosyasına yazıldı.")

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