# Ecowerf voor Home Assistant

Haalt je gegevens op van [mijnecowerf.be](https://www.mijnecowerf.be) en zet ze als sensoren in Home Assistant: volgende ophaling per fractie, laatste ophaling met gewicht en kosten, tarief per kg, jaartotalen, huur, saldo en openstaande betalingen.

Huidige versie van de app: **0.3.2**. Zie [CHANGELOG.md](ecowerf/CHANGELOG.md) voor de wijzigingen per versie.

## Vereisten

- Home Assistant 2025.10 of nieuwer
- Een MQTT-broker, bijvoorbeeld de Mosquitto-app, met de MQTT-integratie in Home Assistant
- Een account op mijnecowerf.be

## Installatie als app (aanbevolen)

1. Ga in Home Assistant naar Instellingen > Apps > App-winkel.
2. Menu rechtsboven (drie puntjes) > Repositories > voeg toe: `https://github.com/rbruyn1/ecowerf-ha`
3. Open de app Ecowerf en kies Installeren.
4. Vul op het tabblad Configuratie je gebruikersnaam en wachtwoord van mijnecowerf.be in en sla op.
5. Start de app en controleer het tabblad Log.
6. De sensoren staan onder Instellingen > Apparaten en diensten > MQTT > Ecowerf.

## Configuratie

| Optie | Standaard | Uitleg |
|---|---|---|
| `username` | leeg | Gebruikersnaam voor mijnecowerf.be (verplicht) |
| `password` | leeg | Wachtwoord voor mijnecowerf.be (verplicht) |
| `update_interval_days` | `1` | Hoe vaak de app gegevens ophaalt, in dagen (1 tot 31) |
| `log_level` | `info` | `debug`, `info`, `warning` of `error` |
| `dump_pages` | `false` | Zet ruwe gegevens in het log, alleen nodig bij problemen (bevat persoonsgegevens) |
| `mqtt_host` | leeg | Leeg laten bij de Mosquitto-app (automatisch via de Supervisor) |
| `mqtt_port` | `1883` | Enkel bij een handmatig ingevulde broker |
| `mqtt_username` | leeg | Enkel bij een handmatig ingevulde broker |
| `mqtt_password` | leeg | Enkel bij een handmatig ingevulde broker |

## Sensoren

Per fractie (restafval, gft, papier en karton): volgende ophaling, laatste ophaling, laatste gewicht, laatste kosten, tarief per kg, gewicht dit jaar, kosten dit jaar, kosten deze maand en huur.

Algemeen: saldo, huur totaal per maand, totaal deze maand (ophalingen en huur), huur dit jaar, totaal dit jaar (ophalingen en huur), openstaand bedrag en volgende vervaldatum.

Een uitgebreide uitleg per sensor staat in [ecowerf/DOCS.md](ecowerf/DOCS.md).

## Privacy

De app slaat je gebruikersnaam en wachtwoord enkel op in de configuratie van de app in Home Assistant en stuurt ze alleen naar mijnecowerf.be. De sensoren bevatten geen adres, klantnummer of OGM. Alleen met `dump_pages` aan komen persoonsgegevens in het log.

## Custom component (niet gebruiken)

De map `custom_components/ecowerf` bevat een eerste versie als integratie. Die kan enkel inloggen en maakt nog geen sensoren aan. Gebruik de app.
