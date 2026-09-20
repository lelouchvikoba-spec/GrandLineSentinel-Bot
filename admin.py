# admin.py
import asyncio
import json
import os
import time
from datetime import datetime
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    BOT_NAME, OWNER_ID, MAIN_GROUP_ID, UPDATE_CHANNEL_ID, BOT_VERSION,
    TIMEZONE,
)
from data_manager import (
    get_player, save_data, user_data, ADMINS, GBANNED, TEMP_BANNED,
    save_admins, save_banned, save_temp_banned, check_temp_bans,
    normal_characters, mythical_characters, save_normal_chars, save_mythical_chars,
    bot_groups, save_bot_groups, add_banned_player_info, remove_banned_player_info,
    get_banned_player_info, set_pending_forward, get_bot_groups, add_bot_group,
    add_normal_character, add_mythical_character,
    delete_normal_character, delete_mythical_character,
    get_character_by_id, get_character_by_name, is_admin_or_owner,
    active_challenges,
)
from utils import parse_amount, get_xp_needed, get_rank
from models import Player


def register_admin(app):

    # ==================== ADD NORMAL CHARACTER ====================
    @app.on_message(filters.command("ncradd"))
    async def add_normal_char(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return

        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(
                "📸 **Add Normal Character**\n\n"
                "Usage:\n"
                "1. `/ncradd Zoro` (then reply to photo)\n"
                "2. `/ncradd Monkey D. Luffy https://i.imgur.com/xxx.jpg`\n"
                "3. `/ncradd Roronoa Zoro <file_id>`"
            )
            return

        name_part = args[1].strip()
        parts = name_part.split()

        if len(parts) >= 2 and (
            parts[-1].startswith(("http://", "https://")) or len(parts[-1]) > 30
        ):
            name = " ".join(parts[:-1])
            photo_input = parts[-1]
        else:
            name = name_part
            photo_input = None

        if not photo_input:
            if message.reply_to_message and message.reply_to_message.photo:
                file_id = message.reply_to_message.photo.file_id
                add_normal_character(name, file_id)
                await message.reply(f"✅ Added **{name}** (photo file_id)")
                return
            await message.reply(
                f"❌ Provide an image!\n\n**Name:** {name}\n\n"
                f"Reply to a photo, or:\n"
                f"`/ncradd {name} https://...`"
            )
            return

        if photo_input.startswith(("http://", "https://")):
            if photo_input.lower().endswith((".png", ".jpg", ".jpeg")):
                add_normal_character(name, photo_input)
                await message.reply(f"✅ Added **{name}** (URL)")
                return
            if photo_input.lower().endswith((".gif", ".webp")):
                await message.reply("❌ Animated images not supported.")
                return
            await message.reply("❌ Invalid image URL!")
            return

        add_normal_character(name, photo_input)
        await message.reply(f"✅ Added **{name}** (file_id)")

    # ==================== ADD MYTHICAL CHARACTER ====================
    @app.on_message(filters.command("mcradd"))
    async def add_mythical_char(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return

        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(
                "📸 **Add Mythical Character**\n\n"
                "Usage: `/mcradd Kaido` (then reply with photo)\n"
                "Or: `/mcradd Monkey D. Luffy <url_or_file_id>`"
            )
            return

        name_part = args[1].strip()
        parts = name_part.split()

        if len(parts) >= 2 and (
            parts[-1].startswith(("http://", "https://")) or len(parts[-1]) > 30
        ):
            name = " ".join(parts[:-1])
            photo_input = parts[-1]
        else:
            name = name_part
            photo_input = None

        if not photo_input:
            if message.reply_to_message and message.reply_to_message.photo:
                file_id = message.reply_to_message.photo.file_id
                add_mythical_character(name, file_id)
                await message.reply(f"✅ Added **{name}** (mythical, photo file_id)")
                return
            await message.reply(f"❌ Provide an image for **{name}**!")
            return

        if photo_input.startswith(("http://", "https://")):
            if photo_input.lower().endswith((".png", ".jpg", ".jpeg")):
                add_mythical_character(name, photo_input)
                await message.reply(f"✅ Added **{name}** (mythical, URL)")
                return
            await message.reply("❌ Invalid image URL!")
            return

        add_mythical_character(name, photo_input)
        await message.reply(f"✅ Added **{name}** (mythical, file_id)")

    # ==================== DELETE CHARACTER ====================
    @app.on_message(filters.command("ncrdelete"))
    async def delete_normal_char(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return

        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/ncrdelete [id]`\nUse `/charslist` to see IDs")
            return

        try:
            char_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid ID!")
            return

        deleted = delete_normal_character(char_id)
        if deleted:
            await message.reply(f"✅ Deleted **{deleted['name']}** (ID: {char_id})")
        else:
            await message.reply(f"❌ No normal character with ID `{char_id}`!")

    @app.on_message(filters.command("mcrdelete"))
    async def delete_mythical_char(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return

        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/mcrdelete [id]`")
            return

        try:
            char_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid ID!")
            return

        deleted = delete_mythical_character(char_id)
        if deleted:
            await message.reply(f"✅ Deleted **{deleted['name']}** (ID: {char_id})")
        else:
            await message.reply(f"❌ No mythical character with ID `{char_id}`!")

    # ==================== LIST CHARACTERS ====================
    @app.on_message(filters.command("charslist"))
    async def chars_list_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return

        text = f"**CHARACTERS (Total: {len(normal_characters) + len(mythical_characters)})**\n\n"
        text += f"**Normal ({len(normal_characters)}):**\n"
        for c in normal_characters:
            text += f"`{c.get('id')}` — {c['name']}\n"
        text += f"\n**Mythical ({len(mythical_characters)}):**\n"
        for c in mythical_characters:
            text += f"`{c.get('id')}` — {c['name']}\n"

        if not normal_characters and not mythical_characters:
            text += "\n*No characters yet.*"

        if len(text) > 4000:
            for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
                await message.reply(chunk)
        else:
            await message.reply(text)

    # ==================== ADMIN MANAGEMENT ====================
    @app.on_message(filters.command("adda"))
    async def add_admin_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/adda [user_id]`")
            return
        try:
            admin_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid ID!")
            return
        ADMINS.add(admin_id)
        save_admins()
        await message.reply(f"✅ Added admin: `{admin_id}`")

    @app.on_message(filters.command("removeadmin"))
    async def remove_admin_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/removeadmin [user_id]`")
            return
        try:
            admin_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid ID!")
            return
        if admin_id in ADMINS:
            ADMINS.remove(admin_id)
            save_admins()
            await message.reply(f"✅ Removed admin: `{admin_id}`")
        else:
            await message.reply("❌ Not an admin!")

    @app.on_message(filters.command("admins"))
    async def list_admins_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return
        text = "👑 **ADMIN LIST** 👑\n\n"
        try:
            owner = await client.get_users(OWNER_ID)
            text += f"👑 **{owner.first_name}**\n   🆔 `{OWNER_ID}`\n\n"
        except Exception:
            text += f"👑 **Owner**\n   🆔 `{OWNER_ID}`\n\n"

        if ADMINS:
            for i, aid in enumerate(ADMINS, 1):
                try:
                    a = await client.get_users(aid)
                    text += f"{i}. **{a.first_name}** — `{aid}`\n"
                except Exception:
                    text += f"{i}. **User {aid}**\n"
        else:
            text += "No admins yet."
        await message.reply(text)

    # ==================== SET BOUNTY / FRUIT ====================
    @app.on_message(filters.command("setb"))
    async def set_bounty_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if not message.reply_to_message:
            await message.reply("Reply to a user!")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/setb [amount]`")
            return
        amount = parse_amount(args[1])
        if amount is None or amount < 0:
            await message.reply("❌ Invalid amount!")
            return
        p = get_player(message.reply_to_message.from_user.id)
        p.bounty = amount
        save_data()
        await message.reply(f"✅ Set {p.name}'s bounty to ฿{amount:,}")

    @app.on_message(filters.command("setf"))
    async def set_fruit_cmd(client, message):
        from config import DEVIL_FRUITS
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if not message.reply_to_message:
            await message.reply("Reply to a user!")
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("Usage: `/setf [fruit name]`")
            return

        fruit_name = args[1].strip().lower()
        matched_name = None
        matched_category = None

        for cat, fruits in DEVIL_FRUITS.items():
            for f in fruits:
                if f["full"].lower() == fruit_name:
                    matched_name = f["full"]
                    matched_category = cat
                    break
                if f["name"].lower() == fruit_name:
                    matched_name = f["full"]
                    matched_category = cat
                    break
            if matched_name:
                break

        if not matched_name:
            await message.reply(f"❌ **Fruit not found: `{args[1]}`**")
            return

        p = get_player(message.reply_to_message.from_user.id)
        p.devil_fruit = matched_name
        p.fruit_category = matched_category
        save_data()
        await message.reply(f"✅ Gave **{p.name}**: {matched_name} ({matched_category})")

    # ==================== GLOBAL BAN ====================
    @app.on_message(filters.command("gban"))
    async def global_ban_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return

        args = message.text.split()
        if len(args) < 2:
            await message.reply(
                "**GLOBAL BAN**\n\n"
                "Usage: `/gban [user_id] [reason]`\n\n"
                "Announces to every group the bot is in."
            )
            return

        try:
            user_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid User ID!")
            return

        reason = " ".join(args[2:]) if len(args) > 2 else "No reason provided"

        if user_id in GBANNED:
            await message.reply(f"❌ User `{user_id}` is already globally banned!")
            return
        if user_id == OWNER_ID:
            await message.reply("❌ You cannot ban yourself!")
            return

        try:
            user = await client.get_users(user_id)
            user_name = user.first_name or "Unknown"
            user_username = f"@{user.username}" if user.username else "No username"
        except Exception:
            user_name = f"User {user_id}"
            user_username = "Unknown"

        GBANNED.add(user_id)
        save_banned()
        add_banned_player_info(
            user_id=user_id,
            user_name=user_name,
            user_username=user_username,
            reason=reason,
            banned_by=message.from_user.id,
            banned_by_name=message.from_user.first_name,
        )

        ban_time = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
        announcement = (
            f"**GLOBAL BAN**\n\n"
            f"User: {user_name}\n"
            f"ID: `{user_id}`\n"
            f"Reason: {reason}\n"
            f"Banned by: {message.from_user.first_name}\n"
            f"Date: {ban_time}\n\n"
            f"This user is banned from ALL groups."
        )

        status_msg = await message.reply(
            f"Broadcasting ban...\n\n"
            f"{user_name} (`{user_id}`)\n\n"
            f"Groups: {len(bot_groups)}"
        )

        targets = set(bot_groups)
        targets.add(MAIN_GROUP_ID)
        targets.discard(message.chat.id)

        asyncio.create_task(
            _broadcast_ban(client, status_msg, targets, announcement, user_id, user_name)
        )

        try:
            await client.send_message(
                user_id,
                f"**YOU HAVE BEEN GLOBALLY BANNED!**\n\n"
                f"Reason: {reason}\n"
                f"By: {message.from_user.first_name}"
            )
        except Exception:
            pass

    @app.on_message(filters.command("ungban"))
    async def global_unban_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return

        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/ungban [user_id]`")
            return

        try:
            user_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid ID!")
            return

        if user_id not in GBANNED:
            await message.reply(f"❌ `{user_id}` is not globally banned!")
            return

        try:
            user = await client.get_users(user_id)
            user_name = user.first_name or "Unknown"
        except Exception:
            user_name = f"User {user_id}"

        GBANNED.discard(user_id)
        save_banned()
        remove_banned_player_info(user_id)

        unban_time = datetime.now(TIMEZONE).strftime("%Y-%m-%d %H:%M:%S")
        announcement = (
            f"**GLOBAL UNBAN**\n\n"
            f"User: {user_name}\n"
            f"ID: `{user_id}`\n"
            f"Unbanned by: {message.from_user.first_name}\n"
            f"Date: {unban_time}"
        )

        status_msg = await message.reply(
            f"Broadcasting unban...\n\n"
            f"{user_name} (`{user_id}`)\n\n"
            f"Groups: {len(bot_groups)}"
        )

        targets = set(bot_groups)
        targets.add(MAIN_GROUP_ID)
        targets.discard(message.chat.id)

        asyncio.create_task(
            _broadcast_ban(client, status_msg, targets, announcement, user_id, user_name)
        )

        try:
            await client.send_message(
                user_id,
                f"**YOU HAVE BEEN UNBANNED!**\n\n"
                f"By: {message.from_user.first_name}"
            )
        except Exception:
            pass

    # ==================== TEMP BAN ====================
    @app.on_message(filters.command("ban"))
    async def temp_ban_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return

        args = message.text.split()
        if len(args) < 3:
            await message.reply(
                "**TEMP BAN**\n\n"
                "Usage: `/ban [user_id] [time] [reason]`\n"
                "Time: `30s`, `5m`, `2h`, `1d`, `1w`"
            )
            return

        try:
            user_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid ID!")
            return

        time_str = args[2].lower()
        reason = " ".join(args[3:]) if len(args) > 3 else "No reason"

        time_map = {"s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
        unit = time_str[-1]
        if unit not in time_map:
            await message.reply("❌ Invalid time format!")
            return
        try:
            value = int(time_str[:-1])
        except ValueError:
            await message.reply("❌ Invalid time value!")
            return

        duration = value * time_map[unit]
        if duration > 2_592_000:
            await message.reply("❌ Max 30 days!")
            return

        unban_time = time.time() + duration
        TEMP_BANNED[user_id] = unban_time
        save_temp_banned()

        unit_names = {"s": "second", "m": "minute", "h": "hour", "d": "day", "w": "week"}
        time_text = f"{value} {unit_names[unit]}{'s' if value != 1 else ''}"

        try:
            user = await client.get_users(user_id)
            user_name = user.first_name
        except Exception:
            user_name = f"User {user_id}"

        await message.reply(
            f"**USER BANNED**\n\n"
            f"{user_name}\n"
            f"Duration: {time_text}\n"
            f"Reason: {reason}"
        )

        try:
            await client.send_message(
                user_id,
                f"**YOU HAVE BEEN BANNED!**\n\n"
                f"Reason: {reason}\n"
                f"Duration: {time_text}"
            )
        except Exception:
            pass

    @app.on_message(filters.command("unban"))
    async def temp_unban_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/unban [user_id]`")
            return
        try:
            user_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid ID!")
            return
        if user_id in TEMP_BANNED:
            del TEMP_BANNED[user_id]
            save_temp_banned()
            await message.reply(f"✅ Unbanned: `{user_id}`")
            try:
                await client.send_message(user_id, "**You have been unbanned!**")
            except Exception:
                pass
        else:
            await message.reply(f"❌ `{user_id}` is not temp-banned!")

    @app.on_message(filters.command("banlist"))
    async def banlist_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return
        check_temp_bans()
        text = "**BANS**\n\n**Global:**\n"
        for uid in GBANNED:
            info = get_banned_player_info(uid)
            text += f"• {info.get('user_name', uid)} (`{uid}`) — {info.get('reason', 'N/A')}\n"
        text += "\n**Temp:**\n"
        for uid, t in TEMP_BANNED.items():
            rem = int(t - time.time())
            text += f"• `{uid}` — {rem // 3600}h left\n"
        await message.reply(text)

    @app.on_message(filters.command("bannedlist"))
    async def banned_list_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return
        if not GBANNED:
            await message.reply("📭 No globally banned users!")
            return
        text = "**GLOBALLY BANNED**\n\n"
        for i, uid in enumerate(GBANNED, 1):
            info = get_banned_player_info(uid)
            text += (
                f"{i}. **{info.get('user_name', uid)}**\n"
                f"   ID: `{uid}`\n"
                f"   Reason: {info.get('reason', 'N/A')}\n"
                f"   By: {info.get('banned_by_name', 'Unknown')}\n"
                f"   At: {info.get('banned_at_str', 'Unknown')}\n\n"
            )
        await message.reply(text)

    # ==================== SPAWN / DESPAWN / RESET ====================
    @app.on_message(filters.command("spawn"))
    async def spawn_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if message.chat.id in active_challenges:
            await message.reply("❌ Already active! Use `/despawn`.")
            return
        from admin import spawn_character
        await spawn_character(app, message.chat.id, "Chat")
        await message.reply("✅ Character spawned! Despawns in 5 min.")

    @app.on_message(filters.command("despawn"))
    async def despawn_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return
        if message.chat.id in active_challenges:
            name = active_challenges[message.chat.id]["char"].get("name", "?")
            del active_challenges[message.chat.id]
            await message.reply(f"✅ **{name}** despawned!")
        else:
            await message.reply("❌ No active character!")

    @app.on_message(filters.command("reset"))
    async def reset_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if message.chat.id in active_challenges:
            del active_challenges[message.chat.id]
            await message.reply("✅ Reset!")
        else:
            await message.reply("❌ No active character!")

    # ==================== PLAYER MANAGEMENT ====================
    @app.on_message(filters.command("setlevel"))
    async def set_level_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if not message.reply_to_message:
            await message.reply("Reply to a user!\nUsage: `/setlevel [level]`")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/setlevel [level]`")
            return
        try:
            level = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid level!")
            return
        if level < 1 or level > 200:
            await message.reply("❌ Level must be 1-200!")
            return
        p = get_player(message.reply_to_message.from_user.id)
        old = p.level
        p.level = level
        p.xp = 0
        save_data()
        await message.reply(f"✅ **{p.name}**: Lv.{old} → Lv.{level}")

    @app.on_message(filters.command("setxp"))
    async def set_xp_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if not message.reply_to_message:
            await message.reply("Reply to a user!\nUsage: `/setxp [xp]`")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/setxp [xp]`")
            return
        try:
            xp = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid XP!")
            return
        p = get_player(message.reply_to_message.from_user.id)
        p.xp = max(0, xp)
        save_data()
        await message.reply(f"✅ **{p.name}** XP: {p.xp}")

    @app.on_message(filters.command("setbounty"))
    async def set_bounty_value_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if not message.reply_to_message:
            await message.reply("Reply to a user!\nUsage: `/setbounty [amount]`")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/setbounty [amount]`")
            return
        amount = parse_amount(args[1])
        if amount is None or amount < 0:
            await message.reply("❌ Invalid amount!")
            return
        p = get_player(message.reply_to_message.from_user.id)
        p.bounty = amount
        save_data()
        await message.reply(f"✅ **{p.name}** bounty: ฿{amount:,}")

    @app.on_message(filters.command("addbounty"))
    async def add_bounty_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if not message.reply_to_message:
            await message.reply("Reply to a user!\nUsage: `/addbounty [amount]`")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/addbounty [amount]`")
            return
        amount = parse_amount(args[1])
        if amount is None:
            await message.reply("❌ Invalid amount!")
            return
        p = get_player(message.reply_to_message.from_user.id)
        p.bounty = max(0, p.bounty + amount)
        save_data()
        await message.reply(f"✅ **{p.name}** new bounty: ฿{p.bounty:,}")

    @app.on_message(filters.command("addtoken"))
    async def add_token_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if not message.reply_to_message:
            await message.reply("Reply to a user!\nUsage: `/addtoken [count]`")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/addtoken [count]`")
            return
        try:
            count = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid count!")
            return
        if abs(count) > 1000:
            await message.reply("❌ Max 1000 tokens per command.")
            return
        p = get_player(message.reply_to_message.from_user.id)
        p.advanced_token = max(0, p.advanced_token + count)
        save_data()
        await message.reply(f"✅ **{p.name}** tokens: {p.advanced_token}")

    @app.on_message(filters.command("resetplayer"))
    async def reset_player_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/resetplayer [user_id]`")
            return
        try:
            target_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid ID!")
            return
        key = str(target_id)
        if key not in user_data:
            await message.reply(f"❌ Player `{target_id}` not found!")
            return

        old_player = user_data[key]
        old_name = old_player.name
        old_username = old_player.username
        old_bounty = old_player.bounty
        old_level = old_player.level

        fresh = Player(target_id)
        fresh.name = old_name
        fresh.username = old_username
        user_data[key] = fresh
        save_data()

        await message.reply(
            f"**PLAYER RESET**\n\n"
            f"{old_name} (`{target_id}`)\n"
            f"Before: ฿{old_bounty:,} Lv.{old_level}\n"
            f"After: ฿0 Lv.1"
        )
        try:
            await client.send_message(target_id, "Your account has been reset!")
        except Exception:
            pass

    @app.on_message(filters.command("resetall"))
    async def reset_all_players_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return

        args = message.text.split()
        if len(args) != 2 or args[1].lower() != "confirm":
            await message.reply(
                f"**RESET ALL PLAYERS**\n\n"
                f"Total Players: {len(user_data)}\n\n"
                f"Type `/resetall confirm` to proceed."
            )
            return

        from config import DATA_DIR
        ts = datetime.now(TIMEZONE).strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(DATA_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)
        backup_path = os.path.join(backup_dir, f"{ts}_users.json")

        try:
            backup_data = {uid: p.to_dict() for uid, p in user_data.items()}
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            await message.reply(f"❌ Backup failed!\n\n`{e}`")
            return

        total = len(user_data)
        new_data = {}
        for uid, old in user_data.items():
            fresh = Player(uid)
            fresh.name = old.name
            fresh.username = old.username
            new_data[uid] = fresh

        user_data.clear()
        user_data.update(new_data)
        save_data()

        await message.reply(
            f"**ALL PLAYERS RESET**\n\n"
            f"Players: **{total}**\n"
            f"Backup: `{os.path.relpath(backup_path)}`"
        )

    # ==================== SYSTEM ====================
    @app.on_message(filters.command("check"))
    async def check_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        await message.reply(
            f"**SYSTEM CHECK**\n\n"
            f"Users: {len(user_data)}\n"
            f"Admins: {len(ADMINS)}\n"
            f"Global bans: {len(GBANNED)}\n"
            f"Temp bans: {len(TEMP_BANNED)}\n"
            f"Active challenges: {len(active_challenges)}\n"
            f"Normal chars: {len(normal_characters)}\n"
            f"Mythical chars: {len(mythical_characters)}"
        )

    @app.on_message(filters.command("gstats"))
    async def global_stats_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        total_b = sum(p.bounty for p in user_data.values())
        total_v = sum(p.vault for p in user_data.values())
        total_c = sum(len(p.captured_chars) for p in user_data.values())
        await message.reply(
            f"**GLOBAL STATS**\n\n"
            f"Players: {len(user_data)}\n"
            f"Total bounty: ฿{total_b:,}\n"
            f"Total vault: ฿{total_v:,}\n"
            f"Total chars: {total_c}\n"
            f"Normal: {len(normal_characters)}\n"
            f"Mythical: {len(mythical_characters)}\n"
            f"Bans: {len(GBANNED)} global, {len(TEMP_BANNED)} temp\n"
            f"Admins: {len(ADMINS)}\n"
            f"Groups: {len(bot_groups)}"
        )

    @app.on_message(filters.command("resetcd"))
    async def reset_cd_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        from utils import last_command_time
        last_command_time.clear()
        for p in user_data.values():
            if hasattr(p, "pay_cd"):
                p.pay_cd = 0
            if hasattr(p, "rob_cd"):
                p.rob_cd = 0
        save_data()
        await message.reply("✅ All cooldowns reset!")

    @app.on_message(filters.command("checkgroup"))
    async def check_group_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        try:
            member = await client.get_chat_member(MAIN_GROUP_ID, client.me.id)
            chat = await client.get_chat(MAIN_GROUP_ID)
            status = str(member.status).split(".")[-1].upper()
            await message.reply(
                f"**Group Check**\n\n"
                f"Config ID: `{MAIN_GROUP_ID}`\n"
                f"Actual ID: `{chat.id}`\n"
                f"Title: {chat.title}\n"
                f"Bot Status: {status}\n"
                f"Match: {'Yes' if chat.id == MAIN_GROUP_ID else 'No'}"
            )
        except Exception as e:
            await message.reply(f"❌ Error: {e}")

    @app.on_message(filters.command("id"))
    async def get_id_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return
        if message.reply_to_message:
            u = message.reply_to_message.from_user
            await message.reply(f"**User ID:** `{u.id}`\n**Name:** {u.first_name}")
        else:
            await message.reply(f"**Chat ID:** `{message.chat.id}`")

    # ==================== BROADCAST ====================
    @app.on_message(filters.command("broadcast"))
    async def broadcast_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if not message.reply_to_message:
            await message.reply(
                "**BROADCAST**\n\n"
                "Reply to a message with:\n"
                "`/broadcast groups`\n"
                "`/broadcast users`\n"
                "`/broadcast all`"
            )
            return
        args = message.text.split()
        target = args[1].lower() if len(args) > 1 else "all"
        if target not in ("groups", "users", "all"):
            await message.reply("Use: groups, users, all")
            return
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Confirm", callback_data=f"confirm_broadcast_{target}")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_broadcast")],
        ])
        await message.reply(
            f"**CONFIRM BROADCAST**\n\n"
            f"Target: **{target.upper()}**\n\n"
            f"Click confirm to proceed.",
            reply_markup=kb,
        )

    @app.on_message(filters.command("forwardall"))
    async def forward_all_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if not message.reply_to_message:
            await message.reply("Reply to a message with `/forwardall`")
            return
        orig = message.reply_to_message
        set_pending_forward(message.from_user.id, {
            "chat_id": orig.chat.id,
            "message_id": orig.id,
            "text": orig.text,
        })
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Confirm", callback_data="confirm_forwardall")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_forwardall")],
        ])
        await message.reply("**CONFIRM FORWARD**\n\nForward to ALL groups and users?", reply_markup=kb)

    @app.on_message(filters.command("forwardgroups"))
    async def forward_groups_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if not message.reply_to_message:
            await message.reply("Reply to a message with `/forwardgroups`")
            return
        orig = message.reply_to_message
        set_pending_forward(message.from_user.id, {
            "chat_id": orig.chat.id, "message_id": orig.id, "text": orig.text,
        })
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Confirm", callback_data="confirm_forwardgroups")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_forwardall")],
        ])
        await message.reply("**CONFIRM FORWARD TO GROUPS**", reply_markup=kb)

    @app.on_message(filters.command("forwardusers"))
    async def forward_users_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if not message.reply_to_message:
            await message.reply("Reply to a message with `/forwardusers`")
            return
        orig = message.reply_to_message
        set_pending_forward(message.from_user.id, {
            "chat_id": orig.chat.id, "message_id": orig.id, "text": orig.text,
        })
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Confirm", callback_data="confirm_forwardusers")],
            [InlineKeyboardButton("Cancel", callback_data="cancel_forwardall")],
        ])
        await message.reply(f"**CONFIRM FORWARD TO USERS**\n\nTotal: {len(user_data)}", reply_markup=kb)

    # ==================== UPDATE ANNOUNCEMENT ====================
    @app.on_message(filters.command("sendupdate"))
    async def send_update_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if not UPDATE_CHANNEL_ID:
            await message.reply("❌ UPDATE_CHANNEL_ID not configured!")
            return
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply("Usage: `/sendupdate [message]`")
            return
        try:
            await client.send_message(
                UPDATE_CHANNEL_ID,
                f"**UPDATE ANNOUNCEMENT**\n\n"
                f"Version: `{BOT_VERSION}`\n"
                f"{datetime.now(TIMEZONE).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"{args[1]}\n\n"
                f"@Grand_Line_Sentinel_bot"
            )
            await message.reply("✅ Sent!")
        except Exception as e:
            await message.reply(f"❌ Failed: {e}")

    # ==================== PATTERN ====================
    @app.on_message(filters.command("pattern"))
    async def pattern_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return

        from config import PATTERNS, PATTERN_OVERRIDE_HOURS
        from data_manager import (
            get_current_pattern, set_current_pattern,
            clear_pattern_override, reset_sequence,
        )

        args = message.text.split()

        if len(args) == 1:
            current = get_current_pattern()
            info = PATTERNS.get(current, PATTERNS["pattern2"])
            await message.reply(
                f"**CURRENT PATTERN**\n\n"
                f"{info['emoji']} **{info['name']}**\n\n"
                f"Use `/currentpattern` for full status."
            )
            return

        if args[1].lower() == "auto":
            clear_pattern_override()
            await message.reply("✅ Override cleared. Auto mode resumed.")
            return

        if args[1].lower() == "reset":
            reset_sequence()
            await message.reply("✅ Sequence positions reset.")
            return

        mapping = {"1": "pattern1", "2": "pattern2", "3": "pattern3", "4": "pattern4"}
        if args[1] not in mapping:
            await message.reply("Usage: `/pattern [1/2/3/4|auto|reset]`")
            return

        chosen = mapping[args[1]]
        set_current_pattern(chosen, manual=True)
        info = PATTERNS[chosen]

        await message.reply(
            f"✅ **Pattern overridden!**\n\n"
            f"{info['emoji']} **{info['name']}**\n\n"
            f"Expires in {PATTERN_OVERRIDE_HOURS}h"
        )

    @app.on_message(filters.command("currentpattern"))
    async def current_pattern_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return

        from config import (
            PATTERNS, TIME_SCHEDULE, AUTO_SWITCH_ENABLED, DEFAULT_PATTERN,
        )
        from data_manager import get_current_pattern, get_override_status

        effective = get_current_pattern()
        info = PATTERNS.get(effective, PATTERNS.get(DEFAULT_PATTERN, {}))

        now = datetime.now(TIMEZONE)
        hour, minute = now.hour, now.minute
        auto = TIME_SCHEDULE.get(hour, "—")

        override = get_override_status()
        if override.get("active"):
            rem = override["remaining_seconds"]
            h, m = rem // 3600, (rem % 3600) // 60
            override_status = f"Active — `{override['pattern']}` (expires in {h}h {m}m)"
        else:
            override_status = "None (auto mode)"

        auto_status = "Enabled" if AUTO_SWITCH_ENABLED else "Disabled"
        next_hour = (hour + 1) % 24
        next_auto = TIME_SCHEDULE.get(next_hour, "—")

        text = (
            f"**PATTERN STATUS**\n"
            f"──────────────────\n\n"
            f"**Active:** {info.get('emoji', '?')} {info.get('name', '?')}\n\n"
            f"**Time:**\n"
            f"• Now: `{hour:02d}:{minute:02d}`\n"
            f"• Auto now: `{auto}`\n"
            f"• Next hour: `{next_auto}`\n\n"
            f"**Override:** {override_status}\n"
            f"**Auto:** {auto_status}\n"
            f"──────────────────\n\n"
            f"**Schedule:**\n"
        )

        for h in range(24):
            p = TIME_SCHEDULE.get(h, "—")
            p_info = PATTERNS.get(p, {})
            emoji = p_info.get("emoji", "?")
            marker = "▶️ " if h == hour else "   "
            text += f"{marker}`{h:02d}:00` {emoji} {p}\n"

        text += f"\n──────────────────\n@Grand_Line_Sentinel_bot"

        await message.reply(text)

    # ==================== STATS ====================
    @app.on_message(filters.command("stats"))
    async def stats_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return

        try:
            total_players = len(user_data)
            total_groups = len(bot_groups)
            now = time.time()

            def is_active(p, days):
                d = getattr(p, "daily", 0)
                if isinstance(d, (int, float)) and d:
                    return (now - d) < days * 86400
                return False

            active_24h = sum(1 for p in user_data.values() if is_active(p, 1))
            active_7d = sum(1 for p in user_data.values() if is_active(p, 7))

            total_bounty = sum(getattr(p, "bounty", 0) for p in user_data.values())
            total_vault = sum(getattr(p, "vault", 0) for p in user_data.values())

            now_local = datetime.now(TIMEZONE)

            text = (
                f"**BOT STATISTICS**\n"
                f"──────────────────\n"
                f"{now_local.strftime('%Y-%m-%d %H:%M')}\n"
                f"──────────────────\n\n"
                f"**USERS**\n"
                f"Total: {total_players:,}\n"
                f"Active (24h): {active_24h:,}\n"
                f"Active (7d): {active_7d:,}\n\n"
                f"**GROUPS**\n"
                f"Total: {total_groups:,}\n\n"
                f"**MODERATION**\n"
                f"Global bans: {len(GBANNED):,}\n"
                f"Temp bans: {len(TEMP_BANNED):,}\n"
                f"Admins: {len(ADMINS):,}\n\n"
                f"**ECONOMY**\n"
                f"Total bounty: ฿{total_bounty:,}\n"
                f"Total vault: ฿{total_vault:,}\n\n"
                f"**CHARACTERS**\n"
                f"Normal: {len(normal_characters):,}\n"
                f"Mythical: {len(mythical_characters):,}\n\n"
                f"──────────────────\n@Grand_Line_Sentinel_bot"
            )

            if len(text) > 4000:
                for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
                    await message.reply(chunk)
            else:
                await message.reply(text)

        except Exception as e:
            print(f"[stats] {e}")
            await message.reply(f"❌ Error: `{e}`")

    # ==================== GROUPS ====================
    @app.on_message(filters.command("groups"))
    async def groups_list_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return

        if not bot_groups:
            await message.reply("📭 **No groups tracked yet.**")
            return

        limit = 30
        groups_list = list(bot_groups)[:limit]

        status = await message.reply(f"Loading {min(len(bot_groups), limit)} groups...")

        text = f"**BOT GROUPS** ({len(bot_groups)} total)\n"
        text += "──────────────────\n\n"

        for i, gid in enumerate(groups_list, 1):
            try:
                try:
                    gid_int = int(gid)
                except (ValueError, TypeError):
                    gid_int = gid

                chat = await client.get_chat(gid_int)
                await asyncio.sleep(0.05)

                title = chat.title or "Untitled"
                if len(title) > 30:
                    title = title[:27] + "…"

                text += f"{i}. **{title}**\n"

                if chat.username:
                    text += f"   @{chat.username}\n"
                text += f"   `{gid}`\n\n"

            except Exception:
                text += f"{i}. Inaccessible\n   `{gid}`\n\n"

        if len(bot_groups) > limit:
            text += f"... and {len(bot_groups) - limit} more\n\n"

        text += f"──────────────────\n@Grand_Line_Sentinel_bot"

        try:
            await status.delete()
        except Exception:
            pass

        if len(text) > 4000:
            for chunk in [text[i:i+4000] for i in range(0, len(text), 4000)]:
                await message.reply(chunk)
        else:
            await message.reply(text)

    @app.on_message(filters.command("removegroup"))
    async def remove_group_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/removegroup [group_id]`")
            return
        try:
            gid = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid group ID!")
            return
        if gid not in bot_groups:
            await message.reply(f"❌ `{gid}` is not tracked!")
            return
        bot_groups.discard(gid)
        save_bot_groups()
        await message.reply(f"✅ Removed `{gid}`.")

    @app.on_message(filters.command("addgroup"))
    async def add_group_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/addgroup [group_id]`")
            return
        try:
            gid = int(args[1])
            add_bot_group(gid)
            await message.reply(f"✅ Added group: `{gid}`")
        except Exception as e:
            await message.reply(f"❌ Error: {e}")

    @app.on_message(filters.command("listgroups"))
    async def list_groups_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return
        if not bot_groups:
            await message.reply("📭 No groups saved!")
            return
        text = "**BOT GROUPS**\n\n"
        for i, gid in enumerate(bot_groups, 1):
            text += f"{i}. `{gid}`\n"
        await message.reply(text)

    # ==================== BACKUP ====================
    @app.on_message(filters.command("backup"))
    async def backup_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return

        from config import DATA_DIR
        ts = datetime.now(TIMEZONE).strftime("%Y%m%d_%H%M%S")
        backup_dir = os.path.join(DATA_DIR, "backups")
        os.makedirs(backup_dir, exist_ok=True)

        files = {
            "users.json": {uid: p.to_dict() for uid, p in user_data.items()},
            "normal_chars.json": normal_characters,
            "mythical_chars.json": mythical_characters,
            "gbanned.json": list(GBANNED),
            "temp_banned.json": {str(k): v for k, v in TEMP_BANNED.items()},
            "admins.json": list(ADMINS),
            "bot_groups.json": list(bot_groups),
        }

        try:
            from crew import CREW_STORE
            files["crews.json"] = CREW_STORE
        except Exception:
            pass

        saved = 0
        failed = 0
        for fname, payload in files.items():
            try:
                path = os.path.join(backup_dir, f"{ts}_{fname}")
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2, ensure_ascii=False)
                saved += 1
            except Exception as e:
                print(f"[backup] {fname}: {e}")
                failed += 1

        total_size = 0
        try:
            for f in os.listdir(backup_dir):
                if f.startswith(ts):
                    total_size += os.path.getsize(os.path.join(backup_dir, f))
        except Exception:
            pass

        await message.reply(
            f"💾 **BACKUP COMPLETE**\n\n"
            f"📁 `data/backups/`\n"
            f"📊 {saved} saved, {failed} failed\n"
            f"💽 {total_size // 1024} KB\n"
            f"⏰ `{ts}`"
        )

    @app.on_message(filters.command("backups"))
    async def list_backups_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return

        from config import DATA_DIR
        from collections import defaultdict

        backup_dir = os.path.join(DATA_DIR, "backups")
        if not os.path.exists(backup_dir):
            await message.reply("📭 No backups yet. Use `/backup`.")
            return

        snaps = defaultdict(list)
        for fname in os.listdir(backup_dir):
            if "_" in fname and fname.endswith(".json"):
                parts = fname.split("_", 2)
                if len(parts) >= 3:
                    ts = f"{parts[0]}_{parts[1]}"
                    snaps[ts].append(fname)

        if not snaps:
            await message.reply("📭 No backups found.")
            return

        sorted_ts = sorted(snaps.keys(), reverse=True)[:15]
        text = f"💾 **BACKUPS** ({len(snaps)} total)\n──────────────────\n\n"

        for i, ts in enumerate(sorted_ts, 1):
            files = snaps[ts]
            try:
                dt = datetime.strptime(ts, "%Y%m%d_%H%M%S").replace(tzinfo=TIMEZONE)
                friendly = dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                friendly = ts

            total = 0
            for f in files:
                try:
                    total += os.path.getsize(os.path.join(backup_dir, f))
                except Exception:
                    pass

            text += f"**{i}.** `{ts}`\n   📅 {friendly}\n   📊 {len(files)} files • {total // 1024} KB\n\n"

        text += f"──────────────────\n💡 `/restore [timestamp]`\n\n@Grand_Line_Sentinel_bot"
        await message.reply(text)

    @app.on_message(filters.command("restore"))
    async def restore_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return

        from config import DATA_DIR
        args = message.text.split()
        if len(args) != 2:
            await message.reply(
                "**RESTORE**\n\n"
                "Usage: `/restore [timestamp]`\n\n"
                "Use `/backups` to list timestamps."
            )
            return

        ts = args[1]
        backup_dir = os.path.join(DATA_DIR, "backups")
        user_file = os.path.join(backup_dir, f"{ts}_users.json")

        if not os.path.exists(user_file):
            await message.reply(f"❌ No backup found for `{ts}`!")
            return

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚠️ Confirm Restore", callback_data=f"restore_confirm_{ts}")],
            [InlineKeyboardButton("❌ Cancel", callback_data="noop")],
        ])

        await message.reply(
            f"⚠️ **RESTORE FROM `{ts}`?**\n\n"
            f"This will **overwrite** current data!\n\n"
            f"Are you sure?",
            reply_markup=kb,
        )

    @app.on_message(filters.command("delbackup"))
    async def del_backup_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return

        from config import DATA_DIR
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/delbackup [timestamp]`")
            return

        ts = args[1]
        backup_dir = os.path.join(DATA_DIR, "backups")

        deleted = 0
        try:
            for fname in os.listdir(backup_dir):
                if fname.startswith(ts + "_"):
                    try:
                        os.remove(os.path.join(backup_dir, fname))
                        deleted += 1
                    except Exception:
                        pass
        except Exception:
            pass

        if deleted:
            await message.reply(f"✅ Deleted {deleted} files from `{ts}`")
        else:
            await message.reply(f"❌ No backup found for `{ts}`")

    # ==================== ADMINHELP (admin-only) ====================
    @app.on_message(filters.command("adminhelp"))
    async def admin_help_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return

        await message.reply(
            f"👑 **ADMIN COMMANDS** 👑\n\n"
            f"👤 **Players:**\n"
            f"• `/resetplayer [id]`\n"
            f"• `/setb [amount]` (reply)\n"
            f"• `/setf [fruit]` (reply)\n"
            f"• `/setlevel [lv]` (reply)\n"
            f"• `/setxp [xp]` (reply)\n"
            f"• `/setbounty [amt]` (reply)\n"
            f"• `/addbounty [amt]` (reply)\n"
            f"• `/addtoken [n]` (reply)\n\n"
            f"🚫 **Bans:**\n"
            f"• `/ban [id] [time] [reason]`\n"
            f"• `/unban [id]`\n"
            f"• `/banlist`\n"
            f"• `/bannedlist`\n\n"
            f"🎮 **Characters:**\n"
            f"• `/ncradd`\n"
            f"• `/mcradd`\n"
            f"• `/ncrdelete [id]`\n"
            f"• `/mcrdelete [id]`\n"
            f"• `/charslist`\n\n"
            f"🎲 **Game:**\n"
            f"• `/despawn`\n"
            f"• `/resetcd`\n\n"
            f"📊 **Stats:**\n"
            f"• `/stats`\n"
            f"• `/groups`\n\n"
            f"📢 **Broadcast:**\n"
            f"• `/broadcast [groups|users|all]`\n"
            f"• `/forwardall`, `/forwardgroups`, `/forwardusers`\n\n"
            f"🎁 **Giveaway:**\n"
            f"• `/tgiveaway`\n"
            f"• `/cancelgiveaway [msg_id]`\n"
            f"• `/endgiveaway [msg_id]`\n"
            f"• `/activegiveaways`\n\n"
            f"🎯 **Pattern:**\n"
            f"• `/pattern [1/2/3/4]`\n"
            f"• `/currentpattern`\n\n"
            f"🤖 @Grand_Line_Sentinel_bot"
        )

    # ==================== OWNERHELP (owner-only) ====================
    @app.on_message(filters.command("ownerhelp"))
    async def owner_help_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return

        await message.reply(
            f"👑 **OWNER COMMANDS** 👑\n\n"
            f"👥 **Admins:**\n"
            f"• `/adda [id]`\n"
            f"• `/removeadmin [id]`\n"
            f"• `/admins`\n\n"
            f"🌍 **Global Bans:**\n"
            f"• `/gban [id] [reason]`\n"
            f"• `/ungban [id]`\n"
            f"• `/bannedlist`\n\n"
            f"👤 **Players:**\n"
            f"• `/resetall confirm`\n"
            f"• `/setbounty [amt]`\n"
            f"• `/setb`, `/setf`, `/setlevel`, `/setxp`\n"
            f"• `/addbounty`, `/addtoken`\n\n"
            f"🎮 **Game:**\n"
            f"• `/spawn`, `/reset`\n"
            f"• `/resetcd`\n"
            f"• `/pattern [1/2/3/4]`, `/pattern auto`\n"
            f"• `/currentpattern`\n\n"
            f"📊 **System:**\n"
            f"• `/check`, `/gstats`, `/checkgroup`\n"
            f"• `/stats`, `/groups`\n"
            f"• `/addgroup`, `/removegroup`, `/listgroups`\n\n"
            f"📢 **Announcements:**\n"
            f"• `/broadcast [groups|users|all]`\n"
            f"• `/forwardall`, `/forwardgroups`, `/forwardusers`\n"
            f"• `/sendupdate [msg]`\n\n"
            f"🎁 **Global Giveaway:**\n"
            f"• `/agiveaway [time] [prize] [winners] [reason]`\n"
            f"• `/cancelagiveaway`\n\n"
            f"💾 **Backup:**\n"
            f"• `/backup`\n"
            f"• `/backups`\n"
            f"• `/restore [timestamp]`\n"
            f"• `/delbackup [timestamp]`\n\n"
            f"🤖 @Grand_Line_Sentinel_bot"
        )


# ==================== BAN BROADCAST HELPER ====================
async def _broadcast_ban(client, status_msg, targets, announcement, user_id, user_name):
    sent = 0
    failed = 0
    removed = []
    total = len(targets)

    sem = asyncio.Semaphore(8)

    async def _one(gid):
        nonlocal sent, failed
        async with sem:
            try:
                await client.send_message(gid, announcement)
                sent += 1
            except Exception as e:
                failed += 1
                err = str(e).lower()
                if any(k in err for k in (
                    "chat not found", "bot was kicked",
                    "bot is not a member", "peer id invalid",
                )):
                    removed.append(gid)
                await asyncio.sleep(0.05)

    await asyncio.gather(*(_one(gid) for gid in targets))

    for gid in removed:
        bot_groups.discard(gid)
    if removed:
        save_bot_groups()

    try:
        await status_msg.edit_text(
            f"**BROADCAST COMPLETE**\n\n"
            f"{user_name}\n"
            f"ID: `{user_id}`\n\n"
            f"Sent: **{sent}**\n"
            f"Failed: **{failed}**\n"
            f"Total: **{total}**"
        )
    except Exception as e:
        print(f"[broadcast_ban] status edit failed: {e}")


# ==================== SPAWN FUNCTION ====================
async def spawn_character(app, chat_id, chat_name):
    import random
    from data_manager import active_challenges, normal_characters, mythical_characters

    if chat_id in active_challenges:
        return

    is_mythical = random.random() < 0.1 and mythical_characters

    if is_mythical:
        char = random.choice(mythical_characters)
        msg = (
            f"⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️\n"
            f"**⚠️ MYTHICAL CHARACTER APPEARED!**\n"
            f"⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️⚠️\n\n"
            f"Character: ???\n"
            f"Type: MYTHICAL\n"
            f"Reward: 10,000,000,000 + 1 Token\n\n"
            f"Despawns in 5 min\n"
            f"Type `/challenge [name]` to fight!"
        )
    elif normal_characters:
        char = random.choice(normal_characters)
        msg = (
            f"**A Wild Character Appeared!**\n\n"
            f"Character: ???\n"
            f"Type: Normal\n"
            f"Reward: Random Bounty + XP\n\n"
            f"Despawns in 5 min\n"
            f"Type `/challenge [name]` to fight!"
        )
    else:
        return

    active_challenges[chat_id] = {
        "char": char,
        "is_mythical": is_mythical,
        "challenger": None,
        "spawn_time": time.time(),
        "chat_name": chat_name,
    }

    if char.get("image"):
        try:
            await app.send_photo(chat_id, char["image"], caption=msg)
            return
        except Exception:
            pass
        try:
            await app.send_document(chat_id, char["image"], caption=msg)
            return
        except Exception:
            pass
    await app.send_message(chat_id, msg)