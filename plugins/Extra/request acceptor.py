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
    acc = None
    
    try:
        # Check bot permissions
        try:
            bot_member = await client.get_chat_member(channel_id, "me")
            if not (bot_member.privileges.can_invite_users and bot_member.privileges.can_promote_members):
                return await show.edit("❌ Need 'Invite Users' & 'Add Admins' permissions")
        except Exception as e:
            return await show.edit(f"❌ Permission check failed: {str(e)}")
        
        # Initialize session with longer timeout
        try:
            acc = Client(
                "joinrequest", 
                session_string=SESSION_STRING, 
                api_hash=API_HASH, 
                api_id=API_ID,
                sleep_threshold=60,  # Increased timeout
                in_memory=True  # Better for short-lived sessions
            )
            await acc.start()
            user_id = (await acc.get_me()).id
        except Exception as e:
            return await show.edit(f"❌ Session error: {str(e)}")
        
        # Create more stable invite link
        try:
            invite_url = (await client.create_chat_invite_link(
                channel_id,
                creates_join_request=True
            )).invite_link
            await show.edit("**🔗 Inviting assistant...**")
        except Exception as e:
            raise Exception(f"Invite creation failed: {str(e)}")
        
        # Join channel with retry
        max_retries = 3
        for attempt in range(max_retries):
            try:
                await acc.join_chat(invite_url)
                await asyncio.sleep(2)  # Wait for join to complete
                await show.edit("**🧑‍💻 Assistant joined...**")
                break
            except UserAlreadyParticipant:
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise Exception(f"Join failed after {max_retries} attempts: {str(e)}")
                await asyncio.sleep(3)
                continue
        
        # Promote with confirmation
        try:
            await client.promote_chat_member(
                channel_id, 
                user_id,
                privileges=ChatPrivileges(
                    can_invite_users=True,
                    can_manage_chat=True,
                    can_delete_messages=False,
                    can_restrict_members=False
                )
            )
            # Verify promotion
            await asyncio.sleep(2)
            assistant_member = await client.get_chat_member(channel_id, user_id)
            if assistant_member.status != enums.ChatMemberStatus.ADMINISTRATOR:
                raise Exception("Assistant promotion verification failed")
            await show.edit("**👑 Promoted assistant...**")
        except Exception as e:
            raise Exception(f"Promotion failed: {str(e)}")
        
        # Process join requests with better error handling
        requests_count = 0
        last_update = 0
        max_attempts = 5  # Max attempts per batch
        batch_size = 50   # Smaller batches
        
        while True:
            attempt = 0
            success = False
            
            while attempt < max_attempts and not success:
                try:
                    join_requests = []
                    async for request in acc.get_chat_join_requests(channel_id, limit=batch_size):
                        join_requests.append(request)
                    
                    if not join_requests:
                        success = True
                        break
                    
                    await acc.approve_all_chat_join_requests(channel_id)
                    requests_count += len(join_requests)
                    success = True
                    
                    # Update progress
                    if requests_count - last_update >= batch_size or not join_requests:
                        await show.edit(f"**✅ Approved {requests_count} requests...**")
                        last_update = requests_count
                    
                    # More conservative delay
                    await asyncio.sleep(3)
                    
                except FloodWait as e:
                    await show.edit(f"⏳ Waiting {e.value} seconds due to flood wait...")
                    await asyncio.sleep(e.value + 2)
                    attempt += 1
                except Exception as e:
                    attempt += 1
                    if attempt == max_attempts:
                        raise Exception(f"Request approval failed after {max_attempts} attempts: {str(e)}")
                    await asyncio.sleep(5)
            
            if not success:
                break
                
            if not join_requests:  # No more requests
                break
        
        await show.edit(f"**🎉 Done! Approved {requests_count} requests**")
        
    except Exception as e:
        await show.edit(f"❌ Failed: {str(e)}")
    finally:
        if acc:
            try:
                # Only leave if we're done processing
                if 'requests_count' in locals():
                    await asyncio.sleep(5)  # Final delay
                    await acc.leave_chat(channel_id)
            except:
                pass
            try:
                await acc.stop()
            except:
                pass

@Client.on_chat_join_request(filters.group | filters.channel)
async def approve_new(client, m):
    if not NEW_REQ_MODE:
        return  # Exit if NEW_REQ_MODE is False

    try:
        await client.approve_chat_join_request(m.chat.id, m.from_user.id)
        try:
            await client.send_message(
                m.from_user.id,
                f"**• Hello {m.from_user.mention}! 👋🏻\n• Your request for {m.chat.title} is accepted.**",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("Team SAT 💫", url="https://t.me/Team_SAT_25")]
                    ]
                )
            )
        except:
            pass
    except Exception as e:
        print(f"⚠️ {str(e)}")
        pass
