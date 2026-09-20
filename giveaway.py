# giveaway.py
import asyncio
import random
import time
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    BOT_NAME, MAIN_GROUP_ID, MAIN_GROUP_LINK, UPDATE_CHANNEL_LINK,
    UPDATE_CHANNEL_USERNAME, UPDATE_CHANNEL_ID, OWNER_ID,
    GIVEAWAY_DM_MIN_PRIZE,
)
from data_manager import (
    get_player, save_data, active_giveaways, user_data,
    get_global_giveaway, set_global_giveaway, clear_global_giveaway,
    get_bot_groups, is_admin_or_owner,
)
from utils import parse_amount
from update_notifier import notify_giveaway_started


def _giveaway_key(chat_id, msg_id):
    return f"{chat_id}_{msg_id}"


def calculate_tiered_prizes(total_prize, winner_count):
    """
    Distribution always adds up to 100% of total_prize.
    """
    prizes = {}
    if winner_count <= 0:
        return prizes

    if winner_count == 1:
        prizes[1] = total_prize
    elif winner_count == 2:
        prizes[1] = int(total_prize * 0.60)
        prizes[2] = total_prize - prizes[1]
    elif winner_count == 3:
        prizes[1] = int(total_prize * 0.50)
        prizes[2] = int(total_prize * 0.30)
        prizes[3] = total_prize - prizes[1] - prizes[2]
    else:
        prizes[1] = int(total_prize * 0.50)
        prizes[2] = int(total_prize * 0.20)
        prizes[3] = int(total_prize * 0.10)
        remaining = total_prize - prizes[1] - prizes[2] - prizes[3]
        remaining_winners = winner_count - 3
        per_winner = remaining // remaining_winners
        for i in range(4, winner_count + 1):
            prizes[i] = per_winner
        given = sum(prizes.values())
        leftover = total_prize - given
        if leftover > 0 and 4 in prizes:
            prizes[4] += leftover
    return prizes


