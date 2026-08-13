const API_BASE = "/api";

async function apiRequest(path, options = {}) {
  const { timeoutMs = 0, ...fetchOptions } = options;
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

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = data.error || data.detail || "Erro ao comunicar com o servidor";
    if (response.status === 401 && typeof showLogin === "function") {
      showLogin(message);
    }
    showToast(message, "danger");
    throw new Error(message);
  }

  return data;
}

function apiGet(path, options = {}) {
  return apiRequest(path, options);
}

function apiPost(path, payload) {
  return apiRequest(path, {
    method: "POST",
    body: JSON.stringify(payload || {}),
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
