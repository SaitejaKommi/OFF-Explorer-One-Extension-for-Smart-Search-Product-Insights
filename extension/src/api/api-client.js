/**
 * api-client.js
 * Thin fetch wrapper for the FastAPI backend.
 * All requests include session_id for conversational continuity.
 */

const BASE_URL = "http://localhost:8000";

/**
 * POST /search
 * @param {string} query
 * @param {string|null} sessionId
 * @param {string} language  "en" | "fr"
 * @param {number} limit
 */
export async function search(query, sessionId = null, language = "en", limit = 20) {
  const resp = await fetch(`${BASE_URL}/search`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId, language, limit }),
  });
  if (!resp.ok) throw new Error(`Search failed: ${resp.status}`);
  return resp.json();
}

/**
 * POST /refine
 * @param {string} refinement
 * @param {string} sessionId
 * @param {number} limit
 */
export async function refine(refinement, sessionId, limit = 20) {
  const resp = await fetch(`${BASE_URL}/refine`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ refinement, session_id: sessionId, limit }),
  });
  if (!resp.ok) throw new Error(`Refine failed: ${resp.status}`);
  return resp.json();
}

/**
 * POST /product-insights
 * @param {string} barcode
 * @param {string|null} sessionId
 * @param {string} language
 */
export async function productInsights(barcode, sessionId = null, language = "en") {
  const resp = await fetch(`${BASE_URL}/product-insights`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ barcode, session_id: sessionId, language }),
  });
  if (!resp.ok) throw new Error(`Insights failed: ${resp.status}`);
  return resp.json();
}

/**
 * GET /health – check if the backend is reachable
 */
export async function healthCheck() {
  try {
    const resp = await fetch(`${BASE_URL}/health`, { method: "GET" });
    return resp.ok;
  } catch {
    return false;
  }
}
