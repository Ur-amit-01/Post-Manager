import os
import re
import asyncio
from typing import Dict, Set, Optional
from pyrogram import Client, filters, enums
from pyrogram.types import Message
from config import *
from plugins.Chapters import CHAPTER_DATA
from fuzzywuzzy import fuzz, process

# Channel IDs
SOURCE_CHANNEL = -1002027394591  # Main channel to monitor
DESTINATION_CHANNELS = {
    'Physics': -1002611033664,
    'Inorganic Chemistry': -1002530766847,
    'Organic Chemistry': -1002623306070,
    'Physical Chemistry': -1002533864126,
    'Botany': -1002537691102,
    'Zoology': -1002549422245
}

# Track forwarded messages for confirmation
forwarded_messages: Dict[int, Set[int]] = {channel: set() for channel in DESTINATION_CHANNELS.values()}

class ContentMatcher:
    def __init__(self):
        self.chapter_map = self._build_chapter_map()
        self.min_word_length = 4
        self.min_match_threshold = 2
        self.fuzzy_threshold = 75
        
    def _build_chapter_map(self) -> Dict[str, str]:
        """Create a mapping of all chapter keywords to subjects"""
        chapter_map = {}
        for subject, chapters in CHAPTER_DATA.items():
            for chapter in chapters:
                words = self._extract_keywords(chapter)
                for word in words:
                    chapter_map[word] = subject
        return chapter_map
        
    def _extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text"""
        words = set(re.findall(r'\w{'+str(self.min_word_length)+r',}', text.lower()))
        return words
        
    def find_subject(self, text: str) -> Optional[str]:
        """Find the best matching subject using multiple matching strategies"""
        text_lower = text.lower()
        text_words = self._extract_keywords(text_lower)
        
        # Strategy 1: Exact multi-word matching
        for subject, chapters in CHAPTER_DATA.items():
            for chapter in chapters:
                if len(chapter.split()) > 1 and chapter.lower() in text_lower:
                    return subject
        
        # Strategy 2: Multiple keyword matching
        subject_scores = {}
        for word in text_words:
            if word in self.chapter_map:
                subject = self.chapter_map[word]
                subject_scores[subject] = subject_scores.get(subject, 0) + 1
                
        if subject_scores:
            best_subject = max(subject_scores.items(), key=lambda x: x[1])[0]
            if subject_scores[best_subject] >= self.min_match_threshold:
                return best_subject
                
        # Strategy 3: Fuzzy matching as fallback
        all_chapters = []
        for subject, chapters in CHAPTER_DATA.items():
            all_chapters.extend((chap, subject) for chap in chapters)
            
        best_match = process.extractOne(
            text_lower, 
            [chap[0] for chap in all_chapters], 
            scorer=fuzz.token_set_ratio
        )
        
        if best_match and best_match[1] >= self.fuzzy_threshold:
            for chap, subject in all_chapters:
                if chap == best_match[0]:
                    return subject
                    
        return None

matcher = ContentMatcher()

async def send_confirmation(client: Client, channel_id: int, count: int):
    """Send confirmation message to destination channel"""
    await client.send_message(
        channel_id,
        f"✅ {count} messages have been automatically sorted to this channel today.",
        parse_mode=enums.ParseMode.MARKDOWN
    )
    # Clear the tracking for this channel
    forwarded_messages[channel_id].clear()

@Client.on_message(filters.chat(SOURCE_CHANNEL))
async def sort_content(client: Client, message: Message):
    # Get message text (including captions for media)
    text = message.text or message.caption or ""
    
    # Find matching subject using advanced matcher
    subject = matcher.find_subject(text)
    
    if subject:
        dest_channel = DESTINATION_CHANNELS.get(subject)
        if dest_channel:
            try:
                # Copy the message while preserving all formatting
                if message.text:
                    sent_msg = await client.send_message(
                        dest_channel,
                        text=message.text,
                        entities=message.entities
                    )
                elif message.photo:
                    sent_msg = await client.send_photo(
                        dest_channel,
                        photo=message.photo.file_id,
                        caption=message.caption,
                        caption_entities=message.caption_entities
                    )
                elif message.document:
                    sent_msg = await client.send_document(
                        dest_channel,
                        document=message.document.file_id,
                        caption=message.caption,
                        caption_entities=message.caption_entities
                    )
                elif message.video:
                    sent_msg = await client.send_video(
                        dest_channel,
                        video=message.video.file_id,
                        caption=message.caption,
                        caption_entities=message.caption_entities
                    )
                
                # Track forwarded message
                forwarded_messages[dest_channel].add(message.id)
                
                print(f"Copied message {message.id} to {subject} channel")
                
                # Schedule confirmation message if this is the first forward today
                if len(forwarded_messages[dest_channel]) == 1:
                    asyncio.create_task(
                        send_confirmation(client, dest_channel, 1)
                    )
                
            except Exception as e:
                print(f"Error copying message {message.id}: {str(e)}")
        else:
            print(f"No destination channel for subject: {subject}")
    else:
        print(f"No matching subject found for message {message.id}")

# Scheduled task to send daily summaries
async def daily_summary(client: Client):
    while True:
        await asyncio.sleep(24 * 60 * 60)  # 24 hours
        
        for channel_id, msg_ids in forwarded_messages.items():
            if msg_ids:
                count = len(msg_ids)
                await send_confirmation(client, channel_id, count)