def register_giveaway(app):

    # ==================== /tgiveaway ====================
    @app.on_message(filters.command("tgiveaway") & filters.group)
    async def start_tiered_giveaway(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return

        args = message.text.split(maxsplit=5)
        if len(args) < 4:
            await message.reply(
                "**TIERED GIVEAWAY**\n\n"
                "Format:\n"
                "`/tgiveaway [time] [amount] [players] [reason]`\n\n"
                "Example:\n"
                "`/tgiveaway 10m 10000000 10 Grand Prize`\n\n"
                "Time: `30s`, `5m`, `1h`, `1d`\n"
                "Players: 1-300"
            )
            return

        time_str = args[1].lower()
        total_prize = parse_amount(args[2])
        try:
            winner_count = int(args[3])
        except ValueError:
            await message.reply("❌ Invalid player count!")
            return
        reason = args[4] if len(args) > 4 else "Tiered Giveaway!"

        if total_prize is None or total_prize <= 0:
            await message.reply("❌ Invalid prize amount!")
            return
        winner_count = max(1, min(300, winner_count))

        time_map = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        unit = time_str[-1] if time_str else ""
        if unit not in time_map:
            await message.reply("❌ Invalid time format!")
            return
        try:
            duration = int(time_str[:-1]) * time_map[unit]
        except ValueError:
            await message.reply("❌ Invalid time value!")
            return
        if duration < 10:
            await message.reply("❌ Minimum 10 seconds!")
            return

        end_time = time.time() + duration
        prizes = calculate_tiered_prizes(total_prize, winner_count)

        prize_lines = ["**PRIZE DISTRIBUTION**\n"]
        for pos in (1, 2, 3):
            if pos in prizes:
                emoji = {1: "🥇", 2: "🥈", 3: "🥉"}[pos]
                suffix = {1: "1st", 2: "2nd", 3: "3rd"}[pos]
                prize_lines.append(f"{emoji} **{suffix}:** ฿{prizes[pos]:,}")
        if winner_count > 3 and 4 in prizes:
            prize_lines.append(f"🎖️ **4th-{winner_count}th:** ~฿{prizes[4]:,} each")
        prize_text = "\n".join(prize_lines)

        unit_names = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
        n = int(time_str[:-1])
        time_text = f"{n} {unit_names[unit]}"

        giveaway_text = (
            f"🎉 **TIERED GIVEAWAY!** 🎉\n\n"
            f"Total Prize: ฿{total_prize:,}\n"
            f"Reason: {reason}\n"
            f"Winners: {winner_count}\n"
            f"Ends in: {time_text}\n\n"
            f"{prize_text}\n\n"
            f"Click below to join!"
        )

        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Giveaway", callback_data="join_tgiveaway")],
            [InlineKeyboardButton("Participants", callback_data="view_tparticipants")],
        ])

        sent = await message.reply(giveaway_text, reply_markup=kb)
        key = _giveaway_key(message.chat.id, sent.id)

        active_giveaways[key] = {
            "chat_id": message.chat.id,
            "message_id": sent.id,
            "total_prize": total_prize,
            "description": reason,
            "end_time": end_time,
            "participants": [],
            "winner_count": winner_count,
            "prizes": prizes,
            "started_by": message.from_user.id,
            "is_tiered": True,
            "duration": duration,
            "chat_title": message.chat.title or "Group",
        }

        asyncio.create_task(
            end_tiered_giveaway_task(app, key, duration)
        )

        asyncio.create_task(notify_giveaway_started(
            app=client,
            giveaway_type="group",
            total_prize=total_prize,
            winner_count=winner_count,
            reason=f"{reason} (in {message.chat.title or 'a group'})",
            time_text=time_text,
            duration_text=time_text,
            channel_id=UPDATE_CHANNEL_ID,
            owner_id=OWNER_ID,
            user_data=user_data,
            main_group_link=MAIN_GROUP_LINK,
            updates_channel_link=UPDATE_CHANNEL_LINK,
            bot_name=BOT_NAME,
            dm_min_prize=GIVEAWAY_DM_MIN_PRIZE,
        ))

    # ==================== /join ====================
    @app.on_message(filters.command("join"))
    async def join_giveaway_by_command(client, message):
        regular = None
        for key, g in active_giveaways.items():
            if g["chat_id"] == message.chat.id:
                regular = (key, g)
                break

        if regular:
            key, g = regular
            uid = message.from_user.id
            if uid in g["participants"]:
                await message.reply("Already joined!")
                return
            g["participants"].append(uid)
            await message.reply(
                f"**Joined!**\n"
                f"Prize: ฿{g['total_prize']:,}\n"
                f"Total: {len(g['participants'])}"
            )
            return

        gg = get_global_giveaway()
        if gg is not None:
            if message.chat.id != MAIN_GROUP_ID:
                await message.reply(
                    f"❌ **Global giveaway is only joinable in the main group!**\n\n"
                    f"{MAIN_GROUP_LINK}"
                )
                return
            uid = message.from_user.id
            if uid in gg["participants"]:
                await message.reply("Already joined!")
                return

            main_ok = False
            updates_ok = False
            try:
                m = await client.get_chat_member(MAIN_GROUP_ID, uid)
                if str(m.status).split(".")[-1].upper() in (
                    "MEMBER", "ADMINISTRATOR", "OWNER", "CREATOR"
                ):
                    main_ok = True
            except Exception:
                pass
            try:
                m = await client.get_chat_member(UPDATE_CHANNEL_USERNAME, uid)
                if str(m.status).split(".")[-1].upper() in (
                    "MEMBER", "ADMINISTRATOR", "OWNER", "CREATOR"
                ):
                    updates_ok = True
            except Exception:
                updates_ok = False

            if not main_ok or not updates_ok:
                missing = []
                if not main_ok:
                    missing.append("Main Group")
                if not updates_ok:
                    missing.append("Updates Channel")
                kb = InlineKeyboardMarkup([
                    [InlineKeyboardButton("Join Main Group", url=MAIN_GROUP_LINK)],
                    [InlineKeyboardButton("Join Updates", url=UPDATE_CHANNEL_LINK)],
                    [InlineKeyboardButton("Verify & Join", callback_data="verify_global_giveaway")],
                ])
                await message.reply(
                    f"❌ **Join first: {', '.join(missing)}**",
                    reply_markup=kb,
                )
                return

            gg["participants"].append(uid)
            await message.reply(
                f"**Joined Global Giveaway!**\n"
                f"Prize: ฿{gg['total_prize']:,}\n"
                f"Total: {len(gg['participants'])}"
            )
            return

        await message.reply("❌ No active giveaway in this chat!")

    # ==================== /cancelgiveaway ====================
    @app.on_message(filters.command("cancelgiveaway") & filters.group)
    async def cancel_giveaway_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/cancelgiveaway [message_id]`")
            return
        try:
            msg_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid ID!")
            return

        key = _giveaway_key(message.chat.id, msg_id)
        if key not in active_giveaways:
            await message.reply("❌ Giveaway not found!")
            return

        g = active_giveaways[key]
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Yes, cancel", callback_data=f"confirm_cancel_giveaway_{key}")],
            [InlineKeyboardButton("No, keep", callback_data="cancel_cancel_giveaway")],
        ])
        await message.reply(
            f"**CANCEL GIVEAWAY?**\n\n"
            f"Prize: ฿{g['total_prize']:,}\n"
            f"Participants: {len(g['participants'])}\n\n"
            f"Are you sure?",
            reply_markup=kb,
        )

    # ==================== /endgiveaway ====================
    @app.on_message(filters.command("endgiveaway") & filters.group)
    async def end_giveaway_early_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/endgiveaway [message_id]`")
            return
        try:
            msg_id = int(args[1])
        except ValueError:
            await message.reply("❌ Invalid ID!")
            return
        key = _giveaway_key(message.chat.id, msg_id)
        if key not in active_giveaways:
            await message.reply("❌ Giveaway not found!")
            return
        g = active_giveaways[key]
        if not g["participants"]:
            await message.reply("❌ No participants!")
            del active_giveaways[key]
            return
        await _finish_tiered_giveaway(app, key)

    # ==================== /activegiveaways ====================
    @app.on_message(filters.command("activegiveaways"))
    async def active_giveaways_cmd(client, message):
        if not is_admin_or_owner(message.from_user.id):
            await message.reply("")
            return

        text = "**ACTIVE GIVEAWAYS**\n\n"
        has = False
        for key, g in list(active_giveaways.items())[:5]:
            has = True
            left = max(0, int(g["end_time"] - time.time()))
            text += (
                f"{g.get('chat_title', 'Unknown')}\n"
                f"   Prize: ฿{g['total_prize']:,}\n"
                f"   Participants: {len(g['participants'])}\n"
                f"   Time left: {left // 60}m\n"
                f"   Key: `{key}`\n\n"
            )

        gg = get_global_giveaway()
        if gg is not None:
            has = True
            left = max(0, int(gg["end_time"] - time.time()))
            text += (
                f"**GLOBAL**\n"
                f"   Prize: ฿{gg['total_prize']:,}\n"
                f"   Participants: {len(gg['participants'])}\n"
                f"   Time left: {left // 60}m\n"
                f"   Reason: {gg.get('description', 'N/A')}\n\n"
            )

        if not has:
            text += "*No active giveaways.*"

        await message.reply(text)

    # ==================== /agiveaway ====================
    @app.on_message(filters.command("agiveaway"))
    async def start_global_giveaway(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if message.chat.id != MAIN_GROUP_ID:
            await message.reply(f"❌ Must be in main group!\n{MAIN_GROUP_LINK}")
            return
        if get_global_giveaway() is not None:
            await message.reply("❌ Global giveaway already active!")
            return

        args = message.text.split(maxsplit=5)
        if len(args) < 4:
            await message.reply(
                "**GLOBAL GIVEAWAY**\n\n"
                "Format: `/agiveaway [time] [amount] [players] [reason]`\n"
                "Time: `30s`, `5m`, `1h`, `1d`"
            )
            return

        time_str = args[1].lower()
        total_prize = parse_amount(args[2])
        try:
            winner_count = int(args[3])
        except ValueError:
            await message.reply("❌ Invalid player count!")
            return
        reason = args[4] if len(args) > 4 else "Global Giveaway!"

        if total_prize is None or total_prize <= 0:
            await message.reply("❌ Invalid prize!")
            return
        winner_count = max(1, min(300, winner_count))

        time_map = {"s": 1, "m": 60, "h": 3600, "d": 86400}
        unit = time_str[-1] if time_str else ""
        if unit not in time_map:
            await message.reply("❌ Invalid time format!")
            return
        try:
            duration = int(time_str[:-1]) * time_map[unit]
        except ValueError:
            await message.reply("❌ Invalid time value!")
            return
        if duration < 10:
            await message.reply("❌ Minimum 10 seconds!")
            return

        end_time = time.time() + duration
        prizes = calculate_tiered_prizes(total_prize, winner_count)

        unit_names = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
        n = int(time_str[:-1])
        time_text = f"{n} {unit_names[unit]}"

        giveaway_data = {
            "chat_id": message.chat.id,
            "total_prize": total_prize,
            "description": reason,
            "end_time": end_time,
            "participants": [],
            "winner_count": winner_count,
            "prizes": prizes,
            "started_by": message.from_user.id,
            "time_text": time_text,
            "duration": duration,
        }
        set_global_giveaway(giveaway_data)

        prize_lines = ["**PRIZE DISTRIBUTION**\n"]
        for pos in (1, 2, 3):
            if pos in prizes:
                emoji = {1: "🥇", 2: "🥈", 3: "🥉"}[pos]
                suffix = {1: "1st", 2: "2nd", 3: "3rd"}[pos]
                prize_lines.append(f"{emoji} **{suffix}:** ฿{prizes[pos]:,}")
        if winner_count > 3 and 4 in prizes:
            prize_lines.append(f"🎖️ **4th-{winner_count}th:** ~฿{prizes[4]:,} each")
        prize_text = "\n".join(prize_lines)

        announcement = (
            f"🌍 **GLOBAL GIVEAWAY!** 🌍\n\n"
            f"Total Prize: ฿{total_prize:,}\n"
            f"Reason: {reason}\n"
            f"Winners: {winner_count}\n"
            f"Ends in: {time_text}\n\n"
            f"{prize_text}\n\n"
            f"**Requirements:**\n"
            f"Join Main Group: {MAIN_GROUP_LINK}\n"
            f"Join Updates: {UPDATE_CHANNEL_LINK}\n\n"
            f"Click below to join!"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join Global Giveaway", callback_data="join_global_giveaway")],
            [InlineKeyboardButton("Join Updates", url=UPDATE_CHANNEL_LINK)],
            [InlineKeyboardButton("Join Main Group", url=MAIN_GROUP_LINK)],
        ])
        try:
            await client.send_message(
                MAIN_GROUP_ID,
                announcement,
                reply_markup=kb,
                disable_web_page_preview=True,
            )
        except Exception as e:
            print(f"[agiveaway] main group send: {e}")

        group_text = (
            f"🌍 **GLOBAL GIVEAWAY!** 🌍\n\n"
            f"Prize: ฿{total_prize:,}\n"
            f"Reason: {reason}\n"
            f"Winners: {winner_count}\n"
            f"Ends in: {time_text}\n\n"
            f"Join the main group to participate!\n"
            f"{MAIN_GROUP_LINK}"
        )
        groups_sent = 0
        for gid in list(get_bot_groups()):
            if gid == MAIN_GROUP_ID:
                continue
            try:
                await client.send_message(gid, group_text, disable_web_page_preview=True)
                groups_sent += 1
                await asyncio.sleep(0.3)
            except Exception:
                pass

        asyncio.create_task(notify_giveaway_started(
            app=client,
            giveaway_type="global",
            total_prize=total_prize,
            winner_count=winner_count,
            reason=reason,
            time_text=time_text,
            duration_text=time_text,
            channel_id=UPDATE_CHANNEL_ID,
            owner_id=OWNER_ID,
            user_data=user_data,
            main_group_link=MAIN_GROUP_LINK,
            updates_channel_link=UPDATE_CHANNEL_LINK,
            bot_name=BOT_NAME,
            dm_min_prize=0,
        ))

        await message.reply(
            f"**GLOBAL GIVEAWAY STARTED!**\n\n"
            f"{time_text}\n"
            f"฿{total_prize:,}\n"
            f"{winner_count} winners\n"
            f"Sent to main + {groups_sent} groups"
        )

        asyncio.create_task(end_global_giveaway_task(app, duration))

    # ==================== /cancelagiveaway ====================
    @app.on_message(filters.command("cancelagiveaway"))
    async def cancel_global_giveaway_cmd(client, message):
        if message.from_user.id != OWNER_ID:
            await message.reply("")
            return
        if message.chat.id != MAIN_GROUP_ID:
            await message.reply("❌ Must be in main group!")
            return
        gg = get_global_giveaway()
        if gg is None:
            await message.reply("❌ No active global giveaway!")
            return
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Yes, cancel", callback_data="confirm_cancel_global_giveaway")],
            [InlineKeyboardButton("No, keep", callback_data="cancel_cancel_global_giveaway")],
        ])
        await message.reply(
            f"**CANCEL GLOBAL GIVEAWAY?**\n\n"
            f"฿{gg['total_prize']:,}\n"
            f"{len(gg['participants'])} participants\n\n"
            f"Are you sure?",
            reply_markup=kb,
        )


