import json, os, subprocess, time, asyncio, random, shutil, sys, re
from telethon import TelegramClient, events, Button
from telethon.tl.functions.channels import GetParticipantRequest
from telethon.tl.types import ChannelParticipantAdmin, ChannelParticipantCreator
from telethon.errors import UserNotParticipantError

# ==================== الإعدادات ====================
API_ID = 37879014
API_HASH = "db129fe3286650ad869b2891abd72df2"
BOT_TOKEN = "8761534960:AAE79eePv-ySF2H_i_3Er6aDcRWN7opu8j8"
FACTORY_CHANNEL = "F2F2FFF"
ADMIN_ID = 29449730

DATA_FILE = "bots_data.json"
BOTS_FOLDER = "bots"
TEMPLATES_FOLDER = "templates"
LOG_FILE = "factory.log"

os.makedirs(BOTS_FOLDER, exist_ok=True)
os.makedirs(TEMPLATES_FOLDER, exist_ok=True)

bot = TelegramClient("factory_bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)
user_states = {}
running_processes = {}

# ==================== اللوج ====================
def log(msg):
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {msg}\n"
    print(line.strip())
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)

# ==================== دوال البيانات ====================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"bots": {}, "users": {}}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    data = load_data()
    uid = str(user_id)
    if uid not in data["users"]:
        data["users"][uid] = {"bots": [], "balance": 0, "joined_at": int(time.time())}
        save_data(data)
    return data

# ==================== التحقق من الاشتراك ====================
async def check_subscription(user_id):
    try:
        participant = await bot(GetParticipantRequest(FACTORY_CHANNEL, user_id))
        return isinstance(participant.participant, (ChannelParticipantAdmin, ChannelParticipantCreator))
    except UserNotParticipantError:
        return False
    except Exception as e:
        log(f"Error checking subscription: {e}")
        return False

# ==================== القائمة الرئيسية ====================
async def main_menu(event, edit=False):
    user_id = str(event.sender_id)
    data = get_user_data(user_id)
    subscribed = await check_subscription(event.sender_id)

    if not subscribed:
        text = f"⚠️ لازم تشترك في قناة المصنع الأول\nhttps://t.me/{FACTORY_CHANNEL}"
        buttons = [[Button.url("اشترك الآن", f"https://t.me/{FACTORY_CHANNEL}")],
                   [Button.inline("✅ تحققت", b"check_sub")]]
    else:
        user_bots_count = len(data["users"][user_id]["bots"])
        text = f"🤖 **مصنع البوتات**\n\nمرحباً بك!\nبوتاتك: {user_bots_count}\nرصيدك: {data['users'][user_id]['balance']} جنيه"
        buttons = [
            [Button.inline("➕ إنشاء بوت جديد", b"create_bot")],
            [Button.inline("📋 بوتاتي", b"my_bots"), Button.inline("📊 الإحصائيات", b"stats")],
            [Button.inline("ℹ️ المساعدة", b"help"), Button.inline("💰 الرصيد", b"balance")]
        ]
        if event.sender_id == ADMIN_ID:
            buttons.append([Button.inline("⚙️ لوحة الأدمن", b"admin_panel")])

    if edit:
        await event.edit(text, buttons=buttons, parse_mode="md")
    else:
        await event.respond(text, buttons=buttons, parse_mode="md")

# ==================== الهاندلرز الأساسية ====================
@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    user_states.pop(event.sender_id, None)
    await main_menu(event)

@bot.on(events.CallbackQuery(pattern=b"check_sub"))
async def check_sub_handler(event):
    await main_menu(event, edit=True)

@bot.on(events.CallbackQuery(pattern=b"back"))
async def back_handler(event):
    user_states.pop(event.sender_id, None)
    await main_menu(event, edit=True)

@bot.on(events.CallbackQuery(pattern=b"help"))
async def help_handler(event):
    text = """ℹ️ **شرح المصنع**

1️⃣ اشترك في القناة
2️⃣ اضغط إنشاء بوت جديد
3️⃣ اختار نوع البوت
4️⃣ ابعت توكن البوت من @BotFather
5️⃣ ابعت اسم البوت
6️⃣ البوت هيشتغل تلقائي

**ملاحظة:** كل بوت بيشتغل في ملف منفصل على السيرفر"""
    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"back")]], parse_mode="md")

