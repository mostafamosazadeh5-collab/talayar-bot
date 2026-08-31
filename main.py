#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
طلایار v14.0.2 Audit Patched + Signal Engine — دستیار هوشمند بازار طلا، ارز و کریپتو
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
  ✅ وب‌سایت رسمی talayarbot.ir + قوانین و حریم خصوصی
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
  ✅ موتور فرصت‌های واقعی کریپتو با OHLCV واقعی + کیفیت داده + پیگیری TP/SL
  ✅ Replay سیگنال‌های باز پس از Restart + وضعیت مبهم بدون حدس ترتیب حرکت
  ✅ کریپتوهای شخصی: رایگان ۳ ارز، VIP تا ۱۰ ارز
  ✅ متاتگ احراز اینماد + FAQ + فرهنگ اصطلاحات + صفحات اعتماد سایت
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
APP_VERSION = "14.0.6"
BUILD_TAG = "BOOT-ISOLATED-FAST-SESSION-CACHE-FIRST"
DEVELOPER_NAME = os.environ.get("DEVELOPER_NAME", "مصطفی موسی‌زاده").strip()
DEVELOPER_USERNAME = os.environ.get("DEVELOPER_USERNAME", "WAHL4").strip().lstrip("@")
BOT_PUBLIC_USERNAME = os.environ.get("BOT_PUBLIC_USERNAME", "").strip().lstrip("@")
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
BRS_RETRY_ATTEMPTS = max(1, min(5, int(os.environ.get("BRS_RETRY_ATTEMPTS", "3"))))
BRS_RETRY_BASE_DELAY = max(0.1, min(3.0, float(os.environ.get("BRS_RETRY_BASE_DELAY", "0.4"))))
BRS_CIRCUIT_FAILURES = max(2, min(10, int(os.environ.get("BRS_CIRCUIT_FAILURES", "3"))))
BRS_CIRCUIT_SECONDS = max(10, min(300, int(os.environ.get("BRS_CIRCUIT_SECONDS", "30"))))
CACHE_TTL_SECONDS = int(os.environ.get("CACHE_TTL_SECONDS", "12"))
CACHE_STALE_MAX_SECONDS = int(os.environ.get("CACHE_STALE_MAX_SECONDS", "180"))
CACHE_PERSISTENT_STALE_MAX_SECONDS = int(os.environ.get("CACHE_PERSISTENT_STALE_MAX_SECONDS", "900"))
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
# v14 Real-data crypto signal engine
CRYPTO_FREE_LIMIT = int(os.environ.get("CRYPTO_FREE_LIMIT", "3"))
CRYPTO_VIP_LIMIT = int(os.environ.get("CRYPTO_VIP_LIMIT", "10"))
SIGNAL_ENGINE_ENABLED = os.environ.get("SIGNAL_ENGINE_ENABLED", "1").strip().lower() not in {"0","false","off","no"}
SIGNAL_SCAN_INTERVAL = max(60, int(os.environ.get("SIGNAL_SCAN_INTERVAL", "300")))
SIGNAL_TRACK_INTERVAL = max(60, int(os.environ.get("SIGNAL_TRACK_INTERVAL", "60")))
SIGNAL_MIN_DATA_QUALITY = max(70, min(100, int(os.environ.get("SIGNAL_MIN_DATA_QUALITY", "90"))))
SIGNAL_MIN_SCORE = max(60, min(95, int(os.environ.get("SIGNAL_MIN_SCORE", "78"))))
SIGNAL_DUPLICATE_COOLDOWN = max(1800, int(os.environ.get("SIGNAL_DUPLICATE_COOLDOWN", "14400")))
SIGNAL_MOVE_TO_BE_AFTER_TP1 = os.environ.get("SIGNAL_MOVE_TO_BE_AFTER_TP1", "1").strip().lower() not in {"0","false","off","no"}
SIGNAL_REPLAY_MAX_MINUTES = max(240, min(20160, int(os.environ.get("SIGNAL_REPLAY_MAX_MINUTES", "10080"))))
BINANCE_API_BASE = os.environ.get("BINANCE_API_BASE", "https://api.binance.com").rstrip("/")
BINANCE_DATA_BASE = os.environ.get("BINANCE_DATA_BASE", "https://data-api.binance.vision").rstrip("/")
COINBASE_API_BASE = os.environ.get("COINBASE_API_BASE", "https://api.coinbase.com").rstrip("/")
CRYPTO_TICKER_CACHE_SECONDS = max(3, int(os.environ.get("CRYPTO_TICKER_CACHE_SECONDS", "8")))
CRYPTO_KLINE_CACHE_SECONDS = max(10, int(os.environ.get("CRYPTO_KLINE_CACHE_SECONDS", "30")))
TROY_OUNCE_GRAMS = 31.1034768
COIN_SPECS = {
    # gross grams * fineness; standard Iranian gold coin specs
    "emami": {"label": "سکه امامی", "gross_g": 8.133, "fineness": 0.900},
    "half": {"label": "نیم‌سکه", "gross_g": 4.0665, "fineness": 0.900},
    "quarter": {"label": "ربع‌سکه", "gross_g": 2.03325, "fineness": 0.900},
}
VIP_MAINTENANCE_INTERVAL = 10800  # هر ۳ ساعت: یادآوری VIP + پشتیبان روزانه
WATCHLIST_VIP_LIMIT = 5
PORTFOLIO_FREE_LIMIT = 2
PORTFOLIO_VIP_LIMIT = 10
TEHRAN_TZ = ZoneInfo("Asia/Tehran")
VIP_PRICE_30 = (os.environ.get("VIP_PRICE_30", "700,000").strip() or "700,000")
VIP_PRICE_90 = (os.environ.get("VIP_PRICE_90", "1,900,000").strip() or "1,900,000")
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

_market_cache = {"data": None, "saved_at": 0.0, "fetched_at": 0, "last_error": "", "persisted_at": 0}
_market_refresh_lock = threading.Lock()
_brs_session = requests.Session()
_brs_failure_count = 0
_brs_circuit_until = 0.0
_brs_background_guard = threading.Lock()
_brs_background_running = False
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
                CREATE TABLE IF NOT EXISTS activity_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    asset_key TEXT DEFAULT '',
                    title TEXT DEFAULT '',
                    detail TEXT DEFAULT '',
                    price REAL,
                    meta_json TEXT DEFAULT '{}',
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS miniapp_preferences (
                    user_id INTEGER PRIMARY KEY,
                    prefs_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS portfolio_positions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    asset_key TEXT NOT NULL,
                    quantity REAL NOT NULL,
                    avg_buy_price REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(user_id, asset_key)
                );
                CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    snapshot_date TEXT NOT NULL,
                    market_value REAL NOT NULL,
                    cost_value REAL NOT NULL,
                    pnl_value REAL NOT NULL,
                    created_at TEXT NOT NULL,
                    UNIQUE(user_id, snapshot_date)
                );
            """)
            c.executescript("""
                CREATE TABLE IF NOT EXISTS crypto_watchlist (
                    user_id INTEGER NOT NULL,
                    asset_key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, asset_key)
                );
                CREATE TABLE IF NOT EXISTS market_signals (
                    signal_id TEXT PRIMARY KEY,
                    asset_key TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    side TEXT NOT NULL,
                    timeframe TEXT NOT NULL,
                    issued_price REAL NOT NULL,
                    entry_low REAL NOT NULL,
                    entry_high REAL NOT NULL,
                    stop_loss REAL NOT NULL,
                    tp1 REAL NOT NULL,
                    tp2 REAL NOT NULL,
                    tp3 REAL NOT NULL,
                    score INTEGER NOT NULL,
                    data_quality INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    reasons_json TEXT NOT NULL DEFAULT '[]',
                    metrics_json TEXT NOT NULL DEFAULT '{}',
                    status TEXT NOT NULL DEFAULT 'open',
                    hit_level INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    closed_at TEXT DEFAULT '',
                    last_checked_at TEXT DEFAULT ''
                );
                CREATE TABLE IF NOT EXISTS signal_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    signal_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    price REAL,
                    event_at TEXT NOT NULL,
                    detail TEXT DEFAULT '',
                    UNIQUE(signal_id, event_type)
                );
                CREATE INDEX IF NOT EXISTS idx_crypto_watchlist_user ON crypto_watchlist(user_id, created_at);
                CREATE INDEX IF NOT EXISTS idx_signals_asset_created ON market_signals(asset_key, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_signals_status ON market_signals(status, created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_signal_events_signal ON signal_events(signal_id, id);
            """)

            self._ensure_column(c, "market_signals", "active_stop", "REAL")
            self._ensure_column(c, "market_signals", "breakeven_armed", "INTEGER DEFAULT 0")
            self._ensure_column(c, "market_signals", "last_event_at", "TEXT DEFAULT ''")
            c.execute("UPDATE market_signals SET active_stop = stop_loss WHERE active_stop IS NULL")
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
            c.execute("CREATE INDEX IF NOT EXISTS idx_activity_history_user_created ON activity_history(user_id, created_at DESC)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_user ON portfolio_positions(user_id)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_portfolio_snapshot_user_date ON portfolio_snapshots(user_id, snapshot_date DESC)")
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


    def portfolio_positions(self, user_id):
        with self._conn() as c:
            c.row_factory=sqlite3.Row
            rows=c.execute("SELECT * FROM portfolio_positions WHERE user_id=? ORDER BY id",(int(user_id),)).fetchall()
            return [dict(r) for r in rows]

    def upsert_portfolio_position(self,user_id,asset_key,quantity,avg_buy_price):
        now=_utc_now()
        with self._conn() as c:
            c.execute("""
                INSERT INTO portfolio_positions(user_id,asset_key,quantity,avg_buy_price,created_at,updated_at)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(user_id,asset_key) DO UPDATE SET
                    quantity=excluded.quantity,avg_buy_price=excluded.avg_buy_price,updated_at=excluded.updated_at
            """,(int(user_id),str(asset_key),float(quantity),float(avg_buy_price),now,now))

    def remove_portfolio_position(self,user_id,asset_key):
        with self._conn() as c:
            cur=c.execute("DELETE FROM portfolio_positions WHERE user_id=? AND asset_key=?",(int(user_id),str(asset_key)))
            return cur.rowcount>0

    def portfolio_user_ids(self):
        with self._conn() as c:
            return [int(r[0]) for r in c.execute("SELECT DISTINCT user_id FROM portfolio_positions").fetchall()]

    def save_portfolio_snapshot_once(self,user_id,snapshot_date,market_value,cost_value,pnl_value):
        with self._conn() as c:
            cur=c.execute("""
                INSERT OR IGNORE INTO portfolio_snapshots(user_id,snapshot_date,market_value,cost_value,pnl_value,created_at)
                VALUES(?,?,?,?,?,?)
            """,(int(user_id),str(snapshot_date),float(market_value),float(cost_value),float(pnl_value),_utc_now()))
            return cur.rowcount>0

    def previous_portfolio_snapshot(self,user_id,before_date):
        with self._conn() as c:
            c.row_factory=sqlite3.Row
            row=c.execute("""
                SELECT * FROM portfolio_snapshots
                WHERE user_id=? AND snapshot_date<? ORDER BY snapshot_date DESC LIMIT 1
            """,(int(user_id),str(before_date))).fetchone()
            return dict(row) if row else None

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

    def add_activity(self, user_id, event_type, asset_key="", title="", detail="", price=None, meta=None):
        with self._conn() as c:
            c.execute(
                "INSERT INTO activity_history (user_id,event_type,asset_key,title,detail,price,meta_json,created_at) VALUES (?,?,?,?,?,?,?,?)",
                (int(user_id), str(event_type)[:40], str(asset_key or "")[:40], str(title or "")[:160],
                 str(detail or "")[:1000], float(price) if price is not None else None,
                 json.dumps(meta or {}, ensure_ascii=False, separators=(",",":")), _utc_now())
            )

    def get_activity(self, user_id, limit=80):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute(
                "SELECT * FROM activity_history WHERE user_id=? ORDER BY id DESC LIMIT ?",
                (int(user_id), max(1, min(int(limit), 200)))
            ).fetchall()
            out=[]
            for r in rows:
                d=dict(r)
                try: d["meta"]=json.loads(d.pop("meta_json") or "{}")
                except Exception: d["meta"]={}
                out.append(d)
            return out

    def get_state(self, key, default=None):
        with self._conn() as c:
            row = c.execute("SELECT value FROM bot_state WHERE key = ?", (key,)).fetchone()
            return json.loads(row[0]) if row else default

    def set_state(self, key, value):
        import json
        with self._conn() as c:
            c.execute("INSERT INTO bot_state (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                      (key, json.dumps(value, ensure_ascii=False)))

    def get_miniapp_preferences(self, user_id):
        defaults = {
            "theme": "light", "home": "pulse", "compact": False,
            "pinned": ["gold18", "melted", "usd", "ounce", "btc"],
            "show_rsi": True, "show_ema": True, "show_levels": True,
            "default_timeframe": "24H"
        }
        with self._conn() as c:
            row = c.execute("SELECT prefs_json FROM miniapp_preferences WHERE user_id = ?", (int(user_id),)).fetchone()
        if row:
            try:
                saved = json.loads(row[0] or "{}")
                if isinstance(saved, dict):
                    defaults.update(saved)
            except Exception:
                pass
        return defaults

    def set_miniapp_preferences(self, user_id, prefs):
        allowed_theme = str(prefs.get("theme") or "dark")
        if allowed_theme not in {"dark", "light"}: allowed_theme = "dark"
        home = str(prefs.get("home") or "pulse")
        if home not in {"pulse", "heatmap", "my_market"}: home = "pulse"
        tf = str(prefs.get("default_timeframe") or "24H").upper()
        if tf not in {"1H", "4H", "24H", "1D", "7D", "30D"}: tf = "24H"
        pinned = []
        for key in list(prefs.get("pinned") or []):
            key = str(key)
            if key in ALERT_ASSETS and key not in pinned:
                pinned.append(key)
            if len(pinned) >= 12: break
        clean = {
            "theme": allowed_theme, "home": home, "compact": bool(prefs.get("compact", False)),
            "pinned": pinned, "show_rsi": bool(prefs.get("show_rsi", True)),
            "show_ema": bool(prefs.get("show_ema", True)), "show_levels": bool(prefs.get("show_levels", True)),
            "default_timeframe": tf
        }
        now = datetime.now(timezone.utc).isoformat()
        with self._conn() as c:
            c.execute("INSERT INTO miniapp_preferences (user_id,prefs_json,updated_at) VALUES (?,?,?) ON CONFLICT(user_id) DO UPDATE SET prefs_json=excluded.prefs_json,updated_at=excluded.updated_at",
                      (int(user_id), json.dumps(clean, ensure_ascii=False), now))
        return clean

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

def _db_persistence_hint():
    """Best-effort operational hint; does not expose secrets or block startup."""
    if os.path.abspath(DATA_DIR) == os.path.abspath("/data"):
        return "persistent-path:/data"
    if os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("RAILWAY_PROJECT_ID"):
        return "WARNING: SQLite is not under /data; attach a Railway Volume at /data or set DATA_DIR to a persistent mount."
    return f"local-path:{os.path.abspath(DATA_DIR)}"

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
# v14 REAL CRYPTO DATA + SIGNAL ENGINE
# No synthetic market prices are generated in this layer. If an upstream
# market feed is unavailable or stale, the API returns unavailable/no-signal.
# ═══════════════════════════════════════════════════════════════
SUPPORTED_CRYPTO = {
    "btc": {"label":"بیت‌کوین","base":"BTC","symbol":"BTCUSDT","coinbase":"BTC-USD"},
    "eth": {"label":"اتریوم","base":"ETH","symbol":"ETHUSDT","coinbase":"ETH-USD"},
    "bnb": {"label":"BNB","base":"BNB","symbol":"BNBUSDT","coinbase":""},
    "sol": {"label":"سولانا","base":"SOL","symbol":"SOLUSDT","coinbase":"SOL-USD"},
    "xrp": {"label":"XRP","base":"XRP","symbol":"XRPUSDT","coinbase":"XRP-USD"},
    "doge": {"label":"دوج‌کوین","base":"DOGE","symbol":"DOGEUSDT","coinbase":"DOGE-USD"},
    "ada": {"label":"کاردانو","base":"ADA","symbol":"ADAUSDT","coinbase":"ADA-USD"},
    "trx": {"label":"ترون","base":"TRX","symbol":"TRXUSDT","coinbase":""},
    "avax": {"label":"آوالانچ","base":"AVAX","symbol":"AVAXUSDT","coinbase":"AVAX-USD"},
    "link": {"label":"چین‌لینک","base":"LINK","symbol":"LINKUSDT","coinbase":"LINK-USD"},
    "dot": {"label":"پولکادات","base":"DOT","symbol":"DOTUSDT","coinbase":"DOT-USD"},
    "ltc": {"label":"لایت‌کوین","base":"LTC","symbol":"LTCUSDT","coinbase":"LTC-USD"},
}
DEFAULT_CRYPTO_KEYS = ("btc","eth","bnb","sol","xrp","doge","ada","trx","avax","link")
GLOSSARY = {
    "rsi": ("قدرت حرکت (RSI)", "شاخصی بین ۰ تا ۱۰۰ برای سنجش قدرت حرکت قیمت. عدد بالا یعنی بازار داغ‌تر و عدد پایین یعنی فشار فروش بیشتر؛ به‌تنهایی دستور خرید یا فروش نیست."),
    "ema": ("جهت روند (EMA)", "میانگین متحرکی که به قیمت‌های جدید وزن بیشتری می‌دهد. مقایسه EMAهای کوتاه و بلند به طلایار کمک می‌کند جهت روند را بسنجد."),
    "macd": ("شتاب روند (MACD)", "ابزاری برای بررسی قدرت و جهت حرکت. طلایار آن را همراه چند معیار دیگر استفاده می‌کند، نه به‌تنهایی."),
    "support": ("حمایت", "محدوده‌ای که قبلاً خریداران در آن فعال‌تر شده‌اند. حمایت تضمینی نیست و ممکن است شکسته شود."),
    "resistance": ("مقاومت", "محدوده‌ای که قبلاً فشار فروش بیشتر شده است. عبور از مقاومت فقط وقتی مهم است که با داده‌های دیگر تأیید شود."),
    "breakout": ("شکست محدوده", "عبور قیمت از یک سقف یا کف مهم. طلایار برای معتبر دانستن شکست، روند، حجم و تایم‌فریم‌های دیگر را هم بررسی می‌کند."),
    "volume": ("حجم معاملات", "مقدار معامله‌شده در یک بازه. افزایش حجم می‌تواند قدرت یک حرکت را تأیید کند."),
    "atr": ("میزان نوسان (ATR)", "معیاری بر پایه سقف، کف و قیمت بسته‌شدن کندل‌ها برای سنجش نوسان. در کریپتو از OHLC واقعی بازار محاسبه می‌شود."),
    "sl": ("حد ضرر", "قیمتی که با رسیدن بازار به آن، سناریوی معامله نامعتبر می‌شود و برای محدودکردن زیان در نظر گرفته می‌شود."),
    "tp": ("هدف قیمت", "هدف‌های مرحله‌ای سناریو؛ طلایار هدف اول، دوم و سوم را جدا ثبت می‌کند."),
    "rr": ("نسبت سود به زیان", "نشان می‌دهد سود بالقوه نسبت به ریسک اولیه چقدر است. این نسبت تضمین رسیدن قیمت به هدف نیست."),
    "quality": ("کیفیت داده", "امتیاز تازگی و سلامت داده بازار، کامل‌بودن کندل‌های واقعی و در صورت امکان تطبیق با منبع دوم. داده ضعیف اجازه صدور سیگنال نمی‌دهد."),
    "score": ("قدرت فرصت", "امتیاز هم‌جهتی چند عامل مثل روند، قدرت حرکت، حجم، شکست محدوده و چند تایم‌فریم. این امتیاز احتمال موفقیت قطعی نیست."),
}
FAQ_ITEMS = [
    ("چطور از طلایار استفاده کنم؟", "ربات را در تلگرام باز کنید و /start را بزنید. قیمت‌ها، نمودارها، هشدارها، مینی‌اپ، بازار شخصی و ابزارهای تحلیلی از منوی اصلی در دسترس‌اند."),
    ("نسخه رایگان چه محدودیتی دارد؟", "نسخه رایگان ابزارهای پایه را دارد. قابلیت‌های حرفه‌ای، تعداد بیشتر دارایی شخصی، سیگنال و بعضی تایم‌فریم‌ها برای VIP فعال می‌شوند."),
    ("قیمت‌ها و سیگنال‌ها واقعی‌اند؟", "v14 در بخش کریپتو قیمت و OHLCV را از API عمومی بازار دریافت می‌کند و عدد قیمت ساختگی تولید نمی‌کند. اگر داده معتبر یا تازه نباشد، طلایار به‌جای ساختن عدد، فقط وضعیت بازار را نشان می‌دهد. هیچ سیگنالی تضمین سود ۱۰۰٪ ندارد."),
    ("پرداخت چگونه انجام می‌شود؟", "در صورت فعال‌بودن زرین‌پال، سفارش از داخل ربات ساخته و فقط بعد از Verify موفق درگاه، VIP فعال می‌شود. روش رسید دستی نیز به‌عنوان مسیر جایگزین باقی مانده است."),
    ("چند ارز کریپتو می‌توانم انتخاب کنم؟", f"کاربر رایگان تا {CRYPTO_FREE_LIMIT} ارز و VIP تا {CRYPTO_VIP_LIMIT} ارز از فهرست پشتیبانی‌شده می‌تواند به بازار کریپتوی شخصی اضافه کند."),
    ("سیگنال چگونه ساخته می‌شود؟", "موتور سیگنال از OHLCV واقعی، EMA، RSI، MACD، ATR، حجم، ساختار حمایت/مقاومت و تأیید چند تایم‌فریم استفاده می‌کند. زیر حد کیفیت داده، فرصت معاملاتی صادر نمی‌شود و وضعیت «داده برای تصمیم کافی نیست» نمایش داده می‌شود."),
]

_crypto_ticker_cache = {"at":0.0,"data":{},"error":""}
_crypto_kline_cache = {}
_coinbase_cache = {}
_crypto_lock = threading.Lock()
_crypto_ticker_fetch_lock = threading.Lock()
_signal_snapshot_cache = {}
_signal_snapshot_lock = threading.Lock()
_signal_background_keys = set()
_signal_background_guard = threading.Lock()
_signal_background_slots = threading.Semaphore(2)


def crypto_limit(user_id):
    return CRYPTO_VIP_LIMIT if is_vip(user_id) else CRYPTO_FREE_LIMIT


def crypto_watchlist(user_id):
    with db._conn() as c:
        rows=c.execute("SELECT asset_key FROM crypto_watchlist WHERE user_id=? ORDER BY created_at",(int(user_id),)).fetchall()
    return [r[0] for r in rows if r and r[0] in SUPPORTED_CRYPTO]


def crypto_watchlist_add(user_id, asset_key):
    asset_key=str(asset_key or "").lower()
    if asset_key not in SUPPORTED_CRYPTO: return "invalid"
    existing=crypto_watchlist(user_id)
    if asset_key in existing: return "exists"
    if len(existing)>=crypto_limit(user_id): return "limit"
    with db._conn() as c:
        c.execute("INSERT OR IGNORE INTO crypto_watchlist(user_id,asset_key,created_at) VALUES(?,?,?)",(int(user_id),asset_key,_utc_now()))
    return "added"


def crypto_watchlist_remove(user_id, asset_key):
    with db._conn() as c:
        cur=c.execute("DELETE FROM crypto_watchlist WHERE user_id=? AND asset_key=?",(int(user_id),str(asset_key)))
    return cur.rowcount>0


def _market_get(path, params=None, timeout=10):
    last=None
    for base in (BINANCE_API_BASE, BINANCE_DATA_BASE):
        try:
            r=requests.get(base+path,params=params,timeout=timeout,headers={"Accept":"application/json","User-Agent":f"TalayarBot/{APP_VERSION}"})
            r.raise_for_status(); return r.json(), base
        except Exception as exc:
            last=exc
    raise requests.RequestException(f"market feed unavailable: {type(last).__name__ if last else 'unknown'}")


def _crypto_tickers_cached_only(max_age_seconds=60):
    """Read ticker cache without touching Binance; used by the fast bootstrap."""
    now=time.monotonic()
    with _crypto_lock:
        cached=dict(_crypto_ticker_cache.get("data") or {})
        at=float(_crypto_ticker_cache.get("at") or 0.0)
        source=_crypto_ticker_cache.get("source","cache")
    if not cached or not at or now-at>max(0,int(max_age_seconds)):
        return {},source
    return cached,source


def _crypto_tickers(force=False):
    now=time.monotonic()
    with _crypto_lock:
        if not force and _crypto_ticker_cache["data"] and now-_crypto_ticker_cache["at"]<=CRYPTO_TICKER_CACHE_SECONDS:
            return _crypto_ticker_cache["data"], _crypto_ticker_cache.get("source","cache"), _crypto_ticker_cache.get("error","")
    with _crypto_ticker_fetch_lock:
        now=time.monotonic()
        with _crypto_lock:
            # Another thread may have refreshed while we waited.
            if not force and _crypto_ticker_cache["data"] and now-_crypto_ticker_cache["at"]<=CRYPTO_TICKER_CACHE_SECONDS:
                return _crypto_ticker_cache["data"], _crypto_ticker_cache.get("source","cache"), _crypto_ticker_cache.get("error","")
        symbols=[x["symbol"] for x in SUPPORTED_CRYPTO.values()]
        try:
            raw,source=_market_get("/api/v3/ticker/24hr",params={"symbols":json.dumps(symbols,separators=(",",":")),"type":"FULL"})
            if isinstance(raw,dict): raw=[raw]
            by_symbol={str(x.get("symbol")):x for x in (raw or []) if isinstance(x,dict)}
            data={}
            for key,spec in SUPPORTED_CRYPTO.items():
                row=by_symbol.get(spec["symbol"])
                if not row: continue
                try:
                    close_time=int(row.get("closeTime") or int(time.time()*1000))
                    data[key]={"key":key,"label":spec["label"],"symbol":spec["symbol"],"price":float(row["lastPrice"]),
                               "change":float(row.get("priceChangePercent") or 0),"high":float(row.get("highPrice") or 0),
                               "low":float(row.get("lowPrice") or 0),"volume":float(row.get("volume") or 0),
                               "quote_volume":float(row.get("quoteVolume") or 0),"bid":float(row.get("bidPrice") or 0),
                               "ask":float(row.get("askPrice") or 0),"close_time":close_time,"unit":"USDT","source":"Binance public market data"}
                except (TypeError,ValueError,KeyError):
                    continue
            if not data: raise ValueError("empty market payload")
            with _crypto_lock:
                _crypto_ticker_cache.update({"at":now,"data":data,"source":source,"error":""})
            return data,source,""
        except Exception as exc:
            with _crypto_lock:
                cached=dict(_crypto_ticker_cache.get("data") or {}); age=now-_crypto_ticker_cache.get("at",0)
            if cached and age<=60:
                return cached,_crypto_ticker_cache.get("source","cache"),f"stale-cache:{type(exc).__name__}"
            return {},"",f"{type(exc).__name__}: market feed unavailable"

def _crypto_klines(asset_key, interval="1h", limit=240, force=False):
    spec=SUPPORTED_CRYPTO.get(str(asset_key))
    if not spec: return [],"invalid_asset"
    limit=max(50,min(int(limit),1000)); ck=(asset_key,interval,limit); now=time.monotonic()
    with _crypto_lock:
        old=_crypto_kline_cache.get(ck)
        if old and not force and now-old[0]<=CRYPTO_KLINE_CACHE_SECONDS:
            return old[1],"cache"
    try:
        raw,source=_market_get("/api/v3/klines",params={"symbol":spec["symbol"],"interval":interval,"limit":limit},timeout=12)
        rows=[]
        for x in raw or []:
            try:
                rows.append({"open_time":int(x[0]),"o":float(x[1]),"h":float(x[2]),"l":float(x[3]),"c":float(x[4]),
                             "v":float(x[5]),"close_time":int(x[6]),"quote_v":float(x[7]),"trades":int(x[8])})
            except (TypeError,ValueError,IndexError): continue
        if len(rows)<20: return [],"insufficient_klines"
        with _crypto_lock: _crypto_kline_cache[ck]=(now,rows,source)
        return rows,source
    except Exception as exc:
        with _crypto_lock: old=_crypto_kline_cache.get(ck)
        if old and now-old[0]<=180: return old[1],"stale-cache"
        return [],f"{type(exc).__name__}: kline unavailable"


def _crypto_klines_since(asset_key, start_ms, end_ms=None, max_points=None):
    """Fetch real 1m OHLCV from the last processed instant forward.

    Pagination deliberately uses exchange timestamps so Railway restarts do not
    create silent TP/SL gaps. If the outage is longer than one replay batch, the
    next tracker run continues from the last processed candle.
    """
    spec=SUPPORTED_CRYPTO.get(str(asset_key))
    if not spec:
        return [],"invalid_asset",False
    now_ms=int(time.time()*1000); end_ms=min(int(end_ms or now_ms),now_ms)
    cursor=max(0,int(start_ms)); max_points=max(60,min(int(max_points or SIGNAL_REPLAY_MAX_MINUTES),SIGNAL_REPLAY_MAX_MINUTES))
    rows=[]; source=""; pages=0; max_pages=max(1,(max_points+999)//1000)
    try:
        while cursor<=end_ms and len(rows)<max_points and pages<max_pages:
            limit=min(1000,max_points-len(rows))
            raw,source=_market_get("/api/v3/klines",params={"symbol":spec["symbol"],"interval":"1m","startTime":cursor,"endTime":end_ms,"limit":limit},timeout=12)
            parsed=[]
            for x in raw or []:
                try:
                    parsed.append({"open_time":int(x[0]),"o":float(x[1]),"h":float(x[2]),"l":float(x[3]),"c":float(x[4]),"v":float(x[5]),"close_time":int(x[6]),"quote_v":float(x[7]),"trades":int(x[8])})
                except (TypeError,ValueError,IndexError):
                    continue
            if not parsed:
                break
            rows.extend(parsed); pages+=1
            nxt=int(parsed[-1]["open_time"])+60000
            if nxt<=cursor:
                break
            cursor=nxt
            if len(parsed)<limit:
                break
        dedup={int(r["open_time"]):r for r in rows}
        out=[dedup[k] for k in sorted(dedup)]
        truncated=bool(out and int(out[-1]["close_time"])<end_ms-120000 and len(out)>=max_points)
        return out,source,truncated
    except Exception as exc:
        return [],f"{type(exc).__name__}: replay unavailable",False


def _coinbase_spot(asset_key):
    spec=SUPPORTED_CRYPTO.get(asset_key) or {}; product=spec.get("coinbase")
    if not product: return None,"not_supported"
    now=time.monotonic(); old=_coinbase_cache.get(asset_key)
    if old and now-old[0]<=30: return old[1],"cache"
    try:
        r=requests.get(f"{COINBASE_API_BASE}/v2/prices/{product}/spot",timeout=7,headers={"Accept":"application/json","User-Agent":f"TalayarBot/{APP_VERSION}"})
        r.raise_for_status(); p=float((r.json().get("data") or {}).get("amount")); _coinbase_cache[asset_key]=(now,p); return p,"Coinbase spot"
    except Exception: return None,"unavailable"


def _true_atr(rows, period=14):
    if len(rows)<period+2: return None
    trs=[]
    for i in range(1,len(rows)):
        h,l,pc=rows[i]["h"],rows[i]["l"],rows[i-1]["c"]
        trs.append(max(h-l,abs(h-pc),abs(l-pc)))
    vals=trs[-period:]
    return sum(vals)/len(vals) if vals else None


def _crypto_data_quality(asset_key, ticker, rows, cross_price=None):
    q=100; reasons=[]; now_ms=int(time.time()*1000)
    age=max(0,(now_ms-int(ticker.get("close_time") or now_ms))/1000)
    if age>60:
        q-=45; reasons.append("ticker_stale")
    elif age>20:
        q-=25; reasons.append("ticker_delayed")
    if len(rows)<120:
        q-=25; reasons.append("few_candles")
    if rows:
        cage=max(0,(now_ms-int(rows[-1].get("close_time") or now_ms))/1000)
        if cage>7200:
            q-=35; reasons.append("candle_stale")
        gaps=0
        pairs=list(zip(rows[-120:-1],rows[-119:])) if len(rows)>=2 else []
        for a,b in pairs:
            try:
                if int(b["open_time"])-int(a["open_time"]) > 5400000:
                    gaps+=1
            except Exception:
                gaps+=1
        if gaps:
            q-=min(30,10*gaps); reasons.append(f"candle_gaps_{gaps}")
    bid=float(ticker.get("bid") or 0); ask=float(ticker.get("ask") or 0); price=float(ticker.get("price") or 0)
    if not bid or not ask or ask<bid:
        q-=12; reasons.append("orderbook_invalid")
    elif price>0:
        spread=(ask-bid)/price*100
        if spread>0.50:
            q-=20; reasons.append(f"wide_spread_{spread:.3f}")
        elif spread>0.20:
            q-=8; reasons.append(f"spread_{spread:.3f}")
    if cross_price and price:
        dev=abs(price-float(cross_price))/price*100
        if dev>2.0:
            q-=45; reasons.append(f"cross_deviation_{dev:.2f}")
        elif dev>1.0:
            q-=20; reasons.append(f"cross_deviation_{dev:.2f}")
        elif dev>0.50:
            q-=8; reasons.append(f"cross_deviation_{dev:.2f}")
    else:
        q-=8; reasons.append("cross_check_unavailable")
    return max(0,min(100,int(round(q)))),reasons


def _compute_crypto_signal_snapshot(asset_key, force=False):
    asset_key=str(asset_key or "").lower(); spec=SUPPORTED_CRYPTO.get(asset_key)
    if not spec: return {"ok":False,"error":"invalid_asset"}
    tickers,src,err=_crypto_tickers(force=force); t=tickers.get(asset_key)
    if not t: return {"ok":False,"error":"market_unavailable","detail":err}
    r15,_=_crypto_klines(asset_key,"15m",220,force=force); r1,_=_crypto_klines(asset_key,"1h",260,force=force); r4,_=_crypto_klines(asset_key,"4h",220,force=force)
    if min(len(r15),len(r1),len(r4))<60: return {"ok":False,"error":"insufficient_real_ohlcv","price":t.get("price"),"source":t.get("source")}
    closes=[x["c"] for x in r1]; c15=[x["c"] for x in r15]; c4=[x["c"] for x in r4]; vols=[x["v"] for x in r1]
    price=float(t["price"]); ema20=_ema(closes,20); ema50=_ema(closes,50); ema20_4=_ema(c4,20); ema50_4=_ema(c4,50)
    rsi=_rsi_close(closes,14); rsi15=_rsi_close(c15,14); macd,macd_sig=_macd(closes); atr=_true_atr(r1,14)
    vavg=sum(vols[-21:-1])/max(1,len(vols[-21:-1])) if len(vols)>=21 else None; volume_ratio=(vols[-1]/vavg if vavg and vavg>0 else None)
    support=min(x["l"] for x in r1[-48:]); resistance=max(x["h"] for x in r1[-48:-1] or r1[-48:])
    cross,_=_coinbase_spot(asset_key); quality,q_reasons=_crypto_data_quality(asset_key,t,r1,cross)
    long_score=50; reasons_long=[]; reasons_short=[]
    def add(points, long_text, short_text):
        nonlocal long_score
        long_score+=points
        if points>0 and long_text: reasons_long.append(long_text)
        elif points<0 and short_text: reasons_short.append(short_text)
    if ema20 is not None and ema50 is not None: add(12 if ema20>ema50 else -12,"EMA20 بالای EMA50","EMA20 زیر EMA50")
    if ema20_4 is not None and ema50_4 is not None: add(14 if ema20_4>ema50_4 else -14,"روند 4H صعودی","روند 4H نزولی")
    if rsi is not None:
        if 52<=rsi<=68: add(8,"RSI مومنتوم مثبت","")
        elif 32<=rsi<=48: add(-8,"","RSI مومنتوم منفی")
        elif rsi>=75: add(-4,"","RSI بسیار داغ")
        elif rsi<=25: add(4,"بازگشت بالقوه از اشباع فروش","")
    if rsi15 is not None:
        if rsi15>=55: add(4,"تأیید 15m مثبت","")
        elif rsi15<=45: add(-4,"","تأیید 15m منفی")
    if macd is not None and macd_sig is not None: add(8 if macd>macd_sig else -8,"MACD بالای Signal","MACD زیر Signal")
    recent_high=max(x["h"] for x in r1[-25:-1]); recent_low=min(x["l"] for x in r1[-25:-1])
    if price>recent_high: add(8,"شکست سقف 24 کندل","" )
    elif price<recent_low: add(-8,"","شکست کف 24 کندل")
    if volume_ratio is not None:
        if volume_ratio>=1.35 and long_score>=50: add(4,"حجم بالاتر از میانگین","")
        elif volume_ratio>=1.35 and long_score<50: add(-4,"","حجم بالاتر از میانگین")
    long_score=max(0,min(100,int(round(long_score)))); short_score=100-long_score
    if long_score>=SIGNAL_MIN_SCORE: side="BUY"; score=long_score; reasons=reasons_long
    elif short_score>=SIGNAL_MIN_SCORE: side="SELL"; score=short_score; reasons=reasons_short
    else: side="NEUTRAL"; score=max(long_score,short_score); reasons=(reasons_long if long_score>=50 else reasons_short)
    if quality<SIGNAL_MIN_DATA_QUALITY: side="NO_SIGNAL"; reasons=["کیفیت داده زیر آستانه امن"]+q_reasons
    if not atr or atr<=0: side="NO_SIGNAL"; reasons=["ATR واقعی قابل محاسبه نیست"]
    result={"ok":True,"asset":asset_key,"label":spec["label"],"symbol":spec["symbol"],"side":side,"score":score,
            "data_quality":quality,"price":price,"source":"Binance public OHLCV","cross_price":cross,
            "cross_source":"Coinbase spot" if cross else "not_available","rsi":rsi,"rsi15":rsi15,"ema20":ema20,"ema50":ema50,
            "macd":macd,"macd_signal":macd_sig,"atr":atr,"volume_ratio":volume_ratio,"support":support,"resistance":resistance,
            "reasons":reasons[:6],"quality_notes":q_reasons,"updated_at":datetime.now(timezone.utc).isoformat()}
    if side in {"BUY","SELL"}:
        risk=max(float(atr)*1.25,price*0.004)
        if side=="BUY":
            entry_low=price-max(atr*.12,price*.0007); entry_high=price+max(atr*.04,price*.0003); sl=min(price-risk,support-atr*.10); actual_risk=max(price-sl,price*.003)
            tp1=price+actual_risk; tp2=price+actual_risk*1.7; tp3=price+actual_risk*2.5
        else:
            entry_low=price-max(atr*.04,price*.0003); entry_high=price+max(atr*.12,price*.0007); sl=max(price+risk,resistance+atr*.10); actual_risk=max(sl-price,price*.003)
            tp1=price-actual_risk; tp2=price-actual_risk*1.7; tp3=price-actual_risk*2.5
        result.update({"entry_low":min(entry_low,entry_high),"entry_high":max(entry_low,entry_high),"stop_loss":sl,"tp1":tp1,"tp2":tp2,"tp3":tp3,"risk_reward":[1.0,1.7,2.5]})
    return result



def _cache_signal_snapshot(asset_key, snapshot):
    if not isinstance(snapshot,dict):
        return
    with _signal_snapshot_lock:
        _signal_snapshot_cache[str(asset_key)] = (time.monotonic(), dict(snapshot))


def crypto_signal_snapshot_cached(asset_key, max_age_seconds=600):
    key=str(asset_key or "").lower(); now=time.monotonic()
    with _signal_snapshot_lock:
        old=_signal_snapshot_cache.get(key)
        if old and now-float(old[0])<=max(1,int(max_age_seconds)):
            return dict(old[1])
    return None


def request_signal_snapshot_background(asset_key):
    key=str(asset_key or "").lower()
    if key not in SUPPORTED_CRYPTO:
        return False
    with _signal_background_guard:
        if key in _signal_background_keys:
            return False
        _signal_background_keys.add(key)
    def _worker():
        try:
            with _signal_background_slots:
                crypto_signal_snapshot(key,force=False)
        except Exception:
            logger.exception("Background signal snapshot failed for %s",key)
        finally:
            with _signal_background_guard:
                _signal_background_keys.discard(key)
    threading.Thread(target=_worker,name=f"signal-snapshot-{key}",daemon=True).start()
    return True


def crypto_signal_snapshot(asset_key, force=False):
    key=str(asset_key or "").lower()
    if not force:
        cached=crypto_signal_snapshot_cached(key,120)
        if cached is not None:
            return cached
    snapshot=_compute_crypto_signal_snapshot(key,force=force)
    _cache_signal_snapshot(key,snapshot)
    return snapshot

def _signal_side_fa(side):
    return {"BUY":"فرصت خرید","SELL":"فرصت فروش","NEUTRAL":"فعلاً فرصت مناسبی دیده نمی‌شود","NO_SIGNAL":"داده برای تصمیم کافی نیست"}.get(str(side or ""),"بازار زیر نظر است")


def _signal_state_message(snapshot):
    if not snapshot.get("ok"):
        return "داده معتبر کافی نیست"
    side=snapshot.get("side")
    if side in {"BUY","SELL"}:
        return _signal_side_fa(side)
    score=int(snapshot.get("score") or 0); quality=int(snapshot.get("data_quality") or 0)
    if quality < SIGNAL_MIN_DATA_QUALITY:
        return "داده برای تصمیم کافی نیست"
    if score >= max(60,SIGNAL_MIN_SCORE-8):
        return "بازار نزدیک به یک فرصت است؛ هنوز تأیید کامل نشده"
    return "فعلاً فرصت مناسبی دیده نمی‌شود"


def _signal_status_fa(status):
    return {"open":"باز","tp1":"هدف اول رسیده","tp2":"هدف دوم رسیده","tp3":"هدف سوم رسیده","stopped":"حد ضرر","breakeven":"سربه‌سر","ambiguous":"نتیجه مبهم"}.get(str(status or ""),str(status or "—"))


def _signal_recent_duplicate(asset_key, side):
    cutoff=(datetime.now(timezone.utc)-timedelta(seconds=SIGNAL_DUPLICATE_COOLDOWN)).isoformat()
    with db._conn() as c:
        row=c.execute("SELECT 1 FROM market_signals WHERE asset_key=? AND side=? AND created_at>=? AND status IN ('open','tp1','tp2') LIMIT 1",(asset_key,side,cutoff)).fetchone()
    return bool(row)


def persist_signal(snapshot):
    if not snapshot.get("ok") or snapshot.get("side") not in {"BUY","SELL"}: return None
    if _signal_recent_duplicate(snapshot["asset"],snapshot["side"]): return None
    sid=f"TS-{snapshot['symbol'].replace('USDT','')}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}-{uuid.uuid4().hex[:5].upper()}"
    now=_utc_now()
    with db._conn() as c:
        c.execute("""INSERT INTO market_signals(signal_id,asset_key,symbol,side,timeframe,issued_price,entry_low,entry_high,stop_loss,tp1,tp2,tp3,score,data_quality,source,reasons_json,metrics_json,status,hit_level,created_at,last_checked_at,active_stop,breakeven_armed,last_event_at)
                     VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'open',0,?,?,?,0,?)""",
                  (sid,snapshot["asset"],snapshot["symbol"],snapshot["side"],"1H",snapshot["price"],snapshot["entry_low"],snapshot["entry_high"],snapshot["stop_loss"],snapshot["tp1"],snapshot["tp2"],snapshot["tp3"],int(snapshot["score"]),int(snapshot["data_quality"]),snapshot["source"],json.dumps(snapshot.get("reasons") or [],ensure_ascii=False),json.dumps({k:snapshot.get(k) for k in ("rsi","rsi15","ema20","ema50","macd","macd_signal","atr","volume_ratio","support","resistance","cross_price","cross_source","quality_notes")},ensure_ascii=False),now,now,float(snapshot["stop_loss"]),now))
        c.execute("INSERT OR IGNORE INTO signal_events(signal_id,event_type,price,event_at,detail) VALUES(?,?,?,?,?)",(sid,"issued",snapshot["price"],now,"issued from real Binance OHLCV"))
    return sid


def recent_signals(limit=30, asset_key=None):
    limit=max(1,min(int(limit),100))
    with db._conn() as c:
        c.row_factory=sqlite3.Row
        if asset_key:
            rows=c.execute("SELECT * FROM market_signals WHERE asset_key=? ORDER BY created_at DESC LIMIT ?",(asset_key,limit)).fetchall()
        else:
            rows=c.execute("SELECT * FROM market_signals ORDER BY created_at DESC LIMIT ?",(limit,)).fetchall()
    out=[]
    for r in rows:
        d=dict(r)
        try:d["reasons"]=json.loads(d.pop("reasons_json") or "[]")
        except Exception:d["reasons"]=[]
        try:d["metrics"]=json.loads(d.pop("metrics_json") or "{}")
        except Exception:d["metrics"]={}
        out.append(d)
    return out


def open_signals_for_tracking(limit=2000):
    """Load open lifecycle records directly instead of relying on recent-history limits."""
    limit=max(1,min(int(limit),5000))
    with db._conn() as c:
        c.row_factory=sqlite3.Row
        rows=c.execute("SELECT * FROM market_signals WHERE status IN ('open','tp1','tp2') ORDER BY created_at ASC LIMIT ?",(limit,)).fetchall()
    out=[]
    for r in rows:
        d=dict(r)
        try: d["reasons"]=json.loads(d.pop("reasons_json") or "[]")
        except Exception: d["reasons"]=[]
        try: d["metrics"]=json.loads(d.pop("metrics_json") or "{}")
        except Exception: d["metrics"]={}
        out.append(d)
    return out


def signal_performance(days=30):
    cutoff=(datetime.now(timezone.utc)-timedelta(days=max(1,int(days)))).isoformat()
    with db._conn() as c:
        c.row_factory=sqlite3.Row
        rows=c.execute("SELECT status,hit_level FROM market_signals WHERE created_at>=?",(cutoff,)).fetchall()
    total=len(rows); terminal={"stopped","tp3","breakeven","ambiguous"}; closed=[r for r in rows if r["status"] in terminal]
    tp1=sum(1 for r in rows if int(r["hit_level"] or 0)>=1); tp2=sum(1 for r in rows if int(r["hit_level"] or 0)>=2); tp3=sum(1 for r in rows if int(r["hit_level"] or 0)>=3 or r["status"]=="tp3")
    sl_initial=sum(1 for r in rows if r["status"]=="stopped" and int(r["hit_level"] or 0)==0); sl_after_target=sum(1 for r in rows if r["status"]=="stopped" and int(r["hit_level"] or 0)>0)
    breakeven=sum(1 for r in rows if r["status"]=="breakeven"); ambiguous=sum(1 for r in rows if r["status"]=="ambiguous")
    evaluable=[r for r in closed if r["status"]!="ambiguous"]; tp1_eval=sum(1 for r in evaluable if int(r["hit_level"] or 0)>=1 or r["status"]=="tp3"); tp3_eval=sum(1 for r in evaluable if r["status"]=="tp3")
    tp1_rate=(tp1_eval/len(evaluable)*100) if evaluable else None; tp3_rate=(tp3_eval/len(evaluable)*100) if evaluable else None
    return {"days":days,"total":total,"tp1":tp1,"tp2":tp2,"tp3":tp3,"sl":sl_initial,"sl_after_target":sl_after_target,"breakeven":breakeven,"ambiguous":ambiguous,"open":total-len(closed),"tp1_rate":tp1_rate,"tp3_rate":tp3_rate,"hit_rate":tp1_rate,"wins":tp1_eval,"losses":sl_initial}


def glossary_text(term_key=None):
    if term_key and term_key in GLOSSARY:
        title,desc=GLOSSARY[term_key]; return f"📘 <b>{html.escape(title)}</b>\n\n{html.escape(desc)}"
    return "📘 <b>فرهنگ اصطلاحات طلایار</b>\n\nروی هر واژه بزن تا توضیح ساده و کاربردی آن را ببینی."


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
        [InlineKeyboardButton("🎯 سیگنال‌های واقعی", callback_data="signals"), InlineKeyboardButton("₿ کریپتوهای من", callback_data="crypto_lab")],
        [InlineKeyboardButton("💼 سبد من", callback_data="portfolio"), InlineKeyboardButton("💬 بپرس از طلایار", callback_data="smart_ask")],
    ]
    if PUBLIC_BASE_URL.startswith("https://"):
        rows.append([InlineKeyboardButton("📱 داشبورد حرفه‌ای طلایار", web_app=WebAppInfo(url=f"{PUBLIC_BASE_URL}/app"))])
    rows += [
        [InlineKeyboardButton("🎁 دعوت دوستان", callback_data="referrals"), InlineKeyboardButton("⭐ عضویت VIP", callback_data="vip")],
        [InlineKeyboardButton("📘 اصطلاحات بازار", callback_data="glossary"), InlineKeyboardButton("❓ سوالات متداول", callback_data="faq")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")],
    ]
    return InlineKeyboardMarkup(rows)



def signal_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("⚡ بررسی فرصت‌های بازار", callback_data="signal_scan")],
        [InlineKeyboardButton("📊 کارنامه شفاف", callback_data="signal_performance"), InlineKeyboardButton("🧾 آخرین فرصت‌ها", callback_data="signal_history")],
        [InlineKeyboardButton("₿ انتخاب ارزهای من", callback_data="crypto_lab")],
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="home")],
    ])


def crypto_lab_menu(user_id):
    selected=set(crypto_watchlist(user_id)); rows=[]
    keys=list(SUPPORTED_CRYPTO)
    for i in range(0,len(keys),2):
        row=[]
        for k in keys[i:i+2]:
            mark="✅" if k in selected else "➕"
            action="cw_remove" if k in selected else "cw_add"
            row.append(InlineKeyboardButton(f"{mark} {SUPPORTED_CRYPTO[k]['label']}",callback_data=f"{action}:{k}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("🎯 سیگنال ارزهای من",callback_data="signal_scan")])
    rows.append([InlineKeyboardButton("🔙 منوی اصلی",callback_data="home")])
    return InlineKeyboardMarkup(rows)


def glossary_menu():
    keys=list(GLOSSARY)
    rows=[]
    for i in range(0,len(keys),2):
        rows.append([InlineKeyboardButton(GLOSSARY[k][0],callback_data=f"term:{k}") for k in keys[i:i+2]])
    rows.append([InlineKeyboardButton("🔙 منوی اصلی",callback_data="home")])
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


def portfolio_menu(user_id):
    rows=[[InlineKeyboardButton("🔄 بروزرسانی قیمت‌ها",callback_data="portfolio_refresh")],
          [InlineKeyboardButton("➕ افزودن / ویرایش موقعیت",callback_data="portfolio_add")]]
    for p in db.portfolio_positions(user_id):
        label=ALERT_ASSETS.get(p["asset_key"],{}).get("label",p["asset_key"])
        rows.append([InlineKeyboardButton(f"✏️ {label}",callback_data=f"portfolio_edit:{p['asset_key']}"),
                     InlineKeyboardButton("🗑",callback_data=f"portfolio_del:{p['asset_key']}")])
    rows.append([InlineKeyboardButton("🔙 منوی اصلی",callback_data="home")])
    return InlineKeyboardMarkup(rows)

def portfolio_asset_menu():
    rows=[]
    keys=list(PORTFOLIO_ASSETS)
    for x in range(0,len(keys),2):
        row=[]
        for key in keys[x:x+2]:
            label=ALERT_ASSETS.get(key,{}).get("label",key)
            if key=="ounce": label+=" (معادل تومان)"
            row.append(InlineKeyboardButton(label,callback_data=f"portfolio_asset:{key}"))
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 سبد من",callback_data="portfolio")])
    return InlineKeyboardMarkup(rows)

def smart_ask_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💼 سبد و P&L من",callback_data="ask:portfolio")],
        [InlineKeyboardButton("💵 دلار + 🌎 انس + 🪙 طلا",callback_data="ask:markets")],
        [InlineKeyboardButton("🔥 آب‌شده نقدی / فردایی",callback_data="ask:melted")],
        [InlineKeyboardButton("🫧 حباب بازار",callback_data="ask:bubble"),
         InlineKeyboardButton("⚡ قوی‌ترین فرصت",callback_data="ask:opportunity")],
        [InlineKeyboardButton("⌨️ سؤال کوتاه",callback_data="ask:text")],
        [InlineKeyboardButton("🔙 منوی اصلی",callback_data="home")],
    ])


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

📱 <b>مینی‌اپ رایگان</b>
• نبض بازار و قیمت‌های لحظه‌ای
• بیشترین رشد و افت و نقشه کلی بازار
• صفحه پایه هر دارایی
• نمودار ۲۴ساعته از داده واقعی موجود

⭐ <b>مینی‌اپ VIP</b>
• اسکن فرصت‌های بازار و امتیاز هر فرصت
• قدرت حرکت (RSI)، جهت روند (EMA)، حمایت و مقاومت
• وضعیت روند و کیفیت داده
• ارزش تقریبی و نقشه حباب در دارایی‌های قابل محاسبه
• بازه‌های زمانی ۱ ساعت / ۴ ساعت / ۱ روز / ۷ روز / ۳۰ روز
• مرکز حرفه‌ای آب‌شده و اختلاف نقدی/فردایی، فقط وقتی داده معتبر مستقیم موجود باشد

🕯 <b>نکته نمودار</b>
برای کریپتو، کندل‌ها از OHLCV واقعی بازار دریافت می‌شوند. برای بازار داخلی، نمودار فقط از نمونه‌های واقعی ذخیره‌شده طلایار ساخته می‌شود و اگر داده کافی نباشد، کندل ساختگی نمایش داده نمی‌شود.

🔒 پرداخت، گزارش، مدیریت حساب و بعضی هشدارها عمدتاً داخل ربات نگه داشته شده‌اند تا مینی‌اپ سبک و سریع بماند.

🆕 <b>مینی‌اپ v14.0.1</b>
• مرکز دارایی‌های پویا و نمایش کریپتوهای انتخابی کاربر
• انتخاب سریع دارایی داخل صفحه تحلیل
• نمایش ساده قدرت فرصت با امکان بازکردن تحلیل فنی کامل
• نقشه قدرت بازار، آزمایش تاریخی و تاریخچه فعالیت
• هشدار هوشمند همراه تصویر وضعیت نمودار
• ارزش تقریبی، بازار من و مرکز حرفه‌ای آب‌شده
• شخصی‌سازی: تم، صفحه شروع، حالت فشرده، ابزارهای قابل نمایش و دارایی‌های سنجاق‌شده
• تنظیمات هر کاربر در SQLite ذخیره می‌شود و با Deploy از بین نمی‌رود
• 💼 سبد شخصی و سود/زیان: رایگان ۲ موقعیت، VIP تا ۱۰ موقعیت
• ☀️ گزارش صبحگاهی شخصی بر پایه بازار من و سبد
• 🕒 نمایش زمان آخرین داده و کیفیت تازگی قیمت
• 💬 پرسش هوشمند محدود و قابل اتکا بدون تولید عدد ساختگی
• 🔎 توضیح ساده «چرا این فرصت/هشدار ایجاد شد؟»

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
    """Owner/admin check resilient to a missing Railway ADMIN_ID env."""
    uid = str(user_id or "")
    if not uid:
        return False
    if bool(ADMIN_ID) and uid == str(ADMIN_ID):
        return True
    return bool(AUTHORIZED_ADMIN_ID) and uid == str(AUTHORIZED_ADMIN_ID)


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
            "✅ مرکز نوسان و فرصت‌های بازار: رادار حباب، اسکن فرصت، نقشه بازار، آزمایش تاریخی و هشدار هوشمند\n\n"
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
def _market_data_age_seconds():
    fetched=int(_market_cache.get("fetched_at") or 0)
    return max(0,int(time.time())-fetched) if fetched else None

def _freshness_badge():
    age=_market_data_age_seconds()
    if age is None: return "⚪ زمان بروزرسانی نامشخص"
    state="🟢 تازه" if age<=15 else ("🟡 کمی با تأخیر" if age<=45 else "🔴 با تأخیر")
    return f"{state} • {age} ثانیه پیش"

def _load_persistent_market_cache():
    """Restore the last known-good BRS payload from SQLite after a process restart.

    This is display fallback only. Jobs that can trigger alerts should reject a
    non-empty error returned alongside stale data.
    """
    try:
        saved = db.get_state("brs_last_good", {}) or {}
        payload = saved.get("payload")
        fetched_at = int(saved.get("fetched_at") or 0)
        if not isinstance(payload, dict) or not fetched_at:
            return None, None
        age = max(0, int(time.time()) - fetched_at)
        if age > CACHE_PERSISTENT_STALE_MAX_SECONDS:
            return None, age
        _market_cache.update({
            "data": payload,
            "saved_at": time.monotonic(),
            "fetched_at": fetched_at,
            "last_error": "",
            "persisted_at": fetched_at,
        })
        return payload, age
    except Exception:
        logger.exception("Could not restore persistent BRS cache")
        return None, None


def _persist_market_cache(payload, fetched_at):
    """Persist at most once per minute to avoid unnecessary SQLite writes."""
    try:
        last = int(_market_cache.get("persisted_at") or 0)
        if fetched_at - last < 60:
            return
        db.set_state("brs_last_good", {"payload": payload, "fetched_at": int(fetched_at)})
        _market_cache["persisted_at"] = int(fetched_at)
    except Exception:
        logger.exception("Could not persist BRS last-good snapshot")


def _brs_fetch_once():
    response = _brs_session.get(
        BRS_API_URL,
        timeout=API_TIMEOUT,
        headers={"Accept": "application/json", "User-Agent": f"TalayarBot/{APP_VERSION}"},
    )
    response.raise_for_status()
    payload = _unwrap_payload(response.json())
    if payload is None:
        raise ValueError("ساختار پاسخ API تغییر کرده")
    return payload


def get_market_data(force_refresh=False):
    """Return (payload, error).

    On a transient BRS failure the last known-good payload may be returned with a
    non-empty error. UI code can display it as stale; alerting jobs must not act
    on it. Concurrent refreshes are coalesced so one slow upstream response does
    not cause a thundering herd.
    """
    global _brs_failure_count, _brs_circuit_until

    now_mono = time.monotonic()
    initial_saved_at = float(_market_cache.get("saved_at") or 0.0)
    if not force_refresh and _market_cache["data"] is not None and now_mono - initial_saved_at < CACHE_TTL_SECONDS:
        return _market_cache["data"], None
    if not BRS_API_URL:
        if _market_cache["data"] is None:
            cached, age = _load_persistent_market_cache()
            if cached is not None:
                return cached, f"تنظیمات اتصال API کامل نیست؛ آخرین داده معتبر ({age} ثانیه قبل) استفاده شد"
        return None, "تنظیمات اتصال API کامل نیست"

    with _market_refresh_lock:
        now_mono = time.monotonic()
        current_saved_at = float(_market_cache.get("saved_at") or 0.0)

        # Normal callers use the TTL. A forced caller still accepts a refresh
        # completed by another thread while it was waiting on this lock.
        if _market_cache["data"] is not None:
            if (not force_refresh and now_mono - current_saved_at < CACHE_TTL_SECONDS) or (
                force_refresh and current_saved_at != initial_saved_at and now_mono - current_saved_at < CACHE_TTL_SECONDS
            ):
                return _market_cache["data"], None

        # Short circuit breaker after repeated upstream failures.
        if now_mono < _brs_circuit_until:
            err = f"منبع بازار موقتاً در حالت بازیابی است؛ {max(1, int(_brs_circuit_until-now_mono))} ثانیه تا تلاش بعدی"
            age = _market_data_age_seconds()
            if _market_cache["data"] is not None and age is not None and age <= CACHE_STALE_MAX_SECONDS:
                return _market_cache["data"], f"{err}؛ آخرین داده معتبر استفاده شد"
            if _market_cache["data"] is None:
                cached, persistent_age = _load_persistent_market_cache()
                if cached is not None:
                    return cached, f"{err}؛ آخرین داده معتبر ({persistent_age} ثانیه قبل) استفاده شد"
            return None, err

        last_exc = None
        last_status = None
        for attempt in range(BRS_RETRY_ATTEMPTS):
            try:
                payload = _brs_fetch_once()
                fetched_at = int(time.time())
                # Important: saved_at is the SUCCESS time, not request-start time.
                _market_cache.update({
                    "data": payload,
                    "saved_at": time.monotonic(),
                    "fetched_at": fetched_at,
                    "last_error": "",
                })
                _brs_failure_count = 0
                _brs_circuit_until = 0.0
                _persist_market_cache(payload, fetched_at)
                return payload, None
            except requests.Timeout as exc:
                last_exc = exc
                err = "زمان پاسخ‌گویی API تمام شد"
            except requests.RequestException as exc:
                last_exc = exc
                last_status = exc.response.status_code if exc.response is not None else None
                err = f"خطای اتصال به API (کد {last_status if last_status is not None else 'no-response'})"
                # Do not retry ordinary permanent 4xx errors.
                if last_status is not None and 400 <= last_status < 500 and last_status not in {408, 425, 429}:
                    break
            except Exception as exc:
                last_exc = exc
                err = str(exc) if str(exc) else "خطای پیش‌بینی‌نشده در دریافت قیمت‌ها"
                # Malformed payloads may be transient, but one extra try is enough.
                if attempt >= 1:
                    break

            if attempt < BRS_RETRY_ATTEMPTS - 1:
                time.sleep(BRS_RETRY_BASE_DELAY * (2 ** attempt))

        _brs_failure_count += 1
        if _brs_failure_count >= BRS_CIRCUIT_FAILURES:
            _brs_circuit_until = time.monotonic() + BRS_CIRCUIT_SECONDS
        _market_cache["last_error"] = err
        logger.warning(
            "BRS refresh failed after %s attempt(s): %s%s",
            min(BRS_RETRY_ATTEMPTS, (attempt + 1) if 'attempt' in locals() else 1),
            type(last_exc).__name__ if last_exc else "unknown",
            f" status={last_status}" if last_status is not None else "",
        )

        age = _market_data_age_seconds()
        if _market_cache["data"] is not None and age is not None and age <= CACHE_STALE_MAX_SECONDS:
            return _market_cache["data"], f"{err}؛ آخرین داده معتبر استفاده شد"

        if _market_cache["data"] is None:
            cached, persistent_age = _load_persistent_market_cache()
            if cached is not None:
                return cached, f"{err}؛ آخرین داده معتبر ({persistent_age} ثانیه قبل) استفاده شد"
        return None, err


async def get_market_data_async(force_refresh=False):
    """Non-blocking adapter for Telegram async handlers/jobs."""
    return await asyncio.to_thread(get_market_data, force_refresh)


def get_market_data_cached(max_age_seconds=CACHE_PERSISTENT_STALE_MAX_SECONDS):
    """Return last known-good BRS payload without any network I/O.

    This function is intentionally safe for Mini App HTTP request threads. It
    never waits on BRS. A persisted SQLite snapshot may be restored after a
    Railway restart, but no value older than ``max_age_seconds`` is returned.
    """
    max_age_seconds=max(0,int(max_age_seconds))
    data=_market_cache.get("data")
    age=_market_data_age_seconds()
    if data is None:
        data,age=_load_persistent_market_cache()
    if data is None or age is None or age>max_age_seconds:
        return None,age
    return data,age


def request_market_refresh_background(force=True):
    """Start one best-effort BRS refresh without blocking a web request."""
    global _brs_background_running
    if not BRS_API_URL:
        return False
    with _brs_background_guard:
        if _brs_background_running:
            return False
        _brs_background_running=True

    def _worker():
        global _brs_background_running
        try:
            get_market_data(force_refresh=bool(force))
        except Exception:
            logger.exception("Background BRS refresh failed")
        finally:
            with _brs_background_guard:
                _brs_background_running=False

    threading.Thread(target=_worker,name="brs-background-refresh",daemon=True).start()
    return True


def find_item(data, symbols, sections=None, name_keywords=None):
    if not isinstance(data, dict):
        return None
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


PORTFOLIO_ASSETS=("gold18","melted","emami","half","quarter","usd","aed","ounce")
PORTFOLIO_UNITS={"gold18":"گرم","melted":"مثقال","emami":"عدد","half":"عدد","quarter":"عدد","usd":"دلار","aed":"درهم","ounce":"انس"}

def _item_price_toman(item):
    p=_item_price(item)
    if p is None: return None
    unit=str((item or {}).get("unit") or "").casefold()
    if "ریال" in unit or unit in {"irr","rial"}: return p/10.0
    return p

def _portfolio_current_price(asset,market):
    item=find_alert_item(market,asset)
    if not item: return None
    p=_item_price_toman(item)
    if p is None: return None
    if asset=="ounce":
        usd=_item_price_toman(find_alert_item(market,"usd"))
        if usd is None: return None
        return p*usd
    return p

def portfolio_limit(user_id):
    return PORTFOLIO_VIP_LIMIT if is_vip(user_id) else PORTFOLIO_FREE_LIMIT

def portfolio_summary(user_id,market):
    positions=db.portfolio_positions(user_id)
    total=cost=0.0; rows=[]; missing=0
    for pos in positions:
        asset=pos["asset_key"]; qty=float(pos["quantity"]); avg=float(pos["avg_buy_price"])
        current=_portfolio_current_price(asset,market)
        base=qty*avg; cost+=base
        if current is None:
            missing+=1
            rows.append({**pos,"current":None,"value":None,"cost":base,"pnl":None,"pnl_pct":None})
            continue
        value=qty*current; pnl=value-base; pct=(pnl/base*100) if base else 0.0
        total+=value
        rows.append({**pos,"current":current,"value":value,"cost":base,"pnl":pnl,"pnl_pct":pct})
    pnl=total-cost if missing==0 else None
    pct=(pnl/cost*100) if pnl is not None and cost else None
    today=datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")
    prev=db.previous_portfolio_snapshot(user_id,today)
    daily=None
    if prev and missing==0:
        daily=total-float(prev.get("market_value") or 0)
    return {"rows":rows,"market_value":total,"cost":cost,"pnl":pnl,"pnl_pct":pct,"daily":daily,"missing":missing}

def build_portfolio_text(user_id,market):
    s=portfolio_summary(user_id,market)
    lines=["💼 <b>سبد من</b>",f"ظرفیت: {len(s['rows'])}/{portfolio_limit(user_id)}",""]
    if not s["rows"]:
        lines.append("هنوز موقعیتی ثبت نکرده‌ای.")
    for r in s["rows"]:
        label=ALERT_ASSETS.get(r["asset_key"],{}).get("label",r["asset_key"])
        unit=PORTFOLIO_UNITS.get(r["asset_key"],"واحد")
        lines.append(f"• <b>{label}</b> — {r['quantity']:g} {unit}")
        lines.append(f"  میانگین خرید: {_format_number(r['avg_buy_price'])} تومان")
        if r["current"] is None:
            lines.append("  قیمت فعلی: —")
        else:
            sign="🟢" if r["pnl"]>=0 else "🔴"
            lines.append(f"  فعلی: {_format_number(r['current'])} • {sign} {_format_number(r['pnl'])} ({r['pnl_pct']:+.2f}%)")
    if s["rows"]:
        lines+=["",f"هزینه کل: <b>{_format_number(s['cost'])}</b> تومان"]
        if s["missing"]==0:
            lines.append(f"ارزش فعلی: <b>{_format_number(s['market_value'])}</b> تومان")
            lines.append(f"P&L کل: <b>{_format_number(s['pnl'])}</b> تومان ({s['pnl_pct']:+.2f}%)")
            if s["daily"] is not None:
                lines.append(f"تغییر نسبت به Snapshot قبلی: <b>{_format_number(s['daily'])}</b> تومان")
        else:
            lines.append(f"⚠️ قیمت {s['missing']} موقعیت فعلاً در دسترس نیست؛ جمع کل ناقص نمایش داده نمی‌شود.")
    lines+=["",_freshness_badge(),f"<i>{DISCLAIMER}</i>"]
    return "\n".join(lines)

def save_portfolio_snapshot_for_user(user_id,market):
    s=portfolio_summary(user_id,market)
    if not s["rows"] or s["missing"]: return False
    day=datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")
    return db.save_portfolio_snapshot_once(user_id,day,s["market_value"],s["cost"],s["pnl"] or 0)

def build_personal_briefing(user_id,market):
    lines=[f"☀️ <b>Briefing شخصی طلایار</b>",f"🕒 {datetime.now(TEHRAN_TZ):%Y/%m/%d - %H:%M}",""]
    watch=db.get_watchlist(user_id)
    keys=[x["asset_key"] for x in watch][:5] or ["usd","gold18","ounce"]
    lines.append("📌 <b>بازارهای مهم شما</b>")
    for key in keys:
        item=find_alert_item(market,key)
        if item:
            ch=_safe_change_percent(item)
            lines.append(f"• {ALERT_ASSETS.get(key,{}).get('label',key)}: <b>{_format_number(item.get('price'))}</b> {item.get('unit') or ''} ({ch:+.2f}%)")
    ps=portfolio_summary(user_id,market)
    if ps["rows"]:
        lines+=["","💼 <b>سبد</b>"]
        if not ps["missing"]:
            lines.append(f"ارزش: <b>{_format_number(ps['market_value'])}</b> تومان")
            lines.append(f"P&L کل: <b>{_format_number(ps['pnl'])}</b> تومان ({ps['pnl_pct']:+.2f}%)")
            if ps["daily"] is not None: lines.append(f"تغییر نسبت به Snapshot قبلی: {_format_number(ps['daily'])} تومان")
        else: lines.append("بعضی قیمت‌های سبد فعلاً در دسترس نیست.")
    # lightweight VIP insight from existing engine
    if is_vip(user_id):
        scored=[]
        for key in ALERT_ASSETS:
            f=_market_features(key,market)
            if f.get("score") is not None: scored.append((int(f["score"]),key,f))
        if scored:
            score,key,f=max(scored,key=lambda x:x[0])
            lines+=["",f"⚡ <b>Insight</b>: {ALERT_ASSETS[key]['label']} امتیاز {score}/100 • Q {f.get('quality') or 0}/100"]
    lines+=["",_freshness_badge(),f"<i>{DISCLAIMER}</i>"]
    return "\n".join(lines)

def _smart_answer(user_id,question,market):
    q=question.strip().casefold()
    if any(w in q for w in ("آبشده","آب‌شده","فردایی","نقدی")):
        return build_melted_center(market)
    if any(w in q for w in ("حباب","ارزش منصفانه")):
        return build_bubble_radar(market) if is_vip(user_id) else "🫧 تحلیل کامل حباب مخصوص VIP است؛ در نسخه رایگان قیمت‌های لحظه‌ای در دسترس‌اند."
    if any(w in q for w in ("قوی","فرصت","بهترین")):
        return build_opportunity_scanner(market) if is_vip(user_id) else "⚡ رتبه‌بندی فرصت‌ها مخصوص VIP است."
    if "دلار" in q and ("انس" in q or "طلا" in q):
        usd=find_alert_item(market,"usd"); ounce=find_alert_item(market,"ounce"); gold=find_alert_item(market,"gold18")
        return ("🧠 <b>خلاصه دلار / انس / طلا</b>\n\n"
                f"دلار: <b>{_format_number((usd or {}).get('price'))}</b> {(usd or {}).get('unit') or ''}\n"
                f"انس: <b>{_format_number((ounce or {}).get('price'))}</b> {(ounce or {}).get('unit') or ''}\n"
                f"طلای ۱۸: <b>{_format_number((gold or {}).get('price'))}</b> {(gold or {}).get('unit') or ''}\n\n{_freshness_badge()}")
    if any(w in q for w in ("سبد","سود","زیان","p&l")):
        return build_portfolio_text(user_id,market)
    return ("فعلاً سؤال‌های هوشمند طلایار محدود به «سبد و سود/زیان»، «دلار و انس و طلا»، "
            "«آب‌شده نقدی/فردایی»، «حباب» و «قوی‌ترین فرصت» هستند.")

def explain_smart_alert(rule,f):
    parts=[]
    if rule=="breakout": parts.append("قیمت از محدوده ۲۴ساعته معتبر عبور کرده.")
    elif rule=="abnormal": parts.append(f"نوسان جاری نسبت به نوسان معمول غیرعادی شده؛ نسبت نوسان {float(f.get('vol_ratio') or 0):.2f}×.")
    elif rule=="confluence": parts.append(f"چند مؤلفه تکنیکال هم‌جهت شده‌اند؛ Strength {f.get('score') or '—'}/100 و Q {f.get('quality') or 0}/100.")
    elif rule=="bubble": parts.append("انحراف/حباب از آستانه تعریف‌شده عبور کرده.")
    exp=_explain_score(f)
    if exp.get("available") and exp.get("parts"):
        positives=[p["label"] for p in exp["parts"] if int(p.get("points") or 0)>0][:3]
        negatives=[p["label"] for p in exp["parts"] if int(p.get("points") or 0)<0][:2]
        if positives: parts.append("تأیید مثبت: "+"، ".join(positives))
        if negatives: parts.append("فشار منفی: "+"، ".join(negatives))
    return " | ".join(parts) if parts else "شرط هشدار تعریف‌شده برقرار شده است."

def build_daily_report(market):
    text = f"🗓 <b>گزارش روزانه طلایار</b>\n🕒 {datetime.now(TEHRAN_TZ):%Y/%m/%d - %H:%M}\n\n"
    for key in ("usd", "gold18", "emami", "half", "quarter", "ounce", "btc"):
        item = find_alert_item(market, key)
        if item:
            text += f"• {ALERT_ASSETS[key]['label']}: <b>{_format_number(item.get('price'))}</b> {item.get('unit') or ''}\n"
    return text + f"\n{_freshness_badge()}\n<i>{DISCLAIMER}</i>"


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


def _explain_score(f):
    if not f or f.get("price") is None:
        return {"available":False,"reason":"داده بازار موجود نیست","parts":[]}
    q=int(f.get("quality") or 0)
    if q<35 or f.get("score") is None:
        return {"available":False,"reason":f"کیفیت داده {q}% است؛ حداقل ۳۵٪ لازم است.","parts":[]}
    parts=[]
    e9,e21,e50=f.get("ema9"),f.get("ema21"),f.get("ema50")
    if e9 is not None and e21 is not None:
        p=1 if e9>e21 else -1; parts.append({"label":"EMA 9/21","points":p*10,"raw":p,"detail":"صعودی" if p>0 else "نزولی"})
    if e21 is not None and e50 is not None:
        p=1 if e21>e50 else -1; parts.append({"label":"EMA 21/50","points":p*10,"raw":p,"detail":"صعودی" if p>0 else "نزولی"})
    if f.get("breakout") in {"up","down"}:
        p=1 if f.get("breakout")=="up" else -1; parts.append({"label":"شکست محدوده","points":p*10,"raw":p,"detail":"رو به بالا" if p>0 else "رو به پایین"})
    r=f.get("rsi")
    if r is not None:
        p=1 if 55<=r<=75 else (-1 if 25<=r<=45 else 0); parts.append({"label":"RSI14","points":p*10,"raw":p,"detail":f"{r:.1f}"})
    v=f.get("v60")
    if v is not None:
        p=1 if v>0.15 else (-1 if v<-0.15 else 0); parts.append({"label":"مومنتوم ۱ساعته","points":p*10,"raw":p,"detail":f"{v:+.2f}%"})
    if f.get("abnormal") and v is not None:
        p=1 if v>0 else (-1 if v<0 else 0); parts.append({"label":"جهش نوسان","points":p*10,"raw":p,"detail":f"{(f.get('vol_ratio') or 0):.2f}×"})
    raw=sum(int(x['raw']) for x in parts); clipped=max(-5,min(5,raw)); score=int(round(50+clipped*10))
    return {"available":True,"base":50,"raw":raw,"clipped":clipped,"score":score,"quality":q,"parts":parts,
            "note":"امتیاز نهایی = ۵۰ + مجموع مؤلفه‌های همگرایی × ۱۰؛ مجموع در بازه -۵ تا +۵ محدود می‌شود."}


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
    for label,key,unit in (("طلای ۱۸","gold18","تومان"),("انس جهانی","ounce","دلار"),("دلار تهران","usd","تومان"),("درهم امارات","aed","تومان")):
        val=m.get(key); lines.append(f"• {label}: <b>{_format_number(val)}</b> {unit}" if val is not None else f"• {label}: داده موجود نیست")
    lines += ["","<i>طلایار برای آب‌شده/فردایی عدد ساختگی نمایش نمی‌دهد. اگر قیمت مستقیم در منبع نباشد، فقط برآورد نظری نقدی با برچسب مشخص نشان داده می‌شود.</i>"]
    return "\n".join(lines)

def _mini_asset_registry(market=None):
    """Public asset registry: hides unreliable rows instead of showing dead cards."""
    rows=[]
    for key, info in ALERT_ASSETS.items():
        if key=="herat_usd":
            continue
        item=_mini_price_item(market,key) if market is not None else None
        if key=="melted_future" and market is not None and not item:
            continue
        section=(info.get("sections") or ["other"])[0]
        rows.append({"key":key,"label":info.get("label",key),"section":section,"available":bool(item),"unit":(item or {}).get("unit","")})
    return rows


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
    """Build the dashboard using local/cached data only.

    No BRS/Binance request is allowed here. This keeps Mini App bootstrap fast
    even during upstream outages; background jobs refresh the caches separately.
    """
    market = market if isinstance(market,dict) else {}
    vip = bool(user_id and is_vip(user_id))
    keys = tuple(ALERT_ASSETS.keys())
    items = [x for k in keys for x in [_mini_price_item(market,k)] if x and k!="herat_usd"]

    selected_crypto=[]
    if user_id:
        selected_keys=crypto_watchlist(user_id)
        tickers,_=_crypto_tickers_cached_only(60)
        for ck in selected_keys[:crypto_limit(user_id)]:
            spec=SUPPORTED_CRYPTO.get(ck)
            if not spec:
                continue
            t=tickers.get(ck) or {}
            selected_crypto.append({
                "key":ck,"label":spec["label"],"symbol":spec["symbol"],
                "price":t.get("price"),"change":t.get("change"),"unit":"USDT",
                "source":t.get("source") or ("cache" if t else "pending")
            })

    movers = sorted(items, key=lambda x: abs(float(x.get("change") or 0)), reverse=True)[:5]
    changes = [float(x.get("change") or 0) for x in items if x.get("change") is not None]
    avg = (sum(changes) / len(changes)) if changes else 0.0
    positives = sum(1 for x in changes if x > 0)
    negatives = sum(1 for x in changes if x < 0)
    pulse_score = max(0, min(100, int(round(50 + avg * 8 + (positives-negatives)*2)))) if changes else None
    pulse_state = "صعودی" if pulse_score is not None and pulse_score >= 58 else ("نزولی" if pulse_score is not None and pulse_score <= 42 else ("خنثی" if pulse_score is not None else "در انتظار داده"))
    heatmap = [{"key":x["key"],"label":x["label"],"price":x["price"],"unit":x["unit"],"change":x["change"]} for x in items]
    return {
        "version": APP_VERSION, "vip": vip, "tier": "vip" if vip else "free",
        "items": items, "movers": movers, "heatmap": heatmap,
        "pulse": {"score": pulse_score, "state": pulse_state, "average_change": avg if changes else None,
                  "positive": positives, "negative": negatives, "count": len(changes)},
        "melted": _melted_snapshot(market),
        "registry": _mini_asset_registry(market),
        "crypto_selected": selected_crypto,
        "preferences": db.get_miniapp_preferences(user_id) if user_id else {},
        "free": {"pulse": True, "prices": True, "movers": True, "heatmap": True, "asset_basic": True, "chart_24h": True, "customize": True, "themes": True},
        "vip_features": {"scanner": vip, "technicals": vip, "fair_value": vip, "pro_timeframes": vip, "melted_pro": vip},
        "updated_at": datetime.now(TEHRAN_TZ).strftime("%H:%M:%S")
    }


def _mini_session_payload(user_id):
    """Fast local-only identity/VIP bootstrap. No market provider is touched."""
    vip=is_vip(user_id)
    days=vip_days_left(user_id)
    return {
        "version":APP_VERSION,
        "user_id":int(user_id),
        "vip":bool(vip),
        "tier":"vip" if vip else "free",
        "vip_days_left":days,
        "is_admin":_is_admin(user_id),
        "preferences":db.get_miniapp_preferences(user_id),
        "crypto_limit":crypto_limit(user_id),
        "storage":_db_persistence_hint(),
        "server_time":datetime.now(timezone.utc).isoformat(),
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
            "vol": f.get("vol"), "vol_ratio": f.get("vol_ratio"), "abnormal": f.get("abnormal"),
            "explain": _explain_score(f)
        }
        if asset in COIN_SPECS or asset in {"gold18","melted"}:
            result["fair_value"] = f.get("fair")
            result["bubble_z"] = f.get("bubble_z")
    return result, 200


def _mini_scanner_payload(market, user_id):
    if not (user_id and is_vip(user_id)):
        return {"error":"vip_required"}, 403
    rows=[]
    for asset in ALERT_ASSETS:
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


def _mini_outlier_threshold(asset):
    if asset in {"btc","eth","usdt"}: return 0.25
    if asset == "ounce": return 0.12
    return 0.08

def _mini_ohlc(asset, hours, bucket_seconds, max_candles=MINIAPP_MAX_CANDLES):
    points=db.get_price_history(asset,int(hours)); derived_factor=None
    if not points and asset=="melted":
        points=db.get_price_history("gold18",int(hours)); derived_factor=MESGHAL_18_EQUIV_FACTOR
    now=int(time.time()); start_ts=now-int(hours*3600)
    first_bucket=(start_ts//bucket_seconds)*bucket_seconds; last_bucket=(now//bucket_seconds)*bucket_seconds
    expected=max(1,int((last_bucket-first_bucket)//bucket_seconds)+1)
    if not points:
        return [], {"expected":expected,"filled":0,"coverage_pct":0.0,"gaps":expected,"filtered_outliers":0,"bucket_seconds":bucket_seconds,"derived":bool(derived_factor)}
    cleaned=[]; recent=[]; filtered=0; threshold=_mini_outlier_threshold(asset)
    for p in points:
        try:
            ts=int(p["ts"]); price=float(p["price"])
            if price<=0: continue
            if derived_factor is not None: price*=derived_factor
        except (TypeError,ValueError,KeyError):
            continue
        if recent:
            med=float(pd.Series(recent[-9:]).median())
            if med>0 and abs(price-med)/med>threshold:
                filtered+=1; continue
        recent.append(price); cleaned.append((ts,price))
    buckets={}
    for ts,price in cleaned:
        b=(ts//bucket_seconds)*bucket_seconds; row=buckets.get(b)
        if row is None: buckets[b]=[price,price,price,price,1]
        else:
            row[1]=max(row[1],price); row[2]=min(row[2],price); row[3]=price; row[4]+=1
    slots=[]; b=first_bucket
    while b<=last_bucket:
        v=buckets.get(b)
        slots.append({"t":b,"gap":True} if v is None else {"t":b,"o":v[0],"h":v[1],"l":v[2],"c":v[3],"n":v[4],"gap":False})
        b+=bucket_seconds
    if len(slots)>max_candles: slots=slots[-max_candles:]
    filled=sum(1 for x in slots if not x.get("gap")); gaps=len(slots)-filled
    coverage=filled/len(slots)*100 if slots else 0.0
    return slots,{"expected":len(slots),"filled":filled,"coverage_pct":coverage,"gaps":gaps,"filtered_outliers":filtered,"bucket_seconds":bucket_seconds,"derived":bool(derived_factor)}


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
    candles,meta=_mini_ohlc(asset,hours,bucket)
    return {"version":APP_VERSION,"vip":vip,"asset":asset,"label":ALERT_ASSETS[asset]["label"],"timeframe":str(timeframe).upper(),
            "candles":candles,"max":MINIAPP_MAX_CANDLES,"coverage":meta,
            "note":"OHLC از تاریخچه ذخیره‌شده طلایار تجمیع شده؛ Gapهای واقعی حفظ و نمونه‌های پرت مشکوک از مقیاس حذف می‌شوند. OHLC مستقیم بورس/صرافی نیست."},200

def _mini_rsi_map_payload(market,user_id):
    if not (user_id and is_vip(user_id)): return {"error":"vip_required"},403
    rows=[]
    for asset in ALERT_ASSETS:
        f=_market_features(asset,market)
        if f.get("price") is None: continue
        r=f.get("rsi")
        zone="نامشخص" if r is None else ("اشباع خرید" if r>=70 else ("اشباع فروش" if r<=30 else ("مثبت" if r>=55 else ("منفی" if r<=45 else "خنثی"))))
        rows.append({"key":asset,"label":ALERT_ASSETS[asset]["label"],"rsi":r,"zone":zone,"score":f.get("score"),"q":f.get("quality")})
    rows.sort(key=lambda x:(x["rsi"] is not None,x["rsi"] or -1),reverse=True)
    return {"version":APP_VERSION,"items":rows},200

def _backtest_lite(asset,rule="confluence",horizon=12):
    vals=[v for _,v in _series(asset,720)]
    if len(vals)<80: return {"samples":0,"message":f"حداقل ۸۰ نمونه لازم است؛ فعلاً {len(vals)} نمونه داریم."}
    horizon=max(6,min(int(horizon or 12),48)); events=[]
    for i in range(55,len(vals)-horizon,12):
        w=vals[:i+1]; e9=_ema(w[-60:],9); e21=_ema(w[-60:],21); r=_rsi_close(w[-40:],14)
        if r is None: continue
        direction=0
        if rule=="rsi_oversold" and r<=30: direction=1
        elif rule=="rsi_overbought" and r>=70: direction=-1
        elif rule=="ema_cross" and e9 is not None and e21 is not None: direction=1 if e9>e21 else -1
        elif rule=="confluence" and e9 is not None and e21 is not None:
            sc=(1 if e9>e21 else -1)+(1 if r>=55 else (-1 if r<=45 else 0))
            if abs(sc)>=2: direction=1 if sc>0 else -1
        if not direction: continue
        future=(vals[i+horizon]-vals[i])/vals[i]*100 if vals[i] else 0; events.append(future*direction)
    if not events: return {"samples":0,"message":"در آرشیو فعلی رخداد کافی برای این شرط پیدا نشد."}
    wins=sum(1 for x in events if x>0)
    return {"samples":len(events),"hit":wins/len(events)*100,"avg":sum(events)/len(events),"best":max(events),"worst":min(events),
            "note":"آزمایش تاریخی سبک روی تاریخچه محلی طلایار است؛ کارمزد، لغزش و نقدشوندگی را لحاظ نمی‌کند."}

def _mini_backtest_payload(user_id,asset,rule):
    if not (user_id and is_vip(user_id)): return {"error":"vip_required"},403
    if asset not in ALERT_ASSETS: return {"error":"invalid_asset"},400
    if rule not in {"confluence","rsi_oversold","rsi_overbought","ema_cross"}: return {"error":"invalid_rule"},400
    return {"version":APP_VERSION,"asset":asset,"result":_backtest_lite(asset,rule)},200

def _mini_activity_payload(user_id):
    if not user_id: return {"error":"unauthorized"},401
    return {"version":APP_VERSION,"items":db.get_activity(user_id,80)},200


def _mini_preferences_payload(user_id):
    return {"version":APP_VERSION,"preferences":db.get_miniapp_preferences(user_id)}, 200

def _mini_save_preferences_payload(user_id, prefs):
    return {"version":APP_VERSION,"preferences":db.set_miniapp_preferences(user_id, prefs if isinstance(prefs,dict) else {})}, 200

def _mini_smart_alert_payload(user_id, asset, rule):
    if not (user_id and is_vip(user_id)):
        return {"error":"vip_required"},403
    if asset not in ALERT_ASSETS or rule not in {"breakout","abnormal","confluence","bubble"}:
        return {"error":"invalid_request"},400
    if rule == "bubble" and not (asset in COIN_SPECS or asset in {"gold18","melted"}):
        return {"error":"rule_not_supported"},400
    result=db.add_smart_alert(user_id,user_id,asset,rule)
    if result=="added": db.add_activity(user_id,"smart_alert_created",asset,"هشدار هوشمند ساخته شد",smart_rule_label(rule),None,{"rule":rule})
    return {"version":APP_VERSION,"ok":True,"result":result,"asset":asset,"rule":rule},200

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


def _crypto_catalog_payload(user_id):
    selected=set(crypto_watchlist(user_id)); tickers,source,error=_crypto_tickers()
    items=[]
    for key,spec in SUPPORTED_CRYPTO.items():
        t=tickers.get(key) or {}
        items.append({"key":key,"label":spec["label"],"symbol":spec["symbol"],"selected":key in selected,"price":t.get("price"),"change":t.get("change"),"high":t.get("high"),"low":t.get("low"),"volume":t.get("volume"),"quote_volume":t.get("quote_volume"),"unit":"USDT","source":t.get("source") or source})
    return {"version":APP_VERSION,"items":items,"selected":list(selected),"limit":crypto_limit(user_id),"vip":is_vip(user_id),"error":error}


def _signal_public_teaser(snapshot):
    """Non-actionable public preview: real state/quality, without entry/SL/targets or deep indicators."""
    if not isinstance(snapshot,dict):
        return {"ok":False,"error":"market_unavailable","locked":True}
    keep=("ok","error","detail","asset","label","symbol","side","score","data_quality","price","source","updated_at")
    out={k:snapshot.get(k) for k in keep if k in snapshot}
    out["locked"]=True
    out["note"]="جزئیات ورود، حد ضرر، هدف‌ها و تحلیل فنی کامل برای کاربران VIP فعال است."
    return out


def _crypto_asset_payload(user_id, asset_key):
    if asset_key not in SUPPORTED_CRYPTO: return {"error":"invalid_asset"},400
    tickers,_,err=_crypto_tickers(); t=tickers.get(asset_key)
    if not t: return {"error":"market_unavailable","detail":err},503
    vip=is_vip(user_id)
    snap=crypto_signal_snapshot_cached(asset_key,600)
    if snap is None:
        request_signal_snapshot_background(asset_key)
        snap={"ok":False,"error":"warming_up","asset":asset_key,"label":SUPPORTED_CRYPTO[asset_key]["label"],"symbol":SUPPORTED_CRYPTO[asset_key]["symbol"],"price":t.get("price"),"source":t.get("source"),"updated_at":_utc_now()}
    if not vip:
        snap=_signal_public_teaser(snap)
    return {"version":APP_VERSION,"vip":vip,"ticker":t,"signal":snap,"selected":asset_key in set(crypto_watchlist(user_id))},200


def _crypto_candles_payload(user_id, asset_key, timeframe):
    tf=str(timeframe or "1h").lower(); mapping={"15m":"15m","1h":"1h","4h":"4h","1d":"1d"}
    if tf not in mapping or asset_key not in SUPPORTED_CRYPTO: return {"error":"invalid_request"},400
    if tf in {"4h","1d"} and not is_vip(user_id): return {"error":"vip_required"},403
    rows,source=_crypto_klines(asset_key,mapping[tf],240)
    if not rows: return {"error":"market_unavailable","detail":source},503
    candles=[{"t":int(x["open_time"]//1000),"o":x["o"],"h":x["h"],"l":x["l"],"c":x["c"],"v":x["v"],"gap":False} for x in rows]
    return {"version":APP_VERSION,"asset":asset_key,"label":SUPPORTED_CRYPTO[asset_key]["label"],"timeframe":tf,"candles":candles[-MINIAPP_MAX_CANDLES:],"source":"Binance public OHLCV","note":"کندل‌ها مستقیماً از OHLCV عمومی صرافی دریافت شده‌اند؛ در صورت نبود داده، نمودار ساختگی نمایش داده نمی‌شود."},200


def _signals_payload(user_id):
    """Fast signal dashboard from background-refreshed snapshots.

    The HTTP request never fans out into dozens of exchange requests. Missing
    snapshots are warmed asynchronously and the UI receives an explicit
    warming-up state instead of timing out.
    """
    vip=is_vip(user_id)
    selected=crypto_watchlist(user_id) or list(DEFAULT_CRYPTO_KEYS[:crypto_limit(user_id)])
    keys=(selected[:crypto_limit(user_id)] if vip else selected[:1])
    rows=[]
    for key in keys:
        snap=crypto_signal_snapshot_cached(key,600)
        if snap is None:
            request_signal_snapshot_background(key)
            spec=SUPPORTED_CRYPTO.get(key) or {}
            snap={"ok":False,"error":"warming_up","asset":key,"label":spec.get("label",key),"symbol":spec.get("symbol",key),"detail":"تحلیل در پس‌زمینه در حال آماده‌سازی است"}
        rows.append(snap if vip else _signal_public_teaser(snap))
    return {"version":APP_VERSION,"vip":vip,"items":rows,"performance":signal_performance(30),"min_quality":SIGNAL_MIN_DATA_QUALITY,"min_score":SIGNAL_MIN_SCORE,"free_note":None if vip else "نسخه رایگان یک نمای کلی واقعی نشان می‌دهد؛ محدوده ورود، اهداف، حد ضرر و اسکن کامل بازار مخصوص VIP است."},200

def _glossary_payload():
    return {"version":APP_VERSION,"items":[{"key":k,"title":v[0],"description":v[1]} for k,v in GLOSSARY.items()],"faq":[{"q":q,"a":a} for q,a in FAQ_ITEMS]}

MINIAPP_HTML = base64.b64decode("PCFkb2N0eXBlIGh0bWw+PGh0bWwgbGFuZz0iZmEiIGRpcj0icnRsIj48aGVhZD48bWV0YSBjaGFyc2V0PSJ1dGYtOCI+PG1ldGEgbmFtZT0idmlld3BvcnQiIGNvbnRlbnQ9IndpZHRoPWRldmljZS13aWR0aCxpbml0aWFsLXNjYWxlPTEsbWF4aW11bS1zY2FsZT0xLHVzZXItc2NhbGFibGU9bm8iPjx0aXRsZT7Yt9mE2KfbjNin2LE8L3RpdGxlPjxzY3JpcHQgc3JjPSJodHRwczovL3RlbGVncmFtLm9yZy9qcy90ZWxlZ3JhbS13ZWItYXBwLmpzIj48L3NjcmlwdD48c3R5bGU+Cjpyb290ey0tYmc6IzA4MDgwODstLWNhcmQ6IzE1MTUxNTstLWNhcmQyOiMxYjFiMWI7LS1nb2xkOiNlM2IzNDE7LS1ncmVlbjojMjhkMTdjOy0tcmVkOiNmZjRkNTU7LS10ZXh0OiNmZmY7LS1tdXRlZDojYWFhOy0tbGluZTojMmIyYjJiOy0tc29mdDojMTExfS5saWdodHstLWJnOiNmN2ZhZmY7LS1jYXJkOiNmZmY7LS1jYXJkMjojZjJmN2ZmOy0tZ29sZDojMDk2OWVmOy0tZ3JlZW46IzA3OTQ1NTstLXJlZDojZDkyZDIwOy0tdGV4dDojMTAyMTNkOy0tbXV0ZWQ6IzY0NzQ4YjstLWxpbmU6I2RjZThmNzstLXNvZnQ6I2Y2ZjlmZH0qe2JveC1zaXppbmc6Ym9yZGVyLWJveH1ib2R5e21hcmdpbjowO2JhY2tncm91bmQ6dmFyKC0tYmcpO2NvbG9yOnZhcigtLXRleHQpO2ZvbnQtZmFtaWx5OlRhaG9tYSxBcmlhbCxzYW5zLXNlcmlmO3RyYW5zaXRpb246LjJzfS53cmFwe21heC13aWR0aDo5NDBweDttYXJnaW46YXV0bztwYWRkaW5nOjE2cHggMTRweCA5MnB4fS5jb21wYWN0IC5jYXJkLC5jb21wYWN0IC5oZXJvLC5jb21wYWN0IC5yb3d7cGFkZGluZzo5cHh9LmJyYW5ke2Rpc3BsYXk6ZmxleDthbGlnbi1pdGVtczpjZW50ZXI7anVzdGlmeS1jb250ZW50OnNwYWNlLWJldHdlZW47bWFyZ2luOjRweCAwIDE0cHg7Z2FwOjhweH0uYnJhbmQgaDF7bWFyZ2luOjA7Y29sb3I6dmFyKC0tZ29sZCk7Zm9udC1zaXplOjI3cHh9LmJyYW5kQWN0aW9uc3tkaXNwbGF5OmZsZXg7Z2FwOjdweDthbGlnbi1pdGVtczpjZW50ZXJ9LnBpbGx7Ym9yZGVyOjFweCBzb2xpZCAjODA2NTFjNTU7YmFja2dyb3VuZDpjb2xvci1taXgoaW4gc3JnYix2YXIoLS1nb2xkKSAxMiUsdHJhbnNwYXJlbnQpO2NvbG9yOnZhcigtLWdvbGQpO3BhZGRpbmc6NnB4IDEwcHg7Ym9yZGVyLXJhZGl1czoxMnB4O2ZvbnQtc2l6ZToxMnB4fS5pY29uYnRue2JvcmRlcjoxcHggc29saWQgdmFyKC0tbGluZSk7YmFja2dyb3VuZDp2YXIoLS1jYXJkKTtjb2xvcjp2YXIoLS10ZXh0KTt3aWR0aDozNnB4O2hlaWdodDozNnB4O2JvcmRlci1yYWRpdXM6MTFweH0uaGVybywuY2FyZHtiYWNrZ3JvdW5kOnZhcigtLWNhcmQpO2JvcmRlcjoxcHggc29saWQgdmFyKC0tbGluZSk7Ym9yZGVyLXJhZGl1czoxOHB4O3BhZGRpbmc6MTVweH0uaGVyb3tib3JkZXItY29sb3I6IzgwNjUxYzY2O2JhY2tncm91bmQ6bGluZWFyLWdyYWRpZW50KDE0NWRlZyxjb2xvci1taXgoaW4gc3JnYix2YXIoLS1nb2xkKSAxMCUsdmFyKC0tY2FyZCkpLHZhcigtLWNhcmQpKX0uaGVyb1RvcHtkaXNwbGF5OmZsZXg7anVzdGlmeS1jb250ZW50OnNwYWNlLWJldHdlZW47Z2FwOjEwcHg7YWxpZ24taXRlbXM6Y2VudGVyfS5zY29yZXtmb250LXNpemU6MzVweDtmb250LXdlaWdodDo5MDB9LmdvbGR7Y29sb3I6dmFyKC0tZ29sZCl9LnVwe2NvbG9yOnZhcigtLWdyZWVuKX0uZG93bntjb2xvcjp2YXIoLS1yZWQpfS5mbGF0e2NvbG9yOnZhcigtLW11dGVkKX0ubXV0ZWR7Y29sb3I6dmFyKC0tbXV0ZWQpfS5zZWN0aW9ue2ZvbnQtc2l6ZToxOXB4O2ZvbnQtd2VpZ2h0OjgwMDtjb2xvcjp2YXIoLS1nb2xkKTttYXJnaW46MjJweCAycHggMTBweH0uZ3JpZHtkaXNwbGF5OmdyaWQ7Z3JpZC10ZW1wbGF0ZS1jb2x1bW5zOnJlcGVhdCgyLDFmcik7Z2FwOjEwcHh9LnByaWNle2ZvbnQtc2l6ZToyMHB4O2ZvbnQtd2VpZ2h0OjgwMDttYXJnaW46N3B4IDB9LmNoYW5nZXtmb250LXNpemU6MTRweH0ubGlzdHtkaXNwbGF5OmZsZXg7ZmxleC1kaXJlY3Rpb246Y29sdW1uO2dhcDo4cHh9LnJvd3tiYWNrZ3JvdW5kOnZhcigtLWNhcmQpO2JvcmRlcjoxcHggc29saWQgdmFyKC0tbGluZSk7Ym9yZGVyLXJhZGl1czoxNHB4O3BhZGRpbmc6MTJweDtkaXNwbGF5OmZsZXg7YWxpZ24taXRlbXM6Y2VudGVyO2p1c3RpZnktY29udGVudDpzcGFjZS1iZXR3ZWVuO2dhcDo4cHh9LmNsaWNre2N1cnNvcjpwb2ludGVyfS5yYW5re3dpZHRoOjI4cHg7aGVpZ2h0OjI4cHg7Ym9yZGVyLXJhZGl1czo5cHg7YmFja2dyb3VuZDpjb2xvci1taXgoaW4gc3JnYix2YXIoLS1nb2xkKSAxNiUsdmFyKC0tY2FyZCkpO2NvbG9yOnZhcigtLWdvbGQpO2Rpc3BsYXk6Z3JpZDtwbGFjZS1pdGVtczpjZW50ZXI7Zm9udC13ZWlnaHQ6ODAwfS50YWJze2Rpc3BsYXk6ZmxleDtnYXA6N3B4O292ZXJmbG93OmF1dG87cGFkZGluZy1ib3R0b206NHB4fS50YWJ7Ym9yZGVyOjFweCBzb2xpZCB2YXIoLS1saW5lKTtiYWNrZ3JvdW5kOnZhcigtLWNhcmQyKTtjb2xvcjp2YXIoLS10ZXh0KTtwYWRkaW5nOjhweCAxMnB4O2JvcmRlci1yYWRpdXM6MTJweDt3aGl0ZS1zcGFjZTpub3dyYXB9LnRhYi5hY3RpdmV7Ym9yZGVyLWNvbG9yOnZhcigtLWdvbGQpO2NvbG9yOnZhcigtLWdvbGQpfS5oZWF0e2Rpc3BsYXk6Z3JpZDtncmlkLXRlbXBsYXRlLWNvbHVtbnM6cmVwZWF0KDMsMWZyKTtnYXA6OHB4fS5oZWF0IC5jYXJke3BhZGRpbmc6MTBweDt0ZXh0LWFsaWduOmNlbnRlcn0uaGVhdFVwe2JvcmRlci1jb2xvcjojMWU4YjU4O2JhY2tncm91bmQ6Y29sb3ItbWl4KGluIHNyZ2IsdmFyKC0tZ3JlZW4pIDExJSx2YXIoLS1jYXJkKSl9LmhlYXREb3due2JvcmRlci1jb2xvcjojOWUzOTQyO2JhY2tncm91bmQ6Y29sb3ItbWl4KGluIHNyZ2IsdmFyKC0tcmVkKSAxMCUsdmFyKC0tY2FyZCkpfS5iYXJ7aGVpZ2h0OjZweDtiYWNrZ3JvdW5kOnZhcigtLWxpbmUpO2JvcmRlci1yYWRpdXM6OTlweDtvdmVyZmxvdzpoaWRkZW59LmJhcj5pe2Rpc3BsYXk6YmxvY2s7aGVpZ2h0OjEwMCU7YmFja2dyb3VuZDp2YXIoLS1nb2xkKTtib3JkZXItcmFkaXVzOjk5cHh9LmxvY2t7Ym9yZGVyOjFweCBkYXNoZWQgIzk0NzUyMjtjb2xvcjp2YXIoLS1nb2xkKTtiYWNrZ3JvdW5kOmNvbG9yLW1peChpbiBzcmdiLHZhcigtLWdvbGQpIDglLHZhcigtLWNhcmQpKTtib3JkZXItcmFkaXVzOjE0cHg7cGFkZGluZzoxNHB4O3RleHQtYWxpZ246Y2VudGVyfS5idG57Ym9yZGVyOjA7Ym9yZGVyLXJhZGl1czoxMnB4O3BhZGRpbmc6MTFweCAxNHB4O2ZvbnQtd2VpZ2h0OjgwMDtiYWNrZ3JvdW5kOnZhcigtLWdvbGQpO2NvbG9yOiMxNzEyMGF9LmJ0bi5kYXJre2JhY2tncm91bmQ6dmFyKC0tY2FyZDIpO2NvbG9yOnZhcigtLXRleHQpO2JvcmRlcjoxcHggc29saWQgdmFyKC0tbGluZSl9LnZpZXd7ZGlzcGxheTpub25lfS52aWV3LmFjdGl2ZXtkaXNwbGF5OmJsb2NrfWNhbnZhc3t3aWR0aDoxMDAlO2hlaWdodDoyNTBweDtiYWNrZ3JvdW5kOnZhcigtLXNvZnQpO2JvcmRlcjoxcHggc29saWQgdmFyKC0tbGluZSk7Ym9yZGVyLXJhZGl1czoxNHB4fS5tZXRyaWNze2Rpc3BsYXk6Z3JpZDtncmlkLXRlbXBsYXRlLWNvbHVtbnM6cmVwZWF0KDMsMWZyKTtnYXA6OHB4fS5tZXRyaWN7YmFja2dyb3VuZDp2YXIoLS1zb2Z0KTtib3JkZXI6MXB4IHNvbGlkIHZhcigtLWxpbmUpO2JvcmRlci1yYWRpdXM6MTJweDtwYWRkaW5nOjEwcHg7dGV4dC1hbGlnbjpjZW50ZXJ9Lm1ldHJpYyBie2Rpc3BsYXk6YmxvY2s7bWFyZ2luLXRvcDo1cHh9LmdhdWdle3dpZHRoOjI0MHB4O21heC13aWR0aDoxMDAlO21hcmdpbjoxMnB4IGF1dG8gMnB4O3RleHQtYWxpZ246Y2VudGVyfS5nYXVnZSBzdmd7ZGlzcGxheTpibG9jazt3aWR0aDoxMDAlO2hlaWdodDphdXRvfS5nYXVnZVZhbHVle2ZvbnQtc2l6ZToyOHB4O2ZvbnQtd2VpZ2h0OjkwMDttYXJnaW4tdG9wOi01cHh9LmdhdWdlTGFiZWx7Zm9udC1zaXplOjEycHg7Y29sb3I6dmFyKC0tbXV0ZWQpO21hcmdpbi10b3A6MnB4fS5nYXVnZVNjYWxle2ZvbnQtc2l6ZToxMHB4O2ZpbGw6dmFyKC0tbXV0ZWQpfS5jb3ZlcmFnZXtkaXNwbGF5OmZsZXg7Z2FwOjdweDtmbGV4LXdyYXA6d3JhcDttYXJnaW4tdG9wOjhweH0uY292ZXJhZ2Ugc3Bhbntib3JkZXI6MXB4IHNvbGlkIHZhcigtLWxpbmUpO2JhY2tncm91bmQ6dmFyKC0tY2FyZDIpO2JvcmRlci1yYWRpdXM6MTBweDtwYWRkaW5nOjVweCA4cHg7Zm9udC1zaXplOjExcHh9LnNwYXJre3dpZHRoOjExMHB4O2hlaWdodDozNHB4O2JvcmRlcjowO2JhY2tncm91bmQ6dHJhbnNwYXJlbnR9LmFzc2V0SHVie2Rpc3BsYXk6Z3JpZDtncmlkLXRlbXBsYXRlLWNvbHVtbnM6cmVwZWF0KDIsMWZyKTtnYXA6OXB4fS5hc3NldENoaXB7YmFja2dyb3VuZDp2YXIoLS1jYXJkKTtib3JkZXI6MXB4IHNvbGlkIHZhcigtLWxpbmUpO2JvcmRlci1yYWRpdXM6MTRweDtwYWRkaW5nOjEycHh9LnNlbGVjdG9ye3dpZHRoOjEwMCU7YmFja2dyb3VuZDp2YXIoLS1jYXJkMik7Y29sb3I6dmFyKC0tdGV4dCk7Ym9yZGVyOjFweCBzb2xpZCB2YXIoLS1saW5lKTtib3JkZXItcmFkaXVzOjEycHg7cGFkZGluZzoxMHB4fS5zZXR0aW5nc0dyaWR7ZGlzcGxheTpncmlkO2dhcDo5cHh9LnNldHRpbmd7ZGlzcGxheTpmbGV4O2p1c3RpZnktY29udGVudDpzcGFjZS1iZXR3ZWVuO2FsaWduLWl0ZW1zOmNlbnRlcjtiYWNrZ3JvdW5kOnZhcigtLWNhcmQpO2JvcmRlcjoxcHggc29saWQgdmFyKC0tbGluZSk7Ym9yZGVyLXJhZGl1czoxM3B4O3BhZGRpbmc6MTJweH0ubmF2e3Bvc2l0aW9uOmZpeGVkO2JvdHRvbTowO2xlZnQ6MDtyaWdodDowO2JhY2tncm91bmQ6Y29sb3ItbWl4KGluIHNyZ2IsdmFyKC0tY2FyZCkgOTQlLHRyYW5zcGFyZW50KTtib3JkZXItdG9wOjFweCBzb2xpZCB2YXIoLS1saW5lKTtkaXNwbGF5OmZsZXg7anVzdGlmeS1jb250ZW50OmNlbnRlcjt6LWluZGV4OjV9Lm5hdmlue3dpZHRoOm1pbig5NDBweCwxMDAlKTtkaXNwbGF5OmdyaWQ7Z3JpZC10ZW1wbGF0ZS1jb2x1bW5zOnJlcGVhdCg1LDFmcil9Lm5hdiBidXR0b257YmFja2dyb3VuZDpub25lO2JvcmRlcjowO2NvbG9yOnZhcigtLW11dGVkKTtwYWRkaW5nOjExcHggM3B4O2ZvbnQtc2l6ZToxMXB4fS5uYXYgYnV0dG9uLmFjdGl2ZXtjb2xvcjp2YXIoLS1nb2xkKX0uZW1wdHl7Y29sb3I6dmFyKC0tbXV0ZWQpO3RleHQtYWxpZ246Y2VudGVyO3BhZGRpbmc6MjBweH0udGlueXtmb250LXNpemU6MTFweH0uZmxleHtkaXNwbGF5OmZsZXg7Z2FwOjhweDthbGlnbi1pdGVtczpjZW50ZXI7anVzdGlmeS1jb250ZW50OnNwYWNlLWJldHdlZW59LnRvb2xzNntkaXNwbGF5OmdyaWQ7Z3JpZC10ZW1wbGF0ZS1jb2x1bW5zOnJlcGVhdCgyLDFmcik7Z2FwOjlweH0uaGlkZXtkaXNwbGF5Om5vbmUhaW1wb3J0YW50fUBtZWRpYShtaW4td2lkdGg6NzAwcHgpey5ncmlke2dyaWQtdGVtcGxhdGUtY29sdW1uczpyZXBlYXQoMywxZnIpfS5oZWF0e2dyaWQtdGVtcGxhdGUtY29sdW1uczpyZXBlYXQoNCwxZnIpfS5hc3NldEh1YntncmlkLXRlbXBsYXRlLWNvbHVtbnM6cmVwZWF0KDQsMWZyKX0udG9vbHM2e2dyaWQtdGVtcGxhdGUtY29sdW1uczpyZXBlYXQoMywxZnIpfX0KPC9zdHlsZT48L2hlYWQ+PGJvZHk+PGRpdiBjbGFzcz0id3JhcCIgaWQ9ImFwcFdyYXAiPjxkaXYgY2xhc3M9ImJyYW5kIj48ZGl2PjxoMT7Yt9mE2KfbjNin2LE8L2gxPjxkaXYgY2xhc3M9Im11dGVkIHRpbnkiPtiv2LPYqtuM2KfYsSDZh9mI2LTZhdmG2K8g2KjYp9iy2KfYsSDigKIg2LPZgduM2K/YjCDYotio24wg2Ygg2LfZhNin24zbjDwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImJyYW5kQWN0aW9ucyI+PGJ1dHRvbiBjbGFzcz0iaWNvbmJ0biIgb25jbGljaz0idG9nZ2xlVGhlbWUoKSIgaWQ9InRoZW1lQnRuIj7imIDvuI88L2J1dHRvbj48YnV0dG9uIGNsYXNzPSJpY29uYnRuIiBvbmNsaWNrPSJnbygnc2V0dGluZ3MnKSI+4pqZ77iPPC9idXR0b24+PHNwYW4gY2xhc3M9InBpbGwiIGlkPSJ0aWVyIj4uLi48L3NwYW4+PC9kaXY+PC9kaXY+CjxkaXYgaWQ9InB1bHNlIiBjbGFzcz0idmlldyBhY3RpdmUiPjxkaXYgY2xhc3M9Imhlcm8iPjxkaXYgY2xhc3M9Imhlcm9Ub3AiPjxkaXY+PGRpdiBjbGFzcz0ibXV0ZWQiPtmG2KjYtiDYqNin2LLYp9ixPC9kaXY+PGRpdiBpZD0icHVsc2VTdGF0ZSIgY2xhc3M9InByaWNlIj7igJQ8L2Rpdj48L2Rpdj48ZGl2PjxzcGFuIGlkPSJwdWxzZVNjb3JlIiBjbGFzcz0ic2NvcmUgZ29sZCI+4oCUPC9zcGFuPjxzcGFuIGNsYXNzPSJtdXRlZCI+LzEwMDwvc3Bhbj48L2Rpdj48L2Rpdj48ZGl2IGNsYXNzPSJiYXIiPjxpIGlkPSJwdWxzZUJhciIgc3R5bGU9IndpZHRoOjAiPjwvaT48L2Rpdj48ZGl2IGlkPSJwdWxzZU1ldGEiIGNsYXNzPSJtdXRlZCB0aW55IiBzdHlsZT0ibWFyZ2luLXRvcDo5cHgiPjwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9InNlY3Rpb24iPtmC24zZhdiq4oCM2YfYp9uMINmE2K3YuNmH4oCM2KfbjDwvZGl2PjxkaXYgaWQ9InByaWNlcyIgY2xhc3M9ImdyaWQiPjwvZGl2PjxkaXYgY2xhc3M9InNlY3Rpb24iPtio24zYtNiq2LHbjNmGINit2LHaqdiqPC9kaXY+PGRpdiBpZD0ibW92ZXJzIiBjbGFzcz0ibGlzdCI+PC9kaXY+PC9kaXY+CjxkaXYgaWQ9InNjYW5uZXIiIGNsYXNzPSJ2aWV3Ij48ZGl2IGNsYXNzPSJzZWN0aW9uIj7wn46vINmB2LHYtdiq4oCM2YfYp9uMINio2KfYstin2LE8L2Rpdj48ZGl2IGlkPSJzY2FubmVyQm9keSI+PC9kaXY+PC9kaXY+CjxkaXYgaWQ9ImhlYXRtYXAiIGNsYXNzPSJ2aWV3Ij48ZGl2IGNsYXNzPSJzZWN0aW9uIj7wn5e6INmG2YLYtNmHINio2KfYstin2LE8L2Rpdj48ZGl2IGlkPSJoZWF0Qm9keSIgY2xhc3M9ImhlYXQiPjwvZGl2PjwvZGl2Pgo8ZGl2IGlkPSJhc3NldEh1YlZpZXciIGNsYXNzPSJ2aWV3Ij48ZGl2IGNsYXNzPSJzZWN0aW9uIj7wn5OIINmF2LHaqdiyINiv2KfYsdin24zbjOKAjNmH2Kc8L2Rpdj48ZGl2IGNsYXNzPSJtdXRlZCB0aW55IiBzdHlsZT0ibWFyZ2luLWJvdHRvbToxMHB4Ij7Zh9ixINiv2KfYsdin24zbjCDYrNiv24zYr9uMINqp2Ycg2KjZhyDZh9iz2KrZhyDYt9mE2KfbjNin2LEg2KfYttin2YHZhyDYtNmI2K/YjCDYp9uM2YbYrNinINiu2YjYr9qp2KfYsSDYuNin2YfYsSDZhduM4oCM2LTZiNivLjwvZGl2PjxkaXYgaWQ9ImFzc2V0SHViIiBjbGFzcz0iYXNzZXRIdWIiPjwvZGl2PjwvZGl2Pgo8ZGl2IGlkPSJhc3NldCIgY2xhc3M9InZpZXciPjxkaXYgY2xhc3M9ImZsZXgiPjxidXR0b24gY2xhc3M9ImJ0biBkYXJrIiBvbmNsaWNrPSJnbygnYXNzZXRIdWJWaWV3JykiPuKGqSDYqNin2LLar9i02Ko8L2J1dHRvbj48c2VsZWN0IGlkPSJhc3NldFNlbGVjdG9yIiBjbGFzcz0ic2VsZWN0b3IiIG9uY2hhbmdlPSJvcGVuQXNzZXQodGhpcy52YWx1ZSkiPjwvc2VsZWN0PjwvZGl2PjxkaXYgaWQ9ImFzc2V0VGl0bGUiIGNsYXNzPSJzZWN0aW9uIj48L2Rpdj48ZGl2IGlkPSJhc3NldEJvZHkiPjwvZGl2PjwvZGl2Pgo8ZGl2IGlkPSJteV9tYXJrZXQiIGNsYXNzPSJ2aWV3Ij48ZGl2IGNsYXNzPSJzZWN0aW9uIj7irZAg2KjYp9iy2KfYsSDZhdmGPC9kaXY+PGRpdiBjbGFzcz0ibXV0ZWQgdGlueSI+2K/Yp9ix2KfbjNuM4oCM2YfYp9uMINiz2YbYrNin2YLigIzYtNiv2Ycg2LTZhdin2Jsg2KfYsiDYqtmG2LjbjNmF2KfYqiDZgtin2KjZhCDZiNuM2LHYp9uM2LQg2KfYs9iqLjwvZGl2PjxkaXYgaWQ9Im15TWFya2V0Qm9keSIgY2xhc3M9Imxpc3QiIHN0eWxlPSJtYXJnaW4tdG9wOjEycHgiPjwvZGl2PjwvZGl2Pgo8ZGl2IGlkPSJzaWduYWxzVmlldyIgY2xhc3M9InZpZXciPjxkaXYgY2xhc3M9InNlY3Rpb24iPvCfjq8g2YHYsdi12KrigIzZh9in24wg2K7YsduM2K8g2Ygg2YHYsdmI2LQ8L2Rpdj48ZGl2IGNsYXNzPSJtdXRlZCB0aW55IiBzdHlsZT0ibWFyZ2luLWJvdHRvbToxMHB4Ij7Yr9in2K/ZhyDZiNin2YLYuduMINio2KfYstin2LHYmyDZgdmC2Lcg2YXZiNmC2LnbjNiq4oCM2YfYp9uMINiq2KPbjNuM2K/YtNiv2Ycg2YbZhdin24zYtCDYr9in2K/ZhyDZhduM4oCM2LTZiNmG2K8uPC9kaXY+PGRpdiBpZD0ic2lnbmFsc0JvZHkiPjwvZGl2PjwvZGl2Pgo8ZGl2IGlkPSJjcnlwdG9WaWV3IiBjbGFzcz0idmlldyI+PGRpdiBjbGFzcz0ic2VjdGlvbiI+4oK/INqp2LHbjNm+2KrZiNmH2KfbjCDZhdmGPC9kaXY+PGRpdiBjbGFzcz0ibXV0ZWQgdGlueSIgc3R5bGU9Im1hcmdpbi1ib3R0b206MTBweCI+2KfYsdiy2YfYp9uMINiv2YTYrtmI2KfZh9iqINix2Kcg2KfZhtiq2K7Yp9ioINqp2YbYmyDYs9mC2YEgRnJlZS9WSVAg2K7ZiNiv2qnYp9ixINin2LnZhdin2YQg2YXbjOKAjNi02YjYry48L2Rpdj48ZGl2IGlkPSJjcnlwdG9Cb2R5Ij48L2Rpdj48L2Rpdj4KPGRpdiBpZD0ibGVhcm5WaWV3IiBjbGFzcz0idmlldyI+PGRpdiBjbGFzcz0ic2VjdGlvbiI+8J+TmCDYsdin2YfZhtmF2KfbjCDYqNin2LLYp9ixPC9kaXY+PGRpdiBpZD0ibGVhcm5Cb2R5Ij48L2Rpdj48L2Rpdj4KPGRpdiBpZD0ibW9yZSIgY2xhc3M9InZpZXciPjxkaXYgY2xhc3M9InNlY3Rpb24iPtin2KjYstin2LHZh9in24wg2K3YsdmB2YfigIzYp9uMPC9kaXY+PGRpdiBjbGFzcz0idG9vbHM2Ij48ZGl2IGNsYXNzPSJjYXJkIGNsaWNrIiBvbmNsaWNrPSJnbygnc2Nhbm5lcicpIj7wn46vPGJyPjxiPtmB2LHYtdiq4oCM2YfYp9uMINio2KfYstin2LE8L2I+PGRpdiBjbGFzcz0idGlueSBtdXRlZCI+2YjbjNqY2Yc8L2Rpdj48L2Rpdj48ZGl2IGNsYXNzPSJjYXJkIGNsaWNrIiBvbmNsaWNrPSJnbygnaGVhdG1hcCcpIj7ilqY8YnI+PGI+2YbZgti02Ycg2KjYp9iy2KfYsTwvYj48ZGl2IGNsYXNzPSJ0aW55IG11dGVkIj7YqNin2LLYp9ixPC9kaXY+PC9kaXY+PGRpdiBjbGFzcz0iY2FyZCBjbGljayIgb25jbGljaz0ibG9hZExlYXJuKCkiPvCfk5g8YnI+PGI+2LHYp9mH2YbZhdin24wg2KfYtdi32YTYp9it2KfYqjwvYj48ZGl2IGNsYXNzPSJ0aW55IG11dGVkIj7YotmF2YjYsti0PC9kaXY+PC9kaXY+PGRpdiBjbGFzcz0iY2FyZCBjbGljayIgb25jbGljaz0ibG9hZEZhaXIoKSI+8J+rpzxicj48Yj7Yrdio2KfYqCDZiCDYp9ix2LLYtCDZhdmG2LXZgdin2YbZhzwvYj48ZGl2IGNsYXNzPSJ0aW55IG11dGVkIj7ZiNuM2pjZhzwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImNhcmQgY2xpY2siIG9uY2xpY2s9ImxvYWRSc2lNYXAoKSI+8J+nrTxicj48Yj7ZhtmC2LTZhyDZgtiv2LHYqiDYrdix2qnYqiAoUlNJKTwvYj48ZGl2IGNsYXNzPSJ0aW55IG11dGVkIj7ZiNuM2pjZhzwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImNhcmQgY2xpY2siIG9uY2xpY2s9Im9wZW5CYWNrdGVzdCgpIj7wn6eqPGJyPjxiPtii2LLZhdin24zYtCDYqtin2LHbjNiu24w8L2I+PGRpdiBjbGFzcz0idGlueSBtdXRlZCI+2YjbjNqY2Yc8L2Rpdj48L2Rpdj48ZGl2IGNsYXNzPSJjYXJkIGNsaWNrIiBvbmNsaWNrPSJsb2FkQWN0aXZpdHkoKSI+8J+TnDxicj48Yj7Zgdi52KfZhNuM2Kog2YXZhjwvYj48ZGl2IGNsYXNzPSJ0aW55IG11dGVkIj7Yqtin2LHbjNiu2obZhzwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImNhcmQgY2xpY2siIG9uY2xpY2s9ImxvYWRNZWx0ZWRQcm8oKSI+8J+UpTxicj48Yj7Zhdix2qnYsiDYrdix2YHZh+KAjNin24wg2KLYqOKAjNi02K/ZhzwvYj48ZGl2IGNsYXNzPSJ0aW55IG11dGVkIj7ZiNuM2pjZhzwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImNhcmQgY2xpY2siIG9uY2xpY2s9ImdvKCdteV9tYXJrZXQnKSI+4q2QPGJyPjxiPtio2KfYstin2LEg2YXZhjwvYj48ZGl2IGNsYXNzPSJ0aW55IG11dGVkIj7YtNiu2LXbjDwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImNhcmQgY2xpY2siIG9uY2xpY2s9ImdvKCdhc3NldEh1YlZpZXcnKSI+8J+TiDxicj48Yj7YrNiy2KbbjNin2Kog2YfYsSDYr9in2LHYp9uM24w8L2I+PGRpdiBjbGFzcz0idGlueSBtdXRlZCI+2YLYr9ix2KogKyDZhtmF2YjYr9in2LE8L2Rpdj48L2Rpdj48ZGl2IGNsYXNzPSJjYXJkIGNsaWNrIiBvbmNsaWNrPSJvcGVuU21hcnRBbGVydCgpIj7wn5qoPGJyPjxiPtmH2LTYr9in2LEgKyDYqti12YjbjNixINmI2LbYuduM2Ko8L2I+PGRpdiBjbGFzcz0idGlueSBtdXRlZCI+2YjbjNqY2Yc8L2Rpdj48L2Rpdj48ZGl2IGNsYXNzPSJjYXJkIGNsaWNrIiBvbmNsaWNrPSJnbygnc2V0dGluZ3MnKSI+8J+OqDxicj48Yj7YtNiu2LXbjOKAjNiz2KfYstuMPC9iPjxkaXYgY2xhc3M9InRpbnkgbXV0ZWQiPtiq2YUg2Ygg2obbjNiv2YXYp9mGPC9kaXY+PC9kaXY+PC9kaXY+PGRpdiBpZD0ibW9yZUJvZHkiIHN0eWxlPSJtYXJnaW4tdG9wOjEycHgiPjwvZGl2PjwvZGl2Pgo8ZGl2IGlkPSJzZXR0aW5ncyIgY2xhc3M9InZpZXciPjxkaXYgY2xhc3M9InNlY3Rpb24iPuKame+4jyDYtNiu2LXbjOKAjNiz2KfYstuMINmF24zZhtuM4oCM2KfZvjwvZGl2PjxkaXYgY2xhc3M9InNldHRpbmdzR3JpZCI+PGRpdiBjbGFzcz0ic2V0dGluZyI+PHNwYW4+2KrZhTwvc3Bhbj48c2VsZWN0IGlkPSJzZXRUaGVtZSIgY2xhc3M9InNlbGVjdG9yIiBzdHlsZT0id2lkdGg6MTUwcHgiPjxvcHRpb24gdmFsdWU9ImRhcmsiPtiq24zYsdmHPC9vcHRpb24+PG9wdGlvbiB2YWx1ZT0ibGlnaHQiPtix2YjYtNmGPC9vcHRpb24+PC9zZWxlY3Q+PC9kaXY+PGRpdiBjbGFzcz0ic2V0dGluZyI+PHNwYW4+2LXZgdit2Ycg2LTYsdmI2Lk8L3NwYW4+PHNlbGVjdCBpZD0ic2V0SG9tZSIgY2xhc3M9InNlbGVjdG9yIiBzdHlsZT0id2lkdGg6MTUwcHgiPjxvcHRpb24gdmFsdWU9InB1bHNlIj7Zvtin2YTYszwvb3B0aW9uPjxvcHRpb24gdmFsdWU9ImhlYXRtYXAiPtmG2YLYtNmHINio2KfYstin2LE8L29wdGlvbj48b3B0aW9uIHZhbHVlPSJteV9tYXJrZXQiPtio2KfYstin2LEg2YXZhjwvb3B0aW9uPjwvc2VsZWN0PjwvZGl2PjxkaXYgY2xhc3M9InNldHRpbmciPjxzcGFuPtit2KfZhNiqINmB2LTYsdiv2Yc8L3NwYW4+PGlucHV0IGlkPSJzZXRDb21wYWN0IiB0eXBlPSJjaGVja2JveCI+PC9kaXY+PGRpdiBjbGFzcz0ic2V0dGluZyI+PHNwYW4+2YbZhdin24zYtCBSU0k8L3NwYW4+PGlucHV0IGlkPSJzZXRSc2kiIHR5cGU9ImNoZWNrYm94Ij48L2Rpdj48ZGl2IGNsYXNzPSJzZXR0aW5nIj48c3Bhbj7ZhtmF2KfbjNi0IEVNQTwvc3Bhbj48aW5wdXQgaWQ9InNldEVtYSIgdHlwZT0iY2hlY2tib3giPjwvZGl2PjxkaXYgY2xhc3M9InNldHRpbmciPjxzcGFuPtmG2YXYp9uM2LQg2K3Zhdin24zYqi/ZhdmC2KfZiNmF2Ko8L3NwYW4+PGlucHV0IGlkPSJzZXRMZXZlbHMiIHR5cGU9ImNoZWNrYm94Ij48L2Rpdj48ZGl2IGNsYXNzPSJzZXR0aW5nIj48c3Bhbj7Yqtin24zZheKAjNmB2LHbjNmFINm+24zYtOKAjNmB2LHYtjwvc3Bhbj48c2VsZWN0IGlkPSJzZXRUZiIgY2xhc3M9InNlbGVjdG9yIiBzdHlsZT0id2lkdGg6MTUwcHgiPjxvcHRpb24+MjRIPC9vcHRpb24+PG9wdGlvbj4xSDwvb3B0aW9uPjxvcHRpb24+NEg8L29wdGlvbj48b3B0aW9uPjdEPC9vcHRpb24+PG9wdGlvbj4zMEQ8L29wdGlvbj48L3NlbGVjdD48L2Rpdj48L2Rpdj48ZGl2IGNsYXNzPSJzZWN0aW9uIj7Yr9in2LHYp9uM24zigIzZh9in24wg2LPZhtis2KfZguKAjNi02K/ZhzwvZGl2PjxkaXYgaWQ9InBpbkVkaXRvciIgY2xhc3M9ImFzc2V0SHViIj48L2Rpdj48YnV0dG9uIGNsYXNzPSJidG4iIHN0eWxlPSJ3aWR0aDoxMDAlO21hcmdpbi10b3A6MTVweCIgb25jbGljaz0ic2F2ZVNldHRpbmdzKCkiPtiw2K7bjNix2Ycg2KrZhti424zZhdin2Ko8L2J1dHRvbj48L2Rpdj4KPC9kaXY+PGRpdiBjbGFzcz0ibmF2Ij48ZGl2IGNsYXNzPSJuYXZpbiI+PGJ1dHRvbiBkYXRhLXY9InB1bHNlIiBjbGFzcz0iYWN0aXZlIiBvbmNsaWNrPSJnbygncHVsc2UnKSI+4peJPGJyPtm+2KfZhNizPC9idXR0b24+PGJ1dHRvbiBkYXRhLXY9InNpZ25hbHNWaWV3IiBvbmNsaWNrPSJsb2FkU2lnbmFscygpIj7wn46vPGJyPtiz24zar9mG2KfZhDwvYnV0dG9uPjxidXR0b24gZGF0YS12PSJjcnlwdG9WaWV3IiBvbmNsaWNrPSJsb2FkQ3J5cHRvKCkiPuKCvzxicj7aqdix24zZvtiq2Yg8L2J1dHRvbj48YnV0dG9uIGRhdGEtdj0iYXNzZXRIdWJWaWV3IiBvbmNsaWNrPSJnbygnYXNzZXRIdWJWaWV3JykiPvCfk4g8YnI+2K/Yp9ix2KfbjNuMPC9idXR0b24+PGJ1dHRvbiBkYXRhLXY9Im1vcmUiIG9uY2xpY2s9ImdvKCdtb3JlJykiPuKYsDxicj7YqNuM2LTYqtixPC9idXR0b24+PC9kaXY+PC9kaXY+CjxzY3JpcHQ+CmNvbnN0IHRnPXdpbmRvdy5UZWxlZ3JhbT8uV2ViQXBwO2lmKHRnKXt0Zy5yZWFkeSgpO3RnLmV4cGFuZCgpfWxldCBzdGF0ZT17b3ZlcnZpZXc6bnVsbCx2aXA6ZmFsc2Usc2Vzc2lvblJlYWR5OmZhbHNlLGFzc2V0Oidnb2xkMTgnLHByZWZzOnt0aGVtZTonbGlnaHQnLGhvbWU6J3B1bHNlJyxjb21wYWN0OmZhbHNlLHBpbm5lZDpbJ2dvbGQxOCcsJ21lbHRlZCcsJ3VzZCcsJ291bmNlJywnYnRjJ10sc2hvd19yc2k6dHJ1ZSxzaG93X2VtYTp0cnVlLHNob3dfbGV2ZWxzOnRydWUsZGVmYXVsdF90aW1lZnJhbWU6JzI0SCd9fTtjb25zdCAkPWlkPT5kb2N1bWVudC5nZXRFbGVtZW50QnlJZChpZCk7Y29uc3QgZXNjPXg9PlN0cmluZyh4Pz8nJykucmVwbGFjZSgvWyY8Pl0vZyxtPT4oeycmJzonJmFtcDsnLCc8JzonJmx0OycsJz4nOicmZ3Q7J31bbV0pKTtjb25zdCBmaW5pdGU9eD0+eCE9PW51bGwmJnghPT0nJyYmTnVtYmVyLmlzRmluaXRlKE51bWJlcih4KSk7Y29uc3QgZm10PXg9PmZpbml0ZSh4KT9OdW1iZXIoeCkudG9Mb2NhbGVTdHJpbmcoJ2VuLVVTJyx7bWF4aW11bUZyYWN0aW9uRGlnaXRzOjJ9KTon4oCUJztjb25zdCBwY3Q9eD0+ZmluaXRlKHgpP051bWJlcih4KS50b0ZpeGVkKDIpKyclJzon4oCUJztjb25zdCBjbHM9bj0+IWZpbml0ZShuKT8nZmxhdCc6TnVtYmVyKG4pPjA/J3VwJzpOdW1iZXIobik8MD8nZG93bic6J2ZsYXQnO2NvbnN0IGFycm93PW49PiFmaW5pdGUobik/J+KAoic6TnVtYmVyKG4pPjA/J+KWsic6TnVtYmVyKG4pPDA/J+KWvCc6J+KAoic7CmFzeW5jIGZ1bmN0aW9uIGFwaShyb3V0ZSxwPXt9LHRpbWVvdXRNcz0xMjAwMCl7Y29uc3QgY3RsPW5ldyBBYm9ydENvbnRyb2xsZXIoKSx0aW1lcj1zZXRUaW1lb3V0KCgpPT5jdGwuYWJvcnQoKSx0aW1lb3V0TXMpO3RyeXtjb25zdCByPWF3YWl0IGZldGNoKHJvdXRlLHttZXRob2Q6J1BPU1QnLGhlYWRlcnM6eydDb250ZW50LVR5cGUnOidhcHBsaWNhdGlvbi9qc29uJ30sY2FjaGU6J25vLXN0b3JlJyxzaWduYWw6Y3RsLnNpZ25hbCxib2R5OkpTT04uc3RyaW5naWZ5KHsuLi5wLGluaXREYXRhOnRnPy5pbml0RGF0YXx8Jyd9KX0pO2xldCBkPXt9O3RyeXtkPWF3YWl0IHIuanNvbigpfWNhdGNoKGUpe31pZighci5vayl0aHJvdyBPYmplY3QuYXNzaWduKG5ldyBFcnJvcihkLmVycm9yfHwn2K7Yt9in24wg2KfYsdiq2KjYp9i3Jykse3N0YXR1czpyLnN0YXR1cyxkYXRhOmR9KTtyZXR1cm4gZH1jYXRjaChlKXtpZihlPy5uYW1lPT09J0Fib3J0RXJyb3InKXRocm93IE9iamVjdC5hc3NpZ24obmV3IEVycm9yKCd0aW1lb3V0Jykse3N0YXR1czowLHRpbWVvdXQ6dHJ1ZX0pO3Rocm93IGV9ZmluYWxseXtjbGVhclRpbWVvdXQodGltZXIpfX0KZnVuY3Rpb24gYXBwbHlTZXNzaW9uKGQpe3N0YXRlLnNlc3Npb25SZWFkeT10cnVlO3N0YXRlLnZpcD0hIWQudmlwO3N0YXRlLnByZWZzPXsuLi5zdGF0ZS5wcmVmcywuLi4oZC5wcmVmZXJlbmNlc3x8e30pfTskKCd0aWVyJykudGV4dENvbnRlbnQ9ZC52aXA/J1ZJUCDZgdi52KfZhCc6J9it2LPYp9ioINix2KfbjNqv2KfZhic7YXBwbHlQcmVmcygpfQphc3luYyBmdW5jdGlvbiBzeW5jU2Vzc2lvbigpe2xldCBkPWF3YWl0IGFwaSgnL2FwaS9zZXNzaW9uJyx7fSw4MDAwKTthcHBseVNlc3Npb24oZCk7cmV0dXJuIGR9CmZ1bmN0aW9uIGFwcGx5VGhlbWUodCx7cGVyc2lzdExvY2FsPXRydWV9PXt9KXt0PXQ9PT0nbGlnaHQnPydsaWdodCc6J2RhcmsnO2RvY3VtZW50LmJvZHkuY2xhc3NMaXN0LnRvZ2dsZSgnbGlnaHQnLHQ9PT0nbGlnaHQnKTtzdGF0ZS5wcmVmcy50aGVtZT10OyQoJ3RoZW1lQnRuJykudGV4dENvbnRlbnQ9dD09PSdsaWdodCc/J/CfjJknOifimIDvuI8nO2lmKCQoJ3NldFRoZW1lJykpJCgnc2V0VGhlbWUnKS52YWx1ZT10O2lmKHBlcnNpc3RMb2NhbCl7dHJ5e2xvY2FsU3RvcmFnZS5zZXRJdGVtKCd0YWxheWFyX3RoZW1lJyx0KX1jYXRjaChlKXt9fX0KbGV0IHRoZW1lU2F2ZVRpbWVyPW51bGw7CmZ1bmN0aW9uIHRvZ2dsZVRoZW1lKCl7bGV0IHQ9c3RhdGUucHJlZnMudGhlbWU9PT0nbGlnaHQnPydkYXJrJzonbGlnaHQnO2FwcGx5VGhlbWUodCk7Y2xlYXJUaW1lb3V0KHRoZW1lU2F2ZVRpbWVyKTt0aGVtZVNhdmVUaW1lcj1zZXRUaW1lb3V0KGFzeW5jKCk9Pnt0cnl7bGV0IGQ9YXdhaXQgYXBpKCcvYXBpL3ByZWZlcmVuY2VzL3NhdmUnLHtwcmVmZXJlbmNlczp7Li4uc3RhdGUucHJlZnMsdGhlbWU6dH19KTtzdGF0ZS5wcmVmcz17Li4uc3RhdGUucHJlZnMsLi4uKGQucHJlZmVyZW5jZXN8fHt9KX19Y2F0Y2goZSl7fX0sMjUwKX0KZnVuY3Rpb24gYXBwbHlQcmVmcygpe2FwcGx5VGhlbWUoc3RhdGUucHJlZnMudGhlbWV8fCdsaWdodCcpOyQoJ2FwcFdyYXAnKS5jbGFzc0xpc3QudG9nZ2xlKCdjb21wYWN0JywhIXN0YXRlLnByZWZzLmNvbXBhY3QpOyQoJ3NldEhvbWUnKS52YWx1ZT1zdGF0ZS5wcmVmcy5ob21lfHwncHVsc2UnOyQoJ3NldENvbXBhY3QnKS5jaGVja2VkPSEhc3RhdGUucHJlZnMuY29tcGFjdDskKCdzZXRSc2knKS5jaGVja2VkPXN0YXRlLnByZWZzLnNob3dfcnNpIT09ZmFsc2U7JCgnc2V0RW1hJykuY2hlY2tlZD1zdGF0ZS5wcmVmcy5zaG93X2VtYSE9PWZhbHNlOyQoJ3NldExldmVscycpLmNoZWNrZWQ9c3RhdGUucHJlZnMuc2hvd19sZXZlbHMhPT1mYWxzZTskKCdzZXRUZicpLnZhbHVlPXN0YXRlLnByZWZzLmRlZmF1bHRfdGltZWZyYW1lfHwnMjRIJztyZW5kZXJQaW5zKCl9CmZ1bmN0aW9uIGdvKHYpe2RvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJy52aWV3JykuZm9yRWFjaCh4PT54LmNsYXNzTGlzdC5yZW1vdmUoJ2FjdGl2ZScpKTskKHYpPy5jbGFzc0xpc3QuYWRkKCdhY3RpdmUnKTtkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCcubmF2IGJ1dHRvbicpLmZvckVhY2goeD0+eC5jbGFzc0xpc3QudG9nZ2xlKCdhY3RpdmUnLHguZGF0YXNldC52PT09dikpO2lmKHY9PT0nc2Nhbm5lcicpbG9hZFNjYW5uZXIoKTtpZih2PT09J215X21hcmtldCcpcmVuZGVyTXlNYXJrZXQoKTtpZih2PT09J3NldHRpbmdzJylhcHBseVByZWZzKCl9CmZ1bmN0aW9uIHJlbmRlck92ZXJ2aWV3KGQsc3luY1ByZWZzPWZhbHNlKXtzdGF0ZS5vdmVydmlldz1kO2lmKCFzdGF0ZS5zZXNzaW9uUmVhZHkpc3RhdGUudmlwPSEhZC52aXA7aWYoc3luY1ByZWZzJiYhc3RhdGUuc2Vzc2lvblJlYWR5KXN0YXRlLnByZWZzPXsuLi5zdGF0ZS5wcmVmcywuLi4oZC5wcmVmZXJlbmNlc3x8e30pfTskKCd0aWVyJykudGV4dENvbnRlbnQ9c3RhdGUudmlwPydWSVAg2YHYudin2YQnOifYrdiz2KfYqCDYsdin24zar9in2YYnOyQoJ3B1bHNlU2NvcmUnKS50ZXh0Q29udGVudD1kLnB1bHNlPy5zY29yZT8/J+KAlCc7JCgncHVsc2VCYXInKS5zdHlsZS53aWR0aD0oZC5wdWxzZT8uc2NvcmV8fDApKyclJzskKCdwdWxzZVN0YXRlJykudGV4dENvbnRlbnQ9ZC5tYXJrZXRfc3RhdHVzPT09J2RlZ3JhZGVkJz8n2KjYp9iy2KfYsSDYr9in2K7ZhNuMINmF2YjZgtiq2KfZiyDYr9ixINiv2LPYqtix2LMg2YbbjNiz2KonOihkLnB1bHNlPy5zdGF0ZXx8J+KAlCcpOyQoJ3B1bHNlU3RhdGUnKS5jbGFzc05hbWU9J3ByaWNlICcrKGQucHVsc2U/LnN0YXRlPT09J9i12LnZiNiv24wnPyd1cCc6ZC5wdWxzZT8uc3RhdGU9PT0n2YbYstmI2YTbjCc/J2Rvd24nOidmbGF0Jyk7JCgncHVsc2VNZXRhJykudGV4dENvbnRlbnQ9ZC5tYXJrZXRfc3RhdHVzPT09J2RlZ3JhZGVkJz8n2KjYrti04oCM2YfYp9uMINmF2LPYqtmC2YQg2YXYq9mEINqp2LHbjNm+2KrZiNiMINiz24zar9mG2KfZhCDZiCDYsdin2YfZhtmF2Kcg2YfZhdqG2YbYp9mGINmB2LnYp9mE4oCM2KfZhtivLic6ZC5tYXJrZXRfc3RhdHVzPT09J3N0YWxlJz9g2KLYrtix24zZhiDYr9in2K/ZhyDZhdi52KrYqNixIOKAoiAke2QubWFya2V0X2FnZT8/J+KAlCd9INir2KfZhtuM2Ycg2YLYqNmEIOKAoiDYqNix2YjYstix2LPYp9mG24wg2K/YsSDZvtiz4oCM2LLZhduM2YbZh2A6YNmF2KvYqNiqICR7ZC5wdWxzZT8ucG9zaXRpdmV8fDB9IOKAoiDZhdmG2YHbjCAke2QucHVsc2U/Lm5lZ2F0aXZlfHwwfSDigKIg2KjYsdmI2LLYsdiz2KfZhtuMICR7ZC51cGRhdGVkX2F0fWA7bGV0IHByaWNlUm93cz0oZC5pdGVtc3x8W10pOyQoJ3ByaWNlcycpLmlubmVySFRNTD1wcmljZVJvd3MubGVuZ3RoP3ByaWNlUm93cy5tYXAoaT0+YDxkaXYgY2xhc3M9ImNhcmQgY2xpY2siIG9uY2xpY2s9Im9wZW5Bc3NldCgnJHtpLmtleX0nKSI+PGRpdiBjbGFzcz0ibXV0ZWQiPiR7ZXNjKGkubGFiZWwpfTwvZGl2PjxkaXYgY2xhc3M9InByaWNlICR7Y2xzKGkuY2hhbmdlKX0iPiR7Zm10KGkucHJpY2UpfSA8c21hbGw+JHtlc2MoaS51bml0KX08L3NtYWxsPjwvZGl2PjxkaXYgY2xhc3M9ImNoYW5nZSAke2NscyhpLmNoYW5nZSl9Ij4ke2Fycm93KGkuY2hhbmdlKX0gJHtwY3QoaS5jaGFuZ2UpfTwvZGl2PiR7aS5zb3VyY2U9PT0nZGVyaXZlZCc/JzxkaXYgY2xhc3M9InRpbnkgbXV0ZWQiPtio2LHYotmI2LHYryDZhti42LHbjDwvZGl2Pic6Jyd9PC9kaXY+YCkuam9pbignJyk6YDxkaXYgY2xhc3M9ImVtcHR5IiBzdHlsZT0iZ3JpZC1jb2x1bW46MS8tMSI+JHtkLm1hcmtldF9zdGF0dXM9PT0nZGVncmFkZWQnPyfZhdmG2KjYuSDYqNin2LLYp9ixINiv2KfYrtmE24wg2YXZiNmC2KrYp9mLINm+2KfYs9iuINmG2YXbjOKAjNiv2YfYr9ibINi52K/YryDZgtiv24zZhduMINuM2Kcg2LPYp9iu2Krar9uMINmG2YXYp9uM2LQg2K/Yp9iv2Ycg2YbZhduM4oCM2LTZiNivLic6J9mH2YbZiNiyINiv2KfYr9mH4oCM2KfbjCDYr9ix24zYp9mB2Kog2YbYtNiv2Ycg2KfYs9iqLid9PC9kaXY+YDtsZXQgbW92ZXJSb3dzPShkLm1vdmVyc3x8W10pOyQoJ21vdmVycycpLmlubmVySFRNTD1tb3ZlclJvd3MubGVuZ3RoP21vdmVyUm93cy5tYXAoKGksbik9PmA8ZGl2IGNsYXNzPSJyb3cgY2xpY2siIG9uY2xpY2s9Im9wZW5Bc3NldCgnJHtpLmtleX0nKSI+PGRpdiBjbGFzcz0iZmxleCI+PHNwYW4gY2xhc3M9InJhbmsiPiR7bisxfTwvc3Bhbj48c3Bhbj4ke2VzYyhpLmxhYmVsKX08L3NwYW4+PC9kaXY+PGIgY2xhc3M9IiR7Y2xzKGkuY2hhbmdlKX0iPiR7YXJyb3coaS5jaGFuZ2UpfSAke3BjdChpLmNoYW5nZSl9PC9iPjwvZGl2PmApLmpvaW4oJycpOmA8ZGl2IGNsYXNzPSJlbXB0eSI+JHtkLm1hcmtldF9zdGF0dXM9PT0nZGVncmFkZWQnPyfZvtizINin2LIg2KjYp9iy2q/YtNiqINmF2YbYqNi5INio2KfYstin2LHYjCDYqNuM2LTYqtix24zZhiDYrdix2qnYqiDYrtmI2K/aqdin2LEg2KjZh+KAjNix2YjYstix2LPYp9mG24wg2YXbjOKAjNi02YjYry4nOifYr9in2K/ZhyDaqdin2YHbjCDZhtuM2LPYqi4nfTwvZGl2PmA7bGV0IGhlYXRSb3dzPShkLmhlYXRtYXB8fFtdKTskKCdoZWF0Qm9keScpLmlubmVySFRNTD1oZWF0Um93cy5sZW5ndGg/aGVhdFJvd3MubWFwKGk9PmA8ZGl2IGNsYXNzPSJjYXJkICR7aS5jaGFuZ2U+MD8naGVhdFVwJzppLmNoYW5nZTwwPydoZWF0RG93bic6Jyd9IGNsaWNrIiBvbmNsaWNrPSJvcGVuQXNzZXQoJyR7aS5rZXl9JykiPjxkaXYgY2xhc3M9InRpbnkiPiR7ZXNjKGkubGFiZWwpfTwvZGl2PjxkaXYgY2xhc3M9InByaWNlIiBzdHlsZT0iZm9udC1zaXplOjE1cHgiPiR7Zm10KGkucHJpY2UpfTwvZGl2PjxkaXYgY2xhc3M9IiR7Y2xzKGkuY2hhbmdlKX0gdGlueSI+JHtwY3QoaS5jaGFuZ2UpfTwvZGl2PjwvZGl2PmApLmpvaW4oJycpOmA8ZGl2IGNsYXNzPSJlbXB0eSIgc3R5bGU9ImdyaWQtY29sdW1uOjEvLTEiPiR7ZC5tYXJrZXRfc3RhdHVzPT09J2RlZ3JhZGVkJz8n2YbZgti02Ycg2KjYp9iy2KfYsSDYr9in2K7ZhNuMINm+2LMg2KfYsiDYqNix2YLYsdin2LHbjCDZhdmG2KjYuSDZgtuM2YXYqiDZhtmF2KfbjNi0INiv2KfYr9mHINmF24zigIzYtNmI2K8uJzon2KjYsdin24wg2LPYp9iu2Kog2YbZgti02Ycg2YfZhtmI2LIg2K/Yp9iv2Ycg2qnYp9mB24wg2YbbjNiz2KouJ308L2Rpdj5gO3JlbmRlckFzc2V0SHViKCk7aWYoc3luY1ByZWZzKWFwcGx5UHJlZnMoKX0KZnVuY3Rpb24gcmVnaXN0cnkoKXtyZXR1cm4gc3RhdGUub3ZlcnZpZXc/LnJlZ2lzdHJ5fHxbXX0KZnVuY3Rpb24gcmVuZGVyQXNzZXRIdWIoKXtsZXQgcj1yZWdpc3RyeSgpLGM9c3RhdGUub3ZlcnZpZXc/LmNyeXB0b19zZWxlY3RlZHx8W107bGV0IGRvbWVzdGljPXIubWFwKGE9PmEuYXZhaWxhYmxlP2A8ZGl2IGNsYXNzPSJhc3NldENoaXAgY2xpY2siIG9uY2xpY2s9Im9wZW5Bc3NldCgnJHthLmtleX0nKSI+PGI+JHtlc2MoYS5sYWJlbCl9PC9iPjxkaXYgY2xhc3M9InRpbnkgdXAiPtmB2LnYp9mEPC9kaXY+PC9kaXY+YDpgPGRpdiBjbGFzcz0iYXNzZXRDaGlwIj48Yj4ke2VzYyhhLmxhYmVsKX08L2I+PGRpdiBjbGFzcz0idGlueSBtdXRlZCI+2K/Yp9iv2Ycg2YXZiNmC2KrYp9mLINiv2LEg2K/Ys9iq2LHYsyDZhtuM2LPYqjwvZGl2PjwvZGl2PmApLmpvaW4oJycpO2xldCBjcnlwdG89Yy5tYXAoYT0+YDxkaXYgY2xhc3M9ImFzc2V0Q2hpcCBjbGljayIgb25jbGljaz0ib3BlbkNyeXB0bygnJHthLmtleX0nKSI+PGI+JHtlc2MoYS5sYWJlbCl9PC9iPjxkaXYgY2xhc3M9InRpbnkgdXAiPiR7Zm10KGEucHJpY2UpfSBVU0RUIOKAoiAke3BjdChhLmNoYW5nZSl9PC9kaXY+PC9kaXY+YCkuam9pbignJyk7JCgnYXNzZXRIdWInKS5pbm5lckhUTUw9ZG9tZXN0aWMrY3J5cHRvOyQoJ2Fzc2V0U2VsZWN0b3InKS5pbm5lckhUTUw9ci5maWx0ZXIoYT0+YS5hdmFpbGFibGUpLm1hcChhPT5gPG9wdGlvbiB2YWx1ZT0iJHthLmtleX0iPiR7ZXNjKGEubGFiZWwpfTwvb3B0aW9uPmApLmpvaW4oJycpfQpmdW5jdGlvbiByZW5kZXJQaW5zKCl7bGV0IHA9bmV3IFNldChzdGF0ZS5wcmVmcy5waW5uZWR8fFtdKTskKCdwaW5FZGl0b3InKS5pbm5lckhUTUw9cmVnaXN0cnkoKS5tYXAoYT0+YDxsYWJlbCBjbGFzcz0iYXNzZXRDaGlwIj48aW5wdXQgdHlwZT0iY2hlY2tib3giIGRhdGEtcGluPSIke2Eua2V5fSIgJHtwLmhhcyhhLmtleSk/J2NoZWNrZWQnOicnfT4gJHtlc2MoYS5sYWJlbCl9PC9sYWJlbD5gKS5qb2luKCcnKX0KYXN5bmMgZnVuY3Rpb24gc2F2ZVNldHRpbmdzKCl7bGV0IHBpbnM9Wy4uLmRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJ1tkYXRhLXBpbl06Y2hlY2tlZCcpXS5tYXAoeD0+eC5kYXRhc2V0LnBpbik7bGV0IHByZWZzPXt0aGVtZTokKCdzZXRUaGVtZScpLnZhbHVlLGhvbWU6JCgnc2V0SG9tZScpLnZhbHVlLGNvbXBhY3Q6JCgnc2V0Q29tcGFjdCcpLmNoZWNrZWQsc2hvd19yc2k6JCgnc2V0UnNpJykuY2hlY2tlZCxzaG93X2VtYTokKCdzZXRFbWEnKS5jaGVja2VkLHNob3dfbGV2ZWxzOiQoJ3NldExldmVscycpLmNoZWNrZWQsZGVmYXVsdF90aW1lZnJhbWU6JCgnc2V0VGYnKS52YWx1ZSxwaW5uZWQ6cGluc307dHJ5e2xldCBkPWF3YWl0IGFwaSgnL2FwaS9wcmVmZXJlbmNlcy9zYXZlJyx7cHJlZmVyZW5jZXM6cHJlZnN9KTtzdGF0ZS5wcmVmcz1kLnByZWZlcmVuY2VzO2FwcGx5UHJlZnMoKTthbGVydCgn2KrZhti424zZhdin2Kog2LDYrtuM2LHZhyDYtNivIOKchScpfWNhdGNoKGUpe2FsZXJ0KCfYsNiu24zYsdmHINiq2YbYuNuM2YXYp9iqINmG2KfZhdmI2YHZgiDYqNmI2K8nKX19CmxldCByZWZyZXNoQnVzeT1mYWxzZSxib290ZWQ9ZmFsc2Usc2Vzc2lvblJldHJ5VGltZXI9bnVsbDsKZnVuY3Rpb24gc2hvd01hcmtldE1lc3NhZ2UobXNnKXskKCdwcmljZXMnKS5pbm5lckhUTUw9YDxkaXYgY2xhc3M9ImVtcHR5IiBzdHlsZT0iZ3JpZC1jb2x1bW46MS8tMSI+JHtlc2MobXNnKX08L2Rpdj5gOyQoJ21vdmVycycpLmlubmVySFRNTD1gPGRpdiBjbGFzcz0iZW1wdHkiPiR7ZXNjKG1zZyl9PC9kaXY+YDskKCdoZWF0Qm9keScpLmlubmVySFRNTD1gPGRpdiBjbGFzcz0iZW1wdHkiIHN0eWxlPSJncmlkLWNvbHVtbjoxLy0xIj4ke2VzYyhtc2cpfTwvZGl2PmB9CmFzeW5jIGZ1bmN0aW9uIGxvYWRNYXJrZXRPdmVydmlldyhzeW5jUHJlZnM9ZmFsc2Upe3RyeXtsZXQgZD1hd2FpdCBhcGkoJy9hcGkvb3ZlcnZpZXcnLHt9LDkwMDApO3JlbmRlck92ZXJ2aWV3KGQsc3luY1ByZWZzKTtpZihkb2N1bWVudC5xdWVyeVNlbGVjdG9yKCcudmlldy5hY3RpdmUnKT8uaWQ9PT0nbXlfbWFya2V0JylyZW5kZXJNeU1hcmtldCgpO2lmKGQubWFya2V0X3N0YXR1cyE9PSdvaycpc2V0VGltZW91dCgoKT0+cmVmcmVzaE92ZXJ2aWV3KCksNTAwMCk7cmV0dXJuIHRydWV9Y2F0Y2goZSl7bGV0IG1zZz1lLnN0YXR1cz09PTQwMT8n2YXbjNmG24zigIzYp9m+INix2Kcg2KfYsiDYr9qp2YXZhyDYr9in2K7ZhCDYsdio2KfYqiDYt9mE2KfbjNin2LEg2KjYp9iyINqp2YbbjNivLic6ZS5zdGF0dXM9PT01MDM/J9mF2YbYqNi5INio2KfYstin2LEg2K/Yp9iu2YTbjCDZhdmI2YLYqtin2Ysg2K/YsSDYr9iz2KrYsdizINmG24zYs9iqLic6J9io2KfYstin2LEg2K/Yp9iu2YTbjCDYr9ixINit2KfZhCDYp9iq2LXYp9mEINin2LPYqtibINio2K7YtOKAjNmH2KfbjCDYr9uM2q/YsSDZgdi52KfZhOKAjNin2YbYry4nO3Nob3dNYXJrZXRNZXNzYWdlKG1zZyk7cmV0dXJuIGZhbHNlfX0KYXN5bmMgZnVuY3Rpb24gbG9hZCgpe2xldCBsb2NhbFRoZW1lPScnO3RyeXtsb2NhbFRoZW1lPWxvY2FsU3RvcmFnZS5nZXRJdGVtKCd0YWxheWFyX3RoZW1lJyl8fCcnfWNhdGNoKGUpe31pZihsb2NhbFRoZW1lKWFwcGx5VGhlbWUobG9jYWxUaGVtZSx7cGVyc2lzdExvY2FsOmZhbHNlfSk7dHJ5e2F3YWl0IHN5bmNTZXNzaW9uKCk7Ym9vdGVkPXRydWU7bGV0IGhvbWU9c3RhdGUucHJlZnMuaG9tZXx8J3B1bHNlJztpZihbJ3B1bHNlJywnaGVhdG1hcCcsJ215X21hcmtldCddLmluY2x1ZGVzKGhvbWUpKWdvKGhvbWUpfWNhdGNoKGUpe3N0YXRlLnNlc3Npb25SZWFkeT1mYWxzZTtib290ZWQ9dHJ1ZTskKCd0aWVyJykudGV4dENvbnRlbnQ9J9iv2LEg2K3Yp9mEINin2KrYtdin2YQnO2lmKGUuc3RhdHVzPT09NDAxKXtzaG93TWFya2V0TWVzc2FnZSgn2YXbjNmG24zigIzYp9m+INix2Kcg2KfYsiDYr9qp2YXZhyDYr9in2K7ZhCDYsdio2KfYqiDYt9mE2KfbjNin2LEg2KjYp9iyINqp2YbbjNivLicpO3JldHVybn1jbGVhclRpbWVvdXQoc2Vzc2lvblJldHJ5VGltZXIpO3Nlc3Npb25SZXRyeVRpbWVyPXNldFRpbWVvdXQoYXN5bmMoKT0+e3RyeXthd2FpdCBzeW5jU2Vzc2lvbigpfWNhdGNoKF9lKXt9fSwzMDAwKX1hd2FpdCBsb2FkTWFya2V0T3ZlcnZpZXcoZmFsc2UpfQphc3luYyBmdW5jdGlvbiByZWZyZXNoT3ZlcnZpZXcoKXtpZihyZWZyZXNoQnVzeSlyZXR1cm47cmVmcmVzaEJ1c3k9dHJ1ZTt0cnl7aWYoIXN0YXRlLnNlc3Npb25SZWFkeSl7dHJ5e2F3YWl0IHN5bmNTZXNzaW9uKCl9Y2F0Y2goZSl7fX1sZXQgY3VycmVudD1kb2N1bWVudC5xdWVyeVNlbGVjdG9yKCcudmlldy5hY3RpdmUnKT8uaWR8fCdwdWxzZSc7YXdhaXQgbG9hZE1hcmtldE92ZXJ2aWV3KGZhbHNlKTtpZihjdXJyZW50PT09J215X21hcmtldCcpcmVuZGVyTXlNYXJrZXQoKX1maW5hbGx5e3JlZnJlc2hCdXN5PWZhbHNlfX0KYXN5bmMgZnVuY3Rpb24gbG9hZFNjYW5uZXIoKXtsZXQgYj0kKCdzY2FubmVyQm9keScpO2IuaW5uZXJIVE1MPSc8ZGl2IGNsYXNzPSJlbXB0eSI+2K/YsSDYrdin2YQg2KrYrdmE24zZhOKApjwvZGl2Pic7dHJ5e2xldCBkPWF3YWl0IGFwaSgnL2FwaS9zY2FubmVyJyk7c3RhdGUudmlwPXRydWU7JCgndGllcicpLnRleHRDb250ZW50PSdWSVAg2YHYudin2YQnO2IuaW5uZXJIVE1MPShkLml0ZW1zfHxbXSkubWFwKChpLG4pPT5gPGRpdiBjbGFzcz0icm93IGNsaWNrIiBvbmNsaWNrPSJvcGVuQXNzZXQoJyR7aS5rZXl9JykiPjxzcGFuIGNsYXNzPSJyYW5rIj4ke24rMX08L3NwYW4+PHNwYW4gc3R5bGU9ImZsZXg6MSI+JHtlc2MoaS5sYWJlbCl9PGJyPjxzcGFuIGNsYXNzPSJ0aW55IG11dGVkIj4ke2VzYyhpLnJlZ2ltZXx8J+KAlCcpfSDigKIgUSAke2kucT8/J+KAlCd9PC9zcGFuPjwvc3Bhbj48YiBjbGFzcz0iZ29sZCI+JHtpLnNjb3JlPz8n4oCUJ30vMTAwPC9iPjwvZGl2PmApLmpvaW4oJycpfHwnPGRpdiBjbGFzcz0iZW1wdHkiPtiv2KfYr9mHINqp2KfZgduMINmG24zYs9iqPC9kaXY+J31jYXRjaChlKXtiLmlubmVySFRNTD1lLnN0YXR1cz09PTQwMz8nPGRpdiBjbGFzcz0ibG9jayI+4q2QINin2LPaqdmGINmB2LHYtdiq4oCM2YfYp9uMINio2KfYstin2LEg2YXYrti12YjYtSBWSVAg2KfYs9iqLjwvZGl2Pic6JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yrti32Kcg2K/YsSDYp9iz2qnZhiDbjNinINiv2KfYr9mHINiq2KfYstmHINio2KfYstin2LEg2K/YsSDYr9iz2KrYsdizINmG24zYs9iqLjwvZGl2Pid9fQpmdW5jdGlvbiBnYXVnZVN2ZyhzY29yZSl7bGV0IHM9ZmluaXRlKHNjb3JlKT9NYXRoLm1heCgwLE1hdGgubWluKDEwMCxOdW1iZXIoc2NvcmUpKSk6MCxhPU1hdGguUEktKHMvMTAwKSpNYXRoLlBJLGN4PTEyMCxjeT0xMDIscj02OCx4PWN4K3IqTWF0aC5jb3MoYSkseT1jeS1yKk1hdGguc2luKGEpLGxhYmVsPXM+PTcwPyfZgtmI24wnOnM+PTQ1PyfZhdiq2YjYs9i3Jzon2LbYuduM2YEnO3JldHVybiBgPGRpdiBjbGFzcz0iZ2F1Z2UiPjxzdmcgdmlld0JveD0iMCAwIDI0MCAxMzIiIHJvbGU9ImltZyI+PHBhdGggZD0iTTI4IDEwMiBBOTIgOTIgMCAwIDEgMjEyIDEwMiIgZmlsbD0ibm9uZSIgc3Ryb2tlPSJ2YXIoLS1saW5lKSIgc3Ryb2tlLXdpZHRoPSIxNiIvPjxwYXRoIGQ9Ik0yOCAxMDIgQTkyIDkyIDAgMCAxIDczIDI0IiBmaWxsPSJub25lIiBzdHJva2U9IiNmZjRkNTUiIHN0cm9rZS13aWR0aD0iMTYiLz48cGF0aCBkPSJNNzMgMjQgQTkyIDkyIDAgMCAxIDE2NyAyNCIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjZDlhOTMzIiBzdHJva2Utd2lkdGg9IjE2Ii8+PHBhdGggZD0iTTE2NyAyNCBBOTIgOTIgMCAwIDEgMjEyIDEwMiIgZmlsbD0ibm9uZSIgc3Ryb2tlPSIjMjhkMTdjIiBzdHJva2Utd2lkdGg9IjE2Ii8+PHRleHQgeD0iMjUiIHk9IjEyMyIgY2xhc3M9ImdhdWdlU2NhbGUiPjA8L3RleHQ+PHRleHQgeD0iMTE1IiB5PSIxNiIgY2xhc3M9ImdhdWdlU2NhbGUiPjUwPC90ZXh0Pjx0ZXh0IHg9IjIwNyIgeT0iMTIzIiBjbGFzcz0iZ2F1Z2VTY2FsZSI+MTAwPC90ZXh0PjxsaW5lIHgxPSIke2N4fSIgeTE9IiR7Y3l9IiB4Mj0iJHt4LnRvRml4ZWQoMSl9IiB5Mj0iJHt5LnRvRml4ZWQoMSl9IiBzdHJva2U9InZhcigtLXRleHQpIiBzdHJva2Utd2lkdGg9IjQiLz48Y2lyY2xlIGN4PSIke2N4fSIgY3k9IiR7Y3l9IiByPSI5IiBmaWxsPSJ2YXIoLS10ZXh0KSIvPjxjaXJjbGUgY3g9IiR7Y3h9IiBjeT0iJHtjeX0iIHI9IjQiIGZpbGw9InZhcigtLWNhcmQpIi8+PC9zdmc+PGRpdiBjbGFzcz0iZ2F1Z2VWYWx1ZSI+JHtNYXRoLnJvdW5kKHMpfS8xMDA8L2Rpdj48ZGl2IGNsYXNzPSJnYXVnZUxhYmVsIj4ke2xhYmVsfTwvZGl2PjwvZGl2PmB9YXN5bmMgZnVuY3Rpb24gb3BlbkFzc2V0KGtleSl7c3RhdGUuYXNzZXQ9a2V5O2dvKCdhc3NldCcpOyQoJ2Fzc2V0U2VsZWN0b3InKS52YWx1ZT1rZXk7JCgnYXNzZXRUaXRsZScpLnRleHRDb250ZW50PSfYr9ixINit2KfZhCDYqNin2LHar9iw2KfYsduM4oCmJzskKCdhc3NldEJvZHknKS5pbm5lckhUTUw9Jyc7dHJ5e2xldCBkPWF3YWl0IGFwaSgnL2FwaS9hc3NldCcse2Fzc2V0OmtleX0pO2xldCBhPWQuYXNzZXQsdGVjaD1kLnRlY2huaWNhbDskKCdhc3NldFRpdGxlJykudGV4dENvbnRlbnQ9YS5sYWJlbDtsZXQgZ2F1Z2U9dGVjaD9nYXVnZVN2Zyh0ZWNoLnNjb3JlKTonJztsZXQgaHRtbD1gPGRpdiBjbGFzcz0iaGVybyI+PGRpdiBjbGFzcz0ibXV0ZWQiPtmC24zZhdiqINmB2LnZhNuMPC9kaXY+PGRpdiBjbGFzcz0ic2NvcmUgJHtjbHMoYS5jaGFuZ2UpfSI+JHtmbXQoYS5wcmljZSl9PC9kaXY+PGRpdj4ke2VzYyhhLnVuaXQpfSA8c3BhbiBjbGFzcz0iJHtjbHMoYS5jaGFuZ2UpfSI+JHthcnJvdyhhLmNoYW5nZSl9ICR7cGN0KGEuY2hhbmdlKX08L3NwYW4+PC9kaXY+JHtnYXVnZX08L2Rpdj5gO2lmKHRlY2gpe2h0bWwrPWA8ZGl2IGNsYXNzPSJzZWN0aW9uIj7Yqtit2YTbjNmEIFZJUDwvZGl2PjxkaXYgY2xhc3M9Im1ldHJpY3MiPjxkaXYgY2xhc3M9Im1ldHJpYyI+2YLYr9ix2Ko8Yj4ke3RlY2guc2NvcmU/PyfigJQnfS8xMDA8L2I+PC9kaXY+PGRpdiBjbGFzcz0ibWV0cmljIj5RINqp24zZgduM2Ko8Yj4ke3RlY2gucT8/J+KAlCd9LzEwMDwvYj48L2Rpdj48ZGl2IGNsYXNzPSJtZXRyaWMiPtix2pjbjNmFPGI+JHtlc2ModGVjaC5yZWdpbWV8fCfigJQnKX08L2I+PC9kaXY+JHtzdGF0ZS5wcmVmcy5zaG93X3JzaSE9PWZhbHNlP2A8ZGl2IGNsYXNzPSJtZXRyaWMiPlJTSTxiPiR7ZmluaXRlKHRlY2gucnNpKT9OdW1iZXIodGVjaC5yc2kpLnRvRml4ZWQoMSk6J+KAlCd9PC9iPjwvZGl2PmA6Jyd9JHtzdGF0ZS5wcmVmcy5zaG93X2VtYSE9PWZhbHNlP2A8ZGl2IGNsYXNzPSJtZXRyaWMiPkVNQSA5LzIxPGI+JHt0ZWNoLmVtYTkmJnRlY2guZW1hMjE/KHRlY2guZW1hOT50ZWNoLmVtYTIxPyfYtdi52YjYr9uMJzon2YbYstmI2YTbjCcpOifigJQnfTwvYj48L2Rpdj5gOicnfTxkaXYgY2xhc3M9Im1ldHJpYyI+2YbZiNiz2KfZhjxiPiR7cGN0KHRlY2gudm9sKX08L2I+PC9kaXY+PC9kaXY+PGRpdiBjbGFzcz0ic2VjdGlvbiI+8J+noCDahtix2Kcg2KfbjNmGINin2YXYqtuM2KfYstifPC9kaXY+JHt0ZWNoLmV4cGxhaW4mJnRlY2guZXhwbGFpbi5hdmFpbGFibGU/YDxkaXYgY2xhc3M9ImNhcmQiPjxkaXYgY2xhc3M9InRpbnkgbXV0ZWQiPiR7ZXNjKHRlY2guZXhwbGFpbi5ub3RlfHwnJyl9PC9kaXY+PGRpdiBjbGFzcz0ibGlzdCIgc3R5bGU9Im1hcmdpbi10b3A6OHB4Ij4keyh0ZWNoLmV4cGxhaW4ucGFydHN8fFtdKS5tYXAocD0+YDxkaXYgY2xhc3M9InJvdyI+PHNwYW4+JHtlc2MocC5sYWJlbCl9PGJyPjxzbWFsbCBjbGFzcz0ibXV0ZWQiPiR7ZXNjKHAuZGV0YWlsfHwnJyl9PC9zbWFsbD48L3NwYW4+PGIgY2xhc3M9IiR7cC5wb2ludHM+MD8ndXAnOnAucG9pbnRzPDA/J2Rvd24nOidmbGF0J30iPiR7cC5wb2ludHM+MD8nKyc6Jyd9JHtwLnBvaW50c308L2I+PC9kaXY+YCkuam9pbignJyl9PC9kaXY+PGRpdiBjbGFzcz0icm93Ij48c3Bhbj7Zvtin24zZhzwvc3Bhbj48Yj41MDwvYj48L2Rpdj48ZGl2IGNsYXNzPSJyb3ciPjxzcGFuPtin2YXYqtuM2KfYsiDZhtmH2KfbjNuMPC9zcGFuPjxiIGNsYXNzPSJnb2xkIj4ke3RlY2guZXhwbGFpbi5zY29yZX0vMTAwPC9iPjwvZGl2PjwvZGl2PmA6YDxkaXYgY2xhc3M9ImxvY2siPiR7ZXNjKHRlY2guZXhwbGFpbj8ucmVhc29ufHwn2K/Yp9iv2Ycg2qnYp9mB24wg2YbbjNiz2KonKX08L2Rpdj5gfSR7c3RhdGUucHJlZnMuc2hvd19sZXZlbHMhPT1mYWxzZT9gPGRpdiBjbGFzcz0ic2VjdGlvbiI+2K3Zhdin24zYqiAvINmF2YLYp9mI2YXYqjwvZGl2PjxkaXYgY2xhc3M9Im1ldHJpY3MiPjxkaXYgY2xhc3M9Im1ldHJpYyI+2K3Zhdin24zYqjxiPiR7Zm10KHRlY2guc3VwcG9ydCl9PC9iPjwvZGl2PjxkaXYgY2xhc3M9Im1ldHJpYyI+2YLbjNmF2Ko8Yj4ke2ZtdChhLnByaWNlKX08L2I+PC9kaXY+PGRpdiBjbGFzcz0ibWV0cmljIj7ZhdmC2KfZiNmF2Ko8Yj4ke2ZtdCh0ZWNoLnJlc2lzdGFuY2UpfTwvYj48L2Rpdj48L2Rpdj5gOicnfWA7aWYoZC5mYWlyX3ZhbHVlIT1udWxsKWh0bWwrPWA8ZGl2IGNsYXNzPSJzZWN0aW9uIj7Yrdio2KfYqCDZiCDYp9ix2LLYtCDZhdmG2LXZgdin2YbZhzwvZGl2PjxkaXYgY2xhc3M9ImNhcmQiPjxkaXYgY2xhc3M9ImZsZXgiPjxzcGFuPtin2LHYsti0INmF2YbYtdmB2KfZhtmHPC9zcGFuPjxiPiR7Zm10KGQuZmFpcl92YWx1ZSl9PC9iPjwvZGl2PjxkaXYgY2xhc3M9InRpbnkgbXV0ZWQiPlog2K3YqNin2Kg6ICR7ZmluaXRlKGQuYnViYmxlX3opP051bWJlcihkLmJ1YmJsZV96KS50b0ZpeGVkKDIpOifigJQnfTwvZGl2PjwvZGl2PmB9ZWxzZSBodG1sKz0nPGRpdiBjbGFzcz0ibG9jayIgc3R5bGU9Im1hcmdpbi10b3A6MTJweCI+8J+UkiDYqtit2YTbjNmEINiq2qnZhtuM2qnYp9mEINi52YXbjNmCINmF2K7YtdmI2LUgVklQINin2LPYqi48L2Rpdj4nO2xldCB0Zj1zdGF0ZS5wcmVmcy5kZWZhdWx0X3RpbWVmcmFtZXx8JzI0SCc7aHRtbCs9YDxkaXYgY2xhc3M9InNlY3Rpb24iPtmG2YXZiNiv2KfYsSDYqti52KfZhdmE24w8L2Rpdj48ZGl2IGNsYXNzPSJ0YWJzIiBpZD0idGYiPjxidXR0b24gY2xhc3M9InRhYiIgb25jbGljaz0ibG9hZENoYXJ0KCcxSCcsdGhpcykiPjFIIOKtkDwvYnV0dG9uPjxidXR0b24gY2xhc3M9InRhYiIgb25jbGljaz0ibG9hZENoYXJ0KCc0SCcsdGhpcykiPjRIIOKtkDwvYnV0dG9uPjxidXR0b24gY2xhc3M9InRhYiIgb25jbGljaz0ibG9hZENoYXJ0KCcyNEgnLHRoaXMpIj4yNEg8L2J1dHRvbj48YnV0dG9uIGNsYXNzPSJ0YWIiIG9uY2xpY2s9ImxvYWRDaGFydCgnN0QnLHRoaXMpIj43RCDirZA8L2J1dHRvbj48YnV0dG9uIGNsYXNzPSJ0YWIiIG9uY2xpY2s9ImxvYWRDaGFydCgnMzBEJyx0aGlzKSI+MzBEIOKtkDwvYnV0dG9uPjwvZGl2PjxkaXYgc3R5bGU9InBvc2l0aW9uOnJlbGF0aXZlIj48Y2FudmFzIGlkPSJjaGFydCIgd2lkdGg9IjgwMCIgaGVpZ2h0PSIzNjAiIHN0eWxlPSJ0b3VjaC1hY3Rpb246bm9uZSI+PC9jYW52YXM+PGRpdiBpZD0iY2hhcnRIdWQiIGNsYXNzPSJ0aW55IiBzdHlsZT0icG9zaXRpb246YWJzb2x1dGU7dG9wOjhweDtyaWdodDoxMHB4O2xlZnQ6MTBweDtwb2ludGVyLWV2ZW50czpub25lO3RleHQtYWxpZ246cmlnaHQiPjwvZGl2PjwvZGl2PjxkaXYgc3R5bGU9ImRpc3BsYXk6ZmxleDtnYXA6OHB4O2FsaWduLWl0ZW1zOmNlbnRlcjtqdXN0aWZ5LWNvbnRlbnQ6c3BhY2UtYmV0d2VlbjttYXJnaW4tdG9wOjdweCI+PGRpdiBpZD0iY2hhcnROb3RlIiBjbGFzcz0idGlueSBtdXRlZCI+PC9kaXY+PGJ1dHRvbiB0eXBlPSJidXR0b24iIGNsYXNzPSJ0YWIiIGlkPSJjaGFydFJlc2V0IiBvbmNsaWNrPSJyZXNldENoYXJ0VmlldygpIj7ihrog2KjYp9iy2YbYtNin2YbbjDwvYnV0dG9uPjwvZGl2PjxkaXYgY2xhc3M9InNlY3Rpb24iPtin2KjYstin2LEg2LPYsduM2Lk8L2Rpdj48ZGl2IGNsYXNzPSJ0b29sczYiPjxkaXYgY2xhc3M9ImNhcmQgY2xpY2siIG9uY2xpY2s9InRvZ2dsZVBpbignJHtrZXl9JykiPuKtkDxicj48Yj7Yp9mB2LLZiNiv2YYv2K3YsNmBINio2KfYstin2LEg2YXZhjwvYj48L2Rpdj48ZGl2IGNsYXNzPSJjYXJkIGNsaWNrIiBvbmNsaWNrPSJvcGVuU21hcnRBbGVydCgnJHtrZXl9JykiPvCfmqg8YnI+PGI+2YfYtNiv2KfYsSDZh9mI2LTZhdmG2K88L2I+PC9kaXY+PGRpdiBjbGFzcz0iY2FyZCBjbGljayIgb25jbGljaz0ibG9hZEZhaXIoKSI+8J+rpzxicj48Yj7Yp9ix2LLYtCDZhdmG2LXZgdin2YbZhzwvYj48L2Rpdj48L2Rpdj5gOyQoJ2Fzc2V0Qm9keScpLmlubmVySFRNTD1odG1sO2xldCBidG49Wy4uLmRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJyN0ZiAudGFiJyldLmZpbmQoeD0+eC50ZXh0Q29udGVudC50cmltKCkuc3RhcnRzV2l0aCh0Zi5yZXBsYWNlKCcxRCcsJzI0SCcpKSl8fGRvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJyN0ZiAudGFiJylbMl07c2V0VGltZW91dCgoKT0+bG9hZENoYXJ0KHRmLGJ0biksMCl9Y2F0Y2goZSl7JCgnYXNzZXRCb2R5JykuaW5uZXJIVE1MPSc8ZGl2IGNsYXNzPSJlbXB0eSI+2KfYt9mE2KfYudin2Kog2K/Yp9ix2KfbjNuMINiv2LEg2K/Ys9iq2LHYsyDZhtuM2LPYqi48L2Rpdj4nfX0KYXN5bmMgZnVuY3Rpb24gbG9hZENoYXJ0KHRmLGVsKXtkb2N1bWVudC5xdWVyeVNlbGVjdG9yQWxsKCcjdGYgLnRhYicpLmZvckVhY2goeD0+eC5jbGFzc0xpc3QucmVtb3ZlKCdhY3RpdmUnKSk7aWYoZWwpZWwuY2xhc3NMaXN0LmFkZCgnYWN0aXZlJyk7dHJ5e2xldCBkPWF3YWl0IGFwaSgnL2FwaS9jYW5kbGVzJyx7YXNzZXQ6c3RhdGUuYXNzZXQsdGltZWZyYW1lOnRmfSk7ZHJhd0NhbmRsZXMoZC5jYW5kbGVzfHxbXSk7JCgnY2hhcnROb3RlJykuaW5uZXJIVE1MPShkLm5vdGV8fCcnKStgPGRpdiBjbGFzcz0iY292ZXJhZ2UiPjxzcGFuPkNvdmVyYWdlICR7ZmluaXRlKGQuY292ZXJhZ2U/LmNvdmVyYWdlX3BjdCk/TnVtYmVyKGQuY292ZXJhZ2UuY292ZXJhZ2VfcGN0KS50b0ZpeGVkKDApOjB9JTwvc3Bhbj48c3Bhbj5HYXAgJHtkLmNvdmVyYWdlPy5nYXBzPz8wfTwvc3Bhbj48c3Bhbj5PdXRsaWVyICR7ZC5jb3ZlcmFnZT8uZmlsdGVyZWRfb3V0bGllcnM/PzB9PC9zcGFuPjwvZGl2PmB9Y2F0Y2goZSl7JCgnY2hhcnROb3RlJykudGV4dENvbnRlbnQ9ZS5zdGF0dXM9PT00MDM/J+KtkCDYp9uM2YYg2KrYp9uM2YXigIzZgdix24zZhSDZhdiu2LXZiNi1IFZJUCDYp9iz2KouJzon2K/Yp9iv2Ycg2qnYp9mB24wg2KjYsdin24wg2YbZhdmI2K/Yp9ixINmI2KzZiNivINmG2K/Yp9ix2K8uJztkcmF3Q2FuZGxlcyhbXSl9fQpsZXQgY2hhcnRTdGF0ZT17Y2FuZGxlczpbXSxzdGFydDowLGNvdW50OjAsaG92ZXI6LTEsZHJhZzpmYWxzZSxsYXN0WDowLHBvaW50ZXJzOm5ldyBNYXAoKSxwaW5jaERpc3Q6MH07CmZ1bmN0aW9uIHJlc2V0Q2hhcnRWaWV3KCl7aWYoIWNoYXJ0U3RhdGUuY2FuZGxlcy5sZW5ndGgpcmV0dXJuO2NoYXJ0U3RhdGUuc3RhcnQ9MDtjaGFydFN0YXRlLmNvdW50PWNoYXJ0U3RhdGUuY2FuZGxlcy5sZW5ndGg7Y2hhcnRTdGF0ZS5ob3Zlcj0tMTtyZW5kZXJJbnRlcmFjdGl2ZUNoYXJ0KCl9CmZ1bmN0aW9uIGNoYXJ0VmlzaWJsZSgpe2xldCBuPWNoYXJ0U3RhdGUuY2FuZGxlcy5sZW5ndGg7aWYoIW4pcmV0dXJuW107bGV0IGNvdW50PU1hdGgubWF4KDgsTWF0aC5taW4oY2hhcnRTdGF0ZS5jb3VudHx8bixuKSksc3RhcnQ9TWF0aC5tYXgoMCxNYXRoLm1pbihjaGFydFN0YXRlLnN0YXJ0LG4tY291bnQpKTtjaGFydFN0YXRlLmNvdW50PWNvdW50O2NoYXJ0U3RhdGUuc3RhcnQ9c3RhcnQ7cmV0dXJuIGNoYXJ0U3RhdGUuY2FuZGxlcy5zbGljZShzdGFydCxzdGFydCtjb3VudCl9CmZ1bmN0aW9uIGNoYXJ0Wm9vbShmYWN0b3IsYW5jaG9yPS41KXtsZXQgbj1jaGFydFN0YXRlLmNhbmRsZXMubGVuZ3RoO2lmKG48OSlyZXR1cm47bGV0IG9sZD1jaGFydFN0YXRlLmNvdW50fHxuLG5ld0NvdW50PU1hdGgubWF4KDgsTWF0aC5taW4obixNYXRoLnJvdW5kKG9sZCpmYWN0b3IpKSk7aWYobmV3Q291bnQ9PT1vbGQpcmV0dXJuO2xldCBjZW50ZXI9Y2hhcnRTdGF0ZS5zdGFydCtvbGQqTWF0aC5tYXgoMCxNYXRoLm1pbigxLGFuY2hvcikpO2NoYXJ0U3RhdGUuc3RhcnQ9TWF0aC5yb3VuZChjZW50ZXItbmV3Q291bnQqYW5jaG9yKTtjaGFydFN0YXRlLmNvdW50PW5ld0NvdW50O2NoYXJ0U3RhdGUuc3RhcnQ9TWF0aC5tYXgoMCxNYXRoLm1pbihjaGFydFN0YXRlLnN0YXJ0LG4tbmV3Q291bnQpKTtyZW5kZXJJbnRlcmFjdGl2ZUNoYXJ0KCl9CmZ1bmN0aW9uIGNoYXJ0UGFuKHB4KXtsZXQgY3Y9JCgnY2hhcnQnKTtpZighY3Z8fCFjaGFydFN0YXRlLmNhbmRsZXMubGVuZ3RoKXJldHVybjtsZXQgcmVjdD1jdi5nZXRCb3VuZGluZ0NsaWVudFJlY3QoKSxzdGVwPXJlY3Qud2lkdGgvTWF0aC5tYXgoMSxjaGFydFN0YXRlLmNvdW50KSxzaGlmdD1NYXRoLnJvdW5kKC1weC9NYXRoLm1heChzdGVwLDEpKTtpZighc2hpZnQpcmV0dXJuO2xldCBuPWNoYXJ0U3RhdGUuY2FuZGxlcy5sZW5ndGg7Y2hhcnRTdGF0ZS5zdGFydD1NYXRoLm1heCgwLE1hdGgubWluKGNoYXJ0U3RhdGUuc3RhcnQrc2hpZnQsbi1jaGFydFN0YXRlLmNvdW50KSk7cmVuZGVySW50ZXJhY3RpdmVDaGFydCgpfQpmdW5jdGlvbiBjYW5kbGVUaW1lKHgpe2xldCB2PXgudHx8eC50aW1lfHx4LnRzfHx4LnRpbWVzdGFtcHx8Jyc7aWYoIXYpcmV0dXJuJyc7dHJ5e2xldCBkPXR5cGVvZiB2PT09J251bWJlcic/bmV3IERhdGUodioodjwxZTEyPzEwMDA6MSkpOm5ldyBEYXRlKHYpO3JldHVybiBpc05hTihkKT9TdHJpbmcodik6ZC50b0xvY2FsZVN0cmluZygnZmEtSVInKX1jYXRjaChlKXtyZXR1cm4gU3RyaW5nKHYpfX0KZnVuY3Rpb24gcmVuZGVySW50ZXJhY3RpdmVDaGFydCgpe2NvbnN0IGN2PSQoJ2NoYXJ0Jyk7aWYoIWN2KXJldHVybjtjb25zdCBjdHg9Y3YuZ2V0Q29udGV4dCgnMmQnKSxXPWN2LndpZHRoLEg9Y3YuaGVpZ2h0LGM9Y2hhcnRWaXNpYmxlKCk7Y3R4LmNsZWFyUmVjdCgwLDAsVyxIKTtsZXQgYmc9Z2V0Q29tcHV0ZWRTdHlsZShkb2N1bWVudC5ib2R5KS5nZXRQcm9wZXJ0eVZhbHVlKCctLXNvZnQnKS50cmltKCl8fCcjMGQwZDBkJztjdHguZmlsbFN0eWxlPWJnO2N0eC5maWxsUmVjdCgwLDAsVyxIKTtpZighYy5sZW5ndGgpe2N0eC5maWxsU3R5bGU9JyM4ODgnO2N0eC50ZXh0QWxpZ249J2NlbnRlcic7Y3R4LmZvbnQ9JzIycHggVGFob21hJztjdHguZmlsbFRleHQoJ9iv2KfYr9mHINqp2KfZgduMINmG24zYs9iqJyxXLzIsSC8yKTtsZXQgaD0kKCdjaGFydEh1ZCcpO2lmKGgpaC50ZXh0Q29udGVudD0nJztyZXR1cm59Y29uc3QgcmVhbD1jLmZpbHRlcih4PT4heC5nYXAmJmZpbml0ZSh4LmgpJiZmaW5pdGUoeC5sKSYmZmluaXRlKHgubykmJmZpbml0ZSh4LmMpKTtpZighcmVhbC5sZW5ndGgpe2N0eC5maWxsU3R5bGU9JyM4ODgnO2N0eC50ZXh0QWxpZ249J2NlbnRlcic7Y3R4LmZvbnQ9JzIycHggVGFob21hJztjdHguZmlsbFRleHQoJ9iv2LEg2KfbjNmGINio2KfYstmHINiv2KfYr9mHINmF2LnYqtio2LEg2qnYp9mB24wg2YbbjNiz2KonLFcvMixILzIpO3JldHVybn1jb25zdCBoaT1NYXRoLm1heCguLi5yZWFsLm1hcCh4PT5OdW1iZXIoeC5oKSkpLGxvPU1hdGgubWluKC4uLnJlYWwubWFwKHg9Pk51bWJlcih4LmwpKSkscGFkPShoaS1sb3x8MSkqLjA4LG1heD1oaStwYWQsbWluPWxvLXBhZCx5PXA9PkgtMjItKE51bWJlcihwKS1taW4pLyhtYXgtbWluKSooSC00NCksc3RlcD0oVy0zNSkvYy5sZW5ndGgsY3c9TWF0aC5tYXgoMyxzdGVwKi41OCk7Y3R4LnN0cm9rZVN0eWxlPScjNzc3Myc7Zm9yKGxldCBpPTE7aTw1O2krKyl7Y3R4LmJlZ2luUGF0aCgpO2N0eC5tb3ZlVG8oMTUsSCppLzUpO2N0eC5saW5lVG8oVy0xMCxIKmkvNSk7Y3R4LnN0cm9rZSgpfWMuZm9yRWFjaCgoeCxpKT0+e2lmKHguZ2FwKXJldHVybjtsZXQgeHg9MjAraSpzdGVwK3N0ZXAvMixjb2w9TnVtYmVyKHguYyk+PU51bWJlcih4Lm8pPycjMjhkMTdjJzonI2ZmNGQ1NSc7Y3R4LnN0cm9rZVN0eWxlPWNvbDtjdHguZmlsbFN0eWxlPWNvbDtjdHguYmVnaW5QYXRoKCk7Y3R4Lm1vdmVUbyh4eCx5KHguaCkpO2N0eC5saW5lVG8oeHgseSh4LmwpKTtjdHguc3Ryb2tlKCk7bGV0IHlvPXkoeC5vKSx5Yz15KHguYyksdG9wPU1hdGgubWluKHlvLHljKSxoaD1NYXRoLm1heCgyLE1hdGguYWJzKHlvLXljKSk7Y3R4LmZpbGxSZWN0KHh4LWN3LzIsdG9wLGN3LGhoKX0pO2N0eC5maWxsU3R5bGU9JyM4ODgnO2N0eC5mb250PScxNXB4IFRhaG9tYSc7Y3R4LnRleHRBbGlnbj0nbGVmdCc7Y3R4LmZpbGxUZXh0KGZtdChoaSksOCwxNyk7Y3R4LmZpbGxUZXh0KGZtdChsbyksOCxILTYpO2lmKGNoYXJ0U3RhdGUuaG92ZXI+PTAmJmNoYXJ0U3RhdGUuaG92ZXI8Yy5sZW5ndGgmJiFjW2NoYXJ0U3RhdGUuaG92ZXJdLmdhcCl7bGV0IGk9Y2hhcnRTdGF0ZS5ob3Zlcix4PWNbaV0seHg9MjAraSpzdGVwK3N0ZXAvMjtjdHguc2F2ZSgpO2N0eC5zZXRMaW5lRGFzaChbNSw0XSk7Y3R4LnN0cm9rZVN0eWxlPScjYWFhOSc7Y3R4LmJlZ2luUGF0aCgpO2N0eC5tb3ZlVG8oeHgsMCk7Y3R4LmxpbmVUbyh4eCxIKTtjdHguc3Ryb2tlKCk7bGV0IHl5PXkoeC5jKTtjdHguYmVnaW5QYXRoKCk7Y3R4Lm1vdmVUbygwLHl5KTtjdHgubGluZVRvKFcseXkpO2N0eC5zdHJva2UoKTtjdHgucmVzdG9yZSgpO2xldCBodWQ9JCgnY2hhcnRIdWQnKTtpZihodWQpaHVkLmlubmVySFRNTD1gPGI+JHtjYW5kbGVUaW1lKHgpfTwvYj4gJm5ic3A7IE8gJHtmbXQoeC5vKX0gJm5ic3A7IEggJHtmbXQoeC5oKX0gJm5ic3A7IEwgJHtmbXQoeC5sKX0gJm5ic3A7IEMgJHtmbXQoeC5jKX1gfX0KZnVuY3Rpb24gY2hhcnRIb3ZlckZyb21FdmVudChlKXtsZXQgY3Y9JCgnY2hhcnQnKTtpZighY3Z8fCFjaGFydFN0YXRlLmNhbmRsZXMubGVuZ3RoKXJldHVybjtsZXQgcj1jdi5nZXRCb3VuZGluZ0NsaWVudFJlY3QoKSx4PShlLmNsaWVudFgtci5sZWZ0KSooY3Yud2lkdGgvci53aWR0aCksYz1jaGFydFZpc2libGUoKSxzdGVwPShjdi53aWR0aC0zNSkvTWF0aC5tYXgoMSxjLmxlbmd0aCksaT1NYXRoLm1heCgwLE1hdGgubWluKGMubGVuZ3RoLTEsTWF0aC5mbG9vcigoeC0yMCkvc3RlcCkpKTtpZihjW2ldPy5nYXApe2xldCBiZXN0PS0xLGRpc3Q9MWU5O2MuZm9yRWFjaCgodixqKT0+e2lmKCF2LmdhcCYmTWF0aC5hYnMoai1pKTxkaXN0KXtiZXN0PWo7ZGlzdD1NYXRoLmFicyhqLWkpfX0pO2k9YmVzdH1jaGFydFN0YXRlLmhvdmVyPWk7cmVuZGVySW50ZXJhY3RpdmVDaGFydCgpfQpmdW5jdGlvbiBiaW5kQ2hhcnRJbnRlcmFjdGlvbnMoKXtsZXQgY3Y9JCgnY2hhcnQnKTtpZighY3Z8fGN2LmRhdGFzZXQuaW50ZXJhY3RpdmU9PT0nMScpcmV0dXJuO2N2LmRhdGFzZXQuaW50ZXJhY3RpdmU9JzEnO2N2LmFkZEV2ZW50TGlzdGVuZXIoJ3doZWVsJyxlPT57ZS5wcmV2ZW50RGVmYXVsdCgpO2xldCByPWN2LmdldEJvdW5kaW5nQ2xpZW50UmVjdCgpLGE9KGUuY2xpZW50WC1yLmxlZnQpL3Iud2lkdGg7Y2hhcnRab29tKGUuZGVsdGFZPjA/MS4xODouODQsYSl9LHtwYXNzaXZlOmZhbHNlfSk7Y3YuYWRkRXZlbnRMaXN0ZW5lcigncG9pbnRlcmRvd24nLGU9Pntjdi5zZXRQb2ludGVyQ2FwdHVyZT8uKGUucG9pbnRlcklkKTtjaGFydFN0YXRlLnBvaW50ZXJzLnNldChlLnBvaW50ZXJJZCx7eDplLmNsaWVudFgseTplLmNsaWVudFl9KTtjaGFydFN0YXRlLmRyYWc9dHJ1ZTtjaGFydFN0YXRlLmxhc3RYPWUuY2xpZW50WDtpZihjaGFydFN0YXRlLnBvaW50ZXJzLnNpemU9PT0xKWNoYXJ0SG92ZXJGcm9tRXZlbnQoZSk7aWYoY2hhcnRTdGF0ZS5wb2ludGVycy5zaXplPT09Mil7bGV0IGE9Wy4uLmNoYXJ0U3RhdGUucG9pbnRlcnMudmFsdWVzKCldO2NoYXJ0U3RhdGUucGluY2hEaXN0PU1hdGguaHlwb3QoYVswXS54LWFbMV0ueCxhWzBdLnktYVsxXS55KX19KTtjdi5hZGRFdmVudExpc3RlbmVyKCdwb2ludGVybW92ZScsZT0+e2lmKGNoYXJ0U3RhdGUucG9pbnRlcnMuaGFzKGUucG9pbnRlcklkKSljaGFydFN0YXRlLnBvaW50ZXJzLnNldChlLnBvaW50ZXJJZCx7eDplLmNsaWVudFgseTplLmNsaWVudFl9KTtpZihjaGFydFN0YXRlLnBvaW50ZXJzLnNpemU9PT0yKXtsZXQgYT1bLi4uY2hhcnRTdGF0ZS5wb2ludGVycy52YWx1ZXMoKV0sZD1NYXRoLmh5cG90KGFbMF0ueC1hWzFdLngsYVswXS55LWFbMV0ueSk7aWYoY2hhcnRTdGF0ZS5waW5jaERpc3Q+MCYmTWF0aC5hYnMoZC1jaGFydFN0YXRlLnBpbmNoRGlzdCk+OCl7Y2hhcnRab29tKGQ+Y2hhcnRTdGF0ZS5waW5jaERpc3QgPyAuODggOiAxLjE0LC41KTtjaGFydFN0YXRlLnBpbmNoRGlzdD1kfXJldHVybn1pZihjaGFydFN0YXRlLmRyYWcmJmNoYXJ0U3RhdGUucG9pbnRlcnMuc2l6ZT09PTEpe2xldCBkeD1lLmNsaWVudFgtY2hhcnRTdGF0ZS5sYXN0WDtpZihNYXRoLmFicyhkeCk+NSl7Y2hhcnRQYW4oZHgpO2NoYXJ0U3RhdGUubGFzdFg9ZS5jbGllbnRYfWVsc2UgY2hhcnRIb3ZlckZyb21FdmVudChlKX1lbHNlIGNoYXJ0SG92ZXJGcm9tRXZlbnQoZSl9KTtjb25zdCB1cD1lPT57Y2hhcnRTdGF0ZS5wb2ludGVycy5kZWxldGUoZS5wb2ludGVySWQpO2lmKGNoYXJ0U3RhdGUucG9pbnRlcnMuc2l6ZT09PTApe2NoYXJ0U3RhdGUuZHJhZz1mYWxzZTtjaGFydFN0YXRlLnBpbmNoRGlzdD0wfX07Y3YuYWRkRXZlbnRMaXN0ZW5lcigncG9pbnRlcnVwJyx1cCk7Y3YuYWRkRXZlbnRMaXN0ZW5lcigncG9pbnRlcmNhbmNlbCcsdXApO2N2LmFkZEV2ZW50TGlzdGVuZXIoJ3BvaW50ZXJsZWF2ZScsZT0+e2lmKCFjaGFydFN0YXRlLmRyYWcpe2NoYXJ0U3RhdGUuaG92ZXI9LTE7cmVuZGVySW50ZXJhY3RpdmVDaGFydCgpfX0pfQpmdW5jdGlvbiBkcmF3Q2FuZGxlcyhjKXtjaGFydFN0YXRlLmNhbmRsZXM9QXJyYXkuaXNBcnJheShjKT9jOltdO2NoYXJ0U3RhdGUuc3RhcnQ9MDtjaGFydFN0YXRlLmNvdW50PWNoYXJ0U3RhdGUuY2FuZGxlcy5sZW5ndGg7Y2hhcnRTdGF0ZS5ob3Zlcj0tMTtiaW5kQ2hhcnRJbnRlcmFjdGlvbnMoKTtyZW5kZXJJbnRlcmFjdGl2ZUNoYXJ0KCl9CmZ1bmN0aW9uIHJlbmRlck15TWFya2V0KCl7bGV0IHBpbnM9c3RhdGUucHJlZnMucGlubmVkfHxbXSxpdGVtcz1zdGF0ZS5vdmVydmlldz8uaXRlbXN8fFtdO2xldCBtYXA9T2JqZWN0LmZyb21FbnRyaWVzKGl0ZW1zLm1hcCh4PT5beC5rZXkseF0pKTskKCdteU1hcmtldEJvZHknKS5pbm5lckhUTUw9cGlucy5tYXAoaz0+e2xldCBpPW1hcFtrXTtpZighaSlyZXR1cm4nJztyZXR1cm5gPGRpdiBjbGFzcz0icm93IGNsaWNrIiBvbmNsaWNrPSJvcGVuQXNzZXQoJyR7a30nKSI+PHNwYW4+JHtlc2MoaS5sYWJlbCl9PGJyPjxzbWFsbCBjbGFzcz0ibXV0ZWQiPiR7Zm10KGkucHJpY2UpfSAke2VzYyhpLnVuaXQpfTwvc21hbGw+PC9zcGFuPjxzcGFuIGNsYXNzPSIke2NscyhpLmNoYW5nZSl9Ij4ke2Fycm93KGkuY2hhbmdlKX0gJHtwY3QoaS5jaGFuZ2UpfTwvc3Bhbj48L2Rpdj5gfSkuam9pbignJyl8fCc8ZGl2IGNsYXNzPSJlbXB0eSI+2KfYsiDYqtmG2LjbjNmF2KfYqtiMINiv2KfYsdin24zbjOKAjNmH2KfbjCDYr9mE2K7ZiNin2Ycg2LHYpyDYs9mG2KzYp9mCINqp2YYuPC9kaXY+J30KYXN5bmMgZnVuY3Rpb24gdG9nZ2xlUGluKGspe2xldCBwPVsuLi4oc3RhdGUucHJlZnMucGlubmVkfHxbXSldO3A9cC5pbmNsdWRlcyhrKT9wLmZpbHRlcih4PT54IT09ayk6Wy4uLnAsa10uc2xpY2UoMCwxMik7c3RhdGUucHJlZnMucGlubmVkPXA7dHJ5e2xldCBkPWF3YWl0IGFwaSgnL2FwaS9wcmVmZXJlbmNlcy9zYXZlJyx7cHJlZmVyZW5jZXM6c3RhdGUucHJlZnN9KTtzdGF0ZS5wcmVmcz1kLnByZWZlcmVuY2VzO3JlbmRlclBpbnMoKTthbGVydCgn2KjYp9iy2KfYsSDZhdmGINio2YfigIzYsdmI2LLYsdiz2KfZhtuMINi02K8g4pyFJyl9Y2F0Y2goZSl7fX0KYXN5bmMgZnVuY3Rpb24gb3BlblNtYXJ0QWxlcnQoYXNzZXQ9c3RhdGUuYXNzZXQpe2dvKCdtb3JlJyk7bGV0IGI9JCgnbW9yZUJvZHknKTtiLmlubmVySFRNTD1gPGRpdiBjbGFzcz0iY2FyZCI+PGRpdiBjbGFzcz0ic2VjdGlvbiIgc3R5bGU9Im1hcmdpbi10b3A6MCI+8J+aqCDZh9i02K/Yp9ixINmH2YjYtNmF2YbYrzwvZGl2PjxzZWxlY3QgaWQ9InNhQXNzZXQiIGNsYXNzPSJzZWxlY3RvciI+JHtyZWdpc3RyeSgpLm1hcChhPT5gPG9wdGlvbiB2YWx1ZT0iJHthLmtleX0iICR7YS5rZXk9PT1hc3NldD8nc2VsZWN0ZWQnOicnfT4ke2VzYyhhLmxhYmVsKX08L29wdGlvbj5gKS5qb2luKCcnKX08L3NlbGVjdD48ZGl2IGNsYXNzPSJ0YWJzIiBzdHlsZT0ibWFyZ2luLXRvcDoxMHB4Ij48YnV0dG9uIGNsYXNzPSJ0YWIiIG9uY2xpY2s9ImNyZWF0ZVNBKCdicmVha291dCcpIj7YtNqp2LPYqiDZhdit2K/ZiNiv2Yc8L2J1dHRvbj48YnV0dG9uIGNsYXNzPSJ0YWIiIG9uY2xpY2s9ImNyZWF0ZVNBKCdhYm5vcm1hbCcpIj7Yrdix2qnYqiDYutuM2LHYudin2K/bjDwvYnV0dG9uPjxidXR0b24gY2xhc3M9InRhYiIgb25jbGljaz0iY3JlYXRlU0EoJ2NvbmZsdWVuY2UnKSI+2YfZhdqv2LHYp9uM24wg2YLZiNuMPC9idXR0b24+PGJ1dHRvbiBjbGFzcz0idGFiIiBvbmNsaWNrPSJjcmVhdGVTQSgnYnViYmxlJykiPtit2KjYp9ioINio2KfZhNinPC9idXR0b24+PC9kaXY+PGRpdiBpZD0ic2FNc2ciIGNsYXNzPSJ0aW55IG11dGVkIiBzdHlsZT0ibWFyZ2luLXRvcDoxMHB4Ij48L2Rpdj48L2Rpdj5gfQphc3luYyBmdW5jdGlvbiBjcmVhdGVTQShydWxlKXtsZXQgYT0kKCdzYUFzc2V0JykudmFsdWU7dHJ5e2xldCBkPWF3YWl0IGFwaSgnL2FwaS9zbWFydC1hbGVydCcse2Fzc2V0OmEscnVsZX0pOyQoJ3NhTXNnJykudGV4dENvbnRlbnQ9ZC5yZXN1bHQ9PT0nZXhpc3RzJz8n2KfbjNmGINmH2LTYr9in2LEg2KfYsiDZgtio2YQg2YHYudin2YQg2KfYs9iqLic6J9mH2LTYr9in2LEg2YfZiNi02YXZhtivINmB2LnYp9mEINi02K8g4pyFJ31jYXRjaChlKXskKCdzYU1zZycpLnRleHRDb250ZW50PWUuc3RhdHVzPT09NDAzPyfYp9uM2YYg2YLYp9io2YTbjNiqINmF2K7YtdmI2LUgVklQINin2LPYqi4nOmUuc3RhdHVzPT09NDAwPyfYp9uM2YYg2YLYp9mG2YjZhiDYqNix2KfbjCDYp9uM2YYg2K/Yp9ix2KfbjNuMINm+2LTYqtuM2KjYp9mG24wg2YbZhduM4oCM2LTZiNivLic6J9iu2LfYpyDYr9ixINir2KjYqiDZh9i02K/Yp9ixJ319CmFzeW5jIGZ1bmN0aW9uIGxvYWRGYWlyKCl7Z28oJ21vcmUnKTtsZXQgYj0kKCdtb3JlQm9keScpO2IuaW5uZXJIVE1MPSc8ZGl2IGNsYXNzPSJlbXB0eSI+2K/YsSDYrdin2YQg2YXYrdin2LPYqNmH4oCmPC9kaXY+Jzt0cnl7bGV0IGQ9YXdhaXQgYXBpKCcvYXBpL2ZhaXItdmFsdWUnKTtzdGF0ZS52aXA9dHJ1ZTskKCd0aWVyJykudGV4dENvbnRlbnQ9J1ZJUCDZgdi52KfZhCc7Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9Imxpc3QiPicrKGQuaXRlbXN8fFtdKS5tYXAoaT0+YDxkaXYgY2xhc3M9InJvdyI+PHNwYW4+JHtlc2MoaS5sYWJlbCl9PGJyPjxzcGFuIGNsYXNzPSJ0aW55IG11dGVkIj7YqNin2LLYp9ixICR7Zm10KGkubWFya2V0KX0g4oCiINmG2LjYsduMICR7Zm10KGkuZmFpcil9PC9zcGFuPjwvc3Bhbj48YiBjbGFzcz0iJHtjbHMoaS5wY3QpfSI+JHtwY3QoaS5wY3QpfTwvYj48L2Rpdj5gKS5qb2luKCcnKSsnPC9kaXY+J31jYXRjaChlKXtiLmlubmVySFRNTD1lLnN0YXR1cz09PTQwMz8nPGRpdiBjbGFzcz0ibG9jayI+4q2QINin2LHYsti0INmF2YbYtdmB2KfZhtmHINmF2K7YtdmI2LUgVklQINin2LPYqi48L2Rpdj4nOic8ZGl2IGNsYXNzPSJlbXB0eSI+2K/Yp9iv2Ycg2KrYp9iy2Ycg2qnYp9mB24wg2YbbjNiz2KouPC9kaXY+J319CmFzeW5jIGZ1bmN0aW9uIGxvYWRSc2lNYXAoKXtnbygnbW9yZScpO2xldCBiPSQoJ21vcmVCb2R5Jyk7Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yr9ixINit2KfZhCDZhdit2KfYs9io2YfigKY8L2Rpdj4nO3RyeXtsZXQgZD1hd2FpdCBhcGkoJy9hcGkvcnNpLW1hcCcpO3N0YXRlLnZpcD10cnVlOyQoJ3RpZXInKS50ZXh0Q29udGVudD0nVklQINmB2LnYp9mEJztiLmlubmVySFRNTD1gPGRpdiBjbGFzcz0ic2VjdGlvbiIgc3R5bGU9Im1hcmdpbi10b3A6MCI+8J+nrSDZhtmC2LTZhyDZgtiv2LHYqiDYrdix2qnYqiAoUlNJKTwvZGl2PjxkaXYgY2xhc3M9Imxpc3QiPiR7KGQuaXRlbXN8fFtdKS5tYXAoaT0+YDxkaXYgY2xhc3M9InJvdyBjbGljayIgb25jbGljaz0ib3BlbkFzc2V0KCcke2kua2V5fScpIj48c3Bhbj4ke2VzYyhpLmxhYmVsKX08YnI+PHNtYWxsIGNsYXNzPSJtdXRlZCI+JHtlc2MoaS56b25lfHwn4oCUJyl9IOKAoiBRICR7aS5xPz8n4oCUJ308L3NtYWxsPjwvc3Bhbj48Yj4ke2Zpbml0ZShpLnJzaSk/TnVtYmVyKGkucnNpKS50b0ZpeGVkKDEpOifigJQnfTwvYj48L2Rpdj5gKS5qb2luKCcnKX08L2Rpdj5gfWNhdGNoKGUpe2IuaW5uZXJIVE1MPWUuc3RhdHVzPT09NDAzPyc8ZGl2IGNsYXNzPSJsb2NrIj7irZAg2YbZgti02Ycg2YLYr9ix2Kog2K3Ysdqp2Kog2YXYrti12YjYtSBWSVAg2KfYs9iqLjwvZGl2Pic6JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yr9in2K/ZhyDYqtin2LLZhyDaqdin2YHbjCDZhtuM2LPYqi48L2Rpdj4nfX0KYXN5bmMgZnVuY3Rpb24gb3BlbkJhY2t0ZXN0KCl7Z28oJ21vcmUnKTtsZXQgYj0kKCdtb3JlQm9keScpO2IuaW5uZXJIVE1MPWA8ZGl2IGNsYXNzPSJjYXJkIj48ZGl2IGNsYXNzPSJzZWN0aW9uIiBzdHlsZT0ibWFyZ2luLXRvcDowIj7wn6eqINii2LLZhdin24zYtCDYqtin2LHbjNiu24w8L2Rpdj48c2VsZWN0IGlkPSJidEFzc2V0IiBjbGFzcz0ic2VsZWN0b3IiPiR7cmVnaXN0cnkoKS5tYXAoYT0+YDxvcHRpb24gdmFsdWU9IiR7YS5rZXl9Ij4ke2VzYyhhLmxhYmVsKX08L29wdGlvbj5gKS5qb2luKCcnKX08L3NlbGVjdD48c2VsZWN0IGlkPSJidFJ1bGUiIGNsYXNzPSJzZWxlY3RvciIgc3R5bGU9Im1hcmdpbi10b3A6OHB4Ij48b3B0aW9uIHZhbHVlPSJjb25mbHVlbmNlIj7Zh9mF2q/Ysdin24zbjCBFTUEgKyBSU0k8L29wdGlvbj48b3B0aW9uIHZhbHVlPSJyc2lfb3ZlcnNvbGQiPlJTSSDiiaQgMzA8L29wdGlvbj48b3B0aW9uIHZhbHVlPSJyc2lfb3ZlcmJvdWdodCI+UlNJIOKJpSA3MDwvb3B0aW9uPjxvcHRpb24gdmFsdWU9ImVtYV9jcm9zcyI+RU1BIDkvMjE8L29wdGlvbj48L3NlbGVjdD48YnV0dG9uIGNsYXNzPSJidG4iIHN0eWxlPSJ3aWR0aDoxMDAlO21hcmdpbi10b3A6MTBweCIgb25jbGljaz0icnVuQmFja3Rlc3QoKSI+2KfYrNix2KfbjCDYotiy2YXYp9uM2LQ8L2J1dHRvbj48ZGl2IGlkPSJidFJlc3VsdCIgc3R5bGU9Im1hcmdpbi10b3A6MTBweCI+PC9kaXY+PC9kaXY+YH0KYXN5bmMgZnVuY3Rpb24gcnVuQmFja3Rlc3QoKXtsZXQgYm94PSQoJ2J0UmVzdWx0Jyk7Ym94LmlubmVySFRNTD0nPGRpdiBjbGFzcz0iZW1wdHkiPtiv2LEg2K3Yp9mEINii2LLZhdin24zYtOKApjwvZGl2Pic7dHJ5e2xldCBkPWF3YWl0IGFwaSgnL2FwaS9iYWNrdGVzdCcse2Fzc2V0OiQoJ2J0QXNzZXQnKS52YWx1ZSxydWxlOiQoJ2J0UnVsZScpLnZhbHVlfSkscj1kLnJlc3VsdHx8e307Ym94LmlubmVySFRNTD1yLnNhbXBsZXM/YDxkaXYgY2xhc3M9Im1ldHJpY3MiPjxkaXYgY2xhc3M9Im1ldHJpYyI+2LHYrtiv2KfYrzxiPiR7ci5zYW1wbGVzfTwvYj48L2Rpdj48ZGl2IGNsYXNzPSJtZXRyaWMiPtit2LHaqdiqINmH2YXigIzYrNmH2Ko8Yj4ke051bWJlcihyLmhpdCkudG9GaXhlZCgxKX0lPC9iPjwvZGl2PjxkaXYgY2xhc3M9Im1ldHJpYyI+2YXbjNin2Ybar9uM2YY8Yj4ke051bWJlcihyLmF2ZykudG9GaXhlZCgzKX0lPC9iPjwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9InRpbnkgbXV0ZWQiPiR7ZXNjKHIubm90ZXx8JycpfTwvZGl2PmA6YDxkaXYgY2xhc3M9ImVtcHR5Ij4ke2VzYyhyLm1lc3NhZ2V8fCfZhtmF2YjZhtmHINqp2KfZgduMINmG24zYs9iqJyl9PC9kaXY+YH1jYXRjaChlKXtib3guaW5uZXJIVE1MPWUuc3RhdHVzPT09NDAzPyc8ZGl2IGNsYXNzPSJsb2NrIj7irZAg2KLYstmF2KfbjNi0INiq2KfYsduM2K7bjCDZhdiu2LXZiNi1IFZJUCDYp9iz2KouPC9kaXY+JzonPGRpdiBjbGFzcz0iZW1wdHkiPtiu2LfYpyDYr9ixINii2LLZhdin24zYtCDYqtin2LHbjNiu24w8L2Rpdj4nfX0KYXN5bmMgZnVuY3Rpb24gbG9hZEFjdGl2aXR5KCl7Z28oJ21vcmUnKTtsZXQgYj0kKCdtb3JlQm9keScpO2IuaW5uZXJIVE1MPSc8ZGl2IGNsYXNzPSJlbXB0eSI+2K/YsSDYrdin2YQg2K/YsduM2KfZgdiq4oCmPC9kaXY+Jzt0cnl7bGV0IGQ9YXdhaXQgYXBpKCcvYXBpL2FjdGl2aXR5Jyk7Yi5pbm5lckhUTUw9YDxkaXYgY2xhc3M9InNlY3Rpb24iIHN0eWxlPSJtYXJnaW4tdG9wOjAiPvCfk5wg2YHYudin2YTbjNiqINmF2YY8L2Rpdj48ZGl2IGNsYXNzPSJsaXN0Ij4keyhkLml0ZW1zfHxbXSkubWFwKGk9PmA8ZGl2IGNsYXNzPSJyb3ciPjxzcGFuPiR7ZXNjKGkudGl0bGV8fGkuZXZlbnRfdHlwZSl9PGJyPjxzbWFsbCBjbGFzcz0ibXV0ZWQiPiR7ZXNjKGkuYXNzZXRfa2V5fHwnJyl9IOKAoiAke2VzYygoaS5jcmVhdGVkX2F0fHwnJykucmVwbGFjZSgnVCcsJyAnKS5zbGljZSgwLDE5KSl9PC9zbWFsbD48YnI+PHNtYWxsPiR7ZXNjKGkuZGV0YWlsfHwnJyl9PC9zbWFsbD48L3NwYW4+JHtmaW5pdGUoaS5wcmljZSk/YDxiPiR7Zm10KGkucHJpY2UpfTwvYj5gOicnfTwvZGl2PmApLmpvaW4oJycpfHwnPGRpdiBjbGFzcz0iZW1wdHkiPtmH2YbZiNiyINix2YjbjNiv2KfYr9uMINir2KjYqiDZhti02K/Zhy48L2Rpdj4nfTwvZGl2PmB9Y2F0Y2goZSl7Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yrti32Kcg2K/YsSDYqtin2LHbjNiu2obZhzwvZGl2Pid9fQphc3luYyBmdW5jdGlvbiBsb2FkTWVsdGVkUHJvKCl7Z28oJ21vcmUnKTtsZXQgYj0kKCdtb3JlQm9keScpO3RyeXtsZXQgcz1hd2FpdCBzeW5jU2Vzc2lvbigpO2lmKCFzLnZpcCl7Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImxvY2siPuKtkCDZhdix2qnYsiDYrdix2YHZh+KAjNin24wg2KLYqOKAjNi02K/ZhyDZhdiu2LXZiNi1IFZJUCDYp9iz2KouPC9kaXY+JztyZXR1cm59fWNhdGNoKGUpe2IuaW5uZXJIVE1MPSc8ZGl2IGNsYXNzPSJlbXB0eSI+2YjYtti524zYqiDYrdiz2KfYqCDZgtin2KjZhCDYqNix2LHYs9uMINmG24zYs9iq2Jsg2K/ZiNio2KfYsdmHINiq2YTYp9i0INqp2YbbjNivLjwvZGl2Pic7cmV0dXJufWxldCBtPXN0YXRlLm92ZXJ2aWV3Py5tZWx0ZWR8fHt9O2IuaW5uZXJIVE1MPWA8ZGl2IGNsYXNzPSJncmlkIj48ZGl2IGNsYXNzPSJjYXJkIj48ZGl2IGNsYXNzPSJtdXRlZCI+2KLYqOKAjNi02K/ZhyDZhtmC2K/bjDwvZGl2PjxkaXYgY2xhc3M9InByaWNlIj4ke2ZtdChtLmNhc2gpfTwvZGl2PjxkaXYgY2xhc3M9InRpbnkiPiR7ZXNjKG0uY2FzaF9zb3VyY2V8fCcnKX08L2Rpdj48L2Rpdj48ZGl2IGNsYXNzPSJjYXJkIj48ZGl2IGNsYXNzPSJtdXRlZCI+2KLYqOKAjNi02K/ZhyDZgdix2K/Yp9uM24w8L2Rpdj48ZGl2IGNsYXNzPSJwcmljZSI+JHtmbXQobS5mdXR1cmUpfTwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9ImNhcmQiPjxkaXYgY2xhc3M9Im11dGVkIj7Yp9iu2KrZhNin2YEg2YbZgtiv24wv2YHYsdiv2KfbjNuMPC9kaXY+PGRpdiBjbGFzcz0icHJpY2UgJHtjbHMobS5zcHJlYWR8fDApfSI+JHtmbXQobS5zcHJlYWQpfTwvZGl2PjxkaXY+JHtwY3QobS5zcHJlYWRfcGN0KX08L2Rpdj48L2Rpdj48ZGl2IGNsYXNzPSJjYXJkIj48ZGl2IGNsYXNzPSJtdXRlZCI+2K/ZhNin2LEg2KrZh9ix2KfZhiAvINiv2LHZh9mFPC9kaXY+PGRpdj4ke2ZtdChtLnVzZCl9IC8gJHtmbXQobS5hZWQpfTwvZGl2PjwvZGl2PjwvZGl2PmB9Cgphc3luYyBmdW5jdGlvbiBsb2FkU2lnbmFscygpe2dvKCdzaWduYWxzVmlldycpO2xldCBiPSQoJ3NpZ25hbHNCb2R5Jyk7Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yr9ixINit2KfZhCDYqNix2LHYs9uMINmB2LHYtdiq4oCM2YfYp9uMINmI2KfZgti524zigKY8L2Rpdj4nO3RyeXtsZXQgZD1hd2FpdCBhcGkoJy9hcGkvc2lnbmFscycse30sODAwMCk7c3RhdGUudmlwPSEhZC52aXA7JCgndGllcicpLnRleHRDb250ZW50PWQudmlwPydWSVAg2YHYudin2YQnOifYrdiz2KfYqCDYsdin24zar9in2YYnO2xldCBwPWQucGVyZm9ybWFuY2V8fHt9O2xldCByYXRlPXAudHAxX3JhdGU9PW51bGw/J+KAlCc6TnVtYmVyKHAudHAxX3JhdGUpLnRvRml4ZWQoMSkrJyUnO2xldCBoZWFkPWA8ZGl2IGNsYXNzPSJjYXJkIj48ZGl2IGNsYXNzPSJmbGV4Ij48Yj7aqdin2LHZhtin2YXZhyDbs9uwINix2YjYstmHPC9iPjxzcGFuIGNsYXNzPSJwaWxsIj7Zh9iv2YEg2KfZiNmEICR7cmF0ZX08L3NwYW4+PC9kaXY+PGRpdiBjbGFzcz0idGlueSBtdXRlZCI+2qnZhCAke3AudG90YWx8fDB9IOKAoiDZh9iv2YHbsSAke3AudHAxfHwwfSDigKIg2YfYr9mB27IgJHtwLnRwMnx8MH0g4oCiINmH2K/ZgduzICR7cC50cDN8fDB9IOKAoiDYrdiv2LbYsdixICR7cC5zbHx8MH0g4oCiINiz2LHYqNmH4oCM2LPYsSAke3AuYnJlYWtldmVufHwwfSDigKIg2YXYqNmH2YUgJHtwLmFtYmlndW91c3x8MH0g4oCiINio2KfYsiAke3Aub3Blbnx8MH08L2Rpdj48L2Rpdj5gO2xldCBmYT14PT54PT09J0JVWSc/J9mB2LHYtdiqINiu2LHbjNivJzp4PT09J1NFTEwnPyfZgdix2LXYqiDZgdix2YjYtCc6eD09PSdOT19TSUdOQUwnPyfYr9in2K/ZhyDYqNix2KfbjCDYqti12YXbjNmFINqp2KfZgduMINmG24zYs9iqJzon2YHYudmE2KfZiyDZgdix2LXYqiDZhdmG2KfYs9io24wg2K/bjNiv2Ycg2YbZhduM4oCM2LTZiNivJztsZXQgcm93cz0oZC5pdGVtc3x8W10pLm1hcChzPT57aWYoIXMub2spcmV0dXJuYDxkaXYgY2xhc3M9InJvdyI+PHNwYW4+JHtlc2Mocy5sYWJlbHx8cy5hc3NldHx8J9io2KfYstin2LEnKX08L3NwYW4+PGIgY2xhc3M9ImZsYXQiPiR7cy5lcnJvcj09PSd3YXJtaW5nX3VwJz8n2K/YsSDYrdin2YQg2KLZhdin2K/Zh+KAjNiz2KfYstuMINiq2K3ZhNuM2YQnOifYr9in2K/ZhyDZhdi52KrYqNixINqp2KfZgduMINmG24zYs9iqJ308L2I+PC9kaXY+YDtsZXQgc2lkZT1zLnNpZGV8fCdORVVUUkFMJyxjPXNpZGU9PT0nQlVZJz8ndXAnOnNpZGU9PT0nU0VMTCc/J2Rvd24nOidmbGF0JztsZXQgZGV0YWlsPXMubG9ja2VkP2A8ZGl2IGNsYXNzPSJ0aW55IG11dGVkIj7wn5SSINmI2LHZiNiv2Iwg2K3YryDYttix2LEg2Ygg2YfYr9mB4oCM2YfYpyDYr9ixIFZJUCDZhtmF2KfbjNi0INiv2KfYr9mHINmF24zigIzYtNmI2K8uPC9kaXY+YDooKHNpZGU9PT0nQlVZJ3x8c2lkZT09PSdTRUxMJyk/YDxkaXYgY2xhc3M9InRpbnkgbXV0ZWQiPtmI2LHZiNivICR7Zm10KHMuZW50cnlfbG93KX3igJMke2ZtdChzLmVudHJ5X2hpZ2gpfSDigKIg2K3YryDYttix2LEgJHtmbXQocy5zdG9wX2xvc3MpfSDigKIg2YfYr9mBINin2YjZhCAke2ZtdChzLnRwMSl9PC9kaXY+YDonJyk7cmV0dXJuYDxkaXYgY2xhc3M9InJvdyI+PHNwYW4+PGI+JHtlc2Mocy5sYWJlbCl9PC9iPjxicj48c3BhbiBjbGFzcz0idGlueSBtdXRlZCI+JHtlc2Mocy5zeW1ib2wpfSDigKIg2qnbjNmB24zYqiAke3MuZGF0YV9xdWFsaXR5Pz8n4oCUJ30vMTAwIOKAoiDZgtiv2LHYqiAke3Muc2NvcmU/PyfigJQnfS8xMDA8L3NwYW4+JHtkZXRhaWx9PC9zcGFuPjxiIGNsYXNzPSIke2N9Ij4ke2VzYyhmYShzaWRlKSl9PC9iPjwvZGl2PmB9KS5qb2luKCcnKTtsZXQgZnJlZT1kLnZpcD8nJzpgPGRpdiBjbGFzcz0ibG9jayIgc3R5bGU9Im1hcmdpbi10b3A6MTBweCI+4q2QINmG2LPYrtmHINix2KfbjNqv2KfZhiDbjNqpINmG2YXYp9uMINmI2KfZgti524wg2KfYsiDYqNin2LLYp9ixINmG2LTYp9mGINmF24zigIzYr9mH2K8uINin2LPaqdmGINqp2KfZhdmE2Iwg2YXYrdiv2YjYr9mHINmI2LHZiNiv2Iwg2K3YryDYttix2LHYjCDYs9mHINmH2K/ZgSDZiCDYrNiy2KbbjNin2Kog2YfZhdmHINin2LHYstmH2KfbjCDYp9mG2KrYrtin2KjbjCDYqNix2KfbjCBWSVAg2YHYudin2YQg2KfYs9iqLjwvZGl2PmA7Yi5pbm5lckhUTUw9aGVhZCsnPGRpdiBjbGFzcz0ibGlzdCIgc3R5bGU9Im1hcmdpbi10b3A6MTBweCI+Jysocm93c3x8JzxkaXYgY2xhc3M9ImVtcHR5Ij7YqNin2LLYp9ixINiy24zYsSDZhti42LEg2KfYs9iqLjwvZGl2PicpKyc8L2Rpdj4nK2ZyZWUrJzxkaXYgY2xhc3M9InRpbnkgbXV0ZWQiIHN0eWxlPSJtYXJnaW4tdG9wOjEwcHgiPtmH24zahiDZgdix2LXYqtuMINiq2LbZhduM2YYg2LPZiNivINmG24zYs9iq2Jsg2KLZhdin2LEg2YHZgti3INin2LIg2LHaqdmI2LHYr9mH2KfbjCDZiNin2YLYuduMINiv24zYqtin2KjbjNizINmF2K3Yp9iz2KjZhyDZhduM4oCM2LTZiNivLjwvZGl2Pid9Y2F0Y2goZSl7Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yr9in2K/ZhyDZgdix2LXYquKAjNmH2Kcg2K/YsSDYr9iz2KrYsdizINmG24zYs9iqLjwvZGl2Pid9fQphc3luYyBmdW5jdGlvbiBsb2FkQ3J5cHRvKCl7Z28oJ2NyeXB0b1ZpZXcnKTtsZXQgYj0kKCdjcnlwdG9Cb2R5Jyk7Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yr9ixINit2KfZhCDYr9ix24zYp9mB2Kog2KjYp9iy2KfYsSDZiNin2YLYuduM4oCmPC9kaXY+Jzt0cnl7bGV0IGQ9YXdhaXQgYXBpKCcvYXBpL2NyeXB0by9jYXRhbG9nJyx7fSwxNTAwMCk7bGV0IGNhcmRzPShkLml0ZW1zfHxbXSkubWFwKGk9PmA8ZGl2IGNsYXNzPSJhc3NldENoaXAiPjxkaXYgY2xhc3M9ImZsZXgiPjxiPiR7ZXNjKGkubGFiZWwpfTwvYj48YnV0dG9uIGNsYXNzPSJ0YWIiIG9uY2xpY2s9InRvZ2dsZUNyeXB0bygnJHtpLmtleX0nLCR7aS5zZWxlY3RlZD8ndHJ1ZSc6J2ZhbHNlJ30pIj4ke2kuc2VsZWN0ZWQ/J+KckyDYp9mG2KrYrtin2KgnOifvvIsg2KfZgdiy2YjYr9mGJ308L2J1dHRvbj48L2Rpdj48ZGl2IGNsYXNzPSJwcmljZSI+JHtmbXQoaS5wcmljZSl9IFVTRFQ8L2Rpdj48ZGl2IGNsYXNzPSIke2NscyhpLmNoYW5nZSl9Ij4ke3BjdChpLmNoYW5nZSl9PC9kaXY+PGRpdiBjbGFzcz0idGlueSBtdXRlZCI+MjRIIEggJHtmbXQoaS5oaWdoKX0g4oCiIEwgJHtmbXQoaS5sb3cpfTwvZGl2PjxidXR0b24gY2xhc3M9ImJ0biBkYXJrIiBzdHlsZT0id2lkdGg6MTAwJTttYXJnaW4tdG9wOjhweCIgb25jbGljaz0ib3BlbkNyeXB0bygnJHtpLmtleX0nKSI+2KzYstim24zYp9iqINmI2KfZgti524w8L2J1dHRvbj48L2Rpdj5gKS5qb2luKCcnKTtiLmlubmVySFRNTD1gPGRpdiBjbGFzcz0iY2FyZCI+PGRpdiBjbGFzcz0iZmxleCI+PGI+2KfZhtiq2K7Yp9io4oCM2YfYp9uMINmF2YY8L2I+PHNwYW4gY2xhc3M9InBpbGwiPiR7KGQuc2VsZWN0ZWR8fFtdKS5sZW5ndGh9LyR7ZC5saW1pdH08L3NwYW4+PC9kaXY+PC9kaXY+PGRpdiBjbGFzcz0iYXNzZXRIdWIiIHN0eWxlPSJtYXJnaW4tdG9wOjEwcHgiPiR7Y2FyZHN9PC9kaXY+YH1jYXRjaChlKXtiLmlubmVySFRNTD0nPGRpdiBjbGFzcz0iZW1wdHkiPtiv2KfYr9mHINiy2YbYr9mHINio2KfYstin2LEg2K/YsSDYr9iz2KrYsdizINmG24zYs9iqLjwvZGl2Pid9fQphc3luYyBmdW5jdGlvbiB0b2dnbGVDcnlwdG8oa2V5LHNlbGVjdGVkKXt0cnl7YXdhaXQgYXBpKCcvYXBpL2NyeXB0by93YXRjaGxpc3Qvc2F2ZScse2Fzc2V0OmtleSxhY3Rpb246c2VsZWN0ZWQ/J3JlbW92ZSc6J2FkZCd9KTtsb2FkQ3J5cHRvKCl9Y2F0Y2goZSl7YWxlcnQoZS5zdGF0dXM9PT0yMDA/J9in2YbYrNin2YUg2LTYryc6J9iz2YLZgSDYp9mG2KrYrtin2Kgg24zYpyDYrti32KfbjCDYqNin2LLYp9ixJyl9fQphc3luYyBmdW5jdGlvbiBvcGVuQ3J5cHRvKGtleSl7Z28oJ2NyeXB0b1ZpZXcnKTtsZXQgYj0kKCdjcnlwdG9Cb2R5Jyk7Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yr9ixINit2KfZhCDYqtit2YTbjNmEINqp2YbYr9mE4oCM2YfYp9uMINmI2KfZgti524zigKY8L2Rpdj4nO3RyeXtsZXQgZD1hd2FpdCBhcGkoJy9hcGkvY3J5cHRvL2Fzc2V0Jyx7YXNzZXQ6a2V5fSwyMDAwMCksdD1kLnRpY2tlcnx8e30scz1kLnNpZ25hbHx8e307bGV0IHN0YXRlQ2FyZD1gPGRpdiBjbGFzcz0ic2VjdGlvbiI+2YjYtti524zYqiDZgdix2LXYqjwvZGl2PjxkaXYgY2xhc3M9ImNhcmQiPjxkaXYgY2xhc3M9ImZsZXgiPjxiIGNsYXNzPSIke3Muc2lkZT09PSdCVVknPyd1cCc6cy5zaWRlPT09J1NFTEwnPydkb3duJzonZmxhdCd9Ij4ke2VzYyhzLnNpZGU9PT0nQlVZJz8n2YHYsdi12Kog2K7YsduM2K8nOnMuc2lkZT09PSdTRUxMJz8n2YHYsdi12Kog2YHYsdmI2LQnOnMuc2lkZT09PSdOT19TSUdOQUwnPyfYr9in2K/ZhyDYqNix2KfbjCDYqti12YXbjNmFINqp2KfZgduMINmG24zYs9iqJzon2YHYudmE2KfZiyDZgdix2LXYqiDZhdmG2KfYs9io24wg2K/bjNiv2Ycg2YbZhduM4oCM2LTZiNivJyl9PC9iPjxzcGFuPtmC2K/YsdiqICR7cy5zY29yZT8/J+KAlCd9IOKAoiDaqduM2YHbjNiqICR7cy5kYXRhX3F1YWxpdHk/PyfigJQnfTwvc3Bhbj48L2Rpdj4ke3MubG9ja2VkPyc8ZGl2IGNsYXNzPSJ0aW55IG11dGVkIj7wn5SSINis2LLYptuM2KfYqiDZiNix2YjYr9iMINit2K8g2LbYsdix2Iwg2YfYr9mB4oCM2YfYpyDZiCDYqtit2YTbjNmEINmB2YbbjCDaqdin2YXZhCDYqNix2KfbjCBWSVAg2YHYudin2YQg2KfYs9iqLjwvZGl2Pic6YDxkaXYgY2xhc3M9InRpbnkgbXV0ZWQiPiR7KHMucmVhc29uc3x8W10pLm1hcChlc2MpLmpvaW4oJyDigKIgJyl9PC9kaXY+YH08L2Rpdj5gO2xldCB0ZWNoPWQudmlwP2A8ZGl2IGNsYXNzPSJzZWN0aW9uIj7Yqtit2YTbjNmEINmB2YbbjCDaqdin2YXZhDwvZGl2PjxkaXYgY2xhc3M9Im1ldHJpY3MiPjxkaXYgY2xhc3M9Im1ldHJpYyI+2YLYr9ix2Kog2K3Ysdqp2Kog27HYs9in2LnYqtmHIChSU0kpPGI+JHtmaW5pdGUocy5yc2kpP051bWJlcihzLnJzaSkudG9GaXhlZCgxKTon4oCUJ308L2I+PC9kaXY+PGRpdiBjbGFzcz0ibWV0cmljIj7Zgtiv2LHYqiDYrdix2qnYqiDbsdu12K/ZgtuM2YLZhyAoUlNJKTxiPiR7ZmluaXRlKHMucnNpMTUpP051bWJlcihzLnJzaTE1KS50b0ZpeGVkKDEpOifigJQnfTwvYj48L2Rpdj48ZGl2IGNsYXNzPSJtZXRyaWMiPtmF24zYstin2YYg2YbZiNiz2KfZhiAoQVRSKTxiPiR7Zm10KHMuYXRyKX08L2I+PC9kaXY+PGRpdiBjbGFzcz0ibWV0cmljIj7YsdmI2YbYryDaqdmI2KrYp9mHIChFTUEyMCk8Yj4ke2ZtdChzLmVtYTIwKX08L2I+PC9kaXY+PGRpdiBjbGFzcz0ibWV0cmljIj7YsdmI2YbYryDYqNmE2YbYryAoRU1BNTApPGI+JHtmbXQocy5lbWE1MCl9PC9iPjwvZGl2PjxkaXYgY2xhc3M9Im1ldHJpYyI+2YbYs9io2Kog2K3YrNmFPGI+JHtmaW5pdGUocy52b2x1bWVfcmF0aW8pP051bWJlcihzLnZvbHVtZV9yYXRpbykudG9GaXhlZCgyKTon4oCUJ308L2I+PC9kaXY+PC9kaXY+PGRpdiBjbGFzcz0iY2FyZCIgc3R5bGU9Im1hcmdpbi10b3A6MTBweCI+PGRpdiBjbGFzcz0idGlueSBtdXRlZCI+2K3Zhdin24zYqiAke2ZtdChzLnN1cHBvcnQpfSDigKIg2YXZgtin2YjZhdiqICR7Zm10KHMucmVzaXN0YW5jZSl9IOKAoiBNQUNEICR7Zm10KHMubWFjZCl9IOKAoiDYrti3INiz24zar9mG2KfZhCAke2ZtdChzLm1hY2Rfc2lnbmFsKX08L2Rpdj48ZGl2IGNsYXNzPSJ0aW55IG11dGVkIj7Yqti32KjbjNmCINmF2YbYqNi5INiv2YjZhTogJHtlc2Mocy5jcm9zc19zb3VyY2V8fCfYr9ixINiv2LPYqtix2LMg2YbbjNiz2KonKX0ke2Zpbml0ZShzLmNyb3NzX3ByaWNlKT8nIOKAoiAnK2ZtdChzLmNyb3NzX3ByaWNlKTonJ308L2Rpdj48L2Rpdj5gOmA8ZGl2IGNsYXNzPSJsb2NrIiBzdHlsZT0ibWFyZ2luLXRvcDoxMHB4Ij7irZAg2KrYrdmE24zZhCDZgdmG24wg2qnYp9mF2YQg2KfbjNmGINin2LHYsiDYqNix2KfbjCBWSVAg2YHYudin2YQg2KfYs9iqLjwvZGl2PmA7Yi5pbm5lckhUTUw9YDxidXR0b24gY2xhc3M9ImJ0biBkYXJrIiBvbmNsaWNrPSJsb2FkQ3J5cHRvKCkiPuKGqSDYqNin2LLar9i02Ko8L2J1dHRvbj48ZGl2IGNsYXNzPSJoZXJvIiBzdHlsZT0ibWFyZ2luLXRvcDoxMHB4Ij48ZGl2IGNsYXNzPSJmbGV4Ij48ZGl2PjxkaXYgY2xhc3M9Im11dGVkIj4ke2VzYyh0LnN5bWJvbHx8a2V5KX08L2Rpdj48ZGl2IGNsYXNzPSJzY29yZSI+JHtmbXQodC5wcmljZSl9PC9kaXY+PC9kaXY+PGRpdiBjbGFzcz0iJHtjbHModC5jaGFuZ2UpfSI+JHtwY3QodC5jaGFuZ2UpfTwvZGl2PjwvZGl2PjxkaXYgY2xhc3M9InRpbnkgbXV0ZWQiPtmF2YbYqNi5OiAke2VzYyh0LnNvdXJjZXx8J9io2KfYstin2LEnKX08L2Rpdj48L2Rpdj4ke3N0YXRlQ2FyZH0ke3RlY2h9PGRpdiBjbGFzcz0ic2VjdGlvbiI+2qnZhtiv2YQg2YjYp9mC2LnbjDwvZGl2PjxkaXYgY2xhc3M9InRhYnMiIGlkPSJjdGYiPjxidXR0b24gY2xhc3M9InRhYiBhY3RpdmUiIG9uY2xpY2s9ImxvYWRDcnlwdG9DaGFydCgnJHtrZXl9JywnMWgnLHRoaXMpIj7bsSDYs9in2LnYqjwvYnV0dG9uPjxidXR0b24gY2xhc3M9InRhYiIgb25jbGljaz0ibG9hZENyeXB0b0NoYXJ0KCcke2tleX0nLCc0aCcsdGhpcykiPtu0INiz2KfYudiqPC9idXR0b24+PGJ1dHRvbiBjbGFzcz0idGFiIiBvbmNsaWNrPSJsb2FkQ3J5cHRvQ2hhcnQoJyR7a2V5fScsJzFkJyx0aGlzKSI+27Eg2LHZiNiyPC9idXR0b24+PC9kaXY+PGNhbnZhcyBpZD0iY3J5cHRvQ2hhcnQiPjwvY2FudmFzPjxkaXYgaWQ9ImNyeXB0b0NoYXJ0Tm90ZSIgY2xhc3M9InRpbnkgbXV0ZWQiPjwvZGl2PmA7YXdhaXQgbG9hZENyeXB0b0NoYXJ0KGtleSwnMWgnKX1jYXRjaChlKXtiLmlubmVySFRNTD0nPGRpdiBjbGFzcz0iZW1wdHkiPtis2LLYptuM2KfYqiDZiNin2YLYuduMINiv2LEg2K/Ys9iq2LHYsyDZhtuM2LPYqi48L2Rpdj4nfX0KZnVuY3Rpb24gZHJhd0NyeXB0b0NhbmRsZXMoYyl7bGV0IGN2PSQoJ2NyeXB0b0NoYXJ0Jyk7aWYoIWN2KXJldHVybjtsZXQgcj1jdi5nZXRCb3VuZGluZ0NsaWVudFJlY3QoKSxkcHI9d2luZG93LmRldmljZVBpeGVsUmF0aW98fDE7Y3Yud2lkdGg9TWF0aC5tYXgoMzIwLHIud2lkdGgqZHByKTtjdi5oZWlnaHQ9MjUwKmRwcjtsZXQgY3R4PWN2LmdldENvbnRleHQoJzJkJyk7Y3R4LnNldFRyYW5zZm9ybShkcHIsMCwwLGRwciwwLDApO2xldCBXPXIud2lkdGgsSD0yNTA7Y3R4LmNsZWFyUmVjdCgwLDAsVyxIKTtsZXQgcm93cz0oY3x8W10pLmZpbHRlcih4PT5maW5pdGUoeC5oKSYmZmluaXRlKHgubCkmJmZpbml0ZSh4Lm8pJiZmaW5pdGUoeC5jKSk7aWYoIXJvd3MubGVuZ3RoKXtjdHguZmlsbFN0eWxlPScjNjQ3NDhiJztjdHgudGV4dEFsaWduPSdjZW50ZXInO2N0eC5mb250PScxNnB4IFRhaG9tYSc7Y3R4LmZpbGxUZXh0KCfYr9in2K/ZhyDZiNin2YLYuduMINqp2KfZgduMINmG24zYs9iqJyxXLzIsSC8yKTtyZXR1cm59bGV0IGhpPU1hdGgubWF4KC4uLnJvd3MubWFwKHg9Pk51bWJlcih4LmgpKSksbG89TWF0aC5taW4oLi4ucm93cy5tYXAoeD0+TnVtYmVyKHgubCkpKSxwYWQ9KGhpLWxvfHwxKSouMDcsbWF4PWhpK3BhZCxtaW49bG8tcGFkLHk9cD0+SC0yMi0oTnVtYmVyKHApLW1pbikvKG1heC1taW4pKihILTQ0KSxzdGVwPShXLTI4KS9yb3dzLmxlbmd0aCxjdz1NYXRoLm1heCgyLHN0ZXAqLjU2KTtjdHguc3Ryb2tlU3R5bGU9JyNkY2U4ZjcnO2ZvcihsZXQgaT0xO2k8NTtpKyspe2N0eC5iZWdpblBhdGgoKTtjdHgubW92ZVRvKDgsSCppLzUpO2N0eC5saW5lVG8oVy04LEgqaS81KTtjdHguc3Ryb2tlKCl9cm93cy5mb3JFYWNoKCh4LGkpPT57bGV0IHh4PTE0K2kqc3RlcCtzdGVwLzIsY29sPU51bWJlcih4LmMpPj1OdW1iZXIoeC5vKT8nIzA3OTQ1NSc6JyNkOTJkMjAnO2N0eC5zdHJva2VTdHlsZT1jb2w7Y3R4LmZpbGxTdHlsZT1jb2w7Y3R4LmJlZ2luUGF0aCgpO2N0eC5tb3ZlVG8oeHgseSh4LmgpKTtjdHgubGluZVRvKHh4LHkoeC5sKSk7Y3R4LnN0cm9rZSgpO2xldCB5bz15KHgubykseWM9eSh4LmMpO2N0eC5maWxsUmVjdCh4eC1jdy8yLE1hdGgubWluKHlvLHljKSxjdyxNYXRoLm1heCgyLE1hdGguYWJzKHlvLXljKSkpfSk7Y3R4LmZpbGxTdHlsZT0nIzY0NzQ4Yic7Y3R4LmZvbnQ9JzExcHggVGFob21hJztjdHgudGV4dEFsaWduPSdsZWZ0JztjdHguZmlsbFRleHQoZm10KGhpKSw1LDE0KTtjdHguZmlsbFRleHQoZm10KGxvKSw1LEgtNSl9CmFzeW5jIGZ1bmN0aW9uIGxvYWRDcnlwdG9DaGFydChrZXksdGYsZWwpe2RvY3VtZW50LnF1ZXJ5U2VsZWN0b3JBbGwoJyNjdGYgLnRhYicpLmZvckVhY2goeD0+eC5jbGFzc0xpc3QucmVtb3ZlKCdhY3RpdmUnKSk7aWYoZWwpZWwuY2xhc3NMaXN0LmFkZCgnYWN0aXZlJyk7dHJ5e2xldCBkPWF3YWl0IGFwaSgnL2FwaS9jcnlwdG8vY2FuZGxlcycse2Fzc2V0OmtleSx0aW1lZnJhbWU6dGZ9LDE1MDAwKTtkcmF3Q3J5cHRvQ2FuZGxlcyhkLmNhbmRsZXN8fFtdKTskKCdjcnlwdG9DaGFydE5vdGUnKS50ZXh0Q29udGVudD1kLm5vdGV8fCcnfWNhdGNoKGUpeyQoJ2NyeXB0b0NoYXJ0Tm90ZScpLnRleHRDb250ZW50PWUuc3RhdHVzPT09NDAzPyfYp9uM2YYg2KrYp9uM2YXigIzZgdix24zZhSDZhdiu2LXZiNi1IFZJUCDYp9iz2KouJzon2K/Yp9iv2Ycg2qnZhtiv2YQg2YjYp9mC2LnbjCDYr9ixINiv2LPYqtix2LMg2YbbjNiz2KouJztkcmF3Q3J5cHRvQ2FuZGxlcyhbXSl9fQphc3luYyBmdW5jdGlvbiBsb2FkTGVhcm4oKXtnbygnbGVhcm5WaWV3Jyk7bGV0IGI9JCgnbGVhcm5Cb2R5Jyk7Yi5pbm5lckhUTUw9JzxkaXYgY2xhc3M9ImVtcHR5Ij7Yr9ixINit2KfZhCDYqNin2LHar9iw2KfYsduM4oCmPC9kaXY+Jzt0cnl7bGV0IGQ9YXdhaXQgYXBpKCcvYXBpL2dsb3NzYXJ5Jyk7bGV0IHRlcm1zPShkLml0ZW1zfHxbXSkubWFwKHg9PmA8ZGl2IGNsYXNzPSJjYXJkIj48YiBjbGFzcz0iZ29sZCI+JHtlc2MoeC50aXRsZSl9PC9iPjxkaXYgY2xhc3M9InRpbnkgbXV0ZWQiPiR7ZXNjKHguZGVzY3JpcHRpb24pfTwvZGl2PjwvZGl2PmApLmpvaW4oJycpO2xldCBmYXE9KGQuZmFxfHxbXSkubWFwKHg9PmA8ZGV0YWlscyBjbGFzcz0iY2FyZCI+PHN1bW1hcnk+PGI+JHtlc2MoeC5xKX08L2I+PC9zdW1tYXJ5PjxkaXYgY2xhc3M9InRpbnkgbXV0ZWQiIHN0eWxlPSJtYXJnaW4tdG9wOjdweCI+JHtlc2MoeC5hKX08L2Rpdj48L2RldGFpbHM+YCkuam9pbignJyk7Yi5pbm5lckhUTUw9YDxkaXYgY2xhc3M9ImFzc2V0SHViIj4ke3Rlcm1zfTwvZGl2PjxkaXYgY2xhc3M9InNlY3Rpb24iPtiz2YjYp9mE2KfYqiDZhdiq2K/Yp9mI2YQ8L2Rpdj48ZGl2IGNsYXNzPSJsaXN0Ij4ke2ZhcX08L2Rpdj5gfWNhdGNoKGUpe2IuaW5uZXJIVE1MPSc8ZGl2IGNsYXNzPSJlbXB0eSI+2LHYp9mH2YbZhdinINiv2LEg2K/Ys9iq2LHYsyDZhtuM2LPYqi48L2Rpdj4nfX0KCmxvYWQoKTtzZXRJbnRlcnZhbChyZWZyZXNoT3ZlcnZpZXcsMzAwMDApO3NldEludGVydmFsKGFzeW5jKCk9Pnt0cnl7YXdhaXQgc3luY1Nlc3Npb24oKX1jYXRjaChlKXt9fSw2MDAwMCk7Cjwvc2NyaXB0PjwvYm9keT48L2h0bWw+").decode("utf-8")

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
    for asset in ("usd","gold18","melted","melted_future","aed","emami","half","quarter","ounce","btc","eth","usdt"):
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
    lines=["🎯 <b>اسکن فرصت‌های بازار</b>", "رتبه‌بندی بر اساس شدت حرکت، هم‌جهتی عوامل، شکست محدوده و کیفیت داده؛ نه دستور خرید.", ""]
    for rank,(_,asset,f) in enumerate(candidates[:7],1):
        direction="⬆️" if (f["score"] or 50)>50 else ("⬇️" if (f["score"] or 50)<50 else "➡️")
        flags=[]
        if f.get("breakout") != "none": flags.append("شکست")
        if f.get("abnormal"): flags.append("جهش نوسان")
        if f.get("z") is not None and abs(f["z"])>=2: flags.append("کشیدگی قیمت")
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


def _site_support_url():
    username = (ADMIN_USERNAME or DEVELOPER_USERNAME or "").strip().lstrip("@")
    return f"https://t.me/{username}" if username else "#contact"


def _site_bot_url():
    username = (BOT_PUBLIC_USERNAME or "").strip().lstrip("@")
    return f"https://t.me/{username}" if username else ""


def _landing_page_html():
    support_url=html.escape(_site_support_url(),quote=True); bot_url=html.escape(_site_bot_url(),quote=True)
    p30=html.escape(str(VIP_PRICE_30)); p90=html.escape(str(VIP_PRICE_90))
    cta=(f"<a class='btn primary' href='{bot_url}' target='_blank' rel='noopener'>ورود به ربات تلگرام</a>" if bot_url else f"<a class='btn primary' href='{support_url}' target='_blank' rel='noopener'>پشتیبانی طلایار</a>")
    faq=''.join(f"<details><summary>{html.escape(q)}</summary><p>{html.escape(a)}</p></details>" for q,a in FAQ_ITEMS)
    glossary=''.join(f"<article class='term'><b>{html.escape(v[0])}</b><span>{html.escape(v[1])}</span></article>" for v in GLOSSARY.values())
    return f"""<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><meta name='theme-color' content='#ffffff'><meta name="enamad" content="294297749"/><title>طلایار | دستیار هوشمند بازار</title><meta name='description' content='طلایار؛ رصد واقعی بازار، نمودار، هشدار، سیگنال الگوریتمی و ابزارهای طلا و کریپتو.'><style>
:root{{--blue:#0969ef;--blue2:#eaf3ff;--gold:#e5ab22;--ink:#10213d;--muted:#64748b;--line:#dce8f7;--card:#fff;--soft:#f6f9fd;--green:#079455;--red:#d92d20}}*{{box-sizing:border-box}}html{{scroll-behavior:smooth}}body{{margin:0;background:#fff;color:var(--ink);font-family:Tahoma,Arial,sans-serif;line-height:1.9}}a{{color:inherit}}.wrap{{width:min(1140px,calc(100% - 30px));margin:auto}}nav{{position:sticky;top:0;z-index:10;background:#ffffffea;backdrop-filter:blur(16px);border-bottom:1px solid var(--line)}}.nav{{height:70px;display:flex;align-items:center;justify-content:space-between;gap:14px}}.brand{{font-size:25px;font-weight:900;color:#0a4fa9;text-decoration:none}}.brand i{{font-style:normal;color:var(--gold)}}.links{{display:flex;gap:18px;color:var(--muted);font-size:13px}}.links a{{text-decoration:none}}.hero{{padding:76px 0 46px;background:radial-gradient(circle at 18% 20%,#e8f3ff 0,transparent 34%),radial-gradient(circle at 88% 8%,#fff5d9 0,transparent 24%)}}.heroGrid{{display:grid;grid-template-columns:1.08fr .92fr;gap:34px;align-items:center}}.badge{{display:inline-block;padding:6px 11px;border-radius:999px;background:var(--blue2);color:var(--blue);font-size:12px;font-weight:800}}h1{{font-size:clamp(42px,7vw,76px);line-height:1.24;margin:15px 0 12px;letter-spacing:-1.5px}}.blue{{color:var(--blue)}}.lead{{color:var(--muted);font-size:18px;max-width:700px}}.actions{{display:flex;gap:10px;flex-wrap:wrap;margin-top:24px}}.btn{{display:inline-flex;min-height:49px;padding:0 20px;align-items:center;justify-content:center;border-radius:13px;text-decoration:none;font-weight:900;border:1px solid var(--line)}}.primary{{background:var(--blue);color:#fff;border-color:var(--blue);box-shadow:0 12px 30px #0969ef26}}.secondary{{background:#fff;color:var(--blue)}}.mock{{background:#fff;border:1px solid var(--line);border-radius:32px;padding:18px;box-shadow:0 28px 80px #37679c1a}}.mocktop{{display:flex;justify-content:space-between;margin-bottom:12px}}.live{{color:var(--green);font-size:12px}}.ticker{{display:grid;grid-template-columns:1fr auto;gap:8px;padding:14px;margin:9px 0;border-radius:16px;background:var(--soft);border:1px solid #ebf1f8}}.ticker b{{font-size:19px}}.gold{{color:#b57c00}}section{{padding:62px 0}}.head h2{{font-size:clamp(28px,4vw,44px);margin:0}}.head p{{color:var(--muted);margin:5px 0 25px}}.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:13px}}.card{{border:1px solid var(--line);border-radius:20px;padding:21px;background:#fff;box-shadow:0 10px 34px #1f5c9b0a}}.card strong{{display:block;font-size:18px;margin:7px 0}}.card p{{color:var(--muted);margin:0;font-size:14px}}.signal{{background:linear-gradient(135deg,#f8fbff,#fff9e7);border:1px solid #d8e7f9;border-radius:26px;padding:28px;display:grid;grid-template-columns:1fr 1fr;gap:20px}}.sigbox{{background:#fff;border:1px solid var(--line);border-radius:20px;padding:20px}}.buy{{color:var(--green)}}.plans{{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;max-width:850px}}.plan{{border:1px solid var(--line);border-radius:22px;padding:25px;background:#fff;position:relative}}.plan.featured{{border:2px solid #e7b331}}.tag{{position:absolute;top:-12px;left:18px;background:var(--gold);color:#3e2b00;border-radius:99px;padding:3px 10px;font-size:11px;font-weight:900}}.money{{font-size:34px;font-weight:900;color:var(--blue)}}.faq details{{border-bottom:1px solid var(--line);padding:14px 4px}}.faq summary{{font-weight:900;cursor:pointer}}.faq p{{color:var(--muted)}}.terms{{display:grid;grid-template-columns:repeat(2,1fr);gap:10px}}.term{{border:1px solid var(--line);background:var(--soft);border-radius:16px;padding:15px}}.term b{{display:block;color:var(--blue)}}.term span{{display:block;color:var(--muted);font-size:13px}}.notice{{background:#fff7e2;border-right:4px solid var(--gold);border-radius:12px;padding:12px 15px;margin-top:18px;color:#5f4b18}}footer{{border-top:1px solid var(--line);padding:28px 0 40px;color:var(--muted);font-size:13px}}.foot{{display:flex;justify-content:space-between;gap:15px;flex-wrap:wrap}}@media(max-width:850px){{.heroGrid,.signal{{grid-template-columns:1fr}}.grid{{grid-template-columns:1fr 1fr}}.links a:not(:last-child){{display:none}}}}@media(max-width:560px){{.grid,.plans,.terms{{grid-template-columns:1fr}}.actions .btn{{width:100%}}.hero{{padding-top:52px}}}}
</style></head><body><nav><div class='wrap nav'><a class='brand' href='/'>طلایار <i>✦</i></a><div class='links'><a href='#features'>امکانات</a><a href='#signals'>سیگنال</a><a href='#vip'>VIP</a><a href='#learn'>راهنما</a><a href='{support_url}' target='_blank'>پشتیبانی</a></div></div></nav><main><header class='hero'><div class='wrap heroGrid'><div><span class='badge'>دستیار هوشمند بازار طلا، ارز و کریپتو</span><h1>بازار را فقط نبین؛<br><span class='blue'>بفهم.</span></h1><p class='lead'>قیمت واقعی، نمودار حرفه‌ای، هشدار، سبد شخصی و موتور فرصت‌یاب با فیلتر کیفیت داده؛ اگر داده معتبر نباشد، طلایار عدد یا سیگنال ساختگی نمایش نمی‌دهد.</p><div class='actions'>{cta}<a class='btn secondary' href='#signals'>دیدن فرصت‌های بازار</a></div></div><div class='mock'><div class='mocktop'><b class='blue'>طلایار زنده</b><span class='live'>● بازار آنلاین</span></div><div class='ticker'><span>BTC/USDT<br><small style='color:var(--muted)'>داده واقعی بازار</small></span><b>لحظه‌ای</b></div><div class='ticker'><span>کیفیت داده<br><small style='color:var(--muted)'>تازگی + کندل واقعی + تطبیق منبع دوم</small></span><b class='gold'>کنترل کیفیت</b></div><div class='ticker'><span>کارنامه شفاف<br><small style='color:var(--muted)'>برد و باخت هر دو ثبت می‌شوند</small></span><b>قابل بررسی</b></div></div></div></header>
<section id='features'><div class='wrap'><div class='head'><h2>یک داشبورد، چند بازار</h2><p>امکانات اصلی طلایار حفظ شده‌اند و ابزارهای جدید بدون شلوغ‌کردن تجربه کاربر به آن اضافه شده‌اند.</p></div><div class='grid'><div class='card'>⚡<strong>قیمت لحظه‌ای</strong><p>طلا، دلار، انس و کریپتو بدون عدد نمایشی.</p></div><div class='card'>📈<strong>نمودار حرفه‌ای</strong><p>برای کریپتو کندل واقعی بازار؛ جزئیات RSI، EMA، MACD و ATR در تحلیل کامل.</p></div><div class='card'>🎯<strong>فرصت‌های خرید و فروش</strong><p>فرصت فقط وقتی نمایش داده می‌شود که قدرت و کیفیت داده کافی باشد.</p></div><div class='card'>₿<strong>کریپتوهای من</strong><p>۳ ارز برای کاربر رایگان و تا {CRYPTO_VIP_LIMIT} ارز برای VIP از فهرست پشتیبانی‌شده.</p></div><div class='card'>🔔<strong>پیگیری خودکار</strong><p>ثبت هدف‌ها، حد ضرر و تاریخچه قابل بررسی.</p></div><div class='card'>📘<strong>راهنمای مفاهیم</strong><p>توضیح ساده اصطلاحات تکنیکال داخل سایت و ربات.</p></div></div></div></section>
<section id='signals'><div class='wrap'><div class='signal'><div><div class='head'><h2>فرصت واقعی، نه عدد نمایشی</h2><p>نمونه کارت زیر فقط ساختار رابط است؛ اعداد واقعی تنها در لحظه از منبع زنده بازار محاسبه می‌شوند.</p></div><ul><li>کندل و حجم واقعی برای کریپتو</li><li>فیلتر سخت‌گیرانه کیفیت داده</li><li>بررسی چند بازه زمانی ۱۵دقیقه / ۱ساعت / ۴ساعت</li><li>ثبت محدوده ورود، حد ضرر، سه هدف و شناسه</li><li>نمایش وضعیت ساده بازار هنگام نبود فرصت معتبر</li></ul></div><div class='sigbox'><span class='buy'>● قالب فرصت زنده</span><h3>BTC/USDT</h3><p>وضعیت: خرید / فروش / فعلاً بدون فرصت</p><p>قدرت فرصت + کیفیت داده + ورود + حد ضرر + هدف‌ها</p><p style='color:var(--muted)'>همه مقادیر از داده واقعی محاسبه می‌شوند؛ این کارت عمداً عدد ساختگی ندارد.</p></div></div></div></section>
<section id='vip'><div class='wrap'><div class='head'><h2>پلن‌های VIP</h2><p>قیمت نهایی فعلی طلایار</p></div><div class='plans'><div class='plan featured'><span class='tag'>VIP</span><h3>یک‌ماهه</h3><div class='money'>{p30} <small>تومان</small></div><p>۳۰ روز دسترسی به ابزارهای VIP و سقف {CRYPTO_VIP_LIMIT} ارز شخصی.</p></div><div class='plan'><h3>سه‌ماهه</h3><div class='money'>{p90} <small>تومان</small></div><p>۹۰ روز دسترسی پیوسته به قابلیت‌های VIP.</p></div></div><div class='notice'>سیگنال و تحلیل بازار تضمین سود نیست. کارنامه فقط بر اساس سیگنال‌های ذخیره‌شده در دیتابیس محاسبه می‌شود.</div></div></section>
<section id='learn'><div class='wrap'><div class='head'><h2>راهنمای اصطلاحات</h2><p>برای اینکه کاربر بداند هر کلمه در ربات چه معنی دارد.</p></div><div class='terms'>{glossary}</div></div></section><section><div class='wrap faq'><div class='head'><h2>سوالات متداول</h2></div>{faq}</div></section></main><footer><div class='wrap foot'><div>© طلایار — v{APP_VERSION}</div><div><a href='/about'>درباره ما</a> · <a href='/contact'>تماس با ما</a> · <a href='/privacy'>حریم خصوصی</a> · <a href='/terms'>شرایط استفاده</a> · <a href='/refund'>بازگشت وجه</a> · <a href='{support_url}' target='_blank'>پشتیبانی</a></div></div></footer></body></html>"""


def _simple_site_page(title, body_html):
    support_url = html.escape(_site_support_url(), quote=True)
    safe_title = html.escape(title)
    return f"""<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'><meta name='theme-color' content='#ffffff'>
<title>{safe_title} | طلایار</title><style>
body{{margin:0;background:#090b10;color:#f5f6f8;font-family:Tahoma,Arial,sans-serif;line-height:2}}a{{color:#e7c765}}.wrap{{width:min(820px,calc(100% - 28px));margin:50px auto}}.box{{background:#11161e;border:1px solid #2c333e;border-radius:22px;padding:28px}}h1{{color:#e7c765;margin-top:0}}.muted{{color:#aab1bd}}.back{{display:inline-block;margin-top:20px;text-decoration:none;border:1px solid #3a414c;border-radius:12px;padding:7px 14px;color:#fff}}
</style></head><body><main class='wrap'><div class='box'><h1>{safe_title}</h1>{body_html}<a class='back' href='/'>بازگشت به صفحه اصلی</a></div><p class='muted'>پشتیبانی: <a href='{support_url}' target='_blank' rel='noopener'>تلگرام طلایار</a></p></main></body></html>"""


def _terms_page_html():
    return _simple_site_page("شرایط استفاده", """
<p>استفاده از طلایار به معنی پذیرش این شرایط است. طلایار یک ابزار اطلاع‌رسانی و تحلیلی بازار است و هیچ خروجی آن تضمین سود یا توصیه قطعی خرید و فروش نیست.</p>
<p>کاربر مسئول تصمیم‌های مالی خود است. امکان اختلاف یا تأخیر میان داده نمایش‌داده‌شده و بازار وجود دارد.</p>
<p>اشتراک VIP برای مدت درج‌شده در زمان خرید فعال می‌شود. فعال‌سازی پرداخت آنلاین فقط پس از تأیید نهایی تراکنش انجام می‌شود.</p>
<p>سوءاستفاده از سرویس، تلاش برای دورزدن محدودیت‌ها، ایجاد بار غیرعادی یا استفاده غیرمجاز از محتوای اختصاصی می‌تواند موجب محدودشدن دسترسی شود.</p>
""")


def _privacy_page_html():
    return _simple_site_page("حریم خصوصی", """
<p>طلایار برای ارائه سرویس، اطلاعات فنی لازم مانند شناسه تلگرام، تنظیمات کاربر، هشدارها، وضعیت اشتراک و سوابق مرتبط با سفارش را نگهداری می‌کند.</p>
<p>اطلاعات محرمانه کارت بانکی در سرور طلایار ذخیره نمی‌شود. پردازش اطلاعات پرداخت توسط درگاه پرداخت انجام می‌شود و طلایار فقط نتیجه و شناسه پیگیری لازم برای فعال‌سازی اشتراک را ثبت می‌کند.</p>
<p>اطلاعات کاربران برای فروش به اشخاص ثالث جمع‌آوری نمی‌شود. داده‌های فنی ممکن است برای امنیت، پشتیبانی و بهبود سرویس استفاده شوند.</p>
""")


def _about_page_html():
    return _simple_site_page("درباره طلایار", """<p>طلایار یک سرویس نرم‌افزاری برای نمایش داده بازار، هشدار قیمت، نمودار، ابزارهای محاسباتی و تحلیل الگوریتمی است.</p><p>هدف سرویس ساده‌کردن رصد بازار است و مدیریت دارایی یا تضمین بازده سرمایه‌گذاری ارائه نمی‌کند.</p>""")


def _contact_page_html():
    support_url=html.escape(_site_support_url(),quote=True)
    return _simple_site_page("تماس با ما", f"""<p>پشتیبانی طلایار از طریق حساب رسمی پشتیبانی در تلگرام انجام می‌شود.</p><p><a href='{support_url}' target='_blank' rel='noopener'>ورود به پشتیبانی تلگرام</a></p><p>در درخواست‌های مالی، شناسه سفارش یا کد پیگیری پرداخت را ارسال کنید و اطلاعات محرمانه کارت بانکی را برای پشتیبانی نفرستید.</p>""")


def _refund_page_html():
    return _simple_site_page("سیاست بازگشت وجه", """<p>اگر مبلغ از حساب کاربر کسر شود اما تراکنش توسط درگاه تأیید نشود، وضعیت تراکنش بر اساس نتیجه رسمی درگاه بررسی می‌شود و بازگشت وجه بانکی تابع فرآیند شبکه پرداخت است.</p><p>اگر پرداخت تأیید شده ولی اشتراک به دلیل خطای فنی فعال نشده باشد، پشتیبانی ابتدا فعال‌سازی را اصلاح می‌کند و در صورت عدم امکان ارائه خدمت، درخواست بازگشت وجه بررسی می‌شود.</p><p>پس از فعال‌شدن و استفاده از اشتراک دیجیتال، بازگشت وجه صرفاً در موارد نقص فنی قابل اثبات در ارائه خدمت و پس از بررسی پشتیبانی انجام می‌شود.</p>""")


class PaymentCallbackHandler(BaseHTTPRequestHandler):
    server_version = f"Talayar/{APP_VERSION}"

    def _send_enamad_verification(self, include_body):
        # Enamad requires an empty file at this exact path.  Supporting both
        # GET and HEAD keeps automated ownership checkers from receiving the
        # BaseHTTPRequestHandler default 501 response for HEAD requests.
        body = b""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", "0")
        self.end_headers()
        if include_body:
            self.wfile.write(body)

    def do_HEAD(self):
        parsed = urlparse(self.path)
        route = parsed.path.rstrip("/") or "/"
        if route == "/294297749.txt":
            self._send_enamad_verification(include_body=False)
            return
        self.send_response(404)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def _write_page(self, status_code, title, message):
        support_url = html.escape(_site_support_url(), quote=True)
        bot_url = html.escape(_site_bot_url(), quote=True)
        primary = (f"<a class='btn primary' href='{bot_url}' target='_blank' rel='noopener'>بازگشت به ربات</a>"
                   if bot_url else f"<a class='btn primary' href='{support_url}' target='_blank' rel='noopener'>پشتیبانی تلگرام</a>")
        body = (
            "<!doctype html><html lang='fa' dir='rtl'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(title)} | طلایار</title>"
            "<style>body{font-family:Tahoma,Arial,sans-serif;background:#090b10;color:#fff;display:grid;"
            "place-items:center;min-height:100vh;margin:0;padding:18px}.box{width:min(520px,100%);background:#11161e;"
            "border:1px solid #303744;padding:30px;border-radius:22px;text-align:center;line-height:2;box-shadow:0 24px 70px #0007}"
            "h2{color:#e7c765}.btn{display:inline-block;margin:8px 4px 0;padding:9px 16px;border-radius:12px;text-decoration:none;font-weight:800}"
            ".primary{background:#e7c765;color:#16120a}.dark{border:1px solid #3b4350;color:#fff}</style></head>"
            f"<body><div class='box'><h2>{html.escape(title)}</h2><p>{html.escape(message)}</p>"
            f"{primary}<a class='btn dark' href='/'>صفحه اصلی</a></div></body></html>"
        ).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
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

        if route == "/294297749.txt":
            self._send_enamad_verification(include_body=True)
            return

        if route == "/":
            body = _landing_page_html().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "public, max-age=120")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        if route == "/terms":
            body = _terms_page_html().encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return

        if route == "/privacy":
            body = _privacy_page_html().encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return

        if route == "/about":
            body = _about_page_html().encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return

        if route == "/contact":
            body = _contact_page_html().encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return

        if route == "/refund":
            body = _refund_page_html().encode("utf-8")
            self.send_response(200); self.send_header("Content-Type", "text/html; charset=utf-8"); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body); return

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
        mini_routes={"/api/session","/api/dashboard","/api/overview","/api/asset","/api/scanner","/api/fair-value","/api/candles","/api/preferences","/api/preferences/save","/api/smart-alert","/api/rsi-map","/api/backtest","/api/activity","/api/crypto/catalog","/api/crypto/watchlist/save","/api/crypto/asset","/api/crypto/candles","/api/signals","/api/signal-now","/api/glossary"}
        if route not in mini_routes:
            self._write_page(404,"صفحه پیدا نشد","آدرس درخواست‌شده معتبر نیست."); return
        try:
            length=min(int(self.headers.get("Content-Length","0") or 0),65536)
            payload=json.loads(self.rfile.read(length).decode("utf-8") or "{}")
            uid=_verify_telegram_init_data(str(payload.get("initData") or ""))
            if uid is None:
                code=401; data={"error":"unauthorized","message":"مینی‌اپ را از دکمه داخل ربات طلایار باز کنید."}
            elif route=="/api/session":
                # Critical bootstrap path: DB only, no BRS/Binance/network calls.
                data,code=_mini_session_payload(uid),200
            elif route in {"/api/dashboard","/api/overview"}:
                # Cache-first dashboard: responds immediately and refreshes BRS in background.
                market,age=get_market_data_cached(CACHE_PERSISTENT_STALE_MAX_SECONDS)
                if age is None or age>CACHE_TTL_SECONDS:
                    request_market_refresh_background(force=True)
                data=_mini_overview_payload(market or {},uid)
                if market is None:
                    data.update({"market_status":"degraded","market_error":"منبع بازار داخلی در حال بازیابی است","market_age":None})
                elif age is not None and age>CACHE_STALE_MAX_SECONDS:
                    data.update({"market_status":"stale","market_error":"نمایش آخرین داده معتبر؛ بروزرسانی در پس‌زمینه در حال انجام است","market_age":age})
                else:
                    data.update({"market_status":"ok","market_error":"","market_age":age})
                code=200
            elif route in {"/api/asset","/api/scanner","/api/fair-value","/api/rsi-map"}:
                # Analytical domestic-market routes never wait for BRS in the HTTP request.
                market,age=get_market_data_cached(CACHE_STALE_MAX_SECONDS)
                if age is None or age>CACHE_TTL_SECONDS:
                    request_market_refresh_background(force=True)
                if market is None:
                    code=503; data={"error":"market_unavailable","message":"داده تازه بازار داخلی موقتاً در دسترس نیست"}
                elif route=="/api/asset":
                    data,code=_mini_asset_payload(market,uid,str(payload.get("asset") or ""))
                elif route=="/api/scanner":
                    data,code=_mini_scanner_payload(market,uid)
                elif route=="/api/fair-value":
                    data,code=_mini_fair_value_payload(market,uid)
                else:
                    data,code=_mini_rsi_map_payload(market,uid)
                if isinstance(data,dict) and market is not None:
                    data.setdefault("market_age",age)
            elif route=="/api/preferences":
                data,code=_mini_preferences_payload(uid)
            elif route=="/api/preferences/save":
                data,code=_mini_save_preferences_payload(uid,payload.get("preferences") or {})
            elif route=="/api/smart-alert":
                data,code=_mini_smart_alert_payload(uid,str(payload.get("asset") or ""),str(payload.get("rule") or ""))
            elif route=="/api/backtest":
                data,code=_mini_backtest_payload(uid,str(payload.get("asset") or ""),str(payload.get("rule") or "confluence"))
            elif route=="/api/activity":
                data,code=_mini_activity_payload(uid)
            elif route=="/api/crypto/catalog":
                data,code=_crypto_catalog_payload(uid),200
            elif route=="/api/crypto/watchlist/save":
                asset=str(payload.get("asset") or "").lower(); action=str(payload.get("action") or "toggle")
                if asset not in SUPPORTED_CRYPTO: data,code={"error":"invalid_asset"},400
                else:
                    selected=set(crypto_watchlist(uid)); result=(crypto_watchlist_remove(uid,asset) and "removed") if (action=="remove" or (action=="toggle" and asset in selected)) else crypto_watchlist_add(uid,asset)
                    data,code={"version":APP_VERSION,"result":result,"selected":crypto_watchlist(uid),"limit":crypto_limit(uid),"vip":is_vip(uid)},200
            elif route=="/api/crypto/asset":
                data,code=_crypto_asset_payload(uid,str(payload.get("asset") or "").lower())
            elif route=="/api/crypto/candles":
                data,code=_crypto_candles_payload(uid,str(payload.get("asset") or "").lower(),str(payload.get("timeframe") or "1h"))
            elif route=="/api/signals":
                data,code=_signals_payload(uid)
            elif route=="/api/signal-now":
                if not is_vip(uid):
                    data,code={"error":"vip_required"},403
                else:
                    asset=str(payload.get("asset") or "").lower(); data=crypto_signal_snapshot(asset,force=True); code=200 if data.get("ok") else 503
            elif route=="/api/glossary":
                data,code=_glossary_payload(),200
            else:
                # /api/candles is based on local SQLite price history only.
                data,code=_mini_chart_payload(uid,str(payload.get("asset") or ""),str(payload.get("timeframe") or "24H"))
            body=json.dumps(data,ensure_ascii=False,separators=(",",":")).encode("utf-8")
            self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8")
            self.send_header("Cache-Control","no-store"); self.send_header("X-Content-Type-Options","nosniff"); self.send_header("Content-Length",str(len(body)))
            self.end_headers(); self.wfile.write(body)
        except BrokenPipeError:
            logger.info("Mini App client disconnected during %s",route)
        except Exception:
            logger.exception("Mini App API error on %s", route)
            body=b'{"error":"server_error","message":"internal error"}'; self.send_response(500)
            self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Cache-Control","no-store"); self.send_header("Content-Length",str(len(body)))
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
        market, error = await get_market_data_async()
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
        await update.message.reply_text("❌ اجرت نامعتبر؛ مبلغ اجرت به ازای هر گرم را عددی وارد کنید.")
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
    market, error = await get_market_data_async()
    if not market:
        await update.message.reply_text(f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=main_menu()); return
    db.update_last_seen(update.effective_user.id); db.increment_activity(update.effective_user.id)
    capture_history(market); await record_referral_interaction(update.effective_user.id, REF_ACTION_PRICE, context)
    await update.message.reply_text(build_gold_text(market)+f"\n<i>{DISCLAIMER}</i>", parse_mode="HTML", reply_markup=price_menu())


async def price_command_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    market, error = await get_market_data_async()
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
    await update.message.reply_text("✅ حذف شد." if db.remove_vip(int(context.args[0])) else "کاربر VIP نبود.")


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
    value = _parse_number(text) if flow in {"alert_value", "alert_edit", "calc_weight", "calc_fee", "portfolio_quantity", "portfolio_price"} else None

    if flow=="portfolio_quantity":
        if value is None or value<=0:
            await update.message.reply_text("❌ مقدار باید عددی و بزرگ‌تر از صفر باشد؛ برای لغو /cancel")
            return
        context.user_data["portfolio_quantity"]=float(value)
        context.user_data["flow"]="portfolio_price"
        asset=context.user_data.get("portfolio_asset")
        unit=PORTFOLIO_UNITS.get(asset,"واحد")
        await update.message.reply_text(f"میانگین قیمت خرید هر {unit} را به <b>تومان</b> بفرست.\nبرای لغو /cancel",parse_mode="HTML")
        return

    if flow=="portfolio_price":
        if value is None or value<=0:
            await update.message.reply_text("❌ قیمت خرید باید عددی و بزرگ‌تر از صفر باشد؛ برای لغو /cancel")
            return
        asset=context.user_data.get("portfolio_asset")
        qty=context.user_data.get("portfolio_quantity")
        if asset not in PORTFOLIO_ASSETS or not qty:
            clear_flow(context); await update.message.reply_text("اطلاعات موقعیت ناقص شد؛ دوباره از «سبد من» شروع کن.",reply_markup=main_menu()); return
        existing=next((p for p in db.portfolio_positions(user_id) if p["asset_key"]==asset),None)
        if existing is None and len(db.portfolio_positions(user_id))>=portfolio_limit(user_id):
            clear_flow(context); await update.message.reply_text(f"سقف سبد شما {portfolio_limit(user_id)} موقعیت است.",reply_markup=main_menu()); return
        db.upsert_portfolio_position(user_id,asset,float(qty),float(value))
        clear_flow(context)
        market,_=await get_market_data_async(force_refresh=True)
        if market: save_portfolio_snapshot_for_user(user_id,market)
        await update.message.reply_text("✅ موقعیت سبد ذخیره شد.\n\n"+build_portfolio_text(user_id,market or {}),parse_mode="HTML",reply_markup=portfolio_menu(user_id))
        return

    if flow=="smart_question":
        market,error=await get_market_data_async(force_refresh=True)
        clear_flow(context)
        if not market:
            await update.message.reply_text(f"❌ {error or 'داده بازار دریافت نشد'}",reply_markup=main_menu()); return
        await update.message.reply_text(_smart_answer(user_id,text,market),parse_mode="HTML",reply_markup=smart_ask_menu())
        return

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
            market, error = await get_market_data_async()
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
            market, _ = await get_market_data_async()
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
        await _show_callback_text(q, "📊 بازار را انتخاب کن:", reply_markup=price_menu())
        return


    if data == "signals":
        perf=signal_performance(30)
        hr="—" if perf["hit_rate"] is None else f"{perf['hit_rate']:.1f}%"
        await _show_callback_text(q,
            "🎯 <b>فرصت‌های خرید و فروش طلایار</b>\n\n"
            "طلایار فقط با داده واقعی و تازه بازار فرصت صادر می‌کند. اگر شرایط کافی نباشد، "
            "به‌جای ساخت سیگنال، وضعیت بازار را ساده و شفاف نشان می‌دهد. نسخه رایگان یک نمای کلی واقعی دارد و جزئیات ورود، اهداف و حد ضرر برای VIP فعال است.\n\n"
            f"📊 کارنامه ۳۰ روزه ثبت‌شده: {perf['total']} سیگنال | نرخ موفقیت بسته‌شده: {hr}\n\n"
            "⚠️ هیچ سیگنالی تضمین سود ۱۰۰٪ نیست.",reply_markup=signal_menu(),parse_mode="HTML"); return

    if data == "crypto_lab":
        selected=crypto_watchlist(user_id); limit=crypto_limit(user_id)
        await _show_callback_text(q,f"₿ <b>کریپتوهای من</b>\n\n{len(selected)}/{limit} انتخاب شده. هر ارز انتخابی در مینی‌اپ قیمت و کندل واقعی دارد؛ تحلیل فنی کامل و جزئیات فرصت‌ها برای VIP فعال است.",reply_markup=crypto_lab_menu(user_id),parse_mode="HTML"); return

    if data.startswith("cw_add:"):
        asset=data.split(":",1)[1]; result=crypto_watchlist_add(user_id,asset)
        msg={"added":"✅ اضافه شد","exists":"این ارز از قبل انتخاب شده","limit":f"❌ سقف شما {crypto_limit(user_id)} ارز است","invalid":"❌ ارز نامعتبر"}.get(result,result)
        await q.answer(msg,show_alert=result in {"limit","invalid"}); await _show_callback_text(q,f"₿ کریپتوهای من — {len(crypto_watchlist(user_id))}/{crypto_limit(user_id)}",reply_markup=crypto_lab_menu(user_id)); return

    if data.startswith("cw_remove:"):
        asset=data.split(":",1)[1]; crypto_watchlist_remove(user_id,asset); await q.answer("حذف شد"); await _show_callback_text(q,f"₿ کریپتوهای من — {len(crypto_watchlist(user_id))}/{crypto_limit(user_id)}",reply_markup=crypto_lab_menu(user_id)); return

    if data in {"signal_scan","signal_history","signal_performance"}:
        if data=="signal_scan" and not is_vip(user_id):
            keys=crypto_watchlist(user_id) or list(DEFAULT_CRYPTO_KEYS[:1]); key=keys[0]
            snap=crypto_signal_snapshot(key,force=True); label=SUPPORTED_CRYPTO[key]["label"]
            if snap.get("ok"):
                text=(f"🎯 <b>نمای رایگان وضعیت بازار — {html.escape(label)}</b>\n\n"
                      f"{_signal_state_message(snap)}\n"
                      f"قدرت فرصت: <b>{snap.get('score','—')}/100</b> | کیفیت داده: <b>{snap.get('data_quality','—')}/100</b>\n"
                      f"قیمت بررسی‌شده: <b>{_format_number(snap.get('price'))} USDT</b>\n\n"
                      "🔒 محدوده ورود، حد ضرر، سه هدف و اسکن کامل ارزهای انتخابی برای کاربران VIP فعال است.\n\n"
                      "<i>این نمای رایگان از داده واقعی ساخته می‌شود و تضمین سود نیست.</i>")
            else:
                text=(f"🎯 <b>نمای رایگان وضعیت بازار — {html.escape(label)}</b>\n\n"
                      "داده معتبر کافی برای ارزیابی فعلی در دسترس نیست. طلایار عدد یا فرصت ساختگی نمایش نمی‌دهد.\n\n"
                      "🔒 اسکن کامل و جزئیات فرصت‌ها برای کاربران VIP فعال است.")
            await _show_callback_text(q,text,reply_markup=vip_menu(user_id),parse_mode="HTML"); return
        if data=="signal_performance":
            p=signal_performance(30); r1="—" if p["tp1_rate"] is None else f"{p['tp1_rate']:.1f}%"; r3="—" if p["tp3_rate"] is None else f"{p['tp3_rate']:.1f}%"
            text=(f"📊 <b>کارنامه شفاف سیگنال‌ها — ۳۰ روز</b>\n\n"
                  f"کل سیگنال‌ها: {p['total']}\nهدف اول رسیده: {p['tp1']}\nهدف دوم رسیده: {p['tp2']}\nهدف سوم رسیده: {p['tp3']}\n"
                  f"حد ضرر قبل از هدف: {p['sl']}\nحد ضرر بعد از هدف: {p['sl_after_target']}\nسربه‌سر: {p['breakeven']}\nنتیجه مبهم: {p['ambiguous']}\nباز: {p['open']}\n\n"
                  f"نرخ رسیدن به هدف اول در معاملات بسته و قابل ارزیابی: {r1}\nنرخ رسیدن به هدف سوم: {r3}\n\n"
                  "<i>همه اعداد مستقیم از رکوردهای دیتابیس محاسبه می‌شوند؛ نتیجه مبهم در نرخ‌ها شمرده نمی‌شود.</i>")
            await _show_callback_text(q,text,reply_markup=signal_menu(),parse_mode="HTML"); return
        if data=="signal_history":
            sigs=recent_signals(12); lines=["🧾 <b>آخرین سیگنال‌های ثبت‌شده</b>",""]
            for x in sigs: lines.append(f"{('🟢' if x['side']=='BUY' else '🔴')} <b>{html.escape(SUPPORTED_CRYPTO.get(x['asset_key'],{}).get('label',x['asset_key']))}</b> {_signal_side_fa(x['side'])} | قدرت {x['score']}/100 | کیفیت {x['data_quality']}/100 | {html.escape(_signal_status_fa(x['status']))}")
            if not sigs: lines.append("هنوز سیگنال ثبت‌شده‌ای وجود ندارد.")
            await _show_callback_text(q,"\n".join(lines),reply_markup=signal_menu(),parse_mode="HTML"); return
        keys=crypto_watchlist(user_id) or list(DEFAULT_CRYPTO_KEYS[:crypto_limit(user_id)]); lines=["⚡ <b>بررسی فرصت‌های بازار</b>",""]
        for key in keys[:crypto_limit(user_id)]:
            snap=crypto_signal_snapshot(key,force=True); label=SUPPORTED_CRYPTO[key]["label"]
            if not snap.get("ok"):
                lines.append(f"⚪ <b>{label}</b>: داده معتبر کافی نیست")
                continue
            side=snap.get("side"); icon="🟢" if side=="BUY" else "🔴" if side=="SELL" else "🟡" if int(snap.get("score") or 0)>=max(60,SIGNAL_MIN_SCORE-8) else "⚪"
            lines.append(f"{icon} <b>{label}</b>: {_signal_state_message(snap)}")
            lines.append(f"↳ قدرت فرصت {snap.get('score')}/100 | کیفیت داده {snap.get('data_quality')}/100 | قیمت {_format_number(snap.get('price'))} USDT")
            if side in {"BUY","SELL"}:
                sid=persist_signal(snap)
                lines.append(f"↳ ورود {_format_number(snap['entry_low'])}–{_format_number(snap['entry_high'])} | حد ضرر {_format_number(snap['stop_loss'])} | هدف اول {_format_number(snap['tp1'])}"+(f" | ID {sid}" if sid else " | قبلاً ثبت شده"))
        lines += ["","<i>بازار دائماً زیر نظر است؛ نبود فرصت معتبر به معنی خرابی موتور نیست. هیچ سیگنالی تضمین سود نیست.</i>"]
        await _show_callback_text(q,"\n".join(lines),reply_markup=signal_menu(),parse_mode="HTML"); return

    if data == "glossary":
        await _show_callback_text(q,glossary_text(),reply_markup=glossary_menu(),parse_mode="HTML"); return
    if data.startswith("term:"):
        key=data.split(":",1)[1]; await _show_callback_text(q,glossary_text(key),reply_markup=glossary_menu(),parse_mode="HTML"); return
    if data == "faq":
        lines=["❓ <b>سوالات متداول طلایار</b>",""]
        for qn,ans in FAQ_ITEMS: lines += [f"<b>{html.escape(qn)}</b>",html.escape(ans),""]
        await _show_callback_text(q,"\n".join(lines),reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📘 اصطلاحات بازار",callback_data="glossary")],[InlineKeyboardButton("🔙 منوی اصلی",callback_data="home")]]),parse_mode="HTML"); return

    if data in {"gold", "iran_currency", "ounce", "crypto"}:
        market, error = await get_market_data_async(force_refresh=False)
        if market is None:
            await _show_callback_text(q, f"❌ {error}", reply_markup=price_menu())
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
        await _show_callback_text(q, text + f"\n<i>{DISCLAIMER}</i>", reply_markup=price_menu(), parse_mode="HTML")
        return

    if data == "melted_center":
        market,error=await get_market_data_async()
        if not market:
            await _show_callback_text(q, f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=main_menu()); return
        capture_history(market)
        await _show_callback_text(q, build_melted_center(market), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 بروزرسانی",callback_data="melted_center")],[InlineKeyboardButton("🔙 منوی اصلی",callback_data="home")]]), parse_mode="HTML"); return

    if data == "navasan":
        if not is_vip(user_id):
            await _show_callback_text(q, "⚡ مرکز نوسان حرفه‌ای مخصوص کاربران VIP است.", reply_markup=vip_menu(user_id))
            return
        market, error = await get_market_data_async()
        if market:
            capture_history(market)
        await _show_callback_text(q, "⚡ <b>Talayar Navasan Intelligence v13</b>\n\nتحلیل چندلایه، رادار انحراف، اسکن فرصت، اعتبارسنجی تاریخی و هشدارهای هوشمند.", reply_markup=navasan_menu(), parse_mode="HTML")
        return

    if data == "nv:scanner":
        if not is_vip(user_id):
            await _show_callback_text(q, "این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        market,error=await get_market_data_async()
        if not market:
            await _show_callback_text(q, f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=navasan_menu()); return
        capture_history(market)
        await _show_callback_text(q, build_opportunity_scanner(market), reply_markup=navasan_menu(), parse_mode="HTML")
        return

    if data == "nv:bubble":
        if not is_vip(user_id):
            await _show_callback_text(q, "این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        market,error=await get_market_data_async()
        if not market:
            await _show_callback_text(q, f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=navasan_menu()); return
        capture_history(market)
        await _show_callback_text(q, build_bubble_radar(market), reply_markup=navasan_menu(), parse_mode="HTML")
        return

    if data == "nv:heatmap":
        if not is_vip(user_id):
            await _show_callback_text(q, "این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        market,error=await get_market_data_async()
        if not market:
            await _show_callback_text(q, f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=navasan_menu()); return
        capture_history(market)
        await _show_callback_text(q, build_heatmap(market), reply_markup=navasan_menu(), parse_mode="HTML")
        return

    if data == "nv:assetmenu":
        if not is_vip(user_id):
            await _show_callback_text(q, "این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        await _show_callback_text(q, "دارایی را برای تحلیل چندلایه انتخاب کن:", reply_markup=navasan_asset_menu("nv:asset")); return

    if data.startswith("nv:asset:"):
        if not is_vip(user_id):
            await _show_callback_text(q, "این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        asset=data.split(":",2)[2]
        market,error=await get_market_data_async()
        if not market:
            await _show_callback_text(q, f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=navasan_menu()); return
        capture_history(market)
        await _show_callback_text(q, build_navasan_asset_text(asset,market), reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 بروزرسانی",callback_data=f"nv:asset:{asset}")],[InlineKeyboardButton("🔙 انتخاب دارایی",callback_data="nv:assetmenu")]]), parse_mode="HTML")
        return

    if data == "nv:backtestmenu":
        if not is_vip(user_id):
            await _show_callback_text(q, "این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        await _show_callback_text(q, "دارایی را برای آزمایش تاریخی انتخاب کن:", reply_markup=navasan_asset_menu("nv:bt")); return

    if data.startswith("nv:bt:"):
        if not is_vip(user_id):
            await _show_callback_text(q, "این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        asset=data.split(":",2)[2]
        await _show_callback_text(q, build_backtest_text(asset), reply_markup=navasan_asset_menu("nv:bt"), parse_mode="HTML"); return

    if data == "nv:method":
        if not is_vip(user_id):
            await _show_callback_text(q, "این بخش مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        await _show_callback_text(q, navasan_method_text(), reply_markup=navasan_menu(), parse_mode="HTML"); return

    if data == "nv:smartalerts":
        if not is_vip(user_id):
            await _show_callback_text(q, "هشدار هوشمند مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        rows=[[InlineKeyboardButton("➕ افزودن هشدار هوشمند",callback_data="nv:saasset")]]
        items=db.user_smart_alerts(user_id)
        for i,a in enumerate(items,1):
            rows.append([InlineKeyboardButton(f"🗑 حذف {i}",callback_data=f"nv:sadel:{a['id']}")])
        if items: rows.append([InlineKeyboardButton("🧹 حذف همه",callback_data="nv:saclear")])
        rows.append([InlineKeyboardButton("🔙 مرکز نوسان",callback_data="navasan")])
        await _show_callback_text(q, build_smart_alerts_text(user_id), reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML"); return

    if data == "nv:saasset":
        if not is_vip(user_id):
            await _show_callback_text(q, "هشدار هوشمند مخصوص VIP است.", reply_markup=vip_menu(user_id)); return
        await _show_callback_text(q, "دارایی هشدار هوشمند را انتخاب کن:",reply_markup=navasan_asset_menu("nv:sarule")); return

    if data.startswith("nv:sarule:"):
        if not is_vip(user_id): return
        asset=data.split(":",2)[2]
        await _show_callback_text(q, f"قانون هشدار برای {ALERT_ASSETS.get(asset,{}).get('label',asset)}:",reply_markup=smart_alert_rule_menu(asset)); return

    if data.startswith("nv:saadd:"):
        if not is_vip(user_id): return
        _,_,asset,rule=data.split(":",3)
        result=db.add_smart_alert(user_id,q.message.chat.id,asset,rule)
        msg="✅ هشدار هوشمند فعال شد." if result=="added" else "✅ این هشدار از قبل وجود داشت و فعال است."
        await _show_callback_text(q, msg,reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🚨 هشدارهای من",callback_data="nv:smartalerts")],[InlineKeyboardButton("🔙 مرکز نوسان",callback_data="navasan")]])); return

    if data.startswith("nv:sadel:"):
        db.delete_smart_alert(data.split(":",2)[2],user_id)
        await _show_callback_text(q, "✅ هشدار حذف شد.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 هشدارهای هوشمند",callback_data="nv:smartalerts")]])); return

    if data == "nv:saclear":
        db.delete_user_smart_alerts(user_id)
        await _show_callback_text(q, "✅ همه هشدارهای هوشمند حذف شدند.",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 مرکز نوسان",callback_data="navasan")]])); return

    if data == "alerts":
        clear_flow(context)
        await _show_callback_text(q, "🔔 هشدار عددی، درصدی و تکرارشونده", reply_markup=alert_menu())
        return

    if data == "alert_new":
        if not is_vip(user_id) and len(db.user_alerts(user_id)) >= FREE_ALERT_LIMIT:
            await _show_callback_text(q, "سقف یک هشدار رایگان پر شده است.", reply_markup=alert_menu())
            return
        context.user_data["alert_draft"] = {}
        await _show_callback_text(q, "نوع هشدار را انتخاب کن:", reply_markup=alert_kind_menu(user_id))
        return

    if data.startswith("alert_kind:"):
        kind = data.split(":", 1)[1]
        if kind == "percent" and not is_vip(user_id):
            await _show_callback_text(q, "هشدار درصدی مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        context.user_data["alert_draft"] = {"type": kind}
        await _show_callback_text(q, "دارایی را انتخاب کن:", reply_markup=alert_asset_menu())
        return

    if data.startswith("alert_asset:"):
        asset = data.split(":", 1)[1]
        draft = context.user_data.get("alert_draft", {})
        draft["asset"] = asset
        await _show_callback_text(q, "شرط هشدار را انتخاب کن:",
                                  reply_markup=percent_condition_menu() if draft.get("type") == "percent" else alert_condition_menu())
        return

    if data.startswith("alert_condition:"):
        draft = context.user_data.get("alert_draft", {})
        draft["condition"] = data.split(":", 1)[1]
        await _show_callback_text(q, "نوع اجرا را انتخاب کن:", reply_markup=alert_mode_menu())
        return

    if data.startswith("alert_mode:"):
        mode = data.split(":", 1)[1]
        if mode == "repeat" and not is_vip(user_id):
            await _show_callback_text(q, "تکرارشونده مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        context.user_data["alert_draft"]["mode"] = mode
        context.user_data["flow"] = "alert_value"
        prompt = "درصد هدف را بفرست؛ مثال 2.5" if context.user_data["alert_draft"].get("type") == "percent" else "قیمت هدف را فقط به‌صورت عدد بفرست."
        await _show_callback_text(q, prompt + "\nبرای لغو /cancel")
        return

    if data == "alert_list":
        alerts = db.user_alerts(user_id)
        if not alerts:
            await _show_callback_text(q, "📋 شما هیچ هشدار فعالی ندارید.", reply_markup=alert_menu())
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
        await _show_callback_text(q, "\n".join(lines).rstrip(), reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML")
        return

    if data.startswith("alert_del:"):
        db.delete_alert(data.split(":", 1)[1], user_id)
        await _show_callback_text(q, "✅ حذف شد.", reply_markup=alert_menu())
        return

    if data.startswith("alert_edit:"):
        context.user_data["flow"] = "alert_edit"
        context.user_data["alert_edit_id"] = data.split(":", 1)[1]
        await _show_callback_text(q, "هدف جدید را فقط به‌صورت عدد بفرست. برای لغو /cancel")
        return

    if data == "alert_delete":
        await _show_callback_text(q, "همه هشدارها حذف شوند؟", reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ بله", callback_data="alert_delete_confirm")],
            [InlineKeyboardButton("❌ خیر", callback_data="alerts")]]))
        return

    if data == "alert_delete_confirm":
        db.delete_user_alerts(user_id)
        await _show_callback_text(q, "✅ همه هشدارها حذف شدند.", reply_markup=alert_menu())
        return

    if data == "daily":
        if not is_vip(user_id):
            await _show_callback_text(q, "گزارش روزانه مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        sub = db.get_daily_sub(user_id)
        status = f"فعال در {sub.get('time')}" if sub and sub.get("active") else "غیرفعال"
        await _show_callback_text(q, f"🗓 گزارش روزانه\nوضعیت: {status}\nساعت را انتخاب کن:", reply_markup=daily_menu(bool(sub and sub.get("active"))))
        return

    if data.startswith("daily_set:"):
        report_time = data.split(":", 1)[1]
        db.set_daily_sub(user_id, q.message.chat.id, report_time)
        await record_referral_interaction(user_id, REF_ACTION_DAILY, context)
        await _show_callback_text(q, f"✅ گزارش ساعت {report_time} فعال شد.", reply_markup=daily_menu(True))
        return

    if data == "daily_now":
        if not is_vip(user_id):
            await _show_callback_text(q, "گزارش روزانه مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        market, error = await get_market_data_async()
        if not market:
            await _show_callback_text(q, f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=daily_menu(False))
            return
        bot_username = await get_bot_username(context)
        await record_referral_interaction(user_id, REF_ACTION_DAILY, context)
        await _show_callback_text(
            q, build_personal_briefing(user_id, market),
            reply_markup=share_report_menu(user_id, bot_username, market),
            parse_mode="HTML",
        )
        return

    if data == "daily_custom":
        context.user_data["flow"] = "daily_time"
        await _show_callback_text(q, "ساعت را به وقت ایران مثل 09:30 بفرست. برای لغو /cancel")
        return

    if data == "daily_stop":
        sub = db.get_daily_sub(user_id)
        if sub:
            db.set_daily_sub(user_id, q.message.chat.id, sub.get("time", "09:00"), False)
        await _show_callback_text(q, "⛔ گزارش متوقف شد.", reply_markup=daily_menu(False))
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
        await _show_callback_text(q, text, reply_markup=main_menu(), parse_mode="HTML")
        return

    if data == "vip":
        await _show_callback_text(q, vip_text(user_id), reply_markup=vip_menu(user_id), parse_mode="HTML")
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
        await _show_callback_text(q, 
            f"🧾 بسته {plan} روزه — {price} تومان\n\n"
            f"روش اول: پرداخت آنلاین و فعال‌سازی فوری\n"
            f"روش دوم: {html.escape(PAYMENT_INFO)}"
            f"{gateway_note}",
            reply_markup=InlineKeyboardMarkup(rows), parse_mode="HTML")
        return

    if data.startswith("receipt:"):
        context.user_data.update({"flow": "receipt", "purchase_plan": int(data.split(":", 1)[1])})
        await _show_callback_text(q, "📷 حالا تصویر رسید را بفرست. برای لغو /cancel")
        return

    if data == "help":
        await _show_callback_text(q, help_text(), reply_markup=help_menu(), parse_mode="HTML")
        return

    if data == "support":
        context.user_data["flow"] = "support"
        await _show_callback_text(q, 
            support_prompt_text(),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💻 پیام مستقیم به توسعه‌دهنده", url=f"https://t.me/{DEVELOPER_USERNAME}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="help")],
            ]), parse_mode="HTML")
        return

    if data == "plans":
        await _show_callback_text(q, 
            "رایگان: قیمت‌ها، ماشین‌حساب، نمودار ۲۴ساعته و یک هشدار عددی.\n\n"
            f"VIP: هشدار نامحدود/درصدی/تکراری، گزارش روزانه، نمودار تکنیکال ۷ و ۳۰ روزه، "
            f"کندل و تحلیل حرفه‌ای دارایی‌های پشتیبانی‌شده، تحلیل هوشمند، بازار من تا {WATCHLIST_VIP_LIMIT} دارایی و مرکز فرصت‌های خرید و فروش.",
            reply_markup=vip_menu(user_id))
        return

    if data == "analysis":
        if not is_vip(user_id):
            await _show_callback_text(q, "تحلیل هوشمند مخصوص کاربران VIP است.", reply_markup=vip_menu(user_id))
            return
        market, error = await get_market_data_async()
        if not market:
            await _show_callback_text(q, f"❌ {error or 'داده بازار دریافت نشد'}", reply_markup=main_menu())
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

    if data in {"portfolio","portfolio_refresh"}:
        market,error=await get_market_data_async(force_refresh=(data=="portfolio_refresh"))
        if not market:
            await _show_callback_text(q,f"❌ {error or 'داده بازار دریافت نشد'}",reply_markup=portfolio_menu(user_id)); return
        capture_history(market)
        save_portfolio_snapshot_for_user(user_id,market)
        await _show_callback_text(q,build_portfolio_text(user_id,market),reply_markup=portfolio_menu(user_id),parse_mode="HTML"); return

    if data=="portfolio_add":
        positions=db.portfolio_positions(user_id)
        if len(positions)>=portfolio_limit(user_id):
            await _show_callback_text(q,f"سقف سبد شما {portfolio_limit(user_id)} موقعیت است.",reply_markup=portfolio_menu(user_id)); return
        await _show_callback_text(q,"دارایی را انتخاب کن:",reply_markup=portfolio_asset_menu()); return

    if data.startswith("portfolio_edit:"):
        asset=data.split(":",1)[1]
        context.user_data.update({"flow":"portfolio_quantity","portfolio_asset":asset})
        old=next((p for p in db.portfolio_positions(user_id) if p["asset_key"]==asset),None)
        hint=f"\nمقدار فعلی: {old['quantity']:g}" if old else ""
        await _show_callback_text(q,f"مقدار جدید {PORTFOLIO_UNITS.get(asset,'واحد')} را عددی بفرست.{hint}\nبرای لغو /cancel"); return

    if data.startswith("portfolio_del:"):
        asset=data.split(":",1)[1]
        db.remove_portfolio_position(user_id,asset)
        market,_=await get_market_data_async()
        await _show_callback_text(q,"✅ موقعیت حذف شد.\n\n"+build_portfolio_text(user_id,market or {}),reply_markup=portfolio_menu(user_id),parse_mode="HTML"); return

    if data.startswith("portfolio_asset:"):
        asset=data.split(":",1)[1]
        existing=next((p for p in db.portfolio_positions(user_id) if p["asset_key"]==asset),None)
        if existing is None and len(db.portfolio_positions(user_id))>=portfolio_limit(user_id):
            await _show_callback_text(q,f"سقف سبد شما {portfolio_limit(user_id)} موقعیت است.",reply_markup=portfolio_menu(user_id)); return
        context.user_data.update({"flow":"portfolio_quantity","portfolio_asset":asset})
        await _show_callback_text(q,f"مقدار {PORTFOLIO_UNITS.get(asset,'واحد')} را عددی بفرست.\nبرای لغو /cancel"); return

    if data=="smart_ask":
        await _show_callback_text(q,"💬 <b>از طلایار بپرس</b>\nپرسش‌های زیر مستقیم از داده و موتور تحلیلی خود طلایار پاسخ داده می‌شوند.",reply_markup=smart_ask_menu(),parse_mode="HTML"); return

    if data=="ask:text":
        context.user_data["flow"]="smart_question"
        await _show_callback_text(q,"سؤال کوتاهت را بفرست؛ مثل «خلاصه دلار و انس امروز» یا «سبدم چقدر سود کرده؟»\nبرای لغو /cancel"); return

    if data.startswith("ask:"):
        key=data.split(":",1)[1]
        prompts={"portfolio":"سبد و سود زیان من","markets":"دلار و انس و طلا","melted":"آبشده نقدی و فردایی","bubble":"حباب بازار","opportunity":"قوی ترین فرصت"}
        market,error=await get_market_data_async(force_refresh=True)
        if not market:
            await _show_callback_text(q,f"❌ {error or 'داده بازار دریافت نشد'}",reply_markup=smart_ask_menu()); return
        await _show_callback_text(q,_smart_answer(user_id,prompts.get(key,key),market),reply_markup=smart_ask_menu(),parse_mode="HTML"); return

    if data == "watchlist":
        if not is_vip(user_id):
            await _show_callback_text(q, "بازار من مخصوص کاربران VIP است.", reply_markup=vip_menu(user_id))
            return
        market, _ = await get_market_data_async()
        text = build_watchlist_text(user_id, market or {})
        await record_referral_interaction(user_id, REF_ACTION_ANALYSIS, context)
        await _show_callback_text(q, text, reply_markup=watchlist_menu(user_id), parse_mode="HTML")
        return

    if data == "wl_add":
        if not is_vip(user_id):
            await _show_callback_text(q, "بازار من مخصوص کاربران VIP است.", reply_markup=vip_menu(user_id))
            return
        if len(db.get_watchlist(user_id)) >= WATCHLIST_VIP_LIMIT:
            await _show_callback_text(q, 
                f"حداکثر {WATCHLIST_VIP_LIMIT} دارایی می‌توانید اضافه کنید.",
                reply_markup=watchlist_menu(user_id),
            )
            return
        await _show_callback_text(q, "دارایی را انتخاب کن:", reply_markup=watchlist_add_menu())
        return

    if data.startswith("wl_add:"):
        if not is_vip(user_id):
            await _show_callback_text(q, "بازار من مخصوص کاربران VIP است.", reply_markup=vip_menu(user_id))
            return
        asset = data.split(":", 1)[1]
        result = db.add_watchlist(user_id, asset)
        if result == "added":
            await _show_callback_text(q, f"✅ {ALERT_ASSETS.get(asset, {}).get('label', asset)} اضافه شد.", reply_markup=watchlist_menu(user_id))
        elif result == "limit":
            await _show_callback_text(q, f"❌ سقف بازار من {WATCHLIST_VIP_LIMIT} دارایی است.", reply_markup=watchlist_menu(user_id))
        else:
            await _show_callback_text(q, "❌ این دارایی قبلاً اضافه شده.", reply_markup=watchlist_menu(user_id))
        return

    if data.startswith("wl_remove:"):
        if not is_vip(user_id):
            await _show_callback_text(q, "بازار من مخصوص کاربران VIP است.", reply_markup=vip_menu(user_id))
            return
        asset = data.split(":", 1)[1]
        db.remove_watchlist(user_id, asset)
        market, _ = await get_market_data_async()
        text = build_watchlist_text(user_id, market or {})
        await _show_callback_text(q, text, reply_markup=watchlist_menu(user_id), parse_mode="HTML")
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
            market, error = await get_market_data_async()
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

    await _show_callback_text(q, "گزینه نامعتبر است.", reply_markup=main_menu())

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
            caption=(f"🚨 <b>هشدار هوشمند طلایار</b>\n\n{ALERT_ASSETS.get(asset,{}).get('label',asset)}\n"
                     f"قانون: <b>{smart_rule_label(a.get('rule'))}</b>\n{html.escape(detail)}\n"
                     f"قیمت: <b>{_format_number(f.get('price'))}</b> {html.escape(str(f.get('unit') or ''))}\n\n📸 Snapshot نمودار ۲۴ساعته")
            rendered=await asyncio.to_thread(_render_candle_chart,asset,24)
            if rendered:
                image_bytes,_=rendered; photo=BytesIO(image_bytes); photo.name="talayar_alert.png"
                await context.bot.send_photo(int(a["chat_id"]),photo=photo,caption=caption,parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚡ مرکز نوسان",callback_data="navasan")]]))
            else:
                await context.bot.send_message(int(a["chat_id"]),caption,parse_mode="HTML",reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⚡ مرکز نوسان",callback_data="navasan")]]))
            db.touch_smart_alert(a["id"],now)
            db.add_activity(a["user_id"],"smart_alert_triggered",asset,"هشدار هوشمند فعال شد",detail,f.get("price"),{"rule":a.get("rule"),"score":f.get("score"),"q":f.get("quality")})
        except Exception:
            logger.exception("Smart alert send failed")


async def market_job(context: ContextTypes.DEFAULT_TYPE):
    market, error = await get_market_data_async(force_refresh=True)
    if market is None or error:
        logger.warning("Alert check skipped (fresh BRS data unavailable): %s", error)
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
                f"قیمت فعلی: <b>{_format_number(current_price)} {item.get('unit') or ''}</b>\n"
                f"🕒 تریگر: {datetime.now(TEHRAN_TZ):%H:%M:%S}\n"
                f"🔎 چرا؟ {html.escape(detail)}\n📡 {_freshness_badge()}",
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


async def portfolio_snapshot_job(context: ContextTypes.DEFAULT_TYPE):
    # Additive snapshot only; never edits/deletes price_history or candle data.
    market,error=await get_market_data_async()
    if not market or error:
        logger.warning("Portfolio snapshot skipped (fresh market data unavailable): %s",error)
        return
    for uid in db.portfolio_user_ids():
        try:
            save_portfolio_snapshot_for_user(uid,market)
        except Exception:
            logger.exception("Portfolio snapshot failed for %s",uid)

async def daily_job(context: ContextTypes.DEFAULT_TYPE):
    subs = db.load_daily_subs()
    now = datetime.now(TEHRAN_TZ)
    due = [s for s in subs if s.get("active") and s.get("time") == now.strftime("%H:%M") and s.get("last_sent") != now.strftime("%Y-%m-%d")]
    if not due:
        return
    market, _ = await get_market_data_async()
    if not market:
        return
    bot_username = await get_bot_username(context)
    for sub in due:
        if not is_vip(sub.get("user_id")):
            with db._conn() as c:
                c.execute("UPDATE daily_subs SET active = 0 WHERE user_id = ?", (sub["user_id"],))
            continue
        try:
            save_portfolio_snapshot_for_user(sub["user_id"],market)
            report=build_personal_briefing(sub["user_id"],market)
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


async def _signal_watchers(asset_key):
    with db._conn() as c:
        rows=c.execute("SELECT user_id FROM crypto_watchlist WHERE asset_key=?",(asset_key,)).fetchall()
    return [int(r[0]) for r in rows if r and is_vip(int(r[0]))]


async def _notify_signal_event(context, sig, event_type, price, detail=""):
    labels={"tp1":"🎯 هدف اول رسید","tp2":"🎯 هدف دوم رسید","tp3":"✅ هدف سوم رسید","sl":"🛑 حد ضرر فعال شد","breakeven":"🟦 معامله سربه‌سر بسته شد","ambiguous":"⚠️ نتیجه این بازه مبهم است","breakeven_armed":"🛡 حد محافظ به نقطه ورود منتقل شد"}
    title=labels.get(event_type)
    if not title:
        return
    asset=sig.get("asset_key"); label=SUPPORTED_CRYPTO.get(asset,{}).get("label",asset)
    text=(f"{title}\n\n<b>{html.escape(label)}</b>\n"
          f"قیمت ثبت رویداد: <b>{_format_number(price)} USDT</b>\n"
          f"شناسه: <code>{html.escape(str(sig.get('signal_id') or ''))}</code>")
    if detail:
        text+=f"\n\n<i>{html.escape(detail)}</i>"
    for uid in await _signal_watchers(asset):
        try:
            await context.bot.send_message(uid,text,parse_mode="HTML")
        except Exception:
            logger.exception("Signal event notify failed for %s",uid)


async def signal_scan_job(context: ContextTypes.DEFAULT_TYPE):
    if not SIGNAL_ENGINE_ENABLED: return
    try:
        with db._conn() as c:
            rows=c.execute("SELECT DISTINCT asset_key FROM crypto_watchlist").fetchall()
        keys=[r[0] for r in rows if r and r[0] in SUPPORTED_CRYPTO]
        if not keys: keys=list(DEFAULT_CRYPTO_KEYS[:4])
        for key in keys:
            snap=await asyncio.to_thread(crypto_signal_snapshot,key,False)
            if not snap.get("ok") or snap.get("side") not in {"BUY","SELL"}:
                continue
            sid=persist_signal(snap)
            if not sid:
                continue
            reason=" • ".join(snap.get("reasons") or [])
            side_text=_signal_side_fa(snap["side"]); icon="🟢" if snap["side"]=="BUY" else "🔴"
            be_note="\n🛡 پس از رسیدن هدف اول، حد محافظ از کندل بعدی روی نقطه ورود قرار می‌گیرد." if SIGNAL_MOVE_TO_BE_AFTER_TP1 else ""
            for uid in await _signal_watchers(key):
                try:
                    await context.bot.send_message(
                        uid,
                        f"{icon} <b>{side_text} — {html.escape(SUPPORTED_CRYPTO[key]['label'])}</b>\n\n"
                        f"قدرت فرصت: <b>{snap['score']}/100</b> | کیفیت داده: <b>{snap['data_quality']}/100</b>\n"
                        f"قیمت لحظه صدور: <b>{_format_number(snap['price'])} USDT</b>\n"
                        f"محدوده ورود: {_format_number(snap['entry_low'])} تا {_format_number(snap['entry_high'])}\n"
                        f"حد ضرر: {_format_number(snap['stop_loss'])}\n"
                        f"هدف اول: {_format_number(snap['tp1'])}\nهدف دوم: {_format_number(snap['tp2'])}\nهدف سوم: {_format_number(snap['tp3'])}\n"
                        f"شناسه: <code>{sid}</code>{be_note}\n\n"
                        f"چرا؟ {html.escape(reason)}\n\n<i>منبع اصلی: Binance OHLCV واقعی. هیچ سیگنالی تضمین سود نیست.</i>",
                        parse_mode="HTML",
                    )
                except Exception:
                    logger.exception("Signal notify failed for %s",uid)
    except Exception:
        logger.exception("Signal scan job failed")


async def signal_track_job(context: ContextTypes.DEFAULT_TYPE):
    """Replay every unprocessed 1m candle in chronological order.

    This avoids the old four-candle observation window and preserves TP/SL events
    across ordinary Railway restarts. If one candle touches both the active stop
    and a new target, the result is marked ambiguous instead of guessing order.
    """
    if not SIGNAL_ENGINE_ENABLED: return
    try:
        open_signals=open_signals_for_tracking()
        by_asset={}
        for sig in open_signals:
            by_asset.setdefault(sig["asset_key"],[]).append(sig)
        for asset,sigs in by_asset.items():
            starts=[]
            for sig in sigs:
                dt=_parse_iso(sig.get("last_checked_at")) or _parse_iso(sig.get("created_at")) or datetime.now(timezone.utc)
                starts.append(dt)
            earliest=min(starts)-timedelta(minutes=1)
            rows,source,truncated=await asyncio.to_thread(_crypto_klines_since,asset,int(earliest.timestamp()*1000))
            if not rows:
                logger.warning("Signal replay unavailable for %s: %s",asset,source)
                continue
            if truncated:
                logger.info("Signal replay batch truncated for %s; next tracker run will continue",asset)
            for sig in sigs:
                last_dt=_parse_iso(sig.get("last_checked_at")) or _parse_iso(sig.get("created_at")) or earliest
                last_ms=int(last_dt.timestamp()*1000)
                relevant=[r for r in rows if int(r.get("close_time") or 0)>last_ms]
                if not relevant:
                    continue
                status=str(sig.get("status") or "open"); hit=int(sig.get("hit_level") or 0)
                active_stop=float(sig.get("active_stop") or sig.get("stop_loss")); be_armed=bool(int(sig.get("breakeven_armed") or 0))
                terminal=False
                for candle in relevant:
                    high=float(candle["h"]); low=float(candle["l"]); last=float(candle["c"]); close_ms=int(candle["close_time"])
                    event_at=datetime.fromtimestamp(close_ms/1000,tz=timezone.utc).isoformat()
                    side=sig["side"]
                    stop_hit=(low<=active_stop if side=="BUY" else high>=active_stop)
                    levels=[]
                    if hit<1 and (high>=sig["tp1"] if side=="BUY" else low<=sig["tp1"]): levels.append(1)
                    if hit<2 and (high>=sig["tp2"] if side=="BUY" else low<=sig["tp2"]): levels.append(2)
                    if hit<3 and (high>=sig["tp3"] if side=="BUY" else low<=sig["tp3"]): levels.append(3)
                    highest=max(levels) if levels else 0
                    events_to_notify=[]
                    if stop_hit and highest:
                        status="ambiguous"; terminal=True
                        detail="حد محافظ و یک هدف جدید داخل همان کندل یک‌دقیقه‌ای لمس شده‌اند؛ ترتیب حرکت قابل اثبات نیست و نتیجه به‌عنوان برد یا باخت شمرده نمی‌شود."
                        with db._conn() as c:
                            c.execute("INSERT OR IGNORE INTO signal_events(signal_id,event_type,price,event_at,detail) VALUES(?,?,?,?,?)",(sig["signal_id"],"ambiguous",last,event_at,detail))
                        events_to_notify.append(("ambiguous",last,detail))
                    elif highest:
                        old_hit=hit; hit=highest; status=f"tp{hit}"
                        with db._conn() as c:
                            for lvl in range(old_hit+1,hit+1):
                                px=float(sig[f"tp{lvl}"])
                                c.execute("INSERT OR IGNORE INTO signal_events(signal_id,event_type,price,event_at,detail) VALUES(?,?,?,?,?)",(sig["signal_id"],f"tp{lvl}",px,event_at,f"TP{lvl} touched on real 1m OHLCV"))
                                events_to_notify.append((f"tp{lvl}",px,f"هدف {lvl} بر اساس کندل واقعی یک‌دقیقه‌ای ثبت شد."))
                        if hit>=3:
                            status="tp3"; terminal=True
                        elif hit>=1 and SIGNAL_MOVE_TO_BE_AFTER_TP1 and not be_armed:
                            # The new stop becomes active from the NEXT candle, never retroactively inside this candle.
                            be_armed=True; active_stop=float(sig["issued_price"])
                            with db._conn() as c:
                                c.execute("INSERT OR IGNORE INTO signal_events(signal_id,event_type,price,event_at,detail) VALUES(?,?,?,?,?)",(sig["signal_id"],"breakeven_armed",active_stop,event_at,"protective stop moved to issued price after TP1"))
                            events_to_notify.append(("breakeven_armed",active_stop,"از کندل بعدی، حد محافظ روی قیمت صدور سیگنال قرار می‌گیرد."))
                    elif stop_hit:
                        if be_armed and abs(active_stop-float(sig["issued_price"])) <= max(abs(float(sig["issued_price"]))*1e-8,1e-12):
                            status="breakeven"; event="breakeven"; detail="Protective break-even stop touched"
                        else:
                            status="stopped"; event="sl"; detail="Original/protective stop touched"
                        terminal=True
                        with db._conn() as c:
                            c.execute("INSERT OR IGNORE INTO signal_events(signal_id,event_type,price,event_at,detail) VALUES(?,?,?,?,?)",(sig["signal_id"],event,active_stop,event_at,detail))
                        events_to_notify.append((event,active_stop,"حد محافظ بر اساس کندل واقعی یک‌دقیقه‌ای لمس شد."))
                    closed_at=event_at if terminal else ""
                    with db._conn() as c:
                        c.execute("UPDATE market_signals SET status=?,hit_level=?,active_stop=?,breakeven_armed=?,closed_at=CASE WHEN ?<>'' THEN ? ELSE closed_at END,last_checked_at=?,last_event_at=CASE WHEN ? THEN ? ELSE last_event_at END WHERE signal_id=?",
                                  (status,hit,active_stop,1 if be_armed else 0,closed_at,closed_at,event_at,1 if events_to_notify else 0,event_at,sig["signal_id"]))
                    for ev,px,detail in events_to_notify:
                        await _notify_signal_event(context,sig,ev,px,detail)
                    if terminal:
                        break
    except Exception:
        logger.exception("Signal tracker job failed")

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def run():
    validate_runtime_license()
    ensure_pre_v13_snapshot()
    logger.info("Database storage: %s", _db_persistence_hint())

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
        per_chat=True,
        per_user=True,
        per_message=False,
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
    app.job_queue.run_repeating(market_job, interval=ALERT_CHECK_INTERVAL, first=3, name="market-job")
    app.job_queue.run_repeating(signal_scan_job, interval=SIGNAL_SCAN_INTERVAL, first=15, name="signal-scan")
    app.job_queue.run_repeating(signal_track_job, interval=SIGNAL_TRACK_INTERVAL, first=90, name="signal-track")
    app.job_queue.run_repeating(referral_qualification_job, interval=300, first=180, name="referral-qualification")
    app.job_queue.run_repeating(portfolio_snapshot_job, interval=3600, first=120, name="portfolio-snapshot")
    app.job_queue.run_repeating(daily_job, interval=30, first=10, name="daily-reports")
    app.job_queue.run_repeating(vip_backup_job, interval=VIP_MAINTENANCE_INTERVAL, first=60, name="vip-maintenance")
    try:
        app.run_polling()
    finally:
        if payment_server is not None:
            payment_server.shutdown()


if __name__ == "__main__":
    run()
