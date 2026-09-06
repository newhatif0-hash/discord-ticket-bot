import discord
from discord.ext import commands
from discord import app_commands
import os
import asyncio
from datetime import datetime

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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

class TicketButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="فتح تذكرة", style=discord.ButtonStyle.success, emoji="🎫")
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild = interaction.guild
        user = interaction.user
        
        # Check if user already has ticket
        for channel in guild.text_channels:
            if channel.topic and f"user_id:{user.id}" in channel.topic:
                await interaction.response.send_message("❌ أنت تملك تذكرة مفتوحة بالفعل!", ephemeral=True)
                return
        
        if guild.id not in ticket_counter:
            ticket_counter[guild.id] = 0
        ticket_counter[guild.id] += 1
        
        ticket_number = ticket_counter[guild.id]
        channel_name = f"🎫-تذكرة-{ticket_number}"
        
        support_role = discord.utils.get(guild.roles, name="Support")
        if not support_role:
            support_role = await guild.create_role(name="Support", color=discord.Color.blue())
        
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
        
        if guild.id not in tickets:
            tickets[guild.id] = {}
        tickets[guild.id][ticket_channel.id] = {
            "user_id": user.id,
            "ticket_number": ticket_number,
            "created_at": datetime.now(),
            "status": "🟢 مفتوحة"
        }
        
        # Welcome embed - MATCHING YOUR DESIGN
        embed = discord.Embed(
            title="Welcome to Ticket",
            description="مرحباً بك في نظام التذاكر\nهذه قناتك الخاصة للدعم",
            color=discord.Color.from_rgb(88, 101, 242)
        )
        embed.add_field(name="👤 صاحب التذكرة", value=f"{user.mention}", inline=True)
        embed.add_field(name="📊 رقم التذكرة", value=f"#{ticket_number}", inline=True)
        embed.add_field(name="🔖 الحالة", value="🟢 مفتوحة", inline=True)
        embed.add_field(name="📅 وقت الإنشاء", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=False)
        embed.set_footer(text="⚠️ لا تغلق هذه الرسالة")
        
        await ticket_channel.send(embed=embed, view=TicketActionButtons())
        
        await interaction.response.send_message(
            f"✅ تم إنشاء تذكرتك: {ticket_channel.mention}",
            ephemeral=True
        )

class TicketActionButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="قبول", style=discord.ButtonStyle.success, emoji="✅")
    async def accept_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        
        embed = discord.Embed(
            title="✅ تم قبول التذكرة",
            description=f"تم قبول التذكرة بواسطة {interaction.user.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="🕐 الوقت", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=False)
        
        await channel.send(embed=embed)
        await interaction.response.defer()
    
    @discord.ui.button(label="رفض", style=discord.ButtonStyle.red, emoji="❌")
    async def reject_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        guild = interaction.guild
        
        embed = discord.Embed(
            title="❌ تم رفض التذكرة",
            description=f"تم رفض التذكرة بواسطة {interaction.user.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="🕐 الوقت", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=False)
        
        await channel.send(embed=embed)
        await interaction.response.defer()
    
    @discord.ui.button(label="معلق", style=discord.ButtonStyle.primary, emoji="⏳")
    async def pending_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        channel = interaction.channel
        
        embed = discord.Embed(
            title="⏳ التذكرة معلقة",
            description=f"تم وضع التذكرة في الانتظار بواسطة {interaction.user.mention}",
            color=discord.Color.from_rgb(255, 165, 0)
        )
        embed.add_field(name="🕐 الوقت", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=False)
        
        await channel.send(embed=embed)
        await interaction.response.defer()
    
    @discord.ui.button(label="غلق", style=discord.ButtonStyle.danger, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        channel = interaction.channel
        guild = interaction.guild
        
        logs_channel = discord.utils.get(guild.text_channels, name="ticket-logs")
        if not logs_channel:
            logs_channel = await guild.create_text_channel("ticket-logs")
        
        # Get ticket info
        ticket_info = None
        if
