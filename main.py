import os, asyncio, json, random, datetime, secrets
from telethon import TelegramClient, events, Button
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError
from telethon.tl.types import MessageEntityCustomEmoji, Channel, Chat
from telethon.tl.functions.account import UpdateStatusRequest

API_ID = 31650696
API_HASH = '2829d6502df68cd12fab33cabf2851d2'
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEV_ID = 154919127
DEV_USERNAME = "Devazf"

DEVICE_MODEL = "iPhone 16 Pro Max"
SYSTEM_VERSION = "iOS 18.2"
APP_VERSION = "11.4.1"
LANG_CODE = "ar"
SYSTEM_LANG_CODE = "ar-AE"

DB_FILE = "azef_one.json"
USERS_FILE = "users.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {
        "accounts": {},
        "current_account": 1,
        "wait_seconds": 5,
        "speed_level": "متوسط",
        "stealth_mode": True,
        "auto_reply": True,
        "temp_post_1": None,
        "temp_post_2": None,
        "stats": {"posts": 0, "messages": 0, "groups_count": {}},
        "logs": []
    }

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {"codes": {}, "users": {}, "trials": []}

def save_db():
    with open(DB_FILE, 'w', encoding='utf-8') as f: json.dump(DB, f, indent=2, ensure_ascii=False)

def save_users():
    with open(USERS_FILE, 'w', encoding='utf-8') as f: json.dump(USERS, f, indent=2, ensure_ascii=False)

def add_log(action, details=""):
    DB["logs"].append({
        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "action": action,
        "details": details
    })
    if len(DB["logs"]) > 50: DB["logs"] = DB["logs"][-50:]
    save_db()

def get_account(acc_id):
    if str(acc_id) not in DB["accounts"]:
        DB["accounts"][str(acc_id)] = {
            "phone": None,
            "groups": [],
            "welcome": "نورت يا {name} 💎",
            "replies": ["موجود ✨", "اؤمرني 🌟", "معاك 💎"],
            "active": False
        }
        save_db()
    return DB["accounts"][str(acc_id)]

def get_current_account():
    return get_account(DB["current_account"])

def get_speed_seconds():
    speeds = {"سريع": 200, "متوسط": 400, "بطيء": 700}
    return speeds.get(DB["speed_level"], 400)

DB = load_db()
USERS = load_users()
userbots = {}
publishing_tasks = {}
stop_flags = {}
bot = None

def is_admin(user_id):
    return user_id == DEV_ID

def check_sub(user_id):
    if is_admin(user_id): return True, 999
    uid = str(user_id)
    if uid not in USERS["users"]: return False, 0
    user = USERS["users"][uid]
    if user.get("banned"): return False, 0
    expire = datetime.datetime.strptime(user["expire_date"], "%Y-%m-%d")
    now = datetime.datetime.now()
    if now > expire: return False, 0
    days_left = (expire - now).days
    return True, days_left

def generate_code(days=30):
    code = f"AZEF-{secrets.token_hex(4).upper()}"
    expire = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
    USERS["codes"][code] = {"user_id": None, "expire_date": expire, "used": False}
    save_users()
    return code, expire

def activate_trial(user_id):
    uid = str(user_id)
    if uid in USERS["trials"]:
        return False, "انت استخدمت التجربة المجانية قبل كده"
    expire = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
    USERS["users"][uid] = {"code": "TRIAL", "expire_date": expire, "banned": False}
    USERS["trials"].append(uid)
    save_users()
    return True, expire

async def register_userbot_handlers(client, acc_id):
    @client.on(events.ChatAction)
    async def welcome_handler(event):
        try:
            acc = get_account(acc_id)
            if (event.user_joined or event.user_added) and event.chat_id in acc["groups"]:
                await client(UpdateStatusRequest(offline=True))
                user = await event.get_user()
                text = acc["welcome"].format(name=user.first_name, username=user.username or "بدون")
                await event.reply(text, silent=True)
                DB["stats"]["messages"] += 1
                add_log(f"ترحيب حساب{acc_id}", f"في {event.chat_id}")
        except Exception as e:
            print(f"Welcome error: {e}")

    @client.on(events.NewMessage)
    async def mention_reply_handler(event):
        try:
            acc = get_account(acc_id)
            if event.chat_id in acc["groups"] and event.mentioned and DB["auto_reply"]:
                await client(UpdateStatusRequest(offline=True))
                reply = random.choice(acc["replies"])
                await event.reply(reply, silent=True)
                DB["stats"]["messages"] += 1
        except Exception as e:
            print(f"Reply error: {e}")

async def start_userbot(acc_id):
    acc = get_account(acc_id)
    if not acc["phone"]: return False
    try:
        client = TelegramClient(
            f'ios_{acc["phone"]}', API_ID, API_HASH,
            device_model=DEVICE_MODEL, system_version=SYSTEM_VERSION,
            app_version=APP_VERSION, lang_code=LANG_CODE, system_lang_code=SYSTEM_LANG_CODE
        )
        await client.connect()
        if await client.is_user_authorized():
            await client(UpdateStatusRequest(offline=True))
            await register_userbot_handlers(client, acc_id)
            userbots[acc_id] = client
            acc["active"] = True
            save_db()
            print(f"✅ حساب {acc_id} | {DEVICE_MODEL} | مخفي 👻")
            return True
    except Exception as e:
        print(f"❌ خطأ في حساب {acc_id}: {e}")
    return False

