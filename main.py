
import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🟡 <b>طلایار</b>\n\n"
        "دستیار هوشمند رصد قیمت طلا، ارز و بازارهای مالی\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:"
    )

    await update.message.reply_text(
        text,
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
            "📊 بخش قیمت لحظه‌ای\n\nبازار مورد نظر را انتخاب کنید:",
            reply_markup=price_menu()
        )

    elif data == "gold":
        await query.edit_message_text(
            "🪙 طلا و سکه\n\n"
            "در نسخه بعدی قیمت لحظه‌ای این بخش متصل می‌شود.\n\n"
            "• طلای ۱۸ عیار\n"
            "• سکه امامی\n"
            "• نیم سکه\n"
            "• ربع سکه",
            reply_markup=price_menu()
        )

    elif data == "iran_currency":
        await query.edit_message_text(
            "💵 بازار ارز\n\n"
            "اتصال API قیمت دلار در مرحله بعد انجام می‌شود.",
            reply_markup=price_menu()
        )

    elif data == "ounce":
        await query.edit_message_text(
            "🌎 انس جهانی\n\n"
            "اتصال قیمت XAUUSD در مرحله بعد.",
            reply_markup=price_menu()
        )

    elif data == "crypto":
        await query.edit_message_text(
            "₿ ارز دیجیتال\n\n"
            "BTC، ETH و USDT در مرحله بعد اضافه می‌شوند.",
            reply_markup=price_menu()
        )

    elif data == "alerts":
        await query.edit_message_text(
            "🔔 هشدار قیمت\n\n"
            "ساخت هشدارهای قیمتی در مرحله بعد فعال می‌شود.",
            reply_markup=main_menu()
        )

    elif data == "account":
        await query.edit_message_text(
            "👤 حساب کاربری\n\n"
            "اطلاعات کاربر و وضعیت VIP اینجا نمایش داده می‌شود.",
            reply_markup=main_menu()
        )

    elif data == "vip":
        await query.edit_message_text(
            "⭐ عضویت VIP\n\n"
            "بخش اشتراک ویژه در حال توسعه است.",
            reply_markup=main_menu()
        )

    elif data == "help":
        await query.edit_message_text(
            "ℹ️ راهنما\n\n"
            "طلایار برای رصد بازارهای مالی طراحی شده است.",
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
