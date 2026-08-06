import os, sys, json, urllib.request, urllib.parse, logging, traceback, random
from datetime import datetime, timezone, timedelta
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from sheets import sheets_booking, sheets_event
except ImportError:
    sheets_booking = None
    sheets_event = None

log = logging.getLogger("topdent")
log.setLevel(logging.INFO)
if not log.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    log.addHandler(h)

BOT_TOKEN = os.environ.get("TOPDENT_TOKEN", "")
OWNER_ID  = int(os.environ.get("OWNER_ID", "0") or "0")
_raw_tg = os.environ.get("OWNER_TG", "").strip()
OWNER_TG  = int(_raw_tg) if _raw_tg and _raw_tg.lstrip("-").isdigit() else OWNER_ID
CLINIC_PHONE = "+7 (913) 307-77-57"
CLINIC_ADDR = "Рудничный район, ул. Институтская, 34"

UPSTASH_URL = os.environ.get("TOPDENT_REDIS_URL", os.environ.get("UPSTASH_REDIS_REST_URL", ""))
UPSTASH_TOK = os.environ.get("TOPDENT_REDIS_TOKEN", os.environ.get("UPSTASH_REDIS_REST_TOKEN", ""))

KEM = timezone(timedelta(hours=7))
_next_id = 1000


def state_get(chat_id):
    """Get booking state from Redis (survives serverless cold starts)."""
    key = f"td:state:{chat_id}"
    raw = _redis("GET", key)
    if raw is not None:
        try:
            return json.loads(raw)
        except Exception:
            return None
    return {}


def state_set(chat_id, data):
    """Save booking state to Redis with 1h TTL."""
    key = f"td:state:{chat_id}"
    payload = json.dumps(data, ensure_ascii=False)
    _redis("SET", key, payload, "EX", "3600")


def state_del(chat_id):
    """Remove booking state from Redis."""
    _redis("DEL", f"td:state:{chat_id}")

