import os
import json
import html
import logging
import re
import shutil
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("talayar")

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BRS_API_URL = os.environ.get("BRS_API_URL")
ADMIN_ID = os.environ.get("ADMIN_ID", "7361040390")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "WAHL4").lstrip("@")
PAYMENT_INFO = os.environ.get(
    "PAYMENT_INFO",
    f"برای دریافت شماره کارت و هماهنگی پرداخت به @{ADMIN_USERNAME} پیام بدهید.",
)
DATA_DIR = os.environ.get("DATA_DIR", "/data" if os.path.isdir("/data") else ".")

API_TIMEOUT = 20
CACHE_TTL_SECONDS = 20
FREE_ALERT_LIMIT = 1
ALERT_CHECK_INTERVAL = 60
HISTORY_SAVE_INTERVAL = 300
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
VIP_PRICE_30 = os.environ.get("VIP_PRICE_30", "69,000")
VIP_PRICE_90 = os.environ.get("VIP_PRICE_90", "249,000")
DISCLAIMER = "قیمت‌ها ممکن است با بازار اختلاف یا تأخیر داشته باشند و توصیه خرید یا فروش نیستند."
ALERTS_FILE = os.path.join(DATA_DIR, "alerts.json")
VIP_USERS_FILE = os.path.join(DATA_DIR, "vip_users.json")
DAILY_SUBS_FILE = os.path.join(DATA_DIR, "daily_subs.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
PURCHASES_FILE = os.path.join(DATA_DIR, "purchase_requests.json")
HISTORY_FILE = os.path.join(DATA_DIR, "price_history.json")
BOT_STATE_FILE = os.path.join(DATA_DIR, "bot_state.json")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")
_market_cache = {"data": None, "saved_at": 0.0}
_data_lock = threading.Lock()

ALERT_ASSETS = {
    "usd": {
        "label": "دلار آمریکا",
        "symbols": ["USD", "IR_USD", "USD_IRR", "USD_IRT"],
        "sections": ["currency"],
        "keywords": ["دلار آمریکا", "US Dollar"],
    },
    "gold18": {
        "label": "طلای ۱۸ عیار",
        "symbols": ["IR_GOLD_18K"],
        "sections": ["gold"],
        "keywords": ["طلای 18", "18K Gold"],
    },
    "emami": {
        "label": "سکه امامی",
        "symbols": ["IR_COIN_EMAMI", "IR_COIN_FULL"],
        "sections": ["gold"],
        "keywords": ["سکه امامی", "Emami"],
    },
    "half": {
        "label": "نیم‌سکه",
        "symbols": ["IR_COIN_HALF"],
        "sections": ["gold"],
        "keywords": ["نیم سکه", "Half Coin"],
    },
    "quarter": {
        "label": "ربع‌سکه",
        "symbols": ["IR_COIN_QUARTER"],
        "sections": ["gold"],
        "keywords": ["ربع سکه", "Quarter Coin"],
    },
    "ounce": {
        "label": "انس جهانی طلا",
        "symbols": ["XAUUSD", "XAU_USD"],
        "sections": ["gold"],
        "keywords": ["انس جهانی", "Gold Ounce"],
    },
    "btc": {
        "label": "بیت‌کوین",
        "symbols": ["BTC", "BTCUSDT"],
        "sections": ["cryptocurrency"],
        "keywords": ["Bitcoin", "بیت کوین"],
    },
}


def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 قیمت لحظه‌ای", callback_data="prices"),
         InlineKeyboardButton("🔔 هشدار قیمت", callback_data="alerts")],
        [InlineKeyboardButton("🗓 گزارش روزانه", callback_data="daily"),
         InlineKeyboardButton("📈 نمودار قیمت", callback_data="charts")],
        [InlineKeyboardButton("🧮 ماشین‌حساب طلا", callback_data="calculator"),
         InlineKeyboardButton("👤 حساب کاربری", callback_data="account")],
        [InlineKeyboardButton("⭐ عضویت VIP", callback_data="vip"),
         InlineKeyboardButton("ℹ️ راهنما", callback_data="help")],
    ])


def price_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 بازار ارز", callback_data="iran_currency")],
        [InlineKeyboardButton("🪙 طلا و سکه", callback_data="gold")],
        [InlineKeyboardButton("🌎 انس جهانی", callback_data="ounce")],
        [InlineKeyboardButton("₿ ارز دیجیتال", callback_data="crypto")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]
    ])


def alert_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ ساخت هشدار جدید", callback_data="alert_new")],
        [InlineKeyboardButton("📋 هشدارهای من", callback_data="alert_list"),
         InlineKeyboardButton("🗑 حذف همه", callback_data="alert_delete")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ])


def alert_asset_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 دلار", callback_data="alert_asset:usd"),
         InlineKeyboardButton("🪙 طلای ۱۸ عیار", callback_data="alert_asset:gold18")],
        [InlineKeyboardButton("🟡 سکه امامی", callback_data="alert_asset:emami"),
         InlineKeyboardButton("نیم‌سکه", callback_data="alert_asset:half")],
        [InlineKeyboardButton("ربع‌سکه", callback_data="alert_asset:quarter"),
         InlineKeyboardButton("🌎 انس جهانی", callback_data="alert_asset:ounce")],
        [InlineKeyboardButton("₿ بیت‌کوین", callback_data="alert_asset:btc")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="alerts")],
    ])


def alert_condition_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 بالاتر یا مساوی", callback_data="alert_condition:above")],
        [InlineKeyboardButton("📉 پایین‌تر یا مساوی", callback_data="alert_condition:below")],
        [InlineKeyboardButton("🔙 انتخاب دارایی", callback_data="alert_new")],
    ])


def alert_kind_menu(user_id):
    rows = [[InlineKeyboardButton("🎯 هشدار عددی", callback_data="alert_kind:price")]]
    if is_vip(user_id):
        rows.append([InlineKeyboardButton("📊 هشدار درصد تغییر VIP", callback_data="alert_kind:percent")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="alerts")])
    return InlineKeyboardMarkup(rows)


def alert_mode_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣ یک‌باره", callback_data="alert_mode:once")],
        [InlineKeyboardButton("🔁 تکرارشونده VIP", callback_data="alert_mode:repeat")],
        [InlineKeyboardButton("❌ لغو", callback_data="alerts")],
    ])


def percent_condition_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 افزایش درصدی", callback_data="alert_condition:up")],
        [InlineKeyboardButton("📉 کاهش درصدی", callback_data="alert_condition:down")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="alert_new")],
    ])


def vip_menu(user_id=None):
    rows = []
    if user_id is None or not is_vip(user_id):
        rows += [
            [InlineKeyboardButton(f"⭐ یک‌ماهه — {VIP_PRICE_30} تومان", callback_data="buy:30")],
            [InlineKeyboardButton(f"🌟 سه‌ماهه — {VIP_PRICE_90} تومان", callback_data="buy:90")],
        ]
    rows += [
        [InlineKeyboardButton("💬 ارتباط با ادمین", url=f"https://t.me/{ADMIN_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ]
    return InlineKeyboardMarkup(rows)


def daily_menu(active=False):
    rows = [
        [InlineKeyboardButton("09:00", callback_data="daily_set:09:00"),
         InlineKeyboardButton("14:00", callback_data="daily_set:14:00"),
         InlineKeyboardButton("21:00", callback_data="daily_set:21:00")],
        [InlineKeyboardButton("⌨️ ساعت دلخواه", callback_data="daily_custom")],
    ]
    if active:
        rows.append([InlineKeyboardButton("⛔ توقف گزارش", callback_data="daily_stop")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="home")])
    return InlineKeyboardMarkup(rows)


def chart_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 دلار", callback_data="chart_asset:usd"),
         InlineKeyboardButton("🪙 طلای ۱۸", callback_data="chart_asset:gold18")],
        [InlineKeyboardButton("🟡 سکه امامی", callback_data="chart_asset:emami"),
         InlineKeyboardButton("🌎 انس", callback_data="chart_asset:ounce")],
        [InlineKeyboardButton("₿ بیت‌کوین", callback_data="chart_asset:btc")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ])


