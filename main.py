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
        
        # Store ticket info
        if guild.id not in tickets:
            tickets[guild.id] = {}
        tickets[guild.id][ticket_channel.id] = {
            "user_id": user.id,
            "ticket_number": ticket_number,
            "created_at": datetime.now(),
            "status": "مفتوحة"
        }
        
        # Send welcome embed in ticket channel
        embed = discord.Embed(
            title=f"🎫 تذكرة جديدة #{ticket_number}",
            description=f"مرحباً {user.mention}!\n\nشكراً لفتحك تذكرة دعم. فريق الدعم سيرد عليك قريباً.\n\n**اكتب رسالتك أدناه وتواصل معنا**",
            color=discord.Color.from_rgb(88, 101, 242)
        )
        embed.add_field(name="👤 المستخدم", value=f"{user.mention}", inline=True)
        embed.add_field(name="📅 التاريخ", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
        embed.add_field(name="🔖 حالة التذكرة", value="🟢 مفتوحة", inline=True)
        embed.set_footer(text="استخدم الأزرار أدناه لإدارة التذكرة")
        
        await ticket_channel.send(embed=embed, view=TicketManagementButtons())
        
        await interaction.response.send_message(
            f"✅ تم إنشاء تذكرتك بنجاح: {ticket_channel.mention}",
            ephemeral=True
        )

# Ticket Management buttons
class TicketManagementButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="إضافة عضو", style=discord.ButtonStyle.blurple, emoji="➕")
    async def add_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(AddUserModal())
    
    @discord.ui.button(label="إزالة عضو", style=discord.ButtonStyle.blurple, emoji="➖")
    async def remove_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RemoveUserModal())
    
    @discord.ui.button(label="تغيير الحالة", style=discord.ButtonStyle.primary, emoji="🔄")
    async def change_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "اختر حالة التذكرة:",
            view=StatusView(),
            ephemeral=True
        )
    
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
            messages.append(f"[{msg.created_at.strftime('%Y-%m-%d %H:%M:%S')}] {msg.author}: {msg.content}")
        
        transcript = "\n".join(messages) if messages else "لا توجد رسائل"
        
        # Send to logs
        embed = discord.Embed(
            title=f"🔒 تذكرة مغلقة: {channel.name}",
            description=f"تم إغلاق التذكرة بواسطة {interaction.user.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="📊 عدد الرسائل", value=str(len(messages)), inline=True)
        embed.add_field(name="👤 صاحب التذكرة", value=f"<@{tickets[guild.id][channel.id]['user_id']}>", inline=True)
        embed.add_field(name="⏱️ المدة", value="تم الإغلاق", inline=True)
        
        await logs_channel.send(embed=embed)
        
        # Send closing message
        await interaction.followup.send(
            embed=discord.Embed(
                title="🔒 تم إغلاق التذكرة",
                description="سيتم حذف قناة التذكرة خلال 10 ثواني...",
                color=discord.Color.red()
            )
        )
        
        await asyncio.sleep(10)
        await channel.delete(reason="تم إغلاق التذكرة")

# Status selection view
class StatusView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="مفتوحة", style=discord.ButtonStyle.success, emoji="🟢")
    async def status_open(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_status(interaction, "مفتوحة", "🟢")
    
    @discord.ui.button(label="قيد المراجعة", style=discord.ButtonStyle.primary, emoji="🟡")
    async def status_pending(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_status(interaction, "قيد المراجعة", "🟡")
    
    @discord.ui.button(label="محلولة", style=discord.ButtonStyle.success, emoji="✅")
    async def status_resolved(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.update_status(interaction, "محلولة", "✅")
    
    async def update_status(self, interaction: discord.Interaction, status: str, emoji: str):
        guild = interaction.guild
        channel = interaction.channel
        
        # Update ticket info
        if guild.id in tickets and channel.id in tickets[guild.id]:
            tickets[guild.id][channel.id]["status"] = status
        
        # Send status update embed
        embed = discord.Embed(
            title=f"{emoji} تم تحديث حالة التذكرة",
            description=f"الحالة الجديدة: **{status}**",
            color=discord.Color.from_rgb(88, 101, 242)
        )
        embed.add_field(name="👤 تم التحديث بواسطة", value=interaction.user.mention, inline=False)
        
        await channel.send(embed=embed)
        await interaction.response.defer()

# Add user modal
class AddUserModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="إضافة عضو للتذكرة")
        self.user_input = discord.ui.TextInput(
            label="معرف أو ذكر المستخدم",
            placeholder="اكتب معرف المستخدم أو أذكره"
        )
        self.add_item(self.user_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_input = str(self.user_input.value).strip()
            guild = interaction.guild
            channel = interaction.channel
            
            # Try to find user
            user = None
            if user_input.startswith("<@") and user_input.endswith(">"):
                user_id = int(user_input[2:-1])
                user = await guild.fetch_member(user_id)
            else:
                try:
                    user = await guild.fetch_member(int(user_input))
                except:
                    user = discord.utils.get(guild.members, name=user_input)
            
            if not user:
                await interaction.response.send_message("❌ لم يتم العثور على المستخدم!", ephemeral=True)
                return
            
            # Add user to channel
            await channel.set_permissions(user, read_messages=True, send_messages=True)
            
            embed = discord.Embed(
                title="➕ تم إضافة عضو",
                description=f"تم إضافة {user.mention} للتذكرة",
                color=discord.Color.green()
            )
            embed.add_field(name="✋ من أضافه", value=interaction.user.mention, inline=False)
            
            await channel.send(embed=embed)
            await interaction.response.defer()
        except Exception as e:
            await interaction.response.send_message(f"❌ خطأ: {str(e)}", ephemeral=True)

# Remove user modal
class RemoveUserModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="إزالة عضو من التذكرة")
        self.user_input = discord.ui.TextInput(
            label="معرف أو ذكر المستخدم",
            placeholder="اكتب معرف المستخدم أو أذكره"
        )
        self.add_item(self.user_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        try:
            user_input = str(self.user_input.value).strip()
            guild = interaction.guild
            channel = interaction.channel
            
            # Try to find user
            user = None
            if user_input.startswith("<@") and user_input.endswith(">"):
                user_id = int(user_input[2:-1])
                user = await guild.fetch_member(user_id)
            else:
                try:
                    user = await guild.fetch_member(int(user_input))
                except:
                    user = discord.utils.get(guild.members, name=user_input)
            
            if not user:
                await interaction.response.send_message("❌ لم يتم العثور على المستخدم!", ephemeral=True)
                return
            
            # Remove user from channel
            await channel.set_permissions(user, overwrite=None)
            
            embed = discord.Embed(
                title="➖ تم إزالة عضو",
                description=f"تم إزالة {user.mention} من التذكرة",
                color=discord.Color.red()
            )
            embed.add_field(name="✋ من أزاله", value=interaction.user.mention, inline=False)
            
            await channel.send(embed=embed)
            await interaction.response.defer()
        except Exception as e:
            await interaction.response.send_message(f"❌ خطأ: {str(e)}", ephemeral=True)

# Command to send ticket embed
@bot.tree.command(name="تذاكر", description="إرسال لوحة التذاكر")
@app_commands.default_permissions(administrator=True)
async def tickets_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🎫 نظام التذاكر",
        description="اضغط على الزر أدناه لفتح تذكرة دعم جديدة\n\n**الميزات:**\n✨ دعم سريع وفعال\n👥 إضافة/إزالة أعضاء\n🔄 تتبع حالة التذكرة\n📊 سجل شامل",
        color=discord.Color.from_rgb(88, 101, 242)
    )
    embed.add_field(name="📌 ملاحظات مهمة", value="• يمكنك فتح تذكرة واحدة فقط\n• التذاكر المفتوحة تُحفظ في السجلات\n• فريق الدعم متاح 24/7", inline=False)
    embed.set_footer(text="نظام التذاكر v1.0")
    
    await interaction.response.send_message(embed=embed, view=TicketButtons())

# Run bot
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    print("❌ لم يتم العثور على DISCORD_TOKEN")
else:
    bot.run(TOKEN)
        
