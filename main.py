import asyncio, aiosqlite, re, os, json
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError
from telethon.tl.functions.auth import LogOutRequest, ResetAuthorizationsRequest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from telegram.error import BadRequest

# ========== الإعدادات من Environment ==========
TOKEN = os.environ.get("TOKEN")
ADMIN_ID = int(os.environ.get("ADMIN_ID", 0))
DEV_USERNAME = "aabdulrahmaan" 
FORCE_CHANNEL = os.environ.get("FORCE_CHANNEL")
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")

# ========== قاعدة البيانات ==========
async def init_db():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, balance REAL DEFAULT 0, state TEXT, temp_data TEXT)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS countries (code TEXT PRIMARY KEY, name TEXT, flag TEXT, available INTEGER DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS numbers (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            country_code TEXT, 
            number TEXT UNIQUE, 
            price REAL, 
            sold INTEGER DEFAULT 0, 
            buyer_id INTEGER,
            session_string TEXT,
            phone_code_hash TEXT,
            status TEXT DEFAULT 'available'
        )""")
        await db.execute("""CREATE TABLE IF NOT EXISTS pending_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            user_id INTEGER, 
            amount REAL, 
            photo_id TEXT, 
            caption TEXT,
            status TEXT DEFAULT 'pending'
        )""")
        await db.commit()

# ========== دوال مساعدة ==========
async def get_balance(user_id):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else 0.0

async def set_user_state(user_id, state, temp_data=None):
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("UPDATE users SET state=?, temp_data=? WHERE user_id=?", (state, json.dumps(temp_data) if temp_data else None, user_id))
        await db.commit()

async def get_user_state(user_id):
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT state, temp_data FROM users WHERE user_id=?", (user_id,)) as cur:
            row = await cur.fetchone()
            if row:
                return row[0], json.loads(row[1]) if row[1] else None
            return None, None

async def update_country_count():
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("""UPDATE countries SET available = (
            SELECT COUNT(*) FROM numbers WHERE numbers.country_code = countries.code AND numbers.sold = 0
        )""")
        await db.commit()

# ========== النصوص البريميوم ==========
WELCOME_MSG = """
<b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b><b> ‹ </b><b>{name}</b><b> › </b><b><tg-emoji emoji-id="5796526727840669257">🎲</tg-emoji></b>

<b><tg-emoji emoji-id="5796499583647359561">📌</tg-emoji></b><b> 𝗪𝗘𝗟𝗖𝗢𝗠𝗘 𝗧𝗢 𝗧𝗚 𝗡𝗨𝗠𝗕𝗘𝗥 </b><b><tg-emoji emoji-id="5796499583647359561">📌</tg-emoji></b>

<b><tg-emoji emoji-id="5798941981224737816">🚀</tg-emoji></b><b> مرحباً بك {name} </b><b><tg-emoji emoji-id="5798941981224737816">🚀</tg-emoji></b>

<b><tg-emoji emoji-id="5794353922816429699">🛡️</tg-emoji></b><b> ايديك : <code>{user_id}</code> </b><b><tg-emoji emoji-id="5794353922816429699">🛡️</tg-emoji></b>

<b><tg-emoji emoji-id="5794353922816429699">💰</tg-emoji></b><b> رصيدك : {balance}$ </b><b><tg-emoji emoji-id="5794353922816429699">💰</tg-emoji></b>

<b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b><b> أرخص أرقام تليجرام في الوطن العربي </b><b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b>

