# NOIR TopDent Bot - Demo Version
import os, sys, json, urllib.request, urllib.parse, logging, traceback, base64, time
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

log = logging.getLogger("topdent_demo")
log.setLevel(logging.INFO)
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)

BOT_TOKEN = os.environ.get("TOPDENT_TOKEN", "")
KEM = timezone(timedelta(hours=7))
SPREADSHEET_ID = os.environ.get("TOPDENT_SHEET_ID", "15pUGJTy5HQDhXGhXxy5N3_S3Jm0U4TFRcj3pNKP75wE")
SA_JSON = os.environ.get("TOPDENT_GOOGLE_SA_JSON") or os.environ.get("GOOGLE_SA_JSON", "")

def tg(method, data=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    payload = json.dumps(data or {}).encode()
    req = urllib.request.Request(url, data=payload)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.error("tg.%s: %s", method, e)
    return {"ok": False}

def send(chat_id, text, reply_markup=None):
    msg = {"chat_id": chat_id, "text": text}
    if reply_markup:
        msg["reply_markup"] = json.dumps(reply_markup)
    return tg("sendMessage", msg)

def kb(rows):
    return {"inline_keyboard": rows}

def now_kem():
    return datetime.now(KEM)

def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

def _get_token():
    if not SA_JSON:
        return None
    try:
        sa = json.loads(SA_JSON)
    except Exception:
        return None
    now = time.time()
    header = {"alg": "RS256", "typ": "JWT"}
    payload = {"iss": sa["client_email"], "scope": "https://www.googleapis.com/auth/spreadsheets",
              "aud": "https://oauth2.googleapis.com/token", "iat": int(now), "exp": int(now) + 3600}
    signing_input = _b64url(json.dumps(header).encode()) + "." + _b64url(json.dumps(payload).encode())
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
    signature = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    jwt_token = signing_input + "." + _b64url(signature)
    body = urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": jwt_token}).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body, method="POST")
    req.add_header("Content-Type", "application/x-www-form-urlencoded")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get("access_token")
    except Exception as e:
        log.error("token: %s", e)
    return None

def sheets_append(row):
    token = _get_token()
    if not token:
        log.error("no token")
        return False
    encoded_sheet = urllib.parse.quote("Лист1")
    path = f"/values/{encoded_sheet}:append?valueInputOption=USER_ENTERED&insertDataOption=INSERT_ROWS"
    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}{path}"
    data = json.dumps({"values": [row]}).encode()
    req = urllib.request.Request(url, data=data, method="POST")
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            result = json.loads(resp.read())
            log.info("sheets_append OK: %s", result.get("updates", {}).get("updatedRange"))
            return True
    except Exception as e:
        log.error("sheets_append FAIL: %s", e)
    return False

def handle_message(chat_id, text):
    """Handle any message from user - write to sheet and respond."""
    now = now_kem().strftime("%d.%m.%Y %H:%M")
    
    # Write to TopDent sheet
    row = [now, str(chat_id), text]
    success = sheets_append(row)
    
    # Respond to user
    if text == "/start":
        send(chat_id, "ТопДент\n\nЦифровой помощник клиники\n\nНапишите что-нибудь и я запишу это в таблицу.", kb([
            [{"text": "Записаться", "callback_data": "demo:book"}],
            [{"text": "Прайс", "callback_data": "demo:price"}],
        ]))
    else:
        send(chat_id, f"Записано в таблицу:\n\n📝 {text}\n\nДата: {now}", kb([
            [{"text": "Ещё", "callback_data": "demo:more"}],
        ]))
    
    return {"ok": True, "written": success}

def handle_callback(chat_id, data):
    """Handle button presses."""
    now = now_kem().strftime("%d.%m.%Y %H:%M")
    
    if data == "demo:book":
        send(chat_id, "Запись на приём\n\nВведите ваше имя и телефон для записи.")
        sheets_append([now, str(chat_id), "Нажал: Записаться"])
    elif data == "demo:price":
        send(chat_id, "Прайс-лист\n\nТерапия: 3 250 – 9 500 ₽\nОртопедия: 9 500 – 20 000 ₽\nИмплантация: от 45 000 ₽\nХирургия: от 3 900 ₽\nГигиена: 4 400 ₽")
        sheets_append([now, str(chat_id), "Нажал: Прайс"])
    elif data == "demo:more":
        send(chat_id, "Напишите что-нибудь:")
        sheets_append([now, str(chat_id), "Нажал: Ещё"])

class handler(BaseHTTPRequestHandler):
    def _send(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 1048576:
            self._send(413, json.dumps({"error": "too large"}))
            return
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw)
            msg = body.get("message") or body.get("callback_query")
            if not msg:
                self._send(200, "ok")
                return
            if "callback_query" in body:
                cb = body["callback_query"]
                chat_id = cb["message"]["chat"]["id"]
                tg("answerCallbackQuery", {"callback_query_id": cb["id"]})
                handle_callback(chat_id, cb["data"])
            else:
                chat_id = msg["chat"]["id"]
                text = msg.get("text", "")
                handle_message(chat_id, text)
            self._send(200, "ok")
        except Exception as e:
            log.error("handler: %s", e)
            self._send(500, json.dumps({"error": str(e)[:200]}))
