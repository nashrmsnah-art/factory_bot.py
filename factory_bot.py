import os, json, asyncio, random, string
from datetime import datetime, timedelta
from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession

API_ID = 31650696
API_HASH = "2829d6502df68cd12fab33cabf2851d2"
BOT_TOKEN = os.environ.get("BOT_TOKEN")
ADMIN_ID = 154919127
DEVELOPER_LINK = "https://t.me/Devazf"

bot = TelegramClient('factory', API_ID, API_HASH)
db_file = "factory_db.json"
db = {"users": {}, "activation_codes": {}, "pending_bots": {}, "all_bots": {}}
waiting_for = {}

DURATIONS = {
    '1m': {'name': 'شهر', 'days': 30},
    '3m': {'name': '3 شهور', 'days': 90},
    '6m': {'name': '6 شهور', 'days': 180},
    '1y': {'name': 'سنة', 'days': 365}
}

def load_db():
    global db
    try:
        with open(db_file, 'r', encoding='utf-8') as f: db = json.load(f)
    except: save_db()

def save_db():
    with open(db_file, 'w', encoding='utf-8') as f: json.dump(db, f, indent=2, ensure_ascii=False)

def get_user(uid):
    uid = str(uid)
    if uid not in db['users']:
        db['users'][uid] = {'activated': False, 'bots': [], 'activation_code': None, 'activated_at': None, 'bots_allowed': 0, 'bots_used': 0}
        save_db()
    return db['users'][uid]

def can_create_bot(uid):
    user = get_user(uid)
    if uid == ADMIN_ID: return True, None
    if not user['activated']: return False, 'المصنع غير مفعل'
    if user['bots_used'] >= user['bots_allowed']: return False, 'استنفذت عدد البوتات المسموح'
    return True, None

def generate_code(length=8):
    return 'VIP-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_bot_file(data):
    with open('bot_template.py', 'r', encoding='utf-8') as f:
        template = f.read()
    return template.format(**data)

def create_bot_menu(uid):
    pending = db['pending_bots'].get(str(uid), {})
    token = '✅ تم' if pending.get('token') else '❌ مطلوب'
    admin = '✅ تم' if pending.get('admin_id') else '❌ مطلوب'
    dev = pending.get('dev_username', '❌ مطلوب')
    channels = '✅ تم' if pending.get('channels') else '➖ اختياري'
    paid = '💰 مدفوع' if pending.get('is_paid') else '🆓 مجاني'
    duration = DURATIONS.get(pending.get('duration'), {'name': '❌ مطلوب'})['name']

    return [
        [Button.inline(f'🔑 توكن البوت: {token}', b'set_token')],
        [Button.inline(f'👑 ايدي الادمن: {admin}', b'set_admin')],
        [Button.inline(f'👨‍💻 يوزر المطور: {dev}', b'set_dev')],
        [Button.inline(f'📢 قناة الاشتراك: {channels}', b'set_channels')],
        [Button.inline(f'💎 نوع البوت: {paid}', b'toggle_bot_type')],
        [Button.inline(f'⏰ الصلاحية: {duration}', b'set_duration')],
        [Button.inline('✅ انشاء البوت الآن', b'generate_bot')],
        [Button.inline('🔙 رجوع', b'back_main')]
    ]

def admin_menu():
    return [
        [Button.inline('🎫 توليد كود - شهر', b'gen_code_1m')],
        [Button.inline('🎫 توليد كود - 3 شهور', b'gen_code_3m')],
        [Button.inline('🎫 توليد كود - 6 شهور', b'gen_code_6m')],
        [Button.inline('🎫 توليد كود - سنة', b'gen_code_1y')],
        [Button.inline('🤖 التحكم في البوتات', b'control_bots')],
        [Button.inline('📋 كل الاكواد', b'list_codes')],
        [Button.inline('👥 كل العملاء', b'list_users')],
        [Button.inline('🔙 رجوع', b'back_main')]
    ]

