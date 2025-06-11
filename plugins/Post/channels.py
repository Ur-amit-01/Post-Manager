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
            "`/admin promote [user_id/username]` - Promote user in all channels\n"
            "`/admin demote [user_id/username]` - Demote user from all channels\n"
            "`/admin check [user_id/username]` - Check user's admin status\n\n"
            "**Examples:**\n"
            "`/admin promote @username`\n"
            "`/admin demote 123456789`"
        )
        return
    
    action = message.command[1].lower()
    user_input = message.command[2]
    
    try:
        # Resolve user ID
        try:
            user_id = int(user_input)
        except ValueError:
            user = await client.get_users(user_input)
            user_id = user.id
        
        channels = await db.get_all_channels()
        
        if not channels:
            await message.reply("No channels connected yet.")
            return
        
        processing_msg = await message.reply(f"⏳ Processing {action} for user {user_id} in {len(channels)} channels...")
        
        success = []
        failed = []
        
        for channel in channels:
            channel_id = channel['_id']
            channel_name = channel['name']
            
            try:
                if action == "promote":
                    # Check if user is already admin
                    try:
                        member = await client.get_chat_member(channel_id, user_id)
                        if member.status in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                            failed.append(f"{channel_name} (Already admin)")
                            continue
                    except:
                        pass
                    
                    # Promote user
                    await client.promote_chat_member(
                        chat_id=channel_id,
                        user_id=user_id,
                        privileges=ChatPrivileges(
                            can_change_info=True,
                            can_post_messages=True,
                            can_edit_messages=True,
                            can_delete_messages=True,
                            can_restrict_members=True,
                            can_invite_users=True,
                            can_pin_messages=True,
                            can_promote_members=False,
                            can_manage_chat=True,
                            can_manage_video_chats=True
                        )
                    )
                    success.append(channel_name)
                    
                elif action == "demote":
                    # Demote user
                    await client.promote_chat_member(
                        chat_id=channel_id,
                        user_id=user_id,
                        privileges=ChatPrivileges(
                            can_change_info=False,
                            can_post_messages=False,
                            can_edit_messages=False,
                            can_delete_messages=False,
                            can_restrict_members=False,
                            can_invite_users=False,
                            can_pin_messages=False,
                            can_promote_members=False,
                            can_manage_chat=False,
                            can_manage_video_chats=False
                        )
                    )
                    success.append(channel_name)
                    
                elif action == "check":
                    # Check admin status
                    try:
                        member = await client.get_chat_member(channel_id, user_id)
                        status = "Owner" if member.status == enums.ChatMemberStatus.OWNER else (
                            "Admin" if member.status == enums.ChatMemberStatus.ADMINISTRATOR else "Member"
                        )
                        success.append(f"{channel_name}: {status}")
                    except Exception as e:
                        failed.append(f"{channel_name}: Error ({str(e)})")
                    continue
                
                else:
                    await processing_msg.edit_text("Invalid action. Use 'promote', 'demote' or 'check'.")
                    return
                
                await asyncio.sleep(1)  # Rate limiting
                
            except Exception as e:
                failed.append(f"{channel_name}: {str(e)}")
        
        # Prepare result message
        result_msg = f"**🏁 {action.capitalize()} Results**\n\n"
        result_msg += f"• User: `{user_id}`\n"
        result_msg += f"• Total Channels: {len(channels)}\n"
        result_msg += f"• Successful: {len(success)}\n"
        result_msg += f"• Failed: {len(failed)}\n\n"
        
        if action == "check":
            result_msg += "**Admin Status:**\n" + "\n".join(success) + "\n\n"
        else:
            result_msg += "**Successful in:**\n" + "\n".join(success) + "\n\n"
        
        if failed:
            result_msg += "**Failed in:**\n" + "\n".join(failed)
        
        await processing_msg.edit_text(result_msg)
        
    except Exception as e:
        await message.reply(f"❌ Error: {str(e)}")

