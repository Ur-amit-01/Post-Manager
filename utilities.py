from typing import Optional, Dict, Any

def format_response(title: str, data: Dict[str, Any]) -> str:
    """Format a response message with title and data"""
    message = f"📌 **{title}**\n\n"
    for key, value in data.items():
        message += f"• {key}: {value}\n"
    return message

async def get_chat_info(client, chat_id: int) -> Optional[Dict]:
    """Get basic chat information"""
    try:
        chat = await client.get_chat(chat_id)
        return {
            "title": chat.title,
            "id": chat.id,
            "type": str(chat.type)
        }
    except Exception:
        return None
