import os
from datetime import datetime, timedelta
from io import BytesIO

import matplotlib.pyplot as plt
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import *
from pyrogram.filters import command
from bson.objectid import ObjectId

# Initialize Pyrogram Client
app = Client(
    "neet_todo_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# MongoDB Setup
mongo_client = MongoClient(DB_URL)
db = mongo_client["neet_study_bot"]
users_col = db["users"]
tasks_col = db["tasks"]
revisions_col = db["revisions"]
stats_col = db["statistics"]
premium_col = db["premium_users"]

# Scheduler for reminders
scheduler = BackgroundScheduler()
scheduler.start()

# Temporary storage for task creation
user_temp_data = {}

# Helper Functions
def schedule_revisions(task_id, user_id):
    """Schedule revision reminders for a completed task"""
    revision_days = [1, 4, 7, 15, 30]
    created_date = datetime.now()
    
    for day in revision_days:
        revision_date = created_date + timedelta(days=day)
        
        revision_data = {
            "task_id": task_id,
            "user_id": user_id,
            "revision_date": revision_date,
            "revision_day": day,
            "is_done": False,
            "reminder_sent": False
        }
        
        revisions_col.insert_one(revision_data)
        
        scheduler.add_job(
            send_revision_reminder,
            'date',
            run_date=revision_date,
            args=[app, str(task_id), user_id, day]
        )
    
    users_col.update_one(
        {"user_id": user_id},
        {"$inc": {"pending_revisions": len(revision_days)}}
    )

async def send_revision_reminder(client, task_id, user_id, revision_day):
    """Send revision reminder to user"""
    task = tasks_col.find_one({"_id": ObjectId(task_id)})
    if not task:
        return
    
    revisions_col.update_one(
        {"task_id": ObjectId(task_id), "user_id": user_id, "revision_day": revision_day},
        {"$set": {"reminder_sent": True, "reminder_sent_at": datetime.now()}}
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Revised", callback_data=f"revised_{task_id}_{revision_day}"),
            InlineKeyboardButton("⏰ Remind Later", callback_data=f"remind_later_{task_id}_{revision_day}")
        ]
    ])
    
    await client.send_message(
        user_id,
        f"⏰ Revision Reminder (Day {revision_day})\n\n"
        f"📝 Task: {task['task_text']}\n\n"
        "Have you revised this today?",
        reply_markup=keyboard
    )

