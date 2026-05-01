from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import asyncio
import json
import os
import subprocess
import sys
import secrets
import string
from datetime import datetime

API_ID = 33595004
API_HASH = 'cbd1066ed026997f2f4a7c4323b7bda7'
BOT_TOKEN = os.getenv('FACTORY_BOT_TOKEN')
ADMIN_ID = 154919127
DB_FILE = 'factory_db.json'
BOTS_DIR = 'client_bots'
PRICE = 15

PAYMENT_METHODS = {
    'vodafone': {'name': 'Vodafone Cash', 'number': '01010706262', 'icon': '📱'},
    'usdt_trc20': {'name': 'USDT TRC20', 'address': 'TWunFGpcDDc63GTDdNxyDHjZ4VdPS6AsMh', 'icon': '💎'},
    'ton': {'name': 'TON', 'address': 'UQAarGycIaNnngwNAQ1Tek32I3MGroiaeF6p6MxEadimfszt', 'icon': '💎'},
    'usdt_aptos': {'name': 'USDT Aptos', 'address': '83f5eede85de0d63ee219d1a5bdbbb3ff18af7fa35281aa330f55a9c8a90cf83', 'icon': '💎'}
}

bot = TelegramClient('factory_bot', API_ID, API_HASH)
db = {'clients': {}, 'pending': {}, 'running_bots': {}, 'setup': {}, 'codes': {}}
waiting_for = {}

def load_db():
    global db
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            db = json.load(f)
    except:
        save_db()

def save_db():
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(db, f, ensure_ascii=False, indent=2)

if not os.path.exists(BOTS_DIR):
    os.makedirs(BOTS_DIR)

def generate_code(length=8):
    return ''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(length))

def main_menu(uid):
    if uid == ADMIN_ID:
        return [
            [Button.inline("👥 العملاء", b"clients"), Button.inline("⏳ قيد الانتظار", b"pending")],
            [Button.inline("🤖 البوتات الشغالة", b"running"), Button.inline("🎫 الاكواد", b"codes")],
            [Button.inline("📊 احصائيات", b"stats")]
        ]
    else:
        return [
            [Button.inline("💰 شراء بوت نشر $15", b"buy")],
            [Button.inline("📊 حالة بوتي", b"my_bot")],
            [Button.url("👨‍💻 المطور", "https://t.me/Devazf")]
        ]

def payment_menu():
    btns = []
    for key, method in PAYMENT_METHODS.items():
        btns.append([Button.inline(f"{method['icon']} {method['name']}", f"pay_{key}".encode())])
    btns.append([Button.inline("✅ دفعت - ارسل الاثبات", b"send_proof")])
    btns.append([Button.inline("🔙 رجوع", b"back")])
    return btns

def setup_menu(uid):
    data = db['setup'].get(str(uid), {})
    token = "✅" if data.get('token') else "❌"
    admin_id = "✅" if data.get('admin_id') else "❌"
    channel = f"✅ @{data['channel']}" if data.get('channel') else "⚪ اختياري"
    dev = f"✅ @{data['dev']}" if data.get('dev') else "⚪ افتراضي"

    btns = [
        [Button.inline(f"🤖 التوكن {token}", b"set_token")],
        [Button.inline(f"👑 ايدي الادمن {admin_id}", b"set_admin")],
        [Button.inline(f"📢 قناة الاشتراك {channel}", b"set_channel")],
        [Button.inline(f"👨‍💻 يوزر المطور {dev}", b"set_dev")]
    ]

    if data.get('token') and data.get('admin_id'):
        btns.append([Button.inline("✅ تشغيل البوت", b"run_bot")])

    return btns

def admin_client_menu(cid):
    client = db['clients'].get(cid, {})
    is_free = "✅ مجاني" if client.get('is_free') else "💰 مدفوع"
    is_vip = "⭐ VIP" if client.get('is_vip') else "👤 عادي"

    return [
        [Button.inline(f"{is_free}", f"toggle_free_{cid}".encode())],
        [Button.inline(f"{is_vip}", f"toggle_vip_{cid}".encode())],
        [Button.inline("🎫 صنع كود له", f"gen_code_{cid}".encode())],
        [Button.inline("🗑️ حذف البوت", f"delete_bot_{cid}".encode())],
        [Button.inline("🔙 رجوع", b"clients")]
    ]

