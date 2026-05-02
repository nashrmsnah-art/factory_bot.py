import os
import json
import asyncio
from datetime import datetime
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
RAILWAY_API_TOKEN = os.getenv('RAILWAY_API_TOKEN')
GITHUB_USERNAME = 'nashrmsnah-art'
DEVELOPER_ID = 154919127 # ايديك انت @Devazf
DEVELOPER_USERNAME = "Devazf"
DB_FILE = 'database.json'
BOT_PRICE = 10
BOT_TEMPLATE_URL = 'https://github.com/nashrmsnah-art/factory_bot.py/blob/835c615afc374b1da645ddf3b747cc9f61da3033/bot-template'

client = TelegramClient('factory_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
pending = {}

# ========== قاعدة البيانات ==========
def load_db():
    try:
        if not os.path.exists(DB_FILE):
            with open(DB_FILE, 'w') as f:
                json.dump({"codes": {}, "bots": {}}, f)
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    except:
        return {"codes": {}, "bots": {}}

def save_db(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def generate_code():
    return 'FACTORY-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

# ========== دوال Railway API ==========
def create_railway_project(name, bot_token, admin_id):
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
    variables = {"input": {"name": name}}

    response = requests.post(
        "https://backboard.railway.app/graphql/v2",
        headers=headers,
        json={"query": query, "variables": variables}
    )
    project_data = response.json()

    if 'data' not in project_data:
        return {"error": "فشل انشاء المشروع"}

    project_id = project_data['data']['projectCreate']['id']

    # ضيف Variables
    variables_list = [
        {"name": "BOT_TOKEN", "value": bot_token},
        {"name": "ADMIN_ID", "value": str(admin_id)},
        {"name": "DEVELOPER_ID", "value": str(DEVELOPER_ID)} # المطور يقدر يتحكم
    ]

    for var in variables_list:
        var_query = """
        mutation($input: VariableUpsertInput!) {
            variableUpsert(input: $input) { id }
        }
        """
        var_variables = {
            "input": {
                "projectId": project_id,
                "name": var["name"],
                "value": var["value"]
            }
        }
        requests.post(
            "https://backboard.railway.app/graphql/v2",
            headers=headers,
            json={"query": var_query, "variables": var_variables}
        )

    return project_data

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

# ========== لوحة تحكم المطور ==========
@client.on(events.NewMessage(pattern='/devpanel|/dev'))
async def dev_panel(event):
    if event.sender_id!= DEVELOPER_ID:
        return

    db = load_db()
    total_codes = len(db["codes"])
    used_codes = sum(1 for c in db["codes"].values() if c["used"])
    total_bots = len(db["bots"])

    await event.respond(
        f"👑 **لوحة تحكم المطور**\n\n"
        f"📊 **احصائيات المصنع:**\n"
        f"• اجمالي الاكواد: {total_codes}\n"
        f"• الاكواد المستخدمة: {used_codes}\n"
        f"• الاكواد المتاحة: {total_codes - used_codes}\n"
        f"• البوتات المصنعة: {total_bots}\n"
        f"• الارباح: {used_codes * BOT_PRICE}$\n\n"
        f"اختر امر:",
        buttons=[
            [Button.inline("🔑 توليد كود", b"gen_code"), Button.inline("📋 الاكواد", b"list_codes")],
            [Button.inline("🤖 البوتات المصنعة", b"list_bots"), Button.inline("📊 احصائيات", b"factory_stats")],
            [Button.inline("📢 اذاعة للمصنع", b"factory_broadcast")],
            [Button.inline("🗑️ حذف بوت", b"delete_bot")]
        ]
    )

@client.on(events.CallbackQuery(pattern=b"gen_code"))
async def gen_code_cb(event):
    if event.sender_id!= DEVELOPER_ID:
        return
    code = generate_code()
    db = load_db()
    db["codes"][code] = {"used": False, "user_id": None, "bot_name": None, "created_at": str(asyncio.get_event_loop().time())}
    save_db(db)
    await event.answer(f"✅ تم توليد كود جديد", alert=True)
    await event.edit(f"🔑 **كود جديد:**\n\n`{code}`\n\n💰 السعر: {BOT_PRICE}$\n⏰ صالح مدى الحياة", buttons=[[Button.inline("🔙 رجوع", b"back_dev")]])

@client.on(events.CallbackQuery(pattern=b"list_codes"))
async def list_codes_cb(event):
    if event.sender_id!= DEVELOPER_ID:
        return
    db = load_db()
    text = "📋 **كل الاكواد:**\n\n"
    for code, data in db["codes"].items():
        status = "✅ مستخدم" if data["used"] else "🟢 متاح"
        bot = f" | {data['bot_name']}" if data['bot_name'] else ""
        text += f"`{code}` - {status}{bot}\n"

    await event.edit(text[:4000], buttons=[[Button.inline("🔙 رجوع", b"back_dev")]])

@client.on(events.CallbackQuery(pattern=b"list_bots"))
async def list_bots_cb(event):
    if event.sender_id!= DEVELOPER_ID:
        return
    db = load_db()
    if not db["bots"]:
        return await event.answer("❌ مفيش بوتات مصنعة لسه", alert=True)

    text = "🤖 **البوتات المصنعة:**\n\n"
    for bot_name, data in db["bots"].items():
        text += f"• **{bot_name}**\n"
        text += f" 👤 المالك: {data['owner_id']}\n"
        text += f" 🔑 الكود: `{data['code']}`\n"
        text += f" 📅 التاريخ: {data['created_at']}\n\n"

    await event.edit(text[:4000], buttons=[[Button.inline("🔙 رجوع", b"back_dev")]])

@client.on(events.CallbackQuery(pattern=b"back_dev"))
async def back_dev(event):
    if event.sender_id!= DEVELOPER_ID:
        return
    await dev_panel(event)

# ========== أوامر العميل ==========
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    if event.sender_id == DEVELOPER_ID:
        return await dev_panel(event)

    await event.respond(
        f"🏭 **مصنع البوتات Pro** 🤖\n\n"
        "💎 **مميزات البوتات:**\n"
        "• لوحة تحكم كاملة للادمن + المطور\n"
        "• اشتراك اجباري متطور\n"
        "• احصائيات لحظية\n"
        "• اذاعة بالصور والازرار\n"
        "• نسخ احتياطي تلقائي\n"
        "• نظام حظر/الغاء حظر\n\n"
        f"💰 **السعر:** {BOT_PRICE}$ مدى الحياة\n\n"
        "ارسل /newbot للبدء\n"
        f"للشراء: @{DEVELOPER_USERNAME}",
        buttons=[[Button.url("💬 تواصل مع المطور", f"https://t.me/{DEVELOPER_USERNAME}")]]
    )

@client.on(events.NewMessage(pattern='/newbot'))
async def newbot(event):
    user_id = event.sender_id
    pending[user_id] = {"step": "code"}
    await event.respond(f"🔐 ارسل كود التفعيل\n\nلو معندكش كود: @{DEVELOPER_USERNAME}")

@client.on(events.NewMessage)
async def handle_message(event):
    user_id = event.sender_id
    if user_id not in pending:
        return

    step = pending[user_id]["step"]
    db = load_db()

    if step == "code":
        code = event.text.strip().upper()
        if code not in db["codes"]:
            return await event.respond("❌ كود غلط")
        if db["codes"][code]["used"]:
            return await event.respond("❌ الكود مستخدم")

        db["codes"][code]["used"] = True
        db["codes"][code]["user_id"] = user_id
        save_db(db)
        pending[user_id]["code"] = code
        pending[user_id]["step"] = "token"
        await event.respond("✅ تم التفعيل!\n\nابعت توكن البوت من @BotFather")

    elif step == "token":
        pending[user_id]["token"] = event.text
        pending[user_id]["step"] = "admin_id"
        await event.respond("تمام ✅\nابعت ايديك انت - ده هيكون ايدي ادمن البوت الجديد")

    elif step == "admin_id":
        try:
            pending[user_id]["admin_id"] = int(event.text)
            pending[user_id]["step"] = "channels"
            await event.respond("تمام ✅\nابعت القنوات الاجبارية\nمثال: channel1,channel2\nاو اكتب none")
        except:
            await event.respond("الايدي لازم رقم")

    elif step == "channels":
        channels = [] if event.text.lower() == 'none' else [ch.strip().replace("@", "") for ch in event.text.split(",")]
        pending[user_id]["channels"] = channels
        msg = await event.respond("⚙️ جاري بناء البوت المتطور... ⏳")

        try:
            response = requests.get(BOT_TEMPLATE_URL)
            bot_code = response.text

            # تبديل البيانات + اضافة ايدي المطور
            bot_code = re.sub(r'ADMIN_ID\s*=\s*\d+', f'ADMIN_ID = int(os.getenv("ADMIN_ID", "{pending[user_id]["admin_id"]}"))', bot_code)
            bot_code = re.sub(r'DEVELOPER_ID\s*=\s*\d+', f'DEVELOPER_ID = int(os.getenv("DEVELOPER_ID", "{DEVELOPER_ID}"))', bot_code)
            bot_code = re.sub(r'DEVELOPER_USERNAME\s*=\s*["\'].*?["\']', f'DEVELOPER_USERNAME = "{DEVELOPER_USERNAME}"', bot_code)
            bot_code = re.sub(r'REQUIRED_CHANNELS\s*=\s*\[.*?\]', f'REQUIRED_CHANNELS = {pending[user_id]["channels"]}', bot_code)
            bot_code = re.sub(r'LICENSE_CODE\s*=\s*["\'].*?["\']', f'LICENSE_CODE = "{pending[user_id]["code"]}"', bot_code)

            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            bot_name = f"probot-{random_suffix}"

            files = {
                'main.py': bot_code,
                'requirements.txt': 'telethon==1.36.0\nrequests==2.31.0\naiohttp==3.9.1\ncryptography==41.0.7\npycryptodome==3.19.0\napscheduler==3.10.4',
                'Procfile': 'worker: python main.py',
                'runtime.txt': 'python-3.11.9',
                'database.json': json.dumps({"users": {}, "stats": {"start_date": ""}}),
                'config.json': json.dumps({"license": pending[user_id]["code"], "plan": "PRO_LIFETIME", "owner": user_id})
            }

            repo_url = create_github_repo(bot_name, files)

            if repo_url:
                project = create_railway_project(bot_name, pending[user_id]["token"], pending[user_id]["admin_id"])

                if "error" in project:
                    return await msg.edit(f"❌ فشل Railway: {project['error']}")

                project_id = project.get('data', {}).get('projectCreate', {}).get('id', 'unknown')

                # حفظ البوت في قاعدة بيانات المصنع
                db = load_db()
                db["codes"][pending[user_id]["code"]]["bot_name"] = bot_name
                db["bots"][bot_name] = {
                    "owner_id": user_id,
                    "code": pending[user_id]["code"],
                    "repo": repo_url,
                    "project_id": project_id,
                    "created_at": str(datetime.now().date())
                }
                save_db(db)

                await msg.edit(
                    f"✅ **تم انشاء البوت Pro بنجاح!**\n\n"
                    f"🏷️ الاسم: `{bot_name}`\n"
                    f"🔐 الكود: `{pending[user_id]['code']}`\n"
                    f"💎 الخطة: PRO مدى الحياة\n\n"
                    f"⚡ **انت الادمن:** ارسل /admin في البوت\n"
                    f"👑 **المطور @{DEVELOPER_USERNAME}** يقدر يتحكم برضو"
                )
            else:
                await msg.edit("❌ فشل GitHub. اتأكد من GITHUB_TOKEN")

        except Exception as e:
            await msg.edit(f"❌ خطأ: {str(e)}")

        del pending[user_id]

print("Factory Bot Pro Started!")
client.run_until_disconnected()
