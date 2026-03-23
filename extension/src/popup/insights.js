/**
 * insights.js – Product Insights Panel Controller
 *
 * Handles:
 *  - Fetching product insights from backend
 *  - Rendering insights UI with data
 *  - Navigation between search and insights views
 *  - Error handling and loading states
 */

import { productInsights } from "../api/api-client.js";

// -------------------------------------------------------------------------
// DOM References
// -------------------------------------------------------------------------

const resultsSection = document.getElementById("results-section");
const insightsSection = document.getElementById("insights-section");
const searchSection = document.getElementById("search-section");
const backBtn = document.getElementById("back-to-results");
const loadingEl = document.getElementById("loading");
const errorEl = document.getElementById("error-msg");
const resultsList = document.getElementById("results-list");

// -------------------------------------------------------------------------
// State
// -------------------------------------------------------------------------

let currentSessionId = null;
let currentLanguage = "en";

// -------------------------------------------------------------------------
// API Calls
// -------------------------------------------------------------------------

async function fetchProductInsights(barcode) {
  try {
    const data = await productInsights(barcode, currentSessionId, currentLanguage);
    return data;
  } catch (err) {
    console.error("Failed to fetch insights:", err);
    throw err;
  }
}

// -------------------------------------------------------------------------
// Render Functions
// -------------------------------------------------------------------------

function renderNutriScore(grade) {
  if (!grade) return "";
  const gradeMap = {
    a: { emoji: "A", className: "grade-a" },
    b: { emoji: "B", className: "grade-b" },
    c: { emoji: "C", className: "grade-c" },
    d: { emoji: "D", className: "grade-d" },
    e: { emoji: "E", className: "grade-e" },
  };
  const g = gradeMap[grade.toLowerCase()];
  return g ? `<span class="nutriscore-badge ${g.className}">${g.emoji}</span>` : "";
}

function renderNovaBadge(novaGroup) {
  if (!novaGroup) return "";
  return `<span class="nova-badge">NOVA ${novaGroup}</span>`;
}

function renderPositiveIndicators(indicators) {
  if (!indicators || indicators.length === 0) {
    return `<div class="empty-state"><div class="empty-state-text">No positive indicators available</div></div>`;
  }

  return indicators
    .map(
      (ind) => `
    <div class="indicator-item positive">
      <div class="indicator-icon">✓</div>
      <div class="indicator-content">
        <div class="indicator-label">${escapeHtml(ind.label)}</div>
        <div class="indicator-value">${escapeHtml(ind.value)}</div>
      </div>
    </div>
  `
    )
    .join("");
}

function renderRiskIndicators(indicators) {
  if (!indicators || indicators.length === 0) {
    return `<div class="empty-state"><div class="empty-state-text">No health risks detected</div></div>`;
  }

  return indicators
    .map(
      (ind) => `
    <div class="indicator-item risk">
      <div class="indicator-icon">✕</div>
      <div class="indicator-content">
        <div class="indicator-label">${escapeHtml(ind.label)}</div>
        <div class="indicator-value">${escapeHtml(ind.value)}</div>
        <div class="indicator-level ${ind.level.toLowerCase()}">${ind.level}</div>
      </div>
    </div>
  `
    )
    .join("");
}

function renderPairings(pairings) {
  if (!pairings || pairings.length === 0) {
    return `<div style="font-size: 12px; color: var(--text-secondary); text-align: center; padding: 12px;">No pairing suggestions available</div>`;
  }

  return `
    ${pairings
      .map((pairing) => `<span class="pairing-tag">${escapeHtml(pairing)}</span>`)
      .join("")}
  `;
}

function renderRecommendations(recommendations) {
  if (!recommendations || recommendations.length === 0) {
    return '<li style="font-size: 12px; color: var(--text-secondary); text-align: center;">No recommendations available</li>';
  }

  return recommendations.map((rec) => `<li>${escapeHtml(rec)}</li>`).join("");
}

function renderAlternatives(alternatives) {
  if (!alternatives || alternatives.length === 0) {
    return `<div style="font-size: 12px; color: var(--text-secondary); text-align: center; padding: 12px;">No better alternatives found</div>`;
  }

  return alternatives
    .map((alt, idx) => {
      const scorePercent = Math.min(100, Math.max(0, alt.score * 100));
      const nutriHtml = alt.nutriscore_grade
        ? `<span class="alternative-nutriscore">${alt.nutriscore_grade.toUpperCase()}</span>`
        : "";

      return `
      <div class="alternative-item">
        <span class="alternative-name">${idx + 1}. ${escapeHtml(alt.product_name)}</span>
        <div class="alternative-score">
          <span class="score-bar"><div class="score-fill" style="width: ${scorePercent}%"></div></span>
          <span>${alt.score.toFixed(2)}</span>
          ${nutriHtml}
        </div>
      </div>
    `;
    })
    .join("");
}

