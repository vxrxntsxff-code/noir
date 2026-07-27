import os, json, html, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
SITE_URL = os.environ.get("SITE_URL", "https://noir-rosy.vercel.app").rstrip("/")

_raw = os.environ.get("LEADS_CHAT_ID", "").strip()
LEADS_CHAT_ID = int(_raw) if _raw and _raw.lstrip("-").isdigit() else OWNER_ID

_state = {}

# ── Telegram API ────────────────────────────────────────
def tg(method, data=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    payload = json.dumps(data or {}).encode()
    req = urllib.request.Request(url, data=payload)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception:
        return {"ok": False}


def send(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    return tg("sendMessage", data)


def kb_inline(buttons):
    return {"inline_keyboard": buttons}


def kb_reply(rows, placeholder="", one_time=False):
    if rows and isinstance(rows[0], str):
        rows = [[b] for b in rows]
    return {
        "keyboard": [[{"text": t} for t in row] for row in rows],
        "resize_keyboard": True,
        "one_time_keyboard": one_time,
        "input_field_placeholder": placeholder,
    }


def now_msk():
    return datetime.now(timezone(timedelta(hours=3)))


def contract_url(params):
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v})
    return f"{SITE_URL}/dogovor.html?{qs}"


def send_lead(text, buttons=None):
    markup = kb_inline(buttons) if buttons else None
    msg = {"chat_id": LEADS_CHAT_ID, "text": text}
    if markup:
        msg["reply_markup"] = json.dumps(markup)
    try:
        tg("sendMessage", msg)
    except Exception:
        pass


# ── Константы ───────────────────────────────────────────
SITE_URL_PROD = "https://noir-rosy.vercel.app"
PRICE_ACTUAL = "29 000"

MAIN_KB = kb_reply(
    [["Оценить проект", "Подобрать решение", "Получить разбор"],
     ["Открыть работы", "Оставить заявку"]],
    "Выберите действие"
)
CANCEL_KB = kb_reply(["Отмена"], "Ваш ответ")
SKIP_KB = kb_reply(["Пропустить", "Отмена"])

# ── Приветствие ─────────────────────────────────────────
WELCOME = (
    "<b>NOIR LAB</b>\n\n"
    "Это не чат поддержки.\n"
    "Это вход в проект цифровой студии.\n\n"
    "Два слота в месяц. Отбор по задаче,\n"
    "а не по бюджету.\n\n"
    "Начнём с цели."
)

# ── Локализация ─────────────────────────────────────────
GOAL_RU = {"leads": "Заявки и продажи", "trust": "Доверие и имидж",
           "time": "Экономия времени", "all": "Всё вместе"}
SITE_RU = {"no": "Нет", "bad": "Есть, но не работает", "redesign": "Есть, нужен редизайн"}
DL_RU = {"2w": "В течение 2 недель", "month": "Месяц", "none": "Без спешки"}

# ── Экраны квалификации ─────────────────────────────────
SCREEN_GOAL = (
    "<b>ЦЕЛЬ · 01</b>\n"
    "шаг 01 / 06\n\n"
    "Зачем вам проект — одной строкой."
)
GOAL_KB = kb_inline([
    [{"text": "Заявки и продажи", "callback_data": "goal:leads"},
     {"text": "Доверие и имидж", "callback_data": "goal:trust"}],
    [{"text": "Экономия времени", "callback_data": "goal:time"},
     {"text": "Всё вместе", "callback_data": "goal:all"}],
])

SCREEN_NICHE = (
    "<b>НИША · 02</b>\n"
    "шаг 02 / 06\n\n"
    "Чем занимаетесь — одной строкой.\n"
    "(например: стоматология, салон красоты, ресторан)"
)

SCREEN_CITY = (
    "<b>ГОРОД · 03</b>\n"
    "шаг 03 / 06\n\n"
    "Где работаете?"
)

SITE_KB = kb_inline([
    [{"text": "Нет", "callback_data": "site:no"},
     {"text": "Есть, но не работает", "callback_data": "site:bad"}],
    [{"text": "Есть, нужен редизайн", "callback_data": "site:redesign"}],
])