def chart_period_menu(asset):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("۲۴ ساعت", callback_data=f"chart:{asset}:24"),
         InlineKeyboardButton("۷ روز VIP", callback_data=f"chart:{asset}:168")],
        [InlineKeyboardButton("🔙 انتخاب دارایی", callback_data="charts")],
    ])


def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار", callback_data="admin:stats"),
         InlineKeyboardButton("🧾 خریدهای منتظر", callback_data="admin:pending")],
        [InlineKeyboardButton("📣 پیام همگانی", callback_data="admin:broadcast"),
         InlineKeyboardButton("💾 پشتیبان", callback_data="admin:backup")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="home")],
    ])


def vip_text(user_id):
    if is_vip(user_id):
        days = vip_days_left(user_id)
        return ("⭐ <b>عضویت VIP فعال است</b> ✅\n\n"
                f"زمان باقی‌مانده: {'بدون انقضا' if days is None else str(days) + ' روز'}\n"
                "هشدار نامحدود، درصدی و تکرارشونده، گزارش روزانه و نمودار هفتگی فعال‌اند.")
    return ("⭐ <b>عضویت VIP طلایار</b>\n\n"
            "✅ هشدار نامحدود، درصدی و تکرارشونده\n"
            "✅ گزارش روزانه خودکار\n✅ نمودار هفتگی\n\n"
            f"یک‌ماهه: <b>{VIP_PRICE_30} تومان</b>\nسه‌ماهه: <b>{VIP_PRICE_90} تومان</b>")


def _ensure_json_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    defaults = (
        (ALERTS_FILE, []), (VIP_USERS_FILE, {}), (DAILY_SUBS_FILE, {}),
        (USERS_FILE, {}), (PURCHASES_FILE, []), (HISTORY_FILE, {}),
        (BOT_STATE_FILE, {}),
    )
    for path, default in defaults:
        if not os.path.exists(path):
            _save_json(path, default)


def _load_json(path, default):
    with _data_lock:
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except FileNotFoundError:
            return default
        except (json.JSONDecodeError, OSError):
            logger.exception("Could not read JSON file: %s", path)
            return default


