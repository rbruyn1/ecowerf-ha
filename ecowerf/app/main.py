"""Ecowerf-app: logt periodiek in op mijnecowerf.be (stap 1: enkel login testen)."""
from __future__ import annotations

import asyncio
import logging
import os
import sys

import aiohttp

from ecowerf_client import EcowerfApi, EcowerfAuthError, EcowerfError

_LOGGER = logging.getLogger("ecowerf")


async def run() -> int:
    username = os.environ.get("ECOWERF_USERNAME", "").strip()
    password = os.environ.get("ECOWERF_PASSWORD", "")
    interval = int(os.environ.get("ECOWERF_INTERVAL_MIN", "360")) * 60

    if not username or not password:
        _LOGGER.error(
            "Gebruikersnaam of wachtwoord ontbreekt: vul ze in op het "
            "tabblad Configuratie van de app en start de app opnieuw"
        )
        return 1

    while True:
        # Telkens een nieuwe sessie, zodat er geen oude cookies blijven hangen
        async with aiohttp.ClientSession() as session:
            api = EcowerfApi(session, username, password)
            try:
                await api.async_login()
            except EcowerfAuthError:
                # Niet blijven proberen: voorkomt dat het account geblokkeerd raakt
                _LOGGER.error(
                    "Login geweigerd: controleer gebruikersnaam en wachtwoord "
                    "in de configuratie en start de app opnieuw"
                )
                return 1
            except EcowerfError as err:
                _LOGGER.warning("Login mislukt, volgende poging over %s s: %s", interval, err)
        _LOGGER.info("Volgende controle over %s minuten", interval // 60)
        await asyncio.sleep(interval)


def main() -> None:
    level = os.environ.get("ECOWERF_LOG_LEVEL", "info").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