# ==================== TASK HELPERS ====================
async def _finish_tiered_giveaway(app, key):
    g = active_giveaways.get(key)
    if not g:
        return
    participants = g["participants"]
    if not participants:
        try:
            await app.send_message(
                g["chat_id"],
                f"❌ **Giveaway ended with no participants!**\n\n"
                f"Prize: ฿{g['total_prize']:,}"
            )
        except Exception:
            pass
        active_giveaways.pop(key, None)
        return

    winner_count = min(g["winner_count"], len(participants))
    prizes = g["prizes"]

    shuffled = participants.copy()
    random.shuffle(shuffled)
    winners = shuffled[:winner_count]

    lines = []
    for pos, wid in enumerate(winners[:10], 1):
        amt = prizes.get(pos, 0)
        if amt > 0:
            p = get_player(wid)
            p.bounty += amt
            save_data()
        try:
            u = await app.get_users(wid)
            mention = (f"[{u.first_name}](https://t.me/{u.username})"
                       if u.username else u.first_name)
        except Exception:
            mention = f"User `{wid}`"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, "🎖️")
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(pos, "th")
        lines.append(f"{medal} **{pos}{suffix}** — {mention} → ฿{amt:,}")

    if winner_count > 10:
        lines.append(f"\n🎁 **+{winner_count - 10} more winners!**")

    result = (
        f"🎊 **GIVEAWAY ENDED!** 🎊\n\n"
        f"Prize: ฿{g['total_prize']:,}\n"
        f"Reason: {g['description']}\n"
        f"Participants: {len(participants)}\n\n"
        f"**WINNERS:**\n" + "\n".join(lines) +
        f"\n\nCongratulations!"
    )

    try:
        await app.send_message(g["chat_id"], result, disable_web_page_preview=True)
    except Exception as e:
        print(f"[tgiveaway end] {e}")
    active_giveaways.pop(key, None)