def _save_json(path, data):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    temp_path = f"{path}.tmp"
    with _data_lock:
        with open(temp_path, "w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
        os.replace(temp_path, path)


def init_storage():
    _ensure_json_files()
    data = _load_json(VIP_USERS_FILE, {})
    if isinstance(data, list):
        migrated = {
            str(item): {"expires_at": None, "legacy_lifetime": True, "added_at": _utc_now()}
            for item in data
        }
        _save_json(VIP_USERS_FILE, migrated)
    alerts = load_alerts()
    changed = False
    for alert in alerts:
        if "type" not in alert:
            alert.update({"type": "price", "mode": "once", "armed": True})
            changed = True
    if changed:
        _save_json(ALERTS_FILE, alerts)
    logger.info("Persistent JSON storage path: %s", os.path.abspath(DATA_DIR))


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except (TypeError, ValueError):
        return None


def _is_admin(user_id):
    return bool(ADMIN_ID) and str(user_id) == str(ADMIN_ID)


def register_user(user, chat_id):
    if not user:
        return
    users = _load_json(USERS_FILE, {})
    old = users.get(str(user.id), {}) if isinstance(users, dict) else {}
    users[str(user.id)] = {
        "user_id": user.id, "chat_id": chat_id,
        "username": user.username or "", "first_name": user.first_name or "",
        "joined_at": old.get("joined_at") or _utc_now(), "last_seen": _utc_now(),
    }
    _save_json(USERS_FILE, users)


def load_alerts():
    data = _load_json(ALERTS_FILE, [])
    return data if isinstance(data, list) else []


def create_alert(alert):
    alerts = load_alerts()
    alerts.append(alert)
    _save_json(ALERTS_FILE, alerts)


def delete_user_alerts(user_id):
    wanted = str(user_id)
    alerts = [alert for alert in load_alerts() if str(alert.get("user_id")) != wanted]
    _save_json(ALERTS_FILE, alerts)


def delete_alert_ids(alert_ids):
    if not alert_ids:
        return
    wanted = {str(alert_id) for alert_id in alert_ids}
    alerts = [alert for alert in load_alerts() if str(alert.get("id")) not in wanted]
    _save_json(ALERTS_FILE, alerts)


def delete_one_alert(alert_id, user_id):
    old = load_alerts()
    new = [a for a in old if not (str(a.get("id")) == str(alert_id) and str(a.get("user_id")) == str(user_id))]
    _save_json(ALERTS_FILE, new)
    return len(old) != len(new)


def update_one_alert(alert_id, user_id, changes):
    alerts = load_alerts()
    for alert in alerts:
        if str(alert.get("id")) == str(alert_id) and str(alert.get("user_id")) == str(user_id):
            alert.update(changes)
            _save_json(ALERTS_FILE, alerts)
            return True
    return False


def is_vip(user_id):
    if _is_admin(user_id):
        return True
    entry = _load_json(VIP_USERS_FILE, {}).get(str(user_id))
    if not isinstance(entry, dict):
        return False
    if entry.get("legacy_lifetime") or not entry.get("expires_at"):
        return True
    expiry = _parse_iso(entry.get("expires_at"))
    return bool(expiry and expiry > datetime.now(timezone.utc))


def add_vip_user(user_id, days=30, source="admin"):
    data = _load_json(VIP_USERS_FILE, {})
    now = datetime.now(timezone.utc)
    old = data.get(str(user_id), {})
    old_expiry = _parse_iso(old.get("expires_at")) if isinstance(old, dict) else None
    start = old_expiry if old_expiry and old_expiry > now else now
    data[str(user_id)] = {
        "expires_at": (start + timedelta(days=max(1, int(days)))).isoformat(),
        "plan_days": int(days), "added_at": _utc_now(), "source": source,
        "last_reminder": "",
    }
    _save_json(VIP_USERS_FILE, data)


def remove_vip_user(user_id):
    data = _load_json(VIP_USERS_FILE, {})
    removed = data.pop(str(user_id), None)
    _save_json(VIP_USERS_FILE, data)
    return bool(removed)


def vip_days_left(user_id):
    entry = _load_json(VIP_USERS_FILE, {}).get(str(user_id), {})
    if entry.get("legacy_lifetime") or not entry.get("expires_at"):
        return None
    expiry = _parse_iso(entry.get("expires_at"))
    if not expiry:
        return 0
    return max(0, int(((expiry - datetime.now(timezone.utc)).total_seconds() + 86399) // 86400))


def user_alerts(user_id):
    wanted = str(user_id)
    return [alert for alert in load_alerts() if str(alert.get("user_id")) == wanted]


def get_daily_sub(user_id):
    return _load_json(DAILY_SUBS_FILE, {}).get(str(user_id))


def set_daily_sub(user_id, chat_id, report_time, active=True):
    data = _load_json(DAILY_SUBS_FILE, {})
    old = data.get(str(user_id), {})
    data[str(user_id)] = {"user_id": user_id, "chat_id": chat_id, "time": report_time,
                          "active": active, "last_sent": old.get("last_sent", "")}
    _save_json(DAILY_SUBS_FILE, data)


def make_backup():
    day = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")
    destination = os.path.join(BACKUP_DIR, day)
    os.makedirs(destination, exist_ok=True)
    for path in (ALERTS_FILE, VIP_USERS_FILE, DAILY_SUBS_FILE, USERS_FILE,
                 PURCHASES_FILE, HISTORY_FILE, BOT_STATE_FILE):
        if os.path.isfile(path):
            shutil.copy2(path, os.path.join(destination, os.path.basename(path)))
    state = _load_json(BOT_STATE_FILE, {})
    state["last_backup"] = day
    _save_json(BOT_STATE_FILE, state)
    return destination


def _unwrap_payload(payload):
    """پاسخ‌های مستقیم و پاسخ‌های پیچیده‌شده داخل data/result را پشتیبانی می‌کند."""
    if not isinstance(payload, dict):
        return None

    if any(isinstance(payload.get(key), list) for key in ("gold", "currency", "cryptocurrency")):
        return payload

    for wrapper in ("data", "result"):
        nested = payload.get(wrapper)
        if isinstance(nested, dict) and any(
            isinstance(nested.get(key), list)
            for key in ("gold", "currency", "cryptocurrency")
        ):
            return nested

    return None


def get_market_data(force_refresh=False):
    now = time.monotonic()
    if (
        not force_refresh
        and _market_cache["data"] is not None
        and now - _market_cache["saved_at"] < CACHE_TTL_SECONDS
    ):
        return _market_cache["data"], None

    if not BRS_API_URL:
        logger.error("BRS_API_URL is missing in Railway Variables")
        return None, "تنظیمات اتصال API کامل نیست"

    try:
        response = requests.get(
            BRS_API_URL,
            timeout=API_TIMEOUT,
            headers={"Accept": "application/json", "User-Agent": "TalayarBot/1.1"},
        )
        logger.info(
            "BRS response: status=%s content_type=%s bytes=%s",
            response.status_code,
            response.headers.get("content-type", "unknown"),
            len(response.content),
        )
        response.raise_for_status()

        try:
            raw_payload = response.json()
        except ValueError:
            logger.error("BRS returned invalid JSON: %r", response.text[:300])
            return None, "پاسخ API معتبر نیست"

        payload = _unwrap_payload(raw_payload)
        if payload is None:
            top_keys = list(raw_payload.keys())[:20] if isinstance(raw_payload, dict) else []
            logger.error("Unexpected BRS structure. top_keys=%s", top_keys)
            return None, "ساختار پاسخ API تغییر کرده"

        section_counts = {
            key: len(payload.get(key, [])) if isinstance(payload.get(key), list) else 0
            for key in ("gold", "currency", "cryptocurrency")
        }
        logger.info("BRS sections loaded: %s", section_counts)
        _market_cache["data"] = payload
        _market_cache["saved_at"] = now
        return payload, None

    except requests.Timeout:
        logger.exception("BRS request timed out")
        return None, "زمان پاسخ‌گویی API تمام شد"
    except requests.RequestException as exc:
        status = exc.response.status_code if exc.response is not None else "no-response"
        body = exc.response.text[:300] if exc.response is not None else ""
        logger.error("BRS request failed: status=%s error=%s body=%r", status, exc, body)
        return None, f"خطای اتصال به API (کد {status})"
    except Exception:
        logger.exception("Unexpected market data error")
        return None, "خطای پیش‌بینی‌نشده در دریافت قیمت‌ها"


def find_item(data, symbols, sections=None, name_keywords=None):
    if isinstance(symbols, str):
        symbols = [symbols]
    wanted_symbols = {str(symbol).strip().upper() for symbol in symbols}
    sections = sections or ["gold", "currency", "cryptocurrency"]

    for section in sections:
        items = data.get(section, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            item_symbol = str(item.get("symbol", "")).strip().upper()
            if item_symbol in wanted_symbols:
                return item

    if name_keywords:
        keywords = [keyword.casefold() for keyword in name_keywords]
        for section in sections:
            for item in data.get(section, []):
                if not isinstance(item, dict):
                    continue
                combined_name = f"{item.get('name', '')} {item.get('name_en', '')}".casefold()
                if any(keyword in combined_name for keyword in keywords):
                    return item

    logger.warning("Market symbol not found: symbols=%s sections=%s", sorted(wanted_symbols), sections)
    return None


def find_alert_item(market, asset_key):
    asset = ALERT_ASSETS.get(asset_key)
    if not asset:
        return None
    return find_item(
        market,
        asset["symbols"],
        sections=asset["sections"],
        name_keywords=asset["keywords"],
    )


def _parse_number(text):
    digit_map = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    cleaned = str(text).translate(digit_map)
    for token in (",", "٬", "،", " ", "تومان", "دلار", "%", "درصد"):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.replace("٫", ".")
    try:
        number = float(cleaned)
        return number if number >= 0 else None
    except ValueError:
        return None


def _condition_label(condition):
    return {"above": "بالاتر یا مساوی", "below": "پایین‌تر یا مساوی",
            "up": "افزایش", "down": "کاهش"}.get(condition, "نامشخص")


def _alert_list_payload(user_id):
    alerts = user_alerts(user_id)
    if not alerts:
        return "📋 شما هیچ هشدار فعالی ندارید.", alert_menu()

    lines = ["📋 <b>هشدارهای فعال شما</b>", ""]
    rows = []
    for index, alert in enumerate(alerts, start=1):
        asset = ALERT_ASSETS.get(alert.get("asset"), {})
        label = asset.get("label", alert.get("asset", "دارایی"))
        if alert.get("type") == "percent":
            detail = f"{_condition_label(alert.get('condition'))} {alert.get('percent')}٪"
        else:
            detail = f"{_condition_label(alert.get('condition'))} {_format_number(alert.get('target'))}"
        lines.append(
            f"{index}. {label}\n"
            f"شرط: {detail}\n"
            f"اجرا: {'تکرارشونده' if alert.get('mode') == 'repeat' else 'یک‌باره'}"
        )
        lines.append("")
        rows.append([
            InlineKeyboardButton(f"✏️ ویرایش {index}", callback_data=f"alert_edit:{alert.get('id')}"),
            InlineKeyboardButton(f"🗑 حذف {index}", callback_data=f"alert_del:{alert.get('id')}"),
        ])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="alerts")])
    return "\n".join(lines).rstrip(), InlineKeyboardMarkup(rows)


def _format_number(value):
    try:
        number = float(str(value).replace(",", ""))
        if number.is_integer():
            return f"{int(number):,}"
        return f"{number:,.2f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value or "نامشخص")


def show_item(item, fallback_name):
    if not item:
        return f"{fallback_name}: اطلاعات موجود نیست\n\n"

    name = item.get("name") or item.get("name_en") or fallback_name
    price = _format_number(item.get("price"))
    unit = item.get("unit") or ""
    change = _format_number(item.get("change_percent", 0))
    return f"{name}:\n{price} {unit}\nتغییر: {change}%\n\n"


def build_gold_text(market):
    items = [
        ("طلای ۱۸ عیار", ["IR_GOLD_18K"], ["طلای 18", "18K Gold"]),
        ("طلای ۲۴ عیار", ["IR_GOLD_24K"], ["طلای 24", "24K Gold"]),
        ("سکه امامی", ["IR_COIN_EMAMI", "IR_COIN_FULL"], ["سکه امامی", "Emami"]),
        ("نیم‌سکه", ["IR_COIN_HALF"], ["نیم سکه", "Half Coin"]),
        ("ربع‌سکه", ["IR_COIN_QUARTER"], ["ربع سکه", "Quarter Coin"]),
    ]
    text = "🪙 <b>طلا و سکه</b>\n\n"
    for label, symbols, keywords in items:
        item = find_item(market, symbols, sections=["gold"], name_keywords=keywords)
        text += show_item(item, label)
    return text


def build_currency_text(market):
    items = [
        ("دلار آمریکا", ["USD", "IR_USD", "USD_IRR", "USD_IRT"], ["دلار آمریکا", "US Dollar"]),
        ("یورو", ["EUR", "IR_EUR", "EUR_IRR", "EUR_IRT"], ["یورو", "Euro"]),
        ("تتر", ["USDT_IRT", "IR_USDT", "USDTIRT"], ["تتر تومان", "Tether Toman"]),
    ]
    text = "💵 <b>بازار ارز</b>\n\n"
    for label, symbols, keywords in items:
        item = find_item(
            market,
            symbols,
            sections=["currency", "cryptocurrency"],
            name_keywords=keywords,
        )
        text += show_item(item, label)
    return text


def _item_price(item):
    try:
        return float(str(item.get("price")).replace(",", ""))
    except (AttributeError, TypeError, ValueError):
        return None


def build_daily_report(market):
    text = f"🗓 <b>گزارش روزانه طلایار</b>\n🕒 {datetime.now(TEHRAN_TZ):%Y/%m/%d - %H:%M}\n\n"
    for key in ("usd", "gold18", "emami", "half", "quarter", "ounce", "btc"):
        item = find_alert_item(market, key)
        if item:
            text += f"• {ALERT_ASSETS[key]['label']}: <b>{_format_number(item.get('price'))}</b> {item.get('unit') or ''}\n"
    return text + f"\n<i>{DISCLAIMER}</i>"


def capture_history(market):
    state = _load_json(BOT_STATE_FILE, {})
    now = int(time.time())
    if now - int(state.get("last_history", 0)) < HISTORY_SAVE_INTERVAL:
        return
    history = _load_json(HISTORY_FILE, {})
    cutoff = now - 7 * 86400
    for key in ALERT_ASSETS:
        item = find_alert_item(market, key)
        price = _item_price(item)
        if price is None:
            continue
        points = history.get(key, [])
        points.append({"ts": now, "price": price, "unit": item.get("unit") or ""})
        history[key] = [point for point in points if int(point.get("ts", 0)) >= cutoff][-2200:]
    _save_json(HISTORY_FILE, history)
    state["last_history"] = now
    _save_json(BOT_STATE_FILE, state)


def _sparkline(values, size=30):
    if len(values) > size:
        values = [values[round(i * (len(values) - 1) / (size - 1))] for i in range(size)]
    bars = "▁▂▃▄▅▆▇█"
    low, high = min(values), max(values)
    if low == high:
        return bars[3] * len(values)
    return "".join(bars[min(7, int((value - low) / (high - low) * 7))] for value in values)


def chart_text(asset, hours):
    history = _load_json(HISTORY_FILE, {})
    cutoff = int(time.time()) - hours * 3600
    points = [p for p in history.get(asset, []) if int(p.get("ts", 0)) >= cutoff]
    if len(points) < 2:
        return "📈 هنوز داده کافی برای نمودار جمع نشده؛ طلایار هر پنج دقیقه یک نمونه ذخیره می‌کند."
    values = [float(p["price"]) for p in points]
    change = (values[-1] - values[0]) / values[0] * 100 if values[0] else 0
    return (f"📈 <b>{ALERT_ASSETS[asset]['label']} — {'۲۴ ساعت' if hours == 24 else '۷ روز'}</b>\n\n"
            f"<code>{_sparkline(values)}</code>\n\nشروع: {_format_number(values[0])}\n"
            f"فعلی: <b>{_format_number(values[-1])}</b>\nکمترین: {_format_number(min(values))}\n"
            f"بیشترین: {_format_number(max(values))}\nتغییر: {change:+.2f}%")


def account_text(user_id):
    sub = get_daily_sub(user_id)
    daily = f"فعال در {sub.get('time')}" if sub and sub.get("active") else "غیرفعال"
    days = vip_days_left(user_id) if is_vip(user_id) else None
    remain = "" if not is_vip(user_id) else f"\nزمان VIP: {'بدون انقضا' if days is None else str(days) + ' روز'}"
    return (f"👤 <b>حساب کاربری</b>\n\nشناسه: <code>{user_id}</code>\n"
            f"نوع حساب: {'VIP ⭐' if is_vip(user_id) else 'رایگان'}{remain}\n"
            f"هشدار فعال: {len(user_alerts(user_id))}\nگزارش روزانه: {daily}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("alert_draft", None)
    await update.message.reply_text("🟡 <b>طلایار</b>\n\nدستیار هوشمند رصد قیمت طلا، ارز و بازارهای مالی", reply_markup=main_menu(), parse_mode="HTML")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.pop("alert_draft", None)
    await update.message.reply_text("ساخت هشدار لغو شد.", reply_markup=alert_menu())


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"شناسه کاربری شما: <code>{update.effective_user.id}</code>", parse_mode="HTML")


async def vip_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        vip_text(update.effective_user.id),
        reply_markup=vip_menu(),
        parse_mode="HTML",
    )


