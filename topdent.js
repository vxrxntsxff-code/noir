(function () {
  'use strict';
  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ── Шапка ── */
  const topbar = document.getElementById('topbar');
  const onScroll = () => topbar.classList.toggle('scrolled', window.scrollY > 24);
  onScroll();
  window.addEventListener('scroll', onScroll, { passive: true });

  /* ── Мобильное меню ── */
  const burger = document.getElementById('burger');
  const menu = document.getElementById('mobileMenu');
  function closeMenu() {
    menu.classList.remove('open');
    burger.classList.remove('open');
    burger.setAttribute('aria-expanded', 'false');
    document.body.classList.remove('locked');
  }
  burger.addEventListener('click', () => {
    const open = menu.classList.toggle('open');
    burger.classList.toggle('open', open);
    burger.setAttribute('aria-expanded', String(open));
    document.body.classList.toggle('locked', open);
  });
  menu.querySelectorAll('a').forEach(a => a.addEventListener('click', closeMenu));
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeMenu(); });

  /* ── Живые окна: выбор времени → предзаполнение формы ── */
  const chips = document.querySelectorAll('#heroSlots .slot-chip');
  chips.forEach(chip => {
    chip.addEventListener('click', () => {
      chips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      const msg = document.getElementById('f-msg');
      if (msg && !msg.value.trim()) msg.value = 'Хочу записаться сегодня в ' + chip.dataset.time + '.';
      document.getElementById('book').scrollIntoView({ behavior: prefersReduced ? 'auto' : 'smooth' });
      const name = document.getElementById('f-name');
      if (name) setTimeout(() => name.focus({ preventScroll: true }), prefersReduced ? 0 : 650);
    });
  });

  /* ── Появление при скролле (включая подчёркивание утверждения) ── */
  const revealEls = document.querySelectorAll('[data-reveal]');
  if (prefersReduced || !('IntersectionObserver' in window)) {
    revealEls.forEach(el => el.classList.add('revealed'));
  } else {
    const io = new IntersectionObserver(entries => {
      entries.forEach(en => { if (en.isIntersecting) { en.target.classList.add('revealed'); io.unobserve(en.target); } });
    }, { threshold: 0.15, rootMargin: '0px 0px -40px 0px' });
    revealEls.forEach(el => io.observe(el));
  }

  /* ── Счётчики ── */
  const counters = document.querySelectorAll('[data-count]');
  function setFinal(el) { el.textContent = (el.dataset.prefix || '') + el.dataset.count + (el.dataset.suffix || ''); }
  function animateCount(el) {
    const target = parseFloat(el.dataset.count);
    const prefix = el.dataset.prefix || '', suffix = el.dataset.suffix || '';
    const dur = 1500, start = performance.now();
    function step(now) {
      const p = Math.min((now - start) / dur, 1);
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
      entries.forEach(en => { if (en.isIntersecting) { animateCount(en.target); cio.unobserve(en.target); } });
    }, { threshold: 0.5 });
    counters.forEach(el => cio.observe(el));
  }

  /* ── Аккордеон ── */
  document.querySelectorAll('.faq-item').forEach(item => {
    const btn = item.querySelector('.faq-q');
    btn.addEventListener('click', () => {
      const open = item.classList.toggle('open');
      btn.setAttribute('aria-expanded', String(open));
      document.querySelectorAll('.faq-item.open').forEach(o => {
        if (o !== item) { o.classList.remove('open'); o.querySelector('.faq-q').setAttribute('aria-expanded', 'false'); }
      });
    });
  });

  /* ── Плавающая запись: показать после скролла, скрыть у формы ── */
  const floatCta = document.getElementById('floatCta');
  const bookSection = document.getElementById('book');
  if (floatCta && 'IntersectionObserver' in window) {
    let nearForm = false;
    const bio = new IntersectionObserver(entries => {
      entries.forEach(en => { nearForm = en.isIntersecting; });
    }, { threshold: 0.1 });
    bio.observe(bookSection);
    window.addEventListener('scroll', () => {
      const show = window.scrollY > 640 && !nearForm;
      floatCta.classList.toggle('show', show);
    }, { passive: true });
  }

  /* ── Форма ── */
  const form = document.getElementById('bookForm');
  if (form) {
    form.addEventListener('submit', e => {
      e.preventDefault();
      if (!form.checkValidity()) { form.reportValidity(); return; }
      const data = Object.fromEntries(new FormData(form));
      const btn = form.querySelector('.form-submit');
      const note = form.querySelector('.form-note');
      const def = note.textContent;
      btn.disabled = true; btn.textContent = 'Отправляем…';

      fetch('/api/bot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ _form: { ...data, source: 'topdent' } }),
      }).then(res => {
        if (!res.ok) throw new Error();
        form.classList.add('sent');
        btn.textContent = 'Заявка отправлена';
        note.textContent = 'Перезвоним в течение 10 минут в рабочее время.';
        form.reset();
        chips.forEach(c => c.classList.remove('active'));
        setTimeout(() => { form.classList.remove('sent'); btn.disabled = false; btn.textContent = 'Записаться на приём'; note.textContent = def; }, 6000);
      }).catch(() => {
        btn.disabled = false;
        btn.textContent = 'Записаться на приём';
        note.textContent = 'Ошибка отправки. Попробуйте снова.';
      });
    });
  }

  /* ── Год ── */
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