# Sycon cloud API release notes

Release notes of the API documented on [cloud.sycon.io/swagger-ui](https://cloud.sycon.io/swagger-ui/index.html#/).

### 1.2.0 - 07/04/2024

Adding `EXT_HUMIDITY_PERCENT` and `EXT_REF_VOLTAGE_VOLT` values to `ESyconFieldType` enum.

### 1.1.0 - 18/03/2025

Starting using semver version numbers.

`/api/devices` endpoint :

- added the field `externalSensorIds` to the returned `SyconDevice` objects ; values are read in recent data
- now reading `fields` values of returned `SyconDevice` in recent data (and documentation of the field)
- added the field `customerId` to the returned `SyconDevice` objects

`/api/devices/{deviceId}/{field}/data/raw` endpoint :

- reminding the requested `externalSensorId` in the returned `SyconFieldData` object

### v1

First published version with endpoints to:

- list devices of the user
- retrieve data by device, time, field