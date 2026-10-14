# -*- coding: utf-8 -*-
"""
SOST AI - v11.0 FINAL (WormGPT Edition - Fixed)
- محرك دردشة: WormGPT فقط
- واجهة فخمة حمراء/سوداء + أنيميشن Particles
- محادثات محفوظة + قائمة جانبية
- إدارة جلسات كاملة
- API Keys (5/يوم، 10 رد)
- لوحة تحكم كاملة
- 15 رسالة مجانية
"""

import os
import json
import random
import secrets
import base64
import hashlib
import sqlite3
import time
import traceback
from datetime import datetime, timedelta
from http.cookies import SimpleCookie

import requests
import urllib3
urllib3.disable_warnings()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════
# الإعدادات
# ═══════════════════════════════════════════════════════════════

ADMIN_PASSWORD = "SOST2009"
TELEGRAM_SUBSCRIBE = "Yb_xY"
TELEGRAM_SUPPORT = "Yb_xY"
FREE_MESSAGE_LIMIT = 15
MAX_MESSAGE_LENGTH = 30000

API_KEY_PREFIX = "SOST"
API_KEY_FREE_LIMIT = 10
API_KEY_MAX_PER_USER = 5
API_KEY_DAILY_CREATE_LIMIT = 5

DB_PATH = os.path.join(BASE_DIR, 'sost_ai.db')

# ═══════════════════════════════════════════════════════════════
# WormGPT — الاتصالات
# ═══════════════════════════════════════════════════════════════

WORMGPT_URL = "https://vex-app.page.gd/worm.php"

WORMGPT_HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    'Connection': 'keep-alive',
    'Referer': 'https://vex-app.page.gd/index.php',
    'Sec-Fetch-Dest': 'empty',
    'Sec-Fetch-Mode': 'cors',
    'Sec-Fetch-Site': 'same-origin',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
    'sec-ch-ua': '"Chromium";v="137", "Not/A)Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
}

WORMGPT_COOKIES = {
    '__test': '61e30ac543fe8bd30e11e282e12201ab',
    'PHPSESSID': 'c69a4d00c854f19db0f38dab75d64aaa',
}

# ═══════════════════════════════════════════════════════════════
# النماذج
# ═══════════════════════════════════════════════════════════════

MODELS = {
    'wormgpt': {
        'id': 'wormgpt',
        'name': 'WormGPT',
        'desc': 'النموذج الأقوى بدون قيود',
        'icon': '🐛',
        'color': '#e11d48',
        'type': 'chat',
    },
}

# ═══════════════════════════════════════════════════════════════
# قاعدة البيانات — محسّنة
# ═══════════════════════════════════════════════════════════════

def hash_password(password):
    return hashlib.sha256((password + "SOST_SALT_2025").encode()).hexdigest()


def _table_cols(c, table):
    try:
        c.execute(f'PRAGMA table_info({table})')
        return {row[1] for row in c.fetchall()}
    except Exception:
        return set()


def _has_table(c, table):
    try:
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        return c.fetchone() is not None
    except Exception:
        return False


def _migrate(conn):
    c = conn.cursor()
    try:
        if _has_table(c, 'sessions'):
            cols = _table_cols(c, 'sessions')
            for col, typ in [('device', 'TEXT'), ('last_seen', 'TEXT'), ('expires_at', 'TEXT'),
                             ('ip', 'TEXT'), ('user_agent', 'TEXT'), ('created_at', 'TEXT')]:
                if col not in cols:
                    try:
                        c.execute(f'ALTER TABLE sessions ADD COLUMN {col} {typ}')
                    except Exception:
                        pass
        if _has_table(c, 'users'):
            cols = _table_cols(c, 'users')
            for col, typ in [('preferred_model', "TEXT DEFAULT 'wormgpt'"),
                             ('messages_used', 'INTEGER DEFAULT 0'),
                             ('subscription_expires', 'TEXT'),
                             ('last_login', 'TEXT'),
                             ('banned', 'INTEGER DEFAULT 0'),
                             ('email', 'TEXT')]:
                if col.split()[0] not in cols:
                    try:
                        c.execute(f'ALTER TABLE users ADD COLUMN {col} {typ}')
                    except Exception:
                        pass
        if _has_table(c, 'chat_logs'):
            cols = _table_cols(c, 'chat_logs')
            if 'model' not in cols:
                try:
                    c.execute("ALTER TABLE chat_logs ADD COLUMN model TEXT DEFAULT 'wormgpt'")
                except Exception:
                    pass
        if _has_table(c, 'api_keys'):
            cols = _table_cols(c, 'api_keys')
            for col, typ in [('expires_at', 'TEXT'), ('banned', 'INTEGER DEFAULT 0')]:
                if col not in cols:
                    try:
                        c.execute(f'ALTER TABLE api_keys ADD COLUMN {col} {typ}')
                    except Exception:
                        pass
        conn.commit()
    except Exception as e:
        print(f'[migrate] {e}')
        try:
            conn.rollback()
        except Exception:
            pass


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        role TEXT DEFAULT 'user',
        banned INTEGER DEFAULT 0,
        messages_used INTEGER DEFAULT 0,
        subscription_type TEXT DEFAULT 'free',
        subscription_expires TEXT,
        preferred_model TEXT DEFAULT 'wormgpt',
        created_at TEXT,
        last_login TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER,
        created_at TEXT,
        expires_at TEXT,
        ip TEXT,
        user_agent TEXT,
        device TEXT,
        last_seen TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        title TEXT,
        messages TEXT,
        created_at TEXT,
        updated_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        user_message TEXT,
        bot_message TEXT,
        model TEXT DEFAULT 'wormgpt',
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS support_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        subject TEXT,
        message TEXT,
        image_data TEXT,
        status TEXT DEFAULT 'open',
        reply TEXT,
        created_at TEXT,
        replied_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        plan TEXT,
        price REAL,
        started_at TEXT,
        expires_at TEXT,
        status TEXT DEFAULT 'active'
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        key_value TEXT UNIQUE NOT NULL,
        key_name TEXT NOT NULL,
        service_name TEXT NOT NULL,
        messages_used INTEGER DEFAULT 0,
        messages_limit INTEGER DEFAULT 10,
        active INTEGER DEFAULT 1,
        banned INTEGER DEFAULT 0,
        last_used TEXT,
        created_at TEXT,
        expires_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS api_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        key_id INTEGER,
        user_id INTEGER,
        endpoint TEXT,
        request_body TEXT,
        response_body TEXT,
        status_code INTEGER,
        ip TEXT,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS api_key_daily (
        user_id INTEGER,
        day TEXT,
        count INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, day)
    )''')
    conn.commit()
    conn.close()
    
    conn = sqlite3.connect(DB_PATH)
    try:
        _migrate(conn)
    finally:
        conn.close()
    
    # إنشاء حساب الأدمن
    try:
        existing = db_query('SELECT id FROM users WHERE username = ?', ('admin',), one=True)
        if not existing:
            db_query('''INSERT INTO users (username, password_hash, role, subscription_type, preferred_model, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     ('admin', hash_password(ADMIN_PASSWORD), 'admin', 'unlimited', 'wormgpt', datetime.now().isoformat()))
            print("[DB] ✅ تم إنشاء حساب الأدمن (admin / SOST2009)")
    except Exception as e:
        print(f'[DB] خطأ في إنشاء الأدمن: {e}')


def db_query(query, params=(), one=False):
    """دالة موحدة للاستعلامات - مع حماية كاملة من الأخطاء"""
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute(query, params)
        if query.strip().upper().startswith('SELECT'):
            result = c.fetchone() if one else c.fetchall()
            if one:
                return dict(result) if result else None
            return [dict(r) for r in result] if result else []
        conn.commit()
        return c.lastrowid
    except Exception as e:
        print(f'[DB Error] {e}')
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        return None
    finally:
        try:
            if conn:
                conn.close()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# WormGPT Engine
# ═══════════════════════════════════════════════════════════════

def call_wormgpt(prompt):
    try:
        params = {'prompt': prompt}
        r = requests.get(
            WORMGPT_URL,
            params=params,
            cookies=WORMGPT_COOKIES,
            headers=WORMGPT_HEADERS,
            timeout=120,
            verify=False
        )
        if r.status_code == 429:
            return None, "⏱️ حد WormGPT - انتظر قليلاً"
        if r.status_code >= 500:
            return None, "⚠️ WormGPT مشغول - حاول بعد قليل"
        if r.status_code != 200:
            return None, f"❌ WormGPT: {r.status_code}"
        
        try:
            data = r.json()
        except Exception:
            return None, "🤔 WormGPT: رد غير صالح"
        
        if data.get('ok') and data.get('reply'):
            return data['reply'], None
        
        if data.get('error'):
            return None, f"⚠️ WormGPT: {data['error']}"
        
        return None, "🤔 WormGPT: رد فارغ"
    except requests.exceptions.Timeout:
        return None, "⏰ WormGPT: انتهت المدة"
    except requests.exceptions.ConnectionError:
        return None, "🌐 WormGPT: تعذّر الاتصال"
    except Exception as e:
        print(f'[WormGPT] {e}')
        return None, "💥 WormGPT: مشكلة، انتظر قليلاً"


def call_model(prompt, model_id='wormgpt'):
    return call_wormgpt(prompt)


# ═══════════════════════════════════════════════════════════════
# Users
# ═══════════════════════════════════════════════════════════════

def create_user(username, password, email=''):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=10)
        c = conn.cursor()
        c.execute('''INSERT INTO users (username, password_hash, email, subscription_type, preferred_model, created_at)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (username, hash_password(password), email, 'free', 'wormgpt', datetime.now().isoformat()))
        conn.commit()
        uid = c.lastrowid
        conn.close()
        return uid
    except sqlite3.IntegrityError:
        return None
    except Exception as e:
        print(f'[create_user] {e}')
        return None


def authenticate(username, password):
    try:
        user = db_query('SELECT * FROM users WHERE username = ?', (username,), one=True)
        if not user:
            return None
        if user.get('password_hash') != hash_password(password):
            return None
        if user.get('banned'):
            return {'banned': True, 'user': user}
        return user
    except Exception as e:
        print(f'[authenticate] {e}')
        return None


def _detect_device(ua):
    if not ua:
        return 'جهاز غير معروف'
    ua = ua.lower()
    for name, key in [('iPhone', 'iphone'), ('iPad', 'ipad'), ('Android', 'android'),
                      ('Windows', 'windows'), ('Mac', 'mac'), ('Linux', 'linux')]:
        if key in ua:
            return name
    return 'جهاز غير معروف'


def create_session(user_id, ip='', ua=''):
    try:
        token = secrets.token_urlsafe(32)
        expires = (datetime.now() + timedelta(days=30)).isoformat()
        db_query('''INSERT INTO sessions (token, user_id, created_at, expires_at, ip, user_agent, device, last_seen)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                 (token, user_id, datetime.now().isoformat(), expires, ip, ua,
                  _detect_device(ua), datetime.now().isoformat()))
        return token
    except Exception as e:
        print(f'[create_session] {e}')
        return None


def get_session_user(token):
    if not token:
        return None
    try:
        session = db_query('SELECT * FROM sessions WHERE token = ?', (token,), one=True)
        if not session:
            return None
        # فحص انتهاء الجلسة
        try:
            if session.get('expires_at'):
                exp = datetime.fromisoformat(session['expires_at'])
                if exp < datetime.now():
                    db_query('DELETE FROM sessions WHERE token = ?', (token,))
                    return None
        except Exception:
            pass
        # تحديث آخر نشاط
        try:
            db_query('UPDATE sessions SET last_seen = ? WHERE token = ?', (datetime.now().isoformat(), token))
        except Exception:
            pass
        return db_query('SELECT * FROM users WHERE id = ?', (session['user_id'],), one=True)
    except Exception as e:
        print(f'[get_session_user] {e}')
        return None


def check_subscription(user):
    if not user:
        return False, 'not_logged_in'
    if user.get('banned'):
        return False, 'banned'
    if user.get('role') == 'admin':
        return True, 'admin'
    if user.get('subscription_type') == 'unlimited':
        return True, 'unlimited'
    if user.get('subscription_type') in ('weekly', 'monthly', 'yearly'):
        if user.get('subscription_expires'):
            try:
                if datetime.fromisoformat(user['subscription_expires']) > datetime.now():
                    return True, user['subscription_type']
                db_query('UPDATE users SET subscription_type = ? WHERE id = ?', ('free', user['id']))
                return False, 'expired'
            except Exception:
                pass
    if user.get('messages_used', 0) >= FREE_MESSAGE_LIMIT:
        return False, 'free_limit'
    return True, 'free'


def increment_usage(user_id):
    try:
        db_query('UPDATE users SET messages_used = messages_used + 1 WHERE id = ?', (user_id,))
    except Exception:
        pass


