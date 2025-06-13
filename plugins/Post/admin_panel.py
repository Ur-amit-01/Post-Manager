
from plugins.helper.db import db
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from config import *

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

