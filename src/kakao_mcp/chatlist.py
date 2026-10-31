"""Read the KakaoTalk main-window chat room list via screen capture + Windows OCR.

KakaoTalk draws the chat list itself (no UIA/MSAA items, verified), so this
captures the list control with PrintWindow and runs the built-in Windows OCR
engine (Korean) on it. Results are best-effort: OCR can misread characters.
"""
import os
import re
import time
import ctypes
import asyncio
import subprocess
from typing import Dict, List, Optional

import win32gui
import win32ui
import win32con

from . import config

_user32 = ctypes.windll.user32
SCALE = 3  # upscale factor before OCR (improves Hangul accuracy)

TIME_RE = re.compile(r"^(오전|오후|오|후)\s*\S*\d|^어제$|^\d{1,2}월\s*\d{1,2}일$|^\d{4}[.\-]\s*\d{1,2}|^\d{1,2}:\d{2}$|요일$")


def _main_hwnd() -> int:
    return win32gui.FindWindow(config.KAKAO_MAIN_WINDOW_CLASS, config.KAKAO_MAIN_WINDOW_TITLE)


def _find_by_title_part(parent: int, part: str) -> Optional[int]:
    found: List[int] = []

    def _cb(h, _):
        if part in win32gui.GetWindowText(h) and win32gui.IsWindowVisible(h):
            found.append(h)
            return False
        return True

    try:
        win32gui.EnumChildWindows(parent, _cb, None)
    except Exception:
        pass
    return found[0] if found else None


def _dpi(hwnd: int) -> int:
    try:
        return _user32.GetDpiForWindow(hwnd) or 96
    except Exception:
        return 96


def _work_area():
    class RECT(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long), ("r", ctypes.c_long), ("b", ctypes.c_long)]
    r = RECT()
    _user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(r), 0)  # SPI_GETWORKAREA
    return r.l, r.t, r.r, r.b


def _capture_region(main: int, region, out_bmp: str):
    l, t, r, b = win32gui.GetWindowRect(main)
    W, H = r - l, b - t
    rl, rt, rr, rb = region
    w, h = rr - rl, rb - rt
    hdc = win32gui.GetWindowDC(main)
    mdc = win32ui.CreateDCFromHandle(hdc)
    src = mdc.CreateCompatibleDC()
    bmp = win32ui.CreateBitmap()
    bmp.CreateCompatibleBitmap(mdc, W, H)
    src.SelectObject(bmp)
    _user32.PrintWindow(main, src.GetSafeHdc(), 2)  # PW_RENDERFULLCONTENT
    dst = mdc.CreateCompatibleDC()
    bmp2 = win32ui.CreateBitmap()
    bmp2.CreateCompatibleBitmap(mdc, w * SCALE, h * SCALE)
    dst.SelectObject(bmp2)
    ctypes.windll.gdi32.SetStretchBltMode(dst.GetSafeHdc(), 4)  # HALFTONE
    dst.StretchBlt((0, 0), (w * SCALE, h * SCALE), src, (rl - l, rt - t), (w, h), win32con.SRCCOPY)
    bmp2.SaveBitmapFile(dst, out_bmp)
    raw = bmp2.GetBitmapBits(True)
    for o in (src, dst):
        o.DeleteDC()
    mdc.DeleteDC()
    win32gui.ReleaseDC(main, hdc)
    win32gui.DeleteObject(bmp.GetHandle())
    win32gui.DeleteObject(bmp2.GetHandle())
    return w * SCALE, h * SCALE, raw


async def _ocr_async(path: str, lang: str = "ko"):
    from winrt.windows.media.ocr import OcrEngine
    from winrt.windows.globalization import Language
    from winrt.windows.graphics.imaging import BitmapDecoder
    from winrt.windows.storage import StorageFile, FileAccessMode
    f = await StorageFile.get_file_from_path_async(path)
    stream = await f.open_async(FileAccessMode.READ)
    dec = await BitmapDecoder.create_async(stream)
    sb = await dec.get_software_bitmap_async()
    eng = OcrEngine.try_create_from_language(Language(lang))
    if eng is None:
        raise RuntimeError("Korean OCR language not installed in Windows")
    res = await eng.recognize_async(sb)
    lines = []
    for ln in res.lines:
        ws = list(ln.words)
        if not ws:
            continue
        x0 = min(w.bounding_rect.x for w in ws)
        y0 = min(w.bounding_rect.y for w in ws)
        x1 = max(w.bounding_rect.x + w.bounding_rect.width for w in ws)
        y1 = max(w.bounding_rect.y + w.bounding_rect.height for w in ws)
        lines.append({"x": x0, "y": y0, "x1": x1, "y1": y1, "text": ln.text,
                      "words": [{"text": w.text, "x": w.bounding_rect.x, "x1": w.bounding_rect.x + w.bounding_rect.width} for w in ws]})
    return lines


def _ocr(path: str, lang: str = "ko"):
    return asyncio.run(_ocr_async(path, lang))


