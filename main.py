import asyncio, aiosqlite, os, json
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ========== الإعدادات ==========
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
DEV_USERNAME = "aabdulrahmaan"
DEVICE_NAME = "iPhone 17 pro" # اسم الجلسة

# ========== قاعدة البيانات ==========
async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            state TEXT,
            temp_data TEXT,
            sessions_count INTEGER DEFAULT 0
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS sessions_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            phone TEXT,
            session_type TEXT,
            created_at TEXT
        )""")
        await db.commit()

async def set_user_state(user_id, username, state, temp_data=None):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""INSERT OR REPLACE INTO users
            (user_id, username, state, temp_data) VALUES (?,?,?,?)""",
            (user_id, username, state, str(temp_data)))
        await db.commit()

async def get_user_state(user_id):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT state, temp_data FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row if row else (None, None)

async def log_session(user_id, phone, session_type):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""INSERT INTO sessions_log (user_id, phone, session_type, created_at)
            VALUES (?,?,?,?)""", (user_id, phone, session_type, datetime.now().isoformat()))
        await db.execute("UPDATE users SET sessions_count = sessions_count + 1 WHERE user_id=?", (user_id,))
        await db.commit()

        # نسخة احتياطية للأدمن
        if ADMIN_ID:
            backup_text = f"🔐 <b>نسخة احتياطية جديدة</b>\n\n"
            backup_text += f"👤 المستخدم: <code>{user_id}</code>\n"
            backup_text += f"📱 الرقم: <code>{phone}</code>\n"
            backup_text += f"⚙️ النوع: {session_type}\n"
            backup_text += f"⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            try:
                await app.bot.send_message(ADMIN_ID, backup_text, parse_mode='HTML')
            except: pass

# ========== رسالة الترحيب بإيموجي بريميوم ==========
WELCOME_MSG = """
<b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b><b> ‹ </b><b>{name}</b><b> › </b><b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b>

<b><tg-emoji emoji-id="5796499583647359561">📌</tg-emoji></b><b> 𝗦𝗘𝗦𝗜𝗢𝗡 𝗘𝗫𝗧𝗥𝗔𝗖𝗧𝗢𝗥 𝗣𝗥𝗢 </b><b><tg-emoji emoji-id="5796499583647359561">📌</tg-emoji></b>

<b><tg-emoji emoji-id="5798941981224737816">🚀</tg-emoji></b><b> أهلاً بك في أقوى بوت استخراج جلسات </b><b><tg-emoji emoji-id="5798941981224737816">🚀</tg-emoji></b>

<b><tg-emoji emoji-id="5794353922816429699">🛡️</tg-emoji></b><b> ايديك : <code>{user_id}</code> </b><b><tg-emoji emoji-id="5794353922816429699">🛡️</tg-emoji></b>

<b><tg-emoji emoji-id="5796526727840669257">🎲</tg-emoji></b><b> استخراج تليثون + بايوجرام </b><b><tg-emoji emoji-id="5796526727840669257">🎲</tg-emoji></b>

<b><tg-emoji emoji-id="5794353922816429699">⚡</tg-emoji></b><b> تحويل فوري بين المكتبتين </b><b><tg-emoji emoji-id="5794353922816429699">⚡</tg-emoji></b>

