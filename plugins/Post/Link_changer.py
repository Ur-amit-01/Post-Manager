from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardRemove, ForceReply
from urllib.parse import urlparse, parse_qs
from pymongo import MongoClient
import config
import asyncio
import random
import re

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

# Example reactions (you can customize these)
SUCCESS_REACTIONS = ["👍", "🔥", "🚀", "🎯", "✅"]

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
        if 'token' in details:
            log_message += f"**🔑:- {details['token']}**\n"
        
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
    return None

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
        f".eyJ1c2VyX2lkIjoiZnJlZSB1c2VyICIsInRnX3VzZXJuYW1lIjoiUFVCTElDIFVTRSIsImlhdCI6MTc0OTYxOTUzM30"
        f".oRI_9FotOi3Av9S2Wrr2g6VXUHJEknWVY91-TZ5XdNg"
    )

def transform_mpd_link(url: str, quality: str) -> str:
    """Transform MPD link with selected quality"""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    if not (token := get_token()):
        return "Error: No token found. Please set a token using /token command."
    
    child_id = params.get('childId', [''])[0]
    parent_id = params.get('parentId', [''])[0]
    
    if not child_id or not parent_id:
        return "Error: Could not extract required parameters from the MPD link."
    return (
        f"http://master-api-v3.vercel.app/pw/m3u8v2?"
        f"childId={params.get('scheduleId', [''])[0]}&"
        f"parentId={params.get('batchSlug', [''])[0]}&"
        f"token={token}&q={quality}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        f".eyJ1c2VyX2lkIjoiZnJlZSB1c2VyICIsInRnX3VzZXJuYW1lIjoiUFVCTElDIFVTRSIsImlhdCI6MTc0OTYxOTUzM30"
        f".oRI_9FotOi3Av9S2Wrr2g6VXUHJEknWVY91-TZ5XdNg"
    )
    

@Client.on_message(filters.command("token") & filters.user(config.ADMIN))
async def set_token(client: Client, message: Message):
    """Handle /token command (admin only)"""    
    reply = await message.reply_text(
        "**Please send me the new token in reply to this message. 👽**",
        reply_markup=ForceReply(selective=True),
        reply_to_message_id=message.id
    )
    user_data[message.from_user.id] = {"awaiting_token": True}

@Client.on_message(filters.private & filters.reply & filters.text)
async def process_token_reply(client: Client, message: Message):
    """Process token reply from user"""
    user_id = message.from_user.id
    
    # Check if this is a reply to our token request
    if (user_id in user_data and 
        user_data[user_id].get("awaiting_token") and 
        message.reply_to_message and 
        "send me the new token" in message.reply_to_message.text):
        
        # Update token in MongoDB
        new_token = message.text.strip()
        tokens_collection.insert_one({"token": new_token})
        
        # Clean up and confirm
        del user_data[user_id]
        await message.reply_text(
            "✅ Token updated successfully!",
            reply_markup=ReplyKeyboardRemove()
        )
        
        # Log the update
        asyncio.create_task(log_to_channel(client, "#Token_Updated", {
            "user": {
                "id": user_id,
                "first_name": message.from_user.first_name
            },
            "token": f"`{new_token[:5]}...{new_token[-5:]}`"  # Show partial token for security
        }))

@Client.on_message(filters.command(["amit", "tawheed", "twhd", "kabir", "batman"]))
async def handle_amit_command(client: Client, message: Message):
    """Handle /amit command"""
    text = message.text.strip()
    user_id = message.from_user.id
    
    # If only /amit is sent
    if text == "/amit":
        example_text = (
            "> **Send links in this format 👇🏻**\n"
            "> **/amit https://pw.live/watch?v=abc123&bat**\n"
            "> **or**\n"
            "> **/amit https://d1d34p8vz63oiq.cloudfront.net/.../master.mpd?childId=...&parentId=...**"
        )
        await message.reply_text(example_text)
        return
    
    # Check for PW Live link
    if "pw.live/watch" in text:
        user_data[user_id] = {
            "url": text.replace("/amit", "").strip(),
            "link_type": "pw_live"
        }
        await message.reply_text(
            "**Please select your preferred quality:🎦**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(q, callback_data=q_data)] 
                for q, q_data in QUALITIES.items()
            ])
        )
    # Check for MPD link
    elif "d1d34p8vz63oiq.cloudfront.net" in text and "master.mpd" in text:
        user_data[user_id] = {
            "url": text.replace("/amit", "").strip(),
            "link_type": "mpd"
        }
        await message.reply_text(
            "**Please select your preferred quality:🎦**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(q, callback_data=q_data)] 
                for q, q_data in QUALITIES.items()
            ])
        )
    else:
        await message.reply_text("❌ Unsupported link format. Please send a valid PW Live or MPD link.")

@Client.on_callback_query()
async def handle_callback(client, callback):
    """Handle quality selection from buttons"""
    user_id = callback.from_user.id
    
    if user_id in user_data and "url" in user_data[user_id]:
        link_type = user_data[user_id].get("link_type", "pw_live")
        
        if link_type == "pw_live":
            transformed_url = transform_pw_link(user_data[user_id]["url"], callback.data)
        elif link_type == "mpd":
            transformed_url = transform_mpd_link(user_data[user_id]["url"], callback.data)
        else:
            await callback.message.edit_text("❌ Error: Unknown link type")
            return
            
        if transformed_url.startswith("Error:"):
            await callback.message.edit_text(transformed_url)
            return
            
        asyncio.create_task(log_to_channel(client, "#Link_converted", {
            "user": {
                "id": user_id,
                "first_name": callback.from_user.first_name
            },
            "transformed_url": transformed_url,
            "quality": f"{callback.data}p",
            "link_type": link_type
        }))
        
        # Send the transformed URL
        msg = await callback.message.edit_text(
            f"> **Here's your {callback.data}p link 🖇️:**\n\n```\n{transformed_url}\n```\n> **Click on link to copy ☝🏻🖇️**"
        )
        
        # Add a random reaction to the message
        try:
            await msg.react(emoji=random.choice(SUCCESS_REACTIONS), big=True)
        except Exception as e:
            print(f"Error adding reaction: {e}")
        
        del user_data[user_id]
    
    await callback.answer()
