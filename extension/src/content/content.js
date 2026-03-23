/**
 * content.js – Content Script
 *
 * Injected on Open Food Facts product pages.
 * Responsibilities:
 *  1. Detect barcode from URL
 *  2. Inject the insight panel sidebar into the page DOM
 *  3. Fetch product insights from the backend
 *  4. Render results in the panel
 */

(function () {
  "use strict";

  // -------------------------------------------------------------------------
  // Helpers
  // -------------------------------------------------------------------------

  function extractBarcode(url) {
    const match = url.match(/\/(?:product|produit)\/(\d{4,14})/);
    return match ? match[1] : null;
  }

  function detectLanguage(url) {
    try {
      const host = new URL(url).hostname;
      if (host.startsWith("fr.")) return "fr";
    } catch {}
    return "en";
  }

  function t(key, lang) {
    const translations = {
      en: {
        title: "OFF Explorer – Insights",
        loading: "Loading insights…",
        error: "Could not load insights. Is the backend running?",
        risks: "Risk Indicators",
        positives: "Positive Points",
        alternatives: "Healthier Alternatives",
        pairings: "Food Pairings",
        recommendations: "Daily Recommendations",
        nutriscore: "Nutri-Score",
        nova: "NOVA Group",
        close: "✕",
        score: "Score",
      },
      fr: {
        title: "OFF Explorer – Aperçu",
        loading: "Chargement…",
        error: "Impossible de charger les données. Le serveur est-il actif ?",
        risks: "Indicateurs de risque",
        positives: "Points positifs",
        alternatives: "Alternatives plus saines",
        pairings: "Accompagnements",
        recommendations: "Recommandations",
        nutriscore: "Nutri-Score",
        nova: "Groupe NOVA",
        close: "✕",
        score: "Score",
      },
    };
    return (translations[lang] || translations["en"])[key] || key;
  }

  // -------------------------------------------------------------------------
  // Panel injection
  // -------------------------------------------------------------------------

  function createPanel(lang) {
    const panel = document.createElement("div");
    panel.id = "off-insight-panel";
    panel.setAttribute("role", "complementary");
    panel.setAttribute("aria-label", t("title", lang));

    panel.innerHTML = `
      <div id="off-panel-header">
        <span id="off-panel-title">${t("title", lang)}</span>
        <button id="off-panel-close" aria-label="${t("close", lang)}">${t("close", lang)}</button>
      </div>
      <div id="off-panel-body">
        <p id="off-panel-loading">${t("loading", lang)}</p>
      </div>
    `;

    document.body.appendChild(panel);

    document.getElementById("off-panel-close").addEventListener("click", () => {
      panel.remove();
    });

    return panel;
  }

  function nsGradeColor(grade) {
    const colors = { a: "#038141", b: "#85BB2F", c: "#FFCC00", d: "#EE8100", e: "#E63312" };
    return colors[(grade || "").toLowerCase()] || "#aaa";
  }

  function renderInsights(data, lang) {
    const body = document.getElementById("off-panel-body");
    if (!body) return;

    const ns = data.nutriscore_grade
      ? `<span class="off-nutriscore" style="background:${nsGradeColor(data.nutriscore_grade)}">${data.nutriscore_grade.toUpperCase()}</span>`
      : "";
    const nova = data.nova_group
      ? `<span class="off-nova">NOVA ${data.nova_group}</span>`
      : "";

    const risksHtml = data.risk_indicators.length
      ? `<section>
          <h3>${t("risks", lang)}</h3>
          <ul>${data.risk_indicators.map(r =>
            `<li class="off-risk off-risk-${r.level}">⚠ ${r.label}: ${r.value}</li>`
          ).join("")}</ul>
        </section>`
      : "";

    const posHtml = data.positive_indicators.length
      ? `<section>
          <h3>${t("positives", lang)}</h3>
          <ul>${data.positive_indicators.map(p =>
            `<li class="off-positive">✓ ${p.label}: ${p.value}</li>`
          ).join("")}</ul>
        </section>`
      : "";

    const altHtml = data.alternatives.length
      ? `<section>
          <h3>${t("alternatives", lang)}</h3>
          <ul>${data.alternatives.slice(0, 3).map(a =>
            `<li><a href="https://world.openfoodfacts.org/product/${a.barcode}" target="_blank">${a.product_name}</a>
              ${a.nutriscore_grade ? `<span class="off-nutriscore" style="background:${nsGradeColor(a.nutriscore_grade)}">${a.nutriscore_grade.toUpperCase()}</span>` : ""}
            </li>`
          ).join("")}</ul>
        </section>`
      : "";

    const pairingsHtml = data.food_pairings.length
      ? `<section>
          <h3>${t("pairings", lang)}</h3>
          <p>${data.food_pairings.join(", ")}</p>
        </section>`
      : "";

    const recsHtml = data.daily_recommendations.length
      ? `<section>
          <h3>${t("recommendations", lang)}</h3>
          <ul>${data.daily_recommendations.map(r => `<li>${r}</li>`).join("")}</ul>
        </section>`
      : "";

    body.innerHTML = `
      <div class="off-summary">
        <p><strong>${data.product_name}</strong></p>
        <div class="off-badges">${ns}${nova}</div>
        <p class="off-health-summary">${data.health_summary}</p>
        ${data.nutriscore_explanation ? `<p class="off-expl">${data.nutriscore_explanation}</p>` : ""}
        ${data.nova_explanation ? `<p class="off-expl">${data.nova_explanation}</p>` : ""}
      </div>
      ${risksHtml}
      ${posHtml}
      ${altHtml}
      ${pairingsHtml}
      ${recsHtml}
      ${data.slm_enhanced ? '<p class="off-slm-badge">✨ Enhanced by Phi-3-mini</p>' : ""}
    `;
  }

  // -------------------------------------------------------------------------
  // Main
  // -------------------------------------------------------------------------

  async function init() {
    const barcode = extractBarcode(window.location.href);
    if (!barcode) return;  // Not a product page

    const lang = detectLanguage(window.location.href);

    // Retrieve session from background
    const { sessionId } = await new Promise((resolve) =>
      chrome.runtime.sendMessage({ type: "GET_SESSION" }, resolve)
    );

    createPanel(lang);

    try {
      const result = await new Promise((resolve) =>
        chrome.runtime.sendMessage(
          { type: "FETCH_INSIGHTS", barcode, sessionId, language: lang },
          resolve
        )
      );

      if (!result || !result.ok) {
        throw new Error(result?.error || "Failed to fetch insights");
      }

      renderInsights(result.data, lang);
    } catch (err) {
      const body = document.getElementById("off-panel-body");
      if (body) {
        body.innerHTML = `<p class="off-error">${t("error", lang)}</p><p class="off-error-detail">${err.message}</p>`;
      }
    }
  }

  // Run after page load
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
