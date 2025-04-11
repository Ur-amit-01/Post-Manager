import asyncio
import time
import re
from datetime import datetime, time as dt_time, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from config import ADMIN
from plugins.helper.db import db

# ========================
# SCHEDULER FUNCTIONS
# ========================

async def schedule_daily_post(client, post_id):
    """Schedule the daily posting job"""
    post = await db.daily_posts.find_one({"_id": post_id})
    if not post:
        return

    async def job():
        post = await db.daily_posts.find_one({"_id": post_id})
        if not post or not post["schedule"]["is_active"]:
            return

        # Get all channels
        channels = await db.get_all_channels()
        
        for channel in channels:
            try:
                msg = await client.copy_message(
                    chat_id=channel["_id"],
                    from_chat_id=post["content"]["chat_id"],
                    message_id=post["content"]["message_id"]
                )
                
                if post["schedule"]["delete_after"] > 0:
                    asyncio.create_task(
                        delete_later(client, channel["_id"], msg.id, post["schedule"]["delete_after"])
                    )
                
            except Exception as e:
                print(f"Failed to post {post_id} to {channel['_id']}: {e}")

        # Update last posted time
        await db.daily_posts.update_one(
            {"_id": post_id},
            {"$set": {"schedule.last_posted": time.time()}}
        )

    # Schedule the job
    hour, minute = map(int, post["schedule"]["post_time"].split(":"))
    client.scheduler.add_job(
        job,
        "cron",
        hour=hour,
        minute=minute,
        id=f"daily_{post_id}"
    )

async def delete_later(client, chat_id, message_id, delay_seconds):
    """Helper for auto-deletion"""
    await asyncio.sleep(delay_seconds)
    try:
        await client.delete_messages(chat_id, message_id)
    except:
        pass

# ========================
# UTILITY FUNCTIONS
# ========================

def parse_time_to_seconds(time_str: str) -> int:
    """Convert time string to seconds"""
    time_str = time_str.lower()
    if "min" in time_str or "m" in time_str:
        return int(re.sub(r"[^\d]", "", time_str)) * 60
    elif "hour" in time_str or "hr" in time_str or "h" in time_str:
        return int(re.sub(r"[^\d]", "", time_str)) * 3600
    elif "day" in time_str or "d" in time_str:
        return int(re.sub(r"[^\d]", "", time_str)) * 86400
    return int(re.sub(r"[^\d]", "", time_str)) if time_str.isdigit() else 0

def format_time(seconds: int) -> str:
    """Convert seconds to human-readable time"""
    if seconds >= 86400:
        return f"{seconds // 86400} day(s)"
    elif seconds >= 3600:
        return f"{seconds // 3600} hour(s)"
    elif seconds >= 60:
        return f"{seconds // 60} minute(s)"
    return f"{seconds} second(s)"

# ========================
# COMMAND HANDLERS
# ========================

@Client.on_message(filters.command("daily") & filters.private)
async def daily_command(client, message: Message):
    """Main menu for daily posts"""
    user_id = message.from_user.id
    
    # Count existing posts
    post_count = await db.daily_posts.count_documents({"user_id": user_id})
    
    buttons = [
        [InlineKeyboardButton("➕ Schedule New Post", callback_data="daily_new")],
        [InlineKeyboardButton("📋 My Daily Posts", callback_data="daily_list")]
    ]
    
    await message.reply(
        f"⏰ **Daily Post Manager**\n\n"
        f"• Active Posts: {post_count}/10\n"
        f"• Manage your scheduled content:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ========================
# CALLBACK HANDLERS
# ========================

@Client.on_callback_query(filters.regex("^daily_new$"))
async def new_daily_post(client, callback: CallbackQuery):
    """Start creating new daily post"""
    await callback.message.edit_text(
        "📤 **Step 1/3**\n"
        "Forward me the message you want to post daily:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 Cancel", callback_data="daily_cancel")]
        ])
    )
    await callback.answer()