<b><tg-emoji emoji-id="5798740083085231609">📊</tg-emoji></b><b> إحصائيات + نسخ احتياطي </b><b><tg-emoji emoji-id="5798740083085231609">📊</tg-emoji></b>
"""

# ========== Start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await set_user_state(user.id, user.username, None)

    welcome_text = WELCOME_MSG.format(name=user.first_name, user_id=user.id)
    keyboard = [
        [InlineKeyboardButton("📱 استخراج جلسة تليثون", callback_data="extract_telethon")],
        [InlineKeyboardButton("📱 استخراج جلسة بايوجرام", callback_data="extract_pyro")],
        [InlineKeyboardButton("🔄 تليثون → بايوجرام", callback_data="tele_to_pyro")],
        [InlineKeyboardButton("🔄 بايوجرام → تليثون", callback_data="pyro_to_tele")],
        [InlineKeyboardButton("📊 إحصائياتي", callback_data="my_stats")],
        [InlineKeyboardButton("👨‍💻 المبرمج", url=f"https://t.me/{DEV_USERNAME}")]
    ]
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")])

    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ========== دوال التحويل ==========
async def telethon_to_pyrogram(session_string):
    tele_client = TelegramClient(StringSession(session_string), API_ID, API_HASH, device_model=DEVICE_NAME)
    await tele_client.connect()
    me = await tele_client.get_me()

    pyro_client = Client(name="temp", api_id=API_ID, api_hash=API_HASH, session_string=session_string, in_memory=True, device_model=DEVICE_NAME)
    await pyro_client.connect()
    new_session = await pyro_client.export_session_string()
    await pyro_client.disconnect()
    await tele_client.disconnect()
    return new_session, me.phone

async def pyrogram_to_telethon(session_string):
    pyro_client = Client(name="temp", api_id=API_ID, api_hash=API_HASH, session_string=session_string, in_memory=True, device_model=DEVICE_NAME)
    await pyro_client.connect()
    me = await pyro_client.get_me()

    tele_client = TelegramClient(StringSession(session_string), API_ID, API_HASH, device_model=DEVICE_NAME)
    await tele_client.connect()
    new_session = tele_client.session.save()
    await tele_client.disconnect()
    await pyro_client.disconnect()
    return new_session, me.phone_number

# ========== استقبال الرسائل ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    state, temp_data = await get_user_state(user_id)

    if state == "awaiting_phone_telethon":
        phone = update.message.text.strip()
        try:
            client = TelegramClient(StringSession(), API_ID, API_HASH, device_model=DEVICE_NAME)
            await client.connect()
            sent = await client.send_code_request(phone)
            await set_user_state(user_id, username, "awaiting_code_telethon", f"{phone}|{sent.phone_code_hash}|{client.session.save()}")
            text = "<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> ارسل الكود اللي وصلك </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>"
            await update.message.reply_text(text, parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"<b>❌ خطأ: {str(e)}</b>", parse_mode='HTML')
            await set_user_state(user_id, username, None)

    elif state and state.startswith("awaiting_code_telethon"):
        phone, phone_hash, session = temp_data.split("|")
        code = update.message.text.strip()
        try:
            client = TelegramClient(StringSession(session), API_ID, API_HASH, device_model=DEVICE_NAME)
            await client.connect()
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_hash)
            new_session = client.session.save()
            await client.disconnect()
            await log_session(user_id, phone, "Telethon")

            text = "<b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b><b> تم استخراج جلسة تليثون </b><b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b>\n\n"
            text += f"<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> الرقم: <code>{phone}</code> </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>\n"
            text += f"<b><tg-emoji emoji-id='5798740083085231609'>📱</tg-emoji></b><b> الجهاز: <code>{DEVICE_NAME}</code> </b><b><tg-emoji emoji-id='5798740083085231609'>📱</tg-emoji></b>\n\n"
            text += f"<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> الجلسة: </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n"
            text += f"<code>{new_session}</code>"

            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            await set_user_state(user_id, username, None)
        except SessionPasswordNeededError:
            await set_user_state(user_id, username, f"awaiting_2fa_telethon", f"{phone}|{session}")
            text = "<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> الحساب عليه تحقق بخطوتين </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n\n"
            text += "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> ارسل باسورد التحقق </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>"
            await update.message.reply_text(text, parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"<b>❌ الكود غلط: {str(e)}</b>", parse_mode='HTML')

    elif state and state.startswith("awaiting_2fa_telethon"):
        phone, session = temp_data.split("|")
        password = update.message.text.strip()
        try:
            client = TelegramClient(StringSession(session), API_ID, API_HASH, device_model=DEVICE_NAME)
            await client.connect()
            await client.sign_in(password=password)
            new_session = client.session.save()
            await client.disconnect()
            await log_session(user_id, phone, "Telethon")

            text = "<b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b><b> تم استخراج جلسة تليثون </b><b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b>\n\n"
            text += f"<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> الرقم: <code>{phone}</code> </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>\n"
            text += f"<b><tg-emoji emoji-id='5798740083085231609'>📱</tg-emoji></b><b> الجهاز: <code>{DEVICE_NAME}</code> </b><b><tg-emoji emoji-id='5798740083085231609'>📱</tg-emoji></b>\n\n"
            text += f"<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> الجلسة: </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n"
            text += f"<code>{new_session}</code>"

            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            await set_user_state(user_id, username, None)
        except Exception as e:
            await update.message.reply_text(f"<b>❌ الباسورد غلط: {str(e)}</b>", parse_mode='HTML')

    elif state == "awaiting_phone_pyro":
        phone = update.message.text.strip()
        try:
            client = Client(name="temp", api_id=API_ID, api_hash=API_HASH, in_memory=True, device_model=DEVICE_NAME)
            await client.connect()
            sent = await client.send_code(phone)
            await set_user_state(user_id, username, f"awaiting_code_pyro", f"{phone}|{sent.phone_code_hash}|{await client.export_session_string()}")
            await client.disconnect()
            text = "<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> ارسل الكود اللي وصلك </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>"
            await update.message.reply_text(text, parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"<b>❌ خطأ: {str(e)}</b>", parse_mode='HTML')
            await set_user_state(user_id, username, None)

    elif state and state.startswith("awaiting_code_pyro"):
        phone, phone_hash, session = temp_data.split("|")
        code = update.message.text.strip()
        try:
            client = Client(name="temp", api_id=API_ID, api_hash=API_HASH, session_string=session, in_memory=True, device_model=DEVICE_NAME)
            await client.connect()
            await client.sign_in(phone, phone_hash, code)
            new_session = await client.export_session_string()
            await client.disconnect()
            await log_session(user_id, phone, "Pyrogram")

            text = "<b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b><b> تم استخراج جلسة بايوجرام </b><b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b>\n\n"
            text += f"<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> الرقم: <code>{phone}</code> </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>\n"
            text += f"<b><tg-emoji emoji-id='5798740083085231609'>📱</tg-emoji></b><b> الجهاز: <code>{DEVICE_NAME}</code> </b><b><tg-emoji emoji-id='5798740083085231609'>📱</tg-emoji></b>\n\n"
            text += f"<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> الجلسة: </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n"
            text += f"<code>{new_session}</code>"

            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            await set_user_state(user_id, username, None)
        except SessionPasswordNeeded:
            await set_user_state(user_id, username, f"awaiting_2fa_pyro", f"{phone}|{session}")
            text = "<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> الحساب عليه تحقق بخطوتين </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n\n"
            text += "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> ارسل باسورد التحقق </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>"
            await update.message.reply_text(text, parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"<b>❌ الكود غلط: {str(e)}</b>", parse_mode='HTML')

    elif state and state.startswith("awaiting_2fa_pyro"):
        phone, session = temp_data.split("|")
        password = update.message.text.strip()
        try:
            client = Client(name="temp", api_id=API_ID, api_hash=API_HASH, session_string=session, in_memory=True, device_model=DEVICE_NAME)
            await client.connect()
            await client.check_password(password)
            new_session = await client.export_session_string()
            await client.disconnect()
            await log_session(user_id, phone, "Pyrogram")

            text = "<b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b><b> تم استخراج جلسة بايوجرام </b><b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b>\n\n"
            text += f"<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> الرقم: <code>{phone}</code> </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>\n"
            text += f"<b><tg-emoji emoji-id='5798740083085231609'>📱</tg-emoji></b><b> الجهاز: <code>{DEVICE_NAME}</code> </b><b><tg-emoji emoji-id='5798740083085231609'>📱</tg-emoji></b>\n\n"
            text += f"<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> الجلسة: </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n"
            text += f"<code>{new_session}</code>"

            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            await set_user_state(user_id, username, None)
        except Exception as e:
            await update.message.reply_text(f"<b>❌ الباسورد غلط: {str(e)}</b>", parse_mode='HTML')

    elif state == "awaiting_tele_session":
        session = update.message.text.strip()
        try:
            new_session, phone = await telethon_to_pyrogram(session)
            await log_session(user_id, phone, "Tele→Pyro")
            text = "<b><tg-emoji emoji-id='5794353922816429699'>⚡</tg-emoji></b><b> تم التحويل بنجاح </b><b><tg-emoji emoji-id='5794353922816429699'>⚡</tg-emoji></b>\n\n"
            text += f"<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> الرقم: <code>{phone}</code> </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>\n\n"
            text += f"<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> جلسة بايوجرام: </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n"
            text += f"<code>{new_session}</code>"

            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            await set_user_state(user_id, username, None)
        except Exception as e:
            await update.message.reply_text(f"<b>❌ خطأ في التحويل: {str(e)}</b>", parse_mode='HTML')
            await set_user_state(user_id, username, None)

    elif state == "awaiting_pyro_session":
        session = update.message.text.strip()
        try:
            new_session, phone = await pyrogram_to_telethon(session)
            await log_session(user_id, phone, "Pyro→Tele")
            text = "<b><tg-emoji emoji-id='5794353922816429699'>⚡</tg-emoji></b><b> تم التحويل بنجاح </b><b><tg-emoji emoji-id='5794353922816429699'>⚡</tg-emoji></b>\n\n"
            text += f"<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> الرقم: <code>{phone}</code> </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>\n\n"
            text += f"<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> جلسة تليثون: </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n"
            text += f"<code>{new_session}</code>"

            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            await set_user_state(user_id, username, None)
        except Exception as e:
            await update.message.reply_text(f"<b>❌ خطأ في التحويل: {str(e)}</b>", parse_mode='HTML')
            await set_user_state(user_id, username, None)

# ========== الأزرار ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username
    data = query.data

    if data == "back_main":
        await start(update, context)

    elif data == "extract_telethon":
        await set_user_state(user_id, username, "awaiting_phone_telethon")
        text = "<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> ارسل رقم الهاتف مع كود الدولة </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>\n\n"
        text += "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> مثال: +201234567890 </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>"
        await query.message.edit_text(text, parse_mode='HTML')

    elif data == "extract_pyro":
        await set_user_state(user_id, username, "awaiting_phone_pyro")
        text = "<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> ارسل رقم الهاتف مع كود الدولة </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>\n\n"
        text += "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> مثال: +201234567890 </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>"
        await query.message.edit_text(text, parse_mode='HTML')

    elif data == "tele_to_pyro":
        await set_user_state(user_id, username, "awaiting_tele_session")
        text = "<b><tg-emoji emoji-id='5794353922816429699'>⚡</tg-emoji></b><b> ارسل جلسة تليثون للتحويل </b><b><tg-emoji emoji-id='5794353922816429699'>⚡</tg-emoji></b>"
        await query.message.edit_text(text, parse_mode='HTML')

    elif data == "pyro_to_tele":
        await set_user_state(user_id, username, "awaiting_pyro_session")
        text = "<b><tg-emoji emoji-id='5794353922816429699'>⚡</tg-emoji></b><b> ارسل جلسة بايوجرام للتحويل </b><b><tg-emoji emoji-id='5794353922816429699'>⚡</tg-emoji></b>"
        await query.message.edit_text(text, parse_mode='HTML')

    elif data == "my_stats":
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("SELECT sessions_count FROM users WHERE user_id=?", (user_id,)) as cur:
                row = await cur.fetchone()
                count = row[0] if row else 0
        text = f"<b><tg-emoji emoji-id='5798740083085231609'>📊</tg-emoji></b><b> إحصائياتك </b><b><tg-emoji emoji-id='5798740083085231609'>📊</tg-emoji></b>\n\n"
        text += f"<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> عدد الجلسات المستخرجة: <code>{count}</code> </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    elif data == "admin_panel" and user_id == ADMIN_ID:
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cur:
                users_count = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM sessions_log") as cur:
                sessions_count = (await cur.fetchone())[0]

        text = "<b><tg-emoji emoji-id='5798740083085231609'>⚙️</tg-emoji></b><b> لوحة الأدمن </b><b><tg-emoji emoji-id='5798740083085231609'>⚙️</tg-emoji></b>\n\n"
        text += f"<b><tg-emoji emoji-id='5794353922816429699'>👥</tg-emoji></b><b> عدد المستخدمين: <code>{users_count}</code> </b><b><tg-emoji emoji-id='5794353922816429699'>👥</tg-emoji></b>\n"
        text += f"<b><tg-emoji emoji-id='5796526727840669257'>🔐</tg-emoji></b><b> عدد الجلسات: <code>{sessions_count}</code> </b><b><tg-emoji emoji-id='5796526727840669257'>🔐</tg-emoji></b>\n"
        text += f"<b><tg-emoji emoji-id='5798482080421649554'>📱</tg-emoji></b><b> اسم الجهاز: <code>{DEVICE_NAME}</code> </b><b><tg-emoji emoji-id='5798482080421649554'>📱</tg-emoji></b>"

        keyboard = [
            [InlineKeyboardButton("📥 تصدير النسخ الاحتياطي", callback_data="export_backup")],
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

    elif data == "export_backup" and user_id == ADMIN_ID:
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("SELECT * FROM sessions_log ORDER BY id DESC LIMIT 50") as cur:
                rows = await cur.fetchall()

        backup_text = "<b>📦 آخر 50 جلسة مستخرجة</b>\n\n"
        for row in rows:
            backup_text += f"<code>{row[2]}</code> - {row[3]} - {row[4][:10]}\n"

        await query.message.reply_text(backup_text, parse_mode='HTML')

# ========== تشغيل البوت ==========
app = None

def main():
    global app
    print("Bot Started...")
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app = Application.builder().token(TOKEN).build()

if __name__ == "__main__":
    asyncio.run(init_db())
    main()
