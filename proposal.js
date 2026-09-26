const params = new URLSearchParams(location.search);
const shortCode = params.get('c');

const packages = {
  start: {name:'Пакет «Старт»', price:'29 000 ₽', desc:'Лендинг до 5 экранов · мобильная адаптация\nФорма заявки · SEO-базовая настройка\nДоговор · чек НПД',
    support:'1 месяц', timeline:'2–3 недели',
    features:['Дизайн до 5 экранов','Мобильная адаптация','Форма заявки','SEO-базовая настройка','Интеграция с Telegram','Договор и чек НПД'],
    stages:[
      {n:'1', t:'Бриф и анализ', d:'1–2 дня'},
      {n:'2', t:'Дизайн', d:'3–4 дня'},
      {n:'3', t:'Разработка', d:'4–6 дней'},
      {n:'4', t:'Тестирование', d:'1–2 дня'},
      {n:'5', t:'Запуск', d:'1 день'},
    ]},
  business: {name:'Пакет «Бизнес»', price:'59 000 ₽', desc:'Лендинг до 8 экранов / сайт до 5 страниц · CRM-интеграция\nОнлайн-запись · Аналитика · SEO\nДоговор · чек НПД',
    support:'2 месяца', timeline:'до месяца',
    features:['Сайт до 5 страниц','Кастомный дизайн','CRM-интеграция','SEO · аналитика','Онлайн-запись','2 месяца поддержки'],
    stages:[
      {n:'1', t:'Бриф и анализ', d:'2–4 дня'},
      {n:'2', t:'Дизайн', d:'5–8 дней'},
      {n:'3', t:'Разработка', d:'10–15 дней'},
      {n:'4', t:'Тестирование и интеграции', d:'3–5 дней'},
      {n:'5', t:'Запуск', d:'2–3 дня'},
    ]},
  premium: {name:'Пакет «Премиум»', price:'112 000 ₽', desc:'Полная цифровая система\nБот + сайт + CRM + аналитика\nДоговор · чек НПД',
    support:'3 месяца', timeline:'от месяца',
    features:['Сайт 10+ страниц / магазин','Полный UX/UI','CRM + оплата','AI-ассистент · Telegram-бот','A/B тесты · аналитика','3 месяца поддержки'],
    stages:[
      {n:'1', t:'Бриф и исследование', d:'3–5 дней'},
      {n:'2', t:'Дизайн и прототип', d:'7–10 дней'},
      {n:'3', t:'Разработка', d:'15–25 дней'},
      {n:'4', t:'Интеграции и тестирование', d:'7–10 дней'},
      {n:'5', t:'Запуск и поддержка', d:'3–5 дней'},
    ]},
  landing: {name:'Модуль «Сайт»', price:'35 000 ₽', desc:'Лендинг, корпоративный сайт, магазин\nОбъясняем, почему покупать у вас\nДоводим до заявки за 10 секунд',
    support:'1 месяц', timeline:'2–3 недели',
    features:['Дизайн лендинга / сайта','Мобильная адаптация','Форма заявки','SEO-базовая настройка','Яндекс.Метрика','Договор и чек НПД'],
    stages:[
      {n:'1', t:'Бриф и анализ', d:'1–2 дня'},
      {n:'2', t:'Дизайн', d:'2–4 дня'},
      {n:'3', t:'Разработка', d:'4–6 дней'},
      {n:'4', t:'Тестирование', d:'1–2 дня'},
      {n:'5', t:'Запуск', d:'1 день'},
    ]},
  bot: {name:'Модуль «Бот»', price:'20 000 ₽', desc:'Запись, оплата, каталог, напоминания\nв Telegram\nБот работает 24/7',
    support:'1 месяц', timeline:'1–2 недели',
    features:['Telegram-бот под ключ','Запись и напоминания','Оплата в боте','Каталог услуг','Аналитика','Договор и чек НПД'],
    stages:[
      {n:'1', t:'Бриф и сценарии', d:'1–2 дня'},
      {n:'2', t:'Дизайн сценария', d:'2–3 дня'},
      {n:'3', t:'Разработка', d:'4–6 дней'},
      {n:'4', t:'Тестирование', d:'1–2 дня'},
      {n:'5', t:'Запуск', d:'1 день'},
    ]},
  auto: {name:'Модуль «CRM»', price:'45 000 ₽', desc:'Связываем сайт, бота, телефонию\nи 1С в одну систему\nЗайвки не теряются',
    support:'2 месяца', timeline:'2-3 недели',
    features:['Настройка CRM','Интеграция с сайтом','Интеграция с ботом','Автоматизация заявок','Обучение','Договор и чек НПД'],
    stages:[
      {n:'1', t:'Аудит процессов', d:'2–3 дня'},
      {n:'2', t:'Настройка CRM', d:'4–6 дней'},
      {n:'3', t:'Интеграции', d:'5–7 дней'},
      {n:'4', t:'Тестирование', d:'2–3 дня'},
      {n:'5', t:'Запуск и обучение', d:'1–2 дня'},
    ]},
  ai: {name:'Модуль «AI»', price:'60 000 ₽', desc:'Чат-бот, который отвечает\nкак ваш лучший менеджер\nОбучаем на вашем бизнесе',
    support:'2 месяца', timeline:'3 недели – месяц',
    features:['AI-чат-бот','Обучение на ваших данных','Консультации клиентов','Запись и продажи','Интеграция с CRM','Договор и чек НПД'],
    stages:[
      {n:'1', t:'Сбор данных', d:'3–5 дней'},
      {n:'2', t:'Настройка модели', d:'5–7 дней'},
      {n:'3', t:'Интеграция', d:'4–6 дней'},
      {n:'4', t:'Тестирование', d:'2–3 дня'},
      {n:'5', t:'Запуск', d:'1–2 дня'},
    ]},
  payment: {name:'Модуль «Оплата»', price:'10 000 ₽', desc:'ЮKassa или Т-Банк\nКарты и СБП на сайте\nКлиент платит за 30 секунд',
    support:'1 месяц', timeline:'3–5 дней',
    features:['Подключение эквайринга','Карты и СБП','Автоматические чеки','Безопасность','Отчёты','Договор и чек НПД'],
    stages:[
      {n:'1', t:'Регистрация', d:'1 день'},
      {n:'2', t:'Настройка', d:'1–2 дня'},
      {n:'3', t:'Интеграция', d:'1–2 дня'},
      {n:'4', t:'Тестирование', d:'1 день'},
      {n:'5', t:'Запуск', d:'1 день'},
    ]},
};

