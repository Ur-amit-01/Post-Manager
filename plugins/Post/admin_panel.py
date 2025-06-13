from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery
)
from config import *
import os
import asyncio
import json
import time
import logging
import psutil
from datetime import datetime, timedelta
from plugins.helper.db import db
from pyrogram.errors import (
    FloodWait, 
    InputUserDeactivated, 
    UserIsBlocked, 
    PeerIdInvalid
)

# ======================== INITIALIZATION ========================
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BOT_START_TIME = time.time()

# ======================== UTILITIES ========================
async def admins_only(_, __, message):
    if not message.from_user:
        return False
    return await db.is_admin(message.from_user.id)

admin_filter = filters.create(admins_only)

def format_time(seconds: int) -> str:
    """Convert seconds to human-readable time format"""
    periods = [
        ('day', 86400),
        ('hour', 3600),
        ('minute', 60),
        ('second', 1)
    ]
    parts = []
    for period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            parts.append(f"{period_value} {period_name}{'s' if period_value != 1 else ''}")
    return ", ".join(parts[:3])

async def generate_admin_menu():
    """Generate the main admin menu"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("👑 User Management", callback_data="admin_user_mgmt"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton("📊 Statistics", callback_data="admin_stats"),
            InlineKeyboardButton("💾 Backup", callback_data="admin_backup")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="admin_settings"),
            InlineKeyboardButton("❌ Close", callback_data="admin_close")
        ]
    ])

async def generate_user_mgmt_menu():
    """Generate user management submenu"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬆️ Promote User", callback_data="admin_promote"),
            InlineKeyboardButton("⬇️ Demote User", callback_data="admin_demote")
        ],
        [
            InlineKeyboardButton("📜 List Admins", callback_data="admin_list_admins"),
            InlineKeyboardButton("👥 List Users", callback_data="admin_list_users")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_back"),
            InlineKeyboardButton("🏠 Home", callback_data="admin_home")
        ]
    ])

async def generate_backup_menu():
    """Generate backup/restore submenu"""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📤 Create Backup", callback_data="admin_create_backup"),
            InlineKeyboardButton("📥 Restore Backup", callback_data="admin_restore_backup")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_back"),
            InlineKeyboardButton("🏠 Home", callback_data="admin_home")
        ]
    ])

# ======================== COMMAND HANDLERS ========================
@Client.on_message(filters.command("admin") & admin_filter)
async def admin_panel(client: Client, message: Message):
    """Main admin panel entry point"""
    await message.reply(
        "✨ **Admin Panel** ✨\n\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        "Manage your bot with the options below:",
        reply_markup=await generate_admin_menu()
    )

# ======================== CALLBACK QUERY HANDLERS ========================
@Client.on_callback_query(filters.regex("^admin_"))
async def admin_callback_handler(client: Client, query: CallbackQuery):
    data = query.data
    
    if data == "admin_home":
        await query.message.edit_text(
            "✨ **Admin Panel** ✨\n\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "Manage your bot with the options below:",
            reply_markup=await generate_admin_menu()
        )
    
    elif data == "admin_back":
        await query.message.edit_text(
            "✨ **Admin Panel** ✨\n\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "Manage your bot with the options below:",
            reply_markup=await generate_admin_menu()
        )
    
    elif data == "admin_close":
        await query.message.delete()
    
    elif data == "admin_user_mgmt":
        await query.message.edit_text(
            "👑 **User Management**\n\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "Manage admin users and permissions:",
            reply_markup=await generate_user_mgmt_menu()
        )
    
    elif data == "admin_stats":
        # Get all statistics
        total_users = await db.total_users_count()
        total_admins = len(await db.get_all_admins())
        total_channels = len(await db.get_all_channels())
        uptime = format_time(int(time.time() - BOT_START_TIME))
        
        # System performance
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        mem_usage = memory.percent
        disk = psutil.disk_usage('/')
        disk_usage = disk.percent
        
        stats_text = f"""
📈 **Bot Statistics Dashboard**

▬▬▬▬▬▬▬▬▬▬▬▬▬▬
👥 **Users**
├─ Total Users: `{total_users}`
└─ Total Admins: `{total_admins}`

📡 **Connections**
└─ Connected Channels: `{total_channels}`

⏱ **Performance**
├─ Uptime: `{uptime}`
├─ CPU Usage: `{cpu_usage}%`
├─ Memory Usage: `{mem_usage}%`
└─ Disk Usage: `{disk_usage}%`
▬▬▬▬▬▬▬▬▬▬▬▬▬▬

🔄 Last Updated: `{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}`
"""
        buttons = [
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_back")]
        ]
        await query.message.edit_text(
            stats_text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    elif data == "admin_list_admins":
        admins = await db.get_all_admins()
        if not admins:
            text = "🚫 **No admins found!**"
        else:
            text = "👑 **Admin List**\n\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            for admin in admins:
                try:
                    user = await client.get_users(admin["_id"])
                    text += f"✨ **{user.mention}**\n"
                    text += f"🆔 `{user.id}`\n"
                    text += f"⏰ Added: `{admin.get('added_at', 'Unknown')}`\n"
                    text += "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                except Exception as e:
                    text += f"👤 Unknown User\n🆔 `{admin['_id']}`\n▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        
        buttons = [
            [InlineKeyboardButton("🔙 Back", callback_data="admin_user_mgmt")]
        ]
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    
    elif data == "admin_backup":
        await query.message.edit_text(
            "💾 **Backup Management**\n\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "Create or restore database backups:",
            reply_markup=await generate_backup_menu()
        )
    
    elif data == "admin_create_backup":
        try:
            # Create loading message
            msg = await query.message.edit_text(
                "⏳ **Creating Backup...**\n\n"
                "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
                "Please wait while we prepare your backup file."
            )
            
            # Get data
            channels = [{"_id": c["_id"], "name": c.get("name")} for c in await db.get_all_channels()]
            admins = [{"_id": a["_id"], "added_at": a.get("added_at")} for a in await db.get_all_admins()]
            
            # Prepare backup
            backup = {
                "meta": {
                    "created_at": datetime.now().isoformat(),
                    "bot_version": "1.0",
                    "total_users": await db.total_users_count(),
                    "total_channels": len(channels),
                    "total_admins": len(admins)
                },
                "data": {
                    "channels": channels,
                    "admins": admins
                }
            }
            
            # Save to file
            filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, "w") as f:
                json.dump(backup, f, indent=4)
            
            # Send file
            await client.send_document(
                query.message.chat.id,
                filename,
                caption="✅ **Backup Created Successfully!**\n\n"
                       f"📅 Created: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
                       f"📦 Size: `{os.path.getsize(filename)/1024:.2f} KB`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_backup")]
                ])
            )
            await msg.delete()
            os.remove(filename)
            
        except Exception as e:
            await query.message.edit_text(
                f"❌ **Backup Failed!**\n\n"
                f"Error: `{str(e)}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 Back", callback_data="admin_backup")]
                ])
            )
            if os.path.exists(filename):
                os.remove(filename)
    
    await query.answer()

