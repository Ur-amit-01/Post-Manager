import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from enum import Enum
from pymongo import MongoClient, ReturnDocument
from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
)
from config import *

# MongoDB setup
mongo_client = MongoClient(DB_URL)
db = mongo_client.todo_bot
users_col = db.users
tasks_col = db.tasks
categories_col = db.categories

# Enums
class Priority(Enum):
    HIGH = 1
    MEDIUM = 2
    LOW = 3

class TaskStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    ARCHIVED = "archived"

# Initialize the bot
app = Client("ultimate_todo_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Helper functions
def get_current_datetime() -> datetime:
    return datetime.now()

def ensure_user_exists(user_id: int, username: str, first_name: str, last_name: str = ""):
    users_col.update_one(
        {"_id": user_id},
        {"$setOnInsert": {
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
            "created_at": get_current_datetime(),
            "settings": {
                "default_priority": Priority.MEDIUM.value,
                "timezone": "UTC",
                "daily_reminder": False,
                "weekly_report": True
            }
        }},
        upsert=True
    )

def get_user_categories(user_id: int) -> List[Dict]:
    return list(categories_col.find({"user_id": user_id}))

def get_user_tasks(user_id: int, status: str = TaskStatus.ACTIVE.value, category: str = None) -> List[Dict]:
    query = {"user_id": user_id, "status": status}
    if category:
        query["category"] = category
    
    return list(tasks_col.find(query).sort([
        ("priority", 1),
        ("due_date", 1),
        ("created_at", 1)
    ]))

def create_task(user_id: int, text: str, priority: int = None, due_date: datetime = None, category: str = None) -> Dict:
    if priority is None:
        user = users_col.find_one({"_id": user_id})
        priority = user.get("settings", {}).get("default_priority", Priority.MEDIUM.value)
    
    task_data = {
        "user_id": user_id,
        "text": text,
        "priority": priority,
        "status": TaskStatus.ACTIVE.value,
        "created_at": get_current_datetime(),
        "completed_at": None,
        "category": category
    }
    
    if due_date:
        task_data["due_date"] = due_date
    
    return tasks_col.insert_one(task_data).inserted_id

def update_task(task_id: str, update_data: Dict) -> Optional[Dict]:
    return tasks_col.find_one_and_update(
        {"_id": task_id},
        {"$set": update_data},
        return_document=ReturnDocument.AFTER
    )

def delete_task(task_id: str) -> bool:
    result = tasks_col.delete_one({"_id": task_id})
    return result.deleted_count > 0

# Keyboard builders
def build_main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 My Tasks", callback_data="view_tasks"),
            InlineKeyboardButton("📊 Stats", callback_data="view_stats")
        ],
        [
            InlineKeyboardButton("⚙️ Settings", callback_data="view_settings"),
            InlineKeyboardButton("📚 Categories", callback_data="view_categories")
        ],
        [
            InlineKeyboardButton("➕ Quick Add", callback_data="quick_add"),
            InlineKeyboardButton("🆘 Help", callback_data="view_help")
        ]
    ])