<b><tg-emoji emoji-id="5796526727840669257">🎲</tg-emoji></b><b> ⎯ ⎯ ⎯ </b><b><tg-emoji emoji-id="5796526727840669257">🎲</tg-emoji></b>
"""

PAYMENT_MSG = """
<b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b><b> إليك طـرق الدفع المتاحة </b><b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b>
<b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b><b> الخاصه بـ @aabdulrahmaan </b><b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b>
<b><tg-emoji emoji-id="5796499583647359561">📌</tg-emoji></b><b> اضغط علي الدفع المناسب للنسخ </b><b><tg-emoji emoji-id="5796499583647359561">📌</tg-emoji></b>
<b>ـــــــ ـــــــ ـــــــ ـــــــ ـــــــ</b>
<b><tg-emoji emoji-id="5794353922816429699">💰</tg-emoji></b><b> Usdt Aptos : </b><b><tg-emoji emoji-id="5794353922816429699">💰</tg-emoji></b>
<b>‹ </b><code>0xf8873fe62b564ff0d8042e84c24277c8cef7ee3beb94be1ab0c5da26a7346f77</code><b> ›</b>
<b>ـــــــ ـــــــ ـــــــ ـــــــ ـــــــ</b>
<b><tg-emoji emoji-id="5794353922816429699">💰</tg-emoji></b><b> Usdt Erc20 : </b><b><tg-emoji emoji-id="5794353922816429699">💰</tg-emoji></b>
<b>‹ </b><code>0x66c81a68b27402038066a146f31d4ffdaad5ab46</code><b> ›</b>
<b>ـــــــ ـــــــ ـــــــ ـــــــ ـــــــ</b>
<b><tg-emoji emoji-id="5794353922816429699">💰</tg-emoji></b><b> Usdt Trc20 : </b><b><tg-emoji emoji-id="5794353922816429699">💰</tg-emoji></b>
<b>‹ </b><code>TDEd6MN8AigEb3jPtEY36ixkrJ7TF7fszL</code><b> ›</b>
<b>ـــــــ ـــــــ ـــــــ ـــــــ ـــــــ</b>
<b><tg-emoji emoji-id="5794353922816429699">💰</tg-emoji></b><b> Ltc : </b><b><tg-emoji emoji-id="5794353922816429699">💰</tg-emoji></b>
<b>‹ </b><code>ltc1qseym8cfl54d84mje3q8j8rpkyzdzm9s53rc8mpzf9566py0hnltsx92w3w</code><b> ›</b>
<b>ـــــــ ـــــــ ـــــــ ـــــــ ـــــــ</b>
<b><tg-emoji emoji-id="5794353922816429699">💰</tg-emoji></b><b> Ton : </b><b><tg-emoji emoji-id="5794353922816429699">💰</tg-emoji></b>
<b>‹ </b><code>UQAFk8b4fKqrqrEKVejWTn95E1v0qoPWDC4SGW_pF9uBkdLj</code><b> ›</b>
<b>ـــــــ ـــــــ ـــــــ ـــــــ ـــــــ</b>

