# data_manager.py
import json
import os
import tempfile
import threading
import time
import asyncio
from collections import defaultdict

from config import (
    USERS_FILE, NORMAL_CHARS_FILE, MYTHICAL_CHARS_FILE,
    GBANNED_FILE, TEMP_BANNED_FILE, ADMINS_FILE, OWNER_ID, DATA_DIR,
    DEFAULT_PATTERN,
)
from models import Player

# ==================== GLOBAL STATE ====================
user_data = {}
normal_characters = []
mythical_characters = []
active_challenges = {}
message_count = defaultdict(int)
pending_trades = {}
GBANNED = set()
TEMP_BANNED = {}
ADMINS = set()
bot_groups = set()
banned_players_info = {}

# World Boss
world_boss_active = False
world_boss_hp = 0
world_boss_damage = defaultdict(int)

# Giveaways
active_giveaways = {}
active_global_giveaway = None

# Pending forwards
pending_forwards = {}

# Pattern state
current_pattern = DEFAULT_PATTERN

pattern_override = {
    "active": False,
    "pattern": None,
    "expires_at": 0,
}

sequence_positions = {
    "__global__": {"bet": 0, "dice": 0},
}

# Files
PATTERN_STATE_FILE = os.path.join(DATA_DIR, "pattern_state.json")
CHAR_ID_COUNTER_FILE = os.path.join(DATA_DIR, "char_id_counter.json")
GROUP_CACHE_FILE = os.path.join(DATA_DIR, "group_cache.json")

_char_id_lock = threading.Lock()
group_cache = {}


# ==================== CHANNEL STORAGE HOOK ====================
_channel_client = None
_last_sync = {}
SYNC_COOLDOWN = 60  # seconds between uploads of the same file


def set_channel_client(client):
    """Called from bot.py at startup to enable channel sync."""
    global _channel_client
    _channel_client = client


async def _do_upload(client, path, fname):
    """Upload + cleanup in one go."""
    try:
        from channel_storage import upload_gzipped, delete_old_from_channel
        await upload_gzipped(client, path, fname)
        await delete_old_from_channel(client, fname, keep=3)
    except Exception as e:
        print(f"[data_manager] upload error ({fname}): {e}")


def _sync_to_channel(fname):
    """Trigger a background upload of a file to the storage channel."""
    if not _channel_client:
        return
    now = time.time()
    if now - _last_sync.get(fname, 0) < SYNC_COOLDOWN:
        return
    _last_sync[fname] = now

    try:
        path = os.path.join(DATA_DIR, fname)
        if not os.path.exists(path):
            return

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = getattr(_channel_client, "loop", None)
            if loop is None:
                return

        loop.create_task(_do_upload(_channel_client, path, fname))
    except Exception as e:
        print(f"[data_manager] sync error ({fname}): {e}")


# ==================== ATOMIC WRITE ====================
def _atomic_json_write(path, payload):
    dir_name = os.path.dirname(path) or "."
    os.makedirs(dir_name, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=dir_name, delete=False, suffix=".tmp", encoding="utf-8"
    ) as tmp:
        json.dump(payload, tmp, indent=2, ensure_ascii=False)
        tmp_path = tmp.name
    os.replace(tmp_path, path)


# ==================== PATTERN STATE ====================
def save_pattern_state():
    try:
        _atomic_json_write(PATTERN_STATE_FILE, {
            "current_pattern": current_pattern,
            "pattern_override": pattern_override,
            "sequence_positions": sequence_positions,
        })
        _sync_to_channel("pattern_state.json")
    except Exception as e:
        print(f"[pattern] save failed: {e}")


def load_pattern_state():
    global current_pattern, pattern_override, sequence_positions
    try:
        with open(PATTERN_STATE_FILE, "r") as f:
            data = json.load(f)

        current_pattern = data.get("current_pattern", DEFAULT_PATTERN)

        # Mutate in place so imported references stay valid
        new_override = data.get("pattern_override", {
            "active": False, "pattern": None, "expires_at": 0,
        })
        pattern_override.clear()
        pattern_override.update(new_override)

        new_seq = data.get("sequence_positions", {
            "__global__": {"bet": 0, "dice": 0},
        })
        sequence_positions.clear()
        sequence_positions.update(new_seq)

        print(f"[DEBUG] Loaded pattern state: {current_pattern}")
    except FileNotFoundError:
        pass
    except Exception as e:
        print(f"[pattern] load failed: {e}")


