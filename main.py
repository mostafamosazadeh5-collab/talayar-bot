#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
طلایار v9 VIP Complete — دستیار هوشمند بازار طلا
نسخهٔ فروش حرفه‌ای:
  ✅ BRS API واقعی (طلا، دلار، ارز، کریپتو)
  ✅ انس جهانی (XAU/USD)
  ✅ Trial VIP ۳ روزه
  ✅ VIP + پرداخت + پنل ادمین
  ✅ هشدار قیمت (عددی + درصدی + تکرارشونده)
  ✅ گزارش روزانه
  ✅ نمودار کندل واقعی انس + نمودارهای ۲۴ ساعت، ۷ روز و ۳۰ روز
  ✅ ماشین حساب طلای کامل
  ✅ تحلیل هوشمند VIP متصل به منوی اصلی
  ✅ Watchlist VIP با سقف ۵ دارایی
  ✅ پرداخت دوحالته زرین‌پال + رسید دستی
  ✅ دیتابیس SQLite مرتب
  ✅ Referral هوشمند (بدون تداخل با Trial)
"""

import os
import re
import html
import json
import uuid
import shutil
import sqlite3
import logging
import threading
import time
import asyncio
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from io import BytesIO
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, quote, urlparse
from zoneinfo import ZoneInfo

import requests
import yfinance as yf
import mplfinance as mpf
import matplotlib
matplotlib.use("Agg")

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
BOT_TOKEN = os.environ.get("BOT_TOKEN")
BRS_API_URL = os.environ.get("BRS_API_URL")
ADMIN_ID = os.environ.get("ADMIN_ID", "")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "WAHL4").lstrip("@")
PAYMENT_INFO = os.environ.get(
    "PAYMENT_INFO",
    f"برای دریافت شماره کارت و هماهنگی پرداخت به @{ADMIN_USERNAME} پیام بدهید.",
)
DATA_DIR = os.environ.get("DATA_DIR", "/data" if os.path.isdir("/data") else ".")
DB_PATH = os.path.join(DATA_DIR, "talayar_v3.db")
BACKUP_DIR = os.path.join(DATA_DIR, "backups")

API_TIMEOUT = 20
CACHE_TTL_SECONDS = 20
FREE_ALERT_LIMIT = 1
ALERT_CHECK_INTERVAL = 60
HISTORY_SAVE_INTERVAL = 300
HISTORY_RETENTION_DAYS = 35
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
    "ZARINPAL_REQUEST_URL", "https://payment.zarinpal.com/pg/v4/payment/request.json"
)
ZARINPAL_VERIFY_URL = os.environ.get(
    "ZARINPAL_VERIFY_URL", "https://payment.zarinpal.com/pg/v4/payment/verify.json"
)
ZARINPAL_STARTPAY_URL = os.environ.get(
    "ZARINPAL_STARTPAY_URL", "https://payment.zarinpal.com/pg/StartPay/"
)
DISCLAIMER = "قیمت‌ها ممکن است با بازار اختلاف یا تأخیر داشته باشند و توصیه خرید یا فروش نیستند."

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger("talayar")

_market_cache = {"data": None, "saved_at": 0.0}
_db_lock = threading.Lock()

# ═══════════════════════════════════════════════════════════════
# DATABASE
# ═══════════════════════════════════════════════════════════════
class Database:
    def __init__(self, path: str = DB_PATH):
        self.path = path
        os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
        self._init_db()

    def _conn(self):
        return sqlite3.connect(self.path, check_same_thread=False)

    def _init_db(self):
        with self._conn() as c:
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
            """)
            self._ensure_column(c, "orders", "authority", "TEXT")
            self._ensure_column(c, "orders", "ref_id", "TEXT")
            self._ensure_column(c, "orders", "payment_method", "TEXT DEFAULT 'manual'")
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_authority ON orders(authority) WHERE authority IS NOT NULL")
            c.execute("CREATE INDEX IF NOT EXISTS idx_price_history_asset_ts ON price_history(asset_key, ts)")

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
            c.execute("SELECT 1 FROM vip_users WHERE user_id = ?", (user_id,))
            if c.fetchone():
                return False
            now = datetime.now(timezone.utc)
            c.execute("""
                INSERT INTO vip_users (user_id, expires_at, plan_days, added_at, source, last_reminder)
                VALUES (?, ?, ?, ?, ?, '')
            """, (user_id, (now + timedelta(days=3)).isoformat(), 3, now.isoformat(), "trial"))
            return True

    def remove_vip(self, user_id):
        with self._conn() as c:
            c.execute("DELETE FROM vip_users WHERE user_id = ?", (user_id,))
            return c.rowcount > 0

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
            c.execute("DELETE FROM alerts WHERE id = ? AND user_id = ?", (alert_id, user_id))
            return c.rowcount > 0

    def update_alert(self, alert_id, user_id, changes):
        with self._conn() as c:
            sets = ", ".join(f"{k} = ?" for k in changes)
            vals = list(changes.values()) + [alert_id, user_id]
            c.execute(f"UPDATE alerts SET {sets} WHERE id = ? AND user_id = ?", vals)
            return c.rowcount > 0

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

    def register_referral(self, new_user_id, referrer_id):
        if str(new_user_id) == str(referrer_id):
            return False
        with self._conn() as c:
            c.execute("SELECT 1 FROM users WHERE user_id = ?", (referrer_id,))
            if not c.fetchone():
                return False
            try:
                c.execute("""
                    INSERT INTO referrals (referrer_id, referred_id, started_at, qualified, qualified_at)
                    VALUES (?, ?, ?, 0, NULL)
                """, (referrer_id, new_user_id, datetime.now(timezone.utc).isoformat()))
                return True
            except sqlite3.IntegrityError:
                return False

    def get_referral(self, referred_id):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT * FROM referrals WHERE referred_id = ?", (referred_id,)).fetchone()
            return dict(row) if row else None

    def qualify_referral(self, referred_id):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            row = c.execute("SELECT * FROM referrals WHERE referred_id = ? AND qualified = 0", (referred_id,)).fetchone()
            if not row:
                return None
            c.execute("UPDATE referrals SET qualified = 1, qualified_at = ? WHERE referred_id = ?",
                      (datetime.now(timezone.utc).isoformat(), referred_id))
            return dict(row)

    def qualified_count(self, referrer_id):
        with self._conn() as c:
            row = c.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND qualified = 1", (referrer_id,)).fetchone()
            return row[0]

    def referral_leaderboard(self, limit=10):
        with self._conn() as c:
            rows = c.execute("""
                SELECT referrer_id, COUNT(*) as cnt FROM referrals
                WHERE qualified = 1 GROUP BY referrer_id ORDER BY cnt DESC LIMIT ?
            """, (limit,)).fetchall()
            return rows

    def add_referral_reward(self, referrer_id, reward_type, amount, days):
        with self._conn() as c:
            c.execute("""
                INSERT INTO referral_rewards (referrer_id, reward_type, amount, days, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (referrer_id, reward_type, amount, days, datetime.now(timezone.utc).isoformat()))

    def get_referral_rewards(self, referrer_id):
        with self._conn() as c:
            c.row_factory = sqlite3.Row
            rows = c.execute("SELECT * FROM referral_rewards WHERE referrer_id = ?", (referrer_id,)).fetchall()
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
            c.execute("DELETE FROM watchlist WHERE user_id = ? AND asset_key = ?", (user_id, asset_key))
            return c.rowcount > 0

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
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 قیمت لحظه‌ای", callback_data="prices"),
         InlineKeyboardButton("🔔 هشدار قیمت", callback_data="alerts")],
        [InlineKeyboardButton("🗓 گزارش روزانه", callback_data="daily"),
         InlineKeyboardButton("📈 نمودار قیمت", callback_data="charts")],
        [InlineKeyboardButton("🧮 ماشین‌حساب طلا", callback_data="calculator"),
         InlineKeyboardButton("👤 حساب کاربری", callback_data="account")],
        [InlineKeyboardButton("📌 بازار من VIP", callback_data="watchlist"),
         InlineKeyboardButton("🤖 تحلیل هوشمند VIP", callback_data="analysis")],
        [InlineKeyboardButton("🎁 دعوت دوستان", callback_data="referrals"),
         InlineKeyboardButton("⭐ عضویت VIP", callback_data="vip")],
        [InlineKeyboardButton("ℹ️ راهنما", callback_data="help")],
    ])


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
    rows = []
    if user_id is None or not is_vip(user_id):
        rows += [
            [InlineKeyboardButton(f"⭐ یک‌ماهه — {VIP_PRICE_30} تومان", callback_data="buy:30")],
            [InlineKeyboardButton(f"🌟 سه‌ماهه — {VIP_PRICE_90} تومان", callback_data="buy:90")],
        ]
    rows += [
        [InlineKeyboardButton("💬 ارتباط با ادمین", url=f"https://t.me/{ADMIN_USERNAME}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ]
    return InlineKeyboardMarkup(rows)


def daily_menu(active=False):
    rows = [
        [InlineKeyboardButton("09:00", callback_data="daily_set:09:00"),
         InlineKeyboardButton("14:00", callback_data="daily_set:14:00"),
         InlineKeyboardButton("21:00", callback_data="daily_set:21:00")],
        [InlineKeyboardButton("⌨️ ساعت دلخواه", callback_data="daily_custom")],
    ]
    if active:
        rows.append([InlineKeyboardButton("⛔ توقف گزارش", callback_data="daily_stop")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="home")])
    return InlineKeyboardMarkup(rows)


@lru_cache(maxsize=1)
def chart_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💵 دلار", callback_data="chart_asset:usd"),
         InlineKeyboardButton("🪙 طلای ۱۸", callback_data="chart_asset:gold18")],
        [InlineKeyboardButton("🟡 سکه امامی", callback_data="chart_asset:emami"),
         InlineKeyboardButton("🌎 انس (کندل واقعی)", callback_data="chart_candle:ounce")],
        [InlineKeyboardButton("₿ بیت‌کوین", callback_data="chart_asset:btc")],
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


def admin_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 آمار", callback_data="admin:stats"),
         InlineKeyboardButton("🧾 خریدهای منتظر", callback_data="admin:pending")],
        [InlineKeyboardButton("📣 پیام همگانی", callback_data="admin:broadcast"),
         InlineKeyboardButton("💾 پشتیبان", callback_data="admin:backup")],
        [InlineKeyboardButton("🏠 منوی اصلی", callback_data="home")],
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
                "هشدار نامحدود، درصدی و تکرارشونده، گزارش روزانه، نمودار ۷ و ۳۰ روزه، "
                "تحلیل هوشمند و بازار من فعال‌اند.")
    return ("⭐ <b>عضویت VIP طلایار</b>\n\n"
            "✅ هشدار نامحدود، درصدی و تکرارشونده\n"
            "✅ گزارش روزانه خودکار\n"
            "✅ نمودار ۷ و ۳۰ روزه + کندل واقعی انس\n"
            "✅ تحلیل هوشمند از داده واقعی\n"
            f"✅ بازار من تا {WATCHLIST_VIP_LIMIT} دارایی\n\n"
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
                                headers={"Accept": "application/json", "User-Agent": "TalayarBot/3.0"})
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
# AI ANALYSIS (Real data from BRS)
# ═══════════════════════════════════════════════════════════════
def build_ai_summary(market):
    items = []
    for key in ("usd", "gold18", "ounce", "btc"):
        item = find_alert_item(market, key)
        if item:
            change = float(item.get("change_percent") or 0)
            direction = "صعودی" if change > 0 else "نزولی" if change < 0 else "ثابت"
            items.append(f"{ALERT_ASSETS[key]['label']}: {direction} ({change:+.2f}٪)")

    rsi_text = ""
    for key in ("usd", "gold18"):
        hist = db.get_price_history(key, 24 * 14)
        if len(hist) >= 14:
            prices = [p["price"] for p in hist]
            gains = [max(0, prices[i] - prices[i-1]) for i in range(1, len(prices))]
            losses = [max(0, prices[i-1] - prices[i]) for i in range(1, len(prices))]
            avg_gain = sum(gains[-14:]) / 14
            avg_loss = sum(losses[-14:]) / 14
            if avg_loss == 0:
                rsi = 100
            else:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            status = "اشباع خرید" if rsi > 70 else "اشباع فروش" if rsi < 30 else "متعادل"
            rsi_text += f"\n📊 RSI {ALERT_ASSETS[key]['label']}: {rsi:.1f} ({status})"

    support_resistance = ""
    for key in ("usd", "gold18"):
        hist = db.get_price_history(key, 24 * 7)
        if len(hist) >= 10:
            prices = [p["price"] for p in hist]
            support = min(prices)
            resistance = max(prices)
            support_resistance += f"\n📉 {ALERT_ASSETS[key]['label']}: حمایت {_format_number(support)} / مقاومت {_format_number(resistance)}"

    readiness = ""
    if not rsi_text:
        readiness = "\n\n⏳ برای RSI و حمایت/مقاومت، آرشیو قیمت در حال تکمیل است."
    return ("🤖 <b>تحلیل هوشمند طلایار (VIP)</b>\n\n"
            + "\n".join(items)
            + rsi_text
            + support_resistance
            + readiness
            + "\n\n<i>این تحلیل بر اساس دادهٔ واقعی بازار محاسبه شده و توصیه خرید یا فروش نیست.</i>")


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
            "url": f"{ZARINPAL_STARTPAY_URL}{authority}",
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
    server_version = "TalayarPayment/1.0"

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
        if parsed.path.rstrip("/") != "/payment/callback":
            self._write_page(404, "صفحه پیدا نشد", "آدرس درخواست‌شده معتبر نیست.")
            return

        query = parse_qs(parsed.query)
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

    def log_message(self, fmt, *args):
        logger.info("Payment callback: " + fmt, *args)


def start_payment_callback_server():
    if not zarinpal_enabled():
        logger.info("ZarinPal is not configured; manual receipt fallback remains active")
        return None
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
# REFERRAL
# ═══════════════════════════════════════════════════════════════
async def get_bot_username(context):
    username = getattr(context.bot, "username", None)
    if username:
        return username
    bot_info = await context.bot.get_me()
    return bot_info.username


def referral_progress_text(user_id, bot_username):
    count = db.qualified_count(user_id)
    next_tier = next(((needed, days) for needed, days in ((3, 7), (10, 30), (25, 90)) if count < needed), None)
    if next_tier:
        progress = f"تا جایزه بعدی: {next_tier[0] - count} دعوت دیگر برای {next_tier[1]} روز VIP"
    else:
        progress = "همه جایزه‌های دعوت را دریافت کرده‌ای 🎉"
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    return (
        "🎁 <b>دعوت دوستان و دریافت VIP</b>\n\n"
        f"دعوت‌های معتبر شما: <b>{count}</b> نفر\n{progress}\n\n"
        "جوایز:\n• ۳ دعوت = ۷ روز VIP\n• ۱۰ دعوت = ۳۰ روز VIP\n• ۲۵ دعوت = ۹۰ روز VIP\n\n"
        "دعوت وقتی معتبر می‌شود که دوست جدیدت ربات را Start کند و حداقل یک قیمت یا هشدار را استفاده کند.\n\n"
        f"لینک اختصاصی شما:\n<code>{link}</code>"
    )


def referral_menu(user_id, bot_username):
    link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    share_text = "با طلایار قیمت طلا و دلار رو رایگان ببین و هشدار قیمت بساز 👇"
    share_url = f"https://t.me/share/url?url={quote(link, safe='')}&text={quote(share_text, safe='')}"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📤 ارسال لینک برای دوستان", url=share_url)],
        [InlineKeyboardButton("🏆 برترین دعوت‌کنندگان", callback_data="referrals_top")],
        [InlineKeyboardButton("🔄 به‌روزرسانی آمار", callback_data="referrals")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="home")],
    ])


async def qualify_referral(user_id, context):
    ref = db.qualify_referral(user_id)
    if not ref:
        return False
    referrer_id = ref["referrer_id"]
    count = db.qualified_count(referrer_id)
    rewards = db.get_referral_rewards(referrer_id)
    claimed = {r.get("days", 0) for r in rewards}
    new_rewards = []
    for needed, days in ((3, 7), (10, 30), (25, 90)):
        if count >= needed and days not in claimed:
            db.add_vip(referrer_id, days, source=f"referral:{needed}")
            db.add_referral_reward(referrer_id, "vip_days", 0, days)
            new_rewards.append((needed, days))
    try:
        message = f"✅ یک دعوت شما معتبر شد.\nتعداد دعوت‌های معتبر: {count} نفر"
        if new_rewards:
            message += "\n\n" + "\n".join(f"🎉 جایزه {needed} دعوت: {days} روز VIP فعال شد." for needed, days in new_rewards)
        await context.bot.send_message(int(referrer_id), message, reply_markup=main_menu())
    except Exception:
        logger.exception("Referral notification failed")
    return True


# ═══════════════════════════════════════════════════════════════
# CANDLE CHART (yfinance for XAU/USD)
# ═══════════════════════════════════════════════════════════════
async def send_candle_chart(update_or_query, context, asset, period_hours):
    if asset != "ounce":
        return False
    try:
        ticker = yf.Ticker("GC=F")
        if period_hours <= 24:
            period, interval = "5d", "1h"
        elif period_hours <= 168:
            period, interval = "1mo", "1h"
        else:
            period, interval = "1mo", "1d"
        df = ticker.history(period=period, interval=interval)
        if not df.empty:
            cutoff = df.index.max() - timedelta(hours=period_hours)
            df = df[df.index >= cutoff]
            df = df.dropna(subset=["Open", "High", "Low", "Close"])
        if df.empty:
            return False

        first = df["Close"].iloc[0]
        last = df["Close"].iloc[-1]
        change = ((last - first) / first) * 100
        emoji = "🟢" if change >= 0 else "🔴"

        buf = BytesIO()
        mc = mpf.make_marketcolors(up="#26a69a", down="#ef5350", edge="inherit", wick="inherit")
        s = mpf.make_mpf_style(
            marketcolors=mc, figcolor="#1e1e2e", facecolor="#1e1e2e",
            edgecolor="#444", gridcolor="#333", gridstyle="--",
            rc={"axes.labelcolor": "white", "xtick.color": "white", "ytick.color": "white"},
        )
        mpf.plot(df, type="candle", style=s,
                 title=f"\nXAU/USD  |  تغییر: {change:+.2f}%",
                 ylabel="قیمت (دلار)", volume=True, figsize=(10, 6),
                 savefig=dict(fname=buf, dpi=150, bbox_inches="tight"))
        buf.seek(0)

        period_label = {24: "۲۴ ساعت", 168: "۷ روز", 720: "۳۰ روز"}.get(period_hours, f"{period_hours} ساعت")
        caption = (f"{emoji} <b>نمودار کندلی واقعی طلای جهانی</b>\n"
                   f"⏳ بازه: {period_label}\n"
                   f"💰 قیمت فعلی: <code>${last:,.2f}</code>\n"
                   f"📈 تغییر: <code>{change:+.2f}%</code>")

        if isinstance(update_or_query, Update):
            await update_or_query.message.reply_photo(
                photo=buf, caption=caption, parse_mode="HTML",
                reply_markup=chart_period_menu(asset, candle=True),
            )
        else:
            await update_or_query.edit_message_text("📊 در حال ارسال نمودار...")
            await context.bot.send_photo(
                chat_id=update_or_query.message.chat.id, photo=buf, caption=caption,
                parse_mode="HTML", reply_markup=chart_period_menu(asset, candle=True),
            )
        return True
    except Exception as e:
        logger.error(f"Candle chart error: {e}")
        return False

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


# ═══════════════════════════════════════════════════════════════
# HANDLERS
# ═══════════════════════════════════════════════════════════════
def clear_flow(context):
    for key in ("flow", "alert_draft", "alert_edit_id", "purchase_plan", "calc_weight", "calc_price", "calc_wage", "calc_profit"):
        context.user_data.pop(key, None)


async def start_v2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_flow(context)
    user = update.effective_user
    chat_id = update.effective_chat.id
    existing = db.get_user(user.id)
    is_new = existing is None

    referral_registered = False
    referrer_id = None
    if is_new and context.args:
        match = re.fullmatch(r"ref_(\d+)", context.args[0])
        if match:
            referrer_id = int(match.group(1))
            referral_registered = db.register_referral(user.id, referrer_id)

    db.add_user(user.id, user.username, user.first_name, chat_id, _utc_now(), referrer_id=referrer_id)
    db.update_last_seen(user.id)

    trial_activated = False
    if is_new:
        trial_activated = db.add_trial_vip(user.id)

    referral_note = "\n\n✅ معرف شما ثبت شد؛ با اولین استفاده، دعوت معتبر می‌شود." if referral_registered else ""
    trial_note = "\n🎁 ۳ روز VIP هدیه شما فعال شد." if trial_activated else ""

    await update.message.reply_text(
        "🟡 <b>طلایار</b>\n\nدستیار قیمت طلا، ارز و بازارهای مالی\n"
        "قیمت لحظه‌ای، هشدار هوشمند، گزارش روزانه، نمودار، ماشین‌حساب و تحلیل VIP"
        + referral_note + trial_note,
        reply_markup=main_menu(), parse_mode="HTML",
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
    await qualify_referral(user_id, context)

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
        clear_flow(context)
        await update.message.reply_text(f"✅ گزارش روزانه ساعت {normalized} فعال شد.", reply_markup=main_menu())
        return

    if flow == "broadcast" and _is_admin(user_id):
        users_rows = []
        with db._conn() as c:
            c.row_factory = sqlite3.Row
            users_rows = c.execute("SELECT chat_id, user_id FROM users").fetchall()
        clear_flow(context)
        sent = failed = 0
        status = await update.message.reply_text("در حال ارسال…")
        for u in users_rows:
            try:
                await context.bot.send_message(u["chat_id"] or u["user_id"], text, reply_markup=main_menu())
                sent += 1
            except Exception:
                failed += 1
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
        await q.edit_message_text("🟡 منوی اصلی طلایار", reply_markup=main_menu())
        return

    if data == "referrals":
        bot_username = await get_bot_username(context)
        await q.edit_message_text(
            referral_progress_text(user_id, bot_username),
            reply_markup=referral_menu(user_id, bot_username),
            parse_mode="HTML",
        )
        return

    if data == "referrals_top":
        leaders = db.referral_leaderboard()
        if not leaders:
            text = "🏆 هنوز دعوت معتبری ثبت نشده است؛ اولین نفر باش!"
        else:
            lines = ["🏆 <b>برترین دعوت‌کنندگان طلایار</b>", ""]
            for rank, (leader_id, count) in enumerate(leaders, start=1):
                user = db.get_user(int(leader_id))
                name = html.escape(user.get("first_name") or "کاربر طلایار") if user else "کاربر طلایار"
                lines.append(f"{rank}. {name} — {count} دعوت معتبر")
            text = "\n".join(lines)
        bot_username = await get_bot_username(context)
        await q.edit_message_text(text, reply_markup=referral_menu(user_id, bot_username), parse_mode="HTML")
        return

    if data == "prices":
        await q.edit_message_text("📊 بازار را انتخاب کن:", reply_markup=price_menu())
        return

    if data in {"gold", "iran_currency", "ounce", "crypto"}:
        market, error = get_market_data()
        if market is None:
            await q.edit_message_text(f"❌ {error}", reply_markup=price_menu())
            return
        await qualify_referral(user_id, context)
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
        await q.edit_message_text(f"✅ گزارش ساعت {report_time} فعال شد.", reply_markup=daily_menu(True))
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
        await q.edit_message_text("📈 دارایی را انتخاب کن:", reply_markup=chart_menu())
        return

    if data.startswith("chart_asset:"):
        asset = data.split(":", 1)[1]
        await q.edit_message_text("بازه نمودار را انتخاب کن:", reply_markup=chart_period_menu(asset))
        return

    if data.startswith("chart_candle:"):
        asset = data.split(":", 1)[1]
        await q.edit_message_text("بازه نمودار کندل را انتخاب کن:", reply_markup=chart_period_menu(asset, candle=True))
        return

    if data.startswith("chart:"):
        _, asset, hours = data.split(":")
        if int(hours) in {168, 720} and not is_vip(user_id):
            await q.edit_message_text("نمودارهای ۷ و ۳۰ روزه مخصوص VIP هستند.", reply_markup=vip_menu(user_id))
            return
        await q.edit_message_text(chart_text(asset, int(hours)), reply_markup=chart_period_menu(asset), parse_mode="HTML")
        return

    if data.startswith("candle:"):
        _, asset, hours = data.split(":")
        if int(hours) in {168, 720} and not is_vip(user_id):
            await q.edit_message_text("نمودار کندلی ۷ و ۳۰ روزه مخصوص VIP است.", reply_markup=vip_menu(user_id))
            return
        sent = await send_candle_chart(q, context, asset, int(hours))
        if not sent:
            await q.edit_message_text(
                "❌ دادهٔ کندلی فعلاً دریافت نشد؛ چند دقیقه دیگر دوباره امتحان کنید.",
                reply_markup=chart_period_menu(asset, candle=True),
            )
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
        await q.edit_message_text(
            "ℹ️ <b>راهنمای طلایار</b>\n\nقیمت لحظه‌ای، هشدار عددی و درصدی، گزارش روزانه، "
            "نمودار و ماشین‌حساب از منوی اصلی در دسترس‌اند.\nبرای لغو ورود اطلاعات /cancel را بفرست.\n\n"
            f"🔒 فقط شناسه تلگرام و تنظیمات لازم ذخیره می‌شود.\n⚠️ {DISCLAIMER}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⭐ مقایسه رایگان و VIP", callback_data="plans")],
                [InlineKeyboardButton("💬 پشتیبانی", url=f"https://t.me/{ADMIN_USERNAME}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="home")]]), parse_mode="HTML")
        return

    if data == "plans":
        await q.edit_message_text(
            "رایگان: قیمت‌ها، ماشین‌حساب، نمودار ۲۴ساعته و یک هشدار عددی.\n\n"
            f"VIP: هشدار نامحدود/درصدی/تکراری، گزارش روزانه، نمودار ۷ و ۳۰ روزه، "
            f"کندل واقعی انس، تحلیل هوشمند و بازار من تا {WATCHLIST_VIP_LIMIT} دارایی.",
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
        await q.edit_message_text(build_ai_summary(market), reply_markup=main_menu(), parse_mode="HTML")
        return

    if data == "watchlist":
        if not is_vip(user_id):
            await q.edit_message_text("بازار من مخصوص کاربران VIP است.", reply_markup=vip_menu(user_id))
            return
        market, _ = get_market_data()
        text = build_watchlist_text(user_id, market or {})
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

    if data.startswith("admin:"):
        if not _is_admin(user_id):
            return
        action = data.split(":", 1)[1]
        if action == "stats":
            s = db.stats()
            text = (f"📊 آمار\n\nکاربران: {s['users']}\nVIP فعال: {s['vip']}\n"
                    f"هشدارها: {s['alerts']}\nگزارش فعال: {s['daily']}\n"
                    f"دعوت معتبر: {s['refs']}\nخرید منتظر: {s['pending']}")
            await q.edit_message_text(text, reply_markup=admin_menu())
        elif action == "pending":
            pending = [o for o in db.load_orders() if o.get("status") == "pending"]
            await q.edit_message_text("🧾 درخواست‌های منتظر: " + str(len(pending)) +
                                      ("\n" + "\n".join(f"{p['order_id']} | {p['user_id']} | {p['plan']} روز" for p in pending[-20:]) if pending else ""),
                                      reply_markup=admin_menu())
        elif action == "broadcast":
            context.user_data["flow"] = "broadcast"
            await q.edit_message_text("متن پیام همگانی را بفرست. برای لغو /cancel")
        elif action == "backup":
            day = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")
            destination = os.path.join(BACKUP_DIR, day)
            os.makedirs(destination, exist_ok=True)
            import shutil
            shutil.copy2(DB_PATH, os.path.join(destination, "talayar_v3.db"))
            db.set_state("last_backup", day)
            await q.edit_message_text(f"✅ پشتیبان ساخته شد: {day}", reply_markup=admin_menu())
        return

    await q.edit_message_text("گزینه نامعتبر است.", reply_markup=main_menu())

# ═══════════════════════════════════════════════════════════════
# JOBS
# ═══════════════════════════════════════════════════════════════
async def market_job(context: ContextTypes.DEFAULT_TYPE):
    market, error = get_market_data(force_refresh=True)
    if market is None:
        logger.warning("Alert check skipped: %s", error)
        return
    capture_history(market)

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
    for sub in due:
        if not is_vip(sub.get("user_id")):
            with db._conn() as c:
                c.execute("UPDATE daily_subs SET active = 0 WHERE user_id = ?", (sub["user_id"],))
            continue
        try:
            await context.bot.send_message(sub["chat_id"], report, parse_mode="HTML", reply_markup=main_menu())
            with db._conn() as c:
                c.execute("UPDATE daily_subs SET last_sent = ? WHERE user_id = ?",
                          (now.strftime("%Y-%m-%d"), sub["user_id"]))
        except Exception:
            logger.exception("Daily report failed")


async def vip_backup_job(context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")
    with db._conn() as c:
        c.row_factory = sqlite3.Row
        rows = c.execute("SELECT * FROM vip_users").fetchall()
    changed = False
    for row in rows:
        user_id = row["user_id"]
        days = vip_days_left(user_id)
        key = f"{today}:{days}"
        if days in {1, 3} and row.get("last_reminder") != key:
            try:
                await context.bot.send_message(int(user_id), f"⏳ {days} روز از VIP شما باقی مانده است.", reply_markup=vip_menu(user_id))
                with db._conn() as c:
                    c.execute("UPDATE vip_users SET last_reminder = ? WHERE user_id = ?", (key, user_id))
                changed = True
            except Exception:
                logger.exception("VIP reminder failed")

    last_backup = db.get_state("last_backup", "")
    if last_backup != today:
        day = datetime.now(TEHRAN_TZ).strftime("%Y-%m-%d")
        destination = os.path.join(BACKUP_DIR, day)
        os.makedirs(destination, exist_ok=True)
        shutil.copy2(DB_PATH, os.path.join(destination, "talayar_v3.db"))
        db.set_state("last_backup", day)


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


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════
def run():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")

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
    app.job_queue.run_repeating(daily_job, interval=30, first=10, name="daily-reports")
    app.job_queue.run_repeating(vip_backup_job, interval=21600, first=60, name="vip-backup")
    try:
        app.run_polling()
    finally:
        if payment_server is not None:
            payment_server.shutdown()


if __name__ == "__main__":
    run()
