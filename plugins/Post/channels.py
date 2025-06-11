from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db
import time
import random
import asyncio
from config import *

# Command to add the current channel to the database
@Client.on_message(filters.command("add") & filters.channel)
async def add_current_channel(client, message: Message):
    channel_id = message.chat.id
    channel_name = message.chat.title

    try:
        added = await db.add_channel(channel_id, channel_name)
        if added:
            await message.reply(f"**Channel '{channel_name}' added! ✅**")
        else:
            await message.reply(f"ℹ️ Channel '{channel_name}' already exists.")
    except Exception as e:
        print(f"Error adding channel: {e}")
        await message.reply("❌ Failed to add channel. Contact developer.")

# Command to remove the current channel from the database
@Client.on_message(filters.command("rem") & filters.channel)
async def remove_current_channel(client, message: Message):
    channel_id = message.chat.id
    channel_name = message.chat.title

    try:
        if await db.is_channel_exist(channel_id):
            await db.delete_channel(channel_id)
            await message.reply(f"**Channel '{channel_name}' removed from my database!**")
        else:
            await message.reply(f"ℹ️ Channel '{channel_name}' not found.")
    except Exception as e:
        print(f"Error removing channel: {e}")
        await message.reply("❌ Failed to remove channel. Try again.")

# Command to list all connected channels
@Client.on_message(filters.command("channels") & filters.private & filters.user(ADMIN))
async def list_channels(client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except:
        pass

    channels = await db.get_all_channels()

    if not channels:
        await message.reply("**No channels connected yet.🙁**")
        return

    total_channels = len(channels)
    channel_list = [f"• **{channel['name']}** :- `{channel['_id']}`" for channel in channels]

    header = f"> **Total Channels :- ({total_channels})**\n\n"
    messages = []
    current_message = header

    for line in channel_list:
        if len(current_message) + len(line) + 1 > 4096:
            messages.append(current_message)
            current_message = ""
        current_message += line + "\n"

    if current_message:
        messages.append(current_message)

    for part in messages:
        await message.reply(part)

@Client.on_message(filters.command("amit") & filters.private & filters.user(ADMIN))
async def manage_admins(client, message: Message):
    """
    Command to promote/demote users as admins in all connected channels
    Usage: /amit [promote/demote] [user_id or @username]
    """
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except:
        pass

    if len(message.command) < 3:
        return await message.reply(
            "**Usage:**\n"
            "`/amit promote user_id/@username` - Promote user in all channels\n"
            "`/amit demote user_id/@username` - Demote user from all channels\n\n"
            "**Note:** Bot must be admin with appropriate rights in all channels."
        )

    action = message.command[1].lower()
    user_identifier = message.command[2]

    if action not in ["promote", "demote"]:
        return await message.reply("Invalid action. Use 'promote' or 'demote'.")

    try:
        # Try to resolve the user
        try:
            user = await client.get_users(user_identifier)
            user_id = user.id
            user_name = user.first_name
        except Exception as e:
            return await message.reply(f"Failed to find user: {e}")

        processing_msg = await message.reply(f"⏳ Processing {action} for {user_name}...")

        channels = await db.get_all_channels()
        if not channels:
            return await processing_msg.edit("**No channels connected yet.🙁**")

        success_count = 0
        failed_count = 0
        results = []

        for channel in channels:
            channel_id = channel['_id']
            channel_name = channel['name']

            try:
                # Check if bot is admin in the channel
                bot_member = await client.get_chat_member(channel_id, "me")
                
                # Version-agnostic permission check
                if not getattr(bot_member, 'can_promote_members', False):
                    results.append(f"❌ {channel_name} - No promote rights")
                    failed_count += 1
                    continue

                # Prepare promotion/demotion parameters
                admin_rights = {
                    'chat_id': channel_id,
                    'user_id': user_id,
                    'can_change_info': False,
                    'can_post_messages': action == "promote",
                    'can_edit_messages': action == "promote",
                    'can_delete_messages': action == "promote",
                    'can_restrict_members': action == "promote",
                    'can_invite_users': action == "promote",
                    'can_pin_messages': action == "promote",
                    'can_promote_members': False,
                    'can_manage_chat': action == "promote",
                    'can_manage_video_chats': action == "promote",
                    'is_anonymous': False
                }

                # Clean up None values for older Pyrogram versions
                admin_rights = {k: v for k, v in admin_rights.items() if v is not None}

                await client.promote_chat_member(**admin_rights)
                action_result = "Promoted" if action == "promote" else "Demoted"
                results.append(f"✅ {channel_name} - {action_result}")
                success_count += 1

                await asyncio.sleep(0.3)  # Rate limiting

            except Exception as e:
                error_msg = str(e).lower()
                if "user not found" in error_msg:
                    reason = "User not in channel"
                elif "not enough rights" in error_msg:
                    reason = "Missing permissions"
                elif "user is an administrator" in error_msg and action == "promote":
                    reason = "Already admin"
                elif "can't remove owner" in error_msg:
                    reason = "User is owner"
                else:
                    reason = f"Error: {str(e)[:50]}..."
                
                results.append(f"❌ {channel_name} - {reason}")
                failed_count += 1

        # Format results
        header = (
            f"**🔧 Admin {action.capitalize()} Results for {user_name}**\n"
            f"**✅ Success: {success_count} | ❌ Failed: {failed_count}**\n\n"
        )
        
        # Split long messages if needed
        message_text = header + "\n".join(results)
        if len(message_text) > 4096:
            parts = [message_text[i:i+4096] for i in range(0, len(message_text), 4096)]
            await processing_msg.delete()
            for part in parts:
                await message.reply(part, disable_web_page_preview=True)
        else:
            await processing_msg.edit_text(
                text=message_text,
                disable_web_page_preview=True
            )

    except Exception as e:
        await message.reply(f"**Error:** {str(e)}")
