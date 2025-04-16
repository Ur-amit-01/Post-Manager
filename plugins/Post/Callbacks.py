from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db  # Database helper
import time
import random
import asyncio
from datetime import datetime, timedelta
from config import *

# ========================================= CALLBACKS =============================================
# Callback Query Handler

@Client.on_callback_query()
async def cb_handler(client: Client, query: CallbackQuery):
    data = query.data

    if data.startswith("delete_"):
        try:
            await query.answer("Processing deletion...")
            post_id = int(data.split("_")[1])
            
            # Retrieve the post's details from the database
            post = await db.get_post(post_id)
            
            if not post:
                await query.answer("❌ Post not found or already deleted", show_alert=True)
                await query.message.edit_text(
                    f"❌ <b>Deletion Failed</b>\n\n"
                    f"• <b>Post ID:</b> <code>{post_id}</code>\n"
                    f"• <b>Reason:</b> Post not found in database"
                )
                return

            processing_msg = await query.message.edit_text(
                f"🗑 <b>Deleting Post ID:</b> <code>{post_id}</code>\n\n"
                f"• <b>Channels: {len(post.get('channels', []))}</b>\n"
                f"⏳ <b><i>Processing deletion...</i></b>"
            )

            channels = post.get("channels", [])
            success_count = 0
            failed_count = 0
            failed_channels = []

            for channel in channels:
                try:
                    await client.delete_messages(
                        chat_id=channel["channel_id"],
                        message_ids=channel["message_id"]
                    )
                    success_count += 1
                    # Remove from database after successful deletion
                    await db.remove_channel_post(post_id, channel["channel_id"])
                except Exception as e:
                    failed_count += 1
                    failed_channels.append(
                        f"  - {channel.get('channel_name', channel['channel_id'])}: {str(e)}"
                    )

            # Check if all channels were deleted
            remaining_channels = await db.get_post_channels(post_id)
            if not remaining_channels:
                await db.delete_post(post_id)

            result_msg = (
                f"🗑 <b>Post Deletion Results</b>\n\n"
                f"• <b>Post ID:</b> <code>{post_id}</code>\n"
                f"• <b>Successfully deleted from:</b> {success_count} channel(s)\n"
            )
            
            if failed_count > 0:
                result_msg += (
                    f"• <b>Failed to delete from:</b> {failed_count} channel(s)\n"
                    f"\n<b>Errors:</b>\n"
                )
                # Show up to 5 error messages to avoid too long messages
                result_msg += "\n".join(failed_channels[:5])
                if len(failed_channels) > 5:
                    result_msg += f"\n  - (and {len(failed_channels)-5} more errors...)"

            await processing_msg.edit_text(result_msg)

        except Exception as e:
            print(f"Error in callback deletion handler: {e}")
            await query.answer("❌ An error occurred during deletion", show_alert=True)
            await query.message.edit_text(
                f"❌ <b>Deletion Failed</b>\n\n"
                f"• <b>Error:</b> {str(e)}\n"
                f"• Please try again or check logs"
            )
    
    elif data == "start":
        txt = (
            f"> **✨👋🏻 Hey {query.from_user.mention} !!**\n"
            f"**Welcome to the Channel Manager Bot, Manage multiple channels and post messages with ease! 😌**\n\n"
            f"> **ᴅᴇᴠᴇʟᴏᴘᴇʀ 🧑🏻‍💻 :- @Axa_bachha**"
        )
        
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton('📜 ᴀʙᴏᴜᴛ', callback_data='about'),
             InlineKeyboardButton('🕵🏻‍♀️ ʜᴇʟᴘ', callback_data='help')]
        ])

    elif data == "hel":
        txt = HELP_TXT
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("ʀᴇᴏ̨ᴜᴇsᴛ ᴀᴄᴄᴇᴘᴛᴏʀ", callback_data="request")],
            [InlineKeyboardButton("ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴄᴏɴᴛᴇɴᴛ sᴀᴠᴇʀ", callback_data="restricted")],
            [InlineKeyboardButton('🏠 𝙷𝙾𝙼𝙴 🏠', callback_data='start')]
        ])

    elif data == "about":
        txt = ABOUT_TXT.format(client.mention)
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("🤖 ᴅᴇᴠᴇʟᴏᴘᴇʀ", url="https://t.me/axa_bachha"),
             InlineKeyboardButton("🏠 𝙷𝙾𝙼𝙴 🏠", callback_data="start")]
        ])

    elif data == "restricted":
        txt = RESTRICTED_TXT
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ 𝙱𝙰𝙲𝙺", callback_data="help")]
        ])

    elif data == "request":
        txt = REQUEST_TXT.format(client.mention)
        reply_markup = InlineKeyboardMarkup([
            [InlineKeyboardButton("◀️ 𝙱𝙰𝙲𝙺", callback_data="help")]
        ])

    await query.message.edit_text(text=txt, reply_markup=reply_markup, disable_web_page_preview=True)


# ========================================= TEXTS =============================================

LOG_TEXT = """<blockquote><b>#NewUser ॥ @interferons_bot </b></blockquote>
<blockquote><b>☃️ Nᴀᴍᴇ :~ {}
🪪 ID :~ <code>{}</code>
👨‍👨‍👦‍👦 ᴛᴏᴛᴀʟ :~ {}</b></blockquote>"""


ABOUT_TXT = """
<b>╭───────────⍟
├➢ ᴍʏꜱᴇʟꜰ : {}
├➢ ᴅᴇᴠᴇʟᴏᴘᴇʀ : <a href=https://t.me/axa_bachha>𝐻𝑜𝑚𝑜 𝑠𝑎𝑝𝑖𝑒𝑛『❅』</a>
├➢ ʟɪʙʀᴀʀʏ : <a href=https://github.com/pyrogram>ᴘʏʀᴏɢʀᴀᴍ</a>
├➢ ʟᴀɴɢᴜᴀɢᴇ : <a href=https://www.python.org>ᴘʏᴛʜᴏɴ 3</a>
├➢ ᴅᴀᴛᴀʙᴀꜱᴇ : <a href=https://cloud.mongodb.com>MᴏɴɢᴏDB</a>
├➢ ꜱᴇʀᴠᴇʀ : <a href=https://apps.koyeb.com>ᴋᴏʏᴇʙ</a>
├➢ ʙᴜɪʟᴅ ꜱᴛᴀᴛᴜꜱ  : ᴘʏᴛʜᴏɴ v3.6.8
╰───────────────⍟

➢ ɴᴏᴛᴇ :- Interested Owners can DM for personal bot. 🤝🏻
</b>"""

HELP_TXT = """
🛸 <b><u>My Functions</u></b> 🛸
"""


RESTRICTED_TXT = """
> **💡 Restricted Content Saver**

**1. 🔒 Private Chats**
➥ For My Owner Only :)

**2. 🌐 Public Chats**
➥ Simply share the post link. I'll download it for you.

**3. 📂 Batch Mode**
➥ Download multiple posts using this format:
> **https://t.me/xxxx/1001-1010**
"""

REQUEST_TXT = """
<b>
> ⚙️ Join Request Acceptor

• I can accept all pending join requests in your channel. 🤝

• Promote {} with full admin rights in your channel. 🔑

• Send /accept command in the channel to accept all requests at once. 💯
</b>
"""
