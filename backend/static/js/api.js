const API_BASE = "/api";

async function apiRequest(path, options = {}) {
  const { timeoutMs = 0, suppressErrorToast = false, ...fetchOptions } = options;
  const controller = timeoutMs > 0 && !fetchOptions.signal ? new AbortController() : null;
  const timeoutId = controller ? window.setTimeout(() => controller.abort(), timeoutMs) : null;
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...fetchOptions,
    signal: fetchOptions.signal || controller?.signal,
  }).catch((error) => {
    if (error?.name === "AbortError") {
      throw new Error("O servidor demorou para responder. Tente novamente.");
    }
    throw error;
  }).finally(() => {
    if (timeoutId) window.clearTimeout(timeoutId);
  });

  const rawBody = await response.text();
  let data = {};
  try { data = rawBody ? JSON.parse(rawBody) : {}; } catch { /* respostas HTML/texto também são reportadas abaixo */ }

  if (!response.ok) {
    const responseText = rawBody.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim().slice(0, 240);
    const message = data.error || data.detail || `Erro HTTP ${response.status}: ${responseText || response.statusText || "resposta vazia"}`;
    if (response.status === 401 && typeof showLogin === "function") {
      showLogin(message);
    }
    if (!suppressErrorToast) showToast(message, "danger");
    throw new Error(message);
  }

  return data;
}

function apiGet(path, options = {}) {
  return apiRequest(path, options);
}

function apiPost(path, payload, options = {}) {
  return apiRequest(path, {
    method: "POST",
    body: JSON.stringify(payload || {}),
    ...options,
  });
}

function apiPut(path, payload) {
  return apiRequest(path, {
    method: "PUT",
    body: JSON.stringify(payload || {}),
  });
}

function apiDelete(path) {
  return apiRequest(path, {
    method: "DELETE",
  });
}