# ==================== بوتاتي ====================
@bot.on(events.CallbackQuery(pattern=b"my_bots"))
async def my_bots_handler(event):
    user_id = str(event.sender_id)
    data = load_data()
    user_bots = data["users"].get(user_id, {}).get("bots", [])

    if not user_bots:
        text = "📋 معندكش أي بوتات لسه"
        buttons = [[Button.inline("➕ أنشئ بوت الآن", b"create_bot")],
                   [Button.inline("🔙 رجوع", b"back")]]
    else:
        text = "📋 **بوتاتك:**\n\n"
        buttons = []
        for i, b in enumerate(user_bots):
            status = "🟢 شغال" if b.get("running") else "🔴 متوقف"
            text += f"{i+1}. **{b['name']}**\n @{b['username']} | {status}\n\n"
            buttons.append([Button.inline(f"⚙️ إدارة {b['name']}", f"manage_{b['id']}".encode())])
        buttons.append([Button.inline("🔙 رجوع", b"back")])

    await event.edit(text, buttons=buttons, parse_mode="md")

# ==================== إنشاء بوت جديد ====================
@bot.on(events.CallbackQuery(pattern=b"create_bot"))
async def create_bot_handler(event):
    text = """➕ **إنشاء بوت جديد**

اختار نوع البوت اللي عايزه:"""
    buttons = [
        [Button.inline("🤖 بوت عادي", b"type_normal")],
        [Button.inline("📢 بوت نشر", b"type_poster")],
        [Button.inline("🎵 بوت تحميل", b"type_downloader")],
        [Button.inline("🔙 رجوع", b"back")]
    ]
    await event.edit(text, buttons=buttons, parse_mode="md")

@bot.on(events.CallbackQuery(pattern=rb"type_(.*)"))
async def bot_type_handler(event):
    bot_type = event.pattern_match.group(1).decode()
    user_states[event.sender_id] = {"state": "waiting_token", "type": bot_type}
    await event.edit("📝 تمام! ابعتلي توكن البوت من @BotFather دلوقتي\n⚠️ التوكن سري، متبعتهوش لحد", parse_mode="md")

# ==================== استقبال الرسايل Conversation ====================
@bot.on(events.NewMessage)
async def message_handler(event):
    uid = event.sender_id
    if uid not in user_states:
        return

    state = user_states[uid]

    if state["state"] == "waiting_token":
        token = event.text.strip()
        if not re.match(r'^\d+:[A-Za-z0-9_-]{35}$', token):
            await event.reply("❌ التوكن غلط! ابعت توكن صحيح من @BotFather")
            return

        # التحقق من صحة التوكن
        try:
            test_client = TelegramClient(None, API_ID, API_HASH).start(bot_token=token)
            me = await test_client.get_me()
            await test_client.disconnect()

            state["token"] = token
            state["username"] = me.username or "unknown"
            state["state"] = "waiting_name"
            await event.reply(f"✅ التوكن صحيح!\nالبوت: @{me.username}\n\n📝 دلوقتي ابعت اسم البوت")
        except Exception as e:
            await event.reply(f"❌ التوكن غير صالح: {str(e)}")

    elif state["state"] == "waiting_name":
        name = event.text.strip()
        if len(name) < 3:
            await event.reply("❌ الاسم قصير، اكتب اسم 3 حروف على الأقل")
            return

        await create_bot_files(uid, state["token"], name, state["type"], state["username"])
        user_states.pop(uid, None)

