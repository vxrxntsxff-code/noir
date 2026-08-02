"""Google Sheets CRM — direct API with service account.

Env vars:
  GOOGLE_SA_JSON    — Service account JSON key (full JSON string)
  GOOGLE_SHEET_ID   — Spreadsheet ID

Usage:
  from sheets import sheets_lead, sheets_client, sheets_update
"""

import os, json, base64, time, hashlib, logging, urllib.request, urllib.parse
from datetime import datetime, timezone, timedelta

log = logging.getLogger("sheets")

SA_JSON = os.environ.get("GOOGLE_SA_JSON", "")
SPREADSHEET_ID = os.environ.get("GOOGLE_SHEET_ID", "")

KEM = timezone(timedelta(hours=7))

SHEETS = {
    "clients": "Clients",
    "projects": "Projects",
    "payments": "Payments",
    "events": "Events",
    "messages": "Messages",
}

_token_cache = {"token": None, "expires": 0}


def _now():
    return datetime.now(KEM).strftime("%d.%m.%Y %H:%M")


def _parse_num(val):
    try:
        return round(float(str(val).strip().replace(",", ".")), 1)
    except (ValueError, TypeError):
        return 0


# ── JWT + OAuth2 for service account ──

def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _get_token():
    """Get Google OAuth2 access token via service account JWT."""
    if not SA_JSON:
        log.warning("GOOGLE_SA_JSON not configured")
        return None

    now = time.time()
    if _token_cache["token"] and _token_cache["expires"] > now + 60:
        return _token_cache["token"]

    try:
        sa = json.loads(SA_JSON)
    except Exception as e:
        log.error("Failed to parse GOOGLE_SA_JSON: %s", e)
        return None

    private_key = sa["private_key"]
    client_email = sa["client_email"]

    # Build JWT
    header = {"alg": "RS256", "typ": "JWT"}
    now_int = int(now)
    payload = {
        "iss": client_email,
        "scope": "https://www.googleapis.com/auth/spreadsheets",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now_int,
        "exp": now_int + 3600,
    }

    signing_input = _b64url(json.dumps(header).encode()) + "." + _b64url(json.dumps(payload).encode())

    # Sign with private key using Python ssl/crypto
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding

        # Load private key
        key = serialization.load_pem_private_key(
            private_key.encode(), password=None
        )

        # Sign
        signature = key.sign(
            signing_input.encode(),
            padding.PKCS1v15(),
            hashes.SHA256()
        )
    except ImportError:
        # Fallback: use subprocess with openssl
        import subprocess, tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write(private_key)
            key_file = f.name
        try:
            proc = subprocess.run(
                ["openssl", "dgst", "-sha256", "-sign", key_file],
                input=signing_input.encode(),
                capture_output=True, timeout=10
            )
            signature = proc.stdout
        finally:
            os.unlink(key_file)

    jwt_token = signing_input + "." + _b64url(signature)

    # Exchange JWT for access token
    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt_token,
    }).encode()

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body, method="POST"
    )
    req.add_header("Content-Type", "application/x-www-form-urlencoded")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            token = data.get("access_token")
            expires_in = data.get("expires_in", 3600)
            _token_cache["token"] = token
            _token_cache["expires"] = now + expires_in
            return token
    except Exception as e:
        log.error("Google token exchange failed: %s", e)
        return None


def _sheets_api(method, path, body=None):
    """Call Google Sheets API."""
    token = _get_token()
    if not token:
        return None

    url = f"https://sheets.googleapis.com/v4/spreadsheets/{SPREADSHEET_ID}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if body:
        req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read())
    except Exception as e:
        log.error("Sheets API %s failed: %s", path, e)
        return None


def _append_row(sheet_name, values):
    """Append a row to a sheet."""
    return _sheets_api(
        "POST",
        f"/values/{sheet_name}:append?valueInputOption=USER_ENTERED",
        {"values": [values]}
    )


def _find_row(sheet_name, col_letter, value):
    """Find row number where col_letter=value. Returns 1-indexed row or None."""
    result = _sheets_api("GET", f"/values/{sheet_name}!A:Z")
    if not result or "values" not in result:
        return None
    col_idx = ord(col_letter.upper()) - ord("A")
    for i, row in enumerate(result["values"], start=1):
        if len(row) > col_idx and row[col_idx] == value:
            return i
    return None


def _update_cell(sheet_name, row, col_letter, value):
    """Update a single cell."""
    return _sheets_api(
        "PUT",
        f"/values/{sheet_name}!{col_letter}{row}?valueInputOption=USER_ENTERED",
        {"values": [[value]]}
    )


# ── Public API ──

