import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from datetime import datetime

# Setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Store ticket data (in-memory for now)
tickets = {}
ticket_counter = {}

@bot.event
async def on_ready():
    print(f"✅ البوت جاهز: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"✅ تم مزامنة {len(synced)} أوامر")
    except Exception as e:
        print(e)

# Create ticket button
class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="فتح تذكرة", style=discord.ButtonStyle.green, emoji="🎫")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        # Check if user already has ticket
        for channel in guild.text_channels:
            if channel.topic and f"user_id:{user.id}" in channel.topic:
                await interaction.response.send_message("❌ أنت تملك تذكرة مفتوحة بالفعل!", ephemeral=True)
                return
        
        # Initialize counter
        if guild.id not in ticket_counter:
            ticket_counter[guild.id] = 0
        ticket_counter[guild.id] += 1
        
        # Create ticket channel
        ticket_number = ticket_counter[guild.id]
        channel_name = f"🎫-تذكرة-{ticket_number}"
        
        # Get support role (or create one)
        support_role = discord.utils.get(guild.roles, name="Support")
        if not support_role:
            support_role = await guild.create_role(name="Support", color=discord.Color.blue())
        
        # Create channel with permissions
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            support_role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            bot.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }
        
        ticket_channel = await guild.create_text_channel(
            channel_name,
            overwrites=overwrites,
            topic=f"user_id:{user.id}|ticket_id:{ticket_number}"
        )
        
        # Send embed in ticket channel
        embed = discord.Embed(
            title=f"تذكرة جديدة #{ticket_number}",
            description=f"مرحباً {user.mention}!\n\nشكراً لفتحك تذكرة. فريق الدعم سيرد عليك قريباً.\n\nاكتب رسالتك أدناه.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="اضغط على الزر لإغلاق التذكرة")
        
        await ticket_channel.send(embed=embed, view=CloseTicketButtons())
        
        await interaction.response.send_message(
            f"✅ تم إنشاء تذكرتك: {ticket_channel.mention}",
            ephemeral=True
        )

# Close ticket button
class CloseTicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="إغلاق التذكرة", style=discord.ButtonStyle.red, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        channel = interaction.channel
        guild = interaction.guild
        
        # Get logs channel
        logs_channel = discord.utils.get(guild.text_channels, name="ticket-logs")
        if not logs_channel:
            logs_channel = await guild.create_text_channel("ticket-logs")
        
        # Create transcript
        messages = []
        async for msg in channel.history(limit=None, oldest_first=True):
            messages.append(f"[{msg.created_at}] {msg.author}: {msg.content}")
        
        transcript = "\n".join(messages)
        
        # Send to logs
        embed = discord.Embed(
            title=f"تذكرة مغلقة: {channel.name}",
            description=f"تم إغلاق التذكرة بواسطة {interaction.user.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="عدد الرسائل", value=len(messages), inline=False)
        
        await logs_channel.send(embed=embed)
        
        # Delete channel after 5 seconds
        await interaction.followup.send("🔒 سيتم حذف التذكرة خلال 5 ثواني...")
        await asyncio.sleep(5)
        await channel.delete(reason="تم إغلاق التذكرة")

# Command to send ticket embed
@bot.tree.command(name="تذاكر", description="إرسال لوحة التذاكر")
@app_commands.default_permissions(administrator=True)
async def tickets(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 نظام التذاكر",
        description="اضغط على الزر أدناه لفتح تذكرة دعم جديدة",
        color=discord.Color.blue()
    )
    embed.add_field(name="📌 ملاحظة", value="يمكنك فتح تذكرة واحدة فقط في المرة", inline=False)
    
    await interaction.response.send_message(embed=embed, view=TicketButtons())

# Run bot
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ لم يتم العثور على DISCORD_TOKEN")
else:
    bot.run(TOKEN)
    