SCREEN_DEADLINE = (
    "<b>СРОК · 04</b>\n"
    "шаг 04 / 06\n\n"
    "Когда нужен запуск."
)
DEADLINE_KB = kb_inline([
    [{"text": "В течение 2 недель", "callback_data": "dl:2w"},
     {"text": "Месяц", "callback_data": "dl:month"}],
    [{"text": "Без спешки", "callback_data": "dl:none"}],
])

SCREEN_TASK = (
    "<b>ЗАДАЧА · 05</b>\n"
    "шаг 05 / 06\n\n"
    "Кратко опишите, что нужно сделать.\n"
    "(лендинг с записью, бот для приёма заявок,\n"
    "сайт-визитка с каталогом и т.д.)"
)


def budget_screen(level):
    labels = {"start": "Старт", "business": "Бизнес", "premium": "Премиум"}
    return (
        f"<b>УРОВЕНЬ · 05</b>\n\n"
        f"По вашим ответам — уровень «{labels[level]}».\n\n"
        f"Актуальная цена: {PRICE_ACTUAL} ₽\n"
        f"(первым 3 клиентам, обычный прайс выше)\n\n"
        f"Срок: {DL_RU.get(_state.get('deadline', ''), '—')}.\n\n"
        f"Всё включено: договор, чек НПД, поддержка 2 месяца."
    )


BUDGET_KB = kb_inline([
    [{"text": "Это мой уровень", "callback_data": "budget:ok"},
     {"text": "Показать другие", "callback_data": "budget:show"}],
    [{"text": "Нужен созвон", "callback_data": "budget:call"}],
])

BUDGET_KB_LEVELS = kb_inline([
    [{"text": "Старт — 29K", "callback_data": "budget:start"},
     {"text": "Бизнес — 59K", "callback_data": "budget:business"}],
    [{"text": "Премиум — 112K", "callback_data": "budget:premium"}],
    [{"text": "Нужен созвон", "callback_data": "budget:call"}],
])

SCREEN_DEMO = (
    "<b>ДОКАЗАТЕЛЬСТВО · 06</b>\n"
    "шаг 06 / 06\n\n"
    "Не обещаем — показываем.\n"
    "Один проект, чтобы понять уровень."
)
DEMO_KB = kb_inline([
    [{"text": "Стоматология · запись", "url": f"{SITE_URL_PROD}/topdent.html"}],
    [{"text": "Все работы", "url": f"{SITE_URL_PROD}/cases.html"}],
    [{"text": "Оставить заявку", "callback_data": "demo:apply"}],
])

SCREEN_FILTER = (
    "Честно: этот формат — не наш.\n"
    "Мы работаем с бизнесом, где проект окупается\n"
    "за 1–2 месяца, и берёмся за систему целиком.\n\n"
    "Но вот что поможет прямо сейчас — бесплатно:\n"
    "чек-лист «5 причин, почему сайт не продаёт»."
)
FILTER_KB = kb_inline([
    [{"text": "Получить чек-лист", "callback_data": "filter:checklist"}],
    [{"text": "Всё равно оставить заявку", "callback_data": "filter:force"}],
    [{"text": "В главное меню", "callback_data": "menu"}],
])

DONE_KB = kb_inline([
    [{"text": "Написать в Telegram", "url": "https://t.me/noir_lab42"}],
    [{"text": "Позвонить", "url": "tel:+79515922618"}],
    [{"text": "В главное меню", "callback_data": "menu"}],
])


# ── Скоринг ─────────────────────────────────────────────
def score(data):
    dl = data.get("deadline", "")
    goal = data.get("goal", "")
    site = data.get("site", "")

    # Фильтр: личное / некоммерческое
    if goal in ("personal", "hobby"):
        return "filter"

    # Прямое соответствие: срок → уровень
    if dl == "2w":
        return "start"
    if dl == "month":
        return "business"
    if dl == "none":
        # Без спешки — премиум, но если цель простая — бизнес
        if goal == "time" and site == "no":
            return "business"
        return "premium"

    return "business"