# ======================== COMMAND HANDLERS WITH INLINE UI ========================
@Client.on_message(filters.command("promote") & admin_filter)
async def promote_user(client: Client, message: Message):
    if not message.reply_to_message and len(message.command) < 2:
        await message.reply(
            "⬆️ **Promote User**\n\n"
            "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            "Reply to a user or send their ID to promote them.\n\n"
            "Example:\n`/promote @username` or reply to a user with `/promote`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("👑 User Management", callback_data="admin_user_mgmt")],
                [InlineKeyboardButton("🏠 Admin Panel", callback_data="admin_home")]
            ])
        )
        return
    
    try:
        user_id = message.reply_to_message.from_user.id if message.reply_to_message else int(message.command[1])
        user = await client.get_users(user_id)
        
        await db.add_admin(user_id)
        
        await message.reply(
            f"✅ **Successfully Promoted!**\n\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"👤 User: {user.mention}\n"
            f"🆔 ID: `{user.id}`\n"
            f"⏰ At: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📜 List Admins", callback_data="admin_list_admins")],
                [InlineKeyboardButton("🏠 Admin Panel", callback_data="admin_home")]
            ])
        )
    except Exception as e:
        await message.reply(
            f"❌ **Promotion Failed**\n\n"
            f"Error: `{str(e)}`",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛠 Help", callback_data="admin_help")]
            ])
        )

@Client.on_message(filters.command("broadcast") & admin_filter & filters.reply)
async def broadcast_handler(client: Client, message: Message):
    # Initial message with loading animation
    msg = await message.reply(
        "📢 **Broadcast Initializing...**\n\n"
        "▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        "⏳ Preparing to send to all users..."
    )
    
    all_users = await db.get_all_users()
    broadcast_msg = message.reply_to_message
    total_users = await db.total_users_count()
    
    # Progress tracking
    progress = {
        "done": 0,
        "success": 0,
        "failed": 0,
        "start": time.time()
    }
    
    # Update progress every 20 users
    async def update_progress():
        elapsed = format_time(int(time.time() - progress["start"]))
        await msg.edit_text(
            f"📢 **Broadcast in Progress**\n\n"
            f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
            f"✅ Success: `{progress['success']}`\n"
            f"❌ Failed: `{progress['failed']}`\n"
            f"📊 Progress: `{progress['done']}/{total_users}`\n"
            f"⏱ Elapsed: `{elapsed}`\n\n"
            f"🔄 Processing...",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🛑 Cancel", callback_data="broadcast_cancel")]
            ])
        )
    
    # Send messages
    async for user in all_users:
        if progress["done"] % 20 == 0:
            await update_progress()
        
        try:
            await broadcast_msg.copy(chat_id=int(user['_id']))
            progress["success"] += 1
        except Exception as e:
            logger.error(f"Broadcast failed for {user['_id']}: {str(e)}")
            progress["failed"] += 1
            if isinstance(e, (InputUserDeactivated, UserIsBlocked)):
                await db.delete_user(user['_id'])
        
        progress["done"] += 1
    
    # Final report
    elapsed = format_time(int(time.time() - progress["start"]))
    await msg.edit_text(
        f"✅ **Broadcast Completed!**\n\n"
        f"▬▬▬▬▬▬▬▬▬▬▬▬▬▬\n"
        f"📊 Total Users: `{total_users}`\n"
        f"✅ Success: `{progress['success']}`\n"
        f"❌ Failed: `{progress['failed']}`\n"
        f"⏱ Time Taken: `{elapsed}`\n\n"
        f"🔄 Last Updated: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Admin Panel", callback_data="admin_home")]
        ])
    )

# ======================== ERROR HANDLER ========================
@Client.on_callback_query(filters.regex("^broadcast_cancel$"))
async def cancel_broadcast(client: Client, query: CallbackQuery):
    await query.answer("Broadcast cannot be canceled once started!", show_alert=True)
