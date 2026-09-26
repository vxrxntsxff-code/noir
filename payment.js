const params = new URLSearchParams(location.search);
const order = params.get('order');
const accessToken = params.get('token') || '';
const ALLOWED_PAY_HOSTS = ['tinkoff.ru', 't-bank.ru', 'www.tinkoff.ru'];

function show(id) {
  document.querySelectorAll('[id^="view-"]').forEach(v => v.classList.add('hidden'));
  document.getElementById(id).classList.remove('hidden');
}

function fmt(n) {
  n = parseInt(n) || 0;
  return n.toLocaleString('ru-RU') + ' ₽';
}

function showErrorBanner(message) {
  let banner = document.getElementById('error-banner');
  if (!banner) {
    banner = document.createElement('div');
    banner.id = 'error-banner';
    banner.setAttribute('role', 'alert');
    banner.style.cssText = 'background:#3a1d1d;border:1px solid #E53935;color:#ECECE6;border-radius:12px;padding:12px 16px;margin-bottom:16px;font-size:14px;text-align:center';
    const card = document.getElementById('card');
    card.prepend(banner);
  }
  banner.textContent = message;
}

function isAllowedPayLink(url) {
  try {
    const u = new URL(url);
    if (u.protocol !== 'https:') return false;
    return ALLOWED_PAY_HOSTS.includes(u.hostname);
  } catch {
    return false;
  }
}

// Ссылка только из ответа API (pay_link/payment_url/link).
// ?paylink= используется лишь как fallback при отсутствии ссылки в API
// и только если host входит в allowlist.
function resolvePayLink(apiData) {
  const apiLink = apiData && (apiData.pay_link || apiData.payment_url || apiData.link);
  if (apiLink) {
    return isAllowedPayLink(apiLink) ? apiLink : null;
  }
  const paramLink = params.get('paylink');
  if (!paramLink) return null;
  return isAllowedPayLink(paramLink) ? paramLink : null;
}

function applyPayLink(payLink) {
  const payLinkEl = document.getElementById('pay-link');
  payLinkEl.href = payLink;
  document.getElementById('qr-img').src = 'https://api.qrserver.com/v1/create-qr-code/?size=432x432&data=' + encodeURIComponent(payLink);
  let hostEl = document.getElementById('pay-host');
  if (!hostEl) {
    hostEl = document.createElement('div');
    hostEl.id = 'pay-host';
    hostEl.className = 'status-sub';
    hostEl.style.margin = '12px 0 16px';
    document.getElementById('qr-wrap').after(hostEl);
  }
  try {
    hostEl.textContent = 'Оплата: ' + new URL(payLink).hostname;
  } catch {
    hostEl.textContent = '';
  }
}

function showInvalidPayLink() {
  show('view-fail');
  const sub = document.querySelector('#view-fail .status-sub');
  if (sub) sub.textContent = 'Некорректная ссылка оплаты';
}

function fillAmounts() {
  const amount = params.get('amount') || '29000';
  const amountNum = parseInt(amount.replace(/\D/g, '')) || 29000;
  const advance = Math.floor(amountNum / 2);
  const remaining = amountNum - advance;

  document.getElementById('amount').textContent = fmt(amountNum);
  document.getElementById('advance').textContent = fmt(advance);
  document.getElementById('remaining').textContent = fmt(remaining);
  document.getElementById('project-name').textContent = params.get('name') || 'Оплата проекта';
  document.getElementById('payment-desc').textContent = params.get('package') || 'NOIR OS';
  document.getElementById('order-id').textContent = order;
}

async function loadPayment(orderId) {
  document.getElementById('order-id').textContent = orderId || '—';
  const resp = await fetch('/api/payment_status?order=' + encodeURIComponent(orderId) + '&token=' + encodeURIComponent(accessToken));
  if (!resp.ok) throw new Error('fetch failed');
  return resp.json();
}

if (order) {
  show('view-loading');
  loadPayment(order)
    .then(d => {
      if (d.status === 'paid') { show('view-success'); return; }

      fillAmounts();

      const payLink = resolvePayLink(d);
      if (!payLink) { showInvalidPayLink(); return; }
      applyPayLink(payLink);

      show('view-payment');
    })
    .catch(() => {
      // Fallback: показать оплату по URL-параметрам, но с видимым баннером об ошибке загрузки
      showErrorBanner('Не удалось загрузить данные оплаты. Показаны предварительные данные.');
      fillAmounts();

      const payLink = resolvePayLink(null);
      if (!payLink) { showInvalidPayLink(); return; }
      applyPayLink(payLink);

      show('view-payment');
    });
} else {
  show('view-fail');
}

const paidBtn = document.getElementById('btn-paid');
if (paidBtn) {
  paidBtn.addEventListener('click', () => {
    show('view-loading');
    fetch('/api/payment_confirm', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({action: 'payment_confirm', order_id: order}),
    })
      .then(r => r.json())
      .then(d => {
        if (d.ok) show('view-pending');
        else show('view-fail');
      })
      .catch(() => show('view-fail'));
  });
}

const refreshBtn = document.getElementById('btn-refresh');
if (refreshBtn) {
  refreshBtn.addEventListener('click', () => location.reload());
}

const retryBtn = document.getElementById('btn-retry');
if (retryBtn) {
  retryBtn.addEventListener('click', () => location.reload());
}
