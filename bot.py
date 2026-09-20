# bot.py
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import time
from datetime import datetime, timedelta
from pyrogram import Client, filters
from pyrogram.enums import ChatType, ChatMemberStatus
from pyrogram.types import (
    InlineQueryResultArticle, InlineQueryResultPhoto,
    InputTextMessageContent, InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import (
    API_ID, API_HASH, BOT_TOKEN, BOT_NAME, OWNER_ID, MAIN_GROUP_ID,
    UPDATE_CHANNEL_USERNAME, UPDATE_CHANNEL_ID, BOT_VERSION, TIMEZONE,
    STORAGE_CHANNEL_ID,
)
from data_manager import (
    load_data, save_data, user_data, normal_characters, mythical_characters,
    active_challenges, message_count, pending_trades, GBANNED, TEMP_BANNED,
    ADMINS, bot_groups, save_bot_groups, banned_players_info,
    get_banned_player_info, check_temp_bans, get_player,
    get_world_boss_active,
)
from utils import check_cooldown, parse_amount, get_xp_needed, get_rank
from models import Player

# ==================== CORE MODULES ====================
from commands import register_commands
from games import register_games
from pvp import register_pvp, start_world_boss, end_world_boss
from shop import register_shop
from giveaway import register_giveaway
from admin import register_admin
from callbacks import register_callbacks

# ==================== OPTIONAL NEW MODULES ====================
try:
    from haki_commands import register_haki
    HAKI_AVAILABLE = True
except ImportError:
    HAKI_AVAILABLE = False
    print("[bot] haki_commands.py not found — skipping")

try:
    from crew import register_crew, reload_crews
    CREW_AVAILABLE = True
except ImportError:
    CREW_AVAILABLE = False
    print("[bot] crew.py not found — skipping")

try:
    from inventory import register_inventory
    INVENTORY_AVAILABLE = True
except ImportError:
    INVENTORY_AVAILABLE = False
    print("[bot] inventory.py not found — skipping")

try:
    from update_notifier import notify_startup
    NOTIFIER_AVAILABLE = True
except ImportError:
    NOTIFIER_AVAILABLE = False
    print("[bot] update_notifier.py not found — skipping")


# ==================== INIT BOT ====================
app = Client("grandline_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# Register handlers
register_commands(app)
register_games(app)
register_pvp(app)
register_shop(app)
register_giveaway(app)
register_admin(app)
register_callbacks(app)

if HAKI_AVAILABLE:
    register_haki(app)
if CREW_AVAILABLE:
    register_crew(app)
if INVENTORY_AVAILABLE:
    register_inventory(app)


# ==================== AUTO NAME UPDATE ====================
_last_name_save = {}


@app.on_message(filters.all, group=-3)
async def auto_update_name(client, message):
    try:
        u = message.from_user
        if not u or u.is_bot:
            message.continue_propagation()
            return

        p = get_player(u.id, u)
        now = time.time()

        last = _last_name_save.get(u.id, 0)
        if now - last > 30:
            save_data()
            _last_name_save[u.id] = now
    except Exception:
        pass

    message.continue_propagation()


# ==================== FILE ID HELPERS ====================
@app.on_message(filters.photo & filters.private, group=1)
async def get_file_id(client, message):
    try:
        file_id = message.photo.file_id
        await message.reply(
            f"**File ID (PHOTO)**\n\n"
            f"**File ID:**\n<code>{file_id}</code>\n\n"
            f"**Info:**\n"
            f"Size: {message.photo.width}x{message.photo.height}\n"
            f"Bytes: {message.photo.file_size}\n\n"
            f"Use with `send_photo` / `reply_photo`.",
            quote=True,
        )
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@app.on_message(filters.document & filters.private, group=1)
async def get_document_file_id(client, message):
    try:
        file_id = message.document.file_id
        await message.reply(
            f"**File ID (DOCUMENT)**\n\n"
            f"**File ID:**\n<code>{file_id}</code>\n\n"
            f"Name: {message.document.file_name}\n"
            f"Bytes: {message.document.file_size}\n\n"
            f"Use with `send_document` / `reply_document`.",
            quote=True,
        )
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


@app.on_message(filters.animation & filters.private, group=1)
async def get_animation_file_id(client, message):
    try:
        file_id = message.animation.file_id
        await message.reply(
            f"**File ID (ANIMATION)**\n\n"
            f"**File ID:**\n<code>{file_id}</code>\n\n"
            f"Name: {message.animation.file_name}\n"
            f"Bytes: {message.animation.file_size}\n"
            f"Duration: {message.animation.duration}s\n\n"
            f"Use with `send_animation` / `reply_animation`.",
            quote=True,
        )
    except Exception as e:
        await message.reply(f"❌ Error: {e}")


# ==================== INLINE QUERY ====================
@app.on_inline_query()
async def inline_character_search(client, inline_query):
    from data_manager import get_player as _get_player

    query = (inline_query.query or "").strip()

    # Player-specific mode
    if query.startswith("character."):
        rest = query[len("character."):]
        parts = rest.split(" ", 1)
        try:
            player_id = int(parts[0])
        except (ValueError, IndexError):
            await inline_query.answer([], cache_time=5)
            return
        search_term = parts[1] if len(parts) > 1 else ""

        player = _get_player(player_id)
        if not player.captured_chars:
            await inline_query.answer([InlineQueryResultArticle(
                id="no_chars",
                title=f"character.{player_id}",
                description="No characters captured yet",
                input_message_content=InputTextMessageContent(
                    f"**{player.name or player_id} has no captured characters!**"
                ),
            )], cache_time=5)
            return

        matches = []
        for char in player.captured_chars:
            name = char.get("name", "")
            if not search_term or search_term.lower() in name.lower():
                matches.append(char)
        if not matches:
            await inline_query.answer([InlineQueryResultArticle(
                id="no_match",
                title=f"character.{player_id}",
                description=f"No '{search_term}' found",
                input_message_content=InputTextMessageContent(
                    f"**No '{search_term}' found in collection!**"
                ),
            )], cache_time=5)
            return

        results = []
        seen = set()
        for char in matches[:50]:
            name = char.get("name", "Unknown")
            if name in seen:
                continue
            seen.add(name)
            count = sum(1 for c in player.captured_chars if c.get("name") == name)
            img = char.get("image")
            rarity = char.get("rarity", "NORMAL")
            emoji = "👹" if rarity == "MYTHICAL" else "💠"
            text = (
                f"{emoji} **{name}**\n"
                f"(RARITY: {rarity})\n\n"
                f"Owner: {player.name or player_id}\n"
                f"Character ID: {char.get('id')}\n"
                f"Captured: {count}x\n\n"
                f"@Grand_Line_Sentinel_bot"
            )
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton(
                    f"Challenge {name}",
                    switch_inline_query_current_chat=f"/challenge {name}"
                )
            ]])
            if isinstance(img, str) and img.startswith(("http://", "https://")):
                results.append(InlineQueryResultPhoto(
                    id=f"p_{player_id}_{name}",
                    photo_url=img,
                    thumb_url=img,
                    title=name,
                    description=f"Captured {count}x",
                    caption=text,
                    reply_markup=kb,
                ))
            else:
                results.append(InlineQueryResultArticle(
                    id=f"p_{player_id}_{name}",
                    title=f"{emoji} {name}",
                    description=f"Captured {count}x",
                    input_message_content=InputTextMessageContent(text),
                    reply_markup=kb,
                ))
        await inline_query.answer(results, cache_time=5)
        return

    # Global mode
    all_chars = [{"char": c, "type": "NORMAL"} for c in normal_characters]
    all_chars += [{"char": c, "type": "MYTHICAL"} for c in mythical_characters]
    if query:
        all_chars = [
            x for x in all_chars
            if query.lower() in x["char"].get("name", "").lower()
        ]

    results = []
    for item in all_chars[:50]:
        char = item["char"]
        ctype = item["type"]
        name = char.get("name", "Unknown")
        img = char.get("image")
        cid = char.get("id")

        total = 0
        capturers = {}
        for p in user_data.values():
            for c in p.captured_chars:
                if c.get("name") == name:
                    total += 1
                    capturers.setdefault(p.user_id, {"name": p.name, "count": 0})
                    capturers[p.user_id]["count"] += 1
        top = sorted(capturers.values(), key=lambda x: x["count"], reverse=True)[:10]
        lines = [f"{i}. {c['name'] or 'User'} - {c['count']}x" for i, c in enumerate(top, 1)]
        cap_text = "\n".join(lines) if lines else "No captures yet."

        emoji = "👹" if ctype == "MYTHICAL" else "💠"
        text = (
            f"{emoji} **{name}**\n"
            f"(RARITY: {ctype})\n"
            f"Character ID: {cid}\n\n"
            f"GLOBAL CAPTURES: {total}\n\n"
            f"TOP CAPTURERS:\n{cap_text}\n\n"
            f"@Grand_Line_Sentinel_bot"
        )
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                f"Challenge {name}",
                switch_inline_query_current_chat=f"/challenge {name}"
            )
        ]])
        if isinstance(img, str) and img.startswith(("http://", "https://")):
            results.append(InlineQueryResultPhoto(
                id=f"g_{ctype}_{cid}",
                photo_url=img,
                thumb_url=img,
                title=f"{emoji} {name}",
                description=f"Global: {total} captures",
                caption=text,
                reply_markup=kb,
            ))
        else:
            results.append(InlineQueryResultArticle(
                id=f"g_{ctype}_{cid}",
                title=f"{emoji} {name} ({ctype})",
                description=f"Global: {total} captures",
                input_message_content=InputTextMessageContent(text),
                reply_markup=kb,
            ))

    if not results:
        results.append(InlineQueryResultArticle(
            id="no_chars",
            title="No Characters Found",
            description=f"Search: '{query}'",
            input_message_content=InputTextMessageContent(
                f"**No characters found**\n\n"
                f"Normal: {len(normal_characters)}\n"
                f"Mythical: {len(mythical_characters)}"
            ),
        ))
    await inline_query.answer(results, cache_time=5)


