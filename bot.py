import os
import sqlite3
import zipfile
import asyncio
from telethon import TelegramClient, events, Button, functions, types
from telethon.errors import SessionPasswordNeededError, FloodWaitError, PhoneCodeInvalidError
import phonenumbers
from phonenumbers import geocoder

# --- إعدادات أساسية ---
API_ID = 31650696  # استبدله بـ API ID
API_HASH = '2829d6502df68cd12fab33cabf2851d2'  # استبدله بـ API HASH
BOT_TOKEN = '8717368656:AAHdK0iBCxMX8ThTC-GgDWDrK9jcO2AJeV0'  # استبدله بـ BOT TOKEN
OWNER_ID = 154919127  # استبدله بـ ID حسابك الشخصي

bot = TelegramClient('admin_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# --- تجهيز قاعدة البيانات ---
db = sqlite3.connect('master_data.db', check_same_thread=False)
cursor = db.cursor()
cursor.execute('CREATE TABLE IF NOT EXISTS accounts (phone TEXT PRIMARY KEY, country TEXT, status TEXT)')
cursor.execute('CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY)')
# إضافة المالك كأدمن تلقائي
cursor.execute('INSERT OR IGNORE INTO admins VALUES (?)', (OWNER_ID,))
db.commit()

if not os.path.exists('sessions'): os.makedirs('sessions')

# --- الدوال المساعدة ---
def is_admin(user_id):
    cursor.execute('SELECT 1 FROM admins WHERE user_id=?', (user_id,))
    return cursor.fetchone() is not None

def get_country_ar(phone):
    try:
        if not phone.startswith('+'): phone = '+' + phone
        parsed = phonenumbers.parse(phone)
        return geocoder.description_for_number(parsed, "ar")
    except: return "غير معروف"

# --- نظام إضافة رقم (Login System) ---
@bot.on(events.CallbackQuery(data="add_number"))
async def add_number_logic(event):
    if not is_admin(event.sender_id): return
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("📞 أرسل الرقم الآن مع مفتاح الدولة (مثال: +2012345678):")
        phone = (await conv.get_response()).text.strip().replace(" ", "")
        
        client = TelegramClient(f'sessions/{phone}', API_ID, API_HASH)
        await client.connect()
        
        try:
            sent_code = await client.send_code_request(phone)
            await conv.send_message("📩 أرسل كود التحقق الذي وصلك:")
            code = (await conv.get_response()).text.strip()
            
            try:
                await client.sign_in(phone, code)
            except SessionPasswordNeededError:
                await conv.send_message("🔐 الحساب محمي بكلمة سر (التحقق بخطوتين)، أرسلها:")
                password = (await conv.get_response()).text.strip()
                await client.sign_in(password=password)
            
            country = get_country_ar(phone)
            cursor.execute("INSERT OR REPLACE INTO accounts VALUES (?, ?, ?)", (phone, country, "active"))
            db.commit()
            await conv.send_message(f"✅ تم تسجيل الحساب بنجاح!\n📍 الدولة: {country}")
            
        except Exception as e:
            await conv.send_message(f"❌ حدث خطأ: {str(e)}")
        finally:
            await client.disconnect()

# --- لوحة التحكم المتطورة ---
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if not is_admin(event.sender_id): return
    btns = [
        [Button.inline("➕ إضافة رقم جديد", data="add_number"), Button.inline("💰 سحب رقم للبيع", data="sell_num")],
        [Button.inline("📊 إحصائيات", data="stats"), Button.inline("🔍 فحص الحسابات", data="check")],
        [Button.inline("📝 تغيير الأسماء", data="edit_name"), Button.inline("🖼 تغيير الصور", data="edit_pic")],
        [Button.inline("👤 إدارة الأدمنية", data="manage_admins"), Button.inline("📦 نسخة احتياطية", data="backup")]
    ]
    await event.respond("🚀 **نظام إدارة الحسابات المتطور**\nمرحباً بك يا مدير، اختر من القائمة:", buttons=btns)

# --- إدارة الأدمنية ---
@bot.on(events.CallbackQuery(data="manage_admins"))
async def admin_management(event):
    if event.sender_id != OWNER_ID:
        return await event.answer("⚠️ عذراً، هذا الأمر للمالك فقط!", alert=True)
    
    btns = [[Button.inline("➕ إضافة أدمن", data="add_adm"), Button.inline("➖ تنزيل أدمن", data="rem_adm")]]
    await event.respond("👥 **قسم إدارة الأدمنية:**", buttons=btns)

@bot.on(events.CallbackQuery(pattern=r"(add_adm|rem_adm)"))
async def process_admin(event):
    action = event.data.decode('utf-8')
    async with bot.conversation(event.sender_id) as conv:
        await conv.send_message("🆔 أرسل الـ ID الخاص بالشخص:")
        target_id = int((await conv.get_response()).text)
        
        if action == "add_adm":
            cursor.execute("INSERT OR IGNORE INTO admins VALUES (?)", (target_id,))
            await conv.send_message(f"✅ تم رفع {target_id} كأدمن.")
        else:
            if target_id == OWNER_ID: return await conv.send_message("❌ لا يمكنك تنزيل المالك!")
            cursor.execute("DELETE FROM admins WHERE user_id=?", (target_id,))
            await conv.send_message(f"✅ تم تنزيل {target_id} من الإدارة.")
        db.commit()

# --- سحب رقم محدد ---
@bot.on(events.CallbackQuery(data="sell_num"))
async def sell_number(event):
    if not is_admin(event.sender_id): return
    cursor.execute("SELECT phone, country FROM accounts ORDER BY RANDOM() LIMIT 1")
    row = cursor.fetchone()
    if row:
        phone, country = row
        path = f'sessions/{phone}.session'
        await bot.send_file(event.sender_id, path, caption=f"✅ تم سحب حساب:\n📞 الرقم: `{phone}`\n📍 الدولة: {country}")
        # خيار: هل تريد حذفه من القاعدة بعد السحب؟
        # cursor.execute("DELETE FROM accounts WHERE phone=?", (phone,))
        # db.commit()
    else:
        await event.answer("❌ المخزن فارغ!", alert=True)

# (بقية الدوال مثل الفحص وتغيير الاسم تظل كما في الكود السابق مع التأكد من فحص is_admin)

print("--- البوت العملاق يعمل الآن ---")
bot.run_until_disconnected()