@bot.on(events.NewMessage(pattern='/start'))
async def factory_start(event):
    uid = event.sender_id
    user = get_user(uid)

    if not user['activated'] and uid!= ADMIN_ID:
        await event.reply(f'''🔒 **المصنع مدفوع**

للتفعيل اطلب كود من المطور

👨‍💻 المطور: {DEVELOPER_LINK}''', buttons=[[Button.inline('🎫 ادخال كود التفعيل', b'enter_factory_code')]])
        return

    bots_left = user['bots_allowed'] - user['bots_used']
    code_text = f'`{user["activation_code"]}`' if user["activation_code"] else 'لا يوجد'
    text = f'''🏭 **مصنع بوتات النشر المتطور**

👤 حسابك: مفعل ✅
🎫 كودك: {code_text}
🤖 البوتات المسموح: {user["bots_allowed"]}
📊 المستخدم: {user["bots_used"]}
✅ المتبقي: {bots_left}

👨‍💻 المطور: {DEVELOPER_LINK}'''

    btns = [
        [Button.inline("🤖 انشاء بوت جديد", b"create_bot")],
        [Button.inline("📊 بوتاتي", b"my_bots")],
        [Button.inline("🎫 اكواد VIP لبوتاتي", b"get_vip_codes")]
    ]
    if uid == ADMIN_ID: btns.append([Button.inline("👑 لوحة الادمن", b"admin_panel")])
    await event.reply(text, buttons=btns)

