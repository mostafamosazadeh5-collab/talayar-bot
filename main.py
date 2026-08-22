import os
import logging
import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BRS_API_URL = os.environ.get("BRS_API_URL")


def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("📊 قیمت لحظه‌ای", callback_data="prices"),
            InlineKeyboardButton("🔔 هشدار قیمت", callback_data="alerts"),
        ],
        [
            InlineKeyboardButton("👤 حساب کاربری", callback_data="account"),
            InlineKeyboardButton("⭐ عضویت VIP", callback_data="vip"),
        ],
        [
            InlineKeyboardButton("ℹ️ راهنما", callback_data="help"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def price_menu():
    keyboard = [
        [InlineKeyboardButton("💵 بازار ارز", callback_data="iran_currency")],
        [InlineKeyboardButton("🪙 طلا و سکه", callback_data="gold")],
        [InlineKeyboardButton("🌎 انس جهانی", callback_data="ounce")],
        [InlineKeyboardButton("₿ ارز دیجیتال", callback_data="crypto")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ]
    return InlineKeyboardMarkup(keyboard)


def get_market_data():
    try:
        response = requests.get(BRS_API_URL, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logging.error(e)
    return None


def find_item(data, symbol):
    for section in ["gold", "currency", "cryptocurrency"]:
        for item in data.get(section, []):
            if item.get("symbol") == symbol:
                return item
    return None


def format_price(item):
    if not item:
        return "اطلاعات موجود نیست\n"

    price = int(float(item.get("price", 0)))
    change = item.get("change_percent", 0)

    return (
        f"{item.get('name')}:\n"
        f"{price:,} {item.get('unit')}\n"
        f"تغییر: {change}%\n\n"
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🟡 <b>طلایار</b>\n\nدستیار هوشمند رصد قیمت طلا، ارز و بازارهای مالی\n\nیکی از گزینه‌ها را انتخاب کنید:",
        reply_markup=main_menu(),
        parse_mode="HTML"
    )


async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "home":
        await query.edit_message_text(
            "🟡 <b>طلایار</b>\n\nمنوی اصلی:",
            reply_markup=main_menu(),
            parse_mode="HTML"
        )

    elif data == "prices":
        await query.edit_message_text(
            "📊 قیمت لحظه‌ای\n\nبازار مورد نظر را انتخاب کنید:",
            reply_markup=price_menu()
        )

    elif data == "gold":
        market = get_market_data()

        if market:
            text = (
                "🪙 <b>بازار طلا و سکه</b>\n\n"
                + format_price(find_item(market, "IR_GOLD_18K"))
                + format_price(find_item(market, "IR_GOLD_24K"))
                + format_price(find_item(market, "IR_COIN_EMAMI"))
                + format_price(find_item(market, "IR_COIN_HALF"))
                + format_price(find_item(market, "IR_COIN_QUARTER"))
            )
        else:
            text = "خطا در دریافت اطلاعات API"

        await query.edit_message_text(
            text,
            reply_markup=price_menu(),
            parse_mode="HTML"
        )

    else:
        await query.edit_message_text(
            "این بخش در حال توسعه است.",
            reply_markup=main_menu()
        )


def run():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN تنظیم نشده است")

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(buttons))

    app.run_polling()


if __name__ == "__main__":
    run()
