const params = new URLSearchParams(location.search);
const urlToken = params.get('token') || params.get('t');

// Safe storage: localStorage with in-memory fallback (private Safari throws SecurityError)
const memStore = {};
function safeGet(key) {
  try {
    return localStorage.getItem(key);
  } catch (e) {
    return Object.prototype.hasOwnProperty.call(memStore, key) ? memStore[key] : null;
  }
}
function safeSet(key, value) {
  try {
    localStorage.setItem(key, value);
  } catch (e) {
    memStore[key] = value;
  }
}
function safeRemove(key) {
  try {
    localStorage.removeItem(key);
  } catch (e) {
    delete memStore[key];
  }
}

// Persist token from URL, then scrub it from history/Referer
if (urlToken) {
  safeSet('noir_token', urlToken);
  try {
    history.replaceState(null, '', location.pathname);
  } catch (e) {}
}
const token = urlToken || safeGet('noir_token');

const STAGES = [
  {key:'brief', label:'Бриф'},
  {key:'research', label:'Исследование'},
  {key:'design', label:'Дизайн'},
  {key:'development', label:'Разработка'},
  {key:'integrations', label:'Интеграции'},
  {key:'launch', label:'Запуск'},
];

function showLogin() {
  document.getElementById('login-view').style.display = 'block';
  document.getElementById('dashboard').style.display = 'none';
}

function showErrorBanner(message) {
  let el = document.getElementById('dash-error');
  if (!el) {
    el = document.createElement('div');
    el.id = 'dash-error';
    el.setAttribute('role', 'alert');
    el.style.cssText = 'max-width:1000px;margin:16px auto 0;padding:14px 18px;background:rgba(255,60,60,.1);border:1px solid rgba(255,60,60,.4);border-radius:12px;color:#ff8a8a;font-size:14px';
    const app = document.getElementById('app');
    if (app && app.firstChild) app.insertBefore(el, app.firstChild);
    else document.body.prepend(el);
  }
  el.textContent = message;
  el.style.display = 'block';
}

function hideErrorBanner() {
  const el = document.getElementById('dash-error');
  if (el) el.style.display = 'none';
}

function showDashboard(data) {
  hideErrorBanner();
  document.getElementById('login-view').style.display = 'none';
  document.getElementById('dashboard').style.display = 'block';

  document.getElementById('project-name').textContent = data.project_name || 'Проект';
  document.getElementById('project-package').textContent = data.package || '';

  const pct = data.progress || 0;
  document.getElementById('progress-fill').style.width = pct + '%';
  document.getElementById('progress-text').textContent = pct + '%';

  document.getElementById('payment-total').textContent = data.price || '—';
  document.getElementById('payment-paid').textContent = data.paid && data.paid != '0' ? data.paid : '—';
  document.getElementById('payment-remaining').textContent = data.remaining || '—';

   // Helper: escape HTML to prevent XSS
   function esc(s){return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');}

   // Allow only http(s):// and relative URLs ("/..." or scheme-less). Block javascript:, data:, etc.
   function isSafeDocUrl(u) {
     const v = String(u ?? '').trim();
     if (!v) return false;
     if (/^https?:\/\//i.test(v)) return true;
     if (v.startsWith('//')) return false;
     if (v.startsWith('/')) return true;
     if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(v)) return false;
     return true;
   }
   function isExternalHttp(u) {
     return /^https?:\/\//i.test(String(u ?? '').trim());
   }

   const timeline = document.getElementById('timeline');
   timeline.innerHTML = '';
   const stageToKey = {
     'Бриф': 'brief', 'Исследование': 'research', 'Дизайн': 'design',
     'Разработка': 'development', 'Интеграции': 'integrations', 'Запуск': 'launch',
   };
   const currentStage = stageToKey[data.stage] || data.stage || 'brief';
   let reached = false;
   STAGES.forEach(s => {
     const li = document.createElement('li');
     let dotClass = 'dot-pending';
     if (!reached && s.key !== currentStage) dotClass = 'dot-done';
     if (s.key === currentStage) { dotClass = 'dot-current'; reached = true; }
     li.innerHTML = `<span class="dot ${dotClass}"></span><span class="label">${esc(s.label)}</span>`;
     timeline.appendChild(li);
   });

   const docs = document.getElementById('docs');
   docs.innerHTML = '';
   (data.docs || []).forEach(d => {
     const li = document.createElement('li');
     if (isSafeDocUrl(d.url)) {
       const rel = isExternalHttp(d.url) ? ' rel="noopener"' : '';
       li.innerHTML = `<span>${esc(d.name)}</span><a class="doc-link" href="${esc(d.url)}" target="_blank"${rel}>Открыть</a>`;
     } else {
       li.innerHTML = `<span>${esc(d.name)}</span>`;
     }
     docs.appendChild(li);
   });

   const payments = document.getElementById('payments');
   payments.innerHTML = '';
   (data.payments || []).forEach(p => {
     const row = document.createElement('div');
     row.className = 'payment-row';
     row.innerHTML = `<span>${esc(p.date)}<br><span style="color:var(--muted);font-size:12px">${esc(p.method)}</span></span><span class="payment-amount">${esc(p.amount)}</span>`;
     payments.appendChild(row);
   });
   if (!data.payments || !data.payments.length) payments.innerHTML = '<div class="empty">Оплат пока нет</div>';

   const updates = document.getElementById('updates');
   updates.innerHTML = '';
   (data.updates || []).forEach(u => {
     const row = document.createElement('div');
     row.style.cssText = 'padding:12px 0;border-bottom:1px solid var(--border);font-size:14px';
     row.innerHTML = `<div>${esc(u.text)}</div><div style="color:var(--muted);font-size:12px;margin-top:4px">${esc(u.date)}</div>`;
     updates.appendChild(row);
   });
   if (!data.updates || !data.updates.length) updates.innerHTML = '<div class="empty">Обновлений пока нет</div>';
}

if (token) {
  fetch('/api/dashboard?token=' + encodeURIComponent(token))
    .then(r => {
      if (!r.ok) {
        if (r.status === 401 || r.status === 403) {
          showLogin();
          return null;
        }
        throw new Error('Сервер вернул ошибку ' + r.status);
      }
      return r.json();
    })
    .then(d => {
      if (!d) return;
      if (d.ok) showDashboard(d);
      else showLogin();
    })
    .catch((err) => {
      // Сюда попадаем только при ошибке сервера/сети (401/403 уже обработаны выше через showLogin без баннера)
      showLogin();
      const detail = err && err.message ? err.message : 'Ошибка соединения';
      showErrorBanner('Ошибка сервера: ' + detail);
    });
} else {
  showLogin();
}

document.getElementById('login-btn').addEventListener('click', () => {
  const val = document.getElementById('login-input').value.trim();
  if (!val) return;
  fetch('/api/dashboard_login', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({action: 'dashboard_login', login: val}),
  })
  .then(r => r.json())
  .then(d => {
    if (d.ok && d.token) {
      safeSet('noir_token', d.token);
      history.replaceState(null, '', '?token=' + d.token);
      showDashboard(d);
    } else {
      alert('Клиент не найден. Попробуйте номер телефона или @username из Telegram.');
    }
  })
  .catch(() => alert('Ошибка соединения'));
});

const logoutBtn = document.getElementById('dash-logout');
if (logoutBtn) {
  logoutBtn.addEventListener('click', () => {
    safeRemove('noir_token');
    try {
      history.replaceState(null, '', location.pathname);
    } catch (e) {}
    location.href = '/';
  });
}