def score_solution(sol_type):
    mapping = {"leads": "business", "routine": "business", "nosys": "business", "all": "premium"}
    return mapping.get(sol_type, "business")


def score_audit(niche, site, goal):
    niche_l = niche.lower()
    if any(w in niche_l for w in ["стоматолог", "клиник", "салон", " beauty", " HoReCa"]):
        return "premium"
    if goal == "all":
        return "premium"
    if site == "bad":
        return "business"
    return "business"


# ── Хендлеры ────────────────────────────────────────────
def handle_start(chat_id):
    _state.pop(chat_id, None)
    send(chat_id, WELCOME, reply_markup=MAIN_KB)


def handle_menu(chat_id):
    _state.pop(chat_id, None)
    send(chat_id, "NOIR LAB · Кемерово\n\nМы берём два проекта в месяц.\nНиже — вход в процесс.", reply_markup=MAIN_KB)


def handle_text(chat_id, text):
    st = _state.get(chat_id)

    if not st:
        if text == "Оценить проект":
            _state[chat_id] = {"step": "eval_material"}
            send(chat_id,
                 "<b>ОЦЕНКА ПРОЕКТА</b>\n\n"
                 "Пришлите ссылку, скрин или опишите проект — одним сообщением.",
                 reply_markup=CANCEL_KB)
        elif text == "Подобрать решение":
            _state[chat_id] = {"step": "sol_pain"}
            send(chat_id,
                 "<b>ПОДБОР РЕШЕНИЯ</b>\n\n"
                 "Что болит сильнее всего — одной строкой.",
                 reply_markup=kb_inline([
                     [{"text": "Нет заявок", "callback_data": "sol:leads"},
                      {"text": "Тону в рутине", "callback_data": "sol:routine"}],
                     [{"text": "Нет системы", "callback_data": "sol:nosys"},
                      {"text": "Всё сразу", "callback_data": "sol:all"}],
                 ]))
        elif text == "Получить разбор":
            _state[chat_id] = {"step": "audit_niche"}
            send(chat_id,
                 "<b>РАЗБОР</b>\n\nЧем занимаетесь — одной строкой.",
                 reply_markup=CANCEL_KB)
        elif text == "Открыть работы":
            kb = kb_inline([
                [{"text": "Стоматология · запись", "url": f"{SITE_URL_PROD}/topdent.html"}],
                [{"text": "Все работы", "url": f"{SITE_URL_PROD}/cases.html"}],
            ])
            send(chat_id, "Наши работы — каждый проект рабочий:", reply_markup=kb)
        elif text == "Оставить заявку":
            _state[chat_id] = {"step": "goal", "data": {}}
            send(chat_id, SCREEN_GOAL, reply_markup=GOAL_KB)
        else:
            send(chat_id, "Отправьте /start чтобы начать.")
        return

    step = st["step"]

    # A: Оценить проект
    if step == "eval_material":
        _state.pop(chat_id, None)
        send_lead(
            f"<b>РАЗБОР · ожидает человека</b>\n\n"
            f"Материал от клиента:\n{text[:500]}",
            [[{"text": "Ответить клиенту", "url": f"https://t.me/{chat_id}"}]]
        )
        send(chat_id,
             "<b>ОЦЕНКА ПРОЕКТА</b>\n\n"
             "Принято. Живой разбор пришлёт человек —\n"
             "обычно в течение 15 минут в рабочее время.\n\n"
             "А пока — три вещи, которые чаще всего\n"
             "мешают сайту продавать:\n"
             "— нет одного главного действия на экране;\n"
             "— цена и срок спрятаны или не зафиксированы;\n"
             "— заявка живёт в мессенджере, а не в CRM.\n\n"
             "Если хоть одно про вас — мы это чиним.",
             reply_markup=kb_inline([
                 [{"text": "Оставить заявку", "callback_data": "flow:start"}],
                 [{"text": "В главное меню", "callback_data": "menu"}],
             ]))
        return

    # C: Разбор — ниша
    if step == "audit_niche":
        st["data"]["niche"] = text
        st["step"] = "audit_site"
        send(chat_id,
             "Есть сайт? Если да — какой статус.",
             reply_markup=kb_inline([
                 [{"text": "Нет", "callback_data": "asite:no"},
                  {"text": "Есть, но не работает", "callback_data": "asite:bad"}],
                 [{"text": "Есть, нужен редизайн", "callback_data": "asite:redesign"}],
             ]))
        return

    # Квалификация: ниша
    if step == "niche":
        st["data"]["niche"] = text
        st["step"] = "city"
        send(chat_id, SCREEN_CITY, reply_markup=CANCEL_KB)
        return

    # Квалификация: город
    if step == "city":
        st["data"]["city"] = text
        st["step"] = "site_ask"
        send(chat_id, "Сайт уже есть?", reply_markup=SITE_KB)
        return

    # Квалификация: задача
    if step == "task":
        st["data"]["task"] = text
        st["step"] = "name"
        send(chat_id,
             "<b>КОНТАКТЫ · 06</b>\n\n"
             "Как к вам обращаться? (ФИО)",
             reply_markup=CANCEL_KB)
        return

    # Квалификация: ФИО
    if step == "name":
        st["data"]["name"] = text
        st["step"] = "phone"
        send(chat_id, "Телефон для связи:", reply_markup=CANCEL_KB)
        return

    # Квалификация: телефон
    if step == "phone":
        st["data"]["phone"] = text
        st["step"] = "telegram"
        send(chat_id,
             "Telegram для связи (или Пропустить):",
             reply_markup=SKIP_KB)
        return

    # Квалификация: telegram
    if step == "telegram":
        if text != "Пропустить":
            st["data"]["telegram"] = text
        else:
            st["data"]["telegram"] = ""
        _finish_qualification(chat_id, st["data"])
        return

    send(chat_id, "Отправьте /start чтобы начать.")