# ==================== SCHEDULERS ====================
async def world_boss_scheduler():
    while True:
        try:
            now = datetime.now(TIMEZONE)
            target = now.replace(hour=22, minute=0, second=0, microsecond=0)
            if now.hour >= 22:
                target += timedelta(days=1)
            wait = (target - now).total_seconds()
            await asyncio.sleep(max(1, wait))
            try:
                await start_world_boss(app, MAIN_GROUP_ID)
            except Exception as e:
                print(f"[world_boss] start failed: {e}")
            await asyncio.sleep(1800)
            if get_world_boss_active():
                try:
                    await end_world_boss(app, MAIN_GROUP_ID)
                except Exception as e:
                    print(f"[world_boss] end failed: {e}")
        except Exception as e:
            print(f"[world_boss] scheduler error: {e}")
            await asyncio.sleep(60)


async def despawn_checker():
    while True:
        await asyncio.sleep(60)
        now = time.time()
        expired = []
        for chat_id, ch in list(active_challenges.items()):
            if now - ch.get("spawn_time", 0) >= 300:
                expired.append(chat_id)
        for chat_id in expired:
            try:
                char = active_challenges[chat_id].get("char", {})
                name = char.get("name", "Character")
                await app.send_message(chat_id, f"**{name}** has left the island!")
            except Exception:
                pass
            active_challenges.pop(chat_id, None)


