import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, List

from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    CallbackQuery
)
from pymongo import MongoClient
from dotenv import load_dotenv
from config import *
# Load environment variables
load_dotenv()

# --- Configuration --- #
class Config:
    REVIEW_SCHEDULE = [1, 4, 7, 15, 30]  # Spaced repetition intervals
    PRIORITY_EMOJIS = {1: "🔥", 2: "🔼", 3: "🔽"}
    PRIORITY_NAMES = {1: "High", 2: "Medium", 3: "Low"}
    SUBJECTS = ["Physics", "Chemistry", "Biology", "Other"]

# --- MongoDB Setup --- #
mongo_client = MongoClient(DB_URL)
db = mongo_client[DB_NAME]
users_collection = db["users"]
tasks_collection = db["tasks"]

# Ensure indexes
tasks_collection.create_index([("user_id", 1)])
tasks_collection.create_index([("next_review", 1)])
tasks_collection.create_index([("user_id", 1), ("completed_date", 1)])

# --- Bot Setup --- #
app = Client("neet_study_bot", bot_token=BOT_TOKEN)

# --- State Management --- #
user_states: Dict[int, Dict] = {}

# --- Keyboard Utilities --- #
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Add Task", callback_data="add_task")],
        [
            InlineKeyboardButton("✅ Completed", callback_data="mark_completed"),
            InlineKeyboardButton("📚 View Tasks", callback_data="view_tasks")
        ],
        [InlineKeyboardButton("📊 Progress", callback_data="view_progress")]
    ])

def subject_kb() -> InlineKeyboardMarkup:
    buttons = []
    for subject in Config.SUBJECTS:
        buttons.append([InlineKeyboardButton(subject, callback_data=f"subject_{subject}")])
    return InlineKeyboardMarkup(buttons)

def priority_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{Config.PRIORITY_EMOJIS[1]} High Priority", callback_data="priority_1")],
        [InlineKeyboardButton(f"{Config.PRIORITY_EMOJIS[2]} Medium Priority", callback_data="priority_2")],
        [InlineKeyboardButton(f"{Config.PRIORITY_EMOJIS[3]} Low Priority", callback_data="priority_3")]
    ])

def review_kb(task_id: str, stage: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Reviewed", callback_data=f"reviewed_{task_id}_{stage}")],
        [InlineKeyboardButton("⏰ Remind Later", callback_data=f"postpone_{task_id}")]
    ])

def task_action_kb(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Mark Completed", callback_data=f"complete_{task_id}")],
        [InlineKeyboardButton("✏️ Edit Task", callback_data=f"edit_{task_id}")],
        [InlineKeyboardButton("🗑️ Delete Task", callback_data=f"delete_{task_id}")]
    ])

# --- Helper Functions --- #
def format_task(task: Dict) -> str:
    status = "✅" if task.get("completed_date") else "🟡"
    priority = Config.PRIORITY_EMOJIS.get(task.get("priority", 2), "")
    
    text = f"{status} {priority} **{task['subject']} - {task['topic']}**\n"
    text += f"📝 {task['details']}\n"
    
    if task.get("completed_date"):
        text += f"📅 Completed: {task['completed_date'].strftime('%d %b %Y')}\n"
        if task.get("next_review"):
            text += f"🔁 Next Review: {task['next_review'].strftime('%d %b %Y')}\n"
    
    return text

def schedule_next_review(current_stage: int) -> Optional[datetime]:
    if current_stage >= len(Config.REVIEW_SCHEDULE):
        return None
    return datetime.now() + timedelta(days=Config.REVIEW_SCHEDULE[current_stage])

# --- Command Handlers --- #
@app.on_message(filters.command("start"))
async def start(client: Client, message: Message):
    user = message.from_user
    
    # Add user to database if not exists
    if not users_collection.find_one({"user_id": user.id}):
        users_collection.insert_one({
            "user_id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "join_date": datetime.now(),
            "last_active": datetime.now()
        })
    
    welcome_msg = f"""
    🎖 **Welcome {user.first_name} to NEET Study Tracker!** 🎖

    I'll help you:
    - Track your study targets
    - Remind you to revise using spaced repetition
    - Monitor your progress

    **Choose an option below to get started:**
    """
    
    await message.reply_text(welcome_msg, reply_markup=main_menu_kb())

# --- Callback Handlers --- #
@app.on_callback_query(filters.regex("^add_task$"))
async def add_task_cb(client: Client, callback: CallbackQuery):
    user_states[callback.from_user.id] = {"action": "add_task", "step": "subject"}
    await callback.message.edit_text(
        "📚 **Select Subject:**",
        reply_markup=subject_kb()
    )
    await callback.answer()

@app.on_callback_query(filters.regex("^subject_"))
async def subject_selected(client: Client, callback: CallbackQuery):
    subject = callback.data.split("_")[1]
    user_states[callback.from_user.id].update({
        "subject": subject,
        "step": "topic"
    })
    await callback.message.edit_text(
        f"📖 **{subject} - Enter Topic/Chapter:**\n\n"
        "(Example: 'Organic Chemistry - Hydrocarbons')"
    )
    await callback.answer()