def handle_callback(chat_id, data):
    st = _state.get(chat_id)

    if data == "menu":
        handle_menu(chat_id)
        return

    if data == "flow:start":
        _state[chat_id] = {"step": "goal", "data": {}}
        send(chat_id, SCREEN_GOAL, reply_markup=GOAL_KB)
        return

    # Цель
    if data.startswith("goal:"):
        goal = data[5:]
        if not st:
            _state[chat_id] = {"step": "niche", "data": {"goal": goal}}
        else:
            st["data"]["goal"] = goal
            st["step"] = "niche"
        send(chat_id, SCREEN_NICHE, reply_markup=CANCEL_KB)
        return

    # Сайт (из квалификации)
    if data.startswith("site:"):
        site = data[5:]
        if st:
            st["data"]["site"] = site
            st["step"] = "deadline"
        send(chat_id, SCREEN_DEADLINE, reply_markup=DEADLINE_KB)
        return

    # Сайт (из разбора)
    if data.startswith("asite:"):
        site = data[6:]
        if st:
            niche = st["data"].get("niche", "")
            goal = st["data"].get("goal", "leads")
            level = score_audit(niche, site, goal)
            _state.pop(chat_id, None)

            labels = {"start": "Старт", "business": "Бизнес", "premium": "Премиум"}
            niche_safe = html.escape(niche)
            send(chat_id,
                 f"<b>РАЗБОР · {niche_safe}</b>\n\n"
                 f"Что хорошо:\nниша с повторными клиентами — автоматизация\n"
                 f"окупается быстрее всего.\n\n"
                 f"Что слабо:\n"
                 f"запись по телефону в 2026 — это потерянные\n"
                 f"клиенты в часы пик.\n\n"
                 f"Что исправить:\n"
                 f"онлайн-запись + напоминания + CRM в одном контуре.\n\n"
                 f"Следующий шаг:\n"
                 f"уровень «{labels[level]}», цена {PRICE_ACTUAL} ₽.\n"
                 f"Показать, как это выглядит вживую?",
                 reply_markup=kb_inline([
                     [{"text": "Показать демо", "url": f"{SITE_URL_PROD}/topdent.html"}],
                     [{"text": "Оставить заявку", "callback_data": "flow:start"}],
                     [{"text": "В главное меню", "callback_data": "menu"}],
                 ]))
        return

    # Срок → скоринг
    if data.startswith("dl:"):
        dl = data[3:]
        if st:
            st["data"]["deadline"] = dl
            level = score(st["data"])

            if level == "filter":
                _state.pop(chat_id, None)
                send(chat_id, SCREEN_FILTER, reply_markup=FILTER_KB)
                return

            st["step"] = "budget_show"
            send(chat_id, budget_screen(level), reply_markup=BUDGET_KB)
        return

    # Бюджет
    if data == "budget:ok":
        if st:
            st["step"] = "task"
        send(chat_id, SCREEN_TASK, reply_markup=CANCEL_KB)
        return

    if data == "budget:show":
        send(chat_id, "Все уровни:", reply_markup=BUDGET_KB_LEVELS)
        return

    if data.startswith("budget:") and data[7:] in ("start", "business", "premium"):
        level = data[7:]
        if st:
            st["data"]["level"] = level
            st["step"] = "task"
        send(chat_id, SCREEN_TASK, reply_markup=CANCEL_KB)
        return

    if data == "budget:call":
        _state.pop(chat_id, None)
        send(chat_id,
             "Хорошо, запишем на созвон.\nКак к вам обращаться?",
             reply_markup=CANCEL_KB)
        _state[chat_id] = {"step": "name", "data": {"need_call": True}}
        return

    # Демо → заявка
    if data == "demo:apply":
        if st:
            st["step"] = "name"
        else:
            _state[chat_id] = {"step": "name", "data": {}}
        send(chat_id,
             "<b>КОНТАКТЫ</b>\n\nКак к вам обращаться? (ФИО)",
             reply_markup=CANCEL_KB)
        return

    # Подобрать решение
    if data.startswith("sol:"):
        sol_type = data[4:]
        level = score_solution(sol_type)
        _state.pop(chat_id, None)

        labels = {"start": "Старт", "business": "Бизнес", "premium": "Премиум"}
        send(chat_id,
             f"Тогда вам — система целиком, а не латание дыр.\n\n"
             f"Уровень «{labels[level]}»: {PRICE_ACTUAL} ₽\n"
             f"Всё включено: договор, чек НПД, поддержка 2 месяца.",
             reply_markup=kb_inline([
                 [{"text": "Это мой уровень", "callback_data": "flow:start"}],
                 [{"text": "Нужен созвон", "callback_data": "budget:call"}],
                 [{"text": "Показать другие уровни", "callback_data": "budget:show"}],
             ]))
        return

    # Фильтр
    if data == "filter:checklist":
        _state.pop(chat_id, None)
        send(chat_id,
             "✓ Чек-лист «5 причин, почему сайт не продаёт»\n\n"
             "1. Нет одного главного CTA на экране\n"
             "2. Цена не зафиксирована или спрятана\n"
             "3. Нет социального доказательства\n"
             "4. Заявка живёт в мессенджере, а не в CRM\n"
             "5. Сайт не оптимизирован под мобильные\n\n"
             "Исправляем? → /start",
             reply_markup=MAIN_KB)
        return

    if data == "filter:force":
        _state[chat_id] = {"step": "name", "data": {}}
        send(chat_id, "Как к вам обращаться? (ФИО)", reply_markup=CANCEL_KB)
        return


