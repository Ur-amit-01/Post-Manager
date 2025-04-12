from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ========================================= HELP TEXTS =============================================

MAIN_HELP_TXT = """
<b>📚 Channel Manager Bot Help</b>

<u>👮 Admin Commands</u>:
• /start - Start the bot
• /channels - List all connected channels
• /post [time] - Post a message to all channels (reply to a message)
• /del_post <post_id> - Delete a specific post from all channels
• /add - Add current channel (use in channel)
• /rem - Remove current channel (use in channel)

<u>⏱ Time Format Examples</u>:
• /post 1h30m - Post with 1 hour 30 minute delay
• /post 2d - Post with 2 day delay
• /post 45min - Post with 45 minute delay
• /post 30s - Post with 30 second delay

<u>🔧 Other Features</u>:
• Auto-delete posts after specified time
• Post tracking with unique IDs
• Simple channel management

<u>📊 Stats</u>:
• Total connected channels
• Success/failure rate tracking
• Post history

Developed by @Axa_bachha
"""

POST_HELP_TXT = """
<b>📢 Post Command Usage</b>

<code>/post [time]</code> - Reply to a message to broadcast it

<u>Time Format Examples</u>:
• <code>/post 1h30m</code> - Auto-delete after 1.5 hours
• <code>/post 2d</code> - Auto-delete after 2 days
• <code>/post 45min</code> - Auto-delete after 45 minutes
• <code>/post</code> - Post without auto-delete

<u>Features</u>:
• Supports all message types (text, media, polls, etc.)
• Progress tracking during sending
• Post ID for later management
"""

CHANNEL_HELP_TXT = """
<b>📋 Channel Management</b>

<u>Add Channel</u>:
1. Add bot to your channel as admin
2. Send <code>/add</code> in the channel

<u>Remove Channel</u>:
1. Send <code>/rem</code> in the channel
2. Bot will be automatically removed

<u>Requirements</u>:
• Bot needs <b>post messages</b> permission
• Bot needs <b>delete messages</b> permission for auto-delete
"""

DELETE_HELP_TXT = """
<b>🗑 Delete Command Usage</b>

<code>/del_post post_id</code> - Delete a specific post

<u>How to find Post ID</u>:
1. After posting, you'll receive a Post ID
2. Or check your post history

<u>Features</u>:
• Deletes from all channels simultaneously
• Clean database record removal
• Immediate feedback on success/failure
"""

# ========================================= HANDLERS =============================================

@Client.on_message(filters.command("help") & filters.private)
async def help_command(client, message: Message):
    await message.reply_text(
        MAIN_HELP_TXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 Post Help", callback_data="post_help"),
             InlineKeyboardButton("📋 Channel Help", callback_data="channel_help")],
            [InlineKeyboardButton("🗑 Delete Help", callback_data="delete_help"),
             InlineKeyboardButton("🏠 Home", callback_data="start")]
        ]),
        disable_web_page_preview=True
    )

@Client.on_callback_query(filters.regex(r"^help$|^post_help$|^channel_help$|^delete_help$"))
async def help_callbacks(client, query: CallbackQuery):
    data = query.data
    
    if data == "help":
        text = MAIN_HELP_TXT
        buttons = [
            [InlineKeyboardButton("📢 Post Help", callback_data="post_help"),
             InlineKeyboardButton("📋 Channel Help", callback_data="channel_help")],
            [InlineKeyboardButton("🗑 Delete Help", callback_data="delete_help"),
             InlineKeyboardButton("🏠 Home", callback_data="start")]
        ]
    elif data == "post_help":
        text = POST_HELP_TXT
        buttons = [[InlineKeyboardButton("◀️ Back", callback_data="help")]]
    elif data == "channel_help":
        text = CHANNEL_HELP_TXT
        buttons = [[InlineKeyboardButton("◀️ Back", callback_data="help")]]
    elif data == "delete_help":
        text = DELETE_HELP_TXT
        buttons = [[InlineKeyboardButton("◀️ Back", callback_data="help")]]
    
    await query.message.edit_text(
        text=text,
        reply_markup=InlineKeyboardMarkup(buttons),
        disable_web_page_preview=True
    )
    await query.answer()
