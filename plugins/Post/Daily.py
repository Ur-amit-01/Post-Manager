import asyncio
import time
import re
from datetime import datetime, time as dt_time, timedelta
from typing import Dict, Union
from pyrogram import Client, filters
from pyrogram.types import (
    InlineKeyboardMarkup, 
    InlineKeyboardButton, 
    Message, 
    CallbackQuery,
    ForceReply
)
from config import ADMIN
from plugins.helper.db import db

# Global state tracker
user_states: Dict[int, dict] = {}  # {user_id: {"state": str, "data": dict}}

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

        await db.daily_posts.update_one(
            {"_id": post_id},
            {"$set": {"schedule.last_posted": time.time()}}
        )

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

def validate_time_input(time_str: str) -> tuple:
    """Validate and parse time input with flexible formats"""
    time_str = time_str.strip().lower()
    
    # Handle 12-hour format with AM/PM
    if re.match(r'^(1[0-2]|0?[1-9]):([0-5][0-9])\s?(am|pm)$', time_str):
        try:
            time_part, period = time_str.split()
            hour, minute = map(int, time_part.split(':'))
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute:02d}", True
        except:
            return None, False
    
    # Handle 24-hour format
    elif re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
        try:
            hour, minute = map(int, time_str.split(':'))
            return f"{hour:02d}:{minute:02d}", True
        except:
            return None, False
    
    # Handle simple hour format
    elif re.match(r'^(1[0-2]|0?[1-9])\s?(am|pm)$', time_str):
        try:
            parts = re.split(r'(\d+)\s?(am|pm)', time_str)
            hour = int(parts[1])
            period = parts[2]
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            return f"{hour:02d}:00", True
        except:
            return None, False
    
    return None, False

# ========================
# COMMAND HANDLERS
# ========================

@Client.on_message(filters.command("daily") & filters.private)
async def daily_command(client, message: Message):
    """Main menu for daily posts"""
    user_id = message.from_user.id
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
# POST CREATION FLOW
# ========================

@Client.on_callback_query(filters.regex("^daily_new$"))
async def new_daily_post(client, callback: CallbackQuery):
    """Start creating new daily post"""
    user_id = callback.from_user.id
    user_states[user_id] = {
        "state": "awaiting_content",
        "data": {}
    }
    
    buttons = [
        [InlineKeyboardButton("📤 Forward a Message", callback_data="forward_content")],
        [InlineKeyboardButton("✏️ Create New Message", callback_data="create_content")],
        [InlineKeyboardButton("🚫 Cancel", callback_data="daily_cancel")]
    ]
    
    await callback.message.edit_text(
        "📤 **Step 1/3**\n"
        "Choose how to provide content:\n\n"
        "1. Forward an existing message\n"
        "2. Create a new message directly",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback.answer()

@Client.on_callback_query(filters.regex("^(forward_content|create_content|back_to_time_input)$"))
async def handle_content_selection(client, callback: CallbackQuery):
    """Handle content selection and move to time input"""
    user_id = callback.from_user.id
    
    if callback.data == "forward_content":
        user_states[user_id]["state"] = "awaiting_forwarded"
        await callback.message.edit_text(
            "📤 Please forward the message you want to post daily:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚫 Cancel", callback_data="daily_cancel")]
            ])
        )
    elif callback.data == "create_content":
        user_states[user_id]["state"] = "awaiting_new_content"
        await callback.message.edit_text(
            "✏️ Please send the message you want to post daily:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚫 Cancel", callback_data="daily_cancel")]
            ])
        )
    else:  # back_to_time_input
        await request_time_input(client, callback.message)
    
    await callback.answer()

@Client.on_message(filters.private & (filters.forwarded | (filters.text & ~filters.command)))
async def handle_content_input(client, message: Message):
    """Handle both forwarded and new content"""
    user_id = message.from_user.id
    
    if user_id not in user_states:
        return
    
    state = user_states[user_id]["state"]
    
    if state == "awaiting_forwarded":
        if not message.forward_from_chat:
            await message.reply("❌ Please forward a message from a channel or group")
            return
            
        user_states[user_id]["data"] = {
            "content_type": "forwarded",
            "message_id": message.forward_from_message_id,
            "chat_id": message.forward_from_chat.id
        }
        await request_time_input(client, message)
        
    elif state == "awaiting_new_content":
        # Store the message directly
        user_states[user_id]["data"] = {
            "content_type": "new",
            "message_id": message.id,
            "chat_id": message.chat.id
        }
        await request_time_input(client, message)

