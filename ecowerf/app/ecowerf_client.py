"""Client voor het Ecowerf-portaal (stap 1: enkel inloggen), zonder Home Assistant."""
from __future__ import annotations

import logging
import time
from urllib.parse import urljoin, urlparse

import aiohttp
from bs4 import BeautifulSoup

_LOGGER = logging.getLogger(__name__)

BASE_URL = "https://www.mijnecowerf.be"
LOGIN_URL = f"{BASE_URL}/Account/Logon"
LOGIN_PATH = "/account/logon"
TARGET_PATH = "/aansluitpunten/containers"
DUMP_PATHS = [
    "/Aansluitpunten/Ophaalkalender",
    "/Aansluitpunten/Statistieken",
]
VERRICHTINGEN_PATH = "/Aansluitpunten/Verrichtingen"
VERRICHTINGEN_AJAX_PATH = "/Aansluitpunten/ShowResultsVerrichtingen"
SCRIPT_KEYWORDS = ("ajax", "ShowResults", "DataTable")
DUMP_CHUNK_SIZE = 3000

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
    ),
    "Accept-Language": "nl-BE,nl;q=0.9",
}
TIMEOUT = aiohttp.ClientTimeout(total=30)


class EcowerfError(Exception):
    """Algemene fout."""


class EcowerfConnectionError(EcowerfError):
    """Portaal niet bereikbaar."""


class EcowerfAuthError(EcowerfError):
    """Login geweigerd."""


