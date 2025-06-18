
from datetime import datetime, timedelta
import time
import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db
import random
import asyncio
from config import *
from plugins.Post.admin_panel import admin_filter

# ... (keep your previous commands) ...

@Client.on_message(filters.command("genlink") & filters.private & admin_filter)
async def generate_invite_links(client, message: Message):
    # Parse time argument
    expire_time = None
    time_suffix = ""
    if len(message.command) > 1:
        time_arg = message.command[1].lower()
        if match := re.match(r"^(\d+)([mhd])$", time_arg):
            num, unit = match.groups()
            num = int(num)
            if unit == 'm':
                expire_time = timedelta(minutes=num)
                time_suffix = f"⏳ Expires in {num} minutes"
            elif unit == 'h':
                expire_time = timedelta(hours=num)
                time_suffix = f"⏳ Expires in {num} hours"
            elif unit == 'd':
                expire_time = timedelta(days=num)
                time_suffix = f"⏳ Expires in {num} days"

    # Initial processing message
    processing_msg = await message.reply("🔄 <b>Generating fresh links...</b>")

    # Generate links
    links = {}
    success_count = 0
    for channel in await db.get_all_channels():
        try:
            invite = await client.create_chat_invite_link(
                chat_id=channel['_id'],
                name=f"Link_{datetime.now().strftime('%m%d%H%M')}",
                expire_date=datetime.now() + expire_time if expire_time else None
            )
            links[channel['_id']] = {
                'link': invite.invite_link,
                'name': channel['name']
            }
            success_count += 1
        except Exception as e:
            print(f"Error in {channel['name']}: {str(e)}")

    # Prepare response
    header = (
        f"✨ <b>Generated Fresh links for {success_count} channels.</b>\n"
        f"{time_suffix}\n\n"
    )
    
    channel_links = "\n".join(
        f"• <a href='{info['link']}'><b>{info['name']}</b></a>"
        for info in links.values()
    )

    footer = (
        "\n\n**⚠️ <i>These links will be automatically revoked when:</i>**\n"
        "**- You generate new links**\n"
        "**- They expire (if time set)**\n"
        "**- You click 'Revoke Now'**"
    ) if links else ""

    # Create buttons
    buttons = []
    if links:
        buttons.append([InlineKeyboardButton("🔴 Revoke Now", callback_data="revoke_all")])
    
    await processing_msg.delete()
    await message.reply(
        header + channel_links + footer,
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        disable_web_page_preview=True
    )

    # Store links
    client.generated_links = links

    # Schedule auto-revocation
    if expire_time:
        asyncio.create_task(auto_revoke_links(client, links, expire_time))

@Client.on_callback_query(filters.regex("^revoke_all$"))
async def revoke_all_links(client, callback_query: CallbackQuery):
    if not hasattr(client, 'generated_links'):
        await callback_query.answer("❌ No active links found!", show_alert=True)
        return

    await callback_query.answer("⏳ Revoking links...")
    
    revoked = 0
    for chat_id, info in client.generated_links.items():
        try:
            await client.revoke_chat_invite_link(chat_id, info['link'])
            revoked += 1
        except:
            continue

    # Update original message
    await callback_query.message.edit_text(
        f"✅ <b>Revoked {revoked} links</b>\n"
        f"**All previous links are now invalid**",
        reply_markup=None
    )
    
    del client.generated_links