function renderInsights(data) {
  // Product Name
  const productNameEl = document.getElementById("insights-product-name");
  productNameEl.textContent = escapeHtml(data.product_name);

  // Badges
  const badgesHtml =
    renderNutriScore(data.nutriscore_grade) + renderNovaBadge(data.nova_group);
  document.getElementById("insights-badges").innerHTML = badgesHtml || '<span style="color: var(--text-secondary); font-size: 12px;">No grade available</span>';

  // Health Summary
  const summary = document.getElementById("insights-health-summary");
  summary.textContent = data.health_summary || "No summary available";

  // Nutri-Score Explanation
  const nutriExplSection = document.getElementById("insights-nutri-explanation-section");
  const nutriText = document.getElementById("insights-nutri-text");
  if (data.nutriscore_explanation) {
    nutriText.textContent = data.nutriscore_explanation;
    nutriExplSection.classList.remove("hidden");
  } else {
    nutriExplSection.classList.add("hidden");
  }

  // NOVA Explanation
  const novaExplSection = document.getElementById("insights-nova-explanation-section");
  const novaText = document.getElementById("insights-nova-text");
  if (data.nova_explanation) {
    novaText.textContent = data.nova_explanation;
    novaExplSection.classList.remove("hidden");
  } else {
    novaExplSection.classList.add("hidden");
  }

  // Positive Indicators
  const positiveList = document.getElementById("insights-positive-list");
  positiveList.innerHTML = renderPositiveIndicators(data.positive_indicators);
  document.getElementById("insights-positive-section").classList.toggle(
    "hidden",
    !data.positive_indicators || data.positive_indicators.length === 0
  );

  // Risk Indicators
  const riskList = document.getElementById("insights-risk-list");
  riskList.innerHTML = renderRiskIndicators(data.risk_indicators);
  document.getElementById("insights-risk-section").classList.toggle(
    "hidden",
    !data.risk_indicators || data.risk_indicators.length === 0
  );

  // Pairings
  const pairingsList = document.getElementById("insights-pairings-list");
  pairingsList.innerHTML = renderPairings(data.food_pairings);
  document.getElementById("insights-pairings-section").classList.toggle(
    "hidden",
    !data.food_pairings || data.food_pairings.length === 0
  );

  // Recommendations
  const recommendationsList = document.getElementById("insights-recommendations-list");
  recommendationsList.innerHTML = renderRecommendations(data.daily_recommendations);
  document.getElementById("insights-recommendations-section").classList.toggle(
    "hidden",
    !data.daily_recommendations || data.daily_recommendations.length === 0
  );

  // Alternatives
  const alternativesList = document.getElementById("insights-alternatives-list");
  alternativesList.innerHTML = renderAlternatives(data.alternatives);
  document.getElementById("insights-alternatives-section").classList.toggle(
    "hidden",
    !data.alternatives || data.alternatives.length === 0
  );

  // SLM Badge
  if (data.slm_enhanced) {
    document.getElementById("insights-slm-badge").classList.remove("hidden");
  } else {
    document.getElementById("insights-slm-badge").classList.add("hidden");
  }
}

function showInsights(show) {
  if (show) {
    searchSection.classList.add("hidden");
    resultsSection.classList.add("hidden");
    insightsSection.classList.remove("hidden");
  } else {
    searchSection.classList.remove("hidden");
    resultsSection.classList.remove("hidden");
    insightsSection.classList.add("hidden");
  }
}

function showLoading(show) {
  loadingEl.classList.toggle("hidden", !show);
}

function showError(msg) {
  errorEl.textContent = msg;
  errorEl.classList.remove("hidden");
}

function clearError() {
  errorEl.classList.add("hidden");
  errorEl.textContent = "";
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str || ""));
  return div.innerHTML;
}

// -------------------------------------------------------------------------
// Event Handlers
// -------------------------------------------------------------------------

async function handleProductClick(barcode, sessionId, language) {
  currentSessionId = sessionId;
  currentLanguage = language || "en";

  clearError();
  showLoading(true);
  showInsights(true);

  try {
    const insights = await fetchProductInsights(barcode);
    renderInsights(insights);
  } catch (err) {
    showError(`Failed to load product insights: ${err.message}`);
    showInsights(false);
  } finally {
    showLoading(false);
  }
}

function handleBackToResults() {
  showInsights(false);
  clearError();
}

// -------------------------------------------------------------------------
// Public API
// -------------------------------------------------------------------------

export { handleProductClick, handleBackToResults, showInsights, showLoading };

// -------------------------------------------------------------------------
// Event Listeners
// -------------------------------------------------------------------------

backBtn.addEventListener("click", handleBackToResults);

// Expose globally for popup.js to use
window.showProductInsights = handleProductClick;