async def add_vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not ADMIN_ID or str(update.effective_user.id) != str(ADMIN_ID):
        await update.message.reply_text("این دستور فقط برای مدیر ربات است.")
        return

    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("فرمت صحیح:\n/addvip CHAT_ID")
        return

    vip_user_id = int(context.args[0])
    add_vip_user(vip_user_id)
    await update.message.reply_text(f"✅ کاربر {vip_user_id} به VIP اضافه شد.")


async def receive_alert_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    draft = context.user_data.get("alert_draft")
    if not draft or draft.get("step") != "price":
        return

    target = _parse_number(update.message.text)
    if target is None:
        await update.message.reply_text(
            "قیمت معتبر نیست. فقط عدد بفرست؛ مثلاً:\n<code>200000</code>",
            parse_mode="HTML",
        )
        return

    user_id = update.effective_user.id
    current_user_alerts = user_alerts(user_id)
    if not is_vip(user_id) and len(current_user_alerts) >= FREE_ALERT_LIMIT:
        context.user_data.pop("alert_draft", None)
        await update.message.reply_text(
            "⚠️ کاربران رایگان فقط یک هشدار فعال می‌توانند داشته باشند.\n"
            "ابتدا هشدار قبلی را حذف کن یا عضویت VIP بگیر.",
            reply_markup=alert_menu(),
        )
        return

    alert = {
        "id": uuid.uuid4().hex[:12],
        "chat_id": update.effective_chat.id,
        "user_id": user_id,
        "asset": draft["asset"],
        "condition": draft["condition"],
        "target": target,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    create_alert(alert)
    context.user_data.pop("alert_draft", None)

    asset_label = ALERT_ASSETS[alert["asset"]]["label"]
    await update.message.reply_text(
        "✅ <b>هشدار ذخیره شد</b>\n\n"
        f"دارایی: {asset_label}\n"
        f"شرط: {_condition_label(alert['condition'])}\n"
        f"قیمت هدف: {_format_number(target)}",
        reply_markup=alert_menu(),
        parse_mode="HTML",
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "prices":
        await q.edit_message_text("📊 بازار را انتخاب کنید:", reply_markup=price_menu())
        return

    if data == "home":
        context.user_data.pop("alert_draft", None)
        await q.edit_message_text("🟡 منوی اصلی", reply_markup=main_menu())
        return

    if data == "alerts":
        context.user_data.pop("alert_draft", None)
        await q.edit_message_text(
            "🔔 <b>هشدار قیمت</b>\n\n"
            "وقتی قیمت به عدد موردنظر برسد، طلایار به شما پیام می‌دهد.",
            reply_markup=alert_menu(),
            parse_mode="HTML",
        )
        return

    if data == "alert_new":
        user_id = q.from_user.id
        if not is_vip(user_id) and len(user_alerts(user_id)) >= FREE_ALERT_LIMIT:
            await q.edit_message_text(
                "⚠️ شما یک هشدار فعال دارید.\n\n"
                "کاربر رایگان حداکثر یک هشدار فعال دارد. ابتدا هشدار قبلی را حذف کن.",
                reply_markup=alert_menu(),
            )
            return
        context.user_data["alert_draft"] = {"step": "asset"}
        await q.edit_message_text("دارایی موردنظر را انتخاب کن:", reply_markup=alert_asset_menu())
        return

    if data.startswith("alert_asset:"):
        asset_key = data.split(":", 1)[1]
        if asset_key not in ALERT_ASSETS:
            await q.edit_message_text("دارایی نامعتبر است.", reply_markup=alert_asset_menu())
            return
        context.user_data["alert_draft"] = {"step": "condition", "asset": asset_key}
        await q.edit_message_text(
            f"دارایی: {ALERT_ASSETS[asset_key]['label']}\n\nچه زمانی هشدار بدهم؟",
            reply_markup=alert_condition_menu(),
        )
        return

    if data.startswith("alert_condition:"):
        condition = data.split(":", 1)[1]
        draft = context.user_data.get("alert_draft")
        if condition not in {"above", "below"} or not draft or not draft.get("asset"):
            await q.edit_message_text("ساخت هشدار از ابتدا شروع شد.", reply_markup=alert_asset_menu())
            context.user_data["alert_draft"] = {"step": "asset"}
            return
        draft["condition"] = condition
        draft["step"] = "price"
        await q.edit_message_text(
            f"قیمت هدف برای {ALERT_ASSETS[draft['asset']]['label']} را فقط به‌صورت عدد بفرست.\n\n"
            "مثال: <code>200000</code>\n"
            "برای لغو: /cancel",
            parse_mode="HTML",
        )
        return

    if data == "alert_list":
        await q.edit_message_text(
            _alert_list_text(q.from_user.id),
            reply_markup=alert_menu(),
            parse_mode="HTML",
        )
        return

    if data == "alert_delete":
        if not user_alerts(q.from_user.id):
            await q.edit_message_text("هشدار فعالی برای حذف نداری.", reply_markup=alert_menu())
            return
        await q.edit_message_text(
            "همه هشدارهای فعال شما حذف شوند؟",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ بله، حذف کن", callback_data="alert_delete_confirm")],
                [InlineKeyboardButton("❌ انصراف", callback_data="alerts")],
            ]),
        )
        return

    if data == "alert_delete_confirm":
        delete_user_alerts(q.from_user.id)
        context.user_data.pop("alert_draft", None)
        await q.edit_message_text("✅ همه هشدارهای شما حذف شدند.", reply_markup=alert_menu())
        return

    if data == "account":
        user_id = q.from_user.id
        status = "VIP ⭐" if is_vip(user_id) else "رایگان"
        count = len(user_alerts(user_id))
        await q.edit_message_text(
            "👤 <b>حساب کاربری</b>\n\n"
            f"شناسه: <code>{user_id}</code>\n"
            f"نوع حساب: {status}\n"
            f"هشدار فعال: {count}",
            reply_markup=main_menu(),
            parse_mode="HTML",
        )
        return

    if data == "vip":
        await q.edit_message_text(
            vip_text(q.from_user.id),
            reply_markup=vip_menu(),
            parse_mode="HTML",
        )
        return

    if data == "help":
        await q.edit_message_text(
            "ℹ️ <b>راهنما</b>\n\n"
            "از «قیمت لحظه‌ای» بازار را ببین.\n"
            "از «هشدار قیمت» دارایی، شرط و قیمت هدف را انتخاب کن.",
            reply_markup=main_menu(),
            parse_mode="HTML",
        )
        return

    if data not in {"gold", "iran_currency", "ounce", "crypto"}:
        logger.warning("Unknown callback data: %s", data)
        await q.edit_message_text("گزینه نامعتبر است.", reply_markup=main_menu())
        return

    market, error = get_market_data()
    if market is None:
        await q.edit_message_text(
            f"❌ {error}\n\nلطفاً چند لحظه بعد دوباره امتحان کنید.",
            reply_markup=price_menu(),
        )
        return

    if data == "gold":
        text = build_gold_text(market)
    elif data == "iran_currency":
        text = build_currency_text(market)
    elif data == "ounce":
        text = "🌎 <b>انس جهانی</b>\n\n" + show_item(
            find_item(market, ["XAUUSD", "XAU_USD"], sections=["gold"], name_keywords=["انس جهانی", "Gold Ounce"]),
            "انس جهانی طلا",
        )
    else:
        text = "₿ <b>ارز دیجیتال</b>\n\n"
        text += show_item(find_item(market, ["BTC", "BTCUSDT"], sections=["cryptocurrency"], name_keywords=["Bitcoin", "بیت کوین"]), "بیت‌کوین")
        text += show_item(find_item(market, ["ETH", "ETHUSDT"], sections=["cryptocurrency"], name_keywords=["Ethereum", "اتریوم"]), "اتریوم")
        text += show_item(find_item(market, ["USDT", "USDTUSD"], sections=["cryptocurrency"], name_keywords=["Tether", "تتر"]), "تتر")

    await q.edit_message_text(text, reply_markup=price_menu(), parse_mode="HTML")


