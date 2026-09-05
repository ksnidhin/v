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

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_NAME = "violet_standalone_userbot"

app = Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH)

active_downloads = set()

START_GIF_URL = "https://media.tenor.com/n14aVlDOPv8AAAAC/anime-hello.gif"

MENU_TEXT = """
**🌟 wassup gng 🌟**

✨ *Welcome! I am operating entirely as a userbot.* ✨

📸 **`/pic [username/id]`**
 ↳ *Download all profile pictures. Delivered progressively!*

🔢 **`/count [username/id]`**
 ↳ *Check how many profile pictures a user has.*

🆕 **`/latest [username/id]`**
 ↳ *Fetch only the current/latest profile picture.*

🗂️ **`/zip [username/id]`**
 ↳ *Download all profile pictures and receive them as a ZIP archive.*

❌ **`/cancel`**
 ↳ *Stop any ongoing download in this chat instantly.*
"""

def get_target(message: Message):
    if len(message.command) > 1:
        return message.text.split(None, 1)[1].strip()
    elif message.reply_to_message and message.reply_to_message.from_user:
        return message.reply_to_message.from_user.id
    return None

async def send_album_with_retry(client: Client, chat_id: int, file_paths: list):
    if not file_paths:
        return
        
    # If there's only 1 photo left, we must use send_photo because send_media_group requires 2+
    if len(file_paths) == 1:
        while True:
            try:
                await client.send_photo(chat_id=chat_id, photo=file_paths[0])
                break
            except FloodWait as e:
                await asyncio.sleep(e.value + 0.5)
            except Exception as e:
                print(f"Error sending single photo: {e}")
                break
        return

    media = [InputMediaPhoto(fp) for fp in file_paths]
    while True:
        try:
            await client.send_media_group(chat_id=chat_id, media=media)
            break
        except FloodWait as e:
            sleep_time = e.value + 0.5
            await asyncio.sleep(sleep_time)
        except Exception as e:
            print(f"Error sending album: {e}")
            break

# ==========================================
# ANTI-AD MODERATION MODULE
# ==========================================
# Runs in group -1 so it intercepts spam before other commands
@app.on_message(filters.group & ~filters.me, group=-1)
async def anti_ad_worker(client: Client, message: Message):
    # Only target messages that have inline keyboards (the primary signature of bot ads)
    if getattr(message, "reply_markup", None) is None:
        return
    if not hasattr(message.reply_markup, "inline_keyboard"):
        return

    text = (message.text or message.caption or "").lower()
    raw_text = message.text or message.caption or ""
    
    # Signature 1: Has Media
    has_media = bool(message.photo or message.animation or message.video or message.document)
    
    # Signature 2: Aggressive Ad Keywords
    ad_keywords = [
        "join channel", "get premium", "special announcement", 
        "massive update", "click the button", "discount",
        "crypto", "airdrop", "giveaway", "bonus", "investment",
        "join now", "subscribe", "limited time"
    ]
    has_ad_keyword = any(kw in text for kw in ad_keywords)
    
    # Signature 3: Heavy Emoji Usage
    ad_emojis = ["🚨", "🔥", "🚀", "💎", "🎁", "👇", "👉", "💯", "✅", "💸", "💰", "⚠️"]
    emoji_count = sum(1 for char in raw_text if char in ad_emojis)
    
    # If it has inline buttons AND matches typical ad formatting, strike it down!
    if has_media or has_ad_keyword or emoji_count >= 2:
        try:
            await message.delete()
            print(f"🗑️ Anti-Ad: Deleted promotional bot message in '{message.chat.title}'")
        except Exception:
            # Silently ignore if the userbot lacks admin/delete permissions in this specific group
            pass