# ==================== إنشاء ملفات البوت ====================
async def create_bot_files(user_id, token, name, bot_type, username):
    bot_id = f"bot_{random.randint(1000, 9999)}_{int(time.time())}"
    bot_folder = os.path.join(BOTS_FOLDER, bot_id)
    os.makedirs(bot_folder, exist_ok=True)

    # كود البوت حسب النوع
    if bot_type == "normal":
        bot_code = f'''import asyncio
from telethon import TelegramClient, events

API_ID = 1234567
API_HASH = "ضع_api_hash_هنا"
BOT_TOKEN = "{token}"

client = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply("مرحباً! البوت شغال بنجاح ✅")

@client.on(events.NewMessage(pattern="/help"))
async def help(event):
    await event.reply("أنا بوت عادي، ابعتلي أي حاجة")

print("البوت شغال...")
client.run_until_disconnected()
'''
    elif bot_type == "poster":
        bot_code = f'''import asyncio
from telethon import TelegramClient, events

API_ID = 1234567
API_HASH = "ضع_api_hash_هنا"
BOT_TOKEN = "{token}"

client = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@client.on(events.NewMessage(pattern="/post"))
async def post(event):
    if not event.is_reply:
        await event.reply("اعمل ريبلاي على الرسالة اللي عايز تنشرها")
        return
    reply = await event.get_reply_message()
    await client.forward_messages("me", reply)
    await event.reply("✅ تم الحفظ في Saved Messages")

print("بوت النشر شغال...")
client.run_until_disconnected()
'''
    else:
        bot_code = f'''import asyncio
from telethon import TelegramClient, events

API_ID = 1234567
API_HASH = "ضع_api_hash_هنا"
BOT_TOKEN = "{token}"

client = TelegramClient("bot", API_ID, API_HASH).start(bot_token=BOT_TOKEN)

@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    await event.reply("مرحباً! بوت التحميل شغال ✅")

print("بوت التحميل شغال...")
client.run_until_disconnected()
'''

    with open(os.path.join(bot_folder, "main.py"), "w", encoding="utf-8") as f:
        f.write(bot_code)

    with open(os.path.join(bot_folder, "requirements.txt"), "w") as f:
        f.write("telethon\n")

    # حفظ البيانات
    data = load_data()
    bot_info = {
        "id": bot_id,
        "name": name,
        "type": bot_type,
        "token": token,
        "username": username,
        "owner": str(user_id),
        "running": False,
        "pid": None,
        "created_at": int(time.time())
    }

    data["bots"][bot_id] = bot_info
    data["users"][str(user_id)]["bots"].append(bot_info)
    save_data(data)
    log(f"Created bot {bot_id} for user {user_id}")

    await bot.send_message(user_id, f"✅ تم إنشاء البوت **{name}** بنجاح!\n\nهيتم تشغيله دلوقتي...", parse_mode="md")
    await start_bot_process(bot_id)

