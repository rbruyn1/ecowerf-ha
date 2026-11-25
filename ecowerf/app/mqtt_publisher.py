"""Publiceert de Ecowerf-gegevens als sensoren in Home Assistant via MQTT-discovery."""
from __future__ import annotations

import json
import logging
from typing import Any

import paho.mqtt.client as mqtt

_LOGGER = logging.getLogger("ecowerf.mqtt")

DISCOVERY_PREFIX = "homeassistant"
STATE_TOPIC = "ecowerf/state"
AVAILABILITY_TOPIC = "ecowerf/status"
HA_STATUS_TOPIC = f"{DISCOVERY_PREFIX}/status"

DEVICE = {
    "identifiers": ["ecowerf"],
    "name": "Ecowerf",
    "manufacturer": "Ecowerf",
    "model": "mijnecowerf.be",
}

FRACTIES = {
    "restafval": "restafval",
    "gft": "gft",
    "papier": "papier en karton",
}


def _sensor(key: str, name: str, **extra: Any) -> dict[str, Any]:
    return {"key": key, "name": name, **extra}


def _build_sensors() -> list[dict[str, Any]]:
    sensors: list[dict[str, Any]] = []
    for fractie, label in FRACTIES.items():
        sensors += [
            _sensor(f"volgende_{fractie}", f"Volgende ophaling {label}",
                    device_class="date", icon="mdi:calendar"),
            _sensor(f"{fractie}_laatste_datum", f"Laatste ophaling {label}",
                    device_class="date", icon="mdi:calendar-check"),
            _sensor(f"{fractie}_laatste_kg", f"Laatste gewicht {label}",
                    device_class="weight", unit="kg"),
            _sensor(f"{fractie}_laatste_kosten", f"Laatste kosten {label}",
                    device_class="monetary", unit="EUR"),
            _sensor(f"{fractie}_tarief_per_kg", f"Tarief per kg {label}",
                    unit="EUR/kg", icon="mdi:cash"),
            _sensor(f"{fractie}_jaar_kg", f"Gewicht dit jaar {label}",
                    device_class="weight", unit="kg"),
            _sensor(f"{fractie}_jaar_kosten", f"Kosten dit jaar {label}",
                    device_class="monetary", unit="EUR"),
            _sensor(f"{fractie}_huur", f"Huur {label}",
                    device_class="monetary", unit="EUR"),
        ]
    sensors += [
        _sensor("saldo", "Saldo", device_class="monetary", unit="EUR"),
        _sensor("openstaand", "Openstaand bedrag", device_class="monetary", unit="EUR"),
        _sensor("volgende_vervaldatum", "Volgende vervaldatum",
                device_class="date", icon="mdi:calendar-alert"),
    ]
    return sensors


SENSORS = _build_sensors()


def _new_client() -> mqtt.Client:
    """Werkt met paho-mqtt 1.x en 2.x."""
    try:
        return mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id="ecowerf_app")
    except AttributeError:
        return mqtt.Client(client_id="ecowerf_app")


class MqttPublisher:
    """Houdt de verbinding vast en publiceert discovery, status en beschikbaarheid."""

    def __init__(self, host: str, port: int, username: str, password: str) -> None:
        self._host = host
        self._port = port
        self._state: dict[str, object] = {}
        self._connected = False
        self._client = _new_client()
        if username:
            self._client.username_pw_set(username, password or None)
        self._client.will_set(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def connect(self) -> None:
        """Verbind op de achtergrond; herverbindt zelf na een storing."""
        _LOGGER.info("MQTT: verbinden met %s:%s", self._host, self._port)
        self._client.connect_async(self._host, self._port, keepalive=60)
        self._client.loop_start()

    def close(self) -> None:
        if self._connected:
            self._client.publish(AVAILABILITY_TOPIC, "offline", qos=1, retain=True)
        self._client.loop_stop()
        self._client.disconnect()

    def publish_state(self, state: dict[str, object]) -> None:
        """Bewaar de nieuwe waarden en stuur ze door zodra er verbinding is."""
        self._state.update(state)
        if self._connected:
            self._publish_state()

    # -- intern --------------------------------------------------------------

    def _on_connect(self, client, userdata, flags, rc) -> None:  # noqa: ANN001
        if rc != 0:
            _LOGGER.error("MQTT: verbinding geweigerd (code %s), controleer de gegevens", rc)
            return
        self._connected = True
        _LOGGER.info("MQTT: verbonden")
        client.subscribe(HA_STATUS_TOPIC)
        self._publish_all()

    def _on_disconnect(self, client, userdata, rc) -> None:  # noqa: ANN001
        self._connected = False
        if rc != 0:
            _LOGGER.warning("MQTT: verbinding verbroken (code %s), er wordt opnieuw verbonden", rc)

    def _on_message(self, client, userdata, msg) -> None:  # noqa: ANN001
        # Home Assistant meldt "online" na een herstart: alles opnieuw sturen
        if msg.topic == HA_STATUS_TOPIC and msg.payload.decode(errors="ignore") == "online":
            _LOGGER.info("MQTT: Home Assistant is opnieuw gestart, gegevens worden herzonden")
            self._publish_all()

    def _publish_all(self) -> None:
        self._publish_discovery()
        self._client.publish(AVAILABILITY_TOPIC, "online", qos=1, retain=True)
        if self._state:
            self._publish_state()

    def _publish_discovery(self) -> None:
        for sensor in SENSORS:
            key = sensor["key"]
            config: dict[str, Any] = {
                "name": sensor["name"],
                "unique_id": f"ecowerf_{key}",
                "default_entity_id": f"sensor.ecowerf_{key}",
                "state_topic": STATE_TOPIC,
                "value_template": f"{{{{ value_json.{key} }}}}",
                "availability_topic": AVAILABILITY_TOPIC,
                "device": DEVICE,
            }
            if "device_class" in sensor:
                config["device_class"] = sensor["device_class"]
            if "unit" in sensor:
                config["unit_of_measurement"] = sensor["unit"]
            if "icon" in sensor:
                config["icon"] = sensor["icon"]
            self._client.publish(
                f"{DISCOVERY_PREFIX}/sensor/ecowerf_{key}/config",
                json.dumps(config),
                qos=1,
                retain=True,
            )
        _LOGGER.info("MQTT: %s sensoren aangemeld bij Home Assistant", len(SENSORS))

    def _publish_state(self) -> None:
        self._client.publish(STATE_TOPIC, json.dumps(self._state), qos=1, retain=True)
        _LOGGER.info("MQTT: %s waarden gepubliceerd", len(self._state))
