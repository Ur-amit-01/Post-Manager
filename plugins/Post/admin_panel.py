
from plugins.helper.db import db
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import *
from plugins.helper.db import db
import os
import asyncio


async def admins_only(_, __, message):
    if not message.from_user:
        return False
    return await db.is_admin(message.from_user.id)

admin_filter = filters.create(admins_only)

        
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

# Usage: 
# /promote 123456  OR  Reply to user with /promote

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

@Client.on_message(filters.command("backup") & filters.user(ADMIN))
async def manual_backup(client, message):
    """Create and send manual backup"""
    msg = await message.reply("🔄 Creating database backup...")
    backup_file = await db.create_backup()
    
    if backup_file:
        try:
            # Send to owner
            await client.send_document(
                chat_id=OWNER_ID,
                document=backup_file,
                caption=f"📦 Database Backup\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )
            
            # Send to log channel
            await client.send_document(
                chat_id=LOG_CHANNEL,
                document=backup_file,
                caption="🔐 Database Backup"
            )
            
            await msg.edit_text("✅ Backup created and sent successfully!")
        except Exception as e:
            await msg.edit_text(f"❌ Failed to send backup: {str(e)}")
        finally:
            os.remove(backup_file)
    else:
        await msg.edit_text("❌ Backup creation failed!")

@Client.on_message(filters.command("import") & filters.user(ADMIN))
async def restore_database(client, message):
    """Restore database from backup file"""
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("Please reply to a backup file to restore")
    
    msg = await message.reply("🔁 Downloading backup file...")
    backup_path = await message.reply_to_message.download()
    
    await msg.edit_text("🔄 Restoring database...")
    success, result = await db.restore_backup(backup_path)
    
    if success:
        await msg.edit_text("✅ Database restored successfully!")
        await client.send_message(
            LOG_CHANNEL,
            f"♻️ Database was restored by {message.from_user.mention}"
        )
    else:
        await msg.edit_text(f"❌ Restore failed: {result}")
    
    os.remove(backup_path)

async def auto_backup_task(client):
    """Automatic weekly backup task"""
    while True:
        backup_file = await db.auto_backup()
        if backup_file:
            try:
                await client.send_document(
                    chat_id=OWNER_ID,
                    document=backup_file,
                    caption="📅 Auto Backup"
                )
                await client.send_document(
                    chat_id=LOG_CHANNEL,
                    document=backup_file,
                    caption="📅 Weekly Auto Backup"
                )
            finally:
                if os.path.exists(backup_file):
                    os.remove(backup_file)
        
        # Sleep for 1 day and check again
        await asyncio.sleep(600)  # 24 hours