# ==================== تشغيل وإيقاف البوتات ====================
async def start_bot_process(bot_id):
    data = load_data()
    if bot_id not in data["bots"]:
        return False

    bot_folder = os.path.join(BOTS_FOLDER, bot_id)
    main_file = os.path.join(bot_folder, "main.py")

    if not os.path.exists(main_file):
        return False

    try:
        process = subprocess.Popen([sys.executable, main_file], cwd=bot_folder,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        running_processes[bot_id] = process

        data["bots"][bot_id]["running"] = True
        data["bots"][bot_id]["pid"] = process.pid
        save_data(data)
        log(f"Started bot {bot_id} with PID {process.pid}")
        return True
    except Exception as e:
        log(f"Error starting bot {bot_id}: {e}")
        return False

async def stop_bot_process(bot_id):
    data = load_data()
    if bot_id not in data["bots"]:
        return False

    pid = data["bots"][bot_id].get("pid")
    if pid:
        try:
            os.kill(pid, 9)
        except:
            pass

    if bot_id in running_processes:
        running_processes[bot_id].terminate()
        del running_processes[bot_id]

    data["bots"][bot_id]["running"] = False
    data["bots"][bot_id]["pid"] = None
    save_data(data)
    log(f"Stopped bot {bot_id}")
    return True

# ==================== إدارة البوت ====================
@bot.on(events.CallbackQuery(pattern=rb"manage_(.*)"))
async def manage_bot_handler(event):
    bot_id = event.pattern_match.group(1).decode()
    data = load_data()

    if bot_id not in data["bots"]:
        await event.answer("البوت مش موجود", alert=True)
        return

    info = data["bots"][bot_id]
    status = "🟢 شغال" if info.get("running") else "🔴 متوقف"

    text = f"""⚙️ **إدارة البوت**

الاسم: {info['name']}
اليوزر: @{info['username']}
الحالة: {status}
النوع: {info['type']}
تاريخ الإنشاء: {time.strftime('%Y-%m-%d', time.localtime(info['created_at']))}"""

    buttons = []
    if info.get("running"):
        buttons.append([Button.inline("⏹️ إيقاف", f"stop_{bot_id}".encode())])
        buttons.append([Button.inline("🔄 إعادة تشغيل", f"restart_{bot_id}".encode())])
    else:
        buttons.append([Button.inline("▶️ تشغيل", f"start_{bot_id}".encode())])

    buttons.extend([
        [Button.inline("📄 عرض اللوج", f"log_{bot_id}".encode())],
        [Button.inline("🗑️ حذف البوت", f"delete_{bot_id}".encode())],
        [Button.inline("🔙 رجوع", b"my_bots")]
    ])

    await event.edit(text, buttons=buttons, parse_mode="md")

@bot.on(events.CallbackQuery(pattern=rb"start_(.*)"))
async def start_bot_handler(event):
    bot_id = event.pattern_match.group(1).decode()
    success = await start_bot_process(bot_id)
    if success:
        await event.answer("✅ تم تشغيل البوت", alert=True)
    else:
        await event.answer("❌ فشل التشغيل", alert=True)
    await manage_bot_handler(event)

@bot.on(events.CallbackQuery(pattern=rb"stop_(.*)"))
async def stop_bot_handler(event):
    bot_id = event.pattern_match.group(1).decode()
    await stop_bot_process(bot_id)
    await event.answer("⏹️ تم إيقاف البوت", alert=True)
    await manage_bot_handler(event)

@bot.on(events.CallbackQuery(pattern=rb"restart_(.*)"))
async def restart_bot_handler(event):
    bot_id = event.pattern_match.group(1).decode()
    await stop_bot_process(bot_id)
    await asyncio.sleep(2)
    await start_bot_process(bot_id)
    await event.answer("🔄 تم إعادة التشغيل", alert=True)
    await manage_bot_handler(event)

@bot.on(events.CallbackQuery(pattern=rb"delete_(.*)"))
async def delete_bot_handler(event):
    bot_id = event.pattern_match.group(1).decode()
    data = load_data()

    if bot_id in data["bots"]:
        await stop_bot_process(bot_id)
        bot_folder = os.path.join(BOTS_FOLDER, bot_id)
        shutil.rmtree(bot_folder, ignore_errors=True)
        del data["bots"][bot_id]

        for uid in data["users"]:
            data["users"][uid]["bots"] = [b for b in data["users"][uid]["bots"] if b["id"]!= bot_id]

        save_data(data)
        log(f"Deleted bot {bot_id}")
        await event.edit("🗑️ تم حذف البوت بنجاح", buttons=[[Button.inline("🔙 رجوع", b"my_bots")]])

@bot.on(events.CallbackQuery(pattern=rb"log_(.*)"))
async def log_bot_handler(event):
    bot_id = event.pattern_match.group(1).decode()
    log_file = os.path.join(BOTS_FOLDER, bot_id, "main.py")

    text = "📄 اللوج مش متاح حالياً"
    if os.path.exists(log_file):
        text = f"📄 **ملف البوت موجود**\nالمسار: {log_file}"

    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", f"manage_{bot_id}".encode())]], parse_mode="md")

# ==================== الإحصائيات والرصيد ====================
@bot.on(events.CallbackQuery(pattern=b"stats"))
async def stats_handler(event):
    data = load_data()
    total_bots = len(data["bots"])
    running_bots = len([b for b in data["bots"].values() if b.get("running")])
    total_users = len(data["users"])

    text = f"""📊 **إحصائيات المصنع**

إجمالي البوتات: {total_bots}
البوتات الشغالة: {running_bots}
البوتات المتوقفة: {total_bots - running_bots}
عدد المستخدمين: {total_users}"""

    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"back")]], parse_mode="md")

