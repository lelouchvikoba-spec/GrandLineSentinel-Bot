# shop.py
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import (
    BOT_NAME, SHOP_IMAGE, VAULT_CAPS,
    FRUIT_SELL_REFUNDS, DEVIL_FRUITS,
    get_fruit_tier, get_fruit_icon, normalize_fruit_name,
)
from data_manager import get_player, save_data
from utils import parse_amount


def register_shop(app):

    # ==================== /shop ====================
    @app.on_message(filters.command("shop"))
    async def shop_cmd(client, message):
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("Haki", callback_data="shop_haki")],
            [InlineKeyboardButton("Shield", callback_data="shop_shield")],
            [InlineKeyboardButton("Devil Fruit", callback_data="shop_fruit")],
            [InlineKeyboardButton("Vault Upgrade", callback_data="shop_vault")],
            [InlineKeyboardButton("2x XP (50M)", callback_data="shop_boost")],
            [InlineKeyboardButton("Switch Haki", callback_data="shop_switch_haki")],
        ])
        text = f"**SHOP**\n\nSelect a category.\n\n{BOT_NAME}"

        if SHOP_IMAGE and isinstance(SHOP_IMAGE, str) and SHOP_IMAGE.strip():
            try:
                await message.reply_photo(SHOP_IMAGE, caption=text, reply_markup=kb)
                return
            except Exception as e:
                print(f"[shop] photo failed: {e}")
            try:
                await message.reply_document(SHOP_IMAGE, caption=text, reply_markup=kb)
                return
            except Exception as e:
                print(f"[shop] document failed: {e}")

        await message.reply(text, reply_markup=kb)

    # ==================== /sell_fruit ====================
    @app.on_message(filters.command("sell_fruit"))
    async def sell_fruit_cmd(client, message):
        p = get_player(message.from_user.id, user=message.from_user)
        if not p.devil_fruit:
            await message.reply("❌ You don't have a devil fruit!")
            return

        normalized = normalize_fruit_name(p.devil_fruit)
        tier = get_fruit_tier(normalized) or p.fruit_category or "Bad"
        refund = FRUIT_SELL_REFUNDS.get(tier, 12_500_000)

        fruit_name = normalized
        icon = get_fruit_icon(fruit_name)

        p.bounty += refund
        p.devil_fruit = None
        p.fruit_category = None
        p.nika_awakened = False
        save_data()

        await message.reply(
            f"**Fruit Sold!**\n\n"
            f"{icon} **Fruit:** {fruit_name}\n"
            f"Refund: ฿{refund:,} (50%)\n"
            f"New Bounty: ฿{p.bounty:,}"
        )

    # ==================== /fruitlist ====================
    @app.on_message(filters.command("fruitlist"))
    async def fruit_list_cmd(client, message):
        text = "**ALL DEVIL FRUITS**\n"
        text += "──────────────────\n\n"

        for category in ("Good", "Medium", "Bad"):
            fruits = DEVIL_FRUITS[category]
            text += f"**{category}** ({len(fruits)}):\n"
            for f in fruits:
                icon = get_fruit_icon(f["full"])
                text += f"  {icon} {f['full']}\n"
            text += "\n"

        text += f"{BOT_NAME}"

        def _split(t, limit=4000):
            lines = t.split("\n")
            out, buf = [], ""
            for line in lines:
                if len(buf) + len(line) + 1 > limit:
                    out.append(buf)
                    buf = line
                else:
                    buf = f"{buf}\n{line}" if buf else line
            if buf:
                out.append(buf)
            return out

        for chunk in _split(text):
            await message.reply(chunk)

    # ==================== /deposit ====================
    @app.on_message(filters.command("deposit"))
    async def deposit_cmd(client, message):
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/deposit [amount]`")
            return

        amount = parse_amount(args[1])
        if amount is None or amount <= 0:
            await message.reply("❌ **Invalid amount!** Must be positive.")
            return

        p = get_player(message.from_user.id, user=message.from_user)
        cap = VAULT_CAPS.get(p.vault_level, 25_000_000)
        if amount > p.bounty:
            await message.reply(f"Not enough! You have ฿{p.bounty:,}")
            return
        if p.vault + amount > cap:
            await message.reply(f"Vault full! Capacity: ฿{cap:,}")
            return

        p.bounty -= amount
        p.vault += amount
        save_data()
        await message.reply(
            f"Deposited ฿{amount:,}!\n"
            f"Vault: ฿{p.vault:,}\n"
            f"Bounty: ฿{p.bounty:,}"
        )

    # ==================== /dig ====================
    @app.on_message(filters.command("dig"))
    async def dig_cmd(client, message):
        args = message.text.split()
        if len(args) != 2:
            await message.reply("Usage: `/dig [amount]`")
            return

        amount = parse_amount(args[1])
        if amount is None or amount <= 0:
            await message.reply("❌ **Invalid amount!** Must be positive.")
            return

        p = get_player(message.from_user.id, user=message.from_user)
        if amount > p.vault:
            await message.reply(f"Not enough! Vault: ฿{p.vault:,}")
            return

        p.vault -= amount
        p.bounty += amount
        save_data()
        await message.reply(
            f"Withdrew ฿{amount:,}!\n"
            f"Vault: ฿{p.vault:,}\n"
            f"Bounty: ฿{p.bounty:,}"
        )