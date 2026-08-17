import os
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! به ربات طلایار خوش اومدید 🌟\n\n"
        "دستورات موجود:\n"
        "/price - قیمت لحظه‌ای ارزهای دیجیتال\n"
        "/help - راهنما"
    )

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,tether&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        data = response.json()

        btc = data["bitcoin"]["usd"]
        eth = data["ethereum"]["usd"]
        usdt = data["tether"]["usd"]

        message = (
            "📊 قیمت لحظه‌ای ارزها (دلار):\n\n"
            f"₿ بیت‌کوین: {btc:,}$\n"
            f"Ξ اتریوم: {eth:,}$\n"
            f"₮ تتر: {usdt}$\n"
        )
        await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text("خطا در دریافت قیمت، لطفاً دوباره امتحان کنید.")
        logging.error(f"Price fetch error: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "راهنمای ربات طلایار:\n\n"
        "/start - شروع\n"
        "/price - قیمت لحظه‌ای ارزها\n"
        "/help - همین راهنما"
    )

def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN not found in environment variables!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("help", help_command))

    app.run_polling()

if __name__ == "__main__":
    main()
