from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db
from plugins.Post.constants import *
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define callback prefixes that should be ignored (handled by admin.py)
ADMIN_PREFIXES = {
    "admin_", 
    "promote_", 
    "demote_", 
    "list_",
    "backup_",
    "restore_",
    "broadcast_",
    "stats_"
}

@Client.on_callback_query(filters.regex(r'^(?!admin_|promote_|demote_|list_|backup_|restore_|broadcast_|stats_).*'))
async def cb_handler(client: Client, query: CallbackQuery):
    try:
        data = query.data
        logger.info(f"Received callback: {data} from {query.from_user.id}")

        # Skip if this is an admin callback (handled by admin.py)
        if any(data.startswith(prefix) for prefix in ADMIN_PREFIXES):
            return
        
        # Delete post handler
        if data.startswith("delete_"):
            await handle_delete_post(client, query)
            return
            
        # Start menu
        elif data == "start":
            txt = f"> **✨👋🏻 Hey {query.from_user.mention} !!**\n" \
                  f"**Welcome to the Channel Manager Bot, Manage multiple channels and post messages with ease! 😌**\n\n" \
                  f"> **ᴅᴇᴠᴇʟᴏᴘᴇʀ �🏻‍💻 :- @Axa_bachha**"
            
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton('📜 ᴀʙᴏᴜᴛ', callback_data='about'),
                 InlineKeyboardButton('🕵🏻‍♀️ ʜᴇʟᴘ', callback_data='help')]
            ])
        
        # Main help menu
        elif data == "help":
            txt = MAIN_HELP_TXT
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("ʀᴇǫᴜᴇsᴛ ᴀᴄᴄᴇᴘᴛᴏʀ", callback_data="request")],
                [InlineKeyboardButton("ʀᴇsᴛʀɪᴄᴛᴇᴅ ᴄᴏɴᴛᴇɴᴛ sᴀᴠᴇʀ", callback_data="restricted")],
                [InlineKeyboardButton("📢 Post Help", callback_data="post_help"),
                 InlineKeyboardButton("📋 Channel Help", callback_data="channel_help")],
                [InlineKeyboardButton("🗑 Delete Help", callback_data="delete_help"),
                 InlineKeyboardButton("🏠 Home", callback_data="start")]
            ])
        
        # Help sub-menus
        elif data == "post_help":
            txt = POST_HELP_TXT
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="help")]])
        
        elif data == "channel_help":
            txt = CHANNEL_HELP_TXT
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="help")]])
        
        elif data == "delete_help":
            txt = DELETE_HELP_TXT
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="help")]])
        
        # Other menus
        elif data == "about":
            txt = ABOUT_TXT.format(client.mention)
            reply_markup = InlineKeyboardMarkup([
                [InlineKeyboardButton("🤖 ᴅᴇᴠᴇʟᴏᴘᴇʀ", url="https://t.me/axa_bachha"),
                 InlineKeyboardButton("🏠 Home", callback_data="start")]
            ])
        
        elif data == "restricted":
            txt = RESTRICTED_TXT
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="help")]])
        
        elif data == "request":
            txt = REQUEST_TXT.format(client.mention)
            reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="help")]])
        
        else:
            await query.answer("⚠️ Unknown command", show_alert=True)
            return
        
        await query.message.edit_text(
            text=txt,
            reply_markup=reply_markup,
            disable_web_page_preview=True
        )
        await query.answer()
        
    except Exception as e:
        logger.error(f"Error in callback handler: {e}", exc_info=True)
        await query.answer(f"Error: {str(e)}", show_alert=True)

async def handle_delete_post(client: Client, query: CallbackQuery):
    try:
        await query.answer("Processing deletion...")
        post_id = int(query.data.split("_")[1])
        
        # Retrieve the post's details from the database
        post = await db.get_post(post_id)
        
        if not post:
            await query.answer("❌ Post not found or already deleted", show_alert=True)
            await query.message.edit_text(
                f"❌ <b>Deletion Failed</b>\n\n"
                f"• <b>Post ID:</b> <code>{post_id}</code>\n"
                f"• <b>Reason:</b> Post not found in database"
            )
            return

        processing_msg = await query.message.edit_text(
            f"🗑 <b>Deleting Post ID:</b> <code>{post_id}</code>\n\n"
            f"• <b>Channels: {len(post.get('channels', []))}</b>\n"
            f"⏳ <b><i>Processing deletion...</i></b>"
        )

        channels = post.get("channels", [])
        success_count = 0
        failed_count = 0
        failed_channels = []

        for channel in channels:
            try:
                await client.delete_messages(
                    chat_id=channel["channel_id"],
                    message_ids=channel["message_id"]
                )
                success_count += 1
                # Remove from database after successful deletion
                await db.remove_channel_post(post_id, channel["channel_id"])
            except Exception as e:
                failed_count += 1
                failed_channels.append(
                    f"  - {channel.get('channel_name', channel['channel_id'])}: {str(e)}"
                )

        # Check if all channels were deleted
        remaining_channels = await db.get_post_channels(post_id)
        if not remaining_channels:
            await db.delete_post(post_id)

        result_msg = (
            f"🗑 <b>Post Deletion Results</b>\n\n"
            f"• <b>Post ID:</b> <code>{post_id}</code>\n"
            f"• <b>Successfully deleted from:</b> {success_count} channel(s)\n"
        )
        
        if failed_count > 0:
            result_msg += (
                f"• <b>Failed to delete from:</b> {failed_count} channel(s)\n"
                f"\n<b>Errors:</b>\n"
            )
            # Show up to 5 error messages to avoid too long messages
            result_msg += "\n".join(failed_channels[:5])
            if len(failed_channels) > 5:
                result_msg += f"\n  - (and {len(failed_channels)-5} more errors...)"

        await processing_msg.edit_text(result_msg)

    except Exception as e:
        logger.error(f"Error in delete handler: {e}", exc_info=True)
        await query.answer("❌ An error occurred during deletion", show_alert=True)
        await query.message.edit_text(
            f"❌ <b>Deletion Failed</b>\n\n"
            f"• <b>Error:</b> {str(e)}\n"
            f"• Please try again or check logs"
      
