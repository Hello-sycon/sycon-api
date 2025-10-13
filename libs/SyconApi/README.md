# SyconApi

Lightweight Python client for the Sycon cloud API — concise, synchronous wrapper to authenticate and fetch device lists and raw device data.

## Install

```bash
# HTTPS
pip install "git+https://github.com/Hello-sycon/sycon-api.git@SyconApi-v$VERSION#subdirectory=libs/SyconApi"

#SSH
pip install "git+ssh://git@github.com/Hello-sycon/sycon-api.git@SyconApi-v$VERSION#subdirectory=libs/SyconApi"
```

>[!NOTE]
>To select the $VERSION variable, you can see the release associate to tag section in github repository

## Quick example

```py
from sycon_api import SyconApi

client = SyconApi(username="me@example.com", password="secret", debug=False)

# authenticate (normally called automatically by methods that need a token)
client.authenticate()

# list devices
devices = client.get_devices_list()
print(devices)

# get data for a single device
data = client.get_data_from_device(
    device_id="device-123",
    field=SyconApi.SyconApiDataFields.TEMPERATURE_CELSIUS,
    start_date="2025-10-03T12:30:00.000Z",
    end_date="2025-10-03T13:30:00.000Z",
    head_limit=100,
)
print(data)

# get data for multiple devices (use tuple — function is cached)
devices_data = client.get_data_from_devices(
    devices_id=("device-123", "device-456"),
    field=SyconApi.SyconApiDataFields.CO2_PPM,
    start_date="2025-10-03T12:30:00.000Z",
    end_date="2025-10-03T13:30:00.000Z",
    head_limit=10,
)
print(devices_data)

# get data for all devices (uses get_devices_list internally)
all_data = client.get_data_from_all_devices(
    field=SyconApi.SyconApiDataFields.HUMIDITY_PERCENT,
    start_date="2025-10-03T12:30:00.000Z",
    end_date="2025-10-03T13:30:00.000Z",
    head_limit=10,
)
print(all_data)
```

## Public API (concise)

All methods below belong to `SyconApi` (no leading underscore).

### Constructor / properties

* `SyconApi(username: str, password: str, debug: bool = False, debug_level: int = SyconApiLogLevel.DEBUG.value) -> SyconApi`
  Create client. Pass `debug=True` to enable logger.
* `username` — property, configured username.
* `token` — property, current token (may be `None` until authenticated).

### Enums

* `SyconApi.SyconApiDataFields` — data field constants (e.g. `TEMPERATURE_CELSIUS`, `CO2_PPM`, `HUMIDITY_PERCENT`, ...).
* `SyconApi.SyconApiV1Route` — endpoints (LOGIN, RENEW, CHECK, DEVICES, DATA).
* `SyconApi.SyconApiLogLevel` — log levels.

### Exceptions you may catch

* `SyconApiInvalidParametersException` — invalid argument(s).
* `SyconApiMissingParametersException` — required parameter missing.
* `SyconApiBadResponseException` — 4xx HTTP response or invalid JSON where JSON is expected.
* `SyconApiServerErrorResponseException` — 5xx HTTP response.

### Main methods

* `authenticate() -> None`
  Authenticate with username/password. On success the client `token` is set from response headers.

* `renew_token() -> None`
  Renew token using current token. Raises `SyconApiBadResponseException` if no `Authorization` header in response.

* `check_token() -> bool`
  Check if current token is still valid. Returns `True` on HTTP 200.

* `get_devices_list() -> Optional[Dict[str, Any]]`
  Return devices list (parsed JSON) on HTTP 200. Raises `SyconApiBadResponseException` if response JSON is invalid.

* `get_data_from_device(device_id: str, field: SyconApiDataFields, start_date: str, end_date: str, head_limit: Optional[int] = None, tail_limit: Optional[int] = None, external_sensor_id: Optional[str] = None) -> Optional[Dict[str, Any]]`
  Fetch raw data for a single device. Returns a `dict` if response JSON parsed, otherwise `None`. Validates date format (ISO-8601 instant) and requires exactly one of `head_limit` / `tail_limit`.

* `get_data_from_devices(devices_id: Tuple[str], field: SyconApiDataFields, start_date: str, end_date: str, head_limit: Optional[int] = None, tail_limit: Optional[int] = None, external_sensor_id: Optional[str] = None) -> Optional[Dict[str, Any]]`
  Fetch raw data for multiple devices. **Important:** `devices_id` must be an **immutable tuple** (function is cached via `lru_cache`). Returns a dict mapping `device_id` → response body (dict or raw text).

* `get_data_from_all_devices(field: SyconApiDataFields, start_date: str, end_date: str, head_limit: Optional[int] = None, tail_limit: Optional[int] = None, external_sensor_id: Optional[str] = None) -> Optional[Dict[str, Any]]`
  Fetch data for all devices returned by `get_devices_list()`. Skips device entries that do not have an `"id"` key.

## Notes & best practices

* **Dates:** use strict ISO-8601 instant format: `YYYY-MM-DDTHH:MM:SS[.ms]Z` (example: `2025-10-03T12:30:00.000Z`). Invalid format raises `SyconApiInvalidParametersException`.
* **Head/Tail limits:** exactly one of `head_limit` or `tail_limit` must be provided (not both). Limits are capped to `k_size_batch_limit` (default 10000).
* **Caching:** `get_data_from_devices` and `get_data_from_device` are cached (`lru_cache`). For cached calls, ensure all arguments are hashable (use `tuple` for device lists). You can clear the cache with e.g. `SyconApi.get_data_from_devices.cache_clear()`.
* **Errors:** 4xx responses raise `SyconApiBadResponseException`; 5xx raise `SyconApiServerErrorResponseException`. Network-level errors (requests exceptions) will propagate.
* **Logging:** enable `debug=True` in the constructor to activate the internal logger.