def _to_png(bmp: str) -> Optional[str]:
    png = os.path.splitext(bmp)[0] + ".png"
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Add-Type -AssemblyName System.Drawing;"
             f"$i=[Drawing.Image]::FromFile('{bmp}');$i.Save('{png}',[Drawing.Imaging.ImageFormat]::Png);$i.Dispose()"],
            capture_output=True, timeout=15,
        )
        return png if os.path.exists(png) else None
    except Exception:
        return None


def _preprocess(raw: bytes, w: int, h: int, out_bmp: str):
    """Binarize for OCR: dark text on white; invert red unread badges so their
    white digits become dark. Returns list of badge boxes (x0,y0,x1,y1)."""
    import numpy as np
    a = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 4)[:, :, :3].astype(np.int16)
    b, g, r = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    lum = (0.299 * r + 0.587 * g + 0.114 * b)
    out = np.clip(lum, 0, 255).astype(np.uint8)
    red = (r > 190) & (g < 150) & (b < 150)
    badges = []
    # find red blobs by scanning rows of the mask in the right 25%
    x_start = int(w * 0.75)
    rows_any = red[:, x_start:].any(axis=1)
    y = 0
    while y < h:
        if rows_any[y]:
            y0 = y
            while y < h and rows_any[y]:
                y += 1
            y1 = y
            cols = np.where(red[y0:y1, x_start:].any(axis=0))[0]
            if y1 - y0 > 8 and len(cols):
                x0, x1 = x_start + cols[0], x_start + cols[-1] + 1
                badges.append((int(x0), int(y0), int(x1), int(y1)))
                sub = a[y0:y1, x0:x1]
                sl = (0.299 * sub[:, :, 2] + 0.587 * sub[:, :, 1] + 0.114 * sub[:, :, 0])
                inv = np.clip((255 - sl) * 255 / 100, 0, 255).astype(np.uint8)
                rm = red[y0:y1, x0:x1]
                for yy in range(y1 - y0):
                    xs = np.where(rm[yy])[0]
                    if len(xs):
                        inv[yy, :xs[0]] = 255
                        inv[yy, xs[-1] + 1:] = 255
                    else:
                        inv[yy, :] = 255
                out[y0:y1, x0:x1] = inv
        y += 1
    _write_gray_bmp(out, out_bmp)
    # badge strip: each badge on white with margins, stacked vertically
    strip_info = []
    if badges:
        # laid out horizontally (Windows OCR ignores tiny isolated images)
        M = 60
        bh = max(b[3] - b[1] for b in badges) + 2 * M
        tiles, xx = [], 0
        for bx in badges:
            t = np.full((bh, bx[2] - bx[0] + 2 * M), 255, np.uint8)
            crop = out[bx[1]:bx[3], bx[0]:bx[2]]
            t[M:M + crop.shape[0], M:M + crop.shape[1]] = np.where(crop < 128, 0, 255)
            strip_info.append((xx, xx + t.shape[1]))
            xx += t.shape[1]
            tiles.append(t)
        strip = np.hstack(tiles)
        canvas = np.full((bh + 400, strip.shape[1] + 400), 255, np.uint8)
        canvas[200:200 + bh, 200:200 + strip.shape[1]] = strip
        strip = canvas
        strip_info = [(s0 + 200, s1 + 200) for s0, s1 in strip_info]
        _write_gray_bmp(strip, out_bmp.replace(".bmp", "_badges.bmp"))
    return badges, strip_info


def _write_gray_bmp(out, path):
    import numpy as np
    import struct
    h, w = out.shape
    img = np.stack([out] * 3, axis=2)[::-1]  # BMP is bottom-up
    pad = (4 - (w * 3) % 4) % 4
    data = b"".join(img[i].tobytes() + b"\0" * pad for i in range(h))
    hdr = struct.pack("<2sIHHI", b"BM", 54 + len(data), 0, 0, 54)
    info = struct.pack("<IiiHHIIiiII", 40, w, h, 1, 24, 0, len(data), 2835, 2835, 0, 0)
    with open(path, "wb") as fh:
        fh.write(hdr + info + data)


def _norm_time(tm: str) -> str:
    t = tm.replace("~", ":").replace(";", ":").strip()
    if t.startswith("오"):
        ampm = "오전" if "전" in t[:4] else "오후"
        digits = "".join(re.findall(r"\d", t))
        if len(digits) in (3, 4):
            return f"{ampm} {int(digits[:-2])}:{digits[-2:]}"
        return f"{ampm} ?({t})"
    return t


