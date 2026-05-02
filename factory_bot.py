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
            "variables": {
                "BOT_TOKEN": bot_token
            }
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
    
    data = {
        "name": name,
        "private": False,
        "auto_init": False
    }
    
    response = requests.post("https://api.github.com/user/repos", headers=headers, json=data)
    repo_data = response.json()
    
    if 'full_name' in repo_data:
        for file_path, content in files_content.items():
            encoded_content = base64.b64encode(content.encode()).decode()
            file_data = {
                "message": f"Add {file_path}",
                "content": encoded_content
            }
            requests.put(
                f"https://api.github.com/repos/{repo_data['full_name']}/contents/{file_path}",
                headers=headers,
                json=file_data
            )
        return repo_data['html_url']
    return None

# ========== أوامر البوت ==========
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    sender = await event.get_sender()
    await event.respond(
        f"أهلا {sender.first_name} 👋\n\n"
        "انا مصنع بوتات التليجرام 🤖\n"
        "ارسل /newbot عشان تبدأ انشاء بوت جديد"
    )

@client.on(events.NewMessage(pattern='/newbot'))
async def newbot(event):
    user_id = event.sender_id
    pending[user_id] = {"step": "token"}
    await event.respond("تمام! ابعت توكن البوت اللي عايز تنشئه من @BotFather")

@client.on(events.NewMessage)
async def handle_message(event):
    user_id = event.sender_id
    
    if user_id not in pending:
        return
    
    step = pending[user_id]["step"]
    
    if step == "token":
        pending[user_id]["token"] = event.text
        pending[user_id]["step"] = "admin_id"
        await event.respond("تمام ✅\nابعت ايدي الادمن بتاع البوت")
    
    elif step == "admin_id":
        try:
            pending[user_id]["admin_id"] = int(event.text)
            pending[user_id]["step"] = "dev_username"
            await event.respond("تمام ✅\nابعت يوزر المطور بدون @")
        except:
            await event.respond("الايدي لازم يكون رقم بس، جرب تاني")
    
    elif step == "dev_username":
        pending[user_id]["dev_username"] = event.text.replace("@", "")
        pending[user_id]["step"] = "channels"
        await event.respond("تمام ✅\nابعت القنوات الاجبارية\nمثال: channel1,channel2")
    
    elif step == "channels":
        channels = [ch.strip().replace("@", "") for ch in event.text.split(",")]
        pending[user_id]["channels"] = channels
        msg = await event.respond("جاري انشاء البوت... ⏳")
        
        try:
            # 1. تحميل القالب
            response = requests.get(BOT_TEMPLATE_URL)
            bot_code = response.text
            
            # 2. تبديل البيانات بـ regex
            bot_code = re.sub(r'BOT_TOKEN\s*=\s*["\'].*?["\']', 'BOT_TOKEN = os.getenv("BOT_TOKEN")', bot_code)
            bot_code = re.sub(r'ADMIN_ID\s*=\s*\d+', f'ADMIN_ID = {pending[user_id]["admin_id"]}', bot_code)
            bot_code = re.sub(r'DEVELOPER_USERNAME\s*=\s*["\'].*?["\']', f'DEVELOPER_USERNAME = "{pending[user_id]["dev_username"]}"', bot_code)
            bot_code = re.sub(r'REQUIRED_CHANNELS\s*=\s*\[.*?\]', f'REQUIRED_CHANNELS = {pending[user_id]["channels"]}', bot_code)
            
            # 3. انشاء ملفات البوت
            random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            bot_name = f"bot-{random_suffix}"
            
            files = {
                'main.py': bot_code,
                'requirements.txt': 'telethon==1.36.0\nrequests==2.31.0\naiohttp==3.9.1\ncryptography==41.0.7\npycryptodome==3.19.0',
                'Procfile': 'worker: python main.py',
                'runtime.txt': 'python-3.11.9',
                'database.json': '{}',
                'sessions_backup.json': '{}'
            }
            
            # 4. رفع على GitHub
            repo_url = create_github_repo(bot_name, files)
            
            if repo_url:
                # 5. انشاء مشروع Railway
                project = create_railway_project(bot_name, pending[user_id]["token"])
                project_id = project.get('data', {}).get('projectCreate', {}).get('id', 'unknown')
                
                await msg.edit(
                    f"✅ تم انشاء وتشغيل البوت بنجاح!\n\n"
                    f"📦 الريبو: {repo_url}\n"
                    f"🚀 Railway: https://railway.app/project/{project_id}\n\n"
                    f"البوت شغال دلوقتي! جربه"
                )
            else:
                await msg.edit("❌ فشل انشاء الريبو. اتأكد من GITHUB_TOKEN في Variables")
            
        except Exception as e:
            await msg.edit(f"❌ حصل خطأ: {str(e)}")
        
        del pending[user_id]

print("Factory Bot Started!")
client.run_until_disconnected()
