# NOIR TopDent Bot Webhook v1.0
import os, sys, json, urllib.request, urllib.parse, logging, traceback, random
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from sheets_topdent import topdent_booking
except ImportError:
    topdent_booking = None

log = logging.getLogger("topdent_bot")
log.setLevel(logging.INFO)
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)

BOT_TOKEN = os.environ.get("TOPDENT_TOKEN", "")
KEM = timezone(timedelta(hours=7))

def tg(method, data=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    payload = json.dumps(data or {}).encode()
    req = urllib.request.Request(url, data=payload)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
            if result.get("ok"):
                return result
    except Exception as e:
        log.warning("tg.%s failed: %s", method, e)
    return {"ok": False}

def send(chat_id, text, reply_markup=None, parse_mode=None):
    msg = {"chat_id": chat_id, "text": text}
    if parse_mode:
        msg["parse_mode"] = parse_mode
    if reply_markup:
        msg["reply_markup"] = json.dumps(reply_markup)
    return tg("sendMessage", msg)

def kb_inline(rows):
    return {"inline_keyboard": rows}

def now_kem():
    return datetime.now(KEM)

def _redis(*args):
    UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "")
    UPSTASH_TOK = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
    if not UPSTASH_URL or not UPSTASH_TOK:
        return None
    body = json.dumps(list(args)).encode()
    req = urllib.request.Request(UPSTASH_URL, data=body)
    req.add_header("Authorization", f"Bearer {UPSTASH_TOK}")
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return json.loads(resp.read()).get("result")
    except Exception:
        return None

def state_get(chat_id):
    key = f"td:state:{chat_id}"
    raw = _redis("GET", key)
    if raw:
        try:
            return json.loads(raw)
        except Exception:
            return None
    return {}

def state_set(chat_id, data):
    key = f"td:state:{chat_id}"
    payload = json.dumps(data, ensure_ascii=False)
    _redis("SET", key, payload, "EX", "3600")

def state_del(chat_id):
    _redis("DEL", f"td:state:{chat_id}")

SPECS = [
    ("therapist", "Терапевт"),
    ("orthopedist", "Ортопед"),
    ("implant", "Имплантация"),
    ("surgeon", "Хирург"),
    ("hygiene", "Гигиена"),
]

DOCTORS = {
    "therapist": [{"id": "anna", "name": "Анна Сергеевна К.", "exp": "12 лет опыта", "rating": "4.9"}],
    "orthopedist": [{"id": "maria", "name": "Мария Александровна В.", "exp": "8 лет опыта", "rating": "4.8"}],
    "implant": [{"id": "dmitry", "name": "Дмитрий Викторович С.", "exp": "15 лет опыта", "rating": "5.0"}],
    "surgeon": [{"id": "sergey", "name": "Сергей Петрович Л.", "exp": "10 лет опыта", "rating": "4.9"}],
    "hygiene": [{"id": "elena", "name": "Елена Михайловна Т.", "exp": "6 лет опыта", "rating": "4.7"}],
}

TIMES_WEEKDAY = ["10:00","10:30","11:00","11:30","12:00","12:30","13:00","13:30",
    "14:00","14:30","15:00","15:30","16:00","16:30",
    "17:00","17:30","18:00","18:30","19:00","19:30","20:00","20:30"]
TIMES_WEEKEND = ["09:00","09:30","10:00","10:30","11:00","11:30",
    "14:00","14:30","15:00","15:30","16:00","16:30"]

CLINIC_PHONE = "+7 (913) 307-77-57"
CLINIC_ADDR = "Рудничный район, ул. Институтская, 34"

def msg_welcome():
    return "ТопДент\n\nЦифровой помощник клиники\n\n\"Запись займет меньше минуты.\""

def kb_welcome():
    return kb_inline([
        [{"text": "Записаться", "callback_data": "bk:start"}],
        [{"text": "Рассчитать стоимость", "callback_data": "pr:start"}],
        [{"text": "Задать вопрос", "callback_data": "faq:start"}],
        [{"text": "Проверить запись", "callback_data": "ac:start"}],
    ])

def msg_booking_spec():
    specs = []
    for key, name in SPECS:
        specs.append([{"text": name, "callback_data": f"bk:spec:{key}"}])
    specs.append([{"text": "← Назад", "callback_data": "bk:back"}])
    return "Шаг 1/5 · Выберите направление", kb_inline(specs)

def msg_booking_doctor(spec_key):
    spec_name = dict(SPECS).get(spec_key, spec_key)
    doctors = DOCTORS.get(spec_key, [])
    rows = []
    for d in doctors:
        text = f"{d['name']}  ·  {d['exp']}  ·  {d['rating']}"
        rows.append([{"text": text, "callback_data": f"bk:doc:{d['id']}"}])
    rows.append([{"text": "← Назад", "callback_data": "bk:start"}])
    return f"Шаг 2/5 · {spec_name}\nВыберите специалиста", kb_inline(rows)

