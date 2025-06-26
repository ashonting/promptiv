// frontend/script.js

// --- Generate or Retrieve Device Hash ---
function getDeviceHash() {
  let hash = localStorage.getItem("promptiv_device_hash");
  if (!hash) {
    // Simple UUIDv4 generator (not cryptographically strong)
    hash = ([1e7]+-1e3+-4e3+-8e3+-1e11)
      .replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
      );
    localStorage.setItem("promptiv_device_hash", hash);
  }
  return hash;
}

// --- UI References ---
document.addEventListener("DOMContentLoaded", () => {
  const promptEl = document.getElementById("prompt");
  const submitBtn = document.getElementById("submit");
  const errorEl = document.getElementById("error-message");
  const resultEl = document.getElementById("result");
  const spinnerEl = document.getElementById("spinner");
  const trialCta = document.getElementById("trial-exhausted-cta");
  const formEl = document.getElementById("prompt-form");

  let deviceUserInfo = null;

  // --- Helper Functions ---
  function showSpinner()   { spinnerEl.style.display = "inline-block"; }
  function hideSpinner()   { spinnerEl.style.display = "none"; }
  function showError(msg)  { errorEl.textContent = msg; errorEl.style.display = "block"; }
  function clearError()    { errorEl.textContent = "";  errorEl.style.display = "none"; }
  function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
      alert("Copied to clipboard");
    });
  }

  // --- Fetch Anonymous Device Quota/State ---
  async function fetchDeviceQuota() {
    try {
      const res = await fetch("/api/user", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ device_hash: getDeviceHash() })
      });
      if (!res.ok) throw new Error("Failed to fetch device quota");
      deviceUserInfo = await res.json();
    } catch (err) {
      deviceUserInfo = { error: true, message: "Could not fetch device quota" };
    }
  }

  // --- Update CTA visibility based on quota/plan ---
  async function updateCtaVisibility() {
    await fetchDeviceQuota();
    if (
      deviceUserInfo &&
      deviceUserInfo.tier === "anonymous" &&
      Number(deviceUserInfo.quota_used) >= 1
    ) {
      formEl.style.display = "none";
      trialCta.style.display = "flex";
    } else {
      formEl.style.display = "block";
      trialCta.style.display = "none";
    }
  }

  // Initial CTA state
  updateCtaVisibility();

  // --- Handle Prompt Submission ---
  submitBtn.addEventListener("click", async () => {
    clearError();
    resultEl.innerHTML = "";

    const promptText = promptEl.value.trim();
    if (!promptText) {
      showError("Please enter a prompt.");
      return;
    }

    // Always re-check quota just before submit
    await updateCtaVisibility();

    // If quota exhausted, bail out
    if (
      deviceUserInfo &&
      deviceUserInfo.tier === "anonymous" &&
      Number(deviceUserInfo.quota_used) >= 1
    ) {
      return;
    }

    showSpinner();

    try {
      const res = await fetch("/api/rewrite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: promptText, device_hash: getDeviceHash() })
      });

      hideSpinner();

      if (!res.ok) {
        const err = await res.json();
        showError(err.error || err.detail || "Error processing request.");
        return;
      }

      const data = await res.json();

      // Accepts variants[] or rewrites[] or single variant (futureproof)
      const variants = data.variants || data.rewrites || (data.rewritten_prompt ? [{
        variant_style: data.variant_style || "Default",
        prompt: data.rewritten_prompt
      }] : []);

      if (!variants.length) {
        showError("No rewritten prompts returned.");
        return;
      }

      variants.forEach((variant, idx) => {
        const card = document.createElement("div");
        card.className = "prompt-card";

        const header = document.createElement("div");
        header.className = "variant-header";
        const heading = document.createElement("span");
        heading.className = "variant-style";
        heading.textContent = variant.variant_style || `Variant ${idx + 1}`;
        header.appendChild(heading);

        const copyBtn = document.createElement("button");
        copyBtn.textContent = "Copy";
        copyBtn.className = "copy-btn";
        copyBtn.onclick = () => copyToClipboard(variant.prompt);
        header.appendChild(copyBtn);

        card.appendChild(header);

        const promptBody = document.createElement("div");
        promptBody.className = "prompt-body";
        promptBody.textContent = variant.prompt || variant;
        card.appendChild(promptBody);

        resultEl.appendChild(card);
      });

      // Re-fetch quota after submit to update CTA
      await updateCtaVisibility();

    } catch (err) {
      hideSpinner();
      showError("Network or server error. Please try again later.");
    }
  });
});