@app.on_message(filters.text & ~filters.command)
async def handle_text_input(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id not in user_states:
        return
    
    state = user_states[user_id]
    if state["action"] == "add_task":
        if state["step"] == "topic":
            state.update({
                "topic": message.text,
                "step": "details"
            })
            await message.reply_text(
                "📝 **Enter Details/Specifics:**\n\n"
                "(Example: 'Practice named reactions from page 45-50')"
            )
        elif state["step"] == "details":
            state.update({
                "details": message.text,
                "step": "priority"
            })
            await message.reply_text(
                "⚡ **Set Priority Level:**",
                reply_markup=priority_kb()
            )

@app.on_callback_query(filters.regex("^priority_"))
async def priority_selected(client: Client, callback: CallbackQuery):
    priority = int(callback.data.split("_")[1])
    user_id = callback.from_user.id
    state = user_states[user_id]
    
    task = {
        "user_id": user_id,
        "subject": state["subject"],
        "topic": state["topic"],
        "details": state["details"],
        "priority": priority,
        "created_at": datetime.now(),
        "completed_date": None,
        "next_review": None,
        "review_stage": 0
    }
    
    tasks_collection.insert_one(task)
    
    del user_states[user_id]
    await callback.message.edit_text(
        "🎉 **Task Added Successfully!**\n\n"
        f"**{state['subject']} - {state['topic']}**\n"
        f"Priority: {Config.PRIORITY_NAMES[priority]}\n\n"
        f"Details: {state['details']}",
        reply_markup=main_menu_kb()
    )
    await callback.answer()

@app.on_callback_query(filters.regex("^mark_completed$"))
async def mark_completed_cb(client: Client, callback: CallbackQuery):
    tasks = list(tasks_collection.find({
        "user_id": callback.from_user.id,
        "completed_date": None
    }).sort("created_at", -1).limit(10))
    
    if not tasks:
        await callback.answer("You have no pending tasks!")
        return
    
    buttons = []
    for task in tasks:
        btn_text = f"{task['subject'][:5]}... - {task['topic'][:15]}..."
        buttons.append([InlineKeyboardButton(btn_text, callback_data=f"complete_{task['_id']}")])
    
    await callback.message.edit_text(
        "✅ **Select Task to Mark as Completed:**",
        reply_markup=InlineKeyboardMarkup(buttons)
    )
    await callback.answer()

@app.on_callback_query(filters.regex("^complete_"))
async def complete_task_cb(client: Client, callback: CallbackQuery):
    task_id = callback.data.split("_")[1]
    result = tasks_collection.update_one(
        {"_id": task_id},
        {"$set": {
            "completed_date": datetime.now(),
            "next_review": datetime.now() + timedelta(days=1),
            "review_stage": 1
        }}
    )
    
    if result.modified_count > 0:
        task = tasks_collection.find_one({"_id": task_id})
        await callback.message.edit_text(
            f"🎯 **Task Marked Completed!**\n\n{format_task(task)}",
            reply_markup=main_menu_kb()
        )
    await callback.answer()

@app.on_callback_query(filters.regex("^view_tasks$"))
async def view_tasks_cb(client: Client, callback: CallbackQuery):
    tasks = list(tasks_collection.find({
        "user_id": callback.from_user.id
    }).sort([("completed_date", -1), ("created_at", -1)]).limit(5))
    
    if not tasks:
        await callback.answer("You have no tasks yet!")
        return
    
    response = "📚 **Your Tasks:**\n\n"
    for task in tasks:
        response += format_task(task) + "\n"
    
    total_tasks = tasks_collection.count_documents({"user_id": callback.from_user.id})
    if total_tasks > 5:
        response += f"\n...and {total_tasks-5} more tasks"
    
    await callback.message.edit_text(
        response,
        reply_markup=main_menu_kb()
    )
    await callback.answer()

# --- Review System --- #
async def send_review_reminders():
    while True:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tasks = list(tasks_collection.find({
            "next_review": {"$lte": today}
        }))
        
        for task in tasks:
            try:
                await app.send_message(
                    task["user_id"],
                    f"⏰ **Review Reminder!**\n\n{format_task(task)}\n\n"
                    "Have you reviewed this material?",
                    reply_markup=review_kb(str(task["_id"]), task.get("review_stage", 1))
                )
            except Exception as e:
                print(f"Failed to send reminder: {e}")
        
        await asyncio.sleep(60 * 60 * 24)  # Check daily

@app.on_callback_query(filters.regex("^reviewed_"))
async def reviewed_cb(client: Client, callback: CallbackQuery):
    _, task_id, stage = callback.data.split("_")
    stage = int(stage)
    
    next_review = schedule_next_review(stage)
    update_data = {
        "review_stage": stage + 1,
        "last_reviewed": datetime.now()
    }
    
    if next_review:
        update_data["next_review"] = next_review
    else:
        update_data["next_review"] = None
    
    result = tasks_collection.update_one(
        {"_id": task_id},
        {"$set": update_data}
    )
    
    if result.modified_count > 0:
        if next_review:
            await callback.message.edit_text(
                f"📚 **Review Logged!**\n\n"
                f"Next review on {next_review.strftime('%d %b %Y')}",
                reply_markup=main_menu_kb()
            )
        else:
            await callback.message.edit_text(
                "🎉 **Review Cycle Complete!**\n\n"
                "You've finished all scheduled reviews for this topic!",
                reply_markup=main_menu_kb()
            )
    await callback.answer()

# --- Main Loop --- #
async def main():
    await app.start()
    print("Bot started!")
    asyncio.create_task(send_review_reminders())
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
