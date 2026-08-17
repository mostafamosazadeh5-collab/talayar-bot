import os
import json
import logging
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ALERTS_FILE = "alerts.json"

COIN_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
}

def load_alerts():
    if os.path.exists(ALERTS_FILE):
        with open(ALERTS_FILE, "r") as f:
            return json.load(f)
    return []

def save_alerts(alerts):
    with open(ALERTS_FILE, "w") as f:
        json.dump(alerts, f)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! به ربات طلایار خوش اومدید 🌟\n\n"
        "دستورات موجود:\n"
        "/price - قیمت لحظه‌ای ارزهای دیجیتال\n"
        "/gold - قیمت لحظه‌ای طلا و نقره\n"
        "/alert - تنظیم هشدار قیمت\n"
        "/myalerts - مشاهده هشدارهای من\n"
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

async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        gold_response = requests.get("https://api.gold-api.com/price/XAU", timeout=10)
        silver_response = requests.get("https://api.gold-api.com/price/XAG", timeout=10)

        gold_data = gold_response.json()
        silver_data = silver_response.json()

        gold_price = gold_data["price"]
        silver_price = silver_data["price"]

        message = (
            "🥇 قیمت لحظه‌ای فلزات (دلار، هر اونس):\n\n"
            f"🟡 طلا: {gold_price:,.2f}$\n"
            f"⚪ نقره: {silver_price:,.2f}$\n"
        )
        await update.message.reply_text(message)
    except Exception as e:
        await update.message.reply_text("خطا در دریافت قیمت طلا/نقره، لطفاً دوباره امتحان کنید.")
        logging.error(f"Gold fetch error: {e}")

async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if len(args) != 2:
        await update.message.reply_text(
            "فرمت درست:\n/alert BTC 70000\n\n"
            "ارزهای موجود: BTC, ETH, USDT"
        )
        return

    coin_symbol = args[0].upper()
    if coin_symbol not in COIN_MAP:
        await update.message.reply_text("ارز نامعتبره. از BTC, ETH یا USDT استفاده کنید.")
        return

    try:
        target_price = float(args[1])
    except ValueError:
        await update.message.reply_text("قیمت باید عدد باشه. مثال: /alert BTC 70000")
        return

    alerts = load_alerts()
    alerts.append({
        "chat_id": update.effective_chat.id,
        "coin": coin_symbol,
        "target_price": target_price,
    })
    save_alerts(alerts)

    await update.message.reply_text(
        f"✅ هشدار تنظیم شد!\n"
        f"وقتی {coin_symbol} به {target_price:,}$ برسه بهتون خبر میدم."
    )

async def myalerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alerts = load_alerts()
    user_alerts = [a for a in alerts if a["chat_id"] == update.effective_chat.id]

    if not user_alerts:
        await update.message.reply_text("هیچ هشداری تنظیم نکردید.")
        return

    message = "🔔 هشدارهای شما:\n\n"
    for a in user_alerts:
        message += f"• {a['coin']} → {a['target_price']:,}$\n"

    await update.message.reply_text(message)

async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    alerts = load_alerts()
    if not alerts:
        return

    try:
        ids = ",".join(set(COIN_MAP[a["coin"]] for a in alerts))
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
        response = requests.get(url, timeout=10)
        prices = response.json()
    except Exception as e:
        logging.error(f"Alert check error: {e}")
        return

    remaining_alerts = []
    for a in alerts:
        current_price = prices.get(COIN_MAP[a["coin"]], {}).get("usd")
        if current_price is not None and current_price >= a["target_price"]:
            try:
                await context.bot.send_message(
                    chat_id=a["chat_id"],
                    text=f"🚨 هشدار قیمت!\n{a['coin']} به {current_price:,}$ رسید (هدف: {a['target_price']:,}$)"
                )
            except Exception as e:
                logging.error(f"Send alert error: {e}")
        else:
            remaining_alerts.append(a)

    save_alerts(remaining_alerts)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "راهنمای ربات طلایار:\n\n"
        "/start - شروع\n"
        "/price - قیمت لحظه‌ای ارزها\n"
        "/gold - قیمت لحظه‌ای طلا و نقره\n"
        "/alert BTC 70000 - تنظیم هشدار قیمت\n"
        "/myalerts - مشاهده هشدارهای من\n"
        "/help - همین راهنما"
    )

def main():
    if not BOT_TOKEN:
        logging.error("BOT_TOKEN not found in environment variables!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("gold", gold))
    app.add_handler(CommandHandler("alert", alert))
    app.add_handler(CommandHandler("myalerts", myalerts))
    app.add_handler(CommandHandler("help", help_command))

    app.job_queue.run_repeating(check_alerts, interval=300, first=10)

    app.run_polling()

if __name__ == "__main__":
    main()
