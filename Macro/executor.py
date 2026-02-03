"""
executor.py

Macro execution engine for Macro Maker Pro.

This module is deliberately UI-agnostic:
- No tkinter imports
- No messageboxes or .after()
- All communication back to the UI happens via callbacks.

Typical usage from the UI layer:

    from executor import MacroExecutor

    executor = MacroExecutor(
        actions=self.actions,
        loop_count=self.loop_count,
        status_callback=lambda msg: self.master.after(0, lambda: self.update_status(msg)),
        error_callback=lambda msg: self.master.after(0, lambda: messagebox.showerror("Error", msg)),
        done_callback=lambda ok: self.master.after(0, self._on_macro_done(ok)),
    )

    thread = threading.Thread(target=executor.run, daemon=True)
    thread.start()

The UI is responsible for wrapping callbacks with `after()` so that
Tkinter is only touched from the main thread.
"""

from __future__ import annotations

import time
import os
from typing import Callable, Optional, List, Sequence, Any, Tuple

import pyautogui
import mss
from PIL import Image
import pytesseract
import pyperclip

from image_ocr import match_template, process_ocr_text


Action = Sequence[Any]
StatusCallback = Callable[[str], None]
ErrorCallback = Callable[[str], None]
DoneCallback = Callable[[bool], None]


# Ensure pyautogui failsafe is on (top-left corner to abort)
try:
    pyautogui.FAILSAFE = True
except Exception:
    pass


