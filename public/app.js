/* global gsap */
(function () {
  'use strict';

  // ---------- Card rotation ----------

  function initCardRotation() {
    var reduceMotion =
      window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var cards = document.querySelectorAll('#card-stack .ex-card');
    if (!cards.length) return;

    if (reduceMotion || typeof gsap === 'undefined') {
      cards[0].style.opacity = '1';
      return;
    }

    gsap.set(cards, { opacity: 0, y: 6 });
    gsap.set(cards[0], { opacity: 1, y: 0 });

    var current = 0;
    var DWELL_MS = 6000;
    var FADE_S = 1.2;

    setInterval(function () {
      var next = (current + 1) % cards.length;
      var tl = gsap.timeline();
      tl.to(cards[current], { opacity: 0, y: -6, duration: FADE_S, ease: 'power4.out' })
        .fromTo(cards[next],
          { opacity: 0, y: 6 },
          { opacity: 1, y: 0, duration: FADE_S, ease: 'power4.out' },
          '-=' + (FADE_S * 0.5));
      current = next;
    }, DWELL_MS);
  }

  // ---------- Form submission ----------

  var state = { signupId: null, budgetBucket: 'mid' };

  function showThanks() {
    document.getElementById('signup-form').classList.add('is-hidden');
    document.getElementById('thanks-state').hidden = false;
  }

  function initSignupForm() {
    var form = document.getElementById('signup-form');
    if (!form) return;

    form.addEventListener('submit', function (evt) {
      evt.preventDefault();
      var emailInput = document.getElementById('email-input');
      var email = (emailInput.value || '').trim();
      if (!email) { emailInput.focus(); return; }

      var btn = form.querySelector('button[type="submit"]');
      btn.disabled = true;
      btn.textContent = '…';

      fetch('/api/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email: email })
      })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
      .then(function (res) {
        if (!res.ok) {
          btn.disabled = false;
          btn.textContent = 'Where can I go?';
          emailInput.focus();
          return;
        }
        state.signupId = res.body.signup_id;
        showThanks();
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = 'Where can I go?';
      });
    });
  }

  // ---------- Pick (budget bucket) buttons ----------

  function initPickButtons() {
    var picks = document.querySelectorAll('#budget-group .pick');
    picks.forEach(function (btn) {
      btn.addEventListener('click', function () {
        picks.forEach(function (b) {
          b.classList.remove('is-selected');
          b.setAttribute('aria-checked', 'false');
        });
        btn.classList.add('is-selected');
        btn.setAttribute('aria-checked', 'true');
        state.budgetBucket = btn.getAttribute('data-pick');
      });
    });
  }

  // ---------- Qualifier submit / skip ----------

  function initQualifierActions() {
    var submitBtn = document.getElementById('qualifier-submit');
    var skipBtn = document.getElementById('qualifier-skip');

    function dismissThanks() {
      // Replace thanks state with a quiet final message
      var thanks = document.getElementById('thanks-state');
      thanks.innerHTML = '<p class="lead-in">Thanks. We\'ll be in touch.</p>';
    }

    if (submitBtn) {
      submitBtn.addEventListener('click', function () {
        if (!state.signupId) { dismissThanks(); return; }
        var payload = {
          budget_bucket: state.budgetBucket,
          home_airport: (document.getElementById('airport-input').value || '').trim() || null,
          frustration: (document.getElementById('frustration-input').value || '').trim() || null
        };
        submitBtn.disabled = true;
        submitBtn.textContent = '…';

        fetch('/api/qualifiers/' + state.signupId, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload)
        }).then(function () { dismissThanks(); })
          .catch(function () { dismissThanks(); });
      });
    }
    if (skipBtn) {
      skipBtn.addEventListener('click', dismissThanks);
    }
  }

  // ---------- Bootstrap ----------

  document.addEventListener('DOMContentLoaded', function () {
    initCardRotation();
    initSignupForm();
    initPickButtons();
    initQualifierActions();
  });
})();

// ===== /go page =====

