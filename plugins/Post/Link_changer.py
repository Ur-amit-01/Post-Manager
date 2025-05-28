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

SUCCESS_REACTIONS = ["👍", "🔥", "🚀", "🎯", "✅"]

async def log_error(client: Client, error: str, details: dict):
    """Log errors to channel"""
    try:
        await client.send_message(
            chat_id=config.LOG_CHANNEL,
            text=f"🚨 **Error**: `{error}`\n\nDetails: `{details}`"
        )
    except Exception as e:
        print(f"Error logging error: {e}")

async def log_to_channel(client: Client, action: str, details: dict):
    """Background logging with sticker"""
    try:
        user = details.get('user', {})
        log_message = (
            f"> **{action}**\n\n"
            f"**User**: [{user.get('first_name', 'User')}](tg://user?id={user.get('id', '')})\n"
            f"**ID**: `{user.get('id', '')}`\n"
        )
        
        if 'transformed_url' in details:
            log_message += f"**URL**: [Transformed Link]({details['transformed_url']})\n"
        if 'token' in details:
            log_message += f"**Token**: `{details['token'][:5]}...{details['token'][-5:]}`\n"
        if 'original_url' in details:
            log_message += f"**Original URL**: `{details['original_url']}`\n"
        
        await client.send_message(
            chat_id=config.LOG_CHANNEL,
            text=log_message,
            disable_web_page_preview=True
        )
    except Exception as e:
        await log_error(client, f"Logging error: {str(e)}", details)

def get_token():
    """Get latest token from MongoDB"""
    try:
        if token_data := tokens_collection.find_one(sort=[('_id', -1)]):
            return token_data['token']
        return None
    except Exception as e:
        print(f"Token fetch error: {e}")
        return None

def transform_pw_link(url: str, quality: str) -> str:
    """Transform PW Live link with selected quality"""
    try:
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
    except Exception as e:
        return f"Error processing PW Live link: {str(e)}"

def transform_mpd_link(url: str, quality: str) -> str:
    """Transform MPD link with selected quality"""
    try:
        # First try standard URL parsing
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        if not (token := get_token()):
            return "Error: No token found. Please set a token using /token command."
        
        # Try different parameter names
        child_id = params.get('childId', params.get('childid', [''])[0]
        parent_id = params.get('parentId', params.get('parentid', [''])[0])
        
        # If still not found, try regex as fallback
        if not child_id or not parent_id:
            child_match = re.search(r'child[Ii]d=([^&]+)', url)
            parent_match = re.search(r'parent[Ii]d=([^&]+)', url)
            child_id = child_match.group(1) if child_match else ''
            parent_id = parent_match.group(1) if parent_match else ''
        
        if not child_id or not parent_id:
            return "Error: Could not extract required parameters from the MPD link."
        
        return (
            f"http://master-api-v3.vercel.app/pw/m3u8v2?"
            f"childId={child_id}&"
            f"parentId={parent_id}&"
            f"token={token}&q={quality}&authorization=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
            f".eyJ1c2VyX2lkIjoiZnJlZSB1c2VyICIsInRnX3VzZXJuYW1lIjoiUFVCTElDIFVTRSAiLCJpYXQiOjE3NDY3MzExNzJ9"
            f".gs1PjfPwzf9ja0OQz7ay7qyysZy-4BDILn-nBbwFAcc"
        )
    except Exception as e:
        return f"Error processing MPD link: {str(e)}"

@Client.on_message(filters.command("token") & filters.user(config.ADMIN))
async def set_token(client: Client, message: Message):
    """Handle /token command (admin only)"""    
    try:
        reply = await message.reply_text(
            "**Please send me the new token in reply to this message. 👽**",
            reply_markup=ForceReply(selective=True),
            reply_to_message_id=message.id
        )
        user_data[message.from_user.id] = {"awaiting_token": True}
    except Exception as e:
        await message.reply_text(f"Error: {str(e)}")
        await log_error(client, f"Token command error: {str(e)}", {"user_id": message.from_user.id})

@Client.on_message(filters.private & filters.reply & filters.text)
async def process_token_reply(client: Client, message: Message):
    """Process token reply from user"""
    try:
        user_id = message.from_user.id
        
        if (user_id in user_data and 
            user_data[user_id].get("awaiting_token") and 
            message.reply_to_message and 
            "send me the new token" in message.reply_to_message.text.lower()):
            
            new_token = message.text.strip()
            if not new_token:
                await message.reply_text("❌ Token cannot be empty!")
                return
                
            tokens_collection.insert_one({"token": new_token})
            del user_data[user_id]
            
            await message.reply_text(
                "✅ Token updated successfully!",
                reply_markup=ReplyKeyboardRemove()
            )
            
            await log_to_channel(client, "#Token_Updated", {
                "user": {
                    "id": user_id,
                    "first_name": message.from_user.first_name
                },
                "token": new_token,
                "original_url": message.reply_to_message.text
            })
    except Exception as e:
        await message.reply_text(f"Error processing token: {str(e)}")
        await log_error(client, f"Token processing error: {str(e)}", {"user_id": message.from_user.id})

@Client.on_message(filters.command("amit"))
async def handle_amit_command(client: Client, message: Message):
    """Handle /amit command"""
    try:
        text = message.text.strip()
        user_id = message.from_user.id
        
        if text == "/amit":
            example_text = (
                "> **Send links in this format 👇🏻**\n"
                "> `/amit https://pw.live/watch?v=abc123&bat`\n"
                "> **or**\n"
                "> `/amit https://d1d34p8vz63oiq.cloudfront.net/.../master.mpd?childId=...&parentId=...`"
            )
            await message.reply_text(example_text)
            return
        
        # Normalize URL (remove command and whitespace)
        url = text.replace("/amit", "").strip()
        
        # Validate URL
        if not url.startswith(('http://', 'https://')):
            await message.reply_text("❌ Invalid URL format. Please include http:// or https://")
            return
        
        # Determine link type
        if "pw.live/watch" in url:
            link_type = "pw_live"
        elif "d1d34p8vz63oiq.cloudfront.net" in url and ("master.mpd" in url or "childId=" in url):
            link_type = "mpd"
        else:
            await message.reply_text("❌ Unsupported link format. Please send a valid PW Live or MPD link.")
            return
        
        # Store user data
        user_data[user_id] = {
            "url": url,
            "link_type": link_type,
            "original_message": message.id
        }
        
        await message.reply_text(
            "**Please select your preferred quality:🎦**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(q, callback_data=q_data)] 
                for q, q_data in QUALITIES.items()
            ])
        )
        
    except Exception as e:
        await message.reply_text(f"❌ Error processing your request: {str(e)}")
        await log_error(client, f"Amit command error: {str(e)}", {
            "user_id": message.from_user.id,
            "text": message.text
        })

