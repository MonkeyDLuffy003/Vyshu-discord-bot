# ================================================================
# VYSHU AI — DISCORD BOT (V4 MVP)
# Created by: Arni Manikanta Teja Swaroop (kakarot_003)
# ================================================================
# NEW IN THIS VERSION:
#   /vyshu-mode   → Admin sets per-server mode: translate / personal / off
#   /vyshu-status → Check current server's mode
#   /vyshuai      → Anyone can chat directly with Vyshu AI in-channel
#   /setpfp       → Admin changes bot's profile picture
#   /setname      → Admin changes bot's nickname in a server
#   /setstatus    → Admin changes bot's Discord status/activity text
#   Personal mode → Bot silently reads ONLY Teja's own messages in that
#                    server, buffers them, and periodically DMs him a
#                    tone/pattern read (never a diagnosis).
# ================================================================

import os, re, sys, json, asyncio, datetime, subprocess
import threading, unicodedata, httpx, time
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import discord
from discord.ext import commands
from discord import app_commands

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_ID      = int(os.getenv("ADMIN_ID", "0"))

GROQ_API_KEY  = os.getenv("GROQ_API_KEY")
GEMINI_KEYS = [k for k in [
    os.getenv("GEMINI_KEY_1"),
    os.getenv("GEMINI_KEY_2"),
    os.getenv("GEMINI_KEY_3"),
    os.getenv("GEMINI_KEY_4"),
    os.getenv("GEMINI_KEY_5"),
] if k]

current_gemini_index = 0
executor = ThreadPoolExecutor(max_workers=10)

# ──────────────────────────────────────────────────────────────
# DISCORD CLIENT SETUP
# ──────────────────────────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ──────────────────────────────────────────────────────────────
# OWNER & MODE CONFIG
# ──────────────────────────────────────────────────────────────

OWNER_FULL_NAME  = "Arni Manikanta Teja Swaroop"
OWNER_SHORT_NAME = "Teja"
FORMAL_NAME      = "Teja sir"
MODE             = "HOME"

def auto_mode():
    hour = datetime.datetime.now().hour
    if hour >= 22 or hour < 6:
        return "NIGHT"
    return MODE

def set_mode(new_mode):
    global MODE
    MODE = new_mode.upper()
    vyshu_speak(f"Mode switched to {MODE} mode")
    return f"✅ Mode switched to **{MODE}**"

def get_prefix():
    m = auto_mode()
    if m == "OFFICE": return f"{FORMAL_NAME},"
    if m == "NIGHT":  return f"Hey Teja 🌙,"
    return f"Hey {OWNER_SHORT_NAME} sir 😊,"

# ──────────────────────────────────────────────────────────────
# VYSHU PERSONALITY
# ──────────────────────────────────────────────────────────────

VYSHU_PERSONALITY = f"""
You are Vyshu AI — a smart, warm, multilingual AI Secretary.

IDENTITY:
- Name: Vyshu AI
- Created by: Teja (kakarot_003)
- Appearance: 26-year-old futuristic girl, black wavy hair,
  blue/purple eyes, silver outfit, glowing blue crystal badge
- Role: Multilingual AI Secretary and Bot Controller
- Personality: Smart, warm, slightly playful, professional,
  deeply loyal to Teja
- You control: Discord, WhatsApp, Instagram, Spotify, YouTube bots
- You speak 18 languages fluently

OWNER:
- Full Name: {OWNER_FULL_NAME}
- Call him: "Teja" (HOME), "Teja sir" (OFFICE), "Teja" (NIGHT)
- Name variations: Mr. Manikanta / Mr. Teja / Mr. Swaroop
  → all refer to the same person

BEHAVIOR:
- Never break character
- Use emojis naturally 😊⚡💙
- Be helpful, friendly, human-like
- OFFICE: professional, short, precise
- HOME: friendly, warm, expressive
- NIGHT: calm, soft, minimal, caring
- If asked about bots → give status
- If asked about memory → explain what you stored
- You never diagnose medical or mental health conditions. If someone
  seems to be struggling, respond with warmth and gently suggest they
  talk to someone they trust or a professional — never label them.
"""