function showLoadErrorBanner() {
  const banner = document.createElement('div');
  banner.textContent = 'Не удалось загрузить данные ссылки, показаны значения по умолчанию';
  banner.setAttribute('style', 'background:#fff3cd;color:#664d03;border:1px solid #ffecb5;border-radius:8px;padding:12px 16px;margin-bottom:24px;font-size:10pt');
  document.body.prepend(banner);
}

function fillForm(data) {
  const name = data.name || params.get('name') || 'Клиент';
  let pkg = data.package || params.get('package') || 'start';
  const price = data.price || params.get('price') || '29000';

  const pkgMap = {'Старт': 'start', 'Бизнес': 'business', 'Премиум': 'premium',
    'landing': 'landing', 'bot': 'bot', 'auto': 'auto', 'ai': 'ai', 'payment': 'payment'};
  pkg = pkgMap[pkg] || pkg;

  const p = packages[pkg] || packages.start;
  document.getElementById('client-name').textContent = 'Для: ' + name;
  document.getElementById('pkg-name').textContent = p.name;
  document.getElementById('pkg-price').textContent = p.price;
  const descEl = document.getElementById('pkg-desc');
  descEl.textContent = '';
  p.desc.split('\n').forEach((line, i, arr) => {
    descEl.appendChild(document.createTextNode(line));
    if (i < arr.length - 1) descEl.appendChild(document.createElement('br'));
  });
  document.getElementById('total-amount').textContent = p.price;
  document.getElementById('doc-date').textContent = new Date().toLocaleDateString('ru-RU');

  // Update support and timeline based on package
  const supportEl = document.getElementById('support-text');
  if (supportEl) supportEl.textContent = p.support || '1 месяц';
  const timelineEl = document.getElementById('timeline-text');
  if (timelineEl) timelineEl.textContent = p.timeline || '2–3 недели';

  const stagesEl = document.getElementById('stages-list');
  if (stagesEl && p.stages) {
    stagesEl.textContent = '';
    p.stages.forEach((s) => {
      const row = document.createElement('div');
      row.setAttribute('style', 'padding:8px 0;border-bottom:1px solid #eee');
      row.textContent = s.n + '. ' + s.t + ' — ' + s.d;
      stagesEl.appendChild(row);
    });
  }

  const featuresEl = document.getElementById('features-list');
  if (featuresEl && p.features) {
    featuresEl.textContent = '';
    p.features.forEach((f) => {
      const li = document.createElement('li');
      li.textContent = f;
      featuresEl.appendChild(li);
    });
  }
}

if (shortCode) {
  fetch('/api/proposal?c=' + encodeURIComponent(shortCode))
    .then(r => r.ok ? r.json() : null)
    .then(data => { if (data) fillForm(data); })
    .catch(() => {
      fillForm({});
      showLoadErrorBanner();
    });
} else {
  const year = new Date().getFullYear();
  const rand = Math.floor(100 + Math.random() * 900);
  document.getElementById('doc-number').textContent = 'КП-' + year + '-' + rand;
  fillForm({});
}
