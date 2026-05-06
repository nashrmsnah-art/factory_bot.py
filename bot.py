import os
import sqlite3
import zipfile
from telethon import TelegramClient, events, Button, functions, types
import phonenumbers
from phonenumbers import geocoder

# --- إعدادات أساسية ---
API_ID = 31650696  
API_HASH = '2829d6502df68cd12fab33cabf2851d2'  
BOT_TOKEN = '8650618464:AAFdn_TQUhzU8aMKHpxcHWaV9icW7XuNt2Q'  
OWNER_ID = 8085768728  # أيدي المالك (أنت)
DEVELOPER_USER = "devazf" # يوزر المطور بدون @

bot = TelegramClient('admin_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- قاعدة البيانات ---
db = sqlite3.connect('pro_store.db', check_same_thread=False)
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS accounts (phone TEXT PRIMARY KEY, country TEXT, status TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)')
cursor.execute('INSERT OR IGNORE INTO admins VALUES (?)', (OWNER_ID,))
db.commit()

if not os.path.exists('sessions'): os.makedirs('sessions')

# --- الدوال المساعدة ---
def is_admin(user_id):
    cursor.execute('SELECT 1 FROM admins WHERE user_id=?', (user_id,))
    return cursor.fetchone() is not None

def get_stats_msg():
    cursor.execute("SELECT country, COUNT(*) FROM accounts GROUP BY country")
    rows = cursor.fetchall()
    if not rows: return "❌ لا توجد أرقام متوفرة حالياً."
    msg = "🌍 **الدول المتوفرة حالياً:**\n\n"
    for row in rows:
        msg += f"📍 {row[0]}: ({row[1]}) حساب\n"
    return msg

# --- التعامل مع الرسائل ---

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    user_id = event.sender_id
    
    if is_admin(user_id):
        # لوحة الأدمن
        btns = [
            [Button.inline("➕ إضافة رقم", data="add_number"), Button.inline("🎁 إهداء رقم لعميل", data="gift_num")],
            [Button.inline("📊 الإحصائيات", data="stats"), Button.inline("🔍 فحص الحسابات", data="check")],
            [Button.inline("👤 إدارة الأدمنية", data="manage_admins"), Button.inline("📦 نسخة احتياطية", data="backup")],
            [Button.inline("🛒 واجهة المستخدم", data="user_view")]
        ]
        await event.respond("👨‍✈️ **أهلاً بك يا مدير في لوحة التحكم:**", buttons=btns)
    else:
        # لوحة المستخدم العادي
        btns = [
            [Button.inline("🛍 شراء رقم", data="buy_num"), Button.inline("🌍 الدول المتوفرة", data="stats")],
            [Button.url("👨‍💻 مطور البوت", f"t.me/{DEVELOPER_USER}")]
        ]
        await event.respond(f"👋 **أهلاً بك في بوت تخزين الأرقام**\n\nيمكنك شراء الأرقام الجاهزة بأسعار مميزة.", buttons=btns)

@bot.on(events.CallbackQuery)
async def callback_handler(event):
    data = event.data.decode('utf-8')
    user_id = event.sender_id

    if data == "stats":
        await event.respond(get_stats_msg())

    elif data == "user_view":
        await start(event)

    elif data == "buy_num":
        await event.respond("💳 للشراء، يرجى التواصل مع المطور مباشرة لتحديد وسيلة الدفع والدولة.\n\n" + get_stats_msg(), 
                            buttons=[Button.url("إضغط للتواصل", f"t.me/{DEVELOPER_USER}")])

    # --- خاصية الإهداء (للمطور فقط) ---
    elif data == "gift_num":
        if not is_admin(user_id): return
        async with bot.conversation(user_id) as conv:
            await conv.send_message("🎁 **نظام الإهداء:**\nأرسل الآن رقم الهاتف المراد إهداؤه (من المخزن):")
            phone = (await conv.get_response()).text.strip()
            
            cursor.execute("SELECT phone FROM accounts WHERE phone=?", (phone,))
            if not cursor.fetchone():
                return await conv.send_message("❌ هذا الرقم غير موجود في المخزن!")
            
            await conv.send_message("🆔 الآن أرسل ID العميل الذي سيستلم الرقم:")
            client_id = int((await conv.get_response()).text.strip())
            
            try:
                path = f'sessions/{phone}.session'
                await bot.send_file(client_id, path, caption=f"🎁 **هدية لك من الإدارة!**\nتم إرسال حساب تليجرام جاهز لك.\nرقم الهاتف: `{phone}`")
                await conv.send_message(f"✅ تم إرسال الرقم `{phone}` إلى العميل `{client_id}` بنجاح.")
                # اختياري: حذف الرقم من المخزن بعد الإهداء
                # cursor.execute("DELETE FROM accounts WHERE phone=?", (phone,))
                # db.commit()
            except Exception as e:
                await conv.send_message(f"❌ فشل الإرسال للعميل. تأكد أنه قام بتشغيل البوت أولاً.\nالخطأ: {e}")

    # --- إضافة رقم (كما في الكود السابق) ---
    elif data == "add_number":
        # (نفس كود إضافة الرقم السابق الذي يطلب الكود والسشن)
        await event.respond("📞 ابدأ عملية تسجيل الدخول الآن...")
        # ... (نفس منطق الكود السابق)

    elif data == "backup":
        if not is_admin(user_id): return
        await event.respond("📦 جاري ضغط الملفات...")
        # (نفس كود الزيب السابق)

print("--- البوت المتطور يعمل بنجاح ---")
bot.run_until_disconnected()
