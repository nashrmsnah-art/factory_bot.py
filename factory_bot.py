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
        ' "active": False, "groups": [], "name": "New Account",',
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
        ' [Button.inline("📱 Add Account", b"add_account")],',
        ' [Button.inline("📱 Manage Accounts", b"accounts_menu")],',
        ' [Button.inline("⚙️ Publishing Settings", b"pub_settings"), Button.inline("📊 Analytics", b"analyze")],',
        ' [Button.inline("🔄 Start", b"start_pub"), Button.inline("⛔ Stop", b"stop_pub")],',
        ' [Button.inline("🎫 Redeem Code", b"redeem"), Button.inline("⭐ Upgrade VIP", b"upgrade_vip")],',
        ' [Button.inline("✨ Features", b"features"), Button.inline("💡 Protection Tips", b"tips")],',
        ' [Button.url("👨‍💻 Developer", DEVELOPER_LINK)]',
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
        ' btns.append([Button.inline("➕ Add New Account", b"add_account")])',
        ' btns.append([Button.inline("🔙 Back", b"back_main")])',
        ' return btns',
        '',
        'def account_details_menu(uid, acc_id):',
        ' acc = get_user_data(uid)["accounts"][acc_id]',
        ' acc = get_account_defaults(acc)',
        ' status = "🟢 Running" if acc["active"] else "🔴 Stopped"',
        ' btns = [',
        ' [Button.inline(f"{status}", f"toggle_acc_{acc_id}".encode())],',
        ' [Button.inline("✏️ Rename", f"rename_acc_{acc_id}".encode())],',
        ' [Button.inline("👥 Groups", f"groups_acc_{acc_id}".encode())],',
        ' [Button.inline("💾 Copy Session", f"copy_session_{acc_id}".encode())],',
        ' [Button.inline("🗑️ Delete Account", f"delete_acc_{acc_id}".encode())],',
        ' [Button.inline("🔙 Back", b"accounts_menu")]',
        ' ]',
        ' return btns',
        '',
        'def pub_settings_menu(uid):',
        ' user = get_user_data(uid)',
        ' acc = get_account(uid)',
        ' if not acc:',
        ' return [[Button.inline("❌ No account selected", b"accounts_menu")], [Button.inline("🔙 Back", b"back_main")]]',
        ' acc = get_account_defaults(acc)',
        ' status = "🟢 Running" if acc["active"] else "🔴 Stopped"',
        ' flood_level = ["❌", "🟡", "🟢", "🛡️"][user["flood_protection"]]',
        ' stealth = STEALTH_MODES[user["stealth_mode"]]["name"]',
        ' auto_reply = "✅" if user["auto_reply"] else "❌"',
        ' msg1 = user["messages"][0]',
        ' msg2 = user["messages"][1]',
        ' msg1_status = "✅ Sticker" if msg1["type"] == "sticker" else "✅ Text" if msg1["text"] else "❌"',
        ' msg2_status = "✅ Sticker" if msg2["type"] == "sticker" else "✅ Text" if msg2["text"] else "❌"',
        ' btns = [',
        ' [Button.inline(f"📱 {acc["name"]} | {status}", b"accounts_menu")],',
        ' [Button.inline("🔄 Fetch Groups", b"fetch_groups"), Button.inline("👥 Groups", b"manage_groups")],',
        ' [Button.inline(f"📝 Message 1 {msg1_status}", b"msg1"), Button.inline(f"📝 Message 2 {msg2_status}", b"msg2")],',
        ' [Button.inline(f"⏱️ Publish every {user["publish_interval"]} min", b"pub_interval")],',
        ' [Button.inline(f"{flood_level} Flood Protection", b"flood_level")],',
        ' [Button.inline(f"{stealth} Stealth", b"stealth_mode")],',
        ' [Button.inline(f"{auto_reply} Auto Reply", b"auto_reply"), Button.inline("✏️ Set Reply", b"set_reply_msg")],',
        ' [Button.inline("👋 Set Welcome", b"set_welcome"), Button.inline("🗑️ Clear Replied", b"clear_replied")],',
        ' [Button.inline("🔙 Back", b"back_main")]',
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
        ' await bot.send_message(uid, f"⚠️ **Diagnosis:**\\n\\n{error_text}")',
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
        ' await event.reply("⭐ **Bot is VIP only**\\n\\nContact admin to upgrade", buttons=[[Button.inline("⭐ Upgrade VIP", b"upgrade_vip")]])',
        ' else:',
        ' await event.reply("💰 **Bot is paid**\\n\\nContact admin or redeem a code")',
        ' return',
        ' for channel in REQUIRED_CHANNELS:',
        ' try:',
        ' await bot(GetParticipantRequest(channel, uid))',
        ' except:',
        ' btns = [[Button.url(f"📢 Join Here", f"https://t.me/{channel}")], [Button.inline("✅ I Joined", b"check_sub")]]',
        ' await event.reply("🔒 **Join the channel first:**", buttons=btns)',
        ' return',
        ' acc = get_account(uid)',
        ' acc = get_account_defaults(acc) if acc else None',
        ' sent = acc["sent_count"] if acc else 0',
        ' accounts_count = len(user["accounts"])',
        ' vip_status = "⭐ VIP" if user.get("is_vip") else "👤 Regular"',
        ' text = f"🔥 **Publishing Bot Pro**\\n\\n"',
        ' text += f"✅ Your subscription: Lifetime\\n"',
        ' text += f"👤 Account: {vip_status}\\n"',
        ' text += f"📱 Accounts: {accounts_count}/{MAX_ACCOUNTS}\\n"',
        ' text += f"📤 Messages sent: {sent}\\n\\n"',
        ' if acc:',
        ' text += f"👤 Current account: {acc["name"]}\\n\\n"',
        ' text += "Choose from menu:"',
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
        ' await safe_edit(event, "🎫 **Send activation code:**\\n\\nIf you have a VIP or subscription code, send it here", buttons=[[Button.inline("🔙 Back", b"back_main")]])',
        ' return',
        ' elif data == "upgrade_vip":',
        ' await safe_edit(event, "⭐ **VIP Upgrade**\\n\\nVIP = Unlimited publishing + Priority\\n\\nContact admin to buy VIP", buttons=[[Button.url("👨‍💻 Developer", DEVELOPER_LINK)], [Button.inline("🔙 Back", b"back_main")]])',
        ' return',
        ' elif data == "add_account":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' if len(user["accounts"]) >= MAX_ACCOUNTS:',
        ' await event.answer("❌ Only 1 account allowed", alert=True)',
        ' return',
        ' waiting_for[uid] = "phone_login"',
        ' await safe_edit(event, "📱 **Send account number:**\\n\\nExample: +201234567890\\n\\n**Bot will login directly - code arrives on the number Telegram**", buttons=[[Button.inline("🔙 Back", b"back_main")]])',
        ' return',
        ' elif data == "accounts_menu":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' accounts_count = len(user["accounts"])',
        ' text = f"📱 **Manage Accounts**\\n\\n"',
        ' text += f"Count: {accounts_count}/{MAX_ACCOUNTS}\\n\\n"',
        ' if user["current_account"]:',
        ' current_acc = get_account_defaults(user["accounts"][user["current_account"]])',
        ' text += f"Current account: **{current_acc["name"]}**\\n"',
        ' text += f"Sent: {current_acc["sent_count"]}\\n"',
        ' text += f"Groups: {len(current_acc["groups"])}\\n\\n"',
        ' text += "Select account for details or add new:"',
        ' await safe_edit(event, text, buttons=accounts_menu(uid))',
        ' return',
        ' elif data.startswith("select_acc_"):',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' acc_id = data.split("_")[2]',
        ' user["current_account"] = acc_id',
        ' save_db()',
        ' acc = get_account_defaults(user["accounts"][acc_id])',
        ' text = f"📱 **{acc["name"]}**\\n\\n"',
        ' text += f"📞 Number: `{acc["phone"]}`\\n"',
        ' text += f"👥 Groups: {len(acc["groups"])}\\n"',
        ' text += f"📤 Sent: {acc["sent_count"]}\\n"',
        ' text += f"Status: {"🟢 Running" if acc["active"] else "🔴 Stopped"}\\n"',
        ' text += f"Added: {acc["created_at"][:10]}\\n\\n"',
        ' text += "Choose action:"',
        ' await safe_edit(event, text, buttons=account_details_menu(uid, acc_id))',
        ' return',
        ' elif data.startswith("copy_session_"):',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' acc_id = data.split("_")[2]',
        ' acc = get_account_defaults(user["accounts"][acc_id])',
        ' session = acc.get("session", "")',
        ' await event.answer("✅ Session copied in message", alert=True)',
        ' await event.respond(f"💾 **Session {acc["name"]}:**\\n\\n```\\n{session}\\n```\\n\\n⚠️ **Keep it safe**")',
        ' return',
        ' elif data.startswith("toggle_acc_"):',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
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
        ' await event.answer("✅ Started" if acc["active"] else "⛔ Stopped", alert=True)',
        ' await safe_edit(event, f"📱 **{acc["name"]}**\\n\\n📞 Number: `{acc["phone"]}`\\n👥 Groups: {len(acc["groups"])}\\n📤 Sent: {acc["sent_count"]}\\nStatus: {"🟢 Running" if acc["active"] else "🔴 Stopped"}\\nAdded: {acc["created_at"][:10]}\\n\\nChoose action:", buttons=account_details_menu(uid, acc_id))',
        ' return',
        ' elif data.startswith("rename_acc_"):',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' acc_id = data.split("_")[2]',
        ' waiting_for[uid] = f"rename_{acc_id}"',
        ' await safe_edit(event, "✏️ **Send new account name:**", buttons=[[Button.inline("🔙 Back", f"select_acc_{acc_id}".encode())]])',
        ' return',
        ' elif data.startswith("delete_acc_"):',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
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
        ' await event.answer("✅ Account deleted", alert=True)',
        ' await safe_edit(event, f"📱 **Manage Accounts**\\n\\nCount: {len(user["accounts"])}/{MAX_ACCOUNTS}\\n\\nSelect account for details or add new:", buttons=accounts_menu(uid))',
        ' return',
        ' elif data == "pub_settings":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' if not acc:',
        ' await event.answer("❌ Select account from Manage Accounts first", alert=True)',
        ' await safe_edit(event, f"📱 **Manage Accounts**\\n\\nCount: {len(user["accounts"])}/{MAX_ACCOUNTS}\\n\\nSelect account for details or add new:", buttons=accounts_menu(uid))',
        ' return',
        ' await safe_edit(event, "⚙️ **Publishing Settings**", buttons=pub_settings_menu(uid))',
        ' return',
        ' elif data == "fetch_groups":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' if not acc:',
        ' await event.answer("❌ Add account first", alert=True)',
        ' return',
        ' msg = await event.edit("⏳ **Fetching groups...**")',
        ' client = await get_user_client(uid)',
        ' if not client:',
        ' await msg.edit("❌ **Account not connected**\\n\\nDelete account and add again", buttons=[[Button.inline("🔙 Back", b"pub_settings")]])',
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
        ' await msg.edit(f"❌ **Fetch error:** {str(e)}", buttons=[[Button.inline("🔙 Back", b"pub_settings")]])',
        ' return',
        ' acc = get_account_defaults(acc)',
        ' acc["groups"] = groups',
        ' save_db()',
        ' await msg.edit(f"✅ **Fetched {len(groups)} groups**\\n\\n📊 Total dialogs: {total_dialogs}", buttons=pub_settings_menu(uid))',
        ' return',
        ' elif data == "manage_groups":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' acc = get_account_defaults(acc)',
        ' groups_text = "\\n".join([f"{i+1}. `{g}`" for i, g in enumerate(acc["groups"][:20])])',
        ' if len(acc["groups"]) > 20:',
        ' groups_text += f"\\n... and {len(acc["groups"])-20} more"',
        ' btns = [',
        ' [Button.inline("➕ Add", b"add_group"), Button.inline("🗑️ Delete", b"del_group")],',
        ' [Button.inline("🗑️ Clear All", b"clear_groups")],',
        ' [Button.inline("🔙 Back", b"pub_settings")]',
        ' ]',
        ' await safe_edit(event, f"👥 **Groups ({len(acc["groups"])}):**\\n\\n{groups_text or "None"}", buttons=btns)',
        ' return',
        ' elif data == "clear_groups":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' acc = get_account_defaults(acc)',
        ' acc["groups"] = []',
        ' save_db()',
        ' await event.answer("✅ Cleared all groups", alert=True)',
        ' await safe_edit(event, "👥 **Groups (0):**\\n\\nNone", buttons=[',
        ' [Button.inline("➕ Add", b"add_group"), Button.inline("🗑️ Delete", b"del_group")],',
        ' [Button.inline("🗑️ Clear All", b"clear_groups")],',
        ' [Button.inline("🔙 Back", b"pub_settings")]',
        ' ])',
        ' return',
        ' elif data == "add_group":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' waiting_for[uid] = "add_group"',
        ' await safe_edit(event, "➕ **Send group username or ID:**\\n\\nExample: @m250025 or -1001234567890\\n\\n⚠️ **Important:** Account must be member of the group", buttons=[[Button.inline("🔙 Back", b"manage_groups")]])',
        ' return',
        ' elif data == "del_group":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' waiting_for[uid] = "del_group"',
        ' await safe_edit(event, "🗑️ **Send group number to delete:**", buttons=[[Button.inline("🔙 Back", b"manage_groups")]])',
        ' return',
        ' elif data == "msg1":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' waiting_for[uid] = "msg1"',
        ' await safe_edit(event, "📝 **Send first message:**\\n\\nYou can send text with premium emoji or sticker\\nBot will save and publish it", buttons=[[Button.inline("🔙 Back", b"pub_settings")]])',
        ' return',
        ' elif data == "msg2":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' waiting_for[uid] = "msg2"',
        ' await safe_edit(event, "📝 **Send second message:**\\n\\nYou can send text with premium emoji or sticker\\nBot will alternate between them", buttons=[[Button.inline("🔙 Back", b"pub_settings")]])',
        ' return',
        ' elif data == "pub_interval":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' waiting_for[uid] = "pub_interval"',
        ' await safe_edit(event, "⏱️ **Send time between publish cycles in minutes:**\\n\\nExample: 5\\nMeans bot sends to all groups then waits 5 minutes and repeats\\n\\nMinimum: 1 minute", buttons=[[Button.inline("🔙 Back", b"pub_settings")]])',
        ' return',
        ' elif data == "flood_level":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' user["flood_protection"] = (user["flood_protection"] + 1) % 4',
        ' save_db()',
        ' await safe_edit(event, "⚙️ **Publishing Settings**", buttons=pub_settings_menu(uid))',
        ' return',
        ' elif data == "stealth_mode":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' modes = list(STEALTH_MODES.keys())',
        ' current = modes.index(user["stealth_mode"])',
        ' user["stealth_mode"] = modes[(current + 1) % len(modes)]',
        ' save_db()',
        ' await safe_edit(event, "⚙️ **Publishing Settings**", buttons=pub_settings_menu(uid))',
        ' return',
        ' elif data == "auto_reply":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' user["auto_reply"] = not user["auto_reply"]',
        ' save_db()',
        ' key = f"{uid}_{user["current_account"]}"',
        ' if user["auto_reply"] and acc["active"]:',
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
        ' await safe_edit(event, "⚙️ **Publishing Settings**", buttons=pub_settings_menu(uid))',
        ' return',
        ' elif data == "set_reply_msg":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' waiting_for[uid] = "reply_msg"',
        ' await safe_edit(event, "✏️ **Send auto reply message:**\\n\\nThis will be sent when someone mentions or replies to you\\n💎 **You can use premium emoji**", buttons=[[Button.inline("🔙 Back", b"pub_settings")]])',
        ' return',
        ' elif data == "set_welcome":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' waiting_for[uid] = "welcome_msg"',
        ' await safe_edit(event, "👋 **Send welcome message:**\\n\\nThis will be sent to anyone who messages you first time\\n💎 **You can use premium emoji**", buttons=[[Button.inline("🔙 Back", b"pub_settings")]])',
        ' return',
        ' elif data == "clear_replied":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' if acc:',
        ' acc["replied_to"] = []',
        ' save_db()',
        ' await event.answer("✅ Cleared replied list", alert=True)',
        ' return',
        ' elif data == "start_pub":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' if not acc:',
        ' await event.answer("❌ Select account from Manage Accounts first", alert=True)',
        ' return',
        ' if not acc["groups"]:',
        ' await event.answer("❌ Add groups first - Fetch Groups", alert=True)',
        ' return',
        ' if not user["messages"][0]["text"] and not user["messages"][0]["file_id"]:',
        ' await event.answer("❌ Add at least one message - Message 1", alert=True)',
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
        ' await event.answer(f"✅ Publishing started every {user["publish_interval"]} minutes", alert=True)',
        ' await safe_edit(event, "⚙️ **Publishing Settings**", buttons=pub_settings_menu(uid))',
        ' await log_error(uid, f"🔄 Started publishing in {len(acc["groups"])} groups")',
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
        ' await event.answer("⛔ Publishing stopped", alert=True)',
        ' await log_error(uid, "⛔ Publishing stopped")',
        ' await safe_edit(event, "⚙️ **Publishing Settings**", buttons=pub_settings_menu(uid))',
        ' return',
        ' elif data == "analyze":',
        ' if not is_subscribed(uid):',
        ' await event.answer("❌ You must subscribe first", alert=True)',
        ' return',
        ' if not acc:',
        ' await event.answer("❌ Select account first", alert=True)',
        ' return',
        ' acc = get_account_defaults(acc)',
        ' text = f"📊 **Analysis {acc["name"]}**\\n\\n"',
        ' text += f"📤 Sent: {acc["sent_count"]}\\n"',
        ' text += f"👥 Groups: {len(acc["groups"])}\\n"',
        ' text += f"Status: {"🟢 Running" if acc["active"] else "🔴 Stopped"}\\n"',
        ' text += f"Auto replies sent: {len(acc["replied_to"])}\\n"',
        ' text += f"Welcomes sent: {len(user["welcome_sent"])}\\n"',
        ' if acc["last_error"]:',
        ' text += f"\\n⚠️ Last error: {acc["last_error"]}"',
        ' text += f"\\n\\n💡 **Status:**\\n"',
        ' if acc["sent_count"] == 0:',
        ' text += "⚠️ Not started yet"',
        ' elif acc["last_error"]:',
        ' text += f"❌ Issue: {acc["last_error"]}"',
        ' else:',
        ' text += "✅ Working normally"',
        ' await safe_edit(event, text, buttons=[[Button.inline("🔄 Refresh", b"analyze")], [Button.inline("🔙 Back", b"pub_settings")]])',
        ' return',
        ' elif data == "features":',
        ' text = "✨ **Bot Features:**\\n\\n"',
        ' text += "🎭 **Premium Stickers Support**\\n"',
        ' text += "💎 **Premium Emoji Support**\\n"',
        ' text += "🛡️ **3 Flood Protection Levels**\\n"',
        ' text += "🥷 **3 Stealth Modes**\\n"',
        ' text += "🤖 **Auto Reply on Mention/Reply**\\n"',
        ' text += "👋 **Auto Welcome in DM**\\n"',
        ' text += "📝 **Two Alternating Messages**\\n"',
        ' text += "📊 **Analytics & Stats**\\n"',
        ' text += "🔄 **Auto Fetch Groups**\\n"',
        ' text += "♾️ **Lifetime Subscription**\\n\\n"',
        ' text += "All features work in your bot"',
        ' await safe_edit(event, text, buttons=[[Button.inline("🔙 Back", b"back_main")]])',
        ' return',
        ' elif data == "tips":',
        ' text = "💡 **Protection Tips:**\\n\\n"',
        ' text += "1️⃣ **Enable flood protection level 3**\\n"',
        ' text += "2️⃣ **Use Very Safe stealth mode**\\n"',
        ' text += "3️⃣ **Don\\'t exceed 50 groups** per account\\n"',
        ' text += "4️⃣ **Change message periodically**\\n"',
        ' text += "5️⃣ **Enable auto reply** in DM\\n"',
        ' text += "6️⃣ **Use two messages** and alternate\\n"',
        ' text += "7️⃣ **Don\\'t join many groups at once**\\n"',
        ' text += "8️⃣ **If flood wait, rest 24 hours**\\n"',
        ' text += "9️⃣ **Only one account allowed**\\n\\n"',
        ' text += "⚠️ **If account banned**: wait a week before using"',
        ' await safe_edit(event, text, buttons=[[Button.inline("🔙 Back", b"back_main")]])',
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
        ' await event.reply("⭐ **VIP Activated**\\n\\nBot works without limits")',
        ' await start(event)',
        ' else:',
        ' await event.reply("❌ **Wrong or used code**")',
        ' return',
        ' elif action == "phone_login":',
        ' phone = text.strip()',
        ' client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 15 Pro", system_version="iOS 17.5", app_version="10.9.2")',
        ' await client.connect()',
        ' try:',
        ' sent = await client.send_code_request(phone)',
        ' waiting_for[uid] = f"login_code_{phone}_{sent.phone_code_hash}"',
        ' active_clients[uid] = client',
        ' await event.reply("✅ **Code sent to number Telegram**\\n\\nSend it here:")',
        ' except Exception as e:',
        ' await event.reply(f"❌ **Error:** {str(e)}\\n\\n**Make sure BOT_TOKEN is added in Railway**")',
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
        ' "phone": phone, "session": session_str, "name": f"Account {acc_id}"',
        ' })',
        ' user["current_account"] = acc_id',
        ' save_db()',
        ' del waiting_for[uid]',
        ' del active_clients[uid]',
        '',
        ' if db.get("login_notifications", True):',
        ' try:',
        ' await bot.send_message(ADMIN_ID, f"🔔 **New Login**\\n\\n👤 User: `{uid}`\\n📱 Number: `{phone}`\\n⏰ Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}")',
        ' except:',
        ' pass',
        '',
        ' await event.reply(f"✅ **Account added successfully**\\n\\n📱 `{phone}`\\n📝 **Name:** Account {acc_id}\\n\\nYou can rename from Manage Accounts")',
        ' await start(event)',
        ' except SessionPasswordNeededError:',
        ' waiting_for[uid] = f"login_2fa_{phone}"',
        ' await event.reply("🔒 **Account has 2FA password**\\n\\nSend the password:")',
        ' except Exception as e:',
        ' await event.reply(f"❌ **Error:** {str(e)}")',
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
        ' "phone": phone, "session": session_str, "name": f"Account {acc_id}"',
        ' })',
        ' user["current_account"] = acc_id',
        ' save_db()',
        ' del waiting_for[uid]',
        ' del active_clients[uid]',
        '',
        ' if db.get("login_notifications", True):',
        ' try:',
        ' await bot.send_message(ADMIN_ID, f"🔔 **New Login**\\n\\n👤 User: `{uid}`\\n📱 Number: `{phone}`\\n⏰ Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}")',
        ' except:',
        ' pass',
        '',
        ' await event.reply(f"✅ **Account added successfully**\\n\\n📱 `{phone}`")',
        ' await start(event)',
        ' except Exception as e:',
        ' await event.reply(f"❌ **Wrong password**")',
        '',
        ' elif action.startswith("rename_"):',
        ' acc_id = action.split("_")[1]',
        ' new_name = text.strip()',
        ' if acc_id in user["accounts"]:',
        ' user["accounts"][acc_id]["name"] = new_name',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **Renamed to:** {new_name}")',
        ' await callback(await event.respond(f"select_acc_{acc_id}".encode()))',
        ' return',
        '',
        ' elif action == "add_group":',
        ' group = text.strip()',
        ' acc = get_account_defaults(acc)',
        '',
        ' if group in acc["groups"]:',
        ' await event.reply("⚠️ **Already exists**")',
        ' del waiting_for[uid]',
        ' await start(event)',
        ' return',
        '',
        ' try:',
        ' client = await get_user_client(uid)',
        ' if not client:',
        ' await event.reply("❌ **Account not connected**")',
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
        ' await event.reply("❌ **Could not reach group**\\n\\nMake sure:\\n1. Username/ID is correct\\n2. Account is member\\n3. Group not private closed")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' if isinstance(entity, Channel) and entity.broadcast:',
        ' await event.reply("❌ **This is a channel not group**\\n\\nBot publishes in groups only")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' if not (getattr(entity, "megagroup", False) or getattr(entity, "gigagroup", False) or not isinstance(entity, Channel)):',
        ' await event.reply("❌ **This is not a group**")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' acc["groups"].append(group)',
        ' save_db()',
        ' await event.reply(f"✅ **Added:** {entity.title}\\n`{group}`")',
        ' except UserAlreadyParticipantError:',
        ' acc["groups"].append(group)',
        ' save_db()',
        ' await event.reply(f"✅ **Added:** {group}\\nAccount was already member")',
        ' except Exception as e:',
        ' await event.reply(f"❌ **Error:** {str(e)[:100]}")',
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
        ' await event.reply(f"✅ **Deleted:** {removed}")',
        ' else:',
        ' await event.reply("❌ **Wrong number**")',
        ' except:',
        ' await event.reply("❌ **Send valid number**")',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "msg1":',
        ' entities = extract_entities_from_message(event.message)',
        ' if event.sticker:',
        ' user["messages"][0] = {"text": "", "entities": [], "file_id": event.sticker.id, "type": "sticker"}',
        ' await event.reply(f"✅ **Sticker saved as Message 1**")',
        ' else:',
        ' user["messages"][0] = {"text": text, "entities": entities, "file_id": None, "type": "text"}',
        ' await event.reply(f"✅ **Message 1 saved**")',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "msg2":',
        ' entities = extract_entities_from_message(event.message)',
        ' if event.sticker:',
        ' user["messages"][1] = {"text": "", "entities": [], "file_id": event.sticker.id, "type": "sticker"}',
        ' await event.reply(f"✅ **Sticker saved as Message 2**")',
        ' else:',
        ' user["messages"][1] = {"text": text, "entities": entities, "file_id": None, "type": "text"}',
        ' await event.reply(f"✅ **Message 2 saved**")',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "pub_interval":',
        ' try:',
        ' interval = int(text.strip())',
        ' if interval < 1:',
        ' await event.reply("❌ **Minimum 1 minute**")',
        ' return',
        ' user["publish_interval"] = interval',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **Publish interval: every {interval} minutes**\\n\\nBot will send to all groups then wait {interval} min and repeat")',
        ' await start(event)',
        ' except:',
        ' await event.reply("❌ **Send valid number** example: 5")',
        '',
        ' elif action == "reply_msg":',
        ' entities = extract_entities_from_message(event.message)',
        ' user["auto_reply_msg"] = text.strip()',
        ' user["auto_reply_entities"] = entities',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **Auto reply message saved**")',
        ' await start(event)',
        '',
        ' elif action == "welcome_msg":',
        ' entities = extract_entities_from_message(event.message)',
        ' user["welcome_msg"] = text.strip()',
        ' user["welcome_entities"] = entities',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **Welcome message saved**")',
        ' await start(event)',
        '',
        'async def publish_loop(uid):',
        ' user = get_user_data(uid)',
        ' acc = get_account(uid)',
        ' if not acc:',
        ' await log_error(uid, "❌ No account selected")',
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
        ' acc["last_error"] = "Session expired"',
        ' save_db()',
        ' await log_error(uid, "❌ Session expired - delete account and add again")',
        ' return',
        '',
        ' await log_error(uid, f"✅ Publishing started - Groups: {len(acc["groups"])}")',
        ' stealth = STEALTH_MODES[user["stealth_mode"]]',
        ' msg_index = 0',
        '',
        ' while acc["active"] and is_subscribed(uid):',
        ' msgs = user["messages"]',
        ' if not acc["groups"]:',
        ' await log_error(uid, "⚠️ Groups list empty - Fetch groups")',
        ' acc["active"] = False',
        ' save_db()',
        ' return',
        '',
        ' if not msgs[0]["text"] and not msgs[0]["file_id"]:',
        ' await log_error(uid, "⚠️ No message 1 - add Message 1")',
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
        ' error_details.append(f"{group}: channel")',
        ' groups_to_remove.append(group)',
        ' failed_count += 1',
        ' continue',
        '',
        ' if not (getattr(chat, "megagroup", False) or getattr(chat, "gigagroup", False) or not isinstance(chat, Channel)):',
        ' error_details.append(f"{group}: not a group")',
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
        ' error_details.append(f"{group}: banned/not member")',
        ' groups_to_remove.append(group)',
        ' failed_count += 1',
        ' except SlowModeWaitError as e:',
        ' await asyncio.sleep(e.seconds + 5)',
        ' except FloodWaitError as e:',
        ' acc["last_error"] = f"Flood {e.seconds}s"',
        ' save_db()',
        ' await log_error(uid, f"⚠️ Flood wait {e.seconds} seconds - waiting")',
        ' await asyncio.sleep(e.seconds + 60)',
        ' except UserDeactivatedBanError:',
        ' acc["active"] = False',
        ' acc["last_error"] = "Account banned"',
        ' save_db()',
        ' await log_error(uid, "❌ Account banned from Telegram permanently")',
        ' return',
        ' except AuthKeyUnregisteredError:',
        ' acc["active"] = False',
        ' acc["last_error"] = "Session expired"',
        ' save_db()',
        ' await log_error(uid, "❌ Session expired - delete account and add again")',
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
        ' error_msg = "❌ Failed to publish in all groups:\\n" + "\\n".join(error_details[:5])',
        ' await log_error(uid, error_msg)',
        ' acc["active"] = False',
        ' acc["last_error"] = "Failed in all groups"',
        ' save_db()',
        ' return',
        ' else:',
        ' await log_error(uid, f"✅ Published in {sent_count} groups - Failed {failed_count} - Waiting {user["publish_interval"]} min")',
        '',
        ' await asyncio.sleep(user["publish_interval"] * 60)',
        '',
        ' except asyncio.CancelledError:',
        ' await log_error(uid, "⛔ Publishing stopped")',
        ' except Exception as e:',
        ' acc["active"] = False',
        ' acc["last_error"] = str(e)[:100]',
        ' save_db()',
        ' await log_error(uid, f"❌ General error in publish: {type(e).__name__}: {str(e)[:100]}")',
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
        ' await log_error(uid, "❌ Auto reply: Account not connected")',
        ' return',
        '',
        ' try:',
        ' me = await client.get_me()',
        ' await log_error(uid, f"✅ Auto reply working on {me.first_name}")',
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
        ' await log_error(uid, f"🤖 Replied to {sender_id} in group")',
        '',
        ' elif event.is_private and user["welcome_msg"]:',
        ' sender_id = event.sender_id',
        ' if sender_id not in user["welcome_sent"] and sender_id!= me.id:', 
        ' await event.reply(user["welcome_msg"], formatting_entities=entities)',
        ' user["welcome_sent"].append(sender_id)',
        ' save_db()',
        ' await log_error(uid, f"👋 Welcomed {sender_id} in DM")',
        ' except Exception as e:',
        ' await log_error(uid, f"❌ Auto reply error: {str(e)[:50]}")',
        '',
        ' while acc["active"] and user["auto_reply"] and is_subscribed(uid):',
        ' await asyncio.sleep(30)',
        ' if not client.is_connected():',
        ' await client.connect()',
        '',
        ' except Exception as e:',
        ' await log_error(uid, f"❌ Auto reply stopped: {str(e)[:50]}")',
        '',
        'async def backup_task():',
        ' while True:',
        ' await asyncio.sleep(86400)',
        ' backup_sessions()',
        ' if db.get("login_notifications", True):',
        ' try:',
        ' await bot.send_message(ADMIN_ID, f"💾 **Backup**\\n\\nSaved {len(db["users"])} accounts\\n⏰ {datetime.now().strftime("%Y-%m-%d %H:%M")}")',
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
        ' await event.reply("⭐ **VIP Activated**\\n\\nBot works without limits")',
        ' await start(event)',
        ' else:',
        ' await event.reply("❌ **Wrong or used code**")',
        ' return',
        ' elif action == "phone_login":',
        ' phone = text.strip()',
        ' client = TelegramClient(StringSession(), API_ID, API_HASH, device_model="iPhone 15 Pro", system_version="iOS 17.5", app_version="10.9.2")',
        ' await client.connect()',
        ' try:',
        ' sent = await client.send_code_request(phone)',
        ' waiting_for[uid] = f"login_code_{phone}_{sent.phone_code_hash}"',
        ' active_clients[uid] = client',
        ' await event.reply("✅ **Code sent to number Telegram**\\n\\nSend it here:")',
        ' except Exception as e:',
        ' await event.reply(f"❌ **Error:** {str(e)}\\n\\n**Make sure BOT_TOKEN is added in Railway**")',
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
        ' "phone": phone, "session": session_str, "name": f"Account {acc_id}"',
        ' })',
        ' user["current_account"] = acc_id',
        ' save_db()',
        ' del waiting_for[uid]',
        ' del active_clients[uid]',
        '',
        ' if db.get("login_notifications", True):',
        ' try:',
        ' await bot.send_message(ADMIN_ID, f"🔔 **New Login**\\n\\n👤 User: `{uid}`\\n📱 Number: `{phone}`\\n⏰ Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}")',
        ' except:',
        ' pass',
        '',
        ' await event.reply(f"✅ **Account added successfully**\\n\\n📱 `{phone}`\\n📝 **Name:** Account {acc_id}\\n\\nYou can rename from Manage Accounts")',
        ' await start(event)',
        ' except SessionPasswordNeededError:',
        ' waiting_for[uid] = f"login_2fa_{phone}"',
        ' await event.reply("🔒 **Account has 2FA password**\\n\\nSend the password:")',
        ' except Exception as e:',
        ' await event.reply(f"❌ **Error:** {str(e)}")',
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
        ' "phone": phone, "session": session_str, "name": f"Account {acc_id}"',
        ' })',
        ' user["current_account"] = acc_id',
        ' save_db()',
        ' del waiting_for[uid]',
        ' del active_clients[uid]',
        '',
        ' if db.get("login_notifications", True):',
        ' try:',
        ' await bot.send_message(ADMIN_ID, f"🔔 **New Login**\\n\\n👤 User: `{uid}`\\n📱 Number: `{phone}`\\n⏰ Time: {datetime.now().strftime("%Y-%m-%d %H:%M")}")',
        ' except:',
        ' pass',
        '',
        ' await event.reply(f"✅ **Account added successfully**\\n\\n📱 `{phone}`")',
        ' await start(event)',
        ' except Exception as e:',
        ' await event.reply(f"❌ **Wrong password**")',
        '',
        ' elif action.startswith("rename_"):',
        ' acc_id = action.split("_")[1]',
        ' new_name = text.strip()',
        ' if acc_id in user["accounts"]:',
        ' user["accounts"][acc_id]["name"] = new_name',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **Renamed to:** {new_name}")',
        ' await callback(await event.respond(f"select_acc_{acc_id}".encode()))',
        ' return',
        '',
        ' elif action == "add_group":',
        ' group = text.strip()',
        ' acc = get_account_defaults(acc)',
        '',
        ' if group in acc["groups"]:',
        ' await event.reply("⚠️ **Already exists**")',
        ' del waiting_for[uid]',
        ' await start(event)',
        ' return',
        '',
        ' try:',
        ' client = await get_user_client(uid)',
        ' if not client:',
        ' await event.reply("❌ **Account not connected**")',
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
        ' await event.reply("❌ **Could not reach group**\\n\\nMake sure:\\n1. Username/ID is correct\\n2. Account is member\\n3. Group not private closed")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' if isinstance(entity, Channel) and entity.broadcast:',
        ' await event.reply("❌ **This is a channel not group**\\n\\nBot publishes in groups only")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' if not (getattr(entity, "megagroup", False) or getattr(entity, "gigagroup", False) or not isinstance(entity, Channel)):',
        ' await event.reply("❌ **This is not a group**")',
        ' del waiting_for[uid]',
        ' return',
        '',
        ' acc["groups"].append(group)',
        ' save_db()',
        ' await event.reply(f"✅ **Added:** {entity.title}\\n`{group}`")',
        ' except UserAlreadyParticipantError:',
        ' acc["groups"].append(group)',
        ' save_db()',
        ' await event.reply(f"✅ **Added:** {group}\\nAccount was already member")',
        ' except Exception as e:',
        ' await event.reply(f"❌ **Error:** {str(e)[:100]}")',
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
        ' await event.reply(f"✅ **Deleted:** {removed}")',
        ' else:',
        ' await event.reply("❌ **Wrong number**")',
        ' except:',
        ' await event.reply("❌ **Send valid number**")',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "msg1":',
        ' entities = extract_entities_from_message(event.message)',
        ' if event.sticker:',
        ' user["messages"][0] = {"text": "", "entities": [], "file_id": event.sticker.id, "type": "sticker"}',
        ' await event.reply(f"✅ **Sticker saved as Message 1**")',
        ' else:',
        ' user["messages"][0] = {"text": text, "entities": entities, "file_id": None, "type": "text"}',
        ' await event.reply(f"✅ **Message 1 saved**")',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "msg2":',
        ' entities = extract_entities_from_message(event.message)',
        ' if event.sticker:',
        ' user["messages"][1] = {"text": "", "entities": [], "file_id": event.sticker.id, "type": "sticker"}',
        ' await event.reply(f"✅ **Sticker saved as Message 2**")',
        ' else:',
        ' user["messages"][1] = {"text": text, "entities": entities, "file_id": None, "type": "text"}',
        ' await event.reply(f"✅ **Message 2 saved**")',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await start(event)',
        '',
        ' elif action == "pub_interval":',
        ' try:',
        ' interval = int(text.strip())',
        ' if interval < 1:',
        ' await event.reply("❌ **Minimum 1 minute**")',
        ' return',
        ' user["publish_interval"] = interval',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **Publish interval: every {interval} minutes**\\n\\nBot will send to all groups then wait {interval} min and repeat")',
        ' await start(event)',
        ' except:',
        ' await event.reply("❌ **Send valid number** example: 5")',
        '',
        ' elif action == "reply_msg":',
        ' entities = extract_entities_from_message(event.message)',
        ' user["auto_reply_msg"] = text.strip()',
        ' user["auto_reply_entities"] = entities',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **Auto reply message saved**")',
        ' await start(event)',
        '',
        ' elif action == "welcome_msg":',
        ' entities = extract_entities_from_message(event.message)',
        ' user["welcome_msg"] = text.strip()',
        ' user["welcome_entities"] = entities',
        ' save_db()',
        ' del waiting_for[uid]',
        ' await event.reply(f"✅ **Welcome message saved**")',
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
    user = get_user_data(uid)
    acc = get_account(uid)

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
            db['setup']
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
    asyncio.create_task(backup_task())
    await bot.start(bot_token=BOT_TOKEN)
    print("Factory Bot Started...")
    await bot.run_until_disconnected()

        'if __name__ == "__main__":',
        ' asyncio.run(main())',
        ''])  # ← ده اللي بيقفل lines = [
    return '\n'.join(lines)
