import os
import json
import logging
import requests
from datetime import time
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
BRSAPI_KEY = os.environ.get("BRSAPI_KEY")
ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID")

ALERTS_FILE = "alerts.json"
VIP_FILE = "vip_users.json"
DAILY_FILE = "daily_subs.json"

FREE_ALERT_LIMIT = 1
IRAN_TZ = pytz.timezone("Asia/Tehran")

COIN_MAP = {"BTC": "bitcoin", "ETH": "ethereum", "USDT": "tether"}

# ---------- Storage helpers ----------

def load_json(path):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_alerts():
    return load_json(ALERTS_FILE)

def save_alerts(data):
    save_json(ALERTS_FILE, data)

def load_vips():
    return load_json(VIP_FILE)

def is_vip(chat_id):
    return chat_id in load_vips()

def load_daily_subs():
    return load_json(DAILY_FILE)

def save_daily_subs(data):
    save_json(DAILY_FILE, data)

# ---------- Data fetchers ----------

def fetch_crypto_usd():
    url = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,tether&vs_currencies=usd"
    r = requests.get(url, timeout=10)
    return r.json()

def fetch_global_metals():
    gold = requests.get("https://api.gold-api.com/price/XAU", timeout=10).json()
    silver = requests.get("https://api.gold-api.com/price/XAG", timeout=10).json()
    return gold["price"], silver["price"]

def fetch_brsapi():
    if not BRSAPI_KEY:
        raise RuntimeError("BRSAPI_KEY not set")
    url = f"https://Api.BrsApi.ir/Market/Gold_Currency.php?key={BRSAPI_KEY}"
    r = requests.get(url, timeout=10)
    data = r.json()
    if "gold" not in data or "currency" not in data:
        logging.error(f"brsapi unexpected response: {data}")
        raise RuntimeError("brsapi invalid response (check BRSAPI_KEY)")
    return data

def find_symbol(items, symbol):
    for item in items:
        if item.get("symbol") == symbol:
            return item
    return None

# ---------- Text builders ----------

def build_crypto_text():
    data = fetch_crypto_usd()
    btc = data["bitcoin"]["usd"]
    eth = data["ethereum"]["usd"]
    usdt = data["tether"]["usd"]
    return (
        "₿ قیمت لحظه‌ای ارزهای دیجیتال (دلار)\n\n"
        f"₿ بیت‌کوین: {btc:,}$\n"
        f"Ξ اتریوم: {eth:,}$\n"
        f"₮ تتر: {usdt}$\n"
    )

def build_ounce_text():
    gold, silver = fetch_global_metals()
    return (
        "🌍 قیمت جهانی فلزات (دلار، هر اونس)\n\n"
        f"🟡 طلا: {gold:,.2f}$\n"
        f"⚪ نقره: {silver:,.2f}$\n"
    )

def build_goldcoin_toman_text():
    data = fetch_brsapi()
    gold_list = data.get("gold", [])

    g18 = find_symbol(gold_list, "IR_GOLD_18K")
    emami = find_symbol(gold_list, "IR_COIN_EMAMI")
    half = find_symbol(gold_list, "IR_COIN_HALF")
    quarter = find_symbol(gold_list, "IR_COIN_QUARTER")

    lines = ["🥇 طلا و سکه (بازار داخلی، تومان)\n"]
    if g18:
        lines.append(f"🟡 طلای ۱۸ عیار (هر گرم): {g18['price']:,} تومان")
    if emami:
        lines.append(f"🪙 سکه امامی: {emami['price']:,} تومان")
    if half:
        lines.append(f"🪙 نیم سکه: {half['price']:,} تومان")
    if quarter:
        lines.append(f"🪙 ربع سکه: {quarter['price']:,} تومان")

    if len(lines) == 1:
        raise RuntimeError("no gold/coin symbols matched in brsapi response")

    return "\n".join(lines) + "\n"

def build_currency_toman_text():
    data = fetch_brsapi()
    currency_list = data.get("currency", [])

    wanted = [("USD", "دلار آمریکا"), ("EUR", "یورو"), ("AED", "درهم امارات"), ("GBP", "پوند")]
    lines = ["💵 بازار ارز (تومان)\n"]
    for symbol, label in wanted:
        item = find_symbol(currency_list, symbol)
        if item:
            lines.append(f"💴 {label}: {item['price']:,} تومان")

    if len(lines) == 1:
        raise RuntimeError("no currency symbols matched in brsapi response")

    return "\n".join(lines) + "\n"

# ---------- Inline keyboards ----------

