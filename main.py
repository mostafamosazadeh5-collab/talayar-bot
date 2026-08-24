import os
import logging
import time
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger("talayar")

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BRS_API_URL = os.environ.get("BRS_API_URL")

API_TIMEOUT = 20
CACHE_TTL_SECONDS = 20
_market_cache = {"data": None, "saved_at": 0.0}


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
    await update.message.reply_text("🟡 <b>طلایار</b>\n\nدستیار هوشمند رصد قیمت طلا، ارز و بازارهای مالی", reply_markup=main_menu(), parse_mode="HTML")


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "prices":
        await q.edit_message_text("📊 بازار را انتخاب کنید:", reply_markup=price_menu())
        return

    if data == "home":
        await q.edit_message_text("🟡 منوی اصلی", reply_markup=main_menu())
        return

    placeholders = {
        "alerts": "🔔 بخش هشدار قیمت در مرحله بعد فعال می‌شود.",
        "account": "👤 بخش حساب کاربری در مرحله بعد فعال می‌شود.",
        "vip": "⭐ بخش عضویت VIP در مرحله بعد فعال می‌شود.",
        "help": "ℹ️ برای مشاهده قیمت‌ها، گزینه «قیمت لحظه‌ای» را انتخاب کنید.",
    }
    if data in placeholders:
        await q.edit_message_text(placeholders[data], reply_markup=main_menu())
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


def run():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")

    if not BRS_API_URL:
        logger.warning("BRS_API_URL is missing; price buttons will show a configuration error")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling()


if __name__ == "__main__":
    run()