def build_tasks_keyboard(tasks: List[Dict], page: int = 0, page_size: int = 5) -> InlineKeyboardMarkup:
    keyboard = []
    
    # Paginate tasks
    start_idx = page * page_size
    paginated_tasks = tasks[start_idx:start_idx + page_size]
    
    for task in paginated_tasks:
        emoji = "✅" if task["status"] == TaskStatus.COMPLETED.value else "⬜"
        priority_emoji = ""
        if task["priority"] == Priority.HIGH.value:
            priority_emoji = "🔥 "
        elif task["priority"] == Priority.LOW.value:
            priority_emoji = "🐢 "
        
        keyboard.append([
            InlineKeyboardButton(
                f"{emoji} {priority_emoji}{task['text'][:20]}",
                callback_data=f"view_task_{task['_id']}"
            )
        ])
    
    # Pagination controls
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton("⬅️ Prev", callback_data=f"tasks_page_{page-1}"))
    
    if len(tasks) > start_idx + page_size:
        pagination_row.append(InlineKeyboardButton("Next ➡️", callback_data=f"tasks_page_{page+1}"))
    
    if pagination_row:
        keyboard.append(pagination_row)
    
    # Action buttons
    action_row = [
        InlineKeyboardButton("➕ Add Task", callback_data="add_task"),
        InlineKeyboardButton("🗂 Filter", callback_data="filter_tasks")
    ]
    keyboard.append(action_row)
    
    # Navigation
    keyboard.append([InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")])
    
    return InlineKeyboardMarkup(keyboard)

def build_task_detail_keyboard(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Complete", callback_data=f"complete_task_{task_id}"),
            InlineKeyboardButton("✏️ Edit", callback_data=f"edit_task_{task_id}")
        ],
        [
            InlineKeyboardButton("📅 Set Due", callback_data=f"set_due_{task_id}"),
            InlineKeyboardButton("🏷 Category", callback_data=f"set_category_{task_id}")
        ],
        [
            InlineKeyboardButton("🔥 Priority", callback_data=f"set_priority_{task_id}"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"delete_task_{task_id}")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="view_tasks")]
    ])

def build_priority_keyboard(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔥 High", callback_data=f"priority_{task_id}_1"),
            InlineKeyboardButton("🔼 Medium", callback_data=f"priority_{task_id}_2")
        ],
        [
            InlineKeyboardButton("🐢 Low", callback_data=f"priority_{task_id}_3"),
            InlineKeyboardButton("🚫 None", callback_data=f"priority_{task_id}_0")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data=f"view_task_{task_id}")]
    ])

def build_categories_keyboard(user_id: int, task_id: str = None) -> InlineKeyboardMarkup:
    categories = get_user_categories(user_id)
    keyboard = []
    
    # Add existing categories
    for category in categories:
        callback = f"apply_category_{task_id}_{category['_id']}" if task_id else f"select_category_{category['_id']}"
        keyboard.append([InlineKeyboardButton(f"🏷 {category['name']}", callback_data=callback)])
    
    # Add management buttons
    if task_id:
        keyboard.append([
            InlineKeyboardButton("➕ New Category", callback_data="new_category"),
            InlineKeyboardButton("🔙 Back", callback_data=f"view_task_{task_id}")
        ])
    else:
        keyboard.append([
            InlineKeyboardButton("➕ New Category", callback_data="new_category"),
            InlineKeyboardButton("🔙 Main Menu", callback_data="main_menu")
        ])
    
    return InlineKeyboardMarkup(keyboard)

# Message formatters
def format_task(task: Dict) -> str:
    emoji = "✅" if task["status"] == TaskStatus.COMPLETED.value else "⬜"
    
    priority_map = {
        Priority.HIGH.value: "🔥 HIGH PRIORITY",
        Priority.MEDIUM.value: "🔼 MEDIUM PRIORITY",
        Priority.LOW.value: "🐢 LOW PRIORITY"
    }
    priority_text = priority_map.get(task.get("priority"), "")
    
    due_text = ""
    if "due_date" in task:
        due_date = task["due_date"]
        if isinstance(due_date, str):
            due_date = datetime.fromisoformat(due_date)
        
        delta = due_date - get_current_datetime()
        if delta.days < 0:
            due_text = f"\n⚠️ OVERDUE by {-delta.days} days"
        elif delta.days == 0:
            due_text = "\n⏰ Due today!"
        else:
            due_text = f"\n📅 Due in {delta.days} days"
    
    category_text = f"\n🏷 Category: {task.get('category', 'Uncategorized')}" if task.get("category") else ""
    
    created_at = task["created_at"]
    if isinstance(created_at, str):
        created_at = datetime.fromisoformat(created_at)
    created_text = f"\n🕒 Created: {created_at.strftime('%b %d, %Y %H:%M')}"
    
    return (
        f"{emoji} <b>{task['text']}</b>\n\n"
        f"{priority_text}{due_text}{category_text}{created_text}"
    )