class MacroExecutor:
    """
    Executes a sequence of actions (click, drag, delay, ocr, img_check, etc.)

    Parameters
    ----------
    actions : list of actions
        The macro actions, typically tuples like ('click', x, y) etc.
    loop_count : int
        Number of times to run the entire action list.
    status_callback : callable(str) -> None, optional
        Called with human-readable status messages as the macro runs.
    error_callback : callable(str) -> None, optional
        Called when a fatal error occurs during macro execution.
    done_callback : callable(bool) -> None, optional
        Called once when the macro stops (naturally or due to error/stop()).
        Argument is True if completed normally, False if failed/aborted.
    """

    def __init__(
        self,
        actions: List[Action],
        loop_count: int = 1,
        status_callback: Optional[StatusCallback] = None,
        error_callback: Optional[ErrorCallback] = None,
        done_callback: Optional[DoneCallback] = None,
    ) -> None:
        self.actions: List[Action] = list(actions)
        self.loop_count: int = max(1, int(loop_count))

        self._status_cb = status_callback
        self._error_cb = error_callback
        self._done_cb = done_callback

        self._running: bool = False

    # ------------------------------------------------------------------ #
    # Public control methods
    # ------------------------------------------------------------------ #

    @property
    def running(self) -> bool:
        """Return True if the macro is currently running."""
        return self._running

    def stop(self) -> None:
        """
        Request that the macro stop as soon as possible.

        The run() method checks this flag between actions and during long delays.
        """
        self._running = False

    # ------------------------------------------------------------------ #
    # Core execution
    # ------------------------------------------------------------------ #

    def run(self) -> None:
        """
        Execute the macro synchronously in the current thread.

        The caller is expected to run this in a background thread if using a GUI.
        """
        if not self.actions:
            self._status("No actions to execute.")
            if self._done_cb:
                self._done_cb(False)
            return

        if self._running:
            self._status("Macro is already running.")
            if self._done_cb:
                self._done_cb(False)
            return

        self._running = True
        completed_ok = False

        try:
            # Countdown (like the original: 3,2,1)
            for i in range(3, 0, -1):
                if not self._running:
                    self._status("Macro start cancelled.")
                    if self._done_cb:
                        self._done_cb(False)
                    return
                self._status(f"Starting in {i}...")
                time.sleep(1.0)

            total_actions = len(self.actions) * self.loop_count
            action_count = 0

            for loop_index in range(self.loop_count):
                if not self._running:
                    break

                self._status(f"Executing loop {loop_index + 1}/{self.loop_count}")

                for action in self.actions:
                    if not self._running:
                        break

                    action_count += 1
                    self._status(f"Action {action_count}/{total_actions}")
                    self._execute_action(action)

            if self._running:
                completed_ok = True
                self._status("Macro completed successfully!")

        except Exception as e:
            msg = f"Fatal error during macro execution: {e}"
            print(msg)
            self._status(msg)
            if self._error_cb:
                self._error_cb(msg)
            completed_ok = False

        finally:
            self._running = False
            if self._done_cb:
                self._done_cb(completed_ok)

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #

    def _status(self, message: str) -> None:
        """Send a status message to the callback (and print for debug)."""
        print(f"[MacroExecutor] {message}")
        if self._status_cb:
            self._status_cb(message)

    def _sleep_with_checks(self, seconds: float) -> None:
        """Sleep in small increments, honoring stop requests."""
        remaining = max(0.0, float(seconds))
        step = 0.05  # 50ms steps
        while remaining > 0 and self._running:
            dt = min(step, remaining)
            time.sleep(dt)
            remaining -= dt

    def _grab_region(self, left: int, top: int, width: int, height: int) -> Image.Image:
        """
        Capture a screen region and return a PIL Image.

        Uses mss when available; falls back to pyautogui.screenshot().
        """
        try:
            with mss.mss() as sct:
                monitor = {
                    "top": int(top),
                    "left": int(left),
                    "width": int(width),
                    "height": int(height),
                }
                sct_img = sct.grab(monitor)
                return Image.frombytes("RGB", sct_img.size, sct_img.rgb)
        except Exception as e:
            print(f"[MacroExecutor] Screenshot capture error (mss): {e}")
            # Fallback to pyautogui
            return pyautogui.screenshot(region=(int(left), int(top), int(width), int(height)))

    # ------------------------------------------------------------------ #
    # Per-action execution
    # ------------------------------------------------------------------ #

    def _execute_action(self, action: Action) -> None:
        """Execute a single high-level action."""
        if not action:
            return

        typ = action[0]

        if typ == "click":
            self._execute_click(action)

        elif typ == "drag":
            self._execute_drag(action)

        elif typ == "delay":
            self._execute_delay(action)

        elif typ == "copy":
            pyautogui.hotkey("ctrl", "c")

        elif typ == "paste":
            pyautogui.hotkey("ctrl", "v")

        elif typ == "hotkey":
            self._execute_hotkey(action)

        elif typ == "key":
            self._execute_key(action)

        elif typ == "ocr":
            self._execute_ocr(action)

        elif typ == "img_check":
            self._execute_img_check(action)

        else:
            self._status(f"Unknown action type: {typ}")

    # --- Basic actions ------------------------------------------------- #

    def _execute_click(self, action: Action) -> None:
        # ('click', x, y)
        try:
            _, x, y = action
            pyautogui.click(int(x), int(y))
        except Exception as e:
            raise RuntimeError(f"Error executing click: {e}")

    def _execute_drag(self, action: Action) -> None:
        # ('drag', (x1, y1), (x2, y2))
        try:
            _, start, end = action
            x1, y1 = start
            x2, y2 = end
            pyautogui.mouseDown(int(x1), int(y1))
            pyautogui.moveTo(int(x2), int(y2), duration=0.1)
            pyautogui.mouseUp()
        except Exception as e:
            raise RuntimeError(f"Error executing drag: {e}")

    def _execute_delay(self, action: Action) -> None:
        # ('delay', seconds)
        try:
            delay_time = float(action[1])
        except Exception:
            delay_time = 0.0
        self._sleep_with_checks(delay_time)

    def _execute_hotkey(self, action: Action) -> None:
        # ('hotkey', 'ctrl', 'a', ...)
        keys = [str(k) for k in action[1:]]
        if not keys:
            return
        try:
            pyautogui.hotkey(*keys)
        except Exception as e:
            raise RuntimeError(f"Error executing hotkey {keys}: {e}")

    def _execute_key(self, action: Action) -> None:
        # ('key', key_name, count, interval)
        try:
            _, key_name, count, interval = action
            key_name = str(key_name).lower()
            count = int(count)
            interval = float(interval)
        except Exception as e:
            raise RuntimeError(f"Malformed key action: {action} ({e})")

        try:
            if pyautogui.KEYBOARD_KEYS and key_name not in pyautogui.KEYBOARD_KEYS:
                raise ValueError(f"Unsupported key: {key_name}")
            pyautogui.press(key_name, presses=count, interval=interval)
        except Exception as e:
            print(f"[MacroExecutor] Key press error: {e}")

    # --- OCR ----------------------------------------------------------- #

    def _execute_ocr(self, action: Action) -> None:
        """
        ('ocr', (x1,y1,x2,y2), mode, pattern, processing)
        or legacy: ('ocr', (x1,y1,x2,y2))
        """
        # Parse fields
        if len(action) >= 5:
            coords = action[1]
            mode = action[2]
            pattern = action[3]
            processing = action[4]
        else:
            coords = action[1]
            mode = "legacy"
            pattern = ""
            processing = "copy"

        try:
            x1, y1, x2, y2 = coords
        except Exception as e:
            raise RuntimeError(f"Malformed OCR coordinates: {coords} ({e})")

        left, top = min(x1, x2), min(y1, y2)
        width, height = abs(x2 - x1), abs(y2 - y1)

        # Capture region
        img = self._grab_region(int(left), int(top), int(width), int(height))

        # Try several PSM modes, like the original code
        configs = ["--psm 6", "--psm 7", "--psm 8", "--psm 13"]
        text = ""
        for cfg in configs:
            try:
                text = pytesseract.image_to_string(img, config=cfg).strip()
                if text:
                    break
            except Exception:
                continue

        if not text:
            # Final fallback
            try:
                text = pytesseract.image_to_string(img).strip()
            except Exception as e:
                raise RuntimeError(f"OCR error: {e}")

        result = process_ocr_text(text, mode, pattern)

        if not result:
            self._status(f"OCR: No matches found for mode '{mode}'")
            return

        # Handle processing behavior
        if processing in ("copy", "first"):
            if isinstance(result, list):
                value = result[0] if result else ""
            else:
                value = str(result)
            pyperclip.copy(value)
            self._status(f"OCR: Copied '{value}'")

        elif processing == "all":
            if isinstance(result, list):
                combined = " ".join(str(r) for r in result)
            else:
                combined = str(result)
            pyperclip.copy(combined)
            if isinstance(result, list):
                self._status(f"OCR: Copied {len(result)} matches")
            else:
                self._status(f"OCR: Copied '{combined}'")

        elif processing == "show":
            display_result = result if isinstance(result, str) else str(result)
            self._status(f"OCR Result: '{display_result}'")

        else:
            # Unknown processing mode, default to showing
            display_result = result if isinstance(result, str) else str(result)
            self._status(f"OCR (mode={processing}): '{display_result}'")

    # --- Image check --------------------------------------------------- #

    def _execute_img_check(self, action: Action) -> None:
        """
        Image check with optional wait-until-found and sub-actions.

        Action layout:
            ('img_check', image_path, (x1,y1,x2,y2), sub_actions, cfg)

        cfg is either:
            - float threshold
            - dict with:
                {
                    "threshold": 0.8,
                    "wait": True/False,
                    "interval": 0.5,
                    "timeout": 0.0,  # seconds, 0 = no timeout
                }
        """
        if len(action) < 5:
            raise RuntimeError(f"Malformed img_check action: {action}")

        _, image_path, coords, sub_actions, cfg = action
        if not os.path.exists(str(image_path)):
            self._status(f"Image check skipped: file not found ({image_path})")
            return

        try:
            x1, y1, x2, y2 = coords
        except Exception as e:
            raise RuntimeError(f"Malformed img_check coordinates: {coords} ({e})")

        left, top = min(x1, x2), min(y1, y2)
        width, height = abs(x2 - x1), abs(y2 - y1)

        # Config: threshold + wait/interval/timeout
        wait = False
        interval = 0.5
        timeout = 0.0

        if isinstance(cfg, dict):
            threshold = float(cfg.get("threshold", 0.8))
            wait = bool(cfg.get("wait", False))
            interval = float(cfg.get("interval", 0.5))
            timeout = float(cfg.get("timeout", 0.0))
        else:
            # Backwards compatibility: just a float threshold
            threshold = float(cfg)

        img_name = os.path.basename(str(image_path))

        def capture_and_match() -> Tuple[bool, float, Optional[Tuple[int, int]], int, int]:
            region_img = self._grab_region(int(left), int(top), int(width), int(height))
            return match_template(str(image_path), region_img)

        # Search loop
        image_found = False
        score = 0.0
        top_left = None  # type: Optional[Tuple[int, int]]
        tmpl_w = tmpl_h = 0

        if wait:
            self._status(f"Waiting for image: {img_name}...")
            start_time = time.time()

            while self._running:
                ok, score, top_left, tmpl_w, tmpl_h = capture_and_match()
                if ok and score >= threshold:
                    image_found = True
                    break
                if not ok:
                    # Can't compare; avoid infinite spinning
                    break
                if timeout > 0.0 and (time.time() - start_time) >= timeout:
                    break
                self._sleep_with_checks(max(0.01, interval))

        else:
            ok, score, top_left, tmpl_w, tmpl_h = capture_and_match()
            image_found = ok and score >= threshold

        if not self._running:
            return  # stopped during wait

        if image_found and top_left is not None:
            self._status(
                f"Image found: {img_name} (score {score:.3f}) - executing {len(sub_actions)} sub-actions"
            )
            print(
                f"[MacroExecutor] Image found: {img_name} - score {score:.3f} - "
                f"sub-actions: {len(sub_actions)}"
            )

            center_x = int(left + top_left[0] + tmpl_w / 2)
            center_y = int(top + top_left[1] + tmpl_h / 2)

            self._execute_sub_actions(sub_actions, center_x, center_y)

        else:
            self._status(
                f"Image not found: {img_name} (score {score:.3f}) - continuing main flow"
            )
            print(
                f"[MacroExecutor] Image not found: {img_name} (score {score:.3f}) - "
                f"continuing main macro"
            )

    def _execute_sub_actions(
        self,
        sub_actions: Sequence[Action],
        found_center_x: int,
        found_center_y: int,
    ) -> None:
        """
        Execute sub-actions for a successful img_check.

        Supported sub-action types:
            'click', 'drag', 'delay', 'copy', 'paste', 'click_found'
        """
        for sub in sub_actions:
            if not self._running:
                break
            if not sub:
                continue

            sub_typ = sub[0]

            try:
                if sub_typ == "click":
                    _, x, y = sub
                    pyautogui.click(int(x), int(y))

                elif sub_typ == "drag":
                    _, start, end = sub
                    x1, y1 = start
                    x2, y2 = end
                    pyautogui.mouseDown(int(x1), int(y1))
                    pyautogui.moveTo(int(x2), int(y2), duration=0.1)
                    pyautogui.mouseUp()

                elif sub_typ == "delay":
                    delay_time = float(sub[1]) if len(sub) > 1 else 0.0
                    self._sleep_with_checks(delay_time)

                elif sub_typ == "copy":
                    pyautogui.hotkey("ctrl", "c")

                elif sub_typ == "paste":
                    pyautogui.hotkey("ctrl", "v")

                elif sub_typ == "click_found":
                    pyautogui.click(int(found_center_x), int(found_center_y))

                else:
                    self._status(f"Unknown sub-action type: {sub_typ}")

            except Exception as e:
                print(f"[MacroExecutor] Error executing sub-action {sub_typ}: {e}")
