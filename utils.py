import hashlib
import json
import unicodedata
from datetime import datetime, timezone
from dateutil import parser as dtparser


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def local_now_text():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def parse_date(value):
    if not value:
        return None
    try:
        dt = dtparser.parse(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def date_sort_key(value):
    dt = parse_date(value)
    return dt.timestamp() if dt else 0


def normalize_version(value):
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def normalize_text(value):
    text = str(value or "").strip().upper()
    text = unicodedata.normalize("NFKD", text)
    return "".join(
        ch for ch in text
        if not unicodedata.combining(ch)
    )


def ariba_source_key(order, buyer_anid):
    stable = {
        "documentNumber": order.get("documentNumber"),
        "poVersion": order.get("poVersion"),
        "payloadId": order.get("payloadId"),
        "created": order.get("created"),
        "orderDate": order.get("orderDate"),
        "buyerContext": buyer_anid,
    }
    raw = json.dumps(stable, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def money_fields(value):
    if isinstance(value, dict):
        return value.get("amount"), value.get("currencyCode")
    return value, None