def get_current_pattern():
    import time as _t
    from config import TIME_SCHEDULE, AUTO_SWITCH_ENABLED
    from datetime import datetime

    if pattern_override.get("active"):
        if _t.time() < pattern_override.get("expires_at", 0):
            return pattern_override["pattern"]
        pattern_override["active"] = False
        pattern_override["pattern"] = None
        pattern_override["expires_at"] = 0
        save_pattern_state()

    if AUTO_SWITCH_ENABLED:
        hour = datetime.now().hour
        auto = TIME_SCHEDULE.get(hour)
        if auto:
            return auto

    return DEFAULT_PATTERN


def set_current_pattern(p, manual=False):
    global current_pattern
    import time as _t

    if p not in ("pattern1", "pattern2", "pattern3", "pattern4"):
        return False

    if manual:
        from config import PATTERN_OVERRIDE_HOURS
        pattern_override["active"] = True
        pattern_override["pattern"] = p
        pattern_override["expires_at"] = _t.time() + (PATTERN_OVERRIDE_HOURS * 3600)
    else:
        current_pattern = p

    save_pattern_state()
    return True


def clear_pattern_override():
    pattern_override["active"] = False
    pattern_override["pattern"] = None
    pattern_override["expires_at"] = 0
    save_pattern_state()


def get_pattern_override():
    return pattern_override


def get_override_status():
    import time as _t
    if not pattern_override.get("active"):
        return {"active": False}
    remaining = max(0, int(pattern_override.get("expires_at", 0) - _t.time()))
    return {
        "active": True,
        "pattern": pattern_override.get("pattern"),
        "remaining_seconds": remaining,
    }


def get_sequence_position(user_id, game):
    key = str(user_id) if user_id else "__global__"
    if key not in sequence_positions:
        sequence_positions[key] = {}
    return sequence_positions[key].get(game, 0)


def advance_sequence(user_id, game, sequence_length):
    key = str(user_id) if user_id else "__global__"
    if key not in sequence_positions:
        sequence_positions[key] = {}
    pos = sequence_positions[key].get(game, 0)
    sequence_positions[key][game] = (pos + 1) % sequence_length
    save_pattern_state()
    return pos


def reset_sequence(user_id=None):
    if user_id is None:
        sequence_positions.clear()
        sequence_positions["__global__"] = {"bet": 0, "dice": 0}
    else:
        key = str(user_id)
        if key in sequence_positions:
            del sequence_positions[key]
    save_pattern_state()


# ==================== GROUP CACHE ====================
def load_group_cache():
    global group_cache
    try:
        with open(GROUP_CACHE_FILE, "r") as f:
            data = json.load(f)
        group_cache.clear()
        group_cache.update(data)
    except (FileNotFoundError, json.JSONDecodeError):
        group_cache.clear()


def save_group_cache():
    try:
        _atomic_json_write(GROUP_CACHE_FILE, group_cache)
        _sync_to_channel("group_cache.json")
    except Exception as e:
        print(f"[group_cache] save failed: {e}")


def get_cached_group(gid):
    import time as _t
    entry = group_cache.get(str(gid))
    if not entry:
        return None
    if _t.time() - entry.get("cached_at", 0) > 86400:
        return None
    return entry


def set_cached_group(gid, title, username, invite_link):
    import time as _t
    group_cache[str(gid)] = {
        "title": title,
        "username": username,
        "invite_link": invite_link,
        "cached_at": _t.time(),
    }
    save_group_cache()


# ==================== CHARACTER ID ====================
def get_next_char_id():
    """Smallest available ID (reuses deleted IDs)."""
    with _char_id_lock:
        used_ids = set()
        for c in normal_characters:
            cid = c.get("id")
            if isinstance(cid, int) and cid > 0:
                used_ids.add(cid)
        for c in mythical_characters:
            cid = c.get("id")
            if isinstance(cid, int) and cid > 0:
                used_ids.add(cid)

        next_id = 1
        while next_id in used_ids:
            next_id += 1

        try:
            _atomic_json_write(CHAR_ID_COUNTER_FILE, {"last_assigned": next_id})
            _sync_to_channel("char_id_counter.json")
        except Exception:
            pass

        return next_id


def reset_char_id_counter():
    with _char_id_lock:
        _atomic_json_write(CHAR_ID_COUNTER_FILE, {"next_id": 1})
        _sync_to_channel("char_id_counter.json")


# ==================== CHARACTER LOOKUP ====================
def get_character_by_id(char_id):
    for c in normal_characters:
        if c.get("id") == char_id:
            return c
    for c in mythical_characters:
        if c.get("id") == char_id:
            return c
    return None


