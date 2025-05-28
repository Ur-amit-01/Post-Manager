

# Constants
USER_SESSION_STRING = "BQFP49AAiVku9pI3VZylmYZ-LJi7gUSLC7iM873LFaQtV7ozu83PEvi3N6ypHhtLaSfTDW9CC7YMK5W6jwgFuJ0ThauW7GnSgkDR7ERtmJtGptXcgA0SX3eWvRepBMWfD3jhGTOK5CveP7UYp5JHsMDMeBAkmwic0R9YWXkwU8jl-bOO8pWisoZkjqOX2-kVacxifW9ZRe52O8zmNB3dF_VTcRCGvp58ZfzaJLHT5lE4_T_TVuHqZK9YUzzstNAHN7yDVZZc49kpRTaGeMhCxjCuSyGDO7iP0NCqzd-DJDr3qe7DT-WfhfqgNMjqoC1BjB5Ksm7qxGK10rPzfqU6vz_5bZSEnQAAAAGVhUI_AA"
YOUR_USER_ID = 2031106491

# Channel configurations


import os
import re
from typing import Dict, List, Optional
from pymongo import MongoClient
from pyrogram import Client, filters
from pyrogram.types import Message
import PyPDF2
from io import BytesIO
from config import *

# Initialize MongoDB
mongo_client = MongoClient(DB_URL)
db = mongo_client.telegram_content_sorter

# Define source and destination channels
CHANNEL_SETS = {
    "Yakeen 1.0": {
        "source": -1002027394591,
        "destinations": {
            'Physics': -1002611033664,
            'Inorganic Chemistry': -1002530766847,
            'Organic Chemistry': -1002623306070,
            'Physical Chemistry': -1002533864126,
            'Botany': -1002537691102,
            'Zoology': -1002549422245
        }
    },
    "Yakeen 2.0": {
        "source": -1002027394591,
        "destinations": {
            'Physics': -1002611033664,
            'Inorganic Chemistry': -1002530766847,
            'Organic Chemistry': -1002623306070,
            'Physical Chemistry': -1002533864126,
            'Botany': -1002537691102,
            'Zoology': -1002549422245
        }
    },
    "Yakeen 3.0": {
        "source": -1002027394591,
        "destinations": {
            'Physics': -1002611033664,
            'Inorganic Chemistry': -1002530766847,
            'Organic Chemistry': -1002623306070,
            'Physical Chemistry': -1002533864126,
            'Botany': -1002537691102,
            'Zoology': -1002549422245
        }
    }
}


