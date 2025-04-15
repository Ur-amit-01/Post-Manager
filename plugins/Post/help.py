from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ========================================= HELP TEXTS =============================================

MAIN_HELP_TXT = """
<b>📚 Channel Manager Bot Help

<blockquote><u>👮 Admin Commands</u>:</blockquote>
• /start - Start the bot
• /channels - List all connected channels
• /post [time] - Post a message to all channels (reply to a message)
• /del_post <post_id> - Delete a specific post from all channels
• /add - Add current channel (use in channel)
• /rem - Remove current channel (use in channel)

<blockquote><u>⏱ Time Format Examples</u>:</blockquote>
• /post 1h30m - Post with 1 hour 30 minute delay
• /post 2d - Post with 2 day delay
• /post 45min - Post with 45 minute delay
• /post 30s - Post with 30 second delay

<blockquote><u>🔧 Other Features</u>:</blockquote>
• Auto-delete posts after specified time
• Post tracking with unique IDs
• Simple channel management

<blockquote><u>📊 Stats</u>:</blockquote>
• Total connected channels
• Success/failure rate tracking
• Post history

<blockquote>Developed by : @Axa_bachha</blockquote> </b>
"""

POST_HELP_TXT = """
<b>📢 Post Command Usage

/post [time] - Reply to a message to broadcast it

<blockquote><u>Time Format Examples</u>:</blockquote>
• <code>/post 1h30m</code> - Auto-delete after 1.5 hours
• <code>/post 2d</code> - Auto-delete after 2 days
• <code>/post 45min</code> - Auto-delete after 45 minutes
• <code>/post</code> - Post without auto-delete

<blockquote><u>Features</u>:</blockquote>
• Supports all message types (text, media, polls, etc.)
• Progress tracking during sending
• Post ID for later management</b>
"""

CHANNEL_HELP_TXT = """
<b>📋 Channel Management

<blockquote><u>Add Channel</u>:</blockquote>
1. Add bot to your channel as admin
2. Send <code>/add</code> in the channel

<blockquote><u>Remove Channel</u>:</blockquote>
1. Send <code>/rem</code> in the channel
2. Bot will be automatically removed

<blockquote><u>Requirements</u>:</blockquote>
• Bot needs <b>post messages</b> permission
• Bot needs <b>delete messages</b> permission for auto-delete </b>
"""

DELETE_HELP_TXT = """
<b><blockquote>🗑 Delete Command Usage</blockquote>

/del_post post_id - Delete a specific post

<blockquote><u>How to find Post ID</u>:</blockquote>
1. After posting, you'll receive a Post ID
2. Or check your post history

<blockquote><u>Features</u>:</blockquote>
• Deletes from all channels simultaneously
• Clean database record removal
• Immediate feedback on success/failure </b>
"""

# ========================================= HANDLERS =============================================

@Client.on_message(filters.command("help") & filters.private)
async def help_command(client, message: Message):
    await message.reply_text(
        MAIN_HELP_TXT,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("ʀᴇᴏ̨ᴜᴇsᴛ ᴀᴄᴄᴇᴘᴛᴏʀ ✅", callback_data="request")],
            [InlineKeyboardButton("ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴄᴏɴᴛᴇɴᴛ sᴀᴠᴇʀ 📥", callback_data="restricted")],
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
            [InlineKeyboardButton("ʀᴇᴏ̨ᴜᴇsᴛ ᴀᴄᴄᴇᴘᴛᴏʀ", callback_data="request")],
            [InlineKeyboardButton("ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴄᴏɴᴛᴇɴᴛ sᴀᴠᴇʀ", callback_data="restricted")],
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