def get_character_by_name(name):
    if not name or not isinstance(name, str):
        return None
    target = name.strip().lower()
    if not target:
        return None
    for c in normal_characters:
        cname = c.get("name", "")
        if isinstance(cname, str) and cname.lower() == target:
            return c
    for c in mythical_characters:
        cname = c.get("name", "")
        if isinstance(cname, str) and cname.lower() == target:
            return c
    return None


# ==================== ADMIN CHECK ====================
def is_admin_or_owner(user_id):
    try:
        return int(user_id) == int(OWNER_ID) or int(user_id) in ADMINS
    except (ValueError, TypeError):
        return False


# ==================== PLAYER ====================
def get_player(uid, user=None):
    uid_str = str(uid)
    if uid_str not in user_data:
        user_data[uid_str] = Player(uid)

    p = user_data[uid_str]

    if user is not None:
        try:
            if getattr(user, "first_name", None):
                p.name = user.first_name
            if getattr(user, "username", None):
                p.username = user.username
        except Exception:
            pass

    return p


# ==================== SAVE ====================
def save_data():
    try:
        data = {uid: p.to_dict() for uid, p in user_data.items()}
        _atomic_json_write(USERS_FILE, data)
        _sync_to_channel("users.json")
    except Exception as e:
        print(f"[DEBUG] Error saving users: {e}")


def save_normal_chars():
    try:
        _atomic_json_write(NORMAL_CHARS_FILE, normal_characters)
        _sync_to_channel("normal_chars.json")
    except Exception as e:
        print(f"[DEBUG] Error saving normal chars: {e}")


def save_mythical_chars():
    try:
        _atomic_json_write(MYTHICAL_CHARS_FILE, mythical_characters)
        _sync_to_channel("mythical_chars.json")
    except Exception as e:
        print(f"[DEBUG] Error saving mythical chars: {e}")


def save_banned():
    try:
        _atomic_json_write(GBANNED_FILE, list(GBANNED))
        _sync_to_channel("gbanned.json")
    except Exception as e:
        print(f"[DEBUG] Error saving global bans: {e}")


def save_temp_banned():
    try:
        data = {uid: unban_time for uid, unban_time in TEMP_BANNED.items()}
        _atomic_json_write(TEMP_BANNED_FILE, data)
        _sync_to_channel("temp_banned.json")
    except Exception as e:
        print(f"[DEBUG] Error saving temp bans: {e}")


def save_admins():
    try:
        _atomic_json_write(ADMINS_FILE, list(ADMINS))
        _sync_to_channel("admins.json")
    except Exception as e:
        print(f"[DEBUG] Error saving admins: {e}")


def save_bot_groups():
    try:
        f = os.path.join(DATA_DIR, "bot_groups.json")
        _atomic_json_write(f, list(bot_groups))
        _sync_to_channel("bot_groups.json")
    except Exception as e:
        print(f"[DEBUG] Error saving bot groups: {e}")


def save_banned_players_info():
    try:
        f = os.path.join(DATA_DIR, "banned_players_info.json")
        _atomic_json_write(f, banned_players_info)
        _sync_to_channel("banned_players_info.json")
    except Exception as e:
        print(f"Error saving banned players info: {e}")


