from pyrogram import Client, filters
from pyrogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
    InputMediaPhoto
)
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import io
import pandas as pd
from typing import List, Dict
from plugins.helper.db import db
from config import ADMINS

class AdminPanel:
    def __init__(self, client: Client):
        self.client = client
        self.setup_handlers()
    
    def setup_handlers(self):
        @self.client.on_message(filters.command("admin") & filters.user(ADMINS))
        async def admin_panel(_, message: Message):
            await self.show_admin_panel(message)
        
        @self.client.on_callback_query(filters.regex(r"^admin_"))
        async def admin_callback(_, query: CallbackQuery):
            await self.handle_admin_callback(query)

    async def show_admin_panel(self, message: Message):
        stats = await db.get_bot_stats()
        
        text = (
            "⚙️ **ADMIN PANEL** ⚙️\n\n"
            f"📊 **Bot Statistics**\n"
            f"• Users: `{stats['total_users']}`\n"
            f"• Channels: `{stats['total_channels']}`\n"
            f"• Posts: `{stats['total_posts']}`\n"
            f"• Active: `{stats['active_posts']}`\n"
            f"• Storage: `{stats['storage_usage']} MB`\n"
            f"• Success Rate: `{stats['success_rate']}%`\n\n"
            "🛠 **Management Tools**"
        )
        
        keyboard = [
            [InlineKeyboardButton("📊 Statistics Dashboard", callback_data="admin_stats")],
            [
                InlineKeyboardButton("📢 Posts", callback_data="admin_posts"),
                InlineKeyboardButton("📋 Channels", callback_data="admin_channels")
            ],
            [
                InlineKeyboardButton("👥 Users", callback_data="admin_users"),
                InlineKeyboardButton("📜 Logs", callback_data="admin_logs")
            ],
            [InlineKeyboardButton("⚙️ System", callback_data="admin_system")],
            [InlineKeyboardButton("❌ Close", callback_data="admin_close")]
        ]
        
        await message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_admin_callback(self, query: CallbackQuery):
        action = query.data.split("_")[1]
        
        if action == "stats":
            await self.show_statistics(query)
        elif action == "posts":
            await self.post_management(query)
        elif action == "channels":
            await self.channel_management(query)
        elif action == "users":
            await self.user_management(query)
        elif action == "logs":
            await self.log_management(query)
        elif action == "system":
            await self.system_tools(query)
        elif action == "close":
            await query.message.delete()
        
        await query.answer()

    async def show_statistics(self, query: CallbackQuery):
        stats = await db.get_bot_stats()
        
        text = (
            "📊 **Statistics Dashboard**\n\n"
            f"• Users: `{stats['total_users']}`\n"
            f"• Channels: `{stats['total_channels']}`\n"
            f"• Total Posts: `{stats['total_posts']}`\n"
            f"• Active Posts: `{stats['active_posts']}`\n"
            f"• Storage Used: `{stats['storage_usage']} MB`\n"
            f"• Uptime: `{stats['uptime']}`\n"
            f"• Avg Post Time: `{stats['avg_post_time']}s`\n"
            f"• Success Rate: `{stats['success_rate']}%`\n\n"
            "📈 **Visual Analytics**"
        )
        
        keyboard = [
            [InlineKeyboardButton("📈 Post Activity", callback_data="admin_graph_posts")],
            [InlineKeyboardButton("📊 Channel Stats", callback_data="admin_graph_channels")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="admin_stats")],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_back")]
        ]
        
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def post_management(self, query: CallbackQuery):
        posts = await db.get_all_posts(limit=5)
        
        text = "📢 **Post Management**\n\n"
        for post in posts:
            text += (
                f"• `{post['post_id']}` - {post.get('timestamp', 'N/A')}\n"
                f"  ↳ Channels: {len(post.get('channels', []))} | Status: {post.get('status', 'unknown')}\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("🔍 View Post", callback_data="admin_post_view")],
            [InlineKeyboardButton("🗑 Delete Post", callback_data="admin_post_delete")],
            [InlineKeyboardButton("📅 Scheduled", callback_data="admin_post_scheduled")],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_back")]
        ]
        
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def channel_management(self, query: CallbackQuery):
        channels = await db.get_channel_stats()
        
        text = "📋 **Channel Management**\n\n"
        for i, channel in enumerate(channels, 1):
            text += (
                f"{i}. {channel.get('name', channel['_id'])}\n"
                f"   ↳ Posts: {channel.get('post_count', 0)}\n"
                f"   ↳ Last Post: {channel.get('last_post', 'Never')}\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("➕ Add Channel", callback_data="admin_channel_add")],
            [InlineKeyboardButton("➖ Remove Channel", callback_data="admin_channel_remove")],
            [InlineKeyboardButton("📊 Channel Stats", callback_data="admin_graph_channels")],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_back")]
        ]
        
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard))
        )

    async def user_management(self, query: CallbackQuery):
        users = await db.get_all_users()
        admin_count = sum(1 for user in users if user.get('is_admin'))
        banned_count = sum(1 for user in users if user.get('is_banned'))
        
        text = (
            "👥 **User Management**\n\n"
            f"• Total Users: `{len(users)}`\n"
            f"• Admins: `{admin_count}`\n"
            f"• Banned: `{banned_count}`\n\n"
            "🛠 **User Actions**"
        )
        
        keyboard = [
            [InlineKeyboardButton("👤 List Users", callback_data="admin_user_list")],
            [
                InlineKeyboardButton("🔼 Add Admin", callback_data="admin_user_add_admin"),
                InlineKeyboardButton("🔽 Remove Admin", callback_data="admin_user_remove_admin")
            ],
            [
                InlineKeyboardButton("🚫 Ban User", callback_data="admin_user_ban"),
                InlineKeyboardButton("✅ Unban User", callback_data="admin_user_unban")
            ],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_back")]
        ]
        
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard))
        )

    async def log_management(self, query: CallbackQuery):
        logs = await db.get_recent_activity()
        
        text = "📜 **Recent Activity Logs**\n\n"
        for log in logs:
            text += (
                f"• {log['timestamp']}\n"
                f"  ↳ {log.get('action', 'Unknown')}: {log.get('details', '')}\n"
            )
        
        keyboard = [
            [InlineKeyboardButton("🗑 Clear Logs", callback_data="admin_logs_clear")],
            [InlineKeyboardButton("📥 Export Logs", callback_data="admin_logs_export")],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_back")]
        ]
        
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard))
        )

    async def system_tools(self, query: CallbackQuery):
        text = (
            "⚙️ **System Tools**\n\n"
            "1. **Database Backup** - Create a backup snapshot\n"
            "2. **Maintenance Mode** - Toggle bot availability\n"
            "3. **Performance Stats** - View system resources\n"
            "4. **Error Logs** - View recent errors\n"
            "5. **Restart Bot** - Graceful restart"
        )
        
        keyboard = [
            [InlineKeyboardButton("💾 Backup Now", callback_data="admin_backup")],
            [InlineKeyboardButton("🛑 Maintenance", callback_data="admin_maintenance")],
            [InlineKeyboardButton("📊 Performance", callback_data="admin_performance")],
            [InlineKeyboardButton("📜 Error Logs", callback_data="admin_errors")],
            [InlineKeyboardButton("🔄 Restart", callback_data="admin_restart")],
            [InlineKeyboardButton("◀️ Back", callback_data="admin_back")]
        ]
        
        await query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard))
        )

    async def generate_graph(self, graph_type: str):
        """Generate matplotlib graphs for analytics"""
        plt.style.use('ggplot')
        fig, ax = plt.subplots(figsize=(10, 5))
        
        if graph_type == "posts":
            data = await db.get_post_activity()
            dates = [pd.to_datetime(d['date']) for d in data]
            counts = [d['count'] for d in data]
            ax.bar(dates, counts)
            ax.set_title('Post Activity (Last 7 Days)')
            ax.set_ylabel('Posts')
            plt.xticks(rotation=45)
        elif graph_type == "channels":
            data = await db.get_channel_stats(limit=8)
            names = [d.get('name', str(d['_id'])) for d in data]
            counts = [d.get('post_count', 0) for d in data]
            ax.barh(names, counts)
            ax.set_title('Top Channels by Post Count')
            ax.set_xlabel('Posts')
        
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        return buf

    async def send_graph(self, query: CallbackQuery, graph_type: str):
        graph = await self.generate_graph(graph_type)
        caption = "📈 Post Activity" if graph_type == "posts" else "📊 Channel Statistics"
        
        await query.message.reply_photo(
            photo=graph,
            caption=caption,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("◀️ Back", callback_data="admin_stats")]
            ])
        )
        await query.message.delete()

# Initialize in your bot.py
# admin_panel = AdminPanel(app)
