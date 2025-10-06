import discord
from discord.ext import commands, tasks
import os
import requests
import json
from datetime import datetime
import pytz
import difflib
import subprocess
from flask import Flask
from threading import Thread
import asyncio

# ------------------ CONFIG ------------------
BOT_NAME = "IDK"
BOT_PREFIX = "!"
KSA_TZ = pytz.timezone("Asia/Riyadh")
LOGS_DIR = "logs"

DISCORD_BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
GROQ_API_KEY = os.environ["GROQ_API_KEY"]

# ------------------ DISCORD SETUP ------------------
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=BOT_PREFIX, intents=intents)

# ------------------ FLASK KEEP-ALIVE ------------------
app = Flask("")

@app.route("/")
def home():
    return "Bot is running!"

def run():
    app.run(host="0.0.0.0", port=8080)

Thread(target=run).start()

# ------------------ MEMORY ------------------
user_memory = {}  # store conversation history per user

def add_to_memory(username, message):
    if username not in user_memory:
        user_memory[username] = []
    user_memory[username].append(message)
    # Optional: summarize memory if > 20 messages
    if len(user_memory[username]) > 20:
        summary_prompt = "Summarize these messages briefly:\n" + "\n".join(user_memory[username])
        summary = ask_groq(summary_prompt, "")
        user_memory[username] = [summary]

def get_memory(username):
    return "\n".join(user_memory.get(username, []))

# ------------------ HELPERS ------------------
def is_bot_mentioned(message_content):
    ratio = difflib.SequenceMatcher(None, BOT_NAME.lower(), message_content.lower()).ratio()
    return BOT_NAME.lower() in message_content.lower() or ratio > 0.6

def save_log(username, user_msg, bot_msg):
    now = datetime.now(KSA_TZ)
    date_folder = f"{LOGS_DIR}/{now.strftime('%Y-%m-%d')}"
    if not os.path.exists(date_folder):
        os.makedirs(date_folder)
    timestamp = now.strftime("%H-%M-%S")
    filename = f"{date_folder}/{username}_{timestamp}.json"
    log_data = {
        "time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "user": user_msg,
        "bot": bot_msg
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(log_data, f, ensure_ascii=False, indent=4)
    # Git commit
    try:
        subprocess.run(["git", "add", filename])
        subprocess.run(["git", "commit", "-m", f"Log {username} {timestamp}"])
        subprocess.run(["git", "push"])
    except Exception as e:
        print("Git push failed:", e)

def ask_groq(prompt, user_history):
    """Call Groq API with dynamic length based on message size"""
    max_tokens = 80 if len(prompt.split()) <= 10 else 400
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
    data = {
        "prompt": f"You are a human-like AI named {BOT_NAME} with memory:\n{user_history}\n\nRespond naturally and thoughtfully: {prompt}",
        "max_output_tokens": max_tokens,
        "stream": True  # request streaming if supported
    }
    try:
        response = requests.post("https://api.groq.com/v1/complete", headers=headers, json=data, stream=True)
        if response.status_code == 200:
            bot_reply = ""
            for chunk in response.iter_lines():
                if chunk:
                    data_chunk = json.loads(chunk.decode("utf-8"))
                    bot_reply += data_chunk.get("completion", "")
            return bot_reply if bot_reply else "Sorry, I couldn't answer that."
        else:
            return "Groq API unreachable."
    except Exception as e:
        print("Groq error:", e)
        return "Error contacting Groq API."

# ------------------ DISCORD EVENTS ------------------
@bot.event
async def on_ready():
    print(f"{bot.user} is online!")

async def stream_send(channel, text):
    """Send message character by character to simulate typing"""
    message = await channel.send("...")
    displayed_text = ""
    for char in text:
        displayed_text += char
        await message.edit(content=displayed_text)
        await asyncio.sleep(0.03)  # typing speed
    return message

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if is_bot_mentioned(message.content):
        add_to_memory(str(message.author), message.content)
        user_history = get_memory(str(message.author))

        async with message.channel.typing():
            await asyncio.sleep(min(len(message.content) * 0.1, 5))  # realistic thinking

            bot_reply = ask_groq(message.content, user_history)

        await stream_send(message.channel, bot_reply)
        save_log(str(message.author), message.content, bot_reply)
        add_to_memory(str(message.author), bot_reply)

    await bot.process_commands(message)

# ------------------ RUN BOT ------------------
bot.run(DISCORD_BOT_TOKEN)