@Client.on_callback_query(filters.regex("^daily_list$"))
async def list_daily_posts(client, callback: CallbackQuery):
    """Show user's daily posts"""
    user_id = callback.from_user.id
    posts = await db.daily_posts.find({"user_id": user_id}).to_list(None)
    
    if not posts:
        return await callback.answer("You have no daily posts!", show_alert=True)
    
    buttons = []
    for post in posts:
        status = "⏸ Paused" if not post["schedule"]["is_active"] else "▶ Active"
        buttons.append([
            InlineKeyboardButton(
                f"{post['schedule']['post_time']} ({status})",
                callback_data=f"daily_detail_{post['_id']}"
            )
        ])
    
    buttons.append([InlineKeyboardButton("🔙 Back", callback_data="daily_back")])
    
    await callback.message.edit_text(
        "📅 Your Daily Posts:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback.answer()

@Client.on_callback_query(filters.regex(r"^daily_detail_"))
async def show_daily_post(client, callback: CallbackQuery):
    """Show details of a specific daily post"""
    post_id = callback.data.split("_")[2]
    post = await db.daily_posts.find_one({"_id": post_id})
    
    if not post:
        return await callback.answer("Post not found!", show_alert=True)
    
    # Get the original content
    try:
        content = await client.get_messages(
            chat_id=post["content"]["chat_id"],
            message_ids=post["content"]["message_id"]
        )
    except:
        return await callback.answer("Original message not found!", show_alert=True)
    
    status = "⏸ Paused" if not post["schedule"]["is_active"] else "▶ Active"
    delete_time = "Never" if post["schedule"]["delete_after"] == 0 else format_time(post["schedule"]["delete_after"])
    
    # Create action buttons
    action_button = InlineKeyboardButton(
        "⏸ Pause" if post["schedule"]["is_active"] else "▶ Resume",
        callback_data=f"daily_toggle_{post_id}"
    )
    
    buttons = [
        [action_button],
        [InlineKeyboardButton("🗑 Delete", callback_data=f"daily_delete_{post_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="daily_list")]
    ]
    
    # Send the original content with controls
    await content.copy(
        chat_id=callback.message.chat.id,
        caption=f"⏰ Daily at {post['schedule']['post_time']}\n"
                f"🗑 Auto-delete: {delete_time}\n"
                f"📌 Status: {status}",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback.answer()

@Client.on_callback_query(filters.regex(r"^daily_toggle_"))
async def toggle_daily_post(client, callback: CallbackQuery):
    """Toggle pause/resume for daily post"""
    post_id = callback.data.split("_")[2]
    post = await db.daily_posts.find_one({"_id": post_id})
    
    new_status = not post["schedule"]["is_active"]
    await db.daily_posts.update_one(
        {"_id": post_id},
        {"$set": {"schedule.is_active": new_status}}
    )
    
    # Update scheduler
    if new_status:
        await schedule_daily_post(client, post_id)
    else:
        try:
            client.scheduler.remove_job(f"daily_{post_id}")
        except:
            pass
    
    await callback.answer(f"Post {'paused' if not new_status else 'resumed'}!")
    await show_daily_post(client, callback)  # Refresh the view

@Client.on_callback_query(filters.regex(r"^daily_delete_"))
async def delete_daily_post(client, callback: CallbackQuery):
    """Delete a daily post"""
    post_id = callback.data.split("_")[2]
    
    # Remove from scheduler
    try:
        client.scheduler.remove_job(f"daily_{post_id}")
    except:
        pass
    
    await db.daily_posts.delete_one({"_id": post_id})
    await callback.answer("Daily post deleted!")
    await list_daily_posts(client, callback)  # Go back to list

@Client.on_callback_query(filters.regex("^daily_back$"))
async def back_to_daily_menu(client, callback: CallbackQuery):
    """Return to main daily menu"""
    await daily_command(client, callback.message)
    await callback.answer()

@Client.on_callback_query(filters.regex("^daily_cancel$"))
async def cancel_daily_creation(client, callback: CallbackQuery):
    """Cancel current operation"""
    user_id = callback.from_user.id
    await db.temp_daily.delete_one({"user_id": user_id})
    await daily_command(client, callback.message)
    await callback.answer("Operation cancelled")

@Client.on_callback_query(filters.regex("^daily_nodelete$"))
async def set_no_deletion(client, callback: CallbackQuery):
    """Set no deletion time"""
    msg = await callback.message.edit_text(
        "🗑 **Step 3/3**\n"
        "Enter 'no' to keep posts forever:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 Cancel", callback_data="daily_cancel")]
        ])
    )
    await callback.answer()

