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
