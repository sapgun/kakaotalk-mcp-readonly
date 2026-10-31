"""Persist seen-message hashes per room so callers get only new messages."""
import os
import json
import hashlib
import tempfile
from typing import Dict, List

STATE_DIR = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "kakao-mcp-readonly")
STATE_FILE = os.path.join(STATE_DIR, "state.json")
MAX_HASHES = 3000


def _load() -> Dict:
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"rooms": {}}


def _save(state: Dict):
    os.makedirs(STATE_DIR, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=STATE_DIR, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_FILE)


def message_hashes(messages: List[Dict]) -> List[str]:
    """Stable per-message ids: date|sender|time|text plus an occurrence index
    so identical messages in the same minute (e.g. 'ㅋㅋ') stay distinct."""
    seen_count: Dict[str, int] = {}
    out = []
    for m in messages:
        key = f"{m.get('date') or ''}|{m.get('sender','')}|{m.get('time','')}|{m.get('text','')}"
        n = seen_count.get(key, 0)
        seen_count[key] = n + 1
        out.append(hashlib.sha1(f"{key}#{n}".encode("utf-8")).hexdigest()[:16])
    return out


def filter_new(room_key: str, messages: List[Dict], first_run_limit: int = 20) -> Dict:
    state = _load()
    rooms = state.setdefault("rooms", {})
    entry = rooms.get(room_key)
    hashes = message_hashes(messages)
    first_run = entry is None
    if first_run:
        new = messages[-first_run_limit:] if first_run_limit > 0 else []
        seen = []
    else:
        seen_set = set(entry.get("seen", []))
        new = [m for m, h in zip(messages, hashes) if h not in seen_set]
        seen = entry.get("seen", [])
    merged = list(dict.fromkeys(seen + hashes))[-MAX_HASHES:]
    import datetime
    rooms[room_key] = {"seen": merged, "updated": datetime.datetime.now().isoformat(timespec="seconds")}
    _save(state)
    return {"first_run": first_run, "new_messages": new, "total_read": len(messages)}


def reset(room_key: str = None):
    state = _load()
    if room_key is None:
        state = {"rooms": {}}
    else:
        state.get("rooms", {}).pop(room_key, None)
    _save(state)