# callbacks.py
import asyncio
import random
import time
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    BOT_NAME, MAIN_GROUP_ID, MAIN_GROUP_LINK, UPDATE_CHANNEL_LINK,
    UPDATE_CHANNEL_USERNAME, HAKI_NAMES, VAULT_CAPS, NIKA_GIF, NIKA_IMAGE,
    HAKI_IMAGE, FRUIT_IMAGE, SHOP_IMAGE, GIVEAWAY_DM_MIN_PRIZE,
    FRUIT_TIER_PRICES, FRUIT_SELL_REFUNDS, DEVIL_FRUITS,
    get_fruit_icon, get_fruit_tier, normalize_fruit_name,
)
from data_manager import (
    get_player, save_data, user_data, active_giveaways,
    get_bot_groups, get_pending_forward, clear_pending_forward,
    get_trade, remove_trade, normal_characters, mythical_characters,
    get_global_giveaway, get_banned_player_info,
    GBANNED, TEMP_BANNED, save_banned, save_temp_banned,
    remove_banned_player_info, is_admin_or_owner,
)
from utils import get_xp_needed, get_random_fruit
from pvp import (
    send_level_up_notification,
    send_level_up_group_notification,
)


# ==================== HELPERS ====================
async def _safe_photo_or_doc(message, file_id, caption, markup=None):
    """Try photo → document. Returns True if media sent."""
    if not file_id:
        return False
    try:
        await message.reply_photo(file_id, caption=caption, reply_markup=markup)
        return True
    except Exception as e:
        print(f"[media photo] {e}")
    try:
        await message.reply_document(file_id, caption=caption, reply_markup=markup)
        return True
    except Exception as e:
        print(f"[media doc] {e}")
    return False


async def _edit_or_send(callback, text, markup=None, file_id=None):
    """Try to edit existing message; fall back to delete + send."""
    try:
        if file_id:
            try:
                await callback.message.delete()
            except Exception:
                pass
            ok = await _safe_photo_or_doc(callback.message, file_id, text, markup)
            if not ok:
                await callback.message.reply(text, reply_markup=markup)
            return
        await callback.message.edit_text(text, reply_markup=markup)
    except Exception as e:
        print(f"[edit_or_send] {e}")
        try:
            await callback.message.delete()
        except Exception:
            pass
        try:
            await callback.message.reply(text, reply_markup=markup)
        except Exception as e2:
            print(f"[edit_or_send fallback] {e2}")


async def _check_main_and_updates(client, user_id):
    """Return (main_ok, updates_ok) with strict defaults."""
    main_ok = False
    updates_ok = False
    try:
        m = await client.get_chat_member(MAIN_GROUP_ID, user_id)
        if str(m.status).split(".")[-1].upper() in (
            "MEMBER", "ADMINISTRATOR", "OWNER", "CREATOR"
        ):
            main_ok = True
    except Exception as e:
        print(f"[check main] {e}")
    try:
        m = await client.get_chat_member(UPDATE_CHANNEL_USERNAME, user_id)
        if str(m.status).split(".")[-1].upper() in (
            "MEMBER", "ADMINISTRATOR", "OWNER", "CREATOR"
        ):
            updates_ok = True
    except Exception as e:
        print(f"[check updates] {e}")
        updates_ok = False
    return main_ok, updates_ok


_ship_upgrade_locks = set()


