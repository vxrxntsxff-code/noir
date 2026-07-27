import os, json, html, urllib.request, urllib.parse
from datetime import datetime
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


def kb_reply(buttons, placeholder="", one_time=False):
    return {
        "keyboard": [[{"text": b}] for b in buttons],
        "resize_keyboard": True,
        "one_time_keyboard": one_time,
        "input_field_placeholder": placeholder,
    }


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

MAIN_KB = kb_reply(
    ["Оценить проект", "Подобрать решение", "Получить разбор", "Открыть работы", "Оставить заявку"],
    "Выберите действие"
)
CANCEL_KB = kb_reply(["Отмена"], "Ваш ответ")

# ── Приветствие (вариант A по умолчанию) ────────────────
WELCOME_A = (
    "<b>NOIR LAB</b>\n\n"
    "Это не чат поддержки.\n"
    "Это вход в проект цифровой студии.\n\n"
    "Два слота в месяц. Отбор по задаче,\n"
    "а не по бюджету.\n\n"
    "Начнём с цели."
)

WELCOME_C = (
    "<b>NOIR LAB</b>\n\n"
    "Набор на август открыт.\n"
    "Свободны 2 слота.\n\n"
    "Мы работаем не со всеми —\n"
    "и это нормально для обеих сторон.\n\n"
    "Куда вас направить."
)

# ── Экраны квалификации ─────────────────────────────────
SCREEN_GOAL = (
    "<b>ЦЕЛЬ · 01</b>\n"
    "шаг 01 / 05\n\n"
    "Зачем вам проект — одной строкой."
)
GOAL_KB = kb_inline([
    [{"text": "Заявки и продажи", "callback_data": "goal:leads"},
     {"text": "Доверие и имидж", "callback_data": "goal:trust"}],
    [{"text": "Экономия времени", "callback_data": "goal:time"},
     {"text": "Всё вместе", "callback_data": "goal:all"}],
])

SCREEN_NICHE = (
    "<b>КВАЛИФИКАЦИЯ · 02</b>\n"
    "шаг 02 / 05\n\n"
    "Чем занимаетесь — двумя словами.\n"
    "(ниша, город)"
)

SITE_KB = kb_inline([
    [{"text": "Нет", "callback_data": "site:no"},
     {"text": "Есть, но не работает", "callback_data": "site:bad"}],
    [{"text": "Есть, нужен редизайн", "callback_data": "site:redesign"}],
])

SCREEN_DEADLINE = (
    "<b>СРОК · 03</b>\n"
    "шаг 03 / 05\n\n"
    "Когда нужен запуск."
)
DEADLINE_KB = kb_inline([
    [{"text": "В течение 2 недель", "callback_data": "dl:2w"}],
    [{"text": "Месяц", "callback_data": "dl:month"}],
    [{"text": "Без спешки", "callback_data": "dl:none"}],
])

SCREEN_DONE = (
    "<b>✓ Заявка в студии.</b>\n\n"
    "Ваш договор уже собран —\n"
    "данные подставлены, можно открыть и распечатать:\n"
    "{url}\n\n"
    "Ответим в течение 15 минут в рабочее время."
)
DONE_KB = kb_inline([
    [{"text": "Написать в Telegram", "url": "https://t.me/noir_lab42"}],
    [{"text": "Позвонить", "url": "tel:+79515922618"}],
    [{"text": "В главное меню", "callback_data": "menu"}],
])

# ── Вилки бюджета ───────────────────────────────────────
BUDGET = {
    "start":    {"label": "Старт",    "range": "29 000 – 39 000 ₽",
                 "includes": "лендинг + оплата + метрика + заявки в TG",
                 "deadline": "2–3 нед"},
    "business": {"label": "Бизнес",   "range": "59 000 – 79 000 ₽",
                 "includes": "+ бот + CRM, ни одна заявка не теряется",
                 "deadline": "3–4 нед"},
    "premium":  {"label": "Премиум",  "range": "112 000 – 149 000 ₽",
                 "+ AI-ассистент + полная автоматизация",
                 "deadline": "от месяца"},
}


def budget_screen(level):
    b = BUDGET[level]
    return (
        f"<b>УРОВЕНЬ ПРОЕКТА · 04</b>\n"
        f"шаг 04 / 05\n\n"
        f"По вашим ответам — уровень «{b['label']}».\n\n"
        f"Ориентир по бюджету: {b['range']}\n"
        f"Нижняя граница — первым трём клиентам,\n"
        f"верхняя — обычный прайс после набора.\n\n"
        f"Что входит: {b['includes']}.\n"
        f"Срок: {b['deadline']}."
    )


