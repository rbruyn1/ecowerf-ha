# Ecowerf

Deze app logt in op [mijnecowerf.be](https://www.mijnecowerf.be) met je eigen account en zet de gegevens als sensoren in Home Assistant, via MQTT (apparaat **Ecowerf**).

## Vereisten

- De Mosquitto-app (of een andere MQTT-broker) en de MQTT-integratie in Home Assistant.
- Een account op mijnecowerf.be.

## Configuratie

Instellingen > Apps > Ecowerf > Configuratie.

| Optie | Standaard | Uitleg |
|---|---|---|
| `username` | leeg | Gebruikersnaam voor mijnecowerf.be (verplicht) |
| `password` | leeg | Wachtwoord voor mijnecowerf.be (verplicht) |
| `update_interval_days` | `1` | Hoe vaak de app gegevens ophaalt, in dagen (1 tot 31). Ecowerf boekt een weging pas de dag na de ophaling, vaker ophalen heeft dus geen zin. |
| `log_level` | `info` | `debug`, `info`, `warning` of `error` |
| `dump_pages` | `false` | Zet na de eerste login ruwe gegevens (verrichtingen, Ophaalkalender, Statistieken) in het log. Alleen nodig bij problemen. Het log bevat dan persoonsgegevens. |
| `mqtt_host` | leeg | Leeg laten als je de Mosquitto-app gebruikt: de app haalt de gegevens dan automatisch op via de Supervisor |
| `mqtt_port` | `1883` | Poort van de broker, enkel bij een handmatig ingevulde broker |
| `mqtt_username` | leeg | Enkel bij een handmatig ingevulde broker |
| `mqtt_password` | leeg | Enkel bij een handmatig ingevulde broker |

## Sensoren

Per fractie (restafval, gft, papier en karton) maakt de app dezelfde sensoren aan:

| Sensor | Eenheid | Uitleg |
|---|---|---|
| Volgende ophaling | datum | Volgende inzameling volgens de Containers-pagina |
| Laatste ophaling | datum | Datum van de laatste gewogen ophaling |
| Laatste gewicht | kg | Gewicht van de laatste ophaling |
| Laatste kosten | EUR | Gewicht plus aanbieding van de laatste ophaling |
| Tarief per kg | EUR/kg | Berekend: bedrag van de laatste weging gedeeld door het gewicht |
| Gewicht dit jaar | kg | Som van de gewogen ophalingen dit kalenderjaar |
| Kosten dit jaar | EUR | Gewicht plus aanbiedingen dit kalenderjaar |
| Kosten deze maand | EUR | Gewicht plus aanbiedingen van de ophalingen in de huidige kalendermaand |
| Huur | EUR | Laatste huurbedrag per maand |

Daarnaast:

| Sensor | Eenheid | Uitleg |
|---|---|---|
| Saldo | EUR | Huidig saldo van de Verrichtingen-pagina |
| Openstaand bedrag | EUR | Som van de betalingsuitnodigingen die nog niet betaald zijn |
| Volgende vervaldatum | datum | Eerste vervaldatum van een onbetaalde uitnodiging |
| Huur totaal per maand | EUR | Som van de huurbedragen van de drie fracties |
| Totaal deze maand | EUR | Ophalingen van deze maand van alle fracties plus de maandelijkse huur |

Bij een mislukte login of een lege reactie probeert de app het na een uur opnieuw, in plaats van pas bij het volgende interval.

Sensoren zonder gegevens (bijvoorbeeld het laatste gewicht gft zolang er nog geen weging was) tonen "onbekend". Als de app stopt, tonen alle sensoren "niet beschikbaar".

## Controleren

Start de app en open het tabblad Log. Je ziet dan `LOGIN GESLAAGD`, `Waarden: {...}` en `MQTT: ... sensoren aangemeld`. De sensoren staan daarna onder Instellingen > Apparaten en diensten > MQTT > Ecowerf.

Bij een foute login stopt de app met een melding, zodat je account niet geblokkeerd raakt door herhaalde pogingen. Pas de configuratie aan en start de app opnieuw.
