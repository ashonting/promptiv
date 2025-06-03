window.addEventListener("DOMContentLoaded", () => {
  const promptEl = document.getElementById("prompt");
  const submitBtn = document.getElementById("submit");
  const errorEl = document.getElementById("error-message");
  const resultEl = document.getElementById("result");
  const spinnerEl = document.getElementById("spinner");
  const darkToggle = document.getElementById("dark-mode-toggle");
  const modelCountEl = document.getElementById('model-count');
  const carouselModelNameEl = document.getElementById('carousel-model-name');

  // ----- DARK MODE -----
  function setDarkMode(isDark) {
    document.body.classList.toggle('dark', isDark);
    localStorage.setItem('promptiv_darkmode', isDark ? '1' : '0');
    if (darkToggle) {
      darkToggle.textContent = isDark ? '☀️' : '🌙';
    }
  }
  (() => {
    const saved = localStorage.getItem('promptiv_darkmode');
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    setDarkMode(saved === '1' || (saved === null && prefersDark));
  })();
  if (darkToggle) {
    darkToggle.addEventListener('click', () => {
      setDarkMode(!document.body.classList.contains('dark'));
    });
  }

  // ----- MODEL CAROUSEL -----
  let modelNames = [];
  let modelCarouselIdx = 0;

  async function fetchLLMInfo() {
    try {
      const resp = await fetch('/api/llm_count');
      const data = await resp.json();
      modelNames = data.models || [];
      modelCountEl.textContent = data.count || modelNames.length;
      setupModelCarousel();
    } catch (e) {
      modelNames = ["Claude 4 Sonnet", "GPT-4o", "Gemini 1.5", "Llama 3"];
      modelCountEl.textContent = modelNames.length;
      setupModelCarousel();
    }
  }

  function setupModelCarousel() {
    if (!modelNames.length) modelNames = ["Claude 4 Sonnet"];
    // Set a min-width so container doesn't resize
    const maxLen = modelNames.reduce((a, b) => a.length > b.length ? a : b, '').length;
    if (carouselModelNameEl) {
      carouselModelNameEl.style.display = 'inline-block';
      carouselModelNameEl.style.minWidth = (maxLen * 0.66) + 'em'; // tune factor if needed
      carouselModelNameEl.textContent = modelNames[0];
    }
    setInterval(() => {
      modelCarouselIdx = (modelCarouselIdx + 1) % modelNames.length;
      if (carouselModelNameEl) {
        carouselModelNameEl.textContent = modelNames[modelCarouselIdx];
      }
    }, 2600);
  }
  fetchLLMInfo();

  // ----- SPINNER -----
  function showSpinner() { spinnerEl && (spinnerEl.style.display = "block"); }
  function hideSpinner() { spinnerEl && (spinnerEl.style.display = "none"); }

  // ----- ESCAPE HTML -----
  function escapeForHtmlAttr(str) {
    return (str || '').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // ----- COPY BUTTON -----
  resultEl.addEventListener('click', function(e) {
    // Copy prompt
    if (e.target.classList.contains('copy-btn')) {
      const promptText = e.target.getAttribute('data-prompt');
      if (promptText) {
        navigator.clipboard.writeText(promptText);
        e.target.textContent = "Copied!";
        e.target.classList.add("copied");
        setTimeout(() => {
          e.target.textContent = "Copy Prompt";
          e.target.classList.remove("copied");
        }, 1300);
      }
    }

    // Open LLM and copy prompt
    if (e.target.classList.contains('open-llm-btn')) {
      const promptText = e.target.getAttribute('data-prompt');
      const llmUrl = e.target.getAttribute('data-llm-url');
      // Always copy
      if (promptText) {
        navigator.clipboard.writeText(promptText);
      }
      // Open the model in new tab
      if (llmUrl) {
        window.open(llmUrl, '_blank', 'noopener');
      }
    }
  });

  // ----- SUBMIT HANDLER -----
  submitBtn.addEventListener("click", async () => {
    errorEl.textContent = "";
    resultEl.innerHTML = "";
    const promptText = promptEl.value.trim();
    if (!promptText) {
      errorEl.textContent = "Please enter a prompt.";
      return;
    }
    showSpinner();
    const startTime = Date.now();
    const minDelay = 700;
    try {
      const res = await fetch(`/api/rewrite`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: promptText })
      });
      if (!res.ok) throw new Error(res.statusText);
      const data = await res.json();
      const elapsed = Date.now() - startTime;
      if (elapsed < minDelay) await new Promise(r => setTimeout(r, minDelay - elapsed));
      hideSpinner();

      // --- RENDER RESULTS ---
      if (Array.isArray(data.variants)) {
        let variantsHtml = data.variants.map((v) => `
          <div class="variant-card">
            <div class="variant-header">
              <span class="variant-badge ${v.variant_style.toLowerCase()}-badge">
                ${capitalize(v.variant_style)} Variant
              </span>
              <div class="variant-actions">
                <button class="copy-btn" data-prompt="${escapeForHtmlAttr(v.prompt)}">Copy Prompt</button>
                ${v.quick_copy_url
                  ? `<button
                       class="open-llm-btn"
                       data-prompt="${escapeForHtmlAttr(v.prompt)}"
                       data-llm-url="${v.quick_copy_url}"
                       data-llm-name="${v.recommended_llm || "LLM"}"
                     >Open in ${v.recommended_llm || "LLM"}</button>`
                  : ""
                }
              </div>
            </div>
            <div class="variant-meta">
              <span>Best for: ${v.best_for || "—"}</span>
              <span>|</span>
              <span>Clarity: ${v.clarity || "—"}</span>
              <span>|</span>
              <span>Complexity: ${v.complexity || "—"}</span>
            </div>
            <pre class="variant-prompt">${v.prompt}</pre>
            <div class="why-card">
              <span>Why this works: ${v.why_this_works || "—"}</span>
            </div>
          </div>
        `).join("");
        resultEl.innerHTML = `<div class="results-variant-grid">${variantsHtml}</div>`;
      } else {
        resultEl.innerHTML = `
          <div class="variant-card">
            <div class="variant-header">
              <span class="variant-badge concise-badge">Improved Prompt</span>
            </div>
            <pre class="variant-prompt">${data.improved || data.improved_prompt || "—"}</pre>
          </div>
        `;
      }
    } catch (err) {
      hideSpinner();
      resultEl.innerHTML = '';
      errorEl.textContent = "Something went wrong: " + (err.message || "Unknown error");
    }
  });

  function capitalize(str) {
    if (!str) return "";
    return str.charAt(0).toUpperCase() + str.slice(1);
  }

  // ENTER key in textarea submits
  promptEl.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      submitBtn.click();
    }
  });
});
