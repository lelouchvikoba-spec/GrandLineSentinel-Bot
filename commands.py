# commands.py
import time
import os
import asyncio
import random
from io import BytesIO
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

try:
    from PIL import Image, ImageDraw, ImageFont, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from config import (
    BOT_NAME, MAIN_GROUP_LINK, UPDATE_CHANNEL_LINK, MAIN_GROUP_ID,
    TOP_IMAGE, WANTED_IMAGE, VAULT_CAPS, DEVIL_FRUITS, HAKI_NAMES,
    UPDATE_CHANNEL_USERNAME,
)
from data_manager import (
    get_player, save_data, user_data, GBANNED,
    get_global_giveaway, normal_characters, mythical_characters,
)
from utils import (
    get_xp_needed, get_rank, check_cooldown, parse_amount,
    load_name_font, load_bounty_font,
)
from pvp import (
    send_level_up_notification, send_level_up_group_notification,
    send_level_down_notification, send_level_down_group_notification,
)

my_chars_sessions = {}


# ==================== MODULE-LEVEL: SHOW CHARS PAGE ====================
async def show_chars_list_page(client, message, user_id, page):
    """Show a page of the user's captured characters."""
    session = my_chars_sessions.get(user_id)
    if not session:
        return

    char_list = session["char_list"]
    items_per_page = 10
    total_pages = (len(char_list) + items_per_page - 1) // items_per_page

    if page >= total_pages:
        page = total_pages - 1
    if page < 0:
        page = 0

    start = page * items_per_page
    end = start + items_per_page
    page_chars = char_list[start:end]

    text = f"📦 **YOUR CAPTURED CHARACTERS - PAGE {page + 1}/{max(1, total_pages)}**\n\n"

    keyboard = []

    for i, char in enumerate(page_chars, start + 1):
        is_mythical = any(c.get("name") == char["name"] for c in mythical_characters)
        rarity_emoji = "👹" if is_mythical else "💠"

        text += f"{rarity_emoji} **{i}.** {char['name']} (x{char['count']})\n"

        keyboard.append([InlineKeyboardButton(
            f"{rarity_emoji} {char['name']} (x{char['count']})",
            switch_inline_query=f"character.{user_id} {char['name']}"
        )])

    keyboard.append([InlineKeyboardButton(
        f"📸 ALL CHARACTERS ({len(char_list)})",
        switch_inline_query=f"character.{user_id}"
    )])

    text += f"\n📊 **Total:** {len(char_list)} unique characters\n"
    text += f"🎮 **Player ID:** `{user_id}`\n\n"
    text += f"💡 **Tap a character name** to see its photos"

    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton("◀️ PREV", callback_data=f"chars_page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton("NEXT ▶️", callback_data=f"chars_page_{page + 1}"))

    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("❌ CLOSE", callback_data="delete_this")])

    session["current_page"] = page
    my_chars_sessions[user_id] = session

    await message.reply(text, reply_markup=InlineKeyboardMarkup(keyboard))