def log_chat(uid, uname, um, bm, model='wormgpt'):
    try:
        db_query('''INSERT INTO chat_logs (user_id, username, user_message, bot_message, model, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 (uid, uname, um, bm, model, datetime.now().isoformat()))
    except Exception:
        pass


def save_conversation(user_id, title, messages):
    try:
        return db_query('''INSERT INTO conversations (user_id, title, messages, created_at, updated_at)
                           VALUES (?, ?, ?, ?, ?)''',
                        (user_id, title, json.dumps(messages, ensure_ascii=False),
                         datetime.now().isoformat(), datetime.now().isoformat()))
    except Exception:
        return None


def get_user_conversations(user_id):
    try:
        return db_query('SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC', (user_id,)) or []
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
# API Keys
# ═══════════════════════════════════════════════════════════════

def generate_api_key():
    return f"{API_KEY_PREFIX}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"


def _daily_count(user_id):
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        row = db_query('SELECT count FROM api_key_daily WHERE user_id = ? AND day = ?', (user_id, today), one=True)
        return row['count'] if row else 0
    except Exception:
        return 0


def _bump_daily(user_id):
    try:
        today = datetime.now().strftime('%Y-%m-%d')
        if db_query('SELECT count FROM api_key_daily WHERE user_id = ? AND day = ?', (user_id, today), one=True):
            db_query('UPDATE api_key_daily SET count = count + 1 WHERE user_id = ? AND day = ?', (user_id, today))
        else:
            db_query('INSERT INTO api_key_daily (user_id, day, count) VALUES (?, ?, 1)', (user_id, today))
    except Exception:
        pass


def create_api_key(user_id, key_name, service_name, messages_limit=API_KEY_FREE_LIMIT):
    try:
        count = db_query('SELECT COUNT(*) as c FROM api_keys WHERE user_id = ? AND banned = 0', (user_id,), one=True)
        if count and count['c'] >= API_KEY_MAX_PER_USER:
            return None, f"وصلت للحد الأقصى ({API_KEY_MAX_PER_USER})"
        if _daily_count(user_id) >= API_KEY_DAILY_CREATE_LIMIT:
            return None, f"⏰ حد الإنشاء اليومي ({API_KEY_DAILY_CREATE_LIMIT}/يوم)"
        key_value = None
        for _ in range(10):
            cand = generate_api_key()
            if not db_query('SELECT id FROM api_keys WHERE key_value = ?', (cand,), one=True):
                key_value = cand
                break
        if not key_value:
            return None, "فشل التوليد"
        kid = db_query('''INSERT INTO api_keys 
            (user_id, key_value, key_name, service_name, messages_limit, created_at)
            VALUES (?, ?, ?, ?, ?, ?)''',
            (user_id, key_value, key_name, service_name, messages_limit, datetime.now().isoformat()))
        _bump_daily(user_id)
        return key_value, kid
    except Exception as e:
        return None, str(e)


def get_user_api_keys(user_id):
    try:
        return db_query('SELECT * FROM api_keys WHERE user_id = ? ORDER BY id DESC', (user_id,)) or []
    except Exception:
        return []


def validate_api_key(key_value):
    if not key_value:
        return None, "missing_key"
    try:
        key = db_query('SELECT * FROM api_keys WHERE key_value = ?', (key_value,), one=True)
        if not key:
            return None, "invalid_key"
        if key.get('banned'):
            return None, "key_banned"
        if not key.get('active'):
            return None, "key_disabled"
        if key.get('expires_at'):
            try:
                if datetime.fromisoformat(key['expires_at']) < datetime.now():
                    return None, "key_expired"
            except Exception:
                pass
        if key.get('messages_used', 0) >= key.get('messages_limit', 0):
            return None, "key_limit_reached"
        user = db_query('SELECT * FROM users WHERE id = ?', (key['user_id'],), one=True)
        if not user:
            return None, "user_not_found"
        if user.get('banned'):
            return None, "user_banned"
        return {'key': key, 'user': user}, None
    except Exception:
        return None, "internal_error"


def use_api_key(key_id):
    try:
        db_query('UPDATE api_keys SET messages_used = messages_used + 1, last_used = ? WHERE id = ?',
                 (datetime.now().isoformat(), key_id))
    except Exception:
        pass


def log_api_request(key_id, user_id, endpoint, req, res, status, ip):
    try:
        db_query('''INSERT INTO api_logs (key_id, user_id, endpoint, request_body, response_body, status_code, ip, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                 (key_id, user_id, endpoint, req, res, status, ip, datetime.now().isoformat()))
    except Exception:
        pass


def delete_api_key(key_id, user_id):
    try:
        db_query('DELETE FROM api_keys WHERE id = ? AND user_id = ?', (key_id, user_id))
    except Exception:
        pass


def toggle_api_key(key_id, user_id):
    try:
        key = db_query('SELECT * FROM api_keys WHERE id = ? AND user_id = ?', (key_id, user_id), one=True)
        if not key:
            return False
        db_query('UPDATE api_keys SET active = ? WHERE id = ?', (0 if key['active'] else 1, key_id))
        return True
    except Exception:
        return False


# ═══════════════════════════════════════════════════════════════
# HTML: LOGIN — واجهة فخمة WormGPT
# ═══════════════════════════════════════════════════════════════

LOGIN_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>SOST AI — تسجيل الدخول</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Cairo',sans-serif}
body{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0a0a0f;overflow:hidden;position:relative;padding:20px}
#c{position:fixed;inset:0;z-index:0}
.b{position:fixed;border-radius:50%;filter:blur(90px);pointer-events:none;z-index:1}
.b1{width:500px;height:500px;background:radial-gradient(circle,rgba(225,29,72,.5),transparent 70%);top:-200px;right:-200px;animation:f1 15s ease-in-out infinite}
.b2{width:400px;height:400px;background:radial-gradient(circle,rgba(124,58,237,.4),transparent 70%);bottom:-150px;left:-150px;animation:f2 18s ease-in-out infinite}
@keyframes f1{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(-60px,60px) scale(1.2)}}
@keyframes f2{0%,100%{transform:translate(0,0) scale(1)}50%{transform:translate(60px,-60px) scale(1.15)}}
.wrap{position:relative;z-index:10;width:100%;max-width:450px}
.card{background:linear-gradient(145deg,rgba(20,10,15,.95),rgba(15,15,24,.95));backdrop-filter:blur(30px);border:1px solid rgba(225,29,72,.4);border-radius:30px;padding:45px 35px;box-shadow:0 30px 90px rgba(225,29,72,.3),inset 0 1px 0 rgba(255,255,255,.05)}
.logo{text-align:center;margin-bottom:30px}
.logo-i{width:90px;height:90px;margin:0 auto 18px;border-radius:26px;background:linear-gradient(135deg,#e11d48,#7c3aed);display:flex;align-items:center;justify-content:center;box-shadow:0 15px 50px rgba(225,29,72,.6);animation:p 3s ease-in-out infinite;position:relative}
.logo-i::after{content:'';position:absolute;inset:-3px;border-radius:28px;background:linear-gradient(135deg,#e11d48,#7c3aed,#06b6d4);z-index:-1;filter:blur(10px);opacity:.7}
@keyframes p{0%,100%{transform:scale(1)}50%{transform:scale(1.08)}}
h1{font-size:1.9rem;font-weight:900;background:linear-gradient(135deg,#e11d48,#7c3aed,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:10px;letter-spacing:-.5px}
.sub{color:#9a9aae;font-size:.92rem;line-height:1.5}
.tabs{display:flex;gap:8px;margin:26px 0 22px;background:rgba(255,255,255,.03);padding:6px;border-radius:16px;border:1px solid rgba(225,29,72,.15)}
.tab{flex:1;padding:13px;text-align:center;border-radius:11px;cursor:pointer;color:#9a9aae;font-weight:700;font-size:.9rem;transition:.3s}
.tab.active{background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;box-shadow:0 6px 20px rgba(225,29,72,.4)}
.fg{margin-bottom:16px}
.fg label{display:block;margin-bottom:8px;color:#c5c5d5;font-size:.85rem;font-weight:700}
.fg input{width:100%;padding:15px 18px;border-radius:14px;background:rgba(255,255,255,.04);border:1px solid rgba(225,29,72,.25);color:#fff;font-size:.95rem;font-family:inherit;outline:none;transition:.3s}
.fg input::placeholder{color:#6a6a80}
.fg input:focus{border-color:#e11d48;background:rgba(225,29,72,.08);box-shadow:0 0 0 4px rgba(225,29,72,.15)}
.btn{width:100%;padding:16px;border-radius:15px;border:none;background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;font-weight:900;font-size:1.05rem;cursor:pointer;font-family:inherit;transition:.3s;box-shadow:0 10px 30px rgba(225,29,72,.45);margin-top:10px;letter-spacing:.3px}
.btn:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 14px 40px rgba(225,29,72,.6)}
.btn:disabled{opacity:.6;cursor:not-allowed}
.divider{display:flex;align-items:center;gap:12px;margin:22px 0;color:#6a6a80;font-size:.8rem}
.divider::before,.divider::after{content:'';flex:1;height:1px;background:linear-gradient(90deg,transparent,rgba(225,29,72,.3),transparent)}
.tg{display:flex;align-items:center;justify-content:center;gap:8px;width:100%;padding:15px;border-radius:15px;background:linear-gradient(135deg,#e11d48,#9f1239);color:#fff;font-weight:800;font-size:.95rem;text-decoration:none;transition:.3s;box-shadow:0 8px 24px rgba(225,29,72,.3)}
.tg:hover{transform:translateY(-2px)}
.err{background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.4);color:#fca5a5;padding:13px 16px;border-radius:13px;font-size:.86rem;margin-bottom:16px;display:none;font-weight:600;line-height:1.5}
.err.show{display:block;animation:shake .4s}
@keyframes shake{0%,100%{transform:translateX(0)}25%{transform:translateX(-5px)}75%{transform:translateX(5px)}}
.badge{display:inline-block;padding:5px 12px;border-radius:20px;background:rgba(225,29,72,.15);border:1px solid rgba(225,29,72,.3);color:#fb7185;font-size:.72rem;font-weight:800;margin-bottom:14px}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div class="b b1"></div>
<div class="b b2"></div>
<div class="wrap">
  <div class="card">
    <div class="logo">
      <div class="logo-i">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none">
          <path d="M12 2L14.5 8.5L21 11L14.5 13.5L12 20L9.5 13.5L3 11L9.5 8.5L12 2Z" fill="white"/>
        </svg>
      </div>
      <div class="badge">🐛 WORMGPT POWERED</div>
      <h1>هلا فيك في SOST AI</h1>
      <p class="sub">النموذج الأقوى بدون قيود — سجل دخول وابدأ الآن</p>
    </div>
    <div class="tabs">
      <div class="tab active" onclick="sw('login',this)">🔐 دخول</div>
      <div class="tab" onclick="sw('register',this)">✨ حساب جديد</div>
    </div>
    <div class="err" id="err"></div>
    <form id="loginForm" onsubmit="event.preventDefault();doLogin()">
      <div class="fg"><label>👤 اسم المستخدم</label><input type="text" id="lu" placeholder="اكتب اسم المستخدم" required autocomplete="username"></div>
      <div class="fg"><label>🔒 كلمة المرور</label><input type="password" id="lp" placeholder="اكتب كلمة المرور" required autocomplete="current-password"></div>
      <button type="submit" class="btn" id="lb">🚀 دخول</button>
    </form>
    <form id="registerForm" style="display:none" onsubmit="event.preventDefault();doReg()">
      <div class="fg"><label>👤 اسم المستخدم</label><input type="text" id="ru" placeholder="3 أحرف على الأقل" required minlength="3" autocomplete="username"></div>
      <div class="fg"><label>📧 البريد (اختياري)</label><input type="email" id="re" placeholder="example@email.com" autocomplete="email"></div>
      <div class="fg"><label>🔒 كلمة المرور</label><input type="password" id="rp" placeholder="6 أحرف على الأقل" required minlength="6" autocomplete="new-password"></div>
      <button type="submit" class="btn" id="rb">✨ إنشاء الحساب</button>
    </form>
    <div class="divider">أو تواصل معنا</div>
    <a href="https://t.me/Yb_xY" target="_blank" class="tg">📱 الدعم — @Yb_xY</a>
  </div>
</div>
<script>
(function(){const c=document.getElementById('c'),x=c.getContext('2d');let w,h,ps=[];function rs(){w=c.width=innerWidth;h=c.height=innerHeight}rs();addEventListener('resize',rs);for(let i=0;i<60;i++)ps.push({x:Math.random()*w,y:Math.random()*h,r:Math.random()*2+1,vx:(Math.random()-.5)*.4,vy:(Math.random()-.5)*.4,hu:Math.random()>.5?340:270});function d(){x.clearRect(0,0,w,h);ps.forEach((p,i)=>{p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>w)p.vx*=-1;if(p.y<0||p.y>h)p.vy*=-1;x.beginPath();x.arc(p.x,p.y,p.r,0,Math.PI*2);x.fillStyle=`hsla(${p.hu},80%,65%,.7)`;x.fill();for(let j=i+1;j<ps.length;j++){const q=ps[j],dx=p.x-q.x,dy=p.y-q.y,dd=Math.sqrt(dx*dx+dy*dy);if(dd<130){x.beginPath();x.moveTo(p.x,p.y);x.lineTo(q.x,q.y);x.strokeStyle=`hsla(${p.hu},80%,65%,${(1-dd/130)*.3})`;x.lineWidth=.6;x.stroke()}}});requestAnimationFrame(d)}d()})();
function sw(t,e){document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));e.classList.add('active');document.getElementById('loginForm').style.display=t==='login'?'':'none';document.getElementById('registerForm').style.display=t==='register'?'':'none';document.getElementById('err').classList.remove('show')}
function err(m){const b=document.getElementById('err');b.textContent='⚠️ '+m;b.classList.add('show');setTimeout(()=>b.classList.remove('show'),7000)}
async function doLogin(){
  const u=document.getElementById('lu').value.trim(),p=document.getElementById('lp').value;
  if(!u||!p)return err('أدخل اسم المستخدم وكلمة المرور');
  const b=document.getElementById('lb');b.disabled=true;b.textContent='جاري...';
  try{
    const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});
    if(!r.ok){err('خطأ سيرفر: '+r.status);b.disabled=false;b.textContent='🚀 دخول';return;}
    const d=await r.json();
    if(d.success){location.href='/';}
    else{err(d.error||'خطأ غير معروف');b.disabled=false;b.textContent='🚀 دخول';}
  }catch(e){err('تعذّر الاتصال بالسيرفر: '+e.message);b.disabled=false;b.textContent='🚀 دخول';}
}
async function doReg(){
  const u=document.getElementById('ru').value.trim(),e=document.getElementById('re').value.trim(),p=document.getElementById('rp').value;
  if(!u||!p)return err('أكمل الحقول المطلوبة');
  if(u.length<3)return err('اسم المستخدم قصير (3 أحرف على الأقل)');
  if(p.length<6)return err('كلمة المرور قصيرة (6 أحرف على الأقل)');
  const b=document.getElementById('rb');b.disabled=true;b.textContent='جاري...';
  try{
    const r=await fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p,email:e})});
    if(!r.ok){err('خطأ سيرفر: '+r.status);b.disabled=false;b.textContent='✨ إنشاء الحساب';return;}
    const d=await r.json();
    if(d.success){location.href='/';}
    else{err(d.error||'خطأ غير معروف');b.disabled=false;b.textContent='✨ إنشاء الحساب';}
  }catch(e){err('تعذّر الاتصال بالسيرفر: '+e.message);b.disabled=false;b.textContent='✨ إنشاء الحساب';}
}
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# HTML: API KEYS
# ═══════════════════════════════════════════════════════════════

API_KEYS_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>مفاتيح API — SOST AI</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Cairo',sans-serif}
body{background:#0a0a0f;color:#f5f5f7;min-height:100vh;padding:20px;line-height:1.6}
.wrap{max-width:1100px;margin:0 auto}
header{background:linear-gradient(135deg,#e11d48,#7c3aed);padding:24px 30px;border-radius:20px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:14px}
h1{font-size:1.5rem;font-weight:900}
.nav{display:flex;gap:10px;flex-wrap:wrap}
.nav a{padding:10px 18px;border-radius:12px;background:rgba(255,255,255,.15);color:#fff;text-decoration:none;font-weight:700;font-size:.88rem}
.card{background:rgba(15,15,24,.9);border:1px solid rgba(225,29,72,.2);border-radius:20px;padding:26px;margin-bottom:20px}
.card h2{font-size:1.2rem;margin-bottom:18px}
.fg{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:14px}
input{padding:13px 16px;border-radius:13px;width:100%;background:rgba(255,255,255,.04);border:1px solid rgba(225,29,72,.2);color:#fff;font-family:inherit;font-size:.92rem;outline:none}
input:focus{border-color:#e11d48}
.btn{padding:13px 24px;border-radius:13px;border:none;background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;font-weight:700;font-size:.92rem;cursor:pointer;font-family:inherit}
.btn:disabled{opacity:.5;cursor:not-allowed}
.btn.danger{background:linear-gradient(135deg,#ef4444,#b91c1c)}
.btn.small{padding:8px 14px;font-size:.8rem;border-radius:10px}
.info{background:rgba(225,29,72,.1);border:1px solid rgba(225,29,72,.3);border-radius:12px;padding:14px;margin-bottom:14px;color:#c5c5d5;font-size:.88rem}
.kc{background:rgba(255,255,255,.03);border:1px solid rgba(225,29,72,.15);border-radius:16px;padding:18px;margin-bottom:14px}
.kh{display:flex;justify-content:space-between;margin-bottom:12px;gap:10px;flex-wrap:wrap}
.kn{font-weight:700;font-size:1rem;display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.kv{font-family:monospace;background:#0a0e17;border:1px solid rgba(225,29,72,.3);border-radius:10px;padding:12px 14px;margin:10px 0;font-size:.85rem;display:flex;justify-content:space-between;align-items:center;gap:10px;word-break:break-all;direction:ltr}
.kv code{color:#fb7185;flex:1}
.cb{padding:6px 12px;border-radius:8px;background:rgba(225,29,72,.2);border:none;color:#fb7185;font-weight:700;font-size:.75rem;cursor:pointer;flex-shrink:0}
.cb:hover{background:#e11d48;color:#fff}
.ks{display:flex;gap:14px;flex-wrap:wrap;font-size:.8rem;color:#9a9aae;margin-top:10px}
.pr{width:100%;height:6px;background:rgba(255,255,255,.05);border-radius:3px;margin-top:10px;overflow:hidden}
.pb{height:100%;background:linear-gradient(90deg,#e11d48,#7c3aed)}
.bd{padding:3px 10px;border-radius:8px;font-size:.72rem;font-weight:700}
.bd.a{background:rgba(16,185,129,.2);color:#34d399}
.bd.i{background:rgba(239,68,68,.2);color:#fca5a5}
.bd.b{background:rgba(239,68,68,.3);color:#fca5a5}
.empty{text-align:center;padding:40px;color:#9a9aae}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.8);backdrop-filter:blur(10px);z-index:1000;display:none;align-items:center;justify-content:center;padding:20px}
.modal.show{display:flex}
.mc{background:#0f0f18;border:1px solid rgba(225,29,72,.3);border-radius:20px;padding:30px;max-width:520px;width:100%}
.mc h3{margin-bottom:14px}
.mb{display:flex;gap:10px;margin-top:20px}
.mb button{flex:1;padding:13px;border-radius:12px;border:none;font-family:inherit;font-weight:700;cursor:pointer;background:rgba(107,114,128,.3);color:#fff}
.toast{position:fixed;bottom:30px;left:50%;transform:translateX(-50%) translateY(100px);background:#0f0f18;border:1px solid #e11d48;color:#fff;padding:14px 24px;border-radius:14px;font-weight:700;z-index:9999;transition:.4s;opacity:0;pointer-events:none}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
@media(max-width:640px){.fg{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>🔑 مفاتيح API</h1>
    <div class="nav"><a href="/">← الرئيسية</a><a href="/api/docs" target="_blank">📖 التوثيق</a></div>
  </header>
  <div class="card">
    <h2>➕ إنشاء مفتاح جديد</h2>
    <div class="info" id="daily">جاري التحميل...</div>
    <div class="fg">
      <input type="text" id="kn" placeholder="اسم المفتاح" maxlength="50">
      <input type="text" id="sv" placeholder="اسم الخدمة" maxlength="50">
    </div>
    <button class="btn" id="cb" onclick="createKey()">🔑 إنشاء مفتاح مجاني (10 رسائل)</button>
  </div>
  <div class="card">
    <h2>🔐 مفاتيحك (<span id="cnt">0</span>)</h2>
    <div id="list"><div class="empty">جاري التحميل...</div></div>
  </div>
</div>
<div class="modal" id="nm"><div class="mc"><h3>✅ تم إنشاء المفتاح!</h3>
  <p style="color:#9a9aae;font-size:.88rem;margin-bottom:14px">⚠️ احفظه — لن يظهر مرة أخرى.</p>
  <div class="kv"><code id="nv"></code><button class="cb" onclick="cpN()">📋</button></div>
  <div class="mb"><button onclick="document.getElementById('nm').classList.remove('show');load()">حسناً</button></div>
</div></div>
<div class="toast" id="tt"></div>
<script>
async function api(u,o){return (await fetch(u,o)).json()}
async function load(){
  const d=await api('/api/keys/list');
  const l=document.getElementById('list'),c=document.getElementById('cnt');
  if(!d.keys||!d.keys.length){l.innerHTML='<div class="empty">لا توجد مفاتيح</div>';c.textContent='0';return}
  c.textContent=d.keys.length;
  l.innerHTML=d.keys.map(k=>{
    const u=k.messages_used||0,li=k.messages_limit||10,p=Math.min(100,Math.round(u/li*100));
    let b='<span class="bd a">✅ نشط</span>';
    if(k.banned)b='<span class="bd b">🚫 محظور</span>';
    else if(!k.active)b='<span class="bd i">⏸️ ملغى</span>';
    return `<div class="kc"><div class="kh"><div><div class="kn">🔑 ${esc(k.key_name)} ${b}</div><div style="font-size:.78rem;color:#9a9aae;margin-top:3px">🏷️ ${esc(k.service_name)}</div></div><div style="display:flex;gap:6px;flex-wrap:wrap">${k.banned?'':`<button class="btn small" onclick="tg(${k.id})">${k.active?'إلغاء':'تفعيل'}</button>`}<button class="btn small danger" onclick="del(${k.id})">🗑️</button></div></div><div class="kv"><code>${esc(k.key_value)}</code><button class="cb" onclick="cp('${k.key_value}')">📋</button></div><div class="ks"><span>💬 ${u}/${li}</span></div><div class="pr"><div class="pb" style="width:${p}%"></div></div></div>`;
  }).join('');
}
async function daily(){
  const d=await api('/api/keys/daily');
  document.getElementById('daily').innerHTML=`📊 أُنشئ اليوم: <strong>${d.used}</strong> / <strong>${d.limit}</strong> • متبقي: <strong>${d.remaining}</strong>`;
  const b=document.getElementById('cb');
  if(d.remaining<=0){b.disabled=true;b.textContent='⏰ وصلت للحد اليومي';}else{b.disabled=false;b.textContent='🔑 إنشاء مفتاح مجاني (10 رسائل)';}
}
async function createKey(){
  const n=document.getElementById('kn').value.trim(),s=document.getElementById('sv').value.trim();
  if(!n||!s)return tt('⚠️ املأ الاسم والخدمة');
  const b=document.getElementById('cb');b.disabled=true;b.textContent='جاري...';
  const r=await api('/api/keys/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key_name:n,service_name:s})});
  if(r.success){document.getElementById('nv').textContent=r.key;document.getElementById('nm').classList.add('show');document.getElementById('kn').value='';document.getElementById('sv').value='';daily();load();}
  else{tt('❌ '+(r.error||'فشل'));b.disabled=false;b.textContent='🔑 إنشاء مفتاح مجاني (10 رسائل)';}
}
async function del(id){if(!confirm('حذف؟'))return;await api('/api/keys/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});tt('🗑️');load();}
async function tg(id){await api('/api/keys/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});load();}
function cp(t){navigator.clipboard.writeText(t).then(()=>tt('📋'))}
function cpN(){cp(document.getElementById('nv').textContent)}
function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML}
let tmp;function tt(m){const t=document.getElementById('tt');t.textContent=m;t.classList.add('show');clearTimeout(tmp);tmp=setTimeout(()=>t.classList.remove('show'),2500)}
load();daily();
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# HTML: API DOCS
# ═══════════════════════════════════════════════════════════════

API_DOCS_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>توثيق API — SOST AI</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Cairo',sans-serif}
body{background:#0a0a0f;color:#f5f5f7;min-height:100vh;padding:20px;line-height:1.8}
.wrap{max-width:900px;margin:0 auto}
header{background:linear-gradient(135deg,#e11d48,#7c3aed);padding:24px 30px;border-radius:20px;margin-bottom:24px}
h1{font-size:1.6rem;font-weight:900}
.card{background:rgba(15,15,24,.9);border:1px solid rgba(225,29,72,.2);border-radius:20px;padding:26px;margin-bottom:20px}
h2{font-size:1.2rem;margin-bottom:14px;color:#fb7185}
pre{background:#0a0e17;border:1px solid rgba(225,29,72,.3);border-radius:12px;padding:16px;overflow-x:auto;direction:ltr;text-align:left;font-family:monospace;font-size:.82rem;color:#e2e8f0;margin:10px 0}
.back{display:inline-block;padding:10px 20px;border-radius:12px;background:rgba(225,29,72,.2);color:#fb7185;text-decoration:none;font-weight:700;margin-bottom:16px}
table{width:100%;border-collapse:collapse;margin:12px 0;font-size:.88rem}
th,td{padding:10px;text-align:right;border-bottom:1px solid rgba(225,29,72,.15)}
th{color:#fb7185;font-weight:700}
code{background:rgba(225,29,72,.15);padding:2px 6px;border-radius:6px;font-size:.85em;color:#fb7185}
</style>
</head>
<body>
<div class="wrap">
  <a href="/keys" class="back">← رجوع</a>
  <header><h1>📖 توثيق SOST AI API</h1></header>
  <div class="card">
    <h2>🔐 المصادقة</h2>
    <pre>Authorization: Bearer SOST-XXXX-XXXX-XXXX</pre>
  </div>
  <div class="card">
    <h2>💬 إرسال رسالة دردشة</h2>
    <pre>POST /v1/chat/completions

Headers:
  Content-Type: application/json
  Authorization: Bearer SOST-XXXX-XXXX-XXXX

Body:
{
  "message": "مرحباً",
  "model": "wormgpt"
}</pre>
    <h2>✅ الرد</h2>
    <pre>{
  "success": true,
  "reply": "...",
  "model": "wormgpt",
  "usage": {"used": 3, "limit": 10, "remaining": 7}
}</pre>
    <h2>❌ الأخطاء</h2>
    <table>
      <tr><th>كود</th><th>الوصف</th></tr>
      <tr><td>401</td><td>مفتاح غير صالح</td></tr>
      <tr><td>403</td><td>ملغى/منتهي/محظور</td></tr>
      <tr><td>429</td><td>تجاوز الحد</td></tr>
      <tr><td>400</td><td>رسالة فارغة</td></tr>
    </table>
  </div>
  <div class="card">
    <h2>🐍 Python</h2>
    <pre>import requests
r = requests.post("https://your-domain/v1/chat/completions",
    headers={"Authorization": "Bearer SOST-XXXX-XXXX-XXXX"},
    json={"message": "مرحباً", "model": "wormgpt"})
print(r.json()["reply"])</pre>
  </div>
</div>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# HTML: MAIN
# ═══════════════════════════════════════════════════════════════

MAIN_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5">
<title>SOST AI</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect width='24' height='24' rx='6' fill='%23e11d48'/><path d='M12 4L14 10L20 12L14 14L12 20L10 14L4 12L10 10L12 4Z' fill='white'/></svg>">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{height:100%;font-family:'Cairo',system-ui,sans-serif;background:#0a0a0f;color:#f5f5f7;overflow:hidden}
body{display:flex}
#bgCanvas{position:fixed;inset:0;z-index:0;pointer-events:none}
.sb{width:280px;background:#0f0f18;border-left:1px solid #1f1f2e;display:flex;flex-direction:column;height:100vh;transition:transform .3s;flex-shrink:0;z-index:100;position:relative}
.sb.col{transform:translateX(100%);position:fixed;top:0;right:0}
.sbh{padding:16px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1f1f2e}
.sbl{display:flex;align-items:center;gap:10px;font-weight:900;font-size:1.05rem;cursor:pointer;color:#f5f5f7}
.sbli{width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,#e11d48,#7c3aed);display:flex;align-items:center;justify-content:center;box-shadow:0 4px 16px rgba(225,29,72,.4)}
.cs{width:32px;height:32px;border-radius:8px;border:none;background:transparent;cursor:pointer;color:#9a9aae;font-size:1.2rem}
.cs:hover{background:#1f1f2e}
.sbb{flex:1;overflow-y:auto;padding:12px}
.sbb::-webkit-scrollbar{width:6px}
.sbb::-webkit-scrollbar-thumb{background:#1f1f2e;border-radius:3px}
.sb-b{display:flex;align-items:center;gap:10px;width:100%;padding:12px 14px;border-radius:11px;border:none;background:transparent;color:#f5f5f7;font-family:inherit;font-size:.92rem;font-weight:600;cursor:pointer;text-align:right;transition:.15s;margin-bottom:4px;text-decoration:none}
.sb-b:hover{background:#1f1f2e}
.sb-b .ico{width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:1rem;flex-shrink:0}
.sb-b.pri{background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;margin-bottom:16px;box-shadow:0 8px 24px rgba(225,29,72,.35)}
.sb-b.pri:hover{background:linear-gradient(135deg,#be123c,#6d28d9);transform:translateY(-2px)}
.sec{padding:16px 14px 8px;font-size:.72rem;color:#6a6a80;font-weight:800;text-transform:uppercase;letter-spacing:.5px}
.cm{display:flex;align-items:center;gap:8px;padding:9px 11px;border-radius:9px;cursor:pointer;font-size:.86rem;color:#c5c5d5;transition:.15s}
.cm:hover{background:#1f1f2e}
.cmt{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cmd{opacity:0;width:22px;height:22px;border-radius:6px;border:none;background:transparent;color:#9a9aae;cursor:pointer;font-size:.8rem;flex-shrink:0}
.cm:hover .cmd{opacity:1}
.cmd:hover{background:#ef4444;color:#fff}
.sbf{padding:12px;border-top:1px solid #1f1f2e}
.uc{display:flex;align-items:center;gap:10px;padding:10px;border-radius:12px;cursor:pointer;transition:.15s}
.uc:hover{background:#1f1f2e}
.ua{width:38px;height:38px;border-radius:50%;background:linear-gradient(135deg,#e11d48,#7c3aed);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:900;font-size:.95rem;flex-shrink:0;overflow:hidden;box-shadow:0 4px 12px rgba(225,29,72,.4)}
.ui{flex:1;min-width:0}
.un{font-weight:700;font-size:.88rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.us{font-size:.72rem;color:#9a9aae}
.mn{flex:1;display:flex;flex-direction:column;height:100vh;min-width:0;background:#0a0a0f;position:relative;z-index:1}
.tb{padding:14px 18px;display:flex;align-items:center;gap:12px;border-bottom:1px solid #1f1f2e;flex-shrink:0;background:#0f0f18}
.mt{width:40px;height:40px;border-radius:11px;border:none;background:transparent;cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;flex-shrink:0}
.mt:hover{background:#1f1f2e}
.mt span{width:20px;height:2px;background:#f5f5f7;border-radius:2px}
.ms{display:flex;align-items:center;gap:10px;padding:10px 16px;border-radius:13px;border:1px solid #1f1f2e;background:#0f0f18;cursor:pointer;font-weight:800;font-size:.92rem;transition:.15s;position:relative;color:#f5f5f7}
.ms:hover{border-color:#e11d48;box-shadow:0 0 20px rgba(225,29,72,.2)}
.ms .ar{font-size:.7rem;color:#9a9aae;transition:.2s}
.ms.op .ar{transform:rotate(180deg)}
.mis{width:24px;height:24px;border-radius:7px;display:flex;align-items:center;justify-content:center;font-size:.9rem;color:#fff;font-weight:900;background:#e11d48}
.md{position:absolute;top:calc(100% + 6px);right:0;background:#0f0f18;border:1px solid #1f1f2e;border-radius:14px;box-shadow:0 20px 60px rgba(0,0,0,.6);padding:8px;min-width:320px;opacity:0;transform:translateY(-8px);pointer-events:none;transition:.2s;z-index:200;max-height:70vh;overflow-y:auto}
.md.show{opacity:1;transform:translateY(0);pointer-events:auto}
.mi{display:flex;align-items:center;gap:12px;padding:12px;border-radius:11px;cursor:pointer;transition:.15s}
.mi:hover{background:#1f1f2e}
.mi.act{background:#1f1f2e}
.mimg{width:42px;height:42px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:1.2rem;color:#fff;font-weight:900}
.mii{flex:1}
.min{font-weight:800;font-size:.92rem}
.mid{font-size:.75rem;color:#9a9aae;margin-top:2px}
.mic{color:#10b981;font-weight:900}
.ch{flex:1;overflow-y:auto;padding:24px 18px 40px;scroll-behavior:smooth}
.ch::-webkit-scrollbar{width:8px}
.ch::-webkit-scrollbar-thumb{background:#1f1f2e;border-radius:4px}
.wl{max-width:780px;margin:20px auto;text-align:center}
.wi{width:180px;height:180px;margin:0 auto 20px;border-radius:26px;overflow:hidden;box-shadow:0 25px 70px rgba(225,29,72,.4);animation:bo 4s ease-in-out infinite;background:#1f1f2e;position:relative}
.wi::after{content:'';position:absolute;inset:-3px;border-radius:28px;background:linear-gradient(135deg,#e11d48,#7c3aed);z-index:-1;filter:blur(15px);opacity:.6}
.wi img{width:100%;height:100%;object-fit:cover;display:block}
@keyframes bo{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-10px) scale(1.02)}}
.wl h1{font-size:2rem;font-weight:900;margin-bottom:12px;background:linear-gradient(135deg,#e11d48,#7c3aed,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.wl p{color:#9a9aae;font-size:1rem;line-height:1.7;max-width:520px;margin:0 auto 30px}
.chips{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:10px;max-width:680px;margin:0 auto}
.chip{padding:14px 16px;border-radius:15px;border:1px solid #1f1f2e;background:#0f0f18;cursor:pointer;transition:.2s;text-align:right;font-family:inherit;font-size:.88rem;color:#f5f5f7}
.chip:hover{border-color:#e11d48;background:#141420;transform:translateY(-3px);box-shadow:0 8px 24px rgba(225,29,72,.2)}
.chip strong{display:block;margin-bottom:4px;font-weight:800;font-size:.92rem}
.chip span{color:#9a9aae;font-size:.8rem}
.msgs{max-width:780px;margin:0 auto}
.mg{margin-bottom:24px;animation:fd .3s}
@keyframes fd{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
.mg.u{display:flex;justify-content:flex-end}
.mg.b{display:flex;gap:12px}
.ma{width:36px;height:36px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:.95rem;color:#fff;font-weight:900}
.mg.b .ma{background:linear-gradient(135deg,#e11d48,#7c3aed);box-shadow:0 4px 12px rgba(225,29,72,.4)}
.mbd{flex:1;min-width:0}
.mg.u .mbd{max-width:80%}
.bb{line-height:1.75;font-size:.97rem;word-wrap:break-word;color:#f5f5f7}
.mg.u .bb{background:linear-gradient(135deg,#1f1f2e,#181826);padding:13px 17px;border-radius:18px;border:1px solid rgba(225,29,72,.15)}
.mg.b .bb{background:transparent;padding:2px 0}
.bb p{margin:8px 0}.bb p:first-child{margin-top:0}.bb p:last-child{margin-bottom:0}
.bb h1,.bb h2,.bb h3,.bb h4{margin:16px 0 10px;font-weight:800;color:#fb7185}
.bb ul,.bb ol{margin:10px 0;padding-right:24px}
.bb li{margin:5px 0}
.bb code{background:#1f1f2e;padding:2px 6px;border-radius:5px;font-family:monospace;font-size:.88em;color:#fb7185}
.bb pre{background:#000;color:#e2e8f0;border-radius:12px;padding:14px;overflow-x:auto;margin:12px 0;direction:ltr;text-align:left;font-size:.85rem;line-height:1.5;border:1px solid #1f1f2e}
.bb pre code{background:transparent;color:inherit;padding:0}
.bb table{border-collapse:collapse;margin:12px 0;width:100%;font-size:.88rem}
.bb th,.bb td{border:1px solid #1f1f2e;padding:8px 12px}
.bb th{background:#141420;font-weight:800;color:#fb7185}
.bb a{color:#fb7185;text-decoration:none}
.bb a:hover{text-decoration:underline}
.tp{display:inline-flex;gap:5px;padding:8px 0}
.tp span{width:8px;height:8px;border-radius:50%;background:#e11d48;animation:td 1.2s infinite ease-in-out}
.tp span:nth-child(2){animation-delay:.15s}
.tp span:nth-child(3){animation-delay:.3s}
@keyframes td{0%,60%,100%{opacity:.3;transform:scale(.7)}30%{opacity:1;transform:scale(1)}}
.ia{padding:16px 18px 22px;flex-shrink:0;background:#0a0a0f}
.ib{max-width:780px;margin:0 auto;background:#0f0f18;border:1px solid #1f1f2e;border-radius:22px;padding:8px 8px 8px 14px;display:flex;gap:8px;align-items:flex-end;transition:.2s}
.ib:focus-within{border-color:#e11d48;background:#141420;box-shadow:0 0 30px rgba(225,29,72,.15)}
#ui{flex:1;background:transparent;border:none;outline:none;font-family:inherit;font-size:.98rem;color:#f5f5f7;resize:none;padding:10px 6px;line-height:1.5;max-height:200px}
#ui::placeholder{color:#6a6a80}
.ibtn{width:42px;height:42px;border-radius:50%;border:none;background:transparent;color:#9a9aae;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:.2s;font-size:1.1rem}
.ibtn:hover{background:#1f1f2e;color:#fb7185}
.ibtn.rec{background:#ef4444;color:#fff;animation:pl 1s infinite}
#sb{width:42px;height:42px;border-radius:50%;border:none;background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;transition:.2s;box-shadow:0 4px 16px rgba(225,29,72,.4)}
#sb:hover:not(:disabled){transform:scale(1.08);box-shadow:0 6px 24px rgba(225,29,72,.6)}
#sb:disabled{opacity:.3;cursor:not-allowed}
.hint{max-width:780px;margin:8px auto 0;font-size:.72rem;color:#6a6a80;text-align:center}
.ov{position:fixed;inset:0;background:rgba(0,0,0,.85);backdrop-filter:blur(6px);z-index:500;display:none;align-items:center;justify-content:center;padding:20px}
.ov.show{display:flex}
.md2{background:#0f0f18;border:1px solid #1f1f2e;border-radius:22px;padding:28px;max-width:520px;width:100%;max-height:88vh;overflow-y:auto;box-shadow:0 30px 90px rgba(225,29,72,.3);position:relative;color:#f5f5f7}
.md2 h2{font-size:1.3rem;margin-bottom:18px;font-weight:900}
.mc2{float:left;width:34px;height:34px;border-radius:9px;border:none;background:#1f1f2e;color:#f5f5f7;cursor:pointer;font-size:1rem}
.mc2:hover{background:#e11d48}
.pc{border:2px solid #1f1f2e;border-radius:16px;padding:18px;margin-bottom:14px;position:relative;transition:.2s}
.pc:hover{border-color:rgba(225,29,72,.4)}
.pc.f{border-color:#e11d48;background:linear-gradient(135deg,rgba(225,29,72,.1),rgba(124,58,237,.1));box-shadow:0 0 30px rgba(225,29,72,.2)}
.pb2{position:absolute;top:-11px;left:16px;background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;font-size:.7rem;padding:4px 12px;border-radius:9px;font-weight:800}
.ph{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px}
.pn{font-weight:900;font-size:1.08rem}
.pp{font-weight:900;font-size:1.4rem;color:#fb7185}
.pfl{list-style:none;font-size:.86rem;color:#9a9aae;margin:10px 0}
.pfl li{padding:4px 0}
.pbt{width:100%;padding:12px;border-radius:12px;border:none;background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;font-weight:800;cursor:pointer;font-family:inherit;margin-top:10px;transition:.2s}
.pbt:hover{transform:translateY(-2px);box-shadow:0 8px 24px rgba(225,29,72,.4)}
.sr{display:flex;justify-content:space-between;align-items:center;padding:13px;border-radius:12px;background:#141420;margin-bottom:8px;gap:10px;border:1px solid #1f1f2e}
.sri{flex:1;min-width:0}
.srd{font-weight:700;font-size:.92rem}
.srm{font-size:.75rem;color:#9a9aae;margin-top:3px}
.scc{font-size:.7rem;color:#10b981;font-weight:800}
.bs{padding:7px 14px;border-radius:9px;border:none;background:#ef4444;color:#fff;font-family:inherit;font-weight:800;font-size:.78rem;cursor:pointer}
.bs:hover{background:#dc2626}
.ft{padding:15px;border-radius:13px;background:linear-gradient(135deg,rgba(16,185,129,.1),rgba(16,185,129,.05));border:1px solid rgba(16,185,129,.3);margin-bottom:10px;display:flex;align-items:center;gap:12px}
.fti{width:42px;height:42px;border-radius:11px;background:linear-gradient(135deg,#10b981,#059669);color:#fff;display:flex;align-items:center;justify-content:center;font-size:1.2rem;flex-shrink:0}
.ftt{font-weight:800;font-size:.92rem}
.ftd{font-size:.75rem;color:#9a9aae;margin-top:3px}
.to{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(100px);background:#1f1f2e;color:#f5f5f7;padding:13px 22px;border-radius:13px;font-size:.88rem;font-weight:700;opacity:0;transition:.3s;z-index:9999;pointer-events:none;max-width:90vw;text-align:center;border:1px solid #e11d48;box-shadow:0 8px 30px rgba(225,29,72,.4)}
.to.show{opacity:1;transform:translateX(-50%) translateY(0)}
.sp{position:fixed;inset:0;background:linear-gradient(135deg,#0a0a0f 0%,#1a0510 50%,#0f0518 100%);z-index:2000;display:flex;align-items:center;justify-content:center;flex-direction:column;padding:20px;text-align:center;transition:opacity .4s;overflow-y:auto}
.sp.hide{opacity:0;pointer-events:none}
.si{width:180px;height:180px;margin-bottom:26px;border-radius:50%;overflow:hidden;box-shadow:0 30px 80px rgba(225,29,72,.5);animation:sbo 3s ease-in-out infinite;background:#1f1f2e;position:relative}
.si::after{content:'';position:absolute;inset:-4px;border-radius:50%;background:linear-gradient(135deg,#e11d48,#7c3aed,#06b6d4);z-index:-1;filter:blur(15px);opacity:.8}
.si img{width:100%;height:100%;object-fit:cover;display:block}
@keyframes sbo{0%,100%{transform:translateY(0) rotate(-2deg)}50%{transform:translateY(-12px) rotate(2deg)}}
.sp h2{font-size:1.9rem;font-weight:900;margin-bottom:12px;color:#f5f5f7;background:linear-gradient(135deg,#e11d48,#7c3aed,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sp p{color:#9a9aae;margin-bottom:32px;font-size:1rem}
.mcs{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:14px;max-width:400px;width:100%;justify-content:center}
.mc3{padding:26px 20px;border-radius:20px;border:2px solid #1f1f2e;background:#0f0f18;cursor:pointer;transition:.25s;text-align:center;font-family:inherit;color:#f5f5f7}
.mc3:hover{border-color:#e11d48;transform:translateY(-6px);box-shadow:0 20px 50px rgba(225,29,72,.3)}
.mc3.sel{border-color:#e11d48;background:linear-gradient(135deg,rgba(225,29,72,.15),rgba(124,58,237,.15))}
.mc3i{width:80px;height:80px;border-radius:22px;margin:0 auto 14px;display:flex;align-items:center;justify-content:center;font-size:2.4rem;color:#fff;font-weight:900;box-shadow:0 10px 30px rgba(225,29,72,.4)}
.mc3n{font-weight:900;font-size:1.1rem;margin-bottom:6px}
.mc3d{font-size:.8rem;color:#9a9aae}
.att-prev{display:flex;flex-wrap:wrap;gap:8px;max-width:780px;margin:0 auto 8px;padding:0 14px}
.att{position:relative;width:72px;height:72px;border-radius:11px;overflow:hidden;border:1px solid #1f1f2e;background:#141420}
.att img{width:100%;height:100%;object-fit:cover}
.att .rm{position:absolute;top:2px;right:2px;width:22px;height:22px;border-radius:50%;background:#ef4444;color:#fff;border:none;cursor:pointer;font-size:.75rem;line-height:1;font-weight:800}
.att .ft{width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:.6rem;text-align:center;padding:4px;word-break:break-all;color:#f5f5f7}
.voice-bar{position:fixed;bottom:0;left:0;right:0;background:#0f0f18;color:#fff;padding:14px;display:none;align-items:center;gap:12px;z-index:1500;box-shadow:0 -4px 30px rgba(225,29,72,.3);border-top:1px solid #1f1f2e}
.voice-bar.show{display:flex}
.voice-bar .pulse{width:14px;height:14px;border-radius:50%;background:#ef4444;animation:pl 1s infinite}
@keyframes pl{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.4;transform:scale(1.4)}}
.voice-bar .txt{flex:1;font-size:.9rem}
.voice-bar button{padding:11px 20px;border-radius:12px;border:none;font-family:inherit;font-weight:800;cursor:pointer;background:#ef4444;color:#fff}
.voice-bar button.keep{background:#10b981}
@media(max-width:768px){
  .sb{position:fixed;top:0;right:0;transform:translateX(100%)}
  .sb.mo{transform:translateX(0)}
  .mt{display:flex}
  .wl h1{font-size:1.5rem}
  .wi{width:130px;height:130px}
  .mg.u .mbd{max-width:88%}
  .ia{padding:12px 12px 16px}
  .md{min-width:260px}
  .mcs{grid-template-columns:1fr}
}
@media(min-width:769px){
  .mt{display:none}
  .sb .cs{display:none}
}
</style>
</head>
<body>

<canvas id="bgCanvas"></canvas>

<!-- SPLASH -->
<div class="sp" id="sp">
  <div class="si"><img src="" alt="" id="sImg"></div>
  <h2>🐛 WormGPT</h2>
  <p>النموذج الأقوى بدون قيود — جاهز للانطلاق</p>
  <div class="mcs" id="mcs"></div>
</div>

<!-- SIDEBAR -->
<aside class="sb" id="sb2">
  <div class="sbh">
    <div class="sbl" onclick="newChat()">
      <div class="sbli"><svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 2L14.5 8.5L21 11L14.5 13.5L12 20L9.5 13.5L3 11L9.5 8.5L12 2Z" fill="white"/></svg></div>
      <span>SOST AI</span>
    </div>
    <button class="cs" onclick="togSidebar()">✕</button>
  </div>
  <div class="sbb">
    <button class="sb-b pri" onclick="newChat()"><span class="ico">✨</span><span>محادثة جديدة</span></button>
    <button class="sb-b" onclick="openSaved()"><span class="ico">💾</span><span>محادثاتي المحفوظة</span></button>
    <button class="sb-b" onclick="saveCur()"><span class="ico">📌</span><span>حفظ الحالية</span></button>
    <div class="sec">قريباً</div>
    <button class="sb-b" onclick="comingSoon('upd')"><span class="ico">🚀</span><span>تحديثات قادمة</span></button>
    <button class="sb-b" onclick="comingSoon('mon')"><span class="ico">📊</span><span>مراقبة مشروعك</span></button>
    <button class="sb-b" onclick="comingSoon('sec')"><span class="ico">🛡️</span><span>الأمن السيبراني</span></button>
    <button class="sb-b" onclick="comingSoon('edu')"><span class="ico">📚</span><span>دراسة وتعليم</span></button>
    <button class="sb-b" onclick="comingSoon('dsn')"><span class="ico">🎨</span><span>مؤسسات والتصميم</span></button>
    <div class="sec" id="rlb" style="display:none">الأخيرة</div>
    <div id="rc"></div>
  </div>
  <div class="sbf">
    <button class="sb-b" onclick="openSupport()"><span class="ico">🎧</span><span>الدعم الفني</span></button>
    <button class="sb-b" onclick="openSub()"><span class="ico">💎</span><span>الاشتراكات</span></button>
    <a href="/keys" class="sb-b" style="text-decoration:none;color:inherit"><span class="ico">🔑</span><span>مفاتيح API</span></a>
    <div class="uc" onclick="openAcc()">
      <div class="ua">{{USERNAME_INITIAL}}</div>
      <div class="ui">
        <div class="un">{{USERNAME}}</div>
        <div class="us">{{SUB_LABEL}}</div>
      </div>
      <div style="color:#9a9aae">⚙️</div>
    </div>
  </div>
</aside>

<!-- MAIN -->
<div class="mn">
  <div class="tb">
    <button class="mt" onclick="togSidebar()"><span></span><span></span><span></span></button>
    <div class="ms" id="ms" onclick="togMD(event)">
      <div class="mis" id="mis">🐛</div>
      <span id="mn2">WormGPT</span>
      <span class="ar">▼</span>
      <div class="md" id="md" onclick="event.stopPropagation()"></div>
    </div>
  </div>
  <div class="ch" id="ch">
    <div class="wl" id="wl">
      <div class="wi"><img src="" alt="" id="wImg"></div>
      <h1>مرحباً {{USERNAME}} 🐛</h1>
      <p>WormGPT — النموذج الأقوى بدون قيود. اسألني أي شيء واحصل على إجابة فورية.</p>
      <div class="chips">
        <button class="chip" onclick="qa('اشرح لي مفهوم الذكاء الاصطناعي ببساطة')"><strong>🧠 تعلم</strong><span>ما هو AI؟</span></button>
        <button class="chip" onclick="qa('اكتب كود Python لحساب مضروب عدد')"><strong>💻 برمجة</strong><span>كود Python</span></button>
        <button class="chip" onclick="qa('اكتب قصيدة عربية عن الأمل')"><strong>✍️ إبداع</strong><span>قصيدة</span></button>
        <button class="chip" onclick="qa('أفضل نصائح لتعلم لغة جديدة')"><strong>💡 نصائح</strong><span>تعلم لغة</span></button>
      </div>
    </div>
    <div class="msgs" id="msgs"></div>
  </div>
  <div class="att-prev" id="attPrev"></div>
  <div class="ia">
    <div class="ib">
      <button class="ibtn" onclick="document.getElementById('fileIn').click()" title="ملف">📎</button>
      <input type="file" id="fileIn" style="display:none" multiple onchange="onFiles(event)">
      <textarea id="ui" placeholder="اكتب رسالتك هنا..." rows="1"></textarea>
      <button class="ibtn" id="vb" title="صوت">🎤</button>
      <button id="sb" onclick="send()">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
      </button>
    </div>
    <div class="hint">Enter للإرسال • Shift+Enter سطر جديد • يدعم حتى 30,000 حرف</div>
  </div>
</div>

<!-- VOICE BAR -->
<div class="voice-bar" id="voiceBar">
  <div class="pulse"></div>
  <div class="txt" id="voiceTxt">🎤 جاري الاستماع...</div>
  <button class="keep" onclick="stopVoice()">إيقاف</button>
</div>

<!-- OVERLAYS -->
<div class="ov" id="svd"><div class="md2"><button class="mc2" onclick="cl('svd')">✕</button><h2>💾 محادثاتي المحفوظة</h2><div id="svdL"></div></div></div>

<div class="ov" id="sub"><div class="md2"><button class="mc2" onclick="cl('sub')">✕</button><h2>💎 الاشتراكات</h2>
  <div class="pc"><div class="ph"><div class="pn">🆓 مجاني</div><div class="pp">$0</div></div><ul class="pfl"><li>✅ 15 رسالة مجانية</li><li>✅ 5 مفاتيح API يومياً</li><li>✅ 10 رسائل لكل مفتاح</li></ul></div>
  <div class="pc"><div class="ph"><div class="pn">⚡ أسبوعي</div><div class="pp">$2</div></div><ul class="pfl"><li>✅ 1000 رسالة</li></ul><button class="pbt" onclick="subs('weekly')">اشترك الآن</button></div>
  <div class="pc f"><div class="pb2">🔥 الأكثر طلباً</div><div class="ph"><div class="pn">🌙 شهري</div><div class="pp">$5</div></div><ul class="pfl"><li>✅ 9000 رسالة</li></ul><button class="pbt" onclick="subs('monthly')">اشترك الآن</button></div>
  <div class="pc"><div class="ph"><div class="pn">👑 سنوي</div><div class="pp">$10</div></div><ul class="pfl"><li>✅ رسائل غير محدودة</li></ul><button class="pbt" onclick="subs('yearly')">اشترك الآن</button></div>
  <p style="text-align:center;font-size:.85rem;color:#9a9aae;margin-top:14px">📱 <a href="https://t.me/Yb_xY" target="_blank" style="color:#fb7185;font-weight:800">@Yb_xY</a></p>
</div></div>

<div class="ov" id="acc"><div class="md2"><button class="mc2" onclick="cl('acc')">✕</button><h2>⚙️ الإعدادات</h2>
  <div style="background:#141420;border-radius:13px;padding:16px;margin-bottom:18px;border:1px solid #1f1f2e">
    <div style="font-weight:900;margin-bottom:6px">👤 {{USERNAME}}</div>
    <div style="font-size:.82rem;color:#9a9aae" id="accInfo">جاري...</div>
  </div>
  <h3 style="font-size:.95rem;margin-bottom:12px">🎙️ صوت المساعد</h3>
  <div style="display:flex;gap:8px;margin-bottom:18px">
    <button id="vM" class="pbt" style="flex:1;background:#1f1f2e" onclick="setVoice('male')">👨 ذكر</button>
    <button id="vF" class="pbt" style="flex:1;background:#e11d48" onclick="setVoice('female')">👩 أنثى</button>
  </div>
  <h3 style="font-size:.95rem;margin-bottom:12px">📱 الجلسات النشطة</h3>
  <div id="sessList">جاري...</div>
  <button class="pbt" style="background:#ef4444;margin-top:18px" onclick="logout()">🚪 تسجيل الخروج</button>
</div></div>

<div class="ov" id="cs"><div class="md2"><button class="mc2" onclick="cl('cs')">✕</button><h2 id="csT">🚀</h2><div id="csB"></div></div></div>

<div class="to" id="to"></div>

<script>
// ═══ Particles Background Animation ═══
(function(){
  const c=document.getElementById('bgCanvas'),x=c.getContext('2d');
  let w,h,ps=[];
  function rs(){w=c.width=innerWidth;h=c.height=innerHeight}
  rs();
  addEventListener('resize',rs);
  for(let i=0;i<70;i++)ps.push({x:Math.random()*w,y:Math.random()*h,r:Math.random()*2+1,vx:(Math.random()-.5)*.5,vy:(Math.random()-.5)*.5,hu:Math.random()>.5?340:270});
  function d(){
    x.clearRect(0,0,w,h);
    ps.forEach((p,i)=>{
      p.x+=p.vx;p.y+=p.vy;
      if(p.x<0||p.x>w)p.vx*=-1;
      if(p.y<0||p.y>h)p.vy*=-1;
      x.beginPath();
      x.arc(p.x,p.y,p.r,0,Math.PI*2);
      x.fillStyle=`hsla(${p.hu},80%,65%,.8)`;
      x.fill();
      for(let j=i+1;j<ps.length;j++){
        const q=ps[j],dx=p.x-q.x,dy=p.y-q.y,dd=Math.sqrt(dx*dx+dy*dy);
        if(dd<150){
          x.beginPath();
          x.moveTo(p.x,p.y);
          x.lineTo(q.x,q.y);
          x.strokeStyle=`hsla(${p.hu},80%,65%,${(1-dd/150)*.25})`;
          x.lineWidth=.6;
          x.stroke();
        }
      }
    });
    requestAnimationFrame(d);
  }
  d();
})();

const MODELS = {{MODELS_JSON}};
const USER = {name:'{{USERNAME}}', id:{{USER_ID}}, sub:'{{SUB_TYPE}}', remaining:'{{REMAINING}}', preferred:'{{PREFERRED_MODEL}}'};
const SPLASH_IMAGES = {{SPLASH_IMAGES_JSON}};
let curModel = 'wormgpt';
let sending = false;
let chatMsgs = [];
let attachments = [];
let voiceMode = false;
let voiceGender = localStorage.getItem('sost_voice') || 'female';

// SPLASH
const rndImg = SPLASH_IMAGES[Math.floor(Math.random()*SPLASH_IMAGES.length)];
document.getElementById('sImg').src = rndImg;
document.getElementById('wImg').src = SPLASH_IMAGES[(SPLASH_IMAGES.indexOf(rndImg)+1)%SPLASH_IMAGES.length];

function buildSplash(){
  document.getElementById('mcs').innerHTML = Object.values(MODELS).map(m => `
    <button class="mc3 ${m.id===curModel?'sel':''}" onclick="pickModel('${m.id}')">
      <div class="mc3i" style="background:${m.color}">${m.icon}</div>
      <div class="mc3n">${m.name}</div>
      <div class="mc3d">${m.desc}</div>
    </button>`).join('');
}
function pickModel(id){
  curModel = id;
  updateMUI();
  document.getElementById('sp').classList.add('hide');
  fetch('/api/set_model',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:id})}).catch(()=>{});
}
function buildMD(){
  document.getElementById('md').innerHTML = Object.values(MODELS).map(m => `
    <div class="mi ${m.id===curModel?'act':''}" onclick="pickMD('${m.id}')">
      <div class="mimg" style="background:${m.color}">${m.icon}</div>
      <div class="mii"><div class="min">${m.name}</div><div class="mid">${m.desc}</div></div>
      ${m.id===curModel?'<span class="mic">✓</span>':''}
    </div>`).join('');
}
function pickMD(id){
  curModel = id; updateMUI(); buildMD();
  document.getElementById('md').classList.remove('show');
  document.getElementById('ms').classList.remove('op');
  fetch('/api/set_model',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:id})}).catch(()=>{});
}
function updateMUI(){
  const m = MODELS[curModel]; if(!m) return;
  document.getElementById('mn2').textContent = m.name;
  const ic = document.getElementById('mis'); ic.textContent = m.icon;
  ic.style.background = m.color;
}
function togMD(e){e.stopPropagation();document.getElementById('md').classList.toggle('show');document.getElementById('ms').classList.toggle('op');}
document.addEventListener('click',()=>{document.getElementById('md')?.classList.remove('show');document.getElementById('ms')?.classList.remove('op')});

// VOICE GENDER
function setVoice(g){
  voiceGender = g;
  localStorage.setItem('sost_voice', g);
  document.getElementById('vM').style.background = g==='male'?'#e11d48':'#1f1f2e';
  document.getElementById('vF').style.background = g==='female'?'#e11d48':'#1f1f2e';
}

// SIDEBAR
function togSidebar(){
  const s = document.getElementById('sb2');
  if(window.innerWidth<=768) s.classList.toggle('mo');
  else s.classList.toggle('col');
}
function closeM(){document.getElementById('sb2').classList.remove('mo')}

// CHAT
function esc(t){const d=document.createElement('div');d.textContent=t||'';return d.innerHTML}
function rmd(t){try{marked.setOptions({breaks:true,gfm:true,headerIds:false});let h=marked.parse(t);if(window.DOMPurify)h=DOMPurify.sanitize(h,{ADD_ATTR:['target'],FORBID_TAGS:['style','script','iframe']});return h}catch(e){return esc(t).replace(/\n/g,'<br>')}}
function scrollB(){const c=document.getElementById('ch');requestAnimationFrame(()=>c.scrollTop=c.scrollHeight)}

function addMsg(role, text, files){
  const w = document.getElementById('msgs');
  document.getElementById('wl').style.display = 'none';
  const d = document.createElement('div');
  d.className = 'mg ' + role;
  if(role === 'user'){
    let attHtml = '';
    if(files && files.length){
      attHtml = '<div style="margin-bottom:8px">' + files.map(f=>{
        if(f.type && f.type.startsWith('image/')) return `<img src="${f.data}" style="max-width:200px;max-height:200px;border-radius:10px;display:block;margin-bottom:4px">`;
        return `<div style="background:#141420;border:1px solid #1f1f2e;border-radius:8px;padding:6px 10px;font-size:.8rem">📎 ${esc(f.name||'ملف')}</div>`;
      }).join('') + '</div>';
    }
    d.innerHTML = `<div class="mbd"><div class="bb">${attHtml}${esc(text).replace(/\n/g,'<br>')}</div></div>`;
  } else {
    const m = MODELS[curModel] || MODELS.wormgpt;
    d.innerHTML = `<div class="ma" style="background:${m.color}">${m.icon}</div><div class="mbd"><div class="bb">${rmd(text)}</div></div>`;
  }
  w.appendChild(d);
  chatMsgs.push({role, text, files: files||[]});
  scrollB();
}
function addTyping(){
  const w = document.getElementById('msgs');
  document.getElementById('wl').style.display = 'none';
  const d = document.createElement('div');
  d.className = 'mg b'; d.id = 'tp';
  const m = MODELS[curModel] || MODELS.wormgpt;
  d.innerHTML = `<div class="ma" style="background:${m.color}">${m.icon}</div><div class="mbd"><div class="bb"><div class="tp"><span></span><span></span><span></span></div></div></div>`;
  w.appendChild(d); scrollB();
}
function rmTyping(){document.getElementById('tp')?.remove()}

async function send(override){
  if(sending) return;
  const i = document.getElementById('ui');
  const text = (override !== undefined ? override : i.value).trim();
  if(!text && !attachments.length) return;
  sending = true;
  document.getElementById('sb').disabled = true;
  i.value = ''; autoResize();
  const files = attachments.slice();
  attachments = []; renderAtt();
  addMsg('user', text, files);
  addTyping();
  closeM();

  try {
    const r = await fetch('/api/chat', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({message:text, model:curModel, files:files})
    });
    const d = await r.json();
    rmTyping();
    if(d.reply){
      addMsg('bot', d.reply);
      if(voiceMode) speak(d.reply);
      if(d.remaining !== undefined) USER.remaining = d.remaining;
    } else {
      addMsg('bot', '⚠️ ' + (d.error || 'خطأ غير معروف'));
      if(d.limit_reached) setTimeout(()=>openOv('sub'), 1200);
    }
  } catch(e) {
    rmTyping(); addMsg('bot', '🌐 تعذّر الاتصال بالسيرفر');
  } finally {
    sending = false;
    document.getElementById('sb').disabled = false;
  }
}
function qa(q){send(q)}

const ui = document.getElementById('ui');
function autoResize(){ui.style.height='auto';ui.style.height=Math.min(ui.scrollHeight,200)+'px'}
ui.addEventListener('input', autoResize);
ui.addEventListener('keydown', e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}});

// FILES
function onFiles(e){
  const fl = e.target.files;
  for(const f of fl){
    const reader = new FileReader();
    reader.onload = ev => {
      attachments.push({name:f.name, type:f.type, data:ev.target.result, size:f.size});
      renderAtt();
    };
    reader.readAsDataURL(f);
  }
  e.target.value = '';
}
function renderAtt(){
  const box = document.getElementById('attPrev');
  box.innerHTML = attachments.map((f,i)=>{
    if(f.type.startsWith('image/')) return `<div class="att"><img src="${f.data}"><button class="rm" onclick="rmAtt(${i})">✕</button></div>`;
    return `<div class="att"><div class="ft">📎 ${esc((f.name||'').slice(0,20))}</div><button class="rm" onclick="rmAtt(${i})">✕</button></div>`;
  }).join('');
}
function rmAtt(i){attachments.splice(i,1);renderAtt()}

// VOICE
let rec = null;
let voiceActive = false;
if('webkitSpeechRecognition' in window || 'SpeechRecognition' in window){
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  rec = new SR();
  rec.continuous = false; rec.interimResults = true; rec.lang = 'ar-SA';
  rec.onstart = () => {
    voiceActive = true;
    document.getElementById('vb').classList.add('rec');
    document.getElementById('voiceBar').classList.add('show');
    document.getElementById('voiceTxt').textContent = '🎤 جاري الاستماع...';
  };
  rec.onresult = e => {
    let finalT = '', interimT = '';
    for(let i = e.resultIndex; i < e.results.length; i++){
      const tr = e.results[i][0].transcript;
      if(e.results[i].isFinal) finalT += tr;
      else interimT += tr;
    }
    const shown = (finalT || interimT).trim();
    document.getElementById('voiceTxt').textContent = '🎤 ' + shown;
    if(finalT){
      rec.stop();
      voiceMode = true;
      ui.value = finalT.trim();
      autoResize();
      setTimeout(()=>{ send(); }, 400);
    }
  };
  rec.onerror = (ev) => {
    voiceActive = false;
    document.getElementById('vb').classList.remove('rec');
    document.getElementById('voiceBar').classList.remove('show');
    tt('⚠️ خطأ صوت: ' + (ev.error || ''));
  };
  rec.onend = () => {
    voiceActive = false;
    document.getElementById('vb').classList.remove('rec');
    document.getElementById('voiceBar').classList.remove('show');
  };
  document.getElementById('vb').onclick = () => {
    if(voiceActive){ rec.stop(); }
    else { try{ rec.start(); }catch(e){ tt('⚠️ تعذّر بدء الاستماع'); } }
  };
} else {
  document.getElementById('vb').onclick = () => tt('⚠️ غير مدعوم');
  document.getElementById('vb').style.opacity = '.5';
}
function stopVoice(){
  voiceActive = false;
  voiceMode = false;
  if(rec) try{ rec.stop(); }catch(e){}
  if(window.speechSynthesis) window.speechSynthesis.cancel();
  document.getElementById('vb').classList.remove('rec');
  document.getElementById('voiceBar').classList.remove('show');
}
function speak(txt){
  if(!('speechSynthesis' in window)) return;
  window.speechSynthesis.cancel();
  const clean = txt.replace(/[`*_#>\[\]()]/g,'').slice(0,3000);
  const u = new SpeechSynthesisUtterance(clean);
  u.lang = 'ar-SA';
  const voices = window.speechSynthesis.getVoices();
  const arVoices = voices.filter(v => v.lang && v.lang.startsWith('ar'));
  if(voiceGender === 'female'){
    const f = arVoices.find(v => /female|hoda|salma|zariyah|amina|لطيفة|هدى/i.test(v.name)) || arVoices[0];
    if(f) u.voice = f;
    u.pitch = 1.15; u.rate = 1.0;
  } else {
    const m = arVoices.find(v => /male|maged|naayf|tarik|شادي|ماجد/i.test(v.name)) || arVoices[arVoices.length-1];
    if(m) u.voice = m;
    u.pitch = 0.85; u.rate = 0.98;
  }
  window.speechSynthesis.speak(u);
}

// CHAT ACTIONS
function newChat(){
  if(chatMsgs.length && !confirm('بدء محادثة جديدة؟')) return;
  document.getElementById('msgs').innerHTML = '';
  document.getElementById('wl').style.display = '';
  chatMsgs = [];
  closeM();
}
async function saveCur(){
  if(!chatMsgs.length) return tt('⚠️ لا توجد رسائل');
  const t = prompt('📌 اسم المحادثة:', 'محادثة ' + new Date().toLocaleDateString('ar-EG'));
  if(!t) return;
  try {
    const r = await fetch('/api/save_chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({title:t, messages:chatMsgs})});
    const d = await r.json();
    if(d.success){tt('💾 تم الحفظ'); loadRec();}
    else tt('❌ فشل');
  } catch(e){tt('❌ فشل')}
}
async function loadRec(){
  try{
    const r = await fetch('/api/get_chats');
    const d = await r.json();
    const box = document.getElementById('rc');
    const lb = document.getElementById('rlb');
    if(!d.chats || !d.chats.length){box.innerHTML='';lb.style.display='none';return}
    lb.style.display = 'block';
    box.innerHTML = d.chats.slice(0,12).map(c=>`
      <div class="cm" onclick='loadChat(${JSON.stringify(c).replace(/'/g,"&#39;")})'>
        <span style="font-size:.85rem">💬</span>
        <span class="cmt">${esc(c.title)}</span>
        <button class="cmd" onclick="event.stopPropagation(); delChat(${c.id})">🗑️</button>
      </div>`).join('');
  }catch(e){}
}
function openSaved(){openOv('svd'); renderSvd()}
async function renderSvd(){
  const box = document.getElementById('svdL');
  box.innerHTML = '<p style="color:#9a9aae;text-align:center;padding:20px">جاري...</p>';
  try{
    const r = await fetch('/api/get_chats');
    const d = await r.json();
    if(!d.chats || !d.chats.length){box.innerHTML='<p style="color:#9a9aae;text-align:center;padding:20px">لا توجد محادثات</p>';return}
    box.innerHTML = d.chats.map(c=>`
      <div class="sr">
        <div class="sri" onclick='loadChatFrom(${JSON.stringify(c).replace(/'/g,"&#39;")})' style="cursor:pointer">
          <div class="srd">💬 ${esc(c.title)}</div>
          <div class="srm">📅 ${new Date(c.created_at).toLocaleString('ar-EG')}</div>
        </div>
        <button class="bs" onclick="delChat(${c.id}); renderSvd()">🗑️</button>
      </div>`).join('');
  }catch(e){box.innerHTML='<p style="color:#ef4444;text-align:center;padding:20px">فشل</p>'}
}
function loadChat(c){
  if(chatMsgs.length && !confirm('استبدال الحالية؟')) return;
  document.getElementById('msgs').innerHTML = '';
  document.getElementById('wl').style.display = 'none';
  chatMsgs = [];
  const m = JSON.parse(c.messages);
  m.forEach(x => addMsg(x.role, x.text, x.files));
  closeM(); tt('📂 تم التحميل');
}
function loadChatFrom(c){cl('svd'); loadChat(c)}
async function delChat(id){
  if(!confirm('حذف؟')) return;
  await fetch('/api/delete_chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  loadRec();
  if(document.getElementById('svd').classList.contains('show')) renderSvd();
}

// OVERLAYS
function openOv(id){document.getElementById(id).classList.add('show'); closeM()}
function cl(id){document.getElementById(id).classList.remove('show')}
function openSub(){openOv('sub')}
function subs(p){window.open('https://t.me/Yb_xY','_blank')}
function openSupport(){window.open('https://t.me/Yb_xY','_blank')}

function comingSoon(tab){
  const T = {
    upd:{t:'🚀 تحديثات قادمة', i:[['🎨','واجهة محسّنة','تصميم جديد كامل'],['⚡','استجابة أسرع','تحسين السرعة 60%'],['🌍','لغات إضافية','دعم 20 لغة'],['🎯','دقة أعلى','نموذج محسّن']]},
    mon:{t:'📊 مراقبة مشروعك', i:[['📈','تتبع الأداء','راقب مشروعك لحظة بلحظة'],['🔔','تنبيهات ذكية','عند أي تغيير مهم'],['📉','تقارير يومية','إحصائيات كاملة']]},
    sec:{t:'🛡️ الأمن السيبراني', i:[['🔍','فحص الثغرات','تحليل عميق'],['🔐','تشفير متقدم','حماية بياناتك'],['🕵️','مراقبة التهديدات','رصد فوري']]},
    edu:{t:'📚 دراسة وتعليم', i:[['📖','مناهج كاملة','لكل المستويات'],['✏️','تمارين تفاعلية','تعلّم ممتع'],['🎓','شهادات','إتمام الدورات']]},
    dsn:{t:'🎨 مؤسسات والتصميم', i:[['🎨','تصميم جرافيك','احترافي'],['🏢','حلول للمؤسسات','خطط مخصصة'],['💼','إدارة الفرق','تعاون سلس']]},
  };
  const d = T[tab]; if(!d) return;
  document.getElementById('csT').textContent = d.t;
  document.getElementById('csB').innerHTML = d.i.map(x=>`
    <div class="ft"><div class="fti">${x[0]}</div><div><div class="ftt">${x[1]}</div><div class="ftd">${x[2]}</div></div></div>
  `).join('') + '<p style="text-align:center;color:#9a9aae;font-size:.85rem;margin-top:16px">تابع @Yb_xY</p>';
  openOv('cs');
}

function openAcc(){openOv('acc'); loadSess(); setVoice(voiceGender)}
async function loadSess(){
  const box = document.getElementById('sessList');
  box.innerHTML = '<p style="color:#9a9aae;padding:10px;text-align:center">جاري...</p>';
  try{
    const r = await fetch('/api/sessions');
    const d = await r.json();
    document.getElementById('accInfo').textContent = `الاشتراك: ${USER.sub} • المتبقي: ${USER.remaining}`;
    if(!d.sessions || !d.sessions.length){box.innerHTML='<p style="color:#9a9aae;padding:10px;text-align:center">لا جلسات</p>';return}
    box.innerHTML = d.sessions.map(s=>`
      <div class="sr">
        <div class="sri">
          <div class="srd">📱 ${esc(s.device||'')} ${s.is_current?'<span class="scc">• الحالية</span>':''}</div>
          <div class="srm">🕐 ${s.last_seen?new Date(s.last_seen).toLocaleString('ar-EG'):'—'}</div>
          <div class="srm">🌐 ${esc(s.ip||'—')}</div>
        </div>
        ${s.is_current?'':`<button class="bs" onclick="killS('${s.token}')">طرد</button>`}
      </div>`).join('');
  }catch(e){box.innerHTML='<p style="color:#ef4444;padding:10px;text-align:center">فشل</p>'}
}
async function killS(token){
  if(!confirm('طرد؟')) return;
  await fetch('/api/kill_session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})});
  tt('✓'); loadSess();
}
async function logout(){
  if(!confirm('خروج؟')) return;
  await fetch('/api/logout',{method:'POST'});
  location.href = '/login';
}
let tmp;
function tt(m){const t=document.getElementById('to');t.textContent=m;t.classList.add('show');clearTimeout(tmp);tmp=setTimeout(()=>t.classList.remove('show'),2400)}

window.addEventListener('DOMContentLoaded', () => {
  buildSplash(); buildMD(); updateMUI(); loadRec(); autoResize();
  setVoice(voiceGender);
  setTimeout(()=>ui.focus(), 300);
});
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# HTML: ADMIN
# ═══════════════════════════════════════════════════════════════

ADMIN_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>لوحة التحكم — SOST AI</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@300;400;600;700;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Cairo',sans-serif}
body{background:#0a0a0f;color:#f5f5f7;min-height:100vh}
.wrap{max-width:1400px;margin:0 auto;padding:20px}
header{background:linear-gradient(135deg,#e11d48,#7c3aed);padding:20px 30px;border-radius:20px;margin-bottom:24px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
h1{font-size:1.5rem;font-weight:900}
.btn{padding:10px 20px;border-radius:12px;border:none;background:rgba(255,255,255,.15);color:#fff;font-weight:700;cursor:pointer;font-family:inherit}
.btn:hover{background:rgba(255,255,255,.25)}
.btn.danger{background:rgba(239,68,68,.3)}
.sg{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:16px;margin-bottom:24px}
.sc{background:rgba(15,15,24,.9);border:1px solid rgba(225,29,72,.2);border-radius:18px;padding:22px}
.sc .ic{font-size:2rem;margin-bottom:10px}
.sc .v{font-size:2rem;font-weight:900;background:linear-gradient(135deg,#e11d48,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sc .l{color:#9a9aae;font-size:.85rem;margin-top:4px}
.tabs{display:flex;gap:8px;margin-bottom:20px;flex-wrap:wrap}
.tab{padding:12px 22px;border-radius:12px;border:1px solid rgba(225,29,72,.2);background:rgba(15,15,24,.9);color:#9a9aae;font-weight:700;cursor:pointer;font-family:inherit;font-size:.9rem}
.tab.act{background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;border-color:transparent}
.pnl{background:rgba(15,15,24,.9);border:1px solid rgba(225,29,72,.2);border-radius:20px;padding:24px}
.pnl h2{margin-bottom:20px;font-size:1.3rem}
.tw{overflow-x:auto;border-radius:14px;border:1px solid rgba(225,29,72,.15)}
table{width:100%;border-collapse:collapse;font-size:.85rem}
th,td{padding:12px;text-align:right;border-bottom:1px solid rgba(225,29,72,.1)}
th{background:rgba(225,29,72,.15);font-weight:700}
tr:hover td{background:rgba(225,29,72,.05)}
.bd{padding:4px 10px;border-radius:8px;font-size:.72rem;font-weight:700}
.bd.admin{background:rgba(244,114,182,.2);color:#f472b6}
.bd.user{background:rgba(6,182,212,.2);color:#06b6d4}
.bd.banned{background:rgba(239,68,68,.2);color:#fca5a5}
.bd.active{background:rgba(16,185,129,.2);color:#34d399}
.bd.free{background:rgba(156,163,175,.2);color:#9ca3af}
.bd.weekly{background:rgba(245,158,11,.2);color:#fbbf24}
.bd.monthly{background:rgba(16,185,129,.2);color:#34d399}
.bd.yearly{background:rgba(139,92,246,.2);color:#a78bfa}
.bd.unlimited{background:rgba(244,114,182,.2);color:#f472b6}
.ab{padding:6px 12px;border-radius:8px;border:none;cursor:pointer;font-family:inherit;font-size:.75rem;font-weight:700;margin:2px}
.ab.ban{background:rgba(239,68,68,.2);color:#fca5a5}
.ab.unban{background:rgba(16,185,129,.2);color:#34d399}
.ab.sub{background:rgba(225,29,72,.2);color:#fb7185}
.ab.del{background:rgba(107,114,128,.2);color:#9ca3af}
.fi{display:flex;gap:10px;margin-bottom:16px;flex-wrap:wrap}
.fi input,.fi select{padding:12px 16px;border-radius:12px;background:rgba(255,255,255,.04);border:1px solid rgba(225,29,72,.2);color:#fff;font-family:inherit;font-size:.9rem;outline:none;flex:1;min-width:150px}
.empty{text-align:center;padding:40px;color:#9a9aae}
.tk{background:rgba(255,255,255,.03);border:1px solid rgba(225,29,72,.15);border-radius:14px;padding:18px;margin-bottom:14px}
.tkh{display:flex;justify-content:space-between;margin-bottom:12px;gap:10px;flex-wrap:wrap}
.tks{font-weight:700;font-size:1rem}
.tkm{font-size:.78rem;color:#9a9aae}
.tkb{color:#c5c5d5;line-height:1.7;margin:10px 0;padding:12px;background:rgba(0,0,0,.2);border-radius:10px;font-size:.9rem}
.tkr{background:rgba(16,185,129,.1);border-right:3px solid #10b981;padding:12px;border-radius:0 10px 10px 0;margin-top:10px;font-size:.9rem}
.rf{display:flex;gap:8px;margin-top:12px}
.rf input{flex:1;padding:12px;border-radius:12px;background:rgba(255,255,255,.04);border:1px solid rgba(225,29,72,.2);color:#fff;font-family:inherit;outline:none}
.cl{background:rgba(0,0,0,.2);border-radius:12px;padding:14px;margin-bottom:12px;font-size:.85rem;border-right:3px solid #e11d48}
.cl .u{color:#60a5fa;font-weight:700;margin-bottom:6px}
.cl .b{color:#9a9aae;line-height:1.6}
.cl .m{font-size:.72rem;color:#6a6a80;margin-top:8px}
.kc{font-family:monospace;font-size:.78rem;background:rgba(225,29,72,.15);padding:3px 8px;border-radius:6px;color:#fb7185;direction:ltr;display:inline-block}
.md{position:fixed;inset:0;background:rgba(0,0,0,.7);backdrop-filter:blur(10px);z-index:1000;display:none;align-items:center;justify-content:center;padding:20px}
.md.show{display:flex}
.mc{background:#0f0f18;border:1px solid rgba(225,29,72,.3);border-radius:20px;padding:28px;max-width:500px;width:100%}
.mc h3{margin-bottom:16px}
.mc input,.mc select{width:100%;padding:12px;border-radius:12px;background:rgba(255,255,255,.04);border:1px solid rgba(225,29,72,.2);color:#fff;font-family:inherit;margin-bottom:12px;outline:none}
.mb{display:flex;gap:10px;margin-top:16px}
.mb button{flex:1;padding:12px;border-radius:12px;border:none;font-family:inherit;font-weight:700;cursor:pointer}
.mb .cancel{background:rgba(107,114,128,.3);color:#fff}
.mb .confirm{background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff}
@media(max-width:768px){header{flex-direction:column;text-align:center}.sg{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>👑 لوحة تحكم SOST AI</h1>
    <div style="display:flex;gap:10px;flex-wrap:wrap">
      <button class="btn" onclick="refresh()">🔄 تحديث</button>
      <button class="btn danger" onclick="logout()">🚪 خروج</button>
    </div>
  </header>
  <div class="sg">
    <div class="sc"><div class="ic">👥</div><div class="v" id="s1">-</div><div class="l">المستخدمين</div></div>
    <div class="sc"><div class="ic">💬</div><div class="v" id="s2">-</div><div class="l">المحادثات</div></div>
    <div class="sc"><div class="ic">🔑</div><div class="v" id="s3">-</div><div class="l">مفاتيح API</div></div>
    <div class="sc"><div class="ic">💎</div><div class="v" id="s4">-</div><div class="l">المشتركين</div></div>
    <div class="sc"><div class="ic">🚫</div><div class="v" id="s5">-</div><div class="l">المحظورين</div></div>
    <div class="sc"><div class="ic">🎫</div><div class="v" id="s6">-</div><div class="l">تذاكر</div></div>
    <div class="sc"><div class="ic">📱</div><div class="v" id="s7">-</div><div class="l">جلسات</div></div>
    <div class="sc"><div class="ic">📊</div><div class="v" id="s8">-</div><div class="l">API Calls</div></div>
  </div>
  <div class="tabs">
    <button class="tab act" onclick="sw('users',this)">👥 المستخدمين</button>
    <button class="tab" onclick="sw('keys',this)">🔑 API</button>
    <button class="tab" onclick="sw('chats',this)">💬 محادثات</button>
    <button class="tab" onclick="sw('tickets',this)">🎫 دعم</button>
    <button class="tab" onclick="sw('subs',this)">💎 اشتراكات</button>
    <button class="tab" onclick="sw('sessions',this)">📱 جلسات</button>
    <button class="tab" onclick="sw('apilogs',this)">📊 API Logs</button>
  </div>
  <div id="p-users" class="pnl">
    <h2>👥 المستخدمين</h2>
    <div class="fi">
      <input type="text" id="fus" placeholder="🔍 بحث..." oninput="rU()">
      <select id="ffu" onchange="rU()">
        <option value="all">الكل</option><option value="free">مجاني</option>
        <option value="paid">مشتركين</option><option value="banned">محظورين</option>
      </select>
    </div>
    <div class="tw"><table><thead><tr><th>#</th><th>المستخدم</th><th>الدور</th><th>الاشتراك</th><th>الرسائل</th><th>الحالة</th><th>إجراءات</th></tr></thead><tbody id="tu"></tbody></table></div>
  </div>
  <div id="p-keys" class="pnl" style="display:none">
    <h2>🔑 API Keys</h2>
    <div class="fi">
      <input type="text" id="fks" placeholder="🔍 بحث..." oninput="rK()">
      <select id="ffk" onchange="rK()"><option value="all">الكل</option><option value="active">نشطة</option><option value="banned">محظورة</option></select>
    </div>
    <div class="tw"><table><thead><tr><th>#</th><th>المستخدم</th><th>المفتاح</th><th>الاسم</th><th>الاستخدام</th><th>الحالة</th><th>إجراءات</th></tr></thead><tbody id="tk"></tbody></table></div>
  </div>
  <div id="p-chats" class="pnl" style="display:none"><h2>💬 المحادثات</h2><div id="lch"></div></div>
  <div id="p-tickets" class="pnl" style="display:none"><h2>🎫 التذاكر</h2><div id="ltk"></div></div>
  <div id="p-subs" class="pnl" style="display:none"><h2>💎 الاشتراكات</h2>
    <div class="tw"><table><thead><tr><th>#</th><th>المستخدم</th><th>الخطة</th><th>السعر</th><th>البداية</th><th>الانتهاء</th><th>الحالة</th></tr></thead><tbody id="tsu"></tbody></table></div>
  </div>
  <div id="p-sessions" class="pnl" style="display:none"><h2>📱 الجلسات</h2>
    <div class="tw"><table><thead><tr><th>#</th><th>المستخدم</th><th>الجهاز</th><th>IP</th><th>آخر نشاط</th><th>إجراء</th></tr></thead><tbody id="tse"></tbody></table></div>
  </div>
  <div id="p-apilogs" class="pnl" style="display:none"><h2>📊 API Logs</h2><div id="lap"></div></div>
</div>

<div class="md" id="sm">
  <div class="mc">
    <h3>💎 تعديل اشتراك</h3>
    <input type="hidden" id="si">
    <input type="text" id="su" disabled>
    <select id="st">
      <option value="free">🆓 مجاني</option><option value="weekly">⚡ أسبوعي</option>
      <option value="monthly">🌙 شهري</option><option value="yearly">👑 سنوي</option>
      <option value="unlimited">♾️ غير محدود</option>
    </select>
    <input type="number" id="sd" placeholder="أيام" min="1" value="30">
    <div class="mb"><button class="cancel" onclick="cm('sm')">إلغاء</button><button class="confirm" onclick="saveS()">حفظ</button></div>
  </div>
</div>

<script>
let U=[],K=[],CH=[],TK=[],SU=[],SE=[],AL=[];
async function api(u,o){return (await fetch(u,o)).json()}
function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML}

async function loadS(){
  const d = await api('/admin/api/stats');
  document.getElementById('s1').textContent = d.total_users||0;
  document.getElementById('s2').textContent = d.total_chats||0;
  document.getElementById('s3').textContent = d.total_keys||0;
  document.getElementById('s4').textContent = d.paid_users||0;
  document.getElementById('s5').textContent = d.banned_users||0;
  document.getElementById('s6').textContent = d.open_tickets||0;
  document.getElementById('s7').textContent = d.active_sessions||0;
  document.getElementById('s8').textContent = d.api_calls||0;
}
async function loadU(){U=await api('/admin/api/users');rU()}
function rU(){
  const s = document.getElementById('fus').value.toLowerCase();
  const f = document.getElementById('ffu').value;
  const tb = document.getElementById('tu');
  let list = (U||[]).filter(u=>{
    if(s && !(u.username||'').toLowerCase().includes(s)) return false;
    if(f==='free' && u.subscription_type!=='free') return false;
    if(f==='paid' && u.subscription_type==='free') return false;
    if(f==='banned' && !u.banned) return false;
    return true;
  });
  if(!list.length){tb.innerHTML='<tr><td colspan="7" class="empty">لا يوجد</td></tr>';return}
  tb.innerHTML = list.map(u=>`<tr>
    <td>${u.id}</td>
    <td><strong>${esc(u.username)}</strong><br><small style="color:#9a9aae">${esc(u.email||'—')}</small></td>
    <td><span class="bd ${u.role}">${u.role==='admin'?'👑':'👤'}</span></td>
    <td><span class="bd ${u.subscription_type}">${u.subscription_type}</span></td>
    <td>${u.messages_used||0}</td>
    <td>${u.banned?'<span class="bd banned">🚫</span>':'✓'}</td>
    <td>${u.banned?`<button class="ab unban" onclick="unb(${u.id})">فك</button>`:`<button class="ab ban" onclick="bn(${u.id})">حظر</button>`}<button class="ab sub" onclick="openSM(${u.id},'${esc(u.username)}','${u.subscription_type}')">💎</button>${u.role!=='admin'?`<button class="ab del" onclick="dU(${u.id})">🗑️</button>`:''}</td>
  </tr>`).join('');
}
async function bn(id){if(!confirm('حظر؟'))return;await api('/admin/api/ban',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});refresh()}
async function unb(id){await api('/admin/api/unban',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});refresh()}
async function dU(id){if(!confirm('حذف؟'))return;await api('/admin/api/delete_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});refresh()}
function openSM(id,n,s){document.getElementById('si').value=id;document.getElementById('su').value=n;document.getElementById('st').value=s;document.getElementById('sm').classList.add('show')}
function cm(id){document.getElementById(id).classList.remove('show')}
async function saveS(){await api('/admin/api/set_subscription',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id:document.getElementById('si').value,type:document.getElementById('st').value,days:document.getElementById('sd').value})});cm('sm');refresh()}

async function loadK(){K=await api('/admin/api/keys');rK()}
function rK(){
  const s = document.getElementById('fks').value.toLowerCase();
  const f = document.getElementById('ffk').value;
  const tb = document.getElementById('tk');
  let list = (K||[]).filter(k=>{
    const t = ((k.key_name||'')+' '+(k.key_value||'')+' '+(k.username||'')+' '+(k.service_name||'')).toLowerCase();
    if(s && !t.includes(s)) return false;
    if(f==='active' && (k.banned || !k.active)) return false;
    if(f==='banned' && !k.banned) return false;
    return true;
  });
  if(!list.length){tb.innerHTML='<tr><td colspan="7" class="empty">لا يوجد</td></tr>';return}
  tb.innerHTML = list.map(k=>`<tr>
    <td>${k.id}</td><td>${esc(k.username||'—')}</td>
    <td><span class="kc">${esc(k.key_value)}</span></td>
    <td>${esc(k.key_name)}</td><td>${k.messages_used}/${k.messages_limit}</td>
    <td>${k.banned?'<span class="bd banned">🚫</span>':(k.active?'<span class="bd active">✓</span>':'<span class="bd free">⏸️</span>')}</td>
    <td>${k.banned?`<button class="ab unban" onclick="unbK(${k.id})">فك</button>`:`<button class="ab ban" onclick="bnK(${k.id})">حظر</button>`}<button class="ab del" onclick="dK(${k.id})">🗑️</button></td>
  </tr>`).join('');
}
async function bnK(id){await api('/admin/api/ban_key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});loadK()}
async function unbK(id){await api('/admin/api/unban_key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});loadK()}
async function dK(id){if(!confirm('حذف؟'))return;await api('/admin/api/delete_key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});loadK()}

async function loadCH(){CH=await api('/admin/api/chats');const l=document.getElementById('lch');if(!CH||!CH.length){l.innerHTML='<div class="empty">لا يوجد</div>';return}l.innerHTML=CH.slice(0,100).map(c=>`<div class="cl"><div class="u">👤 ${esc(c.username)}: ${esc(c.user_message)}</div><div class="b">✨ ${esc((c.bot_message||'').slice(0,300))}...</div><div class="m">🕐 ${new Date(c.created_at).toLocaleString('ar-EG')} • ${c.model||'wormgpt'}</div></div>`).join('')}
async function loadTK(){TK=await api('/admin/api/tickets');const l=document.getElementById('ltk');if(!TK||!TK.length){l.innerHTML='<div class="empty">لا يوجد</div>';return}l.innerHTML=TK.map(t=>`<div class="tk"><div class="tkh"><div><div class="tks">📝 ${esc(t.subject)}</div><div class="tkm">👤 ${esc(t.username)} • ${new Date(t.created_at).toLocaleString('ar-EG')}</div></div><span class="bd ${t.status==='open'?'banned':'monthly'}">${t.status==='open'?'🔴':'✓'}</span></div><div class="tkb">${esc(t.message)}</div>${t.image_data?`<img src="${t.image_data}" style="max-width:100%;border-radius:12px;margin:10px 0">`:''}${t.reply?`<div class="tkr"><strong>✓:</strong> ${esc(t.reply)}</div>`:`<div class="rf"><input type="text" id="r_${t.id}" placeholder="رد..."><button class="ab sub" onclick="replyT(${t.id})">إرسال</button></div>`}</div>`).join('')}
async function replyT(id){const inp=document.getElementById('r_'+id);const r=inp.value.trim();if(!r){alert('اكتب رداً');return}await api('/admin/api/reply_ticket',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,reply:r})});loadTK()}
async function loadSU(){SU=await api('/admin/api/subscriptions');const tb=document.getElementById('tsu');if(!SU||!SU.length){tb.innerHTML='<tr><td colspan="7" class="empty">لا يوجد</td></tr>';return}tb.innerHTML=SU.map(s=>`<tr><td>${s.id}</td><td>${esc(s.username||'—')}</td><td>${s.plan}</td><td>$${s.price}</td><td>${new Date(s.started_at).toLocaleDateString('ar-EG')}</td><td>${new Date(s.expires_at).toLocaleDateString('ar-EG')}</td><td>${s.status==='active'?'✓':'✗'}</td></tr>`).join('')}
async function loadSE(){SE=await api('/admin/api/sessions');const tb=document.getElementById('tse');if(!SE||!SE.length){tb.innerHTML='<tr><td colspan="6" class="empty">لا يوجد</td></tr>';return}tb.innerHTML=SE.map(s=>`<tr><td>${s.id}</td><td>${esc(s.username||'—')}</td><td>${esc(s.device||'—')}</td><td>${esc(s.ip||'—')}</td><td>${s.last_seen?new Date(s.last_seen).toLocaleString('ar-EG'):'—'}</td><td><button class="ab ban" onclick="killSA('${s.token}')">طرد</button></td></tr>`).join('')}
async function killSA(t){if(!confirm('طرد؟'))return;await api('/admin/api/kill_session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token:t})});loadSE()}
async function loadAL(){AL=await api('/admin/api/apilogs');const l=document.getElementById('lap');if(!AL||!AL.length){l.innerHTML='<div class="empty">لا يوجد</div>';return}l.innerHTML=AL.slice(0,100).map(a=>`<div class="cl"><div class="u">🔑 Key #${a.key_id} • ${esc(a.endpoint)} <span style="color:#34d399">${a.status_code}</span></div><div class="b">📤 ${esc((a.request_body||'').slice(0,200))}</div><div class="m">🕐 ${new Date(a.created_at).toLocaleString('ar-EG')} • IP: ${esc(a.ip||'—')}</div></div>`).join('')}

function sw(t,e){
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('act'));e.classList.add('act');
  ['users','keys','chats','tickets','subs','sessions','apilogs'].forEach(p=>{document.getElementById('p-'+p).style.display=p===t?'':'none'});
  if(t==='keys')loadK();if(t==='chats')loadCH();if(t==='tickets')loadTK();if(t==='subs')loadSU();if(t==='sessions')loadSE();if(t==='apilogs')loadAL();
}
async function logout(){if(!confirm('خروج؟'))return;await fetch('/admin/logout',{method:'POST'});location.href='/admin/login'}
function refresh(){loadS();loadU();const a=document.querySelector('.tab.act');if(a){const t=a.textContent;if(t.includes('API')){if(t.includes('Logs'))loadAL();else loadK();}else if(t.includes('محادثات'))loadCH();else if(t.includes('دعم'))loadTK();else if(t.includes('اشتراكات'))loadSU();else if(t.includes('جلسات'))loadSE();}}
window.addEventListener('DOMContentLoaded',()=>{refresh();setInterval(loadS,30000)});
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# HTML: ADMIN LOGIN
# ═══════════════════════════════════════════════════════════════

ADMIN_LOGIN_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>دخول الأدمن</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Cairo',sans-serif}
body{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0a0a0f}
.card{background:rgba(15,15,24,.9);border:1px solid rgba(225,29,72,.3);border-radius:24px;padding:40px;width:100%;max-width:400px}
h1{color:#fff;text-align:center;margin-bottom:24px;font-size:1.5rem}
h1 span{background:linear-gradient(135deg,#e11d48,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
input{width:100%;padding:14px;border-radius:14px;background:rgba(255,255,255,.04);border:1px solid rgba(225,29,72,.2);color:#fff;font-family:inherit;font-size:1rem;margin-bottom:16px;outline:none}
input:focus{border-color:#e11d48}
button{width:100%;padding:15px;border-radius:14px;border:none;background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;font-weight:700;font-size:1rem;cursor:pointer;font-family:inherit}
.err{color:#fca5a5;text-align:center;margin-bottom:14px;font-size:.9rem;display:none}
.err.show{display:block}
</style>
</head>
<body>
<div class="card">
  <h1>👑 لوحة تحكم <span>SOST</span></h1>
  <div class="err" id="e">❌ كلمة مرور خاطئة</div>
  <form onsubmit="event.preventDefault();go()">
    <input type="password" id="p" placeholder="🔒 كلمة مرور الأدمن" autofocus>
    <button type="submit">دخول 🚀</button>
  </form>
</div>
<script>
async function go(){const p=document.getElementById('p').value;const r=await fetch('/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:p})});const d=await r.json();if(d.success)location.href='/admin';else document.getElementById('e').classList.add('show')}
</script>
</body>
</html>"""


# ═══════════════════════════════════════════════════════════════
# Response
# ═══════════════════════════════════════════════════════════════

class Response:
    def __init__(self, status=200, body='', content_type='text/html; charset=utf-8', headers=None):
        if isinstance(body, str):
            body = body.encode('utf-8')
        self.status = status
        self.body = body
        self.content_type = content_type
        self.headers = headers or {}

    def add_cookie(self, name, value, max_age=None, http_only=True, path='/'):
        c = f'{name}={value}; Path={path}'
        if http_only:
            c += '; HttpOnly'
        c += '; SameSite=Lax'
        if max_age is not None:
            c += f'; Max-Age={max_age}'
        if 'Set-Cookie' in self.headers:
            self.headers['Set-Cookie'] += '\n' + c
        else:
            self.headers['Set-Cookie'] = c


def json_response(status, obj):
    return Response(status, json.dumps(obj, ensure_ascii=False), 'application/json; charset=utf-8')


def redirect(url):
    r = Response(302, '', 'text/html; charset=utf-8')
    r.headers['Location'] = url
    return r


def parse_cookies(h):
    r = {}
    if not h:
        return r
    try:
        c = SimpleCookie()
        c.load(h)
        for k, m in c.items():
            r[k] = m.value
    except Exception:
        pass
    return r


def get_user(env):
    try:
        return get_session_user(parse_cookies(env.get('HTTP_COOKIE', '')).get('sost_session'))
    except Exception:
        return None


def get_token(env):
    return parse_cookies(env.get('HTTP_COOKIE', '')).get('sost_session')


def read_json(env):
    try:
        n = int(env.get('CONTENT_LENGTH') or 0)
    except ValueError:
        n = 0
    if n <= 0 or n > 50 * 1024 * 1024:
        return {}
    try:
        return json.loads(env['wsgi.input'].read(n).decode('utf-8'))
    except Exception:
        return {}


def get_ip(env):
    return env.get('HTTP_X_FORWARDED_FOR', env.get('REMOTE_ADDR', '')).split(',')[0].strip()


def get_main_page(user):
    u = user['username'] if user else 'زائر'
    uid = user['id'] if user else 0
    st = user['subscription_type'] if user else 'free'
    mu = user['messages_used'] if user else 0
    pm = (user.get('preferred_model') or 'wormgpt') if user else 'wormgpt'
    rem = FREE_MESSAGE_LIMIT - mu if st == 'free' else '∞'
    labels = {'free':'مجاني','weekly':'أسبوعي','monthly':'شهري','yearly':'سنوي','unlimited':'غير محدود'}
    sl = labels.get(st, st)
    return (MAIN_PAGE
            .replace('{{USERNAME}}', u)
            .replace('{{USERNAME_INITIAL}}', (u[0].upper() if u else '?'))
            .replace('{{USER_ID}}', str(uid))
            .replace('{{SUB_TYPE}}', st)
            .replace('{{SUB_LABEL}}', sl)
            .replace('{{REMAINING}}', str(rem))
            .replace('{{PREFERRED_MODEL}}', pm)
            .replace('{{MODELS_JSON}}', json.dumps(MODELS, ensure_ascii=False))
            .replace('{{SPLASH_IMAGES_JSON}}', json.dumps(SPLASH_IMAGES, ensure_ascii=False)))


# ═══════════════════════════════════════════════════════════════
# Stats
# ═══════════════════════════════════════════════════════════════

def stats():
    try:
        return {
            'total_users': (db_query('SELECT COUNT(*) as c FROM users', one=True) or {}).get('c', 0),
            'total_chats': (db_query('SELECT COUNT(*) as c FROM chat_logs', one=True) or {}).get('c', 0),
            'total_keys': (db_query('SELECT COUNT(*) as c FROM api_keys', one=True) or {}).get('c', 0),
            'banned_users': (db_query('SELECT COUNT(*) as c FROM users WHERE banned=1', one=True) or {}).get('c', 0),
            'paid_users': (db_query('SELECT COUNT(*) as c FROM users WHERE subscription_type != ?', ('free',), one=True) or {}).get('c', 0),
            'open_tickets': (db_query('SELECT COUNT(*) as c FROM support_tickets WHERE status=?', ('open',), one=True) or {}).get('c', 0),
            'active_sessions': (db_query('SELECT COUNT(*) as c FROM sessions WHERE expires_at > ?', (datetime.now().isoformat(),), one=True) or {}).get('c', 0),
            'api_calls': (db_query('SELECT COUNT(*) as c FROM api_logs', one=True) or {}).get('c', 0),
        }
    except Exception:
        return {}


# ═══════════════════════════════════════════════════════════════
# GET
# ═══════════════════════════════════════════════════════════════

def handle_get(path, env):
    try:
        user = get_user(env)

        if path in ('/login', '/register'):
            if user and not user.get('banned'):
                return redirect('/')
            return Response(200, LOGIN_PAGE)

        if path in ('/', '/index.html'):
            if not user:
                return redirect('/login')
            if user.get('banned'):
                return Response(403, '<h1 style="color:#fff;text-align:center;padding:50px">🚫 محظور</h1>')
            return Response(200, get_main_page(user))

        if path == '/keys':
            if not user:
                return redirect('/login')
            if user.get('banned'):
                return Response(403, '<h1 style="color:#fff;text-align:center;padding:50px">🚫</h1>')
            return Response(200, API_KEYS_PAGE)

        if path == '/api/docs':
            return Response(200, API_DOCS_PAGE)

        if path == '/api/keys/list':
            if not user:
                return json_response(401, {'error': 'not_logged_in'})
            return json_response(200, {'keys': get_user_api_keys(user['id'])})

        if path == '/api/keys/daily':
            if not user:
                return json_response(401, {'error': 'not_logged_in'})
            used = _daily_count(user['id'])
            return json_response(200, {'used': used, 'limit': API_KEY_DAILY_CREATE_LIMIT, 'remaining': max(0, API_KEY_DAILY_CREATE_LIMIT - used)})

        if path == '/api/get_chats':
            if not user:
                return json_response(401, {'error': 'not_logged_in'})
            return json_response(200, {'chats': get_user_conversations(user['id'])})

        if path == '/api/sessions':
            if not user:
                return json_response(401, {'error': 'not_logged_in'})
            cur = get_token(env)
            ss = db_query('SELECT * FROM sessions WHERE user_id = ? AND expires_at > ? ORDER BY last_seen DESC',
                          (user['id'], datetime.now().isoformat())) or []
            for s in ss:
                s['is_current'] = (s['token'] == cur)
            return json_response(200, {'sessions': ss})

        if path == '/api/health':
            return json_response(200, {'ok': True, 'service': 'SOST AI', 'version': '11.0'})

        if path == '/favicon.ico':
            return Response(200,
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect width="24" height="24" rx="6" fill="#e11d48"/><path d="M12 4L14 10L20 12L14 14L12 20L10 14L4 12L10 10L12 4Z" fill="white"/></svg>',
                'image/svg+xml')

        if path == '/admin/login':
            return Response(200, ADMIN_LOGIN_PAGE)

        if path.startswith('/admin'):
            ck = parse_cookies(env.get('HTTP_COOKIE', ''))
            if ck.get('sost_admin') != hash_password(ADMIN_PASSWORD):
                return redirect('/admin/login')
            if path in ('/admin', '/admin/'):
                return Response(200, ADMIN_PAGE)
            if path == '/admin/api/stats':
                return json_response(200, stats())
            if path == '/admin/api/users':
                return json_response(200, db_query('SELECT * FROM users ORDER BY id DESC') or [])
            if path == '/admin/api/keys':
                return json_response(200, db_query('''SELECT k.*, u.username FROM api_keys k
                                                      LEFT JOIN users u ON k.user_id = u.id ORDER BY k.id DESC''') or [])
            if path == '/admin/api/chats':
                return json_response(200, db_query('SELECT * FROM chat_logs ORDER BY id DESC LIMIT 500') or [])
            if path == '/admin/api/tickets':
                return json_response(200, db_query('SELECT * FROM support_tickets ORDER BY id DESC') or [])
            if path == '/admin/api/subscriptions':
                return json_response(200, db_query('''SELECT s.*, u.username FROM subscriptions s
                                                      LEFT JOIN users u ON s.user_id = u.id ORDER BY s.id DESC''') or [])
            if path == '/admin/api/sessions':
                return json_response(200, db_query('''SELECT s.rowid as id, s.*, u.username FROM sessions s
                                                      LEFT JOIN users u ON s.user_id = u.id ORDER BY s.last_seen DESC LIMIT 200''') or [])
            if path == '/admin/api/apilogs':
                return json_response(200, db_query('SELECT * FROM api_logs ORDER BY id DESC LIMIT 300') or [])

        return Response(404, '<h1>404</h1>')
    except Exception as e:
        traceback.print_exc()
        return json_response(500, {'error': 'Server error', 'detail': str(e)})


# ═══════════════════════════════════════════════════════════════
# POST
# ═══════════════════════════════════════════════════════════════

def handle_post(path, env):
    try:
        if path == '/api/login':
            b = read_json(env)
            username = (b.get('username') or '').strip()
            password = b.get('password') or ''
            if not username or not password:
                return json_response(200, {'success': False, 'error': 'أدخل اسم المستخدم وكلمة المرور'})
            r = authenticate(username, password)
            if r is None:
                return json_response(200, {'success': False, 'error': 'اسم المستخدم أو كلمة المرور خاطئة'})
            if isinstance(r, dict) and r.get('banned'):
                return json_response(200, {'success': False, 'error': '🚫 حسابك محظور'})
            t = create_session(r['id'], get_ip(env), env.get('HTTP_USER_AGENT', ''))
            if not t:
                return json_response(200, {'success': False, 'error': 'فشل إنشاء الجلسة'})
            try:
                db_query('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now().isoformat(), r['id']))
            except Exception:
                pass
            resp = json_response(200, {'success': True})
            resp.add_cookie('sost_session', t, max_age=2592000)
            return resp

        if path == '/api/register':
            b = read_json(env)
            u = (b.get('username') or '').strip()
            p = b.get('password') or ''
            e = (b.get('email') or '').strip()
            if len(u) < 3:
                return json_response(200, {'success': False, 'error': 'اسم المستخدم قصير (3 أحرف على الأقل)'})
            if len(p) < 6:
                return json_response(200, {'success': False, 'error': 'كلمة المرور قصيرة (6 أحرف على الأقل)'})
            if not u.replace('_','').replace('-','').replace('.','').isalnum():
                return json_response(200, {'success': False, 'error': 'اسم المستخدم يحتوي على رموز غير مسموحة'})
            uid = create_user(u, p, e)
            if not uid:
                return json_response(200, {'success': False, 'error': 'اسم المستخدم موجود مسبقاً'})
            t = create_session(uid, get_ip(env), env.get('HTTP_USER_AGENT', ''))
            if not t:
                return json_response(200, {'success': False, 'error': 'فشل إنشاء الجلسة'})
            resp = json_response(200, {'success': True})
            resp.add_cookie('sost_session', t, max_age=2592000)
            return resp

        if path == '/api/logout':
            t = get_token(env)
            if t:
                db_query('DELETE FROM sessions WHERE token = ?', (t,))
            resp = json_response(200, {'success': True})
            resp.add_cookie('sost_session', '', max_age=0)
            return resp

        if path == '/api/set_model':
            u = get_user(env)
            if not u:
                return json_response(401, {'error': 'not_logged_in'})
            b = read_json(env)
            m = b.get('model', 'wormgpt')
            if m not in MODELS:
                m = 'wormgpt'
            db_query('UPDATE users SET preferred_model = ? WHERE id = ?', (m, u['id']))
            return json_response(200, {'success': True})

        if path == '/api/kill_session':
            u = get_user(env)
            if not u:
                return json_response(401, {'error': 'not_logged_in'})
            b = read_json(env)
            t = b.get('token')
            cur = get_token(env)
            if t and t != cur:
                db_query('DELETE FROM sessions WHERE token = ? AND user_id = ?', (t, u['id']))
            return json_response(200, {'success': True})

        if path == '/api/chat':
            u = get_user(env)
            if not u:
                return json_response(200, {'error': '🔒 سجل الدخول أولاً'})
            ok, reason = check_subscription(u)
            if not ok:
                if reason == 'banned':
                    return json_response(200, {'error': '🚫 حسابك محظور'})
                if reason in ('free_limit', 'expired'):
                    return json_response(200, {'error': '💎 انتهت رسائلك المجانية - اشترك الآن', 'limit_reached': True})
                return json_response(200, {'error': '❌ غير مصرح'})

            b = read_json(env)
            msg = (b.get('message') or '').strip()
            model = b.get('model') or 'wormgpt'
            if model not in MODELS:
                model = 'wormgpt'
            files = b.get('files', [])

            full_msg = msg
            for f in files:
                if f.get('type', '').startswith('text/') or f.get('name', '').endswith(('.txt', '.md', '.json', '.py', '.js', '.csv')):
                    data = f.get('data', '')
                    if data.startswith('data:'):
                        try:
                            _, enc = data.split(',', 1)
                            txt = base64.b64decode(enc).decode('utf-8', errors='ignore')
                            full_msg += f"\n\n=== ملف: {f.get('name','file')} ===\n{txt[:20000]}"
                        except Exception:
                            pass

            if not full_msg:
                return json_response(400, {'error': 'الرسالة فارغة'})
            if len(full_msg) > MAX_MESSAGE_LENGTH:
                full_msg = full_msg[:MAX_MESSAGE_LENGTH]

            reply, err = call_model(full_msg, model)
            if err:
                return json_response(200, {'error': err})
            increment_usage(u['id'])
            log_chat(u['id'], u['username'], msg[:500], reply, model)
            upd = db_query('SELECT messages_used, subscription_type FROM users WHERE id = ?', (u['id'],), one=True) or {}
            rem = '∞' if upd.get('subscription_type') != 'free' else max(0, FREE_MESSAGE_LIMIT - upd.get('messages_used', 0))
            return json_response(200, {'reply': reply, 'remaining': rem, 'model': model})

        if path == '/api/save_chat':
            u = get_user(env)
            if not u:
                return json_response(200, {'success': False})
            b = read_json(env)
            save_conversation(u['id'], b.get('title', 'محادثة'), b.get('messages', []))
            return json_response(200, {'success': True})

        if path == '/api/delete_chat':
            u = get_user(env)
            if not u:
                return json_response(200, {'success': False})
            b = read_json(env)
            db_query('DELETE FROM conversations WHERE id = ? AND user_id = ?', (b.get('id'), u['id']))
            return json_response(200, {'success': True})

        if path == '/api/support':
            u = get_user(env)
            if not u:
                return json_response(200, {'success': False})
            b = read_json(env)
            db_query('''INSERT INTO support_tickets (user_id, username, subject, message, image_data, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (u['id'], u['username'], b.get('subject'), b.get('message'), b.get('image'), datetime.now().isoformat()))
            return json_response(200, {'success': True})

        if path == '/api/keys/create':
            u = get_user(env)
            if not u:
                return json_response(401, {'error': 'not_logged_in'})
            b = read_json(env)
            kn = (b.get('key_name') or '').strip()[:50]
            sv = (b.get('service_name') or '').strip()[:50]
            if not kn or not sv:
                return json_response(200, {'success': False, 'error': 'الاسم والخدمة مطلوبان'})
            k, r = create_api_key(u['id'], kn, sv)
            if not k:
                return json_response(200, {'success': False, 'error': r})
            return json_response(200, {'success': True, 'key': k, 'id': r})

        if path == '/api/keys/delete':
            u = get_user(env)
            if not u:
                return json_response(401, {'error': 'not_logged_in'})
            delete_api_key(read_json(env).get('id'), u['id'])
            return json_response(200, {'success': True})

        if path == '/api/keys/toggle':
            u = get_user(env)
            if not u:
                return json_response(401, {'error': 'not_logged_in'})
            toggle_api_key(read_json(env).get('id'), u['id'])
            return json_response(200, {'success': True})

        if path in ('/v1/chat/completions', '/api/v1/chat'):
            auth = env.get('HTTP_AUTHORIZATION', '')
            kv = None
            if auth.startswith('Bearer '):
                kv = auth[7:].strip()
            elif auth.startswith('SOST-'):
                kv = auth.strip()
            if not kv:
                return json_response(401, {'success': False, 'error': 'missing_api_key'})
            val, err = validate_api_key(kv)
            if err:
                msgs = {'invalid_key':'غير صالح','key_disabled':'ملغى','key_expired':'منتهي',
                        'key_limit_reached':'تجاوز الحد','key_banned':'محظور',
                        'user_banned':'المستخدم محظور','user_not_found':'مفقود','missing_key':'مفقود',
                        'internal_error':'خطأ داخلي'}
                st = 401 if err in ('invalid_key','missing_key') else 403
                if err == 'key_limit_reached':
                    st = 429
                return json_response(st, {'success': False, 'error': err, 'message': msgs.get(err, err)})
            k = val['key']
            au = val['user']
            b = read_json(env)
            msg = (b.get('message') or b.get('prompt') or '').strip()
            model = b.get('model') or 'wormgpt'
            if model not in MODELS:
                model = 'wormgpt'
            if not msg:
                return json_response(400, {'success': False, 'error': 'empty_message'})
            if len(msg) > MAX_MESSAGE_LENGTH:
                msg = msg[:MAX_MESSAGE_LENGTH]
            reply, error = call_model(msg, model)
            if error:
                log_api_request(k['id'], au['id'], path,
                                json.dumps({'message': msg[:200]}, ensure_ascii=False),
                                json.dumps({'error': error}, ensure_ascii=False),
                                500, get_ip(env))
                return json_response(500, {'success': False, 'error': 'engine_error', 'message': error})
            use_api_key(k['id'])
            log_chat(au['id'], f"[API:{k['key_name']}]", msg, reply, model)
            log_api_request(k['id'], au['id'], path,
                            json.dumps({'message': msg[:200], 'model': model}, ensure_ascii=False),
                            json.dumps({'reply': reply[:200]}, ensure_ascii=False),
                            200, get_ip(env))
            upd = db_query('SELECT messages_used, messages_limit FROM api_keys WHERE id = ?', (k['id'],), one=True) or {}
            return json_response(200, {
                'success': True, 'reply': reply, 'model': model,
                'usage': {
                    'used': upd.get('messages_used', 0),
                    'limit': upd.get('messages_limit', 0),
                    'remaining': upd.get('messages_limit', 0) - upd.get('messages_used', 0),
                }
            })

        if path == '/admin/login':
            b = read_json(env)
            if b.get('password') == ADMIN_PASSWORD:
                resp = json_response(200, {'success': True})
                resp.add_cookie('sost_admin', hash_password(ADMIN_PASSWORD), max_age=86400)
                return resp
            return json_response(200, {'success': False})

        if path == '/admin/logout':
            resp = json_response(200, {'success': True})
            resp.add_cookie('sost_admin', '', max_age=0)
            return resp

        if path.startswith('/admin/api/'):
            if parse_cookies(env.get('HTTP_COOKIE', '')).get('sost_admin') != hash_password(ADMIN_PASSWORD):
                return json_response(401, {'error': 'unauthorized'})

            if path == '/admin/api/ban':
                db_query('UPDATE users SET banned = 1 WHERE id = ?', (read_json(env).get('id'),))
                return json_response(200, {'success': True})
            if path == '/admin/api/unban':
                db_query('UPDATE users SET banned = 0 WHERE id = ?', (read_json(env).get('id'),))
                return json_response(200, {'success': True})
            if path == '/admin/api/delete_user':
                uid = read_json(env).get('id')
                db_query('DELETE FROM users WHERE id = ?', (uid,))
                db_query('DELETE FROM sessions WHERE user_id = ?', (uid,))
                db_query('DELETE FROM api_keys WHERE user_id = ?', (uid,))
                db_query('DELETE FROM api_key_daily WHERE user_id = ?', (uid,))
                return json_response(200, {'success': True})
            if path == '/admin/api/ban_key':
                db_query('UPDATE api_keys SET banned = 1, active = 0 WHERE id = ?', (read_json(env).get('id'),))
                return json_response(200, {'success': True})
            if path == '/admin/api/unban_key':
                db_query('UPDATE api_keys SET banned = 0, active = 1 WHERE id = ?', (read_json(env).get('id'),))
                return json_response(200, {'success': True})
            if path == '/admin/api/delete_key':
                db_query('DELETE FROM api_keys WHERE id = ?', (read_json(env).get('id'),))
                return json_response(200, {'success': True})
            if path == '/admin/api/set_subscription':
                b = read_json(env)
                uid = b.get('id')
                st = b.get('type')
                try:
                    days = int(b.get('days', 30))
                except Exception:
                    days = 30
                if st == 'free':
                    db_query('UPDATE users SET subscription_type = ?, subscription_expires = NULL, messages_used = 0 WHERE id = ?', (st, uid))
                elif st == 'unlimited':
                    db_query('UPDATE users SET subscription_type = ?, subscription_expires = NULL WHERE id = ?', (st, uid))
                else:
                    exp = (datetime.now() + timedelta(days=days)).isoformat()
                    pr = {'weekly':2, 'monthly':5, 'yearly':10}
                    db_query('UPDATE users SET subscription_type = ?, subscription_expires = ? WHERE id = ?', (st, exp, uid))
                    db_query('''INSERT INTO subscriptions (user_id, plan, price, started_at, expires_at, status)
                                VALUES (?, ?, ?, ?, ?, ?)''',
                             (uid, st, pr.get(st, 0), datetime.now().isoformat(), exp, 'active'))
                return json_response(200, {'success': True})
            if path == '/admin/api/reply_ticket':
                b = read_json(env)
                db_query('UPDATE support_tickets SET reply = ?, status = ?, replied_at = ? WHERE id = ?',
                        (b.get('reply'), 'closed', datetime.now().isoformat(), b.get('id')))
                return json_response(200, {'success': True})
            if path == '/admin/api/kill_session':
                db_query('DELETE FROM sessions WHERE token = ?', (read_json(env).get('token'),))
                return json_response(200, {'success': True})

        return json_response(404, {'error': 'Not Found'})
    except Exception as e:
        traceback.print_exc()
        return json_response(500, {'error': 'Server error', 'detail': str(e)})


# ═══════════════════════════════════════════════════════════════
# SPLASH IMAGES
# ═══════════════════════════════════════════════════════════════

SPLASH_IMAGES = [
    'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600&q=80',
    'https://images.unsplash.com/photo-1618336753974-aae8e04506aa?w=600&q=80',
    'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=600&q=80',
    'https://images.unsplash.com/photo-1541562232579-512a21360020?w=600&q=80',
    'https://images.unsplash.com/photo-1613376023733-0a73315d9b06?w=600&q=80',
    'https://images.unsplash.com/photo-1580477667995-2b94f01c9516?w=600&q=80',
    'https://images.unsplash.com/photo-1560972550-aba3456b5564?w=600&q=80',
    'https://images.unsplash.com/photo-1601987177651-8edfe6c20009?w=600&q=80',
]


# ═══════════════════════════════════════════════════════════════
# WSGI
# ═══════════════════════════════════════════════════════════════

_db_init = False


def _ensure():
    global _db_init
    if not _db_init:
        try:
            init_db()
            _db_init = True
        except Exception as e:
            print(f'[init_db error] {e}')
            traceback.print_exc()


def application(env, start_response):
    try:
        _ensure()
        m = env.get('REQUEST_METHOD', 'GET').upper()
        p = env.get('PATH_INFO', '/') or '/'

        if m == 'GET':
            r = handle_get(p, env)
        elif m == 'POST':
            r = handle_post(p, env)
        elif m == 'OPTIONS':
            r = Response(204, '', 'text/plain; charset=utf-8')
            r.headers['Access-Control-Allow-Origin'] = '*'
            r.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            r.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        else:
            r = Response(405, 'Method Not Allowed', 'text/plain')

        st_map = {200:'OK',204:'No Content',302:'Found',400:'Bad Request',401:'Unauthorized',
                  403:'Forbidden',404:'Not Found',405:'Method Not Allowed',429:'Too Many Requests',500:'Internal Server Error'}
        st = st_map.get(r.status, 'OK')

        headers = [
            ('Content-Type', r.content_type),
            ('Content-Length', str(len(r.body))),
            ('Cache-Control', 'no-store'),
            ('X-Content-Type-Options', 'nosniff'),
            ('X-Frame-Options', 'SAMEORIGIN'),
        ]
        for k, v in r.headers.items():
            if k == 'Set-Cookie':
                for c in v.split('\n'):
                    headers.append(('Set-Cookie', c))
            else:
                headers.append((k, v))
        start_response(f'{r.status} {st}', headers)
        return [r.body]
    except Exception as e:
        traceback.print_exc()
        body = json.dumps({'error': 'Server error', 'detail': str(e)}, ensure_ascii=False).encode('utf-8')
        start_response('500 Internal Server Error', [('Content-Type', 'application/json'), ('Content-Length', str(len(body)))])
        return [body]


def run():
    from wsgiref.simple_server import make_server, WSGIRequestHandler

    class Q(WSGIRequestHandler):
        def log_message(self, *a): pass

    init_db()
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))

    print(f"""
    ============================================================
         SOST AI v11.0 - WormGPT Edition (Fixed)
         http://localhost:{port}
         /keys       -> API Keys
         /api/docs   -> API Documentation
         /admin      -> Admin Panel (admin / SOST2009)
    ============================================================
    """)

    with make_server(host, port, application, handler_class=Q) as h:
        try:
            h.serve_forever()
        except KeyboardInterrupt:
            print('\n[SOSTAI] Stopping...')


if __name__ == '__main__':
    run()