# ==========================================
# BOT COMMANDS
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

        status_msg = await message.reply_text(f"📥 **Starting progressive delivery of {total_photos} photos...**")
        start_time = time.time()
        
        task_queue = asyncio.Queue()
        result_queue = asyncio.Queue()
        
        async def download_worker():
            while True:
                data = await task_queue.get()
                if data is None:
                    break
                photo, idx = data
                try:
                    if chat_id in active_downloads:
                        fp = await client.download_media(photo.file_id, file_name=f"{temp_dir}/{idx}.jpg")
                        if fp:
                            await result_queue.put((idx, fp))
                except Exception as e:
                    print(f"Download failed: {e}")
                finally:
                    task_queue.task_done()

        async def upload_consumer():
            buffer = []
            sent_count = 0
            groups_sent_in_batch = 0
            while True:
                item = await result_queue.get()
                if item is None:
                    if buffer and chat_id in active_downloads:
                        buffer.sort(key=lambda x: x[0])
                        await send_album_with_retry(client, chat_id, [x[1] for x in buffer])
                        sent_count += len(buffer)
                    break
                
                buffer.append(item)
                if len(buffer) == 10:
                    buffer.sort(key=lambda x: x[0])
                    files = [x[1] for x in buffer]
                    if chat_id in active_downloads:
                        await send_album_with_retry(client, chat_id, files)
                    
                    sent_count += 10
                    groups_sent_in_batch += 1
                    buffer.clear()
                    
                    if chat_id in active_downloads:
                        await status_msg.edit_text(f"📤 **Sent {sent_count} / {total_photos} photos...**")
                    
                    await asyncio.sleep(1.5)
                    
                    if groups_sent_in_batch >= 3:
                        groups_sent_in_batch = 0
                        if chat_id in active_downloads:
                            await status_msg.edit_text(f"⏳ **Cooldown for 10s...**\n*(Delivered: {sent_count} / {total_photos})*")
                        for _ in range(10):
                            if chat_id not in active_downloads:
                                return
                            await asyncio.sleep(1)

        NUM_WORKERS = 5
        workers = [asyncio.create_task(download_worker()) for _ in range(NUM_WORKERS)]
        consumer_task = asyncio.create_task(upload_consumer())
        
        idx = 0
        async for photo in client.get_chat_photos(target):
            if chat_id not in active_downloads:
                break
            await task_queue.put((photo, idx))
            idx += 1
            
        await task_queue.join()
        
        for _ in range(NUM_WORKERS):
            await task_queue.put(None)
            
        await result_queue.put(None)
        await consumer_task
        
        if chat_id in active_downloads:
            elapsed = round(time.time() - start_time, 2)
            await status_msg.edit_text(f"✅ **Done! Pipeline completed.**\n📸 Delivered: `{total_photos}` photos\n⏱️ Time taken: `{elapsed}s`")
        
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

        status_msg = await message.reply_text(f"📥 **Downloading {total_photos} photos for ZIP (Fast Concurrent)...**")
        start_time = time.time()
        
        task_queue = asyncio.Queue()
        file_paths = []
        
        async def zip_worker():
            while True:
                data = await task_queue.get()
                if data is None:
                    break
                photo, idx = data
                try:
                    if chat_id in active_downloads:
                        fp = await client.download_media(photo.file_id, file_name=f"{temp_dir}/{idx}.jpg")
                        if fp:
                            file_paths.append((idx, fp))
                            downloaded = len(file_paths)
                            if downloaded % 20 == 0 or downloaded == total_photos:
                                await status_msg.edit_text(f"📥 **Downloading... {downloaded} / {total_photos}**")
                except Exception as e:
                    print(f"Zip download failed: {e}")
                finally:
                    task_queue.task_done()
                    
        NUM_WORKERS = 8
        workers = [asyncio.create_task(zip_worker()) for _ in range(NUM_WORKERS)]
        
        idx = 0
        async for photo in client.get_chat_photos(target):
            if chat_id not in active_downloads:
                break
            await task_queue.put((photo, idx))
            idx += 1
            
        await task_queue.join()
        
        for _ in range(NUM_WORKERS):
            await task_queue.put(None)
            
        if chat_id not in active_downloads:
            return

        await status_msg.edit_text("🗜️ **Zipping files...**")
        zip_name = f"{temp_dir}/profile_photos.zip"
        
        file_paths.sort(key=lambda x: x[0])
        with zipfile.ZipFile(zip_name, 'w') as zipf:
            for _, file in file_paths:
                zipf.write(file, os.path.basename(file))
                
        if chat_id not in active_downloads:
            return

        await status_msg.edit_text("📤 **Uploading ZIP...**")
        await client.send_document(chat_id, document=zip_name)
        
        elapsed = round(time.time() - start_time, 2)
        await status_msg.edit_text(f"✅ **Done! ZIP delivered.**\n⏱️ Time taken: `{elapsed}s`")
        
    except Exception as e:
        await message.reply_text(f"❌ **Error:** `{e}`")
    finally:
        active_downloads.discard(chat_id)
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

if __name__ == "__main__":
    print("🌟 Violet Userbot is starting...")
    app.run()