async def check_price_alerts(context: ContextTypes.DEFAULT_TYPE):
    alerts = load_alerts()
    if not alerts:
        return

    market, error = get_market_data(force_refresh=True)
    if market is None:
        logger.warning("Alert check skipped: %s", error)
        return

    triggered_ids = []
    for alert in alerts:
        asset_key = alert.get("asset")
        item = find_alert_item(market, asset_key)
        if not item:
            continue

        try:
            current_price = float(str(item.get("price")).replace(",", ""))
            target = float(alert.get("target"))
        except (TypeError, ValueError):
            logger.warning("Invalid alert data: id=%s", alert.get("id"))
            continue

        condition = alert.get("condition")
        triggered = (
            (condition == "above" and current_price >= target)
            or (condition == "below" and current_price <= target)
        )
        if not triggered:
            continue

        asset_label = ALERT_ASSETS.get(asset_key, {}).get("label", "دارایی")
        unit = item.get("unit") or ""
        try:
            await context.bot.send_message(
                chat_id=alert["chat_id"],
                text=(
                    "🔔 <b>هشدار قیمت طلایار</b>\n\n"
                    f"{asset_label} به قیمت هدف شما رسید.\n"
                    f"قیمت فعلی: <b>{_format_number(current_price)} {unit}</b>\n"
                    f"هدف شما: {_format_number(target)} {unit}"
                ),
                parse_mode="HTML",
                reply_markup=main_menu(),
            )
            triggered_ids.append(alert.get("id"))
            logger.info("Alert triggered: id=%s user_id=%s", alert.get("id"), alert.get("user_id"))
        except Exception:
            logger.exception("Could not send alert: id=%s", alert.get("id"))

    delete_alert_ids(triggered_ids)


def clear_flow(context):
    for key in ("flow", "alert_draft", "alert_edit_id", "purchase_plan", "calc_weight"):
        context.user_data.pop(key, None)


async def start_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_flow(context)
    register_user(update.effective_user, update.effective_chat.id)
    await update.message.reply_text(
        "🟡 <b>طلایار</b>\n\nدستیار قیمت طلا، ارز و بازارهای مالی\n"
        "قیمت لحظه‌ای، هشدار هوشمند، گزارش روزانه، نمودار و ماشین‌حساب",
        reply_markup=main_menu(), parse_mode="HTML")


async def cancel_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_flow(context)
    await update.message.reply_text("عملیات لغو شد.", reply_markup=main_menu())


async def admin_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("این بخش فقط برای مدیر ربات است.")
        return
    clear_flow(context)
    await update.message.reply_text("🛠 پنل مدیریت طلایار", reply_markup=admin_menu())


async def vip_command_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await update.message.reply_text(vip_text(user_id), reply_markup=vip_menu(user_id), parse_mode="HTML")


async def add_vip_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("فرمت: /addvip USER_ID DAYS\nمثال: /addvip 123456 30")
        return
    user_id = int(context.args[0])
    days = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 30
    add_vip_user(user_id, days)
    await update.message.reply_text(f"✅ کاربر {user_id} برای {days} روز VIP شد.")
    try:
        await context.bot.send_message(user_id, f"⭐ اشتراک VIP شما برای {days} روز فعال شد.", reply_markup=main_menu())
    except Exception:
        logger.exception("VIP notification failed")


async def remove_vip_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("فرمت: /removevip USER_ID")
        return
    await update.message.reply_text("✅ حذف شد." if remove_vip_user(context.args[0]) else "کاربر VIP نبود.")


async def userinfo_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("فرمت: /userinfo USER_ID")
        return
    user_id = context.args[0]
    user = _load_json(USERS_FILE, {}).get(str(user_id), {})
    await update.message.reply_text(
        f"👤 نام: {html.escape(user.get('first_name') or 'نامشخص')}\n"
        f"یوزرنیم: @{html.escape(user.get('username') or 'ندارد')}\nشناسه: <code>{user_id}</code>\n"
        f"VIP: {'بله' if is_vip(user_id) else 'خیر'}\nهشدار: {len(user_alerts(user_id))}", parse_mode="HTML")


