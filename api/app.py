import os, sys, json, urllib.request, urllib.parse, logging, traceback, random
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from sheets import sheets_lead, sheets_project, sheets_event, sheets_find_client, sheets_get_projects, sheets_update_project, sheets_update_project_by_row, sheets_add_update, sheets_payment, _sheets_api, SPREADSHEET_ID, SHEETS
except Exception as _sheets_err:
    import logging as _elog
    _elog.error("sheets import failed: %s", _sheets_err)
    sheets_lead = None
    sheets_project = None
    sheets_event = None
    sheets_find_client = None
    sheets_get_projects = None
    sheets_update_project = None
    sheets_update_project_by_row = None
    sheets_add_update = None
    _sheets_api = None
    SPREADSHEET_ID = ""
    SHEETS = {}

# ── Config ───────────────────────────────────────────────
BOT_TOKEN   = os.environ.get("BOT_TOKEN", "")
OWNER_ID    = int(os.environ.get("OWNER_ID", "0"))
SITE_URL    = os.environ.get("SITE_URL", "https://noir-rosy.vercel.app").rstrip("/")
_raw        = os.environ.get("LEADS_CHAT_ID", "").strip()
LEADS_CHAT_ID = int(_raw) if _raw and _raw.lstrip("-").isdigit() else OWNER_ID

UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "")
UPSTASH_TOK = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")

PAYMENT_LINK  = os.environ.get("PAYMENT_LINK", "")
PAYMENT_QR    = os.environ.get("PAYMENT_QR_IMG", PAYMENT_LINK)

PRICES     = {"start": "29 000", "business": "59 000", "premium": "112 000"}
PRICES_NUM = {"start": "29000", "business": "59000", "premium": "112000"}
LABELS     = {"start": "Старт", "business": "Бизнес", "premium": "Премиум"}

GOAL_RU  = {"leads": "Заявки и продажи", "trust": "Доверие и имидж",
            "time": "Экономия времени", "all": "Всё вместе",
            "landing": "Лендинг", "site": "Сайт", "bot": "ТГ-бот",
            "crm": "CRM", "ai": "AI-ассистент", "pay": "Оплата"}
SITE_RU  = {"no": "Нет", "bad": "Есть, но не работает", "redesign": "Есть, нужен редизайн"}

SERVICES = {
    "landing": {"name": "Лендинг / сайт",  "price": "35 000 – 50 000 ₽", "num": "35000"},
    "bot":     {"name": "Telegram-бот",     "price": "20 000 – 35 000 ₽", "num": "20000"},
    "auto":    {"name": "Автоматизация",    "price": "45 000 – 80 000 ₽", "num": "45000"},
    "ai":      {"name": "AI-ассистент",     "price": "60 000 – 120 000 ₽","num": "60000"},
    "payment": {"name": "Онлайн-оплата",    "price": "10 000 – 15 000 ₽", "num": "10000"},
}

log = logging.getLogger("noir")
log.setLevel(logging.INFO)
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)


def now_kem():
    return datetime.now(timezone(timedelta(hours=7)))


# ── Texts ────────────────────────────────────────────────
T = {
    "welcome": (
        "NOIR\n\n"
        "Не чат поддержки.\n"
        "Вход в проект цифровой студии.\n\n"
        "Два слота в месяц.\n"
        "Начнём с цели."
    ),
    "menu": "NOIR · Кемерово\n\nДва слота в месяц.",
    "menu_hint": "Выберите действие",

    "eval_title": "ОЦЕНКА ПРОЕКТА",
    "eval_input": "Пришлите ссылку, скрин или опишите проект — одним сообщением.",
    "eval_confirm": (
        "Принято.\n"
        "Разбор пришлём в течение 15 минут.\n\n"
        "Три причины, почему сайт не продаёт:\n"
        "— нет одного CTA на экране;\n"
        "— цена спрятана или не зафиксирована;\n"
        "— заявка в мессенджере, а не в CRM."
    ),

    "sol_title": "ПОДБОР РЕШЕНИЯ",
    "sol_input": "Что болит сильнее всего — одной строкой.",

    "screen_pain": "БОЛЬ\n\nЧто болит сильнее всего — одной строкой.",
    "screen_goal": "ЦЕЛЬ · 1 / 5\n\nЗачем вам проект — одной строкой.",
    "screen_site": "САЙТ · 2 / 5\n\nСайт уже есть?",
    "screen_niche": "НИША · 3 / 5\n\nЧем занимаетесь — одной строкой.\n(стоматология, салон, ресторан)",
    "screen_city": "ГОРОД · 4 / 5\n\nГде работаете?",
    "screen_name": "КОНТАКТЫ · 5 / 5\n\nКак к вам обращаться? (ФИО)",
    "screen_phone": "Телефон для связи:",
    "screen_tg": "Telegram для связи:",
    "screen_email": "Email (или Пропустить):",

    "filter": (
        "Этот формат — не наш.\n"
        "Мы работаем с бизнесом, где проект окупается\n"
        "за 1–2 месяца, и берёмся за систему целиком.\n\n"
        "Что поможет бесплатно:\n"
        "чек-лист «5 причин, почему сайт не продаёт»."
    ),
    "checklist": (
        "Чек-лист «5 причин, почему сайт не продаёт»\n\n"
        "1. Нет одного главного CTA\n"
        "2. Цена не зафиксирована\n"
        "3. Нет социального доказательства\n"
        "4. Заявка в мессенджере, а не в CRM\n"
        "5. Сайт не оптимизирован под мобильные\n\n"
        "Исправляем? → /start"
    ),

    "svc_prefix": "Услуга: {name}\nОриентир: {price}\n\nОпишите задачу кратко:",
    "budget_prefix": (
        "УРОВЕНЬ · {level}\n\n"
        "Цена: {price} ₽\n"
        "(первым 3 клиентам)\n\n"
        "{desc}"
    ),
    "budget_all_levels": "Все уровни:",
    "budget_manual": (
        "Тогда вам — система целиком.\n\n"
        "«{label}»: {price} ₽\n\n"
        "{desc}"
    ),

    "price_list": (
        "ПРАЙС-ЛИСТ\n\n"
        "ПАКЕТЫ\n\n"
        "Старт — 29 000 ₽ · 2–3 недели\n"
        "Лендинг до 5 экранов, мобильная адаптация,\n"
        "форма заявки, SEO, поддержка 1 месяц\n\n"
        "Бизнес — 59 000 ₽ · до месяца\n"
        "Лендинг до 8 экранов / сайт до 5 страниц,\n"
        "кастомный дизайн, CRM, SEO, аналитика,\n"
        "поддержка 2 месяца\n\n"
        "Премиум — 112 000 ₽ · от месяца\n"
        "Сайт до 10+ страниц / интернет-магазин,\n"
        "полный UX/UI, CRM + оплата, AI-ассистент,\n"
        "Telegram-бот, A/B тесты, поддержка 3 месяца\n\n"
        "—\n\n"
        "ОТДЕЛЬНЫЕ УСЛУГИ\n\n"
        "Лендинг / сайт — 35 000 ₽\n"
        "Telegram-бот — 20 000 ₽\n"
        "Автоматизация — 45 000 ₽\n"
        "AI-ассистент — 60 000 ₽\n"
        "Онлайн-оплата — 10 000 ₽\n\n"
        "Цены для первых 3 клиентов.\n"
        "Точную стоимость скажем после разговора."
    ),

    "works_title": "Наши работы — каждый проект рабочий:",

    "call_confirm": (
        "Записали.\n\n"
        "Позвоним с +7 951 592-26-18\n"
        "Если срочно — напишите в Telegram:"
    ),
    "call_lead": "СОЗВОН · запрос",

    "done_confirm": (
        "Заявка в студии.\n\n"
        "Договор уже собран — данные подставлены.\n"
        "Ответим в течение 15 минут."
    ),
    "done_lead": "НОВАЯ ЗАЯВКА · {level}",
    "site_form_lead": "ЗАЯВКА С САЙТА",

    "error_generic": "Что-то пошло не так. Попробуйте /start",
    "error_contract": (
        "Заявка принята.\n\n"
        "Данные получили. Ответим в течение 15 минут.\n\n"
        "Связаться: https://t.me/noir_lab42"
    ),
    "state_lost": "Отправьте /start чтобы начать.",

    "estimator_title": "Калькулятор проекта",
    "estimator_q1": "Какой тип проекта?",
    "estimator_q2": "Сколько экранов/страниц нужно?",
    "estimator_q3": "Нужна ли интеграция?",
    "estimator_result": (
        "Расчёт проекта:\n\n"
        "Тип: {type}\n"
        "Экраны: {screens}\n"
        "Интеграции: {integrations}\n\n"
        "Примерная стоимость: {price}\n\n"
        "Точную стоимость скажем после разговора."
    ),

    "dashboard_link": (
        "Личный кабинет:\n\n"
        "Ваш кабинет: {url}\n\n"
        "Там вы можете:\n"
        "• Смотреть прогресс проекта\n"
        "• Оплачивать счета\n"
        "• Скачивать документы\n"
        "• Видеть таймлайн"
    ),

    "payment_title": "Оплата",
    "payment_q": "Выберите способ оплаты:",
    "payment_qr": "Оплатить через QR-код",
    "payment_tbank": "Оплатить через Т-Банк",

    "status_title": "Статус проекта",
    "status_empty": "У вас пока нет проектов. Оставьте заявку: /start",

    "settings_title": "Настройки",
    "settings_lang": "Язык: Русский",
    "settings_notify": "Уведомления: Включены",

    "pay_title": "Оплата",
    "pay_confirm": "Оплата принята к проверке\n\nСсылка выслана в сообщении выше.",
}


# ── Keyboards ────────────────────────────────────────────
def kb_inline(buttons):
    return {"inline_keyboard": buttons}


def kb_main():
    return kb_inline([
        [{"text": "Оценить проект", "callback_data": "menu:eval"},
         {"text": "Подобрать решение", "callback_data": "menu:sol"}],
        [{"text": "Прайс-лист", "callback_data": "menu:price"},
         {"text": "Работы", "callback_data": "menu:works"}],
        [         {"text": "Калькулятор", "callback_data": "estimator:start"},
         {"text": "Кабинет", "callback_data": "dashboard:link"}],
        [{"text": "Оплата", "callback_data": "pay:start"},
         {"text": "Оставить заявку", "callback_data": "flow:start"}],
    ])


