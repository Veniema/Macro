#!/usr/bin/env python3
"""
Macro Maker Pro v2.2.1 - Complete Edition
Advanced GUI automation tool with image recognition and enhanced OCR

New in v2.2+
- Img Check sub-action: "Click Found Image" (clicks the center of the matched template)
- Keyboard command action (press a key N times at an interval)
- Defensive guards so missing quick-action methods won't crash UI

Features:
- Point-and-click macro recording
- Image recognition with conditional branching (multi-monitor/DPI safe)
- Generalized OCR with multiple extraction modes
- Quick action sequences
- Enhanced keyboard shortcuts
- Backward compatibility with existing macros
"""

import tkinter as tk
from tkinter import simpledialog, messagebox, filedialog
import threading
import time
import re
import json
import sys
import os
import numpy as np

from pynput import mouse
import pyautogui
import pyperclip
import mss
from PIL import Image
import pytesseract


class MacroMaker:
    def __init__(self, master):
        self.master = master
        master.title("Macro Maker Pro v2.2.1 - Complete Edition")
        master.geometry("900x700")

        # Actions: ('click', x, y), ('drag', (x1,y1),(x2,y2)), ('delay', secs),
        #          ('copy',), ('paste',), ('hotkey', key1, key2, ...),
        #          ('key', key_name, count, interval),
        #          ('ocr', (x1,y1,x2,y2), mode, pattern, processing),
        #          ('img_check', image_path, (x1,y1,x2,y2), sub_actions, threshold)
        # Sub-actions supported within img_check:
        #   ('click', x, y), ('drag', (x1,y1),(x2,y2)), ('delay', secs), ('copy',), ('paste',),
        #   ('click_found',)  # NEW: click center of the found image match
        self.actions = []
        self.loop_count = 1
        self.auto_delay = tk.BooleanVar(value=False)
        self.auto_delay_time = tk.DoubleVar(value=0.5)
        self.macro_running = False
        self.macro_thread = None
        self.current_file = None

        self._setup_ui()
        self._setup_shortcuts()

        # DPI-awareness + pyautogui failsafe for reliable coords
        try:
            pyautogui.FAILSAFE = True  # move mouse to top-left to abort
            if sys.platform.startswith("win"):
                import ctypes
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass
        except Exception:
            pass

    def _setup_ui(self):
        """Initialize the user interface"""
        # Menu Bar
        self._create_menu()

        # Status Bar
        self._create_status_bar()

        # Recording Buttons
        self._create_recording_buttons()

        # Quick Actions Bar
        self._create_quick_actions()

        # Action Control Buttons
        self._create_control_buttons()

        # Execution Controls
        self._create_execution_controls()

        # Actions Listbox
        self._create_actions_list()

    def _create_menu(self):
        """Create the menu bar"""
        menubar = tk.Menu(self.master)
        self.master.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Macro (Ctrl+N)", command=self.new_macro)
        file_menu.add_command(label="Open Macro (Ctrl+O)", command=self.load_macro)
        file_menu.add_command(label="Save Macro (Ctrl+S)", command=self.save_macro)
        file_menu.add_command(label="Save As...", command=self.save_macro_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.master.quit)

    def _create_status_bar(self):
        """Create the status bar"""
        status_frame = tk.Frame(self.master)
        status_frame.pack(fill=tk.X, padx=5, pady=2)
        self.status_label = tk.Label(status_frame, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(fill=tk.X)

    def _create_recording_buttons(self):
        """Create the main recording buttons"""
        record_frame = tk.Frame(self.master)
        record_frame.pack(pady=4)

        record_btns = [
            ("🖱️ Click", self.record_click),
            ("↗️ Drag", self.record_drag),
            ("⏱️ Delay", self.add_delay),
            ("📋 Copy", self.record_copy),
            ("📄 Paste", self.record_paste),
            ("👁️ OCR", self.record_ocr),
            ("🔍 Img Check", self.record_img_check),
            ("⌨️ Key", self.record_key),
        ]

        for i, (text, cmd) in enumerate(record_btns):
            tk.Button(record_frame, text=text, command=cmd, width=10).grid(row=0, column=i, padx=2)

    def _create_quick_actions(self):
        """Create quick action buttons for common sequences"""
        quick_frame = tk.Frame(self.master)
        quick_frame.pack(pady=2)

        tk.Label(quick_frame, text="Quick Actions:", font=("Arial", 9, "bold")).pack(side=tk.LEFT, padx=5)

        # Build safely: only add a button if the method exists on self
        candidates = [
            ("Click + Copy", "_quick_click_copy"),
            ("Click + Paste", "_quick_click_paste"),
            ("Drag + Copy", "_quick_drag_copy"),
            ("Triple Click", "_quick_triple_click"),
            ("Ctrl+A + Copy", "_quick_select_all_copy"),
        ]
        for text, meth in candidates:
            if hasattr(self, meth):
                tk.Button(quick_frame, text=text, command=getattr(self, meth),
                          font=("Arial", 8), pady=1).pack(side=tk.LEFT, padx=1)

    def _create_control_buttons(self):
        """Create action control buttons"""
        control_frame = tk.Frame(self.master)
        control_frame.pack(pady=4)

        control_btns = [
            ("✏️ Edit", self.edit_action),
            ("🗑️ Delete", self.delete_action),
            ("📋 Duplicate", self.duplicate_action),
            ("⬆️ Move Up", self.move_up),
            ("⬇️ Move Down", self.move_down),
            ("💾 Insert Delay", self.insert_delay),
        ]

        for i, (text, cmd) in enumerate(control_btns):
            tk.Button(control_frame, text=text, command=cmd, width=10).grid(row=0, column=i, padx=2)

    def _create_execution_controls(self):
        """Create execution control panel"""
        exec_frame = tk.Frame(self.master)
        exec_frame.pack(pady=4)

        tk.Label(exec_frame, text="Loops:").grid(row=0, column=0, padx=2)
        tk.Button(exec_frame, text="Set Count", command=self.set_loop, width=8).grid(row=0, column=1, padx=2)
        self.loop_label = tk.Label(exec_frame, text=f"{self.loop_count}", font=("Arial", 10, "bold"))
        self.loop_label.grid(row=0, column=2, padx=5)

        tk.Checkbutton(exec_frame, text="Auto Delay", variable=self.auto_delay).grid(row=0, column=3, padx=5)
        tk.Entry(exec_frame, textvariable=self.auto_delay_time, width=5).grid(row=0, column=4, padx=2)
        tk.Label(exec_frame, text="s").grid(row=0, column=5)

        self.start_btn = tk.Button(exec_frame, text="▶️ Start (F5)", command=self.start_macro,
                                   bg="#4CAF50", fg="white", font=("Arial", 10, "bold"), width=12)
        self.start_btn.grid(row=0, column=6, padx=5)

        self.stop_btn = tk.Button(exec_frame, text="⏹️ Stop (Esc)", command=self.stop_macro,
                                  bg="#f44336", fg="white", font=("Arial", 10, "bold"), width=12, state=tk.DISABLED)
        self.stop_btn.grid(row=0, column=7, padx=5)

        tk.Button(exec_frame, text="🔍 Preview", command=self.preview_macro, width=8).grid(row=0, column=8, padx=2)
        tk.Button(exec_frame, text="🗑️ Clear All", command=self.clear_actions, width=10).grid(row=0, column=9, padx=2)

    def _create_actions_list(self):
        """Create the actions listbox with scrollbar"""
        list_frame = tk.Frame(self.master)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.listbox = tk.Listbox(list_frame, width=100, height=15, yscrollcommand=scrollbar.set,
                                  font=("Consolas", 10), selectmode=tk.SINGLE)
        self.listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.listbox.yview)

    def _setup_shortcuts(self):
        """Set up all keyboard shortcuts"""
        # Basic shortcuts
        self.master.bind('<Control-n>', lambda e: self.new_macro())
        self.master.bind('<Control-o>', lambda e: self.load_macro())
        self.master.bind('<Control-s>', lambda e: self.save_macro())
        self.master.bind('<Delete>', lambda e: self.delete_action())
        self.master.bind('<F5>', lambda e: self.start_macro())
        self.master.bind('<Escape>', lambda e: self.stop_macro())
        self.master.bind('<Control-k>', lambda e: self.record_key())

        # Enhanced shortcuts
        self.master.bind('<Control-r>', lambda e: self.start_macro())
        self.master.bind('<Control-d>', lambda e: self.duplicate_action())
        self.master.bind('<Control-e>', lambda e: self.edit_action())
        self.master.bind('<Control-t>', lambda e: self._quick_click_copy())
        self.master.bind('<Control-y>', lambda e: self._quick_click_paste())

        # Update title to show shortcuts
        self.master.title("Macro Maker Pro v2.2.1 | Ctrl+R=Run | Ctrl+T=QuickCopy | Ctrl+Y=QuickPaste | Ctrl+K=Key")

    # === CORE FUNCTIONALITY ===

    def update_status(self, message):
        """Update the status bar message"""
        self.status_label.config(text=message)

    def new_macro(self):
        """Create a new macro"""
        if self.actions and not messagebox.askyesno("New Macro", "Clear current macro?"):
            return
        self.actions = []
        self.listbox.delete(0, tk.END)
        self.current_file = None
        self.master.title("Macro Maker Pro v2.2.1")
        self.update_status("New macro created")

    def save_macro(self):
        """Save the current macro"""
        if self.current_file:
            self._save_to_file(self.current_file)
        else:
            self.save_macro_as()

    def save_macro_as(self):
        """Save macro with file dialog"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Macro files", "*.json"), ("All files", "*.*")],
            title="Save Macro As"
        )
        if filename:
            self._save_to_file(filename)

    def _save_to_file(self, filename):
        """Save macro data to file"""
        try:
            macro_data = {
                "actions": self.actions,
                "loop_count": self.loop_count,
                "auto_delay": self.auto_delay.get(),
                "auto_delay_time": self.auto_delay_time.get()
            }
            with open(filename, 'w') as f:
                json.dump(macro_data, f, indent=2)

            self.current_file = filename
            self.master.title(f"Macro Maker Pro v2.2.1 - {filename}")
            self.update_status(f"Saved: {filename}")
            messagebox.showinfo("Save", f"Macro saved to {filename}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save macro:\n{e}")

    def load_macro(self):
        """Load macro from file"""
        if self.actions and not messagebox.askyesno("Load Macro", "Replace current macro?"):
            return

        filename = filedialog.askopenfilename(
            filetypes=[("Macro files", "*.json"), ("All files", "*.*")],
            title="Load Macro"
        )
        if filename:
            try:
                with open(filename, 'r') as f:
                    macro_data = json.load(f)

                self.actions = macro_data.get("actions", [])
                self.loop_count = macro_data.get("loop_count", 1)
                self.auto_delay.set(macro_data.get("auto_delay", False))
                self.auto_delay_time.set(macro_data.get("auto_delay_time", 0.5))

                # Refresh UI
                self.listbox.delete(0, tk.END)
                for action in self.actions:
                    self.listbox.insert(tk.END, self._format_action(action))

                self.loop_label.config(text=f"{self.loop_count}")
                self.current_file = filename
                self.master.title(f"Macro Maker Pro v2.2.1 - {filename}")
                self.update_status(f"Loaded: {filename}")
                messagebox.showinfo("Load", f"Macro loaded from {filename}")
            except Exception as e:
                messagebox.showerror("Load Error", f"Failed to load macro:\n{e}")

        def _format_action(self, action):
            """Format an action for display in the listbox"""
            typ = action[0]
            if typ == 'click':
                return f"🖱️ Click at ({action[1]}, {action[2]})"
            elif typ == 'drag':
                return f"↗️ Drag from {action[1]} to {action[2]}"
            elif typ == 'delay':
                return f"⏱️ Delay {action[1]:.2f}s"
            elif typ == 'copy':
                return "📋 Copy (Ctrl+C)"
            elif typ == 'paste':
                return "📄 Paste (Ctrl+V)"
            elif typ == 'hotkey':
                keys = ' + '.join(action[1:])
                return f"⌨️ Hotkey: {keys}"
            elif typ == 'key':
                key, count, interval = action[1], action[2], action[3]
                return f"⌨️ Key: {key} ×{count} (interval {interval:.2f}s)"
            elif typ == 'ocr':
                if len(action) >= 5:
                    coords, mode, pattern, processing = action[1], action[2], action[3], action[4]
                    mode_desc = {
                        'all_text': 'All text',
                        'numbers': 'Numbers only',
                        'email': 'Email addresses',
                        'custom': f'Custom: {pattern}'
                    }.get(mode, mode)
                    return f"👁️ OCR ({mode_desc}) → {processing}"
                else:
                    return f"👁️ OCR region: {action[1]} (legacy)"
            elif typ == 'img_check':
                image_path = os.path.basename(action[1]) if len(action) > 1 else "unknown"
                sub_count = len(action[3]) if len(action) > 3 else 0
                cfg = action[4] if len(action) > 4 else None
                wait_flag = False
                if isinstance(cfg, dict):
                    wait_flag = bool(cfg.get("wait", False))
                extra = " (wait until found)" if wait_flag else ""
                return f"🔍 Image Check: {image_path}{extra} ({sub_count} sub-actions)"
            elif typ == 'click_found':
                return "🖱️ Click Found Image (center)"
            return str(action)

    def _maybe_auto_delay(self):
        """Add auto delay if enabled"""
        if self.auto_delay.get():
            d = self.auto_delay_time.get()
            self.actions.append(('delay', d))
            self.listbox.insert(tk.END, f"⏱️ Delay {d:.2f}s (auto)")

    # === RECORDING METHODS ===

    def _repick_click(self, idx):
        """Let the user click on screen to set new (x,y) for a click action."""
        self.update_status("Click anywhere to set new coordinates…")
        messagebox.showinfo("Edit Click", "Click anywhere to set the new coordinates.")

        def on_click(x, y, button, pressed):
            if pressed:
                # Update action
                self.actions[idx] = ('click', int(x), int(y))
                # Refresh UI from the Tk thread
                self.master.after(0, lambda: (
                self.listbox.delete(idx),
                self.listbox.insert(idx, self._format_action(self.actions[idx])),
                self.listbox.select_clear(0, tk.END),
                self.listbox.select_set(idx),
                self.update_status(f"Click edited → ({int(x)}, {int(y)})")
            ))
            return False  # stop listener

        mouse.Listener(on_click=on_click).start()


    def record_click(self):
        """Record a mouse click"""
        self.update_status("Click anywhere to record this click...")
        messagebox.showinfo("Record Click", "Click anywhere to record this click.")

        def on_click(x, y, button, pressed):
            if pressed:
                action = ('click', x, y)
                self.actions.append(action)
                self.master.after(0, lambda: (
                    self.listbox.insert(tk.END, self._format_action(action)),
                    self._maybe_auto_delay(),
                    self.update_status("Click recorded successfully")
                ))
                return False
        mouse.Listener(on_click=on_click).start()

    def record_drag(self):
        """Record a mouse drag"""
        self.update_status("Click and drag to record this action...")
        messagebox.showinfo("Record Drag", "Click and drag to record this action.")

        coords = []
        def on_click(x, y, button, pressed):
            if pressed:
                coords.clear()
                coords.append((x, y))
            else:
                coords.append((x, y))
                if len(coords) == 2:
                    action = ('drag', coords[0], coords[1])
                    self.actions.append(action)
                    self.master.after(0, lambda: (
                        self.listbox.insert(tk.END, self._format_action(action)),
                        self._maybe_auto_delay(),
                        self.update_status("Drag recorded successfully")
                    ))
                    return False
        mouse.Listener(on_click=on_click).start()

    def record_copy(self):
        """Record a copy action"""
        action = ('copy',)
        self.actions.append(action)
        self.listbox.insert(tk.END, self._format_action(action))
        self._maybe_auto_delay()
        self.update_status("Copy action added")

    def record_paste(self):
        """Record a paste action"""
        action = ('paste',)
        self.actions.append(action)
        self.listbox.insert(tk.END, self._format_action(action))
        self._maybe_auto_delay()
        self.update_status("Paste action added")

    def record_ocr(self):
        """Record an OCR action with enhanced options"""
        self.update_status("Click upper-left then lower-right to define OCR region...")
        messagebox.showinfo("Record OCR Region", "Click upper-left then release lower-right to define OCR region.")

        coords = []
        def on_click(x, y, button, pressed):
            if pressed:
                coords.clear()
                coords.append((x, y))
            else:
                coords.append((x, y))
                if len(coords) == 2:
                    self.master.after(0, lambda: self._configure_ocr_options(coords))
                    return False
        mouse.Listener(on_click=on_click).start()

    def _configure_ocr_options(self, coords):
        """Configure OCR options through a dialog"""
        dialog = tk.Toplevel(self.master)
        dialog.title("OCR Configuration")
        dialog.geometry("500x400")
        dialog.transient(self.master)
        dialog.grab_set()

        mode_var = tk.StringVar(value="all_text")
        pattern_var = tk.StringVar()
        processing_var = tk.StringVar(value="copy")

        tk.Label(dialog, text="OCR Configuration", font=("Arial", 14, "bold")).pack(pady=10)

        mode_frame = tk.LabelFrame(dialog, text="What to Extract", padx=10, pady=10)
        mode_frame.pack(fill="x", padx=10, pady=5)

        tk.Radiobutton(mode_frame, text="All text (copy everything)",
                       variable=mode_var, value="all_text").pack(anchor="w")
        tk.Radiobutton(mode_frame, text="Numbers only (any digits found)",
                       variable=mode_var, value="numbers").pack(anchor="w")
        tk.Radiobutton(mode_frame, text="Email addresses",
                       variable=mode_var, value="email").pack(anchor="w")
        tk.Radiobutton(mode_frame, text="Custom pattern (regex)",
                       variable=mode_var, value="custom").pack(anchor="w")

        pattern_frame = tk.LabelFrame(dialog, text="Custom Pattern (if selected)", padx=10, pady=10)
        pattern_frame.pack(fill="x", padx=10, pady=5)

        tk.Label(pattern_frame, text="Regex pattern:").pack(anchor="w")
        pattern_entry = tk.Entry(pattern_frame, textvariable=pattern_var, width=50)
        pattern_entry.pack(fill="x", pady=2)

        tk.Label(pattern_frame, text="Examples: \\d{4,8} (4-8 digits), \\b\\w+@\\w+\\.\\w+\\b (emails)",
                 font=("Arial", 8), fg="gray").pack(anchor="w")

        process_frame = tk.LabelFrame(dialog, text="What to do with extracted text", padx=10, pady=10)
        process_frame.pack(fill="x", padx=10, pady=5)

        tk.Radiobutton(process_frame, text="Copy to clipboard",
                       variable=processing_var, value="copy").pack(anchor="w")
        tk.Radiobutton(process_frame, text="Save to variable (show in status)",
                       variable=processing_var, value="show").pack(anchor="w")
        tk.Radiobutton(process_frame, text="Copy first match only",
                       variable=processing_var, value="first").pack(anchor="w")
        tk.Radiobutton(process_frame, text="Copy all matches (separated by spaces)",
                       variable=processing_var, value="all").pack(anchor="w")

        button_frame = tk.Frame(dialog)
        button_frame.pack(pady=20)

        def save_ocr():
            mode = mode_var.get()
            pattern = pattern_var.get() if mode == "custom" else ""
            processing = processing_var.get()

            if mode == "custom" and not pattern:
                messagebox.showwarning("Missing Pattern", "Please enter a regex pattern for custom mode.")
                return

            (x1, y1), (x2, y2) = coords
            action = ('ocr', (x1, y1, x2, y2), mode, pattern, processing)
            self.actions.append(action)
            self.listbox.insert(tk.END, self._format_action(action))
            self._maybe_auto_delay()
            self.update_status(f"OCR region added: {mode} mode")
            dialog.destroy()

        def cancel_ocr():
            self.update_status("OCR recording cancelled")
            dialog.destroy()

        tk.Button(button_frame, text="Add OCR Action", command=save_ocr,
                  bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side="left", padx=5)
        tk.Button(button_frame, text="Cancel", command=cancel_ocr).pack(side="left", padx=5)

    def record_img_check(self):
        """Record an image check action with branching logic"""
        image_path = filedialog.askopenfilename(
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp *.gif"), ("All files", "*.*")],
            title="Select Reference Image"
        )
        if not image_path:
            self.update_status("Image check cancelled")
            return

        self.update_status("Click and drag to define search region...")
        messagebox.showinfo("Define Search Region",
                            "Click and drag to define the region where the image should be found.")

        coords = []
        def on_click(x, y, button, pressed):
            if pressed:
                coords.clear()
                coords.append((x, y))
            else:
                coords.append((x, y))
                if len(coords) == 2:
                    self.master.after(0, lambda: self._finish_img_check_recording(coords, image_path))
                    return False
        mouse.Listener(on_click=on_click).start()

        def _finish_img_check_recording(self, coords, image_path):
            (x1, y1), (x2, y2) = coords

            threshold = simpledialog.askfloat(
                "Image Similarity",
                "Enter similarity threshold (0.0-1.0, higher = more strict):",
                initialvalue=0.8,
                minvalue=0.0,
                maxvalue=1.0
            )
            if threshold is None:
                threshold = 0.8

            # NEW: ask if this image check should wait until the image appears
            wait_until_found = messagebox.askyesno(
                "Wait Until Found?",
                "Do you want this Image Check to keep checking until the image is found?\n\n"
                "Yes = poll the region until the image appears.\n"
                "No  = check once and continue."
            )

            sub_actions = self._create_sub_actions_dialog()

            # For backward compatibility we store either a bare threshold (old behavior)
            # or a dict with extra options.
            if wait_until_found:
                config = {
                    "threshold": float(threshold),
                    "wait": True,
                    "interval": 0.5,   # polling interval in seconds
                    "timeout": 0.0,    # 0 = no timeout; stop only if macro is stopped
                }
            else:
                config = float(threshold)

            action = ('img_check', image_path, (x1, y1, x2, y2), sub_actions, config)
            self.actions.append(action)
            self.listbox.insert(tk.END, self._format_action(action))
            self._maybe_auto_delay()

            img_name = os.path.basename(image_path)
            self.update_status(f"Image check added: {img_name} with {len(sub_actions)} sub-actions")


    def _create_sub_actions_dialog(self):
        """Create a dialog to define sub-actions for image check branching"""
        sub_actions = []

        dialog = tk.Toplevel(self.master)
        dialog.title("Define Sub-Actions")
        dialog.geometry("620x420")
        dialog.transient(self.master)
        dialog.grab_set()

        tk.Label(dialog, text="Define actions to execute when image IS found:",
                 font=("Arial", 12, "bold")).pack(pady=10)

        frame = tk.Frame(dialog)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        sub_listbox = tk.Listbox(frame)
        sub_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(frame, orient=tk.VERTICAL, command=sub_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        sub_listbox.config(yscrollcommand=scrollbar.set)

        btn_frame = tk.Frame(dialog)
        btn_frame.pack(fill=tk.X, padx=10, pady=5)

        def add_click():
            messagebox.showinfo("Record Click", "Click anywhere to record this click for sub-actions.")
            dialog.withdraw()
            def on_click(x, y, button, pressed):
                if pressed:
                    action = ('click', x, y)
                    sub_actions.append(action)
                    self.master.after(0, lambda: (
                        sub_listbox.insert(tk.END, self._format_action(action)),
                        dialog.deiconify()
                    ))
                    return False
            mouse.Listener(on_click=on_click).start()

        def add_delay():
            d = simpledialog.askfloat("Delay", "Enter delay in seconds:", initialvalue=1.0)
            if d is not None:
                action = ('delay', d)
                sub_actions.append(action)
                sub_listbox.insert(tk.END, self._format_action(action))

        def add_copy():
            action = ('copy',)
            sub_actions.append(action)
            sub_listbox.insert(tk.END, self._format_action(action))

        def add_paste():
            action = ('paste',)
            sub_actions.append(action)
            sub_listbox.insert(tk.END, self._format_action(action))

        def add_click_found():
            action = ('click_found',)
            sub_actions.append(action)
            sub_listbox.insert(tk.END, self._format_action(action))

        def remove_action():
            selection = sub_listbox.curselection()
            if selection:
                idx = selection[0]
                sub_actions.pop(idx)
                sub_listbox.delete(idx)

        tk.Button(btn_frame, text="Add Click", command=add_click).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Add Delay", command=add_delay).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Add Copy", command=add_copy).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Add Paste", command=add_paste).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Click Found Image", command=add_click_found).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame, text="Remove", command=remove_action).pack(side=tk.LEFT, padx=2)

        def done():
            dialog.destroy()
        tk.Button(dialog, text="Done", command=done, font=("Arial", 12, "bold")).pack(pady=10)

        dialog.wait_window()
        return sub_actions

    def record_key(self):
        """Create a key-press action (e.g., Arrow Down × N at an interval)."""
        dialog = tk.Toplevel(self.master)
        dialog.title("Add Keyboard Command")
        dialog.geometry("360x260")
        dialog.transient(self.master)
        dialog.grab_set()

        try:
            known = sorted(pyautogui.KEYBOARD_KEYS)
        except Exception:
            known = ["up", "down", "left", "right", "enter", "tab", "esc", "space", "backspace",
                     "delete", "home", "end", "pageup", "pagedown"] + [f"f{i}" for i in range(1, 13)]

        key_var = tk.StringVar(value="down")
        count_var = tk.IntVar(value=1)
        interval_var = tk.DoubleVar(value=0.05)

        frm = tk.Frame(dialog); frm.pack(fill="both", expand=True, padx=12, pady=12)

        tk.Label(frm, text="Key name:").grid(row=0, column=0, sticky="w")
        key_entry = tk.Entry(frm, textvariable=key_var, width=18)
        key_entry.grid(row=0, column=1, sticky="w")
        tk.Label(frm, text="Common:").grid(row=1, column=0, sticky="nw", pady=(8, 0))
        common_list = tk.Listbox(frm, height=8, width=18, exportselection=False)
        for k in ["up", "down", "left", "right", "enter", "tab", "esc", "space", "backspace",
                  "delete", "home", "end", "pageup", "pagedown"]:
            common_list.insert(tk.END, k)
        common_list.grid(row=1, column=1, sticky="w", pady=(8, 0))

        def pick_key(_evt=None):
            sel = common_list.curselection()
            if sel:
                key_var.set(common_list.get(sel[0]))
        common_list.bind("<<ListboxSelect>>", pick_key)

        tk.Label(frm, text="Count:").grid(row=2, column=0, sticky="w", pady=(10, 0))
        tk.Spinbox(frm, from_=1, to=999, textvariable=count_var, width=6).grid(row=2, column=1, sticky="w", pady=(10, 0))

        tk.Label(frm, text="Interval (s):").grid(row=3, column=0, sticky="w", pady=(6, 0))
        tk.Entry(frm, textvariable=interval_var, width=8).grid(row=3, column=1, sticky="w", pady=(6, 0))

        btns = tk.Frame(dialog); btns.pack(pady=10)

        def add_action():
            key = key_var.get().strip().lower()
            cnt = max(1, int(count_var.get()))
            try:
                iv = float(interval_var.get())
            except ValueError:
                iv = 0.0

            try:
                known_keys = sorted(pyautogui.KEYBOARD_KEYS)
            except Exception:
                known_keys = []
            if known_keys and key not in known_keys:
                messagebox.showwarning(
                    "Unknown Key",
                    f"'{key}' is not a recognized key.\n\n"
                    f"Try one of: {', '.join(known_keys[:20])} ..."
                )
                return

            action = ('key', key, cnt, iv)
            self.actions.append(action)
            self.listbox.insert(tk.END, self._format_action(action))
            self._maybe_auto_delay()
            self.update_status(f"Key action added: {key} ×{cnt}")
            dialog.destroy()

        tk.Button(btns, text="Add", command=add_action, bg="#4CAF50", fg="white").pack(side="left", padx=6)
        tk.Button(btns, text="Cancel", command=dialog.destroy).pack(side="left", padx=6)

        key_entry.focus_set()

    # === QUICK ACTIONS ===

    def _quick_click_copy(self):
        """Add click followed by copy action"""
        self.update_status("Click where you want to click then copy...")
        messagebox.showinfo("Quick Click+Copy", "Click anywhere to record click + copy sequence.")

        def on_click(x, y, button, pressed):
            if pressed:
                click_action = ('click', x, y)
                self.actions.append(click_action)
                copy_action = ('copy',)
                self.actions.append(copy_action)
                self.master.after(0, lambda: (
                    self.listbox.insert(tk.END, self._format_action(click_action)),
                    self.listbox.insert(tk.END, self._format_action(copy_action)),
                    self.update_status("Click + Copy sequence added")
                ))
                return False
        mouse.Listener(on_click=on_click).start()

    def _quick_click_paste(self):
        """Add click followed by paste action"""
        self.update_status("Click where you want to click then paste...")
        messagebox.showinfo("Quick Click+Paste", "Click anywhere to record click + paste sequence.")

        def on_click(x, y, button, pressed):
            if pressed:
                click_action = ('click', x, y)
                self.actions.append(click_action)
                paste_action = ('paste',)
                self.actions.append(paste_action)
                self.master.after(0, lambda: (
                    self.listbox.insert(tk.END, self._format_action(click_action)),
                    self.listbox.insert(tk.END, self._format_action(paste_action)),
                    self.update_status("Click + Paste sequence added")
                ))
                return False
        mouse.Listener(on_click=on_click).start()

    def _quick_drag_copy(self):
        """Add drag followed by copy action"""
        self.update_status("Drag to select text then auto-copy...")
        messagebox.showinfo("Quick Drag+Copy", "Drag to select text, will auto-add copy action.")

        coords = []
        def on_click(x, y, button, pressed):
            if pressed:
                coords.clear()
                coords.append((x, y))
            else:
                coords.append((x, y))
                if len(coords) == 2:
                    drag_action = ('drag', coords[0], coords[1])
                    self.actions.append(drag_action)
                    copy_action = ('copy',)
                    self.actions.append(copy_action)
                    self.master.after(0, lambda: (
                        self.listbox.insert(tk.END, self._format_action(drag_action)),
                        self.listbox.insert(tk.END, self._format_action(copy_action)),
                        self.update_status("Drag + Copy sequence added")
                    ))
                    return False
        mouse.Listener(on_click=on_click).start()

    def _quick_triple_click(self):
        """Add triple click (select line) action"""
        self.update_status("Click where you want to triple-click...")
        messagebox.showinfo("Triple Click", "Click anywhere to add triple-click action.")

        def on_click(x, y, button, pressed):
            if pressed:
                actions_to_add = []
                for i in range(3):
                    click_action = ('click', x, y)
                    self.actions.append(click_action)
                    actions_to_add.append((click_action, f" ({i+1}/3)"))
                    if i < 2:
                        delay_action = ('delay', 0.05)
                        self.actions.append(delay_action)
                        actions_to_add.append((delay_action, ""))

                def update_ui():
                    for action, suffix in actions_to_add:
                        self.listbox.insert(tk.END, self._format_action(action) + suffix)
                    self.update_status("Triple-click sequence added")

                self.master.after(0, update_ui)
                return False
        mouse.Listener(on_click=on_click).start()

    def _quick_select_all_copy(self):
        """Add Ctrl+A + Copy sequence"""
        select_action = ('hotkey', 'ctrl', 'a')
        self.actions.append(select_action)
        self.listbox.insert(tk.END, self._format_action(select_action))
        copy_action = ('copy',)
        self.actions.append(copy_action)
        self.listbox.insert(tk.END, self._format_action(copy_action))
        self.update_status("Select All + Copy sequence added")

    # === ACTION MANAGEMENT ===

    def add_delay(self):
        """Add a delay action"""
        d = simpledialog.askfloat("Delay (s)", "Enter delay in seconds:", minvalue=0.0, initialvalue=1.0)
        if d is not None:
            action = ('delay', d)
            self.actions.append(action)
            self.listbox.insert(tk.END, self._format_action(action))
            self.update_status(f"Added {d:.2f}s delay")

    def insert_delay(self):
        """Insert delay after selected action"""
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an action first.")
            return
        d = simpledialog.askfloat("Insert Delay", "Enter delay in seconds:", minvalue=0.0, initialvalue=1.0)
        if d is not None:
            idx = sel[0] + 1  # Insert after selected item
            action = ('delay', d)
            self.actions.insert(idx, action)
            self.listbox.insert(idx, self._format_action(action))
            self.update_status(f"Inserted {d:.2f}s delay")

    def duplicate_action(self):
        """Duplicate the selected action"""
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an action to duplicate.")
            return

        idx = sel[0]
        action = self.actions[idx].copy() if hasattr(self.actions[idx], 'copy') else tuple(self.actions[idx])
        self.actions.insert(idx + 1, action)
        self.listbox.insert(idx + 1, self._format_action(action) + " (copy)")
        self.listbox.select_clear(0, tk.END)
        self.listbox.select_set(idx + 1)
        self.update_status("Action duplicated")

    def delete_action(self):
        """Delete the selected action"""
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an action to delete.")
            return

        idx = sel[0]
        self.actions.pop(idx)
        self.listbox.delete(idx)
        self.update_status("Action deleted")

    def move_up(self):
        """Move selected action up"""
        sel = self.listbox.curselection()
        if not sel or sel[0] == 0:
            return

        idx = sel[0]
        self.actions[idx - 1], self.actions[idx] = self.actions[idx], self.actions[idx - 1]

        self.listbox.delete(idx - 1, idx)
        self.listbox.insert(idx - 1, self._format_action(self.actions[idx - 1]))
        self.listbox.insert(idx, self._format_action(self.actions[idx]))
        self.listbox.select_set(idx - 1)
        self.update_status("Action moved up")

    def move_down(self):
        """Move selected action down"""
        sel = self.listbox.curselection()
        if not sel or sel[0] >= len(self.actions) - 1:
            return

        idx = sel[0]
        self.actions[idx], self.actions[idx + 1] = self.actions[idx + 1], self.actions[idx]

        self.listbox.delete(idx, idx + 1)
        self.listbox.insert(idx, self._format_action(self.actions[idx]))
        self.listbox.insert(idx + 1, self._format_action(self.actions[idx + 1]))
        self.listbox.select_set(idx + 1)
        self.update_status("Action moved down")

    def edit_action(self):
        """Edit the selected action"""
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("No Selection", "Select an action to edit.")
            return

        idx = sel[0]
        act = self.actions[idx]
        typ = act[0]

        if typ == 'delay':
            new_delay = simpledialog.askfloat("Edit Delay", "Enter new delay:", initialvalue=act[1])
            if new_delay is not None:
                self.actions[idx] = ('delay', new_delay)
                self.listbox.delete(idx)
                self.listbox.insert(idx, self._format_action(self.actions[idx]))
                self.listbox.select_set(idx)
                self.update_status("Delay action edited")
            return
        
        elif typ == 'click':
            # act = ('click', x, y)
            x0, y0 = int(act[1]), int(act[2])

            repick = messagebox.askyesno(
                "Edit Click",
                "Do you want to re-pick the coordinates on screen?\n\n"
                "Yes = click to set new (x,y)\nNo = type numbers manually"
            )
            
            if repick:
                self._repick_click(idx)
                return
        
            new_x = simpledialog.askinteger("Edit Click", "New X:", initialvalue=x0)
            if new_x is None:
                return
            new_y = simpledialog.askinteger("Edit Click", "New Y:", initialvalue=y0)
            if new_y is None:
                return

            self.actions[idx] = ('click', int(new_x), int(new_y))
            self.listbox.delete(idx)
            self.listbox.insert(idx, self._format_action(self.actions[idx]))
            self.listbox.select_clear(0, tk.END)
            self.listbox.select_set(idx)
            self.update_status(f"Click edited → ({int(new_x)}, {int(new_y)})")
            return

        else:
            messagebox.showinfo("Edit", f"Editing {typ} actions is not yet supported.")

    def preview_macro(self):
        """Show a preview of what the macro will do"""
        if not self.actions:
            messagebox.showwarning("Empty", "No actions to preview.")
            return

        preview_text = f"Macro Preview - Will execute {self.loop_count} time(s):\n\n"
        for i, action in enumerate(self.actions, 1):
            preview_text += f"{i:2d}. {self._format_action(action)}\n"

        preview_window = tk.Toplevel(self.master)
        preview_window.title("Macro Preview")
        preview_window.geometry("600x400")

        text_widget = tk.Text(preview_window, wrap=tk.WORD, font=("Consolas", 10))
        text_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        text_widget.insert(tk.END, preview_text)
        text_widget.config(state=tk.DISABLED)

    def clear_actions(self):
        """Clear all actions"""
        if self.actions and messagebox.askyesno("Clear All", "Clear all actions?"):
            self.actions = []
            self.listbox.delete(0, tk.END)
            self.update_status("All actions cleared")

    def set_loop(self):
        """Set loop count"""
        count = simpledialog.askinteger("Loop Count", "Enter number of loops:",
                                        minvalue=1, initialvalue=self.loop_count)
        if count:
            self.loop_count = count
            self.loop_label.config(text=f"{self.loop_count}")
            self.update_status(f"Loop count set to {self.loop_count}")

    # === IMAGE PROCESSING ===

    def _match_template(self, reference_path, screenshot_region):
        """Return (ok, max_val, top_left(x,y), tmpl_w, tmpl_h). ok=False if not comparable."""
        try:
            import cv2

            if not hasattr(self, '_ref_cache'):
                self._ref_cache = {}

            ref_gray = self._ref_cache.get(reference_path)
            if ref_gray is None:
                ref_gray = cv2.imread(reference_path, cv2.IMREAD_GRAYSCALE)
                if ref_gray is None:
                    print(f"Failed to read reference image: {reference_path}")
                    return False, 0.0, None, 0, 0
                self._ref_cache[reference_path] = ref_gray

            screen_bgr = np.array(screenshot_region)
            if screen_bgr.ndim == 2:
                screen_gray = screen_bgr.astype(np.uint8)
            else:
                screen_gray = cv2.cvtColor(screen_bgr, cv2.COLOR_RGB2GRAY)

            rh, rw = ref_gray.shape[:2]
            sh, sw = screen_gray.shape[:2]
            if rh > sh or rw > sw:
                return False, 0.0, None, rw, rh

            cv2.setUseOptimized(True)
            res = cv2.matchTemplate(screen_gray, ref_gray, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            return True, float(max_val), (int(max_loc[0]), int(max_loc[1])), rw, rh

        except Exception as e:
            print(f"_match_template error: {e}")
            try:
                self.master.after(0, lambda: self.update_status("Install opencv-python for image matching"))
            except Exception:
                pass
            return False, 0.0, None, 0, 0

    def _compare_images(self, reference_path, screenshot_region, threshold=0.8):
        """Compatibility wrapper. Returns True if match score >= threshold."""
        ok, max_val, _, _, _ = self._match_template(reference_path, screenshot_region)
        print(f"Image similarity: {max_val:.3f}, threshold: {threshold}")
        return ok and (max_val >= float(threshold))

    def _process_ocr_text(self, text, mode, pattern):
        """Process OCR text based on mode and return results"""
        if not text:
            return None

        if mode == "all_text":
            return text.strip()

        elif mode == "numbers":
            numbers = re.findall(r'\d+', text)
            return numbers if numbers else None

        elif mode == "email":
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            emails = re.findall(email_pattern, text)
            return emails if emails else None

        elif mode == "custom":
            if not pattern:
                return None
            try:
                matches = re.findall(pattern, text)
                return matches if matches else None
            except re.error as e:
                print(f"Invalid regex pattern '{pattern}': {e}")
                return None

        elif mode == "legacy":
            found_number = None
            m9 = re.search(r'\b(\d{9})\b', text)
            if m9:
                found_number = m9.group(1)
            else:
                m8 = re.search(r'\b(\d{8})\b', text)
                if m8:
                    found_number = "0" + m8.group(1)
                else:
                    m7 = re.search(r'\b(\d{7})\b', text)
                    if m7:
                        found_number = "00" + m7.group(1)
                    else:
                        m6 = re.search(r'\b(\d{6})\b', text)
                        if m6:
                            found_number = "000" + m6.group(1)
            return found_number

        return None

    # === MACRO EXECUTION ===

    def start_macro(self):
        """Start macro execution"""
        if not self.actions:
            messagebox.showwarning("Empty Macro", "No actions to execute.")
            return

        if self.macro_running:
            messagebox.showwarning("Already Running", "Macro is already running.")
            return

        self.macro_running = True
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)

        self.macro_thread = threading.Thread(target=self.run_macro)
        self.macro_thread.daemon = True
        self.macro_thread.start()

    def stop_macro(self):
        """Stop macro execution"""
        self.macro_running = False
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.update_status("Macro stopped")

    def run_macro(self):
        """Execute the macro actions"""
        try:
            for i in range(3, 0, -1):
                if not self.macro_running:
                    return
                self.master.after(0, lambda cnt=i: self.update_status(f"Starting in {cnt}..."))
                time.sleep(1)

            total_actions = len(self.actions) * self.loop_count
            action_count = 0

            for loop in range(self.loop_count):
                if not self.macro_running:
                    break

                self.master.after(0, lambda l=loop + 1: self.update_status(f"Executing loop {l}/{self.loop_count}"))

                for i, act in enumerate(self.actions):
                    if not self.macro_running:
                        break

                    action_count += 1
                    progress = f"Action {action_count}/{total_actions}"
                    self.master.after(0, lambda p=progress: self.update_status(p))

                    typ = act[0]
                    try:
                        if typ == 'click':
                            _, x, y = act
                            pyautogui.click(x, y)

                        elif typ == 'drag':
                            _, (x1, y1), (x2, y2) = act
                            pyautogui.mouseDown(x1, y1)
                            pyautogui.moveTo(x2, y2, duration=0.1)
                            pyautogui.mouseUp()

                        elif typ == 'delay':
                            delay_time = act[1]
                            steps = max(1, int(delay_time * 10))
                            for _ in range(steps):
                                if not self.macro_running:
                                    break
                                time.sleep(delay_time / steps)

                        elif typ == 'copy':
                            pyautogui.hotkey('ctrl', 'c')

                        elif typ == 'paste':
                            pyautogui.hotkey('ctrl', 'v')

                        elif typ == 'hotkey':
                            keys = act[1:]
                            pyautogui.hotkey(*keys)

                        elif typ == 'key':
                            _, key_name, count, interval = act
                            try:
                                if key_name not in pyautogui.KEYBOARD_KEYS:
                                    raise ValueError(f"Unsupported key: {key_name}")
                                pyautogui.press(key_name, presses=int(count), interval=float(interval))
                            except Exception as e:
                                print(f"Key press error: {e}")

                        elif typ == 'ocr':
                            if len(act) >= 5:
                                x1, y1, x2, y2 = act[1]
                                mode, pattern, processing = act[2], act[3], act[4]
                            else:
                                x1, y1, x2, y2 = act[1]
                                mode, pattern, processing = "legacy", "", "copy"

                            left, top = min(x1, x2), min(y1, y2)
                            width, height = abs(x2 - x1), abs(y2 - y1)

                            with mss.mss() as sct:
                                monitor = {'top': int(top), 'left': int(left), 'width': int(width), 'height': int(height)}
                                sct_img = sct.grab(monitor)
                                img = Image.frombytes('RGB', sct_img.size, sct_img.rgb)

                            configs = ['--psm 6', '--psm 7', '--psm 8', '--psm 13']
                            text = ""
                            for config in configs:
                                try:
                                    text = pytesseract.image_to_string(img, config=config).strip()
                                    if text:
                                        break
                                except Exception:
                                    continue
                            if not text:
                                text = pytesseract.image_to_string(img).strip()

                            result = self._process_ocr_text(text, mode, pattern)

                            if result:
                                if processing in ['copy', 'first']:
                                    if isinstance(result, list):
                                        pyperclip.copy(result[0] if result else "")
                                        self.master.after(0, lambda r=result[0]: self.update_status(f"OCR: Copied '{r}'"))
                                    else:
                                        pyperclip.copy(str(result))
                                        self.master.after(0, lambda r=result: self.update_status(f"OCR: Copied '{r}'"))
                                elif processing == 'all':
                                    if isinstance(result, list):
                                        combined = " ".join(str(r) for r in result)
                                        pyperclip.copy(combined)
                                        self.master.after(0, lambda r=combined: self.update_status(f"OCR: Copied {len(result)} matches"))
                                    else:
                                        pyperclip.copy(str(result))
                                        self.master.after(0, lambda r=result: self.update_status(f"OCR: Copied '{r}'"))
                                elif processing == 'show':
                                    display_result = result if isinstance(result, str) else str(result)
                                    self.master.after(0, lambda r=display_result: self.update_status(f"OCR Result: '{r}'"))
                            else:
                                self.master.after(0, lambda: self.update_status(f"OCR: No matches found for {mode} mode"))

                        elif typ == 'img_check':
                            image_path, (x1, y1, x2, y2), sub_actions, cfg = act[1], act[2], act[3], act[4]
                            left, top = min(x1, x2), min(y1, y2)
                            width, height = abs(x2 - x1), abs(y2 - y1)

                            # Backward-compatible config handling
                            wait = False
                            interval = 0.5
                            timeout = 0.0
                            if isinstance(cfg, dict):
                                threshold = float(cfg.get("threshold", 0.8))
                                wait = bool(cfg.get("wait", False))
                                interval = float(cfg.get("interval", 0.5))
                                timeout = float(cfg.get("timeout", 0.0))
                            else:
                                threshold = float(cfg)

                            img_name = os.path.basename(image_path)

                            def grab_region():
                                try:
                                    with mss.mss() as sct:
                                        region = {
                                            'top': int(top),
                                            'left': int(left),
                                            'width': int(width),
                                            'height': int(height)
                                        }
                                        sct_img = sct.grab(region)
                                        return Image.frombytes('RGB', sct_img.size, sct_img.rgb)
                                except Exception as capture_error:
                                    print(f"Screenshot capture error (mss): {capture_error}")
                                    return pyautogui.screenshot(
                                        region=(int(left), int(top), int(width), int(height))
                                    )

                            image_found = False
                            score = 0.0
                            top_left = None
                            tw = th = 0

                            if wait:
                                self.master.after(
                                    0,
                                    lambda n=img_name: self.update_status(f"Waiting for image: {n}...")
                                )
                                start_time = time.time()
                                while self.macro_running:
                                    img = grab_region()
                                    ok, score, top_left, tw, th = self._match_template(image_path, img)
                                    if ok and (score >= threshold):
                                        image_found = True
                                        break
                                    if not ok:
                                        # Can't compare; abort waiting to avoid infinite loop
                                        break
                                    if timeout > 0.0 and (time.time() - start_time) >= timeout:
                                        break
                                    time.sleep(max(0.01, interval))
                            else:
                                img = grab_region()
                                ok, score, top_left, tw, th = self._match_template(image_path, img)
                                image_found = ok and (score >= threshold)

                            if not self.macro_running:
                                continue  # macro was stopped while waiting

                            if image_found:
                                self.master.after(
                                    0,
                                    lambda n=img_name, s=score: self.update_status(
                                        f"Image found: {n} (score {s:.3f}) - executing sub-actions"
                                    )
                                )
                                print(
                                    f"Image found: {img_name} - score {score:.3f} - "
                                    f"executing {len(sub_actions)} sub-actions"
                                )

                                abs_cx = abs_cy = None
                                if top_left is not None:
                                    abs_cx = int(left + top_left[0] + tw / 2)
                                    abs_cy = int(top + top_left[1] + th / 2)

                                for sub_act in sub_actions:
                                    if not self.macro_running:
                                        break
                                    sub_typ = sub_act[0]
                                    try:
                                        if sub_typ == 'click':
                                            _, sx, sy = sub_act
                                            pyautogui.click(sx, sy)
                                        elif sub_typ == 'drag':
                                            _, (sx1, sy1), (sx2, sy2) = sub_act
                                            pyautogui.mouseDown(sx1, sy1)
                                            pyautogui.moveTo(sx2, sy2, duration=0.1)
                                            pyautogui.mouseUp()
                                        elif sub_typ == 'delay':
                                            delay_time = sub_act[1]
                                            steps = max(1, int(delay_time * 10))
                                            for _ in range(steps):
                                                if not self.macro_running:
                                                    break
                                                time.sleep(delay_time / steps)
                                        elif sub_typ == 'copy':
                                            pyautogui.hotkey('ctrl', 'c')
                                        elif sub_typ == 'paste':
                                            pyautogui.hotkey('ctrl', 'v')
                                        elif sub_typ == 'click_found':
                                            if abs_cx is not None and abs_cy is not None:
                                                pyautogui.click(abs_cx, abs_cy)
                                    except Exception as sub_e:
                                        print(f"Error executing sub-action {sub_typ}: {sub_e}")
                            else:
                                self.master.after(
                                    0,
                                    lambda n=img_name, s=score: self.update_status(
                                        f"Image not found: {n} (score {s:.3f}) - continuing main flow"
                                    )
                                )
                                print(
                                    f"Image not found: {img_name} (score {score:.3f}) - "
                                    f"continuing with main macro"
                                )

                    except Exception as e:
                        error_msg = f"Error executing {typ} action: {str(e)}"
                        print(error_msg)
                        self.master.after(0, lambda msg=error_msg: messagebox.showerror("Execution Error", msg))

            if self.macro_running:
                self.master.after(0, lambda: self.update_status("Macro completed successfully!"))
                self.master.after(0, lambda: messagebox.showinfo("Complete", "Macro execution finished!"))

        except Exception as e:
            error_msg = f"Fatal error during macro execution: {str(e)}"
            print(error_msg)
            self.master.after(0, lambda msg=error_msg: messagebox.showerror("Fatal Error", msg))

        finally:
            self.macro_running = False
            self.master.after(0, lambda: self.start_btn.config(state=tk.NORMAL))
            self.master.after(0, lambda: self.stop_btn.config(state=tk.DISABLED))
            if not self.macro_running:
                self.master.after(0, lambda: self.update_status("Ready"))


if __name__ == "__main__":
    root = tk.Tk()
    app = MacroMaker(root)
    root.mainloop()