@Client.on_callback_query()
async def handle_callback(client, callback):
    """Handle quality selection from buttons"""
    try:
        user_id = callback.from_user.id
        
        if user_id not in user_data or "url" not in user_data[user_id]:
            await callback.answer("Session expired. Please send the link again.", show_alert=True)
            return
            
        link_data = user_data[user_id]
        url = link_data["url"]
        link_type = link_data.get("link_type", "pw_live")
        
        # Transform the URL based on type
        if link_type == "pw_live":
            transformed_url = transform_pw_link(url, callback.data)
        elif link_type == "mpd":
            transformed_url = transform_mpd_link(url, callback.data)
        else:
            await callback.message.edit_text("❌ Error: Unknown link type")
            return
            
        if transformed_url.startswith("Error:"):
            await callback.message.edit_text(transformed_url)
            await log_error(client, "Link transformation failed", {
                "user_id": user_id,
                "url": url,
                "error": transformed_url,
                "link_type": link_type
            })
            return
            
        # Log successful conversion
        await log_to_channel(client, "#Link_Converted", {
            "user": {
                "id": user_id,
                "first_name": callback.from_user.first_name
            },
            "transformed_url": transformed_url,
            "original_url": url,
            "quality": f"{callback.data}p",
            "link_type": link_type
        })
        
        # Send the result
        await callback.message.edit_text(
            f"🔗 **{callback.data}p Link**:\n\n```\n{transformed_url}\n```\n"
            "Click above to copy the link.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 Copy Link", url=transformed_url)]
            ])
        )
        
        # Add random reaction
        try:
            await callback.message.react(emoji=random.choice(SUCCESS_REACTIONS), big=True)
        except:
            pass
            
        # Clean up
        del user_data[user_id]
        
    except Exception as e:
        await callback.answer(f"Error: {str(e)}", show_alert=True)
        await log_error(client, f"Callback error: {str(e)}", {
            "user_id": callback.from_user.id,
            "data": callback.data
        })
    finally:
        await callback.answer()
