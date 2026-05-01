import os
import json
import asyncio
import subprocess
import random
import requests
import base64
import string
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

# ====== بيانات المصنع ======
API_ID = 31650696
API_HASH = '2829d6502df68cd12fab33cabf2851d2'
BOT_TOKEN = os.getenv('BOT_TOKEN')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN') # لازم تضيفه في Railway
GITHUB_USERNAME = 'YourGitHubUsername' # غيره ليوزر جيتهاب بتاعك
ADMIN_ID = 7832394974
DB_FILE = 'database.json'

bot = TelegramClient('factory', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ====== قاعدة البيانات ======
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {'codes': {}, 'used_codes': [], 'bots': {}}

def save_db():
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

db = load_db()

# ====== اوامر الادمن ======
@bot.on(events.NewMessage(pattern='/gen'))
async def gen_code(event):
    if event.sender_id!= ADMIN_ID:
        return

    # توليد كود عشوائي
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    db['codes'][code] = {'created': True, 'used_by': None}
    save_db()

    await event.reply(f'✅ **كود تفعيل جديد:**\n\n`{code}`\n\nالكود يستخدم مرة واحدة فقط')

@bot.on(events.NewMessage(pattern='/codes'))
async def list_codes(event):
    if event.sender_id!= ADMIN_ID:
        return

    unused = [c for c, v in db['codes'].items() if not v['used_by']]
    used = [c for c, v in db['codes'].items() if v['used_by']]

    text = f'**📊 اكواد التفعيل**\n\n'
    text += f'**المتاحة:** {len(unused)}\n'
    for c in unused[:10]:
        text += f'`{c}`\n'

    text += f'\n**المستخدمة:** {len(used)}\n'
    await event.reply(text)

# ====== ستارت ======
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    btns = [
        [Button.inline("➕ انشاء بوت جديد", "new_bot")],
        [Button.inline("📊 بوتاتي", "my_bots")],
        [Button.inline("📞 الدعم", "support")]
    ]
    await event.reply(
        "**🤖 اهلا بك في مصنع بوتات النشر التلقائي**\n\n
        "💰 **السعر:** 10$ للبوت الواحد\n" 
        "🔐 **كود تفعيل** لكل بوت\n\n"
        "كلم المبرمج @Devazf عشان تشتري كود",
        buttons=btns
    )

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

    if waiting == 'set_code':
        if text not in db['codes']:
            await event.reply('❌ **الكود غلط او مستخدم قبل كده**\n\nكلم @Devazf عشان تشتري كود')
            return
        if db['codes'][text]['used_by']:
            await event.reply('❌ **الكود مستخدم قبل كده**')
            return

        # حفظ الكود
        pending['activation_code'] = text
        db['waiting_for'][str(uid)] = 'set_token'
        save_db()
        await event.reply('✅ **تم تفعيل الكود**\n\n📝 **الخطوة 1/4: ابعت توكن البوت**\n\nمن @BotFather')
        return

    elif waiting == 'set_token':
        if 'users' in text.lower() or ':' not in text or len(text) < 30:
            await event.reply('❌ **التوكن غلط!**\n\nابعته تاني من @BotFather')
            return
        pending['token'] = text
        db['waiting_for'][str(uid)] = 'set_admin'
        save_db()
        await event.reply('✅ **تم حفظ التوكن**\n\n📝 **الخطوة 2/4: ابعت ايدي الادمن**\nمن @userinfobot')
        return

    elif waiting == 'set_admin':
        if not text.isdigit():
            await event.reply('❌ الايدي لازم ارقام بس')
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
        await event.reply('✅ **تم حفظ اليوزر**\n\n📝 **الخطوة 4/4: ابعت القنوات الاجبارية**\n\nلو قناة: `Vip6705`\nلو اكتر: `Vip6705,Channel2`\nلو مش عايز: `none`')
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
            f'**الكود:** `{pending["activation_code"]}`\n'
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
        db['waiting_for'][str(uid)] = 'set_code'
        save_db()
        await event.edit(
            '🔐 **ادخل كود التفعيل**\n\n'
            'الكود بتحصل عليه بعد الدفع\n'
            'كلم @Devazf عشان تشتري كود\n\n'
            'سعر البوت: 3$'
        )
        return

    elif data == 'generate_bot':
        if str(uid) not in db.get('pending_bots', {}):
            await event.answer('❌ ابدأ من الاول', alert=True)
            return

        pending = db['pending_bots'][str(uid)]

        if not pending.get('activation_code'):
            await event.answer('❌ كود التفعيل ناقص', alert=True)
            return
        if not pending.get('token') or 'users' in pending['token'].lower():
            await event.answer('❌ التوكن غلط', alert=True)
            return

        msg = await event.edit('⏳ **جاري انشاء البوت...**\n\n1/4 تجهيز الكود...')

        try:
            # 1. جهز كود البوت - حط كود البوت بتاعك كامل هنا
            bot_code = '''import os
import json
from telethon import TelegramClient, events, Button

API_ID = 33595004
API_HASH = 'cbd1066ed026997f2f4a7c4323b7b'
BOT_TOKEN = os.getenv('BOT_TOKEN')
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

# حط باقي كود البوت بتاعك هنا كامل...

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    await event.reply('البوت شغال ✅')

bot.run_until_disconnected()
'''

            # 2. بدل البيانات
            bot_code = bot_code.replace('ADMIN_PLACEHOLDER', str(pending['admin_id']))
            bot_code = bot_code.replace('USERNAME_PLACEHOLDER', pending['dev_username'])
            bot_code = bot_code.replace('CHANNELS_PLACEHOLDER', str(pending['channels']))

            await msg.edit('⏳ **جاري انشاء البوت...**\n\n2/4 رفع الكود على GitHub...')

            # 3. رفع على GitHub
            repo_name = f"bot-{pending['dev_username'].lower()}-{random.randint(1000,9999)}"
            headers = {
                'Authorization': f'token {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json'
            }

            # انشاء الريبو
            repo_data = {
                'name': repo_name,
                'description': f'Bot for @{pending["dev_username"]} - Generated by Factory',
                'private': False,
                'auto_init': True
            }
            r = requests.post('https://api.github.com/user/repos', json=repo_data, headers=headers)

            if r.status_code!= 201:
                raise Exception(f'GitHub: {r.json().get("message", "Error")}')

            repo_url = r.json()['html_url']
            repo_full_name = r.json()['full_name']

            # رفع الملفات
            files = {
                'main.py': bot_code,
                'requirements.txt': 'telethon==1.36.0\nrequests==2.31.0',
                'Procfile': 'worker: python main.py',
                'runtime.txt': 'python-3.11.9'
            }

            for file_path, content in files.items():
                file_data = {
                    'message': f'Add {file_path}',
                    'content': base64.b64encode(content.encode()).decode()
                }
                requests.put(
                    f'https://api.github.com/repos/{repo_full_name}/contents/{file_path}',
                    json=file_data,
                    headers=headers
                )

            await msg.edit('⏳ **جاري انشاء البوت...**\n\n3/4 تجهيز رابط Railway...')

            # 4. تعطيل الكود المستخدم
            db['codes'][pending['activation_code']]['used_by'] = uid
            db['used_codes'].append(pending['activation_code'])

            # حفظ بيانات البوت
            if 'bots' not in db:
                db['bots'] = {}
            db['bots'][repo_name] = {
                'owner': uid,
                'username': pending['dev_username'],
                'repo': repo_url,
                'created': True
            }

            await msg.edit('⏳ **جاري انشاء البوت...**\n\n4/4 تم ✅')

            # 5. رابط النشر
            railway_url = f"https://railway.app/new?template=https://github.com/{repo_full_name}&envs=BOT_TOKEN"

            await msg.edit(
                f'✅ **تم انشاء البوت بنجاح**\n\n'
                f'**الريبو:** {repo_url}\n'
                f'**المطور:** @{pending["dev_username"]}\n'
                f'**الكود المستخدم:** `{pending["activation_code"]}`\n\n'
                f'**الخطوة الاخيرة:**\n'
                f'1️⃣ دوس الزر تحت\n'
                f'2️⃣ حط التوكن ده في BOT_TOKEN:\n`{pending["token"]}`\n'
                f'3️⃣ دوس Deploy\n\n'
                f'⏱️ البوت هيشتغل خلال دقيقتين 🚀',
                buttons=[[Button.url("🚀 انشر على Railway الآن", railway_url)]]
            )

            del db['pending_bots'][str(uid)]
            save_db()

        except Exception as e:
            await msg.edit(f'❌ **حصل خطأ:**\n\n`{str(e)}`\n\nكلم @Devazf')

        return

    elif data == 'my_bots':
        user_bots = [v for k, v in db.get('bots', {}).items() if v['owner'] == uid]
        if not user_bots:
            await event.answer('معندكش بوتات لسه', alert=True)
            return
        text = '**🤖 بوتاتك:**\n\n'
        for b in user_bots:
            text += f'@{b["username"]}\n{b["repo"]}\n\n'
        await event.answer(text, alert=True)
        return

    elif data == 'support':
        await event.answer('كلم @Devazf', alert=True)
        return

print("✅ المصنع شغال...")
bot.run_until_disconnected()
