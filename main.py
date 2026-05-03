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
LOGS_FILE = "logs.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r', encoding='utf-8') as f: return json.load(f)
    return {
        "phone": None,
        "groups": [],
        "active_groups": [], # للفلتر
        "welcome": "نورت يا {name} 💎",
        "replies": ["موجود ✨", "اؤمرني 🌟", "معاك 💎"],
        "wait_min": 5,
        "wait_max": 10,
        "stealth_mode": True,
        "auto_reply": True,
        "speed_mode": False,
        "temp_post": None,
        "scheduled_time": None,
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

DB = load_db()
USERS = load_users()
userbot = None
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

async def register_userbot_handlers():
    global userbot
    if not userbot: return

    @userbot.on(events.ChatAction)
    async def welcome_handler(event):
        try:
            if (event.user_joined or event.user_added) and event.chat_id in DB["groups"]:
                await userbot(UpdateStatusRequest(offline=True))
                user = await event.get_user()
                text = DB["welcome"].format(name=user.first_name, username=user.username or "بدون")
                await event.reply(text, silent=True)
                DB["stats"]["messages"] += 1
                add_log("ترحيب", f"في {event.chat_id}")
        except Exception as e:
            print(f"Welcome error: {e}")

    @userbot.on(events.NewMessage)
    async def mention_reply_handler(event):
        try:
            if event.chat_id in DB["groups"] and event.mentioned and DB["auto_reply"]:
                await userbot(UpdateStatusRequest(offline=True))
                reply = random.choice(DB["replies"])
                await event.reply(reply, silent=True)
                DB["stats"]["messages"] += 1
        except Exception as e:
            print(f"Reply error: {e}")

async def start_userbot():
    global userbot
    if DB["phone"]:
        try:
            userbot = TelegramClient(
                f'ios_{DB["phone"]}', API_ID, API_HASH,
                device_model=DEVICE_MODEL, system_version=SYSTEM_VERSION,
                app_version=APP_VERSION, lang_code=LANG_CODE, system_lang_code=SYSTEM_LANG_CODE
            )
            await userbot.connect()
            if await userbot.is_user_authorized():
                await userbot(UpdateStatusRequest(offline=True))
                await register_userbot_handlers()
                print(f"✅ {DEVICE_MODEL} | iOS {SYSTEM_VERSION} | مخفي 👻")
                return True
        except Exception as e:
            print(f"❌ خطأ في اليوزربوت: {e}")
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
        btns = [
            [Button.inline("➕ توليد كود", b"gen_code"), Button.inline("📊 احصائيات كاملة", b"full_stats")],
            [Button.inline("👥 المستخدمين", b"list_users"), Button.inline("🔑 الاكواد", b"list_codes")],
            [Button.inline("🚫 حظر", b"ban_user"), Button.inline("✅ فك حظر", b"unban_user")],
            [Button.inline("💾 نسخ احتياطي", b"backup"), Button.inline("📥 استيراد", b"restore")]
        ]
        await event.reply(f"👑 **لوحة الادمن Pro**\n\n📱 {DEVICE_MODEL}\n🔢 iOS {SYSTEM_VERSION}\n\nالمستخدمين: {total_users}\nاكواد متاحة: {active_codes}\nتجربة مجانية: {trials}\nالجروبات: {len(DB['groups'])}\nالمنشورات: {DB['stats']['posts']}", buttons=btns)

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
        banned = len([u for u in USERS["users"].values() if u.get("banned")])
        trials = len(USERS["trials"])
        posts = DB['stats']['posts']
        msgs = DB['stats']['messages']
        
        top_groups = sorted(DB['stats']['groups_count'].items(), key=lambda x: x[1], reverse=True)[:5]
        top_text = "\n".join([f"• `{g}`: {c} منشور" for g, c in top_groups]) if top_groups else "مفيش"
        
        txt = f"📊 **احصائيات شاملة**\n\n👥 المستخدمين: {total}\n✅ مفعلين: {active}\n🚫 محظورين: {banned}\n🎁 تجربة: {trials}\n\n📤 المنشورات: {posts}\n💬 الرسايل التلقائية: {msgs}\n👥 الجروبات: {len(DB['groups'])}\n\n**🔥 اكتر جروبات نشطة:**\n{top_text}"
        await event.edit(txt, buttons=[[Button.inline("🔙", b"admin_back")]])

    @bot.on(events.CallbackQuery(data=b"backup"))
    async def backup(event):
        if not is_admin(event.sender_id): return
        data = json.dumps(DB, indent=2, ensure_ascii=False)
        await event.respond(f"💾 **نسخة احتياطية**\n\nانسخ النص ده واحفظه:\n\n```json\n{data[:3500]}\n```", buttons=[[Button.inline("🔙", b"admin_back")]])

    @bot.on(events.CallbackQuery(data=b"restore"))
    async def restore(event):
        if not is_admin(event.sender_id): return
        await event.edit("📥 ابعت ملف JSON او الصق البيانات:\n\nتنبيه: هيتم استبدال كل الاعدادات", buttons=[[Button.inline("🔙", b"admin_back")]])
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
            await event.reply("⚠️ **Azef Pro V29**\n\n🎁 جرب البوت مجاناً لمدة 24 ساعة\n🔑 او فعل كود الاشتراك\n\nللشراء والدعم:", buttons=btns)
            return

        phone_status = f"✅ {DB['phone']}" if DB["phone"] else "❌ مش متضاف"
        wait_status = f"{DB['wait_min']}-{DB['wait_max']}ث"
        stealth_status = "👻 مفعل" if DB["stealth_mode"] else "👁️ معطل"
        auto_status = "✅ مفعل" if DB["auto_reply"] else "❌ معطل"
        speed_status = "⚡ سريع" if DB["speed_mode"] else "🔵 عادي"
        schedule_status = DB["scheduled_time"] or "فوري"
        active_count = len(DB["active_groups"]) if DB["active_groups"] else len(DB["groups"])

        if not is_admin(event.sender_id):
            sub_info = f"\n⏳ فاضل: {days_left} يوم"
        else:
            sub_info = "\n👑 حساب ادمن"

        btns = [
            [Button.inline(f"📱 {phone_status}", b"account"), Button.inline(f"📊 {DB['stats']['posts']} منشور", b"show_stats")],
            [Button.inline("👥 الجروبات", b"groups_menu"), Button.inline("📝 السجلات", b"show_logs")],
            [Button.inline("📤 نشر منشور", b"send_post"), Button.inline("👁️ معاينة", b"preview")],
            [Button.inline(f"⏰ {schedule_status}", b"schedule_time"), Button.inline(f"⏳ {wait_status}", b"set_wait")],
            [Button.inline(f"👻 تخفي: {stealth_status}", b"toggle_stealth"), Button.inline(f"🔔 رد تلقائي: {auto_status}", b"toggle_auto")],
            [Button.inline(f"🚀 السرعة: {speed_status}", b"toggle_speed"), Button.inline("🎯 فلتر الجروبات", b"filter_groups")],
            [Button.inline("👋 الترحيب", b"set_welcome"), Button.inline("💬 الردود", b"set_replies")],
            [Button.inline("⚙️ الاعدادات", b"settings"), Button.url("💬 الدعم", f"https://t.me/{DEV_USERNAME}")]
        ]
        await event.reply(f"🤖 **Azef Pro V29** {sub_info}\n\n📱 {DEVICE_MODEL} | iOS {SYSTEM_VERSION}\n\nالجروبات: {len(DB['groups'])} | النشطة: {active_count}\nالانتظار: {wait_status} | النشر: {schedule_status}\nالتخفي: {stealth_status} | السرعة: {speed_status}", buttons=btns)

    @bot.on(events.CallbackQuery(data=b"show_stats"))
    async def show_stats(event):
        if not check_sub(event.sender_id)[0]: return
        posts = DB['stats']['posts']
        msgs = DB['stats']['messages']
        txt = f"📊 **احصائياتك**\n\n📤 المنشورات: {posts}\n💬 الردود التلقائية: {msgs}\n👥 الجروبات: {len(DB['groups'])}"
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
        btns = [
            [Button.inline("👥 جلب المجموعات", b"get_groups"), Button.inline("📝 مجموعاتي", b"my_groups")],
            [Button.inline("➕ اضافة جروب", b"add_group"), Button.inline("➖ حذف جروب", b"del_group")],
            [Button.inline("🎯 تحديد النشطة", b"set_active"), Button.inline("🗑️ حذف الكل", b"clear_groups")],
            [Button.inline("🔙", b"back")]
        ]
        await event.edit(f"👥 **ادارة الجروبات**\n\nالكل: {len(DB['groups'])}\nالنشطة: {len(DB['active_groups']) if DB['active_groups'] else len(DB['groups'])}", buttons=btns)

    @bot.on(events.CallbackQuery(data=b"set_active"))
    async def set_active(event):
        if not check_sub(event.sender_id)[0]: return
        await event.edit("🎯 ابعت ايديهات الجروبات النشطة مفصولة بسطر جديد:\n\nمثال:\n`-1001234567890`\n`-1009876543210`\n\nاو ابعت `الكل` لنشر في الكل", buttons=[[Button.inline("🔙", b"groups_menu")]])
        bot.wait_active = True

    @bot.on(events.CallbackQuery(data=b"filter_groups"))
    async def filter_groups(event):
        if not check_sub(event.sender_id)[0]: return
        if not DB["active_groups"]:
            await event.answer("الفلتر معطل - النشر في كل الجروبات", alert=True)
        else:
            await event.answer(f"الفلتر مفعل - {len(DB['active_groups'])} جروب نشط", alert=True)

    @bot.on(events.CallbackQuery(data=b"toggle_auto"))
    async def toggle_auto(event):
        if not check_sub(event.sender_id)[0]: return
        DB["auto_reply"] = not DB["auto_reply"]
        save_db()
        status = "مفعل" if DB["auto_reply"] else "معطل"
        await event.answer(f"🔔 الرد التلقائي: {status}", alert=True)
        await start_panel(event)

    @bot.on(events.CallbackQuery(data=b"toggle_speed"))
    async def toggle_speed(event):
        if not check_sub(event.sender_id)[0]: return
        DB["speed_mode"] = not DB["speed_mode"]
        if DB["speed_mode"]:
            DB["wait_min"], DB["wait_max"] = 3, 5
        else:
            DB["wait_min"], DB["wait_max"] = 5, 10
        save_db()
        status = "سريع 3-5ث" if DB["speed_mode"] else "عادي 5-10ث"
        await event.answer(f"🚀 وضع السرعة: {status}", alert=True)
        await start_panel(event)

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
        DB["wait_min"], DB["wait_max"] = 5, 10
        DB["stealth_mode"] = True
        DB["auto_reply"] = True
        DB["speed_mode"] = False
        DB["scheduled_time"] = None
        DB["active_groups"] = []
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

    # باقي الكولباكس زي V28 بالظبط...
    @bot.on(events.CallbackQuery(data=b"schedule_time"))
    async def schedule_time_menu(event):
        if not check_sub(event.sender_id)[0]: return
        btns = [
            [Button.inline("⚡ الآن فوري", b"sched_now")],
            [Button.inline("⏰ بعد ساعة", b"sched_1h"), Button.inline("⏰ بعد 3 ساعات", b"sched_3h")],
            [Button.inline("🌙 الساعة 10 بليل", b"sched_10pm"), Button.inline("🌅 الساعة 9 الصبح", b"sched_9am")],
            [Button.inline("✏️ وقت مخصص", b"sched_custom"), Button.inline("🔙", b"back")]
        ]
        current = DB["scheduled_time"] or "فوري"
        await event.edit(f"⏰ **توقيت النشر:**\n\nالحالي: `{current}`", buttons=btns)

    @bot.on(events.CallbackQuery(pattern=b"sched_"))
    async def set_schedule(event):
        if not check_sub(event.sender_id)[0]: return
        data = event.data.decode()
        now = datetime.datetime.now()
        if data == "sched_now":
            DB["scheduled_time"] = None
            await event.answer("⚡ هيتنشر فوري", alert=True)
        elif data == "sched_1h":
            time = now + datetime.timedelta(hours=1)
            DB["scheduled_time"] = time.strftime("%Y-%m-%d %H:%M")
        elif data == "sched_3h":
            time = now + datetime.timedelta(hours=3)
            DB["scheduled_time"] = time.strftime("%Y-%m-%d %H:%M")
        elif data == "sched_10pm":
            time = now.replace(hour=22, minute=0, second=0)
            if time < now: time += datetime.timedelta(days=1)
            DB["scheduled_time"] = time.strftime("%Y-%m-%d %H:%M")
        elif data == "sched_9am":
            time = now.replace(hour=9, minute=0, second=0)
            if time < now: time += datetime.timedelta(days=1)
            DB["scheduled_time"] = time.strftime("%Y-%m-%d %H:%M")
        elif data == "sched_custom":
            await event.edit("✏️ ابعت الوقت:\n\nصيغة: `YYYY-MM-DD HH:MM`", buttons=[[Button.inline("🔙", b"schedule_time")]])
            bot.wait_schedule = True
            return
        save_db()
        await start_panel(event)

    @bot.on(events.CallbackQuery(data=b"set_wait"))
    async def set_wait_menu(event):
        if not check_sub(event.sender_id)[0]: return
        btns = [
            [Button.inline("⚡ 5-10 ثواني", b"wait_5_10")],
            [Button.inline("🔵 10-20 ثانية", b"wait_10_20")],
            [Button.inline("🟡 30-60 ثانية", b"wait_30_60")],
            [Button.inline("🟢 60-120 ثانية", b"wait_60_120")],
            [Button.inline("✏️ مخصص", b"wait_custom"), Button.inline("🔙", b"back")]
        ]
        current = f"{DB['wait_min']}-{DB['wait_max']} ثانية"
        await event.edit(f"⏳ **وقت الانتظار:**\n\nالحالي: `{current}`", buttons=btns)

    @bot.on(events.CallbackQuery(pattern=b"wait_"))
    async def set_wait(event):
        if not check_sub(event.sender_id)[0]: return
        data = event.data.decode()
        if data == "wait_5_10": DB["wait_min"], DB["wait_max"] = 5, 10
        elif data == "wait_10_20": DB["wait_min"], DB["wait_max"] = 10, 20
        elif data == "wait_30_60": DB["wait_min"], DB["wait_max"] = 30, 60
        elif data == "wait_60_120": DB["wait_min"], DB["wait_max"] = 60, 120
        elif data == "wait_custom":
            await event.edit("✏️ ابعت رقمين:\n\nمثال: `15 30`", buttons=[[Button.inline("🔙", b"set_wait")]])
            bot.wait_delay = True
            return
        save_db()
        await event.answer(f"✅ تم التعيين {DB['wait_min']}-{DB['wait_max']}ث", alert=True)
        await start_panel(event)

    @bot.on(events.CallbackQuery(data=b"toggle_stealth"))
    async def toggle_stealth(event):
        if not check_sub(event.sender_id)[0]: return
        DB["stealth_mode"] = not DB["stealth_mode"]
        save_db()
        if userbot and await userbot.is_user_authorized():
            try:
                if DB["stealth_mode"]:
                    await userbot(UpdateStatusRequest(offline=True))
            except: pass
        await start_panel(event)

    @bot.on(events.CallbackQuery(data=b"account"))
    async def manage_account(event):
        if not check_sub(event.sender_id)[0]: return
        if DB["phone"]:
            btns = [[Button.inline("🔄 تغيير الرقم", b"change_phone")], [Button.inline("🗑️ حذف الرقم", b"del_phone")], [Button.inline("🔙", b"back")]]
            await event.edit(f"📱 الرقم الحالي:\n`{DB['phone']}`\n\nالجهاز: {DEVICE_MODEL}\nالنظام: {SYSTEM_VERSION}", buttons=btns)
        else:
            await event.edit("📱 ابعت رقمك بالكود الدولي\nمثال: `+201012345678`", buttons=[[Button.inline("🔙", b"back")]])
            bot.wait_phone = True

    @bot.on(events.CallbackQuery(data=b"set_welcome"))
    async def set_welcome(event):
        if not check_sub(event.sender_id)[0]: return
        await event.edit(f"👋 الترحيب الحالي:\n\n{DB['welcome']}\n\nابعت الترحيب الجديد:\n{{name}} و {{username}} + ايموجي بريميوم", buttons=[[Button.inline("🔙", b"back")]])
        bot.wait_welcome = True

    @bot.on(events.CallbackQuery(data=b"set_replies"))
    async def set_replies(event):
        if not check_sub(event.sender_id)[0]: return
        replies_text = "\n".join([f"{i+1}. {r}" for i, r in enumerate(DB["replies"])])
        btns = [[Button.inline("➕ اضافة رد", b"add_reply")], [Button.inline("🗑️ حذف آخر رد", b"del_reply"), Button.inline("🔙", b"back")]]
        await event.edit(f"💬 الردود الحالية:\n\n{replies_text}", buttons=btns)

    @bot.on(events.CallbackQuery(data=b"add_reply"))
    async def add_reply(event):
        if not check_sub(event.sender_id)[0]: return
        await event.edit("ابعت الرد الجديد:", buttons=[[Button.inline("🔙", b"set_replies")]])
        bot.wait_reply = True

    @bot.on(events.CallbackQuery(data=b"del_reply"))
    async def del_reply(event):
        if not check_sub(event.sender_id)[0]: return
        if DB["replies"]:
            DB["replies"].pop()
            save_db()
        await set_replies(event)

    @bot.on(events.CallbackQuery(data=b"get_groups"))
    async def get_groups(event):
        if not check_sub(event.sender_id)[0]: return
        if not userbot or not await userbot.is_user_authorized():
            return await event.answer("❌ ضيف رقم الاول", alert=True)
        await event.answer("⏳ جاري الجلب...", alert=False)
        try:
            dialogs = await userbot.get_dialogs(limit=200)
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
            added = 0
            for g in bot.temp_groups:
                if g["id"] not in DB["groups"]:
                    DB["groups"].append(g["id"])
                    added += 1
            save_db()
            add_log("اضافة جروبات", f"{added} جروب")
            await event.answer(f"✅ تم اضافة {added} جروب", alert=True)
            await start_panel(event)

    @bot.on(events.CallbackQuery(data=b"my_groups"))
    async def my_groups(event):
        if not check_sub(event.sender_id)[0]: return
        if not DB["groups"]: return await event.edit("❌ مفيش جروبات", buttons=[[Button.inline("🔙", b"groups_menu")]])
        text = "**📝 جروبات النشر:**\n\n"
        for gid in DB["groups"]:
            try:
                chat = await userbot.get_entity(int(gid))
                count = DB['stats']['groups_count'].get(str(gid), 0)
                text += f"• {chat.title}\n`{gid}` | {count} منشور\n\n"
            except: text += f"• محذوف `{gid}`\n\n"
        await event.edit(text, buttons=[[Button.inline("🔙", b"groups_menu")]])

    @bot.on(events.CallbackQuery(data=b"clear_groups"))
    async def clear_groups(event):
        if not check_sub(event.sender_id)[0]: return
        DB["groups"] = []
        DB["active_groups"] = []
        save_db()
        add_log("حذف الكل", "جروبات")
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

    @bot.on(events.CallbackQuery(data=b"send_post"))
    async def send_post(event):
        if not check_sub(event.sender_id)[0]: return
        if not userbot or not await userbot.is_user_authorized():
            return await event.answer("❌ ضيف رقم الاول", alert=True)
        await event.edit("ابعت المنشور دلوقتي:\n\nنص + ايموجي بريميوم + صور + فيديو", buttons=[[Button.inline("🔙", b"back")]])
        bot.wait_post = True

    @bot.on(events.CallbackQuery(data=b"preview"))
    async def preview(event):
        if not check_sub(event.sender_id)[0]: return
        if not DB.get("temp_post"):
            return await event.answer("❌ مفيش منشور محفوظ", alert=True)
        post = DB["temp_post"]
        btns = [[Button.inline("✅ نشر الآن", b"confirm_post")], [Button.inline("🔙", b"back")]]
        await event.edit("👁️ **معاينة المنشور:**\n\n" + post["text"], buttons=btns)

    @bot.on(events.CallbackQuery(data=b"confirm_post"))
    async def confirm_post(event):
        if not check_sub(event.sender_id)[0]: return
        if not DB.get("temp_post"):
            return await event.answer("❌ مفيش منشور", alert=True)

        if DB["scheduled_time"]:
            sched_time = datetime.datetime.strptime(DB["scheduled_time"], "%Y-%m-%d %H:%M")
            now = datetime.datetime.now()
            if sched_time > now:
                wait_seconds = (sched_time - now).total_seconds()
                await event.edit(f"⏰ تم الجدولة\n\nهيتنشر في: `{DB['scheduled_time']}`\nبعد: {int(wait_seconds/60)} دقيقة")
                await asyncio.sleep(wait_seconds)
                DB["scheduled_time"] = None
                save_db()

        post = DB["temp_post"]
        wait_min, wait_max = DB["wait_min"], DB["wait_max"]
        
        # فلتر الجروبات النشطة
        target_groups = DB["active_groups"] if DB["active_groups"] else DB["groups"]

        msg = await event.edit(f"⏳ جاري النشر في {len(target_groups)} جروب...\nالانتظار: {wait_min}-{wait_max}ث")
        sent, failed = 0, 0

        for gid in target_groups:
            try:
                await userbot(UpdateStatusRequest(offline=True))
                await userbot.send_read_acknowledge(int(gid), max_id=0)

                if post["media"]:
                    from telethon.tl.types import MessageMedia
                    media = MessageMedia.from_dict(post["media"])
                    await userbot.send_file(int(gid), media, caption=post["text"], silent=True)
                else:
                    await userbot.send_message(int(gid), post["text"], silent=True)

                sent += 1
                DB["stats"]["posts"] += 1
                DB["stats"]["groups_count"][str(gid)] = DB["stats"]["groups_count"].get(str(gid), 0) + 1
                wait_time = random.randint(wait_min, wait_max)
                await asyncio.sleep(wait_time)

            except FloodWaitError as e:
                await msg.edit(f"⚠️ تيليجرام عامل حظر مؤقت {e.seconds} ثانية\nزود وقت الانتظار")
                return
            except Exception as e:
                failed += 1
                print(f"Failed {gid}: {e}")

        DB["temp_post"] = None
        save_db()
        add_log("نشر منشور", f"مرسل: {sent} | فشل: {failed}")
        await msg.edit(f"✅ تم\n\nمرسل: {sent}\nفشل: {failed}\nالانتظار: {wait_min}-{wait_max}ث")

    @bot.on(events.CallbackQuery(data=b"change_phone"))
    async def change_phone(event):
        if not check_sub(event.sender_id)[0]: return
        DB["phone"] = None
        save_db()
        global userbot
        if userbot: await userbot.disconnect()
        userbot = None
        await event.edit("📱 ابعت الرقم الجديد:\n`+201012345678`")
        bot.wait_phone = True

    @bot.on(events.CallbackQuery(data=b"del_phone"))
    async def del_phone(event):
        if not check_sub(event.sender_id)[0]: return
        DB["phone"] = None
        save_db()
        global userbot
        if userbot: await userbot.disconnect()
        userbot = None
        await event.answer("🗑️ تم حذف الرقم", alert=True)
        await start_panel(event)

    @bot.on(events.CallbackQuery(data=b"back"))
    async def back(event):
        await start_panel(event)

    @bot.on(events.NewMessage)
    async def handle_input(event):
        global userbot
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
            DB["phone"] = phone
            save_db()
            userbot = TelegramClient(
                f'ios_{phone}', API_ID, API_HASH,
                device_model=DEVICE_MODEL, system_version=SYSTEM_VERSION,
                app_version=APP_VERSION, lang_code=LANG_CODE, system_lang_code=SYSTEM_LANG_CODE
            )
            await userbot.connect()
            try:
                await userbot.send_code_request(phone)
                await msg.edit("✅ اتبعت الكود على تيليجرام\nابعت الكود هنا:")
                bot.wait_code = True
            except Exception as e:
                await msg.edit(f"❌ خطأ: {e}")
                DB["phone"] = None
                save_db()

        elif hasattr(bot, 'wait_code') and bot.wait_code and event.sender_id == DEV_ID:
            bot.wait_code = False
            code = event.text.strip()
            msg = await event.reply("⏳ جاري تسجيل الدخول...")
            try:
                await userbot.sign_in(DB["phone"], code)
                await start_userbot()
                await msg.edit(f"✅ تم التسجيل بنجاح\n\n📱 {DEVICE_MODEL}\n🔢 iOS {SYSTEM_VERSION}\n📲 Telegram {APP_VERSION}")
                await start_panel(event)
            except SessionPasswordNeededError:
                await msg.edit("🔐 الحساب عليه تحقق بخطوتين\nابعت كلمة السر:")
                bot.wait_2fa = True
            except PhoneCodeInvalidError:
                await msg.edit("❌ الكود غلط\nابعت /start وجرب تاني")
            except Exception as e:
                await msg.edit(f"❌ خطأ: {e}")

        elif hasattr(bot, 'wait_2fa') and bot.wait_2fa and event.sender_id == DEV_ID:
            bot.wait_2fa = False
            password = event.text.strip()
            msg = await event.reply("⏳ جاري التحقق...")
            try:
                await userbot.sign_in(password=password)
                await start_userbot()
                await msg.edit(f"✅ تم التسجيل بنجاح\n\n📱 {DEVICE_MODEL}\n🔢 iOS {SYSTEM_VERSION}\n📲 Telegram {APP_VERSION}")
                await start_panel(event)
            except Exception as e:
                await msg.edit(f"✅ تم بنجاح")

        elif hasattr(bot, 'wait_schedule') and bot.wait_schedule and event.sender_id == DEV_ID:
            bot.wait_schedule = False
            try:
                dt = datetime.datetime.strptime(event.text.strip(), "%Y-%m-%d %H:%M")
                if dt < datetime.datetime.now():
                    return await event.reply("❌ التاريخ ده عدى خلاص")
                DB["scheduled_time"] = event.text.strip()
                save_db()
                await event.reply(f"✅ هيتنشر في:\n`{DB['scheduled_time']}`", buttons=[[Button.inline("🔙", b"back")]])
            except:
                await event.reply("❌ صيغة غلط\nمثال: `2026-05-03 14:30`", buttons=[[Button.inline("🔙", b"schedule_time")]])

        elif hasattr(bot, 'wait_delay') and bot.wait_delay and event.sender_id == DEV_ID:
            bot.wait_delay = False
            try:
                parts = event.text.split()
                min_delay = int(parts[0])
                max_delay = int(parts[1])
                if min_delay >= max_delay: raise ValueError
                if min_delay < 3: raise ValueError("اقل حاجة 3 ثواني")
                DB["wait_min"] = min_delay
                DB["wait_max"] = max_delay
                save_db()
                await event.reply(f"✅ تم التعيين\n\nالحد الادنى: {min_delay}ث\nالحد الاقصى: {max_delay}ث", buttons=[[Button.inline("🔙", b"back")]])
            except:
                await event.reply("❌ صيغة غلط\nمثال صحيح: `15 30`", buttons=[[Button.inline("🔙", b"set_wait")]])

        elif hasattr(bot, 'wait_welcome') and bot.wait_welcome and event.sender_id == DEV_ID:
            bot.wait_welcome = False
            DB["welcome"] = event.text
            save_db()
            await event.reply("✅ تم تعيين الترحيب الجديد", buttons=[[Button.inline("🔙", b"back")]])

        elif hasattr(bot, 'wait_reply') and bot.wait_reply and event.sender_id == DEV_ID:
            bot.wait_reply = False
            DB["replies"].append(event.text)
            save_db()
            await event.reply(f"✅ تم اضافة الرد رقم {len(DB['replies'])}", buttons=[[Button.inline("🔙", b"set_replies")]])

        elif hasattr(bot, 'wait_active') and bot.wait_active and event.sender_id == DEV_ID:
            bot.wait_active = False
            text = event.text.strip()
            if text == "الكل":
                DB["active_groups"] = []
                save_db()
                return await event.reply("✅ تم - النشر في كل الجروبات", buttons=[[Button.inline("🔙", b"groups_menu")]])
            try:
                gids = [int(x.strip()) for x in text.split('\n') if x.strip()]
                DB["active_groups"] = [g for g in gids if g in DB["groups"]]
                save_db()
                await event.reply(f"✅ تم تحديد {len(DB['active_groups'])} جروب نشط", buttons=[[Button.inline("🔙", b"groups_menu")]])
            except:
                await event.reply("❌ صيغة غلط", buttons=[[Button.inline("🔙", b"groups_menu")]])

        elif hasattr(bot, 'wait_add_group') and bot.wait_add_group and event.sender_id == DEV_ID:
            bot.wait_add_group = False
            try:
                text = event.text.strip()
                if text.startswith('https://t.me/'):
                    username = text.split('/')[-1]
                    entity = await userbot.get_entity(username)
                    gid = entity.id
                elif text.startswith('-100'):
                    gid = int(text)
                else:
                    gid = int(text)
                
                if gid not in DB["groups"]:
                    DB["groups"].append(gid)
                    save_db()
                    chat = await userbot.get_entity(gid)
                    add_log("اضافة جروب", chat.title)
                    await event.reply(f"✅ تم اضافة الجروب:\n\n{chat.title}\n`{gid}`", buttons=[[Button.inline("🔙", b"groups_menu")]])
                else:
                    await event.reply("⚠️ الجروب متضاف قبل كده", buttons=[[Button.inline("🔙", b"groups_menu")]])
            except Exception as e:
                await event.reply(f"❌ فشل اضافة الجروب\nتأكد ان اليوزربوت جوة الجروب\n\n{e}", buttons=[[Button.inline("🔙", b"groups_menu")]])

        elif hasattr(bot, 'wait_del_group') and bot.wait_del_group and event.sender_id == DEV_ID:
            bot.wait_del_group = False
            try:
                gid = int(event.text.strip())
                if gid in DB["groups"]:
                    DB["groups"].remove(gid)
                    if gid in DB["active_groups"]: DB["active_groups"].remove(gid)
                    save_db()
                    add_log("حذف جروب", str(gid))
                    await event.reply(f"✅ تم حذف الجروب `{gid}`", buttons=[[Button.inline("🔙", b"groups_menu")]])
                else:
                    await event.reply("❌ الجروب مش موجود في القائمة", buttons=[[Button.inline("🔙", b"groups_menu")]])
            except:
                await event.reply("❌ ايدي غلط", buttons=[[Button.inline("🔙", b"groups_menu")]])

        elif hasattr(bot, 'wait_post') and bot.wait_post and event.sender_id == DEV_ID:
            bot.wait_post = False
            if not userbot or not await userbot.is_user_authorized():
                return await event.reply("❌ ضيف رقم الاول")
            if not DB["groups"]: return await event.reply("❌ ضيف جروبات الاول")
            DB["temp_post"] = {
                "text": event.message.text,
                "entities": [e.to_dict() for e in event.message.entities or []],
                "media": event.message.media.to_dict() if event.message.media else None
            }
            save_db()
            wait_text = f"{DB['wait_min']}-{DB['wait_max']} ثانية"
            sched_text = DB["scheduled_time"] or "فوري"
            btns = [
                [Button.inline("✅ نشر الآن", b"confirm_post"), Button.inline("👁️ معاينة", b"preview")],
                [Button.inline("❌ الغاء", b"back")]
            ]
            await event.reply(f"📝 تم حفظ المنشور\n\nالجروبات: {len(DB['groups'])}\nالنشر: {sched_text}\nالانتظار: {wait_text}\nالتخفي: {'مفعل' if DB['stealth_mode'] else 'معطل'}", buttons=btns)

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN مش موجود في Variables")
        return
    await setup_bot()
    await start_userbot()
    print(f"✅ Bot Pro شغال | {DEVICE_MODEL} | iOS {SYSTEM_VERSION} | مخفي 👻")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
