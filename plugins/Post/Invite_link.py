from datetime import datetime, timedelta
import time
import re
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from plugins.helper.db import db
import random
import asyncio
from config import *
from plugins.Post.admin_panel import admin_filter

@Client.on_message(filters.command("genlink") & filters.private & admin_filter)
async def generate_invite_links(client, message: Message):
    # Parse time argument
    expire_time, time_suffix = parse_time_argument(message)

    processing_msg = await message.reply("🔍 <b>Scanning and categorizing channels...</b>")

    # Define categories with grouping rules
    categories = {
        "YAKEEN": {
            "condition": lambda name: 'yakeen' in name.lower(),
            "emoji": "🔥",
            "separate_message": True
        },
        "CHEMISTRY": {
            "subcategories": {
                "PHYSICAL CHEMISTRY": {"keywords": ["pc", "physical"], "emoji": "⚗️"},
                "ORGANIC CHEMISTRY": {"keywords": ["oc", "organic"], "emoji": "🧪"},
                "INORGANIC CHEMISTRY": {"keywords": ["ioc", "inorganic"], "emoji": "⚛️"}
            },
            "emoji": "🧪",
            "separate_message": False  # Group all chemistry in one message
        },
        "PHYSICS": {
            "condition": lambda name: '🧲' in name,
            "emoji": "🧲",
            "separate_message": True
        },
        "BIOLOGY": {
            "subcategories": {
                "ZOOLOGY": {"keywords": ["zoology"], "emoji": "🐾"},
                "BOTANY": {"keywords": ["botany"], "emoji": "🌿"}
            },
            "emoji": "🧬",
            "separate_message": False  # Group biology in one message
        },
        "OTHER": {
            "emoji": "📦",
            "separate_message": True
        }
    }

    # Generate links and categorize
    links = {}
    categorized_channels = {cat: [] for cat in categories}
    
    for channel in await db.get_all_channels():
        try:
            invite = await client.create_chat_invite_link(
                chat_id=channel['_id'],
                name=f"Link_{datetime.now().strftime('%m%d%H%M')}",
                expire_date=datetime.now() + expire_time if expire_time else None
            )
            
            links[channel['_id']] = {
                'link': invite.invite_link,
                'name': channel['name']
            }
            
            # Categorize channel
            channel_categorized = False
            
            # Check Yakeen first (special case)
            if 'yakeen' in channel['name'].lower():
                categorized_channels["YAKEEN"].append(channel)
                continue
                
            # Check other categories
            for cat_name, cat_data in categories.items():
                if cat_name == "YAKEEN":
                    continue
                    
                # Physics (emoji check)
                if cat_name == "PHYSICS" and '🧲' in channel['name']:
                    categorized_channels["PHYSICS"].append(channel)
                    channel_categorized = True
                    break
                    
                # Chemistry subcategories
                if cat_name == "CHEMISTRY":
                    for subcat, subdata in cat_data["subcategories"].items():
                        for kw in subdata["keywords"]:
                            if kw in channel['name'].lower():
                                categorized_channels["CHEMISTRY"].append(channel)
                                channel_categorized = True
                                break
                        if channel_categorized:
                            break
                    if channel_categorized:
                        break
                        
                # Biology subcategories
                if cat_name == "BIOLOGY":
                    for subcat, subdata in cat_data["subcategories"].items():
                        for kw in subdata["keywords"]:
                            if kw in channel['name'].lower():
                                categorized_channels["BIOLOGY"].append(channel)
                                channel_categorized = True
                                break
                        if channel_categorized:
                            break
                    if channel_categorized:
                        break
                        
            if not channel_categorized:
                categorized_channels["OTHER"].append(channel)
                
        except Exception as e:
            print(f"Error in {channel['name']}: {str(e)}")

    # Send processing completion
    await processing_msg.edit("✅ <b>Channel categorization completed!</b>")
    await asyncio.sleep(1)

    # Send categorized messages
    for cat_name in ["YAKEEN", "CHEMISTRY", "PHYSICS", "BIOLOGY", "OTHER"]:
        if not categorized_channels[cat_name]:
            continue
            
        cat_data = categories[cat_name]
        message_text = build_category_message(cat_name, cat_data, categorized_channels[cat_name], time_suffix)
        
        # Send message with revoke button only for this category
        buttons = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                f"🔴 Revoke {cat_name} Links", 
                callback_data=f"revoke_cat:{cat_name.lower()}")
        ]]) if categorized_channels[cat_name] else None
        
        await message.reply(
            message_text,
            reply_markup=buttons,
            disable_web_page_preview=True
        )
        await asyncio.sleep(0.5)  # Prevent flooding

    # Store all links for global revocation
    client.generated_links = links
    if expire_time:
        asyncio.create_task(auto_revoke_links(client, links, expire_time))

