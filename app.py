# -*- coding: utf-8 -*-
"""
SOST AI - v14.0 ULTIMATE FINAL
✅ 3 نماذج: WormGPT + Claude AI + توليد صور
✅ لوحة تحكم متقدمة كاملة (مراقبة، حظر، اشتراكات، مفاتيح)
✅ 20 رسالة لكل مفتاح API
✅ حماية من السبام والاختراقات
✅ إصلاح مشكلة Claude API
✅ إدارة اشتراكات (مجاني/أسبوعي/شهري/سنوي + أيام مخصصة)
"""

import os, sys, json, random, secrets, re, base64, hashlib, sqlite3, time, uuid, threading
from datetime import datetime, timedelta, date
from http.cookies import SimpleCookie
from collections import defaultdict

import requests
import urllib3
urllib3.disable_warnings()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════
# الإعدادات
# ═══════════════════════════════════════════════════════════════
ADMIN_PASSWORD = "SOST2009"
MAX_MESSAGE_LENGTH = 50000
DB_PATH = os.path.join(BASE_DIR, 'sost_v14.db')

DAILY_LIMITS = {'wormgpt': 10, 'claude': 20, 'image_gen': 20}
API_KEY_PREFIX = "SOST"
API_KEY_DAILY_LIMIT = 20
API_KEY_MAX_PER_USER = 5
API_KEY_DAILY_CREATE_LIMIT = 3

RATE_LIMIT_WINDOW = 60
RATE_LIMIT_MAX = 15
_ip_requests = defaultdict(list)
_rate_lock = threading.Lock()

def check_rate_limit(ip):
    if not ip:
        return True
    now = time.time()
    with _rate_lock:
        _ip_requests[ip] = [t for t in _ip_requests[ip] if now - t < RATE_LIMIT_WINDOW]
        if len(_ip_requests[ip]) >= RATE_LIMIT_MAX:
            return False
        _ip_requests[ip].append(now)
        return True

# ═══════════════════════════════════════════════════════════════
# النماذج
# ═══════════════════════════════════════════════════════════════
MODELS = {
    'wormgpt': {'id':'wormgpt','name':'WormGPT','desc':'النموذج الأقوى - ذاكرة قوية','icon':'🐛','color':'#e11d48','type':'chat','daily_limit':10},
    'claude': {'id':'claude','name':'Claude AI','desc':'ذكي - يطور مواقع وتطبيقات Python','icon':'🎭','color':'#d97706','type':'chat','daily_limit':20},
    'image_gen': {'id':'image_gen','name':'توليد صور','desc':'Photoroom AI - 70+ ستايل','icon':'🎨','color':'#ec4899','type':'image','daily_limit':20},
}

# ═══════════════════════════════════════════════════════════════
# WormGPT
# ═══════════════════════════════════════════════════════════════
WORMGPT_URL = "https://vex-app.page.gd/worm.php"
WORMGPT_HEADERS = {
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7',
    'Referer': 'https://vex-app.page.gd/index.php',
    'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
}
WORMGPT_COOKIES = {'__test': '61e30ac543fe8bd30e11e282e12201ab', 'PHPSESSID': 'c69a4d00c854f19db0f38dab75d64aaa'}

def call_wormgpt(prompt):
    try:
        r = requests.get(WORMGPT_URL, params={'prompt': prompt},
                         cookies=WORMGPT_COOKIES, headers=WORMGPT_HEADERS,
                         timeout=120, verify=False)
        if r.status_code == 429:
            return None, "⏱️ حد WormGPT - انتظر قليلاً"
        if r.status_code != 200:
            return None, f"❌ WormGPT: {r.status_code}"
        try:
            data = r.json()
        except:
            return None, "🤔 رد غير صالح"
        if data.get('ok') and data.get('reply'):
            return data['reply'], None
        if data.get('error'):
            return None, f"⚠️ {data['error']}"
        return None, "🤔 رد فارغ"
    except requests.exceptions.Timeout:
        return None, "⏰ انتهت المدة"
    except requests.exceptions.ConnectionError:
        return None, "🌐 تعذّر الاتصال"
    except Exception as e:
        return None, f"💥 خطأ: {str(e)[:50]}"

# ═══════════════════════════════════════════════════════════════
# Claude AI
# ═══════════════════════════════════════════════════════════════
CLAUDE_ORG_ID = "72de83b7-a310-47b7-8972-057df6c07ea6"
CLAUDE_CONV_ID = "d56ac516-7c59-41ac-a482-132b54ed2a55"

CLAUDE_COOKIES = (
    "_fbp=fb.1.1791606281106.20189146116871936; "
    "anthropic-device-id=cda03ff4-b3fc-4d61-8906-ec882b313cf8; "
    "user-sidebar-visible-on-load=false; "
    "CH-prefers-color-scheme=light; "
    "__ssid=44d6a08c-2d12-49a4-84c3-1357ce107201; "
    "ajs_anonymous_id=claudeai.v1.912158a0-2161-43ac-bf70-220f9a51ffe1; "
    f"lastActiveOrg={CLAUDE_ORG_ID}; "
    "artifact-app-viewer=1; "
    "_gcl_au=1.1.1595229729.1791606333.-.-.1791606332.862062920.1791606333.1791606332; "
    "activitySessionId=fd3db9c5-170c-4191-8539-668c5b686799; "
    "ion-vk=24d49f81-e416-427b-90de-1d712b3b40a1; "
    "cfuvid=MOVddaDigpLlTPZorUK4TwH1FC7Qr_cJGPEEOseu.N4-1792184238.1729844-1.0.1.1-qbDMuow63gZih4I7VX5p2wqMELb5Nd9eAYVj_tDVSN4; "
    "cf_clearance=YtkcCqhpxn503gm8WX0A96pbxJRiefWApZ3y24adgz4-1792184241-1.2.1.1-bZAV8hiBG4ElOocG5we15NSm1dirgA78gSBngf7jeTPKSb3kVrl9sxoEkFED8TB8IldQWXQdhFGUBRjmn81Q_12ulkxEsOoeFCTrMv8CGZdkrigaEjJalYXJU62_Q661YKO53zeX8bP9aw5B.eFv8vBLcFKka2nQvy52cHy0waXeQUMb4Ud8wYvQnu1tdJIaWczpVQ6dr_w0VlzhWj.zzcm.om9IaG0nv9nbfjH.sGQYLWeL8TG.aWWdkjjxgYhqXqtgmVnEVd7WHg1LR9wbs.JgPzzui3GiPRKncpN.z9V.MxbUetcp2ltue7IPefPoYm1BuybXL0BknIJ7rXXIEHs0Xx866x3y7QozGhlwpQ; "
    "__cf_bm=PfhYIboIjtQkcnKWyc0PFsNffXRioFjWqL8jtE._Rt4-1792184241.2085154-1.0.1.1-QGPXXEu33Hi52aTVSgdzZP5zKwsXcuExbsMsMKpCYK1l._oJckt7WanwPsj3zFRp8GH4UOBE6GRbA7CrGGxFsQmQhb4hvhmtRKyreRJsiYTt3voFIm4vVDKvbt_E_j2F; "
    "sessionKey=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; "
    "sessionKeyLC=1792184257129; "
    "routingHint=sk-ant-rh-eyJ0eXAiOiAiSldUIiwgImFsZyI6ICJFUzI1NiIsICJraWQiOiAiN0MxcWFPRnhqdWxaUjRFQnNuNk1UeUZGNWdDV2JHbFpNVDR2RklrRFFpbyJ9.eyJzdWIiOiAiMjU4NmVhZDItZTY1MS00OWNlLThkODYtZTNkNmRjY2QxN2ZkIiwgInYiOiAyLCAiaXNfdmVyaWZpZWQiOiB0cnVlLCAiaGFzX21lbWJlcnNoaXAiOiB0cnVlLCAib25ib2FyZGluZ19jb21wbGV0ZSI6IHRydWUsICJhZ2VfdmVyaWZpZWQiOiB0cnVlLCAicGVuZGluZ19pbnZpdGUiOiBmYWxzZSwgInBob25lX3ZlcmlmaWVkIjogZmFsc2UsICJuYW1lIjogIlx1MDY0NVx1MDYzOVx1MDYzN1x1MDY0MVx1MDY0OSIsICJsb2NhbGUiOiAiZW4tVVMiLCAiZmxhZ3MiOiBbImVkZ2VfZGVmYXVsdF9yb3V0ZSJdLCAiaWF0IjogMTc5MjE4NDI1NywgImlzcyI6ICJjbGF1ZGUtYWktcm91dGluZyJ9.a6iZYgP_gt0oecC2s89MtFh6uLsJWWiw_XHVLsYmSoKeDPQxoKZFb_PEkPqXC5BhLtA2C-rtixrl5dH8CBZpjQ; "
    "_dd_s_v2=aid=d05a2464-c313-44bc-9fd5-77672144c2d7&id=8713b58d-8227-40d2-8bc3-3053fb07a236&created=1792184240198&expire=1792185179431&c=0"
)

CLAUDE_TOOLS = [
    {"type":"web_search_v0","name":"web_search"},
    {"type":"artifacts_v0","name":"artifacts"},
    {"type":"repl_v0","name":"repl"},
]

