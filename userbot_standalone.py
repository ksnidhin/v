import os
import asyncio
import zipfile
import shutil
import time
from pyrogram import Client, filters
from pyrogram.types import InputMediaPhoto, Message
from pyrogram.errors import FloodWait

from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

# ==========================================
# CONFIGURATION
# ==========================================
# These will be loaded from the .env file
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_NAME = "violet_standalone_userbot"

app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

# Track active tasks so they can be cancelled per chat
active_downloads = set()

# ==========================================
# CONSTANTS & ASSETS
# ==========================================
# You can change this to any GIF URL or a local file path
START_GIF_URL = "https://media.tenor.com/n14aVlDOPv8AAAAC/anime-hello.gif"

MENU_TEXT = """
**🌟 𝓥𝓲𝓸𝓵𝓮𝓽 𝓤𝓼𝓮𝓻𝓫𝓸𝓽 🌟**

✨ *Welcome! I am operating entirely as a userbot.* ✨

Since I am a user account, I don't use buttons. 
Simply type or copy-paste the commands below:

📸 **`/pic [username/id]`**
 ↳ *Download all profile pictures. Delivered in real-time as albums.*

🔢 **`/count [username/id]`**
 ↳ *Check how many profile pictures a user has.*

🆕 **`/latest [username/id]`**
 ↳ *Fetch only the current/latest profile picture.*

🗂️ **`/zip [username/id]`**
 ↳ *Download all profile pictures and receive them as a ZIP archive.*

❌ **`/cancel`**
 ↳ *Stop any ongoing download in this chat instantly.*

*(Pro tip: You can also reply to someone's message with these commands!)*
"""

# ==========================================
# UTILS
# ==========================================
def get_target(message: Message):
    """Extracts the target user from the command arguments or the replied message."""
    if len(message.command) > 1:
        return message.text.split(None, 1)[1].strip()
    elif message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id
    return None


async def send_album_with_retry(client: Client, chat_id: int, file_paths: list):
    """Sends a media group and properly handles FloodWait limits."""
    media = [InputMediaPhoto(fp) for fp in file_paths]
    while True:
        try:
            await client.send_media_group(chat_id=chat_id, media=media)
            break
        except FloodWait as e:
            # Pyrogram 2.x e.value holds the sleep time
            sleep_time = e.value + 0.5
            await asyncio.sleep(sleep_time)
        except Exception as e:
            print(f"Error sending album: {e}")
            break

# ==========================================
# COMMAND HANDLERS
# ==========================================

@app.on_message(filters.command(["start", "help"], prefixes=["/", ".", "!"]))
async def start_cmd(client: Client, message: Message):
    print(f"➡️ Received command: {message.text} in chat {message.chat.id}")
    try:
        await message.reply_animation(
            animation=START_GIF_URL,
            caption=MENU_TEXT,
            quote=True
        )
    except Exception as e:
        print(f"⚠️ Failed to send GIF: {e}. Sending text instead.")
        await message.reply_text(text=MENU_TEXT, quote=True)


@app.on_message(filters.command("cancel", prefixes=["/", ".", "!"]))
async def cancel_cmd(client: Client, message: Message):
    chat_id = message.chat.id
    if chat_id in active_downloads:
        active_downloads.discard(chat_id)
        await message.reply_text("🛑 **Cancellation requested! Stopping flow...**")
    else:
        await message.reply_text("⚠️ **No active downloads to cancel in this chat.**")


@app.on_message(filters.command("count", prefixes=["/", ".", "!"]))
async def count_cmd(client: Client, message: Message):
    target = get_target(message)
    if not target:
        await message.reply_text("⚠️ **Please provide a username/ID or reply to a user.**")
        return

    try:
        count = await client.get_chat_photos_count(target)
        await message.reply_text(f"🔢 **User has {count} profile photo(s).**")
    except Exception as e:
        await message.reply_text(f"❌ **Error resolving user:** `{e}`")


