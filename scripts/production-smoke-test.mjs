const baseUrl = (process.env.PRODUCTION_URL || "https://crediclass.csrtecnologia.com.br").replace(/\/$/, "");
const expectedVersion = process.env.EXPECTED_VERSION || "4.0.90";

async function get(path) {
  const response = await fetch(`${baseUrl}${path}`, { redirect: "follow" });
  const body = await response.text();
  if (!response.ok) throw new Error(`${path}: HTTP ${response.status}: ${body.slice(0, 300)}`);
  return { response, body };
}

const health = await get("/api/health");
const index = await get("/");
const app = await get(`/static/js/app.js?v=${expectedVersion}`);
const api = await get(`/static/js/api.js?v=${expectedVersion}`);

const checks = [
  ["health", health.body.includes("ok") || health.body.includes("healthy")],
  ["version marker", index.body.includes(expectedVersion)],
  ["embedded editor bundle", app.body.includes("data-embedded-study-editor") && app.body.includes("study_financial")],
  ["API bundle", api.body.length > 1000],
];
const failed = checks.filter(([, ok]) => !ok);
for (const [name, ok] of checks) console.log(`${ok ? "PASS" : "FAIL"} ${name}`);
if (failed.length) process.exit(1);
console.log(`Production smoke test passed: ${baseUrl} (${expectedVersion})`);
