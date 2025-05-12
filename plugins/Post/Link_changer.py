from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ForceReply
from urllib.parse import urlparse, parse_qs
from pymongo import MongoClient
import config

QUALITIES = {
    "240p": "240",
    "360p": "360", 
    "480p": "480",
    "720p": "720"
}

# MongoDB setup only for tokens
mongo_client = MongoClient(config.DB_URL)
db = mongo_client["stream_bot"]
tokens_collection = db["tokens"]

user_data = {}

async def log_to_channel(client: Client, action: str, details: dict):
    """Send simplified logs to Telegram channel"""
    user = details.get('user', {})
    
    log_message = (
        f"👤 [{user.get('first_name', 'User')}](tg://user?id={user.get('id', '')}) "
        f"(ID: `{user.get('id', '')}`)\n"
        f"🔹 **{action}**\n"
    )
    
    if 'original_url' in details:
        log_message += f"🔗 [Original URL]({details['original_url']})\n"
    if 'transformed_url' in details:
        log_message += f"🔀 [Transformed URL]({details['transformed_url']})\n"
    if 'quality' in details:
        log_message += f"📶 Quality: {details['quality']}\n"
    
    try:
        await client.send_message(
            chat_id=config.LOG_CHANNEL,
            text=log_message,
            disable_web_page_preview=True
        )
    except Exception as e:
        print(f"Logging error: {e}")

def get_token():
    """Get the latest token from MongoDB"""
    token_data = tokens_collection.find_one(sort=[('_id', -1)])
    return token_data['token'] if token_data else None

def transform_pw_link(original_url, quality):
    """Transform the PW Live link with selected quality"""
    parsed_url = urlparse(original_url)
    query_params = parse_qs(parsed_url.query)
    
    child_id = query_params.get('scheduleId', [''])[0]
    parent_id = query_params.get('batchSlug', [''])[0]
    token = get_token()
    
    if not token:
        return "Error: No token found. Please set a token using /token command."
    
    transformed_url = (
        f"http://master-api-v3.vercel.app/pw/m3u8v2?childId={child_id}&parentId={parent_id}"
        f"&token={token}&q={quality}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        f".eyJ1c2VyX2lkIjoiZnJlZSB1c2VyICIsInRnX3VzZXJuYW1lIjoiUFVCTElDIFVTRSAiLCJpYXQiOjE3NDY3MzExNzJ9"
        f".gs1PjfPwzf9ja0OQz7ay7qyysZy-4BDILn-nBbwFAcc"
    )
    
    return transformed_url

@Client.on_message(filters.command("token"))
async def set_token_command(client: Client, message: Message):
    """Handle /token command to set new token"""
    await log_to_channel(client, "Token update requested", {
        "user": {
            "id": message.from_user.id,
            "first_name": message.from_user.first_name
        }
    })
    
    await message.reply_text(
        "**Please send me the new token in reply to this message. 👽**",
        reply_markup=ForceReply(selective=True),
        reply_to_message_id=message.id
    )
    user_data[message.from_user.id] = {"awaiting_token": True}

@Client.on_message(filters.text & ~filters.command(["start", "token"]))
async def handle_message(client: Client, message: Message):
    text = message.text.strip()
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    # Token handling
    if user_id in user_data and user_data[user_id].get("awaiting_token"):
        tokens_collection.insert_one({"token": text})
        
        await log_to_channel(client, "Token updated", {
            "user": {
                "id": user_id,
                "first_name": user_name
            }
        })
        
        try:
            await client.delete_messages(
                chat_id=message.chat.id,
                message_ids=message.reply_to_message.id
            )
        except:
            pass
        
        await message.reply_text(
            "**Token successfully updated! ✅**",
            reply_markup=ReplyKeyboardRemove()
        )
        del user_data[user_id]
        return
    
    # Link conversion
    if text.startswith("/amit") and "pw.live/watch" in text:
        url = text.replace("/amit", "").strip()
        user_data[user_id] = {"url": url}
        
        await log_to_channel(client, "Conversion started", {
            "user": {
                "id": user_id,
                "first_name": user_name
            },
            "original_url": url
        })
        
        keyboard = [
            [InlineKeyboardButton(q, callback_data=q_data)]
            for q, q_data in QUALITIES.items()
        ]
        
        await message.reply_text(
            "Please select your preferred quality:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Quality selection via text
    elif (user_id in user_data and "url" in user_data[user_id] and
          any(q.lower() in text.lower() for q in QUALITIES.keys())):
        
        selected_quality = next(
            (q for q in QUALITIES.keys() if q.lower() in text.lower()),
            None
        )
        
        if selected_quality:
            quality = QUALITIES[selected_quality]
            original_url = user_data[user_id]["url"]
            transformed_url = transform_pw_link(original_url, quality)
            
            await log_to_channel(client, "Link converted", {
                "user": {
                    "id": user_id,
                    "first_name": user_name
                },
                "original_url": original_url,
                "transformed_url": transformed_url,
                "quality": selected_quality
            })
            
            await message.reply_text(f"Here's your {selected_quality} link 🖇️:\n\n```{transformed_url}```")
            del user_data[user_id]

@Client.on_callback_query()
async def handle_callback_query(client, callback_query):
    """Handle quality selection from inline buttons"""
    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.first_name
    quality = callback_query.data
    
    if user_id in user_data and "url" in user_data[user_id]:
        original_url = user_data[user_id]["url"]
        transformed_url = transform_pw_link(original_url, quality)
        
        await log_to_channel(client, "Link converted", {
            "user": {
                "id": user_id,
                "first_name": user_name
            },
            "original_url": original_url,
            "transformed_url": transformed_url,
            "quality": f"{quality}p"
        })
        
        await callback_query.message.edit_text(
            f"Here's your {quality}p link 🖇️:\n\n```{transformed_url}```"
        )
        del user_data[user_id]
    
    await callback_query.answer()
