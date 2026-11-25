# Ecowerf voor Home Assistant

Custom integration die inlogt op het Ecowerf-portaal en de ophaaldata en de betaalde tarieven als sensoren in Home Assistant zet.

> Status: in opbouw, nog niet bruikbaar.

## Installatie als app (aanbevolen)

1. Ga in Home Assistant naar Instellingen > Apps > App-winkel.
2. Menu rechtsboven (drie puntjes) > Repositories > voeg toe: `https://github.com/rbruyn1/ecowerf-ha`
3. Open de app Ecowerf en kies Installeren.
4. Vul op het tabblad Configuratie je gebruikersnaam en wachtwoord van mijnecowerf.be in en sla op.
5. Start de app en controleer het tabblad Log.

## Installatie als custom component

1. Kopieer de map `custom_components/ecowerf` naar de map `custom_components` van je Home Assistant.
2. Herstart Home Assistant.
3. Voeg de integratie toe via Instellingen > Apparaten en diensten.