def save_bot_code(bot_token, admin_id, username, required_channel, dev_username, client_id):
    channels = f"['{required_channel}']" if required_channel else "[]"

    lines = [
        'from telethon import TelegramClient, events, Button',
        'from telethon.sessions import StringSession',
        'from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError, UserDeactivatedBanError, UserAlreadyParticipantError',
        'from telethon.tl.functions.channels import GetParticipantRequest, JoinChannelRequest',
        'from telethon.tl.types import MessageEntityCustomEmoji, MessageEntityBold, MessageEntityItalic, MessageEntityCode, MessageEntityPre, MessageEntityTextUrl, MessageEntityUrl, Channel',
        'from telethon.errors.rpcerrorlist import ChatWriteForbiddenError, ChatAdminRequiredError, UserBannedInChannelError, SlowModeWaitError, ChannelPrivateError, UserNotParticipantError, AuthKeyUnregisteredError, MessageNotModifiedError',
        'import asyncio',
        'import json',
        'import os',
        'from datetime import datetime, timedelta',
        'import random',
        'import re',
        '',
        'API_ID = 33595004',
        "API_HASH = 'cbd1066ed026997f2f4a7c4323b7bda7'",
        f'BOT_TOKEN = "{bot_token}"',
        f'ADMIN_ID = {admin_id}',
        f"DEVELOPER_USERNAME = '{dev_username}'",
        "DEVELOPER_LINK = f'https://t.me/{DEVELOPER_USERNAME}'",
        f'REQUIRED_CHANNELS = {channels}',
        f"DB_FILE = 'db_{admin_id}.json'",
        f"BACKUP_FILE = 'backup_{admin_id}.json'",
        f"CLIENT_ID = '{client_id}'",
        f"FACTORY_API = 'https://factory-api-check.com'", # رابط وهمي للتحقق
        'SUB_PRICE = 5',
        'MAX_ACCOUNTS = 1',
        'FREE_TRIAL_DAYS = 99999',
        '',
        f"bot = TelegramClient('bot_{admin_id}', API_ID, API_HASH)",
        "db = {'users': {}, 'codes': {}, 'stats': {'total_sent': 0}, 'login_notifications': True, 'bot_config': {'is_free': False, 'is_vip_only': False}}",
        'waiting_for = {}',
        'active_clients = {}',
        'running_tasks = {}',
        'user_clients = {}',
        'reply_tasks = {}',
        '',
        'STEALTH_MODES = {',
        " 'fast': {'group_delay': [2, 5], 'name': '⚡ سريع'},",
        " 'balanced': {'group_delay': [5, 10], 'name': '⚖️ متوازن'},",
        " 'safe': {'group_delay': [10, 20], 'name': '🛡️ آمن جدا'}",
        '}',
        '',
        'def load_db():',
        ' global db',
        ' try:',
        ' with open(DB_FILE, "r", encoding="utf-8") as f:',
        ' db = json.load(f)',
        ' except:',
        ' save_db()',
        '',
        'def save_db():',
        ' with open(DB_FILE, "w", encoding="utf-8") as f:',
        ' json.dump(db, f, ensure_ascii=False, indent=2)',
        '',
        'async def check_factory_config():',
        ' # هنا تقدر تتحقق من المصنع كل ساعة',
        ' # حاليا بنستخدم الاعدادات المحلية',
        ' pass',
        '',
        'def get_user_data(uid):',
        ' uid = str(uid)',
        ' if uid not in db["users"]:',
        ' db["users"][uid] = {',
        ' "sub_end": (datetime.now() + timedelta(days=36500)).isoformat(),',
        ' "accounts": {}, "current_account": None,',
        ' "messages": [{"text": "", "entities": [], "file_id": None, "type": "text"}, {"text": "", "entities": [], "file_id": None, "type": "text"}],',
        ' "publish_interval": 5, "flood_protection": 2, "stealth_mode": "balanced",',
        ' "auto_reply": False, "auto_reply_msg": "", "auto_reply_entities": [],',
        ' "welcome_msg": "", "welcome_entities": [],',
        ' "welcome_sent": [], "is_trial": False, "used_trial": True,',
        ' "is_vip": False',
        ' }',
        ' save_db()',
        ' if "welcome_sent" not in db["users"][uid]:',
        ' db["users"][uid]["welcome_sent"] = []',
        ' if "auto_reply_entities" not in db["users"][uid]:',
        ' db["users"][uid]["auto_reply_entities"] = []',
        ' if "welcome_entities" not in db["users"][uid]:',
        ' db["users"][uid]["welcome_entities"] = []',
        ' if "is_vip" not in db["users"][uid]:',
        ' db["users"][uid]["is_vip"] = False',
        ' if isinstance(db["users"][uid]["messages"][0], str):',
        ' old_msgs = db["users"][uid]["messages"]',
        ' db["users"][uid]["messages"] = [',
        ' {"text": old_msgs[0] if len(old_msgs) > 0 else "", "entities": [], "file_id": None, "type": "text"},',
        ' {"text": old_msgs[1] if len(old_msgs) > 1 else "", "entities": [], "file_id": None, "type": "text"}',
        ' ]',
        ' return db["users"][uid]',
        '',
        'def is_subscribed(uid):',
        ' if db["bot_config"].get("is_free"):',
        ' return True',
        ' if db["bot_config"].get("is_vip_only"):',
        ' return get_user_data(uid).get("is_vip", False)',
        ' return True',
        '',
        'def get_account(uid):',
        ' user = get_user_data(uid)',
        ' acc_id = user.get("current_account")',
        ' if not acc_id or acc_id not in user["accounts"]:',
        ' return None',
        ' return user["accounts"][acc_id]',
        '',
        'def get_account_defaults(acc):',
        ' defaults = {',
        ' "active": False, "groups": [], "name": "حساب جديد",',
        ' "phone": "", "session": "", "sent_count": 0,',
        ' "last_error": None, "created_at": datetime.now().isoformat(),',
        ' "replied_to": []',
        ' }',
        ' for k, v in defaults.items():',
        ' if k not in acc:',
        ' acc[k] = v',
        ' return acc',
        '',
        'def extract_entities_from_message(message):',
        ' entities = []',
        ' if message.entities:',
        ' for ent in message.entities:',
        ' if isinstance(ent, MessageEntityCustomEmoji):',
        ' entities.append({"type": "custom_emoji", "offset": ent.offset, "length": ent.length, "document_id": ent.document_id})',
        ' elif isinstance(ent, MessageEntityBold):',
        ' entities.append({"type": "bold", "offset": ent.offset, "length": ent.length})',
        ' elif isinstance(ent, MessageEntityItalic):',
        ' entities.append({"type": "italic", "offset": ent.offset, "length": ent.length})',
        ' elif isinstance(ent, MessageEntityCode):',
        ' entities.append({"type": "code", "offset": ent.offset, "length": ent.length})',
        ' elif isinstance(ent, MessageEntityPre):',
        ' entities.append({"type": "pre", "offset": ent.offset, "length": ent.length, "language": ent.language})',
        ' elif isinstance(ent, MessageEntityTextUrl):',
        ' entities.append({"type": "text_url", "offset": ent.offset, "length": ent.length, "url": ent.url})',
        ' elif isinstance(ent, MessageEntityUrl):',
        ' entities.append({"type": "url", "offset": ent.offset, "length": ent.length})',
        ' return entities',
        '',
        'def build_entities(saved_entities):',
        ' entities = []',
        ' for ent in saved_entities:',
        ' if ent["type"] == "custom_emoji":',
        ' entities.append(MessageEntityCustomEmoji(offset=ent["offset"], length=ent["length"], document_id=ent["document_id"]))',
        ' elif ent["type"] == "bold":',
        ' entities.append(MessageEntityBold(offset=ent["offset"], length=ent["length"]))',
        ' elif ent["type"] == "italic":',
        ' entities.append(MessageEntityItalic(offset=ent["offset"], length=ent["length"]))',
        ' elif ent["type"] == "code":',
        ' entities.append(MessageEntityCode(offset=ent["offset"], length=ent["length"]))',
        ' elif ent["type"] == "pre":',
        ' entities.append(MessageEntityPre(offset=ent["offset"], length=ent["length"], language=ent.get("language", "")))',
        ' elif ent["type"] == "text_url":',
        ' entities.append(MessageEntityTextUrl(offset=ent["offset"], length=ent["length"], url=ent["url"]))',
        ' elif ent["type"] == "url":',
        ' entities.append(MessageEntityUrl(offset=ent["offset"], length=ent["length"]))',
        ' return entities',
        '',
        'def main_menu(uid):',
        ' btns = [',
        ' [Button.inline("📱 اضافة حساب برقم", b"add_account")],',
        ' [Button.inline("📱 ادارة الحسابات", b"accounts_menu")],',
        ' [Button.inline("⚙️ اعدادات النشر", b"pub_settings"), Button.inline("📊 تحليل النشر", b"analyze")],',
        ' [Button.inline("🔄 تشغيل", b"start_pub"), Button.inline("⛔ ايقاف", b"stop_pub")],',
        ' [Button.inline("🎫 تفعيل كود", b"redeem"), Button.inline("⭐ ترقية VIP", b"upgrade_vip")],',
        ' [Button.inline("✨ مميزات البوت", b"features"), Button.inline("💡 نصائح الحماية", b"tips")],',
        ' [Button.url("👨‍💻 المطور", DEVELOPER_LINK)]',
        ' ]',
        ' return btns',
        '',
        'def accounts_menu(uid):',
        ' user = get_user_data(uid)',
        ' accounts = user["accounts"]',
        ' btns = []',
        ' for acc_id, acc in accounts.items():',
        ' acc = get_account_defaults(acc)',
        ' status = "🟢" if acc["active"] else "⚪"',
        ' current = " 👈" if user["current_account"] == acc_id else ""',
        ' btns.append([Button.inline(f"{status} {acc["name"]}{current}", f"select_acc_{acc_id}".encode())])',
        ' if len(accounts) < MAX_ACCOUNTS:',
        ' btns.append([Button.inline("➕ اضافة حساب جديد", b"add_account")])',
        ' btns.append([Button.inline("🔙 رجوع", b"back_main")])',
        ' return btns',
        '',
        'def account_details_menu(uid, acc_id):',
        ' acc = get_user_data(uid)["accounts"][acc_id]',
        ' acc = get_account_defaults(acc)',
        ' status = "🟢 يعمل" if acc["active"] else "🔴 متوقف"',
        ' btns = [',
        ' [Button.inline(f"{status}", f"toggle_acc_{acc_id}".encode())],',
        ' [Button.inline("✏️ تغيير الاسم", f"rename_acc_{acc_id}".encode())],',
        ' [Button.inline("👥 الجروبات", f"groups_acc_{acc_id}".encode())],',
        ' [Button.inline("💾 نسخ السيشن", f"copy_session_{acc_id}".encode())],',
        ' [Button.inline("🗑️ حذف الحساب", f"delete_acc_{acc_id}".encode())],',
        ' [Button.inline("🔙 رجوع", b"accounts_menu")]',
        ' ]',
        ' return btns',
        '',
        'def pub_settings_menu(uid):',
        ' user = get_user_data(uid)',
        ' acc = get_account(uid)',
        ' if not acc:',
        ' return [[Button.inline("❌ مفيش حساب محدد", b"accounts_menu")], [Button.inline("🔙 رجوع", b"back_main")]]',
        ' acc = get_account_defaults(acc)',
        ' status = "🟢 يعمل" if acc["active"] else "🔴 متوقف"',
        ' flood_level = ["❌", "🟡", "🟢", "🛡️"][user["flood_protection"]]',
        ' stealth = STEALTH_MODES[user["stealth_mode"]]["name"]',
        ' auto_reply = "✅" if user["auto_reply"] else "❌"',
        ' msg1 = user["messages"][0]',
        ' msg2 = user["messages"][1]',
        ' msg1_status = "✅ ملصق" if msg1["type"] == "sticker" else "✅ نص" if msg1["text"] else "❌"',
        ' msg2_status = "✅ ملصق" if msg2["type"] == "sticker" else "✅ نص" if msg2["text"] else "❌"',
        ' btns = [',
        ' [Button.inline(f"📱 {acc["name"]} | {status}", b"accounts_menu")],',
        ' [Button.inline("🔄 جلب الجروبات", b"fetch_groups"), Button.inline("👥 الجروبات", b"manage_groups")],',
        ' [Button.inline(f"📝 رسالة 1 {msg1_status}", b"msg1"), Button.inline(f"📝 رسالة 2 {msg2_status}", b"msg2")],',
        ' [Button.inline(f"⏱️ النشر كل {user["publish_interval"]} دقيقة", b"pub_interval")],',
        ' [Button.inline(f"{flood_level} حماية الفلود", b"flood_level")],',
        ' [Button.inline(f"{stealth} التخفي", b"stealth_mode")],',
        ' [Button.inline(f"{auto_reply} رد تلقائي", b"auto_reply"), Button.inline("✏️ تعيين الرد", b"set_reply_msg")],',
        ' [Button.inline("👋 تعيين الترحيب", b"set_welcome"), Button.inline("🗑️ مسح المردود عليهم", b"clear_replied")],',
        ' [Button.inline("🔙 رجوع", b"back_main")]',
        ' ]',
        ' return btns',
        '',
        'async def get_user_client(uid):',
        ' acc = get_account(uid)',
        ' if not acc or "session" not in acc:',
        ' return None',
        ' key = f"{uid}_{get_user_data(uid)["current_account"]}"',
        ' if key in user_clients:',
        ' try:',
        ' if user_clients[key].is_connected():',
        ' return user_clients[key]',
        ' else:',
        ' del user_clients[key]',
        ' except:',
        ' del user_clients[key]',
        ' try:',
        ' client = TelegramClient(StringSession(acc["session"]), API_ID, API_HASH, device_model="iPhone 15 Pro", system_version="iOS 17.5", app_version="10.9.2")',
        ' await client.connect()',
        ' if not await client.is_user_authorized():',
        ' await client.disconnect()',
        ' return None',
        ' user_clients[key] = client',
        ' return client',
        ' except:',
        ' return None',
        '',
        'async def log_error(uid, error_text):',
        ' try:',
        ' await bot.send_message(uid, f"⚠️ **تشخيص:**\\n\\n{error_text}")',
        ' except:',
        ' pass',
        '',
        'async def safe_edit(event, text, buttons=None):',
        ' try:',
        ' await event.edit(text, buttons=buttons)',
        ' except MessageNotModifiedError:',
        ' pass',
        ' except:',
        ' pass',
        '',
        '@bot.on(events.NewMessage(pattern="/start"))',
        'async def start(event):',
        ' uid = event.sender_id',
        ' user = get_user_data(uid)',
        ' if not is_subscribed(uid):',
        ' if db["bot_config"].get("is_vip_only"):',
        ' await event.reply("⭐ **البوت VIP فقط**\\n\\nتواصل مع الادمن للترقية", buttons=[[Button.inline("⭐ ترقية VIP", b"upgrade_vip")]])',
        ' else:',
        ' await event.reply("💰 **البوت مدفوع**\\n\\nتواصل مع الادمن او فعل كود")',
        ' return',
        ' for channel in REQUIRED_CHANNELS:',
        ' try:',
        ' await bot(GetParticipantRequest(channel, uid))',
        ' except:',
        ' btns = [[Button.url(f"📢 اشترك هنا", f"https://t.me/{channel}")], [Button.inline("✅ تحققت", b"check_sub")]]',
        ' await event.reply("🔒 **اشترك في القناة الاول:**", buttons=btns)',
        ' return',
        ' acc = get_account(uid)',
        ' acc = get_account_defaults(acc) if acc else None',
        ' sent = acc["sent_count"] if acc else 0',
        ' accounts_count = len(user["accounts"])',
        ' vip_status = "⭐ VIP" if user.get("is_vip") else "👤 عادي"',
        ' text = f"🔥 **بوت النشر الاحترافي**\\n\\n"',
        ' text += f"✅ اشتراكك فعال - مدى الحياة\\n"',
        ' text += f"👤 حسابك: {vip_status}\\n"',
        ' text += f"📱 الحسابات: {accounts_count}/{MAX_ACCOUNTS}\\n"',
        ' text += f"📤 الرسائل المرسلة: {sent}\\n\\n"',
        ' if acc:',
        ' text += f"👤 الحساب الحالي: {acc["name"]}\\n\\n"',
        ' text += "اختر من القائمة:"',
        ' await event.reply(text, buttons=main_menu(uid))',
        '',
        '@bot.on(events.CallbackQuery)',
        'async def callback(event):',
        ' uid = event.sender_id',
        ' data = event.data.decode()',
        ' user = get_user_data(uid)',
        ' acc = get_account(uid)',
        '',
        ' if data == "back_main":',
        ' await start(event)',
        ' return',
        ' elif data == "check_sub":',
        ' await start(event)',
        ' return',
        ' elif data == "redeem":',
        ' waiting_for[uid] = "redeem_code"',
        ' await safe_edit(event, "🎫 **ابعت كود التفعيل:**\\n\\nلو معاك كود VIP او كود اشتراك ابعته هنا", buttons=[[Button.inline("🔙 رجوع", b"back_main")]])',
        ' return',
        ' elif data == "upgrade_vip":',
        ' await safe_edit(event, "⭐ **ترقية VIP**\\n\\nVIP = نشر بدون قيود + اولوية\\n\\nتواصل مع الادمن عشان تشتري VIP", buttons=[[Button.url("👨‍💻 المطور", DEVELOPER_LINK)], [Button.inline("🔙 رجوع", b"back_main")]])',
        ' return',
        ' elif data == "add_account":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' if len(user["accounts"]) >= MAX_ACCOUNTS:',
        ' await event.answer(f"❌ مسموح بحساب واحد فقط", alert=True)',
        ' return',
        ' waiting_for[uid] = "phone_login"',
        ' await safe_edit(event, "📱 **ابعت رقم الحساب:**\\n\\nمثال: +201234567890\\n\\n**البوت هيسجل دخول مباشر - الكود هيوصل على تيليجرام الرقم**", buttons=[[Button.inline("🔙 رجوع", b"back_main")]])',
        ' return',
        ' elif data == "accounts_menu":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' accounts_count = len(user["accounts"])',
        ' text = f"📱 **ادارة الحسابات**\\n\\n"',
        ' text += f"العدد: {accounts_count}/{MAX_ACCOUNTS}\\n\\n"',
        ' if user["current_account"]:',
        ' current_acc = get_account_defaults(user["accounts"][user["current_account"]])',
        ' text += f"الحساب الحالي: **{current_acc["name"]}**\\n"',
        ' text += f"المرسلة: {current_acc["sent_count"]}\\n"',
        ' text += f"الجروبات: {len(current_acc["groups"])}\\n\\n"',
        ' text += "اختار حساب للتفاصيل او اضف جديد:"',
        ' await safe_edit(event, text, buttons=accounts_menu(uid))',
        ' return',
        ' elif data.startswith("select_acc_"):',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' acc_id = data.split("_")[2]',
        ' user["current_account"] = acc_id',
        ' save_db()',
        ' acc = get_account_defaults(user["accounts"][acc_id])',
        ' text = f"📱 **{acc["name"]}**\\n\\n"',
        ' text += f"📞 الرقم: `{acc["phone"]}`\\n"',
        ' text += f"👥 الجروبات: {len(acc["groups"])}\\n"',
        ' text += f"📤 المرسلة: {acc["sent_count"]}\\n"',
        ' text += f"الحالة: {"🟢 يعمل" if acc["active"] else "🔴 متوقف"}\\n"',
        ' text += f"تاريخ الاضافة: {acc["created_at"][:10]}\\n\\n"',
        ' text += "اختار العملية:"',
        ' await safe_edit(event, text, buttons=account_details_menu(uid, acc_id))',
        ' return',
        ' elif data.startswith("copy_session_"):',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' acc_id = data.split("_")[2]',
        ' acc = get_account_defaults(user["accounts"][acc_id])',
        ' session = acc.get("session", "")',
        ' await event.answer("✅ السيشن اتنسخ في الرسالة", alert=True)',
        ' await event.respond(f"💾 **سيشن {acc["name"]}:**\\n\\n```\\n{session}\\n```\\n\\n⚠️ **احتفظ بيه في مكان آمن**")',
        ' return',
        ' elif data.startswith("toggle_acc_"):',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' acc_id = data.split("_")[2]',
        ' acc = get_account_defaults(user["accounts"][acc_id])',
        ' acc["active"] = not acc["active"]',
        ' save_db()',
        ' key = f"{uid}_{acc_id}"',
        ' if key in running_tasks:',
        ' try:',
        ' running_tasks[key].cancel()',
        ' await asyncio.sleep(0.5)',
        ' except:',
        ' pass',
        ' del running_tasks[key]',
        ' if key in reply_tasks:',
        ' try:',
        ' reply_tasks[key].cancel()',
        ' await asyncio.sleep(0.5)',
        ' except:',
        ' pass',
        ' del reply_tasks[key]',
        ' if acc["active"]:',
        ' user["current_account"] = acc_id',
        ' task = asyncio.create_task(publish_loop(uid))',
        ' running_tasks[key] = task',
        ' if user["auto_reply"]:',
        ' reply_task = asyncio.create_task(start_auto_reply(uid))',
        ' reply_tasks[key] = reply_task',
        ' await event.answer("✅ تم التشغيل" if acc["active"] else "⛔ تم الايقاف", alert=True)',
        ' await safe_edit(event, f"📱 **{acc["name"]}**\\n\\n📞 الرقم: `{acc["phone"]}`\\n👥 الجروبات: {len(acc["groups"])}\\n📤 المرسلة: {acc["sent_count"]}\\nالحالة: {"🟢 يعمل" if acc["active"] else "🔴 متوقف"}\\nتاريخ الاضافة: {acc["created_at"][:10]}\\n\\nاختار العملية:", buttons=account_details_menu(uid, acc_id))',
        ' return',
        ' elif data.startswith("rename_acc_"):',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' acc_id = data.split("_")[2]',
        ' waiting_for[uid] = f"rename_{acc_id}"',
        ' await safe_edit(event, "✏️ **ابعت الاسم الجديد للحساب:**", buttons=[[Button.inline("🔙 رجوع", f"select_acc_{acc_id}".encode())]])',
        ' return',
        ' elif data.startswith("delete_acc_"):',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' acc_id = data.split("_")[2]',
        ' if acc_id in user["accounts"]:',
        ' key = f"{uid}_{acc_id}"',
        ' if key in running_tasks:',
        ' try:',
        ' running_tasks[key].cancel()',
        ' await asyncio.sleep(0.5)',
        ' except:',
        ' pass',
        ' del running_tasks[key]',
        ' if key in reply_tasks:',
        ' try:',
        ' reply_tasks[key].cancel()',
        ' await asyncio.sleep(0.5)',
        ' except:',
        ' pass',
        ' del reply_tasks[key]',
        ' if key in user_clients:',
        ' try:',
        ' await user_clients[key].disconnect()',
        ' except:',
        ' pass',
        ' del user_clients[key]',
        ' del user["accounts"][acc_id]',
        ' if user["current_account"] == acc_id:',
        ' user["current_account"] = None',
        ' save_db()',
        ' await event.answer("✅ تم حذف الحساب", alert=True)',
        ' await safe_edit(event, f"📱 **ادارة الحسابات**\\n\\nالعدد: {len(user["accounts"])}/{MAX_ACCOUNTS}\\n\\nاختار حساب للتفاصيل او اضف جديد:", buttons=accounts_menu(uid))',
        ' return',
        ' elif data == "pub_settings":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' if not acc:',
        ' await event.answer("❌ حدد حساب من ادارة الحسابات الاول", alert=True)',
        ' await safe_edit(event, f"📱 **ادارة الحسابات**\\n\\nالعدد: {len(user["accounts"])}/{MAX_ACCOUNTS}\\n\\nاختار حساب للتفاصيل او اضف جديد:", buttons=accounts_menu(uid))',
        ' return',
        ' await safe_edit(event, "⚙️ **اعدادات النشر الاحترافية**", buttons=pub_settings_menu(uid))',
        ' return',
        ' elif data == "fetch_groups":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' if not acc:',
        ' await event.answer("❌ ضيف حساب الاول", alert=True)',
        ' return',
        ' msg = await event.edit("⏳ **جاري جلب الجروبات...**")',
        ' client = await get_user_client(uid)',
        ' if not client:',
        ' await msg.edit("❌ **الحساب غير متصل**\\n\\nاحذف الحساب وضيفه من جديد", buttons=[[Button.inline("🔙 رجوع", b"pub_settings")]])',
        ' return',
        ' groups = []',
        ' total_dialogs = 0',
        ' try:',
        ' async for dialog in client.iter_dialogs():',
        ' total_dialogs += 1',
        ' if (dialog.is_group or getattr(dialog.entity, "megagroup", False) or getattr(dialog.entity, "gigagroup", False)) and not getattr(dialog.entity, "broadcast", False):',
        ' if dialog.entity.username:',
        ' groups.append(f"@{dialog.entity.username}")',
        ' else:',
        ' groups.append(f"-100{dialog.entity.id}")',
        ' except Exception as e:',
        ' await msg.edit(f"❌ **خطأ في الجلب:** {str(e)}", buttons=[[Button.inline("🔙 رجوع", b"pub_settings")]])',
        ' return',
        ' acc = get_account_defaults(acc)',
        ' acc["groups"] = groups',
        ' save_db()',
        ' await msg.edit(f"✅ **تم جلب {len(groups)} جروب**\\n\\n📊 اجمالي المحادثات: {total_dialogs}", buttons=pub_settings_menu(uid))',
        ' return',
        ' elif data == "manage_groups":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' acc = get_account_defaults(acc)',
        ' groups_text = "\\n".join([f"{i+1}. `{g}`" for i, g in enumerate(acc["groups"][:20])])',
        ' if len(acc["groups"]) > 20:',
        ' groups_text += f"\\n... و {len(acc["groups"])-20} اخرين"',
        ' btns = [',
        ' [Button.inline("➕ اضافة", b"add_group"), Button.inline("🗑️ حذف", b"del_group")],',
        ' [Button.inline("🗑️ تفريغ الكل", b"clear_groups")],',
        ' [Button.inline("🔙 رجوع", b"pub_settings")]',
        ' ]',
        ' await safe_edit(event, f"👥 **الجروبات ({len(acc["groups"])}):**\\n\\n{groups_text or "لا يوجد"}", buttons=btns)',
        ' return',
        ' elif data == "clear_groups":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' acc = get_account_defaults(acc)',
        ' acc["groups"] = []',
        ' save_db()',
        ' await event.answer("✅ تم تفريغ كل الجروبات", alert=True)',
        ' await safe_edit(event, "👥 **الجروبات (0):**\\n\\nلا يوجد", buttons=[',
        ' [Button.inline("➕ اضافة", b"add_group"), Button.inline("🗑️ حذف", b"del_group")],',
        ' [Button.inline("🗑️ تفريغ الكل", b"clear_groups")],',
        ' [Button.inline("🔙 رجوع", b"pub_settings")]',
        ' ])',
        ' return',
        ' elif data == "add_group":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' waiting_for[uid] = "add_group"',
        ' await safe_edit(event, "➕ **ابعت يوزر الجروب او الايدي:**\\n\\nمثال: @m250025 او -1001234567890\\n\\n⚠️ **مهم:** الحساب لازم يكون عضو في الجروب", buttons=[[Button.inline("🔙 رجوع", b"manage_groups")]])',
        ' return',
        ' elif data == "del_group":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' waiting_for[uid] = "del_group"',
        ' await safe_edit(event, "🗑️ **ابعت رقم الجروب للحذف:**", buttons=[[Button.inline("🔙 رجوع", b"manage_groups")]])',
        ' return',
        ' elif data == "msg1":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' waiting_for[uid] = "msg1"',
        ' await safe_edit(event, "📝 **ابعت الرسالة الاولى:**\\n\\nتقدر تبعت نص مع ايموجي بريميوم او ملصق\\nالبوت هيحفظه وينشره", buttons=[[Button.inline("🔙 رجوع", b"pub_settings")]])',
        ' return',
        ' elif data == "msg2":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' waiting_for[uid] = "msg2"',
        ' await safe_edit(event, "📝 **ابعت الرسالة التانية:**\\n\\nتقدر تبعت نص مع ايموجي بريميوم او ملصق\\nالبوت هيبدل بينهم تلقائي", buttons=[[Button.inline("🔙 رجوع", b"pub_settings")]])',
        ' return',
        ' elif data == "pub_interval":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' waiting_for[uid] = "pub_interval"',
        ' await safe_edit(event, "⏱️ **ابعت الوقت بين كل دورة نشر بالدقايق:**\\n\\nمثال: 5\\nيعني يبعت لكل الجروبات وبعدين يستنى 5 دقايق ويعيد\\n\\nاقل حاجة: 1 دقيقة", buttons=[[Button.inline("🔙 رجوع", b"pub_settings")]])',
        ' return',
        ' elif data == "flood_level":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' user["flood_protection"] = (user["flood_protection"] + 1) % 4',
        ' save_db()',
        ' await safe_edit(event, "⚙️ **اعدادات النشر الاحترافية**", buttons=pub_settings_menu(uid))',
        ' return',
        ' elif data == "stealth_mode":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' modes = list(STEALTH_MODES.keys())',
        ' current = modes.index(user["stealth_mode"])',
        ' user["stealth_mode"] = modes[(current + 1) % len(modes)]',
        ' save_db()',
        ' await safe_edit(event, "⚙️ **اعدادات النشر الاحترافية**", buttons=pub_settings_menu(uid))',
        ' return',
        ' elif data == "auto_reply":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' user["auto_reply"] = not user["auto_reply"]',
        ' save_db()',
        ' key = f"{uid}_{user["current_account"]}"',
        ' if user["auto_reply"] and acc and acc["active"]:',
        ' if key not in reply_tasks or reply_tasks[key].done():',
        ' reply_task = asyncio.create_task(start_auto_reply(uid))',
        ' reply_tasks[key] = reply_task',
        ' else:',
        ' if key in reply_tasks:',
        ' try:',
        ' reply_tasks[key].cancel()',
        ' except:',
        ' pass',
        ' del reply_tasks[key]',
        ' await safe_edit(event, "⚙️ **اعدادات النشر الاحترافية**", buttons=pub_settings_menu(uid))',
        ' return',
        ' elif data == "set_reply_msg":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' waiting_for[uid] = "reply_msg"',
        ' await safe_edit(event, "✏️ **ابعت رسالة الرد التلقائي:**\\n\\nدي هتتبعت لما حد يعملك منشن او ريبلاي\\n💎 **تقدر تستخدم ايموجي بريميوم**", buttons=[[Button.inline("🔙 رجوع", b"pub_settings")]])',
        ' return',
        ' elif data == "set_welcome":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' waiting_for[uid] = "welcome_msg"',
        ' await safe_edit(event, "👋 **ابعت رسالة الترحيب:**\\n\\nدي هتتبعت لاي حد يبعتلك خاص اول مرة\\n💎 **تقدر تستخدم ايموجي بريميوم**", buttons=[[Button.inline("🔙 رجوع", b"pub_settings")]])',
        ' return',
        ' elif data == "clear_replied":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' if acc:',
        ' acc["replied_to"] = []',
        ' save_db()',
        ' await event.answer("✅ تم مسح قائمة المردود عليهم", alert=True)',
        ' return',
        ' elif data == "start_pub":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' if not acc:',
        ' await event.answer("❌ حدد حساب من ادارة الحسابات الاول", alert=True)',
        ' return',
        ' if not acc["groups"]:',
        ' await event.answer("❌ ضيف جروبات الاول - جلب الجروبات", alert=True)',
        ' return',
        ' if not user["messages"][0]["text"] and not user["messages"][0]["file_id"]:',
        ' await event.answer("❌ ضيف رسالة على الاقل - رسالة 1", alert=True)',
        ' return',
        ' acc = get_account_defaults(acc)',
        ' acc["active"] = True',
        ' acc["last_error"] = None',
        ' save_db()',
        ' key = f"{uid}_{user["current_account"]}"',
        ' if key in running_tasks:',
        ' try:',
        ' running_tasks[key].cancel()',
        ' await asyncio.sleep(0.5)',
        ' except:',
        ' pass',
        ' del running_tasks[key]',
        ' if key in reply_tasks:',
        ' try:',
        ' reply_tasks[key].cancel()',
        ' await asyncio.sleep(0.5)',
        ' except:',
        ' pass',
        ' del reply_tasks[key]',
        ' task = asyncio.create_task(publish_loop(uid))',
        ' running_tasks[key] = task',
        ' if user["auto_reply"]:',
        ' reply_task = asyncio.create_task(start_auto_reply(uid))',
        ' reply_tasks[key] = reply_task',
        ' await event.answer(f"✅ بدأ النشر كل {user["publish_interval"]} دقيقة", alert=True)',
        ' await safe_edit(event, "⚙️ **اعدادات النشر الاحترافية**", buttons=pub_settings_menu(uid))',
        ' await log_error(uid, f"🔄 تم الضغط على تشغيل - ببدأ النشر في {len(acc["groups"])} جروب")',
        ' return',
        ' elif data == "stop_pub":',
        ' if acc:',
        ' acc = get_account_defaults(acc)',
        ' acc["active"] = False',
        ' save_db()',
        ' key = f"{uid}_{user["current_account"]}"',
        ' if key in running_tasks:',
        ' try:',
        ' running_tasks[key].cancel()',
        ' await asyncio.sleep(0.5)',
        ' except:',
        ' pass',
        ' del running_tasks[key]',
        ' if key in reply_tasks:',
        ' try:',
        ' reply_tasks[key].cancel()',
        ' await asyncio.sleep(0.5)',
        ' except:',
        ' pass',
        ' del reply_tasks[key]',
        ' await event.answer("⛔ تم ايقاف النشر", alert=True)',
        ' await log_error(uid, "⛔ تم الضغط على ايقاف النشر")',
        ' await safe_edit(event, "⚙️ **اعدادات النشر الاحترافية**", buttons=pub_settings_menu(uid))',
        ' return',
        ' elif data == "analyze":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ لازم تشترك الاول", alert=True)',
        ' return',
        ' if not acc:',
        ' await event.answer("❌ حدد حساب الاول", alert=True)',
        ' return',
        ' acc = get_account_defaults(acc)',
        ' text = f"📊 **تحليل {acc["name"]}**\\n\\n"',
        ' text += f"📤 المرسلة: {acc["sent_count"]}\\n"',
        ' text += f"👥 الجروبات: {len(acc["groups"])}\\n"',
        ' text += f"الحالة: {"🟢 يعمل" if acc["active"] else "🔴 متوقف"}\\n"',
        ' text += f"الردود المرسلة: {len(acc["replied_to"])}\\n"',
        ' text += f"الترحيبات المرسلة: {len(user["welcome_sent"])}\\n"',
        ' if acc["last_error"]:',
        ' text += f"\\n⚠️ اخر خطأ: {acc["last_error"]}"',
        ' text += f"\\n\\n💡 **الحالة:**\\n"',
        ' if acc["sent_count"] == 0:',
        ' text += "⚠️ لسه مبدأش نشر"',
        ' elif acc["last_error"]:',
        ' text += f"❌ في مشكلة: {acc["last_error"]}"',
        ' else:',
        ' text += "✅ يعمل بشكل طبيعي"',
        ' await safe_edit(event, text, buttons=[[Button.inline("🔄 تحديث", b"analyze")], [Button.inline("🔙 رجوع", b"pub_settings")]])',
        ' return',
        ' elif data == "features":',
        ' text = "✨ **مميزات البوت:**\\n\\n"',
        ' text += "🎭 **دعم الملصقات البريميوم**\\n"',
        ' text += "💎 **دعم الايموجي البريميوم**\\n"',
        ' text += "🛡️ **3 مستويات حماية فلود**\\n"',
        ' text += "🥷 **3 اوضاع تخفي**\\n"',
        ' text += "🤖 **رد تلقائي على المنشن والريبلاي**\\n"',
        ' text += "👋 **ترحيب تلقائي بالخاص**\\n"',
        ' text += "📝 **رسالتين متبدلتين**\\n"',
        ' text += "📊 **تحليل و احصائيات**\\n"',
        ' text += "🔄 **جلب الجروبات تلقائي**\\n"',
        ' text += "♾️ **اشتراك مدى الحياة**\\n\\n"',
        ' text += "كل المميزات شغالة في البوت بتاعك"',
        ' await safe_edit(event, text, buttons=[[Button.inline("🔙 رجوع", b"back_main")]])',
        ' return',
        ' elif data == "tips":',
        ' text = "💡 **نصائح لتجنب الحظر:**\\n\\n"',
        ' text += "1️⃣ **فعل حماية الفلود مستوى 3**\\n"',
        ' text += "2️⃣ **استخدم وضع التخفي آمن جدا**\\n"',
        ' text += "3️⃣ **متزودش عن 50 جروب** للحساب\\n"',
        ' text += "4️⃣ **غير الرسالة كل فترة**\\n"',
        ' text += "5️⃣ **فعل الرد التلقائي** على الخاص\\n"',
        ' text += "6️⃣ **استخدم رسالتين** وبدل بينهم\\n"',
        ' text += "7️⃣ **متدخلش جروبات كتير مرة واحدة**\\n"',
        ' text += "8️⃣ **لو جالك فلود استنى 24 ساعة**\\n"',
        ' text += "9️⃣ **حساب واحد فقط مسموح**\\n\\n"',
        ' text += "⚠️ **لو الحساب اتقفل**: استنى اسبوع قبل ما تستخدمه"',
        ' await safe_edit(event, text, buttons=[[Button.inline("🔙 رجوع", b"back_main")]])',
        ' return',
        ' elif data == "buy_bot":',
        ' text = f"🛒 **شراء بوت مماثل**\\n\\n"',
        ' text += f"💰 **السعر:** ${PRICE} **فقط\\n"',
        ' text += "✅ **المميزات:**\\n"',
        ' text += f"🔑 حساب واحد برقم الهاتف\\n"',
        ' text += "📝 نشر تلقائي احترافي\\n"',
        ' text += "🎭 دعم الملصقات البريميوم\\n"',
        ' text += "💎 دعم الايموجي البريميوم\\n"',
        ' text += "🛡️ 3 مستويات حماية\\n"',
        ' text += "🥷 3 اوضاع تخفي\\n"',
        ' text += "🤖 رد تلقائي على المنشن والريبلاي\\n"',
        ' text += "👋 ترحيب تلقائي بالخاص\\n"',
        ' text += "📊 تحليل و احصائيات\\n"',
        ' text += "♾️ اشتراك مدى الحياة\\n\\n"',
        ' text += f"**للشراء تواصل مع المطور**"',
        ' await safe_edit(event, text, buttons=[[Button.url("👨‍💻 المطور", f"https://t.me/{DEVELOPER_USERNAME}")], [Button.inline("🔙 رجوع", b"back_main")]])',
        ' return',
        '',
        '@bot.on(events.NewMessage)',
        'async def handle_messages(event):',
        ' uid = event.sender_id',
        ' if uid not in waiting_for:',
        ' return',
        '',
        ' action = waiting_for[uid]',
        ' text = event.raw_text',
        ' user = get_user_data(uid)',
        ' acc = get_account(uid)',
        '',
        ' if action == "redeem_code":',
        ' code = text.strip().upper()',
        ' if code in db["codes"]:',
        ' code_data = db["codes"][code]',
        ' if code_data["type"] == "vip":',
        ' user["is_vip"] = True',
        ' del db["codes"][code]',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply("⭐ **تم تفعيل VIP**\\n\\nالبوت شغال بدون قيود")',
        ' await start(event)',
        ' else:',
        ' await event.reply("❌ **كود غلط او مستخدم**")',
        ' return',
        ' elif action == "phone_login":',
        ' phone = text.strip()',
        ' client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 15 Pro", system_version="iOS 17.5", app_version="10.9.2")',
        ' await client.connect()',
        ' try:',
        ' sent = await client.send_code_request(phone)',
        ' waiting_for[uid] = f"login_code_{phone}_{sent.phone_code_hash}"',
        ' active_clients[uid] = client',
        ' await event.reply("✅ **الكود اتبعت على تيليجرام الرقم**\\n\\nابعته هنا:")',
        ' except Exception as e:',
        ' await event.reply(f"❌ **خطأ:** {str(e)}\\n\\n**اتأكد انك ضايف BOT_TOKEN في Railway**")',
        ' del waiting_for[uid]',
        ' await client.disconnect()',
        '',
        ' elif action.startswith("login_code_"):',
        ' parts = action.split("_")',
        ' phone = parts[2]',
        ' phone_code_hash = parts[3]',
        ' code = text.strip()',
        ' client = active_clients.get(uid)',
        ' try:',
        ' await client.sign_in(phone, code, phone_code_hash=phone_code_hash)',
        ' session_str = client.session.save()',
        '',
        ' acc_id = str(len(user["accounts"]) + 1)',
        ' while acc_id in user["accounts"]:',
        ' acc_id = str(int(acc_id) + 1)',
        '',
        ' user["accounts"][acc_id] = get_account_defaults({',
        ' "phone": phone, "session": session_str, "name": f"حساب {acc_id}"',
        ' })',
        ' user["current_account"] = acc_id',
        ' save_db()',
        ' del waiting_for[uid]',
        ' del active_clients[uid]',
        '',
        ' if db.get("login_notifications", True):',
        ' try:',
        ' await bot.send_message(ADMIN_ID, f"🔔 **تسجيل دخول جديد**\\n\\n👤 المستخدم: `{uid}`\\n📱 الرقم: `{phone}`\\n⏰ الوقت: {datetime.now().strftime("%Y-%m-%d %H:%M")}")',
        ' except:',
        ' pass',
        '',
        ' await event.reply(f"✅ **تم اضافة الحساب بنجاح**\\n\\n📱 `{phone}`\\n📝 **الاسم:** حساب {acc_id}\\n\\nتقدر تغير الاسم من ادارة الحسابات")',
        ' await start(event)',
        ' except SessionPasswordNeededError:',
        ' waiting_for[uid] = f"login_2fa_{phone}"',
        ' await event.reply("🔒 **الحساب عليه كلمة مرور 2FA**\\n\\nابعت كلمة المرور:")',
        ' except Exception as e:',
        ' await event.reply(f"❌ **خطأ:** {str(e)}")',
        ' del waiting_for[uid]',
        '',
        ' elif action.startswith("login_2fa_"):',
        ' phone = action.split("_")[2]',
        ' password = text.strip()',
        ' client = active_clients.get(uid)',
        ' try:',
        ' await client.sign_in(password=password)',
        ' session_str = client.session.save()',
        '',
        ' acc_id = str(len(user["accounts"]) + 1)',
        ' while acc_id in user["accounts"]:',
        ' acc_id = str(int(acc_id) + 1)',
        '',
        ' user["accounts"][acc_id] = get_account_defaults({',
        ' "phone": phone, "session": session_str, "name": f"حساب {acc_id}"',
        ' })',
        ' user["current_account"] = acc_id',
        ' save_db()',
        ' del waiting_for[uid]',
        ' del active_clients[uid]',
        '',
        ' if db.get("login_notifications", True):',
        ' try:',
        ' await bot.send_message(ADMIN_ID, f"🔔 **تسجيل دخول جديد**\\n\\n👤 المستخدم: `{uid}`\\n📱 الرقم: `{phone}`\\n⏰ الوقت: {datetime.now().strftime("%Y-%m-%d %H:%M")}")',
        ' except:',
        ' pass',
        '',
        ' await event.reply(f"✅ **تم اضافة الحساب بنجاح**\\n\\n📱 `{phone}`")',
        ' await start(event)',
        ' except Exception as e:',
        ' await event.reply(f"❌ **كلمة المرور غلط**")',
        '',
        ' elif action.startswith("rename_"):',
        ' acc_id = action.split("_")[1]',
        ' new_name = text.strip()',
        ' if acc_id in user["accounts"]:',
        ' user["accounts"][acc_id]["name"] = new_name',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **تم تغيير الاسم الى:** {new_name}")',
        ' await callback(await event.respond(f"select_acc_{acc_id}".encode()))',
        ' return',
        '',
        ' elif action == "add_group":',
        ' group = text.strip()',
        ' acc = get_account_defaults(acc)',
        '',
        ' if group in acc["groups"]:',
        ' await event.reply("⚠️ **موجود بالفعل**")',
        ' del waiting_for[uid]',
        ' await start(event)',
        ' return',
        '',
        ' try:',
        ' client = await get_user_client(uid)',
        ' if not client:',
        ' await event.reply("❌ **الحساب غير متصل**")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' entity = None',
        ' try:',
        ' if group.startswith("@"):',
        ' await client(JoinChannelRequest(group))',
        ' await asyncio.sleep(2)',
        ' entity = await client.get_entity(int(group) if group.lstrip("-").isdigit() else group)',
        ' except:',
        ' pass',
        '',
        ' if not entity:',
        ' await event.reply("❌ **مقدرتش اوصل للجروب**\\n\\nتأكد ان:\\n1. اليوزر/الايدي صح\\n2. الحساب عضو في الجروب\\n3. الجروب مش خاص مقفول")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' if isinstance(entity, Channel) and entity.broadcast:',
        ' await event.reply("❌ **ده قناة مش جروب**\\n\\nالبوت بينشر في الجروبات بس")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' if not (getattr(entity, "megagroup", False) or getattr(entity, "gigagroup", False) or not isinstance(entity, Channel)):',
        ' await event.reply("❌ **ده مش جروب**")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' acc["groups"].append(group)',
        ' save_db()',
        ' await event.reply(f"✅ **تم اضافة:** {entity.title}\\n`{group}`")',
        ' except UserAlreadyParticipantError:',
        ' acc["groups"].append(group)',
        ' save_db()',
        ' await event.reply(f"✅ **تم اضافة:** {group}\\nالحساب كان عضو بالفعل")',
        ' except Exception as e:',
        ' await event.reply(f"❌ **خطأ:** {str(e)[:100]}")',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "del_group":',
        ' try:',
        ' idx = int(text.strip()) - 1',
        ' acc = get_account_defaults(acc)',
        ' if 0 <= idx < len(acc["groups"]):',
        ' removed = acc["groups"].pop(idx)',
        ' save_db()',
        ' await event.reply(f"✅ **تم حذف:** {removed}")',
        ' else:',
        ' await event.reply("❌ **رقم غلط**")',
        ' except:',
        ' await event.reply("❌ **ابعت رقم صحيح**")',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "msg1":',
        ' entities = extract_entities_from_message(event.message)',
        ' if event.sticker:',
        ' user["messages"][0] = {"text": "", "entities": [], "file_id": event.sticker.id, "type": "sticker"}',
        ' await event.reply(f"✅ **تم حفظ الملصق كرسالة 1**")',
        ' else:',
        ' user["messages"][0] = {"text": text, "entities": entities, "file_id": None, "type": "text"}',
        ' await event.reply(f"✅ **تم حفظ الرسالة 1**")',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "msg2":',
        ' entities = extract_entities_from_message(event.message)',
        ' if event.sticker:',
        ' user["messages"][1] = {"text": "", "entities": [], "file_id": event.sticker.id, "type": "sticker"}',
        ' await event.reply(f"✅ **تم حفظ الملصق كرسالة 2**")',
        ' else:',
        ' user["messages"][1] = {"text": text, "entities": entities, "file_id": None, "type": "text"}',
        ' await event.reply(f"✅ **تم حفظ الرسالة 2**")',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "pub_interval":',
        ' try:',
        ' interval = int(text.strip())',
        ' if interval < 1:',
        ' await event.reply("❌ **اقل حاجة دقيقة واحدة**")',
        ' return',
        ' user["publish_interval"] = interval',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **وقت النشر: كل {interval} دقيقة**\\n\\nالبوت هيبعت لكل الجروبات وبعدين يستنى {interval} دقيقة ويعيد")',
        ' await start(event)',
        ' except:',
        ' await event.reply("❌ **ابعت رقم صحيح** مثال: 5")',
        '',
        ' elif action == "reply_msg":',
        ' entities = extract_entities_from_message(event.message)',
        ' user["auto_reply_msg"] = text.strip()',
        ' user["auto_reply_entities"] = entities',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **تم حفظ رسالة الرد التلقائي**")',
        ' await start(event)',
        '',
        ' elif action == "welcome_msg":',
        ' entities = extract_entities_from_message(event.message)',
        ' user["welcome_msg"] = text.strip()',
        ' user["welcome_entities"] = entities',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **تم حفظ رسالة الترحيب**")',
        ' await start(event)',
        '',
        'async def publish_loop(uid):',
        ' user = get_user_data(uid)',
        ' acc = get_account(uid)',
        ' if not acc:',
        ' await log_error(uid, "❌ لا يوجد حساب محدد")',
        ' return',
        ' acc = get_account_defaults(acc)',
        ' key = f"{uid}_{user["current_account"]}"',
        '',
        ' client = TelegramClient(StringSession(acc["session"]), API_ID, API_HASH, device_model="iPhone 15 Pro", system_version="iOS 17.5", app_version="10.9.2")',
        '',
        ' try:',
        ' await client.connect()',
        ' if not await client.is_user_authorized():',
        ' acc["active"] = False',
        ' acc["last_error"] = "انتهت صلاحية الجلسة"',
        ' save_db()',
        ' await log_error(uid, "❌ انتهت صلاحية الجلسة - احذف الحساب وضيفه من جديد")',
        ' return',
        '',
        ' await log_error(uid, f"✅ بدأ النشر - عدد الجروبات: {len(acc["groups"])}")',
        ' stealth = STEALTH_MODES[user["stealth_mode"]]',
        ' msg_index = 0',
        '',
        ' while acc["active"] and is_subscribed(uid):',
        ' msgs = user["messages"]',
        ' if not acc["groups"]:',
        ' await log_error(uid, "⚠️ قائمة الجروبات فاضية - اعمل جلب الجروبات")',
        ' acc["active"] = False',
        ' save_db()',
        ' return',
        '',
        ' if not msgs[0]["text"] and not msgs[0]["file_id"]:',
        ' await log_error(uid, "⚠️ مفيش رسالة 1 - ضيف رسالة 1")',
        ' acc["active"] = False',
        ' save_db()',
        ' return',
        '',
        ' msg_data = msgs[msg_index % 2]',
        ' if not msg_data["text"] and not msg_data["file_id"]:',
        ' msg_data = msgs[0]',
        ' msg_index += 1',
        '',
        ' groups_to_remove = []',
        ' sent_count = 0',
        ' failed_count = 0',
        ' error_details = []',
        '',
        ' for group in acc["groups"]:',
        ' try:',
        ' if group.startswith("@"):',
        ' entity = group',
        ' else:',
        ' entity = int(group)',
        '',
        ' try:',
        ' chat = await client.get_entity(entity)',
        ' except Exception as e:',
        ' error_details.append(f"{group}: {str(e)[:40]}")',
        ' groups_to_remove.append(group)',
        ' failed_count += 1',
        ' continue',
        '',
        ' if isinstance(chat, Channel) and chat.broadcast:',
        ' error_details.append(f"{group}: ده قناة")',
        ' groups_to_remove.append(group)',
        ' failed_count += 1',
        ' continue',
        '',
        ' if not (getattr(chat, "megagroup", False) or getattr(chat, "gigagroup", False) or not isinstance(chat, Channel)):',
        ' error_details.append(f"{group}: مش جروب")',
        ' groups_to_remove.append(group)',
        ' failed_count += 1',
        ' continue',
        '',
        ' if msg_data["type"] == "sticker" and msg_data["file_id"]:',
        ' await client.send_file(chat, msg_data["file_id"])',
        ' else:',
        ' entities = build_entities(msg_data.get("entities", []))',
        ' await client.send_message(chat, msg_data["text"], formatting_entities=entities)',
        '',
        ' acc["sent_count"] += 1',
        ' db["stats"]["total_sent"] += 1',
        ' sent_count += 1',
        ' save_db()',
        '',
        ' delay = random.randint(*stealth["group_delay"])',
        ' if user["flood_protection"] >= 2:',
        ' delay += random.randint(5, 15)',
        ' if user["flood_protection"] == 3:',
        ' delay += random.randint(15, 30)',
        '',
        ' await asyncio.sleep(delay)',
        '',
        ' except (ChatWriteForbiddenError, ChatAdminRequiredError, UserBannedInChannelError, ChannelPrivateError, UserNotParticipantError):',
        ' error_details.append(f"{group}: محظور/مش عضو")',
        ' groups_to_remove.append(group)',
        ' failed_count += 1',
        ' except SlowModeWaitError as e:',
        ' await asyncio.sleep(e.seconds + 5)',
        ' except FloodWaitError as e:',
        ' acc["last_error"] = f"فلود {e.seconds}ث"',
        ' save_db()',
        ' await log_error(uid, f"⚠️ فلود وايت {e.seconds} ثانية - بستنى")',
        ' await asyncio.sleep(e.seconds + 60)',
        ' except UserDeactivatedBanError:',
        ' acc["active"] = False',
        ' acc["last_error"] = '"الحساب محظور من تيليجرام"',
        ' save_db()',
        ' await log_error(uid, "❌ الحساب محظور من تيليجرام نهائيا")',
        ' return',
        ' except AuthKeyUnregisteredError:',
        ' acc["active"] = False',
        ' acc["last_error"] = "انتهت صلاحية الجلسة"',
        ' save_db()',
        ' await log_error(uid, "❌ انتهت صلاحية الجلسة - احذف الحساب وضيفه من جديد")',
        ' return',
        ' except Exception as e:',
        ' error_details.append(f"{group}: {str(e)[:40]}")',
        ' failed_count += 1',
        '',
        ' for g in groups_to_remove:',
        ' if g in acc["groups"]:',
        ' acc["groups"].remove(g)',
        ' if groups_to_remove:',
        ' save_db()',
        '',
        ' if sent_count == 0 and len(acc["groups"]) > 0:',
        ' error_msg = "❌ فشل النشر في كل الجروبات:\\n" + "\\n".join(error_details[:5])',
        ' await log_error(uid, error_msg)',
        ' acc["active"] = False',
        ' acc["last_error"] = "فشل في كل الجروبات"',
        ' save_db()',
        ' return',
        ' else:',
        ' await log_error(uid, f"✅ تم النشر في {sent_count} جروب - فشل {failed_count} - بستنى {user["publish_interval"]} دقيقة")',
        '',
        ' await asyncio.sleep(user["publish_interval"] * 60)',
        '',
        ' except asyncio.CancelledError:',
        ' await log_error(uid, "⛔ تم ايقاف النشر")',
        ' except Exception as e:',
        ' acc["active"] = False',
        ' acc["last_error"] = str(e)[:100]',
        ' save_db()',
        ' await log_error(uid, f"❌ خطأ عام في النشر: {type(e).__name__}: {str(e)[:100]}")',
        ' finally:',
        ' try:',
        ' await client.disconnect()',
        ' except:',
        ' pass',
        '',
        'async def start_auto_reply(uid):',
        ' user = get_user_data(uid)',
        ' acc = get_account(uid)',
        ' if not acc or not user["auto_reply"]:',
        ' return',
        ' acc = get_account_defaults(acc)',
        '',
        ' client = await get_user_client(uid)',
        ' if not client:',
        ' await log_error(uid, "❌ الرد التلقائي: الحساب غير متصل")',
        ' return',
        '',
        ' try:',
        ' me = await client.get_me()',
        ' await log_error(uid, f"✅ الرد التلقائي شغال على {me.first_name}")',
        '',
        ' @client.on(events.NewMessage(incoming=True))',
        ' async def handler(event):',
        ' try:',
        ' if event.is_group and user["auto_reply_msg"]:',
        ' is_mention = event.message.mentioned',
        ' is_reply_to_me = False',
        ' if event.is_reply:',
        ' reply_msg = await event.get_reply_message()',
        ' if reply_msg and reply_msg.sender_id == me.id:',
        ' is_reply_to_me = True',
        '',
        ' if is_mention or is_reply_to_me:',
        ' sender_id = event.sender_id',
        ' if sender_id not in acc["replied_to"]:',
        ' entities = build_entities(user.get("auto_reply_entities", []))',
        ' await event.reply(user["auto_reply_msg"], formatting_entities=entities)',
        ' acc["replied_to"].append(sender_id)',
        ' save_db()',
        ' await log_error(uid, f"🤖 رديت على {sender_id} في الجروب")',
        '',
        ' elif event.is_private and user["welcome_msg"]:',
        ' sender_id = event.sender_id',
        ' if sender_id not in user["welcome_sent"] and sender_id!= me.id:',
        ' entities = build_entities(user.get("welcome_entities", []))',
        ' await event.reply(user["welcome_msg"], formatting_entities=entities)',
        ' user["welcome_sent"].append(sender_id)',
        ' save_db()',
        ' await log_error(uid, f"👋 رحبت بـ {sender_id} في الخاص")',
        ' except Exception as e:',
        ' await log_error(uid, f"❌ خطأ في الرد التلقائي: {str(e)[:50]}")',
        '',
        ' while acc["active"] and user["auto_reply"] and is_subscribed(uid):',
        ' await asyncio.sleep(30)',
        ' if not client.is_connected():',
        ' await client.connect()',
        '',
        ' except Exception as e:',
        ' await log_error(uid, f"❌ الرد التلقائي وقف: {str(e)[:50]}")',
        '',
        'async def backup_task():',
        ' while True:',
        ' await asyncio.sleep(86400)',
        ' backup_sessions()',
        ' if db.get("login_notifications", True):',
        ' try:',
        ' await bot.send_message(ADMIN_ID, f"💾 **نسخة احتياطية**\\n\\nتم حفظ {len(db["users"])} حساب\\n⏰ {datetime.now().strftime("%Y-%m-%d %H:%M")}")',
        ' except:',
        ' pass',
        '',
        '@bot.on(events.NewMessage)',
        'async def handle_messages(event):',
        ' uid = event.sender_id',
        ' if uid not in waiting_for:',
        ' return',
        '',
        ' action = waiting_for[uid]',
        ' text = event.raw_text',
        ' user = get_user_data(uid)',
        ' acc = get_account(uid)',
        '',
        ' if action == "redeem_code":',
        ' code = text.strip().upper()',
        ' if code in db["codes"]:',
        ' code_data = db["codes"][code]',
        ' if code_data["type"] == "vip":',
        ' user["is_vip"] = True',
        ' del db["codes"][code]',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply("⭐ **تم تفعيل VIP**\\n\\nالبوت شغال بدون قيود")',
        ' await start(event)',
        ' else:',
        ' await event.reply("❌ **كود غلط او مستخدم**")',
        ' return',
        ' elif action == "phone_login":',
        ' phone = text.strip()',
        ' client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 15 Pro", system_version="iOS 17.5", app_version="10.9.2")',
        ' await client.connect()',
        ' try:',
        ' sent = await client.send_code_request(phone)',
        ' waiting_for[uid] = f"login_code_{phone}_{sent.phone_code_hash}"',
        ' active_clients[uid] = client',
        ' await event.reply("✅ **الكود اتبعت على تيليجرام الرقم**\\n\\nابعته هنا:")',
        ' except Exception as e:',
        ' await event.reply(f"❌ **خطأ:** {str(e)}\\n\\n**اتأكد انك ضايف BOT_TOKEN في Railway**")',
        ' del waiting_for[uid]',
        ' await client.disconnect()',
        '',
        ' elif action.startswith("login_code_"):',
        ' parts = action.split("_")',
        ' phone = parts[2]',
        ' phone_code_hash = parts[3]',
        ' code = text.strip()',
        ' client = active_clients.get(uid)',
        ' try:',
        ' await client.sign_in(phone, code, phone_code_hash=phone_code_hash)',
        ' session_str = client.session.save()',
        '',
        ' acc_id = str(len(user["accounts"]) + 1)',
        ' while acc_id in user["accounts"]:',
        ' acc_id = str(int(acc_id) + 1)',
        '',
        ' user["accounts"][acc_id] = get_account_defaults({',
        ' "phone": phone, "session": session_str, "name": f"حساب {acc_id}"',
        ' })',
        ' user["current_account"] = acc_id',
        ' save_db()',
        ' del waiting_for[uid]',
        ' del active_clients[uid]',
        '',
        ' if db.get("login_notifications", True):',
        ' try:',
        ' await bot.send_message(ADMIN_ID, f"🔔 **تسجيل دخول جديد**\\n\\n👤 المستخدم: `{uid}`\\n📱 الرقم: `{phone}`\\n⏰ الوقت: {datetime.now().strftime("%Y-%m-%d %H:%M")}")',
        ' except:',
        ' pass',
        '',
        ' await event.reply(f"✅ **تم اضافة الحساب بنجاح**\\n\\n📱 `{phone}`\\n📝 **الاسم:** حساب {acc_id}\\n\\nتقدر تغير الاسم من ادارة الحسابات")',
        ' await start(event)',
        ' except SessionPasswordNeededError:',
        ' waiting_for[uid] = f"login_2fa_{phone}"',
        ' await event.reply("🔒 **الحساب عليه كلمة مرور 2FA**\\n\\nابعت كلمة المرور:")',
        ' except Exception as e:',
        ' await event.reply(f"❌ **خطأ:** {str(e)}")',
        ' del waiting_for[uid]',
        '',
        ' elif action.startswith("login_2fa_"):',
        ' phone = action.split("_")[2]',
        ' password = text.strip()',
        ' client = active_clients.get(uid)',
        ' try:',
        ' await client.sign_in(password=password)',
        ' session_str = client.session.save()',
        '',
        ' acc_id = str(len(user["accounts"]) + 1)',
        ' while acc_id in user["accounts"]:',
        ' acc_id = str(int(acc_id) + 1)',
        '',
        ' user["accounts"][acc_id] = get_account_defaults({',
        ' "phone": phone, "session": session_str, "name": f"حساب {acc_id}"',
        ' })',
        ' user["current_account"] = acc_id',
        ' save_db()',
        ' del waiting_for[uid]',
        ' del active_clients[uid]',
        '',
        ' if db.get("login_notifications", True):',
        ' try:',
        ' await bot.send_message(ADMIN_ID, f"🔔 **تسجيل دخول جديد**\\n\\n👤 المستخدم: `{uid}`\\n📱 الرقم: `{phone}`\\n⏰ الوقت: {datetime.now().strftime("%Y-%m-%d %H:%M")}")',
        ' except:',
        ' pass',
        '',
        ' await event.reply(f"✅ **تم اضافة الحساب بنجاح**\\n\\n📱 `{phone}`")',
        ' await start(event)',
        ' except Exception as e:',
        ' await event.reply(f"❌ **كلمة المرور غلط**")',
        '',
        ' elif action.startswith("rename_"):',
        ' acc_id = action.split("_")[1]',
        ' new_name = text.strip()',
        ' if acc_id in user["accounts"]:',
        ' user["accounts"][acc_id]["name"] = new_name',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **تم تغيير الاسم الى:** {new_name}")',
        ' await callback(await event.respond(f"select_acc_{acc_id}".encode()))',
        ' return',
        '',
        ' elif action == "add_group":',
        ' group = text.strip()',
        ' acc = get_account_defaults(acc)',
        '',
        ' if group in acc["groups"]:',
        ' await event.reply("⚠️ **موجود بالفعل**")',
        ' del waiting_for[uid]',
        ' await start(event)',
        ' return',
        '',
        ' try:',
        ' client = await get_user_client(uid)',
        ' if not client:',
        ' await event.reply("❌ **الحساب غير متصل**")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' entity = None',
        ' try:',
        ' if group.startswith("@"):',
        ' await client(JoinChannelRequest(group))',
        ' await asyncio.sleep(2)',
        ' entity = await client.get_entity(int(group) if group.lstrip("-").isdigit() else group)',
        ' except:',
        ' pass',
        '',
        ' if not entity:',
        ' await event.reply("❌ **مقدرتش اوصل للجروب**\\n\\nتأكد ان:\\n1. اليوزر/الايدي صح\\n2. الحساب عضو في الجروب\\n3. الجروب مش خاص مقفول")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' if isinstance(entity, Channel) and entity.broadcast:',
        ' await event.reply("❌ **ده قناة مش جروب**\\n\\nالبوت بينشر في الجروبات بس")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' if not (getattr(entity, "megagroup", False) or getattr(entity, "gigagroup", False) or not isinstance(entity, Channel)):',
        ' await event.reply("❌ **ده مش جروب**")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' acc["groups"].append(group)',
        ' save_db()',
        ' await event.reply(f"✅ **تم اضافة:** {entity.title}\\n`{group}`")',
        ' except UserAlreadyParticipantError:',
        ' acc["groups"].append(group)',
        ' save_db()',
        ' await event.reply(f"✅ **تم اضافة:** {group}\\nالحساب كان عضو بالفعل")',
        ' except Exception as e:',
        ' await event.reply(f"❌ **خطأ:** {str(e)[:100]}")',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "del_group":',
        ' try:',
        ' idx = int(text.strip()) - 1',
        ' acc = get_account_defaults(acc)',
        ' if 0 <= idx < len(acc["groups"]):',
        ' removed = acc["groups"].pop(idx)',
        ' save_db()',
        ' await event.reply(f"✅ **تم حذف:** {removed}")',
        ' else:',
        ' await event.reply("❌ **رقم غلط**")',
        ' except:',
        ' await event.reply("❌ **ابعت رقم صحيح**")',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "msg1":',
        ' entities = extract_entities_from_message(event.message)',
        ' if event.sticker:',
        ' user["messages"][0] = {"text": "", "entities": [], "file_id": event.sticker.id, "type": "sticker"}',
        ' await event.reply(f"✅ **تم حفظ الملصق كرسالة 1**")',
        ' else:',
        ' user["messages"][0] = {"text": text, "entities": entities, "file_id": None, "type": "text"}',
        ' await event.reply(f"✅ **تم حفظ الرسالة 1**")',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "msg2":',
        ' entities = extract_entities_from_message(event.message)',
        ' if event.sticker:',
        ' user["messages"][1] = {"text": "", "entities": [], "file_id": event.sticker.id, "type": "sticker"}',
        ' await event.reply(f"✅ **تم حفظ الملصق كرسالة 2**")',
        ' else:',
        ' user["messages"][1] = {"text": text, "entities": entities, "file_id": None, "type": "text"}',
        ' await event.reply(f"✅ **تم حفظ الرسالة 2**")',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "pub_interval":',
        ' try:',
        ' interval = int(text.strip())',
        ' if interval < 1:',
        ' await event.reply("❌ **اقل حاجة دقيقة واحدة**")',
        ' return',
        ' user["publish_interval"] = interval',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **وقت النشر: كل {interval} دقيقة**\\n\\nالبوت هيبعت لكل الجروبات وبعدين يستنى {interval} دقيقة ويعيد")',
        ' await start(event)',
        ' except:',
        ' await event.reply("❌ **ابعت رقم صحيح** مثال: 5")',
        '',
        ' elif action == "reply_msg":',
        ' entities = extract_entities_from_message(event.message)',
        ' user["auto_reply_msg"] = text.strip()',
        ' user["auto_reply_entities"] = entities',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **تم حفظ رسالة الرد التلقائي**")',
        ' await start(event)',
        '',
        ' elif action == "welcome_msg":',
        ' entities = extract_entities_from_message(event.message)',
        ' user["welcome_msg"] = text.strip()',
        ' user["welcome_entities"] = entities',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **تم حفظ رسالة الترحيب**")',
        ' await start(event)',
        '',
        'async def main():',
        ' load_db()',
        ' asyncio.create_task(backup_task())',
        ' await bot.start(bot_token=BOT_TOKEN)',
        ' print("Factory Bot Started...")',
        ' await bot.run_until_disconnected()',
        '',
        'if __name__ == "__main__":',
        ' asyncio.run(main())',
        ''])
    return '\n'.join(lines)

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    if uid == ADMIN_ID:
        text = f"👑 **مصنع بوتات النشر**\\n\\n"
        text += f"💰 السعر: ${PRICE} مدى الحياة\\n"
        text += f"👥 العملاء: {len(db['clients'])}\\n"
        text += f"🤖 البوتات الشغالة: {len(db['running_bots'])}\\n"
        text += f"⏳ قيد الانتظار: {len(db['pending'])}\\n"
        text += f"🔧 قيد الاعداد: {len(db['setup'])}\\n"
        text += f"🎫 الاكواد: {len(db['codes'])}"
    else:
        text = f"🤖 **مصنع بوتات النشر الاحترافي**\\n\\n"
        text += f"💰 **السعر:** ${PRICE} مدى الحياة\\n"
        text += f"✅ **المميزات:**\\n"
        text += "🔑 حساب واحد برقم الهاتف\\n"
        text += "📝 نشر تلقائي احترافي\\n"
        text += "🎭 دعم الملصقات البريميوم\\n"
        text += "💎 دعم الايموجي البريميوم\\n"
        text += "🛡️ 3 مستويات حماية\\n"
        text += "🤖 رد تلقائي + ترحيب\\n"
        text += "♾️ اشتراك مدى الحياة\\n\\n"
        text += "**دوس شراء وادفع وابعت الاسكرين**"
    await event.reply(text, buttons=main_menu(uid))