async def setup_bot():
    global bot
    bot = TelegramClient('bot_session', API_ID, API_HASH)
    await bot.start(bot_token=BOT_TOKEN)

    @bot.on(events.NewMessage(pattern='/admin'))
    async def admin_panel(event):
        if not is_admin(event.sender_id): return
        total_users = len(USERS["users"])
        active_codes = len([c for c in USERS["codes"].values() if not c["used"]])
        trials = len(USERS["trials"])
        active_accounts = len([a for a in DB["accounts"].values() if a.get("active")])
        btns = [
            [Button.inline("➕ توليد كود", b"gen_code"), Button.inline("📊 احصائيات", b"full_stats")],
            [Button.inline("👥 المستخدمين", b"list_users"), Button.inline("🔑 الاكواد", b"list_codes")],
            [Button.inline("🚫 حظر", b"ban_user"), Button.inline("✅ فك حظر", b"unban_user")],
            [Button.inline("💾 نسخ احتياطي", b"backup"), Button.inline("📥 استيراد", b"restore")]
        ]
        await event.reply(f"👑 **لوحة الادمن V30.1**\n\n📱 {DEVICE_MODEL}\n\nالمستخدمين: {total_users}\nاكواد متاحة: {active_codes}\nتجربة: {trials}\nحسابات نشطة: {active_accounts}/5\nالمنشورات: {DB['stats']['posts']}", buttons=btns)

    @bot.on(events.CallbackQuery(pattern=b"gen_code"))
    async def gen_code(event):
        if not is_admin(event.sender_id): return
        code, expire = generate_code(30)
        await event.answer(f"✅ كود جديد: {code}\nينتهي: {expire}", alert=True)

    @bot.on(events.CallbackQuery(data=b"full_stats"))
    async def full_stats(event):
        if not is_admin(event.sender_id): return
        total = len(USERS["users"])
        active = len([u for u in USERS["users"].values() if not u.get("banned") and datetime.datetime.strptime(u["expire_date"], "%Y-%m-%d") > datetime.datetime.now()])
        posts = DB['stats']['posts']
        msgs = DB['stats']['messages']
        accounts_info = "\n".join([f"• حساب {i}: {'✅ نشط' if a.get('active') else '❌ معطل'} | {len(a.get('groups', []))} جروب" for i, a in DB["accounts"].items()])
        txt = f"📊 **احصائيات شاملة**\n\n👥 المستخدمين: {total}\n✅ مفعلين: {active}\n\n📤 المنشورات: {posts}\n💬 الردود: {msgs}\n\n**الحسابات:**\n{accounts_info or 'مفيش'}"
        await event.edit(txt, buttons=[[Button.inline("🔙", b"admin_back")]])

    @bot.on(events.CallbackQuery(data=b"backup"))
    async def backup(event):
        if not is_admin(event.sender_id): return
        data = json.dumps(DB, indent=2, ensure_ascii=False)
        await event.respond(f"💾 **نسخة احتياطية**\n\n```json\n{data[:3500]}\n```", buttons=[[Button.inline("🔙", b"admin_back")]])

    @bot.on(events.CallbackQuery(data=b"restore"))
    async def restore(event):
        if not is_admin(event.sender_id): return
        await event.edit("📥 ابعت ملف JSON:", buttons=[[Button.inline("🔙", b"admin_back")]])
        bot.wait_restore = True

    @bot.on(events.CallbackQuery(data=b"list_users"))
    async def list_users(event):
        if not is_admin(event.sender_id): return
        text = "**👥 المستخدمين:**\n\n"
        for uid, data in USERS["users"].items():
            status = "🚫 محظور" if data.get("banned") else "✅ مفعل"
            text += f"• `{uid}`\nانتهاء: {data['expire_date']}\n{status}\n\n"
        await event.edit(text[:4000] or "مفيش مستخدمين", buttons=[[Button.inline("🔙", b"admin_back")]])

    @bot.on(events.CallbackQuery(data=b"list_codes"))
    async def list_codes(event):
        if not is_admin(event.sender_id): return
        text = "**🔑 الاكواد:**\n\n"
        for code, data in USERS["codes"].items():
            status = "✅ مستخدم" if data["used"] else "🟢 متاح"
            text += f"• `{code}`\nينتهي: {data['expire_date']}\n{status}\n\n"
        await event.edit(text[:4000] or "مفيش اكواد", buttons=[[Button.inline("🔙", b"admin_back")]])

    @bot.on(events.CallbackQuery(data=b"ban_user"))
    async def ban_user(event):
        if not is_admin(event.sender_id): return
        await event.edit("🚫 ابعت ايدي المستخدم:", buttons=[[Button.inline("🔙", b"admin_back")]])
        bot.wait_ban = True

    @bot.on(events.CallbackQuery(data=b"unban_user"))
    async def unban_user(event):
        if not is_admin(event.sender_id): return
        await event.edit("✅ ابعت ايدي المستخدم:", buttons=[[Button.inline("🔙", b"admin_back")]])
        bot.wait_unban = True

    @bot.on(events.CallbackQuery(data=b"admin_back"))
    async def admin_back(event):
        if not is_admin(event.sender_id): return
        await admin_panel(event)

    @bot.on(events.NewMessage(pattern='/start'))
    async def start_panel(event):
        has_sub, days_left = check_sub(event.sender_id)
        
        if not has_sub:
            btns = [
                [Button.inline("🎁 تجربة مجانية 24س", b"free_trial")],
                [Button.inline("🔑 تفعيل كود", b"activate_code")],
                [Button.url("💬 مراسلة المبرمج", f"https://t.me/{DEV_USERNAME}")]
            ]
            await event.reply("⚠️ **Azef Pro V30.1**\n\n🎁 جرب البوت مجاناً لمدة 24 ساعة\n🔑 او فعل كود الاشتراك\n\nللشراء والدعم:", buttons=btns)
            return

        acc = get_current_account()
        phone_status = f"✅ {acc['phone']}" if acc['phone'] else "❌ مش متضاف"
        wait_status = f"{DB['wait_seconds']}ث"
        speed_status = DB["speed_level"]
        stealth_status = "👻 مفعل" if DB["stealth_mode"] else "👁️ معطل"
        auto_status = "✅ مفعل" if DB["auto_reply"] else "❌ معطل"
        active_count = len(acc["groups"])
        accounts_active = len([a for a in DB["accounts"].values() if a.get("active")])

        if not is_admin(event.sender_id):
            sub_info = f"\n⏳ فاضل: {days_left} يوم"
        else:
            sub_info = "\n👑 حساب ادمن"

        btns = [
            [Button.inline(f"👤 حساب {DB['current_account']}/5", b"switch_account"), Button.inline(f"📊 {DB['stats']['posts']} منشور", b"show_stats")],
            [Button.inline(f"📱 {phone_status}", b"account_menu"), Button.inline("📝 السجلات", b"show_logs")],
            [Button.inline("👥 الجروبات", b"groups_menu"), Button.inline("💬 الردود", b"replies_menu")],
            [Button.inline("▶️ نشر رسالة 1", b"send_post_1"), Button.inline("▶️ نشر رسالة 2", b"send_post_2")],
            [Button.inline("👁️ معاينة الرسائل", b"preview_menu"), Button.inline("👋 الترحيب", b"set_welcome")],
            [Button.inline(f"⏳ انتظار: {wait_status}", b"set_wait"), Button.inline(f"🚀 سرعة: {speed_status}", b"set_speed")],
            [Button.inline(f"👻 تخفي: {stealth_status}", b"toggle_stealth"), Button.inline(f"🔔 رد تلقائي: {auto_status}", b"toggle_auto")],
            [Button.inline("⚙️ الاعدادات", b"settings"), Button.url("💬 الدعم", f"https://t.me/{DEV_USERNAME}")]
        ]
        await event.reply(f"🤖 **Azef Pro V30.1** {sub_info}\n\n📱 {DEVICE_MODEL}\n\nحسابات نشطة: {accounts_active}/5\nالجروبات: {active_count}\nالانتظار: {wait_status} | السرعة: {speed_status}", buttons=btns)

    @bot.on(events.CallbackQuery(data=b"switch_account"))
    async def switch_account(event):
        if not check_sub(event.sender_id)[0]: return
        btns = []
        for i in range(1, 6):
            acc = get_account(i)
            status = "✅" if acc.get("active") else "❌"
            current = "👈" if DB["current_account"] == i else ""
            btns.append([Button.inline(f"{status} حساب {i} {current}", f"select_acc_{i}".encode())])
        btns.append([Button.inline("🔙", b"back")])
        await event.edit("👥 **اختر الحساب:**", buttons=btns)

    @bot.on(events.CallbackQuery(pattern=b"select_acc_"))
    async def select_acc(event):
        if not check_sub(event.sender_id)[0]: return
        acc_id = int(event.data.decode().split("_")[-1])
        DB["current_account"] = acc_id
        save_db()
        await event.answer(f"✅ تم التحويل لحساب {acc_id}", alert=True)
        await start_panel(event)

    @bot.on(events.CallbackQuery(data=b"account_menu"))
    async def account_menu(event):
        if not check_sub(event.sender_id)[0]: return
        acc = get_current_account()
        phone = acc["phone"] or "مش متضاف"
        btns = [
            [Button.inline("🔄 تغيير الرقم", b"change_phone"), Button.inline("🗑️ حذف الرقم", b"del_phone")],
            [Button.inline("▶️ تشغيل الحساب", b"start_acc"), Button.inline("⏸️ ايقاف", b"stop_acc")],
            [Button.inline("🔙", b"back")]
        ]
        await event.edit(f"📱 **حساب {DB['current_account']}**\n\nالرقم: `{phone}`\nالحالة: {'✅ نشط' if acc.get('active') else '❌ معطل'}\nالجروبات: {len(acc['groups'])}", buttons=btns)

    @bot.on(events.CallbackQuery(data=b"start_acc"))
    async def start_acc(event):
        if not check_sub(event.sender_id)[0]: return
        success = await start_userbot(DB["current_account"])
        if success:
            await event.answer("✅ تم تشغيل الحساب", alert=True)
        else:
            await event.answer("❌ فشل التشغيل", alert=True)
        await account_menu(event)

    @bot.on(events.CallbackQuery(data=b"stop_acc"))
    async def stop_acc(event):
        if not check_sub(event.sender_id)[0]: return
        acc_id = DB["current_account"]
        if acc_id in userbots:
            await userbots[acc_id].disconnect()
            del userbots[acc_id]
        get_current_account()["active"] = False
        save_db()
        await event.answer("⏸️ تم ايقاف الحساب", alert=True)
        await account_menu(event)

    @bot.on(events.CallbackQuery(data=b"show_stats"))
    async def show_stats(event):
        if not check_sub(event.sender_id)[0]: return
        posts = DB['stats']['posts']
        msgs = DB['stats']['messages']
        txt = f"📊 **احصائياتك**\n\n📤 المنشورات: {posts}\n💬 الردود التلقائية: {msgs}\n👥 الجروبات: {len(get_current_account()['groups'])}"
        await event.answer(txt, alert=True)

    @bot.on(events.CallbackQuery(data=b"show_logs"))
    async def show_logs(event):
        if not check_sub(event.sender_id)[0]: return
        if not DB["logs"]:
            return await event.answer("مفيش سجلات", alert=True)
        text = "**📝 آخر 10 عمليات:**\n\n"
        for log in DB["logs"][-10:]:
            text += f"• {log['time']}\n{log['action']}: {log['details']}\n\n"
        await event.edit(text, buttons=[[Button.inline("🔙", b"back")]])

    @bot.on(events.CallbackQuery(data=b"groups_menu"))
    async def groups_menu(event):
        if not check_sub(event.sender_id)[0]: return
        acc = get_current_account()
        btns = [
            [Button.inline("👥 جلب المجموعات", b"get_groups"), Button.inline("📝 مجموعاتي", b"my_groups")],
            [Button.inline("➕ اضافة جروب", b"add_group"), Button.inline("➖ حذف جروب", b"del_group")],
            [Button.inline("🗑️ حذف الكل", b"clear_groups"), Button.inline("🔙", b"back")]
        ]
        await event.edit(f"👥 **جروبات حساب {DB['current_account']}**\n\nالعدد: {len(acc['groups'])}", buttons=btns)

    @bot.on(events.CallbackQuery(data=b"replies_menu"))
    async def replies_menu(event):
        if not check_sub(event.sender_id)[0]: return
        acc = get_current_account()
        replies_text = "\n".join([f"{i+1}. {r}" for i, r in enumerate(acc["replies"])])
        btns = [[Button.inline("➕ اضافة رد", b"add_reply")], [Button.inline("🗑️ حذف آخر رد", b"del_reply"), Button.inline("🔙", b"back")]]
        await event.edit(f"💬 **الردود التلقائية:**\n\n{replies_text}", buttons=btns)

    @bot.on(events.CallbackQuery(data=b"add_reply"))
    async def add_reply(event):
        if not check_sub(event.sender_id)[0]: return
        await event.edit("ابعت الرد الجديد:", buttons=[[Button.inline("🔙", b"replies_menu")]])
        bot.wait_reply = True

    @bot.on(events.CallbackQuery(data=b"del_reply"))
    async def del_reply(event):
        if not check_sub(event.sender_id)[0]: return
        acc = get_current_account()
        if acc["replies"]:
            acc["replies"].pop()
            save_db()
        await replies_menu(event)

    @bot.on(events.CallbackQuery(data=b"send_post_1"))
    async def send_post_1(event):
        if not check_sub(event.sender_id)[0]: return
        await event.edit("📝 ابعت الرسالة رقم 1:\n\nنص + ايموجي بريميوم + صور + فيديو", buttons=[[Button.inline("🔙", b"back")]])
        bot.wait_post_1 = True

    @bot.on(events.CallbackQuery(data=b"send_post_2"))
    async def send_post_2(event):
        if not check_sub(event.sender_id)[0]: return
        await event.edit("📝 ابعت الرسالة رقم 2:\n\nنص + ايموجي بريميوم + صور + فيديو", buttons=[[Button.inline("🔙", b"back")]])
        bot.wait_post_2 = True

    @bot.on(events.CallbackQuery(data=b"preview_menu"))
    async def preview_menu(event):
        if not check_sub(event.sender_id)[0]: return
        btns = [
            [Button.inline("👁️ معاينة رسالة 1", b"preview_1")],
            [Button.inline("👁️ معاينة رسالة 2", b"preview_2")],
            [Button.inline("🔙", b"back")]
        ]
        await event.edit("👁️ **المعاينة**", buttons=btns)

    @bot.on(events.CallbackQuery(data=b"preview_1"))
    async def preview_1(event):
        if not check_sub(event.sender_id)[0]: return
        if not DB.get("temp_post_1"):
            return await event.answer("❌ مفيش رسالة 1 محفوظة", alert=True)
        post = DB["temp_post_1"]
        btns = [[Button.inline("▶️ نشر الآن", b"confirm_post_1")], [Button.inline("🔙", b"preview_menu")]]
        await event.edit("👁️ **معاينة رسالة 1:**\n\n" + post["text"], buttons=btns)

    @bot.on(events.CallbackQuery(data=b"preview_2"))
    async def preview_2(event):
        if not check_sub(event.sender_id)[0]: return
        if not DB.get("temp_post_2"):
            return await event.answer("❌ مفيش رسالة 2 محفوظة", alert=True)
        post = DB["temp_post_2"]
        btns = [[Button.inline("▶️ نشر الآن", b"confirm_post_2")], [Button.inline("🔙", b"preview_menu")]]
        await event.edit("👁️ **معاينة رسالة 2:**\n\n" + post["text"], buttons=btns)

    @bot.on(events.CallbackQuery(data=b"confirm_post_1"))
    async def confirm_post_1(event):
        if not check_sub(event.sender_id)[0]: return
        await do_publish(event, DB["temp_post_1"], 1)

    @bot.on(events.CallbackQuery(data=b"confirm_post_2"))
    async def confirm_post_2(event):
        if not check_sub(event.sender_id)[0]: return
        await do_publish(event, DB["temp_post_2"], 2)

    @bot.on(events.CallbackQuery(pattern=b"stop_pub_"))
    async def stop_publish(event):
        if not check_sub(event.sender_id)[0]: return
        acc_id = int(event.data.decode().split("_")[-1])
        stop_flags[acc_id] = True
        await event.answer("⏹️ جاري الايقاف...", alert=True)

    async def do_publish(event, post, post_num):
        if not post:
            return await event.answer("❌ مفيش منشور", alert=True)

        acc = get_current_account()
        acc_id = DB["current_account"]
        if acc_id not in userbots:
            return await event.answer("❌ شغل الحساب الاول", alert=True)

        if acc_id in publishing_tasks and not publishing_tasks[acc_id].done():
            return await event.answer("⚠️ في نشر شغال حالياً", alert=True)

        client = userbots[acc_id]
        wait_sec = get_speed_seconds() if DB["speed_level"] else DB["wait_seconds"]
        stop_flags[acc_id] = False

        msg = await event.edit(
            f"▶️ **جاري النشر...**\n\nالجروبات: {len(acc['groups'])}\nالانتظار: {wait_sec}ث\n\n⏹️ اضغط ايقاف عشان توقف",
            buttons=[[Button.inline("⏹️ ايقاف النشر", f"stop_pub_{acc_id}".encode())]]
        )

        async def publish_task():
            sent, failed = 0, 0
            total = len(acc["groups"])

            for idx, gid in enumerate(acc["groups"], 1):
                if stop_flags.get(acc_id):
                    await msg.edit(f"⏹️ **تم الايقاف**\n\nمرسل: {sent}/{total}\nفشل: {failed}", buttons=[[Button.inline("🔙", b"back")]])
                    return

                try:
                    await client(UpdateStatusRequest(offline=True))
                    if post["media"]:
                        from telethon.tl.types import MessageMedia
                        media = MessageMedia.from_dict(post["media"])
                        await client.send_file(int(gid), media, caption=post["text"], silent=True)
                    else:
                        await client.send_message(int(gid), post["text"], silent=True)

                    sent += 1
                    DB["stats"]["posts"] += 1
                    DB["stats"]["groups_count"][str(gid)] = DB["stats"]["groups_count"].get(str(gid), 0) + 1
                    save_db()

                    if idx % 3 == 0:
                        await msg.edit(
                            f"▶️ **جاري النشر...**\n\nمرسل: {sent}/{total}\nفشل: {failed}\nفاضل: {total - idx}\nالانتظار: {wait_sec}ث",
                            buttons=[[Button.inline("⏹️ ايقاف النشر", f"stop_pub_{acc_id}".encode())]]
                        )

                    await asyncio.sleep(wait_sec)

                except FloodWaitError as e:
                    await msg.edit(f"⚠️ حظر مؤقت {e.seconds} ثانية\n\nمرسل: {sent}/{total}\nفشل: {failed}", buttons=[[Button.inline("🔙", b"back")]])
                    return
                except Exception as e:
                    failed += 1
                    print(f"Failed {gid}: {e}")

            save_db()
            add_log(f"نشر رسالة {post_num}", f"حساب{acc_id} | مرسل: {sent} | فشل: {failed}")
            await msg.edit(f"✅ **تم الانتهاء**\n\nمرسل: {sent}/{total}\nفشل: {failed}\nالانتظار: {wait_sec}ث", buttons=[[Button.inline("🔙", b"back")]])

        publishing_tasks[acc_id] = asyncio.create_task(publish_task())

    @bot.on(events.CallbackQuery(data=b"set_wait"))
    async def set_wait(event):
        if not check_sub(event.sender_id)[0]: return
        await event.edit(f"⏳ **وقت الانتظار الحالي:** `{DB['wait_seconds']}ث`\n\nابعت الرقم الجديد بالثواني:\nمثال: `30`", buttons=[[Button.inline("🔙", b"back")]])
        bot.wait_seconds = True

    @bot.on(events.CallbackQuery(data=b"set_speed"))
    async def set_speed(event):
        if not check_sub(event.sender_id)[0]: return
        btns = [
            [Button.inline("⚡ سريع 200ث", b"speed_fast")],
            [Button.inline("🔵 متوسط 400ث", b"speed_medium")],
            [Button.inline("🟡 بطيء 700ث", b"speed_slow")],
            [Button.inline("🔙", b"back")]
        ]
        await event.edit(f"🚀 **مستوى السرعة الحالي:** `{DB['speed_level']}`\n\n⚡ سريع = 200 ثانية\n🔵 متوسط = 400 ثانية\n🟡 بطيء = 700 ثانية", buttons=btns)

    @bot.on(events.CallbackQuery(pattern=b"speed_"))
    async def set_speed_level(event):
        if not check_sub(event.sender_id)[0]: return
        data = event.data.decode()
        if data == "speed_fast": DB["speed_level"] = "سريع"
        elif data == "speed_medium": DB["speed_level"] = "متوسط"
        elif data == "speed_slow": DB["speed_level"] = "بطيء"
        save_db()
        await event.answer(f"✅ تم التعيين: {DB['speed_level']}", alert=True)
        await start_panel(event)

    @bot.on(events.CallbackQuery(data=b"toggle_stealth"))
    async def toggle_stealth(event):
        if not check_sub(event.sender_id)[0]: return
        DB["stealth_mode"] = not DB["stealth_mode"]
        save_db()
        await start_panel(event)

    @bot.on(events.CallbackQuery(data=b"toggle_auto"))
    async def toggle_auto(event):
        if not check_sub(event.sender_id)[0]: return
        DB["auto_reply"] = not DB["auto_reply"]
        save_db()
        await start_panel(event)

    @bot.on(events.CallbackQuery(data=b"set_welcome"))
    async def set_welcome(event):
        if not check_sub(event.sender_id)[0]: return
        acc = get_current_account()
        await event.edit(f"👋 **الترحيب الحالي:**\n\n{acc['welcome']}\n\nابعت الترحيب الجديد:\n{{name}} و {{username}} + ايموجي بريميوم", buttons=[[Button.inline("🔙", b"back")]])
        bot.wait_welcome = True

    @bot.on(events.CallbackQuery(data=b"settings"))
    async def settings(event):
        if not check_sub(event.sender_id)[0]: return
        btns = [
            [Button.inline("💾 تصدير الاعدادات", b"export_settings")],
            [Button.inline("🔄 اعادة تعيين", b"reset_settings")],
            [Button.inline("🔙", b"back")]
        ]
        await event.edit("⚙️ **الاعدادات المتقدمة**", buttons=btns)

    @bot.on(events.CallbackQuery(data=b"export_settings"))
    async def export_settings(event):
        if not check_sub(event.sender_id)[0]: return
        data = json.dumps(DB, indent=2, ensure_ascii=False)
        await event.respond(f"💾 **نسخة من اعداداتك:**\n\n```json\n{data[:3500]}\n```")

    @bot.on(events.CallbackQuery(data=b"reset_settings"))
    async def reset_settings(event):
        if not check_sub(event.sender_id)[0]: return
        DB["wait_seconds"] = 5
        DB["speed_level"] = "متوسط"
        DB["stealth_mode"] = True
        DB["auto_reply"] = True
        save_db()
        await event.answer("🔄 تم اعادة التعيين", alert=True)
        await start_panel(event)

    @bot.on(events.CallbackQuery(data=b"free_trial"))
    async def free_trial(event):
        success, msg = activate_trial(event.sender_id)
        if success:
            await event.answer(f"🎁 تم تفعيل التجربة المجانية\n\nينتهي: {msg}", alert=True)
            await start_panel(event)
        else:
            await event.answer(f"❌ {msg}", alert=True)

    @bot.on(events.CallbackQuery(data=b"activate_code"))
    async def activate_code(event):
        await event.edit("🔑 ابعت كود التفعيل:", buttons=[[Button.inline("🔙", b"back")]])
        bot.wait_code_activation = event.sender_id

    @bot.on(events.CallbackQuery(data=b"get_groups"))
    async def get_groups(event):
        if not check_sub(event.sender_id)[0]: return
        acc_id = DB["current_account"]
        if acc_id not in userbots:
            return await event.answer("❌ شغل الحساب الاول", alert=True)
        client = userbots[acc_id]
        await event.answer("⏳ جاري الجلب...", alert=False)
        try:
            dialogs = await client.get_dialogs(limit=200)
            bot.temp_groups = []
            text = "**👥 جروباتك:**\n\n"
            for d in dialogs:
                if isinstance(d.entity, (Channel, Chat)) and d.is_group:
                    bot.temp_groups.append({"id": d.id, "name": d.name})
                    text += f"• {d.name}\n`{d.id}`\n\n"
            if not bot.temp_groups:
                return await event.edit("❌ مفيش جروبات", buttons=[[Button.inline("🔙", b"groups_menu")]])
            btns = [[Button.inline(f"➕ اضافة الكل ({len(bot.temp_groups)})", b"add_all")], [Button.inline("🔙", b"groups_menu")]]
            await event.edit(text[:4000], buttons=btns)
        except Exception as e:
            await event.edit(f"❌ خطأ: {e}", buttons=[[Button.inline("🔙", b"groups_menu")]])

    @bot.on(events.CallbackQuery(data=b"add_all"))
    async def add_all(event):
        if not check_sub(event.sender_id)[0]: return
        if hasattr(bot, 'temp_groups'):
            acc = get_current_account()
            added = 0
            for g in bot.temp_groups:
                if g["id"] not in acc["groups"]:
                    acc["groups"].append(g["id"])
                    added += 1
            save_db()
            add_log(f"اضافة جروبات حساب{DB['current_account']}", f"{added} جروب")
            await event.answer(f"✅ تم اضافة {added} جروب", alert=True)
            await start_panel(event)

    @bot.on(events.CallbackQuery(data=b"my_groups"))
    async def my_groups(event):
        if not check_sub(event.sender_id)[0]: return
        acc = get_current_account()
        if not acc["groups"]: return await event.edit("❌ مفيش جروبات", buttons=[[Button.inline("🔙", b"groups_menu")]])
        text = f"**📝 جروبات حساب {DB['current_account']}:**\n\n"
        for gid in acc["groups"]:
            try:
                acc_id = DB["current_account"]
                if acc_id in userbots:
                    chat = await userbots[acc_id].get_entity(int(gid))
                    count = DB['stats']['groups_count'].get(str(gid), 0)
                    text += f"• {chat.title}\n`{gid}` | {count} منشور\n\n"
                else:
                    text += f"• `{gid}`\n\n"
            except: text += f"• محذوف `{gid}`\n\n"
        await event.edit(text, buttons=[[Button.inline("🔙", b"groups_menu")]])

    @bot.on(events.CallbackQuery(data=b"clear_groups"))
    async def clear_groups(event):
        if not check_sub(event.sender_id)[0]: return
        acc = get_current_account()
        acc["groups"] = []
        save_db()
        add_log(f"حذف جروبات حساب{DB['current_account']}", "الكل")
        await event.answer("🗑️ تم", alert=True)
        await start_panel(event)

    @bot.on(events.CallbackQuery(data=b"add_group"))
    async def add_group(event):
        if not check_sub(event.sender_id)[0]: return
        await event.edit("➕ ابعت ايدي الجروب او لينك:\n\n`-1001234567890`\n`https://t.me/groupname`", buttons=[[Button.inline("🔙", b"groups_menu")]])
        bot.wait_add_group = True

    @bot.on(events.CallbackQuery(data=b"del_group"))
    async def del_group(event):
        if not check_sub(event.sender_id)[0]: return
        await event.edit("➖ ابعت ايدي الجروب:", buttons=[[Button.inline("🔙", b"groups_menu")]])
        bot.wait_del_group = True

    @bot.on(events.CallbackQuery(data=b"change_phone"))
    async def change_phone(event):
        if not check_sub(event.sender_id)[0]: return
        acc = get_current_account()
        acc["phone"] = None
        acc["active"] = False
        save_db()
        acc_id = DB["current_account"]
        if acc_id in userbots: 
            await userbots[acc_id].disconnect()
            del userbots[acc_id]
        await event.edit("📱 ابعت الرقم الجديد:\n`+201012345678`")
        bot.wait_phone = True

    @bot.on(events.CallbackQuery(data=b"del_phone"))
    async def del_phone(event):
        if not check_sub(event.sender_id)[0]: return
        acc = get_current_account()
        acc["phone"] = None
        acc["active"] = False
        save_db()
        acc_id = DB["current_account"]
        if acc_id in userbots: 
            await userbots[acc_id].disconnect()
            del userbots[acc_id]
        await event.answer("🗑️ تم حذف الرقم", alert=True)
        await account_menu(event)

    @bot.on(events.CallbackQuery(data=b"back"))
    async def back(event):
        await start_panel(event)

    @bot.on(events.NewMessage)
    async def handle_input(event):
        global userbots
        uid = str(event.sender_id)

        if hasattr(bot, 'wait_code_activation') and bot.wait_code_activation == event.sender_id:
            bot.wait_code_activation = None
            code = event.text.strip().upper()
            if code not in USERS["codes"]:
                return await event.reply("❌ الكود غلط")
            code_data = USERS["codes"][code]
            if code_data["used"]:
                return await event.reply("❌ الكود مستخدم قبل كده")
            expire = datetime.datetime.strptime(code_data["expire_date"], "%Y-%m-%d")
            if datetime.datetime.now() > expire:
                return await event.reply("❌ الكود منتهي")
            USERS["codes"][code]["used"] = True
            USERS["codes"][code]["user_id"] = event.sender_id
            USERS["users"][uid] = {"code": code, "expire_date": code_data["expire_date"], "banned": False}
            save_users()
            add_log("تفعيل كود", f"يوزر: {uid}")
            await event.reply(f"✅ تم التفعيل بنجاح\n\nينتهي: {code_data['expire_date']}\n\nابعت /start")
            return

        if hasattr(bot, 'wait_ban') and bot.wait_ban and is_admin(event.sender_id):
            bot.wait_ban = False
            try:
                target = event.text.strip()
                if target in USERS["users"]:
                    USERS["users"][target]["banned"] = True
                    save_users()
                    await event.reply(f"🚫 تم حظر `{target}`")
                else:
                    await event.reply("❌ المستخدم مش موجود")
            except:
                await event.reply("❌ ايدي غلط")
            return

        if hasattr(bot, 'wait_unban') and bot.wait_unban and is_admin(event.sender_id):
            bot.wait_unban = False
            try:
                target = event.text.strip()
                if target in USERS["users"]:
                    USERS["users"][target]["banned"] = False
                    save_users()
                    await event.reply(f"✅ تم فك حظر `{target}`")
                else:
                    await event.reply("❌ المستخدم مش موجود")
            except:
                await event.reply("❌ ايدي غلط")
            return

        if hasattr(bot, 'wait_restore') and bot.wait_restore and is_admin(event.sender_id):
            bot.wait_restore = False
            try:
                new_db = json.loads(event.text)
                DB.update(new_db)
                save_db()
                await event.reply("✅ تم استيراد الاعدادات بنجاح")
            except:
                await event.reply("❌ ملف JSON غلط")
            return

        if not check_sub(event.sender_id)[0] and not is_admin(event.sender_id):
            return

        if hasattr(bot, 'wait_phone') and bot.wait_phone and event.sender_id == DEV_ID:
            bot.wait_phone = False
            phone = event.text.strip()
            if not phone.startswith('+'):
                return await event.reply("❌ لازم يبدأ بـ + مثال: +2010")
            msg = await event.reply("⏳ جاري ارسال الكود...")
            acc = get_current_account()
            acc["phone"] = phone
            save_db()
            acc_id = DB["current_account"]
            client = TelegramClient(
                f'ios_{phone}', API_ID, API_HASH,
                device_model=DEVICE_MODEL, system_version=SYSTEM_VERSION,
                app_version=APP_VERSION, lang_code=LANG_CODE, system_lang_code=SYSTEM_LANG_CODE
            )
            await client.connect()
            try:
                await client.send_code_request(phone)
                userbots[acc_id] = client
                await msg.edit("✅ اتبعت الكود على تيليجرام\nابعت الكود هنا:")
                bot.wait_code = True
                bot.wait_code_acc = acc_id
            except Exception as e:
                await msg.edit(f"❌ خطأ: {e}")
                acc["phone"] = None
                save_db()

        elif hasattr(bot, 'wait_code') and bot.wait_code and event.sender_id == DEV_ID:
            bot.wait_code = False
            code = event.text.strip()
            acc_id = bot.wait_code_acc
            msg = await event.reply("⏳ جاري تسجيل الدخول...")
            try:
                await userbots[acc_id].sign_in(get_current_account()["phone"], code)
                await start_userbot(acc_id)
                await msg.edit(f"✅ تم التسجيل بنجاح\n\n📱 {DEVICE_MODEL}\n🔢 iOS {SYSTEM_VERSION}")
                await start_panel(event)
            except SessionPasswordNeededError:
                await msg.edit("🔐 الحساب عليه تحقق بخطوتين\nابعت كلمة السر:")
                bot.wait_2fa = True
                bot.wait_2fa_acc = acc_id
            except PhoneCodeInvalidError:
                await msg.edit("❌ الكود غلط\nابعت /start وجرب تاني")
            except Exception as e:
                await msg.edit(f"❌ خطأ: {e}")

        elif hasattr(bot, 'wait_2fa') and bot.wait_2fa and event.sender_id == DEV_ID:
            bot.wait_2fa = False
            password = event.text.strip()
            acc_id = bot.wait_2fa_acc
            msg = await event.reply("⏳ جاري التحقق...")
            try:
                await userbots[acc_id].sign_in(password=password)
                await start_userbot(acc_id)
                await msg.edit(f"✅ تم التسجيل بنجاح\n\n📱 {DEVICE_MODEL}")
                await start_panel(event)
            except Exception as e:
                await msg.edit(f"✅ تم بنجاح")

        elif hasattr(bot, 'wait_seconds') and bot.wait_seconds and event.sender_id == DEV_ID:
            bot.wait_seconds = False
            try:
                seconds = int(event.text.strip())
                if seconds < 1: raise ValueError
                DB["wait_seconds"] = seconds
                save_db()
                await event.reply(f"✅ تم التعيين: {seconds} ثانية", buttons=[[Button.inline("🔙", b"back")]])
            except:
                await event.reply("❌ رقم غلط\nمثال: `30`", buttons=[[Button.inline("🔙", b"back")]])

        elif hasattr(bot, 'wait_welcome') and bot.wait_welcome and event.sender_id == DEV_ID:
            bot.wait_welcome = False
            acc = get_current_account()
            acc["welcome"] = event.text
            save_db()
            await event.reply("✅ تم تعيين الترحيب الجديد", buttons=[[Button.inline("🔙", b"back")]])

        elif hasattr(bot, 'wait_reply') and bot.wait_reply and event.sender_id == DEV_ID:
            bot.wait_reply = False
            acc = get_current_account()
            acc["replies"].append(event.text)
            save_db()
            await event.reply(f"✅ تم اضافة الرد رقم {len(acc['replies'])}", buttons=[[Button.inline("🔙", b"replies_menu")]])

        elif hasattr(bot, 'wait_post_1') and bot.wait_post_1 and event.sender_id == DEV_ID:
            bot.wait_post_1 = False
            DB["temp_post_1"] = {
                "text": event.message.text,
                "entities": [e.to_dict() for e in event.message.entities or []],
                "media": event.message.media.to_dict() if event.message.media else None
            }
            save_db()
            await event.reply("✅ تم حفظ الرسالة 1\n\nدوس معاينة عشان تشوفها وتنشرها", buttons=[[Button.inline("🔙", b"back")]])

        elif hasattr(bot, 'wait_post_2') and bot.wait_post_2 and event.sender_id == DEV_ID:
            bot.wait_post_2 = False
            DB["temp_post_2"] = {
                "text": event.message.text,
                "entities": [e.to_dict() for e in event.message.entities or []],
                "media": event.message.media.to_dict() if event.message.media else None
            }
            save_db()
            await event.reply("✅ تم حفظ الرسالة 2\n\nدوس معاينة عشان تشوفها وتنشرها", buttons=[[Button.inline("🔙", b"back")]])

        elif hasattr(bot, 'wait_add_group') and bot.wait_add_group and event.sender_id == DEV_ID:
            bot.wait_add_group = False
            try:
                text = event.text.strip()
                acc = get_current_account()
                acc_id = DB["current_account"]
                if acc_id not in userbots:
                    return await event.reply("❌ شغل الحساب الاول")
                client = userbots[acc_id]
                
                if text.startswith('https://t.me/'):
                    username = text.split('/')[-1]
                    entity = await client.get_entity(username)
                    gid = entity.id
                elif text.startswith('-100'):
                    gid = int(text)
                else:
                    gid = int(text)
                
                if gid not in acc["groups"]:
                    acc["groups"].append(gid)
                    save_db()
                    chat = await client.get_entity(gid)
                    add_log(f"اضافة جروب حساب{acc_id}", chat.title)
                    await event.reply(f"✅ تم اضافة الجروب:\n\n{chat.title}\n`{gid}`", buttons=[[Button.inline("🔙", b"groups_menu")]])
                else:
                    await event.reply("⚠️ الجروب متضاف قبل كده", buttons=[[Button.inline("🔙", b"groups_menu")]])
            except Exception as e:
                await event.reply(f"❌ فشل اضافة الجروب\nتأكد ان الحساب جوة الجروب\n\n{e}", buttons=[[Button.inline("🔙", b"groups_menu")]])

        elif hasattr(bot, 'wait_del_group') and bot.wait_del_group and event.sender_id == DEV_ID:
            bot.wait_del_group = False
            try:
                gid = int(event.text.strip())
                acc = get_current_account()
                if gid in acc["groups"]:
                    acc["groups"].remove(gid)
                    save_db()
                    add_log(f"حذف جروب حساب{DB['current_account']}", str(gid))
                    await event.reply(f"✅ تم حذف الجروب `{gid}`", buttons=[[Button.inline("🔙", b"groups_menu")]])
                else:
                    await event.reply("❌ الجروب مش موجود في القائمة", buttons=[[Button.inline("🔙", b"groups_menu")]])
            except:
                await event.reply("❌ ايدي غلط", buttons=[[Button.inline("🔙", b"groups_menu")]])

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN مش موجود في Variables")
        return
    await setup_bot()
    for acc_id, acc in DB["accounts"].items():
        if acc.get("phone"):
            await start_userbot(int(acc_id))
    print(f"✅ Bot V30.1 Pro Plus شغال | {DEVICE_MODEL} | مخفي 👻")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
