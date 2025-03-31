import os
import random
import logging
import time
import asyncio
import pyrogram
from pyrogram import Client, filters, enums
from pyrogram.errors import FloodWait, UserIsBlocked, InputUserDeactivated, UserAlreadyParticipant, InviteHashExpired, UsernameNotOccupied
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from config import *

start_time = time.time()
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
    
#————————————————————————————————————————————————————————————————————————————————————————————

class batch_temp(object):
    IS_BATCH = {}

async def downstatus(client, statusfile, message, chat):
    while True:
        if os.path.exists(statusfile):
            break
        await asyncio.sleep(1)

    while os.path.exists(statusfile):
        with open(statusfile, "r") as downread:
            txt = downread.read()
        try:
            await client.edit_message_text(chat, message.id, f"> **Downloading 📥** \n\n**{txt}**")
            await asyncio.sleep(2)
        except:
            await asyncio.sleep(2)

async def upstatus(client, statusfile, message, chat):
    while True:
        if os.path.exists(statusfile):
            break
        await asyncio.sleep(1)
    while os.path.exists(statusfile):
        with open(statusfile, "r") as upread:
            txt = upread.read()
        try:
            await client.edit_message_text(chat, message.id, f"> **Uploading 📤** \n\n**{txt}**")
            await asyncio.sleep(2)
        except:
            await asyncio.sleep(2)

async def progress(current, total, message, type):
    try:
        # Initialize or reset the start time for each task
        if not hasattr(progress, "start_time") or progress.task_type != type:
            progress.start_time = time.time()
            progress.task_type = type  # Keep track of the current task type

        # Calculate elapsed time
        elapsed_time = time.time() - progress.start_time  # Elapsed time in seconds

        # Calculate percentage progress
        percent = current * 100 / total
        processed = current / (1024 * 1024)  # Processed in MB
        total_size = total / (1024 * 1024)  # Total size in MB
        
        # Calculate the download/upload speed in MB/s
        speed = current / elapsed_time / (1024 * 1024) if elapsed_time > 0 else 0

        # Calculate estimated time remaining (ETA)
        if speed > 0:
            remaining_bytes = total - current
            eta_seconds = remaining_bytes / (speed * 1024 * 1024)
            hours, remainder = divmod(int(eta_seconds), 3600)
            minutes, seconds = divmod(remainder, 60)
            eta_formatted = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"
        else:
            eta_formatted = "Calculating..."

        # Format the elapsed time in a readable format (hours, minutes, seconds)
        hours, remainder = divmod(int(elapsed_time), 3600)
        minutes, seconds = divmod(remainder, 60)
        elapsed_formatted = f"{hours}h {minutes}m {seconds}s" if hours else f"{minutes}m {seconds}s"

        # Create a progress bar
        progress_bar_length = 10  # Length of the progress bar
        filled_length = int(progress_bar_length * percent / 100)
        progress_bar = "▰" * filled_length + "▱" * (progress_bar_length - filled_length)

        # Update progress message in file
        with open(f'{message.id}{type}status.txt', "w") as fileup:
            fileup.write(
                f"**{progress_bar}**\n"
                f"**📈 Progress**: {percent:.1f}%\n"
                f"**📦 Processed**: {processed:.2f}MB / {total_size:.2f}MB\n"
                f"**⚡ Speed**: {speed:.2f} MB/s\n"
                f"**⏱️ Elapsed Time**: {elapsed_formatted}\n"
                f"**⏳ ETA**: {eta_formatted}"
            )

        # Update the message with the progress
        if percent % 5 == 0:  # Update every 5% for smoother experience
            try:
                await message.edit_text(
                    f"**🚀 {type.capitalize()} Progress**\n\n"
                    f"**[{progress_bar}]**\n"
                    f"**📈 Progress**: {percent:.1f}%\n"
                    f"**📦 Processed**: {processed:.2f}MB / {total_size:.2f}MB\n"
                    f"**⚡ Speed**: {speed:.2f} MB/s\n"
                    f"**⏱️ Elapsed Time**: {elapsed_formatted}\n"
                    f"**⏳ ETA**: {eta_formatted}"
                )
            except Exception as e:
                # In case of any errors, log them
                logger.error(f"Error updating message: {e}")
        
    except Exception as e:
        logger.error(f"Error in progress function: {e}")
