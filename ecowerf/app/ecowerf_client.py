"""Client voor het Ecowerf-portaal (stap 1: enkel inloggen), zonder Home Assistant."""
from __future__ import annotations

import json
import logging
import re
import time
from datetime import date, datetime
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
CONTAINERS_PATH = "/Aansluitpunten/Containers"
VERRICHTINGEN_PATH = "/Aansluitpunten/Verrichtingen"
BETALINGEN_PATH = "/Aansluitpunten/Betalingsuitnodigingen"
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
    def _verrichtingen_params() -> dict[str, str]:
        return {
            "sEcho": "1",
            "sSearchFilter": "[]",
            "DisplayStart": "0",
            "DisplayLength": "1000",
            "SortBy": "Verrichtingsdatum",
            "SortDirection": "desc",
            "Verrichtingtypeid": "",
            "_": str(int(time.time() * 1000)),
        }

    @staticmethod
    def _verrichtingen_headers() -> dict[str, str]:
        return {
            **HEADERS,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": f"{BASE_URL}{VERRICHTINGEN_PATH}",
        }

    async def _get_text(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        """Haal een pagina op met de ingelogde sessie."""
        try:
            async with self._session.get(
                f"{BASE_URL}{path}",
                params=params,
                headers=headers or HEADERS,
                timeout=TIMEOUT,
            ) as resp:
                if resp.status != 200:
                    raise EcowerfConnectionError(f"{path} gaf status {resp.status}")
                if urlparse(str(resp.url)).path.rstrip("/").lower() == LOGIN_PATH:
                    raise EcowerfAuthError("Sessie verlopen")
                return await resp.text()
        except (aiohttp.ClientError, TimeoutError) as err:
            raise EcowerfConnectionError(f"{path}: {err}") from err

    async def async_fetch_state(self) -> dict[str, object]:
        """Haal alle gegevens op en geef de waarden per sensor terug.

        Mislukt een pagina, dan ontbreken enkel de sensoren van die pagina.
        """
        state: dict[str, object] = {}
        today = date.today()

        try:
            html = await self._get_text(CONTAINERS_PATH)
            state.update(parse_containers(html))
        except EcowerfError as err:
            _LOGGER.warning("[Ecowerf] Containers-pagina mislukt: %s", err)

        try:
            html = await self._get_text(VERRICHTINGEN_PATH)
            state["saldo"] = parse_saldo(html)
            text = await self._get_text(
                VERRICHTINGEN_AJAX_PATH,
                params=self._verrichtingen_params(),
                headers=self._verrichtingen_headers(),
            )
            state.update(build_verrichtingen_state(parse_verrichtingen(text), today))
        except EcowerfError as err:
            _LOGGER.warning("[Ecowerf] Verrichtingen mislukt: %s", err)

        try:
            html = await self._get_text(BETALINGEN_PATH)
            state.update(build_betalingen_state(parse_betalingen(html)))
        except EcowerfError as err:
            _LOGGER.warning("[Ecowerf] Betalingsuitnodigingen mislukt: %s", err)

        return state

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
        params = self._verrichtingen_params()
        headers = self._verrichtingen_headers()
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


# --------------------------------------------------------------------------
# Parsers (geen netwerk, enkel tekst naar waarden)
# --------------------------------------------------------------------------

# fractie -> code in de mededeling (REST0240, GFT0240, PK0240)
FRACTIES = {"restafval": "REST", "gft": "GFT", "papier": "PK"}
# tekst op de Containers-pagina -> fractie
_FRACTIE_TEKST = {
    "restafval": "restafval",
    "gft": "gft",
    "papier en karton": "papier",
}
_DATE_RE = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
_CODE_RE = re.compile(r"\b(REST|GFT|PK)\d+", re.IGNORECASE)
_KG_RE = re.compile(r"([\d.,]+)\s*kg", re.IGNORECASE)


def parse_date(text: str) -> date | None:
    """Zoek de eerste datum dd/mm/jjjj in een tekst."""
    match = _DATE_RE.search(text or "")
    if not match:
        return None
    day, month, year = (int(part) for part in match.groups())
    try:
        return date(year, month, day)
    except ValueError:
        return None


def parse_amount(text: str) -> float | None:
    """'€ -6,08' of '<div>€ 1.200,50</div>' naar een float."""
    plain = BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)
    cleaned = re.sub(r"[^0-9,.\-]", "", plain)
    if not cleaned or cleaned in {"-", ",", "."}:
        return None
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return None


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value else None


def parse_containers(html: str) -> dict[str, object]:
    """Volgende inzameling per fractie van de Containers-pagina."""
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, object] = {}
    pattern = re.compile(
        r"^Volgende inzameling\s+(restafval|gft|papier en karton)\s+(\d{2}/\d{2}/\d{4})",
        re.IGNORECASE,
    )
    for item in soup.find_all("li"):
        match = pattern.match(item.get_text(" ", strip=True))
        if match:
            fractie = _FRACTIE_TEKST[match.group(1).lower()]
            result[f"volgende_{fractie}"] = _iso(parse_date(match.group(2)))
    return result


def parse_saldo(html: str) -> float | None:
    """Huidig saldo van de Verrichtingen-pagina."""
    soup = BeautifulSoup(html, "html.parser")
    label = soup.find("label", string=re.compile(r"Huidig saldo", re.IGNORECASE))
    group = label.find_parent("div", class_="form-group") if label else None
    field = group.find("input") if group else None
    return parse_amount(field.get("value", "")) if field else None