# ========================
# MESSAGE HANDLERS
# ========================

@Client.on_message(filters.private & filters.forwarded)
async def handle_daily_content(client, message: Message):
    """Step 1: Capture forwarded content"""
    if not message.forward_from_chat:
        return
    
    # Store temporarily
    await db.temp_daily.update_one(
        {"user_id": message.from_user.id},
        {"$set": {
            "content": {
                "message_id": message.forward_from_message_id,
                "chat_id": message.forward_from_chat.id
            }
        }},
        upsert=True
    )
    
    await message.reply(
        "⏰ **Step 2/3**\n"
        "Enter the daily posting time (24h format):\n\n"
        "Example: `09:30` or `15:00`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🚫 Cancel", callback_data="daily_cancel")]
        ])
    )

@Client.on_message(filters.regex(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'))
async def set_daily_time(client, message: Message):
    """Step 2: Set posting time"""
    user_id = message.from_user.id
    post_time = message.text
    
    # Validate time
    try:
        dt_time.strptime(post_time, "%H:%M")
    except ValueError:
        return await message.reply("❌ Invalid time format! Use HH:MM (24h)")
    
    # Update temp data
    await db.temp_daily.update_one(
        {"user_id": user_id},
        {"$set": {"schedule.post_time": post_time}},
        upsert=True
    )
    
    await message.reply(
        "🗑 **Step 3/3**\n"
        "Should I delete this post after some time?\n\n"
        "Examples:\n"
        "• `no` (keep forever)\n"
        "• `30min`\n"
        "• `2h`\n"
        "• `1day`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏳ No Deletion", callback_data="daily_nodelete")],
            [InlineKeyboardButton("🚫 Cancel", callback_data="daily_cancel")]
        ])
    )

@Client.on_message(filters.regex(r'^(no|(\d+\s?(min|m|h|hr|hour|day|d)))'))
async def set_delete_time(client, message: Message):
    """Finalize daily post creation"""
    user_id = message.from_user.id
    temp_data = await db.temp_daily.find_one({"user_id": user_id})
    
    if not temp_data:
        return await message.reply("❌ Session expired. Start over with /daily")
    
    # Parse delete time
    delete_text = message.text.lower()
    delete_after = 0 if delete_text == "no" else parse_time_to_seconds(delete_text)
    
    # Create daily post
    post_id = f"daily_{user_id}_{int(time.time())}"
    post_data = {
        "_id": post_id,
        "user_id": user_id,
        "content": temp_data["content"],
        "schedule": {
            "post_time": temp_data["schedule"]["post_time"],
            "delete_after": delete_after,
            "is_active": True,
            "last_posted": 0
        }
    }
    
    await db.daily_posts.insert_one(post_data)
    await db.temp_daily.delete_one({"user_id": user_id})
    
    # Start scheduler
    await schedule_daily_post(client, post_id)
    
    await message.reply(
        f"✅ Daily post scheduled for {temp_data['schedule']['post_time']}!\n\n"
        f"• Auto-delete: {'Never' if delete_after == 0 else format_time(delete_after)}\n"
        f"• Status: Active",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📋 My Daily Posts", callback_data="daily_list")]
        ])
    )

# ========================
# INITIALIZATION
# ========================

async def initialize_daily_scheduler(client):
    """Initialize all scheduled posts on bot startup"""
    active_posts = await db.daily_posts.find({"schedule.is_active": True}).to_list(None)
    for post in active_posts:
        await schedule_daily_post(client, post["_id"])

# Add this to your bot's startup:
# asyncio.create_task(initialize_daily_scheduler(client))