def build_category_message(cat_name, cat_data, channels, time_suffix):
    """Builds formatted message for a category"""
    if cat_name == "CHEMISTRY":
        return build_chemistry_message(channels, time_suffix)
    elif cat_name == "BIOLOGY":
        return build_biology_message(channels, time_suffix)
    else:
        header = (
            f"╭ ✨ ❰ {cat_data['emoji']} {cat_name} ❱\n"
            f"┃ {time_suffix}\n┃\n"
        )
        body = "\n".join(f"┣➥ {ch['name']}" for ch in channels)
        footer = "\n╰〰〰〰〰〰〰〰〰〰"
        return header + body + footer

def build_chemistry_message(channels, time_suffix):
    """Special formatting for chemistry with subcategories"""
    # Group chemistry channels by subcategory
    subcats = {
        "PHYSICAL CHEMISTRY": [],
        "ORGANIC CHEMISTRY": [],
        "INORGANIC CHEMISTRY": []
    }
    
    for ch in channels:
        lower_name = ch['name'].lower()
        if any(kw in lower_name for kw in ["pc", "physical"]):
            subcats["PHYSICAL CHEMISTRY"].append(ch)
        elif any(kw in lower_name for kw in ["oc", "organic"]):
            subcats["ORGANIC CHEMISTRY"].append(ch)
        elif any(kw in lower_name for kw in ["ioc", "inorganic"]):
            subcats["INORGANIC CHEMISTRY"].append(ch)
    
    message = (
        f"╭ ✨ ❰ 🧪 CHEMISTRY ❱\n"
        f"┃ {time_suffix}\n┃\n"
    )
    
    for subcat, ch_list in subcats.items():
        if not ch_list:
            continue
        emoji = "⚗️" if "PHYSICAL" in subcat else "🧪" if "ORGANIC" in subcat else "⚛️"
        message += f"┃\n┣❤️‍🔥 {emoji} {subcat}\n"
        message += "\n".join(f"┣➥ {ch['name']}" for ch in ch_list)
    
    message += "\n╰〰〰〰〰〰〰〰〰〰"
    return message

def build_biology_message(channels, time_suffix):
    """Special formatting for biology with subcategories"""
    # Similar structure to chemistry but for biology
    subcats = {
        "ZOOLOGY": [],
        "BOTANY": []
    }
    
    for ch in channels:
        lower_name = ch['name'].lower()
        if "zoology" in lower_name:
            subcats["ZOOLOGY"].append(ch)
        elif "botany" in lower_name:
            subcats["BOTANY"].append(ch)
    
    message = (
        f"**╭ ✨ ❰ 🧬 BIOLOGY ❱**\n"
        f"**┃ {time_suffix}**\n┃\n"
    )
    
    for subcat, ch_list in subcats.items():
        if not ch_list:
            continue
        emoji = "🐾" if subcat == "ZOOLOGY" else "🌿"
        message += f"**┃\n┣❤️‍🔥 {emoji} {subcat}**\n"
        message += "\n".join(f"┣➥ {ch['name']}" for ch in ch_list)
    
    message += "\n**╰〰〰〰〰〰〰〰〰〰**"
    return message