async def end_tiered_giveaway_task(app, key, duration):
    await asyncio.sleep(duration)
    await _finish_tiered_giveaway(app, key)


async def end_global_giveaway_task(app, duration):
    await asyncio.sleep(duration)
    gg = get_global_giveaway()
    if gg is None:
        return

    participants = gg["participants"]
    if not participants:
        text = (
            f"🌍 **GLOBAL GIVEAWAY ENDED!**\n\n"
            f"฿{gg['total_prize']:,}\n"
            f"{gg['description']}\n"
            f"No participants."
        )
        try:
            await app.send_message(MAIN_GROUP_ID, text)
        except Exception:
            pass
        for gid in list(get_bot_groups()):
            if gid == MAIN_GROUP_ID:
                continue
            try:
                await app.send_message(gid, text)
                await asyncio.sleep(0.3)
            except Exception:
                pass
        clear_global_giveaway()
        return

    winner_count = min(gg["winner_count"], len(participants))
    prizes = gg["prizes"]

    shuffled = participants.copy()
    random.shuffle(shuffled)
    winners = shuffled[:winner_count]

    lines = []
    for pos, wid in enumerate(winners[:10], 1):
        amt = prizes.get(pos, 0)
        if amt > 0:
            p = get_player(wid)
            p.bounty += amt
            save_data()
        try:
            u = await app.get_users(wid)
            mention = (f"[{u.first_name}](https://t.me/{u.username})"
                       if u.username else u.first_name)
        except Exception:
            mention = f"User `{wid}`"
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(pos, "🎖️")
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(pos, "th")
        lines.append(f"{medal} **{pos}{suffix}** — {mention} → ฿{amt:,}")

    if winner_count > 10:
        lines.append(f"\n🎁 **+{winner_count - 10} more!**")

    result = (
        f"🎊 **GLOBAL GIVEAWAY ENDED!** 🎊\n\n"
        f"Prize: ฿{gg['total_prize']:,}\n"
        f"Reason: {gg['description']}\n"
        f"Participants: {len(participants)}\n\n"
        f"**WINNERS:**\n" + "\n".join(lines) +
        f"\n\nCongratulations!"
    )

    try:
        await app.send_message(MAIN_GROUP_ID, result, disable_web_page_preview=True)
    except Exception:
        pass
    for gid in list(get_bot_groups()):
        if gid == MAIN_GROUP_ID:
            continue
        try:
            await app.send_message(gid, result, disable_web_page_preview=True)
            await asyncio.sleep(0.3)
        except Exception:
            pass

    clear_global_giveaway()