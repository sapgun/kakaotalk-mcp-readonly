#!/usr/bin/env python
"""Read-only KakaoTalk CLI (prints JSON).

  uv run python kakao_ro.py list-rooms [--no-enlarge]
  uv run python kakao_ro.py read "<room>" [-n 50] [--close]
  uv run python kakao_ro.py read-new "<room>" [--first 20] [--close]
  uv run python kakao_ro.py open "<room>"
  uv run python kakao_ro.py open-windows
  uv run python kakao_ro.py reset-state ["<room>"]
  KAKAO_ALLOW_SEND=1 uv run python kakao_ro.py send "<room>" --text-file msg.txt --confirm-room "<room>" [--dry-run]
    (opt-in: exactly one text message to one room; only after the user approved the exact text)
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from kakao_mcp import ro_api, controller, state  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Read-only KakaoTalk CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list-rooms"); p.add_argument("--no-enlarge", action="store_true")
    p = sub.add_parser("read"); p.add_argument("room"); p.add_argument("-n", type=int, default=50); p.add_argument("--close", action="store_true")
    p = sub.add_parser("read-new"); p.add_argument("room"); p.add_argument("--first", type=int, default=20); p.add_argument("--close", action="store_true")
    p = sub.add_parser("open"); p.add_argument("room")
    sub.add_parser("open-windows")
    p = sub.add_parser("reset-state"); p.add_argument("room", nargs="?")
    p = sub.add_parser("send"); p.add_argument("room"); p.add_argument("--text-file", required=True); p.add_argument("--confirm-room", required=True); p.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        if a.cmd == "list-rooms":
            out = ro_api.list_rooms(enlarge=not a.no_enlarge)
        elif a.cmd == "read":
            out = ro_api.read(a.room, a.n, a.close); out.pop("_all", None)
        elif a.cmd == "read-new":
            out = ro_api.read_new(a.room, a.first, a.close)
        elif a.cmd == "open":
            out = ro_api.open_room(a.room, restore_focus=True)
        elif a.cmd == "open-windows":
            out = {"rooms": [w["title"] for w in controller.list_chat_windows()]}
        elif a.cmd == "send":
            with open(a.text_file, encoding="utf-8-sig") as f:
                text = f.read().rstrip("\r\n")
            out = controller.send_single_message(a.room, text, a.confirm_room, dry_run=a.dry_run)
        else:
            state.reset(controller._norm_title(a.room) if a.room else None); out = {"reset": a.room or "all"}
    except Exception as e:
        out = {"error": f"{type(e).__name__}: {e}"}
    print(json.dumps(out, ensure_ascii=False, indent=1))
    sys.exit(1 if isinstance(out, dict) and out.get("error") else 0)


if __name__ == "__main__":
    main()