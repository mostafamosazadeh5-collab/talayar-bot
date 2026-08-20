import os
import json
import logging
import requests

from datetime import time
import pytz

from telegram import (
Update,
InlineKeyboardButton,
InlineKeyboardMarkup
)

from telegram.ext import (
Application,
CommandHandler,
CallbackQueryHandler,
ContextTypes
)

logging.basicConfig(level=logging.INFO)

=========================

تنظیمات

=========================

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

=========================

ذخیره سازی اطلاعات

=========================

def load_json(path):

if os.path.exists(path):  

    with open(path, "r", encoding="utf-8") as f:  
        return json.load(f)  

return []

def save_json(path, data):

with open(path, "w", encoding="utf-8") as f:  

    json.dump(  
        data,  
        f,  
        ensure_ascii=False,  
        indent=4  
    )

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

=========================

دریافت قیمت کریپتو

=========================

def fetch_crypto_price():

url = (  
    "https://api.coingecko.com/api/v3/simple/price"  
    "?ids=bitcoin,ethereum,tether"  
    "&vs_currencies=usd"  
)  


response = requests.get(  
    url,  
    timeout=10  
)  


return response.json()

=========================

منوی اصلی

=========================

def main_menu():

keyboard = [  

    [  
        InlineKeyboardButton(  
            "💰 قیمت لحظه‌ای",  
            callback_data="prices"  
        ),  

        InlineKeyboardButton(  
            "🚨 هشدار قیمت",  
            callback_data="alerts"  
        )  
    ],  


    [  
        InlineKeyboardButton(  
            "📊 مقایسه بازار",  
            callback_data="compare"  
        ),  

        InlineKeyboardButton(  
            "🧮 محاسبه‌گر",  
            callback_data="calculator"  
        )  
    ],  


    [  
        InlineKeyboardButton(  
            "💎 طلاهای من",  
            callback_data="mygold"  
        ),  

        InlineKeyboardButton(  
            "⭐ اشتراک VIP",  
            callback_data="vip"  
        )  
    ],  


    [  
        InlineKeyboardButton(  
            "📚 راهنما",  
            callback_data="help"  
        )  
    ]  

]  


return InlineKeyboardMarkup(keyboard)

=========================

دستور شروع

=========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

await update.message.reply_text(  
    "🌟 به طلایار خوش آمدید\n\n"  
    "دستیار هوشمند بازار طلا، ارز و کریپتو\n\n"  
    "لطفاً یک گزینه را انتخاب کنید:",  
    reply_markup=main_menu()  
)

=========================

نمایش قیمت کریپتو

=========================

async def show_prices(query):

try:  

    data = fetch_crypto_price()  


    btc = data["bitcoin"]["usd"]  
    eth = data["ethereum"]["usd"]  
    usdt = data["tether"]["usd"]  


    message = (  
        "💰 قیمت لحظه‌ای بازار\n\n"  
        "━━━━━━━━━━━━\n\n"  
        f"₿ بیت‌کوین:\n"  
        f"{btc:,}$\n\n"  

        f"Ξ اتریوم:\n"  
        f"{eth:,}$\n\n"  

        f"₮ تتر:\n"  
        f"{usdt}$\n\n"  

        "━━━━━━━━━━━━\n\n"  
        "🥇 بخش طلای ایران به زودی اضافه می‌شود"  
    )  


    await query.edit_message_text(  
        message,  
        reply_markup=main_menu()  
    )  


except Exception as e:  

    logging.error(  
        f"Price error: {e}"  
    )  

    await query.edit_message_text(  
        "❌ خطا در دریافت قیمت",  
        reply_markup=main_menu()  
    )

=========================

نمایش VIP

=========================

async def show_vip(query):

message = (  
    "⭐ اشتراک VIP طلایار\n\n"  

    "با عضویت VIP:\n\n"  

    "🔔 هشدارهای نامحدود\n"  
    "📊 گزارش روزانه بازار\n"  
    "📈 تحلیل هوشمند بازار\n"  
    "🎯 امکانات ویژه\n\n"  

    "برای فعال سازی با پشتیبانی ارتباط بگیرید."  
)  


await query.edit_message_text(  
    message,  
    reply_markup=main_menu()  
)

=========================

راهنما

=========================

async def show_help(query):

message = (  
    "📚 راهنمای طلایار\n\n"  

    "با استفاده از منو می‌توانید:\n\n"  

    "💰 قیمت‌ها را مشاهده کنید\n"  
    "🚨 هشدار تنظیم کنید\n"  
    "⭐ اشتراک VIP بگیرید\n\n"  

    "تمام امکانات بدون نیاز به دستور قابل استفاده است."  
)  


