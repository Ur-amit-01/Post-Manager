from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ForceReply
from urllib.parse import urlparse, parse_qs
from pymongo import MongoClient
import config  # config.py with API_ID, API_HASH, BOT_TOKEN

QUALITIES = {
    "240p": "240",
    "360p": "360", 
    "480p": "480",
    "720p": "720"
}

# MongoDB setup
mongo_client = MongoClient(config.MONGO_URI)
db = mongo_client["stream_bot"]
tokens_collection = db["tokens"]

user_data = {}

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
    # Ask for token with force reply
    await message.reply_text(
        "**Please send me the new token in reply to this message. 👽**",
        reply_markup=ForceReply(selective=True),
        reply_to_message_id=message.id
    )
    # Store that we're expecting a token from this user
    user_data[message.from_user.id] = {"awaiting_token": True}

@Client.on_message(filters.text & ~filters.command(["start"]))
async def handle_message(client: Client, message: Message):
    text = message.text.strip()
    user_id = message.from_user.id

    # Check if we're expecting a token from this user
    if user_id in user_data and user_data[user_id].get("awaiting_token"):
        # Store the token in MongoDB
        tokens_collection.insert_one({"token": text})
        
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
            transformed_url = transform_pw_link(
                user_data[message.from_user.id]["url"],
                quality
            )
            await message.reply_text(f"Here's your {selected_quality} link 🖇️:\n\n`{transformed_url}`")
            del user_data[message.from_user.id]

@Client.on_callback_query()
async def handle_callback_query(client, callback_query):
    """Handle quality selection from inline buttons"""
    user_id = callback_query.from_user.id
    quality = callback_query.data
    
    if user_id in user_data and "url" in user_data[user_id]:
        transformed_url = transform_pw_link(user_data[user_id]["url"], quality)
        
        await callback_query.message.edit_text(
            f"Here's your {quality}p link 🖇️:\n\n`{transformed_url}`"
        )
        del user_data[user_id]
    
    await callback_query.answer()
