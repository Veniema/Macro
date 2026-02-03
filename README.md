# Macro Maker Pro

Macro Maker Pro is a lightweight, Tkinter-based desktop app for recording and replaying automation sequences (mouse, keyboard, OCR, and image checks). It provides a UI for building macros step-by-step and a standalone execution engine for running them with status callbacks.

## Features

- Record mouse clicks, drags, delays, copy/paste, and hotkeys.
- OCR actions with multiple modes (all text, numbers, emails, custom regex).
- Image checks with optional “wait until found” logic and sub-actions.
- Looping execution with a dedicated, UI-agnostic executor.

## Requirements

- Python 3.10+
- Tkinter (bundled with most Python installs)
- Third-party libraries used by the UI/executor:
  - `pynput`
  - `pyautogui`
  - `mss`
  - `Pillow`
  - `pytesseract`
  - `pyperclip`
  - `numpy`
  - `opencv-python` (required for image template matching)

## Run the app

```bash
python3 /workspace/Macro/Macro/main.py
```

> Tip: OCR features require a working Tesseract installation on your system. If OCR or image matching fails, confirm `pytesseract` and `opencv-python` are installed and available.

## Project layout

```
Macro/
├── Macro/
│   ├── actions.py      # Action formatting and helpers
│   ├── executor.py     # UI-agnostic macro execution engine
│   ├── image_ocr.py    # OCR text processing + template matching
│   ├── main.py         # App entry point
│   └── ui.py           # Tkinter UI
└── README.md
```

## Notes

- Move the mouse to the top-left corner to trigger PyAutoGUI’s failsafe and abort a running macro.
- The executor runs in a background thread; the UI uses callbacks for status/error updates.
