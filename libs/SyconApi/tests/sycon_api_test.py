# tests/test_sycon_api_full.py
import pytest
from unittest.mock import MagicMock
import requests

from sycon_api.sycon_api import (
    SyconApi,
    SyconApiMissingParametersException,
    SyconApiInvalidParametersException,
    SyconApiBadResponseException,
    SyconApiServerErrorResponseException,
)

SyconApiDataFields = SyconApi.SyconApiDataFields

# ---------- Helper fake response ----------
class FakeResponse:
    def __init__(self, status_code=200, json_data=None, text="", headers=None):
        self.status_code = status_code
        self._json_data = json_data
        self.text = text
        self.headers = headers or {}

    def json(self):
        if isinstance(self._json_data, Exception):
            raise self._json_data
        return self._json_data


# ---------- Fixtures ----------
@pytest.fixture
def client(monkeypatch):
    c = SyconApi(username="u", password="p", debug=False)
    monkeypatch.setattr(SyconApi, "_manage_token", lambda self: None)
    return c


# ---------- Basic helpers ----------
def test_format_header_helpers():
    headers = {}
    SyconApi._format_header_token("abc", headers)
    assert headers["Authorization"] == "Bearer abc"

    headers2 = {}
    SyconApi._format_header_content_type_json(headers2)
    assert headers2["Content-type"] == "application/json"


# ---------- Parameter validators ----------
def test_raise_on_threshold_presence_errors(client):
    with pytest.raises(SyconApiMissingParametersException):
        client._raise_on_threshold_presence(None, None)

    with pytest.raises(SyconApiInvalidParametersException):
        client._raise_on_threshold_presence(1, 2)

    client._raise_on_threshold_presence(1, None)
    client._raise_on_threshold_presence(None, 2)


def test_raise_on_date_ISO_8601_bad_format_valid_and_invalid(client):
    client._raise_on_date_ISO_8601_bad_format("2025-10-03T12:30:00.000Z")

    with pytest.raises(SyconApiInvalidParametersException):
        client._raise_on_date_ISO_8601_bad_format("2025-10-03 12:30:00")


def test_fill_get_data_args_caps_and_external(monkeypatch):
    c = SyconApi(username="u", password="p")
    args = {}
    c._fill_get_data_args(args=args, start_date="s", end_date="e", head_limit=SyconApi.k_size_batch_limit + 100)
    assert args["start"] == "s"
    assert args["end"] == "e"
    assert args["headLimit"] == SyconApi.k_size_batch_limit

    args = {}
    c._fill_get_data_args(args=args, start_date="s", end_date="e", tail_limit=SyconApi.k_size_batch_limit + 1)
    assert args["tailLimit"] == SyconApi.k_size_batch_limit

    args = {}
    c._fill_get_data_args(args=args, start_date="s", end_date="e", head_limit=1, external_sensor_id="ext123")
    assert args["externalSensorId"] == "ext123"