async def receive_text_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    register_user(update.effective_user, update.effective_chat.id)
    flow = context.user_data.get("flow")
    text = update.message.text.strip()
    value = _parse_number(text) if flow in {"alert_value", "alert_edit", "calc_weight", "calc_fee"} else None

    if flow == "alert_value":
        draft = context.user_data.get("alert_draft", {})
        if value is None or value <= 0:
            await update.message.reply_text("عدد معتبر بفرست؛ برای لغو /cancel")
            return
        if not is_vip(update.effective_user.id) and len(user_alerts(update.effective_user.id)) >= FREE_ALERT_LIMIT:
            clear_flow(context)
            await update.message.reply_text("سقف یک هشدار رایگان پر شده است.", reply_markup=alert_menu())
            return
        alert = {"id": uuid.uuid4().hex[:12], "chat_id": update.effective_chat.id,
                 "user_id": update.effective_user.id, "type": draft.get("type", "price"),
                 "asset": draft.get("asset"), "condition": draft.get("condition"),
                 "mode": draft.get("mode", "once"), "armed": True, "created_at": _utc_now()}
        if alert["type"] == "percent":
            market, error = get_market_data()
            baseline = _item_price(find_alert_item(market, alert["asset"])) if market else None
            if baseline is None:
                await update.message.reply_text(f"قیمت مبنا دریافت نشد: {error or 'ناموجود'}")
                return
            alert.update({"percent": value, "baseline": baseline})
            detail = f"{_condition_label(alert['condition'])} {value}٪"
        else:
            alert["target"] = value
            detail = f"{_condition_label(alert['condition'])} {_format_number(value)}"
        create_alert(alert)
        clear_flow(context)
        await update.message.reply_text(
            f"✅ هشدار ذخیره شد\n\nدارایی: {ALERT_ASSETS[alert['asset']]['label']}\n"
            f"شرط: {detail}\nاجرا: {'تکرارشونده' if alert['mode'] == 'repeat' else 'یک‌باره'}",
            reply_markup=alert_menu())
        return

    if flow == "alert_edit":
        if value is None or value <= 0:
            await update.message.reply_text("عدد معتبر بفرست؛ برای لغو /cancel")
            return
        alert_id = context.user_data.get("alert_edit_id")
        alert = next((a for a in user_alerts(update.effective_user.id) if str(a.get("id")) == str(alert_id)), None)
        if not alert:
            clear_flow(context)
            await update.message.reply_text("هشدار پیدا نشد.", reply_markup=alert_menu())
            return
        changes = {"armed": True, "updated_at": _utc_now()}
        if alert.get("type") == "percent":
            changes["percent"] = value
            market, _ = get_market_data()
            baseline = _item_price(find_alert_item(market, alert["asset"])) if market else None
            if baseline is not None:
                changes["baseline"] = baseline
        else:
            changes["target"] = value
        update_one_alert(alert_id, update.effective_user.id, changes)
        clear_flow(context)
        await update.message.reply_text("✅ هشدار ویرایش شد.", reply_markup=alert_menu())
        return

    if flow == "daily_time":
        normalized = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", normalized):
            await update.message.reply_text("ساعت را مثل 09:30 بفرست؛ برای لغو /cancel")
            return
        set_daily_sub(update.effective_user.id, update.effective_chat.id, normalized)
        clear_flow(context)
        await update.message.reply_text(f"✅ گزارش روزانه ساعت {normalized} فعال شد.", reply_markup=main_menu())
        return

    if flow == "calc_weight":
        if value is None or value <= 0:
            await update.message.reply_text("وزن معتبر به گرم بفرست؛ مثال 2.5")
            return
        context.user_data["calc_weight"] = value
        context.user_data["flow"] = "calc_fee"
        await update.message.reply_text("درصد اجرت را بفرست؛ برای بدون اجرت عدد 0")
        return

    if flow == "calc_fee":
        if value is None or value < 0 or value > 100:
            await update.message.reply_text("درصد اجرت باید بین 0 تا 100 باشد.")
            return
        weight = context.user_data.get("calc_weight")
        market, error = get_market_data()
        price = _item_price(find_alert_item(market, "gold18")) if market else None
        if price is None:
            clear_flow(context)
            await update.message.reply_text(f"محاسبه نشد: {error or 'قیمت طلا ناموجود'}", reply_markup=main_menu())
            return
        raw = weight * price
        fee = raw * value / 100
        clear_flow(context)
        await update.message.reply_text(
            f"🧮 <b>محاسبه تقریبی طلا</b>\n\nوزن: {_format_number(weight)} گرم\n"
            f"ارزش خام: {_format_number(raw)} تومان\nاجرت: {_format_number(fee)} تومان\n"
            f"جمع: <b>{_format_number(raw + fee)} تومان</b>\n\n"
            "<i>مالیات و سود فروشنده محاسبه نشده است.</i>", reply_markup=main_menu(), parse_mode="HTML")
        return

    if flow == "broadcast" and _is_admin(update.effective_user.id):
        users = _load_json(USERS_FILE, {})
        clear_flow(context)
        sent = failed = 0
        status = await update.message.reply_text("در حال ارسال…")
        for user in users.values():
            try:
                await context.bot.send_message(user.get("chat_id") or user.get("user_id"), text, reply_markup=main_menu())
                sent += 1
            except Exception:
                failed += 1
        await status.edit_text(f"✅ تمام شد. موفق: {sent} | ناموفق: {failed}", reply_markup=admin_menu())
        return

    await update.message.reply_text("یکی از دکمه‌های منو را انتخاب کن.", reply_markup=main_menu())


async def receive_photo_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("flow") != "receipt":
        await update.message.reply_text("ابتدا از بخش VIP یک بسته انتخاب کن.", reply_markup=main_menu())
        return
    plan = int(context.user_data.get("purchase_plan", 30))
    request_id = uuid.uuid4().hex[:10]
    file_id = update.message.photo[-1].file_id
    request = {"id": request_id, "user_id": update.effective_user.id,
               "chat_id": update.effective_chat.id, "username": update.effective_user.username or "",
               "plan": plan, "file_id": file_id, "status": "pending", "created_at": _utc_now()}
    purchases = _load_json(PURCHASES_FILE, [])
    purchases.append(request)
    _save_json(PURCHASES_FILE, purchases)
    clear_flow(context)
    await update.message.reply_text("✅ رسید برای ادمین ارسال شد.", reply_markup=main_menu())
    if str(ADMIN_ID).isdigit():
        await context.bot.send_photo(
            int(ADMIN_ID), file_id,
            caption=f"🧾 خرید VIP\nکاربر: {request['user_id']}\n@{request['username'] or 'ندارد'}\nبسته: {plan} روز\nکد: {request_id}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تأیید", callback_data=f"purchase_ok:{request_id}"),
                InlineKeyboardButton("❌ رد", callback_data=f"purchase_no:{request_id}"),
            ]]))


