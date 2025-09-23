#!/usr/bin/env python3
import os
import sys
import time
import requests
from datetime import datetime, timezone, timedelta

BASE_URL = "https://cloud.sycon.io"
USERNAME = os.getenv("SYCON_USERNAME", "your_username")
PASSWORD = os.getenv("SYCON_PASSWORD", "your_password")

# Time window (last 24h)
END = datetime.now(timezone.utc).replace(microsecond=0)
START = END - timedelta(days=1)

DEVICE_ID = 12345  # replace with your own
FIELD = "TEMPERATURE_CELSIUS"  # see enum in OpenAPI

def iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")

def login():
    r = requests.post(
        f"{BASE_URL}/auth/login",
        json={"username": USERNAME, "password": PASSWORD},
        timeout=20,
    )
    if r.status_code != 200:
        print("Login failed:", r.status_code, r.text)
        sys.exit(1)
    auth = r.headers.get("Authorization") or ""
    renew = r.headers.get("Renew") or ""
    if not auth or not renew:
        print("Missing Authorization/Renew headers:", dict(r.headers))
        sys.exit(1)
    jwt = auth.split(" ", 1)[1] if auth.startswith("Bearer ") else auth
    return jwt, renew

def auth_check(jwt: str):
    r = requests.get(
        f"{BASE_URL}/auth/check",
        headers={"Authorization": f"Bearer {jwt}"},
        timeout=10,
    )
    print("auth/check:", r.status_code)

def list_devices(jwt: str):
    r = requests.get(
        f"{BASE_URL}/api/devices",
        headers={"Authorization": f"Bearer {jwt}", "Accept": "application/json"},
        timeout=20,
    )
    r.raise_for_status()
    return r.json()

def get_raw(jwt: str, device_id: int, field: str, start: datetime, end: datetime, tail_limit=1000, external_sensor_id=None):
    params = {"start": iso(start), "end": iso(end), "tailLimit": tail_limit}
    if external_sensor_id:
        params["externalSensorId"] = external_sensor_id
    r = requests.get(
        f"{BASE_URL}/api/devices/{device_id}/{field}/data/raw",
        headers={"Authorization": f"Bearer {jwt}", "Accept": "application/json"},
        params=params,
        timeout=30,
    )
    print("raw data:", r.status_code)
    r.raise_for_status()
    return r.json()

def renew(jwt_renew: str):
    r = requests.get(f"{BASE_URL}/auth/renew", headers={"Renew": jwt_renew}, timeout=10)
    if r.status_code == 200:
        auth = r.headers.get("Authorization", "")
        new_jwt = auth.split(" ", 1)[1] if auth.startswith("Bearer ") else auth
        return new_jwt
    print("Renew failed:", r.status_code, r.text)
    return None

if __name__ == "__main__":
    jwt, renew_token = login()
    auth_check(jwt)

    devices = list_devices(jwt)
    print("Devices:", devices[:1], " ... total:", len(devices))

    data = get_raw(jwt, DEVICE_ID, FIELD, START, END, tail_limit=1000)
    print("First timestamps:", data.get("firstTimestamp"), "Last:", data.get("lastTimestamp"), "Count:", data.get("count"))

    # Optional: try renewing
    new_jwt = renew(renew_token)
    if new_jwt:
        print("JWT renewed (len:", len(new_jwt), ")")
