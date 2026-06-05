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
  // The pairings (origin city + verified cheap/anchor) drive the rotating hero
  // and geo personalization. The authoritative list is generated from the
  // VERIFIED city_pairings into /pairings.js (window.PROMPTIV_PAIRINGS) so the
  // homepage tracks the fact monitor and never shows an unverified claim. This
  // built-in copy is only a fallback if that file fails to load, so the hero
  // never goes blank. lat/lng = airport coords; cheap/anchor = punchy display.
  var FALLBACK_PAIRINGS = [
    { city: 'Nashville',     slug: 'nashville',     lat: 36.124, lng:  -86.678, cheap: 'Medellín',       anchor: 'Vegas' },
    { city: 'New York',      slug: 'new-york',      lat: 40.641, lng:  -73.778, cheap: 'Mexico City',    anchor: 'Honolulu' },
    { city: 'Los Angeles',   slug: 'los-angeles',   lat: 33.942, lng: -118.409, cheap: 'Oaxaca',         anchor: 'Cabo' },
    { city: 'Atlanta',       slug: 'atlanta',       lat: 33.641, lng:  -84.428, cheap: 'Cartagena',      anchor: 'Jackson Hole' },
    { city: 'Dallas',        slug: 'dallas',        lat: 32.900, lng:  -97.040, cheap: 'Mérida',         anchor: 'Cabo' },
    { city: 'Chicago',       slug: 'chicago',       lat: 41.974, lng:  -87.907, cheap: 'Guatemala City', anchor: 'Honolulu' },
    { city: 'Miami',         slug: 'miami',         lat: 25.796, lng:  -80.287, cheap: 'Lima',           anchor: 'Aruba' },
    { city: 'Seattle',       slug: 'seattle',       lat: 47.450, lng: -122.309, cheap: 'Panama City',    anchor: 'Honolulu' },
    { city: 'Denver',        slug: 'denver',        lat: 39.856, lng: -104.674, cheap: 'Bogotá',         anchor: 'Jackson Hole' },
    { city: 'Houston',       slug: 'houston',       lat: 29.990, lng:  -95.337, cheap: 'San José',       anchor: 'Jackson Hole' },
    { city: 'San Francisco', slug: 'san-francisco', lat: 37.621, lng: -122.379, cheap: 'Sofia',          anchor: 'Jackson Hole' },
    { city: 'Boston',        slug: 'boston',        lat: 42.366, lng:  -71.010, cheap: 'Cairo',          anchor: 'Honolulu' }
  ];
  var PAIRINGS = (window.PROMPTIV_PAIRINGS && window.PROMPTIV_PAIRINGS.length)
    ? window.PROMPTIV_PAIRINGS : FALLBACK_PAIRINGS;

  // Returns a controller { pinTo(index) } so geo personalization can stop the
  // rotation and settle the hero on the visitor's city. Returns null off-homepage.
  function initHeadlineRotation() {
    var cheapEl = document.getElementById('rh-cheap');
    var anchorEl = document.getElementById('rh-anchor');
    var cityEl = document.getElementById('rh-city');
    if (!cheapEl || !anchorEl || !cityEl) return null;

    function apply(p) {
      cheapEl.textContent = p.cheap;
      anchorEl.textContent = p.anchor;
      cityEl.textContent = p.city;
    }
    apply(PAIRINGS[0]);

    var targets = [cheapEl, anchorEl, cityEl];
    var current = 0;
    var pinned = false;
    var DWELL_MS = 3500;
    var FADE_S = 0.35;
    var pendingTimer = null;

    var reduceMotion =
      window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var canAnimate = !(reduceMotion || typeof gsap === 'undefined');

    function fadeTo(p) {
      var tl = gsap.timeline();
      tl.to(targets, { opacity: 0, y: -4, duration: FADE_S, ease: 'power3.out' })
        .add(function () { apply(p); })
        .fromTo(targets, { opacity: 0, y: 4 }, { opacity: 1, y: 0, duration: FADE_S, ease: 'power3.out' });
    }

    // Stop rotating and settle on one city (geo personalization).
    function pinTo(idx) {
      pinned = true;
      if (pendingTimer) { clearTimeout(pendingTimer); pendingTimer = null; }
      current = idx;
      if (canAnimate && idx !== 0) { fadeTo(PAIRINGS[idx]); } else { apply(PAIRINGS[idx]); }
    }

    // No animation (reduced motion or no GSAP): first pairing is shown; geo can
    // still pin instantly. Nothing rotates.
    if (!canAnimate) { return { pinTo: pinTo }; }

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
      if (pinned) { return; }
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
      } else if (!document.hidden && !pendingTimer && !pinned) {
        scheduleNext();
      }
    });

    scheduleNext();
    return { pinTo: pinTo };
  }

  // ---------- Geo personalization ----------
  // Detect the visitor's nearest served city (within ~150mi) and swap the hero
  // to their city + a "see your city's trips" CTA. Fully client-side: the free
  // IP API rate-limits by caller IP, so each browser calling from its own IP
  // stays well under the limit (a server-side call would share one limit across
  // every visitor). Crawlers get the generic rotating hero (this runs in JS only).
  // Degrades silently: any failure or no city in range -> rotation keeps running.
  var GEO_MAX_MI = 150;

  function haversineMi(lat1, lng1, lat2, lng2) {
    var R = 3959, toRad = Math.PI / 180;
    var dLat = (lat2 - lat1) * toRad, dLng = (lng2 - lng1) * toRad;
    var a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * toRad) * Math.cos(lat2 * toRad) *
            Math.sin(dLng / 2) * Math.sin(dLng / 2);
    return 2 * R * Math.asin(Math.sqrt(a));
  }

  function nearestCityIndex(lat, lng, maxMi) {
    var best = -1, bestD = Infinity, i, d;
    for (i = 0; i < PAIRINGS.length; i++) {
      d = haversineMi(lat, lng, PAIRINGS[i].lat, PAIRINGS[i].lng);
      if (d < bestD) { bestD = d; best = i; }
    }
    return bestD <= maxMi ? best : -1;
  }

  function slugIndex(slug) {
    var i;
    for (i = 0; i < PAIRINGS.length; i++) {
      if (PAIRINGS[i].slug === slug) { return i; }
    }
    return -1;
  }

  // ?geo=<slug> or ?geo=<lat>,<lng> forces a location — used for testing and so
  // a visitor (or you) can preview any city. Bypasses the IP lookup when present.
  function geoOverrideIndex() {
    var m = /[?&]geo=([^&]+)/.exec(window.location.search);
    if (!m) { return null; }
    var val = decodeURIComponent(m[1]).trim();
    var bySlug = slugIndex(val.toLowerCase());
    if (bySlug >= 0) { return bySlug; }
    var parts = val.split(',');
    if (parts.length === 2) {
      var lat = parseFloat(parts[0]), lng = parseFloat(parts[1]);
      if (isFinite(lat) && isFinite(lng)) { return nearestCityIndex(lat, lng, GEO_MAX_MI); }
    }
    return -1;
  }

  function fetchGeoCoords() {
    return fetch('https://ipapi.co/json/', { cache: 'no-store' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (j) {
        if (!j) { return null; }
        var lat = parseFloat(j.latitude), lng = parseFloat(j.longitude);
        return (isFinite(lat) && isFinite(lng)) ? { lat: lat, lng: lng } : null;
      })
      .catch(function () { return null; });
  }

  function personalizeTo(idx, rotation) {
    var p = PAIRINGS[idx];
    rotation.pinTo(idx); // stop rotation, settle the hero on this city
    var eyebrow = document.getElementById('eyebrow-text');
    if (eyebrow) { eyebrow.textContent = 'Cheap trips from ' + p.city; }
    // Tag the signup with the detected city so a homepage signup subscribes to
    // that city's weekly digest (hub signups already carry hub_city).
    var cityField = document.getElementById('signup-city');
    if (cityField) { cityField.value = p.city; }
    var ctaGo = document.getElementById('cta-go');
    var ctaHub = document.getElementById('cta-hub');
    if (ctaHub) {
      ctaHub.setAttribute('href', '/' + p.slug);
      ctaHub.textContent = 'See ' + p.city + '’s trips →';
      ctaHub.hidden = false;
    }
    if (ctaGo) { ctaGo.hidden = true; }
  }

  function initGeoPersonalization(rotation) {
    if (!rotation) { return; } // homepage only

    var forced = geoOverrideIndex();
    if (forced !== null) {
      if (forced >= 0) { personalizeTo(forced, rotation); }
      return; // an explicit ?geo= means "don't also hit the network"
    }

    fetchGeoCoords().then(function (loc) {
      if (!loc) { return; } // fallback: rotation keeps running
      var idx = nearestCityIndex(loc.lat, loc.lng, GEO_MAX_MI);
      if (idx >= 0) { personalizeTo(idx, rotation); }
    });
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
    var rotation = initHeadlineRotation();
    initGeoPersonalization(rotation);
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

