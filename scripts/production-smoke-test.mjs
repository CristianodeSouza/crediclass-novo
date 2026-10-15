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
  ["financial study fixed introduction is served", index.body.includes("financial-study-part--introduction") && index.body.includes("ESTUDO FINANCEIRO") && index.body.includes("crediclass-logo.png") && app.body.includes("clearRetiredFinancialStudyState") && !app.body.includes("renderEmptyFinancialStudyScreen")],
  ["financial study hypothetical investment part is served", index.body.includes('data-study-part-name="Simulação de Investimento"') && index.body.includes("SIMULAÇÃO DE INVESTIMENTO") && index.body.includes("Exemplo hipotético reproduzido do HTML de referência") && index.body.includes("-R$ 4.708.694,53")],
  ["financial study best consortia part and selected administrator binding are served", index.body.includes('data-study-part-name="Simulação dos melhores consórcios"') && index.body.includes("SIMULAÇÃO DOS MELHORES CONSÓRCIOS") && index.body.includes("Critérios de seleção:") && app.body.includes("renderFinancialStudySelectedAdministrator")],
  ["financial study Quadro Resumo Motor composition and hypothetical investment values are served", index.body.includes('data-study-part-name="Quadro Resumo"') && index.body.includes("SIMULAÇÃO INVESTIMENTOS") && index.body.includes("R$ 6.726.706,47") && index.body.includes("Valores hipotéticos do HTML de referência") && app.body.includes("renderFinancialStudySummary") && app.body.includes("selectedCompositionScenarioMetrics(items, id)")],
  ["financial study Especialistas da Jornada fixed section is served", index.body.includes('data-study-part-name="Especialistas da Jornada"') && index.body.includes("ESPECIALISTAS EM TODA JORNADA") && index.body.includes("Gestão da Contemplação:") && index.body.includes("Gestão da Utilização do Crédito:")],
  ["financial study administrator-specific benefits part is served", index.body.includes('data-study-part-name="Principais Benefícios Itaú"') && index.body.includes("PRINCIPAIS BENEFÍCIOS") && !index.body.slice(index.body.indexOf('data-study-part="6"'), index.body.indexOf("</section>", index.body.indexOf('data-study-part="6"'))).includes("<img") && app.body.includes("renderFinancialStudyBenefits") && app.body.includes("FINANCIAL_STUDY_ADMINISTRATOR_BENEFITS")],
  ["financial study contracting part uses selected Motor data and group averages", index.body.includes('data-study-part-name="Contratação"') && app.body.includes("Parcelas (sem seguro)") && app.body.includes("renderFinancialStudyContracting") && app.body.includes("selectedScenarioIdsForGroup(groupKey)") && app.body.includes('average("term")') && app.body.includes('average("adminRate")') && app.body.includes('average("annualRate")')],
  ["financial study fixed contemplation strategies part is served", index.body.includes('data-study-part-name="Estratégias de contemplação"') && index.body.includes("ESTRATÉGIAS DE CONTEMPLAÇÃO") && index.body.includes("Estratégia 1) Investidor") && index.body.includes("Estratégia 2) Conservadora") && index.body.includes("Estratégia 3) Moderada") && index.body.includes("não havendo garantia de contemplação")],
  ["Motor 360 card renderer", app.body.includes("renderMotor360GroupCardUncached") && app.body.includes("motor360BidSortLabel")],
  ["API bundle", api.body.length > 1000],
];
const failed = checks.filter(([, ok]) => !ok);
for (const [name, ok] of checks) console.log(`${ok ? "PASS" : "FAIL"} ${name}`);
if (failed.length) process.exit(1);
console.log(`Production smoke test passed: ${baseUrl} (${expectedVersion})`);
