# config.py
import os
from datetime import timezone, timedelta
from dotenv import load_dotenv

load_dotenv()

# ==================== BOT ====================
API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
BOT_NAME = os.getenv("BOT_NAME", "Grand Line Sentinel")
OWNER_ID = int(os.getenv("OWNER_ID"))

# ==================== VERSION ====================
BOT_VERSION = os.getenv("BOT_VERSION", "1.1.0")
BOT_CHANGELOG = os.getenv("BOT_CHANGELOG", "").strip()

# ==================== GROUPS / CHANNELS ====================
MAIN_GROUP_ID = int(os.getenv("MAIN_GROUP_ID"))
MAIN_GROUP_LINK = os.getenv("MAIN_GROUP_LINK")
UPDATE_CHANNEL_LINK = os.getenv("UPDATE_CHANNEL_LINK")
UPDATE_CHANNEL_USERNAME = os.getenv("UPDATE_CHANNEL_USERNAME")
UPDATE_CHANNEL_ID = int(os.getenv("UPDATE_CHANNEL_ID", "0"))

# ==================== CHANNEL STORAGE ====================
STORAGE_CHANNEL_ID = int(os.getenv("STORAGE_CHANNEL_ID", "0"))
STORAGE_CHANNEL_USERNAME = os.getenv("STORAGE_CHANNEL_USERNAME", "").strip()

# ==================== TIMEZONE ====================
TIMEZONE = timezone(timedelta(hours=6, minutes=30))

# ==================== PATHS ====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
TEMP_DIR = os.path.join(BASE_DIR, "temp")
IMAGES_DIR = os.path.join(BASE_DIR, "images")
FONTS_DIR = os.path.join(BASE_DIR, "fonts")

for dir_path in [DATA_DIR, TEMP_DIR, IMAGES_DIR, FONTS_DIR]:
    os.makedirs(dir_path, exist_ok=True)

# ==================== IMAGES ====================
WANTED_IMAGE = os.path.join(IMAGES_DIR, "wanted-template.jpg")

SHOP_IMAGE = "AgACAgUAAxkBAAICu2oqK3bgToJqNwGFzyWTzgbS-y9MAAIQEWsb4AlRVXPULjxuULJUAAgBAAMCAAN4AAceBA"
TOP_IMAGE = "AgACAgUAAxkBAAICyWoqLGt8PjhUmTEugDPwk8U9zHrzAAIXEWsb4AlRVSJ5icFV9opfAAgBAAMCAAN4AAceBA"
HAKI_IMAGE = "AgACAgUAAxkBAAICv2oqLClyc0ES0u2wza1AolJaTzpDAAISEWsb4AlRVSiALuqNoR59AAgBAAMCAAN4AAceBA"
FRUIT_IMAGE = "AgACAgUAAxkBAAICwWoqLDXAXPv4yCsI3Kei1BtQ1L4RAAITEWsb4AlRVRjeEw3j4qhRAAgBAAMCAAN4AAceBA"
IMU_IMAGE = "AgACAgUAAxkBAAICxWoqLFnvMBTjrVFggf6V7HKpwrfRAAIVEWsb4AlRVSwfYMMBzIaGAAgBAAMCAAN4AAceBA"

LEVEL_UP_IMAGE = "AgACAgUAAxkBAAIHhWqpUS1KvlN3Mt4VRKq7EonBNXyfAAKAEmsbblFIVe9OPP5HWkrLAAgBAAMCAAN5AAceBA"
LEVEL_UP_GIF = ""
LEVEL_UP_GROUP_IMAGE = "AgACAgUAAxkBAAIHhWqpUS1KvlN3Mt4VRKq7EonBNXyfAAKAEmsbblFIVe9OPP5HWkrLAAgBAAMCAAN5AAceBA"
LEVEL_UP_GROUP_GIF = ""
LEVEL_DOWN_IMAGE = "AgACAgUAAxkBAAIHh2qpUTJnv7UCjTjaWGHRokiKOnbcAAKBEmsbblFIVSQwiO50psBhAAgBAAMCAAN5AAceBA"
LEVEL_DOWN_GIF = ""
LEVEL_DOWN_GROUP_IMAGE = "AgACAgUAAxkBAAIHh2qpUTJnv7UCjTjaWGHRokiKOnbcAAKBEmsbblFIVSQwiO50psBhAAgBAAMCAAN5AAceBA"
LEVEL_DOWN_GROUP_GIF = ""

