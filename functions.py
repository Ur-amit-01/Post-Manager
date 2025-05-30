import os
from datetime import datetime, timedelta
from io import BytesIO

import matplotlib.pyplot as plt
from apscheduler.schedulers.background import BackgroundScheduler
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import *

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

# Scheduler for reminders
scheduler = BackgroundScheduler()
scheduler.start()

# Temporary storage for task creation
user_temp_data = {}

# Helper Functions
def schedule_revisions(task_id, user_id, subject):
    """Schedule revision reminders for a completed task"""
    revision_days = [1, 4, 7, 15, 30]
    created_date = datetime.now()
    
    for day in revision_days:
        revision_date = created_date + timedelta(days=day)
        
        revision_data = {
            "task_id": task_id,
            "user_id": user_id,
            "subject": subject,
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
            args=[app, task_id, user_id, day]
        )
    
    users_col.update_one(
        {"user_id": user_id},
        {"$inc": {"pending_revisions": len(revision_days)}}
    )

async def send_revision_reminder(client, task_id, user_id, revision_day):
    """Send revision reminder to user"""
    task = tasks_col.find_one({"_id": task_id})
    if not task:
        return
    
    revisions_col.update_one(
        {"task_id": task_id, "user_id": user_id, "revision_day": revision_day},
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
        f"Subject: {task['subject']}\n"
        f"Topic: {task['task_text']}\n\n"
        "Have you revised this topic today?",
        reply_markup=keyboard
    )

