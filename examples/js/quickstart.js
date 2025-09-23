// Run with: node examples/js/quickstart.js
// Requires Node 18+ (global fetch)

const BASE_URL = "https://cloud.sycon.io";
const USERNAME = process.env.SYCON_USERNAME || "your_username";
const PASSWORD = process.env.SYCON_PASSWORD || "your_password";

const DEVICE_ID = 12345; // replace with your own
const FIELD = "TEMPERATURE_CELSIUS"; // see enum in OpenAPI

function iso(dt) {
  return dt.toISOString().replace(/\.\d{3}Z$/, "Z");
}

async function login() {
  const r = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: USERNAME, password: PASSWORD }),
  });
  if (!r.ok) {
    const body = await r.text();
    throw new Error(`Login failed: ${r.status} ${body}`);
  }
  const auth = r.headers.get("Authorization") || "";
  const renew = r.headers.get("Renew") || "";
  if (!auth || !renew) {
    throw new Error("Missing Authorization/Renew headers");
  }
  const jwt = auth.startsWith("Bearer ") ? auth.slice(7) : auth;
  return { jwt, renew };
}

async function authCheck(jwt) {
  const r = await fetch(`${BASE_URL}/auth/check`, {
    headers: { Authorization: `Bearer ${jwt}` },
  });
  console.log("auth/check:", r.status);
}

async function listDevices(jwt) {
  const r = await fetch(`${BASE_URL}/api/devices`, {
    headers: { Authorization: `Bearer ${jwt}`, Accept: "application/json" },
  });
  if (!r.ok) throw new Error(`devices failed: ${r.status}`);
  return r.json();
}

async function getRaw(jwt, deviceId, field, start, end, tailLimit = 1000, externalSensorId) {
  const url = new URL(`${BASE_URL}/api/devices/${deviceId}/${field}/data/raw`);
  url.searchParams.set("start", start);
  url.searchParams.set("end", end);
  url.searchParams.set("tailLimit", String(tailLimit));
  if (externalSensorId) url.searchParams.set("externalSensorId", externalSensorId);

  const r = await fetch(url, {
    headers: { Authorization: `Bearer ${jwt}`, Accept: "application/json" },
  });
  console.log("raw data:", r.status);
  if (!r.ok) throw new Error(`raw data failed: ${r.status}`);
  return r.json();
}

async function renewJwt(renewToken) {
  const r = await fetch(`${BASE_URL}/auth/renew`, {
    headers: { Renew: renewToken },
  });
  if (r.ok) {
    const auth = r.headers.get("Authorization") || "";
    return auth.startsWith("Bearer ") ? auth.slice(7) : auth;
  }
  console.warn("Renew failed:", r.status);
  return null;
}

(async () => {
  const { jwt, renew } = await login();
  await authCheck(jwt);

  const devices = await listDevices(jwt);
  console.log("Devices (first):", devices[0], "total:", Array.isArray(devices) ? devices.length : 0);

  // Last 24h window
  const end = new Date();
  const start = new Date(end.getTime() - 24 * 60 * 60 * 1000);
  const data = await getRaw(jwt, DEVICE_ID, FIELD, iso(start), iso(end), 1000);
  console.log("Data count:", data.count, "First:", data.firstTimestamp, "Last:", data.lastTimestamp);

  const newJwt = await renewJwt(renew);
  if (newJwt) console.log("JWT renewed (len):", newJwt.length);
})().catch(err => {
  console.error(err);
  process.exit(1);
});