async def buttons_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id, data = q.from_user.id, q.data
    register_user(q.from_user, q.message.chat.id)

    if data == "home":
        clear_flow(context)
        await q.edit_message_text("🟡 منوی اصلی طلایار", reply_markup=main_menu())
        return
    if data == "prices":
        await q.edit_message_text("📊 بازار را انتخاب کن:", reply_markup=price_menu())
        return
    if data in {"gold", "iran_currency", "ounce", "crypto"}:
        market, error = get_market_data()
        if market is None:
            await q.edit_message_text(f"❌ {error}", reply_markup=price_menu())
            return
        if data == "gold": text = build_gold_text(market)
        elif data == "iran_currency": text = build_currency_text(market)
        elif data == "ounce": text = "🌎 <b>انس جهانی</b>\n\n" + show_item(find_alert_item(market, "ounce"), "انس جهانی")
        else:
            text = "₿ <b>ارز دیجیتال</b>\n\n"
            for symbols, label, words in ((["BTC", "BTCUSDT"], "بیت‌کوین", ["Bitcoin"]),
                                          (["ETH", "ETHUSDT"], "اتریوم", ["Ethereum"]),
                                          (["USDT", "USDTUSD"], "تتر", ["Tether"])):
                text += show_item(find_item(market, symbols, ["cryptocurrency"], words), label)
        await q.edit_message_text(text + f"\n<i>{DISCLAIMER}</i>", reply_markup=price_menu(), parse_mode="HTML")
        return

    if data == "alerts":
        clear_flow(context)
        await q.edit_message_text("🔔 هشدار عددی، درصدی و تکرارشونده", reply_markup=alert_menu())
        return
    if data == "alert_new":
        if not is_vip(user_id) and len(user_alerts(user_id)) >= FREE_ALERT_LIMIT:
            await q.edit_message_text("سقف یک هشدار رایگان پر شده است.", reply_markup=alert_menu())
            return
        context.user_data["alert_draft"] = {}
        await q.edit_message_text("نوع هشدار را انتخاب کن:", reply_markup=alert_kind_menu(user_id))
        return
    if data.startswith("alert_kind:"):
        kind = data.split(":", 1)[1]
        if kind == "percent" and not is_vip(user_id):
            await q.edit_message_text("هشدار درصدی مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        context.user_data["alert_draft"] = {"type": kind}
        await q.edit_message_text("دارایی را انتخاب کن:", reply_markup=alert_asset_menu())
        return
    if data.startswith("alert_asset:"):
        asset = data.split(":", 1)[1]
        draft = context.user_data.get("alert_draft", {})
        draft["asset"] = asset
        await q.edit_message_text("شرط هشدار را انتخاب کن:",
                                  reply_markup=percent_condition_menu() if draft.get("type") == "percent" else alert_condition_menu())
        return
    if data.startswith("alert_condition:"):
        draft = context.user_data.get("alert_draft", {})
        draft["condition"] = data.split(":", 1)[1]
        await q.edit_message_text("نوع اجرا را انتخاب کن:", reply_markup=alert_mode_menu())
        return
    if data.startswith("alert_mode:"):
        mode = data.split(":", 1)[1]
        if mode == "repeat" and not is_vip(user_id):
            await q.edit_message_text("تکرارشونده مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        context.user_data["alert_draft"]["mode"] = mode
        context.user_data["flow"] = "alert_value"
        prompt = "درصد هدف را بفرست؛ مثال 2.5" if context.user_data["alert_draft"].get("type") == "percent" else "قیمت هدف را فقط به‌صورت عدد بفرست."
        await q.edit_message_text(prompt + "\nبرای لغو /cancel")
        return
    if data == "alert_list":
        text, markup = _alert_list_payload(user_id)
        await q.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
        return
    if data.startswith("alert_del:"):
        delete_one_alert(data.split(":", 1)[1], user_id)
        text, markup = _alert_list_payload(user_id)
        await q.edit_message_text("✅ حذف شد.\n\n" + text, reply_markup=markup, parse_mode="HTML")
        return
    if data.startswith("alert_edit:"):
        context.user_data["flow"] = "alert_edit"
        context.user_data["alert_edit_id"] = data.split(":", 1)[1]
        await q.edit_message_text("هدف جدید را فقط به‌صورت عدد بفرست. برای لغو /cancel")
        return
    if data == "alert_delete":
        await q.edit_message_text("همه هشدارها حذف شوند؟", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ بله", callback_data="alert_delete_confirm")],
            [InlineKeyboardButton("❌ خیر", callback_data="alerts")]]))
        return
    if data == "alert_delete_confirm":
        delete_user_alerts(user_id)
        await q.edit_message_text("✅ همه هشدارها حذف شدند.", reply_markup=alert_menu())
        return

    if data == "daily":
        if not is_vip(user_id):
            await q.edit_message_text("گزارش روزانه مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        sub = get_daily_sub(user_id)
        status = f"فعال در {sub.get('time')}" if sub and sub.get("active") else "غیرفعال"
        await q.edit_message_text(f"🗓 گزارش روزانه\nوضعیت: {status}\nساعت را انتخاب کن:", reply_markup=daily_menu(bool(sub and sub.get("active"))))
        return
    if data.startswith("daily_set:"):
        report_time = data.split(":", 1)[1]
        set_daily_sub(user_id, q.message.chat.id, report_time)
        await q.edit_message_text(f"✅ گزارش ساعت {report_time} فعال شد.", reply_markup=daily_menu(True))
        return
    if data == "daily_custom":
        context.user_data["flow"] = "daily_time"
        await q.edit_message_text("ساعت را به وقت ایران مثل 09:30 بفرست. برای لغو /cancel")
        return
    if data == "daily_stop":
        sub = get_daily_sub(user_id)
        if sub: set_daily_sub(user_id, q.message.chat.id, sub.get("time", "09:00"), False)
        await q.edit_message_text("⛔ گزارش متوقف شد.", reply_markup=daily_menu(False))
        return

    if data == "charts":
        await q.edit_message_text("📈 دارایی را انتخاب کن:", reply_markup=chart_menu())
        return
    if data.startswith("chart_asset:"):
        asset = data.split(":", 1)[1]
        await q.edit_message_text("بازه نمودار را انتخاب کن:", reply_markup=chart_period_menu(asset))
        return
    if data.startswith("chart:"):
        _, asset, hours = data.split(":")
        if hours == "168" and not is_vip(user_id):
            await q.edit_message_text("نمودار هفتگی مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        await q.edit_message_text(chart_text(asset, int(hours)), reply_markup=chart_period_menu(asset), parse_mode="HTML")
        return
    if data == "calculator":
        clear_flow(context); context.user_data["flow"] = "calc_weight"
        await q.edit_message_text("وزن طلای ۱۸ عیار را به گرم بفرست؛ مثال 2.5\nبرای لغو /cancel")
        return
    if data == "account":
        await q.edit_message_text(account_text(user_id), reply_markup=main_menu(), parse_mode="HTML")
        return
    if data == "vip":
        await q.edit_message_text(vip_text(user_id), reply_markup=vip_menu(user_id), parse_mode="HTML")
        return
    if data.startswith("buy:"):
        plan = int(data.split(":", 1)[1]); price = VIP_PRICE_30 if plan == 30 else VIP_PRICE_90
        await q.edit_message_text(
            f"🧾 بسته {plan} روزه — {price} تومان\n\n{html.escape(PAYMENT_INFO)}\n\nبعد از پرداخت، رسید را ارسال کن.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📷 ارسال رسید", callback_data=f"receipt:{plan}")],
                [InlineKeyboardButton("💬 ادمین", url=f"https://t.me/{ADMIN_USERNAME}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="vip")]]), parse_mode="HTML")
        return
    if data.startswith("receipt:"):
        context.user_data.update({"flow": "receipt", "purchase_plan": int(data.split(":", 1)[1])})
        await q.edit_message_text("📷 حالا تصویر رسید را بفرست. برای لغو /cancel")
        return

    if data == "help":
        await q.edit_message_text(
            "ℹ️ <b>راهنمای طلایار</b>\n\nقیمت لحظه‌ای، هشدار عددی و درصدی، گزارش روزانه، "
            "نمودار و ماشین‌حساب از منوی اصلی در دسترس‌اند.\nبرای لغو ورود اطلاعات /cancel را بفرست.\n\n"
            f"🔒 فقط شناسه تلگرام و تنظیمات لازم ذخیره می‌شود.\n⚠️ {DISCLAIMER}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⭐ مقایسه رایگان و VIP", callback_data="plans")],
                [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{ADMIN_USERNAME}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]]), parse_mode="HTML")
        return
    if data == "plans":
        await q.edit_message_text(
            "رایگان: قیمت‌ها، ماشین‌حساب، نمودار ۲۴ساعته و یک هشدار عددی.\n\n"
            "VIP: هشدار نامحدود/درصدی/تکراری، گزارش روزانه و نمودار هفتگی.",
            reply_markup=vip_menu(user_id))
        return

    if data.startswith("purchase_ok:") or data.startswith("purchase_no:"):
        if not _is_admin(user_id): return
        request_id = data.split(":", 1)[1]
        purchases = _load_json(PURCHASES_FILE, [])
        request = next((p for p in purchases if p.get("id") == request_id), None)
        if not request or request.get("status") != "pending":
            await q.answer("قبلاً بررسی شده", show_alert=True); return
        approved = data.startswith("purchase_ok:")
        request["status"] = "approved" if approved else "rejected"
        request["reviewed_at"] = _utc_now()
        if approved: add_vip_user(request["user_id"], request["plan"], f"purchase:{request_id}")
        _save_json(PURCHASES_FILE, purchases)
        result = "✅ تأیید و فعال شد" if approved else "❌ رد شد"
        await q.edit_message_caption((q.message.caption or "") + "\n\n" + result)
        await context.bot.send_message(request["chat_id"],
            f"⭐ اشتراک {request['plan']} روزه فعال شد." if approved else f"پرداخت تأیید نشد؛ به @{ADMIN_USERNAME} پیام بده.",
            reply_markup=main_menu())
        return

    if data.startswith("admin:"):
        if not _is_admin(user_id): return
        action = data.split(":", 1)[1]
        if action == "stats":
            users = _load_json(USERS_FILE, {}); registry = _load_json(VIP_USERS_FILE, {})
            subs = _load_json(DAILY_SUBS_FILE, {}); purchases = _load_json(PURCHASES_FILE, [])
            text = (f"📊 آمار\n\nکاربران: {len(users)}\nVIP فعال: {sum(is_vip(i) for i in registry)}\n"
                    f"هشدارها: {len(load_alerts())}\nگزارش فعال: {sum(bool(s.get('active')) for s in subs.values())}\n"
                    f"خرید منتظر: {sum(p.get('status') == 'pending' for p in purchases)}")
            await q.edit_message_text(text, reply_markup=admin_menu())
        elif action == "pending":
            pending = [p for p in _load_json(PURCHASES_FILE, []) if p.get("status") == "pending"]
            await q.edit_message_text("🧾 درخواست‌های منتظر: " + str(len(pending)) +
                                      ("\n" + "\n".join(f"{p['id']} | {p['user_id']} | {p['plan']} روز" for p in pending[-20:]) if pending else ""),
                                      reply_markup=admin_menu())
        elif action == "broadcast":
            context.user_data["flow"] = "broadcast"
            await q.edit_message_text("متن پیام همگانی را بفرست. برای لغو /cancel")
        elif action == "backup":
            path = make_backup(); await q.edit_message_text(f"✅ پشتیبان ساخته شد: {os.path.basename(path)}", reply_markup=admin_menu())
        return

    await q.edit_message_text("گزینه نامعتبر است.", reply_markup=main_menu())


