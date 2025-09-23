#!/usr/bin/env bash
set -euo pipefail

# ---- Config ----
BASE_URL="https://cloud.sycon.io"
USERNAME="${SYCON_USERNAME:-your_username}"
PASSWORD="${SYCON_PASSWORD:-your_password}"

# Time window (UTC, ISO-8601). Adjust as needed.
START="2025-09-22T00:00:00Z"
END="2025-09-23T00:00:00Z"

# Example device & field (replace with your own)
DEVICE_ID="12345"
FIELD="TEMPERATURE_CELSIUS"  # see enum in OpenAPI

echo "Logging in to ${BASE_URL} ..."
HEADERS="$(curl -sS -D - -o /dev/null -X POST "${BASE_URL}/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"username\":\"${USERNAME}\",\"password\":\"${PASSWORD}\"}")"

# Normalize and extract headers (case-insensitive)
AUTH_LINE="$(printf "%s" "$HEADERS" | tr -d '\r' | awk -F': ' 'tolower($1)=="authorization"{print $2}')"
RENEW_LINE="$(printf "%s" "$HEADERS" | tr -d '\r' | awk -F': ' 'tolower($1)=="renew"{print $2}')"

if [[ -z "${AUTH_LINE}" || -z "${RENEW_LINE}" ]]; then
  echo "Login failed or headers missing:"
  echo "$HEADERS"
  exit 1
fi

# Strip optional "Bearer " prefix
JWT="${AUTH_LINE#Bearer }"
RENEW="${RENEW_LINE}"

echo "JWT acquired (len=$(printf "%s" "$JWT" | wc -c)). Renew token acquired."

echo; echo "Checking JWT ..."
curl -sS -i "${BASE_URL}/auth/check" \
  -H "Authorization: Bearer ${JWT}"

echo; echo "Listing devices ..."
curl -sS "${BASE_URL}/api/devices" \
  -H "Authorization: Bearer ${JWT}" \
  -H "Accept: application/json"

echo; echo "Fetching raw data (${FIELD}) ..."
curl -sS "${BASE_URL}/api/devices/${DEVICE_ID}/${FIELD}/data/raw?start=${START}&end=${END}&tailLimit=1000" \
  -H "Authorization: Bearer ${JWT}" \
  -H "Accept: application/json"

echo; echo "Optionally renew the JWT ..."
curl -sS -i "${BASE_URL}/auth/renew" \
  -H "Renew: ${RENEW}"
