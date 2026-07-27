import os, json, html, urllib.request, urllib.parse
from datetime import datetime
from http.server import BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
SITE_URL = os.environ.get("SITE_URL", "https://noir42.ru").rstrip("/")

_raw = os.environ.get("LEADS_CHAT_ID", "").strip()
LEADS_CHAT_ID = int(_raw) if _raw and _raw.lstrip("-").isdigit() else OWNER_ID

# ponytail: in-memory FSM — resets on cold start, good enough for MVP
_state = {}


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
    """[[{"text":..., "callback_data":...|url:...}]]"""
    return {"inline_keyboard": buttons}


def kb_reply(buttons, placeholder="", one_time=False):
    return {
        "keyboard": [[{"text": b}] for b in buttons],
        "resize_keyboard": True,
        "one_time_keyboard": one_time,
        "input_field_placeholder": placeholder,
    }


def contract_url(name, contact, task, price=""):
    params = {"name": name, "phone": contact, "task": task}
    if price:
        params["price"] = price
    return f"{SITE_URL}/dogovor.html?{urllib.parse.urlencode(params)}"


def send_lead(text, buttons=None):
    markup = kb_inline(buttons) if buttons else None
    try:
        tg("sendMessage", {"chat_id": LEADS_CHAT_ID, "text": text, "parse_mode": "HTML",
                           **({"reply_markup": json.dumps(markup)} if markup else {})})
    except Exception:
        pass


# ── Тексты ──────────────────────────────────────────────
WELCOME = (
    "Привет! Я бот цифровой студии <b>NOIR</b>.\n\n"
    "Делаем сайты, Telegram-ботов, автоматизацию и AI для бизнеса.\n\n"
    "Выберите пункт ниже"
)

PACKAGES = (
    "<b>Пакеты под ключ</b> (первым 3 клиентам — цена ниже рынка):\n\n"
    "<b>Старт — 29 000 rub</b>\nЛендинг + онлайн-оплата + метрика + заявки в Telegram.\n\n"
    "<b>Бизнес — 59 000 rub</b>\nВсё из Старта + Telegram-бот + CRM.\n\n"
    "<b>Премиум — 112 000 rub</b>\nВсё из Бизнеса + AI-ассистент + полная автоматизация.\n\n"
    "Нажмите пакет — начнём заявку"
)

FAQ = (
    "<b>Частые вопросы</b>\n\n"
    "<b>Сколько стоит?</b> Пакеты 29 / 59 / 112 тыс. rub.\n"
    "<b>Сроки?</b> Старт 2-3 недели, Бизнес 3-4, Премиум от месяца.\n"
    "<b>Официально?</b> Да, договор + чек (самозанятый, НПД).\n"
    "<b>Оплата?</b> 50/50, не всё сразу."
)

CONTACTS = (
    "<b>Связь с NOIR</b>\n\n"
    "Telegram: @noir_lab42\n"
    "Телефон: +7 951 592-26-18\n"
    "Кемерово"
)

MAIN_KB = kb_reply(
    ["Рассчитать проект", "Пакеты и цены", "Портфолио", "Вопрос", "Контакты"],
    "Выберите пункт меню"
)
CANCEL_KB = kb_reply(["Отмена"], "Ваше имя")


# ── Логика ──────────────────────────────────────────────
def handle_start(chat_id):
    _state.pop(chat_id, None)
    send(chat_id, WELCOME, reply_markup=MAIN_KB)


def handle_menu(chat_id):
    _state.pop(chat_id, None)
    send(chat_id, "Меню:", reply_markup=MAIN_KB)


