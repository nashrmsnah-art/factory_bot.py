import os
import json
import asyncio
import subprocess
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

# ====== بيانات المصنع ======
API_ID = 31650696
API_HASH = '2829d6502df68cd12fab33cabf2851d2'
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = 154919127  # ايديك انت صاحب المصنع
DB_FILE = 'database.json'

bot = TelegramClient('factory', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ====== قاعدة البيانات ======
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_db():
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

db = load_db()

# ====== ستارت ======
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    btns = [
        [Button.inline("➕ انشاء بوت جديد", "new_bot")],
        [Button.inline("📊 بوتاتي", "my_bots")],
        [Button.inline("📞 الدعم", "support")]
    ]
    await event.reply("**🤖 اهلا بيك في مصنع البوتات**\n\nتقدر تنشئ بوت خاص بيك في دقيقة", buttons=btns)

# ====== استقبال النصوص ======
@bot.on(events.NewMessage())
async def handle_text_input(event):
    if event.raw_text.startswith('/'):
        return
        
    uid = event.sender_id
    text = event.raw_text.strip()
    
    if str(uid) not in db.get('waiting_for', {}):
        return
        
    waiting = db['waiting_for'][str(uid)]
    
    if 'pending_bots' not in db:
        db['pending_bots'] = {}
    if str(uid) not in db['pending_bots']:
        db['pending_bots'][str(uid)] = {}
        
    pending = db['pending_bots'][str(uid)]
    
    if waiting == 'set_token':
        if 'users' in text.lower() or ':' not in text or len(text) < 30:
            await event.reply('❌ **التوكن غلط!**\n\nلازم يبدأ بأرقام وفيه `:`\nمثال:\n`1234567890:ABCdEfGhIjKlMnOpQrStUvWxYz`\n\nابعته تاني من @BotFather')
            return
        pending['token'] = text
        db['waiting_for'][str(uid)] = 'set_admin'
        save_db()
        await event.reply('✅ **تم حفظ التوكن**\n\n📝 **الخطوة 2/4: ابعت ايدي الادمن**\nمن @userinfobot')
        return
        
    elif waiting == 'set_admin':
        if not text.isdigit():
            await event.reply('❌ الايدي لازم ارقام بس، ابعته تاني')
            return
        pending['admin_id'] = int(text)
        db['waiting_for'][str(uid)] = 'set_username'
        save_db()
        await event.reply('✅ **تم حفظ الايدي**\n\n📝 **الخطوة 3/4: ابعت يوزر المطور**\n\nمثال: `Devazf` بدون @')
        return
        
    elif waiting == 'set_username':
        pending['dev_username'] = text.replace('@', '')
        db['waiting_for'][str(uid)] = 'set_channels'
        save_db()
        await event.reply('✅ **تم حفظ اليوزر**\n\n📝 **الخطوة 4/4: ابعت القنوات الاجبارية**\n\nلو قناة واحدة: `Vip6705`\nلو اكتر: `Vip6705,Channel2`\nلو مش عايز: `none`')
        return
        
    elif waiting == 'set_channels':
        if text.lower() == 'none':
            pending['channels'] = []
        else:
            pending['channels'] = [c.strip().replace('@', '') for c in text.split(',')]
        del db['waiting_for'][str(uid)]
        save_db()
        
        btns = [[Button.inline("🚀 انشاء البوت دلوقتي", "generate_bot")]]
        await event.reply(
            f'✅ **تم حفظ كل البيانات**\n\n'
            f'**التوكن:** `{pending["token"][:20]}...`\n'
            f'**الادمن:** `{pending["admin_id"]}`\n'
            f'**المطور:** @{pending["dev_username"]}\n'
            f'**القنوات:** {pending["channels"] or "مفيش"}\n\n'
            f'دوس الزر عشان تنشئ البوت', 
            buttons=btns
        )
        return

# ====== الازرار ======
@bot.on(events.CallbackQuery())
async def callback(event):
    uid = event.sender_id
    data = event.data.decode()
    
    if data == 'new_bot':
        if 'pending_bots' not in db:
            db['pending_bots'] = {}
        db['pending_bots'][str(uid)] = {}
        if 'waiting_for' not in db:
            db['waiting_for'] = {}
        db['waiting_for'][str(uid)] = 'set_token'
        save_db()
        await event.edit('📝 **الخطوة 1/4: ابعت توكن البوت**\n\nمن @BotFather\n\nشكله:\n`1234567890:ABCdEfGhI...`')
        return
        
    elif data == 'generate_bot':
        if str(uid) not in db.get('pending_bots', {}):
            await event.answer('❌ ابدأ من الاول', alert=True)
            return
            
        pending = db['pending_bots'][str(uid)]
        
        # فحص البيانات
        if not pending.get('token') or 'users' in pending['token'].lower():
            await event.answer('❌ التوكن غلط', alert=True)
            return
        if not pending.get('admin_id'):
            await event.answer('❌ ايدي الادمن ناقص', alert=True)
            return
            
        await event.edit('⏳ **جاري انشاء البوت...**\n\nده ممكن ياخد دقيقة')
        
        try:
            # هنا بتحط كود النشر بتاعك
            # ده مثال: بتقرا قالب البوت وتعدل عليه
            
            bot_code = '''import os
import json
import random
import re
from telethon import TelegramClient, events, Button

# ====== بيانات البوت ======
API_ID = 33595004
API_HASH = 'cbd1066ed026997f2f4a7c4323b7b'
BOT_TOKEN = 'TOKEN_PLACEHOLDER'
ADMIN_ID = ADMIN_PLACEHOLDER
DEVELOPER_USERNAME = 'USERNAME_PLACEHOLDER'
DEVELOPER_LINK = f'https://t.me/{DEVELOPER_USERNAME}'
REQUIRED_CHANNELS = CHANNELS_PLACEHOLDER
DB_FILE = 'database.json'
BACKUP_FILE = 'sessions_backup.json'
SUB_PRICE = 3
MAX_ACCOUNTS = 1
FREE_TRIAL_DAYS = 1

bot = TelegramClient('bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# باقي كود البوت هنا...
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply('البوت شغال ✅')

bot.run_until_disconnected()
'''
            
            # تبديل البيانات
            bot_code = bot_code.replace('TOKEN_PLACEHOLDER', pending['token'])
            bot_code = bot_code.replace('ADMIN_PLACEHOLDER', str(pending['admin_id']))
            bot_code = bot_code.replace('USERNAME_PLACEHOLDER', pending['dev_username'])
            bot_code = bot_code.replace('CHANNELS_PLACEHOLDER', str(pending['channels']))
            
            # حفظ الملف
            filename = f"bot_{uid}_{random.randint(1000,9999)}.py"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(bot_code)
            
            # هنا المفروض ترفعه على Railway او GitHub
            # ده مجرد مثال
            
            await event.edit(
                f'✅ **تم انشاء البوت بنجاح**\n\n'
                f'**اليوزر:** @{pending["dev_username"]}\n'
                f'**القنوات:** {pending["channels"] or "مفيش"}\n\n'
                f'الملف: `{filename}`\n\n'
                f'**ملحوظة:** ارفع الملف ده على Railway وشغله'
            )
            
            # امسح البيانات المؤقتة
            del db['pending_bots'][str(uid)]
            save_db()
            
        except Exception as e:
            await event.edit(f'❌ **حصل خطأ:**\n\n`{str(e)}`')
        
        return
        
    elif data == 'my_bots':
        await event.answer('قريباً...', alert=True)
        return
        
    elif data == 'support':
        await event.answer('كلم @Devazf', alert=True)
        return
        
    elif data == 'back_main':
        await start(event)
        return

print("✅ المصنع شغال...")
bot.run_until_disconnected()