def format_task_list(tasks: List[Dict]) -> str:
    if not tasks:
        return "No tasks found! Use the buttons below to add one."
    
    today = get_current_datetime().strftime("%A, %B %d, %Y")
    message = [f"📅 <b>Your Tasks - {today}</b>\n"]
    
    for i, task in enumerate(tasks, 1):
        emoji = "✅" if task["status"] == TaskStatus.COMPLETED.value else "⬜"
        priority_emoji = ""
        if task["priority"] == Priority.HIGH.value:
            priority_emoji = "🔥 "
        elif task["priority"] == Priority.LOW.value:
            priority_emoji = "🐢 "
        
        message.append(f"{i}. {emoji} {priority_emoji}{task['text'][:50]}")
        
        if "due_date" in task:
            due_date = task["due_date"]
            if isinstance(due_date, str):
                due_date = datetime.fromisoformat(due_date)
            
            delta = due_date - get_current_datetime()
            if delta.days < 0:
                message.append(f"   ⚠️ OVERDUE by {-delta.days} days")
            elif delta.days == 0:
                message.append("   ⏰ Due today!")
    
    return "\n".join(message)

# Command handlers
@app.on_message(filters.command(["start", "menu"]))
async def start_command(client: Client, message: Message):
    user = message.from_user
    ensure_user_exists(user.id, user.username, user.first_name, user.last_name)
    
    await message.reply_text(
        f"🎯 <b>Welcome to your Ultimate To-Do Bot, {user.first_name}!</b>\n\n"
        "What would you like to do today?",
        reply_markup=build_main_menu()
    )

@app.on_message(filters.command("add"))
async def add_task_command(client: Client, message: Message):
    user = message.from_user
    args = message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await message.reply_text(
            "Please provide a task after /add command.\n"
            "Example: <code>/add Buy milk tomorrow !!high</code>\n\n"
            "Priority markers:\n"
            "!!high 🔥\n"
            "!!medium 🔼\n"
            "!!low 🐢"
        )
        return
    
    # Parse task text (with optional priority and due date)
    task_text = args[1]
    priority = None
    due_date = None
    
    # Check for priority markers
    if " !!high" in task_text.lower():
        priority = Priority.HIGH.value
        task_text = task_text.replace(" !!high", "")
    elif " !!medium" in task_text.lower():
        priority = Priority.MEDIUM.value
        task_text = task_text.replace(" !!medium", "")
    elif " !!low" in task_text.lower():
        priority = Priority.LOW.value
        task_text = task_text.replace(" !!low", "")
    
    # Check for due date
    if " tomorrow" in task_text.lower():
        due_date = get_current_datetime() + timedelta(days=1)
        task_text = task_text.replace(" tomorrow", "")
    elif " today" in task_text.lower():
        due_date = get_current_datetime()
        task_text = task_text.replace(" today", "")
    
    # Create the task
    task_id = create_task(user.id, task_text.strip(), priority, due_date)
    
    await message.reply_text(
        f"Task added successfully!\n\n"
        f"{format_task(tasks_col.find_one({'_id': task_id}))}",
        reply_markup=build_task_detail_keyboard(task_id)
    )