def handle_text(chat_id, text):
    st = _state.get(chat_id)

    # Кнопки главного меню (вне FSM)
    if not st:
        if text == "Рассчитать проект":
            _state[chat_id] = {"step": "name", "data": {"package": "", "price": ""}}
            send(chat_id, "Как к вам обращаться?", reply_markup=CANCEL_KB)
        elif text == "Пакеты и цены":
            kb = kb_inline([
                [{"text": "Хочу Старт", "callback_data": "pkg:Старт|29 000 rub"},
                 {"text": "Хочу Бизнес", "callback_data": "pkg:Бизнес|59 000 rub"}],
                [{"text": "Хочу Премиум", "callback_data": "pkg:Премиум|112 000 rub"}],
            ])
            send(chat_id, PACKAGES, reply_markup=kb)
        elif text == "Портфолио":
            kb = kb_inline([
                [{"text": "Сайт NOIR", "url": f"{SITE_URL}/index.html"}],
                [{"text": "Все кейсы", "url": f"{SITE_URL}/cases.html"}],
                [{"text": "Демо: ТопДент", "url": f"{SITE_URL}/topdent.html"}],
            ])
            send(chat_id, "Наши работы:", reply_markup=kb)
        elif text == "Вопрос":
            kb = kb_inline([[{"text": "Задать вопрос", "callback_data": "ask"}]])
            send(chat_id, FAQ, reply_markup=kb)
        elif text == "Контакты":
            kb = kb_inline([
                [{"text": "Написать в TG", "url": "https://t.me/noir_lab42"}],
                [{"text": "Позвонить", "url": "tel:+79515922618"}],
            ])
            send(chat_id, CONTACTS, reply_markup=kb)
        else:
            send(chat_id, "Отправьте /start чтобы начать.")
        return

    # FSM
    step = st["step"]
    data = st["data"]

    if step == "name":
        data["name"] = text
        st["step"] = "contact"
        send(chat_id, "Телефон или Telegram для связи?", reply_markup=CANCEL_KB)
    elif step == "contact":
        data["contact"] = text
        st["step"] = "task"
        send(chat_id, "Опишите задачу (или Пропустить):",
             reply_markup=kb_reply(["Пропустить", "Отмена"], "Например: лендинг для салона"))
    elif step == "task":
        task = "" if text == "Пропустить" else text
        _state.pop(chat_id, None)
        _send_result(chat_id, data, task)


def handle_callback(chat_id, data):
    if data.startswith("pkg:"):
        pkg, price = data[4:].split("|", 1)
        _state[chat_id] = {"step": "name", "data": {"package": pkg, "price": price}}
        send(chat_id, f"Выбран пакет «{pkg}». Как к вам обращаться?", reply_markup=CANCEL_KB)
    elif data == "ask":
        _state[chat_id] = {"step": "name", "data": {"package": "Вопрос", "price": ""}}
        send(chat_id, "Как к вам обращаться?", reply_markup=CANCEL_KB)


def _send_result(chat_id, data, task):
    name = html.escape(data.get("name", ""))
    contact = html.escape(data.get("contact", ""))
    task_safe = html.escape(task) if task else "---"
    pkg = html.escape(data.get("package", "") or "---")
    price = data.get("price", "")
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    url = contract_url(data.get("name", ""), data.get("contact", ""), task or "Заявка с бота", price)

    lead = (
        f"<b>Новая заявка</b>\n\n"
        f"Имя: {name}\n"
        f"Контакт: {contact}\n"
        f"Задача: {task_safe}\n"
        f"Пакет: {pkg}\n"
        f"{now}"
    )
    buttons = [[{"text": "Договор клиента", "url": url}]]
    if data.get("contact", "").startswith("@"):
        buttons.append([{"text": "Написать в TG", "url": f"https://t.me/{data['contact'].lstrip('@')}"}])
    send_lead(lead, buttons)

    send(chat_id,
         f"Спасибо, {name}! Заявка у нас.\n\n"
         f"Ответим в течение 15 минут.\n"
         f"Договор (данные подставлены): {url}\n\n"
         f"Меню ниже",
         reply_markup=MAIN_KB)


def handle_form(payload):
    name = html.escape(payload.get("name", "---"))
    phone = html.escape(payload.get("phone", "---"))
    message = html.escape(payload.get("message", "---"))
    source = payload.get("source", "")
    url = contract_url(payload.get("name", ""), payload.get("phone", ""), payload.get("message", ""))

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
        self._send(200, json.dumps({"status": "ok", "bot": "NOIR"}))

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
