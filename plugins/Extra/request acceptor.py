import os
import asyncio
from pyrogram import Client, filters, enums
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPrivileges
from pyrogram.errors import UserAlreadyParticipant, ChatAdminRequired, UserNotParticipant
from config import API_ID, API_HASH, BOT_TOKEN, NEW_REQ_MODE, SESSION_STRING

@Client.on_message(filters.command('accept'))
async def accept(client, message):
    if message.chat.type == enums.ChatType.PRIVATE:
        return await message.reply("🚫 Use this in channels only")
    
    channel_id = message.chat.id
    show = await client.send_message(channel_id, "**⏳ Processing...**")
    
    # Check bot permissions
    try:
        bot_member = await client.get_chat_member(channel_id, "me")
        if not (bot_member.privileges.can_invite_users and bot_member.privileges.can_promote_members):
            return await show.edit("❌ Need 'Invite Users' & 'Add Admins' permissions")
    except Exception as e:
        return await show.edit(f"❌ Permission check failed: {str(e)}")
    
    # Initialize session
    try:
        acc = Client("joinrequest", session_string=SESSION_STRING, api_hash=API_HASH, api_id=API_ID)
        await acc.start()
        user_id = (await acc.get_me()).id
    except Exception as e:
        return await show.edit(f"❌ Session error: {str(e)}")
    
    try:
        # Create invite link
        try:
            invite_url = (await client.create_chat_invite_link(channel_id)).invite_link
            await show.edit("**🔗 Inviting assistant...**")
        except Exception as e:
            raise Exception(f"Invite creation failed: {str(e)}")
        
        # Join channel
        try:
            await acc.join_chat(invite_url)
            await show.edit("**🧑‍💻 Assistant joined...**")
        except UserAlreadyParticipant:
            pass
        except Exception as e:
            raise Exception(f"Join failed: {str(e)}")
        
        # Promote to admin
        try:
            await client.promote_chat_member(
                channel_id, 
                user_id,
                privileges=ChatPrivileges(
                    can_invite_users=True,
                    can_manage_chat=True
                )
            )
            await show.edit("**👑 Promoted assistant...**")
        except Exception as e:
            raise Exception(f"Promotion failed: {str(e)}")
        
        # Process join requests
        requests_count = 0
        last_update = 0
        while True:
            try:
                join_requests = []
                async for request in acc.get_chat_join_requests(channel_id, limit=100):
                    join_requests.append(request)
                
                if not join_requests:
                    break
                
                await acc.approve_all_chat_join_requests(channel_id)
                requests_count += len(join_requests)
                
                # Update progress every 50 requests
                if requests_count - last_update >= 50 or not join_requests:
                    await show.edit(f"**✅ Approved {requests_count} requests...**")
                    last_update = requests_count
                
                await asyncio.sleep(2)  # Rate limit protection
            except Exception as e:
                await show.edit(f"⚠️ Partial: {requests_count} approved\nError: {str(e)}")
                break
        
        await show.edit(f"**🎉 Done! Approved {requests_count} requests**")
        
    except Exception as e:
        await show.edit(f"❌ Failed: {str(e)}")
    finally:
        try:
            await acc.leave_chat(channel_id)
        except:
            pass
        await acc.stop()


@Client.on_chat_join_request(filters.group | filters.channel)
async def approve_new(client, m):
    if not NEW_REQ_MODE:
        return  # If NEW_REQ_MODE is False, the function exits without processing the join request.

    try:
        await client.approve_chat_join_request(m.chat.id, m.from_user.id)
        try:
            await client.send_message(
                m.from_user.id,
                f"**• Hello {m.from_user.mention}! 👋🏻\n• Your request for {m.chat.title} is accepted.**\n\n> **• Powered by: @Stellar_Bots x @Team_SAT_25**"
            )
        except:
            pass
    except Exception as e:
        print(f"⚠️ {str(e)}")
        pass
