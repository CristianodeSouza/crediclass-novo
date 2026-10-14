const baseUrl = (process.env.PRODUCTION_URL || "https://crediclass.csrtecnologia.com.br").replace(/\/$/, "");
const expectedVersionOverride = process.env.EXPECTED_VERSION;

async function get(path) {
  const response = await fetch(`${baseUrl}${path}`, { redirect: "follow" });
  const body = await response.text();
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}: ${body.slice(0, 300)}`);
  return { response, body };
}

const health = await get("/api/health");
let healthData;
try {
  healthData = JSON.parse(health.body);
} catch {
  throw new Error(`/api/health returned invalid JSON: ${health.body.slice(0, 300)}`);
}
const expectedVersion = expectedVersionOverride || healthData.version;
if (!expectedVersion) throw new Error("Production health response does not include a version");
const index = await get("/");
const app = await get(`/static/js/app.js?v=${expectedVersion}`);
const api = await get(`/static/js/api.js?v=${expectedVersion}`);

const checks = [
  ["health status", healthData.status === "ok" || healthData.status === "healthy"],
  ["health version", healthData.version === expectedVersion],
  ["version marker", index.body.includes(expectedVersion)],
  ["versioned app asset reference", new RegExp(`/static/js/app\\.js\\?v=${expectedVersion.replaceAll(".", "\\.")}`).test(index.body)],
  ["versioned API asset reference", new RegExp(`/static/js/api\\.js\\?v=${expectedVersion.replaceAll(".", "\\.")}`).test(index.body)],
  ["embedded editor bundle", app.body.includes("data-embedded-study-editor") && app.body.includes("study_financial")],
  ["Motor 360 card renderer", app.body.includes("renderMotor360GroupCardUncached") && app.body.includes("motor360BidSortLabel")],
  ["API bundle", api.body.length > 1000],
];
const failed = checks.filter(([, ok]) => !ok);
for (const [name, ok] of checks) console.log(`${ok ? "PASS" : "FAIL"} ${name}`);
if (failed.length) process.exit(1);
console.log(`Production smoke test passed: ${baseUrl} (${expectedVersion})`);