@bot.on(events.CallbackQuery)
async def factory_callback(event):
    uid = event.sender_id; data = event.data.decode(); user = get_user(uid)

    if data == 'enter_factory_code':
        waiting_for[uid] = 'factory_code'
        await event.edit('''🎫 **ارسل كود تفعيل المصنع:**

اطلبه من المطور''', buttons=[[Button.inline('🔙 رجوع', b'back_main')]])
        return

    if not user['activated'] and uid!= ADMIN_ID and data!= 'back_main':
        await event.answer('❌ المصنع غير مفعل', alert=True); return

    if data == 'create_bot':
        can_create, reason = can_create_bot(uid)
        if not can_create:
            await event.answer(f'❌ {reason}', alert=True); return
        db['pending_bots'][str(uid)] = {'is_paid': False, 'duration': '1m'}
        save_db()
        await event.edit('''🤖 **انشاء بوت جديد**

املأ البيانات المطلوبة بالازرار:''', buttons=create_bot_menu(uid))
        return

    if data == 'set_token':
        waiting_for[uid] = 'bot_token'
        await event.edit('''🔑 **ارسل توكن البوت من @BotFather:**''', buttons=[[Button.inline('🔙 رجوع', b'create_bot')]])
        return

    if data == 'set_admin':
        waiting_for[uid] = 'admin_id'
        await event.edit('''👑 **ارسل ايدي الادمن للبوت:**

هاته من @userinfobot''', buttons=[[Button.inline('🔙 رجوع', b'create_bot')]])
        return

    if data == 'set_dev':
        waiting_for[uid] = 'dev_username'
        await event.edit('''👨‍💻 **ارسل يوزر المطور:**

مثال: @VIP1ST1''', buttons=[[Button.inline('🔙 رجوع', b'create_bot')]])
        return

    if data == 'set_channels':
        waiting_for[uid] = 'channels'
        await event.edit('''📢 **ارسل قنوات الاشتراك الاجباري:**

كل قناة في سطر
مثال:
@ch1
@ch2

اكتب skip للتخطي:''', buttons=[[Button.inline('🔙 رجوع', b'create_bot')]])
        return

    if data == 'toggle_bot_type':
        pending = db['pending_bots'].get(str(uid), {})
        pending['is_paid'] = not pending.get('is_paid', False)
        db['pending_bots'][str(uid)] = pending; save_db()
        await event.edit('''🤖 **انشاء بوت جديد**

املأ البيانات المطلوبة بالازرار:''', buttons=create_bot_menu(uid))
        return

    if data == 'set_duration':
        pending = db['pending_bots'].get(str(uid), {})
        current = pending.get('duration', '1m')
        durations = list(DURATIONS.keys())
        next_idx = (durations.index(current) + 1) % len(durations)
        pending['duration'] = durations[next_idx]
        db['pending_bots'][str(uid)] = pending; save_db()
        await event.edit('''🤖 **انشاء بوت جديد**

املأ البيانات المطلوبة بالازرار:''', buttons=create_bot_menu(uid))
        return

    if data == 'generate_bot':
        can_create, reason = can_create_bot(uid)
        if not can_create:
            await event.answer(f'❌ {reason}', alert=True); return
        pending = db['pending_bots'].get(str(uid), {})
        if not pending.get('token') or not pending.get('admin_id'):
            await event.answer('❌ لازم تدخل التوكن وايدي الادمن اول', alert=True); return

        await event.edit('⏳ **جاري انشاء البوت...**')
        try:
            duration_key = pending.get('duration', '1m')
            expiry_date = (datetime.now() + timedelta(days=DURATIONS[duration_key]['days'])).isoformat()

            bot_data = {
                'BOT_TOKEN': pending['token'],
                'ADMIN_ID': pending['admin_id'],
                'DEVELOPER_LINK': pending.get('dev_username', DEVELOPER_LINK),
                'FORCE_SUB_CHANNELS': repr(pending.get('channels', [])),
                'IS_PAID_BOT': pending.get('is_paid', False),
                'EXPIRY_DATE': f'"{expiry_date}"',
                'FACTORY_ADMIN_ID': ADMIN_ID
            }
            bot_code = generate_bot_file(bot_data)
            filename = f'bot_{uid}_{random.randint(1000,9999)}.py'
            with open(filename, 'w', encoding='utf-8') as f: f.write(bot_code)

            test_client = TelegramClient(StringSession(), API_ID, API_HASH)
            await test_client.start(bot_token=pending['token'])
            me = await test_client.get_me()
            await test_client.disconnect()

            bot_info = {
                'username': me.username,
                'token': pending['token'],
                'created': datetime.now().isoformat(),
                'is_paid': pending.get('is_paid', False),
                'expiry': expiry_date,
                'duration': duration_key,
                'owner_id': uid,
                'disabled': False
            }
            user['bots'].append(bot_info)
            db['all_bots'][me.username] = bot_info
            user['bots_used'] += 1
            del db['pending_bots'][str(uid)]
            save_db()

            bot_type = '💰 مدفوع' if pending.get('is_paid', False) else '🆓 مجاني'
            exp_date = datetime.fromisoformat(expiry_date).strftime('%Y-%m-%d')
            await event.reply(f'''✅ **تم انشاء البوت بنجاح**

🤖 @{me.username}
💎 النوع: {bot_type}
⏰ الصلاحية: {DURATIONS[duration_key]["name"]}
📅 ينتهي: {exp_date}

📁 **الملف جاهز للرفع على Railway**

**تعليمات:**
1. ارفع الملف على GitHub
2. Railway → New Project
3. Variables: BOT_TOKEN = {pending["token"]}
4. Deploy

⚠️ **البوت هيقف تلقائياً بعد انتهاء الصلاحية**''', file=filename)
        except Exception as e:
            await event.reply(f'''❌ **خطأ:** {str(e)}

تأكد من التوكن''')
        return

    if data == 'my_bots':
        if not user['bots']: await event.answer('❌ ماعندكش بوتات', alert=True); return
        text = f'📊 **بوتاتك: {len(user["bots"])}**\n\n'
        for i, b in enumerate(user['bots']):
            b_type = '💰' if b.get('is_paid') else '🆓'
            exp = datetime.fromisoformat(b['expiry']).strftime('%Y-%m-%d')
            expired = '🔴 منتهي' if datetime.now() > datetime.fromisoformat(b['expiry']) else '🟢'
            disabled = '⛔ موقوف' if b.get('disabled') else ''
            text += f'{i+1}. @{b["username"]} {b_type} {expired} {disabled}\n ينتهي: {exp}\n'
        await event.edit(text, buttons=[[Button.inline('🔙 رجوع', b'back_main')]])
        return

    if data == 'get_vip_codes':
        code = f'VIP{random.randint(100000, 999999)}'
        db['activation_codes'][code] = {'type': 'vip', 'owner': uid, 'created': datetime.now().isoformat(), 'used': False}
        save_db()
        await event.edit(f'''🎫 **كود VIP لبوتاتك:**

`{code}`

استخدمه في اي بوت صنعته /redeem''', buttons=[[Button.inline('🔙 رجوع', b'back_main')]])
        return

    if data == 'control_bots' and uid == ADMIN_ID:
        if not db['all_bots']:
            await event.answer('❌ مفيش بوتات مصنوعة لسه', alert=True); return
        btns = []
        for bot_username, bot_data in list(db['all_bots'].items())[-10:]:
            status = '⛔ موقوف' if bot_data.get('disabled') else '✅ شغال'
            btns.append([Button.inline(f'@{bot_username} - {status}', f'toggle_bot_{bot_username}')])
        btns.append([Button.inline('🔙 رجوع', b'admin_panel')])
        await event.edit('''🤖 **التحكم في البوتات المصنوعة**

دوس على البوت عشان تقفله او تشغله:''', buttons=btns)
        return

    if data.startswith('toggle_bot_') and uid == ADMIN_ID:
        bot_username = data.replace('toggle_bot_', '')
        if bot_username in db['all_bots']:
            db['all_bots'][bot_username]['disabled'] = not db['all_bots'][bot_username].get('disabled', False)
            # حدث في بوتات العميل كمان
            for user_id, user_data in db['users'].items():
                for b in user_data.get('bots', []):
                    if b['username'] == bot_username:
                        b['disabled'] = db['all_bots'][bot_username]['disabled']
            save_db()
            status = 'موقوف ⛔' if db['all_bots'][bot_username]['disabled'] else 'شغال ✅'
            await event.answer(f'تم تحديث حالة @{bot_username} - {status}', alert=True)
            await factory_callback(event) # refresh
        return

    if data.startswith('gen_code_') and uid == ADMIN_ID:
        duration_key = data.split('_')[-1]
        code = generate_code()
        db['activation_codes'][code] = {
            'type': 'factory',
            'used': False,
            'created': datetime.now().isoformat(),
            'user_id': None,
            'duration': duration_key,
            'bots_allowed': 1
        }
        save_db()
        await event.answer(f'✅ تم توليد كود: {code}', alert=True)
        await event.edit(f'''🎫 **كود تفعيل جديد:**

`{code}`

⏰ الصلاحية: {DURATIONS[duration_key]["name"]}
🤖 البوتات: 1 فقط

ارسله للعميل عشان يفعل المصنع''', buttons=admin_menu())
        return

    if data == 'admin_panel' and uid == ADMIN_ID:
        total_bots = sum(len(u.get('bots', [])) for u in db['users'].values())
        activated = sum(1 for u in db['users'].values() if u.get('activated'))
        total_codes = len(db['activation_codes'])
        used_codes = sum(1 for c in db['activation_codes'].values() if c.get('used'))
        disabled_bots = sum(1 for b in db['all_bots'].values() if b.get('disabled'))
        text = f'''👑 **لوحة ادمن المصنع**

👥 العملاء: {len(db["users"])}
✅ المفعلين: {activated}
🤖 البوتات: {total_bots}
⛔ الموقوف: {disabled_bots}
🎫 الاكواد: {used_codes}/{total_codes}'''
        await event.edit(text, buttons=admin_menu())
        return

    if data == 'list_codes' and uid == ADMIN_ID:
        unused = [(c, d) for c, d in db['activation_codes'].items() if not d.get('used')]
        used = [(c, d) for c, d in db['activation_codes'].items() if d.get('used')]
        text = f'''📋 **كل الاكواد**

🟢 غير مستخدم: {len(unused)}
🔴 مستخدم: {len(used)}

**اخر 10 غير مستخدم:**
'''
        for c, d in unused[-10:]:
            dur = DURATIONS.get(d.get('duration', '1m'), {'name': 'شهر'})['name']
            text += f'`{c}` - {dur}\n'
        await event.edit(text or 'لا يوجد', buttons=admin_menu())
        return

    if data == 'list_users' and uid == ADMIN_ID:
        text = '👥 **العملاء:**\n\n'
        for uid_str, u_data in list(db['users'].items())[-15:]:
            status = '✅' if u_data.get('activated') else '❌'
            bots = f"{u_data.get('bots_used', 0)}/{u_data.get('bots_allowed', 0)}"
            text += f'{status} `{uid_str}` - {bots} بوت\n'
        await event.edit(text, buttons=admin_menu())
        return

    if data == 'back_main': await factory_start(event); return

