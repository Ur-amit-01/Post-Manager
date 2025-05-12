from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ForceReply
from urllib.parse import urlparse, parse_qs
from pymongo import MongoClient
import config  # config.py with API_ID, API_HASH, BOT_TOKEN, LOG_CHANNEL
from datetime import datetime

QUALITIES = {
    "240p": "240",
    "360p": "360", 
    "480p": "480",
    "720p": "720"
}

# MongoDB setup
mongo_client = MongoClient(config.DB_URL)
db = mongo_client["stream_bot"]
tokens_collection = db["tokens"]
logs_collection = db["user_logs"]  # Collection to store logs

user_data = {}

async def log_to_channel(client: Client, action: str, details: dict):
    """Send formatted logs to the log channel"""
    user = details.get('user', {})
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    log_message = (
        f"📊 **Action**: `{action}`\n"
        f"🕒 **Time**: `{timestamp}`\n"
        f"👤 **User**: [{user.get('first_name', '')}](tg://user?id={user.get('id', '')})\n"
        f"🆔 **User ID**: `{user.get('id', '')}`\n"
    )
    
    if 'original_url' in details:
        log_message += f"🔗 **Original URL**: `{details['original_url']}`\n"
    if 'transformed_url' in details:
        log_message += f"🔄 **Transformed URL**: `{details['transformed_url']}`\n"
    if 'quality' in details:
        log_message += f"📺 **Quality**: `{details['quality']}`\n"
    if 'token' in details:
        log_message += f"🔑 **Token Updated**: `{'Yes' if details['token'] else 'No'}`\n"
    
    try:
        await client.send_message(
            chat_id=config.LOG_CHANNEL,
            text=log_message,
            disable_web_page_preview=True
        )
        
        # Also store in MongoDB
        logs_collection.insert_one({
            "timestamp": datetime.now(),
            "action": action,
            "user_id": user.get('id'),
            "user_name": user.get('first_name'),
            "details": details
        })
    except Exception as e:
        print(f"Failed to send log: {e}")

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
    # Log the token request
    await log_to_channel(client, "Token Update Request", {
        "user": {
            "id": message.from_user.id,
            "first_name": message.from_user.first_name
        }
    })
    
    # Ask for token with force reply
    await message.reply_text(
        "**Please send me the new token in reply to this message. 👽**",
        reply_markup=ForceReply(selective=True),
        reply_to_message_id=message.id
    )
    # Store that we're expecting a token from this user
    user_data[message.from_user.id] = {"awaiting_token": True}

@Client.on_message(filters.text & ~filters.command(["start", "token"]))
async def handle_message(client: Client, message: Message):
    text = message.text.strip()
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    # Check if we're expecting a token from this user
    if user_id in user_data and user_data[user_id].get("awaiting_token"):
        # Store the token in MongoDB
        tokens_collection.insert_one({"token": text})
        
        # Log the token update
        await log_to_channel(client, "Token Updated", {
            "user": {
                "id": user_id,
                "first_name": user_name
            },
            "token": True
        })
        
        # Delete the force reply message (if possible)
        try:
            await client.delete_messages(
                chat_id=message.chat.id,
                message_ids=message.reply_to_message.id
            )
        except:
            pass
        
        # Send confirmation
        await message.reply_text(
            "**Token successfully updated! ✅**",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Clean up user data
        del user_data[user_id]
        return
    
    # Check if message starts with /amit and contains pw.live link
    if text.startswith("/amit") and "pw.live/watch" in text:
        # Extract the actual URL (remove /amit prefix)
        url = text.replace("/amit", "").strip()
        
        # Store the URL for this user
        user_data[message.from_user.id] = {"url": url}
        
        # Log the link conversion request
        await log_to_channel(client, "Link Conversion Request", {
            "user": {
                "id": user_id,
                "first_name": user_name
            },
            "original_url": url
        })
        
        # Create quality selection buttons
        keyboard = [
            [InlineKeyboardButton(q, callback_data=q_data)]
            for q, q_data in QUALITIES.items()
        ]
        
        await message.reply_text(
            "Please select your preferred quality:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    # Handle quality selection via text
    elif (message.from_user.id in user_data and 
          "url" in user_data[message.from_user.id] and
          any(q.lower() in message.text.lower() for q in QUALITIES.keys())):
        
        # Find which quality was selected
        selected_quality = next(
            (q for q in QUALITIES.keys() 
             if q.lower() in message.text.lower()),
            None
        )
        
        if selected_quality:
            quality = QUALITIES[selected_quality]
            original_url = user_data[message.from_user.id]["url"]
            transformed_url = transform_pw_link(original_url, quality)
            
            # Log the successful conversion
            await log_to_channel(client, "Link Converted", {
                "user": {
                    "id": user_id,
                    "first_name": user_name
                },
                "original_url": original_url,
                "transformed_url": transformed_url,
                "quality": selected_quality
            })
            
            await message.reply_text(f"Here's your {selected_quality} link 🖇️:\n\n`{transformed_url}`")
            del user_data[message.from_user.id]

@Client.on_callback_query()
async def handle_callback_query(client, callback_query):
    """Handle quality selection from inline buttons"""
    user_id = callback_query.from_user.id
    user_name = callback_query.from_user.first_name
    quality = callback_query.data
    
    if user_id in user_data and "url" in user_data[user_id]:
        original_url = user_data[user_id]["url"]
        transformed_url = transform_pw_link(original_url, quality)
        
        # Log the successful conversion
        await log_to_channel(client, "Link Converted", {
            "user": {
                "id": user_id,
                "first_name": user_name
            },
            "original_url": original_url,
            "transformed_url": transformed_url,
            "quality": f"{quality}p"
        })
        
        await callback_query.message.edit_text(
            f"Here's your {quality}p link 🖇️:\n\n`{transformed_url}`"
        )
        del user_data[user_id]
    
    await callback_query.answer()
