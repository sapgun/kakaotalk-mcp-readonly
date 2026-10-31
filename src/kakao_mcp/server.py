#!/usr/bin/env python
"""MCP Server for KakaoTalk PC automation via Win32 API."""
import os
from typing import Dict, Optional

from mcp.server.fastmcp import FastMCP

from kakao_mcp import controller
from kakao_mcp import parser
from kakao_mcp import config

app = FastMCP(
    "kakao-mcp-server",
    instructions="MCP Server for KakaoTalk PC automation via Win32 API",
)


@app.tool()
def kakao_health_check() -> Dict:
    """Check if KakaoTalk PC is currently running.
    Returns status, window handle, and process ID."""
    try:
        status = controller.is_kakaotalk_running()
        if status["running"]:
            return {
                "message": "KakaoTalk is running",
                "running": True,
                "hwnd": status["hwnd"],
                "pid": status["pid"],
            }
        return {"message": "KakaoTalk is not running", "running": False}
    except Exception as e:
        return {"error": f"Health check failed: {e}"}


@app.tool()
def kakao_list_open_rooms() -> Dict:
    """List all currently open KakaoTalk chat room windows.
    Returns a list of open chat rooms with their window titles."""
    try:
        status = controller.is_kakaotalk_running()
        if not status["running"]:
            return {"error": "KakaoTalk is not running"}
        rooms = controller.list_chat_windows()
        return {
            "message": f"Found {len(rooms)} open chat room(s)",
            "rooms": [{"title": r["title"], "hwnd": r["hwnd"]} for r in rooms],
        }
    except Exception as e:
        return {"error": f"Failed to list rooms: {e}"}


@app.tool()
def kakao_open_room(room_name: str) -> Dict:
    """Open or bring to front a KakaoTalk chat room by name.
    If the chat window is already open, brings it to foreground.
    If not, searches for the room in KakaoTalk's search bar.

    Args:
        room_name: The name of the chat room or person to open.
    """
    try:
        hwnd = controller.find_chat_window(room_name)
        if hwnd:
            controller.bring_window_to_front(hwnd)
            return {"message": f"Chat room '{room_name}' brought to foreground", "hwnd": hwnd}
        result = controller.search_and_open_room(room_name)
        if result["success"]:
            return {"message": result["message"], "hwnd": result.get("hwnd")}
        return {"error": result["error"]}
    except Exception as e:
        return {"error": f"Failed to open room '{room_name}': {e}"}


# @app.tool()  # disabled: read-only
def kakao_send_message(room_name: str, message: str) -> Dict:
    """Send a text message to a KakaoTalk chat room.
    The chat room window must already be open.

    Args:
        room_name: Exact title of the chat room window.
        message: The text message to send.
    """
    try:
        if not message.strip():
            return {"error": "Message cannot be empty"}
        result = controller.send_message_to_room(room_name, message)
        if result["success"]:
            return {"message": result["message"]}
        return {"error": result["error"]}
    except Exception as e:
        return {"error": f"Failed to send message: {e}"}


# @app.tool()  # disabled: read-only
def kakao_send_bulk(room_names: list[str], message: str, interval_sec: float = 0.5) -> Dict:
    """Send the same message to multiple KakaoTalk chat rooms at once.
    Opens each room if not already open and sends the message sequentially.
    Maintains a safe interval between rooms to ensure reliability.

    Args:
        room_names: List of chat room names or person names to send to.
        message: The text message to send to all rooms.
        interval_sec: Seconds to wait between rooms (default 0.5, minimum 0.3).
    """
    try:
        if not room_names:
            return {"error": "room_names cannot be empty"}
        if not message.strip():
            return {"error": "Message cannot be empty"}
        result = controller.send_bulk_messages(room_names, message, interval_sec)
        if result["success"]:
            return {"message": result["message"], "results": result["results"]}
        return {"error": result.get("message", "Failed to send bulk messages"), "results": result.get("results", [])}
    except Exception as e:
        return {"error": f"Failed to send bulk messages: {e}"}


# @app.tool()  # disabled: read-only
def kakao_send_image(room_name: str, image_paths: list[str]) -> Dict:
    """Send image file(s) to a KakaoTalk chat room.
    Copies the image to clipboard using file-drop format and pastes into the chat.
    KakaoTalk shows a confirmation dialog which is automatically accepted.
    The chat room window must already be open.
    NOTE: This briefly brings the chat window to the foreground.

    Args:
        room_name: Exact title of the chat room window.
        image_paths: List of absolute file paths to images (JPG, PNG, GIF, BMP, WebP).
    """
    try:
        if not image_paths:
            return {"error": "image_paths cannot be empty"}

        for path in image_paths:
            if not os.path.isfile(os.path.abspath(path)):
                return {"error": f"Image file not found: {path}"}

        if len(image_paths) == 1:
            result = controller.send_image_to_room(room_name, image_paths[0])
            if result["success"]:
                return {"message": result["message"]}
            return {"error": result["error"]}
        else:
            result = controller.send_images_to_room(room_name, image_paths)
            if result["success"]:
                return {"message": result["message"], "results": result["results"]}
            return {"error": result.get("message", "Failed to send images"), "results": result.get("results", [])}
    except Exception as e:
        return {"error": f"Failed to send image: {e}"}


