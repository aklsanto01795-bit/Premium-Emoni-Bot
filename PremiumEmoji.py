import telebot
from telebot import types
from telebot.types import MessageEntity
import random
import emoji
import time
import os
import json
from datetime import datetime
import re as _re

# ╔══════════════════════════════════════════════════════════════╗
# ║   🔥 𝗖𝗛𝗦 𝗣ʀᴇᴍɪᴜᴍ 𝗥ᴏʙᴏᴛ 🔥                              ║
# ║   Developer: @ModderSanto                                  ║
# ╚══════════════════════════════════════════════════════════════╝

TOKEN    = "8810274924:AAHP8vYwLjIWHxm7q7793vsrGe_9ttfAZ80"
ADMIN_ID = 8889726455
bot      = telebot.TeleBot(TOKEN, num_threads=1)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BOT STATE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
bot_active   = True
user_db_file = "users.json"

def load_users():
    if os.path.exists(user_db_file):
        with open(user_db_file, "r") as f:
            return set(json.load(f))
    return set()

def save_users(users: set):
    with open(user_db_file, "w") as f:
        json.dump(list(users), f)

all_users: set = load_users()

USER_STATS_FILE = "user_stats.json"
def load_user_stats():
    if os.path.exists(USER_STATS_FILE):
        try:
            with open(USER_STATS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception as e:
            print(f"⚠️ Could not load user stats: {e}")
    return {}

def save_user_stats(data):
    try:
        with open(USER_STATS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"⚠️ Could not save user stats: {e}")

user_stats = load_user_stats()
def get_user_stats(uid):
    key = str(uid)
    if not isinstance(user_stats.get(key), dict):
        user_stats[key] = {"posts": 0, "coins": 0, "channel_force_posts": 0, "group_force_posts": 0}
    st = user_stats[key]
    st.setdefault("posts", 0); st.setdefault("coins", 0)
    st.setdefault("channel_force_posts", 0); st.setdefault("group_force_posts", 0)
    return st

def award_post_reward(uid):
    st = get_user_stats(uid)
    st["posts"] += 1
    st["coins"] += 10
    save_user_stats(user_stats)

def total_stat(name):
    return sum(int(v.get(name, 0)) for v in user_stats.values() if isinstance(v, dict))


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAIN BRAND EMOJI (used for the bot's own UI text, not user posts)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MAIN_EMOJI_ID = "6010060634803148161"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PLACEHOLDER CHARACTER
#  We use 🌟 (U+1F31F) — it is OUTSIDE BMP, so UTF-16 length = 2
#  This matches Telegram's expected custom_emoji entity length=2
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PLACEHOLDER = "🌟"   # U+1F31F — surrogate pair — UTF-16 length = 2

def _utf16_len(ch: str) -> int:
    """Return the UTF-16 code-unit length of a single character."""
    return len(ch.encode("utf-16-le")) // 2

# Confirm placeholder length is 2 at startup
assert _utf16_len(PLACEHOLDER) == 2, "Placeholder must be a surrogate-pair emoji (UTF-16 len 2)"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  TEMP STORAGE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
temp_data = {}

# Short membership cache reduces Telegram API calls on every button/message.
# Verify itself always performs a fresh check.
JOIN_CACHE_TTL = 8
_join_cache = {}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PREMIUM EMOJI DATABASE (premium_emojis.json ONLY)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
PREMIUM_EMOJI_DB_FILE = "premium_emojis.json"

def load_premium_emoji_db() -> dict:
    """Loads and parses premium_emojis.json supporting both flat and structured combined_packs formats."""
    combined_db = {}
    filepath = PREMIUM_EMOJI_DB_FILE

    def _add_local(emj: str, cid):
        if not emj or not cid:
            return
        emj = str(emj).strip()
        cid = str(cid).strip()
        # Security check: MUST contain only digits (0-9) to prevent API crashes
        if not cid.isdigit() or not emoji.is_emoji(emj):
            return
        existing = combined_db.setdefault(emj, [])
        if cid not in existing:
            existing.append(cid)

    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if isinstance(data, dict):
                # Case 1: Structured "combined_packs" format
                if "combined_packs" in data:
                    for pack in data["combined_packs"]:
                        if isinstance(pack, dict) and "emojis" in pack:
                            for item in pack["emojis"]:
                                if isinstance(item, dict):
                                    _add_local(item.get("emoji"), item.get("id") or item.get("custom_emoji_id"))
                # Case 2: Flat dictionary format
                else:
                    for emj, val in data.items():
                        if isinstance(val, list):
                            for cid in val:
                                _add_local(emj, cid)
                        else:
                            _add_local(emj, val)
            elif isinstance(data, list):
                # Case 3: Flat list format
                for entry in data:
                    if isinstance(entry, dict):
                        _add_local(entry.get("emoji"), entry.get("id") or entry.get("custom_emoji_id"))
        except Exception as e:
            print(f"⚠️ Could not load {filepath}: {e}")
    return combined_db

def save_premium_emoji_db(db: dict):
    """Saves updates cleanly back to premium_emojis.json."""
    try:
        with open(PREMIUM_EMOJI_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, ensure_ascii=False, indent=1)
    except Exception as e:
        print(f"⚠️ Could not save database: {e}")

# Master emoji map loaded from the single source file [premium_emojis.json]
EMOJI_TO_PREMIUM = load_premium_emoji_db()

# Hardcode requested custom emoji IDs to prevent mismatches
EMOJI_TO_PREMIUM["➿"] = ["6329854094252970694"]
EMOJI_TO_PREMIUM["📢"] = ["6242454421767198453"]

def _flatten_ids(db: dict) -> list:
    ids = []
    for id_list in db.values():
        ids.extend(id_list)
    return ids

PREMIUM_EMOJIS = _flatten_ids(EMOJI_TO_PREMIUM) or [MAIN_EMOJI_ID]

def premium_ids_for(char: str) -> list:
    return EMOJI_TO_PREMIUM.get(char) or PREMIUM_EMOJIS

def premium_id_for(char: str) -> str:
    """
    Returns a valid numeric custom emoji ID.
    If mapped in EMOJI_TO_PREMIUM, returns a random matching ID.
    Otherwise, falls back to a random ID from the entire PREMIUM_EMOJIS pool.
    """
    ids = EMOJI_TO_PREMIUM.get(char)
    if ids:
        valid_ids = [i for i in ids if i.isdigit()]
        if valid_ids:
            return random.choice(valid_ids)
            
    if char == PLACEHOLDER:
        return MAIN_EMOJI_ID
        
    # FALLBACK: If the emoji is not mapped in the local database,
    # convert it into a random premium emoji from the global pool so it doesn't remain static.
    valid_pool = [i for i in PREMIUM_EMOJIS if str(i).isdigit()]
    if valid_pool:
        return random.choice(valid_pool)
        
    return MAIN_EMOJI_ID

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  EMOJI PACK PARSER (Universal Multi-Format Support)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_EXU_LINE_RE = _re.compile(r'^\s*\d+\.\s+(\d+)\s+\[(.+)\]\s*$')

def parse_emoji_pack(raw_bytes: bytes, filename: str) -> dict:
    text = raw_bytes.decode("utf-8", errors="ignore")
    result: dict = {}

    def _add(emj: str, cid):
        if not emj or not cid:
            return
        emj = str(emj).strip()
        cid = str(cid).strip()
        # Security validation: ID must be entirely numeric, character must be a valid emoji
        if not cid.isdigit() or not emoji.is_emoji(emj):
            return
        result.setdefault(emj, [])
        if cid not in result[emj]:
            result[emj].append(cid)

    if filename.lower().endswith(".json"):
        try:
            data = json.loads(text)
        except Exception:
            return {}

        if isinstance(data, dict):
            # Format 1: Structured "combined_packs" format
            if "combined_packs" in data:
                for pack in data["combined_packs"]:
                    if isinstance(pack, dict) and "emojis" in pack:
                        for item in pack["emojis"]:
                            if isinstance(item, dict):
                                emj = item.get("emoji")
                                cid = item.get("id") or item.get("custom_emoji_id")
                                _add(emj, cid)
            # Format 2: Flat dictionary format
            else:
                for emj, val in data.items():
                    if isinstance(val, list):
                        for cid in val:
                            _add(emj, cid)
                    else:
                        _add(emj, val)
        elif isinstance(data, list):
            # Format 3: Flat list format
            for entry in data:
                if isinstance(entry, dict):
                    emj = entry.get("emoji")
                    cid = entry.get("id") or entry.get("custom_emoji_id")
                    _add(emj, cid)
    else:
        # Format 4: .txt format
        for line in text.splitlines():
            m = _EXU_LINE_RE.match(line.strip())
            if m:
                _add(m.group(2), m.group(1))

    return result

def merge_emoji_pack(new_data: dict) -> tuple:
    global EMOJI_TO_PREMIUM, PREMIUM_EMOJIS
    added_ids = 0
    added_keys = 0
    for emj, ids in new_data.items():
        existing = EMOJI_TO_PREMIUM.setdefault(emj, [])
        if not existing:
            added_keys += 1
        for cid in ids:
            if cid.isdigit() and cid not in existing:
                existing.append(cid)
                added_ids += 1
    save_premium_emoji_db(EMOJI_TO_PREMIUM)
    PREMIUM_EMOJIS = _flatten_ids(EMOJI_TO_PREMIUM) or [MAIN_EMOJI_ID]
    return added_ids, added_keys

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BUTTON STYLING AND BUILD SYSTEM
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
class StyledInlineButton(types.InlineKeyboardButton):
    """
    Subclass of InlineKeyboardButton configured to handle Telegram Bot API 9.4 
    properties safely across any pyTelegramBotAPI library versions.
    """
    def __init__(self, text, url=None, callback_data=None, style=None, icon_custom_emoji_id=None, **kwargs):
        super().__init__(text=text, url=url, callback_data=callback_data)
        self.style = style
        self.icon_custom_emoji_id = icon_custom_emoji_id

    def to_dict(self):
        d = super().to_dict()
        if self.style:
            d['style'] = self.style
        if self.icon_custom_emoji_id:
            d['icon_custom_emoji_id'] = self.icon_custom_emoji_id
        return d

def make_inline_keyboard_button(text: str, url: str = None, callback_data: str = None, style: str = None, icon_custom_emoji_id: str = None):
    return StyledInlineButton(text=text, url=url, callback_data=callback_data, style=style, icon_custom_emoji_id=icon_custom_emoji_id)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FORCE JOIN SYSTEM (4 channels)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
REQUIRED_CHANNELS = [
    {"id": "@ModderSanto_Official", "name": "Channel 1", "link": "https://t.me/ModderSanto_Official"},
    {"id": "@CHS_TEAM_OFFICIAL", "name": "Channel 2", "link": "https://t.me/CHS_TEAM_OFFICIAL"},
    {"id": "@Premium1App", "name": "Channel 3", "link": "https://t.me/Premium1App"},
    {"id": "@EditingAppBySanto", "name": "Channel 4", "link": "https://t.me/EditingAppBySanto"},
]

def build_join_inline(user_id: int, channels_to_show: list) -> types.InlineKeyboardMarkup:
    """Generates the requested 2x2 grid layout dynamically with premium button icons. Excludes text prefix to avoid duplication."""
    markup = types.InlineKeyboardMarkup()
    
    rows = []
    current_row = []
    for ch in channels_to_show:
        eid = premium_id_for("📢")
        btn = make_inline_keyboard_button(
            text=f"{ch['name']}",
            style="primary",
            url=ch["link"],
            icon_custom_emoji_id=eid if (eid and eid.isdigit()) else None
        )
        current_row.append(btn)
        if len(current_row) == 2:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
        
    for r in rows:
        markup.row(*r)
        
    # Verify Button at bottom (no manual emoji prefix to avoid duplicates)
    verify_eid = premium_id_for("✅")
    markup.row(
        make_inline_keyboard_button(
            text="Verify", 
            style="danger", 
            callback_data=f"verify_{user_id}",
            icon_custom_emoji_id=verify_eid if (verify_eid and verify_eid.isdigit()) else None
        )
    )
    return markup

def check_joined(uid: int, force_refresh: bool = False) -> list:
    """Return unjoined required channels. Cached briefly for responsive UI; verify uses force_refresh."""
    if uid == ADMIN_ID:
        return []
    now = time.monotonic()
    cached = _join_cache.get(uid)
    if not force_refresh and cached and now - cached[0] < JOIN_CACHE_TTL:
        return cached[1]

    not_joined = []
    for ch in REQUIRED_CHANNELS:
        try:
            member = bot.get_chat_member(ch["id"], uid)
            if member.status in ("left", "kicked", "banned"):
                not_joined.append(ch)
        except Exception as e:
            print(f"⚠️ membership check failed for {ch['id']}: {e}")
            not_joined.append(ch)
    _join_cache[uid] = (now, not_joined)
    return not_joined

def send_join_notice(chat_id: int, uid: int, include_video: bool = False):
    """
    Sends the complete verification UI as ONE Telegram message when include_video=True:
    the video itself contains the caption and the channel/Verify buttons.
    This prevents the old video -> separate message gap.
    """
    markup = build_join_inline(uid, REQUIRED_CHANNELS)

    text = (
        "➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        "        𝐉ᴏɪɴ & 𝐕ᴇʀɪғʏ        \n"
        "➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        "👋 𝐖ᴇʟᴄᴏᴍᴇ!\n\n"
        "🔐 𝐁ᴏᴛ 𝐀ᴄᴄᴇss 𝐋ᴏᴄᴋᴇᴅ\n"
        "এই বট ব্যবহার করার আগে নিচের সবগুলো\n"
        "চ্যানেলে Join করুন।\n\n"
        "📢 𝐑ᴇǫᴜɪʀᴇᴅ 𝐂ʜᴀɴɴᴇʟs\n"
        "① Channel 1     ② Channel 2\n"
        "③ Channel 3     ④ Channel 4\n\n"
        "✅ সবগুলো Join করার পর নিচের\n"
        "𝐕ᴇʀɪғʏ বাটনে চাপুন।\n\n"
        "⚠️ Verify সফল না হওয়া পর্যন্ত Main Menu\n"
        "ও কোনো Bot Feature Open হবে না।\n"
        "➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿"
    )

    entities = _build_pe_entities(text, use_main=False, italic=True)

    if include_video and os.path.exists("em.mp4"):
        try:
            with open("em.mp4", "rb") as vf:
                return bot.send_video(
                    chat_id,
                    vf,
                    caption=text,
                    caption_entities=entities or None,
                    supports_streaming=True,
                    reply_markup=markup
                )
        except Exception as e:
            print(f"⚠️ Could not send combined em.mp4 verification message: {e}")

    return bot.send_message(
        chat_id,
        text,
        entities=entities or None,
        reply_markup=markup
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CORE ENGINE — build premium emoji entities (Clean typography)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
_TITLE_RE = _re.compile(
    r'(?:🔥 𝗖𝗛𝗦 𝗣ʀᴇᴍɪᴜᴍ 𝗥ᴏʙᴏᴛ[\w\s]+\w|HOW TO USE|BOT STATISTICS|BOT OFFLINE|ADMIN PANEL'
    r'|POST CREATOR|INLINE BUTTON|BUTTON NAME|BUTTON LINK|ADD FILE|SEND FILE'
    r'|BROADCAST|REGISTERED USERS|𝐒ᴍᴀʀᴛ 𝐏ʀᴇᴍɪᴜᴍ 𝐏ᴏsᴛ 𝐌ᴀɴᴀɢᴇʀ|BOT TURNED ON|BOT TURNED OFF'
    r'|POST CREATED SUCCESSFULLY|JOIN REQUIRED|POST TO CHANNEL/GROUP)'
)

_KEYWORD_RE = _re.compile(
    r'\b(STEP\s*\d+|MAKE POST|REFRESH|DELETE|DONE|CANCEL|ONLINE|OFFLINE'
    r'|BOT ON|BOT OFF|BROADCAST|USERS LIST|BOT STATS|Developer|Version'
    r'|Language|Library|Total Users|Emoji Pool|Bot Status|Verify|Channel\s*\d+)\b',
    _re.IGNORECASE
)

def _utf16_len_str(s: str) -> int:
    return len(s.encode("utf-16-le")) // 2

def _collect_bold_ranges(text: str):
    seen   = set()
    result = []
    for pat in (_TITLE_RE, _KEYWORD_RE):
        for m in pat.finditer(text):
            start  = _utf16_len_str(text[:m.start()])
            length = _utf16_len_str(m.group())
            key    = (start, length)
            if key not in seen and length > 0:
                seen.add(key)
                result.append(key)
    return result

def _build_pe_entities(text: str, use_main: bool = True, italic: bool = True):
    """
    Renders messages using elegant, clean formatting.
    Transforms structural icons (➿, 📢, ⭐, and placeholder) into premium custom emojis automatically.
    """
    entities     = []
    utf16_offset = 0
    total_utf16  = _utf16_len_str(text)

    if italic and total_utf16 > 0:
        entities.append(MessageEntity(type="italic", offset=0, length=total_utf16))
        for (start, length) in _collect_bold_ranges(text):
            entities.append(MessageEntity(type="bold", offset=start, length=length))

    utf16_offsets = [0] * (len(text) + 1)
    current_utf16 = 0
    for i, codepoint in enumerate(text):
        utf16_offsets[i] = current_utf16
        current_utf16 += _utf16_len(codepoint)
    utf16_offsets[len(text)] = current_utf16

    emoji_matches = emoji.emoji_list(text)
    for emj_info in emoji_matches:
        start_idx = emj_info.get('start', emj_info.get('match_start'))
        end_idx   = emj_info.get('end', emj_info.get('match_end'))
        if start_idx is None or end_idx is None:
            continue
            
        emj_char = text[start_idx:end_idx]
        offset_utf16 = utf16_offsets[start_idx]
        length_utf16 = utf16_offsets[end_idx] - offset_utf16
        
        eid = None
        if emj_char == PLACEHOLDER:
            eid = MAIN_EMOJI_ID if use_main else premium_id_for(PLACEHOLDER)
        else:
            eid = premium_id_for(emj_char)
            
        if eid and eid.isdigit():
            entities.append(MessageEntity(
                type="custom_emoji",
                offset=offset_utf16,
                length=length_utf16,
                custom_emoji_id=eid
            ))

    return entities

def _send_pe(chat_id, text: str, use_main: bool = True, reply_markup=None):
    entities = _build_pe_entities(text, use_main)
    bot.send_message(
        chat_id,
        text,
        entities=entities if entities else None,
        reply_markup=reply_markup,
        parse_mode=None
    )

def _send_pe_return(chat_id, text: str, use_main: bool = True, reply_markup=None):
    entities = _build_pe_entities(text, use_main)
    return bot.send_message(
        chat_id,
        text,
        entities=entities if entities else None,
        reply_markup=reply_markup,
        parse_mode=None
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  POST CONVERSION (Using Safe emoji_list parsing to prevent splitting)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def process_text_and_entities(text: str, original_entities: list):
    chosen       = {}   
    new_entities = list(original_entities or [])
    
    # Map each Python codepoint string index to its precise UTF-16 offset boundary
    utf16_offsets = [0] * (len(text) + 1)
    current_utf16 = 0
    for i, codepoint in enumerate(text):
        utf16_offsets[i] = current_utf16
        current_utf16 += _utf16_len(codepoint)
    utf16_offsets[len(text)] = current_utf16

    # Extract emojis using safe official library matcher to prevent ZWJ/Variation splitting
    emoji_matches = emoji.emoji_list(text)
    
    for emj_info in emoji_matches:
        start_idx = emj_info.get('start', emj_info.get('match_start'))
        end_idx   = emj_info.get('end', emj_info.get('match_end'))
        
        if start_idx is None or end_idx is None:
            continue
            
        emj_char = text[start_idx:end_idx]
        offset_utf16 = utf16_offsets[start_idx]
        length_utf16 = utf16_offsets[end_idx] - offset_utf16
        
        if emj_char not in chosen:
            chosen[emj_char] = premium_id_for(emj_char)
            
        eid = chosen[emj_char]
        # ONLY apply custom_emoji if we have a valid, matching numeric custom emoji ID [1]
        if eid and eid.isdigit():
            new_entities.append(MessageEntity(
                type="custom_emoji",
                offset=offset_utf16,
                length=length_utf16,
                custom_emoji_id=eid
            ))

    return text, new_entities

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  REGISTER USER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def register_user(uid: int):
    if uid not in all_users:
        all_users.add(uid)
        save_users(all_users)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BOT ON / OFF GUARD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(func=lambda m: not bot_active and m.from_user.id != ADMIN_ID)
def bot_offline_notice(message):
    if message.chat.type != "private":
        return
    _send_pe(
        message.chat.id,
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"          BOT OFFLINE         \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" The bot is currently offline\n"
        f" for maintenance. Please try again\n"
        f" later.\n\n"
        f" Contact: @ModderSanto\n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿"
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  KEYBOARDS — PREMIUM USER MENU
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BTN_NEW_POST       = "𝐌ᴀᴋᴇ 𝐏ᴏꜱᴛ"
BTN_HELP           = "𝐇ᴇʟᴘ"
BTN_ABOUT          = "𝐀ʙᴏᴜᴛ BOT"
BTN_STATS          = "𝐒ᴛᴀᴛs"
BTN_LEADERBOARD    = "𝐋ᴇᴀᴅᴇʀʙᴏᴀʀᴅ"
BTN_HOW_TO_USE     = "𝐇ᴏᴡ 𝐓ᴏ 𝐔ꜱᴇ"
BTN_BOT_STATS      = "BOT STATS"
BTN_BROADCAST      = "BROADCAST"
BTN_BOT_OFF        = "BOT OFF"
BTN_BOT_ON         = "BOT ON"
BTN_USERS_LIST     = "USERS LIST"
BTN_ADD_EMOJI_PACK = "ADD EMOJI PACK"

def _kb_btn(text: str, icon_emoji: str, style: str):
    eid = premium_id_for(icon_emoji)
    btn = {"text": text, "style": style}
    if eid and eid.isdigit(): btn["icon_custom_emoji_id"] = eid
    return btn

def _build_reply_keyboard(buttons, row_width: int = 2):
    colors = ("success", "primary")
    rows, row = [], []
    for text, icon_emoji, style_override in buttons:
        row.append(_kb_btn(text, icon_emoji, style_override or colors[len(row) % 2]))
        if len(row) == row_width: rows.append(row); row=[]
    if row: rows.append(row)
    return json.dumps({"keyboard": rows, "resize_keyboard": True, "is_persistent": True})

def main_menu():
    return _build_reply_keyboard([
        (BTN_NEW_POST, "✏️", None),
        (BTN_LEADERBOARD, "🏆", None),
        (BTN_HOW_TO_USE, "📖", None),
        (BTN_STATS, "📊", None),
        (BTN_HELP, "❓", None),
        (BTN_ABOUT, "ℹ️", "danger"),
    ])

def admin_menu():
    return _build_reply_keyboard([
        (BTN_NEW_POST,None,"success"),(BTN_BROADCAST,"📢","primary"),
        (BTN_BOT_OFF,"🔴","danger"),(BTN_BOT_ON,"🟢","success"),
        (BTN_USERS_LIST,"👥","primary"),(BTN_BOT_STATS,"📊","success"),
        (BTN_ADD_EMOJI_PACK,"➕","primary"),(BTN_HELP,"❓","success"),
        (BTN_STATS,"📊","primary"),(BTN_LEADERBOARD,"🏆","success"),
        (BTN_HOW_TO_USE,"📖","primary"),(BTN_ABOUT,"🌟","danger")])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  BUTTON MATCHING HELPER (Bulletproof caching support)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def match_button(text: str, target: str) -> bool:
    """Safely compares and verifies button texts regardless of casing, mathematical fonts, or emoji prepends."""
    if not text:
        return False
    cleaned_text = emoji.replace_emoji(text, replace="").strip().upper()
    cleaned_target = emoji.replace_emoji(target, replace="").strip().upper()
    return cleaned_text == cleaned_target or text.strip() == target.strip()

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  /start & handlers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
P = PLACEHOLDER  

@bot.message_handler(commands=["start"])
def welcome(message):
    if message.chat.type != "private":
        return

    uid = message.from_user.id

    # ONE Telegram message: em.mp4 + caption + channel buttons + Verify.
    # No separate video/message gap and NEVER open the Main Menu before verification.
    send_join_notice(message.chat.id, uid, include_video=True)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ACCESS GUARD
#  Main menu/features stay locked until Verify succeeds.
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(
    func=lambda m: (
        m.chat.type == "private"
        and not (m.text and m.text.startswith("/start"))
        and m.from_user.id != ADMIN_ID
        and bool(check_joined(m.from_user.id))
    )
)
def verification_required(message):
    send_join_notice(message.chat.id, message.from_user.id)

@bot.message_handler(func=lambda m: match_button(m.text, BTN_HELP) or (m.text and m.text.lower() in ("help", "/help")))
def help_msg(message):
    if message.chat.type != "private": return
    uid = message.from_user.id
    if not bot_active and uid != ADMIN_ID: return
    text=(
        "➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        "                 𝐇ᴇʟᴘ                 \n"
        "➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        "✦ 𝐏ᴏsᴛ 𝐂ʀᴇᴀᴛᴏʀ\n\n"
        "➤ 𝐌ᴀᴋᴇ 𝐏ᴏꜱᴛ চাপুন এবং Text / Photo / Video / GIF / Document পাঠান।\n"
        "➤ 𝐀ᴅᴅ 𝐁ᴜᴛᴛᴏɴ দিয়ে Name + Link যোগ করুন।\n"
        "➤ Button গুলো ২টি করে এক লাইনে সাজবে।\n"
        "➤ 𝐑ᴇғʀᴇsʜ দিয়ে Premium Emoji বদলাতে পারবেন।\n"
        "➤ 𝐃ᴏɴᴇ চাপলে পোস্ট সম্পন্ন হবে।\n\n"
        "🪙 প্রতি সফল পোস্টে 𝟏𝟎 Coins পাবেন।\n"
        "🏆 Leaderboard শুধু Posts/Coins অনুযায়ী হবে, Referral নয়।\n\n"
        "📞 নিচের Support বাটনে যেকোনো সমস্যায় যোগাযোগ করুন।\n"
        "➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿")
    im=types.InlineKeyboardMarkup(row_width=2)
    im.row(make_inline_keyboard_button("𝐇ᴏsᴛ 𝐁ᴏᴛ",url="https://t.me/CHS_HostFileRobot?start=ref_8387845785",style="success",icon_custom_emoji_id=premium_id_for("🔗")),make_inline_keyboard_button("𝐅𝐈𝐋𝐄 𝐁ᴏᴛ",url="https://t.me/FileEarnRoBot?start=8387845785",style="primary",icon_custom_emoji_id=premium_id_for("🔗")))
    im.row(make_inline_keyboard_button("𝐔ᴘᴅᴀᴛᴇs",url="https://t.me/ModderSanto_Official",style="success",icon_custom_emoji_id=premium_id_for("📢")),make_inline_keyboard_button("𝐒ᴜᴘᴘᴏʀᴛ",url="https://t.me/CHS_SAPPORT_TEAM",style="primary",icon_custom_emoji_id=premium_id_for("📞")))
    im.row(make_inline_keyboard_button("𝐌ᴇɴᴜ",callback_data=f"menu_{uid}",style="primary",icon_custom_emoji_id=premium_id_for("🏠")))
    _send_pe(message.chat.id,text,use_main=False,reply_markup=im)

@bot.message_handler(func=lambda m: match_button(m.text, BTN_LEADERBOARD) or (m.text and m.text.lower() in ("leaderboard", "/leaderboard")))
def leaderboard_msg(message):
    if message.chat.type != "private": return
    uid=message.from_user.id
    register_user(uid); ranking=[]
    for x in all_users:
        st=get_user_stats(int(x)); ranking.append((int(x),int(st["coins"]),int(st["posts"])))
    ranking.sort(key=lambda a:(a[1],a[2],-a[0]),reverse=True)
    rank={x[0]:i+1 for i,x in enumerate(ranking)}
    lines=["🏆 Top 10 Leaderboard","╭━━━━━━━━━━━━━━━━━━━━━━╮"]
    medals=["🥇","🥈","🥉"]
    for i,(x,c,pst) in enumerate(ranking[:10],1): lines.append(f"{medals[i-1] if i<=3 else str(i)+'.'} {x} — 🪙 {c} coins | ✦ {pst} posts")
    lines += ["╰━━━━━━━━━━━━━━━━━━━━━━╯",f"👤 Your Rank: #{rank.get(uid,len(ranking)+1)} | 🪙 {get_user_stats(uid)['coins']} coins | ✦ {get_user_stats(uid)['posts']} posts","","ℹ️ 𝐍ᴏ 𝐑ᴇғᴇʀʀᴀʟ 𝐑ᴀɴᴋɪɴɢ — শুধু পোস্ট তৈরি করলেই Coins পাবেন।"]
    _send_pe(message.chat.id,"\n".join(lines),use_main=False,reply_markup=main_menu())

@bot.message_handler(func=lambda m: match_button(m.text, BTN_HOW_TO_USE) or (m.text and m.text.lower() in ("how to use", "/howtouse")))
def how_to_use_msg(message):
    if message.chat.type != "private": return
    uid=message.from_user.id
    text=("╭━⟮ ✦ 📖 𝐁ᴏᴛ 𝐑ᴜʟᴇs ✦ ⟯\n│\n"
          "│ ① ✏️ 𝐌ᴀᴋᴇ 𝐏ᴏꜱᴛ\n│    নতুন পোস্ট তৈরি করতে 𝐌ᴀᴋᴇ 𝐏ᴏꜱᴛ চাপুন।\n│\n"
          "│ ② 📝 𝐂ᴏɴᴛᴇɴᴛ পাঠান\n│    Text, Photo, Video, GIF বা Document পাঠান।\n│\n"
          "│ ③ 🔗 𝐁ᴜᴛᴛᴏɴ যোগ করুন\n│    Button Name এবং Link দিন।\n│\n"
          "│ ④ 👀 𝐏ʀᴇᴠɪᴇᴡ দেখুন\n│    Refresh / Delete / Done ব্যবহার করুন।\n│\n"
          "│ ⑤ 🪙 𝐂ᴏɪɴs সংগ্রহ করুন\n│    প্রতিটি সফল পোস্টে ১০ Coins পাবেন।\n│\n"
          "│ ⑥ 🏆 𝐋ᴇᴀᴅᴇʀʙᴏᴀʀᴅ\n│    Posts ও Coins অনুযায়ী Rank হবে।\n│\n"
          "│ ⑦ 🛡️ 𝐑ᴜʟᴇs মেনে চলুন\n│    Spam বা বটের অপব্যবহার করবেন না।\n│\n"
          "│ ⑧ 📞 𝐇ᴇʟᴘ দরকার?\n│    𝐇ᴇʟᴘ বাটন থেকে Support-এ যোগাযোগ করুন।\n"
          "╰➿➿➿➿➿➿➿➮ ✦ 📖 𝐁ᴏᴛ 𝐑ᴜʟᴇs ✦ ⟯")
    _send_pe(message.chat.id,text,use_main=False,reply_markup=main_menu())

@bot.message_handler(func=lambda m: match_button(m.text, BTN_ABOUT) or (m.text and m.text.lower() in ("about", "about bot", "/about")))
def about_bot(message):
    if message.chat.type != "private":
        return
    uid = message.from_user.id
    if not bot_active and uid != ADMIN_ID:
        return
    kb    = admin_menu() if uid == ADMIN_ID else main_menu()
    total = len(all_users)
    text = (
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"     🔥 𝗖𝗛𝗦 𝗣ʀᴇᴍɪᴜᴍ 𝗥ᴏʙᴏᴛ 🔥   \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" About This Bot:\n\n"
        " 𝗖𝗛𝗦 𝗣ʀᴇᴍɪᴜᴍ 𝗥ᴏʙᴏᴛ is the most\n"
        " advanced Telegram emoji conversion\n"
        " tool. It injects Telegram Premium\n"
        " Animated Emojis directly into your\n"
        " posts — no Premium account needed!\n\n"
        f"➿➿ Core Technology ➿➿\n\n"
        f" CUSTOM EMOJI Entity Injection\n"
        f" UTF-16 Offset Mapping Engine\n"
        f" Real-time Formatting Preserve\n"
        f" Random Premium Emoji Pool 200+\n"
        f" Advanced Callback Action System\n\n"
        f"➿➿ Bot Information ➿➿\n\n"
        f" Total Users     : {total}\n"
        f" Emoji Pool Size : {len(PREMIUM_EMOJIS)}\n"
        f" Version         : 3.0 ADVANCED\n"
        f" Language        : Python\n"
        f" Library         : pyTelegramBotAPI\n\n"
        f"➿➿ Developer Info ➿➿\n\n"
        f" Developer  : 🔥 Modder Santo \n"
        f" Telegram   : @ModderSanto\n"
        f" Brand      : 🔥 𝗖𝗛𝗦 𝗣ʀᴇᴍɪᴜᴍ 𝗥ᴏʙᴏᴛ 🔥\n\n"
        f"➿➿➿➿➿➿\n"
        f" 100% Free — No restrictions!\n"
    )
    _send_pe(message.chat.id, text, use_main=False, reply_markup=kb)

@bot.message_handler(func=lambda m: match_button(m.text, BTN_STATS) or match_button(m.text, BTN_BOT_STATS) or (m.text and m.text.lower() in ("stats", "bot stats", "/stats")))
def stats_msg(message):
    if message.chat.type != "private": return
    uid=message.from_user.id
    if not bot_active and uid != ADMIN_ID: return
    register_user(uid); st=get_user_stats(uid); u=message.from_user
    username=f"@{u.username}" if u.username else "—"
    text=(f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n              𝐒ᴛᴀᴛs              \n"
          f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
          f"👤 𝐍ᴀᴍᴇ : {u.first_name or 'Unknown'}\n🔗 𝐔sᴇʀɴᴀᴍᴇ : {username}\n🆔 𝐔sᴇʀ 𝐈ᴅ : {uid}\n\n"
          f"🪙 𝐌ʏ 𝐂ᴏɪɴs : {st['coins']}\n✦ 𝐌ʏ 𝐌ᴀᴋᴇ 𝐏ᴏꜱᴛ : {st['posts']}\n\n"
          f"👥 𝐓ᴏᴛᴀʟ 𝐔sᴇʀs : {len(all_users)}\n📝 𝐓ᴏᴛᴀʟ 𝐔sᴇʀ POST : {total_stat('posts')}\n"
          f"📢 𝐓ᴏᴛᴀʟ 𝐂ʜᴀɴɴᴇʟ 𝐅ᴏʀᴄᴇ POST : {total_stat('channel_force_posts')}\n"
          f"👥 𝐓ᴏᴛᴀʟ 𝐆ʀᴏᴜᴘ 𝐅ᴏʀᴄᴇ POST : {total_stat('group_force_posts')}\n\n"
          f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\nDeveloper  @ModderSanto")
    _send_pe(message.chat.id,text,use_main=False,reply_markup=main_menu())

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  ADMIN PANEL
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(commands=["admin"])
def admin_panel(message):
    if message.chat.type != "private":
        return
    if message.from_user.id != ADMIN_ID:
        _send_pe(message.chat.id, f"{P} This command is for Admin only!")
        return
    status = "ONLINE 🟢" if bot_active else "OFFLINE 🔴"
    total  = len(all_users)
    text   = (
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"   🔥 𝗖𝗛𝗦 𝗣ʀᴇᴍɪᴜᴍ 𝗥ᴏʙᴏᴛ   \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" Bot Status   : {status}\n"
        f" Total Users  : {total}\n\n"
        f"➿➿➿ Admin Commands ➿➿➿\n\n"
        f" 🟢 BOT ON     — Start the bot\n"
        f" 🔴 BOT OFF    — Stop the bot\n"
        f" 📢 BROADCAST  — Message all users\n"
        f" 👥 USERS LIST — View all user IDs\n"
        f" 📊 BOT STATS  — Statistics\n\n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿"
    )
    _send_pe(message.chat.id, text, use_main=False, reply_markup=admin_menu())

@bot.message_handler(func=lambda m: match_button(m.text, BTN_BOT_OFF) and m.from_user.id == ADMIN_ID)
def bot_off(message):
    if message.chat.type != "private":
        return
    global bot_active
    bot_active = False
    _send_pe(
        message.chat.id,
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"      BOT TURNED OFF 🔴       \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" Bot is now OFFLINE.\n"
        f" All users will see a maintenance\n"
        f" message. Tap 🟢 BOT ON to restart.\n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿",
        use_main=False, reply_markup=admin_menu()
    )

@bot.message_handler(func=lambda m: match_button(m.text, BTN_BOT_ON) and m.from_user.id == ADMIN_ID)
def bot_on(message):
    if message.chat.type != "private":
        return
    global bot_active
    bot_active = True
    _send_pe(
        message.chat.id,
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"       BOT TURNED ON 🟢       \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" Bot is now ONLINE.\n"
        f" All users can use the bot again!\n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿",
        use_main=False, reply_markup=admin_menu()
    )

@bot.message_handler(func=lambda m: match_button(m.text, BTN_USERS_LIST) and m.from_user.id == ADMIN_ID)
def users_list(message):
    if message.chat.type != "private":
        return
    total     = len(all_users)
    user_list = list(all_users)
    _send_pe(
        message.chat.id,
        f"{P}➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿{P}\n"
        f"       REGISTERED USERS       \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" Total Users: {total}\n",
        use_main=False, reply_markup=admin_menu()
    )
    if user_list:
        for i in range(0, len(user_list), 50):
            batch = user_list[i:i + 50]
            bot.send_message(message.chat.id, "\n".join([f"• {uid}" for uid in batch]))

@bot.message_handler(func=lambda m: match_button(m.text, BTN_BROADCAST) and m.from_user.id == ADMIN_ID)
def broadcast_start(message):
    if message.chat.type != "private":
        return
    sent = _send_pe_return(
        message.chat.id,
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"           BROADCAST          \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" Send your broadcast message now.\n"
        f" It will be delivered to ALL users!\n\n"
        f" Supports: Text, Photo, Video,\n"
        f" Document, Sticker, Animation\n\n"
        f" To cancel: /cancel\n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿",
        use_main=False
    )
    bot.register_next_step_handler(sent, do_broadcast)

def do_broadcast(message):
    if message.chat.type != "private":
        return
    if message.text and message.text.strip() == "/cancel":
        _send_pe(message.chat.id, f"{P} Broadcast cancelled.", reply_markup=admin_menu())
        return

    success = 0
    failed  = 0
    total   = len(all_users)
    status_msg = bot.send_message(message.chat.id, f"📢 BROADCAST TOTAL {total} users...")

    for uid in list(all_users):
        try:
            bot.copy_message(uid, message.chat.id, message.message_id)
            success += 1
            time.sleep(0.05)
        except Exception:
            failed += 1

    try:
        bot.delete_message(message.chat.id, status_msg.message_id)
    except Exception:
        pass

    _send_pe(
        message.chat.id,
  	   f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"      BROADCAST COMPLETE      \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" Total    : {total} users\n"
        f" Success  : {success} ✅\n"
        f" Failed   : {failed} ❌\n\n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿",
        use_main=False, reply_markup=admin_menu()
    )

@bot.message_handler(commands=["broadcast"])
def broadcast_cmd(message):
    if message.chat.type != "private":
        return
    if message.from_user.id != ADMIN_ID:
        return
    if not message.reply_to_message:
        _send_pe(message.chat.id, f"{P} Reply to any message with /broadcast")
        return
    success = 0
    failed = 0
    total = len(all_users)
    for uid in list(all_users):
        try:
            bot.copy_message(uid, message.chat.id, message.reply_to_message.message_id)
            success += 1
            time.sleep(0.05)
        except Exception:
            failed += 1
    _send_pe(
        message.chat.id,
        f"{P} Broadcast done!\n{P} Success: {success}/{total}\n{P} Failed: {failed}",
        use_main=False
    )

@bot.message_handler(commands=["cancel"])
def cancel_step_command(message):
    if message.chat.type != "private":
        return
    uid = message.from_user.id
    temp_data.pop(uid, None)
    kb = admin_menu() if uid == ADMIN_ID else main_menu()
    _send_pe(message.chat.id, f"{P} Cancelled successfully!", reply_markup=kb)

@bot.message_handler(func=lambda m: match_button(m.text, BTN_ADD_EMOJI_PACK) and m.from_user.id == ADMIN_ID)
def add_emoji_pack_start(message):
    if message.chat.type != "private":
        return
    sent = _send_pe_return(
        message.chat.id,
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"       ADD EMOJI PACK         \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" Send me a .txt or .json file.\n\n"
        f" Supported .txt format:\n"
        f"   1. <id>  [<emoji>]\n\n"
        f" Supported .json format:\n"
        f"   {{\"😀\": [\"id1\",\"id2\"]}}\n\n"
        f" New IDs will be merged into the\n"
        f" existing emoji database.\n\n"
        f" /cancel to stop.",
        use_main=False
    )
    bot.register_next_step_handler(sent, receive_emoji_pack_file)

def receive_emoji_pack_file(message):
    if message.chat.type != "private":
        return
    chat_id = message.chat.id
    if message.text and message.text.strip() == "/cancel":
        _send_pe(chat_id, f"{P} Cancelled successfully!", reply_markup=admin_menu())
        return

    if not message.document:
        sent = _send_pe_return(
            chat_id,
            f"{P} Please send a .txt or .json file as a document.\n{P} Or /cancel to stop."
        )
        bot.register_next_step_handler(sent, receive_emoji_pack_file)
        return

    filename = message.document.file_name or ""
    if not (filename.lower().endswith(".txt") or filename.lower().endswith(".json")):
        sent = _send_pe_return(
            chat_id,
            f"{P} ❌ Only .txt or .json files are supported.\n{P} Send again or /cancel."
        )
        bot.register_next_step_handler(sent, receive_emoji_pack_file)
        return

    try:
        file_info = bot.get_file(message.document.file_id)
        raw = bot.download_file(file_info.file_path)
        parsed = parse_emoji_pack(raw, filename)
    except Exception as e:
        _send_pe(chat_id, f"{P} ❌ Couldn't read that file: {e}", reply_markup=admin_menu())
        return

    if not parsed:
        _send_pe(
            chat_id,
            f"{P} ⚠️ No valid entries found in that file.\n"
            f"{P} Check the format and try again.",
            reply_markup=admin_menu()
        )
        return

    added_ids, added_keys = merge_emoji_pack(parsed)
    _send_pe(
        chat_id,
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"    ✅ EMOJI PACK ADDED!    \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" File         : {filename}\n"
        f" New IDs      : {added_ids}\n"
        f" New Emojis   : {added_keys}\n"
        f" Total IDs now : {len(PREMIUM_EMOJIS)}\n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿",
        use_main=False, reply_markup=admin_menu()
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAKE POST — STEP 1
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(func=lambda m: match_button(m.text, BTN_NEW_POST) or (m.text and m.text.lower() in ("new post", "make post", "/newpost", "/makepost")))
def start_post(message):
    if message.chat.type != "private":
        return
    uid = message.from_user.id
    register_user(uid)
    if not bot_active and uid != ADMIN_ID:
        bot_offline_notice(message)
        return

    text = (
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"                 𝐌ᴀᴋᴇ 𝐏ᴏꜱᴛ                 \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f"✦ 𝐏ᴏsᴛ 𝐂ʀᴇᴀᴛᴏʀ — এখানে আপনার সম্পূর্ণ Post তৈরি হবে।\n\n"
        f"① 📝 𝐓ᴇxᴛ 𝐏ᴏsᴛ\n"
        f"   শুধু লেখা পাঠালে সেটি Premium Emoji formatting সহ Post হিসেবে তৈরি হবে।\n\n"
        f"② 🖼️ 𝐏ʜᴏᴛᴏ 𝐏ᴏsᴛ\n"
        f"   Photo পাঠান। Caption থাকলে সেটিও Post-এর অংশ হবে।\n\n"
        f"③ 🎬 𝐕ɪᴅᴇᴏ 𝐏ᴏsᴛ\n"
        f"   Video পাঠান এবং চাইলে Caption যোগ করুন।\n\n"
        f"④ 🎞️ 𝐆ɪғ / 𝐀ɴɪᴍᴀᴛɪᴏɴ\n"
        f"   GIF বা Animation পাঠিয়ে সুন্দর Animated Post তৈরি করুন।\n\n"
        f"⑤ 📁 𝐃ᴏᴄᴜᴍᴇɴᴛ\n"
        f"   Document/File পাঠিয়ে সেটাকেও Post-এর সাথে ব্যবহার করতে পারবেন।\n\n"
        f"⑥ 🔗 𝐈ɴʟɪɴᴇ 𝐁ᴜᴛᴛᴏɴ\n"
        f"   Button Name দিন → তারপর Button Link দিন।\n"
        f"   একাধিক Button যোগ করা যাবে এবং সব Button ২টি করে এক লাইনে থাকবে।\n\n"
        f"⑦ 🔄 𝐑ᴇғʀᴇsʜ\n"
        f"   Post-এর Premium Emoji আবার randomize করে নতুন look দেখতে পারবেন।\n\n"
        f"⑧ 🗑️ 𝐃ᴇʟᴇᴛᴇ\n"
        f"   বর্তমান Draft/Preview বাতিল করে Post মুছে দেবে।\n\n"
        f"⑨ ✅ 𝐃ᴏɴᴇ\n"
        f"   সব ঠিক থাকলে Done চাপুন। Post creation complete হবে এবং +10 Coins পাবেন।\n\n"
        f"💡 𝐓ɪᴘs\n"
        f"• /cancel লিখলে বর্তমান creation বন্ধ হবে।\n"
        f"• Button-এর Link অবশ্যই সম্পূর্ণ Telegram/Website URL দিন।\n"
        f"• Preview দেখে তারপর Done করুন।\n"
        f"• Premium Emoji আপনার Post-এর text/emoji অনুযায়ী automatically apply হবে।\n\n"
        f"👇 এখন আপনার Text / Photo / Video / GIF / Document পাঠান।"
    )
    sent = _send_pe_return(message.chat.id, text, use_main=False)
    bot.register_next_step_handler(sent, process_post_content)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  MAKE POST — STEP 2: receive content
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def process_post_content(message):
    if message.chat.type != "private":
        return
    uid = message.from_user.id
    if message.text and message.text.strip() == "/cancel":
        kb = admin_menu() if uid == ADMIN_ID else main_menu()
        _send_pe(message.chat.id, f"{P} Cancelled successfully!", reply_markup=kb)
        return

    # UPDATED: Support photo, text, document, video, animation
    if message.content_type not in ("photo", "text", "document", "video", "animation"):
        sent = _send_pe_return(
            message.chat.id,
            f"{P} Only text, photo, video, animation, or document supported.\nPlease try again:"
        )
        bot.register_next_step_handler(sent, process_post_content)
        return

    data = {
        "original_text": "", "original_entities": [],
        "photo_id": None, "document_id": None, "doc_name": None,
        "video_id": None, "animation_id": None,
        "processed_text": "", "processed_entities": [],
        "btn_name": None, "btn_url": None,
        "buttons": [],
        "preview_msg_id": None, "action_msg_id": None,
    }

    if message.content_type == "text":
        data["original_text"]     = message.text or ""
        data["original_entities"] = message.entities or []
    elif message.content_type == "photo":
        data["photo_id"]          = message.photo[-1].file_id
        data["original_text"]     = message.caption or ""
        data["original_entities"] = message.caption_entities or []
    elif message.content_type == "video":
        data["video_id"]          = message.video.file_id
        data["original_text"]     = message.caption or ""
        data["original_entities"] = message.caption_entities or []
    elif message.content_type == "animation":
        data["animation_id"]      = message.animation.file_id
        data["original_text"]     = message.caption or ""
        data["original_entities"] = message.caption_entities or []
    elif message.content_type == "document":
        data["document_id"]       = message.document.file_id
        data["doc_name"]          = message.document.file_name
        data["original_text"]     = message.caption or ""
        data["original_entities"] = message.caption_entities or []

    pt, pe_list = process_text_and_entities(data["original_text"], data["original_entities"])
    data["processed_text"]     = pt
    data["processed_entities"] = pe_list
    temp_data[uid]             = data

    ask_add_button(message.chat.id, uid)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STEP 3a: Ask — Add Button?
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def ask_add_button(chat_id: int, uid: int):
    data = temp_data.get(uid, {})
    count = len(data.get("buttons", []))
    text = (
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"        ✨ POST BUTTONS ✨        \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" 🔘 Buttons added: {count}\n\n"
        f" You can create as many buttons as you want.\n"
        f" Each button needs a NAME and LINK.\n"
        f" Buttons will appear 2 per row, in order.\n\n"
        f"🔗 𝐀ᴅᴅ 𝐁ᴜᴛᴛᴏɴ — নতুন Button তৈরি করতে চাপুন।\n"
        f"   প্রথমে Button Name, তারপর Button Link দিতে হবে।\n\n"
        f"📎 𝐅ɪɴɪsʜ — Button শেষ করে File/Preview ধাপে যাবেন।\n"
        f"❌ 𝐂ᴀɴᴄᴇʟ — বর্তমান Post creation বাতিল করবেন।\n\n"
        f"💡 Button Layout: ২টি Button এক লাইনে।\n"
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    add_eid = premium_id_for("➕")
    done_eid = premium_id_for("✅")
    cancel_eid = premium_id_for("❌")
    markup.row(
        make_inline_keyboard_button("ADD BUTTON", "", callback_data=f"wizard_addbtn_{uid}", style="success", icon_custom_emoji_id=add_eid),
        make_inline_keyboard_button("FINISH", "", callback_data=f"wizard_finishbtn_{uid}", style="primary", icon_custom_emoji_id=done_eid),
    )
    markup.row(
        make_inline_keyboard_button("CANCEL", "", callback_data=f"wizard_cancelbtn_{uid}", style="danger", icon_custom_emoji_id=cancel_eid),
    )
    entities = _build_pe_entities(text, use_main=False)
    bot.send_message(chat_id, text, entities=entities or None, reply_markup=markup)

def ask_button_name(chat_id: int, uid: int):
    data = temp_data.get(uid, {})
    count = len(data.get("buttons", [])) + 1
    text = (
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"        🔘 BUTTON {count} NAME        \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" Send the name/label for button #{count}.\n\n"
        f" Example:  Join Channel\n\n"
        f" You can keep adding buttons after this one.\n"
        f" /cancel to stop."
    )
    sent = _send_pe_return(chat_id, text, use_main=False)
    bot.register_next_step_handler(sent, receive_button_name)


def receive_button_name(message):
    if message.chat.type != "private":
        return
    uid = message.from_user.id
    if message.text and message.text.strip() == "/cancel":
        kb = admin_menu() if uid == ADMIN_ID else main_menu()
        _send_pe(message.chat.id, f"{P} Cancelled successfully!", reply_markup=kb)
        temp_data.pop(uid, None)
        return
    if uid not in temp_data:
        _send_pe(message.chat.id, f"{P} Session expired! Please /start again.")
        return
    name = (message.text or "").strip()
    if not name:
        sent = _send_pe_return(message.chat.id, f"{P} Button name cannot be empty! Send again:")
        bot.register_next_step_handler(sent, receive_button_name)
        return

    first_emoji_id = None
    clean_name = ""
    for ch in name:
        if emoji.is_emoji(ch):
            if first_emoji_id is None:
                pid = premium_id_for(ch)
                if pid and pid.isdigit():
                    first_emoji_id = pid
        else:
            clean_name += ch
    clean_name = clean_name.strip() or name
    temp_data[uid]["pending_btn_name"] = clean_name
    temp_data[uid]["pending_btn_emoji_id"] = first_emoji_id
    ask_button_url(message.chat.id, uid)

def ask_button_url(chat_id: int, uid: int):
    text = (
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"       BUTTON LINK            \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" Now send the button URL.\n\n"
        f" Must start with:\n"
        f" https:// · http:// · tg://\n\n"
        f" Example:  https://t.me/DarkByteOfficial\n\n"
        f" /cancel to stop."
    )
    sent = _send_pe_return(chat_id, text, use_main=False)
    bot.register_next_step_handler(sent, receive_button_url)

def receive_button_url(message):
    if message.chat.type != "private":
        return
    uid = message.from_user.id
    if message.text and message.text.strip() == "/cancel":
        kb = admin_menu() if uid == ADMIN_ID else main_menu()
        _send_pe(message.chat.id, f"{P} Cancelled successfully!", reply_markup=kb)
        temp_data.pop(uid, None)
        return
    if uid not in temp_data:
        _send_pe(message.chat.id, f"{P} Session expired! Please /start again.")
        return
    url = (message.text or "").strip().strip("\u200b\u200c\u200d\ufeff\xa0")
    valid_prefixes = ("http://", "https://", "tg://")
    if not any(url.startswith(p) for p in valid_prefixes):
        sent = _send_pe_return(message.chat.id,
            f"{P} Invalid URL!\n\n"
            f" The link must start with https://, http://, or tg://\n"
            f" Example: https://t.me/channel\n\n"
            f" Please send the link again:")
        bot.register_next_step_handler(sent, receive_button_url)
        return
    temp_data[uid]["pending_btn_url"] = url
    ask_button_color(message.chat.id, uid)

def ask_button_color(chat_id: int, uid: int):
    data = temp_data.get(uid, {})
    count = len(data.get("buttons", [])) + 1
    text = (
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"       🎨 BUTTON {count} STYLE       \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" Choose a colour/style for button #{count}.\n\n"
        f" 🟢 SUCCESS  — Green\n"
        f" 🔵 PRIMARY  — Blue\n"
        f" 🔴 DANGER   — Red\n"
        f" ⚪ NONE     — Plain\n\n"
        f" After selecting, you can add another button."
    )
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.row(
        make_inline_keyboard_button("SUCCESS", "", style="success", callback_data=f"wizard_colorsuccess_{uid}", icon_custom_emoji_id=premium_id_for("🟢")),
        make_inline_keyboard_button("PRIMARY", "", style="primary", callback_data=f"wizard_colorprimary_{uid}", icon_custom_emoji_id=premium_id_for("🔵")),
    )
    markup.row(
        make_inline_keyboard_button("DANGER", "", style="danger", callback_data=f"wizard_colordanger_{uid}", icon_custom_emoji_id=premium_id_for("🔴")),
        make_inline_keyboard_button("NO COLOUR", "", style=None, callback_data=f"wizard_colornone_{uid}", icon_custom_emoji_id=premium_id_for("⚪")),
    )
    entities = _build_pe_entities(text, use_main=False)
    bot.send_message(chat_id, text, entities=entities or None, reply_markup=markup)

def ask_add_file(chat_id: int, uid: int):
    # UPDATED: Included video and animation in prompt
    text = (
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"         ADD FILE             \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" Do you want to attach a file, photo,\n"
        f" video, or animation to your post?\n\n"
        f" Choose an option below:"
    )
    data = temp_data.get(uid, {})
    has_media = bool(data.get("photo_id") or data.get("document_id") or data.get("video_id") or data.get("animation_id"))

    markup = types.InlineKeyboardMarkup(row_width=2)
    if not has_media:
        file_eid = premium_id_for("📁")
        skip_eid = premium_id_for("⏭️")
        
        btn_add = make_inline_keyboard_button(
            text="Add File",
            style="success",
            callback_data=f"wizard_addfile_{uid}",
            icon_custom_emoji_id=file_eid if (file_eid and file_eid.isdigit()) else None
        )
        btn_skip = make_inline_keyboard_button(
            text="Skip",
            style="primary",
            callback_data=f"wizard_skipfile_{uid}",
            icon_custom_emoji_id=skip_eid if (skip_eid and skip_eid.isdigit()) else None
        )
        markup.row(btn_add, btn_skip)
    else:
        send_preview_and_actions(chat_id, uid)
        return

    entities = _build_pe_entities(text, use_main=False)
    bot.send_message(chat_id, text, entities=entities or None, reply_markup=markup)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  STEP 4b: Receive file/photo/video/gif
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def receive_file(message):
    if message.chat.type != "private":
        return
    uid = message.from_user.id
    if message.text and message.text.strip() == "/cancel":
        kb = admin_menu() if uid == ADMIN_ID else main_menu()
        _send_pe(message.chat.id, f"{P} Cancelled successfully!", reply_markup=kb)
        return
    if uid not in temp_data:
        _send_pe(message.chat.id, f"{P} Session expired! Please /start again.")
        return

    # UPDATED: Robust support for photo, video, animation (gif), document
    if message.content_type == "photo":
        temp_data[uid]["photo_id"]     = message.photo[-1].file_id
        temp_data[uid]["document_id"]  = None
        temp_data[uid]["video_id"]     = None
        temp_data[uid]["animation_id"] = None
    elif message.content_type == "video":
        temp_data[uid]["video_id"]     = message.video.file_id
        temp_data[uid]["photo_id"]     = None
        temp_data[uid]["document_id"]  = None
        temp_data[uid]["animation_id"] = None
    elif message.content_type == "animation":
        temp_data[uid]["animation_id"] = message.animation.file_id
        temp_data[uid]["photo_id"]     = None
        temp_data[uid]["document_id"]  = None
        temp_data[uid]["video_id"]     = None
    elif message.content_type == "document":
        temp_data[uid]["document_id"]  = message.document.file_id
        temp_data[uid]["doc_name"]     = message.document.file_name
        temp_data[uid]["photo_id"]     = None
        temp_data[uid]["video_id"]     = None
        temp_data[uid]["animation_id"] = None
    else:
        sent = _send_pe_return(
            message.chat.id,
            f"{P} Please send a photo, video, animation or document file.\nOr /cancel to stop."
        )
        bot.register_next_step_handler(sent, receive_file)
        return

    send_preview_and_actions(message.chat.id, uid)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  PREVIEW + ACTION BUTTONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def build_post_markup(data: dict):
    buttons = data.get("buttons") or []
    # Backward compatibility with old one-button sessions
    if not buttons and data.get("btn_name") and data.get("btn_url"):
        buttons = [{
            "name": data.get("btn_name", ""),
            "url": data.get("btn_url", ""),
            "color": data.get("btn_color"),
            "emoji_id": data.get("btn_emoji_id")
        }]
    if not buttons:
        return None

    rows = []
    row = []
    for b in buttons:
        name = str(b.get("name", "")).strip()
        url = str(b.get("url", "")).strip()
        if not name or not url:
            continue
        btn = {"text": name, "url": url}
        if b.get("color"):
            btn["style"] = b["color"]
        if b.get("emoji_id") and str(b["emoji_id"]).isdigit():
            btn["icon_custom_emoji_id"] = str(b["emoji_id"])
        row.append(btn)
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return json.dumps({"inline_keyboard": rows}) if rows else None

def send_preview_and_actions(chat_id: int, uid: int):
    data = temp_data.get(uid)
    if not data:
        return
    post_markup = build_post_markup(data)

    # Safe validation of caption and its entities to prevent API crashes when caption is empty
    cap_text = data["processed_text"] if data["processed_text"] else None
    cap_ents = data["processed_entities"] if (cap_text and data["processed_entities"]) else None

    # UPDATED: Sending previews for photo, video, animation, document, or pure text safely
    try:
        if data.get("photo_id"):
            prev = bot.send_photo(
                chat_id, data["photo_id"],
                caption=cap_text,
                caption_entities=cap_ents,
                reply_markup=post_markup
            )
        elif data.get("video_id"):
            prev = bot.send_video(
                chat_id, data["video_id"],
                caption=cap_text,
                caption_entities=cap_ents,
                reply_markup=post_markup
            )
        elif data.get("animation_id"):
            prev = bot.send_animation(
                chat_id, data["animation_id"],
                caption=cap_text,
                caption_entities=cap_ents,
                reply_markup=post_markup
            )
        elif data.get("document_id"):
            prev = bot.send_document(
                chat_id, data["document_id"],
                caption=cap_text,
                caption_entities=cap_ents,
                reply_markup=post_markup
            )
        else:
            prev = bot.send_message(
                chat_id,
                data["processed_text"],
                entities=data["processed_entities"] or None,
                reply_markup=post_markup
            )
        data["preview_msg_id"] = prev.message_id
    except Exception as e:
        bot.send_message(chat_id, f"❌ Preview error: {e}")
        return

    action_markup = types.InlineKeyboardMarkup(row_width=2)
    btn_refresh = make_inline_keyboard_button(
        text="REFRESH EMOJIS",
        style="primary",
        callback_data=f"action_refresh_{uid}",
        icon_custom_emoji_id=premium_id_for("🔄")
    )
    btn_delete = make_inline_keyboard_button(
        text="DELETE",
        style="danger",
        callback_data=f"action_delete_{uid}",
        icon_custom_emoji_id=premium_id_for("🗑")
    )
    btn_done = make_inline_keyboard_button(
        text="DONE",
        style="success",
        callback_data=f"action_done_{uid}",
        icon_custom_emoji_id=premium_id_for("✅")
    )
    action_markup.row(btn_refresh, btn_delete)
    action_markup.row(btn_done)

    button_count = len(data.get("buttons", []))
    action_text = (
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"       ✨ POST MANAGER ✨       \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" 🔘 Buttons: {button_count}\n"
        f" ↔️ Layout: 2 buttons per row\n\n"
        f" 👀 Preview: check your post above.\n"
        f" 🔄 Refresh: randomize premium emojis.\n"
        f" 🗑 Delete: remove the draft.\n"
        f" ✅ Done: finish this post.\n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿"
    )
    entities  = _build_pe_entities(action_text, use_main=False)
    action_msg = bot.send_message(
        chat_id, action_text,
        entities=entities if entities else None,
        reply_markup=action_markup
    )
    data["action_msg_id"] = action_msg.message_id
    temp_data[uid]        = data

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  WIZARD CALLBACKS (button / file choice)
#  UPDATED: Wrapped inside try-except with alerts to ensure buttons never hang
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.callback_query_handler(func=lambda c: c.data.startswith("wizard_"))
def handle_wizard(call):
    if call.message.chat.type != "private":
        return
    try:
        parts  = call.data.split("_")   
        if len(parts) < 2:
            bot.answer_callback_query(call.id, "Invalid action.")
            return
            
        action = parts[1]
        uid    = call.from_user.id
        chat_id = call.message.chat.id

        try: bot.delete_message(chat_id, call.message.message_id)
        except: pass

        # Robust string/integer checking for dictionary session safety
        data = temp_data.get(uid) or temp_data.get(str(uid))
        if not data:
            bot.answer_callback_query(call.id, "Session expired! Please /start again.", show_alert=True)
            return

        bot.answer_callback_query(call.id)

        if action == "addbtn":
            ask_button_name(chat_id, uid)
        elif action == "finishbtn":
            ask_add_file(chat_id, uid)
        elif action == "cancelbtn":
            temp_data.pop(uid, None)
            kb = admin_menu() if uid == ADMIN_ID else main_menu()
            _send_pe(chat_id, f"{P} Button setup cancelled.", reply_markup=kb)
        elif action in ("colorsuccess", "colorprimary", "colordanger", "colornone"):
            colors = {"colorsuccess": "success", "colorprimary": "primary", "colordanger": "danger", "colornone": None}
            data.setdefault("buttons", [])
            data["buttons"].append({
                "name": data.pop("pending_btn_name", "Button"),
                "url": data.pop("pending_btn_url", ""),
                "color": colors[action],
                "emoji_id": data.pop("pending_btn_emoji_id", None)
            })
            # Keep legacy fields synchronized for compatibility.
            last = data["buttons"][-1]
            data["btn_name"] = last["name"]
            data["btn_url"] = last["url"]
            data["btn_color"] = last["color"]
            data["btn_emoji_id"] = last["emoji_id"]
            temp_data[uid] = data
            ask_add_button(chat_id, uid)
        elif action == "addfile":
            text = (
                f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
                f"         SEND FILE            \n"
                f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
                f" Send a photo, video, animation or document now.\n\n"
                f"  Supported: Photo, Video, Animation, Document\n\n"
                f" /cancel to stop."
            )
            sent = _send_pe_return(chat_id, text, use_main=False)
            bot.register_next_step_handler(sent, receive_file)
        elif action == "skipfile":
            send_preview_and_actions(chat_id, uid)
    except Exception as e:
        print(f"⚠️ Error in handle_wizard: {e}")
        try:
            bot.answer_callback_query(call.id, f"Error: {e}", show_alert=True)
        except Exception:
            pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CALLBACK HANDLERS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.callback_query_handler(
    func=lambda call: (
        call.message.chat.type == "private"
        and not call.data.startswith("verify_")
        and call.data != "check_join"
        and call.from_user.id != ADMIN_ID
        and bool(check_joined(call.from_user.id))
    )
)
def locked_callback(call):
    bot.answer_callback_query(
        call.id,
        "🔒 Please join all channels and press Verify first.",
        show_alert=True
    )
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    send_join_notice(call.message.chat.id, call.from_user.id)

@bot.callback_query_handler(func=lambda call: call.data.startswith("verify_") or call.data == "check_join")
def handle_verify(call):
    if call.message.chat.type != "private":
        return
    uid = call.from_user.id
    chat_id = call.message.chat.id

    bot.answer_callback_query(call.id, "⏳ Checking membership...")
    not_joined = check_joined(uid, force_refresh=True)
    if not_joined:
        bot.answer_callback_query(call.id, "❌ You haven't joined all channels! Please join and try again.", show_alert=True)
        # Delete previous message and send new notice with ALL channels (not just unjoined ones) [1]
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except Exception:
            pass
        send_join_notice(chat_id, uid)
    else:
        # Joined all successfully
        bot.answer_callback_query(call.id, "✅ Verification Successful!", show_alert=True)
        register_user(uid)
        _join_cache.pop(uid, None)
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except Exception:
            pass
        
        kb = admin_menu() if uid == ADMIN_ID else main_menu()
        _send_pe(
            chat_id,
            f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
            f"    🔥 𝗖𝗛𝗦 𝗣ʀᴇᴍɪᴜᴍ 𝗥ᴏʙᴏᴛ 🔥    \n"
            f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
            f" Welcome! Choose an option below to continue.",
            use_main=False, reply_markup=kb
        )

# UPDATED: Wrapped inside safe try-except with alerts to ensure buttons never spin indefinitely
@bot.callback_query_handler(func=lambda c: c.data.startswith("action_"))
def handle_action(call):
    if call.message.chat.type != "private":
        return
    try:
        parts   = call.data.split("_")
        if len(parts) < 2:
            bot.answer_callback_query(call.id, "Invalid action.")
            return
            
        action  = parts[1]
        uid     = call.from_user.id # Direct ID resolving is more safe
        chat_id = call.message.chat.id

        # Robust string/integer checking for dictionary session safety
        data = temp_data.get(uid) or temp_data.get(str(uid))
        if not data:
            bot.answer_callback_query(call.id, "Session expired! Make a new post.", show_alert=True)
            return

        if action == "refresh":
            bot.answer_callback_query(call.id, "Refreshing emojis...")
            for key in ("preview_msg_id", "action_msg_id"):
                if data.get(key):
                    try: bot.delete_message(chat_id, data[key])
                    except Exception: pass
            pt, pe_list = process_text_and_entities(data["original_text"], data["original_entities"])
            data["processed_text"]     = pt
            data["processed_entities"] = pe_list
            temp_data[uid]             = data
            send_preview_and_actions(chat_id, uid)

        elif action == "delete":
            bot.answer_callback_query(call.id, "Deleted!")
            for key in ("preview_msg_id", "action_msg_id"):
                if data.get(key):
                    try: bot.delete_message(chat_id, data[key])
                    except Exception: pass
            temp_data.pop(uid, None)

        elif action == "done":
            bot.answer_callback_query(call.id, "Done!")
            if data.get("action_msg_id"):
                try: bot.delete_message(chat_id, data["action_msg_id"])
                except Exception: pass
            award_post_reward(uid)
            temp_data.pop(uid, None)
            kb = admin_menu() if uid == ADMIN_ID else main_menu()
            _send_pe(
                chat_id,
                f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
                f"   POST CREATED SUCCESSFULLY  \n"
                f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
                f" Your premium emoji post is ready!\n"
                f" 🪙 +10 Coins added. Total: {get_user_stats(uid)['coins']} Coins\n"
                f" Tap 𝐌ᴀᴋᴇ 𝐏ᴏꜱᴛ to create another.\n"
                f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿",
                use_main=False, reply_markup=kb
            )
    except Exception as e:
        print(f"⚠️ Error in handle_action: {e}")
        try:
            bot.answer_callback_query(call.id, f"Error: {e}", show_alert=True)
        except Exception:
            pass

@bot.callback_query_handler(func=lambda c: c.data.startswith("menu_"))
def handle_menu_callback(call):
    try:
        uid=call.from_user.id; bot.answer_callback_query(call.id)
        _send_pe(call.message.chat.id,"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n              𝐌ᴀᴋᴇ 𝐏ᴏꜱᴛ              \n➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n👇 𝐂ʜᴏᴏsᴇ 𝐀ɴ 𝐎ᴘᴛɪᴏɴ",use_main=False,reply_markup=admin_menu() if uid==ADMIN_ID else main_menu())
    except Exception as e: print(f"⚠️ Menu callback error: {e}")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  FALLBACK
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@bot.message_handler(func=lambda m: True)
def fallback(message):
    if message.chat.type != "private":
        return
    uid = message.from_user.id
    not_joined = check_joined(uid)
    if not_joined:
        send_join_notice(message.chat.id, uid)
        return
        
    register_user(uid)
    if not bot_active and uid != ADMIN_ID:
        bot_offline_notice(message)
        return
    kb = admin_menu() if uid == ADMIN_ID else main_menu()
    _send_pe(
        message.chat.id,
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n"
        f"        ✨ MAIN MENU ✨        \n"
        f"➿➿➿➿➿➿➿➿➿➿➿➿➿➿➿\n\n"
        f" Please choose an option below.\n\n"
        f" ✏️ MAKE POST   — Create a new post\n"
        f" ❓ HELP        — Learn how the bot works\n"
        f" ℹ️ ABOUT BOT   — Bot information\n"
        f"📌 Tip: During post creation, follow each step shown by the bot.",
        use_main=False, reply_markup=kb
    )

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  LAUNCH 24/7 AUTO-RECOVERY POLLING
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
if __name__ == "__main__":
    print("╔══════════════════════════════════════╗")
    print("║ 🔥 🔥 𝗖𝗛𝗦 𝗣ʀᴇᴍɪᴜᴍ 𝗥ᴏʙᴏᴛ FIXED 🔥 ║")
    print("║   Developer : @ModderSanto 	       ║")
    print(f"║   Placeholder: {PLACEHOLDER} (UTF-16 len={_utf16_len(PLACEHOLDER)})     ║")
    print("║   Status    : RUNNING ✅             ║")
    print("╚══════════════════════════════════════╝")
    
    # 24/7 Infinite Polling loop to prevent the bot from ever going offline
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            print(f"⚠️ Infinity polling crashed: {e}. Auto-recovering and restarting in 5 seconds...")
            time.sleep(5)