def parse_verrichtingen(text: str) -> list[dict[str, object]]:
    """JSON van ShowResultsVerrichtingen naar een lijst met rijen."""
    try:
        data = json.loads(text)
        rows = data["aaData"]
    except (ValueError, KeyError, TypeError) as err:
        raise EcowerfError(f"Onverwacht antwoord voor verrichtingen: {err}") from err

    result: list[dict[str, object]] = []
    for row in rows:
        if len(row) < 4:
            continue
        mededeling = str(row[2])
        code = _CODE_RE.search(mededeling)
        fractie = None
        if code:
            fractie = next(
                (k for k, v in FRACTIES.items() if v == code.group(1).upper()), None
            )
        kg_match = _KG_RE.search(mededeling)
        kg = None
        if kg_match:
            try:
                kg = float(kg_match.group(1).replace(",", "."))
            except ValueError:
                kg = None
        row_date = parse_date(str(row[0]))
        result.append(
            {
                "datum": row_date,
                "type": str(row[1]).strip(),
                "fractie": fractie,
                # datum van de ophaling staat in de mededeling, anders de rijdatum
                "ophaaldatum": parse_date(mededeling) or row_date,
                "kg": kg,
                "bedrag": parse_amount(str(row[3])),
            }
        )
    return result


def build_verrichtingen_state(
    rows: list[dict[str, object]], today: date
) -> dict[str, object]:
    """Laatste ophaling, tarief, jaar- en maandtotalen en huur per fractie."""
    result: dict[str, object] = {}
    huur_totaal = 0.0
    maand_totaal = 0.0
    for fractie in FRACTIES:
        own = [r for r in rows if r["fractie"] == fractie]
        gewicht = [r for r in own if r["type"] == "Gewicht" and r["kg"] is not None]
        kosten_rows = [r for r in own if r["type"] in ("Gewicht", "Aanbieding")]

        def kosten(ophaaldatum: date | None) -> float:
            return round(
                -sum(
                    (r["bedrag"] or 0.0)
                    for r in kosten_rows
                    if r["ophaaldatum"] == ophaaldatum
                ),
                2,
            )

        # laatste ophaling
        laatste = max(gewicht, key=lambda r: r["ophaaldatum"] or date.min, default=None)
        if laatste:
            kg = laatste["kg"]
            result[f"{fractie}_laatste_datum"] = _iso(laatste["ophaaldatum"])
            result[f"{fractie}_laatste_kg"] = kg
            result[f"{fractie}_laatste_kosten"] = kosten(laatste["ophaaldatum"])
            bedrag = laatste["bedrag"]
            result[f"{fractie}_tarief_per_kg"] = (
                round(-bedrag / kg, 4) if bedrag is not None and kg else None
            )
        else:
            for key in ("laatste_datum", "laatste_kg", "laatste_kosten", "tarief_per_kg"):
                result[f"{fractie}_{key}"] = None

        # dit jaar
        dit_jaar = [
            r for r in gewicht if r["ophaaldatum"] and r["ophaaldatum"].year == today.year
        ]
        result[f"{fractie}_jaar_kg"] = round(sum(r["kg"] for r in dit_jaar), 2)
        result[f"{fractie}_jaar_kosten"] = round(
            -sum(
                (r["bedrag"] or 0.0)
                for r in kosten_rows
                if r["ophaaldatum"] and r["ophaaldatum"].year == today.year
            ),
            2,
        )

        # deze maand (zelfde berekening als dit jaar, voor de huidige kalendermaand)
        maand_kosten = round(
            -sum(
                (r["bedrag"] or 0.0)
                for r in kosten_rows
                if r["ophaaldatum"]
                and (r["ophaaldatum"].year, r["ophaaldatum"].month)
                == (today.year, today.month)
            ),
            2,
        )
        result[f"{fractie}_maand_kosten"] = maand_kosten
        maand_totaal += maand_kosten

        # huur: laatste huurrij
        huur = [r for r in own if r["type"] == "Huur" and r["bedrag"] is not None]
        laatste_huur = max(huur, key=lambda r: r["datum"] or date.min, default=None)
        result[f"{fractie}_huur"] = (
            round(-laatste_huur["bedrag"], 2) if laatste_huur else None
        )
        if laatste_huur:
            huur_totaal += -laatste_huur["bedrag"]

    # alle fracties samen: ophalingen van deze maand plus de maandelijkse huur
    result["huur_totaal"] = round(huur_totaal, 2)
    result["maand_totaal"] = round(maand_totaal + huur_totaal, 2)
    return result


def parse_betalingen(html: str) -> list[dict[str, object]]:
    """Tabel van de Betalingsuitnodigingen-pagina."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table", id="BetalingsUitnodigingen")
    result: list[dict[str, object]] = []
    if table is None or table.tbody is None:
        return result
    for tr in table.tbody.find_all("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(cells) < 5:
            continue
        result.append(
            {
                "bedrag": parse_amount(cells[2]),
                "betaald": cells[3].strip().lower() == "ja",
                "vervaldatum": parse_date(cells[4]),
            }
        )
    return result


def build_betalingen_state(rows: list[dict[str, object]]) -> dict[str, object]:
    """Openstaand bedrag en eerstvolgende vervaldatum."""
    open_rows = [r for r in rows if not r["betaald"]]
    dates = [r["vervaldatum"] for r in open_rows if r["vervaldatum"]]
    return {
        "openstaand": round(sum((r["bedrag"] or 0.0) for r in open_rows), 2),
        "volgende_vervaldatum": _iso(min(dates)) if dates else None,
    }