@app.tool()
def kakao_read_messages(room_name: str, max_messages: int = 50) -> Dict:
    """Read recent messages from a KakaoTalk chat room.
    Uses clipboard-based reading (Ctrl+A, Ctrl+C on the chat list).
    NOTE: This briefly brings the chat window to the foreground.

    Args:
        room_name: Exact title of the chat room window.
        max_messages: Maximum number of recent messages to return (default 50).
    """
    try:
        result = controller.read_chat_messages(room_name)
        if not result["success"]:
            return {"error": result["error"]}
        parsed = parser.parse_chat_text(result["raw_text"])
        messages = parsed["messages"]
        if len(messages) > max_messages:
            messages = messages[-max_messages:]
        return {
            "message": f"Read {len(messages)} messages from '{room_name}'",
            "room_name": parsed["room_name"],
            "member_count": parsed["member_count"],
            "messages": messages,
        }
    except Exception as e:
        return {"error": f"Failed to read messages: {e}"}


@app.tool()
def kakao_extract_links(room_name: str) -> Dict:
    """Extract all URLs/links from messages in a KakaoTalk chat room.
    Reads the chat first, then extracts URLs from all messages.

    Args:
        room_name: Exact title of the chat room window.
    """
    try:
        result = controller.read_chat_messages(room_name)
        if not result["success"]:
            return {"error": result["error"]}
        parsed = parser.parse_chat_text(result["raw_text"])
        urls = parser.extract_urls_from_messages(parsed["messages"])
        return {
            "message": f"Found {len(urls)} URL(s) in '{room_name}'",
            "links": urls,
        }
    except Exception as e:
        return {"error": f"Failed to extract links: {e}"}


# @app.tool()  # disabled: read-only
def kakao_send_mention(room_name: str, mention_name: str, message: str) -> Dict:
    """Send a message with @mention to a KakaoTalk chat room.
    Types '@' to activate the mention popup, selects the target user,
    then sends the message. The chat room window must already be open.
    NOTE: This briefly brings the chat window to the foreground.

    Args:
        room_name: Exact title of the chat room window.
        mention_name: Display name of the person to mention (e.g. '홍길동').
        message: The text message to send after the mention.
    """
    try:
        if not mention_name.strip():
            return {"error": "Mention name cannot be empty"}
        if not message.strip():
            return {"error": "Message cannot be empty"}
        result = controller.send_mention_message(room_name, mention_name, message)
        if result["success"]:
            return {"message": result["message"]}
        return {"error": result["error"]}
    except Exception as e:
        return {"error": f"Failed to send mention message: {e}"}


@app.tool()
def kakao_download_images(
    room_name: str,
    output_dir: Optional[str] = None,
    max_images: int = 10,
) -> Dict:
    """Download recent images from KakaoTalk's local cache.
    Images are sorted by modification time (newest first).
    Note: Cache is global, not per-room — images are the most recently cached ones.

    Args:
        room_name: Chat room name (for context/logging).
        output_dir: Directory to save images. Defaults to Documents/KakaoMCP_Images.
        max_images: Maximum number of images to download (default 10).
    """
    try:
        if output_dir is None:
            output_dir = config.DEFAULT_IMAGE_OUTPUT_DIR
        os.makedirs(output_dir, exist_ok=True)
        result = controller.download_recent_images(room_name, output_dir, max_images)
        return result
    except Exception as e:
        return {"error": f"Failed to download images: {e}"}


@app.tool()
def kakao_start_monitor(
    room_name: str,
    keywords: list[str],
    poll_interval_sec: float = 5.0,
) -> Dict:
    """Start monitoring a KakaoTalk chat room for keyword matches.
    Runs in background, checking for new messages at the specified interval.
    Use kakao_get_monitor_events() to retrieve detected keyword matches.
    NOTE: The chat room window must be open. Polling brings it to foreground briefly.

    Args:
        room_name: Exact title of the chat room window to monitor.
        keywords: List of keywords to watch for (case-insensitive).
        poll_interval_sec: Seconds between each poll (minimum 3, default 5).
    """
    try:
        if not keywords:
            return {"error": "Keywords list cannot be empty"}
        result = controller._chat_monitor.start(room_name, keywords, poll_interval_sec)
        if result["success"]:
            return {"message": result["message"]}
        return {"error": result["error"]}
    except Exception as e:
        return {"error": f"Failed to start monitor: {e}"}


@app.tool()
def kakao_stop_monitor() -> Dict:
    """Stop the running chat room monitor."""
    try:
        result = controller._chat_monitor.stop()
        if result["success"]:
            return {"message": result["message"]}
        return {"error": result["error"]}
    except Exception as e:
        return {"error": f"Failed to stop monitor: {e}"}


@app.tool()
def kakao_get_monitor_events() -> Dict:
    """Get pending keyword match events from the chat monitor.
    Returns events detected since last call. Each event includes:
    - keyword: the matched keyword
    - trigger_message: the message that matched (sender, time, text)
    - recent_context: last 10 messages for context understanding
    - room_name: the monitored chat room

    Call this periodically while monitor is running to check for matches.
    """
    try:
        is_running = controller._chat_monitor.is_running
        events = controller._chat_monitor.get_events()
        return {
            "monitoring": is_running,
            "event_count": len(events),
            "events": events,
        }
    except Exception as e:
        return {"error": f"Failed to get monitor events: {e}"}


def main():
    app.run(transport="stdio")


if __name__ == "__main__":
    main()