WIN_GIF = "CgACAgUAAxkBAAIC02oqLO0DInIooeD5XTaPRGKqgzfKAAJGJAAC4AlRVQUM8S3wHjocHgQ"
WIN_IMAGE = ""
LOSE_GIF = "CgACAgUAAxkBAAIC0WoqLOSTj5mCBZ5FKzW30bO7yDBSAAJFJAAC4AlRVTsYNBXwuYroHgQ"
LOSE_IMAGE = ""
PVP_VICTORY_GIF = "CgACAgUAAxkBAAIC02oqLO0DInIooeD5XTaPRGKqgzfKAAJGJAAC4AlRVQUM8S3wHjocHgQ"
PVP_VICTORY_IMAGE = ""
PVP_DEFEAT_GIF = "CgACAgUAAxkBAAIC0WoqLOSTj5mCBZ5FKzW30bO7yDBSAAJFJAAC4AlRVTsYNBXwuYroHgQ"
PVP_DEFEAT_IMAGE = ""

NIKA_GIF = "CgACAgUAAxkBAAICz2oqLMrofO0NIz3WvMZPuQorS0t4AAJEJAAC4AlRVWosqgUqLKsCHgQ"
NIKA_IMAGE = "AgACAgUAAxkBAAICx2oqLGEnINrroO3qSpb_c8S3LCVcAAIWEWsb4AlRVWRnZVpRQa5EAAgBAAMCAAN4AAceBA"

# ==================== DATA FILES ====================
USERS_FILE = os.path.join(DATA_DIR, "users.json")
NORMAL_CHARS_FILE = os.path.join(DATA_DIR, "normal_chars.json")
MYTHICAL_CHARS_FILE = os.path.join(DATA_DIR, "mythical_chars.json")
GBANNED_FILE = os.path.join(DATA_DIR, "gbanned.json")
TEMP_BANNED_FILE = os.path.join(DATA_DIR, "temp_banned.json")
ADMINS_FILE = os.path.join(DATA_DIR, "admins.json")

# ==================== GAME SETTINGS ====================
VAULT_CAPS = {1: 25_000_000, 2: 25_000_000_000, 3: 500_000_000_000}
HAKI_NAMES = {"obv": "Observation", "arm": "Armament", "conq": "Conqueror's"}
GIVEAWAY_DM_MIN_PRIZE = 10_000_000

# ==================== HAKI EFFECTS ====================
OBSERVATION_THRESHOLDS = {0: 4, 1: 4, 2: 3, 3: 2}
ARMAMENT_MULTIPLIERS = {0: 1.00, 1: 1.30, 2: 1.60, 3: 2.00}
ARMAMENT_ADV_SHIELD_IGNORE = 0.50
CONQ_AUTOWIN_CHANCE = {0: 0.00, 1: 0.10, 2: 0.20, 3: 0.30, 4: 0.30}
SHIELD_PENETRATION = {0: 0, 1: 1, 2: 2, 3: 3}
CONQ_PVP_BYPASS_LEVEL = 2
CONQ_LEVEL_BYPASS_LEVEL = 4
SHIELD_NAMES = {0: "None", 1: "Basic", 2: "Advanced", 3: "Ultimate"}
SHIELD_PENETRATED_STEAL_PCT = 0.02

# ==================== ROB SYSTEM ====================
ROB_COOLDOWN = 300
ROB_MAX_PERCENT = 0.20
ROB_BASE_PERCENT = 0.05
ROB_CONQ_BONUS_PER_LEVEL = 0.02
ROB_LEVEL_RANGES = [
    (1, 10, 10),
    (11, 50, 15),
    (51, 100, 20),
    (101, 200, 30),
]

# ==================== HAKI SYSTEM ====================
HAKI_MAX_LEVEL = 3
ADVANCED_REQUIRES_COIN = 1
ADVANCED_BOUNTY_COST = 100_000_000
HAKI_BAR_MAX = 10
HAKI_BAR_PER_USE = 2
HAKI_REGEN_NORMAL = 5400
HAKI_REGEN_ADVANCED = 10800
OBSERVATION_WIN_RATES = {0: None, 1: 2/3, 2: 3/4, 3: 4/5, 4: 4/5}
OBSERVATION_ADV_MONEY_MULTIPLIER = 2.0
ARMAMENT_RECOVERY = {0: 0.0, 1: 0.30, 2: 0.50, 3: 0.70, 4: 1.00}
CONQ_SHIELD_BYPASS = {0: 0, 1: 1, 2: 2, 3: 3, 4: 99}
HAKI_BASE_PRICE = 25_000_000
HAKI_UPGRADE_COSTS = {1: 50_000_000, 2: 100_000_000}
HAKI_SELL_REFUND = 12_500_000