def msg_booking_date():
    today = now_kem()
    day_names = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    rows = []
    row = []
    for i in range(0, 8):
        d = today + timedelta(days=i)
        key = d.strftime("%Y-%m-%d")
        label = d.strftime(f"%d.%m {day_names[d.weekday()]}")
        row.append({"text": label, "callback_data": f"bk:date:{key}"})
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "← Назад", "callback_data": "bk:back_doc"}])
    return "Шаг 3/5 · Выберите дату", kb_inline(rows)

def _time_to_min(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)

def msg_booking_time(date_str, is_today=False):
    try:
        parts = date_str.split(" ")[0].split(".")
        d = datetime(now_kem().year, int(parts[1]), int(parts[0]))
        is_weekend = d.weekday() >= 5
    except Exception:
        is_weekend = False
    times = TIMES_WEEKEND if is_weekend else TIMES_WEEKDAY
    if is_today:
        now = now_kem()
        now_min = now.hour * 60 + now.minute + 5
        times = [t for t in times if _time_to_min(t) > now_min]
    rows = []
    row = []
    for t in times:
        row.append({"text": t, "callback_data": f"bk:time:{t}"})
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([{"text": "← Назад", "callback_data": "bk:back_date"}])
    return "Шаг 4/5 · Выберите время", kb_inline(rows)

def msg_booking_confirm(data):
    spec_name = dict(SPECS).get(data.get("spec",""), data.get("spec",""))
    doctor_name = data.get("doctor",{}).get("name","") if isinstance(data.get("doctor"), dict) else data.get("doctor_name","")
    date = data.get("date","")
    time = data.get("time","")
    name = data.get("name","")
    phone = data.get("phone","")
    text = (
        "Подтвердите запись\n\n"
        f"{spec_name} · {doctor_name}\n"
        f"{date} · {time}\n\n"
        f"{name} · {phone}"
    )
    kb = kb_inline([
        [{"text": "Подтвердить", "callback_data": "bk:confirm"}],
        [{"text": "Отмена", "callback_data": "bk:cancel"}],
    ])
    return text, kb

def handle_start(chat_id):
    state_del(chat_id)
    send(chat_id, msg_welcome(), kb_welcome())