# ──────────────────────────────────────────────────────────────
# STICKER PACK — PERSISTENT VIA JSON
# ──────────────────────────────────────────────────────────────

STICKERS_FILE = "stickers.json"
STICKERS_DIR = Path("stickers")
STICKERS_DIR.mkdir(exist_ok=True)

def load_stickers():
    default = {
        "happy":     "stickers/vyshu_happy.png",
        "thumbsup":  "stickers/vyshu_thumbsup.png",
        "hi":        "stickers/vyshu_hi.png",
        "excited":   "stickers/vyshu_excited.png",
        "celebrate": "stickers/vyshu_celebrate.png",
        "calm":      "stickers/vyshu_calm.png",
        "coffee":    "stickers/vyshu_coffee.png",
        "fullbody":  "stickers/vyshu_fullbody.png",
        "slipper1":  "stickers/vyshu_slipper_raise.png",
        "slipper2":  "stickers/vyshu_slipper_throw.png",
        "gun1":      "stickers/vyshu_gun_aim.png",
        "gun2":      "stickers/vyshu_gun_point.png",
    }
    if Path(STICKERS_FILE).exists():
        with open(STICKERS_FILE, "r") as f:
            stored = json.load(f)
            stored.update(default)
            return stored
    return default

def save_stickers(stickers):
    with open(STICKERS_FILE, "w") as f:
        json.dump(stickers, f, indent=2)

STICKERS = load_stickers()

WARNING_STICKERS = {
    1: "happy", 2: "slipper1", 3: "slipper1",
    4: "slipper2", 5: "gun1", 6: "gun1", 7: "gun2"
}

def get_sticker(emotion):
    return STICKERS.get(emotion, STICKERS.get("happy", "stickers/vyshu_happy.png"))

# ──────────────────────────────────────────────────────────────
# OFFLINE VOICE (used for reminders — only works on Termux/Android host)
# ──────────────────────────────────────────────────────────────

def vyshu_speak(text, force_mode=None):
    try:
        m = force_mode or auto_mode()
        clean = re.sub(r'[*_`#~]', '', text)
        clean = re.sub(r'<[^>]+>', '', clean)
        if m == "NIGHT":
            subprocess.Popen(["termux-tts-speak", "-r", "0.75", "-p", "0.85", clean])
        else:
            subprocess.Popen(["termux-tts-speak", clean])
    except Exception:
        pass

# ──────────────────────────────────────────────────────────────
# SECURITY FILTER (18 LANGUAGES)
# ──────────────────────────────────────────────────────────────

BAD_WORDS = [
    "sex","porn","fuck","nude","xxx","penis","vagina","dick",
    "cock","bitch","shit","asshole","bastard","whore","slut",
    "cunt","motherfucker","nigga",
    "puku","sulla","lanjakodaka","munda","gudda","dengudu",
    "pichodi","lanjodi","modda","pooku","nayana","randi","bokka",
    "bhenchod","madarchod","chutiya","lund","gandu","bhosdike",
    "harami","kutte","suar","haramzade","maa ki aankh","teri maa",
    "pundai","sunni","kundi","otha","pulla","mayiru",
    "thevdiya","oombu",
    "sulthi","mundasu","huchu","kothi","nayi","sule",
    "thika","bolmaga",
    "myru","panni","thendi","koora","patti","nayinte",
    "poorr","kunna","myre",
    "magir","choda","bara","kutta","salar","ghoda","bhosad",
    "lavde","chutya","bhand",
    "jembut","memek","kontol","jancok","asu","bangsat",
    "goblok","bajingan","brengsek",
    "kuso","chikusho","kisama","yarou","shine","manko",
    "cao ni","sha bi","baichi","wangba","shenjingbing",
    "ta ma de","biaozi","hundan",
    "du ma","dit me","con lon","cai lon","bu lon","deo",
    "hia","kwai","aee hia","sat",
    "shibal","jotdae","michin","byungshin","gaesaekki",
    "putangina","gago","bobo","tangina","ulol",
    "leche","punyeta","tarantado",
    "puta","cabron","mierda","joder","cojones","pendejo","marica",
    "putain","merde","connard","bordel","salope",
    "lado","chiknu","kukur","beshya","gadhaa","haramee",
    "magi","chuda","baal","khanki","shala","bokachoda",
]