def sheets_client(**kwargs):
    """Add a client row."""
    if not SPREADSHEET_ID:
        log.warning("GOOGLE_SHEET_ID not configured")
        return False
    values = [
        kwargs.get("name", ""),       # A: ФИО
        kwargs.get("phone", ""),      # B: Телефон
        kwargs.get("telegram", ""),   # C: Telegram
        kwargs.get("email", ""),      # D: Email
        kwargs.get("city", ""),       # E: Город
        kwargs.get("niche", ""),      # F: Ниша
        kwargs.get("budget", ""),     # G: Бюджет
        kwargs.get("source", ""),     # H: Источник
        kwargs.get("status", "Новый"),# I: Статус
        _now(),                       # J: Дата
    ]
    return _append_row(SHEETS["clients"], values) is not None


def sheets_project(**kwargs):
    """Add a project row."""
    if not SPREADSHEET_ID:
        return False
    values = [
        _now(),                        # A: Дата
        kwargs.get("client", ""),       # B: Клиент
        kwargs.get("name", ""),         # C: Название
        kwargs.get("package", ""),      # D: Пакет
        kwargs.get("status", "Новый"), # E: Статус
        kwargs.get("stage", "Бриф"),   # F: Этап
        str(kwargs.get("progress", 0)),# G: Прогресс
        kwargs.get("deadline", ""),     # H: Дедлайн
        kwargs.get("price", ""),        # I: Цена
        kwargs.get("paid", "0"),        # J: Оплачено
        kwargs.get("remaining", ""),    # K: Остаток
    ]
    return _append_row(SHEETS["projects"], values) is not None


def sheets_payment(**kwargs):
    """Add a payment row."""
    if not SPREADSHEET_ID:
        return False
    values = [
        _now(),                        # A: Дата
        kwargs.get("project", ""),      # B: Проект
        kwargs.get("client", ""),       # C: Клиент
        kwargs.get("amount", ""),       # D: Сумма
        kwargs.get("type", "Аванс"),   # E: Тип
        kwargs.get("status", "Ожидает"),# F: Статус
        kwargs.get("method", "QR"),    # G: Способ
        kwargs.get("receipt", ""),      # H: Чек
        kwargs.get("purpose", ""),      # I: Назначение
    ]
    return _append_row(SHEETS["payments"], values) is not None


def sheets_event(**kwargs):
    """Add an event row."""
    if not SPREADSHEET_ID:
        return False
    values = [
        _now(),                        # A: Дата
        kwargs.get("project", ""),      # B: Проект
        kwargs.get("client", ""),       # C: Клиент
        kwargs.get("type", ""),         # D: Тип
        kwargs.get("description", ""),  # E: Описание
        kwargs.get("importance", "Обычная"),  # F: Важность
    ]
    return _append_row(SHEETS["events"], values) is not None


def sheets_message(**kwargs):
    """Add a message row."""
    if not SPREADSHEET_ID:
        return False
    values = [
        _now(),
        kwargs.get("project", ""),
        kwargs.get("client", ""),
        kwargs.get("sender", ""),
        kwargs.get("text", ""),
        kwargs.get("read", "Нет"),
    ]
    return _append_row(SHEETS["messages"], values) is not None


def sheets_update(sheet_name, row_key, row_value, update_col, update_value):
    """Update a cell: find row where row_key=row_value, set update_col=update_value."""
    if not SPREADSHEET_ID:
        return False
    row = _find_row(sheet_name, row_key, row_value)
    if row:
        return _update_cell(sheet_name, row, update_col, update_value) is not None
    log.warning("sheets_update: row not found for %s=%s", row_key, row_value)
    return False


def sheets_lead(name="", phone="", telegram="", email="", source="bot", city="", niche="", budget=""):
    """Quick lead entry."""
    return sheets_client(
        name=name, phone=phone, telegram=telegram, email=email,
        source=source, city=city, niche=niche, budget=budget,
        status="Новый",
    )


def sheets_find_client(query):
    """Find client by phone or telegram. Returns dict or None."""
    if not SPREADSHEET_ID:
        log.warning("sheets_find_client: GOOGLE_SHEET_ID not configured")
        return None
    result = _sheets_api("GET", f"/values/{SHEETS['clients']}!A:Z")
    if not result or "values" not in result:
        log.warning("sheets_find_client: no data, result=%s", str(result)[:200])
        return None
    q = query.lower().replace("@", "").replace("+", "").strip()
    log.info("sheets_find_client: query=%s norm=%s rows=%d", query, q, len(result["values"]))
    for i, row in enumerate(result["values"], start=2):
        # Clients: A:ФИО B:Телефон C:Telegram D:Email E:Город F:Ниша
        phone = str(row[1]).replace("+", "").replace(" ", "").replace("-", "") if len(row) > 1 else ""
        tg = str(row[2]).replace("@", "").lower() if len(row) > 2 else ""
        if q in phone or q in tg:
            log.info("sheets_find_client: FOUND row=%d name=%s", i, row[0] if row else "")
            return {
                "row": i,
                "name": str(row[0]) if len(row) > 0 else "",
                "phone": str(row[1]) if len(row) > 1 else "",
                "telegram": str(row[2]) if len(row) > 2 else "",
                "email": str(row[3]) if len(row) > 3 else "",
                "city": str(row[4]) if len(row) > 4 else "",
                "niche": str(row[5]) if len(row) > 5 else "",
            }
    log.info("sheets_find_client: NOT FOUND. rows sample: %s", [r[:3] for r in result["values"][1:4]])
    return None


