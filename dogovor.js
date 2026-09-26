(function () {
  // Предзаполнение из параметров ссылки:
  // dogovor.html?name=...&phone=...&task=...&price=...&date=...&num=...&tg=...&email=...&city...
  // или dogovor.html?c=SHORTCODE для короткой ссылки
  var p = new URLSearchParams(window.location.search);
  var shortCode = p.get('c');

  function showLoadError() {
    if (document.getElementById('contract-load-error')) return;
    var banner = document.createElement('div');
    banner.id = 'contract-load-error';
    banner.setAttribute('role', 'alert');
    banner.style.cssText = 'max-width:800px;margin:16px auto;padding:12px 16px;background:#fef2f2;border:1px solid #fca5a5;color:#991b1b;border-radius:8px;font-size:14px;text-align:center';
    banner.textContent = 'Не удалось загрузить данные договора. Проверьте ссылку или заполните поля вручную.';
    var toolbar = document.querySelector('.doc-toolbar');
    if (toolbar && toolbar.parentNode) {
      toolbar.parentNode.insertBefore(banner, toolbar.nextSibling);
    } else {
      document.body.insertBefore(banner, document.body.firstChild);
    }
  }

  function fillForm(data) {
    var map = {
      'client-name': data.name || p.get('name'),
      'client-name-2': data.name || p.get('name'),
      'client-phone': data.phone || p.get('phone'),
      'client-phone-2': data.phone || p.get('phone'),
      'client-task': data.task || p.get('task'),
      'deal-price': data.price || p.get('price'),
      'deal-date': data.date || p.get('date'),
      'deal-num': data.num || p.get('num'),
      'client-tg': data.tg || p.get('tg'),
      'client-email': data.email || p.get('email'),
      'client-city': data.city || p.get('city'),
      'support-duration': data.support || p.get('support')
    };
    for (var id in map) {
      if (Object.prototype.hasOwnProperty.call(map, id)) {
        var el = document.getElementById(id);
        var val = map[id];
        if (el && val) el.textContent = val;
      }
    }

    var taskEl = document.getElementById('client-task');
    if (taskEl && !taskEl.textContent.trim()) {
      var pkg = ((data.package || p.get('package')) || '').toLowerCase();
      var tasks = {
        'старт': 'Разработка лендинга, Telegram-бот и подключение CRM',
        'бизнес': 'Разработка сайта, Telegram-бот, подключение CRM и AI-ассистента',
        'премиум': 'Разработка сайта, Telegram-бот, CRM, AI-ассистент и подключение онлайн-оплаты'
      };
      var fallback = 'Разработка цифровых продуктов для бизнеса';
      taskEl.textContent = tasks[pkg] || fallback;
    }

    var payment = data.payment || p.get('payment');
    var paymentEl = document.getElementById('deal-payment');
    if (paymentEl && payment === 'full') {
      paymentEl.innerHTML = 'Порядок оплаты: 100% &mdash; предоплата до начала работ.';
    } else if (paymentEl && payment === 'stages') {
      paymentEl.innerHTML = 'Порядок оплаты по этапам: 50% &mdash; предоплата до начала работ, 50% &mdash; после сдачи результата.';
    }
  }

  if (shortCode) {
    fetch('/api/contract?c=' + encodeURIComponent(shortCode))
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (data) {
          fillForm(data);
        } else {
          fillForm({});
          showLoadError();
        }
      })
      .catch(function () {
        fillForm({});
        showLoadError();
      });
  } else {
    fillForm({});
  }

  var printBtn = document.getElementById('printBtn');
  if (printBtn) {
    printBtn.addEventListener('click', function () { window.print(); });
  }

  /* Страховка от «белой страницы» в Safari при переходе по ссылке.
     Форсит перерисовку, когда документ пришёл из навигации / кэша. */
  function repaint() {
    var d = document.documentElement;
    d.style.opacity = '0.999';
    requestAnimationFrame(function () { d.style.opacity = ''; });
  }
  window.addEventListener('pageshow', repaint);
  window.addEventListener('load', repaint);
  /* если Safari всё же схлопнул слой — чиним по первому скроллу/движению */
  var once = function () { repaint(); window.removeEventListener('scroll', once); };
  window.addEventListener('scroll', once, { passive: true });
})();
