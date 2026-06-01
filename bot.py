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

PERIOD_CHOICES = [
    app_commands.Choice(name="Today", value="today"),
    app_commands.Choice(name="This Week", value="week"),
    app_commands.Choice(name="This Month", value="month"),
    app_commands.Choice(name="This Year", value="year"),
    app_commands.Choice(name="All Time", value="all"),
]


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
        embed = discord.Embed(title="✅ Study time added", description=f"Added **{format_time(minutes)}** to **{subject_value}**", color=SUBJECTS[subject_value], timestamp=datetime.now())
        embed.set_footer(text=f"Requested by {user.display_name}")
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        await channel.send(embed=embed)
    else:
        await channel.send(f"❌ <@{user.id}> {message}")

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
        embed = discord.Embed(title="✅ Study time removed", description=f"Removed **{format_time(minutes)}** from **{subject_value}**", color=SUBJECTS[subject_value], timestamp=datetime.now())
        embed.set_footer(text=f"Requested by {user.display_name}")
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        await channel.send(embed=embed)
    else:
        await channel.send(f"❌ <@{user.id}> {message}")

async def process_dashboard_command(channel: discord.TextChannel, user: discord.User, period: str = "all"):
    if period == "all":
        progress = bot.db.get_user_progress(user.id, str(user))
    else:
        progress = bot.db.get_user_progress_by_period(user.id, str(user), period)

    embed = discord.Embed(title="📊 Dashboard", description=f"**{user.display_name}'s** Progress Report ({period.replace('_', ' ').title()})", color=0xDCDCDC, timestamp=datetime.now())
    total_study_time = 0

    if not progress:
        embed.add_field(name="📚 No data yet", value="Start studying and use `/add` to track your time!", inline=False)
    else:
        max_minutes = max((minutes for _, minutes in progress), default=0)
        
        items = list(progress)
        for i in range(0, len(items), 2):
            field_value = ""
            subject1, minutes1 = items[i]
            if minutes1 > 0:
                bar_length = 20
                filled = int((minutes1 / max_minutes) * bar_length) if max_minutes > 0 else 0
                bar = "█" * filled + "░" * (bar_length - filled)
                field_value += f"**{subject1}**\n`{bar}`\n{format_time(minutes1)} total"
                total_study_time += minutes1
            
            if i + 1 < len(items):
                subject2, minutes2 = items[i + 1]
                if minutes2 > 0:
                    field_value += "\n\n"
                    bar_length = 20
                    filled = int((minutes2 / max_minutes) * bar_length) if max_minutes > 0 else 0
                    bar = "█" * filled + "░" * (bar_length - filled)
                    field_value += f"**{subject2}**\n`{bar}`\n{format_time(minutes2)} total"
                    total_study_time += minutes2
            
            embed.add_field(name="​", value=field_value, inline=True)

    embed.add_field(name="📈 Total progress", value=f"**{format_time(total_study_time)}** across all subjects", inline=False)
    embed.set_footer(text="Keep up the great work! 🎓")
    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)

    await channel.send(embed=embed)

async def process_leaderboard_command(channel: discord.TextChannel, period: str = "all"):
    if period == "all":
        leaderboard_data = bot.db.get_leaderboard()
    else:
        leaderboard_data = bot.db.get_leaderboard_by_period(period)

    embed = discord.Embed(title="🏆 Leaderboard", description=f"Top students ({period.replace('_', ' ').title()})", color=0xDCDCDC, timestamp=datetime.now())

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
    await channel.send(embed=embed)

async def process_timeline_command(channel: discord.TextChannel, user: discord.User, page: int = 1):
    per_page = 5
    offset = (page - 1) * per_page
    total = bot.db.count_user_sessions(user.id)
    sessions = bot.db.get_user_timeline(user.id, per_page, offset)

    if not sessions:
        await channel.send(f"📭 <@{user.id}> No study sessions recorded yet.")
        return

    embed = discord.Embed(title="📜 Study Timeline", description=f"Recent activity for **{user.display_name}** (Page {page})", color=0xDCDCDC, timestamp=datetime.now())
    for s in sessions:
        action = "➕ Added" if s["minutes"] > 0 else "➖ Removed"
        minutes_abs = abs(s["minutes"])
        time_str = s["timestamp"].strftime("%Y-%m-%d %H:%M")
        embed.add_field(name=f"{action} **{s['subject']}**", value=f"`{format_time(minutes_abs)}` at {time_str}", inline=False)
    embed.set_footer(text=f"Showing {offset+1}-{min(offset+per_page, total)} of {total} entries")
    await channel.send(embed=embed)