# ── Telegram API ────────────────────────────────────
def tg(method, data=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    payload = json.dumps(data or {}).encode()
    req = urllib.request.Request(url, data=payload)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except Exception as e:
        return {"ok": False, "description": str(e)}

def send(chat_id, text, reply_markup=None, parse_mode=None):
    tg("sendChatAction", {"chat_id": chat_id, "action": "typing"})
    msg = {"chat_id": chat_id, "text": text}
    if parse_mode:
        msg["parse_mode"] = parse_mode
    if reply_markup:
        msg["reply_markup"] = json.dumps(reply_markup)
    return tg("sendMessage", msg)


def edit_message(chat_id, message_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "message_id": message_id, "text": text}
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    return tg("editMessageText", data)

def kb_inline(rows):
    return {"inline_keyboard": rows}

def kb_reply(rows, placeholder=""):
    return {
        "keyboard": [[{"text": t} for t in row] for row in rows],
        "resize_keyboard": True,
        "input_field_placeholder": placeholder,
    }

def now_kem():
    return datetime.now(KEM)


def _redis(*args):
    if not UPSTASH_URL or not UPSTASH_TOK:
        log.warning("redis not configured: URL=%s TOK=%s", bool(UPSTASH_URL), bool(UPSTASH_TOK))
        return None
    body = json.dumps(list(args)).encode()
    req = urllib.request.Request(UPSTASH_URL, data=body)
    req.add_header("Authorization", f"Bearer {UPSTASH_TOK}")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            result = json.loads(r.read()).get("result")
            log.info("redis %s → %s", args[0], str(result)[:100])
            return result
    except Exception as e:
        log.error("redis %s failed: %s", args[0], e)
        return None


def appts_get(chat_id):
    raw = _redis("GET", f"td:appts:{chat_id}")
    if raw is not None:
        try:
            data = json.loads(raw)
            log.info("appts_get chat=%s count=%s", chat_id, len(data))
            return data
        except Exception as e:
            log.error("appts_get parse error: %s", e)
            return []
    return []


def appts_set(chat_id, data):
    payload = json.dumps(data, ensure_ascii=False)
    log.info("appts_set chat=%s payload_len=%d", chat_id, len(payload))
    ok = _redis("SET", f"td:appts:{chat_id}", payload, "EX", "604800")
    if ok is None:
        log.warning("appts_set FAILED for chat=%s", chat_id)
        return False
    return True


def appts_append(chat_id, appt):
    appts = appts_get(chat_id)
    appts.append(appt)
    return appts_set(chat_id, appts)

# ── Data ────────────────────────────────────────────
SPECS = [
    ("therapist", "Терапевт"),
    ("orthopedist", "Ортопед"),
    ("implant", "Имплантация"),
    ("surgeon", "Хирург"),
    ("hygiene", "Гигиена"),
]

DOCTORS = {
    "therapist": [
        {"id": "anna", "name": "Анна Сергеевна К.", "exp": "12 лет опыта", "rating": "4.9"},
    ],
    "orthopedist": [
        {"id": "maria", "name": "Мария Александровна В.", "exp": "8 лет опыта", "rating": "4.8"},
    ],
    "implant": [
        {"id": "dmitry", "name": "Дмитрий Викторович С.", "exp": "15 лет опыта", "rating": "5.0"},
    ],
    "surgeon": [
        {"id": "sergey", "name": "Сергей Петрович Л.", "exp": "10 лет опыта", "rating": "4.9"},
    ],
    "hygiene": [
        {"id": "elena", "name": "Елена Михайловна Т.", "exp": "6 лет опыта", "rating": "4.7"},
    ],
}

# v2 times fix
TIMES_WEEKDAY = [
    "10:00","10:30","11:00","11:30","12:00","12:30","13:00","13:30",
    "14:00","14:30","15:00","15:30","16:00","16:30",
    "17:00","17:30","18:00","18:30","19:00","19:30","20:00","20:30",
]
TIMES_WEEKEND = [
    "09:00","09:30","10:00","10:30","11:00","11:30",
    "14:00","14:30","15:00","15:30","16:00","16:30",
]

PRICES = {
    "therapy":  ("Терапия",     "3 250 – 9 500 ₽",    "Кариес, пульпит, реставрация, анестезия"),
    "ortho":    ("Ортопедия",   "9 500 – 20 000 ₽",   "Коронки, мосты, протезирование"),
    "implant":  ("Имплантация","от 45 000 ₽",         "Имплант, абатмент, коронка, контроль"),
    "surgery":  ("Хирургия",    "от 3 900 ₽",          "Удаление зубов, консультация"),
    "hygiene":  ("Гигиена",     "4 400 ₽",             "Профессиональная чистка + фторирование"),
}

FAQ_DATA = [
    ("hours",    "Режим работы",     "Пн–Пт 10:00–21:00\nСб–Вс 09:00–17:00\nПо предварительной записи"),
    ("address",  "Адрес",            f"г. Кемерово, {CLINIC_ADDR}\nРадуга м-н, 650002"),
    ("phone",    "Телефон",          f"{CLINIC_PHONE}"),
    ("payment",  "Оплата",           "Картой, наличные, QR-код"),
    ("services", "Услуги",           "Терапия, ортопедия, имплантация, хирургия, гигиена"),
    ("docs",     "Что взять с собой","Паспорт, полис ДМС (если есть), рентген-снимки (если есть)"),
]

URGENT_KW = ["боль","болит","опухла","отёк","воспаление","сломался","откололся","кровь","гной","киста","флюс"]

SYMPTOM_RULES = {
    "кариес": {"spec": "therapy", "urgency": "средняя", "recommendation": "Запишитесь на приём в ближайшие дни. Не откладывайте — кариес прогрессирует."},
    "пульпит": {"spec": "therapy", "urgency": "высокая", "recommendation": "Нужно срочно! Пульпит требует немедленного лечения. Запишитесь на сегодня."},
    "периодонтит": {"spec": "therapy", "urgency": "высокая", "recommendation": "Срочно к стоматологу! Воспаление вокруг корня требует лечения."},
    " зуб": {"spec": "surgery", "urgency": "средняя", "recommendation": "Если зуб сломан или расшатан — запишитесь к хирургу."},
    "откололся": {"spec": "therapy", "urgency": "средняя", "recommendation": "Сохраните осколок! Реставрация возможна. Запишитесь на приём."},
    "протез": {"spec": "ortho", "urgency": "низкая", "recommendation": "Запишитесь на консультацию к ортопеду для подбора протеза."},
    "имплант": {"spec": "implant", "urgency": "низкая", "recommendation": "Запишитесь на консультацию. Имплантация — это этап за этапом."},
    "чистка": {"spec": "hygiene", "urgency": "низкая", "recommendation": "Профессиональная чистка каждые 6 месяцев. Запишитесь!"},
    "отбеливание": {"spec": "hygiene", "urgency": "низкая", "recommendation": "Сначала чистка, потом отбеливание. Запишитесь на гигиену."},
}

TREATMENT_TIPS = {
    "therapy": [
        "Не ешьте 2 часа после лечения",
        "Избегайте горячего и холодного в течение суток",
        "При боли — ибупрофен по инструкции",
        "Контрольный визит через 2 недели",
    ],
    "ortho": [
        "Носите протез регулярно",
        "Чистите протез специальной щёткой",
        "Снимайте на ночь (если съёмный)",
        "Контрольный визит через 1 месяц",
    ],
    "implant": [
        "Не ешьте твёрдое 3 дня",
        "Антисептик по назначению врача",
        "Контрольные визиты: через 3 дня, 2 недели, 3 месяца",
        "Гигиена каждые 3 месяца",
    ],
    "surgery": [
        "Не полоскайте рот 24 часа",
        "Не ешьте горячее и твёрдое",
        "При кровотечении — марлевый тампон 20 минут",
        "Контрольный визит через 3–5 дней",
    ],
    "hygiene": [
        "Не ешьте 30 минут после чистки",
        "Избегайте красящих продуктов сутки",
        "Используйте ирригатор для межзубных промежутков",
        "Следующая чистка через 6 месяцев",
    ],
}

# ── Messages ────────────────────────────────────────
def msg_welcome():
    return (
        "ТопДент\n\n"
        "Цифровой помощник клиники\n\n"
        "\"Запись займет меньше минуты.\""
    )

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


def _time_to_min(t):
    h, m = t.split(":")
    return int(h) * 60 + int(m)

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

def msg_faq_menu():
    rows = []
    for key, title, _ in FAQ_DATA:
        rows.append([{"text": title, "callback_data": f"faq:a:{key}"}])
    rows.append([{"text": "← Назад", "callback_data": "bk:back"}])
    return "Частые вопросы", kb_inline(rows)

def msg_faq_answer(key, msg_id):
    for k, title, answer in FAQ_DATA:
        if k == key:
            kb = kb_inline([[{"text": "← Назад", "callback_data": f"faq:back:{msg_id}"}]])
            return f"{title}\n\n{answer}", kb
    return "Не нашли ответ? Задайте вопрос оператору.", kb_inline([[{"text": "← Назад", "callback_data": f"faq:back:{msg_id}"}]])

def msg_price_menu():
    rows = []
    for key, (name, price, _) in PRICES.items():
        rows.append([{"text": f"{name} — {price}", "callback_data": f"pr:a:{key}"}])
    rows.append([{"text": "← Назад", "callback_data": "bk:back"}])
    return "Стоимость услуг", kb_inline(rows)

def msg_price_result(key, msg_id):
    name, price, includes = PRICES.get(key, ("", "", ""))
    spec_map = {"therapy": "therapist", "ortho": "orthopedist",
                "implant": "implant", "surgery": "surgeon", "hygiene": "hygiene"}
    spec_key = spec_map.get(key, key)
    text = f"{name}\n\n{price}\n\nВключено:\n{includes}"
    kb = kb_inline([
        [{"text": "Записаться", "callback_data": f"bk:spec:{spec_key}"}],
        [{"text": "← Назад", "callback_data": f"pr:back:{msg_id}"}],
    ])
    return text, kb

def msg_account(chat_id):
    user_appts = appts_get(chat_id)
    if not user_appts:
        kb = kb_inline([
            [{"text": "Записаться", "callback_data": "bk:start"}],
            [{"text": "← Назад", "callback_data": "bk:back"}],
        ])
        return "У вас пока нет записей.", kb
    lines = ["Ваши записи:\n"]
    for i, a in enumerate(user_appts):
        lines.append(f"{i+1}. {a['spec']} · {a['doctor']}\n   {a['date']} · {a['time']}\n   {a['name']} · {a['phone']}")
    rows = []
    for i in range(len(user_appts)):
        rows.append([{"text": f"Отменить запись #{i+1}", "callback_data": f"ac:cancel:{i}"}])
    rows.append([{"text": "Записаться ещё", "callback_data": "bk:start"}])
    rows.append([{"text": "← Назад", "callback_data": "bk:back"}])
    return "\n".join(lines), kb_inline(rows)

# ── Handlers ────────────────────────────────────────
def handle_start(chat_id):
    state_del(chat_id)
    send(chat_id, msg_welcome(), kb_welcome())

def handle_menu(chat_id):
    handle_start(chat_id)

def handle_callback(chat_id, data, msg_id=0):
    parts = data.split(":")

    # ── Booking ──
    if parts[0] == "bk":
        if parts[1] == "start":
            state_set(chat_id, {"step": "spec"})
            text, kb = msg_booking_spec()
            send(chat_id, text, kb)

        elif parts[1] == "spec" and len(parts) > 2:
            spec_key = parts[2]
            doctors = DOCTORS.get(spec_key, [])
            if not doctors:
                send(chat_id, "Временно нет свободных специалистов.")
                return
            state_set(chat_id, {"step": "doctor", "spec": spec_key, "doctor": doctors[0]})
            text, kb = msg_booking_doctor(spec_key)
            send(chat_id, text, kb)

        elif parts[1] == "doc" and len(parts) > 2:
            doc_id = parts[2]
            st = state_get(chat_id)
            spec_key = st.get("spec", "")
            doctor = None
            for d in DOCTORS.get(spec_key, []):
                if d["id"] == doc_id:
                    doctor = d
                    break
            if not doctor:
                return
            state_set(chat_id, {**st, "step": "date", "doctor": doctor})
            text, kb = msg_booking_date()
            send(chat_id, text, kb)

        elif parts[1] == "date" and len(parts) > 2:
            st = state_get(chat_id)
            date_key = parts[2]
            try:
                d = datetime.strptime(date_key, "%Y-%m-%d")
            except ValueError:
                return
            today = now_kem()
            is_today = (d.year == today.year and d.month == today.month and d.day == today.day)
            day_names = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
            date_label = d.strftime(f"%d.%m ({day_names[d.weekday()]})")
            state_set(chat_id, {**st, "step": "time", "date": date_label})
            text, kb = msg_booking_time(date_label, is_today)
            send(chat_id, text, kb)

        elif parts[1] == "time" and len(parts) > 2:
            st = state_get(chat_id)
            time_val = ":".join(parts[2:])
            state_set(chat_id, {**st, "step": "name", "time": time_val})
            send(chat_id, "Как к вам обратиться?")

        elif parts[1] == "confirm":
            st = state_get(chat_id)
            if st.get("step") != "confirm":
                return
            global _next_id
            _next_id += 1
            appt = {
                "id": _next_id,
                "spec": dict(SPECS).get(st.get("spec",""), st.get("spec","")),
                "doctor": st.get("doctor",{}).get("name",""),
                "date": st.get("date",""),
                "time": st.get("time",""),
                "name": st.get("name",""),
                "phone": st.get("phone",""),
            }
            saved = appts_append(chat_id, appt)
            confirm_msg = f"Запись подтверждена\n\n{appt['spec']} · {appt['doctor']}\n{appt['date']} · {appt['time']}\n\nМы ждём вас!"
            if not saved:
                confirm_msg += "\n\n[!] Запись не сохранилась — попробуйте «Проверить запись» позже."
            send(chat_id, confirm_msg, kb_welcome())
            # lead to admin
            lead = (
                f"НОВАЯ ЗАПИСЬ · ТопДент\n\n"
                f"Пациент: {appt['name']}\n"
                f"Телефон: {appt['phone']}\n"
                f"Специалист: {appt['doctor']}\n"
                f"Направление: {appt['spec']}\n"
                f"Дата: {appt['date']} · {appt['time']}"
            )
            if OWNER_TG:
                tg("sendMessage", {"chat_id": OWNER_TG, "text": lead})

            if sheets_booking:
                sheets_booking(
                    name=appt['name'], phone=appt['phone'],
                    doctor=appt['doctor'], service=appt['spec'],
                    date=appt['date'], time=appt['time'],
                )
            state_del(chat_id)

            # Treatment recommendations
            spec_key = st.get("spec", "")
            tips = TREATMENT_TIPS.get(spec_key, [])
            if tips:
                tips_text = "\n".join(f"• {tip}" for tip in tips)
                spec_name = dict(SPECS).get(spec_key, spec_key)
                send(chat_id, f"Рекомендации после визита ({spec_name}):\n\n{tips_text}")

        elif parts[1] == "cancel":
            state_del(chat_id)
            send(chat_id, "Запись отменена.", kb_welcome())

        elif parts[1] == "back":
            state_del(chat_id)
            send(chat_id, msg_welcome(), kb_welcome())

        elif parts[1] == "back_doc":
            st = state_get(chat_id)
            spec_key = st.get("spec", "")
            text, kb = msg_booking_doctor(spec_key)
            send(chat_id, text, kb)

        elif parts[1] == "back_date":
            text, kb = msg_booking_date()
            send(chat_id, text, kb)

    # ── FAQ ──
    elif parts[0] == "faq":
        if parts[1] == "start":
            state_set(chat_id, {"step": "faq"})
            text, kb = msg_faq_menu()
            if msg_id:
                edit_message(chat_id, msg_id, text, kb)
            else:
                send(chat_id, text, kb)
        elif parts[1] == "a" and len(parts) > 2:
            text, kb = msg_faq_answer(parts[2], msg_id)
            edit_message(chat_id, msg_id, text, kb)
        elif parts[1] == "back" and len(parts) > 2:
            try:
                back_id = int(parts[2])
            except (ValueError, IndexError):
                return
            text, kb = msg_faq_menu()
            edit_message(chat_id, back_id, text, kb)

    # ── Price ──
    elif parts[0] == "pr":
        if parts[1] == "start":
            state_set(chat_id, {"step": "price"})
            text, kb = msg_price_menu()
            if msg_id:
                edit_message(chat_id, msg_id, text, kb)
            else:
                send(chat_id, text, kb)
        elif parts[1] == "a" and len(parts) > 2:
            text, kb = msg_price_result(parts[2], msg_id)
            edit_message(chat_id, msg_id, text, kb)
        elif parts[1] == "back" and len(parts) > 2:
            try:
                back_id = int(parts[2])
            except (ValueError, IndexError):
                return
            text, kb = msg_price_menu()
            edit_message(chat_id, back_id, text, kb)

    # ── Account ──
    elif parts[0] == "ac":
        if parts[1] == "start":
            state_set(chat_id, {"step": "account"})
            text, kb = msg_account(chat_id)
            send(chat_id, text, kb)
        elif parts[1] == "cancel" and len(parts) > 2:
            try:
                idx = int(parts[2])
            except (ValueError, IndexError):
                return
            user_appts = appts_get(chat_id)
            if 0 <= idx < len(user_appts):
                removed = user_appts.pop(idx)
                appts_set(chat_id, user_appts)
                send(chat_id, f"Запись на {removed['date']} · {removed['time']} отменена.", kb_welcome())
            else:
                send(chat_id, "Запись не найдена.", kb_welcome())
            state_del(chat_id)

    # ── Global ──
    if data == "menu:back":
        handle_start(chat_id)
        return

def handle_text(chat_id, text):
    st = state_get(chat_id)

    # Symptom triage — check before state machine
    text_lower = text.lower()
    for keyword, info in SYMPTOM_RULES.items():
        if keyword in text_lower:
            spec_name = dict(SPECS).get(info["spec"], info["spec"])
            urgency_label = {"высокая": "[!] ", "средняя": "[~] ", "низкая": "[+] "}.get(info["urgency"], "[-] ")
            response = (
                f"Анализ симптомов\n\n"
                f"Похоже на: {spec_name}\n"
                f"Срочность: {urgency_label}{info['urgency']}\n\n"
                f"{info['recommendation']}\n\n"
                f"Запишитесь на приём:"
            )
            kb = kb_inline([
                [{"text": "Записаться", "callback_data": f"bk:spec:{info['spec']}"}],
                [{"text": "Задать вопрос", "callback_data": "faq:start"}],
                [{"text": "← Меню", "callback_data": "menu:back"}],
            ])
            send(chat_id, response, kb)
            return

    if st.get("step") == "name":
        name = text.strip()
        if len(name) < 2:
            send(chat_id, "Введите имя (минимум 2 символа).")
            return
        state_set(chat_id, {**st, "step": "phone", "name": name})
        send(chat_id, "Введите номер телефона:")

    elif st.get("step") == "phone":
        phone = text.strip()
        if len(phone) < 6:
            send(chat_id, "Введите корректный номер телефона.")
            return
        state_set(chat_id, {**st, "step": "confirm", "phone": phone})
        spec_name = dict(SPECS).get(st.get("spec",""), st.get("spec",""))
        doctor_name = st.get("doctor",{}).get("name","")
        st_name = st.get("name","")
        text_msg = (
            "Подтвердите запись\n\n"
            f"{spec_name} · {doctor_name}\n"
            f"{st.get('date','')} · {st.get('time','')}\n\n"
            f"{st_name} · {phone}"
        )
        kb = kb_inline([
            [{"text": "Подтвердить", "callback_data": "bk:confirm"}],
            [{"text": "Отмена", "callback_data": "bk:cancel"}],
        ])
        send(chat_id, text_msg, kb)

    elif st.get("step") == "faq":
        # AI triage: keyword check
        t = text.lower()
        is_urgent = any(kw in t for kw in URGENT_KW)
        if is_urgent:
            send(chat_id, f"По описанию рекомендуем записаться в ближайшее время.\n\nПозвоните: {CLINIC_PHONE}", kb_inline([
                [{"text": "Записаться", "callback_data": "bk:start"}],
                [{"text": "← Назад", "callback_data": "faq:start"}],
            ]))
        else:
            send(chat_id, "Запишитесь на консультацию — разберёмся.", kb_inline([
                [{"text": "Записаться", "callback_data": "bk:start"}],
                [{"text": "← Назад", "callback_data": "faq:start"}],
            ]))

    elif st.get("step") == "price":
        send(chat_id, "Выберите категорию из кнопок ниже.")

    elif st.get("step") == "account":
        send(chat_id, "Используйте кнопки для управления записями.")

    else:
        handle_start(chat_id)

# ── Vercel Entry Point ─────────────────────────────
class handler(BaseHTTPRequestHandler):
    def _send(self, status, body):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body.encode() if isinstance(body, str) else body)

    def do_GET(self):
        path = self.path.split("?")[0]
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)

        if path == "/api/dashboard":
            token = params.get("token", [""])[0]
            raw = _redis("GET", f"noir:dash:{token}") if token else None
            if raw:
                cached = json.loads(raw)
                # Always rebuild data fresh from Sheets
                try:
                    from sheets import sheets_find_client, sheets_get_projects, sheets_get_events, sheets_get_payments
                    client_name = cached.get("client_name", "")
                    username_d = cached.get("username", "")
                    chat_id_d = cached.get("chat_id", "")
                    client = None
                    if username_d:
                        client = sheets_find_client(username_d)
                    if client and not client_name:
                        client_name = client["name"]
                    if not client and client_name:
                        client = sheets_find_client(client_name)
                    # Fallback: try Redis mapping (chat_id → client_name)
                    if not client_name and chat_id_d:
                        redis_client = _redis("GET", f"noir:client_name:{chat_id_d}")
                        if redis_client:
                            client_name = redis_client
                            client = sheets_find_client(client_name)
                    if client_name:
                        projects = sheets_get_projects(client_name)
                        events = sheets_get_events(client_name)
                        payments = sheets_get_payments(client_name)
                        if projects:
                            proj = projects[0]
                            stage_map = {
                                "Бриф": "brief", "Исследование": "research",
                                "Дизайн": "design", "Разработка": "development",
                                "Интеграции": "integrations", "Запуск": "launch",
                                "Новый": "brief", "В работе": "development",
                            }
                            pkg = proj.get("package", "")
                            raw_stage = proj.get("stage", "")
                            display_stage = {
                                "brief": "Бриф", "research": "Исследование", "design": "Дизайн",
                                "development": "Разработка", "integrations": "Интеграции", "launch": "Запуск",
                                "Бриф": "Бриф", "Исследование": "Исследование", "Дизайн": "Дизайн",
                                "Разработка": "Разработка", "Интеграции": "Интеграции", "Запуск": "Запуск",
                                "Новый": "Бриф", "В работе": "Разработка",
                            }.get(raw_stage, raw_stage)
                            # Use service_price from Redis for modules
                            redis_price = cdata.get("service_price", "")
                            display_price = redis_price if redis_price else proj.get('price', '')
                            # Calculate remaining properly
                            price_str = str(display_price or "0").replace(" ", "").replace("\xa0", "").replace("₽", "")
                            paid_str = str(proj.get("paid", "0")).replace(" ", "").replace("\xa0", "").replace("₽", "")
                            try:
                                price_num = int(price_str) if price_str else 0
                            except ValueError:
                                price_num = 0
                            try:
                                paid_num = int(paid_str) if paid_str else 0
                            except ValueError:
                                paid_num = 0
                            remaining_num = max(0, price_num - paid_num)
                            # Format with spaces: 35 000 ₽
                            price_fmt = f"{price_num:,} ₽".replace(",", " ")
                            remaining_fmt = f"{remaining_num:,} ₽".replace(",", " ")
                            paid_fmt = f"{paid_num:,} ₽".replace(",", " ")
                            data.update({
                                "client_name": client_name,
                                "project_name": proj.get("name", "Проект"),
                                "package": pkg,
                                "stage": display_stage,
                                "progress": proj.get("progress", 0),
                                "price": price_fmt,
                                "paid": paid_fmt,
                                "remaining": remaining_fmt,
                            })
                        if events:
                            data["updates"] = [{"text": e['description'], "date": e["date"]} for e in reversed(events)]
                        if payments:
                            data["payments"] = [{"date": p["date"], "amount": f"{p['amount']} ₽", "method": p["type"]} for p in payments if p.get("status") != "Ожидает"]
                        pkg = data.get("package", "")
                        import secrets as _secrets
                        import urllib.parse as _up
                        contract_raw = _redis("GET", f"noir:contract_data:{client_name}")
                        cdata = {}
                        if contract_raw:
                            try:
                                cdata = json.loads(contract_raw)
                            except Exception:
                                pass
                        invoice_num = cdata.get("num", "")
                        invoice_date = cdata.get("date", "")
                        service = cdata.get("service", "")
                        service_price = cdata.get("service_price", "")
                        if not invoice_num:
                            invoice_num = now_kem().strftime("%Y-%m-") + str(random.randint(100, 999))
                        if not invoice_date:
                            invoice_date = now_kem().strftime('%d.%m.%Y')
                        display_price = service_price if service_price else proj.get('price','').replace(' ','').replace('₽','')
                        if not display_price:
                            display_price = '29000'
                        mod_map_reverse = {"Лендинг / сайт": "landing", "Telegram-бот": "bot", "Автоматизация": "auto", "AI-ассистент": "ai", "Онлайн-оплата": "payment"}
                        pkg_map = {"Старт": "start", "Бизнес": "business", "Премиум": "premium"}
                        if service:
                            pkg_en = mod_map_reverse.get(service, "start")
                        else:
                            pkg_en = pkg_map.get(pkg, pkg.lower()) if pkg else "start"
                        support_map = {"Старт": "1 мес", "Бизнес": "2 мес", "Премиум": "3 мес"}
                        support_val = support_map.get(pkg, "1 мес")
                        if pkg or service:
                            # Use static contract/invoice URLs from Redis (immutable after bot creates lead)
                            static_contract_qs = _redis("GET", f"noir:contract_qs:{client_name}")
                            static_invoice_qs = _redis("GET", f"noir:invoice_qs:{client_name}")
                            if static_contract_qs:
                                contract_url = f"/dogovor.html?{static_contract_qs}"
                            else:
                                contract_url = f"/dogovor.html?{_up.urlencode({'name': client_name, 'phone': client.get('phone','') if client else '', 'task': service if service else proj.get('name',''), 'price': display_price, 'date': invoice_date, 'num': invoice_num, 'tg': client.get('telegram','') if client else '', 'email': client.get('email','') if client else '', 'city': client.get('city','') if client else '', 'support': '1 мес' if service else support_val})}"
                            if static_invoice_qs:
                                invoice_url = f"/invoice?{static_invoice_qs}"
                            else:
                                invoice_url = f"/invoice?name={client_name}&project={proj.get('name','')}&price={display_price}&num={invoice_num}&date={invoice_date}"
                            proposal_code = _secrets.token_urlsafe(8)[:8]
                            _redis("SET", f"noir:proposal:{proposal_code}", json.dumps({
                                "name": client_name, "package": pkg_en,
                                "price": display_price,
                            }, ensure_ascii=False), "EX", 2592000)
                            data["docs"] = [
                                {"name": "Договор", "url": contract_url},
                                {"name": "Коммерческое предложение", "url": f"/proposal?c={proposal_code}"},
                                {"name": "Счёт на оплату", "url": invoice_url},
                            ]
                        _redis("SET", f"noir:dash:{token}",
                               json.dumps(data), "EX", 2592000)
                except Exception as e:
                    log.error("dashboard enrich failed: %s", e)
                self._send(200, json.dumps({"ok": True, **data}))
            else:
                self._send(200, json.dumps({"ok": False}))
            return

        now = now_kem()
        now_min = now.hour * 60 + now.minute + 5
        today_str = now.strftime("%Y-%m-%d")
        test_times = [t for t in TIMES_WEEKDAY if _time_to_min(t) > now_min]
        url_ok = bool(UPSTASH_URL)
        tok_ok = bool(UPSTASH_TOK)
        redis_test = _redis("PING") if url_ok and tok_ok else "not configured"
        self._send(200, json.dumps({
            "status": "ok", "bot": "TopDent", "v": "3.5",
            "redis_url": url_ok, "redis_tok": tok_ok,
            "redis_test": str(redis_test),
            "now": f"{now.hour}:{now.minute:02d}",
            "today": today_str,
            "available_today": test_times[:5]
        }))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        if length > 1048576:
            self._send(413, json.dumps({"error": "Payload too large"}))
            return
        raw = self.rfile.read(length) if length else b"{}"
        try:
            body = json.loads(raw)

            # Dashboard login
            if body.get("action") == "dashboard_login":
                import secrets

                login = body.get("login", "").strip()
                if not login:
                    self._send(200, json.dumps({"ok": False}))
                    return

                # Admin always gets access
                if login.replace("@", "").lower() == "vxrxntsxff":
                    token = secrets.token_urlsafe(16)
                    dashboard_data = {
                        "client_name": "NOIR Admin",
                        "project_name": "NOIR OS",
                        "package": "Админ",
                        "stage": "launch",
                        "progress": 100,
                        "price": "—",
                        "paid": "—",
                        "remaining": "—",
                        "docs": [],
                        "payments": [],
                        "updates": [{"text": "Админ-доступ", "date": "Сейчас"}],
                    }
                    _redis("SET", f"noir:dash:{token}",
                           json.dumps(dashboard_data), "EX", 2592000)
                    self._send(200, json.dumps({"ok": True, "token": token, **dashboard_data}))
                    return

                try:
                    from sheets import sheets_find_client, sheets_get_projects, sheets_get_events, sheets_get_payments, SPREADSHEET_ID, _sheets_api, SHEETS
                    log.info("dashboard_login: searching login=%s SPREADSHEET_ID=%s", login, SPREADSHEET_ID[:15] if SPREADSHEET_ID else "EMPTY")
                    client = sheets_find_client(login)
                    log.info("dashboard_login: client=%s", client)
                    if not client and SPREADSHEET_ID and _sheets_api:
                        result = _sheets_api("GET", f"/values/{SHEETS.get('clients','Clients')}!A:C")
                        rows = result.get("values", []) if result else []
                        log.info("dashboard_login: sheet has %d rows, first3=%s", len(rows), rows[:3])
                except Exception as e:
                    log.error("sheets_find_client failed: %s", e)
                    client = None

                if not client:
                    log.error("dashboard_login: client NOT found for login=%s", login)
                    self._send(200, json.dumps({"ok": False, "debug": "client not found"}))
                    return

                try:
                    projects = sheets_get_projects(client["name"])
                    events = sheets_get_events(client["name"])
                    payments = sheets_get_payments(client["name"])
                except Exception as e:
                    log.error("sheets failed: %s", e)
                    projects, events, payments = [], [], []

                proj = projects[0] if projects else {}

                raw_stage_s = proj.get("stage", "")
                stage = {
                    "brief": "Бриф", "research": "Исследование", "design": "Дизайн",
                    "development": "Разработка", "integrations": "Интеграции", "launch": "Запуск",
                    "Бриф": "Бриф", "Исследование": "Исследование", "Дизайн": "Дизайн",
                    "Разработка": "Разработка", "Интеграции": "Интеграции", "Запуск": "Запуск",
                    "Новый": "Бриф", "В работе": "Разработка",
                }.get(raw_stage_s, raw_stage_s)
                pkg = proj.get("package", "")
                support_map = {"Старт": "1 мес", "Бизнес": "2 мес", "Премиум": "3 мес"}
                support_val = support_map.get(pkg, "1 мес")
                client_name = client["name"] or login
                price_val = proj.get("price", "")
                # Use service_price from Redis for modules
                contract_raw_post = _redis("GET", f"noir:contract_data:{client_name}")
                cdata_post = {}
                if contract_raw_post:
                    try:
                        cdata_post = json.loads(contract_raw_post)
                    except Exception:
                        pass
                redis_price_post = cdata_post.get("service_price", "")
                display_price_post = redis_price_post if redis_price_post else price_val

                # Format remaining with ₽
                remaining_raw_post = str(proj.get("remaining", "")).replace(" ", "").replace("\xa0", "").replace("₽", "")
                paid_raw_post = str(proj.get("paid", "0")).replace(" ", "").replace("\xa0", "").replace("₽", "")
                try:
                    remaining_num_post = int(remaining_raw_post) if remaining_raw_post else 0
                except ValueError:
                    remaining_num_post = 0
                try:
                    paid_num_post = int(paid_raw_post) if paid_raw_post else 0
                except ValueError:
                    paid_num_post = 0
                try:
                    price_num_post = int(str(display_price_post).replace(" ", "").replace("\xa0", "").replace("₽", "")) if display_price_post else 0
                except ValueError:
                    price_num_post = 0
                remaining_calc_post = max(0, price_num_post - paid_num_post)
                remaining_fmt_post = f"{remaining_calc_post:,} ₽".replace(",", " ") if remaining_calc_post > 0 else f"{remaining_num_post:,} ₽".replace(",", " ")
                paid_fmt_post = f"{paid_num_post:,} ₽".replace(",", " ")
                price_fmt_post = f"{price_num_post:,} ₽".replace(",", " ") if price_num_post > 0 else "—"
                dashboard_data = {
                    "client_name": client_name,
                    "project_name": proj.get("name", "Проект"),
                    "package": pkg,
                    "stage": stage,
                    "progress": proj.get("progress", 0),
                    "price": price_fmt_post,
                    "paid": paid_fmt_post,
                    "remaining": remaining_fmt_post,
                    "docs": [] if not pkg else [],
                    "payments": [{"date": p["date"], "amount": f"{p['amount']} ₽", "method": p["type"]} for p in payments if p.get("status") != "Ожидает"] if payments else [],
                    "updates": [{"text": e['description'], "date": e["date"]} for e in reversed(events)] if events else [{"text": "Вы вошли в кабинет", "date": "Сейчас"}],
                }

                if pkg or cdata_post.get("service", ""):
                    invoice_num = cdata_post.get("num", "")
                    invoice_date = cdata_post.get("date", "")
                    service_c = cdata_post.get("service", "")
                    service_price_c = cdata_post.get("service_price", "")
                    if not invoice_num:
                        invoice_num = now_kem().strftime("%Y-%m-") + str(random.randint(100, 999))
                    if not invoice_date:
                        invoice_date = now_kem().strftime('%d.%m.%Y')
                    display_price = service_price_c if service_price_c else price_val.replace(' ','').replace('₽','')
                    if not display_price:
                        display_price = '29000'
                    mod_map_reverse = {"Лендинг / сайт": "landing", "Telegram-бот": "bot", "Автоматизация": "auto", "AI-ассистент": "ai", "Онлайн-оплата": "payment"}
                    pkg_map = {"Старт": "start", "Бизнес": "business", "Премиум": "premium"}
                    if service_c:
                        pkg_en = mod_map_reverse.get(service_c, "start")
                    else:
                        pkg_en = pkg_map.get(pkg, pkg.lower()) if pkg else "start"
                    # Use static URLs from Redis (immutable after bot creates lead)
                    static_contract_qs = _redis("GET", f"noir:contract_qs:{client_name}")
                    static_invoice_qs = _redis("GET", f"noir:invoice_qs:{client_name}")
                    import urllib.parse as _up
                    if static_contract_qs:
                        contract_url = f"/dogovor.html?{static_contract_qs}"
                    else:
                        contract_url = f"/dogovor.html?{_up.urlencode({'name': client_name, 'phone': client.get('phone','') if client else '', 'task': service_c if service_c else proj.get('name',''), 'price': display_price, 'date': invoice_date, 'num': invoice_num, 'tg': client.get('telegram','') if client else '', 'email': client.get('email','') if client else '', 'city': client.get('city','') if client else '', 'support': '1 мес' if service_c else support_val})}"
                    if static_invoice_qs:
                        invoice_url = f"/invoice?{static_invoice_qs}"
                    else:
                        invoice_url = f"/invoice?project={proj.get('name','')}&price={display_price}&name={client_name}&num={invoice_num}&date={invoice_date}"
                    proposal_code = secrets.token_urlsafe(8)[:8]
                    _redis("SET", f"noir:proposal:{proposal_code}", json.dumps({
                        "name": client_name, "package": pkg_en, "price": display_price,
                    }, ensure_ascii=False), "EX", 2592000)
                    dashboard_data["docs"] = [
                        {"name": "Договор", "url": contract_url},
                        {"name": "Коммерческое предложение", "url": f"/proposal?c={proposal_code}"},
                        {"name": "Счёт на оплату", "url": invoice_url},
                    ]

                token = secrets.token_urlsafe(16)
                _redis("SET", f"noir:dash:{token}",
                       json.dumps(dashboard_data), "EX", 2592000)
                self._send(200, json.dumps({"ok": True, "token": token, **dashboard_data}))
                return

            msg = body.get("message") or body.get("callback_query")
            if not msg:
                self._send(200, "ok")
                return

            if "callback_query" in body:
                cb = body["callback_query"]
                chat_id = cb["message"]["chat"]["id"]
                chat_type = cb["message"]["chat"].get("type", "private")
                if chat_type != "private":
                    self._send(200, "ok")
                    return
                tg("answerCallbackQuery", {"callback_query_id": cb["id"]})
                handle_callback(chat_id, cb["data"], cb["message"]["message_id"])
            else:
                chat_id = msg["chat"]["id"]
                chat_type = msg["chat"].get("type", "private")
                if chat_type != "private":
                    self._send(200, "ok")
                    return
                text = msg.get("text", "")
                if text == "/start" or text == "/menu":
                    handle_start(chat_id)
                else:
                    handle_text(chat_id, text)

            self._send(200, "ok")
        except Exception as e:
            log.error("handler error: %s\n%s", e, traceback.format_exc())
            self._send(500, json.dumps({"error": "Internal error"}))
