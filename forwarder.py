import asyncio
import time
from pyrogram import Client
from pyrogram.errors import RPCError
from plugins.Sorting import matcher
from typing import Dict, List

class MessageForwarder:
    def __init__(self, user_client: Client, bot_client: Client, db_manager):
        self.user_client = user_client
        self.bot_client = bot_client
        self.db = db_manager
        self.forwarding_active = False
    
    async def get_last_message_id(self, source_channel: int) -> int:
        try:
            async for message in self.user_client.get_chat_history(source_channel, limit=1):
                return message.id
            return 0
        except Exception as e:
            raise Exception(f"Error getting last message ID: {e}")
    
    async def get_new_messages(self, source_channel: int, last_forwarded_id: int) -> List:
        try:
            current_last_id = await self.get_last_message_id(source_channel)
            if last_forwarded_id >= current_last_id:
                return []
            
            all_messages = []
            async for message in self.user_client.get_chat_history(source_channel, limit=None):
                if message.id > last_forwarded_id:
                    all_messages.append(message)
                elif message.id <= last_forwarded_id:
                    break
            
            return sorted(all_messages, key=lambda m: m.id)
        except Exception as e:
            raise Exception(f"Error getting new messages: {e}")
    
    async def forward_messages(self, set_name: str, config: Dict) -> int:
        if self.forwarding_active:
            return 0
        
        self.forwarding_active = True
        forwarded_count = 0
        
        try:
            source_channel = config["SOURCE"]
            destinations = config["DESTINATIONS"]
            
            last_forwarded_id = await self.db.load_state(set_name)
            new_messages = await self.get_new_messages(source_channel, last_forwarded_id)
            
            if not new_messages:
                return 0
                
            for message in reversed(new_messages):
                try:
                    if message.service or (not message.text and not message.caption and not message.media):
                        continue
                    
                    text = message.text or message.caption or ""
                    subject = matcher.find_subject(text)
                    if not subject or subject not in destinations:
                        continue
                    
                    await self.bot_client.copy_message(
                        chat_id=destinations[subject],
                        from_chat_id=source_channel,
                        message_id=message.id
                    )
                    
                    await self.db.save_state(set_name, message.id)
                    forwarded_count += 1
                    await asyncio.sleep(0.1)
                    
                except RPCError as e:
                    print(f"Failed to forward message {message.id}: {e}")
                except Exception as e:
                    print(f"Error processing message {message.id}: {e}")

            return forwarded_count
            
        finally:
            self.forwarding_active = False