@bot.on(events.NewMessage)
async def factory_handle(event):
    uid = event.sender_id
    if uid not in waiting_for: return
    action = waiting_for[uid]; text = event.raw_text.strip()

    if action == 'factory_code':
        if text in db['activation_codes'] and not db['activation_codes'][text].get('used'):
            code_data = db['activation_codes'][text]
            code_data['used'] = True
            code_data['user_id'] = uid
            user = get_user(uid)
            user['activated'] = True
            user['activation_code'] = text
            user['activated_at'] = datetime.now().isoformat()
            user['bots_allowed'] = code_data.get('bots_allowed', 1)
            user['bots_used'] = 0
            save_db(); del waiting_for[uid]
            dur_name = DURATIONS.get(code_data.get('duration', '1m'), {'name': 'شهر'})['name']
            await event.reply(f'''✅ **تم تفعيل المصنع بنجاح**

⏰ الصلاحية: {dur_name}
🤖 البوتات المسموح: {user["bots_allowed"]}

تقدر دلوقتي تصنع بوت'''); await factory_start(event)
        else:
            await event.reply('''❌ **كود غلط او مستخدم قبل كده**

اطلب كود جديد من المطور''')
        return

    if action == 'bot_token':
        if text.count(':')!= 1: await event.reply('❌ **توكن غلط**'); return
        db['pending_bots'][str(uid)]['token'] = text; save_db(); del waiting_for[uid]
        await event.reply('✅ **تم حفظ التوكن**'); await event.respond('''🤖 **انشاء بوت جديد**

املأ البيانات المطلوبة بالازرار:''', buttons=create_bot_menu(uid))
        return

    if action == 'admin_id':
        try:
            admin_id = int(text)
            db['pending_bots'][str(uid)]['admin_id'] = admin_id; save_db(); del waiting_for[uid]
            await event.reply('✅ **تم حفظ ايدي الادمن**'); await event.respond('''🤖 **انشاء بوت جديد**

املأ البيانات المطلوبة بالازرار:''', buttons=create_bot_menu(uid))
        except: await event.reply('❌ **ارسل رقم صحيح**')
        return

    if action == 'dev_username':
        if not text.startswith('@'): text = '@' + text
        db['pending_bots'][str(uid)]['dev_username'] = text; save_db(); del waiting_for[uid]
        await event.reply('✅ **تم حفظ يوزر المطور**'); await event.respond('''🤖 **انشاء بوت جديد**

املأ البيانات المطلوبة بالازرار:''', buttons=create_bot_menu(uid))
        return

    if action == 'channels':
        if text.lower() == 'skip': channels = []
        else: channels = [ch.strip() for ch in text.split('\n') if ch.strip().startswith('@')]
        db['pending_bots'][str(uid)]['channels'] = channels; save_db(); del waiting_for[uid]
        await event.reply(f'✅ **تم حفظ {len(channels)} قناة**'); await event.respond('''🤖 **انشاء بوت جديد**

املأ البيانات المطلوبة بالازرار:''', buttons=create_bot_menu(uid))
        return

async def main():
    load_db()
    await bot.start(bot_token=BOT_TOKEN)
    print('🏭 Factory Bot Started...')
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
