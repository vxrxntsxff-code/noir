(function () {
  'use strict';

  /* ── Clean URL — убрать #hero, #services и т.д. из адресной строки ── */
  function hideHash() {
    if (window.location.hash) {
      window.history.replaceState(null, '', window.location.pathname + window.location.search);
    }
  }
  hideHash();

  // ponytail: убираем hash после скролла при клике на ссылки с #
  document.addEventListener('click', e => {
    const a = e.target.closest('a[href^=\"#"]');
    if (a) {
      setTimeout(hideHash, 1);
    }
  });
  window.addEventListener('hashchange', hideHash);

  const prefersReduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  if (prefersReduced) document.querySelector('.marquee')?.classList.add('paused');

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

  /* ── Автозаполнение услуги в форму ── */
  const serviceMap = {
    'site': 'Модуль «Сайт» — лендинг/корпоративный сайт/магазин. 35 000 ₽',
    'bot': 'Модуль «Бот» — запись, оплата, каталог в Telegram. 20 000 ₽',
    'crm': 'Модуль «CRM» — связь сайт, бот, телефония, 1С. 45 000 ₽',
    'ai': 'Модуль «AI» — чат-бот менеджер. 60 000 ₽',
    'payment': 'Модуль «Оплата» — Kassa или Т-Банк, СБП, чеки по 54-ФЗ. 10 000 ₽',
  };

  document.querySelectorAll('.service-row[data-service]').forEach(link => {
    link.addEventListener('click', () => {
      const serviceKey = link.getAttribute('data-service');
      const taskEl = document.getElementById('f-task');
      if (taskEl && serviceMap[serviceKey]) {
        taskEl.value = serviceMap[serviceKey];
      }
    });
  });
  const form = document.getElementById('contactForm');
  const payModal = document.getElementById('payModal');
  const modalChoose = document.getElementById('modal-choose');
  const modalPayForm = document.getElementById('modal-pay-form');
  const modalQr = document.getElementById('modal-qr');

  function showModal() {
    if (payModal) {
      payModal.style.display = 'flex';
      showStep(modalChoose);
    }
  }
  function closePayModal() {
    if (payModal) payModal.style.display = 'none';
    showStep(modalChoose);
  }
  function showStep(step) {
    [modalChoose, modalPayForm, modalQr].forEach(s => {
      if (s) {
        s.classList.remove('active');
        s.style.removeProperty('display');
      }
    });
    if (step) {
      step.classList.add('active');
      step.style.display = 'block';
    }
  }
  function showPayForm() {
    showStep(modalPayForm);
  }
  function showQr() {
    const nameEl = document.getElementById('pay-name');
    const phoneEl = document.getElementById('pay-phone');
    const tgEl = document.getElementById('pay-tg');
    const emailEl = document.getElementById('pay-email');

    if (!nameEl.value || !phoneEl.value || !tgEl.value || !emailEl.value) {
      alert('Заполните все поля');
      return;
    }

    showStep(modalQr);

    const paymentLink = 'https://www.tinkoff.ru/rm/r_SzKUZwgODe.kMlhwmbzwy/8yPZg94022';
    // ponytail: QR params synced with bot (app.py)
    const qrUrl = 'https://api.qrserver.com/v1/create-qr-code/?size=280x280&data=' + encodeURIComponent(paymentLink) + '&color=C9A96E&bgcolor=0B0B0D&margin=0&qzone=1&radius=20';

    const payLink = document.getElementById('modal-pay-link');
    if (payLink) payLink.href = paymentLink;

    const qrImg = document.getElementById('qr-code');
    if (qrImg) qrImg.src = qrUrl;
  }
  function markPaid() {
    const clientInfo = {
      name: document.getElementById('pay-name')?.value || '',
      phone: document.getElementById('pay-phone')?.value || '',
      telegram: document.getElementById('pay-tg')?.value || '',
      email: document.getElementById('pay-email')?.value || '',
      order_id: window.pendingOrderId || '',
      price: document.querySelector('.modal-step:where(#modal-qr) p')?.textContent.replace('Предоплата 50% — ', '') || '',
    };
    fetch('/api/payment_confirm', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({action: 'payment_confirm', ...clientInfo}),
    }).then(r => r.json()).then(d => {
      if (d.ok) {
        alert('Спасибо! Мы свяжемся с вами для подтверждения оплаты.');
      } else {
        alert('Ошибка подтверждения. Попробуйте снова.');
      }
    }).catch(() => {
      alert('Ошибка связи. Попробуйте снова.');
    }).finally(() => closePayModal());
  }
  window.closePayModal = closePayModal;
  window.showPayForm = showPayForm;
  window.showQr = showQr;
  window.markPaid = markPaid;

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
      }).then(async res => {
        if (!res.ok) throw new Error();
        const result = await res.json();

        form.classList.add('sent');
        btn.disabled = true;
        btn.textContent = 'Заявка отправлена';
        note.textContent = 'Ответим в течение 15 минут в рабочее время.';

        // Pre-fill payment form with client data
        const nameInput = document.getElementById('pay-name');
        if (nameInput) nameInput.value = data.name || '';
        const phoneInput = document.getElementById('pay-phone');
        if (phoneInput) phoneInput.value = data.contact || '';

        // Store order_id for markPaid()
        if (result.order_id) {
          window.pendingOrderId = result.order_id;
        }

        // Show modal with "Оплатить / Связаться"
        setTimeout(() => showModal(), 300);

        setTimeout(() => {
          form.classList.remove('sent');
          btn.disabled = false;
          btn.textContent = 'Запустить NOIR OS';
          note.textContent = defaultNote;
        }, 8000);
      }).catch(() => {
        btn.disabled = false;
        btn.textContent = 'Запустить NOIR OS';
        note.textContent = 'Ошибка отправки. Попробуйте снова.';
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