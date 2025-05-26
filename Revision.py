from pyrogram import Client, filters
from pyrogram.types import (
    Message, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton,
    ReplyKeyboardMarkup
)
from datetime import datetime, timedelta
from pymongo import MongoClient
import asyncio
import os
from config import *

# Initialize bot
app = Client(
    "neet_prep_bot",
    bot_token=os.getenv("BOT_TOKEN"),
    api_id=int(os.getenv("API_ID")),
    api_hash=os.getenv("API_HASH")
)

# MongoDB setup
MONGO_URI = os.getenv("DB_URL")
mongo_client = MongoClient(DB_URL)
db = mongo_client.neet_prep_bot

# Collections
users = db.users
topics = db.topics
revisions = db.revisions
todos = db.todos
progress = db.progress

# Spaced repetition intervals (in days)
SPACED_INTERVALS = [1, 3, 7, 15, 30, 60]

## ===== DATABASE OPERATIONS ===== ##

async def get_or_create_user(user_id, username):
    user = users.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "username": username,
            "join_date": datetime.now(),
            "settings": {
                "daily_reminder": True,
                "reminder_time": "20:00",
                "active_subjects": ["Physics", "Chemistry", "Biology"]
            }
        }
        users.insert_one(user)
    return user

async def add_study_topic(user_id, subject, topic, details):
    topic_data = {
        "user_id": user_id,
        "subject": subject,
        "topic": topic,
        "details": details,
        "study_date": datetime.now(),
        "revision_count": 0,
        "mastery_level": 0,  # 0-5 scale
        "last_revised": None
    }
    result = topics.insert_one(topic_data)
    
    # Schedule first revision for tomorrow
    first_revision = datetime.now() + timedelta(days=1)
    revisions.insert_one({
        "topic_id": result.inserted_id,
        "user_id": user_id,
        "scheduled_date": first_revision,
        "completed": False,
        "revision_number": 1
    })
    
    return result

## ===== COMMAND HANDLERS ===== ##

@app.on_message(filters.command(["start", "help"]))
async def start(client, message):
    user = message.from_user
    await get_or_create_user(user.id, user.username)
    
    await message.reply_text(
        f"📚 Welcome {user.first_name} to NEET Prep Bot!\n\n"
        "Here's what I can help you with:\n"
        "1. Track your daily study topics\n"
        "2. Schedule spaced revisions automatically\n"
        "3. Manage your study tasks and DPPs\n"
        "4. Analyze your preparation progress\n\n"
        "Try these commands:\n"
        "/addtopic - Add what you studied today\n"
        "/addtask - Add a study task/DPP\n"
        "/today - See today's revision schedule\n"
        "/progress - View your preparation analytics"
    )

@app.on_message(filters.command("addtopic"))
async def add_topic(client, message):
    await message.reply_text(
        "📝 Add what you studied today (format):\n\n"
        "**Subject**: Physics/Chemistry/Biology\n"
        "**Topic**: Topic name\n"
        "**Details**: Key points (optional)\n\n"
        "Example:\n"
        "Subject: Physics\n"
        "Topic: Electrostatics\n"
        "Details: Coulomb's Law, Electric Field"
    )

@app.on_message(filters.regex(r"Subject: (.+)"))
async def process_topic(client, message):
    try:
        text = message.text
        subject = text.split("Subject: ")[1].split("\n")[0].strip()
        topic = text.split("Topic: ")[1].split("\n")[0].strip()
        details = text.split("Details: ")[1].strip() if "Details: " in text else ""
        
        await add_study_topic(message.from_user.id, subject, topic, details)
        
        await message.reply_text(
            f"✅ Topic added successfully!\n\n"
            f"**{subject} - {topic}**\n"
            f"{details}\n\n"
            f"I'll remind you to revise this tomorrow!"
        )
    except Exception as e:
        await message.reply_text("❌ Invalid format. Please use the correct format.")

## ===== TASK MANAGEMENT ===== ##

@app.on_message(filters.command("addtask"))
async def add_task(client, message):
    await message.reply_text(
        "📌 Add a study task (format):\n\n"
        "**Type**: Lecture/DPP/Extra/Test\n"
        "**Subject**: Physics/Chemistry/Biology\n"
        "**Description**: Task details\n"
        "**Due**: Optional date (DD-MM-YYYY)\n\n"
        "Example:\n"
        "Type: DPP\n"
        "Subject: Chemistry\n"
        "Description: Chemical Kinetics problems\n"
        "Due: 15-05-2024"
    )

## ===== REVISION SYSTEM ===== ##

async def check_pending_revisions():
    while True:
        now = datetime.now()
        pending = revisions.find({
            "scheduled_date": {"$lte": now},
            "completed": False
        })
        
        for revision in pending:
            topic = topics.find_one({"_id": revision["topic_id"]})
            user = users.find_one({"user_id": revision["user_id"]})
            
            if user and topic:
                try:
                    await app.send_message(
                        chat_id=revision["user_id"],
                        text=f"🔄 Revision Reminder!\n\n"
                             f"**{topic['subject']} - {topic['topic']}**\n"
                             f"Last studied: {topic['last_revised'] or topic['study_date']}\n\n"
                             f"Please review this topic and click /revised when done!",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("Mark as Revised", callback_data=f"revised_{revision['_id']}")
                        ]])
                    )
                except Exception as e:
                    print(f"Failed to send reminder: {e}")
        
        await asyncio.sleep(3600)  # Check every hour

## ===== BOT STARTUP ===== ##

async def run_bot():
    await app.start()
    asyncio.create_task(check_pending_revisions())
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(run_bot())