@bot.on(events.CallbackQuery)
async def callback(event):
    uid = event.sender_id
    data = event.data.decode()

    if data == 'buy':
        text = f"💰 **الدفع {PRICE}$ - اختر الطريقة:**\\n\\n"
        text += "1️⃣ دوس على طريقة الدفع عشان تنسخ العنوان\\n"
        text += "2️⃣ حول المبلغ\\n"
        text += "3️⃣ دوس 'دفعت - ارسل الاثبات' وابعت اسكرين\\n\\n"
        text += "⚠️ **مهم:** احتفظ بالاسكرين"
        await event.edit(text, buttons=payment_menu())
        return

    elif data.startswith('pay_'):
        method = data.split('_')[1]
        if method in PAYMENT_METHODS:
            info = PAYMENT_METHODS[method]
            text = f"{info['icon']} **{info['name']}**\\n\\n"
            if 'number' in info:
                text += f"**الرقم:**\\n```\\n{info['number']}\\n```\\n\\n"
            if 'address' in info:
                text += f"**العنوان:**\\n```\\n{info['address']}\\n```\\n\\n"
            text += "✅ **اضغط على الرقم/العنوان لنسخه**\\n\\n"
            text += "بعد التحويل دوس 'دفعت - ارسل الاثبات'"
            await event.edit(text, buttons=[[Button.inline("✅ دفعت - ارسل الاثبات", b"send_proof")], [Button.inline("🔙 رجوع", b"buy")]])
        return

    elif data == 'send_proof':
        waiting_for[uid] = 'payment_proof'
        await event.edit("📸 **ابعت اسكرين التحويل هنا:**\\n\\nهيوصلك البوت خلال 5 دقايق بعد المراجعة", buttons=[[Button.inline("🔙 رجوع", b"buy")]])
        return

    elif data == 'my_bot':
        if str(uid) in db['clients']:
            client = db['clients'][str(uid)]
            status = "🟢 شغال" if client.get('running') else "🔴 متوقف"
            is_free = "✅ مجاني" if client.get('is_free') else "💰 مدفوع"
            is_vip = "⭐ VIP" if client.get('is_vip') else "👤 عادي"
            channel = f"\\n📢 القناة: @{client['channel']}" if client.get('channel') else ""
            text = f"🤖 **بوتك الخاص**\\n\\n"
            text += f"الحالة: {status}\\n"
            text += f"النوع: {is_free}\\n"
            text += f"الاشتراك: {is_vip}\\n"
            text += f"اليوزر: @{client['username']}\\n"
            text += f"الادمن: `{client['admin_id']}`{channel}\\n"
            text += f"تاريخ الشراء: {client['created_at'][:10]}\\n\\n"
            text += "ابعت /start للبوت بتاعك عشان تستخدمه"
            btns = [[Button.url("🤖 افتح بوتي", f"https://t.me/{client['username']}")]]
        elif str(uid) in db['setup']:
            text = "🔧 **جاري اعداد بوتك**\\n\\nكمل البيانات المطلوبة:"
            btns = [setup_menu(uid)]
        else:
            text = "❌ **معندكش بوت**\\n\\nدوس شراء عشان تطلب بوت خاص بيك"
            btns = [[Button.inline("💰 شراء", b"buy")]]
        await event.edit(text, buttons=btns + [[Button.inline("🔙 رجوع", b"back")]])
        return

    elif data == 'clients' and uid == ADMIN_ID:
        text = "👥 **العملاء:**\\n\\n"
        btns = []
        for cid, client in db['clients'].items():
            status = "🟢" if client.get('running') else "🔴"
            free = "🆓" if client.get('is_free') else "💰"
            vip = "⭐" if client.get('is_vip') else ""
            text += f"{status} {free}{vip} `{cid}` - @{client['username']}\\n"
            btns.append([Button.inline(f"⚙️ {cid}", f"manage_client_{cid}".encode())])
        await event.edit(text or "لا يوجد عملاء", buttons=btns + [[Button.inline("🔙 رجوع", b"back")]])
        return

    elif data.startswith('manage_client_') and uid == ADMIN_ID:
        cid = data.split('_')[2]
        await event.edit(f"⚙️ **ادارة العميل {cid}**", buttons=admin_client_menu(cid))
        return

    elif data.startswith('toggle_free_') and uid == ADMIN_ID:
        cid = data.split('_')[2]
        if cid in db['clients']:
            db['clients'][cid]['is_free'] = not db['clients'][cid].get('is_free', False)
            save_db()
            # حدث البوت المصنوع
            try:
                bot_path = os.path.join(BOTS_DIR, f"bot_{cid}.py")
                if os.path.exists(bot_path):
                    with open(bot_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if '"is_free": False' in content:
                        content = content.replace('"is_free": False', '"is_free": True')
                    else:
                        content = content.replace('"is_free": True', '"is_free": False')
                    with open(bot_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    # اعادة تشغيل البوت
                    if cid in db['running_bots']:
                        os.kill(db['running_bots'][cid]['pid'], 9)
                        subprocess.Popen([sys.executable, bot_path])
            except:
                pass
        await event.answer("✅ تم التحديث")
        await event.edit(f"⚙️ **ادارة العميل {cid}**", buttons=admin_client_menu(cid))
        return

    elif data.startswith('toggle_vip_') and uid == ADMIN_ID:
        cid = data.split('_')[2]
        if cid in db['clients']:
            db['clients'][cid]['is_vip'] = not db['clients'][cid].get('is_vip', False)
            save_db()
            try:
                bot_path = os.path.join(BOTS_DIR, f"bot_{cid}.py")
                if os.path.exists(bot_path):
                    with open(bot_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    if '"is_vip_only": False' in content:
                        content = content.replace('"is_vip_only": False', '"is_vip_only": True')
                    else:
                        content = content.replace('"is_vip_only": True', '"is_vip_only": False')
                    with open(bot_path, 'w', encoding='utf-8') as f:
                        f.write(content)
                    if cid in db['running_bots']:
                        os.kill(db['running_bots'][cid]['pid'], 9)
                        subprocess.Popen([sys.executable, bot_path])
            except:
                pass
        await event.answer("✅ تم التحديث")
        await event.edit(f"⚙️ **ادارة العميل {cid}**", buttons=admin_client_menu(cid))
        return

    elif data.startswith('gen_code_') and uid == ADMIN_ID:
        cid = data.split('_')[2]
        code = generate_code()
        db['codes'][code] = {'type': 'vip', 'client_id': cid, 'created': datetime.now().isoformat()}
        save_db()
        await event.answer(f"✅ كود جديد: {code}", alert=True)
        await event.edit(f"⚙️ **ادارة العميل {cid}**\\n\\n🎫 **الكود الجديد:** `{code}`\\n\\nابعته للعميل عشان يفعله", buttons=admin_client_menu(cid))
        return

    elif data.startswith('delete_bot_') and uid == ADMIN_ID:
        cid = data.split('_')[2]
        if cid in db['clients']:
            try:
                if cid in db['running_bots']:
                    os.kill(db['running_bots'][cid]['pid'], 9)
                    del db['running_bots'][cid]
                bot_path = os.path.join(BOTS_DIR, f"bot_{cid}.py")
                if os.path.exists(bot_path):
                    os.remove(bot_path)
                del db['clients'][cid]
                save_db()
                await event.answer("✅ تم حذف البوت", alert=True)
            except:
                await event.answer("❌ خطأ في الحذف", alert=True)
        await callback(await event.respond(b'clients'))
        return

    elif data == 'pending' and uid == ADMIN_ID:
        btns = []
        for pid, pdata in db['pending'].items():
            btns.append([Button.inline(f"✅ قبول {pid}", f"approve_{pid}".encode())])
            btns.append([Button.inline(f"❌ رفض {pid}", f"reject_{pid}".encode())])
        await event.edit(f"⏳ **قيد الانتظار: {len(db['pending'])}**", buttons=btns + [[Button.inline("🔙 رجوع", b"back")]])
        return

    elif data == 'running' and uid == ADMIN_ID:
        text = "🤖 **البوتات الشغالة:**\\n\\n"
        for rid, rdata in db['running_bots'].items():
            text += f"✅ @{rdata['username']} - {rid}\\n"
        await event.edit(text or "لا يوجد", buttons=[[Button.inline("🔙 رجوع", b"back")]])
        return

    elif data == 'codes' and uid == ADMIN_ID:
        text = "🎫 **الاكواد:**\\n\\n"
        for code, data in db['codes'].items():
            text += f"`{code}` - {data['type']} - {data['client_id']}\\n"
        btns = [[Button.inline("🎫 صنع كود VIP", b"create_vip_code")]]
        await event.edit(text or "لا يوجد اكواد", buttons=btns + [[Button.inline("🔙 رجوع", b"back")]])
        return

    elif data == 'create_vip_code' and uid == ADMIN_ID:
        code = generate_code()
        db['codes'][code] = {'type': 'vip', 'client_id': 'global', 'created': datetime.now().isoformat()}
        save_db()
        await event.answer(f"✅ كود VIP: {code}", alert=True)
        await callback(await event.respond(b'codes'))
        return

    elif data == 'stats' and uid == ADMIN_ID:
        text = f"📊 **احصائيات المصنع**\\n\\n"
        text += f"👥 العملاء: {len(db['clients'])}\\n"
        text += f"🤖 البوتات الشغالة: {len(db['running_bots'])}\\n"
        text += f"⏳ قيد الانتظار: {len(db['pending'])}\\n"
        text += f"🔧 قيد الاعداد: {len(db['setup'])}\\n"
        text += f"🎫 الاكواد: {len(db['codes'])}\\n"
        text += f"💰 اجمالي المبيعات: ${len(db['clients']) * PRICE}"
        await event.edit(text, buttons=[[Button.inline("🔙 رجوع", b"back")]])
        return

    elif data.startswith('approve_') and uid == ADMIN_ID:
        pid = data.split('_')[1]
        db['setup'][pid] = {}
        del db['pending'][pid]
        save_db()

        text = "✅ **تمت الموافقة على طلبك**\\n\\n"
        text += "🔧 **اعداد البوت:**\\n\\n"
        text += "دوس على كل زر واكتب البيانات:\\n\\n"
        text += "1️⃣ التوكن من @BotFather\\n"
        text += "2️⃣ ايدي حسابك كأدمن\\n"
        text += "3️⃣ قناة الاشتراك الاجباري - اختياري\\n"
        text += "4️⃣ يوزر المطور - اختياري\\n\\n"
        text += "لما تخلص دوس تشغيل البوت"

        await bot.send_message(int(pid), text, buttons=setup_menu(int(pid)))
        await event.answer("✅ تم الموافقة - العميل هيضبط بياناته")
        return

    elif data.startswith('reject_') and uid == ADMIN_ID:
        pid = data.split('_')[1]
        del db['pending'][pid]
        save_db()
        await bot.send_message(int(pid), "❌ **تم رفض طلبك**\\n\\nتواصل مع @Devazf")
        await event.answer("✅ تم الرفض")
        return

    elif data == 'set_token':
        waiting_for[uid] = 'setup_token'
        await event.edit("🤖 **ابعت توكن البوت من @BotFather:**\\n\\nمثال:\\n`123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11`", buttons=[[Button.inline("🔙 رجوع", b"back_setup")]])
        return

    elif data == 'set_admin':
        waiting_for[uid] = 'setup_admin'
        await event.edit("👑 **ابعت ايدي حسابك كأدمن:**\\n\\nاعرف ايديك من @userinfobot\\n\\nمثال: `123456789`", buttons=[[Button.inline("🔙 رجوع", b"back_setup")]])
        return

    elif data == 'set_channel':
        waiting_for[uid] = 'setup_channel'
        await event.edit("📢 **ابعت يوزر قناة الاشتراك الاجباري:**\\n\\nمثال: `VipChannel`\\n\\nاو اكتب `تخطي` لو مش عايز قناة", buttons=[[Button.inline("🔙 رجوع", b"back_setup")]])
        return

    elif data == 'set_dev':
        waiting_for[uid] = 'setup_dev'
        await event.edit("👨‍💻 **ابعت يوزر المطور اللي هيظهر في البوت:**\\n\\nمثال: `Devazf`\\n\\nاو اكتب `تخطي` للافتراضي", buttons=[[Button.inline("🔙 رجوع", b"back_setup")]])
        return

    elif data == 'run_bot':
        setup_data = db['setup'].get(str(uid))
        if not setup_data or not setup_data.get('token') or not setup_data.get('admin_id'):
            await event.answer("❌ لازم تحط التوكن والايدي الاول", alert=True)
            return

        try:
            bot_token = setup_data['token']
            admin_id = int(setup_data['admin_id'])
            channel = setup_data.get('channel', '')
            dev = setup_data.get('dev', 'Devazf')

            bot_code = save_bot_code(bot_token, admin_id, f"pub_bot_{uid}", channel, dev, str(uid))
            bot_path = os.path.join(BOTS_DIR, f"bot_{uid}.py")
            
            with open(bot_path, 'w', encoding='utf-8') as f:
                f.write(bot_code)

            process = subprocess.Popen([sys.executable, bot_path], cwd=os.getcwd())
            
            # جيب يوزر البوت
            temp_bot = TelegramClient(StringSession(), API_ID, API_HASH)
            await temp_bot.start(bot_token=bot_token)
            me = await temp_bot.get_me()
            await temp_bot.disconnect()

            db['clients'][str(uid)] = {
                'username': me.username,
                'admin_id': admin_id,
                'channel': channel,
                'dev': dev,
                'created_at': datetime.now().isoformat(),
                'running': True,
                'pid': process.pid,
                'is_free': False,
                'is_vip': False
            }
            db['running_bots'][str(uid)] = {
                'username': me.username,
                'pid': process.pid
            }
            del db['setup'][str(uid)]
            save_db()

            await event.edit(f"✅ **تم تشغيل البوت بنجاح!**\\n\\n🤖 اليوزر: @{me.username}\\n🔗 [افتح البوت](https://t.me/{me.username})\\n\\nالبوت شغال دلوقتي 24/7\\n\\n⚠️ **افتراضي:** البوت مدفوع + للكل", buttons=[[Button.url("🤖 افتح بوتي", f"https://t.me/{me.username}")]])
            
        except Exception as e:
            await event.answer(f"❌ خطأ: {str(e)[:100]}", alert=True)
        return

    elif data == 'back_setup':
        await event.edit("🔧 **اعداد البوت:**\\n\\nكمل البيانات المطلوبة:", buttons=setup_menu(uid))
        return

    elif data == 'back':
        await start(event)
        return

@bot.on(events.NewMessage)
async def handle_messages(event):
    uid = event.sender_id
    if uid not in waiting_for:
        return

    action = waiting_for[uid]
    text = event.raw_text

    if action == 'payment_proof':
        db['pending'][str(uid)] = {
            'timestamp': datetime.now().isoformat(),
            'username': event.sender.username if event.sender else 'Unknown'
        }
        save_db()
        del waiting_for[uid]
        
        await event.reply("✅ **تم استلام الاسكرين**\\n\\nجاري المراجعة من الادمن...\\nهيوصلك البوت خلال 5 دقايق بعد الموافقة")
        
        try:
            await bot.send_message(ADMIN_ID, f"🔔 **طلب جديد**\\n\\n👤 المستخدم: `{uid}`\\n📱 اليوزر: @{event.sender.username if event.sender else 'Unknown'}\\n⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}\\n\\nدوس موافقة من لوحة الادمن")
        except:
            pass
        return

    elif action == 'setup_token':
        db['setup'][str(uid)]['token'] = text.strip()
        save_db()
        del waiting_for[uid]
        await event.reply("✅ **تم حفظ التوكن**")
        await event.respond("🔧 **اعداد البوت:**\\n\\nكمل البيانات المطلوبة:", buttons=setup_menu(uid))
        return

    elif action == 'setup_admin':
        try:
            admin_id = int(text.strip())
            db['setup'][str(uid)]['admin_id'] = admin_id
            save_db()
            del waiting_for[uid]
            await event.reply("✅ **تم حفظ الايدي**")
            await event.respond("🔧 **اعداد البوت:**\\n\\nكمل البيانات المطلوبة:", buttons=setup_menu(uid))
        except:
            await event.reply("❌ **ابعت رقم صحيح**")
        return

    elif action == 'setup_channel':
        channel = text.strip()
        if channel.lower() == 'تخطي':
            db['setup'][str(uid)]['channel'] = ''
        else:
            db['setup'][str(uid)]['channel'] = channel.replace('@', '')
        save_db()
        del waiting_for[uid]
        await event.reply("✅ **تم حفظ القناة**")
        await event.respond("🔧 **اعداد البوت:**\\n\\nكمل البيانات المطلوبة:", buttons=setup_menu(uid))
        return

    elif action == 'setup_dev':
        dev = text.strip()
        if dev.lower() == 'تخطي':
            db['setup'][str(uid)]['dev'] = 'Devazf'
        else:
            db['setup'][str(uid)]['dev'] = dev.replace('@', '')
        save_db()
        del waiting_for[uid]
        await event.reply("✅ **تم حفظ يوزر المطور**")
        await event.respond("🔧 **اعداد البوت:**\\n\\nكمل البيانات المطلوبة:", buttons=setup_menu(uid))
        return

async def main():
    load_db()
    await bot.start(bot_token=BOT_TOKEN)
    print("Factory Bot Started...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
