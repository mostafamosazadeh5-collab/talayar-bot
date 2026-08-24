import os
import json
import logging
import threading
import time
import uuid
from datetime import datetime, timezone

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
DATA_DIR = os.environ.get("DATA_DIR", ".")

API_TIMEOUT = 20
CACHE_TTL_SECONDS = 20
FREE_ALERT_LIMIT = 1
ALERT_CHECK_INTERVAL = 60
ALERTS_FILE = os.path.join(DATA_DIR, "alerts.json")
VIP_USERS_FILE = os.path.join(DATA_DIR, "vip_users.json")
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
        [InlineKeyboardButton("👤 حساب کاربری", callback_data="account"),
         InlineKeyboardButton("⭐ عضویت VIP", callback_data="vip")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")]
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
         InlineKeyboardButton("🗑 حذف هشدارها", callback_data="alert_delete")],
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


def vip_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(
            "💬 ارتباط با ادمین برای خرید",
            url=f"https://t.me/{ADMIN_USERNAME}",
        )],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ])


def vip_text(user_id):
    return (
        "⭐ <b>عضویت VIP طلایار</b>\n\n"
        "✅ ساخت هشدار قیمت نامحدود\n"
        "✅ امکانات ویژه نسخه‌های آینده\n\n"
        "برای خرید اشتراک روی دکمه زیر بزن و این شناسه را برای ادمین بفرست:\n"
        f"<code>{user_id}</code>"
    )


def _ensure_data_files():
    os.makedirs(DATA_DIR, exist_ok=True)
    for path, default in ((ALERTS_FILE, []), (VIP_USERS_FILE, [])):
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


def load_alerts():
    data = _load_json(ALERTS_FILE, [])
    return data if isinstance(data, list) else []


def save_alerts(alerts):
    _save_json(ALERTS_FILE, alerts)


def is_vip(user_id):
    data = _load_json(VIP_USERS_FILE, [])
    wanted = str(user_id)
    if isinstance(data, list):
        return any(str(item) == wanted for item in data)
    if isinstance(data, dict):
        users = data.get("users", data)
        if isinstance(users, list):
            return any(str(item) == wanted for item in users)
        return wanted in {str(key) for key in users.keys()}
    return False


def add_vip_user(user_id):
    data = _load_json(VIP_USERS_FILE, [])
    if not isinstance(data, list):
        data = []
    if str(user_id) not in {str(item) for item in data}:
        data.append(int(user_id))
        _save_json(VIP_USERS_FILE, data)


def user_alerts(user_id):
    wanted = str(user_id)
    return [alert for alert in load_alerts() if str(alert.get("user_id")) == wanted]


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
    for token in (",", "٬", "،", " ", "تومان", "دلار"):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.replace("٫", ".")
    try:
        number = float(cleaned)
        return number if number > 0 else None
    except ValueError:
        return None


def _condition_label(condition):
    return "بالاتر یا مساوی" if condition == "above" else "پایین‌تر یا مساوی"


def _alert_list_text(user_id):
    alerts = user_alerts(user_id)
    if not alerts:
        return "📋 شما هیچ هشدار فعالی ندارید."

    lines = ["📋 <b>هشدارهای فعال شما</b>", ""]
    for index, alert in enumerate(alerts, start=1):
        asset = ALERT_ASSETS.get(alert.get("asset"), {})
        label = asset.get("label", alert.get("asset", "دارایی"))
        lines.append(
            f"{index}. {label}\n"
            f"شرط: {_condition_label(alert.get('condition'))}\n"
            f"هدف: {_format_number(alert.get('target'))}"
        )
        lines.append("")
    return "\n".join(lines).rstrip()


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
    alerts = load_alerts()
    alerts.append(alert)
    save_alerts(alerts)
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
        wanted = str(q.from_user.id)
        alerts = [alert for alert in load_alerts() if str(alert.get("user_id")) != wanted]
        save_alerts(alerts)
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

    remaining = []
    changed = False
    for alert in alerts:
        asset_key = alert.get("asset")
        item = find_alert_item(market, asset_key)
        if not item:
            remaining.append(alert)
            continue

        try:
            current_price = float(str(item.get("price")).replace(",", ""))
            target = float(alert.get("target"))
        except (TypeError, ValueError):
            logger.warning("Invalid alert data: id=%s", alert.get("id"))
            remaining.append(alert)
            continue

        condition = alert.get("condition")
        triggered = (
            (condition == "above" and current_price >= target)
            or (condition == "below" and current_price <= target)
        )
        if not triggered:
            remaining.append(alert)
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
            changed = True
            logger.info("Alert triggered: id=%s user_id=%s", alert.get("id"), alert.get("user_id"))
        except Exception:
            logger.exception("Could not send alert: id=%s", alert.get("id"))
            remaining.append(alert)

    if changed:
        save_alerts(remaining)


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Telegram update failed", exc_info=context.error)


def run():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")

    if not BRS_API_URL:
        logger.warning("BRS_API_URL is missing; price buttons will show a configuration error")

    _ensure_data_files()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("myid", my_id))
    app.add_handler(CommandHandler("vip", vip_command))
    app.add_handler(CommandHandler("addvip", add_vip))
    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_alert_price))
    app.add_error_handler(error_handler)

    if app.job_queue is None:
        raise RuntimeError("JobQueue is unavailable. Install python-telegram-bot[job-queue].")
    app.job_queue.run_repeating(
        check_price_alerts,
        interval=ALERT_CHECK_INTERVAL,
        first=20,
        name="price-alert-checker",
    )
    app.run_polling()


if __name__ == "__main__":
    run()