# ---------- _get_request / _post_request behavior (use __wrapped__ to bypass tenacity waits) ----------
def test__get_request_raises_server_error(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        return FakeResponse(status_code=503, text="srv error")

    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(SyconApiServerErrorResponseException):
        SyconApi._get_request.__wrapped__(headers={}, url="http://x", args={})


def test__get_request_raises_client_bad_response(monkeypatch):
    def fake_get(url, params=None, headers=None, timeout=None):
        return FakeResponse(status_code=404, text="not found")

    monkeypatch.setattr(requests, "get", fake_get)
    with pytest.raises(SyconApiBadResponseException):
        SyconApi._get_request.__wrapped__(headers={}, url="http://x", args={})


def test__post_request_raises_server_and_client(monkeypatch):
    def fake_post(url, headers=None, data=None, timeout=None):
        return FakeResponse(status_code=502, text="bad")
    monkeypatch.setattr(requests, "post", fake_post)
    with pytest.raises(SyconApiServerErrorResponseException):
        SyconApi._post_request.__wrapped__(headers={}, url="http://x", data={})

    def fake_post2(url, headers=None, data=None, timeout=None):
        return FakeResponse(status_code=400, text="bad json")
    monkeypatch.setattr(requests, "post", fake_post2)
    with pytest.raises(SyconApiBadResponseException):
        SyconApi._post_request.__wrapped__(headers={}, url="http://x", data={})


# ---------- Authentication / renew / check ----------
def test_authenticate_sets_token(monkeypatch):
    client = SyconApi(username="u", password="p")
    def fake_post(headers, url, data=None):
        return FakeResponse(status_code=200, headers={"Authorization": "Bearer-TOKEN"})

    monkeypatch.setattr(SyconApi, "_post_request", staticmethod(fake_post))
    client.authenticate()
    assert client._token == "Bearer-TOKEN"


def test_renew_token_and_check_token(monkeypatch):
    client = SyconApi(username="u", password="p")
    client._token = "oldtoken"

    def fake_get_no_auth(headers, url, args=None):
        return FakeResponse(status_code=200, headers={})

    monkeypatch.setattr(SyconApi, "_get_request", staticmethod(fake_get_no_auth))
    with pytest.raises(SyconApiBadResponseException):
        client.renew_token()

    def fake_get_with_auth(headers, url, args=None):
        return FakeResponse(status_code=200, headers={"Authorization": "newtoken"})

    monkeypatch.setattr(SyconApi, "_get_request", staticmethod(fake_get_with_auth))
    client.renew_token()
    assert client._token == "newtoken"

    monkeypatch.setattr(SyconApi, "_get_request", staticmethod(lambda headers, url, args=None: FakeResponse(status_code=200)))
    assert client.check_token() is True
    monkeypatch.setattr(SyconApi, "_get_request", staticmethod(lambda headers, url, args=None: FakeResponse(status_code=401)))
    assert client.check_token() is False


# ---------- Devices / data retrieval ----------
def test_get_devices_list_success_and_invalid_json(monkeypatch, client):
    monkeypatch.setattr(SyconApi, "_get_request", staticmethod(lambda headers, url, args=None: FakeResponse(status_code=200, json_data={"devices": []})))
    res = client.get_devices_list()
    assert isinstance(res, dict) and "devices" in res

    monkeypatch.setattr(SyconApi, "_get_request", staticmethod(lambda headers, url, args=None: FakeResponse(status_code=200, json_data=ValueError("bad"))))
    with pytest.raises(SyconApiBadResponseException):
        client.get_devices_list()


def test_get_data_from_device_success_and_invalid(monkeypatch, client):
    monkeypatch.setattr(SyconApi, "_get_request", staticmethod(lambda headers, url, args=None: FakeResponse(status_code=200, json_data={"k": "v"})))
    res = client.get_data_from_device(
        device_id="d1",
        field=SyconApiDataFields.TEMPERATURE_CELSIUS,
        start_date="2025-10-03T12:30:00.000Z",
        end_date="2025-10-03T13:30:00.000Z",
        head_limit=1,
    )
    assert res == {"k": "v"}

    monkeypatch.setattr(SyconApi, "_get_request", staticmethod(lambda headers, url, args=None: FakeResponse(status_code=200, json_data=ValueError("bad"), text="raw")))
    res2 = client.get_data_from_device(
        device_id="d2",
        field=SyconApiDataFields.TEMPERATURE_CELSIUS,
        start_date="2025-10-03T12:30:00.000Z",
        end_date="2025-10-03T13:30:00.000Z",
        head_limit=1,
    )
    assert res2 is None


def test_get_data_from_devices_collects_each_body(monkeypatch):
    c = SyconApi(username="u", password="p")
    monkeypatch.setattr(SyconApi, "_manage_token", lambda self: None)

    def fake_get(headers, url, args=None):
        if "/a/" in url:
            return FakeResponse(status_code=200, json_data={"v": 1})
        return FakeResponse(status_code=200, json_data=ValueError("bad"), text="raw-b")

    call_count = {"n": 0}
    def counting_fake_get(headers, url, args=None):
        call_count["n"] += 1
        return fake_get(headers, url, args)

    monkeypatch.setattr(SyconApi, "_get_request", staticmethod(counting_fake_get))

    devices = ("a", "b")
    res = c.get_data_from_devices(
        devices_id=devices,
        field=SyconApiDataFields.TEMPERATURE_CELSIUS,
        start_date="2025-10-03T12:30:00.000Z",
        end_date="2025-10-03T13:30:00.000Z",
        head_limit=2,
    )
    assert res["a"] == {"v": 1}
    assert res["b"] == "raw-b"
    assert call_count["n"] == 2

    res2 = c.get_data_from_devices(
        devices_id=devices,
        field=SyconApiDataFields.TEMPERATURE_CELSIUS,
        start_date="2025-10-03T12:30:00.000Z",
        end_date="2025-10-03T13:30:00.000Z",
        head_limit=2,
    )
    assert call_count["n"] == 2 


def test_get_data_from_all_devices_skips_missing_id(monkeypatch, client):
    monkeypatch.setattr(SyconApi, "get_devices_list", lambda self: [{"foo": "bar"}, {"id": "d1"}])
    monkeypatch.setattr(SyconApi, "_get_request", staticmethod(lambda headers, url, args=None: FakeResponse(status_code=200, json_data={"v": 1}) if "d1" in url else FakeResponse(status_code=200, json_data=ValueError("bad"), text="raw")))
    res = client.get_data_from_all_devices(
        field=SyconApiDataFields.TEMPERATURE_CELSIUS,
        start_date="2025-10-03T12:30:00.000Z",
        end_date="2025-10-03T13:30:00.000Z",
        head_limit=1,
    )
    assert "d1" in res
    assert "foo" not in res 
