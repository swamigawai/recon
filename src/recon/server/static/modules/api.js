/**
 * Recon Client API Engine (modules/api.js)
 * Clean, centralized fetch wrapper with automatic authentication headers and response parsing.
 */

export function getAuthHeaders() {
  const token = localStorage.getItem("recon_pilot_api_key") || "";
  const headers = {};
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
    headers["X-Recon-Key"] = token;
  }
  return headers;
}

export async function apiRequest(endpoint, options = {}) {
  const defaultHeaders = getAuthHeaders();
  const headers = { ...defaultHeaders, ...(options.headers || {}) };

  const response = await fetch(endpoint, {
    ...options,
    headers,
  });

  if (!response.ok) {
    let errDetail = `HTTP ${response.status} ${response.statusText}`;
    try {
      const data = await response.json();
      if (data && data.detail) {
        errDetail = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
      }
    } catch (_) {}
    throw new Error(errDetail);
  }

  return response;
}

export async function apiGetJson(endpoint) {
  const res = await apiRequest(endpoint);
  return res.json();
}

export async function apiPostJson(endpoint, body) {
  const res = await apiRequest(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return res.json();
}
