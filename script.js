(function () {
  'use strict';

  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Шапка при скролле ─────────────────── */
  const nav = document.getElementById('nav');
  const onScroll = () => nav.classList.toggle('scrolled', window.scrollY > 24);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  /* ── Мобильное меню ────────────────────── */
  const burger = document.getElementById('burger');
  const menu = document.getElementById('mobileMenu');

  function closeMenu() {
    menu.classList.remove('open');
    burger.classList.remove('open');
    burger.setAttribute('aria-expanded', 'false');
    burger.setAttribute('aria-label', 'Открыть меню');
    document.body.classList.remove('locked');
  }

  burger.addEventListener('click', () => {
    const open = menu.classList.toggle('open');
    burger.classList.toggle('open', open);
    burger.setAttribute('aria-expanded', String(open));
    burger.setAttribute('aria-label', open ? 'Закрыть меню' : 'Открыть меню');
    document.body.classList.toggle('locked', open);
  });

  menu.querySelectorAll('a').forEach(a => a.addEventListener('click', closeMenu));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });

  /* ── Появление блоков при скролле ──────── */
  const revealEls = document.querySelectorAll('[data-reveal]');
  if (prefersReduced || !('IntersectionObserver' in window)) {
    revealEls.forEach(el => el.classList.add('revealed'));
  } else {
    const io = new IntersectionObserver(entries => {
      entries.forEach(en => {
        if (en.isIntersecting) { en.target.classList.add('revealed'); io.unobserve(en.target); }
      });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach(el => io.observe(el));
  }

  /* ── Счётчики ──────────────────────────── */
  const counters = document.querySelectorAll('[data-count]');

  function setFinal(el) {
    el.textContent = (el.dataset.prefix || '') + el.dataset.count + (el.dataset.suffix || '');
  }

  function animateCount(el) {
    const target = parseFloat(el.dataset.count);
    const prefix = el.dataset.prefix || '';
    const suffix = el.dataset.suffix || '';
    const duration = 1400;
    const start = performance.now();

    function step(now) {
      const p = Math.min((now - start) / duration, 1);
      const eased = 1 - Math.pow(1 - p, 3);
      el.textContent = prefix + Math.round(target * eased) + suffix;
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  if (prefersReduced || !('IntersectionObserver' in window)) {
    counters.forEach(setFinal);
  } else {
    const cio = new IntersectionObserver(entries => {
      entries.forEach(en => {
        if (en.isIntersecting) { animateCount(en.target); cio.unobserve(en.target); }
      });
    }, { threshold: 0.5 });
    counters.forEach(el => cio.observe(el));
  }

  /* ── Аккордеон вопросов ────────────────── */
  document.querySelectorAll('.faq-item').forEach(item => {
    const btn = item.querySelector('.faq-q');
    btn.addEventListener('click', () => {
      const open = item.classList.toggle('open');
      btn.setAttribute('aria-expanded', String(open));
      document.querySelectorAll('.faq-item.open').forEach(other => {
        if (other !== item) {
          other.classList.remove('open');
          other.querySelector('.faq-q').setAttribute('aria-expanded', 'false');
        }
      });
    });
  });

  /* ── Подсветка активного пункта меню ───── */
  const sections = document.querySelectorAll('main section[id]');
  const navLinks = document.querySelectorAll('.nav-link[data-nav]');
  if ('IntersectionObserver' in window && navLinks.length) {
    const sio = new IntersectionObserver(entries => {
      entries.forEach(en => {
        if (en.isIntersecting) {
          navLinks.forEach(l => l.classList.toggle('active', l.dataset.nav === en.target.id));
        }
      });
    }, { rootMargin: '-45% 0px -50% 0px' });
    sections.forEach(s => sio.observe(s));
  }

  /* ── Форма заявки ──────────────────────── */
  const form = document.getElementById('contactForm');
  if (form) {
    form.addEventListener('submit', e => {
      e.preventDefault();
      if (!form.checkValidity()) { form.reportValidity(); return; }

      const data = Object.fromEntries(new FormData(form));

      const btn = form.querySelector('.form-submit');
      const note = form.querySelector('.form-note');
      const defaultNote = note.textContent;

      btn.disabled = true;
      btn.textContent = 'Отправляем…';

      fetch('/api/bot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ _form: data }),
      }).catch(() => {}).finally(() => {
        form.classList.add('sent');
        btn.textContent = 'Заявка отправлена ✓';
        note.textContent = 'Ответим в течение 15 минут в рабочее время.';
        form.reset();
        setTimeout(() => {
          form.classList.remove('sent');
          btn.disabled = false;
          btn.textContent = 'Получить расчёт';
          note.textContent = defaultNote;
        }, 6000);
      });
    });
  }

  /* ── Год в подвале ─────────────────────── */
  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();
    /* ── Страховка раскрытия для Safari (bfcache + глюк IntersectionObserver) ── */
  function revealInView() {
    revealEls.forEach(el => {
      if (el.classList.contains('revealed')) return;
      const r = el.getBoundingClientRect();
      if (r.top < window.innerHeight && r.bottom > 0) el.classList.add('revealed');
    });
  }
  function revealAll() {
    revealEls.forEach(el => el.classList.add('revealed'));
    counters.forEach(setFinal);
  }
  // bfcache: Safari не стреляет load при возврате из кэша — чиним через pageshow
  window.addEventListener('pageshow', e => { if (e.persisted) revealAll(); });
  // первичная загрузка: раскрыть видимое, если IntersectionObserver не стрельнул
  if (document.readyState === 'complete') {
    revealInView();
  } else {
    window.addEventListener('load', () => { revealInView(); setTimeout(revealInView, 300); });
  }
  // первый скролл — раскрыть то, что попало в экран
  window.addEventListener('scroll', revealInView, { passive: true, once: true });
  // финальная страховка: через 2.5с раскрыть всё, что в экране
  setTimeout(revealInView, 2500);
})();