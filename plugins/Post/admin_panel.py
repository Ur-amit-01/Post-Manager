
from plugins.helper.db import db
from pyrogram import Client, filters
from pyrogram.types import Message
from config import *
import os
import asyncio
from datetime import datetime
import json

async def admins_only(_, __, message):
    if not message.from_user:
        return False
    return await db.is_admin(message.from_user.id)

admin_filter = filters.create(admins_only)

#========================================================================================        

@Client.on_message(filters.command("promote") & filters.user(ADMIN))
async def promote_user(client, message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply("Reply to a user or use: /promote user_id")
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        try:
            user_id = int(message.command[1])
        except:
            return await message.reply("Invalid user ID!")

    await db.add_admin(user_id)
    await message.reply(f"✅ Promoted user {user_id} to admin!")

@Client.on_message(filters.command("demote") & filters.user(ADMIN))
async def demote_user(client, message):
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply("Reply to a user or use: /demote user_id")
    
    if message.reply_to_message:
        user_id = message.reply_to_message.from_user.id
    else:
        try:
            user_id = int(message.command[1])
        except:
            return await message.reply("Invalid user ID!")

    await db.remove_admin(user_id)
    await message.reply(f"❌ Demoted user {user_id}")


@Client.on_message(filters.command("listadmins") & filters.user(ADMIN))
async def list_admins(client, message):
    """List all admins with details"""
    admins = await db.get_all_admins()
    if not admins:
        return await message.reply("No admins found!")
    
    text = "👑 **Admin List**\n\n"
    for admin in admins:
        try:
            user = await client.get_users(admin["_id"])
            text += f"• {user.mention} (`{user.id}`)\n"
            text += f"  ⏰ Added: `{admin.get('added_at', 'Unknown')}`\n"
            text += f"  🔍 Last Active: `{admin.get('last_active', 'Never')}`\n\n"
        except:
            text += f"• Unknown User (`{admin['_id']}`)\n\n"
    
    await message.reply(text)
    
# Dont touch above code
#========================================================================================


# Admin management commands (keep your existing promote/demote/listadmins)

@Client.on_message(filters.command("backup") & admin_filter)
async def manual_backup(client, message):
    """Create and send manual JSON backup"""
    try:
        progress_msg = await message.reply("🔄 **Creating database backup...**")
        
        # Create backup
        backup_file = await create_json_backup()
        if not backup_file:
            await progress_msg.edit_text("❌ Backup creation failed!")
            return

        # Compress the backup file
        compressed_file = f"{backup_file}.gz"
        compress_cmd = f"gzip -c {backup_file} > {compressed_file}"
        os.system(compress_cmd)
        
        if not os.path.exists(compressed_file):
            await progress_msg.edit_text("❌ Backup compression failed!")
            return

        # Send the backup
        await progress_msg.edit_text("📤 **Uploading backup file...**")
        
        try:
            # Send to owner
            await client.send_document(
                chat_id=ADMIN,
                document=compressed_file,
                caption=f"📦 Database Backup\n{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                progress=lambda c, t: progress_callback(c, t, progress_msg, "Owner")
            )
            
            # Send to log channel
            await client.send_document(
                chat_id=LOG_CHANNEL,
                document=compressed_file,
                caption="🔐 Database Backup",
                progress=lambda c, t: progress_callback(c, t, progress_msg, "Log Channel")
            )
            
            await progress_msg.edit_text("✅ **Backup completed and sent successfully!**")
            
        except Exception as send_error:
            await progress_msg.edit_text(f"❌ Failed to send backup: {str(send_error)}")
            
        finally:
            # Clean up files
            for file_path in [backup_file, compressed_file]:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    
    except Exception as e:
        error_msg = f"Backup process error: {str(e)}"
        print(error_msg)
        await message.reply(error_msg)

async def create_json_backup():
    """Create a JSON backup of the database"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        backup_file = f"{backup_dir}/backup_{timestamp}.json"
        
        # Get all collections
        collections = await db.db.list_collection_names()
        backup_data = {}
        
        for collection_name in collections:
            collection = db.db[collection_name]
            backup_data[collection_name] = [
                doc async for doc in collection.find({})
            ]
        
        # Save to JSON file
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=4, default=str)
        
        return backup_file
        
    except Exception as e:
        error_msg = f"Backup creation error: {str(e)}"
        print(error_msg)
        return None

@Client.on_message(filters.command("restore") & filters.user(ADMIN))
async def restore_database(client, message):
    """Restore database from JSON backup"""
    if not message.reply_to_message or not message.reply_to_message.document:
        return await message.reply("⚠️ Please reply to a backup file to restore")
    
    # Check file extension
    if not message.reply_to_message.document.file_name.endswith(('.json', '.gz')):
        return await message.reply("❌ Invalid backup file format. Please send a .json or .json.gz file")
    
    msg = await message.reply("⬇️ **Downloading backup file...**")
    
    try:
        # Download the file
        backup_path = await message.reply_to_message.download()
        
        # Decompress if it's a gzip file
        if backup_path.endswith('.gz'):
            decompressed_path = backup_path.replace('.gz', '')
            os.system(f"gzip -d {backup_path}")
            backup_path = decompressed_path
        
        if not os.path.exists(backup_path):
            await msg.edit_text("❌ Failed to prepare backup file for restore")
            return
            
        await msg.edit_text("🔄 **Restoring database...**")
        
        # Read the backup file
        with open(backup_path, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        # Restore each collection
        for collection_name, documents in backup_data.items():
            collection = db.db[collection_name]
            
            # Clear existing data
            await collection.delete_many({})
            
            # Insert documents in batches
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                try:
                    await collection.insert_many(batch)
                except Exception as e:
                    print(f"Error restoring {collection_name} batch {i}: {str(e)}")
                    continue
        
        # Send success message
        await msg.edit_text("✅ **Database restored successfully!**")
        await client.send_message(
            LOG_CHANNEL,
            f"♻️ Database was restored by {message.from_user.mention}"
        )
        
    except json.JSONDecodeError:
        await msg.edit_text("❌ Invalid backup file format")
    except Exception as e:
        await msg.edit_text(f"❌ Restore failed: {str(e)}")
    finally:
        if os.path.exists(backup_path):
            os.remove(backup_path)

async def progress_callback(current, total, message, target):
    """Update progress during file upload"""
    percent = (current / total) * 100
    try:
        await message.edit_text(
            f"📤 Uploading to {target}: {human_readable_size(current)}/{human_readable_size(total)} "
            f"({percent:.1f}%)"
        )
    except:
        pass

def human_readable_size(size):
    """Convert bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size < 1024.0:
            return f"{size:.1f} {unit}"
        size /= 1024.0
    return f"{size:.1f} TB"

async def auto_backup_task(client):
    """Automatic weekly backup task"""
    while True:
        try:
            # Check if it's Monday (weekly backup)
            if datetime.now().weekday() == 0:
                backup_file = await create_json_backup()
                if backup_file:
                    # Compress the backup
                    compressed_file = f"{backup_file}.gz"
                    os.system(f"gzip -c {backup_file} > {compressed_file}")
                    
                    if os.path.exists(compressed_file):
                        # Send to owner
                        await client.send_document(
                            chat_id=ADMIN,
                            document=compressed_file,
                            caption="📅 Weekly Auto Backup"
                        )
                        
                        # Send to log channel
                        await client.send_document(
                            chat_id=LOG_CHANNEL,
                            document=compressed_file,
                            caption="📅 Weekly Auto Backup"
                        )
                    
                    # Clean up files
                    for f in [backup_file, compressed_file]:
                        if os.path.exists(f):
                            os.remove(f)
            
            # Sleep for 1 hour and check again
            await asyncio.sleep(3600)
            
        except Exception as e:
            print(f"Auto backup error: {str(e)}")
            await asyncio.sleep(3600)  # Wait before retrying