def handle_callback(chat_id, data, msg_id=0):
    if data == "bk:start":
        state_set(chat_id, {"step": "spec"})
        text, kb = msg_booking_spec()
        send(chat_id, text, kb)
    elif data.startswith("bk:spec:"):
        spec_key = data[8:]
        state_set(chat_id, {"step": "doctor", "spec": spec_key})
        text, kb = msg_booking_doctor(spec_key)
        send(chat_id, text, kb)
    elif data.startswith("bk:doc:"):
        doc_id = data[7:]
        st = state_get(chat_id)
        spec_key = st.get("spec", "")
        for d in DOCTORS.get(spec_key, []):
            if d["id"] == doc_id:
                state_set(chat_id, {**st, "step": "date", "doctor": d})
                break
        text, kb = msg_booking_date()
        send(chat_id, text, kb)
    elif data.startswith("bk:date:"):
        st = state_get(chat_id)
        date_key = data[8:]
        try:
            d = datetime.strptime(date_key, "%Y-%m-%d")
            today = now_kem()
            is_today = (d.year == today.year and d.month == today.month and d.day == today.day)
            day_names = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
            date_label = d.strftime(f"%d.%m ({day_names[d.weekday()]})")
            state_set(chat_id, {**st, "step": "time", "date": date_label})
            text, kb = msg_booking_time(date_key, is_today)
            send(chat_id, text, kb)
        except Exception:
            send(chat_id, "Ошибка даты")
    elif data.startswith("bk:time:"):
        st = state_get(chat_id)
        time_val = data[8:]
        state_set(chat_id, {**st, "step": "name", "time": time_val})
        send(chat_id, "Как к вам обратиться?")
    elif data == "bk:confirm":
        st = state_get(chat_id)
        if st.get("step") != "confirm":
            return
        # Save booking to TopDent spreadsheet
        if topdent_booking:
            spec_name = dict(SPECS).get(st.get("spec",""), st.get("spec",""))
            doctor_name = st.get("doctor",{}).get("name","") if isinstance(st.get("doctor"), dict) else ""
            topdent_booking(
                name=st.get("name",""),
                phone=st.get("phone",""),
                doctor=doctor_name,
                service=spec_name,
                date=st.get("date",""),
                time_str=st.get("time",""),
            )
        send(chat_id, "Запись подтверждена!\n\nМы ждём вас!", kb_welcome())
        state_del(chat_id)
    elif data == "bk:cancel":
        state_del(chat_id)
        send(chat_id, "Запись отменена.", kb_welcome())
    elif data == "bk:back":
        handle_start(chat_id)
    elif data == "bk:back_doc":
        st = state_get(chat_id)
        spec_key = st.get("spec", "")
        text, kb = msg_booking_doctor(spec_key)
        send(chat_id, text, kb)
    elif data == "bk:back_date":
        text, kb = msg_booking_date()
        send(chat_id, text, kb)
    elif data == "pr:start":
        rows = []
        for key, (name, price, _) in PRICES.items():
            rows.append([{"text": f"{name} — {price}", "callback_data": f"pr:a:{key}"}])
        rows.append([{"text": "← Назад", "callback_data": "bk:back"}])
        send(chat_id, "Стоимость услуг", kb_inline(rows))
    elif data.startswith("pr:a:"):
        key = data[5:]
        name, price, includes = PRICES.get(key, ("", "", ""))
        send(chat_id, f"{name}\n\n{price}\n\nВключено:\n{includes}", kb_inline([
            [{"text": "Записаться", "callback_data": f"bk:spec:{key}"}],
            [{"text": "← Назад", "callback_data": "pr:start"}],
        ]))
    elif data == "faq:start":
        rows = []
        for key, title, _ in FAQ_DATA:
            rows.append([{"text": title, "callback_data": f"faq:a:{key}"}])
        rows.append([{"text": "← Назад", "callback_data": "bk:back"}])
        send(chat_id, "Частые вопросы", kb_inline(rows))
    elif data.startswith("faq:a:"):
        for k, title, answer in FAQ_DATA:
            if k == data[6:]:
                send(chat_id, f"{title}\n\n{answer}", kb_inline([
                    [{"text": "← Назад", "callback_data": "faq:start"}],
                ]))
                break
    elif data == "ac:start":
        send(chat_id, "Ваши записи будут здесь.", kb_inline([
            [{"text": "Записаться ещё", "callback_data": "bk:start"}],
            [{"text": "← Назад", "callback_data": "bk:back"}],
        ]))

def handle_text(chat_id, text):
    st = state_get(chat_id)
    if st.get("step") == "name":
        if len(text.strip()) < 2:
            send(chat_id, "Введите имя (минимум 2 символа).")
            return
        state_set(chat_id, {**st, "step": "phone", "name": text.strip()})
        send(chat_id, "Введите номер телефона:")
    elif st.get("step") == "phone":
        if len(text.strip()) < 6:
            send(chat_id, "Введите корректный номер телефона.")
            return
        full_st = {**st, "step": "confirm", "phone": text.strip()}
        state_set(chat_id, full_st)
        text_msg, kb = msg_booking_confirm(full_st)
        send(chat_id, text_msg, kb)
    else:
        handle_start(chat_id)

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
                handle_callback(chat_id, cb["data"], cb["message"]["message_id"])
            else:
                chat_id = msg["chat"]["id"]
                text = msg.get("text", "")
                if text == "/start" or text == "/menu":
                    handle_start(chat_id)
                else:
                    handle_text(chat_id, text)
            self._send(200, "ok")
        except Exception as e:
            log.error("handler error: %s", e)
            self._send(500, json.dumps({"error": "Internal error"}))

PRICES = {
    "therapy": ("Терапия", "3 250 – 9 500 ₽", "Кариес, пульпит, реставрация"),
    "ortho": ("Ортопедия", "9 500 – 20 000 ₽", "Коронки, мосты, протезирование"),
    "implant": ("Имплантация","от 45 000 ₽", "Имплант, абатмент, коронка"),
    "surgery": ("Хирургия", "от 3 900 ₽", "Удаление зубов, консультация"),
    "hygiene": ("Гигиена", "4 400 ₽", "Профессиональная чистка + фторирование"),
}

FAQ_DATA = [
    ("hours",    "Режим работы",     "Пн–Пт 10:00–21:00\nСб–Вс 09:00–17:00"),
    ("address",  "Адрес",            f"г. Кемерово, {CLINIC_ADDR}"),
    ("phone",    "Телефон",          f"{CLINIC_PHONE}"),
    ("payment",  "Оплата",           "Картой, наличные, QR-код"),
    ("services", "Услуги",           "Терапия, ортопедия, имплантация, хирургия, гигиена"),
    ("docs",     "Что взять с собой","Паспорт, полис ДМС (если есть), рентген-снимки (если есть)"),
]
