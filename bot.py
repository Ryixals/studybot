import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta

from config import TOKEN, SUBJECTS, COMMAND_COOLDOWN, COMMAND_MAX_MINUTES, RECAP_WINDOW_HOURS, RECAP_MESSAGES_PER_CHANNEL
from database import Database


class StudyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database()

    async def close(self):
        self.db.close()
        await super().close()

    async def setup_hook(self):
        try:
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")


bot = StudyBot()


SUBJECT_CHOICES = [
    app_commands.Choice(name=subject, value=subject)
    for subject in SUBJECTS.keys()
]


@bot.event
async def on_ready():
    print(f"✅ {bot.user} has connected to Discord!")
    print(f"📊 Bot is in {len(bot.guilds)} guild(s)")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Your study progress 📚"))
    await process_recap_messages()


def format_time(minutes: int) -> str:
    hours = minutes // 60
    mins = minutes % 60

    if hours > 0 and mins > 0:
        return f"{hours} hour(s) {mins} minute(s)"
    elif hours > 0:
        return f"{hours} hour(s)"
    else:
        return f"{mins} minute(s)"


async def process_add_command(channel: discord.TextChannel, user: discord.User, subject_name: str, minutes: int):
    if minutes > COMMAND_MAX_MINUTES:
        await channel.send(f"❌ <@{user.id}> Cannot add more than {COMMAND_MAX_MINUTES} minutes at once.")
        return

    subject_value = None
    for name in SUBJECTS.keys():
        if name.lower() == subject_name.lower():
            subject_value = name
            break

    if not subject_value:
        await channel.send(f"❌ <@{user.id}> Invalid subject. Available: {', '.join(SUBJECTS.keys())}")
        return

    success, message = bot.db.add_study_time(user.id, str(user), subject_value, minutes)

    if success:
        await channel.send(f"✅ <@{user.id}> Added **{format_time(minutes)}** to **{subject_value}**")
    else:
        await channel.send(f"❌ <@{user.id}> {message}")


async def process_check_command(channel: discord.TextChannel, user: discord.User):
    progress = bot.db.get_user_progress(user.id, str(user))
    total_study_time = 0

    if not progress:
        await channel.send(f"📊 <@{user.id}> No study data yet. Use `r;add` to start tracking!")
        return

    lines = [f"**{user.display_name}'s Progress**"]
    for subject, minutes in progress:
        if minutes > 0:
            lines.append(f"• {subject}: {format_time(minutes)}")
            total_study_time += minutes

    lines.append(f"\n**Total:** {format_time(total_study_time)}")
    await channel.send("\n".join(lines))


async def process_leaderboard_command(channel: discord.TextChannel):
    leaderboard = bot.db.get_leaderboard()

    if not leaderboard:
        await channel.send("🏆 No data yet. Be the first to study!")
        return

    medals = ["🥇", "🥈", "🥉"]
    lines = ["**🏆 Leaderboard**"]

    for i, (username, total_minutes) in enumerate(leaderboard):
        if i < 3:
            prefix = medals[i]
        else:
            prefix = f"{i+1}."
        lines.append(f"{prefix} **{username}** - {format_time(total_minutes)}")

    await channel.send("\n".join(lines))

async def process_help(channel: discord.TextChannel):
    lines = [
        "**❓ Help**",
        "Coming soon..."
    ]

    await channel.send("\n".join(lines))

async def process_recap_messages():
    last_id = bot.db.get_last_processed_message_id()
    new_last_id = last_id

    for guild in bot.guilds:
        for channel in guild.text_channels:
            if not channel.permissions_for(guild.me).read_message_history:
                continue

            try:
                after = None
                if last_id == 0:
                    after = datetime.now() - timedelta(hours=RECAP_WINDOW_HOURS)

                messages = []
                async for msg in channel.history(limit=RECAP_MESSAGES_PER_CHANNEL, after=after, oldest_first=True):
                    if msg.id > last_id:
                        messages.append(msg)
                    if msg.id > new_last_id:
                        new_last_id = msg.id

                for msg in messages:
                    content = msg.content.strip()
                    if not content.lower().startswith("r;"):
                        continue

                    cmd_part = content[2:].lstrip("/").strip()
                    if not cmd_part:
                        continue

                    parts = cmd_part.split()
                    command = parts[0].lower()

                    if command == "add" and len(parts) >= 3:
                        subject_name = parts[1]
                        try:
                            minutes = int(parts[2])
                            await process_add_command(channel, msg.author, subject_name, minutes)
                        except ValueError:
                            await channel.send(f"❌ <@{msg.author.id}> Invalid minutes value.")

                    elif command == "remove" and len(parts) >= 3:
                        subject_name = parts[1]
                        try:
                            minutes = int(parts[2])
                            await process_remove_command(channel, msg.author, subject_name, minutes)
                        except ValueError:
                            await channel.send(f"❌ <@{msg.author.id}> Invalid minutes value.")

                    elif command == "check":
                        await process_check_command(channel, msg.author)

                    elif command == "leaderboard":
                        await process_leaderboard_command(channel)

                    elif command == "help":
                        await process_help(channel)

                    else:
                        await channel.send(f"❌ <@{msg.author.id}> Unknown command. Use `r;add`, `r;remove`, `r;check`, or `r;leaderboard`.")

            except Exception as e:
                print(f"Error processing channel {channel.name} in guild {guild.name}: {e}")

    if new_last_id > last_id:
        bot.db.set_last_processed_message_id(new_last_id)
        print(f"📥 Recap processed messages up to ID {new_last_id}")


