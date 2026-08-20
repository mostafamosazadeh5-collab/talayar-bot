import os
import json
import logging
import requests
from datetime import time
import pytz
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
ALERTS_FILE = "alerts.json"
VIP_FILE = "vip_users.json"
DAILY_FILE = "daily_subs.json"

FREE_ALERT_LIMIT = 1
IRAN_TZ = pytz.timezone("Asia/Tehran")

COIN_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "USDT": "tether",
}

# ---------- Helper functions ----------

def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)

def load_alerts():
    return load_json(ALERTS_FILE)

def save_alerts(alerts):
    save_json(ALERTS_FILE, alerts)

def load_vips():
    return load_json(VIP_FILE)

def is_vip(chat_id):
    vips = load_vips()
    return chat_id in vips

def load_daily_subs():
    return load_json(DAILY_FILE)

def save_daily_subs(subs):
    save_json(DAILY_FILE, subs)

# ---------- Shared price fetch ----------

def fetch_market_summary():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,tether&vs_currencies=usd"
    response = requests.get(url, timeout=10)
    data = response.json()
    btc = data["bitcoin"]["usd"]
    eth = data["ethereum"]["usd"]
    usdt = data["tether"]["usd"]

    gold_response = requests.get("https://api.gold-api.com/price/XAU", timeout=10)
    silver_response = requests.get("https://api.gold-api.com/price/XAG", timeout=10)
    gold_price = gold_response.json()["price"]
    silver_price = silver_response.json()["price"]

    return (
        "📊 قیمت لحظه‌ای ارزها (دلار):\n\n"
        f"₿ بیت‌کوین: {btc:,}$\n"
        f"Ξ اتریوم: {eth:,}$\n"
        f"₮ تتر: {usdt}$\n"
        f"🟡 طلا: {gold_price:,.2f}$\n"
        f"⚪ نقره: {silver_price:,.2f}$\n"
    )

# ---------- Commands ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "سلام! به ربات طلایار خوش اومدید 🌟\n\n"
        "دستورات موجود:\n"
        "/price - قیمت لحظه‌ای ارزهای دیجیتال\n"
        "/gold - قیمت لحظه‌ای طلا و نقره\n"
        "/alert - تنظیم هشدار قیمت\n"
        "/myalerts - مشاهده هشدارهای من\n"
        "/dailyreport - فعال/غیرفعال کردن گزارش روزانه (ویژه VIP)\n"
        "/vip - اطلاعات اشتراک VIP\n"
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
    chat_id = update.effective_chat.id
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
    user_alert_count = len([a for a in alerts if a["chat_id"] == chat_id])

    if not is_vip(chat_id) and user_alert_count >= FREE_ALERT_LIMIT:
        await update.message.reply_text(
            f"⚠️ در نسخه‌ی رایگان فقط می‌تونید {FREE_ALERT_LIMIT} هشدار فعال داشته باشید.\n\n"
            "برای هشدار نامحدود و امکانات بیشتر، دستور /vip رو بزنید 🌟"
        )
        return

    alerts.append({
        "chat_id": chat_id,
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

async def dailyreport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id

    if not is_vip(chat_id):
        await update.message.reply_text(
            "📊 گزارش خودکار روزانه یک امکان ویژه‌ی VIP هست.\n\n"
            "برای فعال‌سازی، دستور /vip رو بزنید 🌟"
        )
        return

    args = context.args
    if not args or args[0].lower() not in ["on", "off"]:
        await update.message.reply_text(
            "فرمت درست:\n"
            "/dailyreport on - فعال‌سازی گزارش روزانه (ساعت ۹ صبح)\n"
            "/dailyreport off - غیرفعال‌سازی"
        )
        return

    subs = load_daily_subs()

    if args[0].lower() == "on":
        if chat_id not in subs:
            subs.append(chat_id)
            save_daily_subs(subs)
        await update.message.reply_text("✅ گزارش خودکار روزانه فعال شد! هر روز ساعت ۹ صبح براتون ارسال میشه.")
    else:
        if chat_id in subs:
            subs.remove(chat_id)
            save_daily_subs(subs)
        await update.message.reply_text("❌ گزارش خودکار روزانه غیرفعال شد.")

async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if is_vip(chat_id):
        await update.message.reply_text(
            "🌟 شما عضو VIP هستید!\n\n"
            "برای فعال‌سازی گزارش خودکار روزانه:\n/dailyreport on"
        )
        return

    message = (
        "🌟 اشتراک VIP طلایار 🌟\n\n"
        "با ارتقا به VIP از این امکانات بهره‌مند میشید:\n\n"
        "🔔 هشدار قیمت نامحدود\n"
        "📊 گزارش خودکار روزانه بازار\n"
        "📈 هشدار بر اساس درصد نوسان\n"
        "🎯 پشتیبانی اولویت‌دار\n"
        "📚 آموزش پایه تحلیل تکنیکال\n"
        "📢 دسترسی به کانال خصوصی تحلیل\n\n"
        "برای خرید اشتراک، با پشتیبانی در ارتباط باشید:\n"
        "👉 @WAHL4"
    )
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

async def send_daily_reports(context: ContextTypes.DEFAULT_TYPE):
    subs = load_daily_subs()
    if not subs:
        return

    try:
        summary = fetch_market_summary()
    except Exception as e:
        logging.error(f"Daily report fetch error: {e}")
        return

    message = "☀️ گزارش صبحگاهی بازار\n\n" + summary

    for chat_id in subs:
        try:
            await context.bot.send_message(chat_id=chat_id, text=message)
        except Exception as e:
            logging.error(f"Send daily report error to {chat_id}: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "راهنمای ربات طلایار:\n\n"
        "/start - شروع\n"
        "/price - قیمت لحظه‌ای ارزها\n"
        "/gold - قیمت لحظه‌ای طلا و نقره\n"
        "/alert BTC 70000 - تنظیم هشدار قیمت\n"
        "/myalerts - مشاهده هشدارهای من\n"
        "/dailyreport on|off - گزارش خودکار روزانه (VIP)\n"
        "/vip - اطلاعات اشتراک VIP\n"
        "/help - همین راهنما"
    )

# ---------- Admin-only: manually add VIP ----------

ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

async def addvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if str(chat_id) != str(ADMIN_CHAT_ID):
        return

    if len(context.args) != 1:
        await update.message.reply_text("فرمت: /addvip CHAT_ID")
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("CHAT_ID باید عدد باشه.")
        return

    vips = load_vips()
    if target_id not in vips:
        vips.append(target_id)
        save_json(VIP_FILE, vips)

    await update.message.reply_text(f"✅ کاربر {target_id} به VIP اضافه شد.")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"چت آیدی شما: {update.effective_chat.id}")

# ---------- Main ----------

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
    app.add_handler(CommandHandler("dailyreport", dailyreport))
    app.add_handler(CommandHandler("vip", vip))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("addvip", addvip))
    app.add_handler(CommandHandler("myid", myid))

    app.job_queue.run_repeating(check_alerts, interval=300, first=10)
    app.job_queue.run_daily(send_daily_reports, time=time(hour=9, minute=0, tzinfo=IRAN_TZ))

    app.run_polling()

if __name__ == "__main__":
    main()
