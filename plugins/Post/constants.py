# ========================================= TEXT CONSTANTS =============================================

MAIN_HELP_TXT = """
<b>📚 Channel Manager Bot Help

<blockquote><u>👮 Admin Commands</u>:</blockquote>
• /start - Start the bot
• /channels - List all connected channels
• /admin - Access admin controls
• /post - Post a message to all channels (reply to a message)
• /del_post <post_id> - Delete a specific post from all channels
• /add - Add current channel (use in channel)
• /rem - Remove current channel (use in channel)


<blockquote><u>🔧 Advanced Features</u>:</blockquote>
• Auto-delete posts after specified time
• Post tracking with unique IDs
• Easy channel management

<blockquote><u>📊 Stats</u>:</blockquote>
• Total connected channels
• Success/failure rate tracking
• Post history

<blockquote>Developed by : @xDzoddd</blockquote> </b>
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

ABOUT_TXT = """
<b>╭───────────⍟
├➢ ᴍʏꜱᴇʟꜰ : {}
├➢ ᴅᴇᴠᴇʟᴏᴘᴇʀ : <a href=https://t.me/xDzoddd>Amit Singh 🪫ᯤ̸</a>
├➢ ʟɪʙʀᴀʀʏ : <a href=https://github.com/pyrogram>ᴘʏʀᴏɢʀᴀᴍ</a>
├➢ ʟᴀɴɢᴜᴀɢᴇ : <a href=https://www.python.org>ᴘʏᴛʜᴏɴ 3</a>
├➢ ᴅᴀᴛᴀʙᴀꜱᴇ : <a href=https://cloud.mongodb.com>MᴏɴɢᴏDB</a>
├➢ ꜱᴇʀᴠᴇʀ : <a href=https://apps.koyeb.com>ᴋᴏʏᴇʙ</a>
├➢ ʙᴜɪʟᴅ ꜱᴛᴀᴛᴜꜱ  : ᴘʏᴛʜᴏɴ v3.6.8
╰───────────────⍟

➢ ɴᴏᴛᴇ :- Interested Owners can DM @xDzoddd for personal bot. 🤝🏻
</b>"""

RESTRICTED_TXT = """
> **💡 Restricted Content Saver**

**1. 🔒 Private Chats**
➥ For My Owner Only :)

**2. 🌐 Public Chats**
➥ Simply share the post link. I'll download it for you.

**3. 📂 Batch Mode**
➥ Download multiple posts using this format:
> **https://t.me/xxxx/1001-1010**
"""

REQUEST_TXT = """
<b>
> ⚙️ Join Request Acceptor

• I can accept all pending join requests in your channel. 🤝

• Promote {} with full admin rights in your channel. 🔑

• Send /accept command in the channel to accept all requests at once. 💯
</b>
"""

LOG_TEXT = """<blockquote><b>#NewUser ॥ @interferons_bot </b></blockquote>
<blockquote><b>☃️ Nᴀᴍᴇ :~ {}
🪪 ID :~ <code>{}</code>
👨‍👨‍👦‍👦 ᴛᴏᴛᴀʟ :~ {}</b></blockquote>"""
