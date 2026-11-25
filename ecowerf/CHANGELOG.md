# Changelog

## 0.2.0 - 2026-11-25

- Nieuw: de app zet de gegevens van mijnecowerf.be als sensoren in Home Assistant, via MQTT-discovery (apparaat **Ecowerf**, 27 sensoren).
- Per fractie (restafval, gft, papier en karton): volgende ophaling, laatste ophaling, laatste gewicht, laatste kosten, tarief per kg, gewicht en kosten dit jaar, huur.
- Algemeen: saldo, openstaand bedrag en volgende vervaldatum.
- Nieuwe opties: `mqtt_host`, `mqtt_port`, `mqtt_username` en `mqtt_password`. Laat `mqtt_host` leeg als je de Mosquitto-app gebruikt, dan haalt de app de gegevens automatisch op via de Supervisor.
- Gewijzigd: `dump_pages` staat nu standaard op `false`.
- Vereist Home Assistant 2025.10 of nieuwer en een MQTT-broker.

## 0.1.3 - 2026-11-25

- De optie `dump_pages` zet nu de verrichtingen (JSON van `ShowResultsVerrichtingen`), de Ophaalkalender en de Statistieken in het log.

## 0.1.2 - 2026-11-25

- Nieuwe optie `dump_pages`: zet na de eerste login de HTML van Containers, Verrichtingen en Betalingsuitnodigingen in het log.

## 0.1.1 - 2026-11-25

- Opgelost: de app kon niet gebouwd worden (`$BUILD_FROM` was leeg). Er is een `build.yaml` met een vaste baseimage toegevoegd.

## 0.1.0 - 2026-11-25

- Eerste versie: de app logt in op mijnecowerf.be en meldt het resultaat in het log.