async def process_remove_command(channel: discord.TextChannel, user: discord.User, subject_name: str, minutes: int):
    if minutes > COMMAND_MAX_MINUTES:
        await channel.send(f"❌ <@{user.id}> Cannot remove more than {COMMAND_MAX_MINUTES} minutes at once.")
        return

    subject_value = None
    for name in SUBJECTS.keys():
        if name.lower() == subject_name.lower():
            subject_value = name
            break

    if not subject_value:
        await channel.send(f"❌ <@{user.id}> Invalid subject. Available: {', '.join(SUBJECTS.keys())}")
        return

    success, message = bot.db.remove_study_time(user.id, subject_value, minutes)

    if success:
        await channel.send(f"✅ <@{user.id}> Removed **{format_time(minutes)}** from **{subject_value}**")
    else:
        await channel.send(f"❌ <@{user.id}> {message}")


@bot.tree.command(name="add", description="Add studying time to a subject")
@app_commands.describe(subject="Select the subject you studied", minutes="How many minutes to add (required)")
@app_commands.choices(subject=SUBJECT_CHOICES)
async def add_study_time(interaction: discord.Interaction, subject: app_commands.Choice[str], minutes: app_commands.Range[int, 1, COMMAND_MAX_MINUTES]):
    if minutes > COMMAND_MAX_MINUTES:
        await interaction.response.send_message(f"❌ Cannot add more than {COMMAND_MAX_MINUTES} minutes ({COMMAND_MAX_MINUTES//60} hours) at once.", ephemeral=True)
        return

    success, message = bot.db.add_study_time(interaction.user.id, str(interaction.user), subject.value, minutes)

    if success:
        embed = discord.Embed(title="✅ Study time added", description=f"Added **{format_time(minutes)}** to **{subject.name}**", color=SUBJECTS[subject.value], timestamp=datetime.now())
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"❌ {message}", ephemeral=True)


@bot.tree.command(name="check", description="Show your studying progress dashboard")
async def check_progress(interaction: discord.Interaction):
    await interaction.response.defer()

    progress = bot.db.get_user_progress(interaction.user.id, str(interaction.user))

    embed = discord.Embed(title="📊 Dashboard", description=f"**{interaction.user.display_name}'s** Progress Report", color=0xDCDCDC, timestamp=datetime.now())
    total_study_time = 0

    if not progress:
        embed.add_field(name="📚 No data yet", value="Start studying and use `/add` to track your time!", inline=False)
    else:
        max_minutes = max((minutes for _, minutes in progress), default=0)

        for subject, minutes in progress:
            if minutes > 0:
                bar_length = 20
                filled = int((minutes / max_minutes) * bar_length) if max_minutes > 0 else 0
                bar = "█" * filled + "░" * (bar_length - filled)
                embed.add_field(name=f"**{subject}**", value=f"`{bar}`\n{format_time(minutes)} total", inline=True)
                total_study_time += minutes

    embed.add_field(name="📈 Total progress", value=f"**{format_time(total_study_time)}** across all subjects", inline=False)
    embed.set_footer(text="Keep up the great work! 🎓")
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="leaderboard", description="Show the global study leaderboard")
async def show_leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()

    leaderboard_data = bot.db.get_leaderboard()

    embed = discord.Embed(title="🏆 Leaderboard", description="Top students across all subjects", color=0xDCDCDC, timestamp=datetime.now())

    if not leaderboard_data:
        embed.add_field(name="No data yet", value="Be the first to start studying and appear on the leaderboard! 🎯", inline=False)
    else:
        medals = ["🥇", "🥈", "🥉"]
        leaderboard_text = ""

        for i, (username, total_minutes) in enumerate(leaderboard_data):
            if i < 3:
                prefix = medals[i]
            else:
                prefix = f"**{i+1}.**"
            leaderboard_text += f"{prefix} **{username}** - {format_time(total_minutes)}\n"

        embed.add_field(name="Top students", value=leaderboard_text, inline=False)

    embed.set_footer(text="Study more to climb the ranks! 📈")

    await interaction.followup.send(embed=embed)


@bot.tree.command(name="remove", description="Remove studying time from a subject")
@app_commands.describe(subject="Select the subject", minutes="How many minutes to remove (required)")
@app_commands.choices(subject=SUBJECT_CHOICES)
async def remove_study_time(interaction: discord.Interaction, subject: app_commands.Choice[str], minutes: app_commands.Range[int, 1, COMMAND_MAX_MINUTES]):
    success, message = bot.db.remove_study_time(interaction.user.id, subject.value, minutes)

    if success:
        embed = discord.Embed(title="✅ Study time removed", description=f"Removed **{format_time(minutes)}** from **{subject.name}**", color=SUBJECTS[subject.value], timestamp=datetime.now())
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"❌ {message}", ephemeral=True)


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(f"⏰ Command on cooldown. Try again in {error.retry_after:.1f} seconds.", ephemeral=True)

    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)

    else:
        print(f"❌ Unexpected error: {error}")
        await interaction.response.send_message("❌ An unexpected error occurred. Please try again later.", ephemeral=True)


if __name__ == "__main__":
    bot.run(TOKEN)