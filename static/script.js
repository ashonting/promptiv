// ========== Dark Mode (toggle, system, persistence) ==========
function setDarkMode(isDark) {
  document.body.classList.toggle('dark', isDark);
  localStorage.setItem('promptiv_darkmode', isDark ? '1' : '0');
  document.getElementById('dark-mode-toggle').textContent = isDark ? '☀️' : '🌙';
}
(function () {
  const saved = localStorage.getItem('promptiv_darkmode');
  const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  setDarkMode(saved === '1' || (saved === null && prefersDark));
})();
document.getElementById('dark-mode-toggle').addEventListener('click', () => {
  setDarkMode(!document.body.classList.contains('dark'));
});

// ========== Model Count & Carousel ==========
async function fetchLLMInfo() {
  try {
    const resp = await fetch('/api/llm_count');
    const data = await resp.json();
    const modelCount = data.count || 12;
    const models = data.models || [
      "Claude 3 Opus","GPT-4o","Gemini 1.5","Llama 3",
      "Perplexity Sonar","DeepSeek-V2","Google Veo","Cohere Command R"
    ];
    document.getElementById('model-count').textContent = modelCount;
    startModelCarousel(models);
  } catch (e) {
    document.getElementById('model-count').textContent = "12";
    startModelCarousel([
      "Claude 3 Opus","GPT-4o","Gemini 1.5","Llama 3",
      "Perplexity Sonar","DeepSeek-V2","Google Veo","Cohere Command R"
    ]);
  }
}
function startModelCarousel(models) {
  const nameEl = document.getElementById('carousel-model-name');
  let i = 0;
  // Calculate and fix the width for the longest name for a non-jumpy look
  let maxLen = Math.max(...models.map(name => name.length));
  nameEl.style.width = `${maxLen + 2}ch`;
  nameEl.style.display = "inline-block";
  nameEl.style.overflow = "hidden";
  nameEl.style.whiteSpace = "nowrap";
  nameEl.style.textAlign = "center";
  nameEl.textContent = models[0];
  setInterval(() => {
    i = (i + 1) % models.length;
    // Animate fade out & in
    nameEl.style.opacity = 0;
    setTimeout(() => {
      nameEl.textContent = models[i];
      nameEl.style.opacity = 1;
    }, 200);
  }, 2200);
}
fetchLLMInfo();

// ========== Prompt Submission & Result Rendering ==========
const submitBtn = document.getElementById('submit');
const promptEl = document.getElementById('prompt');
const errorEl = document.getElementById('error-message');
const spinnerEl = document.getElementById('spinner');
const resultEl = document.getElementById('result');

// Helper: Escape HTML
function escapeHTML(str) {
  return str.replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;',
    '"': '&quot;', "'": '&#39;'
  }[c]));
}

// Helper: Card color/badge classes
function variantBadgeClass(variant) {
  if (/concise/i.test(variant)) return "variant-badge concise-badge";
  if (/creative/i.test(variant)) return "variant-badge creative-badge";
  if (/analytical/i.test(variant)) return "variant-badge analytical-badge";
  return "variant-badge";
}

// Helper: Copy to clipboard with visual feedback
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
        <span class="${variantBadgeClass(v.variant_style)}">${escapeHTML(v.variant_style)} Variant</span>
        <div class="variant-actions">
          <button class="copy-btn" data-prompt="${escapeHTML(v.prompt)}" tabindex="0">📋 Copy Prompt</button>
          <a class="open-llm-btn" href="${v.quick_copy_url || '#'}" target="_blank" rel="noopener" tabindex="0">
            🔗 Open in ${escapeHTML(v.recommended_llm || 'AI')}
          </a>
        </div>
      </div>
      <div class="variant-meta">
        <span class="meta-label">Best for:</span> ${escapeHTML(v.best_for || '—')}
        ${v.clarity ? ` | <span class="meta-label">Clarity:</span> ${escapeHTML(v.clarity)}` : ""}
        ${v.complexity ? ` | <span class="meta-label">Complexity:</span> ${escapeHTML(v.complexity)}` : ""}
      </div>
      <div class="variant-prompt">${escapeHTML(v.prompt)}</div>
      ${v.why_works ? `<div class="variant-why show"><b>Why this works:</b> ${escapeHTML(v.why_works)}</div>` : ""}
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
  submitBtn.disabled = true;
  try {
    const response = await fetch('/api/rewrite', {
      method: 'POST',
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt }),
    });
    spinnerEl.style.display = "none";
    submitBtn.disabled = false;
    if (!response.ok) throw new Error("Server error.");
    const data = await response.json();
    if (data.variants && data.variants.length) {
      resultEl.innerHTML = data.variants.map(renderVariantCard).join('');
      // Add copy logic
      resultEl.querySelectorAll('.copy-btn').forEach(btn => {
        btn.addEventListener('click', function() {
          copyPrompt(this.getAttribute('data-prompt'), this);
        });
      });
    } else {
      resultEl.innerHTML = "<div class='variant-card'>No rewrites found.</div>";
    }
  } catch (e) {
    spinnerEl.style.display = "none";
    submitBtn.disabled = false;
    errorEl.textContent = "Sorry, something went wrong.";
  }
});

// Allow pressing Enter+Ctrl/Cmd to submit
promptEl.addEventListener('keydown', (e) => {
  if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
    submitBtn.click();
  }
});