def main_menu_kb():
    keyboard = [
        [InlineKeyboardButton("💰 قیمت لحظه‌ای", callback_data="menu_price"),
         InlineKeyboardButton("🚨 هشدار قیمت", callback_data="menu_alert")],
        [InlineKeyboardButton("👤 حساب کاربری", callback_data="menu_account"),
         InlineKeyboardButton("⭐ عضویت VIP", callback_data="menu_vip")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="menu_help")],
    ]
    return InlineKeyboardMarkup(keyboard)

def price_menu_kb():
    keyboard = [
        [InlineKeyboardButton("💵 بازار ارز", callback_data="sub_currency"),
         InlineKeyboardButton("🥇 طلا و سکه", callback_data="sub_goldcoin")],
        [InlineKeyboardButton("🌍 انس جهانی", callback_data="sub_ounce"),
         InlineKeyboardButton("₿ ارز دیجیتال", callback_data="sub_crypto")],
        [InlineKeyboardButton("⬅️ بازگشت", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def back_only_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ بازگشت", callback_data="menu_price")]])

# ---------- Command handlers ----------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🌟 به ربات طلایار خوش اومدید\n\n"
        "دستیار هوشمند بازار طلا، ارز و کریپتو\n\n"
        "از منوی زیر یا دستورات متنی (/help) استفاده کنید:",
        reply_markup=main_menu_kb()
    )

async def price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        await update.message.reply_text(build_crypto_text())
    except Exception as e:
        logging.error(f"price error: {e}")
        await update.message.reply_text("❌ خطا در دریافت قیمت، لطفاً دوباره امتحان کنید.")

async def gold(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        text = build_ounce_text()
    except Exception as e:
        logging.error(f"gold(ounce) error: {e}")
        text = "❌ خطا در دریافت قیمت جهانی.\n"

    try:
        text += "\n" + build_goldcoin_toman_text()
    except Exception as e:
        logging.error(f"gold(toman) error: {e}")
        text += "\n❌ خطا در دریافت قیمت بازار داخلی."

    await update.message.reply_text(text)

async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    args = context.args

    if len(args) != 2:
        await update.message.reply_text("فرمت درست:\n/alert BTC 70000\n\nارزهای موجود: BTC, ETH, USDT")
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
            "برای هشدار نامحدود، دستور /vip رو بزنید 🌟"
        )
        return

    alerts.append({"chat_id": chat_id, "coin": coin_symbol, "target_price": target_price})
    save_alerts(alerts)

    await update.message.reply_text(f"✅ هشدار تنظیم شد!\nوقتی {coin_symbol} به {target_price:,}$ برسه بهتون خبر میدم.")

async def myalerts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    alerts = load_alerts()
    user_alerts = [a for a in alerts if a["chat_id"] == update.effective_chat.id]
    if not user_alerts:
        await update.message.reply_text("هیچ هشداری تنظیم نکردید.")
        return
    msg = "🔔 هشدارهای شما:\n\n" + "\n".join(f"• {a['coin']} → {a['target_price']:,}$" for a in user_alerts)
    await update.message.reply_text(msg)

async def dailyreport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if not is_vip(chat_id):
        await update.message.reply_text("📊 گزارش خودکار روزانه یک امکان ویژه‌ی VIP هست.\n\nبرای فعال‌سازی /vip رو بزنید 🌟")
        return

    args = context.args
    if not args or args[0].lower() not in ["on", "off"]:
        await update.message.reply_text("فرمت درست:\n/dailyreport on\n/dailyreport off")
        return

    subs = load_daily_subs()
    if args[0].lower() == "on":
        if chat_id not in subs:
            subs.append(chat_id)
            save_daily_subs(subs)
        await update.message.reply_text("✅ گزارش خودکار روزانه فعال شد! هر روز ساعت ۹ صبح ارسال میشه.")
    else:
        if chat_id in subs:
            subs.remove(chat_id)
            save_daily_subs(subs)
        await update.message.reply_text("❌ گزارش خودکار روزانه غیرفعال شد.")

def vip_text(chat_id):
    if is_vip(chat_id):
        return "🌟 شما عضو VIP هستید!\n\nبرای فعال‌سازی گزارش روزانه:\n/dailyreport on"
    return (
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

async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(vip_text(update.effective_chat.id))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "راهنمای ربات طلایار:\n\n"
        "/start - شروع و نمایش منو\n"
        "/price - قیمت لحظه‌ای ارزهای دیجیتال\n"
        "/gold - قیمت جهانی و داخلی طلا/سکه\n"
        "/alert BTC 70000 - تنظیم هشدار قیمت\n"
        "/myalerts - مشاهده هشدارهای من\n"
        "/dailyreport on|off - گزارش خودکار روزانه (VIP)\n"
        "/vip - اطلاعات اشتراک VIP\n"
        "/help - همین راهنما"
    )

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"چت آیدی شما: {update.effective_chat.id}")

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

# ---------- Button (callback) handler ----------

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action = query.data
    chat_id = query.message.chat.id

    try:
        if action == "menu_price":
            await query.edit_message_text("💰 کدوم بازار رو می‌خواید ببینید؟", reply_markup=price_menu_kb())

        elif action == "back_main":
            await query.edit_message_text(
                "🌟 به ربات طلایار خوش اومدید\n\nاز منوی زیر استفاده کنید:",
                reply_markup=main_menu_kb()
            )

        elif action == "sub_crypto":
            await query.edit_message_text(build_crypto_text(), reply_markup=back_only_kb())

        elif action == "sub_ounce":
            await query.edit_message_text(build_ounce_text(), reply_markup=back_only_kb())

        elif action == "sub_goldcoin":
            await query.edit_message_text(build_goldcoin_toman_text(), reply_markup=back_only_kb())

        elif action == "sub_currency":
            await query.edit_message_text(build_currency_toman_text(), reply_markup=back_only_kb())

        elif action == "menu_alert":
            await query.edit_message_text(
                "🚨 برای تنظیم هشدار قیمت، این دستور رو بفرستید:\n\n"
                "/alert BTC 70000\n\n"
                "(به‌جای BTC می‌تونید از ETH یا USDT هم استفاده کنید)\n\n"
                "برای دیدن هشدارهای فعال: /myalerts",
                reply_markup=main_menu_kb()
            )

        elif action == "menu_account":
            vip_status = "🌟 VIP" if is_vip(chat_id) else "کاربر عادی"
            alerts_count = len([a for a in load_alerts() if a["chat_id"] == chat_id])
            await query.edit_message_text(
                f"👤 حساب کاربری شما\n\n"
                f"وضعیت: {vip_status}\n"
                f"هشدارهای فعال: {alerts_count}\n"
                f"چت آیدی: {chat_id}",
                reply_markup=main_menu_kb()
            )

        elif action == "menu_vip":
            await query.edit_message_text(vip_text(chat_id), reply_markup=main_menu_kb())

        elif action == "menu_help":
            await query.edit_message_text(
                "📚 راهنمای طلایار\n\n"
                "از منو برای دیدن قیمت‌ها استفاده کنید یا دستورات متنی زیر رو بفرستید:\n\n"
                "/price /gold /alert /myalerts /vip /dailyreport /help",
                reply_markup=main_menu_kb()
            )

    except Exception as e:
        logging.error(f"button_handler error ({action}): {e}")
        await query.edit_message_text(
            "❌ خطا در دریافت اطلاعات. چند لحظه دیگه دوباره امتحان کنید.",
            reply_markup=main_menu_kb()
        )

# ---------- Background jobs ----------

async def check_alerts(context: ContextTypes.DEFAULT_TYPE):
    alerts = load_alerts()
    if not alerts:
        return
    try:
        ids = ",".join(set(COIN_MAP[a["coin"]] for a in alerts))
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
        prices = requests.get(url, timeout=10).json()
    except Exception as e:
        logging.error(f"check_alerts fetch error: {e}")
        return

    remaining = []
    for a in alerts:
        current = prices.get(COIN_MAP[a["coin"]], {}).get("usd")
        if current is not None and current >= a["target_price"]:
            try:
                await context.bot.send_message(
                    chat_id=a["chat_id"],
                    text=f"🚨 هشدار قیمت!\n{a['coin']} به {current:,}$ رسید (هدف: {a['target_price']:,}$)"
                )
            except Exception as e:
                logging.error(f"send alert error: {e}")
        else:
            remaining.append(a)
    save_alerts(remaining)

async def send_daily_reports(context: ContextTypes.DEFAULT_TYPE):
    subs = load_daily_subs()
    if not subs:
        return
    try:
        text = "☀️ گزارش صبحگاهی طلایار\n\n" + build_crypto_text() + "\n" + build_goldcoin_toman_text()
    except Exception as e:
        logging.error(f"daily report build error: {e}")
        return
    for chat_id in subs:
        try:
            await context.bot.send_message(chat_id=chat_id, text=text)
        except Exception as e:
            logging.error(f"send daily report error to {chat_id}: {e}")

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
    app.add_handler(CallbackQueryHandler(button_handler))

    app.job_queue.run_repeating(check_alerts, interval=300, first=10)
    app.job_queue.run_daily(send_daily_reports, time=time(hour=9, minute=0, tzinfo=IRAN_TZ))

    app.run_polling()

if __name__ == "__main__":
    main()