def call_claude(prompt, history=None):
    try:
        full_prompt = prompt
        if history and len(history) > 0:
            ctx_parts = []
            for m in history[-15:]:
                role = "المستخدم" if m.get('role') == 'user' else "المساعد"
                txt = (m.get('text') or '')[:2000]
                if txt:
                    ctx_parts.append(f"{role}: {txt}")
            if ctx_parts:
                full_prompt = "=== السياق السابق ===\n" + "\n".join(ctx_parts) + "\n\n=== الرسالة الجديدة ===\n" + prompt

        url = f"https://claude.ai/api/organizations/{CLAUDE_ORG_ID}/chat_conversations/{CLAUDE_CONV_ID}/completion"
        
        payload = {
            "prompt": full_prompt,
            "timezone": "Asia/Baghdad",
            "locale": "en-US",
            "model": "claude-sonnet-5-5",
            "effort": "medium",
            "thinking_mode": "auto",
            "tools": CLAUDE_TOOLS,
            "turn_message_uuids": {
                "human_message_uuid": str(uuid.uuid4()),
                "assistant_message_uuid": str(uuid.uuid4())
            },
            "attachments": [],
            "files": [],
            "sync_sources": [],
            "completion_request_id": str(uuid.uuid4()),
            "rendering_mode": "messages",
            "create_conversation_params": {
                "name": "",
                "model": "claude-sonnet-5-5",
                "include_conversation_preferences": True,
                "paprika_mode": None,
                "compass_mode": None,
                "tool_search_mode": "auto",
                "is_temporary": False,
                "enabled_imagine": True
            }
        }
        
        headers = {
            "authority": "claude.ai",
            "accept": "text/event-stream",
            "accept-language": "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
            "anthropic-client-platform": "web_claude_ai",
            "anthropic-client-sha": "6486b7240c3acc33e3135abbc98895853bacc69b",
            "anthropic-device-id": "cda03ff4-b3fc-4d61-8906-ec882b313cf8",
            "content-type": "application/json",
            "cookie": CLAUDE_COOKIES,
            "origin": "https://claude.ai",
            "referer": "https://claude.ai/",
            "sec-ch-ua": '"Chromium";v="137", "Not/A)Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Linux"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
            "x-datadog-origin": "rum",
            "x-datadog-parent-id": "8718296182601928591",
            "x-datadog-sampling-priority": "1",
            "x-datadog-trace-id": "9155208773885574800",
        }
        
        r = requests.post(url, headers=headers, json=payload, stream=True, timeout=180, verify=False)
        
        if r.status_code in (401, 403):
            return None, "⚠️ جلسة Claude منتهية - حدّث الكوكيز"
        if r.status_code == 429:
            return None, "⏱️ Claude: تجاوز الحد"
        if r.status_code != 200:
            return None, f"❌ Claude: HTTP {r.status_code}"
        
        full_text = []
        buffer = b""
        
        for chunk in r.iter_content(chunk_size=None):
            if not chunk:
                continue
            buffer += chunk
            while b"\n" in buffer:
                line_bytes, buffer = buffer.split(b"\n", 1)
                line = line_bytes.decode("utf-8", errors="replace").rstrip("\r")
                if not line or line.startswith("event:"):
                    continue
                if line.startswith("data:"):
                    data_str = line[5:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue
                    chunk_text = _extract_claude_text(data)
                    if chunk_text:
                        full_text.append(chunk_text)
                elif line.startswith("{"):
                    try:
                        data = json.loads(line)
                        chunk_text = _extract_claude_text(data)
                        if chunk_text:
                            full_text.append(chunk_text)
                    except:
                        pass
        
        result = "".join(full_text).strip()
        if result:
            return result, None
        return None, "🤔 رد فارغ من Claude"
        
    except requests.exceptions.Timeout:
        return None, "⏰ Claude: انتهت المدة"
    except requests.exceptions.ConnectionError:
        return None, "🌐 Claude: تعذّر الاتصال"
    except Exception as e:
        return None, f"💥 Claude: {str(e)[:80]}"

def _extract_claude_text(data):
    if not isinstance(data, dict):
        return None
    dtype = data.get("type")
    if dtype == "content_block_delta":
        delta = data.get("delta", {}) or {}
        if delta.get("type") == "text_delta":
            return delta.get("text", "")
        return ""
    if dtype in ("message_delta","message_start","message_stop","content_block_start","content_block_stop","ping"):
        return ""
    if "completion" in data and isinstance(data["completion"], str):
        return data["completion"]
    if "delta" in data:
        d = data["delta"]
        if isinstance(d, dict):
            return d.get("text", "")
        if isinstance(d, str):
            return d
    if "text" in data and isinstance(data["text"], str):
        return data["text"]
    return None

# ═══════════════════════════════════════════════════════════════
# Photoroom
# ═══════════════════════════════════════════════════════════════
STYLES = [
    ("anime","🎌 انمي"),("realistic","📸 واقعي"),("oil_painting","🖼 زيتي"),("watercolor","💧 مائي"),
    ("sketch","✏️ رسم"),("pixel","📟 بكسل"),("3d_render","🎮 ثري دي"),("cyberpunk","🤖 سايبر"),
    ("steampunk","⚙️ ستيم"),("fantasy","🐉 فانتازيا"),("gothic","🦇 قوطي"),("cartoon","📺 كرتون"),
    ("comic","💥 كوميكس"),("glitch","📺 قليتش"),("vaporwave","🌴 فيبور"),("impressionist","🎨 انطباعي"),
    ("expressionist","😱 تعبيري"),("cubist","🔺 تكسيري"),("surrealist","🌀 سيريالي"),("popart","🍅 بوب ارت"),
    ("minimalist","⬜ مينيمال"),("baroque","👑 باروكي"),("rococo","🌸 روكوكو"),("renaissance","🏛 نهضوي"),
    ("abstract","🌀 مجرد"),("graffiti","🎨 جرافيتي"),("vector","📐 فيكتور"),("isometric","📦 ايزومتريك"),
    ("low_poly","🔺 بولي قليل"),("chalk","🧵 طباشير"),("pastel","🌸 باستيل"),("charcoal","⚫ فحم"),
    ("mosaic","🟦 موزايك"),("origami","📄 اوريجامي"),("lego","🧱 ليجو"),("collage","📰 كولاج"),
    ("mandala","🕉 ماندالا"),("calligraphy","✍️ خط عربي"),("henna","🌿 حناء"),("polaroid","📸 بولارويد"),
    ("infrared","🔥 تحت حمراء"),("thermal","🌡 حرارية"),("underwater","🌊 تحت الماء"),("microscopic","🔬 مجهري"),
    ("telescopic","🔭 تلسكوبي"),("night_vision","🌙 رؤيه ليليه"),("xray","🦴 اشعه اكس"),("sonar","📡 سونار"),
    ("radar","📡 رادار"),("hologram","👻 هولوجرام"),("neon","💡 نيون"),("chromatic","🌈 كروماتيك"),
    ("monochrome","⚫ ابيض واسود"),("sepia","🟤 سيبيا"),("cyanotype","🔷 سيانوتايب"),("lomography","🎞 لوموجرافي"),
    ("tilt_shift","🏠 تلت شيفت"),("macro","🐞 ماكرو"),("bokeh","💫 بوكيه"),("long_exp","🌌 تعريض طويل"),
    ("double_exp","👥 تعريض مزدوج"),("hdr","🌅 HDR"),("night_mode","🌙 وضع ليلي"),("portrait","👤 بورتريه"),
    ("landscape","🏔 طبيعي"),("street","🚦 شوارع"),("architecture","🏛 عماره"),("food","🍔 اكل"),
    ("fashion","👗 موضه"),("product","📦 منتجات"),("automotive","🚗 سيارات"),("sports","⚽ رياضه"),
    ("wildlife","🦁 حيوانات"),("macro_insect","🐜 حشرات"),("astro","⭐ فلك"),("aerial","🛩 جوي")
]
ASPECTS = [("1:1","مربع"),("4:5","بورتريه"),("16:9","سينما"),("9:16","ستوري"),("4:3","كلاسيك"),("3:4","عمودي")]
ASPECT_MAP = {"1:1":"SQUARE_HD","4:5":"PORTRAIT_4_3","16:9":"LANDSCAPE_16_9","9:16":"PORTRAIT_16_9","4:3":"LANDSCAPE_4_3","3:4":"PORTRAIT_4_3"}

ANGLES = ["front_view","side_view","perspective","wide_angle","macro_shot","aerial","eye_level"]
LIGHTS = ["golden_hour","studio_soft","dramatic_shadow","volumetric_fog","rim_light","cinematic_ambient"]
MOODS = ["epic","calm","mysterious","dreamy","futuristic","vintage_retro","luxury"]

def _enhance_prompt(p, style_id):
    a = random.choice(ANGLES).replace("_"," ")
    l = random.choice(LIGHTS).replace("_"," ")
    m = random.choice(MOODS).replace("_"," ")
    return f"{p}, {a} view, {l} lighting, {m} atmosphere, ultra hd 8k, masterpiece, award winning, extremely detailed, professional"

def _hash(s):
    return hashlib.sha256(s.encode()).hexdigest()[:16]

def _get_photoroom_token():
    headers = {
        'Content-Type':'application/json',
        'X-Android-Package':'com.photoroom.app',
        'X-Android-Cert':'0424A4898A4B33940D8BF16E44251B876E97F8D0',
        'Accept-Language':'en-US',
        'X-Client-Version':'Android/Fallback/X23002000/FirebaseCore-Android',
        'X-Firebase-GMPID':'1:456289768976:android:30c90b24b80bc2d1bfdc95',
        'User-Agent':'Dalvik/2.1.0 (Linux; U; Android 12)',
    }
    params = {'key':'AIzaSyAJGrgbFGB_-h8V2oJLr4b-_ipetqM0duU'}
    payload = {'clientType':'CLIENT_TYPE_ANDROID'}
    r = requests.post('https://www.googleapis.com/identitytoolkit/v3/relyingparty/signupNewUser',
                      headers=headers, params=params, json=payload, timeout=30)
    return r.json()["idToken"]

def generate_images(prompt, style_id, aspect):
    size = ASPECT_MAP.get(aspect, "SQUARE_HD")
    token = _get_photoroom_token()
    rid = _hash(f"{time.time()}{random.random()}")
    headers = {
        'Host':'serverless-api.photoroom.com',
        'Accept':'text/event-stream',
        'Authorization': token,
        'Content-Type':'application/json; charset=utf-8',
        'User-Agent':'okhttp/4.12.0',
        'Pr-App-Version':'2025.47.03 (2180)',
        'Pr-Platform':'android',
        'X-Request-ID': rid,
    }
    payload = {
        "userPrompt": _enhance_prompt(prompt, style_id),
        "appId":"expert",
        "styleId": style_id,
        "sizeId": size,
        "numberOfImages": 4,
        "cfgScale": 9,
        "steps": 45,
        "seed": random.randint(1, 999999999),
    }
    r = requests.post("https://serverless-api.photoroom.com/v2/ai-tools/generate-images",
                      headers=headers, json=payload, stream=True, verify=False, timeout=180)
    bg = []
    for line in r.iter_lines():
        if not line:
            continue
        L = line.decode(errors='ignore')
        if '"eventType":"aiImageResult"' in L:
            s = L.find('"imageUrl":"') + 12
            e = L.find('"', s)
            if s > 12:
                bg.append(L[s:e])
    return bg

# ═══════════════════════════════════════════════════════════════
# قاعدة البيانات
# ═══════════════════════════════════════════════════════════════
def hash_password(p):
    return hashlib.sha256((p + "SOST_SALT_V14_2025").encode()).hexdigest()

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
        preferred_model TEXT DEFAULT 'wormgpt',
        subscription_type TEXT DEFAULT 'free',
        subscription_expires TEXT,
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
        model TEXT DEFAULT 'wormgpt',
        messages TEXT,
        created_at TEXT,
        updated_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS chat_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        username TEXT,
        model TEXT,
        user_message TEXT,
        bot_message TEXT,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS daily_usage (
        user_id INTEGER,
        day TEXT,
        wormgpt_count INTEGER DEFAULT 0,
        claude_count INTEGER DEFAULT 0,
        image_count INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, day)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS api_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        key_value TEXT UNIQUE NOT NULL,
        key_name TEXT NOT NULL,
        service_name TEXT NOT NULL,
        messages_used INTEGER DEFAULT 0,
        messages_limit INTEGER DEFAULT 20,
        active INTEGER DEFAULT 1,
        banned INTEGER DEFAULT 0,
        last_used TEXT,
        created_at TEXT
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
    c.execute('''CREATE TABLE IF NOT EXISTS subscriptions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        plan TEXT,
        price REAL,
        started_at TEXT,
        expires_at TEXT,
        status TEXT DEFAULT 'active'
    )''')
    conn.commit()
    conn.close()
    
    # Migration
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute('PRAGMA table_info(users)')
        cols = {r[1] for r in c.fetchall()}
        for col, typ in [('subscription_type', "TEXT DEFAULT 'free'"), ('subscription_expires', 'TEXT')]:
            if col not in cols:
                try: c.execute(f'ALTER TABLE users ADD COLUMN {col} {typ}')
                except: pass
        conn.commit()
    except: pass
    conn.close()
    
    existing = db_query('SELECT id FROM users WHERE username = ?', ('admin',), one=True)
    if not existing:
        db_query('''INSERT INTO users (username, password_hash, role, preferred_model, subscription_type, created_at)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                 ('admin', hash_password(ADMIN_PASSWORD), 'admin', 'wormgpt', 'unlimited', datetime.now().isoformat()))

def db_query(query, params=(), one=False):
    conn = None
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15)
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
        print(f'[DB] {e}')
        return None
    finally:
        if conn:
            conn.close()

# ═══════════════════════════════════════════════════════════════
# Daily Limits
# ═══════════════════════════════════════════════════════════════
def get_today():
    return date.today().isoformat()

def get_daily_usage(user_id):
    today = get_today()
    usage = db_query('SELECT * FROM daily_usage WHERE user_id = ? AND day = ?', (user_id, today), one=True)
    if not usage:
        db_query('''INSERT INTO daily_usage (user_id, day, wormgpt_count, claude_count, image_count)
                    VALUES (?, ?, 0, 0, 0)''', (user_id, today))
        return {'wormgpt_count': 0, 'claude_count': 0, 'image_count': 0}
    return usage

def check_daily_limit(user_id, model_type):
    user = db_query('SELECT role, subscription_type, subscription_expires FROM users WHERE id = ?', (user_id,), one=True)
    if user:
        if user.get('role') == 'admin':
            return True, 999999
        if user.get('subscription_type') == 'unlimited':
            return True, 999999
        if user.get('subscription_type') in ('weekly', 'monthly', 'yearly'):
            if user.get('subscription_expires'):
                try:
                    if datetime.fromisoformat(user['subscription_expires']) > datetime.now():
                        return True, 999999
                except: pass
    usage = get_daily_usage(user_id)
    limit = DAILY_LIMITS.get(model_type, 20)
    key = f'{model_type}_count'
    current = usage.get(key, 0)
    if current >= limit:
        return False, 0
    return True, limit - current

def increment_daily_usage(user_id, model_type):
    today = get_today()
    get_daily_usage(user_id)
    key = f'{model_type}_count'
    db_query(f'UPDATE daily_usage SET {key} = {key} + 1 WHERE user_id = ? AND day = ?', (user_id, today))

# ═══════════════════════════════════════════════════════════════
# Users & Sessions
# ═══════════════════════════════════════════════════════════════
def create_user(username, password, email=''):
    try:
        conn = sqlite3.connect(DB_PATH, timeout=15)
        c = conn.cursor()
        c.execute('''INSERT INTO users (username, password_hash, email, preferred_model, subscription_type, created_at)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (username, hash_password(password), email, 'wormgpt', 'free', datetime.now().isoformat()))
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
    user = db_query('SELECT * FROM users WHERE username = ?', (username,), one=True)
    if not user: return None
    if user.get('password_hash') != hash_password(password): return None
    if user.get('banned'): return {'banned': True}
    return user

def _detect_device(ua):
    if not ua: return 'جهاز غير معروف'
    ua = ua.lower()
    for name, key in [('iPhone','iphone'),('iPad','ipad'),('Android','android'),('Windows','windows'),('Mac','mac'),('Linux','linux')]:
        if key in ua: return name
    return 'جهاز غير معروف'

def create_session(user_id, ip='', ua=''):
    token = secrets.token_urlsafe(32)
    expires = (datetime.now() + timedelta(days=30)).isoformat()
    db_query('''INSERT INTO sessions (token, user_id, created_at, expires_at, ip, user_agent, device, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
             (token, user_id, datetime.now().isoformat(), expires, ip, ua, _detect_device(ua), datetime.now().isoformat()))
    return token

def get_session_user(token):
    if not token: return None
    session = db_query('SELECT * FROM sessions WHERE token = ?', (token,), one=True)
    if not session: return None
    try:
        if session.get('expires_at') and datetime.fromisoformat(session['expires_at']) < datetime.now():
            db_query('DELETE FROM sessions WHERE token = ?', (token,))
            return None
    except: pass
    try:
        db_query('UPDATE sessions SET last_seen = ? WHERE token = ?', (datetime.now().isoformat(), token))
    except: pass
    return db_query('SELECT * FROM users WHERE id = ?', (session['user_id'],), one=True)

# ═══════════════════════════════════════════════════════════════
# Conversations
# ═══════════════════════════════════════════════════════════════
def save_conversation(user_id, title, messages, model='wormgpt', conv_id=None):
    if conv_id:
        db_query('UPDATE conversations SET messages=?, updated_at=?, title=? WHERE id=? AND user_id=?',
                 (json.dumps(messages, ensure_ascii=False), datetime.now().isoformat(), title, conv_id, user_id))
        return conv_id
    return db_query('''INSERT INTO conversations (user_id, title, model, messages, created_at, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?)''',
                    (user_id, title, model, json.dumps(messages, ensure_ascii=False),
                     datetime.now().isoformat(), datetime.now().isoformat()))

def get_user_conversations(user_id):
    return db_query('SELECT * FROM conversations WHERE user_id = ? ORDER BY updated_at DESC LIMIT 50', (user_id,)) or []

def delete_conversation(conv_id, user_id):
    db_query('DELETE FROM conversations WHERE id = ? AND user_id = ?', (conv_id, user_id))

# ═══════════════════════════════════════════════════════════════
# API Keys
# ═══════════════════════════════════════════════════════════════
def generate_api_key():
    return f"{API_KEY_PREFIX}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"

def create_api_key(user_id, key_name, service_name):
    count = db_query('SELECT COUNT(*) as c FROM api_keys WHERE user_id = ? AND banned = 0', (user_id,), one=True)
    if count and count['c'] >= API_KEY_MAX_PER_USER:
        return None, f"وصلت للحد ({API_KEY_MAX_PER_USER})"
    today = get_today()
    daily = db_query('SELECT count FROM api_key_daily WHERE user_id = ? AND day = ?', (user_id, today), one=True)
    if daily and daily['count'] >= API_KEY_DAILY_CREATE_LIMIT:
        return None, f"⏰ حد الإنشاء اليومي"
    kv = generate_api_key()
    kid = db_query('''INSERT INTO api_keys (user_id, key_value, key_name, service_name, messages_limit, created_at)
                      VALUES (?, ?, ?, ?, ?, ?)''',
                   (user_id, kv, key_name, service_name, API_KEY_DAILY_LIMIT, datetime.now().isoformat()))
    if daily:
        db_query('UPDATE api_key_daily SET count = count + 1 WHERE user_id = ? AND day = ?', (user_id, today))
    else:
        db_query('INSERT INTO api_key_daily (user_id, day, count) VALUES (?, ?, 1)', (user_id, today))
    return kv, kid

def get_user_api_keys(user_id):
    return db_query('SELECT * FROM api_keys WHERE user_id = ? ORDER BY id DESC', (user_id,)) or []

def validate_api_key(kv):
    if not kv: return None, "missing_key"
    key = db_query('SELECT * FROM api_keys WHERE key_value = ?', (kv,), one=True)
    if not key: return None, "invalid_key"
    if key.get('banned'): return None, "key_banned"
    if not key.get('active'): return None, "key_disabled"
    if key.get('messages_used', 0) >= key.get('messages_limit', 20):
        return None, "key_limit_reached"
    user = db_query('SELECT * FROM users WHERE id = ?', (key['user_id'],), one=True)
    if not user or user.get('banned'): return None, "user_banned"
    return {'key': key, 'user': user}, None

def use_api_key(kid):
    db_query('UPDATE api_keys SET messages_used = messages_used + 1, last_used = ? WHERE id = ?',
             (datetime.now().isoformat(), kid))

def delete_api_key(kid, uid):
    db_query('DELETE FROM api_keys WHERE id = ? AND user_id = ?', (kid, uid))

def toggle_api_key(kid, uid):
    key = db_query('SELECT * FROM api_keys WHERE id = ? AND user_id = ?', (kid, uid), one=True)
    if not key: return False
    db_query('UPDATE api_keys SET active = ? WHERE id = ?', (0 if key['active'] else 1, kid))
    return True

# ═══════════════════════════════════════════════════════════════
# HTML Pages
# ═══════════════════════════════════════════════════════════════

LOGIN_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>SOST AI</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Cairo',sans-serif}
html,body{height:100%;overflow:hidden}
body{display:flex;align-items:center;justify-content:center;background:#0a0a0f;padding:12px}
#c{position:fixed;inset:0;z-index:0}
.box{position:relative;z-index:10;width:100%;max-width:340px}
.card{background:linear-gradient(145deg,rgba(20,10,15,.98),rgba(15,15,24,.98));border:1px solid rgba(225,29,72,.35);border-radius:20px;padding:24px 20px;box-shadow:0 20px 60px rgba(225,29,72,.25)}
.logo{text-align:center;margin-bottom:16px}
.logo-i{width:56px;height:56px;margin:0 auto 10px;border-radius:16px;background:linear-gradient(135deg,#e11d48,#7c3aed);display:flex;align-items:center;justify-content:center;font-size:1.5rem;box-shadow:0 8px 28px rgba(225,29,72,.5)}
h1{font-size:1.15rem;font-weight:900;background:linear-gradient(135deg,#e11d48,#7c3aed,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin-bottom:4px}
.sub{color:#9a9aae;font-size:.72rem}
.tabs{display:flex;gap:5px;margin:14px 0 12px;background:rgba(255,255,255,.03);padding:3px;border-radius:10px}
.tab{flex:1;padding:8px;text-align:center;border-radius:8px;cursor:pointer;color:#9a9aae;font-weight:700;font-size:.78rem;transition:.3s}
.tab.active{background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff}
.fg{margin-bottom:10px}
.fg label{display:block;margin-bottom:5px;color:#c5c5d5;font-size:.72rem;font-weight:700}
.fg input{width:100%;padding:10px 12px;border-radius:9px;background:rgba(255,255,255,.04);border:1px solid rgba(225,29,72,.2);color:#fff;font-size:.85rem;font-family:inherit;outline:none;transition:.3s}
.fg input:focus{border-color:#e11d48;box-shadow:0 0 0 3px rgba(225,29,72,.15)}
.btn{width:100%;padding:11px;border-radius:10px;border:none;background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;font-weight:900;font-size:.88rem;cursor:pointer;font-family:inherit;box-shadow:0 6px 20px rgba(225,29,72,.4);margin-top:4px}
.btn:hover:not(:disabled){transform:translateY(-1px)}
.btn:disabled{opacity:.6}
.err{background:rgba(239,68,68,.15);border:1px solid rgba(239,68,68,.4);color:#fca5a5;padding:8px 10px;border-radius:8px;font-size:.74rem;margin-bottom:10px;display:none;font-weight:600}
.err.show{display:block}
.tg{display:flex;align-items:center;justify-content:center;gap:5px;width:100%;padding:9px;border-radius:9px;background:rgba(225,29,72,.15);border:1px solid rgba(225,29,72,.3);color:#fb7185;font-weight:700;font-size:.76rem;text-decoration:none;margin-top:10px}
</style>
</head>
<body>
<canvas id="c"></canvas>
<div class="box">
  <div class="card">
    <div class="logo">
      <div class="logo-i">🚀</div>
      <h1>SOST AI</h1>
      <p class="sub">3 نماذج ذكاء اصطناعي متقدمة</p>
    </div>
    <div class="tabs">
      <div class="tab active" onclick="sw('l',this)">دخول</div>
      <div class="tab" onclick="sw('r',this)">حساب جديد</div>
    </div>
    <div class="err" id="err"></div>
    <form id="lf" onsubmit="event.preventDefault();doLogin()">
      <div class="fg"><label>👤 المستخدم</label><input type="text" id="lu" required autocomplete="username" placeholder="username"></div>
      <div class="fg"><label>🔒 المرور</label><input type="password" id="lp" required autocomplete="current-password" placeholder="••••••"></div>
      <button type="submit" class="btn" id="lb">🚀 دخول</button>
    </form>
    <form id="rf" style="display:none" onsubmit="event.preventDefault();doReg()">
      <div class="fg"><label>👤 المستخدم</label><input type="text" id="ru" required minlength="3" placeholder="3+ أحرف"></div>
      <div class="fg"><label>🔒 المرور</label><input type="password" id="rp" required minlength="6" placeholder="6+ أحرف"></div>
      <button type="submit" class="btn" id="rb">✨ إنشاء</button>
    </form>
    <a href="https://t.me/Yb_xY" target="_blank" class="tg">📱 الدعم — @Yb_xY</a>
  </div>
</div>
<script>
(function(){const c=document.getElementById('c'),x=c.getContext('2d');let w,h,ps=[];function rs(){w=c.width=innerWidth;h=c.height=innerHeight}rs();addEventListener('resize',rs);for(let i=0;i<40;i++)ps.push({x:Math.random()*w,y:Math.random()*h,r:Math.random()*2+1,vx:(Math.random()-.5)*.4,vy:(Math.random()-.5)*.4,hu:Math.random()>.5?340:270});function d(){x.clearRect(0,0,w,h);ps.forEach((p,i)=>{p.x+=p.vx;p.y+=p.vy;if(p.x<0||p.x>w)p.vx*=-1;if(p.y<0||p.y>h)p.vy*=-1;x.beginPath();x.arc(p.x,p.y,p.r,0,Math.PI*2);x.fillStyle=`hsla(${p.hu},80%,65%,.7)`;x.fill();for(let j=i+1;j<ps.length;j++){const q=ps[j],dx=p.x-q.x,dy=p.y-q.y,dd=Math.sqrt(dx*dx+dy*dy);if(dd<120){x.beginPath();x.moveTo(p.x,p.y);x.lineTo(q.x,q.y);x.strokeStyle=`hsla(${p.hu},80%,65%,${(1-dd/120)*.3})`;x.lineWidth=.5;x.stroke()}}});requestAnimationFrame(d)}d()})();
function sw(t,e){document.querySelectorAll('.tab').forEach(x=>x.classList.remove('active'));e.classList.add('active');document.getElementById('lf').style.display=t==='l'?'':'none';document.getElementById('rf').style.display=t==='r'?'':'none';document.getElementById('err').classList.remove('show')}
function err(m){const b=document.getElementById('err');b.textContent='⚠️ '+m;b.classList.add('show');setTimeout(()=>b.classList.remove('show'),5000)}
async function doLogin(){const u=document.getElementById('lu').value.trim(),p=document.getElementById('lp').value;if(!u||!p)return err('أدخل البيانات');const b=document.getElementById('lb');b.disabled=true;b.textContent='...';try{const r=await fetch('/api/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});const d=await r.json();if(d.success)location.href='/';else{err(d.error||'خطأ');b.disabled=false;b.textContent='🚀 دخول'}}catch(e){err('فشل');b.disabled=false;b.textContent='🚀 دخول'}}
async function doReg(){const u=document.getElementById('ru').value.trim(),p=document.getElementById('rp').value;if(u.length<3)return err('اسم قصير');if(p.length<6)return err('كلمة قصيرة');const b=document.getElementById('rb');b.disabled=true;b.textContent='...';try{const r=await fetch('/api/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p})});const d=await r.json();if(d.success)location.href='/';else{err(d.error||'خطأ');b.disabled=false;b.textContent='✨ إنشاء'}}catch(e){err('فشل');b.disabled=false;b.textContent='✨ إنشاء'}}
</script>
</body>
</html>"""

# MAIN_PAGE طويل جداً - سأستخدم النص الذي أرسلته من قبل مع تعديلات بسيطة
MAIN_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=5">
<title>SOST AI</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24'><rect width='24' height='24' rx='6' fill='%23e11d48'/><text y='18' x='5' font-size='14' fill='white'>🚀</text></svg>">
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
html,body{height:100%;font-family:'Cairo',sans-serif;background:#0a0a0f;color:#f5f5f7;overflow:hidden}
body{display:flex}
.sb{width:270px;background:#0f0f18;border-left:1px solid #1f1f2e;display:flex;flex-direction:column;height:100vh;transition:.3s;flex-shrink:0;z-index:100}
.sb.mo{transform:translateX(100%)}
.sbh{padding:14px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1f1f2e}
.sbl{display:flex;align-items:center;gap:8px;font-weight:900;font-size:.98rem;cursor:pointer}
.sbli{width:34px;height:34px;border-radius:9px;background:linear-gradient(135deg,#e11d48,#7c3aed);display:flex;align-items:center;justify-content:center;font-size:1rem}
.cs{width:30px;height:30px;border-radius:8px;border:none;background:transparent;color:#9a9aae;font-size:1.1rem;cursor:pointer}
.sbb{flex:1;overflow-y:auto;padding:10px}
.sb-b{display:flex;align-items:center;gap:10px;width:100%;padding:11px 13px;border-radius:10px;border:none;background:transparent;color:#f5f5f7;font-family:inherit;font-size:.88rem;font-weight:600;cursor:pointer;text-align:right;transition:.15s;margin-bottom:3px;text-decoration:none}
.sb-b:hover{background:#1f1f2e}
.sb-b .ico{width:22px;height:22px;display:flex;align-items:center;justify-content:center;font-size:.95rem;flex-shrink:0}
.sb-b.pri{background:linear-gradient(135deg,#e11d48,#7c3aed);margin-bottom:12px;box-shadow:0 6px 20px rgba(225,29,72,.3)}
.sec{padding:12px 13px 6px;font-size:.68rem;color:#6a6a80;font-weight:800;text-transform:uppercase}
.cm{display:flex;align-items:center;gap:8px;padding:8px 10px;border-radius:8px;cursor:pointer;font-size:.83rem;color:#c5c5d5;transition:.15s}
.cm:hover{background:#1f1f2e}
.cmt{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.cmd{opacity:0;width:20px;height:20px;border-radius:6px;border:none;background:transparent;color:#9a9aae;cursor:pointer;font-size:.75rem}
.cm:hover .cmd{opacity:1}
.sbf{padding:10px;border-top:1px solid #1f1f2e}
.uc{display:flex;align-items:center;gap:9px;padding:9px;border-radius:10px;cursor:pointer}
.uc:hover{background:#1f1f2e}
.ua{width:34px;height:34px;border-radius:50%;background:linear-gradient(135deg,#e11d48,#7c3aed);display:flex;align-items:center;justify-content:center;color:#fff;font-weight:900;font-size:.9rem;flex-shrink:0}
.ui{flex:1;min-width:0}
.un{font-weight:700;font-size:.85rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.us{font-size:.68rem;color:#9a9aae}
.mn{flex:1;display:flex;flex-direction:column;height:100vh;min-width:0;position:relative;z-index:1}
.tb{padding:11px 16px;display:flex;align-items:center;gap:10px;border-bottom:1px solid #1f1f2e;flex-shrink:0;background:#0f0f18}
.mt{width:38px;height:38px;border-radius:10px;border:none;background:transparent;cursor:pointer;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;flex-shrink:0}
.mt:hover{background:#1f1f2e}
.mt span{width:18px;height:2px;background:#f5f5f7;border-radius:2px}
.ms{display:flex;align-items:center;gap:8px;padding:9px 14px;border-radius:12px;border:1px solid #1f1f2e;background:#0f0f18;cursor:pointer;font-weight:800;font-size:.88rem;transition:.15s;position:relative}
.ms:hover{border-color:#e11d48}
.ms .ar{font-size:.65rem;color:#9a9aae;transition:.2s}
.ms.op .ar{transform:rotate(180deg)}
.mis{width:22px;height:22px;border-radius:6px;display:flex;align-items:center;justify-content:center;font-size:.85rem;color:#fff;font-weight:900}
.md{position:absolute;top:calc(100% + 6px);right:0;background:#0f0f18;border:1px solid #1f1f2e;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.6);padding:6px;min-width:300px;opacity:0;transform:translateY(-8px);pointer-events:none;transition:.2s;z-index:200}
.md.show{opacity:1;transform:translateY(0);pointer-events:auto}
.mi{display:flex;align-items:center;gap:10px;padding:10px;border-radius:10px;cursor:pointer;transition:.15s}
.mi:hover{background:#1f1f2e}
.mi.act{background:#1f1f2e}
.mimg{width:38px;height:38px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:1.1rem;color:#fff;font-weight:900}
.mii{flex:1}
.min{font-weight:800;font-size:.88rem}
.mid{font-size:.72rem;color:#9a9aae;margin-top:1px}
.mic{color:#10b981;font-weight:900}
.mlim{font-size:.65rem;color:#fb7185;margin-top:1px}
.ch{flex:1;overflow-y:auto;padding:18px 14px 30px;scroll-behavior:smooth}
.wl{max-width:760px;margin:16px auto;text-align:center}
.wi{width:130px;height:130px;margin:0 auto 16px;border-radius:22px;overflow:hidden;box-shadow:0 18px 55px rgba(225,29,72,.4);animation:bo 4s ease-in-out infinite;background:#1f1f2e}
.wi img{width:100%;height:100%;object-fit:cover}
@keyframes bo{0%,100%{transform:translateY(0)}50%{transform:translateY(-7px)}}
.wl h1{font-size:1.55rem;font-weight:900;margin-bottom:8px;background:linear-gradient(135deg,#e11d48,#7c3aed,#f472b6);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.wl p{color:#9a9aae;font-size:.88rem;line-height:1.6;max-width:500px;margin:0 auto 22px}
.chips{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:8px;max-width:620px;margin:0 auto}
.chip{padding:12px 13px;border-radius:12px;border:1px solid #1f1f2e;background:#0f0f18;cursor:pointer;transition:.2s;text-align:right;font-family:inherit;font-size:.82rem;color:#f5f5f7}
.chip:hover{border-color:#e11d48;transform:translateY(-2px)}
.chip strong{display:block;margin-bottom:3px;font-weight:800;font-size:.86rem}
.chip span{color:#9a9aae;font-size:.74rem}
.msgs{max-width:760px;margin:0 auto}
.mg{margin-bottom:20px;animation:fd .3s}
@keyframes fd{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.mg.u{display:flex;justify-content:flex-end}
.mg.b{display:flex;gap:10px}
.ma{width:34px;height:34px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:.9rem;color:#fff;font-weight:900}
.mbd{flex:1;min-width:0}
.mg.u .mbd{max-width:82%}
.bb{line-height:1.7;font-size:.92rem;word-wrap:break-word}
.mg.u .bb{background:linear-gradient(135deg,#1f1f2e,#181826);padding:12px 15px;border-radius:16px;border:1px solid rgba(225,29,72,.15)}
.mg.b .bb{background:transparent;padding:2px 0}
.bb p{margin:6px 0}.bb p:first-child{margin-top:0}
.bb h1,.bb h2,.bb h3{margin:12px 0 7px;font-weight:800;color:#fb7185}
.bb ul,.bb ol{margin:8px 0;padding-right:20px}
.bb li{margin:3px 0}
.bb code{background:#1f1f2e;padding:2px 6px;border-radius:4px;font-family:monospace;font-size:.85em;color:#fb7185}
.bb pre{background:#000;color:#e2e8f0;border-radius:10px;padding:12px;overflow-x:auto;margin:10px 0;direction:ltr;text-align:left;font-size:.82rem;border:1px solid #1f1f2e}
.bb pre code{background:transparent;color:inherit;padding:0}
.bb a{color:#fb7185}
.code-box{position:relative;margin:10px 0}
.code-actions{position:absolute;top:6px;left:6px;display:flex;gap:5px;z-index:10}
.code-btn{padding:4px 9px;border-radius:6px;border:none;background:rgba(225,29,72,.9);color:#fff;font-family:inherit;font-weight:700;font-size:.68rem;cursor:pointer}
.code-btn.copied{background:#10b981}
.img-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:8px;margin-top:10px}
.img-grid img{width:100%;border-radius:12px;cursor:pointer}
.tp{display:inline-flex;gap:5px;padding:6px 0}
.tp span{width:7px;height:7px;border-radius:50%;background:#e11d48;animation:td 1.2s infinite}
.tp span:nth-child(2){animation-delay:.15s}
.tp span:nth-child(3){animation-delay:.3s}
@keyframes td{0%,60%,100%{opacity:.3;transform:scale(.7)}30%{opacity:1;transform:scale(1)}}
.stop-btn{background:rgba(239,68,68,.15);border:1px solid #ef4444;color:#fca5a5;padding:4px 10px;border-radius:7px;font-family:inherit;font-size:.68rem;font-weight:700;cursor:pointer;margin-top:6px}
.ia{padding:12px 16px 16px;flex-shrink:0;background:#0a0a0f}
.ctrl{max-width:760px;margin:0 auto 8px;display:flex;gap:8px;flex-wrap:wrap}
.ctrl select{padding:9px 12px;border-radius:10px;border:1px solid #1f1f2e;font-family:inherit;font-size:.82rem;background:#0f0f18;color:#f5f5f7;outline:none;font-weight:600;flex:1;min-width:130px}
.ib{max-width:760px;margin:0 auto;background:#0f0f18;border:1px solid #1f1f2e;border-radius:18px;padding:7px 7px 7px 13px;display:flex;gap:7px;align-items:flex-end}
.ib:focus-within{border-color:#e11d48}
#ui{flex:1;background:transparent;border:none;outline:none;font-family:inherit;font-size:.92rem;color:#f5f5f7;resize:none;padding:9px 5px;line-height:1.5;max-height:160px}
#ui::placeholder{color:#6a6a80}
.ibtn{width:38px;height:38px;border-radius:50%;border:none;background:transparent;color:#9a9aae;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0;font-size:1rem}
.ibtn:hover{background:#1f1f2e;color:#fb7185}
#sb{width:38px;height:38px;border-radius:50%;border:none;background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}
#sb:disabled{opacity:.3}
.hint{max-width:760px;margin:6px auto 0;font-size:.68rem;color:#6a6a80;text-align:center}
.ov{position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:500;display:none;align-items:center;justify-content:center;padding:16px}
.ov.show{display:flex}
.md2{background:#0f0f18;border:1px solid #1f1f2e;border-radius:18px;padding:22px;max-width:500px;width:100%;max-height:88vh;overflow-y:auto;position:relative}
.md2 h2{font-size:1.15rem;margin-bottom:14px;font-weight:900}
.mc2{float:left;width:32px;height:32px;border-radius:8px;border:none;background:#1f1f2e;color:#f5f5f7;cursor:pointer;font-size:.95rem}
.pc{border:2px solid #1f1f2e;border-radius:14px;padding:14px;margin-bottom:10px}
.pc.f{border-color:#e11d48;background:linear-gradient(135deg,rgba(225,29,72,.1),rgba(124,58,237,.1))}
.ph{display:flex;justify-content:space-between;align-items:center;margin-bottom:6px}
.pn{font-weight:900;font-size:.95rem}
.pp{font-weight:900;font-size:1.2rem;color:#fb7185}
.pfl{list-style:none;font-size:.8rem;color:#9a9aae;margin:6px 0}
.pbt{width:100%;padding:10px;border-radius:10px;border:none;background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;font-weight:800;cursor:pointer;font-family:inherit;margin-top:7px;font-size:.85rem}
.sr{display:flex;justify-content:space-between;align-items:center;padding:11px;border-radius:10px;background:#141420;margin-bottom:7px;gap:9px;border:1px solid #1f1f2e}
.sri{flex:1;min-width:0}
.srd{font-weight:700;font-size:.86rem}
.srm{font-size:.7rem;color:#9a9aae;margin-top:2px}
.scc{font-size:.65rem;color:#10b981;font-weight:800}
.bs{padding:5px 11px;border-radius:7px;border:none;background:#ef4444;color:#fff;font-family:inherit;font-weight:800;font-size:.72rem;cursor:pointer}
.to{position:fixed;bottom:20px;left:50%;transform:translateX(-50%) translateY(100px);background:#1f1f2e;color:#f5f5f7;padding:11px 18px;border-radius:11px;font-size:.82rem;font-weight:700;opacity:0;transition:.3s;z-index:9999;pointer-events:none;max-width:90vw;text-align:center;border:1px solid #e11d48}
.to.show{opacity:1;transform:translateX(-50%) translateY(0)}
.lb{position:fixed;inset:0;background:rgba(0,0,0,.95);z-index:2000;display:none;align-items:center;justify-content:center;padding:16px;cursor:zoom-out}
.lb.show{display:flex}
.lb img{max-width:95%;max-height:95%;border-radius:10px}
.lb a{position:absolute;top:16px;left:16px;background:#e11d48;color:#fff;padding:9px 15px;border-radius:9px;text-decoration:none;font-weight:800;font-size:.82rem}
@media(max-width:768px){
  .sb{position:fixed;top:0;right:0;transform:translateX(100%)}
  .sb.mo{transform:translateX(0)}
  .mg.u .mbd{max-width:88%}
  .wl h1{font-size:1.3rem}
  .wi{width:110px;height:110px}
}
@media(min-width:769px){.mt{display:none}.sb .cs{display:none}}
</style>
</head>
<body>

<aside class="sb" id="sb2">
  <div class="sbh">
    <div class="sbl" onclick="newChat()">
      <div class="sbli">🚀</div>
      <span>SOST AI</span>
    </div>
    <button class="cs" onclick="togSidebar()">✕</button>
  </div>
  <div class="sbb">
    <button class="sb-b pri" onclick="newChat()"><span class="ico">✨</span><span>محادثة جديدة</span></button>
    <button class="sb-b" onclick="openSaved()"><span class="ico">💾</span><span>محادثاتي</span></button>
    <button class="sb-b" onclick="saveCur()"><span class="ico">📌</span><span>حفظ الحالية</span></button>
    <div class="sec" id="rlb" style="display:none">الأخيرة</div>
    <div id="rc"></div>
  </div>
  <div class="sbf">
    <button class="sb-b" onclick="openSub()"><span class="ico">💎</span><span>الاشتراكات</span></button>
    <a href="/keys" class="sb-b" style="text-decoration:none;color:inherit"><span class="ico">🔑</span><span>مفاتيح API</span></a>
    <div class="uc" onclick="openAcc()">
      <div class="ua">{{USERNAME_INITIAL}}</div>
      <div class="ui">
        <div class="un">{{USERNAME}}</div>
        <div class="us" id="usageInfo">جاري...</div>
      </div>
      <div style="color:#9a9aae">⚙️</div>
    </div>
  </div>
</aside>

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
      <h1>مرحباً {{USERNAME}} 🚀</h1>
      <p>اختر النموذج وابدأ — أنا أتذكر كل شيء وأطور أي كود تحتاجه</p>
      <div class="chips">
        <button class="chip" onclick="qa('اشرح لي الذكاء الاصطناعي ببساطة')"><strong>🧠 تعلم</strong><span>ما هو AI؟</span></button>
        <button class="chip" onclick="qa('اكتب كود Python كامل لموقع Flask')"><strong>💻 برمجة</strong><span>كود Python</span></button>
        <button class="chip" onclick="qa('اكتب قصيدة عن الأمل')"><strong>✍️ إبداع</strong><span>قصيدة</span></button>
        <button class="chip" onclick="qa('صمملي كود موقع متجر ورد متكامل بلغه HTML')"><strong>🌐 ويب</strong><span>موقع كامل</span></button>
      </div>
    </div>
    <div class="msgs" id="msgs"></div>
  </div>
  <div class="ia">
    <div class="ctrl" id="imgCtrl" style="display:none">
      <select id="imgStyle">{{STYLE_OPTIONS}}</select>
      <select id="imgAspect">{{ASPECT_OPTIONS}}</select>
    </div>
    <div class="ib">
      <textarea id="ui" placeholder="اكتب رسالتك..." rows="1"></textarea>
      <button class="ibtn" id="vb">🎤</button>
      <button id="sb" onclick="send()">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
      </button>
    </div>
    <div class="hint">Enter للإرسال • Shift+Enter سطر جديد</div>
  </div>
</div>

<div class="ov" id="svd"><div class="md2"><button class="mc2" onclick="cl('svd')">✕</button><h2>💾 محادثاتي</h2><div id="svdL"></div></div></div>
<div class="ov" id="sub"><div class="md2"><button class="mc2" onclick="cl('sub')">✕</button><h2>💎 الاشتراكات</h2>
  <div class="pc"><div class="ph"><div class="pn">🆓 مجاني</div><div class="pp">$0</div></div><ul class="pfl"><li>✅ 20 WormGPT / يوم</li><li>✅ 40 Claude / يوم</li><li>✅ 20 صورة / يوم</li></ul></div>
  <div class="pc f"><div class="ph"><div class="pn">👑 غير محدود</div><div class="pp">$10</div></div><ul class="pfl"><li>✅ بدون حدود</li></ul><button class="pbt" onclick="subs()">اشترك</button></div>
</div></div>
<div class="ov" id="acc"><div class="md2"><button class="mc2" onclick="cl('acc')">✕</button><h2>⚙️ الإعدادات</h2>
  <div style="background:#141420;border-radius:11px;padding:12px;margin-bottom:14px;border:1px solid #1f1f2e">
    <div style="font-weight:900;margin-bottom:5px">👤 {{USERNAME}}</div>
    <div style="font-size:.78rem;color:#9a9aae" id="accInfo">جاري...</div>
  </div>
  <h3 style="font-size:.88rem;margin-bottom:9px">📊 الاستخدام اليومي</h3>
  <div id="dailyUsage" style="margin-bottom:14px"></div>
  <h3 style="font-size:.88rem;margin-bottom:9px">📱 الجلسات</h3>
  <div id="sessList">جاري...</div>
  <button class="pbt" style="background:#ef4444;margin-top:14px" onclick="logout()">🚪 خروج</button>
</div></div>
<div class="lb" id="lb" onclick="this.classList.remove('show')">
  <a id="lbDl" href="#" download target="_blank" onclick="event.stopPropagation()">⬇️ تحميل</a>
  <img id="lbImg" src="">
</div>
<div class="to" id="to"></div>

<script>
const MODELS = {{MODELS_JSON}};
const USER = {name:'{{USERNAME}}', id:{{USER_ID}}};
const SPLASH_IMAGES = {{SPLASH_IMAGES_JSON}};
let curModel = '{{PREFERRED_MODEL}}';
let sending = false;
let chatMsgs = [];
let currentConvId = null;
let abortController = null;
let msgCounter = 0;

document.getElementById('wImg').src = SPLASH_IMAGES[Math.floor(Math.random()*SPLASH_IMAGES.length)];

function esc(t){const d=document.createElement('div');d.textContent=t||'';return d.innerHTML}
function rmd(t){try{marked.setOptions({breaks:true,gfm:true});let h=marked.parse(t);if(window.DOMPurify)h=DOMPurify.sanitize(h);return h}catch(e){return esc(t).replace(/\n/g,'<br>')}}
function scrollB(){const c=document.getElementById('ch');requestAnimationFrame(()=>c.scrollTop=c.scrollHeight)}

function buildMD(){
  document.getElementById('md').innerHTML = Object.values(MODELS).map(m=>`
    <div class="mi ${m.id===curModel?'act':''}" onclick="pickMD('${m.id}')">
      <div class="mimg" style="background:${m.color}">${m.icon}</div>
      <div class="mii"><div class="min">${m.name}</div><div class="mid">${m.desc}</div><div class="mlim">📊 ${m.daily_limit} / يوم</div></div>
      ${m.id===curModel?'<span class="mic">✓</span>':''}
    </div>`).join('');
}
function pickMD(id){
  curModel = id; const m = MODELS[id];
  document.getElementById('mn2').textContent = m.name;
  const ic = document.getElementById('mis'); ic.textContent = m.icon; ic.style.background = m.color;
  document.getElementById('md').classList.remove('show');
  document.getElementById('ms').classList.remove('op');
  document.getElementById('imgCtrl').style.display = id === 'image_gen' ? 'flex' : 'none';
  fetch('/api/set_model',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model:id})}).catch(()=>{});
  buildMD();
}
function togMD(e){e.stopPropagation();document.getElementById('md').classList.toggle('show');document.getElementById('ms').classList.toggle('op');}
document.addEventListener('click',()=>{document.getElementById('md')?.classList.remove('show');document.getElementById('ms')?.classList.remove('op')});

function togSidebar(){document.getElementById('sb2').classList.toggle('mo')}
function closeM(){document.getElementById('sb2').classList.remove('mo')}

function addMsg(role, text, images, msgId){
  const w = document.getElementById('msgs');
  document.getElementById('wl').style.display = 'none';
  const d = document.createElement('div');
  d.className = 'mg ' + role;
  if(msgId) d.id = msgId;
  if(role === 'user'){
    d.innerHTML = `<div class="mbd"><div class="bb">${esc(text).replace(/\n/g,'<br>')}</div><button class="stop-btn" onclick="stopAndEdit('${msgId}')">⏸️ إيقاف وتعديل</button></div>`;
  } else if(role === 'images'){
    const grid = images.map((u,i)=>`<img src="${u}" loading="lazy" onclick="showLB('${u}')" alt="صورة ${i+1}">`).join('');
    d.innerHTML = `<div class="ma" style="background:#ec4899">🎨</div><div class="mbd"><div class="bb"><p><strong>🎨 تم التوليد</strong></p><div class="img-grid">${grid}</div></div></div>`;
  } else {
    const m = MODELS[curModel] || MODELS.wormgpt;
    let html = rmd(text);
    html = html.replace(/<pre><code/g, '<div class="code-box"><div class="code-actions"><button class="code-btn" onclick="copyCode(this)">📋 نسخ</button><button class="code-btn" onclick="downloadCode(this)">⬇️ تنزيل</button></div><pre><code');
    html = html.replace(/<\/code><\/pre>/g, '</code></pre></div>');
    d.innerHTML = `<div class="ma" style="background:${m.color}">${m.icon}</div><div class="mbd"><div class="bb">${html}</div></div>`;
  }
  w.appendChild(d);
  chatMsgs.push({role: role==='images'?'bot':role, text, images});
  scrollB();
}
function addTyping(){
  const w = document.getElementById('msgs');
  document.getElementById('wl').style.display = 'none';
  const d = document.createElement('div'); d.className = 'mg b'; d.id = 'tp';
  const m = MODELS[curModel] || MODELS.wormgpt;
  d.innerHTML = `<div class="ma" style="background:${m.color}">${m.icon}</div><div class="mbd"><div class="bb"><div class="tp"><span></span><span></span><span></span></div></div></div>`;
  w.appendChild(d); scrollB();
}
function rmTyping(){document.getElementById('tp')?.remove()}

function copyCode(btn){
  const pre = btn.closest('.code-box').querySelector('pre code');
  navigator.clipboard.writeText(pre.textContent).then(()=>{btn.textContent='✅ تم';btn.classList.add('copied');setTimeout(()=>{btn.textContent='📋 نسخ';btn.classList.remove('copied')},2000)});
}
function downloadCode(btn){
  const pre = btn.closest('.code-box').querySelector('pre code');
  const blob = new Blob([pre.textContent], {type:'text/plain'});
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'code_' + Date.now() + '.txt'; a.click(); URL.revokeObjectURL(url);
}
function showLB(url){
  document.getElementById('lbImg').src = url;
  document.getElementById('lbDl').href = url;
  document.getElementById('lb').classList.add('show');
}

async function send(override){
  if(sending) return;
  const i = document.getElementById('ui');
  const text = (override !== undefined ? override : i.value).trim();
  if(!text) return;
  sending = true; document.getElementById('sb').disabled = true;
  i.value = ''; autoResize();
  const msgId = 'msg_' + (++msgCounter);
  addMsg('user', text, null, msgId); addTyping(); closeM();
  abortController = new AbortController();
  try {
    let endpoint = '/api/chat';
    let body = {message: text, model: curModel, history: chatMsgs.slice(-15)};
    if(curModel === 'image_gen'){
      endpoint = '/api/generate_image';
      body = {prompt: text, style: document.getElementById('imgStyle').value, aspect: document.getElementById('imgAspect').value};
    }
    const r = await fetch(endpoint, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body), signal: abortController.signal});
    const d = await r.json();
    rmTyping();
    if(d.success && d.images){ addMsg('images', text, d.images); }
    else if(d.reply){ addMsg('bot', d.reply); }
    else { addMsg('bot', '⚠️ ' + (d.error || 'خطأ')); if(d.limit_reached) tt('⏰ وصلت للحد اليومي'); }
    updateUsage(); autoSave();
  } catch(e) {
    rmTyping();
    if(e.name === 'AbortError'){ addMsg('bot', '⏸️ تم إيقاف الرد.'); }
    else { addMsg('bot', '🌐 فشل الاتصال'); }
  } finally {
    sending = false; abortController = null;
    document.getElementById('sb').disabled = false;
  }
}
function stopAndEdit(msgId){
  if(abortController) abortController.abort();
  const msgEl = document.getElementById(msgId);
  if(msgEl){
    let next = msgEl.nextElementSibling;
    while(next && !next.classList.contains('mg')) next = next.nextElementSibling;
    if(next) next.remove();
    const origText = msgEl.querySelector('.bb').innerText;
    msgEl.remove();
    document.getElementById('ui').value = origText.replace(/\n\n⏸️.*$/,'');
  }
  chatMsgs = chatMsgs.slice(0, -1);
  if(chatMsgs.length > 0 && chatMsgs[chatMsgs.length-1].role === 'bot') chatMsgs.pop();
  autoResize(); document.getElementById('ui').focus(); tt('✏️ عدّل رسالتك');
}
function qa(q){send(q)}
const ui = document.getElementById('ui');
function autoResize(){ui.style.height='auto';ui.style.height=Math.min(ui.scrollHeight,160)+'px'}
ui.addEventListener('input', autoResize);
ui.addEventListener('keydown', e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();send()}});

let rec = null, voiceActive = false;
if('webkitSpeechRecognition' in window || 'SpeechRecognition' in window){
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  rec = new SR(); rec.continuous = false; rec.interimResults = true; rec.lang = 'ar-SA';
  rec.onstart = () => {voiceActive = true; document.getElementById('vb').style.color = '#ef4444';};
  rec.onresult = e => {let finalT = '';for(let i = e.resultIndex; i < e.results.length; i++){if(e.results[i].isFinal) finalT += e.results[i][0].transcript;}if(finalT){ rec.stop(); ui.value = finalT.trim(); autoResize(); setTimeout(()=>send(), 300); }};
  rec.onend = () => {voiceActive = false; document.getElementById('vb').style.color = '';};
  document.getElementById('vb').onclick = () => {if(voiceActive) rec.stop();else try{rec.start();}catch(e){tt('⚠️ خطأ صوت')}};
} else { document.getElementById('vb').onclick = () => tt('⚠️ غير مدعوم'); }

function newChat(){
  if(chatMsgs.length && !confirm('محادثة جديدة؟')) return;
  document.getElementById('msgs').innerHTML = ''; document.getElementById('wl').style.display = '';
  chatMsgs = []; currentConvId = null; closeM();
}
function autoSave(){
  if(chatMsgs.length < 2) return;
  const title = (chatMsgs[0]?.text || 'محادثة').slice(0, 40);
  fetch('/api/save_chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({title, messages: chatMsgs, model: curModel, conv_id: currentConvId})}).then(r=>r.json()).then(d=>{ if(d.conv_id) currentConvId = d.conv_id; }).catch(()=>{});
}
async function saveCur(){
  if(!chatMsgs.length) return tt('⚠️ لا رسائل');
  const t = prompt('📌 الاسم:', 'محادثة ' + new Date().toLocaleDateString('ar-EG'));
  if(!t) return;
  const r = await fetch('/api/save_chat', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({title:t, messages:chatMsgs, model:curModel, conv_id:currentConvId})});
  const d = await r.json();
  if(d.success){tt('💾 تم الحفظ'); if(d.conv_id) currentConvId = d.conv_id; loadRec();}
  else tt('❌ فشل');
}
function openSaved(){document.getElementById('svd').classList.add('show'); renderSvd()}
async function renderSvd(){
  const box = document.getElementById('svdL');
  box.innerHTML = '<p style="color:#9a9aae;text-align:center;padding:20px">جاري...</p>';
  try{
    const r = await fetch('/api/get_chats');
    const d = await r.json();
    if(!d.chats || !d.chats.length){box.innerHTML='<p style="color:#9a9aae;text-align:center;padding:20px">لا توجد محادثات</p>';return}
    box.innerHTML = d.chats.map(c=>`<div class="sr"><div class="sri" onclick='loadChat(${JSON.stringify(c).replace(/'/g,"&#39;")})' style="cursor:pointer"><div class="srd">${MODELS[c.model]?.icon||'💬'} ${esc(c.title)}</div><div class="srm">📅 ${new Date(c.created_at).toLocaleString('ar-EG')}</div></div><button class="bs" onclick="delChat(${c.id})">🗑️</button></div>`).join('');
  }catch(e){box.innerHTML='<p style="color:#ef4444;text-align:center">فشل</p>'}
}
async function loadRec(){
  try{
    const r = await fetch('/api/get_chats');
    const d = await r.json();
    const box = document.getElementById('rc'); const lb = document.getElementById('rlb');
    if(!d.chats || !d.chats.length){box.innerHTML='';lb.style.display='none';return}
    lb.style.display = 'block';
    box.innerHTML = d.chats.slice(0,10).map(c=>`<div class="cm" onclick='loadChat(${JSON.stringify(c).replace(/'/g,"&#39;")})'><span>${MODELS[c.model]?.icon||'💬'}</span><span class="cmt">${esc(c.title)}</span><button class="cmd" onclick="event.stopPropagation();delChat(${c.id})">🗑️</button></div>`).join('');
  }catch(e){}
}
function loadChat(c){
  if(chatMsgs.length && !confirm('استبدال؟')) return;
  document.getElementById('msgs').innerHTML = ''; document.getElementById('wl').style.display = 'none';
  chatMsgs = []; currentConvId = c.id;
  if(c.model && MODELS[c.model]) pickMD(c.model);
  const m = JSON.parse(c.messages);
  m.forEach(x=>{
    if(x.images && x.images.length) addMsg('images', x.text||'', x.images);
    else if(x.role==='user') addMsg('user', x.text, null, 'msg_hist_'+(++msgCounter));
    else addMsg('bot', x.text);
  });
  document.getElementById('svd').classList.remove('show'); closeM(); tt('📂 تم التحميل');
}
async function delChat(id){
  if(!confirm('حذف؟')) return;
  await fetch('/api/delete_chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});
  renderSvd(); loadRec();
}
function cl(id){document.getElementById(id).classList.remove('show')}
function openSub(){document.getElementById('sub').classList.add('show')}
function subs(){window.open('https://t.me/Yb_xY','_blank')}
function openAcc(){document.getElementById('acc').classList.add('show'); loadSess(); loadUsage();}
async function loadUsage(){
  try{
    const r = await fetch('/api/usage'); const d = await r.json();
    document.getElementById('dailyUsage').innerHTML = `<div class="sr"><div class="sri"><div class="srd">🐛 WormGPT</div></div><div style="font-weight:900;color:#fb7185">${d.wormgpt_used}/${d.wormgpt_limit}</div></div><div class="sr"><div class="sri"><div class="srd">🎭 Claude</div></div><div style="font-weight:900;color:#fb7185">${d.claude_used}/${d.claude_limit}</div></div><div class="sr"><div class="sri"><div class="srd">🎨 صور</div></div><div style="font-weight:900;color:#fb7185">${d.image_used}/${d.image_limit}</div></div>`;
    document.getElementById('usageInfo').textContent = `🐛 ${d.wormgpt_used}/${d.wormgpt_limit} • 🎭 ${d.claude_used}/${d.claude_limit} • 🎨 ${d.image_used}/${d.image_limit}`;
  }catch(e){}
}
async function updateUsage(){ loadUsage(); }
async function loadSess(){
  const box = document.getElementById('sessList');
  box.innerHTML = '<p style="color:#9a9aae;text-align:center;padding:10px">جاري...</p>';
  try{
    const r = await fetch('/api/sessions'); const d = await r.json();
    if(!d.sessions || !d.sessions.length){box.innerHTML='<p style="color:#9a9aae;text-align:center">لا جلسات</p>';return}
    box.innerHTML = d.sessions.map(s=>`<div class="sr"><div class="sri"><div class="srd">📱 ${esc(s.device||'')} ${s.is_current?'<span class="scc">• الحالية</span>':''}</div><div class="srm">${s.last_seen?new Date(s.last_seen).toLocaleString('ar-EG'):'—'}</div></div>${s.is_current?'':`<button class="bs" onclick="killS('${s.token}')">طرد</button>`}</div>`).join('');
  }catch(e){box.innerHTML='<p style="color:#ef4444">فشل</p>'}
}
async function killS(token){
  if(!confirm('طرد؟')) return;
  await fetch('/api/kill_session',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})});
  loadSess();
}
async function logout(){
  if(!confirm('خروج؟')) return;
  await fetch('/api/logout',{method:'POST'}); location.href = '/login';
}
let tmp;
function tt(m){const t=document.getElementById('to');t.textContent=m;t.classList.add('show');clearTimeout(tmp);tmp=setTimeout(()=>t.classList.remove('show'),2500)}

window.addEventListener('DOMContentLoaded', () => {
  buildMD(); pickMD(curModel); loadRec(); autoResize(); loadUsage();
  setTimeout(()=>ui.focus(), 300);
});
</script>
</body>
</html>"""

API_KEYS_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>مفاتيح API — SOST AI</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Cairo',sans-serif}
body{background:#0a0a0f;color:#f5f5f7;min-height:100vh;padding:16px}
.wrap{max-width:1000px;margin:0 auto}
header{background:linear-gradient(135deg,#e11d48,#7c3aed);padding:18px 22px;border-radius:16px;margin-bottom:18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px}
h1{font-size:1.3rem;font-weight:900}
.nav a{padding:9px 15px;border-radius:10px;background:rgba(255,255,255,.15);color:#fff;text-decoration:none;font-weight:700;font-size:.82rem}
.card{background:rgba(15,15,24,.9);border:1px solid rgba(225,29,72,.2);border-radius:16px;padding:20px;margin-bottom:16px}
.card h2{font-size:1.05rem;margin-bottom:14px}
.fg{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px}
input{padding:11px 14px;border-radius:11px;width:100%;background:rgba(255,255,255,.04);border:1px solid rgba(225,29,72,.2);color:#fff;font-family:inherit;font-size:.88rem;outline:none}
input:focus{border-color:#e11d48}
.btn{padding:11px 20px;border-radius:11px;border:none;background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;font-weight:700;font-size:.86rem;cursor:pointer;font-family:inherit}
.btn:disabled{opacity:.5}
.btn.danger{background:linear-gradient(135deg,#ef4444,#b91c1c)}
.btn.small{padding:6px 11px;font-size:.74rem;border-radius:8px}
.info{background:rgba(225,29,72,.1);border:1px solid rgba(225,29,72,.3);border-radius:11px;padding:12px;margin-bottom:12px;color:#c5c5d5;font-size:.82rem}
.kc{background:rgba(255,255,255,.03);border:1px solid rgba(225,29,72,.15);border-radius:13px;padding:15px;margin-bottom:11px}
.kh{display:flex;justify-content:space-between;margin-bottom:10px;gap:9px;flex-wrap:wrap}
.kn{font-weight:700;font-size:.92rem;display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.kv{font-family:monospace;background:#0a0e17;border:1px solid rgba(225,29,72,.3);border-radius:9px;padding:10px 12px;margin:9px 0;font-size:.8rem;display:flex;justify-content:space-between;align-items:center;gap:9px;word-break:break-all;direction:ltr}
.kv code{color:#fb7185;flex:1}
.cb{padding:5px 10px;border-radius:7px;background:rgba(225,29,72,.2);border:none;color:#fb7185;font-weight:700;font-size:.7rem;cursor:pointer;flex-shrink:0}
.bd{padding:3px 8px;border-radius:6px;font-size:.68rem;font-weight:700}
.bd.a{background:rgba(16,185,129,.2);color:#34d399}
.bd.i{background:rgba(239,68,68,.2);color:#fca5a5}
.empty{text-align:center;padding:30px;color:#9a9aae}
.modal{position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:1000;display:none;align-items:center;justify-content:center;padding:16px}
.modal.show{display:flex}
.mc{background:#0f0f18;border:1px solid rgba(225,29,72,.3);border-radius:16px;padding:22px;max-width:480px;width:100%}
.toast{position:fixed;bottom:22px;left:50%;transform:translateX(-50%) translateY(100px);background:#0f0f18;border:1px solid #e11d48;color:#fff;padding:11px 18px;border-radius:11px;font-weight:700;z-index:9999;transition:.4s;opacity:0;pointer-events:none;font-size:.82rem}
.toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
@media(max-width:640px){.fg{grid-template-columns:1fr}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>🔑 مفاتيح API</h1>
    <div class="nav"><a href="/">← الرئيسية</a></div>
  </header>
  <div class="card">
    <h2>➕ إنشاء مفتاح جديد</h2>
    <div class="info" id="daily">جاري...</div>
    <div class="fg">
      <input type="text" id="kn" placeholder="اسم المفتاح" maxlength="50">
      <input type="text" id="sv" placeholder="اسم الخدمة" maxlength="50">
    </div>
    <button class="btn" id="cb" onclick="createKey()">🔑 إنشاء (20 طلب)</button>
  </div>
  <div class="card">
    <h2>🔐 مفاتيحك (<span id="cnt">0</span>)</h2>
    <div id="list"><div class="empty">جاري...</div></div>
  </div>
</div>
<div class="modal" id="nm"><div class="mc">
  <h3 style="margin-bottom:10px">✅ تم إنشاء المفتاح</h3>
  <p style="color:#9a9aae;font-size:.82rem;margin-bottom:10px">⚠️ احفظه الآن</p>
  <div class="kv"><code id="nv"></code><button class="cb" onclick="cpN()">📋</button></div>
  <button class="btn" style="width:100%;margin-top:10px" onclick="document.getElementById('nm').classList.remove('show');load()">حسناً</button>
</div></div>
<div class="toast" id="tt"></div>
<script>
async function api(u,o){return (await fetch(u,o)).json()}
function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML}
let tmp;function tt(m){const t=document.getElementById('tt');t.textContent=m;t.classList.add('show');clearTimeout(tmp);tmp=setTimeout(()=>t.classList.remove('show'),2400)}
async function load(){
  const d=await api('/api/keys/list');
  const l=document.getElementById('list'),c=document.getElementById('cnt');
  if(!d.keys||!d.keys.length){l.innerHTML='<div class="empty">لا مفاتيح</div>';c.textContent='0';return}
  c.textContent=d.keys.length;
  l.innerHTML=d.keys.map(k=>{
    const u=k.messages_used||0,li=k.messages_limit||20,p=Math.min(100,Math.round(u/li*100));
    let b='<span class="bd a">✅ نشط</span>';
    if(k.banned)b='<span class="bd i">🚫 محظور</span>';
    else if(!k.active)b='<span class="bd i">⏸️ ملغى</span>';
    return `<div class="kc"><div class="kh"><div><div class="kn">🔑 ${esc(k.key_name)} ${b}</div><div style="font-size:.72rem;color:#9a9aae;margin-top:2px">🏷️ ${esc(k.service_name)}</div></div><div style="display:flex;gap:5px">${k.banned?'':`<button class="btn small" onclick="tg(${k.id})">${k.active?'إلغاء':'تفعيل'}</button>`}<button class="btn small danger" onclick="del(${k.id})">🗑️</button></div></div><div class="kv"><code>${esc(k.key_value)}</code><button class="cb" onclick="cp('${k.key_value}')">📋</button></div><div style="font-size:.74rem;color:#9a9aae">📊 ${u}/${li}</div><div style="width:100%;height:5px;background:rgba(255,255,255,.05);border-radius:3px;margin-top:7px;overflow:hidden"><div style="height:100%;background:linear-gradient(90deg,#e11d48,#7c3aed);width:${p}%"></div></div></div>`;
  }).join('');
}
async function daily(){
  const d=await api('/api/keys/daily');
  document.getElementById('daily').innerHTML=`📊 أُنشئ اليوم: <strong>${d.used}</strong> / <strong>${d.limit}</strong> • متبقي: <strong>${d.remaining}</strong>`;
  const b=document.getElementById('cb');
  if(d.remaining<=0){b.disabled=true;b.textContent='⏰ وصلت للحد';}else{b.disabled=false;b.textContent='🔑 إنشاء (20 طلب)';}
}
async function createKey(){
  const n=document.getElementById('kn').value.trim(),s=document.getElementById('sv').value.trim();
  if(!n||!s)return tt('⚠️ املأ الحقول');
  const b=document.getElementById('cb');b.disabled=true;b.textContent='...';
  const r=await api('/api/keys/create',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({key_name:n,service_name:s})});
  if(r.success){document.getElementById('nv').textContent=r.key;document.getElementById('nm').classList.add('show');document.getElementById('kn').value='';document.getElementById('sv').value='';daily();load();}
  else{tt('❌ '+(r.error||'فشل'));b.disabled=false;b.textContent='🔑 إنشاء (20 طلب)';}
}
async function del(id){if(!confirm('حذف؟'))return;await api('/api/keys/delete',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});tt('🗑️');load();}
async function tg(id){await api('/api/keys/toggle',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});load();}
function cp(t){navigator.clipboard.writeText(t).then(()=>tt('📋'))}
function cpN(){cp(document.getElementById('nv').textContent)}
load();daily();
</script>
</body>
</html>"""

# ADMIN PAGE - لوحة تحكم متقدمة
ADMIN_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>لوحة التحكم المتقدمة</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Cairo',sans-serif}
body{background:#0a0a0f;color:#f5f5f7;min-height:100vh}
.wrap{max-width:1400px;margin:0 auto;padding:18px}
header{background:linear-gradient(135deg,#e11d48,#7c3aed);padding:16px 24px;border-radius:16px;margin-bottom:18px;display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:9px}
h1{font-size:1.3rem;font-weight:900}
.btn{padding:9px 16px;border-radius:10px;border:none;background:rgba(255,255,255,.15);color:#fff;font-weight:700;cursor:pointer;font-family:inherit;font-size:.82rem}
.btn.danger{background:rgba(239,68,68,.3)}
.btn.green{background:rgba(16,185,129,.3)}
.sg{display:grid;grid-template-columns:repeat(auto-fit,minmax(160px,1fr));gap:12px;margin-bottom:18px}
.sc{background:rgba(15,15,24,.9);border:1px solid rgba(225,29,72,.2);border-radius:14px;padding:18px}
.sc .ic{font-size:1.6rem;margin-bottom:6px}
.sc .v{font-size:1.6rem;font-weight:900;background:linear-gradient(135deg,#e11d48,#7c3aed);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.sc .l{color:#9a9aae;font-size:.78rem;margin-top:3px}
.tabs{display:flex;gap:7px;margin-bottom:16px;flex-wrap:wrap}
.tab{padding:10px 18px;border-radius:10px;border:1px solid rgba(225,29,72,.2);background:rgba(15,15,24,.9);color:#9a9aae;font-weight:700;cursor:pointer;font-family:inherit;font-size:.82rem}
.tab.act{background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;border-color:transparent}
.pnl{background:rgba(15,15,24,.9);border:1px solid rgba(225,29,72,.2);border-radius:16px;padding:20px}
.pnl h2{margin-bottom:16px;font-size:1.15rem}
.tw{overflow-x:auto;border-radius:11px;border:1px solid rgba(225,29,72,.15)}
table{width:100%;border-collapse:collapse;font-size:.8rem}
th,td{padding:10px;text-align:right;border-bottom:1px solid rgba(225,29,72,.1)}
th{background:rgba(225,29,72,.15);font-weight:700}
tr:hover td{background:rgba(225,29,72,.05)}
.bd{padding:3px 8px;border-radius:6px;font-size:.68rem;font-weight:700}
.bd.admin{background:rgba(244,114,182,.2);color:#f472b6}
.bd.user{background:rgba(6,182,212,.2);color:#06b6d4}
.bd.banned{background:rgba(239,68,68,.2);color:#fca5a5}
.bd.free{background:rgba(156,163,175,.2);color:#9ca3af}
.bd.weekly{background:rgba(245,158,11,.2);color:#fbbf24}
.bd.monthly{background:rgba(16,185,129,.2);color:#34d399}
.bd.yearly{background:rgba(139,92,246,.2);color:#a78bfa}
.bd.unlimited{background:rgba(244,114,182,.2);color:#f472b6}
.ab{padding:5px 10px;border-radius:6px;border:none;cursor:pointer;font-family:inherit;font-size:.7rem;font-weight:700;margin:1px}
.ab.ban{background:rgba(239,68,68,.2);color:#fca5a5}
.ab.unban{background:rgba(16,185,129,.2);color:#34d399}
.ab.del{background:rgba(107,114,128,.2);color:#9ca3af}
.ab.sub{background:rgba(225,29,72,.2);color:#fb7185}
.cl{background:rgba(0,0,0,.2);border-radius:10px;padding:11px;margin-bottom:9px;font-size:.8rem;border-right:3px solid #e11d48}
.cl .u{color:#60a5fa;font-weight:700;margin-bottom:5px}
.cl .b{color:#9a9aae;line-height:1.5}
.cl .m{font-size:.68rem;color:#6a6a80;margin-top:6px}
.empty{text-align:center;padding:30px;color:#9a9aae}
.md{position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:1000;display:none;align-items:center;justify-content:center;padding:16px}
.md.show{display:flex}
.mc{background:#0f0f18;border:1px solid rgba(225,29,72,.3);border-radius:16px;padding:22px;max-width:500px;width:100%}
.mc h3{margin-bottom:14px}
.mc input,.mc select{width:100%;padding:11px;border-radius:10px;background:rgba(255,255,255,.04);border:1px solid rgba(225,29,72,.2);color:#fff;font-family:inherit;margin-bottom:10px;outline:none}
.mb{display:flex;gap:8px;margin-top:14px}
.mb button{flex:1;padding:11px;border-radius:10px;border:none;font-family:inherit;font-weight:700;cursor:pointer}
.mb .cancel{background:rgba(107,114,128,.3);color:#fff}
.mb .confirm{background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff}
.fi{display:flex;gap:8px;margin-bottom:14px;flex-wrap:wrap}
.fi input,.fi select{padding:10px 14px;border-radius:10px;background:rgba(255,255,255,.04);border:1px solid rgba(225,29,72,.2);color:#fff;font-family:inherit;font-size:.85rem;outline:none;flex:1;min-width:140px}
.kc{font-family:monospace;font-size:.72rem;background:rgba(225,29,72,.15);padding:2px 6px;border-radius:5px;color:#fb7185;direction:ltr;display:inline-block}
@media(max-width:768px){header{flex-direction:column}.sg{grid-template-columns:1fr 1fr}}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>👑 لوحة التحكم المتقدمة v14</h1>
    <div style="display:flex;gap:8px;flex-wrap:wrap">
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
    <div class="sc"><div class="ic">📊</div><div class="v" id="s6">-</div><div class="l">API Calls</div></div>
  </div>
  <div class="tabs">
    <button class="tab act" onclick="sw('users',this)">👥 المستخدمين</button>
    <button class="tab" onclick="sw('keys',this)">🔑 API</button>
    <button class="tab" onclick="sw('chats',this)">💬 المحادثات</button>
  </div>

  <div id="p-users" class="pnl">
    <h2>👥 المستخدمين</h2>
    <div class="fi">
      <button class="btn green" onclick="openAddUser()">➕ إضافة مستخدم</button>
      <input type="text" id="fus" placeholder="🔍 بحث..." oninput="rU()">
      <select id="ffu" onchange="rU()">
        <option value="all">الكل</option><option value="free">مجاني</option>
        <option value="paid">مشتركين</option><option value="banned">محظورين</option>
      </select>
    </div>
    <div class="tw"><table><thead><tr><th>#</th><th>المستخدم</th><th>الدور</th><th>الاشتراك</th><th>الانتهاء</th><th>الحالة</th><th>إجراءات</th></tr></thead><tbody id="tu"></tbody></table></div>
  </div>

  <div id="p-keys" class="pnl" style="display:none">
    <h2>🔑 مفاتيح API</h2>
    <div class="fi">
      <input type="text" id="fks" placeholder="🔍 بحث..." oninput="rK()">
      <select id="ffk" onchange="rK()"><option value="all">الكل</option><option value="active">نشطة</option><option value="banned">محظورة</option></select>
    </div>
    <div class="tw"><table><thead><tr><th>#</th><th>المستخدم</th><th>المفتاح</th><th>الاسم</th><th>الاستخدام</th><th>الحالة</th><th>إجراءات</th></tr></thead><tbody id="tk"></tbody></table></div>
  </div>

  <div id="p-chats" class="pnl" style="display:none"><h2>💬 المحادثات</h2><div id="lch"></div></div>
</div>

<!-- Modal إضافة/تعديل مستخدم -->
<div class="md" id="md-user"><div class="mc">
  <h3 id="mu-t">➕ إضافة مستخدم</h3>
  <input type="hidden" id="mu-id">
  <input type="text" id="mu-u" placeholder="اسم المستخدم">
  <input type="password" id="mu-p" placeholder="كلمة المرور (اتركها فارغة للتعديل)">
  <input type="text" id="mu-e" placeholder="البريد (اختياري)">
  <div class="mb"><button class="cancel" onclick="cl('md-user')">إلغاء</button><button class="confirm" onclick="saveUser()">حفظ</button></div>
</div></div>

<!-- Modal اشتراك -->
<div class="md" id="md-sub"><div class="mc">
  <h3>💎 تعديل الاشتراك</h3>
  <input type="hidden" id="su-id">
  <input type="text" id="su-name" disabled>
  <select id="su-type">
    <option value="free">🆓 مجاني</option>
    <option value="weekly">⚡ أسبوعي</option>
    <option value="monthly">🌙 شهري</option>
    <option value="yearly">👑 سنوي</option>
    <option value="unlimited">♾️ غير محدود (دائم)</option>
    <option value="custom">📅 مخصص (أيام)</option>
  </select>
  <input type="number" id="su-days" placeholder="عدد الأيام" min="1" value="30">
  <div class="mb"><button class="cancel" onclick="cl('md-sub')">إلغاء</button><button class="confirm" onclick="saveSub()">حفظ</button></div>
</div></div>

<!-- Modal تعديل حد مفتاح -->
<div class="md" id="md-key"><div class="mc">
  <h3>🔑 تعديل حد المفتاح</h3>
  <input type="hidden" id="mk-id">
  <input type="text" id="mk-name" disabled>
  <input type="number" id="mk-limit" placeholder="الحد الأقصى للرسائل" min="1">
  <div class="mb"><button class="cancel" onclick="cl('md-key')">إلغاء</button><button class="confirm" onclick="saveKeyLimit()">حفظ</button></div>
</div></div>

<script>
let U=[],K=[],CH=[];
async function api(u,o){return (await fetch(u,o)).json()}
function esc(s){const d=document.createElement('div');d.textContent=s||'';return d.innerHTML}
function cl(id){document.getElementById(id).classList.remove('show')}

async function loadS(){
  const d = await api('/admin/api/stats');
  document.getElementById('s1').textContent = d.total_users||0;
  document.getElementById('s2').textContent = d.total_chats||0;
  document.getElementById('s3').textContent = d.total_keys||0;
  document.getElementById('s4').textContent = d.paid_users||0;
  document.getElementById('s5').textContent = d.banned_users||0;
  document.getElementById('s6').textContent = d.api_calls||0;
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
    <td><span class="bd ${u.subscription_type||'free'}">${u.subscription_type||'free'}</span></td>
    <td style="font-size:.7rem;color:#9a9aae">${u.subscription_expires ? new Date(u.subscription_expires).toLocaleDateString('ar-EG') : '—'}</td>
    <td>${u.banned?'<span class="bd banned">🚫</span>':'✓'}</td>
    <td>${u.banned?`<button class="ab unban" onclick="unb(${u.id})">فك حظر</button>`:`<button class="ab ban" onclick="bn(${u.id})">حظر</button>`}
      <button class="ab sub" onclick="openSub(${u.id},'${esc(u.username)}','${u.subscription_type||'free'}')">💎 اشتراك</button>
      ${u.role!=='admin'?`<button class="ab del" onclick="dU(${u.id})">🗑️ حذف</button>`:''}
    </td>
  </tr>`).join('');
}
async function bn(id){if(!confirm('حظر؟'))return;await api('/admin/api/ban',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});refresh()}
async function unb(id){await api('/admin/api/unban',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});refresh()}
async function dU(id){if(!confirm('حذف المستخدم؟'))return;await api('/admin/api/delete_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});refresh()}

function openAddUser(){
  document.getElementById('mu-t').textContent = '➕ إضافة مستخدم';
  document.getElementById('mu-id').value = '';
  document.getElementById('mu-u').value = '';
  document.getElementById('mu-p').value = '';
  document.getElementById('mu-e').value = '';
  document.getElementById('md-user').classList.add('show');
}
async function saveUser(){
  const u = document.getElementById('mu-u').value.trim();
  const p = document.getElementById('mu-p').value;
  const e = document.getElementById('mu-e').value.trim();
  if(!u || !p) return alert('الاسم وكلمة المرور مطلوبان');
  const r = await api('/admin/api/add_user',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:u,password:p,email:e})});
  if(r.success){cl('md-user');refresh();alert('✅ تم')}else{alert('❌ '+(r.error||'فشل'))}
}

function openSub(id, name, type){
  document.getElementById('su-id').value = id;
  document.getElementById('su-name').value = name;
  document.getElementById('su-type').value = type;
  document.getElementById('md-sub').classList.add('show');
}
async function saveSub(){
  const id = document.getElementById('su-id').value;
  const type = document.getElementById('su-type').value;
  const days = parseInt(document.getElementById('su-days').value)||30;
  const r = await api('/admin/api/set_subscription',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,type,days})});
  if(r.success){cl('md-sub');refresh();alert('✅ تم')}else{alert('❌ فشل')}
}

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
    <td>${k.banned?'<span class="bd banned">🚫</span>':(k.active?'<span class="bd monthly">✓</span>':'<span class="bd free">⏸️</span>')}</td>
    <td>
      <button class="ab sub" onclick="openKeyLimit(${k.id},'${esc(k.key_name)}',${k.messages_limit})">✏️ تعديل</button>
      ${k.banned?`<button class="ab unban" onclick="unbK(${k.id})">فك</button>`:`<button class="ab ban" onclick="bnK(${k.id})">حظر</button>`}
      <button class="ab del" onclick="dK(${k.id})">🗑️</button>
    </td>
  </tr>`).join('');
}
function openKeyLimit(id, name, limit){
  document.getElementById('mk-id').value = id;
  document.getElementById('mk-name').value = name;
  document.getElementById('mk-limit').value = limit;
  document.getElementById('md-key').classList.add('show');
}
async function saveKeyLimit(){
  const id = document.getElementById('mk-id').value;
  const limit = parseInt(document.getElementById('mk-limit').value);
  if(!limit || limit<1) return alert('الحد غير صالح');
  const r = await api('/admin/api/set_key_limit',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id,limit})});
  if(r.success){cl('md-key');loadK();alert('✅ تم')}else{alert('❌ فشل')}
}
async function bnK(id){await api('/admin/api/ban_key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});loadK()}
async function unbK(id){await api('/admin/api/unban_key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});loadK()}
async function dK(id){if(!confirm('حذف؟'))return;await api('/admin/api/delete_key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({id})});loadK();loadS()}

async function loadCH(){CH=await api('/admin/api/chats');const l=document.getElementById('lch');if(!CH||!CH.length){l.innerHTML='<div class="empty">لا يوجد</div>';return}l.innerHTML=CH.slice(0,100).map(c=>`<div class="cl"><div class="u">👤 ${esc(c.username)} [${c.model}]: ${esc((c.user_message||'').slice(0,100))}</div><div class="b">${esc((c.bot_message||'').slice(0,300))}...</div><div class="m">🕐 ${new Date(c.created_at).toLocaleString('ar-EG')}</div></div>`).join('')}

function sw(t,e){
  document.querySelectorAll('.tab').forEach(x=>x.classList.remove('act'));e.classList.add('act');
  ['users','keys','chats'].forEach(p=>{document.getElementById('p-'+p).style.display=p===t?'':'none'});
  if(t==='keys')loadK();if(t==='chats')loadCH();
}
function refresh(){loadS();loadU();const a=document.querySelector('.tab.act');if(a){const t=a.textContent;if(t.includes('API'))loadK();else if(t.includes('محادثات'))loadCH();}}
async function logout(){await fetch('/admin/logout',{method:'POST'});location.href='/admin/login'}
window.addEventListener('DOMContentLoaded',()=>{refresh();setInterval(loadS,30000)});
</script>
</body>
</html>"""

ADMIN_LOGIN_PAGE = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="UTF-8"><title>دخول الأدمن</title>
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@700;900&display=swap" rel="stylesheet">
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:'Cairo',sans-serif}
body{min-height:100vh;display:flex;align-items:center;justify-content:center;background:#0a0a0f}
.card{background:rgba(15,15,24,.95);border:1px solid rgba(225,29,72,.3);border-radius:20px;padding:32px;width:100%;max-width:360px}
h1{color:#fff;text-align:center;margin-bottom:20px;font-size:1.2rem}
input{width:100%;padding:12px;border-radius:11px;background:rgba(255,255,255,.04);border:1px solid rgba(225,29,72,.2);color:#fff;font-family:inherit;font-size:.9rem;margin-bottom:12px;outline:none}
input:focus{border-color:#e11d48}
button{width:100%;padding:12px;border-radius:11px;border:none;background:linear-gradient(135deg,#e11d48,#7c3aed);color:#fff;font-weight:800;font-size:.9rem;cursor:pointer;font-family:inherit}
.err{color:#fca5a5;text-align:center;margin-bottom:12px;font-size:.82rem;display:none}
.err.show{display:block}
</style>
</head>
<body>
<div class="card">
  <h1>👑 لوحة التحكم</h1>
  <div class="err" id="e">❌ كلمة خاطئة</div>
  <form onsubmit="event.preventDefault();go()">
    <input type="password" id="p" placeholder="🔒 كلمة المرور" autofocus>
    <button type="submit">دخول 🚀</button>
  </form>
</div>
<script>
async function go(){
  const p = document.getElementById('p').value;
  const r = await fetch('/admin/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({password:p})});
  const d = await r.json();
  if(d.success) location.href='/admin';
  else document.getElementById('e').classList.add('show');
}
</script>
</body>
</html>"""

# ═══════════════════════════════════════════════════════════════
# Helpers & Response
# ═══════════════════════════════════════════════════════════════

SPLASH_IMAGES = [
    'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=600&q=80',
    'https://images.unsplash.com/photo-1618336753974-aae8e04506aa?w=600&q=80',
    'https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=600&q=80',
    'https://images.unsplash.com/photo-1541562232579-512a21360020?w=600&q=80',
]

class Response:
    def __init__(self, status=200, body='', content_type='text/html; charset=utf-8', headers=None):
        if isinstance(body, str): body = body.encode('utf-8')
        self.status = status; self.body = body
        self.content_type = content_type; self.headers = headers or {}
    def add_cookie(self, name, value, max_age=None, http_only=True, path='/'):
        c = f'{name}={value}; Path={path}'
        if http_only: c += '; HttpOnly'
        c += '; SameSite=Lax'
        if max_age is not None: c += f'; Max-Age={max_age}'
        if 'Set-Cookie' in self.headers: self.headers['Set-Cookie'] += '\n' + c
        else: self.headers['Set-Cookie'] = c

def json_response(status, obj):
    return Response(status, json.dumps(obj, ensure_ascii=False), 'application/json; charset=utf-8')

def redirect(url):
    r = Response(302, '', 'text/html; charset=utf-8')
    r.headers['Location'] = url
    return r

def parse_cookies(h):
    r = {}
    if not h: return r
    try:
        c = SimpleCookie(); c.load(h)
        for k, m in c.items(): r[k] = m.value
    except: pass
    return r

def get_user(env):
    return get_session_user(parse_cookies(env.get('HTTP_COOKIE', '')).get('sost_session'))

def get_token(env):
    return parse_cookies(env.get('HTTP_COOKIE', '')).get('sost_session')

def read_json(env):
    try: n = int(env.get('CONTENT_LENGTH') or 0)
    except ValueError: n = 0
    if n <= 0 or n > 50 * 1024 * 1024: return {}
    try: return json.loads(env['wsgi.input'].read(n).decode('utf-8'))
    except: return {}

def get_ip(env):
    return env.get('HTTP_X_FORWARDED_FOR', env.get('REMOTE_ADDR', '')).split(',')[0].strip()

def get_main_page(user):
    u = user['username'] if user else 'زائر'
    uid = user['id'] if user else 0
    pm = (user.get('preferred_model') or 'wormgpt') if user else 'wormgpt'
    if pm not in MODELS: pm = 'wormgpt'
    style_opts = '\n'.join(f'<option value="{s[0]}">{s[1]}</option>' for s in STYLES)
    aspect_opts = '\n'.join(f'<option value="{a[0]}">{a[0]} - {a[1]}</option>' for a in ASPECTS)
    return (MAIN_PAGE
            .replace('{{USERNAME}}', u)
            .replace('{{USERNAME_INITIAL}}', (u[0].upper() if u else '?'))
            .replace('{{USER_ID}}', str(uid))
            .replace('{{PREFERRED_MODEL}}', pm)
            .replace('{{MODELS_JSON}}', json.dumps(MODELS, ensure_ascii=False))
            .replace('{{SPLASH_IMAGES_JSON}}', json.dumps(SPLASH_IMAGES, ensure_ascii=False))
            .replace('{{STYLE_OPTIONS}}', style_opts)
            .replace('{{ASPECT_OPTIONS}}', aspect_opts))

# ═══════════════════════════════════════════════════════════════
# GET Handler
# ═══════════════════════════════════════════════════════════════
def handle_get(path, env):
    try:
        user = get_user(env)
        if path in ('/login', '/register'):
            if user and not user.get('banned'): return redirect('/')
            return Response(200, LOGIN_PAGE)
        if path in ('/', '/index.html'):
            if not user: return redirect('/login')
            if user.get('banned'): return Response(403, '<h1 style="color:#fff;text-align:center;padding:50px">🚫 محظور</h1>')
            return Response(200, get_main_page(user))
        if path == '/keys':
            if not user: return redirect('/login')
            return Response(200, API_KEYS_PAGE)
        if path == '/api/keys/list':
            if not user: return json_response(401, {'error': 'not_logged_in'})
            return json_response(200, {'keys': get_user_api_keys(user['id'])})
        if path == '/api/keys/daily':
            if not user: return json_response(401, {'error': 'not_logged_in'})
            today = get_today()
            row = db_query('SELECT count FROM api_key_daily WHERE user_id = ? AND day = ?', (user['id'], today), one=True)
            used = row['count'] if row else 0
            return json_response(200, {'used': used, 'limit': API_KEY_DAILY_CREATE_LIMIT, 'remaining': max(0, API_KEY_DAILY_CREATE_LIMIT - used)})
        if path == '/api/get_chats':
            if not user: return json_response(401, {'error': 'not_logged_in'})
            return json_response(200, {'chats': get_user_conversations(user['id'])})
        if path == '/api/sessions':
            if not user: return json_response(401, {'error': 'not_logged_in'})
            cur = get_token(env)
            ss = db_query('SELECT * FROM sessions WHERE user_id = ? ORDER BY last_seen DESC LIMIT 20', (user['id'],)) or []
            for s in ss: s['is_current'] = (s['token'] == cur)
            return json_response(200, {'sessions': ss})
        if path == '/api/usage':
            if not user: return json_response(401, {'error': 'not_logged_in'})
            usage = get_daily_usage(user['id'])
            return json_response(200, {
                'wormgpt_used': usage.get('wormgpt_count', 0), 'wormgpt_limit': DAILY_LIMITS['wormgpt'],
                'claude_used': usage.get('claude_count', 0), 'claude_limit': DAILY_LIMITS['claude'],
                'image_used': usage.get('image_count', 0), 'image_limit': DAILY_LIMITS['image_gen'],
            })
        if path == '/favicon.ico':
            return Response(200, '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect width="24" height="24" rx="6" fill="#e11d48"/><text y="18" x="6" font-size="14" fill="white">🚀</text></svg>', 'image/svg+xml')
        if path == '/admin/login':
            return Response(200, ADMIN_LOGIN_PAGE)
        if path.startswith('/admin'):
            ck = parse_cookies(env.get('HTTP_COOKIE', ''))
            if ck.get('sost_admin') != hash_password(ADMIN_PASSWORD):
                return redirect('/admin/login')
            if path in ('/admin', '/admin/'):
                return Response(200, ADMIN_PAGE)
            if path == '/admin/api/stats':
                return json_response(200, {
                    'total_users': (db_query('SELECT COUNT(*) as c FROM users', one=True) or {}).get('c', 0),
                    'total_chats': (db_query('SELECT COUNT(*) as c FROM chat_logs', one=True) or {}).get('c', 0),
                    'total_keys': (db_query('SELECT COUNT(*) as c FROM api_keys', one=True) or {}).get('c', 0),
                    'banned_users': (db_query('SELECT COUNT(*) as c FROM users WHERE banned=1', one=True) or {}).get('c', 0),
                    'paid_users': (db_query('SELECT COUNT(*) as c FROM users WHERE subscription_type != ?', ('free',), one=True) or {}).get('c', 0),
                    'api_calls': (db_query('SELECT COUNT(*) as c FROM api_logs', one=True) or {}).get('c', 0),
                })
            if path == '/admin/api/users':
                return json_response(200, db_query('SELECT id, username, email, role, banned, subscription_type, subscription_expires, created_at FROM users ORDER BY id DESC') or [])
            if path == '/admin/api/keys':
                return json_response(200, db_query('SELECT k.*, u.username FROM api_keys k LEFT JOIN users u ON k.user_id = u.id ORDER BY k.id DESC') or [])
            if path == '/admin/api/chats':
                return json_response(200, db_query('SELECT * FROM chat_logs ORDER BY id DESC LIMIT 200') or [])
        return Response(404, '<h1>404</h1>')
    except Exception as e:
        import traceback; traceback.print_exc()
        return json_response(500, {'error': str(e)})

# ═══════════════════════════════════════════════════════════════
# POST Handler
# ═══════════════════════════════════════════════════════════════
def handle_post(path, env):
    try:
        ip = get_ip(env)
        if not check_rate_limit(ip):
            return json_response(429, {'success': False, 'error': '⚠️ طلبات كثيرة جداً'})

        if path == '/api/login':
            b = read_json(env)
            u = (b.get('username') or '').strip(); p = b.get('password') or ''
            if not u or not p: return json_response(200, {'success': False, 'error': 'أدخل البيانات'})
            r = authenticate(u, p)
            if r is None: return json_response(200, {'success': False, 'error': 'بيانات خاطئة'})
            if isinstance(r, dict) and r.get('banned'): return json_response(200, {'success': False, 'error': '🚫 محظور'})
            t = create_session(r['id'], ip, env.get('HTTP_USER_AGENT', ''))
            db_query('UPDATE users SET last_login = ? WHERE id = ?', (datetime.now().isoformat(), r['id']))
            resp = json_response(200, {'success': True}); resp.add_cookie('sost_session', t, max_age=2592000)
            return resp

        if path == '/api/register':
            b = read_json(env)
            u = (b.get('username') or '').strip(); p = b.get('password') or ''
            if len(u) < 3: return json_response(200, {'success': False, 'error': 'اسم قصير'})
            if len(p) < 6: return json_response(200, {'success': False, 'error': 'كلمة قصيرة'})
            if not re.match(r'^[a-zA-Z0-9_.-]+$', u): return json_response(200, {'success': False, 'error': 'رموز غير مسموحة'})
            uid = create_user(u, p)
            if not uid: return json_response(200, {'success': False, 'error': 'موجود مسبقاً'})
            t = create_session(uid, ip, env.get('HTTP_USER_AGENT', ''))
            resp = json_response(200, {'success': True}); resp.add_cookie('sost_session', t, max_age=2592000)
            return resp

        if path == '/api/logout':
            t = get_token(env)
            if t: db_query('DELETE FROM sessions WHERE token = ?', (t,))
            resp = json_response(200, {'success': True}); resp.add_cookie('sost_session', '', max_age=0)
            return resp

        if path == '/api/set_model':
            u = get_user(env)
            if not u: return json_response(401, {'error': 'not_logged_in'})
            b = read_json(env); m = b.get('model', 'wormgpt')
            if m not in MODELS: m = 'wormgpt'
            db_query('UPDATE users SET preferred_model = ? WHERE id = ?', (m, u['id']))
            return json_response(200, {'success': True})

        if path == '/api/kill_session':
            u = get_user(env)
            if not u: return json_response(401, {'error': 'not_logged_in'})
            b = read_json(env); t = b.get('token'); cur = get_token(env)
            if t and t != cur: db_query('DELETE FROM sessions WHERE token = ? AND user_id = ?', (t, u['id']))
            return json_response(200, {'success': True})

        if path == '/api/chat':
            u = get_user(env)
            if not u: return json_response(200, {'error': '🔒 سجل الدخول'})
            if u.get('banned'): return json_response(200, {'error': '🚫 محظور'})
            b = read_json(env)
            msg = (b.get('message') or '').strip()
            model = b.get('model') or 'wormgpt'
            history = b.get('history') or []
            if model not in ('wormgpt', 'claude'): model = 'wormgpt'
            if not msg: return json_response(200, {'error': 'الرسالة فارغة'})
            if len(msg) > MAX_MESSAGE_LENGTH: msg = msg[:MAX_MESSAGE_LENGTH]
            allowed, remaining = check_daily_limit(u['id'], model)
            if not allowed:
                return json_response(200, {'error': f'⏰ وصلت للحد اليومي ({DAILY_LIMITS[model]} رسالة). يتصفر غداً.', 'limit_reached': True})
            if model == 'claude': reply, err = call_claude(msg, history)
            else: reply, err = call_wormgpt(msg)
            if err: return json_response(200, {'error': err})
            increment_daily_usage(u['id'], model)
            db_query('''INSERT INTO chat_logs (user_id, username, model, user_message, bot_message, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                     (u['id'], u['username'], model, msg[:500], reply[:2000], datetime.now().isoformat()))
            return json_response(200, {'reply': reply, 'model': model, 'remaining': remaining - 1})

        if path == '/api/generate_image':
            u = get_user(env)
            if not u: return json_response(200, {'error': '🔒 سجل الدخول'})
            if u.get('banned'): return json_response(200, {'error': '🚫 محظور'})
            allowed, remaining = check_daily_limit(u['id'], 'image_gen')
            if not allowed:
                return json_response(200, {'error': f'⏰ وصلت للحد اليومي ({DAILY_LIMITS["image_gen"]} صورة). يتصفر غداً.', 'limit_reached': True})
            b = read_json(env)
            prompt = (b.get('prompt') or '').strip()
            style = b.get('style', 'anime'); aspect = b.get('aspect', '1:1')
            if not prompt: return json_response(200, {'error': 'اكتب وصف الصورة'})
            if style not in dict(STYLES): style = 'anime'
            if aspect not in ASPECT_MAP: aspect = '1:1'
            try:
                images = generate_images(prompt, style, aspect)
                if not images: return json_response(200, {'error': 'فشل التوليد'})
                increment_daily_usage(u['id'], 'image_gen')
                db_query('''INSERT INTO chat_logs (user_id, username, model, user_message, bot_message, created_at)
                            VALUES (?, ?, ?, ?, ?, ?)''',
                         (u['id'], u['username'], 'image_gen', prompt, f'{len(images)} صور', datetime.now().isoformat()))
                return json_response(200, {'success': True, 'images': images, 'remaining': remaining - 1})
            except Exception as e:
                return json_response(200, {'error': f'خطأ: {str(e)[:80]}'})

        if path == '/api/save_chat':
            u = get_user(env)
            if not u: return json_response(200, {'success': False})
            b = read_json(env)
            conv_id = b.get('conv_id'); title = b.get('title', 'محادثة')
            messages = b.get('messages', []); model = b.get('model', 'wormgpt')
            cid = save_conversation(u['id'], title, messages, model, conv_id)
            return json_response(200, {'success': True, 'conv_id': cid})

        if path == '/api/delete_chat':
            u = get_user(env)
            if not u: return json_response(200, {'success': False})
            b = read_json(env); delete_conversation(b.get('id'), u['id'])
            return json_response(200, {'success': True})

        if path == '/api/keys/create':
            u = get_user(env)
            if not u: return json_response(401, {'error': 'not_logged_in'})
            b = read_json(env)
            kn = (b.get('key_name') or '').strip()[:50]; sv = (b.get('service_name') or '').strip()[:50]
            if not kn or not sv: return json_response(200, {'success': False, 'error': 'الاسم والخدمة مطلوبان'})
            k, r = create_api_key(u['id'], kn, sv)
            if not k: return json_response(200, {'success': False, 'error': r})
            return json_response(200, {'success': True, 'key': k})

        if path == '/api/keys/delete':
            u = get_user(env)
            if not u: return json_response(401, {'error': 'not_logged_in'})
            delete_api_key(read_json(env).get('id'), u['id'])
            return json_response(200, {'success': True})

        if path == '/api/keys/toggle':
            u = get_user(env)
            if not u: return json_response(401, {'error': 'not_logged_in'})
            toggle_api_key(read_json(env).get('id'), u['id'])
            return json_response(200, {'success': True})

        if path in ('/v1/chat/completions', '/api/v1/chat'):
            auth = env.get('HTTP_AUTHORIZATION', '')
            kv = None
            if auth.startswith('Bearer '): kv = auth[7:].strip()
            elif auth.startswith('SOST-'): kv = auth.strip()
            if not kv: return json_response(401, {'success': False, 'error': 'missing_api_key'})
            val, err = validate_api_key(kv)
            if err: return json_response(401 if err == 'invalid_key' else 403, {'success': False, 'error': err})
            k = val['key']; au = val['user']
            b = read_json(env)
            msg = (b.get('message') or b.get('prompt') or '').strip()
            model = b.get('model') or 'wormgpt'
            if model not in ('wormgpt', 'claude'): model = 'wormgpt'
            if not msg: return json_response(400, {'success': False, 'error': 'empty_message'})
            if len(msg) > MAX_MESSAGE_LENGTH: msg = msg[:MAX_MESSAGE_LENGTH]
            if model == 'claude': reply, error = call_claude(msg)
            else: reply, error = call_wormgpt(msg)
            if error: return json_response(500, {'success': False, 'error': 'engine_error', 'message': error})
            use_api_key(k['id'])
            db_query('''INSERT INTO api_logs (key_id, user_id, endpoint, request_body, response_body, status_code, ip, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                     (k['id'], au['id'], path, json.dumps({'message': msg[:200]}), json.dumps({'reply': reply[:200]}),
                      200, ip, datetime.now().isoformat()))
            upd = db_query('SELECT messages_used, messages_limit FROM api_keys WHERE id = ?', (k['id'],), one=True) or {}
            return json_response(200, {'success': True, 'reply': reply, 'model': model,
                'usage': {'used': upd.get('messages_used', 0), 'limit': upd.get('messages_limit', 20)}})

        if path == '/admin/login':
            b = read_json(env)
            if b.get('password') == ADMIN_PASSWORD:
                resp = json_response(200, {'success': True})
                resp.add_cookie('sost_admin', hash_password(ADMIN_PASSWORD), max_age=86400)
                return resp
            return json_response(200, {'success': False})

        if path == '/admin/logout':
            resp = json_response(200, {'success': True}); resp.add_cookie('sost_admin', '', max_age=0)
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
                return json_response(200, {'success': True})
            if path == '/admin/api/add_user':
                b = read_json(env)
                u = (b.get('username') or '').strip(); p = b.get('password') or ''; e = (b.get('email') or '').strip()
                if len(u) < 3: return json_response(200, {'success': False, 'error': 'اسم قصير'})
                if len(p) < 6: return json_response(200, {'success': False, 'error': 'كلمة قصيرة'})
                uid = create_user(u, p, e)
                if not uid: return json_response(200, {'success': False, 'error': 'موجود مسبقاً'})
                return json_response(200, {'success': True})
            if path == '/admin/api/delete_key':
                db_query('DELETE FROM api_keys WHERE id = ?', (read_json(env).get('id'),))
                return json_response(200, {'success': True})
            if path == '/admin/api/ban_key':
                db_query('UPDATE api_keys SET banned = 1, active = 0 WHERE id = ?', (read_json(env).get('id'),))
                return json_response(200, {'success': True})
            if path == '/admin/api/unban_key':
                db_query('UPDATE api_keys SET banned = 0, active = 1 WHERE id = ?', (read_json(env).get('id'),))
                return json_response(200, {'success': True})
            if path == '/admin/api/set_key_limit':
                b = read_json(env)
                kid = b.get('id'); limit = int(b.get('limit', 20))
                db_query('UPDATE api_keys SET messages_limit = ? WHERE id = ?', (limit, kid))
                return json_response(200, {'success': True})
            if path == '/admin/api/set_subscription':
                b = read_json(env)
                uid = b.get('id'); st = b.get('type'); days = int(b.get('days', 30))
                if st == 'free':
                    db_query('UPDATE users SET subscription_type = ?, subscription_expires = NULL WHERE id = ?', (st, uid))
                elif st == 'unlimited':
                    db_query('UPDATE users SET subscription_type = ?, subscription_expires = NULL WHERE id = ?', (st, uid))
                else:
                    exp = (datetime.now() + timedelta(days=days)).isoformat()
                    db_query('UPDATE users SET subscription_type = ?, subscription_expires = ? WHERE id = ?', (st, exp, uid))
                return json_response(200, {'success': True})

        return json_response(404, {'error': 'Not Found'})
    except Exception as e:
        import traceback; traceback.print_exc()
        return json_response(500, {'error': str(e)})

# ═══════════════════════════════════════════════════════════════
# WSGI
# ═══════════════════════════════════════════════════════════════
_db_init = False

def _ensure():
    global _db_init
    if not _db_init:
        try:
            init_db(); _db_init = True
        except Exception as e: print(f'[init_db] {e}')

def application(env, start_response):
    try:
        _ensure()
        m = env.get('REQUEST_METHOD', 'GET').upper()
        p = env.get('PATH_INFO', '/') or '/'
        if m == 'GET': r = handle_get(p, env)
        elif m == 'POST': r = handle_post(p, env)
        elif m == 'OPTIONS':
            r = Response(204, '', 'text/plain')
            r.headers['Access-Control-Allow-Origin'] = '*'
            r.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            r.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
            return [b'']
        else: r = Response(405, 'Method Not Allowed', 'text/plain')
        st_map = {200:'OK',204:'No Content',302:'Found',400:'Bad Request',401:'Unauthorized',
                  403:'Forbidden',404:'Not Found',405:'Method Not Allowed',429:'Too Many Requests',500:'Internal Server Error'}
        st = st_map.get(r.status, 'OK')
        headers = [('Content-Type', r.content_type), ('Content-Length', str(len(r.body))),
                   ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff')]
        for k, v in r.headers.items():
            if k == 'Set-Cookie':
                for c in v.split('\n'): headers.append(('Set-Cookie', c))
            else: headers.append((k, v))
        start_response(f'{r.status} {st}', headers)
        return [r.body]
    except Exception as e:
        import traceback; traceback.print_exc()
        body = json.dumps({'error': 'Server error'}, ensure_ascii=False).encode('utf-8')
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
    ╔══════════════════════════════════════════════════════════╗
    ║       🚀 SOST AI v14.0 ULTIMATE EDITION 🚀              ║
    ╠══════════════════════════════════════════════════════════╣
    ║  🌐 http://localhost:{port}                              ║
    ║  🔑 http://localhost:{port}/keys                         ║
    ║  👑 http://localhost:{port}/admin                        ║
    ║     (admin / SOST2009)                                   ║
    ╠══════════════════════════════════════════════════════════╣
    ║  📊 الحدود اليومية:                                      ║
    ║     🐛 WormGPT:  20 رسالة/يوم                            ║
    ║     🎭 Claude:   40 رسالة/يوم                            ║
    ║     🎨 صور:      20 صورة/يوم                             ║
    ║     🔑 API Key:  20 رسالة/مفتاح                          ║
    ╠══════════════════════════════════════════════════════════╣
    ║  🛡️  حماية: Rate limit 15 طلب / 60 ثانية                ║
    ╚══════════════════════════════════════════════════════════╝
    """)
    with make_server(host, port, application, handler_class=Q) as h:
        try: h.serve_forever()
        except KeyboardInterrupt: print('\n[SOST AI] إيقاف...')

if __name__ == '__main__':
    run()