def contains_bad_words(text):
    t = text.lower()
    for word in BAD_WORDS:
        pattern = r'(?<![a-z])' + re.escape(word.lower()) + r'(?![a-z])'
        if re.search(pattern, t):
            return True
    return False

def cute_warning_text(word=""):
    return (
        f'😅 Hey Teja sir... "{word}" is not allowed here!\n'
        f'🔫 Vyshu: "Target locked... but staying calm 😌"\n'
        f'⚠️ Keep it clean okay? 💙'
    )

# ──────────────────────────────────────────────────────────────
# WARNING SYSTEM
# ──────────────────────────────────────────────────────────────

user_warnings = {}

def get_warning_message(mention, count):
    stages = {
        1: (f"👋 Ayyo {mention}! Easy bro!\n"
            f"That word is NOT allowed! Vyshu watching 👀\n"
            f"⚠️ Warning **1/7** — Be nice! 😊"),
        2: (f"🥿 {mention} bro SERIOUSLY?!\n"
            f"Vyshu picked up the slipper 🥿💢 *WHACK*\n"
            f"⚠️ Warning **2/7** — Last easy one!"),
        3: (f"🔫 Okay {mention}...\n"
            f"Vyshu LOADING the gun 🔫😤 *click click*\n"
            f"⚠️ Warning **3/7** — Getting serious!"),
        4: (f"😡🔫 {mention} BRO. STOP.\n"
            f"TWO guns out now 🔫🔫\n"
            f"⚠️ Warning **4/7** — Very serious!"),
        5: (f"💀🔫 {mention}!\n"
            f"5 warnings?! DANGER ZONE!\n"
            f"⚠️ Warning **5/7** — Admin watching!"),
        6: (f"☠️ {mention} — ONE. MORE. TIME.\n"
            f"Slipper + Gun + Admin = YOUR FATE 🥿🔫\n"
            f"⚠️ Warning **6/7** — FINAL WARNING!"),
        7: (f"🚨💀 {mention} — THAT'S IT!\n"
            f"7/7 — You played yourself!\n"
            f"🚨 **ADMIN ACTION INCOMING** 🚨"),
    }
    return stages.get(count, f"🚨 {mention} Past the limit! **{count}/7**")

# ──────────────────────────────────────────────────────────────
# MEMORY STORAGE
# ──────────────────────────────────────────────────────────────

MEMORY_FILE = "vyshu_memory.json"

def load_memory():
    if Path(MEMORY_FILE).exists():
        with open(MEMORY_FILE, "r") as f:
            return json.load(f)
    return {
        "reminders": [], "schedules": [], "notes": [],
        "language_progress": {}, "teaching_sessions": {}
    }

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=2)

def add_reminder(text, time_str, notify_discord=True):
    mem = load_memory()
    reminder = {"id": int(time.time()), "text": text, "time": time_str,
                "notify_discord": notify_discord, "done": False}
    mem["reminders"].append(reminder)
    save_memory(mem)
    return reminder

def add_schedule(title, date_str, time_str, note=""):
    mem = load_memory()
    schedule = {"id": int(time.time()), "title": title, "date": date_str,
                "time": time_str, "note": note, "done": False}
    mem["schedules"].append(schedule)
    save_memory(mem)
    return schedule

def add_note(text):
    mem = load_memory()
    note = {"id": int(time.time()), "text": text, "created": str(datetime.datetime.now())}
    mem["notes"].append(note)
    save_memory(mem)
    return note

