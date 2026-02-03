"""
macro_maker.actions

Core action representation and utilities for Macro Maker Pro.

We intentionally keep actions as simple tuple-like sequences so that
existing JSON macro files (saved from older versions) remain usable.
"""

from __future__ import annotations

from typing import Any, Sequence
import os


Action = Sequence[Any]


def format_action(action: Action) -> str:
    """
    Format an action for display in the UI listbox / previews.

    This is essentially the old `_format_action` method, turned into a
    standalone utility so both the UI and executor can share it.
    """
    if not action:
        return "⚠️ <empty action>"

    typ = action[0]

    # --- Basic mouse / timing actions ---

    if typ == "click":
        # ('click', x, y)
        try:
            return f"🖱️ Click at ({int(action[1])}, {int(action[2])})"
        except Exception:
            return f"🖱️ Click at {tuple(action[1:])}"

    elif typ == "drag":
        # ('drag', (x1, y1), (x2, y2))
        try:
            start = action[1]
            end = action[2]
            return f"↗️ Drag from {start} to {end}"
        except Exception:
            return f"↗️ Drag (malformed: {action})"

    elif typ == "delay":
        # ('delay', seconds)
        try:
            secs = float(action[1])
            return f"⏱️ Delay {secs:.2f}s"
        except Exception:
            return f"⏱️ Delay (malformed: {action})"

    # --- Clipboard & hotkeys ---

    elif typ == "copy":
        # ('copy',)
        return "📋 Copy (Ctrl+C)"

    elif typ == "paste":
        # ('paste',)
        return "📄 Paste (Ctrl+V)"

    elif typ == "hotkey":
        # ('hotkey', 'ctrl', 'a', 'c', ...)
        keys = [str(k) for k in action[1:]]
        label = " + ".join(keys) if keys else "<no keys>"
        return f"⌨️ Hotkey: {label}"

    elif typ == "key":
        # ('key', key_name, count, interval)
        try:
            key = str(action[1])
            count = int(action[2])
            interval = float(action[3])
            return f"⌨️ Key: {key} ×{count} (interval {interval:.2f}s)"
        except Exception:
            return f"⌨️ Key (malformed: {action})"

    # --- OCR actions ---

    elif typ == "ocr":
        # New-style:
        # ('ocr', (x1,y1,x2,y2), mode, pattern, processing)
        # Legacy:
        # ('ocr', (x1,y1,x2,y2))  # no extra info
        if len(action) >= 5:
            coords = action[1]
            mode = action[2]
            pattern = action[3]
            processing = action[4]

            mode_desc = {
                "all_text": "All text",
                "numbers": "Numbers only",
                "email": "Email addresses",
                "custom": f"Custom: {pattern}",
                "legacy": "Legacy number grab",
            }.get(mode, str(mode))

            return f"👁️ OCR ({mode_desc}) → {processing or 'copy'}"
        else:
            coords = action[1] if len(action) > 1 else None
            return f"👁️ OCR region: {coords} (legacy)"

    # --- Image check actions ---

    elif typ == "img_check":
        # New-style:
        # ('img_check', image_path, (x1,y1,x2,y2), sub_actions, cfg)
        # where cfg is either:
        #   - float threshold
        #   - dict with {threshold, wait, interval, timeout}
        #
        # Backwards compatibility: we support both.
        image_path = "unknown"
        sub_count = 0
        cfg = None

        if len(action) > 1 and action[1]:
            try:
                image_path = os.path.basename(str(action[1]))
            except Exception:
                image_path = str(action[1])

        if len(action) > 3 and isinstance(action[3], (list, tuple)):
            sub_count = len(action[3])

        if len(action) > 4:
            cfg = action[4]

        wait_flag = False
        if isinstance(cfg, dict):
            wait_flag = bool(cfg.get("wait", False))

        extra = " (wait until found)" if wait_flag else ""
        return f"🔍 Image Check: {image_path}{extra} ({sub_count} sub-actions)"

    elif typ == "click_found":
        # Sub-action used inside img_check blocks
        return "🖱️ Click Found Image (center)"

    # --- Fallback ---

    # If it's something we don't explicitly know how to pretty-print:
    return str(tuple(action))
