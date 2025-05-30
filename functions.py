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

# Scheduler for reminders
scheduler = BackgroundScheduler()
scheduler.start()

# Temporary storage for task creation
user_temp_data = {}
user_last_message = {}  # To track last message ID for each user

# Helper Functions
def schedule_revisions(task_id, user_id):
    """Schedule revision reminders for a completed task"""
    revision_days = [1, 4, 7, 15, 30]
    created_date = datetime.now()
    
    for day in revision_days:
        revision_date = created_date + timedelta(days=day)
        
        revision_data = {
            "task_id": task_id,  # This is now an ObjectId
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
            args=[app, str(task_id), user_id, day]  # Convert ObjectId to string for scheduling
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
        f"Task: {task['task_text']}\n\n"
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

async def update_task_message(client, user_id, message_id=None):
    """Update the task list message with current status"""
    tasks = list(tasks_col.find({"user_id": user_id}).sort("created_at", -1))
    
    if not tasks:
        if message_id:
            try:
                await client.edit_message_text(
                    user_id,
                    message_id,
                    "You don't have any tasks yet. Use /addtask to add one."
                )
            except:
                pass
        return
    
    completed = sum(1 for t in tasks if t["is_completed"])
    completion_rate = (completed / len(tasks)) * 100 if tasks else 0
    
    keyboard = []
    for task in tasks:
        status = "✅" if task["is_completed"] else "☐"
        btn_text = f"{status} {task['task_text'][:30]}"  # Limit text length
        keyboard.append([
            InlineKeyboardButton(
                btn_text, 
                callback_data=f"task_{task['_id']}"
            ),
            InlineKeyboardButton(
                "✅", 
                callback_data=f"complete_{task['_id']}"
            ),
            InlineKeyboardButton(
                "❌", 
                callback_data=f"delete_{task['_id']}"
            )
        ])
    
    # Add Done button at the bottom
    keyboard.append([
        InlineKeyboardButton("✅ Done", callback_data="done_viewing_tasks")
    ])
    
    progress_text = (
        f"📊 Your Progress: {completed}/{len(tasks)} tasks completed ({completion_rate:.1f}%)\n\n"
        "Click on a task to toggle its status or use buttons:"
    )
    
    if message_id:
        try:
            await client.edit_message_text(
                user_id,
                message_id,
                progress_text,
                reply_markup=InlineKeyboardMarkup(keyboard)
        except:
            pass
    else:
        msg = await client.send_message(
            user_id,
            progress_text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        user_last_message[user_id] = msg.id

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
        "📚 Task Tracker Bot\n\n"
        "Manage your tasks with:\n"
        "- Task tracking ✓\n"
        "- Spaced repetition ⏰\n"
        "- Progress analytics 📈\n\n"
        "Commands:\n"
        "/addtask - Add new task\n"
        "/mytasks - View your tasks\n"
        "/stats - View your progress\n"
        "/report - Get detailed performance report"
    )

@app.on_message(filters.command("addtask"))
async def add_task(client, message):
    user_id = message.from_user.id
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Done Adding Tasks", callback_data="done_adding_tasks")]
    ])
    
    # Delete previous message if exists
    if user_id in user_last_message:
        try:
            await client.delete_messages(user_id, user_last_message[user_id])
        except:
            pass
    
    msg = await message.reply_text(
        "Please send me your tasks one by one. Click the button below when you're done:",
        reply_markup=keyboard
    )
    user_last_message[user_id] = msg.id
    
    user_temp_data[user_id] = {"adding_task": True}

@app.on_message(filters.private & ~command(["start", "addtask", "mytasks", "stats", "report"]))
async def process_task_description(client, message):
    user_id = message.from_user.id
    
    if not user_temp_data.get(user_id, {}).get("adding_task"):
        return
    
    task_text = message.text
    
    task_data = {
        "user_id": user_id,
        "task_text": task_text,
        "created_at": datetime.now(),
        "is_completed": False,
        "completion_date": None,
        "priority": 1
    }
    
    result = tasks_col.insert_one(task_data)
    users_col.update_one({"user_id": user_id}, {"$inc": {"total_tasks": 1}})
    
    # Delete previous message if exists
    if user_id in user_last_message:
        try:
            await client.delete_messages(user_id, user_last_message[user_id])
        except:
            pass
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Done", callback_data=f"confirm_task_{result.inserted_id}")]
    ])
    
    msg = await message.reply_text(
        f"✅ Task added: {task_text}\n\n"
        "Click Done to confirm or send another task.",
        reply_markup=keyboard
    )
    user_last_message[user_id] = msg.id

@app.on_callback_query(filters.regex("^confirm_task_"))
async def confirm_task(client, callback_query):
    user_id = callback_query.from_user.id
    task_id = callback_query.data.split("_")[-1]
    
    # Delete confirmation message
    try:
        await callback_query.message.delete()
    except:
        pass
    
    await callback_query.answer("Task confirmed!")
    await show_tasks(client, callback_query.message)

@app.on_callback_query(filters.regex("^done_adding_tasks$"))
async def done_adding_tasks(client, callback_query):
    user_id = callback_query.from_user.id
    if user_id in user_temp_data:
        user_temp_data.pop(user_id)
    
    try:
        await callback_query.message.delete()
    except:
        pass
    
    await callback_query.answer("Task addition completed!")
    await show_tasks(client, callback_query.message)

