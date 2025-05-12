from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ForceReply
from urllib.parse import urlparse, parse_qs
from pymongo import MongoClient
import config
import asyncio

QUALITIES = {
    "240p": "240",
    "360p": "360", 
    "480p": "480",
    "720p": "720"
}

# MongoDB setup
db = MongoClient(config.DB_URL).get_database("stream_bot")
tokens_collection = db.tokens
user_data = {}

async def log_to_channel(client: Client, action: str, details: dict):
    """Background logging with sticker"""
    try:
        user = details.get('user', {})
        log_message = (
            f"> **{action}**\n\n"
            f"**🥷:- [{user.get('first_name', 'User')}](tg://user?id={user.get('id', '')})\n**"
            f"**🪪:- `{user.get('id', '')}`**\n"
        )
        
        if 'transformed_url' in details:
            log_message += f"**🖇️:- [Transformed URL]({details['transformed_url']})**\n"
        
        await client.send_message(
            chat_id=config.LOG_CHANNEL,
            text=log_message,
            disable_web_page_preview=True
        )
        await client.send_sticker(
            chat_id=config.LOG_CHANNEL,
            sticker="CAACAgUAAxkBAAIFzmgiOxQ19r2m1i-W49e-VlTJqYtpAAKGBwACu2wYVQI6LPA8iaJvHgQ"
        )
    except Exception as e:
        print(f"Logging error: {e}")

def get_token():
    """Get latest token from MongoDB"""
    if token_data := tokens_collection.find_one(sort=[('_id', -1)]):
        return token_data['token']

def transform_pw_link(url: str, quality: str) -> str:
    """Transform PW Live link with selected quality"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    if not (token := get_token()):
        return "Error: No token found. Please set a token using /token command."
    
    return (
        f"http://master-api-v3.vercel.app/pw/m3u8v2?"
        f"childId={params.get('scheduleId', [''])[0]}&"
        f"parentId={params.get('batchSlug', [''])[0]}&"
        f"token={token}&q={quality}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        f".eyJ1c2VyX2lkIjoiZnJlZSB1c2VyICIsInRnX3VzZXJuYW1lIjoiUFVCTElDIFVTRSAiLCJpYXQiOjE3NDY3MzExNzJ9"
        f".gs1PjfPwzf9ja0OQz7ay7qyysZy-4BDILn-nBbwFAcc"
    )

@Client.on_message(filters.command("token"))
async def set_token(client: Client, message: Message):
    """Handle /token command"""    
    reply = await message.reply_text(
        "**Please send me the new token in reply to this message. 👽**",
        reply_markup=ForceReply(selective=True),
        reply_to_message_id=message.id
    )
    user_data[message.from_user.id] = {"awaiting_token": True}

@Client.on_message(filters.text & ~filters.command(["start", "token", "users", "broadcast"]))
async def handle_text(client: Client, message: Message):
    text = message.text.strip()
    user_id = message.from_user.id
    
    # Handle token update
    if user_id in user_data and user_data[user_id].get("awaiting_token"):
        tokens_collection.insert_one({"token": text})
        asyncio.create_task(log_to_channel(client, "#Token_updated", {
            "user": {
                "id": user_id,
                "first_name": message.from_user.first_name
            }
        }))
        
        try:
            await client.delete_messages(message.chat.id, message.reply_to_message.id)
        except:
            pass
        
        await message.reply_text("**Token successfully updated! ✅**", reply_markup=ReplyKeyboardRemove())
        del user_data[user_id]
        return
    
    # Handle link conversion
    if text.startswith("/amit") and "pw.live/watch" in text:
        user_data[user_id] = {"url": text.replace("/amit", "").strip()}
        await message.reply_text(
            "Please select your preferred quality:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(q, callback_data=q_data)] 
                for q, q_data in QUALITIES.items()
            ])
        )
    elif user_id in user_data and "url" in user_data[user_id]:
        if quality := next((q for q in QUALITIES if q.lower() in text.lower()), None):
            transformed_url = transform_pw_link(user_data[user_id]["url"], QUALITIES[quality])
            asyncio.create_task(log_to_channel(client, "#Link_converted", {
                "user": {
                    "id": user_id,
                    "first_name": message.from_user.first_name
                },
                "transformed_url": transformed_url,
                "quality": quality
            }))
            await message.reply_text(f"Here's your {quality} link 🖇️:\n\n```{transformed_url}```")
            del user_data[user_id]

@Client.on_callback_query()
async def handle_callback(client, callback):
    """Handle quality selection from buttons"""
    user_id = callback.from_user.id
    
    if user_id in user_data and "url" in user_data[user_id]:
        transformed_url = transform_pw_link(user_data[user_id]["url"], callback.data)
        asyncio.create_task(log_to_channel(client, "#Link_converted", {
            "user": {
                "id": user_id,
                "first_name": callback.from_user.first_name
            },
            "transformed_url": transformed_url,
            "quality": f"{callback.data}p"
        }))
        
        await callback.message.edit_text(f"Here's your {callback.data}p link 🖇️:\n\n`{transformed_url}` \n\n> **Click on link to copy ☝🏻🖇️**")
        del user_data[user_id]
    
    await callback.answer()
