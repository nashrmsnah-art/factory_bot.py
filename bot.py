import os
import sqlite3
import zipfile
import asyncio
from telethon import TelegramClient, events, Button, functions, types
from telethon.errors import SessionPasswordNeededError, FloodWaitError
import phonenumbers
from phonenumbers import geocoder

# --- إعدادات أساسية (ضع بياناتك هنا) ---
API_ID = 31650696  # استبدله بـ API ID
API_HASH = '2829d6502df68cd12fab33cabf2851d2'  # استبدله بـ API HASH
BOT_TOKEN = '8717368656:AAHdK0iBCxMX8ThTC-GgDWDrK9jcO2AJeV0'  # استبدله بـ BOT TOKEN
ADMIN_ID = 154919127  # استبدله بـ ID حسابك الشخصي

bot = TelegramClient('admin_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# إنشاء البيئة
if not os.path.exists('sessions'): os.makedirs('sessions')
db = sqlite3.connect('storage.db', check_same_thread=False)
cursor = db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS accounts 
                (phone TEXT PRIMARY KEY, country TEXT, status TEXT)''')
db.commit()

# --- دوال برمجية متطورة ---

async def change_account_name(phone, new_name):
    try:
        client = TelegramClient(f'sessions/{phone}', API_ID, API_HASH)
        await client.connect()
        if await client.is_user_authorized():
            await client(functions.account.UpdateProfileRequest(first_name=new_name))
            await client.disconnect()
            return True
    except: return False

async def change_account_photo(phone, photo_path):
    try:
        client = TelegramClient(f'sessions/{phone}', API_ID, API_HASH)
        await client.connect()
        if await client.is_user_authorized():
            file = await client.upload_file(photo_path)
            await client(functions.photos.UploadProfilePhotoRequest(file=file))
            await client.disconnect()
            return True
    except: return False

def get_country_name(phone):
    try:
        parsed = phonenumbers.parse(f"+{phone}" if not phone.startswith('+') else phone)
        return geocoder.description_for_number(parsed, "ar")
    except: return "غير معروف"

# --- الأوامر ولوحة التحكم ---

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id != ADMIN_ID: return
    buttons = [
        [Button.inline("📊 إحصائيات الدول", data="stats"), Button.inline("🔍 فحص الشغال", data="check")],
        [Button.inline("📝 تغيير الأسماء", data="ask_name"), Button.inline("🖼 تغيير الصور", data="ask_photo")],
        [Button.inline("📦 نسخة احتياطية", data="backup"), Button.inline("💰 سحب حساب للبيع", data="sell")],
        [Button.inline("➕ إضافة جلسات (رفع ملفات)", data="add_info")]
    ]
    await event.respond("🛡 **مرحباً بك في نظام التخزين المتطور**\nإدارة كاملة لحساباتك من مكان واحد.", buttons=buttons)

@bot.on(events.CallbackQuery)
async def handler(event):
    if event.sender_id != ADMIN_ID: return
    data = event.data.decode('utf-8')

    if data == "stats":
        cursor.execute("SELECT country, COUNT(*) FROM accounts GROUP BY country")
        res = cursor.fetchall()
        msg = "📍 **إحصائيات الدول:**\n\n"
        for row in res: msg += f"• {row[0]}: ({row[1]}) حساب\n"
        await event.respond(msg)

    elif data == "check":
        m = await event.respond("🔄 جاري الفحص وتحديث قاعدة البيانات...")
        cursor.execute("SELECT phone FROM accounts")
        phones = cursor.fetchall()
        good, bad = 0, 0
        for (phone,) in phones:
            client = TelegramClient(f'sessions/{phone}', API_ID, API_HASH)
            try:
                await client.connect()
                if not await client.is_user_authorized():
                    cursor.execute("DELETE FROM accounts WHERE phone=?", (phone,))
                    bad += 1
                else: good += 1
                await client.disconnect()
            except: bad += 1
        db.commit()
        await m.edit(f"✅ فحص مكتمل:\n🟢 شغال: {good}\n🔴 محذوف: {bad}")

    elif data == "backup":
        await event.respond("📦 يتم الآن ضغط الجلسات...")
        with zipfile.ZipFile('sessions_backup.zip', 'w') as z:
            for f in os.listdir('sessions'): z.write(f'sessions/{f}', f)
        await bot.send_file(ADMIN_ID, 'sessions_backup.zip', caption="✅ نسخة احتياطية")
        os.remove('sessions_backup.zip')

    elif data == "ask_name":
        async with bot.conversation(ADMIN_ID) as conv:
            await conv.send_message("📝 أرسل الاسم الجديد لكل الحسابات:")
            name = (await conv.get_response()).text
            await conv.send_message("🔄 جاري التغيير... قد يستغرق وقت")
            cursor.execute("SELECT phone FROM accounts")
            for (p,) in cursor.fetchall(): await change_account_name(p, name)
            await conv.send_message("✅ تم تغيير اسم جميع الحسابات بنجاح!")

    elif data == "ask_photo":
        async with bot.conversation(ADMIN_ID) as conv:
            await conv.send_message("🖼 أرسل الصورة المراد وضعها لكل الحسابات:")
            pic = await conv.get_response()
            path = await pic.download_media()
            await conv.send_message("🔄 جاري تحديث الصور...")
            cursor.execute("SELECT phone FROM accounts")
            for (p,) in cursor.fetchall(): await change_account_photo(p, path)
            os.remove(path)
            await conv.send_message("✅ تم تحديث صور البروفايل للجميع!")

    elif data == "sell":
        cursor.execute("SELECT phone FROM accounts LIMIT 1")
        row = cursor.fetchone()
        if row:
            phone = row[0]
            await bot.send_file(ADMIN_ID, f'sessions/{phone}.session', caption=f"✅ تم سحب حساب جاهز:\nرقم: `{phone}`\nدولة: {get_country_name(phone)}")
            cursor.execute("DELETE FROM accounts WHERE phone=?", (phone,))
            db.commit()
        else: await event.respond("❌ لا توجد حسابات متوفرة حالياً.")

    elif data == "add_info":
        await event.respond("➕ لإضافة حسابات: قم برفع ملفات الـ `.session` في المحادثة مباشرة وسيقوم البوت بتخزينها.")

# استقبال ملفات السشن يدوياً من الأدمن وتخزينها
@bot.on(events.NewMessage(func=lambda e: e.document and e.sender_id == ADMIN_ID))
async def downloader(event):
    if event.file.ext == ".session":
        path = await event.download_media(file='sessions/')
        phone = os.path.basename(path).replace(".session", "")
        country = get_country_name(phone)
        try:
            cursor.execute("INSERT INTO accounts VALUES (?, ?, ?)", (phone, country, "active"))
            db.commit()
            await event.reply(f"✅ تم تخزين الحساب بنجاح!\n📍 الدولة: {country}")
        except: await event.reply("⚠️ الحساب موجود بالفعل.")

print("--- البوت شغال الآن ---")
bot.run_until_disconnected()
