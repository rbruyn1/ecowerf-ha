# Ecowerf

Deze app logt in op [mijnecowerf.be](https://www.mijnecowerf.be) met je eigen account.

> Status: in opbouw. Op dit moment test de app enkel de login en toont het resultaat in het log. Sensoren voor ophaaldata en tarieven volgen.

## Configuratie

Instellingen > Apps > Ecowerf > Configuratie.

| Optie | Standaard | Uitleg |
|---|---|---|
| `username` | leeg | Gebruikersnaam voor mijnecowerf.be (verplicht) |
| `password` | leeg | Wachtwoord voor mijnecowerf.be (verplicht) |
| `update_interval_minutes` | `360` | Hoe vaak de app inlogt, tussen 15 en 1440 minuten |
| `log_level` | `info` | `debug`, `info`, `warning` of `error` |

## Controleren

Start de app en open het tabblad Log. Bij een geslaagde login staat er `LOGIN GESLAAGD`. Bij een foute login stopt de app met een melding, zodat je account niet geblokkeerd raakt door herhaalde pogingen. Pas de configuratie aan en start de app opnieuw.
