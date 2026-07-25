(() => {
  document.documentElement.classList.add('js');
  const toggle = document.querySelector('.nav-toggle');
  const navigation = document.querySelector('#site-navigation');
  if (toggle && navigation) {
    const close = (restoreFocus = false) => {
      navigation.dataset.open = 'false';
      toggle.setAttribute('aria-expanded', 'false');
      toggle.setAttribute('aria-label', 'Open menu');
      if (restoreFocus) toggle.focus();
    };
    toggle.addEventListener('click', () => {
      const opening = toggle.getAttribute('aria-expanded') !== 'true';
      navigation.dataset.open = String(opening);
      toggle.setAttribute('aria-expanded', String(opening));
      toggle.setAttribute('aria-label', opening ? 'Close menu' : 'Open menu');
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') close(true);
    });
    navigation.addEventListener('click', (event) => {
      if (event.target.closest('a')) close(false);
    });
  }

  const mobileActions = document.querySelector('.mobile-actions');
  if (mobileActions) {
    const suppressionReasons = new Set();
    const renderMobileActions = () => {
      const suppressed = suppressionReasons.size > 0;
      mobileActions.dataset.suppressed = String(suppressed);
      mobileActions.setAttribute('aria-hidden', String(suppressed));
    };
    const setSuppressed = (reason, suppressed) => {
      if (suppressed) suppressionReasons.add(reason);
      else suppressionReasons.delete(reason);
      renderMobileActions();
    };
    const heroActions = document.querySelector('.hero .actions, .home-hero-actions');
    if (heroActions && 'IntersectionObserver' in window) {
      setSuppressed('hero-actions-visible', true);
      const observer = new IntersectionObserver(([entry]) => {
        setSuppressed('hero-actions-visible', entry.isIntersecting);
      });
      observer.observe(heroActions);
    }
    const intakeForms = [...document.querySelectorAll('form[data-intake-form]')];
    if (intakeForms.length && 'IntersectionObserver' in window) {
      const visibleForms = new Set();
      const formObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) visibleForms.add(entry.target);
          else visibleForms.delete(entry.target);
        });
        setSuppressed('intake-form-visible', visibleForms.size > 0);
      }, {threshold: 0.01});
      intakeForms.forEach((form) => formObserver.observe(form));
    }
    const isFormControl = (element) => element?.matches('form input, form select, form textarea, form button');
    document.addEventListener('focusin', (event) => {
      if (isFormControl(event.target)) setSuppressed('form-control-focused', true);
    });
    document.addEventListener('focusout', () => {
      window.setTimeout(() => setSuppressed('form-control-focused', isFormControl(document.activeElement)), 0);
    });
    renderMobileActions();
  }

  const feed = document.querySelector('#updates-feed');
  if (feed) {
    const FRESHNESS_WINDOW_MS = 14 * 24 * 60 * 60 * 1000;
    const status = document.querySelector('#updates-status');
    const refresh = document.querySelector('#refresh-updates');
    const render = async () => {
      refresh?.setAttribute('aria-busy', 'true');
      try {
        const response = await fetch('/data/garden-grove-chemical-leak-updates.json', {cache: 'no-store'});
        if (!response.ok) throw new Error('Update feed unavailable');
        const data = await response.json();
        if (!data || !Array.isArray(data.updates) || !data.updates.length || typeof data.lastVerifiedUtc !== 'string') {
          throw new Error('Malformed update feed');
        }
        const verified = new Date(data.lastVerifiedUtc);
        if (Number.isNaN(verified.getTime()) || data.updates.some((item) => !item || !item.timeUtc || Number.isNaN(Date.parse(item.timeUtc)) || !item.title || !item.summary || !item.sourceLabel || !item.sourceUrl)) {
          throw new Error('Malformed update feed');
        }
        feed.replaceChildren(...data.updates.map((item) => {
          const li = document.createElement('li');
          const time = document.createElement('time');
          const heading = document.createElement('h3');
          const summary = document.createElement('p');
          const link = document.createElement('a');
          time.dateTime = item.timeUtc;
          time.textContent = new Date(item.timeUtc).toLocaleDateString('en-US', {year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC'});
          heading.textContent = item.title;
          summary.textContent = item.summary;
          link.href = item.sourceUrl;
          link.textContent = `Source: ${item.sourceLabel}`;
          link.target = '_blank';
          link.rel = 'noopener noreferrer';
          li.append(time, heading, summary, link);
          return li;
        }));
        const verifiedLabel = verified.toLocaleDateString('en-US', {year: 'numeric', month: 'long', day: 'numeric', timeZone: 'UTC'});
        const stale = Date.now() - verified.getTime() > FRESHNESS_WINDOW_MS;
        status.classList.toggle('feed-status--stale', stale);
        status.dataset.feedState = stale ? 'stale' : 'fresh';
        status.setAttribute('role', stale ? 'alert' : 'status');
        status.textContent = stale
          ? `Update feed is stale. Last verified ${verifiedLabel}. Follow the official City and County sources below for current instructions.`
          : `Update feed last verified ${verifiedLabel}. Official emergency sources remain primary.`;
      } catch (error) {
        const malformed = error.message === 'Malformed update feed';
        status.classList.add('feed-status--stale');
        status.dataset.feedState = malformed ? 'malformed' : 'unavailable';
        status.setAttribute('role', 'alert');
        status.textContent = malformed
          ? 'The stored update feed is malformed and cannot be verified. Use the cited official City and County sources below for current instructions.'
          : 'The local update feed is unavailable. Use the cited official City and County sources below for current instructions.';
      } finally {
        refresh?.removeAttribute('aria-busy');
      }
    };
    refresh?.addEventListener('click', render);
    render();
  }
})();

