/**
 * app.js — CodeAlpha URL Shortener frontend logic
 *
 * Uses the Fetch API to talk to the Flask backend.
 * No page reloads occur; all state is managed in the DOM.
 *
 * Security notes
 * --------------
 * - User-supplied text is set via textContent or element.href,
 *   never via innerHTML, to prevent XSS injection.
 * - No secret values or credentials live here.
 */

"use strict";

/* ---- DOM references ---- */
const form           = document.getElementById("shorten-form");
const urlInput       = document.getElementById("url-input");
const submitBtn      = document.getElementById("submit-btn");
const btnText        = document.getElementById("btn-text");
const btnSpinner     = document.getElementById("btn-spinner");

const successSection = document.getElementById("success-section");
const errorSection   = document.getElementById("error-section");

const shortUrlAnchor = document.getElementById("short-url-anchor");
const originalNote   = document.getElementById("original-url-note");
const copyBtn        = document.getElementById("copy-btn");
const anotherBtn     = document.getElementById("another-btn");

const errorText      = document.getElementById("error-text");
const toast          = document.getElementById("copy-toast");


/* ---- Helpers ---- */

/** Show or hide an element by toggling the "visible" class. */
function setVisible(el, show) {
  el.classList.toggle("visible", show);
}

/** Display a brief toast notification. */
function showToast(message) {
  toast.textContent = message;
  toast.classList.add("show");
  setTimeout(() => toast.classList.remove("show"), 2000);
}

/** Reset UI to the blank initial state. */
function resetUI() {
  setVisible(successSection, false);
  setVisible(errorSection,   false);
  urlInput.classList.remove("input-error");
}

/** Put the submit button into loading or idle mode. */
function setLoading(isLoading) {
  submitBtn.disabled = isLoading;
  btnText.textContent = isLoading ? "Shortening…" : "Shorten URL";
  btnSpinner.style.display = isLoading ? "block" : "none";
}

/** Display an error message to the user. */
function showError(message) {
  // Use textContent, never innerHTML, to prevent XSS.
  errorText.textContent = message;
  urlInput.classList.add("input-error");
  setVisible(errorSection,   true);
  setVisible(successSection, false);
}

/** Display the successful result. */
function showSuccess(data) {
  // Set the short URL anchor safely.
  shortUrlAnchor.href        = data.short_url;
  shortUrlAnchor.textContent = data.short_url;

  // Show original URL note using textContent.
  const originalAnchor = document.getElementById("original-anchor");
  originalAnchor.href        = data.original_url;
  originalAnchor.textContent = data.original_url;

  urlInput.classList.remove("input-error");
  setVisible(successSection, true);
  setVisible(errorSection,   false);
}


/* ---- Form submission ---- */

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  resetUI();

  const rawUrl = urlInput.value.trim();
  if (!rawUrl) {
    showError("Please enter a URL before submitting.");
    return;
  }

  setLoading(true);

  try {
    const response = await fetch("/api/shorten", {
      method:  "POST",
      headers: { "Content-Type": "application/json" },
      body:    JSON.stringify({ url: rawUrl }),
    });

    const data = await response.json();

    if (response.ok) {
      showSuccess(data);
    } else {
      // Use the server's error message, or a generic fallback.
      showError(data.error || "An unexpected error occurred. Please try again.");
    }
  } catch (networkError) {
    // Covers cases where the server is down or the response is not JSON.
    showError("Could not reach the server. Please check your connection and try again.");
  } finally {
    setLoading(false);
  }
});


/* ---- Copy to clipboard ---- */

copyBtn.addEventListener("click", async () => {
  const urlToCopy = shortUrlAnchor.href;
  try {
    await navigator.clipboard.writeText(urlToCopy);
    showToast("✓ Copied to clipboard!");
  } catch {
    // Clipboard API may be unavailable in some browsers / contexts.
    showToast("Could not copy. Please copy the URL manually.");
  }
});


/* ---- Shorten another URL ---- */

anotherBtn.addEventListener("click", () => {
  resetUI();
  urlInput.value = "";
  urlInput.focus();
});


/* ---- Clear input error styling on typing ---- */

urlInput.addEventListener("input", () => {
  urlInput.classList.remove("input-error");
  if (!urlInput.value) resetUI();
});
