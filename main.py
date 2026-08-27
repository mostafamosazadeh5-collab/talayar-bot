#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
طلایار v12.0 Navasan Intelligence — دستیار هوشمند بازار طلا
نسخهٔ فروش حرفه‌ای:
  ✅ BRS API واقعی (طلا، دلار، ارز، کریپتو)
  ✅ انس جهانی (XAU/USD)
  ✅ نمودار تکنیکال حرفه‌ای همه دارایی‌های اصلی + کش بهینه
  ✅ Trial VIP ۳ روزه
  ✅ VIP + پرداخت + پنل ادمین
  ✅ هشدار قیمت (عددی + درصدی + تکرارشونده)
  ✅ گزارش روزانه
  ✅ کندل + EMA20/EMA50 + RSI14 + حمایت/مقاومت در ۲۴ساعت، ۷روز و ۳۰روز
  ✅ ماشین حساب طلای کامل
  ✅ تحلیل هوشمند VIP متصل به منوی اصلی
  ✅ Watchlist VIP با سقف ۵ دارایی
  ✅ پرداخت دوحالته زرین‌پال + رسید دستی
  ✅ دیتابیس SQLite مرتب
  ✅ Referral ضدتقلب + Progress + Source Tracking + Share Engine
  ✅ پنل مدیریت پیشرفته با دسترسی دکمه‌ای
  ✅ Runtime License Lock برای جلوگیری از اجرای مستقیم سورس کپی‌شده
  ✅ خوشامدگویی حرفه‌ای و وضعیت حساب در /start
  ✅ یادآوری هوشمند تمدید VIP (۳ روز، ۱ روز، ۶ ساعت و انقضا)
  ✅ تحلیل الگوریتمی پیشرفته RSI/EMA/MACD/حمایت و مقاومت
  ✅ معرفی توسعه‌دهنده + پشتیبانی داخلی + سفارش ربات اختصاصی
  ✅ دستورات /help /gold /price /version
  ✅ رفع خطای دکمه‌های نمودار روی Photo Message + لغو نتایج قدیمی
"""

import os
import re
import html
import json
import uuid
import hashlib
import hmac
import socket
import shutil
import sqlite3
import logging
import threading
import time
import asyncio
import base64
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from io import BytesIO
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse
from zoneinfo import ZoneInfo

import requests
import yfinance as yf
import mplfinance as mpf
import pandas as pd
import matplotlib
matplotlib.use("Agg")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, WebAppInfo
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# ═══════════════════════════════════════════════════════════════
# CONFIG
# ═══════════════════════════════════════════════════════════════
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
BRS_API_URL = os.environ.get("BRS_API_URL", "").strip()
ADMIN_ID = os.environ.get("ADMIN_ID", "").strip()
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "WAHL4").strip().lstrip("@")
APP_VERSION = "13.5.0"
BUILD_TAG = "MINIAPP-PRO-LIGHT-FREE-VIP"
DEVELOPER_NAME = os.environ.get("DEVELOPER_NAME", "مصطفی موسی‌زاده").strip()
DEVELOPER_USERNAME = os.environ.get("DEVELOPER_USERNAME", "WAHL4").strip().lstrip("@")
AUTHORIZED_ADMIN_ID = "7361040390"
LICENSE_KEY = os.environ.get("LICENSE_KEY", "").strip()
LICENSE_ENFORCE = os.environ.get("LICENSE_ENFORCE", "1").strip().lower() not in {"0", "false", "off", "no"}
LICENSE_REBIND = os.environ.get("LICENSE_REBIND", "0").strip().lower() in {"1", "true", "on", "yes"}
LICENSE_EXPECTED_SHA256 = "807a2ca400cdb1a0dc72cd04f09d8b72721e1b37466bae4b570b59efaabbe2d3"
LICENSE_CONTEXT = "TALAYAR-V11.4"  # production-license compatibility; do not change without re-issuing key
REFERRAL_MIN_AGE_SECONDS = 90
REFERRAL_MIN_ACTIONS = 3
REFERRAL_MIN_DISTINCT_ACTIONS = 2
REFERRAL_SUSPICIOUS_WINDOW_SECONDS = 600
REFERRAL_SUSPICIOUS_STARTS = 12
REF_ACTION_PRICE = 1
REF_ACTION_CHART = 2
REF_ACTION_ALERT = 4
REF_ACTION_ANALYSIS = 8
REF_ACTION_DAILY = 16
STARTED_AT_MONO = time.monotonic()
PAYMENT_INFO = os.environ.get(
    "PAYMENT_INFO",
    f"برای دریافت شماره کارت و هماهنگی پرداخت به @{ADMIN_USERNAME} پیام بدهید.",
)
DATA_DIR = os.environ.get("DATA_DIR", "/data" if os.path.isdir("/data") else ".")
DB_PATH = os.path.join(DATA_DIR, "talayar_v3.db")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

API_TIMEOUT = 20
CACHE_TTL_SECONDS = 20
CHART_CACHE_TTL_SECONDS = 120
CHART_CACHE_MAX_ITEMS = 16
FREE_ALERT_LIMIT = 1
ALERT_CHECK_INTERVAL = 60
HISTORY_SAVE_INTERVAL = 300
HISTORY_RETENTION_DAYS = int(os.environ.get("HISTORY_RETENTION_DAYS", "365"))
MESGHAL_18_EQUIV_FACTOR = 4.3318
MINIAPP_AUTH_MAX_AGE_SECONDS = 86400
MINIAPP_MAX_CANDLES = 120
MINIAPP_OVERVIEW_CACHE_SECONDS = 15
NAVASAN_MIN_POINTS = 24
NAVASAN_PRO_POINTS = 96
SMART_ALERT_COOLDOWN_SECONDS = 1800
TROY_OUNCE_GRAMS = 31.1034768
COIN_SPECS = {
    # gross grams * fineness; standard Iranian gold coin specs
    "emami": {"label": "سکه امامی", "gross_g": 8.133, "fineness": 0.900},
    "half": {"label": "نیم‌سکه", "gross_g": 4.0665, "fineness": 0.900},
    "quarter": {"label": "ربع‌سکه", "gross_g": 2.03325, "fineness": 0.900},
}
VIP_MAINTENANCE_INTERVAL = 10800  # هر ۳ ساعت: یادآوری VIP + پشتیبان روزانه
WATCHLIST_VIP_LIMIT = 5
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
VIP_PRICE_30 = os.environ.get("VIP_PRICE_30", "69,000")
VIP_PRICE_90 = os.environ.get("VIP_PRICE_90", "249,000")
ZARINPAL_MERCHANT_ID = os.environ.get("ZARINPAL_MERCHANT_ID", "").strip()
PUBLIC_BASE_URL = os.environ.get("PUBLIC_BASE_URL", "").strip().rstrip("/")
if not PUBLIC_BASE_URL and os.environ.get("RAILWAY_PUBLIC_DOMAIN"):
    PUBLIC_BASE_URL = f"https://{os.environ['RAILWAY_PUBLIC_DOMAIN'].strip().strip('/')}"
ZARINPAL_CALLBACK_URL = os.environ.get("ZARINPAL_CALLBACK_URL", "").strip()
if not ZARINPAL_CALLBACK_URL and PUBLIC_BASE_URL:
    ZARINPAL_CALLBACK_URL = f"{PUBLIC_BASE_URL}/payment/callback"
PAYMENT_HTTP_PORT = int(os.environ.get("PORT", "8080"))
ZARINPAL_REQUEST_URL = os.environ.get(
    "ZARINPAL_REQUEST_URL", "https://api.zarinpal.com/pg/v4/payment/request.json"
)
ZARINPAL_VERIFY_URL = os.environ.get(
    "ZARINPAL_VERIFY_URL", "https://api.zarinpal.com/pg/v4/payment/verify.json"
)
ZARINPAL_STARTPAY_URL = os.environ.get(
    "ZARINPAL_STARTPAY_URL", "https://www.zarinpal.com/pg/StartPay/"
)
DISCLAIMER = "قیمت‌ها ممکن است با بازار اختلاف یا تأخیر داشته باشند و توصیه خرید یا فروش نیستند."

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("talayar")

_market_cache = {"data": None, "saved_at": 0.0}
_db_lock = threading.Lock()
_chart_cache = {}
_chart_cache_lock = threading.Lock()
_chart_render_semaphore = asyncio.Semaphore(1)

# ═══════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════
class Database:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.path, check_same_thread=False, timeout=30)

    def _init_db(self):
        with self._conn() as c:
            c.execute("PRAGMA journal_mode=WAL")
            c.execute("PRAGMA synchronous=NORMAL")
            c.execute("PRAGMA busy_timeout=30000")
            c.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    chat_id INTEGER,
                    joined_at TEXT,
                    last_seen TEXT,
                    referrer_id INTEGER,
                    referral_rewarded INTEGER DEFAULT 0,
                    activity_score INTEGER DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS vip_users (
                    user_id INTEGER PRIMARY KEY,
                    expires_at TEXT,
                    plan_days INTEGER,
                    added_at TEXT,
                    source TEXT,
                    last_reminder TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS alerts (
                    id TEXT PRIMARY KEY,
                    chat_id INTEGER,
                    user_id INTEGER,
                    type TEXT DEFAULT 'price',
                    asset TEXT,
                    condition TEXT,
                    mode TEXT DEFAULT 'once',
                    armed INTEGER DEFAULT 1,
                    target REAL,
                    percent REAL,
                    baseline REAL,
                    created_at TEXT,
                    updated_at TEXT
                );
                CREATE TABLE IF NOT EXISTS daily_subs (
                    user_id INTEGER PRIMARY KEY,
                    chat_id INTEGER,
                    time TEXT,
                    active INTEGER DEFAULT 1,
                    last_sent TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS orders (
                    order_id TEXT PRIMARY KEY,
                    user_id INTEGER,
                    plan INTEGER,
                    amount TEXT,
                    status TEXT DEFAULT 'pending',
                    created_at TEXT,
                    receipt_file_id TEXT,
                    reviewed_at TEXT
                );
                CREATE TABLE IF NOT EXISTS referrals (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    referred_id INTEGER UNIQUE,
                    started_at TEXT,
                    qualified INTEGER DEFAULT 0,
                    qualified_at TEXT
                );
                CREATE TABLE IF NOT EXISTS referral_rewards (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    referrer_id INTEGER,
                    reward_type TEXT,
                    amount INTEGER,
                    days INTEGER,
                    created_at TEXT
                );
                CREATE TABLE IF NOT EXISTS watchlist (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    asset_key TEXT,
                    created_at TEXT,
                    UNIQUE(user_id, asset_key)
                );
                CREATE TABLE IF NOT EXISTS price_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_key TEXT,
                    price REAL,
                    unit TEXT,
                    ts INTEGER
                );
                CREATE TABLE IF NOT EXISTS bot_state (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS bubble_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    asset_key TEXT NOT NULL,
                    bubble_percent REAL,
                    fair_value REAL,
                    market_price REAL,
                    ts INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS smart_alerts (
                    id TEXT PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    chat_id INTEGER NOT NULL,
                    asset_key TEXT NOT NULL,
                    rule TEXT NOT NULL,
                    active INTEGER DEFAULT 1,
                    last_triggered INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, asset_key, rule)
                );
            """)
            self._ensure_column(c, "orders", "authority", "TEXT")
            self._ensure_column(c, "orders", "ref_id", "TEXT")
            self._ensure_column(c, "orders", "payment_method", "TEXT DEFAULT 'manual'")
            self._ensure_column(c, "referrals", "source", "TEXT DEFAULT 'direct'")
            self._ensure_column(c, "referrals", "activity_mask", "INTEGER DEFAULT 0")
            self._ensure_column(c, "referrals", "activity_count", "INTEGER DEFAULT 0")
            self._ensure_column(c, "referrals", "last_activity_at", "TEXT DEFAULT ''")
            self._ensure_column(c, "referrals", "flagged", "INTEGER DEFAULT 0")
            self._ensure_column(c, "referrals", "flag_reason", "TEXT DEFAULT ''")
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_authority ON orders(authority) WHERE authority IS NOT NULL")
            c.execute("CREATE INDEX IF NOT EXISTS idx_price_history_asset_ts ON price_history(asset_key, ts)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_bubble_history_asset_ts ON bubble_history(asset_key, ts)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_smart_alerts_user ON smart_alerts(user_id, active)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_referrals_referrer_started ON referrals(referrer_id, started_at)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_referrals_source ON referrals(source)")

    @staticmethod
    def _ensure_column(connection, table, column, definition):
        columns = {row[1] for row in connection.execute(f"PRAGMA table_info({table})")}
        if column not in columns:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def add_user(self, user_id, username, first_name, chat_id, joined_at, referrer_id=None):
        with self._conn() as c:
            c.execute("""
                INSERT OR IGNORE INTO users (user_id, username, first_name, chat_id, joined_at, last_seen, referrer_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, username or "", first_name or "", chat_id, joined_at, joined_at, referrer_id))

    def get_user(self, user_id):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def update_last_seen(self, user_id):
        with self._conn() as c:
            c.execute("UPDATE users SET last_seen = ? WHERE user_id = ?",
                      (datetime.now(timezone.utc).isoformat(), user_id))

    def set_referral_rewarded(self, user_id):
        with self._conn() as c:
            c.execute("UPDATE users SET referral_rewarded = 1 WHERE user_id = ?", (user_id,))

    def increment_activity(self, user_id):
        with self._conn() as c:
            c.execute("UPDATE users SET activity_score = activity_score + 1 WHERE user_id = ?", (user_id,))

    def add_vip(self, user_id, days, source="admin"):
        now = datetime.now(timezone.utc)
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            old = c.execute("SELECT * FROM vip_users WHERE user_id = ?", (user_id,)).fetchone()
            start = now
            if old:
                try:
                    old_dt = datetime.fromisoformat(old["expires_at"])
                    if old_dt > now:
                        start = old_dt
                except Exception:
                    pass
            expires = (start + timedelta(days=max(1, int(days)))).isoformat()
            c.execute("""
                INSERT INTO vip_users (user_id, expires_at, plan_days, added_at, source, last_reminder)
                VALUES (?, ?, ?, ?, ?, '')
                ON CONFLICT(user_id) DO UPDATE SET
                    expires_at=excluded.expires_at,
                    plan_days=excluded.plan_days,
                    added_at=excluded.added_at,
                    source=excluded.source,
                    last_reminder=''
            """, (user_id, expires, int(days), now.isoformat(), source))

    def add_trial_vip(self, user_id):
        with self._conn() as c:
            if c.execute("SELECT 1 FROM vip_users WHERE user_id = ?", (user_id,)).fetchone():
                return False
            now = datetime.now(timezone.utc)
            c.execute("""
                INSERT INTO vip_users (user_id, expires_at, plan_days, added_at, source, last_reminder)
                VALUES (?, ?, ?, ?, ?, '')
            """, (user_id, (now + timedelta(days=3)).isoformat(), 3, now.isoformat(), "trial"))
            return True

    def remove_vip(self, user_id):
        with self._conn() as c:
            cursor = c.execute("DELETE FROM vip_users WHERE user_id = ?", (user_id,))
            return cursor.rowcount > 0

    def get_vip(self, user_id):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT * FROM vip_users WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def update_vip_reminder(self, user_id, reminder):
        with self._conn() as c:
            c.execute("UPDATE vip_users SET last_reminder = ? WHERE user_id = ?", (reminder, user_id))

    def create_alert(self, alert):
        with self._conn() as c:
            c.execute("""
                INSERT INTO alerts (id, chat_id, user_id, type, asset, condition, mode, armed, target, percent, baseline, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert["id"], alert["chat_id"], alert["user_id"], alert.get("type", "price"),
                alert["asset"], alert["condition"], alert.get("mode", "once"),
                1 if alert.get("armed", True) else 0,
                alert.get("target"), alert.get("percent"), alert.get("baseline"),
                alert["created_at"], alert.get("updated_at", alert["created_at"])
            ))

    def load_alerts(self):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM alerts").fetchall()
            return [dict(r) for r in rows]

    def user_alerts(self, user_id):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM alerts WHERE user_id = ?", (user_id,)).fetchall()
            return [dict(r) for r in rows]

    def delete_user_alerts(self, user_id):
        with self._conn() as c:
            c.execute("DELETE FROM alerts WHERE user_id = ?", (user_id,))

    def delete_alert(self, alert_id, user_id):
        with self._conn() as c:
            cursor = c.execute("DELETE FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id))
            return cursor.rowcount > 0

    def update_alert(self, alert_id, user_id, changes):
        with self._conn() as c:
            sets = ", ".join(f"{k} = ?" for k in changes)
            vals = list(changes.values()) + [alert_id, user_id]
            cursor = c.execute(f"UPDATE alerts SET {sets} WHERE id = ? AND user_id = ?", vals)
            return cursor.rowcount > 0

    def save_alerts(self, alerts):
        with self._conn() as c:
            c.execute("DELETE FROM alerts")
            for a in alerts:
                c.execute("""
                    INSERT INTO alerts (id, chat_id, user_id, type, asset, condition, mode, armed, target, percent, baseline, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    a["id"], a["chat_id"], a["user_id"], a.get("type", "price"),
                    a["asset"], a["condition"], a.get("mode", "once"),
                    1 if a.get("armed", True) else 0,
                    a.get("target"), a.get("percent"), a.get("baseline"),
                    a["created_at"], a.get("updated_at", a["created_at"])
                ))

    def get_daily_sub(self, user_id):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT * FROM daily_subs WHERE user_id = ?", (user_id,)).fetchone()
            return dict(row) if row else None

    def set_daily_sub(self, user_id, chat_id, report_time, active=True):
        with self._conn() as c:
            c.execute("""
                INSERT INTO daily_subs (user_id, chat_id, time, active, last_sent)
                VALUES (?, ?, ?, ?, '')
                ON CONFLICT(user_id) DO UPDATE SET
                    chat_id=excluded.chat_id, time=excluded.time, active=excluded.active
            """, (user_id, chat_id, report_time, 1 if active else 0))

    def load_daily_subs(self):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM daily_subs").fetchall()
            return [dict(r) for r in rows]

    def create_order(self, order_id, user_id, plan, amount, status, created_at,
                     payment_method="manual", authority=None):
        with self._conn() as c:
            c.execute("""
                INSERT INTO orders
                    (order_id, user_id, plan, amount, status, created_at, payment_method, authority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (order_id, user_id, plan, amount, status, created_at, payment_method, authority))

    def get_pending_order(self, user_id):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            row = c.execute("""
                SELECT * FROM orders WHERE user_id = ? AND status IN ('pending', 'pending_gateway')
                ORDER BY created_at DESC LIMIT 1
            """, (user_id,)).fetchone()
            return dict(row) if row else None

    def get_order_by_id(self, order_id):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT * FROM orders WHERE order_id = ?", (order_id,)).fetchone()
            return dict(row) if row else None

    def get_order_by_authority(self, authority):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT * FROM orders WHERE authority = ?", (authority,)).fetchone()
            return dict(row) if row else None

    def set_order_authority(self, order_id, authority):
        with self._conn() as c:
            cursor = c.execute("UPDATE orders SET authority = ? WHERE order_id = ?", (authority, order_id))
            return cursor.rowcount > 0

    def approve_gateway_order(self, authority, ref_id):
        with _db_lock:
            with self._conn() as c:
                c.row_factory = sqlite3.Row
                row = c.execute("SELECT * FROM orders WHERE authority = ?", (authority,)).fetchone()
                if not row:
                    return None, False
                order = dict(row)
                if order.get("status") == "approved":
                    return order, False
                if order.get("status") != "pending_gateway":
                    return order, False

                now = datetime.now(timezone.utc)
                old = c.execute("SELECT * FROM vip_users WHERE user_id = ?", (order["user_id"],)).fetchone()
                start = now
                if old and old["expires_at"]:
                    try:
                        old_dt = datetime.fromisoformat(old["expires_at"])
                        if old_dt > now:
                            start = old_dt
                    except (TypeError, ValueError):
                        pass
                expires = (start + timedelta(days=max(1, int(order["plan"])))).isoformat()
                c.execute("""
                    INSERT INTO vip_users (user_id, expires_at, plan_days, added_at, source, last_reminder)
                    VALUES (?, ?, ?, ?, ?, '')
                    ON CONFLICT(user_id) DO UPDATE SET
                        expires_at=excluded.expires_at,
                        plan_days=excluded.plan_days,
                        added_at=excluded.added_at,
                        source=excluded.source,
                        last_reminder=''
                """, (
                    order["user_id"], expires, int(order["plan"]), now.isoformat(),
                    f"zarinpal:{order['order_id']}",
                ))
                reviewed_at = datetime.now(timezone.utc).isoformat()
                c.execute(
                    "UPDATE orders SET status = 'approved', ref_id = ?, reviewed_at = ? WHERE order_id = ?",
                    (str(ref_id), reviewed_at, order["order_id"]),
                )
                order.update({"status": "approved", "ref_id": str(ref_id), "reviewed_at": reviewed_at})
                return order, True

    def update_order_status(self, order_id, status, reviewed_at=None):
        with self._conn() as c:
            if reviewed_at:
                c.execute("UPDATE orders SET status = ?, reviewed_at = ? WHERE order_id = ?",
                          (status, reviewed_at, order_id))
            else:
                c.execute("UPDATE orders SET status = ? WHERE order_id = ?", (status, order_id))

    def load_orders(self):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM orders").fetchall()
            return [dict(r) for r in rows]

    def register_referral(self, new_user_id, referrer_id, source="direct"):
        if str(new_user_id) == str(referrer_id):
            return False
        source = (source or "direct")[:24]
        now = datetime.now(timezone.utc)
        cutoff = (now - timedelta(seconds=REFERRAL_SUSPICIOUS_WINDOW_SECONDS)).isoformat()
        with _db_lock:
            with self._conn() as c:
                c.row_factory = sqlite3.Row
                if not c.execute("SELECT 1 FROM users WHERE user_id = ?", (referrer_id,)).fetchone():
                    return False
                recent_starts = c.execute(
                    "SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND started_at >= ?",
                    (referrer_id, cutoff),
                ).fetchone()[0]
                flagged = 1 if recent_starts >= REFERRAL_SUSPICIOUS_STARTS else 0
                reason = "rapid_referral_starts" if flagged else ""
                try:
                    c.execute("""
                        INSERT INTO referrals
                            (referrer_id, referred_id, started_at, qualified, qualified_at,
                             source, activity_mask, activity_count, last_activity_at, flagged, flag_reason)
                        VALUES (?, ?, ?, 0, NULL, ?, 0, 0, '', ?, ?)
                    """, (referrer_id, new_user_id, now.isoformat(), source, flagged, reason))
                    return True
                except sqlite3.IntegrityError:
                    return False

    def get_referral(self, referred_id):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT * FROM referrals WHERE referred_id = ?", (referred_id,)).fetchone()
            return dict(row) if row else None

    def record_referral_activity(self, referred_id, action_bit):
        """ثبت تعامل معنادار Referral؛ با bitmask جلوی کلیک تکراری یک نوع تعامل گرفته می‌شود."""
        action_bit = int(action_bit or 0)
        if action_bit <= 0:
            return None
        with _db_lock:
            with self._conn() as c:
                c.row_factory = sqlite3.Row
                row = c.execute(
                    "SELECT * FROM referrals WHERE referred_id = ? AND qualified = 0",
                    (referred_id,),
                ).fetchone()
                if not row:
                    return None
                mask = int(row["activity_mask"] or 0) | action_bit
                count = int(row["activity_count"] or 0) + 1
                now = datetime.now(timezone.utc).isoformat()
                c.execute(
                    "UPDATE referrals SET activity_mask = ?, activity_count = ?, last_activity_at = ? WHERE referred_id = ?",
                    (mask, count, now, referred_id),
                )
                data = dict(row)
                data.update({"activity_mask": mask, "activity_count": count, "last_activity_at": now})
                return data

    def qualify_referral(self, referred_id, allow_flagged=False):
        with _db_lock:
            with self._conn() as c:
                c.row_factory = sqlite3.Row
                row = c.execute("SELECT * FROM referrals WHERE referred_id = ? AND qualified = 0", (referred_id,)).fetchone()
                if not row:
                    return None
                if int(row["flagged"] or 0) and not allow_flagged:
                    return None
                now = datetime.now(timezone.utc).isoformat()
                cursor = c.execute(
                    "UPDATE referrals SET qualified = 1, qualified_at = ?, flagged = 0, flag_reason = '' WHERE referred_id = ? AND qualified = 0",
                    (now, referred_id),
                )
                if cursor.rowcount != 1:
                    return None
                data = dict(row)
                data.update({"qualified": 1, "qualified_at": now, "flagged": 0, "flag_reason": ""})
                return data

    def qualified_count(self, referrer_id):
        with self._conn() as c:
            row = c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND qualified = 1", (referrer_id,)).fetchone()
            return row[0]

    def referral_counts(self, referrer_id):
        with self._conn() as c:
            row = c.execute("""
                SELECT COUNT(*) AS total,
                       SUM(CASE WHEN qualified = 1 THEN 1 ELSE 0 END) AS qualified,
                       SUM(CASE WHEN qualified = 0 THEN 1 ELSE 0 END) AS pending,
                       SUM(CASE WHEN flagged = 1 THEN 1 ELSE 0 END) AS flagged
                FROM referrals WHERE referrer_id = ?
            """, (referrer_id,)).fetchone()
            return {
                "total": int(row[0] or 0), "qualified": int(row[1] or 0),
                "pending": int(row[2] or 0), "flagged": int(row[3] or 0),
            }

    def referral_leaderboard(self, limit=10):
        with self._conn() as c:
            rows = c.execute("""
                SELECT referrer_id, COUNT(*) as cnt FROM referrals
                WHERE qualified = 1 GROUP BY referrer_id ORDER BY cnt DESC LIMIT ?
            """, (limit,)).fetchall()
            return rows

    def referral_source_stats(self):
        with self._conn() as c:
            rows = c.execute("""
                SELECT COALESCE(source, 'direct') AS source,
                       COUNT(*) AS total,
                       SUM(CASE WHEN qualified = 1 THEN 1 ELSE 0 END) AS qualified
                FROM referrals GROUP BY COALESCE(source, 'direct') ORDER BY total DESC
            """).fetchall()
            return [(str(r[0]), int(r[1] or 0), int(r[2] or 0)) for r in rows]

    def suspicious_referrals(self, limit=20):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("""
                SELECT * FROM referrals WHERE flagged = 1 AND qualified = 0
                ORDER BY started_at DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    def add_referral_reward(self, referrer_id, reward_type, amount, days):
        """Idempotent: یک سطح جایزه برای هر معرف فقط یک بار ثبت می‌شود."""
        with _db_lock:
            with self._conn() as c:
                exists = c.execute(
                    "SELECT 1 FROM referral_rewards WHERE referrer_id = ? AND reward_type = ? AND days = ?",
                    (referrer_id, reward_type, days),
                ).fetchone()
                if exists:
                    return False
                c.execute("""
                    INSERT INTO referral_rewards (referrer_id, reward_type, amount, days, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (referrer_id, reward_type, amount, days, datetime.now(timezone.utc).isoformat()))
                return True

    def get_referral_rewards(self, referrer_id):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM referral_rewards WHERE referrer_id = ?", (referrer_id,)).fetchall()
            return [dict(r) for r in rows]

    def pending_referrals_for_review(self, limit=100):
        """دعوت‌های آمادهٔ بررسی خودکار؛ Query سبک و محدود برای Job پنج‌دقیقه‌ای."""
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("""
                SELECT * FROM referrals
                WHERE qualified = 0 AND flagged = 0 AND activity_count >= ?
                ORDER BY started_at ASC LIMIT ?
            """, (REFERRAL_MIN_ACTIONS, int(limit))).fetchall()
            return [dict(r) for r in rows]

    def recent_users(self, limit=10):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM users ORDER BY last_seen DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def recent_vips(self, limit=10):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM vip_users ORDER BY added_at DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]

    def add_watchlist(self, user_id, asset_key, limit=WATCHLIST_VIP_LIMIT):
        with _db_lock:
            with self._conn() as c:
                exists = c.execute(
                    "SELECT 1 FROM watchlist WHERE user_id = ? AND asset_key = ?",
                    (user_id, asset_key),
                ).fetchone()
                if exists:
                    return "duplicate"
                count = c.execute("SELECT COUNT(*) FROM watchlist WHERE user_id = ?", (user_id,)).fetchone()[0]
                if count >= limit:
                    return "limit"
                c.execute("INSERT INTO watchlist (user_id, asset_key, created_at) VALUES (?, ?, ?)",
                          (user_id, asset_key, datetime.now(timezone.utc).isoformat()))
                return "added"

    def remove_watchlist(self, user_id, asset_key):
        with self._conn() as c:
            cursor = c.execute("DELETE FROM watchlist WHERE user_id = ? AND asset_key = ?", (user_id, asset_key))
            return cursor.rowcount > 0

    def get_watchlist(self, user_id):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM watchlist WHERE user_id = ? ORDER BY id", (user_id,)).fetchall()
            return [dict(r) for r in rows]

    def save_price_history(self, asset_key, price, unit, ts):
        with self._conn() as c:
            c.execute("INSERT INTO price_history (asset_key, price, unit, ts) VALUES (?, ?, ?, ?)",
                      (asset_key, price, unit, ts))

    def get_price_history(self, asset_key, hours):
        cutoff = int(time.time()) - hours * 3600
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT * FROM price_history WHERE asset_key = ? AND ts >= ? ORDER BY ts",
                (asset_key, cutoff)
            ).fetchall()
            return [dict(r) for r in rows]

    def prune_price_history(self, days=7):
        cutoff = int(time.time()) - days * 86400
        with self._conn() as c:
            c.execute("DELETE FROM price_history WHERE ts < ?", (cutoff,))

    def save_bubble_history(self, asset_key, bubble_percent, fair_value, market_price, ts):
        with self._conn() as c:
            c.execute(
                "INSERT INTO bubble_history (asset_key, bubble_percent, fair_value, market_price, ts) VALUES (?, ?, ?, ?, ?)",
                (asset_key, float(bubble_percent), float(fair_value), float(market_price), int(ts)),
            )

    def get_bubble_history(self, asset_key, hours=720):
        cutoff = int(time.time()) - int(hours * 3600)
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT * FROM bubble_history WHERE asset_key = ? AND ts >= ? ORDER BY ts",
                (asset_key, cutoff),
            ).fetchall()
            return [dict(r) for r in rows]

    def prune_bubble_history(self, days=35):
        cutoff = int(time.time()) - int(days * 86400)
        with self._conn() as c:
            c.execute("DELETE FROM bubble_history WHERE ts < ?", (cutoff,))

    def add_smart_alert(self, user_id, chat_id, asset_key, rule):
        alert_id = uuid.uuid4().hex[:16]
        with self._conn() as c:
            try:
                c.execute(
                    "INSERT INTO smart_alerts (id, user_id, chat_id, asset_key, rule, active, last_triggered, created_at) VALUES (?, ?, ?, ?, ?, 1, 0, ?)",
                    (alert_id, int(user_id), int(chat_id), asset_key, rule, _utc_now()),
                )
                return "added"
            except sqlite3.IntegrityError:
                c.execute(
                    "UPDATE smart_alerts SET active=1 WHERE user_id=? AND asset_key=? AND rule=?",
                    (int(user_id), asset_key, rule),
                )
                return "exists"

    def user_smart_alerts(self, user_id):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT * FROM smart_alerts WHERE user_id=? AND active=1 ORDER BY created_at",
                (int(user_id),),
            ).fetchall()
            return [dict(r) for r in rows]

    def load_smart_alerts(self):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM smart_alerts WHERE active=1").fetchall()
            return [dict(r) for r in rows]

    def touch_smart_alert(self, alert_id, ts):
        with self._conn() as c:
            c.execute("UPDATE smart_alerts SET last_triggered=? WHERE id=?", (int(ts), alert_id))

    def delete_smart_alert(self, alert_id, user_id):
        with self._conn() as c:
            c.execute("DELETE FROM smart_alerts WHERE id=? AND user_id=?", (alert_id, int(user_id)))

    def delete_user_smart_alerts(self, user_id):
        with self._conn() as c:
            c.execute("DELETE FROM smart_alerts WHERE user_id=?", (int(user_id),))

    def get_state(self, key, default=None):
        with self._conn() as c:
            row = c.execute("SELECT value FROM bot_state WHERE key = ?", (key,)).fetchone()
            return json.loads(row[0]) if row else default

    def set_state(self, key, value):
        import json
        with self._conn() as c:
            c.execute("INSERT INTO bot_state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                      (key, json.dumps(value, ensure_ascii=False)))

    def stats(self):
        with self._conn() as c:
            users = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            vip = c.execute("SELECT COUNT(*) FROM vip_users").fetchone()[0]
            alerts = c.execute("SELECT COUNT(*) FROM alerts").fetchone()[0]
            daily = c.execute("SELECT COUNT(*) FROM daily_subs WHERE active = 1").fetchone()[0]
            refs = c.execute("SELECT COUNT(*) FROM referrals WHERE qualified = 1").fetchone()[0]
            pending = c.execute("SELECT COUNT(*) FROM orders WHERE status IN ('pending', 'pending_gateway')").fetchone()[0]
            return {"users": users, "vip": vip, "alerts": alerts, "daily": daily, "refs": refs, "pending": pending}


db = Database()

# ═══════════════════════════════════════════════════════════════
# ASSETS
# ═══════════════════════════════════════════════════════════════
ALERT_ASSETS = {
    "usd": {
        "label": "دلار آمریکا",
        "symbols": ["USD", "IR_USD", "USD_IRR", "USD_IRT"],
        "sections": ["currency"],
        "keywords": ["دلار آمریکا", "US Dollar"],
    },
    "gold18": {
        "label": "طلای ۱۸ عیار",
        "symbols": ["IR_GOLD_18K"],
        "sections": ["gold"],
        "keywords": ["طلای 18", "18K Gold"],
    },
    "melted": {
        "label": "آب‌شده نقدی",
        "symbols": ["IR_GOLD_MELTED", "IR_GOLD_MELTED_CASH", "GOLD_MELTED"],
        "sections": ["gold"],
        "keywords": ["آبشده", "آب‌شده", "طلای آب شده", "Melted Gold"],
    },
    "melted_future": {
        "label": "آب‌شده فردایی",
        "symbols": ["IR_GOLD_MELTED_FUTURE", "IR_GOLD_MELTED_TOMORROW", "GOLD_MELTED_FUTURE"],
        "sections": ["gold"],
        "keywords": ["آبشده فردایی", "آب‌شده فردایی", "فردایی آبشده", "Melted Gold Future"],
    },
    "herat_usd": {
        "label": "دلار هرات",
        "symbols": ["AF_USD", "USD_HERAT", "HERAT_USD", "IR_USD_HERAT"],
        "sections": ["currency"],
        "keywords": ["دلار هرات", "Herat Dollar", "Herat USD"],
    },
    "aed": {
        "label": "درهم امارات",
        "symbols": ["AED", "IR_AED", "AED_IRT"],
        "sections": ["currency"],
        "keywords": ["درهم امارات", "UAE Dirham", "AED"],
    },
    "emami": {
        "label": "سکه امامی",
        "symbols": ["IR_COIN_EMAMI", "IR_COIN_FULL"],
        "sections": ["gold"],
        "keywords": ["سکه امامی", "Emami"],
    },
    "half": {
        "label": "نیم‌سکه",
        "symbols": ["IR_COIN_HALF"],
        "sections": ["gold"],
        "keywords": ["نیم سکه", "Half Coin"],
    },
    "quarter": {
        "label": "ربع‌سکه",
        "symbols": ["IR_COIN_QUARTER"],
        "sections": ["gold"],
        "keywords": ["ربع سکه", "Quarter Coin"],
    },
    "ounce": {
        "label": "انس جهانی طلا",
        "symbols": ["XAUUSD", "XAU_USD"],
        "sections": ["gold"],
        "keywords": ["انس جهانی", "Gold Ounce"],
    },
    "btc": {
        "label": "بیت‌کوین",
        "symbols": ["BTC", "BTCUSDT"],
        "sections": ["cryptocurrency"],
        "keywords": ["Bitcoin", "بیت کوین"],
    },
    "eth": {
        "label": "اتریوم",
        "symbols": ["ETH", "ETHUSDT"],
        "sections": ["cryptocurrency"],
        "keywords": ["Ethereum", "اتریوم"],
    },
    "usdt": {
        "label": "تتر",
        "symbols": ["USDT", "USDTUSD", "USDT_IRT"],
        "sections": ["cryptocurrency", "currency"],
        "keywords": ["Tether", "تتر"],
    },
}

# ═══════════════════════════════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════════════════════════════
@lru_cache(maxsize=1)
def main_menu():
    rows = [
        [InlineKeyboardButton("📊 قیمت لحظه‌ای", callback_data="prices"), InlineKeyboardButton("🔔 هشدار قیمت", callback_data="alerts")],
        [InlineKeyboardButton("🗓 گزارش روزانه", callback_data="daily"), InlineKeyboardButton("📈 نمودار تکنیکال", callback_data="charts")],
        [InlineKeyboardButton("🧮 ماشین‌حساب طلا", callback_data="calculator"), InlineKeyboardButton("👤 حساب کاربری", callback_data="account")],
        [InlineKeyboardButton("🔥 مرکز آب‌شده", callback_data="melted_center"), InlineKeyboardButton("⚡ مرکز نوسان VIP", callback_data="navasan")],
        [InlineKeyboardButton("📌 بازار من VIP", callback_data="watchlist"), InlineKeyboardButton("🤖 تحلیل هوشمند VIP", callback_data="analysis")],
    ]
    if PUBLIC_BASE_URL.startswith("https://"):
        rows.append([InlineKeyboardButton("📱 داشبورد حرفه‌ای طلایار", web_app=WebAppInfo(url=f"{PUBLIC_BASE_URL}/app"))])
    rows += [
        [InlineKeyboardButton("🎁 دعوت دوستان", callback_data="referrals"), InlineKeyboardButton("⭐ عضویت VIP", callback_data="vip")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")],
    ]
    return InlineKeyboardMarkup(rows)


@lru_cache(maxsize=1)
def price_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 بازار ارز", callback_data="iran_currency")],
        [InlineKeyboardButton("🪙 طلا و سکه", callback_data="gold")],
        [InlineKeyboardButton("🌎 انس جهانی", callback_data="ounce")],
        [InlineKeyboardButton("₿ ارز دیجیتال", callback_data="crypto")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]
    ])