# Callback handlers
@app.on_callback_query(filters.regex("^main_menu$"))
async def main_menu_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.message.edit_text(
        "🎯 <b>Main Menu</b>\n\n"
        "What would you like to do?",
        reply_markup=build_main_menu()
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("^view_tasks$"))
async def view_tasks_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    tasks = get_user_tasks(user_id)
    
    await callback_query.message.edit_text(
        format_task_list(tasks),
        reply_markup=build_tasks_keyboard(tasks)
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("^tasks_page_"))
async def tasks_page_callback(client: Client, callback_query: CallbackQuery):
    page = int(callback_query.data.split("_")[2])
    user_id = callback_query.from_user.id
    tasks = get_user_tasks(user_id)
    
    await callback_query.message.edit_text(
        format_task_list(tasks),
        reply_markup=build_tasks_keyboard(tasks, page)
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("^view_task_"))
async def view_task_callback(client: Client, callback_query: CallbackQuery):
    task_id = callback_query.data.split("_")[2]
    task = tasks_col.find_one({"_id": task_id})
    
    if not task:
        await callback_query.answer("Task not found!", show_alert=True)
        return
    
    await callback_query.message.edit_text(
        format_task(task),
        reply_markup=build_task_detail_keyboard(task_id)
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("^complete_task_"))
async def complete_task_callback(client: Client, callback_query: CallbackQuery):
    task_id = callback_query.data.split("_")[2]
    updated_task = update_task(task_id, {
        "status": TaskStatus.COMPLETED.value,
        "completed_at": get_current_datetime()
    })
    
    if updated_task:
        await callback_query.message.edit_text(
            format_task(updated_task),
            reply_markup=build_task_detail_keyboard(task_id)
        )
        await callback_query.answer("Task completed! 🎉")
    else:
        await callback_query.answer("Failed to complete task", show_alert=True)

@app.on_callback_query(filters.regex("^set_priority_"))
async def set_priority_callback(client: Client, callback_query: CallbackQuery):
    task_id = callback_query.data.split("_")[2]
    await callback_query.message.edit_text(
        "Select a priority level:",
        reply_markup=build_priority_keyboard(task_id)
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("^priority_"))
async def apply_priority_callback(client: Client, callback_query: CallbackQuery):
    _, task_id, priority = callback_query.data.split("_")
    priority = int(priority)
    
    priority_map = {
        1: "🔥 HIGH PRIORITY",
        2: "🔼 MEDIUM PRIORITY",
        3: "🐢 LOW PRIORITY",
        0: "No priority"
    }
    
    if priority > 0:
        update_task(task_id, {"priority": priority})
        message = f"Priority set to {priority_map[priority]}"
    else:
        update_task(task_id, {"$unset": {"priority": ""}})
        message = "Priority removed"
    
    await callback_query.answer(message)
    await view_task_callback(client, callback_query)

@app.on_callback_query(filters.regex("^view_categories$"))
async def view_categories_callback(client: Client, callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    await callback_query.message.edit_text(
        "📚 <b>Your Categories</b>\n\n"
        "Select a category to view tasks or create a new one:",
        reply_markup=build_categories_keyboard(user_id)
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("^apply_category_"))
async def apply_category_callback(client: Client, callback_query: CallbackQuery):
    _, _, task_id, category_id = callback_query.data.split("_")
    category = categories_col.find_one({"_id": category_id})
    
    if category:
        update_task(task_id, {"category": category["name"]})
        await callback_query.answer(f"Category set to {category['name']}")
    else:
        await callback_query.answer("Category not found", show_alert=True)
    
    await view_task_callback(client, callback_query)

@app.on_callback_query(filters.regex("^quick_add$"))
async def quick_add_callback(client: Client, callback_query: CallbackQuery):
    await callback_query.message.reply_text(
        "Type your task quickly:\n\n"
        "You can include:\n"
        "- !!high for high priority\n"
        "- !!low for low priority\n"
        "- 'today' or 'tomorrow' for due dates",
        reply_markup=ReplyKeyboardRemove()
    )
    await callback_query.answer()

# Message handler for quick add
@app.on_message(filters.private & ~filters.command(["start", "menu", "add", "help"]))
async def handle_quick_add(client: Client, message: Message):
    if message.reply_to_message and "Type your task quickly" in message.reply_to_message.text:
        user = message.from_user
        await add_task_command(client, message)

if __name__ == "__main__":
    print("Ultimate To-Do Bot is running...")
    app.run()