BUDGET_KB_MENU = kb_inline([
    [{"text": "Это мой уровень", "callback_data": "budget:ok"}],
    [{"text": "Показать другие уровни", "callback_data": "budget:show"}],
    [{"text": "Нужен созвон", "callback_data": "budget:call"}],
])

BUDGET_KB_LEVELS = kb_inline([
    [{"text": f"Старт — 29 000–39 000 ₽", "callback_data": "budget:start"}],
    [{"text": f"Бизнес — 59 000–79 000 ₽", "callback_data": "budget:business"}],
    [{"text": f"Премиум — 112 000–149 000 ₽", "callback_data": "budget:premium"}],
    [{"text": "Нужен созвон", "callback_data": "budget:call"}],
])

SCREEN_DEMO = (
    "<b>ДОКАЗАТЕЛЬСТВО · 05</b>\n"
    "шаг 05 / 05\n\n"
    "Не обещаем — показываем.\n"
    "Один проект, чтобы понять уровень."
)
DEMO_KB = kb_inline([
    [{"text": "Стоматология · запись", "url": f"{SITE_URL_PROD}/topdent.html"}],
    [{"text": "Все работы", "url": f"{SITE_URL_PROD}/cases.html"}],
    [{"text": "Главный сайт", "url": f"{SITE_URL_PROD}/index.html"}],
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

SCREEN_AUDIT_HEADER = "<b>РАЗБОР · {niche}</b>"

EVAL_HEADER = "<b>ОЦЕНКА ПРОЕКТА</b>"
EVAL_BODY = (
    "Принято. Живой разбор пришлёт человек —\n"
    "обычно в течение 15 минут в рабочее время.\n\n"
    "А пока — три вещи, которые чаще всего\n"
    "мешают сайту продавать:\n"
    "— нет одного главного действия на экране;\n"
    "— цена и срок спрятаны или не зафиксированы;\n"
    "— заявка живёт в мессенджере, а не в CRM.\n\n"
    "Если хоть одно про вас — мы это чиним."
)

SOLUTION_HEADER = "<b>ПОДБОР РЕШЕНИЯ</b>"
SOLUTION_BODY = "Что болит сильнее всего — одной строкой."
SOLUTION_KB = kb_inline([
    [{"text": "Нет заявок", "callback_data": "sol:leads"},
     {"text": "Тону в рутине", "callback_data": "sol:routine"}],
    [{"text": "Нет системы", "callback_data": "sol:nosys"},
     {"text": "Всё сразу", "callback_data": "sol:all"}],
])

ANTIPRESS = (
    "Можно не оставлять заявку.\n"
    "Можно просто открыть один проект\n"
    "и решить самим."
)
ANTIPRESS_KB = kb_inline([
    [{"text": "Открыть работы", "url": f"{SITE_URL_PROD}/cases.html"}],
    [{"text": "Написать в Telegram", "url": "https://t.me/noir_lab42"}],
])


# ── Скоринг ─────────────────────────────────────────────
def score(data):
    goal = data.get("goal", "")
    site = data.get("site", "")
    niche = data.get("niche", "").lower()
    dl = data.get("deadline", "")

    premium_niche = any(w in niche for w in [
        "стоматолог", "клиник", "опт", " HoReCa", "ресторан", "отель", "салон", " beauty"
    ])

    # Фильтр: личное / некоммерческое
    if goal in ("personal", "hobby"):
        return "filter"

    # Премиум
    if goal == "all" or (goal == "trust" and premium_niche):
        return "premium"
    if site == "bad" and goal == "leads":
        return "business"
    if dl == "2w" and goal == "all":
        return "call"

    # Старт
    if goal == "time" and site == "no":
        return "start"

    # Бизнес по умолчанию
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
    send(chat_id, WELCOME_A, reply_markup=MAIN_KB)


def handle_menu(chat_id):
    _state.pop(chat_id, None)
    send(chat_id, "NOIR LAB · Кемерово\n\nМы берём два проекта в месяц.\nНиже — вход в процесс.", reply_markup=MAIN_KB)


def handle_text(chat_id, text):
    st = _state.get(chat_id)

    if not st:
        if text == "Оценить проект":
            _state[chat_id] = {"step": "eval_material"}
            send(chat_id,
                 f"{EVAL_HEADER}\n\n"
                 "Пришлите ссылку, скрин или опишите проект — одним сообщением.",
                 reply_markup=CANCEL_KB)
        elif text == "Подобрать решение":
            _state[chat_id] = {"step": "sol_pain"}
            send(chat_id, f"{SOLUTION_HEADER}\n\n{SOLUTION_BODY}", reply_markup=SOLUTION_KB)
        elif text == "Получить разбор":
            _state[chat_id] = {"step": "audit_niche"}
            send(chat_id,
                 "<b>РАЗБОР</b>\n\nЧем занимаетесь — двумя словами. (ниша, город)",
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

    # A: Оценить проект — принимаем любой текст
    if step == "eval_material":
        _state.pop(chat_id, None)
        send_lead(
            f"<b>РАЗБОР · ожидает человека</b>\n\n"
            f"Материал от клиента:\n{text[:500]}",
            [[{"text": "Ответить клиенту", "url": f"https://t.me/{chat_id}"}]]
        )
        send(chat_id,
             f"{EVAL_HEADER}\n\n"
             "Принято. Живой разбор пришлёт человек —\n"
             "обычно в течение 15 минут в рабочее время.\n\n"
             "А пока — три вещи, которые чаще всего\n"
             "мешают сайту продавать:\n"
             "— нет одного главного действия на экране;\n"
             "— цена и срок спрятаны или не зафиксированы;\n"
             "— заявка живёт в мессенджере, а не в CRM.\n\n"
             "Если хоть одно про вас — мы это чиним.",
             reply_markup=kb_inline([
                 [{"text": "Оставить заявку на разбор", "callback_data": "flow:start"}],
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

    # B: Подобрать решение — ответ на "что болит"
    if step == "sol_pain":
        sol_type = ""
        t = text.lower()
        if any(w in t for w in ["заявк", "продаж", "клиент"]):
            sol_type = "leads"
        elif any(w in t for w in ["рутин", "время", "задач"]):
            sol_type = "routine"
        elif any(w in t for w in ["систем", "crm", "учёт"]):
            sol_type = "nosys"
        else:
            sol_type = "all"

        level = score_solution(sol_type)
        _state.pop(chat_id, None)

        if level == "premium":
            send(chat_id,
                 "Тогда вам — система целиком, а не латание дыр.\n\n"
                 "Уровень «Премиум»: 112 000–149 000 ₽\n"
                 "AI-ассистент + бот + CRM + оплата + всё под ключ.",
                 reply_markup=kb_inline([
                     [{"text": "Это мой уровень", "callback_data": "flow:name"}],
                     [{"text": "Нужен созвон", "callback_data": "flow:call"}],
                     [{"text": "Показать другие уровни", "callback_data": "budget:show"}],
                 ]))
        else:
            b = BUDGET[level]
            send(chat_id,
                 f"Тогда вам — система целиком, а не латание дыр.\n\n"
                 f"Уровень «{b['label']}»: {b['range']}\n"
                 f"Что входит: {b['includes']}.",
                 reply_markup=kb_inline([
                     [{"text": "Это мой уровень", "callback_data": "flow:name"}],
                     [{"text": "Нужен созвон", "callback_data": "flow:call"}],
                     [{"text": "Показать другие уровни", "callback_data": "budget:show"}],
                 ]))
        return

    # Квалификация: ввод ниши
    if step == "niche":
        st["data"]["niche"] = text
        st["step"] = "site_ask"
        send(chat_id, "Сайт уже есть?", reply_markup=SITE_KB)
        return

    # Квалификация: ввод имени
    if step == "name":
        st["data"]["name"] = text
        st["step"] = "contact"
        send(chat_id, "Телефон или Telegram для связи?", reply_markup=CANCEL_KB)
        return

    # Квалификация: ввод контакта
    if step == "contact":
        st["data"]["contact"] = text
        st["step"] = "ref"
        send(chat_id,
             "Ссылка на сайт / соцсети (или Пропустить):",
             reply_markup=kb_reply(["Пропустить", "Отмена"]))
        return

    # Квалификация: ссылка / бриф
    if step == "ref":
        ref = "" if text == "Пропустить" else text
        st["data"]["ref"] = ref
        _finish_qualification(chat_id, st["data"])
        return

    # Квалификация: текст ниши (через inline кнопку сайта)
    if step == "niche_text":
        st["data"]["niche"] = text
        st["step"] = "site_ask"
        send(chat_id, "Сайт уже есть?", reply_markup=SITE_KB)
        return

    send(chat_id, "Отправьте /start чтобы начать.")


def handle_callback(chat_id, data):
    st = _state.get(chat_id)

    # Навигация
    if data == "menu":
        handle_menu(chat_id)
        return

    if data == "flow:start":
        _state[chat_id] = {"step": "goal", "data": {}}
        send(chat_id, SCREEN_GOAL, reply_markup=GOAL_KB)
        return

    if data == "flow:name":
        _state[chat_id] = {"step": "name", "data": st["data"] if st else {}}
        send(chat_id, "Как к вам обращаться?", reply_markup=CANCEL_KB)
        return

    if data == "flow:call":
        _state.pop(chat_id, None)
        send(chat_id,
             "Хорошо, запишем на созвон.\n"
             "Как к вам обращаться?",
             reply_markup=CANCEL_KB)
        _state[chat_id] = {"step": "name", "data": {"need_call": True}}
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

            b = BUDGET[level]
            niche_safe = html.escape(niche)
            send(chat_id,
                 f"{SCREEN_AUDIT_HEADER.format(niche=niche_safe)}\n\n"
                 f"Что хорошо:\nниша с повторными клиентами — автоматизация\n"
                 f"окупается быстрее всего.\n\n"
                 f"Что слабо:\n"
                 f"запись по телефону в 2026 — это потерянные\n"
                 f"клиенты в часы пик.\n\n"
                 f"Что исправить:\n"
                 f"онлайн-запись + напоминания + CRM в одном контуре.\n\n"
                 f"Следующий шаг:\n"
                 f"уровень «{b['label']}», ориентир {b['range']}.\n"
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

            if level == "call":
                _state.pop(chat_id, None)
                send(chat_id,
                     "Честно: за 2 недели комплекс не собрать.\n"
                     "Нужен созвон, чтобы понять приоритеты.",
                     reply_markup=kb_inline([
                         [{"text": "Записаться на созвон", "callback_data": "flow:call"}],
                         [{"text": "В главное меню", "callback_data": "menu"}],
                     ]))
                return

            st["step"] = "budget_show"
            send(chat_id, budget_screen(level), reply_markup=BUDGET_KB_MENU)
        return

    # Бюджет
    if data == "budget:ok":
        if st:
            st["step"] = "demo"
        send(chat_id, SCREEN_DEMO, reply_markup=DEMO_KB)
        return

    if data == "budget:show":
        if st:
            st["step"] = "budget_pick"
        send(chat_id,
             "Все уровни с вилками budgets:",
             reply_markup=BUDGET_KB_LEVELS)
        return

    if data.startswith("budget:") and data[7:] in ("start", "business", "premium"):
        level = data[7:]
        if st:
            st["data"]["level"] = level
            st["step"] = "demo"
        send(chat_id, budget_screen(level), reply_markup=DEMO_KB)
        return

    if data == "budget:call":
        _state.pop(chat_id, None)
        send(chat_id,
             "Хорошо, запишем на созвон.\nКак к вам обращаться?",
             reply_markup=CANCEL_KB)
        _state[chat_id] = {"step": "name", "data": {"need_call": True}}
        return

    # Демо →下一步 к контакту
    if data == "demo:next":
        if st:
            st["step"] = "name"
        send(chat_id, "ПОСЛЕДНИЙ ШАГ\n\nКак к вам обращаться.", reply_markup=CANCEL_KB)
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
        send(chat_id, "Как к вам обращаться?", reply_markup=CANCEL_KB)
        return

    # Отмена
    if data == "cancel":
        handle_menu(chat_id)
        return

    # Пакет (обратная совместимость)
    if data.startswith("pkg:"):
        pkg, price = data[4:].split("|", 1)
        _state[chat_id] = {"step": "name", "data": {"package": pkg, "price": price}}
        send(chat_id, f"Выбран пакет «{pkg}». Как к вам обращаться?", reply_markup=CANCEL_KB)
        return


def _finish_qualification(chat_id, data):
    name = html.escape(data.get("name", ""))
    contact = html.escape(data.get("contact", ""))
    niche = html.escape(data.get("niche", ""))
    goal = html.escape(data.get("goal", ""))
    site = html.escape(data.get("site", ""))
    dl = html.escape(data.get("deadline", ""))
    ref = html.escape(data.get("ref", ""))
    level = data.get("level", score(data))
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    b = BUDGET.get(level, BUDGET["business"])
    url = contract_url({
        "name": data.get("name", ""),
        "phone": data.get("contact", ""),
        "task": f"Заявка из бота · {b['label']} · {niche}",
        "price": b["range"],
    })

    # Лид в группу
    lead = (
        f"<b>НОВАЯ ЗАЯВКА · уровень «{b['label']}»</b>\n\n"
        f"Имя: {name}\n"
        f"Ниша: {niche}\n"
        f"Цель: {goal}\n"
        f"Сайт: {site}\n"
        f"Срок: {dl}\n"
        f"Контакт: {contact}\n"
        f"Ориентир: {b['range']}\n"
        f"{now}"
    )
    lead_kb = [[{"text": "Договор клиента", "url": url}]]
    if data.get("contact", "").startswith("@"):
        lead_kb.append([{"text": "Написать в TG", "url": f"https://t.me/{data['contact'].lstrip('@')}"}])
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
    url = contract_url({
        "name": payload.get("name", ""),
        "phone": payload.get("phone", ""),
        "task": payload.get("message", ""),
    })
    lead = f"<b>Заявка с сайта</b>\n\nИмя: {name}\nТелефон: {phone}\nСообщение: {message}"
    if source:
        lead += f"\nИсточник: {source}"
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