def record_task_completion(user_id, subject):
    """Record task completion for statistics"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    stats_col.update_one(
        {"user_id": user_id, "date": today},
        {"$inc": {f"subjects.{subject}": 1, "total": 1}},
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
    
    ax.bar(dates, completed, color='skyblue')
    ax.set_title("Tasks Completed in Last 30 Days")
    ax.set_xlabel("Date")
    ax.set_ylabel("Tasks Completed")
    plt.xticks(rotation=45)
    plt.tight_layout()
    
    buf = BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    plt.close()
    
    return buf

# Command Handlers
@app.on_message(filters.command("start"))
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
    
    await message.reply_text(
        "📚 NEET Study Tracker Bot\n\n"
        "Manage your study targets with:\n"
        "- Task tracking ✓\n"
        "- Spaced repetition ⏰\n"
        "- Progress analytics 📈\n\n"
        "Commands:\n"
        "/addtask - Add new study target\n"
        "/mytasks - View your tasks\n"
        "/stats - View your progress\n"
        "/report - Get detailed performance report"
    )

@app.on_message(filters.command("addtask"))
async def add_task(client, message):
    user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Physics", callback_data="addtask_Physics"),
            InlineKeyboardButton("Chemistry", callback_data="addtask_Chemistry"),
            InlineKeyboardButton("Biology", callback_data="addtask_Biology")
        ]
    ])
    
    await message.reply_text(
        "Select the subject for your new task:",
        reply_markup=keyboard
    )

@app.on_callback_query(filters.regex("^addtask_"))
async def process_task_subject(client, callback_query):
    subject = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    
    await callback_query.message.edit_text(f"Now enter your {subject} study target:")
    
    user_temp_data[user_id] = {"adding_task": True, "subject": subject}

@app.on_message(filters.private & ~command(["start", "addtask", "mytasks", "stats", "report"]))
async def process_task_description(client, message):
    user_id = message.from_user.id
    
    if not user_temp_data.get(user_id, {}).get("adding_task"):
        return
    
    task_text = message.text
    subject = user_temp_data[user_id]["subject"]
    
    task_data = {
        "user_id": user_id,
        "task_text": task_text,
        "subject": subject,
        "created_at": datetime.now(),
        "is_completed": False,
        "completion_date": None,
        "priority": 1
    }
    
    tasks_col.insert_one(task_data)
    users_col.update_one({"user_id": user_id}, {"$inc": {"total_tasks": 1}})
    
    await message.reply_text(f"✅ {subject} task added: {task_text}")
    user_temp_data.pop(user_id, None)

@app.on_message(filters.command("mytasks"))
async def show_tasks(client, message):
    user_id = message.from_user.id
    tasks = list(tasks_col.find({"user_id": user_id}).sort("created_at", -1))
    
    if not tasks:
        await message.reply_text("You don't have any tasks yet. Use /addtask to add one.")
        return
    
    completed = sum(1 for t in tasks if t["is_completed"])
    completion_rate = (completed / len(tasks)) * 100 if tasks else 0
    
    keyboard = []
    for task in tasks:
        status = "✅" if task["is_completed"] else "🔄"
        subject_icon = {
            "Physics": "⚛️",
            "Chemistry": "🧪",
            "Biology": "🧬"
        }.get(task["subject"], "📝")
        
        btn_text = f"{status} {subject_icon} {task['task_text']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"task_{task['_id']}")])
    
    progress_text = (
        f"📊 Your Progress: {completed}/{len(tasks)} tasks completed ({completion_rate:.1f}%)\n"
        f"⚛️ Physics: {sum(1 for t in tasks if t['subject'] == 'Physics' and t['is_completed'])}/{sum(1 for t in tasks if t['subject'] == 'Physics')}\n"
        f"🧪 Chemistry: {sum(1 for t in tasks if t['subject'] == 'Chemistry' and t['is_completed'])}/{sum(1 for t in tasks if t['subject'] == 'Chemistry')}\n"
        f"🧬 Biology: {sum(1 for t in tasks if t['subject'] == 'Biology' and t['is_completed'])}/{sum(1 for t in tasks if t['subject'] == 'Biology')}\n\n"
        "Click on a task to toggle its status:"
    )
    
    await message.reply_text(
        progress_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

@app.on_callback_query(filters.regex("^task_"))
async def toggle_task_status(client, callback_query):
    task_id = callback_query.data.split("_")[1]
    user_id = callback_query.from_user.id
    
    task = tasks_col.find_one({"_id": task_id, "user_id": user_id})
    if not task:
        await callback_query.answer("Task not found!")
        return
    
    new_status = not task["is_completed"]
    update_data = {
        "is_completed": new_status,
        "completion_date": datetime.now() if new_status else None
    }
    
    tasks_col.update_one({"_id": task_id}, {"$set": update_data})
    users_col.update_one({"user_id": user_id}, {"$inc": {"completed_tasks": 1 if new_status else -1}})
    
    if new_status:
        schedule_revisions(task_id, user_id, task["subject"])
        record_task_completion(user_id, task["subject"])
    
    await callback_query.answer("Task status updated!")
    await show_tasks(client, callback_query.message)

@app.on_callback_query(filters.regex("^revised_"))
async def mark_as_revised(client, callback_query):
    parts = callback_query.data.split("_")
    task_id = parts[1]
    revision_day = int(parts[2])
    user_id = callback_query.from_user.id
    
    revisions_col.update_one(
        {"task_id": task_id, "user_id": user_id, "revision_day": revision_day},
        {"$set": {"is_done": True, "completed_at": datetime.now()}}
    )
    
    users_col.update_one({"user_id": user_id}, {"$inc": {"pending_revisions": -1}})
    
    await callback_query.answer("Great job! Keep revising regularly.")
    await callback_query.message.delete()

@app.on_callback_query(filters.regex("^remind_later_"))
async def remind_later(client, callback_query):
    parts = callback_query.data.split("_")
    task_id = parts[2]
    revision_day = int(parts[3])
    user_id = callback_query.from_user.id
    
    new_time = datetime.now() + timedelta(hours=3)  # Remind after 3 hours
    
    scheduler.add_job(
        send_revision_reminder,
        'date',
        run_date=new_time,
        args=[app, task_id, user_id, revision_day]
    )
    
    await callback_query.answer("Okay, I'll remind you again in 3 hours!")
    await callback_query.message.delete()

@app.on_message(filters.command("stats"))
async def show_stats(client, message):
    user_id = message.from_user.id
    tasks = list(tasks_col.find({"user_id": user_id}))
    
    if not tasks:
        await message.reply_text("You don't have any tasks yet. Use /addtask to add one.")
        return
    
    completed = sum(1 for t in tasks if t["is_completed"])
    completion_rate = (completed / len(tasks)) * 100 if tasks else 0
    
    subjects = ["Physics", "Chemistry", "Biology"]
    subject_stats = {}
    for subject in subjects:
        total = sum(1 for t in tasks if t["subject"] == subject)
        done = sum(1 for t in tasks if t["subject"] == subject and t["is_completed"])
        subject_stats[subject] = {
            "total": total,
            "done": done,
            "percent": (done / total * 100) if total else 0
        }
    
    week_ago = datetime.now() - timedelta(days=7)
    weekly_completed = tasks_col.count_documents({
        "user_id": user_id,
        "is_completed": True,
        "completion_date": {"$gte": week_ago}
    })
    
    stats_text = (
        f"📊 Your Study Statistics\n\n"
        f"📝 Total Tasks: {len(tasks)}\n"
        f"✅ Completed: {completed} ({completion_rate:.1f}%)\n"
        f"📅 Completed this week: {weekly_completed}\n\n"
        f"Subject-wise Completion:\n"
    )
    
    for subject, stats in subject_stats.items():
        icon = {
            "Physics": "⚛️",
            "Chemistry": "🧪",
            "Biology": "🧬"
        }[subject]
        
        stats_text += (
            f"{icon} {subject}: {stats['done']}/{stats['total']} "
            f"({stats['percent']:.1f}%)\n"
        )
    
    await message.reply_text(stats_text)

@app.on_message(filters.command("report"))
async def generate_report(client, message):
    user_id = message.from_user.id
    
    chart = generate_progress_chart(user_id)
    await message.reply_photo(
        photo=chart,
        caption="📈 Your 30-Day Progress Report"
    )
    
    await show_stats(client, message)

# Run the bot
if __name__ == "__main__":
    print("NEET Study Tracker Bot is running...")
    try:
        app.run()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    finally:
        scheduler.shutdown()
        mongo_client.close()