#————————————————————————————————————————————————————————————————————————————————————————————

@Client.on_message(filters.command(["cancel"]))
async def send_cancel(client: Client, message: Message):
    logger.info(f"/cancel command triggered by user {message.from_user.id}")
    batch_temp.IS_BATCH[message.from_user.id] = True
    await client.send_message(
        chat_id=message.chat.id,
        text="**Batch Successfully Cancelled.**"
    )

@Client.on_message(filters.text & filters.private & filters.regex("https://t.me/"))
async def save(client: Client, message: Message):
    if "https://t.me/" in message.text:
        if batch_temp.IS_BATCH.get(message.from_user.id) == False:
            return await message.reply_text("**One Task Is Already Processing. Wait For It To Complete. If You Want To Cancel This Task Then Use - /cancel**")

        datas = message.text.split("/")
        temp = datas[-1].replace("?single", "").split("-")
        fromID = int(temp[0].strip())
        try:
            toID = int(temp[1].strip())
        except:
            toID = fromID

        batch_temp.IS_BATCH[message.from_user.id] = False

        # Connect using the session string
        acc = Client("manual_session", session_string=SESSION_STRING, api_hash=API_HASH, api_id=API_ID)
        await acc.connect()

        try:
            for msgid in range(fromID, toID + 1):
                if batch_temp.IS_BATCH.get(message.from_user.id):
                    break

                # Handle private chats
                if "https://t.me/c/" in message.text:
                    chatid = int("-100" + datas[4])
                    source_link = f"https://t.me/c/{datas[4]}/{msgid}"
                    
                    try:
                        await handle_private(client, acc, message, chatid, msgid)

                        # Log message with source link
                        log_text = f"📩 **New Message saved** ☝🏻☝🏻\n\n**☃️ Nᴀᴍᴇ: {message.from_user.mention}**\n👤 **User ID:** `{message.from_user.id}`\n🔗 **Source:** [Click Here]({source_link})"
                        await client.send_message(LOG_CHANNEL, log_text, disable_web_page_preview=True)

                    except Exception as e:
                        if ERROR_MESSAGE:
                            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

                # Handle public chats
                else:
                    username = datas[3]
                    source_link = f"https://t.me/{username}/{msgid}"

                    try:
                        msg = await client.get_messages(username, msgid)
                    except UsernameNotOccupied:
                        await client.send_message(message.chat.id, "The username is not occupied by anyone", reply_to_message_id=message.id)
                        return

                    try:
                        # Copy message to user and log channel
                        await client.copy_message(message.chat.id, msg.chat.id, msg.id, reply_to_message_id=message.id)
                        await client.copy_message(LOG_CHANNEL, msg.chat.id, msg.id)

                        # Log message with source link
                        log_text = f"📩 **New Message saved** ☝🏻☝🏻\n\n**☃️ Nᴀᴍᴇ: {message.from_user.mention}**\n👤 **User ID:** `{message.from_user.id}`\n🔗 **Source: [Click Here]({source_link})**"
                        await client.send_message(LOG_CHANNEL, log_text, disable_web_page_preview=True)

                    except Exception as e:
                        if ERROR_MESSAGE:
                            await client.send_message(message.chat.id, f"Error: {e}", reply_to_message_id=message.id)

                await asyncio.sleep(1)

        finally:
            batch_temp.IS_BATCH[message.from_user.id] = True
            await acc.disconnect()

# handle private

