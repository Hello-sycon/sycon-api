from typing import Dict, Tuple, Any, Optional
import requests
from enum import Enum
import logging
import re
from json import dumps
from functools import lru_cache
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)


class SyconApiInvalidParametersException(Exception):
    pass


class SyconApiMissingParametersException(Exception):
    pass


class SyconApiBadResponseException(Exception):
    pass


class SyconApiServerErrorResponseException(Exception):
    pass


class SyconApi:
    k_size_batch_limit: int = 10000

    class SyconApiV1Route(Enum):
        LOGIN = "/auth/login"
        RENEW = "/auth/renew"
        CHECK = "/auth/check"
        DEVICES = "/api/devices"
        DATA = "/api/devices/{deviceId}/{field}/data/raw"

    class SyconApiDataFields(Enum):
        ACCELERATION_X_MS2 = "ACCELERATION_X_MS2"
        ACCELERATION_Y_MS2 = "ACCELERATION_Y_MS2"
        ACCELERATION_Z_MS2 = "ACCELERATION_Z_MS2"
        ACCELERATION_MAG_MAX_MS2 = "ACCELERATION_MAG_MAX_MS2"
        ACCELERATION_MAG_MEAN_MS2 = "ACCELERATION_MAG_MEAN_MS2"
        ACCELERATION_MAG_VARIANCE_MS2 = "ACCELERATION_MAG_VARIANCE_MS2"
        AIR_QUALITY_INDEX = "AIR_QUALITY_INDEX"
        CO2_PPM = "CO2_PPM"
        HUMIDITY_PERCENT = "HUMIDITY_PERCENT"
        PRESSURE_HPA = "PRESSURE_HPA"
        TEMPERATURE_CELSIUS = "TEMPERATURE_CELSIUS"
        VOLATILE_ORGANIC_COMPOUND_PPM = "VOLATILE_ORGANIC_COMPOUND_PPM"
        EXT_CURRENT_AMP = "EXT_CURRENT_AMP"
        EXT_ELECTRICAL_POWER_WATT = "EXT_ELECTRICAL_POWER_WATT"
        EXT_TEMPERATURE_CELSIUS = "EXT_TEMPERATURE_CELSIUS"
        EXT_VOLTAGE_VOLT = "EXT_VOLTAGE_VOLT"
        EXT_HUMIDITY_PERCENT = "EXT_HUMIDITY_PERCENT"

    class SyconApiLogLevel(Enum):
        CRITICAL = 50
        FATAL = CRITICAL
        ERROR = 40
        WARNING = 30
        WARN = WARNING
        INFO = 20
        DEBUG = 10

    def __init__(
        self,
        username: str,
        password: str,
        debug: bool = False,
        debug_level: int = SyconApiLogLevel.DEBUG.value,
    ) -> None:
        self._username: str = username
        self._password: str = password
        self._token: Optional[str] = None
        self._logger: Optional[logging.Logger] = None
        self._server: str = "https://cloud.sycon.io"
        if debug:
            self._configure_logger(debug_lvl=debug_level)

    @property
    def username(self) -> str:
        return self._username

    @property
    def token(self) -> str:
        return self._token

    def _configure_logger(self, debug_lvl: int) -> None:
        logging.basicConfig(
            level=debug_lvl,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        self._logger = logging.getLogger("SyconApi")
        self._logger.setLevel(debug_lvl)

    @staticmethod
    def _format_header_token(token: str, headers: Dict[str, Any]) -> None:
        headers["Authorization"] = f"Bearer {token}"

    @staticmethod
    def _format_header_content_type_json(headers: Dict[str, Any]) -> None:
        headers["Content-type"] = "application/json"

    def _raise_on_threshold_presence(
        self, head_limit: Optional[int], tail_limit: Optional[int]
    ) -> None:
        """raise SyconApiInvalidParametersException if head or tail limit are bad precised
        @param headLimit: [Optional] the limit of values to return from the start (<= 10000)
        @param tailLimit: [Optional] the limit of values to return from the end (<= 10000)
        """
        if head_limit is None and tail_limit is None:
            if self._logger is not None:
                self._logger.critical("Either headLimit or tailLimit field is required")
            raise SyconApiMissingParametersException(
                "Either headLimit or tailLimit field is required"
            )

        if head_limit is not None and tail_limit is not None:
            if self._logger is not None:
                self._logger.critical(
                    "Either headLimit or tailLimit field is required, not both"
                )
            raise SyconApiInvalidParametersException(
                "Either headLimit or tailLimit field is required, not both"
            )

    def _raise_on_date_ISO_8601_bad_format(self, date: str) -> None:
        """raise SyconApiInvalidParametersException if date is incorrect
        @param data : ISO-8601 format
        """
        iso_instant_re: str = re.compile(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z$"
        )
        if not iso_instant_re.fullmatch(date):
            if self._logger is not None:
                self._logger.critical(
                    "date is not well formatted, use ISO-8601 instant format: YYYY-MM-DDTHH:MM:SS[.MS]Z"
                )
            raise SyconApiInvalidParametersException(
                f"date is not well formatted, use ISO-8601 instant format: YYYY-MM-DDTHH:MM:SS[.MS]Z"
            )

    def _fill_get_data_args(
        self,
        args: Dict[str, Any],
        start_date: str,
        end_date: str,
        head_limit: Optional[int] = None,
        tail_limit: Optional[int] = None,
        external_sensor_id: Optional[str] = None,
    ) -> None:
        """fill args by arguments
        @param args: dict to fill
        @param start_date: beginning date for data range (ISO-8601)
        @param end_date: End date for data range (ISO-8601)
        @param head_limit: [Optional] the limit of values to return from the start (<= 10000)
        @param tail_limit: [Optional] the limit of values to return from the end (<= 10000)
        @param external_sensor_id: [Optional] external sensor identifier
        """
        args["start"] = start_date
        args["end"] = end_date

        if head_limit is not None:
            if head_limit > SyconApi.k_size_batch_limit:
                if self._logger is not None:
                    self._logger.warning(
                        f"headLimit exceed max {SyconApi.k_size_batch_limit} value, force request to {SyconApi.k_size_batch_limit}"
                    )
                head_limit = SyconApi.k_size_batch_limit
            args["headLimit"] = head_limit

        if tail_limit is not None:
            if tail_limit > SyconApi.k_size_batch_limit:
                if self._logger is not None:
                    self._logger.warning(
                        f"tailLimit exceed max {SyconApi.k_size_batch_limit} value, force request to {SyconApi.k_size_batch_limit}"
                    )
                tail_limit = SyconApi.k_size_batch_limit
            args["tailLimit"] = tail_limit

        if external_sensor_id is not None:
            args["externalSensorId"] = external_sensor_id

    def _manage_token(self) -> None:
        """Manage token to add in request"""
        if self._token is not None:
            if not self.check_token():
                self.renew_token()
                if self._logger is not None:
                    self._logger.info("Token has been be renewed")
            else:
                if self._logger is not None:
                    self._logger.info("Token is still valid")
        else:
            self.authenticate()
            if self._logger is not None:
                self._logger.info("Token has been attributes")

    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=15),
        retry=retry_if_exception_type(SyconApiServerErrorResponseException),
    )
    def _get_request(
        headers: Dict[str, str], url: str, args: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """Send get request to Tele2Iot server depending on attributes
        @param token: user token
        @param url: url for request
        @param args: query arguments
        @return http Code, body(json)
        """
        rep: requests.Response = requests.get(
            url=url, params=args, headers=headers, timeout=30
        )

        if rep.status_code >= 500 and rep.status_code < 600:
            raise SyconApiServerErrorResponseException(
                f"Server error {rep.status_code} : {rep.text}"
            )

        if rep.status_code >= 400 and rep.status_code < 500:
            raise SyconApiBadResponseException(
                f"Invalid response from server {rep.status_code} : {rep.text}"
            )

        return rep

    @staticmethod
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=15),
        retry=retry_if_exception_type(SyconApiServerErrorResponseException),
    )
    def _post_request(
        headers: Dict[str, str], url: str, data: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        """send a put request to url with specified data
        @param headers: headers to request
        @param: url: url
        @param data: data to send
        @return error code| body"""
        rep: requests.Response = requests.post(
            url=url, headers=headers, data=dumps(data), timeout=30
        )

        if rep.status_code >= 500 and rep.status_code < 600:
            raise SyconApiServerErrorResponseException(
                f"Server error {rep.status_code} : {rep.text}"
            )

        if rep.status_code >= 400 and rep.status_code < 500:
            raise SyconApiBadResponseException(
                f"Invalid response from server {rep.status_code} : {rep.text}"
            )

        return rep

    def authenticate(self) -> bool:
        """authenticates to Sycon cloud by using username/password
        @return True if authentication is success, False otherwise
        """
        url: str = f"{self._server}{SyconApi.SyconApiV1Route.LOGIN.value}"
        body: Dict[str, Any] = {"username": self._username, "password": self._password}
        headers: Dict[str, Any] = {}
        SyconApi._format_header_content_type_json(headers=headers)

        response: requests.Response = self._post_request(
            headers=headers, url=url, data=body
        )

        if self._logger is not None:
            self._logger.debug(
                f"Receive response from auth login with status code {response.status_code} | headers : {response.headers} | body : {response.text}"
            )

        if response.status_code == 200:
            self._token = response.headers.get("Authorization")

    def renew_token(self) -> bool:
        """renew the token to authenticate to Sycon cloud
        @return True if authentication is success, False otherwise
        """
        url: str = f"{self._server}{SyconApi.SyconApiV1Route.RENEW.value}"
        headers: Dict[str, Any] = {}
        SyconApi._format_header_token(token=self._token, headers=headers)
        response: requests.Response = self._get_request(headers=headers, url=url)

        if self._logger is not None:
            self._logger.debug(
                f"Receive response from auth renew with status code {response.status_code} | headers : {response.headers} | body : {response.text}"
            )

        if response.status_code == 200:
            if not "Authorization" in response.headers:
                raise SyconApiBadResponseException(
                    "Authorization token not in received response"
                )
            self._token = response.headers.get("Authorization")

    def check_token(self) -> bool:
        """check the token validity to authenticate to Sycon cloud
        @return True if token still valid, False otherwise
        """
        url: str = f"{self._server}{SyconApi.SyconApiV1Route.CHECK.value}"
        headers: Dict[str, Any] = {}
        SyconApi._format_header_token(token=self._token, headers=headers)
        response: requests.Response = self._get_request(headers=headers, url=url)

        if self._logger is not None:
            self._logger.debug(
                f"Receive response from auth check with status code {response.status_code} | headers : {response.headers} | body : {response.text}"
            )

        return bool(response.status_code == 200)

    def get_devices_list(self) -> Optional[Dict[str, Any]]:
        """Get the devices list associate to customer user
        @return device list if exists, None otherwise
        """
        url: str = f"{self._server}{SyconApi.SyconApiV1Route.DEVICES.value}"
        self._manage_token()

        headers: Dict[str, Any] = {}
        SyconApi._format_header_token(token=self._token, headers=headers)
        response: requests.Response = SyconApi._get_request(headers=headers, url=url)

        if self._logger:
            self._logger.debug(
                f"Receive response from data devices with status code {response.status_code} | headers : {response.headers} | body : {response.text}"
            )

        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                raise SyconApiBadResponseException(
                    f"Invalid response received from server for request {url}"
                )

    @lru_cache(maxsize=10)
    def get_data_from_device(
        self,
        device_id: str,
        field: SyconApiDataFields,
        start_date: str,
        end_date: str,
        head_limit: Optional[int] = None,
        tail_limit: Optional[int] = None,
        external_sensor_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """@brief Get data produces between start and end time for precised field about device identifier
        @param device_id: device identifier
        @param field: data field to retrieve:
            - ACCELERATION_X_MS2
            - ACCELERATION_Y_MS2
            - ACCELERATION_Z_MS2
            - ACCELERATION_MAG_MAX_MS2
            - ACCELERATION_MAG_MEAN_MS2
            - ACCELERATION_MAG_VARIANCE_MS2
            - AIR_QUALITY_INDEX
            - CO2_PPM
            - HUMIDITY_PERCENT
            - PRESSURE_HPA
            - TEMPERATURE_CELSIUS
            - VOLATILE_ORGANIC_COMPOUND_PPM
            - EXT_CURRENT_AMP
            - EXT_ELECTRICAL_POWER_WATT
            - EXT_TEMPERATURE_CELSIUS
            - EXT_VOLTAGE_VOLT
            - EXT_HUMIDITY_PERCENT
        @param start_date: beginning date for data range (ISO-8601)
        @param end_date: End date for data range (ISO-8601)
        @param head_limit: [Optional] the limit of values to return from the start (<= 10000)
        @param tail_limit: [Optional] the limit of values to return from the end (<= 10000)
        @param external_sensor_id: [Optional] external sensor identifier
        @note either head_limit or tail_limit must be used
        """
        args: Dict[str, Any] = {}

        self._raise_on_threshold_presence(head_limit, tail_limit)
        self._raise_on_date_ISO_8601_bad_format(start_date)
        self._raise_on_date_ISO_8601_bad_format(end_date)

        self._fill_get_data_args(
            args=args,
            end_date=end_date,
            start_date=start_date,
            head_limit=head_limit,
            tail_limit=tail_limit,
            external_sensor_id=external_sensor_id,
        )
        self._manage_token()

        headers: Dict[str, Any] = {}
        SyconApi._format_header_token(token=self._token, headers=headers)
        url: str = (
            f"{self._server}{SyconApi.SyconApiV1Route.DATA.value.format(deviceId=device_id, field=field.value)}"
        )

        response: requests.Response = SyconApi._get_request(
            headers=headers, url=url, args=args
        )

        try:
            body: Dict[str, Any] | str = response.json()
        except ValueError:
            body = response.text

        if self._logger is not None:
            self._logger.debug(
                f"Receive code : {response.status_code} | body : {body} | from request : {url} | with parameters : {args}"
            )

        return body if isinstance(body, Dict) else None

    @lru_cache(maxsize=10)
    def get_data_from_devices(
        self,
        devices_id: Tuple[str],
        field: SyconApiDataFields,
        start_date: str,
        end_date: str,
        head_limit: Optional[int] = None,
        tail_limit: Optional[int] = None,
        external_sensor_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """@brief Get data produces between start and end time for precised field about device identifier
        @param devices_id: list of device identifier
        @param field: data field to retrieve:
            - ACCELERATION_X_MS2
            - ACCELERATION_Y_MS2
            - ACCELERATION_Z_MS2
            - ACCELERATION_MAG_MAX_MS2
            - ACCELERATION_MAG_MEAN_MS2
            - ACCELERATION_MAG_VARIANCE_MS2
            - AIR_QUALITY_INDEX
            - CO2_PPM
            - HUMIDITY_PERCENT
            - PRESSURE_HPA
            - TEMPERATURE_CELSIUS
            - VOLATILE_ORGANIC_COMPOUND_PPM
            - EXT_CURRENT_AMP
            - EXT_ELECTRICAL_POWER_WATT
            - EXT_TEMPERATURE_CELSIUS
            - EXT_VOLTAGE_VOLT
            - EXT_HUMIDITY_PERCENT
        @param start_date: beginning date for data range (ISO-8601)
        @param end_date: End date for data range (ISO-8601)
        @param head_limit: [Optional] the limit of values to return from the start (<= 10000)
        @param tail_limit: [Optional] the limit of values to return from the end (<= 10000)
        @param external_sensor_id: [Optional] external sensor identifier
        @note either head_limit or tail_limit must be used
        """
        args: Dict[str, Any] = {}
        data: Dict[str, Any] = {}

        self._raise_on_threshold_presence(head_limit, tail_limit)
        self._raise_on_date_ISO_8601_bad_format(start_date)
        self._raise_on_date_ISO_8601_bad_format(end_date)

        self._fill_get_data_args(
            args=args,
            end_date=end_date,
            start_date=start_date,
            head_limit=head_limit,
            tail_limit=tail_limit,
            external_sensor_id=external_sensor_id,
        )
        self._manage_token()

        for device_id in devices_id:
            headers: Dict[str, Any] = {}
            SyconApi._format_header_token(token=self._token, headers=headers)
            url: str = (
                f"{self._server}{SyconApi.SyconApiV1Route.DATA.value.format(deviceId=device_id, field=field.value)}"
            )

            response: requests.Response = SyconApi._get_request(
                headers=headers, url=url, args=args
            )
            try:
                body: Dict[str, Any] | str = response.json()
            except ValueError:
                body = response.text

            if self._logger is not None:
                self._logger.debug(
                    f"Receive code : {response.status_code} | body : {body} | from request : {url} | with parameters : {args}"
                )

            data[str(device_id)] = body

        return data

    @lru_cache(maxsize=10)
    def get_data_from_all_devices(
        self,
        field: SyconApiDataFields,
        start_date: str,
        end_date: str,
        head_limit: Optional[int] = None,
        tail_limit: Optional[int] = None,
        external_sensor_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """@brief Get data produces between start and end time for precised field about device identifier
        @param devices_id: list of device identifier
        @param field: data field to retrieve:
            - ACCELERATION_X_MS2
            - ACCELERATION_Y_MS2
            - ACCELERATION_Z_MS2
            - ACCELERATION_MAG_MAX_MS2
            - ACCELERATION_MAG_MEAN_MS2
            - ACCELERATION_MAG_VARIANCE_MS2
            - AIR_QUALITY_INDEX
            - CO2_PPM
            - HUMIDITY_PERCENT
            - PRESSURE_HPA
            - TEMPERATURE_CELSIUS
            - VOLATILE_ORGANIC_COMPOUND_PPM
            - EXT_CURRENT_AMP
            - EXT_ELECTRICAL_POWER_WATT
            - EXT_TEMPERATURE_CELSIUS
            - EXT_VOLTAGE_VOLT
            - EXT_HUMIDITY_PERCENT
        @param start_date: beginning date for data range (ISO-8601)
        @param end_date: End date for data range (ISO-8601)
        @param head_limit: [Optional] the limit of values to return from the start (<= 10000)
        @param tail_limit: [Optional] the limit of values to return from the end (<= 10000)
        @param external_sensor_id: [Optional] external sensor identifier
        @note either head_limit or tail_limit must be used
        """
        args: Dict[str, Any] = {}
        data: Dict[str, Any] = {}

        self._raise_on_threshold_presence(head_limit, tail_limit)
        self._raise_on_date_ISO_8601_bad_format(start_date)
        self._raise_on_date_ISO_8601_bad_format(end_date)

        self._fill_get_data_args(
            args=args,
            end_date=end_date,
            start_date=start_date,
            head_limit=head_limit,
            tail_limit=tail_limit,
            external_sensor_id=external_sensor_id,
        )
        self._manage_token()

        devices: Dict[str, Any] = self.get_devices_list()
        for device in devices:
            if not "id" in device:
                continue

            device_id: str = device.get("id")
            headers: Dict[str, Any] = {}
            SyconApi._format_header_token(token=self._token, headers=headers)
            url: str = (
                f"{self._server}{SyconApi.SyconApiV1Route.DATA.value.format(deviceId=device_id, field=field.value)}"
            )

            response: requests.Response = SyconApi._get_request(
                headers=headers, url=url, args=args
            )

            try:
                body: Dict[str, Any] | str = response.json()
            except ValueError:
                body = response.text

            if self._logger is not None:
                self._logger.debug(
                    f"Receive code : {response.status_code} | body : {body} | from request : {url} | with parameters : {args}"
                )

            data[str(device_id)] = body

        return data
     