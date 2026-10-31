"""High-level read-only operations shared by the MCP server and kakao_ro.py."""
from typing import Dict

from . import controller, parser, chatlist, state


def list_rooms(enlarge: bool = True) -> Dict:
    return chatlist.list_chat_rooms(enlarge=enlarge)


def open_room(room_name: str, restore_focus: bool = False) -> Dict:
    return controller.search_and_open_room(room_name, restore_focus=restore_focus)


def read(room_name: str, max_messages: int = 50, close_after: bool = False,
         open_if_needed: bool = True) -> Dict:
    r = controller.read_chat_messages(room_name, open_if_needed=open_if_needed, close_after=close_after)
    if not r["success"]:
        return {"error": r["error"]}
    p = parser.parse_chat_text(r["raw_text"])
    msgs = p["messages"][-max_messages:] if max_messages > 0 else p["messages"]
    return {"room": r.get("window_title") or room_name, "member_count": p["member_count"],
            "opened_here": r.get("opened_here"), "closed": r.get("closed"),
            "count": len(msgs), "messages": msgs, "_all": p["messages"]}


def read_new(room_name: str, first_run_limit: int = 20, close_after: bool = False,
             open_if_needed: bool = True) -> Dict:
    r = read(room_name, max_messages=0, close_after=close_after, open_if_needed=open_if_needed)
    if "error" in r:
        return r
    if not r["_all"]:
        return {"error": "No messages parsed (copy may have failed); state not updated", "room": r["room"]}
    key = controller._norm_title(r["room"]) or r["room"]
    f = state.filter_new(key, r["_all"], first_run_limit)
    return {"room": r["room"], "first_run": f["first_run"], "total_read": f["total_read"],
            "new_count": len(f["new_messages"]), "new_messages": f["new_messages"],
            "opened_here": r["opened_here"], "closed": r["closed"]}