#!/usr/bin/with-contenv bashio

export ECOWERF_USERNAME="$(bashio::config 'username')"
export ECOWERF_PASSWORD="$(bashio::config 'password')"
export ECOWERF_INTERVAL_MIN="$(bashio::config 'update_interval_minutes')"
export ECOWERF_LOG_LEVEL="$(bashio::config 'log_level')"
export ECOWERF_DUMP_PAGES="$(bashio::config 'dump_pages')"

bashio::log.info "Ecowerf-app wordt gestart"
exec python3 -u /app/main.py
