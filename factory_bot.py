import os
import json
import asyncio
import random
import requests
import base64
import string
import re
from telethon import TelegramClient, events, Button

# ========== إعدادات المصنع ==========
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

client = TelegramClient('factory_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
pending = {}
codes_db = "codes.json"

# ========== نظام الاكواد ==========
def load_codes():
    if not os.path.exists(codes_db):
        with open(codes_db, 'w') as f:
            json.dump({"codes": {}}, f)
    with open(codes_db, 'r') as f:
        return json.load(f)

def save_codes(data):
    with open(codes_db, 'w') as f:
        json.dump(data, f, indent=2)

def generate_code():
    return 'FACTORY-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

# ========== دوال Railway API ==========
def create_railway_project(name, bot_token):
    headers = {
        "Authorization": f"Bearer {RAILWAY_API_TOKEN}",
        "Content-Type": "application/json"
    }
    query = """
    mutation($input: ProjectCreateInput!) {
        projectCreate(input: $input) {
            id
            name
        }
    }
    """
    variables = {
        "input": {
            "name": name,
            "variables": {"BOT_TOKEN": bot_token}
        }
    }
    response = requests.post(
        "https://backboard.railway.app/graphql/v2",
        headers=headers,
        json={"query": query, "variables": variables}
    )
    return response.json()

def create_github_repo(name, files_content):
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    data = {"name": name, "private": False, "auto_init": False}
    response = requests.post("https://api.github.com/user/repos", headers=headers, json=data)
    repo_data = response.json()

    if 'full_name' in repo_data:
        for file_path, content in files_content.items():
            encoded_content = base64.b64encode(content.encode()).decode()
            file_data = {"message": f"Add {file_path}", "content": encoded_content}
            requests.put(
                f"https://api.github.com/repos/{repo_data['full_name']}/contents/{file_path}",
                headers=headers,
                json=file_data
            )
        return repo_data['html_url']
    return None

# ========== أوامر المطور ==========
@client.on(events.NewMessage(pattern='/gencode'))
async def gen_code(event):
    if event.sender_id!= DEVELOPER_ID:
        return await event.respond("❌ الامر ده للمطور فقط")

    code = generate_code()
    codes = load_codes()
    codes["codes"][code] = {"used": False, "user_id": None, "bot_name": None}
    save_codes(codes)

    await event.respond(
        f"✅ تم توليد كود تفعيل جديد:\n\n"
        f"`{code}`\n\n"
        f"السعر: 10$ مدى الحياة\n"
        f"صالح لبوت واحد فقط"
    )

@client.on(events.NewMessage(pattern='/codes'))
async def list_codes(event):
    if event.sender_id!= DEVELOPER_ID:
        return

    codes = load_codes()
    used = sum(1 for c in codes["codes"].values() if c["used"])
    unused = len(codes["codes"]) - used

    text = f"📊 احصائيات الاكواد:\n\n"
    text += f"✅ مستخدم: {used}\n"
    text += f"🟢 متاح: {unused}\n"
    text += f"💰 الارباح: {used * 10}$\n\n"
    text += "الاكواد المتاحة:\n"

    for code, data in codes["codes"].items():
        if not data["used"]:
            text += f"`{code}`\n"

    await event.respond(text)

# ========== أوامر العميل ==========
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    sender = await event.get_sender()
    await event.respond(
        f"أهلا {sender.first_name} 👋\n\n"
        "🏭 **مصنع البوتات المتطور Pro** 🤖\n\n"
        "💎 مميزات البوتات:\n"
        "• حماية اشتراك اجباري متقدمة\n"
        "• لوحة تحكم احترافية\n"
        "• احصائيات لحظية\n"
        "• نسخ احتياطي تلقائي\n"
        "• سرعة صاروخية\n"
        "• دعم فني 24/7\n\n"
        "💰 السعر: 10$ مدى الحياة\n\n"
        "ارسل /newbot عشان تبدأ\n"
        "للشراء تواصل مع المطور: @nashrmsnah",
        buttons=[[Button.url("💬 تواصل مع المطور", "https://t.me/nashrmsnah")]]
    )

@client.on(events.NewMessage(pattern='/newbot'))
async def newbot(event):
    user_id = event.sender_id
    pending[user_id] = {"step": "code"}
    await event.respond(
        "🔐 **تفعيل المصنع**\n\n"
        "ارسل كود التفعيل اللي اشتريته من المطور\n\n"
        "⚠️ كل كود صالح لبوت واحد فقط مدى الحياة\n"
        "💰 السعر: 10$\n\n"
        "لو معندكش كود تواصل مع @nashrmsnah"
    )

@client.on(events.NewMessage)
async def handle_message(event):
    user_id = event.sender_id

    if user_id not in pending:
        return

    step = pending[user_id]["step"]

    if step == "code":
        code = event.text.strip().upper()
        codes = load_codes()

        if code not in codes["codes"]:
            return await event.respond("❌ كود غلط. اتأكد من الكود او تواصل مع المطور")

        if codes["codes"][code]["used"]:
            return await event.respond("❌ الكود ده مستخدم قبل كده")

        # تفعيل الكود
        codes["codes"][code]["used"] = True
        codes["codes"][code]["user_id"] = user_id
        save_codes(codes)

        pending[user_id]["code"] = code
        pending[user_id]["step"] = "token"
        await event.respond("✅ تم تفعيل الكود بنجاح!\n\nابعت توكن البوت من @BotFather")

    elif step == "token":
        pending[user_id]["token"] = event.text
        pending[user_id]["step"] = "admin_id"
        await event.respond("تمام ✅\nابعت ايدي الادمن بتاع البوت")

    elif step == "admin_id":
        try:
            pending[user_id]["admin_id"] = int(event.text)
            pending[user_id]["step"] = "dev_username"
            await event.respond("تمام ✅\nابعت يوزر المطور بدون @")
        except:
            await event.respond("الايدي لازم يكون رقم بس")

    elif step == "dev_username":
        pending[user_id]["dev_username"] = event.text.replace("@", "")
        pending[user_id]["step"] = "channels"
        await event.respond("تمام ✅\nابعت القنوات الاجبارية\nمثال: channel1,channel2")

    elif step == "channels":
        channels = [ch.strip().replace("@", "") for ch in event.text.split(",")]
        pending[user_id]["channels"] = channels
        msg = await event.respond("⚙️ جاري بناء البوت المتطور... ⏳")

        try:
            # 1. تحميل القالب المتطور
            response = requests.get(BOT_TEMPLATE_URL)
            bot_code = response.text

            # 2. تبديل البيانات
            bot_code = re.sub(r'BOT_TOKEN\s*=\s*["\'].*?["\']', 'BOT_TOKEN = os.getenv("BOT_TOKEN")', bot_code)
            bot_code = re.sub(r'ADMIN_ID\s*=\s*\d+', f'ADMIN_ID = {pending[user_id]["admin_id"]}', bot_code)
            bot_code = re.sub(r'DEVELOPER_USERNAME\s*=\s*["\'].*?["\']', f'DEVELOPER_USERNAME = "{pending[user_id]["dev_username"]}"', bot_code)
            bot_code = re.sub(r'REQUIRED_CHANNELS\s*=\s*\[.*?\]', f'REQUIRED_CHANNELS = {pending[user_id]["channels"]}', bot_code)

            # 3. انشاء ملفات البوت
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            bot_name = f"probot-{random_suffix}"

            files = {
                'main.py': bot_code,
                'requirements.txt': 'telethon==1.36.0\nrequests==2.31.0\naiohttp==3.9.1\ncryptography==41.0.7\npycryptodome==3.19.0\napscheduler==3.10.4',
                'Procfile': 'worker: python main.py',
                'runtime.txt': 'python-3.11.9',
                'database.json': '{}',
                'sessions_backup.json': '{}',
                'config.json': json.dumps({
                    "license": pending[user_id]["code"],
                    "activated": True,
                    "plan": "PRO_LIFETIME"
                })
            }

            # 4. رفع على GitHub
            repo_url = create_github_repo(bot_name, files)

            if repo_url:
                # 5. انشاء مشروع Railway
                project = create_railway_project(bot_name, pending[user_id]["token"])
                project_id = project.get('data', {}).get('projectCreate', {}).get('id', 'unknown')

                # تحديث الكود بالبوت
                codes = load_codes()
                codes["codes"][pending[user_id]["code"]]["bot_name"] = bot_name
                save_codes(codes)

                await msg.edit(
                    f"✅ **تم انشاء البوت Pro بنجاح!**\n\n"
                    f"🏷️ الاسم: `{bot_name}`\n"
                    f"🔐 كود التفعيل: `{pending[user_id]['code']}`\n"
                    f"💎 الخطة: PRO مدى الحياة\n\n"
                    f"🚀 Railway: https://railway.app/project/{project_id}\n\n"
                    f"⚡ البوت شغال دلوقتي بكل المميزات!"
                )
            else:
                await msg.edit("❌ فشل انشاء الريبو. اتأكد من GITHUB_TOKEN")

        except Exception as e:
            await msg.edit(f"❌ حصل خطأ: {str(e)}")

        del pending[user_id]

print("Factory Bot Pro Started!")
client.run_until_disconnected()