def alert_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ ساخت هشدار جدید", callback_data="alert_new")],
        [InlineKeyboardButton("📋 هشدارهای من", callback_data="alert_list"),
         InlineKeyboardButton("🗑 حذف همه", callback_data="alert_delete")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ])


def alert_asset_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 دلار", callback_data="alert_asset:usd"),
         InlineKeyboardButton("🪙 طلای ۱۸ عیار", callback_data="alert_asset:gold18")],
        [InlineKeyboardButton("🔥 آب‌شده نقدی", callback_data="alert_asset:melted"), InlineKeyboardButton("📅 آب‌شده فردایی", callback_data="alert_asset:melted_future")],
        [InlineKeyboardButton("🟡 سکه امامی", callback_data="alert_asset:emami"),
         InlineKeyboardButton("نیم‌سکه", callback_data="alert_asset:half")],
        [InlineKeyboardButton("ربع‌سکه", callback_data="alert_asset:quarter"),
         InlineKeyboardButton("🌎 انس جهانی", callback_data="alert_asset:ounce")],
        [InlineKeyboardButton("₿ بیت‌کوین", callback_data="alert_asset:btc")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="alerts")],
    ])


def alert_condition_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 بالاتر یا مساوی", callback_data="alert_condition:above")],
        [InlineKeyboardButton("📉 پایین‌تر یا مساوی", callback_data="alert_condition:below")],
        [InlineKeyboardButton("🔙 انتخاب دارایی", callback_data="alert_new")],
    ])


def alert_kind_menu(user_id):
    rows = [[InlineKeyboardButton("🎯 هشدار عددی", callback_data="alert_kind:price")]]
    if is_vip(user_id):
        rows.append([InlineKeyboardButton("📊 هشدار درصد تغییر VIP", callback_data="alert_kind:percent")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="alerts")])
    return InlineKeyboardMarkup(rows)


def alert_mode_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("1️⃣ یک‌باره", callback_data="alert_mode:once")],
        [InlineKeyboardButton("🔁 تکرارشونده VIP", callback_data="alert_mode:repeat")],
        [InlineKeyboardButton("❌ لغو", callback_data="alerts")],
    ])


def percent_condition_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📈 افزایش درصدی", callback_data="alert_condition:up")],
        [InlineKeyboardButton("📉 کاهش درصدی", callback_data="alert_condition:down")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="alert_new")],
    ])


