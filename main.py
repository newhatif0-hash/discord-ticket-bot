import discord
from discord.ext import commands
from datetime import datetime, timedelta

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Temporary database for warnings
member_warns = {}

# YOUR ROLE IDs MAPPING
ROLE_PERMISSIONS = {
    "clear": [1545277913077907558, 1545277921109745764],
    "timeout": [1545277913077907558, 1545277937836761128, 1545277921109745764],
    "warn": [1545277913077907558, 1545277937836761128, 1545277921109745764],
    "warn_list": [1545277937836761128, 1545277913077907558, 1545277921109745764],
    "role": [1545277913077907558, 1545277888897617940],
    "lock": [1545277888897617940, 1545277913077907558],
    "kick": [1545277888897617940, 1545277913077907558],
    "ban": [1545277888897617940, 1545277913077907558]
}

async def has_permission(ctx, permission_key):
    """Checks if the user has one of the required Role IDs for the action"""
    user_role_ids = [role.id for role in ctx.author.roles]
    required_roles = ROLE_PERMISSIONS.get(permission_key, [])
    return any(role_id in user_role_ids for role_id in required_roles)

async def log_action(ctx, embed):
    """Sends moderation logs to a channel named #mod-logs"""
    log_channel = discord.utils.get(ctx.guild.text_channels, name="mod-logs")
    if not log_channel:
        try:
            log_channel = await ctx.guild.create_text_channel("mod-logs")
        except:
            return
    await log_channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f"✅ System Ready: {bot.user}")

# ========================
# MODERATION COMMANDS
# ========================

# 1. CLEARING (مسح)
@bot.command(name="مسح")
async def clear(ctx, amount: int = 5):
    if not await has_permission(ctx, "clear"):
        return await ctx.send("❌ ليس لديك صلاحية استخدام هذا الأمر!")
    
    deleted = await ctx.channel.purge(limit=amount + 1)
    await ctx.send(f"✅ تم مسح {len(deleted)-1} رسالة", delete_after=3)
    
    embed = discord.Embed(title="🗑️ مسح رسائل", color=discord.Color.blue())
    embed.add_field(name="المسؤول", value=ctx.author.mention)
    embed.add_field(name="القناة", value=ctx.channel.mention)
    embed.add_field(name="العدد", value=str(len(deleted)-1))
    await log_action(ctx, embed)

# 2. TIMEOUT (صمها، اسكت، اص)
@bot.command(name="صمها", aliases=["اسكت", "اص"])
async def timeout(ctx, member: discord.Member, minutes: int = 10):
    if not await has_permission(ctx, "timeout"):
        return await ctx.send("❌ ليس لديك صلاحية إسكات الأعضاء!")
    
    duration = timedelta(minutes=minutes)
    try:
        await member.timeout(duration, reason=f"Mod Action by {ctx.author}")
        await ctx.send(f"✅ تم إسكات {member.mention} لمدة {minutes} دقيقة")
        
        embed = discord.Embed(title="🔇 إسكات عضو", color=discord.Color.orange())
        embed.add_field(name="العضو", value=member.mention)
        embed.add_field(name="المسؤول", value=ctx.author.mention)
        embed.add_field(name="المدة", value=f"{minutes} دقيقة")
        await log_action(ctx, embed)
    except Exception as e:
        await ctx.send(f"❌ حدث خطأ: {e}")

# 3. WARN (تحذير، ت)
@bot.command(name="تحذير", aliases=["ت"])
async def warn(ctx, member: discord.Member, *, reason="لا يوجد سبب"):
    if not await has_permission(ctx, "warn"):
        return await ctx.send("❌ ليس لديك صلاحية تحذير الأعضاء!")
    
    gid = ctx.guild.id
    if gid not in member_warns: member_warns[gid] = {}
    if member.id not in member_warns[gid]: member_warns[gid][member.id] = 0
    
    member_warns[gid][member.id] += 1
    count = member_warns[gid][member.id]
    
    await ctx.send(f"✅ تم تحذير {member.mention} | التحذير رقم: {count}")
    
    embed = discord.Embed(title="⚠️ تحذير عضو", color=discord.Color.yellow())
    embed.add_field(name="العضو", value=member.mention)
    embed.add_field(name="المسؤول", value=ctx.author.mention)
    embed.add_field(name="السبب", value=reason)
    embed.add_field(name="إجمالي التحذيرات", value=str(count))
    await log_action(ctx, embed)