def kb_goal():
    return kb_inline([
        [{"text": "Заявки и продажи", "callback_data": "goal:leads"},
         {"text": "Доверие и имидж", "callback_data": "goal:trust"}],
        [{"text": "Экономия времени", "callback_data": "goal:time"},
         {"text": "Всё вместе", "callback_data": "goal:all"}],
    ])


def kb_site():
    return kb_inline([
        [{"text": "Нет", "callback_data": "site:no"},
         {"text": "Есть, но не работает", "callback_data": "site:bad"}],
        [{"text": "Есть, нужен редизайн", "callback_data": "site:redesign"}],
    ])


def kb_budget(level):
    return kb_inline([
        [{"text": "Это мой уровень", "callback_data": "budget:ok"},
         {"text": "Показать другие", "callback_data": "budget:show"}],
        [{"text": "Нужен созвон", "callback_data": "budget:call"}],
    ])


def kb_budget_levels():
    return kb_inline([
        [{"text": "Старт — 29K", "callback_data": "budget:start"},
         {"text": "Бизнес — 59K", "callback_data": "budget:business"}],
        [{"text": "Премиум — 112K", "callback_data": "budget:premium"}],
        [{"text": "Нужен созвон", "callback_data": "budget:call"}],
    ])


def kb_budget_manual(level):
    return kb_inline([
        [{"text": "Это мой уровень", "callback_data": f"budget:confirm:{level}"}],
        [{"text": "Нужен созвон", "callback_data": "budget:call"}],
        [{"text": "Показать другие", "callback_data": "budget:show"}],
    ])


def kb_services():
    return kb_inline([
        [{"text": "Лендинг / сайт", "callback_data": "svc:landing"},
         {"text": "Telegram-бот", "callback_data": "svc:bot"}],
        [{"text": "Автоматизация", "callback_data": "svc:auto"},
         {"text": "AI-ассистент", "callback_data": "svc:ai"}],
        [{"text": "Онлайн-оплата", "callback_data": "svc:payment"}],
        [{"text": "Назад", "callback_data": "menu"}],
    ])


def kb_works():
    return kb_inline([
        [{"text": "Стоматология · запись", "url": f"{SITE_URL}/topdent.html"}],
        [{"text": "Все работы", "url": f"{SITE_URL}/cases.html"}],
    ])


def kb_filter():
    return kb_inline([
        [{"text": "Получить чек-лист", "callback_data": "filter:checklist"}],
        [{"text": "Всё равно оставить заявку", "callback_data": "filter:force"}],
        [{"text": "В главное меню", "callback_data": "menu"}],
    ])


def kb_done():
    return kb_inline([
        [{"text": "Написать в Telegram", "url": "https://t.me/vxrxntsxff"}],
        [{"text": "В главное меню", "callback_data": "menu"}],
    ])


def kb_cancel():
    return kb_inline([[{"text": "Отмена", "callback_data": "menu"}]])


def kb_skip():
    return kb_inline([
        [{"text": "Пропустить", "callback_data": "skip"},
         {"text": "Отмена", "callback_data": "menu"},],
    ])


def kb_pay_start():
    return kb_inline([
        [{"text": "Через Т-Банк", "url": PAYMENT_LINK or "https://t.me/noir_lab42"}],
        [{"text": "Показать QR", "callback_data": "pay:qr"},
         {"text": "Главное меню", "callback_data": "menu"}],
    ])


def kb_pay_back():
    return kb_inline([
        [{"text": "Я оплатил", "callback_data": "pay:confirm"}],
        [{"text": "Главное меню", "callback_data": "menu"}],
    ])


def kb_after_eval():
    return kb_inline([
        [{"text": "Оставить заявку", "callback_data": "flow:start"}],
        [{"text": "В главное меню", "callback_data": "menu"}],
    ])


def kb_after_demo():
    return kb_inline([
        [{"text": "Показать демо", "url": f"{SITE_URL}/topdent.html"}],
        [{"text": "Оставить заявку", "callback_data": "flow:start"}],
        [{"text": "В главное меню", "callback_data": "menu"}],
    ])


def kb_lead(user_data):
    buttons = []
    if user_data.get("telegram"):
        buttons.append([{"text": "Написать в TG",
                         "url": f"https://t.me/{user_data['telegram'].lstrip('@')}"}])
    elif user_data.get("phone"):
        buttons.append([{"text": "Позвонить", "url": f"tel:{user_data['phone']}"}])
    return buttons


# ── Telegram API ─────────────────────────────────────────
TELEGRAM_BASES = [
    "https://api.telegram.org/bot",
    "https://t.me/botapi/bot",
]
def tg(method, data=None):
    payload = json.dumps(data or {}).encode()
    for base in TELEGRAM_BASES:
        url = f"{base}{BOT_TOKEN}/{method}"
        req = urllib.request.Request(url, data=payload)
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
                if result.get("ok"):
                    return result
                log.warning("tg.%s via %s: %s", method, base, result.get("description", ""))
        except Exception as e:
            log.warning("tg.%s via %s failed: %s", method, base, str(e)[:200])
            continue
    log.error("tg.%s ALL ENDPOINTS FAILED", method)
    return {"ok": False}


def get_username(chat_id):
    """Fetch username from Telegram API by chat_id."""
    result = tg("getChat", {"chat_id": chat_id})
    if result.get("ok"):
        return result.get("result", {}).get("username", "")
    return ""


def send(chat_id, text, reply_markup=None, parse_mode=None):
    data = {"chat_id": chat_id, "text": text}
    if parse_mode:
        data["parse_mode"] = parse_mode
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    return tg("sendMessage", data)


def send_lead(text, buttons=None):
    markup = kb_inline(buttons) if buttons else None
    msg = {"chat_id": LEADS_CHAT_ID, "text": text}
    if markup:
        msg["reply_markup"] = json.dumps(markup)
    log.info("send_lead → chat %s (len=%d)", LEADS_CHAT_ID, len(text))
    result = tg("sendMessage", msg)
    if not result.get("ok"):
        detail = result.get("description", "unknown")
        log.error("send_lead FAIL → chat %s: %s", LEADS_CHAT_ID, detail)
        if OWNER_ID:
            fallback = {"chat_id": OWNER_ID, "text": f"[Из группы не доставлено]\n\n{text}"}
            if markup:
                fallback["reply_markup"] = json.dumps(markup)
            fb_result = tg("sendMessage", fallback)
            if not fb_result.get("ok"):
                log.error("send_lead OWNER FAIL → %s: %s", OWNER_ID, fb_result.get("description",""))
            else:
                log.info("send_lead fallback → OWNER %s ok", OWNER_ID)
    else:
        log.info("send_lead OK → chat %s msg_id=%s", LEADS_CHAT_ID, result.get("result",{}).get("message_id",""))
    return result


def contract_url(params):
    qs = urllib.parse.urlencode({k: v for k, v in params.items() if v})
    return f"{SITE_URL}/dogovor.html?{qs}"


def payment_url(order_id, amount=None, name=None):
    """Generate payment page URL with optional params."""
    qs = urllib.parse.urlencode({
        "order": order_id,
        "amount": amount or "",
        "name": name or "",
    })
    return f"{SITE_URL}/payment?{qs}"


def create_order_id(data):
    """Generate a unique order ID from client data."""
    import random as _r
    date_str = now_kem().strftime("%Y%m%d")
    rand = _r.randint(100, 999)
    name_part = (data.get("name") or "client").replace(" ", "").lower()[:4]
    return f"NOIR-{date_str}-{name_part}-{rand}"


# ── Admin ────────────────────────────────────────────────

def kb_admin():
    return kb_inline([
        [{"text": "Лиды", "callback_data": "admin:leads"},
         {"text": "Проекты", "callback_data": "admin:projects"}],
        [{"text": "Оплаты", "callback_data": "admin:payments"},
         {"text": "Статистика", "callback_data": "admin:stats"}],
        [{"text": "Google Sheets", "callback_data": "admin:sheets"},
         {"text": "NOIR.md", "callback_data": "admin:noir_playbook"}],
    ])


def kb_admin_lead(lead_id):
    return kb_inline([
        [{"text": "Принять", "callback_data": f"admin:accept:{lead_id}"},
         {"text": "Отклонить", "callback_data": f"admin:reject:{lead_id}"}],
        [{"text": "Написать", "callback_data": f"admin:msg:{lead_id}"}],
    ])


def kb_admin_project(project_id):
    return kb_inline([
        [{"text": "Название", "callback_data": f"admin:edit_name:{project_id}"},
         {"text": "Этап", "callback_data": f"admin:edit_stage:{project_id}"}],
        [{"text": "Прогресс", "callback_data": f"admin:edit_progress:{project_id}"},
         {"text": "Цена", "callback_data": f"admin:edit_price:{project_id}"}],
        [{"text": "+ Обновление", "callback_data": f"admin:add_update:{project_id}"}],
        [{"text": "Подтвердить оплату", "callback_data": f"admin:pay_ask:{project_id}"},
         {"text": "Закрыть", "callback_data": f"admin:close:{project_id}"}],
    ])


def kb_admin_pay_select(project_id):
    return kb_inline([
        [{"text": "100%", "callback_data": f"admin:pay:100:{project_id}"}],
        [{"text": "50%", "callback_data": f"admin:pay:50:{project_id}"}],
        [{"text": "Произвольная", "callback_data": f"admin:pay:custom:{project_id}"}],
        [{"text": "← Назад", "callback_data": f"admin:project:{project_id}"}],
    ])


STAGE_LABELS = {
    "brief": "Бриф", "research": "Исследование", "design": "Дизайн",
    "development": "Разработка", "integrations": "Интеграции", "launch": "Запуск",
}


def kb_admin_stage_select(project_id):
    return kb_inline([
        [{"text": "Бриф", "callback_data": f"admin:set_stage:{project_id}:brief"},
         {"text": "Исследование", "callback_data": f"admin:set_stage:{project_id}:research"}],
        [{"text": "Дизайн", "callback_data": f"admin:set_stage:{project_id}:design"},
         {"text": "Разработка", "callback_data": f"admin:set_stage:{project_id}:development"}],
        [{"text": "Интеграции", "callback_data": f"admin:set_stage:{project_id}:integrations"},
         {"text": "Запуск", "callback_data": f"admin:set_stage:{project_id}:launch"}],
        [{"text": "Назад", "callback_data": f"admin:project:{project_id}"}],
    ])