def register_callbacks(app):

    @app.on_callback_query()
    async def handle_callback(client, callback):
        try:
            data = callback.data or ""
            uid = callback.from_user.id

            # ==================== MYCHARS PAGINATION ====================
            if data.startswith("chars_page_"):
                try:
                    page = int(data.replace("chars_page_", ""))
                except ValueError:
                    await callback.answer("Invalid page!", show_alert=True)
                    return
                from commands import my_chars_sessions, show_chars_list_page
                if uid not in my_chars_sessions:
                    await callback.answer("Session expired. Use /mychars.", show_alert=True)
                    return
                if show_chars_list_page:
                    await show_chars_list_page(client, callback.message, uid, page)
                await callback.answer()
                return

            # ==================== DELETE THIS ====================
            if data == "delete_this":
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.answer()
                return

            if data == "noop":
                await callback.answer()
                return

            # ==================== CHAR STATS ====================
            if data.startswith("char_stats_"):
                name = data.replace("char_stats_", "")
                found = None
                ctype = None
                for c in mythical_characters:
                    if c.get("name") == name:
                        found, ctype = c, "MYTHICAL"
                        break
                if not found:
                    for c in normal_characters:
                        if c.get("name") == name:
                            found, ctype = c, "NORMAL"
                            break
                if not found:
                    await callback.answer("Not found!", show_alert=True)
                    return

                caps = []
                for pl in user_data.values():
                    cnt = sum(1 for c in pl.captured_chars if c.get("name") == name)
                    if cnt > 0:
                        caps.append({
                            "user_id": pl.user_id,
                            "name": pl.name or f"User_{pl.user_id}",
                            "username": pl.username,
                            "count": cnt,
                        })
                caps.sort(key=lambda x: x["count"], reverse=True)
                total = sum(c["count"] for c in caps)

                text = (
                    f"**{name} STATS**\n\n"
                    f"Rarity: {ctype}\n"
                    f"ID: {found.get('id', 'N/A')}\n"
                    f"Total captures: {total}\n\n"
                    f"**CAPTURERS ({len(caps)}):**\n"
                )
                for i, c in enumerate(caps[:30], 1):
                    if c["username"]:
                        m = f"[{c['name']}](https://t.me/{c['username']})"
                    else:
                        m = f"[{c['name']}](tg://user?id={c['user_id']})"
                    text += f"{i}. {m} — {c['count']}x\n"
                if len(caps) > 30:
                    text += f"\n... +{len(caps) - 30} more"
                text += f"\n\n{BOT_NAME}"

                img = found.get("image")
                if img:
                    await _safe_photo_or_doc(callback.message, img, text)
                else:
                    await callback.message.reply(text)
                await callback.answer()
                return

            # ==================== CHECK MEMBERSHIP ====================
            if data == "check_membership":
                main_ok, updates_ok = await _check_main_and_updates(client, uid)
                text = (
                    "**MEMBERSHIP**\n\n"
                    f"Main Group: {'Yes' if main_ok else 'No'}\n"
                    f"Updates: {'Yes' if updates_ok else 'No'}\n\n"
                )
                if main_ok and updates_ok:
                    text += "You're all set! Use `/claim` in the main group."
                else:
                    text += "Join both to unlock everything!"
                await callback.message.reply(text)
                await callback.answer()
                return

            # ==================== TRY CLAIM ====================
            if data == "try_claim":
                main_ok, _ = await _check_main_and_updates(client, uid)
                if not main_ok:
                    kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("Join Main Group", url=MAIN_GROUP_LINK)],
                        [InlineKeyboardButton("Check Again", callback_data="try_claim")],
                    ])
                    await callback.message.reply(
                        "❌ **Join main group first!**",
                        reply_markup=kb,
                    )
                    await callback.answer("❌ Not joined!", show_alert=True)
                    return

                p = get_player(uid)
                if p.claimed_main:
                    await callback.message.reply("✅ **Already verified!**")
                    await callback.answer()
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

                lt = f"\n\nLEVEL UP! {old_lvl} → {p.level}" if p.level > old_lvl else ""
                await callback.message.edit_text(
                    f"**CLAIMED!**\n\n"
                    f"+฿3,000,000\n"
                    f"+200 XP\n"
                    f"2x XP (15 min){lt}\n\n"
                    f"฿{p.bounty:,}\n"
                    f"Lv.{p.level}"
                )
                if p.level > old_lvl:
                    asyncio.create_task(send_level_up_notification(
                        client, uid, old_lvl, p.level, "claim"
                    ))
                    asyncio.create_task(send_level_up_group_notification(
                        client, callback.message.chat.id, p.name, old_lvl, p.level
                    ))
                await callback.answer("✅ Claimed!", show_alert=True)
                return

            # ==================== SHOP BACK ====================
            if data == "shop_back":
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Haki", callback_data="shop_haki")],
                    [InlineKeyboardButton("Shield", callback_data="shop_shield")],
                    [InlineKeyboardButton("Devil Fruit", callback_data="shop_fruit")],
                    [InlineKeyboardButton("Vault Upgrade", callback_data="shop_vault")],
                    [InlineKeyboardButton("2x XP (50M)", callback_data="shop_boost")],
                    [InlineKeyboardButton("Switch Haki", callback_data="shop_switch_haki")],
                ])
                text = f"**SHOP**\n\nSelect a category.\n\n{BOT_NAME}"
                await _edit_or_send(callback, text, kb, SHOP_IMAGE)
                await callback.answer()
                return

            # ==================== HAKI SHOP ====================
            if data == "shop_haki":
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Observation (25M)", callback_data="buy_haki_obv")],
                    [InlineKeyboardButton("Armament (25M)", callback_data="buy_haki_arm")],
                    [InlineKeyboardButton("Conqueror's (25M)", callback_data="buy_haki_conq")],
                    [InlineKeyboardButton("Back", callback_data="shop_back")],
                ])
                text = (
                    f"**HAKI SHOP**\n\n"
                    f"**Price:** ฿25,000,000 each\n\n"
                    f"**Observation** — dodge in games (Lv.3+ = advanced)\n"
                    f"**Armament** — PVP damage\n"
                    f"**Conqueror's** — PVP dominance\n\n"
                    f"Upgrade with `/upgradehaki`\n"
                    f"Check details with `/haki`\n\n"
                    f"{BOT_NAME}"
                )
                await _edit_or_send(callback, text, kb, HAKI_IMAGE)
                await callback.answer()
                return

            # ==================== SHIELD SHOP ====================
            if data == "shop_shield":
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Lv1 (25M)", callback_data="buy_shield_1")],
                    [InlineKeyboardButton("Lv2 (250M)", callback_data="buy_shield_2")],
                    [InlineKeyboardButton("Lv3 (25B)", callback_data="buy_shield_3")],
                    [InlineKeyboardButton("Back", callback_data="shop_back")],
                ])
                text = (
                    f"**SHIELD SHOP**\n\n"
                    f"Lv1 — ฿25M (3 uses)\n"
                    f"Lv2 — ฿250M (3 uses)\n"
                    f"Lv3 — ฿25B (3 uses)\n\n"
                    f"{BOT_NAME}"
                )
                await _edit_or_send(callback, text, kb, SHOP_IMAGE)
                await callback.answer()
                return

            # ==================== FRUIT SHOP ====================
            if data == "shop_fruit":
                p = get_player(uid)
                current = ""
                if p.devil_fruit:
                    icon = get_fruit_icon(p.devil_fruit)
                    current = f"\nYou already have: {icon} {p.devil_fruit}\n"

                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"{FRUIT_TIER_PRICES['Bad']:,}", callback_data="buy_fruit_1")],
                    [InlineKeyboardButton(f"{FRUIT_TIER_PRICES['Medium']:,}", callback_data="buy_fruit_2")],
                    [InlineKeyboardButton(f"{FRUIT_TIER_PRICES['Good']:,}", callback_data="buy_fruit_3")],
                    [InlineKeyboardButton("Back", callback_data="shop_back")],
                ])

                text = (
                    f"**FRUIT SHOP**\n\n"
                    f"**Random Devil Fruit**\n"
                    f"Pick your gamble:\n\n"
                    f"• ฿{FRUIT_TIER_PRICES['Bad']:,}\n"
                    f"• ฿{FRUIT_TIER_PRICES['Medium']:,}\n"
                    f"• ฿{FRUIT_TIER_PRICES['Good']:,}\n"
                    f"{current}\n"
                    f"{BOT_NAME}"
                )
                await _edit_or_send(callback, text, kb, FRUIT_IMAGE)
                await callback.answer()
                return

            # ==================== VAULT SHOP ====================
            if data == "shop_vault":
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Lv2 (25B)", callback_data="buy_vault_2")],
                    [InlineKeyboardButton("Lv3 (500B)", callback_data="buy_vault_3")],
                    [InlineKeyboardButton("Back", callback_data="shop_back")],
                ])
                text = (
                    f"**VAULT SHOP**\n\n"
                    f"Lv2 — ฿25B (25B cap)\n"
                    f"Lv3 — ฿500B (500B cap)\n\n"
                    f"{BOT_NAME}"
                )
                await _edit_or_send(callback, text, kb, SHOP_IMAGE)
                await callback.answer()
                return

            # ==================== BOOST ====================
            if data == "shop_boost":
                p = get_player(uid)
                if p.boost_end > time.time():
                    rem = int(p.boost_end - time.time())
                    await callback.answer(
                        f"Active boost! {rem // 60}m {rem % 60}s left",
                        show_alert=True,
                    )
                    return

                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Confirm (50M)", callback_data="confirm_boost")],
                    [InlineKeyboardButton("Cancel", callback_data="shop_back")],
                ])
                text = (
                    f"**2x XP BOOST**\n\n"
                    f"฿50,000,000\n"
                    f"15 minutes\n"
                    f"Double XP from all games\n\n"
                    f"Your bounty: ฿{p.bounty:,}\n\n"
                    f"Confirm?"
                )
                await _edit_or_send(callback, text, kb, SHOP_IMAGE)
                await callback.answer()
                return

            if data == "confirm_boost":
                p = get_player(uid)
                if p.boost_end > time.time():
                    await callback.answer("Already active!", show_alert=True)
                    return
                if p.bounty < 50_000_000:
                    await callback.answer("❌ Need ฿50M!", show_alert=True)
                    return
                p.bounty -= 50_000_000
                p.boost_end = max(p.boost_end, time.time() + 900)
                save_data()
                await callback.message.edit_text(
                    f"**2x XP ACTIVATED!**\n\n"
                    f"15 minutes\n"
                    f"฿{p.bounty:,} left"
                )
                await callback.answer("✅ Activated!", show_alert=True)
                return

            # ==================== SWITCH HAKI ====================
            if data == "shop_switch_haki":
                p = get_player(uid)
                current_name = HAKI_NAMES.get(p.haki, "None") if p.haki else "None"
                options = [
                    (None, "switch_haki_none", "None"),
                    ("obv", "switch_haki_obv", "Observation"),
                    ("arm", "switch_haki_arm", "Armament"),
                    ("conq", "switch_haki_conq", "Conqueror's"),
                ]
                kb = []
                for key, cb, disp in options:
                    if p.haki == key:
                        kb.append([InlineKeyboardButton(f"{disp} (Current)", callback_data=cb)])
                    else:
                        kb.append([InlineKeyboardButton(disp, callback_data=cb)])
                kb.append([InlineKeyboardButton("Back", callback_data="shop_back")])

                current = f"**{current_name}** Lv.{p.haki_level}" if p.haki else "**None**"
                text = (
                    f"**SWITCH HAKI**\n\n"
                    f"Current: {current}\n\n"
                    f"Switch to a Haki: ฿5,000,000\n"
                    f"Unequip: FREE\n\n"
                    f"Select:"
                )
                await _edit_or_send(callback, text, InlineKeyboardMarkup(kb), HAKI_IMAGE)
                await callback.answer()
                return

            if data.startswith("switch_haki_"):
                haki_type = data.replace("switch_haki_", "")
                p = get_player(uid)

                if (haki_type == "none" and p.haki is None) or (
                    haki_type != "none" and p.haki == haki_type
                ):
                    await callback.answer("Already have this!", show_alert=True)
                    return

                if haki_type != "none":
                    if p.bounty < 5_000_000:
                        await callback.answer("❌ Need ฿5M!", show_alert=True)
                        return
                    p.bounty -= 5_000_000

                if haki_type == "none":
                    p.haki = None
                    p.haki_level = 0
                    p.advanced_haki = False
                    note = "unequipped (free)"
                else:
                    p.haki = haki_type
                    if p.haki_level == 0:
                        p.haki_level = 1
                    p.advanced_haki = (p.haki_level >= 3)
                    note = "equipped (cost ฿5M)"

                save_data()
                new_name = HAKI_NAMES.get(p.haki, "None") if p.haki else "None"
                lvl = f" Lv.{p.haki_level}" if p.haki else ""
                await callback.message.edit_text(
                    f"✅ **Haki Switched!**\n\n"
                    f"Now: **{new_name}**{lvl}\n"
                    f"Left: ฿{p.bounty:,}\n"
                    f"*({note})*"
                )
                await callback.answer("✅ Switched!", show_alert=True)
                return

            # ==================== BUY HAKI ====================
            if data.startswith("buy_haki_"):
                haki_type = data.replace("buy_haki_", "")
                p = get_player(uid)
                if p.haki:
                    await callback.answer("Already have Haki! Use Switch.", show_alert=True)
                    return
                if p.bounty < 25_000_000:
                    await callback.answer("❌ Need ฿25M!", show_alert=True)
                    return
                p.bounty -= 25_000_000
                p.haki = haki_type
                p.haki_level = 1
                p.advanced_haki = False
                save_data()
                await callback.message.edit_text(
                    f"✅ **You got {HAKI_NAMES.get(haki_type, haki_type)} Haki!**\n\n"
                    f"฿{p.bounty:,} left\n\n"
                    f"Upgrade with `/upgradehaki`"
                )
                await callback.answer("✅ Haki obtained!", show_alert=True)
                return

            # ==================== CONFIRM HAKI UPGRADE ====================
            if data.startswith("confirm_upgrade_haki_"):
                ht = data.replace("confirm_upgrade_haki_", "")
                p = get_player(uid)
                if p.haki != ht:
                    await callback.answer("❌ Don't have this Haki!", show_alert=True)
                    return
                if p.haki_level >= 5:
                    await callback.answer("❌ Max level!", show_alert=True)
                    return
                from haki_commands import haki_upgrade_cost
                cost = haki_upgrade_cost(p.haki_level)
                if cost is None or p.bounty < cost:
                    await callback.answer(f"❌ Need ฿{cost:,}!", show_alert=True)
                    return
                p.bounty -= cost
                p.haki_level += 1
                p.advanced_haki = (p.haki_level >= 3)
                save_data()
                extra = ""
                if p.haki_level == 3:
                    extra = "\n\nADVANCED HAKI UNLOCKED!"
                await callback.message.edit_text(
                    f"✅ **Haki Upgraded!**\n\n"
                    f"{HAKI_NAMES.get(p.haki, p.haki)} → Lv.{p.haki_level}\n"
                    f"Cost: ฿{cost:,}\n"
                    f"Left: ฿{p.bounty:,}"
                    f"{extra}"
                )
                await callback.answer("✅ Upgraded!", show_alert=True)
                return

            # ==================== CONFIRM SELL HAKI ====================
            if data.startswith("confirm_sell_haki_"):
                ht = data.replace("confirm_sell_haki_", "")
                p = get_player(uid)
                if p.haki != ht:
                    await callback.answer("❌ Don't have this Haki!", show_alert=True)
                    return
                refund = 12_500_000
                p.bounty += refund
                p.haki = None
                p.haki_level = 0
                p.advanced_haki = False
                save_data()
                await callback.message.edit_text(
                    f"✅ **Haki Sold!**\n\n"
                    f"+฿{refund:,}\n"
                    f"Bounty: ฿{p.bounty:,}"
                )
                await callback.answer("✅ Sold!", show_alert=True)
                return

            # ==================== BUY SHIELD ====================
            if data.startswith("buy_shield_"):
                level = int(data.replace("buy_shield_", ""))
                price = {1: 25_000_000, 2: 250_000_000, 3: 25_000_000_000}[level]
                p = get_player(uid)
                if p.bounty < price:
                    await callback.answer(f"❌ Need ฿{price:,}!", show_alert=True)
                    return
                p.bounty -= price
                p.shield_level = level
                p.shield_uses = 3
                save_data()
                await callback.message.edit_text(
                    f"✅ **Shield Lv{level} obtained!**\n\n"
                    f"฿{p.bounty:,} left"
                )
                await callback.answer("✅ Obtained!", show_alert=True)
                return

            # ==================== BUY FRUIT ====================
            if data.startswith("buy_fruit_"):
                tier_num = int(data.replace("buy_fruit_", ""))
                tier_map = {1: "Bad", 2: "Medium", 3: "Good"}
                category = tier_map.get(tier_num, "Bad")
                price = FRUIT_TIER_PRICES[category]

                p = get_player(uid)
                if p.bounty < price:
                    await callback.answer(f"❌ Need ฿{price:,}!", show_alert=True)
                    return
                if p.devil_fruit:
                    await callback.answer("❌ Already have a fruit!", show_alert=True)
                    return

                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Confirm", callback_data=f"confirm_fruit_{tier_num}")],
                    [InlineKeyboardButton("Cancel", callback_data="shop_fruit")],
                ])
                await callback.message.edit_text(
                    f"**Confirm Purchase**\n\n"
                    f"Price: ฿{price:,}\n"
                    f"Your Bounty: ฿{p.bounty:,}\n\n"
                    f"You'll get a **random** Devil Fruit!\n\n"
                    f"Confirm?",
                    reply_markup=kb,
                )
                await callback.answer()
                return

            if data.startswith("confirm_fruit_"):
                tier_num = int(data.replace("confirm_fruit_", ""))
                tier_map = {1: "Bad", 2: "Medium", 3: "Good"}
                category = tier_map.get(tier_num, "Bad")
                price = FRUIT_TIER_PRICES[category]

                p = get_player(uid)
                if p.bounty < price or p.devil_fruit:
                    await callback.answer("❌ Purchase failed!", show_alert=True)
                    return

                p.bounty -= price
                fruit = random.choice(DEVIL_FRUITS[category])
                p.devil_fruit = fruit["full"]
                p.fruit_category = category
                save_data()

                icon = get_fruit_icon(fruit["full"])
                await callback.message.edit_text(
                    f"{icon} **You got {fruit['full']}!**\n\n"
                    f"Type: {fruit['type']}\n"
                    f"Bounty left: ฿{p.bounty:,}"
                )

                if fruit["full"] == "Gomu Gomu no Mi, Model: Nika" and not p.nika_awakened:
                    p.nika_awakened = True
                    save_data()
                    if NIKA_GIF:
                        try:
                            await callback.message.reply_animation(
                                NIKA_GIF, caption="GEAR 5 — NIKA AWAKENING!"
                            )
                            await asyncio.sleep(2)
                        except Exception:
                            pass
                    await callback.message.reply(
                        f"*Drum of Liberation...*\n\n"
                        f"**{p.name}**'s heart beats to freedom!\n\n"
                        f"**AWAKENING!**"
                    )
                    await asyncio.sleep(1)
                    if NIKA_IMAGE:
                        try:
                            await callback.message.reply_photo(
                                NIKA_IMAGE,
                                caption=f"**{p.name}** — Joy Boy's Successor!",
                            )
                        except Exception:
                            pass

                await callback.answer(f"Got {fruit['full']}!", show_alert=True)
                return

            # ==================== BUY VAULT ====================
            if data.startswith("buy_vault_"):
                level = int(data.replace("buy_vault_", ""))
                price = {2: 25_000_000_000, 3: 500_000_000_000}[level]
                p = get_player(uid)
                if level > p.vault_level and p.bounty >= price:
                    kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("Confirm", callback_data=f"confirm_vault_{level}")],
                        [InlineKeyboardButton("Cancel", callback_data="shop_vault")],
                    ])
                    await callback.message.edit_text(
                        f"**Confirm**\n\n"
                        f"Vault Lv{level} — cap ฿{VAULT_CAPS[level]:,}\n"
                        f"Price: ฿{price:,}\n\n"
                        f"Confirm?",
                        reply_markup=kb,
                    )
                    await callback.answer()
                    return
                await callback.answer(f"❌ Need ฿{price:,}!", show_alert=True)
                return

            if data.startswith("confirm_vault_"):
                level = int(data.replace("confirm_vault_", ""))
                price = {2: 25_000_000_000, 3: 500_000_000_000}[level]
                p = get_player(uid)
                if level > p.vault_level and p.bounty >= price:
                    p.bounty -= price
                    p.vault_level = level
                    save_data()
                    await callback.message.edit_text(
                        f"✅ **Vault Lv{level}!**\n\n"
                        f"Cap: ฿{VAULT_CAPS[level]:,}\n"
                        f"฿{p.bounty:,} left"
                    )
                    await callback.answer("✅ Upgraded!", show_alert=True)
                    return
                await callback.answer("❌ Failed!", show_alert=True)
                return

            # ==================== TRADE ====================
            if data.startswith("trade_select_"):
                parts = data.replace("trade_select_", "").rsplit("_", 1)
                if len(parts) != 2:
                    await callback.answer("Invalid!", show_alert=True)
                    return
                trade_id, idx_str = parts
                try:
                    idx = int(idx_str)
                except ValueError:
                    await callback.answer("Invalid!", show_alert=True)
                    return

                trade = get_trade(trade_id)
                if trade is None:
                    await callback.answer("❌ Trade expired!", show_alert=True)
                    return
                if callback.from_user.id != trade["seller_id"]:
                    await callback.answer("❌ Only seller can select!", show_alert=True)
                    return
                if idx >= len(trade["chars"]):
                    await callback.answer("❌ Invalid selection!", show_alert=True)
                    return

                sel = trade["chars"][idx]
                trade["selected_char"] = sel

                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Confirm", callback_data=f"trade_confirm_{trade_id}")],
                    [InlineKeyboardButton("Cancel", callback_data=f"trade_cancel_{trade_id}")],
                ])
                s_name = get_player(trade["seller_id"]).name or "Seller"
                b_name = get_player(trade["buyer_id"]).name or "Buyer"

                await callback.message.edit_text(
                    f"**TRADE READY**\n\n"
                    f"Seller: {s_name}\n"
                    f"Buyer: {b_name}\n"
                    f"Character: **{sel.get('name', '?')}**\n"
                    f"Price: ฿{trade['amount']:,}\n\n"
                    f"Buyer, confirm!",
                    reply_markup=kb,
                )
                await callback.answer()
                return

            if data.startswith("trade_confirm_"):
                trade_id = data.replace("trade_confirm_", "")
                trade = get_trade(trade_id)
                if trade is None:
                    await callback.answer("❌ Trade expired!", show_alert=True)
                    return
                if callback.from_user.id != trade["buyer_id"]:
                    await callback.answer("❌ Only buyer can confirm!", show_alert=True)
                    return
                if trade["selected_char"] is None:
                    await callback.answer("❌ Seller hasn't selected!", show_alert=True)
                    return

                seller = get_player(trade["seller_id"])
                buyer = get_player(trade["buyer_id"])

                if buyer.bounty < trade["amount"]:
                    await callback.answer(f"❌ Need ฿{trade['amount']:,}!", show_alert=True)
                    return

                buyer.bounty -= trade["amount"]
                seller.bounty += trade["amount"]

                sel_id = trade["selected_char"].get("id")
                sel_name = trade["selected_char"].get("name")

                if sel_id is not None:
                    seller.captured_chars = [
                        c for c in seller.captured_chars if c.get("id") != sel_id
                    ]
                else:
                    removed = False
                    new_list = []
                    for c in seller.captured_chars:
                        if not removed and c.get("name") == sel_name:
                            removed = True
                            continue
                        new_list.append(c)
                    seller.captured_chars = new_list

                buyer.captured_chars.append(trade["selected_char"].copy())
                save_data()
                remove_trade(trade_id)

                s_name = seller.name or "Seller"
                b_name = buyer.name or "Buyer"
                await callback.message.edit_text(
                    f"✅ **TRADE COMPLETED!**\n\n"
                    f"{sel_name}\n"
                    f"฿{trade['amount']:,}\n\n"
                    f"{s_name}: ฿{seller.bounty:,}\n"
                    f"{b_name}: ฿{buyer.bounty:,}"
                )
                await callback.answer("✅ Done!", show_alert=True)
                return

            if data.startswith("trade_cancel_"):
                trade_id = data.replace("trade_cancel_", "")
                remove_trade(trade_id)
                await callback.message.edit_text("❌ **Trade cancelled!**")
                await callback.answer("Cancelled!", show_alert=True)
                return

            # ==================== GIVEAWAY: JOIN ====================
            if data == "join_tgiveaway":
                key = f"{callback.message.chat.id}_{callback.message.id}"
                if key not in active_giveaways:
                    await callback.answer("❌ Giveaway ended!", show_alert=True)
                    return
                g = active_giveaways[key]
                if uid in g["participants"]:
                    await callback.answer("✅ Already joined!", show_alert=True)
                    return
                g["participants"].append(uid)
                cnt = len(g["participants"])
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"Joined! ({cnt})", callback_data="join_tgiveaway")],
                    [InlineKeyboardButton("Participants", callback_data="view_tparticipants")],
                ])
                try:
                    await callback.message.edit_reply_markup(reply_markup=kb)
                except Exception:
                    pass
                await callback.answer(f"✅ Joined! Total: {cnt}", show_alert=True)
                return

            if data == "view_tparticipants":
                key = f"{callback.message.chat.id}_{callback.message.id}"
                g = active_giveaways.get(key)
                if not g:
                    await callback.answer("Not found!", show_alert=True)
                    return
                parts = g["participants"]
                if not parts:
                    await callback.answer("No participants!", show_alert=True)
                    return
                lines = []
                for i, u in enumerate(parts[:20], 1):
                    try:
                        user = await client.get_users(u)
                        lines.append(f"{i}. {user.first_name}")
                    except Exception:
                        lines.append(f"{i}. `{u}`")
                text = f"**Participants ({len(parts)})**\n\n" + "\n".join(lines)
                if len(parts) > 20:
                    text += f"\n\n+{len(parts) - 20} more"
                await callback.message.reply(text)
                await callback.answer()
                return

            # ==================== CANCEL GIVEAWAY ====================
            if data.startswith("confirm_cancel_giveaway_"):
                key = data.replace("confirm_cancel_giveaway_", "")
                g = active_giveaways.get(key)
                if g:
                    del active_giveaways[key]
                    await callback.message.edit_text(
                        f"✅ **Cancelled!**\n\n"
                        f"Prize: ฿{g['total_prize']:,}\n"
                        f"Participants: {len(g['participants'])}"
                    )
                else:
                    await callback.message.edit_text("❌ Already ended!")
                await callback.answer("Cancelled!", show_alert=True)
                return

            if data == "cancel_cancel_giveaway":
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.answer("Aborted!", show_alert=True)
                return

            # ==================== GLOBAL GIVEAWAY ====================
            if data == "join_global_giveaway":
                gg = get_global_giveaway()
                if gg is None:
                    await callback.answer("❌ No active giveaway!", show_alert=True)
                    return
                if uid in gg["participants"]:
                    await callback.answer("✅ Already joined!", show_alert=True)
                    return

                main_ok, updates_ok = await _check_main_and_updates(client, uid)
                if not main_ok or not updates_ok:
                    missing = []
                    if not main_ok:
                        missing.append("Main Group")
                    if not updates_ok:
                        missing.append("Updates Channel")
                    kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("Join Main", url=MAIN_GROUP_LINK)],
                        [InlineKeyboardButton("Join Updates", url=UPDATE_CHANNEL_LINK)],
                        [InlineKeyboardButton("Verify & Join", callback_data="verify_global_giveaway")],
                    ])
                    await callback.message.reply(
                        f"❌ **Join: {', '.join(missing)}**",
                        reply_markup=kb,
                    )
                    await callback.answer()
                    return

                gg["participants"].append(uid)
                cnt = len(gg["participants"])
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton(f"Joined! ({cnt})", callback_data="join_global_giveaway")],
                    [InlineKeyboardButton("Participants", callback_data="view_global_participants")],
                ])
                try:
                    await callback.message.edit_reply_markup(reply_markup=kb)
                except Exception:
                    pass
                await callback.answer(f"✅ Joined! Total: {cnt}", show_alert=True)
                return

            if data == "verify_global_giveaway":
                gg = get_global_giveaway()
                if gg is None:
                    await callback.answer("❌ No giveaway!", show_alert=True)
                    try:
                        await callback.message.delete()
                    except Exception:
                        pass
                    return
                if uid in gg["participants"]:
                    await callback.answer("✅ Already joined!", show_alert=True)
                    try:
                        await callback.message.delete()
                    except Exception:
                        pass
                    return

                main_ok, updates_ok = await _check_main_and_updates(client, uid)
                if not main_ok or not updates_ok:
                    missing = []
                    if not main_ok:
                        missing.append("Main Group")
                    if not updates_ok:
                        missing.append("Updates Channel")
                    await callback.answer(f"❌ Join: {', '.join(missing)}", show_alert=True)
                    return

                gg["participants"].append(uid)
                cnt = len(gg["participants"])
                await callback.message.edit_text(
                    f"✅ **Joined!**\n\n"
                    f"฿{gg['total_prize']:,}\n"
                    f"Total: {cnt}\n\n"
                    f"Good luck!"
                )
                await callback.answer("✅ Joined!", show_alert=True)
                return

            if data == "view_global_participants":
                gg = get_global_giveaway()
                if gg is None:
                    await callback.answer("❌ No giveaway!", show_alert=True)
                    return
                parts = gg["participants"]
                if not parts:
                    await callback.answer("No participants!", show_alert=True)
                    return
                lines = []
                for i, u in enumerate(parts[:20], 1):
                    try:
                        user = await client.get_users(u)
                        lines.append(f"{i}. {user.first_name}")
                    except Exception:
                        lines.append(f"{i}. `{u}`")
                text = f"**Participants ({len(parts)})**\n\n" + "\n".join(lines)
                if len(parts) > 20:
                    text += f"\n\n+{len(parts) - 20} more"
                await callback.message.reply(text)
                await callback.answer()
                return

            if data == "confirm_cancel_global_giveaway":
                gg = get_global_giveaway()
                if gg is None:
                    await callback.message.edit_text("❌ No active giveaway!")
                    await callback.answer()
                    return
                prize = gg["total_prize"]
                cnt = len(gg["participants"])
                from data_manager import clear_global_giveaway
                clear_global_giveaway()
                await callback.message.edit_text(
                    f"✅ **Global Giveaway Cancelled!**\n\n"
                    f"฿{prize:,}\n"
                    f"{cnt} participants"
                )
                await callback.answer("Cancelled!", show_alert=True)
                return

            if data == "cancel_cancel_global_giveaway":
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.answer("Aborted!", show_alert=True)
                return

            # ==================== BROADCAST ====================
            if data.startswith("confirm_broadcast_"):
                target = data.replace("confirm_broadcast_", "")
                orig = None
                if callback.message.reply_to_message:
                    orig = callback.message.reply_to_message
                else:
                    try:
                        async for msg in client.get_chat_history(
                            callback.message.chat.id, limit=10
                        ):
                            if msg.text and msg.text.startswith("/broadcast") and msg.reply_to_message:
                                orig = msg.reply_to_message
                                break
                    except Exception:
                        pass

                if not orig:
                    await callback.answer("No message!", show_alert=True)
                    return

                status = await callback.message.edit_text(
                    f"Broadcasting to {target.upper()}..."
                )

                g_ok = g_fail = u_ok = u_fail = 0

                async def _send(cid):
                    if orig.text:
                        await client.send_message(cid, orig.text)
                    elif orig.photo:
                        await client.send_photo(cid, orig.photo.file_id, caption=orig.caption)
                    elif orig.video:
                        await client.send_video(cid, orig.video.file_id, caption=orig.caption)
                    elif orig.animation:
                        await client.send_animation(cid, orig.animation.file_id, caption=orig.caption)
                    else:
                        await orig.copy(cid)

                if target in ("groups", "all"):
                    for gid in list(get_bot_groups()):
                        try:
                            await _send(gid)
                            g_ok += 1
                            await asyncio.sleep(0.3)
                        except Exception:
                            g_fail += 1

                if target in ("users", "all"):
                    for uid_str in list(user_data.keys()):
                        try:
                            u = int(uid_str)
                            if u == client.me.id:
                                continue
                            await _send(u)
                            u_ok += 1
                            await asyncio.sleep(0.1)
                        except Exception:
                            u_fail += 1

                result = f"✅ **DONE!**\n\nTarget: {target.upper()}\n"
                if target in ("groups", "all"):
                    result += f"Groups: OK {g_ok} FAIL {g_fail}\n"
                if target in ("users", "all"):
                    result += f"Users: OK {u_ok} FAIL {u_fail}\n"
                await status.edit_text(result)
                await callback.answer("Done!", show_alert=True)
                return

            if data == "cancel_broadcast":
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.answer("Cancelled!", show_alert=True)
                return

            # ==================== FORWARD ====================
            if data == "confirm_forwardall":
                fd = get_pending_forward(uid)
                if not fd:
                    await callback.answer("No pending forward!", show_alert=True)
                    return
                try:
                    orig = await client.get_messages(fd["chat_id"], fd["message_id"])
                except Exception:
                    await callback.answer("Failed to fetch!", show_alert=True)
                    return
                clear_pending_forward(uid)

                status = await callback.message.edit_text("Forwarding...")
                g_ok = g_fail = u_ok = u_fail = 0

                for gid in list(get_bot_groups()):
                    try:
                        await orig.copy(gid)
                        g_ok += 1
                        await asyncio.sleep(0.3)
                    except Exception:
                        g_fail += 1

                for uid_str in list(user_data.keys()):
                    try:
                        u = int(uid_str)
                        if u == client.me.id:
                            continue
                        await orig.copy(u)
                        u_ok += 1
                        await asyncio.sleep(0.1)
                    except Exception:
                        u_fail += 1

                await status.edit_text(
                    f"✅ **DONE!**\n\n"
                    f"Groups: OK {g_ok} FAIL {g_fail}\n"
                    f"Users: OK {u_ok} FAIL {u_fail}"
                )
                await callback.answer("Done!", show_alert=True)
                return

            if data == "confirm_forwardgroups":
                fd = get_pending_forward(uid)
                if not fd:
                    await callback.answer("No pending!", show_alert=True)
                    return
                try:
                    orig = await client.get_messages(fd["chat_id"], fd["message_id"])
                except Exception:
                    await callback.answer("Failed!", show_alert=True)
                    return
                clear_pending_forward(uid)

                status = await callback.message.edit_text("Forwarding...")
                g_ok = g_fail = 0
                for gid in list(get_bot_groups()):
                    try:
                        await orig.copy(gid)
                        g_ok += 1
                        await asyncio.sleep(0.3)
                    except Exception:
                        g_fail += 1
                await status.edit_text(f"✅ **DONE!**\n\nOK {g_ok} FAIL {g_fail}")
                await callback.answer("Done!", show_alert=True)
                return

            if data == "confirm_forwardusers":
                fd = get_pending_forward(uid)
                if not fd:
                    await callback.answer("No pending!", show_alert=True)
                    return
                try:
                    orig = await client.get_messages(fd["chat_id"], fd["message_id"])
                except Exception:
                    await callback.answer("Failed!", show_alert=True)
                    return
                clear_pending_forward(uid)

                status = await callback.message.edit_text("Forwarding...")
                u_ok = u_fail = 0
                for uid_str in list(user_data.keys()):
                    try:
                        u = int(uid_str)
                        if u == client.me.id:
                            continue
                        await orig.copy(u)
                        u_ok += 1
                        await asyncio.sleep(0.1)
                    except Exception:
                        u_fail += 1
                await status.edit_text(f"✅ **DONE!**\n\nOK {u_ok} FAIL {u_fail}")
                await callback.answer("Done!", show_alert=True)
                return

            if data == "cancel_forwardall":
                clear_pending_forward(uid)
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.answer("Cancelled!", show_alert=True)
                return

            # ==================== CREW MENUS ====================
            if data.startswith("crewmenu_"):
                from crew import (
                    get_player_crew, can_manage, is_captain,
                    _build_crew_overview, SHIPS, _safe_ship_tier,
                )
                crew = get_player_crew(uid)
                if not crew:
                    await callback.answer("❌ No crew!", show_alert=True)
                    return

                sub = data.replace("crewmenu_", "")

                if sub == "bank":
                    await callback.message.reply(
                        f"**Crew Bank:** ฿{int(crew.get('bank', 0) or 0):,}\n\n"
                        f"`/crewbank deposit [amount]`\n"
                        f"`/crewbank withdraw [amount]` *(Officer+)*"
                    )
                    await callback.answer()
                    return

                if sub == "members":
                    await callback.message.reply(await _build_crew_overview(crew, detailed=True))
                    await callback.answer()
                    return

                if sub == "invite":
                    if not can_manage(uid, crew):
                        await callback.answer("❌ Officers only!", show_alert=True)
                        return
                    await callback.message.reply("Reply to a user with `/crewinvite`.")
                    await callback.answer()
                    return

                if sub == "ship":
                    tier = _safe_ship_tier(crew)
                    ship = SHIPS[tier]
                    await callback.message.reply(
                        f"**Current Ship:** {ship['emoji']} {ship['name']} (Tier {tier})\n\n"
                        f"`/ship` — Full details\n"
                        f"`/shipupgrade` — Upgrade *(Captain only)*\n"
                        f"`/shiplist` — All tiers"
                    )
                    await callback.answer()
                    return

                if sub == "manage":
                    if not is_captain(uid, crew):
                        await callback.answer("❌ Captain only!", show_alert=True)
                        return
                    await callback.message.reply(
                        "**Manage**\n\n"
                        "`/crewkick` — Kick (reply)\n"
                        "`/crewp` — Promote (reply)\n"
                        "`/crewd` — Demote (reply)\n"
                        "`/crewtransfer` — Transfer captaincy\n"
                        "`/crewdisband` — Disband"
                    )
                    await callback.answer()
                    return

                if sub == "leave":
                    await callback.message.reply("Use `/crewleave` to leave.")
                    await callback.answer()
                    return

                await callback.answer()
                return

            # ==================== CREW DISBAND ====================
            if data.startswith("crewdisband_"):
                from crew import get_crew, is_captain, _disband_crew
                tag = data.replace("crewdisband_", "")
                crew = get_crew(tag)
                if not crew:
                    await callback.answer("❌ Crew not found.", show_alert=True)
                    return
                if not is_captain(uid, crew):
                    await callback.answer("❌ Only Captain!", show_alert=True)
                    return

                result = await _disband_crew(crew)
                await callback.message.edit_text(
                    f"✅ **Crew [{tag}] disbanded.**\n\n"
                    f"Bank split: ฿{result['bank_split']:,}\n"
                    f"Ship refund: ฿{result['ship_refund']:,}"
                )
                await callback.answer("Disbanded!", show_alert=True)
                return

            # ==================== CREWTOP VIEWS ====================
            if data.startswith("crewtop_"):
                from crew import (
                    _show_crew_top_page,
                    _show_crew_top_by_level,
                    _show_crew_top_by_power,
                )
                view = data.replace("crewtop_", "")
                if view == "level":
                    await _show_crew_top_by_level(client, callback.message, edit=True)
                elif view == "power":
                    await _show_crew_top_by_power(client, callback.message, edit=True)
                else:
                    await _show_crew_top_page(client, callback.message, edit=True)
                await callback.answer()
                return

            # ==================== SHIP UPGRADE ====================
            if data.startswith("shipupgrade_confirm_"):
                from crew import get_crew, is_captain, save_crews, _safe_ship_tier
                from config import SHIPS

                try:
                    rest = data.replace("shipupgrade_confirm_", "")
                    tag, tier_str = rest.rsplit("_", 1)
                    target_tier = int(tier_str)
                except (ValueError, IndexError):
                    await callback.answer("Invalid request!", show_alert=True)
                    return

                crew = get_crew(tag)
                if not crew:
                    await callback.answer("❌ Crew not found!", show_alert=True)
                    return
                if not is_captain(uid, crew):
                    await callback.answer("❌ Only Captain!", show_alert=True)
                    return

                if tag in _ship_upgrade_locks:
                    await callback.answer("Processing...", show_alert=True)
                    return
                _ship_upgrade_locks.add(tag)
                try:
                    current_tier = _safe_ship_tier(crew)
                    if target_tier != current_tier + 1:
                        await callback.answer("❌ Invalid upgrade.", show_alert=True)
                        return

                    target_ship = SHIPS.get(target_tier)
                    if not target_ship:
                        await callback.answer("❌ Invalid tier!", show_alert=True)
                        return

                    cost = target_ship["cost"]
                    bank = int(crew.get("bank", 0) or 0)
                    if bank < cost:
                        await callback.answer(f"❌ Bank only has ฿{bank:,}", show_alert=True)
                        return

                    crew["bank"] = bank - cost
                    crew["ship_tier"] = target_tier
                    save_crews()

                    for mid in crew["members"]:
                        try:
                            await client.send_message(
                                mid,
                                f"**SHIP UPGRADED!**\n\n"
                                f"[{crew['tag']}] {crew['name']}\n"
                                f"{target_ship['emoji']} Now sailing: **{target_ship['name']}**!\n\n"
                                f"+{int(target_ship['pvp_damage_bonus'] * 100)}% PVP\n"
                                f"+{int(target_ship['daily_bonus'] * 100)}% daily\n"
                                f"+{int(target_ship['xp_bonus'] * 100)}% XP"
                            )
                        except Exception:
                            pass

                    await callback.message.edit_text(
                        f"✅ **SHIP UPGRADED!**\n\n"
                        f"[{crew['tag']}] {crew['name']}\n"
                        f"{target_ship['emoji']} **{target_ship['name']}** (Tier {target_tier})\n\n"
                        f"Cost: ฿{cost:,}\n"
                        f"Bank left: ฿{crew['bank']:,}\n\n"
                        f"Notified all members."
                    )
                    await callback.answer("✅ Upgraded!", show_alert=True)
                finally:
                    _ship_upgrade_locks.discard(tag)
                return

            if data == "shipupgrade_cancel":
                try:
                    await callback.message.delete()
                except Exception:
                    pass
                await callback.answer("Cancelled.", show_alert=False)
                return

            # ==================== BANNED PAGINATION ====================
            if data.startswith("bannedpage_"):
                parts = data.replace("bannedpage_", "").split("_", 1)
                if len(parts) != 2:
                    await callback.answer()
                    return
                mode = parts[0]
                page_str = parts[1]
                if mode == "noop" or page_str == "noop":
                    await callback.answer()
                    return
                try:
                    page = int(page_str)
                except ValueError:
                    page = 0
                from admin import _show_banned_page
                await _show_banned_page(
                    client, callback.message, uid,
                    mode=mode, page=page, edit=True,
                )
                await callback.answer()
                return

            if data.startswith("baninfo_"):
                if not is_admin_or_owner(uid):
                    await callback.answer("", show_alert=True)
                    return
                try:
                    target_id = int(data.replace("baninfo_", ""))
                except ValueError:
                    await callback.answer("Invalid ID!", show_alert=True)
                    return
                from admin import _build_baninfo_text
                text = await _build_baninfo_text(client, target_id)
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Unban", callback_data=f"unban_{target_id}")],
                    [InlineKeyboardButton("Back", callback_data="bannedpage_all_0")],
                ])
                try:
                    await callback.message.reply(text, reply_markup=kb)
                except Exception:
                    await callback.message.reply(text)
                await callback.answer()
                return

            if data.startswith("unban_"):
                if not is_admin_or_owner(uid):
                    await callback.answer("", show_alert=True)
                    return
                try:
                    target_id = int(data.replace("unban_", ""))
                except ValueError:
                    await callback.answer("Invalid ID!", show_alert=True)
                    return
                if target_id not in GBANNED:
                    await callback.answer("❌ Not globally banned!", show_alert=True)
                    return
                GBANNED.discard(target_id)
                save_banned()
                remove_banned_player_info(target_id)
                try:
                    await client.send_message(
                        target_id,
                        f"**YOU HAVE BEEN UNBANNED!**\n\nBy: {callback.from_user.first_name}"
                    )
                except Exception:
                    pass
                await callback.message.edit_text(
                    f"✅ **UNBANNED!**\n\n`{target_id}`\nBy: {callback.from_user.first_name}"
                )
                await callback.answer("✅ Unbanned!", show_alert=True)
                return

            if data.startswith("tempunban_"):
                if not is_admin_or_owner(uid):
                    await callback.answer("", show_alert=True)
                    return
                try:
                    target_id = int(data.replace("tempunban_", ""))
                except ValueError:
                    await callback.answer("Invalid ID!", show_alert=True)
                    return
                if target_id not in TEMP_BANNED:
                    await callback.answer("❌ Not temp-banned!", show_alert=True)
                    return
                del TEMP_BANNED[target_id]
                save_temp_banned()
                try:
                    await client.send_message(target_id, "Your temporary ban was lifted!")
                except Exception:
                    pass
                await callback.message.edit_text(
                    f"✅ **TEMP UNBANNED!**\n\n`{target_id}`\nBy: {callback.from_user.first_name}"
                )
                await callback.answer("✅ Unbanned!", show_alert=True)
                return

            # ==================== UNHANDLED ====================
            print(f"[callback] Unhandled: {data}")
            await callback.answer("Unknown action", show_alert=False)
            return

        except Exception as e:
            import traceback
            print(f"[callback error] {e}")
            traceback.print_exc()
            try:
                await callback.answer("Error occurred", show_alert=True)
            except Exception:
                pass