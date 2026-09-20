# games.py
import asyncio
import random
import time
from pyrogram import filters

from config import BOT_NAME
from data_manager import get_player, save_data
from utils import (
    check_cooldown, parse_amount, get_xp_needed,
    get_pattern_result, get_observation_win_rate,
    get_observation_money_mult, get_armament_recovery,
    consume_haki_use, is_haki_active, is_advanced_haki,
    get_dart_threshold,
)
from pvp import (
    send_level_up_notification, send_level_up_group_notification,
    send_level_down_notification, send_level_down_group_notification,
)


last_pay_time = {}


# ==================== HAKI OUTCOME HELPER ====================
def _apply_haki_outcome(player, win, amount):
    """
    Apply Observation (better luck) and Armament (recovery) to game outcome.
    Returns (final_win, final_amount, note)
    """
    note = ""

    # Observation: flip a loss to a win at the given rate
    if not win and is_haki_active(player) and player.haki == "obv":
        rate = get_observation_win_rate(player)
        if rate is not None and random.random() < rate:
            win = True
            note = "\n*Observation Haki flipped the odds!*"
            consume_haki_use(player)

    # Observation ADV: 2x money on win
    if win and is_haki_active(player) and player.haki == "obv":
        mult = get_observation_money_mult(player)
        if mult > 1.0:
            amount = int(amount * mult)
            note += f"\n*ADV Observation: x{mult} money!*"

    # Armament: recovery on loss
    if not win and is_haki_active(player) and player.haki == "arm":
        recovery = get_armament_recovery(player)
        if recovery > 0:
            refund = int(amount * recovery)
            player.bounty += refund
            note += f"\n*Armament recovered ฿{refund:,} ({int(recovery * 100)}%)!*"
            consume_haki_use(player)

    return win, amount, note


def _apply_win(player, amount, base_xp):
    player.bounty += amount
    player.xp += base_xp
    old_level = player.level
    while player.xp >= get_xp_needed(player.level) and player.level < 200:
        player.xp -= get_xp_needed(player.level)
        player.level += 1
    if player.level >= 200:
        player.xp = 0
    level_text = f"\n\nLEVEL UP! {old_level} → {player.level}" if player.level > old_level else ""
    return base_xp, old_level, level_text


def _apply_loss(player, amount, base_xp):
    player.bounty -= amount
    player.xp -= base_xp
    old_level = player.level
    level_down_text = ""
    while player.xp < 0 and player.level > 1:
        player.level -= 1
        player.xp += get_xp_needed(player.level)
        level_down_text = f"\n\nLEVEL DOWN! {old_level} → {player.level}"
    if player.xp < 0:
        player.xp = 0
        player.level = 1
    return base_xp, old_level, level_down_text


def _xp_with_bonus(player, base_xp):
    """Apply crew ship XP bonus if available."""
    try:
        from crew import player_crew_bonus
        bonus = player_crew_bonus(player.user_id, "xp_bonus")
        if bonus > 0:
            base_xp = int(base_xp * (1 + bonus))
    except Exception:
        pass
    return max(1, base_xp)