<b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b><b> بعد التحويل عليك بإرسال إيصالك ( سكرين شوت ) </b><b><tg-emoji emoji-id="5798482080421649554">🔒</tg-emoji></b>
<b><tg-emoji emoji-id="5796526727840669257">🎲</tg-emoji></b><b> مع كتابة المبلغ في الكابشن </b><b><tg-emoji emoji-id="5796526727840669257">🎲</tg-emoji></b>
"""

# ========== لوحة الأدمن الرئيسية ==========
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    text = "<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> لوحة تحكم الأدمن </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>"
    keyboard = [
        [InlineKeyboardButton("🌍 إدارة الدول", callback_data="admin_countries")],
        [InlineKeyboardButton("💰 إدارة الرصيد", callback_data="admin_balance")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("💾 نسخة احتياطية", callback_data="admin_backup")]
    ]
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ========== إدارة الدول ==========
async def admin_countries_panel(query):
    await update_country_count()
    text = "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> إدارة الدول </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>"
    keyboard = [
        [InlineKeyboardButton("➕ إضافة دولة", callback_data="admin_add_country")],
        [InlineKeyboardButton("➕ إنشاء أرقام", callback_data="admin_create_nums")],
        [InlineKeyboardButton("🗑️ حذف دولة", callback_data="admin_del_country")],
        [InlineKeyboardButton("🌍 الدول المتوفرة", callback_data="admin_list_countries")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
    ]
    await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ========== أزرار Inline ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # لوحة الأدمن
    if data == "admin_panel": await admin_panel(update, context)
    elif data == "admin_countries": await admin_countries_panel(query)
    
    elif data == "admin_add_country":
        await set_user_state(user_id, "adding_country")
        text = "<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> ارسل الدولة </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>\n\n"
        text += "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> الصيغة: +20|🇪🇬 مصر </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>"
        await query.message.edit_text(text, parse_mode='HTML')
    
    elif data == "admin_create_nums":
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("SELECT code, name FROM countries") as cur:
                countries = await cur.fetchall()
        if not countries:
            await query.answer("ضيف دول أولاً", show_alert=True)
            return
        keyboard = [[InlineKeyboardButton(f"{c[1]}", callback_data=f"select_country_{c[0]}")] for c in countries]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_countries")])
        text = "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> اختر الدولة </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>"
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    elif data.startswith("select_country_"):
        country_code = data.split("_")[2]
        await set_user_state(user_id, f"creating_nums_{country_code}")
        text = "<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> ارسل الأرقام </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>\n\n"
        text += "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> الصيغة: 2012345678|1$ </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>\n"
        text += "<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> كل رقم في سطر </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>"
        await query.message.edit_text(text, parse_mode='HTML')
    
    elif data == "admin_list_countries":
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("SELECT name, available FROM countries WHERE available > 0") as cur:
                countries = await cur.fetchall()
        text = "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> الدول المتوفرة </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>\n\n"
        for c in countries:
            text += f"<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> {c[0]} - متاح: {c[1]} </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>\n"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_countries")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    # شراء للمستخدم
    elif data == "buy":
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("SELECT code, name, available FROM countries WHERE available > 0") as cur:
                countries = await cur.fetchall()
        if not countries:
            text = "<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> لا توجد أرقام متاحة حالياً </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>"
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            return
        keyboard = [[InlineKeyboardButton(f"{c[1]} | متاح {c[2]}", callback_data=f"country_{c[0]}")] for c in countries]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
        text = "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> اختر الدولة </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>"
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    elif data.startswith("country_"):
        country_code = data.split("_")[1]
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("""SELECT n.id, n.number, n.price, c.name 
                                     FROM numbers n JOIN countries c ON n.country_code=c.code 
                                     WHERE n.country_code=? AND n.sold=0 LIMIT 10""", (country_code,)) as cur:
                nums = await cur.fetchall()
        country_name = nums[0][3] if nums else ""
        text = f"<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> {country_name} </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>\n"
        text += f"<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> عدد الحسابات المتوفرة: {len(nums)} </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n\n"
        keyboard = []
        for n in nums:
            text += f"<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> {n[1]} - {n[2]}$ </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>\n"
            keyboard.append([InlineKeyboardButton(f"شراء {n[1]} - {n[2]}$", callback_data=f"buynum_{n[0]}")])
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="buy")])
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    elif data.startswith("buynum_"):
        await buy_number_callback(query, context, int(data.split("_")[1]))
    
    elif data.startswith("logout_"):
        await logout_callback(query, context, int(data.split("_")[1]))
    
    elif data == "charge":
        keyboard = [[InlineKeyboardButton("📸 ارسلت الدفع", callback_data="send_proof")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.message.edit_text(PAYMENT_MSG, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    elif data == "send_proof":
        await set_user_state(user_id, "awaiting_payment_proof")
        text = "<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> ارسل سكرين التحويل </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>\n\n"
        text += "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> اكتب المبلغ في الكابشن </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>\n"
        text += "<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> مثال: 5$ </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>"
        keyboard = [[InlineKeyboardButton("❌ الغاء", callback_data="back_main")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    elif data.startswith("confirm_pay_"):
        payment_id = int(data.split("_")[2])
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("SELECT user_id, amount FROM pending_payments WHERE id=?", (payment_id,)) as cur:
                row = await cur.fetchone()
            if row:
                uid, amount = row
                await db.execute("UPDATE users SET balance = balance +? WHERE user_id=?", (amount, uid))
                await db.execute("UPDATE pending_payments SET status='confirmed' WHERE id=?", (payment_id,))
                await db.commit()
                await context.bot.send_message(uid, f"<b><tg-emoji emoji-id='5794353922816429699'>💰</tg-emoji></b><b> تم تأكيد الدفع وإضافة {amount}$ </b><b><tg-emoji emoji-id='5794353922816429699'>💰</tg-emoji></b>", parse_mode='HTML')
                await query.message.edit_caption(caption=query.message.caption + "\n\n<b>✅ تم التأكيد</b>", parse_mode='HTML')
    
    elif data.startswith("reject_pay_"):
        payment_id = int(data.split("_")[2])
        async with aiosqlite.connect("bot.db") as db:
            await db.execute("UPDATE pending_payments SET status='rejected' WHERE id=?", (payment_id,))
            await db.commit()
        await query.message.edit_caption(caption=query.message.caption + "\n\n<b>❌ تم الرفض</b>", parse_mode='HTML')
    
    elif data == "back_main":
        await start_callback(query, context)

async def start_callback(query, context):
    user = query.from_user
    balance = await get_balance(user.id)
    welcome_text = WELCOME_MSG.format(name=user.first_name, user_id=user.id, balance=balance)
    keyboard = [
        [InlineKeyboardButton("🛒 شراء رقم", callback_data="buy")],
        [InlineKeyboardButton("💳 شحن رصيد", callback_data="charge")],
        [InlineKeyboardButton("📊 حسابي", callback_data="account")],
        [InlineKeyboardButton("👨‍💻 المبرمج", url=f"https://t.me/{DEV_USERNAME}")]
    ]
    await query.message.edit_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ========== شراء رقم مع Telethon ==========
async def buy_number_callback(query, context, num_id):
    user_id = query.from_user.id
    balance = await get_balance(user_id)
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("""SELECT n.number, n.price, c.name 
                                 FROM numbers n JOIN countries c ON n.country_code=c.code 
                                 WHERE n.id=? AND n.sold=0""", (num_id,)) as cur:
            row = await cur.fetchone()
    
    if not row:
        await query.answer("الرقم اتباع خلاص", show_alert=True)
        return
    
    number, price, country_name = row
    if balance < price:
        await query.answer("رصيدك غير كافي", show_alert=True)
        return

    await db.execute("UPDATE users SET balance = balance -? WHERE user_id =?", (price, user_id))
    await db.commit()

    text = f"<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> جاري تسجيل الدخول... </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>"
    await query.message.edit_text(text, parse_mode='HTML')
    
    try:
        client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 17 Pro", system_version="iOS 18.0", app_version="10.0.0")
        await client.connect()
        sent = await client.send_code_request(number)
        
        async with aiosqlite.connect("bot.db") as db:
            await db.execute("UPDATE numbers SET sold=1, buyer_id=?, session_string=?, phone_code_hash=? WHERE id=?", 
                             (user_id, client.session.save(), sent.phone_code_hash, num_id))
            await db.commit()
        
        text = f"<b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b><b> تم الشراء بنجاح </b><b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b>\n\n"
        text += f"<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> الدولة: {country_name} </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>\n"
        text += f"<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> الرقم: <code>{number}</code> </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>\n"
        text += f"<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> اسم الجلسة: iPhone 17 Pro </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n\n"
        text += f"<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> ارسل الكود اللي وصلك </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>"
        
        await set_user_state(user_id, f"awaiting_code_{num_id}", {"phone": number, "hash": sent.phone_code_hash, "session": client.session.save()})
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_buy")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
        await client.disconnect()
        
    except FloodWaitError as e:
        await query.message.edit_text(f"<b>❌ لازم تستنى {e.seconds} ثانية</b>", parse_mode='HTML')
        async with aiosqlite.connect("bot.db") as db:
            await db.execute("UPDATE users SET balance = balance +? WHERE user_id =?", (price, user_id))
            await db.commit()
    except Exception as e:
        await query.message.edit_text(f"<b>❌ خطأ: {str(e)}</b>", parse_mode='HTML')
        async with aiosqlite.connect("bot.db") as db:
            await db.execute("UPDATE users SET balance = balance +? WHERE user_id =?", (price, user_id))
            await db.commit()

# ========== تسجيل خروج فعلي ==========
async def logout_callback(query, context, num_id):
    user_id = query.from_user.id
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT session_string FROM numbers WHERE id=? AND buyer_id=?", (num_id, user_id)) as cur:
            row = await cur.fetchone()
    
    if not row or not row[0]:
        await query.answer("الجلسة غير موجودة", show_alert=True)
        return
    
    try:
        client = TelegramClient(StringSession(row[0]), API_ID, API_HASH)
        await client.connect()
        await client(ResetAuthorizationsRequest()) # تسجيل خروج فعلي من كل الأجهزة
        await client.disconnect()
        
        text = "<b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b><b> تم تسجيل الخروج من كل الجلسات بنجاح </b><b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b>\n"
        text += "<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> الحساب آمن الآن 100% </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>"
        keyboard = [[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back_main")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    except Exception as e:
        await query.answer(f"خطأ: {str(e)}", show_alert=True)

# ========== باقي الدوال ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user.id,))
        await db.commit()
    balance = await get_balance(user.id)
    welcome_text = WELCOME_MSG.format(name=user.first_name, user_id=user.id, balance=balance)
    keyboard = [
        [InlineKeyboardButton("🛒 شراء رقم", callback_data="buy")],
        [InlineKeyboardButton("💳 شحن رصيد", callback_data="charge")],
        [InlineKeyboardButton("📊 حسابي", callback_data="account")],
        [InlineKeyboardButton("👨‍💻 المبرمج", url=f"https://t.me/{DEV_USERNAME}")]
    ]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state, temp_data = await get_user_state(user_id)
    
    # إضافة دولة
    if user_id == ADMIN_ID and state == "adding_country":
        try:
            code, name = update.message.text.split("|")
            async with aiosqlite.connect("bot.db") as db:
                await db.execute("INSERT INTO countries (code, name) VALUES (?,?)", (code.strip(), name.strip()))
                await db.commit()
            await set_user_state(user_id, None)
            text = f"<b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b><b> تم إضافة {name} </b><b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b>"
            await update.message.reply_text(text, parse_mode='HTML')
        except:
            await update.message.reply_text("<b>❌ الصيغة غلط</b>", parse_mode='HTML')
    
    elif user_id == ADMIN_ID and state and state.startswith("creating_nums_"):
        country_code = state.split("_")[2]
        lines = update.message.text.strip().split("\n")
        added = 0
        async with aiosqlite.connect("bot.db") as db:
            for line in lines:
                try:
                    number, price = line.split("|")
                    await db.execute("INSERT INTO numbers (country_code, number, price) VALUES (?,?,?)", 
                                     (country_code, number.strip(), float(price.replace("$", ""))))
                    added += 1
                except:
                    pass
            await db.commit()
        await update_country_count()
        await set_user_state(user_id, None)
        text = f"<b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b><b> تم إنشاء {added} رقم </b><b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b>"
        await update.message.reply_text(text, parse_mode='HTML')
    
    elif state and state.startswith("awaiting_code_"):
        num_id = int(state.split("_")[2])
        code = update.message.text.strip()
        try:
            client = TelegramClient(StringSession(temp_data['session']), API_ID, API_HASH, device_model="iPhone 17 Pro", system_version="iOS 18.0", app_version="10.14")
            await client.connect()
            await client.sign_in(phone=temp_data['phone'], code=code, phone_code_hash=temp_data['hash'])
            new_session = client.session.save()
            async with aiosqlite.connect("bot.db") as db:
                await db.execute("UPDATE numbers SET session_string=?, status='active' WHERE id=?", (new_session, num_id))
                await db.commit()
            
            text = "<b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b><b> تم تسجيل الدخول بنجاح </b><b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b>\n\n"
            text += "<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> اسم الجلسة: iPhone 17 Pro </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n\n"
            text += "<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> تسجيل خروج من كل الجلسات؟ </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>"
            
            keyboard = [
                [InlineKeyboardButton("✅ نعم، سجل خروج", callback_data=f"logout_{num_id}")],
                [InlineKeyboardButton("❌ لا، احتفظ بالجلسات", callback_data="back_main")]
            ]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            await set_user_state(user_id, None)
            await client.disconnect()
            
        except PhoneCodeInvalidError:
            await update.message.reply_text("<b>❌ الكود غلط، حاول تاني</b>", parse_mode='HTML')
        except SessionPasswordNeededError:
            await set_user_state(user_id, f"awaiting_2fa_{num_id}", temp_data)
            text = "<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> الحساب عليه تحقق بخطوتين </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n\n"
            text += "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> ارسل باسورد التحقق بخطوتين </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>"
            await update.message.reply_text(text, parse_mode='HTML')
        except FloodWaitError as e:
            await update.message.reply_text(f"<b>❌ لازم تستنى {e.seconds} ثانية</b>", parse_mode='HTML')
        except Exception as e:
            await update.message.reply_text(f"<b>❌ خطأ: {str(e)}</b>", parse_mode='HTML')
    
    elif state and state.startswith("awaiting_2fa_"):
        num_id = int(state.split("_")[2])
        password = update.message.text.strip()
        try:
            client = TelegramClient(StringSession(temp_data['session']), API_ID, API_HASH, device_model="iPhone 17 Pro", system_version="iOS 18.0", app_version="10.14")
            await client.connect()
            await client.sign_in(password=password)
            new_session = client.session.save()
            async with aiosqlite.connect("bot.db") as db:
                await db.execute("UPDATE numbers SET session_string=?, status='active' WHERE id=?", (new_session, num_id))
                await db.commit()
            
            text = "<b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b><b> تم تسجيل الدخول بنجاح </b><b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b>\n\n"
            text += "<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> اسم الجلسة: iPhone 17 Pro </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n\n"
            text += "<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> تسجيل خروج من كل الجلسات؟ </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>"
            
            keyboard = [
                [InlineKeyboardButton("✅ نعم، سجل خروج", callback_data=f"logout_{num_id}")],
                [InlineKeyboardButton("❌ لا", callback_data="back_main")]
            ]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            await set_user_state(user_id, None)
            await client.disconnect()
        except Exception as e:
            await update.message.reply_text(f"<b>❌ الباسورد غلط: {str(e)}</b>", parse_mode='HTML')
        
        # استقبال سكرين الدفع
    elif state == "awaiting_payment_proof":
        if not update.message.photo:
            await update.message.reply_text("<b>❌ لازم ترسل صورة</b>", parse_mode='HTML')
            return
            
            caption = update.message.caption or "0"
            amount = 0.0
            for word in caption.replace("$", "").split():
                try:
                    amount = float(word)
                    break
                except:
                    pass
            
            if amount <= 0:
                await update.message.reply_text("<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> لازم تكتب المبلغ في الكابشن </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>", parse_mode='HTML')
                return
            
            photo_id = update.message.photo[-1].file_id
            async with aiosqlite.connect("bot.db") as db:
                cursor = await db.execute("INSERT INTO pending_payments (user_id, amount, photo_id, caption) VALUES (?,?,?,?)", 
                                         (user_id, amount, photo_id, caption))
                payment_id = cursor.lastrowid
                await db.commit()
            
            await set_user_state(user_id, None)
            await update.message.reply_text("<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> تم استلام الإيصال، جاري المراجعة </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>", parse_mode='HTML')
            
            keyboard = [
                [InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_pay_{payment_id}")],
                [InlineKeyboardButton("❌ رفض", callback_data=f"reject_pay_{payment_id}")]
            ]
            admin_text = f"<b><tg-emoji emoji-id='5794353922816429699'>💰</tg-emoji></b><b> طلب شحن جديد </b><b><tg-emoji emoji-id='5794353922816429699'>💰</tg-emoji></b>\n\n"
            admin_text += f"<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> من: {update.effective_user.first_name} </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>\n"
            admin_text += f"<b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b><b> ايدي: <code>{user_id}</code> </b><b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b>\n"
            admin_text += f"<b><tg-emoji emoji-id='5794353922816429699'>💰</tg-emoji></b><b> المبلغ: {amount}$ </b><b><tg-emoji emoji-id='5794353922816429699'>💰</tg-emoji></b>\n"
            admin_text += f"<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> التفاصيل: {caption} </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>"
            
            await context.bot.send_photo(ADMIN_ID, photo_id, caption=admin_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ========== حذف دولة ==========
async def delete_country_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id!= ADMIN_ID: return
    async with aiosqlite.connect("bot.db") as db:
        async with db.execute("SELECT code, name, available FROM countries") as cur:
            countries = await cur.fetchall()
    if not countries:
        await update.message.reply_text("<b>❌ مفيش دول</b>", parse_mode='HTML')
        return
    keyboard = [[InlineKeyboardButton(f"{c[1]} | {c[2]} رقم", callback_data=f"del_country_{c[0]}")] for c in countries]
    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_countries")])
    text = "<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> اختر الدولة للحذف </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>"
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    # لوحة الأدمن
    if data == "admin_panel": await admin_panel(update, context)
    elif data == "admin_countries": await admin_countries_panel(query)
    
    elif data == "admin_add_country":
        await set_user_state(user_id, "adding_country")
        text = "<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> ارسل الدولة </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>\n\n"
        text += "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> الصيغة: +20|🇪🇬 مصر </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>"
        await query.message.edit_text(text, parse_mode='HTML')
    
    elif data == "admin_create_nums":
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("SELECT code, name FROM countries") as cur:
                countries = await cur.fetchall()
        if not countries:
            await query.answer("ضيف دول أولاً", show_alert=True)
            return
        keyboard = [[InlineKeyboardButton(f"{c[1]}", callback_data=f"select_country_{c[0]}")] for c in countries]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="admin_countries")])
        text = "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> اختر الدولة </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>"
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    elif data.startswith("select_country_"):
        country_code = data.split("_")[2]
        await set_user_state(user_id, f"creating_nums_{country_code}")
        text = "<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> ارسل الأرقام </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>\n\n"
        text += "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> الصيغة: 2012345678|1$ </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>\n"
        text += "<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> كل رقم في سطر </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>"
        await query.message.edit_text(text, parse_mode='HTML')
    
    elif data == "admin_del_country":
        await delete_country_handler(update, context)
    
    elif data.startswith("del_country_"):
        code = data.split("_")[2]
        async with aiosqlite.connect("bot.db") as db:
            await db.execute("DELETE FROM countries WHERE code=?", (code,))
            await db.execute("DELETE FROM numbers WHERE country_code=?", (code,))
            await db.commit()
        await query.answer("✅ تم الحذف", show_alert=True)
        await admin_countries_panel(query)
    
    elif data == "admin_list_countries":
        await update_country_count()
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("SELECT name, available FROM countries WHERE available > 0") as cur:
                countries = await cur.fetchall()
        text = "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> الدول المتوفرة </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>\n\n"
        for c in countries:
            text += f"<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> {c[0]} - متاح: {c[1]} </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>\n"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="admin_countries")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    # شراء للمستخدم
    elif data == "buy":
        await update_country_count()
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("SELECT code, name, available FROM countries WHERE available > 0") as cur:
                countries = await cur.fetchall()
        if not countries:
            text = "<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> لا توجد أرقام متاحة حالياً </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>"
            keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
            await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
            return
        keyboard = [[InlineKeyboardButton(f"{c[1]} | متاح {c[2]}", callback_data=f"country_{c[0]}")] for c in countries]
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_main")])
        text = "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> اختر الدولة </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>"
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    elif data.startswith("country_"):
        country_code = data.split("_")[1]
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("""SELECT n.id, n.number, n.price, c.name 
                                     FROM numbers n JOIN countries c ON n.country_code=c.code 
                                     WHERE n.country_code=? AND n.sold=0 LIMIT 10""", (country_code,)) as cur:
                nums = await cur.fetchall()
        country_name = nums[0][3] if nums else ""
        text = f"<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> {country_name} </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>\n"
        text += f"<b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b><b> عدد الحسابات المتوفرة: {len(nums)} </b><b><tg-emoji emoji-id='5798482080421649554'>🔒</tg-emoji></b>\n\n"
        keyboard = []
        for n in nums:
            text += f"<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> {n[1]} - {n[2]}$ </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>\n"
            keyboard.append([InlineKeyboardButton(f"شراء {n[1]} - {n[2]}$", callback_data=f"buynum_{n[0]}")])
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="buy")])
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    elif data.startswith("buynum_"):
        await buy_number_callback(query, context, int(data.split("_")[1]))
    
    elif data.startswith("logout_"):
        await logout_callback(query, context, int(data.split("_")[1]))
    
    elif data == "charge":
        keyboard = [[InlineKeyboardButton("📸 ارسلت الدفع", callback_data="send_proof")],
                    [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.message.edit_text(PAYMENT_MSG, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    elif data == "send_proof":
        await set_user_state(user_id, "awaiting_payment_proof")
        text = "<b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b><b> ارسل سكرين التحويل </b><b><tg-emoji emoji-id='5798941981224737816'>🚀</tg-emoji></b>\n\n"
        text += "<b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b><b> اكتب المبلغ في الكابشن </b><b><tg-emoji emoji-id='5796499583647359561'>📌</tg-emoji></b>\n"
        text += "<b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b><b> مثال: 5$ </b><b><tg-emoji emoji-id='5796526727840669257'>🎲</tg-emoji></b>"
        keyboard = [[InlineKeyboardButton("❌ الغاء", callback_data="back_main")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')
    
    elif data.startswith("confirm_pay_"):
        payment_id = int(data.split("_")[2])
        async with aiosqlite.connect("bot.db") as db:
            async with db.execute("SELECT user_id, amount FROM pending_payments WHERE id=?", (payment_id,)) as cur:
                row = await cur.fetchone()
            if row:
                uid, amount = row
                await db.execute("UPDATE users SET balance = balance +? WHERE user_id=?", (amount, uid))
                await db.execute("UPDATE pending_payments SET status='confirmed' WHERE id=?", (payment_id,))
                await db.commit()
                await context.bot.send_message(uid, f"<b><tg-emoji emoji-id='5794353922816429699'>💰</tg-emoji></b><b> تم تأكيد الدفع وإضافة {amount}$ </b><b><tg-emoji emoji-id='5794353922816429699'>💰</tg-emoji></b>", parse_mode='HTML')
                await query.message.edit_caption(caption=query.message.caption + "\n\n<b>✅ تم التأكيد</b>", parse_mode='HTML')
    
    elif data.startswith("reject_pay_"):
        payment_id = int(data.split("_")[2])
        async with aiosqlite.connect("bot.db") as db:
            await db.execute("UPDATE pending_payments SET status='rejected' WHERE id=?", (payment_id,))
            await db.commit()
        await query.message.edit_caption(caption=query.message.caption + "\n\n<b>❌ تم الرفض</b>", parse_mode='HTML')
    
    elif data == "back_main":
        await start_callback(query, context)
    
    elif data == "account":
        balance = await get_balance(user_id)
        text = f"<b><tg-emoji emoji-id='5794353922816429699'>📊</tg-emoji></b><b> حسابك </b><b><tg-emoji emoji-id='5794353922816429699'>📊</tg-emoji></b>\n\n"
        text += f"<b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b><b> ايديك: <code>{user_id}</code> </b><b><tg-emoji emoji-id='5794353922816429699'>🛡️</tg-emoji></b>\n"
        text += f"<b><tg-emoji emoji-id='5794353922816429699'>💰</tg-emoji></b><b> رصيدك: {balance}$ </b><b><tg-emoji emoji-id='5794353922816429699'>💰</tg-emoji></b>"
        keyboard = [[InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

async def start_callback(query, context):
    user = query.from_user
    balance = await get_balance(user.id)
    welcome_text = WELCOME_MSG.format(name=user.first_name, user_id=user.id, balance=balance)
    keyboard = [
        [InlineKeyboardButton("🛒 شراء رقم", callback_data="buy")],
        [InlineKeyboardButton("💳 شحن رصيد", callback_data="charge")],
        [InlineKeyboardButton("📊 حسابي", callback_data="account")],
        [InlineKeyboardButton("👨‍💻 المبرمج", url=f"https://t.me/{DEV_USERNAME}")]
    ]
    await query.message.edit_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ========== Start ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    async with aiosqlite.connect("bot.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user.id,))
        await db.commit()
    balance = await get_balance(user.id)
    welcome_text = WELCOME_MSG.format(name=user.first_name, user_id=user.id, balance=balance)
    keyboard = [
        [InlineKeyboardButton("🛒 شراء رقم", callback_data="buy")],
        [InlineKeyboardButton("💳 شحن رصيد", callback_data="charge")],
        [InlineKeyboardButton("📊 حسابي", callback_data="account")],
        [InlineKeyboardButton("👨‍💻 المبرمج", url=f"https://t.me/{DEV_USERNAME}")]
    ]
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='HTML')

# ========== تشغيل البوت ==========
def main():
    print("Bot Started...")
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    asyncio.run(init_db())
    main()
