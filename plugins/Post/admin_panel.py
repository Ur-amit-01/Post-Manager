from plugins.helper.db import db
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import *
import os
import asyncio
from datetime import datetime, timedelta
import json
import time
import logging
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid

# Bot start time for uptime calculation
START_TIME = datetime.now()

# Logging setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

async def admins_only(_, __, message):
    if not message.from_user:
        return False
    return await db.is_admin(message.from_user.id)

admin_filter = filters.create(admins_only)

# ==================================== ADMIN PANEL MAIN MENU ====================================

async def show_admin_panel(client, message_or_query):
    text = """
<b>🤖 ADMIN PANEL

Choose from the options below:
</b>"""
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("👑 Admin Management", callback_data="admin_management")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast_menu"),
         InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("🔰 Backup/Restore", callback_data="admin_backup_menu")]
    ])
    
    if isinstance(message_or_query, CallbackQuery):
        await message_or_query.edit_message_text(text, reply_markup=buttons)
        await message_or_query.answer()
    else:
        if message_or_query.chat.type == "private":
            await message_or_query.delete()
        await message_or_query.reply_text(text, reply_markup=buttons)

@Client.on_message(filters.command("admin") & admin_filter)
async def admin_panel(client, message):
    await show_admin_panel(client, message)

@Client.on_callback_query(filters.regex("^back_to_main$") & admin_filter)
async def back_to_main(client, query: CallbackQuery):
    await show_admin_panel(client, query)

# ==================================== ADMIN MANAGEMENT ====================================

@Client.on_callback_query(filters.regex("^admin_management$") & admin_filter)
async def admin_management(client, query: CallbackQuery):
    text = """
<b>👑 ADMIN MANAGEMENT

Manage bot admins with the options below:
</b>"""
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Promote User", callback_data="promote_user"),
         InlineKeyboardButton("➖ Demote User", callback_data="demote_user")],
        [InlineKeyboardButton("📜 List Admins", callback_data="list_admins")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)
    await query.answer()

@Client.on_callback_query(filters.regex("^promote_user$") & admin_filter)
async def promote_user_callback(client, query: CallbackQuery):
    await query.edit_message_text(
        "**🔸 To promote a user:**\n\n"
        "**1. Use <code>/promote user_id</code>**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="admin_management")]
        ])
    )
    await query.answer()

@Client.on_callback_query(filters.regex("^demote_user$") & admin_filter)
async def demote_user_callback(client, query: CallbackQuery):
    await query.edit_message_text(
        "**🔸 To demote a user:**\n\n"
        "**1. Use <code>/demote user_id</code>**",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="admin_management")]
        ])
    )
    await query.answer()

@Client.on_callback_query(filters.regex("^list_admins$") & admin_filter)
async def list_admins_callback(client, query: CallbackQuery):
    admins = await db.get_all_admins()
    if not admins:
        text = "No admins found!"
    else:
        text = "👑 <b>Admin List</b>\n\n"
        for admin in admins:
            try:
                user = await client.get_users(admin["_id"])
                text += f"🫦 {user.mention} (<code>{user.id}</code>)\n"
                text += f"🔸 Added: <code>{admin.get('added_at', 'Unknown')}</code>\n\n"
            except:
                text += f"• Unknown User (<code>{admin['_id']}</code>)\n\n"
    
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 Back", callback_data="admin_management")]
        ])
    )
    await query.answer()

# ==================================== BROADCAST MENU ====================================

@Client.on_callback_query(filters.regex("^admin_broadcast_menu$") & admin_filter)
async def broadcast_menu(client, query: CallbackQuery):
    total_users = await db.total_users_count()
    text = f"""
<b>📢 BROADCAST MESSAGE

🔺 Current users: <code>{total_users}</code>

🔸 To send a broadcast:
1. Reply to any message with <code>/broadcast</code>
</b>"""
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)
    await query.answer()

# ==================================== STATS MENU ====================================

@Client.on_callback_query(filters.regex("^admin_stats$") & admin_filter)
async def stats_menu(client, query: CallbackQuery):
    # Calculate bot uptime
    uptime = datetime.now() - START_TIME
    hours, remainder = divmod(int(uptime.total_seconds()), 3600)
    minutes, seconds = divmod(remainder, 60)
    days, hours = divmod(hours, 24)
    uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
    
    # Get stats
    total_users = await db.total_users_count()
    total_admins = len(await db.get_all_admins())
    total_channels = len(await db.get_all_channels())
    
    text = f"""
<b>📊 BOT STATISTICS</b>

👥 <b>Total Users:</b> <code>{total_users}</code>
👑 <b>Total Admins:</b> <code>{total_admins}</code>
📢 <b>Total Channels:</b> <code>{total_channels}</code>
⏰ <b>Uptime:</b> <code>{uptime_str}</code>
"""
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats"),
         InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)
    await query.answer()

