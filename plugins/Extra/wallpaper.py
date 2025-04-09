import random
import requests
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto
from config import LOG_CHANNEL

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# GitHub repository details (no token needed - using raw content)
REPO_OWNER = "Ur-amit-01"
REPO_NAME = "minimalistic-wallpaper-collection"
BRANCH = "main"
FOLDER_PATH = "images"  # Path to wallpapers in your repo

# Base URL for raw GitHub content
GITHUB_RAW_URL = f"https://raw.githubusercontent.com/{REPO_OWNER}/{REPO_NAME}/{BRANCH}/{FOLDER_PATH}/"

# Cache storage for wallpapers
WALLPAPER_CACHE = []

def load_wallpapers():
    """Load all wallpapers from GitHub once at startup"""
    global WALLPAPER_CACHE
    
    # GitHub API URL to list contents (public repo doesn't need token)
    api_url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{FOLDER_PATH}"
    
    try:
        response = requests.get(api_url)
        if response.status_code == 200:
            files = response.json()
            WALLPAPER_CACHE = [
                f"{GITHUB_RAW_URL}{file['name']}"
                for file in files 
                if file['name'].lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
            ]
            logging.info(f"✅ Loaded {len(WALLPAPER_CACHE)} wallpapers into cache")
        else:
            logging.error(f"Failed to load wallpapers: {response.status_code} - {response.text}")
    except Exception as e:
        logging.error(f"Error loading wallpapers: {str(e)}")

# Load wallpapers when bot starts
load_wallpapers()

def get_random_wallpaper():
    """Get a random wallpaper from cache"""
    if not WALLPAPER_CACHE:
        logging.warning("No wallpapers in cache")
        return None
    return random.choice(WALLPAPER_CACHE)

@Client.on_message(filters.command("amit") & filters.channel)
async def send_wallpaper(client, message):
    image_url = get_random_wallpaper()
    if not image_url:
        await message.reply_text("⚠️ No wallpapers available")
        return
    
    await message.reply_photo(
        photo=image_url,
        caption="✨ Minimalist Vibes! 🔥\nTap **Refresh** for more!",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_wallpaper")]
        ])
    )

@Client.on_callback_query(filters.regex("refresh_wallpaper"))
async def refresh_wallpaper(client: Client, query: CallbackQuery):
    new_image_url = get_random_wallpaper()
    if not new_image_url:
        await query.answer("⚠️ No wallpapers available", show_alert=True)
        return
    
    await query.message.edit_media(
        media=InputMediaPhoto(
            media=new_image_url,
            caption="• **Wallpaper Generator Bot 🎨 ...**\n• **Click the button for magic 🧞‍♂️...**"
        ),
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 New Wallpaper", callback_data="refresh_wallpaper")]
        ])
    )
    
    # Log to channel
    user = query.from_user
    await client.send_message(
        LOG_CHANNEL,
        f"🖼 Wallpaper refreshed by [{user.first_name}](tg://user?id={user.id})\n"
        f"🔗 [View Image]({new_image_url})",
        disable_web_page_preview=True
    )