async def handle_private(client: Client, acc, message: Message, chatid: int, msgid: int):
    msg: Message = await acc.get_messages(chatid, msgid)
    if msg.empty: 
        return 
    msg_type = get_message_type(msg)
    if not msg_type: 
        return 
    chat = message.chat.id
    user_id = message.from_user.id  # User's DM ID

    if batch_temp.IS_BATCH.get(user_id): 
        return 

    if msg_type == "Text":
        try:
            text_msg = await client.send_message(user_id, msg.text, entities=msg.entities, parse_mode=enums.ParseMode.HTML)
            await client.send_message(LOG_CHANNEL, msg.text, entities=msg.entities, parse_mode=enums.ParseMode.HTML)
            return 
        except Exception as e:
            await client.send_message(chat, f"Error: {e}", reply_to_message_id=message.id)
            return 

    smsg = await client.send_message(chat, '**Downloading**', reply_to_message_id=message.id)
    asyncio.create_task(downstatus(client, f'{message.id}downstatus.txt', smsg, chat))

    try:
        file = await acc.download_media(msg, progress=progress, progress_args=[message, "down"])
        os.remove(f'{message.id}downstatus.txt')
    except Exception as e:
        await client.send_message(chat, f"Error: {e}", reply_to_message_id=message.id)
        return await smsg.delete()

    if batch_temp.IS_BATCH.get(user_id): 
        return 

    asyncio.create_task(upstatus(client, f'{message.id}upstatus.txt', smsg, chat))

    caption = msg.caption if msg.caption else None

    # Sending to both DM and log channel separately
    async def send_to_user_and_log(send_func, **kwargs):
        try:
            # Send to user's DM
            sent_msg = await send_func(user_id, **kwargs)

            # Send to log channel separately (new message)
            await send_func(LOG_CHANNEL, **kwargs)
        except Exception as e:
            await client.send_message(chat, f"Error: {e}", reply_to_message_id=message.id)

    if msg_type == "Document":
        thumb = await acc.download_media(msg.document.thumbs[0].file_id) if msg.document.thumbs else None
        await send_to_user_and_log(client.send_document, document=file, thumb=thumb, caption=caption, parse_mode=enums.ParseMode.HTML)
        if thumb:
            os.remove(thumb)

    elif msg_type == "Video":
        thumb = await acc.download_media(msg.video.thumbs[0].file_id) if msg.video.thumbs else None
        await send_to_user_and_log(client.send_video, video=file, duration=msg.video.duration, width=msg.video.width, height=msg.video.height, thumb=thumb, caption=caption, parse_mode=enums.ParseMode.HTML)
        if thumb:
            os.remove(thumb)

    elif msg_type == "Animation":
        await send_to_user_and_log(client.send_animation, animation=file, caption=caption, parse_mode=enums.ParseMode.HTML)

    elif msg_type == "Sticker":
        await send_to_user_and_log(client.send_sticker, sticker=file)

    elif msg_type == "Voice":
        await send_to_user_and_log(client.send_voice, voice=file, caption=caption, parse_mode=enums.ParseMode.HTML)

    elif msg_type == "Audio":
        thumb = await acc.download_media(msg.audio.thumbs[0].file_id) if msg.audio.thumbs else None
        await send_to_user_and_log(client.send_audio, audio=file, thumb=thumb, caption=caption, parse_mode=enums.ParseMode.HTML)
        if thumb:
            os.remove(thumb)

    elif msg_type == "Photo":
        await send_to_user_and_log(client.send_photo, photo=file, caption=caption, parse_mode=enums.ParseMode.HTML)

    if os.path.exists(f'{message.id}upstatus.txt'): 
        os.remove(f'{message.id}upstatus.txt')
    os.remove(file)
    await smsg.delete()


# get the type of message
def get_message_type(msg: pyrogram.types.messages_and_media.message.Message):
    try:
        msg.document.file_id
        return "Document"
    except:
        pass

    try:
        msg.video.file_id
        return "Video"
    except:
        pass

    try:
        msg.animation.file_id
        return "Animation"
    except:
        pass

    try:
        msg.sticker.file_id
        return "Sticker"
    except:
        pass

    try:
        msg.voice.file_id
        return "Voice"
    except:
        pass

    try:
        msg.audio.file_id
        return "Audio"
    except:
        pass

    try:
        msg.photo.file_id
        return "Photo"
    except:
        pass

    try:
        msg.text
        return "Text"
    except:
        pass