/*
 * Native scroll motion. Content is fully visible before this runs and stays visible
 * if it never runs: the `motion` class on <html> is the only thing that hides or
 * offsets anything, and it is added only when IntersectionObserver, requestAnimationFrame,
 * and a no-preference reduced-motion setting are all present. Any failure removes the
 * class and restores the final state. Scrolling is never intercepted.
 */
(() => {
  const root = document.documentElement;
  const OBSERVER_FALLBACK_MS = 1600;

  const revealEverything = () => {
    document.querySelectorAll('[data-reveal]').forEach((element) => {
      element.dataset.revealed = 'true';
    });
    document.querySelectorAll('[data-timeline-step]').forEach((step) => {
      step.dataset.active = 'true';
    });
    document.querySelectorAll('[data-timeline]').forEach((section) => {
      section.style.setProperty('--timeline-progress', '1');
    });
  };

  const failOpen = () => {
    root.classList.remove('motion');
    revealEverything();
  };

  try {
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const capable = 'IntersectionObserver' in window && typeof window.requestAnimationFrame === 'function';
    if (!capable) return;

    const reveals = [...document.querySelectorAll('[data-reveal]')];
    const heroes = [...document.querySelectorAll('[data-hero]')];
    const timelines = [...document.querySelectorAll('[data-timeline]')];
    let running = false;
    let ticking = false;
    let observer = null;

    const clamp = (value) => Math.min(1, Math.max(0, value));

    const update = () => {
      ticking = false;
      if (!running) return;
      const scrollable = root.scrollHeight - window.innerHeight;
      const offset = window.scrollY || window.pageYOffset || 0;
      root.style.setProperty('--scroll-progress', (scrollable > 0 ? clamp(offset / scrollable) : 0).toFixed(4));
      heroes.forEach((hero) => {
        const rect = hero.getBoundingClientRect();
        const shift = rect.bottom > 0 ? Math.min(52, Math.max(0, -rect.top) * 0.11) : 52;
        hero.style.setProperty('--hero-parallax', `${shift.toFixed(2)}px`);
      });
      timelines.forEach((section) => {
        const track = section.querySelector('.case-track');
        if (!track) return;
        const rect = track.getBoundingClientRect();
        const anchor = window.innerHeight * 0.62;
        section.style.setProperty('--timeline-progress', clamp((anchor - rect.top) / Math.max(1, rect.height)).toFixed(4));
        section.querySelectorAll('[data-timeline-step]').forEach((step) => {
          step.dataset.active = String(step.getBoundingClientRect().top + 24 <= anchor);
        });
      });
    };

    const onScroll = () => {
      if (ticking || !running) return;
      ticking = true;
      window.requestAnimationFrame(update);
    };

    const start = () => {
      if (running) return;
      running = true;
      root.classList.add('motion');
      document.querySelectorAll('[data-reveal-group]').forEach((group) => {
        [...group.children].forEach((child, index) => {
          const target = child.matches('[data-reveal]') ? child : child.querySelector('[data-reveal]');
          if (target) target.dataset.stagger = String(Math.min(index + 1, 6));
        });
      });
      observer = new IntersectionObserver((entries, self) => {
        entries.forEach((entry) => {
          if (!entry.isIntersecting) return;
          entry.target.dataset.revealed = 'true';
          self.unobserve(entry.target);
        });
      }, {rootMargin: '0px 0px -6% 0px', threshold: 0.04});
      reveals.forEach((element) => observer.observe(element));
      window.addEventListener('scroll', onScroll, {passive: true});
      window.addEventListener('resize', onScroll, {passive: true});
      window.addEventListener('orientationchange', onScroll, {passive: true});
      update();
      if (reveals.length) {
        window.setTimeout(() => {
          if (!running) return;
          const missedVisibleTarget = reveals.some((element) => {
            if (element.dataset.revealed === 'true') return false;
            const rect = element.getBoundingClientRect();
            return rect.top < window.innerHeight && rect.bottom > 0;
          });
          if (missedVisibleTarget) failOpen();
        }, OBSERVER_FALLBACK_MS);
      }
    };

    const stop = () => {
      running = false;
      if (observer) observer.disconnect();
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onScroll);
      window.removeEventListener('orientationchange', onScroll);
      failOpen();
    };

    const applyPreference = () => {
      if (reduceMotion.matches) stop();
      else start();
    };

    if (typeof reduceMotion.addEventListener === 'function') reduceMotion.addEventListener('change', applyPreference);
    else if (typeof reduceMotion.addListener === 'function') reduceMotion.addListener(applyPreference);
    applyPreference();
  } catch (error) {
    failOpen();
  }
})();