def _parse_rows(lines: List[Dict], width: int, row_h: float, badges=()) -> List[Dict]:
    text_left = width * 0.22  # left part is avatars
    right_col = width * 0.78
    lines = [l for l in lines if l["x1"] > text_left and l["text"].strip()]
    lines.sort(key=lambda l: l["y"])
    rows: List[List[Dict]] = []
    start = None
    for l in lines:
        if start is None or l["y"] - start > row_h * 0.6:
            rows.append([])
            start = l["y"]
        rows[-1].append(l)
    out = []
    for r in rows:
        top_y = r[0]["y"]
        top = [l for l in r if l["y"] - top_y < row_h * 0.25]
        bottom = [l for l in r if l not in top]
        name_parts = [l for l in top if l["x"] < right_col and not (TIME_RE.search(l["text"]) and l["x"] > width * 0.6)]
        time_parts = [l for l in top if l not in name_parts]
        prev_parts = [l for l in bottom if l["x"] < right_col]
        unread_parts = [l for l in bottom if l["x"] >= right_col]
        name = " ".join(l["text"] for l in sorted(name_parts, key=lambda l: l["x"])).strip()
        if not name:
            continue
        member = None
        m = re.match(r"^(.*?)\s+(\d{1,4})\s*\S?$", name)
        if m and not re.search(r"\d$", m.group(1)):
            name, member = m.group(1).strip(), int(m.group(2))
        unread = None
        row_y0 = r[0]["y"] - row_h * 0.2
        row_y1 = r[0]["y"] + row_h * 0.8
        mine = [b for b in badges if row_y0 <= (b[1] + b[3]) / 2 <= row_y1]
        has_badge = bool(mine)
        if mine:
            unread = mine[0][4]
        if has_badge and not unread:
            unread = "?"
        if not has_badge:
            unread = None
        tm = " ".join(l["text"] for l in time_parts).strip() or None
        if tm:
            tm = _norm_time(tm)
        out.append({
            "name": name,
            "member_count": member,
            "preview": " ".join(l["text"] for l in sorted(prev_parts, key=lambda l: (l["y"], l["x"]))).strip(),
            "time": tm,
            "unread": unread,
        })
    return out


def list_chat_rooms(enlarge: bool = True, save_png: bool = True) -> Dict:
    main = _main_hwnd()
    if not main:
        return {"success": False, "error": "KakaoTalk main window not found"}
    if _user32.IsIconic(main):
        return {"success": False, "error": "KakaoTalk main window is minimized; restore it first"}
    list_hwnd = _find_by_title_part(main, "ChatRoomListCtrl")
    if not list_hwnd:
        return {"success": False, "error": "Chat list not visible (open the 채팅 tab in KakaoTalk)"}

    orig = win32gui.GetWindowRect(main)
    resized = False
    try:
        if enlarge:
            wl, wt, wr, wb = _work_area()
            new_h = (wb - 8) - orig[1]
            if new_h > (orig[3] - orig[1]) + 40:
                SWP = 0x0002 | 0x0004 | 0x0010  # NOMOVE|NOZORDER|NOACTIVATE
                _user32.SetWindowPos(main, 0, 0, 0, orig[2] - orig[0], new_h, SWP)
                resized = True
                time.sleep(0.6)
        region = win32gui.GetWindowRect(list_hwnd)
        # drop right scrollbar strip
        region = (region[0], region[1], region[2] - 14, region[3])
        out_bmp = os.path.join(os.environ.get("TEMP", "."), "kakao_chatlist.bmp")
        w, h, raw = _capture_region(main, region, out_bmp)
    finally:
        if resized:
            _user32.SetWindowPos(main, 0, orig[0], orig[1], orig[2] - orig[0], orig[3] - orig[1], 0x0004 | 0x0010)
    ocr_bmp = out_bmp.replace(".bmp", "_ocr.bmp")
    badges, strip = _preprocess(raw, w, h, ocr_bmp)
    lines = _ocr(ocr_bmp)
    badge_vals = []
    if badges:
        bl = []
        for lang in ("en-US", "fr-FR", "ko"):
            try:
                bl = _ocr(ocr_bmp.replace(".bmp", "_badges.bmp"), lang)
                break
            except Exception:
                continue
        for bi, (s0, s1) in enumerate(strip):
            bx = badges[bi]
            inside = [wd["text"] for l in lines for wd in l.get("words", [])
                      if bx[0] - 10 <= (wd["x"] + wd["x1"]) / 2 <= bx[2] + 10 and bx[1] - 10 <= (l["y"] + l["y1"]) / 2 <= bx[3] + 10]
            d_main = re.sub(r"[^\d+]", "", "".join(inside))
            words = [wd for l in bl for wd in l.get("words", [])]
            txt = "".join(wd["text"] for wd in words if s0 <= (wd["x"] + wd["x1"]) / 2 < s1)
            txt = txt.replace("O", "0").replace("o", "0").replace("I", "1").replace("l", "1")
            badge_vals.append(re.sub(r"[^\d+]", "", txt) or d_main or "?")
    badges = [b + (v,) for b, v in zip(badges, badge_vals)]
    row_h = 70 * _dpi(main) / 96 * SCALE
    rooms = _parse_rows(lines, w, row_h, badges)
    res = {"success": True, "rooms": rooms, "ocr_note": "OCR-based; names/previews may contain misread characters"}
    if save_png:
        res["image"] = _to_png(out_bmp)
    return res