def register_commands(app):

    # ==================== START COMMAND ====================
    @app.on_message(filters.command("start"))
    async def start_cmd(client, message):
        user_id = message.from_user.id
        p = get_player(user_id, user=message.from_user)
        p.name = message.from_user.first_name
        if message.from_user.username:
            p.username = message.from_user.username
        save_data()

        args = message.text.split()
        if len(args) > 1 and args[1] == "global_giveaway":
            gg = get_global_giveaway()
            if gg is not None:
                if user_id not in gg["participants"]:
                    main_joined = False
                    updates_joined = False

                    try:
                        m = await client.get_chat_member(MAIN_GROUP_ID, user_id)
                        if str(m.status).split(".")[-1].upper() in (
                            "MEMBER", "ADMINISTRATOR", "OWNER", "CREATOR"
                        ):
                            main_joined = True
                    except Exception:
                        pass

                    try:
                        m = await client.get_chat_member(UPDATE_CHANNEL_USERNAME, user_id)
                        if str(m.status).split(".")[-1].upper() in (
                            "MEMBER", "ADMINISTRATOR", "OWNER", "CREATOR"
                        ):
                            updates_joined = True
                    except Exception:
                        pass

                    if main_joined and updates_joined:
                        gg["participants"].append(user_id)
                        await message.reply(
                            f"✅ **Joined the Global Giveaway!**\n\n"
                            f"📦 Prize: ฿{gg['total_prize']:,}\n"
                            f"👥 Total: {len(gg['participants'])}\n\n"
                            f"Good luck!"
                        )
                    else:
                        kb = InlineKeyboardMarkup([
                            [InlineKeyboardButton("🏠 Join Main Group", url=MAIN_GROUP_LINK)],
                            [InlineKeyboardButton("📢 Join Updates", url=UPDATE_CHANNEL_LINK)],
                            [InlineKeyboardButton("✅ Verify & Join", callback_data="verify_global_giveaway")]
                        ])
                        await message.reply(
                            f"❌ **Join both communities first!**",
                            reply_markup=kb
                        )
                else:
                    await message.reply("✅ **Already joined!**")
            else:
                await message.reply("❌ **No active global giveaway!**")
            return

        is_new = p.bounty == 0 and p.level == 1

        join_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🏠 Join Main Group", url=MAIN_GROUP_LINK)],
            [InlineKeyboardButton("📢 Join Updates Channel", url=UPDATE_CHANNEL_LINK)],
            [InlineKeyboardButton("🔄 Check Membership", callback_data="check_membership")]
        ])

        if is_new:
            welcome_text = (
                f"🏴‍☠️ **WELCOME TO GRAND LINE SENTINEL!** 🏴‍☠️\n\n"
                f"⚓ Welcome to the Grand Line, {message.from_user.first_name}!\n"
                f"💪 Your journey to become the Pirate King starts now!\n\n"
                f"📜 **Get started:**\n"
                f"• Use /help to see all commands\n"
                f"• Use /daily to claim daily reward\n"
                f"• Use /shop to buy items\n"
                f"• Use /info to view your profile\n\n"
                f"⚠️ **Please join our communities:**\n"
                f"• Main Group for events\n"
                f"• Updates Channel for news\n\n"
                f"⚔️ **Good luck on your adventure!** ⚔️\n\n"
                f"🤖 @Grand_Line_Sentinel_bot"
            )
        else:
            welcome_text = (
                f"🏴‍☠️ **WELCOME BACK!** 🏴‍☠️\n\n"
                f"⚓ Welcome back, {message.from_user.first_name}!\n"
                f"💪 Continue your journey to become the Pirate King!\n\n"
                f"📊 **Your Stats:**\n"
                f"💰 Bounty: ฿{p.bounty:,}\n"
                f"⚔️ Level: {p.level}\n"
                f"🏆 Rank: {get_rank(p.level)}\n\n"
                f"📜 Use /help for commands.\n\n"
                f"🤖 @Grand_Line_Sentinel_bot"
            )

        await message.reply(welcome_text, reply_markup=join_keyboard, disable_web_page_preview=True)

    # ==================== HELP COMMAND (Public) ====================
    @app.on_message(filters.command("help"))
    async def help_cmd(client, message):
        await message.reply(
            f"📜 **COMMANDS** 📜\n\n"
            f"💰 **GAMES (CD: 2s):**\n"
            f"/bet [amount] [t/h] - 🪙 Coin flip\n"
            f"/dice [amount] [e/o] - 🎲 Dice game\n"
            f"/dart [amount] - 🎯 Dart game\n"
            f"/bowl [amount] - 🎳 Bowling game\n"
            f"/soccer [amount] - ⚽ Soccer game\n\n"
            f"👤 **PROFILE:**\n"
            f"/info - 📸 Your wanted poster\n"
            f"/bal - 💰 Check balance\n"
            f"/tokens - 🔮 Check advanced tokens\n"
            f"/daily - 📅 Daily reward (10k)\n"
            f"/weekly - 📆 Weekly reward (1M)\n"
            f"/claim - 🎁 Main group join reward\n"
            f"/top - 🏆 Top 10 bounty\n"
            f"/xtop - ⚔️ Top 10 level\n\n"
            f"🎒 **INVENTORY:**\n"
            f"/inventory - 📦 View your items\n"
            f"/useshield - 🛡️ Activate a shield\n"
            f"/useboost - ⚡ Activate an XP boost\n\n"
            f"🛒 **SHOP:**\n"
            f"/shop - 🏪 Buy items\n"
            f"/sell_fruit - 🍎 Sell fruit (50%)\n\n"
            f"⚔️ **PVP & FIGHT:**\n"
            f"/attack - ⚔️ Fight player (reply)\n"
            f"/rob - 💰 Rob player (reply)\n"
            f"/challenge [name] - 👹 Fight character\n"
            f"/timeleft - ⏰ Character despawn timer\n"
            f"/mychars - 📦 Your captured characters\n"
            f"/trade [amount] - 💰 Sell character (reply)\n"
            f"/battle - 🌑 Fight World Boss\n\n"
            f"🏦 **VAULT:**\n"
            f"/deposit [amount] - 📥 Store bounty\n"
            f"/dig [amount] - 📤 Withdraw bounty\n\n"
            f"⚙️ **SETTINGS:**\n"
            f"/pvp - ⚔️ Toggle PVP Mode\n"
            f"/passive - 🛡️ Toggle Shield Protection\n\n"
            f"⚔️ **HAKI:**\n"
            f"/haki - 📊 View your Haki\n"
            f"/activehaki - 🟢 Activate Haki\n"
            f"/disactivehaki - 🔴 Deactivate Haki\n"
            f"/upgradehaki - ⬆️ Level up Haki\n"
            f"/sell_haki - 💵 Sell Haki\n\n"
            f"⚓ **CREW:**\n"
            f"/crew - 📋 Crew menu\n"
            f"/crewcreate [name] | [TAG] - Create crew\n"
            f"/crewinfo - Crew info\n"
            f"/crewlist - Top crews\n"
            f"/crewtop - Full leaderboard\n"
            f"/crewbank - Shared bank\n"
            f"/ship - View your ship\n"
            f"/shiplist - All ships\n\n"
            f"🎁 **GIVEAWAY:**\n"
            f"/join - Join active giveaway\n\n"
            f"📊 **CHARACTER INFO:**\n"
            f"/charinfo [name] or /c [name] - View character info\n"
            f"@Grand_Line_Sentinel_bot [name] - Search inline\n\n"
            f"🤖 @Grand_Line_Sentinel_bot"
        )

    # ==================== BALANCE COMMAND ====================
    @app.on_message(filters.command("bal"))
    async def balance_cmd(client, message):
        if message.reply_to_message:
            target_user = message.reply_to_message.from_user
            p = get_player(target_user.id, user=target_user)
            name = target_user.first_name
        else:
            p = get_player(message.from_user.id, user=message.from_user)
            name = message.from_user.first_name

        cap = VAULT_CAPS.get(p.vault_level, 25_000_000)
        await message.reply(f"**{name}'s Bounty:** ฿{p.bounty:,}\n**Vault:** ฿{p.vault:,} / {cap:,}")

    # ==================== TOKENS COMMAND ====================
    @app.on_message(filters.command("tokens"))
    async def tokens_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        await message.reply(
            f"🔮 **ADVANCED TOKENS** 🔮\n\n"
            f"📦 Tokens: ⚜️**{p.advanced_token}**\n"
            f"✨ Advanced Haki: **{'✅ Unlocked' if p.advanced_haki else '❌ Locked'}**"
        )

    # ==================== DAILY COMMAND ====================
    @app.on_message(filters.command("daily"))
    async def daily_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        now = int(time.time())
        if now - p.daily < 86400:
            left = 86400 - (now - p.daily)
            await message.reply(f"📅 Already claimed! Next in {left // 3600}h")
            return
        p.daily = now
        p.bounty += 10_000
        p.xp += 50
        if p.boost_end > time.time():
            p.xp += 25

        old_lvl = p.level
        while p.xp >= get_xp_needed(p.level) and p.level < 200:
            p.xp -= get_xp_needed(p.level)
            p.level += 1
        if p.level >= 200:
            p.xp = 0

        save_data()

        if p.level > old_lvl:
            await send_level_up_notification(app, message.from_user.id, old_lvl, p.level, "daily")
            await send_level_up_group_notification(app, message.chat.id, p.name, old_lvl, p.level)

        lt = f"\n\n🎉 **LEVEL UP!** {old_lvl} → {p.level}" if p.level > old_lvl else ""
        await message.reply(f"🎁 **Daily:** ฿10,000 + 50 XP!{lt}")

    # ==================== WEEKLY COMMAND ====================
    @app.on_message(filters.command("weekly"))
    async def weekly_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        now = int(time.time())
        if now - p.weekly < 604800:
            left = 604800 - (now - p.weekly)
            await message.reply(f"📆 Already claimed! Next in {left // 86400}d")
            return
        p.weekly = now
        p.bounty += 1_000_000
        p.xp += 500
        if p.boost_end > time.time():
            p.xp += 250

        old_lvl = p.level
        while p.xp >= get_xp_needed(p.level) and p.level < 200:
            p.xp -= get_xp_needed(p.level)
            p.level += 1
        if p.level >= 200:
            p.xp = 0

        save_data()

        if p.level > old_lvl:
            await send_level_up_notification(app, message.from_user.id, old_lvl, p.level, "weekly")
            await send_level_up_group_notification(app, message.chat.id, p.name, old_lvl, p.level)

        lt = f"\n\n🎉 **LEVEL UP!** {old_lvl} → {p.level}" if p.level > old_lvl else ""
        await message.reply(f"🎁 **Weekly:** ฿1,000,000 + 500 XP!{lt}")

    # ==================== CHARACTER INFO ====================
    @app.on_message(filters.command("charinfo") | filters.command("c"))
    async def character_info_cmd(client, message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.reply(
                "📊 **CHARACTER INFO**\n\n"
                "Usage: `/charinfo [name]` or `/c [name]`\n"
                "Example: `/charinfo Zoro`"
            )
            return

        query = args[1].lower().strip()
        found = None
        ctype = None
        for c in normal_characters:
            if c.get("name", "").lower() == query:
                found, ctype = c, "Normal"
                break
        if not found:
            for c in mythical_characters:
                if c.get("name", "").lower() == query:
                    found, ctype = c, "Mythical"
                    break
        if not found:
            for c in normal_characters:
                if query in c.get("name", "").lower():
                    found, ctype = c, "Normal"
                    break
        if not found:
            for c in mythical_characters:
                if query in c.get("name", "").lower():
                    found, ctype = c, "Mythical"
                    break

        if not found:
            await message.reply(f"❌ Character **{args[1]}** not found!")
            return

        capturers = []
        total = 0
        for uid_str, pl in user_data.items():
            cnt = sum(1 for c in pl.captured_chars if c.get("name") == found["name"])
            if cnt > 0:
                total += cnt
                capturers.append({
                    "user_id": pl.user_id,
                    "name": pl.name or f"User_{uid_str}",
                    "username": pl.username,
                    "count": cnt,
                })
        capturers.sort(key=lambda x: x["count"], reverse=True)

        cap_lines = []
        for i, st in enumerate(capturers[:15], 1):
            if st["username"]:
                m = f"[{st['name']}](https://t.me/{st['username']})"
            else:
                m = f"[{st['name']}](tg://user?id={st['user_id']})"
            cap_lines.append(f"{i}. {m} - {st['count']}x")
        if len(capturers) > 15:
            cap_lines.append(f"... +{len(capturers) - 15} more")
        cap_text = "\n".join(cap_lines) if cap_lines else "No one captured yet."

        info_text = (
            f"📊 **CHARACTER INFO**\n\n"
            f"👤 **Name:** {found['name']}\n"
            f"⭐ **Rarity:** {ctype}\n"
            f"🆔 **ID:** {found.get('id', 'N/A')}\n"
            f"📦 **Captures:** {total}\n\n"
            f"🏆 **Captured by:**\n{cap_text}\n\n"
            f"🤖 @Grand_Line_Sentinel_bot"
        )

        img = found.get("image")
        if img and isinstance(img, str):
            try:
                if img.startswith(("http://", "https://")):
                    await message.reply_photo(img, caption=info_text)
                    return
                try:
                    await message.reply_photo(img, caption=info_text)
                    return
                except Exception:
                    await message.reply_document(img, caption=info_text)
                    return
            except Exception:
                pass
        await message.reply(info_text)

    # ==================== TOP COMMAND ====================
    @app.on_message(filters.command("top"))
    async def top_cmd(client, message):
        top = sorted(user_data.values(), key=lambda x: x.bounty, reverse=True)[:10]
        if not top:
            await message.reply("No players!")
            return

        text = "🏆 **TOP 10 BOUNTY** 🏆\n────────────────────────────────\n\n"
        for i, p in enumerate(top, 1):
            name = p.name if (p.name and p.name.lower() != "nameless") else f"User_{p.user_id}"
            mention = f"[{name}](https://t.me/{p.username})" if p.username else name
            medal = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {mention}\n   💰 ฿{p.bounty:,}\n\n"
        text += f"────────────────────────────────\n🤖 @Grand_Line_Sentinel_bot"

        if TOP_IMAGE:
            try:
                await message.reply_photo(TOP_IMAGE, caption=text)
                return
            except Exception:
                pass
            try:
                await message.reply_document(TOP_IMAGE, caption=text)
                return
            except Exception:
                pass
        await message.reply(text)

    # ==================== XTOP COMMAND ====================
    @app.on_message(filters.command("xtop"))
    async def xtop_cmd(client, message):
        top = sorted(user_data.values(), key=lambda x: x.level, reverse=True)[:10]
        if not top:
            await message.reply("No players!")
            return

        text = "🏆 **TOP 10 LEVEL** 🏆\n────────────────────────────────\n\n"
        for i, p in enumerate(top, 1):
            name = p.name if (p.name and p.name.lower() != "nameless") else f"User_{p.user_id}"
            mention = f"[{name}](https://t.me/{p.username})" if p.username else name
            medal = "👑" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            text += f"{medal} {mention}\n   ⚔️ Lv.{p.level}\n\n"
        text += f"────────────────────────────────\n🤖 @Grand_Line_Sentinel_bot"

        if TOP_IMAGE:
            try:
                await message.reply_photo(TOP_IMAGE, caption=text)
                return
            except Exception:
                pass
        await message.reply(text)

    # ==================== CLAIM COMMAND ====================
    @app.on_message(filters.command("claim"))
    async def claim_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)

        if message.chat.id != MAIN_GROUP_ID:
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 Join Main Group", url=MAIN_GROUP_LINK)],
                [InlineKeyboardButton("🔄 Check Again", callback_data="try_claim")]
            ])
            await message.reply(
                f"❌ **Use this in the main group!**\n\n{MAIN_GROUP_LINK}",
                reply_markup=kb,
                disable_web_page_preview=True
            )
            return

        if p.claimed_main:
            await message.reply("❌ Already claimed!")
            return

        p.claimed_main = True
        p.bounty += 3_000_000
        p.xp += 200
        p.boost_end = max(p.boost_end, time.time() + 900)

        old_lvl = p.level
        while p.xp >= get_xp_needed(p.level) and p.level < 200:
            p.xp -= get_xp_needed(p.level)
            p.level += 1
        if p.level >= 200:
            p.xp = 0

        save_data()

        if p.level > old_lvl:
            await send_level_up_notification(app, message.from_user.id, old_lvl, p.level, "claim")
            await send_level_up_group_notification(app, message.chat.id, p.name, old_lvl, p.level)

        lt = f"\n\n🎉 **LEVEL UP!** {old_lvl} → {p.level}" if p.level > old_lvl else ""
        await message.reply(
            f"🎁 **CLAIMED!**\n\n"
            f"💰 +฿3,000,000\n"
            f"⭐ +200 XP\n"
            f"⚡ 2x XP (15 min){lt}\n\n"
            f"🏆 ฿{p.bounty:,}\n"
            f"⚔️ Lv.{p.level}"
        )

    # ==================== PVP TOGGLE ====================
    @app.on_message(filters.command("pvp"))
    async def pvp_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        p.pvp_enabled = not p.pvp_enabled
        save_data()
        if p.pvp_enabled:
            await message.reply(f"⚔️ **PVP: ON**\n\nYou can attack and be attacked.")
        else:
            await message.reply(f"🛡️ **PVP: OFF**\n\nYou're safe from attacks.")

    # ==================== PASSIVE TOGGLE ====================
    @app.on_message(filters.command("passive"))
    async def passive_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        p.passive_enabled = not p.passive_enabled
        save_data()
        if p.passive_enabled:
            await message.reply(f"🛡️ **PASSIVE: ON**\n\nShield will protect you.")
        else:
            await message.reply(f"⚔️ **PASSIVE: OFF**\n\nShield won't protect you.")

    # ==================== INFO COMMAND ====================
    @app.on_message(filters.command("info"))
    async def info_cmd(client, message):
        if message.reply_to_message:
            u = message.reply_to_message.from_user
            p = get_player(u.id, user=u)
            player_name = u.first_name
            is_self = False
        else:
            u = message.from_user
            p = get_player(u.id, user=u)
            player_name = u.first_name
            is_self = True

        need = get_xp_needed(p.level)
        rank = get_rank(p.level)

        if p.haki:
            haki_name = HAKI_NAMES.get(p.haki, p.haki)
            haki_line = f"Haki: {haki_name} Lv.{p.haki_level}"
        else:
            haki_line = "Haki: None"

        is_banned = p.user_id in GBANNED
        passive_status = "🟢 ON" if p.passive_enabled else "🔴 OFF"
        pvp_status = "⚔️ ON" if p.pvp_enabled else "🛡️ OFF"

        fruit_display = "None"
        fruit_emoji = "❌"
        if p.devil_fruit:
            found = False
            for category, fruits in DEVIL_FRUITS.items():
                for fruit in fruits:
                    if fruit["full"] == p.devil_fruit:
                        fruit_emoji = "☄️" if category == "Good" else "⚡" if category == "Medium" else "🌀"
                        fruit_display = f"{fruit['name']} ({fruit['model']})"
                        found = True
                        break
                if found:
                    break
            if not found:
                fruit_display = p.devil_fruit

        save_data()

        percent = int((p.xp / need) * 10) if need > 0 else 0
        bar = "█" * percent + "░" * (10 - percent)
        xp_needed = need - p.xp

        sorted_players = sorted(user_data.values(), key=lambda x: x.bounty, reverse=True)
        global_rank = 1
        for i, pl in enumerate(sorted_players, 1):
            if pl.user_id == p.user_id:
                global_rank = i
                break

        shield_text = f"🛡️ Lv.{p.shield_level}" if p.shield_level > 0 else "❌ No"

        ban_warning = ""
        if is_banned:
            ban_warning = "\n⚠️ **GLOBALLY BANNED!** ⚠️\n"

        stats = (
            f"**{player_name}**  [`{p.user_id}`]\n"
            f"──────────────────\n"
            f"Username: @{p.username or 'None'}\n"
            f"Rank: {rank}\n"
            f"Shield: {shield_text}\n"
            f"Passive: {passive_status}\n"
            f"PVP Mode: {pvp_status}\n"
            f"{haki_line}\n"
            f"Global Rank: {global_rank}\n"
            f"──────────────────\n"
            f"Bounty: ฿{p.bounty:,}\n"
            f"Token: ⚜️{p.advanced_token}\n"
            f"Vault: ฿{p.vault:,}/{VAULT_CAPS.get(p.vault_level, 25_000_000):,}\n"
            f"──────────────────\n"
            f"Level: {p.level}\n"
            f"[{bar}] ({xp_needed} XP for next level)\n"
            f"──────────────────\n"
            f"Devil Fruit: {fruit_display} {fruit_emoji}"
            f"{ban_warning}\n"
            f"🤖 @Grand_Line_Sentinel_bot"
        )

        # Poster generation
        if PIL_AVAILABLE and WANTED_IMAGE and os.path.exists(WANTED_IMAGE):
            try:
                poster = Image.open(WANTED_IMAGE).convert("RGB").resize((1000, 1400))

                pfp_path = f"temp/pfp_{p.user_id}.jpg"
                pfp = None
                if os.path.exists(pfp_path):
                    pfp = pfp_path
                else:
                    try:
                        async for photo in client.get_chat_photos(int(p.user_id), limit=1):
                            pfp = await client.download_media(photo.file_id, file_name=pfp_path)
                            break
                    except Exception:
                        pfp = None

                if pfp and os.path.exists(pfp):
                    try:
                        img = Image.open(pfp).convert("RGB")
                        img = ImageOps.fit(img, (820, 588), Image.Resampling.LANCZOS)
                        poster.paste(img, (90, 298))
                    except Exception as e:
                        print(f"[poster pfp] {e}")

                draw = ImageDraw.Draw(poster)

                import unicodedata
                cleaned = "".join(
                    c for c in player_name
                    if unicodedata.category(c)[0] not in ("S", "C")
                ).strip() or f"User {p.user_id}"
                if len(cleaned) > 16:
                    cleaned = cleaned[:15] + "…"
                name_text = cleaned.upper()

                name_font = None
                name_y = 996
                for size in (150, 140, 130, 120, 110, 100, 90, 80, 70, 60):
                    try:
                        f = load_name_font(size)
                        if f is None:
                            continue
                        bbox = draw.textbbox((0, 0), name_text, font=f)
                        if bbox[2] - bbox[0] <= 900:
                            name_font = f
                            name_y = 996 + (150 - size) // 3
                            break
                    except Exception:
                        continue

                if name_font is None:
                    name_font = load_name_font(60) or ImageFont.load_default()
                    name_y = 1015

                try:
                    bbox = draw.textbbox((0, 0), name_text, font=name_font)
                    tw = bbox[2] - bbox[0]
                    x = (1000 - tw) // 2
                    draw.text((x, name_y), name_text, fill=(80, 55, 25), font=name_font)
                except Exception:
                    pass

                bounty_value = p.bounty if isinstance(p.bounty, (int, float)) else 0
                bounty_text = f"{int(bounty_value):,} -"
                RIGHT_X = 950
                LEFT_LIMIT = 450
                max_width = RIGHT_X - LEFT_LIMIT

                digits = len(f"{int(bounty_value):,}")
                size_map = {
                    10: 108, 11: 100, 12: 92, 13: 86, 14: 80,
                    15: 74, 16: 68, 17: 62, 18: 56,
                    19: 50, 20: 44, 21: 38, 22: 32, 23: 26,
                }
                size = size_map.get(digits, 20) if digits > 9 else 110

                bounty_font = load_bounty_font(size) or ImageFont.load_default()

                try:
                    bbox = draw.textbbox((0, 0), bounty_text, font=bounty_font)
                    tw = bbox[2] - bbox[0]
                    attempts = 0
                    while tw > max_width and size > 20 and attempts < 30:
                        size -= 4
                        attempts += 1
                        bounty_font = load_bounty_font(size) or ImageFont.load_default()
                        bbox = draw.textbbox((0, 0), bounty_text, font=bounty_font)
                        tw = bbox[2] - bbox[0]

                    x = max(LEFT_LIMIT, RIGHT_X - tw)
                    y = 1155 + (110 - size) // 4
                    draw.text((x, y), bounty_text, fill=(80, 55, 25), font=bounty_font)
                except Exception as e:
                    print(f"[poster bounty] {e}")

                buf = BytesIO()
                poster.save(buf, format="JPEG", quality=90, optimize=True)
                buf.seek(0)
                buf.name = f"wanted_{p.user_id}.jpg"

                await message.reply_photo(buf, caption=stats)
                return

            except Exception as e:
                print(f"[info poster] {e}")

        await message.reply(stats)

    # ==================== MYCHARS ====================
    @app.on_message(filters.command("mychars"))
    async def my_chars_cmd(client, message):
        user_id = message.from_user.id
        p = get_player(user_id, user=message.from_user)

        if not p.captured_chars:
            await message.reply(
                "📭 **No captured characters yet!**\n\n"
                "Fight spawning characters with `/challenge [name]`!"
            )
            return

        char_counts = {}
        for char in p.captured_chars:
            name = char.get("name", "Unknown")
            char_counts[name] = char_counts.get(name, 0) + 1

        char_list = [{"name": name, "count": count} for name, count in char_counts.items()]

        my_chars_sessions[user_id] = {
            "char_list": char_list,
            "current_page": 0,
        }

        await show_chars_list_page(client, message, user_id, 0)