await query.edit_message_text(  
    message,  
    reply_markup=main_menu()  
)

=========================

کنترل دکمه ها

=========================

async def button_handler(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

query = update.callback_query  

await query.answer()  


action = query.data  


if action == "prices":  

    await show_prices(query)  


elif action == "vip":  

    await show_vip(query)  


elif action == "help":  

    await show_help(query)  


elif action == "alerts":  

    await query.edit_message_text(  
        "🚨 بخش هشدار قیمت\n\n"  
        "این قسمت در مرحله بعدی با سیستم دکمه‌ای کامل می‌شود.",  
        reply_markup=main_menu()  
    )  


elif action == "compare":  

    await query.edit_message_text(  
        "📊 مقایسه بازار به زودی فعال می‌شود.",  
        reply_markup=main_menu()  
    )  


elif action == "calculator":  

    await query.edit_message_text(  
        "🧮 محاسبه‌گر به زودی فعال می‌شود.",  
        reply_markup=main_menu()  
    )  


elif action == "mygold":  

    await query.edit_message_text(  
        "💎 طلاهای من\n\n"  
        "هنوز کیف پول طلا فعال نشده است.",  
        reply_markup=main_menu()  
    )

=========================

هشدار قیمت (نسخه فعلی)

=========================

async def alert(update: Update, context: ContextTypes.DEFAULT_TYPE):

chat_id = update.effective_chat.id  

args = context.args  


if len(args) != 2:  

    await update.message.reply_text(  
        "فرمت درست:\n\n"  
        "/alert BTC 70000"  
    )  

    return  



coin = args[0].upper()  


if coin not in COIN_MAP:  

    await update.message.reply_text(  
        "❌ ارز نامعتبر است."  
    )  

    return  



try:  

    target = float(args[1])  


except:  

    await update.message.reply_text(  
        "❌ قیمت باید عدد باشد."  
    )  

    return  



alerts = load_alerts()  


count = len(  
    [  
        a for a in alerts  
        if a["chat_id"] == chat_id  
    ]  
)  


if not is_vip(chat_id) and count >= FREE_ALERT_LIMIT:  

    await update.message.reply_text(  
        "⚠️ نسخه رایگان فقط یک هشدار فعال دارد.\n\n"  
        "برای هشدار نامحدود VIP شوید."  
    )  

    return  



alerts.append({  

    "chat_id": chat_id,  
    "coin": coin,  
    "target_price": target  

})  


save_alerts(alerts)  


await update.message.reply_text(  
    "✅ هشدار ثبت شد\n\n"  
    f"{coin} → {target:,}$"  
)

=========================

مشاهده هشدارها

=========================

async def myalerts(update: Update, context: ContextTypes.DEFAULT_TYPE):

alerts = load_alerts()  


user_alerts = [  

    a for a in alerts  
    if a["chat_id"] == update.effective_chat.id  

]  


if not user_alerts:  

    await update.message.reply_text(  
        "هیچ هشداری ندارید."  
    )  

    return  



text = "🔔 هشدارهای شما:\n\n"  


for a in user_alerts:  

    text += (  
        f"• {a['coin']} "  
        f"{a['target_price']:,}$\n"  
    )  


await update.message.reply_text(text)

=========================

گزارش روزانه

=========================

async def dailyreport(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

chat_id = update.effective_chat.id  


if not is_vip(chat_id):  

    await update.message.reply_text(  
        "⭐ گزارش روزانه فقط برای VIP فعال است."  
    )  

    return  



args = context.args  


if not args:  

    await update.message.reply_text(  
        "/dailyreport on\n"  
        "/dailyreport off"  
    )  

    return  



subs = load_daily_subs()  



if args[0] == "on":  

    if chat_id not in subs:  

        subs.append(chat_id)  

        save_daily_subs(subs)  


    await update.message.reply_text(  
        "✅ گزارش روزانه فعال شد."  
    )  


else:  

    if chat_id in subs:  

        subs.remove(chat_id)  

        save_daily_subs(subs)  


    await update.message.reply_text(  
        "❌ گزارش روزانه خاموش شد."  
    )

=========================

VIP

=========================

async def vip(update: Update, context: ContextTypes.DEFAULT_TYPE):

if is_vip(update.effective_chat.id):  

    await update.message.reply_text(  
        "🌟 شما عضو VIP هستید."  
    )  

    return  



await update.message.reply_text(  
    "⭐ اشتراک VIP طلایار\n\n"  

    "امکانات:\n"  
    "🔔 هشدار نامحدود\n"  
    "📊 گزارش روزانه\n"  
    "📈 تحلیل بازار\n\n"  

    "برای خرید با پشتیبانی ارتباط بگیرید."  
)

=========================

بررسی هشدارها

=========================

async def check_alerts(
context: ContextTypes.DEFAULT_TYPE
):

alerts = load_alerts()  


if not alerts:  

    return  



try:  

    data = fetch_crypto_price()  


except Exception as e:  

    logging.error(e)  

    return  



remaining = []  



for alert_item in alerts:  


    current = data.get(  
        COIN_MAP[alert_item["coin"]],  
        {}  
    ).get("usd")  



    if current and current >= alert_item["target_price"]:  


        await context.bot.send_message(  

            chat_id=alert_item["chat_id"],  

            text=(  
                "🚨 هشدار قیمت\n\n"  
                f"{alert_item['coin']}\n"  
                f"قیمت فعلی: {current:,}$"  
            )  

        )  


    else:  

        remaining.append(alert_item)  



save_alerts(remaining)

=========================

راهنما

=========================

async def help_command(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

await update.message.reply_text(  
    "📚 راهنمای طلایار\n\n"  

    "از منوی ربات استفاده کنید.\n\n"  

    "💰 قیمت لحظه‌ای\n"  
    "🚨 هشدار قیمت\n"  
    "⭐ VIP\n"  
    "📊 تحلیل بازار\n\n"  

    "برای شروع /start را بزنید."  
)

=========================

گزارش صبحگاهی

=========================

async def send_daily_reports(
context: ContextTypes.DEFAULT_TYPE
):

subs = load_daily_subs()  


if not subs:  
    return  



try:  

    data = fetch_crypto_price()  


    message = (  
        "☀️ گزارش صبحگاهی طلایار\n\n"  

        f"₿ بیت‌کوین: "  
        f"{data['bitcoin']['usd']:,}$\n\n"  

        f"Ξ اتریوم: "  
        f"{data['ethereum']['usd']:,}$\n\n"  

        f"₮ تتر: "  
        f"{data['tether']['usd']}$\n\n"  

        "🥇 قیمت طلای ایران به زودی اضافه می‌شود."  
    )  


except Exception:  

    return  



for chat_id in subs:  

    try:  

        await context.bot.send_message(  

            chat_id=chat_id,  

            text=message  

        )  

    except Exception as e:  

        logging.error(e)

=========================

مدیریت VIP توسط ادمین

=========================

ADMIN_CHAT_ID = os.environ.get(
"ADMIN_CHAT_ID"
)

async def addvip(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

if str(update.effective_chat.id) != str(ADMIN_CHAT_ID):  

    return  



if len(context.args) != 1:  

    await update.message.reply_text(  
        "فرمت:\n/addvip CHAT_ID"  
    )  

    return  



user_id = int(context.args[0])  


vips = load_vips()  



if user_id not in vips:  

    vips.append(user_id)  

    save_json(  
        VIP_FILE,  
        vips  
    )  



await update.message.reply_text(  
    "✅ کاربر VIP شد."  
)

=========================

نمایش آیدی

=========================

async def myid(
update: Update,
context: ContextTypes.DEFAULT_TYPE
):

await update.message.reply_text(  

    f"Chat ID:\n{update.effective_chat.id}"  

)

=========================

اجرای ربات

=========================

def main():

if not BOT_TOKEN:  

    logging.error(  
        "BOT_TOKEN پیدا نشد"  
    )  

    return  



app = (  
    Application  
    .builder()  
    .token(BOT_TOKEN)  
    .build()  
)  



# Commands  

app.add_handler(  
    CommandHandler(  
        "start",  
        start  
    )  
)  


app.add_handler(  
    CommandHandler(  
        "alert",  
        alert  
    )  
)  


app.add_handler(  
    CommandHandler(  
        "myalerts",  
        myalerts  
    )  
)  


app.add_handler(  
    CommandHandler(  
        "dailyreport",  
        dailyreport  
    )  
)  


app.add_handler(  
    CommandHandler(  
        "vip",  
        vip  
    )  
)  


app.add_handler(  
    CommandHandler(  
        "help",  
        help_command  
    )  
)  


app.add_handler(  
    CommandHandler(  
        "addvip",  
        addvip  
    )  
)  


app.add_handler(  
    CommandHandler(  
        "myid",  
        myid  
    )  
)  



# دکمه های منو  

app.add_handler(  

    CallbackQueryHandler(  
        button_handler  
    )  

)  



# بررسی هشدارها  

app.job_queue.run_repeating(  

    check_alerts,  

    interval=300,  

    first=10  

)  



# گزارش روزانه ساعت ۹  

app.job_queue.run_daily(  

    send_daily_reports,  

    time=time(  
        hour=9,  
        minute=0,  
        tzinfo=IRAN_TZ  
    )  

)  



app.run_polling()

if name == "main":

main()
