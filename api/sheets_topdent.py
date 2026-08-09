"""Google Sheets for TopDent bookings.

Writes to a separate spreadsheet for dental clinic bookings.
"""
import os, json, base64, time, logging, urllib.request
from datetime import datetime, timezone, timedelta

log = logging.getLogger("sheets_topdent")

SA_JSON = os.environ.get("GOOGLE_SA_JSON", "")
SPREADSHEET_ID = os.environ.get("TOPDENT_SHEET_ID", "15pUGJTy5HQDhXGhXxy5N3_S3Jm0U4TFRcj3pNKP75wE")

KEM = timezone(timedelta(hours=7))

_token_cache = {"token": None, "expires": 0}


def _b64url(data):
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _get_token():
    if not SA_JSON:
        return None
    now = time.time()
    if _token_cache["token"] and _token_cache["expires"] > now + 60:
        return _token_cache["token"]
    try:
        sa = json.loads(SA_JSON)
    except Exception:
        return None
    header = {"alg": "RS256", "typ": "JWT"}
    now_int = int(now)
    payload = {
        "iss": sa["client_email"],
        "scope": "https://www.googleapis.com/auth/spreadsheets",
        "aud": "https://oauth2.googleapis.com/token",
        "iat": now_int,
        "exp": now_int + 3600,
    }
    signing_input = _b64url(json.dumps(header).encode()) + "." + _b64url(json.dumps(payload).encode())
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import padding
        key = serialization.load_pem_private_key(sa["private_key"].encode(), password=None)
        signature = key.sign(signing_input.encode(), padding.PKCS1v15(), hashes.SHA256())
    except ImportError:
        import subprocess, tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pem', delete=False) as f:
            f.write(sa["private_key"])
            key_file = f.name
        try:
            proc = subprocess.run(["openssl", "dgst", "-sha256", "-sign", key_file],
                                input=signing_input.encode(), capture_output=True, timeout=10)
            signature = proc.stdout
        finally:
            os.unlink(key_file)
    jwt_token = signing_input + "." + _b64url(signature)
    body = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": jwt_token,
    }).encode()
    req = urllib.request.Request("https://oauth2.googleapis.com/token", data=body, method="POST")
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
        log.error("token failed: %s", e)
        return None


def _sheets_api(method, path, body=None):
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


def _now():
    return datetime.now(KEM).strftime("%d.%m.%Y %H:%M")


def topdent_booking(name, phone, doctor, service, date, time_str):
    """Add a booking row to TopDent spreadsheet."""
    log.info("topdent_bookING CALLED: name=%s phone=%s doctor=%s service=%s date=%s time=%s",
             name, phone, doctor, service, date, time_str)
    log.info("topdent_booking SPREADSHEET_ID=%s SA_JSON_SET=%s", SPREADSHEET_ID, bool(SA_JSON))
    values = [
        _now(),
        name,
        phone,
        service,
        doctor,
        date,
        time_str,
        "Новый",
    ]
    result = _sheets_api(
        "POST",
        "/values/Bookings!A:H:append?valueInputOption=USER_ENTERED",
        {"values": [values]}
    )
    if result:
        log.info("topdent_booking OK: %s %s", name, phone)
    else:
        log.error("topdent_booking FAIL: %s %s (check if sheet 'Bookings' exists and SA has access)", name, phone)
    return result is not None
