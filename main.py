import asyncio, aiosqlite, os, json, logging
from datetime import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from pyrogram import Client
from pyrogram.errors import SessionPasswordNeeded
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# شغل اللوج عشان نشوف كل حاجة
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# ========== الإعدادات - حط بياناتك هنا ==========
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
        await db.execute("""INSERT OR REPLACE INTO users
            (user_id, username, state, temp_data) VALUES (?,?,?,?)""",
            (user_id, username, state, str(temp_data)))
        await db.commit()

async def get_user_state(user_id):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT state, temp_data FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row if row else (None, None)

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
    print(f"!!! START COMMAND RECEIVED FROM {update.effective_user.id} !!!") # للتأكيد
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
    print("Start message sent successfully")

# باقي الدوال زي ما هي... هحطلك المختصر عشان الرسالة
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Message received: {update.message.text}")
    user_id = update.effective_user.id
    username = update.effective_user.username
    state, temp_data = await get_user_state(user_id)
    # ... باقي الكود بتاع handle_message زي ما بعتهولك فوق بالظبط

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    print(f"Button clicked: {query.data}")
    # ... باقي الكود بتاع button_handler زي ما بعتهولك فوق

# ========== تشغيل البوت ==========
app = None

async def main():
    global app
    print("Bot Started...")
    print(f"TOKEN: {TOKEN[:10]}...")
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # لازم await عشان دي async
    await app.bot.delete_webhook(drop_pending_updates=True)
    print("Webhook deleted, starting polling...")
    
    # شغل البوت
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)
    
    # خلي البوت شغال
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