(function initGo() {
  const form = document.getElementById('go-form');
  if (!form) return;  // not on /go page

  const resultsEl = document.getElementById('results');
  const emptyEl = document.getElementById('empty-state');
  const gateEl = document.getElementById('email-gate');
  const gateDismiss = document.getElementById('gate-dismiss');
  const SEARCH_COUNT_KEY = 'promptiv_search_count';

  function readSearchCount() {
    return parseInt(localStorage.getItem(SEARCH_COUNT_KEY) || '0', 10);
  }
  function incrementSearchCount() {
    const n = readSearchCount() + 1;
    localStorage.setItem(SEARCH_COUNT_KEY, String(n));
    return n;
  }
  function gateSatisfied() {
    return localStorage.getItem('promptiv_gate_ok') === '1';
  }

  function renderCards(results) {
    if (!results.length) {
      resultsEl.hidden = true;
      emptyEl.hidden = false;
      return;
    }
    emptyEl.hidden = true;
    resultsEl.hidden = false;
    resultsEl.innerHTML = results.map(cardHtml).join('');
  }

  function cardHtml(c) {
    const dep = formatDate(c.departure_date);
    const ret = formatDate(c.return_date);
    const vibesText = c.vibes.join(' · ');
    const monthsText = c.best_months.map(monthName).join(', ');
    const catchHtml = c.catch ? `<p class="card-catch">catch: ${escapeHtml(c.catch)}</p>` : '';
    return `
      <article class="trip-card">
        <header class="card-head">
          <h3>${escapeHtml(c.city)}, ${escapeHtml(c.country)}</h3>
          <div class="card-price">$${c.price_usd}</div>
        </header>
        <div class="card-meta">${c.trip_nights} nights · ${dep}–${ret}</div>
        ${catchHtml}
        <dl class="card-details">
          <div><dt>best months</dt><dd>${monthsText}</dd></div>
          <div><dt>daily budget</dt><dd>~$${c.avg_daily_cost_usd} food + lodging</dd></div>
          <div><dt>vibes</dt><dd>${escapeHtml(vibesText)}</dd></div>
        </dl>
        <a class="card-link" href="${c.google_flights_url}" target="_blank" rel="noopener">See on Google Flights →</a>
      </article>
    `;
  }

  function formatDate(iso) {
    const [, m, d] = iso.split('-');
    return `${monthName(parseInt(m, 10)).slice(0, 3)} ${parseInt(d, 10)}`;
  }
  function monthName(n) {
    return ['', 'January','February','March','April','May','June','July','August','September','October','November','December'][n];
  }
  function escapeHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
    }[c]));
  }

  async function submitSearch(payload) {
    const r = await fetch('/api/go', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return r.json();
  }

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(form);
    const vibes = fd.getAll('vibes');
    const payload = {
      origin_iata: fd.get('origin_iata'),
      budget_usd: parseInt(fd.get('budget_usd'), 10),
      trip_nights: parseInt(fd.get('trip_nights'), 10),
      vibes: vibes,
    };

    // Email gate: trigger BEFORE the 6th search runs
    const count = readSearchCount();
    if (count >= 5 && !gateSatisfied()) {
      gateEl.hidden = false;
      return;
    }

    try {
      const data = await submitSearch(payload);
      incrementSearchCount();
      renderCards(data.results);
    } catch (err) {
      resultsEl.hidden = false;
      resultsEl.innerHTML = `<p class="error">Something went wrong. Try again in a moment.</p>`;
    }
  });

  const gateForm = document.getElementById('gate-form');
  gateForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const fd = new FormData(gateForm);
    try {
      await fetch('/api/signup', { method: 'POST', body: fd });
    } catch (err) { /* ignore - still mark satisfied */ }
    localStorage.setItem('promptiv_gate_ok', '1');
    gateEl.hidden = true;
    form.dispatchEvent(new Event('submit'));
  });

  gateDismiss.addEventListener('click', () => {
    gateEl.hidden = true;
  });
})();

