
from plugins.helper.db import db
from pyrogram import Client, filters
from pyrogram.types import Message
from config import *
import os
import asyncio
from datetime import datetime
import json
import time
import logging
from pyrogram.errors import FloodWait, InputUserDeactivated, UserIsBlocked, PeerIdInvalid

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
            text += f"**• {user.mention} (`{user.id}`)**\n"
            text += f"**  ⏰ Added: `{admin.get('added_at', 'Unknown')}`**\n\n"
        except:
            text += f"• Unknown User (`{admin['_id']}`)\n\n"
    
    await message.reply(text)
    
# Dont touch above code
#======================================== BROADCAST ================================================

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

@Client.on_message(filters.command("users") & filters.user(ADMIN))
async def get_stats(bot: Client, message: Message):
    mr = await message.reply('**𝙰𝙲𝙲𝙴𝚂𝚂𝙸𝙽𝙶 𝙳𝙴𝚃𝙰𝙸𝙻𝚂.....**')
    total_users = await db.total_users_count()
    await mr.edit(text=f"**❤️‍🔥 TOTAL USERS = {total_users}**")

@Client.on_message(filters.command("broadcast") & filters.user(ADMIN) & filters.reply)
async def broadcast_handler(bot: Client, m: Message):
    all_users = await db.get_all_users()
    broadcast_msg = m.reply_to_message
    sts_msg = await m.reply_text("Broadcast started!")
    
    done, failed, success = 0, 0, 0
    start_time = time.time()
    total_users = await db.total_users_count()

    async for user in all_users:
        sts = await send_msg(bot, user['_id'], broadcast_msg)
        if sts == 200:
            success += 1
        else:
            failed += 1
        if sts == 400:
            await db.delete_user(user['_id'])

        done += 1
        if not done % 20:
            await sts_msg.edit(
                f"**Broadcast in progress:\nTotal Users: {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nFailed: {failed}**"
            )

    completed_in = datetime.timedelta(seconds=int(time.time() - start_time))
    await sts_msg.edit(
        f"**Broadcast Completed:\nCompleted in `{completed_in}`.\n\nTotal Users: {total_users}\nCompleted: {done} / {total_users}\nSuccess: {success}\nFailed: {failed}**"
    )

async def send_msg(bot, user_id, message):
    try:
        await message.copy(chat_id=int(user_id))
        return 200
    except FloodWait as e:
        await asyncio.sleep(e.value)
        return await send_msg(bot, user_id, message)
    except InputUserDeactivated:
        logger.info(f"{user_id} : deactivated")
        return 400
    except UserIsBlocked:
        logger.info(f"{user_id} : blocked the bot")
        return 400
    except PeerIdInvalid:
        logger.info(f"{user_id} : user id invalid")
        return 400
    except Exception as e:
        logger.error(f"{user_id} : {e}")
        return 500

#======================================== BACKUP/RESTORE ================================================
@Client.on_message(filters.command("backup") & admin_filter)
async def backup_data(client, message):
    """Simple backup of channels and admins to JSON"""
    try:        
        # Get only the essential fields
        channels = [{"_id": c["_id"], "name": c.get("name")} for c in await db.get_all_channels()]
        admins = [{"_id": a["_id"]} for a in await db.get_all_admins()]
        
        # Prepare backup data
        backup = {
            "channels": channels,
            "admins": admins
        }
        
        # Save to JSON file
        me = await client.get_me()
        filename = f"{me.username}_backup.json"
        with open(filename, "w") as f:
            json.dump(backup, f, indent=4)
        
        # Send and clean up
        await client.send_document(message.chat.id, filename, caption="**🔰 Backup**")
        os.remove(filename)
        await message.reply("**✅ Backup completed successfully!**")
        
    except Exception as e:
        await message.reply(f"**❌ Backup failed: {str(e)}**")
        if os.path.exists(filename):
            os.remove(filename)
		

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