async def request_time_input(client, message: Union[Message, CallbackQuery]):
    """Request time input using force reply"""
    if isinstance(message, CallbackQuery):
        message = message.message
    
    user_id = message.from_user.id
    user_states[user_id]["state"] = "awaiting_time"
    
    buttons = [
        [InlineKeyboardButton("🕘 Suggest Times", callback_data="suggest_times")],
        [InlineKeyboardButton("🚫 Cancel", callback_data="daily_cancel")]
    ]
    
    msg = await message.reply(
        "⏰ **Step 2/3**\n"
        "Please reply to this message with your posting time:\n\n"
        "Formats accepted:\n"
        "• 09:30 (24h)\n"
        "• 2:30pm (12h)\n"
        "• 3pm (hour only)\n",
        reply_markup=ForceReply(selective=True),
        reply_to_message_id=message.id
    )
    
    # Store the force reply message ID
    user_states[user_id]["force_reply_msg"] = msg.id

@Client.on_message(filters.private & filters.reply & ~filters.command("daily"))
async def handle_time_reply(client, message: Message):
    """Handle time input from force reply"""
    user_id = message.from_user.id
    
    # Check if this is a reply to our force reply message
    if (user_id not in user_states or 
        user_states[user_id].get("state") != "awaiting_time" or
        message.reply_to_message_id != user_states[user_id].get("force_reply_msg")):
        return
    
    time_str = message.text.strip()
    formatted_time, valid = validate_time_input(time_str)
    
    if not valid:
        await message.reply(
            "❌ Invalid time format. Please reply again with:\n"
            "• 09:30 (24h)\n"
            "• 2:30pm (12h)\n"
            "• 3pm (hour only)\n\n"
            "Reply to the previous message:",
            reply_to_message_id=user_states[user_id]["force_reply_msg"],
            reply_markup=ForceReply(selective=True)
        )
        return
    
    # Store the time and move to next step
    user_states[user_id]["data"]["post_time"] = formatted_time
    user_states[user_id]["state"] = "awaiting_delete"
    
    # Clean up force reply tracking
    user_states[user_id].pop("force_reply_msg", None)
    
    await request_delete_option(client, message)

@Client.on_callback_query(filters.regex("^suggest_times$"))
async def suggest_times(client, callback: CallbackQuery):
    """Suggest common times with force reply compatibility"""
    common_times = ["08:00", "12:00", "15:00", "18:00", "21:00", "9am", "12pm", "3pm", "6pm", "9pm"]
    
    buttons = [
        [InlineKeyboardButton(time, callback_data=f"select_time_{time}")]
        for time in common_times
    ]
    buttons.append([InlineKeyboardButton("↩️ Back", callback_data="back_to_time_input")])
    
    await callback.message.edit_text(
        "🕘 Select a suggested time (will auto-fill):",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback.answer()

@Client.on_callback_query(filters.regex(r"^select_time_"))
async def handle_time_selection(client, callback: CallbackQuery):
    """Handle time selection from suggestions"""
    time_str = callback.data.split("_")[2]
    user_id = callback.from_user.id
    
    formatted_time, valid = validate_time_input(time_str)
    if not valid:
        await callback.answer("Invalid time format", show_alert=True)
        return
    
    # Store the selected time
    user_states[user_id]["data"]["post_time"] = formatted_time
    user_states[user_id]["state"] = "awaiting_delete"
    
    # Clean up force reply tracking if exists
    user_states[user_id].pop("force_reply_msg", None)
    
    await request_delete_option(client, callback.message)
    await callback.answer(f"Selected: {formatted_time}")

async def request_delete_option(client, message: Union[Message, CallbackQuery]):
    """Request delete after option"""
    if isinstance(message, CallbackQuery):
        message = message.message
    
    buttons = [
        [
            InlineKeyboardButton("30m", callback_data="delete_30m"),
            InlineKeyboardButton("1h", callback_data="delete_1h"),
            InlineKeyboardButton("3h", callback_data="delete_3h")
        ],
        [
            InlineKeyboardButton("6h", callback_data="delete_6h"),
            InlineKeyboardButton("12h", callback_data="delete_12h"),
            InlineKeyboardButton("1d", callback_data="delete_1d")
        ],
        [
            InlineKeyboardButton("⏳ Never Delete", callback_data="delete_never"),
            InlineKeyboardButton("✏️ Custom Time", callback_data="delete_custom")
        ],
        [InlineKeyboardButton("🚫 Cancel", callback_data="daily_cancel")]
    ]
    
    await message.reply(
        "🗑 **Step 3/3**\n"
        "When should I delete this post after posting?\n\n"
        "Select from common options or specify custom time:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# [Rest of the handlers (delete options, confirmation, etc.) remain the same]
# [Include all the other handlers from the original code]

# ========================
# INITIALIZATION
# ========================

async def initialize_daily_scheduler(client):
    """Initialize all scheduled posts on bot startup"""
    active_posts = await db.daily_posts.find({"schedule.is_active": True}).to_list(None)
    for post in active_posts:
        await schedule_daily_post(client, post["_id"])