def sheets_get_projects(client_name):
    """Get projects for a client by name. Returns list of dicts."""
    if not SPREADSHEET_ID:
        log.warning("sheets_get_projects: no SPREADSHEET_ID")
        return []
    result = _sheets_api("GET", f"/values/{SHEETS['projects']}!A:K")
    if not result or "values" not in result:
        log.warning("sheets_get_projects: no data from Sheets")
        return []
    projects = []
    cn = client_name.strip().lower()
    for i, row in enumerate(result["values"]):
        # Projects: A:Дата B:Клиент C:Название D:Пакет E:Статус F:Этап G:Прогресс H:Дедлайн I:Цена J:Оплачено K:Остаток
        if i == 0:
            continue  # skip header
        client_val = str(row[1]).strip().lower() if len(row) > 1 else ""
        if client_val == cn:
            projects.append({
                "name": str(row[2]) if len(row) > 2 else "",
                "package": str(row[3]) if len(row) > 3 else "",
                "status": str(row[4]) if len(row) > 4 else "",
                "stage": str(row[5]) if len(row) > 5 else "brief",
                "progress": _parse_num(row[6]),
                "price": str(row[8]) if len(row) > 8 else "",
                "paid": str(row[9]) if len(row) > 9 else "0",
                "remaining": str(row[10]) if len(row) > 10 else "",
            })
    log.info("sheets_get_projects client='%s' found=%d", client_name, len(projects))
    return projects


def sheets_update_project(client_name, field, value):
    """Update a project field in Google Sheets."""
    if not SPREADSHEET_ID:
        return False
    result = _sheets_api("GET", f"/values/{SHEETS['projects']}!A:K")
    if not result or "values" not in result:
        return False
    field_map = {
        "name": 2, "package": 3, "status": 4, "stage": 5,
        "progress": 6, "deadline": 7, "price": 8, "paid": 9, "remaining": 10,
    }
    col_idx = field_map.get(field)
    if col_idx is None:
        return False
    for i, row in enumerate(result["values"], start=1):
        if len(row) > 1 and str(row[1]).lower() == client_name.lower():
            return _update_cell(SHEETS["projects"], i, chr(ord("A") + col_idx), str(value)) is not None
    return False


def sheets_update_project_by_row(row_str, field, value):
    """Update a project field by row number (1-indexed from Sheets)."""
    if not SPREADSHEET_ID:
        return False
    field_map = {
        "name": 2, "package": 3, "status": 4, "stage": 5,
        "progress": 6, "deadline": 7, "price": 8, "paid": 9, "remaining": 10,
    }
    col_idx = field_map.get(field)
    if col_idx is None:
        return False
    try:
        row = int(row_str)
    except ValueError:
        return False
    return _update_cell(SHEETS["projects"], row, chr(ord("A") + col_idx), str(value)) is not None


def sheets_add_update(client_name, text):
    """Add an update event for a project."""
    return sheets_event(
        project=client_name,
        client=client_name,
        type="Обновление",
        description=text,
        importance="Обычная",
    )


def sheets_booking(name, phone, doctor, service, date, time):
    """TopDent booking entry."""
    sheets_client(name=name, phone=phone, source="topdent_bot", status="Записан")
    sheets_event(
        type="Запись",
        description=f"{doctor} · {service} · {date} {time}",
        importance="Высокая",
    )


def sheets_get_events(client_name):
    """Get events for a client. Returns list of {date, type, description}."""
    if not SPREADSHEET_ID:
        return []
    result = _sheets_api("GET", f"/values/{SHEETS['events']}!A:F")
    if not result or "values" not in result:
        return []
    events = []
    cn = client_name.strip().lower()
    for row in result["values"][1:]:
        client_val = str(row[2]).strip().lower() if len(row) > 2 else ""
        if client_val == cn:
            events.append({
                "date": str(row[0]) if len(row) > 0 else "",
                "type": str(row[3]) if len(row) > 3 else "",
                "description": str(row[4]) if len(row) > 4 else "",
            })
    return events[-10:]


def sheets_get_payments(client_name):
    """Get payments for a client. Returns list of {date, amount, type, method}."""
    if not SPREADSHEET_ID:
        return []
    result = _sheets_api("GET", f"/values/{SHEETS['payments']}!A:I")
    if not result or "values" not in result:
        return []
    payments = []
    cn = client_name.strip().lower()
    for row in result["values"][1:]:
        client_val = str(row[2]).strip().lower() if len(row) > 2 else ""
        if client_val == cn:
            payments.append({
                "date": str(row[0]) if len(row) > 0 else "",
                "amount": str(row[3]) if len(row) > 3 else "",
                "type": str(row[4]) if len(row) > 4 else "",
                "method": str(row[6]) if len(row) > 6 else "",
            })
    return payments