# ==================== PATTERNS ====================
PATTERNS = {
    "pattern1": {"name": "HIGH WIN", "emoji": "🎁", "win_rate": 0.70, "mode": "random"},
    "pattern2": {"name": "BALANCED", "emoji": "⚖️", "win_rate": 0.50, "mode": "random"},
    "pattern3": {"name": "HIGH LOSS", "emoji": "💀", "win_rate": 0.30, "mode": "random"},
    "pattern4": {
        "name": "FIXED SEQUENCE",
        "emoji": "🔮",
        "mode": "sequence",
        "sequences": {
            "bet":  ["t", "h", "t", "h", "t", "h", "h", "h", "t", "t"],
            "dice": ["o", "e", "e", "o", "o", "e", "e", "e", "o", "o"],
        },
    },
}

DEFAULT_PATTERN = "pattern2"

TIME_SCHEDULE = {
    0: "pattern1", 1: "pattern1", 2: "pattern1", 3: "pattern1",
    4: "pattern1", 5: "pattern1",
    6: "pattern2", 7: "pattern2", 8: "pattern2", 9: "pattern2",
    10: "pattern2", 11: "pattern2", 12: "pattern2", 13: "pattern2",
    14: "pattern2", 15: "pattern2", 16: "pattern2", 17: "pattern2",
    18: "pattern3", 19: "pattern3", 20: "pattern3", 21: "pattern3",
    22: "pattern2",
    23: "pattern1",
}

PATTERN_OVERRIDE_HOURS = 6
AUTO_SWITCH_ENABLED = True

# ==================== SHIPS ====================
SHIPS = {
    1: {"name": "Dinghy", "emoji": "🛶", "cost": 0, "pvp_damage_bonus": 0.0, "daily_bonus": 0.0, "xp_bonus": 0.0, "description": "Starting ship"},
    2: {"name": "Caravel", "emoji": "⛵", "cost": 100_000_000, "pvp_damage_bonus": 0.05, "daily_bonus": 0.0, "xp_bonus": 0.0, "description": "+5% PVP"},
    3: {"name": "Brigantine", "emoji": "🚤", "cost": 500_000_000, "pvp_damage_bonus": 0.10, "daily_bonus": 0.05, "xp_bonus": 0.0, "description": "+10% PVP, +5% daily"},
    4: {"name": "Galleon", "emoji": "🚢", "cost": 2_000_000_000, "pvp_damage_bonus": 0.15, "daily_bonus": 0.10, "xp_bonus": 0.05, "description": "+15% PVP, +10% daily, +5% XP"},
    5: {"name": "Man-o'-War", "emoji": "⛴️", "cost": 10_000_000_000, "pvp_damage_bonus": 0.20, "daily_bonus": 0.15, "xp_bonus": 0.10, "description": "+20% PVP, +15% daily, +10% XP"},
    6: {"name": "Thousand Sunny", "emoji": "🦁", "cost": 50_000_000_000, "pvp_damage_bonus": 0.30, "daily_bonus": 0.25, "xp_bonus": 0.20, "description": "+30% PVP, +25% daily, +20% XP"},
}
SHIP_MAX_TIER = 6
SHIP_IMAGES = {1: "", 2: "", 3: "", 4: "", 5: "", 6: ""}

