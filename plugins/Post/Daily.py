from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db
import time
import random
from plugins.helper.time_parser import *
import asyncio
from config import *
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Add this near your other imports
scheduler = AsyncIOScheduler()

async def start_scheduler(client):
    """Start the scheduler when bot starts"""
    scheduler.start()
    await restore_scheduled_posts(client)  # Restore any scheduled posts from DB

async def restore_scheduled_posts(client):
    """Restore scheduled posts from database when bot starts"""
    try:
        scheduled_posts = await db.get_scheduled_posts()  # You'll need to implement this in db.py
        for post in scheduled_posts:
            # Schedule each post again
            await schedule_auto_post(
                client,
                post["post_data"],
                post["schedule_time"],
                post["delete_after"],
                post["user_id"],
                post["_id"]  # schedule_id
            )
    except Exception as e:
        print(f"Error restoring scheduled posts: {e}")

@Client.on_message(filters.command("auto") & filters.private & filters.user(ADMIN))
async def schedule_post(client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except:
        pass
    
    if not message.reply_to_message:
        await message.reply("**Reply to a message to schedule it.**")
        return

    if len(message.command) < 3:
        await message.reply(
            "**Usage:** `/schedule HH:MM delete_time`\n"
            "**Example:** `/schedule 09:00 2h30m` - Posts daily at 9AM, deletes after 2.5 hours\n"
            "**Example:** `/schedule 15:30 1d` - Posts daily at 3:30PM, deletes after 1 day"
        )
        return

    try:
        # Parse schedule time
        schedule_time = message.command[1]
        hour, minute = map(int, schedule_time.split(':'))
        if not (0 <= hour < 24 and 0 <= minute < 60):
            raise ValueError("Invalid time format")

        # Parse delete after duration
        delete_after_input = ' '.join(message.command[2:]).lower()
        delete_after = parse_time(delete_after_input)
        if delete_after <= 0:
            await message.reply("❌ Delete duration must be greater than 0")
            return

    except ValueError as e:
        await message.reply(f"❌ {str(e)}\nExample: /schedule 09:00 2h30m")
        return

    post_content = message.reply_to_message
    channels = await db.get_all_channels()

    if not channels:
        await message.reply("**No channels connected yet.**")
        return

    # Generate a unique schedule ID
    schedule_id = int(time.time())
    post_id = f"auto_{schedule_id}"  # Auto posts get special IDs

    # Save the scheduled post data
    post_data = {
        "post_id": post_id,
        "content": post_content,  # You'll need to serialize this properly for storage
        "channels": [channel["_id"] for channel in channels],
        "user_id": message.from_user.id,
        "created_at": time.time(),
        "delete_after": delete_after,
        "is_auto_post": True
    }

    schedule_data = {
        "_id": schedule_id,
        "post_data": post_data,
        "schedule_time": schedule_time,
        "delete_after": delete_after,
        "user_id": message.from_user.id,
        "created_at": time.time()
    }

    await db.save_scheduled_post(schedule_data)  # Implement this in db.py

    # Schedule the post
    await schedule_auto_post(client, post_data, schedule_time, delete_after, message.from_user.id, schedule_id)

    time_str = format_time(delete_after)
    await message.reply(
        f"✅ <b>Post Scheduled Successfully!</b>\n\n"
        f"• <b>Schedule ID:</b> <code>{schedule_id}</code>\n"
        f"• <b>Will post daily at:</b> {schedule_time}\n"
        f"• <b>Auto-delete after:</b> {time_str}\n"
        f"• <b>Channels:</b> {len(channels)}"
    )

async def schedule_auto_post(client, post_data, schedule_time, delete_after, user_id, schedule_id):
    """Schedule an auto post with the given parameters"""
    hour, minute = map(int, schedule_time.split(':'))
    
    # Schedule the post to run daily at the specified time
    scheduler.add_job(
        execute_auto_post,
        CronTrigger(hour=hour, minute=minute),
        args=[client, post_data, delete_after, user_id, schedule_id],
        id=f"auto_post_{schedule_id}",
        replace_existing=True
    )

async def execute_auto_post(client, post_data, delete_after, user_id, schedule_id):
    """Execute the actual posting of an auto post"""
    try:
        post_id = post_data["post_id"]
        channels = post_data["channels"]
        content = post_data["content"]  # You'll need to deserialize this properly
        
        sent_messages = []
        deletion_tasks = []
        
        for channel_id in channels:
            try:
                # You'll need to implement proper message reconstruction from serialized content
                sent_message = await client.copy_message(
                    chat_id=channel_id,
                    from_chat_id=content["chat_id"],
                    message_id=content["message_id"]
                )

                sent_messages.append({
                    "channel_id": channel_id,
                    "message_id": sent_message.id,
                    "channel_name": str(channel_id)  # You might want to store channel names
                })

                if delete_after:
                    deletion_tasks.append(
                        schedule_deletion(
                            client,
                            channel_id,
                            sent_message.id,
                            delete_after,
                            user_id,
                            post_id,
                            str(channel_id),
                            None  # No confirmation message for auto posts
                        )
                    )
                    
            except Exception as e:
                print(f"Error posting to channel {channel_id}: {e}")

        # Update post data with sent messages
        post_data["channels"] = sent_messages
        post_data["posted_at"] = time.time()
        
        # Save the actual post (not the schedule)
        await db.save_post(post_data)

        if deletion_tasks:
            asyncio.create_task(
                handle_deletion_results(
                    client=client,
                    deletion_tasks=deletion_tasks,
                    post_id=post_id,
                    delay_seconds=delete_after
                )
            )

        # Log the auto post
        try:
            await client.send_message(
                chat_id=LOG_CHANNEL,
                text=f"🔄 <blockquote><b>#AutoPost | @Interferons_bot</b></blockquote>\n\n"
                     f"📌 <b>Schedule ID:</b> <code>{schedule_id}</code>\n"
                     f"📌 <b>Post ID:</b> <code>{post_id}</code>\n"
                     f"📡 <b>Sent to:</b> {len(sent_messages)} channels\n"
                     f"⏳ <b>Auto-delete in:</b> {format_time(delete_after)}"
            )
        except Exception as e:
            print(f"Error logging auto post: {e}")

    except Exception as e:
        print(f"Error executing auto post: {e}")
        try:
            await client.send_message(
                user_id,
                f"❌ Failed to execute scheduled post (ID: {schedule_id})\nError: {str(e)}"
            )
        except:
            pass

@Client.on_message(filters.command("listschedule") & filters.private & filters.user(ADMIN))
async def list_scheduled_posts(client, message: Message):
    """List all scheduled posts"""
    try:
        scheduled_posts = await db.get_all_scheduled_posts()  # Implement this in db.py
        
        if not scheduled_posts:
            await message.reply("No scheduled posts found.")
            return

        response = "📅 <b>Scheduled Posts:</b>\n\n"
        for post in scheduled_posts:
            response += (
                f"• <b>ID:</b> <code>{post['_id']}</code>\n"
                f"  <b>Time:</b> {post['schedule_time']}\n"
                f"  <b>Delete after:</b> {format_time(post['delete_after'])}\n"
                f"  <b>Channels:</b> {len(post['post_data']['channels'])}\n\n"
            )

        await message.reply(response)

    except Exception as e:
        await message.reply(f"Error listing scheduled posts: {str(e)}")

@Client.on_message(filters.command("del_auto") & filters.private & filters.user(ADMIN))
async def unschedule_post(client, message: Message):
    """Remove a scheduled post"""
    if len(message.command) < 2:
        await message.reply("Usage: /unschedule <schedule_id>")
        return

    try:
        schedule_id = int(message.command[1])
        
        # Remove from scheduler
        scheduler.remove_job(f"auto_post_{schedule_id}")
        
        # Remove from database
        await db.remove_scheduled_post(schedule_id)  # Implement this in db.py
        
        await message.reply(f"✅ Successfully unscheduled post (ID: {schedule_id})")

    except Exception as e:
        await message.reply(f"Error unscheduling post: {str(e)}")

# Add this to your bot startup
async def on_startup(client):
    await restore_pending_deletions(client)
    await start_scheduler(client)

