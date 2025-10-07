import discord
from discord.ext import commands
import os
import requests
import json
from datetime import datetime
import pytz
import difflib
from flask import Flask
from threading import Thread
import asyncio

# ------------------ CONFIG ------------------
BOT_NAME = "IDK"
BOT_PREFIX = "!"
KSA_TZ = pytz.timezone("Asia/Riyadh")
LOGS_DIR = "logs"

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# ------------------ DISCORD SETUP ------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

# ------------------ KEEPALIVE ------------------
app = Flask("")

@app.route('/')
def home():
    return "✅ IDK Discord AI Chatbot is running."

def run():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run).start()

# ------------------ FUNCTIONS ------------------
def is_name_mentioned(content):
    """Detects if bot's name or close variations are mentioned."""
    content = content.lower()
    for word in content.split():
        if difflib.SequenceMatcher(None, word, BOT_NAME.lower()).ratio() > 0.6:
            return True
    return False

async def generate_ai_response(prompt):
    """Generates response using Groq AI."""
    try:
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.1-70b-versatile",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8
        }
        response = requests.post(url, headers=headers, json=data, timeout=25)
        result = response.json()
        text = result["choices"][0]["message"]["content"].strip()

        # Short question = short answer
        if len(prompt.split()) < 6:
            text = text.split(".")[0] + "."
        return text[:1999]  # Never exceed Discord limit
    except Exception as e:
        print(f"[ERROR] Groq API unreachable: {e}")
        return "⚠️ I'm having trouble reaching my brain right now."

def log_chat(user, user_msg, bot_msg):
    """Logs messages organized by day and time (KSA)."""
    now = datetime.now(KSA_TZ)
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H:%M:%S")
    folder_path = os.path.join(LOGS_DIR, date_str)
    os.makedirs(folder_path, exist_ok=True)
    file_path = os.path.join(folder_path, f"{user}.txt")
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(f"[{time_str}] {user}: {user_msg}\n")
        f.write(f"[{time_str}] {BOT_NAME}: {bot_msg}\n\n")

# ------------------ AI CHAT LOGIC ------------------
recent_convos = {}

@bot.event
async def on_ready():
    print(f"✅ {BOT_NAME} is online as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.strip()
    user_id = message.author.id
    channel = message.channel

    # Detect if talking to bot (by name or context)
    if is_name_mentioned(content):
        recent_convos[user_id] = True
    elif user_id not in recent_convos:
        return

    # Send typing effect (normal, no delay)
    async with channel.typing():
        response = await generate_ai_response(content)

    await message.reply(response, mention_author=False)
    log_chat(str(message.author), content, response)

    # End conversation keywords
    if any(word in content.lower() for word in ["bye", "stop", "thanks", "ok bye"]):
        recent_convos.pop(user_id, None)

# ------------------ START BOT ------------------
bot.run(DISCORD_BOT_TOKEN)