@app.on_message(filters.command("latest", prefixes=["/", ".", "!"]))
async def latest_cmd(client: Client, message: Message):
    target = get_target(message)
    if not target:
        await message.reply_text("⚠️ **Please provide a username/ID or reply to a user.**")
        return

    try:
        count = await client.get_chat_photos_count(target)
        if count == 0:
            await message.reply_text("⚠️ **User has no profile photos.**")
            return
            
        async for photo in client.get_chat_photos(target, limit=1):
            fp = await client.download_media(photo.file_id)
            await message.reply_photo(photo=fp, caption="🆕 **Latest Profile Photo**")
            os.remove(fp)
            
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{e}`")


@app.on_message(filters.command("pic", prefixes=["/", ".", "!"]))
async def pic_cmd(client: Client, message: Message):
    target = get_target(message)
    if not target:
        await message.reply_text("⚠️ **Please provide a username/ID or reply to a user.**")
        return

    chat_id = message.chat.id
    if chat_id in active_downloads:
        await message.reply_text("⚠️ **A download is already running! Use `/cancel` first.**")
        return

    active_downloads.add(chat_id)
    temp_dir = f"temp_albums_{chat_id}_{time.time()}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        total_photos = await client.get_chat_photos_count(target)
        if total_photos == 0:
            await message.reply_text("⚠️ **This user has no profile photos.**")
            active_downloads.discard(chat_id)
            return

        status_msg = await message.reply_text(f"📥 **Starting download of {total_photos} photos...**")
        
        sent_count = 0
        groups_sent_in_batch = 0
        photo_batch = []
        
        async for photo in client.get_chat_photos(target):
            # Check for cancellation
            if chat_id not in active_downloads:
                await status_msg.edit_text("❌ **Cancelled.**")
                return
                
            photo_batch.append(photo)
                
            # When we hit 10 photos, download and send them concurrently
            if len(photo_batch) == 10:
                tasks = [client.download_media(p.file_id, file_name=f"{temp_dir}/") for p in photo_batch]
                downloaded_paths = await asyncio.gather(*tasks)
                buffer = [fp for fp in downloaded_paths if fp]
                
                await send_album_with_retry(client, chat_id, buffer)
                sent_count += len(buffer)
                groups_sent_in_batch += 1
                photo_batch.clear()
                
                await status_msg.edit_text(f"📤 **Sent {sent_count} / {total_photos} photos...**")
                
                # 1.5s intra-batch stagger
                await asyncio.sleep(1.5)
                
                # If we've sent 3 groups (30 photos), initiate a 10s cooldown
                if groups_sent_in_batch >= 3:
                    groups_sent_in_batch = 0
                    await status_msg.edit_text(
                        f"⏳ **Cooldown for 10s to prevent spam limits...**\n"
                        f"*(Delivered: {sent_count} / {total_photos})*"
                    )
                    
                    # Interruptible 10s wait
                    for _ in range(10):
                        if chat_id not in active_downloads:
                            await status_msg.edit_text("❌ **Cancelled during cooldown.**")
                            return
                        await asyncio.sleep(1)
        
        # Send any remaining photos that didn't form a perfect 10
        if photo_batch and chat_id in active_downloads:
            tasks = [client.download_media(p.file_id, file_name=f"{temp_dir}/") for p in photo_batch]
            downloaded_paths = await asyncio.gather(*tasks)
            buffer = [fp for fp in downloaded_paths if fp]
            
            await send_album_with_retry(client, chat_id, buffer)
            sent_count += len(buffer)
            photo_batch.clear()
            
        await status_msg.edit_text(f"✅ **Done! All {sent_count} photos delivered successfully.**")
        
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{e}`")
    finally:
        active_downloads.discard(chat_id)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


@app.on_message(filters.command("zip", prefixes=["/", ".", "!"]))
async def zip_cmd(client: Client, message: Message):
    target = get_target(message)
    if not target:
        await message.reply_text("⚠️ **Please provide a username/ID or reply to a user.**")
        return

    chat_id = message.chat.id
    if chat_id in active_downloads:
        await message.reply_text("⚠️ **A download is already running! Use `/cancel` first.**")
        return

    active_downloads.add(chat_id)
    temp_dir = f"temp_zip_{chat_id}_{time.time()}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        total_photos = await client.get_chat_photos_count(target)
        if total_photos == 0:
            await message.reply_text("⚠️ **This user has no profile photos.**")
            active_downloads.discard(chat_id)
            return

        status_msg = await message.reply_text(f"📥 **Downloading {total_photos} photos for ZIP...**")
        
        downloaded = 0
        file_paths = []
        photo_batch = []
        
        async for photo in client.get_chat_photos(target):
            if chat_id not in active_downloads:
                await status_msg.edit_text("❌ **Cancelled.**")
                return
            
            photo_batch.append(photo)
            
            # Download in chunks of 20 for speed
            if len(photo_batch) == 20:
                tasks = [client.download_media(p.file_id, file_name=f"{temp_dir}/") for p in photo_batch]
                paths = await asyncio.gather(*tasks)
                file_paths.extend([fp for fp in paths if fp])
                downloaded += len(photo_batch)
                photo_batch.clear()
                
                await status_msg.edit_text(f"📥 **Downloading... {downloaded} / {total_photos}**")

        # Flush remaining
        if photo_batch and chat_id in active_downloads:
            tasks = [client.download_media(p.file_id, file_name=f"{temp_dir}/") for p in photo_batch]
            paths = await asyncio.gather(*tasks)
            file_paths.extend([fp for fp in paths if fp])
            downloaded += len(photo_batch)
            photo_batch.clear()
            await status_msg.edit_text(f"📥 **Downloading... {downloaded} / {total_photos}**")

        if chat_id not in active_downloads:
            return

        await status_msg.edit_text("🗜️ **Zipping files...**")
        zip_name = f"{temp_dir}/profile_photos.zip"
        
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            for file in file_paths:
                zipf.write(file, os.path.basename(file))
                
        if chat_id not in active_downloads:
            return

        await status_msg.edit_text("📤 **Uploading ZIP...**")
        await client.send_document(chat_id, document=zip_name)
        await status_msg.edit_text("✅ **Done! ZIP delivered.**")
        
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{e}`")
    finally:
        active_downloads.discard(chat_id)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    print("🌟 Violet Userbot is starting...")
    app.run()
