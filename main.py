import json, os, subprocess, time, asyncio, random, shutil, sys, re
from telethon import TelegramClient, events, Button

# ===================== الإعدادات =====================
API_ID = 37879014
API_HASH = "db129fe3286650ad869b2891abd72df2"
BOT_TOKEN = "8761534960:AAE79eePv-ySF2H_i_3Er6aDcRWN7opu8j8"
ADMIN_IDS = [29449730] # حط أيديك هنا

FACTORY_CHANNEL = "F2F2FFF" # بدون @
FACTORY_CHANNEL_LINK = "https://t.me/F2F2FFF"
BOT_FOLDER = "bots"

# ===================== البداية =====================
os.makedirs(BOT_FOLDER, exist_ok=True)
bot = TelegramClient('factory_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ===================== تحميل البيانات =====================
def load_json(file, default):
    return json.load(open(file, encoding='utf-8')) if os.path.exists(file) else default

data = load_json('data.json', {})
codes = load_json('codes.json', {})
processes = load_json('processes.json', {})
user_state = {}

def save_all():
    json.dump(data, open('data.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    json.dump(codes, open('codes.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
    json.dump(processes, open('processes.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=2)

def is_expired(uid):
    return uid not in data or time.time() > data[uid]['expire_at']

# ===================== فحص الاشتراك الإجباري =====================
async def check_subscription(user_id):
    try:
        await bot.get_participants(FACTORY_CHANNEL, filter=user_id)
        return True
    except:
        return False

# ===================== تشغيل/إيقاف البوتات =====================
async def start_bot(uid):
    if is_expired(uid):
        await bot.send_message(int(uid), "❌ اشتراكك منتهي")
        return False

    data[uid]['status'] = 'starting'
    save_all()

    template_path = "bot_template.py"
    bot_path = f"{BOT_FOLDER}/bot_{uid}.py"

    if not os.path.exists(bot_path):
        shutil.copy(template_path, bot_path)

    if os.name == 'nt':
        proc = subprocess.Popen([sys.executable, bot_path, uid], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    else:
        proc = subprocess.Popen([sys.executable, bot_path, uid], start_new_session=True)

    processes[uid] = proc.pid
    data[uid]['status'] = 'active'
    save_all()

    await bot.send_message(int(uid), "⏳ جاري تشغيل البوت...")
    await asyncio.sleep(2)
    await bot.send_message(int(uid), "✅ تم تشغيل البوت بنجاح!")
    return True

async def stop_bot(uid):
    if uid in processes:
        try:
            pid = processes[uid]
            if pid!= "auto":
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/F', '/PID', str(pid)], check=False)
                else:
                    subprocess.run(['kill', '-9', str(pid)], check=False)
        except Exception as e:
            print(f"Error stopping bot {uid}: {e}")
        processes.pop(uid)

    data[uid]['status'] = 'stopped'
    save_all()

async def auto_start_bots():
    print("🚀 جاري تشغيل البوتات الفعالة...")
    count = 0
    for uid, info in data.items():
        if info.get('status') == 'active' and not is_expired(uid):
            bot_path = f"{BOT_FOLDER}/bot_{uid}.py"
            if os.path.exists(bot_path):
                try:
                    if os.name == 'nt':
                        proc = subprocess.Popen([sys.executable, bot_path, uid], creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
                    else:
                        proc = subprocess.Popen([sys.executable, bot_path, uid], start_new_session=True)
                    processes[uid] = proc.pid
                    count += 1
                except Exception as e:
                    print(f"Failed to start {uid}: {e}")
    print(f"✅ تم تشغيل {count} بوت")
    save_all()

# ===================== /start والترحيب =====================
@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = str(event.sender_id)
    name = event.sender.first_name or "مستخدم"

    # فحص الاشتراك الإجباري
    if not await check_subscription(event.sender_id):
        text = "**لازم تشترك في قناة المصنع الأول** 🔒\n\n"
        text += "اشترك وبعدين اضغط تحقق عشان تقدر تستخدم المصنع"
        buttons = [
            [Button.url("📢 اشترك هنا", FACTORY_CHANNEL_LINK)],
            [Button.inline("✅ تحققت", b"check_sub")]
        ]
        return await event.respond(text, buttons=buttons, parse_mode='md')

    is_admin = event.sender_id in ADMIN_IDS
    has_bot = uid in data and not is_expired(uid)

    text = f"**مرحباً {name} 👋**\n"
    text += "**مصنع بوتات النشر الاحترافي** 🚀\n\n"
    text += "اصنع بوت نشر بضغطة زر مع نظام إجباري اشتراك ولوحة تحكم كاملة\n"
    text += "────────────────────\n"

    if is_admin:
        text += "**لوحة المطور** 👑"
        buttons = [
            [Button.inline("📊 البوتات الفعالة", b"dev_bots"),
             Button.inline("📈 الإحصائيات", b"dev_stats")],
            [Button.inline("🔑 توليد كود", b"gen_code"),
             Button.inline("📋 كل الأكواد", b"list_codes")],
            [Button.inline("🔄 إعادة تشغيل الكل", b"restart_all")]
        ]
    elif has_bot:
        expire = time.strftime("%Y-%m-%d", time.localtime(data[uid]['expire_at']))
        status_emoji = "🟢" if data[uid]['status'] == 'active' else "🔴"
        sup_price = data[uid].get('sup_price', 0)

        text += f"**حالتك:** {status_emoji} {data[uid]['status']}\n"
        text += f"**ينتهي:** `{expire}`\n"
        text += f"**البوت:** @{data[uid]['username']}\n"
        text += f"**سعر البوت:** {sup_price} جنيه\n"

        buttons = [
            [Button.inline("🎛️ التحكم بالبوت", b"manage_bot"),
             Button.inline("📊 معلومات", b"bot_info")],
            [Button.inline("💬 الدعم الفني", url="https://t.me/your_username")]
        ]
    else:
        text += "مفيش بوت شغال عندك حالياً\n"
        text += "اشتري كود اشتراك وابدأ في دقيقتين 👇"
        buttons = [
            [Button.inline("🚀 إنشاء بوت جديد", b"create")],
            [Button.inline("💰 الأسعار", b"pricing"),
             Button.inline("❓ المساعدة", b"help")],
            [Button.inline("💬 الدعم الفني", url="https://t.me/your_username")]
        ]

    await event.respond(text, buttons=buttons, parse_mode='md', link_preview=False)

@bot.on(events.CallbackQuery(data=b'check_sub'))
async def check_sub(event):
    if await check_subscription(event.sender_id):
        await event.delete()
        await start(event)
    else:
        await event.answer("❌ لسه مش مشترك في القناة", alert=True)

# ===================== توليد الأكواد =====================
@bot.on(events.CallbackQuery(data=b'gen_code'))
async def gen_code(event):
    if event.sender_id not in ADMIN_IDS: return
    await event.edit("اختر نوع الكود:", buttons=[
        [Button.inline("📅 شهر - 30 يوم", b"code_month")],
        [Button.inline("📅 سنة - 365 يوم", b"code_year")],
        [Button.inline("🔙 رجوع", b"back")]
    ])

@bot.on(events.CallbackQuery(data=re.compile(b'code_(.*)')))
async def create_code(event):
    if event.sender_id not in ADMIN_IDS: return
    code_type = event.pattern_match.group(1).decode()

    days = 30 if code_type == 'month' else 365
    code = f"{'MONTH' if code_type=='month' else 'YEAR'}_{random.randint(1000,9999)}_{random.randint(100,999)}"

    codes[code] = {'type': code_type, 'days': days, 'used': False, 'created_by': event.sender_id}
    save_all()

    await event.edit(f"✅ تم توليد كود {code_type}\n\n`{code}`\n\nصالح {days} يوم\nاستخدام: مرة واحدة فقط", parse_mode='md')

@bot.on(events.CallbackQuery(data=b'list_codes'))
async def list_codes(event):
    if event.sender_id not in ADMIN_IDS: return
    text = "**آخر 20 كود:**\n\n"
    for code, info in list(codes.items())[-20:]:
        status = "✅ مستخدم" if info['used'] else "🟢 متاح"
        text += f"`{code}`\n نوع: {info['type']} | {info['days']} يوم | {status}\n\n"
    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"back")]], parse_mode='md')

# ===================== إنشاء بوت جديد =====================
@bot.on(events.CallbackQuery(data=b'create'))
async def create(event):
    uid = str(event.sender_id)
    if uid in data and not is_expired(uid):
        return await event.edit("❌ عندك بوت شغال بالفعل\nاحذفه الأول لو عايز تعمل واحد جديد")

    await event.edit("🔐 ابعت كود الاشتراك اللي خدته من المطور:")
    user_state[uid] = {'step': 'code'}

@bot.on(events.NewMessage())
async def handle_steps(event):
    uid = str(event.sender_id)
    if uid not in user_state: return

    step = user_state[uid]['step']

    if step == 'code':
        code = event.text.strip()
        if code not in codes or codes[code]['used']:
            return await event.respond("❌ كود غلط أو مستخدم من قبل")

        user_state[uid]['code'] = code
        user_state[uid]['step'] = 'bot_id'
        await event.respond("1️⃣ ابعت **أيدي البوت** الرقمي\nتقدر تجيبه من @userinfobot")

    elif step == 'bot_id':
        if not event.text.isdigit():
            return await event.respond("❌ الأيدي لازم يكون أرقام فقط")
        user_state[uid]['bot_id'] = event.text
        user_state[uid]['step'] = 'token'
        await event.respond("2️⃣ ابعت **توكن البوت**\nمن @BotFather")

    elif step == 'token':
        user_state[uid]['token'] = event.text.strip()
        user_state[uid]['step'] = 'username'
        await event.respond("3️⃣ ابعت **يوزر البوت** بدون @")

    elif step == 'username':
        user_state[uid]['username'] = event.text.replace('@', '')
        user_state[uid]['step'] = 'channel'
        await event.respond("4️⃣ ابعت **يوزر قناة الإجباري** بدون @\n\n⚠️ لازم تضيف البوت أدمن في القناة")

    elif step == 'channel':
        channel = event.text.replace('@', '')
        user_state[uid]['channel'] = channel
        user_state[uid]['step'] = 'sup_price'
        await event.respond("5️⃣ ابعت **سعر البوت** اللي هيتباع بيه للعملاء\nاكتب رقم فقط، مثال: 50")

    elif step == 'sup_price':
        if not event.text.isdigit():
            return await event.respond("❌ اكتب رقم صحيح فقط")

        sup_price = int(event.text)
        info = user_state[uid]
        channel = info['channel']

        # التحقق من الأدمن في القناة
        try:
            client = TelegramClient(f'check_{uid}', API_ID, API_HASH).start(bot_token=info['token'])
            admins = await client.get_participants(channel, filter='admins')
            is_admin = any(getattr(admin, 'username', '') == info['username'] for admin in admins)
            await client.disconnect()

            if not is_admin:
                await event.respond("❌ البوت مش أدمن في القناة!\nضيفه كأدمن وجرب تاني")
                return
        except Exception as e:
            await event.respond(f"❌ حصل خطأ في التحقق:\n`{e}`", parse_mode='md')
            return

        # حفظ وتفعيل
        code_info = codes[info['code']]
        expire_at = time.time() + (code_info['days'] * 86400)

        data[uid] = {
            'bot_id': info['bot_id'],
            'token': info['token'],
            'username': info['username'],
            'channel': channel,
            'sup_price': sup_price,
            'code': info['code'],
            'expire_at': expire_at,
            'status': 'stopped',
            'created_at': time.time()
        }
        codes[info['code']]['used'] = True
        save_all()

        await event.respond(f"✅ تم التسجيل بنجاح!\n💰 سعر البوت: {sup_price} جنيه\nجاري تشغيل البوت...")
        await start_bot(uid)
        user_state.pop(uid)

# ===================== لوحة التحكم =====================
@bot.on(events.CallbackQuery(data=b'manage_bot'))
async def manage_bot(event):
    uid = str(event.sender_id)
    if uid not in data: return

    status = data[uid]['status']
    expire = time.strftime("%Y-%m-%d %H:%M", time.localtime(data[uid]['expire_at']))
    sup_price = data[uid].get('sup_price', 0)

    text = f"**التحكم بالبوت** 🎛️\n\n"
    text += f"**الحالة:** {'🟢 شغال' if status=='active' else '🔴 متوقف'}\n"
    text += f"**ينتهي:** `{expire}`\n"
    text += f"**البوت:** @{data[uid]['username']}\n"
    text += f"**القناة:** @{data[uid]['channel']}\n"
    text += f"**سعر البوت:** {sup_price} جنيه\n"

    btn = []
    if status == 'active':
        btn.append([Button.inline("⏸️ تعطيل البوت", b"stop_bot")])
    else:
        btn.append([Button.inline("▶️ تشغيل البوت", b"start_bot")])

    btn += [
        [Button.inline("🔄 إعادة تشغيل", b"restart_bot")],
        [Button.inline("🗑️ حذف البوت", b"delete_bot")],
        [Button.inline("🔙 رجوع", b"back")]
    ]

    await event.edit(text, buttons=btn, parse_mode='md')

@bot.on(events.CallbackQuery(data=b'start_bot'))
async def start_bot_btn(event):
    uid = str(event.sender_id)
    await event.edit("⏳ جاري تشغيل البوت...")
    success = await start_bot(uid)
    if success:
        await event.edit("✅ تم تشغيل البوت بنجاح!")

@bot.on(events.CallbackQuery(data=b'stop_bot'))
async def stop_bot_btn(event):
    uid = str(event.sender_id)
    await event.edit("⏸️ جاري تعطيل البوت...")
    await stop_bot(uid)
    await event.edit("✅ تم تعطيل البوت")

@bot.on(events.CallbackQuery(data=b'restart_bot'))
async def restart_bot(event):
    uid = str(event.sender_id)
    await event.edit("🔄 جاري إعادة التشغيل...")
    await stop_bot(uid)
    await asyncio.sleep(1)
    await start_bot(uid)

@bot.on(events.CallbackQuery(data=b'delete_bot'))
async def delete_bot(event):
    uid = str(event.sender_id)
    await event.edit("⚠️ متأكد إنك عايز تحذف البوت؟\nمش هتقدر ترجعه", buttons=[
        [Button.inline("✅ نعم احذف", b"confirm_delete")],
        [Button.inline("❌ إلغاء", b"manage_bot")]
    ])

@bot.on(events.CallbackQuery(data=b'confirm_delete'))
async def confirm_delete(event):
    uid = str(event.sender_id)
    await stop_bot(uid)
    bot_path = f"{BOT_FOLDER}/bot_{uid}.py"
    if os.path.exists(bot_path):
        os.remove(bot_path)
    data.pop(uid)
    save_all()
    await event.edit("🗑️ تم حذف البوت والملف نهائياً")

# ===================== لوحة المطور =====================
@bot.on(events.CallbackQuery(data=b'dev_bots'))
async def dev_bots(event):
    if event.sender_id not in ADMIN_IDS: return

    active = sum(1 for u, i in data.items() if i['status']=='active' and not is_expired(u))
    total = len(data)

    text = f"**إحصائيات سريعة**\n"
    text += f"البوتات الفعالة: {active}\n"
    text += f"إجمالي العملاء: {total}\n\n"
    text += "**آخر 10 عملاء:**\n\n"

    count = 0
    for uid, info in list(data.items())[-10:]:
        count += 1
        status = "🟢" if info['status']=='active' else "🔴"
        expire = time.strftime("%m-%d", time.localtime(info['expire_at']))
        sup_price = info.get('sup_price', 0)
        text += f"{count}. {status} `{uid}`\n"
        text += f" @{info['username']} | سعر: {sup_price} | ينتهي: {expire}\n\n"

    if count == 0:
        text = "مفيش عملاء لسه"

    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"back")]], parse_mode='md')

