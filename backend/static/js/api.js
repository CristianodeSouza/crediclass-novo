const API_BASE = "/api";

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const data = await response.json().catch(() => ({}));

  if (!response.ok) {
    const message = data.error || data.detail || "Erro ao comunicar com o servidor";
    showToast(message, "danger");
    throw new Error(message);
  }

  return data;
}

function apiGet(path) {
  return apiRequest(path);
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
