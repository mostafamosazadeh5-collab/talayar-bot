import os
import logging
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BRS_API_URL = os.environ.get("BRS_API_URL")


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


def get_market_data():
    try:
        r = requests.get(BRS_API_URL, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception as e:
        logging.error(e)
    return None


def find_item(data, symbol):
    for section in ["gold", "currency", "cryptocurrency"]:
        for item in data.get(section, []):
            if item.get("symbol") == symbol:
                return item
    return None


def show_item(item):
    if not item:
        return "اطلاعات موجود نیست\n\n"
    return f"{item['name']}:\n{int(float(item['price'])):,} {item['unit']}\nتغییر: {item.get('change_percent',0)}%\n\n"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🟡 <b>طلایار</b>\n\nدستیار هوشمند رصد قیمت طلا، ارز و بازارهای مالی", reply_markup=main_menu(), parse_mode="HTML")


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data

    if data == "prices":
        await q.edit_message_text("📊 بازار را انتخاب کنید:", reply_markup=price_menu())
        return

    market = get_market_data()

    if data == "gold" and market:
        text = "🪙 <b>طلا و سکه</b>\n\n" + show_item(find_item(market,"IR_GOLD_18K")) + show_item(find_item(market,"IR_GOLD_24K")) + show_item(find_item(market,"IR_COIN_EMAMI")) + show_item(find_item(market,"IR_COIN_HALF")) + show_item(find_item(market,"IR_COIN_QUARTER"))
    elif data == "iran_currency" and market:
        text = "💵 <b>ارز</b>\n\n" + show_item(find_item(market,"USD")) + show_item(find_item(market,"EUR")) + show_item(find_item(market,"USDT_IRT"))
    elif data == "ounce" and market:
        text = "🌎 <b>انس جهانی</b>\n\n" + show_item(find_item(market,"XAUUSD"))
    elif data == "crypto" and market:
        text = "₿ <b>کریپتو</b>\n\n" + show_item(find_item(market,"BTC")) + show_item(find_item(market,"ETH")) + show_item(find_item(market,"USDT"))
    elif data == "home":
        await q.edit_message_text("🟡 منوی اصلی", reply_markup=main_menu())
        return
    else:
        text = "خطا در دریافت اطلاعات"

    await q.edit_message_text(text, reply_markup=price_menu(), parse_mode="HTML")


def run():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))
    app.run_polling()


if __name__ == "__main__":
    run()