async def process_help_command(channel: discord.TextChannel):
    embed = discord.Embed(title="📚 Study Bot Help", description="Track your study time across subjects and compete with friends!", color=0xDCDCDC, timestamp=datetime.now())
    embed.add_field(name="**Online Commands**", value=(
        "`/add <subject> <minutes>` – Add study time\n"
        "`/remove <subject> <minutes>` – Remove study time\n"
        "`/dashboard [period]` – View your progress\n"
        "`/leaderboard [period]` – View the top students\n"
        "`/timeline` – View your previous study sessions\n"
        "`/help` – This message"
    ), inline=False)
    embed.add_field(name="**Offline Commands**", value=(
        "When the bot is offline, use `r;` prefix:\n"
        "`r;add subject minutes`  `r;remove subject minutes`\n"
        "`r;dashboard`  `r;leaderboard`  `r;timeline`  `r;help`"
    ), inline=False)
    embed.add_field(name="**Subjects**", value=", ".join(SUBJECTS.keys()), inline=False)
    embed.set_footer(text="Study hard, stay focused! 🎓")
    await channel.send(embed=embed)


@bot.tree.command(name="add", description="Add studying time to a subject")
@app_commands.describe(subject="Select the subject you studied", minutes="How many minutes to add (required)")
@app_commands.choices(subject=SUBJECT_CHOICES)
async def add_study_time(interaction: discord.Interaction, subject: app_commands.Choice[str], minutes: app_commands.Range[int, 1, COMMAND_MAX_MINUTES]):
    success, message = bot.db.add_study_time(interaction.user.id, str(interaction.user), subject.value, minutes)
    if success:
        embed = discord.Embed(title="✅ Study time added", description=f"Added **{format_time(minutes)}** to **{subject.name}**", color=SUBJECTS[subject.value], timestamp=datetime.now())
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"❌ {message}", ephemeral=True)

@bot.tree.command(name="remove", description="Remove studying time from a subject")
@app_commands.describe(subject="Select the subject", minutes="How many minutes to remove (required)")
@app_commands.choices(subject=SUBJECT_CHOICES)
async def remove_study_time(interaction: discord.Interaction, subject: app_commands.Choice[str], minutes: app_commands.Range[int, 1, COMMAND_MAX_MINUTES]):
    success, message = bot.db.remove_study_time(interaction.user.id, subject.value, minutes)
    if success:
        embed = discord.Embed(title="✅ Study time removed", description=f"Removed **{format_time(minutes)}** from **{subject.name}**", color=SUBJECTS[subject.value], timestamp=datetime.now())
        embed.set_footer(text=f"Requested by {interaction.user.display_name}")
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"❌ {message}", ephemeral=True)