# ==================== FRUIT PRICES ====================
FRUIT_TIER_PRICES = {
    "Good": 25_000_000_000,
    "Medium": 250_000_000,
    "Bad": 25_000_000,
}
FRUIT_SELL_REFUNDS = {k: v // 2 for k, v in FRUIT_TIER_PRICES.items()}

# ==================== FRUIT ICONS ====================
FRUIT_ICONS = {
    "Gomu Gomu no Mi, Model: Nika": "☀️",
    "Gura Gura no Mi": "💥",
    "Yami Yami no Mi": "🕳️",
    "Ope Ope no Mi": "💉",
    "Magu Magu no Mi": "🌋",
    "Pika Pika no Mi": "💡",
    "Uo Uo no Mi, Model: Seiryu": "🐉",
    "Goro Goro no Mi": "⚡",
    "Mori Mori no Mi": "🌳",
    "Hie Hie no Mi": "❄️",
    "Zushi Zushi no Mi": "🌍",
    "Nikyu Nikyu no Mi": "🐾",
    "Tori Tori no Mi, Model: Phoenix": "🦅",
    "Soru Soru no Mi": "🕯️",
    "Hito Hito no Mi, Model: Daibutsu": "🧘",
    "Doku Doku no Mi": "☠️",
    "Ito Ito no Mi": "🕸️",
    "Mochi Mochi no Mi": "🍡",
    "Toshi Toshi no Mi": "⏳",
    "Gasu Gasu no Mi": "☁️",
    "Mera Mera no Mi": "🔥",
    "Hana Hana no Mi": "🌸",
    "Bari Bari no Mi": "🛡️",
    "Jiki Jiki no Mi": "🧲",
    "Kage Kage no Mi": "🖤",
    "Horu Horu no Mi": "💗",
    "Mero Mero no Mi": "💘",
    "Buki Buki no Mi": "🔫",
    "Suna Suna no Mi": "🏜️",
    "Noro Noro no Mi": "🐌",
    "Suke Suke no Mi": "👻",
    "Doa Doa no Mi": "🚪",
    "Fuwa Fuwa no Mi": "🎈",
    "Hobi Hobi no Mi": "🧸",
    "Mira Mira no Mi": "🪞",
    "Bisu Bisu no Mi": "🍪",
    "Pero Pero no Mi": "🍬",
    "Chiyu Chiyu no Mi": "💚",
    "Wara Wara no Mi": "🧵",
    "Guru Guru no Mi": "🌀",
    "Jake Jake no Mi": "🛢️",
    "Pamu Pamu no Mi": "💣",
    "Ton Ton no Mi": "⚖️",
    "Hira Hira no Mi": "🍃",
    "Ishi Ishi no Mi": "🗿",
    "Fude Fude no Mi": "🖌️",
    "Nagi Nagi no Mi": "🌊",
    "Kuri Kuri no Mi": "🍦",
    "Bata Bata no Mi": "🧈",
    "Buku Buku no Mi": "📚",
    "Kuku Kuku no Mi": "🍳",
    "Gocha Gocha no Mi": "🎲",
    "Shiku Shiku no Mi": "🩸",
    "Wapu Wapu no Mi": "💧",
    "Riki Riki no Mi": "💪",
    "Nomi Nomi no Mi": "🐛",
    "Gabu Gabu no Mi": "🥤",
    "Tsutsu Tsutsu no Mi": "🎋",
    "Muchi Muchi no Mi": "🪢",
    "Nori Nori no Mi": "📎",
}

# ==================== FRUIT HELPERS ====================
LEGACY_FRUIT_NAMES = {
    "Hito Hito no Mi, Model: Nika": "Gomu Gomu no Mi, Model: Nika",
}


def normalize_fruit_name(name):
    if not name:
        return name
    return LEGACY_FRUIT_NAMES.get(name, name)


def get_fruit_icon(fruit_full_name):
    if not fruit_full_name:
        return "❓"
    name = normalize_fruit_name(fruit_full_name)
    return FRUIT_ICONS.get(name, "🍎")


def get_fruit_tier(fruit_full_name):
    if not fruit_full_name:
        return None
    name = normalize_fruit_name(fruit_full_name)
    for tier, fruits in DEVIL_FRUITS.items():
        for f in fruits:
            if f["full"] == name:
                return tier
    return None


def get_fruit_by_name(query):
    if not query:
        return None, None
    q = normalize_fruit_name(query.strip()).lower()
    for tier, fruits in DEVIL_FRUITS.items():
        for f in fruits:
            if f["full"].lower() == q or f["name"].lower() == q:
                return f, tier
    for tier, fruits in DEVIL_FRUITS.items():
        for f in fruits:
            if q in f["name"].lower() or q in f["full"].lower():
                return f, tier
    return None, None


def get_fruit_by_full_name(fruit_full_name):
    name = normalize_fruit_name(fruit_full_name)
    for tier, fruits in DEVIL_FRUITS.items():
        for f in fruits:
            if f["full"] == name:
                return f
    return None


# ==================== DEVIL FRUITS ====================
DEVIL_FRUITS = {
    "Good": [
        {"name": "Gomu Gomu no Mi", "model": "Model: Nika", "type": "Mythical Zoan", "full": "Gomu Gomu no Mi, Model: Nika"},
        {"name": "Gura Gura no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Gura Gura no Mi"},
        {"name": "Yami Yami no Mi", "model": "Logia", "type": "Logia", "full": "Yami Yami no Mi"},
        {"name": "Ope Ope no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Ope Ope no Mi"},
        {"name": "Magu Magu no Mi", "model": "Logia", "type": "Logia", "full": "Magu Magu no Mi"},
        {"name": "Pika Pika no Mi", "model": "Logia", "type": "Logia", "full": "Pika Pika no Mi"},
        {"name": "Uo Uo no Mi", "model": "Model: Seiryu", "type": "Mythical Zoan", "full": "Uo Uo no Mi, Model: Seiryu"},
        {"name": "Goro Goro no Mi", "model": "Logia", "type": "Logia", "full": "Goro Goro no Mi"},
        {"name": "Mori Mori no Mi", "model": "Logia", "type": "Logia", "full": "Mori Mori no Mi"},
        {"name": "Hie Hie no Mi", "model": "Logia", "type": "Logia", "full": "Hie Hie no Mi"},
        {"name": "Zushi Zushi no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Zushi Zushi no Mi"},
        {"name": "Nikyu Nikyu no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Nikyu Nikyu no Mi"},
        {"name": "Tori Tori no Mi", "model": "Model: Phoenix", "type": "Mythical Zoan", "full": "Tori Tori no Mi, Model: Phoenix"},
        {"name": "Soru Soru no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Soru Soru no Mi"},
        {"name": "Hito Hito no Mi", "model": "Model: Daibutsu", "type": "Mythical Zoan", "full": "Hito Hito no Mi, Model: Daibutsu"},
        {"name": "Doku Doku no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Doku Doku no Mi"},
        {"name": "Ito Ito no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Ito Ito no Mi"},
        {"name": "Mochi Mochi no Mi", "model": "Special Paramecia", "type": "Special Paramecia", "full": "Mochi Mochi no Mi"},
        {"name": "Toshi Toshi no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Toshi Toshi no Mi"},
        {"name": "Gasu Gasu no Mi", "model": "Logia", "type": "Logia", "full": "Gasu Gasu no Mi"},
    ],
    "Medium": [
        {"name": "Mera Mera no Mi", "model": "Logia", "type": "Logia", "full": "Mera Mera no Mi"},
        {"name": "Hana Hana no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Hana Hana no Mi"},
        {"name": "Bari Bari no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Bari Bari no Mi"},
        {"name": "Jiki Jiki no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Jiki Jiki no Mi"},
        {"name": "Kage Kage no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Kage Kage no Mi"},
        {"name": "Horu Horu no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Horu Horu no Mi"},
        {"name": "Mero Mero no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Mero Mero no Mi"},
        {"name": "Buki Buki no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Buki Buki no Mi"},
        {"name": "Suna Suna no Mi", "model": "Logia", "type": "Logia", "full": "Suna Suna no Mi"},
        {"name": "Noro Noro no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Noro Noro no Mi"},
        {"name": "Suke Suke no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Suke Suke no Mi"},
        {"name": "Doa Doa no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Doa Doa no Mi"},
        {"name": "Fuwa Fuwa no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Fuwa Fuwa no Mi"},
        {"name": "Hobi Hobi no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Hobi Hobi no Mi"},
        {"name": "Mira Mira no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Mira Mira no Mi"},
        {"name": "Bisu Bisu no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Bisu Bisu no Mi"},
        {"name": "Pero Pero no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Pero Pero no Mi"},
        {"name": "Chiyu Chiyu no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Chiyu Chiyu no Mi"},
        {"name": "Wara Wara no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Wara Wara no Mi"},
        {"name": "Guru Guru no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Guru Guru no Mi"},
    ],
    "Bad": [
        {"name": "Jake Jake no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Jake Jake no Mi"},
        {"name": "Pamu Pamu no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Pamu Pamu no Mi"},
        {"name": "Ton Ton no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Ton Ton no Mi"},
        {"name": "Hira Hira no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Hira Hira no Mi"},
        {"name": "Ishi Ishi no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Ishi Ishi no Mi"},
        {"name": "Fude Fude no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Fude Fude no Mi"},
        {"name": "Nagi Nagi no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Nagi Nagi no Mi"},
        {"name": "Kuri Kuri no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Kuri Kuri no Mi"},
        {"name": "Bata Bata no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Bata Bata no Mi"},
        {"name": "Buku Buku no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Buku Buku no Mi"},
        {"name": "Kuku Kuku no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Kuku Kuku no Mi"},
        {"name": "Gocha Gocha no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Gocha Gocha no Mi"},
        {"name": "Shiku Shiku no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Shiku Shiku no Mi"},
        {"name": "Wapu Wapu no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Wapu Wapu no Mi"},
        {"name": "Riki Riki no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Riki Riki no Mi"},
        {"name": "Nomi Nomi no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Nomi Nomi no Mi"},
        {"name": "Gabu Gabu no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Gabu Gabu no Mi"},
        {"name": "Tsutsu Tsutsu no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Tsutsu Tsutsu no Mi"},
        {"name": "Muchi Muchi no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Muchi Muchi no Mi"},
        {"name": "Nori Nori no Mi", "model": "Paramecia", "type": "Paramecia", "full": "Nori Nori no Mi"},
    ],
}