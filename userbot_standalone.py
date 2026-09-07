import os
import asyncio
import zipfile
import shutil
import time
import re
from pyrogram import Client, filters, idle
from pyrogram.types import InputMediaPhoto, Message
from pyrogram.errors import FloodWait
from pyrogram.enums import MessageEntityType

try:
    from groq import AsyncGroq
except ImportError:
    AsyncGroq = None

from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO)

load_dotenv()

API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_NAME = "violet_standalone_userbot"
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

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
# ANAGRAM GAME AUTO-SOLVER (GROQ API)
# ==========================================
if AsyncGroq and GROQ_API_KEY:
    groq_client = AsyncGroq(api_key=GROQ_API_KEY)
else:
    groq_client = None

async def solve_scrambled_word(scrambled: str) -> str:
    if not groq_client:
        print("⚠️ Groq client not initialized. Install 'groq' package and set GROQ_API_KEY.")
        return ""
        
    try:
        completion = await groq_client.chat.completions.create(
            model="groq/compound-mini",
            messages=[
                {
                    "role": "system", 
                    "content": "You are a highly advanced anagram solver. The user will give you a scrambled sequence of letters. Respond with EXACTLY ONE unscrambled dictionary word in lowercase. Do not include any punctuation, spaces, quotes, or conversational text. Just the single word."
                },
                {"role": "user", "content": scrambled}
            ],
            temperature=0.0,
            max_tokens=15
        )
        return completion.choices[0].message.content.strip().lower()
    except Exception as e:
        print(f"⚠️ Groq API Error: {e}")
        return ""

@app.on_message(filters.group & filters.text & ~filters.me)
async def scramble_game_worker(client: Client, message: Message):
    text = message.text or ""
    
    # Check if it matches the specific bot game format
    if "Scrambled Word Challenge!" in text and "Word:" in text:
        match = re.search(r"Word:\s*([A-Za-z]+)", text)
        if match:
            scrambled_word = match.group(1)
            print(f"🧩 Detected scramble game! Word: {scrambled_word}")
            
            answer = await solve_scrambled_word(scrambled_word)
            if answer:
                # Some LLMs might accidentally include punctuation like "fairly."
                clean_answer = re.sub(r"[^a-z]", "", answer)
                print(f"💡 Groq Solved it: {clean_answer}. Sending to group!")
                
                # Send the answer directly into the chat
                await client.send_message(chat_id=message.chat.id, text=clean_answer)

# ==========================================
# ANTI-AD MODERATION MODULE
# ==========================================
def is_promotional_ad(message: Message) -> bool:
    if not message:
        return False
        
    is_bot_sender = False
    
    if message.from_user and message.from_user.is_bot:
        is_bot_sender = True
        
    if message.sender_chat and message.sender_chat.id != message.chat.id:
        is_bot_sender = True
        
    has_inline_keyboard = getattr(message, "reply_markup", None) is not None and hasattr(message.reply_markup, "inline_keyboard")
    
    if not (is_bot_sender or has_inline_keyboard):
        return False

    text = (message.text or message.caption or "").lower()
    raw_text = message.text or message.caption or ""
    
    has_media = bool(message.photo or message.animation or message.video or message.document)
    
    has_links = False
    ents = message.entities or message.caption_entities
    if ents:
        if any(e.type in [MessageEntityType.URL, MessageEntityType.TEXT_LINK] for e in ents):
            has_links = True

    ad_keywords = [
        "join channel", "get premium", "special announcement", 
        "massive update", "click the button", "discount",
        "crypto", "airdrop", "giveaway", "bonus", "investment",
        "join now", "subscribe", "limited time", "t.me/"
    ]
    has_ad_keyword = any(kw in text for kw in ad_keywords)
    
    ad_emojis = ["🚨", "🔥", "🚀", "💎", "🎁", "👇", "👉", "💯", "✅", "💸", "💰", "⚠️"]
    emoji_count = sum(1 for char in raw_text if char in ad_emojis)
    
    if has_inline_keyboard or has_links or has_media:
        if has_ad_keyword or emoji_count >= 2:
            return True
            
    return False

@app.on_message(filters.group & ~filters.me, group=-1)
async def anti_ad_worker(client: Client, message: Message):
    if is_promotional_ad(message):
        try:
            await message.delete()
            print(f"🗑️ Anti-Ad (Live): Deleted promotional bot message in '{message.chat.title}'")
        except Exception:
            pass

async def hourly_scanner(client: Client):
    print("🕒 Hourly background scanner activated.")
    while True:
        await asyncio.sleep(3600)
        print("🕒 Hourly scanner waking up to check for missed spam...")
        try:
            async for dialog in client.get_dialogs():
                chat = dialog.chat
                if chat.type.name in ["GROUP", "SUPERGROUP"]:
                    try:
                        async for msg in client.get_chat_history(chat.id, limit=100):
                            if is_promotional_ad(msg):
                                try:
                                    await msg.delete()
                                    print(f"🗑️ Anti-Ad (Scanner): Deleted missed ad in '{chat.title}'")
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"⚠️ Scanner error: {e}")

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

async def main():
    async with app:
        print("🌟 Violet Userbot connected.")
        asyncio.create_task(hourly_scanner(app))
        print("🌟 Hourly scanner is active.")
        await idle()

if __name__ == "__main__":
    print("🌟 Violet Userbot is starting...")
    app.run(main())