async def market_job(context: ContextTypes.DEFAULT_TYPE):
    market, error = get_market_data(force_refresh=True)
    if market is None:
        logger.warning("Market job skipped: %s", error); return
    capture_history(market)
    alerts, remaining, changed = load_alerts(), [], False
    for alert in alerts:
        item = find_alert_item(market, alert.get("asset")); current = _item_price(item)
        if current is None: remaining.append(alert); continue
        try:
            if alert.get("type") == "percent":
                baseline, target = float(alert.get("baseline")), float(alert.get("percent"))
                change = (current - baseline) / baseline * 100 if baseline else 0
                triggered = (alert.get("condition") == "up" and change >= target) or (alert.get("condition") == "down" and change <= -target)
                detail = f"تغییر: {change:+.2f}%"
            else:
                target = float(alert.get("target"))
                triggered = (alert.get("condition") == "above" and current >= target) or (alert.get("condition") == "below" and current <= target)
                detail = f"هدف: {_format_number(target)}"
        except (TypeError, ValueError):
            remaining.append(alert); continue
        if not triggered:
            if alert.get("mode") == "repeat" and not alert.get("armed", True): alert["armed"] = True; changed = True
            remaining.append(alert); continue
        if alert.get("mode") == "repeat" and not alert.get("armed", True): remaining.append(alert); continue
        try:
            await context.bot.send_message(alert["chat_id"],
                f"🔔 <b>هشدار طلایار</b>\n\n{ALERT_ASSETS[alert['asset']]['label']} به شرط رسید.\n"
                f"قیمت فعلی: <b>{_format_number(current)} {item.get('unit') or ''}</b>\n{detail}",
                parse_mode="HTML", reply_markup=main_menu())
            changed = True
            if alert.get("mode") == "repeat":
                if alert.get("type") == "percent": alert["baseline"] = current
                else: alert["armed"] = False
                remaining.append(alert)
        except Exception:
            logger.exception("Alert send failed"); remaining.append(alert)
    if changed or len(remaining) != len(alerts): _save_json(ALERTS_FILE, remaining)


async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    subs = _load_json(DAILY_SUBS_FILE, {}); now = datetime.now(TEHRAN_TZ)
    due = [s for s in subs.values() if s.get("active") and s.get("time") == now.strftime("%H:%M") and s.get("last_sent") != now.strftime("%Y-%m-%d")]
    if not due: return
    market, _ = get_market_data()
    if not market: return
    report = build_daily_report(market)
    for sub in due:
        if not is_vip(sub.get("user_id")): sub["active"] = False; continue
        try:
            await context.bot.send_message(sub["chat_id"], report, parse_mode="HTML", reply_markup=main_menu())
            sub["last_sent"] = now.strftime("%Y-%m-%d")
        except Exception: logger.exception("Daily report failed")
    _save_json(DAILY_SUBS_FILE, subs)


async def vip_backup_job(context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")
    registry = _load_json(VIP_USERS_FILE, {}); changed = False
    for user_id, entry in registry.items():
        days = vip_days_left(user_id)
        key = f"{today}:{days}"
        if days in {1, 3} and entry.get("last_reminder") != key:
            try:
                await context.bot.send_message(int(user_id), f"⏳ {days} روز از VIP شما باقی مانده است.", reply_markup=vip_menu(user_id))
                entry["last_reminder"] = key; changed = True
            except Exception: logger.exception("VIP reminder failed")
    if changed: _save_json(VIP_USERS_FILE, registry)
    state = _load_json(BOT_STATE_FILE, {})
    if state.get("last_backup") != today: make_backup()


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Telegram update failed", exc_info=context.error)
    state = _load_json(BOT_STATE_FILE, {})
    now = int(time.time())
    if str(ADMIN_ID).isdigit() and now - int(state.get("last_error_notice", 0)) > 600:
        try:
            await context.bot.send_message(int(ADMIN_ID), "⚠️ یک خطای فنی در طلایار ثبت شد؛ جزئیات در Railway Logs است.")
            state["last_error_notice"] = now
            _save_json(BOT_STATE_FILE, state)
        except Exception:
            logger.exception("Admin error notification failed")


def run():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")

    if not BRS_API_URL:
        logger.warning("BRS_API_URL is missing; price buttons will show a configuration error")

    init_storage()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start_v2))
    app.add_handler(CommandHandler("cancel", cancel_v2))
    app.add_handler(CommandHandler("myid", my_id))
    app.add_handler(CommandHandler("vip", vip_command_v2))
    app.add_handler(CommandHandler("admin", admin_v2))
    app.add_handler(CommandHandler("addvip", add_vip_v2))
    app.add_handler(CommandHandler("removevip", remove_vip_v2))
    app.add_handler(CommandHandler("userinfo", userinfo_v2))
    app.add_handler(CallbackQueryHandler(buttons_v2))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo_v2))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text_v2))
    app.add_error_handler(error_handler)

    if app.job_queue is None:
        raise RuntimeError("JobQueue is unavailable. Install python-telegram-bot[job-queue].")
    app.job_queue.run_repeating(
        market_job,
        interval=ALERT_CHECK_INTERVAL,
        first=20,
        name="market-job",
    )
    app.job_queue.run_repeating(daily_job, interval=30, first=10, name="daily-reports")
    app.job_queue.run_repeating(vip_backup_job, interval=21600, first=60, name="vip-backup")
    app.run_polling()


if __name__ == "__main__":
    run()
