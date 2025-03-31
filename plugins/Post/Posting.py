from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db  # Database helper
import time
import random
from plugins.helper.time_parser import *
import asyncio
from datetime import datetime, timedelta
from config import *
    
@Client.on_message(filters.command("post") & filters.private & filters.user(ADMIN))
async def send_post(client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)  # React with a random emoji
    except:
        pass
    # Check if the user is replying to a message
    if not message.reply_to_message:
        await message.reply("**Reply to a message to post it.**")
        return

    # Parse time delay if provided
    delete_after = None
    time_input = None
    if len(message.command) > 1:
        try:
            time_input = ' '.join(message.command[1:]).lower()
            delete_after = parse_time(time_input)
            if delete_after <= 0:
                await message.reply("❌ Time must be greater than 0")
                return
        except ValueError as e:
            await message.reply(f"❌ {str(e)}\nExample: /post 1h 30min or /post 2 hours 15 minutes")
            return

    post_content = message.reply_to_message
    channels = await db.get_all_channels()

    if not channels:
        await message.reply("**No channels connected yet.**")
        return

    # Generate a unique post ID (using timestamp)
    post_id = int(time.time())
    sent_messages = []
    success_count = 0
    total_channels = len(channels)

    # Send initial processing message (now as reply to original content)
    processing_msg = await message.reply(
        f"**📢 Posting to {total_channels} channels...**",
        reply_to_message_id=post_content.id
    )

    for channel in channels:
        try:
            # Copy the message to the channel
            sent_message = await client.copy_message(
                chat_id=channel["_id"],
                from_chat_id=message.chat.id,
                message_id=post_content.id
            )

            sent_messages.append({
                "channel_id": channel["_id"],
                "message_id": sent_message.id,
                "channel_name": channel.get("name", str(channel["_id"]))
            })
            success_count += 1

            # Schedule deletion if time was specified
            if delete_after:
                asyncio.create_task(
                    schedule_deletion(
                        client,
                        channel["_id"],
                        sent_message.id,
                        delete_after,
                        message.from_user.id,
                        post_id,
                        channel.get("name", str(channel["_id"])),
                        processing_msg.id  # Pass confirmation message ID to delete later
                    )
                )
                
        except Exception as e:
            print(f"Error posting to channel {channel['_id']}: {e}")

    # Save the post with its unique ID
    if sent_messages:
        await db.save_post(post_id, sent_messages)

    # Prepare the result message (replaces processing message)
    result_msg = (
        f"📣 <b>Posting Completed!</b>\n\n"
        f"• <b>Post ID:</b> <code>{post_id}</code>\n"
        f"• <b>Success:</b> {success_count}/{total_channels} channels\n"
    )
    if delete_after:
        time_str = format_time(delete_after)
        result_msg += f"• <b>Auto-delete in:</b> {time_str}\n"

    if success_count < total_channels:
        result_msg += f"• <b>Failed:</b> {total_channels - success_count} channels\n"

    # Create inline keyboard with delete button
    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗑 Delete This Post", callback_data=f"delete_{post_id}")]
    ])

    # Edit the processing message with final result and delete button
    await processing_msg.edit_text(result_msg, reply_markup=reply_markup)


async def schedule_deletion(client, channels, sent_messages, delay_seconds, user_id, post_id):
    """Schedule a message for deletion after a delay"""
    await asyncio.sleep(delay_seconds)

    failed_channels = []
    
    for msg in sent_messages:
        try:
            await client.delete_messages(chat_id=msg["channel_id"], message_ids=msg["message_id"])
        except Exception as e:
            failed_channels.append(msg["channel_name"])

    try:
        # Send a single confirmation message
        confirmation_msg = (
            f"🗑 <b>Auto Post Deleted</b>\n\n"
            f"• <b>Post ID:</b> <code>{post_id}</code>\n"
            f"• <b>Deleted in:</b> {len(sent_messages) - len(failed_channels)} channels\n"
        )

        if failed_channels:
            confirmation_msg += f"• <b>Failed:</b> {len(failed_channels)} channels\n"

        await client.send_message(user_id, confirmation_msg)
        
    except Exception as e:
        print(f"Error sending confirmation: {e}")
