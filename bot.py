import discord
import json
import os
from discord.ext import commands

# ============================================================
#  CONFIG — reads from Railway env vars or falls back to config.json
# ============================================================
TOKEN = os.environ.get("TOKEN")
BANNED_WORDS_ENV = os.environ.get("BANNED_WORDS")
WARN_LIMIT = int(os.environ.get("WARN_LIMIT", 3))
LOG_CHANNEL_ID = os.environ.get("LOG_CHANNEL_ID")
LOG_CHANNEL_ID = int(LOG_CHANNEL_ID) if LOG_CHANNEL_ID else None

# Fall back to config.json if no env vars set (local testing)
if not TOKEN:
    with open("config.json", "r") as f:
        config = json.load(f)
    TOKEN = config["token"]
    BANNED_WORDS = [w.lower() for w in config["banned_words"]]
    WARN_LIMIT = config.get("warn_limit", 3)
    LOG_CHANNEL_ID = config.get("log_channel_id")
else:
    BANNED_WORDS = [w.strip().lower() for w in BANNED_WORDS_ENV.split(",")] if BANNED_WORDS_ENV else []

# ── Users to greet — add their ID and a friendly message ──
GREET_USERS = {
    123456789012345678: "Hey! 👋 Great to see you! Hope you're having an amazing day! 😊",
    # Add more users below like this:
    # 987654321098765432: "Yo! What's up! 🔥",
}

# In-memory warning tracker: {user_id: warn_count}
warnings = {}

# ============================================================
#  BOT SETUP
# ============================================================
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ============================================================
#  HELPERS
# ============================================================
def contains_banned_word(content: str) -> str | None:
    lower = content.lower()
    for word in BANNED_WORDS:
        if word in lower:
            return word
    return None

async def log(guild: discord.Guild, message: str):
    if LOG_CHANNEL_ID:
        ch = guild.get_channel(LOG_CHANNEL_ID)
        if ch:
            await ch.send(message)

# ============================================================
#  EVENTS
# ============================================================
@bot.event
async def on_ready():
    print(f"✅ Logged in as {bot.user} — watching {len(BANNED_WORDS)} banned word(s).")

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    # ── Friendly greeting for specific users ──
    if message.author.id in GREET_USERS:
        await message.channel.send(GREET_USERS[message.author.id])

    # ── Banned word check ──
    trigger = contains_banned_word(message.content)

    if trigger:
        try:
            await message.delete()
        except discord.Forbidden:
            print("❌ Missing permission to delete messages.")
            return

        uid = message.author.id
        warnings[uid] = warnings.get(uid, 0) + 1
        count = warnings[uid]

        warn_msg = (
            f"⚠️ {message.author.mention}, your message was removed because it contained a banned word.\n"
            f"You have **{count}/{WARN_LIMIT}** warning(s)."
        )

        if count >= WARN_LIMIT:
            warn_msg += "\n🚨 You have reached the warning limit. A moderator will review your account."

        await message.channel.send(warn_msg, delete_after=10)

        await log(
            message.guild,
            f"🚫 **{message.author}** triggered word `{trigger}` in {message.channel.mention} "
            f"(warning {count}/{WARN_LIMIT})"
        )

    await bot.process_commands(message)

# ============================================================
#  MOD COMMANDS (admin only)
# ============================================================
def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator
    return commands.check(predicate)

@bot.command(name="warnings")
@is_admin()
async def check_warnings(ctx, member: discord.Member):
    count = warnings.get(member.id, 0)
    await ctx.send(f"⚠️ {member.mention} has **{count}** warning(s).")

@bot.command(name="clearwarnings")
@is_admin()
async def clear_warnings(ctx, member: discord.Member):
    warnings[member.id] = 0
    await ctx.send(f"✅ Warnings cleared for {member.mention}.")

@bot.command(name="addword")
@is_admin()
async def add_word(ctx, *, word: str):
    word = word.lower().strip()
    if word not in BANNED_WORDS:
        BANNED_WORDS.append(word)
        await ctx.send(f"✅ `{word}` added to the banned words list.")
    else:
        await ctx.send(f"ℹ️ `{word}` is already banned.")

@bot.command(name="removeword")
@is_admin()
async def remove_word(ctx, *, word: str):
    word = word.lower().strip()
    if word in BANNED_WORDS:
        BANNED_WORDS.remove(word)
        await ctx.send(f"✅ `{word}` removed from the banned words list.")
    else:
        await ctx.send(f"ℹ️ `{word}` wasn't in the list.")

@bot.command(name="listwords")
@is_admin()
async def list_words(ctx):
    if BANNED_WORDS:
        words = ", ".join(f"`{w}`" for w in BANNED_WORDS)
        await ctx.send(f"🚫 Banned words: {words}")
    else:
        await ctx.send("No banned words set.")

bot.run(TOKEN)