# ==================================== BACKUP/RESTORE MENU ====================================

@Client.on_callback_query(filters.regex("^admin_backup_menu$") & admin_filter)
async def backup_menu(client, query: CallbackQuery):
    text = """
<b>🔰 BACKUP & RESTORE</b>

• <b>Backup:</b> Creates a JSON file with channels and admins data
• <b>Restore:</b> Restores data from a backup file

<b>🤖 Commands:</b>
• /backup - Create a backup
• /restore (reply to backup file) - Restore data
"""
    buttons = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ])
    
    await query.edit_message_text(text, reply_markup=buttons)
    await query.answer()

# ==================================== BACK BUTTON ====================================
# ==================================== ORIGINAL COMMANDS (KEPT FOR COMPATIBILITY) ====================================

@Client.on_message(filters.command("promote") & filters.user(ADMIN))
async def promote_user(client, message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply("**Reply to a user or use: /promote user_id**")
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        try:
            user_id = int(message.command[1])
        except:
            return await message.reply("Invalid user ID!")

    await db.add_admin(user_id)
    await message.reply(f"**✅ Promoted user {user_id} to admin!**")

@Client.on_message(filters.command("demote") & filters.user(ADMIN))
async def demote_user(client, message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply("**Reply to a user or use: /demote user_id**")
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        try:
            user_id = int(message.command[1])
        except:
            return await message.reply("Invalid user ID!")

    await db.remove_admin(user_id)
    await message.reply(f"**❌ Demoted user {user_id}**")


@Client.on_message(filters.command("backup") & admin_filter)
async def backup_data(client, message):
    try:        
        channels = [{"_id": c["_id"], "name": c.get("name")} for c in await db.get_all_channels()]
        admins = [{"_id": a["_id"]} for a in await db.get_all_admins()]
        
        backup = {
            "channels": channels,
            "admins": admins,
            "backup_date": datetime.now().strftime("%d-%m-%Y")
        }
        
        me = await client.get_me()
        filename = f"{me.username}_backup.json"
        with open(filename, "w") as f:
            json.dump(backup, f, indent=4)
        
        await client.send_document(
            message.chat.id, 
            filename, 
            caption=f"📦 <b>Backup File</b>\n\n"
                    f"📅 <b>Date:</b> <code>{backup['backup_date']}</code>\n"
                    f"📢 <b>Channels:</b> <code>{len(backup['channels'])}</code>\n"
                    f"👑 <b>Admins:</b> <code>{len(backup['admins'])}</code>"
        )
        os.remove(filename)
        await message.reply("✅ <b>Backup completed successfully!</b>")
        
    except Exception as e:
        await message.reply(f"❌ <b>Backup failed:</b> <code>{str(e)}</code>")
        if 'filename' in locals() and os.path.exists(filename):
            os.remove(filename)

@Client.on_message(filters.command("restore") & admin_filter)
async def restore_data(client, message):
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ <b>Please reply to a backup file</b>")
    
    try:
        msg = await message.reply("🔄 <b>Restoring data...</b>")
        file = await message.reply_to_message.download()
        
        with open(file, "r") as f:
            backup = json.load(f)
        
        # Restore channels
        channels_count = 0
        for channel in backup.get("channels", []):
            await db.add_channel(channel["_id"], channel.get("name"))
            channels_count += 1
        
        # Restore admins
        admins_count = 0
        for admin in backup.get("admins", []):
            await db.add_admin(admin["_id"])
            admins_count += 1
        
        os.remove(file)
        await msg.edit(
            f"✅ <b>Restore completed successfully!</b>\n\n"
            f"📢 <b>Channels restored:</b> <code>{channels_count}</code>\n"
            f"👑 <b>Admins restored:</b> <code>{admins_count}</code>\n"
            f"📅 <b>Backup date:</b> <code>{backup.get('backup_date', 'Unknown')}</code>"
        )
        
    except Exception as e:
        await message.reply(f"❌ <b>Restore failed:</b> <code>{str(e)}</code>")
        if 'file' in locals() and os.path.exists(file):
            os.remove(file)