def handle_admin(chat_id):
    if chat_id != OWNER_ID:
        send(chat_id, "Нет доступа")
        return
    send(chat_id, "Панель управления", reply_markup=kb_admin())


def _sheets_get_clients():
    """Read all clients from Google Sheets."""
    if not _sheets_api or not SPREADSHEET_ID:
        return []
    result = _sheets_api("GET", f"/values/{SHEETS.get('clients','Clients')}!A:J")
    if not result or "values" not in result:
        return []
    clients = []
    for i, row in enumerate(result["values"][1:], start=2):
        name_val = str(row[0]).strip() if len(row) > 0 else ""
        phone_val = str(row[1]).strip() if len(row) > 1 else ""
        if name_val or phone_val:
            clients.append({
                "row": i,
                "name": name_val,
                "phone": phone_val,
                "telegram": str(row[2]) if len(row) > 2 else "",
                "email": str(row[3]) if len(row) > 3 else "",
                "city": str(row[4]) if len(row) > 4 else "",
                "niche": str(row[5]) if len(row) > 5 else "",
                "budget": str(row[6]) if len(row) > 6 else "",
                "source": str(row[7]) if len(row) > 7 else "",
                "status": str(row[8]) if len(row) > 8 else "Новый",
                "date": str(row[9]) if len(row) > 9 else "",
            })
    return clients


def _sheets_get_projects_all():
    """Read all projects from Google Sheets."""
    if not _sheets_api or not SPREADSHEET_ID:
        return []
    result = _sheets_api("GET", f"/values/{SHEETS.get('projects','Projects')}!A:K")
    if not result or "values" not in result:
        return []
    projects = []
    for i, row in enumerate(result["values"][1:], start=2):
        client_val = str(row[1]).strip() if len(row) > 1 else ""
        if client_val:
            projects.append({
                "row": i,
                "client": client_val,
                "name": str(row[2]) if len(row) > 2 else "",
                "package": str(row[3]) if len(row) > 3 else "",
                "status": str(row[4]) if len(row) > 4 else "",
                "stage": str(row[5]) if len(row) > 5 else "",
                "progress": str(row[6]) if len(row) > 6 else "0",
                "deadline": str(row[7]) if len(row) > 7 else "",
                "price": str(row[8]) if len(row) > 8 else "",
                "paid": str(row[9]) if len(row) > 9 else "0",
                "remaining": str(row[10]) if len(row) > 10 else "",
            })
    return projects


def _do_payment(chat_id, rid, proj, amount, label):
    client_name = proj.get("client", "")
    project_name = proj.get("name", "")
    sheets_payment(project=project_name, client=client_name, amount=str(int(amount)), type=label, status="Оплачен", method="Перевод")
    paid_str = str(proj.get("paid", "0")).replace(" ", "").replace("\xa0", "")
    try:
        old_paid = float(paid_str)
    except ValueError:
        old_paid = 0
    new_paid = old_paid + amount
    price_str = str(proj.get("price", "0")).replace(" ", "").replace("\xa0", "")
    try:
        price = float(price_str)
    except ValueError:
        price = 0
    remaining = max(0, price - new_paid)
    sheets_update_project_by_row(rid, "paid", str(int(new_paid)))
    sheets_update_project_by_row(rid, "remaining", str(int(remaining)))
    if new_paid >= price:
        sheets_update_project_by_row(rid, "status", "Оплачен")
    send(chat_id, f"Оплата: {int(amount)} ₽ ({label})\nОплачено: {int(new_paid)} ₽\nОстаток: {int(remaining)} ₽")


def _handle_admin_callback(chat_id, data):
    if chat_id != OWNER_ID:
        return
    parts = data.split(":")
    log.info("ADMIN_CALLBACK chat=%s data=%s parts=%s", chat_id, data, parts)

    try:
        _do_admin_callback(chat_id, data, parts)
    except Exception as e:
        log.error("ADMIN_CALLBACK ERROR data=%s: %s\n%s", data, e, traceback.format_exc())
        send(chat_id, f"Ошибка: {e}")