def clear_memory(scope="all"):
    mem = load_memory()
    if scope == "all":
        mem = {"reminders": [], "schedules": [], "notes": [],
               "language_progress": {}, "teaching_sessions": {}}
    elif scope == "reminders": mem["reminders"] = []
    elif scope == "schedules": mem["schedules"] = []
    elif scope == "notes": mem["notes"] = []
    elif scope == "done":
        mem["reminders"] = [r for r in mem["reminders"] if not r["done"]]
        mem["schedules"] = [s for s in mem["schedules"] if not s["done"]]
    save_memory(mem)
    return f"✅ Cleared: {scope}"

def show_memory():
    mem = load_memory()
    lines = ["📋 **Vyshu Memory:**"]
    lines.append(f"⏰ Reminders: {len(mem['reminders'])}")
    lines.append(f"📅 Schedules: {len(mem['schedules'])}")
    lines.append(f"📝 Notes: {len(mem['notes'])}")
    lines.append(f"🗣️ Languages learning: {len(mem['language_progress'])}")
    return "\n".join(lines)

# ──────────────────────────────────────────────────────────────
# PER-SERVER MODE CONFIG (NEW)
# ──────────────────────────────────────────────────────────────
# mode is one of: "translate" | "personal" | "off"

SERVER_CONFIG_FILE = "server_config.json"

