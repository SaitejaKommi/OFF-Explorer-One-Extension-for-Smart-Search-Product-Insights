/**
 * popup.js – Search Mode UI controller
 *
 * Handles:
 *  - Search query submission
 *  - Conversational refinement
 *  - Session management via background service worker
 *  - Backend health check on open
 */

import { search, refine, healthCheck } from "../api/api-client.js";

// -------------------------------------------------------------------------
// State
// -------------------------------------------------------------------------
let sessionId = null;
let language = "en";
let lastResults = [];

// -------------------------------------------------------------------------
// DOM references
// -------------------------------------------------------------------------
const searchInput = document.getElementById("search-input");
const searchBtn = document.getElementById("search-btn");
const refineInput = document.getElementById("refine-input");
const refineBtn = document.getElementById("refine-btn");
const resultsList = document.getElementById("results-list");
const resultsSection = document.getElementById("results-section");
const resultsCount = document.getElementById("results-count");
const relaxationNotice = document.getElementById("relaxation-notice");
const refineSection = document.getElementById("refine-section");
const loadingEl = document.getElementById("loading");
const errorEl = document.getElementById("error-msg");
const clearBtn = document.getElementById("clear-btn");
const backendStatusBanner = document.getElementById("backend-status");

// -------------------------------------------------------------------------
// Helpers
// -------------------------------------------------------------------------

function showLoading(show) {
  loadingEl.classList.toggle("hidden", !show);
  searchBtn.disabled = show;
  refineBtn.disabled = show;
}

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.classList.remove("hidden");
}

function clearError() {
  errorEl.classList.add("hidden");
  errorEl.textContent = "";
}

function nsGradeColor(grade) {
  const colors = { a: "#038141", b: "#85BB2F", c: "#FFCC00", d: "#EE8100", e: "#E63312" };
  return colors[(grade || "").toLowerCase()] || "#ccc";
}

function renderResults(data) {
  clearError();
  lastResults = data.results || [];
  sessionId = data.session_id;

  resultsCount.textContent = `${lastResults.length} result${lastResults.length !== 1 ? "s" : ""}`;

  // Relaxation notice
  if (data.relaxation_applied && data.relaxation_description) {
    relaxationNotice.textContent = `ℹ Constraints relaxed: ${data.relaxation_description}`;
    relaxationNotice.classList.remove("hidden");
  } else {
    relaxationNotice.classList.add("hidden");
  }

  resultsList.innerHTML = "";
  if (lastResults.length === 0) {
    resultsList.innerHTML = `<li class="no-results">No products found. Try a broader query.</li>`;
  } else {
    lastResults.forEach((product) => {
      const li = document.createElement("li");
      li.className = "result-item";
      li.setAttribute("role", "listitem");
      li.setAttribute("data-barcode", product.barcode);
      li.style.cursor = "pointer";

      const grade = product.nutriscore_grade || "";
      const nova = product.nova_group ? `NOVA ${product.nova_group}` : "";
      const expKeys = Object.keys(product.explanation || {}).slice(0, 3);
      const expHtml = expKeys
        .map((k) => `<span class="expl-tag">${k.replace(/^.*:/, "")}: ${product.explanation[k]}</span>`)
        .join("");

      li.innerHTML = `
        <div class="result-main">
          <span class="result-name">${escapeHtml(product.product_name)}</span>
          <div class="result-badges">
            ${grade ? `<span class="ns-badge" style="background:${nsGradeColor(grade)}" title="Nutri-Score">${grade.toUpperCase()}</span>` : ""}
            ${nova ? `<span class="nova-badge" title="NOVA group">${nova}</span>` : ""}
          </div>
        </div>
        <div class="result-explanation">${expHtml}</div>
        <a class="result-link" href="https://ca.openfoodfacts.org/product/${product.barcode}" target="_blank">View on OFF ↗</a>
      `;
      
      // Add click handler to show insights
      li.addEventListener("click", (e) => {
        if (e.target.classList.contains("result-link")) return; // Allow link clicks
        window.showProductInsights(product.barcode, sessionId, language);
      });
      
      resultsList.appendChild(li);
    });
  }

  resultsSection.classList.remove("hidden");
  refineSection.classList.remove("hidden");

  // Save session
  chrome.runtime.sendMessage({ type: "SET_SESSION", sessionId });
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str || ""));
  return div.innerHTML;
}

function clearResults() {
  resultsList.innerHTML = "";
  resultsSection.classList.add("hidden");
  refineSection.classList.add("hidden");
  relaxationNotice.classList.add("hidden");
  sessionId = null;
  lastResults = [];
  searchInput.value = "";
  refineInput.value = "";
  chrome.runtime.sendMessage({ type: "CLEAR_SESSION" });
}

// -------------------------------------------------------------------------
// Event handlers
// -------------------------------------------------------------------------

async function handleSearch() {
  const query = searchInput.value.trim();
  if (!query) return;
  showLoading(true);
  clearError();
  try {
    const data = await search(query, null, language);
    renderResults(data);
  } catch (err) {
    showError(`Search failed: ${err.message}`);
  } finally {
    showLoading(false);
  }
}

async function handleRefine() {
  const refinement = refineInput.value.trim();
  if (!refinement || !sessionId) return;
  showLoading(true);
  clearError();
  try {
    const data = await refine(refinement, sessionId);
    renderResults(data);
    refineInput.value = "";
  } catch (err) {
    showError(`Refinement failed: ${err.message}`);
  } finally {
    showLoading(false);
  }
}

searchBtn.addEventListener("click", handleSearch);
searchInput.addEventListener("keydown", (e) => { if (e.key === "Enter") handleSearch(); });
refineBtn.addEventListener("click", handleRefine);
refineInput.addEventListener("keydown", (e) => { if (e.key === "Enter") handleRefine(); });
clearBtn.addEventListener("click", clearResults);

// -------------------------------------------------------------------------
// Init
// -------------------------------------------------------------------------

async function init() {
  // Detect language from active tab
  const tabInfo = await new Promise((resolve) =>
    chrome.runtime.sendMessage({ type: "GET_ACTIVE_TAB_INFO" }, resolve)
  );
  language = tabInfo.language || "en";
  document.documentElement.lang = language;

  // Restore session if any
  const sessionData = await new Promise((resolve) =>
    chrome.runtime.sendMessage({ type: "GET_SESSION" }, resolve)
  );
  if (sessionData.sessionId) sessionId = sessionData.sessionId;

  // Backend health check
  const alive = await healthCheck();
  if (!alive) {
    backendStatusBanner.classList.remove("hidden");
  }
}

init();