def vip_menu(user_id=None):
    active = user_id is not None and is_vip(user_id)
    action = "تمدید" if active else "خرید"
    rows = [
        [InlineKeyboardButton(f"⭐ {action} یک‌ماهه — {VIP_PRICE_30} تومان", callback_data="buy:30")],
        [InlineKeyboardButton(f"🌟 {action} سه‌ماهه — {VIP_PRICE_90} تومان", callback_data="buy:90")],
        [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ]
    return InlineKeyboardMarkup(rows)


def vip_renew_menu():
    """منوی تمدید که حتی قبل از انقضای VIP هم بسته‌ها را نشان می‌دهد."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"⭐ تمدید ۳۰ روزه — {VIP_PRICE_30} تومان", callback_data="buy:30")],
        [InlineKeyboardButton(f"🌟 تمدید ۹۰ روزه — {VIP_PRICE_90} تومان", callback_data="buy:90")],
        [InlineKeyboardButton("💬 پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="home")],
    ])


def daily_menu(active=False):
    rows = [
        [InlineKeyboardButton("09:00", callback_data="daily_set:09:00"),
         InlineKeyboardButton("14:00", callback_data="daily_set:14:00"),
         InlineKeyboardButton("21:00", callback_data="daily_set:21:00")],
        [InlineKeyboardButton("📄 گزارش همین حالا", callback_data="daily_now")],
        [InlineKeyboardButton("⌨️ ساعت دلخواه", callback_data="daily_custom")],
    ]
    if active:
        rows.append([InlineKeyboardButton("⛔ توقف گزارش", callback_data="daily_stop")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="home")])
    return InlineKeyboardMarkup(rows)


@lru_cache(maxsize=1)
def chart_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 دلار", callback_data="chart_candle:usd"),
         InlineKeyboardButton("🪙 طلای ۱۸", callback_data="chart_candle:gold18")],
        [InlineKeyboardButton("🔥 آب‌شده", callback_data="chart_candle:melted"), InlineKeyboardButton("📅 فردایی", callback_data="chart_candle:melted_future")],
        [InlineKeyboardButton("🟡 سکه امامی", callback_data="chart_candle:emami"),
         InlineKeyboardButton("🥈 نیم‌سکه", callback_data="chart_candle:half")],
        [InlineKeyboardButton("🟠 ربع‌سکه", callback_data="chart_candle:quarter"),
         InlineKeyboardButton("🌎 انس جهانی", callback_data="chart_candle:ounce")],
        [InlineKeyboardButton("₿ بیت‌کوین", callback_data="chart_candle:btc"),
         InlineKeyboardButton("Ξ اتریوم", callback_data="chart_candle:eth")],
        [InlineKeyboardButton("💲 تتر", callback_data="chart_candle:usdt")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ])

def chart_period_menu(asset, candle=False):
    prefix = "candle" if candle else "chart"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("۲۴ ساعت", callback_data=f"{prefix}:{asset}:24"),
         InlineKeyboardButton("۷ روز VIP", callback_data=f"{prefix}:{asset}:168")],
        [InlineKeyboardButton("۳۰ روز VIP", callback_data=f"{prefix}:{asset}:720")],
        [InlineKeyboardButton("🔙 انتخاب دارایی", callback_data="charts")],
    ])


def navasan_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎯 اسکن فرصت‌ها", callback_data="nv:scanner"),
         InlineKeyboardButton("🫧 رادار انحراف/حباب", callback_data="nv:bubble")],
        [InlineKeyboardButton("🧠 تحلیل چندلایه", callback_data="nv:assetmenu"),
         InlineKeyboardButton("🌡 هیت‌مپ بازار", callback_data="nv:heatmap")],
        [InlineKeyboardButton("🧪 آزمایش تاریخی", callback_data="nv:backtestmenu"),
         InlineKeyboardButton("🚨 هشدار هوشمند", callback_data="nv:smartalerts")],
        [InlineKeyboardButton("📘 روش‌شناسی و ریسک", callback_data="nv:method")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ])


def navasan_asset_menu(prefix="nv:asset"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 دلار", callback_data=f"{prefix}:usd"),
         InlineKeyboardButton("🪙 طلای ۱۸", callback_data=f"{prefix}:gold18")],
        [InlineKeyboardButton("🔥 آب‌شده", callback_data=f"{prefix}:melted"), InlineKeyboardButton("📅 فردایی", callback_data=f"{prefix}:melted_future")],
        [InlineKeyboardButton("🟡 امامی", callback_data=f"{prefix}:emami"),
         InlineKeyboardButton("🥈 نیم", callback_data=f"{prefix}:half")],
        [InlineKeyboardButton("🟠 ربع", callback_data=f"{prefix}:quarter"),
         InlineKeyboardButton("🌎 انس", callback_data=f"{prefix}:ounce")],
        [InlineKeyboardButton("₿ بیت‌کوین", callback_data=f"{prefix}:btc"),
         InlineKeyboardButton("Ξ اتریوم", callback_data=f"{prefix}:eth")],
        [InlineKeyboardButton("💲 تتر", callback_data=f"{prefix}:usdt")],
        [InlineKeyboardButton("🔙 مرکز نوسان", callback_data="navasan")],
    ])


def smart_alert_rule_menu(asset):
    rows = [
        [InlineKeyboardButton("🚀 شکست محدوده ۲۴ساعته", callback_data=f"nv:saadd:{asset}:breakout")],
        [InlineKeyboardButton("🌪 حرکت غیرعادی", callback_data=f"nv:saadd:{asset}:abnormal")],
        [InlineKeyboardButton("🔥 همگرایی قوی", callback_data=f"nv:saadd:{asset}:confluence")],
    ]
    if asset in COIN_SPECS or asset in {"gold18", "melted"}:
        rows.append([InlineKeyboardButton("🫧 انحراف/حباب بالا", callback_data=f"nv:saadd:{asset}:bubble")])
    rows.append([InlineKeyboardButton("🔙 هشدارهای هوشمند", callback_data="nv:smartalerts")])
    return InlineKeyboardMarkup(rows)


def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار کلی", callback_data="admin:stats"),
         InlineKeyboardButton("👥 کاربران", callback_data="admin:users")],
        [InlineKeyboardButton("⭐ مدیریت VIP", callback_data="admin:vip"),
         InlineKeyboardButton("🔎 جستجوی کاربر", callback_data="admin:search")],
        [InlineKeyboardButton("🧾 سفارش‌ها / پرداخت", callback_data="admin:payments"),
         InlineKeyboardButton("🎁 آمار دعوت", callback_data="admin:referrals")],
        [InlineKeyboardButton("🚨 دعوت‌های مشکوک", callback_data="admin:suspicious"),
         InlineKeyboardButton("📣 پیام همگانی", callback_data="admin:broadcast")],
        [InlineKeyboardButton("📡 وضعیت API", callback_data="admin:api"),
         InlineKeyboardButton("🗄 دیتابیس", callback_data="admin:database")],
        [InlineKeyboardButton("💾 پشتیبان", callback_data="admin:backup"),
         InlineKeyboardButton("🧪 سیستم / نسخه", callback_data="admin:system")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="home")],
    ])


def admin_vip_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ افزودن / تمدید VIP", callback_data="admin:addvip")],
        [InlineKeyboardButton("➖ حذف VIP", callback_data="admin:removevip")],
        [InlineKeyboardButton("📋 VIPهای اخیر", callback_data="admin:vip_recent")],
        [InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin:menu")],
    ])


def admin_user_menu(target_user_id):
    uid = str(target_user_id)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ +۳۰ روز VIP", callback_data=f"admin_user_vip30:{uid}"),
         InlineKeyboardButton("🌟 +۹۰ روز VIP", callback_data=f"admin_user_vip90:{uid}")],
        [InlineKeyboardButton("➖ حذف VIP", callback_data=f"admin_user_removevip:{uid}")],
        [InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin:menu")],
    ])


def admin_suspicious_menu(referred_id):
    uid = str(referred_id)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأیید دستی دعوت", callback_data=f"admin_ref_approve:{uid}")],
        [InlineKeyboardButton("🔙 دعوت‌های مشکوک", callback_data="admin:suspicious")],
    ])


def watchlist_menu(user_id):
    items = db.get_watchlist(user_id)
    rows = [[InlineKeyboardButton(
        f"📌 دارایی‌های من: {len(items)}/{WATCHLIST_VIP_LIMIT}", callback_data="watchlist"
    )]]
    if items:
        for item in items:
            ak = item["asset_key"]
            label = ALERT_ASSETS.get(ak, {}).get("label", ak)
            rows.append([InlineKeyboardButton(f"❌ {label}", callback_data=f"wl_remove:{ak}")])
    if len(items) < WATCHLIST_VIP_LIMIT:
        rows.append([InlineKeyboardButton("➕ افزودن دارایی", callback_data="wl_add")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="home")])
    return InlineKeyboardMarkup(rows)


def watchlist_add_menu():
    rows = []
    for key, info in ALERT_ASSETS.items():
        rows.append([InlineKeyboardButton(info["label"], callback_data=f"wl_add:{key}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="watchlist")])
    return InlineKeyboardMarkup(rows)


# ═══════════════════════════════════════════════════════════════
# ABOUT / SUPPORT
# ═══════════════════════════════════════════════════════════════
def help_text():
    return f"""🟡 <b>طلایار</b>
دستیار هوشمند بازار طلا، ارز و کریپتو

🆓 <b>امکانات رایگان ربات</b>
⚡ قیمت لحظه‌ای بازار
🧮 ماشین‌حساب طلا
🔔 ۱ هشدار عددی فعال
📊 نمودار پایه ۲۴ساعته
👤 حساب کاربری و 🎁 دعوت دوستان

📱 <b>Mini App رایگان</b>
• Market Pulse و قیمت‌های لحظه‌ای
• Top Movers و Heatmap پایه
• صفحه پایه هر دارایی
• کندل ۲۴ساعته از تاریخچه ذخیره‌شده طلایار

⭐ <b>Mini App VIP</b>
• Opportunity Scanner و امتیاز فرصت
• RSI / EMA / حمایت / مقاومت
• Market Regime و Q کیفیت داده
• Fair Value / Bubble Map
• تایم‌فریم‌های 1H / 4H / 1D / 7D / 30D
• مرکز آب‌شده Pro و اختلاف نقدی/فردایی در صورت وجود دیتای مستقیم

🕯 <b>نکته نمودار</b>
OHLC مینی‌اپ از نمونه‌های قیمت ذخیره‌شده خود طلایار تجمیع می‌شود و OHLC مستقیم بورس/صرافی نیست. اگر داده کافی نباشد، کندل ساختگی نمایش داده نمی‌شود.

🔒 قابلیت‌های عملیاتی مثل پرداخت، گزارش، مدیریت حساب و هشدارها عمدتاً داخل Bot نگه داشته شده‌اند تا Mini App سبک و غیرتکراری بماند.

🆕 <b>قاعده به‌روزرسانی</b>: هر قابلیت جدید همراه همان نسخه به این راهنما اضافه می‌شود.

برای لغو ورود اطلاعات <code>/cancel</code> را بفرست.

👨‍💻 <b>توسعه و پشتیبانی فنی</b>
<b>{html.escape(DEVELOPER_NAME)}</b>
@{html.escape(DEVELOPER_USERNAME)}

⚠️ {DISCLAIMER}

<code>Talayar v{APP_VERSION}</code>"""


def help_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⭐ مقایسه رایگان و VIP", callback_data="plans")],
        [InlineKeyboardButton("💬 ارسال پیام به پشتیبانی", callback_data="support")],
        [InlineKeyboardButton("💻 سفارش ربات اختصاصی", url=f"https://t.me/{DEVELOPER_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ])


def support_prompt_text():
    return (
        "👋 <b>سلام، خوش اومدید.</b>\n\n"
        "پیام شما برای پشتیبانی طلایار دریافت می‌شود.\n"
        "اگر درباره خرید VIP، پرداخت، مشکلات فنی یا سفارش ربات اختصاصی سؤال دارید، "
        "پیامتان را کامل در همین چت بفرستید.\n\n"
        f"🟡 توسعه و پشتیبانی: <b>{html.escape(DEVELOPER_NAME)}</b> — @{html.escape(DEVELOPER_USERNAME)}\n\n"
        "برای لغو <code>/cancel</code> را بفرست."
    )

# ═══════════════════════════════════════════════════════════════
# SECURITY / LICENSE
# ═══════════════════════════════════════════════════════════════
def _license_digest(key, admin_id):
    raw = f"{key}|{admin_id}|{LICENSE_CONTEXT}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _current_public_host():
    candidate = PUBLIC_BASE_URL or os.environ.get("RAILWAY_PUBLIC_DOMAIN", "")
    candidate = str(candidate or "").strip()
    if not candidate:
        return ""
    if "://" not in candidate:
        candidate = "https://" + candidate
    try:
        return (urlparse(candidate).hostname or "").lower()
    except Exception:
        return ""


def _bot_token_fingerprint():
    return hashlib.sha256(str(BOT_TOKEN or "").encode("utf-8")).hexdigest()[:24]


def _binding_signature(admin_id, domain, bot_fp):
    payload = f"{admin_id}|{domain}|{bot_fp}|TALAYAR-RUNTIME-BINDING".encode("utf-8")
    return hmac.new(LICENSE_KEY.encode("utf-8"), payload, hashlib.sha256).hexdigest()


def license_status():
    if not LICENSE_ENFORCE:
        return True, "غیرفعال (Development)"
    if str(ADMIN_ID) != AUTHORIZED_ADMIN_ID:
        return False, "ADMIN_ID مجاز نیست"
    if not LICENSE_KEY:
        return False, "LICENSE_KEY تنظیم نشده"
    valid = hmac.compare_digest(_license_digest(LICENSE_KEY, ADMIN_ID), LICENSE_EXPECTED_SHA256)
    return (True, "فعال و معتبر") if valid else (False, "کلید لایسنس نامعتبر")


def validate_runtime_binding():
    """Bind production runtime to ADMIN_ID + bot token fingerprint + Railway/public domain.

    The binding is stored signed in SQLite. LICENSE_REBIND=1 intentionally refreshes it once
    after a legitimate token/domain rotation; remove that variable immediately afterwards.
    """
    if not LICENSE_ENFORCE:
        return True
    domain = _current_public_host()
    bot_fp = _bot_token_fingerprint()
    current = {"admin_id": str(ADMIN_ID), "domain": domain, "bot_fp": bot_fp}
    stored = db.get_state("license_binding", None)

    if not stored or LICENSE_REBIND:
        current["signature"] = _binding_signature(current["admin_id"], current["domain"], current["bot_fp"])
        db.set_state("license_binding", current)
        if LICENSE_REBIND:
            logger.warning("Runtime license binding was intentionally refreshed; remove LICENSE_REBIND after this deploy")
        return True

    if not isinstance(stored, dict):
        raise RuntimeError("Talayar runtime binding is corrupted")
    signature = str(stored.get("signature") or "")
    expected_sig = _binding_signature(str(stored.get("admin_id") or ""), str(stored.get("domain") or ""), str(stored.get("bot_fp") or ""))
    if not hmac.compare_digest(signature, expected_sig):
        raise RuntimeError("Talayar runtime binding signature is invalid")
    if str(stored.get("admin_id") or "") != current["admin_id"]:
        raise RuntimeError("Talayar runtime ADMIN_ID binding mismatch")
    if str(stored.get("bot_fp") or "") != current["bot_fp"]:
        raise RuntimeError("Talayar runtime BOT_TOKEN binding mismatch; set LICENSE_REBIND=1 once only if this rotation is legitimate")

    bound_domain = str(stored.get("domain") or "")
    if bound_domain and domain and bound_domain != domain:
        raise RuntimeError("Talayar runtime domain binding mismatch; set LICENSE_REBIND=1 once only if this domain change is legitimate")
    if not bound_domain and domain:
        # Safe one-way upgrade when a public Railway domain is configured later.
        current["signature"] = _binding_signature(current["admin_id"], current["domain"], current["bot_fp"])
        db.set_state("license_binding", current)
    return True


def validate_runtime_license():
    ok, detail = license_status()
    if not ok:
        raise RuntimeError(f"Talayar license check failed: {detail}")
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")
    validate_runtime_binding()
    return True


# ═══════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════
def _is_admin(user_id):
    return bool(ADMIN_ID) and str(user_id) == str(ADMIN_ID)


def _utc_now():
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value):
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed
    except (TypeError, ValueError):
        return None


def is_vip(user_id):
    if _is_admin(user_id):
        return True
    entry = db.get_vip(user_id)
    if not entry:
        return False
    expires = entry.get("expires_at")
    if not expires:
        return True
    exp = _parse_iso(expires)
    return bool(exp and exp > datetime.now(timezone.utc))


def vip_days_left(user_id):
    entry = db.get_vip(user_id)
    if not entry or not entry.get("expires_at"):
        return None
    exp = _parse_iso(entry["expires_at"])
    if not exp:
        return 0
    return max(0, int(((exp - datetime.now(timezone.utc)).total_seconds() + 86399) // 86400))


def vip_text(user_id):
    if is_vip(user_id):
        days = vip_days_left(user_id)
        return ("⭐ <b>عضویت VIP فعال است</b> ✅\n\n"
                f"زمان باقی‌مانده: {'بدون انقضا' if days is None else str(days) + ' روز'}\n"
                "هشدار نامحدود، درصدی و تکرارشونده، گزارش روزانه، نمودار تکنیکال ۷ و ۳۰ روزه، "
                "تحلیل هوشمند، بازار من و مرکز نوسان حرفه‌ای فعال‌اند.")
    return ("⭐ <b>عضویت VIP طلایار</b>\n\n"
            "✅ هشدار نامحدود، درصدی و تکرارشونده\n"
            "✅ گزارش روزانه خودکار\n"
            "✅ نمودار تکنیکال ۷ و ۳۰ روزه: کندل + EMA + RSI + حمایت/مقاومت\n"
            "✅ تحلیل هوشمند از داده واقعی\n"
            f"✅ بازار من تا {WATCHLIST_VIP_LIMIT} دارایی\n"
            "✅ مرکز نوسان v12: رادار حباب، اسکنر، هیت‌مپ، Backtest و هشدار هوشمند\n\n"
            f"یک‌ماهه: <b>{VIP_PRICE_30} تومان</b>\n"
            f"سه‌ماهه: <b>{VIP_PRICE_90} تومان</b>")


def _parse_number(text):
    digit_map = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
    cleaned = str(text).translate(digit_map)
    for token in (",", "٬", "،", " ", "تومان", "دلار", "%", "درصد"):
        cleaned = cleaned.replace(token, "")
    cleaned = cleaned.replace("٫", ".")
    try:
        number = float(cleaned)
        return number if number >= 0 else None
    except ValueError:
        return None


def _format_number(value):
    try:
        number = float(str(value).replace(",", ""))
        if number.is_integer():
            return f"{int(number):,}"
        return f"{number:,.2f}".rstrip("0").rstrip(".")
    except (TypeError, ValueError):
        return str(value or "نامشخص")


def _condition_label(condition):
    return {"above": "بالاتر یا مساوی", "below": "پایین‌تر یا مساوی",
            "up": "افزایش", "down": "کاهش"}.get(condition, "نامشخص")


def _unwrap_payload(payload):
    if not isinstance(payload, dict):
        return None
    if any(isinstance(payload.get(key), list) for key in ("gold", "currency", "cryptocurrency")):
        return payload
    for wrapper in ("data", "result"):
        nested = payload.get(wrapper)
        if isinstance(nested, dict) and any(isinstance(nested.get(key), list) for key in ("gold", "currency", "cryptocurrency")):
            return nested
    return None


# ═══════════════════════════════════════════════════════════════
# BRS API
# ═══════════════════════════════════════════════════════════════
def get_market_data(force_refresh=False):
    now = time.monotonic()
    if not force_refresh and _market_cache["data"] is not None and now - _market_cache["saved_at"] < CACHE_TTL_SECONDS:
        return _market_cache["data"], None
    if not BRS_API_URL:
        return None, "تنظیمات اتصال API کامل نیست"
    try:
        response = requests.get(BRS_API_URL, timeout=API_TIMEOUT,
                                headers={"Accept": "application/json", "User-Agent": "TalayarBot/12.0.0"})
        response.raise_for_status()
        raw_payload = response.json()
        payload = _unwrap_payload(raw_payload)
        if payload is None:
            return None, "ساختار پاسخ API تغییر کرده"
        _market_cache["data"] = payload
        _market_cache["saved_at"] = now
        return payload, None
    except requests.Timeout:
        return None, "زمان پاسخ‌گویی API تمام شد"
    except requests.RequestException as exc:
        status = exc.response.status_code if exc.response is not None else "no-response"
        return None, f"خطای اتصال به API (کد {status})"
    except Exception:
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
    return None


def find_alert_item(market, asset_key):
    asset = ALERT_ASSETS.get(asset_key)
    if not asset:
        return None
    return find_item(market, asset["symbols"], sections=asset["sections"], name_keywords=asset["keywords"])


def _item_price(item):
    try:
        return float(str(item.get("price")).replace(",", ""))
    except (AttributeError, TypeError, ValueError):
        return None


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
        ("آب‌شده نقدی", ["IR_GOLD_MELTED", "IR_GOLD_MELTED_CASH", "GOLD_MELTED"], ["آبشده", "آب‌شده", "Melted Gold"]),
        ("آب‌شده فردایی", ["IR_GOLD_MELTED_FUTURE", "IR_GOLD_MELTED_TOMORROW"], ["آبشده فردایی", "آب‌شده فردایی"]),
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
        item = find_item(market, symbols, sections=["currency", "cryptocurrency"], name_keywords=keywords)
        text += show_item(item, label)
    return text


def build_crypto_text(market):
    text = "₿ <b>ارز دیجیتال</b>\n\n"
    for key in ("btc", "eth", "usdt"):
        text += show_item(find_alert_item(market, key), ALERT_ASSETS[key]["label"])
    return text


def build_daily_report(market):
    text = f"🗓 <b>گزارش روزانه طلایار</b>\n🕒 {datetime.now(TEHRAN_TZ):%Y/%m/%d - %H:%M}\n\n"
    for key in ("usd", "gold18", "emami", "half", "quarter", "ounce", "btc"):
        item = find_alert_item(market, key)
        if item:
            text += f"• {ALERT_ASSETS[key]['label']}: <b>{_format_number(item.get('price'))}</b> {item.get('unit') or ''}\n"
    return text + f"\n<i>{DISCLAIMER}</i>"


def capture_history(market):
    now = int(time.time())
    last = db.get_state("last_history", 0)
    if now - int(last) < HISTORY_SAVE_INTERVAL:
        return
    for key in ALERT_ASSETS:
        item = find_alert_item(market, key)
        price = _item_price(item)
        if price is not None:
            db.save_price_history(key, price, item.get("unit") or "", now)
    db.set_state("last_history", now)
    db.prune_price_history(days=HISTORY_RETENTION_DAYS)
    capture_bubble_history(market)


def _sparkline(values, size=30):
    if len(values) > size:
        values = [values[round(i * (len(values) - 1) / (size - 1))] for i in range(size)]
    bars = "▁▂▃▄▅▆▇█"
    low, high = min(values), max(values)
    if low == high:
        return bars[3] * len(values)
    return "".join(bars[min(7, int((value - low) / (high - low) * 7))] for value in values)


def chart_text(asset, hours):
    points = db.get_price_history(asset, hours)
    if len(points) < 2:
        return "📈 هنوز داده کافی برای نمودار جمع نشده؛ طلایار هر پنج دقیقه یک نمونه ذخیره می‌کند."
    values = [float(p["price"]) for p in points]
    change = (values[-1] - values[0]) / values[0] * 100 if values[0] else 0
    period_label = {24: "۲۴ ساعت", 168: "۷ روز", 720: "۳۰ روز"}.get(hours, f"{hours} ساعت")
    coverage_hours = max(0, int((points[-1]["ts"] - points[0]["ts"]) / 3600))
    coverage_note = ""
    if coverage_hours < int(hours * 0.8):
        started = datetime.fromtimestamp(points[0]["ts"], TEHRAN_TZ).strftime("%Y/%m/%d")
        coverage_note = f"\n<i>آرشیو این دارایی از {started} در دسترس است و به‌تدریج کامل می‌شود.</i>"
    return (f"📈 <b>{ALERT_ASSETS[asset]['label']} — {period_label}</b>\n\n"
            f"<code>{_sparkline(values)}</code>\n\nشروع: {_format_number(values[0])}\n"
            f"فعلی: <b>{_format_number(values[-1])}</b>\nکمترین: {_format_number(min(values))}\n"
            f"بیشترین: {_format_number(max(values))}\nتغییر: {change:+.2f}%"
            f"{coverage_note}")


# ═══════════════════════════════════════════════════════════════
# NAVASAN INTELLIGENCE v12
# Transparent, deterministic decision-support analytics. No buy/sell calls.
# ═══════════════════════════════════════════════════════════════
def _normalize_toman(price, unit):
    """Normalize Iranian market quotes to toman when the API explicitly reports rial."""
    if price is None:
        return None
    u = str(unit or "").casefold()
    p = float(price)
    if "ریال" in u or "rial" in u:
        return p / 10.0
    return p


def _series(asset, hours=720):
    pts = db.get_price_history(asset, hours)
    return [(int(p["ts"]), float(p["price"])) for p in pts if p.get("price") is not None]


def _nearest_change(series, seconds):
    if len(series) < 2:
        return None
    now_ts, now_p = series[-1]
    target = now_ts - seconds
    prior = min(series[:-1], key=lambda x: abs(x[0] - target), default=None)
    if not prior or prior[1] == 0:
        return None
    # Reject a very distant prior sample; prevents pretending we have a timeframe we do not cover.
    tolerance = max(900, int(seconds * 0.35))
    if abs(prior[0] - target) > tolerance:
        return None
    return (now_p - prior[1]) / prior[1] * 100.0


def _ema(values, span):
    if not values:
        return None
    return float(pd.Series(values, dtype="float64").ewm(span=span, adjust=False).mean().iloc[-1])


def _rsi_close(values, period=14):
    if len(values) < period + 2:
        return None
    ss = pd.Series(values, dtype="float64")
    delta = ss.diff()
    gain = delta.clip(lower=0).ewm(alpha=1/period, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1/period, adjust=False).mean()
    rs = gain / loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    if pd.isna(val):
        return 100.0 if delta.tail(period).min() >= 0 else 50.0
    return float(val)


def _zscore(values):
    if len(values) < 10:
        return None
    ss = pd.Series(values, dtype="float64")
    std = float(ss.std(ddof=0))
    if std <= 0:
        return 0.0
    return float((ss.iloc[-1] - ss.mean()) / std)


def _realized_volatility(values, window=24):
    """Close-to-close realized volatility proxy, expressed as average absolute percent move."""
    if len(values) < 3:
        return None
    ss = pd.Series(values[-(window+1):], dtype="float64").pct_change().dropna() * 100
    return float(ss.abs().mean()) if len(ss) else None


def _fair_value_snapshot(market, asset):
    usd_i = find_alert_item(market, "usd")
    ounce_i = find_alert_item(market, "ounce")
    target_i = find_alert_item(market, asset)
    usd = _normalize_toman(_item_price(usd_i), usd_i.get("unit") if usd_i else "") if usd_i else None
    ounce = _item_price(ounce_i) if ounce_i else None
    market_price = _normalize_toman(_item_price(target_i), target_i.get("unit") if target_i else "") if target_i else None
    if not usd or not ounce or not market_price:
        return None
    if asset in COIN_SPECS:
        spec = COIN_SPECS[asset]
        pure_g = spec["gross_g"] * spec["fineness"]
        fair = (ounce / TROY_OUNCE_GRAMS) * pure_g * usd
        kind = "حباب سکه"
    elif asset == "gold18":
        fair = (ounce / TROY_OUNCE_GRAMS) * 0.750 * usd
        kind = "انحراف ارزش نظری"
    elif asset == "melted":
        fair = (ounce / TROY_OUNCE_GRAMS) * 0.750 * usd * MESGHAL_18_EQUIV_FACTOR
        kind = "انحراف آب‌شده از ارزش نظری"
    else:
        return None
    if fair <= 0:
        return None
    bubble = market_price - fair
    pct = bubble / fair * 100.0
    return {"fair": fair, "market": market_price, "bubble": bubble, "pct": pct, "kind": kind}


def capture_bubble_history(market):
    now = int(time.time())
    last = int(db.get_state("last_bubble_history", 0) or 0)
    if now - last < HISTORY_SAVE_INTERVAL:
        return
    for asset in ("gold18", "melted", "emami", "half", "quarter"):
        snap = _fair_value_snapshot(market, asset)
        if snap:
            db.save_bubble_history(asset, snap["pct"], snap["fair"], snap["market"], now)
    db.set_state("last_bubble_history", now)
    db.prune_bubble_history(HISTORY_RETENTION_DAYS)


def _bubble_z(asset):
    vals = [float(x["bubble_percent"]) for x in db.get_bubble_history(asset, 720)]
    return _zscore(vals), len(vals)


def _market_features(asset, market):
    data = _series(asset, 720)
    vals = [p for _, p in data]
    item = find_alert_item(market, asset)
    current = _item_price(item) if item else (vals[-1] if vals else None)
    if current is None:
        return {"asset": asset, "quality": 0, "reason": "قیمت فعلی در دسترس نیست"}
    if vals and abs(vals[-1] - current) / max(abs(current), 1) > 1e-12:
        data.append((int(time.time()), float(current))); vals.append(float(current))
    n = len(vals)
    quality = min(100, int(n / NAVASAN_PRO_POINTS * 100))
    ema9 = _ema(vals, 9) if n >= 9 else None
    ema21 = _ema(vals, 21) if n >= 21 else None
    ema50 = _ema(vals, 50) if n >= 50 else None
    rsi = _rsi_close(vals, 14)
    z = _zscore(vals[-96:]) if n >= 10 else None
    vol = _realized_volatility(vals, 24)
    prev_vol = _realized_volatility(vals[:-24], 24) if n >= 50 else None
    vol_ratio = (vol / prev_vol) if vol is not None and prev_vol not in (None, 0) else None
    prior = vals[:-1]
    support = min(prior[-288:]) if prior else current
    resistance = max(prior[-288:]) if prior else current
    breakout = "none"
    if prior and current > resistance:
        breakout = "up"
    elif prior and current < support:
        breakout = "down"
    v5 = _nearest_change(data, 300)
    v15 = _nearest_change(data, 900)
    v60 = _nearest_change(data, 3600)
    v240 = _nearest_change(data, 14400)
    v24h = _nearest_change(data, 86400)
    trend = 0
    if ema9 is not None and ema21 is not None:
        trend += 1 if ema9 > ema21 else -1
    if ema21 is not None and ema50 is not None:
        trend += 1 if ema21 > ema50 else -1
    mom = 0
    if rsi is not None:
        if 55 <= rsi <= 75: mom += 1
        elif 25 <= rsi <= 45: mom -= 1
        elif rsi > 80: mom += 0  # overextended, not extra bullish evidence
        elif rsi < 20: mom += 0
    if v60 is not None:
        mom += 1 if v60 > 0.15 else (-1 if v60 < -0.15 else 0)
    abnormal = bool(vol_ratio is not None and vol_ratio >= 1.8)
    if abnormal and v60 is not None:
        mom += 1 if v60 > 0 else (-1 if v60 < 0 else 0)
    if breakout == "up": trend += 1
    elif breakout == "down": trend -= 1
    confluence = max(-5, min(5, trend + mom))
    score = int(round(50 + confluence * 10))
    if quality < 35:
        score = None
    if vol_ratio is not None and vol_ratio >= 2.5:
        regime = "نوسان بسیار بالا"
    elif breakout != "none":
        regime = "شکست رو به بالا" if breakout == "up" else "شکست رو به پایین"
    elif trend >= 2 or trend <= -2:
        regime = "رونددار"
    elif vol is not None and vol < 0.08:
        regime = "کم‌نوسان"
    else:
        regime = "رنج/انتقالی"
    snap = _fair_value_snapshot(market, asset)
    bz, bz_n = _bubble_z(asset) if asset in COIN_SPECS or asset in {"gold18", "melted"} else (None, 0)
    return {
        "asset": asset, "price": current, "unit": (item.get("unit") or "") if item else "",
        "n": n, "quality": quality, "ema9": ema9, "ema21": ema21, "ema50": ema50,
        "rsi": rsi, "z": z, "vol": vol, "vol_ratio": vol_ratio, "support": support,
        "resistance": resistance, "breakout": breakout, "v5": v5, "v15": v15,
        "v60": v60, "v240": v240, "v24h": v24h, "trend_raw": trend, "mom_raw": mom,
        "confluence": confluence, "score": score, "regime": regime, "fair": snap,
        "bubble_z": bz, "bubble_n": bz_n, "abnormal": abnormal,
    }


def _fmt_pct(v):
    return "—" if v is None else f"{v:+.2f}%"


def _direction_word(v):
    if v is None: return "نامشخص"
    return "صعودی" if v > 0 else ("نزولی" if v < 0 else "خنثی")


def build_navasan_asset_text(asset, market):
    f = _market_features(asset, market)
    label = ALERT_ASSETS.get(asset, {}).get("label", asset)
    if f.get("price") is None:
        return f"⚡ <b>{label}</b>\n\nداده کافی در دسترس نیست."
    q = f["quality"]
    score_txt = f"{f['score']}/100" if f.get("score") is not None else "داده ناکافی"
    rsi_txt = "—" if f.get("rsi") is None else f"{f['rsi']:.1f}"
    z_txt = "—" if f.get("z") is None else f"{f['z']:+.2f}σ"
    vr = "—" if f.get("vol_ratio") is None else f"{f['vol_ratio']:.2f}×"
    lines = [
        f"⚡ <b>تحلیل چندلایه — {label}</b>", "",
        f"💰 قیمت: <b>{_format_number(f['price'])}</b> {html.escape(str(f['unit']))}",
        f"🧭 رژیم بازار: <b>{f['regime']}</b>",
        f"🔥 قدرت همگرایی: <b>{score_txt}</b> | کیفیت داده: <b>{q}%</b>",
        f"📊 RSI14: <code>{rsi_txt}</code> | Z-Score: <code>{z_txt}</code>",
        f"🌪 نوسان تحقق‌یافته: <code>{'—' if f['vol'] is None else format(f['vol'], '.3f') + '%/نمونه'}</code> | جهش نوسان: <code>{vr}</code>",
        f"⚡ سرعت: 5m {_fmt_pct(f['v5'])} | 15m {_fmt_pct(f['v15'])} | 1h {_fmt_pct(f['v60'])} | 4h {_fmt_pct(f['v240'])}",
        f"🧱 حمایت آرشیوی: <code>{_format_number(f['support'])}</code>",
        f"🎯 مقاومت آرشیوی: <code>{_format_number(f['resistance'])}</code>",
    ]
    if f.get("breakout") != "none":
        lines.append("🚀 شکست محدوده: <b>رو به بالا</b>" if f["breakout"] == "up" else "🚨 شکست محدوده: <b>رو به پایین</b>")
    if f.get("fair"):
        snap=f["fair"]
        zpart = "" if f.get("bubble_z") is None else f" | Z: {f['bubble_z']:+.2f}σ"
        lines += [
            "",
            f"🫧 {snap['kind']}: <b>{snap['pct']:+.2f}%</b>{zpart}",
            f"ارزش نظری: <code>{_format_number(snap['fair'])}</code> تومان",
        ]
    # Risk bands use recent support/resistance and realized movement; not a trade instruction.
    risk_move = (f.get("vol") or 0) * 3
    lines += [
        "",
        f"🛡 باند ریسک کوتاه‌مدت: تقریباً <b>±{risk_move:.2f}%</b> بر مبنای نوسان اخیر" if risk_move else "🛡 باند ریسک: داده کافی نیست",
        "",
        "<i>این خروجی ابزار پشتیبان تصمیم است، نه توصیه خرید/فروش. شکست‌ها و امتیازها باید با نقدشوندگی و شرایط لحظه‌ای بازار بررسی شوند.</i>",
    ]
    return "\n".join(lines)


def _derived_melted_from_gold18(market):
    item = find_alert_item(market, "gold18")
    price = _item_price(item)
    if price is None:
        return None
    p = _normalize_toman(price, (item or {}).get("unit"))
    return p * MESGHAL_18_EQUIV_FACTOR if p else None

def _melted_snapshot(market):
    cash_item = find_alert_item(market, "melted")
    future_item = find_alert_item(market, "melted_future")
    cash = _item_price(cash_item); future = _item_price(future_item)
    if cash is not None:
        cash = _normalize_toman(cash, (cash_item or {}).get("unit")); cash_source = "بازار"
    else:
        cash = _derived_melted_from_gold18(market); cash_source = "برآورد از طلای ۱۸" if cash is not None else "ناموجود"
    if future is not None:
        future = _normalize_toman(future, (future_item or {}).get("unit"))
    def tv(item):
        p=_item_price(item); return _normalize_toman(p, (item or {}).get("unit")) if p is not None else None
    spread = future-cash if future is not None and cash is not None else None
    return {"cash":cash,"cash_source":cash_source,"future":future,"spread":spread,"spread_pct":(spread/cash*100 if spread is not None and cash else None),"gold18":tv(find_alert_item(market,"gold18")),"ounce":_item_price(find_alert_item(market,"ounce")),"usd":tv(find_alert_item(market,"usd")),"herat":tv(find_alert_item(market,"herat_usd")),"aed":tv(find_alert_item(market,"aed"))}

def build_melted_center(market):
    m=_melted_snapshot(market); lines=["🔥 <b>مرکز آب‌شده طلایار</b>",""]
    if m["cash"] is not None:
        suffix="" if m["cash_source"]=="بازار" else " <i>(برآورد نظری؛ قیمت مستقیم بازار دریافت نشد)</i>"
        lines.append(f"🟡 آب‌شده نقدی: <b>{_format_number(m['cash'])}</b> تومان{suffix}")
    else: lines.append("🟡 آب‌شده نقدی: داده بازار در دسترس نیست")
    lines.append(f"📅 آب‌شده فردایی: <b>{_format_number(m['future'])}</b> تومان" if m["future"] is not None else "📅 آب‌شده فردایی: منبع فعلی داده نداد")
    if m["spread"] is not None:
        icon="🟢" if m["spread"]>0 else "🔴" if m["spread"]<0 else "⚪"
        lines.append(f"{icon} اختلاف فردایی/نقدی: <b>{m['spread']:+,.0f}</b> تومان ({m['spread_pct']:+.2f}%)")
    lines += ["","📌 <b>بازارهای مرجع</b>"]
    for label,key,unit in (("طلای ۱۸","gold18","تومان"),("انس جهانی","ounce","دلار"),("دلار تهران","usd","تومان"),("دلار هرات","herat","تومان"),("درهم امارات","aed","تومان")):
        val=m.get(key); lines.append(f"• {label}: <b>{_format_number(val)}</b> {unit}" if val is not None else f"• {label}: داده موجود نیست")
    lines += ["","<i>طلایار برای آب‌شده/فردایی عدد ساختگی نمایش نمی‌دهد. اگر قیمت مستقیم در منبع نباشد، فقط برآورد نظری نقدی با برچسب مشخص نشان داده می‌شود.</i>"]
    return "\n".join(lines)

def _mini_price_item(market, key):
    item = find_alert_item(market, key)
    price = _item_price(item)
    source = "market"
    unit = (item or {}).get("unit") or ""
    change = _safe_change_percent(item) if item else 0.0
    if price is None and key == "melted":
        price = _derived_melted_from_gold18(market)
        unit = "تومان"
        source = "derived"
        change = 0.0
    if price is None:
        return None
    return {"key": key, "label": ALERT_ASSETS[key]["label"], "price": price, "unit": unit,
            "change": float(change or 0.0), "source": source}


def _dashboard_payload(market, user_id=None):
    """Compatibility payload used by v13 clients."""
    return _mini_overview_payload(market, user_id)


def _mini_overview_payload(market, user_id=None):
    capture_history(market)
    vip = bool(user_id and is_vip(user_id))
    keys = ("gold18","melted","melted_future","emami","usd","herat_usd","aed","ounce","btc","eth","usdt")
    items = [x for x in (_mini_price_item(market, k) for k in keys) if x]
    movers = sorted(items, key=lambda x: abs(float(x.get("change") or 0)), reverse=True)[:5]
    # Lightweight market pulse: uses feed change values only; deep feature engine is lazy-loaded for VIP scanner/details.
    changes = [float(x.get("change") or 0) for x in items if x.get("change") is not None]
    avg = (sum(changes) / len(changes)) if changes else 0.0
    positives = sum(1 for x in changes if x > 0)
    negatives = sum(1 for x in changes if x < 0)
    pulse_score = max(0, min(100, int(round(50 + avg * 8 + (positives-negatives)*2))))
    pulse_state = "صعودی" if pulse_score >= 58 else ("نزولی" if pulse_score <= 42 else "خنثی")
    heatmap = [{"key":x["key"],"label":x["label"],"price":x["price"],"unit":x["unit"],"change":x["change"]} for x in items]
    return {
        "version": APP_VERSION, "vip": vip, "tier": "vip" if vip else "free",
        "items": items, "movers": movers, "heatmap": heatmap,
        "pulse": {"score": pulse_score, "state": pulse_state, "average_change": avg,
                  "positive": positives, "negative": negatives, "count": len(changes)},
        "melted": _melted_snapshot(market),
        "free": {"pulse": True, "prices": True, "movers": True, "heatmap": True, "asset_basic": True, "chart_24h": True},
        "vip_features": {"scanner": vip, "technicals": vip, "fair_value": vip, "pro_timeframes": vip, "melted_pro": vip},
        "updated_at": datetime.now(TEHRAN_TZ).strftime("%H:%M:%S")
    }


def _mini_asset_payload(market, user_id, asset):
    if asset not in ALERT_ASSETS:
        return None, 404
    vip = bool(user_id and is_vip(user_id))
    basic = _mini_price_item(market, asset)
    if basic is None:
        return {"error":"price unavailable"}, 404
    result = {"version":APP_VERSION,"vip":vip,"asset":basic,"technical_locked":not vip}
    if vip:
        f = _market_features(asset, market)
        result["technical"] = {
            "q": f.get("quality"), "score": f.get("score"), "regime": f.get("regime"),
            "rsi": f.get("rsi"), "ema9": f.get("ema9"), "ema21": f.get("ema21"), "ema50": f.get("ema50"),
            "support": f.get("support"), "resistance": f.get("resistance"), "breakout": f.get("breakout"),
            "v5": f.get("v5"), "v15": f.get("v15"), "v60": f.get("v60"), "v240": f.get("v240"), "v24h": f.get("v24h"),
            "vol": f.get("vol"), "vol_ratio": f.get("vol_ratio"), "abnormal": f.get("abnormal")
        }
        if asset in COIN_SPECS or asset in {"gold18","melted"}:
            result["fair_value"] = f.get("fair")
            result["bubble_z"] = f.get("bubble_z")
    return result, 200


def _mini_scanner_payload(market, user_id):
    if not (user_id and is_vip(user_id)):
        return {"error":"vip_required"}, 403
    rows=[]
    for asset in ("melted","gold18","usd","emami","half","quarter","ounce","btc","eth","usdt","aed","herat_usd"):
        f=_market_features(asset, market)
        if f.get("price") is None: continue
        rows.append({"key":asset,"label":ALERT_ASSETS[asset]["label"],"price":f.get("price"),"unit":f.get("unit"),
                     "score":f.get("score"),"q":f.get("quality"),"regime":f.get("regime"),"v60":f.get("v60"),"v24h":f.get("v24h")})
    rows.sort(key=lambda r: (r["score"] is not None, r["score"] or -1, r["q"] or 0), reverse=True)
    return {"version":APP_VERSION,"vip":True,"items":rows}, 200


def _mini_fair_value_payload(market, user_id):
    if not (user_id and is_vip(user_id)):
        return {"error":"vip_required"}, 403
    rows=[]
    for asset in ("gold18","melted","emami","half","quarter"):
        snap=_fair_value_snapshot(market,asset)
        if snap:
            z,n=_bubble_z(asset)
            rows.append({"key":asset,"label":ALERT_ASSETS[asset]["label"],"fair":snap["fair"],"market":snap["market"],
                         "bubble":snap["bubble"],"pct":snap["pct"],"z":z,"samples":n})
    return {"version":APP_VERSION,"vip":True,"items":rows}, 200


def _mini_ohlc(asset, hours, bucket_seconds, max_candles=MINIAPP_MAX_CANDLES):
    points = db.get_price_history(asset, int(hours))
    derived_factor = None
    if not points and asset == "melted":
        # When direct melted history is unavailable, a clearly-derived OHLC can be built
        # from the bot's own stored 18K history using the fixed mesghal-equivalent factor.
        points = db.get_price_history("gold18", int(hours))
        derived_factor = MESGHAL_18_EQUIV_FACTOR
    if not points:
        return []
    buckets={}
    for p in points:
        try:
            ts=int(p["ts"]); price=float(p["price"])
            if derived_factor is not None:
                price *= derived_factor
        except (TypeError,ValueError,KeyError):
            continue
        b=(ts//bucket_seconds)*bucket_seconds
        row=buckets.get(b)
        if row is None: buckets[b]=[price,price,price,price]
        else:
            row[1]=max(row[1],price); row[2]=min(row[2],price); row[3]=price
    rows=[{"t":b,"o":v[0],"h":v[1],"l":v[2],"c":v[3]} for b,v in sorted(buckets.items())]
    return rows[-max_candles:]


def _mini_chart_payload(user_id, asset, timeframe):
    vip=bool(user_id and is_vip(user_id))
    specs={
        "1H":(1,300,True), "4H":(4,600,True), "24H":(24,900,False), "1D":(24,900,False),
        "7D":(168,7200,True), "30D":(720,21600,True)
    }
    spec=specs.get(str(timeframe).upper())
    if asset not in ALERT_ASSETS or not spec: return {"error":"invalid_request"},400
    hours,bucket,vip_only=spec
    if vip_only and not vip: return {"error":"vip_required"},403
    candles=_mini_ohlc(asset,hours,bucket)
    return {"version":APP_VERSION,"vip":vip,"asset":asset,"label":ALERT_ASSETS[asset]["label"],"timeframe":str(timeframe).upper(),
            "candles":candles,"max":MINIAPP_MAX_CANDLES,
            "note":"OHLC از نمونه‌های قیمت ذخیره‌شده طلایار تجمیع شده و OHLC مستقیم بورس/صرافی نیست."},200

def _verify_telegram_init_data(init_data):
    try:
        pairs=dict(parse_qs(init_data, keep_blank_values=True)); received=(pairs.pop("hash",[""])[0] or "").strip()
        if not received: return None
        flat={k:(v[0] if isinstance(v,list) else v) for k,v in pairs.items()}; auth_date=int(flat.get("auth_date") or 0)
        if abs(int(time.time())-auth_date)>MINIAPP_AUTH_MAX_AGE_SECONDS: return None
        check="\n".join(f"{k}={flat[k]}" for k in sorted(flat)); secret=hmac.new(b"WebAppData",BOT_TOKEN.encode(),hashlib.sha256).digest(); digest=hmac.new(secret,check.encode(),hashlib.sha256).hexdigest()
        if not hmac.compare_digest(digest,received): return None
        user=json.loads(flat.get("user") or "{}"); return int(user.get("id")) if user.get("id") is not None else None
    except Exception: return None

MINIAPP_HTML = base64.b64decode("PCFkb2N0eXBlIGh0bWw+PGh0bWwgbGFuZz0iZmEiIGRpcj0icnRsIj48aGVhZD48bWV0YSBjaGFyc2V0PSJ1dGYtOCI+PG1ldGEgbmFtZT0idmlld3BvcnQiIGNvbnRlbnQ9IndpZHRoPWRldmljZS13aWR0aCxpbml0aWFsLXNjYWxlPTEsbWF4aW11bS1zY2FsZT0xLHVzZXItc2NhbGFibGU9bm8iPjx0aXRsZT7Yt9mE2KfbjNin2LE8L3RpdGxlPjxzY3JpcHQgc3JjPSJodHRwczovL3RlbGVncmFtLm9yZy9qcy90ZWxlZ3JhbS13ZWItYXBwLmpzIj48L3NjcmlwdD48c3R5bGU+Cjpyb290ey0tYmc6IzA4MDgwODstLWNhcmQ6IzE1MTUxNTstLWNhcmQyOiMxYjFiMWI7LS1nb2xkOiNlM2IzNDE7LS1ncmVlbjojMjhkMTdjOy0tcmVkOiNmZjRkNTU7LS1tdXRlZDojYWFhOy0tbGluZTojMmIyYjJifSp7Ym94LXNpemluZzpib3JkZXItYm94fWJvZHl7bWFyZ2luOjA7YmFja2dyb3VuZDp2YXIoLS1iZyk7Y29sb3I6I2ZmZjtmb250LWZhbWlseTpUYWhvbWEsQXJpYWwsc2Fucy1zZXJpZn0ud3JhcHttYXgtd2lkdGg6OTQwcHg7bWFyZ2luOmF1dG87cGFkZGluZzoxNnB4IDE0cHggODhweH0uYnJhbmR7ZGlzcGxheTpmbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2VlbjttYXJnaW46NHB4IDAgMTRweH0uYnJhbmQgaDF7bWFyZ2luOjA7Y29sb3I6dmFyKC0tZ29sZCk7Zm9udC1zaXplOjI3cHh9LnBpbGx7Ym9yZGVyOjFweCBzb2xpZCAjNDkzOTBkO2JhY2tncm91bmQ6IzIyMWIwYTtjb2xvcjp2YXIoLS1nb2xkKTtwYWRkaW5nOjZweCAxMHB4O2JvcmRlci1yYWRpdXM6MTJweDtmb250LXNpemU6MTJweH0uaGVybywuY2FyZHtiYWNrZ3JvdW5kOnZhcigtLWNhcmQpO2JvcmRlcjoxcHggc29saWQgdmFyKC0tbGluZSk7Ym9yZGVyLXJhZGl1czoxOHB4O3BhZGRpbmc6MTVweH0uaGVyb3tib3JkZXItY29sb3I6IzRkM2IxMjtiYWNrZ3JvdW5kOmxpbmVhci1ncmFkaWVudCgxNDVkZWcsIzE3MTMwYSwjMGIwYjBiKX0uaGVyb1RvcHtkaXNwbGF5OmZsZXg7anVzdGlmeS1jb250ZW50OnNwYWNlLWJldHdlZW47Z2FwOjEwcHg7YWxpZ24taXRlbXM6Y2VudGVyfS5zY29yZXtmb250LXNpemU6MzVweDtmb250LXdlaWdodDo5MDB9LmdvbGR7Y29sb3I6dmFyKC0tZ29sZCl9LnVwe2NvbG9yOnZhcigtLWdyZWVuKX0uZG93bntjb2xvcjp2YXIoLS1yZWQpfS5mbGF0e2NvbG9yOiNkZGR9Lm11dGVke2NvbG9yOnZhcigtLW11dGVkKX0uc2VjdGlvbntmb250LXNpemU6MTlweDtmb250LXdlaWdodDo4MDA7Y29sb3I6dmFyKC0tZ29sZCk7bWFyZ2luOjIycHggMnB4IDEwcHh9LmdyaWR7ZGlzcGxheTpncmlkO2dyaWQtdGVtcGxhdGUtY29sdW1uczpyZXBlYXQoMiwxZnIpO2dhcDoxMHB4fS5wcmljZXtmb250LXNpemU6MjBweDtmb250LXdlaWdodDo4MDA7bWFyZ2luOjdweCAwfS5jaGFuZ2V7Zm9udC1zaXplOjE0cHh9Lmxpc3R7ZGlzcGxheTpmbGV4O2ZsZXgtZGlyZWN0aW9uOmNvbHVtbjtnYXA6OHB4fS5yb3d7YmFja2dyb3VuZDp2YXIoLS1jYXJkKTtib3JkZXI6MXB4IHNvbGlkIHZhcigtLWxpbmUpO2JvcmRlci1yYWRpdXM6MTRweDtwYWRkaW5nOjEycHg7ZGlzcGxheTpmbGV4O2FsaWduLWl0ZW1zOmNlbnRlcjtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2VlbjtnYXA6OHB4fS5yb3cuY2xpY2t7Y3Vyc29yOnBvaW50ZXJ9LnJhbmt7d2lkdGg6MjhweDtoZWlnaHQ6MjhweDtib3JkZXItcmFkaXVzOjlweDtiYWNrZ3JvdW5kOiMyYzIyMDg7Y29sb3I6dmFyKC0tZ29sZCk7ZGlzcGxheTpncmlkO3BsYWNlLWl0ZW1zOmNlbnRlcjtmb250LXdlaWdodDo4MDB9LnRhYnN7ZGlzcGxheTpmbGV4O2dhcDo3cHg7b3ZlcmZsb3c6YXV0bztwYWRkaW5nLWJvdHRvbTo0cHh9LnRhYntib3JkZXI6MXB4IHNvbGlkIHZhcigtLWxpbmUpO2JhY2tncm91bmQ6IzE0MTQxNDtjb2xvcjojZGRkO3BhZGRpbmc6OHB4IDEycHg7Ym9yZGVyLXJhZGl1czoxMnB4O3doaXRlLXNwYWNlOm5vd3JhcH0udGFiLmFjdGl2ZXtib3JkZXItY29sb3I6IzZiNTIxNDtjb2xvcjp2YXIoLS1nb2xkKTtiYWNrZ3JvdW5kOiMyNDFkMGJ9LmhlYXR7ZGlzcGxheTpncmlkO2dyaWQtdGVtcGxhdGUtY29sdW1uczpyZXBlYXQoMywxZnIpO2dhcDo4cHh9LmhlYXQgLmNhcmR7cGFkZGluZzoxMHB4O3RleHQtYWxpZ246Y2VudGVyfS5oZWF0VXB7Ym9yZGVyLWNvbG9yOiMxNDVjMzk7YmFja2dyb3VuZDojMGYyNDFifS5oZWF0RG93bntib3JkZXItY29sb3I6IzZjMjAyNTtiYWNrZ3JvdW5kOiMyNzExMTN9LmJhcntoZWlnaHQ6NnB4O2JhY2tncm91bmQ6IzI5MjkyOTtib3JkZXItcmFkaXVzOjk5cHg7b3ZlcmZsb3c6aGlkZGVufS5iYXI+aXtkaXNwbGF5OmJsb2NrO2hlaWdodDoxMDAlO2JhY2tncm91bmQ6dmFyKC0tZ29sZCk7Ym9yZGVyLXJhZGl1czo5OXB4fS5sb2Nre2JvcmRlcjoxcHggZGFzaGVkICM3MjViMWM7Y29sb3I6I2U3Yzc2ZDtiYWNrZ3JvdW5kOiMxYzE3MDk7Ym9yZGVyLXJhZGl1czoxNHB4O3BhZGRpbmc6MTRweDt0ZXh0LWFsaWduOmNlbnRlcn0uYnRue2JvcmRlcjowO2JvcmRlci1yYWRpdXM6MTJweDtwYWRkaW5nOjExcHggMTRweDtmb250LXdlaWdodDo4MDA7YmFja2dyb3VuZDp2YXIoLS1nb2xkKTtjb2xvcjojMTcxMjBhfS5idG4uZGFya3tiYWNrZ3JvdW5kOiMxZDFkMWQ7Y29sb3I6I2VlZTtib3JkZXI6MXB4IHNvbGlkICMzMzN9LnZpZXd7ZGlzcGxheTpub25lfS52aWV3LmFjdGl2ZXtkaXNwbGF5OmJsb2NrfWNhbnZhc3t3aWR0aDoxMDAlO2hlaWdodDoyNjBweDtiYWNrZ3JvdW5kOiMwZDBkMGQ7Ym9yZGVyOjFweCBzb2xpZCAjMjkyOTI5O2JvcmRlci1yYWRpdXM6MTRweH0ubWV0cmljc3tkaXNwbGF5OmdyaWQ7Z3JpZC10ZW1wbGF0ZS1jb2x1bW5zOnJlcGVhdCgzLDFmcik7Z2FwOjhweH0ubWV0cmlje2JhY2tncm91bmQ6IzExMTtib3JkZXI6MXB4IHNvbGlkICMyOTI5Mjk7Ym9yZGVyLXJhZGl1czoxMnB4O3BhZGRpbmc6MTBweDt0ZXh0LWFsaWduOmNlbnRlcn0ubWV0cmljIGJ7ZGlzcGxheTpibG9jazttYXJnaW4tdG9wOjVweH0ubmF2e3Bvc2l0aW9uOmZpeGVkO2JvdHRvbTowO2xlZnQ6MDtyaWdodDowO2JhY2tncm91bmQ6IzEwMTAxMGVGO2JvcmRlci10b3A6MXB4IHNvbGlkICMyOTI5Mjk7ZGlzcGxheTpmbGV4O2p1c3RpZnktY29udGVudDpjZW50ZXI7ei1pbmRleDo1fS5uYXZpbnt3aWR0aDptaW4oOTQwcHgsMTAwJSk7ZGlzcGxheTpncmlkO2dyaWQtdGVtcGxhdGUtY29sdW1uczpyZXBlYXQoNSwxZnIpfS5uYXYgYnV0dG9ue2JhY2tncm91bmQ6bm9uZTtib3JkZXI6MDtjb2xvcjojYWFhO3BhZGRpbmc6MTFweCAzcHg7Zm9udC1zaXplOjExcHh9Lm5hdiBidXR0b24uYWN0aXZle2NvbG9yOnZhcigtLWdvbGQpfS5lbXB0eXtjb2xvcjojYWFhO3RleHQtYWxpZ246Y2VudGVyO3BhZGRpbmc6MjBweH0udGlueXtmb250LXNpemU6MTFweH0uZmxleHtkaXNwbGF5OmZsZXg7Z2FwOjhweDthbGlnbi1pdGVtczpjZW50ZXI7anVzdGlmeS1jb250ZW50OnNwYWNlLWJldHdlZW59QG1lZGlhKG1pbi13aWR0aDo3MDBweCl7LmdyaWR7Z3JpZC10ZW1wbGF0ZS1jb2x1bW5zOnJlcGVhdCgzLDFmcil9LmhlYXR7Z3JpZC10ZW1wbGF0ZS1jb2x1bW5zOnJlcGVhdCg0LDFmcil9fQo8L3N0eWxlPjwvaGVhZD48Ym9keT48ZGl2IGNsYXNzPSJ3cmFwIj48ZGl2IGNsYXNzPSJicmFuZCI+PGRpdj48aDE+2LfZhNin24zYp9ixPC9oMT48ZGl2IGNsYXNzPSJtdXRlZCB0aW55Ij7Yr9in2LTYqNmI2LHYryDYs9io2qkg2Ygg2YfZiNi02YXZhtivINio2KfYstin2LE8L2Rpdj48L2Rpdj48c3BhbiBjbGFzcz0icGlsbCIgaWQ9InRpZXIiPi4uLjwvc3Bhbj48L2Rpdj4KPGRpdiBpZD0icHVsc2UiIGNsYXNzPSJ2aWV3IGFjdGl2ZSI+PGRpdiBjbGFzcz0iaGVybyI+PGRpdiBjbGFzcz0iaGVyb1RvcCI+PGRpdj48ZGl2IGNsYXNzPSJtdXRlZCI+2YbYqNi2INio2KfYstin2LE8L2Rpdj48ZGl2IGlkPSJwdWxzZVN0YXRlIiBjbGFzcz0icHJpY2UiPuKAlDwvZGl2PjwvZGl2PjxkaXY+PHNwYW4gaWQ9InB1bHNlU2NvcmUiIGNsYXNzPSJzY29yZSBnb2xkIj7igJQ8L3NwYW4+PHNwYW4gY2xhc3M9Im11dGVkIj4vMTAwPC9zcGFuPjwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImJhciI+PGkgaWQ9InB1bHNlQmFyIiBzdHlsZT0id2lkdGg6MCI+PC9pPjwvZGl2PjxkaXYgaWQ9InB1bHNlTWV0YSIgY2xhc3M9Im11dGVkIHRpbnkiIHN0eWxlPSJtYXJnaW4tdG9wOjlweCI+PC9kaXY+PC9kaXY+PGRpdiBjbGFzcz0ic2VjdGlvbiI+2YLbjNmF2KrigIzZh9in24wg2YTYrdi42YfigIzYp9uMPC9kaXY+PGRpdiBpZD0icHJpY2VzIiBjbGFzcz0iZ3JpZCI+PC9kaXY+PGRpdiBjbGFzcz0ic2VjdGlvbiI+2KjbjNi02KrYsduM2YYg2K3Ysdqp2Ko8L2Rpdj48ZGl2IGlkPSJtb3ZlcnMiIGNsYXNzPSJsaXN0Ij48L2Rpdj48L2Rpdj4KPGRpdiBpZD0ic2Nhbm5lciIgY2xhc3M9InZpZXciPjxkaXYgY2xhc3M9InNlY3Rpb24iPvCfjq8gT3Bwb3J0dW5pdHkgU2Nhbm5lcjwvZGl2PjxkaXYgaWQ9InNjYW5uZXJCb2R5Ij48L2Rpdj48L2Rpdj4KPGRpdiBpZD0iaGVhdG1hcCIgY2xhc3M9InZpZXciPjxkaXYgY2xhc3M9InNlY3Rpb24iPvCfl7og2YbZgti02Ycg2KjYp9iy2KfYsTwvZGl2PjxkaXYgaWQ9ImhlYXRCb2R5IiBjbGFzcz0iaGVhdCI+PC9kaXY+PC9kaXY+CjxkaXYgaWQ9ImFzc2V0IiBjbGFzcz0idmlldyI+PGRpdiBjbGFzcz0iZmxleCI+PGJ1dHRvbiBjbGFzcz0iYnRuIGRhcmsiIG9uY2xpY2s9ImdvKCdwdWxzZScpIj7ihqkg2KjYp9iy2q/YtNiqPC9idXR0b24+PGRpdiBpZD0iYXNzZXRUaXRsZSIgY2xhc3M9InNlY3Rpb24iIHN0eWxlPSJtYXJnaW46MCI+PC9kaXY+PC9kaXY+PGRpdiBpZD0iYXNzZXRCb2R5IiBzdHlsZT0ibWFyZ2luLXRvcDoxMnB4Ij48L2Rpdj48L2Rpdj4KPGRpdiBpZD0ibW9yZSIgY2xhc3M9InZpZXciPjxkaXYgY2xhc3M9InNlY3Rpb24iPtin2KjYstin2LHZh9in24wg2K3YsdmB2YfigIzYp9uMPC9kaXY+PGRpdiBjbGFzcz0ibGlzdCI+PGRpdiBjbGFzcz0icm93IGNsaWNrIiBvbmNsaWNrPSJsb2FkRmFpcigpIj48c3Bhbj7wn6unIEZhaXIgVmFsdWUgLyBCdWJibGUgTWFwPC9zcGFuPjxzcGFuPlZJUDwvc3Bhbj48L2Rpdj48ZGl2IGNsYXNzPSJyb3cgY2xpY2siIG9uY2xpY2s9ImxvYWRNZWx0ZWRQcm8oKSI+PHNwYW4+8J+UpSDZhdix2qnYsiDYotio4oCM2LTYr9mHIFBybzwvc3Bhbj48c3Bhbj5WSVA8L3NwYW4+PC9kaXY+PC9kaXY+PGRpdiBpZD0ibW9yZUJvZHkiIHN0eWxlPSJtYXJnaW4tdG9wOjEycHgiPjwvZGl2PjwvZGl2PjwvZGl2Pgo8ZGl2IGNsYXNzPSJuYXYiPjxkaXYgY2xhc3M9Im5hdmluIj48YnV0dG9uIGRhdGEtdj0icHVsc2UiIGNsYXNzPSJhY3RpdmUiIG9uY2xpY2s9ImdvKCdwdWxzZScpIj7il4k8YnI+2b7Yp9mE2LM8L2J1dHRvbj48YnV0dG9uIGRhdGEtdj0ic2Nhbm5lciIgb25jbGljaz0iZ28oJ3NjYW5uZXInKSI+8J+Orzxicj7Yp9iz2qnZhtixPC9idXR0b24+PGJ1dHRvbiBkYXRhLXY9ImhlYXRtYXAiIG9uY2xpY2s9ImdvKCdoZWF0bWFwJykiPuKWpjxicj7ZhtmC2LTZhzwvYnV0dG9uPjxidXR0b24gZGF0YS12PSJhc3NldCIgb25jbGljaz0ib3BlbkFzc2V0KCdnb2xkMTgnKSI+8J+TiDxicj7Yr9in2LHYp9uM24w8L2J1dHRvbj48YnV0dG9uIGRhdGEtdj0ibW9yZSIgb25jbGljaz0iZ28oJ21vcmUnKSI+4piwPGJyPtio24zYtNiq2LE8L2J1dHRvbj48L2Rpdj48L2Rpdj4KPHNjcmlwdD4KY29uc3QgdGc9d2luZG93LlRlbGVncmFtPy5XZWJBcHA7aWYodGcpe3RnLnJlYWR5KCk7dGcuZXhwYW5kKCl9bGV0IHN0YXRlPXtvdmVydmlldzpudWxsLHZpcDpmYWxzZSxhc3NldDonZ29sZDE4J307Y29uc3QgJD1pZD0+ZG9jdW1lbnQuZ2V0RWxlbWVudEJ5SWQoaWQpO2NvbnN0IGVzYz14PT5TdHJpbmcoeD8/JycpLnJlcGxhY2UoL1smPD5dL2csbT0+KHsnJic6JyZhbXA7JywnPCc6JyZsdDsnLCc+JzonJmd0Oyd9W21dKSk7Y29uc3QgZm10PXg9Png9PW51bGw/J+KAlCc6TnVtYmVyKHgpLnRvTG9jYWxlU3RyaW5nKCdlbi1VUycse21heGltdW1GcmFjdGlvbkRpZ2l0czoyfSk7Y29uc3QgY2xzPW49Pm4+MD8ndXAnOm48MD8nZG93bic6J2ZsYXQnO2NvbnN0IGFycm93PW49Pm4+MD8n4payJzpuPDA/J+KWvCc6J+KAoic7CmFzeW5jIGZ1bmN0aW9uIGFwaShyb3V0ZSxwPXt9KXtjb25zdCByPWF3YWl0IGZldGNoKHJvdXRlLHttZXRob2Q6J1BPU1QnLGhlYWRlcnM6eydDb250ZW50LVR5cGUnOidhcHBsaWNhdGlvbi9qc29uJ30sYm9keTpKU09OLnN0cmluZ2lmeSh7Li4ucCxpbml0RGF0YTp0Zz8uaW5pdERhdGF8fCcnfSl9KTtsZXQgZD17fTt0cnl7ZD1hd2FpdCByLmpzb24oKX1jYXRjaChlKXt9aWYoIXIub2spdGhyb3cgT2JqZWN0LmFzc2lnbihuZXcgRXJyb3IoZC5lcnJvcnx8J9iu2LfYp9uMINin2LHYqtio2KfYtycpLHtzdGF0dXM6ci5zdGF0dXMsZGF0YTpkfSk7cmV0dXJuIGR9CmZ1bmN0aW9uIGdvKHYpe2RvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJy52aWV3JykuZm9yRWFjaCh4PT54LmNsYXNzTGlzdC5yZW1vdmUoJ2FjdGl2ZScpKTskKHYpLmNsYXNzTGlzdC5hZGQoJ2FjdGl2ZScpO2RvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJy5uYXYgYnV0dG9uJykuZm9yRWFjaCh4PT54LmNsYXNzTGlzdC50b2dnbGUoJ2FjdGl2ZScseC5kYXRhc2V0LnY9PT12KSk7aWYodj09PSdzY2FubmVyJylsb2FkU2Nhbm5lcigpfQpmdW5jdGlvbiByZW5kZXJPdmVydmlldyhkKXtzdGF0ZS5vdmVydmlldz1kO3N0YXRlLnZpcD0hIWQudmlwOyQoJ3RpZXInKS50ZXh0Q29udGVudD1kLnZpcD8nVklQINmB2LnYp9mEJzon2K3Ys9in2Kgg2LHYp9uM2q/Yp9mGJzskKCdwdWxzZVNjb3JlJykudGV4dENvbnRlbnQ9ZC5wdWxzZT8uc2NvcmU/PyfigJQnOyQoJ3B1bHNlQmFyJykuc3R5bGUud2lkdGg9KGQucHVsc2U/LnNjb3JlfHwwKSsnJSc7JCgncHVsc2VTdGF0ZScpLnRleHRDb250ZW50PWQucHVsc2U/LnN0YXRlfHwn4oCUJzskKCdwdWxzZVN0YXRlJykuY2xhc3NOYW1lPSdwcmljZSAnKyhkLnB1bHNlPy5zdGF0ZT09PSfYtdi52YjYr9uMJz8ndXAnOmQucHVsc2U/LnN0YXRlPT09J9mG2LLZiNmE24wnPydkb3duJzonZmxhdCcpOyQoJ3B1bHNlTWV0YScpLnRleHRDb250ZW50PWDZhdir2KjYqiAke2QucHVsc2U/LnBvc2l0aXZlfHwwfSDigKIg2YXZhtmB24wgJHtkLnB1bHNlPy5uZWdhdGl2ZXx8MH0g4oCiINio2LHZiNiy2LHYs9in2YbbjCAke2QudXBkYXRlZF9hdH1gOwokKCdwcmljZXMnKS5pbm5lckhUTUw9KGQuaXRlbXN8fFtdKS5tYXAoaT0+YDxkaXYgY2xhc3M9ImNhcmQgcm93IGNsaWNrIiBzdHlsZT0iZGlzcGxheTpibG9jayIgb25jbGljaz0ib3BlbkFzc2V0KCcke2kua2V5fScpIj48ZGl2IGNsYXNzPSJtdXRlZCI+JHtlc2MoaS5sYWJlbCl9PC9kaXY+PGRpdiBjbGFzcz0icHJpY2UgJHtjbHMoaS5jaGFuZ2UpfSI+JHtmbXQoaS5wcmljZSl9IDxzbWFsbD4ke2VzYyhpLnVuaXQpfTwvc21hbGw+PC9kaXY+PGRpdiBjbGFzcz0iY2hhbmdlICR7Y2xzKGkuY2hhbmdlKX0iPiR7YXJyb3coaS5jaGFuZ2UpfSAke051bWJlcihpLmNoYW5nZXx8MCkudG9GaXhlZCgyKX0lPC9kaXY+JHtpLnNvdXJjZT09PSdkZXJpdmVkJz8nPGRpdiBjbGFzcz0idGlueSBtdXRlZCI+2KjYsdii2YjYsdivINmG2LjYsduMPC9kaXY+JzonJ308L2Rpdj5gKS5qb2luKCcnKTskKCdtb3ZlcnMnKS5pbm5lckhUTUw9KGQubW92ZXJzfHxbXSkubWFwKChpLG4pPT5gPGRpdiBjbGFzcz0icm93IGNsaWNrIiBvbmNsaWNrPSJvcGVuQXNzZXQoJyR7aS5rZXl9JykiPjxkaXYgY2xhc3M9ImZsZXgiPjxzcGFuIGNsYXNzPSJyYW5rIj4ke24rMX08L3NwYW4+PHNwYW4+JHtlc2MoaS5sYWJlbCl9PC9zcGFuPjwvZGl2PjxiIGNsYXNzPSIke2NscyhpLmNoYW5nZSl9Ij4ke2Fycm93KGkuY2hhbmdlKX0gJHtOdW1iZXIoaS5jaGFuZ2V8fDApLnRvRml4ZWQoMil9JTwvYj48L2Rpdj5gKS5qb2luKCcnKTskKCdoZWF0Qm9keScpLmlubmVySFRNTD0oZC5oZWF0bWFwfHxbXSkubWFwKGk9PmA8ZGl2IGNsYXNzPSJjYXJkICR7aS5jaGFuZ2U+MD8naGVhdFVwJzppLmNoYW5nZTwwPydoZWF0RG93bic6Jyd9IiBvbmNsaWNrPSJvcGVuQXNzZXQoJyR7aS5rZXl9JykiPjxkaXYgY2xhc3M9InRpbnkiPiR7ZXNjKGkubGFiZWwpfTwvZGl2PjxkaXYgY2xhc3M9InByaWNlIiBzdHlsZT0iZm9udC1zaXplOjE1cHgiPiR7Zm10KGkucHJpY2UpfTwvZGl2PjxkaXYgY2xhc3M9IiR7Y2xzKGkuY2hhbmdlKX0gdGlueSI+JHtOdW1iZXIoaS5jaGFuZ2V8fDApLnRvRml4ZWQoMil9JTwvZGl2PjwvZGl2PmApLmpvaW4oJycpfQphc3luYyBmdW5jdGlvbiBsb2FkKCl7dHJ5e3JlbmRlck92ZXJ2aWV3KGF3YWl0IGFwaSgnL2FwaS9vdmVydmlldycpKX1jYXRjaChlKXskKCdwcmljZXMnKS5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yrti32Kcg2K/YsSDYr9ix24zYp9mB2Kog2K/Yp9i02KjZiNix2K88L2Rpdj4nfX0KYXN5bmMgZnVuY3Rpb24gbG9hZFNjYW5uZXIoKXtsZXQgYj0kKCdzY2FubmVyQm9keScpO2lmKCFzdGF0ZS52aXApe2IuaW5uZXJIVE1MPSc8ZGl2IGNsYXNzPSJsb2NrIj7irZAgT3Bwb3J0dW5pdHkgU2Nhbm5lciDZhdiu2LXZiNi1IFZJUCDYp9iz2KouINiu2LHbjNivINmIINmF2K/bjNix24zYqiBWSVAg2KfYsiDYr9in2K7ZhCDYsdio2KfYqiDYp9mG2KzYp9mFINmF24zigIzYtNmI2K8uPC9kaXY+JztyZXR1cm59Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yr9ixINit2KfZhCDYqtit2YTbjNmE4oCmPC9kaXY+Jzt0cnl7bGV0IGQ9YXdhaXQgYXBpKCcvYXBpL3NjYW5uZXInKTtiLmlubmVySFRNTD0oZC5pdGVtc3x8W10pLm1hcCgoaSxuKT0+YDxkaXYgY2xhc3M9InJvdyBjbGljayIgb25jbGljaz0ib3BlbkFzc2V0KCcke2kua2V5fScpIj48c3BhbiBjbGFzcz0icmFuayI+JHtuKzF9PC9zcGFuPjxzcGFuIHN0eWxlPSJmbGV4OjEiPiR7ZXNjKGkubGFiZWwpfTxicj48c3BhbiBjbGFzcz0idGlueSBtdXRlZCI+JHtlc2MoaS5yZWdpbWV8fCfigJQnKX0g4oCiIFEgJHtpLnE/PyfigJQnfTwvc3Bhbj48L3NwYW4+PGIgY2xhc3M9ImdvbGQiPiR7aS5zY29yZT8/J+KAlCd9LzEwMDwvYj48L2Rpdj5gKS5qb2luKCcnKXx8JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yr9in2K/ZhyDaqdin2YHbjCDZhtuM2LPYqjwvZGl2Pid9Y2F0Y2goZSl7Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yrti32Kcg2K/YsSDYp9iz2qnZhjwvZGl2Pid9fQphc3luYyBmdW5jdGlvbiBvcGVuQXNzZXQoa2V5KXtzdGF0ZS5hc3NldD1rZXk7Z28oJ2Fzc2V0Jyk7JCgnYXNzZXRUaXRsZScpLnRleHRDb250ZW50PSfYr9ixINit2KfZhCDYqNin2LHar9iw2KfYsduM4oCmJzskKCdhc3NldEJvZHknKS5pbm5lckhUTUw9Jyc7dHJ5e2xldCBkPWF3YWl0IGFwaSgnL2FwaS9hc3NldCcse2Fzc2V0OmtleX0pOyQoJ2Fzc2V0VGl0bGUnKS50ZXh0Q29udGVudD1kLmFzc2V0LmxhYmVsO2xldCBhPWQuYXNzZXQ7bGV0IHRlY2g9ZC50ZWNobmljYWw7bGV0IGh0bWw9YDxkaXYgY2xhc3M9Imhlcm8iPjxkaXYgY2xhc3M9Im11dGVkIj7ZgtuM2YXYqiDZgdi52YTbjDwvZGl2PjxkaXYgY2xhc3M9InNjb3JlICR7Y2xzKGEuY2hhbmdlKX0iPiR7Zm10KGEucHJpY2UpfTwvZGl2PjxkaXY+JHtlc2MoYS51bml0KX0gPHNwYW4gY2xhc3M9IiR7Y2xzKGEuY2hhbmdlKX0iPiR7YXJyb3coYS5jaGFuZ2UpfSAke051bWJlcihhLmNoYW5nZXx8MCkudG9GaXhlZCgyKX0lPC9zcGFuPjwvZGl2PjwvZGl2PmA7aWYodGVjaCl7aHRtbCs9YDxkaXYgY2xhc3M9InNlY3Rpb24iPtiq2K3ZhNuM2YQgVklQPC9kaXY+PGRpdiBjbGFzcz0ibWV0cmljcyI+PGRpdiBjbGFzcz0ibWV0cmljIj7Zgtiv2LHYqjxiPiR7dGVjaC5zY29yZT8/J+KAlCd9LzEwMDwvYj48L2Rpdj48ZGl2IGNsYXNzPSJtZXRyaWMiPlEg2qnbjNmB24zYqjxiPiR7dGVjaC5xPz8n4oCUJ30vMTAwPC9iPjwvZGl2PjxkaXYgY2xhc3M9Im1ldHJpYyI+2LHamNuM2YU8Yj4ke2VzYyh0ZWNoLnJlZ2ltZXx8J+KAlCcpfTwvYj48L2Rpdj48ZGl2IGNsYXNzPSJtZXRyaWMiPlJTSTxiPiR7dGVjaC5yc2k9PW51bGw/J+KAlCc6TnVtYmVyKHRlY2gucnNpKS50b0ZpeGVkKDEpfTwvYj48L2Rpdj48ZGl2IGNsYXNzPSJtZXRyaWMiPkVNQSA5LzIxPGI+JHt0ZWNoLmVtYTkmJnRlY2guZW1hMjE/KHRlY2guZW1hOT50ZWNoLmVtYTIxPyfYtdi52YjYr9uMJzon2YbYstmI2YTbjCcpOifigJQnfTwvYj48L2Rpdj48ZGl2IGNsYXNzPSJtZXRyaWMiPtmG2YjYs9in2YY8Yj4ke3RlY2gudm9sPT1udWxsPyfigJQnOk51bWJlcih0ZWNoLnZvbCkudG9GaXhlZCgyKSsnJSd9PC9iPjwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9InNlY3Rpb24iPtit2YXYp9uM2KogLyDZhdmC2KfZiNmF2Ko8L2Rpdj48ZGl2IGNsYXNzPSJtZXRyaWNzIj48ZGl2IGNsYXNzPSJtZXRyaWMiPtit2YXYp9uM2Ko8Yj4ke2ZtdCh0ZWNoLnN1cHBvcnQpfTwvYj48L2Rpdj48ZGl2IGNsYXNzPSJtZXRyaWMiPtmC24zZhdiqPGI+JHtmbXQoYS5wcmljZSl9PC9iPjwvZGl2PjxkaXYgY2xhc3M9Im1ldHJpYyI+2YXZgtin2YjZhdiqPGI+JHtmbXQodGVjaC5yZXNpc3RhbmNlKX08L2I+PC9kaXY+PC9kaXY+YH1lbHNlIGh0bWwrPSc8ZGl2IGNsYXNzPSJsb2NrIiBzdHlsZT0ibWFyZ2luLXRvcDoxMnB4Ij7wn5SSIFJTSdiMIEVNQdiMINit2YXYp9uM2Kov2YXZgtin2YjZhdiq2IwgTWFya2V0IFJlZ2ltZSDZiCBRINmF2K7YtdmI2LUgVklQINmH2LPYqtmG2K8uPC9kaXY+JztodG1sKz1gPGRpdiBjbGFzcz0ic2VjdGlvbiI+2YbZhdmI2K/Yp9ixINqp2YbYr9mE24w8L2Rpdj48ZGl2IGNsYXNzPSJ0YWJzIiBpZD0idGYiPjxidXR0b24gY2xhc3M9InRhYiIgb25jbGljaz0ibG9hZENoYXJ0KCcxSCcsdGhpcykiPjFIIOKtkDwvYnV0dG9uPjxidXR0b24gY2xhc3M9InRhYiIgb25jbGljaz0ibG9hZENoYXJ0KCc0SCcsdGhpcykiPjRIIOKtkDwvYnV0dG9uPjxidXR0b24gY2xhc3M9InRhYiBhY3RpdmUiIG9uY2xpY2s9ImxvYWRDaGFydCgnMjRIJyx0aGlzKSI+MjRIPC9idXR0b24+PGJ1dHRvbiBjbGFzcz0idGFiIiBvbmNsaWNrPSJsb2FkQ2hhcnQoJzdEJyx0aGlzKSI+N0Qg4q2QPC9idXR0b24+PGJ1dHRvbiBjbGFzcz0idGFiIiBvbmNsaWNrPSJsb2FkQ2hhcnQoJzMwRCcsdGhpcykiPjMwRCDirZA8L2J1dHRvbj48L2Rpdj48Y2FudmFzIGlkPSJjaGFydCIgd2lkdGg9IjgwMCIgaGVpZ2h0PSIzNjAiPjwvY2FudmFzPjxkaXYgaWQ9ImNoYXJ0Tm90ZSIgY2xhc3M9InRpbnkgbXV0ZWQiIHN0eWxlPSJtYXJnaW4tdG9wOjdweCI+PC9kaXY+YDskKCdhc3NldEJvZHknKS5pbm5lckhUTUw9aHRtbDtzZXRUaW1lb3V0KCgpPT5sb2FkQ2hhcnQoJzI0SCcsZG9jdW1lbnQucXVlcnlTZWxlY3RvcignI3RmIC5hY3RpdmUnKSksMCl9Y2F0Y2goZSl7JCgnYXNzZXRCb2R5JykuaW5uZXJIVE1MPSc8ZGl2IGNsYXNzPSJlbXB0eSI+2KfYt9mE2KfYudin2Kog2K/Yp9ix2KfbjNuMINiv2LEg2K/Ys9iq2LHYsyDZhtuM2LPYqi48L2Rpdj4nfX0KYXN5bmMgZnVuY3Rpb24gbG9hZENoYXJ0KHRmLGVsKXtkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCcjdGYgLnRhYicpLmZvckVhY2goeD0+eC5jbGFzc0xpc3QucmVtb3ZlKCdhY3RpdmUnKSk7aWYoZWwpZWwuY2xhc3NMaXN0LmFkZCgnYWN0aXZlJyk7dHJ5e2xldCBkPWF3YWl0IGFwaSgnL2FwaS9jYW5kbGVzJyx7YXNzZXQ6c3RhdGUuYXNzZXQsdGltZWZyYW1lOnRmfSk7ZHJhd0NhbmRsZXMoZC5jYW5kbGVzfHxbXSk7JCgnY2hhcnROb3RlJykudGV4dENvbnRlbnQ9ZC5ub3RlfHwnJ31jYXRjaChlKXtpZihlLnN0YXR1cz09PTQwMyl7JCgnY2hhcnROb3RlJykudGV4dENvbnRlbnQ9J+KtkCDYp9uM2YYg2KrYp9uM2YXigIzZgdix24zZhSDZhdiu2LXZiNi1IFZJUCDYp9iz2KouJztkcmF3Q2FuZGxlcyhbXSl9ZWxzZXskKCdjaGFydE5vdGUnKS50ZXh0Q29udGVudD0n2K/Yp9iv2Ycg2qnYp9mB24wg2KjYsdin24wg2YbZhdmI2K/Yp9ixINmI2KzZiNivINmG2K/Yp9ix2K8uJztkcmF3Q2FuZGxlcyhbXSl9fX0KZnVuY3Rpb24gZHJhd0NhbmRsZXMoYyl7Y29uc3QgY3Y9JCgnY2hhcnQnKTtpZighY3YpcmV0dXJuO2NvbnN0IGN0eD1jdi5nZXRDb250ZXh0KCcyZCcpLFc9Y3Yud2lkdGgsSD1jdi5oZWlnaHQ7Y3R4LmNsZWFyUmVjdCgwLDAsVyxIKTtjdHguZmlsbFN0eWxlPScjMGQwZDBkJztjdHguZmlsbFJlY3QoMCwwLFcsSCk7aWYoIWMubGVuZ3RoKXtjdHguZmlsbFN0eWxlPScjODg4JztjdHgudGV4dEFsaWduPSdjZW50ZXInO2N0eC5mb250PScyMnB4IFRhaG9tYSc7Y3R4LmZpbGxUZXh0KCfYr9in2K/ZhyDaqdin2YHbjCDZhtuM2LPYqicsVy8yLEgvMik7cmV0dXJufWNvbnN0IGhpPU1hdGgubWF4KC4uLmMubWFwKHg9PnguaCkpLGxvPU1hdGgubWluKC4uLmMubWFwKHg9PngubCkpLHBhZD0oaGktbG98fDEpKi4wOCxtYXg9aGkrcGFkLG1pbj1sby1wYWQseT1wPT5ILTIyLShwLW1pbikvKG1heC1taW4pKihILTQ0KSxjdz1NYXRoLm1heCgzLChXLTM1KS9jLmxlbmd0aCouNTgpLHN0ZXA9KFctMzUpL2MubGVuZ3RoO2N0eC5zdHJva2VTdHlsZT0nIzIyMic7Zm9yKGxldCBpPTE7aTw1O2krKyl7Y3R4LmJlZ2luUGF0aCgpO2N0eC5tb3ZlVG8oMTUsSCppLzUpO2N0eC5saW5lVG8oVy0xMCxIKmkvNSk7Y3R4LnN0cm9rZSgpfWMuZm9yRWFjaCgoeCxpKT0+e2xldCB4eD0yMCtpKnN0ZXArc3RlcC8yLGNvbD14LmM+PXgubz8nIzI4ZDE3Yyc6JyNmZjRkNTUnO2N0eC5zdHJva2VTdHlsZT1jb2w7Y3R4LmZpbGxTdHlsZT1jb2w7Y3R4LmJlZ2luUGF0aCgpO2N0eC5tb3ZlVG8oeHgseSh4LmgpKTtjdHgubGluZVRvKHh4LHkoeC5sKSk7Y3R4LnN0cm9rZSgpO2xldCB5bz15KHgubykseWM9eSh4LmMpLHRvcD1NYXRoLm1pbih5byx5YyksaGg9TWF0aC5tYXgoMixNYXRoLmFicyh5by15YykpO2N0eC5maWxsUmVjdCh4eC1jdy8yLHRvcCxjdyxoaCl9KTtjdHguZmlsbFN0eWxlPScjYWFhJztjdHguZm9udD0nMTVweCBUYWhvbWEnO2N0eC50ZXh0QWxpZ249J2xlZnQnO2N0eC5maWxsVGV4dChmbXQoaGkpLDgsMTcpO2N0eC5maWxsVGV4dChmbXQobG8pLDgsSC02KX0KYXN5bmMgZnVuY3Rpb24gbG9hZEZhaXIoKXtnbygnbW9yZScpO2xldCBiPSQoJ21vcmVCb2R5Jyk7aWYoIXN0YXRlLnZpcCl7Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImxvY2siPuKtkCBGYWlyIFZhbHVlIC8gQnViYmxlIE1hcCDZhdiu2LXZiNi1IFZJUCDYp9iz2KouPC9kaXY+JztyZXR1cm59Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yr9ixINit2KfZhCDZhdit2KfYs9io2YfigKY8L2Rpdj4nO3RyeXtsZXQgZD1hd2FpdCBhcGkoJy9hcGkvZmFpci12YWx1ZScpO2IuaW5uZXJIVE1MPSc8ZGl2IGNsYXNzPSJsaXN0Ij4nKyhkLml0ZW1zfHxbXSkubWFwKGk9PmA8ZGl2IGNsYXNzPSJyb3ciPjxzcGFuPiR7ZXNjKGkubGFiZWwpfTxicj48c3BhbiBjbGFzcz0idGlueSBtdXRlZCI+2KjYp9iy2KfYsSAke2ZtdChpLm1hcmtldCl9IOKAoiDZhti42LHbjCAke2ZtdChpLmZhaXIpfTwvc3Bhbj48L3NwYW4+PGIgY2xhc3M9IiR7Y2xzKGkucGN0KX0iPiR7TnVtYmVyKGkucGN0KS50b0ZpeGVkKDIpfSU8L2I+PC9kaXY+YCkuam9pbignJykrJzwvZGl2Pid9Y2F0Y2goZSl7Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yr9in2K/ZhyDaqdin2YHbjCDZhtuM2LPYqjwvZGl2Pid9fQphc3luYyBmdW5jdGlvbiBsb2FkTWVsdGVkUHJvKCl7Z28oJ21vcmUnKTtsZXQgYj0kKCdtb3JlQm9keScpO2lmKCFzdGF0ZS52aXApe2IuaW5uZXJIVE1MPSc8ZGl2IGNsYXNzPSJsb2NrIj7irZAg2YXYsdqp2LIg2KLYqOKAjNi02K/ZhyBQcm8g2YXYrti12YjYtSBWSVAg2KfYs9iqLjwvZGl2Pic7cmV0dXJufWxldCBtPXN0YXRlLm92ZXJ2aWV3Py5tZWx0ZWR8fHt9O2IuaW5uZXJIVE1MPWA8ZGl2IGNsYXNzPSJncmlkIj48ZGl2IGNsYXNzPSJjYXJkIj48ZGl2IGNsYXNzPSJtdXRlZCI+2KLYqOKAjNi02K/ZhyDZhtmC2K/bjDwvZGl2PjxkaXYgY2xhc3M9InByaWNlIj4ke2ZtdChtLmNhc2gpfTwvZGl2PjxkaXYgY2xhc3M9InRpbnkiPiR7ZXNjKG0uY2FzaF9zb3VyY2V8fCcnKX08L2Rpdj48L2Rpdj48ZGl2IGNsYXNzPSJjYXJkIj48ZGl2IGNsYXNzPSJtdXRlZCI+2KLYqOKAjNi02K/ZhyDZgdix2K/Yp9uM24w8L2Rpdj48ZGl2IGNsYXNzPSJwcmljZSI+JHtmbXQobS5mdXR1cmUpfTwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImNhcmQiPjxkaXYgY2xhc3M9Im11dGVkIj7Yp9iu2KrZhNin2YE8L2Rpdj48ZGl2IGNsYXNzPSJwcmljZSAke2NscyhtLnNwcmVhZHx8MCl9Ij4ke2ZtdChtLnNwcmVhZCl9PC9kaXY+PGRpdj4ke20uc3ByZWFkX3BjdD09bnVsbD8n4oCUJzpOdW1iZXIobS5zcHJlYWRfcGN0KS50b0ZpeGVkKDIpKyclJ308L2Rpdj48L2Rpdj48ZGl2IGNsYXNzPSJjYXJkIj48ZGl2IGNsYXNzPSJtdXRlZCI+2KrZh9ix2KfZhiAvINmH2LHYp9iqIC8g2K/YsdmH2YU8L2Rpdj48ZGl2PiR7Zm10KG0udXNkKX0gLyAke2ZtdChtLmhlcmF0KX0gLyAke2ZtdChtLmFlZCl9PC9kaXY+PC9kaXY+PC9kaXY+YH0KbG9hZCgpO3NldEludGVydmFsKGxvYWQsMzAwMDApOwo8L3NjcmlwdD48L2JvZHk+PC9odG1sPg==").decode("utf-8")

def build_bubble_radar(market):
    lines=["🫧 <b>رادار حباب / انحراف ارزش</b>", ""]
    for asset in ("gold18","melted","emami","half","quarter"):
        snap=_fair_value_snapshot(market, asset)
        label=ALERT_ASSETS[asset]["label"]
        if not snap:
            lines.append(f"• {label}: داده کافی نیست")
            continue
        z,n=_bubble_z(asset)
        zt = f" | Z30: {z:+.2f}σ" if z is not None else f" | آرشیو حباب: {n} نمونه"
        state = "گسترش مثبت" if snap["pct"] > 0 else "زیر ارزش نظری"
        lines.append(f"• <b>{label}</b>: {snap['pct']:+.2f}% ({state}){zt}")
        lines.append(f"  بازار {_format_number(snap['market'])} | نظری {_format_number(snap['fair'])}")
    lines += ["", "<i>برای ارز و کریپتو «حباب کلاسیک» نمایش داده نمی‌شود؛ آن‌ها با Z-Score و انحراف آماری سنجیده می‌شوند.</i>"]
    return "\n".join(lines)


def build_heatmap(market):
    rows=[]
    for asset in ("usd","gold18","melted","melted_future","herat_usd","aed","emami","half","quarter","ounce","btc","eth","usdt"):
        f=_market_features(asset, market)
        if f.get("price") is None: continue
        impulse=f.get("v60")
        mark="🟢" if impulse is not None and impulse > 0.15 else ("🔴" if impulse is not None and impulse < -0.15 else "⚪")
        score="—" if f.get("score") is None else str(f["score"])
        rows.append(f"{mark} {ALERT_ASSETS[asset]['label']}: 1h {_fmt_pct(impulse)} | قدرت {score}")
    return "🌡 <b>هیت‌مپ نوسان بازار</b>\n\n" + ("\n".join(rows) if rows else "داده کافی نیست") + "\n\n<i>رنگ بر اساس جهت حرکت یک‌ساعته است، نه سیگنال معامله.</i>"


def build_opportunity_scanner(market):
    candidates=[]
    for asset in ALERT_ASSETS:
        f=_market_features(asset, market)
        if f.get("score") is None: continue
        strength=abs(f["score"]-50)
        if f.get("breakout") != "none": strength += 15
        if f.get("abnormal"): strength += 10
        # Penalize severely overextended conditions to avoid ranking pure chasing as best opportunity.
        if f.get("z") is not None and abs(f["z"]) > 2.5: strength -= 8
        candidates.append((strength, asset, f))
    candidates.sort(reverse=True, key=lambda x:x[0])
    lines=["🎯 <b>Opportunity Scanner</b>", "رتبه‌بندی بر اساس شدت حرکت + همگرایی + شکست + کیفیت داده؛ نه پیشنهاد خرید.", ""]
    for rank,(_,asset,f) in enumerate(candidates[:7],1):
        direction="⬆️" if (f["score"] or 50)>50 else ("⬇️" if (f["score"] or 50)<50 else "➡️")
        flags=[]
        if f.get("breakout") != "none": flags.append("Breakout")
        if f.get("abnormal"): flags.append("Vol Spike")
        if f.get("z") is not None and abs(f["z"])>=2: flags.append("Extended")
        lines.append(f"{rank}. {direction} <b>{ALERT_ASSETS[asset]['label']}</b> — قدرت {f['score']}/100 | Q {f['quality']}%")
        lines.append(f"   1h {_fmt_pct(f['v60'])} | {f['regime']}" + (f" | {', '.join(flags)}" if flags else ""))
    if not candidates:
        lines.append("هنوز برای اسکن حرفه‌ای داده تاریخی کافی جمع نشده است.")
    return "\n".join(lines)


def _historical_validation(asset):
    data=_series(asset, 720)
    vals=[v for _,v in data]
    if len(vals)<80:
        return {"samples":0, "message":f"برای آزمایش تاریخی حداقل ۸۰ نمونه لازم است؛ فعلاً {len(vals)} نمونه داریم."}
    horizon=12
    events=[]
    # Evaluate sparse historical setups to reduce autocorrelation between adjacent 5-min samples.
    for i in range(55, len(vals)-horizon, 12):
        window=vals[:i+1]
        e9=_ema(window[-60:],9); e21=_ema(window[-60:],21)
        r=_rsi_close(window[-40:],14)
        if e9 is None or e21 is None or r is None: continue
        score=0
        score += 1 if e9>e21 else -1
        if r>=55: score+=1
        elif r<=45: score-=1
        if abs(score)<2: continue
        direction=1 if score>0 else -1
        future=(vals[i+horizon]-vals[i])/vals[i]*100 if vals[i] else 0
        signed=future*direction
        events.append(signed)
    if not events:
        return {"samples":0,"message":"در آرشیو فعلی setup همگرایی کافی برای اعتبارسنجی پیدا نشد."}
    wins=sum(1 for x in events if x>0)
    avg=sum(events)/len(events)
    worst=min(events)
    return {"samples":len(events),"hit":wins/len(events)*100,"avg":avg,"worst":worst}


def build_backtest_text(asset):
    label=ALERT_ASSETS.get(asset,{}).get("label",asset)
    r=_historical_validation(asset)
    if not r.get("samples"):
        return f"🧪 <b>آزمایش تاریخی — {label}</b>\n\n{r.get('message')}\n\n<i>تا وقتی نمونه کافی نباشد، طلایار نرخ موفقیت ساختگی نمایش نمی‌دهد.</i>"
    return (f"🧪 <b>آزمایش تاریخی — {label}</b>\n\n"
            f"تعداد setup مستقل: <b>{r['samples']}</b>\n"
            f"Follow-through هم‌جهت: <b>{r['hit']:.1f}%</b>\n"
            f"میانگین حرکت هم‌جهت در افق آزمون: <b>{r['avg']:+.3f}%</b>\n"
            f"بدترین حرکت خلاف جهت: <b>{r['worst']:+.3f}%</b>\n\n"
            "<i>این Backtest ساده و walk-forward روی تاریخچه محلی ربات است؛ کارمزد، لغزش و نقدشوندگی را لحاظ نمی‌کند و تضمین آینده نیست.</i>")


def smart_rule_label(rule):
    return {"breakout":"شکست محدوده ۲۴ساعته","abnormal":"حرکت غیرعادی","confluence":"همگرایی قوی","bubble":"حباب/انحراف بالا"}.get(rule,rule)


def _smart_rule_trigger(rule, f):
    if f.get("quality",0)<35:
        return False, ""
    if rule=="breakout" and f.get("breakout") in {"up","down"}:
        return True, "شکست رو به بالا" if f["breakout"]=="up" else "شکست رو به پایین"
    if rule=="abnormal" and f.get("abnormal"):
        return True, f"نوسان اخیر {f.get('vol_ratio',0):.2f} برابر پنجره قبلی"
    if rule=="confluence" and f.get("score") is not None and abs(f["score"]-50)>=30:
        return True, f"قدرت همگرایی {f['score']}/100"
    if rule=="bubble" and f.get("fair"):
        pct=abs(float(f["fair"]["pct"]))
        z=abs(float(f.get("bubble_z") or 0))
        if pct>=5 or z>=2:
            return True, f"انحراف {f['fair']['pct']:+.2f}%" + (f" | Z {f['bubble_z']:+.2f}σ" if f.get("bubble_z") is not None else "")
    return False, ""


def build_smart_alerts_text(user_id):
    items=db.user_smart_alerts(user_id)
    lines=["🚨 <b>هشدارهای هوشمند VIP</b>", ""]
    if not items:
        lines.append("هنوز هشدار هوشمندی فعال نکرده‌ای.")
    else:
        for i,a in enumerate(items,1):
            lines.append(f"{i}. {ALERT_ASSETS.get(a['asset_key'],{}).get('label',a['asset_key'])} — {smart_rule_label(a['rule'])}")
    lines += ["", "هشدارها با cooldown سی‌دقیقه‌ای اجرا می‌شوند تا در حرکت‌های ممتد اسپم ایجاد نشود."]
    return "\n".join(lines)


def navasan_method_text():
    return ("📘 <b>روش‌شناسی Navasan Intelligence</b>\n\n"
            "• Trend: EMA9/21/50 و شکست محدوده آرشیوی\n"
            "• Momentum: RSI14 + سرعت ۱ساعته\n"
            "• Volatility: میانگین قدرمطلق بازده close-to-close و نسبت پنجره‌های اخیر\n"
            "• Deviation: Z-Score قیمت؛ برای طلا/سکه، ارزش نظری با دلار و انس\n"
            "• Confluence: امتیاز شفاف ۰ تا ۱۰۰؛ زیر کیفیت داده ۳۵٪ نمایش داده نمی‌شود\n"
            "• Backtest: آزمون walk-forward روی تاریخچه محلی، بدون ادعای پیش‌بینی قطعی\n\n"
            "⚠️ برای بازار داخلی که OHLC واقعی نداریم، شاخص نوسان «ATR واقعی» نام‌گذاری نشده و از پروکسی close-to-close استفاده می‌شود. "
            "این طراحی عمداً از دقت کاذب جلوگیری می‌کند.\n\n"
            f"<i>{DISCLAIMER}</i>")

# ═══════════════════════════════════════════════════════════════
# WATCHLIST
# ═══════════════════════════════════════════════════════════════
def build_watchlist_text(user_id, market):
    items = db.get_watchlist(user_id)
    if not items:
        return "📌 <b>بازار من</b>\n\nهنوز دارایی اضافه نکرده‌اید."
    lines = ["📌 <b>بازار من</b>\n"]
    for item in items:
        ak = item["asset_key"]
        info = ALERT_ASSETS.get(ak)
        if not info:
            continue
        it = find_alert_item(market, ak)
        if it:
            price = _format_number(it.get("price"))
            change = _format_number(it.get("change_percent", 0))
            unit = it.get("unit") or ""
            lines.append(f"• {info['label']}: <b>{price}</b> {unit} ({change}%)")
        else:
            lines.append(f"• {info['label']}: ناموجود")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# SMART ANALYSIS (BRS + SQLite history, no paid AI dependency)
# ═══════════════════════════════════════════════════════════════
def _hourly_history(points):
    """نمونه‌های ۵ دقیقه‌ای را به آخرین قیمت هر ساعت تبدیل می‌کند تا اندیکاتورها معنی‌دارتر باشند."""
    buckets = {}
    for point in points:
        try:
            ts = int(point["ts"])
            price = float(point["price"])
        except (KeyError, TypeError, ValueError):
            continue
        bucket = ts // 3600
        previous = buckets.get(bucket)
        if previous is None or ts > previous[0]:
            buckets[bucket] = (ts, price)
    return [buckets[key] for key in sorted(buckets)]


def _ema(values, period):
    if len(values) < period:
        return None
    multiplier = 2 / (period + 1)
    value = sum(values[:period]) / period
    for price in values[period:]:
        value = (price * multiplier) + (value * (1 - multiplier))
    return value


def _ema_series(values, period):
    if len(values) < period:
        return []
    multiplier = 2 / (period + 1)
    ema_value = sum(values[:period]) / period
    result = [ema_value]
    for price in values[period:]:
        ema_value = (price * multiplier) + (ema_value * (1 - multiplier))
        result.append(ema_value)
    return result


def _rsi(values, period=14):
    if len(values) <= period:
        return None
    changes = [values[i] - values[i - 1] for i in range(1, len(values))]
    gains = [max(change, 0) for change in changes]
    losses = [max(-change, 0) for change in changes]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = ((avg_gain * (period - 1)) + gains[i]) / period
        avg_loss = ((avg_loss * (period - 1)) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def _macd(values):
    """MACD(12,26,9) روی داده ساعتی؛ خروجی current MACD و signal."""
    if len(values) < 35:
        return None, None
    ema12 = _ema_series(values, 12)
    ema26 = _ema_series(values, 26)
    # EMA26 از نقطه 26 شروع می‌شود؛ EMA12 را با همان محور هم‌تراز می‌کنیم.
    aligned_ema12 = ema12[14:]
    macd_series = [a - b for a, b in zip(aligned_ema12, ema26)]
    if len(macd_series) < 9:
        return None, None
    signal = _ema(macd_series, 9)
    return macd_series[-1], signal


def _safe_change_percent(item):
    try:
        return float(item.get("change_percent") or 0)
    except (AttributeError, TypeError, ValueError):
        return 0.0


def build_ai_summary(market):
    now_text = datetime.now(TEHRAN_TZ).strftime("%Y/%m/%d - %H:%M")
    sections = [
        "🤖 <b>تحلیل هوشمند الگوریتمی طلایار (VIP)</b>",
        f"🕒 {now_text}",
        "<i>منبع: قیمت لحظه‌ای BRS + آرشیو واقعی SQLite</i>",
    ]

    for key in ("usd", "gold18", "ounce", "btc"):
        item = find_alert_item(market, key)
        if not item:
            continue

        current = _item_price(item)
        if current is None:
            continue
        unit = item.get("unit") or ""
        market_change = _safe_change_percent(item)
        points = db.get_price_history(key, 24 * 14)
        hourly = _hourly_history(points)
        values = [price for _, price in hourly]

        # تا زمانی که آرشیو کافی نشده، فقط داده واقعی موجود را گزارش می‌کنیم.
        if len(values) < 15:
            direction = "صعودی" if market_change > 0 else "نزولی" if market_change < 0 else "خنثی"
            sections.append(
                f"\n<b>{ALERT_ASSETS[key]['label']}</b> — {_format_number(current)} {unit}\n"
                f"• تغییر فعلی: {market_change:+.2f}٪ | وضعیت: {direction}\n"
                "• ⏳ آرشیو ساعتی برای اندیکاتورهای حرفه‌ای در حال تکمیل است."
            )
            continue

        rsi = _rsi(values, 14)
        ema20 = _ema(values, 20)
        macd, signal = _macd(values)

        last_24 = values[-24:] if len(values) >= 24 else values
        change_24h = ((last_24[-1] - last_24[0]) / last_24[0] * 100) if len(last_24) > 1 and last_24[0] else 0
        volatility_24h = ((max(last_24) - min(last_24)) / last_24[-1] * 100) if last_24 and last_24[-1] else 0

        last_7d = values[-168:] if len(values) >= 168 else values
        support = min(last_7d)
        resistance = max(last_7d)

        score = 0
        score += 1 if change_24h > 0 else -1 if change_24h < 0 else 0
        if ema20 is not None:
            score += 1 if current >= ema20 else -1
        if macd is not None and signal is not None:
            score += 1 if macd >= signal else -1

        if score >= 2:
            bias = "🟢 متمایل به صعود"
        elif score <= -2:
            bias = "🔴 متمایل به نزول"
        else:
            bias = "🟡 خنثی / سیگنال‌های مختلط"

        if rsi is None:
            rsi_line = "نامشخص"
        else:
            rsi_state = "اشباع خرید" if rsi >= 70 else "اشباع فروش" if rsi <= 30 else "متعادل"
            rsi_line = f"{rsi:.1f} ({rsi_state})"

        if macd is None or signal is None:
            macd_line = "داده ناکافی"
        else:
            macd_line = "بالای Signal" if macd >= signal else "پایین Signal"

        ema_line = _format_number(ema20) if ema20 is not None else "داده ناکافی"
        sections.append(
            f"\n<b>{ALERT_ASSETS[key]['label']}</b> — {_format_number(current)} {unit}\n"
            f"• جهت ترکیبی: <b>{bias}</b>\n"
            f"• تغییر ۲۴ساعته آرشیو: {change_24h:+.2f}٪ | نوسان: {volatility_24h:.2f}٪\n"
            f"• RSI(14): {rsi_line} | EMA20: {ema_line}\n"
            f"• MACD(12,26,9): {macd_line}\n"
            f"• حمایت/مقاومت آرشیو: {_format_number(support)} / {_format_number(resistance)}"
        )

    if len(sections) == 3:
        sections.append("\n❌ در حال حاضر داده کافی برای تحلیل دریافت نشد.")

    sections.append(
        "\n<i>این خروجی تحلیل الگوریتمی است، نه سیگنال قطعی و نه توصیه خرید یا فروش. "
        "کیفیت اندیکاتورها با کامل‌تر شدن آرشیو قیمت بهتر می‌شود.</i>"
    )
    return "\n".join(sections)


# ═══════════════════════════════════════════════════════════════
# DUAL-MODE VIP PAYMENT (ZarinPal + manual receipt fallback)
# ═══════════════════════════════════════════════════════════════
def zarinpal_enabled():
    return bool(ZARINPAL_MERCHANT_ID and ZARINPAL_CALLBACK_URL)


def vip_plan_amount(plan):
    raw = VIP_PRICE_30 if int(plan) == 30 else VIP_PRICE_90
    amount = _parse_number(raw)
    return int(amount or 0)


def create_zarinpal_payment(user_id, plan):
    if not zarinpal_enabled():
        return None, "درگاه خودکار هنوز تنظیم نشده است"

    amount = vip_plan_amount(plan)
    if amount <= 0:
        return None, "مبلغ بسته VIP معتبر نیست"

    order_id = uuid.uuid4().hex[:10].upper()
    db.create_order(
        order_id, user_id, int(plan), amount, "pending_gateway", _utc_now(),
        payment_method="zarinpal",
    )
    payload = {
        "merchant_id": ZARINPAL_MERCHANT_ID,
        "amount": amount,
        "currency": "IRT",
        "callback_url": ZARINPAL_CALLBACK_URL,
        "description": f"اشتراک {plan} روزه VIP طلایار - سفارش {order_id}",
        "metadata": {"order_id": order_id},
    }
    try:
        response = requests.post(
            ZARINPAL_REQUEST_URL,
            json=payload,
            timeout=API_TIMEOUT,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
        )
        response.raise_for_status()
        result = response.json()
        data = result.get("data") or {}
        if int(data.get("code", 0)) != 100 or not data.get("authority"):
            raise ValueError((result.get("errors") or {}).get("message") or "پاسخ نامعتبر درگاه")
        authority = str(data["authority"])
        db.set_order_authority(order_id, authority)
        return {
            "order_id": order_id,
            "authority": authority,
            "url": (f"{PUBLIC_BASE_URL}/payment/start?authority={quote(authority, safe='')}"
                    if PUBLIC_BASE_URL else f"{ZARINPAL_STARTPAY_URL}{authority}"),
            "amount": amount,
        }, None
    except Exception as exc:
        db.update_order_status(order_id, "gateway_failed", _utc_now())
        logger.warning("ZarinPal payment request failed for order %s: %s", order_id, type(exc).__name__)
        return None, "اتصال به درگاه انجام نشد"


def _notify_gateway_payment(order, ref_id):
    if not BOT_TOKEN:
        return
    text = (
        f"✅ پرداخت شما با موفقیت تأیید شد.\n\n"
        f"⭐ اشتراک VIP برای {order['plan']} روز فعال شد.\n"
        f"🧾 کد پیگیری: {ref_id}"
    )
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": order["user_id"], "text": text},
            timeout=API_TIMEOUT,
        )
        response.raise_for_status()
    except Exception:
        logger.exception("Gateway payment notification failed for order %s", order.get("order_id"))


class PaymentCallbackHandler(BaseHTTPRequestHandler):
    server_version = "Talayar/13.5"

    def _write_page(self, status_code, title, message):
        body = (
            "<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)}</title>"
            "<style>body{font-family:sans-serif;background:#111827;color:#fff;display:grid;"
            "place-items:center;min-height:100vh;margin:0}.box{max-width:520px;background:#1f2937;"
            "padding:28px;border-radius:18px;text-align:center;line-height:2}</style></head>"
            f"<body><div class='box'><h2>{html.escape(title)}</h2><p>{html.escape(message)}</p>"
            "<p>می‌توانید به تلگرام و ربات طلایار برگردید.</p></div></body></html>"
        ).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"

        if route == "/health":
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if route == "/app":
            body = MINIAPP_HTML.encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Cache-Control", "no-store"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return

        query = parse_qs(parsed.query)
        if route == "/payment/start":
            authority = (query.get("authority") or [""])[0].strip()
            order = db.get_order_by_authority(authority) if authority else None
            if not authority or not order:
                self._write_page(404, "پرداخت پیدا نشد", "شناسه پرداخت معتبر نیست.")
                return
            target = f"{ZARINPAL_STARTPAY_URL}{quote(authority, safe='')}"
            safe_target = html.escape(target, quote=True)
            body = (
                "<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>"
                "<meta name='viewport' content='width=device-width,initial-scale=1'>"
                "<title>پرداخت طلایار</title>"
                "<style>body{font-family:sans-serif;background:#0f172a;color:#fff;display:grid;place-items:center;"
                "min-height:100vh;margin:0}.box{max-width:520px;background:#1e293b;padding:30px;border-radius:20px;"
                "text-align:center;line-height:2}.btn{display:inline-block;background:#d4af37;color:#111827;padding:10px 22px;"
                "border-radius:12px;text-decoration:none;font-weight:700}</style></head>"
                "<body><div class='box'><h2>🟡 پرداخت امن طلایار</h2>"
                "<p>برای ادامه و ورود به درگاه زرین‌پال روی دکمه زیر بزنید.</p>"
                f"<a class='btn' href='{safe_target}'>ادامه پرداخت</a>"
                "</div></body></html>"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if route != "/payment/callback":
            self._write_page(404, "صفحه پیدا نشد", "آدرس درخواست‌شده معتبر نیست.")
            return

        authority = (query.get("Authority") or query.get("authority") or [""])[0].strip()
        status = (query.get("Status") or query.get("status") or [""])[0].strip().upper()
        if not authority:
            self._write_page(400, "پرداخت نامعتبر", "شناسه پرداخت دریافت نشد.")
            return

        order = db.get_order_by_authority(authority)
        if not order:
            self._write_page(404, "سفارش پیدا نشد", "این پرداخت با هیچ سفارش طلایار مطابقت ندارد.")
            return
        if order.get("status") == "approved":
            self._write_page(200, "پرداخت قبلاً تأیید شده", "اشتراک VIP شما فعال است.")
            return
        if status != "OK":
            db.update_order_status(order["order_id"], "cancelled_gateway", _utc_now())
            self._write_page(200, "پرداخت لغو شد", "مبلغی تأیید نشد؛ می‌توانید دوباره تلاش کنید.")
            return

        amount = int(_parse_number(order.get("amount")) or 0)
        try:
            response = requests.post(
                ZARINPAL_VERIFY_URL,
                json={
                    "merchant_id": ZARINPAL_MERCHANT_ID,
                    "amount": amount,
                    "authority": authority,
                },
                timeout=API_TIMEOUT,
                headers={"Accept": "application/json", "Content-Type": "application/json"},
            )
            response.raise_for_status()
            result = response.json()
            data = result.get("data") or {}
            code = int(data.get("code", 0))
            if code not in {100, 101}:
                raise ValueError("verification failed")
            ref_id = str(data.get("ref_id") or order.get("ref_id") or authority[-8:])
            paid_order, activated = db.approve_gateway_order(authority, ref_id)
            if not paid_order:
                raise ValueError("order missing during activation")
            if activated:
                _notify_gateway_payment(paid_order, ref_id)
            self._write_page(200, "پرداخت موفق", f"اشتراک VIP فعال شد. کد پیگیری: {ref_id}")
        except Exception as exc:
            logger.warning("ZarinPal verification failed for order %s: %s", order["order_id"], type(exc).__name__)
            self._write_page(502, "تأیید پرداخت ناموفق", "پرداخت فعلاً تأیید نشد؛ با پشتیبانی تماس بگیرید.")

    def do_POST(self):
        parsed=urlparse(self.path); route=parsed.path.rstrip("/") or "/"
        mini_routes={"/api/dashboard","/api/overview","/api/asset","/api/scanner","/api/fair-value","/api/candles"}
        if route not in mini_routes:
            self._write_page(404,"صفحه پیدا نشد","آدرس درخواست‌شده معتبر نیست."); return
        try:
            length=min(int(self.headers.get("Content-Length","0") or 0),65536)
            payload=json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            uid=_verify_telegram_init_data(str(payload.get("initData") or ""))
            if uid is None:
                code=401; data={"error":"unauthorized"}
            else:
                market,error=get_market_data()
                if not market:
                    code=503; data={"error":error or "market unavailable"}
                elif route in {"/api/dashboard","/api/overview"}:
                    code=200; data=_mini_overview_payload(market,uid)
                elif route=="/api/asset":
                    data,code=_mini_asset_payload(market,uid,str(payload.get("asset") or ""))
                elif route=="/api/scanner":
                    data,code=_mini_scanner_payload(market,uid)
                elif route=="/api/fair-value":
                    data,code=_mini_fair_value_payload(market,uid)
                else:
                    data,code=_mini_chart_payload(uid,str(payload.get("asset") or ""),str(payload.get("timeframe") or "24H"))
            body=json.dumps(data,ensure_ascii=False,separators=(",",":")).encode("utf-8")
            self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Cache-Control","no-store"); self.send_header("Content-Length",str(len(body)))
            self.end_headers(); self.wfile.write(body)
        except Exception:
            logger.exception("Mini App API error on %s", route)
            body=b'{"error":"bad request"}'; self.send_response(400)
            self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(body)))
            self.end_headers(); self.wfile.write(body)

    def log_message(self, fmt, *args):
        logger.info("Payment callback: " + fmt, *args)


def start_payment_callback_server():
    if not zarinpal_enabled():
        logger.info("ZarinPal is not configured yet; health endpoint is active and manual receipt fallback remains available")
    try:
        server = ThreadingHTTPServer(("0.0.0.0", PAYMENT_HTTP_PORT), PaymentCallbackHandler)
        thread = threading.Thread(target=server.serve_forever, name="payment-callback", daemon=True)
        thread.start()
        logger.info("Payment callback server started on port %s", PAYMENT_HTTP_PORT)
        return server
    except OSError:
        logger.exception("Payment callback server could not start")
        return None


# ═══════════════════════════════════════════════════════════════
# VIRAL GROWTH / REFERRAL ENGINE
# ═══════════════════════════════════════════════════════════════
REFERRAL_SOURCE_LABELS = {
    "direct": "دعوت مستقیم",
    "report": "گزارش روزانه",
    "analysis": "تحلیل هوشمند",
}


async def get_bot_username(context):
    username = getattr(context.bot, "username", None)
    if username:
        return username
    bot_info = await context.bot.get_me()
    return bot_info.username


def referral_link(user_id, bot_username, source="direct"):
    code = {"direct": "d", "report": "r", "analysis": "a"}.get(source, "d")
    return f"https://t.me/{bot_username}?start=r{int(user_id)}_{code}"


def _parse_referral_payload(payload):
    payload = str(payload or "").strip()
    old = re.fullmatch(r"ref_(\d+)", payload)
    if old:
        return int(old.group(1)), "direct"
    new = re.fullmatch(r"r(\d+)_([dra])", payload)
    if not new:
        return None, None
    source = {"d": "direct", "r": "report", "a": "analysis"}.get(new.group(2), "direct")
    return int(new.group(1)), source


def _progress_bar(current, target, width=10):
    if target <= 0:
        return "█" * width
    ratio = min(1.0, max(0.0, current / target))
    filled = int(round(ratio * width))
    return "█" * filled + "░" * (width - filled)


def referral_progress_text(user_id, bot_username):
    counts = db.referral_counts(user_id)
    count = counts["qualified"]
    tiers = ((3, 7), (10, 30), (25, 90))
    next_tier = next(((needed, days) for needed, days in tiers if count < needed), None)
    link = referral_link(user_id, bot_username, "direct")
    if next_tier:
        needed, days = next_tier
        bar = _progress_bar(count, needed)
        progress = (
            f"🎯 تا جایزه بعدی: <b>{needed - count}</b> دعوت معتبر دیگر\n"
            f"<code>{bar}</code>  {count}/{needed}\n"
            f"جایزه بعدی: <b>{days} روز VIP رایگان</b>"
        )
    else:
        progress = "🏆 همه جایزه‌های دعوت را دریافت کرده‌ای."
    pending_line = f"\n⏳ دعوت‌های در حال اعتبارسنجی: <b>{counts['pending']}</b>" if counts["pending"] else ""
    return (
        "🎁 <b>دعوت دوستان و دریافت VIP رایگان</b>\n\n"
        f"✅ دعوت‌های معتبر: <b>{count}</b>{pending_line}\n\n"
        f"{progress}\n\n"
        "🎁 <b>جوایز:</b>\n"
        "• ۳ دعوت معتبر → ۷ روز VIP\n"
        "• ۱۰ دعوت معتبر → ۳۰ روز VIP\n"
        "• ۲۵ دعوت معتبر → ۹۰ روز VIP\n\n"
        "🛡 برای جلوگیری از تقلب، فقط Start کافی نیست؛ کاربر جدید باید چند تعامل واقعی و متفاوت داخل طلایار انجام دهد.\n\n"
        f"🔗 لینک اختصاصی شما:\n<code>{link}</code>"
    )


def referral_menu(user_id, bot_username):
    link = referral_link(user_id, bot_username, "direct")
    share_text = "طلایار؛ قیمت لحظه‌ای طلا، دلار، سکه و کریپتو + نمودار و هشدار قیمت 👇"
    share_url = f"https://t.me/share/url?url={quote(link, safe='')}&text={quote(share_text, safe='')}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 ارسال لینک دعوت", url=share_url)],
        [InlineKeyboardButton("🏆 مشاهده جوایز من", callback_data="referrals_rewards")],
        [InlineKeyboardButton("🔄 به‌روزرسانی آمار", callback_data="referrals")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ])


def referral_rewards_text(user_id):
    rewards = db.get_referral_rewards(user_id)
    if not rewards:
        return "🏆 <b>جوایز دعوت من</b>\n\nهنوز جایزه‌ای دریافت نکرده‌ای."
    lines = ["🏆 <b>جوایز دعوت من</b>", ""]
    for reward in rewards[-10:]:
        lines.append(f"• {int(reward.get('days') or 0)} روز VIP — {str(reward.get('created_at') or '')[:10]}")
    return "\n".join(lines)


def _referral_distinct_actions(mask):
    return bin(int(mask or 0)).count("1")


async def record_referral_interaction(user_id, action_bit, context):
    """اعتبارسنجی Referral فقط بر اساس تعامل واقعی؛ بدون سرویس خارجی یا پردازش سنگین."""
    state = db.record_referral_activity(user_id, action_bit)
    if not state:
        return False
    started = _parse_iso(state.get("started_at"))
    age_seconds = (datetime.now(timezone.utc) - started).total_seconds() if started else 0
    ready = (
        int(state.get("activity_count") or 0) >= REFERRAL_MIN_ACTIONS
        and _referral_distinct_actions(state.get("activity_mask")) >= REFERRAL_MIN_DISTINCT_ACTIONS
        and age_seconds >= REFERRAL_MIN_AGE_SECONDS
    )
    if not ready or int(state.get("flagged") or 0):
        return False
    return await qualify_referral(user_id, context)


async def qualify_referral(user_id, context, allow_flagged=False):
    ref = db.qualify_referral(user_id, allow_flagged=allow_flagged)
    if not ref:
        return False
    referrer_id = int(ref["referrer_id"])
    count = db.qualified_count(referrer_id)
    rewards = db.get_referral_rewards(referrer_id)
    claimed = {int(r.get("days") or 0) for r in rewards}
    new_rewards = []
    for needed, days in ((3, 7), (10, 30), (25, 90)):
        if count >= needed and days not in claimed:
            if db.add_referral_reward(referrer_id, "vip_days", 0, days):
                db.add_vip(referrer_id, days, source=f"referral:{needed}")
                new_rewards.append((needed, days))
    try:
        next_tier = next(((n, d) for n, d in ((3, 7), (10, 30), (25, 90)) if count < n), None)
        message = f"✅ یک دعوت شما معتبر شد.\nتعداد دعوت‌های معتبر: <b>{count}</b> نفر"
        if new_rewards:
            message += "\n\n" + "\n".join(f"🎉 جایزه {needed} دعوت: <b>{days} روز VIP</b> فعال شد." for needed, days in new_rewards)
        elif next_tier:
            message += f"\n\n🎯 فقط {next_tier[0] - count} دعوت دیگر تا {next_tier[1]} روز VIP رایگان."
        await context.bot.send_message(referrer_id, message, parse_mode="HTML", reply_markup=main_menu())
    except Exception:
        logger.exception("Referral notification failed")
    return True


def _market_share_lines(market):
    rows = []
    for key in ("usd", "gold18", "emami", "ounce", "btc"):
        item = find_alert_item(market, key)
        if not item:
            continue
        change = _safe_change_percent(item)
        arrow = "🟢" if change > 0 else "🔴" if change < 0 else "🟡"
        unit = item.get("unit") or ""
        rows.append(f"{arrow} {ALERT_ASSETS[key]['label']}: {_format_number(item.get('price'))} {unit} ({change:+.2f}٪)")
    return rows


def build_share_report_text(market, user_id, bot_username):
    link = referral_link(user_id, bot_username, "report")
    lines = ["🟡 گزارش بازار | طلایار", *(_market_share_lines(market)[:5]), "", "قیمت لحظه‌ای، نمودار و هشدار بازار:", link]
    return "\n".join(lines)


def build_share_analysis_text(market, user_id, bot_username):
    link = referral_link(user_id, bot_username, "analysis")
    lines = ["🤖 تحلیل کوتاه بازار | طلایار"]
    for key in ("usd", "gold18", "ounce", "btc"):
        item = find_alert_item(market, key)
        if not item:
            continue
        change = _safe_change_percent(item)
        bias = "🟢 صعودی" if change > 0.35 else "🔴 نزولی" if change < -0.35 else "🟡 خنثی"
        lines.append(f"{ALERT_ASSETS[key]['label']}: {bias} | {change:+.2f}٪")
    lines.extend(["", "تحلیل کامل، نمودار تکنیکال و قیمت لحظه‌ای:", link, "⚠️ تحلیل الگوریتمی است و توصیه قطعی خرید یا فروش نیست."])
    return "\n".join(lines)


def share_report_menu(user_id, bot_username, market):
    share_text = build_share_report_text(market, user_id, bot_username)
    share_url = f"https://t.me/share/url?url=&text={quote(share_text, safe='')}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 اشتراک گزارش", url=share_url)],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="home")],
    ])


def share_analysis_menu(user_id, bot_username, market):
    share_text = build_share_analysis_text(market, user_id, bot_username)
    share_url = f"https://t.me/share/url?url=&text={quote(share_text, safe='')}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 اشتراک تحلیل", url=share_url)],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="home")],
    ])

# ═══════════════════════════════════════════════════════════════
# TECHNICAL CANDLE CHARTS (ALL MAIN ASSETS)
# ═══════════════════════════════════════════════════════════════
_CHART_SYMBOLS = {
    "usd": "USD/IRT", "gold18": "GOLD 18K", "melted": "MELTED GOLD", "melted_future": "MELTED FUTURE", "herat_usd": "HERAT USD", "aed": "AED/IRT", "emami": "EMAMI COIN",
    "half": "HALF COIN", "quarter": "QUARTER COIN", "ounce": "GOLD",
    "btc": "BTC/USD", "eth": "ETH/USD", "usdt": "USDT/IRT",
}

_YF_CHART_ASSETS = {
    "ounce": ("GC=F", "USD", "بازار جهانی طلا (GC=F)"),
    "btc": ("BTC-USD", "USD", "بازار جهانی بیت‌کوین"),
    "eth": ("ETH-USD", "USD", "بازار جهانی اتریوم"),
}

_TIMEFRAME_RULES = [
    (5, "5min", "۵ دقیقه"),
    (15, "15min", "۱۵ دقیقه"),
    (30, "30min", "۳۰ دقیقه"),
    (60, "1h", "۱ ساعت"),
    (120, "2h", "۲ ساعت"),
    (240, "4h", "۴ ساعت"),
    (720, "12h", "۱۲ ساعت"),
    (1440, "1D", "۱ روز"),
]


def _period_label(hours):
    return {24: "۲۴ ساعت", 168: "۷ روز", 720: "۳۰ روز"}.get(hours, f"{hours} ساعت")


def _period_short(hours):
    return {24: "24H", 168: "7D", 720: "30D"}.get(hours, f"{hours}H")


def _coverage_label(hours):
    if hours < 1:
        return f"{max(1, round(hours * 60))} دقیقه"
    if hours < 48:
        return f"{hours:.1f} ساعت" if abs(hours - round(hours)) > 0.05 else f"{int(round(hours))} ساعت"
    days = hours / 24
    return f"{days:.1f} روز" if abs(days - round(days)) > 0.05 else f"{int(round(days))} روز"


def _dynamic_rule(coverage_minutes, minimum_minutes=5):
    """حدود 35 تا 80 کندل روی تصویر نگه می‌دارد و از رزولوشن منبع ریزتر نمی‌شود."""
    valid = [item for item in _TIMEFRAME_RULES if item[0] >= minimum_minutes]
    for minutes, rule, label in valid:
        if coverage_minutes / minutes <= 100:
            return rule, label, minutes
    return valid[-1][1], valid[-1][2], valid[-1][0]


def _chart_cache_get(key):
    now = time.monotonic()
    with _chart_cache_lock:
        entry = _chart_cache.get(key)
        if not entry:
            return None
        if now - entry[0] > CHART_CACHE_TTL_SECONDS:
            _chart_cache.pop(key, None)
            return None
        return entry[1], entry[2]


def _chart_cache_put(key, image_bytes, caption):
    with _chart_cache_lock:
        if len(_chart_cache) >= CHART_CACHE_MAX_ITEMS:
            oldest = min(_chart_cache, key=lambda k: _chart_cache[k][0])
            _chart_cache.pop(oldest, None)
        _chart_cache[key] = (time.monotonic(), image_bytes, caption)


def _resample_ohlc(frame, rule, has_volume=False):
    agg = {
        "open": "first", "high": "max", "low": "min", "close": "last"
    }
    if has_volume and "volume" in frame.columns:
        agg["volume"] = "sum"
    return frame.resample(rule).agg(agg).dropna(subset=["open", "high", "low", "close"])


def _build_local_ohlc(asset, period_hours):
    points = db.get_price_history(asset, period_hours)
    if len(points) < 6:
        return None
    frame = pd.DataFrame(points)
    if frame.empty:
        return None
    frame["dt"] = pd.to_datetime(frame["ts"], unit="s")
    frame["price"] = pd.to_numeric(frame["price"], errors="coerce")
    frame = frame.dropna(subset=["price"]).sort_values("dt")
    if len(frame) < 6:
        return None

    first_ts = int(frame["ts"].iloc[0])
    last_ts = int(frame["ts"].iloc[-1])
    coverage_hours = max(0.0, (last_ts - first_ts) / 3600)
    coverage_minutes = max(5.0, coverage_hours * 60)
    rule, timeframe_label, _ = _dynamic_rule(coverage_minutes, minimum_minutes=5)

    # از نمونه‌های واقعی پنج‌دقیقه‌ای OHLC می‌سازیم؛ هیچ حجم ساختگی تولید نمی‌شود.
    price = frame.set_index("dt")["price"]
    ohlc = price.resample(rule).ohlc().dropna()
    if len(ohlc) < 3:
        # در آرشیو خیلی کوتاه، ریزترین تایم‌فریم ممکن را نگه می‌داریم.
        ohlc = price.resample("5min").ohlc().dropna()
        timeframe_label = "۵ دقیقه"
    if len(ohlc) < 3:
        return None

    complete = coverage_hours >= period_hours * 0.8
    return {
        "df": ohlc,
        "unit": str(frame["unit"].iloc[-1] or "").strip(),
        "timeframe": timeframe_label,
        "coverage_hours": coverage_hours,
        "requested_hours": period_hours,
        "complete": complete,
        "started_ts": first_ts,
        "source": "آرشیو واقعی طلایار (نمونه‌برداری ۵ دقیقه‌ای)",
        "external": False,
    }


def _build_external_ohlc(asset, period_hours):
    config = _YF_CHART_ASSETS.get(asset)
    if not config:
        return None
    ticker_symbol, unit, source = config
    try:
        ticker = yf.Ticker(ticker_symbol)
        if period_hours <= 24:
            period, interval, min_minutes = "5d", "15m", 15
        elif period_hours <= 168:
            period, interval, min_minutes = "1mo", "1h", 60
        else:
            period, interval, min_minutes = "3mo", "1h", 60
        raw = ticker.history(period=period, interval=interval)
        if raw.empty:
            return None
        cutoff = raw.index.max() - timedelta(hours=period_hours)
        raw = raw[raw.index >= cutoff]
        if raw.empty:
            return None
        raw = raw.rename(columns={
            "Open": "open", "High": "high", "Low": "low",
            "Close": "close", "Volume": "volume",
        })
        raw = raw.dropna(subset=["open", "high", "low", "close"])
        if len(raw) < 3:
            return None
        coverage_hours = max(0.0, (raw.index.max() - raw.index.min()).total_seconds() / 3600)
        coverage_minutes = max(float(min_minutes), coverage_hours * 60)
        rule, timeframe_label, _ = _dynamic_rule(coverage_minutes, minimum_minutes=min_minutes)
        frame = _resample_ohlc(raw, rule, has_volume="volume" in raw.columns)
        if len(frame) < 3:
            frame = raw[[c for c in ("open", "high", "low", "close", "volume") if c in raw.columns]].copy()
            timeframe_label = {15: "۱۵ دقیقه", 60: "۱ ساعت"}.get(min_minutes, f"{min_minutes} دقیقه")
        return {
            "df": frame,
            "unit": unit,
            "timeframe": timeframe_label,
            "coverage_hours": coverage_hours,
            "requested_hours": period_hours,
            "complete": coverage_hours >= period_hours * 0.8,
            "started_ts": None,
            "source": source,
            "external": True,
        }
    except Exception:
        logger.exception("External chart data failed for %s", asset)
        return None


def _rsi_series(close, period=14):
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    avg_loss = loss.ewm(alpha=1 / period, adjust=False, min_periods=period).mean()
    rs = avg_gain / avg_loss.replace(0, float("nan"))
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def _fmt_chart_value(value, asset, unit):
    if asset in {"ounce", "btc", "eth"} and unit.upper() == "USD":
        return f"${value:,.2f}"
    return f"{_format_number(value)} {unit}".strip()


def _render_candle_chart(asset, period_hours):
    # برای طلا جهانی و BTC/ETH تاریخچه جهانی؛ در صورت خطا آرشیو خود طلایار fallback است.
    info = _build_external_ohlc(asset, period_hours) if asset in _YF_CHART_ASSETS else None
    if not info:
        info = _build_local_ohlc(asset, period_hours)
    if not info:
        return None

    frame = info["df"].copy()
    frame.columns = [str(c).lower() for c in frame.columns]
    frame = frame.dropna(subset=["open", "high", "low", "close"])
    if len(frame) < 3:
        return None

    close = frame["close"].astype(float)
    first = float(close.iloc[0])
    last = float(close.iloc[-1])
    change = ((last - first) / first) * 100 if first else 0.0

    # Guard: برای بازارهای داخلی تا حداقل ۲۴ ساعت آرشیو و تعداد کافی کندل،
    # اندیکاتورهای تکنیکال نمایش داده نمی‌شوند تا خروجی گمراه‌کننده نباشد.
    indicator_ready = bool(info["external"] or (info["coverage_hours"] >= 24 and len(frame) >= 50))

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    rsi = _rsi_series(close, 14)
    recent = frame.tail(min(30, len(frame)))
    support = float(recent["low"].min()) if indicator_ready else None
    resistance = float(recent["high"].max()) if indicator_ready else None
    rsi_last = float(rsi.iloc[-1]) if len(rsi) else 50.0

    addplots = []
    if indicator_ready:
        addplots.append(mpf.make_addplot(ema20, color="#f5c542", width=1.15))
        addplots.append(mpf.make_addplot(ema50, color="#38bdf8", width=1.0))
    has_rsi = bool(indicator_ready and len(frame) >= 15)
    if has_rsi:
        addplots.extend([
            mpf.make_addplot(rsi, panel=1, color="#a78bfa", width=1.05, ylabel="RSI 14", ylim=(0, 100)),
            mpf.make_addplot(pd.Series(70.0, index=frame.index), panel=1, color="#6b7280", width=0.65, linestyle="--", ylim=(0, 100)),
            mpf.make_addplot(pd.Series(30.0, index=frame.index), panel=1, color="#6b7280", width=0.65, linestyle="--", ylim=(0, 100)),
        ])

    mc = mpf.make_marketcolors(
        up="#16c784", down="#ea3943", edge="inherit", wick="inherit", volume="inherit"
    )
    style = mpf.make_mpf_style(
        marketcolors=mc,
        figcolor="#0b1220",
        facecolor="#0b1220",
        edgecolor="#334155",
        gridcolor="#223047",
        gridstyle="--",
        rc={
            "axes.labelcolor": "#d1d5db", "xtick.color": "#94a3b8", "ytick.color": "#94a3b8",
            "axes.titlecolor": "#f8fafc", "font.size": 9,
        },
    )

    hlines = [last]
    hcolors = ["#94a3b8"]
    if indicator_ready and support is not None and resistance is not None:
        if abs(support - last) > max(abs(last), 1) * 1e-8:
            hlines.append(support); hcolors.append("#22c55e")
        if abs(resistance - last) > max(abs(last), 1) * 1e-8 and abs(resistance - support) > max(abs(last), 1) * 1e-8:
            hlines.append(resistance); hcolors.append("#ef4444")

    buf = BytesIO()
    symbol = _CHART_SYMBOLS.get(asset, asset.upper())
    kwargs = dict(
        type="candle",
        style=style,
        figsize=(12, 8 if has_rsi else 6.75),
        title=f"\nTALAYAR  •  {symbol}  •  {_period_short(period_hours)}  •  {info['timeframe']}",
        ylabel=("USD" if info["unit"].upper() == "USD" else (info["unit"] or "PRICE")),
        hlines=dict(hlines=hlines, colors=hcolors, linestyle="--", linewidths=0.8),
        tight_layout=True,
        savefig=dict(fname=buf, dpi=150, bbox_inches="tight", facecolor="#0b1220"),
    )
    if addplots:
        kwargs["addplot"] = addplots
    if has_rsi:
        kwargs["panel_ratios"] = (3, 1)
    mpf.plot(frame, **kwargs)

    image_bytes = buf.getvalue()
    buf.close()
    emoji = "🟢" if change >= 0 else "🔴"
    price_text = _fmt_chart_value(last, asset, info["unit"])
    coverage_note = ""
    if not info["complete"]:
        coverage_note = (
            f"\n⚠️ تاریخچه کامل {_period_label(period_hours)} هنوز جمع نشده؛ "
            f"این نمودار فقط <b>{_coverage_label(info['coverage_hours'])}</b> داده واقعی موجود را نشان می‌دهد."
        )

    if indicator_ready:
        support_text = _fmt_chart_value(support, asset, info["unit"])
        resistance_text = _fmt_chart_value(resistance, asset, info["unit"])
        ema20_text = _fmt_chart_value(float(ema20.iloc[-1]), asset, info["unit"])
        ema50_text = _fmt_chart_value(float(ema50.iloc[-1]), asset, info["unit"])
        indicator_block = (
            f"📐 EMA20: <code>{ema20_text}</code> | EMA50: <code>{ema50_text}</code>\n"
            f"📊 RSI14: <code>{rsi_last:.1f}</code>\n"
            f"🛡 حمایت: <code>{support_text}</code> | 🎯 مقاومت: <code>{resistance_text}</code>\n"
            f"🟨 EMA20  🟦 EMA50  🟪 RSI14\n"
        )
    else:
        remaining = max(0.0, 24 - float(info["coverage_hours"]))
        remaining_text = _coverage_label(remaining) if remaining > 0.05 else "چند نمونه بیشتر"
        indicator_block = (
            "🧪 <b>اندیکاتورهای تکنیکال هنوز فعال نشده‌اند.</b>\n"
            "برای جلوگیری از تحلیل گمراه‌کننده، EMA20/EMA50، RSI14 و حمایت/مقاومت "
            "پس از جمع‌شدن حداقل ۲۴ ساعت آرشیو واقعی و تعداد کافی کندل نمایش داده می‌شوند.\n"
            f"⏳ حدود <b>{remaining_text}</b> دیگر تا حداقل آرشیو زمانی موردنیاز.\n"
        )

    caption = (
        f"{emoji} <b>نمودار تکنیکال {ALERT_ASSETS[asset]['label']}</b>\n"
        f"⏳ بازه درخواستی: {_period_label(period_hours)} | 🕯 کندل: {info['timeframe']}\n"
        f"💰 قیمت فعلی: <code>{price_text}</code> | تغییر: <code>{change:+.2f}%</code>\n"
        f"{indicator_block}"
        f"🗂 منبع: {info['source']}{coverage_note}"
    )
    return image_bytes, caption


async def _show_callback_text(q, text, reply_markup=None, parse_mode=None):
    """روی پیام متنی edit می‌کند؛ اگر Callback از عکس باشد، عکس را حذف و یک پیام متنی جدید می‌فرستد."""
    try:
        if getattr(q.message, "photo", None) or getattr(q.message, "video", None) or getattr(q.message, "document", None):
            chat_id = q.message.chat.id
            try:
                await q.message.delete()
            except Exception:
                logger.debug("Could not delete media message during navigation", exc_info=True)
            await q.get_bot().send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode=parse_mode)
        else:
            await q.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
        return True
    except Exception:
        logger.exception("Safe callback navigation failed")
        try:
            await q.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return True
        except Exception:
            logger.exception("Fallback callback navigation failed")
            return False


async def send_candle_chart(update_or_query, context, asset, period_hours):
    period_hours = int(period_hours)
    request_token = uuid.uuid4().hex
    context.user_data["chart_request_token"] = request_token
    key = (asset, period_hours)
    cached = _chart_cache_get(key)
    try:
        if cached:
            image_bytes, caption = cached
        else:
            async with _chart_render_semaphore:
                cached = _chart_cache_get(key)
                if cached:
                    image_bytes, caption = cached
                else:
                    rendered = await asyncio.to_thread(_render_candle_chart, asset, period_hours)
                    if not rendered:
                        return False
                    image_bytes, caption = rendered
                    _chart_cache_put(key, image_bytes, caption)

        # اگر کاربر در زمان رندر /start یا مسیر دیگری را زده، نتیجه قدیمی دیگر ارسال نشود.
        if context.user_data.get("chart_request_token") != request_token:
            return None

        photo = BytesIO(image_bytes)
        photo.name = f"talayar_{asset}_{period_hours}.png"
        markup = chart_period_menu(asset, candle=True)

        if isinstance(update_or_query, Update):
            await update_or_query.message.reply_photo(
                photo=photo, caption=caption, parse_mode="HTML", reply_markup=markup
            )
        else:
            q = update_or_query
            if getattr(q.message, "photo", None):
                # تعویض بازه روی همان عکس؛ دیگر edit_message_text روی Photo Message اجرا نمی‌شود.
                media = InputMediaPhoto(media=photo, caption=caption, parse_mode="HTML")
                await q.edit_message_media(media=media, reply_markup=markup)
            else:
                # از منوی متنی وارد نمودار شده‌ایم؛ عکس جدید را بفرست و منوی متنی قبلی را پاک کن.
                chat_id = q.message.chat.id
                await context.bot.send_photo(
                    chat_id=chat_id, photo=photo, caption=caption,
                    parse_mode="HTML", reply_markup=markup,
                )
                try:
                    await q.message.delete()
                except Exception:
                    logger.debug("Could not delete chart selection message", exc_info=True)
        return True
    except Exception:
        logger.exception("Technical chart error for %s/%s", asset, period_hours)
        return False
    finally:
        if context.user_data.get("chart_request_token") == request_token:
            context.user_data.pop("chart_request_token", None)

# ═══════════════════════════════════════════════════════════════
# GOLD CALCULATOR (ConversationHandler)
# ═══════════════════════════════════════════════════════════════
(WEIGHT, LIVE_PRICE, WAGE, PROFIT, TAX) = range(5)


async def gold_calc_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_flow(context)
    prompt = (
        "🧮 <b>ماشین حساب طلا</b>\n\n"
        "لطفاً <b>وزن</b> را به گرم وارد کنید:\n"
        "مثال: <code>2.5</code>\nبرای لغو /cancel"
    )
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(prompt, parse_mode="HTML")
    else:
        await update.message.reply_text(prompt, parse_mode="HTML")
    return WEIGHT


async def gc_weight(update: Update, context: ContextTypes.DEFAULT_TYPE):
    w = _parse_number(update.message.text)
    if w is None or w <= 0:
        await update.message.reply_text("❌ لطفاً یک عدد معتبر (گرم) وارد کنید.")
        return WEIGHT
    context.user_data["calc_weight"] = w
    await update.message.reply_text(
        "💰 <b>قیمت لحظه‌ای طلای ۱۸ عیار</b> (تومان) را وارد کنید:\n"
        "یا بنویسید <code>auto</code> تا از API بگیرم.\nبرای لغو /cancel",
        parse_mode="HTML",
    )
    return LIVE_PRICE


async def gc_live_price(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text.lower() == "auto":
        market, error = get_market_data()
        item = find_alert_item(market, "gold18") if market else None
        price = _item_price(item)
        if price is None:
            await update.message.reply_text(f"❌ خطا در دریافت قیمت: {error or 'ناموجود'}\nلطفاً دستی وارد کنید.")
            return LIVE_PRICE
    else:
        price = _parse_number(text)
        if price is None or price <= 0:
            await update.message.reply_text("❌ عدد نامعتبر. لطفاً دوباره وارد کنید.")
            return LIVE_PRICE

    context.user_data["calc_price"] = price
    await update.message.reply_text(
        "🔧 <b>اجرت ساخت</b> (تومان به ازای هر گرم) را وارد کنید:\nبرای لغو /cancel",
        parse_mode="HTML",
    )
    return WAGE


async def gc_wage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    wage = _parse_number(update.message.text)
    if wage is None:
        await update.message.reply_text("❌ درصد نامعتبر.")
        return WAGE
    context.user_data["calc_wage"] = wage
    await update.message.reply_text(
        "📊 <b>سود فروشنده</b> (درصد) را وارد کنید:\nمثال: <code>7</code>\nبرای لغو /cancel",
        parse_mode="HTML",
    )
    return PROFIT


async def gc_profit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    profit = _parse_number(update.message.text)
    if profit is None:
        await update.message.reply_text("❌ درصد نامعتبر.")
        return PROFIT
    context.user_data["calc_profit"] = profit
    await update.message.reply_text(
        "🏛 <b>مالیات</b> (درصد) را وارد کنید:\nاگر ۹٪ است، بنویسید <code>9</code>\nبرای لغو /cancel",
        parse_mode="HTML",
    )
    return TAX


async def gc_tax(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tax_percent = _parse_number(update.message.text)
    if tax_percent is None:
        await update.message.reply_text("❌ درصد نامعتبر. محاسبه لغو شد.")
        return ConversationHandler.END

    d = context.user_data
    weight = d["calc_weight"]
    unit_price = d["calc_price"]
    wage_per_gram = d["calc_wage"]
    profit_percent = d["calc_profit"]

    base_price = weight * unit_price
    total_wage = weight * wage_per_gram
    subtotal = base_price + total_wage
    profit = subtotal * (profit_percent / 100)
    taxable = subtotal + profit
    tax = taxable * (tax_percent / 100)
    final_price = taxable + tax
    per_gram = final_price / weight

    result = (
        f"🧾 <b>رسید محاسبه طلا</b>\n\n"
        f"⚖️ وزن: <code>{weight:,.2f} گرم</code>\n"
        f"💰 قیمت پایه: <code>{base_price:,.0f} تومان</code>\n"
        f"🔧 اجرت ساخت: <code>{total_wage:,.0f} تومان</code>\n"
        f"📈 سود فروشنده ({profit_percent}%): <code>{profit:,.0f} تومان</code>\n"
        f"🏛 مالیات ({tax_percent}%): <code>{tax:,.0f} تومان</code>\n"
        f"{'─' * 24}\n"
        f"💵 <b>قیمت نهایی:</b> <code>{final_price:,.0f} تومان</code>\n"
        f"📌 <b>هر گرم:</b> <code>{per_gram:,.0f} تومان</code>"
    )
    clear_flow(context)
    await update.message.reply_text(result, parse_mode="HTML", reply_markup=main_menu())
    return ConversationHandler.END


async def gc_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_flow(context)
    await update.message.reply_text("❌ عملیات لغو شد.", reply_markup=main_menu())
    return ConversationHandler.END


async def help_command_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_flow(context)
    await update.message.reply_text(help_text(), parse_mode="HTML", reply_markup=help_menu())


async def gold_command_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    market, error = get_market_data()
    if not market:
        await update.message.reply_text(f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=main_menu()); return
    db.update_last_seen(update.effective_user.id); db.increment_activity(update.effective_user.id)
    capture_history(market); await record_referral_interaction(update.effective_user.id, REF_ACTION_PRICE, context)
    await update.message.reply_text(build_gold_text(market)+f"\n<i>{DISCLAIMER}</i>", parse_mode="HTML", reply_markup=price_menu())


async def price_command_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    market, error = get_market_data()
    if not market:
        await update.message.reply_text(f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=main_menu()); return
    db.update_last_seen(update.effective_user.id); db.increment_activity(update.effective_user.id)
    capture_history(market); await record_referral_interaction(update.effective_user.id, REF_ACTION_PRICE, context)
    await update.message.reply_text(build_crypto_text(market)+f"\n<i>{DISCLAIMER}</i>", parse_mode="HTML", reply_markup=price_menu())


async def version_command_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"✅ <b>Talayar v{APP_VERSION}</b>\nBuild: <code>{BUILD_TAG}</code>", parse_mode="HTML")


# ═══════════════════════════════════════════════════════════════
# HANDLERS
# ═══════════════════════════════════════════════════════════════
def clear_flow(context):
    for key in ("flow", "alert_draft", "alert_edit_id", "purchase_plan", "calc_weight", "calc_price", "calc_wage", "calc_profit", "chart_request_token"):
        context.user_data.pop(key, None)


async def start_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_flow(context)
    user = update.effective_user
    chat_id = update.effective_chat.id
    existing = db.get_user(user.id)
    is_new = existing is None

    referral_registered = False
    referrer_id = None
    referral_source = "direct"
    if is_new and context.args:
        referrer_id, referral_source = _parse_referral_payload(context.args[0])
        if referrer_id:
            referral_registered = db.register_referral(user.id, referrer_id, source=referral_source)
            if not referral_registered:
                referrer_id = None

    db.add_user(user.id, user.username, user.first_name, chat_id, _utc_now(), referrer_id=referrer_id)
    db.update_last_seen(user.id)

    trial_activated = False
    if is_new:
        trial_activated = db.add_trial_vip(user.id)

    name = html.escape(user.first_name or "دوست من")
    greeting = "به طلایار خوش آمدی" if is_new else "خوش برگشتی به طلایار"
    referral_note = ("\n✅ دعوت شما ثبت شد؛ بعد از چند استفاده واقعی و متفاوت از ربات، دعوت معتبر می‌شود." if referral_registered else "")

    if trial_activated:
        account_status = "🎁 <b>VIP آزمایشی ۳ روزه شما همین الان فعال شد.</b>"
    elif is_vip(user.id):
        days = vip_days_left(user.id)
        remaining = "بدون انقضا" if days is None else f"{days} روز باقی‌مانده"
        account_status = f"⭐ <b>وضعیت حساب: VIP فعال — {remaining}</b>"
    else:
        account_status = f"👤 وضعیت حساب: رایگان — {FREE_ALERT_LIMIT} هشدار فعال رایگان"

    welcome = (
        f"🟡 <b>{name}، {greeting}</b>\n\n"
        "طلایار دستیار بازار طلا، ارز و کریپتوست؛ برای اینکه بدون شلوغی، اطلاعات مهم بازار را سریع ببینی.\n\n"
        "⚡ <b>قیمت لحظه‌ای</b> طلا، سکه، دلار، انس و کریپتو\n"
        "🔔 <b>هشدار قیمت</b> عددی؛ برای VIP درصدی و تکرارشونده\n"
        "📈 <b>نمودار واقعی</b> ۲۴ساعته، ۷روزه و ۳۰روزه\n"
        "🧮 <b>ماشین‌حساب طلا</b> برای محاسبه خرید\n"
        "📌 <b>بازار من</b> و 🤖 <b>تحلیل هوشمند</b> برای کاربران VIP\n\n"
        f"{account_status}{referral_note}\n\n"
        "از منوی زیر شروع کن 👇"
    )

    await update.message.reply_text(
        welcome,
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


async def cancel_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_flow(context)
    await update.message.reply_text("عملیات لغو شد.", reply_markup=main_menu())


async def my_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"شناسه کاربری شما: <code>{update.effective_user.id}</code>", parse_mode="HTML")


async def vip_command_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(vip_text(update.effective_user.id), reply_markup=vip_menu(update.effective_user.id), parse_mode="HTML")


async def admin_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        await update.message.reply_text("این بخش فقط برای مدیر ربات است.")
        return
    clear_flow(context)
    await update.message.reply_text("🛠 پنل مدیریت طلایار", reply_markup=admin_menu())


async def add_vip_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("فرمت: /addvip USER_ID DAYS\nمثال: /addvip 123456 30")
        return
    user_id = int(context.args[0])
    days = int(context.args[1]) if len(context.args) > 1 and context.args[1].isdigit() else 30
    db.add_vip(user_id, days)
    await update.message.reply_text(f"✅ کاربر {user_id} برای {days} روز VIP شد.")
    try:
        await context.bot.send_message(user_id, f"⭐ اشتراک VIP شما برای {days} روز فعال شد.", reply_markup=main_menu())
    except Exception:
        logger.exception("VIP notification failed")


async def remove_vip_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("فرمت: /removevip USER_ID")
        return
    await update.message.reply_text("✅ حذف شد." if db.remove_vip(context.args[0]) else "کاربر VIP نبود.")


async def userinfo_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update.effective_user.id):
        return
    if not context.args or not context.args[0].isdigit():
        await update.message.reply_text("فرمت: /userinfo USER_ID")
        return
    user_id = context.args[0]
    user = db.get_user(int(user_id))
    if not user:
        await update.message.reply_text("کاربر یافت نشد.")
        return
    await update.message.reply_text(
        f"👤 نام: {html.escape(user.get('first_name') or 'نامشخص')}\n"
        f"یوزرنیم: @{html.escape(user.get('username') or 'ندارد')}\nشناسه: <code>{user_id}</code>\n"
        f"VIP: {'بله' if is_vip(user_id) else 'خیر'}\nهشدار: {len(db.user_alerts(int(user_id)))}", parse_mode="HTML")


async def receive_text_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    db.update_last_seen(user_id)
    db.increment_activity(user_id)

    flow = context.user_data.get("flow")
    text = update.message.text.strip()
    value = _parse_number(text) if flow in {"alert_value", "alert_edit", "calc_weight", "calc_fee"} else None

    if flow == "alert_value":
        draft = context.user_data.get("alert_draft", {})
        if value is None or value <= 0:
            await update.message.reply_text("عدد معتبر بفرست؛ برای لغو /cancel")
            return
        if not is_vip(user_id) and len(db.user_alerts(user_id)) >= FREE_ALERT_LIMIT:
            clear_flow(context)
            await update.message.reply_text("سقف یک هشدار رایگان پر شده است.", reply_markup=alert_menu())
            return
        alert = {"id": uuid.uuid4().hex[:12], "chat_id": update.effective_chat.id,
                 "user_id": user_id, "type": draft.get("type", "price"),
                 "asset": draft.get("asset"), "condition": draft.get("condition"),
                 "mode": draft.get("mode", "once"), "armed": True, "created_at": _utc_now()}
        if alert["type"] == "percent":
            market, error = get_market_data()
            baseline = _item_price(find_alert_item(market, alert["asset"])) if market else None
            if baseline is None:
                await update.message.reply_text(f"قیمت مبنا دریافت نشد: {error or 'ناموجود'}")
                return
            alert.update({"percent": value, "baseline": baseline})
            detail = f"{_condition_label(alert['condition'])} {value}٪"
        else:
            alert["target"] = value
            detail = f"{_condition_label(alert['condition'])} {_format_number(value)}"
        db.create_alert(alert)
        await record_referral_interaction(user_id, REF_ACTION_ALERT, context)
        clear_flow(context)
        await update.message.reply_text(
            f"✅ هشدار ذخیره شد\n\nدارایی: {ALERT_ASSETS[alert['asset']]['label']}\n"
            f"شرط: {detail}\nاجرا: {'تکرارشونده' if alert['mode'] == 'repeat' else 'یک‌باره'}",
            reply_markup=alert_menu())
        return

    if flow == "alert_edit":
        if value is None or value <= 0:
            await update.message.reply_text("عدد معتبر بفرست؛ برای لغو /cancel")
            return
        alert_id = context.user_data.get("alert_edit_id")
        alert = next((a for a in db.user_alerts(user_id) if str(a.get("id")) == str(alert_id)), None)
        if not alert:
            clear_flow(context)
            await update.message.reply_text("هشدار پیدا نشد.", reply_markup=alert_menu())
            return
        changes = {"armed": 1, "updated_at": _utc_now()}
        if alert.get("type") == "percent":
            changes["percent"] = value
            market, _ = get_market_data()
            baseline = _item_price(find_alert_item(market, alert["asset"])) if market else None
            if baseline is not None:
                changes["baseline"] = baseline
        else:
            changes["target"] = value
        db.update_alert(alert_id, user_id, changes)
        clear_flow(context)
        await update.message.reply_text("✅ هشدار ویرایش شد.", reply_markup=alert_menu())
        return

    if flow == "daily_time":
        normalized = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
        if not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", normalized):
            await update.message.reply_text("ساعت را مثل 09:30 بفرست؛ برای لغو /cancel")
            return
        db.set_daily_sub(user_id, update.effective_chat.id, normalized)
        await record_referral_interaction(user_id, REF_ACTION_DAILY, context)
        clear_flow(context)
        await update.message.reply_text(f"✅ گزارش روزانه ساعت {normalized} فعال شد.", reply_markup=main_menu())
        return

    if flow == "admin_search" and _is_admin(user_id):
        query = text.strip()
        target = None
        if query.isdigit():
            target = db.get_user(int(query))
        else:
            username = query.lstrip("@").casefold()
            with db._conn() as c:
                c.row_factory = sqlite3.Row
                row = c.execute("SELECT * FROM users WHERE lower(username) = ? LIMIT 1", (username,)).fetchone()
                target = dict(row) if row else None
        clear_flow(context)
        if not target:
            await update.message.reply_text("❌ کاربر پیدا نشد.", reply_markup=admin_menu())
            return
        uid = int(target["user_id"])
        counts = db.referral_counts(uid)
        days = vip_days_left(uid) if is_vip(uid) else None
        vip_state = "فعال" if is_vip(uid) else "غیرفعال"
        if is_vip(uid):
            vip_state += " — بدون انقضا" if days is None else f" — {days} روز"
        info = (
            f"👤 <b>{html.escape(target.get('first_name') or 'کاربر')}</b>\n"
            f"🔗 @{html.escape(target.get('username') or 'ندارد')}\n"
            f"🆔 <code>{uid}</code>\n\n"
            f"⭐ VIP: {vip_state}\n"
            f"🔔 هشدارها: {len(db.user_alerts(uid))}\n"
            f"🎁 دعوت معتبر: {counts['qualified']} | در انتظار: {counts['pending']}\n"
            f"📅 عضویت: {str(target.get('joined_at') or '')[:10]}"
        )
        await update.message.reply_text(info, parse_mode="HTML", reply_markup=admin_user_menu(uid))
        return

    if flow == "admin_addvip" and _is_admin(user_id):
        parts = text.replace(",", " ").split()
        if not parts or not parts[0].isdigit():
            await update.message.reply_text(
                "فرمت: <code>USER_ID DAYS</code>\nمثال: <code>123456789 30</code>",
                parse_mode="HTML",
            )
            return
        target_id = int(parts[0])
        days = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 30
        days = max(1, min(days, 3650))
        db.add_vip(target_id, days, source="admin_panel")
        clear_flow(context)
        await update.message.reply_text(
            f"✅ کاربر <code>{target_id}</code> برای {days} روز VIP شد.",
            parse_mode="HTML", reply_markup=admin_vip_menu(),
        )
        try:
            await context.bot.send_message(
                target_id, f"⭐ اشتراک VIP شما برای {days} روز فعال/تمدید شد.", reply_markup=main_menu()
            )
        except Exception:
            logger.debug("Admin VIP notification failed", exc_info=True)
        return

    if flow == "admin_removevip" and _is_admin(user_id):
        target = text.strip()
        if not target.isdigit():
            await update.message.reply_text("شناسه عددی کاربر را بفرست.")
            return
        removed = db.remove_vip(int(target))
        clear_flow(context)
        await update.message.reply_text(
            "✅ VIP حذف شد." if removed else "این کاربر VIP فعال ثبت‌شده نداشت.",
            reply_markup=admin_vip_menu(),
        )
        return

    if flow == "support":
        clear_flow(context)
        user = update.effective_user
        if not str(ADMIN_ID).isdigit():
            await update.message.reply_text(f"پشتیبانی داخل ربات موقتاً در دسترس نیست. مستقیم به @{DEVELOPER_USERNAME} پیام بدهید.", reply_markup=main_menu()); return
        safe_name=html.escape(user.full_name or user.first_name or "کاربر")
        safe_username=html.escape(user.username or "ندارد")
        admin_text=("💬 <b>پیام جدید پشتیبانی طلایار</b>\n\n"
                    f"👤 کاربر: {safe_name}\n🔗 یوزرنیم: @{safe_username}\n🆔 شناسه: <code>{user.id}</code>\n\n"
                    f"📝 پیام:\n{html.escape(text)}")
        try:
            await context.bot.send_message(int(ADMIN_ID),admin_text,parse_mode="HTML")
            await update.message.reply_text("✅ پیام شما برای پشتیبانی ارسال شد. در اولین فرصت پاسخ داده می‌شود.",reply_markup=main_menu())
        except Exception:
            logger.exception("Support forwarding failed")
            await update.message.reply_text(f"❌ ارسال داخلی انجام نشد. لطفاً مستقیم به @{DEVELOPER_USERNAME} پیام بدهید.",reply_markup=main_menu())
        return

    if flow == "broadcast" and _is_admin(user_id):
        with db._conn() as c:
            c.row_factory = sqlite3.Row
            users_rows = c.execute("SELECT chat_id, user_id FROM users").fetchall()
        clear_flow(context)
        status = await update.message.reply_text("در حال ارسال…")
        sent = failed = 0

        async def _send_one(row):
            try:
                await context.bot.send_message(row["chat_id"] or row["user_id"], text, reply_markup=main_menu())
                return 1, 0
            except Exception:
                return 0, 1

        # Batch کوچک برای جلوگیری از فشار CPU/شبکه و Rate Limit تلگرام.
        for start in range(0, len(users_rows), 20):
            batch = users_rows[start:start + 20]
            results = await asyncio.gather(*(_send_one(row) for row in batch))
            sent += sum(r[0] for r in results)
            failed += sum(r[1] for r in results)
            if start + 20 < len(users_rows):
                await asyncio.sleep(1.0)
        await status.edit_text(f"✅ تمام شد. موفق: {sent} | ناموفق: {failed}", reply_markup=admin_menu())
        return

    await update.message.reply_text("یکی از دکمه‌های منو را انتخاب کن.", reply_markup=main_menu())


async def receive_photo_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("flow") != "receipt":
        await update.message.reply_text("ابتدا از بخش VIP یک بسته انتخاب کن.", reply_markup=main_menu())
        return
    plan = int(context.user_data.get("purchase_plan", 30))
    order_id = str(uuid.uuid4())[:8].upper()
    file_id = update.message.photo[-1].file_id
    db.create_order(order_id, update.effective_user.id, plan, VIP_PRICE_30 if plan == 30 else VIP_PRICE_90,
                    "pending", _utc_now())
    # Update order with receipt
    with db._conn() as c:
        c.execute("UPDATE orders SET receipt_file_id = ? WHERE order_id = ?", (file_id, order_id))
    clear_flow(context)
    await update.message.reply_text("✅ رسید برای ادمین ارسال شد.", reply_markup=main_menu())
    if str(ADMIN_ID).isdigit():
        await context.bot.send_photo(
            int(ADMIN_ID), file_id,
            caption=f"🧾 خرید VIP\nکاربر: {update.effective_user.id}\n@{update.effective_user.username or 'ندارد'}\nبسته: {plan} روز\nکد: {order_id}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ تأیید", callback_data=f"purchase_ok:{order_id}"),
                InlineKeyboardButton("❌ رد", callback_data=f"purchase_no:{order_id}"),
            ]]))


async def buttons_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id, data = q.from_user.id, q.data
    db.update_last_seen(user_id)
    db.increment_activity(user_id)

    if data == "home":
        clear_flow(context)
        await _show_callback_text(q, "🟡 منوی اصلی طلایار", reply_markup=main_menu())
        return

    if data == "referrals":
        bot_username = await get_bot_username(context)
        await _show_callback_text(
            q,
            referral_progress_text(user_id, bot_username),
            reply_markup=referral_menu(user_id, bot_username),
            parse_mode="HTML",
        )
        return

    if data in {"referrals_rewards", "referrals_top"}:
        bot_username = await get_bot_username(context)
        await _show_callback_text(
            q,
            referral_rewards_text(user_id),
            reply_markup=referral_menu(user_id, bot_username),
            parse_mode="HTML",
        )
        return

    if data == "prices":
        await q.edit_message_text("📊 بازار را انتخاب کن:", reply_markup=price_menu())
        return

    if data in {"gold", "iran_currency", "ounce", "crypto"}:
        market, error = get_market_data()
        if market is None:
            await q.edit_message_text(f"❌ {error}", reply_markup=price_menu())
            return
        await record_referral_interaction(user_id, REF_ACTION_PRICE, context)
        if data == "gold":
            text = build_gold_text(market)
        elif data == "iran_currency":
            text = build_currency_text(market)
        elif data == "ounce":
            text = "🌎 <b>انس جهانی</b>\n\n" + show_item(find_alert_item(market, "ounce"), "انس جهانی")
        else:
            text = "₿ <b>ارز دیجیتال</b>\n\n"
            for symbols, label, words in ((["BTC", "BTCUSDT"], "بیت‌کوین", ["Bitcoin"]),
                                          (["ETH", "ETHUSDT"], "اتریوم", ["Ethereum"]),
                                          (["USDT", "USDTUSD"], "تتر", ["Tether"])):
                text += show_item(find_item(market, symbols, ["cryptocurrency"], words), label)
        await q.edit_message_text(text + f"\n<i>{DISCLAIMER}</i>", reply_markup=price_menu(), parse_mode="HTML")
        return

    if data == "melted_center":
        market,error=get_market_data()
        if not market:
            await q.edit_message_text(f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=main_menu()); return
        capture_history(market)
        await _show_callback_text(q, build_melted_center(market), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 بروزرسانی",callback_data="melted_center")],[InlineKeyboardButton("🔙 منوی اصلی",callback_data="home")]]), parse_mode="HTML"); return

    if data == "navasan":
        if not is_vip(user_id):
            await q.edit_message_text("⚡ مرکز نوسان حرفه‌ای مخصوص کاربران VIP است.", reply_markup=vip_menu(user_id))
            return
        market, error = get_market_data()
        if market:
            capture_history(market)
        await _show_callback_text(q, "⚡ <b>Talayar Navasan Intelligence v13</b>\n\nتحلیل چندلایه، رادار انحراف، اسکن فرصت، اعتبارسنجی تاریخی و هشدارهای هوشمند.", reply_markup=navasan_menu(), parse_mode="HTML")
        return

    if data == "nv:scanner":
        if not is_vip(user_id):
            await q.edit_message_text("این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        market,error=get_market_data()
        if not market:
            await q.edit_message_text(f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=navasan_menu()); return
        capture_history(market)
        await _show_callback_text(q, build_opportunity_scanner(market), reply_markup=navasan_menu(), parse_mode="HTML")
        return

    if data == "nv:bubble":
        if not is_vip(user_id):
            await q.edit_message_text("این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        market,error=get_market_data()
        if not market:
            await q.edit_message_text(f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=navasan_menu()); return
        capture_history(market)
        await _show_callback_text(q, build_bubble_radar(market), reply_markup=navasan_menu(), parse_mode="HTML")
        return

    if data == "nv:heatmap":
        if not is_vip(user_id):
            await q.edit_message_text("این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        market,error=get_market_data()
        if not market:
            await q.edit_message_text(f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=navasan_menu()); return
        capture_history(market)
        await _show_callback_text(q, build_heatmap(market), reply_markup=navasan_menu(), parse_mode="HTML")
        return

    if data == "nv:assetmenu":
        if not is_vip(user_id):
            await q.edit_message_text("این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        await q.edit_message_text("دارایی را برای تحلیل چندلایه انتخاب کن:", reply_markup=navasan_asset_menu("nv:asset")); return

    if data.startswith("nv:asset:"):
        if not is_vip(user_id):
            await q.edit_message_text("این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        asset=data.split(":",2)[2]
        market,error=get_market_data()
        if not market:
            await q.edit_message_text(f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=navasan_menu()); return
        capture_history(market)
        await _show_callback_text(q, build_navasan_asset_text(asset,market), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 بروزرسانی",callback_data=f"nv:asset:{asset}")],[InlineKeyboardButton("🔙 انتخاب دارایی",callback_data="nv:assetmenu")]]), parse_mode="HTML")
        return

    if data == "nv:backtestmenu":
        if not is_vip(user_id):
            await q.edit_message_text("این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        await q.edit_message_text("دارایی را برای آزمایش تاریخی انتخاب کن:", reply_markup=navasan_asset_menu("nv:bt")); return

    if data.startswith("nv:bt:"):
        if not is_vip(user_id):
            await q.edit_message_text("این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        asset=data.split(":",2)[2]
        await _show_callback_text(q, build_backtest_text(asset), reply_markup=navasan_asset_menu("nv:bt"), parse_mode="HTML"); return

    if data == "nv:method":
        if not is_vip(user_id):
            await q.edit_message_text("این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        await _show_callback_text(q, navasan_method_text(), reply_markup=navasan_menu(), parse_mode="HTML"); return

    if data == "nv:smartalerts":
        if not is_vip(user_id):
            await q.edit_message_text("هشدار هوشمند مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        rows=[[InlineKeyboardButton("➕ افزودن هشدار هوشمند",callback_data="nv:saasset")]]
        items=db.user_smart_alerts(user_id)
        for i,a in enumerate(items,1):
            rows.append([InlineKeyboardButton(f"🗑 حذف {i}",callback_data=f"nv:sadel:{a['id']}")])
        if items: rows.append([InlineKeyboardButton("🧹 حذف همه",callback_data="nv:saclear")])
        rows.append([InlineKeyboardButton("🔙 مرکز نوسان",callback_data="navasan")])
        await _show_callback_text(q, build_smart_alerts_text(user_id), reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML"); return

    if data == "nv:saasset":
        if not is_vip(user_id):
            await q.edit_message_text("هشدار هوشمند مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        await q.edit_message_text("دارایی هشدار هوشمند را انتخاب کن:",reply_markup=navasan_asset_menu("nv:sarule")); return

    if data.startswith("nv:sarule:"):
        if not is_vip(user_id): return
        asset=data.split(":",2)[2]
        await q.edit_message_text(f"قانون هشدار برای {ALERT_ASSETS.get(asset,{}).get('label',asset)}:",reply_markup=smart_alert_rule_menu(asset)); return

    if data.startswith("nv:saadd:"):
        if not is_vip(user_id): return
        _,_,asset,rule=data.split(":",3)
        result=db.add_smart_alert(user_id,q.message.chat.id,asset,rule)
        msg="✅ هشدار هوشمند فعال شد." if result=="added" else "✅ این هشدار از قبل وجود داشت و فعال است."
        await q.edit_message_text(msg,reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚨 هشدارهای من",callback_data="nv:smartalerts")],[InlineKeyboardButton("🔙 مرکز نوسان",callback_data="navasan")]])); return

    if data.startswith("nv:sadel:"):
        db.delete_smart_alert(data.split(":",2)[2],user_id)
        await q.edit_message_text("✅ هشدار حذف شد.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 هشدارهای هوشمند",callback_data="nv:smartalerts")]])); return

    if data == "nv:saclear":
        db.delete_user_smart_alerts(user_id)
        await q.edit_message_text("✅ همه هشدارهای هوشمند حذف شدند.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 مرکز نوسان",callback_data="navasan")]])); return

    if data == "alerts":
        clear_flow(context)
        await q.edit_message_text("🔔 هشدار عددی، درصدی و تکرارشونده", reply_markup=alert_menu())
        return

    if data == "alert_new":
        if not is_vip(user_id) and len(db.user_alerts(user_id)) >= FREE_ALERT_LIMIT:
            await q.edit_message_text("سقف یک هشدار رایگان پر شده است.", reply_markup=alert_menu())
            return
        context.user_data["alert_draft"] = {}
        await q.edit_message_text("نوع هشدار را انتخاب کن:", reply_markup=alert_kind_menu(user_id))
        return

    if data.startswith("alert_kind:"):
        kind = data.split(":", 1)[1]
        if kind == "percent" and not is_vip(user_id):
            await q.edit_message_text("هشدار درصدی مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        context.user_data["alert_draft"] = {"type": kind}
        await q.edit_message_text("دارایی را انتخاب کن:", reply_markup=alert_asset_menu())
        return

    if data.startswith("alert_asset:"):
        asset = data.split(":", 1)[1]
        draft = context.user_data.get("alert_draft", {})
        draft["asset"] = asset
        await q.edit_message_text("شرط هشدار را انتخاب کن:",
                                  reply_markup=percent_condition_menu() if draft.get("type") == "percent" else alert_condition_menu())
        return

    if data.startswith("alert_condition:"):
        draft = context.user_data.get("alert_draft", {})
        draft["condition"] = data.split(":", 1)[1]
        await q.edit_message_text("نوع اجرا را انتخاب کن:", reply_markup=alert_mode_menu())
        return

    if data.startswith("alert_mode:"):
        mode = data.split(":", 1)[1]
        if mode == "repeat" and not is_vip(user_id):
            await q.edit_message_text("تکرارشونده مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        context.user_data["alert_draft"]["mode"] = mode
        context.user_data["flow"] = "alert_value"
        prompt = "درصد هدف را بفرست؛ مثال 2.5" if context.user_data["alert_draft"].get("type") == "percent" else "قیمت هدف را فقط به‌صورت عدد بفرست."
        await q.edit_message_text(prompt + "\nبرای لغو /cancel")
        return

    if data == "alert_list":
        alerts = db.user_alerts(user_id)
        if not alerts:
            await q.edit_message_text("📋 شما هیچ هشدار فعالی ندارید.", reply_markup=alert_menu())
            return
        lines = ["📋 <b>هشدارهای فعال شما</b>", ""]
        rows = []
        for index, alert in enumerate(alerts, start=1):
            asset = ALERT_ASSETS.get(alert.get("asset"), {})
            label = asset.get("label", alert.get("asset", "دارایی"))
            if alert.get("type") == "percent":
                detail = f"{_condition_label(alert.get('condition'))} {alert.get('percent')}٪"
            else:
                detail = f"{_condition_label(alert.get('condition'))} {_format_number(alert.get('target'))}"
            lines.append(f"{index}. {label}\nشرط: {detail}\nاجرا: {'تکرارشونده' if alert.get('mode') == 'repeat' else 'یک‌باره'}")
            lines.append("")
            rows.append([
                InlineKeyboardButton(f"✏️ ویرایش {index}", callback_data=f"alert_edit:{alert.get('id')}"),
                InlineKeyboardButton(f"🗑 حذف {index}", callback_data=f"alert_del:{alert.get('id')}"),
            ])
        rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="alerts")])
        await q.edit_message_text("\n".join(lines).rstrip(), reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML")
        return

    if data.startswith("alert_del:"):
        db.delete_alert(data.split(":", 1)[1], user_id)
        await q.edit_message_text("✅ حذف شد.", reply_markup=alert_menu())
        return

    if data.startswith("alert_edit:"):
        context.user_data["flow"] = "alert_edit"
        context.user_data["alert_edit_id"] = data.split(":", 1)[1]
        await q.edit_message_text("هدف جدید را فقط به‌صورت عدد بفرست. برای لغو /cancel")
        return

    if data == "alert_delete":
        await q.edit_message_text("همه هشدارها حذف شوند؟", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ بله", callback_data="alert_delete_confirm")],
            [InlineKeyboardButton("❌ خیر", callback_data="alerts")]]))
        return

    if data == "alert_delete_confirm":
        db.delete_user_alerts(user_id)
        await q.edit_message_text("✅ همه هشدارها حذف شدند.", reply_markup=alert_menu())
        return

    if data == "daily":
        if not is_vip(user_id):
            await q.edit_message_text("گزارش روزانه مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        sub = db.get_daily_sub(user_id)
        status = f"فعال در {sub.get('time')}" if sub and sub.get("active") else "غیرفعال"
        await q.edit_message_text(f"🗓 گزارش روزانه\nوضعیت: {status}\nساعت را انتخاب کن:", reply_markup=daily_menu(bool(sub and sub.get("active"))))
        return

    if data.startswith("daily_set:"):
        report_time = data.split(":", 1)[1]
        db.set_daily_sub(user_id, q.message.chat.id, report_time)
        await record_referral_interaction(user_id, REF_ACTION_DAILY, context)
        await q.edit_message_text(f"✅ گزارش ساعت {report_time} فعال شد.", reply_markup=daily_menu(True))
        return

    if data == "daily_now":
        if not is_vip(user_id):
            await q.edit_message_text("گزارش روزانه مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        market, error = get_market_data()
        if not market:
            await q.edit_message_text(f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=daily_menu(False))
            return
        bot_username = await get_bot_username(context)
        await record_referral_interaction(user_id, REF_ACTION_DAILY, context)
        await _show_callback_text(
            q, build_daily_report(market),
            reply_markup=share_report_menu(user_id, bot_username, market),
            parse_mode="HTML",
        )
        return

    if data == "daily_custom":
        context.user_data["flow"] = "daily_time"
        await q.edit_message_text("ساعت را به وقت ایران مثل 09:30 بفرست. برای لغو /cancel")
        return

    if data == "daily_stop":
        sub = db.get_daily_sub(user_id)
        if sub:
            db.set_daily_sub(user_id, q.message.chat.id, sub.get("time", "09:00"), False)
        await q.edit_message_text("⛔ گزارش متوقف شد.", reply_markup=daily_menu(False))
        return

    if data == "charts":
        context.user_data.pop("chart_request_token", None)
        await _show_callback_text(q, "📈 دارایی را برای نمودار تکنیکال انتخاب کن:", reply_markup=chart_menu())
        return

    if data.startswith("chart_asset:"):
        asset = data.split(":", 1)[1]
        context.user_data.pop("chart_request_token", None)
        await _show_callback_text(q, "بازه نمودار تکنیکال را انتخاب کن:", reply_markup=chart_period_menu(asset, candle=True))
        return

    if data.startswith("chart_candle:"):
        asset = data.split(":", 1)[1]
        context.user_data.pop("chart_request_token", None)
        await _show_callback_text(q, "بازه نمودار تکنیکال را انتخاب کن:", reply_markup=chart_period_menu(asset, candle=True))
        return

    if data.startswith("chart:"):
        _, asset, hours = data.split(":")
        if int(hours) in {168, 720} and not is_vip(user_id):
            await _show_callback_text(q, "نمودارهای ۷ و ۳۰ روزه مخصوص VIP هستند.", reply_markup=vip_menu(user_id))
            return
        sent = await send_candle_chart(q, context, asset, int(hours))
        if sent is False:
            await _show_callback_text(
                q,
                "❌ داده کافی برای ساخت نمودار تکنیکال وجود ندارد؛ بعد از جمع‌شدن چند نمونه دیگر دوباره امتحان کن.",
                reply_markup=chart_period_menu(asset, candle=True),
            )
        else:
            await record_referral_interaction(user_id, REF_ACTION_CHART, context)
        return

    if data.startswith("candle:"):
        _, asset, hours = data.split(":")
        if int(hours) in {168, 720} and not is_vip(user_id):
            await _show_callback_text(q, "نمودار تکنیکال ۷ و ۳۰ روزه مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        sent = await send_candle_chart(q, context, asset, int(hours))
        if sent is False:
            await _show_callback_text(
                q,
                "❌ داده کافی برای ساخت نمودار تکنیکال وجود ندارد؛ بعد از جمع‌شدن چند نمونه دیگر دوباره امتحان کن.",
                reply_markup=chart_period_menu(asset, candle=True),
            )
        else:
            await record_referral_interaction(user_id, REF_ACTION_CHART, context)
        return

    if data == "account":
        sub = db.get_daily_sub(user_id)
        daily = f"فعال در {sub.get('time')}" if sub and sub.get("active") else "غیرفعال"
        days = vip_days_left(user_id) if is_vip(user_id) else None
        remain = "" if not is_vip(user_id) else f"\nزمان VIP: {'بدون انقضا' if days is None else str(days) + ' روز'}"
        text = (f"👤 <b>حساب کاربری</b>\n\nشناسه: <code>{user_id}</code>\n"
                f"نوع حساب: {'VIP ⭐' if is_vip(user_id) else 'رایگان'}{remain}\n"
                f"هشدار فعال: {len(db.user_alerts(user_id))}\nگزارش روزانه: {daily}")
        await q.edit_message_text(text, reply_markup=main_menu(), parse_mode="HTML")
        return

    if data == "vip":
        await q.edit_message_text(vip_text(user_id), reply_markup=vip_menu(user_id), parse_mode="HTML")
        return

    if data.startswith("buy:"):
        plan = int(data.split(":", 1)[1])
        price = VIP_PRICE_30 if plan == 30 else VIP_PRICE_90
        payment, error = await asyncio.to_thread(create_zarinpal_payment, user_id, plan)
        rows = []
        if payment:
            rows.append([InlineKeyboardButton("💳 پرداخت آنلاین و فعال‌سازی فوری", url=payment["url"])])
        rows.extend([
            [InlineKeyboardButton("📷 پرداخت کارت‌به‌کارت و ارسال رسید", callback_data=f"receipt:{plan}")],
            [InlineKeyboardButton("💬 ادمین", url=f"https://t.me/{ADMIN_USERNAME}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="vip")],
        ])
        gateway_note = (
            f"\n\n✅ درگاه آنلاین آماده است؛ پس از پرداخت، VIP خودکار فعال می‌شود.\n"
            f"کد سفارش: <code>{payment['order_id']}</code>"
            if payment else
            f"\n\n⚠️ {html.escape(error or 'درگاه آنلاین فعال نیست')}؛ روش ارسال رسید در دسترس است."
        )
        await q.edit_message_text(
            f"🧾 بسته {plan} روزه — {price} تومان\n\n"
            f"روش اول: پرداخت آنلاین و فعال‌سازی فوری\n"
            f"روش دوم: {html.escape(PAYMENT_INFO)}"
            f"{gateway_note}",
            reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML")
        return

    if data.startswith("receipt:"):
        context.user_data.update({"flow": "receipt", "purchase_plan": int(data.split(":", 1)[1])})
        await q.edit_message_text("📷 حالا تصویر رسید را بفرست. برای لغو /cancel")
        return

    if data == "help":
        await q.edit_message_text(help_text(), reply_markup=help_menu(), parse_mode="HTML")
        return

    if data == "support":
        context.user_data["flow"] = "support"
        await q.edit_message_text(
            support_prompt_text(),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💻 پیام مستقیم به توسعه‌دهنده", url=f"https://t.me/{DEVELOPER_USERNAME}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="help")],
            ]), parse_mode="HTML")
        return

    if data == "plans":
        await q.edit_message_text(
            "رایگان: قیمت‌ها، ماشین‌حساب، نمودار ۲۴ساعته و یک هشدار عددی.\n\n"
            f"VIP: هشدار نامحدود/درصدی/تکراری، گزارش روزانه، نمودار تکنیکال ۷ و ۳۰ روزه، "
            f"کندل حرفه‌ای همه دارایی‌های اصلی، تحلیل هوشمند، بازار من تا {WATCHLIST_VIP_LIMIT} دارایی و مرکز نوسان v12.",
            reply_markup=vip_menu(user_id))
        return

    if data == "analysis":
        if not is_vip(user_id):
            await q.edit_message_text("تحلیل هوشمند مخصوص کاربران VIP است.", reply_markup=vip_menu(user_id))
            return
        market, error = get_market_data()
        if not market:
            await q.edit_message_text(f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=main_menu())
            return
        capture_history(market)
        bot_username = await get_bot_username(context)
        await record_referral_interaction(user_id, REF_ACTION_ANALYSIS, context)
        await _show_callback_text(
            q, build_ai_summary(market),
            reply_markup=share_analysis_menu(user_id, bot_username, market),
            parse_mode="HTML",
        )
        return

    if data == "watchlist":
        if not is_vip(user_id):
            await q.edit_message_text("بازار من مخصوص کاربران VIP است.", reply_markup=vip_menu(user_id))
            return
        market, _ = get_market_data()
        text = build_watchlist_text(user_id, market or {})
        await record_referral_interaction(user_id, REF_ACTION_ANALYSIS, context)
        await q.edit_message_text(text, reply_markup=watchlist_menu(user_id), parse_mode="HTML")
        return

    if data == "wl_add":
        if not is_vip(user_id):
            await q.edit_message_text("بازار من مخصوص کاربران VIP است.", reply_markup=vip_menu(user_id))
            return
        if len(db.get_watchlist(user_id)) >= WATCHLIST_VIP_LIMIT:
            await q.edit_message_text(
                f"حداکثر {WATCHLIST_VIP_LIMIT} دارایی می‌توانید اضافه کنید.",
                reply_markup=watchlist_menu(user_id),
            )
            return
        await q.edit_message_text("دارایی را انتخاب کن:", reply_markup=watchlist_add_menu())
        return

    if data.startswith("wl_add:"):
        if not is_vip(user_id):
            await q.edit_message_text("بازار من مخصوص کاربران VIP است.", reply_markup=vip_menu(user_id))
            return
        asset = data.split(":", 1)[1]
        result = db.add_watchlist(user_id, asset)
        if result == "added":
            await q.edit_message_text(f"✅ {ALERT_ASSETS.get(asset, {}).get('label', asset)} اضافه شد.", reply_markup=watchlist_menu(user_id))
        elif result == "limit":
            await q.edit_message_text(f"❌ سقف بازار من {WATCHLIST_VIP_LIMIT} دارایی است.", reply_markup=watchlist_menu(user_id))
        else:
            await q.edit_message_text("❌ این دارایی قبلاً اضافه شده.", reply_markup=watchlist_menu(user_id))
        return

    if data.startswith("wl_remove:"):
        if not is_vip(user_id):
            await q.edit_message_text("بازار من مخصوص کاربران VIP است.", reply_markup=vip_menu(user_id))
            return
        asset = data.split(":", 1)[1]
        db.remove_watchlist(user_id, asset)
        market, _ = get_market_data()
        text = build_watchlist_text(user_id, market or {})
        await q.edit_message_text(text, reply_markup=watchlist_menu(user_id), parse_mode="HTML")
        return

    if data.startswith("purchase_ok:") or data.startswith("purchase_no:"):
        if not _is_admin(user_id):
            return
        order_id = data.split(":", 1)[1]
        order = db.get_order_by_id(order_id)
        if not order or order.get("status") != "pending":
            await q.answer("قبلاً بررسی شده", show_alert=True)
            return
        approved = data.startswith("purchase_ok:")
        db.update_order_status(order_id, "approved" if approved else "rejected", _utc_now())
        if approved:
            db.add_vip(order["user_id"], order["plan"], f"purchase:{order_id}")
        result = "✅ تأیید و فعال شد" if approved else "❌ رد شد"
        await q.edit_message_caption((q.message.caption or "") + "\n\n" + result)
        await context.bot.send_message(order["user_id"],
            f"⭐ اشتراک {order['plan']} روزه فعال شد." if approved else f"پرداخت تأیید نشد؛ به @{ADMIN_USERNAME} پیام بده.",
            reply_markup=main_menu())
        return

    if data.startswith("admin_order:"):
        if not _is_admin(user_id):
            return
        order_id = data.split(":", 1)[1]
        order = db.get_order_by_id(order_id)
        if not order:
            await _show_callback_text(q, "❌ سفارش پیدا نشد.", reply_markup=admin_menu())
            return
        caption = (
            f"🧾 <b>سفارش {html.escape(order_id)}</b>\n\n"
            f"👤 کاربر: <code>{order.get('user_id')}</code>\n"
            f"⭐ بسته: {order.get('plan')} روز\n"
            f"💰 مبلغ: {html.escape(str(order.get('amount') or ''))}\n"
            f"💳 روش: {html.escape(str(order.get('payment_method') or 'manual'))}\n"
            f"📌 وضعیت: {html.escape(str(order.get('status') or ''))}"
        )
        receipt = order.get("receipt_file_id")
        if receipt and order.get("status") == "pending":
            await context.bot.send_photo(
                chat_id=q.message.chat.id,
                photo=receipt,
                caption=caption,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("✅ تأیید", callback_data=f"purchase_ok:{order_id}"),
                    InlineKeyboardButton("❌ رد", callback_data=f"purchase_no:{order_id}"),
                ]]),
            )
            await q.answer("رسید ارسال شد")
        else:
            await _show_callback_text(q, caption, reply_markup=admin_menu(), parse_mode="HTML")
        return

    if data.startswith("admin_user:"):
        if not _is_admin(user_id):
            return
        target_id = data.split(":", 1)[1]
        if not target_id.isdigit():
            await q.answer("شناسه نامعتبر", show_alert=True)
            return
        target = db.get_user(int(target_id))
        if not target:
            await _show_callback_text(q, "❌ کاربر پیدا نشد.", reply_markup=admin_menu())
            return
        uid = int(target_id)
        counts = db.referral_counts(uid)
        days = vip_days_left(uid) if is_vip(uid) else None
        vip_state = "غیرفعال"
        if is_vip(uid):
            vip_state = "فعال — بدون انقضا" if days is None else f"فعال — {days} روز"
        text = (
            f"👤 <b>{html.escape(target.get('first_name') or 'کاربر')}</b>\n"
            f"🔗 @{html.escape(target.get('username') or 'ندارد')}\n"
            f"🆔 <code>{uid}</code>\n\n"
            f"⭐ VIP: {vip_state}\n"
            f"🔔 هشدارها: {len(db.user_alerts(uid))}\n"
            f"🎁 دعوت معتبر: {counts['qualified']} | در انتظار: {counts['pending']}\n"
            f"📈 امتیاز فعالیت: {int(target.get('activity_score') or 0)}\n"
            f"🕒 آخرین فعالیت: {str(target.get('last_seen') or '')[:16]}"
        )
        await _show_callback_text(q, text, reply_markup=admin_user_menu(uid), parse_mode="HTML")
        return

    if data.startswith("admin_user_vip30:") or data.startswith("admin_user_vip90:"):
        if not _is_admin(user_id):
            return
        target_id = data.split(":", 1)[1]
        if not target_id.isdigit():
            return
        days = 30 if data.startswith("admin_user_vip30:") else 90
        db.add_vip(int(target_id), days, source="admin_panel")
        await _show_callback_text(q, f"✅ <code>{target_id}</code> به مدت {days} روز VIP شد/تمدید شد.", reply_markup=admin_user_menu(target_id), parse_mode="HTML")
        try:
            await context.bot.send_message(int(target_id), f"⭐ اشتراک VIP شما برای {days} روز فعال/تمدید شد.", reply_markup=main_menu())
        except Exception:
            logger.debug("Admin user VIP notification failed", exc_info=True)
        return

    if data.startswith("admin_user_removevip:"):
        if not _is_admin(user_id):
            return
        target_id = data.split(":", 1)[1]
        if target_id.isdigit():
            removed = db.remove_vip(int(target_id))
            await _show_callback_text(q, "✅ VIP حذف شد." if removed else "کاربر VIP ثبت‌شده نداشت.", reply_markup=admin_user_menu(target_id))
        return

    if data.startswith("admin_ref_approve:"):
        if not _is_admin(user_id):
            return
        referred_id = data.split(":", 1)[1]
        if not referred_id.isdigit():
            return
        ok = await qualify_referral(int(referred_id), context, allow_flagged=True)
        await _show_callback_text(
            q,
            "✅ دعوت به‌صورت دستی تأیید شد و پاداش‌ها بررسی شدند." if ok else "این دعوت قبلاً تأیید شده یا وجود ندارد.",
            reply_markup=admin_menu(),
        )
        return

    if data.startswith("admin:"):
        if not _is_admin(user_id):
            await q.answer("دسترسی غیرمجاز", show_alert=True)
            return
        action = data.split(":", 1)[1]

        if action == "menu":
            clear_flow(context)
            await _show_callback_text(q, "👑 <b>پنل مدیریت طلایار</b>\n\nتمام دسترسی‌های مدیریتی از اینجا در دسترس است.", reply_markup=admin_menu(), parse_mode="HTML")
            return

        if action == "stats":
            s = db.stats()
            with db._conn() as c:
                active_vip_rows = c.execute("SELECT user_id, expires_at FROM vip_users").fetchall()
            active_vip = sum(1 for uid, exp in active_vip_rows if is_vip(uid))
            text = (
                "📊 <b>آمار کلی طلایار</b>\n\n"
                f"👥 کاربران: <b>{s['users']}</b>\n"
                f"⭐ VIP فعال: <b>{active_vip}</b>\n"
                f"🔔 هشدارها: <b>{s['alerts']}</b>\n"
                f"🗓 گزارش روزانه فعال: <b>{s['daily']}</b>\n"
                f"🎁 دعوت معتبر: <b>{s['refs']}</b>\n"
                f"🧾 سفارش منتظر: <b>{s['pending']}</b>"
            )
            await _show_callback_text(q, text, reply_markup=admin_menu(), parse_mode="HTML")
            return

        if action == "users":
            users = db.recent_users(10)
            lines = ["👥 <b>کاربران اخیر</b>", ""]
            rows = []
            for u in users:
                uid = int(u["user_id"])
                name = html.escape(u.get("first_name") or "کاربر")
                lines.append(f"• {name} — <code>{uid}</code> {'⭐' if is_vip(uid) else ''}")
                rows.append([InlineKeyboardButton(f"👤 {name[:20]}", callback_data=f"admin_user:{uid}")])
            rows.append([InlineKeyboardButton("🔎 جستجوی کاربر", callback_data="admin:search")])
            rows.append([InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin:menu")])
            await _show_callback_text(q, "\n".join(lines), reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML")
            return

        if action == "search":
            context.user_data["flow"] = "admin_search"
            await _show_callback_text(q, "🔎 شناسه عددی یا @username کاربر را بفرست.\nبرای لغو /cancel", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin:menu")]]))
            return

        if action == "vip":
            with db._conn() as c:
                rows = c.execute("SELECT user_id FROM vip_users").fetchall()
            active_count = sum(1 for (uid,) in rows if is_vip(uid))
            await _show_callback_text(q, f"⭐ <b>مدیریت VIP</b>\n\nVIP فعال: <b>{active_count}</b>\nاز دکمه‌های زیر استفاده کن.", reply_markup=admin_vip_menu(), parse_mode="HTML")
            return

        if action == "addvip":
            context.user_data["flow"] = "admin_addvip"
            await _show_callback_text(q, "➕ شناسه کاربر و تعداد روز را بفرست.\nمثال: <code>123456789 30</code>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 مدیریت VIP", callback_data="admin:vip")]]), parse_mode="HTML")
            return

        if action == "removevip":
            context.user_data["flow"] = "admin_removevip"
            await _show_callback_text(q, "➖ شناسه عددی کاربری که باید VIP او حذف شود را بفرست.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 مدیریت VIP", callback_data="admin:vip")]]))
            return

        if action == "vip_recent":
            rows = db.recent_vips(10)
            lines = ["📋 <b>VIPهای اخیر</b>", ""]
            buttons = []
            for row in rows:
                uid = int(row["user_id"])
                days = vip_days_left(uid) if is_vip(uid) else 0
                lines.append(f"• <code>{uid}</code> — {'فعال' if is_vip(uid) else 'منقضی'} — {days if days is not None else '∞'} روز")
                buttons.append([InlineKeyboardButton(f"👤 {uid}", callback_data=f"admin_user:{uid}")])
            buttons.append([InlineKeyboardButton("🔙 مدیریت VIP", callback_data="admin:vip")])
            await _show_callback_text(q, "\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
            return

        if action in {"payments", "pending"}:
            orders = db.load_orders()
            pending = [o for o in orders if o.get("status") in {"pending", "pending_gateway"}]
            approved = sum(1 for o in orders if o.get("status") == "approved")
            rejected = sum(1 for o in orders if o.get("status") in {"rejected", "gateway_failed"})
            lines = [
                "🧾 <b>سفارش‌ها و پرداخت</b>", "",
                f"⏳ منتظر: <b>{len(pending)}</b>",
                f"✅ تأییدشده: <b>{approved}</b>",
                f"❌ رد/ناموفق: <b>{rejected}</b>",
                f"💳 زرین‌پال: <b>{'آماده' if zarinpal_enabled() else 'هنوز تنظیم نشده'}</b>",
            ]
            buttons = []
            if pending:
                lines.extend(["", "آخرین سفارش‌های منتظر:"])
                for order in pending[-10:]:
                    lines.append(f"• {order['order_id']} | <code>{order['user_id']}</code> | {order['plan']} روز | {order.get('payment_method') or 'manual'}")
                    buttons.append([InlineKeyboardButton(f"🧾 بررسی {order['order_id']}", callback_data=f"admin_order:{order['order_id']}")])
            buttons.append([InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin:menu")])
            await _show_callback_text(q, "\n".join(lines), reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
            return

        if action == "referrals":
            sources = db.referral_source_stats()
            with db._conn() as c:
                total = c.execute("SELECT COUNT(*) FROM referrals").fetchone()[0]
                pending = c.execute("SELECT COUNT(*) FROM referrals WHERE qualified = 0").fetchone()[0]
                flagged = c.execute("SELECT COUNT(*) FROM referrals WHERE flagged = 1 AND qualified = 0").fetchone()[0]
                rewards = c.execute("SELECT COUNT(*) FROM referral_rewards").fetchone()[0]
            lines = [
                "🎁 <b>آمار سیستم دعوت</b>", "",
                f"کل دعوت‌ها: <b>{total}</b>",
                f"معتبر: <b>{db.stats()['refs']}</b>",
                f"در اعتبارسنجی: <b>{pending}</b>",
                f"مشکوک: <b>{flagged}</b>",
                f"جوایز صادرشده: <b>{rewards}</b>", "", "منبع جذب:",
            ]
            for source, source_total, source_qualified in sources:
                label = REFERRAL_SOURCE_LABELS.get(source, source)
                lines.append(f"• {label}: {source_total} ورود / {source_qualified} معتبر")
            await _show_callback_text(q, "\n".join(lines), reply_markup=admin_menu(), parse_mode="HTML")
            return

        if action == "suspicious":
            items = db.suspicious_referrals(10)
            if not items:
                await _show_callback_text(q, "🚨 <b>دعوت‌های مشکوک</b>\n\nموردی برای بررسی وجود ندارد ✅", reply_markup=admin_menu(), parse_mode="HTML")
                return
            lines = ["🚨 <b>دعوت‌های مشکوک</b>", ""]
            rows = []
            for item in items:
                referred = int(item["referred_id"])
                referrer = int(item["referrer_id"])
                lines.append(f"• معرف <code>{referrer}</code> → کاربر <code>{referred}</code>\n  دلیل: {html.escape(item.get('flag_reason') or 'رفتار غیرعادی')}")
                rows.append([InlineKeyboardButton(f"✅ تأیید دستی {referred}", callback_data=f"admin_ref_approve:{referred}")])
            rows.append([InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin:menu")])
            await _show_callback_text(q, "\n".join(lines), reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML")
            return

        if action == "broadcast":
            context.user_data["flow"] = "broadcast"
            await _show_callback_text(q, "📣 متن پیام همگانی را بفرست.\nبرای لغو /cancel")
            return

        if action == "api":
            market, error = get_market_data()
            if not market:
                text = f"📡 <b>وضعیت API</b>\n\n❌ {html.escape(error or 'داده دریافت نشد')}"
            else:
                counts = {section: len(market.get(section, [])) if isinstance(market.get(section), list) else 0 for section in ("gold", "currency", "cryptocurrency")}
                text = (
                    "📡 <b>وضعیت API</b>\n\n✅ اتصال برقرار است\n"
                    f"طلا: {counts['gold']} آیتم\nارز: {counts['currency']} آیتم\nکریپتو: {counts['cryptocurrency']} آیتم\n"
                    f"Cache: {CACHE_TTL_SECONDS}s | History: هر {HISTORY_SAVE_INTERVAL // 60} دقیقه"
                )
            await _show_callback_text(q, text, reply_markup=admin_menu(), parse_mode="HTML")
            return

        if action == "database":
            try:
                size_mb = os.path.getsize(DB_PATH) / (1024 * 1024) if os.path.exists(DB_PATH) else 0
                with db._conn() as c:
                    quick = c.execute("PRAGMA quick_check").fetchone()[0]
                    history_count = c.execute("SELECT COUNT(*) FROM price_history").fetchone()[0]
                    user_count = c.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                text = (
                    "🗄 <b>وضعیت دیتابیس</b>\n\n"
                    f"SQLite: <b>{html.escape(str(quick))}</b>\n"
                    f"حجم: <b>{size_mb:.2f} MB</b>\n"
                    f"کاربران: <b>{user_count}</b>\n"
                    f"نمونه‌های قیمت: <b>{history_count}</b>\n"
                    f"Retention: <b>{HISTORY_RETENTION_DAYS} روز</b>"
                )
            except Exception as exc:
                text = f"🗄 خطای بررسی دیتابیس: {html.escape(type(exc).__name__)}"
            await _show_callback_text(q, text, reply_markup=admin_menu(), parse_mode="HTML")
            return

        if action == "backup":
            day = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")
            destination = os.path.join(BACKUP_DIR, day)
            os.makedirs(destination, exist_ok=True)
            backup_path = os.path.join(destination, "talayar_v3.db")
            try:
                with db._conn() as source, sqlite3.connect(backup_path) as target:
                    source.backup(target)
                db.set_state("last_backup", day)
                await _show_callback_text(q, f"✅ پشتیبان امن SQLite ساخته شد: <b>{day}</b>", reply_markup=admin_menu(), parse_mode="HTML")
            except Exception:
                logger.exception("Admin SQLite backup failed")
                await _show_callback_text(q, "❌ ساخت پشتیبان انجام نشد؛ Railway Logs را بررسی کن.", reply_markup=admin_menu())
            return

        if action == "system":
            license_ok, license_detail = license_status()
            uptime = int(time.monotonic() - STARTED_AT_MONO)
            hours, rem = divmod(uptime, 3600)
            minutes = rem // 60
            text = (
                "🧪 <b>سیستم / نسخه</b>\n\n"
                f"نسخه: <b>Talayar v{APP_VERSION}</b>\n"
                f"Build: <code>{BUILD_TAG}</code>\n"
                f"🔐 License: {'✅' if license_ok else '❌'} {html.escape(license_detail)}\n"
                f"⏱ Uptime: {hours}h {minutes}m\n"
                f"🖥 Host: <code>{html.escape(socket.gethostname()[:32])}</code>\n"
                f"🌐 Public URL: {'✅' if PUBLIC_BASE_URL else '➖ هنوز تنظیم نشده'}\n"
                f"💳 ZarinPal: {'✅' if zarinpal_enabled() else '➖ هنوز تنظیم نشده'}"
            )
            await _show_callback_text(q, text, reply_markup=admin_menu(), parse_mode="HTML")
            return

        await _show_callback_text(q, "گزینه مدیریتی نامعتبر است.", reply_markup=admin_menu())
        return

    await q.edit_message_text("گزینه نامعتبر است.", reply_markup=main_menu())

# ═══════════════════════════════════════════════════════════════
# JOBS
# ═══════════════════════════════════════════════════════════════
async def referral_qualification_job(context: ContextTypes.DEFAULT_TYPE):
    """دعوت‌هایی که تعامل کافی داشته‌اند ولی شرط سن ۹۰ ثانیه را بعداً کامل کرده‌اند، معطل نمی‌مانند."""
    now = datetime.now(timezone.utc)
    for ref in db.pending_referrals_for_review(100):
        started = _parse_iso(ref.get("started_at"))
        if not started or (now - started).total_seconds() < REFERRAL_MIN_AGE_SECONDS:
            continue
        if _referral_distinct_actions(ref.get("activity_mask")) < REFERRAL_MIN_DISTINCT_ACTIONS:
            continue
        try:
            await qualify_referral(int(ref["referred_id"]), context)
        except Exception:
            logger.exception("Referral qualification job failed for %s", ref.get("referred_id"))


async def check_smart_alerts(context: ContextTypes.DEFAULT_TYPE, market):
    now=int(time.time())
    alerts=db.load_smart_alerts()
    if not alerts:
        return
    feature_cache={}
    for a in alerts:
        uid=int(a.get("user_id") or 0)
        if not is_vip(uid):
            continue
        last=int(a.get("last_triggered") or 0)
        if now-last < SMART_ALERT_COOLDOWN_SECONDS:
            continue
        asset=a.get("asset_key")
        if asset not in feature_cache:
            feature_cache[asset]=_market_features(asset,market)
        f=feature_cache[asset]
        hit,detail=_smart_rule_trigger(a.get("rule"),f)
        if not hit:
            continue
        try:
            await context.bot.send_message(
                int(a["chat_id"]),
                f"🚨 <b>هشدار هوشمند طلایار</b>\n\n"
                f"{ALERT_ASSETS.get(asset,{}).get('label',asset)}\n"
                f"قانون: <b>{smart_rule_label(a.get('rule'))}</b>\n"
                f"{html.escape(detail)}\n"
                f"قیمت: <b>{_format_number(f.get('price'))}</b> {html.escape(str(f.get('unit') or ''))}\n\n"
                "برای جزئیات وارد مرکز نوسان شو.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚡ مرکز نوسان",callback_data="navasan")]])
            )
            db.touch_smart_alert(a["id"],now)
        except Exception:
            logger.exception("Smart alert send failed")


async def market_job(context: ContextTypes.DEFAULT_TYPE):
    market, error = get_market_data(force_refresh=True)
    if market is None:
        logger.warning("Alert check skipped: %s", error)
        return
    capture_history(market)
    await check_smart_alerts(context, market)

    alerts = db.load_alerts()
    if not alerts:
        return

    remaining, changed = [], False
    for alert in alerts:
        asset_key = alert.get("asset")
        item = find_alert_item(market, asset_key)
        if not item:
            remaining.append(alert)
            continue

        try:
            current_price = float(str(item.get("price")).replace(",", ""))
        except (TypeError, ValueError):
            remaining.append(alert)
            continue

        triggered = False
        detail = ""
        if alert.get("type") == "percent":
            baseline = float(alert.get("baseline", 0))
            target = float(alert.get("percent", 0))
            change = (current_price - baseline) / baseline * 100 if baseline else 0
            triggered = (alert.get("condition") == "up" and change >= target) or (alert.get("condition") == "down" and change <= -target)
            detail = f"تغییر: {change:+.2f}%"
        else:
            target = float(alert.get("target", 0))
            triggered = (alert.get("condition") == "above" and current_price >= target) or (alert.get("condition") == "below" and current_price <= target)
            detail = f"هدف: {_format_number(target)}"

        if not triggered:
            if alert.get("mode") == "repeat" and not alert.get("armed", True):
                alert["armed"] = True
                changed = True
            remaining.append(alert)
            continue

        if alert.get("mode") == "repeat" and not alert.get("armed", True):
            remaining.append(alert)
            continue

        try:
            await context.bot.send_message(alert["chat_id"],
                f"🔔 <b>هشدار طلایار</b>\n\n{ALERT_ASSETS[alert['asset']]['label']} به شرط رسید.\n"
                f"قیمت فعلی: <b>{_format_number(current_price)} {item.get('unit') or ''}</b>\n{detail}",
                parse_mode="HTML", reply_markup=main_menu())
            changed = True
            if alert.get("mode") == "repeat":
                if alert.get("type") == "percent":
                    alert["baseline"] = current_price
                else:
                    alert["armed"] = False
                remaining.append(alert)
        except Exception:
            logger.exception("Alert send failed")
            remaining.append(alert)

    if changed or len(remaining) != len(alerts):
        db.save_alerts(remaining)


async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    subs = db.load_daily_subs()
    now = datetime.now(TEHRAN_TZ)
    due = [s for s in subs if s.get("active") and s.get("time") == now.strftime("%H:%M") and s.get("last_sent") != now.strftime("%Y-%m-%d")]
    if not due:
        return
    market, _ = get_market_data()
    if not market:
        return
    report = build_daily_report(market)
    bot_username = await get_bot_username(context)
    for sub in due:
        if not is_vip(sub.get("user_id")):
            with db._conn() as c:
                c.execute("UPDATE daily_subs SET active = 0 WHERE user_id = ?", (sub["user_id"],))
            continue
        try:
            await context.bot.send_message(
                sub["chat_id"], report, parse_mode="HTML",
                reply_markup=share_report_menu(sub["user_id"], bot_username, market),
            )
            with db._conn() as c:
                c.execute("UPDATE daily_subs SET last_sent = ? WHERE user_id = ?",
                          (now.strftime("%Y-%m-%d"), sub["user_id"]))
        except Exception:
            logger.exception("Daily report failed")


async def vip_backup_job(context: ContextTypes.DEFAULT_TYPE):
    """چرخه تمدید VIP + بکاپ روزانه؛ بدون سرویس خارجی و مناسب Railway/ایران."""
    now_utc = datetime.now(timezone.utc)
    today = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")

    with db._conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("""
            SELECT v.*, u.chat_id
            FROM vip_users AS v
            LEFT JOIN users AS u ON u.user_id = v.user_id
        """).fetchall()

    for raw_row in rows:
        row = dict(raw_row)
        user_id = int(row["user_id"])
        expires = _parse_iso(row.get("expires_at"))
        if not expires:
            continue

        seconds_left = (expires - now_utc).total_seconds()
        source = str(row.get("source") or "")
        is_trial = source == "trial"
        stage = None
        text = None

        # برای Trial پیام ۳ روزه نمی‌فرستیم تا بلافاصله پس از /start مزاحم کاربر نشود.
        if 24 * 3600 < seconds_left <= 72 * 3600 and not is_trial:
            stage = "3d"
            text = "⏳ <b>۳ روز تا پایان VIP طلایار</b>\n\nبرای اینکه هشدارهای پیشرفته، گزارش روزانه، نمودارهای ۷/۳۰ روزه، بازار من و تحلیل هوشمند قطع نشوند، می‌توانی از الان تمدید کنی."
        elif 6 * 3600 < seconds_left <= 24 * 3600:
            stage = "1d"
            prefix = "VIP هدیه شما" if is_trial else "اشتراک VIP شما"
            text = f"⏰ <b>کمتر از ۱ روز باقی مانده</b>\n\n{prefix} به پایان نزدیک است. با تمدید، امکانات VIP بدون وقفه ادامه پیدا می‌کند."
        elif 0 < seconds_left <= 6 * 3600:
            stage = "6h"
            text = "⚠️ <b>کمتر از ۶ ساعت تا پایان VIP</b>\n\nاگر می‌خواهی هشدارها و امکانات حرفه‌ای بدون وقفه فعال بمانند، اشتراک را تمدید کن."
        elif -48 * 3600 <= seconds_left <= 0:
            stage = "expired"
            text = "🔒 <b>VIP طلایار به پایان رسید</b>\n\nحساب شما به حالت رایگان برگشت. قیمت لحظه‌ای و امکانات رایگان همچنان فعال‌اند و هر زمان بخواهی می‌توانی VIP را دوباره فعال کنی."

        if stage is not None:
            expiry_token = expires.strftime("%Y%m%d%H%M")
            reminder_key = f"{expiry_token}:{stage}"
            if row.get("last_reminder") != reminder_key:
                chat_id = int(row.get("chat_id") or user_id)
                try:
                    markup = vip_menu(user_id) if stage == "expired" else vip_renew_menu()
                    await context.bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=markup)
                    db.update_vip_reminder(user_id, reminder_key)
                    if stage == "expired":
                        with db._conn() as c:
                            c.execute("UPDATE daily_subs SET active = 0 WHERE user_id = ?", (user_id,))
                except Exception:
                    logger.exception("VIP reminder failed for user %s stage %s", user_id, stage)

    # بکاپ امن SQLite یک بار در روز؛ DB اصلی talayar_v3.db می‌ماند تا داده‌های قبلی حفظ شوند.
    last_backup = db.get_state("last_backup", "")
    if last_backup != today:
        destination = os.path.join(BACKUP_DIR, today)
        os.makedirs(destination, exist_ok=True)
        backup_path = os.path.join(destination, "talayar_v3.db")
        try:
            with db._conn() as source, sqlite3.connect(backup_path) as target:
                source.backup(target)
            db.set_state("last_backup", today)
        except Exception:
            logger.exception("SQLite daily backup failed")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.exception("Telegram update failed", exc_info=context.error)
    last_notice = db.get_state("last_error_notice", 0)
    now = int(time.time())
    if str(ADMIN_ID).isdigit() and now - int(last_notice) > 600:
        try:
            await context.bot.send_message(int(ADMIN_ID), "⚠️ یک خطای فنی در طلایار ثبت شد؛ جزئیات در Railway Logs است.")
            db.set_state("last_error_notice", now)
        except Exception:
            logger.exception("Admin error notification failed")


def ensure_pre_v13_snapshot():
    key="pre_v13_snapshot_done"
    if db.get_state(key,""): return
    try:
        stamp=datetime.now(TEHRAN_TZ).strftime("%Y%m%d-%H%M%S"); destination=os.path.join(BACKUP_DIR,f"pre-v13-{stamp}"); os.makedirs(destination,exist_ok=True); backup_path=os.path.join(destination,"talayar_v3.db")
        with db._conn() as source, sqlite3.connect(backup_path) as target: source.backup(target)
        db.set_state(key,backup_path); logger.info("Pre-v13 database snapshot created: %s", backup_path)
    except Exception:
        logger.exception("Pre-v13 snapshot failed; production DB was not reset")

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def run():
    validate_runtime_license()
    ensure_pre_v13_snapshot()

    if not BRS_API_URL:
        logger.warning("BRS_API_URL is missing; price buttons will show a configuration error")

    app = Application.builder().token(BOT_TOKEN).build()

    # ConversationHandler for Gold Calculator
    gold_conv = ConversationHandler(
        entry_points=[
            CommandHandler("calculator", gold_calc_entry),
            CallbackQueryHandler(gold_calc_entry, pattern=r"^calculator$"),
        ],
        states={
            WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, gc_weight)],
            LIVE_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, gc_live_price)],
            WAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, gc_wage)],
            PROFIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, gc_profit)],
            TAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, gc_tax)],
        },
        fallbacks=[CommandHandler("cancel", gc_cancel)],
        allow_reentry=True,
    )

    app.add_handler(CommandHandler("start", start_v2))
    app.add_handler(CommandHandler("help", help_command_v2))
    app.add_handler(CommandHandler("gold", gold_command_v2))
    app.add_handler(CommandHandler("price", price_command_v2))
    app.add_handler(CommandHandler("version", version_command_v2))
    app.add_handler(gold_conv)
    app.add_handler(CommandHandler("cancel", cancel_v2))
    app.add_handler(CommandHandler("myid", my_id))
    app.add_handler(CommandHandler("vip", vip_command_v2))
    app.add_handler(CommandHandler("admin", admin_v2))
    app.add_handler(CommandHandler("addvip", add_vip_v2))
    app.add_handler(CommandHandler("removevip", remove_vip_v2))
    app.add_handler(CommandHandler("userinfo", userinfo_v2))
    app.add_handler(CallbackQueryHandler(buttons_v2))
    app.add_handler(MessageHandler(filters.PHOTO, receive_photo_v2))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text_v2))
    app.add_error_handler(error_handler)

    payment_server = start_payment_callback_server()

    if app.job_queue is None:
        raise RuntimeError("JobQueue is unavailable. Install python-telegram-bot[job-queue].")
    app.job_queue.run_repeating(market_job, interval=ALERT_CHECK_INTERVAL, first=20, name="market-job")
    app.job_queue.run_repeating(referral_qualification_job, interval=300, first=180, name="referral-qualification")
    app.job_queue.run_repeating(daily_job, interval=30, first=10, name="daily-reports")
    app.job_queue.run_repeating(vip_backup_job, interval=VIP_MAINTENANCE_INTERVAL, first=60, name="vip-maintenance")
    try:
        app.run_polling()
    finally:
        if payment_server is not None:
            payment_server.shutdown()


if __name__ == "__main__":
    run()
