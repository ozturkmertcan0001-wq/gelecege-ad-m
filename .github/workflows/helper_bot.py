import io
import random
import ssl
import threading
import time
import urllib3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import cloudscraper
    CLOUDSCRAPER_AKTIF = True
except ImportError:
    CLOUDSCRAPER_AKTIF = False

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AKTIF = True
except ImportError:
    PLAYWRIGHT_AKTIF = False

try:
    from pypdf import PdfReader
    PYPDF_AKTIF = True
except ImportError:
    PYPDF_AKTIF = False


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:132.0) Gecko/20100101 Firefox/132.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
]


class EsnekSSLAdapter(HTTPAdapter):
    """Eski veya eksik sertifika zincirine sahip .gov.tr sunucuları için esnek SSL bağdaştırıcısı."""

    def init_poolmanager(self, *args, **kwargs):
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        try:
            ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
        except Exception:
            pass
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


class GuvenliIstemci:
    """
    4 Katmanlı Engel Aşma İstemcisi:
      1) Esnek SSL + Otomatik Tekrarlı requests.Session
      2) cloudscraper (WAF / Cloudflare / TLS parmak izi koruması aşımı)
      3) Headless Chromium / Playwright (JS ile yüklenen portallar için)
      4) PDF Metin Ayrıştırıcı (Doğrudan PDF açılan duyurular için)
    """

    def __init__(self):
        self.session = requests.Session()
        retry = Retry(
            total=2,
            backoff_factor=0.6,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "HEAD"],
        )
        adapter = EsnekSSLAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self._pw_kilit = threading.Semaphore(2)
        self._scraper_kilit = threading.Lock()
        self.scraper = None
        if CLOUDSCRAPER_AKTIF:
            try:
                self.scraper = cloudscraper.create_scraper(
                    browser={"browser": "chrome", "platform": "windows", "desktop": True}
                )
            except Exception:
                self.scraper = None

    def _headers(self, referer: str = "") -> dict:
        h = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
        if referer:
            h["Referer"] = referer
        return h

    @staticmethod
    def _engellendi_mi(durum_kodu: int, html: str) -> bool:
        if durum_kodu in (401, 403, 406, 429, 503):
            return True
        kucuk = (html or "")[:3000].lower()
        waf_izleri = [
            "cf-browser-verification",
            "just a moment...",
            "attention required! | cloudflare",
            "ddos-guard",
            "incapsula incident",
            "request blocked",
            "erişim engellendi",
            "güvenlik doğrulaması",
        ]
        return any(iz in kucuk for iz in waf_izleri)

    @staticmethod
    def _js_kabugu_mu(html: str) -> bool:
        if not html:
            return True
        temiz = " ".join(html.split())
        if len(temiz) < 1200 and any(
            k in temiz.lower() for k in ['id="root"', 'id="app"', "__next_data__", "ng-version", "enable javascript"]
        ):
            return True
        return False

    def pdf_metni_cikar(self, pdf_baytlari: bytes) -> str:
        if not PYPDF_AKTIF or not pdf_baytlari:
            return ""
        try:
            okuyucu = PdfReader(io.BytesIO(pdf_baytlari))
            parcalar = []
            for sayfa in okuyucu.pages[:6]:
                metin = sayfa.extract_text() or ""
                if metin.strip():
                    parcalar.append(metin.strip())
            return "\n".join(parcalar)[:25000]
        except Exception:
            return ""

    def _playwright_ile_getir(self, url: str, timeout_ms: int = 18000) -> str:
        if not PLAYWRIGHT_AKTIF:
            return ""
        with self._pw_kilit:
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(
                        headless=True,
                        args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"],
                    )
                    context = browser.new_context(
                        user_agent=random.choice(USER_AGENTS),
                        locale="tr-TR",
                        ignore_https_errors=True,
                    )
                    page = context.new_page()
                    page.route(
                        "**/*",
                        lambda route: route.abort()
                        if route.request.resource_type in ("image", "media", "font")
                        else route.continue_(),
                    )
                    page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
                    page.wait_for_timeout(1800)
                    icerik = page.content()
                    context.close()
                    browser.close()
                    return icerik or ""
            except Exception:
                return ""

    def sayfa_getir(self, url: str, timeout: int = 14, js_destegi: bool = True) -> dict:
        """
        Dönüş: {"ok": bool, "html": str, "pdf_text": str, "yontem": str}
        Hiçbir durumda hata fırlatmaz.
        """
        sonuc = {"ok": False, "html": "", "pdf_text": "", "yontem": "yok"}
        url_kucuk = url.lower()

        # Katman 1: Esnek SSL'li requests.Session
        try:
            resp = self.session.get(url, headers=self._headers(), timeout=timeout, verify=False, allow_redirects=True)
            icerik_turu = resp.headers.get("Content-Type", "").lower()

            if "application/pdf" in icerik_turu or url_kucuk.endswith(".pdf"):
                pdf_txt = self.pdf_metni_cikar(resp.content)
                if pdf_txt:
                    return {"ok": True, "html": "", "pdf_text": pdf_txt, "yontem": "pdf"}
                return sonuc

            if not resp.encoding or resp.encoding.lower() == "iso-8859-1":
                resp.encoding = resp.apparent_encoding or "utf-8"

            html = resp.text or ""
            if resp.status_code == 200 and not self._engellendi_mi(resp.status_code, html):
                if js_destegi and self._js_kabugu_mu(html):
                    js_html = self._playwright_ile_getir(url)
                    if len(js_html) > len(html):
                        return {"ok": True, "html": js_html, "pdf_text": "", "yontem": "playwright-spa"}
                return {"ok": True, "html": html, "pdf_text": "", "yontem": "requests"}
        except Exception:
            pass

        # Katman 2: cloudscraper (WAF / 403 / TLS koruması)
        if self.scraper is not None:
            try:
                time.sleep(0.25)
                with self._scraper_kilit:
                    resp2 = self.scraper.get(url, headers=self._headers(), timeout=timeout)
                if "application/pdf" in resp2.headers.get("Content-Type", "").lower():
                    pdf_txt = self.pdf_metni_cikar(resp2.content)
                    if pdf_txt:
                        return {"ok": True, "html": "", "pdf_text": pdf_txt, "yontem": "cloudscraper-pdf"}
                    return sonuc

                if not resp2.encoding or resp2.encoding.lower() == "iso-8859-1":
                    resp2.encoding = resp2.apparent_encoding or "utf-8"
                html2 = resp2.text or ""
                if resp2.status_code == 200 and not self._engellendi_mi(resp2.status_code, html2):
                    if js_destegi and self._js_kabugu_mu(html2):
                        js_html = self._playwright_ile_getir(url)
                        if len(js_html) > len(html2):
                            return {"ok": True, "html": js_html, "pdf_text": "", "yontem": "playwright-spa"}
                    return {"ok": True, "html": html2, "pdf_text": "", "yontem": "cloudscraper"}
            except Exception:
                pass

        # Katman 3: Tam tarayıcı (Playwright Chromium)
        if js_destegi and not url_kucuk.endswith(".pdf"):
            js_html = self._playwright_ile_getir(url)
            if js_html and not self._engellendi_mi(200, js_html):
                return {"ok": True, "html": js_html, "pdf_text": "", "yontem": "playwright"}

        return sonuc