def _do_admin_callback(chat_id, data, parts):
    if data == "admin:leads":
        leads = _sheets_get_clients()
        log.info("ADMIN_LEADS count=%d", len(leads))
        if not leads:
            send(chat_id, "Нет лидов")
            return
        for lead in leads[-5:]:
            status = lead.get("status", "Новый")
            rid = str(lead.get("row", 0))
            text = (
                f"{lead.get('name','—')}\n"
                f"Тел: {lead.get('phone','—')}\n"
                f"TG: @{lead.get('telegram','—')}\n"
                f"Город: {lead.get('city','—')}\n"
                f"Статус: {status}"
            )
            send(chat_id, text, reply_markup=kb_admin_lead(rid))

    elif data == "admin:projects":
        projects = _sheets_get_projects_all()
        log.info("ADMIN_PROJECTS count=%d", len(projects))
        if not projects:
            send(chat_id, "Нет проектов")
            return
        for proj in projects[-5:]:
            stage_label = STAGE_LABELS.get(proj.get("stage",""), proj.get("stage","—"))
            rid = str(proj.get("row", 0))
            text = (
                f"{proj.get('name','—')}\n"
                f"Клиент: {proj.get('client','—')}\n"
                f"Пакет: {proj.get('package','—')}\n"
                f"Этап: {stage_label}\n"
                f"Прогресс: {proj.get('progress','0')}%\n"
                f"Цена: {proj.get('price','—')} ₽"
            )
            send(chat_id, text, reply_markup=kb_admin_project(rid))

    elif data.startswith("admin:project:"):
        rid = parts[2]
        projects = _sheets_get_projects_all()
        for proj in projects:
            if str(proj.get("row", 0)) == rid:
                stage_label = STAGE_LABELS.get(proj.get("stage",""), proj.get("stage","—"))
                text = (
                    f"{proj.get('name','—')}\n"
                    f"Клиент: {proj.get('client','—')}\n"
                    f"Пакет: {proj.get('package','—')}\n"
                    f"Этап: {stage_label}\n"
                    f"Прогресс: {proj.get('progress','0')}%\n"
                    f"Цена: {proj.get('price','—')} ₽\n"
                    f"Оплачено: {proj.get('paid','0')} ₽\n"
                    f"Остаток: {proj.get('remaining','—')} ₽"
                )
                send(chat_id, text, reply_markup=kb_admin_project(rid))
                return
        send(chat_id, f"Проект #{rid} не найден")

    elif data.startswith("admin:edit_name:"):
        rid = parts[2]
        state_set(chat_id, {"admin_action": "edit_name", "project_id": rid})
        send(chat_id, "Новое название:", reply_markup=kb_cancel())

    elif data.startswith("admin:edit_stage:"):
        rid = parts[2]
        send(chat_id, "Выберите этап:", reply_markup=kb_admin_stage_select(rid))

    elif data.startswith("admin:set_stage:"):
        rid = parts[2]
        stage = parts[3]
        label = STAGE_LABELS.get(stage, stage)
        if sheets_update_project:
            ok = sheets_update_project_by_row(rid, "stage", label)
            send(chat_id, f"Этап → {label}" if ok else "Ошибка")
        else:
            send(chat_id, f"Этап → {label} (Sheets не подключены)")

    elif data.startswith("admin:edit_progress:"):
        rid = parts[2]
        state_set(chat_id, {"admin_action": "edit_progress", "project_id": rid})
        send(chat_id, "Прогресс (0-100):", reply_markup=kb_cancel())

    elif data.startswith("admin:edit_price:"):
        rid = parts[2]
        state_set(chat_id, {"admin_action": "edit_price", "project_id": rid})
        send(chat_id, "Новая цена:", reply_markup=kb_cancel())

    elif data.startswith("admin:add_update:"):
        rid = parts[2]
        state_set(chat_id, {"admin_action": "add_update", "project_id": rid})
        send(chat_id, "Текст обновления:", reply_markup=kb_cancel())

    elif data.startswith("admin:pay_ask:"):
        rid = parts[2]
        send(chat_id, "Сколько оплатил?", reply_markup=kb_admin_pay_select(rid))

    elif data.startswith("admin:pay:") and len(parts) >= 4:
        rid = parts[3]
        pct = parts[2]
        projects = _sheets_get_projects_all()
        proj = None
        for p in projects:
            if str(p.get("row", 0)) == rid:
                proj = p
                break
        if not proj:
            send(chat_id, "Проект не найден")
            return
        price_str = str(proj.get("price", "0")).replace(" ", "").replace("\xa0", "")
        try:
            price = float(price_str)
        except ValueError:
            send(chat_id, "Цена не задана")
            return
        if pct == "custom":
            state_set(chat_id, {"admin_action": "pay_custom", "project_id": rid, "price": price})
            send(chat_id, "Сумма оплаты:", reply_markup=kb_cancel())
            return
        amount = price * int(pct) / 100
        _do_payment(chat_id, rid, proj, amount, f"Аванс {pct}%")

    elif data.startswith("admin:close:"):
        rid = parts[2]
        if sheets_update_project:
            sheets_update_project_by_row(rid, "status", "Закрыт")
        send(chat_id, "Проект закрыт")

    elif data == "admin:payments":
        if _sheets_api and SPREADSHEET_ID:
            result = _sheets_api("GET", f"/values/{SHEETS.get('payments','Payments')}!A:I")
            if result and "values" in result and len(result["values"]) > 1:
                lines = []
                for row in result["values"][-5:]:
                    date = row[0] if len(row) > 0 else ""
                    proj = row[1] if len(row) > 1 else ""
                    amount = row[3] if len(row) > 3 else ""
                    status = row[5] if len(row) > 5 else ""
                    lines.append(f"{date} · {proj} · {amount} · {status}")
                send(chat_id, "Оплаты:\n" + "\n".join(lines))
            else:
                send(chat_id, "Оплат пока нет")
        else:
            send(chat_id, "Google Sheets не подключены")

    elif data == "admin:stats":
        clients = _sheets_get_clients()
        projects = _sheets_get_projects_all()
        new_count = sum(1 for c in clients if c.get("status", "Новый") == "Новый")
        active_count = sum(1 for p in projects if p.get("status", "") not in ("Закрыт", ""))
        text = (
            f"Статистика\n\n"
            f"Всего лидов: {len(clients)}\n"
            f"Новых: {new_count}\n"
            f"Проектов: {len(projects)}\n"
            f"Активных: {active_count}"
        )
        send(chat_id, text)

    elif data == "admin:sheets":
        sheets_ok = bool(_sheets_api and SPREADSHEET_ID)
        if sheets_ok:
            try:
                clients = _sheets_get_clients()
                projects = _sheets_get_projects_all()
                send(chat_id, f"Google Sheets: подключены\nКлиентов: {len(clients)}\nПроектов: {len(projects)}")
            except Exception:
                send(chat_id, "Google Sheets: подключены (ошибка чтения)")
        else:
            send(chat_id, "Google Sheets: не настроены")

    elif data == "admin:noir_playbook":
        playbook_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "NOIR.md")
        with open(playbook_path, "rb") as f:
            content = f.read()
        import io
        boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
        body = io.BytesIO()
        body.write(f"--{boundary}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="chat_id"\r\n\r\n')
        body.write(str(chat_id).encode())
        body.write(b"\r\n")
        body.write(f"--{boundary}\r\n".encode())
        body.write(b'Content-Disposition: form-data; name="document"; filename="NOIR.md"\r\n')
        body.write(b"Content-Type: text/markdown; charset=utf-8\r\n\r\n")
        body.write(content)
        body.write(b"\r\n")
        body.write(f"--{boundary}--\r\n".encode())
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
        req = urllib.request.Request(url, data=body.getvalue(), method="POST")
        req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if not result.get("ok"):
                send(chat_id, f"Ошибка: {result.get('description', '')}")
            else:
                log.info("NOIR.md sent OK chat=%s", chat_id)

    elif parts[1] == "accept" and len(parts) > 2:
        rid = parts[2]
        if _sheets_api and SPREADSHEET_ID:
            try:
                _sheets_api("PUT",
                    f"/values/{SHEETS['clients']}!I{rid}?valueInputOption=USER_ENTERED",
                    {"values": [["Активный"]]})
            except Exception as e:
                log.error("accept error row=%s: %s", rid, e)
        send(chat_id, "Лид принят")

    elif parts[1] == "reject" and len(parts) > 2:
        rid = parts[2]
        if _sheets_api and SPREADSHEET_ID:
            try:
                _sheets_api("PUT",
                    f"/values/{SHEETS['clients']}!I{rid}?valueInputOption=USER_ENTERED",
                    {"values": [["Отклонён"]]})
            except Exception as e:
                log.error("reject error row=%s: %s", rid, e)
        send(chat_id, "Лид отклонён")

    elif parts[1] == "msg" and len(parts) > 2:
        rid = parts[2]
        state_set(chat_id, {"admin_action": "send_to_client", "project_id": rid})
        send(chat_id, "Текст сообщения:", reply_markup=kb_cancel())


def pkg_desc(level):
    _descs = {
        "start": (
            "Лендинг до 5 экранов · мобильная адаптация\n"
            "Форма заявки · SEO-базовая настройка\n"
            "Срок: 2–3 недели · поддержка 1 месяц\n"
            "Договор · чек НПД"
        ),
        "business": (
            "Лендинг до 8 экранов / сайт до 5 страниц\n"
            "Кастомный дизайн · интеграция с CRM\n"
            "SEO · аналитика\n"
            "Срок: до месяца · поддержка 2 месяца\n"
            "Договор · чек НПД"
        ),
        "premium": (
            "Сайт до 10+ страниц / интернет-магазин\n"
            "Полный UX/UI · CRM + оплата\n"
            "AI-ассистент · Telegram-бот · A/B тесты\n"
            "Срок: от месяца · поддержка 3 месяца\n"
            "Приоритет · договор · чек НПД"
        ),
    }
    return _descs.get(level, _descs["business"])


# ── State (Upstash Redis with fallback) ──────────────────
_mem = {}  # fallback when Redis unavailable


def _restore_json(s):
    """Parse JSON where Vercel stripped double-quotes from keys and string values.
    Uses a proper tokenizer that handles nested objects and colons in values."""
    import re
    
    # First, quote any unquoted keys
    s = re.sub(r'([{,]\s*)([^"\\s{},:]+)(\s*:)', r'\1"\2"\3', s)
    
    def skip_ws(s, pos):
        while pos < len(s) and s[pos] in ' \t\n\r':
            pos += 1
        return pos

    def parse_value(s, pos):
        pos = skip_ws(s, pos)
        if pos >= len(s):
            raise ValueError("Unexpected end")
        
        if s[pos] == '{':
            return parse_object(s, pos)
        elif s[pos] == '[':
            return parse_array(s, pos)
        elif s[pos] == '"':
            return parse_string(s, pos)
        else:
            # Number, boolean, null, or unquoted string
            start = pos
            while pos < len(s) and s[pos] not in ',}]':
                pos += 1
            val = s[start:pos].strip()
            if re.match(r'^-?\d+(\.\d+)?$', val):
                return (float(val) if '.' in val else int(val), pos)
            elif val == 'true':
                return (True, pos)
            elif val == 'false':
                return (False, pos)
            elif val == 'null':
                return (None, pos)
            else:
                return (val, pos)  # unquoted string

    def parse_string(s, pos):
        pos += 1  # skip opening "
        result = []
        while pos < len(s) and s[pos] != '"':
            if s[pos] == '\\' and pos + 1 < len(s):
                result.append(s[pos+1])
                pos += 2
            else:
                result.append(s[pos])
                pos += 1
        return (''.join(result), pos + 1)

    def parse_object(s, pos):
        pos += 1  # skip {
        obj = {}
        while True:
            pos = skip_ws(s, pos)
            if pos < len(s) and s[pos] == '}':
                return (obj, pos + 1)
            if pos >= len(s):
                return (obj, pos)
            
            if s[pos] == '"':
                key, pos = parse_string(s, pos)
            else:
                start = pos
                while pos < len(s) and s[pos] != ':':
                    pos += 1
                key = s[start:pos].strip()
            
            pos = skip_ws(s, pos)
            if pos < len(s) and s[pos] == ':':
                pos += 1
            else:
                raise ValueError(f"Expected : at {pos}")
            
            val, pos = parse_value(s, pos)
            obj[key] = val
            
            pos = skip_ws(s, pos)
            if pos < len(s) and s[pos] == ',':
                pos += 1
            elif pos < len(s) and s[pos] == '}':
                return (obj, pos + 1)
            else:
                break
        return (obj, pos)

    def parse_array(s, pos):
        pos += 1  # skip [
        arr = []
        while True:
            pos = skip_ws(s, pos)
            if pos >= len(s) or s[pos] == ']':
                return (arr, pos + 1)
            val, pos = parse_value(s, pos)
            arr.append(val)
            pos = skip_ws(s, pos)
            if pos < len(s) and s[pos] == ',':
                pos += 1
            elif pos < len(s) and s[pos] == ']':
                return (arr, pos + 1)
            else:
                break
        return (arr, pos)

    result, _ = parse_value(s, 0)
    return result


def _redis(*args):
    if not UPSTASH_URL or not UPSTASH_TOK:
        return None
    body = json.dumps(list(args)).encode()
    req = urllib.request.Request(UPSTASH_URL, data=body)
    req.add_header("Authorization", f"Bearer {UPSTASH_TOK}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read()).get("result")
    except Exception as e:
        log.warning("upstash.%s failed: %s", args[0], e)
        return None


def state_get(chat_id):
    key = f"noir:state:{chat_id}"
    raw = _redis("GET", key)
    if raw is not None:
        try:
            return json.loads(raw)
        except Exception:
            return None
    return _mem.get(chat_id)


def state_set(chat_id, data):
    key = f"noir:state:{chat_id}"
    payload = json.dumps(data, ensure_ascii=False)
    ok = _redis("SET", key, payload, "EX", "3600")
    if ok is None:
        _mem[chat_id] = data


def state_del(chat_id):
    key = f"noir:state:{chat_id}"
    _redis("DEL", key)
    _mem.pop(chat_id, None)


# ── Scoring ──────────────────────────────────────────────
def score(data):
    goal = data.get("goal", "")
    site = data.get("site", "")
    if goal == "all":
        return "premium"
    if site == "redesign":
        return "business"
    return "business"


def score_solution(sol_type):
    return {"leads": "business", "routine": "business",
            "nosys": "business", "all": "premium"}.get(sol_type, "business")


# ── Handlers ─────────────────────────────────────────────
def handle_start(chat_id, username=""):
    if not username:
        username = get_username(chat_id)
    state_del(chat_id)
    state_set(chat_id, {"step": None, "data": {}, "username": username})
    result = send(chat_id, T["welcome"], reply_markup=kb_main())
    if not result.get("ok"):
        log.error("handle_start send FAILED: %s", result)
    else:
        log.info("handle_start sent OK to chat=%s", chat_id)
    log.info("start user=%s chat=%s", username, chat_id)


def handle_menu(chat_id):
    state_del(chat_id)
    send(chat_id, T["menu"], reply_markup=kb_main())


def _handle_text(chat_id, text, st, username=""):
    step = st.get("step", "")
    username = st.get("username", "")

    # ── Admin text input ──
    admin_action = st.get("admin_action", "")
    if admin_action and chat_id == OWNER_ID:
        rid = st.get("project_id", "")
        state_del(chat_id)
        # Resolve row to client name for add_update / send_to_client
        client_name = ""
        if _sheets_api and SPREADSHEET_ID:
            try:
                result = _sheets_api("GET", f"/values/{SHEETS.get('clients','Clients')}!A:J")
                if result and "values" in result:
                    idx = int(rid) - 1  # row 2 = index 1
                    if 0 <= idx < len(result["values"]):
                        row = result["values"][idx]
                        client_name = row[0] if len(row) > 0 else ""
            except Exception:
                pass
        if admin_action == "edit_name" and sheets_update_project_by_row:
            ok = sheets_update_project_by_row(rid, "name", text)
            send(chat_id, f"Название → {text}" if ok else "Ошибка")
        elif admin_action == "edit_progress" and sheets_update_project_by_row:
            ok = sheets_update_project_by_row(rid, "progress", text)
            send(chat_id, f"Прогресс → {text}%" if ok else "Ошибка")
        elif admin_action == "edit_price" and sheets_update_project_by_row:
            ok = sheets_update_project_by_row(rid, "price", text)
            send(chat_id, f"Цена → {text} ₽" if ok else "Ошибка")
        elif admin_action == "add_update" and sheets_add_update:
            ok = sheets_add_update(client_name or rid, text)
            send(chat_id, "Обновление добавлено" if ok else "Ошибка")
        elif admin_action == "pay_custom":
            price = st.get("price", 0)
            try:
                amount = float(text.replace(" ", "").replace("\xa0", "").replace(",", "."))
            except ValueError:
                send(chat_id, "Введите число")
                return
            projects = _sheets_get_projects_all()
            proj = None
            for p in projects:
                if str(p.get("row", 0)) == rid:
                    proj = p
                    break
            if proj:
                _do_payment(chat_id, rid, proj, amount, "Частичная оплата")
            else:
                send(chat_id, "Проект не найден")
        elif admin_action == "send_to_client":
            if sheets_find_client and client_name:
                client = sheets_find_client(client_name)
                if client and client.get("telegram"):
                    tg("sendMessage", {
                        "chat_id": client["telegram"],
                        "text": f"NOIR · Обновление\n\n{text}"
                    })
                    send(chat_id, "Сообщение отправлено")
                else:
                    send(chat_id, "Telegram клиента не найден")
            else:
                send(chat_id, "Клиент не найден")
        else:
            send(chat_id, "Действие выполнено")
        return

    if step == "eval_material":
        state_del(chat_id)
        client_link = f"https://t.me/{username}" if username else f"tg://user?id={chat_id}"
        send_lead(
            f"РАЗБОР · ожидает человека\n\n"
            f"Материал от клиента:\n{text[:500]}",
            [[{"text": "Ответить клиенту", "url": client_link}]]
        )
        send(chat_id, T["eval_confirm"], reply_markup=kb_after_eval())
        log.info("eval received chat=%s", chat_id)
        return

    if step == "pain":
        st["data"]["pain"] = text
        st["step"] = "goal"
        state_set(chat_id, st)
        send(chat_id, T["screen_goal"], reply_markup=kb_goal())
        return

    if step == "niche":
        st["data"]["niche"] = text
        st["step"] = "city"
        state_set(chat_id, st)
        send(chat_id, T["screen_city"], reply_markup=kb_cancel())
        return

    if step == "city":
        st["data"]["city"] = text
        level = score(st["data"])
        st["data"]["level"] = level
        st["step"] = "budget_show"
        state_set(chat_id, st)
        text_msg = T["budget_prefix"].format(
            level=LABELS[level], price=PRICES[level], desc=pkg_desc(level)
        )
        send(chat_id, text_msg, reply_markup=kb_budget(level))
        return

    if step == "name":
        st["data"]["name"] = text
        st["step"] = "phone"
        state_set(chat_id, st)
        send(chat_id, T["screen_phone"], reply_markup=kb_cancel())
        return

    if step == "phone":
        st["data"]["phone"] = text
        tg_username = st.get("username", "")
        if not tg_username:
            tg_username = get_username(chat_id)
            if tg_username:
                st["username"] = tg_username
        log.info("PHONE_STEP chat=%s tg_from_state=%s tg_final=%s", chat_id, st.get("username", ""), tg_username)
        if st["data"].get("need_call"):
            state_del(chat_id)
            send(chat_id, T["call_confirm"], reply_markup=kb_done())
            send_lead(
                T["call_lead"],
                [[{"text": "Клиент",
                   "url": f"https://t.me/{tg_username}" if tg_username
                   else f"tg://user?id={chat_id}"}]]
            )
            log.info("call_request chat=%s", chat_id)
            return
        st["data"]["telegram"] = tg_username
        st["step"] = "email"
        state_set(chat_id, st)
        send(chat_id, T["screen_email"], reply_markup=kb_skip())
        return

    if step == "email":
        st["data"]["email"] = "" if text == "Пропустить" else text
        try:
            _finish_qualification(chat_id, st["data"])
        except Exception as e:
            log.error("qualification error: %s", e)
            state_del(chat_id)
            send(chat_id, T["error_contract"], reply_markup=kb_done())
            err_text = (
                f"ОШИБКА · квалификация\n\n"
                f"Ошибка: {e}\n"
                f"Данные: {json.dumps(st.get('data', {}), ensure_ascii=False)}"
            )
            result = tg("sendMessage", {"chat_id": LEADS_CHAT_ID, "text": err_text})
            if not result.get("ok") and OWNER_ID:
                tg("sendMessage", {"chat_id": OWNER_ID, "text": err_text})
        return

    if step == "svc_name":
        st["data"]["task"] = text
        st["step"] = "name"
        state_set(chat_id, st)
        send(chat_id, T["screen_name"], reply_markup=kb_cancel())
        return

    send(chat_id, T["state_lost"])


def _send_est_int(chat_id, est_type):
    """Send integrations question tailored to project type."""
    q3_variants = {
        "landing": ([{"text": "Нет", "callback_data": "est:int:no"},
                     {"text": "Форма заявки", "callback_data": "est:int:form"}],
                    [{"text": "CRM", "callback_data": "est:int:crm"},
                     {"text": "Оплата", "callback_data": "est:int:pay"}],
                    [{"text": "Полная интеграция", "callback_data": "est:int:all"}]),
        "site":    ([{"text": "Нет", "callback_data": "est:int:no"},
                     {"text": "CRM", "callback_data": "est:int:crm"}],
                    [{"text": "Оплата", "callback_data": "est:int:pay"},
                     {"text": "AI-ассистент", "callback_data": "est:int:ai"}],
                    [{"text": "Полная интеграция", "callback_data": "est:int:all"}]),
        "bot":     ([{"text": "Нет", "callback_data": "est:int:no"},
                     {"text": "CRM", "callback_data": "est:int:crm"}],
                    [{"text": "Оплата", "callback_data": "est:int:pay"},
                     {"text": "Всё", "callback_data": "est:int:all"}]),
        "crm":     ([{"text": "Нет", "callback_data": "est:int:no"},
                     {"text": "Базовая", "callback_data": "est:int:crm"}],
                    [{"text": "С оплатой", "callback_data": "est:int:pay"},
                     {"text": "Полная", "callback_data": "est:int:all"}]),
        "ai":      ([{"text": "Нет", "callback_data": "est:int:no"},
                     {"text": "С CRM", "callback_data": "est:int:crm"}],
                    [{"text": "С оплатой", "callback_data": "est:int:pay"},
                     {"text": "Всё вместе", "callback_data": "est:int:all"}]),
        "pay":     ([{"text": "Нет", "callback_data": "est:int:no"},
                     {"text": "С CRM", "callback_data": "est:int:crm"}],
                    [{"text": "Подписки", "callback_data": "est:int:pay"},
                     {"text": "Полная", "callback_data": "est:int:all"}]),
    }
    row1, row2 = q3_variants.get(est_type, q3_variants["landing"])
    send(chat_id, T["estimator_q3"], reply_markup=kb_inline([row1, row2]))


def handle_callback(chat_id, data):
    st = state_get(chat_id) or {}

    # ── Admin routing ──
    if data.startswith("admin:"):
        _handle_admin_callback(chat_id, data)
        return

    # ── Global routing ──
    if data == "menu":
        handle_menu(chat_id)
        return
    if data == "skip":
        step = st.get("step", "")
        if step == "email":
            st["data"]["email"] = ""
            try:
                _finish_qualification(chat_id, st["data"])
            except Exception as e:
                log.error("qualification error (skip): %s", e)
                state_del(chat_id)
                send(chat_id, T["error_contract"], reply_markup=kb_done())
        return

    # ── Main menu actions ──
    if data == "menu:eval":
        state_set(chat_id, {"step": "eval_material"})
        send(chat_id, T["eval_input"], reply_markup=kb_cancel())
        return
    if data == "menu:sol":
        state_set(chat_id, {"step": "pain", "data": {}, "username": st.get("username", "")})
        send(chat_id, T["screen_pain"], reply_markup=kb_inline([
            [{"text": "Нет заявок", "callback_data": "sol:leads"},
             {"text": "Тону в рутине", "callback_data": "sol:routine"}],
            [{"text": "Нет системы", "callback_data": "sol:nosys"},
             {"text": "Всё сразу", "callback_data": "sol:all"}],
            [{"text": "Отмена", "callback_data": "menu"}],
        ]))
        return
    if data == "menu:price":
        send(chat_id, T["price_list"], reply_markup=kb_main())
        return
    if data == "menu:works":
        send(chat_id, T["works_title"], reply_markup=kb_works())
        return

    # ── Estimator ──
    if data == "estimator:start":
        state_set(chat_id, {"step": "est_type", "data": {}, "username": st.get("username", "")})
        send(chat_id, T["estimator_q1"], reply_markup=kb_inline([
            [{"text": "Лендинг", "callback_data": "est:type:landing"},
             {"text": "Сайт", "callback_data": "est:type:site"}],
            [{"text": "ТГ-бот", "callback_data": "est:type:bot"},
             {"text": "CRM", "callback_data": "est:type:crm"}],
            [{"text": "AI-ассистент", "callback_data": "est:type:ai"},
             {"text": "Оплата", "callback_data": "est:type:pay"}],
        ]))
        return

    if data.startswith("est:type:"):
        est_type = data[9:]
        st.setdefault("data", {})["est_type"] = est_type
        # Skip screens for bot/crm/ai/payment — they don't have "screens"
        if est_type in ("bot", "crm", "ai", "pay"):
            st["step"] = "est_integrations"
            state_set(chat_id, st)
            _send_est_int(chat_id, est_type)
        else:
            st["step"] = "est_screens"
            state_set(chat_id, st)
            send(chat_id, T["estimator_q2"], reply_markup=kb_inline([
                [{"text": "0", "callback_data": "est:screens:none"},
                 {"text": "1–3", "callback_data": "est:screens:few"}],
                [{"text": "4–6", "callback_data": "est:screens:mid"},
                 {"text": "7–10", "callback_data": "est:screens:many"}],
            ]))
        return

    if data.startswith("est:screens:"):
        screens = data[12:]
        st.setdefault("data", {})["est_screens"] = screens
        est_type = st.get("data", {}).get("est_type", "landing")
        st["step"] = "est_integrations"
        state_set(chat_id, st)
        _send_est_int(chat_id, est_type)
        return

    if data.startswith("est:int:"):
        integrations = data[8:]
        d = st.get("data", {})
        est_type = d.get("est_type", "landing")
        screens = d.get("est_screens", "few")

        # Package logic: map selections to packages
        # Старт (29k): landing 1-3 screens, no CRM, no оплата
        # Бизнес (59k): site/bot 4-6 screens + CRM
        # Премиум (112k): site 7-10 + CRM + оплата, or system

        has_crm = integrations in ("crm", "all")
        has_pay = integrations in ("pay", "all")
        has_ai = integrations in ("ai", "all")
        has_form = integrations == "form"

        package = None
        extra_modules = []
        extra_price = 0

        # Determine package — only for landing/site
        if est_type in ("landing", "site"):
            if screens == "none":
                package = ("start", "Старт", 0)
                extra_modules.append("Расчёт после обсуждения")
            elif screens == "few" and not has_crm and not has_pay:
                package = ("start", "Старт", 29000)
            elif screens == "mid" and not has_pay:
                package = ("business", "Бизнес", 59000)
            elif screens in ("many",) or has_pay:
                package = ("premium", "Премиум", 112000)
            else:
                package = ("business", "Бизнес", 59000)
            if has_crm:
                extra_modules.append("CRM")
                extra_price += 20000
            if has_pay:
                extra_modules.append("Онлайн-оплата")
                extra_price += 15000
            if has_ai:
                extra_modules.append("AI-ассистент")
                extra_price += 25000
            if has_form:
                extra_modules.append("Форма заявки")
                extra_price += 5000

        # Individual services — site module prices from website
        else:
            svc_prices = {"bot": 20000, "crm": 45000, "ai": 60000, "pay": 10000}
            svc_labels = {"bot": "Бот", "crm": "CRM", "ai": "AI", "pay": "Оплата"}
            base = svc_prices.get(est_type, 0)
            if est_type == "bot":
                if has_crm:
                    extra_modules.append("CRM-интеграция")
                    extra_price += 20000
                if has_pay:
                    extra_modules.append("Онлайн-оплата")
                    extra_price += 15000
                if has_ai:
                    extra_modules.append("AI-модуль")
                    extra_price += 25000
            elif est_type == "crm":
                if has_pay:
                    extra_modules.append("Онлайн-оплата")
                    extra_price += 15000
                if has_ai:
                    extra_modules.append("AI-автоматизация")
                    extra_price += 25000
            elif est_type == "ai":
                if has_crm:
                    extra_modules.append("CRM-интеграция")
                    extra_price += 20000
                if has_pay:
                    extra_modules.append("Онлайн-оплата")
                    extra_price += 15000
            elif est_type == "pay":
                if has_crm:
                    extra_modules.append("CRM")
                    extra_price += 20000
            total = base + extra_price

        pkg_key, pkg_name, base_price = package if package else ("", "", 0)

        # Build result text
        type_labels = {
            "landing": "Лендинг", "site": "Сайт", "bot": "ТГ-бот",
            "crm": "CRM", "ai": "AI-ассистент", "pay": "Оплата",
        }
        screen_labels = {"none": "0", "few": "1-3", "mid": "4-6", "many": "7-10"}
        int_labels = {
            "no": "Нет", "crm": "CRM", "pay": "Оплата", "ai": "AI",
            "all": "Всё", "form": "Форма заявки",
        }

        result_lines = [
            "Расчёт проекта:",
            "",
            f"Тип: {type_labels.get(est_type, est_type)}",
        ]
        if est_type in ("landing", "site"):
            result_lines.append(f"Экраны: {screen_labels.get(screens, screens)}")
        result_lines.append(f"Дополнительно: {int_labels.get(integrations, integrations)}")
        if package:
            result_lines.extend([
                "",
                f"Пакет: {pkg_name}",
            ])
            if extra_modules:
                result_lines.append(f"Доп. модули: {', '.join(extra_modules)}")
            result_lines.extend([
                "",
                f"Стоимость: {total:,} ₽".replace(",", " "),
                "",
                "Точную стоимость скажем после разговора.",
            ])
        else:
            if extra_modules:
                result_lines.append(f"Доп. модули: {', '.join(extra_modules)}")
            result_lines.extend([
                "",
                f"Стоимость: {total:,} ₽".replace(",", " "),
                "",
                "Точную стоимость скажем после разговора.",
            ])
        result_text = "\n".join(result_lines)

        # Save calculator data for pre-filling the lead
        calc_data = {
            "est_type": est_type,
            "est_screens": screens,
            "est_integrations": integrations,
            "package": pkg_name or "Индивидуально",
            "price": str(total),
        }

        state_set(chat_id, {"step": "est_result", "data": calc_data, "username": st.get("username", "")})
        result_kb = [
            [{"text": "Оставить заявку", "callback_data": "est:apply"}],
        ]
        if PAYMENT_LINK:
            order_id = create_order_id({"name": f"{chat_id}"})
            pay_url = payment_url(order_id, total, "NOIR OS")
            _redis("SET", f"noir:order:{order_id}",
                   json.dumps({"client": str(chat_id), "price": str(total), "package": pkg_name or "Индивидуально",
                                "status": "pending", "order_id": order_id}),
                   "EX", "604800")
            result_kb = [
                [{"text": "Оплатить онлайн", "url": pay_url}],
                [{"text": "Оставить заявку", "callback_data": "est:apply"}],
            ]
        result_kb.append([{"text": "Меню", "callback_data": "menu"}])
        send(chat_id, result_text, reply_markup=kb_inline(result_kb))
        return

    # ── Calculator: apply with pre-filled data ──
    if data == "est:apply":
        d = st.get("data", {})
        d["goal"] = d.get("est_type", "all")
        st["step"] = "name"
        st["data"] = d
        state_set(chat_id, st)
        calc_price = d.get("price", "")
        pay_hint = ""
        if PAYMENT_LINK and calc_price:
            order_id = create_order_id({"name": f"{chat_id}"})
            pay_url = payment_url(order_id, calc_price, "NOIR OS")
            _redis("SET", f"noir:order:{order_id}",
                   json.dumps({"client": str(chat_id), "price": calc_price, "package": d.get("package", "Индивидуально"),
                                "status": "pending", "order_id": order_id}),
                   "EX", "604800")
            pay_hint = f"\nОплатить можно здесь: {pay_url}"
        send(chat_id, T["screen_name"] + pay_hint, reply_markup=kb_cancel())
        return

    # ── Dashboard ──
    if data == "dashboard:link":
        import secrets
        token = secrets.token_urlsafe(16)
        username = st.get("username", "")
        _redis("SET", f"noir:dash:{token}",
               json.dumps({"chat_id": chat_id, "username": username}), "EX", 2592000)
        url = f"{SITE_URL}/dashboard?token={token}"
        send(chat_id, T["dashboard_link"].format(url=url), reply_markup=kb_main())
        return

    # ── Payment ──
    if data == "pay:start":
        username = st.get("username", "")
        order_info = ""
        if username and sheets_find_client:
            client = sheets_find_client(username)
            if client and sheets_get_projects:
                projects = sheets_get_projects(client["name"])
                if projects:
                    o = projects[0]
                    order_info = f"\n\nВаш заказ: {o.get('name', o.get('package', '—'))}\nПакет: {o.get('package', '—')}\nСумма: {o.get('price', '—')} ₽\nОплачено: {o.get('paid', '0')} ₽\nОстаток: {o.get('remaining', '—')} ₽"
        msg = "Оплата через Т-Банк или QR-код.\nСсылка: " + (PAYMENT_LINK or "https://t.me/noir_lab42") + order_info
        send(chat_id, msg, reply_markup=kb_pay_start())
        return

    if data == "pay:qr":
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={urllib.parse.quote(PAYMENT_LINK or '')}"
        caption = "Оплата через Т-Банк или QR-код.\nСсылка: " + (PAYMENT_LINK or "https://t.me/noir_lab42") + order_info
        if PAYMENT_LINK:
            tg("sendPhoto", {
                "chat_id": chat_id,
                "photo": qr_url,
                "caption": caption,
                "reply_markup": json.dumps(kb_pay_back()),
            })
        else:
            send(chat_id, caption, reply_markup=kb_pay_back())
        return

    if data == "pay:confirm":
        _redis("SET", f"noir:pay:{st.get('order_id', chat_id)}",
               json.dumps({"status": "pending", "telegram_id": chat_id, "username": st.get("username", "")}),
               "EX", "604800")
        notify_owner(f"Пользователь @{st.get('username', 'без_ник')} оплатил. Telegram: {chat_id}")
        send(chat_id, "Спасибо! Подтверждение оплаты отправлено администратору.", reply_markup=kb_menu_main())
        return

    if data == "pay:back":
        send(chat_id, T["payment_q"], reply_markup=kb_pay_start())
        return

    # ── Qualification flow ──
    if data == "flow:start":
        state_set(chat_id, {"step": "goal", "data": {}, "username": st.get("username", "")})
        send(chat_id, T["screen_goal"], reply_markup=kb_goal())
        return

    if data.startswith("goal:"):
        goal = data[5:]
        st.setdefault("data", {})["goal"] = goal
        st["step"] = "site_ask"
        state_set(chat_id, st)
        send(chat_id, T["screen_site"], reply_markup=kb_site())
        return

    if data.startswith("site:"):
        site = data[5:]
        if st:
            st["data"]["site"] = site
            st["step"] = "niche"
            state_set(chat_id, st)
        send(chat_id, T["screen_niche"], reply_markup=kb_cancel())
        return

    if data == "budget:ok":
        level = (st.get("data") or {}).get("level", "business")
        st["step"] = "name"
        state_set(chat_id, st)
        send(chat_id, T["screen_name"], reply_markup=kb_cancel())
        return

    if data == "budget:show":
        send(chat_id, T["budget_all_levels"], reply_markup=kb_budget_levels())
        return

    if data.startswith("budget:") and data[7:] in ("start", "business", "premium"):
        level = data[7:]
        st.setdefault("data", {})["level"] = level
        text = T["budget_manual"].format(
            label=LABELS[level], price=PRICES[level], desc=pkg_desc(level)
        )
        send(chat_id, text, reply_markup=kb_budget_manual(level))
        return

    if data.startswith("budget:confirm:"):
        level = data[15:]
        st["data"]["level"] = level
        st["step"] = "name"
        state_set(chat_id, st)
        send(chat_id, T["screen_name"], reply_markup=kb_cancel())
        return

    if data == "budget:call":
        level = (st.get("data") or {}).get("level", "")
        st["data"]["level"] = level
        st["data"]["need_call"] = True
        st["step"] = "name"
        state_set(chat_id, st)
        send(chat_id, T["screen_name"], reply_markup=kb_cancel())
        return

    # ── Solution ──
    if data.startswith("sol:"):
        sol_type = data[4:]
        level = score_solution(sol_type)
        pain_map = {"leads": "Нет заявок", "routine": "Тону в рутине",
                    "nosys": "Нет системы", "all": "Всё сразу"}
        st.setdefault("data", {})["pain"] = pain_map.get(sol_type, sol_type)
        st["data"]["level"] = level
        st["data"]["sol_type"] = sol_type
        st["step"] = "goal"
        state_set(chat_id, st)
        send(chat_id, T["screen_goal"], reply_markup=kb_goal())
        return

    # ── Services ──
    if data.startswith("svc:"):
        svc_key = data[4:]
        svc = SERVICES.get(svc_key)
        if not svc:
            return
        st.setdefault("data", {})["service"] = svc["name"]
        st["data"]["service_price"] = svc["num"]
        st["step"] = "svc_name"
        state_set(chat_id, st)
        send(chat_id, T["svc_prefix"].format(name=svc["name"], price=svc["price"]), reply_markup=kb_cancel())
        return

    # ── Filter ──
    if data == "filter:checklist":
        state_del(chat_id)
        send(chat_id, T["checklist"], reply_markup=kb_main())
        return
    if data == "filter:force":
        state_set(chat_id, {"step": "pain", "data": {}, "username": st.get("username", "")})
        send(chat_id, T["screen_pain"], reply_markup=kb_cancel())
        return




def _finish_qualification(chat_id, data):
    log.info("FINISH_QUALIFICATION chat=%s data=%s", chat_id, json.dumps(data, ensure_ascii=False)[:500])
    if not data.get("name"):
        send(chat_id, "Не хватает имени. Начнём сначала?", reply_markup=kb_main())
        state_del(chat_id)
        return

    name    = str(data.get("name", ""))
    phone   = str(data.get("phone", ""))
    telegram = str(data.get("telegram", ""))
    email   = str(data.get("email", ""))
    niche   = str(data.get("niche", ""))
    city    = str(data.get("city", ""))
    goal    = GOAL_RU.get(data.get("goal", ""), data.get("goal", ""))
    site    = SITE_RU.get(data.get("site", ""), data.get("site", ""))
    level   = data.get("level") or score(data) or "business"
    service = data.get("service", "")
    svc_price = data.get("service_price", "")

    if service:
        task_for_contract = service
        price_for_contract = svc_price
    else:
        task_for_contract = f"Пакет «{LABELS.get(level, 'Бизнес')}»"
        price_for_contract = PRICES_NUM.get(level, "29000")

    dt = now_kem()
    date_str = dt.strftime("%d.%m.%Y")
    time_str = dt.strftime("%H:%M")
    num = dt.strftime(f"%Y-%m-{random.randint(100,999)}")

    support_map = {"start": "1 месяц", "business": "2 месяца", "premium": "3 месяца"}
    support_months = support_map.get(level, "1 месяц")

    url = contract_url({
        "name": data.get("name", ""),
        "phone": data.get("phone", ""),
        "task": task_for_contract,
        "price": price_for_contract,
        "date": date_str,
        "num": num,
        "tg": data.get("telegram", ""),
        "email": data.get("email", ""),
        "city": data.get("city", ""),
        "support": support_months,
    })

    lead = (
        f"{T['done_lead'].format(level=LABELS.get(level, 'Бизнес'))}\n\n"
        f"ФИО: {name}\n"
        f"Телефон: {phone}\n"
        f"Telegram: {telegram or '—'}\n"
        f"Email: {email or '—'}\n"
        f"Ниша: {niche}\n"
        f"Город: {city}\n"
        f"Цель: {goal}\n"
        f"Сайт: {site}\n"
        f"Услуга: {task_for_contract}\n\n"
        f"Цена: {PRICES.get(level, '29 000')} ₽\n"
        f"{date_str} · {time_str} МСК"
    )
    lead_kb = [[{"text": "Договор клиента", "url": url}]]
    lead_kb += kb_lead(data)

    state_del(chat_id)
    tg("sendMessage", {
        "chat_id": chat_id,
        "text": T["done_confirm"],
        "reply_markup": json.dumps(kb_done()),
    })

    send_lead(lead, lead_kb)
    log.info("lead_created level=%s chat=%s username=%s email=%s", level, chat_id, data.get("telegram",""), data.get("email",""))

    # Create order for payment
    order_id = create_order_id(data)
    price_num = int(PRICES_NUM.get(level, "29000"))
    advance = price_num // 2

    _redis("SET", f"noir:order:{order_id}",
           json.dumps({
               "client": name,
               "level": level,
               "package": LABELS.get(level, "Бизнес"),
               "price": str(price_num),
               "advance": str(advance),
               "remaining": str(price_num - advance),
               "task": task_for_contract,
               "status": "pending",
               "order_id": order_id,
           }), "EX", "604800")

    pay_url = payment_url(order_id, advance, name)

    pay_kb = kb_inline([
        [{"text": "Оплатить", "url": pay_url}],
        [{"text": "Договор", "url": url}],
        [{"text": "Главное меню", "callback_data": "menu"}],
    ])
    pay_text = (
        f"Заявка принята.\n\n"
        f"Пакет: {LABELS.get(level, 'Бизнес')}\n"
        f"Счёт: {price_num:,} ₽\n"
        f"Аванс (50%): {advance:,} ₽\n\n"
        f"Оплатить → {pay_url}\n\n"
        f"После оплаты — проект в личном кабинете."
    ).replace(",", " ")
    send(chat_id, pay_text, reply_markup=pay_kb)

    if sheets_lead:
        budget_str = PRICES.get(level, "")
        log.info("sheets_lead data: name=%s phone=%s tg=%s email=%s city=%s niche=%s budget=%s",
                 data.get("name",""), data.get("phone",""), data.get("telegram",""),
                 data.get("email",""), data.get("city",""), data.get("niche",""), budget_str)
        sheets_lead(
            name=data.get("name", ""), phone=data.get("phone", ""),
            telegram=data.get("telegram", ""), email=data.get("email", ""),
            source="noir_bot",
            city=data.get("city", ""), niche=data.get("niche", ""),
            budget=budget_str,
        )
        task = service if service else f"Пакет «{LABELS.get(level, 'Бизнес')}»"
        if sheets_project:
            deadline_days = {"Старт": 21, "Бизнес": 30, "Премиум": 30}
            deadline_dt = now_kem() + timedelta(days=deadline_days.get(level, 30))
            sheets_project(
                client=data.get("name", ""),
                name=task,
                package=LABELS.get(level, "Бизнес"),
                stage="Бриф",
                price=PRICES.get(level, ""),
                deadline=deadline_dt.strftime("%d.%m.%Y"),
            )
        if sheets_event:
            sheets_event(
                project=task,
                client=data.get("name", ""),
                type="Заявка",
                description=f"Новая заявка — {LABELS.get(level, 'Бизнес')}",
                importance="Высокая",
            )
        if sheets_payment:
            sheets_payment(
                project=task,
                client=data.get("name", ""),
                amount=str(int(PRICES.get(level, "0").replace(" ", "").replace("₽", "")) // 2),
                type="Аванс",
                status="Ожидает",
                method="Перевод",
                purpose=f"Предоплата {LABELS.get(level, 'Бизнес')}",
            )


# ── Form from website ────────────────────────────────────
def handle_form(payload):
    name    = payload.get("name", "---")
    phone   = payload.get("phone") or payload.get("contact") or "---"
    message = payload.get("message") or payload.get("task") or "---"
    source  = payload.get("source", "")

    dt = now_kem()
    date_str = dt.strftime("%d.%m.%Y")

    lead = (
        f"{T['site_form_lead']}\n\n"
        f"ФИО: {name}\n"
        f"Телефон: {phone}\n"
        f"Сообщение: {message}"
    )
    if source:
        lead += f"\nИсточник: {source}"
    lead += f"\n{date_str}"
    send_lead(lead)
    log.info("form_lead source=%s", source)

    if sheets_lead:
        sheets_lead(
            name=name, phone=phone, source=source or "website",
        )

    result = {"ok": True}
    if PAYMENT_LINK:
        order_id = create_order_id({"name": name})
        _redis("SET", f"noir:order:{order_id}",
               json.dumps({
                   "client": name,
                   "price": "",
                   "status": "pending",
                   "order_id": order_id,
               }),
               "EX", "604800")
        result["payment_url"] = payment_url(order_id, name=name)
        result["order_id"] = order_id
    return result


# ── Vercel entry point ───────────────────────────────────
class handler(BaseHTTPRequestHandler):
    def _send(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)

    def do_GET(self):
        path = self.path.split("?")[0]
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        if path == "/api/health" or path == "/health":
            self._send(200, "ok")
            return
        if path == "/api/payment_status" or path == "/payment_status":
            order = params.get("order", [""])[0]
            raw = _redis("GET", f"noir:order:{order}") if order else None
            if raw:
                data = json.loads(raw)
                # Check if there's also a payment confirmation status
                pay_raw = _redis("GET", f"noir:pay:{order}") if order else None
                if pay_raw:
                    pay_data = json.loads(pay_raw)
                    data.update(pay_data)
                status = data
            else:
                status = {"status": "unknown"}
            self._send(200, json.dumps(status))
            return
        if path == "/api/dashboard" or path == "/dashboard":
            token = params.get("token", [""])[0]
            raw = _redis("GET", f"noir:dash:{token}") if token else None
            if raw:
                data = json.loads(raw)
                # Always read fresh from Sheets
                client_name = data.get("client_name", "")
                username_d = data.get("username", "")
                if not client_name and username_d and sheets_find_client:
                    client = sheets_find_client(username_d)
                    if client:
                        client_name = client["name"]
                log.info("DASHBOARD token=%s client=%s username=%s", token[:8], client_name, username_d)
                if client_name and sheets_get_projects:
                    projects = sheets_get_projects(client_name)
                    log.info("DASHBOARD projects_found=%d", len(projects))
                    if projects:
                        proj = projects[0]
                        log.info("DASHBOARD proj=%s stage=%s progress=%s", proj.get("name"), proj.get("stage"), proj.get("progress"))
                        data.update({
                            "client_name": client_name,
                            "project_name": proj.get("name", data.get("project_name", "Проект")),
                            "package": proj.get("package", data.get("package", "")),
                            "stage": proj.get("stage", data.get("stage", "brief")),
                            "progress": int(proj.get("progress", data.get("progress", 0))),
                            "price": proj.get("price", data.get("price", "")),
                            "paid": proj.get("paid", data.get("paid", "0")),
                            "remaining": proj.get("remaining", data.get("remaining", "")),
                        })
                    else:
                        log.warning("DASHBOARD no projects for client=%s", client_name)
                self._send(200, json.dumps({"ok": True, **data}))
            else:
                self._send(200, json.dumps({"ok": False}))
            return
        self._send(200, json.dumps({"status": "ok", "bot": "NOIR"}))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 1048576:
            self._send(413, json.dumps({"error": "too large"}))
            return
        
        raw = self.rfile.read(length) if length else b"{}"
        
        try:
            raw_str = raw.decode('utf-8') if isinstance(raw, bytes) else str(raw)
            body = json.loads(raw_str)
        except Exception as e:
            # Vercel strips JSON double-quotes from POST body — restore them
            log.error("JSON parse fail, raw=%s", repr(raw_str[:200]))
            try:
                body = _restore_json(raw_str)
            except Exception as e2:
                log.error("restore_json fail: %s", e2)
                self._send(500, json.dumps({"error": str(e)[:200]}))
                return

            if body.get("_form"):
                result = handle_form(body["_form"])
                self._send(200, json.dumps(result))
                return

            if body.get("test_tg"):
                me = tg("getMe")
                self._send(200, json.dumps({"tg_ok": me.get("ok", False), "tg_result": me}))
                return

            # Google Sheets webhook
            if body.get("sheet"):
                sheet = body.get("sheet", "")
                row = body.get("row", 0)
                col = body.get("col", 0)
                value = body.get("value", "")
                log.info("sheets_webhook sheet=%s row=%s col=%s val=%s", sheet, row, col, value)
                _handle_sheets_webhook(sheet, row, col, value)
                self._send(200, json.dumps({"ok": True}))
                return

            if body.get("action") == "payment_confirm":
                order_id = body.get("order_id", "")
                if order_id:
                    client_data = {
                        "name": body.get("name", ""),
                        "phone": body.get("phone", ""),
                        "telegram": body.get("telegram", ""),
                        "email": body.get("email", ""),
                        "price": body.get("price", ""),
                        "status": "pending",
                        "order_id": order_id,
                    }
                    _redis("SET", f"noir:pay:{order_id}",
                           json.dumps(client_data),
                           "EX", "604800")
                    # Store in order record too
                    existing = _redis("GET", f"noir:order:{order_id}")
                    if existing:
                        order = json.loads(existing)
                        order.update({"paid": client_data["price"], "status": "pending"})
                        _redis("SET", f"noir:order:{order_id}",
                               json.dumps(order), "EX", "604800")
                    if OWNER_ID:
                        msg = (
                            "✅ Клиент подтвердил оплату\n\n"
                            f"Заказ: {order_id}\n"
                            f"ФИО: {client_data['name']}\n"
                            f"Телефон: {client_data['phone']}\n"
                            f"Telegram: {client_data['telegram']}\n"
                            f"Email: {client_data['email']}\n"
                            f"Сумма: {client_data['price']}"
                        )
                        tg("sendMessage", {"chat_id": OWNER_ID, "text": msg})
                        # Also send to group chat
                        tg("sendMessage", {"chat_id": -1004435537674, "text": msg})
                    self._send(200, json.dumps({"ok": True}))
                else:
                    self._send(400, json.dumps({"error": "missing order_id"}))
                return

            # T-Bank payment callback
            if body.get("TerminalKey") or body.get("PaymentId"):
                order_id = body.get("OrderId", "")
                status = body.get("Status", "")
                if order_id:
                    payment_status = "paid" if status == "CONFIRMED" else "failed"
                    _redis("SET", f"noir:pay:{order_id}",
                           json.dumps({"status": payment_status, "order_id": order_id}),
                           "EX", "604800")
                    if payment_status == "paid" and OWNER_ID:
                        tg("sendMessage", {"chat_id": OWNER_ID,
                            "text": f"Оплата подтверждена Т-Банк\nЗаказ: {order_id}"})
                self._send(200, json.dumps({"ok": True}))
                return

            if body.get("action") == "dashboard_login":
                login = body.get("login", "").strip()
                if not login:
                    self._send(200, json.dumps({"ok": False}))
                    return
                import secrets
                token = secrets.token_urlsafe(16)

                # Try to find client in Google Sheets
                client_data = None
                projects = []
                if sheets_find_client:
                    client_data = sheets_find_client(login)
                    if client_data and sheets_get_projects:
                        projects = sheets_get_projects(client_data["name"])

                if client_data:
                    proj = projects[0] if projects else {}
                    log.info("DASHBOARD_LOGIN client='%s' projects=%d proj_name='%s' progress=%s",
                             client_data["name"], len(projects), proj.get("name",""), proj.get("progress",""))
                    project_name = proj.get("name", "Проект")
                    package = proj.get("package", "")
                    stage = proj.get("stage", "brief")
                    progress = proj.get("progress", 0)
                    price = proj.get("price", "")
                    paid = proj.get("paid", "0")
                    remaining = proj.get("remaining", "")

                    dashboard_data = {
                        "client_name": client_data["name"],
                        "project_name": project_name,
                        "package": package,
                        "stage": stage,
                        "progress": progress,
                        "price": f"{price} ₽" if price else "—",
                        "paid": f"{paid} ₽" if paid and paid != "0" else "0 ₽",
                        "remaining": f"{remaining} ₽" if remaining else "—",
                        "docs": [
                            {"name": "Договор", "url": "/dogovor.html"},
                        ],
                        "payments": [],
                        "updates": [],
                    }
                else:
                    # Fallback — no Sheets data
                    dashboard_data = {
                        "client_name": login,
                        "project_name": "Проект",
                        "package": "",
                        "stage": "brief",
                        "progress": 0,
                        "price": "—",
                        "paid": "0 ₽",
                        "remaining": "—",
                        "docs": [],
                        "payments": [],
                        "updates": [],
                    }

                _redis("SET", f"noir:dash:{token}",
                       json.dumps(dashboard_data), "EX", "2592000")
                self._send(200, json.dumps({"ok": True, "token": token, **dashboard_data}))
                return

            msg = body.get("message") or body.get("callback_query")
            print(f"INCOMING: {json.dumps(body)[:300]}")
            if not msg:
                self._send(200, "ok")
                return

            if "callback_query" in body:
                cb = body["callback_query"]
                chat_id = cb["message"]["chat"]["id"]
                if cb["message"]["chat"].get("type", "private") != "private":
                    self._send(200, "ok")
                    return
                handle_callback(chat_id, cb["data"])
                tg("answerCallbackQuery", {"callback_query_id": cb["id"]})
            else:
                chat_id = msg["chat"]["id"]
                if msg["chat"].get("type", "private") != "private":
                    self._send(200, "ok")
                    return
                text = msg.get("text", "")
                username = msg.get("from", {}).get("username", "")

                if text == "/start":
                    handle_start(chat_id, username)
                elif text == "/menu":
                    handle_menu(chat_id)
                elif text == "/admin":
                    handle_admin(chat_id)
                elif text == "/diag":
                    _handle_diag(chat_id)
                else:
                    st = state_get(chat_id)
                    if not st:
                        send(chat_id, T["state_lost"])
                    else:
                        _handle_text(chat_id, text, st, username)
                self._send(200, "ok")
        except Exception as e:
            log.error("handler error: %s\n%s", e, traceback.format_exc())
            self._send(500, json.dumps({"error": str(e)[:500]}))


def _handle_sheets_webhook(sheet, row, col, value):
    """Process Google Sheets cell edit webhook."""
    try:
        if sheet == "Clients" and col == 9:
            status = str(value).strip()
            result = _sheets_api("GET", f"/values/Clients!A{row}:J{row}")
            if result and "values" in result and result["values"]:
                r = result["values"][0]
                # Clients: A:ФИО B:Телефон C:Telegram D:Email
                name = r[0] if len(r) > 0 else ""
                phone = r[1] if len(r) > 1 else ""
                telegram = r[2] if len(r) > 2 else ""
                if OWNER_ID:
                    tg("sendMessage", {"chat_id": OWNER_ID,
                        "text": f"CRM · Статус клиента обновлён\n{name}\nСтатус: {status}"})

        elif sheet == "Projects" and col == 5:
            result = _sheets_api("GET", f"/values/Projects!A{row}:K{row}")
            if result and "values" in result and result["values"]:
                r = result["values"][0]
                client = r[1] if len(r) > 1 else ""
                proj_name = r[2] if len(r) > 2 else ""
                stage = r[5] if len(r) > 5 else ""
                if OWNER_ID:
                    tg("sendMessage", {"chat_id": OWNER_ID,
                        "text": f"CRM · Этап проекта обновлён\n{proj_name}\nКлиент: {client}\nЭтап: {stage}"})

        elif sheet == "Payments" and col == 4:
            result = _sheets_api("GET", f"/values/Payments!A{row}:I{row}")
            if result and "values" in result and result["values"]:
                r = result["values"][0]
                amount = r[3] if len(r) > 3 else ""
                status = r[5] if len(r) > 5 else ""
                if OWNER_ID:
                    tg("sendMessage", {"chat_id": OWNER_ID,
                        "text": f"CRM · Оплата обновлена\nСумма: {amount}\nСтатус: {status}"})
    except Exception as e:
        log.warning("sheets_webhook error: %s", e)


def _handle_diag(chat_id):
    if chat_id != OWNER_ID:
        send(chat_id, "Нет доступа")
        return
    token_ok = bool(BOT_TOKEN and len(BOT_TOKEN) > 40)
    me = tg("getMe") if token_ok else {"ok": False}
    bot_name = me.get("result", {}).get("username", "?") if me.get("ok") else "FAIL"
    test_lead = tg("sendMessage", {
        "chat_id": LEADS_CHAT_ID,
        "text": f"DIAG · test ping\nchat_id={LEADS_CHAT_ID}"
    })
    lead_ok = test_lead.get("ok", False)
    lead_err = test_lead.get("description", "") if not lead_ok else ""
    redis_ok = _redis("PING") is not None
    diag = (
        f"BOT TOKEN: {'ok' if token_ok else 'MISSING/BAD'}\n"
        f"BOT: @{bot_name}\n"
        f"OWNER_ID: {OWNER_ID}\n"
        f"LEADS_CHAT_ID: {LEADS_CHAT_ID}\n"
        f"GROUP DELIVERY: {'ok' if lead_ok else 'FAIL — ' + lead_err}\n"
        f"SITE_URL: {SITE_URL}\n"
        f"REDIS: {'ok' if redis_ok else 'not configured'}"
    )
    send(chat_id, diag)