@bot.tree.command(name="dashboard", description="Show your studying progress dashboard")
@app_commands.describe(period="Time period to view (default: All Time)")
@app_commands.choices(period=PERIOD_CHOICES)
async def show_dashboard(interaction: discord.Interaction, period: app_commands.Choice[str] = None):
    await interaction.response.defer()
    period_value = period.value if period else "all"
    
    if period_value == "all":
        progress = bot.db.get_user_progress(interaction.user.id, str(interaction.user))
    else:
        progress = bot.db.get_user_progress_by_period(interaction.user.id, str(interaction.user), period_value)

    embed = discord.Embed(title="📊 Dashboard", description=f"**{interaction.user.display_name}'s** Progress Report ({period_value.replace('_', ' ').title()})", color=0xDCDCDC, timestamp=datetime.now())
    total_study_time = 0

    if not progress:
        embed.add_field(name="📚 No data yet", value="Start studying and use `/add` to track your time!", inline=False)
    else:
        max_minutes = max((minutes for _, minutes in progress), default=0)
        
        items = list(progress)
        for i in range(0, len(items), 2):
            field_value = ""
            subject1, minutes1 = items[i]
            if minutes1 > 0:
                bar_length = 20
                filled = int((minutes1 / max_minutes) * bar_length) if max_minutes > 0 else 0
                bar = "█" * filled + "░" * (bar_length - filled)
                field_value += f"**{subject1}**\n`{bar}`\n{format_time(minutes1)} total"
                total_study_time += minutes1
            
            if i + 1 < len(items):
                subject2, minutes2 = items[i + 1]
                if minutes2 > 0:
                    field_value += "\n\n"
                    bar_length = 20
                    filled = int((minutes2 / max_minutes) * bar_length) if max_minutes > 0 else 0
                    bar = "█" * filled + "░" * (bar_length - filled)
                    field_value += f"**{subject2}**\n`{bar}`\n{format_time(minutes2)} total"
                    total_study_time += minutes2
            
            embed.add_field(name="​", value=field_value, inline=True)

    embed.add_field(name="📈 Total progress", value=f"**{format_time(total_study_time)}** across all subjects", inline=False)
    embed.set_footer(text="Keep up the great work! 🎓")
    if interaction.user.avatar:
        embed.set_thumbnail(url=interaction.user.avatar.url)

    await interaction.followup.send(embed=embed)

@bot.tree.command(name="leaderboard", description="Show the global study leaderboard")
@app_commands.describe(period="Time period to view (default: All Time)")
@app_commands.choices(period=PERIOD_CHOICES)
async def show_leaderboard(interaction: discord.Interaction, period: app_commands.Choice[str] = None):
    await interaction.response.defer()
    period_value = period.value if period else "all"
    
    if period_value == "all":
        leaderboard_data = bot.db.get_leaderboard()
    else:
        leaderboard_data = bot.db.get_leaderboard_by_period(period_value)

    embed = discord.Embed(title="🏆 Leaderboard", description=f"Top students ({period_value.replace('_', ' ').title()})", color=0xDCDCDC, timestamp=datetime.now())

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

@bot.tree.command(name="timeline", description="View your recent study sessions (paginated)")
async def show_timeline(interaction: discord.Interaction):
    await interaction.response.defer()
    total = bot.db.count_user_sessions(interaction.user.id)
    if total == 0:
        await interaction.followup.send("📭 You have no study sessions recorded yet.")
        return
    per_page = 5
    total_pages = (total + per_page - 1) // per_page
    sessions = bot.db.get_user_timeline(interaction.user.id, per_page, 0)
    embed = discord.Embed(title="📜 Study Timeline", description=f"Recent activity for **{interaction.user.display_name}** (Page 1)", color=0xDCDCDC, timestamp=datetime.now())
    for s in sessions:
        action = "➕ Added" if s["minutes"] > 0 else "➖ Removed"
        minutes_abs = abs(s["minutes"])
        time_str = s["timestamp"].strftime("%Y-%m-%d %H:%M")
        embed.add_field(name=f"{action} **{s['subject']}**", value=f"`{format_time(minutes_abs)}` at {time_str}", inline=False)
    embed.set_footer(text=f"Showing 1-{min(per_page, total)} of {total} entries")

    class TimelineView(discord.ui.View):
        def __init__(self, user: discord.User, current_page: int, total_pages: int):
            super().__init__(timeout=60)
            self.user = user
            self.current_page = current_page
            self.total_pages = total_pages

        @discord.ui.button(label="◀ Previous", style=discord.ButtonStyle.primary)
        async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("This timeline belongs to someone else.", ephemeral=True)
                return
            if self.current_page > 1:
                self.current_page -= 1
                await self.update_message(interaction)

        @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.primary)
        async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
            if interaction.user.id != self.user.id:
                await interaction.response.send_message("This timeline belongs to someone else.", ephemeral=True)
                return
            if self.current_page < self.total_pages:
                self.current_page += 1
                await self.update_message(interaction)

        async def update_message(self, interaction: discord.Interaction):
            offset = (self.current_page - 1) * per_page
            sessions = bot.db.get_user_timeline(self.user.id, per_page, offset)
            embed = discord.Embed(title="📜 Study Timeline", description=f"Recent activity for **{self.user.display_name}** (Page {self.current_page})", color=0xDCDCDC, timestamp=datetime.now())
            for s in sessions:
                action = "➕ Added" if s["minutes"] > 0 else "➖ Removed"
                minutes_abs = abs(s["minutes"])
                time_str = s["timestamp"].strftime("%Y-%m-%d %H:%M")
                embed.add_field(name=f"{action} **{s['subject']}**", value=f"`{format_time(minutes_abs)}` at {time_str}", inline=False)
            total = bot.db.count_user_sessions(self.user.id)
            embed.set_footer(text=f"Showing {offset+1}-{min(offset+per_page, total)} of {total} entries")
            await interaction.response.edit_message(embed=embed, view=self)

    view = TimelineView(interaction.user, 1, total_pages)
    await interaction.followup.send(embed=embed, view=view)

