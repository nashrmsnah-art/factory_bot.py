from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
import asyncio
import json
import os
import subprocess
import sys
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
db = {'clients': {}, 'pending': {}, 'running_bots': {}}
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

def main_menu(uid):
    if uid == ADMIN_ID:
        return [
            [Button.inline("👥 العملاء", b"clients"), Button.inline("⏳ قيد الانتظار", b"pending")],
            [Button.inline("🤖 البوتات الشغالة", b"running")],
            [Button.inline("➕ اضافة عميل يدوي", b"add_manual")]
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

def save_bot_code(bot_token, admin_id, username, required_channel, dev_username):
    """ينسخ كود بوت النشر مخصص لكل عميل"""
    channels = f"['{required_channel}']" if required_channel else "[]"

    code = f'''from telethon import TelegramClient, events, Button
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, FloodWaitError, UserDeactivatedBanError, UserAlreadyParticipantError
from telethon.tl.functions.channels import GetParticipantRequest, JoinChannelRequest
from telethon.tl.types import MessageEntityCustomEmoji, MessageEntityBold, MessageEntityItalic, MessageEntityCode, MessageEntityPre, MessageEntityTextUrl, MessageEntityUrl, Channel
from telethon.errors.rpcerrorlist import ChatWriteForbiddenError, ChatAdminRequiredError, UserBannedInChannelError, SlowModeWaitError, ChannelPrivateError, UserNotParticipantError, AuthKeyUnregisteredError, MessageNotModifiedError
import asyncio
import json
import os
from datetime import datetime, timedelta
import random
import re

API_ID = 33595004
API_HASH = 'cbd1066ed026997f2f4a7c4323b7bda7'
BOT_TOKEN = "{bot_token}"
ADMIN_ID = {admin_id}
DEVELOPER_USERNAME = '{dev_username}'
DEVELOPER_LINK = f'https://t.me/{{DEVELOPER_USERNAME}}'
REQUIRED_CHANNELS = {channels}
DB_FILE = 'db_{admin_id}.json'
BACKUP_FILE = 'backup_{admin_id}.json'
SUB_PRICE = 5
MAX_ACCOUNTS = 1
FREE_TRIAL_DAYS = 99999

bot = TelegramClient('bot_{admin_id}', API_ID, API_HASH)
db = {{'users': {{}}, 'codes': {{}}, 'stats': {{'total_sent': 0}}, 'login_notifications': True}}
waiting_for = {{}}
active_clients = {{}}
running_tasks = {{}}
user_clients = {{}}
reply_tasks = {{}}

STEALTH_MODES = {{
    'fast': {{'group_delay': [2, 5], 'name': '⚡ سريع'}},
    'balanced': {{'group_delay': [5, 10], 'name': '⚖️ متوازن'}},
    'safe': {{'group_delay': [10, 20], 'name': '🛡️ آمن جدا'}}
}}

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

def backup_sessions():
    backup = {{}}
    for uid, user in db['users'].items():
        for acc_id, acc in user.get('accounts', {{}}).items():
            if acc.get('session'):
                backup[f"{{uid}}_{{acc_id}}"] = {{
                    'phone': acc['phone'],
                    'session': acc['session'],
                    'name': acc['name'],
                    'user_id': uid,
                    'backed_up_at': datetime.now().isoformat()
                }}
    with open(BACKUP_FILE, 'w', encoding='utf-8') as f:
        json.dump(backup, f, ensure_ascii=False, indent=2)

def get_user_data(uid):
    uid = str(uid)
    if uid not in db['users']:
        db['users'][uid] = {{
            'sub_end': (datetime.now() + timedelta(days=36500)).isoformat(),
            'accounts': {{}}, 'current_account': None,
            'messages': [{{'text': '', 'entities': [], 'file_id': None, 'type': 'text'}}, {{'text': '', 'entities': [], 'file_id': None, 'type': 'text'}}],
            'publish_interval': 5, 'flood_protection': 2, 'stealth_mode': 'balanced',
            'auto_reply': False, 'auto_reply_msg': '', 'auto_reply_entities': [],
            'welcome_msg': '', 'welcome_entities': [],
            'welcome_sent': [], 'is_trial': False, 'used_trial': True
        }}
        save_db()
    return db['users'][uid]

def is_subscribed(uid):
    return True

def get_account(uid):
    user = get_user_data(uid)
    acc_id = user.get('current_account')
    if not acc_id or acc_id not in user['accounts']:
        return None
    return user['accounts'][acc_id]

def get_account_defaults(acc):
    defaults = {{
        'active': False, 'groups': [], 'name': 'حساب جديد',
        'phone': '', 'session': '', 'sent_count': 0,
        'last_error': None, 'created_at': datetime.now().isoformat(),
        'replied_to': []
    }}
    for k, v in defaults.items():
        if k not in acc:
            acc[k] = v
    return acc

def extract_entities_from_message(message):
    entities = []
    if message.entities:
        for ent in message.entities:
            if isinstance(ent, MessageEntityCustomEmoji):
                entities.append({{'type': 'custom_emoji', 'offset': ent.offset, 'length': ent.length, 'document_id': ent.document_id}})
            elif isinstance(ent, MessageEntityBold):
                entities.append({{'type': 'bold', 'offset': ent.offset, 'length': ent.length}})
            elif isinstance(ent, MessageEntityItalic):
                entities.append({{'type': 'italic', 'offset': ent.offset, 'length': ent.length}})
            elif isinstance(ent, MessageEntityCode):
                entities.append({{'type': 'code', 'offset': ent.offset, 'length': ent.length}})
            elif isinstance(ent, MessageEntityPre):
                entities.append({{'type': 'pre', 'offset': ent.offset, 'length': ent.length, 'language': ent.language}})
            elif isinstance(ent, MessageEntityTextUrl):
                entities.append({{'type': 'text_url', 'offset': ent.offset, 'length': ent.length, 'url': ent.url}})
            elif isinstance(ent, MessageEntityUrl):
                entities.append({{'type': 'url', 'offset': ent.offset, 'length': ent.length}})
    return entities

def build_entities(saved_entities):
    entities = []
    for ent in saved_entities:
        if ent['type'] == 'custom_emoji':
            entities.append(MessageEntityCustomEmoji(offset=ent['offset'], length=ent['length'], document_id=ent['document_id']))
        elif ent['type'] == 'bold':
            entities.append(MessageEntityBold(offset=ent['offset'], length=ent['length']))
        elif ent['type'] == 'italic':
            entities.append(MessageEntityItalic(offset=ent['offset'], length=ent['length']))
        elif ent['type'] == 'code':
            entities.append(MessageEntityCode(offset=ent['offset'], length=ent['length']))
        elif ent['type'] == 'pre':
            entities.append(MessageEntityPre(offset=ent['offset'], length=ent['length'], language=ent.get('language', '')))
        elif ent['type'] == 'text_url':
            entities.append(MessageEntityTextUrl(offset=ent['offset'], length=ent['length'], url=ent['url']))
        elif ent['type'] == 'url':
            entities.append(MessageEntityUrl(offset=ent['offset'], length=ent['length']))
    return entities

def main_menu(uid):
    btns = [
        [Button.inline("📱 اضافة حساب برقم", b"add_account")],
        [Button.inline("📱 ادارة الحسابات", b"accounts_menu")],
        [Button.inline("⚙️ اعدادات النشر", b"pub_settings"), Button.inline("📊 تحليل النشر", b"analyze")],
        [Button.inline("🔄 تشغيل", b"start_pub"), Button.inline("⛔ ايقاف", b"stop_pub")],
        [Button.inline("✨ مميزات البوت", b"features"), Button.inline("💡 نصائح الحماية", b"tips")],
        [Button.url("👨‍💻 المطور", DEVELOPER_LINK)]
    ]
    return btns

def accounts_menu(uid):
    user = get_user_data(uid)
    accounts = user['accounts']
    btns = []
    for acc_id, acc in accounts.items():
        acc = get_account_defaults(acc)
        status = "🟢" if acc['active'] else "⚪"
        current = " 👈" if user['current_account'] == acc_id else ""
        btns.append([Button.inline(f"{{status}} {{acc['name']}}{{current}}", f"select_acc_{{acc_id}}".encode())])
    if len(accounts) < MAX_ACCOUNTS:
        btns.append([Button.inline("➕ اضافة حساب جديد", b"add_account")])
    btns.append([Button.inline("🔙 رجوع", b"back_main")])
    return btns

def account_details_menu(uid, acc_id):
    acc = get_user_data(uid)['accounts'][acc_id]
    acc = get_account_defaults(acc)
    status = "🟢 يعمل" if acc['active'] else "🔴 متوقف"
    btns = [
        [Button.inline(f"{{status}}", f"toggle_acc_{{acc_id}}".encode())],
        [Button.inline("✏️ تغيير الاسم", f"rename_acc_{{acc_id}}".encode())],
        [Button.inline("👥 الجروبات", f"groups_acc_{{acc_id}}".encode())],
        [Button.inline("💾 نسخ السيشن", f"copy_session_{{acc_id}}".encode())],
        [Button.inline("🗑️ حذف الحساب", f"delete_acc_{{acc_id}}".encode())],
        [Button.inline("🔙 رجوع", b"accounts_menu")]
    ]
    return btns

def pub_settings_menu(uid):
    user = get_user_data(uid)
    acc = get_account(uid)
    if not acc:
        return [[Button.inline("❌ مفيش حساب محدد", b"accounts_menu")], [Button.inline("🔙 رجوع", b"back_main")]]
    acc = get_account_defaults(acc)
    status = "🟢 يعمل" if acc['active'] else "🔴 متوقف"
    flood_level = ["❌", "🟡", "🟢", "🛡️"][user['flood_protection']]
    stealth = STEALTH_MODES[user['stealth_mode']]['name']
    auto_reply = "✅" if user['auto_reply'] else "❌"
    msg1 = user['messages'][0]
    msg2 = user['messages'][1]
    msg1_status = "✅ ملصق" if msg1['type'] == 'sticker' else "✅ نص" if msg1['text'] else "❌"
    msg2_status = "✅ ملصق" if msg2['type'] == 'sticker' else "✅ نص" if msg2['text'] else "❌"
    btns = [
        [Button.inline(f"📱 {{acc['name']}} | {{status}}", b"accounts_menu")],
        [Button.inline("🔄 جلب الجروبات", b"fetch_groups"), Button.inline("👥 الجروبات", b"manage_groups")],
        [Button.inline(f"📝 رسالة 1 {{msg1_status}}", b"msg1"), Button.inline(f"📝 رسالة 2 {{msg2_status}}", b"msg2")],
        [Button.inline(f"⏱️ النشر كل {{user['publish_interval']}} دقيقة", b"pub_interval")],
        [Button.inline(f"{{flood_level}} حماية الفلود", b"flood_level")],
        [Button.inline(f"{{stealth}} التخفي", b"stealth_mode")],
        [Button.inline(f"{{auto_reply}} رد تلقائي", b"auto_reply"), Button.inline("✏️ تعيين الرد", b"set_reply_msg")],
        [Button.inline("👋 تعيين الترحيب", b"set_welcome"), Button.inline("🗑️ مسح المردود عليهم", b"clear_replied")],
        [Button.inline("🔙 رجوع", b"back_main")]
    ]
    return btns

async def get_user_client(uid):
    acc = get_account(uid)
    if not acc or 'session' not in acc:
        return None
    key = f"{{uid}}_{{get_user_data(uid)['current_account']}}"
    if key in user_clients:
        try:
            if user_clients[key].is_connected():
                return user_clients[key]
            else:
                del user_clients[key]
        except:
            del user_clients[key]
    try:
        client = TelegramClient(StringSession(acc['session']), API_ID, API_HASH, device_model="iPhone 15 Pro", system_version="iOS 17.5", app_version="10.9.2")
        await client.connect()
        if not await client.is_user_authorized():
            await client.disconnect()
            return None
        user_clients[key] = client
        return client
    except:
        return None

async def log_error(uid, error_text):
    try:
        await bot.send_message(uid, f"⚠️ **تشخيص:**\\n\\n{{error_text}}")
    except:
        pass

async def safe_edit(event, text, buttons=None):
    try:
        await event.edit(text, buttons=buttons)
    except MessageNotModifiedError:
        pass
    except:
        pass

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    user = get_user_data(uid)

    for channel in REQUIRED_CHANNELS:
        try:
            await bot(GetParticipantRequest(channel, uid))
        except:
            btns = [[Button.url(f"📢 اشترك هنا", f"https://t.me/{{channel}}")], [Button.inline("✅ تحققت", b"check_sub")]]
            await event.reply("🔒 **اشترك في القناة الاول:**", buttons=btns)
            return

    acc = get_account(uid)
    acc = get_account_defaults(acc) if acc else None
    sent = acc['sent_count'] if acc else 0
    accounts_count = len(user['accounts'])
    text = f"🔥 **بوت النشر الاحترافي**\\n\\n"
    text += f"✅ اشتراكك فعال - مدى الحياة\\n"
    text += f"📱 الحسابات: {{accounts_count}}/{{MAX_ACCOUNTS}}\\n"
    text += f"📤 الرسائل المرسلة: {{sent}}\\n\\n"
    if acc:
        text += f"👤 الحساب الحالي: {{acc['name']}}\\n\\n"
    text += "اختر من القائمة:"
    await event.reply(text, buttons=main_menu(uid))

#... باقي الهاندلرز كاملة من الكود السابق...

async def publish_loop(uid):
    user = get_user_data(uid)
    acc = get_account(uid)
    if not acc:
        await log_error(uid, '❌ لا يوجد حساب محدد')
        return
    acc = get_account_defaults(acc)
    key = f"{{uid}}_{{user['current_account']}}"
    client = TelegramClient(StringSession(acc['session']), API_ID, API_HASH, device_model="iPhone 15 Pro", system_version="iOS 17.5", app_version="10.9.2")
    try:
        await client.connect()
        if not await client.is_user_authorized():
            acc['active'] = False
            acc['last_error'] = 'انتهت صلاحية الجلسة'
            save_db()
            await log_error(uid, '❌ انتهت صلاحية الجلسة - احذف الحساب وضيفه من جديد')
            return
        await log_error(uid, f'✅ بدأ النشر - عدد الجروبات: {{len(acc["groups"])}}')
        stealth = STEALTH_MODES[user['stealth_mode']]
        msg_index = 0
        while acc['active'] and is_subscribed(uid):
            msgs = user['messages']
            if not acc['groups']:
                await log_error(uid, '⚠️ قائمة الجروبات فاضية - اعمل جلب الجروبات')
                acc['active'] = False
                save_db()
                return
            if not msgs[0]['text'] and not msgs[0]['file_id']:
                await log_error(uid, '⚠️ مفيش رسالة 1 - ضيف رسالة 1')
                acc['active'] = False
                save_db()
                return
            msg_data = msgs[msg_index % 2]
            if not msg_data['text'] and not msg_data['file_id']:
                msg_data = msgs[0]
            msg_index += 1
            groups_to_remove = []
            sent_count = 0
            failed_count = 0
            error_details = []
            for group in acc['groups']:
                try:
                    if group.startswith('@'):
                        entity = group
                    else:
                        entity = int(group)
                    try:
                        chat = await client.get_entity(entity)
                    except Exception as e:
                        error_details.append(f"{{group}}: {{str(e)[:40]}}")
                        groups_to_remove.append(group)
                        failed_count += 1
                        continue
                    if isinstance(chat, Channel) and chat.broadcast:
                        error_details.append(f"{{group}}: ده قناة")
                        groups_to_remove.append(group)
                        failed_count += 1
                        continue
                    if not (getattr(chat, 'megagroup', False) or getattr(chat, 'gigagroup', False) or not isinstance(chat, Channel)):
                        error_details.append(f"{{group}}: مش جروب")
                        groups_to_remove.append(group)
                        failed_count += 1
                        continue
                    if msg_data['type'] == 'sticker' and msg_data['file_id']:
                        await client.send_file(chat, msg_data['file_id'])
                    else:
                        entities = build_entities(msg_data.get('entities', []))
                        await client.send_message(chat, msg_data['text'], formatting_entities=entities)
                    acc['sent_count'] += 1
                    db['stats']['total_sent'] += 1
                    sent_count += 1
                    save_db()
                    delay = random.randint(*stealth['group_delay'])
                    if user['flood_protection'] >= 2:
                        delay += random.randint(5, 15)
                    if user['flood_protection'] == 3:
                        delay += random.randint(15, 30)
                    await asyncio.sleep(delay)
                except (ChatWriteForbiddenError, ChatAdminRequiredError, UserBannedInChannelError, ChannelPrivateError, UserNotParticipantError):
                    error_details.append(f"{{group}}: محظور/مش عضو")
                    groups_to_remove.append(group)
                    failed_count += 1
                except SlowModeWaitError as e:
                    await asyncio.sleep(e.seconds + 5)
                except FloodWaitError as e:
                    acc['last_error'] = f'فلود {{e.seconds}}ث'
                    save_db()
                    await log_error(uid, f'⚠️ فلود وايت {{e.seconds}} ثانية - بستنى')
                    await asyncio.sleep(e.seconds + 60)
                except UserDeactivatedBanError:
                    acc['active'] = False
                    acc['last_error'] = 'الحساب محظور من تيليجرام'
                    save_db()
                    await log_error(uid, '❌ الحساب محظور من تيليجرام نهائيا')
                    return
                except AuthKeyUnregisteredError:
                    acc['active'] = False
                    acc['last_error'] = 'انتهت صلاحية الجلسة'
                    save_db()
                    await log_error(uid, '❌ انتهت صلاحية الجلسة - احذف الحساب وضيفه من جديد')
                    return
                except Exception as e:
                    error_details.append(f"{{group}}: {{str(e)[:40]}}")
                    failed_count += 1
            for g in groups_to_remove:
                if g in acc['groups']:
                    acc['groups'].remove(g)
            if groups_to_remove:
                save_db()
            if sent_count == 0 and len(acc['groups']) > 0:
                error_msg = "❌ فشل النشر في كل الجروبات:\\n" + "\\n".join(error_details[:5])
                await log_error(uid, error_msg)
                acc['active'] = False
                acc['last_error'] = 'فشل في كل الجروبات'
                save_db()
                return
            else:
                await log_error(uid, f'✅ تم النشر في {{sent_count}} جروب - فشل {{failed_count}} - بستنى {{user["publish_interval"]}} دقيقة')
            await asyncio.sleep(user['publish_interval'] * 60)
    except asyncio.CancelledError:
        await log_error(uid, '⛔ تم ايقاف النشر')
    except Exception as e:
        acc['active'] = False
        acc['last_error'] = str(e)[:100]
        save_db()
        await log_error(uid, f'❌ خطأ عام في النشر: {{type(e).__name__}}: {{str(e)[:100]}}')
    finally:
        try:
            await client.disconnect()
        except:
            pass

async def start_auto_reply(uid):
    user = get_user_data(uid)
    acc = get_account(uid)
    if not acc or not user['auto_reply']:
        return
    acc = get_account_defaults(acc)
    client = await get_user_client(uid)
    if not client:
        await log_error(uid, '❌ الرد التلقائي: الحساب غير متصل')
        return
    try:
        me = await client.get_me()
        await log_error(uid, f'✅ الرد التلقائي شغال على {{me.first_name}}')
        @client.on(events.NewMessage(incoming=True))
        async def handler(event):
            try:
                if event.is_group and user['auto_reply_msg']:
                    is_mention = event.message.mentioned
                    is_reply_to_me = False
                    if event.is_reply:
                        reply_msg = await event.get_reply_message()
                        if reply_msg and reply_msg.sender_id == me.id:
                            is_reply_to_me = True
                    if is_mention or is_reply_to_me:
                        sender_id = event.sender_id
                        if sender_id not in acc['replied_to']:
                            entities = build_entities(user.get('auto_reply_entities', []))
                            await event.reply(user['auto_reply_msg'], formatting_entities=entities)
                            acc['replied_to'].append(sender_id)
                            save_db()
                            await log_error(uid, f'🤖 رديت على {{sender_id}} في الجروب')
                elif event.is_private and user['welcome_msg']:
                    sender_id = event.sender_id
                    if sender_id not in user['welcome_sent'] and sender_id!= me.id:
                        entities = build_entities(user.get('welcome_entities', []))
                        await event.reply(user['welcome_msg'], formatting_entities=entities)
                        user['welcome_sent'].append(sender_id)
                        save_db()
                        await log_error(uid, f'👋 رحبت بـ {{sender_id}} في الخاص')
            except Exception as e:
                await log_error(uid, f'❌ خطأ في الرد التلقائي: {{str(e)[:50]}}')
        while acc['active'] and user['auto_reply'] and is_subscribed(uid):
            await asyncio.sleep(30)
            if not client.is_connected():
                await client.connect()
    except Exception as e:
        await log_error(uid, f'❌ الرد التلقائي وقف: {{str(e)[:50]}}')

async def backup_task():
    while True:
        await asyncio.sleep(86400)
        backup_sessions()
        if db.get('login_notifications', True):
            try:
                await bot.send_message(ADMIN_ID, f"💾 **نسخة احتياطية**\\n\\nتم حفظ {{len(db['users'])}} حساب\\n⏰ {{datetime.now().strftime('%Y-%m-%d %H:%M')}}")
            except:
                pass

async def main():
    load_db()
    asyncio.create_task(backup_task())
    await bot.start(bot_token=BOT_TOKEN)
    print("Bot Started Successfully...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
'''
    return code

@bot.on(events.NewMessage(pattern='/start'))
async def start(event):
    uid = event.sender_id
    if uid == ADMIN_ID:
        text = f"👑 **مصنع بوتات النشر**\n\n"
        text += f"💰 السعر: ${PRICE} مدى الحياة\n"
        text += f"👥 العملاء: {len(db['clients'])}\n"
        text += f"🤖 البوتات الشغالة: {len(db['running_bots'])}\n"
        text += f"⏳ قيد الانتظار: {len(db['pending'])}"
    else:
        text = f"🤖 **مصنع بوتات النشر الاحترافي**\n\n"
        text += f"💰 **السعر:** ${PRICE} مدى الحياة\n"
        text += f"✅ **المميزات:**\n"
        text += "🔑 حساب واحد برقم الهاتف\n"
        text += "📝 نشر تلقائي احترافي\n"
        text += "🎭 دعم الملصقات البريميوم\n"
        text += "💎 دعم الايموجي البريميوم\n"
        text += "🛡️ 3 مستويات حماية\n"
        text += "🤖 رد تلقائي + ترحيب\n"
        text += "♾️ اشتراك مدى الحياة\n\n"
        text += "**دوس شراء وادفع وابعت الاسكرين**"
    await event.reply(text, buttons=main_menu(uid))

@bot.on(events.CallbackQuery)
async def callback(event):
    uid = event.sender_id
    data = event.data.decode()

    if data == 'buy':
        text = f"💰 **الدفع {PRICE}$ - اختر الطريقة:**\n\n"
        text += "1️⃣ دوس على طريقة الدفع عشان تنسخ العنوان\n"
        text += "2️⃣ حول المبلغ\n"
        text += "3️⃣ دوس 'دفعت - ارسل الاثبات' وابعت اسكرين\n\n"
        text += "⚠️ **مهم:** احتفظ بالاسكرين"
        await event.edit(text, buttons=payment_menu())
        return

    elif data.startswith('pay_'):
        method = data.split('_')[1]
        if method in PAYMENT_METHODS:
            info = PAYMENT_METHODS[method]
            text = f"{info['icon']} **{info['name']}**\n\n"
            if 'number' in info:
                text += f"**الرقم:**\n```\n{info['number']}\n```\n\n"
            if 'address' in info:
                text += f"**العنوان:**\n```\n{info['address']}\n```\n\n"
            text += "✅ **اضغط على الرقم/العنوان لنسخه**\n\n"
            text += "بعد التحويل دوس 'دفعت - ارسل الاثبات'"
            await event.edit(text, buttons=[[Button.inline("✅ دفعت - ارسل الاثبات", b"send_proof")], [Button.inline("🔙 رجوع", b"buy")]])
        return

    elif data == 'send_proof':
        waiting_for[uid] = 'payment_proof'
        await event.edit("📸 **ابعت اسكرين التحويل هنا:**\n\nهيوصلك البوت خلال 5 دقايق بعد المراجعة", buttons=[[Button.inline("🔙 رجوع", b"buy")]])
        return

    elif data == 'my_bot':
        if str(uid) in db['clients']:
            client = db['clients'][str(uid)]
            status = "🟢 شغال" if client.get('running') else "🔴 متوقف"
            text = f"🤖 **بوتك الخاص**\n\n"
            text += f"الحالة: {status}\n"
            text += f"اليوزر: @{client['username']}\n"
            text += f"تاريخ الشراء: {client['created_at'][:10]}\n\n"
            text += "ابعت /start للبوت بتاعك عشان تستخدمه"
            btns = [[Button.url("🤖 افتح بوتي", f"https://t.me/{client['username']}")]]
        else:
            text = "❌ **معندكش بوت**\n\nدوس شراء عشان تطلب بوت خاص بيك"
            btns = [[Button.inline("💰 شراء", b"buy")]]
        await event.edit(text, buttons=btns + [[Button.inline("🔙 رجوع", b"back")]])
        return

    elif data == 'clients' and uid == ADMIN_ID:
        text = "👥 **العملاء:**\n\n"
        for cid, client in db['clients'].items():
            status = "🟢" if client.get('running') else "🔴"
            text += f"{status} `{cid}` - @{client['username']}\n"
        await event.edit(text or "لا يوجد عملاء", buttons=[[Button.inline("🔙 رجوع", b"back")]])
        return

    elif data == 'pending' and uid == ADMIN_ID:
        btns = []
        for pid, pdata in db['pending'].items():
            btns.append([Button.inline(f"✅ قبول {pid}", f"approve_{pid}".encode())])
            btns.append([Button.inline(f"❌ رفض {pid}", f"reject_{pid}".encode())])
        await event.edit(f"⏳ **قيد الانتظار: {len(db['pending'])}**", buttons=btns + [[Button.inline("🔙 رجوع", b"back")]])
        return

    elif data == 'running' and uid == ADMIN_ID:
        text = "🤖 **البوتات الشغالة:**\n\n"
        for rid, rdata in db['running_bots'].items():
            text += f"✅ @{rdata['username']} - {rid}\n"
        await event.edit(text or "لا يوجد", buttons=[[Button.inline("🔙 رجوع", b"back")]])
        return

    elif data.startswith('approve_') and uid == ADMIN_ID:
        pid = data.split('_')[1]
        waiting_for[ADMIN_ID] = f'get_details_{pid}'
        await event.edit(f"📝 **اكتب بيانات البوت للعميل {pid}:**\n\nالصيغة:\n`TOKEN|ADMIN_ID|CHANNEL|DEV_USERNAME`\n\nمثال:\n`123:ABC|987654321|VipChannel|Devazf`\n\nCHANNEL = قناة الاشتراك الاجباري او خليها فاضية\nDEV_USERNAME = يوزر المطور اللي هيظهر في البوت", buttons=[[Button.inline("🔙 رجوع", b"back")]])
        return

    elif data.startswith('reject_') and uid == ADMIN_ID:
        pid = data.split('_')[1]
        del db['pending'][pid]
        save_db()
        await bot.send_message(int(pid), "❌ **تم رفض طلبك**\n\nتواصل مع @Devazf")
        await event.answer("✅ تم الرفض")
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

    if action == 'payment_proof':
        db['pending'][str(uid)] = {
            'payment_proof': event.message.id,
            'time': datetime.now().isoformat()
        }
        save_db()
        del waiting_for[uid]
        await event.reply("✅ **تم استلام طلبك**\n\nجاري المراجعة وهيوصلك البوت خلال 5 دقايق بعد الموافقة")
        await bot.send_message(ADMIN_ID, f"💰 **طلب جديد**\n\n👤 العميل: `{uid}`\n⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\nراجع الاسكرين فوق")
        await bot.forward_messages(ADMIN_ID, event.message)
        return

    elif action.startswith('get_details_'):
        pid = action.split('_')[2]
        try:
            parts = event.raw_text.strip().split('|')
            bot_token = parts[0].strip()
            admin_id = int(parts[1].strip())
            required_channel = parts[2].strip() if len(parts) > 2 and parts[2].strip() else ""
            dev_username = parts[3].strip() if len(parts) > 3 and parts[3].strip() else "Devazf"

            bot_code = save_bot_code(bot_token, admin_id, f"pub_bot_{pid}", required_channel, dev_username)
            bot_file = f"{BOTS_DIR}/bot_{pid}.py"

            with open(bot_file, 'w', encoding='utf-8') as f:
                f.write(bot_code)

            process = subprocess.Popen([sys.executable, bot_file],
                                                 stdout=subprocess.PIPE,
                                     stderr=subprocess.PIPE)

            # جلب يوزر البوت
            temp_client = TelegramClient(StringSession(), API_ID, API_HASH)
            await temp_client.start(bot_token=bot_token)
            me = await temp_client.get_me()
            username = me.username
            await temp_client.disconnect()

            db['clients'][pid] = {
                'token': bot_token,
                'username': username,
                'admin_id': admin_id,
                'required_channel': required_channel,
                'dev_username': dev_username,
                'running': True,
                'pid': process.pid,
                'created_at': datetime.now().isoformat()
            }
            db['running_bots'][pid] = {
                'username': username,
                'pid': process.pid
            }
            del db['pending'][pid]
            save_db()
            del waiting_for[ADMIN_ID]

            channel_text = f"\n📢 قناة الاشتراك: @{required_channel}" if required_channel else ""

            await event.reply(f"✅ **تم تشغيل البوت**\n\n🤖 @{username}\n👤 للعميل: `{pid}`\n👑 ادمن: `{admin_id}`{channel_text}")
            await bot.send_message(int(pid), f"🎉 **مبروك! بوتك جاهز**\n\n🤖 اليوزر: @{username}\n👑 الادمن: `{admin_id}`{channel_text}\n💰 مدى الحياة\n\nابعت /start للبوت بتاعك عشان تبدأ\n\n**مهم:** انت الادمن الوحيد اللي يقدر يتحكم في البوت")

        except Exception as e:
            await event.reply(f"❌ **خطأ في التشغيل:** {str(e)}\n\nتأكد من:\n1. التوكن صحيح\n2. الايدي رقم فقط\n3. القناة موجودة لو كتبتها")
        return

async def main():
    load_db()
    await bot.start(bot_token=BOT_TOKEN)
    print("Factory Bot Started...")
    await bot.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
