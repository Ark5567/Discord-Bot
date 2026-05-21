import discord
import os
import random
from discord.ext import commands

# ============================================================
#  CONFIG — edit everything here
# ============================================================
TOKEN = os.environ.get("TOKEN")  # Set this in Railway variables

BANNED_WORDS = [
    "nigger",
    "nigga",
    # Add more words here
]

WARN_LIMIT = 999  # Warnings before the alert fires

LOG_CHANNEL_ID = None  # Set to a channel ID like 123456789 if you want logs

GREET_ENABLED = True  # Change to False to turn off all greetings

GREET_USERS = {
    1221109127359627405: [
        "Shut the fuck up Nigger",
        "Sub 3",
        "Fuck you",
        "Hentai Beater",
        "Monkey",
    ],
    1116351244424982578: [
        "What's up King",
        "You're the Goat!",
        "Holy Adam",
    ],
}

# ============================================================
#  BOT SETUP
# ============================================================
warnings = {}
intents = discord.Intents.all()
bot = commands.Bot(command_prefix=["!", "?"], intents=intents)

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

    # ── Random greeting for specific users ──
    if GREET_ENABLED and message.author.id in GREET_USERS:
        reply = random.choice(GREET_USERS[message.author.id])
        await message.reply(reply)

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

@bot.command(name="greet")
@is_admin()
async def toggle_greet(ctx):
    """!greet — toggle greetings on/off without editing the file."""
    global GREET_ENABLED
    GREET_ENABLED = not GREET_ENABLED
    status = "on 🟢" if GREET_ENABLED else "off 🔴"
    await ctx.send(f"Greetings turned {status}")

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


@bot.command(name="purge")
@is_admin()
async def purge(ctx, amount: int):
    """?purge <number> — delete that many messages in this channel."""
    await ctx.message.delete()
    deleted = await ctx.channel.purge(limit=amount)
    confirm = await ctx.send(f"🗑️ Deleted {len(deleted)} messages.")
    await confirm.delete(delay=5)

bot.run(TOKEN)