@app.on_callback_query(filters.regex("^task_"))
async def toggle_task_status(client, callback_query):
    try:
        task_id = callback_query.data.split("_")[1]
        user_id = callback_query.from_user.id
        
        task = tasks_col.find_one({"_id": ObjectId(task_id), "user_id": user_id})
        
        if not task:
            await callback_query.answer("Task not found!", show_alert=True)
            return
        
        new_status = not task["is_completed"]
        update_data = {
            "is_completed": new_status,
            "completion_date": datetime.now() if new_status else None
        }
        
        tasks_col.update_one({"_id": ObjectId(task_id)}, {"$set": update_data})
        users_col.update_one(
            {"user_id": user_id}, 
            {"$inc": {"completed_tasks": 1 if new_status else -1}}
        )
        
        if new_status:
            schedule_revisions(ObjectId(task_id), user_id)
            record_task_completion(user_id)
        
        await callback_query.answer("Task status updated!")
        await update_task_message(client, user_id, callback_query.message.id)
    except Exception as e:
        print(f"Error in toggle_task_status: {e}")
        await callback_query.answer("Error updating task status", show_alert=True)

@app.on_callback_query(filters.regex("^complete_"))
async def complete_task(client, callback_query):
    try:
        task_id = callback_query.data.split("_")[1]
        user_id = callback_query.from_user.id
        
        task = tasks_col.find_one({"_id": ObjectId(task_id), "user_id": user_id})
        
        if not task:
            await callback_query.answer("Task not found!", show_alert=True)
            return
        
        if task["is_completed"]:
            await callback_query.answer("Task already completed!")
            return
        
        update_data = {
            "is_completed": True,
            "completion_date": datetime.now()
        }
        
        tasks_col.update_one({"_id": ObjectId(task_id)}, {"$set": update_data})
        users_col.update_one({"user_id": user_id}, {"$inc": {"completed_tasks": 1}})
        
        schedule_revisions(ObjectId(task_id), user_id)
        record_task_completion(user_id)
        
        await callback_query.answer("Task marked as completed!")
        await update_task_message(client, user_id, callback_query.message.id)
    except Exception as e:
        print(f"Error in complete_task: {e}")
        await callback_query.answer("Error completing task", show_alert=True)

@app.on_callback_query(filters.regex("^delete_"))
async def delete_task(client, callback_query):
    try:
        task_id = callback_query.data.split("_")[1]
        user_id = callback_query.from_user.id
        
        task = tasks_col.find_one({"_id": ObjectId(task_id), "user_id": user_id})
        
        if not task:
            await callback_query.answer("Task not found!", show_alert=True)
            return
        
        # Delete the task and any associated revisions
        tasks_col.delete_one({"_id": ObjectId(task_id)})
        revisions_col.delete_many({"task_id": ObjectId(task_id)})
        
        # Update user stats
        update_data = {"$inc": {"total_tasks": -1}}
        if task["is_completed"]:
            update_data["$inc"]["completed_tasks"] = -1
            # Decrement pending revisions count
            pending_revs = revisions_col.count_documents({
                "task_id": ObjectId(task_id),
                "is_done": False
            })
            if pending_revs > 0:
                users_col.update_one(
                    {"user_id": user_id},
                    {"$inc": {"pending_revisions": -pending_revs}}
                )
        
        users_col.update_one({"user_id": user_id}, update_data)
        
        await callback_query.answer("Task deleted!")
        await update_task_message(client, user_id, callback_query.message.id)
    except Exception as e:
        print(f"Error in delete_task: {e}")
        await callback_query.answer("Error deleting task", show_alert=True)

@app.on_callback_query(filters.regex("^done_viewing_tasks$"))
async def done_viewing_tasks(client, callback_query):
    user_id = callback_query.from_user.id
    
    try:
        await callback_query.message.delete()
    except:
        pass
    
    await callback_query.answer("Task viewing completed!")

@app.on_message(filters.command("mytasks"))
async def show_tasks(client, message):
    user_id = message.from_user.id
    
    # Delete previous message if exists
    if user_id in user_last_message:
        try:
            await client.delete_messages(user_id, user_last_message[user_id])
        except:
            pass
    
    await update_task_message(client, user_id)

@app.on_callback_query(filters.regex("^revised_"))
async def mark_as_revised(client, callback_query):
    parts = callback_query.data.split("_")
    task_id = parts[1]
    revision_day = int(parts[2])
    user_id = callback_query.from_user.id
    
    revisions_col.update_one(
        {"task_id": ObjectId(task_id), "user_id": user_id, "revision_day": revision_day},
        {"$set": {"is_done": True, "completed_at": datetime.now()}}
    )
    
    users_col.update_one({"user_id": user_id}, {"$inc": {"pending_revisions": -1}})
    
    await callback_query.answer("Great job! Keep revising regularly.")
    await callback_query.message.delete()

@app.on_callback_query(filters.regex("^remind_later_"))
async def remind_later(client, callback_query):
    parts = callback_query.data.split("_")
    task_id = parts[1]
    revision_day = int(parts[2])
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
    
    week_ago = datetime.now() - timedelta(days=7)
    weekly_completed = tasks_col.count_documents({
        "user_id": user_id,
        "is_completed": True,
        "completion_date": {"$gte": week_ago}
    })
    
    stats_text = (
        f"📊 Your Task Statistics\n\n"
        f"📝 Total Tasks: {len(tasks)}\n"
        f"✅ Completed: {completed} ({completion_rate:.1f}%)\n"
        f"📅 Completed this week: {weekly_completed}\n"
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
    print("Task Tracker Bot is running...")
    try:
        app.run()
    except KeyboardInterrupt:
        print("Bot stopped by user")
    finally:
        scheduler.shutdown()
        mongo_client.close()
