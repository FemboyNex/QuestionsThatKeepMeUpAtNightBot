import discord
from discord.ext import commands, tasks
import random
import json
import os
from dotenv import load_dotenv
import re

load_dotenv()
TOKEN = os.getenv("TOKEN")
ADMINS = [int(x.strip()) for x in os.getenv("ADMINS", "").split(",") if x.strip()]

MAXLENGTH = 500

BLACKLIST_PATTERN = re.compile(
    r"(`|\$\(.*\)|;|&&|\|\||__import__|import\s+|exec\(|eval\(|subprocess|os\.|pickle\.|open\(|socket\.)",
    re.IGNORECASE
)

intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True 

bot = commands.Bot(command_prefix="!", intents=intents)

if os.path.exists("questions.json"):
    with open("questions.json", "r", encoding="utf-8") as f:
        questions = json.load(f)
else:
    questions = []

if os.path.exists("requests.json"):
    with open("requests.json", "r", encoding="utf-8") as f:
        requests = json.load(f)
else:
    requests = []

if os.path.exists("guilds.json"):
    with open("guilds.json", "r", encoding="utf-8") as f:
        guild_channels = json.load(f)
else:
    guild_channels = {}

def save_guilds():
    with open("guilds.json", "w", encoding="utf-8") as f:
        json.dump(guild_channels, f, indent=4)

def save_requests():
    with open("requests.json", "w", encoding="utf-8") as f:
        json.dump(requests, f, indent=4)

def save_questions():
    with open("questions.json", "w", encoding="utf-8") as f:
        json.dump(questions, f, indent=4)

def sanitizetext(s: str) -> str | None:
    s = s.strip()
    if not s:
        return None
    if len(s) > MAXLENGTH:
        return None
    if "\x00" in s:
        return None
    if BLACKLIST_PATTERN.search(s):
        return None
    s = discord.utils.escape_markdown(s)
    return s

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}!")
    send_question.start()

@bot.command()
@commands.has_permissions(administrator=True)
async def setquestionchannel(ctx, channel_id: int):
    guild_channels[str(ctx.guild.id)] = channel_id
    save_guilds()
    await ctx.send(f"Set this server's hourly question channel to <#{channel_id}>")

@bot.command()
async def requestquestion(ctx, *, question: str):
    safe = sanitizetext(question)
    if safe is None:
        await ctx.send(f"{ctx.author.name}, your question was rejected for safety reasons. Keep it under {MAXLENGTH} characters and avoid code-like content.")
        return

    requests.append({"text": safe, "user": str(ctx.author), "username": ctx.author.name})
    save_requests()
    await ctx.send(f"Your question request has been noted, {ctx.author.name}. An admin will review it.")

@bot.command()
async def addquestion(ctx, *, question: str):
    if ctx.author.id in ADMINS:
        safe = sanitizetext(question)
        if safe is None:
            await ctx.send("no.")
            return
        questions.append({"text": question, "user": None})
        save_questions()
        await ctx.send(f"Question added.")
    else:
        await ctx.send(f"You do not have permission to use this command, {ctx.author.name}.")
        

@tasks.loop(hours=1)
async def send_question():
    for guild_id, channel_id in guild_channels.items():
        guild = bot.get_guild(int(guild_id))
        if guild:
            channel = guild.get_channel(int(channel_id))
            if channel and questions:
                q = random.choice(questions)
                requester = q["user"] if q["user"] else "Admin"
                await channel.send(f"**Hourly question that keeps me up at night:** {q['text']}\nQuestion requested by: {requester}")

bot.run(TOKEN)