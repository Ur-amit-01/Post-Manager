from pyrogram import Client, filters
from pyrogram.types import Message
from plugins.Fsub import auth_check


@Client.on_message(filters.command("id"))
@auth_check
async def id_command(client: Client, message: Message):
    """
    Handler for the /id command.
    Sends the chat ID of the current chat or user.
    """
    # Determine the chat title or user's full name
    if message.chat.title:
        chat_title = message.chat.title
    else:
        chat_title = message.from_user.full_name

    # Prepare the response text
    id_text = f"**Chat ID of** {chat_title} **is**\n`{message.chat.id}`"

    # Send the response
    await client.send_message(
        chat_id=message.chat.id,
        text=id_text,
        reply_to_message_id=message.id,
    )
