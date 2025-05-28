import asyncio
import logging
from pyrogram import Client
from pyrogram.types import Message
from pyrogram.errors import RPCError
from typing import Dict, List
from config import CHANNEL_CONFIGS
from database import Database
from models import ForwarderState

logger = logging.getLogger(__name__)

class MessageForwarder:
    def __init__(self, user_client: Client, bot_client: Client, db: Database):
        self.user_client = user_client
        self.bot_client = bot_client
        self.db = db
        self.state = ForwarderState()

    async def get_last_message_id(self, source_channel: int) -> int:
        """Get the latest message ID from a channel"""
        async for message in self.user_client.get_chat_history(source_channel, limit=1):
            return message.id
        return 0

    async def get_new_messages(self, source_channel: int, last_forwarded_id: int) -> List[Message]:
        """Get messages newer than last_forwarded_id"""
        messages = []
        current_last_id = await self.get_last_message_id(source_channel)
        
        if last_forwarded_id >= current_last_id:
            logger.info(f"No new messages (last: {last_forwarded_id}, current: {current_last_id})")
            return []
        
        logger.info(f"Fetching messages between {last_forwarded_id} and {current_last_id}")
        
        async for message in self.user_client.get_chat_history(source_channel, limit=None):
            if message.id > last_forwarded_id:
                messages.append(message)
            else:
                break
        
        return sorted(messages, key=lambda m: m.id)

    async def forward_messages(self, set_name: str) -> int:
        """Process new messages for forwarding"""
        if self.state.is_forwarding:
            logger.warning("Forwarding already in progress")
            return 0
        
        self.state.start_forwarding()
        forwarded_count = 0
        
        try:
            config = CHANNEL_CONFIGS[set_name]
            last_id = await self.db.get_state(set_name)
            new_messages = await self.get_new_messages(config["SOURCE"], last_id)
            
            if not new_messages:
                return 0
                
            for message in reversed(new_messages):
                try:
                    if message.service or (not message.text and not message.caption and not message.media):
                        continue
                    
                    # Forwarding logic here
                    # ...
                    
                    await self.db.save_state(set_name, message.id)
                    forwarded_count += 1
                    await asyncio.sleep(0.1)
                    
                except RPCError as e:
                    logger.error(f"Failed to forward message {message.id}: {e}")
            
            return forwarded_count
            
        finally:
            self.state.stop_forwarding()