def register_games(app):

    # ==================== /bet ====================
    @app.on_message(filters.command("bet"))
    async def bet_cmd(client, message):
        uid = message.from_user.id
        can, rem = check_cooldown(uid, 2)
        if not can:
            await message.reply(f"⏰ Slow down! Wait {rem}s!")
            return

        args = message.text.split()
        if len(args) != 3:
            await message.reply("Usage: `/bet [amount] [t/h]`")
            return

        amount = parse_amount(args[1])
        if amount is None or amount <= 0:
            await message.reply("❌ Invalid amount!")
            return

        choice = args[2].lower()
        if choice not in ("t", "h"):
            await message.reply("Choose 't' or 'h'!")
            return

        p = get_player(uid, user=message.from_user)
        if p.bounty < amount:
            await message.reply(f"Need ฿{amount:,}! You have ฿{p.bounty:,}")
            return

        # Pattern-driven result
        result = get_pattern_result(
            game="bet",
            user_id=uid,
            default_choice_fn=lambda: random.choice(["h", "t"]),
        )

        win = (choice == result)
        display = "HEADS" if result == "h" else "TAILS"

        # Haki outcome
        win, amount, haki_note = _apply_haki_outcome(p, win, amount)

        xp = _xp_with_bonus(p, max(1, min(50, amount // 100_000)))
        if p.boost_end > time.time() and win:
            xp = min(75, int(xp * 1.5))

        if win:
            gained, old_lvl, lt = _apply_win(p, amount, xp)
            save_data()
            if p.level > old_lvl:
                await send_level_up_notification(app, uid, old_lvl, p.level, "game")
                await send_level_up_group_notification(app, message.chat.id, p.name, old_lvl, p.level)
            await message.reply(
                f"🎉 Coin landed on **{display}**!\n"
                f"✅ **Won ฿{amount:,}!**\n"
                f"⭐ **+{gained} XP**{haki_note}{lt}"
            )
        else:
            lost, old_lvl, lt = _apply_loss(p, amount, xp)
            save_data()
            if p.level < old_lvl:
                await send_level_down_notification(app, uid, old_lvl, p.level, "game")
                await send_level_down_group_notification(app, message.chat.id, p.name, old_lvl, p.level)
            await message.reply(
                f"😢 Coin landed on **{display}**!\n"
                f"❌ **Lost ฿{amount:,}!**\n"
                f"⭐ **-{lost} XP**{haki_note}{lt}"
            )

    # ==================== /dice ====================
    @app.on_message(filters.command("dice"))
    async def dice_cmd(client, message):
        uid = message.from_user.id
        can, rem = check_cooldown(uid, 2)
        if not can:
            await message.reply(f"⏰ Slow down! Wait {rem}s!")
            return

        args = message.text.split()
        if len(args) != 3:
            await message.reply("Usage: `/dice [amount] [e/o]`")
            return

        amount = parse_amount(args[1])
        if amount is None or amount <= 0:
            await message.reply("❌ Invalid amount!")
            return

        choice = args[2].lower()
        if choice not in ("e", "o"):
            await message.reply("Choose 'e' or 'o'!")
            return

        p = get_player(uid, user=message.from_user)
        if p.bounty < amount:
            await message.reply(f"Need ฿{amount:,}! You have ฿{p.bounty:,}")
            return

        pattern_result = get_pattern_result(
            game="dice",
            user_id=uid,
            default_choice_fn=lambda: random.choice(["e", "o"]),
        )

        dice_msg = await client.send_dice(message.chat.id, emoji="🎲")
        await asyncio.sleep(2)
        roll = dice_msg.dice.value

        is_even = (pattern_result == "e")
        win = (choice == "e" and is_even) or (choice == "o" and not is_even)

        win, amount, haki_note = _apply_haki_outcome(p, win, amount)

        xp = _xp_with_bonus(p, max(1, min(50, amount // 100_000)))
        if p.boost_end > time.time() and win:
            xp = min(75, int(xp * 1.5))

        if win:
            gained, old_lvl, lt = _apply_win(p, amount, xp)
            save_data()
            if p.level > old_lvl:
                await send_level_up_notification(app, uid, old_lvl, p.level, "game")
                await send_level_up_group_notification(app, message.chat.id, p.name, old_lvl, p.level)
            await message.reply(
                f"🎲 Rolled **{roll}** ({pattern_result.upper()})!\n"
                f"✅ Won ฿{amount:,}!\n"
                f"⭐ **+{gained} XP**{haki_note}{lt}"
            )
        else:
            lost, old_lvl, lt = _apply_loss(p, amount, xp)
            save_data()
            if p.level < old_lvl:
                await send_level_down_notification(app, uid, old_lvl, p.level, "game")
                await send_level_down_group_notification(app, message.chat.id, p.name, old_lvl, p.level)
            await message.reply(
                f"🎲 Rolled **{roll}** ({pattern_result.upper()})!\n"
                f"❌ Lost ฿{amount:,}!\n"
                f"⭐ **-{lost} XP**{haki_note}{lt}"
            )

    # ==================== /dart ====================
    @app.on_message(filters.command("dart"))
    async def dart_cmd(client, message):
        uid = message.from_user.id
        can, rem = check_cooldown(uid, 2)
        if not can:
            await message.reply(f"⏰ Slow down! Wait {rem}s!")
            return

        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/dart [amount]`")
            return

        amount = parse_amount(args[1])
        if amount is None or amount <= 0:
            await message.reply("❌ Invalid amount!")
            return

        p = get_player(uid, user=message.from_user)
        if p.bounty < amount:
            await message.reply(f"Need ฿{amount:,}! You have ฿{p.bounty:,}")
            return

        dart_msg = await client.send_dice(message.chat.id, emoji="🎯")
        await asyncio.sleep(2)
        dart_value = dart_msg.dice.value

        threshold = get_dart_threshold(p)
        win = dart_value >= threshold

        # Advanced Observation reroll
        if not win and is_advanced_haki(p) and p.haki == "obv":
            reroll = random.randint(1, 6)
            if reroll >= threshold:
                win = True
                dart_value = reroll

        win, amount, haki_note = _apply_haki_outcome(p, win, amount)

        xp = _xp_with_bonus(p, max(1, min(50, amount // 100_000)))
        if p.boost_end > time.time() and win:
            xp = min(75, int(xp * 1.5))

        if win:
            gained, old_lvl, lt = _apply_win(p, amount, xp)
            save_data()
            if p.level > old_lvl:
                await send_level_up_notification(app, uid, old_lvl, p.level, "game")
                await send_level_up_group_notification(app, message.chat.id, p.name, old_lvl, p.level)
            header = "🎯 **BULLSEYE!**" if dart_value == 6 else f"🎯 Scored **{dart_value}**!"
            await message.reply(f"{header}\n+฿{amount:,}!\n⭐ **+{gained} XP**{haki_note}{lt}")
        else:
            lost, old_lvl, lt = _apply_loss(p, amount, xp)
            save_data()
            if p.level < old_lvl:
                await send_level_down_notification(app, uid, old_lvl, p.level, "game")
                await send_level_down_group_notification(app, message.chat.id, p.name, old_lvl, p.level)
            await message.reply(
                f"💨 **MISSED!**\n"
                f"Scored {dart_value}!\n"
                f"-฿{amount:,}!\n"
                f"⭐ **-{lost} XP**{haki_note}{lt}"
            )

    # ==================== /bowl ====================
    @app.on_message(filters.command("bowl"))
    async def bowl_cmd(client, message):
        uid = message.from_user.id
        can, rem = check_cooldown(uid, 2)
        if not can:
            await message.reply(f"⏰ Slow down! Wait {rem}s!")
            return

        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/bowl [amount]`")
            return

        amount = parse_amount(args[1])
        if amount is None or amount <= 0:
            await message.reply("❌ Invalid amount!")
            return

        p = get_player(uid, user=message.from_user)
        if p.bounty < amount:
            await message.reply(f"Need ฿{amount:,}! You have ฿{p.bounty:,}")
            return

        bowl_msg = await client.send_dice(message.chat.id, emoji="🎳")
        await asyncio.sleep(2)
        # ✅ Telegram bowling: value 1-6 = pins KNOCKED (6 = STRIKE)
        pins = bowl_msg.dice.value

        obv_haki = (p.haki == "obv" and p.haki_level >= 3)

        if pins == 6:
            win, result = True, "🎳 **STRIKE!** All 6 pins!"
        elif pins == 5:
            win, result = True, "🎳 **SPARE!** 5 pins!"
        elif pins == 4:
            win, result = True, "🎳 **GOOD!** 4 pins!"
        elif pins == 3:
            win = True if obv_haki else (random.random() < 0.5)
            result = f"🎳 **3 pins!** " + ("Win!" if win else "Lose!")
        elif pins == 2:
            win, result = False, "💨 **WEAK!** Only 2 pins!"
        else:  # 1
            win, result = False, "💨 **GUTTER!** Only 1 pin!"

        win, amount, haki_note = _apply_haki_outcome(p, win, amount)

        xp = _xp_with_bonus(p, max(1, min(50, amount // 100_000)))
        if p.boost_end > time.time() and win:
            xp = min(75, int(xp * 1.5))

        if win:
            gained, old_lvl, lt = _apply_win(p, amount, xp)
            save_data()
            if p.level > old_lvl:
                await send_level_up_notification(app, uid, old_lvl, p.level, "game")
                await send_level_up_group_notification(app, message.chat.id, p.name, old_lvl, p.level)
            await message.reply(f"{result}{haki_note}\n+฿{amount:,}!\n⭐ **+{gained} XP**{lt}")
        else:
            lost, old_lvl, lt = _apply_loss(p, amount, xp)
            save_data()
            if p.level < old_lvl:
                await send_level_down_notification(app, uid, old_lvl, p.level, "game")
                await send_level_down_group_notification(app, message.chat.id, p.name, old_lvl, p.level)
            await message.reply(f"{result}\n-฿{amount:,}!\n⭐ **-{lost} XP**{haki_note}{lt}")

    # ==================== /soccer ====================
    @app.on_message(filters.command("soccer"))
    async def soccer_cmd(client, message):
        uid = message.from_user.id
        can, rem = check_cooldown(uid, 2)
        if not can:
            await message.reply(f"⏰ Slow down! Wait {rem}s!")
            return

        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/soccer [amount]`")
            return

        amount = parse_amount(args[1])
        if amount is None or amount <= 0:
            await message.reply("❌ Invalid amount!")
            return

        p = get_player(uid, user=message.from_user)
        if p.bounty < amount:
            await message.reply(f"Need ฿{amount:,}! You have ฿{p.bounty:,}")
            return

        msg = await client.send_dice(message.chat.id, emoji="⚽")
        await asyncio.sleep(2)
        val = msg.dice.value

        obv_haki = (p.haki == "obv" and p.haki_level >= 3)
        win = val >= (3 if obv_haki else 4)

        win, amount, haki_note = _apply_haki_outcome(p, win, amount)

        xp = _xp_with_bonus(p, max(1, min(50, amount // 100_000)))
        if p.boost_end > time.time() and win:
            xp = min(75, int(xp * 1.5))

        if win:
            gained, old_lvl, lt = _apply_win(p, amount, xp)
            save_data()
            if p.level > old_lvl:
                await send_level_up_notification(app, uid, old_lvl, p.level, "game")
                await send_level_up_group_notification(app, message.chat.id, p.name, old_lvl, p.level)
            await message.reply(f"⚽ **GOAL!**{haki_note}\n+฿{amount:,}!\n⭐ **+{gained} XP**{lt}")
        else:
            lost, old_lvl, lt = _apply_loss(p, amount, xp)
            save_data()
            if p.level < old_lvl:
                await send_level_down_notification(app, uid, old_lvl, p.level, "game")
                await send_level_down_group_notification(app, message.chat.id, p.name, old_lvl, p.level)
            await message.reply(f"🥅 **MISSED!**\n-฿{amount:,}!\n⭐ **-{lost} XP**{haki_note}{lt}")

    # ==================== /pay ====================
    @app.on_message(filters.command("pay"))
    async def pay_cmd(client, message):
        uid = message.from_user.id
        p = get_player(uid, user=message.from_user)

        now = time.time()
        if now - p.pay_cd < 600:
            rem = 600 - (now - p.pay_cd)
            await message.reply(f"⏰ **Cooldown!** Wait {int(rem // 60)}m {int(rem % 60)}s.")
            return

        if not message.reply_to_message:
            await message.reply(
                "**PAY**\n\n"
                "Reply to a user with `/pay [amount]`\n"
                "Max: ฿500,000,000 | Cooldown: 10 min"
            )
            return

        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/pay [amount]`")
            return

        amount = parse_amount(args[1])
        if amount is None or amount <= 0:
            await message.reply("❌ Invalid amount!")
            return
        if amount > 500_000_000:
            await message.reply("❌ Max is ฿500,000,000!")
            return

        receiver = get_player(message.reply_to_message.from_user.id, user=message.reply_to_message.from_user)
        if int(p.user_id) == int(receiver.user_id):
            await message.reply("❌ Can't pay yourself!")
            return
        if p.bounty < amount:
            await message.reply(f"❌ Need ฿{amount:,}, have ฿{p.bounty:,}")
            return

        p.bounty -= amount
        receiver.bounty += amount
        p.pay_cd = now
        save_data()

        s_name = p.name or f"User_{p.user_id}"
        r_name = receiver.name or f"User_{receiver.user_id}"
        s_mention = (
            f"[{s_name}](https://t.me/{message.from_user.username})"
            if message.from_user.username else f"[{s_name}](tg://user?id={p.user_id})"
        )
        r_mention = (
            f"[{r_name}](https://t.me/{message.reply_to_message.from_user.username})"
            if message.reply_to_message.from_user.username
            else f"[{r_name}](tg://user?id={receiver.user_id})"
        )

        await message.reply(
            f"**PAYMENT SENT!**\n\n"
            f"From: {s_mention}\n"
            f"To: {r_mention}\n"
            f"Amount: ฿{amount:,}\n\n"
            f"{s_name}: ฿{p.bounty:,}\n"
            f"{r_name}: ฿{receiver.bounty:,}\n\n"
            f"Next payment in 10 min."
        )
        try:
            await client.send_message(
                receiver.user_id,
                f"**Received payment!**\n\n"
                f"From: {s_name}\n"
                f"Amount: ฿{amount:,}\n"
                f"Your bounty: ฿{receiver.bounty:,}"
            )
        except Exception:
            pass