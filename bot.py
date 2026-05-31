import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
from config import TOKEN, SUBJECTS
from database import Database

class StudyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.db = Database()
    
    async def setup_hook(self):
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} command(s)")
        except Exception as e:
            print(f"Failed to sync commands: {e}")

bot = StudyBot()

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')
    print(f'Bot is in {len(bot.guilds)} guild(s)')
    
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="your study progress 📚"
        )
    )

@bot.tree.command(name="add", description="Add studying time to a subject")
@app_commands.describe(
    subject="Select the subject you studied",
    minutes="How many minutes to add"
)
@app_commands.choices(subject=[
    app_commands.Choice(name="English", value="English"),
    app_commands.Choice(name="Math", value="Math"),
    app_commands.Choice(name="Science", value="Science"),
    app_commands.Choice(name="History", value="History")
])
async def add_study_time(
    interaction: discord.Interaction,
    subject: app_commands.Choice[str],
    minutes: int = 0
):
    if minutes <= 0:
        await interaction.response.send_message(
            "❌ Please specify a positive amount of study time (minutes or hours).",
            ephemeral=True
        )
        return
    
    success, message = bot.db.add_study_time(
        interaction.user.id,
        str(interaction.user),
        subject.value,
        minutes
    )
    
    if success:
        hours_display = minutes // 60
        mins_display = minutes % 60
        
        time_str = ""
        if hours_display > 0:
            time_str += f"{hours_display} hour(s) "
        if mins_display > 0:
            time_str += f"{mins_display} minute(s)"
        
        embed = discord.Embed(
            title="✅ Study time added",
            description=f"Added **{time_str.strip()}** to **{subject.name}**",
            color=SUBJECTS[subject.value],
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Requested by {interaction.user}")
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"❌ {message}", ephemeral=True)

@bot.tree.command(name="rm", description="Remove studying time from a subject")
@app_commands.describe(
    subject="Select the subject",
    minutes="How many minutes to remove",
)
@app_commands.choices(subject=[
    app_commands.Choice(name="English", value="English"),
    app_commands.Choice(name="Math", value="Math"),
    app_commands.Choice(name="Science", value="Science"),
    app_commands.Choice(name="History", value="History")
])
async def remove_study_time(
    interaction: discord.Interaction,
    subject: app_commands.Choice[str],
    minutes: int = 0,
):
    
    if minutes <= 0:
        await interaction.response.send_message(
            "❌ Please specify a positive amount of time to remove (minutes)",
            ephemeral=True
        )
        return
    
    success, message = bot.db.remove_study_time(
        interaction.user.id,
        subject.value,
        minutes
    )
    
    if success:
        hours_display = minutes // 60
        mins_display = minutes % 60
        
        time_str = ""
        if hours_display > 0:
            time_str += f"{hours_display} hour(s) "
        if mins_display > 0:
            time_str += f"{mins_display} minute(s)"
        
        embed = discord.Embed(
            title="✅ Study time removed",
            description=f"Removed **{time_str.strip()}** from **{subject.name}**",
            color=SUBJECTS[subject.value],
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"Requested by {interaction.user}")
        
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"❌ {message}", ephemeral=True)

@bot.tree.command(name="check", description="Show your studying progress dashboard")
async def check_progress(interaction: discord.Interaction):
    await interaction.response.defer()
    
    progress = bot.db.get_user_progress(interaction.user.id, str(interaction.user))
    
    embed = discord.Embed(
        title="📊 Dashboard",
        description=f"**{interaction.user.name}'s** Progress Report",
        color=0x9b59b6,
        timestamp=datetime.now()
    )
    
    total_study_time = 0
    
    if not progress:
        embed.add_field(
            name="No data yet",
            value="Start studying and use `/add` to track your time 📚",
            inline=False
        )
    else:
        for subject, minutes in progress:
            if minutes > 0:
                hours = minutes // 60
                mins = minutes % 60
                
                time_display = ""
                if hours > 0:
                    time_display = f"{hours}h {mins}m"
                else:
                    time_display = f"{mins}m"
                
                max_bar_length = 36
                max_minutes = max(p[1] for p in progress)
                filled = int((minutes / max_minutes) * max_bar_length) if max_minutes > 0 else 0
                bar = "█" * filled + "░" * (max_bar_length - filled)
                
                embed.add_field(
                    name=f"{subject}",
                    value=f"```{bar}```\n**{time_display}** total",
                    inline=True
                )
                
                total_study_time += minutes
    
    total_hours = total_study_time // 60
    total_mins = total_study_time % 60
    total_display = f"{total_hours}h {total_mins}m" if total_hours > 0 else f"{total_mins}m"
    
    embed.add_field(
        name="Total study time",
        value=f"**{total_display}** across all subjects",
        inline=False
    )
    
    embed.set_footer(text=f"Keep up the studying")
    embed.set_thumbnail(url=interaction.user.avatar.url if interaction.user.avatar else None)
    
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="leaderboard", description="Show the leaderboard across all subjects")
async def show_leaderboard(interaction: discord.Interaction):
    await interaction.response.defer()
    
    leaderboard_data = bot.db.get_leaderboard()
    
    embed = discord.Embed(
        title="🏆 Leaderboard",
        description="Top students across all subjects",
        color=0xf39c12,
        timestamp=datetime.now()
    )
    
    if not leaderboard_data:
        embed.add_field(
            name="No data yet",
            value="Be the first to start studying and appear on the leaderboard",
            inline=False
        )
    else:
        medals = ["🥇", "🥈", "🥉"]
        leaderboard_text = ""
        
        for i, (username, total_minutes) in enumerate(leaderboard_data):
            hours = total_minutes // 60
            mins = total_minutes % 60
            
            if hours > 0:
                time_str = f"{hours}h {mins}m"
            else:
                time_str = f"{mins}m"
            
            if i < 3:
                prefix = medals[i]
            else:
                prefix = f"**{i+1}.**"
            
            leaderboard_text += f"{prefix} **{username}** - {time_str}\n"
        
        embed.add_field(
            name="Top students",
            value=leaderboard_text,
            inline=False
        )
    
    legend = ""
    for subject, color in SUBJECTS.items():
        legend += f"**{subject}**\n"
    
    embed.add_field(
        name="Subjects",
        value=legend,
        inline=False
    )
    
    embed.set_footer(text="Study more to climb the ranks 📈")
    
    await interaction.followup.send(embed=embed)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.response.send_message(
            f"❌ Command on cooldown. Try again in {error.retry_after:.1f} seconds",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ An error occurred: {str(error)}",
            ephemeral=True
        ) 
        print(f"Error: {error}")

if __name__ == "__main__":
    bot.run(TOKEN)