@bot.on(events.CallbackQuery(pattern=b"balance"))
async def balance_handler(event):
    user_id = str(event.sender_id)
    data = load_data()
    balance = data["users"].get(user_id, {}).get("balance", 0)

    text = f"💰 **رصيدك الحالي:** {balance} جنيه\nللشحن تواصل مع الأدمن"
    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"back")]], parse_mode="md")

# ==================== لوحة الأدمن ====================
@bot.on(events.CallbackQuery(pattern=b"admin_panel"))
async def admin_panel_handler(event):
    if event.sender_id!= ADMIN_ID:
        await event.answer("مش مسموح", alert=True)
        return

    data = load_data()
    text = f"""⚙️ **لوحة الأدمن**

البوتات الكلية: {len(data['bots'])}
المستخدمين: {len(data['users'])}
البوتات الشغالة: {len([b for b in data['bots'].values() if b.get('running')])}"""

    buttons = [
        [Button.inline("📢 إذاعة", b"broadcast")],
        [Button.inline("👥 المستخدمين", b"users_list")],
        [Button.inline("🔙 رجوع", b"back")]
    ]
    await event.edit(text, buttons=buttons, parse_mode="md")

@bot.on(events.CallbackQuery(pattern=b"broadcast"))
async def broadcast_handler(event):
    if event.sender_id!= ADMIN_ID:
        return
    user_states[event.sender_id] = {"state": "waiting_broadcast"}
    await event.edit("📢 ابعت الرسالة اللي عايز تبعتها لكل المستخدمين")

@bot.on(events.CallbackQuery(pattern=b"users_list"))
async def users_list_handler(event):
    if event.sender_id!= ADMIN_ID:
        return
    data = load_data()
    text = f"👥 **المستخدمين: {len(data['users'])}**\n\n"
    for uid, info in list(data["users"].items())[:20]:
        text += f"• {uid} - {len(info['bots'])} بوت\n"
    await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"admin_panel")]], parse_mode="md")

# ==================== إذاعة الرسالة ====================
@bot.on(events.NewMessage)
async def broadcast_message_handler(event):
    uid = event.sender_id
    if uid not in user_states:
        return

    state = user_states[uid]
    if state.get("state") == "waiting_broadcast" and uid == ADMIN_ID:
        msg = event.text
        data = load_data()
        success = 0
        failed = 0

        await event.reply("📢 بدء الإذاعة...")

        for user_id in data["users"]:
            try:
                await bot.send_message(int(user_id), f"📢 **إذاعة من الأدمن:**\n\n{msg}", parse_mode="md")
                success += 1
                await asyncio.sleep(0.5)
            except:
                failed += 1

        await event.reply(f"✅ انتهت الإذاعة\nنجح: {success}\nفشل: {failed}")
        user_states.pop(uid, None)

# ==================== تشغيل البوتات عند البداية ====================
async def auto_start_bots():
    data = load_data()
    log(f"Checking {len(data['bots'])} bots...")

    for bot_id, info in data["bots"].items():
        if info.get("running"):
            log(f"Starting {info['name']}...")
            await start_bot_process(bot_id)
            await asyncio.sleep(2)

    log("Auto start completed")

# ==================== تشغيل المصنع ====================
async def main():
    log("🚀 Starting factory bot...")
    await auto_start_bots()
    log("✅ Factory is ready")
    try:
        await bot.run_until_disconnected()
    finally:
        log("⏹️ Closing factory...")
        # اقفل كل البوتات الفرعية
        data = load_data()
        for bot_id, info in data["bots"].items():
            if info.get("running"):
                await stop_bot_process(bot_id)
        await bot.disconnect()
        log("✅ Factory closed cleanly")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log("Factory stopped by user")
    except Exception as e:
        log(f"Critical error: {e}")