# Initialize Pyrogram client
app = Client("content_sorter_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

def extract_filters_from_pdf(pdf_path: str) -> Dict[str, Dict[str, List[str]]]:
    """
    Extract subject and topic filters from the provided PDF
    """
    filters = {
        "Physics": {},
        "Chemistry": {
            "Inorganic": {},
            "Organic": {},
            "Physical": {}
        },
        "Biology": {
            "Botany": {},
            "Zoology": {}
        }
    }
    
    # For demo purposes, we'll just outline the structure
    # In a real implementation, you would parse the PDF to extract actual filters
    
    # Example for Physics
    filters["Physics"]["Basic Maths & Calculus"] = [
        "Trigonometry", "Algebra", "Binomial", "AP", "GP", "Graphs", 
        "Logarithms", "Coordinate Geometry", "Differentiation"
    ]
    
    # Example for Chemistry
    filters["Chemistry"]["Inorganic"]["Classification of Elements"] = [
        "Introduction", "Electronic Configurations", "Screening Effect",
        "Atomic Radius", "Ionisation Enthalpy", "Electron Affinity"
    ]
    
    # Example for Biology
    filters["Biology"]["Botany"]["Cell - The Unit of Life"] = [
        "What is a Cell", "Discovery of the Cell", "Microscopy", "Cell Theory",
        "Overview of Cell", "Types of Cell Structure"
    ]
    
    return filters

def initialize_database():
    """
    Initialize database with filters and last message IDs
    """
    if not db.filters.find_one():
        # Extract filters from PDF (in a real app, you'd provide the PDF)
        filters = extract_filters_from_pdf("Planner.pdf")
        db.filters.insert_one({"filters": filters})
    
    # Initialize last message IDs if not present
    for channel_set in CHANNEL_SETS.values():
        source = channel_set["source"]
        if not db.last_message_ids.find_one({"source": source}):
            db.last_message_ids.insert_one({
                "source": source,
                "last_message_id": 0
            })

def get_subject_from_text(text: str) -> Optional[str]:
    """
    Determine the subject from message text
    """
    text_lower = text.lower()
    
    # Check Physics keywords
    physics_keywords = ["physics", "mechanics", "electromagnetism", "optics", "thermodynamics"]
    if any(keyword in text_lower for keyword in physics_keywords):
        return "Physics"
    
    # Check Chemistry keywords
    chem_keywords = ["chemistry", "organic", "inorganic", "physical chem", "reaction"]
    if any(keyword in text_lower for keyword in chem_keywords):
        return "Chemistry"
    
    # Check Biology keywords
    bio_keywords = ["biology", "botany", "zoology", "cell", "genetics"]
    if any(keyword in text_lower for keyword in bio_keywords):
        return "Biology"
    
    # Check Math keywords
    math_keywords = ["math", "mathematics", "algebra", "calculus", "geometry"]
    if any(keyword in text_lower for keyword in math_keywords):
        return "Mathematics"
    
    # Check English keywords
    english_keywords = ["english", "grammar", "literature", "writing"]
    if any(keyword in text_lower for keyword in english_keywords):
        return "English"
    
    return "General"

async def get_last_message_id(source_channel: str) -> int:
    """
    Get the last processed message ID for a source channel
    """
    record = db.last_message_ids.find_one({"source": source_channel})
    return record["last_message_id"] if record else 0

async def update_last_message_id(source_channel: str, message_id: int):
    """
    Update the last processed message ID for a source channel
    """
    db.last_message_ids.update_one(
        {"source": source_channel},
        {"$set": {"last_message_id": message_id}},
        upsert=True
    )

async def forward_messages_from_source(source_channel: str, set_name: str):
    """
    Process and forward messages from source channel
    """
    last_id = await get_last_message_id(source_channel)
    destinations = CHANNEL_SETS[set_name]["destinations"]
    
    # Get the latest message in the source channel
    latest_message = None
    async for message in app.get_chat_history(source_channel, limit=1):
        latest_message = message
    
    if not latest_message:
        return 0, "No messages found in source channel"
    
    new_last_id = latest_message.id
    forwarded_count = 0
    
    # Process messages in chronological order (from last_id to new_last_id)
    messages_to_process = []
    async for message in app.get_chat_history(source_channel):
        if message.id > last_id:
            messages_to_process.append(message)
        else:
            break
    
    # Process in reverse order to maintain chronology
    for message in reversed(messages_to_process):
        if not message.caption and not message.text:
            continue
            
        text = message.caption or message.text
        subject = get_subject_from_text(text)
        
        if subject not in destinations:
            subject = "General"
        
        try:
            # Forward the message to the appropriate channel
            await message.forward(destinations[subject])
            forwarded_count += 1
        except Exception as e:
            print(f"Failed to forward message {message.id}: {e}")
    
    # Update the last processed message ID
    if forwarded_count > 0:
        await update_last_message_id(source_channel, new_last_id)
    
    return forwarded_count, f"Forwarded {forwarded_count} messages from {source_channel}"

@app.on_message(filters.command("forward") & filters.private)
async def handle_forward_command(client: Client, message: Message):
    """
    Handle the /forward command in bot's DM
    """
    # Process each channel set
    results = []
    for set_name, channels in CHANNEL_SETS.items():
        count, msg = await forward_messages_from_source(channels["source"], set_name)
        results.append(f"{set_name}: {msg}")
    
    # Send confirmation
    await message.reply("\n".join(results))

@app.on_message(filters.command("start") & filters.private)
async def handle_start_command(client: Client, message: Message):
    """
    Handle the /start command
    """
    # Initialize database if not already done
    initialize_database()
    
    # Get the latest message ID for each source channel
    for set_name, channels in CHANNEL_SETS.items():
        source = channels["source"]
        last_id = 0
        async for msg in app.get_chat_history(source, limit=1):
            last_id = msg.id
        
        await update_last_message_id(source, last_id)
    
    await message.reply("Bot initialized successfully. Use /forward to process new messages.")

if __name__ == "__main__":
    initialize_database()
    app.run()                                                    
