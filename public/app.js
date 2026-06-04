/* global gsap */
(function () {
  'use strict';

  // ---------- Headline rotation (the 12 city pairings) ----------
  // The PAIRING is the durable creative; rotated client-side so the static
  // homepage shows all 12 cities with no geo. No dollar figures here on purpose
  // (those are volatile + fact-monitored; they live on the city hubs).
  // (city, cheapest marquee destination, recognizable splurge anchor). All three
  // flip in the headline. Each pairing is verified true (cheap week < anchor week
  // all-in) at authoring time; the engine will re-verify against live data later.
  var PAIRINGS = [
    { city: 'Nashville',     cheap: 'Medellín',     anchor: 'Vegas' },
    { city: 'New York',      cheap: 'Mexico City',       anchor: 'Honolulu' },
    { city: 'Los Angeles',   cheap: 'Oaxaca',            anchor: 'Cabo' },
    { city: 'Atlanta',       cheap: 'Cartagena',         anchor: 'Jackson Hole' },
    { city: 'Dallas',        cheap: 'Mérida',       anchor: 'Cabo' },
    { city: 'Chicago',       cheap: 'Guatemala City',    anchor: 'Honolulu' },
    { city: 'Miami',         cheap: 'Lima',              anchor: 'Aruba' },
    { city: 'Seattle',       cheap: 'Panama City',       anchor: 'Honolulu' },
    { city: 'Denver',        cheap: 'Bogotá',       anchor: 'Jackson Hole' },
    { city: 'Houston',       cheap: 'San José',     anchor: 'Jackson Hole' },
    { city: 'San Francisco', cheap: 'Sofia',             anchor: 'Jackson Hole' },
    { city: 'Boston',        cheap: 'Cairo',             anchor: 'Honolulu' }
  ];

  function initHeadlineRotation() {
    var cheapEl = document.getElementById('rh-cheap');
    var anchorEl = document.getElementById('rh-anchor');
    var cityEl = document.getElementById('rh-city');
    if (!cheapEl || !anchorEl || !cityEl) return;

    function apply(p) {
      cheapEl.textContent = p.cheap;
      anchorEl.textContent = p.anchor;
      cityEl.textContent = p.city;
    }
    apply(PAIRINGS[0]);

    var reduceMotion =
      window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    if (reduceMotion || typeof gsap === 'undefined') return; // first pairing, no rotation

    // Only the three changing words flip — the sentence frame stays put. Punchier.
    var targets = [cheapEl, anchorEl, cityEl];
    var current = 0;
    var DWELL_MS = 3500;
    var FADE_S = 0.35;
    var pendingTimer = null;
    var headlineEl = document.getElementById('headline');
    var ledeEl = cityEl.parentNode; // the .lede paragraph

    // Reserve the tallest rendered height across all pairings so a longer word
    // (e.g. "Guatemala City") can't rewrap the headline and bob the CTA below.
    // Re-measured after web fonts load and on resize, so it's right at any width.
    function lockHeights() {
      headlineEl.style.minHeight = '';
      ledeEl.style.minHeight = '';
      var maxH = 0, maxL = 0, i;
      for (i = 0; i < PAIRINGS.length; i++) {
        apply(PAIRINGS[i]);
        if (headlineEl.offsetHeight > maxH) maxH = headlineEl.offsetHeight;
        if (ledeEl.offsetHeight > maxL) maxL = ledeEl.offsetHeight;
      }
      apply(PAIRINGS[current]);
      headlineEl.style.minHeight = maxH + 'px';
      ledeEl.style.minHeight = maxL + 'px';
    }
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(lockHeights);
    } else {
      lockHeights();
    }
    var resizeTimer = null;
    window.addEventListener('resize', function () {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(lockHeights, 150);
    });

    // setTimeout chain (not setInterval) so animations can't pile up after the
    // tab is backgrounded and refocused.
    function scheduleNext() {
      pendingTimer = setTimeout(tick, DWELL_MS);
    }

    function tick() {
      if (document.hidden) {
        scheduleNext();
        return;
      }
      var next = (current + 1) % PAIRINGS.length;
      var tl = gsap.timeline({ onComplete: scheduleNext });
      tl.to(targets, { opacity: 0, y: -4, duration: FADE_S, ease: 'power3.out' })
        .add(function () { apply(PAIRINGS[next]); })
        .fromTo(targets,
          { opacity: 0, y: 4 },
          { opacity: 1, y: 0, duration: FADE_S, ease: 'power3.out' });
      current = next;
    }

    document.addEventListener('visibilitychange', function () {
      if (document.hidden && pendingTimer) {
        clearTimeout(pendingTimer);
        pendingTimer = null;
      } else if (!document.hidden && !pendingTimer) {
        scheduleNext();
      }
    });

    scheduleNext();
  }

  // ---------- Form submission ----------

  var state = { signupId: null, budgetBucket: 'mid' };

  function showThanks() {
    document.getElementById('signup-form').classList.add('is-hidden');
    var thanks = document.getElementById('thanks-state');
    if (thanks) { thanks.hidden = false; return; }
    // Hub pages have no qualifier flow — just show the inline confirmation.
    var confirm = document.getElementById('signup-confirm');
    if (confirm) confirm.hidden = false;
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

      // Hub pages carry a hidden hub_city so signups can be attributed to the city.
      var payload = { email: email };
      var hubCity = form.querySelector('input[name="hub_city"]');
      if (hubCity && hubCity.value) payload.hub_city = hubCity.value;

      fetch('/api/signup', {
        method: 'POST',
        // Accept JSON so the server returns the signup_id instead of a 303 redirect
        // to /thanks.html (the no-JS fallback). Without this the success path never runs.
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify(payload)
      })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, body: j }; }); })
      .then(function (res) {
        if (!res.ok) {
          btn.disabled = false;
          btn.textContent = 'Notify me';
          emailInput.focus();
          return;
        }
        state.signupId = res.body.signup_id;
        showThanks();
      })
      .catch(function () {
        btn.disabled = false;
        btn.textContent = 'Notify me';
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
    initHeadlineRotation();
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

