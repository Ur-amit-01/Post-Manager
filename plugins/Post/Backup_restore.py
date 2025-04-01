import os
import json
from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    CallbackQuery
)
from datetime import datetime
from plugins.helper.db import db
from config import *

# ==================== BACKUP/RESTORE HANDLERS ====================

@Client.on_message(filters.command("backup") & filters.private & filters.user(ADMIN))
async def backup_command(client, message: Message):
    try:
        backup_data = await db.get_complete_backup()
        filename = f"channel_backup_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
        
        with open(filename, "w") as f:
            json.dump(backup_data, f, indent=4)
        
        await message.reply_document(
            document=filename,
            caption="🔐 **Full Channel Manager Backup**\n\n"
                   f"• Channels: {len(backup_data['channels'])}\n"
                   f"• Posts: {len(backup_data['posts'])}\n"
                   f"• Users: {backup_data['metadata']['total_users']}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("♻️ Restore", callback_data="restore_prompt")
            ]])
        )
        
        os.remove(filename)
        
    except Exception as e:
        await message.reply(f"❌ Backup failed: {str(e)}")

@Client.on_message(filters.command("restore") & filters.private & filters.user(ADMIN))
async def restore_command(client, message: Message):
    reply = message.reply_to_message
    if not reply or not reply.document:
        return await message.reply("ℹ️ Please reply to a backup file with /restore")
    
    try:
        # Download the backup file
        path = await reply.download()
        
        with open(path, "r") as f:
            data = json.load(f)
        
        # Verify backup structure
        if not all(k in data for k in ["channels", "posts"]):
            raise ValueError("Invalid backup format")
        
        # Restore channels
        restored_channels = 0
        for channel in data["channels"]:
            if not await db.is_channel_exist(channel["_id"]):
                await db.add_channel(channel["_id"], channel["name"])
                restored_channels += 1
        
        # Restore posts
        restored_posts = 0
        for post in data["posts"]:
            await db.save_post(post["_id"], post["messages"])
            restored_posts += 1
        
        os.remove(path)
        
        await message.reply(
            "✅ **Restore Complete**\n\n"
            f"• New Channels: {restored_channels}\n"
            f"• Restored Posts: {restored_posts}"
        )
        
    except Exception as e:
        await message.reply(f"❌ Restore failed: {str(e)}")
        if 'path' in locals() and os.path.exists(path):
            os.remove(path)

# ==================== CALLBACK HANDLERS ====================

@Client.on_callback_query(filters.regex("^restore_prompt$"))
async def restore_prompt_handler(client, query: CallbackQuery):
    await query.message.edit_text(
        "**To restore data:**\n\n"
        "1. Reply to a backup file\n"
        "2. Type /restore",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("« Back", callback_data="back_to_main")
        ]])
    )

@Client.on_callback_query(filters.regex("^back_to_main$"))
async def back_to_main_handler(client, query: CallbackQuery):
    await query.message.edit_text(
        "📂 **Backup Manager**\n\n"
        "• /backup - Generate backup\n"
        "• /restore - Restore from file",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("Close", callback_data="close_menu")
        ]])
    )

