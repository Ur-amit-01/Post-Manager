from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from taskmaster_bot import app, mongo_client, ADMINS, is_premium
from config import *
from bson.objectid import ObjectId

db = mongo_client["neet_study_bot"]
users_col = db["users"]
premium_col = db["premium_users"]
admin_col = db["admin_settings"]

def is_admin(user_id):
    """Check if user is admin"""
    return user_id in ADMINS

# Premium Features
@app.on_message(filters.command("addpremium") & filters.user(ADMINS))
async def add_premium(client, message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.reply_text("Usage: /addpremium <user_id> <days>")
            return
        
        user_id = int(parts[1])
        days = int(parts[2])
        
        expiry_date = datetime.now() + timedelta(days=days)
        
        premium_col.update_one(
            {"user_id": user_id},
            {"$set": {
                "user_id": user_id,
                "expiry_date": expiry_date,
                "plan_days": days,
                "granted_by": message.from_user.id,
                "granted_at": datetime.now()
            }},
            upsert=True
        )
        
        await message.reply_text(f"✅ Success! User {user_id} granted premium for {days} days.")
        
        try:
            await client.send_message(
                user_id,
                f"🎉 Congratulations! You've been granted Premium access for {days} days!\n\n"
                "You now have access to all premium features!"
            )
        except:
            pass
        
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")

@app.on_message(filters.command("removepremium") & filters.user(ADMINS))
async def remove_premium(client, message):
    try:
        if len(message.command) != 2:
            await message.reply_text("Usage: /removepremium <user_id>")
            return
        
        user_id = int(message.command[1])
        
        result = premium_col.delete_one({"user_id": user_id})
        
        if result.deleted_count > 0:
            await message.reply_text(f"✅ Premium access removed for user {user_id}.")
            
            try:
                await client.send_message(
                    user_id,
                    "⚠️ Your Premium access has been revoked by admin."
                )
            except:
                pass
        else:
            await message.reply_text("User not found in premium database.")
            
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")

@app.on_message(filters.command("premiumusers") & filters.user(ADMINS))
async def list_premium_users(client, message):
    active_premium = list(premium_col.find({
        "expiry_date": {"$gt": datetime.now()}
    }).sort("expiry_date", 1))
    
    if not active_premium:
        await message.reply_text("No active premium users found.")
        return
    
    text = "🌟 Active Premium Users:\n\n"
    for user in active_premium:
        remaining_days = (user["expiry_date"] - datetime.now()).days
        text += (
            f"👤 User ID: {user['user_id']}\n"
            f"📅 Expires in: {remaining_days} days\n"
            f"⏳ Expiry Date: {user['expiry_date'].strftime('%Y-%m-%d')}\n"
            f"🔹 Plan: {user['plan_days']} days\n\n"
        )
    
    await message.reply_text(text)

# Admin Panel
@app.on_callback_query(filters.regex("^admin_panel$"))
async def admin_panel(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ Access denied!", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Bot Statistics", callback_data="admin_stats"),
            InlineKeyboardButton("👥 User Management", callback_data="admin_users")
        ],
        [
            InlineKeyboardButton("💎 Premium Management", callback_data="admin_premium"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_to_main")
        ]
    ])
    
    await callback_query.message.edit_text(
        "👑 *Admin Panel*\n\n"
        "Manage the bot and user data with the options below:",
        reply_markup=keyboard
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("^admin_stats$"))
async def admin_stats(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ Access denied!", show_alert=True)
        return
    
    total_users = users_col.count_documents({})
    active_users = users_col.count_documents({"last_active": {"$gte": datetime.now() - timedelta(days=7)}})
    total_tasks = tasks_col.count_documents({})
    completed_tasks = tasks_col.count_documents({"is_completed": True})
    premium_users = premium_col.count_documents({"expiry_date": {"$gt": datetime.now()}})
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_panel")]
    ])
    
    await callback_query.message.edit_text(
        "📊 *Bot Statistics*\n\n"
        f"👥 Total Users: {total_users}\n"
        f"🟢 Active Users (7d): {active_users}\n"
        f"💎 Premium Users: {premium_users}\n"
        f"📝 Total Tasks: {total_tasks}\n"
        f"✅ Completed Tasks: {completed_tasks}\n\n"
        f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        reply_markup=keyboard
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("^admin_premium$"))
async def admin_premium(client, callback_query):
    if not is_admin(callback_query.from_user.id):
        await callback_query.answer("⚠️ Access denied!", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add Premium", callback_data="admin_add_premium"),
            InlineKeyboardButton("➖ Remove Premium", callback_data="admin_remove_premium")
        ],
        [
            InlineKeyboardButton("📜 List Premium Users", callback_data="admin_list_premium")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="admin_panel")
        ]
    ])
    
    await callback_query.message.edit_text(
        "💎 *Premium Management*\n\n"
        "Manage premium subscriptions and users:",
        reply_markup=keyboard
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("^admin_list_premium$"))
async def admin_list_premium(client, callback_query):
    await list_premium_users(client, callback_query.message)
    await callback_query.answer()

# Premium Features for Users
@app.on_callback_query(filters.regex("^premium_info$"))
async def premium_info(client, callback_query):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💎 Get Premium", url="https://t.me/YourPremiumChannel")],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ])
    
    await callback_query.message.edit_text(
        "🚀 *TaskMaster Pro Premium Features*\n\n"
        "• 📅 Unlimited task history\n"
        "• 🔔 Priority reminders\n"
        "• 📈 Advanced analytics\n"
        "• 🎯 Custom revision schedules\n"
        "• 🏆 Achievement badges\n\n"
        "💎 Only $4.99/month!\n\n"
        "Contact @YourSupportBot to get Premium access!",
        reply_markup=keyboard
    )
    await callback_query.answer()

@app.on_callback_query(filters.regex("^premium_btn$"))
async def premium_features(client, callback_query):
    if not is_premium(callback_query.from_user.id):
        await premium_info(client, callback_query)
        return
    
    user_premium = premium_col.find_one({"user_id": callback_query.from_user.id})
    expiry_date = user_premium["expiry_date"].strftime("%Y-%m-%d")
    remaining_days = (user_premium["expiry_date"] - datetime.now()).days
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Advanced Stats", callback_data="premium_stats"),
            InlineKeyboardButton("⏰ Custom Reminders", callback_data="premium_reminders")
        ],
        [
            InlineKeyboardButton("📈 Detailed Reports", callback_data="premium_reports"),
            InlineKeyboardButton("🎯 Goal Setting", callback_data="premium_goals")
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="back_to_main")
        ]
    ])
    
    await callback_query.message.edit_text(
        "💎 *Premium Features*\n\n"
        f"Your Premium subscription is active until {expiry_date} "
        f"({remaining_days} days remaining)\n\n"
        "Access your exclusive premium features:",
        reply_markup=keyboard
    )
    await callback_query.answer()
