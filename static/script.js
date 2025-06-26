// ========== Device Hash (anonymous trial) ==========
function getDeviceHash() {
  let hash = localStorage.getItem("promptiv_device_hash");
  if (!hash) {
    hash = ([1e7] + -1e3 + -4e3 + -8e3 + -1e11)
      .replace(/[018]/g, c =>
        (c ^ crypto.getRandomValues(new Uint8Array(1))[0] & 15 >> c / 4).toString(16)
      );
    localStorage.setItem("promptiv_device_hash", hash);
  }
  return hash;
}

// ========== Dark Mode (toggle, system, persistence) ==========
function setDarkMode(isDark) {
  document.body.classList.toggle('dark', isDark);
  localStorage.setItem('promptiv_darkmode', isDark ? '1' : '0');
  document.getElementById('dark-mode-toggle').textContent = isDark ? '☀️' : '🌙';
}
(function () {
  const saved = localStorage.getItem('promptiv_darkmode');
  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)')?.matches;
  setDarkMode(saved === '1' || (saved === null && prefersDark));
})();
document.getElementById('dark-mode-toggle')
  .addEventListener('click', () => setDarkMode(!document.body.classList.contains('dark')));

// ========== Model Count & Carousel ==========
async function fetchLLMInfo() {
  try {
    const resp = await fetch('/api/llm_count');
    const data = await resp.json();
    const models = data.models || [];
    const count  = data.count ?? models.length;
    document.getElementById('model-count').textContent = count;
    startModelCarousel(models.length ? models : [
      "Claude 3 Opus","GPT-4o","Gemini 1.5","Llama 3",
      "Perplexity Sonar","DeepSeek-V2","Google Veo","Cohere Command R"
    ]);
  } catch {
    const fallback = [
      "Claude 3 Opus","GPT-4o","Gemini 1.5","Llama 3",
      "Perplexity Sonar","DeepSeek-V2","Google Veo","Cohere Command R"
    ];
    document.getElementById('model-count').textContent = fallback.length;
    startModelCarousel(fallback);
  }
}
function startModelCarousel(models) {
  const nameEl = document.getElementById('carousel-model-name');
  let idx = 0;
  const maxLen = Math.max(...models.map(n => n.length));
  Object.assign(nameEl.style, {
    width:    `${maxLen+2}ch`,
    display:  'inline-block',
    overflow: 'hidden',
    whiteSpace: 'nowrap',
    textAlign: 'center'
  });
  nameEl.textContent = models[0];
  setInterval(() => {
    idx = (idx + 1) % models.length;
    nameEl.style.opacity = 0;
    setTimeout(() => {
      nameEl.textContent = models[idx];
      nameEl.style.opacity = 1;
    }, 200);
  }, 2200);
}
fetchLLMInfo();

// ========== Prompt Submission & Result Rendering ==========
const submitBtn = document.getElementById('submit');
const promptEl  = document.getElementById('prompt');
const errorEl   = document.getElementById('error-message');
const spinnerEl = document.getElementById('spinner');
const resultEl  = document.getElementById('result');

// Escape HTML entities
function escapeHTML(str) {
  return String(str).replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;',
    '"': '&quot;', "'": '&#39;'
  }[c]));
}

// Badge CSS helper
function variantBadgeClass(style) {
  if (/concise/i.test(style))    return "variant-badge concise-badge";
  if (/creative/i.test(style))   return "variant-badge creative-badge";
  if (/analytical/i.test(style)) return "variant-badge analytical-badge";
  return "variant-badge";
}

// Copy button feedback
function copyPrompt(text, btn) {
  navigator.clipboard.writeText(text).then(() => {
    btn.classList.add('copied');
    btn.textContent = 'Copied!';
    setTimeout(() => {
      btn.classList.remove('copied');
      btn.textContent = '📋 Copy Prompt';
    }, 1200);
  });
}

// Render one variant card
function renderVariantCard(v) {
  return `
    <div class="variant-card">
      <div class="variant-header">
        <span class="${variantBadgeClass(v.variant_style)}">
          ${escapeHTML(v.variant_style)}
        </span>
        <div class="variant-actions">
          <button class="copy-btn" data-prompt="${escapeHTML(v.prompt)}">
            📋 Copy Prompt
          </button>
          <button class="copy-llm-btn"
                  data-prompt="${escapeHTML(v.prompt)}"
                  data-llm-url="${v.quick_copy_url}"
                  data-llm-name="${escapeHTML(v.best_llm)}">
            🔗 Open in ${escapeHTML(v.best_llm)}
          </button>
        </div>
      </div>
      ${ (v.best_for || v.clarity || v.complexity) ? `
      <div class="variant-meta">
        ${v.best_for    ? `<span class="meta-label">Best for:</span> ${escapeHTML(v.best_for)}` : ''}
        ${v.clarity     ? ` | <span class="meta-label">Clarity:</span> ${escapeHTML(v.clarity)}/10` : ''}
        ${v.complexity  ? ` | <span class="meta-label">Complexity:</span> ${escapeHTML(v.complexity)}/10` : ''}
      </div>` : ''}
      <div class="variant-prompt">${escapeHTML(v.prompt)}</div>
      ${v.why_this_works ? `<div class="variant-why">Why this works: ${escapeHTML(v.why_this_works)}</div>` : ''}
    </div>
  `;
}

submitBtn.addEventListener('click', async () => {
  errorEl.textContent = "";
  resultEl.innerHTML = "";
  const prompt = promptEl.value.trim();
  if (!prompt) {
    errorEl.textContent = "Please enter your prompt.";
    return;
  }

  spinnerEl.style.display = "block";
  submitBtn.disabled    = true;

  try {
    const res = await fetch('/api/rewrite', {
      method: 'POST',
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        prompt,
        device_hash: getDeviceHash()
      }),
    });

    spinnerEl.style.display = "none";
    submitBtn.disabled     = false;

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Server error.' }));
      throw new Error(err.detail || 'Server error.');
    }

    const data = await res.json();
    const variants = data.variants || [];

    if (!variants.length) {
      resultEl.innerHTML = "<div class='variant-card'>No rewrites found.</div>";
      return;
    }

    resultEl.innerHTML = variants.map(renderVariantCard).join('');

    // Attach copy handlers
    resultEl.querySelectorAll('.copy-btn').forEach(btn => {
      btn.addEventListener('click', () => copyPrompt(btn.dataset.prompt, btn));
    });
    resultEl.querySelectorAll('.copy-llm-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const text = btn.dataset.prompt;
        const url  = btn.dataset.llmUrl || null;
        const name = btn.dataset.llmName;
        navigator.clipboard.writeText(text).then(() => {
          btn.classList.add('copied');
          btn.textContent = 'Opened!';
          if (url) window.open(url, '_blank');
          setTimeout(() => {
            btn.classList.remove('copied');
            btn.textContent = `🔗 Open in ${name}`;
          }, 1200);
        });
      });
    });

  } catch (e) {
    spinnerEl.style.display = "none";
    submitBtn.disabled     = false;
    errorEl.textContent    = e.message || "Sorry, something went wrong.";
  }
});

// Ctrl+Enter or Cmd+Enter → submit
promptEl.addEventListener('keydown', e => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    submitBtn.click();
  }
});
