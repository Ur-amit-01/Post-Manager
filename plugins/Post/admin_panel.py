
from plugins.helper.db import db
from pyrogram import Client, filters
from pyrogram.types import Message
from config import *
import os
import asyncio
from datetime import datetime
import json


async def admins_only(_, __, message):
    if not message.from_user:
        return False
    return await db.is_admin(message.from_user.id)

admin_filter = filters.create(admins_only)

#========================================================================================        

@Client.on_message(filters.command("promote") & filters.user(ADMIN))
async def promote_user(client, message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply("Reply to a user or use: /promote user_id")
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        try:
            user_id = int(message.command[1])
        except:
            return await message.reply("Invalid user ID!")

    await db.add_admin(user_id)
    await message.reply(f"✅ Promoted user {user_id} to admin!")

@Client.on_message(filters.command("demote") & filters.user(ADMIN))
async def demote_user(client, message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply("Reply to a user or use: /demote user_id")
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        try:
            user_id = int(message.command[1])
        except:
            return await message.reply("Invalid user ID!")

    await db.remove_admin(user_id)
    await message.reply(f"❌ Demoted user {user_id}")


@Client.on_message(filters.command("listadmins") & filters.user(ADMIN))
async def list_admins(client, message):
    """List all admins with details"""
    admins = await db.get_all_admins()
    if not admins:
        return await message.reply("No admins found!")
    
    text = "👑 **Admin List**\n\n"
    for admin in admins:
        try:
            user = await client.get_users(admin["_id"])
            text += f"• {user.mention} (`{user.id}`)\n"
            text += f"  ⏰ Added: `{admin.get('added_at', 'Unknown')}`\n"
            text += f"  🔍 Last Active: `{admin.get('last_active', 'Never')}`\n\n"
        except:
            text += f"• Unknown User (`{admin['_id']}`)\n\n"
    
    await message.reply(text)
    
# Dont touch above code
#========================================================================================

@Client.on_message(filters.command("backup") & admin_filter)
async def backup_data(client, message):
    """Simple backup of channels and admins to JSON"""
    try:
        # Get all channels and admins
        channels = await db.get_all_channels()
        admins = await db.get_all_admins()
        
        # Prepare backup data
        backup = {
            "channels": channels,
            "admins": admins,
            "backup_date": str(datetime.now())
        }
        
# Save to JSON file
        timestamp = datetime.now().strftime("%d-%m-%Y")
        filename = f"{BOT_USERNAME}_backup_{timestamp}.json"
        with open(filename, "w") as f:
            json.dump(backup, f, indent=4)
        
        # Send the file
        await client.send_document(
            chat_id=message.chat.id,
            document=filename,
            caption="**🔰 Backup**"
        )
        
        # Clean up
        os.remove(filename)
        await message.reply("**✅ Backup completed successfully!**")
        
    except Exception as e:
        await message.reply(f"**❌ Backup failed: {str(e)}**")

@Client.on_message(filters.command("restore") & admin_filter)
async def restore_data(client, message):
    """Restore channels and admins from JSON backup"""
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("**⚠️ Please reply to a backup file**")
    
    try:
        # Download the backup file
        file = await message.reply_to_message.download()
        
        # Load the backup data
        with open(file, "r") as f:
            backup = json.load(f)
        
        # Restore channels
        for channel in backup.get("channels", []):
            await db.add_channel(channel["_id"], channel.get("name"))
        
        # Restore admins
        for admin in backup.get("admins", []):
            await db.add_admin(admin["_id"])
        
        # Clean up
        os.remove(file)
        await message.reply("**✅ Restore completed successfully!**")
        
    except Exception as e:
        await message.reply(f"**❌ Restore failed: {str(e)}**")
        if os.path.exists(file):
            os.remove(file)
