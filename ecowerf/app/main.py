"""Ecowerf-app: haalt gegevens op van mijnecowerf.be en publiceert ze via MQTT."""
from __future__ import annotations

import asyncio
import json
import logging
import os
import sys

import aiohttp

from ecowerf_client import EcowerfApi, EcowerfAuthError, EcowerfError
from mqtt_publisher import MqttPublisher

_LOGGER = logging.getLogger("ecowerf")


async def run() -> int:
    username = os.environ.get("ECOWERF_USERNAME", "").strip()
    password = os.environ.get("ECOWERF_PASSWORD", "")
    days = int(os.environ.get("ECOWERF_INTERVAL_DAYS", "1"))
    interval = days * 86400
    retry = min(interval, 3600)  # na een storing na een uur opnieuw proberen
    dump_pages = os.environ.get("ECOWERF_DUMP_PAGES", "false").lower() == "true"
    mqtt_host = os.environ.get("MQTT_HOST", "").strip()

    if not username or not password:
        _LOGGER.error(
            "Gebruikersnaam of wachtwoord ontbreekt: vul ze in op het "
            "tabblad Configuratie van de app en start de app opnieuw"
        )
        return 1
    if not mqtt_host:
        _LOGGER.error(
            "Geen MQTT-broker gevonden: installeer en start de Mosquitto-app met de "
            "MQTT-integratie, of vul mqtt_host in op het tabblad Configuratie"
        )
        return 1

    publisher = MqttPublisher(
        mqtt_host,
        int(os.environ.get("MQTT_PORT", "1883") or 1883),
        os.environ.get("MQTT_USERNAME", ""),
        os.environ.get("MQTT_PASSWORD", ""),
    )
    publisher.connect()

    first_run = True
    try:
        while True:
            wait = interval
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
                    wait = retry
                    _LOGGER.warning("Login mislukt, volgende poging over %s min: %s", wait // 60, err)
                else:
                    # De dump gebeurt enkel bij de eerste run na het starten van de app
                    if dump_pages and first_run:
                        await api.async_dump_pages()
                    state = await api.async_fetch_state()
                    if state:
                        _LOGGER.info("Waarden: %s", json.dumps(state, ensure_ascii=False))
                        publisher.publish_state(state)
                    else:
                        wait = retry
                        _LOGGER.warning(
                            "Geen gegevens opgehaald, MQTT wordt niet bijgewerkt, "
                            "volgende poging over %s min", wait // 60
                        )
            first_run = False
            if wait == interval:
                _LOGGER.info("Volgende controle over %s dag(en)", days)
            await asyncio.sleep(wait)
    finally:
        publisher.close()


def main() -> None:
    level = os.environ.get("ECOWERF_LOG_LEVEL", "info").upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s %(levelname)s %(message)s",
    )
    sys.exit(asyncio.run(run()))


if __name__ == "__main__":
    main()
