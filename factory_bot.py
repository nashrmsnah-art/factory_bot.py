import os
import json
import asyncio
import random
import requests
import base64
import string
import re
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

# ====== بيانات المصنع ======
API_ID = 31650696
API_HASH = '2829d6502df68cd12fab33cabf2851d2'
BOT_TOKEN = os.getenv('BOT_TOKEN')
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
RAILWAY_TOKEN = os.getenv('RAILWAY_TOKEN')
GITHUB_USERNAME = 'nashrmsnah-art'
ADMIN_ID = 154919127
DB_FILE = 'database.json'
BOT_PRICE = 10
BOT_TEMPLATE_URL = 'https://github.com/nashrmsnah-art/factory_bot.py/blob/835c615afc374b1da645ddf3b747cc9f61da3033/bot-template'

bot = TelegramClient('factory', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ====== قاعدة البيانات ======
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {'codes': {}, 'used_codes': [], 'bots': {}, 'pending_bots': {}, 'waiting_for': {}}

def save_db():
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

db = load_db()

# ====== اوامر الادمن ======
@bot.on(events.NewMessage(pattern='/gen'))
async def gen_code(event):
    if event.sender_id!= ADMIN_ID:
        return

    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    db['codes'][code] = {'created': True, 'used_by': None, 'price': BOT_PRICE}
    save_db()

    await event.reply(f'✅ **كود تفعيل جديد:**\n\n`{code}`\n\n💰 السعر: {BOT_PRICE}$\nالكود يستخدم مرة واحدة فقط')

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
    text += f'\n💰 **سعر الكود:** {BOT_PRICE}$'
    await event.reply(text)

@bot.on(events.NewMessage(pattern='/stats'))
async def stats(event):
    if event.sender_id!= ADMIN_ID:
        return

    total_bots = len(db.get('bots', {}))
    total_codes = len(db.get('codes', {}))
    used_codes = len([c for c, v in db['codes'].items() if v['used_by']])
    earnings = used_codes * BOT_PRICE

    text = f'**📊 احصائيات المصنع**\n\n'
    text += f'🤖 **البوتات المنشأة:** {total_bots}\n'
    text += f'🎟️ **الاكواد الكلية:** {total_codes}\n'
    text += f'✅ **الاكواد المستخدمة:** {used_codes}\n'
    text += f'💵 **الارباح:** {earnings}$\n'
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
    text = "**🤖 اهلا بيك في مصنع البوتات الاحترافي**\n\n"
    text += f"💰 **السعر:** {BOT_PRICE}$ للبوت الواحد\n"
    text += "⚡️ **رفع وتشغيل تلقائي** بالكامل\n"
    text += "🔐 **كود تفعيل** لكل بوت\n"
    text += "🚀 **دعم فني** 24/7\n\n"
    text += "كلم الادمن @Devazf عشان تشتري كود"
    await event.reply(text, buttons=btns)

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
            await event.reply('❌ **الكود غلط**\n\nكلم @Devazf عشان تشتري كود')
            return
        if db['codes'][text]['used_by']:
            await event.reply('❌ **الكود مستخدم قبل كده**')
            return

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

        btns = [[Button.inline("🚀 انشاء وتشغيل البوت الآن", "generate_bot")]]
        await event.reply(
            f'✅ **تم حفظ كل البيانات**\n\n'
            f'**الكود:** `{pending["activation_code"]}`\n'
            f'**التوكن:** `{pending["token"][:20]}...`\n'
            f'**الادمن:** `{pending["admin_id"]}`\n'
            f'**المطور:** @{pending["dev_username"]}\n'
            f'**القنوات:** {pending["channels"] or "مفيش"}\n\n'
            f'دوس الزر والمصنع هيعمل كل حاجة تلقائي 🚀',
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
            f'الكود بتحصل عليه بعد دفع {BOT_PRICE}$\n'
            'كلم @Devazf عشان تشتري كود\n\n'
            f'💰 سعر البوت: {BOT_PRICE}$'
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

        msg = await event.edit('⏳ **جاري انشاء البوت...**\n\n1/7 تحميل كود البوت...')

        try:
            # 1. تحميل كود البوت بتاعك من GitHub
            r = requests.get(BOT_TEMPLATE_URL)
            if r.status_code!= 200:
                raise Exception('فشل تحميل كود البوت من GitHub')
            bot_code = r.text

            # 2. تبديل البيانات
   import re
   bot_code = re.sub(r'BOT_TOKEN\s*=\s*["\'].*?["\']', 'BOT_TOKEN = os.getenv("BOT_TOKEN")', bot_code)
   bot_code = re.sub(r'ADMIN_ID\s*=\s*\d+', f'ADMIN_ID = {pending["admin_id"]}', bot_code)
   bot_code = re.sub(r'DEVELOPER_USERNAME\s*=\s*["\'].*?["\']', f'DEVELOPER_USERNAME = "{pending["dev_username"]}"', bot_code)
   bot_code = re.sub(r'REQUIRED_CHANNELS\s*=\s*\[.*?\]', f'REQUIRED_CHANNELS = {pending["channels"]}', bot_code)

            await msg.edit('⏳ **جاري انشاء البوت...**\n\n2/7 رفع على GitHub...')

            # 3. رفع على GitHub
            repo_name = f"bot-{pending['dev_username'].lower()}-{random.randint(1000,9999)}"
            github_headers = {
                'Authorization': f'token {GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json'
            }

            repo_data = {
                'name': repo_name,
                'description': f'Bot for @{pending["dev_username"]} - Auto Generated',
                'private': False,
                'auto_init': True
            }
            r = requests.post('https://api.github.com/user/repos', json=repo_data, headers=github_headers)

            if r.status_code!= 201:
                raise Exception(f'GitHub: {r.json().get("message", "Error")}')

            repo_url = r.json()['html_url']
            repo_full_name = r.json()['full_name']

   files = {
    'main.py': bot_code,
    'requirements.txt': 'telethon==1.36.0\nrequests==2.31.0\naiohttp==3.9.1\ncryptography==41.0.7\npycryptodome==3.19.0',
    'Procfile': 'worker: python main.py',
    'runtime.txt': 'python-3.11.9',
    'database.json': '{}',
    'sessions_backup.json': '{}'
}

            for file_path, content in files.items():
                file_data = {
                    'message': f'Add {file_path}',
                    'content': base64.b64encode(content.encode()).decode()
                }
                requests.put(
                    f'https://api.github.com/repos/{repo_full_name}/contents/{file_path}',
                    json=file_data,
                    headers=github_headers
                )

            await msg.edit('⏳ **جاري انشاء البوت...**\n\n3/7 انشاء مشروع Railway...')

            # 4. انشاء مشروع Railway
            railway_headers = {
                'Authorization': f'Bearer {RAILWAY_TOKEN}',
                'Content-Type': 'application/json'
            }

            project_query = '''
            mutation projectCreate($name: String!) {
                projectCreate(input: {name: $name}) {
                    id
                }
            }
            '''
            project_vars = {'name': repo_name}
            r = requests.post(
                'https://backboard.railway.app/graphql/v2',
                json={'query': project_query, 'variables': project_vars},
                headers=railway_headers
            )

            if 'errors' in r.json():
                raise Exception(f'Railway: {r.json()["errors"][0]["message"]}')

            project_id = r.json()['data']['projectCreate']['id']

            await msg.edit('⏳ **جاري انشاء البوت...**\n\n4/7 ربط GitHub مع Railway...')

            service_query = '''
            mutation serviceCreate($projectId: String!, $source: ServiceSourceInput!) {
                serviceCreate(input: {projectId: $projectId, source: $source}) {
                    id
                }
            }
            '''
            service_vars = {
                'projectId': project_id,
                'source': {'repo': f'{GITHUB_USERNAME}/{repo_name}'}
            }
            r = requests.post(
                'https://backboard.railway.app/graphql/v2',
                json={'query': service_query, 'variables': service_vars},
                headers=railway_headers
            )
            service_id = r.json()['data']['serviceCreate']['id']

            await msg.edit('⏳ **جاري انشاء البوت...**\n\n5/7 اضافة المتغيرات...')

            var_query = '''
            mutation variableUpsert($projectId: String!, $serviceId: String!, $name: String!, $value: String!) {
                variableUpsert(input: {projectId: $projectId, serviceId: $serviceId, name: $name, value: $value}) {
                    id
                }
            }
            '''
            var_vars = {
                'projectId': project_id,
                'serviceId': service_id,
                'name': 'BOT_TOKEN',
                'value': pending['token']
            }
            requests.post(
                'https://backboard.railway.app/graphql/v2',
                json={'query': var_query, 'variables': var_vars},
                headers=railway_headers
            )

            await msg.edit('⏳ **جاري انشاء البوت...**\n\n6/7 تشغيل البوت...')

            deploy_query = '''
            mutation serviceInstanceDeploy($serviceId: String!) {
                serviceInstanceDeploy(serviceId: $serviceId) {
                    id
                }
            }
            '''
            deploy_vars = {'serviceId': service_id}
            requests.post(
                'https://backboard.railway.app/graphql/v2',
                json={'query': deploy_query, 'variables': deploy_vars},
                headers=railway_headers
            )

            await msg.edit('⏳ **جاري انشاء البوت...**\n\n7/7 فحص البوت...')

            # 5. تعطيل الكود وحفظ البيانات
            db['codes'][pending['activation_code']]['used_by'] = uid
            db['used_codes'].append(pending['activation_code'])

            if 'bots' not in db:
                db['bots'] = {}
            db['bots'][repo_name] = {
                'owner': uid,
                'username': pending['dev_username'],
                'repo': repo_url,
                'project_id': project_id,
                'service_id': service_id,
                'created': True
            }

            # فحص ان البوت اشتغل
            await asyncio.sleep(15)
            test_bot = TelegramClient(StringSession(), API_ID, API_HASH)
            await test_bot.start(bot_token=pending['token'])
            me = await test_bot.get_me()
            await test_bot.disconnect()

            await msg.edit(
                f'✅ **تم انشاء وتشغيل البوت بنجاح**\n\n'
                f'**يوزر البوت:** @{me.username}\n'
                f'**المطور:** @{pending["dev_username"]}\n'
                f'**الكود المستخدم:** `{pending["activation_code"]}`\n\n'
                f'🚀 **البوت شغال دلوقتي** جرب تبعتله /start\n\n'
                f'الرابط: https://t.me/{me.username}\n\n'
                f'💰 تم خصم {BOT_PRICE}$ من رصيد الاكواد',
                buttons=[[Button.url("🤖 افتح البوت", f"https://t.me/{me.username}")]]
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