@bot.tree.command(name="help", description="Show all commands and how to use the bot")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(title="📚 Study Bot Help", description="Track your study time across subjects and compete with friends!", color=0xDCDCDC, timestamp=datetime.now())
    embed.add_field(name="**Slash Commands**", value=(
        "`/add <subject> <minutes>` – Add study time\n"
        "`/remove <subject> <minutes>` – Remove study time\n"
        "`/dashboard [period]` – View your progress (today/week/month/year/all)\n"
        "`/leaderboard [period]` – Global ranking\n"
        "`/timeline` – Paginated history of your entries\n"
        "`/help` – This message"
    ), inline=False)
    embed.add_field(name="**Offline Commands**", value=(
        "When the bot is offline, use `r;` prefix:\n"
        "`r;add subject minutes`  `r;remove subject minutes`\n"
        "`r;dashboard`  `r;leaderboard`  `r;timeline`  `r;help`"
    ), inline=False)
    embed.add_field(name="**Subjects**", value=", ".join(SUBJECTS.keys()), inline=False)
    embed.set_footer(text="Study hard, stay focused! 🎓")
    await interaction.response.send_message(embed=embed)


@bot.event
async def on_ready():
    print(f"✅ {bot.user} has connected to Discord!")
    print(f"📊 Bot is in {len(bot.guilds)} guild(s)")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Your study progress 📚"))
    await process_recap_messages()

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
                    elif command == "dashboard":
                        await process_dashboard_command(channel, msg.author, "all")
                    elif command == "leaderboard":
                        await process_leaderboard_command(channel, "all")
                    elif command == "timeline":
                        await process_timeline_command(channel, msg.author, 1)
                    elif command == "help":
                        await process_help_command(channel)
                    else:
                        await channel.send(f"❌ <@{msg.author.id}> Unknown command. Use `r;add`, `r;remove`, `r;dashboard`, `r;leaderboard`, `r;timeline`, or `r;help`.")
            except Exception as e:
                print(f"Error processing channel {channel.name} in guild {guild.name}: {e}")

    if new_last_id > last_id:
        bot.db.set_last_processed_message_id(new_last_id)
        print(f"📥 Recap processed messages up to ID {new_last_id}")


@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        if not interaction.response.is_done():
            await interaction.response.send_message(f"⏰ Command on cooldown. Try again in {error.retry_after:.1f} seconds.", ephemeral=True)
        else:
            await interaction.followup.send(f"⏰ Command on cooldown. Try again in {error.retry_after:.1f} seconds.", ephemeral=True)
    elif isinstance(error, app_commands.MissingPermissions):
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            await interaction.followup.send("❌ You don't have permission to use this command.", ephemeral=True)
    else:
        print(f"❌ Unexpected error: {error}")
        if not interaction.response.is_done():
            await interaction.response.send_message("❌ An unexpected error occurred. Please try again later.", ephemeral=True)
        else:
            await interaction.followup.send("❌ An unexpected error occurred. Please try again later.", ephemeral=True)


if __name__ == "__main__":
    bot.run(TOKEN)