def _finish_qualification(chat_id, data):
    name = html.escape(data.get("name", ""))
    phone = html.escape(data.get("phone", ""))
    telegram = html.escape(data.get("telegram", ""))
    niche = html.escape(data.get("niche", ""))
    city = html.escape(data.get("city", ""))
    goal = GOAL_RU.get(data.get("goal", ""), data.get("goal", ""))
    site = SITE_RU.get(data.get("site", ""), data.get("site", ""))
    dl = DL_RU.get(data.get("deadline", ""), data.get("deadline", ""))
    task = html.escape(data.get("task", ""))
    level = data.get("level", score(data))
    dt = now_msk()
    date_str = dt.strftime("%d.%m.%Y")
    time_str = dt.strftime("%H:%M")
    num = dt.strftime("%Y-%m-001")

    labels = {"start": "Старт", "business": "Бизнес", "premium": "Премиум"}
    label = labels.get(level, "Бизнес")

    url = contract_url({
        "name": data.get("name", ""),
        "phone": data.get("phone", ""),
        "task": data.get("task", ""),
        "price": "29000",
        "date": date_str,
        "num": num,
    })

    # Лид в группу
    lead = (
        f"<b>НОВАЯ ЗАЯВКА · {label}</b>\n\n"
        f"ФИО: {name}\n"
        f"Телефон: {phone}\n"
        f"Telegram: {telegram or '—'}\n"
        f"Ниша: {niche}\n"
        f"Город: {city}\n"
        f"Цель: {goal}\n"
        f"Сайт: {site}\n"
        f"Срок: {dl}\n"
        f"Задача: {task}\n\n"
        f"Цена: {PRICE_ACTUAL} ₽\n"
        f"{date_str} · {time_str} МСК"
    )
    lead_kb = [[{"text": "Договор клиента", "url": url}]]
    if data.get("telegram"):
        tg_nick = data["telegram"].lstrip("@")
        lead_kb.append([{"text": "Написать в TG", "url": f"https://t.me/{tg_nick}"}])
    elif data.get("phone"):
        lead_kb.append([{"text": "Позвонить", "url": f"tel:{data['phone']}"}])
    send_lead(lead, lead_kb)

    # Ответ клиенту
    _state.pop(chat_id, None)
    send(chat_id,
         f"✓ Заявка в студии.\n\n"
         f"Ваш договор уже собран —\n"
         f"данные подставлены, можно открыть и распечатать:\n{url}\n\n"
         f"Ответим в течение 15 минут в рабочее время.",
         reply_markup=DONE_KB)