# ==================== MESSAGE COUNTER ====================
@app.on_message(filters.group, group=-1)
async def message_counter(client, message):
    if message.from_user and not message.from_user.is_bot:
        gid = message.chat.id
        message_count[gid] = message_count.get(gid, 0) + 1
        if message_count[gid] >= 150:
            message_count[gid] = 0
            if gid not in active_challenges:
                from admin import spawn_character
                try:
                    await spawn_character(app, gid, message.chat.title or "Group")
                except Exception as e:
                    print(f"[spawn] failed: {e}")
    message.continue_propagation()


# ==================== BAN CHECK ====================
_last_temp_ban_check = 0
_banned_reply_cache = {}


@app.on_message(filters.all, group=-20)
async def check_banned(client, message):
    global _last_temp_ban_check
    if not message.from_user:
        return
    uid = message.from_user.id

    cmd = ""
    if message.text:
        cmd = message.text.split()[0].split("@")[0]
    if cmd == "/info":
        message.continue_propagation()
        return

    now = time.time()
    if now - _last_temp_ban_check > 30:
        check_temp_bans()
        _last_temp_ban_check = now

    if uid in GBANNED:
        if _banned_reply_cache.get(uid, 0) > now - 60:
            message.stop_propagation()
            return
        _banned_reply_cache[uid] = now

        info = get_banned_player_info(uid)
        try:
            await message.reply(
                f"**YOU ARE GLOBALLY BANNED!**\n\n"
                f"Reason: {info.get('reason', 'Unknown')}\n"
                f"By: {info.get('banned_by_name', 'Unknown')}\n"
                f"Date: {info.get('banned_at_str', 'Unknown')}\n\n"
                f"You can only use /info."
            )
        except Exception:
            pass
        message.stop_propagation()
        return

    if uid in TEMP_BANNED:
        t = TEMP_BANNED[uid]
        if t > now:
            remaining = int(t - now)
            h, m, s = remaining // 3600, (remaining % 3600) // 60, remaining % 60
            if _banned_reply_cache.get(uid, 0) > now - 30:
                message.stop_propagation()
                return
            _banned_reply_cache[uid] = now
            try:
                await message.reply(
                    f"**YOU ARE TEMPORARILY BANNED!**\n\n"
                    f"Time left: **{h}h {m}m {s}s**"
                )
            except Exception:
                pass
            message.stop_propagation()
            return
        else:
            del TEMP_BANNED[uid]
            from data_manager import save_temp_banned
            save_temp_banned()

    message.continue_propagation()