@bot.on(events.CallbackQuery(data=b'restart_all'))
async def restart_all(event):
    if event.sender_id not in ADMIN_IDS: return
    await event.edit("⏳ جاري إعادة تشغيل كل البوتات...")
    await auto_start_bots()
    await event.edit("✅ تم إعادة تشغيل كل البوتات الفعالة")

@bot.on(events.CallbackQuery(data=b'pricing'))
async def pricing(event):
    text = """
**الأسعار والخطط** 💰

📅 **اشتراك شهر**
- 30 يوم
- بوت نشر كامل
- لوحة تحكم
- دعم فني

📅 **اشتراك سنة**
- 365 يوم
- نفس المميزات
- سعر أفضل

للشراء تواصل مع المطور 👇
"""
    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"back")]], parse_mode='md')

@bot.on(events.CallbackQuery(data=b'help'))
async def help_btn(event):
    text = """
**طريقة الاستخدام** ❓

1. اشترك في قناة المصنع أولاً
2. اشتري كود اشتراك من المطور
3. اضغط إنشاء بوت وابعث الكود
4. ابعت بيانات البوت: الأيدي، التوكن، اليوزر، القناة، السعر
5. البوت هيشتغل أوتوماتيك
6. تحكم فيه من زر التحكم

**ملاحظة:** لازم تضيف البوت أدمن في قناة الإجباري
"""
    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"back")]], parse_mode='md')

@bot.on(events.CallbackQuery(data=b'back'))
async def back(event):
    await start(event)

# ===================== التشغيل =====================
async def main():
    await auto_start_bots()
    print("✅ المصنع شغال ومستعد")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nتم إيقاف المصنع")
