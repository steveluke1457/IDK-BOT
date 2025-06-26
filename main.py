import discord
from discord.ext import commands
import os
import asyncio
import aiohttp
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

intents = discord.Intents.all()

bot = commands.Bot(command_prefix="!", intents=intents)

BAD_WORDS = ["badword1", "badword2", "exampleword"]  # Customize as needed
COUNT_CHANNEL_ID = 123456789012345678  # Replace with your counting channel ID

last_user = None
current_count = 1

# Load commands (Cogs) from commands folder
initial_extensions = [
    "commands.tickets",
    # Add other command files as you create them (e.g. commands.music)
]

if __name__ == "__main__":
    for extension in initial_extensions:
        bot.load_extension(extension)

# --- STARTUP ---
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game(name="with humans | !help"))

# --- MODERATION & COUNTING ---
@bot.event
async def on_message(message):
    global last_user, current_count

    if message.author.bot:
        return

    # AI Chat Reply - only respond if bot mentioned or message is a reply
    if bot.user.mentioned_in(message) or message.reference:
        reply = await get_groq_reply(message.content)
        if reply:
            await message.channel.send(reply)
        return

    # Moderation - bad word filter
    for word in BAD_WORDS:
        if word in message.content.lower():
            await message.delete()
            try:
                await message.author.send("⛔ Your message was removed due to inappropriate language.")
            except:
                pass
            return

    # Counting game channel logic
    if message.channel.id == COUNT_CHANNEL_ID:
        if message.author == last_user:
            await message.delete()
            return
        try:
            if int(message.content) == current_count:
                await message.add_reaction("✅")
                current_count += 1
                last_user = message.author
            else:
                await message.delete()
        except ValueError:
            await message.delete()
        return

    await bot.process_commands(message)

# --- GROQ AI CHAT FUNCTION ---
async def get_groq_reply(prompt):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=data, headers=headers) as resp:
            if resp.status == 200:
                response_json = await resp.json()
                return response_json["choices"][0]["message"]["content"]
            else:
                return None

# --- BASIC COMMANDS ---
@bot.command()
async def ping(ctx):
    await ctx.send("🏓 Pong!")

@bot.command()
async def hello(ctx):
    await ctx.send(f"Hi {ctx.author.mention}, I'm IDK BOT!")

# --- RUN THE BOT ---
bot.run(TOKEN)