class EcowerfApi:
    """Houdt een ingelogde sessie vast."""

    def __init__(
        self, session: aiohttp.ClientSession, username: str, password: str
    ) -> None:
        self._session = session
        self._username = username
        self._password = password

    async def async_login(self) -> None:
        """Log in en controleer dat we op de Containers-pagina eindigen."""
        _LOGGER.info("[Ecowerf] === Login gestart ===")
        try:
            async with self._session.get(
                LOGIN_URL, headers=HEADERS, timeout=TIMEOUT
            ) as resp:
                _LOGGER.info(
                    "[Ecowerf] Loginpagina opgehaald: status=%s url=%s",
                    resp.status,
                    resp.url,
                )
                if resp.status != 200:
                    raise EcowerfConnectionError(
                        f"Loginpagina gaf status {resp.status}"
                    )
                html = await resp.text()
                page_url = str(resp.url)

            post_url, payload = self._build_payload(html, page_url)

            async with self._session.post(
                post_url,
                data=payload,
                headers={**HEADERS, "Referer": page_url},
                timeout=TIMEOUT,
                allow_redirects=True,
            ) as resp:
                for step in resp.history:
                    _LOGGER.info(
                        "[Ecowerf] Redirect: status=%s -> %s",
                        step.status,
                        step.headers.get("Location"),
                    )
                final_url = str(resp.url)
                _LOGGER.info(
                    "[Ecowerf] Na login: status=%s eind-url=%s",
                    resp.status,
                    final_url,
                )
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.error("[Ecowerf] Verbindingsfout: %s", err)
            raise EcowerfConnectionError(str(err)) from err

        path = urlparse(final_url).path.rstrip("/").lower()
        if path == TARGET_PATH:
            _LOGGER.info(
                "[Ecowerf] *** LOGIN GESLAAGD *** eindpagina is %s", final_url
            )
            return
        if path == LOGIN_PATH:
            _LOGGER.warning(
                "[Ecowerf] *** LOGIN MISLUKT *** nog op de loginpagina "
                "(foute gegevens, of er ontbreekt een veld in het formulier)"
            )
            raise EcowerfAuthError("Login geweigerd")
        _LOGGER.warning(
            "[Ecowerf] *** ONVERWACHTE EINDPAGINA *** %s (verwacht pad: %s)",
            final_url,
            TARGET_PATH,
        )
        raise EcowerfError(f"Onverwachte eindpagina: {final_url}")

    def _build_payload(self, html: str, page_url: str) -> tuple[str, dict]:
        """Lees het loginformulier uit en vul het in."""
        soup = BeautifulSoup(html, "html.parser")
        field = soup.find("input", id="Identifier")
        form = field.find_parent("form") if field else None
        if form is None:
            _LOGGER.error("[Ecowerf] Loginformulier (veld 'Identifier') niet gevonden")
            raise EcowerfError("Loginformulier niet gevonden")

        payload: dict[str, str] = {}
        for hidden in form.find_all("input", type="hidden"):
            name = hidden.get("name")
            if name:
                payload[name] = hidden.get("value", "")
        _LOGGER.info(
            "[Ecowerf] Verborgen velden in formulier: %s", sorted(payload) or "geen"
        )

        payload["Identifier"] = self._username
        payload["AuthenticationValue"] = self._password
        payload["LogonByName"] = "Aanmelden"

        post_url = urljoin(page_url, form.get("action") or page_url)
        _LOGGER.info(
            "[Ecowerf] Formulier wordt verstuurd naar %s (methode %s)",
            post_url,
            form.get("method", "get").upper(),
        )
        return post_url, payload

    @staticmethod
    def _log_chunks(label: str, text: str) -> None:
        """Zet tekst in blokken in het log, met BEGIN/EIND-markeringen."""
        chunks = [
            text[i : i + DUMP_CHUNK_SIZE]
            for i in range(0, len(text), DUMP_CHUNK_SIZE)
        ] or [""]
        total = len(chunks)
        for number, chunk in enumerate(chunks, start=1):
            _LOGGER.info(
                "[Ecowerf] ===== %s deel %s/%s BEGIN =====\n%s\n"
                "===== %s deel %s/%s EIND =====",
                label, number, total, chunk, label, number, total,
            )

    async def async_dump_pages(self) -> None:
        """Zet de verrichtingen (JSON) en enkele pagina's in het log."""
        await self._dump_verrichtingen()
        for path in DUMP_PATHS:
            await self._dump_page(path)

    async def _dump_verrichtingen(self) -> None:
        """Haal de verrichtingen op via dezelfde aanroep als de website."""
        _LOGGER.info("[Ecowerf] ##### DUMP START verrichtingen (JSON) #####")
        params = {
            "sEcho": "1",
            "sSearchFilter": "[]",
            "DisplayStart": "0",
            "DisplayLength": "1000",
            "SortBy": "Verrichtingsdatum",
            "SortDirection": "desc",
            "Verrichtingtypeid": "",
            "_": str(int(time.time() * 1000)),
        }
        headers = {
            **HEADERS,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{BASE_URL}{VERRICHTINGEN_PATH}",
        }
        try:
            async with self._session.get(
                f"{BASE_URL}{VERRICHTINGEN_AJAX_PATH}",
                params=params,
                headers=headers,
                timeout=TIMEOUT,
            ) as resp:
                status = resp.status
                content_type = resp.headers.get("Content-Type", "")
                text = await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.error("[Ecowerf] Dump van verrichtingen mislukt: %s", err)
            return
        _LOGGER.info(
            "[Ecowerf] Verrichtingen: status=%s content-type=%s lengte=%s tekens",
            status, content_type, len(text),
        )
        self._log_chunks("VERRICHTINGEN-JSON", text)
        _LOGGER.info("[Ecowerf] ##### DUMP EINDE verrichtingen (JSON) #####")

    async def _dump_page(self, path: str) -> None:
        """Zet een pagina (zonder script/style/svg) en de relevante scripts in het log."""
        _LOGGER.info("[Ecowerf] ##### DUMP START %s #####", path)
        try:
            async with self._session.get(
                f"{BASE_URL}{path}", headers=HEADERS, timeout=TIMEOUT
            ) as resp:
                status = resp.status
                final_url = str(resp.url)
                content_type = resp.headers.get("Content-Type", "")
                raw = await resp.read()
        except (aiohttp.ClientError, TimeoutError) as err:
            _LOGGER.error("[Ecowerf] Dump van %s mislukt: %s", path, err)
            return

        _LOGGER.info(
            "[Ecowerf] Dump %s: status=%s eind-url=%s content-type=%s grootte=%s bytes",
            path, status, final_url, content_type, len(raw),
        )
        if "html" not in content_type and "text" not in content_type and "json" not in content_type:
            _LOGGER.info("[Ecowerf] Geen tekst of HTML, inhoud wordt niet gelogd")
            _LOGGER.info("[Ecowerf] ##### DUMP EINDE %s #####", path)
            return

        html = raw.decode("utf-8", errors="replace")
        soup = BeautifulSoup(html, "html.parser")

        scripts = [
            tag.get_text()
            for tag in soup.find_all("script")
            if not tag.get("src")
            and any(key in tag.get_text() for key in SCRIPT_KEYWORDS)
        ]
        for number, script in enumerate(scripts, start=1):
            self._log_chunks(f"SCRIPT {path} {number}/{len(scripts)}", script)
        if not scripts:
            _LOGGER.info("[Ecowerf] Geen inline scripts met %s gevonden", SCRIPT_KEYWORDS)

        for tag in soup(["script", "style", "svg"]):
            tag.decompose()
        text = "\n".join(
            line.strip() for line in str(soup).splitlines() if line.strip()
        )
        self._log_chunks(f"HTML {path}", text)

        links: list[str] = []
        for anchor in soup.find_all("a", href=True):
            entry = (
                f"{anchor.get_text(' ', strip=True)} -> "
                f"{urljoin(final_url, anchor['href'])}"
            )
            if entry not in links:
                links.append(entry)
        _LOGGER.info(
            "[Ecowerf] ===== LINKS %s (%s) =====\n%s",
            path, len(links), "\n".join(links) or "geen",
        )
        _LOGGER.info("[Ecowerf] ##### DUMP EINDE %s #####", path)
