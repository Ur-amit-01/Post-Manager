from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import datetime, timedelta
import time
import re

# ... (keep your previous commands) ...

@Client.on_message(filters.command("genlink") & filters.private & admin_filter)
async def generate_invite_links(client, message: Message):
    # Parse time argument (e.g. "/genlink 10m")
    expire_time = None
    if len(message.command) > 1:
        time_arg = message.command[1].lower()
        if match := re.match(r"^(\d+)([mhd])$", time_arg):
            num, unit = match.groups()
            num = int(num)
            if unit == 'm':
                expire_time = timedelta(minutes=num)
            elif unit == 'h':
                expire_time = timedelta(hours=num)
            elif unit == 'd':
                expire_time = timedelta(days=num)

    channels = await db.get_all_channels()
    
    # Generate links
    links = {}
    for channel in channels:
        try:
            invite = await client.create_chat_invite_link(
                chat_id=channel['_id'],
                name=f"BotGen_{datetime.now().strftime('%Y%m%d')}",
                expire_date=datetime.now() + expire_time if expire_time else None
            )
            links[channel['_id']] = {
                'link': invite.invite_link,
                'name': channel['name'],
                'revoke_token': invite.invite_link.split('/')[-1]  # Extract unique part
            }
        except Exception as e:
            print(f"Error generating link for {channel['name']}: {e}")

    # Send results with revoke button
    text = "**Generated Links**\n\n" + "\n".join(
        f"🔗 [{info['name']}]({info['link']})" + 
        (f" (expires in {expire_time})" if expire_time else "")
        for _, info in links.items()
    )

    reply_markup = None
    if links:
        reply_markup = InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Revoke All Links", callback_data="revoke_all")
        ]])

    await message.reply(
        text,
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

    # Store links for possible revocation
    if hasattr(client, 'generated_links'):
        client.generated_links.update(links)
    else:
        client.generated_links = links

    # Schedule auto-revocation if time specified
    if expire_time:
        asyncio.create_task(auto_revoke_links(client, links, expire_time))

async def auto_revoke_links(client, links, delay):
    await asyncio.sleep(delay.total_seconds())
    for channel_id, info in links.items():
        try:
            await client.revoke_chat_invite_link(
                chat_id=channel_id,
                invite_link=info['link']
            )
            print(f"Auto-revoked link for {info['name']}")
        except Exception as e:
            print(f"Error revoking link for {info['name']}: {e}")

@Client.on_callback_query(filters.regex("^revoke_all$"))
async def revoke_all_links(client, callback_query: CallbackQuery):
    if not hasattr(client, 'generated_links') or not client.generated_links:
        await callback_query.answer("No active links to revoke!", show_alert=True)
        return

    await callback_query.answer("Revoking all links...")
    
    success = failed = 0
    for channel_id, info in client.generated_links.items():
        try:
            await client.revoke_chat_invite_link(
                chat_id=channel_id,
                invite_link=info['link']
            )
            success += 1
        except Exception as e:
            print(f"Error revoking {info['name']}: {e}")
            failed += 1

    await callback_query.message.reply(
        f"🔒 Revoked {success} links\n"
        f"⚠️ Failed to revoke {failed} links"
    )
    
    # Clear stored links
    client.generated_links.clear()
