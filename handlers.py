from pyrogram import filters
from pyrogram.types import Message
from typing import Dict

class CommandHandlers:
    def __init__(self, bot_client, forwarder, user_client, config):
        self.bot_client = bot_client
        self.forwarder = forwarder
        self.user_client = user_client
        self.config = config
        
    async def handle_forward(self, _, message: Message):
        try:
            if message.from_user.id != self.config.YOUR_USER_ID:
                return await message.reply("🚨 Access denied")
            
            start_time = time.time()
            processing_msg = await message.reply("🔄 Processing forwarding request...")
            
            total_forwarded = 0
            for set_name, channel_config in self.config.CHANNEL_CONFIGS.items():
                count = await self.forwarder.forward_messages(set_name, channel_config)
                total_forwarded += count
            
            elapsed = time.time() - start_time
            response = (
                f"📊 **Forwarding Complete**\n\n"
                f"✅ Forwarded: {total_forwarded} messages\n"
                f"⏱️ Time taken: {elapsed:.2f} seconds\n\n"
            )
            
            for set_name, channel_config in self.config.CHANNEL_CONFIGS.items():
                last_id = await self.forwarder.db.load_state(set_name)
                current_id = await self.forwarder.get_last_message_id(channel_config["SOURCE"])
                
                response += (
                    f"🔹 **{set_name}**\n"
                    f"Last forwarded ID: `{last_id}`\n"
                    f"Current last ID: `{current_id}`\n\n"
                )
            
            await processing_msg.edit_text(response)
            
        except Exception as e:
            await message.reply(f"⚠️ Error during forwarding: {str(e)}")
    
    async def handle_channels(self, _, message: Message):
        try:
            if message.from_user.id != self.config.YOUR_USER_ID:
                return await message.reply("🚨 Access denied")
            
            response = "📚 **Configured Channels**\n\n"
            for set_name, config in self.config.CHANNEL_CONFIGS.items():
                try:
                    chat = await self.user_client.get_chat(config["SOURCE"])
                    source_name = chat.title
                except:
                    source_name = "Unknown"
                
                response += f"🔷 **{set_name}**\n"
                response += f"Source: {source_name} (`{config['SOURCE']}`)\n"
                response += "Destinations:\n"
                
                for subject, channel_id in config["DESTINATIONS"].items():
                    try:
                        dest_chat = await self.bot_client.get_chat(channel_id)
                        dest_name = dest_chat.title
                    except:
                        dest_name = "Unknown"
                    response += f"• {subject}: {dest_name} (`{channel_id}`)\n"
                
                response += "\n"
            
            await message.reply(response)
            
        except Exception as e:
            await message.reply(f"⚠️ Error listing channels: {str(e)}")
    
    def register_handlers(self):
        self.bot_client.on_message(filters.command("forward") & filters.private)(self.handle_forward)
        self.bot_client.on_message(filters.command("channels") & filters.private)(self.handle_channels)