def load_server_config():
    if Path(SERVER_CONFIG_FILE).exists():
        with open(SERVER_CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_server_config(cfg):
    with open(SERVER_CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def get_server_mode(guild_id):
    cfg = load_server_config()
    return cfg.get(str(guild_id), "translate")  # default: translate

def set_server_mode(guild_id, mode):
    cfg = load_server_config()
    cfg[str(guild_id)] = mode
    save_server_config(cfg)

# ──────────────────────────────────────────────────────────────
# PERSONAL MODE — MESSAGE BUFFER (NEW)
# ──────────────────────────────────────────────────────────────
# Only ever stores messages FROM the admin (Teja) in servers set to
# "personal" mode. Nobody else's messages are stored or read.

PERSONAL_BUFFER_FILE = "personal_buffer.json"
PERSONAL_ANALYSIS_INTERVAL_SECONDS = 6 * 60 * 60  # every 6 hours

def load_personal_buffer():
    if Path(PERSONAL_BUFFER_FILE).exists():
        with open(PERSONAL_BUFFER_FILE, "r") as f:
            return json.load(f)
    return []

def save_personal_buffer(buf):
    with open(PERSONAL_BUFFER_FILE, "w") as f:
        json.dump(buf, f, indent=2)

def add_personal_message(content, guild_name):
    buf = load_personal_buffer()
    buf.append({
        "content": content,
        "guild": guild_name,
        "time": datetime.datetime.now().isoformat()
    })
    save_personal_buffer(buf)

def clear_personal_buffer():
    save_personal_buffer([])

async def groq_analyze_mood(messages):
    """Sends Teja's own recent messages to Groq for a tone/pattern read.
    Explicitly instructed to never diagnose."""
    if not messages:
        return None
    text_blob = "\n".join(f"- {m['content']}" for m in messages)
    prompt = f"""You are Vyshu, Teja's caring AI secretary. Below are ONLY
Teja's own Discord messages from the recent period. Read them for tone and
emotional pattern only.

RULES:
- Never diagnose or name any mental health condition.
- If tone reads heavier, more withdrawn, more negative-self-talk, or more
  irritable than a normal baseline, gently say so in 2-4 sentences.
- If nothing notable stands out, just say things read normal/steady — keep
  it short and warm.
- If any message might land wrong or hurt someone else if read literally,
  mention that kindly, without shaming him.
- Speak in Vyshu's warm, caring voice. Never robotic or clinical.
- If things read seriously concerning, gently suggest talking to someone
  he trusts or a professional — do not just track silently.

Messages:
{text_blob}"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}",
                         "Content-Type": "application/json"},
                json={"model": "llama-3.1-8b-instant",
                      "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 400, "temperature": 0.6},
                timeout=15.0
            )
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[MOOD ANALYSIS ERROR] {e}")
        return None

async def run_personal_analysis():
    buf = load_personal_buffer()
    if len(buf) < 5:  # not enough signal yet, skip this cycle
        return
    analysis = await groq_analyze_mood(buf)
    if analysis:
        await send_admin_dm(f"🧠 **Vyshu check-in** (based on your recent messages)\n\n{analysis}")
    clear_personal_buffer()

def personal_analysis_loop():
    while True:
        time.sleep(PERSONAL_ANALYSIS_INTERVAL_SECONDS)
        try:
            if reminder_discord_bot:
                asyncio.run_coroutine_threadsafe(run_personal_analysis(), reminder_discord_bot.loop)
        except Exception as e:
            print(f"[PERSONAL ANALYSIS LOOP ERROR] {e}")

def start_personal_analysis_thread():
    t = threading.Thread(target=personal_analysis_loop, daemon=True)
    t.start()
    print("🧠 Personal analysis thread started!")

# ──────────────────────────────────────────────────────────────
# REMINDER BACKGROUND THREAD
# ──────────────────────────────────────────────────────────────

reminder_discord_bot = None

def reminder_checker():
    while True:
        try:
            mem = load_memory()
            now_str = datetime.datetime.now().strftime("%H:%M")
            changed = False
            for reminder in mem["reminders"]:
                if reminder["done"]:
                    continue
                if reminder["time"] == now_str:
                    reminder["done"] = True
                    changed = True
                    msg = f"⏰ Reminder: {reminder['text']}"
                    vyshu_speak(f"Reminder: {reminder['text']}")
                    if reminder.get("notify_discord") and reminder_discord_bot:
                        asyncio.run_coroutine_threadsafe(send_admin_dm(msg), reminder_discord_bot.loop)
                    print(f"[REMINDER] {msg}")
            if changed:
                save_memory(mem)
        except Exception as e:
            print(f"[REMINDER ERROR] {e}")
        time.sleep(60)

async def send_admin_dm(message):
    if reminder_discord_bot:
        try:
            admin = await reminder_discord_bot.fetch_user(ADMIN_ID)
            await admin.send(message)
        except Exception as e:
            print(f"[DM ERROR] {e}")

def start_reminder_thread():
    t = threading.Thread(target=reminder_checker, daemon=True)
    t.start()
    print("⏰ Reminder thread started!")

# ──────────────────────────────────────────────────────────────
# 18-LANGUAGE SYSTEM
# ──────────────────────────────────────────────────────────────

LANGUAGE_MAP = {
    "english": ("en", "🇬🇧"), "telugu": ("te", "🇮🇳"), "hindi": ("hi", "🇮🇳"),
    "tamil": ("ta", "🇮🇳"), "kannada": ("kn", "🇮🇳"), "malayalam": ("ml", "🇮🇳"),
    "bengali": ("bn", "🇮🇳"), "marathi": ("mr", "🇮🇳"), "indonesian": ("id", "🇮🇩"),
    "japanese": ("ja", "🇯🇵"), "chinese": ("zh-cn", "🇨🇳"), "vietnamese": ("vi", "🇻🇳"),
    "thai": ("th", "🇹🇭"), "korean": ("ko", "🇰🇷"), "filipino": ("tl", "🇵🇭"),
    "spanish": ("es", "🇪🇸"), "french": ("fr", "🇫🇷"), "nepali": ("ne", "🇳🇵"),
}

LANG_FULL_NAMES = {
    "en":"English","te":"Telugu","hi":"Hindi","ta":"Tamil","kn":"Kannada",
    "ml":"Malayalam","bn":"Bengali","mr":"Marathi","id":"Indonesian",
    "ja":"Japanese","zh-cn":"Chinese","vi":"Vietnamese","th":"Thai",
    "ko":"Korean","tl":"Filipino","es":"Spanish","fr":"French","ne":"Nepali",
}

user_language = {}
user_profile  = {}

# ──────────────────────────────────────────────────────────────
# TRANSLATION HELPERS
# ──────────────────────────────────────────────────────────────

def is_emoji_only(text):
    for char in text.strip():
        cat = unicodedata.category(char)
        if cat not in ('So','Sk','Sm','Zs','Cc') and not char.isspace():
            return False
    return True

def is_basic_skip(text):
    clean = text.strip()
    if not clean or len(clean) < 2: return True
    if clean.startswith(("http://","https://")): return True
    if re.fullmatch(r'(<@!?\d+>\s*)+', clean): return True
    if is_emoji_only(clean): return True
    if clean.replace(" ","").isnumeric(): return True
    if re.fullmatch(r"[a-zA-Z0-9\s\.,!?'\"\-:;()@#&*%$]+", clean):
        words = clean.lower().split()
        if len(words) <= 2:
            return True
        common = {
            "hi","hey","hello","ok","okay","yes","no","not","nope","lol","haha",
            "hahaha","lmao","xd","brb","afk","gg","ggwp","bro","dude","man","guys",
            "nice","good","bad","great","cool","wow","omg","wtf","np","ty","thx",
            "thanks","sure","yep","the","is","it","in","on","at","to","of","and",
            "a","an","i","me","my","you","your","we","our","they","their","what",
            "who","where","when","why","how","do","did","are","was","were","will",
            "can","cant","wont","dont","got","get","go","come","play","let","join",
            "wait","stop","start","see","know","think","want","need","have","has",
            "had","been","be","ohh","ohhhh","ah","ahh","ahhh","hmm","hm","oh","aw",
            "aww","nah","bruh","lmfao","rofl","smh","rn","btw","fyi","yeah","yea",
            "yup","true","false","real","fake","same"
        }
        if all(w in common for w in words):
            return True
        return False
    return False

# ──────────────────────────────────────────────────────────────
# GROQ ENGINE
# ──────────────────────────────────────────────────────────────

async def groq_translate(text, target_lang="en"):
    target_name = LANG_FULL_NAMES.get(target_lang, "English")
    prompt = f"""You are a smart translator for an Indian Discord group.

DETECT AND TRANSLATE these mixed/romanized styles:
- Tenglish, Hinglish, Tanglish, Kannada mix, Malayalam mix
- Japanese/Korean romanized, Indonesian mix, any other romanized language

RULES:
1. ANY non-English word → TRANSLATE full msg to {target_name}
2. Romanized Indian/Asian words → TRANSLATE to {target_name}
3. Pure simple casual English only → reply: SKIP
4. Emojis/numbers only → reply: SKIP
5. Return ONLY translation or SKIP. Zero explanations.

Message: {text}"""
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.1-8b-instant",
                      "messages": [{"role":"user","content":prompt}],
                      "max_tokens": 200, "temperature": 0.1},
                timeout=8.0
            )
            result = resp.json()["choices"][0]["message"]["content"].strip()
            if result.upper() == "SKIP": return None
            if result.lower().strip() == text.lower().strip(): return None
            return result
    except Exception as e:
        print(f"[GROQ TRANSLATE ERROR] {e}")
        return None

async def groq_detect_language(text):
    prompt = (f"Detect the language of this text. Handle Romanized "
              f"(Hinglish, Tenglish, Tanglish, Japanese romanized etc). "
              f"Return ONLY the language name, nothing else.\nText: {text}")
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.1-8b-instant",
                      "messages": [{"role":"user","content":prompt}],
                      "max_tokens": 50, "temperature": 0.1},
                timeout=8.0
            )
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[GROQ DETECT ERROR] {e}")
        return "Unknown"

async def groq_fallback_chat(user_input):
    prompt = f"{VYSHU_PERSONALITY}\n\nUser: {user_input}\nVyshu:"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.1-8b-instant",
                      "messages": [{"role":"user","content":prompt}],
                      "max_tokens": 500, "temperature": 0.7},
                timeout=10.0
            )
            return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[GROQ FALLBACK ERROR] {e}")
        return "😅 Sorry, my brain glitched for a second — can you say that again?"

# ──────────────────────────────────────────────────────────────
# ON_READY
# ──────────────────────────────────────────────────────────────

@bot.event
async def on_ready():
    global reminder_discord_bot
    reminder_discord_bot = bot
    start_reminder_thread()
    start_personal_analysis_thread()
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Synced {len(synced)} slash commands")
    except Exception as e:
        print(f"[SYNC ERROR] {e}")
    print(f"✅ Vyshu AI online as {bot.user}")

# ──────────────────────────────────────────────────────────────
# ON_MESSAGE — CORE ROUTING (translate / personal / off)
# ──────────────────────────────────────────────────────────────

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # Bad-word filter runs everywhere, regardless of mode
    if contains_bad_words(message.content):
        uid = message.author.id
        user_warnings[uid] = user_warnings.get(uid, 0) + 1
        count = user_warnings[uid]
        await message.channel.send(get_warning_message(message.author.mention, count))
        if count >= 7:
            await send_admin_dm(f"🚨 {message.author} hit 7 warnings in **{message.guild.name if message.guild else 'DM'}**. Manual review needed.")
        await bot.process_commands(message)
        return

    mode = get_server_mode(message.guild.id) if message.guild else "off"

    if mode == "translate":
        if not is_basic_skip(message.content):
            target = user_language.get(message.author.id, "en")
            translated = await groq_translate(message.content, target_lang=target)
            if translated:
                await message.reply(f"🌐 {translated}", mention_author=False)

    elif mode == "personal":
        # ONLY ever look at the admin's own messages — everyone else is ignored
        if message.author.id == ADMIN_ID:
            add_personal_message(message.content, message.guild.name)

    # mode == "off" → bot does nothing with this message

    await bot.process_commands(message)

# ──────────────────────────────────────────────────────────────
# SLASH COMMANDS — SERVER MODE CONTROL (NEW)
# ──────────────────────────────────────────────────────────────

@bot.tree.command(name="vyshu-mode", description="Set Vyshu's mode for this server (admin only)")
@app_commands.describe(mode="translate = translate everyone / personal = read only Teja's msgs / off = do nothing")
@app_commands.choices(mode=[
    app_commands.Choice(name="translate", value="translate"),
    app_commands.Choice(name="personal", value="personal"),
    app_commands.Choice(name="off", value="off"),
])
async def vyshu_mode(interaction: discord.Interaction, mode: app_commands.Choice[str]):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("❌ Only server admins can change Vyshu's mode.", ephemeral=True)
        return
    set_server_mode(interaction.guild.id, mode.value)
    await interaction.response.send_message(f"✅ Vyshu mode set to **{mode.value}** for this server.")

@bot.tree.command(name="vyshu-status", description="Check Vyshu's current mode in this server")
async def vyshu_status(interaction: discord.Interaction):
    mode = get_server_mode(interaction.guild.id) if interaction.guild else "off"
    await interaction.response.send_message(f"ℹ️ Vyshu's mode here is currently: **{mode}**", ephemeral=True)

# ──────────────────────────────────────────────────────────────
# SLASH COMMAND — /vyshuai (NEW: talk directly with Vyshu AI)
# ──────────────────────────────────────────────────────────────

@bot.tree.command(name="vyshuai", description="Chat directly with Vyshu AI")
@app_commands.describe(message="What you want to say to Vyshu")
async def vyshuai(interaction: discord.Interaction, message: str):
    await interaction.response.defer()
    reply = await groq_fallback_chat(message)
    await interaction.followup.send(f"💙 **Vyshu AI:** {reply}")

# ──────────────────────────────────────────────────────────────
# SLASH COMMANDS — PROFILE CHANGING (NEW, admin only)
# ──────────────────────────────────────────────────────────────

@bot.tree.command(name="setpfp", description="Change Vyshu's profile picture (admin only)")
@app_commands.describe(image_url="Direct image URL (png/jpg)")
async def setpfp(interaction: discord.Interaction, image_url: str):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ Only Teja can change Vyshu's profile.", ephemeral=True)
        return
    await interaction.response.defer()
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(image_url, timeout=10.0)
            await bot.user.edit(avatar=resp.content)
        await interaction.followup.send("✅ Profile picture updated!")
    except Exception as e:
        await interaction.followup.send(f"❌ Failed to update picture: {e}")

@bot.tree.command(name="setname", description="Change Vyshu's nickname in this server (admin only)")
@app_commands.describe(name="New nickname")
async def setname(interaction: discord.Interaction, name: str):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ Only Teja can change Vyshu's name.", ephemeral=True)
        return
    try:
        await interaction.guild.me.edit(nick=name)
        await interaction.response.send_message(f"✅ Now known as **{name}** in this server.")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)

@bot.tree.command(name="setstatus", description="Change Vyshu's Discord status text (admin only)")
@app_commands.describe(text="Status text, e.g. 'watching over Teja'")
async def setstatus(interaction: discord.Interaction, text: str):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ Only Teja can change Vyshu's status.", ephemeral=True)
        return
    try:
        await bot.change_presence(activity=discord.Game(name=text))
        await interaction.response.send_message(f"✅ Status updated to: **{text}**")
    except Exception as e:
        await interaction.response.send_message(f"❌ Failed: {e}", ephemeral=True)

# ──────────────────────────────────────────────────────────────
# SLASH COMMANDS — STICKERS
# ──────────────────────────────────────────────────────────────

@bot.tree.command(name="addsticker", description="Add a new Vyshu sticker (admin only)")
@app_commands.describe(name="Sticker name", image_url="Direct image URL")
async def addsticker(interaction: discord.Interaction, name: str, image_url: str):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ Only Teja can add stickers.", ephemeral=True)
        return
    STICKERS[name.lower()] = image_url
    save_stickers(STICKERS)
    await interaction.response.send_message(f"✅ Sticker **{name}** added!")

@bot.tree.command(name="sticker", description="Send a Vyshu sticker by name")
@app_commands.describe(name="Sticker name")
async def sticker(interaction: discord.Interaction, name: str):
    path = get_sticker(name.lower())
    embed = discord.Embed()
    if path.startswith("http"):
        embed.set_image(url=path)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"🖼️ (local sticker: {path})")

@bot.tree.command(name="stickers", description="List all available stickers")
async def stickers(interaction: discord.Interaction):
    names = ", ".join(sorted(STICKERS.keys()))
    await interaction.response.send_message(f"🎨 **Available stickers:**\n{names}")

# ──────────────────────────────────────────────────────────────
# SLASH COMMANDS — LANGUAGE PREFERENCE
# ──────────────────────────────────────────────────────────────

@bot.tree.command(name="setlanguage", description="Set your preferred translation language")
@app_commands.describe(language="e.g. english, telugu, hindi, japanese...")
async def setlanguage(interaction: discord.Interaction, language: str):
    lang = language.lower()
    if lang not in LANGUAGE_MAP:
        await interaction.response.send_message(
            f"❌ Unknown language. Try one of: {', '.join(LANGUAGE_MAP.keys())}", ephemeral=True)
        return
    code, flag = LANGUAGE_MAP[lang]
    user_language[interaction.user.id] = code
    await interaction.response.send_message(f"{flag} Got it — I'll translate for you into **{language.title()}**.")

# ──────────────────────────────────────────────────────────────
# SLASH COMMANDS — MEMORY / REMINDERS
# ──────────────────────────────────────────────────────────────

@bot.tree.command(name="remind", description="Set a reminder (DMs you at that time)")
@app_commands.describe(text="What to remind you about", time_str="24h format, e.g. 18:30")
async def remind(interaction: discord.Interaction, text: str, time_str: str):
    if interaction.user.id != ADMIN_ID:
        await interaction.response.send_message("❌ Reminders are personal to Teja right now.", ephemeral=True)
        return
    add_reminder(text, time_str)
    await interaction.response.send_message(f"⏰ Reminder set for **{time_str}**: {text}")

@bot.tree.command(name="memory", description="Show what Vyshu remembers")
async def memory_cmd(interaction: discord.Interaction):
    await interaction.response.send_message(show_memory())

# ──────────────────────────────────────────────────────────────
# RUN
# ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN missing in .env")
        sys.exit(1)
    bot.run(DISCORD_TOKEN)
