import json, os, urllib.request, urllib.parse
from http.server import BaseHTTPRequestHandler

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))
LEADS_CHAT_ID = os.environ.get("LEADS_CHAT_ID", "")
SITE_URL = os.environ.get("SITE_URL", "https://noir42.ru")

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


def notify_owner(text):
    if OWNER_ID:
        send(OWNER_ID, text)


def contract_url(params):
    qs = urllib.parse.urlencode(params)
    return f"{SITE_URL}/dogovor.html?{qs}"


def handle_start(chat_id, user):
    name = user.get("first_name", "")
    _state[chat_id] = {"step": "wait_name", "data": {"name": name}}
    kb = {"inline_keyboard": [[{"text": "Пропустить", "callback_data": "skip_name"}]]}
    send(chat_id, f"Привет{' ' + name if name else ''}! Я соберу заявку.\n\nКак к вам обращаться?", reply_markup=kb)


def handle_menu(chat_id):
    _state.pop(chat_id, None)
    kb = {"inline_keyboard": [
        [{"text": "Оставить заявку", "callback_data": "new_lead"}],
        [{"text": "На сайт", "url": SITE_URL}],
    ]}
    send(chat_id, "Главное меню:", reply_markup=kb)


def handle_text(chat_id, text):
    st = _state.get(chat_id)
    if not st:
        send(chat_id, "Отправьте /start чтобы начать.")
        return
    step = st["step"]
    data = st["data"]
    if step == "wait_name":
        data["name"] = text
        st["step"] = "wait_phone"
        send(chat_id, "Как с вами связаться?")
    elif step == "wait_phone":
        data["phone"] = text
        st["step"] = "wait_task"
        send(chat_id, "Опишите кратко задачу:")
    elif step == "wait_task":
        data["task"] = text
        _state.pop(chat_id, None)
        url = contract_url(data)
        kb = {"inline_keyboard": [
            [{"text": "Договор", "url": url}],
            [{"text": "На сайт", "url": SITE_URL}],
        ]}
        send(chat_id, "Готово! Договор:", reply_markup=kb)
        notify_owner(f"Заявка\nИмя: {data['name']}\nКонтакт: {data['phone']}\nЗадача: {data['task']}\nДоговор: {url}")


def handle_callback(chat_id, data):
    if data == "new_lead":
        handle_start(chat_id, {"first_name": ""})
    elif data == "skip_name":
        st = _state.get(chat_id)
        if st:
            st["step"] = "wait_phone"
            send(chat_id, "Как с вами связаться?")
    elif data == "menu":
        handle_menu(chat_id)


def handle_form(payload):
    name = payload.get("name", "—")
    phone = payload.get("phone", "—")
    message = payload.get("message", "—")
    url = contract_url({"name": name, "phone": phone, "task": message})
    if LEADS_CHAT_ID:
        send(LEADS_CHAT_ID, f"Заявка с сайта\nИмя: {name}\nТелефон: {phone}\nСообщение: {message}\nДоговор: {url}")
    return {"ok": True, "contract_url": url}


def process_update(body):
    msg = body.get("message") or body.get("callback_query")
    if not msg:
        return {"statusCode": 200, "body": "ok"}

    if body.get("_form"):
        result = handle_form(body["_form"])
        return {"statusCode": 200, "body": json.dumps(result)}

    if "callback_query" in body:
        cb = body["callback_query"]
        chat_id = cb["message"]["chat"]["id"]
        handle_callback(chat_id, cb["data"])
        tg("answerCallbackQuery", {"callback_query_id": cb["id"]})
    else:
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        if text == "/start":
            handle_start(chat_id, msg.get("from", {}))
        elif text == "/menu":
            handle_menu(chat_id)
        else:
            handle_text(chat_id, text)

    return {"statusCode": 200, "body": "ok"}


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
            result = process_update(body)
            self._send(result["statusCode"], result.get("body", "ok"))
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}))