# 4. WARNS LIST (تحذيرات)
@bot.command(name="تحذيرات")
async def warn_list(ctx, member: discord.Member):
    if not await has_permission(ctx, "warn_list"):
        return await ctx.send("❌ ليس لديك صلاحية رؤية التحذيرات!")
    
    gid = ctx.guild.id
    count = member_warns.get(gid, {}).get(member.id, 0)
    await ctx.send(f"📊 العضو {member.mention} لديه **{count}** تحذيرات")

# 5. ROLE GIVE/REMOVE (ر، رول)
@bot.command(name="ر", aliases=["رول"])
async def manage_role(ctx, member: discord.Member, *, role_name: str):
    if not await has_permission(ctx, "role"):
        return await ctx.send("❌ ليس لديك صلاحية إدارة الأدوار!")
    
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    if not role:
        return await ctx.send(f"❌ لم يتم العثور على رول باسم `{role_name}`")
    
    if role in member.roles:
        await member.remove_roles(role)
        action = "إزالة"
        color = discord.Color.red()
    else:
        await member.add_roles(role)
        action = "إضافة"
        color = discord.Color.green()
        
    await ctx.send(f"✅ تم {action} رول {role.name} لـ {member.mention}")
    
    embed = discord.Embed(title=f"🎭 {action} رول", color=color)
    embed.add_field(name="العضو", value=member.mention)
    embed.add_field(name="الرول", value=role.mention)
    embed.add_field(name="المسؤول", value=ctx.author.mention)
    await log_action(ctx, embed)

# 6. LOCK (ق)
@bot.command(name="ق")
async def lock(ctx):
    if not await has_permission(ctx, "lock"):
        return await ctx.send("❌ ليس لديك صلاحية قفل القناة!")
    
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=False)
    await ctx.send("🔒 تم قفل القناة")
    
    embed = discord.Embed(title="🔒 قفل قناة", color=discord.Color.red())
    embed.add_field(name="القناة", value=ctx.channel.mention)
    embed.add_field(name="المسؤول", value=ctx.author.mention)
    await log_action(ctx, embed)

# 7. UNLOCK (ف)
@bot.command(name="ف")
async def unlock(ctx):
    if not await has_permission(ctx, "lock"):
        return await ctx.send("❌ ليس لديك صلاحية فتح القناة!")
    
    await ctx.channel.set_permissions(ctx.guild.default_role, send_messages=True)
    await ctx.send("🔓 تم فتح القناة")
    
    embed = discord.Embed(title="🔓 فتح قناة", color=discord.Color.green())
    embed.add_field(name="القناة", value=ctx.channel.mention)
    embed.add_field(name="المسؤول", value=ctx.author.mention)
    await log_action(ctx, embed)

# 8. KICK (برا)
@bot.command(name="برا")
async def kick(ctx, member: discord.Member, *, reason="لا يوجد سبب"):
    if not await has_permission(ctx, "kick"):
        return await ctx.send("❌ ليس لديك صلاحية طرد الأعضاء!")
    
    await member.kick(reason=reason)
    await ctx.send(f"✅ تم طرد {member.name} من السيرفر")
    
    embed = discord.Embed(title="👢 طرد عضو", color=discord.Color.orange())
    embed.add_field(name="العضو", value=member.mention)
    embed.add_field(name="السبب", value=reason)
    embed.add_field(name="المسؤول", value=ctx.author.mention)
    await log_action(ctx, embed)

# 9. BAN (بنعالي، كسرة، بان)
@bot.command(name="بان", aliases=["بنعالي", "كسرة"])
async def ban(ctx, member: discord.Member, *, reason="لا يوجد سبب"):
    if not await has_permission(ctx, "ban"):
        return await ctx.send("❌ ليس لديك صلاحية حظر الأعضاء!")
    
    await member.ban(reason=reason)
    await ctx.send(f"✅ تم حظر {member.name} نهائياً")
    
    embed = discord.Embed(title="🔨 حظر عضو", color=discord.Color.dark_red())
    embed.add_field(name="العضو", value=member.mention)
    embed.add_field(name="السبب", value=reason)
    embed.add_field(name="المسؤول", value=ctx.author.mention)
    await log_action(ctx, embed)

bot.run("YOUR_TOKEN_HERE")
