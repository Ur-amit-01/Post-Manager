from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db  # Database helper
from config import ADMIN

@Client.on_message(filters.command("del_post") & filters.private & filters.user(ADMIN))
async def delete_post_manually(client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except:
        pass
    
    if len(message.command) < 2:
        await message.reply("**Please provide a Post ID to delete.**\nExample: `/del_post 123456789`")
        return
    
    try:
        post_id = int(message.command[1])
    except ValueError:
        await message.reply("❌ Invalid Post ID. It must be a number.")
        return
    
    # Get the post from database
    post = await db.get_post(post_id)
    if not post:
        await message.reply("❌ Post not found. Either it's already deleted or the ID is incorrect.")
        return
    
    processing_msg = await message.reply(f"🗑 <b>Deleting Post ID:</b> <code>{post_id}</code>\n\n⏳ <i>Processing...</i>")
    
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
            failed_channels.append(f"{channel.get('channel_name', channel['channel_id'])}: {str(e)}")
    
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
        result_msg += f"• <b>Failed to delete from:</b> {failed_count} channel(s)\n"
        if len(failed_channels) <= 5:  # Don't show too many errors
            result_msg += "\n".join([f"  - {err}" for err in failed_channels])
        else:
            result_msg += f"  - (Too many errors to display)"
    
    await processing_msg.edit_text(result_msg)