# ── Форма с сайта ───────────────────────────────────────
def handle_form(payload):
    name = html.escape(payload.get("name", "---"))
    phone = html.escape(payload.get("phone", "---"))
    message = html.escape(payload.get("message", "---"))
    source = payload.get("source", "")
    dt = now_msk()
    date_str = dt.strftime("%d.%m.%Y")
    url = contract_url({
        "name": payload.get("name", ""),
        "phone": payload.get("phone", ""),
        "task": payload.get("message", ""),
        "price": "29000",
        "date": date_str,
        "num": dt.strftime("%Y-%m-001"),
    })
    lead = (
        f"<b>ЗАЯВКА С САЙТА</b>\n\n"
        f"ФИО: {name}\n"
        f"Телефон: {phone}\n"
        f"Сообщение: {message}"
    )
    if source:
        lead += f"\nИсточник: {source}"
    lead += f"\n\nЦена: {PRICE_ACTUAL} ₽\n{date_str}"
    send_lead(lead, [[{"text": "Договор", "url": url}]])
    return {"ok": True, "contract_url": url}


# ── Vercel entry point ──────────────────────────────────
class handler(BaseHTTPRequestHandler):
    def _send(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)

    def do_GET(self):
        self._send(200, json.dumps({"status": "ok", "bot": "NOIR LAB"}))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw)

            if body.get("_form"):
                result = handle_form(body["_form"])
                self._send(200, json.dumps(result))
                return

            msg = body.get("message") or body.get("callback_query")
            if not msg:
                self._send(200, "ok")
                return

            if "callback_query" in body:
                cb = body["callback_query"]
                chat_id = cb["message"]["chat"]["id"]
                handle_callback(chat_id, cb["data"])
                tg("answerCallbackQuery", {"callback_query_id": cb["id"]})
            else:
                chat_id = msg["chat"]["id"]
                text = msg.get("text", "")
                if text == "/start":
                    handle_start(chat_id)
                elif text == "/menu":
                    handle_menu(chat_id)
                else:
                    handle_text(chat_id, text)

            self._send(200, "ok")
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))