# ==================== GROUP TRACKING ====================
@app.on_chat_member_updated()
async def track_groups(client, update):
    try:
        if update.new_chat_member and update.new_chat_member.user.id == client.me.id:
            status = update.new_chat_member.status
            if status in (ChatMemberStatus.MEMBER, ChatMemberStatus.ADMINISTRATOR):
                bot_groups.add(update.chat.id)
                save_bot_groups()
                print(f"[groups] Bot added: {update.chat.id} — {update.chat.title}")

        if update.old_chat_member and update.old_chat_member.user.id == client.me.id:
            old_status = update.old_chat_member.status
            if old_status in (ChatMemberStatus.LEFT, ChatMemberStatus.BANNED):
                if update.chat.id in bot_groups:
                    bot_groups.discard(update.chat.id)
                    save_bot_groups()
                    print(f"[groups] Bot removed: {update.chat.id}")
    except Exception as e:
        print(f"[track_groups] {e}")


@app.on_message(filters.group & filters.new_chat_members)
async def on_bot_added(client, message):
    try:
        for member in message.new_chat_members:
            if member.id == client.me.id:
                gid = message.chat.id
                if gid not in bot_groups:
                    bot_groups.add(gid)
                    save_bot_groups()
                    print(f"[groups] Bot added via message: {gid}")
                    await message.reply(
                        "**Thanks for adding me!**\n\nUse `/help` to see commands!"
                    )
                break
    except Exception as e:
        print(f"[on_bot_added] {e}")


# ==================== MAIN ====================
async def _post_start(app):
    """Runs inside the client's event loop after app.start()."""

    # ============ CHANNEL STORAGE ============
    if STORAGE_CHANNEL_ID:
        try:
            from channel_storage import sync_all_from_channel
            from data_manager import set_channel_client

            set_channel_client(app)
            await asyncio.sleep(2)

            print("[ChannelStorage] Syncing from Telegram...")
            await sync_all_from_channel(app)

            load_data()
            if CREW_AVAILABLE:
                try:
                    reload_crews()
                except Exception as e:
                    print(f"[crew] reload after sync failed: {e}")

            print("[ChannelStorage] Ready ✅")
        except Exception as e:
            print(f"[ChannelStorage] Sync failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("[ChannelStorage] STORAGE_CHANNEL_ID not set — skipping")

    # ============ STARTUP NOTIFICATION ============
    if NOTIFIER_AVAILABLE and UPDATE_CHANNEL_ID:
        try:
            await notify_startup(app, BOT_NAME, BOT_VERSION, UPDATE_CHANNEL_ID)
        except Exception as e:
            print(f"[startup notifier] {e}")

    # ============ BACKGROUND TASKS ============
    asyncio.create_task(world_boss_scheduler())
    asyncio.create_task(despawn_checker())


if __name__ == "__main__":
    print("=" * 50)
    print("GRAND LINE SENTINEL BOT")
    print("=" * 50)
    print(f"{BOT_NAME} v{BOT_VERSION} is running...")
    print("=" * 50)

    load_data()

    if CREW_AVAILABLE:
        try:
            reload_crews()
        except Exception as e:
            print(f"[crew] reload failed: {e}")

    # 1. Start client
    app.start()
    print("[DEBUG] Bot started. Listening...")

    # 2. Schedule post-start tasks INSIDE the client's loop
    app.loop.create_task(_post_start(app))

    # 3. Keep alive
    from pyrogram import idle
    idle()

    # 4. Cleanup
    app.stop()