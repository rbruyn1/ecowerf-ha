#!/usr/bin/with-contenv bashio

export ECOWERF_USERNAME="$(bashio::config 'username')"
export ECOWERF_PASSWORD="$(bashio::config 'password')"
export ECOWERF_INTERVAL_DAYS="$(bashio::config 'update_interval_days')"
export ECOWERF_LOG_LEVEL="$(bashio::config 'log_level')"
export ECOWERF_DUMP_PAGES="$(bashio::config 'dump_pages')"

# MQTT: handmatig ingevuld, anders automatisch via de Supervisor (Mosquitto-app)
if bashio::config.has_value 'mqtt_host'; then
    export MQTT_HOST="$(bashio::config 'mqtt_host')"
    export MQTT_PORT="$(bashio::config 'mqtt_port')"
    export MQTT_USERNAME="$(bashio::config 'mqtt_username')"
    export MQTT_PASSWORD="$(bashio::config 'mqtt_password')"
    bashio::log.info "MQTT-broker uit de configuratie: ${MQTT_HOST}:${MQTT_PORT}"
elif bashio::services.available "mqtt"; then
    export MQTT_HOST="$(bashio::services mqtt 'host')"
    export MQTT_PORT="$(bashio::services mqtt 'port')"
    export MQTT_USERNAME="$(bashio::services mqtt 'username')"
    export MQTT_PASSWORD="$(bashio::services mqtt 'password')"
    bashio::log.info "MQTT-broker via de Supervisor: ${MQTT_HOST}:${MQTT_PORT}"
else
    bashio::log.warning "Geen MQTT-broker gevonden"
fi

bashio::log.info "Ecowerf-app wordt gestart"
exec python3 -u /app/main.py