def record_task_completion(user_id):
    """Record task completion for statistics"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    stats_col.update_one(
        {"user_id": user_id, "date": today},
        {"$inc": {"total": 1}},
        upsert=True
    )

def generate_progress_chart(user_id):
    """Generate progress chart for the user"""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    dates = []
    completed = []
    for i in range(30, -1, -1):
        date = (datetime.now() - timedelta(days=i)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        dates.append(date.strftime("%d %b"))
        
        stats = stats_col.find_one({"user_id": user_id, "date": date})
        completed.append(stats["total"] if stats else 0)
    
    ax.bar(dates, completed, color='#4CAF50')
    ax.set_title("📈 Tasks Completed in Last 30 Days")
    ax.set_xlabel("Date")
    ax.set_ylabel("Tasks Completed")
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    
    return buf

async def update_task_message(message, user_id):
    """Update the task message with current status"""
    tasks = list(tasks_col.find({"user_id": user_id}).sort("created_at", -1))
    
    if not tasks:
        await message.edit_text("**Congratulations 🎉. You've completed all your tasks! Use /addtask to add more.**")
        return
    
    completed = sum(1 for t in tasks if t["is_completed"])
    completion_rate = (completed / len(tasks)) * 100 if tasks else 0
    
    keyboard = []
    for task in tasks:
        status = "✅" if task["is_completed"] else "◻️"
        btn_text = f"{status} {task['task_text'][:30]}"
        keyboard.append([
            InlineKeyboardButton(
                btn_text, 
                callback_data=f"task_{task['_id']}"
            ),
            InlineKeyboardButton(
                "❌", 
                callback_data=f"delete_{task['_id']}"
            )
        ])
    
    progress_text = (
        f"**📋 Your Tasks**\n"
        f"**> • Progress :- {completed}/{len(tasks)} ~ ({completion_rate:.1f}%)\n\n**"
        f"**Click on Task to mark it. ✅**\n"
        f"**Click ❌ to delete task.**"
    )
    
    await message.edit_text(
        progress_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def is_premium(user_id):
    """Check if user has active premium subscription"""
    premium_user = premium_col.find_one({
        "user_id": user_id,
        "expiry_date": {"$gt": datetime.now()}
    })
    return premium_user is not None

# Command Handlers
@app.on_message(filters.command(["start", "help"]))
async def start(client, message):
    user_id = message.from_user.id
    user_data = {
        "user_id": user_id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name,
        "last_name": message.from_user.last_name or "",
        "join_date": datetime.now(),
        "last_active": datetime.now(),
        "total_tasks": 0,
        "completed_tasks": 0,
        "pending_revisions": 0
    }
    
    users_col.update_one(
        {"user_id": user_id},
        {"$setOnInsert": user_data},
        upsert=True
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add Tasks", callback_data="add_task_btn"),
            InlineKeyboardButton("📋 My Tasks", callback_data="my_tasks_btn")
        ],
        [
            InlineKeyboardButton("📊 Statistics", callback_data="stats_btn"),
            InlineKeyboardButton("📈 Progress Report", callback_data="report_btn")
        ]
    ])
    
    if is_premium(user_id):
        keyboard.inline_keyboard.append([InlineKeyboardButton("💎 Premium Features", callback_data="premium_btn")])
    else:
        keyboard.inline_keyboard.append([InlineKeyboardButton("💎 Get Premium", callback_data="premium_info")])
    
    await message.reply_photo(
        photo="https://telegra.ph/file/5e53a3e5a5a3e9a5e5a3e.jpg",
        caption=(
            "🌟 *Welcome to TaskMaster Pro!* 🌟\n\n"
            "🚀 *Supercharge your productivity with:*\n"
            "• 📝 Smart task management\n"
            "• ⏰ Intelligent revision reminders\n"
            "• 📊 Detailed analytics\n\n"
            "✨ *Get started by adding your first task!*"
        ),
        reply_markup=keyboard
    )

@app.on_message(filters.command("addtask"))
async def add_task(client, message):
    user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Done ✅", callback_data="done_adding_tasks")]
    ])

    await message.reply_text(
        "**📩 Please send me your tasks one by one.**\n"
        "**Click the button below when you're done:**",
        reply_markup=keyboard
    )
    
    user_temp_data[user_id] = {"adding_task": True}

@app.on_message(filters.command("mytasks"))
async def show_tasks(client, message):
    user_id = message.from_user.id
    tasks = list(tasks_col.find({"user_id": user_id}).sort("created_at", -1))
    
    if not tasks:
        await message.reply_text("🎉 You don't have any tasks yet!\nUse /addtask to get started.")
        return
    
    completed = sum(1 for t in tasks if t["is_completed"])
    completion_rate = (completed / len(tasks)) * 100 if tasks else 0
    
    keyboard = []
    for task in tasks:
        status = "✅" if task["is_completed"] else "◻️"
        btn_text = f"{status} {task['task_text'][:30]}"
        keyboard.append([
            InlineKeyboardButton(
                btn_text, 
                callback_data=f"task_{task['_id']}"
            ),
            InlineKeyboardButton(
                "❌", 
                callback_data=f"delete_{task['_id']}"
            )
        ])
    
    progress_text = (
        f"**📋 Your Tasks**\n"
        f"**> • Progress :- {completed}/{len(tasks)} ~ ({completion_rate:.1f}%)\n\n**"
        f"**Click on Task to mark it. ✅**\n"
        f"**Click ❌ to delete task.**"
    )
    
    await message.reply_text(
        progress_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@app.on_message(filters.command("stats"))
async def show_stats(client, message):
    user_id = message.from_user.id
    user = users_col.find_one({"user_id": user_id})
    tasks = list(tasks_col.find({"user_id": user_id}))
    
    if not tasks:
        await message.reply_text("🎯 You don't have any tasks yet!\nUse /addtask to get started.")
        return
    
    completed = user.get("completed_tasks", 0)
    total = user.get("total_tasks", 1)
    completion_rate = (completed / total) * 100
    
    week_ago = datetime.now() - timedelta(days=7)
    weekly_completed = tasks_col.count_documents({
        "user_id": user_id,
        "is_completed": True,
        "completion_date": {"$gte": week_ago}
    })
    
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    streak = 0
    current_date = today
    while True:
        day_stats = stats_col.find_one({"user_id": user_id, "date": current_date})
        if day_stats and day_stats.get("total", 0) > 0:
            streak += 1
            current_date -= timedelta(days=1)
        else:
            break
    
    stats_text = (
        f"📊 *Your Productivity Dashboard*\n\n"
        f"📌 Total Tasks: {total}\n"
        f"✅ Completed: {completed} ({completion_rate:.1f}%)\n"
        f"📅 Completed this week: {weekly_completed}\n"
        f"🔥 Current streak: {streak} day{'s' if streak != 1 else ''}\n"
        f"⏳ Pending revisions: {user.get('pending_revisions', 0)}\n\n"
        f"💡 *Tip:* Complete at least 1 task daily to maintain your streak!"
    )
    
    await message.reply_text(stats_text)

@app.on_message(filters.command("report"))
async def generate_report(client, message):
    user_id = message.from_user.id
    
    chart = generate_progress_chart(user_id)
    await message.reply_photo(
        photo=chart,
        caption="📈 *Your 30-Day Progress Report*\n\nCheck your detailed statistics below:"
    )
    
    await show_stats(client, message)

# Run the bot
if __name__ == "__main__":
    print("🚀 TaskMaster Pro Bot is running...")
    try:
        app.run()
    except KeyboardInterrupt:
        print("🛑 Bot stopped by user")
    finally:
        scheduler.shutdown()
        mongo_client.close()
