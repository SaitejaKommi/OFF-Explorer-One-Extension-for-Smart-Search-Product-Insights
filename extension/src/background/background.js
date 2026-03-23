/**
 * background.js – Service Worker
 *
 * Responsibilities:
 *  - Persist session_id across popup opens/closes (via chrome.storage.session)
 *  - Detect language from active tab URL (ca.openfoodfacts.org → en,
 *    fr.openfoodfacts.org → fr)
 *  - Relay messages between popup and content scripts
 */

const SESSION_KEY = "off_session_id";
const LANG_KEY = "off_language";

/**
 * Detect language from URL hostname.
 * @param {string} url
 * @returns {"en"|"fr"}
 */
function detectLanguageFromUrl(url) {
  try {
    const hostname = new URL(url).hostname;
    if (hostname.startsWith("fr.")) return "fr";
  } catch {}
  return "en";
}

/**
 * Extract barcode from an Open Food Facts product URL.
 * Supports:  /product/1234567890/...  and /produit/1234567890/...
 * @param {string} url
 * @returns {string|null}
 */
function extractBarcode(url) {
  const match = url.match(/\/(?:product|produit)\/(\d{4,14})/);
  return match ? match[1] : null;
}

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === "GET_SESSION") {
    chrome.storage.session.get([SESSION_KEY, LANG_KEY], (data) => {
      sendResponse({
        sessionId: data[SESSION_KEY] || null,
        language: data[LANG_KEY] || "en",
      });
    });
    return true; // async response
  }

  if (message.type === "SET_SESSION") {
    chrome.storage.session.set({ [SESSION_KEY]: message.sessionId });
    sendResponse({ ok: true });
    return true;
  }

  if (message.type === "GET_ACTIVE_TAB_INFO") {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0];
      if (!tab) {
        sendResponse({ barcode: null, language: "en", url: null });
        return;
      }
      const barcode = extractBarcode(tab.url || "");
      const language = detectLanguageFromUrl(tab.url || "");
      // Persist detected language
      chrome.storage.session.set({ [LANG_KEY]: language });
      sendResponse({ barcode, language, url: tab.url });
    });
    return true;
  }

  if (message.type === "CLEAR_SESSION") {
    chrome.storage.session.remove([SESSION_KEY, LANG_KEY]);
    sendResponse({ ok: true });
    return true;
  }

  if (message.type === "FETCH_INSIGHTS") {
    const { barcode, sessionId, language } = message;
    fetch("http://localhost:8000/product-insights", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        barcode,
        session_id: sessionId || null,
        language: language || "en",
      }),
    })
      .then(async (resp) => {
        if (!resp.ok) {
          let detail = `HTTP ${resp.status}`;
          try {
            const err = await resp.json();
            if (err && err.detail) detail = `${detail}: ${err.detail}`;
          } catch {}
          sendResponse({ ok: false, error: detail });
          return;
        }
        const data = await resp.json();
        sendResponse({ ok: true, data });
      })
      .catch((err) => {
        sendResponse({ ok: false, error: err?.message || "Failed to fetch insights" });
      });
    return true; // async response
  }
});

// On extension install / update: clear old session data
chrome.runtime.onInstalled.addListener(() => {
  chrome.storage.session.clear();
});
