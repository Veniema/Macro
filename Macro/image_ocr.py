"""
image_ocr.py

Image matching and OCR text post-processing utilities for Macro Maker Pro.

This module is deliberately UI-agnostic:
- No tkinter imports
- No direct references to the main app

Executor / UI code should call these helpers and decide how to display errors.
"""

from __future__ import annotations

import re
from typing import Tuple, Optional, Any, List

import numpy as np
from PIL import Image

# Lazy-imported cv2 and cached reference images
_REF_CACHE = {}  # type: ignore[var-annotated]


def _ensure_cv2():
    """
    Lazy import for OpenCV so that importing this module doesn't crash
    if opencv-python is not installed. Raises ImportError if missing.
    """
    try:
        import cv2  # type: ignore[import-untyped]
        return cv2
    except Exception as exc:  # ImportError or others
        raise ImportError(
            "opencv-python is required for image template matching. "
            "Install with: pip install opencv-python"
        ) from exc


def match_template(
    reference_path: str,
    screenshot_region: Image.Image
) -> Tuple[bool, float, Optional[Tuple[int, int]], int, int]:
    """
    Core template match helper.

    Parameters
    ----------
    reference_path : str
        Path to the reference image on disk.
    screenshot_region : PIL.Image.Image
        Region of the screen captured as an RGB image.

    Returns
    -------
    (ok, max_val, top_left, width, height)
        ok       : False if images cannot be compared (e.g. template bigger).
        max_val  : Best match score (0–1).
        top_left : (x, y) pixel position of best match inside screenshot_region,
                   or None if not found / incomparable.
        width    : Template width in pixels.
        height   : Template height in pixels.
    """
    try:
        cv2 = _ensure_cv2()

        # Load and cache the reference image in grayscale
        global _REF_CACHE
        ref_gray = _REF_CACHE.get(reference_path)
        if ref_gray is None:
            ref_gray = cv2.imread(reference_path, cv2.IMREAD_GRAYSCALE)
            if ref_gray is None:
                print(f"[match_template] Failed to read reference image: {reference_path}")
                return False, 0.0, None, 0, 0
            _REF_CACHE[reference_path] = ref_gray

        # Convert screenshot to grayscale
        screen_rgb = np.array(screenshot_region)
        if screen_rgb.ndim == 2:
            screen_gray = screen_rgb.astype(np.uint8)
        else:
            screen_gray = cv2.cvtColor(screen_rgb, cv2.COLOR_RGB2GRAY)

        rh, rw = ref_gray.shape[:2]
        sh, sw = screen_gray.shape[:2]

        # Template larger than region → not comparable
        if rh > sh or rw > sw:
            return False, 0.0, None, rw, rh

        cv2.setUseOptimized(True)
        res = cv2.matchTemplate(screen_gray, ref_gray, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)

        return True, float(max_val), (int(max_loc[0]), int(max_loc[1])), rw, rh

    except ImportError as e:
        # OpenCV is missing
        print(f"[match_template] {e}")
        return False, 0.0, None, 0, 0

    except Exception as e:
        print(f"[match_template] Unexpected error: {e}")
        return False, 0.0, None, 0, 0


def compare_images(
    reference_path: str,
    screenshot_region: Image.Image,
    threshold: float = 0.8,
) -> bool:
    """
    Backwards-compatible wrapper for simple yes/no comparison.

    Returns True if the match score >= threshold, False otherwise.
    """
    ok, max_val, _, _, _ = match_template(reference_path, screenshot_region)
    print(f"[compare_images] similarity: {max_val:.3f}, threshold: {threshold}")
    return ok and (max_val >= float(threshold))


def process_ocr_text(
    text: str,
    mode: str,
    pattern: str = "",
) -> Optional[Any]:
    """
    Post-process raw OCR text according to the selected mode.

    Parameters
    ----------
    text : str
        Raw OCR text.
    mode : str
        One of: 'all_text', 'numbers', 'email', 'custom', 'legacy'
    pattern : str
        Regex used when mode == 'custom'.

    Returns
    -------
    Any or None
        - 'all_text' : str (stripped text) or None
        - 'numbers'  : list of digit strings or None
        - 'email'    : list of email strings or None
        - 'custom'   : list of matches or None
        - 'legacy'   : single ID string or None
    """
    if not text:
        return None

    if mode == "all_text":
        return text.strip()

    elif mode == "numbers":
        numbers = re.findall(r"\d+", text)
        return numbers if numbers else None

    elif mode == "email":
        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        emails = re.findall(email_pattern, text)
        return emails if emails else None

    elif mode == "custom":
        if not pattern:
            return None
        try:
            matches: List[str] = re.findall(pattern, text)
            return matches if matches else None
        except re.error as e:
            print(f"[process_ocr_text] Invalid regex pattern '{pattern}': {e}")
            return None

    elif mode == "legacy":
        # Legacy logic copied from the monolithic version:
        # try 9-digit ID, else pad shorter digit runs with leading zeros.
        found_number = None

        m9 = re.search(r"\b(\d{9})\b", text)
        if m9:
            found_number = m9.group(1)
        else:
            m8 = re.search(r"\b(\d{8})\b", text)
            if m8:
                found_number = "0" + m8.group(1)
            else:
                m7 = re.search(r"\b(\d{7})\b", text)
                if m7:
                    found_number = "00" + m7.group(1)
                else:
                    m6 = re.search(r"\b(\d{6})\b", text)
                    if m6:
                        found_number = "000" + m6.group(1)

        return found_number

    # Unknown mode
    return None
