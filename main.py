import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

def main_menu():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💰 قیمت لحظه‌ای", callback_data="prices"),
            InlineKeyboardButton("🚨 هشدار قیمت", callback_data="alerts")
        ],
        [
            InlineKeyboardButton("📊 مقایسه بازار", callback_data="compare"),
            InlineKeyboardButton("🧮 محاسبه‌گر", callback_data="calculator")
        ],
        [
            InlineKeyboardButton("💎 طلاهای من", callback_data="mygold"),
            InlineKeyboardButton("⭐ VIP", callback_data="vip")
        ],
        [
            InlineKeyboardButton("📚 راهنما", callback_data="help")
        ]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌟 به طلایار خوش آمدید\n\nیک گزینه را انتخاب کنید:",
        reply_markup=main_menu()
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "این بخش در حال توسعه است.",
        reply_markup=main_menu()
    )

def main():
    if not BOT_TOKEN:
        return
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.run_polling()

if __name__ == "__main__":
    main()
