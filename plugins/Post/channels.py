from pyrogram import Client, filters, enums
from pyrogram.types import Message, ChatPrivileges
from plugins.helper.db import db
import time
import random
import asyncio
from config import *

# Command to add the current channel to the database
@Client.on_message(filters.command("add") & filters.channel)
async def add_current_channel(client, message: Message):
    channel_id = message.chat.id
    channel_name = message.chat.title

    try:
        added = await db.add_channel(channel_id, channel_name)
        if added:
            await message.reply(f"**Channel '{channel_name}' added! ✅**")
        else:
            await message.reply(f"ℹ️ Channel '{channel_name}' already exists.")
    except Exception as e:
        print(f"Error adding channel: {e}")
        await message.reply("❌ Failed to add channel. Contact developer.")

# Command to remove the current channel from the database
@Client.on_message(filters.command("rem") & filters.channel)
async def remove_current_channel(client, message: Message):
    channel_id = message.chat.id
    channel_name = message.chat.title

    try:
        if await db.is_channel_exist(channel_id):
            await db.delete_channel(channel_id)
            await message.reply(f"**Channel '{channel_name}' removed from my database!**")
        else:
            await message.reply(f"ℹ️ Channel '{channel_name}' not found.")
    except Exception as e:
        print(f"Error removing channel: {e}")
        await message.reply("❌ Failed to remove channel. Try again.")

# Command to list all connected channels
@Client.on_message(filters.command("channels") & filters.private & filters.user(ADMIN))
async def list_channels(client, message: Message):
    try:
        await message.react(emoji=random.choice(REACTIONS), big=True)
    except:
        pass

    channels = await db.get_all_channels()

    if not channels:
        await message.reply("**No channels connected yet.🙁**")
        return

    total_channels = len(channels)
    channel_list = [f"• **{channel['name']}** :- `{channel['_id']}`" for channel in channels]

    header = f"> **Total Channels :- ({total_channels})**\n\n"
    messages = []
    current_message = header

    for line in channel_list:
        if len(current_message) + len(line) + 1 > 4096:
            messages.append(current_message)
            current_message = ""
        current_message += line + "\n"

    if current_message:
        messages.append(current_message)

    for part in messages:
        await message.reply(part)

# Admin management command
@Client.on_message(filters.command("admin") & filters.private & filters.user(ADMIN))
async def admin_management(client, message: Message):
    if len(message.command) < 3:
        await message.reply(
            "**Admin Management**\n\n"
            "**Usage:**\n"
            "`/admin promote [user_id/username] [permissions]` - Promote user\n"
            "`/admin demote [user_id/username]` - Demote user\n\n"
            "**Permission Flags:**\n"
            "`post`=Post Messages, `edit`=Edit Messages, `delete`=Delete Messages\n"
            "`invite`=Invite Users, `pin`=Pin Messages, `info`=Change Info\n\n"
            "**Example:**\n"
            "`/admin promote @username post+edit+delete`"
        )
        return
    
    action = message.command[1].lower()
    user_input = message.command[2]
    permission_flags = message.command[3] if len(message.command) > 3 else ""

    try:
        # Resolve user ID
        try:
            user_id = int(user_input)
        except ValueError:
            user = await client.get_users(user_input)
            user_id = user.id
        
        channels = await db.get_all_channels()
        
        if not channels:
            await message.reply("❌ No channels connected yet.")
            return
        
        processing_msg = await message.reply(f"⏳ Processing {action} for user {user_id}...")
        
        success = []
        failed = []
        details = []

        for channel in channels:
            channel_id = channel['_id']
            channel_name = channel['name']
            
            try:
                # Verify bot's admin status first
                bot_member = await client.get_chat_member(channel_id, "me")
                if not bot_member.privileges or not bot_member.privileges.can_promote_members:
                    failed.append(f"{channel_name} (Bot lacks permissions)")
                    continue

                if action == "promote":
                    # Parse permission flags
                    privileges = ChatPrivileges(
                        can_change_info="info" in permission_flags,
                        can_post_messages="post" in permission_flags,
                        can_edit_messages="edit" in permission_flags,
                        can_delete_messages="delete" in permission_flags,
                        can_invite_users="invite" in permission_flags,
                        can_pin_messages="pin" in permission_flags,
                        can_promote_members=False,  # Never allow this
                        can_manage_chat=True,  # Basic management
                        can_manage_video_chats=False  # Not for channels
                    )

                    # Special handling for channels vs supergroups
                    chat = await client.get_chat(channel_id)
                    if chat.type == enums.ChatType.CHANNEL:
                        # Channels have more restricted permissions
                        privileges = ChatPrivileges(
                            can_post_messages="post" in permission_flags,
                            can_edit_messages="edit" in permission_flags,
                            can_delete_messages="delete" in permission_flags,
                            can_invite_users=False,  # Not available in channels
                            can_pin_messages=False,  # Not available in channels
                            can_promote_members=False,
                            can_change_info=False  # Channel-specific restriction
                        )

                    await client.promote_chat_member(
                        chat_id=channel_id,
                        user_id=user_id,
                        privileges=privileges
                    )
                    success.append(channel_name)
                    details.append(f"{channel_name}: Granted {permission_flags}")

                elif action == "demote":
                    await client.promote_chat_member(
                        chat_id=channel_id,
                        user_id=user_id,
                        privileges=ChatPrivileges(
                            can_change_info=False,
                            can_post_messages=False,
                            can_edit_messages=False,
                            can_delete_messages=False,
                            can_invite_users=False,
                            can_pin_messages=False,
                            can_promote_members=False,
                            can_manage_chat=False,
                            can_manage_video_chats=False
                        )
                    )
                    success.append(channel_name)
                
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                error = str(e)
                if "USER_NOT_PARTICIPANT" in error:
                    failed.append(f"{channel_name} (User not in channel)")
                elif "ADMIN_RANK_EMOJI_NOT_ALLOWED" in error:
                    failed.append(f"{channel_name} (Invalid admin title)")
                elif "RIGHT_FORBIDDEN" in error:
                    # More detailed forbidden error analysis
                    chat = await client.get_chat(channel_id)
                    if chat.type == enums.ChatType.CHANNEL:
                        failed.append(f"{channel_name} (Channel restrictions apply)")
                    else:
                        failed.append(f"{channel_name} (Check bot's admin privileges)")
                else:
                    failed.append(f"{channel_name}: {error}")

        # Compile results
        result_msg = f"**🏁 {action.capitalize()} Results**\n"
        result_msg += f"• 👤 User: `{user_id}`\n"
        result_msg += f"• 📊 Channels: {len(channels)}\n"
        result_msg += f"• ✅ Success: {len(success)}\n"
        result_msg += f"• ❌ Failed: {len(failed)}\n\n"
        
        if success:
            result_msg += "**Successful in:**\n" + "\n".join(success) + "\n\n"
            if details:
                result_msg += "**Permissions granted:**\n" + "\n".join(details) + "\n\n"
        
        if failed:
            result_msg += "**Failed in:**\n" + "\n".join(failed) + "\n\n"
            result_msg += "**Troubleshooting:**\n"
            result_msg += "- Ensure user is member of each channel\n"
            result_msg += "- Verify bot has full admin rights\n"
            result_msg += "- Channels have more restricted permissions\n"
            result_msg += "- Try with fewer permissions first"

        await processing_msg.edit_text(result_msg)
        
    except Exception as e:
        await message.reply(f"❌ Critical Error: {str(e)}")