# ==================== LOAD ====================
def load_data():
    global user_data, normal_characters, mythical_characters
    global GBANNED, TEMP_BANNED, ADMINS, banned_players_info, bot_groups

    print("[DEBUG] Loading data...")

    # Users — mutate in place
    try:
        with open(USERS_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("users.json root must be a dict")
        user_data.clear()
        for uid, pdata in data.items():
            try:
                user_data[str(uid)] = Player.from_dict(int(uid), pdata)
            except (ValueError, TypeError):
                try:
                    user_data[str(uid)] = Player.from_dict(uid, pdata)
                except Exception as e:
                    print(f"[DEBUG] Skipping bad user {uid}: {e}")
        print(f"[DEBUG] Loaded {len(user_data)} users")
    except FileNotFoundError:
        user_data.clear()
        save_data()
    except Exception as e:
        print(f"[DEBUG] Error loading users: {e}")
        user_data.clear()

    # Normal characters — mutate in place
    try:
        with open(NORMAL_CHARS_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, list):
            data = []
        normal_characters.clear()
        normal_characters.extend(data)
        print(f"[DEBUG] Loaded {len(normal_characters)} normal characters")
    except FileNotFoundError:
        normal_characters.clear()
        save_normal_chars()
    except Exception as e:
        print(f"[DEBUG] Error loading normal chars: {e}")
        normal_characters.clear()

    # Mythical characters — mutate in place
    try:
        with open(MYTHICAL_CHARS_FILE, "r") as f:
            data = json.load(f)
        if not isinstance(data, list):
            data = []
        mythical_characters.clear()
        mythical_characters.extend(data)
        print(f"[DEBUG] Loaded {len(mythical_characters)} mythical characters")
    except FileNotFoundError:
        mythical_characters.clear()
        save_mythical_chars()
    except Exception as e:
        print(f"[DEBUG] Error loading mythical chars: {e}")
        mythical_characters.clear()

    # Global bans — mutate in place
    try:
        with open(GBANNED_FILE, "r") as f:
            data = json.load(f)
        GBANNED.clear()
        GBANNED.update(data)
        print(f"[DEBUG] Loaded {len(GBANNED)} global bans")
    except FileNotFoundError:
        GBANNED.clear()
        save_banned()
    except Exception as e:
        print(f"[DEBUG] Error loading global bans: {e}")
        GBANNED.clear()

    # Temp bans — mutate in place
    try:
        with open(TEMP_BANNED_FILE, "r") as f:
            raw = json.load(f)
        TEMP_BANNED.clear()
        for uid, t in raw.items():
            try:
                TEMP_BANNED[int(uid)] = float(t)
            except (ValueError, TypeError):
                pass
        print(f"[DEBUG] Loaded {len(TEMP_BANNED)} temp bans")
    except FileNotFoundError:
        TEMP_BANNED.clear()
        save_temp_banned()
    except Exception as e:
        print(f"[DEBUG] Error loading temp bans: {e}")
        TEMP_BANNED.clear()

    # Admins — mutate in place
    try:
        with open(ADMINS_FILE, "r") as f:
            data = json.load(f)
        ADMINS.clear()
        ADMINS.update(data)
        print(f"[DEBUG] Loaded {len(ADMINS)} admins")
    except FileNotFoundError:
        ADMINS.clear()
        save_admins()
    except Exception as e:
        print(f"[DEBUG] Error loading admins: {e}")
        ADMINS.clear()

    load_bot_groups()
    load_banned_players_info()
    load_pattern_state()
    load_group_cache()

    print(
        f"[DEBUG] FINAL — Users: {len(user_data)}, "
        f"Normal: {len(normal_characters)}, "
        f"Mythical: {len(mythical_characters)}, "
        f"Groups: {len(bot_groups)}"
    )


# ==================== CHARACTER MANAGEMENT ====================
def add_normal_character(name, image):
    char_id = get_next_char_id()
    normal_characters.append({
        "id": char_id,
        "name": name,
        "image": image,
        "rarity": "NORMAL",
        "created_at": time.time(),
    })
    save_normal_chars()
    return True


def add_mythical_character(name, image):
    char_id = get_next_char_id()
    mythical_characters.append({
        "id": char_id,
        "name": name,
        "image": image,
        "rarity": "MYTHICAL",
        "created_at": time.time(),
    })
    save_mythical_chars()
    return True


def delete_normal_character(char_id):
    """Delete by ID + remove from all players."""
    global normal_characters
    for i, c in enumerate(normal_characters):
        if c.get("id") == char_id:
            deleted = normal_characters.pop(i)
            name = deleted.get("name")

            for chat_id in list(active_challenges.keys()):
                ch = active_challenges[chat_id]
                if ch.get("char", {}).get("id") == char_id:
                    del active_challenges[chat_id]

            for tid in list(pending_trades.keys()):
                trade = pending_trades[tid]
                sel = trade.get("selected_char")
                if sel and sel.get("id") == char_id:
                    del pending_trades[tid]

            for player in user_data.values():
                player.captured_chars = [
                    x for x in player.captured_chars
                    if x.get("id") != char_id and x.get("name") != name
                ]
            save_normal_chars()
            save_data()
            return deleted
    return None


def delete_mythical_character(char_id):
    """Delete by ID + remove from all players."""
    global mythical_characters
    for i, c in enumerate(mythical_characters):
        if c.get("id") == char_id:
            deleted = mythical_characters.pop(i)
            name = deleted.get("name")

            for chat_id in list(active_challenges.keys()):
                ch = active_challenges[chat_id]
                if ch.get("char", {}).get("id") == char_id:
                    del active_challenges[chat_id]

            for tid in list(pending_trades.keys()):
                trade = pending_trades[tid]
                sel = trade.get("selected_char")
                if sel and sel.get("id") == char_id:
                    del pending_trades[tid]

            for player in user_data.values():
                player.captured_chars = [
                    x for x in player.captured_chars
                    if x.get("id") != char_id and x.get("name") != name
                ]
            save_mythical_chars()
            save_data()
            return deleted
    return None


def get_normal_characters():
    return normal_characters


def get_mythical_characters():
    return mythical_characters


# ==================== TEMP BAN ====================
def check_temp_bans():
    now = time.time()
    expired = [uid for uid, t in TEMP_BANNED.items() if t <= now]
    for uid in expired:
        del TEMP_BANNED[uid]
    if expired:
        save_temp_banned()


# ==================== BOT GROUPS ====================
def load_bot_groups():
    global bot_groups
    try:
        f = os.path.join(DATA_DIR, "bot_groups.json")
        if os.path.exists(f):
            with open(f, "r") as fp:
                data = json.load(fp)
            bot_groups.clear()
            bot_groups.update(data)
        else:
            bot_groups.clear()
            save_bot_groups()
    except Exception as e:
        print(f"[DEBUG] Error loading bot groups: {e}")
        bot_groups.clear()


def add_bot_group(group_id):
    bot_groups.add(group_id)
    save_bot_groups()


def remove_bot_group(group_id):
    if group_id in bot_groups:
        bot_groups.discard(group_id)
        save_bot_groups()


def get_bot_groups():
    return bot_groups


# ==================== BANNED INFO ====================
def load_banned_players_info():
    global banned_players_info
    try:
        f = os.path.join(DATA_DIR, "banned_players_info.json")
        if os.path.exists(f):
            with open(f, "r") as fp:
                data = json.load(fp)
            banned_players_info.clear()
            banned_players_info.update(data)
        else:
            banned_players_info.clear()
    except Exception:
        banned_players_info.clear()


def add_banned_player_info(user_id, user_name, user_username, reason,
                           banned_by, banned_by_name):
    banned_players_info[str(user_id)] = {
        "reason": reason,
        "banned_by": banned_by,
        "banned_by_name": banned_by_name,
        "banned_at": time.time(),
        "banned_at_str": time.strftime("%Y-%m-%d %H:%M:%S"),
        "user_name": user_name,
        "user_username": user_username,
    }
    save_banned_players_info()


def remove_banned_player_info(user_id):
    if str(user_id) in banned_players_info:
        del banned_players_info[str(user_id)]
        save_banned_players_info()


def get_banned_player_info(user_id):
    return banned_players_info.get(str(user_id), {})


# ==================== TRADES ====================
def add_trade(trade_id, trade_data):
    pending_trades[trade_id] = trade_data


def get_trade(trade_id):
    return pending_trades.get(trade_id)


def remove_trade(trade_id):
    if trade_id in pending_trades:
        del pending_trades[trade_id]


# ==================== CHALLENGE ====================
def get_active_challenge(chat_id):
    return active_challenges.get(chat_id)


def set_active_challenge(chat_id, challenge_data):
    active_challenges[chat_id] = challenge_data


def remove_active_challenge(chat_id):
    if chat_id in active_challenges:
        del active_challenges[chat_id]


def increment_message_count(chat_id):
    message_count[chat_id] = message_count.get(chat_id, 0) + 1
    return message_count[chat_id]


def reset_message_count(chat_id):
    message_count[chat_id] = 0


# ==================== WORLD BOSS ====================
def set_world_boss_active(active):
    global world_boss_active
    world_boss_active = bool(active)


def get_world_boss_active():
    return world_boss_active


def get_world_boss_hp():
    return world_boss_hp


def set_world_boss_hp(hp):
    global world_boss_hp
    world_boss_hp = hp


def add_world_boss_damage(user_id, damage):
    world_boss_damage[user_id] = world_boss_damage.get(user_id, 0) + damage


def get_world_boss_damage():
    return world_boss_damage


def clear_world_boss_damage():
    world_boss_damage.clear()


# ==================== GIVEAWAYS ====================
def add_giveaway(key, giveaway_data):
    active_giveaways[key] = giveaway_data


def get_giveaway(key):
    return active_giveaways.get(key)


def remove_giveaway(key):
    if key in active_giveaways:
        del active_giveaways[key]


def get_all_giveaways():
    return active_giveaways


def get_global_giveaway():
    return active_global_giveaway


def set_global_giveaway(giveaway_data):
    global active_global_giveaway
    active_global_giveaway = giveaway_data


def clear_global_giveaway():
    global active_global_giveaway
    active_global_giveaway = None


def is_global_giveaway_active():
    return active_global_giveaway is not None


# ==================== PENDING FORWARDS ====================
def set_pending_forward(user_id, data):
    pending_forwards[user_id] = data


def get_pending_forward(user_id):
    return pending_forwards.get(user_id)


def clear_pending_forward(user_id):
    if user_id in pending_forwards:
        del pending_forwards[user_id]


def get_all_pending_forwards():
    return pending_forwards